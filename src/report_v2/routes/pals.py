"""
SpinSleeve V2 SpinPals & User Settings Blueprint (`routes/pals.py`)
------------------------------------------------------------------
Encapsulates Flask Blueprint routes for the SpinPals Listening Lounge (`/pals`),
acoustic compatibility matching, music legend avatar picker (`/api/user/avatar`),
and user privacy/sync pause toggles.
"""
import logging
from flask import Blueprint, render_template_string, request, jsonify, session
from google.cloud import datastore

from config import ADMIN_USER_IDS, ICON_A_SVG, ICON_GATEFOLD_SVG, AVATAR_PRESETS, logger
from routes.auth import login_required
import services.datastore
from services.avatars import AVATAR_SVGS

pals_bp = Blueprint("pals", __name__)


@pals_bp.route("/api/user/avatar", methods=["POST"])
@pals_bp.route("/beta/api/user/avatar", methods=["POST"])
@login_required
def update_user_avatar():
    """Saves user's chosen Music Legend Persona to Cloud Datastore & active session (APP-04)."""
    data = request.get_json(silent=True) or {}
    avatar_id = str(data.get("avatar_id", "")).strip().lower()

    valid_ids = set(AVATAR_SVGS.keys()) | {"spotify", "default", ""}
    if avatar_id not in valid_ids:
        return jsonify({"status": "error", "message": "Invalid avatar preset"}), 400

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401

    try:
        ds_client = services.datastore.get_datastore_client()
        key = ds_client.key("User", user_id)
        user = ds_client.get(key)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        spotify_avatar = user.get("spotify_avatar_url", "")
        if avatar_id and avatar_id != "spotify" and avatar_id != "default":
            custom_url = f"/avatar/{avatar_id}.svg"
            user["custom_avatar_id"] = avatar_id
            user["avatar_url"] = custom_url
            session["custom_avatar_id"] = avatar_id
            session["avatar_url"] = custom_url
        elif avatar_id == "spotify":
            user["custom_avatar_id"] = ""
            user["avatar_url"] = spotify_avatar
            session["custom_avatar_id"] = ""
            session["avatar_url"] = spotify_avatar
        else:
            user["custom_avatar_id"] = ""
            user["avatar_url"] = spotify_avatar or "/avatar/default.svg"
            session["custom_avatar_id"] = ""
            session["avatar_url"] = user["avatar_url"]

        ds_client.put(user)
        logger.info("[%s] Updated avatar preset to: %s", user_id, avatar_id)

        from app import _user_album_cache, _user_album_cache_time
        _user_album_cache.pop(user_id, None)
        _user_album_cache_time.pop(user_id, None)

        return jsonify({
            "status": "success",
            "avatar_id": user.get("custom_avatar_id", ""),
            "avatar_url": user.get("avatar_url", "")
        })
    except Exception as e:
        logger.error("[%s] Error updating avatar: %s", user_id, e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@pals_bp.route("/api/user/toggle-pals", methods=["POST"])
@pals_bp.route("/beta/api/user/toggle-pals", methods=["POST"])
@login_required
def api_toggle_user_pals():
    """Toggles user's SpinPals directory opt-in / opt-out presence (APP-12)."""
    user_id = session.get("user_id")
    try:
        ds_client = services.datastore.get_datastore_client()
        key = ds_client.key("User", user_id)
        user = ds_client.get(key)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        current_val = bool(user.get("pals_opt_in", False))
        new_val = not current_val
        user["pals_opt_in"] = new_val
        ds_client.put(user)
        session["pals_opt_in"] = new_val

        logger.info("[%s] Toggled SpinPals opt-in status to: %s", user_id, new_val)
        return jsonify({"status": "success", "pals_opt_in": new_val})
    except Exception as e:
        logger.error("[%s] Error toggling SpinPals opt-in: %s", user_id, e)
        return jsonify({"status": "error", "message": str(e)}), 500


@pals_bp.route("/api/user/toggle-sync-pause", methods=["POST"])
@pals_bp.route("/beta/api/user/toggle-sync-pause", methods=["POST"])
@login_required
def api_toggle_user_sync_pause():
    """Toggles user's scrobble sync pause flag (APP-12 / APP-13)."""
    user_id = session.get("user_id")
    try:
        ds_client = services.datastore.get_datastore_client()
        key = ds_client.key("User", user_id)
        user = ds_client.get(key)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404

        current_val = bool(user.get("sync_paused", False))
        new_val = not current_val
        user["sync_paused"] = new_val
        ds_client.put(user)
        session["sync_paused"] = new_val

        logger.info("[%s] Toggled scrobble sync pause status to: %s", user_id, new_val)
        return jsonify({"status": "success", "sync_paused": new_val})
    except Exception as e:
        logger.error("[%s] Error toggling scrobble sync pause: %s", user_id, e)
        return jsonify({"status": "error", "message": str(e)}), 500


@pals_bp.route("/pals")
@pals_bp.route("/beta/pals")
@pals_bp.route("/pals/<pal_id>")
@pals_bp.route("/beta/pals/<pal_id>")
@login_required
def beta_pals(pal_id=None):
    current_user_id = session["user_id"]
    ds_client = services.datastore.get_datastore_client()
    key = ds_client.key("User", current_user_id)
    curr_user = ds_client.get(key)

    is_impersonating = bool(session.get("is_impersonating", False))
    is_admin_direct = (
        (current_user_id in ADMIN_USER_IDS)
        and (session.get("role") == "admin")
        and not is_impersonating
    )

    pals_opt_in = curr_user and curr_user.get("pals_opt_in", False)
    if not is_admin_direct and not pals_opt_in:
        from app import PALS_LOCKED_HTML
        return render_template_string(PALS_LOCKED_HTML, brand_icon=ICON_A_SVG, user=session)

    from app import fetch_pals_directory, compute_pal_compatibility, PALS_HTML
    pals = fetch_pals_directory(current_user_id)

    selected_pal = None
    borrow_recommendations = []
    pal_albums = []
    pal_top_genres = []
    pal_compatibility = None
    horizon = request.args.get("horizon", "30d")

    if pal_id:
        selected_pal = next((p for p in pals if p["spotify_id"] == pal_id), None)
        if selected_pal:
            pal_data = compute_pal_compatibility(current_user_id, pal_id, horizon=horizon)
            borrow_recommendations = pal_data["borrow_recommendations"]
            pal_albums = pal_data["pal_albums"]
            pal_top_genres = pal_data["pal_top_genres"]
            pal_compatibility = pal_data["compatibility"]

    return render_template_string(
        PALS_HTML,
        pals=pals,
        selected_pal=selected_pal,
        borrow_recommendations=borrow_recommendations,
        pal_albums=pal_albums,
        pal_top_genres=pal_top_genres,
        pal_compatibility=pal_compatibility,
        horizon=horizon,
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


@pals_bp.route("/api/pal/compatibility/<pal_id>")
@pals_bp.route("/beta/api/pal/compatibility/<pal_id>")
@login_required
def api_pal_compatibility(pal_id):
    current_user_id = session["user_id"]
    horizon = request.args.get("horizon", "30d")
    from app import compute_pal_compatibility
    pal_data = compute_pal_compatibility(current_user_id, pal_id, horizon=horizon)
    return jsonify({
        "status": "success",
        "compatibility": pal_data["compatibility"],
        "borrow_recommendations": pal_data["borrow_recommendations"],
        "horizon": horizon
    })
