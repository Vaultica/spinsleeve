"""
SpinSleeve V2 Apple Music Service Module (`services/apple_music.py`)
------------------------------------------------------------------
Encapsulates Apple Music backend business logic, developer token acquisition,
and library catalog synchronization for web application consumers.
Adheres strictly to the layer separation invariant: route blueprints delegate
all Apple Music API and database operations through this service.

Key Exports:
- get_developer_token: Retrieves Apple Music developer JWT token.
- sync_apple_music_library: Executes user library ingestion and cache invalidation.
- AppleMusicAuthError, AppleMusicAPIError: Service-level domain exceptions.
"""

import logging
from typing import Dict, Any, Optional

from pipeline_v2.apple_music import (
    get_apple_developer_token,
    sync_apple_music_saved_albums,
    AppleMusicAuthError,
    AppleMusicAPIError
)

logger = logging.getLogger("spinsleeve_v2")


def get_developer_token(force_refresh: bool = False) -> str:
    """
    Obtains an Apple MusicKit developer bearer JWT token.
    Raises ValueError if developer credentials are unconfigured.
    """
    return get_apple_developer_token(force_refresh=force_refresh)


def sync_apple_music_library(
    user_id: str,
    music_user_token: str,
    table_suffix: str = "",
    max_albums: Optional[int] = None,
    mock_mode: bool = False
) -> Dict[str, Any]:
    """
    Syncs the user's Apple Music saved library into BigQuery user_saved_albums.
    Delegates to pipeline_v2.apple_music and triggers Datastore cache invalidations.
    """
    if not user_id:
        raise ValueError("user_id is required for Apple Music sync")
    if not music_user_token and not mock_mode:
        raise AppleMusicAuthError("music_user_token must be provided")

    token = music_user_token or ("mock_apple_music_token" if mock_mode else "")

    return sync_apple_music_saved_albums(
        user_id=user_id,
        music_user_token=token,
        table_suffix=table_suffix,
        max_albums=max_albums,
        mock_mode=mock_mode
    )
