#!/usr/bin/env python3
"""
SpinSleeve V2 Automated Multi-Tenant Pipeline Sync Runner.
Loops through all approved users in Google Cloud Datastore,
refreshes their Spotify tokens, ingests recent listening history and newly saved albums,
and updates BigQuery spotify_v2 tables.
"""

import os
import sys
import time
import json
import logging
import datetime
from google.cloud import bigquery, datastore, secretmanager, storage
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_pipeline_v2")

PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
BUCKET_NAME = os.environ.get("GCS_BUCKET", "secret-compass-181513")
DATASET_V2 = "spotify_v2"


def get_secret(secret_name, default=""):
    val = os.getenv(secret_name)
    if val:
        return val.strip()
    try:
        sm_client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        res = sm_client.access_secret_version(request={"name": path})
        return res.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.debug("Could not fetch secret %s: %s", secret_name, e)
        return default


SPOTIPY_CLIENT_ID = get_secret("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = get_secret("SPOTIPY_CLIENT_SECRET")


def upload_blob(bucket_name, blob_text, destination_blob_name):
    """Uploads a string as a blob to Google Cloud Storage."""
    try:
        storage_client = storage.Client(project=PROJECT_ID)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_string(blob_text, content_type="application/json")
        logger.info("Archived payload to gs://%s/%s", bucket_name, destination_blob_name)
    except Exception as e:
        logger.warning("Error uploading raw blob to GCS: %s", e)


def fetch_artist_genres(sp, artist_ids):
    """Fetches genres for unique artist IDs from Spotify in batches of 50."""
    artist_genres = {}
    unique_ids = [aid for aid in set(artist_ids) if aid]
    for i in range(0, len(unique_ids), 50):
        batch = unique_ids[i:i + 50]
        try:
            results = sp.artists(batch)
            for artist in results.get("artists", []):
                if artist and "id" in artist:
                    genres = artist.get("genres", [])
                    artist_genres[artist["id"]] = ", ".join(genres)
        except Exception as e:
            logger.warning("Error fetching artist genres: %s", e)
    return artist_genres


def sync_user_tracks(user_id, sp, bq_client):
    """Syncs recent track play history into spotify_v2.playback_history."""
    logger.info("[%s] Ingesting listening history...", user_id)

    # 1. Query latest play timestamp in BigQuery
    query = f"""
    SELECT MAX(played_at) as latest_play
    FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
    WHERE user_id = @user_id
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    df_latest = bq_client.query(query, job_config=job_config).to_dataframe()

    after_ms = None
    if not df_latest.empty and pd.notna(df_latest["latest_play"].iloc[0]):
        latest_ts = df_latest["latest_play"].iloc[0]
        # 10 minute lookback buffer for in-flight streams
        buffered = latest_ts - datetime.timedelta(minutes=10)
        after_ms = int(buffered.timestamp() * 1000)
        logger.info("[%s] Latest play in BQ: %s. Fetching after: %s (epoch ms: %d)", user_id, latest_ts, buffered, after_ms)
    else:
        logger.info("[%s] No prior plays found in BQ. Fetching last 50 tracks.", user_id)

    # 2. Query Spotify API
    if after_ms:
        recent = sp.current_user_recently_played(limit=50, after=after_ms)
    else:
        recent = sp.current_user_recently_played(limit=50)

    items = recent.get("items", [])
    if not items:
        logger.info("[%s] No new tracks returned by Spotify.", user_id)
        return 0

    # Archive raw JSON
    timestr = time.strftime("%Y%m%d_%H%M%S")
    folders = time.strftime("%Y/%m/%d")
    upload_blob(BUCKET_NAME, json.dumps(recent, indent=2), f"spotify_v2/{user_id}/{folders}/tracks_{timestr}.json")

    # 3. Format and deduplicate
    rows = []
    for item in items:
        track = item.get("track", {})
        alb = track.get("album", {})
        artists = track.get("artists", [])
        artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
        artist_id = artists[0].get("id", None) if artists else None
        rows.append({
            "user_id": user_id,
            "played_at": item.get("played_at"),
            "track_uri": track.get("uri"),
            "track_id": track.get("id"),
            "track_name": track.get("name"),
            "artist_id": artist_id,
            "artist_name": artist_name,
            "album_id": alb.get("id"),
            "album_name": alb.get("name")
        })

    df = pd.DataFrame(rows)
    df["played_at"] = pd.to_datetime(df["played_at"])

    # Deduplicate against existing (track_uri, played_at) in BQ for this window
    if after_ms:
        existing_q = f"""
        SELECT track_uri, played_at
        FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
        WHERE user_id = @user_id
          AND played_at >= TIMESTAMP_MILLIS(@after_ms)
        """
        existing_cfg = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("user_id", "STRING", user_id),
                bigquery.ScalarQueryParameter("after_ms", "INT64", after_ms)
            ]
        )
        df_existing = bq_client.query(existing_q, job_config=existing_cfg).to_dataframe()
        if not df_existing.empty:
            df_existing["played_at"] = pd.to_datetime(df_existing["played_at"])
            merged = pd.merge(df, df_existing, on=["track_uri", "played_at"], how="left", indicator=True)
            df = df[merged["_merge"] == "left_only"]

    if df.empty:
        logger.info("[%s] All %d fetched tracks were already recorded in BQ.", user_id, len(items))
        return 0

    table_ref = f"{PROJECT_ID}.{DATASET_V2}.playback_history"
    load_job = bq_client.load_table_from_dataframe(df, table_ref)
    load_job.result()
    logger.info("[%s] Successfully loaded %d new listening events into %s!", user_id, len(df), table_ref)
    return len(df)


def sync_user_saved_albums(user_id, sp, bq_client):
    """Syncs recently saved albums into spotify_v2.user_saved_albums."""
    logger.info("[%s] Ingesting saved albums...", user_id)

    # 1. Fetch recently saved albums (limit 50)
    saved = sp.current_user_saved_albums(limit=50)
    items = saved.get("items", [])
    if not items:
        logger.info("[%s] No saved albums found.", user_id)
        return 0

    timestr = time.strftime("%Y%m%d_%H%M%S")
    folders = time.strftime("%Y/%m/%d")
    upload_blob(BUCKET_NAME, json.dumps(saved, indent=2), f"spotify_v2/{user_id}/{folders}/recent_albums_{timestr}.json")

    # 2. Extract artist genres
    artist_ids = []
    for item in items:
        artists = item.get("album", {}).get("artists", [])
        if artists and "id" in artists[0]:
            artist_ids.append(artists[0]["id"])
    artist_genres_map = fetch_artist_genres(sp, artist_ids)

    # 3. Format DataFrame
    rows = []
    for item in items:
        alb = item.get("album", {})
        artists = alb.get("artists", [])
        artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
        artist_id = artists[0].get("id", None) if artists else None
        images = alb.get("images", [])
        image_url = images[0].get("url", None) if images else None
        rel_date = alb.get("release_date", "")
        rel_year = int(rel_date[:4]) if rel_date and rel_date[:4].isdigit() else None
        genres = artist_genres_map.get(artist_id, "")

        rows.append({
            "user_id": user_id,
            "album_id": alb.get("id"),
            "album_uri": alb.get("uri"),
            "album_name": alb.get("name"),
            "artist_id": artist_id,
            "artist_name": artist_name,
            "added_at": item.get("added_at"),
            "release_date": rel_date,
            "release_year": rel_year,
            "tracks_total": alb.get("total_tracks"),
            "album_type": alb.get("album_type"),
            "label": alb.get("label", ""),
            "image_url": image_url,
            "genres": genres
        })

    df = pd.DataFrame(rows)
    df["added_at"] = pd.to_datetime(df["added_at"])

    # 4. Check existing album_ids in BigQuery for this user
    existing_q = f"""
    SELECT DISTINCT album_id
    FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
    WHERE user_id = @user_id
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    df_existing = bq_client.query(existing_q, job_cfg).to_dataframe()
    existing_ids = set(df_existing["album_id"]) if not df_existing.empty else set()

    new_albums = df[~df["album_id"].isin(existing_ids)]

    if new_albums.empty:
        logger.info("[%s] All %d recent albums already exist in BQ user_saved_albums.", user_id, len(df))
        return 0

    table_ref = f"{PROJECT_ID}.{DATASET_V2}.user_saved_albums"
    load_job = bq_client.load_table_from_dataframe(new_albums, table_ref)
    load_job.result()
    logger.info("[%s] Successfully appended %d brand new albums into %s!", user_id, len(new_albums), table_ref)
    return len(new_albums)


def run_pipeline():
    logger.info("=== Starting SpinSleeve V2 Multi-Tenant Ingestion Pipeline ===")
    ds_client = datastore.Client(project=PROJECT_ID)
    bq_client = bigquery.Client(project=PROJECT_ID)

    # 1. Fetch all approved users with refresh tokens
    query = ds_client.query(kind="User")
    query.add_filter("is_approved", "=", True)
    approved_users = list(query.fetch())

    logger.info("Found %d approved users in Datastore.", len(approved_users))

    sp_oauth = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri="http://127.0.0.1:8080/callback"
    )

    total_new_tracks = 0
    total_new_albums = 0

    for user in approved_users:
        user_id = user.key.name or user.get("spotify_id")
        display_name = user.get("display_name", user_id)
        refresh_token = user.get("refresh_token")

        if not refresh_token:
            logger.warning("Skipping user '%s' (%s): No refresh token stored in Datastore.", user_id, display_name)
            continue

        logger.info("------------------------------------------------------------")
        logger.info("Processing user: %s (%s)", display_name, user_id)

        try:
            token_info = sp_oauth.refresh_access_token(refresh_token)
            sp = spotipy.Spotify(auth=token_info["access_token"])

            new_tracks = sync_user_tracks(user_id, sp, bq_client)
            new_albums = sync_user_saved_albums(user_id, sp, bq_client)

            total_new_tracks += new_tracks
            total_new_albums += new_albums

            user["last_sync_at"] = datetime.datetime.now(datetime.timezone.utc)
            user["sync_status"] = "idle"
            ds_client.put(user)

        except Exception as e:
            logger.error("Failed to sync user '%s': %s", user_id, e)
            try:
                user["sync_status"] = "error"
                ds_client.put(user)
            except Exception:
                pass

    logger.info("============================================================")
    logger.info("SpinSleeve V2 Ingestion Pipeline Run Finished.")
    logger.info("Summary: %d new tracks, %d new albums synced across %d users.", total_new_tracks, total_new_albums, len(approved_users))
    logger.info("============================================================")


if __name__ == "__main__":
    run_pipeline()
