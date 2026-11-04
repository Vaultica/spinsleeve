import os
import sys
import time
import json
import logging
import datetime
import urllib.parse
import re
from collections import Counter
from functools import wraps

from flask import (
    Flask,
    render_template_string,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    Response
)
import pandas as pd
import requests
from google.cloud import bigquery, datastore, secretmanager
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_v2")

app = Flask(__name__)

# Project & Dataset settings
PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = "spotify_v2"
ADMIN_USER_IDS = ["serbou", "sergebou", "vaultica"]


# ==============================================================================
# SECRET MANAGER & AUTHENTICATION CONFIGURATION
# ==============================================================================
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
app.secret_key = get_secret("FLASK_SECRET_KEY", "spinsleeve-beta-secure-session-key-2026")
app.config["SESSION_COOKIE_NAME"] = "__session"  # Required for Firebase Hosting
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_datastore_client():
    return datastore.Client(project=PROJECT_ID)


def get_oauth_client(request_obj):
    """Builds a SpotifyOAuth client with a dynamic callback URL based on incoming request."""
    scheme = "https" if (request_obj.is_secure or request_obj.headers.get("X-Forwarded-Proto") == "https") else "http"
    host = request_obj.headers.get("X-Forwarded-Host") or request_obj.host
    redirect_uri = f"{scheme}://{host}/beta/callback"

    scope = "user-library-read user-read-recently-played user-read-email user-read-private"
    return SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=redirect_uri,
        scope=scope,
        show_dialog=True
    )


# Brand Logo: Original 33 RPM Rotating Platter + Spotify Soundwaves + Tonearm
ICON_A_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <defs>
    <style>
      @keyframes spin33 {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
      }
      .spin-record {
        transform-origin: 48px 52px;
        animation: spin33 1.8s linear infinite;
      }
    </style>
  </defs>
  <!-- Spinning Vinyl Platter (33 RPM = 1.80s per revolution) -->
  <g class="spin-record">
    <!-- Vinyl Platter Base / Dark Rim -->
    <circle cx="48" cy="52" r="46" fill="#0C0F12" stroke="#1DB954" stroke-width="3"/>
    <!-- Spotify Green Core Platter -->
    <circle cx="48" cy="52" r="40" fill="#1DB954"/>
    <!-- Spotify Soundwaves in Bold Black -->
    <path d="M30 40c9-2.5 19-1.5 27 3" stroke="#0C0F12" stroke-width="5" stroke-linecap="round"/>
    <path d="M33 49c8-1.8 16-1 22 2.5" stroke="#0C0F12" stroke-width="4.2" stroke-linecap="round"/>
    <path d="M36 58c6-1.2 12-0.5 17 2" stroke="#0C0F12" stroke-width="3.5" stroke-linecap="round"/>
    <!-- Center Spindle -->
    <circle cx="48" cy="52" r="5" fill="#0C0F12"/>
  </g>
  <!-- Stationary Tonearm & Pivot (Does NOT rotate) -->
  <circle cx="86" cy="14" r="9" fill="#181D22" stroke="#9CA3AF" stroke-width="3"/>
  <circle cx="86" cy="14" r="4" fill="#1DB954"/>
  <!-- Metallic Tonearm Rod in Bright White -->
  <path d="M83 19 L66 62 L52 68" stroke="#FFFFFF" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
  <!-- Cartridge / Headshell Needle -->
  <rect x="43" y="63" width="11" height="8" rx="2" fill="#0C0F12" stroke="#1DB954" stroke-width="1.5" transform="rotate(-22 48 67)"/>
</svg>"""

ICON_GATEFOLD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
</svg>"""


@app.context_processor
def inject_admin_context():
    real_admin = session.get("admin_user_id") or session.get("user_id")
    is_admin = (real_admin in ADMIN_USER_IDS) or (session.get("role") == "admin")
    return {
        "is_admin": is_admin,
        "is_impersonating": bool(session.get("is_impersonating", False)),
        "admin_user_id": session.get("admin_user_id")
    }


@app.route("/favicon.svg")
@app.route("/favicon.ico")
@app.route("/beta/favicon.svg")
@app.route("/beta/favicon.ico")
def favicon():
    return Response(ICON_A_SVG, mimetype="image/svg+xml")


# ==============================================================================
# AUTHENTICATION & ACCESS CONTROL HELPERS
# ==============================================================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/beta/login")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/beta/login")
        if session.get("role") != "admin" and session.get("user_id") not in ADMIN_USER_IDS and session.get("admin_user_id") not in ADMIN_USER_IDS:
            return redirect("/beta/")
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# DATA CONVERTERS & SAFE PARSING
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
    if pd.notna(val) and val is not None:
        s = str(val).strip()
        if s and s.lower() != "nan":
            return s
    return default


# ==============================================================================
# MULTI-TENANT BIGQUERY ENGINE & INITIAL SYNC
# ==============================================================================
_user_album_cache = {}
_user_album_cache_time = {}
_user_analytics_cache = {}
_user_analytics_cache_time = {}
CACHE_TTL = 60


def sync_user_initial_data(user_id, access_token):
    """Syncs the initial 50 saved albums and 50 tracks for an approved user on first login."""
    try:
        sp = spotipy.Spotify(auth=access_token)
        bq_client = bigquery.Client(project=PROJECT_ID)

        # 1. Fetch saved albums
        saved = sp.current_user_saved_albums(limit=50)
        items = saved.get("items", [])
        if items:
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
                    "genres": ""
                })
            df_albums = pd.DataFrame(rows)
            table_ref = f"{PROJECT_ID}.{DATASET_V2}.user_saved_albums"
            job = bq_client.load_table_from_dataframe(df_albums, table_ref)
            job.result()
            logger.info("Loaded %d initial albums for %s into %s", len(df_albums), user_id, table_ref)

        # 2. Fetch recently played tracks
        recent_tracks = sp.current_user_recently_played(limit=50)
        t_items = recent_tracks.get("items", [])
        if t_items:
            t_rows = []
            for item in t_items:
                track = item.get("track", {})
                alb = track.get("album", {})
                artists = track.get("artists", [])
                artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
                artist_id = artists[0].get("id", None) if artists else None
                t_rows.append({
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
            df_tracks = pd.DataFrame(t_rows)
            table_ref = f"{PROJECT_ID}.{DATASET_V2}.playback_history"
            job = bq_client.load_table_from_dataframe(df_tracks, table_ref)
            job.result()
            logger.info("Loaded %d initial tracks for %s into %s", len(df_tracks), user_id, table_ref)

    except Exception as e:
        logger.error("Error during initial sync for %s: %s", user_id, e)


def fetch_user_album_data(user_id, force_refresh=False):
    global _user_album_cache, _user_album_cache_time
    now = time.time()

    if not force_refresh and user_id in _user_album_cache and (now - _user_album_cache_time.get(user_id, 0)) < CACHE_TTL:
        return _user_album_cache[user_id]

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features`
    WHERE user_id = @user_id
    ORDER BY album_plays DESC, added_at DESC
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )
    df = client.query(query, job_config=job_config).to_dataframe()

    if df.empty:
        empty_data = {
            "albums": [],
            "top_genres": [],
            "kpis": {"total_albums": 0, "played_albums": 0, "unplayed_albums": 0, "pct_explored": 0, "total_plays": 0, "top_album": "None", "top_album_plays": 0}
        }
        _user_album_cache[user_id] = empty_data
        _user_album_cache_time[user_id] = now
        return empty_data

    processed = []
    genre_counter = Counter()

    for _, row in df.iterrows():
        raw_personnel = row.get("personnel")
        personnel_list = []
        if isinstance(raw_personnel, list):
            personnel_list = raw_personnel
        elif isinstance(raw_personnel, str) and raw_personnel.strip():
            try:
                personnel_list = json.loads(raw_personnel)
            except Exception:
                personnel_list = [p.strip() for p in raw_personnel.split(",") if p.strip()]

        desc_str = safe_str(row.get("album_description"))
        pf_str = safe_str(row.get("pitchfork_score"))
        meta_str = safe_str(row.get("metacritic_score"))
        am_str = safe_str(row.get("allmusic_score"))
        disc_str = safe_str(row.get("discogs_rating"))

        has_gatefold = bool(desc_str or pf_str or meta_str or am_str or disc_str or personnel_list)

        item = {
            "album_id": safe_str(row.get("album_id")),
            "album_name": safe_str(row.get("album_name"), "Unknown Album"),
            "album_artist_name": safe_str(row.get("album_artist_name"), "Unknown Artist"),
            "album_release_date": safe_str(row.get("album_release_date")),
            "release_year": safe_str(row.get("release_year")),
            "album_type": safe_str(row.get("album_type"), "album"),
            "album_label": safe_str(row.get("album_label")),
            "album_tracks_total": safe_int(row.get("album_tracks_total")),
            "album_track_plays": safe_int(row.get("album_track_plays")),
            "album_plays": safe_float(row.get("album_plays")),
            "album_image_url": safe_str(row.get("album_image_url")) or "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80",
            "album_url": safe_str(row.get("album_url")) or f"https://open.spotify.com/album/{safe_str(row.get('album_id'))}",
            "album_genres": safe_str(row.get("album_genres")),
            "added_at": safe_str(row.get("added_at")),
            "has_gatefold": has_gatefold,
            "album_description": desc_str,
            "pitchfork_score": pf_str,
            "metacritic_score": meta_str,
            "allmusic_score": am_str,
            "discogs_rating": disc_str,
            "discogs_votes": safe_int(row.get("discogs_votes")),
            "wikipedia_url": safe_str(row.get("wikipedia_url")),
            "discogs_url": safe_str(row.get("discogs_url")),
            "styles": safe_str(row.get("enriched_styles")) or safe_str(row.get("album_genres")),
            "personnel": personnel_list
        }
        processed.append(item)

        g_str = safe_str(row.get("album_genres"))
        if g_str:
            for g in g_str.split(","):
                clean_g = g.strip().lower()
                if clean_g:
                    genre_counter[clean_g] += 1

    total_albums = len(processed)
    played_albums = sum(1 for a in processed if a["album_track_plays"] > 0)
    unplayed_albums = total_albums - played_albums
    pct_explored = round((played_albums / total_albums * 100), 1) if total_albums > 0 else 0
    total_plays = sum(a["album_track_plays"] for a in processed)
    top_album = processed[0]["album_name"] if processed else "None"
    top_album_plays = int(processed[0]["album_plays"]) if processed else 0

    kpis = {
        "total_albums": total_albums,
        "played_albums": played_albums,
        "unplayed_albums": unplayed_albums,
        "pct_explored": pct_explored,
        "total_plays": total_plays,
        "top_album": top_album,
        "top_album_plays": top_album_plays
    }

    result = {
        "albums": processed,
        "top_genres": [g for g, _ in genre_counter.most_common(20)],
        "kpis": kpis
    }

    _user_album_cache[user_id] = result
    _user_album_cache_time[user_id] = now
    return result


def fetch_user_analytics_data(user_id, range_param="30d", genre_param="all", start_date=None, end_date=None):
    global _user_analytics_cache, _user_analytics_cache_time
    cache_key = f"{user_id}::{range_param}::{genre_param}::{start_date}::{end_date}"
    now = time.time()

    if cache_key in _user_analytics_cache and (now - _user_analytics_cache_time.get(cache_key, 0)) < 300:
        return _user_analytics_cache[cache_key]

    client = bigquery.Client(project=PROJECT_ID)

    conditions = ["p.user_id = @user_id"]
    query_params = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]

    if start_date and end_date:
        conditions.append("DATE(p.played_at) BETWEEN @start_date AND @end_date")
        query_params.append(bigquery.ScalarQueryParameter("start_date", "STRING", start_date))
        query_params.append(bigquery.ScalarQueryParameter("end_date", "STRING", end_date))
    elif range_param == "1d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)")
    elif range_param == "7d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)")
    elif range_param == "30d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
    elif range_param == "60d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)")
    elif range_param == "90d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)")
    elif range_param in ("year", "this_year"):
        conditions.append("EXTRACT(YEAR FROM p.played_at) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP())")

    if genre_param and genre_param != "all":
        conditions.append("LOWER(COALESCE(a.genres, '')) LIKE @genre_filter")
        query_params.append(bigquery.ScalarQueryParameter("genre_filter", "STRING", f"%{genre_param.lower()}%"))

    where_str = "WHERE " + " AND ".join(conditions)

    query = f"""
    WITH first_plays AS (
      SELECT album_name, MIN(played_at) as first_played_at
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history`
      WHERE user_id = @user_id
      GROUP BY album_name
    ),
    filtered_plays AS (
      SELECT 
        p.album_name as album,
        p.artist_name as artist,
        p.track_name as track,
        p.track_uri,
        p.played_at as ts,
        DATE(p.played_at) as play_date,
        EXTRACT(DAYOFWEEK FROM p.played_at) as dow,
        EXTRACT(HOUR FROM p.played_at) as hour,
        COALESCE(a.image_url, g.image_url) as album_image_url,
        COALESCE(a.release_date, g.release_date) as album_release_date,
        COALESCE(a.genres, g.genres) as album_genres,
        fp.first_played_at
      FROM `{PROJECT_ID}.{DATASET_V2}.playback_history` p
      LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` a
        ON p.user_id = a.user_id AND (p.album_id = a.album_id OR LOWER(TRIM(p.album_name)) = LOWER(TRIM(a.album_name)))
      LEFT JOIN (
        SELECT 
          LOWER(TRIM(album_name)) as norm_name, 
          MAX(image_url) as image_url, 
          MAX(release_date) as release_date, 
          MAX(genres) as genres
        FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
        GROUP BY norm_name
      ) g
        ON LOWER(TRIM(p.album_name)) = g.norm_name
      LEFT JOIN first_plays fp
        ON p.album_name = fp.album_name
      {where_str}
    )
    SELECT * FROM filtered_plays
    """
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    df = client.query(query, job_config=job_config).to_dataframe()

    if df.empty:
        empty_payload = {
            "kpis": {"total_tracks": 0, "total_albums": 0, "total_artists": 0, "listening_time": "0h 0m", "top_album": None},
            "time_series": [],
            "discovery_vs_repeat": {"fresh_albums": 0, "repeat_albums": 0, "fresh_plays": 0, "repeat_plays": 0, "fresh_pct": 0, "repeat_pct": 0},
            "top_albums": [],
            "top_artists": [],
            "top_tracks": [],
            "eras": [],
            "genres": [],
            "heatmap": [[0]*24 for _ in range(7)]
        }
        _user_analytics_cache[cache_key] = empty_payload
        _user_analytics_cache_time[cache_key] = now
        return empty_payload

    total_tracks = len(df)
    total_albums = int(df["album"].nunique())
    total_artists = int(df["artist"].nunique())
    total_seconds = total_tracks * 210
    hours = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    listening_time = f"{hours}h {mins}m"

    album_counts = df.groupby(["album", "artist"]).agg(
        plays=("ts", "count"),
        album_image_url=("album_image_url", "first")
    ).reset_index().sort_values("plays", ascending=False)

    if not album_counts.empty:
        top_row = album_counts.iloc[0]
        top_img = safe_str(top_row.get("album_image_url"))
        if not top_img:
            top_img = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80"
        top_album = {
            "name": safe_str(top_row.get("album"), "Unknown Album"),
            "artist": safe_str(top_row.get("artist"), "Unknown Artist"),
            "image": top_img,
            "plays": int(top_row["plays"])
        }
    else:
        top_album = None

    daily = df.groupby("play_date").size().reset_index(name="plays").sort_values("play_date")
    time_series = [{"date": str(r["play_date"]), "plays": int(r["plays"])} for _, r in daily.iterrows()]

    min_window = df["ts"].min()
    album_window = df.groupby(["album", "first_played_at"]).size().reset_index(name="plays")
    fresh_mask = album_window["first_played_at"] >= min_window
    fresh_albums = int(fresh_mask.sum())
    repeat_albums = int((~fresh_mask).sum())
    fresh_plays = int(album_window[fresh_mask]["plays"].sum())
    repeat_plays = int(album_window[~fresh_mask]["plays"].sum())
    total_window_plays = fresh_plays + repeat_plays
    fresh_pct = round((fresh_plays / total_window_plays) * 100, 1) if total_window_plays > 0 else 0
    repeat_pct = round((repeat_plays / total_window_plays) * 100, 1) if total_window_plays > 0 else 0

    top_albums = []
    for _, r in album_counts.head(10).iterrows():
        img = safe_str(r.get("album_image_url"))
        if not img:
            img = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80"
        top_albums.append({
            "name": safe_str(r.get("album"), "Unknown Album"),
            "artist": safe_str(r.get("artist"), "Unknown Artist"),
            "image": img,
            "plays": int(r["plays"])
        })

    artist_counts = df.groupby("artist").size().reset_index(name="plays").sort_values("plays", ascending=False)
    top_artists = [{"name": safe_str(r.get("artist"), "Unknown Artist"), "plays": int(r["plays"])} for _, r in artist_counts.head(10).iterrows()]

    track_counts = df.groupby(["track", "artist", "album"]).size().reset_index(name="plays").sort_values("plays", ascending=False)
    top_tracks = []
    for _, r in track_counts.head(10).iterrows():
        top_tracks.append({
            "title": safe_str(r.get("track"), "Unknown Track"),
            "artist": safe_str(r.get("artist"), "Unknown Artist"),
            "album": safe_str(r.get("album"), "Unknown Album"),
            "plays": int(r["plays"])
        })

    def get_era(rel_date):
        if not rel_date or len(str(rel_date)) < 4:
            return "Unknown"
        y = str(rel_date)[:4]
        if not y.isdigit(): return "Unknown"
        yi = int(y)
        if yi < 1970: return "<1970"
        elif yi < 1980: return "70s"
        elif yi < 1990: return "80s"
        elif yi < 2000: return "90s"
        elif yi < 2010: return "2000s"
        elif yi < 2020: return "2010s"
        else: return "2020s"

    df["era"] = df["album_release_date"].apply(get_era)
    era_order = ["<1970", "70s", "80s", "90s", "2000s", "2010s", "2020s"]
    era_counts = df.groupby("era").size().to_dict()
    eras = [{"era": e, "plays": int(era_counts.get(e, 0))} for e in era_order if era_counts.get(e, 0) > 0]

    genre_counter = Counter()
    for g_str in df["album_genres"].dropna():
        if g_str:
            for g in str(g_str).split(","):
                clean_g = g.strip().lower()
                if clean_g:
                    genre_counter[clean_g] += 1
    genres = [{"genre": g.title(), "plays": count} for g, count in genre_counter.most_common(8)]

    heatmap = [[0]*24 for _ in range(7)]
    for _, r in df.iterrows():
        d_idx = (int(r["dow"]) + 5) % 7
        h_idx = int(r["hour"])
        if 0 <= d_idx < 7 and 0 <= h_idx < 24:
            heatmap[d_idx][h_idx] += 1

    payload = {
        "kpis": {
            "total_tracks": total_tracks,
            "total_albums": total_albums,
            "total_artists": total_artists,
            "listening_time": listening_time,
            "top_album": top_album
        },
        "time_series": time_series,
        "discovery_vs_repeat": {
            "fresh_albums": fresh_albums,
            "repeat_albums": repeat_albums,
            "fresh_plays": fresh_plays,
            "repeat_plays": repeat_plays,
            "fresh_pct": fresh_pct,
            "repeat_pct": repeat_pct
        },
        "top_albums": top_albums,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "eras": eras,
        "genres": genres,
        "heatmap": heatmap
    }

    def sanitize_payload(obj):
        import math
        if isinstance(obj, dict):
            return {k: sanitize_payload(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_payload(v) for v in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return 0.0
        return obj

    payload = sanitize_payload(payload)
    _user_analytics_cache[cache_key] = payload
    _user_analytics_cache_time[cache_key] = now
    return payload


# ==============================================================================
# 4. SPINPALS: CRATEMATES & ACOUSTIC CHEMISTRY ENGINE
# ==============================================================================
def fetch_pals_directory(current_user_id):
    """Fetches all approved community members in the Listening Lounge."""
    ds_client = get_datastore_client()
    query = ds_client.query(kind="User")
    query.add_filter(filter=datastore.query.PropertyFilter("is_approved", "=", True))
    raw_users = list(query.fetch())
    # Only include community members who have opted into SpinPals or are administrators
    users = [
        u for u in raw_users
        if u.get("pals_opt_in") or (u.key.name in ADMIN_USER_IDS) or (u.get("spotify_id") in ADMIN_USER_IDS)
    ]

    bq_client = bigquery.Client(project=PROJECT_ID)
    q_counts = f"""
    SELECT user_id, COUNT(*) as album_count
    FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
    GROUP BY user_id
    """
    df_counts = bq_client.query(q_counts).to_dataframe()
    counts_map = dict(zip(df_counts["user_id"], df_counts["album_count"]))

    pals = []
    for u in users:
        uid = u.key.name or u.get("spotify_id")
        if uid == "vaultica":  # Skip system alias
            continue
        pals.append({
            "spotify_id": uid,
            "display_name": u.get("display_name") or uid,
            "avatar_url": u.get("avatar_url") or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
            "album_count": int(counts_map.get(uid, 0)),
            "is_self": (uid == current_user_id)
        })

    # Sort so self is first, followed by others alphabetically
    pals.sort(key=lambda p: (not p["is_self"], p["display_name"].lower()))
    return pals


def compute_pal_compatibility(current_user_id, pal_id):
    """Computes acoustic chemistry, shared vinyl, and top 5 borrow recommendations."""
    bq_client = bigquery.Client(project=PROJECT_ID)
    ds_client = get_datastore_client()

    pal_key = ds_client.key("User", pal_id)
    pal_entity = ds_client.get(pal_key)
    pal_name = pal_entity.get("display_name") if pal_entity else pal_id
    pal_avatar = pal_entity.get("avatar_url") if pal_entity else ""
    if not pal_avatar:
        pal_avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"

    q_pal_albums = f"""
    SELECT 
      f.album_id,
      f.album_name,
      f.album_artist_name,
      f.album_image_url,
      f.release_year,
      f.album_genres,
      f.album_track_plays,
      f.album_plays,
      f.pitchfork_score,
      f.metacritic_score,
      f.discogs_rating,
      f.discogs_votes,
      f.album_description,
      f.personnel,
      f.wikipedia_url,
      f.discogs_url,
      f.enriched_styles,
      CASE WHEN my.album_id IS NOT NULL THEN 1 ELSE 0 END as current_user_owns
    FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features` f
    LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` my
      ON my.user_id = @current_user_id AND f.album_id = my.album_id
    WHERE f.user_id = @pal_id
    ORDER BY f.album_plays DESC, f.added_at DESC
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("current_user_id", "STRING", current_user_id),
            bigquery.ScalarQueryParameter("pal_id", "STRING", pal_id)
        ]
    )
    df_pal = bq_client.query(q_pal_albums, job_config=job_cfg).to_dataframe()

    q_my_count = f"""
    SELECT COUNT(*) as total_albums
    FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
    WHERE user_id = @current_user_id
    """
    my_cnt_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("current_user_id", "STRING", current_user_id)]
    )
    df_my_count = bq_client.query(q_my_count, job_config=my_cnt_cfg).to_dataframe()
    my_total_albums = int(df_my_count["total_albums"].iloc[0]) if not df_my_count.empty else 0

    processed_pal_albums = []
    for _, row in df_pal.iterrows():
        raw_personnel = row.get("personnel")
        personnel_list = []
        if isinstance(raw_personnel, list):
            personnel_list = raw_personnel
        elif isinstance(raw_personnel, str) and raw_personnel.strip():
            try:
                personnel_list = json.loads(raw_personnel)
            except Exception:
                personnel_list = [p.strip() for p in raw_personnel.split(",") if p.strip()]

        desc_str = safe_str(row.get("album_description"))
        pf_str = safe_str(row.get("pitchfork_score"))
        meta_str = safe_str(row.get("metacritic_score"))
        am_str = safe_str(row.get("allmusic_score"))
        disc_str = safe_str(row.get("discogs_rating"))
        has_gatefold = bool(desc_str or pf_str or meta_str or am_str or disc_str or personnel_list)

        processed_pal_albums.append({
            "album_id": safe_str(row.get("album_id")),
            "album_name": safe_str(row.get("album_name"), "Unknown Album"),
            "album_artist_name": safe_str(row.get("album_artist_name"), "Unknown Artist"),
            "release_year": safe_str(row.get("release_year")),
            "album_track_plays": safe_int(row.get("album_track_plays")),
            "album_plays": safe_float(row.get("album_plays")),
            "album_image_url": safe_str(row.get("album_image_url")) or "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80",
            "album_url": f"https://open.spotify.com/album/{safe_str(row.get('album_id'))}",
            "album_genres": safe_str(row.get("album_genres")),
            "has_gatefold": has_gatefold,
            "album_description": desc_str,
            "pitchfork_score": pf_str,
            "metacritic_score": meta_str,
            "allmusic_score": am_str,
            "discogs_rating": disc_str,
            "discogs_votes": safe_int(row.get("discogs_votes")),
            "wikipedia_url": safe_str(row.get("wikipedia_url")),
            "discogs_url": safe_str(row.get("discogs_url")),
            "styles": safe_str(row.get("enriched_styles")) or safe_str(row.get("album_genres")),
            "personnel": personnel_list,
            "current_user_owns": bool(row.get("current_user_owns", 0))
        })

    shared_albums = [a for a in processed_pal_albums if a["current_user_owns"]]
    unowned_albums = [a for a in processed_pal_albums if not a["current_user_owns"]]

    # Compare shared artists
    q_shared_artists = f"""
    WITH artists_a AS (
      SELECT DISTINCT LOWER(TRIM(artist_name)) as artist
      FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
      WHERE user_id = @current_user_id
    ),
    artists_b AS (
      SELECT DISTINCT LOWER(TRIM(artist_name)) as artist
      FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
      WHERE user_id = @pal_id
    )
    SELECT a.artist
    FROM artists_a a
    JOIN artists_b b ON a.artist = b.artist
    """
    df_art = bq_client.query(q_shared_artists, job_config=job_cfg).to_dataframe()
    shared_artists = [a.title() for a in df_art["artist"].tolist()] if not df_art.empty else []

    # Hybrid match percentage
    min_catalog = min(my_total_albums, len(processed_pal_albums)) if (my_total_albums > 0 and len(processed_pal_albums) > 0) else 1
    album_ratio = len(shared_albums) / min_catalog
    artist_ratio = len(shared_artists) / max(1, min(my_total_albums, len(processed_pal_albums), 20))
    raw_match = int(round(50 * album_ratio + 50 * artist_ratio))
    match_pct = max(15, min(99, raw_match))

    if match_pct >= 80:
        kinship = {
            "tier": "Vinyl Soulmates",
            "badge": "🔥 Vinyl Soulmates",
            "color": "text-rose-400 bg-rose-500/10 border-rose-500/30",
            "desc": "Uncanny acoustic connection! Your record crates and listening habits are cut from the exact same cloth."
        }
    elif match_pct >= 60:
        kinship = {
            "tier": "Acoustic Kin",
            "badge": "📻 Acoustic Kin",
            "color": "text-amber-400 bg-amber-500/10 border-amber-500/30",
            "desc": "Deep taste alignment across heavy rotations and key genres, with plenty of common ground."
        }
    elif match_pct >= 40:
        kinship = {
            "tier": "Crate Companions",
            "badge": "🤝 Crate Companions",
            "color": "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
            "desc": "Solid overlapping favorites with fantastic new territory to discover on each other's shelves."
        }
    elif match_pct >= 25:
        kinship = {
            "tier": "Curious Explorers",
            "badge": "🔍 Curious Explorers",
            "color": "text-blue-400 bg-blue-500/10 border-blue-500/30",
            "desc": "Distinct record collections with intriguing common threads waiting to be explored."
        }
    else:
        kinship = {
            "tier": "Fresh Discoveries Ahead",
            "badge": "🌌 Fresh Discoveries Ahead",
            "color": "text-purple-400 bg-purple-500/10 border-purple-500/30",
            "desc": "Completely fresh territory! Their record shelf is an uncharted goldmine of new sounds for your ears."
        }

    # Top 5 Meaningful Recommendations to Borrow
    def borrow_score(alb):
        score = alb["album_plays"] * 5
        if alb["pitchfork_score"]:
            try:
                score += float(alb["pitchfork_score"].split("/")[0]) * 2
            except Exception: pass
        if alb["discogs_rating"]:
            try:
                score += float(alb["discogs_rating"]) * 3
            except Exception: pass
        if alb["has_gatefold"]:
            score += 10
        return score

    unowned_sorted = sorted(unowned_albums, key=borrow_score, reverse=True)
    top_borrow = unowned_sorted[:5]

    for item in top_borrow:
        reasons = []
        if item["album_plays"] > 0:
            reasons.append(f"{pal_name}'s Heavy Rotation ({int(item['album_plays'])} spins)")
        if item["pitchfork_score"]:
            reasons.append(f"Pitchfork {item['pitchfork_score']}")
        elif item["discogs_rating"]:
            reasons.append(f"Discogs {item['discogs_rating']}★")
        if not reasons:
            reasons.append(f"From {pal_name}'s Crate")
        item["borrow_reason"] = " • ".join(reasons)

    return {
        "pal": {
            "spotify_id": pal_id,
            "display_name": pal_name,
            "avatar_url": pal_avatar,
            "album_count": len(processed_pal_albums)
        },
        "compatibility": {
            "match_pct": match_pct,
            "kinship": kinship,
            "shared_albums_count": len(shared_albums),
            "shared_artists_count": len(shared_artists),
            "borrow_count": len(unowned_albums),
            "shared_artists": shared_artists[:10]
        },
        "top_borrow": top_borrow,
        "shared_albums": shared_albums[:24],
        "pal_full_crate": processed_pal_albums
    }


# ==============================================================================
# AUDIO PREVIEWS (ITUNES ENGINE) & APPLE MUSIC REDIRECTOR
# ==============================================================================
_preview_cache = {}


@app.route("/api/preview")
@app.route("/beta/api/preview")
def api_preview():
    artist = request.args.get("artist", "").strip()
    album = request.args.get("album", "").strip()
    if not artist or not album:
        return jsonify({"status": "error", "message": "Missing artist or album"}), 400

    key = f"{artist.lower()}::{album.lower()}"
    if key in _preview_cache:
        return jsonify(_preview_cache[key])

    term = f"{artist} {album}"
    try:
        res = requests.get(
            "https://itunes.apple.com/search",
            params={"term": term, "entity": "song", "limit": 1},
            timeout=3.5
        )
        data = res.json()
        if data.get("resultCount", 0) > 0:
            result = data["results"][0]
            raw_url = result.get("collectionViewUrl") or result.get("trackViewUrl") or ""
            m = re.search(r"/album/(?:[^/]+/)?(\d+)", raw_url)
            am_url = f"https://geo.music.apple.com/album/{m.group(1)}?app=music&ls=1" if m else raw_url
            payload = {
                "status": "success",
                "preview_url": result.get("previewUrl"),
                "apple_music_url": am_url,
                "track_name": result.get("trackName", "Preview Snippet")
            }
        else:
            payload = {
                "status": "not_found",
                "preview_url": None,
                "apple_music_url": f"https://geo.music.apple.com/search?term={urllib.parse.quote(term)}&app=music",
                "track_name": None
            }
    except Exception as e:
        payload = {
            "status": "error",
            "message": str(e),
            "preview_url": None,
            "apple_music_url": f"https://geo.music.apple.com/search?term={urllib.parse.quote(f'{artist} {album}')}&app=music",
            "track_name": None
        }

    _preview_cache[key] = payload
    return jsonify(payload)


APPLE_REDIRECT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Opening Apple Music...</title>
    <meta http-equiv="refresh" content="0; url={{ geo_url | safe }}">
    <script>
        window.location.replace("{{ geo_url | safe }}");
    </script>
</head>
<body style="background:#0c0f12; color:#fff; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; margin:0;">
    <div style="text-align:center;">
        <p style="font-size:14px; color:#9ca3af;">Opening album in Apple Music...</p>
        <p><a href="{{ geo_url | safe }}" style="color:#1DB954; font-size:12px; text-decoration:none;">Click here if app does not open automatically</a></p>
    </div>
</body>
</html>
"""


@app.route("/open/apple/<album_id>")
@app.route("/beta/open/apple/<album_id>")
def open_apple(album_id):
    geo_url = f"https://geo.music.apple.com/album/{album_id}?app=music&ls=1"
    return render_template_string(APPLE_REDIRECT_HTML, geo_url=geo_url)


# ==============================================================================
# HTML TEMPLATES: LOGIN, PENDING INVITE, ADMIN
# ==============================================================================
LOGIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Private Beta Login</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-[#14181f] border border-gray-800 rounded-3xl p-8 text-center shadow-2xl relative overflow-hidden">
        <div class="w-16 h-16 mx-auto mb-4">
            {{ brand_icon | safe }}
        </div>
        <div class="inline-block px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full text-xs font-bold mb-3 tracking-wide">
            FRIENDS &amp; BETA ACCESS
        </div>
        <h1 class="text-3xl font-extrabold text-white tracking-tight">SpinSleeve</h1>
        <p class="text-sm text-gray-400 mt-2 mb-8 leading-relaxed">
            A virtual record crate, 12" gatefold liner notes reader, and deep listening telemetry engine for your Spotify library.
        </p>

        <a href="/beta/auth" class="w-full py-3.5 px-6 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-sm flex items-center justify-center gap-3 transition shadow-lg hover:scale-[1.02] active:scale-[0.98]">
            <svg class="w-5 h-5 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.495 17.306c-.215.353-.674.464-1.026.25-2.812-1.718-6.353-2.107-10.522-1.155-.403.092-.806-.16-.898-.564-.092-.403.16-.806.564-.898 4.568-1.045 8.483-.598 11.632 1.341.352.215.464.674.25 1.026zm1.467-3.262c-.27.44-.847.579-1.287.308-3.22-1.979-8.128-2.553-11.936-1.396-.497.151-1.025-.133-1.176-.63-.151-.497.133-1.025.63-1.176 4.356-1.323 9.775-.68 13.461 1.587.44.27.579.847.308 1.287zm.126-3.41c-3.86-2.292-10.229-2.503-13.896-1.39-.592.18-1.221-.155-1.401-.747-.18-.592.155-1.221.747-1.401 4.218-1.281 11.253-1.033 15.696 1.604.533.316.707 1.011.391 1.544-.316.533-1.011.707-1.537.39z"/></svg>
            <span>Log in with Spotify</span>
        </a>

        <div class="mt-3 text-center">
            <a href="https://accounts.spotify.com/en/logout" target="_blank" class="text-[11px] text-gray-500 hover:text-emerald-400 transition underline">
                Switch or log out of Spotify Web account
            </a>
        </div>

        <!-- Fast Testing Switcher -->
        <div class="mt-6 pt-5 border-t border-gray-800/80">
            <p class="text-[10px] font-mono uppercase text-gray-500 mb-2.5 font-bold tracking-wider">🛠️ 1-Click Fast Switcher (For Testing)</p>
            <div class="flex flex-wrap items-center justify-center gap-2">
                <a href="/beta/dev-switch/sergebou" class="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-emerald-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                    <span>👑</span> Serge
                </a>
                <a href="/beta/dev-switch/sarahboosch" class="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-rose-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                    <span>👩</span> Sarah
                </a>
                <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-amber-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                    <span>🐹</span> GuineaPig
                </a>
            </div>
        </div>

        <div class="mt-6 pt-5 border-t border-gray-800 text-[11px] text-gray-500">
            Private Beta: Access is currently invite-only. If you haven't been invited yet, your login will submit an approval request to Serge.
        </div>
    </div>
</body>
</html>
"""

PENDING_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Access Pending</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-[#14181f] border border-gray-800 rounded-3xl p-8 text-center shadow-2xl">
        <div class="w-16 h-16 rounded-full overflow-hidden mx-auto mb-4 border-2 border-amber-500/40 shadow">
            <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150' }}" class="w-full h-full object-cover">
        </div>
        <div class="inline-block px-3 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-full text-xs font-bold mb-3 tracking-wide">
            ⏳ INVITE PENDING APPROVAL
        </div>
        <h2 class="text-2xl font-bold text-white">Hey {{ user.display_name }}!</h2>
        <p class="text-sm text-gray-400 mt-2 mb-6 leading-relaxed">
            Your Spotify account is connected, but SpinSleeve is currently in private invite-only beta. We have notified Serge to approve your access!
        </p>

        <div class="flex flex-col gap-3">
            <a href="/beta/auth" class="py-3 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow">
                🔄 Check Approval Status
            </a>
            <a href="https://accounts.spotify.com/en/logout" class="py-2.5 px-4 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 font-semibold text-xs transition border border-gray-700">
                Switch to a Different Spotify Account
            </a>
            <a href="/beta/logout" class="text-xs text-gray-500 hover:text-gray-400 py-1 transition">
                Return to Login Page
            </a>
        </div>
    </div>
</body>
</html>
"""

ADMIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Admin Control Deck</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen p-6 md:p-10">
    <div class="max-w-6xl mx-auto">
        {% if is_impersonating %}
        <div class="bg-amber-500/10 border border-amber-500/30 text-amber-300 px-4 py-2.5 rounded-2xl text-xs flex items-center justify-between mb-6 shadow-lg">
            <span class="flex items-center gap-2">
                👑 <span>Currently impersonating: <strong class="text-white">{{ session.display_name }}</strong> ({{ session.user_id }})</span>
            </span>
            <a href="/beta/admin/revert" class="bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-3 py-1 rounded-xl text-xs transition">
                ↩ Revert to Admin
            </a>
        </div>
        {% endif %}

        <div class="flex items-center justify-between pb-6 mb-8 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 shrink-0">{{ brand_icon | safe }}</div>
                <div>
                    <h1 class="text-2xl font-black text-white">⚙️ Admin Control Deck</h1>
                    <p class="text-xs text-gray-400 mt-0.5">Manage private beta invitations, SpinPals permissions, and user auditing</p>
                </div>
            </div>
            <div class="flex items-center gap-3">
                <a href="/beta/" class="text-xs font-bold bg-[#1DB954] text-black px-4 py-2 rounded-xl transition hover:bg-[#1ed760] shadow">
                    Back to Library
                </a>
            </div>
        </div>

        <div class="bg-[#14181f] p-5 rounded-2xl border border-gray-800 mb-8 shadow-sm">
            <h3 class="text-sm font-bold text-white mb-3">Pre-Approve a Friend</h3>
            <form action="/beta/admin/whitelist" method="POST" class="flex flex-col gap-3">
                <div class="flex flex-col sm:flex-row gap-3">
                    <input type="text" name="spotify_id" placeholder="Spotify User ID or Username" required class="bg-[#0c0f12] border border-gray-700 rounded-xl px-4 py-2 text-xs text-white flex-1 focus:outline-none focus:border-[#1DB954]">
                    <input type="text" name="display_name" placeholder="Display Name (optional)" class="bg-[#0c0f12] border border-gray-700 rounded-xl px-4 py-2 text-xs text-white flex-1 focus:outline-none focus:border-[#1DB954]">
                    <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-5 py-2 rounded-xl transition shrink-0">
                        + Whitelist User
                    </button>
                </div>
                <div class="flex items-center gap-2 pt-1">
                    <input type="checkbox" id="pals_opt_in" name="pals_opt_in" class="rounded bg-[#0c0f12] border-gray-700 text-emerald-500 focus:ring-0">
                    <label for="pals_opt_in" class="text-xs text-gray-400 cursor-pointer">Activate SpinPals (Listening Lounge) immediately for this user</label>
                </div>
            </form>
        </div>

        <div class="bg-[#14181f] rounded-2xl border border-gray-800 overflow-hidden shadow-sm">
            <table class="w-full text-left text-xs">
                <thead class="bg-black/30 border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider font-bold">
                    <tr>
                        <th class="p-4">User</th>
                        <th class="p-4">Spotify ID</th>
                        <th class="p-4">Email</th>
                        <th class="p-4">Account Status</th>
                        <th class="p-4">SpinPals Social</th>
                        <th class="p-4">Role</th>
                        <th class="p-4 text-right">Actions</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-800/60 text-gray-300">
                    {% for u in users %}
                    <tr class="hover:bg-white/[0.02] transition">
                        <td class="p-4 flex items-center gap-3">
                            <div class="w-8 h-8 rounded-full overflow-hidden bg-gray-900 border border-gray-700 shrink-0">
                                <img src="{{ u.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                            </div>
                            <span class="font-bold text-white">{{ u.display_name or 'Anonymous' }}</span>
                        </td>
                        <td class="p-4 font-mono text-gray-400">{{ u.spotify_id }}</td>
                        <td class="p-4 text-gray-400">{{ u.email or '--' }}</td>
                        <td class="p-4">
                            {% if u.is_approved %}
                            <span class="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md font-bold text-[10px]">
                                APPROVED
                            </span>
                            {% else %}
                            <span class="px-2.5 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/20 rounded-md font-bold text-[10px]">
                                PENDING
                            </span>
                            {% endif %}
                        </td>
                        <td class="p-4">
                            {% if u.pals_opt_in %}
                            <span class="px-2.5 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-md font-bold text-[10px]">
                                ACTIVE
                            </span>
                            {% else %}
                            <span class="px-2.5 py-1 bg-gray-800 text-gray-400 border border-gray-700 rounded-md font-bold text-[10px]">
                                DISABLED
                            </span>
                            {% endif %}
                        </td>
                        <td class="p-4 text-gray-400">{{ u.role or 'user' }}</td>
                        <td class="p-4 text-right">
                            <div class="flex items-center justify-end gap-2">
                                <a href="/beta/admin/assume/{{ u.spotify_id }}" class="px-2.5 py-1 bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 rounded-lg text-[11px] font-bold transition flex items-center gap-1 shadow-sm" title="Assume this user's view">
                                    👤 Assume View
                                </a>
                                <form action="/beta/admin/toggle-pals/{{ u.spotify_id }}" method="POST" class="inline">
                                    {% if u.pals_opt_in %}
                                    <button type="submit" class="text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 border border-gray-700 px-2.5 py-1 rounded-lg text-[11px] font-bold transition">
                                        Deactivate Pals
                                    </button>
                                    {% else %}
                                    <button type="submit" class="text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg text-[11px] font-bold transition">
                                        + Opt-In Pals
                                    </button>
                                    {% endif %}
                                </form>
                                <form action="/beta/admin/toggle/{{ u.spotify_id }}" method="POST" class="inline">
                                    {% if u.is_approved %}
                                    <button type="submit" class="text-rose-400 hover:text-rose-300 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-lg text-[11px] font-bold transition">
                                        Revoke
                                    </button>
                                    {% else %}
                                    <button type="submit" class="text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-lg text-[11px] font-bold transition">
                                        ✓ Approve
                                    </button>
                                    {% endif %}
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


# ==============================================================================
# AUTHENTICATION ROUTES
# ==============================================================================
@app.route("/login")
@app.route("/beta/login")
def login():
    if "user_id" in session:
        return redirect("/beta/")
    return render_template_string(LOGIN_HTML_TEMPLATE, brand_icon=ICON_A_SVG)


@app.route("/beta/auth")
def auth():
    sp_oauth = get_oauth_client(request)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
@app.route("/beta/callback")
def callback():
    sp_oauth = get_oauth_client(request)
    code = request.args.get("code")
    if not code:
        return redirect("/beta/login")

    try:
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info.get("access_token")
        refresh_token = token_info.get("refresh_token")

        sp = spotipy.Spotify(auth=access_token)
        user_info = sp.current_user()
        spotify_id = user_info["id"]
        display_name = user_info.get("display_name") or spotify_id
        email = user_info.get("email") or ""
        images = user_info.get("images") or []
        avatar_url = images[0].get("url") if images else ""

        logger.info("Spotify OAuth authenticated user: id=%s, name=%s, email=%s", spotify_id, display_name, email)

        ds_client = get_datastore_client()
        key = ds_client.key("User", spotify_id)
        user = ds_client.get(key)

        is_admin = (spotify_id in ADMIN_USER_IDS)
        if not user:
            user = datastore.Entity(key=key)
            user.update({
                "spotify_id": spotify_id,
                "display_name": display_name,
                "email": email,
                "avatar_url": avatar_url,
                "is_approved": is_admin,
                "role": "admin" if is_admin else "user",
                "pals_opt_in": is_admin,
                "refresh_token": refresh_token,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "last_login_at": datetime.datetime.now(datetime.timezone.utc),
                "sync_status": "idle" if is_admin else "pending"
            })
            ds_client.put(user)
        else:
            user["display_name"] = display_name
            user["email"] = email
            user["avatar_url"] = avatar_url
            if is_admin:
                user["role"] = "admin"
                user["is_approved"] = True
                user["pals_opt_in"] = True
            if refresh_token:
                user["refresh_token"] = refresh_token
            user["last_login_at"] = datetime.datetime.now(datetime.timezone.utc)
            ds_client.put(user)

        if not user.get("is_approved"):
            return render_template_string(PENDING_HTML_TEMPLATE, user=user)

        session["user_id"] = spotify_id
        session["display_name"] = display_name
        session["avatar_url"] = avatar_url
        session["role"] = user.get("role", "user")
        session["pals_opt_in"] = bool(user.get("pals_opt_in", False))
        if is_admin:
            session["admin_user_id"] = spotify_id
        session["is_impersonating"] = False

        if user.get("sync_status") == "pending":
            sync_user_initial_data(spotify_id, access_token)
            user["sync_status"] = "idle"
            ds_client.put(user)

        return redirect("/beta/")

    except spotipy.exceptions.SpotifyException as se:
        if se.http_status == 403:
            logger.warning("User not registered in Spotify Developer Dashboard: %s", se)
            return render_template_string("""
                <body style="background:#0c0f12; color:#fff; font-family:sans-serif; display:flex; align-items:center; justify-content:center; height:100vh; text-align:center; padding:20px;">
                    <div style="max-width:440px; background:#14181f; border:1px solid #374151; padding:30px; border-radius:24px;">
                        <h2 style="color:#f59e0b; font-size:22px; margin-bottom:10px;">⏳ Spotify Allowlist Required</h2>
                        <p style="color:#9ca3af; font-size:13px; line-height:1.6;">
                            SpinSleeve is currently in Spotify Development Mode. Your Spotify account email needs to be added to Serge's developer dashboard.
                        </p>
                        <p style="color:#10b981; font-size:12px; margin-top:15px;">Ask Serge to add your email, then try again!</p>
                        <a href="/beta/login" style="display:inline-block; margin-top:20px; background:#1DB954; color:#000; padding:10px 20px; border-radius:12px; font-weight:bold; font-size:13px; text-decoration:none;">Return to Login</a>
                    </div>
                </body>
            """), 403
        return f"Authentication error: {se}", 500
    except Exception as e:
        logger.exception("Error in Spotify OAuth callback: %s", e)
        return f"Authentication error: {e}", 500


@app.route("/logout")
@app.route("/beta/logout")
def logout():
    session.clear()
    return redirect("/beta/login")


@app.route("/beta/admin/assume/<target_id>")
@admin_required
def admin_assume(target_id):
    ds_client = get_datastore_client()
    key = ds_client.key("User", target_id)
    user = ds_client.get(key)
    if not user:
        return f"User {target_id} not found in Datastore", 404

    real_admin = session.get("admin_user_id") or session.get("user_id")
    session["admin_user_id"] = real_admin
    session["user_id"] = target_id
    session["display_name"] = user.get("display_name", target_id)
    session["avatar_url"] = user.get("avatar_url", "")
    session["role"] = user.get("role", "user")
    session["pals_opt_in"] = bool(user.get("pals_opt_in", False))
    session["is_impersonating"] = (target_id not in ADMIN_USER_IDS)

    # Invalidate in-memory caches for this user
    _user_album_cache.pop(target_id, None)
    _user_album_cache_time.pop(target_id, None)
    keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{target_id}::")]
    for k in keys_to_del:
        _user_analytics_cache.pop(k, None)
        _user_analytics_cache_time.pop(k, None)

    logger.info("Admin %s assumed identity of: %s (%s)", real_admin, target_id, session["display_name"])
    return redirect("/beta/")


@app.route("/beta/admin/revert")
def admin_revert():
    real_admin = session.get("admin_user_id")
    if not real_admin or real_admin not in ADMIN_USER_IDS:
        return redirect("/beta/login")

    ds_client = get_datastore_client()
    key = ds_client.key("User", real_admin)
    admin_user = ds_client.get(key)
    if not admin_user:
        return redirect("/beta/login")

    session["user_id"] = real_admin
    session["display_name"] = admin_user.get("display_name", real_admin)
    session["avatar_url"] = admin_user.get("avatar_url", "")
    session["role"] = "admin"
    session["pals_opt_in"] = True
    session["is_impersonating"] = False

    logger.info("Admin %s reverted back to admin profile", real_admin)
    return redirect("/beta/admin")


@app.route("/beta/dev-switch/<user_id>")
def dev_switch(user_id):
    real_admin = session.get("admin_user_id") or session.get("user_id")
    if real_admin not in ADMIN_USER_IDS:
        return "Unauthorized switch. Only administrators can assume user profiles.", 403
    return admin_assume(user_id)


# ==============================================================================
# ADMIN ROUTES (INVITE ALLOWLIST & PERMISSIONS)
# ==============================================================================
@app.route("/admin")
@app.route("/beta/admin")
@admin_required
def admin_panel():
    client = get_datastore_client()
    query = client.query(kind="User")
    users = list(query.fetch())
    return render_template_string(ADMIN_HTML_TEMPLATE, users=users)


@app.route("/beta/admin/toggle/<spotify_id>", methods=["POST"])
@admin_required
def admin_toggle(spotify_id):
    client = get_datastore_client()
    key = client.key("User", spotify_id)
    user = client.get(key)
    if user:
        user["is_approved"] = not user.get("is_approved", False)
        client.put(user)
    return redirect("/beta/admin")


@app.route("/beta/admin/toggle-pals/<spotify_id>", methods=["POST"])
@admin_required
def admin_toggle_pals(spotify_id):
    client = get_datastore_client()
    key = client.key("User", spotify_id)
    user = client.get(key)
    if user:
        user["pals_opt_in"] = not user.get("pals_opt_in", False)
        client.put(user)
    return redirect("/beta/admin")


@app.route("/beta/admin/whitelist", methods=["POST"])
@admin_required
def admin_whitelist():
    spotify_id = request.form.get("spotify_id", "").strip()
    display_name = request.form.get("display_name", "").strip()
    pals_opt_in = request.form.get("pals_opt_in") == "on"
    if spotify_id:
        client = get_datastore_client()
        key = client.key("User", spotify_id)
        user = client.get(key)
        if not user:
            user = datastore.Entity(key=key)
            user.update({
                "spotify_id": spotify_id,
                "display_name": display_name or spotify_id,
                "is_approved": True,
                "role": "user",
                "pals_opt_in": pals_opt_in,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "sync_status": "pending"
            })
        else:
            user["is_approved"] = True
            if display_name:
                user["display_name"] = display_name
        client.put(user)
    return redirect("/beta/admin")


# ==============================================================================
# 1. TAB 1: LIBRARY EXPLORER ROUTE & TEMPLATE
# ==============================================================================
@app.route("/")
@app.route("/beta")
@app.route("/beta/")
@login_required
def beta_index():
    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    return render_template_string(
        BETA_EXPLORER_HTML,
        albums=data["albums"],
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


BETA_EXPLORER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - {{ user.display_name }}'s Library</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #14181f; }
        .serif-title { font-family: 'Playfair Display', serif; }
        .sleeve-shadow { box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.6); }
        .custom-scroll::-webkit-scrollbar { width: 5px; }
        .custom-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
        @keyframes soundWave { 0%, 100% { height: 4px; } 50% { height: 16px; } }
        .wave-bar { animation: soundWave 1.2s ease-in-out infinite; }
        .wave-bar:nth-child(2) { animation-delay: 0.2s; }
        .wave-bar:nth-child(3) { animation-delay: 0.4s; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Persistent Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-3xl font-extrabold tracking-tight text-white">SpinSleeve</h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">BETA v2</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Multi-tenant edition • Personal vinyl crate &amp; gatefold archive</p>
            </div>
            
            <!-- User Status & Quick Audio Toggle -->
            <div class="flex flex-wrap items-center gap-3">
                <button id="audioToggleBtn" onclick="toggleHoverAudio()"
                        class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 text-gray-300 hover:text-white flex items-center gap-1.5 transition">
                    <span id="audioIcon">🔊</span> <span id="audioText">Hover Audio: ON</span>
                </button>
                {% if is_admin %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <div class="flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5">
                    <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 shrink-0">
                        <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                    </div>
                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_admin or is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        {% if is_impersonating %}
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition">↩ Revert</a>
                        {% else %}
                        <span class="text-[10px] text-gray-500 font-bold">Switch:</span>
                        {% if user.user_id != 'sergebou' %}
                        <a href="/beta/dev-switch/sergebou" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold ml-1 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded transition">👑 Serge</a>
                        {% endif %}
                        {% if user.user_id != 'sarahboosch' %}
                        <a href="/beta/dev-switch/sarahboosch" class="text-[10px] text-rose-400 hover:text-rose-300 font-bold ml-1 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded transition">👩 Sarah</a>
                        {% endif %}
                        {% if user.user_id != '31sevhztrcbajfcowsahl7z2p26q' %}
                        <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="text-[10px] text-amber-400 hover:text-amber-300 font-bold ml-1 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded transition">🐹 GuineaPig</a>
                        {% endif %}
                        {% endif %}
                    </div>
                    {% endif %}
                    <a href="/beta/logout" class="text-[11px] text-gray-400 hover:text-white ml-1.5 transition">Logout</a>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/beta/recommend" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📻</span> Crate Digger
            </a>
            <a href="/beta/analytics" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📊</span> Analytics
            </a>
            <a href="/beta/pals" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>{% if is_admin or user.pals_opt_in %}🤝{% else %}🔒{% endif %}</span> SpinPals
            </a>
        </nav>

        <!-- Filter Controls Toolbar -->
        <div class="card-bg p-4 rounded-xl border border-gray-800 mb-6 shadow-sm">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 items-center">
                <div class="relative lg:col-span-2">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">🔍</span>
                    <input type="text" id="searchInput" placeholder="Search your albums or artists..."
                           class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#1DB954] transition"
                           oninput="onFilterChange()">
                </div>

                <div>
                    <select id="genreSelect" onchange="onFilterChange()"
                            class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition">
                        <option value="all">All Genres</option>
                        {% for g in top_genres %}
                        <option value="{{ g }}">{{ g.title() }}</option>
                        {% endfor %}
                    </select>
                </div>

                <div>
                    <select id="sortSelect" onchange="onFilterChange()"
                            class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition">
                        <option value="plays_desc">Most Played</option>
                        <option value="plays_asc">Least Played / Unplayed</option>
                        <option value="added_desc">Recently Added</option>
                        <option value="year_desc">Release Year (Newest)</option>
                        <option value="artist_asc">Artist (A-Z)</option>
                        <option value="artist_albums_desc">Artist (A-Z), Albums (Year desc)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Album Grid -->
        <div id="albumGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4"></div>

        <div id="loadMoreTrigger" class="text-center py-10">
            <span class="text-xs text-gray-500">Showing <span id="displayedCount">0</span> of <span id="totalMatchCount">0</span> albums</span>
        </div>
    </div>

    <!-- Pinned Preview Toast -->
    <div id="previewToast" class="fixed bottom-6 right-6 z-40 bg-[#161a22]/95 border border-emerald-500/30 rounded-2xl p-3.5 shadow-2xl backdrop-blur-md flex items-center gap-3.5 max-w-sm transition-all duration-300 translate-y-28 opacity-0 pointer-events-none">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0">
            <div class="flex items-end gap-0.5 h-3">
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <p id="toastTrack" class="text-xs font-bold text-white truncate">Preview Snippet</p>
            <p id="toastArtist" class="text-[11px] text-gray-400 truncate">--</p>
        </div>
        <button onclick="stopPreview()" class="text-gray-400 hover:text-white p-1 text-sm font-bold">&times;</button>
    </div>

    <!-- 12" Gatefold Modal Markup -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6" onclick="onModalBackdropClick(event)">
        <div class="relative w-full max-w-5xl bg-[#14181f] border border-gray-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row h-[88vh] md:h-[640px]" onclick="event.stopPropagation()">
            <!-- LEFT PANEL: 12" Vinyl Jacket (Desktop) / Compact Header (Mobile <110px) -->
            <div class="w-full md:w-5/12 bg-black/40 p-3 sm:p-4 md:p-6 flex flex-col justify-between border-b md:border-b-0 md:border-r border-gray-800/80 shrink-0">
                <!-- Mobile Compact Header (<md: <110px height without scrolling) -->
                <div class="md:hidden flex items-center justify-between gap-3 w-full">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-16 h-16 rounded-xl overflow-hidden shadow-lg border border-gray-800 shrink-0">
                            <img id="modalCoverMobile" src="" class="w-full h-full object-cover" alt="Album Cover">
                        </div>
                        <div class="min-w-0">
                            <span class="text-[9px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-bold uppercase inline-block mb-0.5">12" Gatefold</span>
                            <h3 id="modalTitleMobile" class="text-sm font-bold text-white truncate leading-snug">--</h3>
                            <p id="modalArtistMobile" class="text-xs font-semibold text-emerald-400 truncate">--</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <a id="modalSpotifyLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Play on Spotify" class="w-8 h-8 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        </a>
                        <a id="modalAppleMusicLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Listen on Apple Music" class="w-8 h-8 rounded-full bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        </a>
                        <button onclick="closeGatefold()" class="w-8 h-8 rounded-full bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white flex items-center justify-center text-lg font-bold transition">&times;</button>
                    </div>
                </div>

                <!-- Desktop Full Jacket (>md) -->
                <div class="hidden md:flex w-full justify-between items-center mb-3">
                    <span class="text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-bold uppercase">12" Gatefold Edition</span>
                </div>
                <div class="hidden md:block w-56 h-56 lg:w-64 lg:h-64 rounded-2xl overflow-hidden shadow-2xl border border-gray-800 my-auto mx-auto shrink-0">
                    <img id="modalCover" src="" class="w-full h-full object-cover" alt="Album Cover">
                </div>
                <div class="hidden md:flex w-full mt-4 flex-col gap-2">
                    <a id="modalSpotifyLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        <span>Play on Spotify</span>
                    </a>
                    <a id="modalAppleMusicLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 font-bold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        <span>Open in Apple Music</span>
                    </a>
                </div>
            </div>

            <!-- RIGHT PANEL: Gatefold Liner Notes, Audio Scrubber & Archival Review Badges -->
            <div class="w-full md:w-7/12 p-3 sm:p-4 md:p-6 flex flex-col justify-between overflow-y-auto custom-scroll flex-1">
                <div>
                    <!-- Audio Scrubber & Player Bar -->
                    <div id="gatefoldAudioBar" class="mb-4 p-3 rounded-2xl bg-black/40 border border-gray-800 flex flex-col gap-2">
                        <div class="flex items-center justify-between gap-3">
                            <div class="flex items-center gap-3 min-w-0">
                                <button id="gatefoldPlayBtn" onclick="toggleModalAudioPlayback()"
                                        class="w-9 h-9 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center shrink-0 transition shadow-lg">
                                    <span id="gatefoldPlayIcon" class="text-xs">▶</span>
                                </button>
                                <div class="min-w-0">
                                    <p id="gatefoldAudioTrack" class="text-xs font-bold text-white truncate">30-Second Audio Preview</p>
                                    <p id="gatefoldAudioSubtext" class="text-[10px] text-gray-400">iTunes Audio Snippet</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span id="gatefoldAudioTime" class="text-[10px] font-mono text-gray-400">0:00 / 0:30</span>
                                <div id="gatefoldWaveform" class="hidden items-end gap-0.5 h-3.5 pr-1">
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                </div>
                            </div>
                        </div>
                        <!-- Scrubber Track -->
                        <div id="gatefoldScrubber" class="relative w-full bg-gray-800/80 hover:bg-gray-700/80 h-2 rounded-full overflow-hidden cursor-pointer transition-colors"
                             onpointerdown="seekGatefoldAudio(event)">
                            <div id="gatefoldProgressBar" class="h-full bg-[#1DB954] rounded-full w-0 transition-[width] duration-100 pointer-events-none"></div>
                        </div>
                    </div>

                    <!-- Desktop Title & Artist (md:flex) -->
                    <div class="hidden md:flex items-start justify-between gap-4 mb-2">
                        <div>
                            <h3 id="modalTitle" class="text-xl md:text-2xl font-black text-white leading-tight">--</h3>
                            <p id="modalArtist" class="text-sm font-semibold text-emerald-400 mt-0.5">--</p>
                        </div>
                        <button onclick="closeGatefold()" class="text-gray-400 hover:text-white p-1 text-2xl font-bold">&times;</button>
                    </div>

                    <!-- Archival Badges with External Deep Links -->
                    <div id="modalScores" class="flex flex-wrap items-center gap-2 my-3"></div>

                    <!-- Liner Notes & Personnel -->
                    <div class="space-y-4 text-xs text-gray-300 leading-relaxed mt-4">
                        <div id="modalDescriptionSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Album Narrative &amp; Critical Reception</h4>
                            <p id="modalDescription" class="italic text-gray-300">--</p>
                        </div>
                        <div id="modalPersonnelSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Production &amp; Personnel Credits</h4>
                            <div id="modalPersonnel" class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] text-gray-400"></div>
                        </div>
                    </div>
                </div>

                <!-- Footer with Meta Info and SpinSleeve Verified -->
                <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-[11px] text-gray-500">
                    <span id="modalMetaInfo">--</span>
                    <span class="text-emerald-500 font-mono font-semibold flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        SpinSleeve Verified
                    </span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let filteredAlbums = [...ALL_ALBUMS];
        let displayLimit = 48;

        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = true;
        let isModalOpen = false;
        let currentModalAlbum = null;
        const previewUrlCache = new Map();

        activeAudio.volume = 0.75;
        activeAudio.addEventListener('ended', () => {
            hidePreviewToast();
            updateModalPlayIcon(false);
        });

        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                btnText.innerText = 'Hover Audio: ON';
                btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                btnText.innerText = 'Hover Audio: MUTED';
                btnIcon.innerText = '🔇';
            }
        }

        function onCardHover(artist, album, spotifyUrl, cardEl) {
            if (!isAudioEnabled || isModalOpen) return;
            const key = `${artist.toLowerCase()}::${album.toLowerCase()}`;
            currentHoverKey = key;

            if (hoverTimer) clearTimeout(hoverTimer);

            hoverTimer = setTimeout(async () => {
                if (currentHoverKey !== key) return;

                let data = previewUrlCache.get(key);
                if (!data) {
                    try {
                        const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}`);
                        data = await res.json();
                        previewUrlCache.set(key, data);
                    } catch (e) {
                        return;
                    }
                }

                if (currentHoverKey !== key) return;

                if (data && data.preview_url) {
                    activeAudio.src = data.preview_url;
                    activeAudio.play().then(() => {
                        showPreviewToast(artist, album, data.track_name || 'Preview Snippet', data.apple_music_url, spotifyUrl);
                        const pulse = cardEl.querySelector('.audio-pulse');
                        if (pulse) pulse.classList.remove('hidden');
                    }).catch(e => {});
                }
            }, 350);
        }

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            if (isModalOpen) return;
            currentHoverKey = null;
            stopPreview();
            if (cardEl) {
                const pulse = cardEl.querySelector('.audio-pulse');
                if (pulse) pulse.classList.add('hidden');
            }
        }

        function stopPreview() {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
            updateModalPlayIcon(false);
        }

        function showPreviewToast(artist, album, track, appleUrl, spotifyUrl) {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            document.getElementById('toastTrack').innerText = track;
            document.getElementById('toastArtist').innerText = `${artist} • ${album}`;
            toast.classList.remove('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.add('translate-y-0', 'opacity-100');
        }

        function hidePreviewToast() {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            toast.classList.add('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.remove('translate-y-0', 'opacity-100');
        }

        function renderGrid() {
            const grid = document.getElementById("albumGrid");
            const toShow = filteredAlbums.slice(0, displayLimit);
            document.getElementById("displayedCount").innerText = toShow.length;
            document.getElementById("totalMatchCount").innerText = filteredAlbums.length;

            if (toShow.length === 0) {
                grid.innerHTML = '<div class="col-span-full py-16 text-center text-gray-500 text-sm">No albums match your search filters.</div>';
                return;
            }

            grid.innerHTML = toShow.map(a => `
                <div class="group relative flex flex-col cursor-pointer"
                     onmouseenter="onCardHover('${a.album_artist_name.replace(/'/g, "\\\\'")}', '${a.album_name.replace(/'/g, "\\\\'")}', '${a.album_url}', this)"
                     onmouseleave="onCardLeave(this)"
                     onclick='openGatefold(${JSON.stringify(a).replace(/'/g, "&apos;")})'>
                    <div class="aspect-square w-full rounded-2xl overflow-hidden bg-gray-900 border border-gray-800/80 sleeve-shadow transition duration-300 group-hover:scale-[1.03] group-hover:border-gray-700 relative">
                        <img src="${a.album_image_url}" alt="${a.album_name}" class="w-full h-full object-cover">
                        ${a.has_gatefold ? `
                            <div class="absolute top-2 left-2 bg-black/75 backdrop-blur-md rounded-lg p-1.5 border border-white/10 shadow" title="12\\" Gatefold Liner Notes Available">
                                {{ gatefold_icon | safe }}
                            </div>
                        ` : ''}
                        <div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] font-black text-emerald-400">
                            ${a.album_track_plays || 0}
                        </div>
                        <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                        </div>
                    </div>
                    <div class="mt-2.5 px-0.5">
                        <h4 class="text-xs font-bold text-white truncate group-hover:text-emerald-400 transition" title="${a.album_name}">${a.album_name}</h4>
                        <p class="text-[11px] text-gray-400 truncate" title="${a.album_artist_name}">${a.album_artist_name}</p>
                        <p class="text-[10px] text-gray-500 mt-0.5">${a.release_year || ''}</p>
                    </div>
                </div>
            `).join('');
        }

        function onFilterChange() {
            const query = document.getElementById("searchInput").value.toLowerCase().trim();
            const genre = document.getElementById("genreSelect").value.toLowerCase();
            const sort = document.getElementById("sortSelect").value;

            filteredAlbums = ALL_ALBUMS.filter(a => {
                const matchQ = !query || a.album_name.toLowerCase().includes(query) || a.album_artist_name.toLowerCase().includes(query);
                const matchG = genre === "all" || (a.album_genres && a.album_genres.toLowerCase().includes(genre));
                return matchQ && matchG;
            });

            if (sort === "plays_desc") filteredAlbums.sort((a,b) => (b.album_track_plays||0) - (a.album_track_plays||0));
            else if (sort === "plays_asc") filteredAlbums.sort((a,b) => (a.album_track_plays||0) - (b.album_track_plays||0));
            else if (sort === "added_desc") filteredAlbums.sort((a,b) => (b.added_at||"").localeCompare(a.added_at||""));
            else if (sort === "year_desc") filteredAlbums.sort((a,b) => (b.release_year||0) - (a.release_year||0));
            else if (sort === "artist_asc") filteredAlbums.sort((a,b) => (a.album_artist_name||"").localeCompare(b.album_artist_name||""));
            else if (sort === "artist_albums_desc") {
                filteredAlbums.sort((a, b) => {
                    const artistA = (a.album_artist_name || "").toLowerCase();
                    const artistB = (b.album_artist_name || "").toLowerCase();
                    const cmp = artistA.localeCompare(artistB);
                    if (cmp !== 0) return cmp;
                    const yearA = parseInt(a.release_year) || 0;
                    const yearB = parseInt(b.release_year) || 0;
                    return yearB - yearA;
                });
            }

            displayLimit = 48;
            renderGrid();
        }

        async function openGatefold(album) {
            isModalOpen = true;
            currentModalAlbum = album;

            // Desktop elements
            const coverEl = document.getElementById("modalCover");
            if (coverEl) coverEl.src = album.album_image_url;
            const titleEl = document.getElementById("modalTitle");
            if (titleEl) titleEl.innerText = album.album_name;
            const artistEl = document.getElementById("modalArtist");
            if (artistEl) artistEl.innerText = album.album_artist_name;
            const spotEl = document.getElementById("modalSpotifyLink");
            if (spotEl) spotEl.href = album.album_url;

            // Mobile compact elements (<110px header)
            const coverMob = document.getElementById("modalCoverMobile");
            if (coverMob) coverMob.src = album.album_image_url;
            const titleMob = document.getElementById("modalTitleMobile");
            if (titleMob) titleMob.innerText = album.album_name;
            const artistMob = document.getElementById("modalArtistMobile");
            if (artistMob) artistMob.innerText = album.album_artist_name;
            const spotMob = document.getElementById("modalSpotifyLinkMobile");
            if (spotMob) spotMob.href = album.album_url;

            // Apple Music deep links
            const appleMusicUrl = `https://music.apple.com/search?term=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
            const appleEl = document.getElementById("modalAppleMusicLink");
            if (appleEl) appleEl.href = appleMusicUrl;
            const appleMob = document.getElementById("modalAppleMusicLinkMobile");
            if (appleMob) appleMob.href = appleMusicUrl;

            const key = `${album.album_artist_name.toLowerCase()}::${album.album_name.toLowerCase()}`;
            if (!activeAudio.paused && currentHoverKey === key) {
                updateModalPlayIcon(true);
                updateModalProgress();
            } else {
                updateModalPlayIcon(false);
                resetModalProgress();
            }

            let pData = previewUrlCache.get(key);
            if (!pData) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(album.album_artist_name)}&album=${encodeURIComponent(album.album_name)}`);
                    pData = await res.json();
                    previewUrlCache.set(key, pData);
                } catch(e){}
            }
            if (pData && pData.track_name) {
                document.getElementById('gatefoldAudioTrack').innerText = pData.track_name;
            } else {
                document.getElementById('gatefoldAudioTrack').innerText = '30-Second Audio Preview';
            }

            const scoresContainer = document.getElementById("modalScores");
            scoresContainer.innerHTML = '';
            if (album.pitchfork_score) {
                const pfUrl = album.pitchfork_url || `https://pitchfork.com/search/?query=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${pfUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Review on Pitchfork"
                       class="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Pitchfork ${album.pitchfork_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.discogs_rating) {
                const discUrl = album.discogs_url || `https://www.discogs.com/search/?q=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}&type=release`;
                const votes = album.discogs_votes ? ` (${album.discogs_votes.toLocaleString()} votes)` : '';
                scoresContainer.innerHTML += `
                    <a href="${discUrl}" target="_blank" rel="noopener noreferrer"
                       title="View Pressings on Discogs${votes}"
                       class="px-2.5 py-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 border border-blue-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Discogs ${album.discogs_rating} ★</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.metacritic_score) {
                const mcUrl = `https://www.metacritic.com/search/${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}/?page=1&category=1`;
                scoresContainer.innerHTML += `
                    <a href="${mcUrl}" target="_blank" rel="noopener noreferrer"
                       title="View on Metacritic"
                       class="px-2.5 py-1 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 hover:text-yellow-300 border border-yellow-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Metacritic ${album.metacritic_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.wikipedia_url || album.album_description) {
                const wikiUrl = album.wikipedia_url || `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${wikiUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Wikipedia Article"
                       class="px-2.5 py-1 bg-gray-500/10 hover:bg-gray-500/20 text-gray-300 hover:text-white border border-gray-600/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Wikipedia</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }

            const descEl = document.getElementById("modalDescription");
            descEl.innerText = album.album_description || "No archival liner notes found for this release yet.";

            const personnelEl = document.getElementById("modalPersonnel");
            if (album.personnel && album.personnel.length > 0) {
                personnelEl.innerHTML = album.personnel.map(p => `<div>• ${p}</div>`).join('');
                document.getElementById("modalPersonnelSection").classList.remove("hidden");
            } else {
                document.getElementById("modalPersonnelSection").classList.add("hidden");
            }

            document.getElementById("modalMetaInfo").innerText = `${album.release_year || 'Unknown Year'} • ${album.album_tracks_total || 0} tracks • ${album.album_track_plays || 0} total plays`;
            document.getElementById("gatefoldModal").classList.remove("hidden");
        }

        async function toggleModalAudioPlayback() {
            if (!currentModalAlbum) return;
            const key = `${currentModalAlbum.album_artist_name.toLowerCase()}::${currentModalAlbum.album_name.toLowerCase()}`;

            if (!activeAudio.paused && currentHoverKey === key) {
                activeAudio.pause();
                updateModalPlayIcon(false);
                return;
            }

            let data = previewUrlCache.get(key);
            if (!data) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(currentModalAlbum.album_artist_name)}&album=${encodeURIComponent(currentModalAlbum.album_name)}`);
                    data = await res.json();
                    previewUrlCache.set(key, data);
                } catch(e) { return; }
            }

            if (data && data.preview_url) {
                currentHoverKey = key;
                activeAudio.src = data.preview_url;
                activeAudio.play().then(() => {
                    updateModalPlayIcon(true);
                    updateModalProgress();
                }).catch(e => {});
            }
        }

        function seekGatefoldAudio(e) {
            if (!activeAudio || !activeAudio.duration || isNaN(activeAudio.duration) || activeAudio.duration <= 0) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
            const clickX = clientX - rect.left;
            const pct = Math.max(0, Math.min(1, clickX / rect.width));
            activeAudio.currentTime = pct * activeAudio.duration;
            updateModalProgress();
        }

        function updateModalProgress() {
            const cur = activeAudio.currentTime || 0;
            const dur = (activeAudio.duration && !isNaN(activeAudio.duration) && activeAudio.duration > 0) ? activeAudio.duration : 30;
            const pct = Math.min(100, Math.max(0, (cur / dur) * 100));
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = `${pct}%`;
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) {
                const curSec = Math.floor(cur);
                const durSec = Math.floor(dur);
                timeEl.innerText = `0:${curSec < 10 ? '0' : ''}${curSec} / 0:${durSec < 10 ? '0' : ''}${durSec}`;
            }
        }

        function resetModalProgress() {
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = '0%';
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) timeEl.innerText = '0:00 / 0:30';
        }

        activeAudio.addEventListener('timeupdate', () => {
            if (isModalOpen) updateModalProgress();
        });
        activeAudio.addEventListener('ended', () => {
            resetModalProgress();
        });

        function updateModalPlayIcon(isPlaying) {
            const icon = document.getElementById('gatefoldPlayIcon');
            const wave = document.getElementById('gatefoldWaveform');
            if (!icon || !wave) return;
            if (isPlaying) {
                icon.innerText = '❚❚';
                wave.classList.remove('hidden');
                wave.classList.add('flex');
            } else {
                icon.innerText = '▶';
                wave.classList.remove('flex');
                wave.classList.add('hidden');
            }
        }

        function closeGatefold() {
            isModalOpen = false;
            currentModalAlbum = null;
            document.getElementById("gatefoldModal").classList.add("hidden");
            stopPreview();
            resetModalProgress();
        }

        function onModalBackdropClick(e) {
            closeGatefold();
        }

        window.addEventListener("scroll", () => {
            if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 500) {
                if (displayLimit < filteredAlbums.length) {
                    displayLimit += 36;
                    renderGrid();
                }
            }
        });

        document.addEventListener("DOMContentLoaded", () => {
            renderGrid();
        });
    </script>
</body>
</html>
"""


# ==============================================================================
# 2. TAB 2: CRATE DIGGER ROUTE & TEMPLATE
# ==============================================================================
@app.route("/recommend")
@app.route("/beta/recommend")
@login_required
def beta_recommend():
    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    return render_template_string(
        BETA_RECOMMEND_HTML,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


BETA_RECOMMEND_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Crate Digger</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #14181f; }
        .serif-title { font-family: 'Playfair Display', serif; }
        .sleeve-shadow { box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.6); }
        .custom-scroll::-webkit-scrollbar { width: 5px; }
        .custom-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
        .pill-active { background-color: #1DB954; color: #000; font-weight: 700; }
        .pill-inactive { background-color: #1a2027; color: #9ca3af; border: 1px solid #28323c; }
        .pill-inactive:hover { background-color: #28323c; color: #fff; }
        @keyframes soundWave { 0%, 100% { height: 4px; } 50% { height: 16px; } }
        .wave-bar { animation: soundWave 1.2s ease-in-out infinite; }
        .wave-bar:nth-child(2) { animation-delay: 0.2s; }
        .wave-bar:nth-child(3) { animation-delay: 0.4s; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Persistent Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-3xl font-extrabold tracking-tight text-white">SpinSleeve</h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">CRATE DIGGER</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Smart crate digging &amp; personalized discovery based on {{ user.display_name }}'s library</p>
            </div>
            
            <div class="flex flex-wrap items-center gap-3">
                <button id="audioToggleBtn" onclick="toggleHoverAudio()"
                        class="text-xs font-semibold px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800/80 text-gray-300 hover:text-white flex items-center gap-1.5 transition">
                    <span id="audioIcon">🔊</span> <span id="audioText">Hover Audio: ON</span>
                </button>
                <button onclick="spinAgain()" class="text-xs font-bold text-black bg-[#1DB954] hover:bg-[#1ed760] px-4 py-2 rounded-lg transition shadow-md flex items-center gap-1.5">
                    <span>🎲</span> Spin Again
                </button>
                {% if is_admin %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <div class="flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5">
                    <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 shrink-0">
                        <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                    </div>
                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_admin or is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        {% if is_impersonating %}
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition">↩ Revert</a>
                        {% else %}
                        <span class="text-[10px] text-gray-500 font-bold">Switch:</span>
                        {% if user.user_id != 'sergebou' %}
                        <a href="/beta/dev-switch/sergebou" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold ml-1 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded transition">👑 Serge</a>
                        {% endif %}
                        {% if user.user_id != 'sarahboosch' %}
                        <a href="/beta/dev-switch/sarahboosch" class="text-[10px] text-rose-400 hover:text-rose-300 font-bold ml-1 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded transition">👩 Sarah</a>
                        {% endif %}
                        {% if user.user_id != '31sevhztrcbajfcowsahl7z2p26q' %}
                        <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="text-[10px] text-amber-400 hover:text-amber-300 font-bold ml-1 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded transition">🐹 GuineaPig</a>
                        {% endif %}
                        {% endif %}
                    </div>
                    {% endif %}
                    <a href="/beta/logout" class="text-[11px] text-gray-400 hover:text-white ml-1.5 transition">Logout</a>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/beta/recommend" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📻</span> Crate Digger
            </a>
            <a href="/beta/analytics" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📊</span> Analytics
            </a>
            <a href="/beta/pals" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>{% if is_admin or user.pals_opt_in %}🤝{% else %}🔒{% endif %}</span> SpinPals
            </a>
        </nav>

        <!-- Control Deck -->
        <div class="card-bg p-5 rounded-2xl border border-gray-800 mb-8 shadow-lg">
            <div class="space-y-4">
                <div>
                    <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">1. Listening Mode</label>
                    <div class="flex flex-wrap gap-2.5">
                        <button onclick="setMode('discover')" id="modeBtn-discover" class="pill-active px-4 py-2 rounded-xl text-xs transition flex items-center gap-2">
                            <span>🔍</span> Discover (Never Played: {{ kpis.unplayed_albums }} albums)
                        </button>
                        <button onclick="setMode('favorites')" id="modeBtn-favorites" class="pill-inactive px-4 py-2 rounded-xl text-xs transition flex items-center gap-2">
                            <span>⭐</span> Favorites (Heavy Rotation: {{ kpis.played_albums }} albums)
                        </button>
                    </div>
                </div>

                <div>
                    <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">2. Mood &amp; Vibe</label>
                    <div class="flex flex-wrap gap-2">
                        <button onclick="setVibe('all')" id="vibeBtn-all" class="pill-active px-3.5 py-1.5 rounded-lg text-xs transition">🌌 Any Vibe</button>
                        <button onclick="setVibe('chill')" id="vibeBtn-chill" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">🌙 Late Night / Chill</button>
                        <button onclick="setVibe('energetic')" id="vibeBtn-energetic" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">⚡ Energetic / Focus</button>
                        <button onclick="setVibe('mellow')" id="vibeBtn-mellow" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">☕ Mellow / Acoustic</button>
                        <button onclick="setVibe('vintage')" id="vibeBtn-vintage" class="pill-inactive px-3.5 py-1.5 rounded-lg text-xs transition">📻 Vintage Classics</button>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-gray-800/80">
                    <div>
                        <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">3. Era Preference</label>
                        <div class="flex flex-wrap gap-2">
                            <button onclick="setEra('all')" id="eraBtn-all" class="pill-active px-3 py-1.5 rounded-lg text-xs transition">Any Era</button>
                            <button onclick="setEra('recent')" id="eraBtn-recent" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">✨ Recent (2018+)</button>
                            <button onclick="setEra('modern')" id="eraBtn-modern" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">💿 2000s &amp; 2010s</button>
                            <button onclick="setEra('classic')" id="eraBtn-classic" class="pill-inactive px-3 py-1.5 rounded-lg text-xs transition">📼 Vintage (&lt; 2000)</button>
                        </div>
                    </div>
                    <div>
                        <label class="text-[11px] font-bold uppercase tracking-wider text-gray-400 block mb-2">4. Specific Sub-Genre (Optional)</label>
                        <select id="genreSelect" onchange="onGenreSelect(this.value)" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg p-2 text-xs text-gray-200 focus:outline-none focus:border-[#1DB954]">
                            <option value="">Any Genre</option>
                            {% for g in top_genres %}
                            <option value="{{ g }}">{{ g|title }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
            </div>
        </div>

        <div class="mb-10">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-[#1DB954] animate-pulse"></span>
                    <h2 class="text-xl font-black text-white tracking-tight">Top 3 Spotlight Picks For You</h2>
                </div>
                <div class="text-xs text-gray-400">
                    <span id="poolCountText">Calculating candidates...</span>
                </div>
            </div>

            <div id="spotlightContainer" class="grid grid-cols-1 md:grid-cols-3 gap-5"></div>
        </div>

        <div>
            <div class="flex items-center justify-between mb-4 pb-2 border-b border-gray-800">
                <h3 class="text-sm font-bold uppercase tracking-wider text-gray-300">All Matching Candidates</h3>
                <span class="text-xs text-gray-500" id="candidateSubtext"></span>
            </div>
            <div id="candidatePoolGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4"></div>
        </div>
    </div>

    <!-- Pinned Preview Toast -->
    <div id="previewToast" class="fixed bottom-6 right-6 z-40 bg-[#161a22]/95 border border-emerald-500/30 rounded-2xl p-3.5 shadow-2xl backdrop-blur-md flex items-center gap-3.5 max-w-sm transition-all duration-300 translate-y-28 opacity-0 pointer-events-none">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0">
            <div class="flex items-end gap-0.5 h-3">
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <p id="toastTrack" class="text-xs font-bold text-white truncate">Preview Snippet</p>
            <p id="toastArtist" class="text-[11px] text-gray-400 truncate">--</p>
        </div>
        <button onclick="stopPreview()" class="text-gray-400 hover:text-white p-1 text-sm font-bold">&times;</button>
    </div>

    <!-- 12" Gatefold Modal Markup -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6" onclick="onModalBackdropClick(event)">
        <div class="relative w-full max-w-5xl bg-[#14181f] border border-gray-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row h-[88vh] md:h-[640px]" onclick="event.stopPropagation()">
            <!-- LEFT PANEL: 12" Vinyl Jacket (Desktop) / Compact Header (Mobile <110px) -->
            <div class="w-full md:w-5/12 bg-black/40 p-3 sm:p-4 md:p-6 flex flex-col justify-between border-b md:border-b-0 md:border-r border-gray-800/80 shrink-0">
                <!-- Mobile Compact Header (<md: <110px height without scrolling) -->
                <div class="md:hidden flex items-center justify-between gap-3 w-full">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-16 h-16 rounded-xl overflow-hidden shadow-lg border border-gray-800 shrink-0">
                            <img id="modalCoverMobile" src="" class="w-full h-full object-cover" alt="Album Cover">
                        </div>
                        <div class="min-w-0">
                            <span class="text-[9px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-bold uppercase inline-block mb-0.5">12" Gatefold</span>
                            <h3 id="modalTitleMobile" class="text-sm font-bold text-white truncate leading-snug">--</h3>
                            <p id="modalArtistMobile" class="text-xs font-semibold text-emerald-400 truncate">--</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <a id="modalSpotifyLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Play on Spotify" class="w-8 h-8 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        </a>
                        <a id="modalAppleMusicLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Listen on Apple Music" class="w-8 h-8 rounded-full bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        </a>
                        <button onclick="closeGatefold()" class="w-8 h-8 rounded-full bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white flex items-center justify-center text-lg font-bold transition">&times;</button>
                    </div>
                </div>

                <!-- Desktop Full Jacket (>md) -->
                <div class="hidden md:flex w-full justify-between items-center mb-3">
                    <span class="text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-bold uppercase">12" Gatefold Edition</span>
                </div>
                <div class="hidden md:block w-56 h-56 lg:w-64 lg:h-64 rounded-2xl overflow-hidden shadow-2xl border border-gray-800 my-auto mx-auto shrink-0">
                    <img id="modalCover" src="" class="w-full h-full object-cover" alt="Album Cover">
                </div>
                <div class="hidden md:flex w-full mt-4 flex-col gap-2">
                    <a id="modalSpotifyLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        <span>Play on Spotify</span>
                    </a>
                    <a id="modalAppleMusicLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 font-bold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        <span>Open in Apple Music</span>
                    </a>
                </div>
            </div>

            <!-- RIGHT PANEL: Gatefold Liner Notes, Audio Scrubber & Archival Review Badges -->
            <div class="w-full md:w-7/12 p-3 sm:p-4 md:p-6 flex flex-col justify-between overflow-y-auto custom-scroll flex-1">
                <div>
                    <!-- Audio Scrubber & Player Bar -->
                    <div id="gatefoldAudioBar" class="mb-4 p-3 rounded-2xl bg-black/40 border border-gray-800 flex flex-col gap-2">
                        <div class="flex items-center justify-between gap-3">
                            <div class="flex items-center gap-3 min-w-0">
                                <button id="gatefoldPlayBtn" onclick="toggleModalAudioPlayback()"
                                        class="w-9 h-9 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center shrink-0 transition shadow-lg">
                                    <span id="gatefoldPlayIcon" class="text-xs">▶</span>
                                </button>
                                <div class="min-w-0">
                                    <p id="gatefoldAudioTrack" class="text-xs font-bold text-white truncate">30-Second Audio Preview</p>
                                    <p id="gatefoldAudioSubtext" class="text-[10px] text-gray-400">iTunes Audio Snippet</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span id="gatefoldAudioTime" class="text-[10px] font-mono text-gray-400">0:00 / 0:30</span>
                                <div id="gatefoldWaveform" class="hidden items-end gap-0.5 h-3.5 pr-1">
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                </div>
                            </div>
                        </div>
                        <!-- Scrubber Track -->
                        <div id="gatefoldScrubber" class="relative w-full bg-gray-800/80 hover:bg-gray-700/80 h-2 rounded-full overflow-hidden cursor-pointer transition-colors"
                             onpointerdown="seekGatefoldAudio(event)">
                            <div id="gatefoldProgressBar" class="h-full bg-[#1DB954] rounded-full w-0 transition-[width] duration-100 pointer-events-none"></div>
                        </div>
                    </div>

                    <!-- Desktop Title & Artist (md:flex) -->
                    <div class="hidden md:flex items-start justify-between gap-4 mb-2">
                        <div>
                            <h3 id="modalTitle" class="text-xl md:text-2xl font-black text-white leading-tight">--</h3>
                            <p id="modalArtist" class="text-sm font-semibold text-emerald-400 mt-0.5">--</p>
                        </div>
                        <button onclick="closeGatefold()" class="text-gray-400 hover:text-white p-1 text-2xl font-bold">&times;</button>
                    </div>

                    <!-- Archival Badges with External Deep Links -->
                    <div id="modalScores" class="flex flex-wrap items-center gap-2 my-3"></div>

                    <!-- Liner Notes & Personnel -->
                    <div class="space-y-4 text-xs text-gray-300 leading-relaxed mt-4">
                        <div id="modalDescriptionSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Album Narrative &amp; Critical Reception</h4>
                            <p id="modalDescription" class="italic text-gray-300">--</p>
                        </div>
                        <div id="modalPersonnelSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Production &amp; Personnel Credits</h4>
                            <div id="modalPersonnel" class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] text-gray-400"></div>
                        </div>
                    </div>
                </div>

                <!-- Footer with Meta Info and SpinSleeve Verified -->
                <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-[11px] text-gray-500">
                    <span id="modalMetaInfo">--</span>
                    <span class="text-emerald-500 font-mono font-semibold flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        SpinSleeve Verified
                    </span>
                </div>
            </div>
        </div>
    </div>

    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let selectedMode = 'discover';
        let selectedVibe = 'all';
        let selectedEra = 'all';
        let selectedGenre = '';
        let currentSeed = Math.random();

        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = true;
        let isModalOpen = false;
        let currentModalAlbum = null;
        const previewUrlCache = new Map();

        activeAudio.volume = 0.75;
        activeAudio.addEventListener('ended', () => {
            hidePreviewToast();
            updateModalPlayIcon(false);
        });

        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                btnText.innerText = 'Hover Audio: ON';
                btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                btnText.innerText = 'Hover Audio: MUTED';
                btnIcon.innerText = '🔇';
            }
        }

        function onCardHover(artist, album, spotifyUrl, cardEl) {
            if (!isAudioEnabled || isModalOpen) return;
            const key = `${artist.toLowerCase()}::${album.toLowerCase()}`;
            currentHoverKey = key;

            if (hoverTimer) clearTimeout(hoverTimer);

            hoverTimer = setTimeout(async () => {
                if (currentHoverKey !== key) return;

                let data = previewUrlCache.get(key);
                if (!data) {
                    try {
                        const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}`);
                        data = await res.json();
                        previewUrlCache.set(key, data);
                    } catch (e) { return; }
                }

                if (currentHoverKey !== key) return;

                if (data && data.preview_url) {
                    activeAudio.src = data.preview_url;
                    activeAudio.play().then(() => {
                        showPreviewToast(artist, album, data.track_name || 'Preview Snippet', data.apple_music_url, spotifyUrl);
                        const pulse = cardEl.querySelector('.audio-pulse');
                        if (pulse) pulse.classList.remove('hidden');
                    }).catch(e => {});
                }
            }, 350);
        }

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            if (isModalOpen) return;
            currentHoverKey = null;
            stopPreview();
            if (cardEl) {
                const pulse = cardEl.querySelector('.audio-pulse');
                if (pulse) pulse.classList.add('hidden');
            }
        }

        function stopPreview() {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
            updateModalPlayIcon(false);
        }

        function showPreviewToast(artist, album, track, appleUrl, spotifyUrl) {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            document.getElementById('toastTrack').innerText = track;
            document.getElementById('toastArtist').innerText = `${artist} • ${album}`;
            toast.classList.remove('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.add('translate-y-0', 'opacity-100');
        }

        function hidePreviewToast() {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            toast.classList.add('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.remove('translate-y-0', 'opacity-100');
        }

        const VIBES = {
            chill: ['ambient', 'chill', 'downtempo', 'lo-fi', 'dream pop', 'slowcore', 'post-rock', 'minimalism'],
            energetic: ['punk', 'electronic', 'rock', 'dance', 'techno', 'house', 'hip hop', 'funk', 'post-punk'],
            mellow: ['folk', 'acoustic', 'singer-songwriter', 'indie folk', 'jazz', 'soul', 'bossa nova'],
            vintage: ['classic rock', 'soul', 'psychedelic', 'blues', 'funk', 'motown', 'vintage', '60s', '70s', '80s']
        };

        function setMode(mode) {
            selectedMode = mode;
            document.getElementById('modeBtn-discover').className = (mode === 'discover' ? 'pill-active' : 'pill-inactive') + ' px-4 py-2 rounded-xl text-xs transition flex items-center gap-2';
            document.getElementById('modeBtn-favorites').className = (mode === 'favorites' ? 'pill-active' : 'pill-inactive') + ' px-4 py-2 rounded-xl text-xs transition flex items-center gap-2';
            runRecommender();
        }

        function setVibe(vibe) {
            selectedVibe = vibe;
            ['all', 'chill', 'energetic', 'mellow', 'vintage'].forEach(v => {
                const btn = document.getElementById(`vibeBtn-${v}`);
                if (btn) btn.className = (v === vibe ? 'pill-active' : 'pill-inactive') + ' px-3.5 py-1.5 rounded-lg text-xs transition';
            });
            runRecommender();
        }

        function setEra(era) {
            selectedEra = era;
            ['all', 'recent', 'modern', 'classic'].forEach(e => {
                const btn = document.getElementById(`eraBtn-${e}`);
                if (btn) btn.className = (e === era ? 'pill-active' : 'pill-inactive') + ' px-3 py-1.5 rounded-lg text-xs transition';
            });
            runRecommender();
        }

        function onGenreSelect(g) {
            selectedGenre = g.toLowerCase();
            runRecommender();
        }

        function spinAgain() {
            currentSeed = Math.random();
            runRecommender();
        }

        function seededScore(album, index) {
            let score = 50;
            const seedFactor = Math.sin((index + 1) * 997 + currentSeed * 1000) * 20;
            score += seedFactor;

            if (selectedVibe !== 'all') {
                const keywords = VIBES[selectedVibe] || [];
                const gStr = (album.album_genres || '').toLowerCase();
                const matched = keywords.filter(k => gStr.includes(k)).length;
                score += matched * 18;
            }

            if (album.has_gatefold) score += 12;

            if (selectedMode === 'discover') {
                const plays = album.album_track_plays || 0;
                if (plays === 0) score += 30;
                else score -= plays * 2;
            } else {
                const plays = album.album_track_plays || 0;
                score += Math.min(plays * 2.5, 35);
            }

            return score;
        }

        function runRecommender() {
            let pool = ALL_ALBUMS.filter(a => {
                if (selectedMode === 'discover' && (a.album_track_plays || 0) > 0) return false;
                if (selectedMode === 'favorites' && (a.album_track_plays || 0) === 0) return false;

                const year = parseInt(a.release_year) || 0;
                if (selectedEra === 'recent' && year < 2018) return false;
                if (selectedEra === 'modern' && (year < 2000 || year >= 2018)) return false;
                if (selectedEra === 'classic' && (year <= 0 || year >= 2000)) return false;

                if (selectedGenre && !(a.album_genres && a.album_genres.toLowerCase().includes(selectedGenre))) {
                    return false;
                }

                if (selectedVibe !== 'all') {
                    const keywords = VIBES[selectedVibe] || [];
                    const gStr = (a.album_genres || '').toLowerCase();
                    const hasVibe = keywords.some(k => gStr.includes(k));
                    if (!hasVibe) return false;
                }

                return true;
            });

            document.getElementById('poolCountText').innerText = `${pool.length.toLocaleString()} matching records in your library`;

            const scored = pool.map((album, idx) => ({
                album: album,
                score: seededScore(album, idx)
            })).sort((a, b) => b.score - a.score);

            const topPicks = scored.slice(0, 3).map(s => s.album);
            const remainingPool = scored.slice(3, 48).map(s => s.album);

            renderSpotlight(topPicks);
            renderCandidatePool(remainingPool);
        }

        function renderSpotlight(albums) {
            const container = document.getElementById('spotlightContainer');
            if (albums.length === 0) {
                container.innerHTML = '<div class="col-span-3 py-10 text-center text-gray-500 text-xs">No records match your selected vibe & era filters. Try choosing "Any Vibe" or "Any Era".</div>';
                return;
            }

            const badges = [
                { icon: '🥇', label: 'Prime Selection', color: 'from-emerald-500/20 to-transparent' },
                { icon: '🥈', label: 'Vibe Match', color: 'from-blue-500/20 to-transparent' },
                { icon: '🥉', label: 'Hidden Gem', color: 'from-amber-500/20 to-transparent' }
            ];

            container.innerHTML = albums.map((a, i) => {
                const badge = badges[i] || badges[0];
                return `
                    <div class="card-bg border border-gray-800 rounded-3xl p-5 shadow-xl flex flex-col justify-between hover:border-gray-700 transition relative overflow-hidden group cursor-pointer"
                         onmouseenter="onCardHover('${a.album_artist_name.replace(/'/g, "\\\\'")}', '${a.album_name.replace(/'/g, "\\\\'")}', '${a.album_url}', this)"
                         onmouseleave="onCardLeave(this)"
                         onclick='openGatefold(${JSON.stringify(a).replace(/'/g, "&apos;")})'>
                        <div class="absolute inset-0 bg-gradient-to-b ${badge.color} opacity-40 pointer-events-none"></div>

                        <div class="flex items-center justify-between mb-4 relative z-10">
                            <span class="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                                <span>${badge.icon}</span> ${badge.label}
                            </span>
                            ${a.has_gatefold ? `
                                <div class="bg-black/60 rounded-lg p-1.5 border border-white/10" title="12\\" Gatefold Liner Notes Available">
                                    {{ gatefold_icon | safe }}
                                </div>
                            ` : ''}
                        </div>

                        <div class="aspect-square w-full rounded-2xl overflow-hidden bg-gray-900 border border-gray-800/80 mb-4 sleeve-shadow relative">
                            <img src="${a.album_image_url}" alt="${a.album_name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            </div>
                        </div>

                        <div class="relative z-10">
                            <h3 class="text-base font-black text-white truncate group-hover:text-emerald-400 transition" title="${a.album_name}">${a.album_name}</h3>
                            <p class="text-xs font-bold text-gray-400 truncate mt-0.5">${a.album_artist_name}</p>
                            <p class="text-[11px] text-gray-500 mt-1 truncate">${a.album_genres || 'Uncategorized'}</p>
                        </div>
                    </div>
                `;
            }).join('');
        }

        function renderCandidatePool(albums) {
            const grid = document.getElementById('candidatePoolGrid');
            document.getElementById('candidateSubtext').innerText = `${albums.length} more matching records`;

            if (albums.length === 0) {
                grid.innerHTML = '<div class="col-span-full py-6 text-center text-gray-600 text-xs">No further candidate records in this pool.</div>';
                return;
            }

            grid.innerHTML = albums.map(a => `
                <div class="group relative flex flex-col cursor-pointer"
                     onmouseenter="onCardHover('${a.album_artist_name.replace(/'/g, "\\\\'")}', '${a.album_name.replace(/'/g, "\\\\'")}', '${a.album_url}', this)"
                     onmouseleave="onCardLeave(this)"
                     onclick='openGatefold(${JSON.stringify(a).replace(/'/g, "&apos;")})'>
                    <div class="aspect-square w-full rounded-2xl overflow-hidden bg-gray-900 border border-gray-800/80 sleeve-shadow transition duration-300 group-hover:scale-[1.03] group-hover:border-gray-700 relative">
                        <img src="${a.album_image_url}" alt="${a.album_name}" class="w-full h-full object-cover">
                        ${a.has_gatefold ? `
                            <div class="absolute top-2 left-2 bg-black/75 backdrop-blur-md rounded-lg p-1.5 border border-white/10 shadow" title="12\\" Gatefold Liner Notes Available">
                                {{ gatefold_icon | safe }}
                            </div>
                        ` : ''}
                        <div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] font-black text-emerald-400">
                            ${a.album_track_plays || 0}
                        </div>
                        <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                        </div>
                    </div>
                    <div class="mt-2.5 px-0.5">
                        <h4 class="text-xs font-bold text-white truncate group-hover:text-emerald-400 transition" title="${a.album_name}">${a.album_name}</h4>
                        <p class="text-[11px] text-gray-400 truncate" title="${a.album_artist_name}">${a.album_artist_name}</p>
                        <p class="text-[10px] text-gray-500 mt-0.5">${a.release_year || ''}</p>
                    </div>
                </div>
            `).join('');
        }

        async function openGatefold(album) {
            isModalOpen = true;
            currentModalAlbum = album;

            // Desktop elements
            const coverEl = document.getElementById("modalCover");
            if (coverEl) coverEl.src = album.album_image_url;
            const titleEl = document.getElementById("modalTitle");
            if (titleEl) titleEl.innerText = album.album_name;
            const artistEl = document.getElementById("modalArtist");
            if (artistEl) artistEl.innerText = album.album_artist_name;
            const spotEl = document.getElementById("modalSpotifyLink");
            if (spotEl) spotEl.href = album.album_url;

            // Mobile compact elements (<110px header)
            const coverMob = document.getElementById("modalCoverMobile");
            if (coverMob) coverMob.src = album.album_image_url;
            const titleMob = document.getElementById("modalTitleMobile");
            if (titleMob) titleMob.innerText = album.album_name;
            const artistMob = document.getElementById("modalArtistMobile");
            if (artistMob) artistMob.innerText = album.album_artist_name;
            const spotMob = document.getElementById("modalSpotifyLinkMobile");
            if (spotMob) spotMob.href = album.album_url;

            // Apple Music deep links
            const appleMusicUrl = `https://music.apple.com/search?term=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
            const appleEl = document.getElementById("modalAppleMusicLink");
            if (appleEl) appleEl.href = appleMusicUrl;
            const appleMob = document.getElementById("modalAppleMusicLinkMobile");
            if (appleMob) appleMob.href = appleMusicUrl;

            const key = `${album.album_artist_name.toLowerCase()}::${album.album_name.toLowerCase()}`;
            if (!activeAudio.paused && currentHoverKey === key) {
                updateModalPlayIcon(true);
                updateModalProgress();
            } else {
                updateModalPlayIcon(false);
                resetModalProgress();
            }

            let pData = previewUrlCache.get(key);
            if (!pData) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(album.album_artist_name)}&album=${encodeURIComponent(album.album_name)}`);
                    pData = await res.json();
                    previewUrlCache.set(key, pData);
                } catch(e){}
            }
            if (pData && pData.track_name) {
                document.getElementById('gatefoldAudioTrack').innerText = pData.track_name;
            } else {
                document.getElementById('gatefoldAudioTrack').innerText = '30-Second Audio Preview';
            }

            const scoresContainer = document.getElementById("modalScores");
            scoresContainer.innerHTML = '';
            if (album.pitchfork_score) {
                const pfUrl = album.pitchfork_url || `https://pitchfork.com/search/?query=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${pfUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Review on Pitchfork"
                       class="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Pitchfork ${album.pitchfork_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.discogs_rating) {
                const discUrl = album.discogs_url || `https://www.discogs.com/search/?q=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}&type=release`;
                const votes = album.discogs_votes ? ` (${album.discogs_votes.toLocaleString()} votes)` : '';
                scoresContainer.innerHTML += `
                    <a href="${discUrl}" target="_blank" rel="noopener noreferrer"
                       title="View Pressings on Discogs${votes}"
                       class="px-2.5 py-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 border border-blue-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Discogs ${album.discogs_rating} ★</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.metacritic_score) {
                const mcUrl = `https://www.metacritic.com/search/${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}/?page=1&category=1`;
                scoresContainer.innerHTML += `
                    <a href="${mcUrl}" target="_blank" rel="noopener noreferrer"
                       title="View on Metacritic"
                       class="px-2.5 py-1 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 hover:text-yellow-300 border border-yellow-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Metacritic ${album.metacritic_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.wikipedia_url || album.album_description) {
                const wikiUrl = album.wikipedia_url || `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${wikiUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Wikipedia Article"
                       class="px-2.5 py-1 bg-gray-500/10 hover:bg-gray-500/20 text-gray-300 hover:text-white border border-gray-600/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Wikipedia</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }

            const descEl = document.getElementById("modalDescription");
            descEl.innerText = album.album_description || "No archival liner notes found for this release yet.";

            const personnelEl = document.getElementById("modalPersonnel");
            if (album.personnel && album.personnel.length > 0) {
                personnelEl.innerHTML = album.personnel.map(p => `<div>• ${p}</div>`).join('');
                document.getElementById("modalPersonnelSection").classList.remove("hidden");
            } else {
                document.getElementById("modalPersonnelSection").classList.add("hidden");
            }

            document.getElementById("modalMetaInfo").innerText = `${album.release_year || 'Unknown Year'} • ${album.album_tracks_total || 0} tracks • ${album.album_track_plays || 0} total plays`;
            document.getElementById("gatefoldModal").classList.remove("hidden");
        }

        async function toggleModalAudioPlayback() {
            if (!currentModalAlbum) return;
            const key = `${currentModalAlbum.album_artist_name.toLowerCase()}::${currentModalAlbum.album_name.toLowerCase()}`;

            if (!activeAudio.paused && currentHoverKey === key) {
                activeAudio.pause();
                updateModalPlayIcon(false);
                return;
            }

            let data = previewUrlCache.get(key);
            if (!data) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(currentModalAlbum.album_artist_name)}&album=${encodeURIComponent(currentModalAlbum.album_name)}`);
                    data = await res.json();
                    previewUrlCache.set(key, data);
                } catch(e) { return; }
            }

            if (data && data.preview_url) {
                currentHoverKey = key;
                activeAudio.src = data.preview_url;
                activeAudio.play().then(() => {
                    updateModalPlayIcon(true);
                    updateModalProgress();
                }).catch(e => {});
            }
        }

        function seekGatefoldAudio(e) {
            if (!activeAudio || !activeAudio.duration || isNaN(activeAudio.duration) || activeAudio.duration <= 0) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
            const clickX = clientX - rect.left;
            const pct = Math.max(0, Math.min(1, clickX / rect.width));
            activeAudio.currentTime = pct * activeAudio.duration;
            updateModalProgress();
        }

        function updateModalProgress() {
            const cur = activeAudio.currentTime || 0;
            const dur = (activeAudio.duration && !isNaN(activeAudio.duration) && activeAudio.duration > 0) ? activeAudio.duration : 30;
            const pct = Math.min(100, Math.max(0, (cur / dur) * 100));
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = `${pct}%`;
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) {
                const curSec = Math.floor(cur);
                const durSec = Math.floor(dur);
                timeEl.innerText = `0:${curSec < 10 ? '0' : ''}${curSec} / 0:${durSec < 10 ? '0' : ''}${durSec}`;
            }
        }

        function resetModalProgress() {
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = '0%';
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) timeEl.innerText = '0:00 / 0:30';
        }

        activeAudio.addEventListener('timeupdate', () => {
            if (isModalOpen) updateModalProgress();
        });
        activeAudio.addEventListener('ended', () => {
            resetModalProgress();
        });

        function updateModalPlayIcon(isPlaying) {
            const icon = document.getElementById('gatefoldPlayIcon');
            const wave = document.getElementById('gatefoldWaveform');
            if (!icon || !wave) return;
            if (isPlaying) {
                icon.innerText = '❚❚';
                wave.classList.remove('hidden');
                wave.classList.add('flex');
            } else {
                icon.innerText = '▶';
                wave.classList.remove('flex');
                wave.classList.add('hidden');
            }
        }

        function closeGatefold() {
            isModalOpen = false;
            currentModalAlbum = null;
            document.getElementById("gatefoldModal").classList.add("hidden");
            stopPreview();
            resetModalProgress();
        }

        function onModalBackdropClick(e) {
            closeGatefold();
        }

        document.addEventListener("DOMContentLoaded", () => {
            runRecommender();
        });
    </script>
</body>
</html>
"""


# ==============================================================================
# 3. TAB 3: LISTENING TELEMETRY & ANALYTICS ROUTE & TEMPLATE
# ==============================================================================
@app.route("/analytics")
@app.route("/beta/analytics")
@login_required
def beta_analytics():
    user_id = session["user_id"]
    data = fetch_user_album_data(user_id)

    return render_template_string(
        BETA_ANALYTICS_HTML,
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG
    )


@app.route("/api/analytics")
@app.route("/beta/api/analytics")
@login_required
def beta_api_analytics():
    user_id = session["user_id"]
    range_param = request.args.get("range", "30d")
    genre_param = request.args.get("genre", "all")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    payload = fetch_user_analytics_data(
        user_id=user_id,
        range_param=range_param,
        genre_param=genre_param,
        start_date=start_date,
        end_date=end_date
    )
    return jsonify(payload)


BETA_ANALYTICS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - {{ user.display_name }}'s Analytics</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/themes/dark.css">
    <script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #14181f; }
        .active-pill { background-color: #1DB954; color: #000; font-weight: 700; }
        .inactive-pill { background-color: #1b2127; color: #9ca3af; border: 1px solid #28323c; }
        .inactive-pill:hover { background-color: #28323c; color: #fff; }
        .custom-scroll::-webkit-scrollbar { width: 4px; }
        .custom-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
        .flatpickr-calendar { background: #14181f !important; border: 1px solid #374151 !important; border-radius: 1rem !important; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5) !important; }
        .flatpickr-day.selected, .flatpickr-day.startRange, .flatpickr-day.endRange { background: #1DB954 !important; border-color: #1DB954 !important; color: #000 !important; font-weight: bold !important; }
        .flatpickr-day.inRange { background: rgba(29, 185, 84, 0.2) !important; border-color: transparent !important; color: #fff !important; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Persistent Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-3xl font-extrabold tracking-tight text-white">SpinSleeve</h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">ANALYTICS</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Deep listening telemetry, taste velocity &amp; acoustic habits for {{ user.display_name }}</p>
            </div>
            
            <div class="flex items-center gap-3">
                {% if is_admin %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <div class="flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5">
                    <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 shrink-0">
                        <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                    </div>
                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_admin or is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        {% if is_impersonating %}
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition">↩ Revert</a>
                        {% else %}
                        <span class="text-[10px] text-gray-500 font-bold">Switch:</span>
                        {% if user.user_id != 'sergebou' %}
                        <a href="/beta/dev-switch/sergebou" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold ml-1 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded transition">👑 Serge</a>
                        {% endif %}
                        {% if user.user_id != 'sarahboosch' %}
                        <a href="/beta/dev-switch/sarahboosch" class="text-[10px] text-rose-400 hover:text-rose-300 font-bold ml-1 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded transition">👩 Sarah</a>
                        {% endif %}
                        {% if user.user_id != '31sevhztrcbajfcowsahl7z2p26q' %}
                        <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="text-[10px] text-amber-400 hover:text-amber-300 font-bold ml-1 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded transition">🐹 GuineaPig</a>
                        {% endif %}
                        {% endif %}
                    </div>
                    {% endif %}
                    <a href="/beta/logout" class="text-[11px] text-gray-400 hover:text-white ml-1.5 transition">Logout</a>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/beta/recommend" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📻</span> Crate Digger
            </a>
            <a href="/beta/analytics" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📊</span> Analytics
            </a>
            <a href="/beta/pals" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>{% if is_admin or user.pals_opt_in %}🤝{% else %}🔒{% endif %}</span> SpinPals
            </a>
        </nav>

        <!-- Filter Control Bar -->
        <div class="card-bg p-4 rounded-2xl border border-gray-800 mb-6 shadow-md flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
            <div class="flex flex-wrap items-center gap-2">
                <span class="text-[11px] font-bold text-gray-400 uppercase tracking-wider mr-1">Period:</span>
                <button onclick="setRange('1d')" id="btn-1d" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">Last 24h</button>
                <button onclick="setRange('7d')" id="btn-7d" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">7 Days</button>
                <button onclick="setRange('30d')" id="btn-30d" class="active-pill px-3 py-1.5 rounded-lg text-xs transition">30 Days</button>
                <button onclick="setRange('60d')" id="btn-60d" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">60 Days</button>
                <button onclick="setRange('90d')" id="btn-90d" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">90 Days</button>
                <button onclick="setRange('year')" id="btn-year" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">This Year</button>
                <button onclick="setRange('all')" id="btn-all" class="inactive-pill px-3 py-1.5 rounded-lg text-xs transition">All Time</button>
            </div>

            <div class="flex flex-wrap items-center gap-3">
                <div class="relative flex items-center">
                    <input type="text" id="calendarPicker" placeholder="📅 Pick custom dates..." 
                           class="bg-[#0c0f12] border border-gray-700/80 hover:border-emerald-500/60 focus:border-[#1DB954] rounded-xl px-3 py-1.5 text-xs text-gray-200 focus:outline-none transition cursor-pointer w-48 shadow-inner font-medium">
                </div>

                <div class="relative">
                    <select id="genreSelect" onchange="onFilterChange()" class="bg-[#0c0f12] border border-gray-700/80 rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-[#1DB954] appearance-none pr-7">
                        <option value="all">All Genres</option>
                        {% for g in top_genres %}
                        <option value="{{ g }}">{{ g.title() }}</option>
                        {% endfor %}
                    </select>
                    <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400 text-xs">▼</div>
                </div>

                <div id="loadingSpinner" class="hidden">
                    <div class="w-4 h-4 border-2 border-[#1DB954] border-t-transparent rounded-full animate-spin"></div>
                </div>
            </div>
        </div>

        <!-- 4 KPI SUMMARY TILES -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div class="card-bg p-4 rounded-2xl border border-gray-800 shadow-sm flex flex-col justify-between">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Albums Explored</p>
                <div class="mt-2">
                    <p id="kpiAlbums" class="text-3xl font-black text-white">--</p>
                    <p id="kpiAlbumsSub" class="text-[11px] text-gray-400 mt-1">-- fresh / -- repeat</p>
                </div>
            </div>

            <div class="card-bg p-4 rounded-2xl border border-gray-800 shadow-sm flex flex-col justify-between">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Stream Events</p>
                <div class="mt-2">
                    <p id="kpiTracks" class="text-3xl font-black text-white">--</p>
                    <p id="kpiTracksSub" class="text-[11px] text-gray-400 mt-1">Individual track plays</p>
                </div>
            </div>

            <div class="card-bg p-4 rounded-2xl border border-gray-800 shadow-sm flex flex-col justify-between">
                <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Listening Time</p>
                <div class="mt-2">
                    <p id="kpiTime" class="text-3xl font-black text-[#1DB954]">--</p>
                    <p id="kpiTimeSub" class="text-[11px] text-gray-400 mt-1">Est. at ~3.5 min/track</p>
                </div>
            </div>

            <div class="card-bg p-4 rounded-2xl border border-gray-800 shadow-sm flex items-center gap-3">
                <div class="w-14 h-14 rounded-xl overflow-hidden shrink-0 bg-gray-900 border border-gray-800 shadow">
                    <img id="kpiTopImage" src="https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80" alt="Top Album" class="w-full h-full object-cover">
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-400">Top Album</p>
                    <h4 id="kpiTopTitle" class="text-sm font-bold text-white truncate mt-0.5">--</h4>
                    <p id="kpiTopArtist" class="text-xs text-gray-400 truncate">--</p>
                    <p id="kpiTopPlays" class="text-[11px] text-[#1DB954] font-bold mt-0.5">-- plays</p>
                </div>
            </div>
        </div>

        <!-- ROW 1: PLAYS OVER TIME & DISCOVERY VELOCITY -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
            <div class="lg:col-span-2 card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col justify-between">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h3 class="text-sm font-bold text-white">Daily Listening Activity</h3>
                        <p class="text-xs text-gray-400">Track play volume across the selected window</p>
                    </div>
                    <span class="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20">
                        Activity Stream
                    </span>
                </div>
                <div class="relative h-64 w-full">
                    <canvas id="timeSeriesChart"></canvas>
                </div>
            </div>

            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col justify-between">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h3 class="text-sm font-bold text-white">Taste Velocity</h3>
                        <p class="text-xs text-gray-400">Fresh Discoveries vs. Catalog Repeats</p>
                    </div>
                </div>
                <div class="relative h-56 w-full flex items-center justify-center">
                    <canvas id="discoveryChart"></canvas>
                </div>
                <div class="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-800 text-center text-xs">
                    <div>
                        <span class="text-emerald-400 font-bold block" id="freshPct">--%</span>
                        <span class="text-gray-400 text-[11px]" id="freshCount">-- Fresh</span>
                    </div>
                    <div>
                        <span class="text-amber-400 font-bold block" id="repeatPct">--%</span>
                        <span class="text-gray-400 text-[11px]" id="repeatCount">-- Repeat</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- ROW 2: TOP 10 ALBUMS, ARTISTS, AND TRACKS -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col">
                <div class="flex items-center justify-between mb-3.5">
                    <h3 class="text-sm font-bold text-white flex items-center gap-2">
                        <span>💿</span> Top 10 Albums
                    </h3>
                </div>
                <div id="topAlbumsList" class="space-y-2 flex-1 overflow-y-auto max-h-[440px] pr-1 custom-scroll"></div>
            </div>

            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col">
                <div class="flex items-center justify-between mb-3.5">
                    <h3 class="text-sm font-bold text-white flex items-center gap-2">
                        <span>🎤</span> Top 10 Artists
                    </h3>
                </div>
                <div class="relative flex-1 min-h-[380px] w-full">
                    <canvas id="artistChart"></canvas>
                </div>
            </div>

            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col">
                <div class="flex items-center justify-between mb-3.5">
                    <h3 class="text-sm font-bold text-white flex items-center gap-2">
                        <span>🎵</span> Top 10 Tracks
                    </h3>
                </div>
                <div id="topTracksList" class="space-y-2 flex-1 overflow-y-auto max-h-[440px] pr-1 custom-scroll"></div>
            </div>
        </div>

        <!-- ROW 3: RELEASE ERA & GENRE ECOSYSTEM -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col justify-between">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h3 class="text-sm font-bold text-white flex items-center gap-2">
                            <span>⏳</span> Release Era "Time Machine"
                        </h3>
                        <p class="text-xs text-gray-400">Listening volume by original album release decade</p>
                    </div>
                </div>
                <div class="relative h-64 w-full">
                    <canvas id="eraChart"></canvas>
                </div>
            </div>

            <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md flex flex-col justify-between">
                <div class="flex items-center justify-between mb-4">
                    <div>
                        <h3 class="text-sm font-bold text-white flex items-center gap-2">
                            <span>🎷</span> Genre Ecosystem
                        </h3>
                        <p class="text-xs text-gray-400">Distribution of top music styles</p>
                    </div>
                </div>
                <div class="relative h-64 w-full flex items-center justify-center">
                    <canvas id="genreChart"></canvas>
                </div>
            </div>
        </div>

        <!-- ROW 4: THE LISTENING CLOCK (Heatmap) -->
        <div class="card-bg p-5 rounded-2xl border border-gray-800 shadow-md mb-8">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-800/80 mb-4 gap-2">
                <div>
                    <h3 class="text-sm font-bold text-white flex items-center gap-2">
                        <span>🕒</span> The "Listening Clock" Heatmap
                    </h3>
                    <p class="text-xs text-gray-400">Acoustic rhythm: Play intensity across hour of the day (00:00–23:00) and day of the week</p>
                </div>
                <div class="flex items-center gap-1.5 text-[10px] text-gray-400">
                    <span>Less</span>
                    <span class="w-2.5 h-2.5 rounded bg-[#161c22]"></span>
                    <span class="w-2.5 h-2.5 rounded bg-[#0e4429]"></span>
                    <span class="w-2.5 h-2.5 rounded bg-[#006d32]"></span>
                    <span class="w-2.5 h-2.5 rounded bg-[#26a641]"></span>
                    <span class="w-2.5 h-2.5 rounded bg-[#39d353]"></span>
                    <span>More</span>
                </div>
            </div>
            
            <div class="overflow-x-auto pb-2">
                <div class="min-w-[680px]">
                    <div class="flex items-center pl-12 pr-2 mb-1.5 text-[10px] font-mono text-gray-500">
                        {% for h in range(24) %}
                        <div class="flex-1 text-center">{{ "%02d" % h }}</div>
                        {% endfor %}
                    </div>
                    <div id="heatmapGrid" class="space-y-1.5"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentRange = '30d';
        let customStart = null;
        let customEnd = null;
        let fpInstance = null;

        let timeSeriesChartInstance = null;
        let discoveryChartInstance = null;
        let artistChartInstance = null;
        let eraChartInstance = null;
        let genreChartInstance = null;

        const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

        function setRange(range) {
            currentRange = range;
            customStart = null;
            customEnd = null;
            if (fpInstance) fpInstance.clear();

            ['1d', '7d', '30d', '60d', '90d', 'year', 'all'].forEach(r => {
                const btn = document.getElementById(`btn-${r}`);
                if (btn) {
                    btn.className = (r === range) 
                        ? 'active-pill px-3 py-1.5 rounded-lg text-xs transition'
                        : 'inactive-pill px-3 py-1.5 rounded-lg text-xs transition';
                }
            });

            loadAnalytics();
        }

        function onFilterChange() {
            loadAnalytics();
        }

        async function loadAnalytics() {
            const spinner = document.getElementById('loadingSpinner');
            if (spinner) spinner.classList.remove('hidden');

            const genre = document.getElementById('genreSelect').value;
            let url = `/beta/api/analytics?range=${encodeURIComponent(currentRange)}&genre=${encodeURIComponent(genre)}`;
            if (customStart && customEnd) {
                url += `&start=${encodeURIComponent(customStart)}&end=${encodeURIComponent(customEnd)}`;
            }

            try {
                const res = await fetch(url);
                const data = await res.json();
                renderDashboard(data);
            } catch (err) {
                console.error("Failed to load analytics:", err);
            } finally {
                if (spinner) spinner.classList.add('hidden');
            }
        }

        function renderDashboard(data) {
            document.getElementById('kpiAlbums').textContent = (data.kpis.total_albums || 0).toLocaleString();
            document.getElementById('kpiAlbumsSub').textContent = `${data.discovery_vs_repeat.fresh_albums} fresh / ${data.discovery_vs_repeat.repeat_albums} repeat`;
            document.getElementById('kpiTracks').textContent = (data.kpis.total_tracks || 0).toLocaleString();
            document.getElementById('kpiTime').textContent = data.kpis.listening_time || '0h 0m';

            if (data.kpis.top_album) {
                document.getElementById('kpiTopImage').src = data.kpis.top_album.image;
                document.getElementById('kpiTopTitle').textContent = data.kpis.top_album.name;
                document.getElementById('kpiTopArtist').textContent = data.kpis.top_album.artist;
                document.getElementById('kpiTopPlays').textContent = `${data.kpis.top_album.plays} plays`;
            } else {
                document.getElementById('kpiTopTitle').textContent = 'None';
                document.getElementById('kpiTopArtist').textContent = '--';
                document.getElementById('kpiTopPlays').textContent = '0 plays';
            }

            renderTimeSeries(data.time_series);
            renderDiscovery(data.discovery_vs_repeat);
            renderTopAlbums(data.top_albums);
            renderTopArtists(data.top_artists);
            renderTopTracks(data.top_tracks);
            renderEras(data.eras);
            renderGenres(data.genres);
            renderHeatmap(data.heatmap);
        }

        function renderTimeSeries(series) {
            const ctx = document.getElementById('timeSeriesChart').getContext('2d');
            if (timeSeriesChartInstance) timeSeriesChartInstance.destroy();

            const labels = series.map(s => s.date.slice(5));
            const values = series.map(s => s.plays);

            const gradient = ctx.createLinearGradient(0, 0, 0, 240);
            gradient.addColorStop(0, 'rgba(29, 185, 84, 0.4)');
            gradient.addColorStop(1, 'rgba(29, 185, 84, 0.0)');

            timeSeriesChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Plays',
                        data: values,
                        borderColor: '#1DB954',
                        backgroundColor: gradient,
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#1DB954',
                        pointRadius: values.length > 30 ? 0 : 3,
                        pointHoverRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } }, beginAtZero: true }
                    }
                }
            });
        }

        function renderDiscovery(disc) {
            const ctx = document.getElementById('discoveryChart').getContext('2d');
            if (discoveryChartInstance) discoveryChartInstance.destroy();

            document.getElementById('freshPct').textContent = `${disc.fresh_pct}%`;
            document.getElementById('freshCount').textContent = `${disc.fresh_albums} Fresh Albums`;
            document.getElementById('repeatPct').textContent = `${disc.repeat_pct}%`;
            document.getElementById('repeatCount').textContent = `${disc.repeat_albums} Repeat Albums`;

            discoveryChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Fresh Discoveries', 'Catalog Repeats'],
                    datasets: [{
                        data: [disc.fresh_plays, disc.repeat_plays],
                        backgroundColor: ['#10b981', '#f59e0b'],
                        borderColor: '#14181f',
                        borderWidth: 3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '72%',
                    plugins: {
                        legend: { position: 'bottom', labels: { color: '#9ca3af', font: { size: 11 }, boxWidth: 12 } }
                    }
                }
            });
        }

        function renderTopAlbums(albums) {
            const container = document.getElementById('topAlbumsList');
            if (!albums || albums.length === 0) {
                container.innerHTML = '<p class="text-xs text-gray-500 py-6 text-center">No albums played in this period.</p>';
                return;
            }
            const maxPlays = albums[0].plays || 1;
            container.innerHTML = albums.map((a, i) => `
                <div class="flex items-center gap-3 p-2 rounded-xl bg-black/25 border border-gray-800/60 hover:border-gray-700 transition">
                    <span class="text-xs font-bold text-gray-500 w-4 text-center">${i + 1}</span>
                    <div class="w-10 h-10 rounded-lg overflow-hidden shrink-0 bg-gray-900 border border-gray-800 shadow">
                        <img src="${a.image}" alt="${a.name}" class="w-full h-full object-cover">
                    </div>
                    <div class="flex-1 min-w-0">
                        <h5 class="text-xs font-bold text-white truncate">${a.name}</h5>
                        <p class="text-[11px] text-gray-400 truncate">${a.artist}</p>
                        <div class="w-full bg-gray-800/80 h-1 rounded-full overflow-hidden mt-1.5">
                            <div class="bg-[#1DB954] h-full rounded-full" style="width: ${(a.plays / maxPlays) * 100}%"></div>
                        </div>
                    </div>
                    <span class="text-xs font-black text-[#1DB954] px-2 py-0.5 rounded-lg bg-[#1DB954]/10 border border-[#1DB954]/20 shrink-0">
                        ${a.plays}
                    </span>
                </div>
            `).join('');
        }

        function renderTopArtists(artists) {
            const ctx = document.getElementById('artistChart').getContext('2d');
            if (artistChartInstance) artistChartInstance.destroy();

            artistChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: artists.map(a => a.name),
                    datasets: [{
                        label: 'Plays',
                        data: artists.map(a => a.plays),
                        backgroundColor: 'rgba(29, 185, 84, 0.85)',
                        borderColor: '#1DB954',
                        borderWidth: 1,
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } }, beginAtZero: true },
                        y: { grid: { display: false }, ticks: { color: '#e5e7eb', font: { size: 11, weight: 'bold' } } }
                    }
                }
            });
        }

        function renderTopTracks(tracks) {
            const container = document.getElementById('topTracksList');
            if (!tracks || tracks.length === 0) {
                container.innerHTML = '<p class="text-xs text-gray-500 py-6 text-center">No tracks played in this period.</p>';
                return;
            }
            container.innerHTML = tracks.map((t, i) => `
                <div class="flex items-center gap-2.5 p-2 rounded-xl bg-black/25 border border-gray-800/60 hover:border-gray-700 transition">
                    <span class="text-xs font-bold text-gray-500 w-4 text-center">${i + 1}</span>
                    <div class="flex-1 min-w-0">
                        <h5 class="text-xs font-bold text-white truncate">${t.title}</h5>
                        <p class="text-[11px] text-gray-400 truncate">${t.artist} • <span class="text-gray-500">${t.album}</span></p>
                    </div>
                    <span class="text-[11px] font-bold text-gray-300 px-2 py-0.5 rounded-md bg-gray-800 border border-gray-700 shrink-0">
                        ${t.plays} plays
                    </span>
                </div>
            `).join('');
        }

        function renderEras(eras) {
            const ctx = document.getElementById('eraChart').getContext('2d');
            if (eraChartInstance) eraChartInstance.destroy();

            eraChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: eras.map(e => e.era),
                    datasets: [{
                        label: 'Plays',
                        data: eras.map(e => e.plays),
                        backgroundColor: '#6366f1',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: '#e5e7eb', font: { size: 11, weight: 'bold' } } },
                        y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#9ca3af', font: { size: 10 } }, beginAtZero: true }
                    }
                }
            });
        }

        function renderGenres(genres) {
            const ctx = document.getElementById('genreChart').getContext('2d');
            if (genreChartInstance) genreChartInstance.destroy();

            const palette = ['#1DB954', '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899', '#f97316', '#eab308', '#14b8a6'];

            genreChartInstance = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: genres.map(g => g.genre),
                    datasets: [{
                        data: genres.map(g => g.plays),
                        backgroundColor: palette.slice(0, genres.length),
                        borderColor: '#14181f',
                        borderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '65%',
                    plugins: {
                        legend: { position: 'right', labels: { color: '#9ca3af', font: { size: 10 }, boxWidth: 10 } }
                    }
                }
            });
        }

        function renderHeatmap(matrix) {
            const container = document.getElementById('heatmapGrid');
            if (!container || !matrix) return;

            let maxVal = 1;
            for (let r of matrix) {
                for (let v of r) {
                    if (v > maxVal) maxVal = v;
                }
            }

            container.innerHTML = matrix.map((row, dIdx) => {
                const dayName = dayNames[dIdx];
                const cells = row.map((count, hIdx) => {
                    let bg = '#161c22';
                    if (count > 0) {
                        const ratio = count / maxVal;
                        if (ratio < 0.25) bg = '#0e4429';
                        else if (ratio < 0.5) bg = '#006d32';
                        else if (ratio < 0.75) bg = '#26a641';
                        else bg = '#39d353';
                    }
                    const hourStr = `${hIdx.toString().padStart(2, '0')}:00`;
                    return `
                        <div class="flex-1 h-5 rounded-sm transition-all hover:scale-125 cursor-pointer"
                             style="background-color: ${bg};"
                             title="${dayName} ${hourStr} - ${count} plays">
                        </div>
                    `;
                }).join('');

                return `
                    <div class="flex items-center gap-1.5">
                        <span class="w-10 text-[10px] font-mono text-gray-400 font-bold text-right pr-2">${dayName}</span>
                        <div class="flex-1 flex items-center gap-1">
                            ${cells}
                        </div>
                    </div>
                `;
            }).join('');
        }

        document.addEventListener("DOMContentLoaded", () => {
            fpInstance = flatpickr("#calendarPicker", {
                mode: "range",
                dateFormat: "Y-m-d",
                altInput: true,
                altFormat: "M j, Y",
                maxDate: "today",
                onClose: function(selectedDates, dateStr, instance) {
                    if (selectedDates.length === 2) {
                        customStart = instance.formatDate(selectedDates[0], "Y-m-d");
                        customEnd = instance.formatDate(selectedDates[1], "Y-m-d");
                        currentRange = 'custom';

                        ['1d', '7d', '30d', '60d', '90d', 'year', 'all'].forEach(r => {
                            const btn = document.getElementById(`btn-${r}`);
                            if (btn) btn.className = 'inactive-pill px-3 py-1.5 rounded-lg text-xs transition';
                        });

                        loadAnalytics();
                    }
                }
            });

            loadAnalytics();
        });
    </script>
</body>
</html>
"""


# ==============================================================================
# 5. TAB 4: SPINPALS (CRATEMATES & ACOUSTIC CHEMISTRY) ROUTE & TEMPLATE
# ==============================================================================
PALS_LOCKED_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinPals - Private Listening Lounge</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen p-6 md:p-10 flex flex-col justify-between">
    <div class="max-w-4xl mx-auto w-full">
        <header class="flex items-center justify-between pb-6 mb-8 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 shrink-0">{{ brand_icon | safe }}</div>
                <div>
                    <h1 class="text-xl font-black text-white">SpinSleeve</h1>
                    <p class="text-[10px] font-mono tracking-widest text-emerald-400 uppercase">Listening Lounge</p>
                </div>
            </div>
            <a href="/beta/" class="text-xs font-bold text-gray-300 hover:text-white bg-gray-800 border border-gray-700 px-3.5 py-1.5 rounded-xl transition">
                ← Back to Library
            </a>
        </header>

        <div class="max-w-md mx-auto text-center py-12 px-6 bg-[#14181f] border border-gray-800 rounded-3xl shadow-2xl">
            <div class="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mx-auto mb-4 text-2xl">
                🔒
            </div>
            <h2 class="text-xl font-black text-white tracking-tight mb-2">SpinPals: Members Only</h2>
            <p class="text-xs text-gray-400 leading-relaxed mb-6">
                The Listening Lounge and friend-to-friend acoustic chemistry engine is currently private.
                If you'd like to link your crate, compare vinyl taste, and borrow records with friends, contact Serge to activate your access!
            </p>
            <a href="/beta/" class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-xs transition shadow-lg">
                <span>📚</span> Return to Library Explorer
            </a>
        </div>
    </div>
</body>
</html>
"""


@app.route("/pals")
@app.route("/beta/pals")
@app.route("/pals/<pal_id>")
@app.route("/beta/pals/<pal_id>")
@login_required
def beta_pals(pal_id=None):
    current_user_id = session["user_id"]
    ds_client = get_datastore_client()
    key = ds_client.key("User", current_user_id)
    curr_user = ds_client.get(key)
    is_admin = (current_user_id in ADMIN_USER_IDS) or (session.get("admin_user_id") in ADMIN_USER_IDS) or (session.get("role") == "admin")

    if not is_admin and not (curr_user and curr_user.get("pals_opt_in")):
        return render_template_string(PALS_LOCKED_HTML, user=session, brand_icon=ICON_A_SVG)

    pals_directory = fetch_pals_directory(current_user_id)

    # Pick target pal: either requested pal_id, or first other member in directory
    other_pals = [p for p in pals_directory if not p["is_self"]]
    if not other_pals:
        return render_template_string("""
            <body style="background:#0c0f12; color:#fff; font-family:sans-serif; padding:40px; text-align:center;">
                <div style="max-width:440px; margin:40px auto; background:#14181f; border:1px solid #374151; padding:30px; border-radius:24px;">
                    <h2 style="font-size:20px; font-weight:bold; margin-bottom:10px;">No Other Pals in the Lounge Yet</h2>
                    <p style="color:#9ca3af; font-size:13px; line-height:1.6;">Once more friends are approved and opted in, you'll see acoustic compatibility, shared records, and borrow picks here!</p>
                    <a href="/beta/" style="display:inline-block; margin-top:20px; background:#1DB954; color:#000; padding:10px 20px; border-radius:12px; font-weight:bold; font-size:13px; text-decoration:none;">Return to Library</a>
                </div>
            </body>
        """)

    target_pal = None
    if pal_id:
        target_pal = next((p for p in other_pals if p["spotify_id"] == pal_id), None)
    if not target_pal:
        target_pal = other_pals[0]

    pal_data = compute_pal_compatibility(current_user_id, target_pal["spotify_id"])

    return render_template_string(
        BETA_PALS_HTML,
        user=session,
        pals=pals_directory,
        selected_pal=pal_data["pal"],
        compatibility=pal_data["compatibility"],
        top_borrow=pal_data["top_borrow"],
        shared_albums=pal_data["shared_albums"],
        pal_crate=pal_data["pal_full_crate"],
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


BETA_PALS_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinPals: CrateMates - {{ user.display_name }} × {{ selected_pal.display_name }}</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #14181f; }
        .sleeve-shadow { box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.6); }
        .custom-scroll::-webkit-scrollbar { width: 5px; }
        .custom-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
        @keyframes soundWave { 0%, 100% { height: 4px; } 50% { height: 16px; } }
        .wave-bar { animation: soundWave 1.2s ease-in-out infinite; }
        .wave-bar:nth-child(2) { animation-delay: 0.2s; }
        .wave-bar:nth-child(3) { animation-delay: 0.4s; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Persistent Header -->
        <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-3xl font-extrabold tracking-tight text-white">SpinSleeve</h1>
                        <span class="bg-rose-500/20 text-rose-400 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-rose-500/30">SPINPALS: CRATEMATES</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Acoustic chemistry, taste overlap &amp; vinyl shelf borrowing</p>
            </div>
            
            <div class="flex items-center gap-3">
                {% if is_admin %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <div class="flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5">
                    <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 shrink-0">
                        <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                    </div>
                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_admin or is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        {% if is_impersonating %}
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition">↩ Revert</a>
                        {% else %}
                        <span class="text-[10px] text-gray-500 font-bold">Switch:</span>
                        {% if user.user_id != 'sergebou' %}
                        <a href="/beta/dev-switch/sergebou" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold ml-1 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded transition">👑 Serge</a>
                        {% endif %}
                        {% if user.user_id != 'sarahboosch' %}
                        <a href="/beta/dev-switch/sarahboosch" class="text-[10px] text-rose-400 hover:text-rose-300 font-bold ml-1 bg-rose-500/10 border border-rose-500/20 px-1.5 py-0.5 rounded transition">👩 Sarah</a>
                        {% endif %}
                        {% if user.user_id != '31sevhztrcbajfcowsahl7z2p26q' %}
                        <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="text-[10px] text-amber-400 hover:text-amber-300 font-bold ml-1 bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 rounded transition">🐹 GuineaPig</a>
                        {% endif %}
                        {% endif %}
                    </div>
                    {% endif %}
                    <a href="/beta/logout" class="text-[11px] text-gray-400 hover:text-white ml-1.5 transition">Logout</a>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="/beta/recommend" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📻</span> Crate Digger
            </a>
            <a href="/beta/analytics" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>📊</span> Analytics
            </a>
            <a href="/beta/pals" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>🤝</span> SpinPals
            </a>
        </nav>

        <!-- 1. THE LISTENING LOUNGE (Active Club Members Carousel) -->
        <div class="mb-8">
            <div class="flex items-center justify-between mb-3 px-1">
                <div class="flex items-center gap-2">
                    <span class="text-sm">🍸</span>
                    <h3 class="text-xs font-bold uppercase tracking-wider text-gray-400">The Listening Lounge (Vinyl Club Directory)</h3>
                </div>
                <span class="text-[11px] text-gray-500">Click a friend to calculate acoustic chemistry</span>
            </div>

            <div class="flex items-center gap-3 overflow-x-auto pb-2 custom-scroll">
                {% for p in pals %}
                {% if not p.is_self %}
                <a href="/beta/pals/{{ p.spotify_id }}"
                   class="flex items-center gap-3 p-2.5 pr-4 rounded-2xl border transition shrink-0 shadow-md {{ 'bg-emerald-950/20 border-emerald-500/50 shadow-emerald-500/10' if p.spotify_id == selected_pal.spotify_id else 'card-bg border-gray-800 hover:border-gray-700' }}">
                    <div class="w-10 h-10 rounded-full overflow-hidden bg-gray-800 border {{ 'border-emerald-400 ring-2 ring-emerald-500/30' if p.spotify_id == selected_pal.spotify_id else 'border-gray-700' }} shrink-0">
                        <img src="{{ p.avatar_url }}" class="w-full h-full object-cover">
                    </div>
                    <div>
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-bold text-white">{{ p.display_name }}</span>
                            {% if p.spotify_id == selected_pal.spotify_id %}
                            <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                            {% endif %}
                        </div>
                        <span class="text-[10px] text-gray-400">{{ p.album_count }} saved albums</span>
                    </div>
                </a>
                {% endif %}
                {% endfor %}
            </div>
        </div>

        <!-- 2. CRATEMATES COMPARISON HERO (Acoustic Chemistry Gauge) -->
        <div class="card-bg rounded-3xl border border-gray-800 p-6 md:p-8 mb-8 shadow-xl relative overflow-hidden">
            <div class="absolute -top-24 -right-24 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

            <div class="flex flex-col lg:flex-row items-center justify-between gap-8 relative z-10">
                <!-- Chemistry Gauge & Narrative -->
                <div class="flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
                    <!-- Gauge Meter -->
                    <div class="relative w-28 h-28 shrink-0 flex items-center justify-center rounded-full bg-[#0c0f12] border-4 border-emerald-500/40 shadow-inner">
                        <div class="text-center">
                            <span class="text-3xl font-black text-white leading-none block">{{ compatibility.match_pct }}%</span>
                            <span class="text-[9px] font-mono text-emerald-400 font-bold uppercase tracking-wider">Taste Match</span>
                        </div>
                    </div>

                    <!-- Narrative -->
                    <div>
                        <div class="flex flex-wrap items-center justify-center sm:justify-start gap-2 mb-1.5">
                            <span class="text-xs text-gray-400 font-bold">{{ user.display_name }} × {{ selected_pal.display_name }}</span>
                            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold border {{ compatibility.kinship.color }}">
                                {{ compatibility.kinship.badge }}
                            </span>
                        </div>
                        <h2 class="text-xl md:text-2xl font-black text-white tracking-tight">Acoustic Chemistry &amp; Kinship</h2>
                        <p class="text-xs text-gray-300 mt-1 max-w-lg leading-relaxed">
                            {{ compatibility.kinship.desc }}
                        </p>
                    </div>
                </div>

                <!-- 3 Stats Tiles -->
                <div class="grid grid-cols-3 gap-3 w-full lg:w-auto shrink-0">
                    <div class="bg-black/40 border border-gray-800 rounded-2xl p-3.5 text-center">
                        <span class="text-xl md:text-2xl font-black text-white block">{{ compatibility.shared_albums_count }}</span>
                        <span class="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Shared Records</span>
                    </div>
                    <div class="bg-black/40 border border-gray-800 rounded-2xl p-3.5 text-center">
                        <span class="text-xl md:text-2xl font-black text-emerald-400 block">{{ compatibility.shared_artists_count }}</span>
                        <span class="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">Mutual Artists</span>
                    </div>
                    <div class="bg-black/40 border border-gray-800 rounded-2xl p-3.5 text-center">
                        <span class="text-xl md:text-2xl font-black text-amber-400 block">{{ compatibility.borrow_count }}</span>
                        <span class="text-[10px] uppercase tracking-wider text-gray-400 font-semibold">To Borrow</span>
                    </div>
                </div>
            </div>

            <!-- Mutual Artists Pill Bar -->
            {% if compatibility.shared_artists %}
            <div class="mt-6 pt-4 border-t border-gray-800/80 flex flex-wrap items-center gap-2 text-xs">
                <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400 mr-1">🤝 Mutual Obsessions:</span>
                {% for artist in compatibility.shared_artists %}
                <span class="px-2.5 py-1 rounded-lg bg-gray-800/60 border border-gray-700/60 text-gray-300 font-medium text-[11px]">
                    {{ artist }}
                </span>
                {% endfor %}
            </div>
            {% endif %}
        </div>

        <!-- 3. TOP 5 RECORDS TO BORROW FROM PAL -->
        <div class="mb-10">
            <div class="flex items-center justify-between mb-4">
                <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
                    <h2 class="text-xl font-black text-white tracking-tight">Top 5 Records to Borrow from {{ selected_pal.display_name }}</h2>
                </div>
                <span class="text-xs text-gray-400">Curated gems on their shelf you haven't saved yet</span>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                {% if top_borrow %}
                {% for a in top_borrow %}
                <div class="card-bg border border-gray-800 rounded-2xl p-4 shadow-xl flex flex-col justify-between hover:border-amber-500/40 transition group cursor-pointer relative overflow-hidden"
                     onmouseenter="onCardHover('{{ a.album_artist_name | replace(\"'\", \"\\\\'\") }}', '{{ a.album_name | replace(\"'\", \"\\\\'\") }}', '{{ a.album_url }}', this)"
                     onmouseleave="onCardLeave(this)"
                     onclick='openGatefold({{ a | tojson }})'>
                    <div>
                        <div class="aspect-square w-full rounded-xl overflow-hidden bg-gray-900 border border-gray-800/80 mb-3 sleeve-shadow relative">
                            <img src="{{ a.album_image_url }}" alt="{{ a.album_name }}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            {% if a.has_gatefold %}
                            <div class="absolute top-2 left-2 bg-black/75 backdrop-blur-md rounded-lg p-1.5 border border-white/10" title="12&quot; Gatefold Liner Notes Available">
                                {{ gatefold_icon | safe }}
                            </div>
                            {% endif %}
                            <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            </div>
                        </div>

                        <span class="text-[9px] font-mono font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20 inline-block mb-1.5">
                            {{ a.borrow_reason }}
                        </span>
                        <h4 class="text-xs font-black text-white truncate group-hover:text-amber-400 transition" title="{{ a.album_name }}">{{ a.album_name }}</h4>
                        <p class="text-[11px] text-gray-400 truncate mt-0.5" title="{{ a.album_artist_name }}">{{ a.album_artist_name }}</p>
                    </div>
                    <p class="text-[10px] text-gray-500 mt-2 font-mono">{{ a.release_year }}</p>
                </div>
                {% endfor %}
                {% else %}
                <div class="col-span-full py-8 text-center text-gray-500 text-xs">
                    You already own every single album in {{ selected_pal.display_name }}'s crate!
                </div>
                {% endif %}
            </div>
        </div>

        <!-- 4. FLIP THROUGH PAL'S VIRTUAL CRATE -->
        <div>
            <div class="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-800 mb-6 gap-2">
                <div>
                    <h3 class="text-sm font-bold uppercase tracking-wider text-gray-300 flex items-center gap-2">
                        <span>📦</span> Flip Through {{ selected_pal.display_name }}'s Virtual Crate
                    </h3>
                    <p class="text-xs text-gray-500 mt-0.5">Browse all {{ pal_crate | length }} records in their collection</p>
                </div>
            </div>

            <div id="palCrateGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
                {% for a in pal_crate %}
                <div class="group relative flex flex-col cursor-pointer"
                     onmouseenter="onCardHover('{{ a.album_artist_name | replace(\"'\", \"\\\\'\") }}', '{{ a.album_name | replace(\"'\", \"\\\\'\") }}', '{{ a.album_url }}', this)"
                     onmouseleave="onCardLeave(this)"
                     onclick='openGatefold({{ a | tojson }})'>
                    <div class="aspect-square w-full rounded-2xl overflow-hidden bg-gray-900 border border-gray-800/80 sleeve-shadow transition duration-300 group-hover:scale-[1.03] group-hover:border-gray-700 relative">
                        <img src="{{ a.album_image_url }}" alt="{{ a.album_name }}" class="w-full h-full object-cover">
                        {% if a.has_gatefold %}
                        <div class="absolute top-2 left-2 bg-black/75 backdrop-blur-md rounded-lg p-1.5 border border-white/10 shadow" title="12&quot; Gatefold Liner Notes Available">
                            {{ gatefold_icon | safe }}
                        </div>
                        {% endif %}
                        {% if a.current_user_owns %}
                        <div class="absolute top-2 right-2 bg-emerald-500/80 backdrop-blur-md rounded-lg px-2 py-0.5 border border-emerald-400 text-[10px] font-black text-black" title="You both own this record!">
                            🤝 Both Own
                        </div>
                        {% endif %}
                        <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                        </div>
                    </div>
                    <div class="mt-2.5 px-0.5">
                        <h4 class="text-xs font-bold text-white truncate group-hover:text-emerald-400 transition" title="{{ a.album_name }}">{{ a.album_name }}</h4>
                        <p class="text-[11px] text-gray-400 truncate" title="{{ a.album_artist_name }}">{{ a.album_artist_name }}</p>
                        <p class="text-[10px] text-gray-500 mt-0.5">{{ a.release_year }}</p>
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <!-- Pinned Preview Toast -->
    <div id="previewToast" class="fixed bottom-6 right-6 z-40 bg-[#161a22]/95 border border-emerald-500/30 rounded-2xl p-3.5 shadow-2xl backdrop-blur-md flex items-center gap-3.5 max-w-sm transition-all duration-300 translate-y-28 opacity-0 pointer-events-none">
        <div class="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center shrink-0">
            <div class="flex items-end gap-0.5 h-3">
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                <span class="w-0.5 bg-emerald-400 wave-bar"></span>
            </div>
        </div>
        <div class="flex-1 min-w-0">
            <p id="toastTrack" class="text-xs font-bold text-white truncate">Preview Snippet</p>
            <p id="toastArtist" class="text-[11px] text-gray-400 truncate">--</p>
        </div>
        <button onclick="stopPreview()" class="text-gray-400 hover:text-white p-1 text-sm font-bold">&times;</button>
    </div>

    <!-- 12" Gatefold Modal Markup -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6" onclick="onModalBackdropClick(event)">
        <div class="relative w-full max-w-5xl bg-[#14181f] border border-gray-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row h-[88vh] md:h-[640px]" onclick="event.stopPropagation()">
            <!-- LEFT PANEL: 12" Vinyl Jacket (Desktop) / Compact Header (Mobile <110px) -->
            <div class="w-full md:w-5/12 bg-black/40 p-3 sm:p-4 md:p-6 flex flex-col justify-between border-b md:border-b-0 md:border-r border-gray-800/80 shrink-0">
                <!-- Mobile Compact Header (<md: <110px height without scrolling) -->
                <div class="md:hidden flex items-center justify-between gap-3 w-full">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-16 h-16 rounded-xl overflow-hidden shadow-lg border border-gray-800 shrink-0">
                            <img id="modalCoverMobile" src="" class="w-full h-full object-cover" alt="Album Cover">
                        </div>
                        <div class="min-w-0">
                            <span class="text-[9px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20 font-bold uppercase inline-block mb-0.5">12" Gatefold</span>
                            <h3 id="modalTitleMobile" class="text-sm font-bold text-white truncate leading-snug">--</h3>
                            <p id="modalArtistMobile" class="text-xs font-semibold text-emerald-400 truncate">--</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2 shrink-0">
                        <a id="modalSpotifyLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Play on Spotify" class="w-8 h-8 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        </a>
                        <a id="modalAppleMusicLinkMobile" href="#" target="_blank" rel="noopener noreferrer" title="Listen on Apple Music" class="w-8 h-8 rounded-full bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 flex items-center justify-center transition shadow">
                            <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        </a>
                        <button onclick="closeGatefold()" class="w-8 h-8 rounded-full bg-gray-800/80 hover:bg-gray-700 text-gray-400 hover:text-white flex items-center justify-center text-lg font-bold transition">&times;</button>
                    </div>
                </div>

                <!-- Desktop Full Jacket (>md) -->
                <div class="hidden md:flex w-full justify-between items-center mb-3">
                    <span class="text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-bold uppercase">12" Gatefold Edition</span>
                </div>
                <div class="hidden md:block w-56 h-56 lg:w-64 lg:h-64 rounded-2xl overflow-hidden shadow-2xl border border-gray-800 my-auto mx-auto shrink-0">
                    <img id="modalCover" src="" class="w-full h-full object-cover" alt="Album Cover">
                </div>
                <div class="hidden md:flex w-full mt-4 flex-col gap-2">
                    <a id="modalSpotifyLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.498 17.306c-.218.358-.684.472-1.042.254-2.855-1.745-6.449-2.14-10.684-1.173-.41.093-.816-.164-.91-.573-.093-.41.164-.817.573-.91 4.636-1.06 8.607-.611 11.81 1.35.358.218.472.684.253 1.052zm1.467-3.26c-.275.448-.865.59-1.313.315-3.268-2.008-8.25-2.59-12.115-1.416-.503.153-1.034-.136-1.187-.64-.153-.504.136-1.035.64-1.188 4.414-1.34 9.907-.69 13.66 1.616.448.275.59.865.315 1.313zm.126-3.41c-3.918-2.327-10.37-2.542-14.103-1.408-.6.183-1.238-.157-1.421-.758-.182-.601.157-1.239.758-1.421 4.29-1.303 11.41-1.053 15.908 1.616.539.32.716 1.02.396 1.56-.32.539-1.02.716-1.56.396z"/></svg>
                        <span>Play on Spotify</span>
                    </a>
                    <a id="modalAppleMusicLink" href="#" target="_blank" rel="noopener noreferrer" class="w-full py-2.5 rounded-xl bg-[#fc3c44]/15 hover:bg-[#fc3c44]/25 text-[#fc3c44] border border-[#fc3c44]/30 font-bold text-xs flex items-center justify-center gap-2 transition shadow">
                        <svg class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg>
                        <span>Open in Apple Music</span>
                    </a>
                </div>
            </div>

            <!-- RIGHT PANEL: Gatefold Liner Notes, Audio Scrubber & Archival Review Badges -->
            <div class="w-full md:w-7/12 p-3 sm:p-4 md:p-6 flex flex-col justify-between overflow-y-auto custom-scroll flex-1">
                <div>
                    <!-- Audio Scrubber & Player Bar -->
                    <div id="gatefoldAudioBar" class="mb-4 p-3 rounded-2xl bg-black/40 border border-gray-800 flex flex-col gap-2">
                        <div class="flex items-center justify-between gap-3">
                            <div class="flex items-center gap-3 min-w-0">
                                <button id="gatefoldPlayBtn" onclick="toggleModalAudioPlayback()"
                                        class="w-9 h-9 rounded-full bg-[#1DB954] hover:bg-[#1ed760] text-black flex items-center justify-center shrink-0 transition shadow-lg">
                                    <span id="gatefoldPlayIcon" class="text-xs">▶</span>
                                </button>
                                <div class="min-w-0">
                                    <p id="gatefoldAudioTrack" class="text-xs font-bold text-white truncate">30-Second Audio Preview</p>
                                    <p id="gatefoldAudioSubtext" class="text-[10px] text-gray-400">iTunes Audio Snippet</p>
                                </div>
                            </div>
                            <div class="flex items-center gap-2 shrink-0">
                                <span id="gatefoldAudioTime" class="text-[10px] font-mono text-gray-400">0:00 / 0:30</span>
                                <div id="gatefoldWaveform" class="hidden items-end gap-0.5 h-3.5 pr-1">
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                    <span class="w-0.5 bg-[#1DB954] wave-bar"></span>
                                </div>
                            </div>
                        </div>
                        <!-- Scrubber Track -->
                        <div id="gatefoldScrubber" class="relative w-full bg-gray-800/80 hover:bg-gray-700/80 h-2 rounded-full overflow-hidden cursor-pointer transition-colors"
                             onpointerdown="seekGatefoldAudio(event)">
                            <div id="gatefoldProgressBar" class="h-full bg-[#1DB954] rounded-full w-0 transition-[width] duration-100 pointer-events-none"></div>
                        </div>
                    </div>

                    <!-- Desktop Title & Artist (md:flex) -->
                    <div class="hidden md:flex items-start justify-between gap-4 mb-2">
                        <div>
                            <h3 id="modalTitle" class="text-xl md:text-2xl font-black text-white leading-tight">--</h3>
                            <p id="modalArtist" class="text-sm font-semibold text-emerald-400 mt-0.5">--</p>
                        </div>
                        <button onclick="closeGatefold()" class="text-gray-400 hover:text-white p-1 text-2xl font-bold">&times;</button>
                    </div>

                    <!-- Archival Badges with External Deep Links -->
                    <div id="modalScores" class="flex flex-wrap items-center gap-2 my-3"></div>

                    <!-- Liner Notes & Personnel -->
                    <div class="space-y-4 text-xs text-gray-300 leading-relaxed mt-4">
                        <div id="modalDescriptionSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Album Narrative &amp; Critical Reception</h4>
                            <p id="modalDescription" class="italic text-gray-300">--</p>
                        </div>
                        <div id="modalPersonnelSection">
                            <h4 class="text-[10px] font-mono uppercase tracking-wider text-gray-400 font-bold mb-1">Production &amp; Personnel Credits</h4>
                            <div id="modalPersonnel" class="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[11px] text-gray-400"></div>
                        </div>
                    </div>
                </div>

                <!-- Footer with Meta Info and SpinSleeve Verified -->
                <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-[11px] text-gray-500">
                    <span id="modalMetaInfo">--</span>
                    <span class="text-emerald-500 font-mono font-semibold flex items-center gap-1.5">
                        <svg class="w-3.5 h-3.5 text-emerald-400" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/></svg>
                        SpinSleeve Verified
                    </span>
                </div>
            </div>
        </div>
    </div>

    <script>
        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = true;
        let isModalOpen = false;
        let currentModalAlbum = null;
        const previewUrlCache = new Map();

        activeAudio.volume = 0.75;
        activeAudio.addEventListener('ended', () => {
            hidePreviewToast();
            updateModalPlayIcon(false);
        });

        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                btnText.innerText = 'Hover Audio: ON';
                btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                btnText.innerText = 'Hover Audio: MUTED';
                btnIcon.innerText = '🔇';
            }
        }

        function onCardHover(artist, album, spotifyUrl, cardEl) {
            if (!isAudioEnabled || isModalOpen) return;
            const key = `${artist.toLowerCase()}::${album.toLowerCase()}`;
            currentHoverKey = key;

            if (hoverTimer) clearTimeout(hoverTimer);

            hoverTimer = setTimeout(async () => {
                if (currentHoverKey !== key) return;

                let data = previewUrlCache.get(key);
                if (!data) {
                    try {
                        const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(artist)}&album=${encodeURIComponent(album)}`);
                        data = await res.json();
                        previewUrlCache.set(key, data);
                    } catch (e) { return; }
                }

                if (currentHoverKey !== key) return;

                if (data && data.preview_url) {
                    activeAudio.src = data.preview_url;
                    activeAudio.play().then(() => {
                        showPreviewToast(artist, album, data.track_name || 'Preview Snippet', data.apple_music_url, spotifyUrl);
                        const pulse = cardEl.querySelector('.audio-pulse');
                        if (pulse) pulse.classList.remove('hidden');
                    }).catch(e => {});
                }
            }, 350);
        }

        function onCardLeave(cardEl) {
            if (hoverTimer) clearTimeout(hoverTimer);
            if (isModalOpen) return;
            currentHoverKey = null;
            stopPreview();
            if (cardEl) {
                const pulse = cardEl.querySelector('.audio-pulse');
                if (pulse) pulse.classList.add('hidden');
            }
        }

        function stopPreview() {
            activeAudio.pause();
            activeAudio.currentTime = 0;
            hidePreviewToast();
            document.querySelectorAll('.audio-pulse').forEach(el => el.classList.add('hidden'));
            updateModalPlayIcon(false);
        }

        function showPreviewToast(artist, album, track, appleUrl, spotifyUrl) {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            document.getElementById('toastTrack').innerText = track;
            document.getElementById('toastArtist').innerText = `${artist} • ${album}`;
            toast.classList.remove('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.add('translate-y-0', 'opacity-100');
        }

        function hidePreviewToast() {
            const toast = document.getElementById('previewToast');
            if (!toast) return;
            toast.classList.add('translate-y-28', 'opacity-0', 'pointer-events-none');
            toast.classList.remove('translate-y-0', 'opacity-100');
        }

        async function openGatefold(album) {
            isModalOpen = true;
            currentModalAlbum = album;

            // Desktop elements
            const coverEl = document.getElementById("modalCover");
            if (coverEl) coverEl.src = album.album_image_url;
            const titleEl = document.getElementById("modalTitle");
            if (titleEl) titleEl.innerText = album.album_name;
            const artistEl = document.getElementById("modalArtist");
            if (artistEl) artistEl.innerText = album.album_artist_name;
            const spotEl = document.getElementById("modalSpotifyLink");
            if (spotEl) spotEl.href = album.album_url;

            // Mobile compact elements (<110px header)
            const coverMob = document.getElementById("modalCoverMobile");
            if (coverMob) coverMob.src = album.album_image_url;
            const titleMob = document.getElementById("modalTitleMobile");
            if (titleMob) titleMob.innerText = album.album_name;
            const artistMob = document.getElementById("modalArtistMobile");
            if (artistMob) artistMob.innerText = album.album_artist_name;
            const spotMob = document.getElementById("modalSpotifyLinkMobile");
            if (spotMob) spotMob.href = album.album_url;

            // Apple Music deep links
            const appleMusicUrl = `https://music.apple.com/search?term=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
            const appleEl = document.getElementById("modalAppleMusicLink");
            if (appleEl) appleEl.href = appleMusicUrl;
            const appleMob = document.getElementById("modalAppleMusicLinkMobile");
            if (appleMob) appleMob.href = appleMusicUrl;

            const key = `${album.album_artist_name.toLowerCase()}::${album.album_name.toLowerCase()}`;
            if (!activeAudio.paused && currentHoverKey === key) {
                updateModalPlayIcon(true);
                updateModalProgress();
            } else {
                updateModalPlayIcon(false);
                resetModalProgress();
            }

            let pData = previewUrlCache.get(key);
            if (!pData) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(album.album_artist_name)}&album=${encodeURIComponent(album.album_name)}`);
                    pData = await res.json();
                    previewUrlCache.set(key, pData);
                } catch(e){}
            }
            if (pData && pData.track_name) {
                document.getElementById('gatefoldAudioTrack').innerText = pData.track_name;
            } else {
                document.getElementById('gatefoldAudioTrack').innerText = '30-Second Audio Preview';
            }

            const scoresContainer = document.getElementById("modalScores");
            scoresContainer.innerHTML = '';
            if (album.pitchfork_score) {
                const pfUrl = album.pitchfork_url || `https://pitchfork.com/search/?query=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${pfUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Review on Pitchfork"
                       class="px-2.5 py-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 border border-red-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Pitchfork ${album.pitchfork_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.discogs_rating) {
                const discUrl = album.discogs_url || `https://www.discogs.com/search/?q=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}&type=release`;
                const votes = album.discogs_votes ? ` (${album.discogs_votes.toLocaleString()} votes)` : '';
                scoresContainer.innerHTML += `
                    <a href="${discUrl}" target="_blank" rel="noopener noreferrer"
                       title="View Pressings on Discogs${votes}"
                       class="px-2.5 py-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 hover:text-blue-300 border border-blue-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Discogs ${album.discogs_rating} ★</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.metacritic_score) {
                const mcUrl = `https://www.metacritic.com/search/${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}/?page=1&category=1`;
                scoresContainer.innerHTML += `
                    <a href="${mcUrl}" target="_blank" rel="noopener noreferrer"
                       title="View on Metacritic"
                       class="px-2.5 py-1 bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 hover:text-yellow-300 border border-yellow-500/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Metacritic ${album.metacritic_score}</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }
            if (album.wikipedia_url || album.album_description) {
                const wikiUrl = album.wikipedia_url || `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(album.album_artist_name + ' ' + album.album_name)}`;
                scoresContainer.innerHTML += `
                    <a href="${wikiUrl}" target="_blank" rel="noopener noreferrer"
                       title="Read Wikipedia Article"
                       class="px-2.5 py-1 bg-gray-500/10 hover:bg-gray-500/20 text-gray-300 hover:text-white border border-gray-600/30 rounded-lg text-[11px] font-bold inline-flex items-center gap-1.5 transition shadow-sm">
                        <span>Wikipedia</span>
                        <svg class="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/></svg>
                    </a>`;
            }

            const descEl = document.getElementById("modalDescription");
            descEl.innerText = album.album_description || "No archival liner notes found for this release yet.";

            const personnelEl = document.getElementById("modalPersonnel");
            if (album.personnel && album.personnel.length > 0) {
                personnelEl.innerHTML = album.personnel.map(p => `<div>• ${p}</div>`).join('');
                document.getElementById("modalPersonnelSection").classList.remove("hidden");
            } else {
                document.getElementById("modalPersonnelSection").classList.add("hidden");
            }

            document.getElementById("modalMetaInfo").innerText = `${album.release_year || 'Unknown Year'} • ${album.album_tracks_total || 0} tracks • ${album.album_track_plays || 0} total plays`;
            document.getElementById("gatefoldModal").classList.remove("hidden");
        }

        async function toggleModalAudioPlayback() {
            if (!currentModalAlbum) return;
            const key = `${currentModalAlbum.album_artist_name.toLowerCase()}::${currentModalAlbum.album_name.toLowerCase()}`;

            if (!activeAudio.paused && currentHoverKey === key) {
                activeAudio.pause();
                updateModalPlayIcon(false);
                return;
            }

            let data = previewUrlCache.get(key);
            if (!data) {
                try {
                    const res = await fetch(`/beta/api/preview?artist=${encodeURIComponent(currentModalAlbum.album_artist_name)}&album=${encodeURIComponent(currentModalAlbum.album_name)}`);
                    data = await res.json();
                    previewUrlCache.set(key, data);
                } catch(e) { return; }
            }

            if (data && data.preview_url) {
                currentHoverKey = key;
                activeAudio.src = data.preview_url;
                activeAudio.play().then(() => {
                    updateModalPlayIcon(true);
                    updateModalProgress();
                }).catch(e => {});
            }
        }

        function seekGatefoldAudio(e) {
            if (!activeAudio || !activeAudio.duration || isNaN(activeAudio.duration) || activeAudio.duration <= 0) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
            const clickX = clientX - rect.left;
            const pct = Math.max(0, Math.min(1, clickX / rect.width));
            activeAudio.currentTime = pct * activeAudio.duration;
            updateModalProgress();
        }

        function updateModalProgress() {
            const cur = activeAudio.currentTime || 0;
            const dur = (activeAudio.duration && !isNaN(activeAudio.duration) && activeAudio.duration > 0) ? activeAudio.duration : 30;
            const pct = Math.min(100, Math.max(0, (cur / dur) * 100));
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = `${pct}%`;
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) {
                const curSec = Math.floor(cur);
                const durSec = Math.floor(dur);
                timeEl.innerText = `0:${curSec < 10 ? '0' : ''}${curSec} / 0:${durSec < 10 ? '0' : ''}${durSec}`;
            }
        }

        function resetModalProgress() {
            const pBar = document.getElementById('gatefoldProgressBar');
            if (pBar) pBar.style.width = '0%';
            const timeEl = document.getElementById('gatefoldAudioTime');
            if (timeEl) timeEl.innerText = '0:00 / 0:30';
        }

        activeAudio.addEventListener('timeupdate', () => {
            if (isModalOpen) updateModalProgress();
        });
        activeAudio.addEventListener('ended', () => {
            resetModalProgress();
        });

        function updateModalPlayIcon(isPlaying) {
            const icon = document.getElementById('gatefoldPlayIcon');
            const wave = document.getElementById('gatefoldWaveform');
            if (!icon || !wave) return;
            if (isPlaying) {
                icon.innerText = '❚❚';
                wave.classList.remove('hidden');
                wave.classList.add('flex');
            } else {
                icon.innerText = '▶';
                wave.classList.remove('flex');
                wave.classList.add('hidden');
            }
        }

        function closeGatefold() {
            isModalOpen = false;
            currentModalAlbum = null;
            document.getElementById("gatefoldModal").classList.add("hidden");
            stopPreview();
            resetModalProgress();
        }

        function onModalBackdropClick(e) {
            closeGatefold();
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
