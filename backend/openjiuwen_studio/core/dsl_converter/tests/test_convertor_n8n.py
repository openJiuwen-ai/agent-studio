#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for N8nWorkflowConvertor

Tests conversion of n8n format workflows to OpenJiuwen format.
"""

import pytest
import json
from pathlib import Path

from openjiuwen_studio.core.dsl_converter.convertor.convertor_n8n import N8nWorkflowConvertor
from openjiuwen_studio.core.common.dsl import ComponentType


class TestN8nWorkflowConvertor:
    """Test suite for N8nWorkflowConvertor"""

    @pytest.fixture
    def convertor(self):
        """Create convertor instance"""
        return N8nWorkflowConvertor()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path"""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def simple_n8n_workflow(self):
        """Create simple n8n workflow"""
        return {
            "name": "Simple n8n Workflow",
            "nodes": [
                {
                    "id": "node1",
                    "name": "HTTP Request",
                    "type": "n8n-nodes-base.httpRequest",
                    "position": [100, 200],
                    "parameters": {
                        "url": "https://api.example.com",
                        "method": "GET"
                    }
                },
                {
                    "id": "node2",
                    "name": "Process Code",
                    "type": "n8n-nodes-base.code",
                    "position": [300, 200],
                    "parameters": {
                        "code": "return items;"
                    }
                }
            ],
            "connections": {
                "HTTP Request": {
                    "main": [[{"node": "Process Code", "type": "main", "index": 0}]]
                }
            }
        }

    def test_convert_from_fixture(self, convertor, fixtures_dir):
        """Test conversion from n8n fixture file"""
        fixture_file = fixtures_dir / "n8n_workflow.json"
        with open(fixture_file) as f:
            data = json.load(f)

        result = convertor.convert(data)

        assert result.workflow_data is not None
        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_name"] == data["name"]

    def test_convert_creates_workflow_with_metadata(self, convertor, simple_n8n_workflow):
        """Test that conversion creates workflow with correct metadata"""
        result = convertor.convert(simple_n8n_workflow)

        assert result.workflow_data["name"] == "Simple n8n Workflow (Imported)"
        assert "Imported from n8n" in result.workflow_data["desc"]
        assert result.workflow_data["workflow_id"] is not None
        assert result.workflow_data["create_time"] is not None

    def test_convert_creates_openjiuwen_schema(self, convertor, simple_n8n_workflow):
        """Test that conversion creates valid OpenJiuwen schema"""
        result = convertor.convert(simple_n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        assert "nodes" in schema
        assert "edges" in schema
        assert isinstance(schema["nodes"], list)
        assert isinstance(schema["edges"], list)

    def test_convert_adds_start_and_end_nodes(self, convertor, simple_n8n_workflow):
        """Test that START and END nodes are added"""
        result = convertor.convert(simple_n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        node_types = [str(node["type"]) for node in schema["nodes"]]

        # Should have START (1) and END (2)
        assert str(ComponentType.COMPONENT_TYPE_START) in node_types
        assert str(ComponentType.COMPONENT_TYPE_END) in node_types

    def test_convert_http_request_to_plugin(self, convertor):
        """Test conversion of n8n httpRequest to Plugin component"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "API Call",
                "type": "n8n-nodes-base.httpRequest",
                "position": [100, 200],
                "parameters": {
                    "url": "https://api.test.com",
                    "method": "POST"
                }
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # Find the converted node (not START/END)
        plugin_nodes = [n for n in schema["nodes"]
                       if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_PLUGIN)]

        assert len(plugin_nodes) == 1
        assert plugin_nodes[0]["data"]["title"] == "API Call"

    def test_convert_code_node_to_code_component(self, convertor):
        """Test conversion of n8n code node to Code component"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Process",
                "type": "n8n-nodes-base.code",
                "position": [100, 200],
                "parameters": {
                    "code": "const result = 42;\nreturn result;"
                }
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        code_nodes = [n for n in schema["nodes"]
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        assert len(code_nodes) == 1
        assert "const result = 42;" in code_nodes[0]["data"]["configs"]["code"]

    def test_convert_if_node_to_branch_component(self, convertor):
        """Test conversion of n8n IF node to Branch component"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Check Condition",
                "type": "n8n-nodes-base.if",
                "position": [100, 200],
                "parameters": {
                    "conditions": {"value": "test"}
                }
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        if_nodes = [n for n in schema["nodes"]
                   if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_IF)]

        assert len(if_nodes) == 1
        assert "branches" in if_nodes[0]["data"]

    def test_convert_preserves_node_positions(self, convertor):
        """Test that node positions are preserved"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Node",
                "type": "n8n-nodes-base.code",
                "position": [250, 350],
                "parameters": {}
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # Find converted node (not START/END)
        code_nodes = [n for n in schema["nodes"]
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        assert code_nodes[0]["meta"]["position"]["x"] == 250
        assert code_nodes[0]["meta"]["position"]["y"] == 350

    def test_convert_creates_fallback_for_unsupported_type(self, convertor):
        """Test that unsupported node types get fallback CODE component"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Unsupported",
                "type": "n8n-nodes-base.unsupportedNodeType",
                "position": [100, 200],
                "parameters": {"test": "value"}
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)

        # Should have warning about failed conversion
        assert len(result.warnings) > 0

        schema = json.loads(result.workflow_data["schema"])
        # Should create fallback CODE node
        code_nodes = [n for n in schema["nodes"]
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        assert len(code_nodes) >= 1
        # Fallback should have TODO in title or code
        fallback = code_nodes[0]
        has_todo = ("TODO" in fallback["data"]["title"] or
                   "TODO" in fallback["data"]["configs"]["code"])
        assert has_todo

    def test_convert_connections_to_edges(self, convertor, simple_n8n_workflow):
        """Test that n8n connections are converted to edges"""
        result = convertor.convert(simple_n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])

        # Should have edges connecting nodes (plus START/END connections)
        assert len(schema["edges"]) >= 1

        # Check edge structure
        for edge in schema["edges"]:
            assert "id" in edge
            assert "source" in edge
            assert "target" in edge

    def test_convert_extracts_input_output_parameters(self, convertor, simple_n8n_workflow):
        """Test that input/output parameters are extracted"""
        result = convertor.convert(simple_n8n_workflow)

        assert "input_parameters" in result.workflow_data
        assert "output_parameters" in result.workflow_data
        assert isinstance(result.workflow_data["input_parameters"], list)
        assert isinstance(result.workflow_data["output_parameters"], list)

    def test_convert_includes_conversion_metadata(self, convertor, simple_n8n_workflow):
        """Test that result includes conversion metadata"""
        result = convertor.convert(simple_n8n_workflow)

        assert "source" in result.metadata
        assert "original_name" in result.metadata
        assert "converted_nodes" in result.metadata
        assert "original_nodes" in result.metadata

        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_nodes"] == 2

    def test_convert_empty_workflow_raises_error(self, convertor):
        """Test that workflow with no nodes raises error"""
        n8n_workflow = {
            "name": "Empty",
            "nodes": [],
            "connections": {}
        }

        with pytest.raises(ValueError, match="n8n workflow has no nodes"):
            convertor.convert(n8n_workflow)

    def test_convert_handles_function_node(self, convertor):
        """Test conversion of n8n function node (alternative to code)"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Function",
                "type": "n8n-nodes-base.function",
                "position": [100, 200],
                "parameters": {
                    "functionCode": "return items;"
                }
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        code_nodes = [n for n in schema["nodes"]
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        assert len(code_nodes) == 1
        assert "return items;" in code_nodes[0]["data"]["configs"]["code"]

    def test_convert_handles_merge_node(self, convertor):
        """Test conversion of n8n merge node"""
        n8n_workflow = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "name": "Merge Data",
                "type": "n8n-nodes-base.merge",
                "position": [100, 200],
                "parameters": {}
            }],
            "connections": {}
        }

        result = convertor.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        merge_nodes = [n for n in schema["nodes"]
                      if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_VARIABLE_MERGE)]

        assert len(merge_nodes) == 1

    def test_add_start_end_nodes_connects_entry_points(self, convertor):
        """Test that START node connects to entry points"""
        nodes = [
            {"id": "node1", "type": "3"},
            {"id": "node2", "type": "3"}
        ]
        edges = [
            {"source": "node2", "target": "node3"}
        ]

        result_nodes, result_edges = convertor._add_start_end_nodes(nodes, edges)

        # Should have START node
        start_nodes = [n for n in result_nodes
                      if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_START)]
        assert len(start_nodes) == 1

        # START should connect to node1 (has no incoming edges)
        start_id = start_nodes[0]["id"]
        start_edges = [e for e in result_edges if e["source"] == start_id]
        assert len(start_edges) >= 1
        assert any(e["target"] == "node1" for e in start_edges)

    def test_add_start_end_nodes_connects_exit_points(self, convertor):
        """Test that END node connects to exit points"""
        nodes = [
            {"id": "node1", "type": "3"},
            {"id": "node2", "type": "3"}
        ]
        edges = [
            {"source": "node1", "target": "node2"}
        ]

        result_nodes, result_edges = convertor._add_start_end_nodes(nodes, edges)

        # Should have END node
        end_nodes = [n for n in result_nodes
                    if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_END)]
        assert len(end_nodes) == 1

        # node2 (has no outgoing edges) should connect to END
        end_id = end_nodes[0]["id"]
        end_edges = [e for e in result_edges if e["target"] == end_id]
        assert len(end_edges) >= 1
        assert any(e["source"] == "node2" for e in end_edges)

    def test_convert_headers_from_dict(self, convertor):
        """Test _convert_headers with dict input"""
        headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        result = convertor._convert_headers(headers)
        assert result == headers

    def test_convert_headers_from_list(self, convertor):
        """Test _convert_headers with list input (n8n format)"""
        headers = [
            {"name": "Authorization", "value": "Bearer token"},
            {"name": "Content-Type", "value": "application/json"}
        ]
        result = convertor._convert_headers(headers)
        assert result["Authorization"] == "Bearer token"
        assert result["Content-Type"] == "application/json"

    def test_convert_headers_empty(self, convertor):
        """Test _convert_headers with empty input"""
        assert convertor._convert_headers(None) == {}
        assert convertor._convert_headers({}) == {}
        assert convertor._convert_headers([]) == {}

    def test_generate_node_id_format(self, convertor):
        """Test that _generate_node_id creates valid IDs"""
        node_id = convertor._generate_node_id("n8n-nodes-base.httpRequest")

        assert node_id.startswith("httpRequest_")
        assert len(node_id) > len("httpRequest_")
