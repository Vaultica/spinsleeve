import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

# Add src/pipeline_v2 to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src", "pipeline_v2")))

import enrich


class TestEnrichV2(unittest.TestCase):

    def test_clean_search_term(self):
        cases = [
            ("OK Computer (OKNOTOK 1997 2017)", "OK Computer (OKNOTOK 1997 2017)"),
            ("Abbey Road (Remastered 2009)", "Abbey Road"),
            ("Nevermind (Deluxe Edition)", "Nevermind"),
            ("Rumours [2013 Remaster]", "Rumours"),
            ("Thriller (25th Anniversary Edition)", "Thriller"),
            ("Ten (Legacy Edition)", "Ten"),
        ]
        for raw, expected in cases:
            cleaned = enrich.clean_search_term(raw)
            self.assertEqual(cleaned, expected, f"Failed for '{raw}' -> got '{cleaned}', expected '{expected}'")

    @patch("enrich.requests.get")
    def test_fetch_wikipedia_data(self, mock_get):
        search_res = MagicMock()
        search_res.json.return_value = {
            "query": {
                "search": [{"title": "OK Computer"}]
            }
        }
        sum_res = MagicMock()
        sum_res.json.return_value = {
            "extract": "OK Computer is the third studio album by English rock band Radiohead.",
            "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/OK_Computer"}}
        }
        parse_res = MagicMock()
        parse_res.json.return_value = {
            "parse": {
                "wikitext": {
                    "*": """
                    {{Album ratings
                    | MC = 91/100
                    | rev1 = [[Pitchfork]]
                    | rev1score = 10/10
                    | rev2 = [[AllMusic]]
                    | rev2score = {{Rating|5|5}}
                    | rev3 = [[The Guardian]]
                    | rev3score = {{Rating|5|5}}
                    }}
                    """
                }
            }
        }

        mock_get.side_effect = [search_res, sum_res, parse_res]

        data = enrich.fetch_wikipedia_data("Radiohead", "OK Computer")
        self.assertIn("OK Computer is the third studio album", data["wiki_summary"])
        self.assertEqual(data["wiki_url"], "https://en.wikipedia.org/wiki/OK_Computer")
        self.assertEqual(data["pitchfork_score"], "10/10")
        self.assertEqual(data["metacritic_score"], "91/100")
        self.assertEqual(data["allmusic_score"], "5/5")
        self.assertEqual(data["guardian_score"], "5/5")

    @patch("enrich.time.sleep")
    @patch("enrich.requests.get")
    def test_fetch_discogs_data(self, mock_get, mock_sleep):
        search_res = MagicMock()
        search_res.json.return_value = {
            "results": [{"id": 12345}]
        }
        detail_res = MagicMock()
        detail_res.json.return_value = {
            "extraartists": [
                {"name": "Nigel Godrich", "role": "Producer"},
                {"name": "Chris Blair", "role": "Mastered By"}
            ],
            "community": {
                "rating": {"average": 4.82, "count": 12500}
            },
            "styles": ["Alternative Rock", "Art Rock"],
            "notes": "Recorded in St Catherine's Court, Bath."
        }

        mock_get.side_effect = [search_res, detail_res]

        data = enrich.fetch_discogs_data("Radiohead", "OK Computer")
        self.assertEqual(data["discogs_url"], "https://www.discogs.com/release/12345")
        self.assertIn("Nigel Godrich (Producer)", data["personnel"])
        self.assertIn("Chris Blair (Mastered By)", data["personnel"])
        self.assertEqual(data["discogs_rating"], 4.82)
        self.assertEqual(data["discogs_votes"], 12500.0)
        self.assertEqual(data["discogs_styles"], "Alternative Rock, Art Rock")
        self.assertEqual(data["discogs_notes"], "Recorded in St Catherine's Court, Bath.")

    @patch("enrich.time.sleep")
    @patch("enrich.requests.get")
    def test_fetch_musicbrainz_data(self, mock_get, mock_sleep):
        mb_res = MagicMock()
        mb_res.json.return_value = {
            "release-groups": [
                {
                    "id": "mb-rg-12345",
                    "title": "OK Computer",
                    "tags": [{"name": "art rock"}, {"name": "alternative rock"}],
                    "genres": [{"name": "rock"}]
                }
            ]
        }
        mock_get.return_value = mb_res

        data = enrich.fetch_musicbrainz_data("Radiohead", "OK Computer")
        self.assertEqual(data["musicbrainz_release_id"], "mb-rg-12345")
        self.assertIn("art rock", data["mb_tags"])
        self.assertIn("rock", data["mb_genres"])

    @patch("enrich.bigquery.Client")
    def test_run_enrichment_dry_run(self, mock_bq_cls):
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        # Mock candidate query results
        df_fake = pd.DataFrame([
            {
                "album_id": "test_id_123",
                "artist_name": "Radiohead",
                "album_name": "Kid A",
                "release_date": "2000-10-02",
                "release_year": "2000",
                "genres": "art rock, electronic",
                "total_plays": 25,
                "collector_count": 2
            }
        ])
        mock_bq.query.return_value.to_dataframe.return_value = df_fake

        with patch("enrich.fetch_wikipedia_data") as mock_wiki, \
             patch("enrich.fetch_discogs_data") as mock_discogs, \
             patch("enrich.fetch_musicbrainz_data") as mock_mb:
            mock_wiki.return_value = {"wiki_summary": "Summary text", "pitchfork_score": "10/10"}
            mock_discogs.return_value = {"discogs_rating": 4.9, "personnel": "Producer"}
            mock_mb.return_value = {"musicbrainz_release_id": "mb-123", "mb_genres": "electronic", "mb_tags": "ambient"}

            count = enrich.run_enrichment(batch_size=1, dry_run=True)
            self.assertEqual(count, 1)
            # Verify no BigQuery load job was executed on dry run
            self.assertFalse(mock_bq.load_table_from_json.called)

    @patch("enrich.bigquery.Client")
    def test_get_candidate_albums_re_enrich(self, mock_bq_cls):
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        # Verify query with re_enrich=True includes mb_scraped and min_quality_score
        mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame([{"album_id": "test_id_1"}])
        res = enrich.get_candidate_albums(mock_bq, batch_limit=5, re_enrich=True, min_quality_score=0.85)
        self.assertEqual(len(res), 1)

        # Check query string passed to BigQuery
        call_args = mock_bq.query.call_args
        query_sql = call_args[0][0]
        self.assertIn("enrichment_raw_musicbrainz", query_sql)
        self.assertIn("min_quality_score", query_sql)

    @patch("enrich.bigquery.Client")
    def test_get_candidate_albums_missing_gatefolds(self, mock_bq_cls):
        mock_bq = MagicMock()
        mock_bq_cls.return_value = mock_bq

        mock_bq.query.return_value.to_dataframe.return_value = pd.DataFrame([{"album_id": "test_id_mg"}])
        res = enrich.get_candidate_albums(mock_bq, batch_limit=5, missing_gatefolds=True)
        self.assertEqual(len(res), 1)

        call_args = mock_bq.query.call_args
        query_sql = call_args[0][0]
        self.assertIn("album_description IS NULL", query_sql)
        self.assertIn("personnel IS NULL", query_sql)
        self.assertIn("total_plays DESC", query_sql)


if __name__ == "__main__":
    unittest.main()
