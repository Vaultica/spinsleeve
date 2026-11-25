"""
SpinSleeve Catalog Reclassification Script (`scripts/reclassify_catalog.py`)
----------------------------------------------------------------------------
Architectural Purpose:
Re-evaluates and updates macro-genre classifications in `album_enriched_metadata`
using the dominant-genre multi-vote engine, expanded sub-genre lexicon, and
hierarchical narrative description fallback.

Usage:
  # Simulate reclassification without writing to BigQuery (default)
  .venv/bin/python3 scripts/reclassify_catalog.py --dry-run

  # Apply updates to BigQuery and invalidate Datastore user catalog caches
  .venv/bin/python3 scripts/reclassify_catalog.py --execute --invalidate-cache
"""

import os
import sys
import argparse
import logging
from datetime import datetime
import pandas as pd
from google.cloud import bigquery, datastore

# Add src and report_v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from app_config import PROJECT_ID, DATASET_V2
from pipeline_v2.classifier import classify_album_metadata, classify_macro_genre

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reclassify_catalog")


def fetch_catalog_candidates(client: bigquery.Client, target_unclassified_only: bool = True) -> pd.DataFrame:
    """
    Fetches catalog albums from album_enriched_metadata alongside supplementary
    artist genres from user_saved_albums to maximize classification accuracy.
    """
    where_clause = "WHERE e.macro_genre IN ('Eclectic / Other', 'Other / Unclassified')" if target_unclassified_only else ""
    query = f"""
    WITH user_saved AS (
      SELECT 
        COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name)))) as canonical_album_key,
        STRING_AGG(DISTINCT genres, ', ') as saved_genres
      FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
      WHERE genres IS NOT NULL AND TRIM(genres) != ''
      GROUP BY canonical_album_key
    )
    SELECT 
      e.canonical_album_key,
      e.artist_name,
      e.album_name,
      e.macro_genre as current_macro_genre,
      COALESCE(NULLIF(e.genres, ''), s.saved_genres, '') as genres,
      COALESCE(e.styles, '') as styles,
      COALESCE(e.album_description, '') as album_description,
      e.pitchfork_score,
      e.metacritic_score,
      e.allmusic_score,
      e.guardian_score,
      e.personnel,
      e.discogs_rating
    FROM `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` e
    LEFT JOIN user_saved s ON e.canonical_album_key = s.canonical_album_key
    {where_clause}
    """
    return client.query(query).to_dataframe()


def reclassify_records(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes updated classifications for each candidate record.
    """
    updated_macro = []
    changed_flags = []

    for _, row in df.iterrows():
        rec = row.to_dict()
        cls_out = classify_album_metadata(rec)
        new_genre = cls_out["macro_genre"]
        old_genre = row["current_macro_genre"]

        updated_macro.append(new_genre)
        changed_flags.append(new_genre != old_genre)

    df["new_macro_genre"] = updated_macro
    df["has_changed"] = changed_flags
    return df


def execute_bigquery_updates(client: bigquery.Client, df_changed: pd.DataFrame, batch_size: int = 100) -> None:
    """
    Batches updates via BigQuery MERGE statements to safely update macro_genre.
    """
    target_table = f"`{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata`"
    total = len(df_changed)
    logger.info("Executing BigQuery MERGE updates for %d reclassified albums in batches of %d...", total, batch_size)

    for i in range(0, total, batch_size):
        batch = df_changed.iloc[i : i + batch_size]
        when_clauses = []
        keys = []
        for _, r in batch.iterrows():
            clean_key = str(r["canonical_album_key"]).replace("'", "\\'")
            clean_genre = str(r["new_macro_genre"]).replace("'", "\\'")
            when_clauses.append(f"WHEN canonical_album_key = '{clean_key}' THEN '{clean_genre}'")
            keys.append(f"'{clean_key}'")

        keys_str = ", ".join(keys)
        case_stmt = " ".join(when_clauses)
        update_sql = f"""
        UPDATE {target_table}
        SET 
          macro_genre = CASE {case_stmt} ELSE macro_genre END,
          updated_at = CURRENT_TIMESTAMP()
        WHERE canonical_album_key IN ({keys_str});
        """
        job = client.query(update_sql)
        job.result()
        logger.info("Updated batch %d-%d of %d.", i + 1, min(i + batch_size, total), total)


def invalidate_user_caches() -> None:
    """
    Invalidates Datastore UserCatalogCache entities so web views render fresh taxonomy.
    """
    ds_client = datastore.Client(project=PROJECT_ID)
    query = ds_client.query(kind="UserCatalogCache")
    keys = [e.key for e in query.fetch()]
    if keys:
        ds_client.delete_multi(keys)
        logger.info("Successfully invalidated %d Datastore UserCatalogCache entities.", len(keys))
    else:
        logger.info("No active UserCatalogCache entities found in Datastore.")


def main():
    parser = argparse.ArgumentParser(description="SpinSleeve Catalog Reclassification Utility")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Simulate reclassification without writing to BigQuery")
    parser.add_argument("--execute", action="store_true", default=False, help="Write reclassifications to BigQuery")
    parser.add_argument("--all", action="store_true", default=False, help="Re-evaluate all albums, not just Eclectic / Other")
    parser.add_argument("--invalidate-cache", action="store_true", default=False, help="Invalidate Datastore UserCatalogCache")
    args = parser.parse_args()

    # Dry-run is default unless --execute is explicitly specified
    is_dry_run = not args.execute

    logger.info("=== SpinSleeve Catalog Reclassification ===")
    logger.info("Mode: %s | Target: %s", "DRY-RUN (Simulation)" if is_dry_run else "EXECUTE (Live Update)", "ALL Albums" if args.all else "Unclassified Only")

    client = bigquery.Client(project=PROJECT_ID)
    df = fetch_catalog_candidates(client, target_unclassified_only=not args.all)
    logger.info("Fetched %d candidate albums for reclassification.", len(df))

    if df.empty:
        logger.info("No candidate albums found matching criteria.")
        return

    df_evaluated = reclassify_records(df)
    df_changed = df_evaluated[df_evaluated["has_changed"]].copy()

    logger.info("\n--- Reclassification Summary ---")
    logger.info("Total Candidates Evaluated: %d", len(df_evaluated))
    logger.info("Albums Successfully Reclassified: %d (%.1f%%)", len(df_changed), (len(df_changed) * 100.0 / len(df_evaluated)))
    logger.info("Albums Remaining Unclassified: %d", len(df_evaluated) - len(df_changed))

    logger.info("\n--- New Macro-Genre Distribution for Changed Albums ---")
    dist = df_changed["new_macro_genre"].value_counts()
    for genre, count in dist.items():
        logger.info("  %-22s : %3d albums", genre, count)

    logger.info("\n--- Sample 15 Reclassifications ---")
    sample = df_changed[["artist_name", "album_name", "current_macro_genre", "new_macro_genre"]].head(15)
    for _, r in sample.iterrows():
        logger.info("  %s — %s: %s -> %s", r["artist_name"], r["album_name"], r["current_macro_genre"], r["new_macro_genre"])

    if not is_dry_run:
        execute_bigquery_updates(client, df_changed)
        if args.invalidate_cache:
            invalidate_user_caches()
        logger.info("Catalog reclassification complete.")
    else:
        logger.info("\n[DRY RUN] No BigQuery updates were performed. Run with --execute to apply.")


if __name__ == "__main__":
    main()
