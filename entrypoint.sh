#!/bin/bash
set -e

JOB_TYPE="${1:-sync}"
PARAM_TWO="${2:-100}"

echo "=== Starting SpinSleeve V2 Pipeline Runner [Job: $JOB_TYPE] ==="

if [ "$JOB_TYPE" = "enrich" ]; then
    echo "Running V2 Album Metadata Enrichment (Batch size: $PARAM_TWO)..."
    python src/pipeline_v2/enrich.py "$PARAM_TWO"
else
    python src/pipeline_v2/sync.py
fi

echo "=== SpinSleeve V2 Pipeline Runner Completed Successfully ==="
