"""Assert agent_runtime no longer imports agent_builder (full decoupling)."""

import os
import subprocess

# Resolve to an absolute path: Windows CreateProcess with shell=False won't
# resolve a forward-slash relative executable path (WinError 2). The assertion
# intent (agent_runtime.serve.server imports cleanly) is unchanged.
VENV_PY = os.path.abspath("agent-runtime/.venv/Scripts/python.exe")


def test_runtime_server_imports_without_agent_builder():
    # agent_runtime.serve.server must import cleanly (no removed-name errors).
    proc = subprocess.run(
        [VENV_PY, "-c", "import agent_runtime.serve.server"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr


def test_no_agent_builder_imports_in_runtime_source():
    # Assert no real import of the agent_builder package remains.
    # (Substring "agent_builder" alone is a false positive — agent_runtime has
    # an unrelated local `agent_builder_error_handler` function and an
    # `AgentBuilderError` exception. We check actual import statements instead.)
    import pathlib
    import re

    runtime_root = pathlib.Path("agent-runtime/agent_runtime")
    pattern = re.compile(r"^\s*(from\s+agent_builder|import\s+agent_builder)\b", re.M)
    hits = []
    for p in runtime_root.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        for m in pattern.finditer(text):
            hits.append(f"{p}: {m.group(0).strip()}")
    assert not hits, f"agent_runtime still imports agent_builder: {hits}"
