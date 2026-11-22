"""
Unit test suite for Apple Music Backend Pipeline & JWT Ingestion Service (APP-02a).
Verifies:
1. ES256 developer bearer JWT minting, claim verification, and cryptographic signing.
2. Apple Music API pagination, rate limit (429), and auth rejection (401) handling.
3. Album normalization, canonical deduplication, artwork formatting, and zero-NaN safety.
4. BigQuery ingestion into user_saved_albums with QA table suffix (_app_02a).
5. Foreign provider bridging into album_provider_ids with provider='apple_music'.
6. Explicit Cloud Datastore cache invalidation (UserCatalogCache, UserAnalyticsCache, PalCompatibilityCache).
7. Flask REST routes (/api/apple-music/developer-token, /api/apple-music/sync) and backward-compatible /beta/* aliases.
"""

import os
import sys
import json
import time
import base64
import unittest
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import pandas as pd

from pipeline_v2.apple_music import (
    mint_developer_token,
    get_apple_developer_token,
    format_artwork_url,
    normalize_apple_music_album,
    parse_apple_music_library,
    fetch_apple_music_library_albums,
    sync_apple_music_saved_albums,
    invalidate_user_datastore_caches,
    AppleMusicAuthError,
    AppleMusicAPIError
)
from report_v2.app import app


class TestAppleMusicPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Generate an EC P-256 test key
        cls.ec_key = ec.generate_private_key(ec.SECP256R1())
        cls.pem_key = cls.ec_key.private_bytes(
            Encoding.PEM,
            PrivateFormat.PKCS8,
            NoEncryption()
        ).decode("utf-8")
        cls.test_key_id = "KEY1234567"
        cls.test_team_id = "TEAM123456"

    def test_mint_developer_token_structure_and_signature(self):
        """Verifies that mint_developer_token produces a valid ES256 JWT with correct claims and signature."""
        exp_seconds = 3600
        token = mint_developer_token(
            key_id=self.test_key_id,
            team_id=self.test_team_id,
            private_key_pem=self.pem_key,
            exp_seconds=exp_seconds
        )

        parts = token.split(".")
        self.assertEqual(len(parts), 3, "JWT must consist of header, payload, and signature segments")

        # Decode header
        header_raw = base64.urlsafe_b64decode(parts[0] + "=" * (-len(parts[0]) % 4))
        header = json.loads(header_raw.decode("utf-8"))
        self.assertEqual(header["alg"], "ES256")
        self.assertEqual(header["kid"], self.test_key_id)
        self.assertEqual(header["typ"], "JWT")

        # Decode payload
        payload_raw = base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        payload = json.loads(payload_raw.decode("utf-8"))
        self.assertEqual(payload["iss"], self.test_team_id)
        self.assertAlmostEqual(payload["iat"], int(time.time()), delta=5)
        self.assertEqual(payload["exp"], payload["iat"] + exp_seconds)

        # Verify cryptographic signature using public key
        sig_bytes = base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4))
        self.assertEqual(len(sig_bytes), 64, "P-256 signature must be 64 bytes (32 bytes r + 32 bytes s)")
        r = int.from_bytes(sig_bytes[:32], "big")
        s = int.from_bytes(sig_bytes[32:], "big")
        der_sig = encode_dss_signature(r, s)

        signing_input = f"{parts[0]}.{parts[1]}".encode("ascii")
        pub_key = self.ec_key.public_key()
        # verify() raises InvalidSignature if verification fails
        pub_key.verify(der_sig, signing_input, ec.ECDSA(hashes.SHA256()))

    def test_mint_developer_token_invalid_parameters(self):
        """Verifies that missing parameters raise ValueError."""
        with self.assertRaises(ValueError):
            mint_developer_token("", self.test_team_id, self.pem_key)
        with self.assertRaises(ValueError):
            mint_developer_token(self.test_key_id, "", self.pem_key)
        with self.assertRaises(ValueError):
            mint_developer_token(self.test_key_id, self.test_team_id, "")

    @patch("pipeline_v2.apple_music.get_secret")
    def test_get_apple_developer_token_caching(self, mock_get_secret):
        """Verifies get_apple_developer_token caches the minted token to avoid redundant signing."""
        def secret_side_effect(name, default=""):
            if "KEY_ID" in name:
                return self.test_key_id
            if "TEAM_ID" in name:
                return self.test_team_id
            if "PRIVATE_KEY" in name:
                return self.pem_key
            return default

        mock_get_secret.side_effect = secret_side_effect

        token1 = get_apple_developer_token(force_refresh=True)
        token2 = get_apple_developer_token(force_refresh=False)
        self.assertEqual(token1, token2)

    def test_format_artwork_url(self):
        """Verifies Apple Music artwork URL template replacement."""
        template = "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/xx/yy/zz/{w}x{h}bb.{f}"
        resolved = format_artwork_url(template, width=800, height=800, fmt="jpg")
        self.assertEqual(resolved, "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/xx/yy/zz/800x800bb.jpg")

        self.assertEqual(format_artwork_url(None), "")
        self.assertEqual(format_artwork_url(""), "")

    def test_normalize_apple_music_album(self):
        """Verifies normalization to user_saved_albums schema, canonical keys, and zero-NaN safety."""
        item = {
            "id": "l.AbCd123",
            "type": "library-albums",
            "attributes": {
                "name": "OK Computer (Deluxe Edition)",
                "artistName": "Radiohead",
                "trackCount": 12,
                "releaseDate": "1997-05-21",
                "artwork": {
                    "url": "https://is1-ssl.mzstatic.com/image/thumb/{w}x{h}bb.{f}"
                },
                "genreNames": ["Alternative", "Rock"],
                "dateAdded": "2024-02-10T15:30:00Z",
                "recordLabel": "XL Recordings"
            },
            "relationships": {
                "artists": {
                    "data": [{"id": "r.Radiohead1", "type": "library-artists"}]
                }
            }
        }

        row = normalize_apple_music_album(item, "user_apple_1")
        self.assertEqual(row["user_id"], "user_apple_1")
        self.assertEqual(row["album_id"], "l.AbCd123")
        self.assertEqual(row["album_name"], "OK Computer (Deluxe Edition)")
        self.assertEqual(row["artist_name"], "Radiohead")
        self.assertEqual(row["artist_id"], "r.Radiohead1")
        self.assertEqual(row["release_year"], 1997)
        self.assertEqual(row["tracks_total"], 12)
        self.assertEqual(row["label"], "XL Recordings")
        self.assertEqual(row["genres"], "Alternative, Rock")
        self.assertEqual(row["platform"], "apple_music")
        # Canonical deduplication should strip (Deluxe Edition)
        self.assertEqual(row["canonical_album_key"], "radiohead::ok computer")
        self.assertEqual(row["image_url"], "https://is1-ssl.mzstatic.com/image/thumb/600x600bb.jpg")

    def test_parse_apple_music_library_empty_and_valid(self):
        """Verifies DataFrame conversion and empty collection handling."""
        empty_df = parse_apple_music_library([], "user_1")
        self.assertTrue(empty_df.empty)
        self.assertIn("canonical_album_key", empty_df.columns)
        self.assertIn("platform", empty_df.columns)

        valid_items = [
            {
                "id": "l.1",
                "attributes": {
                    "name": "Album One",
                    "artistName": "Artist One",
                    "trackCount": 10,
                    "releaseDate": "2020-01-01"
                }
            }
        ]
        df = parse_apple_music_library(valid_items, "user_1")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["canonical_album_key"], "artist one::album one")
        self.assertEqual(df.iloc[0]["platform"], "apple_music")

    @patch("pipeline_v2.apple_music.requests.get")
    def test_fetch_apple_music_library_albums_pagination(self, mock_get):
        """Verifies multi-page fetching via 'next' pagination."""
        page1 = {
            "data": [{"id": "l.1", "attributes": {"name": "A1"}}],
            "next": "/v1/me/library/albums?offset=1"
        }
        page2 = {
            "data": [{"id": "l.2", "attributes": {"name": "A2"}}]
        }

        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = page1

        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = page2

        mock_get.side_effect = [mock_resp1, mock_resp2]

        albums = fetch_apple_music_library_albums(
            music_user_token="test_user_token",
            developer_token="test_dev_token"
        )
        self.assertEqual(len(albums), 2)
        self.assertEqual(albums[0]["id"], "l.1")
        self.assertEqual(albums[1]["id"], "l.2")

    @patch("pipeline_v2.apple_music.requests.get")
    def test_fetch_apple_music_library_albums_auth_and_rate_limit_errors(self, mock_get):
        """Verifies HTTP 401 raises AppleMusicAuthError and HTTP 429 raises AppleMusicAPIError."""
        # 401 Unauthorized
        mock_401 = MagicMock()
        mock_401.status_code = 401
        mock_401.text = "Unauthorized"
        mock_get.return_value = mock_401

        with self.assertRaises(AppleMusicAuthError):
            fetch_apple_music_library_albums("bad_token", developer_token="dev_tok")

        # 429 Rate Limit
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.text = "Too Many Requests"
        mock_get.return_value = mock_429

        with self.assertRaises(AppleMusicAPIError):
            fetch_apple_music_library_albums("tok", developer_token="dev_tok")

    @patch("pipeline_v2.apple_music.fetch_apple_music_library_albums")
    @patch("pipeline_v2.apple_music.invalidate_user_datastore_caches")
    def test_sync_apple_music_saved_albums_isolated_qa(self, mock_invalidate, mock_fetch):
        """Verifies ingestion into QA isolated table user_saved_albums_app_02a and provider bridging."""
        mock_fetch.return_value = [
            {
                "id": "l.new1",
                "attributes": {
                    "name": "New Album",
                    "artistName": "New Artist",
                    "trackCount": 10,
                    "releaseDate": "2023-01-01"
                }
            },
            {
                "id": "l.existing2",
                "attributes": {
                    "name": "Existing Album",
                    "artistName": "Existing Artist",
                    "trackCount": 8,
                    "releaseDate": "2021-01-01"
                }
            }
        ]

        # Mock BigQuery Client
        mock_bq = MagicMock()
        # df_existing returns existing album 'l.existing2'
        mock_query_job = MagicMock()
        mock_query_job.to_dataframe.return_value = pd.DataFrame([{"album_id": "l.existing2"}])
        mock_bq.query.return_value = mock_query_job

        mock_load_job = MagicMock()
        mock_load_job.result.return_value = None
        mock_bq.load_table_from_dataframe.return_value = mock_load_job
        mock_bq.load_table_from_json.return_value = mock_load_job

        mock_ds = MagicMock()

        result = sync_apple_music_saved_albums(
            user_id="user_apple_qa",
            music_user_token="user_tok",
            bq_client=mock_bq,
            ds_client=mock_ds,
            table_suffix="_app_02a"
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["new_albums"], 1)
        self.assertEqual(result["total_synced"], 2)

        # Verify BigQuery load target table has _app_02a suffix
        load_call_args = mock_bq.load_table_from_dataframe.call_args
        target_table = load_call_args[0][1]
        self.assertTrue(target_table.endswith("user_saved_albums_app_02a"))

        # Verify provider bridging called with _app_02a suffix
        provider_call_args = mock_bq.load_table_from_json.call_args
        provider_rows = provider_call_args[0][0]
        provider_table = provider_call_args[0][1]
        self.assertTrue(provider_table.endswith("album_provider_ids_app_02a"))
        self.assertEqual(len(provider_rows), 1)
        self.assertEqual(provider_rows[0]["provider"], "apple_music")
        self.assertEqual(provider_rows[0]["external_album_id"], "l.new1")

        # Verify Datastore cache invalidation was triggered
        mock_invalidate.assert_called_once_with("user_apple_qa", mock_ds)

    def test_invalidate_user_datastore_caches(self):
        """Verifies explicit cache deletion on UserCatalogCache, UserAnalyticsCache, and PalCompatibilityCache."""
        mock_ds = MagicMock()
        mock_analytics_entity = MagicMock()
        mock_analytics_entity.key.name = "user123::30d"

        mock_pal_entity = MagicMock()
        mock_pal_entity.key.name = "user123::pal456::30d"

        mock_ds.query.side_effect = [
            MagicMock(fetch=MagicMock(return_value=[mock_analytics_entity])),
            MagicMock(fetch=MagicMock(return_value=[mock_pal_entity]))
        ]

        invalidate_user_datastore_caches("user123", ds_client=mock_ds)

        # Verify UserCatalogCache key deletion
        mock_ds.delete.assert_called_once()
        # Verify multi-deletions on analytics and pals
        self.assertEqual(mock_ds.delete_multi.call_count, 2)

    @patch("routes.apple_music.get_developer_token")
    def test_route_developer_token_success_and_beta_alias(self, mock_get_token):
        """Verifies /api/apple-music/developer-token and /beta/... alias."""
        mock_get_token.return_value = "mock_jwt_developer_token_123"

        with app.test_client() as client:
            res1 = client.get("/api/apple-music/developer-token")
            self.assertEqual(res1.status_code, 200)
            data1 = res1.get_json()
            self.assertEqual(data1["developer_token"], "mock_jwt_developer_token_123")

            res2 = client.get("/beta/api/apple-music/developer-token")
            self.assertEqual(res2.status_code, 200)
            data2 = res2.get_json()
            self.assertEqual(data2["developer_token"], "mock_jwt_developer_token_123")

    @patch("routes.apple_music.get_developer_token")
    def test_route_developer_token_unconfigured(self, mock_get_token):
        """Verifies HTTP 503 response when developer credentials are unconfigured."""
        mock_get_token.side_effect = ValueError("Missing credentials")

        with app.test_client() as client:
            res = client.get("/api/apple-music/developer-token")
            self.assertEqual(res.status_code, 503)
            data = res.get_json()
            self.assertEqual(data["status"], "error")

    @patch("routes.apple_music.sync_apple_music_library")
    def test_route_sync_library_auth_and_execution(self, mock_sync):
        """Verifies /api/apple-music/sync route requires login and executes sync on valid token."""
        mock_sync.return_value = {
            "status": "success",
            "new_albums": 5,
            "total_synced": 20
        }

        with app.test_client() as client:
            # 1. Unauthenticated request -> redirects to /login (via @login_required)
            res_unauth = client.post("/api/apple-music/sync")
            self.assertEqual(res_unauth.status_code, 302)

            # 2. Authenticated without token -> 400 Bad Request
            with client.session_transaction() as sess:
                sess["user_id"] = "user_am_test"

            res_no_tok = client.post("/api/apple-music/sync", json={})
            self.assertEqual(res_no_tok.status_code, 400)

            # 3. Authenticated with token in body -> 200 OK
            res_ok = client.post(
                "/api/apple-music/sync",
                json={"music_user_token": "valid_user_tok"}
            )
            self.assertEqual(res_ok.status_code, 200)
            data_ok = res_ok.get_json()
            self.assertEqual(data_ok["new_albums"], 5)
            mock_sync.assert_called_once_with(
                user_id="user_am_test",
                music_user_token="valid_user_tok",
                table_suffix=""
            )

            # 4. Authenticated with token in header & QA suffix -> 200 OK
            mock_sync.reset_mock()
            res_header = client.post(
                "/beta/api/apple-music/sync",
                headers={
                    "Music-User-Token": "header_user_tok",
                    "X-Table-Suffix": "_app_02a"
                }
            )
            self.assertEqual(res_header.status_code, 200)
            mock_sync.assert_called_once_with(
                user_id="user_am_test",
                music_user_token="header_user_tok",
                table_suffix="_app_02a"
            )

    @patch("routes.apple_music.sync_apple_music_library")
    def test_route_sync_library_auth_and_api_errors(self, mock_sync):
        """Verifies HTTP 401 on AppleMusicAuthError and HTTP 502 on AppleMusicAPIError."""
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = "user_am_test"

            # 401 when token invalid/expired
            mock_sync.side_effect = AppleMusicAuthError("Invalid user token")
            res_auth_err = client.post(
                "/api/apple-music/sync",
                json={"music_user_token": "expired_tok"}
            )
            self.assertEqual(res_auth_err.status_code, 401)

            # 502 on Apple API failure
            mock_sync.side_effect = AppleMusicAPIError("Apple Music service unavailable")
            res_api_err = client.post(
                "/api/apple-music/sync",
                json={"music_user_token": "tok"}
            )
            self.assertEqual(res_api_err.status_code, 502)


if __name__ == "__main__":
    unittest.main()
