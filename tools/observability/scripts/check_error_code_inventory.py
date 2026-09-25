#!/usr/bin/env python3
"""Report error-code inventory regressions relative to an reviewed advisory baseline."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from generate_error_code_docs import load_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]
BASELINE_PATH = REPO_ROOT / "tools/observability/error-code-advisory-baseline.json"
SERVICE_ROOTS = {
    "manager": [REPO_ROOT / "backend"],
    "runtime": [REPO_ROOT / "agent-runtime/agent_runtime", REPO_ROOT / "agent-runtime/jiuwen"],
    "builder": [REPO_ROOT / "agent_builder"],
}
EXCLUDED_PARTS = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "target",
    "dist",
    "build",
    "logs",
}
SOURCE_EXTENSIONS = {".java", ".py", ".properties", ".json", ".yaml", ".yml"}
CANONICAL_LITERAL_RE = re.compile(r"openjiuwen\.[0-9]+")
JAVA_HTTP_STATUS_RE = re.compile(r"HTTP_([0-9]{3})_")
I18N_SUFFIX_RE = re.compile(r"\.(reason|suggestion)$")
REQUIRED_I18N_FIELDS = {"message", "reason", "suggestion"}
REQUIRED_LOCALES = {"zh_cn", "en_us"}
GOVERNED_SOURCE_PATHS = ("backend", "agent-runtime", "agent_builder")
EXPECTED_TARGET_BRANCH = "studio-2.0-dev"


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def current_commit() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.strip()


def working_tree_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return bool(result.stdout.strip())


def studio_source_tree_dirty() -> bool:
    result = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "backend",
            "agent-runtime",
            "agent_builder",
        ],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return bool(result.stdout.strip())


def target_source_tree_matches(target: str) -> bool:
    result = subprocess.run(
        ["git", "diff", "--quiet", target, "HEAD", "--", *GOVERNED_SOURCE_PATHS],
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"cannot compare Studio source tree with {target}")
    return result.returncode == 0


def source_inventory_sha256() -> str:
    digest = hashlib.sha256()
    paths = {path for _service, path in iter_service_files()}
    paths.add(REPO_ROOT / "tools/observability/error-codes.yaml")
    for path in sorted(paths):
        digest.update(relative(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def iter_service_files() -> Iterable[tuple[str, Path]]:
    seen: set[Path] = set()
    for service, roots in SERVICE_ROOTS.items():
        for root in roots:
            if not root.exists():
                continue
            for path in sorted(root.rglob("*")):
                if not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
                    continue
                if any(part in EXCLUDED_PARTS for part in path.relative_to(root).parts):
                    continue
                resolved = path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield service, path


def literal_int(node: ast.AST) -> int | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        value = literal_int(node.operand)
        return -value if value is not None else None
    return None


def literal_str(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        left = target_name(node.value)
        return f"{left}.{node.attr}" if left else node.attr
    return None


def python_tuple_code(value: ast.AST, class_strings: dict[str, str]) -> str | None:
    if not isinstance(value, (ast.Tuple, ast.List)) or not value.elts:
        return None
    first_int = literal_int(value.elts[0])
    second_str = literal_str(value.elts[1]) if len(value.elts) > 1 else None
    if first_int is not None and second_str is not None:
        return str(first_int)
    if len(value.elts) < 3:
        return None
    module = literal_str(value.elts[1])
    if module is None and isinstance(value.elts[1], ast.Name):
        module = class_strings.get(value.elts[1].id)
    local = literal_str(value.elts[2])
    if module and local and module.isdigit() and local.isdigit():
        return f"openjiuwen.{module}{local}"
    return None


def scan_python_definitions(service: str, path: Path, text: str) -> list[dict[str, str]]:
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    found: list[dict[str, str]] = []
    definition_file = any(token in path.name.lower() for token in ("error", "exception", "status", "code"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and ("StatusCode" in node.name or "ErrorCode" in node.name):
            class_strings: dict[str, str] = {}
            for item in node.body:
                if isinstance(item, ast.Assign) and len(item.targets) == 1:
                    name = target_name(item.targets[0])
                    value = literal_str(item.value)
                    if name and value:
                        class_strings[name] = value
            for item in node.body:
                if not isinstance(item, ast.Assign) or len(item.targets) != 1:
                    continue
                name = target_name(item.targets[0])
                code = python_tuple_code(item.value, class_strings)
                if name and name.isupper() and code is not None:
                    found.append({"code": code, "symbol": f"{node.name}.{name}"})

        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        name = target_name(node.targets[0])
        if not name:
            continue
        if isinstance(node.value, ast.Call) and target_name(node.value.func) == "ExtensionStatusCode":
            value = literal_int(node.value.args[0]) if node.value.args else None
            if value is not None:
                found.append({"code": str(value), "symbol": name})
        raw_int = literal_int(node.value)
        raw_str = literal_str(node.value)
        looks_like_name = bool(re.search(r"(?:^|_)(?:ERROR_?CODE|CODE|ERROR|FAIL(?:ED)?)$", name))
        code_scope = definition_file or name in {"CODE", "ERROR_CODE"}
        if code_scope and looks_like_name and raw_int is not None and (raw_int < 0 or raw_int >= 1000):
            found.append({"code": str(raw_int), "symbol": name})
        elif (
            code_scope
            and looks_like_name
            and raw_str
            and re.fullmatch(r"(?:-?[0-9]+|[A-Z][A-Z0-9_-]*(?:ERROR|FAIL)[A-Z0-9_-]*)", raw_str)
        ):
            found.append({"code": raw_str, "symbol": name})

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or target_name(node.func) != "ModelErrorSpec":
            continue
        keywords = {keyword.arg: keyword.value for keyword in node.keywords if keyword.arg}
        code = literal_str(keywords["full_code"]) if "full_code" in keywords else None
        if code:
            found.append({"code": code, "symbol": f"ModelErrorSpec@{node.lineno}"})
    return found


def scan_java_definitions(path: Path, text: str) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if path.name == "StudioError.java":
        modules = dict(
            re.findall(r'^[ \t]*([A-Z][A-Z0-9_]*)\("([0-9]{4})"\)[ \t]*[,;]', text, re.MULTILINE)
        )
        pattern = re.compile(
            r'^[ \t]*([A-Z][A-Z0-9_]*)\s*\(\s*([A-Z_]+)\s*,\s*(?:Module\.)?'
            r'([A-Z][A-Z0-9_]*)\s*,\s*"([0-9]{4})"\s*\)\s*[,;]',
            re.MULTILINE,
        )
        for symbol, _http, module, local in pattern.findall(text):
            if module in modules:
                found.append({"code": f"openjiuwen.{modules[module]}{local}", "symbol": f"StudioError.{symbol}"})
    if path.name == "ErrorCode.java" and "foundation/base/exception" in relative(path):
        base = re.search(r'BASE_CODE\s*=\s*"([0-9]{4})"', text)
        if base:
            pattern = re.compile(
                r'^[ \t]*([A-Z][A-Z0-9_]*)\s*\(\s*HttpStatus\.[A-Z_]+\.value\(\)\s*,'
                r'\s*"([0-9]{4})"\s*,',
                re.MULTILINE,
            )
            for symbol, local in pattern.findall(text):
                found.append({"code": f"openjiuwen.{base.group(1)}{local}", "symbol": f"ErrorCode.{symbol}"})
    return found


def locale_from_path(path: Path) -> str | None:
    name = path.name.lower().replace("-", "_")
    if "zh_cn" in name:
        return "zh_cn"
    if "en_us" in name:
        return "en_us"
    return None


def scan_inventory() -> tuple[list[dict[str, str]], dict[tuple[str, str], dict[str, set[str]]]]:
    definitions: list[dict[str, str]] = []
    i18n: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for service, path in iter_service_files():
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        rel = relative(path)
        if path.suffix == ".py":
            for item in scan_python_definitions(service, path, text):
                definitions.append({**item, "service": service, "path": rel})
        elif path.suffix == ".java":
            for item in scan_java_definitions(path, text):
                definitions.append({**item, "service": service, "path": rel})
        if path.suffix == ".properties":
            locale = locale_from_path(path)
            if locale:
                for line in text.splitlines():
                    stripped = line.strip()
                    if not stripped or stripped.startswith(("#", "!")) or "=" not in stripped:
                        continue
                    key = stripped.split("=", 1)[0].strip()
                    suffix = I18N_SUFFIX_RE.search(key)
                    field = suffix.group(1) if suffix else "message"
                    base = key[: suffix.start()] if suffix else key
                    i18n[(service, base)][locale].add(field)
    return definitions, i18n


def issue(kind: str, **details: str) -> dict[str, Any]:
    identity = {"kind": kind, **details}
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {"fingerprint": hashlib.sha256(encoded.encode("utf-8")).hexdigest(), **identity}


def public_definition_code(service: str, code: str) -> str:
    if service == "runtime" and code == "121007":
        return "openjiuwen.121007"
    return code


def collect_issues(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    definitions, i18n = scan_inventory()
    by_code = {item["full_code"]: item for item in manifest["definitions"]}
    declared_references = {
        (item["service"], item["full_code"])
        for item in manifest.get("references", [])
    }

    locations: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in definitions:
        code = public_definition_code(item["service"], item["code"])
        locations[code].append(item)
        registered = by_code.get(code)
        if not registered:
            issues.append(
                issue(
                    "unregistered_definition",
                    service=item["service"],
                    code=code,
                    path=item["path"],
                    symbol=item["symbol"],
                )
            )
        elif registered["code_owner"] != item["service"]:
            issues.append(
                issue(
                    "definition_owner_mismatch",
                    service=item["service"],
                    code=code,
                    expected_owner=registered["code_owner"],
                    path=item["path"],
                    symbol=item["symbol"],
                )
            )

    for code, code_locations in locations.items():
        unique_locations = {(item["service"], item["path"], item["symbol"]) for item in code_locations}
        if len(unique_locations) > 1:
            for service, path, symbol in sorted(unique_locations):
                issues.append(
                    issue(
                        "multiple_definition_location",
                        service=service,
                        code=code,
                        path=path,
                        symbol=symbol,
                    )
                )

    for service, path in iter_service_files():
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        literal_counts: dict[str, int] = defaultdict(int)
        for code in CANONICAL_LITERAL_RE.findall(text):
            literal_counts[code] += 1
        for code, occurrences in sorted(literal_counts.items()):
            if code not in by_code:
                issues.append(
                    issue(
                        "unknown_literal_reference",
                        service=service,
                        code=code,
                        path=relative(path),
                        occurrences=str(occurrences),
                    )
                )
            elif by_code[code]["code_owner"] != service and (service, code) not in declared_references:
                issues.append(
                    issue(
                        "undeclared_cross_service_reference",
                        service=service,
                        code=code,
                        expected_owner=by_code[code]["code_owner"],
                        path=relative(path),
                        occurrences=str(occurrences),
                    )
                )

    for definition in manifest["definitions"]:
        owner = definition["code_owner"]
        key = str(definition["i18n_key"])
        locales = i18n.get((owner, key), {})
        for locale in sorted(REQUIRED_LOCALES):
            missing = sorted(REQUIRED_I18N_FIELDS - locales.get(locale, set()))
            if missing:
                issues.append(
                    issue(
                        "manifest_i18n_incomplete",
                        service=owner,
                        code=definition["full_code"],
                        locale=locale,
                        missing=",".join(missing),
                    )
                )
        source = definition.get("definition_source", {})
        source_path = REPO_ROOT / str(source.get("path", ""))
        if not source_path.is_file():
            issues.append(
                issue(
                    "manifest_definition_source_missing",
                    code=definition["full_code"],
                    path=str(source.get("path", "")),
                )
            )
        else:
            symbol_tail = str(source.get("symbol", "")).split(".")[-1]
            if symbol_tail and symbol_tail not in source_path.read_text(encoding="utf-8-sig"):
                issues.append(
                    issue(
                        "manifest_definition_symbol_missing",
                        code=definition["full_code"],
                        path=str(source.get("path", "")),
                        symbol=str(source.get("symbol", "")),
                    )
                )

    for reference in manifest.get("references", []):
        definition = by_code.get(reference["full_code"])
        if not definition:
            continue
        key = str(definition["i18n_key"])
        if reference["service"] == "runtime" and key.startswith("openjiuwen."):
            key = key.removeprefix("openjiuwen.")
        locales = i18n.get((reference["service"], key), {})
        if not all(REQUIRED_I18N_FIELDS <= locales.get(locale, set()) for locale in REQUIRED_LOCALES):
            issues.append(
                issue(
                    "manifest_reference_i18n_incomplete",
                    service=reference["service"],
                    code=reference["full_code"],
                )
            )

    return sorted({item["fingerprint"]: item for item in issues}.values(), key=lambda item: item["fingerprint"])


def markdown_report(
    current: list[dict[str, Any]],
    known: list[dict[str, Any]],
) -> str:
    current_by_id = {item["fingerprint"]: item for item in current}
    known_by_id = {item["fingerprint"]: item for item in known}
    new = [current_by_id[key] for key in sorted(current_by_id.keys() - known_by_id.keys())]
    resolved = [known_by_id[key] for key in sorted(known_by_id.keys() - current_by_id.keys())]
    lines = [
        "# 错误码存量提示式检查",
        "",
        f"- 当前问题指纹：{len(current)}",
        f"- 已评审基线指纹：{len(known)}",
        f"- 新增问题：{len(new)}",
        f"- 已消失的基线问题：{len(resolved)}",
        "",
    ]
    if new:
        lines.extend(["## 新增问题", "", "| 类型 | 服务 | 错误码 | 位置/说明 |", "| --- | --- | --- | --- |"])
        for item in new[:100]:
            location = item.get("path") or item.get("missing") or item.get("symbol") or "—"
            lines.append(
                f"| `{item['kind']}` | {item.get('service', '—')} | "
                f"`{item.get('code', '—')}` | `{location}` |"
            )
        if len(new) > 100:
            lines.append(f"| 其余 {len(new) - 100} 项 | — | — | 见 JSON 报告 |")
    else:
        lines.extend(["## 结论", "", "未发现相对已评审基线新增的错误码治理问题。"])
    if resolved:
        lines.extend(["", "## 基线中已消失的问题", "", f"共 {len(resolved)} 项；待人工确认后再刷新基线，不自动删除。"])
    lines.append("")
    return "\n".join(lines)


def validate_baseline_metadata(baseline: dict[str, Any], manifest: dict[str, Any]) -> None:
    if baseline.get("version") != 2:
        raise ValueError("unsupported advisory baseline version")
    if baseline.get("protocol_version") != manifest.get("protocol_version"):
        raise ValueError("advisory baseline protocol_version does not match Manifest")
    if baseline.get("target_branch") != EXPECTED_TARGET_BRANCH:
        raise ValueError(f"advisory baseline target_branch must be {EXPECTED_TARGET_BRANCH}")
    if not re.fullmatch(r"[0-9a-f]{40}", str(baseline.get("generated_from_commit", ""))):
        raise ValueError("advisory baseline generated_from_commit must be a full Git SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", str(baseline.get("target_branch_commit", ""))):
        raise ValueError("advisory baseline target_branch_commit must be a full Git SHA")
    if baseline.get("studio_source_tree_dirty") is not False:
        raise ValueError("advisory baseline must not be generated from a dirty Studio source tree")
    if not isinstance(baseline.get("working_tree_dirty"), bool):
        raise ValueError("advisory baseline working_tree_dirty must be boolean")
    if baseline.get("target_source_tree_verified") is not True:
        raise ValueError("advisory baseline target source tree was not verified")
    if not re.fullmatch(r"[0-9a-f]{64}", str(baseline.get("source_inventory_sha256", ""))):
        raise ValueError("advisory baseline source_inventory_sha256 is invalid")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, default=BASELINE_PATH)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument(
        "--target-branch",
        help="target branch whose Studio source tree is represented by a newly written baseline",
    )
    parser.add_argument("--json-report", type=Path)
    parser.add_argument("--markdown-report", type=Path)
    args = parser.parse_args()

    manifest = load_manifest()
    current = collect_issues(manifest)
    if args.write_baseline:
        source_commit = current_commit()
        target_commit = None
        if args.target_branch:
            target_commit = subprocess.run(
                ["git", "rev-parse", args.target_branch],
                cwd=REPO_ROOT,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            ).stdout.strip()
            if args.target_branch != EXPECTED_TARGET_BRANCH:
                raise ValueError(
                    f"advisory governance only supports target branch {EXPECTED_TARGET_BRANCH}"
                )
            if studio_source_tree_dirty():
                raise ValueError("Studio source tree has uncommitted changes; baseline refresh refused")
            if not target_source_tree_matches(target_commit):
                raise ValueError(
                    f"Studio source tree at HEAD differs from target branch {args.target_branch} "
                    f"({target_commit}); refresh from a governance-only change"
                )
        governed = [
            {
                **item,
                "action_owner": item.get("service", "observability-governance"),
                "review_status": "accepted_existing",
                "target_milestone": "before_strict_ci",
            }
            for item in current
        ]
        payload = {
            "version": 2,
            "protocol_version": manifest.get("protocol_version"),
            "generated_from_commit": source_commit,
            "target_branch": args.target_branch,
            "target_branch_commit": target_commit,
            "working_tree_dirty": working_tree_dirty(),
            "studio_source_tree_dirty": studio_source_tree_dirty(),
            "target_source_tree_verified": bool(args.target_branch),
            "source_inventory_sha256": source_inventory_sha256(),
            "known_issues": governed,
        }
        args.baseline.parent.mkdir(parents=True, exist_ok=True)
        args.baseline.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote advisory baseline: issues={len(current)}")
        return 0

    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    validate_baseline_metadata(baseline, manifest)
    known = baseline.get("known_issues", [])
    required_governance = {"action_owner", "review_status", "target_milestone"}
    if any(not required_governance <= item.keys() for item in known):
        raise ValueError("advisory baseline issue is missing governance metadata")
    if len({item["fingerprint"] for item in known}) != len(known):
        raise ValueError("advisory baseline contains duplicate fingerprints")
    current_ids = {item["fingerprint"] for item in current}
    known_ids = {item["fingerprint"] for item in known}
    new_count = len(current_ids - known_ids)
    report = {
        "protocol_version": manifest.get("protocol_version"),
        "baseline_commit": baseline.get("generated_from_commit"),
        "current_issue_count": len(current),
        "known_issue_count": len(known),
        "new_issues": [item for item in current if item["fingerprint"] not in known_ids],
        "resolved_baseline_issues": [item for item in known if item["fingerprint"] not in current_ids],
    }
    markdown = markdown_report(current, known)
    if args.json_report:
        args.json_report.parent.mkdir(parents=True, exist_ok=True)
        args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.markdown_report:
        args.markdown_report.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_report.write_text(markdown, encoding="utf-8")
    print(markdown, end="")
    return 1 if new_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
