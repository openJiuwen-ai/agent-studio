# -*- coding: UTF-8 -*-
# pylint: disable=protected-access
"""_compile_nested_patched must stay call-compatible with core PregelGraph._compile.

core d8cd86e12 (0.1.17_hotfix line) added a ``nodes`` kwarg to
``PregelGraph._compile`` and ``compile()`` passes it by keyword. This patch
replaces ``_compile`` wholesale, so an unsynced signature makes workflow
compilation raise TypeError before any node starts running (the "execute
button does nothing" failure mode).
"""
import inspect

from types import SimpleNamespace

from openjiuwen.core.graph.graph import PregelGraph

from jiuwen.extension.patches import nested_branch_barrier_patch as nbp


def _empty_graph() -> SimpleNamespace:
    """Minimal stand-in whose Step-1 scans (edges / branches / branch_targets /
    waits) all iterate empty, so a call runs straight through to the Step-2
    original-compile forward that these tests target.
    """
    return SimpleNamespace(edges=[], branches={}, branch_targets={}, waits=set())


class TestNestedBarrierCompileSync:
    def test_patched_signature_covers_live_core_compile_params(self):
        """Whatever params the installed core _compile takes, the patched
        replacement must accept them all — core compile() calls it by keyword.
        """
        core_params = set(inspect.signature(PregelGraph._compile).parameters)
        patch_params = set(inspect.signature(nbp._compile_nested_patched).parameters)
        assert core_params <= patch_params

    def test_nodes_forwarded_when_original_accepts_it(self, monkeypatch):
        """Hotfix-line core: nodes must reach the original, not be swallowed."""
        calls = []

        def original_with_nodes(self, graph_store=None, step_callback=None, nodes=None):
            calls.append(
                {"graph_store": graph_store, "step_callback": step_callback, "nodes": nodes}
            )
            return "COMPILED"

        monkeypatch.setattr(nbp, "_original_compile", original_with_nodes)
        result = nbp._compile_nested_patched(
            _empty_graph(), graph_store="gs", step_callback="cb", nodes=["n1", "n2"]
        )

        assert result == "COMPILED"
        assert calls == [
            {"graph_store": "gs", "step_callback": "cb", "nodes": ["n1", "n2"]}
        ]

    def test_nodes_dropped_when_original_lacks_it(self, monkeypatch):
        """Develop-line core has no nodes param — forwarding must degrade to the
        two-kwarg call instead of raising TypeError.
        """
        calls = []

        def original_without_nodes(self, graph_store=None, step_callback=None):
            calls.append({"graph_store": graph_store, "step_callback": step_callback})
            return "COMPILED"

        monkeypatch.setattr(nbp, "_original_compile", original_without_nodes)
        result = nbp._compile_nested_patched(
            _empty_graph(), graph_store="gs", step_callback="cb", nodes=["n1"]
        )

        assert result == "COMPILED"
        assert calls == [{"graph_store": "gs", "step_callback": "cb"}]
