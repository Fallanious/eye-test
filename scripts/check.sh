#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
.venv/bin/python -m pytest tests/unit tests/integration
npm --prefix frontend run build
npm --prefix frontend run lint
