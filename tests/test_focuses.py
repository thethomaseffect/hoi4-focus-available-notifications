from __future__ import annotations

import unittest
from pathlib import Path

from tools.focuses import load_focus_files
from tools.generate import _brace_delta, render_mod
from tools.pdx import parse_pdx
from tools.targets import Target

FIXTURE = Path(__file__).parent / "fixtures" / "sample_focus.txt"


def _target() -> Target:
    return Target(
        keyword="sample",
        slug="focus_available_notifications_sample",
        name="Focus Available Notifications Sample",
        dependencies=("Example Parent",),
        layers=(),
        id_prefix="fans",
    )


class FocusLibraryTest(unittest.TestCase):
    def test_unclosed_brace_keeps_the_block(self) -> None:
        root = parse_pdx("focus_tree = { id = broken", source="broken.txt")
        self.assertEqual(1, root.unclosed)
        self.assertEqual("broken", root.get("focus_tree").get("id"))

    def test_library_keeps_availability_and_skips_dead_focuses(self) -> None:
        library = load_focus_files([FIXTURE])
        self.assertEqual(["sample_tree"], list(library.trees))
        active = library.active_ids_for_tree("sample_tree")
        self.assertEqual(["SAMPLE_a", "SAMPLE_b", "SHARED_root"], active)
        self.assertEqual("allow_branch always no", library.focuses["SAMPLE_hidden"].skip_reason)
        self.assertEqual("available always no", library.focuses["SAMPLE_locked"].skip_reason)
        shared = library.focuses["SHARED_root"]
        self.assertIn("threat > 0.5", shared.available or "")
        sample_b = library.focuses["SAMPLE_b"]
        self.assertEqual([["SAMPLE_a", "SHARED_root"], ["SAMPLE_c"]], sample_b.prerequisite_groups)
        self.assertIn("date > 5", sample_b.available or "")
        self.assertNotIn("@days", sample_b.available or "")
        self.assertIsNone(sample_b.bypass)
        self.assertFalse(sample_b.available_if_capitulated)
        self.assertTrue(library.focuses["SAMPLE_a"].available_if_capitulated)

    def test_generated_mod_tracks_seen_focuses_without_repeating_them(self) -> None:
        library = load_focus_files([FIXTURE])
        files = render_mod(library, _target(), "1.19.3.0")
        script = "\n".join(files.values())
        self.assertEqual(0, _brace_delta(script))
        self.assertIn('name="Focus Available Notifications Sample"', files["descriptor.mod"])
        self.assertIn('\t"Example Parent"', files["descriptor.mod"])
        self.assertNotIn("replace_path", files["descriptor.mod"])
        self.assertIn('fans_enable:0 "Enable Focus Available Notifications"', script)
        self.assertIn('fans_disable:0 "Disable Focus Available Notifications"', script)
        self.assertIn('fans_event_title:0 "New Focus Available"', script)
        self.assertIn('The focus $SAMPLE_a$ is now available.', script)
        self.assertIn('The focus $SHARED_root$ is now available.', script)
        self.assertNotIn("SAMPLE_hidden", script)
        self.assertNotIn("SAMPLE_locked", script)
        self.assertIn("has_country_flag = fans_seen_SAMPLE_b", script)
        self.assertIn("set_country_flag = fans_seen_SAMPLE_b", script)
        self.assertIn("clr_country_flag = fans_enabled", script)
        self.assertNotIn("clr_country_flag = fans_seen_", script)
        self.assertIn("has_completed_focus = SAMPLE_a", script)
        self.assertIn("has_completed_focus = SHARED_root", script)
        self.assertIn('has_dlc = "Test"', script)
        self.assertIn("NOT = { has_capitulated = yes }", script)
        self.assertIn("has_focus_tree = sample_tree", script)
        self.assertIn("fire_only_once = yes", script)
        enable = files["common/decisions/fans_decisions.txt"]
        self.assertLess(enable.index("set_country_flag = fans_enabled"), enable.index("fans_scan_focuses = yes"))
        self.assertIn("hidden_effect", enable)


if __name__ == "__main__":
    unittest.main()
