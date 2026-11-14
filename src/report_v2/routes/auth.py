"""
SpinSleeve V2 Authentication Blueprint (`routes/auth.py`)
-------------------------------------------------------
Encapsulates Flask Blueprint routes for Spotify OAuth login, callbacks,
session security decorators (@login_required, @admin_required), logout,
and zero-lockout admin impersonation / revert actions.
"""
import datetime
import logging
from functools import wraps
from flask import Blueprint, render_template, request, redirect, session
import spotipy
from google.cloud import datastore, bigquery

from config import PROJECT_ID, DATASET_V2, ADMIN_USER_IDS, ICON_A_SVG, logger
from services.datastore import get_datastore_client
from services.spotify import get_oauth_client

auth_bp = Blueprint("auth", __name__)


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


@auth_bp.route("/login")
@auth_bp.route("/beta/login")
def login():
    if "user_id" in session:
        return redirect("/")
    return render_template('landing.html', brand_icon=ICON_A_SVG)


@auth_bp.route("/roadmap")
@auth_bp.route("/beta/roadmap")
@auth_bp.route("/roadmap/")
@auth_bp.route("/beta/roadmap/")
def public_roadmap():
    return render_template('roadmap.html', brand_icon=ICON_A_SVG)


@auth_bp.route("/auth")
@auth_bp.route("/beta/auth")
def auth():
    sp_oauth = get_oauth_client(request)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@auth_bp.route("/callback")
@auth_bp.route("/beta/callback")
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
            return render_template('pending.html', user=user)

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
            from app import sync_user_initial_data
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


@auth_bp.route("/logout")
@auth_bp.route("/beta/logout")
def logout():
    session.clear()
    return redirect("/login")


@auth_bp.route("/admin/assume/<target_id>")
@auth_bp.route("/beta/admin/assume/<target_id>")
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

    from app import _user_album_cache, _user_album_cache_time, _user_analytics_cache, _user_analytics_cache_time
    _user_album_cache.pop(target_id, None)
    _user_album_cache_time.pop(target_id, None)
    keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{target_id}::")]
    for k in keys_to_del:
        _user_analytics_cache.pop(k, None)
        _user_analytics_cache_time.pop(k, None)

    logger.info("Admin %s assumed identity of: %s (%s)", real_admin, target_id, session["display_name"])
    return redirect("/")


@auth_bp.route("/admin/revert")
@auth_bp.route("/beta/admin/revert")
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
    session["pals_opt_in"] = bool(admin_user.get("pals_opt_in", True))
    session["sync_paused"] = bool(admin_user.get("sync_paused", False))
    session["admin_user_id"] = real_admin
    session["is_impersonating"] = False

    from app import _user_album_cache, _user_album_cache_time
    _user_album_cache.pop(real_admin, None)
    _user_album_cache_time.pop(real_admin, None)

    logger.info("Admin reverted to original identity: %s", real_admin)
    return redirect("/")
