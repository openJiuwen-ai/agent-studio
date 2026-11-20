#!/usr/bin/env python3
"""Run error-code governance checks and produce reports without blocking by default."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parent


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return result.returncode, result.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / ".artifacts/error-code-governance")
    parser.add_argument("--step-summary", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="return non-zero when a check reports a problem; reserved for blocking CI",
    )
    args = parser.parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)

    manifest_status, manifest_output = run(
        [sys.executable, str(SCRIPTS_DIR / "check_error_codes.py")]
    )
    inventory_json = args.report_dir / "inventory-report.json"
    inventory_markdown = args.report_dir / "inventory-report.md"
    inventory_status, inventory_output = run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "check_error_code_inventory.py"),
            "--json-report",
            str(inventory_json),
            "--markdown-report",
            str(inventory_markdown),
        ]
    )

    inventory_summary = (
        inventory_markdown.read_text(encoding="utf-8")
        if inventory_markdown.exists()
        else inventory_output
    )
    has_warning = manifest_status != 0 or inventory_status != 0
    combined = "\n".join(
        [
            "# 错误码提示式 CI",
            "",
            f"总体状态：{'⚠️ 发现提示项（当前不阻断）' if has_warning else '✅ 未发现新增问题'}",
            "",
            "## Manifest 与生成目录校验",
            "",
            "```text",
            manifest_output.strip() or "no output",
            "```",
            "",
            inventory_summary.rstrip(),
            "",
            "> 当前阶段固定为提示式：报告中的问题不会使流水线失败。切换阻断模式必须另行完成治理评审。",
            "",
        ]
    )
    summary_path = args.report_dir / "summary.md"
    summary_path.write_text(combined, encoding="utf-8")
    (args.report_dir / "check-status.json").write_text(
        json.dumps(
            {
                "mode": "strict" if args.strict else "advisory",
                "manifest_check_exit_code": manifest_status,
                "inventory_check_exit_code": inventory_status,
                "has_warning": has_warning,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if args.step_summary:
        args.step_summary.parent.mkdir(parents=True, exist_ok=True)
        with args.step_summary.open("a", encoding="utf-8") as stream:
            stream.write(combined)
    print(combined, end="")
    return 1 if args.strict and has_warning else 0


if __name__ == "__main__":
    raise SystemExit(main())
