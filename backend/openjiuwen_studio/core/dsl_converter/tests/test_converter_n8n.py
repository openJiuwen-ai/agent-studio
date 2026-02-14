#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for N8nWorkflowConverter

Tests conversion of n8n format workflows to OpenJiuwen format using actual fixture file.
"""

import json
from pathlib import Path
import pytest

from openjiuwen_studio.core.dsl_converter.converter.converter_n8n import N8nWorkflowConverter
from openjiuwen_studio.core.common.dsl import ComponentType


class TestN8nWorkflowConverter:
    """Test suite for N8nWorkflowConverter"""

    @pytest.fixture
    def converter(self):
        """Create converter instance"""
        return N8nWorkflowConverter()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path"""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def n8n_workflow(self, fixtures_dir):
        """Load n8n_workflow.json fixture"""
        with open(fixtures_dir / "n8n_workflow.json") as f:
            return json.load(f)

    def test_convert_from_n8n_fixture(self, converter, n8n_workflow):
        """Test conversion from n8n_workflow.json fixture"""
        result = converter.convert(n8n_workflow)

        assert result.workflow_data is not None
        # Metadata should track source format
        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_name"] == n8n_workflow["name"]
        # n8n_workflow has 5 nodes
        assert result.metadata["original_nodes"] == 5

    def test_convert_creates_workflow_with_metadata(self, converter, n8n_workflow):
        """Test that conversion creates workflow with correct metadata"""
        result = converter.convert(n8n_workflow)

        # Name should have "(Imported)" suffix
        assert "Example n8n Workflow" in result.workflow_data["name"]
        assert "(Imported)" in result.workflow_data["name"]
        # Description should mention n8n
        assert "Imported from n8n" in result.workflow_data["desc"]
        assert result.workflow_data["workflow_id"] is not None
        assert result.workflow_data["create_time"] is not None

    def test_convert_creates_openjiuwen_schema(self, converter, n8n_workflow):
        """Test that conversion creates valid OpenJiuwen schema"""
        result = converter.convert(n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        assert "nodes" in schema
        assert "edges" in schema
        assert isinstance(schema["nodes"], list)
        assert isinstance(schema["edges"], list)

    def test_convert_adds_start_and_end_nodes(self, converter, n8n_workflow):
        """Test that START and END nodes are added"""
        result = converter.convert(n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])
        node_types = [str(node["type"]) for node in schema["nodes"]]

        # Should have START (1) and END (2) nodes added
        assert str(ComponentType.COMPONENT_TYPE_START) in node_types
        assert str(ComponentType.COMPONENT_TYPE_END) in node_types

    def test_convert_http_request_node(self, converter, n8n_workflow):
        """Test conversion of n8n httpRequest node to Plugin component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # n8n_workflow has http_request_1 node
        plugin_nodes = [n for n in schema["nodes"]
                       if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_PLUGIN)]

        # Should have at least one plugin node (HTTP Request)
        assert len(plugin_nodes) >= 1
        # Check one has title from fixture
        assert any("HTTP Request" in n["data"]["title"] for n in plugin_nodes)

    def test_convert_code_node(self, converter, n8n_workflow):
        """Test conversion of n8n code node to Code component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # n8n_workflow has code_1 node
        code_nodes = [n for n in schema["nodes"]
                     if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_CODE)]

        # Should have at least one code node
        assert len(code_nodes) >= 1
        # Check one has title from fixture
        assert any("Process Data" in n["data"]["title"] for n in code_nodes)

    def test_convert_if_node(self, converter, n8n_workflow):
        """Test conversion of n8n IF node to Branch component"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # n8n_workflow has if_1 node
        if_nodes = [n for n in schema["nodes"]
                   if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_IF)]

        # Should have at least one IF node
        assert len(if_nodes) >= 1
        # Check one has title from fixture
        assert any("Check Condition" in n["data"]["title"] for n in if_nodes)

    def test_convert_preserves_node_positions(self, converter, n8n_workflow):
        """Test that node positions are preserved from fixture"""
        result = converter.convert(n8n_workflow)
        schema = json.loads(result.workflow_data["schema"])

        # n8n_workflow webhook node is at [250, 300]
        # Find converted nodes (not START/END which have generated positions)
        converted_nodes = [n for n in schema["nodes"]
                          if str(n["type"]) not in [
                              str(ComponentType.COMPONENT_TYPE_START),
                              str(ComponentType.COMPONENT_TYPE_END)
                          ]]

        # Should have preserved positions
        assert len(converted_nodes) >= 5  # Original 5 nodes from fixture
        # At least one should have position from fixture
        positions_preserved = any(
            n.get("meta", {}).get("position", {}).get("x") in [250, 450, 650, 850, 1050]
            for n in converted_nodes
        )
        assert positions_preserved

    def test_convert_connections_to_edges(self, converter, n8n_workflow):
        """Test that n8n connections are converted to edges"""
        result = converter.convert(n8n_workflow)

        schema = json.loads(result.workflow_data["schema"])

        # n8n_workflow has 4 connections between nodes
        # Plus START and END connections
        assert len(schema["edges"]) >= 4

        # Check edge structure
        for edge in schema["edges"]:
            assert "id" in edge
            assert "sourceNodeID" in edge
            assert "targetNodeID" in edge

    def test_convert_extracts_input_output_parameters(self, converter, n8n_workflow):
        """Test that input/output parameters are extracted"""
        result = converter.convert(n8n_workflow)

        assert "input_parameters" in result.workflow_data
        assert "output_parameters" in result.workflow_data
        assert isinstance(result.workflow_data["input_parameters"], list)
        assert isinstance(result.workflow_data["output_parameters"], list)

    def test_convert_includes_conversion_metadata(self, converter, n8n_workflow):
        """Test that result includes conversion metadata"""
        result = converter.convert(n8n_workflow)

        assert "source" in result.metadata
        assert "original_name" in result.metadata
        assert "converted_nodes" in result.metadata
        assert "original_nodes" in result.metadata

        assert result.metadata["source"] == "n8n"
        assert result.metadata["original_name"] == "Example n8n Workflow"
        assert result.metadata["original_nodes"] == 5

    def test_convert_empty_workflow_raises_error(self, converter):
        """Test that workflow with no nodes raises error"""
        n8n_workflow = {
            "name": "Empty",
            "nodes": [],
            "connections": {}
        }

        with pytest.raises(ValueError, match="n8n workflow has no nodes"):
            converter.convert(n8n_workflow)

    def test_add_start_end_nodes_adds_both(self, converter):
        """Test that _add_start_end_nodes adds START and END nodes"""
        nodes = [
            {"id": "node1", "type": "3", "data": {"title": "Test"}}
        ]
        edges = []

        result_nodes, result_edges = converter._add_start_end_nodes(nodes, edges)

        # Should have START node
        start_nodes = [n for n in result_nodes
                      if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_START)]
        assert len(start_nodes) == 1

        # Should have END node
        end_nodes = [n for n in result_nodes
                    if str(n["type"]) == str(ComponentType.COMPONENT_TYPE_END)]
        assert len(end_nodes) == 1

        # Should have edges connecting START -> node1 -> END
        assert len(result_edges) >= 2

    def test_convert_headers_from_dict(self, converter):
        """Test _convert_headers with dict input"""
        headers = {"Authorization": "Bearer token", "Content-Type": "application/json"}
        result = converter._convert_headers(headers)
        assert result == headers

    def test_convert_headers_from_list(self, converter):
        """Test _convert_headers with list input (n8n format)"""
        # n8n_workflow has headers in list format
        headers = [
            {"name": "Authorization", "value": "Bearer token123"}
        ]
        result = converter._convert_headers(headers)
        assert result["Authorization"] == "Bearer token123"

    def test_convert_headers_empty(self, converter):
        """Test _convert_headers with empty input"""
        assert converter._convert_headers(None) == {}
        assert converter._convert_headers({}) == {}
        assert converter._convert_headers([]) == {}

    def test_generate_node_id_format(self, converter):
        """Test that _generate_node_id creates valid IDs"""
        node_id = converter._generate_node_id("n8n-nodes-base.httpRequest")

        assert node_id.startswith("httpRequest_")
        assert len(node_id) > len("httpRequest_")
