"""
SpinSleeve V2 Core Application Entrypoint (`app.py`)
---------------------------------------------------
Main Flask WSGI application entrypoint. Initializes the Flask application,
configures session cookies for Firebase Hosting, registers modular blueprints
(auth, crate, analytics, pals, admin), and injects global template variables.
"""
import os
import sys
# Ensure src is in python path for pipeline_v2 imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import logging

from flask import Flask, session
from google.cloud import secretmanager, bigquery

from config import APP_VERSION, PROJECT_ID, ICON_A_SVG, ICON_GATEFOLD_SVG, ADMIN_USER_IDS, AVATAR_PRESETS
from services.avatars import AVATAR_SVGS
from routes.auth import auth_bp
from routes.crate import crate_bp
from routes.analytics import analytics_bp
from routes.pals import pals_bp
from routes.admin import admin_bp

# Re-export service helpers, caches, and template strings for unit tests & backward compatibility
from services.catalog import (
    fetch_user_album_data,
    fetch_unowned_album_data,
    compute_normalized_album_plays,
    sync_user_initial_data,
    _user_album_cache,
    _user_album_cache_time
)
from services.analytics import (
    fetch_user_analytics_data,
    invalidate_user_analytics_cache,
    _user_analytics_cache,
    _user_analytics_cache_time
)
from services.datastore import (
    get_datastore_client,
    save_catalog_to_datastore,
    get_catalog_from_datastore
)
from services.pals import fetch_pals_directory, compute_pal_compatibility

DATASTORE_CACHE_TTL = 86400

# Load template strings for test suite assertions
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
def _load_template(name):
    path = os.path.join(templates_dir, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

BETA_EXPLORER_HTML = _load_template("explorer.html")
BETA_RECOMMEND_HTML = _load_template("recommend.html")
BETA_ANALYTICS_HTML = _load_template("analytics.html")
BETA_PALS_HTML = _load_template("pals.html")
ADMIN_HTML_TEMPLATE = _load_template("admin.html")
PALS_LOCKED_HTML = _load_template("pals_locked.html")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("spinsleeve_v2")

app = Flask(__name__, template_folder="templates")

app.register_blueprint(auth_bp)
app.register_blueprint(crate_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(pals_bp)
app.register_blueprint(admin_bp)


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


app.secret_key = get_secret("FLASK_SECRET_KEY", "spinsleeve-beta-secure-session-key-2026")
app.config["SESSION_COOKIE_NAME"] = "__session"  # Required for Firebase Hosting
app.config["SESSION_COOKIE_PATH"] = "/"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"


@app.context_processor
def inject_globals():
    current_user_id = session.get("user_id")
    is_admin = bool(
        current_user_id in ADMIN_USER_IDS
        and session.get("role") == "admin"
        and not session.get("is_impersonating", False)
    )
    return {
        "app_version": APP_VERSION,
        "is_admin": is_admin,
        "avatar_presets": AVATAR_PRESETS,
        "avatar_svgs": AVATAR_SVGS
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
