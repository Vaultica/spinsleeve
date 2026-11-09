"""
Batch QA Ingestion script for Spotify ZIP data export (`my_spotify_data.zip`).
Extracts and parses all Streaming_History_Audio_*.json files from the zip,
and loads them year-by-year into BigQuery table `spotify_v2.playback_history_qa`
to respect BigQuery's 4,000 partition DML modification limit.
"""

import argparse
import logging
import os
import sys
import zipfile
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

def batch_ingest_zip(zip_path, user_id):
    client = bigquery.Client(project=PROJECT_ID)
    ensure_qa_table(client)

    if not os.path.exists(zip_path):
        logger.error("ZIP file not found: %s", zip_path)
        return

    all_dfs = []
    logger.info("Opening ZIP archive: %s", zip_path)
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        for filename in z.namelist():
            if "Streaming_History_Audio_" in filename and filename.endswith(".json"):
                logger.info("Parsing audio history file from ZIP: %s", filename)
                with z.open(filename) as f:
                    df_file = parse_spotify_history_json(f, user_id)
                    if not df_file.empty:
                        all_dfs.append(df_file)
                        logger.info(" -> Parsed %d valid scrobbles from %s", len(df_file), filename)

    if not all_dfs:
        logger.warning("No audio history records found in zip.")
        return

    combined_df = pd.concat(all_dfs, ignore_index=True)
    logger.info("Total parsed valid scrobbles across all files: %d. Processing year-by-year...", len(combined_df))

    # Extract year for batching
    combined_df["year"] = combined_df["played_at"].dt.year
    years = sorted(combined_df["year"].unique())

    safe_uid = user_id.replace("-", "_")

    for yr in years:
        df_year = combined_df[combined_df["year"] == yr].drop(columns=["year"])
        if df_year.empty:
            continue

        logger.info("--- Ingesting Year %d (%d scrobbles) ---", yr, len(df_year))
        staging_table = f"{PROJECT_ID}.{DATASET_V2}.playback_history_staging_{safe_uid}_{yr}"

        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
        )
        load_job = client.load_table_from_dataframe(df_year, staging_table, job_config=job_config)
        load_job.result()

        # MERGE query for this year
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

        merge_job = client.query(merge_query)
        merge_job.result()

        # Clean up staging table
        client.delete_table(staging_table, not_found_ok=True)
        logger.info("Successfully merged year %d into QA table.", yr)

    logger.info("Successfully completed batch ZIP QA ingestion across all years for user %s!", user_id)

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
    parser = argparse.ArgumentParser(description="Batch Ingest Spotify ZIP Export into QA Table Year-by-Year")
    parser.add_argument("--zip", default="my_spotify_data.zip", help="Path to Spotify data export ZIP")
    parser.add_argument("--user-id", default="sergebou", help="Spotify User ID")
    args = parser.parse_args()

    batch_ingest_zip(args.zip, args.user_id)
