"""
SpinSleeve V2 Library & Crate Blueprint (`routes/crate.py`)
-----------------------------------------------------------
Encapsulates Flask Blueprint routes for the Virtual Record Crate / Library Explorer (`/`),
Unowned Crate ("You Should Save These") API, and 1-click album saving (`/api/save-album`).
"""
import datetime
import logging
from flask import Blueprint, render_template, request, jsonify, session
import spotipy
from google.cloud import bigquery

from config import PROJECT_ID, DATASET_V2, ICON_A_SVG, ICON_GATEFOLD_SVG, logger
from routes.auth import login_required
from services.datastore import get_datastore_client
from services.spotify import get_token_for_user

crate_bp = Blueprint("crate", __name__)


@crate_bp.route("/api/unowned-albums")
@crate_bp.route("/beta/api/unowned-albums")
@login_required
def api_unowned_albums():
    """API endpoint to fetch unowned albums by time horizon (APP-07)."""
    user_id = session.get("user_id")
    horizon = request.args.get("horizon", "30d")
    from app import fetch_unowned_album_data
    unowned = fetch_unowned_album_data(user_id, horizon=horizon)
    return jsonify({"status": "success", "unowned": unowned, "horizon": horizon})


@crate_bp.route("/api/save-album", methods=["POST"])
@crate_bp.route("/beta/api/save-album", methods=["POST"])
@login_required
def api_save_album():
    """Saves an unowned album to Spotify saved albums and inserts into BigQuery / clears cache (APP-07)."""
    data = request.get_json(silent=True) or {}
    album_id = str(data.get("album_id", "")).strip()
    album_name = str(data.get("album_name", "")).strip()
    artist_name = str(data.get("artist_name", "")).strip()

    user_id = session.get("user_id")
    token_info = get_token_for_user(user_id, request)
    if not token_info:
        return jsonify({"status": "error", "message": "Not authorized with Spotify"}), 401

    try:
        sp = spotipy.Spotify(auth=token_info.get("access_token"), requests_timeout=15)
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

        from app import _user_album_cache, _user_album_cache_time
        if user_id in _user_album_cache:
            del _user_album_cache[user_id]
        if user_id in _user_album_cache_time:
            del _user_album_cache_time[user_id]
        try:
            ds_client = get_datastore_client()
            ds_client.delete(ds_client.key("UserCatalogCache", user_id))
        except Exception:
            pass

        return jsonify({
            "status": "success",
            "album_id": album_id,
            "image_url": image_url,
            "message": f"Successfully saved '{album_meta.get('name')}' to your library!"
        })
    except Exception as e:
        logger.error("Error saving album %s: %s", album_id, e, exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500


@crate_bp.route("/")
@crate_bp.route("/beta")
@crate_bp.route("/beta/")
def beta_index():
    if "user_id" not in session:
        from services.catalog import fetch_landing_showcase_albums
        showcase_albums = fetch_landing_showcase_albums()
        return render_template('landing.html', brand_icon=ICON_A_SVG, showcase_albums=showcase_albums)

    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    from services.catalog import fetch_user_album_data, fetch_unowned_album_data
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)
    unowned_albums = fetch_unowned_album_data(user_id)

    return render_template(
        'explorer.html',
        albums=data["albums"],
        unowned_albums=unowned_albums,
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )


@crate_bp.route("/recommend")
@crate_bp.route("/beta/recommend")
@login_required
def beta_recommend():
    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    from services.catalog import fetch_user_album_data
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    return render_template(
        'recommend.html',
        albums=data["albums"],
        top_genres=data["top_genres"],
        kpis=data["kpis"],
        user=session,
        brand_icon=ICON_A_SVG,
        gatefold_icon=ICON_GATEFOLD_SVG
    )
