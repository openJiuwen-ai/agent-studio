# Copyright (c) guanenqiang 2026. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Offline regression tests: Python 3, Bash and awk; no Docker or downloads.

Run: python3 -m unittest discover -s docker/tests -v
Set JVM_TEST_BASH to select a Bash executable (e.g. Git Bash on Windows).
"""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "studio-manager/script/jvm-memory.sh"
)
BASH = os.environ.get("JVM_TEST_BASH", "bash")


class ManagerMemoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="manager-memory-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # 15703 MiB of visible physical memory.
        self.write("/proc/meminfo", "MemTotal:       16079872 kB\n")
        self.v2()

    def write(self, path, value):
        target = self.root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value, encoding="utf-8", newline="\n")

    def v2(self, group="/", mount="/sys/fs/cgroup", mount_root="/"):
        self.write("/proc/self/cgroup", f"0::{group}\n")
        escaped = mount.replace(" ", r"\040")
        self.write(
            "/proc/self/mountinfo",
            f"1 0 0:1 {mount_root} {escaped} rw - cgroup2 cgroup rw\n",
        )
        self.write(f"{mount}/memory.max", "max\n")

    def v1(self, group="/", mount_root="/"):
        self.write("/proc/self/cgroup", f"5:cpu,memory:{group}\n")
        self.write(
            "/proc/self/mountinfo",
            f"1 0 0:1 {mount_root} /sys/fs/cgroup/memory rw "
            "- cgroup cgroup rw,cpu,memory\n",
        )
        self.write(
            "/sys/fs/cgroup/memory/memory.limit_in_bytes",
            "9223372036854771712\n",
        )
        self.write("/sys/fs/cgroup/memory/memory.use_hierarchy", "1\n")

    def run_config(self, **settings):
        env = os.environ.copy()
        for key in (
            "jvm_xmx_percent",
            "jvm_direct_memory_ratio",
            "jvm_direct_memory_cap_mb",
        ):
            env.pop(key, None)
        env.update(settings)
        result = subprocess.run(
            [
                BASH,
                "-c",
                'source "$1"; manager_configure_jvm_memory "$2"',
                "memory-test",
                SCRIPT.as_posix(),
                self.root.as_posix(),
            ],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=20,
        )
        self.assertNotIn("integer expression expected", result.stderr)
        self.assertNotIn("syntax error", result.stderr)
        return result

    def expect(self, budget, heap, direct, source=None, **settings):
        result = self.run_config(**settings)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            f"budget={budget}MiB Xms={heap}m Xmx={heap}m direct={direct}m",
            result.stdout,
        )
        if source:
            self.assertIn(source, result.stdout)
        return result

    def test_v2_four_gib(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        result = self.expect(4096, 2458, 819, "/sys/fs/cgroup/memory.max")
        self.assertEqual(result.stderr, "")

    def test_v1_four_gib(self):
        self.v1()
        self.write(
            "/sys/fs/cgroup/memory/memory.limit_in_bytes", "4294967296\n"
        )
        self.expect(4096, 2458, 819, "/memory.limit_in_bytes")

    def test_same_container_limit_on_different_hosts(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        for host_mb in (8192, 15703, 65536):
            with self.subTest(host_mb=host_mb):
                self.write("/proc/meminfo", f"MemTotal: {host_mb * 1024} kB\n")
                self.expect(4096, 2458, 819)

    def test_physical_memory_caps_large_limit(self):
        self.write("/proc/meminfo", "MemTotal: 2097152 kB\n")
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        self.expect(2048, 1229, 410, "/proc/meminfo")

    def test_v2_unlimited(self):
        self.expect(15703, 9422, 1024, "/proc/meminfo")

    def test_v1_unlimited_sentinels_do_not_overflow(self):
        self.v1()
        for value in (
            "9223372036854771712",
            "9223372036854775807",
            "18446744073709551615",
        ):
            with self.subTest(value=value):
                self.write(
                    "/sys/fs/cgroup/memory/memory.limit_in_bytes", value + "\n"
                )
                self.expect(15703, 9422, 1024)

    def test_visible_v2_parent_limit_when_child_is_unlimited(self):
        self.v2(group="/pod/container")
        self.write("/sys/fs/cgroup/pod/container/memory.max", "max\n")
        self.write("/sys/fs/cgroup/pod/memory.max", "4294967296\n")
        self.expect(4096, 2458, 819, "/pod/memory.max")

    def test_parent_stricter_than_child(self):
        self.v2(group="/pod/container")
        self.write("/sys/fs/cgroup/pod/container/memory.max", "8589934592\n")
        self.write("/sys/fs/cgroup/pod/memory.max", "4294967296\n")
        self.expect(4096, 2458, 819)

    def test_child_stricter_than_parent(self):
        self.v2(group="/pod/container")
        self.write("/sys/fs/cgroup/pod/container/memory.max", "2147483648\n")
        self.write("/sys/fs/cgroup/pod/memory.max", "4294967296\n")
        self.expect(2048, 1229, 410, "/pod/container/memory.max")

    def test_nondefault_mount_and_mount_root(self):
        self.v2(
            group="/tenant/pod/container",
            mount="/custom/memory",
            mount_root="/tenant",
        )
        self.write("/custom/memory/pod/container/memory.max", "max\n")
        self.write("/custom/memory/pod/memory.max", "4294967296\n")
        self.expect(4096, 2458, 819, "/custom/memory/pod/memory.max")

    def test_mount_path_with_space(self):
        self.v2(mount="/custom/memory controller")
        self.write("/custom/memory controller/memory.max", "4294967296\n")
        self.expect(4096, 2458, 819)

    def test_v1_mount_root_equals_membership(self):
        self.v1(group="/docker/abc", mount_root="/docker/abc")
        self.write(
            "/sys/fs/cgroup/memory/memory.limit_in_bytes", "4294967296\n"
        )
        self.expect(4096, 2458, 819)

    def test_v1_hierarchical_parent(self):
        self.v1(group="/child")
        self.write(
            "/sys/fs/cgroup/memory/child/memory.limit_in_bytes", "8589934592\n"
        )
        self.write(
            "/sys/fs/cgroup/memory/memory.limit_in_bytes", "4294967296\n"
        )
        self.expect(4096, 2458, 819)
        self.write("/sys/fs/cgroup/memory/memory.use_hierarchy", "0\n")
        self.expect(8192, 4915, 1024)

    def test_unrelated_mount_is_ignored(self):
        self.v2(group="/tenant-other", mount_root="/tenant")
        self.write("/sys/fs/cgroup/memory.max", "1048576\n")
        result = self.expect(15703, 9422, 1024)
        self.assertIn("no matching memory cgroup mount", result.stderr)

    def test_hidden_membership_does_not_escape_mount(self):
        self.v2(group="/../../outside")
        self.write("/outside/memory.max", "1048576\n")
        result = self.expect(15703, 9422, 1024)
        self.assertIn("container limit unknown", result.stderr)

    def test_metadata_unavailable(self):
        (self.root / "proc/self/mountinfo").unlink()
        result = self.expect(15703, 9422, 1024)
        self.assertIn("metadata unavailable", result.stderr)

    def test_no_memory_controller(self):
        self.write("/proc/self/cgroup", "5:cpu:/\n")
        result = self.expect(15703, 9422, 1024)
        self.assertIn("container limit unknown", result.stderr)

    def test_invalid_leaf_retains_valid_parent(self):
        self.v2(group="/child")
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        for invalid in ("", "invalid", "-1", "1.5", "123\n456"):
            with self.subTest(invalid=invalid):
                self.write("/sys/fs/cgroup/child/memory.max", invalid + "\n")
                result = self.expect(4096, 2458, 819)
                self.assertIn("invalid limit", result.stderr)

    def test_missing_leaf_retains_valid_parent(self):
        self.v2(group="/child")
        (self.root / "sys/fs/cgroup/child").mkdir()
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        result = self.expect(4096, 2458, 819)
        self.assertIn("cannot read", result.stderr)

    def test_unreadable_file_retains_parent(self):
        self.v2(group="/child")
        # A directory makes cat fail even when tests run as root.
        (self.root / "sys/fs/cgroup/child/memory.max").mkdir(parents=True)
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        result = self.expect(4096, 2458, 819)
        self.assertIn("cannot read", result.stderr)

    def test_too_small_limit_is_not_treated_as_unlimited(self):
        for value in ("0", "1", "1048575"):
            with self.subTest(value=value):
                self.write("/sys/fs/cgroup/memory.max", value + "\n")
                result = self.run_config()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("below 1 MiB", result.stderr)

    def test_invalid_physical_memory_fails(self):
        self.write("/proc/meminfo", "MemTotal: invalid kB\n")
        result = self.run_config()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Cannot determine physical memory", result.stderr)

    def test_existing_overrides_and_cap(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        self.expect(
            4096, 2048, 256,
            jvm_xmx_percent="0.5",
            jvm_direct_memory_ratio="0.1",
            jvm_direct_memory_cap_mb="256",
        )

    def test_fraction_without_leading_zero(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        self.expect(
            4096, 2458, 819,
            jvm_xmx_percent=".6",
            jvm_direct_memory_ratio=".2",
        )

    def test_missing_root_limit_is_explicit(self):
        (self.root / "sys/fs/cgroup/memory.max").unlink()
        result = self.expect(15703, 9422, 1024)
        self.assertIn("memory.max unavailable", result.stderr)

    def test_invalid_root_limit_is_explicit(self):
        self.write("/sys/fs/cgroup/memory.max", "invalid\n")
        result = self.expect(15703, 9422, 1024)
        self.assertIn("invalid limit", result.stderr)

    def test_real_v2_root_without_memory_interface(self):
        self.v2(group="/child")
        (self.root / "sys/fs/cgroup/memory.max").unlink()
        self.write("/sys/fs/cgroup/child/memory.max", "4294967296\n")
        result = self.expect(4096, 2458, 819)
        self.assertEqual(result.stderr, "")

    def test_budget_rounding_does_not_emit_zero_direct_memory(self):
        self.write("/sys/fs/cgroup/memory.max", "1048576\n")
        result = self.run_config()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid JVM memory budget", result.stderr)

    def test_empty_settings_keep_defaults(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        self.expect(
            4096, 2458, 819,
            jvm_xmx_percent="",
            jvm_direct_memory_ratio="",
            jvm_direct_memory_cap_mb="",
        )

    def test_invalid_configuration_fails(self):
        for key, value in (
            ("jvm_xmx_percent", "garbage"),
            ("jvm_xmx_percent", "0"),
            ("jvm_xmx_percent", "1"),
            ("jvm_xmx_percent", "-0.1"),
            ("jvm_xmx_percent", '0.6; system("false")'),
            ("jvm_direct_memory_ratio", "0"),
            ("jvm_direct_memory_ratio", "NaN"),
            ("jvm_direct_memory_cap_mb", "0"),
            ("jvm_direct_memory_cap_mb", "-1"),
            ("jvm_direct_memory_cap_mb", "1.5"),
        ):
            with self.subTest(key=key, value=value):
                result = self.run_config(**{key: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    "Invalid JVM memory configuration", result.stderr
                )

    def test_budget_requires_native_memory_headroom(self):
        self.write("/sys/fs/cgroup/memory.max", "4294967296\n")
        result = self.run_config(
            jvm_xmx_percent="0.8", jvm_direct_memory_ratio="0.2"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("leave room for native memory", result.stderr)


if __name__ == "__main__":
    unittest.main()
