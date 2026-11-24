"""
SpinSleeve Pipeline V2: Apple Music Integration Module (`pipeline_v2/apple_music.py`)
----------------------------------------------------------------------------------
Handles Apple Music developer bearer JWT token minting (ES256), Apple Music Web API
catalog and library querying (`/v1/me/library/albums`), record normalization to
the SpinSleeve `user_saved_albums` schema with canonical deduplication, BigQuery loading
with QA isolation support, and Cloud Datastore cache invalidation.

Key Exports:
- mint_developer_token: Generates ES256 JWT for Apple MusicKit authentication.
- get_apple_developer_token: Retrieves cached or freshly minted developer token.
- fetch_apple_music_library_albums: Paginates through user's Apple Music saved albums.
- get_mock_apple_music_albums: Returns curated realistic Apple Music library records for testing.
- parse_apple_music_library: Normalizes Apple Music records into sanitized DataFrame.
- sync_apple_music_saved_albums: Full sync workflow (fetch -> normalize -> BQ -> cache invalidation).
"""

import os
import re
import time
import json
import base64
import logging
import datetime
from typing import Optional, List, Dict, Any, Tuple

from google.cloud import bigquery, datastore, secretmanager
import pandas as pd
import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from cryptography.hazmat.primitives.serialization import load_pem_private_key

logger = logging.getLogger("spinsleeve_apple_music")

EDITION_BLACKLIST = [
    "deluxe", "remastered", "anniversary", "edition", "version", "reissue",
    "expanded", "collector", "live", "acoustic", "mono", "stereo", "remix",
    "deluxe edition", "anniversary edition", "expanded edition", "remaster",
    "archive collection", "archive", "super deluxe", "remastered edition",
    "collector's edition", "ultimate edition"
]


def compute_canonical_album_key(artist_name: str, album_name: str) -> str:
    """Computes a canonical sibling key for grouping editions (e.g. Deluxe vs Standard)."""
    if not artist_name or not album_name:
        return ""
    artist = str(artist_name).lower().strip()
    album = str(album_name).lower().strip()
    pattern_paren = r'\s*\((?:' + '|'.join(EDITION_BLACKLIST) + r')[^)]*\)'
    pattern_bracket = r'\s*\[(?:' + '|'.join(EDITION_BLACKLIST) + r')[^\]]*\]'
    album = re.sub(pattern_paren, '', album, flags=re.IGNORECASE)
    album = re.sub(pattern_bracket, '', album, flags=re.IGNORECASE)
    album = re.sub(r'\s*-\s*(?:deluxe|remastered|anniversary|edition|version|reissue|expanded|collector|live|acoustic|mono|stereo|remix).*$', '', album, flags=re.IGNORECASE)
    album = re.sub(r'\s+', ' ', album).strip()
    return f"{artist}::{album}"

PROJECT_ID = os.environ.get("GCP_PROJECT", "secret-compass-181513")
DATASET_V2 = "spotify_v2"
APPLE_MUSIC_API_BASE = "https://api.music.apple.com"

# In-memory token cache
_cached_developer_token: Optional[str] = None
_token_expiry_timestamp: float = 0.0


class AppleMusicAuthError(Exception):
    """Raised when Apple Music developer or user token authentication fails."""
    pass


class AppleMusicAPIError(Exception):
    """Raised when Apple Music Web API encounters an unexpected error."""
    pass


def get_secret(secret_name: str, default: str = "") -> str:
    """Fetches a secret from environment variables or Google Cloud Secret Manager."""
    val = os.getenv(secret_name)
    if val:
        return val.strip()
    try:
        sm_client = secretmanager.SecretManagerServiceClient()
        path = f"projects/{PROJECT_ID}/secrets/{secret_name}/versions/latest"
        res = sm_client.access_secret_version(request={"name": path})
        return res.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.debug("Could not fetch secret %s: %s", secret_name, e)
        return default


def safe_str(val: Any, default: str = "") -> str:
    """Ensures value is a clean string without NaN or None."""
    if val is None or pd.isna(val):
        return default
    return str(val).strip()


def safe_int(val: Any, default: Optional[int] = None) -> Optional[int]:
    """Ensures value is an integer or None."""
    if val is None or pd.isna(val):
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def safe_float(val: Any, default: Optional[float] = None) -> Optional[float]:
    """Ensures value is a float or None."""
    if val is None or pd.isna(val):
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _base64url_encode(data: bytes) -> str:
    """Encodes bytes into unpadded base64url string."""
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def mint_developer_token(
    key_id: str,
    team_id: str,
    private_key_pem: str,
    exp_seconds: int = 15552000
) -> str:
    """
    Generates an ES256 JSON Web Token (JWT) for Apple MusicKit authentication.
    - key_id: 10-character Apple Music Key ID (e.g., 'ABC123DEFG')
    - team_id: 10-character Apple Developer Team ID
    - private_key_pem: PEM-encoded EC private key (.p8 format)
    - exp_seconds: Expiration in seconds (default: 180 days, max allowed by Apple)
    """
    if not key_id or not team_id or not private_key_pem:
        raise ValueError("key_id, team_id, and private_key_pem must all be provided")

    # Load EC private key
    key_bytes = private_key_pem.encode("utf-8") if isinstance(private_key_pem, str) else private_key_pem
    private_key = load_pem_private_key(key_bytes, password=None)
    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Apple Music private key must be an Elliptic Curve (EC) private key")

    now = int(time.time())
    header = {
        "alg": "ES256",
        "kid": key_id.strip(),
        "typ": "JWT"
    }
    payload = {
        "iss": team_id.strip(),
        "iat": now,
        "exp": now + exp_seconds
    }

    # Prepare signature payload
    header_b64 = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")

    # Sign with ECDSA SHA-256
    der_signature = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = decode_dss_signature(der_signature)

    # Standard IEEE P1363 (32 bytes r + 32 bytes s for P-256)
    raw_signature = r.to_bytes(32, byteorder="big") + s.to_bytes(32, byteorder="big")
    sig_b64 = _base64url_encode(raw_signature)

    return f"{header_b64}.{payload_b64}.{sig_b64}"


def get_apple_developer_token(force_refresh: bool = False) -> str:
    """
    Retrieves a cached developer token or mints a new one if expired or not found.
    Checks environment / Secret Manager for credentials:
    - APPLE_MUSIC_KEY_ID or APPLE_KEY_ID
    - APPLE_MUSIC_TEAM_ID or APPLE_TEAM_ID
    - APPLE_MUSIC_PRIVATE_KEY or APPLE_PRIVATE_KEY
    """
    global _cached_developer_token, _token_expiry_timestamp

    now = time.time()
    # If cached and has at least 24 hours of validity left, reuse
    if not force_refresh and _cached_developer_token and (_token_expiry_timestamp - now) > 86400:
        return _cached_developer_token

    key_id = get_secret("APPLE_MUSIC_KEY_ID") or get_secret("APPLE_KEY_ID")
    team_id = get_secret("APPLE_MUSIC_TEAM_ID") or get_secret("APPLE_TEAM_ID")
    private_key_pem = get_secret("APPLE_MUSIC_PRIVATE_KEY") or get_secret("APPLE_PRIVATE_KEY")

    if not key_id or not team_id or not private_key_pem:
        raise ValueError(
            "Apple Music developer credentials missing. "
            "Ensure APPLE_MUSIC_KEY_ID, APPLE_MUSIC_TEAM_ID, and APPLE_MUSIC_PRIVATE_KEY are configured."
        )

    # Lifetime: 180 days (~15,552,000 seconds)
    exp_seconds = 15552000
    token = mint_developer_token(key_id, team_id, private_key_pem, exp_seconds=exp_seconds)
    _cached_developer_token = token
    _token_expiry_timestamp = now + exp_seconds

    logger.info("Successfully minted Apple Music developer token (exp: %s seconds)", exp_seconds)
    return token


def format_artwork_url(template_url: Optional[str], width: int = 600, height: int = 600, fmt: str = "jpg") -> str:
    """Resolves Apple Music artwork placeholder template '{w}x{h}bb.{f}' to concrete image URL."""
    if not template_url or not isinstance(template_url, str):
        return ""
    url = template_url.replace("{w}", str(width)).replace("{h}", str(height))
    url = url.replace("{f}", fmt)
    return url


def normalize_apple_music_album(item: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """
    Normalizes a single Apple Music library album object to the SpinSleeve user_saved_albums schema.
    Guarantees zero-NaN safety and computes canonical_album_key.
    """
    attributes = item.get("attributes") or {}
    raw_album_name = safe_str(attributes.get("name"), default="Unknown Album")
    raw_artist_name = safe_str(attributes.get("artistName"), default="Unknown Artist")
    album_id = safe_str(item.get("id"), default="")

    artwork_data = attributes.get("artwork") or {}
    raw_artwork_url = artwork_data.get("url") if isinstance(artwork_data, dict) else None
    image_url = format_artwork_url(raw_artwork_url, width=600, height=600)

    rel_date = safe_str(attributes.get("releaseDate"), default="")
    rel_year = int(rel_date[:4]) if rel_date and rel_date[:4].isdigit() else None
    tracks_total = safe_int(attributes.get("trackCount"), default=None)

    date_added_raw = attributes.get("dateAdded")
    try:
        added_at = pd.to_datetime(date_added_raw, utc=True) if date_added_raw else pd.Timestamp.now(tz="UTC")
    except Exception:
        added_at = pd.Timestamp.now(tz="UTC")

    genre_list = attributes.get("genreNames") or []
    genres = ", ".join(safe_str(g) for g in genre_list if g) if isinstance(genre_list, list) else ""

    # Relationships artist_id if available
    artist_id = None
    relationships = item.get("relationships") or {}
    artists_rel = relationships.get("artists") or {}
    artists_data = artists_rel.get("data") or []
    if artists_data and isinstance(artists_data, list) and isinstance(artists_data[0], dict):
        artist_id = safe_str(artists_data[0].get("id"), default=None)

    canonical_key = compute_canonical_album_key(raw_artist_name, raw_album_name)
    is_mock_album = bool(album_id.startswith("am_mock_") or album_id.startswith("mock_"))

    return {
        "user_id": str(user_id),
        "album_id": album_id,
        "album_uri": f"apple_music:album:{album_id}" if album_id else "",
        "album_name": raw_album_name,
        "artist_id": artist_id,
        "artist_name": raw_artist_name,
        "added_at": added_at,
        "release_date": rel_date,
        "release_year": rel_year,
        "tracks_total": tracks_total,
        "album_type": "album",
        "label": safe_str(attributes.get("recordLabel"), default=""),
        "image_url": image_url,
        "genres": genres,
        "canonical_album_key": canonical_key,
        "platform": "apple_music",
        "is_mock": is_mock_album
    }


def parse_apple_music_library(items: List[Dict[str, Any]], user_id: str) -> pd.DataFrame:
    """Transforms a list of Apple Music library album records into a sanitized pandas DataFrame."""
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        row = normalize_apple_music_album(item, user_id)
        if row["album_id"]:
            rows.append(row)

    if not rows:
        return pd.DataFrame(columns=[
            "user_id", "album_id", "album_uri", "album_name", "artist_id",
            "artist_name", "added_at", "release_date", "release_year",
            "tracks_total", "album_type", "label", "image_url", "genres",
            "canonical_album_key", "platform", "is_mock"
        ])

    df = pd.DataFrame(rows)
    df["added_at"] = pd.to_datetime(df["added_at"], utc=True)
    return df


def fetch_apple_music_library_albums(
    music_user_token: str,
    developer_token: Optional[str] = None,
    limit: int = 100,
    max_albums: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Paginates through Apple Music user library (`GET /v1/me/library/albums`).
    Returns complete raw items list.
    """
    if not music_user_token:
        raise AppleMusicAuthError("music_user_token must be provided")

    dev_token = developer_token or get_apple_developer_token()
    headers = {
        "Authorization": f"Bearer {dev_token}",
        "Music-User-Token": music_user_token.strip(),
        "Accept": "application/json"
    }

    url = f"{APPLE_MUSIC_API_BASE}/v1/me/library/albums"
    params: Dict[str, Any] = {"limit": min(limit, 100)}
    all_albums: List[Dict[str, Any]] = []

    while url:
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=10.0)
        except Exception as e:
            logger.error("Failed to connect to Apple Music API: %s", e)
            raise AppleMusicAPIError(f"Network error querying Apple Music API: {e}")

        if resp.status_code in (401, 403):
            logger.warning("Apple Music authentication rejected (HTTP %d): %s", resp.status_code, resp.text[:200])
            raise AppleMusicAuthError(f"Apple Music authentication failed (HTTP {resp.status_code})")
        elif resp.status_code == 429:
            logger.warning("Apple Music rate limit encountered (HTTP 429)")
            raise AppleMusicAPIError("Apple Music rate limit exceeded. Please retry later.")
        elif resp.status_code >= 400:
            logger.error("Apple Music API returned HTTP %d: %s", resp.status_code, resp.text[:200])
            raise AppleMusicAPIError(f"Apple Music API error: HTTP {resp.status_code}")

        try:
            payload = resp.json()
        except Exception as e:
            logger.error("Failed to decode Apple Music API JSON response: %s", e)
            raise AppleMusicAPIError("Invalid JSON from Apple Music API")

        items = payload.get("data") or []
        all_albums.extend(items)

        if max_albums and len(all_albums) >= max_albums:
            all_albums = all_albums[:max_albums]
            break

        # Check pagination
        next_path = payload.get("next")
        if next_path:
            if next_path.startswith("http"):
                url = next_path
            else:
                url = f"{APPLE_MUSIC_API_BASE}{next_path}"
            params = {}  # Next URL already includes offset and limit
        else:
            url = None

    logger.info("Fetched %d saved albums from Apple Music library", len(all_albums))
    return all_albums


def invalidate_user_datastore_caches(user_id: str, ds_client: Optional[datastore.Client] = None) -> None:
    """Invalidates UserCatalogCache, UserAnalyticsCache, and PalCompatibilityCache for user_id."""
    try:
        client = ds_client or datastore.Client(project=PROJECT_ID)
        # 1. UserCatalogCache
        cat_key = client.key("UserCatalogCache", user_id)
        client.delete(cat_key)

        # 2. UserAnalyticsCache
        analytics_query = client.query(kind="UserAnalyticsCache")
        analytics_keys = [
            e.key for e in analytics_query.fetch()
            if e.key.name and e.key.name.startswith(f"{user_id}::")
        ]
        if analytics_keys:
            client.delete_multi(analytics_keys)

        # 3. PalCompatibilityCache
        pals_query = client.query(kind="PalCompatibilityCache")
        pals_keys = [
            e.key for e in pals_query.fetch()
            if e.key.name and (e.key.name.startswith(f"{user_id}::") or f"::{user_id}::" in e.key.name)
        ]
        if pals_keys:
            client.delete_multi(pals_keys)

        logger.info("[%s] Explicitly invalidated UserCatalogCache, UserAnalyticsCache, and PalCompatibilityCache", user_id)
    except Exception as e:
        logger.warning("[%s] Error during Datastore cache invalidation: %s", user_id, e)


def get_mock_apple_music_albums() -> List[Dict[str, Any]]:
    """
    Returns a curated collection of realistic Apple Music library album records
    for development, sandbox testing, and users without an active Apple Developer subscription.
    """
    return [
        {
            "id": "am_mock_1440857781",
            "type": "library-albums",
            "attributes": {
                "name": "OK Computer",
                "artistName": "Radiohead",
                "releaseDate": "1997-05-21",
                "trackCount": 12,
                "recordLabel": "XL Recordings",
                "dateAdded": "2018-05-21T12:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/a4/82/3d/a4823d14-3686-218f-2879-11c50352ef2e/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Alternative", "Rock"]
            }
        },
        {
            "id": "am_mock_1440879161",
            "type": "library-albums",
            "attributes": {
                "name": "Discovery",
                "artistName": "Daft Punk",
                "releaseDate": "2001-03-12",
                "trackCount": 14,
                "recordLabel": "Parlophone France",
                "dateAdded": "2019-03-12T10:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/e0/75/ca/e075caec-c6ec-07ec-d4c3-58586f4a86f1/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Electronic", "Dance"]
            }
        },
        {
            "id": "am_mock_1440829233",
            "type": "library-albums",
            "attributes": {
                "name": "To Pimp a Butterfly",
                "artistName": "Kendrick Lamar",
                "releaseDate": "2015-03-15",
                "trackCount": 16,
                "recordLabel": "Top Dawg Entertainment / Aftermath",
                "dateAdded": "2020-04-01T15:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/71/f1/b7/71f1b70d-f2eb-cf0d-5872-9fbda9278bf6/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Hip-Hop/Rap"]
            }
        },
        {
            "id": "am_mock_1440854483",
            "type": "library-albums",
            "attributes": {
                "name": "Rumours",
                "artistName": "Fleetwood Mac",
                "releaseDate": "1977-02-04",
                "trackCount": 11,
                "recordLabel": "Warner Records",
                "dateAdded": "2017-02-14T09:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/4b/36/53/4b365318-6c84-18fa-35e6-ec083b7083a2/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Rock", "Pop"]
            }
        },
        {
            "id": "am_mock_1440838766",
            "type": "library-albums",
            "attributes": {
                "name": "Kind of Blue",
                "artistName": "Miles Davis",
                "releaseDate": "1959-08-17",
                "trackCount": 5,
                "recordLabel": "Columbia / Legacy",
                "dateAdded": "2016-08-17T11:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/bb/e4/22/bbe42273-df33-3151-51fb-0e42d99d1461/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Jazz"]
            }
        },
        {
            "id": "am_mock_1440818299",
            "type": "library-albums",
            "attributes": {
                "name": "Dummy",
                "artistName": "Portishead",
                "releaseDate": "1994-08-22",
                "trackCount": 11,
                "recordLabel": "Go! Beat",
                "dateAdded": "2019-08-22T14:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/3d/bf/99/3dbf999f-7e8c-8f43-aeb6-928f24419cb7/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Electronic", "Trip Hop"]
            }
        },
        {
            "id": "am_mock_1440866532",
            "type": "library-albums",
            "attributes": {
                "name": "Hounds of Love",
                "artistName": "Kate Bush",
                "releaseDate": "1985-09-16",
                "trackCount": 12,
                "recordLabel": "Fish People",
                "dateAdded": "2018-09-16T16:00:00Z",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/28/bf/ee/28bfee82-a554-ce13-7ff1-ae28fcfece4a/{w}x{h}bb.jpg",
                    "width": 1400,
                    "height": 1400
                },
                "genreNames": ["Pop", "Art Pop"]
            }
        }
    ]


def sync_apple_music_saved_albums(
    user_id: str,
    music_user_token: str,
    bq_client: Optional[bigquery.Client] = None,
    ds_client: Optional[datastore.Client] = None,
    table_suffix: str = "",
    max_albums: Optional[int] = None,
    mock_mode: bool = False
) -> Dict[str, Any]:
    """
    Executes full Apple Music saved catalog ingestion workflow:
    1. Fetches library albums via Apple Music API (or mock generator if mock_mode=True).
    2. Parses and normalizes into sanitized DataFrame.
    3. Checks existing albums in BigQuery user_saved_albums{table_suffix}.
    4. Inserts new albums and bridges entries into album_provider_ids{table_suffix}.
    5. Invalidates Datastore caches for immediate UI refresh.
    """
    is_mock = mock_mode or bool(music_user_token and music_user_token.startswith("mock_"))
    logger.info("[%s] Beginning Apple Music library synchronization (mock_mode=%s)...", user_id, is_mock)

    if is_mock:
        raw_items = get_mock_apple_music_albums()
        if max_albums and len(raw_items) > max_albums:
            raw_items = raw_items[:max_albums]
    else:
        raw_items = fetch_apple_music_library_albums(
            music_user_token=music_user_token,
            max_albums=max_albums
        )

    if not raw_items:
        logger.info("[%s] No albums found in Apple Music library.", user_id)
        return {
            "status": "success",
            "new_albums": 0,
            "total_synced": 0,
            "message": "No albums found in Apple Music library."
        }

    df = parse_apple_music_library(raw_items, user_id)
    if df.empty:
        return {
            "status": "success",
            "new_albums": 0,
            "total_synced": 0,
            "message": "No valid album records to ingest."
        }

    client = bq_client or bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_V2}.user_saved_albums{table_suffix}"

    # Query existing album_ids for this tenant
    existing_query = f"""
    SELECT DISTINCT album_id
    FROM `{table_ref}`
    WHERE user_id = @user_id
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
    )

    try:
        df_existing = client.query(existing_query, job_config=job_cfg).to_dataframe()
        existing_ids = set(df_existing["album_id"]) if not df_existing.empty else set()
    except Exception as e:
        logger.warning("[%s] Could not read existing albums from %s: %s. Assuming 0 existing.", user_id, table_ref, e)
        existing_ids = set()

    new_albums = df[~df["album_id"].isin(existing_ids)]

    if not new_albums.empty:
        load_cfg = bigquery.LoadJobConfig(
            schema_update_options=[bigquery.SchemaUpdateOption.ALLOW_FIELD_ADDITION]
        )
        load_job = client.load_table_from_dataframe(new_albums, table_ref, job_config=load_cfg)
        load_job.result()
        logger.info("[%s] Successfully inserted %d new Apple Music albums into %s", user_id, len(new_albums), table_ref)

        # Bridge into album_provider_ids
        try:
            provider_rows = []
            now_ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            for _, row in new_albums.iterrows():
                aid = row.get("album_id")
                ckey = row.get("canonical_album_key")
                if aid and ckey:
                    provider_rows.append({
                        "provider": "apple_music",
                        "external_album_id": str(aid),
                        "canonical_album_key": str(ckey),
                        "raw_album_name": str(row.get("album_name") or ""),
                        "raw_artist_name": str(row.get("artist_name") or ""),
                        "updated_at": now_ts
                    })
            if provider_rows:
                provider_table = f"{PROJECT_ID}.{DATASET_V2}.album_provider_ids{table_suffix}"
                p_job = client.load_table_from_json(provider_rows, provider_table)
                p_job.result()
                logger.info("[%s] Synced %d entries into %s", user_id, len(provider_rows), provider_table)
        except Exception as e:
            logger.warning("[%s] Error populating album_provider_ids: %s", user_id, e)

        # Invalidate Datastore document store & analytics caches
        invalidate_user_datastore_caches(user_id, ds_client)
    else:
        logger.info("[%s] All %d Apple Music albums already exist in BigQuery.", user_id, len(df))

    return {
        "status": "success",
        "new_albums": len(new_albums),
        "total_synced": len(df),
        "message": f"Successfully synced {len(new_albums)} new albums ({len(df)} total in Apple Music library)."
    }
