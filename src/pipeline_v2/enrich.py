#!/usr/bin/env python3
"""
SpinSleeve V2 Album Metadata Enrichment Pipeline (APP-16).

Enriches albums in BigQuery (dataset: spotify_v2) via a two-tier architecture:
  Tier 1 (Raw Append-Only Sources):
    - `enrichment_raw_wikipedia`: Summaries, URLs, review ratings (Pitchfork, Metacritic, AllMusic, Guardian).
    - `enrichment_raw_discogs`: Liner notes, personnel, community ratings, styles.
    - `enrichment_raw_musicbrainz`: Canonical release group identifiers, genres, tags.
    - `album_provider_ids`: External streaming ID bridge (Spotify, Apple Music) to canonical_album_key.

  Tier 2 (Golden Synthesized Table):
    - `album_enriched_metadata`: Clustered by `canonical_album_key`, enriched with APP-16 semantic
      classification (`macro_genre`, `derived_moods`, `descriptive_tags`, `enrichment_quality_score`).
"""

import os
import sys
import time
import argparse
import urllib.parse
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import requests
import pandas as pd
from google.cloud import bigquery, datastore

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from classifier import classify_album_metadata
from sync import compute_canonical_album_key, rematerialize_user_albums_features

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_enrichment_v2")

PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = os.environ.get("BQ_DATASET", "spotify_v2")
TARGET_TABLE = f"{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata"

HEADERS_WIKI = {"User-Agent": "SpinSleeveEnrichment/2.0 (serge.bouschet@gmail.com)"}
HEADERS_DISCOGS = {"User-Agent": "SpinSleeveEnrichment/2.0 (serge.bouschet@gmail.com)"}
HEADERS_MB = {"User-Agent": "SpinSleeveEnrichment/2.0 (serge.bouschet@gmail.com)"}


def clean_search_term(text: Optional[str]) -> str:
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


def fetch_wikipedia_data(artist: str, album: str) -> Dict[str, Any]:
    """
    Finds and extracts album prose description and critical reviews/scores
    from Wikipedia MediaWiki API and REST summary endpoint.
    """
    clean_album = clean_search_term(album)
    clean_art = clean_search_term(artist)
    q = f"{clean_art} {clean_album} album"

    data: Dict[str, Any] = {
        "wiki_summary": None,
        "wiki_url": None,
        "pitchfork_score": None,
        "metacritic_score": None,
        "allmusic_score": None,
        "guardian_score": None,
    }

    try:
        # Step 1: Search Wikipedia for best matching page
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


def fetch_discogs_data(artist: str, album: str) -> Dict[str, Any]:
    """
    Queries Discogs for liner notes, personnel (musicians, producers, mixers),
    styles, and community scores with polite rate limiting.
    """
    clean_album = clean_search_term(album)
    clean_art = artist if "various" not in artist.lower() else ""

    data: Dict[str, Any] = {
        "discogs_release_id": None,
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

        rel_id = results[0].get("id")
        data["discogs_release_id"] = rel_id
        data["discogs_url"] = f"https://www.discogs.com/release/{rel_id}"

        # Respect Discogs rate limit (1 req/s)
        time.sleep(1.0)
        rel_url = f"https://api.discogs.com/releases/{rel_id}"
        detail = requests.get(rel_url, headers=HEADERS_DISCOGS, timeout=5).json()

        extra = detail.get("extraartists", [])
        personnel_list = []
        for p in extra[:20]:
            name = p.get("name")
            role = p.get("role")
            if name and role:
                personnel_list.append(f"{name} ({role})")

        if personnel_list:
            data["personnel"] = " • ".join(personnel_list)

        comm = detail.get("community", {})
        avg_score = comm.get("rating", {}).get("average")
        votes = comm.get("rating", {}).get("count")
        if avg_score is not None:
            data["discogs_rating"] = round(float(avg_score), 2)
            data["discogs_votes"] = float(votes) if votes else 0.0

        styles = detail.get("styles", []) or detail.get("genres", [])
        if styles:
            data["discogs_styles"] = ", ".join(styles[:6])

        notes = detail.get("notes")
        if notes:
            data["discogs_notes"] = notes.strip()

    except Exception as e:
        logger.debug("Discogs fetch exception for %s - %s: %s", artist, album, e)

    return data


def fetch_musicbrainz_data(artist: str, album: str) -> Dict[str, Any]:
    """
    Queries MusicBrainz API for release group tags, genres, and identifiers.
    """
    clean_album = clean_search_term(album)
    clean_art = clean_search_term(artist)
    data: Dict[str, Any] = {
        "musicbrainz_release_id": None,
        "mb_genres": None,
        "mb_tags": None,
    }
    if not clean_album or not clean_art:
        return data

    try:
        url = "https://musicbrainz.org/ws/2/release-group"
        query = f'artist:"{clean_art}" AND releasegroup:"{clean_album}"'
        params = {"query": query, "fmt": "json", "limit": 3}
        time.sleep(1.0)  # MusicBrainz rate limit
        res = requests.get(url, params=params, headers=HEADERS_MB, timeout=5).json()
        rgs = res.get("release-groups", [])
        if not rgs:
            return data

        best = rgs[0]
        data["musicbrainz_release_id"] = best.get("id")

        tags = [t.get("name") for t in best.get("tags", []) if t.get("name")]
        if tags:
            data["mb_tags"] = ", ".join(tags[:10])

        genres = [g.get("name") for g in best.get("genres", []) if g.get("name")]
        if genres:
            data["mb_genres"] = ", ".join(genres[:8])

    except Exception as e:
        logger.debug("MusicBrainz fetch exception for %s - %s: %s", artist, album, e)

    return data


def get_candidate_albums(
    bq_client: bigquery.Client,
    batch_limit: int = 50,
    specific_album_id: Optional[str] = None,
    re_enrich: bool = False,
    min_quality_score: float = 0.85
) -> pd.DataFrame:
    """
    Selects candidate albums from spotify_v2.user_saved_albums.
    - If specific_album_id is provided: targets that single album.
    - If re_enrich is False: targets only completely unenriched albums.
    - If re_enrich is True: targets unenriched albums, albums missing MusicBrainz tags,
      and albums with enrichment_quality_score < min_quality_score, prioritized by play count.
    """
    if specific_album_id:
        query = f"""
        SELECT 
          album_id,
          ANY_VALUE(artist_name) as artist_name,
          ANY_VALUE(album_name) as album_name,
          ANY_VALUE(canonical_album_key) as canonical_album_key,
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

    if not re_enrich:
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
            ANY_VALUE(canonical_album_key) as canonical_album_key,
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
          COALESCE(NULLIF(a.canonical_album_key, ''), CONCAT(LOWER(TRIM(a.artist_name)), '::', LOWER(TRIM(a.album_name)))) as canonical_album_key,
          a.release_date,
          a.release_year,
          a.genres,
          COALESCE(p.play_count, 0) as total_plays,
          a.collector_count
        FROM albums a
        LEFT JOIN plays p ON a.album_id = p.album_id
        LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` e 
          ON COALESCE(NULLIF(a.canonical_album_key, ''), CONCAT(LOWER(TRIM(a.artist_name)), '::', LOWER(TRIM(a.album_name)))) = e.canonical_album_key
        WHERE e.canonical_album_key IS NULL
          AND a.album_name IS NOT NULL
          AND a.artist_name IS NOT NULL
        ORDER BY total_plays DESC, a.collector_count DESC, a.release_date DESC
        LIMIT @batch_limit
        """
        job_cfg = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("batch_limit", "INT64", batch_limit)]
        )
        return bq_client.query(query, job_config=job_cfg).to_dataframe()

    # Re-Enrich Mode: targets albums missing MusicBrainz or with quality score < min_quality_score
    query = f"""
    WITH plays AS (
      SELECT album_id, COUNT(*) as play_count
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
      WHERE album_id IS NOT NULL AND album_id != ""
      GROUP BY album_id
    ),
    mb_scraped AS (
      SELECT DISTINCT canonical_album_key
      FROM `{PROJECT_ID}.{DATASET_V2}.enrichment_raw_musicbrainz`
      WHERE canonical_album_key IS NOT NULL AND canonical_album_key != ""
    ),
    albums AS (
      SELECT 
        album_id,
        ANY_VALUE(artist_name) as artist_name,
        ANY_VALUE(album_name) as album_name,
        ANY_VALUE(canonical_album_key) as canonical_album_key,
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
      COALESCE(NULLIF(a.canonical_album_key, ''), CONCAT(LOWER(TRIM(a.artist_name)), '::', LOWER(TRIM(a.album_name)))) as canonical_album_key,
      a.release_date,
      a.release_year,
      a.genres,
      COALESCE(p.play_count, 0) as total_plays,
      a.collector_count,
      e.enrichment_quality_score,
      (mb.canonical_album_key IS NOT NULL) as has_musicbrainz
    FROM albums a
    LEFT JOIN plays p ON a.album_id = p.album_id
    LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata` e 
      ON COALESCE(NULLIF(a.canonical_album_key, ''), CONCAT(LOWER(TRIM(a.artist_name)), '::', LOWER(TRIM(a.album_name)))) = e.canonical_album_key
    LEFT JOIN mb_scraped mb
      ON COALESCE(NULLIF(a.canonical_album_key, ''), CONCAT(LOWER(TRIM(a.artist_name)), '::', LOWER(TRIM(a.album_name)))) = mb.canonical_album_key
    WHERE (
        e.canonical_album_key IS NULL 
        OR mb.canonical_album_key IS NULL 
        OR COALESCE(e.enrichment_quality_score, 0.0) < @min_quality_score
      )
      AND a.album_name IS NOT NULL
      AND a.artist_name IS NOT NULL
    ORDER BY 
      CASE WHEN e.canonical_album_key IS NULL THEN 1 ELSE 2 END ASC,
      total_plays DESC,
      a.collector_count DESC,
      COALESCE(e.enrichment_quality_score, 0.0) ASC,
      a.release_date DESC
    LIMIT @batch_limit
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("batch_limit", "INT64", batch_limit),
            bigquery.ScalarQueryParameter("min_quality_score", "FLOAT64", min_quality_score)
        ]
    )
    return bq_client.query(query, job_config=job_cfg).to_dataframe()


def invalidate_all_user_caches():
    """Invalidates UserCatalogCache, PalCompatibilityCache, and UserAnalyticsCache across all users."""
    try:
        ds_client = datastore.Client(project=PROJECT_ID)
        for kind in ["UserCatalogCache", "PalCompatibilityCache", "UserAnalyticsCache"]:
            query = ds_client.query(kind=kind)
            keys = [entity.key for entity in query.fetch()]
            if keys:
                for i in range(0, len(keys), 500):
                    ds_client.delete_multi(keys[i:i + 500])
                logger.info("Invalidated %d entities from Datastore kind '%s'", len(keys), kind)
    except Exception as e:
        logger.warning("Error invalidating Datastore caches: %s", e)


def run_enrichment(
    batch_size: int = 50,
    specific_album_id: Optional[str] = None,
    dry_run: bool = False,
    re_enrich: bool = False,
    min_quality_score: float = 0.85
) -> int:
    """
    Runs the V2 metadata enrichment pipeline and appends records to BigQuery.
    """
    logger.info("=== Starting SpinSleeve V2 Album Metadata Enrichment ===")
    logger.info("Target Dataset: %s.%s | Batch Size: %d | Dry Run: %s | Re-Enrich: %s", PROJECT_ID, DATASET_V2, batch_size, dry_run, re_enrich)

    bq_client = bigquery.Client(project=PROJECT_ID)

    df_candidates = get_candidate_albums(
        bq_client,
        batch_limit=batch_size,
        specific_album_id=specific_album_id,
        re_enrich=re_enrich,
        min_quality_score=min_quality_score
    )
    total_to_enrich = len(df_candidates)

    if total_to_enrich == 0:
        logger.info("All albums in spotify_v2 are already enriched! Zero pending records.")
        return 0

    logger.info("Found %d candidate albums needing 12\" gatefold enrichment.", total_to_enrich)

    now_dt = datetime.utcnow()
    now_ts = now_dt.strftime("%Y-%m-%d %H:%M:%S")

    wiki_raw_records = []
    discogs_raw_records = []
    mb_raw_records = []
    provider_records = []
    golden_records = []

    for idx, row in df_candidates.iterrows():
        album_id = str(row["album_id"])
        artist = str(row.get("artist_name") or "Unknown Artist")
        album = str(row.get("album_name") or "Unknown Album")
        canon_key = compute_canonical_album_key(artist, album)
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

        # 3. Fetch MusicBrainz
        mb_data = fetch_musicbrainz_data(artist, album)

        # Merge descriptions
        description = wiki_data.get("wiki_summary")
        if not description and discogs_data.get("discogs_notes"):
            description = discogs_data["discogs_notes"][:500]

        # 4. APP-16 Semantic Classification
        rec_for_classifier = {
            "genres": row.get("genres"),
            "styles": discogs_data.get("discogs_styles"),
            "mb_tags": mb_data.get("mb_tags"),
            "album_description": description,
            "discogs_notes": discogs_data.get("discogs_notes"),
            "pitchfork_score": wiki_data.get("pitchfork_score"),
            "metacritic_score": wiki_data.get("metacritic_score"),
            "allmusic_score": wiki_data.get("allmusic_score"),
            "guardian_score": wiki_data.get("guardian_score"),
            "personnel": discogs_data.get("personnel"),
            "discogs_rating": discogs_data.get("discogs_rating")
        }
        cls_out = classify_album_metadata(rec_for_classifier)

        # Populate Raw Wikipedia record
        if wiki_data.get("wiki_summary") or wiki_data.get("wiki_url") or wiki_data.get("pitchfork_score"):
            wiki_raw_records.append({
                "canonical_album_key": canon_key,
                "fetched_at": now_ts,
                "extractor_version": "v2_live",
                "confidence_score": 0.95,
                "raw_payload": None,
                "wiki_summary": wiki_data.get("wiki_summary"),
                "wiki_url": wiki_data.get("wiki_url"),
                "pitchfork_score": wiki_data.get("pitchfork_score"),
                "metacritic_score": wiki_data.get("metacritic_score"),
                "allmusic_score": wiki_data.get("allmusic_score"),
                "guardian_score": wiki_data.get("guardian_score")
            })

        # Populate Raw Discogs record
        if discogs_data.get("personnel") or discogs_data.get("discogs_rating") or discogs_data.get("discogs_styles"):
            discogs_raw_records.append({
                "canonical_album_key": canon_key,
                "fetched_at": now_ts,
                "extractor_version": "v2_live",
                "confidence_score": 0.95,
                "raw_payload": None,
                "discogs_release_id": discogs_data.get("discogs_release_id"),
                "personnel": discogs_data.get("personnel"),
                "discogs_rating": discogs_data.get("discogs_rating"),
                "discogs_votes": discogs_data.get("discogs_votes"),
                "discogs_styles": discogs_data.get("discogs_styles"),
                "discogs_notes": discogs_data.get("discogs_notes"),
                "discogs_url": discogs_data.get("discogs_url")
            })

        # Populate Raw MusicBrainz record
        if mb_data.get("musicbrainz_release_id") or mb_data.get("mb_tags"):
            mb_raw_records.append({
                "canonical_album_key": canon_key,
                "fetched_at": now_ts,
                "extractor_version": "v2_live",
                "confidence_score": 0.95,
                "raw_payload": None,
                "musicbrainz_release_id": mb_data.get("musicbrainz_release_id"),
                "mb_genres": mb_data.get("mb_genres"),
                "mb_tags": mb_data.get("mb_tags")
            })

        # Populate Provider Bridge record
        provider_records.append({
            "provider": "spotify",
            "external_album_id": album_id,
            "canonical_album_key": canon_key,
            "raw_album_name": album,
            "raw_artist_name": artist,
            "updated_at": now_ts
        })

        # Populate Golden record
        golden_records.append({
            "album_id": album_id,
            "artist_name": artist,
            "album_name": album,
            "canonical_album_key": canon_key,
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
            "macro_genre": cls_out["macro_genre"],
            "derived_moods": cls_out["derived_moods"],
            "descriptive_tags": cls_out["descriptive_tags"],
            "enrichment_quality_score": cls_out["enrichment_quality_score"],
            "updated_at": now_ts
        })

    if dry_run:
        logger.info("[DRY RUN] Would synthesize %d records. Preview:\n%s", len(golden_records), golden_records[0])
        return len(golden_records)

    # 1. Ingest Raw Records
    if wiki_raw_records:
        w_table = f"{PROJECT_ID}.{DATASET_V2}.enrichment_raw_wikipedia"
        load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
        bq_client.load_table_from_json(wiki_raw_records, w_table, job_config=load_cfg).result()
        logger.info("Appended %d records into %s", len(wiki_raw_records), w_table)

    if discogs_raw_records:
        d_table = f"{PROJECT_ID}.{DATASET_V2}.enrichment_raw_discogs"
        load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
        bq_client.load_table_from_json(discogs_raw_records, d_table, job_config=load_cfg).result()
        logger.info("Appended %d records into %s", len(discogs_raw_records), d_table)

    if mb_raw_records:
        mb_table = f"{PROJECT_ID}.{DATASET_V2}.enrichment_raw_musicbrainz"
        load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
        bq_client.load_table_from_json(mb_raw_records, mb_table, job_config=load_cfg).result()
        logger.info("Appended %d records into %s", len(mb_raw_records), mb_table)

    if provider_records:
        p_table = f"{PROJECT_ID}.{DATASET_V2}.album_provider_ids"
        load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_APPEND)
        bq_client.load_table_from_json(provider_records, p_table, job_config=load_cfg).result()
        logger.info("Appended %d records into %s", len(provider_records), p_table)

    # 2. Merge into Golden Table
    staging_table = f"{PROJECT_ID}.{DATASET_V2}.album_enriched_metadata_staging"
    load_cfg = bigquery.LoadJobConfig(write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE)
    bq_client.load_table_from_json(golden_records, staging_table, job_config=load_cfg).result()

    merge_sql = f"""
    MERGE `{TARGET_TABLE}` T
    USING `{staging_table}` S
    ON T.canonical_album_key = S.canonical_album_key
    WHEN MATCHED THEN UPDATE SET
        T.album_id = S.album_id,
        T.artist_name = S.artist_name,
        T.album_name = S.album_name,
        T.release_date = CAST(S.release_date AS STRING),
        T.release_year = CAST(S.release_year AS STRING),
        T.era_group = S.era_group,
        T.genres = S.genres,
        T.styles = S.styles,
        T.album_description = COALESCE(NULLIF(S.album_description, ''), T.album_description),
        T.personnel = COALESCE(NULLIF(S.personnel, ''), T.personnel),
        T.pitchfork_score = COALESCE(NULLIF(S.pitchfork_score, ''), T.pitchfork_score),
        T.metacritic_score = COALESCE(NULLIF(S.metacritic_score, ''), T.metacritic_score),
        T.allmusic_score = COALESCE(NULLIF(S.allmusic_score, ''), T.allmusic_score),
        T.guardian_score = COALESCE(NULLIF(S.guardian_score, ''), T.guardian_score),
        T.discogs_rating = COALESCE(S.discogs_rating, T.discogs_rating),
        T.discogs_votes = COALESCE(S.discogs_votes, T.discogs_votes),
        T.wikipedia_url = COALESCE(NULLIF(S.wikipedia_url, ''), T.wikipedia_url),
        T.discogs_url = COALESCE(NULLIF(S.discogs_url, ''), T.discogs_url),
        T.macro_genre = S.macro_genre,
        T.derived_moods = S.derived_moods,
        T.descriptive_tags = S.descriptive_tags,
        T.enrichment_quality_score = S.enrichment_quality_score,
        T.updated_at = S.updated_at
    WHEN NOT MATCHED THEN INSERT (
        album_id, artist_name, album_name, canonical_album_key, release_date, release_year, era_group,
        genres, styles, album_description, personnel, pitchfork_score, metacritic_score, allmusic_score,
        guardian_score, discogs_rating, discogs_votes, wikipedia_url, discogs_url, macro_genre,
        derived_moods, descriptive_tags, enrichment_quality_score, updated_at
    ) VALUES (
        S.album_id, S.artist_name, S.album_name, S.canonical_album_key, CAST(S.release_date AS STRING), CAST(S.release_year AS STRING), S.era_group,
        S.genres, S.styles, S.album_description, S.personnel, S.pitchfork_score, S.metacritic_score, S.allmusic_score,
        S.guardian_score, S.discogs_rating, S.discogs_votes, S.wikipedia_url, S.discogs_url, S.macro_genre,
        S.derived_moods, S.descriptive_tags, S.enrichment_quality_score, S.updated_at
    );
    """
    bq_client.query(merge_sql).result()
    bq_client.delete_table(staging_table, not_found_ok=True)
    logger.info("Successfully merged %d golden records into %s!", len(golden_records), TARGET_TABLE)

    # 3. Re-materialize User Albums Features Table
    rematerialize_user_albums_features(bq_client)

    # 4. Invalidate Datastore Caches
    invalidate_all_user_caches()

    return len(golden_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpinSleeve V2 Album Metadata Enrichment Pipeline")
    parser.add_argument("positional_batch", nargs="?", type=int, default=None, help="Batch size (e.g., 50 or 100)")
    parser.add_argument("--batch-size", "-b", type=int, default=50, help="Number of albums to enrich (default: 50)")
    parser.add_argument("--album-id", type=str, default=None, help="Enrich a single specific Spotify album ID")
    parser.add_argument("--dry-run", action="store_true", help="Perform scraping without saving to BigQuery")
    parser.add_argument("--re-enrich", "-r", action="store_true", help="Re-enrich existing albums missing MusicBrainz or with quality score < min-score")
    parser.add_argument("--min-score", type=float, default=0.85, help="Minimum quality score threshold for re-enrichment (default: 0.85)")

    args = parser.parse_args()
    batch = args.positional_batch if args.positional_batch is not None else args.batch_size

    run_enrichment(
        batch_size=batch,
        specific_album_id=args.album_id,
        dry_run=args.dry_run,
        re_enrich=args.re_enrich,
        min_quality_score=args.min_score
    )
