"""
SpinSleeve V2 Apple Music Blueprint (`routes/apple_music.py`)
-----------------------------------------------------------
Encapsulates Flask Blueprint routes for Apple MusicKit integration, including
developer token retrieval (`/api/apple-music/developer-token`) and authenticated
library synchronization (`/api/apple-music/sync`).
Preserves backward compatibility across root and `/beta/*` route aliases.
"""

import logging
from flask import Blueprint, request, jsonify, session

from routes.auth import login_required
from services.apple_music import (
    get_developer_token,
    sync_apple_music_library,
    AppleMusicAuthError,
    AppleMusicAPIError
)

logger = logging.getLogger("spinsleeve_v2")

apple_music_bp = Blueprint("apple_music", __name__)


@apple_music_bp.route("/api/apple-music/developer-token")
@apple_music_bp.route("/beta/api/apple-music/developer-token")
def api_developer_token():
    """
    Returns an Apple Music developer bearer JWT token for MusicKit client configuration.
    """
    try:
        token = get_developer_token()
        return jsonify({
            "status": "success",
            "developer_token": token
        })
    except ValueError as e:
        logger.warning("Apple Music developer token unconfigured: %s", e)
        return jsonify({
            "status": "error",
            "message": "Apple Music integration is not configured on this server."
        }), 503
    except Exception as e:
        logger.error("Failed to generate Apple Music developer token: %s", e)
        return jsonify({
            "status": "error",
            "message": "Failed to mint developer token."
        }), 500


@apple_music_bp.route("/api/apple-music/sync", methods=["POST"])
@apple_music_bp.route("/beta/api/apple-music/sync", methods=["POST"])
@login_required
def api_sync_library():
    """
    Accepts Music-User-Token from headers or JSON body, fetches user's Apple Music saved
    albums, normalizes and inserts records into BigQuery user_saved_albums, and invalidates
    Cloud Datastore caches for immediate catalog refresh.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Authentication required"}), 401

    # Extract user token and mock mode from header or JSON payload
    body = request.get_json(silent=True) or {}
    music_user_token = request.headers.get("Music-User-Token") or body.get("music_user_token")
    mock_mode = bool(
        body.get("mock_mode", False)
        or (music_user_token and music_user_token.startswith("mock_"))
        or request.headers.get("X-Mock-Mode") == "true"
    )

    if mock_mode and not music_user_token:
        music_user_token = "mock_apple_music_token"

    if not music_user_token and not mock_mode:
        return jsonify({
            "status": "error",
            "message": "Missing required 'Music-User-Token' in headers or request body."
        }), 400

    try:
        # Check for optional QA table suffix in development/testing
        table_suffix = request.headers.get("X-Table-Suffix", "")
        sync_kwargs = {
            "user_id": user_id,
            "music_user_token": music_user_token,
            "table_suffix": table_suffix
        }
        if mock_mode:
            sync_kwargs["mock_mode"] = True
        result = sync_apple_music_library(**sync_kwargs)
        return jsonify(result), 200

    except AppleMusicAuthError as e:
        logger.warning("[%s] Apple Music user token authorization error: %s", user_id, e)
        return jsonify({
            "status": "error",
            "message": "Apple Music authentication failed. The user token may be invalid or expired."
        }), 401

    except AppleMusicAPIError as e:
        logger.error("[%s] Apple Music API error during sync: %s", user_id, e)
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 502

    except Exception as e:
        logger.exception("[%s] Unexpected error during Apple Music sync: %s", user_id, e)
        return jsonify({
            "status": "error",
            "message": "An internal error occurred during Apple Music synchronization."
        }), 500
