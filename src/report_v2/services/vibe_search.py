"""
SpinSleeve Vibe Search & Natural Language Crate Discovery Engine (APP-19 Phase 3).

Provides in-memory semantic retrieval and hybrid ranking across user vinyl crates:
- Multi-intent query deconstruction (labels, telemetry scope, acclaim, intensity, instruments, era).
- Fast NumPy dot-product vector scoring against precomputed catalog embeddings.
- Layered hybrid boosts ensuring precision ranking for authentic labels and critical masterworks.
- Graceful lexical fallback if sentence-transformers is unavailable.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional

import numpy as np

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOG_CACHE_FILE = DATA_DIR / "catalog_cache.json"
EMBEDDINGS_FILE = DATA_DIR / "embeddings_minilm.npy"

_EMBEDDINGS_MATRIX: Optional[np.ndarray] = None
_CATALOG_KEY_INDEX: Dict[str, int] = {}
_CATALOG_METADATA: List[Dict[str, Any]] = []
_TRANSFORMER_MODEL = None

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


def _load_data_assets():
    """Lazily loads precomputed embeddings matrix and catalog index on first query."""
    global _EMBEDDINGS_MATRIX, _CATALOG_KEY_INDEX, _CATALOG_METADATA
    if _EMBEDDINGS_MATRIX is not None:
        return

    if EMBEDDINGS_FILE.exists() and CATALOG_CACHE_FILE.exists():
        try:
            _EMBEDDINGS_MATRIX = np.load(EMBEDDINGS_FILE)
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                _CATALOG_METADATA = json.load(f)

            for idx, a in enumerate(_CATALOG_METADATA):
                key = a.get("key") or f"{a.get('artist_name', '').lower()}::{a.get('album_name', '').lower()}"
                _CATALOG_KEY_INDEX[key.strip().lower()] = idx

            logger.info("Loaded precomputed vibe embeddings matrix %s with %d catalog keys",
                        _EMBEDDINGS_MATRIX.shape, len(_CATALOG_KEY_INDEX))
        except Exception as e:
            logger.warning("Could not load vibe embeddings file: %s", e)
            _EMBEDDINGS_MATRIX = None


def _get_transformer_model():
    """Lazily instantiates all-MiniLM-L6-v2 model with safe fallback."""
    global _TRANSFORMER_MODEL
    if _TRANSFORMER_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _TRANSFORMER_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Initialized in-memory SentenceTransformer('all-MiniLM-L6-v2') for Vibe Digger")
        except Exception as e:
            logger.warning("SentenceTransformer unavailable for Vibe Search (%s); using lexical fallback", e)
            _TRANSFORMER_MODEL = False
    return _TRANSFORMER_MODEL


def normalize_query(query: str) -> str:
    """Corrects common musical search typos."""
    q = query
    for pat, repl in TYPO_CORRECTIONS.items():
        q = re.sub(pat, repl, q, flags=re.IGNORECASE)
    return q


def extract_query_intent(query: str, catalog: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Deconstructs user prompt into structured search criteria."""
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

    # 1. Decade & Year
    m_decade = re.search(r'\b(?:19|20)?([5-9]0)s\b', q_lower)
    if m_decade:
        d = int(m_decade.group(1))
        base_century = 1900 if d >= 40 else 2000
        start = base_century + d
        intent["decade_range"] = (start, start + 9)
    else:
        if re.search(r'\b(2000s|00s)\b', q_lower):
            intent["decade_range"] = (2000, 2009)
        elif re.search(r'\b(2010s|10s)\b', q_lower):
            intent["decade_range"] = (2010, 2019)

    m_year = re.search(r'\b(19\d\d|20\d\d)\b', q_lower)
    if m_year:
        intent["specific_year"] = int(m_year.group(1))

    # 2. Record Label
    for lbl_key, lbl_canonical in ICONIC_LABELS.items():
        if re.search(rf'\b{re.escape(lbl_key)}\b', q_lower):
            intent["label"] = lbl_canonical
            break

    # 3. Listening Telemetry
    if re.search(r'\b(recent|recently|lately|last month|30 days|past few weeks)\b', q_lower):
        intent["telemetry_scope"] = "recent"
    elif re.search(r'\b(heavy rotation|most played|top played|favorite|frequently)\b', q_lower):
        intent["telemetry_scope"] = "heavy_rotation"
    elif re.search(r'\b(never played|unheard|unplayed|fresh|zero plays)\b', q_lower):
        intent["telemetry_scope"] = "unplayed"

    # 4. Critical Acclaim
    if re.search(r'\b(critically acclaimed|critical acclaim|acclaimed|masterpiece|highest rated|top rated|essential|classic|best albums)\b', q_lower):
        intent["critical_acclaim"] = True

    # 5. Intensity Mode
    if re.search(r'\b(aggressive|chaotic|furious|hardcore|abrasive|heavy|intense|harsh|noisy)\b', q_lower):
        intent["intensity_mode"] = "high"
    elif re.search(r'\b(calm|peaceful|relaxing|quiet|serene|mellow)\b', q_lower):
        intent["intensity_mode"] = "calm"

    # 6. Macro Genres
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

    # 8. Artist Matching
    if catalog:
        artists = sorted(list(set(a.get("album_artist_name", a.get("artist_name", "")) for a in catalog if len(a.get("album_artist_name", a.get("artist_name", ""))) >= 4)), key=len, reverse=True)
        for art in artists:
            if re.search(rf'\b{re.escape(art.lower())}\b', q_lower):
                intent["artist"] = art
                break

    # 9. Clean Residual Vibe Query
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


def warmup_vibe_engine():
    """Preloads embeddings and SentenceTransformer model so queries execute in <200ms."""
    try:
        _load_data_assets()
        m = _get_transformer_model()
        if m and m is not False:
            m.encode(["warmup"], normalize_embeddings=True)
            logger.info("SentenceTransformer model fully warmed up and compiled")
    except Exception as e:
        logger.debug("Vibe engine warmup notice: %s", e)


def search_user_crate(
    user_id: str,
    query: str,
    scope: str = "saved",
    horizon: str = "all_time",
    top_k: int = 15
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Executes Model 2 Multi-Intent Hybrid Search across the user's crate.
    Returns: (ranked_albums_list, detected_intent_dict)
    """
    from services.catalog import fetch_user_album_data, fetch_unowned_album_data

    catalog_data = fetch_user_album_data(user_id) or {}
    owned_albums = catalog_data.get("albums", [])

    candidate_albums = list(owned_albums)
    if scope == "unowned":
        try:
            unowned = fetch_unowned_album_data(user_id, horizon=horizon)
            if unowned:
                for u in unowned:
                    u_copy = dict(u)
                    u_copy["is_unowned"] = True
                    candidate_albums.append(u_copy)
        except Exception as e:
            logger.warning("Could not fetch unowned albums for vibe search: %s", e)

    if not candidate_albums:
        return [], {"error": "No albums in library"}

    _load_data_assets()
    intent = extract_query_intent(query, catalog=candidate_albums)
    vibe_query = intent["clean_vibe_query"]

    model = _get_transformer_model()
    use_dense = (model and model is not False and _EMBEDDINGS_MATRIX is not None)

    q_emb = None
    if use_dense:
        try:
            q_emb = model.encode([vibe_query], normalize_embeddings=True)[0]
        except Exception as e:
            logger.warning("Error encoding vibe query vector: %s; falling back to lexical", e)
            use_dense = False

    q_tokens = set(re.findall(r'\b\w{3,}\b', vibe_query.lower()))

    scored_items = []
    for a in candidate_albums:
        ar_name = a.get("album_artist_name", a.get("artist_name", ""))
        al_name = a.get("album_name", "")
        canon_key = a.get("canonical_album_key") or f"{ar_name.lower()}::{al_name.lower()}".strip()

        # Base similarity score
        base_sim = 0.20  # Neutral baseline
        reasons = []

        if use_dense and q_emb is not None:
            idx = _CATALOG_KEY_INDEX.get(canon_key.lower())
            if idx is not None and idx < len(_EMBEDDINGS_MATRIX):
                alb_emb = _EMBEDDINGS_MATRIX[idx]
                sim = float(np.dot(alb_emb, q_emb))
                base_sim = max(0.0, sim)
                reasons.append(f"Vibe Match: {base_sim:.2f}")
            else:
                # Text token overlap baseline for un-embedded records
                text_corpus = f"{al_name} {ar_name} {a.get('macro_genre', '')} {a.get('album_genres', '')} {a.get('album_description', '')}".lower()
                doc_tokens = set(re.findall(r'\b\w{3,}\b', text_corpus))
                overlap = q_tokens.intersection(doc_tokens)
                if q_tokens:
                    base_sim = 0.25 + (len(overlap) / len(q_tokens)) * 0.45
        else:
            # Lexical overlap
            text_corpus = f"{al_name} {ar_name} {a.get('macro_genre', '')} {a.get('album_genres', '')} {a.get('album_description', '')}".lower()
            doc_tokens = set(re.findall(r'\b\w{3,}\b', text_corpus))
            overlap = q_tokens.intersection(doc_tokens)
            if q_tokens:
                base_sim = (len(overlap) / len(q_tokens)) * 0.60
            if overlap:
                reasons.append(f"Matched: {', '.join(list(overlap)[:3])}")

        boost = 0.0

        # 1. Telemetry Scope
        plays_30d = float(a.get("album_plays_30d", a.get("play_count_30d", 0.0)))
        total_plays = float(a.get("album_plays", a.get("total_plays", 0.0)))
        scope_intent = intent["telemetry_scope"]

        if scope_intent == "recent":
            if plays_30d > 0:
                boost += 0.40 + min(0.15, plays_30d * 0.05)
                reasons.append(f"+Recent [{plays_30d:.1f} plays 30d]")
            else:
                boost -= 0.35
                reasons.append("-No recent plays")
        elif scope_intent == "heavy_rotation":
            if total_plays >= 5.0:
                boost += 0.35 + min(0.15, total_plays * 0.02)
                reasons.append(f"+Rotation [{total_plays:.1f} plays]")
            else:
                boost -= 0.20
        elif scope_intent == "unplayed":
            if total_plays == 0.0:
                boost += 0.30
                reasons.append("+Unplayed in crate")
            else:
                boost -= 0.25

        # 2. Record Label Match
        alb_label = str(a.get("album_label", a.get("label", "")))
        if intent["label"]:
            target_lbl = intent["label"].lower()
            if target_lbl in alb_label.lower():
                boost += 0.50
                reasons.append(f"+Label [{alb_label}]")
            else:
                boost -= 0.15

        # 3. Critical Acclaim Validation
        if intent["critical_acclaim"]:
            d_rat = float(a.get("discogs_rating", 0.0) or 0.0)
            pf = str(a.get("pitchfork_score", "") or "")
            is_acclaimed = (d_rat >= 4.20) or any(k in pf for k in ["8.", "9.", "10", "Best New Music"])
            if is_acclaimed:
                boost += 0.40
                reasons.append(f"+Acclaimed [{d_rat:.2f}★, pf:{pf}]" if d_rat > 0 else f"+Acclaimed [pf:{pf}]")
            elif d_rat >= 4.0:
                boost += 0.15
                reasons.append(f"+High Rating [{d_rat:.2f}★]")
            else:
                boost -= 0.25
                reasons.append("-Not Acclaimed")

        # 4. Artist Entity Boost
        if intent["artist"]:
            art_target = intent["artist"].lower()
            if art_target == ar_name.lower():
                boost += 0.50
                reasons.append(f"+Artist [{ar_name}]")
            elif art_target in ar_name.lower():
                boost += 0.25
                reasons.append(f"+Partial Artist [{ar_name}]")

        # 5. Intensity Calibration (Aggressive vs Calm)
        alb_mg = a.get("macro_genre", "")
        if intent["intensity_mode"] == "high":
            if alb_mg in ["Punk / Alternative", "Metal"]:
                boost += 0.35
                reasons.append(f"+Intense Genre [{alb_mg}]")
            elif alb_mg == "Rock":
                boost += 0.15
                reasons.append(f"+Rock [{alb_mg}]")
            elif alb_mg in ["Ambient", "Classical"]:
                boost -= 0.40
                reasons.append(f"-Calm Genre [{alb_mg}]")
        elif intent["intensity_mode"] == "calm":
            if alb_mg in ["Ambient", "Classical"]:
                boost += 0.30
                reasons.append(f"+Calm Genre [{alb_mg}]")
            elif alb_mg in ["Metal", "Punk / Alternative"]:
                boost -= 0.40
                reasons.append(f"-Intense Genre [{alb_mg}]")

        # 6. Temporal / Era Boost
        year_str = str(a.get("release_year", a.get("year", "")) or "")
        if year_str.isdigit():
            y = int(year_str)
            if intent["decade_range"]:
                d_start, d_end = intent["decade_range"]
                if d_start <= y <= d_end:
                    boost += 0.15
                    reasons.append(f"+Era [{d_start}s]")
            elif intent["specific_year"]:
                sy = intent["specific_year"]
                if y == sy:
                    boost += 0.20
                    reasons.append(f"+Year [{sy}]")

        # 7. Macro Genre Boost
        if intent["macro_genres"] and alb_mg in intent["macro_genres"]:
            boost += 0.15
            reasons.append(f"+Genre [{alb_mg}]")

        # 8. Instruments Overlap
        doc_lower = (
            str(a.get("album_description", "")) + " " +
            str(a.get("enriched_styles", "")) + " " +
            str(a.get("album_genres", "")) + " " +
            str(a.get("personnel", ""))
        ).lower()
        matched_insts = [inst for inst in intent["instruments"] if inst in doc_lower]
        if matched_insts:
            boost += 0.08 * len(matched_insts)
            reasons.append(f"+Inst [{', '.join(matched_insts)}]")

        final_score = max(0.01, min(0.99, base_sim + boost))
        a_result = dict(a)
        a_result["vibe_score"] = round(final_score, 3)
        a_result["vibe_reasons"] = reasons
        scored_items.append((final_score, a_result))

    scored_items.sort(key=lambda x: x[0], reverse=True)
    top_results = [item[1] for item in scored_items[:top_k]]
    return top_results, intent
