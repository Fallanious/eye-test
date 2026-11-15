#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/api${PYTHONPATH:+:$PYTHONPATH}"
exec .venv/bin/gunicorn --config gunicorn.conf.py 'eye_test:create_app()'
