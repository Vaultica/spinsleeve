#!/usr/bin/env python3
"""
SpinSleeve Vibe Search & Natural Language Discovery Evaluator
------------------------------------------------------------
Interactive benchmarking and prototyping harness to evaluate semantic vector
search, hybrid ranking, and lexical baselines across the SpinSleeve catalog.

Usage:
  # Interactive mode:
  .venv/bin/python3 scripts/eval_vibe_search.py

  # Single query evaluation:
  .venv/bin/python3 scripts/eval_vibe_search.py --query "rainy day jazz piano with trumpet"

  # Force refresh catalog cache from BigQuery:
  .venv/bin/python3 scripts/eval_vibe_search.py --refresh-cache
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
from typing import List, Dict, Any, Tuple

CACHE_DIR = Path(__file__).resolve().parent / ".cache_vibe"
CATALOG_CACHE_FILE = CACHE_DIR / "catalog_cache.json"
EMBEDDINGS_MINILM_FILE = CACHE_DIR / "embeddings_minilm.npy"
GCP_PROJECT = os.environ.get("GCP_PROJECT", "secret-compass-181513")


def ensure_cache_dir():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_and_cache_catalog(force: bool = False) -> List[Dict[str, Any]]:
    """Fetches golden album metadata from BigQuery and caches locally as JSON."""
    ensure_cache_dir()
    if not force and CATALOG_CACHE_FILE.exists():
        try:
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data and len(data) > 100:
                    return data
        except Exception as e:
            print(f"[!] Cache load error: {e}. Re-fetching from BigQuery...")

    print("[-] Fetching catalog from BigQuery (`album_enriched_metadata` + `user_saved_albums`)...")
    from google.cloud import bigquery
    bq = bigquery.Client(project=GCP_PROJECT)

    query = """
    WITH saved_genres AS (
      SELECT 
        COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name)))) as key,
        STRING_AGG(DISTINCT genres, ', ') as artist_genres
      FROM `secret-compass-181513.spotify_v2.user_saved_albums`
      WHERE genres IS NOT NULL AND genres != ''
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
        ROW_NUMBER() OVER(
          PARTITION BY COALESCE(NULLIF(canonical_album_key, ''), CONCAT(LOWER(TRIM(artist_name)), '::', LOWER(TRIM(album_name))))
          ORDER BY 
            CASE WHEN album_description IS NOT NULL AND album_description != '' THEN 1 ELSE 2 END ASC,
            updated_at DESC
        ) as rk
      FROM `secret-compass-181513.spotify_v2.album_enriched_metadata`
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
      g.artist_genres
    FROM golden_catalog c
    LEFT JOIN saved_genres g ON c.key = g.key
    WHERE c.rk = 1
    """

    df = bq.query(query).to_dataframe()
    records = []
    for _, row in df.iterrows():
        raw_moods = row.get("derived_moods")
        if isinstance(raw_moods, (list, tuple)):
            moods = raw_moods
        elif hasattr(raw_moods, "tolist"):
            moods = raw_moods.tolist()
        elif isinstance(raw_moods, str) and raw_moods.strip():
            moods = [m.strip() for m in raw_moods.split(",") if m.strip()]
        else:
            moods = []

        raw_tags = row.get("descriptive_tags")
        if isinstance(raw_tags, (list, tuple)):
            tags = raw_tags
        elif hasattr(raw_tags, "tolist"):
            tags = raw_tags.tolist()
        elif isinstance(raw_tags, str) and raw_tags.strip():
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = []

        records.append({
            "key": str(row.get("key") or ""),
            "album_name": str(row.get("album_name") or ""),
            "artist_name": str(row.get("artist_name") or ""),
            "release_year": str(row.get("release_year") or ""),
            "macro_genre": str(row.get("macro_genre") or "Other / Unclassified"),
            "styles": str(row.get("styles") or ""),
            "derived_moods": [str(m) for m in moods if m],
            "descriptive_tags": [str(t) for t in tags if t],
            "album_description": str(row.get("album_description") or ""),
            "personnel": str(row.get("personnel") or ""),
            "artist_genres": str(row.get("artist_genres") or "")
        })

    with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    print(f"[✓] Cached {len(records)} albums to {CATALOG_CACHE_FILE}")
    return records


def build_vibe_document(album: Dict[str, Any]) -> str:
    """Builds a rich semantic document for vector embedding."""
    name = album.get("album_name", "")
    artist = album.get("artist_name", "")
    year = album.get("release_year", "")
    genre = album.get("macro_genre", "")
    subgenres = album.get("artist_genres", "")
    styles = album.get("styles", "")
    moods = ", ".join(album.get("derived_moods", []))
    tags = ", ".join(album.get("descriptive_tags", []))
    desc = album.get("album_description", "")
    snippet = desc[:500].strip() if desc else ""
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
    if moods:
        parts.append(f"Moods: {moods}")
    if tags:
        parts.append(f"Tags: {tags}")
    if pers_snippet:
        parts.append(f"Personnel: {pers_snippet}")
    if snippet:
        parts.append(f"Overview: {snippet}")

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

    print(f"[-] Computing all-MiniLM-L6-v2 embeddings for {len(catalog)} albums on CPU...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")

    docs = [build_vibe_document(a) for a in catalog]
    embeddings = model.encode(docs, batch_size=64, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype=np.float32)

    np.save(EMBEDDINGS_MINILM_FILE, embeddings)
    print(f"[✓] Saved embeddings matrix ({embeddings.shape}) to {EMBEDDINGS_MINILM_FILE}")
    return embeddings


# ---------------------------------------------------------------------------
# Retrieval & Ranking Engines
# ---------------------------------------------------------------------------

def extract_query_intent(query: str) -> Dict[str, Any]:
    """Extracts decade, specific year, instruments, and macro-genres from prompt."""
    q_lower = query.lower()
    intent = {
        "decade_range": None,
        "specific_year": None,
        "macro_genres": [],
        "instruments": [],
        "mood_tokens": []
    }

    # Decade pattern (e.g., '90s', '1980s', '70s', '2000s')
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

    # Macro-genres mentioned
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

    # Instruments
    instruments = ["trumpet", "saxophone", "sax", "piano", "guitar", "synthesizer", "synth",
                   "modular", "strings", "cello", "violin", "flute", "drums", "bass", "fuzz",
                   "acoustic guitar", "pedal steel", "organ"]
    for inst in instruments:
        if re.search(rf'\b{re.escape(inst)}\b', q_lower):
            intent["instruments"].append(inst)

    return intent


def rank_minilm(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
    """Pure dense semantic vector search via all-MiniLM-L6-v2."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    q_emb = model.encode([query], normalize_embeddings=True)[0]

    # Cosine similarities (since embeddings are normalized, dot product = cosine similarity)
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


def rank_hybrid(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 10) -> List[Dict[str, Any]]:
    """Hybrid ranker: Dense semantic vector + Temporal anchor + Macro-genre/Lexical boost."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    q_emb = model.encode([query], normalize_embeddings=True)[0]
    base_scores = np.dot(embeddings, q_emb)

    intent = extract_query_intent(query)
    q_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))

    combined = []
    for i, a in enumerate(catalog):
        base_sim = float(base_scores[i])
        boost = 0.0
        reasons = [f"Base sim: {base_sim:.3f}"]

        # 1. Temporal / Decade Boost
        year_str = a.get("release_year", "")
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

        # 2. Macro-Genre Boost
        album_mg = a.get("macro_genre", "")
        if intent["macro_genres"] and album_mg in intent["macro_genres"]:
            boost += 0.12
            reasons.append(f"+Genre [{album_mg}]")

        # 3. Instrument / Tag Lexical Overlap
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
        "model": "Hybrid Ranker",
        "reasons": item[2]
    } for item in combined[:top_k]]


def rank_lexical(query: str, catalog: List[Dict[str, Any]], top_k: int = 10) -> List[Dict[str, Any]]:
    """Lexical baseline: TF-IDF / Token overlap across fields (no semantic embeddings)."""
    q_tokens = set(re.findall(r'\b\w{3,}\b', query.lower()))
    if not q_tokens:
        return []

    results = []
    for a in catalog:
        text_corpus = (
            f"{a.get('album_name', '')} {a.get('artist_name', '')} {a.get('release_year', '')} "
            f"{a.get('macro_genre', '')} {a.get('styles', '')} {a.get('artist_genres', '')} "
            f"{' '.join(a.get('derived_moods', []))} {' '.join(a.get('descriptive_tags', []))} "
            f"{a.get('album_description', '')}"
        ).lower()

        doc_tokens = set(re.findall(r'\b\w{3,}\b', text_corpus))
        overlap = q_tokens.intersection(doc_tokens)
        if not overlap:
            continue

        # Score by token overlap fraction and length
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
# Output Formatter
# ---------------------------------------------------------------------------

def display_results_table(title: str, results: List[Dict[str, Any]]):
    """Renders formatted evaluation table to terminal."""
    print(f"\n{'='*100}")
    print(f"📊 {title}")
    print(f"{'='*100}")
    header = f"{'Rank':<4} {'Score':<7} {'Year':<5} {'Genre':<18} {'Artist & Album':<42} {'Rationale / Matches'}"
    print(header)
    print("─" * 100)

    for i, res in enumerate(results, 1):
        a = res["album"]
        score_str = f"{res['score']:.3f}"
        year_str = str(a.get("release_year") or "—")[:4]
        genre_str = str(a.get("macro_genre") or "—")[:17]
        artist_album = f"{a.get('artist_name', 'Unknown')} - {a.get('album_name', 'Unknown')}"
        if len(artist_album) > 40:
            artist_album = artist_album[:38] + ".."
        reasons_str = " | ".join(res.get("reasons", []))

        print(f"#{i:<3} {score_str:<7} {year_str:<5} {genre_str:<18} {artist_album:<42} {reasons_str}")
    print("─" * 100)


def evaluate_query(query: str, catalog: List[Dict[str, Any]], embeddings: np.ndarray, top_k: int = 5):
    """Executes side-by-side evaluation across all 3 models."""
    print(f"\n🔮 QUERY: \"{query}\"")
    intent = extract_query_intent(query)
    intent_summary = []
    if intent["decade_range"]:
        intent_summary.append(f"Decade: {intent['decade_range'][0]}s")
    if intent["specific_year"]:
        intent_summary.append(f"Year: {intent['specific_year']}")
    if intent["macro_genres"]:
        intent_summary.append(f"Genre: {', '.join(intent['macro_genres'])}")
    if intent["instruments"]:
        intent_summary.append(f"Instruments: {', '.join(intent['instruments'])}")

    if intent_summary:
        print(f"   [Detected Intent: {' | '.join(intent_summary)}]")

    # 1. Pure Semantic Vector Search
    res_minilm = rank_minilm(query, catalog, embeddings, top_k=top_k)
    display_results_table("Model 1: Pure Semantic Vectors (all-MiniLM-L6-v2)", res_minilm)

    # 2. Hybrid Vibe Ranker
    res_hybrid = rank_hybrid(query, catalog, embeddings, top_k=top_k)
    display_results_table("Model 2: Hybrid Vibe Ranker (MiniLM + Temporal/Genre/Instrument Boost)", res_hybrid)

    # 3. Lexical Baseline
    res_lexical = rank_lexical(query, catalog, top_k=top_k)
    display_results_table("Model 3: Lexical Baseline (Keyword / Token Overlap)", res_lexical)


def interactive_loop(catalog: List[Dict[str, Any]], embeddings: np.ndarray):
    """REPL for interactive user testing."""
    print("\n" + "="*80)
    print("🎧 SpinSleeve Vibe Search Interactive Evaluation Studio")
    print("   Type any vibe, mood, era, style, or musical description.")
    print("   (Enter 'q' or press Ctrl+C to exit)")
    print("="*80)

    sample_prompts = [
        "melancholic rainy day jazz piano with trumpet",
        "90s slowcore with whispery vocals and sad guitars",
        "dark dystopian techno with heavy modular synths",
        "upbeat japanese city pop for a sunny drive",
        "introspective acoustic folk recorded in a cabin"
    ]
    print("\nTip: Try prompts like:")
    for p in sample_prompts:
        print(f"  • \"{p}\"")

    while True:
        try:
            print("\n" + "─"*80)
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
    args = parser.parse_args()

    print("[*] Initializing SpinSleeve Vibe Search Evaluator...")
    catalog = fetch_and_cache_catalog(force=args.refresh_cache)
    embeddings = get_or_compute_minilm_embeddings(catalog, force=args.refresh_cache)

    if args.query:
        evaluate_query(args.query, catalog, embeddings, top_k=args.top_k)
    else:
        interactive_loop(catalog, embeddings)


if __name__ == "__main__":
    main()
