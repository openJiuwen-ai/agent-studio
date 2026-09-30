#!/usr/bin/env python3
"""Validate the error-code Manifest and its generated reference documents."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

from generate_error_code_docs import expected_outputs, load_manifest


REQUIRED_DEFINITION_FIELDS = {
    "full_code",
    "code_format",
    "name",
    "summary_zh_cn",
    "summary_en_us",
    "http_status",
    "category",
    "code_owner",
    "module_steward",
    "owning_module",
    "default_level",
    "i18n_key",
    "lifecycle_status",
    "definition_source",
}
ALLOWED_OWNERS = {"manager", "runtime", "builder"}
ALLOWED_CATEGORIES = {"system", "business", "security", "dependency"}
ALLOWED_LEVELS = {"DEBUG", "INFO", "WARN", "ERROR"}
ALLOWED_LIFECYCLES = {"active", "deprecated", "reserved"}
ALLOWED_MODULE_STATES = {"provisional", "frozen", "reserved"}
ALLOWED_CODE_FORMATS = {"canonical8", "legacy6", "legacy_symbolic", "legacy_other"}
REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_PATH = REPO_ROOT / "docs/zh/reference/observability-contract.md"


def expected_code_format(code: str) -> str:
    if re.fullmatch(r"openjiuwen\.[0-9]{8}", code):
        return "canonical8"
    if re.fullmatch(r"[0-9]{6}", code):
        return "legacy6"
    if re.fullmatch(r"(?:-?[0-9]+|[A-Za-z_][A-Za-z0-9_-]*)", code):
        return "legacy_symbolic"
    return "legacy_other"


def source_service(path: str) -> str | None:
    if path.startswith("backend/"):
        return "manager"
    if path.startswith("agent-runtime/"):
        return "runtime"
    if path.startswith("agent_builder/"):
        return "builder"
    return None


def validate() -> list[str]:
    errors: list[str] = []
    manifest = load_manifest()
    if manifest.get("version") != 1:
        errors.append("manifest schema version must be 1")
    protocol_text = PROTOCOL_PATH.read_text(encoding="utf-8")
    version_match = re.search(r"^> 版本：([^\s]+)$", protocol_text, re.MULTILINE)
    protocol_version = version_match.group(1) if version_match else None
    if not protocol_version or manifest.get("protocol_version") != protocol_version:
        errors.append("manifest protocol_version does not match authoritative protocol")
    protocol_sha256 = hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()
    if manifest.get("protocol_sha256") != protocol_sha256:
        errors.append("manifest protocol_sha256 does not match authoritative protocol")
    review_artifact = manifest.get("baseline", {}).get("review_artifact")
    if not isinstance(review_artifact, str) or not (REPO_ROOT / review_artifact).is_file():
        errors.append("manifest baseline review_artifact must reference an existing repository file")

    modules = manifest.get("modules", [])
    module_names = {item.get("module_name") for item in modules}
    if len(module_names) != len(modules):
        errors.append("duplicate module_name")
    modules_by_name = {item.get("module_name"): item for item in modules}
    module_codes = [item.get("module_code") for item in modules]
    if len(module_codes) != len(set(module_codes)):
        errors.append("duplicate module_code")
    for module in modules:
        if not re.fullmatch(r"[0-9]{4}", str(module.get("module_code", ""))):
            errors.append(f"invalid module_code: {module.get('module_code')}")
        if module.get("module_steward") not in ALLOWED_OWNERS:
            errors.append(f"invalid module_steward: {module.get('module_code')}")
        if module.get("allocation_status") not in ALLOWED_MODULE_STATES:
            errors.append(f"invalid allocation_status: {module.get('module_code')}")

    definitions = manifest.get("definitions", [])
    codes = [item.get("full_code") for item in definitions]
    if len(codes) != len(set(codes)):
        errors.append("duplicate full_code definition")
    definitions_by_code = {item.get("full_code"): item for item in definitions}

    for definition in definitions:
        code = definition.get("full_code")
        missing = REQUIRED_DEFINITION_FIELDS - definition.keys()
        if missing:
            errors.append(f"{code}: missing fields {sorted(missing)}")
            continue
        if definition["code_format"] not in ALLOWED_CODE_FORMATS:
            errors.append(f"{code}: invalid code_format")
        elif definition["code_format"] != expected_code_format(str(code)):
            errors.append(f"{code}: code_format does not match exact value")
        if code == "openjiuwen.121007" and definition["code_format"] != "legacy_other":
            errors.append(f"{code}: must remain legacy_other")
        status = definition["http_status"]
        if isinstance(status, bool) or not isinstance(status, int) or not 400 <= status <= 599:
            errors.append(f"{code}: invalid http_status")
        if definition["code_owner"] not in ALLOWED_OWNERS:
            errors.append(f"{code}: invalid code_owner")
        if definition["module_steward"] not in ALLOWED_OWNERS:
            errors.append(f"{code}: invalid module_steward")
        if definition["owning_module"] not in module_names:
            errors.append(f"{code}: unknown owning_module")
        else:
            module = modules_by_name[definition["owning_module"]]
            if definition["module_steward"] != module.get("module_steward"):
                errors.append(f"{code}: module_steward does not match module registry")
            if definition["code_format"] == "canonical8":
                numeric = str(code).removeprefix("openjiuwen.")
                if numeric[:4] != module.get("module_code"):
                    errors.append(f"{code}: canonical module prefix does not match owning_module")
                if definition["lifecycle_status"] == "active" and module.get("allocation_status") != "frozen":
                    errors.append(f"{code}: active canonical code requires a frozen module")
        if definition["category"] not in ALLOWED_CATEGORIES:
            errors.append(f"{code}: invalid category")
        if definition["default_level"] not in ALLOWED_LEVELS:
            errors.append(f"{code}: invalid default_level")
        if definition["lifecycle_status"] not in ALLOWED_LIFECYCLES:
            errors.append(f"{code}: invalid lifecycle_status")
        if not definition["name"] or not definition["summary_zh_cn"] or not definition["summary_en_us"]:
            errors.append(f"{code}: empty bilingual summary")
        source = definition["definition_source"]
        if not isinstance(source, dict) or not source.get("path") or not source.get("symbol"):
            errors.append(f"{code}: invalid definition_source")
        else:
            actual_owner = source_service(str(source["path"]))
            authorized = bool(definition.get("governance_authorization"))
            if actual_owner and actual_owner != definition["code_owner"] and not authorized:
                errors.append(f"{code}: definition source owner mismatch without governance authorization")

    seen_references = set()
    for reference in manifest.get("references", []):
        if reference.get("service") not in ALLOWED_OWNERS:
            errors.append(f"invalid reference service: {reference.get('service')}")
        key = (reference.get("service"), reference.get("full_code"))
        if key in seen_references:
            errors.append(f"duplicate reference: {key}")
        seen_references.add(key)
        definition = definitions_by_code.get(reference.get("full_code"))
        if not definition:
            errors.append(f"reference points to unknown code: {reference.get('full_code')}")
            continue
        if reference.get("expected_owner") != definition["code_owner"]:
            errors.append(f"reference owner mismatch: {reference.get('full_code')}")
        if reference.get("service") == definition["code_owner"]:
            errors.append(f"owner must not create a self-reference: {reference.get('full_code')}")

    for path, expected in expected_outputs(manifest).items():
        if not path.exists() or path.read_text(encoding="utf-8") != expected:
            errors.append(f"generated document drift: {path}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("error-code Manifest and generated documents are valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
