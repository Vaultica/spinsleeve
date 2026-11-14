"""
SpinSleeve V2 Admin Control Deck Blueprint (`routes/admin.py`)
--------------------------------------------------------------
Encapsulates Flask Blueprint routes for the Admin Portal (`/admin`),
whitelist pre-approvals, SpinPals opt-in toggles, and user management.
"""
import datetime
import logging
from flask import Blueprint, render_template, request, redirect, session
from google.cloud import datastore

from app_config import ADMIN_USER_IDS, ICON_A_SVG, logger
from routes.auth import admin_required
import services.datastore

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@admin_bp.route("/beta/admin")
@admin_required
def admin_panel():
    client = services.datastore.get_datastore_client()
    query = client.query(kind="User")
    users = list(query.fetch())
    # Auto-heal: Ensure all administrator entities in Datastore have pals_opt_in set to True
    for u in users:
        uid = u.key.name or u.get("spotify_id")
        if uid in ADMIN_USER_IDS or u.get("role") == "admin":
            if not u.get("pals_opt_in"):
                u["pals_opt_in"] = True
                try:
                    client.put(u)
                except Exception as e:
                    logger.warning("Could not persist pals_opt_in for admin %s: %s", uid, e)
    return render_template('admin.html', users=users, brand_icon=ICON_A_SVG)


@admin_bp.route("/admin/toggle/<spotify_id>", methods=["POST"])
@admin_bp.route("/beta/admin/toggle/<spotify_id>", methods=["POST"])
@admin_required
def admin_toggle(spotify_id):
    client = services.datastore.get_datastore_client()
    key = client.key("User", spotify_id)
    user = client.get(key)
    if user:
        user["is_approved"] = not user.get("is_approved", False)
        client.put(user)
    return redirect("/admin")


@admin_bp.route("/admin/toggle-pals/<spotify_id>", methods=["POST"])
@admin_bp.route("/beta/admin/toggle-pals/<spotify_id>", methods=["POST"])
@admin_required
def admin_toggle_pals(spotify_id):
    client = services.datastore.get_datastore_client()
    key = client.key("User", spotify_id)
    user = client.get(key)
    if user:
        user["pals_opt_in"] = not user.get("pals_opt_in", False)
        client.put(user)
    return redirect("/admin")


@admin_bp.route("/admin/whitelist", methods=["POST"])
@admin_bp.route("/beta/admin/whitelist", methods=["POST"])
@admin_required
def admin_whitelist():
    spotify_id = request.form.get("spotify_id", "").strip()
    display_name = request.form.get("display_name", "").strip()
    pals_opt_in = request.form.get("pals_opt_in") == "on"
    if spotify_id:
        client = services.datastore.get_datastore_client()
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
    return redirect("/admin")
