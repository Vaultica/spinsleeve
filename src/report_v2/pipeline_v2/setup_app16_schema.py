"""
SpinSleeve APP-16 Schema Provisioning, Migration & Backfill.

Provisions two-tier album enrichment tables:
  1. `album_provider_ids` (Streaming ID to canonical_album_key bridge)
  2. `enrichment_raw_musicbrainz` (Append-only raw MusicBrainz data)
  3. `enrichment_raw_wikipedia` (Append-only raw Wikipedia data)
  4. `enrichment_raw_discogs` (Append-only raw Discogs data)
  5. Upgrades `album_enriched_metadata` (Adds canonical_album_key & APP-16 columns)
  6. Backfills all 2,170 existing records with APP-16 classifications and seeds raw tables.
"""

import os
import sys
import logging
from datetime import datetime
import pandas as pd
from google.cloud import bigquery

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from classifier import classify_album_metadata
from sync import compute_canonical_album_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("setup_app16_schema")

PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = os.environ.get("BQ_DATASET", "spotify_v2")


def provision_schema(bq_client):
    """Creates the raw source tables, bridge table, and adds columns to golden table."""
    logger.info("Provisioning APP-16 tables and schema in %s.%s...", PROJECT_ID, DATASET_V2)

    # 0. Create safety snapshot of existing golden table
    snapshot_sql = f"""
    CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata_backup_app16`
    CLONE `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata`;
    """
    logger.info("Creating safety backup clone: %s.%s.album_enriched_metadata_backup_app16", PROJECT_ID, DATASET_V2)
    bq_client.query(snapshot_sql).result()

    # 1. album_provider_ids
    provider_ids_sql = f"""
    CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET_V2}.album_provider_ids` (
        provider STRING NOT NULL,
        external_album_id STRING NOT NULL,
        canonical_album_key STRING NOT NULL,
        raw_album_name STRING,
        raw_artist_name STRING,
        updated_at TIMESTAMP NOT NULL
    )
    CLUSTER BY canonical_album_key, provider;
    """
    logger.info("Ensuring album_provider_ids table exists...")
    bq_client.query(provider_ids_sql).result()

    # 2. enrichment_raw_musicbrainz
    raw_mb_sql = f"""
    CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET_V2}.enrichment_raw_musicbrainz` (
        canonical_album_key STRING NOT NULL,
        fetched_at TIMESTAMP NOT NULL,
        extractor_version STRING,
        confidence_score FLOAT64,
        raw_payload JSON,
        musicbrainz_release_id STRING,
        mb_genres STRING,
        mb_tags STRING
    )
    PARTITION BY DATE(fetched_at)
    CLUSTER BY canonical_album_key;
    """
    logger.info("Ensuring enrichment_raw_musicbrainz table exists...")
    bq_client.query(raw_mb_sql).result()

    # 3. enrichment_raw_wikipedia
    raw_wiki_sql = f"""
    CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET_V2}.enrichment_raw_wikipedia` (
        canonical_album_key STRING NOT NULL,
        fetched_at TIMESTAMP NOT NULL,
        extractor_version STRING,
        confidence_score FLOAT64,
        raw_payload JSON,
        wiki_summary STRING,
        wiki_url STRING,
        pitchfork_score STRING,
        metacritic_score STRING,
        allmusic_score STRING,
        guardian_score STRING
    )
    PARTITION BY DATE(fetched_at)
    CLUSTER BY canonical_album_key;
    """
    logger.info("Ensuring enrichment_raw_wikipedia table exists...")
    bq_client.query(raw_wiki_sql).result()

    # 4. enrichment_raw_discogs
    raw_discogs_sql = f"""
    CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.{DATASET_V2}.enrichment_raw_discogs` (
        canonical_album_key STRING NOT NULL,
        fetched_at TIMESTAMP NOT NULL,
        extractor_version STRING,
        confidence_score FLOAT64,
        raw_payload JSON,
        discogs_release_id INT64,
        personnel STRING,
        discogs_rating FLOAT64,
        discogs_votes FLOAT64,
        discogs_styles STRING,
        discogs_notes STRING,
        discogs_url STRING
    )
    PARTITION BY DATE(fetched_at)
    CLUSTER BY canonical_album_key;
    """
    logger.info("Ensuring enrichment_raw_discogs table exists...")
    bq_client.query(raw_discogs_sql).result()

    # 5. Alter golden table to add APP-16 columns
    alter_golden_sql = f"""
    ALTER TABLE `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata`
    ADD COLUMN IF NOT EXISTS canonical_album_key STRING,
    ADD COLUMN IF NOT EXISTS macro_genre STRING,
    ADD COLUMN IF NOT EXISTS derived_moods ARRAY<STRING>,
    ADD COLUMN IF NOT EXISTS descriptive_tags ARRAY<STRING>,
    ADD COLUMN IF NOT EXISTS enrichment_quality_score FLOAT64,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
    """
    logger.info("Adding APP-16 columns to album_enriched_metadata...")
    bq_client.query(alter_golden_sql).result()
    logger.info("Schema provisioning completed successfully.")


def backfill_and_seed(bq_client):
    """
    Reads existing 2,170 rows from album_enriched_metadata:
    - Calculates canonical_album_key
    - Classifies macro_genre, derived_moods, descriptive_tags, enrichment_quality_score
    - Seeds album_provider_ids, enrichment_raw_wikipedia, enrichment_raw_discogs
    - Updates album_enriched_metadata with APP-16 columns
    """
    logger.info("Starting backfill of existing album_enriched_metadata...")
    fetch_q = f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata`
    """
    df = bq_client.query(fetch_q).to_dataframe()
    total_rows = len(df)
    logger.info("Loaded %d existing records for backfill and seeding.", total_rows)

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    provider_rows = []
    wiki_rows = []
    discogs_rows = []
    golden_updates = []

    for _, row in df.iterrows():
        album_id = str(row.get("album_id") or "")
        artist = str(row.get("artist_name") or "")
        album = str(row.get("album_name") or "")
        canon_key = compute_canonical_album_key(artist, album)

        # 1. Provider Bridge
        if album_id and canon_key:
            provider_rows.append({
                "provider": "spotify",
                "external_album_id": album_id,
                "canonical_album_key": canon_key,
                "raw_album_name": album,
                "raw_artist_name": artist,
                "updated_at": now
            })

        # 2. Raw Wikipedia
        wiki_summary = row.get("wiki_summary") or row.get("album_description") or ""
        wiki_url = row.get("wikipedia_url") or ""
        pf_score = str(row.get("pitchfork_score") or "")
        mc_score = str(row.get("metacritic_score") or "")
        am_score = str(row.get("allmusic_score") or "")
        g_score = str(row.get("guardian_score") or "")

        has_wiki = bool(wiki_summary or wiki_url or pf_score or mc_score or am_score or g_score)
        if has_wiki and canon_key:
            wiki_rows.append({
                "canonical_album_key": canon_key,
                "fetched_at": now,
                "extractor_version": "v1_legacy_seed",
                "confidence_score": 0.90,
                "raw_payload": None,
                "wiki_summary": str(wiki_summary),
                "wiki_url": str(wiki_url),
                "pitchfork_score": pf_score,
                "metacritic_score": mc_score,
                "allmusic_score": am_score,
                "guardian_score": g_score
            })

        # 3. Raw Discogs
        personnel = str(row.get("personnel") or "")
        disc_rat = row.get("discogs_rating")
        disc_votes = row.get("discogs_votes")
        disc_styles = str(row.get("styles") or "")
        disc_url = str(row.get("discogs_url") or "")
        has_discogs = bool(personnel or disc_rat or disc_styles or disc_url)

        if has_discogs and canon_key:
            discogs_rows.append({
                "canonical_album_key": canon_key,
                "fetched_at": now,
                "extractor_version": "v1_legacy_seed",
                "confidence_score": 0.90,
                "raw_payload": None,
                "discogs_release_id": None,
                "personnel": personnel,
                "discogs_rating": float(disc_rat) if disc_rat is not None and not pd.isna(disc_rat) else None,
                "discogs_votes": float(disc_votes) if disc_votes is not None and not pd.isna(disc_votes) else None,
                "discogs_styles": disc_styles,
                "discogs_notes": None,
                "discogs_url": disc_url
            })

        # 4. APP-16 Semantic Classification
        rec_for_classifier = {
            "genres": row.get("genres"),
            "styles": row.get("styles"),
            "album_description": wiki_summary,
            "pitchfork_score": pf_score,
            "metacritic_score": mc_score,
            "allmusic_score": am_score,
            "guardian_score": g_score,
            "personnel": personnel,
            "discogs_rating": disc_rat
        }
        cls_out = classify_album_metadata(rec_for_classifier)

        golden_updates.append({
            "album_id": album_id,
            "canonical_album_key": canon_key,
            "macro_genre": cls_out["macro_genre"],
            "derived_moods": cls_out["derived_moods"],
            "descriptive_tags": cls_out["descriptive_tags"],
            "enrichment_quality_score": cls_out["enrichment_quality_score"],
            "updated_at": now
        })

    # Seed album_provider_ids (skip if already seeded)
    existing_p_rows = bq_client.get_table(f"{PROJECT_ID}.{DATASET_V2}.album_provider_ids").num_rows
    if provider_rows and existing_p_rows == 0:
        p_table = f"{PROJECT_ID}.{DATASET_V2}.album_provider_ids"
        logger.info("Seeding %d rows into %s...", len(provider_rows), p_table)
        job = bq_client.load_table_from_json(provider_rows, p_table)
        job.result()
    else:
        logger.info("album_provider_ids already seeded with %d rows. Skipping.", existing_p_rows)

    # Seed enrichment_raw_wikipedia
    if wiki_rows:
        w_table = f"{PROJECT_ID}.{DATASET_V2}.enrichment_raw_wikipedia"
        logger.info("Seeding %d rows into %s via load_table_from_json...", len(wiki_rows), w_table)
        job = bq_client.load_table_from_json(wiki_rows, w_table)
        job.result()
        logger.info("Successfully seeded %s!", w_table)

    # Seed enrichment_raw_discogs
    if discogs_rows:
        d_table = f"{PROJECT_ID}.{DATASET_V2}.enrichment_raw_discogs"
        logger.info("Seeding %d rows into %s via load_table_from_json...", len(discogs_rows), d_table)
        job = bq_client.load_table_from_json(discogs_rows, d_table)
        job.result()
        logger.info("Successfully seeded %s!", d_table)

    # Update Golden Table
    logger.info("Updating %d golden records in album_enriched_metadata with APP-16 classifications...", len(golden_updates))
    staging_table = f"{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata_app16_staging"
    
    # Load into staging via load_table_from_json
    load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    job = bq_client.load_table_from_json(golden_updates, staging_table, job_config=load_cfg)
    job.result()

    merge_sql = f"""
    MERGE `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` T
    USING `{staging_table}` S
    ON T.album_id = S.album_id
    WHEN MATCHED THEN UPDATE SET
        T.canonical_album_key = S.canonical_album_key,
        T.macro_genre = S.macro_genre,
        T.derived_moods = S.derived_moods,
        T.descriptive_tags = S.descriptive_tags,
        T.enrichment_quality_score = S.enrichment_quality_score,
        T.updated_at = S.updated_at;
    """
    logger.info("Executing MERGE into album_enriched_metadata...")
    bq_client.query(merge_sql).result()

    # Drop staging table
    bq_client.delete_table(staging_table, not_found_ok=True)
    logger.info("Backfill and seeding completed successfully!")


if __name__ == "__main__":
    client = bigquery.Client(project=PROJECT_ID)
    provision_schema(client)
    backfill_and_seed(client)
