-- SpinSleeve V2: Enrichment Progress & Coverage Assessment Query
-- Calculates unique library coverage, MusicBrainz match rate, percentage enriched,
-- high-quality count (score >= 0.85), and average enrichment quality score.

WITH total_library AS (
  SELECT DISTINCT 
    COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name)))) as canonical_album_key
  FROM `secret-compass-181513.spotify_v2.user_saved_albums`
  WHERE album_name IS NOT NULL AND artist_name IS NOT NULL
),
enriched_status AS (
  SELECT 
    t.canonical_album_key,
    (e.canonical_album_key IS NOT NULL) as is_enriched,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    (mb.canonical_album_key IS NOT NULL) as has_musicbrainz
  FROM total_library t
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON t.canonical_album_key = e.canonical_album_key
  LEFT JOIN (
    SELECT DISTINCT canonical_album_key 
    FROM `secret-compass-181513.spotify_v2.enrichment_raw_musicbrainz`
    WHERE canonical_album_key IS NOT NULL
  ) mb ON t.canonical_album_key = mb.canonical_album_key
)
SELECT 
  COUNT(*) AS total_unique_albums_in_library,
  SUM(CASE WHEN is_enriched THEN 1 ELSE 0 END) AS enriched_albums_count,
  ROUND(SUM(CASE WHEN is_enriched THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_enriched,
  SUM(CASE WHEN has_musicbrainz THEN 1 ELSE 0 END) AS musicbrainz_matched_count,
  ROUND(SUM(CASE WHEN has_musicbrainz THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_musicbrainz,
  SUM(CASE WHEN quality_score >= 0.85 THEN 1 ELSE 0 END) AS high_quality_count,
  ROUND(SUM(CASE WHEN quality_score >= 0.85 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS pct_high_quality,
  ROUND(AVG(quality_score), 2) AS average_quality_score
FROM enriched_status;
