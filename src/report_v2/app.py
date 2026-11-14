import os
import sys
# Ensure src is in python path for pipeline_v2 imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import time
import json
import gzip
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

from config import APP_VERSION, ICON_A_SVG, ADMIN_USER_IDS, PROJECT_ID
from routes.auth import auth_bp
from routes.crate import crate_bp
from routes.analytics import analytics_bp
from routes.pals import pals_bp
from routes.admin import admin_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_v2")

app = Flask(__name__)
app.register_blueprint(auth_bp)
app.register_blueprint(crate_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(pals_bp)
app.register_blueprint(admin_bp)

# Project & Dataset settings
PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = "spotify_v2"
PLAYBACK_HISTORY_TABLE = os.getenv("PLAYBACK_HISTORY_TABLE", f"{PROJECT_ID}.{DATASET_V2}.playback_history")
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

# Application Version (POLISH-04, POLISH-01, APP-04, POLISH-09, v2.6.4)
APP_VERSION = "v2.6.4"


@app.context_processor
def inject_globals():
    return {"app_version": APP_VERSION}


def get_datastore_client():
    return datastore.Client(project=PROJECT_ID)


def get_oauth_client(request_obj):
    """Builds a SpotifyOAuth client with a dynamic callback URL based on incoming request."""
    scheme = "https" if (request_obj.is_secure or request_obj.headers.get("X-Forwarded-Proto") == "https") else "http"
    host = request_obj.headers.get("X-Forwarded-Host") or request_obj.host
    redirect_uri = f"{scheme}://{host}/beta/callback"

    scope = "user-library-read user-library-modify user-read-recently-played user-read-email user-read-private"
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

# ==============================================================================
# MUSIC LEGEND ILLUSTRATED AVATARS (APP-04)
# ==============================================================================
AVATAR_PRESETS = [
    {"id": "beethoven", "name": "Ludwig van Beethoven", "era": "Classical", "badge": "🎹", "desc": "Romantic & classical titan"},
    {"id": "chet_baker", "name": "Chet Baker", "era": "Cool Jazz", "badge": "🎺", "desc": "West Coast jazz noir"},
    {"id": "miles_davis", "name": "Miles Davis", "era": "Modal Jazz", "badge": "🕶️", "desc": "Kind of Blue trumpet legend"},
    {"id": "bob_dylan", "name": "Bob Dylan", "era": "Folk / 60s", "badge": "🎸", "desc": "Counterculture poet"},
    {"id": "david_bowie", "name": "David Bowie", "era": "Glam Rock", "badge": "⚡", "desc": "Aladdin Sane chameleon"},
    {"id": "stevie_wonder", "name": "Stevie Wonder", "era": "Soul & Funk", "badge": "🎹", "desc": "Motown visionary"},
    {"id": "jimi_hendrix", "name": "Jimi Hendrix", "era": "Psychedelic Rock", "badge": "🎸", "desc": "Voodoo child virtuoso"},
    {"id": "fela_kuti", "name": "Fela Kuti", "era": "Afrobeat", "badge": "🎷", "desc": "Afrobeat pioneer & activist"},
    {"id": "madonna", "name": "Madonna", "era": "80s Pop", "badge": "👑", "desc": "Queen of Pop & reinvention"},
    {"id": "amy_winehouse", "name": "Amy Winehouse", "era": "Neo-Soul", "badge": "🎤", "desc": "Camden beehive & jazz voice"},
    {"id": "daft_punk", "name": "Daft Punk", "era": "French House", "badge": "🤖", "desc": "Chrome helmet electronic duo"},
    {"id": "drake", "name": "Drake", "era": "Hip-Hop / R&B", "badge": "🦉", "desc": "Certified Lover Boy & OVO"}
]

AVATAR_SVGS = {
    "beethoven": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-beethoven" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-beethoven)" stroke="#64748b" stroke-width="2"/>
  <path d="M22 56 C14 42 16 26 30 18 C40 12 60 12 70 18 C84 26 86 42 78 56 C82 46 80 30 68 22 C58 16 42 16 32 22 C20 30 18 46 22 56 Z" fill="#cbd5e1"/>
  <path d="M18 48 C14 36 22 24 34 20 C24 26 22 38 24 50 Z" fill="#94a3b8"/>
  <path d="M82 48 C86 36 78 24 66 20 C76 26 78 38 76 50 Z" fill="#94a3b8"/>
  <path d="M34 38 Q50 34 66 38 Q68 56 62 68 Q50 76 38 68 Q32 56 34 38 Z" fill="#fed7aa"/>
  <path d="M40 45 Q46 44 49 47" stroke="#334155" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M60 45 Q54 44 51 47" stroke="#334155" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <circle cx="45" cy="50" r="2" fill="#1e293b"/>
  <circle cx="55" cy="50" r="2" fill="#1e293b"/>
  <path d="M50 48 L48 57 L52 57" stroke="#ea580c" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  <path d="M44 63 Q50 62 56 63" stroke="#9a3412" stroke-width="2" stroke-linecap="round"/>
  <polygon points="26,96 32,72 42,76 36,96" fill="#e2e8f0"/>
  <polygon points="74,96 68,72 58,76 64,96" fill="#e2e8f0"/>
  <polygon points="40,73 50,82 60,73 55,96 45,96" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <polygon points="22,96 30,72 18,80 14,96" fill="#1e293b"/>
  <polygon points="78,96 70,72 82,80 86,96" fill="#1e293b"/>
  <rect x="36" y="92" width="28" height="6" rx="1" fill="#ffffff"/>
  <rect x="41" y="92" width="3" height="4" fill="#0f172a"/>
  <rect x="47" y="92" width="3" height="4" fill="#0f172a"/>
  <rect x="56" y="92" width="3" height="4" fill="#0f172a"/>
</svg>""",

    "chet_baker": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-chet" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#050515"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-chet)" stroke="#4338ca" stroke-width="2"/>
  <path d="M28 36 C28 20 40 16 56 16 C70 16 76 24 76 36 C76 40 70 30 56 26 C40 22 30 30 28 36 Z" fill="#1e293b"/>
  <path d="M34 36 C38 28 58 26 66 34 C72 40 72 54 66 64 C60 72 48 72 40 68 L36 54 Z" fill="#fed7aa"/>
  <path d="M44 42 Q50 40 54 43" stroke="#312e81" stroke-width="2" stroke-linecap="round" fill="none"/>
  <circle cx="50" cy="45" r="2" fill="#1e1b4b"/>
  <path d="M58 52 C54 58 48 62 42 63" stroke="#d97706" stroke-width="1.5" fill="none" opacity="0.6"/>
  <polygon points="46,54 20,62 18,68 48,57" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
  <rect x="28" y="57" width="3" height="7" fill="#fbbf24"/>
  <rect x="33" y="55" width="3" height="7" fill="#fbbf24"/>
  <rect x="38" y="53" width="3" height="7" fill="#fbbf24"/>
  <polygon points="18,56 8,52 6,72 18,68" fill="#fbbf24" stroke="#d97706" stroke-width="1.5"/>
  <ellipse cx="7" cy="62" rx="2" ry="10" fill="#f59e0b"/>
  <path d="M6 55 Q-2 62 6 69" stroke="#818cf8" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.8"/>
  <path d="M24 96 C24 76 40 72 50 72 C64 72 80 76 80 96 Z" fill="#0f172a"/>
</svg>""",

    "miles_davis": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-miles" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#0369a1"/>
      <stop offset="100%" stop-color="#04182e"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-miles)" stroke="#0284c7" stroke-width="2"/>
  <path d="M36 34 C36 22 46 18 58 18 C70 18 76 26 76 38 C76 52 70 66 58 70 C48 72 38 64 36 50 Z" fill="#451a03"/>
  <rect x="42" y="38" width="26" height="10" rx="2" fill="#0f172a"/>
  <polygon points="45,40 52,40 48,46 43,46" fill="#38bdf8" opacity="0.7"/>
  <polygon points="57,40 64,40 60,46 55,46" fill="#38bdf8" opacity="0.7"/>
  <path d="M22 96 C22 74 38 70 54 70 C70 70 82 74 82 96 Z" fill="#18181b"/>
  <polygon points="48,70 54,84 60,70" fill="#dc2626"/>
  <polygon points="48,56 32,74 28,70 46,52" fill="#eab308" stroke="#ca8a04" stroke-width="1"/>
  <polygon points="32,74 22,84 16,78 28,70" fill="#eab308"/>
  <ellipse cx="19" cy="81" rx="5" ry="7" fill="#dc2626" stroke="#991b1b" stroke-width="1.5"/>
  <circle cx="19" cy="81" r="2.5" fill="#18181b"/>
</svg>""",

    "bob_dylan": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-dylan" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#78350f"/>
      <stop offset="100%" stop-color="#1c0d02"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-dylan)" stroke="#b45309" stroke-width="2"/>
  <path d="M24 44 C18 32 24 16 38 14 C48 12 64 12 72 16 C84 22 86 36 80 48 C84 38 82 24 70 18 C58 14 42 16 30 22 C22 28 20 38 24 44 Z" fill="#451a03"/>
  <circle cx="30" cy="26" r="8" fill="#451a03"/>
  <circle cx="44" cy="18" r="8" fill="#542305"/>
  <circle cx="60" cy="18" r="9" fill="#451a03"/>
  <circle cx="74" cy="28" r="8" fill="#542305"/>
  <path d="M35 34 Q50 30 65 34 Q68 54 62 66 Q50 74 38 66 Q33 54 35 34 Z" fill="#fed7aa"/>
  <rect x="36" y="38" width="13" height="10" rx="2" fill="#18181b"/>
  <rect x="51" y="38" width="13" height="10" rx="2" fill="#18181b"/>
  <rect x="47" y="40" width="6" height="2.5" fill="#18181b"/>
  <path d="M30 82 L34 65 L40 64" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" fill="none"/>
  <path d="M70 82 L66 65 L60 64" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" fill="none"/>
  <rect x="36" y="62" width="28" height="6" rx="1.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1"/>
  <line x1="39" y1="65" x2="61" y2="65" stroke="#475569" stroke-width="1.5" stroke-dasharray="2 2"/>
  <polygon points="22,96 32,78 42,84 38,96" fill="#92400e"/>
  <polygon points="78,96 68,78 58,84 62,96" fill="#92400e"/>
  <polygon points="42,84 50,96 58,84" fill="#1e3a8a"/>
</svg>""",

    "david_bowie": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-bowie" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#0c0a1f"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-bowie)" stroke="#ec4899" stroke-width="2"/>
  <path d="M24 48 C16 34 22 18 36 14 C48 10 66 12 76 18 C86 26 84 42 78 52 C74 38 68 20 50 18 C34 18 26 32 24 48 Z" fill="#f97316"/>
  <polygon points="30,18 36,8 44,16 52,8 60,16 68,10 70,20" fill="#ea580c"/>
  <path d="M34 34 Q50 30 66 34 Q68 56 60 70 Q50 78 40 70 Q32 56 34 34 Z" fill="#ffedd5"/>
  <polygon points="54,22 62,38 54,44 66,66 58,54 62,46 50,24" fill="#06b6d4"/>
  <polygon points="52,22 60,38 52,44 64,66 56,54 60,46 48,24" fill="#ef4444"/>
  <path d="M39 46 Q44 43 48 46" stroke="#475569" stroke-width="1.8" fill="none"/>
  <circle cx="43" cy="48" r="2.2" fill="#0284c7"/>
  <path d="M45 66 Q50 68 55 66" stroke="#e11d48" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M20 96 C24 78 38 74 50 74 C62 74 76 78 80 96 Z" fill="#0f172a"/>
  <polygon points="42,74 50,86 58,74" fill="#f43f5e"/>
  <circle cx="50" cy="74" r="3" fill="#fbbf24"/>
</svg>""",

    "stevie_wonder": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-stevie" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#b45309"/>
      <stop offset="100%" stop-color="#3b1d06"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-stevie)" stroke="#f59e0b" stroke-width="2"/>
  <path d="M26 38 C26 22 36 16 50 16 C64 16 74 22 74 38 Z" fill="#18181b"/>
  <line x1="28" y1="36" x2="24" y2="56" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="24" cy="56" r="2.5" fill="#fbbf24"/>
  <line x1="32" y1="34" x2="28" y2="60" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="28" cy="60" r="2.5" fill="#fbbf24"/>
  <line x1="68" y1="34" x2="72" y2="60" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="72" cy="60" r="2.5" fill="#fbbf24"/>
  <line x1="72" y1="36" x2="76" y2="56" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="76" cy="56" r="2.5" fill="#fbbf24"/>
  <path d="M33 34 Q50 30 67 34 Q70 56 64 68 Q50 76 36 68 Q30 56 33 34 Z" fill="#78350f"/>
  <rect x="34" y="38" width="14" height="11" rx="3" fill="#18181b" stroke="#fbbf24" stroke-width="1.5"/>
  <rect x="52" y="38" width="14" height="11" rx="3" fill="#18181b" stroke="#fbbf24" stroke-width="1.5"/>
  <line x1="48" y1="42" x2="52" y2="42" stroke="#fbbf24" stroke-width="2"/>
  <path d="M40 58 Q50 70 60 58 Z" fill="#ffffff" stroke="#451a03" stroke-width="1"/>
  <path d="M20 96 C24 76 38 72 50 72 C62 72 76 76 80 96 Z" fill="#15803d"/>
  <polygon points="44,72 50,86 56,72" fill="#f59e0b"/>
</svg>""",

    "jimi_hendrix": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-hendrix" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#6b21a8"/>
      <stop offset="100%" stop-color="#1e0836"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-hendrix)" stroke="#c084fc" stroke-width="2"/>
  <circle cx="50" cy="40" r="32" fill="#18181b"/>
  <circle cx="28" cy="42" r="14" fill="#18181b"/>
  <circle cx="72" cy="42" r="14" fill="#18181b"/>
  <path d="M26 40 Q50 34 74 40 L73 47 Q50 41 27 47 Z" fill="#ec4899"/>
  <polygon points="24,44 16,54 22,56 26,46" fill="#f43f5e"/>
  <path d="M35 44 Q50 40 65 44 Q67 60 62 70 Q50 78 38 70 Q33 60 35 44 Z" fill="#854d0e"/>
  <path d="M40 50 Q45 48 48 51" stroke="#291807" stroke-width="2" fill="none"/>
  <path d="M60 50 Q55 48 52 51" stroke="#291807" stroke-width="2" fill="none"/>
  <path d="M42 62 Q50 64 58 62 Q54 67 50 65 Q46 67 42 62 Z" fill="#18181b"/>
  <circle cx="50" cy="69" r="1.5" fill="#18181b"/>
  <path d="M20 96 C24 76 38 72 50 72 C62 72 76 76 80 96 Z" fill="#3b0764"/>
  <line x1="36" y1="80" x2="64" y2="80" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="38" y1="88" x2="62" y2="88" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
</svg>""",

    "fela_kuti": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-fela" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ea580c"/>
      <stop offset="100%" stop-color="#431407"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-fela)" stroke="#fb923c" stroke-width="2"/>
  <path d="M34 32 C34 20 44 16 54 16 C64 16 70 20 70 32 Q72 56 64 68 Q54 76 40 68 Q32 56 34 32 Z" fill="#713f12"/>
  <path d="M34 32 C34 20 44 16 54 16 C64 16 70 20 70 32 Q54 26 34 32 Z" fill="#18181b"/>
  <ellipse cx="44" cy="42" rx="3.5" ry="2" fill="#ffffff"/>
  <circle cx="44" cy="42" r="1.8" fill="#18181b"/>
  <ellipse cx="60" cy="42" rx="3.5" ry="2" fill="#ffffff"/>
  <circle cx="60" cy="42" r="1.8" fill="#18181b"/>
  <circle cx="38" cy="48" r="1.5" fill="#ffffff"/>
  <circle cx="42" cy="50" r="1.5" fill="#ffffff"/>
  <circle cx="46" cy="51" r="1.5" fill="#ffffff"/>
  <circle cx="58" cy="51" r="1.5" fill="#ffffff"/>
  <circle cx="62" cy="50" r="1.5" fill="#ffffff"/>
  <circle cx="66" cy="48" r="1.5" fill="#ffffff"/>
  <path d="M52 64 C56 70 56 80 50 86 C44 92 34 88 32 80 L36 80 C37 84 43 87 46 84 C49 80 49 72 46 66 Z" fill="#f59e0b"/>
  <polygon points="30,76 24,72 26,84 34,82" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>
  <path d="M22 96 C24 76 36 72 46 72 L50 84 L54 72 C64 72 76 76 78 96 Z" fill="#eab308"/>
</svg>""",

    "madonna": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-madonna" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#db2777"/>
      <stop offset="100%" stop-color="#3f0723"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-madonna)" stroke="#f472b6" stroke-width="2"/>
  <path d="M22 46 C16 30 24 16 38 14 C48 12 62 12 72 16 C86 22 86 38 80 50 C86 36 82 22 68 18 C56 14 40 16 28 24 C22 30 20 40 22 46 Z" fill="#fef08a"/>
  <path d="M42 16 C34 10 32 6 38 6 C44 6 46 12 48 16 Z" fill="#18181b"/>
  <path d="M58 16 C66 10 68 6 62 6 C56 6 54 12 52 16 Z" fill="#18181b"/>
  <circle cx="50" cy="16" r="3.5" fill="#27272a"/>
  <path d="M36 34 Q50 30 64 34 Q68 54 60 68 Q50 76 40 68 Q32 54 36 34 Z" fill="#fed7aa"/>
  <path d="M40 40 Q45 37 49 40" stroke="#18181b" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M60 40 Q55 37 51 40" stroke="#18181b" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <polygon points="41,45 48,45 46,47" fill="#18181b"/>
  <polygon points="59,45 52,45 54,47" fill="#18181b"/>
  <path d="M44 61 Q50 65 56 61 Q50 67 44 61 Z" fill="#e11d48"/>
  <circle cx="43" cy="59" r="1.2" fill="#18181b"/>
  <path d="M24 96 C26 78 38 72 50 72 C62 72 74 78 76 96 Z" fill="#09090b"/>
  <line x1="50" y1="74" x2="50" y2="88" stroke="#e2e8f0" stroke-width="1.8"/>
  <line x1="46" y1="78" x2="54" y2="78" stroke="#e2e8f0" stroke-width="1.8"/>
</svg>""",

    "amy_winehouse": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-amy" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#0d9488"/>
      <stop offset="100%" stop-color="#042f2e"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-amy)" stroke="#2dd4bf" stroke-width="2"/>
  <path d="M30 46 C24 34 26 10 50 8 C74 10 76 34 70 46 C76 36 74 16 50 14 C26 16 24 36 30 46 Z" fill="#09090b"/>
  <ellipse cx="50" cy="24" rx="22" ry="16" fill="#09090b"/>
  <circle cx="32" cy="26" r="6" fill="#ef4444"/>
  <circle cx="30" cy="24" r="2" fill="#fde047"/>
  <path d="M35 40 Q50 36 65 40 Q67 58 61 70 Q50 78 39 70 Q33 58 35 40 Z" fill="#fed7aa"/>
  <polygon points="38,48 49,46 48,48 36,46" fill="#09090b"/>
  <polygon points="62,48 51,46 52,48 64,46" fill="#09090b"/>
  <path d="M44 64 Q50 67 56 64 Q50 69 44 64 Z" fill="#dc2626"/>
  <circle cx="43" cy="59" r="1.2" fill="#09090b"/>
  <ellipse cx="33" cy="54" rx="2" ry="6" fill="none" stroke="#fbbf24" stroke-width="2"/>
  <path d="M22 96 C24 78 38 74 50 74 C62 74 76 78 78 96 Z" fill="#18181b"/>
  <polygon points="42,74 50,86 58,74" fill="#fed7aa"/>
</svg>""",

    "daft_punk": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-daft" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1f2937"/>
      <stop offset="100%" stop-color="#030712"/>
    </radialGradient>
    <linearGradient id="visor-led" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ef4444"/>
      <stop offset="25%" stop-color="#f59e0b"/>
      <stop offset="50%" stop-color="#10b981"/>
      <stop offset="75%" stop-color="#06b6d4"/>
      <stop offset="100%" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-daft)" stroke="#fbbf24" stroke-width="2"/>
  <path d="M28 44 C28 24 38 16 50 16 C62 16 72 24 72 44 Q74 62 66 70 Q50 76 34 70 Q26 62 28 44 Z" fill="#fbbf24" stroke="#d97706" stroke-width="2"/>
  <polygon points="34,66 50,74 66,66 62,76 50,80 38,76" fill="#ca8a04"/>
  <circle cx="26" cy="48" r="4.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
  <circle cx="74" cy="48" r="4.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
  <path d="M30 42 Q50 38 70 42 L68 54 Q50 50 32 54 Z" fill="#09090b" stroke="#ca8a04" stroke-width="1"/>
  <path d="M32 44 Q50 40 68 44 L67 52 Q50 48 33 52 Z" fill="url(#visor-led)"/>
  <line x1="33" y1="48" x2="67" y2="48" stroke="#ffffff" stroke-width="1" opacity="0.8"/>
  <path d="M20 96 C24 78 36 74 50 74 C64 74 76 78 80 96 Z" fill="#09090b"/>
  <line x1="50" y1="76" x2="50" y2="96" stroke="#94a3b8" stroke-width="2" stroke-dasharray="3 1"/>
</svg>""",

    "drake": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-drake" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#713f12"/>
      <stop offset="100%" stop-color="#0a0a0a"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-drake)" stroke="#eab308" stroke-width="2"/>
  <path d="M32 36 C32 20 42 16 52 16 C62 16 70 20 70 36 Z" fill="#18181b"/>
  <path d="M40 22 C38 19 35 20 35 23 C35 25 39 28 40 29 C41 28 45 25 45 23 C45 20 42 19 40 22 Z" fill="#fde047"/>
  <path d="M34 36 Q52 32 68 36 Q70 56 64 68 Q52 76 38 68 Q32 56 34 36 Z" fill="#9a3412"/>
  <ellipse cx="44" cy="44" rx="3" ry="1.8" fill="#18181b"/>
  <ellipse cx="58" cy="44" rx="3" ry="1.8" fill="#18181b"/>
  <path d="M36 54 C36 70 44 76 52 76 C60 76 66 70 66 54 C66 58 60 62 52 62 C44 62 36 58 36 54 Z" fill="#18181b"/>
  <path d="M44 56 Q52 54 58 56 Q52 59 44 56 Z" fill="#18181b"/>
  <path d="M20 96 C24 76 36 72 52 72 C66 72 78 76 82 96 Z" fill="#1c1917"/>
  <path d="M42 74 Q52 86 60 74" stroke="#fbbf24" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="51" cy="85" r="4" fill="#fbbf24"/>
  <circle cx="49.5" cy="84" r="1.2" fill="#1c1917"/>
  <circle cx="52.5" cy="84" r="1.2" fill="#1c1917"/>
</svg>"""
}


@app.context_processor
def inject_admin_context():
    real_admin = session.get("admin_user_id") or session.get("user_id")
    is_admin = (real_admin in ADMIN_USER_IDS) or (session.get("role") == "admin")
    return {
        "is_admin": is_admin,
        "is_impersonating": bool(session.get("is_impersonating", False)),
        "admin_user_id": session.get("admin_user_id"),
        "avatar_presets": AVATAR_PRESETS
    }


@app.route("/favicon.svg")
@app.route("/favicon.ico")
@app.route("/beta/favicon.svg")
@app.route("/beta/favicon.ico")
def favicon():
    return Response(ICON_A_SVG, mimetype="image/svg+xml")


@app.route("/avatar/<avatar_id>.svg")
@app.route("/avatar/<avatar_id>")
@app.route("/beta/avatar/<avatar_id>.svg")
@app.route("/beta/avatar/<avatar_id>")
def serve_avatar(avatar_id):
    """Serves high-fidelity vector avatars for music legends (APP-04)."""
    clean_id = avatar_id.replace(".svg", "").strip().lower()
    if clean_id in AVATAR_SVGS:
        return Response(
            AVATAR_SVGS[clean_id],
            mimetype="image/svg+xml",
            headers={"Cache-Control": "public, max-age=604800, immutable"}
        )
    return "Avatar persona not found", 404


# ==============================================================================
# AUTHENTICATION & ACCESS CONTROL HELPERS
# ==============================================================================
# @app.before_request
# def local_dev_auth_bypass():
#     """Bypasses Spotify OAuth when testing locally on localhost or 127.0.0.1."""
#     host = request.headers.get("X-Forwarded-Host") or request.host or ""
#     if host.startswith("localhost") or host.startswith("127.0.0.1"):
#         if "user_id" not in session:
#             session["user_id"] = "sergebou"
#             session["display_name"] = "Serge"
#             session["role"] = "admin"
#             session["is_admin"] = True


@app.route("/dev/login")
def dev_login():
    """Local development helper to switch or initialize test sessions without Spotify OAuth."""
    host = request.headers.get("X-Forwarded-Host") or request.host or ""
    if not (host.startswith("localhost") or host.startswith("127.0.0.1")):
        return redirect("/login")
    user = request.args.get("user", "sergebou")
    name = "Serge" if user == "sergebou" else ("Sarah" if user == "sarahboosch" else user)
    session["user_id"] = user
    session["display_name"] = name
    session["role"] = "admin" if user in ADMIN_USER_IDS else "user"
    session["is_admin"] = (user in ADMIN_USER_IDS)
    return redirect("/")


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/login")
        if session.get("role") != "admin" and session.get("user_id") not in ADMIN_USER_IDS and session.get("admin_user_id") not in ADMIN_USER_IDS:
            return redirect("/")
        return f(*args, **kwargs)
    return decorated_function





def invalidate_user_catalog_cache(user_id):
    """Deletes cached catalog in Datastore when new listening events are synced (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        ds_client.delete(key)
        if user_id in _user_album_cache:
            del _user_album_cache[user_id]
        if user_id in _user_album_cache_time:
            del _user_album_cache_time[user_id]
        logger.info("[%s] Invalidated Datastore UserCatalogCache & in-memory cache.", user_id)
    except Exception as e:
        logger.warning("[%s] Failed to invalidate Datastore UserCatalogCache: %s", user_id, e)

def rematerialize_user_albums_features(bq_client):
    """Materializes the dynamic user_albums_features view into a clustered physical table (INFRA-03a)."""
    logger.info("Materializing %s.user_albums_features_table...", DATASET_V2)
    remat_q = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
    CLUSTER BY user_id AS
    SELECT * FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features`
    """
    try:
        job = bq_client.query(remat_q)
        job.result()
        logger.info("Successfully refreshed %s.user_albums_features_table!", DATASET_V2)
    except Exception as e:
        logger.error("Error refreshing materialized user_albums_features_table: %s", e)


@app.route("/api/user/upload-history", methods=["POST"])
@app.route("/beta/api/user/upload-history", methods=["POST"])
@login_required
def api_upload_history():
    """Uploads and ingests Spotify streaming history JSON files for the active user (APP-13)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    if "files" not in request.files:
        return jsonify({"status": "error", "message": "No files provided"}), 400

    files = request.files.getlist("files")
    if not files or all(f.filename == '' for f in files):
        return jsonify({"status": "error", "message": "No selected files"}), 400

    logger.info("[%s] Starting history upload/ingestion request (files=%d)...", user_id, len(files))

    try:
        from pipeline_v2.history_parser import parse_spotify_history_json
        
        bq_client = bigquery.Client(project=PROJECT_ID)
        all_dfs = []

        for file in files:
            filename = file.filename.lower()
            if filename.endswith('.zip'):
                logger.info("[%s] Extracting and parsing ZIP archive: %s", user_id, file.filename)
                import zipfile, io
                zip_bytes = file.read()
                try:
                    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                        for sub_name in z.namelist():
                            if ("Streaming_History_Audio_" in sub_name or "StreamingHistory_music_" in sub_name) and sub_name.endswith(".json"):
                                with z.open(sub_name) as zf:
                                    content = zf.read().decode('utf-8', errors='ignore')
                                    df_file = parse_spotify_history_json(content, user_id)
                                    if not df_file.empty:
                                        all_dfs.append(df_file)
                                        logger.info("[%s]  -> Parsed %d scrobbles from %s", user_id, len(df_file), sub_name)
                except Exception as ze:
                    logger.warning("[%s] Failed to parse uploaded zip %s: %s", user_id, file.filename, ze)
            else:
                logger.info("[%s] Parsing JSON file: %s", user_id, file.filename)
                content = file.read().decode('utf-8', errors='ignore')
                df_file = parse_spotify_history_json(content, user_id)
                if not df_file.empty:
                    all_dfs.append(df_file)
                    logger.info("[%s]  -> Parsed %d scrobbles from %s", user_id, len(df_file), file.filename)

        if not all_dfs:
            return jsonify({"status": "error", "message": "No valid scrobbles found in uploaded JSON files."}), 400

        combined_df = pd.concat(all_dfs, ignore_index=True)
        if combined_df.empty:
            return jsonify({"status": "error", "message": "Parsed dataframe is empty."}), 400

        # Deduplicate to guarantee strict idempotency (prevent duplicate plays if JSON files overlap/duplicate)
        combined_df = combined_df.drop_duplicates(subset=["user_id", "played_at", "track_name", "artist_name"])

        logger.info("[%s] Total unique valid scrobbles parsed: %d. Processing year-by-year...", user_id, len(combined_df))

        # Extract year for batching to respect BigQuery's 4,000 partition DML limit
        combined_df["year"] = combined_df["played_at"].dt.year
        years = sorted(combined_df["year"].unique())
        safe_uid = user_id.replace("-", "_")

        for yr in years:
            df_year = combined_df[combined_df["year"] == yr].drop(columns=["year"])
            if df_year.empty:
                continue

            logger.info("[%s] --- Ingesting Year %d (%d scrobbles) ---", user_id, yr, len(df_year))
            staging_table = f"{PROJECT_ID}.{DATASET_V2}.playback_history_staging_ui_{safe_uid}_{yr}"

            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            )
            load_job = bq_client.load_table_from_dataframe(df_year, staging_table, job_config=job_config)
            load_job.result()

            merge_query = f"""
            MERGE `{PLAYBACK_HISTORY_TABLE}` T
            USING `{staging_table}` S
            ON T.user_id = S.user_id
               AND T.played_at = S.played_at
               AND T.track_name = S.track_name
               AND T.artist_name = S.artist_name
            WHEN NOT MATCHED THEN
              INSERT (user_id, played_at, track_uri, track_id, track_name, artist_id, artist_name, album_id, album_name)
              VALUES (user_id, played_at, track_uri, track_id, track_name, artist_id, artist_name, album_id, album_name)
            """
            merge_job = bq_client.query(merge_query)
            merge_job.result()
            bq_client.delete_table(staging_table, not_found_ok=True)

        # Rematerialize features table and invalidate cache so Library Explorer updates instantly
        rematerialize_user_albums_features(bq_client)
        invalidate_user_catalog_cache(user_id)

        logger.info("[%s] Successfully completed web history upload workflow (%d scrobbles processed)!", user_id, len(combined_df))

        return jsonify({
            "status": "success",
            "imported_count": len(combined_df),
            "message": f"Successfully ingested {len(combined_df):,} historical scrobbles!"
        })

    except Exception as e:
        logger.error("[%s] Error uploading history: %s", user_id, e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


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


def compute_normalized_album_plays(track_plays, tracks_total, is_30d=False, added_at=None):
    """
    Computes normalized complete album spins, display badge string, and hover tooltip (APP-05, APP-06, POLISH-03).
    Formula: round(track_plays / tracks_total, 1) if tracks_total > 0 else track_plays
    Fallback: If tracks_total is unavailable or <= 0, uses track scrobbles.
    When track_plays == 0, checks if newly added (within 14 days) or never played.
    When is_30d=True, adds 30-day context to the label and tooltip.
    """
    track_plays = safe_int(track_plays)
    tracks_total = safe_int(tracks_total)

    period_label = "in last 30 days " if is_30d else ""
    badge_suffix = " (30D)" if is_30d else ""

    if track_plays == 0:
        is_new = False
        if added_at:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromisoformat(str(added_at).replace('Z', '+00:00'))
                delta = datetime.now(timezone.utc) - dt
                if delta.days <= 14:
                    is_new = True
            except Exception:
                pass
        display_badge = "✨ Newly Added" if is_new else "💤 Never Played"
        tooltip = "Newly added album (0 plays)" if is_new else "Never played (0 plays)"
        return 0.0, display_badge, tooltip

    if tracks_total > 0:
        decimal_plays = round(track_plays / tracks_total, 1)
        disp_val = int(decimal_plays) if decimal_plays.is_integer() else decimal_plays
        tooltip = f"Estimated complete album spins {period_label}based on {track_plays} track plays across {tracks_total} tracks".strip()
        display_badge = f"🔥 {disp_val} Play{badge_suffix}" if disp_val == 1 else f"🔥 {disp_val} Plays{badge_suffix}"
        return decimal_plays, display_badge, tooltip
    else:
        decimal_plays = float(track_plays)
        disp_val = int(decimal_plays) if decimal_plays.is_integer() else decimal_plays
        period_name = "30-day track plays" if is_30d else "Total track plays"
        tooltip = f"{period_name}: {track_plays} (track count unavailable)"
        display_badge = f"🔥 {disp_val} Play{badge_suffix}" if disp_val == 1 else f"🔥 {disp_val} Plays{badge_suffix}"
        return decimal_plays, display_badge, tooltip


# ==============================================================================
# MULTI-TENANT BIGQUERY ENGINE & INITIAL SYNC
# ==============================================================================
_user_album_cache = {}
_user_album_cache_time = {}
_user_analytics_cache = {}
_user_analytics_cache_time = {}
CACHE_TTL = 60
DATASTORE_CACHE_TTL = 86400  # 24 hours


def get_catalog_from_datastore(user_id):
    """Retrieves and decompresses user catalog payload from Cloud Datastore (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        entity = ds_client.get(key)
        if not entity:
            return None

        updated_at = entity.get("updated_at")
        if updated_at:
            if hasattr(updated_at, "timestamp"):
                age = time.time() - updated_at.timestamp()
            else:
                age = 0
            if age > DATASTORE_CACHE_TTL:
                logger.info("[%s] Datastore UserCatalogCache expired (age=%.0fs)", user_id, age)
                return None

        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None

        decompressed_json = gzip.decompress(raw_bytes).decode("utf-8")
        data = json.loads(decompressed_json)
        logger.info("[%s] Loaded catalog from Cloud Datastore cache (albums=%d)", user_id, len(data.get("albums", [])))
        return data
    except Exception as e:
        logger.warning("[%s] Failed to read catalog from Cloud Datastore cache: %s", user_id, e)
        return None


def save_catalog_to_datastore(user_id, data):
    """Serializes, gzips, and stores user catalog payload into Cloud Datastore (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])

        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))

        entity["compressed_payload"] = compressed_bytes
        entity["album_count"] = len(data.get("albums", []))
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        entity["uncompressed_kb"] = round(len(raw_json) / 1024, 1)
        entity["compressed_kb"] = round(len(compressed_bytes) / 1024, 1)

        ds_client.put(entity)
        logger.info("[%s] Saved catalog to Cloud Datastore (albums=%d, raw=%.1fKB, compressed=%.1fKB)",
                    user_id, entity["album_count"], entity["uncompressed_kb"], entity["compressed_kb"])
    except Exception as e:
        logger.warning("[%s] Failed to save catalog to Cloud Datastore cache: %s", user_id, e)


def get_pal_compatibility_from_datastore(current_user_id, pal_id, horizon):
    """Retrieves and decompresses pal compatibility payload from Cloud Datastore (INFRA-03c)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{current_user_id}::{pal_id}::{horizon}"
        key = ds_client.key("PalCompatibilityCache", cache_key_name)
        entity = ds_client.get(key)
        if not entity:
            return None
        updated_at = entity.get("updated_at")
        if updated_at:
            age = time.time() - updated_at.timestamp() if hasattr(updated_at, "timestamp") else 0
            if age > DATASTORE_CACHE_TTL:
                return None
        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None
        return json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
    except Exception as e:
        logger.warning("Failed to read pal compatibility from Datastore cache: %s", e)
        return None


def save_pal_compatibility_to_datastore(current_user_id, pal_id, horizon, data):
    """Serializes, gzips, and stores pal compatibility payload into Cloud Datastore (INFRA-03c)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{current_user_id}::{pal_id}::{horizon}"
        key = ds_client.key("PalCompatibilityCache", cache_key_name)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])
        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))
        entity["compressed_payload"] = compressed_bytes
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        ds_client.put(entity)
    except Exception as e:
        logger.warning("Failed to save pal compatibility to Datastore cache: %s", e)


def get_analytics_from_datastore(user_id, range_param):
    """Retrieves and decompresses user analytics telemetry payload from Cloud Datastore (INFRA-03d)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{user_id}::{range_param}"
        key = ds_client.key("UserAnalyticsCache", cache_key_name)
        entity = ds_client.get(key)
        if not entity:
            return None
        updated_at = entity.get("updated_at")
        if updated_at:
            age = time.time() - updated_at.timestamp() if hasattr(updated_at, "timestamp") else 0
            if age > DATASTORE_CACHE_TTL:
                return None
        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None
        return json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
    except Exception as e:
        logger.warning("[%s] Failed to read analytics from Datastore cache: %s", user_id, e)
        return None


def save_analytics_to_datastore(user_id, range_param, data):
    """Serializes, gzips, and stores user analytics telemetry payload into Cloud Datastore (INFRA-03d)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{user_id}::{range_param}"
        key = ds_client.key("UserAnalyticsCache", cache_key_name)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])
        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))
        entity["compressed_payload"] = compressed_bytes
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        ds_client.put(entity)
    except Exception as e:
        logger.warning("[%s] Failed to save analytics to Datastore cache: %s", user_id, e)


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
            table_ref = PLAYBACK_HISTORY_TABLE
            job = bq_client.load_table_from_dataframe(df_tracks, table_ref)
            job.result()
            logger.info("Loaded %d initial tracks for %s into %s", len(df_tracks), user_id, table_ref)

    except Exception as e:
        logger.error("Error during initial sync for %s: %s", user_id, e)


def fetch_user_album_data(user_id, force_refresh=False):
    global _user_album_cache, _user_album_cache_time
    now = time.time()

    # Tier 1: Local process in-memory cache (0ms)
    if not force_refresh and user_id in _user_album_cache and (now - _user_album_cache_time.get(user_id, 0)) < CACHE_TTL:
        return _user_album_cache[user_id]

    # Tier 2: Cloud Datastore Document Store Cache (~50ms - INFRA-03b)
    if not force_refresh:
        cached_doc = get_catalog_from_datastore(user_id)
        if cached_doc:
            _user_album_cache[user_id] = cached_doc
            _user_album_cache_time[user_id] = now
            return cached_doc

    # Tier 3: BigQuery Materialized Table
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
    SELECT *
    FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
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
            "kpis": {"total_albums": 0, "played_albums": 0, "played_albums_30d": 0, "unplayed_albums": 0, "pct_explored": 0, "total_plays": 0, "total_plays_30d": 0, "top_album": "None", "top_album_plays": 0}
        }
        save_catalog_to_datastore(user_id, empty_data)
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

        tracks_total = safe_int(row.get("album_tracks_total"))
        track_plays = safe_int(row.get("album_track_plays"))
        track_plays_30d = safe_int(row.get("album_track_plays_30d"))
        added_at_val = row.get("added_at")
        norm_plays, plays_display, plays_tooltip = compute_normalized_album_plays(track_plays, tracks_total, added_at=added_at_val)
        norm_plays_30d, plays_display_30d, plays_tooltip_30d = compute_normalized_album_plays(track_plays_30d, tracks_total, is_30d=True, added_at=added_at_val)

        item = {
            "album_id": safe_str(row.get("album_id")),
            "album_name": safe_str(row.get("album_name"), "Unknown Album"),
            "album_artist_name": safe_str(row.get("album_artist_name"), "Unknown Artist"),
            "album_release_date": safe_str(row.get("album_release_date")),
            "release_year": safe_str(row.get("release_year")),
            "album_type": safe_str(row.get("album_type"), "album"),
            "album_label": safe_str(row.get("album_label")),
            "album_tracks_total": tracks_total,
            "album_track_plays": track_plays,
            "album_plays": safe_float(row.get("album_plays")),
            "album_normalized_plays": norm_plays,
            "album_plays_display": plays_display,
            "album_plays_tooltip": plays_tooltip,
            "album_track_plays_30d": track_plays_30d,
            "album_plays_30d": safe_float(row.get("album_plays_30d")),
            "album_normalized_plays_30d": norm_plays_30d,
            "album_plays_display_30d": plays_display_30d,
            "album_plays_tooltip_30d": plays_tooltip_30d,
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
    played_albums_30d = sum(1 for a in processed if (a.get("album_track_plays_30d") or 0) > 0)
    unplayed_albums = total_albums - played_albums
    pct_explored = round((played_albums / total_albums * 100), 1) if total_albums > 0 else 0
    total_plays = sum(a["album_track_plays"] for a in processed)
    total_plays_30d = sum(a.get("album_track_plays_30d", 0) for a in processed)
    top_album = processed[0]["album_name"] if processed else "None"
    top_album_plays = int(processed[0]["album_plays"]) if processed else 0

    kpis = {
        "total_albums": total_albums,
        "played_albums": played_albums,
        "played_albums_30d": played_albums_30d,
        "unplayed_albums": unplayed_albums,
        "pct_explored": pct_explored,
        "total_plays": total_plays,
        "total_plays_30d": total_plays_30d,
        "top_album": top_album,
        "top_album_plays": top_album_plays
    }

    result = {
        "albums": processed,
        "top_genres": [g for g, _ in genre_counter.most_common(20)],
        "kpis": kpis
    }

    save_catalog_to_datastore(user_id, result)
    _user_album_cache[user_id] = result
    _user_album_cache_time[user_id] = now
    return result


def invalidate_user_analytics_cache(user_id):
    """Deletes cached analytics in Cloud Datastore & memory when refresh is requested (INFRA-03d)."""
    try:
        ds_client = get_datastore_client()
        for r_param in ["1d", "7d", "30d", "60d", "90d", "year", "this_year", "all"]:
            try:
                key = ds_client.key("UserAnalyticsCache", f"{user_id}::{r_param}")
                ds_client.delete(key)
            except Exception:
                pass
        keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{user_id}::")]
        for k in keys_to_del:
            _user_analytics_cache.pop(k, None)
            _user_analytics_cache_time.pop(k, None)
        logger.info("[%s] Invalidated Datastore UserAnalyticsCache & in-memory analytics cache.", user_id)
    except Exception as e:
        logger.warning("[%s] Failed to invalidate Datastore UserAnalyticsCache: %s", user_id, e)


def fetch_user_analytics_data(user_id, range_param="30d", genre_param="all", start_date=None, end_date=None, force_refresh=False):
    global _user_analytics_cache, _user_analytics_cache_time
    cache_key = f"{user_id}::{range_param}::{genre_param}::{start_date}::{end_date}"
    now = time.time()

    if force_refresh:
        invalidate_user_analytics_cache(user_id)

    if not force_refresh:
        if cache_key in _user_analytics_cache and (now - _user_analytics_cache_time.get(cache_key, 0)) < 300:
            return _user_analytics_cache[cache_key]

        ds_cached = get_analytics_from_datastore(user_id, cache_key)
        if ds_cached:
            _user_analytics_cache[cache_key] = ds_cached
            _user_analytics_cache_time[cache_key] = now
            logger.info("[%s] Loaded analytics from Cloud Datastore cache (key=%s)", user_id, cache_key)
            return ds_cached

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
      SELECT
        LOWER(TRIM(album_name)) as norm_album_name,
        LOWER(TRIM(artist_name)) as norm_artist_name,
        MIN(played_at) as first_played_at
      FROM `{PLAYBACK_HISTORY_TABLE}`
      WHERE user_id = @user_id
      GROUP BY norm_album_name, norm_artist_name
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
      FROM `{PLAYBACK_HISTORY_TABLE}` p
      LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` a
        ON p.user_id = a.user_id
        AND (
          p.album_id = a.album_id
          OR (
            LOWER(TRIM(p.album_name)) = LOWER(TRIM(a.album_name))
            AND LOWER(TRIM(p.artist_name)) = LOWER(TRIM(a.artist_name))
          )
        )
      LEFT JOIN (
        SELECT
          LOWER(TRIM(album_name)) as norm_name,
          LOWER(TRIM(artist_name)) as norm_artist,
          MAX(image_url) as image_url,
          MAX(release_date) as release_date,
          MAX(genres) as genres
        FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
        GROUP BY norm_name, norm_artist
      ) g
        ON LOWER(TRIM(p.album_name)) = g.norm_name
        AND LOWER(TRIM(p.artist_name)) = g.norm_artist
      LEFT JOIN first_plays fp
        ON LOWER(TRIM(p.album_name)) = fp.norm_album_name
        AND LOWER(TRIM(p.artist_name)) = fp.norm_artist_name
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
    total_artists = int(df["artist"].nunique())
    total_seconds = total_tracks * 210
    hours = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    listening_time = f"{hours}h {mins}m"

    album_counts = df.groupby(["album", "artist"]).agg(
        plays=("ts", "count"),
        album_image_url=("album_image_url", "first")
    ).reset_index().sort_values("plays", ascending=False)
    total_albums = len(album_counts)

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
    album_window = df.groupby(["album", "artist", "first_played_at"]).size().reset_index(name="plays")
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
    save_analytics_to_datastore(user_id, cache_key, payload)
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


def compute_pal_compatibility(current_user_id, pal_id, horizon="30d"):
    """Computes acoustic chemistry, shared vinyl, and top 5 borrow recommendations (supporting 30D and all-time horizon)."""
    ds_cached = get_pal_compatibility_from_datastore(current_user_id, pal_id, horizon)
    if ds_cached:
        logger.info("[%s] Loaded pal compatibility from Datastore cache (pal=%s, horizon=%s)", current_user_id, pal_id, horizon)
        return ds_cached

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
      f.album_tracks_total,
      f.album_track_plays,
      f.album_plays,
      f.album_track_plays_30d,
      f.album_plays_30d,
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
    FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table` f
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

        tracks_total = safe_int(row.get("album_tracks_total"))
        track_plays = safe_int(row.get("album_track_plays"))
        track_plays_30d = safe_int(row.get("album_track_plays_30d"))
        added_at_val = row.get("added_at")
        norm_plays, plays_display, plays_tooltip = compute_normalized_album_plays(track_plays, tracks_total, added_at=added_at_val)
        norm_plays_30d, plays_display_30d, plays_tooltip_30d = compute_normalized_album_plays(track_plays_30d, tracks_total, is_30d=True, added_at=added_at_val)

        processed_pal_albums.append({
            "album_id": safe_str(row.get("album_id")),
            "album_name": safe_str(row.get("album_name"), "Unknown Album"),
            "album_artist_name": safe_str(row.get("album_artist_name"), "Unknown Artist"),
            "release_year": safe_str(row.get("release_year")),
            "album_tracks_total": tracks_total,
            "album_track_plays": track_plays,
            "album_plays": safe_float(row.get("album_plays")),
            "album_normalized_plays": norm_plays,
            "album_plays_display": plays_display,
            "album_plays_tooltip": plays_tooltip,
            "album_track_plays_30d": track_plays_30d,
            "album_plays_30d": safe_float(row.get("album_plays_30d")),
            "album_normalized_plays_30d": norm_plays_30d,
            "album_plays_display_30d": plays_display_30d,
            "album_plays_tooltip_30d": plays_tooltip_30d,
            "album_image_url": safe_str(row.get("album_image_url")) or "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80",
            "album_url": f"https://open.spotify.com/album/{safe_str(row.get('album_id'))}",
            "album_genres": safe_str(row.get("album_genres")),
            "has_gatefold": has_gatefold,
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

    # Top 5 Meaningful Recommendations to Borrow (APP-06: 30D vs All-Time horizon)
    def borrow_score(alb):
        if horizon == "30d":
            score = (alb.get("album_plays_30d", 0) * 12) + (alb.get("album_plays", 0) * 2)
        else:
            score = alb.get("album_plays", 0) * 5

        if alb.get("pitchfork_score"):
            try:
                score += float(alb["pitchfork_score"].split("/")[0]) * 2
            except Exception: pass
        if alb.get("discogs_rating"):
            try:
                score += float(alb["discogs_rating"]) * 3
            except Exception: pass
        if alb.get("has_gatefold"):
            score += 10
        return score

    unowned_sorted = sorted(unowned_albums, key=borrow_score, reverse=True)
    top_borrow = unowned_sorted[:5]

    for item in top_borrow:
        reasons = []
        if horizon == "30d" and item.get("album_plays_30d", 0) > 0:
            reasons.append(f"{pal_name}'s Current Obsession ({int(item['album_plays_30d'])} spins this month)")
        elif item.get("album_plays", 0) > 0:
            reasons.append(f"{pal_name}'s Heavy Rotation ({int(item['album_plays'])} lifetime spins)")
        if item.get("pitchfork_score"):
            reasons.append(f"Pitchfork {item['pitchfork_score']}")
        elif item.get("discogs_rating"):
            reasons.append(f"Discogs {item['discogs_rating']}★")
        if not reasons:
            reasons.append(f"From {pal_name}'s Crate")
        item["borrow_reason"] = " • ".join(reasons)

        if horizon == "30d" and item.get("album_track_plays_30d", 0) > 0:
            item["active_plays_display"] = item["album_plays_display_30d"]
            item["active_plays_tooltip"] = item["album_plays_tooltip_30d"]
            item["active_track_plays"] = item["album_track_plays_30d"]
        else:
            item["active_plays_display"] = item["album_plays_display"]
            item["active_plays_tooltip"] = item["album_plays_tooltip"]
            item["active_track_plays"] = item["album_track_plays"]

    result = {
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
        "pal_full_crate": processed_pal_albums,
        "horizon": horizon
    }
    save_pal_compatibility_to_datastore(current_user_id, pal_id, horizon, result)
    return result


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
ROADMAP_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve - Product Roadmap (APP Features)</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }</style>
</head>
<body class="min-h-screen p-6 md:p-12">
    <div class="max-w-4xl mx-auto">
        <div class="flex items-center justify-between pb-6 mb-8 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 shrink-0">{{ brand_icon | safe }}</div>
                <div>
                    <h1 class="text-2xl font-black text-white">🗺️ SpinSleeve Product Roadmap</h1>
                    <p class="text-xs text-gray-400 mt-0.5">Core Application Features (`APP`) &amp; Release Backlog</p>
                </div>
            </div>
            <a href="/" class="bg-[#1DB954] hover:bg-[#1ed760] text-black font-bold text-xs px-4 py-2 rounded-xl transition shadow">
                ← Back to SpinSleeve
            </a>
        </div>

        <div class="space-y-4">
            <!-- Shipped Section -->
            <div class="bg-[#14181f] border border-gray-800 rounded-2xl p-6 shadow-sm">
                <h2 class="text-sm font-bold text-emerald-400 uppercase tracking-wider mb-4">✅ Shipped &amp; Deployed Core Features</h2>
                <div class="space-y-3 text-xs">
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-04: Music Legend Illustrated Avatar Picker</strong> (12 vector legend presets, Datastore sync).</div>
                        <span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 font-bold rounded">v2.3.0</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-05: Album Sleeve Normalized Play Count Badge</strong> ("🔥 X Plays").</div>
                        <span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 font-bold rounded">v2.2.0</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-06: Dynamic Time Horizon</strong> (Heavy Rotation Last 30D vs All-Time Collection).</div>
                        <span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 font-bold rounded">v2.2.0</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-07: Played But Not Owned Crate</strong> ("You Should Save These" Amber dashed sleeves).</div>
                        <span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 font-bold rounded">v2.4.0</span>
                    </div>
                    <div class="flex items-start justify-between">
                        <div><strong class="text-white">APP-13: Spotify Full Scrobble Historical Data Upload</strong> (Extended/Legacy JSON &amp; ZIP support).</div>
                        <span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 font-bold rounded">v2.5.0</span>
                    </div>
                </div>
            </div>

            <!-- In Progress / Upcoming Section -->
            <div class="bg-[#14181f] border border-gray-800 rounded-2xl p-6 shadow-sm">
                <h2 class="text-sm font-bold text-amber-400 uppercase tracking-wider mb-4">⏳ Upcoming Application Backlog (`APP`)</h2>
                <div class="space-y-3 text-xs">
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-01: 12" Gatefold Tracklisting &amp; Side A / Side B Breakdown</strong> (Spotify API track sequences and needle-drop track auditioning).</div>
                        <span class="text-gray-400 font-mono">4-6h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-02: Cross-Platform Apple Music Library Onboarding</strong> (MusicKit JS v3 &amp; Apple Developer JWT tokens).</div>
                        <span class="text-gray-400 font-mono">16-24h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-03: In-App Feedback &amp; Liner Notes Wishlist Collector</strong> (Direct collector feedback drawer).</div>
                        <span class="text-gray-400 font-mono">5-7h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-08: Full-Length Virtual Turntable Player</strong> (Spotify Web Playback SDK integration).</div>
                        <span class="text-gray-400 font-mono">8-12h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-09: Granular Track-Level Telemetry &amp; Audio Archive</strong> (Deep track play archives).</div>
                        <span class="text-gray-400 font-mono">6-8h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-10: Local Gig Radar</strong> (Bandsintown API integration for top live artists).</div>
                        <span class="text-gray-400 font-mono">6-8h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-11: Collector’s Inscriptions</strong> (Personal star ratings and archival grade notes).</div>
                        <span class="text-gray-400 font-mono">5-7h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-12: Header Profile Dropdown &amp; Settings</strong> (SpinPals opt-in, display name editing, scrobble pause).</div>
                        <span class="text-gray-400 font-mono">3-4h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-14: Headless API &amp; Firestore Catalog Rearchitecture</strong> (REST JSON endpoints &amp; Firebase CDN proxy).</div>
                        <span class="text-gray-400 font-mono">12-16h</span>
                    </div>
                    <div class="flex items-start justify-between pb-3 border-b border-gray-800/60">
                        <div><strong class="text-white">APP-16: Semantic Liner Notes &amp; Description Classification</strong> (NLP text parsing &amp; macro-genres).</div>
                        <span class="text-gray-400 font-mono">6-8h</span>
                    </div>
                    <div class="flex items-start justify-between">
                        <div><strong class="text-white">APP-15: Native iOS SwiftUI Companion App (Phase 2)</strong> (SwiftUI iOS app with Spotify OAuth PKCE &amp; crate browsing).</div>
                        <span class="text-gray-400 font-mono">20-30h</span>
                    </div>
                </div>
            </div>

            <!-- Effort vs Value ROI Matrix Section -->
            <div class="bg-[#14181f] border border-gray-800 rounded-2xl p-6 shadow-sm">
                <h2 class="text-sm font-bold text-cyan-400 uppercase tracking-wider mb-4">🎯 Effort vs. Value ROI Priority Matrix</h2>
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-xs">
                        <thead>
                            <tr class="border-b border-gray-800 text-gray-400">
                                <th class="pb-3 font-semibold">Priority / Tier</th>
                                <th class="pb-3 font-semibold">Feature &amp; Code</th>
                                <th class="pb-3 font-semibold">Effort</th>
                                <th class="pb-3 font-semibold">Value</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-800/60 text-gray-300">
                            <tr>
                                <td class="py-3 font-bold text-amber-400">🔥 Tier 1: Quick Wins</td>
                                <td class="py-3"><strong class="text-white">APP-12</strong>: Header Profile Dropdown &amp; Settings</td>
                                <td class="py-3 font-mono">3–4h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-amber-400">🔥 Tier 1: Quick Wins</td>
                                <td class="py-3"><strong class="text-white">DOCS-01</strong>: Technical Architecture Map / README</td>
                                <td class="py-3 font-mono">3–4h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-amber-500/10 text-amber-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-emerald-400">⭐ Tier 2: High-Impact</td>
                                <td class="py-3"><strong class="text-white">APP-01</strong>: 12" Gatefold Tracklisting &amp; Side A/B Splits</td>
                                <td class="py-3 font-mono">4–6h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-emerald-400">⭐ Tier 2: High-Impact</td>
                                <td class="py-3"><strong class="text-white">APP-11</strong>: Collector’s Inscriptions &amp; Ratings</td>
                                <td class="py-3 font-mono">5–7h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-emerald-400">⭐ Tier 2: High-Impact</td>
                                <td class="py-3"><strong class="text-white">APP-09</strong>: Granular Track Telemetry &amp; Audio Archive</td>
                                <td class="py-3 font-mono">6–8h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-emerald-400">⭐ Tier 2: High-Impact</td>
                                <td class="py-3"><strong class="text-white">APP-10</strong>: Local Gig Radar (Bandsintown API)</td>
                                <td class="py-3 font-mono">6–8h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 rounded">High</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-indigo-400">🚀 Tier 3: Strategic</td>
                                <td class="py-3"><strong class="text-white">APP-08</strong>: Full-Length Virtual Turntable Web Player</td>
                                <td class="py-3 font-mono">8–12h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded">Massive</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-indigo-400">🚀 Tier 3: Strategic</td>
                                <td class="py-3"><strong class="text-white">APP-02</strong>: Apple Music Library Onboarding (Phase 7)</td>
                                <td class="py-3 font-mono">16–24h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded">Massive</span></td>
                            </tr>
                            <tr>
                                <td class="py-3 font-bold text-indigo-400">🚀 Tier 3: Strategic</td>
                                <td class="py-3"><strong class="text-white">APP-15</strong>: Native iOS SwiftUI Companion App (Phase 2)</td>
                                <td class="py-3 font-mono">20–30h</td>
                                <td class="py-3"><span class="px-2 py-0.5 bg-indigo-500/10 text-indigo-400 rounded">Massive</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SpinSleeve — Your Digital Library, Pressed on Virtual Vinyl</title>
    <link rel="icon" type="image/svg+xml" href="/favicon.svg?v=4">
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Playfair+Display:ital,wght@0,600;0,700;1,600&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; background-color: #0c0f12; color: #f3f4f6; }
        .serif-title { font-family: 'Playfair Display', serif; }
        .card-bg { background-color: #14181f; }
        .sleeve-shadow { box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.8), 0 10px 20px -10px rgba(0, 0, 0, 0.5); }
        @keyframes spinSlow { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .animate-spin-slow { animation: spinSlow 20s linear infinite; }
        @keyframes soundWave { 0%, 100% { height: 4px; } 50% { height: 20px; } }
        .wave-bar { animation: soundWave 1.2s ease-in-out infinite; }
        .wave-bar:nth-child(2) { animation-delay: 0.2s; }
        .wave-bar:nth-child(3) { animation-delay: 0.4s; }
        .wave-bar:nth-child(4) { animation-delay: 0.6s; }
    </style>
</head>
<body class="min-h-screen selection:bg-emerald-500 selection:text-black">

    <!-- Navigation Bar -->
    <header class="fixed top-0 left-0 right-0 z-50 bg-[#0c0f12]/80 backdrop-blur-md border-b border-gray-800/60 px-6 py-4">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <a href="#" class="flex items-center gap-3 group">
                <div class="w-9 h-9 relative">
                    {{ brand_icon | safe }}
                </div>
                <span class="text-xl font-extrabold tracking-tight">Spin<span class="text-[#1DB954]">Sleeve</span></span>
            </a>
            <nav class="hidden md:flex items-center gap-8 text-sm font-semibold text-gray-400">
                <a href="#features" class="hover:text-white transition">Features</a>
                <a href="#carousel" class="hover:text-white transition">Gatefold Gallery</a>
                <a href="#social" class="hover:text-white transition">SpinPals</a>
                <a href="/roadmap" class="hover:text-white transition">Roadmap (APP)</a>
            </nav>
            <div class="flex items-center gap-4">
                <a href="/beta/auth" class="px-5 py-2.5 rounded-xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-sm transition shadow-lg shadow-emerald-500/20 hover:scale-105 active:scale-95">
                    Connect Spotify
                </a>
            </div>
        </div>
    </header>

    <!-- Hero Section -->
    <section class="relative pt-32 pb-20 md:pt-44 md:pb-32 px-6 overflow-hidden">
        <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-950/20 via-[#0c0f12] to-[#0c0f12] -z-10"></div>
        <div class="max-w-5xl mx-auto text-center">
            <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-bold mb-6 tracking-wide shadow-sm">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                v2.5.2 LIVE • VIRTUAL CRATE &amp; TELEMETRY ENGINE
            </div>
            <h1 class="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight mb-8 leading-[1.1]">
                Your digital library,<br>
                <span class="serif-title italic font-normal text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-green-500">pressed on virtual vinyl.</span>
            </h1>
            <p class="text-lg sm:text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
                Transform sterile streaming playlists into an archival record store crate. Featuring 12" gatefold liner notes, 30s needle-drop previews, heavy rotation time horizons, and acoustic taste chemistry with friends.
            </p>
            <div class="flex flex-col sm:flex-row items-center justify-center gap-4">
                <a href="/beta/auth" class="w-full sm:w-auto px-8 py-4 rounded-2xl bg-[#1DB954] hover:bg-[#1ed760] text-black font-extrabold text-base transition shadow-xl shadow-emerald-500/30 hover:scale-105 active:scale-95 flex items-center justify-center gap-3">
                    <svg class="w-6 h-6 fill-current" viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.495 17.306c-.215.353-.674.464-1.026.25-2.812-1.718-6.353-2.107-10.522-1.155-.403.092-.806-.16-.898-.564-.092-.403.16-.806.564-.898 4.568-1.045 8.483-.598 11.632 1.341.352.215.464.674.25 1.026zm1.467-3.262c-.27.44-.847.579-1.287.308-3.22-1.979-8.128-2.553-11.936-1.396-.497.151-1.025-.133-1.176-.63-.151-.497.133-1.025.63-1.176 4.356-1.323 9.775-.68 13.461 1.587.44.27.579.847.308 1.287zm.126-3.41c-3.86-2.292-10.229-2.503-13.896-1.39-.592.18-1.221-.155-1.401-.747-.18-.592.155-1.221.747-1.401 4.218-1.281 11.253-1.033 15.696 1.604.533.316.707 1.011.391 1.544-.316.533-1.011.707-1.537.39z"/></svg>
                    <span>Connect with Spotify</span>
                </a>
                <a href="#carousel" class="w-full sm:w-auto px-8 py-4 rounded-2xl card-bg border border-gray-800 hover:border-gray-700 font-bold text-base transition flex items-center justify-center gap-2 text-gray-300 hover:text-white">
                    <span>Explore Gatefolds</span>
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </a>
            </div>

            <!-- Fast Testing Switcher -->
            <div class="mt-10 pt-6 border-t border-gray-800/80 max-w-md mx-auto">
                <p class="text-[10px] font-mono uppercase text-gray-500 mb-2.5 font-bold tracking-wider">🛠️ 1-Click Fast Switcher (For Testing)</p>
                <div class="flex flex-wrap items-center justify-center gap-2">
                    <a href="/beta/dev-switch/sergebou" class="px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-xs text-emerald-400 font-bold border border-gray-700 transition flex items-center gap-1.5 shadow-sm">
                        <span>👑</span> Serge (Admin)
                    </a>
                </div>
            </div>
        </div>
    </section>

    <!-- Static Gatefold Record Sleeve Gallery Section -->
    <section id="carousel" class="py-20 px-6 card-bg border-y border-gray-800/80">
        <div class="max-w-6xl mx-auto">
            <div class="text-center mb-16">
                <span class="text-xs font-mono uppercase text-emerald-400 font-bold tracking-widest">Archival Presentation</span>
                <h2 class="text-3xl sm:text-4xl font-extrabold tracking-tight mt-2">12" Gatefold Liners &amp; Record Sleeves</h2>
                <p class="text-gray-400 mt-2 max-w-xl mx-auto">Experience your music collection transformed into archival physical record store sleeves with Wikipedia summaries and Pitchfork scores.</p>
            </div>

            <!-- 3-Card Static Sleeve Showcase with Authentic Apple Music / iTunes CDN Artwork -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
                <!-- Sleeve 1: Pink Floyd -->
                <div class="bg-[#0c0f12] border border-gray-800 rounded-3xl p-6 sleeve-shadow flex flex-col justify-between group hover:border-emerald-500/50 transition">
                    <div>
                        <div class="w-full h-56 rounded-2xl bg-black relative overflow-hidden shadow-inner border border-gray-700/55 flex items-center justify-center">
                            <img src="https://thumb.wikimedia.org/wikipedia/commons/thumb/3/3b/Dark_Side_of_the_Moon.png/960px-Dark_Side_of_the_Moon.png" alt="Pink Floyd - The Dark Side of the Moon" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 flex flex-col justify-between p-4 text-white pointer-events-none">
                                <div class="flex justify-between items-start">
                                    <span class="text-xs font-mono bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-emerald-400 font-bold">1973</span>
                                    <span class="text-xs font-bold bg-emerald-500 text-black px-2.5 py-0.5 rounded-full shadow">🔥 84 Plays</span>
                                </div>
                                <div>
                                    <h3 class="text-xl font-bold serif-title italic text-white">The Dark Side of the Moon</h3>
                                    <p class="text-xs text-gray-300 font-medium">Pink Floyd</p>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Progressive Rock</span>
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">Pitchfork: 10/10</span>
                            </div>
                            <p class="text-xs text-gray-400 leading-relaxed">
                                A monumental exploration of conflict, greed, time, and mental illness, wrapped in Hipgnosis's iconic prism artwork.
                            </p>
                        </div>
                    </div>
                    <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-500 font-mono">
                        <span>Side A • 1 Track</span>
                        <span class="text-emerald-400 font-bold">Gatefold Loaded</span>
                    </div>
                </div>

                <!-- Sleeve 2: Daft Punk -->
                <div class="bg-[#0c0f12] border border-gray-800 rounded-3xl p-6 sleeve-shadow flex flex-col justify-between group hover:border-emerald-500/50 transition">
                    <div>
                        <div class="w-full h-56 rounded-2xl bg-black relative overflow-hidden shadow-inner border border-gray-700/55 flex items-center justify-center">
                            <img src="https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/fd/4a/77/fd4a77db-0ebc-d043-41a2-f32fa1bb0fb4/dj.qrikkdwj.jpg/600x600bb.jpg" alt="Daft Punk - Discovery" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 flex flex-col justify-between p-4 text-white pointer-events-none">
                                <div class="flex justify-between items-start">
                                    <span class="text-xs font-mono bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-emerald-400 font-bold">2001</span>
                                    <span class="text-xs font-bold bg-emerald-500 text-black px-2.5 py-0.5 rounded-full shadow">🔥 68 Plays</span>
                                </div>
                                <div>
                                    <h3 class="text-xl font-bold serif-title italic text-white">Discovery</h3>
                                    <p class="text-xs text-gray-300 font-medium">Daft Punk</p>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">House / Synth-Pop</span>
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">Pitchfork: 8.8/10</span>
                            </div>
                            <p class="text-xs text-gray-400 leading-relaxed">
                                An emotional odyssey of vocoded vocals, filtered disco loops, and futuristic pop hooks soundtracking neon night drives.
                            </p>
                        </div>
                    </div>
                    <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-500 font-mono">
                        <span>Side B • Track 4</span>
                        <span class="text-emerald-400 font-bold">Gatefold Loaded</span>
                    </div>
                </div>

                <!-- Sleeve 3: Radiohead -->
                <div class="bg-[#0c0f12] border border-gray-800 rounded-3xl p-6 sleeve-shadow flex flex-col justify-between group hover:border-emerald-500/50 transition">
                    <div>
                        <div class="w-full h-56 rounded-2xl bg-black relative overflow-hidden shadow-inner border border-gray-700/55 flex items-center justify-center">
                            <img src="https://is1-ssl.mzstatic.com/image/thumb/Music122/v4/bd/8e/13/bd8e1358-b367-a689-cb84-cebd0b067dc4/634904078263.png/600x600bb.jpg" alt="Radiohead - Kid A" class="w-full h-full object-cover group-hover:scale-105 transition duration-300">
                            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20 flex flex-col justify-between p-4 text-white pointer-events-none">
                                <div class="flex justify-between items-start">
                                    <span class="text-xs font-mono bg-black/60 backdrop-blur-md px-2.5 py-1 rounded-md text-emerald-400 font-bold">2000</span>
                                    <span class="text-xs font-bold bg-emerald-500 text-black px-2.5 py-0.5 rounded-full shadow">🔥 42 Plays</span>
                                </div>
                                <div>
                                    <h3 class="text-xl font-bold serif-title italic text-white">Kid A</h3>
                                    <p class="text-xs text-gray-300 font-medium">Radiohead</p>
                                </div>
                            </div>
                        </div>
                        <div class="mt-4">
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Art Rock / Electronic</span>
                                <span class="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">Pitchfork: 10/10</span>
                            </div>
                            <p class="text-xs text-gray-400 leading-relaxed">
                                A radical departure from guitar rock, weaving fractured electronica and jazz samples into an icy architectural monument.
                            </p>
                        </div>
                    </div>
                    <div class="mt-6 pt-4 border-t border-gray-800/80 flex items-center justify-between text-xs text-gray-500 font-mono">
                        <span>Side A • Track 1</span>
                        <span class="text-emerald-400 font-bold">Gatefold Loaded</span>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Core Features Grid -->
    <section id="features" class="py-24 px-6">
        <div class="max-w-7xl mx-auto">
            <div class="text-center mb-16">
                <span class="text-xs font-mono uppercase text-emerald-400 font-bold tracking-widest">Engineered for Collectors</span>
                <h2 class="text-3xl sm:text-5xl font-extrabold tracking-tight mt-2">Everything Your Digital Library Missed</h2>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
                <!-- Feature 1 -->
                <div class="card-bg border border-gray-800 rounded-3xl p-8 hover:border-emerald-500/50 transition group">
                    <div class="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-6 group-hover:scale-110 transition">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    </div>
                    <h3 class="text-xl font-bold mb-3">Smart Crate Digger</h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        Filter by vibe (Chill, Energetic, Vintage, Mellow), era, and subgenres. Switch instantly between Heavy Rotation (30D) and All-Time Collection.
                    </p>
                </div>

                <!-- Feature 2 -->
                <div class="card-bg border border-gray-800 rounded-3xl p-8 hover:border-emerald-500/50 transition group">
                    <div class="w-12 h-12 rounded-2xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 mb-6 group-hover:scale-110 transition">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    </div>
                    <h3 id="social" class="text-xl font-bold mb-3">SpinPals (CrateMates)</h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        The Listening Lounge member directory. Calculate acoustic chemistry gauges (50% artist + 50% album overlap), earn kinship badges, and borrow recommendations.
                    </p>
                </div>

                <!-- Feature 3 -->
                <div class="card-bg border border-gray-800 rounded-3xl p-8 hover:border-emerald-500/50 transition group">
                    <div class="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-6 group-hover:scale-110 transition">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    </div>
                    <h3 class="text-xl font-bold mb-3">Unowned Crate Discovery</h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        Automatically detects heavily scrobbled albums missing from your saved library, displaying amber dashed sleeves with 1-click Spotify save actions.
                    </p>
                </div>

                <!-- Feature 4 -->
                <div class="card-bg border border-gray-800 rounded-3xl p-8 hover:border-emerald-500/50 transition group">
                    <div class="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-6 group-hover:scale-110 transition">
                        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    </div>
                    <h3 class="text-xl font-bold mb-3">Listening Analytics</h3>
                    <p class="text-sm text-gray-400 leading-relaxed">
                        Deep listening telemetry engine with listening clock heatmaps, custom date ranges, fresh vs repeat ratios, and taste velocity tracking.
                    </p>
                </div>
            </div>
        </div>
    </section>

    <!-- Footer -->
    <footer class="py-12 px-6 border-t border-gray-800/80 bg-[#0c0f12]">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6 text-sm text-gray-500">
            <div class="flex items-center gap-3">
                <div class="w-6 h-6 animate-spin-slow">
                    {{ brand_icon | safe }}
                </div>
                <span class="font-bold text-gray-300">SpinSleeve v2.5.2</span>
                <span>•</span>
                <span>Built for music collectors</span>
            </div>
            <div class="flex items-center gap-6">
                <a href="/roadmap" class="hover:text-emerald-400 transition">Roadmap</a>
                <a href="https://github.com" target="_blank" class="hover:text-emerald-400 transition">GitHub</a>
                <a href="/beta/auth" class="text-emerald-400 font-bold hover:underline">Log In with Spotify →</a>
            </div>
        </div>
    </footer>

    <!-- Carousel JS Script -->
    <script>
        const slides = [
            {
                album: "The Dark Side of the Moon",
                artist: "Pink Floyd",
                year: "1973",
                plays: "84 Plays",
                genre: "Progressive Rock / Psychedelic",
                score: "Pitchfork: 10/10",
                title: "The Definitive Progressive Masterpiece",
                desc: "A monumental exploration of conflict, greed, time, and mental illness, wrapped in Hipgnosis's iconic prism artwork and pristine analog production.",
                image: "https://upload.wikimedia.org/wikipedia/en/3/3b/Dark_Side_of_the_Moon.png"
            },
            {
                album: "Discovery",
                artist: "Daft Punk",
                year: "2001",
                plays: "68 Plays",
                genre: "House / Synth-Pop",
                score: "Pitchfork: 8.8/10",
                title: "The Golden Age of French Touch",
                desc: "An emotional odyssey of vocoded vocals, filtered disco loops, and futuristic pop hooks that soundtracked an entire generation's neon-lit night drives.",
                image: "https://upload.wikimedia.org/wikipedia/en/2/27/Daft_Punk_-_Discovery.png"
            },
            {
                album: "Kid A",
                artist: "Radiohead",
                year: "2000",
                plays: "42 Plays",
                genre: "Art Rock / Electronic",
                score: "Pitchfork: 10/10",
                title: "Masterpiece of Electronic Ambience",
                desc: "A radical departure from guitar rock, weaving fractured electronica, jazz samples, and haunting falsettos into an icy architectural monument of the new millennium.",
                image: "https://upload.wikimedia.org/wikipedia/en/a/a1/Radiohead.kida.albumart.jpg"
            }
        ];

        let currentSlide = 0;

        function updateSlide() {
            const s = slides[currentSlide];
            document.getElementById('slide-year').innerText = s.year;
            document.getElementById('slide-plays').innerText = s.plays;
            document.getElementById('slide-album').innerText = s.album;
            document.getElementById('slide-artist').innerText = s.artist;
            document.getElementById('slide-genre').innerText = s.genre;
            document.getElementById('slide-score').innerText = s.score;
            document.getElementById('slide-title').innerText = s.title;
            document.getElementById('slide-desc').innerText = s.desc;
            document.getElementById('slide-indicator').innerText = (currentSlide + 1) + ' / ' + slides.length;
            document.getElementById('slide-img').src = s.image;
        }

        function nextSlide() {
            currentSlide = (currentSlide + 1) % slides.length;
            updateSlide();
        }

        function prevSlide() {
            currentSlide = (currentSlide - 1 + slides.length) % slides.length;
            updateSlide();
        }
    </script>
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
                            {% set is_admin_account = (u.role == 'admin') or (u.spotify_id in ['serbou', 'sergebou', 'vaultica']) %}
                            {% if u.pals_opt_in or is_admin_account %}
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
                                {% if not is_admin_account %}
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
                                {% endif %}
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
# AUTHENTICATION & PUBLIC ROUTES
# ==============================================================================
@app.route("/login")
@app.route("/beta/login")
def login():
    if "user_id" in session:
        return redirect("/")
    return render_template_string(LANDING_PAGE_HTML, brand_icon=ICON_A_SVG)


@app.route("/roadmap")
@app.route("/beta/roadmap")
@app.route("/roadmap/")
@app.route("/beta/roadmap/")
def public_roadmap():
    return render_template_string(ROADMAP_HTML_TEMPLATE, brand_icon=ICON_A_SVG)


@app.route("/auth")
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
        return redirect("/login")

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
                "spotify_avatar_url": avatar_url,
                "custom_avatar_id": "",
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
            user["spotify_avatar_url"] = avatar_url
            if not user.get("custom_avatar_id"):
                user["avatar_url"] = avatar_url
            else:
                user["avatar_url"] = f"/avatar/{user['custom_avatar_id']}.svg"
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
        session["avatar_url"] = user.get("avatar_url", "")
        session["spotify_avatar_url"] = user.get("spotify_avatar_url", "")
        session["custom_avatar_id"] = user.get("custom_avatar_id", "")
        session["role"] = user.get("role", "user")
        session["pals_opt_in"] = bool(user.get("pals_opt_in", False))
        session["sync_paused"] = bool(user.get("sync_paused", False))
        if is_admin:
            session["admin_user_id"] = spotify_id
        session["is_impersonating"] = False

        if user.get("sync_status") == "pending":
            sync_user_initial_data(spotify_id, access_token)
            user["sync_status"] = "idle"
            ds_client.put(user)

        return redirect("/")

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
                        <a href="/login" style="display:inline-block; margin-top:20px; background:#1DB954; color:#000; padding:10px 20px; border-radius:12px; font-weight:bold; font-size:13px; text-decoration:none;">Return to Login</a>
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
    return redirect("/login")


@app.route("/admin/assume/<target_id>")
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
    session["spotify_avatar_url"] = user.get("spotify_avatar_url", "")
    session["custom_avatar_id"] = user.get("custom_avatar_id", "")
    session["role"] = user.get("role", "user")
    session["pals_opt_in"] = bool(user.get("pals_opt_in", False))
    session["sync_paused"] = bool(user.get("sync_paused", False))
    session["is_impersonating"] = (target_id not in ADMIN_USER_IDS)

    # Invalidate in-memory caches for this user
    _user_album_cache.pop(target_id, None)
    _user_album_cache_time.pop(target_id, None)
    keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{target_id}::")]
    for k in keys_to_del:
        _user_analytics_cache.pop(k, None)
        _user_analytics_cache_time.pop(k, None)

    logger.info("Admin %s assumed identity of: %s (%s)", real_admin, target_id, session["display_name"])
    return redirect("/")


@app.route("/admin/revert")
@app.route("/beta/admin/revert")
def admin_revert():
    real_admin = session.get("admin_user_id")
    if not real_admin or real_admin not in ADMIN_USER_IDS:
        return redirect("/login")

    ds_client = get_datastore_client()
    key = ds_client.key("User", real_admin)
    admin_user = ds_client.get(key)
    if not admin_user:
        return redirect("/login")

    session["user_id"] = real_admin
    session["display_name"] = admin_user.get("display_name", real_admin)
    session["avatar_url"] = admin_user.get("avatar_url", "")
    session["spotify_avatar_url"] = admin_user.get("spotify_avatar_url", "")
    session["custom_avatar_id"] = admin_user.get("custom_avatar_id", "")
    session["role"] = "admin"
    session["pals_opt_in"] = True
    session["sync_paused"] = bool(admin_user.get("sync_paused", False))
    session["is_impersonating"] = False

    logger.info("Admin %s reverted back to admin profile", real_admin)
    return redirect("/admin")


@app.route("/dev-switch/<user_id>")
@app.route("/beta/dev-switch/<user_id>")
def dev_switch(user_id):
    real_admin = session.get("admin_user_id") or session.get("user_id")
    if real_admin not in ADMIN_USER_IDS:
        return "Unauthorized switch. Only administrators can assume user profiles.", 403
    return admin_assume(user_id)





def fetch_unowned_album_data(user_id, horizon="all"):
    """Fetches streamed albums not in saved library, filtered by time horizon (APP-07)."""
    try:
        client = bigquery.Client(project=PROJECT_ID)

        horizon_clause = ""
        if horizon == "30d":
            horizon_clause = "AND p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
        elif horizon == "90d":
            horizon_clause = "AND p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)"

        query = f"""
        SELECT 
          p.album_name,
          p.artist_name,
          MAX(p.album_id) as album_id,
          COUNT(1) as play_count,
          COUNT(DISTINCT p.track_name) as distinct_tracks,
          MAX(p.played_at) as last_played_at
        FROM `{PLAYBACK_HISTORY_TABLE}` p
        WHERE p.user_id = @user_id
          AND CONCAT(LOWER(TRIM(p.album_name)), '::', LOWER(TRIM(p.artist_name))) NOT IN (
            SELECT CONCAT(LOWER(TRIM(album_name)), '::', LOWER(TRIM(artist_name)))
            FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
            WHERE user_id = @user_id
          )
          {horizon_clause}
        GROUP BY p.album_name, p.artist_name
        HAVING distinct_tracks >= 2
        ORDER BY play_count DESC
        LIMIT 50
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        df = client.query(query, job_config=job_config).to_dataframe()
        if df.empty:
            return []
        unowned = []
        for _, row in df.iterrows():
            aid = safe_str(row.get("album_id"))
            unowned.append({
                "album_id": aid if aid != "None" else "",
                "album_name": safe_str(row.get("album_name"), "Unknown Album"),
                "album_artist_name": safe_str(row.get("artist_name"), "Unknown Artist"),
                "album_image_url": "/avatar/miles.svg",
                "album_url": f"https://open.spotify.com/album/{aid}" if aid and aid != "None" else f"https://open.spotify.com/search/{safe_str(row.get('album_name'))}",
                "play_count": safe_int(row.get("play_count")),
                "last_played_at": str(row.get("last_played_at", ""))
            })

        # On-the-fly Spotify API artwork enrichment for unowned albums
        try:
            sp = None
            token_info = get_token_for_user(user_id)
            if token_info and token_info.get("access_token"):
                sp = spotipy.Spotify(auth=token_info.get("access_token"), requests_timeout=10)
            else:
                # Fallback to client credentials for local dev login bypasses
                from spotipy.oauth2 import SpotifyClientCredentials
                client_credentials_manager = SpotifyClientCredentials()
                sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, requests_timeout=10)

            if sp:
                # 1. Batch fetch by album_id
                valid_aids = [row["album_id"] for row in unowned if row["album_id"] and row["album_id"] != "None"]
                if valid_aids:
                    for i in range(0, len(valid_aids), 20):
                        chunk = valid_aids[i:i+20]
                        res = sp.albums(chunk)
                        for album_obj in res.get("albums", []):
                            if album_obj and album_obj.get("id"):
                                aid = album_obj["id"]
                                images = album_obj.get("images", [])
                                img_url = images[0].get("url") if images else ""
                                if img_url:
                                    for item in unowned:
                                        if item["album_id"] == aid:
                                            item["album_image_url"] = img_url

                # 2. Fallback search by album name and artist name for any still missing images
                for item in unowned:
                    if not item["album_image_url"] or item["album_image_url"] == "/avatar/miles.svg":
                        try:
                            search_res = sp.search(q=f"album:{item['album_name']} artist:{item['album_artist_name']}", type="album", limit=1)
                            items = search_res.get("albums", {}).get("items", [])
                            if items:
                                alb = items[0]
                                if not item["album_id"] or item["album_id"] == "None":
                                    item["album_id"] = alb.get("id", "")
                                    item["album_url"] = f"https://open.spotify.com/album/{item['album_id']}"
                                images = alb.get("images", [])
                                if images:
                                    item["album_image_url"] = images[0].get("url", "")
                        except Exception as ex:
                            logger.debug("Could not search Spotify for unowned album %s: %s", item["album_name"], ex)
        except Exception as e:
            logger.debug("Could not enrich unowned album artwork from Spotify: %s", e)

        return unowned
    except Exception as e:
        logger.error("Error fetching unowned albums for %s: %s", user_id, e)
        return []


@app.route("/api/unowned-albums")
@app.route("/beta/api/unowned-albums")
@login_required
def api_unowned_albums():
    """API endpoint to fetch unowned albums by time horizon (APP-07)."""
    user_id = session.get("user_id")
    horizon = request.args.get("horizon", "30d")
    unowned = fetch_unowned_album_data(user_id, horizon=horizon)
    return jsonify({"status": "success", "unowned": unowned, "horizon": horizon})


def get_token_for_user(user_id):
    """Retrieves and refreshes Spotify access token for a user from Datastore."""
    try:
        ds_client = get_datastore_client()
        user_key = ds_client.key("User", user_id)
        user = ds_client.get(user_key)
        if not user or not user.get("refresh_token"):
            return None
        sp_oauth = get_oauth_client(request)
        token_info = sp_oauth.refresh_access_token(user.get("refresh_token"))
        return token_info
    except Exception as e:
        logger.error("Error refreshing token for user %s: %s", user_id, e)
        return None


@app.route("/api/save-album", methods=["POST"])
@app.route("/beta/api/save-album", methods=["POST"])
@login_required
def api_save_album():
    """Saves an unowned album to Spotify saved albums and inserts into BigQuery / clears cache (APP-07)."""
    data = request.get_json(silent=True) or {}
    album_id = str(data.get("album_id", "")).strip()
    album_name = str(data.get("album_name", "")).strip()
    artist_name = str(data.get("artist_name", "")).strip()

    user_id = session.get("user_id")
    token_info = get_token_for_user(user_id)
    if not token_info:
        return jsonify({"status": "error", "message": "Not authorized with Spotify"}), 401

    try:
        sp = spotipy.Spotify(auth=token_info.get("access_token"), requests_timeout=15)
        # If album_id is missing or None, search Spotify for it using album_name and artist_name
        if not album_id or album_id == "None":
            if not album_name:
                return jsonify({"status": "error", "message": "Missing album_id or album_name"}), 400
            search_res = sp.search(q=f"album:{album_name} artist:{artist_name}", type="album", limit=1)
            albums_found = search_res.get("albums", {}).get("items", [])
            if not albums_found:
                search_res = sp.search(q=f"{album_name} {artist_name}", type="album", limit=1)
                albums_found = search_res.get("albums", {}).get("items", [])
            if albums_found:
                album_id = albums_found[0]["id"]
            else:
                return jsonify({"status": "error", "message": f"Could not locate '{album_name}' by '{artist_name}' on Spotify"}), 404

        sp.current_user_saved_albums_add(albums=[album_id])

        client = bigquery.Client(project=PROJECT_ID)
        album_meta = sp.album(album_id)
        image_url = album_meta["images"][0]["url"] if album_meta.get("images") else ""
        artists = album_meta.get("artists", [])
        artist_name = artists[0]["name"] if artists else "Unknown Artist"
        artist_id = artists[0]["id"] if artists else ""
        rel_date = album_meta.get("release_date", "")
        rel_year = rel_date[:4] if rel_date else ""

        row_to_insert = [{
            "user_id": user_id,
            "album_id": album_id,
            "album_name": album_meta.get("name", "Unknown Album"),
            "artist_id": artist_id,
            "artist_name": artist_name,
            "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "release_date": rel_date,
            "release_year": rel_year,
            "tracks_total": album_meta.get("total_tracks", 0),
            "album_type": album_meta.get("album_type", "album"),
            "label": album_meta.get("label", ""),
            "image_url": image_url,
            "genres": ""
        }]
        table_ref = f"{PROJECT_ID}.{DATASET_V2}.user_saved_albums"
        errors = client.insert_rows_json(table_ref, row_to_insert)
        if errors:
            logger.error("Error inserting saved album into BQ for %s: %s", user_id, errors)

        if user_id in _user_album_cache:
            del _user_album_cache[user_id]
        if user_id in _user_album_cache_time:
            del _user_album_cache_time[user_id]
        try:
            ds_client = get_datastore_client()
            ds_client.delete(ds_client.key("UserCatalogCache", user_id))
        except Exception:
            pass

        return jsonify({"status": "success", "message": f"'{album_meta.get('name')}' saved to library successfully!"})
    except requests.exceptions.Timeout:
        logger.warning("Spotify API timeout while saving album %s for user %s", album_id or album_name, user_id)
        return jsonify({"status": "error", "message": "Spotify API request timed out. Please try again in a few moments."}), 504
    except Exception as e:
        logger.error("Error saving album %s for %s: %s", album_id or album_name, user_id, str(e))
        return jsonify({"status": "error", "message": str(e)}), 500


def fetch_landing_showcase_albums():
    """Fetches real scrobbled album artwork from BigQuery user_albums_features_table for landing showcase."""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        query = f"""
            SELECT album_name, artist_name, image_url, release_year, album_plays
            FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
            WHERE image_url IS NOT NULL AND image_url != ''
            GROUP BY album_name, artist_name, image_url, release_year, album_plays
            ORDER BY album_plays DESC
            LIMIT 3
        """
        df = client.query(query).to_dataframe()
        if not df.empty:
            showcase = []
            for _, r in df.iterrows():
                showcase.append({
                    "album": safe_str(r.get("album_name")),
                    "artist": safe_str(r.get("artist_name")),
                    "year": safe_str(r.get("release_year")) or "2020",
                    "plays": int(r.get("album_plays") or 42),
                    "image": safe_str(r.get("image_url"))
                })
            if len(showcase) >= 3:
                return showcase
    except Exception as e:
        logger.debug("Could not query BigQuery for showcase albums: %s", e)

    # Fallback default real album artwork (Spotify CDN)
    return [
        {
            "album": "The Dark Side of the Moon",
            "artist": "Pink Floyd",
            "year": "1973",
            "plays": 84,
            "image": "https://i.scdn.co/image/ab67616d0000b273ea75e50f9d414e0cc7f45abf"
        },
        {
            "album": "Discovery",
            "artist": "Daft Punk",
            "year": "2001",
            "plays": 68,
            "image": "https://i.scdn.co/image/ab67616d0000b273a0484dcec2eb06a0956b9c9e"
        },
        {
            "album": "Kid A",
            "artist": "Radiohead",
            "year": "2000",
            "plays": 42,
            "image": "https://i.scdn.co/image/ab67616d0000b273bd2631586554749b6b0cfa9a"
        }
    ]


# ==============================================================================
# 1. TAB 1: LIBRARY EXPLORER ROUTE & TEMPLATE
# ==============================================================================
@app.route("/")
@app.route("/beta")
@app.route("/beta/")
def beta_index():
    if "user_id" not in session:
        showcase_albums = fetch_landing_showcase_albums()
        return render_template_string(LANDING_PAGE_HTML, brand_icon=ICON_A_SVG, showcase_albums=showcase_albums)

    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)
    unowned_albums = fetch_unowned_album_data(user_id)

    return render_template_string(
        EXPLORER_HTML,
        albums=data["albums"],
        unowned_albums=unowned_albums,
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


EXPLORER_HTML = """
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
        <header class="flex flex-col lg:flex-row lg:items-center justify-between pb-6 mb-4 border-b border-gray-800 gap-4">
            <div>
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 flex-shrink-0">
                        {{ brand_icon | safe }}
                    </div>
                    <div class="flex items-center gap-2">
                        <h1 class="text-3xl font-extrabold tracking-tight">
                            <span class="text-white">Spin</span><span class="text-[#1DB954]">Sleeve</span>
                        </h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border border-emerald-500/30" title="SpinSleeve {{ app_version }}">{{ app_version }}</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Multi-tenant edition • Personal vinyl crate &amp; gatefold archive</p>
            </div>

            <!-- Top-Level Navigation Tabs -->
            

                        <!-- Top-Level Navigation Tabs -->
            

                        <!-- Top-Level Navigation Tabs -->
            

                        <!-- Top-Level Navigation Tabs -->
            

                        <!-- Top-Level Navigation Tabs -->
            <nav class="hidden md:flex items-center gap-1 bg-[#0c0f12] p-1 rounded-xl border border-gray-800 shadow-inner">
                <a href="/beta/" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 flex items-center gap-2 transition shadow-sm">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    Library
                </a>
                <a href="/beta/analytics" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Analytics
                </a>
                <a href="/beta/pals" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    SpinPals
                </a>
            </nav>

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
                <div class="relative flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5" id="userProfileWidget">
                    <button type="button" onclick="toggleAvatarDropdown(event)"
                            class="relative w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 hover:border-emerald-400 hover:scale-105 active:scale-95 transition-all cursor-pointer flex items-center justify-center shrink-0 focus:outline-none"
                            title="Click for settings & avatar picker">
                        <img class="headerUserAvatarImg w-full h-full object-cover" src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" alt="{{ user.display_name }}">
                    </button>

                    <!-- Avatar & Settings Dropdown Menu (POLISH-08) -->
                    <div class="avatarPickerDropdown hidden absolute right-0 top-full mt-2 w-72 bg-[#14181f] border border-gray-700/80 rounded-2xl shadow-2xl p-3 z-50 text-left backdrop-blur-xl">
                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-gray-800">
                            <div>
                                <span class="text-[11px] font-black uppercase tracking-wider text-emerald-400">User Settings</span>
                                <p class="text-[10px] text-gray-400">{{ user.display_name }}'s Crate &amp; Lounge</p>
                            </div>
                            <button type="button" onclick="closeAvatarDropdown(event)" class="text-gray-400 hover:text-white text-xs p-1 leading-none font-bold">&times;</button>
                        </div>

                        <div class="space-y-2 mb-3 pb-3 border-b border-gray-800">
                            <button type="button" onclick="toggleUserPalsOptIn()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-emerald-500/40 transition text-xs font-semibold text-white">
                                <span class="span-left flex items-center gap-2">🤝 Opt-in SpinPals</span>
                                <span id="palsOptInStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.pals_opt_in %}bg-emerald-500/20 text-emerald-300 border border-emerald-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.pals_opt_in %}Active{% else %}Inactive{% endif %}
                                </span>
                            </button>
                            <button type="button" onclick="toggleUserSyncPause()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-amber-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">⏸️ Sync Pause</span>
                                <span id="syncPauseStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.sync_paused %}bg-amber-500/20 text-amber-300 border border-amber-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.sync_paused %}Paused{% else %}Active{% endif %}
                                </span>
                            </button>
                            <input type="file" id="historyUploadInput" accept=".json,.zip" multiple class="hidden" onchange="uploadHistoryFiles(event)">
                            <button type="button" onclick="document.getElementById('historyUploadInput').click()"
                                    class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold transition">
                                📂 Import History (.json / .zip)
                            </button>
                            <div id="historyUploadStatus" class="hidden text-[10px] text-center font-bold text-amber-400 pt-1"></div>
                            <a href="/beta/logout" class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold transition">
                                🚪 Logout ({{ user.display_name }})
                            </a>
                        </div>

                        <div class="mb-2">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Music Legend Persona</span>
                        </div>
                        <div class="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar avatarOptionsList">
                            <button type="button" onclick="selectAvatarPreset('spotify', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if not user.custom_avatar_id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center shrink-0">
                                    {% if user.spotify_avatar_url %}
                                    <img src="{{ user.spotify_avatar_url }}" class="w-full h-full object-cover">
                                    {% else %}
                                    <span class="text-xs">🟢</span>
                                    {% endif %}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">Spotify Profile</div>
                                    <div class="text-[10px] text-gray-400 truncate">Default Spotify photo</div>
                                </div>
                                {% if not user.custom_avatar_id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>

                            {% if avatar_presets %}
                            {% for preset in avatar_presets %}
                            <button type="button" onclick="selectAvatarPreset('{{ preset.id }}', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if user.custom_avatar_id == preset.id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden shrink-0 shadow-sm">
                                    <img src="/avatar/{{ preset.id }}.svg" alt="{{ preset.name }}" class="w-full h-full object-cover">
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">{{ preset.name }}</div>
                                    <div class="text-[10px] text-gray-400 truncate">{{ preset.badge }} {{ preset.era }} • {{ preset.desc }}</div>
                                </div>
                                {% if user.custom_avatar_id == preset.id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>
                            {% endfor %}
                            {% endif %}
                        </div>

                        <div class="avatarSaveStatus hidden mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400">
                            ✓ Persona saved!
                        </div>
                    </div>

                    <a href="/beta/logout" class="text-xs font-bold text-white hover:text-emerald-400 transition" title="Click to logout">{{ user.display_name }}</a>
                    {% if is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition" title="Exit assumed view and revert to Admin">↩ Revert</a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </header>

        

        <!-- Hardware-Inspired Segmented Sub-Tab Control Deck under Library (POLISH-08) -->
        <div class="flex items-center p-1 bg-[#080a0c] rounded-xl border border-gray-800 shadow-inner mb-6 w-fit">
            <button id="savedVinylTabBtn" onclick="switchCrateTab('saved')"
                    class="px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-gradient-to-r from-emerald-500/20 to-teal-500/25 text-emerald-300 border border-emerald-500/30 shadow-sm">
                <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                <span>My Saved Vinyl</span>
                <span class="bg-emerald-500/30 text-emerald-200 text-[10px] font-mono px-1.5 py-0.5 rounded-full">{{ albums|length }}</span>
            </button>
            <a href="/beta/recommend" id="diggerTabBtn"
               class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/40 transition flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
                <span>Crate Digger</span>
            </a>
            <button id="unownedVinylTabBtn" onclick="switchCrateTab('unowned')"
                    class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/40 transition flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
                <span>You Should Save These</span>
                <span class="bg-amber-500/20 text-amber-300 text-[10px] font-mono px-1.5 py-0.5 rounded-full border border-amber-500/30" id="unownedCountBadge">{{ (unowned_albums or [])|length }}</span>
            </button>
        </div>

        <!-- Saved Vinyl View Container -->
        <div id="savedVinylView">
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
                            <option value="plays_30d_desc">🔥 Heavy Rotation (Last 30 Days)</option>
                            <option value="plays_desc">Most Played (All Time)</option>
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

        <!-- Unowned Stream Discoveries View Container (APP-07) -->
        <div id="unownedVinylView" class="hidden">
            <div class="card-bg p-4 rounded-xl border border-gray-800 mb-6 shadow-sm space-y-3">
                <div class="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    <div class="relative flex-1">
                        <span class="absolute inset-y-0 left-0 flex items-center pl-3 text-gray-500">🔍</span>
                        <input type="text" id="unownedSearchInput" placeholder="Search unowned streamed albums or artists..."
                               class="w-full bg-[#0c0f12] border border-gray-800 rounded-lg pl-9 pr-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-amber-400 transition"
                               oninput="onUnownedFilterChange()">
                    </div>
                    <!-- Time Horizon Selector (APP-07) -->
                    <div class="flex items-center gap-1.5 bg-[#0c0f12] p-1 rounded-xl border border-gray-800">
                        <button onclick="changeUnownedHorizon('30d')" id="unownedHorizon-30d" class="px-3 py-1 rounded-lg text-xs font-medium text-gray-400 hover:text-white transition">Last 30 Days</button>
                        <button onclick="changeUnownedHorizon('90d')" id="unownedHorizon-90d" class="px-3 py-1 rounded-lg text-xs font-medium text-gray-400 hover:text-white transition">Last 90 Days</button>
                        <button onclick="changeUnownedHorizon('all')" id="unownedHorizon-all" class="px-3 py-1 rounded-lg text-xs font-bold transition bg-amber-500/20 text-amber-300 border border-amber-500/30">All Time</button>
                    </div>
                </div>
            </div>

            <div id="unownedAlbumGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4"></div>

            <div class="text-center py-10">
                <span class="text-xs text-gray-500">Showing <span id="unownedDisplayedCount">0</span> unowned stream-discovered albums</span>
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
        const ALL_ALBUMS = {{ albums | tojson }};
        const UNOWNED_ALBUMS = {{ (unowned_albums or []) | tojson }};
        let filteredAlbums = [...ALL_ALBUMS];
        let filteredUnowned = [...UNOWNED_ALBUMS];
        let displayLimit = 48;

        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = localStorage.getItem('spinAudioEnabled') !== 'false';
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
            localStorage.setItem('spinAudioEnabled', isAudioEnabled);
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                if (btnText) btnText.innerText = 'Hover Audio: ON';
                if (btnIcon) btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
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

        function getAlbumPlayBadge(a) {
            const sortEl = document.getElementById("sortSelect");
            const is30d = sortEl && sortEl.value === "plays_30d_desc";
            const trackPlays = is30d ? (Number(a.album_track_plays_30d) || 0) : (Number(a.album_track_plays) || 0);
            const tracksTotal = Number(a.album_tracks_total) || 0;

            if (is30d && a.album_plays_display_30d && a.album_plays_tooltip_30d) {
                const colorClass = trackPlays > 0 ? 'text-amber-400 font-black' : 'text-gray-400 font-bold';
                return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${a.album_plays_tooltip_30d}">${a.album_plays_display_30d}</div>`;
            } else if (!is30d && a.album_plays_display && a.album_plays_tooltip) {
                const colorClass = trackPlays > 0 ? 'text-emerald-400 font-black' : 'text-gray-400 font-bold';
                return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${a.album_plays_tooltip}">${a.album_plays_display}</div>`;
            }

            if (trackPlays === 0) {
                let isNew = false;
                if (a.added_at) {
                    try {
                        const dt = new Date(a.added_at);
                        const now = new Date();
                        const diffDays = (now - dt) / (1000 * 60 * 60 * 24);
                        if (diffDays <= 14) isNew = true;
                    } catch(e) {}
                }
                const label = isNew ? "✨ Newly Added" : "💤 Never Played";
                const tooltip = isNew ? "Newly added album (0 plays)" : "Never played (0 plays)";
                return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] text-gray-400 font-bold select-none" title="${tooltip}">${label}</div>`;
            }

            let decimalPlays = trackPlays;
            let tooltip = '';
            if (tracksTotal > 0) {
                decimalPlays = Math.round((trackPlays / tracksTotal) * 10) / 10;
                tooltip = is30d
                    ? `Estimated complete album spins in last 30 days based on ${trackPlays} track plays across ${tracksTotal} tracks`
                    : `Estimated complete album spins based on ${trackPlays} track plays across ${tracksTotal} tracks`;
            } else {
                tooltip = is30d
                    ? `30-day track plays: ${trackPlays} (track count unavailable)`
                    : `Total track plays: ${trackPlays} (track count unavailable)`;
            }
            const dispVal = Number.isInteger(decimalPlays) ? decimalPlays : decimalPlays;
            const suffix = is30d ? ' (30D)' : '';
            const label = `🔥 ${dispVal} ${dispVal === 1 ? 'Play' + suffix : 'Plays' + suffix}`;
            const colorClass = trackPlays > 0 ? (is30d ? 'text-amber-400 font-black' : 'text-emerald-400 font-black') : 'text-gray-400 font-bold';
            return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${tooltip}">${label}</div>`;
        }

        function renderUnownedGrid() {
            const grid = document.getElementById("unownedAlbumGrid");
            const toShow = filteredUnowned;
            document.getElementById("unownedDisplayedCount").innerText = toShow.length;
            const badge = document.getElementById("unownedCountBadge");
            if (badge) badge.innerText = UNOWNED_ALBUMS.length;

            if (toShow.length === 0) {
                grid.innerHTML = '<div class="col-span-full py-16 text-center text-gray-500 text-sm">No unowned stream-discovered albums found. You have saved everything you spin!</div>';
                return;
            }

            grid.innerHTML = toShow.map(a => `
                <div class="group relative flex flex-col cursor-pointer"
                     onmouseenter="onCardHover('${a.album_artist_name.replace(/'/g, "\\\\'")}', '${a.album_name.replace(/'/g, "\\\\'")}', '${a.album_url}', this)"
                     onmouseleave="onCardLeave(this)">
                    <div class="aspect-square w-full rounded-2xl overflow-hidden bg-gray-900 border-2 border-dashed border-amber-500/40 group-hover:border-amber-400/70 shadow-[0_10px_25px_-5px_rgba(245,158,11,0.15)] transition duration-300 group-hover:scale-[1.03] relative flex items-center justify-center">
                        ${a.album_image_url && a.album_image_url.startsWith('http') ? `
                            <img src="${a.album_image_url}" alt="${a.album_name}" class="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition">
                        ` : `
                            <div class="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-amber-950/40 via-gray-900 to-gray-950 p-4 text-center">
                                <div class="w-14 h-14 mb-2 text-amber-400 opacity-90">
                                    {{ brand_icon | safe }}
                                </div>
                                <span class="text-[10px] font-bold text-amber-300 tracking-wider uppercase px-2 py-0.5 bg-amber-500/10 rounded-md border border-amber-500/30">Unowned Crate</span>
                            </div>
                        `}

                        <div class="absolute top-2 left-2 bg-amber-500/20 text-amber-300 backdrop-blur-md rounded-lg px-2 py-0.5 border border-amber-500/30 text-[10px] font-bold select-none flex items-center gap-1 shadow">
                            ✨ Streamed
                        </div>

                        <div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] text-amber-200 select-none">
                            🔥 ${a.play_count} ${a.play_count === 1 ? 'Play' : 'Plays'}
                        </div>

                        <div class="audio-pulse hidden absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded-full px-2 py-1 flex items-end gap-0.5 h-4 border border-emerald-500/40">
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                            <span class="w-0.5 bg-emerald-400 wave-bar"></span>
                        </div>

                        <div class="absolute inset-x-0 bottom-0 p-3 bg-gradient-to-t from-black/90 via-black/60 to-transparent opacity-0 group-hover:opacity-100 transition flex justify-center">
                            <button onclick="saveAlbumToLibrary('${(a.album_id||'').replace(/'/g, "\\\\'")}', '${a.album_name.replace(/'/g, "\\\\'")}', '${a.album_artist_name.replace(/'/g, "\\\\'")}', event)" class="bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs px-3 py-1.5 rounded-xl shadow transition flex items-center gap-1.5">
                                ➕ Save to Library
                            </button>
                        </div>
                    </div>
                    <div class="mt-2.5 px-0.5">
                        <h4 class="text-xs font-bold text-white truncate group-hover:text-amber-400 transition" title="${a.album_name}">${a.album_name}</h4>
                        <p class="text-[11px] text-gray-400 truncate" title="${a.album_artist_name}">${a.album_artist_name}</p>
                        <p class="text-[10px] text-gray-500 mt-0.5">Last played: ${a.last_played_at ? a.last_played_at.substring(0,10) : 'Recent'}</p>
                    </div>
                </div>
            `).join('');
        }

        function onUnownedFilterChange() {
            const query = document.getElementById("unownedSearchInput").value.toLowerCase().trim();
            filteredUnowned = UNOWNED_ALBUMS.filter(a => {
                return !query || a.album_name.toLowerCase().includes(query) || a.album_artist_name.toLowerCase().includes(query);
            });
            renderUnownedGrid();
        }

        async function saveAlbumToLibrary(albumId, albumName, artistName, event) {
            if (event) event.stopPropagation();
            const displayName = albumName ? `"${albumName}"` : "this album";
            if (!confirm(`Add ${displayName} to your Spotify saved library and permanent vinyl crate?`)) return;

            try {
                const res = await fetch("/api/save-album", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ album_id: albumId, album_name: albumName, artist_name: artistName })
                });
                const data = await res.json();
                if (data.status === "success") {
                    alert(data.message || "Album successfully added to your library! Refreshing view...");
                    window.location.reload();
                } else {
                    alert("Error: " + (data.message || "Failed to save album"));
                }
            } catch (e) {
                alert("Network error while saving album.");
            }
        }

        let currentUnownedHorizon = 'all';

        async function changeUnownedHorizon(horizon) {
            currentUnownedHorizon = horizon;
            ['30d', '90d', 'all'].forEach(h => {
                const btn = document.getElementById(`unownedHorizon-${h}`);
                if (!btn) return;
                if (h === horizon) {
                    btn.className = "px-3 py-1 rounded-lg text-xs font-bold transition bg-amber-500/20 text-amber-300 border border-amber-500/30";
                } else {
                    btn.className = "px-3 py-1 rounded-lg text-xs font-medium text-gray-400 hover:text-white transition";
                }
            });

            try {
                const res = await fetch(`/api/unowned-albums?horizon=${horizon}`);
                const data = await res.json();
                if (data.status === "success") {
                    UNOWNED_ALBUMS.length = 0;
                    UNOWNED_ALBUMS.push(...data.unowned);
                    filteredUnowned = [...UNOWNED_ALBUMS];
                    renderUnownedGrid();
                }
            } catch(e) {
                console.error("Error fetching unowned albums horizon:", e);
            }
        }

        function switchCrateTab(tab) {
            const savedView = document.getElementById("savedVinylView");
            const unownedView = document.getElementById("unownedVinylView");
            const savedBtn = document.getElementById("savedVinylTabBtn");
            const unownedBtn = document.getElementById("unownedVinylTabBtn");

            if (tab === 'saved') {
                savedView.classList.remove("hidden");
                unownedView.classList.add("hidden");
                savedBtn.className = "px-4 py-2 rounded-xl text-xs font-bold transition bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-2 shadow";
                unownedBtn.className = "px-4 py-2 rounded-xl text-xs font-bold transition bg-gray-900 text-gray-400 hover:text-white border border-gray-800 hover:border-gray-700 flex items-center gap-2";
            } else {
                savedView.classList.add("hidden");
                unownedView.classList.remove("hidden");
                unownedBtn.className = "px-4 py-2 rounded-xl text-xs font-bold transition bg-amber-500/20 text-amber-300 border border-amber-500/40 flex items-center gap-2 shadow";
                savedBtn.className = "px-4 py-2 rounded-xl text-xs font-bold transition bg-gray-900 text-gray-400 hover:text-white border border-gray-800 hover:border-gray-700 flex items-center gap-2";
                renderUnownedGrid();
            }
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
                        ${getAlbumPlayBadge(a)}
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

            if (sort === "plays_30d_desc") {
                filteredAlbums.sort((a,b) => {
                    const normB = b.album_normalized_plays_30d !== undefined ? Number(b.album_normalized_plays_30d) : (b.album_tracks_total ? Math.floor((b.album_track_plays_30d||0)/b.album_tracks_total) : (b.album_track_plays_30d||0));
                    const normA = a.album_normalized_plays_30d !== undefined ? Number(a.album_normalized_plays_30d) : (a.album_tracks_total ? Math.floor((a.album_track_plays_30d||0)/a.album_tracks_total) : (a.album_track_plays_30d||0));
                    return (normB - normA) || ((b.album_track_plays_30d||0) - (a.album_track_plays_30d||0)) || ((b.album_track_plays||0) - (a.album_track_plays||0));
                });
            } else if (sort === "plays_desc") {
                filteredAlbums.sort((a,b) => {
                    const normB = b.album_normalized_plays !== undefined ? Number(b.album_normalized_plays) : (b.album_tracks_total ? Math.floor((b.album_track_plays||0)/b.album_tracks_total) : (b.album_track_plays||0));
                    const normA = a.album_normalized_plays !== undefined ? Number(a.album_normalized_plays) : (a.album_tracks_total ? Math.floor((a.album_track_plays||0)/a.album_tracks_total) : (a.album_track_plays||0));
                    return (normB - normA) || ((b.album_track_plays||0) - (a.album_track_plays||0));
                });
            } else if (sort === "plays_asc") {
                filteredAlbums.sort((a,b) => {
                    const normB = b.album_normalized_plays !== undefined ? Number(b.album_normalized_plays) : (b.album_tracks_total ? Math.floor((b.album_track_plays||0)/b.album_tracks_total) : (b.album_track_plays||0));
                    const normA = a.album_normalized_plays !== undefined ? Number(a.album_normalized_plays) : (a.album_tracks_total ? Math.floor((a.album_track_plays||0)/a.album_tracks_total) : (a.album_track_plays||0));
                    return (normA - normB) || ((a.album_track_plays||0) - (b.album_track_plays||0));
                });
            }
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

        /* Avatar Persona Picker Handlers (APP-04) */
        function toggleAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.toggle('hidden');
        }

        function closeAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.add('hidden');
        }

        document.addEventListener('click', function(e) {
            const d = document.querySelector('.avatarPickerDropdown');
            if (d && !d.classList.contains('hidden')) {
                if (!d.contains(e.target)) {
                    d.classList.add('hidden');
                }
            }
        });

        async function uploadHistoryFiles(e) {
            if (e) e.stopPropagation();
            const files = e.target.files;
            if (!files || files.length === 0) return;

            const statusEl = document.getElementById('historyUploadStatus');
            if (statusEl) {
                statusEl.className = "text-[10px] text-center font-bold text-amber-400 pt-1";
                statusEl.textContent = `Uploading & parsing ${files.length} file(s)...`;
                statusEl.classList.remove('hidden');
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                const resp = await fetch('/api/user/upload-history', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (resp.ok && data.status === 'success') {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-emerald-400 pt-1";
                        statusEl.textContent = `✓ ${data.message}`;
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                        statusEl.textContent = `Error: ${data.message || 'Upload failed'}`;
                    }
                }
            } catch (err) {
                console.error("Upload error:", err);
                if (statusEl) {
                    statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                    statusEl.textContent = `Error: Network failure`;
                }
            }
        }

        async function toggleUserPalsOptIn() {
            try {
                const res = await fetch('/api/user/toggle-pals', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('palsOptInStatusBadge');
                    if (badge) {
                        if (data.pals_opt_in) {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
                        } else {
                            badge.textContent = 'Inactive';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle pals opt-in:', err);
            }
        }

        async function toggleUserSyncPause() {
            try {
                const res = await fetch('/api/user/toggle-sync-pause', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('syncPauseStatusBadge');
                    if (badge) {
                        if (data.sync_paused) {
                            badge.textContent = 'Paused';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
                        } else {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle sync pause:', err);
            }
        }

        async function selectAvatarPreset(presetId, e) {
            if (e) e.stopPropagation();
            const statusEl = document.querySelector('.avatarSaveStatus');
            if (statusEl) {
                statusEl.innerText = "⏳ Saving...";
                statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-amber-400";
                statusEl.classList.remove('hidden');
            }

            try {
                const resp = await fetch('/api/user/avatar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({avatar_id: presetId})
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    const avatarImgs = document.querySelectorAll('.headerUserAvatarImg');
                    avatarImgs.forEach(img => {
                        if (data.avatar_url) img.src = data.avatar_url;
                    });
                    if (statusEl) {
                        statusEl.innerText = "✓ Persona saved!";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400";
                    }
                    const list = document.querySelector('.avatarOptionsList');
                    if (list) {
                        const buttons = list.querySelectorAll('button');
                        buttons.forEach(btn => {
                            btn.classList.remove('bg-emerald-500/10', 'border-emerald-500/30');
                            const check = btn.querySelector('.text-emerald-400.text-xs');
                            if (check) check.remove();
                        });
                        const clickedBtn = e ? e.currentTarget : null;
                        if (clickedBtn) {
                            clickedBtn.classList.add('bg-emerald-500/10', 'border-emerald-500/30');
                            const span = document.createElement('span');
                            span.className = 'text-emerald-400 text-xs font-bold shrink-0';
                            span.innerText = '✓';
                            clickedBtn.appendChild(span);
                        }
                    }
                    setTimeout(() => {
                        closeAvatarDropdown();
                    }, 500);
                } else {
                    if (statusEl) {
                        statusEl.innerText = "❌ Error saving persona";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                    }
                }
            } catch (err) {
                console.error("Avatar error:", err);
                if (statusEl) {
                    statusEl.innerText = "❌ Network error";
                    statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                }
            }
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
            onFilterChange();
            if (!isAudioEnabled) {
                const btnText = document.getElementById('audioText');
                const btnIcon = document.getElementById('audioIcon');
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
            }
            const urlParams = new URLSearchParams(window.location.search);
            const tab = urlParams.get('tab');
            if (tab === 'unowned') {
                switchCrateTab('unowned');
            } else if (tab === 'saved') {
                switchCrateTab('saved');
            }
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
        RECOMMEND_HTML,
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


RECOMMEND_HTML = """
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
                        <h1 class="text-3xl font-extrabold tracking-tight">
                            <span class="text-white">Spin</span><span class="text-[#1DB954]">Sleeve</span>
                        </h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2 py-0.5 rounded-full border border-emerald-500/30">CRATE DIGGER</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Smart crate digging &amp; personalized discovery based on {{ user.display_name }}'s library</p>
            </div>

            <!-- Top-Level Navigation Tabs -->
            <nav class="hidden md:flex items-center gap-1 bg-[#0c0f12] p-1 rounded-xl border border-gray-800 shadow-inner">
                <a href="/beta/" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    Library
                </a>
                <a href="/beta/analytics" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Analytics
                </a>
                <a href="/beta/pals" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    SpinPals
                </a>
            </nav>

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
                <div class="relative flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5" id="userProfileWidget">
                    <button type="button" onclick="toggleAvatarDropdown(event)"
                            class="relative w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 hover:border-emerald-400 hover:scale-105 active:scale-95 transition-all cursor-pointer flex items-center justify-center shrink-0 focus:outline-none"
                            title="Click to choose Music Legend avatar">
                        <img class="headerUserAvatarImg w-full h-full object-cover" src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" alt="{{ user.display_name }}">
                    </button>

                    <!-- Avatar & Settings Dropdown Menu (POLISH-08) -->
                    <div class="avatarPickerDropdown hidden absolute right-0 top-full mt-2 w-72 bg-[#14181f] border border-gray-700/80 rounded-2xl shadow-2xl p-3 z-50 text-left backdrop-blur-xl">
                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-gray-800">
                            <div>
                                <span class="text-[11px] font-black uppercase tracking-wider text-emerald-400">User Settings</span>
                                <p class="text-[10px] text-gray-400">{{ user.display_name }}'s Crate &amp; Lounge</p>
                            </div>
                            <button type="button" onclick="closeAvatarDropdown(event)" class="text-gray-400 hover:text-white text-xs p-1 leading-none font-bold">&times;</button>
                        </div>

                        <div class="space-y-2 mb-3 pb-3 border-b border-gray-800">
                            <button type="button" onclick="toggleUserPalsOptIn()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-emerald-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">🤝 Opt-in SpinPals</span>
                                <span id="palsOptInStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.pals_opt_in %}bg-emerald-500/20 text-emerald-300 border border-emerald-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.pals_opt_in %}Active{% else %}Inactive{% endif %}
                                </span>
                            </button>
                            <button type="button" onclick="toggleUserSyncPause()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-amber-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">⏸️ Sync Pause</span>
                                <span id="syncPauseStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.sync_paused %}bg-amber-500/20 text-amber-300 border border-amber-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.sync_paused %}Paused{% else %}Active{% endif %}
                                </span>
                            </button>
                            <input type="file" id="historyUploadInput" accept=".json,.zip" multiple class="hidden" onchange="uploadHistoryFiles(event)">
                            <button type="button" onclick="document.getElementById('historyUploadInput').click()"
                                    class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold transition">
                                📂 Import History (.json / .zip)
                            </button>
                            <div id="historyUploadStatus" class="hidden text-[10px] text-center font-bold text-amber-400 pt-1"></div>
                            <a href="/beta/logout" class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold transition">
                                🚪 Logout ({{ user.display_name }})
                            </a>
                        </div>

                        <div class="mb-2">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Music Legend Persona</span>
                        </div>
                        <div class="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar avatarOptionsList">
                            <button type="button" onclick="selectAvatarPreset('spotify', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if not user.custom_avatar_id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center shrink-0">
                                    {% if user.spotify_avatar_url %}
                                    <img src="{{ user.spotify_avatar_url }}" class="w-full h-full object-cover">
                                    {% else %}
                                    <span class="text-xs">🟢</span>
                                    {% endif %}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">Spotify Profile</div>
                                    <div class="text-[10px] text-gray-400 truncate">Default Spotify photo</div>
                                </div>
                                {% if not user.custom_avatar_id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>

                            {% if avatar_presets %}
                            {% for preset in avatar_presets %}
                            <button type="button" onclick="selectAvatarPreset('{{ preset.id }}', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if user.custom_avatar_id == preset.id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden shrink-0 shadow-sm">
                                    <img src="/avatar/{{ preset.id }}.svg" alt="{{ preset.name }}" class="w-full h-full object-cover">
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">{{ preset.name }}</div>
                                    <div class="text-[10px] text-gray-400 truncate">{{ preset.badge }} {{ preset.era }} • {{ preset.desc }}</div>
                                </div>
                                {% if user.custom_avatar_id == preset.id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>
                            {% endfor %}
                            {% endif %}
                        </div>

                        <div class="avatarSaveStatus hidden mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400">
                            ✓ Persona saved!
                        </div>
                    </div>

                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition" title="Exit assumed view and revert to Admin">↩ Revert</a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </header>

        

        <!-- Hardware-Inspired Segmented Sub-Tab Control Deck under Library (POLISH-08) -->
        <div class="flex items-center p-1 bg-[#080a0c] rounded-xl border border-gray-800 shadow-inner mb-6 w-fit">
            <a href="/beta/" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/40 transition flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"/></svg>
                <span>My Saved Vinyl</span>
            </a>
            <a href="/beta/recommend" class="px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-gradient-to-r from-emerald-500/20 to-teal-500/25 text-emerald-300 border border-emerald-500/30 shadow-sm">
                <svg class="w-3.5 h-3.5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"/></svg>
                <span>Crate Digger</span>
            </a>
            <a href="/beta/?tab=unowned" class="px-4 py-2 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/40 transition flex items-center gap-2">
                <svg class="w-3.5 h-3.5 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"/></svg>
                <span>You Should Save These</span>
            </a>
        </div>

        <!-- Control Deck (Streamlined 2-Tier Digging Console - POLISH-01) -->
        <div class="card-bg p-4 rounded-2xl border border-gray-800/90 mb-6 shadow-xl backdrop-blur-sm">
            <!-- Row 1: Crate Target Focus (Single Dimension) & Shuffle -->
            <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-3 border-b border-gray-800/70">
                <div class="flex flex-col sm:flex-row sm:items-center gap-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400 shrink-0">1. Crate Target:</span>
                    <div class="flex flex-wrap gap-1.5">
                        <button onclick="setTarget('heavy_30d')" id="horizonBtn-30d" class="pill-active px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0" title="Albums actively spun in the last 30 days">
                            <span>🔥</span> Heavy Rotation (30D: {{ kpis.played_albums_30d or 0 }})
                        </button>
                        <button onclick="setTarget('unplayed')" id="modeBtn-discover" class="pill-inactive px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0" title="Albums in your library with zero recorded plays">
                            <span>🔍</span> Unplayed Gems ({{ kpis.unplayed_albums or 0 }})
                        </button>
                        <button onclick="setTarget('cold')" id="targetBtn-cold" class="pill-inactive px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0" title="Played before, but not spun in the last 30 days">
                            <span>❄️</span> Cold Shelf ({{ (kpis.played_albums - (kpis.played_albums_30d or 0)) if kpis.played_albums >= (kpis.played_albums_30d or 0) else 0 }})
                        </button>
                        <button onclick="setTarget('classics')" id="horizonBtn-all" class="pill-inactive px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0" title="All-time most-played favorite records">
                            <span>⭐</span> All-Time Favorites ({{ kpis.played_albums or 0 }})
                        </button>
                        <button onclick="setTarget('all')" id="targetBtn-all" class="pill-inactive px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0" title="Entire library collection">
                            <span>🌌</span> Full Crate ({{ kpis.total_albums or 0 }})
                        </button>
                    </div>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                    <button onclick="spinAgain()" class="text-xs font-bold text-black bg-[#1DB954] hover:bg-[#1ed760] px-3.5 py-1.5 rounded-xl transition shadow flex items-center gap-1.5" title="Reshuffle spotlight picks and candidate records">
                        <span>🎲</span> Spin Again
                    </button>
                </div>
            </div>

            <!-- Row 2: Vibe, Era & Sub-Genre (Horizontal Flow) -->
            <div class="grid grid-cols-1 md:grid-cols-12 gap-2 pt-3 items-center">
                <!-- Mood & Vibe (Col 1-5) -->
                <div class="md:col-span-5 flex flex-col sm:flex-row sm:items-center gap-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400 shrink-0">2. Vibe:</span>
                    <div class="flex flex-wrap gap-1.5">
                        <button onclick="setVibe('all')" id="vibeBtn-all" class="pill-active px-2.5 py-1 rounded-lg text-xs transition">🌌 Any</button>
                        <button onclick="setVibe('chill')" id="vibeBtn-chill" class="pill-inactive px-2.5 py-1 rounded-lg text-xs transition" title="Ambient, Dream Pop, Shoegaze, Downtempo, Trip Hop">🌙 Chill</button>
                        <button onclick="setVibe('energetic')" id="vibeBtn-energetic" class="pill-inactive px-2.5 py-1 rounded-lg text-xs transition" title="Punk, Alt Rock, Electronic, Dance, Techno, Hip Hop">⚡ Energetic</button>
                        <button onclick="setVibe('mellow')" id="vibeBtn-mellow" class="pill-inactive px-2.5 py-1 rounded-lg text-xs transition" title="Acoustic, Folk, Singer-Songwriter, Jazz, Bossa Nova">☕ Mellow</button>
                        <button onclick="setVibe('vintage')" id="vibeBtn-vintage" class="pill-inactive px-2.5 py-1 rounded-lg text-xs transition" title="Classic Soul, Motown, Blues, 60s/70s Psychedelic">📻 Vintage</button>
                    </div>
                </div>

                <!-- Era Preference (Col 6-9) -->
                <div class="md:col-span-4 flex items-center gap-1.5">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400 shrink-0">3. Era:</span>
                    <div class="flex flex-nowrap gap-1">
                        <button onclick="setEra('all')" id="eraBtn-all" class="pill-active px-2 py-1 rounded-lg text-xs transition whitespace-nowrap">All</button>
                        <button onclick="setEra('recent')" id="eraBtn-recent" class="pill-inactive px-2 py-1 rounded-lg text-xs transition whitespace-nowrap" title="2018 to Present">✨ 2018+</button>
                        <button onclick="setEra('modern')" id="eraBtn-modern" class="pill-inactive px-2 py-1 rounded-lg text-xs transition whitespace-nowrap" title="2000 - 2017">💿 00s-10s</button>
                        <button onclick="setEra('classic')" id="eraBtn-classic" class="pill-inactive px-2 py-1 rounded-lg text-xs transition whitespace-nowrap" title="Before 2000">📼 &lt;2000</button>
                    </div>
                </div>

                <!-- Sub-Genre Dropdown (Col 10-12) -->
                <div class="md:col-span-3 flex items-center gap-2">
                    <span class="text-[11px] font-bold uppercase tracking-wider text-gray-400 shrink-0">4. Genre:</span>
                    <select id="genreSelect" onchange="onGenreSelect(this.value)" class="w-full bg-[#11151a] border border-gray-700/80 rounded-lg py-1 px-2 text-xs text-gray-200 focus:outline-none focus:border-[#1DB954]">
                        <option value="">Any Genre</option>
                        {% for g in top_genres %}
                        <option value="{{ g }}">{{ g|title }}</option>
                        {% endfor %}
                    </select>
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
        let selectedTarget = 'heavy_30d';
        let selectedHorizon = '30d';
        let selectedMode = 'favorites';
        let selectedVibe = 'all';
        let selectedEra = 'all';
        let selectedGenre = '';
        let currentSeed = Math.random();

        let hoverTimer = null;
        let activeAudio = new Audio();
        let currentHoverKey = null;
        let isAudioEnabled = localStorage.getItem('spinAudioEnabled') !== 'false';
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
            localStorage.setItem('spinAudioEnabled', isAudioEnabled);
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                if (btnText) btnText.innerText = 'Hover Audio: ON';
                if (btnIcon) btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
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
            chill: [
                'ambient', 'chill', 'downtempo', 'lo-fi', 'dream pop', 'slowcore',
                'shoegaze', 'trip hop', 'ethereal', 'ambient pop', 'minimalism',
                'idm', 'post-rock', 'bedroom pop', 'chillwave', 'drone'
            ],
            energetic: [
                'punk', 'hard rock', 'garage rock', 'alternative rock', 'grunge',
                'noise rock', 'post-punk', 'electronic', 'dance', 'techno',
                'house', 'hip hop', 'rap', 'club', 'breakbeat', 'big beat',
                'drum and bass', 'edm', 'synthpop', 'indietronica'
            ],
            mellow: [
                'folk', 'acoustic', 'singer-songwriter', 'indie folk', 'chamber pop',
                'chamber folk', 'jazz', 'bossa nova', 'quiet storm', 'americana',
                'bluegrass', 'soft rock', 'chanson', 'soul'
            ],
            vintage: [
                'classic rock', 'psychedelic rock', 'blues', 'motown', 'classic soul',
                'brill building', 'roots rock', 'funk', 'hard bop', 'soul jazz',
                'traditional pop', 'rockabilly', 'doo-wop', 'vintage'
            ]
        };

        function setTarget(target) {
            selectedTarget = target;
            selectedHorizon = (target === 'heavy_30d') ? '30d' : 'all';
            selectedMode = (target === 'unplayed') ? 'discover' : 'favorites';

            const targets = ['heavy_30d', 'unplayed', 'cold', 'classics', 'all'];
            targets.forEach(t => {
                const btnId = (t === 'heavy_30d') ? 'horizonBtn-30d' :
                              (t === 'unplayed') ? 'modeBtn-discover' :
                              (t === 'classics') ? 'horizonBtn-all' :
                              `targetBtn-${t}`;
                const btn = document.getElementById(btnId);
                if (btn) {
                    btn.className = (t === target ? 'pill-active' : 'pill-inactive') + ' px-3 py-1.5 rounded-xl text-xs font-semibold transition flex items-center gap-1.5 shrink-0';
                }
            });
            runRecommender();
        }

        function setHorizon(horizon) {
            selectedHorizon = horizon;
            if (horizon === '30d') {
                setTarget('heavy_30d');
            } else {
                setTarget('classics');
            }
        }

        function setMode(mode) {
            selectedMode = mode;
            if (mode === 'discover') {
                setTarget('unplayed');
            } else {
                setTarget(selectedHorizon === '30d' ? 'heavy_30d' : 'classics');
            }
        }

        function setVibe(vibe) {
            selectedVibe = vibe;
            ['all', 'chill', 'energetic', 'mellow', 'vintage'].forEach(v => {
                const btn = document.getElementById(`vibeBtn-${v}`);
                if (btn) btn.className = (v === vibe ? 'pill-active' : 'pill-inactive') + ' px-2.5 py-1 rounded-lg text-xs transition';
            });
            runRecommender();
        }

        function setEra(era) {
            selectedEra = era;
            ['all', 'recent', 'modern', 'classic'].forEach(e => {
                const btn = document.getElementById(`eraBtn-${e}`);
                if (btn) btn.className = (e === era ? 'pill-active' : 'pill-inactive') + ' px-2 py-1 rounded-lg text-xs transition';
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
                if (selectedVibe === 'vintage') {
                    const y = parseInt(album.release_year) || 0;
                    if (y > 0 && y < 1985) score += 20;
                }
            }

            if (album.has_gatefold) score += 12;

            if (selectedTarget === 'unplayed') {
                const plays = (album.album_track_plays || 0);
                if (plays === 0) score += 35;
                else score -= plays * 2;
            } else if (selectedTarget === 'cold') {
                const playsAll = album.album_track_plays || 0;
                score += Math.min(playsAll * 2.0, 35);
            } else if (selectedTarget === 'heavy_30d') {
                const plays30 = album.album_track_plays_30d || 0;
                score += Math.min(plays30 * 4.0, 40);
                score += Math.min((album.album_track_plays || 0) * 0.5, 10);
            } else if (selectedTarget === 'classics') {
                const plays = album.album_track_plays || 0;
                score += Math.min(plays * 2.5, 35);
            } else {
                score += (album.album_track_plays || 0) > 0 ? 10 : 0;
            }

            return score;
        }

        function runRecommender() {
            let pool = ALL_ALBUMS.filter(a => {
                if (selectedTarget === 'unplayed') {
                    if ((a.album_track_plays || 0) > 0) return false;
                } else if (selectedTarget === 'cold') {
                    if ((a.album_track_plays || 0) === 0) return false;
                    if ((a.album_track_plays_30d || 0) > 0) return false;
                } else if (selectedTarget === 'heavy_30d') {
                    if ((a.album_track_plays_30d || 0) === 0) return false;
                } else if (selectedTarget === 'classics') {
                    if ((a.album_track_plays || 0) === 0) return false;
                }

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
                    let hasVibe = keywords.some(k => gStr.includes(k));
                    if (!hasVibe && selectedVibe === 'vintage') {
                        const y = parseInt(a.release_year) || 0;
                        if (y > 0 && y < 1985) hasVibe = true;
                    }
                    if (!hasVibe) return false;
                }

                return true;
            });

            // If 30-day heavy rotation filter produced no results, gracefully fall back to all-time favorites
            if (pool.length === 0 && selectedTarget === 'heavy_30d') {
                pool = ALL_ALBUMS.filter(a => (a.album_track_plays || 0) > 0);
                if (pool.length === 0) pool = ALL_ALBUMS;
            }

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

        function getAlbumPlayBadge(a) {
            const is30d = (typeof selectedHorizon !== 'undefined') && selectedHorizon === '30d';
            const trackPlays = is30d ? (Number(a.album_track_plays_30d) || 0) : (Number(a.album_track_plays) || 0);
            const tracksTotal = Number(a.album_tracks_total) || 0;

            if (is30d && a.album_plays_display_30d && a.album_plays_tooltip_30d) {
                const colorClass = trackPlays > 0 ? 'text-amber-400 font-black' : 'text-gray-400 font-bold';
                return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${a.album_plays_tooltip_30d}">${a.album_plays_display_30d}</div>`;
            } else if (!is30d && a.album_plays_display && a.album_plays_tooltip) {
                const colorClass = trackPlays > 0 ? 'text-emerald-400 font-black' : 'text-gray-400 font-bold';
                return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${a.album_plays_tooltip}">${a.album_plays_display}</div>`;
            }

            let normPlays = 0;
            let tooltip = '';
            if (tracksTotal > 0) {
                normPlays = Math.floor(trackPlays / tracksTotal);
                tooltip = is30d
                    ? `Estimated complete album spins in last 30 days based on ${trackPlays} track plays across ${tracksTotal} tracks`
                    : `Estimated complete album spins based on ${trackPlays} track plays across ${tracksTotal} tracks`;
            } else {
                normPlays = trackPlays;
                tooltip = is30d
                    ? `30-day track plays: ${trackPlays} (track count unavailable)`
                    : `Total track plays: ${trackPlays} (track count unavailable)`;
            }
            const suffix = is30d ? ' (30D)' : '';
            const label = `🔥 ${normPlays} ${normPlays === 1 ? 'Play' + suffix : 'Plays' + suffix}`;
            const colorClass = trackPlays > 0 ? (is30d ? 'text-amber-400 font-black' : 'text-emerald-400 font-black') : 'text-gray-400 font-bold';
            return `<div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] ${colorClass} select-none" title="${tooltip}">${label}</div>`;
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
                            ${getAlbumPlayBadge(a)}
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
                        ${getAlbumPlayBadge(a)}
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

        /* Avatar Persona Picker Handlers (APP-04) */
        function toggleAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.toggle('hidden');
        }

        function closeAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.add('hidden');
        }

        document.addEventListener('click', function(e) {
            const d = document.querySelector('.avatarPickerDropdown');
            if (d && !d.classList.contains('hidden')) {
                if (!d.contains(e.target)) {
                    d.classList.add('hidden');
                }
            }
        });

        async function uploadHistoryFiles(e) {
            if (e) e.stopPropagation();
            const files = e.target.files;
            if (!files || files.length === 0) return;

            const statusEl = document.getElementById('historyUploadStatus');
            if (statusEl) {
                statusEl.className = "text-[10px] text-center font-bold text-amber-400 pt-1";
                statusEl.textContent = `Uploading & parsing ${files.length} file(s)...`;
                statusEl.classList.remove('hidden');
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                const resp = await fetch('/api/user/upload-history', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (resp.ok && data.status === 'success') {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-emerald-400 pt-1";
                        statusEl.textContent = `✓ ${data.message}`;
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                        statusEl.textContent = `Error: ${data.message || 'Upload failed'}`;
                    }
                }
            } catch (err) {
                console.error("Upload error:", err);
                if (statusEl) {
                    statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                    statusEl.textContent = `Error: Network failure`;
                }
            }
        }

        async function toggleUserPalsOptIn() {
            try {
                const res = await fetch('/api/user/toggle-pals', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('palsOptInStatusBadge');
                    if (badge) {
                        if (data.pals_opt_in) {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
                        } else {
                            badge.textContent = 'Inactive';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle pals opt-in:', err);
            }
        }

        async function toggleUserSyncPause() {
            try {
                const res = await fetch('/api/user/toggle-sync-pause', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('syncPauseStatusBadge');
                    if (badge) {
                        if (data.sync_paused) {
                            badge.textContent = 'Paused';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
                        } else {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle sync pause:', err);
            }
        }

        async function selectAvatarPreset(presetId, e) {
            if (e) e.stopPropagation();
            const statusEl = document.querySelector('.avatarSaveStatus');
            if (statusEl) {
                statusEl.innerText = "⏳ Saving...";
                statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-amber-400";
                statusEl.classList.remove('hidden');
            }

            try {
                const resp = await fetch('/api/user/avatar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({avatar_id: presetId})
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    const avatarImgs = document.querySelectorAll('.headerUserAvatarImg');
                    avatarImgs.forEach(img => {
                        if (data.avatar_url) img.src = data.avatar_url;
                    });
                    if (statusEl) {
                        statusEl.innerText = "✓ Persona saved!";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400";
                    }
                    const list = document.querySelector('.avatarOptionsList');
                    if (list) {
                        const buttons = list.querySelectorAll('button');
                        buttons.forEach(btn => {
                            btn.classList.remove('bg-emerald-500/10', 'border-emerald-500/30');
                            const check = btn.querySelector('.text-emerald-400.text-xs');
                            if (check) check.remove();
                        });
                        const clickedBtn = e ? e.currentTarget : null;
                        if (clickedBtn) {
                            clickedBtn.classList.add('bg-emerald-500/10', 'border-emerald-500/30');
                            const span = document.createElement('span');
                            span.className = 'text-emerald-400 text-xs font-bold shrink-0';
                            span.innerText = '✓';
                            clickedBtn.appendChild(span);
                        }
                    }
                    setTimeout(() => {
                        closeAvatarDropdown();
                    }, 500);
                } else {
                    if (statusEl) {
                        statusEl.innerText = "❌ Error saving persona";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                    }
                }
            } catch (err) {
                console.error("Avatar error:", err);
                if (statusEl) {
                    statusEl.innerText = "❌ Network error";
                    statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                }
            }
        }

        document.addEventListener("DOMContentLoaded", () => {
            runRecommender();
            if (!isAudioEnabled) {
                const btnText = document.getElementById('audioText');
                const btnIcon = document.getElementById('audioIcon');
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
            }
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
    force_refresh = request.args.get("refresh") in ("1", "true")
    if force_refresh:
        keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{user_id}::")]
        for k in keys_to_del:
            _user_analytics_cache.pop(k, None)
            _user_analytics_cache_time.pop(k, None)
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    return render_template_string(
        ANALYTICS_HTML,
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
    force_refresh = request.args.get("refresh") in ("1", "true")
    if force_refresh:
        keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{user_id}::")]
        for k in keys_to_del:
            _user_analytics_cache.pop(k, None)
            _user_analytics_cache_time.pop(k, None)

    payload = fetch_user_analytics_data(
        user_id=user_id,
        range_param=range_param,
        genre_param=genre_param,
        start_date=start_date,
        end_date=end_date,
        force_refresh=force_refresh
    )
    return jsonify(payload)


ANALYTICS_HTML = """
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
                        <h1 class="text-3xl font-extrabold tracking-tight">
                            <span class="text-white">Spin</span><span class="text-[#1DB954]">Sleeve</span>
                        </h1>
                        <span class="bg-emerald-500/20 text-emerald-400 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-emerald-500/30">ANALYTICS</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Deep listening telemetry, taste velocity &amp; acoustic habits for {{ user.display_name }}</p>
            </div>

                        <!-- Top-Level Navigation Tabs -->
            

                        <!-- Top-Level Navigation Tabs -->
            <nav class="hidden md:flex items-center gap-1 bg-[#0c0f12] p-1 rounded-xl border border-gray-800 shadow-inner">
                <a href="/beta/" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    Library
                </a>
                <a href="/beta/analytics" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 flex items-center gap-2 transition shadow-sm">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Analytics
                </a>
                <a href="/beta/pals" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    SpinPals
                </a>
            </nav>

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
                <div class="relative flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5" id="userProfileWidget">
                    <button type="button" onclick="toggleAvatarDropdown(event)"
                            class="relative w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 hover:border-emerald-400 hover:scale-105 active:scale-95 transition-all cursor-pointer flex items-center justify-center shrink-0 focus:outline-none"
                            title="Click for settings & avatar picker">
                        <img class="headerUserAvatarImg w-full h-full object-cover" src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" alt="{{ user.display_name }}">
                    </button>

                    <!-- Avatar & Settings Dropdown Menu (POLISH-08) -->
                    <div class="avatarPickerDropdown hidden absolute right-0 top-full mt-2 w-72 bg-[#14181f] border border-gray-700/80 rounded-2xl shadow-2xl p-3 z-50 text-left backdrop-blur-xl">
                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-gray-800">
                            <div>
                                <span class="text-[11px] font-black uppercase tracking-wider text-emerald-400">User Settings</span>
                                <p class="text-[10px] text-gray-400">{{ user.display_name }}'s Crate &amp; Lounge</p>
                            </div>
                            <button type="button" onclick="closeAvatarDropdown(event)" class="text-gray-400 hover:text-white text-xs p-1 leading-none font-bold">&times;</button>
                        </div>

                        <div class="space-y-2 mb-3 pb-3 border-b border-gray-800">
                            <button type="button" onclick="toggleUserPalsOptIn()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-emerald-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">🤝 Opt-in SpinPals</span>
                                <span id="palsOptInStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.pals_opt_in %}bg-emerald-500/20 text-emerald-300 border border-emerald-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.pals_opt_in %}Active{% else %}Inactive{% endif %}
                                </span>
                            </button>
                            <button type="button" onclick="toggleUserSyncPause()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-amber-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">⏸️ Sync Pause</span>
                                <span id="syncPauseStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.sync_paused %}bg-amber-500/20 text-amber-300 border border-amber-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.sync_paused %}Paused{% else %}Active{% endif %}
                                </span>
                            </button>
                            <input type="file" id="historyUploadInput" accept=".json,.zip" multiple class="hidden" onchange="uploadHistoryFiles(event)">
                            <button type="button" onclick="document.getElementById('historyUploadInput').click()"
                                    class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold transition">
                                📂 Import History (.json / .zip)
                            </button>
                            <div id="historyUploadStatus" class="hidden text-[10px] text-center font-bold text-amber-400 pt-1"></div>
                            <a href="/beta/logout" class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold transition">
                                🚪 Logout ({{ user.display_name }})
                            </a>
                        </div>

                        <div class="mb-2">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Music Legend Persona</span>
                        </div>
                        <div class="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar avatarOptionsList">
                            <button type="button" onclick="selectAvatarPreset('spotify', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if not user.custom_avatar_id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center shrink-0">
                                    {% if user.spotify_avatar_url %}
                                    <img src="{{ user.spotify_avatar_url }}" class="w-full h-full object-cover">
                                    {% else %}
                                    <span class="text-xs">🟢</span>
                                    {% endif %}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">Spotify Profile</div>
                                    <div class="text-[10px] text-gray-400 truncate">Default Spotify photo</div>
                                </div>
                                {% if not user.custom_avatar_id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>

                            {% if avatar_presets %}
                            {% for preset in avatar_presets %}
                            <button type="button" onclick="selectAvatarPreset('{{ preset.id }}', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if user.custom_avatar_id == preset.id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden shrink-0 shadow-sm">
                                    <img src="/avatar/{{ preset.id }}.svg" alt="{{ preset.name }}" class="w-full h-full object-cover">
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">{{ preset.name }}</div>
                                    <div class="text-[10px] text-gray-400 truncate">{{ preset.badge }} {{ preset.era }} • {{ preset.desc }}</div>
                                </div>
                                {% if user.custom_avatar_id == preset.id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>
                            {% endfor %}
                            {% endif %}
                        </div>

                        <div class="avatarSaveStatus hidden mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400">
                            ✓ Persona saved!
                        </div>
                    </div>

                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition" title="Exit assumed view and revert to Admin">↩ Revert</a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </header>

        

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
            if (window.location.search.includes('refresh=1') || window.location.search.includes('refresh=true')) {
                url += '&refresh=1';
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

        let isAudioEnabled = localStorage.getItem('spinAudioEnabled') !== 'false';
        function toggleHoverAudio() {
            isAudioEnabled = !isAudioEnabled;
            localStorage.setItem('spinAudioEnabled', isAudioEnabled);
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                if (btnText) btnText.innerText = 'Hover Audio: ON';
                if (btnIcon) btnIcon.innerText = '🔊';
            } else {
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
            }
        }

        document.addEventListener("DOMContentLoaded", () => {
            if (!isAudioEnabled) {
                const btnText = document.getElementById('audioText');
                const btnIcon = document.getElementById('audioIcon');
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
            }
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

        /* Avatar Persona Picker Handlers (APP-04) */
        function toggleAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.toggle('hidden');
        }

        function closeAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.add('hidden');
        }

        document.addEventListener('click', function(e) {
            const d = document.querySelector('.avatarPickerDropdown');
            if (d && !d.classList.contains('hidden')) {
                if (!d.contains(e.target)) {
                    d.classList.add('hidden');
                }
            }
        });

        async function uploadHistoryFiles(e) {
            if (e) e.stopPropagation();
            const files = e.target.files;
            if (!files || files.length === 0) return;

            const statusEl = document.getElementById('historyUploadStatus');
            if (statusEl) {
                statusEl.className = "text-[10px] text-center font-bold text-amber-400 pt-1";
                statusEl.textContent = `Uploading & parsing ${files.length} file(s)...`;
                statusEl.classList.remove('hidden');
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                const resp = await fetch('/api/user/upload-history', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (resp.ok && data.status === 'success') {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-emerald-400 pt-1";
                        statusEl.textContent = `✓ ${data.message}`;
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                        statusEl.textContent = `Error: ${data.message || 'Upload failed'}`;
                    }
                }
            } catch (err) {
                console.error("Upload error:", err);
                if (statusEl) {
                    statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                    statusEl.textContent = `Error: Network failure`;
                }
            }
        }

        async function toggleUserPalsOptIn() {
            try {
                const res = await fetch('/api/user/toggle-pals', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('palsOptInStatusBadge');
                    if (badge) {
                        if (data.pals_opt_in) {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
                        } else {
                            badge.textContent = 'Inactive';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle pals opt-in:', err);
            }
        }

        async function toggleUserSyncPause() {
            try {
                const res = await fetch('/api/user/toggle-sync-pause', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('syncPauseStatusBadge');
                    if (badge) {
                        if (data.sync_paused) {
                            badge.textContent = 'Paused';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
                        } else {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle sync pause:', err);
            }
        }

        async function selectAvatarPreset(presetId, e) {
            if (e) e.stopPropagation();
            const statusEl = document.querySelector('.avatarSaveStatus');
            if (statusEl) {
                statusEl.innerText = "⏳ Saving...";
                statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-amber-400";
                statusEl.classList.remove('hidden');
            }

            try {
                const resp = await fetch('/api/user/avatar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({avatar_id: presetId})
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    const avatarImgs = document.querySelectorAll('.headerUserAvatarImg');
                    avatarImgs.forEach(img => {
                        if (data.avatar_url) img.src = data.avatar_url;
                    });
                    if (statusEl) {
                        statusEl.innerText = "✓ Persona saved!";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400";
                    }
                    const list = document.querySelector('.avatarOptionsList');
                    if (list) {
                        const buttons = list.querySelectorAll('button');
                        buttons.forEach(btn => {
                            btn.classList.remove('bg-emerald-500/10', 'border-emerald-500/30');
                            const check = btn.querySelector('.text-emerald-400.text-xs');
                            if (check) check.remove();
                        });
                        const clickedBtn = e ? e.currentTarget : null;
                        if (clickedBtn) {
                            clickedBtn.classList.add('bg-emerald-500/10', 'border-emerald-500/30');
                            const span = document.createElement('span');
                            span.className = 'text-emerald-400 text-xs font-bold shrink-0';
                            span.innerText = '✓';
                            clickedBtn.appendChild(span);
                        }
                    }
                    setTimeout(() => {
                        closeAvatarDropdown();
                    }, 500);
                } else {
                    if (statusEl) {
                        statusEl.innerText = "❌ Error saving persona";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                    }
                }
            } catch (err) {
                console.error("Avatar error:", err);
                if (statusEl) {
                    statusEl.innerText = "❌ Network error";
                    statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                }
            }
        }
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
        {% if is_impersonating %}
        <div class="bg-amber-500/10 border border-amber-500/30 text-amber-300 px-4 py-2.5 rounded-2xl text-xs flex items-center justify-between mb-6 shadow-lg">
            <span class="flex items-center gap-2">
                👑 <span>Currently testing as: <strong class="text-white">{{ session.display_name }}</strong> (SpinPals Locked for this account)</span>
            </span>
            <div class="flex items-center gap-2">
                <a href="/beta/admin" class="text-xs text-amber-400 hover:text-amber-300 font-bold px-2 py-1">⚙️ Admin Deck</a>
                <a href="/beta/admin/revert" class="bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-3 py-1 rounded-xl text-xs transition">
                    ↩ Revert to Admin
                </a>
            </div>
        </div>
        {% endif %}

        <header class="flex items-center justify-between pb-6 mb-8 border-b border-gray-800">
            <div class="flex items-center gap-3">
                <div class="w-10 h-10 shrink-0">{{ brand_icon | safe }}</div>
                <div>
                    <h1 class="text-xl font-black text-white">SpinSleeve</h1>
                    <p class="text-[10px] font-mono tracking-widest text-emerald-400 uppercase">Listening Lounge</p>
                </div>
            </div>
            <div class="flex items-center gap-2">
                {% if is_admin %}
                <a href="/beta/admin" class="text-xs font-semibold text-gray-300 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 rounded-lg transition border border-gray-700">
                    ⚙️ Admin
                </a>
                {% endif %}
                <a href="/beta/" class="text-xs font-bold text-gray-300 hover:text-white bg-gray-800 border border-gray-700 px-3.5 py-1.5 rounded-xl transition">
                    ← Back to Library
                </a>
            </div>
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

    is_impersonating = bool(session.get("is_impersonating", False))
    # If the real admin is logged in directly as themselves (not impersonating), they have full access
    is_admin_direct = (
        (current_user_id in ADMIN_USER_IDS)
        and (session.get("role") == "admin")
        and not is_impersonating
    )

    # When impersonating, strictly evaluate the assumed user's opt-in status!
    has_access = is_admin_direct or bool(
        curr_user and curr_user.get("pals_opt_in")
    )

    if not has_access:
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

    horizon = request.args.get("horizon", "30d").lower()
    if horizon not in ("30d", "all_time"):
        horizon = "30d"

    pal_data = compute_pal_compatibility(current_user_id, target_pal["spotify_id"], horizon=horizon)

    return render_template_string(
        PALS_HTML,
        user=session,
        pals=pals_directory,
        selected_pal=pal_data["pal"],
        compatibility=pal_data["compatibility"],
        top_borrow=pal_data["top_borrow"],
        shared_albums=pal_data["shared_albums"],
        pal_crate=pal_data["pal_full_crate"],
        horizon=horizon,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


PALS_HTML = """
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
                        <h1 class="text-3xl font-extrabold tracking-tight">
                            <span class="text-white">Spin</span><span class="text-[#1DB954]">Sleeve</span>
                        </h1>
                        <span class="bg-rose-500/20 text-rose-400 text-[10px] font-bold px-2.5 py-0.5 rounded-full border border-rose-500/30">SPINPALS: CRATEMATES</span>
                    </div>
                </div>
                <p class="text-xs text-gray-400 mt-1">Acoustic chemistry, taste overlap &amp; vinyl shelf borrowing</p>
            </div>

            <!-- Top-Level Navigation Tabs -->
            <nav class="hidden md:flex items-center gap-1 bg-[#0c0f12] p-1 rounded-xl border border-gray-800 shadow-inner">
                <a href="/beta/" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/></svg>
                    Library
                </a>
                <a href="/beta/analytics" class="px-4 py-1.5 rounded-lg text-xs font-medium text-gray-400 hover:text-white hover:bg-gray-800/50 flex items-center gap-2 transition">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>
                    Analytics
                </a>
                <a href="/beta/pals" class="px-4 py-1.5 rounded-lg text-xs font-semibold text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 flex items-center gap-2 transition shadow-sm">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>
                    SpinPals
                </a>
            </nav>

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
                <div class="relative flex items-center gap-2 bg-[#14181f] border border-gray-800 rounded-xl px-3 py-1.5" id="userProfileWidget">
                    <button type="button" onclick="toggleAvatarDropdown(event)"
                            class="relative w-6 h-6 rounded-full overflow-hidden bg-gray-800 border border-gray-700 hover:border-emerald-400 hover:scale-105 active:scale-95 transition-all cursor-pointer flex items-center justify-center shrink-0 focus:outline-none"
                            title="Click to choose Music Legend avatar">
                        <img class="headerUserAvatarImg w-full h-full object-cover" src="{{ user.avatar_url or 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=100' }}" alt="{{ user.display_name }}">
                    </button>

                    <!-- Avatar & Settings Dropdown Menu (POLISH-08) -->
                    <div class="avatarPickerDropdown hidden absolute right-0 sm:right-0 max-w-[calc(100vw-2rem)] sm:w-72 top-full mt-2 bg-[#14181f] border border-gray-700/80 rounded-2xl shadow-2xl p-3 z-50 text-left backdrop-blur-xl">
                        <div class="flex items-center justify-between pb-2 mb-2 border-b border-gray-800">
                            <div>
                                <span class="text-[11px] font-black uppercase tracking-wider text-emerald-400">User Settings</span>
                                <p class="text-[10px] text-gray-400">{{ user.display_name }}'s Crate &amp; Lounge</p>
                            </div>
                            <button type="button" onclick="closeAvatarDropdown(event)" class="text-gray-400 hover:text-white text-xs p-1 leading-none font-bold">&times;</button>
                        </div>

                        <div class="space-y-2 mb-3 pb-3 border-b border-gray-800">
                            <button type="button" onclick="toggleUserPalsOptIn()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-emerald-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">🤝 Opt-in SpinPals</span>
                                <span id="palsOptInStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.pals_opt_in %}bg-emerald-500/20 text-emerald-300 border border-emerald-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.pals_opt_in %}Active{% else %}Inactive{% endif %}
                                </span>
                            </button>
                            <button type="button" onclick="toggleUserSyncPause()"
                                    class="w-full flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 hover:bg-gray-800 border border-gray-800 hover:border-amber-500/40 transition text-xs font-semibold text-white">
                                <span class="flex items-center gap-2">⏸️ Sync Pause</span>
                                <span id="syncPauseStatusBadge" class="text-[10px] font-mono px-2 py-0.5 rounded-full {% if user.sync_paused %}bg-amber-500/20 text-amber-300 border border-amber-500/30{% else %}bg-gray-800 text-gray-400{% endif %}">
                                    {% if user.sync_paused %}Paused{% else %}Active{% endif %}
                                </span>
                            </button>
                            <input type="file" id="historyUploadInput" accept=".json,.zip" multiple class="hidden" onchange="uploadHistoryFiles(event)">
                            <button type="button" onclick="document.getElementById('historyUploadInput').click()"
                                    class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs font-bold transition">
                                📂 Import History (.json / .zip)
                            </button>
                            <div id="historyUploadStatus" class="hidden text-[10px] text-center font-bold text-amber-400 pt-1"></div>
                            <a href="/beta/logout" class="w-full flex items-center justify-center gap-2 p-2.5 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-300 text-xs font-bold transition">
                                🚪 Logout ({{ user.display_name }})
                            </a>
                        </div>

                        <div class="mb-2">
                            <span class="text-[10px] font-bold uppercase tracking-wider text-gray-400">Music Legend Persona</span>
                        </div>
                        <div class="max-h-48 overflow-y-auto space-y-1 pr-1 custom-scrollbar avatarOptionsList">
                            <button type="button" onclick="selectAvatarPreset('spotify', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if not user.custom_avatar_id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden flex items-center justify-center shrink-0">
                                    {% if user.spotify_avatar_url %}
                                    <img src="{{ user.spotify_avatar_url }}" class="w-full h-full object-cover">
                                    {% else %}
                                    <span class="text-xs">🟢</span>
                                    {% endif %}
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">Spotify Profile</div>
                                    <div class="text-[10px] text-gray-400 truncate">Default Spotify photo</div>
                                </div>
                                {% if not user.custom_avatar_id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>

                            {% if avatar_presets %}
                            {% for preset in avatar_presets %}
                            <button type="button" onclick="selectAvatarPreset('{{ preset.id }}', event)"
                                    class="w-full flex items-center gap-2.5 p-2 rounded-xl text-left hover:bg-gray-800/80 transition group border border-transparent hover:border-gray-700 {% if user.custom_avatar_id == preset.id %}bg-emerald-500/10 border-emerald-500/30{% endif %}">
                                <div class="w-11 h-11 rounded-full bg-gray-800 border border-gray-700 overflow-hidden shrink-0 shadow-sm">
                                    <img src="/avatar/{{ preset.id }}.svg" alt="{{ preset.name }}" class="w-full h-full object-cover">
                                </div>
                                <div class="flex-1 min-w-0">
                                    <div class="text-xs font-bold text-white truncate group-hover:text-emerald-400">{{ preset.name }}</div>
                                    <div class="text-[10px] text-gray-400 truncate">{{ preset.badge }} {{ preset.era }} • {{ preset.desc }}</div>
                                </div>
                                {% if user.custom_avatar_id == preset.id %}
                                <span class="text-emerald-400 text-xs font-bold shrink-0">✓</span>
                                {% endif %}
                            </button>
                            {% endfor %}
                            {% endif %}
                        </div>

                        <div class="avatarSaveStatus hidden mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400">
                            ✓ Persona saved!
                        </div>
                    </div>

                    <span class="text-xs font-bold text-white">{{ user.display_name }}</span>
                    {% if is_impersonating %}
                    <div class="flex items-center gap-1 border-l border-gray-800 pl-2 ml-1">
                        <span class="text-[10px] text-amber-400 font-bold">👑 Assuming: {{ user.display_name }}</span>
                        <a href="/beta/admin/revert" class="text-[10px] bg-amber-500 hover:bg-amber-400 text-black font-extrabold px-2 py-0.5 rounded transition" title="Exit assumed view and revert to Admin">↩ Revert</a>
                    </div>
                    {% endif %}
                </div>
            </div>
        </header>

        

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
            <div class="flex flex-col sm:flex-row sm:items-center justify-between mb-4 gap-3">
                <div>
                    <div class="flex items-center gap-2">
                        <span class="w-2.5 h-2.5 rounded-full bg-amber-400 animate-pulse"></span>
                        <h2 class="text-xl font-black text-white tracking-tight">Top 5 Records to Borrow from {{ selected_pal.display_name }}</h2>
                    </div>
                    <span class="text-xs text-gray-400">Curated gems on their shelf you haven't saved yet</span>
                </div>

                <!-- 2-way Horizon Switcher (APP-06) -->
                <div class="flex items-center gap-1.5 bg-black/40 border border-gray-800 rounded-xl p-1 shrink-0">
                    <a href="?horizon=30d" class="px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 {% if horizon != 'all_time' %}bg-amber-500 text-black shadow-md{% else %}text-gray-400 hover:text-white{% endif %}">
                        <span>🔥</span> Heavy Rotation (30D)
                    </a>
                    <a href="?horizon=all_time" class="px-3 py-1.5 rounded-lg text-xs font-bold transition flex items-center gap-1.5 {% if horizon == 'all_time' %}bg-amber-500 text-black shadow-md{% else %}text-gray-400 hover:text-white{% endif %}">
                        <span>🏛️</span> All-Time
                    </a>
                </div>
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
                            <div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] font-black {% if (a.active_track_plays or a.album_track_plays or 0) > 0 %}text-amber-400{% else %}text-gray-400 font-bold{% endif %} select-none"
                                 title="{{ a.active_plays_tooltip or a.album_plays_tooltip or ('Total track plays: ' ~ (a.album_track_plays | default(0))) }}">
                                {{ a.active_plays_display or a.album_plays_display or ('🔥 ' ~ (a.album_normalized_plays | default(0)) ~ ' Plays') }}
                            </div>
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
                        <div class="absolute bottom-2 left-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] font-black {% if (a.album_track_plays or 0) > 0 %}text-emerald-400{% else %}text-gray-400 font-bold{% endif %} select-none"
                             title="{{ a.album_plays_tooltip or ('Total track plays: ' ~ (a.album_track_plays | default(0))) }}">
                            {{ a.album_plays_display or ('🔥 ' ~ (a.album_normalized_plays | default(0)) ~ ' Plays') }}
                        </div>
                        {% else %}
                        <div class="absolute top-2 right-2 bg-black/75 backdrop-blur-md rounded-lg px-2 py-0.5 border border-white/10 text-[10px] font-black {% if (a.album_track_plays or 0) > 0 %}text-emerald-400{% else %}text-gray-400 font-bold{% endif %} select-none"
                             title="{{ a.album_plays_tooltip or ('Total track plays: ' ~ (a.album_track_plays | default(0))) }}">
                            {{ a.album_plays_display or ('🔥 ' ~ (a.album_normalized_plays | default(0)) ~ ' Plays') }}
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
        let isAudioEnabled = localStorage.getItem('spinAudioEnabled') !== 'false';
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
            localStorage.setItem('spinAudioEnabled', isAudioEnabled);
            const btnText = document.getElementById('audioText');
            const btnIcon = document.getElementById('audioIcon');
            if (isAudioEnabled) {
                if (btnText) btnText.innerText = 'Hover Audio: ON';
                if (btnIcon) btnIcon.innerText = '🔊';
            } else {
                stopPreview();
                if (btnText) btnText.innerText = 'Hover Audio: MUTED';
                if (btnIcon) btnIcon.innerText = '🔇';
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

        /* Avatar Persona Picker Handlers (APP-04) */
        function toggleAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.toggle('hidden');
        }

        function closeAvatarDropdown(e) {
            if (e) e.stopPropagation();
            const d = document.querySelector('.avatarPickerDropdown');
            if (d) d.classList.add('hidden');
        }

        document.addEventListener('click', function(e) {
            const d = document.querySelector('.avatarPickerDropdown');
            if (d && !d.classList.contains('hidden')) {
                if (!d.contains(e.target)) {
                    d.classList.add('hidden');
                }
            }
        });

        async function uploadHistoryFiles(e) {
            if (e) e.stopPropagation();
            const files = e.target.files;
            if (!files || files.length === 0) return;

            const statusEl = document.getElementById('historyUploadStatus');
            if (statusEl) {
                statusEl.className = "text-[10px] text-center font-bold text-amber-400 pt-1";
                statusEl.textContent = `Uploading & parsing ${files.length} file(s)...`;
                statusEl.classList.remove('hidden');
            }

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }

            try {
                const resp = await fetch('/api/user/upload-history', {
                    method: 'POST',
                    body: formData
                });
                const data = await resp.json();
                if (resp.ok && data.status === 'success') {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-emerald-400 pt-1";
                        statusEl.textContent = `✓ ${data.message}`;
                    }
                    setTimeout(() => {
                        window.location.reload();
                    }, 2000);
                } else {
                    if (statusEl) {
                        statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                        statusEl.textContent = `Error: ${data.message || 'Upload failed'}`;
                    }
                }
            } catch (err) {
                console.error("Upload error:", err);
                if (statusEl) {
                    statusEl.className = "text-[10px] text-center font-bold text-rose-400 pt-1";
                    statusEl.textContent = `Error: Network failure`;
                }
            }
        }

        async function toggleUserPalsOptIn() {
            try {
                const res = await fetch('/api/user/toggle-pals', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('palsOptInStatusBadge');
                    if (badge) {
                        if (data.pals_opt_in) {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30';
                        } else {
                            badge.textContent = 'Inactive';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle pals opt-in:', err);
            }
        }

        async function toggleUserSyncPause() {
            try {
                const res = await fetch('/api/user/toggle-sync-pause', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    const badge = document.getElementById('syncPauseStatusBadge');
                    if (badge) {
                        if (data.sync_paused) {
                            badge.textContent = 'Paused';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30';
                        } else {
                            badge.textContent = 'Active';
                            badge.className = 'text-[10px] font-mono px-2 py-0.5 rounded-full bg-gray-800 text-gray-400';
                        }
                    }
                }
            } catch (err) {
                console.error('Failed to toggle sync pause:', err);
            }
        }

        async function selectAvatarPreset(presetId, e) {
            if (e) e.stopPropagation();
            const statusEl = document.querySelector('.avatarSaveStatus');
            if (statusEl) {
                statusEl.innerText = "⏳ Saving...";
                statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-amber-400";
                statusEl.classList.remove('hidden');
            }

            try {
                const resp = await fetch('/api/user/avatar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({avatar_id: presetId})
                });
                const data = await resp.json();
                if (data.status === 'success') {
                    const avatarImgs = document.querySelectorAll('.headerUserAvatarImg');
                    avatarImgs.forEach(img => {
                        if (data.avatar_url) img.src = data.avatar_url;
                    });
                    if (statusEl) {
                        statusEl.innerText = "✓ Persona saved!";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-emerald-400";
                    }
                    const list = document.querySelector('.avatarOptionsList');
                    if (list) {
                        const buttons = list.querySelectorAll('button');
                        buttons.forEach(btn => {
                            btn.classList.remove('bg-emerald-500/10', 'border-emerald-500/30');
                            const check = btn.querySelector('.text-emerald-400.text-xs');
                            if (check) check.remove();
                        });
                        const clickedBtn = e ? e.currentTarget : null;
                        if (clickedBtn) {
                            clickedBtn.classList.add('bg-emerald-500/10', 'border-emerald-500/30');
                            const span = document.createElement('span');
                            span.className = 'text-emerald-400 text-xs font-bold shrink-0';
                            span.innerText = '✓';
                            clickedBtn.appendChild(span);
                        }
                    }
                    setTimeout(() => {
                        closeAvatarDropdown();
                    }, 500);
                } else {
                    if (statusEl) {
                        statusEl.innerText = "❌ Error saving persona";
                        statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                    }
                }
            } catch (err) {
                console.error("Avatar error:", err);
                if (statusEl) {
                    statusEl.innerText = "❌ Network error";
                    statusEl.className = "avatarSaveStatus mt-2 pt-2 border-t border-gray-800 text-[10px] text-center font-bold text-rose-400";
                }
            }
        }
    </script>
</body>
</html>
"""

BETA_EXPLORER_HTML = EXPLORER_HTML
BETA_RECOMMEND_HTML = RECOMMEND_HTML
BETA_PALS_HTML = PALS_HTML
BETA_ANALYTICS_HTML = ANALYTICS_HTML

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
