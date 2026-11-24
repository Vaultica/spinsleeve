"""
Spotify Streaming History Parser (Extended & Legacy formats)
Supports parsing Spotify GDPR export JSON files, filtering podcasts and skips (<30s),
and normalizing records to match BigQuery playback_history schema.
"""

import json
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def parse_spotify_history_json(json_content, user_id):
    """
    Parses a Spotify streaming history JSON string or file buffer/list.
    Returns a pandas DataFrame matching playback_history schema:
    [user_id, played_at, track_uri, track_id, track_name, artist_id, artist_name, album_id, album_name]
    """
    if isinstance(json_content, str):
        try:
            data = json.loads(json_content)
        except Exception as e:
            logger.error("Failed to parse JSON string: %s", e)
            return pd.DataFrame()
    elif isinstance(json_content, list):
        data = json_content
    else:
        try:
            data = json.load(json_content)
        except Exception as e:
            logger.error("Failed to load JSON from stream: %s", e)
            return pd.DataFrame()

    rows = []
    for item in data:
        if not isinstance(item, dict):
            continue

        # Check for podcast / episode fields (skip podcasts)
        episode_name = item.get("episode_name") or item.get("episodeName")
        episode_uri = item.get("spotify_episode_uri") or item.get("episodeUri")
        if episode_name or episode_uri:
            continue

        # Determine format (Extended vs Legacy)
        # Extended format uses 'ts', 'ms_played', 'master_metadata_track_name'
        # Legacy format uses 'endTime', 'msPlayed', 'trackName', 'artistName'
        is_extended = "ts" in item or "master_metadata_track_name" in item

        if is_extended:
            played_at_raw = item.get("ts")
            ms_played = int(item.get("ms_played", 0))
            track_name = item.get("master_metadata_track_name")
            artist_name = item.get("master_metadata_album_artist_name")
            album_name = item.get("master_metadata_album_album_name")
            track_uri = item.get("spotify_track_uri")
        else:
            played_at_raw = item.get("endTime")
            ms_played = int(item.get("msPlayed", 0))
            track_name = item.get("trackName")
            artist_name = item.get("artistName")
            album_name = item.get("albumName", "Unknown Album")
            track_uri = item.get("spotifyTrackUri")

        # Skip if missing essential fields or short scrobble (< 30 seconds)
        if not track_name or not artist_name:
            continue
        if ms_played < 30000:
            continue

        # Parse timestamp
        try:
            if is_extended:
                # ISO 8601 e.g. 2024-01-15T12:34:56Z
                played_at = pd.to_datetime(played_at_raw, utc=True)
            else:
                # Legacy e.g. 2023-11-08 14:32
                played_at = pd.to_datetime(played_at_raw, utc=True)
        except Exception:
            continue

        if pd.isna(played_at):
            continue

        # Extract track_id from track_uri if available (spotify:track:ID)
        track_id = None
        if track_uri and isinstance(track_uri, str) and ":" in track_uri:
            parts = track_uri.split(":")
            if len(parts) >= 3:
                track_id = parts[2]

        rows.append({
            "user_id": str(user_id),
            "played_at": played_at,
            "track_uri": track_uri,
            "track_id": track_id,
            "track_name": str(track_name),
            "artist_id": None,
            "artist_name": str(artist_name),
            "album_id": None,
            "album_name": str(album_name) if album_name else "Unknown Album"
        })

    if not rows:
        return pd.DataFrame(columns=[
            "user_id", "played_at", "track_uri", "track_id", "track_name",
            "artist_id", "artist_name", "album_id", "album_name"
        ])

    df = pd.DataFrame(rows)
    # Ensure played_at is datetime with timezone
    df["played_at"] = pd.to_datetime(df["played_at"], utc=True)
    return df
