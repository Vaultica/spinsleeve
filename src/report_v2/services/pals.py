"""
SpinSleeve V2 SpinPals Service (`services/pals.py`)
--------------------------------------------------
Manages SpinPals member directory fetching and acoustic chemistry / compatibility calculations.
"""
import json
import logging
from google.cloud import bigquery, datastore

from app_config import PROJECT_ID, DATASET_V2, logger
from services.datastore import get_datastore_client
from services.bigquery import safe_str, safe_int, safe_float


def fetch_pals_directory(current_user_id):
    """Fetches all approved community members in the Listening Lounge."""
    ds_client = get_datastore_client()
    query = ds_client.query(kind="User")
    query.add_filter(filter=datastore.query.PropertyFilter("is_approved", "=", True))
    users = list(query.fetch())

    bq_client = bigquery.Client(project=PROJECT_ID)
    q_counts = f"""
    SELECT user_id, COUNT(*) as album_count
    FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
    GROUP BY user_id
    """
    df_counts = bq_client.query(q_counts).to_dataframe()
    counts_map = dict(zip(df_counts["user_id"], df_counts["album_count"]))

    pals = []
    for u in users:
        uid = u.key.name or u.get("spotify_id")
        if uid == "vaultica":  # Skip system alias
            continue
        pals.append({
            "spotify_id": uid,
            "display_name": u.get("display_name") or uid,
            "avatar_url": u.get("avatar_url") or "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150",
            "album_count": int(counts_map.get(uid, 0)),
            "is_self": (uid == current_user_id)
        })

    pals.sort(key=lambda p: (not p["is_self"], p["display_name"].lower()))
    return pals


def compute_pal_compatibility(current_user_id, pal_id, horizon="30d"):
    """Computes acoustic chemistry, shared vinyl, and top 5 borrow recommendations."""
    bq_client = bigquery.Client(project=PROJECT_ID)
    ds_client = get_datastore_client()

    pal_key = ds_client.key("User", pal_id)
    pal_entity = ds_client.get(pal_key)
    pal_name = pal_entity.get("display_name") if pal_entity else pal_id
    pal_avatar = pal_entity.get("avatar_url") if pal_entity else ""
    if not pal_avatar:
        pal_avatar = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"

    plays_col = "album_track_plays_30d" if horizon == "30d" else "album_track_plays"
    total_col = "album_plays_30d" if horizon == "30d" else "album_plays"

    q_pal_albums = f"""
    SELECT 
      f.album_id,
      f.album_name,
      f.album_artist_name,
      f.album_image_url,
      f.release_year,
      f.album_genres,
      f.{plays_col} as album_track_plays,
      f.{total_col} as album_plays,
      f.pitchfork_score,
      f.metacritic_score,
      f.discogs_rating,
      f.discogs_votes,
      f.album_description,
      f.personnel,
      f.wikipedia_url,
      f.discogs_url,
      f.enriched_styles,
      CASE WHEN my.album_id IS NOT NULL THEN 1 ELSE 0 END as current_user_owns
    FROM `{PROJECT_ID}.{DATASET_V2}.user_albums_features_table` f
    LEFT JOIN `{PROJECT_ID}.{DATASET_V2}.user_saved_albums` my
      ON my.user_id = @current_user_id AND f.album_id = my.album_id
    WHERE f.user_id = @pal_id
    ORDER BY f.{total_col} DESC, f.added_at DESC
    """
    job_cfg = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("current_user_id", "STRING", current_user_id),
            bigquery.ScalarQueryParameter("pal_id", "STRING", pal_id)
        ]
    )
    df_pal = bq_client.query(q_pal_albums, job_config=job_cfg).to_dataframe()

    q_my_albums = f"""
    SELECT album_id, album_name, artist_name
    FROM `{PROJECT_ID}.{DATASET_V2}.user_saved_albums`
    WHERE user_id = @current_user_id
    """
    my_cfg = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("current_user_id", "STRING", current_user_id)]
    )
    df_my = bq_client.query(q_my_albums, job_config=my_cfg).to_dataframe()
    my_album_ids = set(df_my["album_id"].tolist())
    my_total_albums = len(my_album_ids)

    processed_pal_albums = []
    shared_albums = []
    for _, row in df_pal.iterrows():
        raw_personnel = row.get("personnel")
        personnel_list = []
        if isinstance(raw_personnel, list):
            personnel_list = raw_personnel
        elif isinstance(raw_personnel, str) and raw_personnel.strip():
            try:
                personnel_list = json.loads(raw_personnel)
            except Exception:
                personnel_list = [p.strip() for p in raw_personnel.split(",") if p.strip()]

        album_item = {
            "album_id": safe_str(row.get("album_id")),
            "album_name": safe_str(row.get("album_name")),
            "album_artist_name": safe_str(row.get("album_artist_name")),
            "album_image_url": safe_str(row.get("album_image_url")),
            "release_year": safe_str(row.get("release_year")),
            "album_genres": safe_str(row.get("album_genres")),
            "album_track_plays": safe_int(row.get("album_track_plays")),
            "album_plays": safe_int(row.get("album_plays")),
            "pitchfork_score": safe_str(row.get("pitchfork_score")),
            "metacritic_score": safe_str(row.get("metacritic_score")),
            "discogs_rating": safe_float(row.get("discogs_rating")),
            "discogs_votes": safe_int(row.get("discogs_votes")),
            "album_description": safe_str(row.get("album_description")),
            "personnel": personnel_list,
            "wikipedia_url": safe_str(row.get("wikipedia_url")),
            "discogs_url": safe_str(row.get("discogs_url")),
            "album_url": f"https://open.spotify.com/album/{safe_str(row.get('album_id'))}",
            "has_gatefold": bool(safe_str(row.get("album_description"))),
            "current_user_owns": int(row.get("current_user_owns", 0)) == 1
        }
        processed_pal_albums.append(album_item)
        if album_item["current_user_owns"] or album_item["album_id"] in my_album_ids:
            shared_albums.append(album_item)

    pal_total_albums = len(df_pal)
    overlap_count = len(shared_albums)
    denominator = max(1, min(my_total_albums, pal_total_albums))
    match_pct = min(100, int((overlap_count / denominator) * 100)) if denominator > 0 else 0

    my_artists = set(df_my["artist_name"].str.lower().str.strip() if not df_my.empty else [])
    pal_artists = set(df_pal["album_artist_name"].str.lower().str.strip() if not df_pal.empty else [])
    shared_artists_list = sorted(list(my_artists.intersection(pal_artists)))

    if match_pct >= 40 or overlap_count >= 15:
        kinship = {"badge": "Vinyl Soulmates", "color": "bg-emerald-500/20 text-emerald-300 border-emerald-500/30", "desc": f"Incredible acoustic overlap! You both share {overlap_count} albums and enjoy identical master pressings."}
    elif match_pct >= 20 or overlap_count >= 8:
        kinship = {"badge": "Acoustic Kin", "color": "bg-blue-500/20 text-blue-300 border-blue-500/30", "desc": f"Strong sonic resonance. You share {overlap_count} records and several mutual artist obsessions."}
    else:
        kinship = {"badge": "Crate Companions", "color": "bg-purple-500/20 text-purple-300 border-purple-500/30", "desc": f"Complementary tastes! Exploring {pal_name}'s crate is a great way to discover unowned gems."}

    unowned_by_me = [a for a in processed_pal_albums if not a["current_user_owns"] and a["album_id"] not in my_album_ids]
    unowned_by_me.sort(key=lambda x: x["album_plays"], reverse=True)
    top_borrow = unowned_by_me[:5]
    for b in top_borrow:
        b["borrow_reason"] = f"Frequent Rotation ({b['album_plays']} plays)"

    return {
        "pal": {"spotify_id": pal_id, "display_name": pal_name, "avatar_url": pal_avatar, "album_count": pal_total_albums},
        "compatibility": {
            "match_pct": match_pct,
            "shared_albums_count": overlap_count,
            "shared_artists_count": len(shared_artists_list),
            "borrow_count": len(unowned_by_me),
            "shared_artists": [art.title() for art in shared_artists_list[:8]],
            "kinship": kinship
        },
        "top_borrow": top_borrow,
        "shared_albums": shared_albums,
        "pal_full_crate": processed_pal_albums,
        "borrow_recommendations": [{"album_id": b["album_id"], "album_name": b["album_name"], "artist_name": b["album_artist_name"]} for b in top_borrow]
    }
