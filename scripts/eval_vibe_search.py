#!/usr/bin/env python3
"""
SpinSleeve Vibe Search & Natural Language Discovery Evaluator (APP-19 Prototype)
-------------------------------------------------------------------------------
Interactive benchmarking and prototyping harness to evaluate:
  - Model 1: Pure Semantic Vectors (all-MiniLM-L6-v2)
  - Model 2: Multi-Intent Hybrid Ranker (Dense Vectors + Telemetry / Label / Acclaim Interceptor)
  - Model 3: Lexical Baseline (Keyword / Token Overlap)

Usage:
  # Run standard benchmark suite on the 5 failing queries + 4 core queries:
  .venv/bin/python3 scripts/eval_vibe_search.py --benchmark

  # Single query evaluation:
  .venv/bin/python3 scripts/eval_vibe_search.py --query "blue notes records with a vintage sound"

  # Force refresh catalog cache and embeddings from BigQuery:
  .venv/bin/python3 scripts/eval_vibe_search.py --refresh-cache

  # Interactive mode:
  .venv/bin/python3 scripts/eval_vibe_search.py
"""

import os
import re
import sys
import json
import warnings
import argparse
import numpy as np

warnings.filterwarnings("ignore")
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

CACHE_DIR = Path(__file__).resolve().parent / ".cache_vibe"
CATALOG_CACHE_FILE = CACHE_DIR / "catalog_cache.json"
EMBEDDINGS_MINILM_FILE = CACHE_DIR / "embeddings_minilm.npy"
GCP_PROJECT = os.environ.get("GCP_PROJECT", "secret-compass-181513")


def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Phase 1: Corpus & Vector Enrichment
# ---------------------------------------------------------------------------

def fetch_and_cache_catalog(force: bool = False, user_id: str = "sergebou") -> List[Dict[str, Any]]:
    """
    Fetches golden album metadata enriched with record labels, critical review
    scores, and personal listening telemetry from BigQuery.
    """
    ensure_cache_dir()
    if not force and CATALOG_CACHE_FILE.exists():
        try:
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and len(data) > 100:
                    # Check if schema has Phase 1 fields
                    first = data[0]
                    if "label" in first and "album_plays_30d" in first:
                        return data
        except Exception as e:
            print(f"[!] Cache load error: {e}. Re-fetching from BigQuery...")

    print("[-] Fetching catalog from BigQuery (`album_enriched_metadata` + `user_saved_albums` + `user_albums_features_table`)...")
    from google.cloud import bigquery
    bq = bigquery.Client(project=GCP_PROJECT)

    query = f"""
    WITH saved_info AS (
      SELECT 
        COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name)))) as key,
        ANY_VALUE(label) as label,
        STRING_AGG(DISTINCT genres, ', ') as artist_genres
      FROM `{GCP_PROJECT}.spotify_v2.user_saved_albums`
      GROUP BY 1
    ),
    user_plays AS (
      SELECT
        COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(album_artist_name)), '::', LOWER(TRIM(album_name)))) as key,
        MAX(album_plays) as album_plays,
        MAX(album_plays_30d) as album_plays_30d
      FROM `{GCP_PROJECT}.spotify_v2.user_albums_features_table`
      WHERE user_id = '{user_id}'
      GROUP BY 1
    ),
    golden_catalog AS (
      SELECT
        COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name)))) as key,
        album_name,
        artist_name,
        release_year,
        macro_genre,
        styles,
        derived_moods,
        descriptive_tags,
        album_description,
        personnel,
        discogs_rating,
        discogs_votes,
        pitchfork_score,
        metacritic_score,
        allmusic_score,
        guardian_score,
        ROW_NUMBER() OVER(
          PARTITION BY COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name))))
          ORDER BY 
            CASE WHEN album_description IS NOT NULL AND album_description != '' THEN 1 ELSE 2 END ASC,
            updated_at DESC
        ) as rk
      FROM `{GCP_PROJECT}.spotify_v2.album_enriched_metadata`
      WHERE album_name IS NOT NULL AND album_name != ''
    )
    SELECT 
      c.key,
      c.album_name,
      c.artist_name,
      c.release_year,
      c.macro_genre,
      c.styles,
      c.derived_moods,
      c.descriptive_tags,
      c.album_description,
      c.personnel,
      c.discogs_rating,
      c.discogs_votes,
      c.pitchfork_score,
      c.metacritic_score,
      c.allmusic_score,
      c.guardian_score,
      s.label,
      s.artist_genres,
      COALESCE(p.album_plays, 0.0) as album_plays,
      COALESCE(p.album_plays_30d, 0.0) as album_plays_30d
    FROM golden_catalog c
    LEFT JOIN saved_info s ON c.key = s.key
    LEFT JOIN user_plays p ON c.key = p.key
    WHERE c.rk = 1
    """

    df = bq.query(query).to_dataframe()
    records = []
    for _, row in df.iterrows():
        raw_moods = row.get("derived_moods")
        if isinstance(raw_moods, (list, tuple)):
            moods = list(raw_moods)
        elif hasattr(raw_moods, "tolist"):
            moods = raw_moods.tolist()
        elif isinstance(raw_moods, str) and raw_moods.strip():
            moods = [m.strip() for m in raw_moods.split(",") if m.strip()]
        else:
            moods = []

        raw_tags = row.get("descriptive_tags")
        if isinstance(raw_tags, (list, tuple)):
            tags = list(raw_tags)
        elif hasattr(raw_tags, "tolist"):
            tags = raw_tags.tolist()
        elif isinstance(raw_tags, str) and raw_tags.strip():
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = []

        d_rating = row.get("discogs_rating")
        if d_rating is not None and not np.isnan(d_rating):
            d_rating = float(d_rating)
        else:
            d_rating = None

        d_votes = row.get("discogs_votes")
        if d_votes is not None and not np.isnan(d_votes):
            d_votes = float(d_votes)
        else:
            d_votes = None

        records.append({
            "key": str(row.get("key") or ""),
            "album_name": str(row.get("album_name") or ""),
            "artist_name": str(row.get("artist_name") or ""),
            "release_year": str(row.get("release_year") or ""),
            "macro_genre": str(row.get("macro_genre") or "Other / Unclassified"),
            "styles": str(row.get("styles") or ""),
            "label": str(row.get("label") or ""),
            "derived_moods": [str(m) for m in moods if m],
            "descriptive_tags": [str(t) for t in tags if t],
            "album_description": str(row.get("album_description") or ""),
            "personnel": str(row.get("personnel") or ""),
            "artist_genres": str(row.get("artist_genres") or ""),
            "discogs_rating": d_rating,
            "discogs_votes": d_votes,
            "pitchfork_score": str(row.get("pitchfork_score") or ""),
            "metacritic_score": str(row.get("metacritic_score") or ""),
            "allmusic_score": str(row.get("allmusic_score") or ""),
            "guardian_score": str(row.get("guardian_score") or ""),
            "album_plays": float(row.get("album_plays") or 0.0),
            "album_plays_30d": float(row.get("album_plays_30d") or 0.0),
        })

    with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"[✓] Cached {len(records)} albums with labels, ratings, and telemetry to {CATALOG_CACHE_FILE}")
    return records


def build_vibe_document(album: Dict[str, Any]) -> str:
    """
    Builds a rich semantic document for vector embedding.
    Includes:
      - Title, Artist, Year, Macro-Genre, Subgenres, Styles
      - Record Label (solves label queries e.g. Blue Note, Warp, 4AD)
      - Synthetic Critical Acclaim tokens (solves 'critically acclaimed' queries)
      - Derived Moods, Descriptive Tags, Personnel, and Liner Note Overview
    """
    name = album.get("album_name", "")
    artist = album.get("artist_name", "")
    year = album.get("release_year", "")
    genre = album.get("macro_genre", "")
    subgenres = album.get("artist_genres", "")
    styles = album.get("styles", "")
    label = album.get("label", "")
    moods = ", ".join(album.get("derived_moods", []))
    tags = ", ".join(album.get("descriptive_tags", []))
    desc = album.get("album_description", "")
    snippet = desc[:600].strip() if desc else ""
    pers = album.get("personnel", "")
    pers_snippet = pers[:250].strip() if pers else ""

    parts = [f"{name} by {artist}"]
    if year:
        parts.append(f"({year})")
    if genre:
        parts.append(f"Genre: {genre}")
    if subgenres:
        parts.append(f"Subgenres: {subgenres}")
    if styles:
        parts.append(f"Styles: {styles}")
    if label:
        parts.append(f"Record Label: {label}")
    if moods:
        parts.append(f"Moods: {moods}")
    if tags:
        parts.append(f"Tags: {tags}")
    if pers_snippet:
        parts.append(f"Personnel: {pers_snippet}")
    if snippet:
        parts.append(f"Overview: {snippet}")

    # Inject Synthetic Acclaim Tokens for Vector Proximity
    acclaim_tokens = []
    d_rating = album.get("discogs_rating")
    d_votes = album.get("discogs_votes") or 0.0
    if d_rating is not None:
        if d_rating >= 4.25 and d_votes >= 40:
            acclaim_tokens.append("Masterpiece, highly rated classic, critical acclaim, essential listening")
        elif d_rating >= 4.0:
            acclaim_tokens.append("Acclaimed, widely praised record")

    pf = str(album.get("pitchfork_score") or "")
    if any(k in pf for k in ["8.", "9.", "10", "Best New Music"]):
        acclaim_tokens.append("Pitchfork Best New Music, critical acclaim, essential release")

    mc = str(album.get("metacritic_score") or "")
    try:
        mc_clean = mc.replace("/100", "").strip()
        if mc_clean and float(mc_clean) >= 80:
            acclaim_tokens.append("Universal acclaim, critically acclaimed masterpiece")
    except Exception:
        pass

    if acclaim_tokens:
        parts.append(f"Critical Acclaim: {' | '.join(acclaim_tokens)}")

    return " | ".join(parts)


def get_or_compute_minilm_embeddings(catalog: List[Dict[str, Any]], force: bool = False) -> np.ndarray:
    """Computes or loads all-MiniLM-L6-v2 embeddings for the catalog."""
    ensure_cache_dir()
    if not force and EMBEDDINGS_MINILM_FILE.exists():
        try:
            arr = np.load(EMBEDDINGS_MINILM_FILE)
            if len(arr) == len(catalog):
                return arr
        except Exception:
            pass

    print(f"[-] Computing all-MiniLM-L6-v2 embeddings for {len(catalog)} enriched albums on CPU...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")

    docs = [build_vibe_document(a) for a in catalog]
    embeddings = model.encode(docs, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    np.save(EMBEDDINGS_MINILM_FILE, embeddings)
    print(f"[✓] Saved enriched embeddings matrix ({embeddings.shape}) to {EMBEDDINGS_MINILM_FILE}")
    return embeddings


# ---------------------------------------------------------------------------
# Phase 2: Multi-Intent Query Interceptor & Hybrid Slicing
# ---------------------------------------------------------------------------

ICONIC_LABELS = {
    "blue note": "Blue Note",
    "blue notes": "Blue Note",
    "warp": "Warp",
    "4ad": "4AD",
    "impulse": "Impulse",
    "ecm": "ECM",
    "sub pop": "Sub Pop",
    "motown": "Motown",
    "def jam": "Def Jam",
    "rough trade": "Rough Trade",
    "ninja tune": "Ninja Tune",
    "thrill jockey": "Thrill Jockey",
    "dead oceans": "Dead Oceans",
    "jagjaguwar": "Jagjaguwar",
    "matador": "Matador",
    "domino": "Domino",
    "xl recordings": "XL",
    "xl": "XL",
    "mute": "Mute",
    "brainfeeder": "Brainfeeder",
    "kranky": "Kranky",
    "columbia": "Columbia",
    "atlantic": "Atlantic",
    "verve": "Verve",
    "deutsche grammophon": "Deutsche Grammophon",
    "bella union": "Bella Union",
    "city slang": "City Slang",
    "anti": "Anti",
    "epitaph": "Epitaph",
    "parlophone": "Parlophone",
}

TYPO_CORRECTIONS = {
    r"\baggresive\b": "aggressive",
    r"\bchaotique\b": "chaotic",
    r"\bpsychedlic\b": "psychedelic",
    r"\bjazzy\b": "jazz",
    r"\baccoustic\b": "acoustic",
    r"\bambienty\b": "ambient",
    r"\belectonico\b": "electronic",
}


def normalize_query(query: str) -> str:
    """Corrects common musical search typos."""
    q = query
    for pat, repl in TYPO_CORRECTIONS.items():
        q = re.sub(pat, repl, q, flags=re.IGNORECASE)
    return q


def extract_query_intent(query: str, catalog: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Deconstructs user prompt into structured criteria:
      - decade_range & specific_year
      - macro_genres & instruments
      - label (e.g., Blue Note, Warp, 4AD)
      - telemetry_scope ('recent', 'heavy_rotation', 'unplayed', None)
      - critical_acclaim (Boolean)
      - intensity_mode ('high', 'calm', None)
      - artist (detected catalog artist)
      - clean_vibe_query (residual prompt for dense vector comparison)
    """
    norm_q = normalize_query(query)
    q_lower = norm_q.lower()

    intent: Dict[str, Any] = {
        "raw_query": query,
        "normalized_query": norm_q,
        "decade_range": None,
        "specific_year": None,
        "macro_genres": [],
        "instruments": [],
        "label": None,
        "telemetry_scope": None,
        "critical_acclaim": False,
        "intensity_mode": None,
        "artist": None,
        "clean_vibe_query": norm_q
    }

    # 1. Decade pattern (e.g., '90s', '1980s', '70s', '2000s')
    m_decade = re.search(r'\b(?:19|20)?([5-9]0)s\b', q_lower)
    if m_decade:
        d = int(m_decade.group(1))
        base_century = 1900 if d >= 40 else 2000
        start = base_century + d
        intent["decade_range"] = (start, start + 9)
    else:
        m_2000s = re.search(r'\b(2000s|00s)\b', q_lower)
        if m_2000s:
            intent["decade_range"] = (2000, 2009)
        elif re.search(r'\b(2010s|10s)\b', q_lower):
            intent["decade_range"] = (2010, 2019)

    # Specific year pattern (e.g., '1974', '2001')
    m_year = re.search(r'\b(19\d\d|20\d\d)\b', q_lower)
    if m_year:
        intent["specific_year"] = int(m_year.group(1))

    # 2. Record Label Detection
    for lbl_key, lbl_canonical in ICONIC_LABELS.items():
        if re.search(rf'\b{re.escape(lbl_key)}\b', q_lower):
            intent["label"] = lbl_canonical
            break

    # 3. User Listening Telemetry Scope
    if re.search(r'\b(recent|recently|lately|last month|30 days|past few weeks)\b', q_lower):
        intent["telemetry_scope"] = "recent"
    elif re.search(r'\b(heavy rotation|most played|top played|favorite|frequently)\b', q_lower):
        intent["telemetry_scope"] = "heavy_rotation"
    elif re.search(r'\b(never played|unheard|unplayed|fresh|zero plays)\b', q_lower):
        intent["telemetry_scope"] = "unplayed"

    # 4. Critical Acclaim Intent
    if re.search(r'\b(critically acclaimed|critical acclaim|acclaimed|masterpiece|highest rated|top rated|essential|classic|best albums)\b', q_lower):
        intent["critical_acclaim"] = True

    # 5. Intensity Calibration (Aggressive / Chaotic vs Calm / Ambient)
    if re.search(r'\b(aggressive|chaotic|furious|hardcore|abrasive|heavy|intense|harsh|noisy)\b', q_lower):
        intent["intensity_mode"] = "high"
    elif re.search(r'\b(calm|peaceful|relaxing|quiet|serene|mellow)\b', q_lower):
        intent["intensity_mode"] = "calm"

    # 6. Macro-genres mentioned
    macro_map = {
        "rock": "Rock", "jazz": "Jazz", "ambient": "Ambient", "electronic": "Electronic",
        "folk": "Folk / Country", "country": "Folk / Country", "pop": "Pop",
        "classical": "Classical", "punk": "Punk / Alternative", "metal": "Metal",
        "hip hop": "Hip-Hop", "hip-hop": "Hip-Hop", "rap": "Hip-Hop",
        "soul": "R&B / Soul", "r&b": "R&B / Soul", "blues": "Blues",
        "reggae": "Reggae / Dub", "dub": "Reggae / Dub", "latin": "Latin / World"
    }
    for kw, mg in macro_map.items():
        if re.search(rf'\b{re.escape(kw)}\b', q_lower):
            if mg not in intent["macro_genres"]:
                intent["macro_genres"].append(mg)

    # 7. Instruments
    instruments = ["trumpet", "saxophone", "sax", "piano", "guitar", "synthesizer", "synth",
                   "modular", "strings", "cello", "violin", "flute", "drums", "bass", "fuzz",
                   "acoustic guitar", "pedal steel", "organ"]
    for inst in instruments:
        if re.search(rf'\b{re.escape(inst)}\b', q_lower):
            intent["instruments"].append(inst)

    # 8. Artist Entity Matching (e.g. "Talk Talk", "Miles Davis")
    if catalog:
        # Check against unique catalog artists (longest names first to avoid partial collision)
        artists = sorted(list(set(a["artist_name"] for a in catalog if len(a.get("artist_name", "")) >= 4)), key=len, reverse=True)
        for art in artists:
            if re.search(rf'\b{re.escape(art.lower())}\b', q_lower):
                intent["artist"] = art
                break

    # 9. Clean Residual Vibe Query
    # Strip meta-stopwords and search noise so vector model focuses strictly on sonic descriptors
    stopwords = [
        r'\b(?:i(?:\'ve| have)? been listening to|listening to|listened to)\b',
        r'\b(?:recently|recent|lately|in my library|in my crate)\b',
        r'\b(?:critically acclaimed|critical acclaim|masterpiece|best albums)\b',
        r'\b(?:album|albums|record|records|music|tracks|sleeve|cover)\b',
    ]
    if intent["label"]:
        stopwords.append(rf'\b{re.escape(intent["label"].lower())}\b')
        stopwords.append(r'\bblue notes?\b')

    clean_q = norm_q
    for pat in stopwords:
        clean_q = re.sub(pat, " ", clean_q, flags=re.IGNORECASE)
    clean_q = re.sub(r'\s+', ' ', clean_q).strip()

    intent["clean_vibe_query"] = clean_q if clean_q else norm_q
    return intent


# ---------------------------------------------------------------------------
# Retrieval & Ranking Engines
# ---------------------------------------------------------------------------

def rank_minilm(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
    """Model 1: Pure dense semantic vector search via all-MiniLM-L6-v2."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    # Cosine similarities
    scores = np.dot(embeddings, q_emb)
    top_indices = np.argsort(scores)[::-1][:top_k]

    results = []
    for idx in top_indices:
        results.append({
            "album": catalog[idx],
            "score": float(scores[idx]),
            "model": "all-MiniLM-L6-v2",
            "reasons": [f"Cosine sim: {scores[idx]:.3f}"]
        })
    return results


def rank_intent_hybrid(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
    """
    Model 2: Multi-Intent Hybrid Ranker.
    Combines:
      - Residual dense semantic vector score (using clean_vibe_query)
      - Stateful telemetry boost/filter (recent plays, heavy rotation, unplayed)
      - Record label exact/boost filter
      - Critical acclaim validation boost (Discogs, Pitchfork, Metacritic)
      - Intensity calibration (Metal/Punk vs Ambient disqualification)
      - Artist entity match boost
      - Decade, genre, and instrument roster boosts
    """
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")

    intent = extract_query_intent(query, catalog=catalog)
    vibe_query = intent["clean_vibe_query"]

    # Compute base similarity against the residual sonic query
    q_emb = model.encode([vibe_query], normalize_embeddings=True)[0]
    base_scores = np.dot(embeddings, q_emb)

    combined = []
    for i, a in enumerate(catalog):
        base_sim = float(base_scores[i])
        boost = 0.0
        reasons = [f"Base sim ({vibe_query}): {base_sim:.3f}"]

        # 1. Stateful Telemetry Boost / Penalty
        scope = intent["telemetry_scope"]
        plays_30d = float(a.get("album_plays_30d", 0.0))
        total_plays = float(a.get("album_plays", 0.0))

        if scope == "recent":
            if plays_30d > 0:
                boost += 0.40 + min(0.15, plays_30d * 0.05)
                reasons.append(f"+Recent [{plays_30d:.1f} plays 30d]")
            else:
                boost -= 0.35
                reasons.append(f"-No recent plays")
        elif scope == "heavy_rotation":
            if total_plays >= 5.0:
                boost += 0.35 + min(0.15, total_plays * 0.02)
                reasons.append(f"+Rotation [{total_plays:.1f} plays]")
            else:
                boost -= 0.20
        elif scope == "unplayed":
            if total_plays == 0.0:
                boost += 0.30
                reasons.append(f"+Unplayed in crate")
            else:
                boost -= 0.25

        # 2. Record Label Boost
        if intent["label"]:
            album_lbl = str(a.get("label", "")).lower()
            target_lbl = intent["label"].lower()
            if target_lbl in album_lbl:
                boost += 0.50
                reasons.append(f"+Label [{a.get('label')}]")
            else:
                boost -= 0.10

        # 3. Critical Acclaim Validation
        if intent["critical_acclaim"]:
            d_rat = a.get("discogs_rating") or 0.0
            d_votes = a.get("discogs_votes") or 0.0
            pf = str(a.get("pitchfork_score") or "")
            mc = str(a.get("metacritic_score") or "")

            is_acclaimed = False
            acclaim_note = []
            if d_rat >= 4.25 and d_votes >= 40:
                is_acclaimed = True
                acclaim_note.append(f"Discogs {d_rat:.2f}")
            if any(k in pf for k in ["8.", "9.", "10", "Best New Music"]):
                is_acclaimed = True
                acclaim_note.append(f"P4K {pf}")
            try:
                mc_val = float(mc.replace("/100", "").strip())
                if mc_val >= 80:
                    is_acclaimed = True
                    acclaim_note.append(f"MC {mc_val:.0f}")
            except Exception:
                pass

            if is_acclaimed:
                boost += 0.40
                reasons.append(f"+Acclaimed [{', '.join(acclaim_note)}]")
            elif d_rat >= 4.0:
                boost += 0.15
                reasons.append(f"+High Rating [{d_rat:.2f}]")
            else:
                boost -= 0.25
                reasons.append(f"-Not Acclaimed")

        # 4. Artist Entity Boost
        if intent["artist"]:
            art_target = intent["artist"].lower()
            art_album = str(a.get("artist_name", "")).lower()
            if art_target == art_album:
                boost += 0.50
                reasons.append(f"+Artist Match [{a.get('artist_name')}]")
            elif art_target in art_album:
                boost += 0.25
                reasons.append(f"+Partial Artist [{a.get('artist_name')}]")

        # 5. Intensity Calibration (Aggressive / Chaotic vs Calm)
        album_mg = a.get("macro_genre", "")
        if intent["intensity_mode"] == "high":
            if album_mg in ["Punk / Alternative", "Metal"]:
                boost += 0.35
                reasons.append(f"+Intense Genre [{album_mg}]")
            elif album_mg == "Rock":
                boost += 0.15
                reasons.append(f"+Rock [{album_mg}]")
            elif album_mg in ["Ambient", "Classical"]:
                boost -= 0.40
                reasons.append(f"-Calm Genre Disqualified [{album_mg}]")
        elif intent["intensity_mode"] == "calm":
            if album_mg in ["Ambient", "Classical"]:
                boost += 0.30
                reasons.append(f"+Calm Genre [{album_mg}]")
            elif album_mg in ["Metal", "Punk / Alternative"]:
                boost -= 0.40
                reasons.append(f"-Intense Genre Disqualified [{album_mg}]")

        # 6. Temporal / Decade Boost
        year_str = str(a.get("release_year") or "")
        if year_str.isdigit():
            y = int(year_str)
            if intent["decade_range"]:
                d_start, d_end = intent["decade_range"]
                if d_start <= y <= d_end:
                    boost += 0.15
                    reasons.append(f"+Era [{d_start}s]")
                elif abs(y - d_start) <= 2 or abs(y - d_end) <= 2:
                    boost += 0.05
                    reasons.append(f"~Near era [{y}]")
            elif intent["specific_year"]:
                sy = intent["specific_year"]
                if y == sy:
                    boost += 0.20
                    reasons.append(f"+Year [{sy}]")
                elif abs(y - sy) <= 3:
                    boost += 0.08
                    reasons.append(f"~Near year [{y}]")

        # 7. Macro-Genre Boost
        if intent["macro_genres"] and album_mg in intent["macro_genres"]:
            boost += 0.15
            reasons.append(f"+Genre [{album_mg}]")

        # 8. Instrument Overlap
        doc_lower = (
            a.get("album_description", "") + " " +
            a.get("styles", "") + " " +
            a.get("artist_genres", "") + " " +
            a.get("personnel", "") + " " +
            " ".join(a.get("derived_moods", []))
        ).lower()

        matched_insts = [inst for inst in intent["instruments"] if inst in doc_lower]
        if matched_insts:
            boost += 0.08 * len(matched_insts)
            reasons.append(f"+Inst [{', '.join(matched_insts)}]")

        final_score = base_sim + boost
        combined.append((final_score, a, reasons))

    combined.sort(key=lambda x: x[0], reverse=True)
    return [{
        "album": item[1],
        "score": item[0],
        "model": "Multi-Intent Hybrid Ranker",
        "reasons": item[2]
    } for item in combined[:top_k]]


def rank_lexical(query: str, catalog: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    """Model 3: Lexical baseline: Token overlap across text fields."""
    norm_q = normalize_query(query)
    q_tokens = set(re.findall(r'\b\w{3,}\b', norm_q.lower()))
    if not q_tokens:
        return []

    results = []
    for a in catalog:
        text_corpus = (
            f"{a.get('album_name', '')} {a.get('artist_name', '')} {a.get('release_year', '')} "
            f"{a.get('macro_genre', '')} {a.get('styles', '')} {a.get('label', '')} {a.get('artist_genres', '')} "
            f"{' '.join(a.get('derived_moods', []))} {' '.join(a.get('descriptive_tags', []))} "
            f"{a.get('album_description', '')}"
        ).lower()

        doc_tokens = set(re.findall(r'\b\w{3,}\b', text_corpus))
        overlap = q_tokens.intersection(doc_tokens)
        if not overlap:
            continue

        score = len(overlap) / len(q_tokens)
        results.append({
            "album": a,
            "score": float(score),
            "model": "Lexical Baseline",
            "reasons": [f"Matched: {', '.join(list(overlap)[:5])}"]
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_k]


# ---------------------------------------------------------------------------
# Output Formatter & Benchmark Harness
# ---------------------------------------------------------------------------

def display_results_table(title: str, results: List[Dict[str, Any]]):
    """Renders formatted evaluation table to terminal."""
    print(f"\n{'='*115}")
    print(f"📊 {title}")
    print(f"{'='*115}")
    header = f"{'Rank':<4} {'Score':<7} {'Year':<5} {'Genre':<18} {'Label':<18} {'Artist & Album':<36} {'Rationale / Matches'}"
    print(header)
    print("─" * 115)

    for i, res in enumerate(results, 1):
        a = res["album"]
        score_str = f"{res['score']:.3f}"
        year_str = str(a.get("release_year") or "—")[:4]
        genre_str = str(a.get("macro_genre") or "—")[:17]
        label_str = str(a.get("label") or "—")[:17]
        artist_album = f"{a.get('artist_name', 'Unknown')} - {a.get('album_name', 'Unknown')}"
        if len(artist_album) > 34:
            artist_album = artist_album[:32] + ".."
        reasons_str = " | ".join(res.get("reasons", []))

        print(f"#{i:<3} {score_str:<7} {year_str:<5} {genre_str:<18} {label_str:<18} {artist_album:<36} {reasons_str}")
    print("─" * 115)


def evaluate_query(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 5):
    """Executes side-by-side evaluation across all 3 models."""
    print(f"\n🔮 QUERY: \"{query}\"")
    intent = extract_query_intent(query, catalog=catalog)
    intent_summary = []
    if intent["decade_range"]:
        intent_summary.append(f"Decade: {intent['decade_range'][0]}s")
    if intent["specific_year"]:
        intent_summary.append(f"Year: {intent['specific_year']}")
    if intent["label"]:
        intent_summary.append(f"Label: {intent['label']}")
    if intent["telemetry_scope"]:
        intent_summary.append(f"Scope: {intent['telemetry_scope']}")
    if intent["critical_acclaim"]:
        intent_summary.append("Filter: Critical Acclaim")
    if intent["intensity_mode"]:
        intent_summary.append(f"Intensity: {intent['intensity_mode']}")
    if intent["artist"]:
        intent_summary.append(f"Artist: {intent['artist']}")
    if intent["macro_genres"]:
        intent_summary.append(f"Genre: {', '.join(intent['macro_genres'])}")
    if intent["instruments"]:
        intent_summary.append(f"Instruments: {', '.join(intent['instruments'])}")
    intent_summary.append(f"Residual Vibe: \"{intent['clean_vibe_query']}\"")

    print(f"   [Detected Intent: {' | '.join(intent_summary)}]")

    # 1. Pure Semantic Vector Search (Model 1)
    res_minilm = rank_minilm(query, catalog, embeddings, top_k=top_k)
    display_results_table("Model 1: Pure Semantic Vectors (all-MiniLM-L6-v2)", res_minilm)

    # 2. Multi-Intent Hybrid Ranker (Model 2 - Phase 1 & 2)
    res_hybrid = rank_intent_hybrid(query, catalog, embeddings, top_k=top_k)
    display_results_table("Model 2: Multi-Intent Hybrid Ranker (Dense Vectors + Telemetry/Label/Acclaim Interceptor)", res_hybrid)

    # 3. Lexical Baseline (Model 3)
    res_lexical = rank_lexical(query, catalog, top_k=top_k)
    display_results_table("Model 3: Lexical Baseline (Keyword / Token Overlap)", res_lexical)


def run_benchmark_suite(catalog: List[Dict[str, Any]], embeddings: np.ndarray):
    """Runs automated benchmark on the 5 failing queries + 4 core vibe queries."""
    benchmark_queries = [
        ("Failing Query 1", "aggresive and chaotic records!"),
        ("Failing Query 2", "critically acclaimed records"),
        ("Failing Query 3", "talk talk album with a tree on the sleeve cover"),
        ("Failing Query 4", "jazz albums I have been listening to recently"),
        ("Failing Query 5", "blue notes records with a vintage sound"),
        ("Core Query A", "rainy day jazz piano with trumpet"),
        ("Core Query B", "90s slowcore with whispery vocals and sad guitars"),
        ("Core Query C", "dark hypnotic techno with modular synths"),
        ("Core Query D", "upbeat japanese city pop for a summer drive"),
    ]

    print("\n" + "="*115)
    print("🏆 RUNNING SPINSLEEVE VIBE SEARCH BENCHMARK SUITE (PHASE 1 & PHASE 2)")
    print("="*115)

    for label, q in benchmark_queries:
        print(f"\n>>> [{label}]: \"{q}\"")
        evaluate_query(q, catalog, embeddings, top_k=5)


def interactive_loop(catalog: List[Dict[str, Any]], embeddings: np.ndarray):
    """REPL for interactive user testing."""
    print("\n" + "="*90)
    print("🎧 SpinSleeve Vibe Search Interactive Evaluation Studio (Phase 1 & Phase 2)")
    print("   Type any vibe, mood, era, label, or listening status description.")
    print("   (Enter 'q' or press Ctrl+C to exit)")
    print("="*90)

    while True:
        try:
            print("\n" + "─"*90)
            user_input = input("Enter vibe prompt > ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("q", "quit", "exit"):
                print("\n[✓] Exiting Vibe Search Evaluator. Goodbye!")
                break
            evaluate_query(user_input, catalog, embeddings, top_k=5)
        except (KeyboardInterrupt, EOFError):
            print("\n\n[✓] Session terminated. Goodbye!")
            break


def main():
    parser = argparse.ArgumentParser(description="Evaluate SpinSleeve Vibe Search models.")
    parser.add_argument("--query", "-q", type=str, help="Single query to evaluate in non-interactive mode.")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results to display per model.")
    parser.add_argument("--refresh-cache", action="store_true", help="Force refresh catalog and embeddings cache.")
    parser.add_argument("--benchmark", action="store_true", help="Execute the complete benchmark suite.")
    parser.add_argument("--user-id", "-u", type=str, default="sergebou", help="User ID for personal telemetry joins.")
    args = parser.parse_args()

    print("[*] Initializing SpinSleeve Vibe Search Evaluator...")
    catalog = fetch_and_cache_catalog(force=args.refresh_cache, user_id=args.user_id)
    embeddings = get_or_compute_minilm_embeddings(catalog, force=args.refresh_cache)

    if args.benchmark:
        run_benchmark_suite(catalog, embeddings)
    elif args.query:
        evaluate_query(args.query, catalog, embeddings, top_k=args.top_k)
    else:
        interactive_loop(catalog, embeddings)


if __name__ == "__main__":
    main()
