import os
import sys
import time
import json
import logging
import datetime
from collections import Counter
from functools import wraps

from flask import (
    Flask,
    render_template_string,
    request,
    jsonify,
    redirect,
    url_for,
    session
)
import pandas as pd
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
app.config["SESSION_COOKIE_NAME"] = "__session"
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


def get_datastore_client():
    return datastore.Client(project=PROJECT_ID)


def get_oauth_client(request_obj):
    """Builds a SpotifyOAuth client with a dynamic callback URL based on incoming request."""
    # Build redirect URI: prefer https in production
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


# Brand Logo
ICON_A_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" fill="none">
  <circle cx="50" cy="50" r="46" fill="#14181f" stroke="#1DB954" stroke-width="4"/>
  <circle cx="50" cy="50" r="34" stroke="#28323c" stroke-width="1.5" stroke-dasharray="3 3"/>
  <circle cx="50" cy="50" r="24" stroke="#28323c" stroke-width="1.5"/>
  <circle cx="50" cy="50" r="14" fill="#1DB954"/>
  <circle cx="50" cy="50" r="4" fill="#0c0f12"/>
</svg>"""

ICON_GATEFOLD_SVG = """<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
</svg>"""


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
        if session.get("role") != "admin" and session.get("user_id") not in ADMIN_USER_IDS:
            return redirect("/beta/")
        return f(*args, **kwargs)
    return decorated_function


# ==============================================================================
# DATA SYNC & BIGQUERY RETRIEVAL (MULTI-TENANT)
# ==============================================================================
_user_album_cache = {}
_user_album_cache_time = {}
CACHE_TTL = 600


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
            # Write to BigQuery user_saved_albums
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
        return str(val).strip()
    return default


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

    # Format albums
    processed = []
    genre_counter = Counter()

    for _, row in df.iterrows():
        # Parse personnel if JSON string or list
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

        g_str = str(row.get("album_genres") or "")
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
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
    </style>
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
            <p class="text-[10px] font-mono uppercase text-gray-500 mb-2.5 font-bold tracking-wider">🛠️ 1-Click Test Switcher</p>
            <div class="flex items-center justify-center gap-2.5">
                <a href="/beta/dev-switch/sergebou" class="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-emerald-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                    <span>👑</span> Serge (Admin)
                </a>
                <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="px-3.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-amber-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                    <span>🐹</span> Guinea Pig
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
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen p-6 md:p-10">
    <div class="max-w-5xl mx-auto">
        <div class="flex items-center justify-between pb-6 mb-8 border-b border-gray-800">
            <div>
                <h1 class="text-2xl font-black text-white">⚙️ Admin Control Deck</h1>
                <p class="text-xs text-gray-400 mt-1">Manage private beta invitations and friends access</p>
            </div>
            <div class="flex items-center gap-3">
                <a href="/beta/" class="text-xs font-bold bg-[#1DB954] text-black px-4 py-2 rounded-xl transition hover:bg-[#1ed760]">
                    Back to Library
                </a>
            </div>
        </div>

        <!-- Add / Whitelist User Card -->
        <div class="bg-[#14181f] p-5 rounded-2xl border border-gray-800 mb-8 shadow-sm">
            <h3 class="text-sm font-bold text-white mb-3">Pre-Approve a Friend</h3>
            <form action="/beta/admin/whitelist" method="POST" class="flex flex-col sm:flex-row gap-3">
                <input type="text" name="spotify_id" placeholder="Spotify User ID or Username" required class="bg-[#0c0f12] border border-gray-700 rounded-xl px-4 py-2 text-xs text-white flex-1 focus:outline-none focus:border-[#1DB954]">
                <input type="text" name="display_name" placeholder="Display Name (optional)" class="bg-[#0c0f12] border border-gray-700 rounded-xl px-4 py-2 text-xs text-white flex-1 focus:outline-none focus:border-[#1DB954]">
                <button type="submit" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-5 py-2 rounded-xl transition">
                    + Whitelist User
                </button>
            </form>
        </div>

        <!-- Users Table -->
        <div class="bg-[#14181f] rounded-2xl border border-gray-800 overflow-hidden shadow-sm">
            <table class="w-full text-left text-xs">
                <thead class="bg-black/30 border-b border-gray-800 text-gray-400 uppercase text-[10px] tracking-wider font-bold">
                    <tr>
                        <th class="p-4">User</th>
                        <th class="p-4">Spotify ID</th>
                        <th class="p-4">Email</th>
                        <th class="p-4">Status</th>
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
                        <td class="p-4 text-gray-400">{{ u.role or 'user' }}</td>
                        <td class="p-4 text-right">
                            <form action="/beta/admin/toggle/{{ u.spotify_id }}" method="POST" class="inline">
                                {% if u.is_approved %}
                                <button type="submit" class="text-rose-400 hover:text-rose-300 bg-rose-500/10 border border-rose-500/20 px-3 py-1 rounded-lg text-[11px] font-bold transition">
                                    Revoke
                                </button>
                                {% else %}
                                <button type="submit" class="text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg text-[11px] font-bold transition">
                                    ✓ Approve
                                </button>
                                {% endif %}
                            </form>
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

        # First-time registration
        is_admin = (spotify_id in ADMIN_USER_IDS)
        if not user:
            user = datastore.Entity(key=key)
            user.update({
                "spotify_id": spotify_id,
                "display_name": display_name,
                "email": email,
                "avatar_url": avatar_url,
                "is_approved": is_admin,  # Admin is auto-approved, others require invite
                "role": "admin" if is_admin else "user",
                "refresh_token": refresh_token,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
                "last_login_at": datetime.datetime.now(datetime.timezone.utc),
                "sync_status": "idle" if is_admin else "pending"
            })
            ds_client.put(user)
        else:
            # Update tokens and profile
            user["display_name"] = display_name
            user["email"] = email
            user["avatar_url"] = avatar_url
            if is_admin:
                user["role"] = "admin"
                user["is_approved"] = True
            if refresh_token:
                user["refresh_token"] = refresh_token
            user["last_login_at"] = datetime.datetime.now(datetime.timezone.utc)
            ds_client.put(user)

        # Check approval
        if not user.get("is_approved"):
            return render_template_string(PENDING_HTML_TEMPLATE, user=user)

        # User is approved: establish session
        session["user_id"] = spotify_id
        session["display_name"] = display_name
        session["avatar_url"] = avatar_url
        session["role"] = user.get("role", "user")

        # Initial background sync for new approved users
        if user.get("sync_status") == "pending":
            sync_user_initial_data(spotify_id, access_token)
            user["sync_status"] = "idle"
            ds_client.put(user)

        return redirect("/beta/")

    except Exception as e:
        logger.exception("Error in Spotify OAuth callback: %s", e)
        return f"Authentication error: {e}", 500


@app.route("/logout")
@app.route("/beta/logout")
def logout():
    session.clear()
    return redirect("/beta/login")


@app.route("/beta/dev-switch/<user_id>")
def dev_switch(user_id):
    if user_id not in ("sergebou", "31sevhztrcbajfcowsahl7z2p26q", "vaultica"):
        return "Unauthorized test switch", 403
    ds_client = get_datastore_client()
    key = ds_client.key("User", user_id)
    user = ds_client.get(key)
    if not user:
        return f"User {user_id} not found in Datastore", 404

    session["user_id"] = user_id
    session["display_name"] = user.get("display_name", user_id)
    session["avatar_url"] = user.get("avatar_url", "")
    session["role"] = user.get("role", "user")
    logger.info("Dev switched session to: %s (%s)", user_id, session["display_name"])
    return redirect("/beta/")


# ==============================================================================
# ADMIN ROUTES (INVITE ALLOWLIST)
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


@app.route("/beta/admin/whitelist", methods=["POST"])
@admin_required
def admin_whitelist():
    spotify_id = request.form.get("spotify_id", "").strip()
    display_name = request.form.get("display_name", "").strip()
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
# BETA APPLICATION ROUTES
# ==============================================================================
@app.route("/")
@app.route("/beta")
@app.route("/beta/")
@login_required
def beta_index():
    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    # Render template with user info and beta navigation
    return render_template_string(
        BETA_EXPLORER_HTML,
        albums=data["albums"],
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


# ==============================================================================
# HTML TEMPLATE: BETA LIBRARY EXPLORER (With Gatefolds, Previews & User Header)
# ==============================================================================
BETA_EXPLORER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve Beta - {{ user.display_name }}</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .card-bg { background-color: #14181f; }
        .serif-title { font-family: 'Playfair Display', serif; }
        .sleeve-shadow { box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.6); }
        .custom-scroll::-webkit-scrollbar { width: 5px; }
        .custom-scroll::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
        .custom-scroll::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
    </style>
</head>
<body class="min-h-screen p-4 md:p-8">
    <div class="max-w-7xl mx-auto">
        <!-- Header with User Profile -->
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
            
            <!-- User Status & Actions -->
            <div class="flex items-center gap-3">
                {% if user.role == 'admin' %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-2 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <div class="flex items-center gap-2.5 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5">
                    <div class="w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700">
                        <img src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" class="w-full h-full object-cover">
                    </div>
                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if user.user_id == 'sergebou' %}
                    <a href="/beta/dev-switch/31sevhztrcbajfcowsahl7z2p26q" class="text-[10px] text-amber-400 hover:text-amber-300 font-bold ml-1.5 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded transition">
                        🐹 Switch to Guinea Pig
                    </a>
                    {% else %}
                    <a href="/beta/dev-switch/sergebou" class="text-[10px] text-emerald-400 hover:text-emerald-300 font-bold ml-1.5 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded transition">
                        👑 Switch to Admin
                    </a>
                    {% endif %}
                    <a href="/beta/logout" class="text-[11px] text-gray-400 hover:text-white ml-2 transition">Logout</a>
                </div>
            </div>
        </header>

        <!-- Navigation Tabs -->
        <nav class="flex items-center gap-2 mb-6 border-b border-gray-800 pb-3">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-bold transition bg-[#1DB954]/15 text-[#1DB954] border border-[#1DB954]/30 flex items-center gap-2">
                <span>📚</span> Library Explorer
            </a>
            <a href="https://spinsleeve.cc" target="_blank" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/60 transition flex items-center gap-2">
                <span>🌐</span> Production App (v1)
            </a>
        </nav>

        <!-- Filter Controls Toolbar -->
        <div class="card-bg p-4 rounded-xl border border-gray-800 mb-6 shadow-sm">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 items-center">
                <!-- Search -->
                <div class="relative lg:col-span-2">
                    <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">🔍</span>
                    <input type="text" id="searchInput" placeholder="Search your albums or artists..."
                           class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#1DB954] transition"
                           oninput="onFilterChange()">
                </div>

                <!-- Genre Selector -->
                <div>
                    <select id="genreSelect" onchange="onFilterChange()"
                            class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition">
                        <option value="all">All Genres</option>
                        {% for g in top_genres %}
                        <option value="{{ g }}">{{ g.title() }}</option>
                        {% endfor %}
                    </select>
                </div>

                <!-- Sort Selector -->
                <div>
                    <select id="sortSelect" onchange="onFilterChange()"
                            class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-[#1DB954] transition">
                        <option value="plays_desc">Most Played</option>
                        <option value="plays_asc">Least Played / Unplayed</option>
                        <option value="added_desc">Recently Added</option>
                        <option value="year_desc">Release Year (Newest)</option>
                        <option value="artist_asc">Artist (A-Z)</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Album Grid -->
        <div id="albumGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            <!-- Populated via JS -->
        </div>

        <!-- Load More Trigger -->
        <div id="loadMoreTrigger" class="text-center py-10">
            <span class="text-xs text-gray-500">Showing <span id="displayedCount">0</span> of <span id="totalMatchCount">0</span> albums</span>
        </div>
    </div>

    <!-- 12" Gatefold Modal Markup -->
    <div id="gatefoldModal" class="fixed inset-0 z-50 hidden bg-black/85 backdrop-blur-md flex items-center justify-center p-2 sm:p-4 md:p-6" onclick="onModalBackdropClick(event)">
        <div class="relative w-full max-w-5xl bg-[#14181f] border border-gray-800 rounded-3xl shadow-2xl overflow-hidden flex flex-col md:flex-row h-[90vh] md:h-[620px]" onclick="event.stopPropagation()">
            <!-- Left 12" Panel: Cover Art & Streaming -->
            <div class="w-full md:w-5/12 bg-black/40 p-4 md:p-6 flex flex-col items-center justify-between border-b md:border-b-0 md:border-r border-gray-800/80">
                <div class="w-full flex justify-between items-center mb-3">
                    <span class="text-[10px] font-mono tracking-widest text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/20 font-bold uppercase">12" Gatefold Edition</span>
                    <button onclick="closeGatefold()" class="md:hidden text-gray-400 hover:text-white p-1 text-xl font-bold">&times;</button>
                </div>
                <div class="w-44 h-44 sm:w-56 sm:h-56 md:w-64 md:h-64 rounded-2xl overflow-hidden shadow-2xl border border-gray-800 my-auto">
                    <img id="modalCover" src="" class="w-full h-full object-cover">
                </div>
                <div class="w-full mt-4 flex flex-col gap-2">
                    <a id="modalSpotifyLink" href="#" target="_blank" class="w-full py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-xs flex items-center justify-center gap-2 transition shadow">
                        <span>Play on Spotify</span>
                    </a>
                </div>
            </div>

            <!-- Right 12" Panel: Liner Notes, Ratings & Reviews -->
            <div class="w-full md:w-7/12 p-4 md:p-6 flex flex-col justify-between overflow-y-auto custom-scroll">
                <div>
                    <div class="flex items-start justify-between gap-4 mb-2">
                        <div>
                            <h3 id="modalTitle" class="text-xl md:text-2xl font-black text-white leading-tight">--</h3>
                            <p id="modalArtist" class="text-sm font-semibold text-emerald-400 mt-0.5">--</p>
                        </div>
                        <button onclick="closeGatefold()" class="hidden md:block text-gray-400 hover:text-white p-1 text-2xl font-bold">&times;</button>
                    </div>

                    <!-- Scores & Badges -->
                    <div id="modalScores" class="flex flex-wrap items-center gap-2 my-3"></div>

                    <!-- Liner Notes Prose -->
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

                <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-[11px] text-gray-500">
                    <span id="modalMetaInfo">--</span>
                    <span class="text-emerald-500 font-mono">SpinSleeve Verified</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Client Script -->
    <script>
        const ALL_ALBUMS = {{ albums | tojson }};
        let filteredAlbums = [...ALL_ALBUMS];
        let displayLimit = 48;

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
                <div class="group relative flex flex-col cursor-pointer" onclick='openGatefold(${JSON.stringify(a).replace(/'/g, "&apos;")})'>
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

            displayLimit = 48;
            renderGrid();
        }

        function openGatefold(album) {
            document.getElementById("modalCover").src = album.album_image_url;
            document.getElementById("modalTitle").innerText = album.album_name;
            document.getElementById("modalArtist").innerText = album.album_artist_name;
            document.getElementById("modalSpotifyLink").href = album.album_url;

            const scoresContainer = document.getElementById("modalScores");
            scoresContainer.innerHTML = '';
            if (album.pitchfork_score) {
                scoresContainer.innerHTML += `<span class="px-2.5 py-1 bg-red-500/10 text-red-400 border border-red-500/20 rounded-md text-[11px] font-bold">Pitchfork ${album.pitchfork_score}</span>`;
            }
            if (album.metacritic_score) {
                scoresContainer.innerHTML += `<span class="px-2.5 py-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 rounded-md text-[11px] font-bold">Metacritic ${album.metacritic_score}</span>`;
            }
            if (album.discogs_rating) {
                scoresContainer.innerHTML += `<span class="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded-md text-[11px] font-bold">Discogs ${album.discogs_rating} ★</span>`;
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

        function closeGatefold() {
            document.getElementById("gatefoldModal").classList.add("hidden");
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
