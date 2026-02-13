#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for NativeWorkflowConvertor

Tests conversion of OpenJiuwen native format workflows.
"""

import pytest
import json
from pathlib import Path

from openjiuwen_studio.core.dsl_converter.convertor.convertor_native import NativeWorkflowConvertor


class TestNativeWorkflowConvertor:
    """Test suite for NativeWorkflowConvertor"""

    @pytest.fixture
    def convertor(self):
        """Create convertor instance"""
        return NativeWorkflowConvertor()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path"""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def sample_workflow(self):
        """Create sample workflow data"""
        return {
            "workflow_id": "original-123",
            "name": "Test Workflow",
            "desc": "Test Description",
            "space_id": "space-123",
            "schema": json.dumps({
                "nodes": [
                    {
                        "id": "start_abc",
                        "type": "1",
                        "data": {"title": "Start"}
                    },
                    {
                        "id": "llm_def",
                        "type": "3",
                        "data": {
                            "title": "LLM",
                            "inputs": {
                                "inputParameters": {
                                    "query": {
                                        "type": "ref",
                                        "content": ["start_abc", "query"]
                                    }
                                }
                            }
                        }
                    },
                    {
                        "id": "end_ghi",
                        "type": "2",
                        "data": {"title": "End"}
                    }
                ],
                "edges": [
                    {"id": "edge1", "sourceNodeID": "start_abc", "targetNodeID": "llm_def"},
                    {"id": "edge2", "sourceNodeID": "llm_def", "targetNodeID": "end_ghi"}
                ]
            }),
            "input_parameters": [{"name": "query", "type": "string"}],
            "output_parameters": [{"name": "result", "type": "string"}],
            "create_time": 1234567890,
            "update_time": 1234567890
        }

    def test_convert_from_fixture(self, convertor, fixtures_dir):
        """Test conversion from fixture file"""
        fixture_file = fixtures_dir / "openjiuwen_export.json"
        with open(fixture_file) as f:
            data = json.load(f)

        result = convertor.convert(data)

        assert result.workflow_data is not None
        assert result.workflow_data["workflow_id"] != data["workflow_id"]
        assert result.workflow_data["name"] == data["name"]
        assert result.metadata["original_workflow_id"] == data["workflow_id"]
        assert result.metadata["source_format"] == "openjiuwen_native"

    def test_convert_regenerates_workflow_id(self, convertor, sample_workflow):
        """Test that workflow_id is regenerated"""
        original_id = sample_workflow["workflow_id"]

        result = convertor.convert(sample_workflow)

        assert result.workflow_data["workflow_id"] != original_id
        assert result.metadata["original_workflow_id"] == original_id

    def test_convert_regenerates_node_ids(self, convertor, sample_workflow):
        """Test that node IDs in canvas are regenerated"""
        schema = json.loads(sample_workflow["schema"])
        original_node_ids = [node["id"] for node in schema["nodes"]]

        result = convertor.convert(sample_workflow)

        new_schema = json.loads(result.workflow_data["schema"])
        new_node_ids = [node["id"] for node in new_schema["nodes"]]

        # IDs should be different
        assert set(original_node_ids) != set(new_node_ids)
        # Should have same count
        assert len(original_node_ids) == len(new_node_ids)

    def test_convert_updates_timestamps(self, convertor, sample_workflow):
        """Test that timestamps are updated"""
        original_create_time = sample_workflow["create_time"]

        result = convertor.convert(sample_workflow)

        assert result.workflow_data["create_time"] != original_create_time
        assert result.workflow_data["update_time"] != sample_workflow["update_time"]
        assert result.workflow_data["create_time"] == result.workflow_data["update_time"]

    def test_convert_updates_edge_references(self, convertor, sample_workflow):
        """Test that edge source/target IDs are updated"""
        result = convertor.convert(sample_workflow)

        new_schema = json.loads(result.workflow_data["schema"])
        node_ids = {node["id"] for node in new_schema["nodes"]}

        # All edge sources and targets should reference new node IDs
        for edge in new_schema["edges"]:
            assert edge["sourceNodeID"] in node_ids
            assert edge["targetNodeID"] in node_ids

    def test_convert_updates_input_parameter_references(self, convertor, sample_workflow):
        """Test that ref-type inputParameters are updated"""
        result = convertor.convert(sample_workflow)

        new_schema = json.loads(result.workflow_data["schema"])
        node_ids = {node["id"] for node in new_schema["nodes"]}

        # Find LLM node and check its input reference
        llm_node = next(n for n in new_schema["nodes"] if n["type"] == "3")
        input_params = llm_node["data"]["inputs"]["inputParameters"]
        query_param = input_params["query"]

        assert query_param["type"] == "ref"
        # First element of content should be a valid node ID
        assert query_param["content"][0] in node_ids

    def test_convert_clears_version_fields(self, convertor):
        """Test that version fields are cleared"""
        workflow = {
            "workflow_id": "test-123",
            "name": "Test",
            "schema": json.dumps({"nodes": [], "edges": []}),
            "input_parameters": [],
            "output_parameters": [],
            "workflow_version": "1.0.0",
            "latest_publish_version": "1.0.0",
            "latest_publish_time": 1234567890
        }

        result = convertor.convert(workflow)

        assert "workflow_version" not in result.workflow_data
        assert "latest_publish_version" not in result.workflow_data
        assert "latest_publish_time" not in result.workflow_data

    def test_convert_preserves_workflow_name(self, convertor, sample_workflow):
        """Test that workflow name is preserved"""
        result = convertor.convert(sample_workflow)
        assert result.workflow_data["name"] == sample_workflow["name"]

    def test_convert_preserves_description(self, convertor, sample_workflow):
        """Test that description is preserved"""
        result = convertor.convert(sample_workflow)
        assert result.workflow_data["desc"] == sample_workflow["desc"]

    def test_convert_preserves_input_output_parameters(self, convertor, sample_workflow):
        """Test that input/output parameters are preserved"""
        result = convertor.convert(sample_workflow)

        assert result.workflow_data["input_parameters"] == sample_workflow["input_parameters"]
        assert result.workflow_data["output_parameters"] == sample_workflow["output_parameters"]

    def test_convert_handles_schema_as_dict(self, convertor):
        """Test conversion when schema is already a dict (not string)"""
        workflow = {
            "workflow_id": "test-123",
            "name": "Test",
            "schema": {  # Dict, not string
                "nodes": [{"id": "n1", "type": "1"}],
                "edges": []
            },
            "input_parameters": [],
            "output_parameters": []
        }

        result = convertor.convert(workflow)

        # Should still work
        assert result.workflow_data is not None
        # Schema should be converted to string
        assert isinstance(result.workflow_data["schema"], str)

    def test_convert_handles_nested_loop_nodes(self, convertor):
        """Test conversion handles loop nodes with blocks"""
        workflow = {
            "workflow_id": "test-123",
            "name": "Test Loop",
            "schema": json.dumps({
                "nodes": [
                    {
                        "id": "loop_1",
                        "type": "5",
                        "data": {"title": "Loop"},
                        "blocks": [
                            {
                                "id": "block_1",
                                "type": "3",
                                "data": {
                                    "title": "LLM in Loop",
                                    "inputs": {
                                        "inputParameters": {
                                            "query": {
                                                "type": "ref",
                                                "content": ["loop_1", "item"]
                                            }
                                        }
                                    }
                                }
                            }
                        ],
                        "edges": []
                    }
                ],
                "edges": []
            }),
            "input_parameters": [],
            "output_parameters": []
        }

        result = convertor.convert(workflow)

        new_schema = json.loads(result.workflow_data["schema"])
        loop_node = new_schema["nodes"][0]

        # Check that block IDs were regenerated
        assert loop_node["blocks"][0]["id"] != "block_1"
        # Check that references were updated
        block_input = loop_node["blocks"][0]["data"]["inputs"]["inputParameters"]["query"]
        assert block_input["content"][0] != "loop_1"  # Should be new loop ID

    def test_convert_invalid_schema_raises_error(self, convertor):
        """Test that invalid workflow structure raises ValueError"""
        workflow = {
            "name": "Invalid",  # Missing workflow_id
            "schema": "{}"
        }

        with pytest.raises(ValueError, match="Invalid OpenJiuwen workflow format"):
            convertor.convert(workflow)

    def test_convert_includes_metadata(self, convertor, sample_workflow):
        """Test that result includes conversion metadata"""
        result = convertor.convert(sample_workflow)

        assert "original_workflow_id" in result.metadata
        assert "source_format" in result.metadata
        assert "regenerated_nodes" in result.metadata
        assert result.metadata["source_format"] == "openjiuwen_native"

    def test_convert_detects_missing_resources(self, convertor):
        """Test that missing resource references are detected"""
        workflow = {
            "workflow_id": "test-123",
            "name": "Test",
            "schema": json.dumps({
                "nodes": [
                    {
                        "id": "sub_wf_1",
                        "type": "14",  # Sub-workflow
                        "data": {
                            "title": "Sub Workflow",
                            "configs": {
                                "subWorkflow": {
                                    "workflowId": "missing-workflow-123"
                                }
                            }
                        }
                    }
                ],
                "edges": []
            }),
            "input_parameters": [],
            "output_parameters": []
        }

        result = convertor.convert(workflow)

        # Should have warning about missing sub-workflow
        assert len(result.warnings) > 0
        assert any("missing-workflow-123" in w for w in result.warnings)

    def test_regenerate_canvas_ids_creates_mapping(self, convertor):
        """Test that _regenerate_canvas_ids creates correct ID mapping"""
        schema = {
            "nodes": [
                {"id": "old_1", "type": "1"},
                {"id": "old_2", "type": "3"}
            ],
            "edges": [
                {"sourceNodeID": "old_1", "targetNodeID": "old_2"}
            ]
        }

        new_schema, id_mapping = convertor._regenerate_canvas_ids(schema)

        assert "old_1" in id_mapping
        assert "old_2" in id_mapping
        assert id_mapping["old_1"] != "old_1"
        assert id_mapping["old_2"] != "old_2"

    def test_update_node_references_updates_refs(self, convertor):
        """Test that _update_node_references correctly updates refs"""
        nodes = [
            {
                "id": "new_1",
                "data": {
                    "inputs": {
                        "inputParameters": {
                            "field": {
                                "type": "ref",
                                "content": ["old_1", "output"]
                            }
                        }
                    }
                }
            }
        ]
        id_mapping = {"old_1": "new_1"}

        convertor._update_node_references(nodes, id_mapping)

        # Reference should be updated
        ref = nodes[0]["data"]["inputs"]["inputParameters"]["field"]
        assert ref["content"][0] == "new_1"
