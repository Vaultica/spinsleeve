"""
SpinSleeve LLM Vibe Digger Service (`services/vibe_llm.py`) — APP-19 LLM Upgrade.
--------------------------------------------------------------------------------
Provider-pluggable LLM layer on top of the deterministic hybrid ranker
(`services/vibe_search.py`), benchmarking Mistral AI vs Gemini side-by-side:

- Option 1 (default, "compiler"): LLM "Vibe Compiler" converts the free-text prompt
  into strict JSON intent (macro_genres, moods, era bounds, exclusions, expansion
  terms); deterministic Python scoring over the user's candidate pool is executed by
  `vibe_search.search_user_crate` via a merged precomputed intent. No catalog dump
  is ever sent to the provider.
- Option 3 (prototype, "rerank"): existing fast retrieval selects the top-30 candidate
  albums, compact metadata rows are reranked by the LLM with strict `album_id`
  grounding — any hallucinated ID not present in the candidate pool is discarded.

Invariants:
- Provider abstraction: Mistral (Mistral Small 4 / Ministral 3 14B) and Gemini
  (2.5 Flash-Lite) adapters via environment/Secret Manager keys, strict request
  timeout (default 2.5s), and structured JSON schema validation.
- Deterministic fallback: missing API keys, timeouts, HTTP errors, or invalid JSON
  seamlessly fall back to the heuristic/MiniLM ranker — user requests never fail.
- Normalized Datastore caching (`VibeSearchCache`) keyed by
  LOWER(TRIM(q)) + scope + horizon + provider + mode with TTL; zero per-request
  catalogue re-embedding (query embedding only, catalog vectors are precomputed).
- Zero raw NaN/NaT: every payload passes through `safe_str`/`safe_int`/`safe_float`
  sanitization before leaving this module.

Key exports: llm_vibe_search, resolve_provider_mode, build_cache_key.
"""
import os
import re
import json
import time
import math
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests

from services.bigquery import safe_float, safe_int, safe_str

logger = logging.getLogger(__name__)

DEFAULT_PROVIDER = "mistral"
DEFAULT_MISTRAL_COMPILER_MODEL = "mistral-small-4"
DEFAULT_MISTRAL_RERANKER_MODEL = "ministral-3-14b"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

RERANK_POOL_SIZE = 30
MAX_EXPANDED_TERMS = 8
MAX_RERANK_ENTRIES = 30
MAX_REASON_CHARS = 140
_MEMORY_CACHE_CAP = 256

MACRO_GENRE_MENU = [
    "Rock", "Jazz", "Ambient", "Electronic", "Folk / Country", "Pop",
    "Classical", "Punk / Alternative", "Metal", "Hip-Hop", "R&B / Soul",
    "Blues", "Reggae / Dub", "Latin / World",
]

_COMPILER_SYSTEM_PROMPT = (
    "You are the SpinSleeve Vibe Compiler for a personal vinyl crate app. "
    "Convert the user's free-text music vibe request into strict JSON with EXACTLY these keys: "
    f"macro_genres (array; only from this menu: {', '.join(MACRO_GENRE_MENU)}; empty if unclear), "
    "moods (array of lowercase mood adjectives, e.g. melancholic, nocturnal), "
    "era_min (integer year or null), era_max (integer year or null), "
    "excluded_moods (array of lowercase moods the user negates, e.g. sleepy for 'not sleepy'), "
    "expanded_terms (array of short search phrases capturing imagery, instruments, and style). "
    "Never invent album or artist names. Return ONLY the JSON object."
)

_RERANK_SYSTEM_PROMPT = (
    "You are the SpinSleeve Vibe Reranker. You receive a user's vibe request and candidate "
    'albums as JSON. Return strict JSON {"ranked": [{"album_id": "...", "reason": "..."}]} '
    "ordered best-fit first (max 30 entries). Use ONLY album_id values present in the "
    f"candidates; write each reason in under {MAX_REASON_CHARS} characters. Return ONLY the JSON object."
)


class VibeLLMError(Exception):
    """Raised when an LLM provider call or schema validation fails (triggers fallback)."""


_MEMORY_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}


def _llm_timeout() -> float:
    """Resolves the strict LLM request timeout in seconds (default 2.5s, clamped 1.0-10.0)."""
    timeout = safe_float(os.environ.get("VIBE_LLM_TIMEOUT"), 2.5)
    return max(1.0, min(10.0, timeout))


def resolve_provider_mode(provider: Optional[str], mode: Optional[str]) -> Tuple[Optional[str], str]:
    """Normalizes provider/mode request params; returns (None, 'heuristic') when the LLM is off."""
    p = (str(provider) if provider is not None else "").strip().lower() or "auto"
    if p == "auto":
        p = safe_str(os.environ.get("VIBE_LLM_PROVIDER")).strip().lower() or DEFAULT_PROVIDER
    if p in ("", "off", "none", "heuristic", "local") or p not in ("mistral", "gemini"):
        return None, "heuristic"
    m = safe_str(mode).strip().lower() or "compiler"
    if m not in ("compiler", "rerank"):
        m = "compiler"
    return p, m


def _norm_component(value: str) -> str:
    """Normalizes a cache-key component: trimmed, lowercased, whitespace collapsed."""
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def build_cache_key(user_id: str, query: str, scope: str, horizon: str, provider: str, mode: str) -> str:
    """Builds the normalized cache key: LOWER(TRIM(q)) + scope + horizon + provider + mode."""
    return "::".join([
        _norm_component(user_id), _norm_component(query), _norm_component(scope),
        _norm_component(horizon), _norm_component(provider), _norm_component(mode),
    ])


def _memory_get(cache_key: str) -> Optional[Dict[str, Any]]:
    entry = _MEMORY_CACHE.get(cache_key)
    if not entry:
        return None
    expires_at, payload = entry
    if expires_at < time.time():
        _MEMORY_CACHE.pop(cache_key, None)
        return None
    return payload


def _memory_set(cache_key: str, payload: Dict[str, Any]) -> None:
    if len(_MEMORY_CACHE) >= _MEMORY_CACHE_CAP:
        oldest_key = min(_MEMORY_CACHE, key=lambda k: _MEMORY_CACHE[k][0])
        _MEMORY_CACHE.pop(oldest_key, None)
    from services.datastore import VIBE_SEARCH_CACHE_TTL
    _MEMORY_CACHE[cache_key] = (time.time() + VIBE_SEARCH_CACHE_TTL, payload)


# ---------------------------------------------------------------------------
# Provider adapters (strict timeout, structured JSON responses)
# ---------------------------------------------------------------------------

def _extract_json(text: Any) -> Dict[str, Any]:
    """Extracts the first JSON object from an LLM completion, tolerating markdown fences."""
    s = safe_str(text).strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end <= start:
        raise VibeLLMError("No JSON object found in LLM response")
    try:
        parsed = json.loads(s[start:end + 1])
    except (ValueError, TypeError) as e:
        raise VibeLLMError(f"Invalid JSON from LLM: {e}")
    if not isinstance(parsed, dict):
        raise VibeLLMError("LLM JSON payload is not an object")
    return parsed


def _call_mistral(kind: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Mistral AI chat-completions adapter (Mistral Small 4 compiler / Ministral 3 14B reranker)."""
    api_key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not api_key:
        raise VibeLLMError("MISTRAL_API_KEY not configured")
    model = os.environ.get(
        "MISTRAL_RERANKER_MODEL" if kind == "rerank" else "MISTRAL_COMPILER_MODEL",
        DEFAULT_MISTRAL_RERANKER_MODEL if kind == "rerank" else DEFAULT_MISTRAL_COMPILER_MODEL,
    )
    try:
        res = requests.post(
            MISTRAL_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 250 if kind == "rerank" else 150,
                "response_format": {"type": "json_object"},
            },
            timeout=_llm_timeout(),
        )
    except requests.RequestException as e:
        raise VibeLLMError(f"Mistral request failed: {type(e).__name__}: {e}")
    if res.status_code != 200:
        raise VibeLLMError(f"Mistral HTTP {res.status_code}")
    try:
        content = res.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise VibeLLMError(f"Unexpected Mistral response shape: {e}")
    return _extract_json(content)


def _call_gemini(kind: str, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Gemini generateContent adapter (gemini-2.5-flash-lite), JSON response mime enforced."""
    api_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")).strip()
    if not api_key:
        raise VibeLLMError("GEMINI_API_KEY not configured")
    model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    try:
        res = requests.post(
            GEMINI_API_URL.format(model=model),
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2,
                    "maxOutputTokens": 250 if kind == "rerank" else 150,
                },
            },
            timeout=_llm_timeout(),
        )
    except requests.RequestException as e:
        raise VibeLLMError(f"Gemini request failed: {type(e).__name__}: {e}")
    if res.status_code != 200:
        raise VibeLLMError(f"Gemini HTTP {res.status_code}")
    try:
        content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as e:
        raise VibeLLMError(f"Unexpected Gemini response shape: {e}")
    return _extract_json(content)


_PROVIDER_CALLERS = {"mistral": _call_mistral, "gemini": _call_gemini}


# ---------------------------------------------------------------------------
# Schema validation & intent merging
# ---------------------------------------------------------------------------

def _validated_str_list(value: Any, cap: int, field: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise VibeLLMError(f"LLM field '{field}' must be an array")
    out = []
    for item in value[:cap]:
        s = safe_str(item).strip()
        if s:
            out.append(s)
    return out


def _validated_era(value: Any) -> Optional[int]:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        era = int(float(value))
    except (ValueError, TypeError):
        return None
    return era if 1900 <= era <= 2100 else None


def validate_compiler_intent(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validates and clamps the Vibe Compiler JSON schema (Option 1)."""
    return {
        "macro_genres": _validated_str_list(data.get("macro_genres"), 4, "macro_genres"),
        "moods": [m.lower() for m in _validated_str_list(data.get("moods"), 6, "moods")],
        "excluded_moods": [m.lower() for m in _validated_str_list(data.get("excluded_moods"), 6, "excluded_moods")],
        "expanded_terms": _validated_str_list(data.get("expanded_terms"), MAX_EXPANDED_TERMS, "expanded_terms"),
        "era_min": _validated_era(data.get("era_min")),
        "era_max": _validated_era(data.get("era_max")),
    }


def validate_rerank_output(data: Dict[str, Any], valid_ids: set) -> List[Dict[str, str]]:
    """Validates reranker JSON and deterministically discards hallucinated album_ids (Option 3)."""
    ranked = data.get("ranked")
    if not isinstance(ranked, list):
        raise VibeLLMError("LLM rerank field 'ranked' must be an array")
    validated = []
    for item in ranked[:MAX_RERANK_ENTRIES]:
        if not isinstance(item, dict):
            continue
        album_id = safe_str(item.get("album_id")).strip()
        if not album_id or album_id not in valid_ids:
            logger.debug("Discarded hallucinated or blank album_id from reranker: %r", album_id)
            continue
        validated.append({
            "album_id": album_id,
            "reason": safe_str(item.get("reason")).strip()[:MAX_REASON_CHARS],
        })
    return validated


def _merge_intents(heuristic_intent: Dict[str, Any], llm_intent: Dict[str, Any]) -> Dict[str, Any]:
    """Merges validated LLM compiler output into the heuristic intent for the deterministic scorer."""
    merged = dict(heuristic_intent)
    merged["moods"] = llm_intent["moods"]
    merged["excluded_moods"] = llm_intent["excluded_moods"]
    genres = list(heuristic_intent.get("macro_genres") or [])
    for genre in llm_intent["macro_genres"]:
        if genre not in genres and len(genres) < 4:
            genres.append(genre)
    merged["macro_genres"] = genres
    if llm_intent["era_min"] or llm_intent["era_max"]:
        merged["decade_range"] = [llm_intent["era_min"] or 1900, llm_intent["era_max"] or 2100]
    if llm_intent["expanded_terms"]:
        merged["clean_vibe_query"] = (
            f"{safe_str(heuristic_intent.get('clean_vibe_query'))} "
            f"{' '.join(llm_intent['expanded_terms'])}"
        ).strip()
        merged["llm_expanded_terms"] = llm_intent["expanded_terms"]
    return merged


# ---------------------------------------------------------------------------
# Payload assembly & sanitization (zero NaN guarantee)
# ---------------------------------------------------------------------------

def _sanitize_payload(obj: Any) -> Any:
    """Recursively removes NaN/inf floats and converts tuples to JSON-safe lists."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else 0.0
    if isinstance(obj, dict):
        return {safe_str(k): _sanitize_payload(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_payload(x) for x in obj]
    return obj


def _compact_album_row(album: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the compact metadata row sent to the reranker (Profile B, ~1.5k tokens for 30 rows)."""
    moods = album.get("derived_moods")
    moods_str = ", ".join(str(m) for m in moods) if isinstance(moods, (list, tuple)) else safe_str(moods)
    return {
        "album_id": safe_str(album.get("album_id") or album.get("canonical_album_key") or album.get("key") or ""),
        "artist": safe_str(album.get("album_artist_name", album.get("artist_name", ""))),
        "album": safe_str(album.get("album_name", "")),
        "year": safe_int(album.get("release_year", album.get("year")), 0),
        "macro_genre": safe_str(album.get("macro_genre", "")),
        "moods": safe_str(moods_str),
        "plays": safe_float(album.get("album_plays", album.get("total_plays", 0.0))),
    }


def _heuristic_payload(user_id: str, query: str, scope: str, horizon: str, top_k: int) -> Dict[str, Any]:
    """Deterministic fallback payload from the existing MiniLM/heuristic ranker."""
    from services.vibe_search import search_user_crate
    results, intent = search_user_crate(user_id, query, scope=scope, horizon=horizon, top_k=top_k)
    return {
        "query": query,
        "detected_intent": intent,
        "results_count": len(results),
        "results": results,
        "engine": "heuristic",
        "fallback": False,
        "cached": False,
    }


# ---------------------------------------------------------------------------
# LLM pipelines (Option 1 compiler & Option 3 reranker)
# ---------------------------------------------------------------------------

def _run_llm_pipeline(user_id: str, query: str, scope: str, horizon: str,
                      provider: str, mode: str, top_k: int) -> Dict[str, Any]:
    from services.vibe_search import fetch_candidate_pool, extract_query_intent, search_user_crate
    pool = fetch_candidate_pool(user_id, scope, horizon)
    if not pool:
        return _heuristic_payload(user_id, query, scope, horizon, top_k)
    caller = _PROVIDER_CALLERS[provider]

    if mode == "rerank":
        base_results, base_intent = search_user_crate(
            user_id, query, scope=scope, horizon=horizon,
            top_k=RERANK_POOL_SIZE,
            candidate_pool=pool,
        )
        rows = [_compact_album_row(a) for a in base_results]
        valid_ids = {row["album_id"] for row in rows if row["album_id"]}
        user_prompt = f"Vibe request: {query}\nCandidates:\n{json.dumps(rows, ensure_ascii=False)}"
        ranked = validate_rerank_output(caller("rerank", _RERANK_SYSTEM_PROMPT, user_prompt), valid_ids)

        by_id = {}
        for row, album in zip(rows, base_results):
            by_id[row["album_id"]] = album
        ordered, seen = [], set()
        for entry in ranked:
            album = dict(by_id[entry["album_id"]])
            album["llm_reason"] = entry["reason"]
            ordered.append(album)
            seen.add(entry["album_id"])
        for row, album in zip(rows, base_results):
            if row["album_id"] not in seen:
                ordered.append(album)
        return {
            "query": query,
            "detected_intent": base_intent,
            "results_count": len(ordered[:top_k]),
            "results": ordered[:top_k],
            "engine": f"{provider}:rerank",
            "fallback": False,
            "cached": False,
        }

    heuristic_intent = extract_query_intent(query, catalog=pool)
    user_prompt = f"Vibe request: {query}\nLibrary scope: {scope}\nTime horizon: {horizon}"
    llm_intent = validate_compiler_intent(caller("compiler", _COMPILER_SYSTEM_PROMPT, user_prompt))
    merged_intent = _merge_intents(heuristic_intent, llm_intent)
    results, intent = search_user_crate(
        user_id, query, scope=scope, horizon=horizon, top_k=top_k,
        candidate_pool=pool, precomputed_intent=merged_intent,
    )
    return {
        "query": query,
        "detected_intent": intent,
        "results_count": len(results),
        "results": results,
        "engine": f"{provider}:compiler",
        "fallback": False,
        "cached": False,
    }


def llm_vibe_search(user_id: str, query: str, scope: str = "saved", horizon: str = "all_time",
                    provider: Optional[str] = "auto", mode: Optional[str] = "compiler",
                    top_k: int = 15) -> Dict[str, Any]:
    """
    Entry point for the LLM-upgraded Vibe Digger (APP-19).

    Order of operations: in-memory cache -> Datastore VibeSearchCache -> LLM pipeline
    (Option 1 compiler by default, Option 3 rerank when requested) -> deterministic
    heuristic fallback on any provider failure. Cached hits skip the LLM entirely
    (~80-130ms); successful LLM responses are cached with TTL. Never raises.
    """
    resolved_provider, resolved_mode = resolve_provider_mode(provider, mode)
    if resolved_provider is None:
        return _sanitize_payload(_heuristic_payload(user_id, query, scope, horizon, top_k))

    cache_key = build_cache_key(user_id, query, scope, horizon, resolved_provider, resolved_mode)

    cached = _memory_get(cache_key)
    if cached is None:
        from services.datastore import get_vibe_search_from_datastore
        cached = get_vibe_search_from_datastore(user_id, cache_key)
        if cached is not None:
            _memory_set(cache_key, cached)
    if cached is not None:
        payload = dict(cached)
        payload["cached"] = True
        return _sanitize_payload(payload)

    try:
        payload = _run_llm_pipeline(user_id, query, scope, horizon, resolved_provider, resolved_mode, top_k)
    except Exception as e:
        logger.warning("[%s] Vibe LLM (%s/%s) failed, falling back to heuristic ranker: %s",
                       user_id, resolved_provider, resolved_mode, e)
        payload = _heuristic_payload(user_id, query, scope, horizon, top_k)
        payload["fallback"] = True
        payload["fallback_reason"] = safe_str(e)
        return _sanitize_payload(payload)

    payload = _sanitize_payload(payload)
    _memory_set(cache_key, payload)
    try:
        from services.datastore import save_vibe_search_to_datastore
        save_vibe_search_to_datastore(user_id, cache_key, payload)
    except Exception as e:
        logger.warning("[%s] Vibe search cache save failed: %s", user_id, e)
    return payload
