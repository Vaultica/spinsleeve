"""
SpinSleeve V2 Listening Telemetry & Analytics Service (`services/analytics.py`)
-----------------------------------------------------------------------------
Manages extraction and aggregation of listening telemetry, time series, KPIs,
discovery vs. repeat ratios, listening heatmaps, eras, and genre breakdowns from BigQuery.
"""
import time
import math
import logging
from collections import Counter
from google.cloud import bigquery

from app_config import PROJECT_ID, DATASET_V2, PLAYBACK_HISTORY_TABLE, logger
from services.datastore import get_analytics_from_datastore, save_analytics_to_datastore
from services.bigquery import safe_str, safe_int, safe_float

_user_analytics_cache = {}
_user_analytics_cache_time = {}


def invalidate_user_analytics_cache(user_id):
    """Deletes cached analytics in Datastore when new listening events are synced (INFRA-03d)."""
    global _user_analytics_cache, _user_analytics_cache_time
    try:
        keys_to_del = [k for k in _user_analytics_cache if k.startswith(f"{user_id}::")]
        for k in keys_to_del:
            _user_analytics_cache.pop(k, None)
            _user_analytics_cache_time.pop(k, None)
        logger.info("[%s] Invalidated Datastore UserAnalyticsCache & in-memory analytics cache.", user_id)
    except Exception as e:
        logger.warning("[%s] Failed to invalidate Datastore UserAnalyticsCache: %s", user_id, e)


def fetch_user_analytics_data(user_id, range_param="30d", genre_param="all", start_date=None, end_date=None, force_refresh=False):
    global _user_analytics_cache, _user_analytics_cache_time
    cache_key = f"{user_id}::{range_param}::{genre_param}::{start_date}::{end_date}"
    now = time.time()

    if force_refresh:
        invalidate_user_analytics_cache(user_id)

    if not force_refresh:
        if cache_key in _user_analytics_cache and (now - _user_analytics_cache_time.get(cache_key, 0)) < 300:
            return _user_analytics_cache[cache_key]

        ds_cached = get_analytics_from_datastore(user_id, cache_key)
        if ds_cached:
            _user_analytics_cache[cache_key] = ds_cached
            _user_analytics_cache_time[cache_key] = now
            logger.info("[%s] Loaded analytics from Cloud Datastore cache (key=%s)", user_id, cache_key)
            return ds_cached

    client = bigquery.Client(project=PROJECT_ID)

    conditions = ["p.user_id = @user_id"]
    query_params = [bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]

    if start_date and end_date:
        conditions.append("DATE(p.played_at) BETWEEN @start_date AND @end_date")
        query_params.append(bigquery.ScalarQueryParameter("start_date", "STRING", start_date))
        query_params.append(bigquery.ScalarQueryParameter("end_date", "STRING", end_date))
    elif range_param == "1d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)")
    elif range_param == "7d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)")
    elif range_param == "30d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)")
    elif range_param == "60d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 60 DAY)")
    elif range_param == "90d":
        conditions.append("p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)")
    elif range_param in ("year", "this_year"):
        conditions.append("EXTRACT(YEAR FROM p.played_at) = EXTRACT(YEAR FROM CURRENT_TIMESTAMP())")

    if genre_param and genre_param != "all":
        conditions.append("LOWER(COALESCE(a.genres, '')) LIKE @genre_filter")
        query_params.append(bigquery.ScalarQueryParameter("genre_filter", "STRING", f"%{genre_param.lower()}%"))

    where_str = "WHERE " + " AND ".join(conditions)

    query = f"""
    WITH first_plays AS (
      SELECT
        LOWER(TRIM(album_name)) as norm_album_name,
        LOWER(TRIM(artist_name)) as norm_artist_name,
        MIN(played_at) as first_played_at
      FROM `{PLAYBACK_HISTORY_TABLE}`
      WHERE user_id = @user_id
      GROUP BY norm_album_name, norm_artist_name
    ),
    filtered_plays AS (
      SELECT
        p.album_name as album,
        p.artist_name as artist,
        p.track_name as track,
        p.track_uri,
        p.played_at as ts,
        DATE(p.played_at) as play_date,
        EXTRACT(DAYOFWEEK FROM p.played_at) as dow,
        EXTRACT(HOUR FROM p.played_at) as hour,
        COALESCE(a.image_url, g.image_url) as album_image_url,
        COALESCE(a.release_date, g.release_date) as album_release_date,
        COALESCE(a.genres, g.genres) as album_genres,
        fp.first_played_at
      FROM `{PLAYBACK_HISTORY_TABLE}` p
      LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` a
        ON p.user_id = a.user_id
        AND (
          p.album_id = a.album_id
          OR (
            LOWER(TRIM(p.album_name)) = LOWER(TRIM(a.album_name))
            AND LOWER(TRIM(p.artist_name)) = LOWER(TRIM(a.artist_name))
          )
        )
      LEFT JOIN (
        SELECT
          LOWER(TRIM(album_name)) as norm_name,
          LOWER(TRIM(artist_name)) as norm_artist,
          MAX(image_url) as image_url,
          MAX(release_date) as release_date,
          MAX(genres) as genres
        FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
        GROUP BY norm_name, norm_artist
      ) g
        ON LOWER(TRIM(p.album_name)) = g.norm_name
        AND LOWER(TRIM(p.artist_name)) = g.norm_artist
      LEFT JOIN first_plays fp
        ON LOWER(TRIM(p.album_name)) = fp.norm_album_name
        AND LOWER(TRIM(p.artist_name)) = fp.norm_artist_name
      {where_str}
    )
    SELECT * FROM filtered_plays
    """
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    df = client.query(query, job_config=job_config).to_dataframe()

    if df.empty:
        empty_payload = {
            "kpis": {"total_tracks": 0, "total_albums": 0, "total_artists": 0, "listening_time": "0h 0m", "top_album": None},
            "time_series": [],
            "discovery_vs_repeat": {"fresh_albums": 0, "repeat_albums": 0, "fresh_plays": 0, "repeat_plays": 0, "fresh_pct": 0, "repeat_pct": 0},
            "top_albums": [],
            "top_artists": [],
            "top_tracks": [],
            "eras": [],
            "genres": [],
            "heatmap": [[0]*24 for _ in range(7)]
        }
        _user_analytics_cache[cache_key] = empty_payload
        _user_analytics_cache_time[cache_key] = now
        return empty_payload

    total_tracks = len(df)
    total_artists = int(df["artist"].nunique())
    total_seconds = total_tracks * 210
    hours = total_seconds // 3600
    mins = (total_seconds % 3600) // 60
    listening_time = f"{hours}h {mins}m"

    album_counts = df.groupby(["album", "artist"]).agg(
        plays=("ts", "count"),
        album_image_url=("album_image_url", "first")
    ).reset_index().sort_values("plays", ascending=False)
    total_albums = len(album_counts)

    if not album_counts.empty:
        top_row = album_counts.iloc[0]
        top_img = safe_str(top_row.get("album_image_url"))
        if not top_img:
            top_img = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80"
        top_album = {
            "name": safe_str(top_row.get("album"), "Unknown Album"),
            "artist": safe_str(top_row.get("artist"), "Unknown Artist"),
            "image": top_img,
            "plays": int(top_row["plays"])
        }
    else:
        top_album = None

    daily = df.groupby("play_date").size().reset_index(name="plays").sort_values("play_date")
    time_series = [{"date": str(r["play_date"]), "plays": int(r["plays"])} for _, r in daily.iterrows()]

    min_window = df["ts"].min()
    album_window = df.groupby(["album", "artist", "first_played_at"]).size().reset_index(name="plays")
    fresh_mask = album_window["first_played_at"] >= min_window
    fresh_albums = int(fresh_mask.sum())
    repeat_albums = int((~fresh_mask).sum())
    fresh_plays = int(album_window[fresh_mask]["plays"].sum())
    repeat_plays = int(album_window[~fresh_mask]["plays"].sum())
    total_window_plays = fresh_plays + repeat_plays
    fresh_pct = round((fresh_plays / total_window_plays) * 100, 1) if total_window_plays > 0 else 0
    repeat_pct = round((repeat_plays / total_window_plays) * 100, 1) if total_window_plays > 0 else 0

    top_albums = []
    for _, r in album_counts.head(10).iterrows():
        img = safe_str(r.get("album_image_url"))
        if not img:
            img = "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=300&q=80"
        top_albums.append({
            "name": safe_str(r.get("album"), "Unknown Album"),
            "artist": safe_str(r.get("artist"), "Unknown Artist"),
            "image": img,
            "plays": int(r["plays"])
        })

    artist_counts = df.groupby("artist").size().reset_index(name="plays").sort_values("plays", ascending=False)
    top_artists = [{"name": safe_str(r.get("artist"), "Unknown Artist"), "plays": int(r["plays"])} for _, r in artist_counts.head(10).iterrows()]

    track_counts = df.groupby(["track", "artist", "album"]).size().reset_index(name="plays").sort_values("plays", ascending=False)
    top_tracks = []
    for _, r in track_counts.head(10).iterrows():
        top_tracks.append({
            "title": safe_str(r.get("track"), "Unknown Track"),
            "artist": safe_str(r.get("artist"), "Unknown Artist"),
            "album": safe_str(r.get("album"), "Unknown Album"),
            "plays": int(r["plays"])
        })

    def get_era(rel_date):
        if not rel_date or len(str(rel_date)) < 4:
            return "Unknown"
        y = str(rel_date)[:4]
        if not y.isdigit(): return "Unknown"
        yi = int(y)
        if yi < 1970: return "<1970"
        elif yi < 1980: return "70s"
        elif yi < 1990: return "80s"
        elif yi < 2000: return "90s"
        elif yi < 2010: return "2000s"
        elif yi < 2020: return "2010s"
        else: return "2020s"

    df["era"] = df["album_release_date"].apply(get_era)
    era_order = ["<1970", "70s", "80s", "90s", "2000s", "2010s", "2020s"]
    era_counts = df.groupby("era").size().to_dict()
    eras = [{"era": e, "plays": int(era_counts.get(e, 0))} for e in era_order if era_counts.get(e, 0) > 0]

    genre_counter = Counter()
    for g_str in df["album_genres"].dropna():
        if g_str:
            for g in str(g_str).split(","):
                clean_g = g.strip().lower()
                if clean_g:
                    genre_counter[clean_g] += 1
    genres = [{"genre": g.title(), "plays": count} for g, count in genre_counter.most_common(8)]

    heatmap = [[0]*24 for _ in range(7)]
    for _, r in df.iterrows():
        d_idx = (int(r["dow"]) + 5) % 7
        h_idx = int(r["hour"])
        if 0 <= d_idx < 7 and 0 <= h_idx < 24:
            heatmap[d_idx][h_idx] += 1

    payload = {
        "kpis": {
            "total_tracks": total_tracks,
            "total_albums": total_albums,
            "total_artists": total_artists,
            "listening_time": listening_time,
            "top_album": top_album
        },
        "time_series": time_series,
        "discovery_vs_repeat": {
            "fresh_albums": fresh_albums,
            "repeat_albums": repeat_albums,
            "fresh_plays": fresh_plays,
            "repeat_plays": repeat_plays,
            "fresh_pct": fresh_pct,
            "repeat_pct": repeat_pct
        },
        "top_albums": top_albums,
        "top_artists": top_artists,
        "top_tracks": top_tracks,
        "eras": eras,
        "genres": genres,
        "heatmap": heatmap
    }

    def sanitize_payload(obj):
        if isinstance(obj, dict):
            return {k: sanitize_payload(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_payload(v) for v in obj]
        elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return 0.0
        return obj

    payload = sanitize_payload(payload)
    save_analytics_to_datastore(user_id, cache_key, payload)
    _user_analytics_cache[cache_key] = payload
    _user_analytics_cache_time[cache_key] = now
    return payload
