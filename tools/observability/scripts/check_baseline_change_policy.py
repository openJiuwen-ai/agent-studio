#!/usr/bin/env python3
"""Prevent a source change from hiding new findings by refreshing the baseline in the same change."""

from __future__ import annotations

import os
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE = "tools/observability/error-code-advisory-baseline.json"
GOVERNED_SOURCE_PREFIXES = ("backend/", "agent-runtime/", "agent_builder/")


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def comparison_base() -> str | None:
    event_name = os.environ.get("ATOMGIT_EVENT_NAME", "").strip()
    if event_name == "workflow_dispatch":
        return None
    base_ref = os.environ.get("ATOMGIT_BASE_REF", "").strip()
    if base_ref:
        remote_ref = f"origin/{base_ref}"
        if git("rev-parse", "--verify", remote_ref, check=False).returncode != 0:
            raise RuntimeError(f"missing fetched PR base ref: {remote_ref}")
        return remote_ref

    event_path = os.environ.get("ATOMGIT_EVENT_PATH", "").strip()
    if event_name == "push" and event_path:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
        before = str(payload.get("before", "")).strip()
        if before and set(before) != {"0"}:
            if git("rev-parse", "--verify", f"{before}^{{commit}}", check=False).returncode != 0:
                fetched = git("fetch", "--no-tags", "origin", before, "--depth=1", check=False)
                if fetched.returncode != 0:
                    raise RuntimeError(f"cannot fetch push comparison commit {before}: {fetched.stderr.strip()}")
            return before
        return None

    if git("rev-parse", "--verify", "HEAD^", check=False).returncode == 0:
        return "HEAD^"
    return None


def source_changes_in(changed: set[str]) -> list[str]:
    return sorted(path for path in changed if path.startswith(GOVERNED_SOURCE_PREFIXES))


def should_reject_baseline_change(changed: set[str], baseline_existed: bool) -> bool:
    return BASELINE in changed and baseline_existed and bool(source_changes_in(changed))


def main() -> int:
    base = comparison_base()
    if base is None:
        print("baseline change policy: no comparison base; bootstrap check skipped")
        return 0

    changed = {
        line.strip()
        for line in git("diff", "--name-only", base, "HEAD").stdout.splitlines()
        if line.strip()
    }
    if BASELINE not in changed:
        print("baseline change policy: baseline unchanged")
        return 0

    baseline_existed = git("cat-file", "-e", f"{base}:{BASELINE}", check=False).returncode == 0
    if not baseline_existed:
        print("baseline change policy: initial baseline bootstrap allowed; CODEOWNERS approval is still required")
        return 0

    source_changes = source_changes_in(changed)
    if should_reject_baseline_change(changed, baseline_existed):
        print(
            "ERROR: baseline and governed Studio source changed together; split the baseline refresh "
            "into a dedicated CODEOWNERS-reviewed change after reviewing new findings.",
            file=sys.stderr,
        )
        for path in source_changes[:100]:
            print(f"  - {path}", file=sys.stderr)
        return 1

    print("baseline change policy: dedicated governance-only baseline change; CODEOWNERS approval required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
