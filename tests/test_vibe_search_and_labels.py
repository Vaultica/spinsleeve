"""
Tests for APP-19 Vibe Search & Gatefold Record Label Integration.

Verifies:
- Intent extraction for iconic labels, listening telemetry, acclaim, and intensity.
- In-memory hybrid ranker and user crate slicing.
- Flask API route /api/crate/vibe-search and /beta/api/crate/vibe-search.
- UI elements in recommend.html and gatefold record label badges.
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "report_v2")))

from services.vibe_search import extract_query_intent, normalize_query, search_user_crate
from app import app, BETA_RECOMMEND_HTML, BETA_EXPLORER_HTML


class TestVibeSearchIntent(unittest.TestCase):

    def test_typo_normalization(self):
        self.assertEqual(normalize_query("aggresive and chaotique records!"), "aggressive and chaotic records!")
        self.assertEqual(normalize_query("psychedlic jazzy rock"), "psychedelic jazz rock")

    def test_intent_blue_note_vintage(self):
        intent = extract_query_intent("blue notes records with a vintage sound")
        self.assertEqual(intent["label"], "Blue Note")
        self.assertIn("vintage sound", intent["clean_vibe_query"])

    def test_intent_telemetry_recent(self):
        intent = extract_query_intent("jazz albums I have been listening to recently")
        self.assertEqual(intent["telemetry_scope"], "recent")
        self.assertIn("Jazz", intent["macro_genres"])
        self.assertEqual(intent["clean_vibe_query"], "jazz")

    def test_intent_critical_acclaim(self):
        intent = extract_query_intent("critically acclaimed records")
        self.assertTrue(intent["critical_acclaim"])

    def test_intent_intensity_high(self):
        intent = extract_query_intent("aggresive and chaotic records!")
        self.assertEqual(intent["intensity_mode"], "high")

    def test_intent_artist_matching(self):
        catalog = [
            {"album_artist_name": "Talk Talk", "album_name": "Spirit of Eden"},
            {"album_artist_name": "BADBADNOTGOOD", "album_name": "Talk Memory"},
        ]
        intent = extract_query_intent("talk talk album with a tree on the sleeve cover", catalog=catalog)
        self.assertEqual(intent["artist"], "Talk Talk")


class TestVibeSearchService(unittest.TestCase):

    def setUp(self):
        self.mock_albums = [
            {
                "album_id": "alb_1",
                "album_name": "Drums Around The Corner",
                "album_artist_name": "Art Blakey",
                "album_label": "Blue Note Records",
                "macro_genre": "Jazz",
                "album_plays_30d": 0.0,
                "album_plays": 12.0,
                "discogs_rating": 4.5,
                "release_year": "1961"
            },
            {
                "album_id": "alb_2",
                "album_name": "Stay Safe!",
                "album_artist_name": "La Sécurité",
                "album_label": "Ray-On",
                "macro_genre": "Punk / Alternative",
                "album_plays_30d": 3.0,
                "album_plays": 5.0,
                "discogs_rating": 4.1,
                "release_year": "2023"
            },
            {
                "album_id": "alb_3",
                "album_name": "Orange Wine",
                "album_artist_name": "Okvsho",
                "album_label": "Boyoom Connective",
                "macro_genre": "Jazz",
                "album_plays_30d": 2.4,
                "album_plays": 15.0,
                "discogs_rating": 4.3,
                "release_year": "2021"
            }
        ]

    @patch("services.catalog.fetch_user_album_data")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    def test_search_user_crate_label_match(self, mock_unowned, mock_fetch):
        mock_fetch.return_value = {"albums": self.mock_albums}
        results, intent = search_user_crate("test_user", "blue notes records with a vintage sound")

        self.assertEqual(intent["label"], "Blue Note")
        self.assertTrue(len(results) > 0)
        # Art Blakey on Blue Note must rank #1
        self.assertEqual(results[0]["album_name"], "Drums Around The Corner")
        self.assertIn("vibe_score", results[0])
        self.assertTrue(any("+Label" in r for r in results[0]["vibe_reasons"]))

    @patch("services.catalog.fetch_user_album_data")
    @patch("services.catalog.fetch_unowned_album_data", return_value=[])
    def test_search_user_crate_recent_jazz(self, mock_unowned, mock_fetch):
        mock_fetch.return_value = {"albums": self.mock_albums}
        results, intent = search_user_crate("test_user", "jazz albums I have been listening to recently")

        self.assertEqual(intent["telemetry_scope"], "recent")
        self.assertTrue(len(results) > 0)
        # Okvsho has recent plays in Jazz
        self.assertEqual(results[0]["album_name"], "Orange Wine")
        self.assertTrue(any("+Recent" in r for r in results[0]["vibe_reasons"]))


class TestVibeSearchAPI(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_api_vibe_search_unauthorized(self):
        res = self.client.get("/api/crate/vibe-search?q=jazz")
        # Login required redirects to login or 302
        self.assertIn(res.status_code, (302, 401))

    @patch("services.vibe_search.search_user_crate")
    def test_api_vibe_search_authorized(self, mock_search):
        mock_search.return_value = (
            [{"album_name": "Test Album", "album_artist_name": "Test Artist", "vibe_score": 0.85}],
            {"label": None, "clean_vibe_query": "ambient chill"}
        )
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_user"

        res = self.client.get("/beta/api/crate/vibe-search?q=ambient%20chill")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["query"], "ambient chill")
        self.assertEqual(data["results_count"], 1)
        self.assertEqual(data["results"][0]["album_name"], "Test Album")


class TestVibeSearchUIElements(unittest.TestCase):

    def test_recommend_html_contains_vibe_digger(self):
        self.assertIn('id="vibeSearchInput"', BETA_RECOMMEND_HTML)
        self.assertIn('id="vibeDigBtn"', BETA_RECOMMEND_HTML)
        self.assertIn('id="vibeClearBtn"', BETA_RECOMMEND_HTML)
        self.assertIn('id="vibeIntentBanner"', BETA_RECOMMEND_HTML)
        self.assertIn('executeVibeSearch', BETA_RECOMMEND_HTML)
        self.assertIn('applyVibeChip', BETA_RECOMMEND_HTML)
        self.assertIn('clearVibeSearch', BETA_RECOMMEND_HTML)

    def test_explorer_html_contains_vibe_digger(self):
        self.assertIn('id="vibeSearchInput"', BETA_EXPLORER_HTML)
        self.assertIn('id="vibeDigBtn"', BETA_EXPLORER_HTML)
        self.assertIn('id="vibeClearBtn"', BETA_EXPLORER_HTML)
        self.assertIn('id="vibeIntentBanner"', BETA_EXPLORER_HTML)
        self.assertIn('executeVibeSearch', BETA_EXPLORER_HTML)
        self.assertIn('applyVibeChip', BETA_EXPLORER_HTML)
        self.assertIn('clearVibeSearch', BETA_EXPLORER_HTML)


if __name__ == "__main__":
    unittest.main()
