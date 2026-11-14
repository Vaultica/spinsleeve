import os
import sys
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    app,
    APP_VERSION,
    BETA_EXPLORER_HTML,
    BETA_RECOMMEND_HTML,
    BETA_ANALYTICS_HTML,
    BETA_PALS_HTML
)
from report_v2.services.avatars import AVATAR_PRESETS, AVATAR_SVGS


class TestAvatarPersonaPicker(unittest.TestCase):
    """Unit test suite for APP-04: Music Legend Illustrated Avatar Persona Picker."""

    def setUp(self):
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_roster_contains_twelve_legends(self):
        """Verify the avatar presets roster contains exactly 12 curated legends."""
        self.assertEqual(len(AVATAR_PRESETS), 12)
        expected_ids = {
            "beethoven", "chet_baker", "miles_davis", "bob_dylan",
            "david_bowie", "stevie_wonder", "jimi_hendrix", "fela_kuti",
            "madonna", "amy_winehouse", "daft_punk", "drake"
        }
        roster_ids = {p["id"] for p in AVATAR_PRESETS}
        self.assertEqual(roster_ids, expected_ids)

    def test_each_preset_has_metadata_fields(self):
        """Verify each preset has id, name, era, badge, and description."""
        for preset in AVATAR_PRESETS:
            self.assertIn("id", preset)
            self.assertIn("name", preset)
            self.assertIn("era", preset)
            self.assertIn("badge", preset)
            self.assertIn("desc", preset)
            self.assertTrue(len(preset["name"]) > 0)
            self.assertTrue(len(preset["era"]) > 0)

    def test_each_svg_is_valid_xml(self):
        """Verify every legend SVG string parses as valid XML and contains a viewBox."""
        for preset in AVATAR_PRESETS:
            preset_id = preset["id"]
            self.assertIn(preset_id, AVATAR_SVGS)
            svg_str = AVATAR_SVGS[preset_id]
            # Must parse without syntax errors
            root = ET.fromstring(svg_str)
            self.assertTrue(root.tag.endswith("svg"))
            self.assertIn("viewBox", root.attrib)
            self.assertEqual(root.attrib["viewBox"], "0 0 100 100")

    def test_serve_avatar_routes(self):
        """Verify GET /avatar/<id>.svg and GET /avatar/<id> return HTTP 200 with SVG mimetype."""
        for preset_id in ["david_bowie", "chet_baker", "daft_punk"]:
            res_svg = self.client.get(f"/avatar/{preset_id}.svg")
            self.assertEqual(res_svg.status_code, 200)
            self.assertIn("image/svg+xml", res_svg.content_type)
            self.assertIn("<svg", res_svg.data.decode("utf-8"))

            res_plain = self.client.get(f"/avatar/{preset_id}")
            self.assertEqual(res_plain.status_code, 200)
            self.assertIn("image/svg+xml", res_plain.content_type)

    def test_serve_nonexistent_avatar_404(self):
        """Non-existent avatar presets must return 404."""
        res = self.client.get("/avatar/non_existent_artist.svg")
        self.assertEqual(res.status_code, 404)

    def test_update_avatar_unauthenticated_fails(self):
        """POST /api/user/avatar without session user_id on production host redirects to /login."""
        # Supply X-Forwarded-Host to bypass the local dev auth bypass
        res = self.client.post(
            "/api/user/avatar",
            json={"avatar_id": "david_bowie"},
            headers={"X-Forwarded-Host": "spinsleeve.cc"}
        )
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers["Location"].endswith("/login"))

    @patch("services.datastore.get_datastore_client")
    def test_update_avatar_authenticated_success(self, mock_get_ds):
        """POST /api/user/avatar updates user's custom_avatar_id and avatar_url."""
        mock_ds = MagicMock()
        mock_user = {
            "spotify_id": "test_user_1",
            "display_name": "Test User",
            "spotify_avatar_url": "https://spotify.com/photo.jpg",
            "custom_avatar_id": ""
        }
        mock_ds.get.return_value = mock_user
        mock_get_ds.return_value = mock_ds

        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_user_1"
            sess["display_name"] = "Test User"
            sess["role"] = "user"

        res = self.client.post("/api/user/avatar", json={"avatar_id": "david_bowie"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["avatar_id"], "david_bowie")
        self.assertEqual(data["avatar_url"], "/avatar/david_bowie.svg")

        # Verify Datastore put was invoked and updated the dict
        mock_ds.put.assert_called_once()
        self.assertEqual(mock_user["custom_avatar_id"], "david_bowie")
        self.assertEqual(mock_user["avatar_url"], "/avatar/david_bowie.svg")

    @patch("services.datastore.get_datastore_client")
    def test_revert_to_spotify_avatar(self, mock_get_ds):
        """POST /api/user/avatar with 'spotify' clears custom_avatar_id."""
        mock_ds = MagicMock()
        mock_user = {
            "spotify_id": "test_user_1",
            "display_name": "Test User",
            "spotify_avatar_url": "https://spotify.com/photo.jpg",
            "custom_avatar_id": "chet_baker"
        }
        mock_ds.get.return_value = mock_user
        mock_get_ds.return_value = mock_ds

        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_user_1"
            sess["display_name"] = "Test User"
            sess["role"] = "user"
            sess["custom_avatar_id"] = "chet_baker"

        res = self.client.post("/api/user/avatar", json={"avatar_id": "spotify"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["avatar_id"], "")
        self.assertEqual(data["avatar_url"], "https://spotify.com/photo.jpg")

        self.assertEqual(mock_user["custom_avatar_id"], "")
        self.assertEqual(mock_user["avatar_url"], "https://spotify.com/photo.jpg")

    def test_update_avatar_invalid_id_returns_400(self):
        """POST /api/user/avatar with invalid avatar_id must return 400."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = "test_user_1"
            sess["display_name"] = "Test User"
            sess["role"] = "user"

        res = self.client.post("/api/user/avatar", json={"avatar_id": "invalid_artist_999"})
        self.assertEqual(res.status_code, 400)

    def test_templates_render_avatar_dropdown_widget(self):
        """Verify templates render avatarPickerDropdown and music legend presets."""
        templates = {
            "explorer": BETA_EXPLORER_HTML,
            "recommend": BETA_RECOMMEND_HTML,
            "analytics": BETA_ANALYTICS_HTML,
            "pals": BETA_PALS_HTML
        }
        context = {
            "user": {
                "display_name": "Serge",
                "user_id": "sergebou",
                "avatar_url": "/avatar/david_bowie.svg",
                "custom_avatar_id": "david_bowie",
                "pals_opt_in": True
            },
            "is_admin": True,
            "is_impersonating": False,
            "app_version": APP_VERSION,
            "avatar_presets": AVATAR_PRESETS,
            "brand_icon": "",
            "gatefold_icon": "",
            "albums": [],
            "top_genres": [],
            "kpis": {"total_albums": 0, "unplayed_albums": 0, "played_albums": 0},
            "pals": [],
            "selected_pal": {"display_name": "Buddy", "spotify_id": "buddy1", "avatar_url": "", "album_count": 10},
            "compatibility": {
                "match_pct": 80,
                "kinship": {"tier": "Kin", "badge": "Kin", "color": "", "desc": ""},
                "artist_score": 80,
                "album_score": 80,
                "shared_artists_count": 0,
                "shared_albums_count": 0,
                "borrow_count": 0,
                "shared_artists": []
            },
            "top_borrow": [],
            "shared_albums": [],
            "pal_crate": []
        }

        for name, html in templates.items():
            with self.subTest(template=name):
                t = jinja2.Template(html)
                rendered = t.render(**context)
                self.assertIn("avatarPickerDropdown", rendered, f"avatarPickerDropdown missing in {name}")
                self.assertIn("Music Legend Persona", rendered, f"Header title missing in {name}")
                self.assertIn("David Bowie", rendered, f"David Bowie option missing in {name}")
                self.assertIn("selectAvatarPreset", rendered, f"selectAvatarPreset handler missing in {name}")


if __name__ == "__main__":
    unittest.main()
