"""
Unit tests for Spotify streaming history parser (APP-13).
"""

import unittest
import pandas as pd
from src.pipeline_v2.history_parser import parse_spotify_history_json

class TestHistoryParser(unittest.TestCase):

    def test_parse_extended_format(self):
        sample_data = [
            {
                "ts": "2024-01-15T12:34:56Z",
                "ms_played": 210000,
                "master_metadata_track_name": "Test Song",
                "master_metadata_album_artist_name": "Test Artist",
                "master_metadata_album_album_name": "Test Album",
                "spotify_track_uri": "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"
            },
            {
                "ts": "2024-01-15T13:00:00Z",
                "ms_played": 10000,  # Under 30s - should be filtered out
                "master_metadata_track_name": "Short Skip",
                "master_metadata_album_artist_name": "Test Artist",
                "master_metadata_album_album_name": "Test Album",
                "spotify_track_uri": "spotify:track:short"
            },
            {
                "ts": "2024-01-15T13:10:00Z",
                "ms_played": 180000,
                "episode_name": "Podcast Episode",  # Podcast - should be filtered out
                "spotify_episode_uri": "spotify:episode:123"
            }
        ]

        df = parse_spotify_history_json(sample_data, "user_123")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["track_name"], "Test Song")
        self.assertEqual(df.iloc[0]["artist_name"], "Test Artist")
        self.assertEqual(df.iloc[0]["album_name"], "Test Album")
        self.assertEqual(df.iloc[0]["track_id"], "4iV5W9uYEdYUVa79Axb7Rh")
        self.assertEqual(df.iloc[0]["user_id"], "user_123")

    def test_parse_legacy_format(self):
        sample_data = [
            {
                "endTime": "2023-11-08 14:32",
                "artistName": "Legacy Artist",
                "trackName": "Legacy Track",
                "msPlayed": 200000
            }
        ]

        df = parse_spotify_history_json(sample_data, "user_456")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["track_name"], "Legacy Track")
        self.assertEqual(df.iloc[0]["artist_name"], "Legacy Artist")
        self.assertEqual(df.iloc[0]["album_name"], "Unknown Album")
        self.assertEqual(df.iloc[0]["user_id"], "user_456")

if __name__ == "__main__":
    unittest.main()
