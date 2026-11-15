"""Exercise the actual Lua script against an isolated Redis over a Unix socket."""
import shutil
import subprocess
import time
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
import redis

from public_limits import RedisRateLimits
from eye_test import create_app


@pytest.fixture
def redis_url(tmp_path):
    executable = shutil.which('redis-server')
    if not executable:
        pytest.skip('redis-server is required for Redis integration tests')
    temporary = tempfile.TemporaryDirectory(prefix='eye-redis-', dir='/tmp')
    socket = Path(temporary.name) / 'r.sock'
    process = subprocess.Popen([executable, '--port', '0', '--unixsocket', str(socket),
                                '--save', '', '--appendonly', 'no'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f'unix://{socket}'
    client = redis.Redis.from_url(url)
    try:
        for _ in range(100):
            try:
                if client.ping():
                    break
            except redis.RedisError:
                time.sleep(.05)
        else:
            pytest.fail('Redis did not start')
        yield url
    finally:
        process.terminate()
        process.wait(timeout=10)
        temporary.cleanup()


def test_replicas_share_atomic_budget_and_expire(redis_url):
    first, second = RedisRateLimits(redis_url), RedisRateLimits(redis_url)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda i: (first if i % 2 else second).take([('test', 5)]), range(20)))
    assert results.count(0) == 5
    assert 0 < first.client.ttl('{eye-test}:test') <= 61
    first.client.hset('{eye-test}:test', 'window', -1)
    assert second.take([('test', 5)]) == 0


def test_rejected_budget_does_not_consume_other_budgets(redis_url):
    limiter = RedisRateLimits(redis_url)
    assert limiter.take([('global', 1)]) == 0
    assert limiter.take([('browse', 10), ('global', 1)]) > 0
    assert not limiter.client.exists('{eye-test}:browse')


def test_cloud_requests_fail_closed_when_redis_is_down(tmp_path):
    app = create_app({'TESTING': True, 'REDIS_URL': f'unix://{tmp_path}/missing.sock'})
    client = app.test_client()
    assert client.get('/healthz').status_code == 200
    response = client.get('/api/players')
    assert response.status_code == 503
    assert response.headers['Retry-After'] == '5'
