"""Tests for the EIBuilder entrypoint — CLI surface + import safety."""

import os
import subprocess
import sys


VENV_PY = "agent-runtime/.venv/Scripts/python.exe"


def test_eibuilder_module_imports():
    import importlib

    mod = importlib.import_module("agent_builder.EIBuilder_base")
    assert hasattr(mod, "main")
    assert callable(mod.main)


def test_eibuilder_cli_help_exits_zero():
    # `--help` must exit 0 and mention --host/--port/--log-level.
    proc = subprocess.run(
        [os.path.normpath(VENV_PY), "-m", "agent_builder.EIBuilder", "--help"],
        capture_output=True,
        text=True,
        cwd=".",
    )
    assert proc.returncode == 0, proc.stderr
    assert "--host" in proc.stdout
    assert "--port" in proc.stdout
    assert "--log-level" in proc.stdout
