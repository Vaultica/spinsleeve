import os
import sys
import unittest
import gzip
import json
import datetime
from unittest.mock import patch, MagicMock

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    get_catalog_from_datastore,
    save_catalog_to_datastore,
    fetch_user_album_data,
    DATASTORE_CACHE_TTL,
    _user_album_cache
)


class TestDatastoreCatalogCache(unittest.TestCase):

    def setUp(self):
        # Clear in-memory caches between tests
        _user_album_cache.clear()

    def test_compression_decompression_roundtrip(self):
        sample_catalog = {
            "albums": [
                {
                    "album_id": "test1",
                    "album_name": "Kid A",
                    "album_artist_name": "Radiohead",
                    "release_year": "2000",
                    "album_tracks_total": 10,
                    "album_track_plays": 50,
                    "album_plays": 5.0,
                    "album_normalized_plays": 5,
                    "album_plays_display": "🔥 5 Plays",
                    "album_plays_tooltip": "Estimated complete album spins based on 50 track plays across 10 tracks",
                    "album_track_plays_30d": 20,
                    "album_plays_30d": 2.0,
                    "album_normalized_plays_30d": 2,
                    "album_plays_display_30d": "🔥 2 Plays (30D)",
                    "album_plays_tooltip_30d": "Estimated complete album spins in last 30 days based on 20 track plays across 10 tracks",
                    "has_gatefold": True
                }
            ],
            "top_genres": ["art rock", "electronic"],
            "kpis": {"total_albums": 1, "played_albums": 1, "total_plays": 50}
        }

        raw_json = json.dumps(sample_catalog)
        compressed = gzip.compress(raw_json.encode("utf-8"))
        self.assertLess(len(compressed), len(raw_json))

        decompressed = json.loads(gzip.decompress(compressed).decode("utf-8"))
        self.assertEqual(decompressed, sample_catalog)

    @patch("report_v2.app.get_datastore_client")
    def test_save_and_get_catalog_mocked(self, mock_ds_client_func):
        mock_ds = MagicMock()
        mock_ds_client_func.return_value = mock_ds

        stored_entities = {}

        def mock_put(entity):
            stored_entities[entity.key.name] = entity

        def mock_get(key):
            return stored_entities.get(key.name)

        def make_key(kind, name):
            k = MagicMock()
            k.name = name
            return k

        mock_ds.put.side_effect = mock_put
        mock_ds.get.side_effect = mock_get
        mock_ds.key.side_effect = make_key

        sample_data = {
            "albums": [{"album_name": "In Rainbows"}],
            "top_genres": ["rock"],
            "kpis": {"total_albums": 1}
        }

        # Save to Datastore
        save_catalog_to_datastore("user123", sample_data)
        self.assertIn("user123", stored_entities)
        saved_entity = stored_entities["user123"]
        self.assertIn("compressed_payload", saved_entity)
        self.assertIn("album_count", saved_entity)

        # Retrieve from Datastore
        retrieved = get_catalog_from_datastore("user123")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["albums"][0]["album_name"], "In Rainbows")

    @patch("report_v2.app.get_datastore_client")
    def test_get_catalog_expired_returns_none(self, mock_ds_client_func):
        mock_ds = MagicMock()
        mock_ds_client_func.return_value = mock_ds

        mock_entity = {
            "compressed_payload": gzip.compress(b'{"albums": []}'),
            # 2 days old
            "updated_at": datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)
        }
        mock_ds.get.return_value = mock_entity
        mock_ds.key.return_value = MagicMock()

        result = get_catalog_from_datastore("expired_user")
        self.assertIsNone(result)

    @patch("report_v2.app.get_catalog_from_datastore")
    @patch("report_v2.app.bigquery.Client")
    def test_fetch_user_album_data_tier2_cache_hit(self, mock_bq_client_class, mock_get_ds_catalog):
        mock_get_ds_catalog.return_value = {
            "albums": [{"album_name": "OK Computer", "album_plays_display": "🔥 10 Plays"}],
            "top_genres": ["alternative"],
            "kpis": {"total_albums": 1}
        }

        # Call fetch_user_album_data with empty in-memory cache
        res = fetch_user_album_data("cached_user")

        # Datastore cache was checked and hit
        mock_get_ds_catalog.assert_called_once_with("cached_user")
        # BigQuery client was NEVER instantiated!
        mock_bq_client_class.assert_not_called()
        self.assertEqual(res["albums"][0]["album_name"], "OK Computer")


if __name__ == "__main__":
    unittest.main()
