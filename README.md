# Eye Test

Standalone React/TypeScript player browser and Python API, extracted from CLIP's Players tab. Searches players, filters teams and play roles, paginates clips, and streams a bounded cut of the game film from S3. Uses the existing Neon schema (`players`, `teams`, `games`, `clips`, `clip_players`). No upload, job, or processing routes are exposed.

## Layout

- `frontend/`: the complete Eye Test React app and npm lockfile.
- `api/eye_test.py`: independent Flask app, read-only database access and public limits.
- `api/routes/players.py`: player search, clip metadata and playback.
- `api/generate_clips.py`, `api/services/`, `api/utils/`: local playback and labeling dependencies; no imports from CLIP.
- `scripts/`: imported matcher/persistence and attribute-backfill tools that populate player clips, plus launch/check scripts. These administrative tools are not included in the cloud image.
- `tests/unit/`: imported player, playback, public boundary, role, season, matcher provenance and persistence-guard tests, plus playback API regression coverage.
- `tests/db/`: original isolated PostgreSQL persistence tests and schema fixture.
- `tests/integration/`: actual Redis concurrency and failure tests.

The original operational uploader/downloader remains in CLIP. Shared processing helpers remain there because CLIP still uses them; Eye Test owns independent copies of everything it needs. No secret files, media, database contents, dependency symlinks or virtual environments were imported.

## Local development

Requires Python 3.10+, Node 22+, ffmpeg and ffprobe.

```sh
python3.10 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
npm --prefix frontend ci
cp .env.example .env
# Fill in the same Neon database and S3 bucket used by CLIP.
.venv/bin/python api/eye_test.py
```

In another terminal run `npm --prefix frontend run dev`. The UI is at http://localhost:5174 and proxies `/api` to port 5009. Credentials stay on the API; use your normal boto3 AWS profile locally. Keep `REDIS_URL` empty for local SQLite limits or point it at Redis.

```sh
bash scripts/check.sh
# Requires local PostgreSQL binaries (initdb, pg_ctl, psql); never connects to Neon:
.venv/bin/python -m pytest tests/db -q
```

Redis integration tests require `redis-server` (otherwise explicitly skipped). The tests create isolated local Redis and PostgreSQL instances. Unit tests need neither live Neon nor S3.

## Cloud deployment

```sh
docker build -t eyetest .
docker run --rm --env-file .env -p 8080:8080 eyetest
```

The multi-stage image builds React, installs ffmpeg, and starts Gunicorn as a non-root user. It serves both the UI and API on `PORT` (default 8080), so production needs no cross-origin browser configuration. `/healthz` is a process liveness endpoint, not a database readiness check. Without Docker, build the frontend and run `bash scripts/serve.sh`.

Configure these in the hosting service's secret/environment settings:

- `EYE_TEST_DATABASE_URL`: the existing Neon pooled URL, ideally with a SELECT-only role. Requests also enforce read-only transactions and an 8-second SQL timeout.
- `S3_BUCKET`, `AWS_REGION`: existing game storage. Assign an IAM role with `s3:GetObject` for the game-film prefix, or supply AWS credentials through your host's secret manager.
- `REDIS_URL`: **required for shared limits across multiple cloud replicas**, including TLS via `rediss://` where needed. Every replica must use the same Redis. Redis failure rejects API requests with 503 rather than bypassing limits. Empty uses SQLite, suitable only for one instance.
- `EYE_TEST_TRUSTED_PROXY_HOPS`: exact number of trusted forwarding proxies. Default 0 ignores forwarded client IPs. If enabled, restrict origin access to those proxies.
- `EYE_TEST_BROWSE_PER_MINUTE`, `EYE_TEST_PLAYBACK_PER_MINUTE`, `EYE_TEST_GLOBAL_PLAYBACK_PER_MINUTE`: defaults 120, 10 and 30. Limits use fixed minute windows; 429 responses include `Retry-After`.
- `PORT`, `WEB_CONCURRENCY`: default 8080 and 2 workers. Each playback can run ffprobe and ffmpeg; size CPU and worker count accordingly. Gunicorn timeout is 240 seconds; configure the ingress timeout to accommodate playback.

Playback still cuts on demand (maximum 120 seconds of film). This container needs a service that supports long requests, subprocesses and writable temporary storage. Rate limiting protects admission but does not replace CPU capacity planning or pre-generated media/CDN caching. No cloud resources are created by this repository.

## Administrative player-data scripts

Use the development dependencies and `PYTHONPATH=api:scripts`, for example:

```sh
PYTHONPATH=api:scripts .venv/bin/python scripts/backfill_clip_attributes.py --help
PYTHONPATH=api:scripts .venv/bin/python scripts/match_play_timestamps.py --help
```

Persistence retains CLIP's DEV/test target guards and source-provenance checks. These tools use `DATABASE_URL` and `APP_ENV`, separately from the public API's read-only URL. They are not a production migration mechanism; the existing Neon schema is reused without mutation by the API.
