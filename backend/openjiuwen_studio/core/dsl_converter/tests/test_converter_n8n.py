#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for N8nWorkflowConverter

Run all tests:
    python -m pytest tests/test_converter_n8n.py -v

Run a specific node suite:
    python -m pytest tests/test_converter_n8n.py::TestN8nWorkflowConverter -v  # fixture-based
    python -m pytest tests/test_converter_n8n.py::TestIDGenerator -v
    python -m pytest tests/test_converter_n8n.py::TestLLMNode -v
    python -m pytest tests/test_converter_n8n.py::TestIFNode -v
    python -m pytest tests/test_converter_n8n.py::TestLoopNode -v
    python -m pytest tests/test_converter_n8n.py::TestCodeNode -v
    python -m pytest tests/test_converter_n8n.py::TestSetNode -v
    python -m pytest tests/test_converter_n8n.py::TestPluginNode -v
    python -m pytest tests/test_converter_n8n.py::TestMergeNode -v
    python -m pytest tests/test_converter_n8n.py::TestWorkflowNode -v
    python -m pytest tests/test_converter_n8n.py::TestTriggerNodes -v
    python -m pytest tests/test_converter_n8n.py::TestConnections -v
    python -m pytest tests/test_converter_n8n.py::TestExpressions -v
    python -m pytest tests/test_converter_n8n.py::TestModelMapping -v
    python -m pytest tests/test_converter_n8n.py::TestNormalizePythonMain -v
    python -m pytest tests/test_converter_n8n.py::TestFallbackNode -v
"""

import json
from pathlib import Path
import pytest

from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import N8nWorkflowConverter
from openjiuwen_studio.core.common.dsl import ComponentType


class TestableConverter(N8nWorkflowConverter):
    """Subclass that exposes protected helpers as public methods for testing."""

    def setup(self) -> "TestableConverter":
        """Reset state and return self for chaining."""
        self._reset_state()
        self.start_node_id = "start_1"
        return self

    def convert_expression(self, text: str) -> str:
        """Public wrapper for _convert_expression."""
        return self._convert_expression(text)

    def convert_expression_with_mapping(self, text: str) -> str:
        """Public wrapper for _convert_expression_with_mapping."""
        return self._convert_expression_with_mapping(text)

    def map_model(self, model_name: str, provider: str = "") -> dict:
        """Public wrapper for _map_model_to_jiuwen."""
        return self._map_model_to_jiuwen(model_name, provider)

    def normalize_python_main(self, code: str) -> str:
        """Public wrapper for _normalize_python_main."""
        return self._normalize_python_main(code)


# =============================================================================
# SHARED HELPERS
# =============================================================================

def make_node(name, n8n_type, params=None, position=None):
    """Build a minimal n8n node dict."""
    return {
        "name": name,
        "type": n8n_type,
        "parameters": params or {},
        "position": position or [100, 100],
    }


def make_workflow(*nodes, connections=None):
    """Build a minimal n8n workflow dict."""
    return {
        "name": "Test Workflow",
        "nodes": list(nodes),
        "connections": connections or {},
    }


def connect(source, target, output_index=0):
    """Return an n8n connection entry for one source→target pair."""
    slots = [[] for _ in range(output_index + 1)]
    slots[output_index] = [{"node": target, "type": "main", "index": 0}]
    return {source: {"main": slots}}


def merge_connections(*conn_dicts):
    """Merge multiple connect() dicts into one connections object."""
    merged = {}
    for d in conn_dicts:
        for src, types_map in d.items():
            if src not in merged:
                merged[src] = {}
            for conn_type, slots in types_map.items():
                if conn_type not in merged[src]:
                    merged[src][conn_type] = []
                for i, slot in enumerate(slots):
                    while len(merged[src][conn_type]) <= i:
                        merged[src][conn_type].append([])
                    merged[src][conn_type][i].extend(slot)
    return merged


def schema_from(workflow_dict):
    """Run convert_to_schema and return (nodes, edges)."""
    c = N8nWorkflowConverter()
    result = c.convert_to_schema(workflow_dict)
    return result["nodes"], result["edges"]


def node_of_type(nodes, jiuwen_type):
    """Return first node matching the given ComponentType int."""
    return next((n for n in nodes if int(n["type"]) == jiuwen_type), None)


def nodes_of_type(nodes, jiuwen_type):
    """Return all nodes matching the given ComponentType int."""
    return [n for n in nodes if int(n["type"]) == jiuwen_type]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def converter():
    """Create a fresh converter instance."""
    return N8nWorkflowConverter()


@pytest.fixture
def fixtures_dir():
    """Path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def n8n_workflow(fixtures_dir):
    """Load n8n_workflow.json fixture."""
    with open(fixtures_dir / "n8n_workflow.json") as f:
        return json.load(f)


# =============================================================================
# FIXTURE-BASED TESTS (full pipeline with real JSON)
# =============================================================================

class TestN8nWorkflowConverter:
    """Integration tests using the n8n_workflow.json fixture."""

    @staticmethod
    def test_convert_from_n8n_fixture(converter, n8n_workflow):
        """Test conversion from n8n_workflow.json fixture"""
        result = converter.convert(n8n_workflow)

        assert result.workflow_data is not None
        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_name"] == n8n_workflow["name"]
        assert result.metadata["original_nodes"] == 5

    @staticmethod
    def test_convert_creates_workflow_with_metadata(converter, n8n_workflow):
        """Test that conversion creates workflow with correct metadata"""
        result = converter.convert(n8n_workflow)

        assert "Example n8n Workflow" in result.workflow_data["name"]
        assert "Imported from n8n" in result.workflow_data["desc"]
        assert result.workflow_data["workflow_id"] is not None
        assert result.workflow_data["create_time"] is not None

    @staticmethod
    def test_convert_creates_openjiuwen_schema(converter, n8n_workflow):
        """Test that conversion creates valid OpenJiuwen schema"""
        result = converter.convert(n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        assert "nodes" in schema
        assert "edges" in schema
        assert isinstance(schema["nodes"], list)
        assert isinstance(schema["edges"], list)

    @staticmethod
    def test_convert_adds_start_and_end_nodes(converter, n8n_workflow):
        """Test that START and END nodes are added"""
        result = converter.convert(n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        node_types = [str(node["type"]) for node in schema["nodes"]]

        assert str(ComponentType.COMPONENT_TYPE_START) in node_types
        assert str(ComponentType.COMPONENT_TYPE_END) in node_types

    @staticmethod
    def test_convert_http_request_node(converter, n8n_workflow):
        """Test conversion of n8n httpRequest node to Plugin component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        plugin_nodes = [n for n in schema["nodes"]
                        if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_PLUGIN)]

        assert len(plugin_nodes) >= 1
        assert any("HTTP Request" in n["data"]["title"] for n in plugin_nodes)

    @staticmethod
    def test_convert_code_node(converter, n8n_workflow):
        """Test conversion of n8n code node to Code component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        code_nodes = [n for n in schema["nodes"]
                      if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        assert len(code_nodes) >= 1
        # converter hardcodes title as "代码"; verify we got at least one code node from the fixture
        assert all(n["data"]["title"] == "代码" for n in code_nodes)

    @staticmethod
    def test_convert_if_node(converter, n8n_workflow):
        """Test conversion of n8n IF node to Branch component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        if_nodes = [n for n in schema["nodes"]
                    if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_IF)]

        assert len(if_nodes) >= 1
        assert any("Check Condition" in n["data"]["title"] for n in if_nodes)

    @staticmethod
    def test_convert_preserves_node_positions(converter, n8n_workflow):
        """Test that node positions are preserved from fixture"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        excluded_types = {
            str(ComponentType.COMPONENT_TYPE_START),
            str(ComponentType.COMPONENT_TYPE_END)
        }
        converted_nodes = [
            n for n in schema["nodes"] if str(n["type"]) not in excluded_types
        ]

        assert len(converted_nodes) >= 5
        positions_preserved = any(
            n.get("meta", {}).get("position", {}).get("x") in [250, 450, 650, 850, 1050]
            for n in converted_nodes
        )
        assert positions_preserved

    @staticmethod
    def test_convert_connections_to_edges(converter, n8n_workflow):
        """Test that n8n connections are converted to edges"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        assert len(schema["edges"]) >= 4
        for edge in schema["edges"]:
            assert "id" in edge
            assert "sourceNodeID" in edge
            assert "targetNodeID" in edge

    @staticmethod
    def test_convert_extracts_input_output_parameters(converter, n8n_workflow):
        """Test that input/output parameters are extracted"""
        result = converter.convert(n8n_workflow)

        assert "input_parameters" in result.workflow_data
        assert "output_parameters" in result.workflow_data
        assert isinstance(result.workflow_data["input_parameters"], list)
        assert isinstance(result.workflow_data["output_parameters"], list)

    @staticmethod
    def test_convert_includes_conversion_metadata(converter, n8n_workflow):
        """Test that result includes conversion metadata"""
        result = converter.convert(n8n_workflow)

        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_name"] == "Example n8n Workflow"
        assert result.metadata["original_nodes"] == 5
        assert "converted_nodes" in result.metadata

    @staticmethod
    def test_convert_empty_workflow_raises_error(converter):
        """Test that workflow with no nodes raises error"""
        with pytest.raises(ValueError, match="n8n workflow has no nodes"):
            converter.convert({"name": "Empty", "nodes": [], "connections": {}})

    @staticmethod
    def test_add_start_end_nodes_adds_both(converter):
        """Test that add_start_end_nodes adds START and END nodes"""
        nodes = [{"id": "node1", "type": "3", "data": {"title": "Test"}}]
        edges = []

        result_nodes, result_edges = converter.add_start_end_nodes(nodes, edges)

        start_nodes = [n for n in result_nodes
                       if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_START)]
        end_nodes = [n for n in result_nodes
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_END)]

        assert len(start_nodes) == 1
        assert len(end_nodes) == 1
        assert len(result_edges) >= 2

    @staticmethod
    def test_convert_headers_from_dict(converter):
        """Test convert_headers with dict input"""
        headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        assert converter.convert_headers(headers) == headers

    @staticmethod
    def test_convert_headers_from_list(converter):
        """Test convert_headers with list input (n8n format)"""
        headers = [{"name": "Authorization", "value": "Bearer token123"}]
        result = converter.convert_headers(headers)
        assert result["Authorization"] == "Bearer token123"

    @staticmethod
    def test_convert_headers_empty(converter):
        """Test convert_headers with empty input"""
        assert converter.convert_headers(None) == {}
        assert converter.convert_headers({}) == {}
        assert converter.convert_headers([]) == {}

    @staticmethod
    def test_generate_node_id_format(converter):
        """Test that generate_node_id creates valid IDs"""
        node_id = converter.generate_node_id("n8n-nodes-base.httpRequest")
        assert node_id.startswith("httpRequest_")
        assert len(node_id) > len("httpRequest_")


# =============================================================================
# UNIT TESTS — IDGenerator
# =============================================================================

class TestIDGenerator:
    @staticmethod
    def test_sequential_ids():
        from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import IDGenerator
        gen = IDGenerator()
        assert gen.next_id("llm") == "llm_1"
        assert gen.next_id("llm") == "llm_2"
        assert gen.next_id("end") == "end_1"

    @staticmethod
    def test_reset():
        from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import IDGenerator
        gen = IDGenerator()
        gen.next_id("llm")
        gen.reset()
        assert gen.next_id("llm") == "llm_1"

    @staticmethod
    def test_independent_prefixes():
        from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import IDGenerator
        gen = IDGenerator()
        gen.next_id("a")
        gen.next_id("b")
        assert gen.next_id("a") == "a_2"
        assert gen.next_id("b") == "b_2"


# =============================================================================
# UNIT TESTS — Start / End nodes
# =============================================================================

class TestStartEndNodes:
    @staticmethod
    def _simple_workflow():
        return make_workflow(
            make_node("Code", "n8n-nodes-base.code",
                      {"language": "javaScript", "jsCode": "return [];"})
        )

    def test_start_node_created(self):
        nodes, _ = schema_from(self._simple_workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_START) is not None

    def test_end_node_created(self):
        nodes, _ = schema_from(self._simple_workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_END) is not None

    def test_only_one_start_node(self):
        nodes, _ = schema_from(self._simple_workflow())
        assert len(nodes_of_type(nodes, ComponentType.COMPONENT_TYPE_START)) == 1

    def test_start_connected_to_first_node(self):
        nodes, edges = schema_from(self._simple_workflow())
        start = node_of_type(nodes, ComponentType.COMPONENT_TYPE_START)
        assert any(e["sourceNodeID"] == start["id"] for e in edges)

    def test_last_node_connected_to_end(self):
        nodes, edges = schema_from(self._simple_workflow())
        end = node_of_type(nodes, ComponentType.COMPONENT_TYPE_END)
        assert any(e["targetNodeID"] == end["id"] for e in edges)

    def test_generic_start_has_input_property(self):
        nodes, _ = schema_from(self._simple_workflow())
        start = node_of_type(nodes, ComponentType.COMPONENT_TYPE_START)
        assert "input" in start["data"]["outputs"]["properties"]


# =============================================================================
# UNIT TESTS — Trigger nodes
# =============================================================================

class TestTriggerNodes:
    @staticmethod
    def test_webhook_trigger_merged_into_start():
        trigger = make_node("Webhook", "n8n-nodes-base.webhook")
        code = make_node("Code", "n8n-nodes-base.code",
                         {"language": "javaScript", "jsCode": ""})
        nodes, _ = schema_from(make_workflow(trigger, code, connections=connect("Webhook", "Code")))
        start = node_of_type(nodes, ComponentType.COMPONENT_TYPE_START)
        assert "body" in start["data"]["outputs"]["properties"]

    @staticmethod
    def test_only_one_start_node_with_trigger():
        trigger = make_node("Webhook", "n8n-nodes-base.webhook")
        code = make_node("Code", "n8n-nodes-base.code",
                         {"language": "javaScript", "jsCode": ""})
        nodes, _ = schema_from(make_workflow(trigger, code, connections=connect("Webhook", "Code")))
        assert len(nodes_of_type(nodes, ComponentType.COMPONENT_TYPE_START)) == 1

    @staticmethod
    def test_chat_trigger_outputs_chat_input():
        trigger = make_node("Chat", "n8n-nodes-base.chatTrigger")
        code = make_node("Code", "n8n-nodes-base.code",
                         {"language": "javaScript", "jsCode": ""})
        nodes, _ = schema_from(make_workflow(trigger, code, connections=connect("Chat", "Code")))
        start = node_of_type(nodes, ComponentType.COMPONENT_TYPE_START)
        assert "chatInput" in start["data"]["outputs"]["properties"]

    @staticmethod
    def test_form_trigger_maps_field_names():
        trigger = make_node("Form", "n8n-nodes-base.formTrigger", {
            "formFields": {"values": [
                {"fieldLabel": "City", "requiredField": True},
                {"fieldLabel": "Date"},
            ]}
        })
        code = make_node("Code", "n8n-nodes-base.code",
                         {"language": "javaScript", "jsCode": ""})
        nodes, _ = schema_from(make_workflow(trigger, code, connections=connect("Form", "Code")))
        start = node_of_type(nodes, ComponentType.COMPONENT_TYPE_START)
        props = start["data"]["outputs"]["properties"]
        assert "city" in props
        assert "date" in props

    @staticmethod
    def test_cron_treated_as_trigger():
        trigger = make_node("Cron", "n8n-nodes-base.cron")
        code = make_node("Code", "n8n-nodes-base.code",
                         {"language": "javaScript", "jsCode": ""})
        nodes, _ = schema_from(make_workflow(trigger, code, connections=connect("Cron", "Code")))
        assert len(nodes_of_type(nodes, ComponentType.COMPONENT_TYPE_START)) == 1


# =============================================================================
# UNIT TESTS — LLM node
# =============================================================================

class TestLLMNode:
    @staticmethod
    def _workflow(params=None):
        return make_workflow(make_node("Agent", "n8n-nodes-base.agent", params or {
            "text": "Hello {{input}}",
            "options": {"systemMessage": "You are helpful."}
        }))

    def test_llm_node_created(self):
        nodes, _ = schema_from(self._workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM) is not None

    def test_llm_has_system_prompt(self):
        nodes, _ = schema_from(self._workflow())
        llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
        assert llm["data"]["inputs"]["llmParam"]["systemPrompt"]["content"] == "You are helpful."

    def test_llm_has_user_prompt(self):
        nodes, _ = schema_from(self._workflow())
        llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
        assert "{{input}}" in llm["data"]["inputs"]["llmParam"]["prompt"]["content"]

    @staticmethod
    def test_llm_default_prompt_when_empty():
        nodes, _ = schema_from(make_workflow(make_node("A", "n8n-nodes-base.agent")))
        llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
        assert len(llm["data"]["inputs"]["llmParam"]["prompt"]["content"]) > 0

    def test_llm_output_has_output_property(self):
        nodes, _ = schema_from(self._workflow())
        llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
        assert "output" in llm["data"]["outputs"]["properties"]

    def test_llm_connected_to_end(self):
        nodes, edges = schema_from(self._workflow())
        llm = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM)
        end = node_of_type(nodes, ComponentType.COMPONENT_TYPE_END)
        assert any(e["sourceNodeID"] == llm["id"] and e["targetNodeID"] == end["id"]
                   for e in edges)

    @staticmethod
    def test_langchain_agent_maps_to_llm():
        nodes, _ = schema_from(
            make_workflow(make_node("LCAgent", "@n8n/n8n-nodes-langchain.agent"))
        )
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_LLM) is not None


# =============================================================================
# UNIT TESTS — IF / Selector node
# =============================================================================

class TestIFNode:
    @staticmethod
    def _two_branch_workflow():
        if_node = make_node("IF", "n8n-nodes-base.if")
        true_code = make_node("T", "n8n-nodes-base.code",
                              {"language": "javaScript", "jsCode": ""})
        false_code = make_node("F", "n8n-nodes-base.code",
                               {"language": "javaScript", "jsCode": ""})
        conns = merge_connections(
            connect("IF", "T", output_index=0),
            connect("IF", "F", output_index=1),
        )
        return make_workflow(if_node, true_code, false_code, connections=conns)

    @staticmethod
    def _one_branch_workflow():
        if_node = make_node("IF", "n8n-nodes-base.if")
        true_code = make_node("T", "n8n-nodes-base.code",
                              {"language": "javaScript", "jsCode": ""})
        return make_workflow(if_node, true_code, connections=connect("IF", "T", output_index=0))

    def test_if_node_created(self):
        nodes, _ = schema_from(self._two_branch_workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF) is not None

    def test_if_has_two_branches(self):
        nodes, _ = schema_from(self._two_branch_workflow())
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        assert len(selector["data"]["branches"]) == 2

    def test_true_branch_has_condition(self):
        nodes, _ = schema_from(self._two_branch_workflow())
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        assert len(selector["data"]["branches"][0]["conditions"]) > 0

    def test_else_branch_has_no_conditions(self):
        nodes, _ = schema_from(self._two_branch_workflow())
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        assert selector["data"]["branches"][1]["conditions"] == []

    def test_branch_edges_have_source_port(self):
        nodes, edges = schema_from(self._two_branch_workflow())
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        sel_edges = [e for e in edges if e["sourceNodeID"] == selector["id"]]
        assert all("sourcePortID" in e for e in sel_edges)

    def test_single_branch_else_goes_to_end(self):
        """Core fix: else branch must connect to end when only true branch is wired."""
        nodes, edges = schema_from(self._one_branch_workflow())
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        end = node_of_type(nodes, ComponentType.COMPONENT_TYPE_END)
        else_branch_id = selector["data"]["branches"][1]["branchId"]
        assert any(
            e["sourceNodeID"] == selector["id"]
            and e["targetNodeID"] == end["id"]
            and e.get("sourcePortID") == else_branch_id
            for e in edges
        ), "Else branch must be wired to the end node when no explicit target exists"

    @staticmethod
    def test_switch_maps_to_if():
        nodes, _ = schema_from(make_workflow(make_node("S", "n8n-nodes-base.switch")))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF) is not None


# =============================================================================
# UNIT TESTS — Loop node
# =============================================================================

class TestLoopNode:
    @staticmethod
    def _workflow(batch_size=5):
        return make_workflow(
            make_node("Loop", "n8n-nodes-base.splitInBatches", {"batchSize": batch_size})
        )

    def test_loop_node_created(self):
        nodes, _ = schema_from(self._workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_LOOP) is not None

    def test_loop_batch_size_preserved(self):
        nodes, _ = schema_from(self._workflow(batch_size=7))
        loop = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LOOP)
        assert loop["data"]["inputs"]["batchSize"] == 7

    def test_loop_has_two_blocks(self):
        nodes, _ = schema_from(self._workflow())
        loop = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LOOP)
        assert len(loop["blocks"]) == 2

    def test_loop_block_types(self):
        nodes, _ = schema_from(self._workflow())
        loop = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LOOP)
        block_types = {int(b["type"]) for b in loop["blocks"]}
        assert ComponentType.COMPONENT_TYPE_BLOCK_START in block_types
        assert ComponentType.COMPONENT_TYPE_BLOCK_END in block_types

    def test_loop_outputs_results(self):
        nodes, _ = schema_from(self._workflow())
        loop = node_of_type(nodes, ComponentType.COMPONENT_TYPE_LOOP)
        assert "results" in loop["data"]["outputs"]["properties"]


# =============================================================================
# UNIT TESTS — Code node
# =============================================================================

class TestCodeNode:
    @staticmethod
    def _workflow(lang="javaScript", js_code="return [];", py_code=""):
        params = {"language": lang}
        if lang == "javaScript":
            params["jsCode"] = js_code
        else:
            params["pythonCode"] = py_code
        return make_workflow(make_node("Code", "n8n-nodes-base.code", params))

    def test_code_node_created(self):
        nodes, _ = schema_from(self._workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE) is not None

    def test_javascript_language_preserved(self):
        nodes, _ = schema_from(self._workflow(lang="javaScript"))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert code["data"]["inputs"]["language"] == "javascript"

    def test_python_language_preserved(self):
        nodes, _ = schema_from(self._workflow(lang="python", js_code="", py_code="x = 1"))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert code["data"]["inputs"]["language"] == "python"

    def test_js_code_wrapped_in_main(self):
        nodes, _ = schema_from(self._workflow(js_code="const x = 1;"))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "function main" in code["data"]["inputs"]["code"]

    def test_python_code_wrapped_in_main(self):
        nodes, _ = schema_from(self._workflow(lang="python", js_code="", py_code="x = 1"))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "def main" in code["data"]["inputs"]["code"]

    def test_python_main_not_double_wrapped(self):
        py = "def main(args):\n    return {'result': 1}"
        nodes, _ = schema_from(self._workflow(lang="python", js_code="", py_code=py))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert code["data"]["inputs"]["code"].count("def main") == 1

    def test_code_outputs_result(self):
        nodes, _ = schema_from(self._workflow())
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "result" in code["data"]["outputs"]["properties"]

    def test_code_has_exception_config(self):
        nodes, _ = schema_from(self._workflow())
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "exceptionConfig" in code["data"]

    @staticmethod
    def test_function_node_maps_to_code():
        node = make_node("Fn", "n8n-nodes-base.function", {"functionCode": "return items;"})
        nodes, _ = schema_from(make_workflow(node))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE) is not None


# =============================================================================
# UNIT TESTS — Set node
# =============================================================================

class TestSetNode:
    @staticmethod
    def _params(assignments):
        return {"assignments": {"assignments": assignments}}

    def test_set_node_produces_code_node(self):
        params = self._params([{"name": "foo", "value": "bar", "type": "string"}])
        nodes, _ = schema_from(make_workflow(make_node("Set", "n8n-nodes-base.set", params)))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE) is not None

    def test_set_node_code_contains_field_name(self):
        params = self._params([{"name": "myField", "value": "hello", "type": "string"}])
        nodes, _ = schema_from(make_workflow(make_node("Set", "n8n-nodes-base.set", params)))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "myField" in code["data"]["inputs"]["code"]

    @staticmethod
    def test_set_node_raw_mode():
        params = {"mode": "raw", "jsonOutput": '{"key": "value"}'}
        nodes, _ = schema_from(make_workflow(make_node("Set", "n8n-nodes-base.set", params)))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "raw_json" in code["data"]["inputs"]["code"]

    def test_set_node_boolean_value(self):
        params = self._params([{"name": "flag", "value": True, "type": "boolean"}])
        nodes, _ = schema_from(make_workflow(make_node("Set", "n8n-nodes-base.set", params)))
        code = node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)
        assert "True" in code["data"]["inputs"]["code"]

    def test_passthrough_set_node_optimised_away(self):
        """Set node with pure $json refs should be merged into its predecessor."""
        params = self._params([{"name": "city", "value": "={{ $json.city }}", "type": "string"}])
        trigger = make_node("Trigger", "n8n-nodes-base.manualTrigger")
        set_node = make_node("PassSet", "n8n-nodes-base.set", params)
        after = make_node("After", "n8n-nodes-base.code",
                          {"language": "javaScript", "jsCode": ""})
        conns = merge_connections(connect("Trigger", "PassSet"), connect("PassSet", "After"))
        nodes, _ = schema_from(make_workflow(trigger, set_node, after, connections=conns))
        code_titles = [n["data"].get("title", "") for n in nodes_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)]
        assert not any("PassSet" in t for t in code_titles)


# =============================================================================
# UNIT TESTS — Plugin node
# =============================================================================

class TestPluginNode:
    @staticmethod
    def _workflow(params=None):
        return make_workflow(
            make_node("HTTP", "n8n-nodes-base.httpRequest",
                      params or {"url": "https://api.example.com", "method": "GET"})
        )

    def test_http_maps_to_plugin(self):
        nodes, _ = schema_from(self._workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN) is not None

    def test_plugin_has_plugin_param(self):
        nodes, _ = schema_from(self._workflow())
        plugin = node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN)
        assert "pluginParam" in plugin["data"]["inputs"]

    def test_plugin_raw_params_stored(self):
        """n8n params are forwarded in _n8n_params for downstream use."""
        nodes, _ = schema_from(self._workflow(params={"url": "https://test.io", "method": "POST"}))
        plugin = node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN)
        assert plugin["data"]["inputs"]["_n8n_params"]["url"] == "https://test.io"
        assert plugin["data"]["inputs"]["_n8n_params"]["method"] == "POST"

    def test_plugin_outputs_structure(self):
        nodes, _ = schema_from(self._workflow())
        plugin = node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN)
        props = plugin["data"]["outputs"]["properties"]
        assert "error_code" in props
        assert "data" in props

    def test_plugin_connected_to_end(self):
        nodes, edges = schema_from(self._workflow())
        plugin = node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN)
        end = node_of_type(nodes, ComponentType.COMPONENT_TYPE_END)
        assert any(e["sourceNodeID"] == plugin["id"] and e["targetNodeID"] == end["id"]
                   for e in edges)

    @staticmethod
    def test_slack_app_node_maps_to_plugin():
        node = make_node("Slack", "n8n-nodes-base.slack", {"operation": "message"})
        nodes, _ = schema_from(make_workflow(node))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_PLUGIN) is not None


# =============================================================================
# UNIT TESTS — Merge node
# =============================================================================

class TestMergeNode:
    @staticmethod
    def test_merge_node_created():
        nodes, _ = schema_from(make_workflow(make_node("Merge", "n8n-nodes-base.merge")))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_VARIABLE_MERGE) is not None

    @staticmethod
    def test_merge_outputs_merged_property():
        nodes, _ = schema_from(make_workflow(make_node("Merge", "n8n-nodes-base.merge")))
        merge = node_of_type(nodes, ComponentType.COMPONENT_TYPE_VARIABLE_MERGE)
        assert "merged" in merge["data"]["outputs"]["properties"]

    @staticmethod
    def test_merge_has_groups_config():
        nodes, _ = schema_from(make_workflow(make_node("Merge", "n8n-nodes-base.merge")))
        merge = node_of_type(nodes, ComponentType.COMPONENT_TYPE_VARIABLE_MERGE)
        assert "groups" in merge["data"]["configs"]


# =============================================================================
# UNIT TESTS — SubWorkflow node
# =============================================================================

class TestWorkflowNode:
    @staticmethod
    def _workflow():
        return make_workflow(
            make_node("SubWF", "n8n-nodes-base.executeWorkflow",
                      {"workflowId": "wf-123", "mode": "sync"})
        )

    def test_sub_workflow_node_created(self):
        nodes, _ = schema_from(self._workflow())
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_SUB_WORKFLOW) is not None

    def test_sub_workflow_id_preserved(self):
        nodes, _ = schema_from(self._workflow())
        wf = node_of_type(nodes, ComponentType.COMPONENT_TYPE_SUB_WORKFLOW)
        assert wf["data"]["inputs"]["workflowParam"]["workflowId"] == "wf-123"

    def test_sub_workflow_mode_preserved(self):
        nodes, _ = schema_from(self._workflow())
        wf = node_of_type(nodes, ComponentType.COMPONENT_TYPE_SUB_WORKFLOW)
        assert wf["data"]["inputs"]["workflowParam"]["mode"] == "sync"

    def test_sub_workflow_outputs_result(self):
        nodes, _ = schema_from(self._workflow())
        wf = node_of_type(nodes, ComponentType.COMPONENT_TYPE_SUB_WORKFLOW)
        assert "result" in wf["data"]["outputs"]["properties"]


# =============================================================================
# UNIT TESTS — Connections / Edges
# =============================================================================

class TestConnections:
    @staticmethod
    def test_linear_chain_produces_edges():
        a = make_node("A", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        b = make_node("B", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        _, edges = schema_from(make_workflow(a, b, connections=connect("A", "B")))
        assert len(edges) >= 2

    @staticmethod
    def test_no_duplicate_edges():
        a = make_node("A", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        b = make_node("B", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        _, edges = schema_from(make_workflow(a, b, connections=connect("A", "B")))
        pairs = [(e["sourceNodeID"], e["targetNodeID"]) for e in edges]
        assert len(pairs) == len(set(pairs))

    @staticmethod
    def test_if_branch_edges_have_source_port():
        if_node = make_node("IF", "n8n-nodes-base.if")
        t = make_node("T", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        f = make_node("F", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        conns = merge_connections(connect("IF", "T", 0), connect("IF", "F", 1))
        nodes, edges = schema_from(make_workflow(if_node, t, f, connections=conns))
        selector = node_of_type(nodes, ComponentType.COMPONENT_TYPE_IF)
        sel_edges = [e for e in edges if e["sourceNodeID"] == selector["id"]]
        assert all("sourcePortID" in e for e in sel_edges)

    @staticmethod
    def test_code_edges_have_source_port_zero():
        a = make_node("A", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        b = make_node("B", "n8n-nodes-base.code", {"language": "javaScript", "jsCode": ""})
        nodes, edges = schema_from(make_workflow(a, b, connections=connect("A", "B")))
        first_code_id = nodes_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE)[0]["id"]
        code_edges = [e for e in edges if e.get("sourceNodeID") == first_code_id]
        assert all(e.get("sourcePortID") == "0" for e in code_edges)

    @staticmethod
    def test_ai_subnode_not_a_standalone_node():
        model = make_node("Model", "@n8n/n8n-nodes-langchain.lmChatOpenAi")
        agent = make_node("Agent", "@n8n/n8n-nodes-langchain.agent")
        conns = {"Model": {"ai_languageModel": [[{"node": "Agent", "type": "ai_languageModel", "index": 0}]]}}
        nodes, _ = schema_from(make_workflow(model, agent, connections=conns))
        assert not any("Model" in n.get("data", {}).get("title", "") for n in nodes)


# =============================================================================
# UNIT TESTS — Expression conversion
# =============================================================================

class TestExpressions:
    @staticmethod
    def make_converter() -> TestableConverter:
        return TestableConverter().setup()

    def test_json_dot_notation(self):
        assert self.make_converter().convert_expression("={{ $json.city }}") == "{{city}}"

    def test_json_bracket_notation(self):
        assert self.make_converter().convert_expression('={{ $json["my field"] }}') == "{{my_field}}"

    def test_node_reference_expression(self):
        assert self.make_converter().convert_expression("={{ $('SomeNode').item.json.name }}") == "{{name}}"

    def test_leading_equals_stripped(self):
        result = self.make_converter().convert_expression("={{ $json.foo }}")
        assert "=" not in result and "foo" in result

    def test_plain_text_unchanged(self):
        assert self.make_converter().convert_expression("Hello World") == "Hello World"

    def test_display_placeholder_single_braced(self):
        result = self.make_converter().convert_expression("{{Weather Phenomenon, e.g. Sunny}}")
        assert result.startswith("{") and not result.startswith("{{")

    def test_template_var_kept_double_brace(self):
        assert self.make_converter().convert_expression("{{city}}") == "{{city}}"

    def test_field_mapping_applied(self):
        c = self.make_converter()
        c.field_name_map = {"City": "city"}
        assert c.convert_expression_with_mapping('={{ $json["City"] }}') == "{{city}}"


# =============================================================================
# UNIT TESTS — Model mapping
# =============================================================================

class TestModelMapping:
    @staticmethod
    def _map(model_name, provider=""):
        return TestableConverter().setup().map_model(model_name, provider)

    def test_gpt4_maps_to_openai(self):
        assert self._map("gpt-4-turbo")["name"] == "openai"

    def test_claude_maps_to_anthropic(self):
        assert self._map("claude-3-opus")["name"] == "anthropic"

    def test_qwen_maps_to_qwen(self):
        assert self._map("qwen-max")["name"] == "Qwen"

    def test_deepseek_maps_to_deepseek(self):
        assert self._map("deepseek-chat")["name"] == "deepseek"

    def test_llama_maps_to_ollama(self):
        assert self._map("llama-3")["name"] == "ollama"

    def test_gemini_maps_to_gemini(self):
        assert self._map("gemini-pro")["name"] == "gemini"

    def test_unknown_uses_provider(self):
        assert self._map("some-model", provider="myprovider")["name"] == "myprovider"


# =============================================================================
# UNIT TESTS — Normalize Python main
# =============================================================================

class TestNormalizePythonMain:
    @staticmethod
    def _norm(code):
        return TestableConverter().setup().normalize_python_main(code)

    def test_already_correct_unchanged(self):
        code = "def main(args):\n    return 1"
        assert self._norm(code) == code

    def test_other_def_renamed(self):
        result = self._norm("def process(x, y):\n    return x + y")
        assert "def main(args):" in result
        assert "def process" not in result

    def test_no_def_wrapped(self):
        result = self._norm("x = 1\nreturn x")
        assert "def main(args):" in result
        assert "    x = 1" in result


# =============================================================================
# UNIT TESTS — Fallback / unsupported node
# =============================================================================

class TestFallbackNode:
    @staticmethod
    def test_unknown_node_becomes_code():
        nodes, _ = schema_from(make_workflow(make_node("X", "n8n-nodes-base.unknownXYZ")))
        assert node_of_type(nodes, ComponentType.COMPONENT_TYPE_CODE) is not None

    @staticmethod
    def test_unknown_node_adds_warning():
        c = N8nWorkflowConverter()
        c.convert_to_schema(make_workflow(make_node("Mystery", "n8n-nodes-base.unknownXYZ")))
        assert any("Mystery" in w for w in c.report.to_warnings_list())