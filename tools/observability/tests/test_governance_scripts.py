import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class BaselineChangePolicyTest(unittest.TestCase):
    def setUp(self):
        self.policy = load_script("check_baseline_change_policy")

    def test_detects_all_governed_service_roots(self):
        changed = {
            "backend/A.java",
            "agent-runtime/a.py",
            "agent_builder/b.py",
            "frontend/a.ts",
        }
        self.assertEqual(
            self.policy.source_changes_in(changed),
            ["agent-runtime/a.py", "agent_builder/b.py", "backend/A.java"],
        )

    def test_push_uses_before_sha(self):
        before = "1" * 40
        with tempfile.TemporaryDirectory() as temp_dir:
            event = Path(temp_dir) / "event.json"
            event.write_text(json.dumps({"before": before}), encoding="utf-8")
            completed = mock.Mock(returncode=0)
            with mock.patch.dict(
                os.environ,
                {"ATOMGIT_EVENT_NAME": "push", "ATOMGIT_EVENT_PATH": str(event)},
                clear=True,
            ), mock.patch.object(self.policy, "git", return_value=completed):
                self.assertEqual(self.policy.comparison_base(), before)

    def test_rejects_existing_baseline_with_source_change(self):
        changed = {self.policy.BASELINE, "backend/A.java"}
        self.assertTrue(self.policy.should_reject_baseline_change(changed, True))

    def test_allows_dedicated_baseline_change(self):
        self.assertFalse(self.policy.should_reject_baseline_change({self.policy.BASELINE}, True))

    def test_allows_initial_baseline_bootstrap(self):
        changed = {self.policy.BASELINE, "backend/A.java"}
        self.assertFalse(self.policy.should_reject_baseline_change(changed, False))

    def test_manual_dispatch_has_no_comparison_base(self):
        with mock.patch.dict(os.environ, {"ATOMGIT_EVENT_NAME": "workflow_dispatch"}, clear=True):
            self.assertIsNone(self.policy.comparison_base())


class BaselineMetadataTest(unittest.TestCase):
    def setUp(self):
        self.inventory = load_script("check_error_code_inventory")
        self.baseline = {
            "version": 2,
            "protocol_version": "v1.2",
            "generated_from_commit": "0" * 40,
            "target_branch": "studio-2.0-dev",
            "target_branch_commit": "1" * 40,
            "studio_source_tree_dirty": False,
            "working_tree_dirty": True,
            "target_source_tree_verified": True,
            "source_inventory_sha256": "2" * 64,
        }

    def test_accepts_verified_target_metadata(self):
        self.inventory.validate_baseline_metadata(self.baseline, {"protocol_version": "v1.2"})

    def test_rejects_other_target_branch(self):
        self.baseline["target_branch"] = "studio-2.0"
        with self.assertRaisesRegex(ValueError, "target_branch"):
            self.inventory.validate_baseline_metadata(self.baseline, {"protocol_version": "v1.2"})

    def test_rejects_dirty_source_tree(self):
        self.baseline["studio_source_tree_dirty"] = True
        with self.assertRaisesRegex(ValueError, "dirty Studio source tree"):
            self.inventory.validate_baseline_metadata(self.baseline, {"protocol_version": "v1.2"})

    def test_expected_target_branch_is_fixed(self):
        self.assertEqual(self.inventory.EXPECTED_TARGET_BRANCH, "studio-2.0-dev")


if __name__ == "__main__":
    unittest.main()
