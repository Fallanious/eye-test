"""Eye Test: public, read-only player library API and React application."""
import os
import sqlite3
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask.json.provider import DefaultJSONProvider

from dataclass.base import Base as ModelBase
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from public_limits import RateLimits, RedisRateLimits, LimiterUnavailable
from routes.players import bp
from routes.teams import bp as teams_bp


def _origins(raw):
    return {item.strip().rstrip('/') for item in (raw or '').split(',') if item.strip()}


class ModelJSONProvider(DefaultJSONProvider):
    """Let jsonify turn a mapped dataclass into its column dictionary."""

    def default(self, o):
        if isinstance(o, ModelBase):
            return o.to_dict()
        return super().default(o)


def create_app(overrides=None):
    load_dotenv()
    dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
    app = Flask(__name__, static_folder=None)
    app.json = ModelJSONProvider(app)
    app.config.from_mapping(
        DATABASE_URL=os.getenv('DATABASE_URL'),
        DATABASE_URL_SQLALCHEMY=os.getenv('DATABASE_URL_SQLALCHEMY'),
        REDIS_URL=os.getenv('REDIS_URL', ''),
        RATE_LIMIT_PATH=os.getenv('EYE_TEST_RATE_LIMIT_PATH', '/tmp/eye-test-limits.sqlite3'),
        BROWSE_PER_MINUTE=int(os.getenv('EYE_TEST_BROWSE_PER_MINUTE', '120')),
        PLAYBACK_PER_MINUTE=int(os.getenv('EYE_TEST_PLAYBACK_PER_MINUTE', '10')),
        GLOBAL_PLAYBACK_PER_MINUTE=int(os.getenv('EYE_TEST_GLOBAL_PLAYBACK_PER_MINUTE', '30')),
        TRUSTED_PROXY_HOPS=int(os.getenv('EYE_TEST_TRUSTED_PROXY_HOPS', '0')),
        ALLOWED_ORIGINS=_origins(os.getenv('EYE_TEST_ALLOWED_ORIGINS', '')),
    )
    if overrides:
        app.config.update(overrides)
    for key in ('BROWSE_PER_MINUTE', 'PLAYBACK_PER_MINUTE', 'GLOBAL_PLAYBACK_PER_MINUTE'):
        if app.config[key] < 1:
            raise ValueError(f'{key} must be positive')
    hops = app.config['TRUSTED_PROXY_HOPS']
    if hops < 0:
        raise ValueError('TRUSTED_PROXY_HOPS must be nonnegative')
    if hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops)
    limiter = (RedisRateLimits(app.config['REDIS_URL']) if app.config['REDIS_URL']
               else RateLimits(app.config['RATE_LIMIT_PATH']))
    app.extensions['rate_limiter'] = limiter
    app.register_blueprint(bp)
    app.register_blueprint(teams_bp)

    @app.before_request
    def cors_preflight():
        if request.method != 'OPTIONS':
            return None
        origin = request.headers.get('Origin', '').rstrip('/')
        if origin not in app.config['ALLOWED_ORIGINS']:
            return None
        response = app.response_class('', status=204)
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Max-Age'] = '600'
        response.headers['Vary'] = 'Origin'
        return response

    @app.before_request
    def limit_requests():
        if not request.path.startswith('/api/'):
            return None
        identity = request.remote_addr or 'unknown'
        budgets = [(f'browse:{identity}', app.config['BROWSE_PER_MINUTE'])]
        if request.endpoint in ('players.serve_player_clip', 'teams.serve_game_clip'):
            budgets += [(f'play:{identity}', app.config['PLAYBACK_PER_MINUTE']),
                        ('play:global', app.config['GLOBAL_PLAYBACK_PER_MINUTE'])]
        try:
            retry = limiter.take(budgets)
        except (sqlite3.Error, LimiterUnavailable):
            return jsonify(error='Service temporarily unavailable.'), 503, {'Retry-After': '5'}
        if retry:
            return jsonify(error=f'Too many requests. Try again in {retry} seconds.'), 429, {'Retry-After': str(retry)}

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if response.status_code >= 400:
            response.headers['Cache-Control'] = 'no-store'
        origin = request.headers.get('Origin', '').rstrip('/')
        if origin in app.config['ALLOWED_ORIGINS']:
            response.headers['Access-Control-Allow-Origin'] = origin
            vary = [part.strip() for part in response.headers.get('Vary', '').split(',') if part.strip()]
            if 'Origin' not in vary:
                vary.append('Origin')
            response.headers['Vary'] = ', '.join(vary)
        return response

    @app.errorhandler(Exception)
    def errors(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.description), exc.code
        app.logger.error('Eye Test request failed (%s)', type(exc).__name__)
        return jsonify(error='Service temporarily unavailable.'), 503

    @app.get('/healthz')
    def health():
        return jsonify(status='ok')

    if (dist / 'index.html').is_file():
        @app.get('/')
        def index():
            return send_from_directory(dist, 'index.html')

        @app.get('/assets/<path:filename>')
        def assets(filename):
            return send_from_directory(dist / 'assets', filename)

    return app


if __name__ == '__main__':
    create_app().run(host=os.getenv('EYE_TEST_BIND_HOST', '127.0.0.1'),
                     port=int(os.getenv('EYE_TEST_PORT', '5009')), debug=False)
