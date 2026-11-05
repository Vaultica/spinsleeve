#!/usr/bin/env python3
"""
SpinSleeve V2 Album Metadata Enrichment Pipeline.

Enriches albums in BigQuery (dataset: spotify_v2) with:
  1. Wikipedia: Album narrative story, executive summary, and critical ratings
     (Pitchfork, Metacritic, AllMusic, The Guardian).
  2. Discogs: Physical liner notes, personnel (musicians, producers, mixers,
     mastering engineers), vinyl styles, and community ratings.

Target BigQuery Table:
  `secret-compass-181513.spotify_v2.album_enriched_metadata`
"""

import os
import sys
import time
import argparse
import urllib.parse
import re
import logging
from datetime import datetime
import requests
import pandas as pd
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_enrichment_v2")

PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = os.environ.get("BQ_DATASET", "spotify_v2")
TARGET_TABLE = f"{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata"

HEADERS_WIKI = {"User-Agent": "SpinSleeveEnrichment/2.0 (serge.bouschet@gmail.com)"}
HEADERS_DISCOGS = {"User-Agent": "SpinSleeveEnrichment/2.0 (serge.bouschet@gmail.com)"}


def clean_search_term(text):
    """Strips remaster labels, deluxe indicators, and special chars for clean search."""
    if not text:
        return ""
    text = re.sub(r"\(.*?remaster.*?\)", "", text, flags=re.I)
    text = re.sub(r"\(.*?deluxe.*?\)", "", text, flags=re.I)
    text = re.sub(r"\(.*?anniversary.*?\)", "", text, flags=re.I)
    text = re.sub(r"\(.*?edition.*?\)", "", text, flags=re.I)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_wikipedia_data(artist, album):
    """
    Finds and extracts album prose description and critical reviews/scores
    from Wikipedia MediaWiki API and REST summary endpoint.
    """
    clean_album = clean_search_term(album)
    clean_art = clean_search_term(artist)
    q = f"{clean_art} {clean_album} album"

    data = {
        "wiki_summary": None,
        "wiki_url": None,
        "pitchfork_score": None,
        "metacritic_score": None,
        "allmusic_score": None,
        "guardian_score": None,
    }

    try:
        # Step 1: Search Wikipedia for the best matching page
        search_url = "https://en.wikipedia.org/w/api.php"
        s_params = {
            "action": "query",
            "list": "search",
            "srsearch": q,
            "format": "json"
        }
        res = requests.get(search_url, params=s_params, headers=HEADERS_WIKI, timeout=5).json()
        matches = res.get("query", {}).get("search", [])
        if not matches:
            return data

        # Select best page prioritizing exact album title matches
        top_title = None
        for m in matches:
            t_low = m["title"].lower()
            if clean_album.lower() in t_low and "discography" not in t_low:
                top_title = m["title"]
                break
        if not top_title and matches:
            first_word = clean_album.lower().split()[0] if clean_album else ""
            for m in matches:
                t_low = m["title"].lower()
                if first_word and first_word in t_low and "discography" not in t_low:
                    top_title = m["title"]
                    break

        if not top_title:
            return data

        # Step 2: Fetch Summary Extract
        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title)}"
        sum_res = requests.get(sum_url, headers=HEADERS_WIKI, timeout=5).json()
        if "extract" in sum_res and "may refer to" not in sum_res.get("extract", ""):
            data["wiki_summary"] = sum_res.get("extract")
            data["wiki_url"] = sum_res.get("content_urls", {}).get("desktop", {}).get("page")

        # Step 3: Parse Wikitext for Review Ratings
        parse_params = {
            "action": "parse",
            "page": top_title,
            "prop": "wikitext",
            "format": "json"
        }
        p_res = requests.get(search_url, params=parse_params, headers=HEADERS_WIKI, timeout=5).json()
        wikitext = p_res.get("parse", {}).get("wikitext", {}).get("*", "")

        # Extract Metacritic
        m_mc = re.search(r"\|\s*MC\s*=\s*(\d+/\d+|\d+)", wikitext, re.I)
        if m_mc:
            val = m_mc.group(1).strip()
            data["metacritic_score"] = val if "/" in val else f"{val}/100"

        # Extract Pitchfork
        m_pf = re.search(r"\|\s*rev(\d+)\s*=\s*.*Pitchfork", wikitext, re.I)
        if m_pf:
            num = m_pf.group(1)
            m_score = re.search(rf"\|\s*rev{num}score\s*=\s*([^\n<{{|]+)", wikitext)
            if m_score:
                s_val = m_score.group(1).strip()
                data["pitchfork_score"] = s_val if "/" in s_val else f"{s_val}/10"

        # Extract AllMusic
        m_am = re.search(r"\|\s*rev(\d+)\s*=\s*.*AllMusic", wikitext, re.I)
        if m_am:
            num = m_am.group(1)
            m_score = re.search(rf"\|\s*rev{num}score\s*=\s*(?:\{{\{{Rating\|)?([\d\.]+)(?:\|(\d+)\}}\}})?", wikitext)
            if m_score:
                s1 = m_score.group(1)
                s2 = m_score.group(2) or "5"
                data["allmusic_score"] = f"{s1}/{s2}"

        # Extract Guardian
        m_g = re.search(r"\|\s*rev(\d+)\s*=\s*.*Guardian", wikitext, re.I)
        if m_g:
            num = m_g.group(1)
            m_score = re.search(rf"\|\s*rev{num}score\s*=\s*(?:\{{\{{Rating\|)?([\d\.]+)(?:\|(\d+)\}}\}})?", wikitext)
            if m_score:
                data["guardian_score"] = f"{m_score.group(1)}/5"

    except Exception as e:
        logger.debug("Wikipedia fetch exception for %s - %s: %s", artist, album, e)

    return data


def fetch_discogs_data(artist, album):
    """
    Queries Discogs for liner notes, personnel (musicians, producers, mixers),
    styles, and community scores with polite rate limiting.
    """
    clean_album = clean_search_term(album)
    clean_art = artist if "various" not in artist.lower() else ""

    data = {
        "discogs_url": None,
        "discogs_rating": None,
        "discogs_votes": None,
        "discogs_styles": None,
        "personnel": None,
        "discogs_notes": None,
    }

    try:
        search_url = "https://api.discogs.com/database/search"
        params = {"release_title": clean_album, "artist": clean_art, "type": "release"}
        r = requests.get(search_url, params=params, headers=HEADERS_DISCOGS, timeout=5).json()
        results = r.get("results", [])
        if not results:
            return data

        # Fetch release detail
        rel_id = results[0].get("id")
        data["discogs_url"] = f"https://www.discogs.com/release/{rel_id}"

        # Respect Discogs rate limit (1 req/s)
        time.sleep(1.0)
        rel_url = f"https://api.discogs.com/releases/{rel_id}"
        detail = requests.get(rel_url, headers=HEADERS_DISCOGS, timeout=5).json()

        # Extract Personnel credits
        extra = detail.get("extraartists", [])
        personnel_list = []
        for p in extra[:20]:
            name = p.get("name")
            role = p.get("role")
            if name and role:
                personnel_list.append(f"{name} ({role})")

        if personnel_list:
            data["personnel"] = " • ".join(personnel_list)

        # Community Ratings
        comm = detail.get("community", {})
        avg_score = comm.get("rating", {}).get("average")
        votes = comm.get("rating", {}).get("count")
        if avg_score is not None:
            data["discogs_rating"] = round(float(avg_score), 2)
            data["discogs_votes"] = float(votes) if votes else 0.0

        # Styles / Genres
        styles = detail.get("styles", []) or detail.get("genres", [])
        if styles:
            data["discogs_styles"] = ", ".join(styles[:6])

        # Notes
        notes = detail.get("notes")
        if notes:
            data["discogs_notes"] = notes.strip()

    except Exception as e:
        logger.debug("Discogs fetch exception for %s - %s: %s", artist, album, e)

    return data


def get_candidate_albums(bq_client, batch_limit=50, specific_album_id=None):
    """
    Selects unenriched albums from spotify_v2.user_saved_albums prioritized by:
    1. Total track plays across all tenants in playback_history
    2. Number of users who saved the album
    3. Most recent release date
    """
    if specific_album_id:
        query = f"""
        SELECT 
          album_id,
          ANY_VALUE(artist_name) as artist_name,
          ANY_VALUE(album_name) as album_name,
          ANY_VALUE(release_date) as release_date,
          ANY_VALUE(release_year) as release_year,
          ANY_VALUE(genres) as genres,
          0 as total_plays
        FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
        WHERE album_id = @album_id
        GROUP BY album_id
        """
        job_cfg = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("album_id", "STRING", specific_album_id)]
        )
        return bq_client.query(query, job_config=job_cfg).to_dataframe()

    query = f"""
    WITH plays AS (
      SELECT album_id, COUNT(*) as play_count
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
      WHERE album_id IS NOT NULL AND album_id != ""
      GROUP BY album_id
    ),
    albums AS (
      SELECT 
        album_id,
        ANY_VALUE(artist_name) as artist_name,
        ANY_VALUE(album_name) as album_name,
        ANY_VALUE(release_date) as release_date,
        ANY_VALUE(release_year) as release_year,
        ANY_VALUE(genres) as genres,
        COUNT(DISTINCT user_id) as collector_count
      FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
      GROUP BY album_id
    )
    SELECT 
      a.album_id,
      a.artist_name,
      a.album_name,
      a.release_date,
      a.release_year,
      a.genres,
      COALESCE(p.play_count, 0) as total_plays,
      a.collector_count
    FROM albums a
    LEFT JOIN plays p ON a.album_id = p.album_id
    LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` e ON a.album_id = e.album_id
    WHERE e.album_id IS NULL
      AND a.album_name IS NOT NULL
      AND a.artist_name IS NOT NULL
    ORDER BY total_plays DESC, a.collector_count DESC, a.release_date DESC
    LIMIT @batch_limit
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("batch_limit", "INT64", batch_limit)]
    )
    return bq_client.query(query, job_config=job_cfg).to_dataframe()


def run_enrichment(batch_size=50, specific_album_id=None, dry_run=False):
    """
    Runs the V2 metadata enrichment pipeline and appends records to BigQuery.
    """
    logger.info("=== Starting SpinSleeve V2 Album Metadata Enrichment ===")
    logger.info("Target Dataset: %s.%s | Batch Size: %d | Dry Run: %s", PROJECT_ID, DATASET_V2, batch_size, dry_run)

    bq_client = bigquery.Client(project=PROJECT_ID)

    df_candidates = get_candidate_albums(bq_client, batch_limit=batch_size, specific_album_id=specific_album_id)
    total_to_enrich = len(df_candidates)

    if total_to_enrich == 0:
        logger.info("All albums in spotify_v2 are already enriched! Zero pending records.")
        return 0

    logger.info("Found %d candidate albums needing 12\" gatefold enrichment.", total_to_enrich)

    enriched_records = []
    for idx, row in df_candidates.iterrows():
        album_id = row["album_id"]
        artist = row.get("artist_name", "Unknown Artist")
        album = row.get("album_name", "Unknown Album")
        rel_date = str(row.get("release_date") or "")
        rel_year = str(row.get("release_year") or (rel_date[:4] if len(rel_date) >= 4 else ""))

        # Compute era group
        if rel_year and rel_year.isdigit():
            y_int = int(rel_year)
            if y_int < 1990:
                era_group = "Vintage (<1990)"
            elif y_int < 2010:
                era_group = "90s & 2000s"
            elif y_int < 2020:
                era_group = "2010s"
            else:
                era_group = "2020s"
        else:
            era_group = "Unknown"

        logger.info("[%d/%d] Enriching: %s — %s (%s, %s plays)", idx + 1, total_to_enrich, artist, album, rel_year, row.get("total_plays", 0))

        # 1. Fetch Wikipedia
        wiki_data = fetch_wikipedia_data(artist, album)

        # 2. Fetch Discogs
        discogs_data = fetch_discogs_data(artist, album)

        # Merge descriptions
        description = wiki_data.get("wiki_summary")
        if not description and discogs_data.get("discogs_notes"):
            description = discogs_data["discogs_notes"][:500]

        record = {
            "album_id": str(album_id),
            "artist_name": str(artist),
            "album_name": str(album),
            "release_date": rel_date,
            "release_year": rel_year,
            "era_group": era_group,
            "genres": str(row.get("genres") or ""),
            "styles": str(discogs_data.get("discogs_styles") or ""),
            "album_description": str(description or ""),
            "personnel": str(discogs_data.get("personnel") or ""),
            "pitchfork_score": str(wiki_data.get("pitchfork_score") or ""),
            "metacritic_score": str(wiki_data.get("metacritic_score") or ""),
            "allmusic_score": str(wiki_data.get("allmusic_score") or ""),
            "guardian_score": str(wiki_data.get("guardian_score") or ""),
            "discogs_rating": discogs_data.get("discogs_rating"),
            "discogs_votes": discogs_data.get("discogs_votes"),
            "wikipedia_url": str(wiki_data.get("wiki_url") or ""),
            "discogs_url": str(discogs_data.get("discogs_url") or ""),
            "enriched_at": datetime.utcnow()
        }
        enriched_records.append(record)

    df_out = pd.DataFrame(enriched_records)

    if dry_run:
        logger.info("[DRY RUN] Would append %d records to %s. First row preview:\n%s", len(df_out), TARGET_TABLE, df_out.iloc[0].to_dict())
        return len(df_out)

    # BigQuery Table schema alignment
    schema = [
        bigquery.SchemaField("album_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("artist_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("album_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("release_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("release_year", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("era_group", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("genres", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("styles", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("album_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("personnel", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitchfork_score", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("metacritic_score", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("allmusic_score", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("guardian_score", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discogs_rating", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("discogs_votes", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("wikipedia_url", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("discogs_url", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("enriched_at", "DATETIME", mode="NULLABLE"),
    ]

    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )

    logger.info("Appending %d enriched album records into BigQuery table %s...", len(df_out), TARGET_TABLE)
    load_job = bq_client.load_table_from_dataframe(df_out, TARGET_TABLE, job_config=job_config)
    load_job.result()
    logger.info("Successfully enriched and appended %d albums into %s!", len(df_out), TARGET_TABLE)
    return len(df_out)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpinSleeve V2 Album Metadata Enrichment Pipeline")
    parser.add_argument("positional_batch", nargs="?", type=int, default=None, help="Batch size (e.g., 50 or 100)")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Number of albums to enrich (default: 50)")
    parser.add_argument("--album-id", type=str, default=None, help="Enrich a single specific Spotify album ID")
    parser.add_argument("--dry-run", action="store_true", help="Perform scraping without saving to BigQuery")

    args = parser.parse_args()
    batch = args.positional_batch if args.positional_batch is not None else args.batch_size

    run_enrichment(batch_size=batch, specific_album_id=args.album_id, dry_run=args.dry_run)
