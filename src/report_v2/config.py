"""
SpinSleeve V2 Configuration & Constants Module (`config.py`)
------------------------------------------------------------
Defines project settings, GCP environment variables, Secret Manager accessors,
brand SVGs (rotating 33 RPM vinyl platter), and Music Legend avatar presets.
"""
import os
import logging
from google.cloud import secretmanager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_v2")

# Project & Dataset settings
PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = "spotify_v2"
PLAYBACK_HISTORY_TABLE = os.getenv("PLAYBACK_HISTORY_TABLE", f"{PROJECT_ID}.{DATASET_V2}.playback_history")
ADMIN_USER_IDS = ["serbou", "sergebou", "vaultica"]


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
SECRET_KEY = get_secret("FLASK_SECRET_KEY", "spinsleeve-beta-secure-session-key-2026")

# Application Version (POLISH-04, POLISH-01, APP-04, POLISH-09, v2.6.4)
APP_VERSION = "v2.6.4"

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

# MUSIC LEGEND ILLUSTRATED AVATARS (APP-04)
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
    {"id": "daft_punk", "name": "Daft Punk", "era": "Electronic / House", "badge": "🤖", "desc": "French touch robot duo"},
    {"id": "nina_simone", "name": "Nina Simone", "era": "Jazz & Soul", "badge": "🎶", "desc": "High Priestess of Soul"},
]
