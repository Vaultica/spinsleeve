"""
SpinSleeve V2 Catalog & Crate Service (`services/catalog.py`)
-------------------------------------------------------------
Manages user album catalog fetching, unowned crate discovery ("You Should Save These"),
landing showcase albums, and initial user synchronization on first login.
"""
import time
import datetime
import logging
from collections import Counter
import pandas as pd
import spotipy
from google.cloud import bigquery

from app_config import PROJECT_ID, DATASET_V2, PLAYBACK_HISTORY_TABLE, logger
from services.datastore import get_datastore_client, get_catalog_from_datastore, save_catalog_to_datastore
from services.bigquery import safe_int, safe_float, safe_str

_user_album_cache = {}
_user_album_cache_time = {}
CATALOG_IN_MEMORY_TTL = 300  # 5 minutes


def fetch_landing_showcase_albums():
    """Fetches public showcase albums for the landing page hero grid."""
    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        query = f"""
        SELECT album_id, album_name, album_artist_name, album_image_url, release_year
        FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
        WHERE album_image_url IS NOT NULL AND album_image_url != ''
        GROUP BY album_id, album_name, album_artist_name, album_image_url, release_year
        ORDER BY RAND()
        LIMIT 12
        """
        df = bq_client.query(query).to_dataframe()
        albums = []
        for _, row in df.iterrows():
            albums.append({
                "album_id": safe_str(row.get("album_id")),
                "album_name": safe_str(row.get("album_name")),
                "artist_name": safe_str(row.get("album_artist_name")),
                "image": safe_str(row.get("album_image_url")),
                "year": safe_str(row.get("release_year"))
            })
        return albums
    except Exception as e:
        logger.warning("Could not fetch showcase albums: %s", e)
        return []


def sync_user_initial_data(user_id, access_token):
    """Syncs the initial 50 saved albums and 50 tracks for an approved user on first login."""
    try:
        sp = spotipy.Spotify(auth=access_token)
        bq_client = bigquery.Client(project=PROJECT_ID)

        saved_albums = sp.current_user_saved_albums(limit=50)
        rows_to_insert = []
        for item in saved_albums.get("items", []):
            album = item.get("album", {})
            if not album:
                continue
            images = album.get("images", [])
            image_url = images[0].get("url") if images else ""
            artists = album.get("artists", [])
            artist_name = artists[0]["name"] if artists else "Unknown Artist"
            artist_id = artists[0]["id"] if artists else ""
            rel_date = album.get("release_date", "")
            rel_year = rel_date[:4] if rel_date else ""

            rows_to_insert.append({
                "user_id": user_id,
                "album_id": album.get("id", ""),
                "album_name": album.get("name", "Unknown Album"),
                "artist_id": artist_id,
                "artist_name": artist_name,
                "added_at": item.get("added_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                "release_date": rel_date,
                "release_year": rel_year,
                "tracks_total": album.get("total_tracks", 0),
                "album_type": album.get("album_type", "album"),
                "label": album.get("label", ""),
                "image_url": image_url,
                "genres": ""
            })

        if rows_to_insert:
            table_ref = f"{PROJECT_ID}.{DATASET_V2}.user_saved_albums"
            errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
            if errors:
                logger.error("Error inserting initial saved albums for %s: %s", user_id, errors)
            else:
                logger.info("Successfully synced %d initial saved albums for %s", len(rows_to_insert), user_id)
    except Exception as e:
        logger.error("Error in sync_user_initial_data for %s: %s", user_id, e)


def fetch_user_album_data(user_id, force_refresh=False):
    """Fetches user album catalog from Datastore cache or BigQuery (INFRA-03a/03b)."""
    now = time.time()
    if not force_refresh:
        if user_id in _user_album_cache and (now - _user_album_cache_time.get(user_id, 0) < CATALOG_IN_MEMORY_TTL):
            return _user_album_cache[user_id]

        ds_cached = get_catalog_from_datastore(user_id)
        if ds_cached:
            cached_albums = ds_cached.get("albums", [])
            for a in cached_albums:
                if "album_image_url" not in a and "image" in a:
                    a["album_image_url"] = a["image"]
                elif "image" not in a and "album_image_url" in a:
                    a["image"] = a["album_image_url"]

                if "album_artist_name" not in a and "artist_name" in a:
                    a["album_artist_name"] = a["artist_name"]
                elif "artist_name" not in a and "album_artist_name" in a:
                    a["artist_name"] = a["album_artist_name"]

                if "album_genres" not in a and "genres" in a:
                    a["album_genres"] = a["genres"]
                elif "genres" not in a and "album_genres" in a:
                    a["genres"] = a["album_genres"]

                if "album_track_plays" not in a and "total_plays" in a:
                    a["album_track_plays"] = a["total_plays"]
                elif "total_plays" not in a and "album_track_plays" in a:
                    a["total_plays"] = a["album_track_plays"]

                if "album_description" not in a and "summary" in a:
                    a["album_description"] = a["summary"]
                elif "summary" not in a and "album_description" in a:
                    a["summary"] = a["album_description"]

            if "kpis" not in ds_cached:
                tot_alb = len(cached_albums)
                p_alb = sum(1 for a in cached_albums if a.get("total_plays", 0) > 0 or a.get("album_track_plays", 0) > 0)
                p_alb_30d = sum(1 for a in cached_albums if a.get("play_count_30d", 0) > 0 or a.get("album_track_plays_30d", 0) > 0)
                unp_alb = tot_alb - p_alb
                tot_plays = sum(a.get("total_plays", 0) or a.get("album_track_plays", 0) for a in cached_albums)
                tot_plays_30d = sum(a.get("play_count_30d", 0) or a.get("album_track_plays_30d", 0) for a in cached_albums)
                pct_exp = round((p_alb / tot_alb * 100), 1) if tot_alb > 0 else 0.0
                top_a = max(cached_albums, key=lambda x: x.get("total_plays", 0) or x.get("album_track_plays", 0)) if cached_albums else None
                ds_cached["kpis"] = {
                    "total_albums": tot_alb,
                    "played_albums": p_alb,
                    "played_albums_30d": p_alb_30d,
                    "unplayed_albums": unp_alb,
                    "pct_explored": pct_exp,
                    "total_plays": tot_plays,
                    "total_plays_30d": tot_plays_30d,
                    "top_album": top_a["album_name"] if top_a and (top_a.get("total_plays", 0) > 0 or top_a.get("album_track_plays", 0) > 0) else None,
                    "top_album_plays": top_a.get("total_plays", 0) or top_a.get("album_track_plays", 0) if top_a else 0
                }
            _user_album_cache[user_id] = ds_cached
            _user_album_cache_time[user_id] = now
            return ds_cached

    try:
        bq_client = bigquery.Client(project=PROJECT_ID)
        query = f"""
        SELECT 
            album_id, album_name, album_artist_name, album_image_url, release_year, 
            album_genres, album_track_plays, album_plays, album_track_plays_30d, album_plays_30d,
            album_tracks_total, album_description, personnel, pitchfork_score, discogs_rating, enriched_styles
        FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table`
        WHERE user_id = @user_id
        ORDER BY album_plays_30d DESC, album_plays DESC
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        df = bq_client.query(query, job_config=job_config).to_dataframe()

        albums = []
        genre_counter = Counter()

        for _, row in df.iterrows():
            genres_str = safe_str(row.get("album_genres"), "")
            if genres_str:
                for g in genres_str.split(","):
                    g_clean = g.strip().title()
                    if g_clean:
                        genre_counter[g_clean] += 1

            aid = safe_str(row.get("album_id"))
            aname = safe_str(row.get("album_name"), "Unknown Album")
            arname = safe_str(row.get("album_artist_name"), "Unknown Artist")
            img_url = safe_str(row.get("album_image_url"))
            r_year = safe_str(row.get("release_year"), "2024")
            tr_plays = safe_int(row.get("album_track_plays"), 0)
            alb_plays = safe_float(row.get("album_plays"), 0.0)
            tr_plays_30d = safe_int(row.get("album_track_plays_30d"), 0)
            alb_plays_30d = safe_float(row.get("album_plays_30d"), 0.0)
            tr_total = safe_int(row.get("album_tracks_total"), 0)
            desc = safe_str(row.get("album_description"))
            pers = safe_str(row.get("personnel"))
            pf = safe_str(row.get("pitchfork_score"))
            disc_rat = safe_float(row.get("discogs_rating"), 0.0)
            styles_str = safe_str(row.get("enriched_styles"))
            has_gf = bool(desc or pers)

            albums.append({
                "album_id": aid,
                "album_name": aname,
                "album_artist_name": arname,
                "album_image_url": img_url,
                "release_year": r_year,
                "album_genres": genres_str,
                "album_track_plays": tr_plays,
                "album_plays": alb_plays,
                "album_track_plays_30d": tr_plays_30d,
                "album_plays_30d": alb_plays_30d,
                "album_tracks_total": tr_total,
                "album_description": desc,
                "personnel": pers,
                "pitchfork_score": pf,
                "discogs_rating": disc_rat,
                "enriched_styles": styles_str,
                "album_url": f"https://open.spotify.com/album/{aid}" if aid else "",
                "has_gatefold": has_gf,
                "image": img_url,
                "artist_name": arname,
                "year": r_year,
                "genres": genres_str,
                "total_plays": tr_plays,
                "play_count_30d": tr_plays_30d,
                "normalized_play_score": alb_plays,
                "summary": desc,
                "pitchfork": pf,
                "discogs": disc_rat,
                "styles_tag": styles_str,
                "preview_url": ""
            })

        total_albums = len(albums)
        played_albums = sum(1 for a in albums if a["total_plays"] > 0)
        played_albums_30d = sum(1 for a in albums if a["play_count_30d"] > 0)
        unplayed_albums = total_albums - played_albums
        total_plays = sum(a["total_plays"] for a in albums)
        total_plays_30d = sum(a["play_count_30d"] for a in albums)
        pct_explored = round((played_albums / total_albums * 100), 1) if total_albums > 0 else 0.0

        top_album = max(albums, key=lambda x: x["total_plays"]) if albums else None
        top_album_name = top_album["album_name"] if top_album and top_album["total_plays"] > 0 else None
        top_album_plays = top_album["total_plays"] if top_album and top_album["total_plays"] > 0 else 0

        kpis = {
            "total_albums": total_albums,
            "played_albums": played_albums,
            "played_albums_30d": played_albums_30d,
            "unplayed_albums": unplayed_albums,
            "pct_explored": pct_explored,
            "total_plays": total_plays,
            "total_plays_30d": total_plays_30d,
            "top_album": top_album_name,
            "top_album_plays": top_album_plays
        }

        top_genres = [g for g, count in genre_counter.most_common(10)]
        payload = {"albums": albums, "top_genres": top_genres, "kpis": kpis}

        save_catalog_to_datastore(user_id, payload)
        _user_album_cache[user_id] = payload
        _user_album_cache_time[user_id] = now
        return payload

    except Exception as e:
        logger.error("[%s] Error fetching user album data: %s", user_id, e, exc_info=True)
        return {"albums": [], "top_genres": []}


def fetch_unowned_album_data(user_id, horizon="all"):
    """Fetches streamed albums not in saved library, filtered by time horizon (APP-07)."""
    try:
        client = bigquery.Client(project=PROJECT_ID)

        horizon_clause = ""
        if horizon == "30d":
            horizon_clause = "AND p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)"
        elif horizon == "90d":
            horizon_clause = "AND p.played_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)"

        query = f"""
        SELECT 
          p.album_name,
          p.artist_name,
          MAX(p.album_id) as album_id,
          COUNT(1) as play_count,
          COUNT(DISTINCT p.track_name) as distinct_tracks,
          MAX(p.played_at) as last_played_at
        FROM `{PLAYBACK_HISTORY_TABLE}` p
        WHERE p.user_id = @user_id
          AND CONCAT(LOWER(TRIM(p.album_name)), '::', LOWER(TRIM(p.artist_name))) NOT IN (
            SELECT CONCAT(LOWER(TRIM(album_name)), '::', LOWER(TRIM(artist_name)))
            FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
            WHERE user_id = @user_id
          )
          {horizon_clause}
        GROUP BY p.album_name, p.artist_name
        HAVING distinct_tracks >= 2
        ORDER BY play_count DESC
        LIMIT 25
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("user_id", "STRING", user_id)]
        )
        df = client.query(query, job_config=job_config).to_dataframe()

        unowned = []
        for _, row in df.iterrows():
            aid = safe_str(row.get("album_id"))
            if not aid or aid == "None":
                aid = ""
            unowned.append({
                "album_id": aid,
                "album_name": safe_str(row.get("album_name")),
                "album_artist_name": safe_str(row.get("artist_name")),
                "play_count": safe_int(row.get("play_count")),
                "distinct_tracks": safe_int(row.get("distinct_tracks")),
                "last_played_at": str(row.get("last_played_at", "")),
                "album_image_url": "/avatar/miles.svg",
                "album_url": f"https://open.spotify.com/album/{aid}" if aid else ""
            })

        # Enrich artwork from Spotify
        try:
            from services.spotify import get_token_for_user
            token_info = get_token_for_user(user_id, None)
            sp = None
            if token_info and token_info.get("access_token"):
                sp = spotipy.Spotify(auth=token_info.get("access_token"), requests_timeout=10)
            else:
                from spotipy.oauth2 import SpotifyClientCredentials
                client_credentials_manager = SpotifyClientCredentials()
                sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager, requests_timeout=10)

            if sp:
                valid_aids = [row["album_id"] for row in unowned if row["album_id"] and row["album_id"] != "None"]
                if valid_aids:
                    for i in range(0, len(valid_aids), 20):
                        chunk = valid_aids[i:i+20]
                        res = sp.albums(chunk)
                        for album_obj in res.get("albums", []):
                            if album_obj and album_obj.get("id"):
                                aid = album_obj["id"]
                                images = album_obj.get("images", [])
                                img_url = images[0].get("url") if images else ""
                                if img_url:
                                    for item in unowned:
                                        if item["album_id"] == aid:
                                            item["album_image_url"] = img_url

                for item in unowned:
                    if not item["album_image_url"] or item["album_image_url"] == "/avatar/miles.svg":
                        try:
                            search_res = sp.search(q=f"album:{item['album_name']} artist:{item['album_artist_name']}", type="album", limit=1)
                            items = search_res.get("albums", {}).get("items", [])
                            if items:
                                alb = items[0]
                                if not item["album_id"] or item["album_id"] == "None":
                                    item["album_id"] = alb.get("id", "")
                                    item["album_url"] = f"https://open.spotify.com/album/{item['album_id']}"
                                images = alb.get("images", [])
                                if images:
                                    item["album_image_url"] = images[0].get("url", "")
                        except Exception as ex:
                            logger.debug("Could not search Spotify for unowned album %s: %s", item["album_name"], ex)
        except Exception as e:
            logger.debug("Could not enrich unowned album artwork from Spotify: %s", e)

        return unowned
    except Exception as e:
        logger.error("Error fetching unowned albums for %s: %s", user_id, e)
        return []


def compute_normalized_album_plays(track_plays, tracks_total, is_30d=False):
    """
    Computes normalized complete album spins, display badge string, and hover tooltip (APP-05 & APP-06).
    """
    try:
        tp = float(track_plays) if track_plays is not None else 0.0
        tt = int(tracks_total) if tracks_total is not None and int(tracks_total) > 0 else 0
    except (ValueError, TypeError):
        tp = 0.0
        tt = 0

    period_label = "in last 30 days " if is_30d else ""
    badge_suffix = " (30D)" if is_30d else ""

    if tp <= 0:
        return 0.0, "💤 Never Played", f"Never played (0 plays){' in last 30 days' if is_30d else ''}"

    if tt > 0:
        norm_plays = round(tp / tt, 1)
        if norm_plays.is_integer():
            norm_plays = int(norm_plays)
        tooltip = f"Estimated complete album spins {period_label}based on {int(tp) if tp.is_integer() else tp} track plays across {tt} tracks".strip()
    else:
        norm_plays = int(tp) if tp.is_integer() else tp
        period_name = "30-day track plays" if is_30d else "Total track plays"
        tooltip = f"{period_name}: {int(tp) if tp.is_integer() else tp} (track count unavailable)"

    if norm_plays == 1:
        display_badge = f"🔥 1 Play{badge_suffix}"
    else:
        display_badge = f"🔥 {norm_plays} Plays{badge_suffix}"

    return norm_plays, display_badge, tooltip
