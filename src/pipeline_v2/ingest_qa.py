"""
QA Ingestion & Reconciliation script for Spotify historical scrobbles (APP-13).
Creates or uses `spotify_v2.playback_history_qa` table, parses streaming history JSON,
and merges records with deduplication.
"""

import argparse
import logging
import os
import sys
import pandas as pd
from google.cloud import bigquery

# Ensure src is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from pipeline_v2.history_parser import parse_spotify_history_json

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = "secret-compass-181513"
DATASET_V2 = "spotify_v2"
QA_TABLE = f"{PROJECT_ID}.{DATASET_V2}.playback_history_qa"

def ensure_qa_table(client):
    """Creates playback_history_qa table if it does not exist."""
    ddl = f"""
    CREATE TABLE IF NOT EXISTS `{QA_TABLE}` (
      user_id STRING NOT NULL,
      played_at TIMESTAMP NOT NULL,
      track_uri STRING,
      track_id STRING,
      track_name STRING,
      artist_id STRING,
      artist_name STRING,
      album_id STRING,
      album_name STRING
    )
    PARTITION BY DATE(played_at)
    CLUSTER BY user_id, artist_name;
    """
    logger.info("Ensuring QA table exists: %s", QA_TABLE)
    query_job = client.query(ddl)
    query_job.result()
    logger.info("QA table ready.")

def ingest_and_reconcile(json_file_path, user_id):
    """
    Parses JSON file, loads to staging table, and MERGEs into playback_history_qa with deduplication.
    """
    client = bigquery.Client(project=PROJECT_ID)
    ensure_qa_table(client)

    logger.info("Parsing JSON file: %s for user: %s", json_file_path, user_id)
    if not os.path.exists(json_file_path):
        logger.error("File not found: %s", json_file_path)
        return

    with open(json_file_path, "r", encoding="utf-8") as f:
        df = parse_spotify_history_json(f, user_id)

    if df.empty:
        logger.warning("No valid scrobbles found in %s after filtering.", json_file_path)
        return

    logger.info("Parsed %d valid scrobbles. Loading to BigQuery staging...", len(df))

    # Staging table name
    safe_uid = user_id.replace("-", "_")
    staging_table = f"{PROJECT_ID}.{DATASET_V2}.playback_history_staging_{safe_uid}"

    # Load dataframe to staging table
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    load_job = client.load_table_from_dataframe(df, staging_table, job_config=job_config)
    load_job.result()
    logger.info("Loaded staging table %s", staging_table)

    # MERGE query into QA table with deduplication
    merge_query = f"""
    MERGE `{QA_TABLE}` T
    USING `{staging_table}` S
    ON T.user_id = S.user_id
       AND T.played_at = S.played_at
       AND T.track_name = S.track_name
       AND T.artist_name = S.artist_name
    WHEN NOT MATCHED THEN
      INSERT (user_id, played_at, track_uri, track_id, track_name, artist_id, artist_name, album_id, album_name)
      VALUES (user_id, played_at, track_uri, track_id, track_name, artist_id, artist_name, album_id, album_name)
    """

    logger.info("Executing reconciliation MERGE into %s...", QA_TABLE)
    merge_job = client.query(merge_query)
    merge_job.result()

    # Clean up staging table
    client.delete_table(staging_table, not_found_ok=True)
    logger.info("Successfully completed QA ingestion and reconciliation for user %s!", user_id)

    # Query QA stats
    stats_query = f"""
    SELECT COUNT(*) as total_rows, MIN(played_at) as earliest_play, MAX(played_at) as latest_play
    FROM `{QA_TABLE}`
    WHERE user_id = @user_id
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    stats_res = client.query(stats_query, job_config=job_cfg).result()
    for row in stats_res:
        logger.info("QA Table Stats for %s -> Total Rows: %d, Earliest: %s, Latest: %s",
                    user_id, row.total_rows, row.earliest_play, row.latest_play)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Spotify History JSON into QA Table")
    parser.add_argument("--file", required=True, help="Path to Spotify Streaming History JSON file")
    parser.add_argument("--user-id", required=True, help="Spotify User ID")
    args = parser.parse_args()

    ingest_and_reconcile(args.file, args.user_id)
