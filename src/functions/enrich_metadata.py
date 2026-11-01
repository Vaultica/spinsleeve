#!/usr/bin/env python3
"""
SpinSleeve Album Metadata Enrichment Pipeline

Enriches albums in BigQuery with:
  1. Wikipedia: Album background story, executive summary, and critical ratings
     (Pitchfork, Metacritic, AllMusic, Rolling Stone, The Guardian).
  2. Discogs: Physical liner notes, personnel (musicians, producers, mixers,
     mastering engineers), vinyl styles, and community ratings.

Target BigQuery Table:
  spotify.album_enriched_metadata
"""

import os
import sys
import time
import urllib.parse
import re
import logging
from datetime import datetime
import requests
import pandas as pd
import pandas_gbq
from google.cloud import bigquery

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ID = os.getenv("GCP_PROJECT", "secret-compass-181513")
DATASET_NAME = os.getenv("BQ_DATASET", "spotify")
TARGET_TABLE = f"{DATASET_NAME}.album_enriched_metadata"

HEADERS_WIKI = {"User-Agent": "SpinSleeveEnrichment/1.0 (serge.bouschet@gmail.com)"}
HEADERS_DISCOGS = {"User-Agent": "SpinSleeveEnrichment/1.0 (serge.bouschet@gmail.com)"}


def clean_search_term(text):
    """Strips remaster labels, deluxe indicators, and special chars for clean search."""
    if not text:
        return ""
    text = re.sub(r"\(.*?remaster.*?\)", "", text, flags=re.I)
    text = re.sub(r"\(.*?deluxe.*?\)", "", text, flags=re.I)
    text = re.sub(r"\(.*?anniversary.*?\)", "", text, flags=re.I)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_wikipedia_data(artist, album):
    """
    Finds and extracts album prose description and critical reviews/scores
    from Wikipedia.
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
        "rolling_stone_score": None,
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
        res = requests.get(search_url, params=s_params, headers=HEADERS_WIKI, timeout=4).json()
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
            first_word = clean_album.lower().split()[0]
            for m in matches:
                t_low = m["title"].lower()
                if first_word in t_low and "discography" not in t_low:
                    top_title = m["title"]
                    break

        if not top_title:
            return data

        # Step 2: Fetch Summary Extract
        sum_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(top_title)}"
        sum_res = requests.get(sum_url, headers=HEADERS_WIKI, timeout=4).json()
        if "extract" in sum_res and "may refer to" not in sum_res["extract"]:
            data["wiki_summary"] = sum_res.get("extract")
            data["wiki_url"] = sum_res.get("content_urls", {}).get("desktop", {}).get("page")

        # Step 3: Parse Wikitext for Review Ratings
        parse_params = {
            "action": "parse",
            "page": top_title,
            "prop": "wikitext",
            "format": "json"
        }
        p_res = requests.get(search_url, params=parse_params, headers=HEADERS_WIKI, timeout=4).json()
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
        logger.debug("Wikipedia fetch error for %s - %s: %s", artist, album, e)

    return data


def fetch_discogs_data(artist, album):
    """
    Queries Discogs for liner notes, personnel (musicians, producers, mixers),
    styles, and community scores.
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
        r = requests.get(search_url, params=params, headers=HEADERS_DISCOGS, timeout=4).json()
        results = r.get("results", [])
        if not results:
            return data

        # Fetch release detail
        rel_id = results[0].get("id")
        data["discogs_url"] = f"https://www.discogs.com/release/{rel_id}"

        # Respect Discogs rate limit (1 req/s)
        time.sleep(1.0)
        rel_url = f"https://api.discogs.com/releases/{rel_id}"
        detail = requests.get(rel_url, headers=HEADERS_DISCOGS, timeout=4).json()

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
        if avg_score:
            data["discogs_rating"] = round(float(avg_score), 2)
            data["discogs_votes"] = int(votes) if votes else 0

        # Styles / Genres
        styles = detail.get("styles", []) or detail.get("genres", [])
        if styles:
            data["discogs_styles"] = ", ".join(styles[:6])

        # Notes
        notes = detail.get("notes")
        if notes:
            data["discogs_notes"] = notes.strip()

    except Exception as e:
        logger.debug("Discogs fetch error for %s - %s: %s", artist, album, e)

    return data


def table_exists(client, table_id):
    """Checks if a BigQuery table exists."""
    try:
        client.get_table(table_id)
        return True
    except Exception:
        return False


def get_stratified_sample(sample_per_era=5):
    """
    Selects a balanced, randomized sample across release eras and genres
    from BigQuery all_albums_features.
    """
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    WITH stratified AS (
      SELECT
        REGEXP_EXTRACT(album_url, r"album/([a-zA-Z0-9]+)") AS album_id,
        album_artist_name,
        album_name,
        album_release_date,
        album_genres,
        CASE
          WHEN SUBSTR(album_release_date, 1, 4) < "1990" THEN "Vintage (<1990)"
          WHEN SUBSTR(album_release_date, 1, 4) < "2010" THEN "90s & 2000s"
          WHEN SUBSTR(album_release_date, 1, 4) < "2020" THEN "2010s"
          ELSE "2020s"
        END AS era_group,
        ROW_NUMBER() OVER(
          PARTITION BY
            CASE
              WHEN SUBSTR(album_release_date, 1, 4) < "1990" THEN "Vintage (<1990)"
              WHEN SUBSTR(album_release_date, 1, 4) < "2010" THEN "90s & 2000s"
              WHEN SUBSTR(album_release_date, 1, 4) < "2020" THEN "2010s"
              ELSE "2020s"
            END
          ORDER BY RAND()
        ) AS rn
      FROM `{PROJECT_ID}.{DATASET_NAME}.all_albums_features`
      WHERE album_name IS NOT NULL
    )
    SELECT
      album_id,
      album_artist_name AS artist_name,
      album_name,
      album_release_date AS release_date,
      era_group,
      album_genres AS genres
    FROM stratified
    WHERE rn <= {sample_per_era}
    ORDER BY era_group, album_release_date
    """
    logger.info("Selecting stratified random sample from BigQuery (%d per era)...", sample_per_era)
    df = client.query(query).to_dataframe()
    return df


def get_albums_to_enrich(batch_limit=100, mode="incremental"):
    """
    Queries BigQuery for albums requiring enrichment.
    In incremental mode, excludes album_ids that already exist in target table,
    prioritizing your most-played and recently-added albums first.
    """
    client = bigquery.Client(project=PROJECT_ID)
    full_table_id = f"{PROJECT_ID}.{TARGET_TABLE}"

    if mode == "sample":
        return get_stratified_sample(sample_per_era=batch_limit)

    has_table = table_exists(client, full_table_id)

    if not has_table or mode == "all":
        exclude_clause = "WHERE album_name IS NOT NULL"
    else:
        exclude_clause = f"""
        WHERE album_name IS NOT NULL
          AND REGEXP_EXTRACT(album_url, r"album/([a-zA-Z0-9]+)") NOT IN (
            SELECT album_id FROM `{full_table_id}` WHERE album_id IS NOT NULL
          )
        """

    query = f"""
    SELECT
      REGEXP_EXTRACT(album_url, r"album/([a-zA-Z0-9]+)") AS album_id,
      album_artist_name AS artist_name,
      album_name,
      album_release_date AS release_date,
      CASE
        WHEN SUBSTR(album_release_date, 1, 4) < "1990" THEN "Vintage (<1990)"
        WHEN SUBSTR(album_release_date, 1, 4) < "2010" THEN "90s & 2000s"
        WHEN SUBSTR(album_release_date, 1, 4) < "2020" THEN "2010s"
        ELSE "2020s"
      END AS era_group,
      album_genres AS genres,
      album_plays
    FROM `{PROJECT_ID}.{DATASET_NAME}.all_albums_features`
    {exclude_clause}
    ORDER BY album_plays DESC, added_at DESC
    LIMIT {batch_limit}
    """
    logger.info("Querying BigQuery for next %d albums to enrich (Mode: %s)...", batch_limit, mode)
    df = client.query(query).to_dataframe()
    return df


def run_enrichment(batch_size=100, mode="incremental", write_to_bq=True):
    """
    Executes the metadata enrichment pipeline in batches.
    """
    logger.info("=== Starting SpinSleeve Metadata Enrichment Pipeline ===")
    logger.info("Configuration: Batch Size = %d, Mode = %s", batch_size, mode)

    client = bigquery.Client(project=PROJECT_ID)
    full_table_id = f"{PROJECT_ID}.{TARGET_TABLE}"
    table_already_exists = table_exists(client, full_table_id)

    target_df = get_albums_to_enrich(batch_limit=batch_size, mode=mode)
    total_records = len(target_df)

    if total_records == 0:
        logger.info("All albums in your library are already enriched! No work to do.")
        return pd.DataFrame()

    logger.info("Starting enrichment loop for %d albums...", total_records)
    enriched_records = []

    for idx, row in target_df.iterrows():
        album_id = row["album_id"]
        artist = row["artist_name"]
        album = row["album_name"]
        release_date = str(row["release_date"])
        year = release_date[:4] if release_date else ""
        era = row["era_group"]

        logger.info("[%d/%d] Enriching: %s - %s (%s)", idx + 1, total_records, artist, album, era)

        # 1. Fetch Wikipedia
        wiki_data = fetch_wikipedia_data(artist, album)

        # 2. Fetch Discogs
        discogs_data = fetch_discogs_data(artist, album)

        # Merge descriptions
        description = wiki_data["wiki_summary"]
        if not description and discogs_data["discogs_notes"]:
            description = discogs_data["discogs_notes"][:500]

        record = {
            "album_id": album_id,
            "artist_name": artist,
            "album_name": album,
            "release_date": release_date,
            "release_year": year,
            "era_group": era,
            "genres": row["genres"] or "",
            "styles": discogs_data["discogs_styles"] or "",
            "album_description": description or "",
            "personnel": discogs_data["personnel"] or "",
            "pitchfork_score": wiki_data["pitchfork_score"] or "",
            "metacritic_score": wiki_data["metacritic_score"] or "",
            "allmusic_score": wiki_data["allmusic_score"] or "",
            "guardian_score": wiki_data["guardian_score"] or "",
            "discogs_rating": discogs_data["discogs_rating"],
            "discogs_votes": discogs_data["discogs_votes"],
            "wikipedia_url": wiki_data["wiki_url"] or "",
            "discogs_url": discogs_data["discogs_url"] or "",
            "enriched_at": datetime.utcnow()
        }
        enriched_records.append(record)

    df_enriched = pd.DataFrame(enriched_records)

    if write_to_bq:
        if_exists_mode = "append" if table_already_exists and mode == "incremental" else "replace"
        logger.info("Writing %d enriched records to BigQuery (%s mode)...", len(df_enriched), if_exists_mode)
        pandas_gbq.to_gbq(
            df_enriched,
            TARGET_TABLE,
            project_id=PROJECT_ID,
            if_exists=if_exists_mode
        )
        logger.info("Successfully saved enriched records to BigQuery table %s!", TARGET_TABLE)

    logger.info("=== Metadata Enrichment Pipeline Complete ===")
    return df_enriched


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="SpinSleeve Metadata Enrichment")
    parser.add_argument("--batch", "-b", type=int, default=int(os.getenv("BATCH_SIZE", 100)), help="Batch size of albums to process")
    parser.add_argument("--mode", "-m", choices=["incremental", "sample", "all"], default=os.getenv("ENRICH_MODE", "incremental"), help="Execution mode")
    args = parser.parse_args()

    run_enrichment(batch_size=args.batch, mode=args.mode, write_to_bq=True)
