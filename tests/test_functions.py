import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Add src/functions to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "functions")))

import main


class TestSpotifyFunctions(unittest.TestCase):

    def test_flatten_json(self):
        nested = {
            "track": {
                "id": "123",
                "name": "Song Name",
                "artists": [{"name": "Artist 1"}, {"name": "Artist 2"}]
            },
            "played_at": "2026-10-31T12:00:00.000Z"
        }
        flattened = main.flatten_json(nested)
        self.assertEqual(flattened.get("track_id"), "123")
        self.assertEqual(flattened.get("track_name"), "Song Name")
        self.assertEqual(flattened.get("track_artists_0_name"), "Artist 1")
        self.assertEqual(flattened.get("track_artists_1_name"), "Artist 2")
        self.assertEqual(flattened.get("played_at"), "2026-10-31T12:00:00.000Z")

    @patch("main.get_secret")
    def test_get_spotify_client_missing_credentials(self, mock_get_secret):
        mock_get_secret.return_value = None
        with self.assertRaises(ValueError) as ctx:
            main.get_spotify_client()
        self.assertIn("Missing SPOTIPY_CLIENT_ID", str(ctx.exception))

    @patch("main.get_secret")
    def test_get_spotify_client_missing_refresh_token(self, mock_get_secret):
        def fake_secret(key, default=None):
            if key in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET"):
                return "fake-value"
            return None

        mock_get_secret.side_effect = fake_secret
        with self.assertRaises(ValueError) as ctx:
            main.get_spotify_client()
        self.assertIn("Missing SPOTIPY_REFRESH_TOKEN", str(ctx.exception))

    @patch("main.bigquery.Client")
    def test_get_latest_played_timestamp(self, mock_bq_client):
        mock_instance = MagicMock()
        mock_bq_client.return_value = mock_instance
        mock_row = MagicMock()
        mock_row.max_played_at = "2026-10-31T12:00:00.000Z"
        mock_instance.query.return_value.result.return_value = [mock_row]

        epoch_ms = main.get_latest_played_timestamp(lookback_minutes=10)
        # 12:00:00 - 10m = 11:50:00
        expected_dt = main.pd.to_datetime("2026-10-31T11:50:00.000Z")
        expected_ms = int(expected_dt.timestamp() * 1000)
        self.assertEqual(epoch_ms, expected_ms)

    @patch("pandas_gbq.to_gbq")
    def test_load_tracks_bq(self, mock_to_gbq):
        sample_tracks = {
            "items": [
                {
                    "track": {
                        "name": "Test Track",
                        "album": {
                            "name": "Test Album",
                            "artists": [{"name": "Test Artist"}]
                        },
                        "type": "track",
                        "uri": "spotify:track:123"
                    },
                    "played_at": "2026-10-31T10:00:00.000Z"
                }
            ]
        }
        res = main.load_tracks_bq(sample_tracks)
        self.assertEqual(res, "dataset loaded to BQ")
        self.assertTrue(mock_to_gbq.called)

        # Verify DataFrame passed to to_gbq
        df_passed = mock_to_gbq.call_args[0][0]
        self.assertIn("track_name", df_passed.columns)
        self.assertIn("played_at", df_passed.columns)
        self.assertIn("track_album_artists_0_name", df_passed.columns)
        self.assertEqual(df_passed.iloc[0]["track_name"], "Test Track")

    @patch("pandas_gbq.to_gbq")
    def test_load_all_albums_bq(self, mock_to_gbq):
        sample_albums = [
            {
                "added_at": "2026-10-31T10:00:00Z",
                "album": {
                    "id": "alb123",
                    "name": "Sample Album",
                    "album_type": "album",
                    "label": "Test Label",
                    "release_date": "2026-01-01",
                    "total_tracks": 10,
                    "uri": "spotify:album:alb123",
                    "artists": [{"id": "art456", "name": "Sample Artist"}],
                    "images": [{"height": 640, "url": "https://example.com/cover.jpg", "width": 640}]
                }
            }
        ]
        genres_map = {"art456": "indie rock, post-punk"}
        res = main.load_all_albums_bq(sample_albums, artist_genres_map=genres_map)
        self.assertEqual(res, "dataset loaded to BQ")
        self.assertTrue(mock_to_gbq.called)

        df_passed = mock_to_gbq.call_args[0][0]
        self.assertIn("album_image_url", df_passed.columns)
        self.assertIn("album_genres", df_passed.columns)
        self.assertEqual(df_passed.iloc[0]["album_image_url"], "https://example.com/cover.jpg")
        self.assertEqual(df_passed.iloc[0]["album_genres"], "indie rock, post-punk")

    @patch("main.get_spotify_client")
    def test_get_recently_played_error_handling(self, mock_client):
        mock_client.side_effect = Exception("Spotify API 401 Unauthorized")
        response_body, status_code, headers = main.get_recently_played(None)

        self.assertEqual(status_code, 500)
        self.assertEqual(headers["Content-Type"], "application/json")
        data = json.loads(response_body)
        self.assertEqual(data["status"], "error")
        self.assertIn("Spotify API 401 Unauthorized", data["message"])


if __name__ == "__main__":
    unittest.main()
