"""
SpinSleeve V2 Analytics & Telemetry Blueprint (`routes/analytics.py`)
--------------------------------------------------------------------
Encapsulates Flask Blueprint routes for listening telemetry, analytics page (`/analytics`),
and JSON telemetry endpoints (`/api/analytics`).
"""
import logging
from flask import Blueprint, render_template, request, jsonify, session

from config import ICON_A_SVG, logger
from routes.auth import login_required

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/analytics")
@analytics_bp.route("/beta/analytics")
@login_required
def beta_analytics():
    user_id = session["user_id"]
    force_refresh = request.args.get("refresh") in ("1", "true")
    from services.analytics import invalidate_user_analytics_cache
    from services.catalog import fetch_user_album_data
    if force_refresh:
        invalidate_user_analytics_cache(user_id)
    data = fetch_user_album_data(user_id, force_refresh=force_refresh)

    return render_template(
        'analytics.html',
        top_genres=data["top_genres"],
        user=session,
        brand_icon=ICON_A_SVG
    )


@analytics_bp.route("/api/analytics")
@analytics_bp.route("/beta/api/analytics")
@login_required
def beta_api_analytics():
    user_id = session["user_id"]
    range_param = request.args.get("range", "30d")
    genre_param = request.args.get("genre", "all")
    start_date = request.args.get("start")
    end_date = request.args.get("end")
    force_refresh = request.args.get("refresh") in ("1", "true")
    from app import _user_analytics_cache, _user_analytics_cache_time, fetch_user_analytics_data
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
