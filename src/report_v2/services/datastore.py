"""
SpinSleeve V2 Cloud Datastore Service Module (`services/datastore.py`)
--------------------------------------------------------------------
Manages Cloud Datastore client connections and gzipped document store caching
for user catalogs (`UserCatalogCache`), pal compatibility (`PalCompatibilityCache`),
and listening telemetry (`UserAnalyticsCache`).
"""
import time
import json
import gzip
import datetime
import logging
from google.cloud import datastore
from app_config import PROJECT_ID, logger

DATASTORE_CACHE_TTL = 86400  # 24 hours

_user_album_cache = {}
_user_album_cache_time = {}


def get_datastore_client():
    return datastore.Client(project=PROJECT_ID)


def invalidate_user_catalog_cache(user_id):
    """Deletes cached catalog in Datastore when new listening events are synced (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        ds_client.delete(key)
        if user_id in _user_album_cache:
            del _user_album_cache[user_id]
        if user_id in _user_album_cache_time:
            del _user_album_cache_time[user_id]
        logger.info("[%s] Invalidated Datastore UserCatalogCache & in-memory cache.", user_id)
    except Exception as e:
        logger.warning("[%s] Failed to invalidate Datastore UserCatalogCache: %s", user_id, e)


def get_catalog_from_datastore(user_id):
    """Retrieves and decompresses user catalog payload from Cloud Datastore (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        entity = ds_client.get(key)
        if not entity:
            return None

        updated_at = entity.get("updated_at")
        if updated_at:
            if hasattr(updated_at, "timestamp"):
                age = time.time() - updated_at.timestamp()
            else:
                age = 0
            if age > DATASTORE_CACHE_TTL:
                logger.info("[%s] Datastore UserCatalogCache expired (age=%.0fs)", user_id, age)
                return None

        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None

        decompressed_json = gzip.decompress(raw_bytes).decode("utf-8")
        data = json.loads(decompressed_json)
        logger.info("[%s] Loaded catalog from Cloud Datastore cache (albums=%d)", user_id, len(data.get("albums", [])))
        return data
    except Exception as e:
        logger.warning("[%s] Failed to read catalog from Cloud Datastore cache: %s", user_id, e)
        return None


def save_catalog_to_datastore(user_id, data):
    """Serializes, gzips, and stores user catalog payload into Cloud Datastore (INFRA-03b)."""
    try:
        ds_client = get_datastore_client()
        key = ds_client.key("UserCatalogCache", user_id)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])

        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))

        entity["compressed_payload"] = compressed_bytes
        entity["album_count"] = len(data.get("albums", []))
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        entity["uncompressed_kb"] = round(len(raw_json) / 1024, 1)
        entity["compressed_kb"] = round(len(compressed_bytes) / 1024, 1)

        ds_client.put(entity)
        logger.info("[%s] Saved catalog to Cloud Datastore (albums=%d, raw=%.1fKB, compressed=%.1fKB)",
                    user_id, entity["album_count"], entity["uncompressed_kb"], entity["compressed_kb"])
    except Exception as e:
        logger.warning("[%s] Failed to save catalog to Cloud Datastore cache: %s", user_id, e)


def get_pal_compatibility_from_datastore(current_user_id, pal_id, horizon):
    """Retrieves and decompresses pal compatibility payload from Cloud Datastore (INFRA-03c)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{current_user_id}::{pal_id}::{horizon}"
        key = ds_client.key("PalCompatibilityCache", cache_key_name)
        entity = ds_client.get(key)
        if not entity:
            return None
        updated_at = entity.get("updated_at")
        if updated_at:
            age = time.time() - updated_at.timestamp() if hasattr(updated_at, "timestamp") else 0
            if age > DATASTORE_CACHE_TTL:
                return None
        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None
        return json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
    except Exception as e:
        logger.warning("Failed to read pal compatibility from Datastore cache: %s", e)
        return None


def save_pal_compatibility_to_datastore(current_user_id, pal_id, horizon, data):
    """Serializes, gzips, and stores pal compatibility payload into Cloud Datastore (INFRA-03c)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{current_user_id}::{pal_id}::{horizon}"
        key = ds_client.key("PalCompatibilityCache", cache_key_name)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])
        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))
        entity["compressed_payload"] = compressed_bytes
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        ds_client.put(entity)
    except Exception as e:
        logger.warning("Failed to save pal compatibility to Datastore cache: %s", e)


def get_analytics_from_datastore(user_id, range_param):
    """Retrieves and decompresses user analytics telemetry payload from Cloud Datastore (INFRA-03d)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{user_id}::{range_param}"
        key = ds_client.key("UserAnalyticsCache", cache_key_name)
        entity = ds_client.get(key)
        if not entity:
            return None
        updated_at = entity.get("updated_at")
        if updated_at:
            age = time.time() - updated_at.timestamp() if hasattr(updated_at, "timestamp") else 0
            if age > DATASTORE_CACHE_TTL:
                return None
        raw_bytes = entity.get("compressed_payload")
        if not raw_bytes:
            return None
        return json.loads(gzip.decompress(raw_bytes).decode("utf-8"))
    except Exception as e:
        logger.warning("[%s] Failed to read analytics from Datastore cache: %s", user_id, e)
        return None


def save_analytics_to_datastore(user_id, range_param, data):
    """Serializes, gzips, and stores user analytics telemetry payload into Cloud Datastore (INFRA-03d)."""
    try:
        ds_client = get_datastore_client()
        cache_key_name = f"{user_id}::{range_param}"
        key = ds_client.key("UserAnalyticsCache", cache_key_name)
        entity = datastore.Entity(key=key, exclude_from_indexes=["compressed_payload"])
        raw_json = json.dumps(data)
        compressed_bytes = gzip.compress(raw_json.encode("utf-8"))
        entity["compressed_payload"] = compressed_bytes
        entity["updated_at"] = datetime.datetime.now(datetime.timezone.utc)
        ds_client.put(entity)
    except Exception as e:
        logger.warning("[%s] Failed to save analytics to Datastore cache: %s", user_id, e)
