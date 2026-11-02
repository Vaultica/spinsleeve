# Copyright 2026 Google LLC / Serge Bouschet
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
import json
import logging
import pandas as pd
import pandas_gbq

from google.cloud import storage
from google.cloud import bigquery
import functions_framework

import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Project configuration with environment overrides
PROJECT_ID = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", "secret-compass-181513"))
BUCKET_NAME = os.getenv("GCS_BUCKET", "secret-compass-181513")
DATASET_NAME = os.getenv("BQ_DATASET", "spotify")


def get_secret(secret_name, default=None):
    """
    Retrieves secret from environment variable, falling back to Secret Manager
    if running in GCP.
    """
    val = os.getenv(secret_name)
    if val:
        return val
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.debug("Could not fetch secret %s from Secret Manager: %s", secret_name, e)
        return default


def get_spotify_client():
    """
    Builds an authenticated spotipy client headlessly using a refresh token.
    Credentials can be set via environment variables or Secret Manager:
      - SPOTIPY_CLIENT_ID
      - SPOTIPY_CLIENT_SECRET
      - SPOTIPY_REFRESH_TOKEN
    """
    client_id = get_secret("SPOTIPY_CLIENT_ID")
    client_secret = get_secret("SPOTIPY_CLIENT_SECRET")
    refresh_token = get_secret("SPOTIPY_REFRESH_TOKEN")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8080/callback")

    if not client_id or not client_secret:
        raise ValueError(
            "Missing SPOTIPY_CLIENT_ID or SPOTIPY_CLIENT_SECRET. "
            "Set them in environment variables or Secret Manager."
        )
    if not refresh_token:
        raise ValueError(
            "Missing SPOTIPY_REFRESH_TOKEN. Run src/auth/get_refresh_token.py "
            "to authenticate once and obtain your refresh token."
        )

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )
    token_info = auth_manager.refresh_access_token(refresh_token)
    access_token = token_info.get("access_token")
    if not access_token:
        raise RuntimeError("Failed to refresh Spotify access token.")

    return spotipy.Spotify(auth=access_token)


def flatten_json(y):
    """Recursively flattens a nested JSON dictionary or list."""
    out = {}

    def flatten(x, name=''):
        if isinstance(x, dict):
            for a in x:
                flatten(x[a], f"{name}{a}_")
        elif isinstance(x, list):
            for i, a in enumerate(x):
                flatten(a, f"{name}{i}_")
        else:
            out[name[:-1]] = x

    flatten(y)
    return out


def upload_blob(bucket_name, blob_text, destination_blob_name):
    """Uploads text/JSON payload to Cloud Storage."""
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_string(blob_text, content_type="application/json")
    logger.info("File %s uploaded to %s.", destination_blob_name, bucket_name)
    return destination_blob_name


def load_tracks_bq(tracks):
    """Loads recently played tracks to BigQuery play_history_new table."""
    items = tracks.get("items", [])
    if not items:
        logger.info("No tracks found in response to load into BigQuery.")
        return "No tracks to load"

    dic_flattened = [flatten_json(d) for d in items]
    df = pd.DataFrame(dic_flattened)

    expected_cols = [
        "track_name",
        "played_at",
        "track_album_artists_0_name",
        "track_album_name",
        "track_type",
        "track_uri"
    ]
    # Ensure expected columns exist even if API response omitted any
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df_recently_played = df[expected_cols]

    destination_table = f"{DATASET_NAME}.play_history_new"
    pandas_gbq.to_gbq(
        df_recently_played,
        destination_table,
        project_id=PROJECT_ID,
        if_exists="append"
    )
    logger.info("Loaded %d tracks into %s.", len(df_recently_played), destination_table)
    return "dataset loaded to BQ"


def load_albums_bq(albums, artist_genres_map=None):
    """Loads saved albums into BigQuery new_albums and upserts into all_albums with cover art and genres."""
    items = albums.get("items", [])
    if not items:
        logger.info("No albums found in response to load into BigQuery.")
        return "No albums to load"

    dic_flattened = [flatten_json(d) for d in items]
    df = pd.DataFrame(dic_flattened)

    # Extract best available cover image (prefer 640px or 300px)
    if "album_images_0_url" in df.columns:
        df["album_image_url"] = df["album_images_0_url"]
    elif "album_images_1_url" in df.columns:
        df["album_image_url"] = df["album_images_1_url"]
    else:
        df["album_image_url"] = None

    # Map genres if available
    if artist_genres_map and "album_artists_0_id" in df.columns:
        df["album_genres"] = df["album_artists_0_id"].map(artist_genres_map).fillna("")
    else:
        df["album_genres"] = ""

    expected_cols = [
        "album_uri",
        "added_at",
        "album_artists_0_name",
        "album_name",
        "album_type",
        "album_label",
        "album_release_date",
        "album_tracks_total",
        "album_id",
        "album_image_url",
        "album_genres"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df_recent_albums = df[expected_cols]

    # 1. Append to legacy new_albums table (subset of columns)
    legacy_cols = [
        "album_uri", "added_at", "album_artists_0_name", "album_name",
        "album_type", "album_label", "album_release_date", "album_tracks_total", "album_id"
    ]
    destination_table = f"{DATASET_NAME}.new_albums"
    try:
        pandas_gbq.to_gbq(
            df_recent_albums[legacy_cols],
            destination_table,
            project_id=PROJECT_ID,
            if_exists="append"
        )
        logger.info("Loaded %d albums into %s.", len(df_recent_albums), destination_table)
    except Exception as e:
        logger.warning("Error appending to %s: %s", destination_table, e)

    # 2. Append new albums directly into all_albums (dashboard source of truth)
    try:
        client = bigquery.Client(project=PROJECT_ID)
        all_albums_table = f"{PROJECT_ID}.{DATASET_NAME}.all_albums"
        existing_q = f"SELECT DISTINCT album_id FROM `{all_albums_table}` WHERE album_id IS NOT NULL"
        existing_ids = set(client.query(existing_q).to_dataframe()["album_id"])

        new_in_all = df_recent_albums[~df_recent_albums["album_id"].isin(existing_ids)]
        if not new_in_all.empty:
            pandas_gbq.to_gbq(
                new_in_all,
                f"{DATASET_NAME}.all_albums",
                project_id=PROJECT_ID,
                if_exists="append"
            )
            logger.info("Successfully appended %d brand new albums into %s.all_albums!", len(new_in_all), DATASET_NAME)
        else:
            logger.info("All %d recent albums already exist in %s.all_albums.", len(df_recent_albums), DATASET_NAME)
    except Exception as e:
        logger.warning("Error appending to all_albums: %s", e)

    return "dataset loaded to BQ"


def fetch_artist_genres(sp, artist_ids):
    """
    Fetches genres for a list of artist IDs from Spotify in batches of 50.
    Returns a dict mapping artist_id -> comma-separated genres string.
    """
    artist_genres = {}
    valid_ids = list(set([aid for aid in artist_ids if aid]))
    logger.info("Fetching genres for %d unique artists...", len(valid_ids))

    for i in range(0, len(valid_ids), 50):
        batch = valid_ids[i:i + 50]
        try:
            res = sp.artists(batch)
            for artist in res.get("artists", []):
                if artist and "id" in artist:
                    genres = artist.get("genres", [])
                    artist_genres[artist["id"]] = ", ".join(genres)
        except Exception as e:
            logger.warning("Error fetching artist genres for batch: %s", e)

    return artist_genres


def load_all_albums_bq(albums, artist_genres_map=None):
    """Replaces all_albums table with full library scan, including images and genres."""
    if not albums:
        logger.info("No albums provided to load into BigQuery.")
        return "No albums to load"

    dic_flattened = [flatten_json(d) for d in albums]
    df = pd.DataFrame(dic_flattened)

    # Extract best available cover image (prefer 640px or 300px)
    if "album_images_0_url" in df.columns:
        df["album_image_url"] = df["album_images_0_url"]
    elif "album_images_1_url" in df.columns:
        df["album_image_url"] = df["album_images_1_url"]
    else:
        df["album_image_url"] = None

    # Map genres if available
    if artist_genres_map and "album_artists_0_id" in df.columns:
        df["album_genres"] = df["album_artists_0_id"].map(artist_genres_map).fillna("")
    else:
        df["album_genres"] = ""

    expected_cols = [
        "album_uri",
        "added_at",
        "album_artists_0_name",
        "album_name",
        "album_type",
        "album_label",
        "album_release_date",
        "album_tracks_total",
        "album_id",
        "album_image_url",
        "album_genres"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df_all_albums = df[expected_cols]

    destination_table = f"{DATASET_NAME}.all_albums"
    pandas_gbq.to_gbq(
        df_all_albums,
        destination_table,
        project_id=PROJECT_ID,
        if_exists="replace"
    )
    logger.info("Saved %d total albums into %s.", len(df_all_albums), destination_table)
    return "dataset loaded to BQ"


def get_latest_played_timestamp(lookback_minutes=10):
    """
    Queries BigQuery for the latest played_at timestamp in the landing table
    and subtracts a safety lookback buffer (default: 10 mins).
    Returns epoch timestamp in milliseconds, or None if table is empty.
    """
    try:
        client = bigquery.Client(project=PROJECT_ID)
        query = (
            f"SELECT MAX(played_at) as max_played_at "
            f"FROM `{PROJECT_ID}.{DATASET_NAME}.play_history_new` "
            f"WHERE played_at IS NOT NULL AND played_at != 'href'"
        )
        query_job = client.query(query)
        results = list(query_job.result())
        if results and results[0].max_played_at:
            max_dt = pd.to_datetime(results[0].max_played_at)
            buffer_dt = max_dt - pd.Timedelta(minutes=lookback_minutes)
            epoch_ms = int(buffer_dt.timestamp() * 1000)
            logger.info(
                "Latest BQ play: %s. Querying Spotify with %dm buffer: %s (epoch ms: %s)",
                max_dt, lookback_minutes, buffer_dt, epoch_ms
            )
            return epoch_ms
    except Exception as e:
        logger.warning("Could not determine latest played timestamp from BQ: %s", e)
    return None


@functions_framework.http
def get_recently_played(request):
    """
    Cloud Function HTTP handler: Fetches recently played tracks
    from Spotify, archives to GCS, and appends to BigQuery.
    Uses after cursor with lookback buffer to guarantee zero track loss.
    """
    try:
        sp = get_spotify_client()
        after_ms = get_latest_played_timestamp(lookback_minutes=10)

        if after_ms:
            recent_tracks = sp.current_user_recently_played(limit=50, after=after_ms)
        else:
            recent_tracks = sp.current_user_recently_played(limit=50)

        items = recent_tracks.get("items", [])
        if not items:
            logger.info("No new tracks found since last ingestion window.")
            return (
                json.dumps({
                    "status": "success",
                    "tracks_loaded": 0,
                    "message": "No new tracks in window"
                }),
                200,
                {"Content-Type": "application/json"}
            )

        timestr = time.strftime("%Y%m%d_%H%M%S")
        folders = time.strftime("%Y/%m/%d")
        recent_tracks_json = json.dumps(recent_tracks, sort_keys=True, indent=2)

        destination_blob = f"spotify/{folders}/recently_played_{timestr}.json"
        upload_blob(BUCKET_NAME, recent_tracks_json, destination_blob)

        load_tracks_bq(recent_tracks)

        item_count = len(items)
        return (
            json.dumps({
                "status": "success",
                "tracks_loaded": item_count,
                "gcs_path": destination_blob
            }),
            200,
            {"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.exception("Error executing get_recently_played: %s", e)
        return (
            json.dumps({"status": "error", "message": str(e)}),
            500,
            {"Content-Type": "application/json"}
        )


@functions_framework.http
def get_recent_albums(request):
    """
    Cloud Function HTTP handler: Fetches recently saved albums,
    archives to GCS, and appends to BigQuery.
    """
    try:
        sp = get_spotify_client()
        recent_albums = sp.current_user_saved_albums(limit=50)

        timestr = time.strftime("%Y%m%d_%H%M%S")
        folders = time.strftime("%Y/%m/%d")
        recent_albums_json = json.dumps(recent_albums, sort_keys=True, indent=2)

        destination_blob = f"spotify/{folders}/recent_albums_{timestr}.json"
        upload_blob(BUCKET_NAME, recent_albums_json, destination_blob)

        # Collect artist IDs to enrich recent albums with genres
        items = recent_albums.get("items", [])
        artist_ids = []
        for item in items:
            album_obj = item.get("album", {})
            artists = album_obj.get("artists", [])
            if artists and "id" in artists[0]:
                artist_ids.append(artists[0]["id"])
        artist_genres_map = fetch_artist_genres(sp, artist_ids)

        load_albums_bq(recent_albums, artist_genres_map=artist_genres_map)

        item_count = len(items)
        return (
            json.dumps({
                "status": "success",
                "albums_loaded": item_count,
                "gcs_path": destination_blob
            }),
            200,
            {"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.exception("Error executing get_recent_albums: %s", e)
        return (
            json.dumps({"status": "error", "message": str(e)}),
            500,
            {"Content-Type": "application/json"}
        )


@functions_framework.http
def get_all_saved_albums(request):
    """
    Cloud Function HTTP handler: Fetches all saved albums with pagination,
    archives to GCS, and replaces all_albums in BigQuery.
    """
    try:
        sp = get_spotify_client()
        albums = []
        results = sp.current_user_saved_albums(limit=50)
        albums.extend(results.get("items", []))

        while results.get("next"):
            results = sp.next(results)
            albums.extend(results.get("items", []))

        # Collect artist IDs to enrich with genres
        artist_ids = []
        for item in albums:
            album_obj = item.get("album", {})
            artists = album_obj.get("artists", [])
            if artists and "id" in artists[0]:
                artist_ids.append(artists[0]["id"])

        artist_genres_map = fetch_artist_genres(sp, artist_ids)

        timestr = time.strftime("%Y%m%d_%H%M%S")
        folders = time.strftime("%Y/%m/%d")
        all_albums_json = json.dumps(albums, sort_keys=True, indent=2)

        destination_blob = f"spotify/{folders}/all_albums_{timestr}.json"
        upload_blob(BUCKET_NAME, all_albums_json, destination_blob)

        load_all_albums_bq(albums, artist_genres_map=artist_genres_map)

        return (
            json.dumps({
                "status": "success",
                "albums_total": len(albums),
                "gcs_path": destination_blob
            }),
            200,
            {"Content-Type": "application/json"}
        )
    except Exception as e:
        logger.exception("Error executing get_all_saved_albums: %s", e)
        return (
            json.dumps({"status": "error", "message": str(e)}),
            500,
            {"Content-Type": "application/json"}
        )


if __name__ == "__main__":
    job = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if job == "sync":
        logger.info("--- 1. Ingesting Recently Played Tracks ---")
        print(get_recently_played(None))
        logger.info("--- 2. Ingesting Recently Saved Albums ---")
        print(get_recent_albums(None))
    elif job == "albums":
        print(get_recent_albums(None))
    elif job == "all_albums":
        print(get_all_saved_albums(None))
    else:
        print(get_recently_played(None))
