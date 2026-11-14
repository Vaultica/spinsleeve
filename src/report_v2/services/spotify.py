"""
SpinSleeve V2 Spotify Service Module (`services/spotify.py`)
------------------------------------------------------------
Handles Spotify OAuth 2.0 PKCE client instantiation, dynamic callback URI resolution,
and offline token refreshing from Cloud Datastore.
"""
from spotipy.oauth2 import SpotifyOAuth
from app_config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, logger
from services.datastore import get_datastore_client


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


def get_token_for_user(user_id, request_obj):
    """Retrieves and refreshes Spotify access token for a user from Datastore."""
    try:
        ds_client = get_datastore_client()
        user_key = ds_client.key("User", user_id)
        user = ds_client.get(user_key)
        if not user or not user.get("refresh_token"):
            return None
        sp_oauth = get_oauth_client(request_obj)
        token_info = sp_oauth.refresh_access_token(user.get("refresh_token"))
        return token_info
    except Exception as e:
        logger.error("Error refreshing token for user %s: %s", user_id, e)
        return None
