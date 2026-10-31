#!/usr/bin/env python3
"""
Spotify Refresh Token Generator for spotify-dash

Run this script locally on your computer to authenticate with Spotify
and obtain a long-lived refresh token for Cloud Functions.

Requirements:
    pip install spotipy

Usage:
    export SPOTIPY_CLIENT_ID="your_client_id"
    export SPOTIPY_CLIENT_SECRET="your_client_secret"
    python get_refresh_token.py
"""

import os
import sys

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("Error: 'spotipy' library not found. Install it with: pip install spotipy")
    sys.exit(1)

SCOPES = [
    "user-read-recently-played",
    "user-library-read"
]
DEFAULT_REDIRECT = "http://127.0.0.1:8080/callback"


def main():
    print("=" * 60)
    print(" Spotify Dash - One-Time Refresh Token Generator")
    print("=" * 60)

    client_id = os.getenv("SPOTIPY_CLIENT_ID") or input("Enter SPOTIPY_CLIENT_ID: ").strip()
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET") or input("Enter SPOTIPY_CLIENT_SECRET: ").strip()
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", DEFAULT_REDIRECT)

    print(f"\n[NOTE] Ensure '{redirect_uri}' is added to 'Redirect URIs'")
    print("       in your Spotify Developer Dashboard under App Settings!\n")

    input("Press Enter to launch browser and authenticate with Spotify...")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=" ".join(SCOPES),
        open_browser=True,
    )

    token_info = auth_manager.get_access_token(as_dict=True)
    refresh_token = token_info.get("refresh_token")

    if not refresh_token:
        print("\n[ERROR] Failed to obtain refresh token. Please check credentials.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("SUCCESS! Your permanent Spotify Refresh Token is:")
    print("=" * 60)
    print(refresh_token)
    print("=" * 60)
    print("\nNext Steps:")
    print("1. Keep this token safe.")
    print("2. Set SPOTIPY_REFRESH_TOKEN in Secret Manager or Cloud Functions.")


if __name__ == "__main__":
    main()
