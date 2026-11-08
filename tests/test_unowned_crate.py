import os
import sys
import unittest
import jinja2

# Add src to path for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from report_v2.app import (
    BETA_EXPLORER_HTML,
    ICON_A_SVG,
    ICON_GATEFOLD_SVG
)


class TestUnownedCrate(unittest.TestCase):

    def test_explorer_template_contains_unowned_crate_elements(self):
        self.assertIn("You Should Save These", BETA_EXPLORER_HTML)
        self.assertIn("switchCrateTab", BETA_EXPLORER_HTML)
        self.assertIn("Streamed", BETA_EXPLORER_HTML)
        self.assertIn("Save to Library", BETA_EXPLORER_HTML)

    def test_unowned_tab_rendering_logic(self):
        self.assertIn("savedVinylView", BETA_EXPLORER_HTML)
        self.assertIn("unownedVinylView", BETA_EXPLORER_HTML)
        self.assertIn("unownedAlbumGrid", BETA_EXPLORER_HTML)


if __name__ == "__main__":
    unittest.main()
