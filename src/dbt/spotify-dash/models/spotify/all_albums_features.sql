{{ config(materialized='view') }}

with raw_albums as (

  select
    *,
    row_number() over (
      partition by lower(trim(album_artists_0_name)), lower(trim(album_name))
      order by
        -- 1. Prefer releases that have valid cover image URLs
        case when album_image_url is not null and album_image_url != '' then 1 else 2 end asc,
        -- 2. Prefer the most recently added / active release in your library
        added_at desc
    ) as dedupe_rank
  from {{ source('spotify', 'all_albums') }}
  -- Filter out 1-2 track releases (singles and teaser tracks)
  where coalesce(album_tracks_total, 0) > 2

),

deduped_albums as (

  select *
  from raw_albums
  where dedupe_rank = 1

),

joined as (

  select
     albums.added_at,
     albums.album_artists_0_name                               as album_artist_name,
     albums.album_name,
     albums.album_type,
     albums.album_label,
     albums.album_release_date,
     albums.album_tracks_total,
     albums.album_image_url,
     albums.album_genres,
     coalesce(play.no_albums, 0)                               as album_track_plays,
     round(coalesce(play.no_albums, 0) / nullif(albums.album_tracks_total, 0), 1) as album_plays,
     concat('https://open.spotify.com/album/', albums.album_id) as album_url
  from deduped_albums albums
  left join {{ ref('spotify', 'most_played_albums') }} play
       on play.album_name = albums.album_name

)

select
     *
from joined
