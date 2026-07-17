"""Assert agent_builder source does NOT import agent_runtime (architectural decoupling).

agent_builder is an independent microservice and must not depend on agent_runtime.
The shared mechanism layer lives in packages/model_service (which both hosts use);
agent_builder talks to model_service via its ports, never to agent_runtime directly.

This is the reverse of tests/test_runtime_decoupled.py (which asserts agent_runtime
does not import agent_builder). Substring "agent_runtime" alone in comments/docstrings
is a false positive — we check actual import statements only.
"""

import pathlib
import re


def test_no_agent_runtime_imports_in_builder_source():
    builder_root = pathlib.Path("agent_builder")
    pattern = re.compile(r"^\s*(from\s+agent_runtime|import\s+agent_runtime)\b", re.M)
    hits = []
    for p in builder_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        if "tests" in p.parts:
            # Tests may reference agent_runtime for cross-cutting assertions; not a
            # production dependency.
            continue
        text = p.read_text(encoding="utf-8")
        for m in pattern.finditer(text):
            hits.append(f"{p}: {m.group(0).strip()}")
    assert not hits, f"agent_builder still imports agent_runtime: {hits}"
