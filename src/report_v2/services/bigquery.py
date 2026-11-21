"""
SpinSleeve V2 BigQuery Service Module (`services/bigquery.py`)
--------------------------------------------------------------
Manages BigQuery client connections, table materialization (INFRA-03a),
and robust safe data parsing helpers (safe_int, safe_float, safe_str).
"""
import pandas as pd
from google.cloud import bigquery
from app_config import PROJECT_ID, DATASET_V2, PLAYBACK_HISTORY_TABLE, logger


def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)


def rematerialize_user_albums_features(bq_client):
    """Materializes the dynamic user_albums_features view into a clustered physical table (INFRA-03a) with canonical album key deduplication."""
    logger.info("Materializing %s.user_albums_features_table...", DATASET_V2)
    remat_q = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
    CLUSTER BY user_id AS
    WITH album_plays_by_id AS (
      SELECT 
        user_id,
        album_id,
        COUNT(*) as track_plays_by_id,
        COUNTIF(played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)) as track_plays_by_id_30d
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
      WHERE album_id IS NOT NULL AND album_id != ""
      GROUP BY user_id, album_id
    ),
    album_plays_by_name AS (
      SELECT 
        user_id,
        LOWER(TRIM(album_name)) as norm_album_name,
        LOWER(TRIM(artist_name)) as norm_artist_name,
        COUNT(*) as track_plays_by_name,
        COUNTIF(played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)) as track_plays_by_name_30d
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
      GROUP BY user_id, norm_album_name, norm_artist_name
    ),
    raw_albums AS (
      SELECT 
        a.*,
        ROW_NUMBER() OVER(
          PARTITION BY a.user_id, CONCAT(
            LOWER(TRIM(a.artist_name)), 
            '::', 
            TRIM(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    LOWER(TRIM(a.album_name)),
                    r'\s*\((?:deluxe|remastered|anniversary|edition|version|reissue|expanded|collector|live|acoustic|mono|stereo|remix|archive collection|archive|super deluxe|remaster|ultimate edition)[^)]*\)',
                    ''
                  ),
                  r'\s*\[(?:deluxe|remastered|anniversary|edition|version|reissue|expanded|collector|live|acoustic|mono|stereo|remix|archive collection|archive|super deluxe|remaster|ultimate edition)[^\]]*\]',
                  ''
                ),
                r'\s*-\s*(?:deluxe|remastered|anniversary|edition|version|reissue|expanded|collector|live|acoustic|mono|stereo|remix|archive collection|archive|super deluxe|remaster).*$',
                ''
              )
            )
          )
          ORDER BY 
            CASE WHEN a.image_url IS NOT NULL AND a.image_url != "" THEN 1 ELSE 2 END ASC,
            a.added_at DESC
        ) as dedupe_rank
      FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` a
      WHERE COALESCE(a.tracks_total, 0) > 2
    ),
    deduped AS (
      SELECT * FROM raw_albums WHERE dedupe_rank = 1
    )
    SELECT 
      d.user_id,
      d.album_id,
      d.album_name,
      d.artist_name as album_artist_name,
      d.added_at,
      d.release_date as album_release_date,
      d.release_year,
      d.tracks_total as album_tracks_total,
      d.album_type,
      d.label as album_label,
      d.image_url as album_image_url,
      d.genres as album_genres,
      GREATEST(COALESCE(pid.track_plays_by_id, 0), COALESCE(pname.track_plays_by_name, 0)) as album_track_plays,
      ROUND(GREATEST(COALESCE(pid.track_plays_by_id, 0), COALESCE(pname.track_plays_by_name, 0)) / NULLIF(d.tracks_total, 0), 1) as album_plays,
      GREATEST(COALESCE(pid.track_plays_by_id_30d, 0), COALESCE(pname.track_plays_by_name_30d, 0)) as album_track_plays_30d,
      ROUND(GREATEST(COALESCE(pid.track_plays_by_id_30d, 0), COALESCE(pname.track_plays_by_name_30d, 0)) / NULLIF(d.tracks_total, 0), 1) as album_plays_30d,
      CONCAT("https://open.spotify.com/album/", d.album_id) as album_url,
      COALESCE(NULLIF(d.canonical_album_key, ''), CONCAT(LOWER(TRIM(d.artist_name)), '::', LOWER(TRIM(d.album_name)))) as canonical_album_key,
      e.pitchfork_score,
      e.metacritic_score,
      e.allmusic_score,
      e.discogs_rating,
      e.discogs_votes,
      e.album_description,
      e.personnel,
      e.wikipedia_url,
      e.discogs_url,
      e.styles as enriched_styles
    FROM deduped d
    LEFT JOIN album_plays_by_id pid
      ON d.user_id = pid.user_id AND d.album_id = pid.album_id
    LEFT JOIN album_plays_by_name pname
      ON d.user_id = pname.user_id 
      AND LOWER(TRIM(d.album_name)) = pname.norm_album_name
      AND LOWER(TRIM(d.artist_name)) = pname.norm_artist_name
    LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` e
      ON d.album_id = e.album_id
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
