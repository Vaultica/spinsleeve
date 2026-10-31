#!/bin/bash
set -e

JOB_TYPE="${1:-tracks}"

echo "=== Starting Spotify Data Pipeline [Job: $JOB_TYPE] ==="
python src/functions/main.py "$JOB_TYPE"

echo "=== Spotify Data Pipeline Completed Successfully ==="
