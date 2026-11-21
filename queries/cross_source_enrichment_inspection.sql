-- SpinSleeve V2: Cross-Source Album Metadata Enrichment Inspection Query
-- Filters for albums with enrichment_quality_score > 0.5 across all sources
-- (Wikipedia, Discogs, MusicBrainz, and Synthesized Golden Record).

SELECT 
  -- Golden Record / Synthesized Attributes
  e.canonical_album_key,
  e.artist_name,
  e.album_name,
  e.release_date,
  e.release_year,
  e.era_group,
  e.genres,
  e.styles,
  e.macro_genre,
  e.derived_moods,
  e.descriptive_tags,
  e.enrichment_quality_score,
  
  -- Tier 1: Wikipedia Source (`enrichment_raw_wikipedia`)
  w.wiki_summary,
  w.wiki_url,
  w.pitchfork_score,
  w.metacritic_score,
  w.allmusic_score,
  w.guardian_score,
  w.fetched_at AS wiki_fetched_at,
  
  -- Tier 1: Discogs Source (`enrichment_raw_discogs`)
  d.discogs_release_id,
  d.personnel,
  d.discogs_rating,
  d.discogs_votes,
  d.discogs_styles,
  d.discogs_notes,
  d.discogs_url,
  d.fetched_at AS discogs_fetched_at,
  
  -- Tier 1: MusicBrainz Source (`enrichment_raw_musicbrainz`)
  mb.mb_release_group_id,
  mb.genres AS mb_genres,
  mb.tags AS mb_tags,
  mb.fetched_at AS mb_fetched_at

FROM `secret-compass-181513.spotify_v2.album_enriched_metadata` e
LEFT JOIN (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY canonical_album_key ORDER BY fetched_at DESC) as rn
  FROM `secret-compass-181513.spotify_v2.enrichment_raw_wikipedia`
) w ON e.canonical_album_key = w.canonical_album_key AND w.rn = 1
LEFT JOIN (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY canonical_album_key ORDER BY fetched_at DESC) as rn
  FROM `secret-compass-181513.spotify_v2.enrichment_raw_discogs`
) d ON e.canonical_album_key = d.canonical_album_key AND d.rn = 1
LEFT JOIN (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY canonical_album_key ORDER BY fetched_at DESC) as rn
  FROM `secret-compass-181513.spotify_v2.enrichment_raw_musicbrainz`
) mb ON e.canonical_album_key = mb.canonical_album_key AND mb.rn = 1

WHERE e.enrichment_quality_score > 0.5
ORDER BY e.enrichment_quality_score DESC, e.artist_name, e.album_name;
