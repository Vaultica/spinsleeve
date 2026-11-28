#!/usr/bin/env python3
"""
SpinSleeve Vibe Digger LLM Evaluation Harness (APP-19 LLM Upgrade)
-------------------------------------------------------------------
Benchmarks ~20 tricky vibe queries across available engines:
  - heuristic  : existing MiniLM/heuristic hybrid ranker (vibe_search.py)
  - mistral    : LLM "Vibe Compiler" / reranker via Mistral (MISTRAL_API_KEY)
  - gemini     : LLM "Vibe Compiler" / reranker via Gemini (GEMINI_API_KEY)

Usage:
  # Full comparison (heuristic always runs; LLM engines run only when keys are set):
  .venv/bin/python3 scripts/eval_vibe_llm.py

  # Restrict engines and modes:
  .venv/bin/python3 scripts/eval_vibe_llm.py --engines heuristic,mistral --modes compiler,rerank

  # Single query:
  .venv/bin/python3 scripts/eval_vibe_llm.py --query "rainy Tokyo midnight jazz that isn't sleepy"

  # Offline mode: reuse the scripts/.cache_vibe catalog snapshot instead of BigQuery:
  .venv/bin/python3 scripts/eval_vibe_llm.py --offline

Outputs a Markdown comparison table (top-3 per engine, latency, engine/fallback flag)
for manual relevance scoring alongside the latency/cost model in the APP-19 spec.
"""
import os
import sys
import json
import time
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache_vibe")

VIBE_EVAL_QUERIES = [
    "rainy day jazz piano with trumpet",
    "rainy Tokyo midnight jazz that isn't sleepy",
    "90s slowcore with whispery vocals and sad guitars",
    "upbeat japanese city pop for a summer drive",
    "dark hypnotic techno with modular synths",
    "aggressive early 80s hardcore punk under 2 minutes vibes",
    "warm acoustic guitar on a sunny porch, nothing electronic",
    "sparse solo piano for a 3am insomnia session",
    "ethereal female vocals over glitchy ambient textures",
    "funky bassline for a late night drive, but no disco",
    "blue note records with a vintage hard bop sound",
    "something like Talk Talk but more abstract and layered",
    "critically acclaimed 90s electronic masterpieces",
    "records I've been playing a lot recently that feel euphoric",
    "unplayed ambient albums in my crate for a meditation morning",
    "dusty soul 45s with raw horns, pre-1975 only",
    "post-rock crescendos that never get heavy",
    "hypnotic kalimba or mbira patterns, modern production",
    "melancholic orchestral strings for a film noir montage",
    "ecm-style spacious jazz that isn't cold or sterile",
]


def load_offline_catalog_patch():
    """Patches services.catalog fetchers with the local eval snapshot (no BigQuery calls)."""
    catalog_file = os.path.join(CACHE_DIR, "catalog_cache.json")
    if not os.path.exists(catalog_file):
        print(f"[!] Offline snapshot missing: {catalog_file}. Run scripts/eval_vibe_search.py once first.")
        sys.exit(1)
    with open(catalog_file, "r", encoding="utf-8") as f:
        albums = json.load(f)
    albums = [dict(a, album_id=a.get("album_id") or a.get("key") or "") for a in albums]

    from services import catalog
    catalog.fetch_user_album_data = lambda user_id, force_refresh=False: {
        "albums": albums, "top_genres": [], "kpis": {}
    }
    catalog.fetch_unowned_album_data = lambda user_id, horizon="all": []


def run_engine(engine: str, mode: str, user_id: str, query: str, top_k: int):
    """Executes one query on one engine; returns (payload, latency_ms)."""
    from services.vibe_llm import llm_vibe_search
    started = time.perf_counter()
    payload = llm_vibe_search(
        user_id, query, scope="saved", horizon="all_time",
        provider=engine, mode=mode, top_k=top_k,
    )
    latency_ms = (time.perf_counter() - started) * 1000.0
    return payload, latency_ms


def fmt_top3(payload):
    lines = []
    for i, r in enumerate(payload.get("results", [])[:3], 1):
        artist = r.get("album_artist_name", r.get("artist_name", "?"))
        reason = r.get("llm_reason") or ""
        suffix = f" — {reason}" if reason else ""
        lines.append(f"{i}. {artist} - *{r.get('album_name', '?')}*{suffix}")
    return "<br>".join(lines) or "_no results_"


def main():
    parser = argparse.ArgumentParser(description="APP-19 Vibe Digger LLM evaluation harness")
    parser.add_argument("--query", help="Evaluate a single query instead of the full suite")
    parser.add_argument("--engines", default="heuristic,mistral,gemini",
                        help="Comma-separated: heuristic,mistral,gemini")
    parser.add_argument("--modes", default="compiler", help="Comma-separated: compiler,rerank")
    parser.add_argument("--offline", action="store_true", help="Use local catalog snapshot")
    parser.add_argument("--user", default="sergebou", help="User ID for candidate pool")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    if args.offline:
        load_offline_catalog_patch()

    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]

    available = {"heuristic": True}
    available["mistral"] = bool(os.environ.get("MISTRAL_API_KEY", "").strip())
    available["gemini"] = bool(os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", ""))

    active = []
    for engine in engines:
        if not available.get(engine):
            print(f"[!] Skipping {engine}: no API key configured")
            continue
        for mode in modes:
            active.append((engine, "heuristic" if engine == "heuristic" else mode))

    queries = [args.query] if args.query else VIBE_EVAL_QUERIES

    try:
        from services.vibe_search import warmup_vibe_engine
        warmup_vibe_engine()
    except Exception as e:
        print(f"[!] Vibe engine warmup notice: {e}")

    print(f"| Query | Engine | Mode | Top-3 | Latency (ms) | Fallback |")
    print(f"| :--- | :--- | :--- | :--- | ---: | :--- |")
    for query in queries:
        for engine, mode in active:
            try:
                payload, latency_ms = run_engine(engine, mode, args.user, query, args.top_k)
                print(f"| {query} | {payload.get('engine', engine)} | {mode} | "
                      f"{fmt_top3(payload)} | {latency_ms:.0f} | {payload.get('fallback', False)} |")
            except Exception as e:
                print(f"| {query} | {engine}:{mode} | {mode} | ERROR: {e} | - | - |")


if __name__ == "__main__":
    main()
