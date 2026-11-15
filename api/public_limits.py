"""Atomic fixed-window limits shared by API workers on one host."""
import math
import sqlite3
import time


class RateLimits:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as conn:
            conn.execute('CREATE TABLE IF NOT EXISTS limits (key TEXT PRIMARY KEY, window INTEGER, count INTEGER)')

    def take(self, budgets, now=None):
        now = time.time() if now is None else now
        window = int(now // 60)
        with sqlite3.connect(self.path, timeout=2) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM limits WHERE window < ?', (window,))
            for key, limit in budgets:
                row = conn.execute('SELECT count FROM limits WHERE key = ?', (key,)).fetchone()
                if row and row[0] >= limit:
                    return max(1, math.ceil((window + 1) * 60 - now))
            for key, _ in budgets:
                conn.execute('INSERT INTO limits VALUES (?, ?, 1) ON CONFLICT(key) DO UPDATE SET count = count + 1', (key, window))
        return 0


class LimiterUnavailable(Exception):
    """The shared limiter cannot safely accept a request."""


class RedisRateLimits:
    """One atomic budget check across all workers and replicas, using Redis time."""

    SCRIPT = """
    local now = tonumber(redis.call('TIME')[1])
    local window = math.floor(now / 60)
    local retry = (window + 1) * 60 - now
    for i, key in ipairs(KEYS) do
        local stored = redis.call('HMGET', key, 'window', 'count')
        if tonumber(stored[1]) == window and tonumber(stored[2]) >= tonumber(ARGV[i]) then
            return retry
        end
    end
    for i, key in ipairs(KEYS) do
        local previous = redis.call('HGET', key, 'window')
        if tonumber(previous) ~= window then
            redis.call('HSET', key, 'window', window, 'count', 0)
        end
        redis.call('HINCRBY', key, 'count', 1)
        redis.call('EXPIRE', key, retry + 1)
    end
    return 0
    """

    def __init__(self, url):
        import redis
        self.client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        self.script = self.client.register_script(self.SCRIPT)

    def take(self, budgets):
        from redis.exceptions import RedisError
        try:
            # Hash tag keeps the entire atomic operation in one Redis Cluster slot.
            return int(self.script(keys=[f'{{eye-test}}:{key}' for key, _ in budgets],
                                   args=[limit for _, limit in budgets]))
        except RedisError as exc:
            raise LimiterUnavailable() from exc
