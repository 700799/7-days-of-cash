#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
exec uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
