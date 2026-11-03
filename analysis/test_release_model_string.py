"""The displayed model string must come from the live release's run metadata.

Incident guard (hygiene audit P2/P3): the About and Thematic pages once said
claude-opus-4-8 while the release pointer targeted the Fable 5 run, and the
Thematic tab's caveat banner later still said "Claude Opus". The
displayed model is now sourced from <classification_dir>/run_metadata.json via
dashboard.config.RELEASE_MODEL, with a visible placeholder when the metadata is
missing — it can match the live run or say it is unknown, never drift.
"""

import json
import unittest

from dashboard.config import (
    RELEASE_MODEL,
    RUN_METADATA_JSON,
    _RELEASE_MODEL_FALLBACK,
    _load_release_model,
)


class ReleaseModelStringTest(unittest.TestCase):
    def test_release_model_matches_live_run_metadata(self):
        with open(RUN_METADATA_JSON, encoding="utf-8") as f:
            recorded = str(json.load(f)["model"]).strip()
        self.assertTrue(recorded)
        self.assertEqual(RELEASE_MODEL, recorded)

    def test_layouts_render_the_release_model(self):
        from dashboard.layout.about import build_about_tab
        from dashboard.layout.analysis import thematic

        def component_strings(node):
            if isinstance(node, str):
                yield node
            elif isinstance(node, (list, tuple)):
                for child in node:
                    yield from component_strings(child)
            elif hasattr(node, "children"):
                yield from component_strings(node.children)

        pages = {
            "About": " ".join(component_strings(build_about_tab())),
            "Thematic tab": " ".join(component_strings(thematic.build_thematic_tab())),
            "Thematic methodology": thematic._thematic_methodology_md,
        }
        for page, text in pages.items():
            with self.subTest(page=page):
                self.assertIn(RELEASE_MODEL, text)
                # The thematic banner once said "Claude Opus" for the Fable 5
                # run: no page may name a model family the live run did not use.
                for family in ("opus", "sonnet", "haiku", "fable"):
                    if family not in RELEASE_MODEL.lower():
                        self.assertNotIn(family, text.lower())

    def test_fallback_when_metadata_missing_or_unreadable(self):
        self.assertEqual(
            _load_release_model("nonexistent/run_metadata.json"),
            _RELEASE_MODEL_FALLBACK,
        )

    def test_fallback_when_model_field_empty(self):
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "run_metadata.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"model": ""}, f)
            self.assertEqual(_load_release_model(path), _RELEASE_MODEL_FALLBACK)


if __name__ == "__main__":
    unittest.main()
