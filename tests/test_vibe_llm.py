"""
Tests for APP-19 LLM Vibe Digger upgrade (`services/vibe_llm.py`).

Verifies:
- Provider abstraction & resolution (Mistral / Gemini adapters, off switch, defaults).
- Strict JSON schema validation for the Vibe Compiler and the Top-N reranker.
- Hallucinated album_id grounding (any ID outside the candidate pool is discarded).
- Datastore + in-memory cache hit/miss behavior keyed on normalized query/scope/horizon.
- Deterministic fallback to the heuristic/MiniLM ranker on missing keys, timeouts,
  HTTP errors, and invalid JSON.
- Zero NaN/inf leakage into JSON payloads (safe_str / safe_int / safe_float).
- Route integration (/api/crate/vibe-search) staying thin with provider/mode params.
"""

import os
import sys
import json
import math
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from services import vibe_llm
from services.vibe_llm import (
    VibeLLMError,
    llm_vibe_search,
    resolve_provider_mode,
    build_cache_key,
    validate_compiler_intent,
    validate_rerank_output,
    _extract_json,
    _sanitize_payload,
    _merge_intents,
)
from app import app

MOCK_ALBUMS = [
    {
        "album_id": "alb_1",
        "album_name": "Nocturne",
        "album_artist_name": "Night Trio",
        "macro_genre": "Jazz",
        "derived_moods": ["Nocturnal", "Calm"],
        "album_plays": 4.0,
        "album_plays_30d": 1.0,
        "release_year": "1975",
        "album_description": "smoky late night jazz piano",
    },
    {
        "album_id": "alb_2",
        "album_name": "Sunburst",
        "album_artist_name": "Day Ensemble",
        "macro_genre": "Jazz",
        "derived_moods": ["Energetic", "Uplifting"],
        "album_plays": 9.0,
        "album_plays_30d": 0.0,
        "release_year": "2015",
        "album_description": "bright energetic big band",
    },
    {
        "album_id": "alb_3",
        "album_name": "Static Bloom",
        "album_artist_name": "Moss",
        "macro_genre": "Ambient",
        "derived_moods": ["Hypnotic"],
        "album_plays": 0.0,
        "album_plays_30d": 0.0,
        "release_year": "2003",
        "album_description": "drone textures",
    },
]

COMPILER_JSON = json.dumps({
    "macro_genres": ["Jazz"],
    "moods": ["nocturnal", "smoky"],
    "era_min": 1960,
    "era_max": 1980,
    "excluded_moods": ["energetic"],
    "expanded_terms": ["late night", "smoky club"],
})


class TestProviderResolution(unittest.TestCase):

    def test_default_resolves_to_mistral_compiler(self):
        with patch.dict(os.environ, {"VIBE_LLM_PROVIDER": ""}, clear=False):
            self.assertEqual(resolve_provider_mode("auto", None), ("mistral", "compiler"))

    def test_explicit_provider_and_mode(self):
        self.assertEqual(resolve_provider_mode("gemini", "rerank"), ("gemini", "rerank"))

    def test_off_and_unknown_providers_disable_llm(self):
        for value in ("off", "none", "heuristic", "bogus-llm"):
            self.assertEqual(resolve_provider_mode(value, "compiler")[0], None)

    def test_invalid_mode_falls_back_to_compiler(self):
        self.assertEqual(resolve_provider_mode("mistral", "hologram"), ("mistral", "compiler"))

    def test_env_provider_override(self):
        with patch.dict(os.environ, {"VIBE_LLM_PROVIDER": "gemini"}):
            self.assertEqual(resolve_provider_mode("auto", None), ("gemini", "compiler"))


class TestCacheKey(unittest.TestCase):

    def test_normalization_lower_trim_collapse(self):
        key = build_cache_key("u1", "  Rainy   DAY Jazz ", " saved ", "all_time", "mistral", "compiler")
        self.assertEqual(key, "u1::rainy day jazz::saved::all_time::mistral::compiler")

    def test_distinct_scopes_produce_distinct_keys(self):
        a = build_cache_key("u1", "jazz", "saved", "30d", "mistral", "compiler")
        b = build_cache_key("u1", "jazz", "unowned", "30d", "mistral", "compiler")
        self.assertNotEqual(a, b)


class TestJsonExtractionAndValidation(unittest.TestCase):

    def test_extract_json_plain(self):
        self.assertEqual(_extract_json('{"a": 1}'), {"a": 1})

    def test_extract_json_markdown_fenced(self):
        self.assertEqual(_extract_json('```json\n{"a": 1}\n```'), {"a": 1})

    def test_extract_json_with_prose(self):
        self.assertEqual(_extract_json('Here you go: {"a": [1, 2]} done.'), {"a": [1, 2]})

    def test_extract_json_missing_raises(self):
        with self.assertRaises(VibeLLMError):
            _extract_json("no json here at all")

    def test_compiler_validation_valid(self):
        intent = validate_compiler_intent({
            "macro_genres": ["Jazz", "Ambient"],
            "moods": ["Nocturnal", "SMOKY"],
            "era_min": "1965",
            "era_max": 1980,
            "excluded_moods": ["Energetic"],
            "expanded_terms": ["late night piano"],
        })
        self.assertEqual(intent["macro_genres"], ["Jazz", "Ambient"])
        self.assertEqual(intent["moods"], ["nocturnal", "smoky"])
        self.assertEqual(intent["era_min"], 1965)
        self.assertEqual(intent["era_max"], 1980)
        self.assertEqual(intent["excluded_moods"], ["energetic"])

    def test_compiler_validation_rejects_non_list_genres(self):
        with self.assertRaises(VibeLLMError):
            validate_compiler_intent({"macro_genres": "Jazz"})

    def test_compiler_validation_era_clamped(self):
        intent = validate_compiler_intent({"era_min": 42, "era_max": 9999})
        self.assertIsNone(intent["era_min"])
        self.assertIsNone(intent["era_max"])

    def test_compiler_validation_caps_lists(self):
        intent = validate_compiler_intent({
            "expanded_terms": [f"term{i}" for i in range(20)],
            "moods": [f"mood{i}" for i in range(20)],
        })
        self.assertEqual(len(intent["expanded_terms"]), vibe_llm.MAX_EXPANDED_TERMS)
        self.assertEqual(len(intent["moods"]), 6)

    def test_rerank_filters_hallucinated_ids(self):
        valid = {"alb_1", "alb_2"}
        ranked = validate_rerank_output({
            "ranked": [
                {"album_id": "alb_2", "reason": "fits"},
                {"album_id": "hallucinated_9", "reason": "made up"},
                {"album_id": "", "reason": "blank"},
                {"album_id": "alb_1", "reason": "also fits"},
            ]
        }, valid)
        self.assertEqual([r["album_id"] for r in ranked], ["alb_2", "alb_1"])

    def test_rerank_rejects_non_list_ranked(self):
        with self.assertRaises(VibeLLMError):
            validate_rerank_output({"ranked": "alb_1"}, {"alb_1"})


class TestMergeIntents(unittest.TestCase):

    def test_merge_adds_llm_fields_and_era(self):
        heuristic = {
            "macro_genres": ["Jazz"], "clean_vibe_query": "midnight", "decade_range": None,
            "specific_year": None, "instruments": [], "label": None, "telemetry_scope": None,
            "critical_acclaim": False, "intensity_mode": None, "artist": None,
            "moods": [], "excluded_moods": [], "normalized_query": "midnight", "raw_query": "midnight",
        }
        merged = _merge_intents(heuristic, {
            "macro_genres": ["Ambient", "Jazz"],
            "moods": ["nocturnal"],
            "excluded_moods": ["sleepy"],
            "expanded_terms": ["rain", "moody saxophone"],
            "era_min": 1990, "era_max": 1999,
        })
        self.assertEqual(merged["macro_genres"], ["Jazz", "Ambient"])
        self.assertEqual(merged["moods"], ["nocturnal"])
        self.assertEqual(merged["excluded_moods"], ["sleepy"])
        self.assertEqual(merged["decade_range"], [1990, 1999])
        self.assertIn("moody saxophone", merged["clean_vibe_query"])
        self.assertEqual(merged["llm_expanded_terms"], ["rain", "moody saxophone"])


class TestProviderAdapters(unittest.TestCase):

    def _mistral_response(self, content):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": content}}]}
        return resp

    def test_mistral_missing_key_raises(self):
        env = {k: "" for k in ("MISTRAL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(VibeLLMError):
                vibe_llm._call_mistral("compiler", "sys", "user")

    @patch("services.vibe_llm.requests.post")
    def test_mistral_success(self, mock_post):
        mock_post.return_value = self._mistral_response('{"moods": ["calm"]}')
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            data = vibe_llm._call_mistral("compiler", "sys", "user")
        self.assertEqual(data, {"moods": ["calm"]})
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["timeout"], 2.5)
        self.assertEqual(kwargs["json"]["model"], vibe_llm.DEFAULT_MISTRAL_COMPILER_MODEL)

    @patch("services.vibe_llm.requests.post")
    def test_mistral_http_error_raises(self, mock_post):
        mock_post.return_value = MagicMock(status_code=503)
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with self.assertRaises(VibeLLMError):
                vibe_llm._call_mistral("compiler", "sys", "user")

    @patch("services.vibe_llm.requests.post", side_effect=__import__("requests").exceptions.Timeout)
    def test_mistral_timeout_raises(self, mock_post):
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with self.assertRaises(VibeLLMError):
                vibe_llm._call_mistral("compiler", "sys", "user")

    @patch("services.vibe_llm.requests.post")
    def test_mistral_rerank_uses_reranker_model(self, mock_post):
        mock_post.return_value = self._mistral_response('{"ranked": []}')
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            vibe_llm._call_mistral("rerank", "sys", "user")
        self.assertEqual(mock_post.call_args.kwargs["json"]["model"], vibe_llm.DEFAULT_MISTRAL_RERANKER_MODEL)

    @patch("services.vibe_llm.requests.post")
    def test_gemini_success(self, mock_post):
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"candidates": [{"content": {"parts": [{"text": '{"macro_genres": ["Jazz"]}'}]}}]}
        mock_post.return_value = resp
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            data = vibe_llm._call_gemini("compiler", "sys", "user")
        self.assertEqual(data, {"macro_genres": ["Jazz"]})
        self.assertIn("gemini-2.5-flash-lite", mock_post.call_args.args[0])

    @patch("services.vibe_llm.requests.post")
    def test_gemini_http_error_raises(self, mock_post):
        mock_post.return_value = MagicMock(status_code=429)
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            with self.assertRaises(VibeLLMError):
                vibe_llm._call_gemini("compiler", "sys", "user")


class TestLLMVibeSearchOption1(unittest.TestCase):

    def setUp(self):
        vibe_llm._MEMORY_CACHE.clear()

    def tearDown(self):
        vibe_llm._MEMORY_CACHE.clear()

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_compiler_pipeline_scores_with_llm_intent(self, mock_fetch, mock_unowned,
                                                      mock_post, mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": COMPILER_JSON}}]}
        mock_post.return_value = resp

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key", "VIBE_LLM_PROVIDER": "mistral"}):
            payload = llm_vibe_search("u1", "smoky late night jazz", provider="mistral", mode="compiler", top_k=3)

        self.assertEqual(payload["engine"], "mistral:compiler")
        self.assertFalse(payload["fallback"])
        self.assertFalse(payload["cached"])
        self.assertEqual(payload["detected_intent"]["moods"], ["nocturnal", "smoky"])
        self.assertEqual(payload["detected_intent"]["excluded_moods"], ["energetic"])
        self.assertEqual(payload["detected_intent"]["decade_range"], [1960, 1980])
        self.assertGreaterEqual(mock_post.call_count, 1)
        mock_ds_save.assert_called_once()

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_excluded_mood_demotes_album(self, mock_fetch, mock_unowned, mock_post,
                                         mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": COMPILER_JSON}}]}
        mock_post.return_value = resp

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "smoky late night jazz", provider="mistral", top_k=3)

        names = [r["album_name"] for r in payload["results"]]
        self.assertNotEqual(names.index("Sunburst"), 0,
                            "Energetic album demoted by excluded_moods")
        top = payload["results"][0]
        self.assertTrue(any("+Mood" in r or "-Excluded Mood" in r for r in top["vibe_reasons"]))

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post", side_effect=__import__("requests").exceptions.Timeout)
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_fallback_on_timeout(self, mock_fetch, mock_unowned, mock_post,
                                 mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "jazz", provider="mistral", top_k=3)

        self.assertTrue(payload["fallback"])
        self.assertEqual(payload["engine"], "heuristic")
        self.assertIn("timeout", payload["fallback_reason"].lower())
        self.assertTrue(len(payload["results"]) > 0)

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_fallback_on_invalid_json(self, mock_fetch, mock_unowned, mock_post,
                                      mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": "not valid json {"}}]}
        mock_post.return_value = resp
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "jazz", provider="mistral", top_k=3)
        self.assertTrue(payload["fallback"])

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_fallback_on_missing_api_key(self, mock_fetch, mock_unowned, mock_post,
                                         mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        env = {k: "" for k in ("MISTRAL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")}
        with patch.dict(os.environ, env, clear=False):
            payload = llm_vibe_search("u1", "jazz", provider="mistral", top_k=3)
        self.assertTrue(payload["fallback"])
        mock_post.assert_not_called()


class TestLLMVibeSearchOption3Rerank(unittest.TestCase):

    def setUp(self):
        vibe_llm._MEMORY_CACHE.clear()

    def tearDown(self):
        vibe_llm._MEMORY_CACHE.clear()

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_rerank_reorders_and_grounds_ids(self, mock_fetch, mock_unowned, mock_post,
                                             mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": json.dumps({
            "ranked": [
                {"album_id": "alb_3", "reason": "hypnotic drone matches"},
                {"album_id": "alb_1", "reason": "nocturnal jazz fits"},
                {"album_id": "hallucinated_id", "reason": "ignored"},
            ]
        })}}]}
        mock_post.return_value = resp

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "hypnotic nocturnal textures",
                                      provider="mistral", mode="rerank", top_k=3)

        self.assertEqual(payload["engine"], "mistral:rerank")
        names = [r["album_name"] for r in payload["results"]]
        self.assertEqual(names[:2], ["Static Bloom", "Nocturne"])
        self.assertEqual(payload["results"][0]["llm_reason"], "hypnotic drone matches")
        self.assertNotIn("hallucinated_id", [r.get("album_id") for r in payload["results"]])

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_rerank_appends_unranked_pool_albums(self, mock_fetch, mock_unowned, mock_post,
                                                 mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": json.dumps({
            "ranked": [{"album_id": "alb_1", "reason": "best fit"}]
        })}}]}
        mock_post.return_value = resp
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "jazz", provider="mistral", mode="rerank", top_k=3)
        self.assertEqual(len(payload["results"]), 3)
        self.assertEqual(payload["results"][0]["album_id"], "alb_1")


class TestVibeCacheBehavior(unittest.TestCase):

    def setUp(self):
        vibe_llm._MEMORY_CACHE.clear()

    def tearDown(self):
        vibe_llm._MEMORY_CACHE.clear()

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_memory_cache_hit_skips_llm(self, mock_fetch, mock_unowned, mock_post,
                                        mock_ds_get, mock_ds_save):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": COMPILER_JSON}}]}
        mock_post.return_value = resp

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            first = llm_vibe_search("u1", "smoky late night jazz", provider="mistral", top_k=3)
            second = llm_vibe_search("u1", "  SMOKY   late night jazz ", provider="mistral", top_k=3)

        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(mock_post.call_count, 1, "LLM must not be called on cache hit")
        self.assertEqual(first["results"], second["results"])

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore")
    @patch("services.vibe_llm.requests.post")
    def test_datastore_cache_hit_skips_llm(self, mock_post, mock_ds_get, mock_ds_save):
        cached_payload = {
            "query": "jazz", "detected_intent": {}, "results_count": 1,
            "results": [{"album_id": "alb_1", "album_name": "Nocturne",
                         "album_artist_name": "Night Trio", "vibe_score": 0.9}],
            "engine": "gemini:compiler", "fallback": False, "cached": False,
        }
        mock_ds_get.return_value = cached_payload
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "jazz", provider="gemini", top_k=3)
        self.assertTrue(payload["cached"])
        self.assertEqual(payload["engine"], "gemini:compiler")
        mock_post.assert_not_called()
        mock_ds_save.assert_not_called()

    def test_normalized_keys_differ_by_provider_and_mode(self):
        a = build_cache_key("u1", "Jazz", "saved", "all_time", "mistral", "compiler")
        b = build_cache_key("u1", "jazz", "saved", "all_time", "gemini", "compiler")
        c = build_cache_key("u1", "jazz", "saved", "all_time", "mistral", "rerank")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)

    @patch("services.vibe_search.get_query_embedding", return_value=None)
    @patch("services.datastore.get_datastore_client")
    def test_invalidate_vibe_cache_deletes_user_keys(self, mock_ds_func, mock_emb):
        from services.datastore import invalidate_user_catalog_cache
        mock_ds = MagicMock()
        mock_ds_func.return_value = mock_ds
        entity = MagicMock()
        entity.key.name = "u1::jazz::saved::all_time::mistral::compiler"
        mock_ds.query.return_value.fetch.return_value = [entity]

        invalidate_user_catalog_cache("u1")

        mock_ds.delete.assert_called_once()
        mock_ds.delete_multi.assert_called_once()
        deleted = mock_ds.delete_multi.call_args.args[0]
        self.assertEqual(deleted, [entity.key])


class TestNaNAndPayloadSafety(unittest.TestCase):

    def test_sanitize_payload_removes_nan_inf(self):
        dirty = {"a": float("nan"), "b": float("inf"), "c": [float("nan"), 1.5],
                 "d": (1990, 1999), "e": "ok", None: "x"}
        clean = _sanitize_payload(dirty)
        self.assertEqual(clean["a"], 0.0)
        self.assertEqual(clean["b"], 0.0)
        self.assertEqual(clean["c"], [0.0, 1.5])
        self.assertEqual(clean["d"], [1990, 1999])
        self.assertEqual(clean["e"], "ok")
        self.assertIn("", clean)
        json.dumps(clean, allow_nan=False)

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_llm_payload_is_nan_free_json(self, mock_fetch, mock_unowned, mock_post,
                                          mock_ds_get, mock_ds_save):
        dirty_albums = json.loads(json.dumps(MOCK_ALBUMS))
        dirty_albums[0]["album_plays"] = float("nan")
        mock_fetch.return_value = {"albums": dirty_albums}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": COMPILER_JSON}}]}
        mock_post.return_value = resp
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            payload = llm_vibe_search("u1", "smoky jazz", provider="mistral", top_k=3)
        json.dumps(payload, allow_nan=False)
        for result in payload["results"]:
            self.assertFalse(math.isnan(float(result.get("vibe_score", 0.0))))


class TestVibeSearchAPIRoute(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()
        vibe_llm._MEMORY_CACHE.clear()

    def tearDown(self):
        vibe_llm._MEMORY_CACHE.clear()

    def test_api_vibe_search_unauthorized(self):
        res = self.client.get("/api/crate/vibe-search?q=jazz")
        self.assertIn(res.status_code, (302, 401))

    @patch("services.datastore.save_vibe_search_to_datastore")
    @patch("services.datastore.get_vibe_search_from_datastore", return_value=None)
    @patch("services.vibe_llm.requests.post")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    @patch("services.catalog.fetch_user_album_data")
    def test_api_route_with_provider_and_mode(self, mock_fetch, mock_unowned, mock_post,
                                              mock_ds_save, mock_ds_get):
        mock_fetch.return_value = {"albums": MOCK_ALBUMS}
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": COMPILER_JSON}}]}
        mock_post.return_value = resp
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key"}):
            with self.client.session_transaction() as sess:
                sess["user_id"] = "route_user"
            res = self.client.get("/beta/api/crate/vibe-search?q=smoky%20jazz&provider=mistral&mode=compiler")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["engine"], "mistral:compiler")
        self.assertIn("fallback", data)
        self.assertIn("cached", data)
        self.assertEqual(data["results_count"], len(data["results"]))

    @patch("services.vibe_search.search_user_crate")
    def test_api_route_heuristic_mode_uses_ranker_directly(self, mock_search):
        mock_search.return_value = (
            [{"album_name": "Test Album", "album_artist_name": "Test Artist", "vibe_score": 0.85}],
            {"label": None, "clean_vibe_query": "ambient chill"}
        )
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_user"
        res = self.client.get("/beta/api/crate/vibe-search?q=ambient%20chill&provider=heuristic")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["engine"], "heuristic")
        self.assertFalse(data["fallback"])
        mock_search.assert_called_once()


class TestEvalHarnessQueries(unittest.TestCase):

    def test_eval_suite_defines_twenty_tricky_queries(self):
        spec_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "eval_vibe_llm.py"))
        import importlib.util
        spec = importlib.util.spec_from_file_location("eval_vibe_llm", spec_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(len(module.VIBE_EVAL_QUERIES), 20)
        for query in module.VIBE_EVAL_QUERIES:
            self.assertIsInstance(query, str)
            self.assertGreater(len(query.strip()), 5)


if __name__ == "__main__":
    unittest.main()
