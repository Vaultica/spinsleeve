"""
SpinSleeve V2 BigQuery Service Module (`services/bigquery.py`)
--------------------------------------------------------------
Manages BigQuery client connections, table materialization (INFRA-03a),
and robust safe data parsing helpers (safe_int, safe_float, safe_str).
"""
import pandas as pd
from google.cloud import bigquery
from config import PROJECT_ID, DATASET_V2, PLAYBACK_HISTORY_TABLE, logger


def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)


def rematerialize_user_albums_features(bq_client):
    """Materializes the dynamic user_albums_features view into a clustered physical table (INFRA-03a)."""
    logger.info("Materializing %s.user_albums_features_table...", DATASET_V2)
    remat_q = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
    CLUSTER BY user_id AS
    SELECT * FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features`
    """
    try:
        job = bq_client.query(remat_q)
        job.result()
        logger.info("Successfully refreshed %s.user_albums_features_table!", DATASET_V2)
    except Exception as e:
        logger.error("Error refreshing materialized user_albums_features_table: %s", e)


# ==============================================================================
# DATA CONVERTERS & SAFE PARSING (Zero NaN Guarantee)
# ==============================================================================
def safe_int(val, default=0):
    try:
        if pd.notna(val) and val is not None:
            return int(float(val))
    except Exception:
        pass
    return default


def safe_float(val, default=0.0):
    try:
        if pd.notna(val) and val is not None:
            return float(val)
    except Exception:
        pass
    return default


def safe_str(val, default=""):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return default
    s = str(val).strip()
    if s.lower() in ("nan", "none", "nat", "<na>"):
        return default
    return s
