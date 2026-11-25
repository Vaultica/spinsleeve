-- =====================================================================================
-- SpinSleeve V2: Multi-Level Metadata Enrichment & Gatefold Quality Analytics
-- File: queries/enrichment_distribution_and_gaps.sql
-- Dataset: secret-compass-181513.spotify_v2
--
-- PURPOSE:
-- Replaces naive row-existence metrics (e.canonical_album_key IS NOT NULL) with
-- comprehensive, multi-dimensional quality diagnostics. Analyzes enrichment depth,
-- percentiles (p10, p25, median p50, p75, p90), and structural attribute gaps
-- across five hierarchical analytical dimensions:
--
--   * LEVEL 1: Portfolio-Wide Enrichment Overview & Score Quantiles
--   * LEVEL 2: Multi-Tenant / Per-User Library Readiness & Gatefold Coverage
--   * LEVEL 3: Macro-Genre Distribution, Score Spread & Attribute Pillars
--   * LEVEL 4A: Chronological Distribution by Era & Decade
--   * LEVEL 4B: Recent Years Chronological Breakdown (2015 - Present)
--   * LEVEL 5: Actionable High-Impact Queue (Top-Played Missing Gatefolds)
-- =====================================================================================


-- -------------------------------------------------------------------------------------
-- LEVEL 1: Portfolio-Wide Enrichment Overview & Score Quantiles
-- -------------------------------------------------------------------------------------
-- Evaluates the global catalog across row existence vs actual metadata fidelity.
-- A quality score of 0.0 indicates an empty placeholder stub that needs re-enrichment.

WITH library_albums AS (
  SELECT 
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key,
    ANY_VALUE(s.artist_name) as artist_name,
    ANY_VALUE(s.album_name) as album_name
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY canonical_album_key
),
joined AS (
  SELECT 
    l.canonical_album_key,
    (e.canonical_album_key IS NOT NULL) as row_exists,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold,
    (e.album_description IS NOT NULL AND e.album_description != '') as has_summary,
    (e.personnel IS NOT NULL AND e.personnel != '') as has_personnel,
    ((e.pitchfork_score IS NOT NULL AND e.pitchfork_score != '') OR (e.metacritic_score IS NOT NULL AND e.metacritic_score != '') OR (e.allmusic_score IS NOT NULL AND e.allmusic_score != '') OR (e.guardian_score IS NOT NULL AND e.guardian_score != '')) as has_reviews,
    (e.discogs_rating IS NOT NULL AND NOT IS_NAN(e.discogs_rating) AND e.discogs_rating > 0) as has_rating,
    (mb.canonical_album_key IS NOT NULL) as has_musicbrainz
  FROM library_albums l
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON l.canonical_album_key = e.canonical_album_key
  LEFT JOIN (
    SELECT DISTINCT canonical_album_key 
    FROM `secret-compass-181513.spotify_v2.enrichment_raw_musicbrainz`
    WHERE canonical_album_key IS NOT NULL
  ) mb ON l.canonical_album_key = mb.canonical_album_key
)
SELECT 
  COUNT(*) as total_unique_albums,
  ROUND(COUNTIF(row_exists) * 100.0 / COUNT(*), 1) as pct_table_row_exists,
  ROUND(COUNTIF(quality_score > 0.0) * 100.0 / COUNT(*), 1) as pct_meaningful_enrichment,
  ROUND(COUNTIF(has_gatefold) * 100.0 / COUNT(*), 1) as pct_gatefold_ready,
  COUNTIF(NOT has_gatefold) as total_missing_gatefolds,
  ROUND(COUNTIF(quality_score >= 0.60) * 100.0 / COUNT(*), 1) as pct_solid_quality,
  ROUND(COUNTIF(quality_score >= 0.85) * 100.0 / COUNT(*), 1) as pct_high_quality,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(10)], 2) as p10,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(25)], 2) as p25,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(50)], 2) as p50_median,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(75)], 2) as p75,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(90)], 2) as p90,
  ROUND(COUNTIF(has_summary) * 100.0 / COUNT(*), 1) as pct_with_summary,
  ROUND(COUNTIF(has_personnel) * 100.0 / COUNT(*), 1) as pct_with_personnel,
  ROUND(COUNTIF(has_reviews) * 100.0 / COUNT(*), 1) as pct_with_reviews,
  ROUND(COUNTIF(has_rating) * 100.0 / COUNT(*), 1) as pct_with_rating,
  ROUND(COUNTIF(has_musicbrainz) * 100.0 / COUNT(*), 1) as pct_with_musicbrainz
FROM joined;


-- -------------------------------------------------------------------------------------
-- LEVEL 2: Multi-Tenant / Per-User Library Readiness & Gatefold Coverage
-- -------------------------------------------------------------------------------------
-- Measures enrichment progress per tenant library, comparing album coverage and
-- gatefold readiness against individual listening activity (scrobble volume).

WITH user_library AS (
  SELECT 
    s.user_id,
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY s.user_id, canonical_album_key
),
user_plays AS (
  SELECT 
    p.user_id,
    COUNT(*) as total_scrobbles
  FROM `secret-compass-181513.spotify_v2.playback_history` p
  GROUP BY p.user_id
),
user_joined AS (
  SELECT 
    u.user_id,
    u.canonical_album_key,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold,
    COALESCE(e.enrichment_quality_score, 0.0) >= 0.60 as is_solid
  FROM user_library u
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON u.canonical_album_key = e.canonical_album_key
)
SELECT 
  j.user_id,
  COUNT(*) as saved_albums_count,
  COALESCE(p.total_scrobbles, 0) as lifetime_scrobbles,
  COUNTIF(j.has_gatefold) as gatefold_ready_count,
  ROUND(COUNTIF(j.has_gatefold) * 100.0 / COUNT(*), 1) as gatefold_coverage_pct,
  COUNTIF(NOT j.has_gatefold) as missing_gatefolds_count,
  ROUND(COUNTIF(j.is_solid) * 100.0 / COUNT(*), 1) as solid_quality_pct,
  ROUND(AVG(j.quality_score), 2) as avg_quality_score,
  ROUND(APPROX_QUANTILES(j.quality_score, 100)[OFFSET(50)], 2) as p50_median_score
FROM user_joined j
LEFT JOIN user_plays p ON j.user_id = p.user_id
GROUP BY j.user_id, p.total_scrobbles
ORDER BY saved_albums_count DESC;


-- -------------------------------------------------------------------------------------
-- LEVEL 3: Macro-Genre Distribution, Score Spread & Attribute Pillars
-- -------------------------------------------------------------------------------------
-- Highlights taxonomy-level coverage gaps. Inspects the 4 scoring pillars to pinpoint
-- whether low scores stem from missing summaries, credits, reviews, or community ratings.

WITH unique_albums AS (
  SELECT 
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY canonical_album_key
),
joined AS (
  SELECT 
    u.canonical_album_key,
    COALESCE(NULLIF(e.macro_genre, ''), 'Other / Unclassified') as macro_genre,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold,
    (e.album_description IS NOT NULL AND e.album_description != '') as has_summary,
    (e.personnel IS NOT NULL AND e.personnel != '') as has_personnel,
    ((e.pitchfork_score IS NOT NULL AND e.pitchfork_score != '') OR (e.metacritic_score IS NOT NULL AND e.metacritic_score != '') OR (e.allmusic_score IS NOT NULL AND e.allmusic_score != '') OR (e.guardian_score IS NOT NULL AND e.guardian_score != '')) as has_reviews,
    (e.discogs_rating IS NOT NULL AND NOT IS_NAN(e.discogs_rating) AND e.discogs_rating > 0) as has_rating
  FROM unique_albums u
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON u.canonical_album_key = e.canonical_album_key
)
SELECT 
  macro_genre,
  COUNT(*) as album_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as library_share_pct,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(25)], 2) as p25,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(50)], 2) as p50_median,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(75)], 2) as p75,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(90)], 2) as p90,
  ROUND(COUNTIF(has_gatefold) * 100.0 / COUNT(*), 1) as gatefold_coverage_pct,
  COUNTIF(NOT has_gatefold) as missing_gatefolds_count,
  ROUND(COUNTIF(has_summary) * 100.0 / COUNT(*), 1) as pct_with_summary,
  ROUND(COUNTIF(has_personnel) * 100.0 / COUNT(*), 1) as pct_with_personnel,
  ROUND(COUNTIF(has_reviews) * 100.0 / COUNT(*), 1) as pct_with_reviews,
  ROUND(COUNTIF(has_rating) * 100.0 / COUNT(*), 1) as pct_with_rating
FROM joined
GROUP BY macro_genre
ORDER BY album_count DESC;


-- -------------------------------------------------------------------------------------
-- LEVEL 4A: Chronological Distribution by Era & Decade
-- -------------------------------------------------------------------------------------
-- Tracks enrichment quality across release history (vintage catalogs vs modern streaming).

WITH unique_albums AS (
  SELECT 
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key,
    ANY_VALUE(NULLIF(s.release_year, 0)) as release_year
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY canonical_album_key
),
joined AS (
  SELECT 
    u.canonical_album_key,
    u.release_year,
    CASE 
      WHEN u.release_year IS NULL THEN 'Unknown Era'
      WHEN u.release_year < 1970 THEN 'Pre-1970'
      WHEN u.release_year < 1980 THEN '1970s'
      WHEN u.release_year < 1990 THEN '1980s'
      WHEN u.release_year < 2000 THEN '1990s'
      WHEN u.release_year < 2010 THEN '2000s'
      WHEN u.release_year < 2020 THEN '2010s'
      ELSE '2020s'
    END as decade_bucket,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold,
    (e.album_description IS NOT NULL AND e.album_description != '') as has_summary,
    (e.personnel IS NOT NULL AND e.personnel != '') as has_personnel,
    ((e.pitchfork_score IS NOT NULL AND e.pitchfork_score != '') OR (e.metacritic_score IS NOT NULL AND e.metacritic_score != '') OR (e.allmusic_score IS NOT NULL AND e.allmusic_score != '') OR (e.guardian_score IS NOT NULL AND e.guardian_score != '')) as has_reviews
  FROM unique_albums u
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON u.canonical_album_key = e.canonical_album_key
)
SELECT 
  decade_bucket,
  COUNT(*) as album_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as library_share_pct,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(25)], 2) as p25,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(50)], 2) as p50_median,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(75)], 2) as p75,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(90)], 2) as p90,
  ROUND(COUNTIF(has_gatefold) * 100.0 / COUNT(*), 1) as gatefold_coverage_pct,
  COUNTIF(NOT has_gatefold) as missing_gatefolds_count,
  ROUND(COUNTIF(has_summary) * 100.0 / COUNT(*), 1) as pct_with_summary,
  ROUND(COUNTIF(has_personnel) * 100.0 / COUNT(*), 1) as pct_with_personnel,
  ROUND(COUNTIF(has_reviews) * 100.0 / COUNT(*), 1) as pct_with_reviews
FROM joined
GROUP BY decade_bucket
ORDER BY 
  CASE decade_bucket
    WHEN 'Pre-1970' THEN 1
    WHEN '1970s' THEN 2
    WHEN '1980s' THEN 3
    WHEN '1990s' THEN 4
    WHEN '2000s' THEN 5
    WHEN '2010s' THEN 6
    WHEN '2020s' THEN 7
    ELSE 8
  END;


-- -------------------------------------------------------------------------------------
-- LEVEL 4B: Recent Years Chronological Breakdown (2015 - Present)
-- -------------------------------------------------------------------------------------
-- Deep dives into the last 12 release years to expose the recency decay pattern.

WITH unique_albums AS (
  SELECT 
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key,
    ANY_VALUE(NULLIF(s.release_year, 0)) as release_year
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY canonical_album_key
),
joined AS (
  SELECT 
    u.canonical_album_key,
    u.release_year,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold,
    (e.album_description IS NOT NULL AND e.album_description != '') as has_summary,
    (e.personnel IS NOT NULL AND e.personnel != '') as has_personnel
  FROM unique_albums u
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON u.canonical_album_key = e.canonical_album_key
  WHERE u.release_year >= 2015
)
SELECT 
  release_year,
  COUNT(*) as album_count,
  ROUND(AVG(quality_score), 2) as avg_quality_score,
  ROUND(APPROX_QUANTILES(quality_score, 100)[OFFSET(50)], 2) as p50_median,
  ROUND(COUNTIF(has_gatefold) * 100.0 / COUNT(*), 1) as gatefold_coverage_pct,
  COUNTIF(NOT has_gatefold) as missing_gatefolds_count,
  ROUND(COUNTIF(has_summary) * 100.0 / COUNT(*), 1) as pct_with_summary,
  ROUND(COUNTIF(has_personnel) * 100.0 / COUNT(*), 1) as pct_with_personnel
FROM joined
GROUP BY release_year
ORDER BY release_year DESC;


-- -------------------------------------------------------------------------------------
-- LEVEL 5: Actionable High-Impact Queue (Top-Played Missing Gatefolds)
-- -------------------------------------------------------------------------------------
-- Ranks albums currently missing gatefolds by listening plays and collector count.
-- These are the highest-impact targets for:
--   .venv/bin/python3 src/pipeline_v2/enrich.py --missing-gatefolds --batch-size 50

WITH saved AS (
  SELECT 
    COALESCE(NULLIF(s.canonical_album_key, ''), CONCAT(LOWER(TRIM(s.artist_name)), '::', LOWER(TRIM(s.album_name)))) as canonical_album_key,
    ANY_VALUE(s.artist_name) as artist_name,
    ANY_VALUE(s.album_name) as album_name,
    ANY_VALUE(NULLIF(s.release_year, 0)) as release_year,
    COUNT(DISTINCT s.user_id) as collector_count
  FROM `secret-compass-181513.spotify_v2.user_saved_albums` s
  WHERE s.album_name IS NOT NULL AND s.artist_name IS NOT NULL
  GROUP BY canonical_album_key
),
plays AS (
  SELECT 
    COALESCE(NULLIF(p.canonical_album_key, ''), CONCAT(LOWER(TRIM(p.artist_name)), '::', LOWER(TRIM(p.album_name)))) as canonical_album_key,
    COUNT(*) as total_plays
  FROM `secret-compass-181513.spotify_v2.playback_history` p
  WHERE p.album_name IS NOT NULL AND p.artist_name IS NOT NULL
  GROUP BY 1
),
joined AS (
  SELECT 
    s.canonical_album_key,
    s.artist_name,
    s.album_name,
    s.release_year,
    COALESCE(NULLIF(e.macro_genre, ''), 'Other / Unclassified') as macro_genre,
    COALESCE(p.total_plays, 0) as total_plays,
    s.collector_count,
    COALESCE(e.enrichment_quality_score, 0.0) as quality_score,
    ((e.album_description IS NOT NULL AND e.album_description != '') OR (e.personnel IS NOT NULL AND e.personnel != '')) as has_gatefold
  FROM saved s
  LEFT JOIN plays p ON s.canonical_album_key = p.canonical_album_key
  LEFT JOIN `secret-compass-181513.spotify_v2.album_enriched_metadata` e 
    ON s.canonical_album_key = e.canonical_album_key
)
SELECT 
  artist_name,
  album_name,
  release_year,
  macro_genre,
  total_plays,
  collector_count,
  quality_score,
  canonical_album_key
FROM joined
WHERE NOT has_gatefold
ORDER BY total_plays DESC, collector_count DESC
LIMIT 25;
