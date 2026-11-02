#!/bin/bash
set -e

JOB_TYPE="${1:-sync}"
PARAM_TWO="${2:-100}"

echo "=== Starting SpinSleeve Pipeline Runner [Job: $JOB_TYPE] ==="

if [ "$JOB_TYPE" = "enrich" ]; then
    echo "Running Album Metadata Enrichment (Batch size: $PARAM_TWO)..."
    python src/functions/enrich_metadata.py --batch "$PARAM_TWO"
else
    python src/functions/main.py "$JOB_TYPE"
fi

echo "=== SpinSleeve Pipeline Runner Completed Successfully ==="
