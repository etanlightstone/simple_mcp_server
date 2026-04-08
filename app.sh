#!/usr/bin/env bash
PORT="${1:-8888}"
exec uvicorn main:app --host 0.0.0.0 --port "$PORT"
