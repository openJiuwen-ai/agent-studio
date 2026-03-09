#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for NativeWorkflowConverter

Tests conversion of OpenJiuwen native format workflows using actual fixture files.
"""

import json
from pathlib import Path
import pytest

from openjiuwen_studio.core.dsl_converter.converter.converter_native import NativeWorkflowConverter


@pytest.fixture
def converter():
    """Create converter instance"""
    return NativeWorkflowConverter()


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def openjiuwen_export(fixtures_dir):
    """Load openjiuwen_export.json fixture"""
    with open(fixtures_dir / "openjiuwen_export.json") as f:
        return json.load(f)


@pytest.fixture
def minimal_workflow(fixtures_dir):
    """Load minimal_workflow.json fixture"""
    with open(fixtures_dir / "minimal_workflow.json") as f:
        return json.load(f)


class TestNativeWorkflowConverter:
    """Test suite for NativeWorkflowConverter"""

    @staticmethod
    def test_convert_from_openjiuwen_export(converter, openjiuwen_export):
        """Test conversion from openjiuwen_export.json fixture"""
        result = converter.convert(openjiuwen_export)

        assert result.workflow_data is not None
        # workflow_id should be regenerated
        assert result.workflow_data["workflow_id"] != openjiuwen_export["workflow_id"]
        # Name should be preserved
        assert result.workflow_data["name"] == openjiuwen_export["name"]
        # Metadata should track original
        assert result.metadata["original_workflow_id"] == openjiuwen_export["workflow_id"]
        assert result.metadata["source_format"] == "openjiuwen_native"

    @staticmethod
    def test_convert_from_minimal_workflow(converter, minimal_workflow):
        """Test conversion from minimal_workflow.json fixture (only schema)"""
        result = converter.convert(minimal_workflow)

        assert result.workflow_data is not None
        # Should have all required fields with defaults
        assert result.workflow_data["workflow_id"]  # Generated
        assert result.workflow_data["name"] == "Imported Workflow"  # Default
        assert result.workflow_data["desc"] == "Imported Workflow"  # Default
        assert result.workflow_data["space_id"] == ""  # Cleared
        assert result.workflow_data["input_parameters"] == []
        assert result.workflow_data["output_parameters"] == []

    @staticmethod
    def test_convert_regenerates_workflow_id(converter, openjiuwen_export):
        """Test that workflow_id is regenerated"""
        original_id = openjiuwen_export["workflow_id"]

        result = converter.convert(openjiuwen_export)

        assert result.workflow_data["workflow_id"] != original_id
        assert result.metadata["original_workflow_id"] == original_id

    @staticmethod
    def test_convert_regenerates_node_ids(converter, openjiuwen_export):
        """Test that node IDs in canvas are regenerated"""
        original_schema = openjiuwen_export["schema"]
        original_node_ids = [node["id"] for node in original_schema["nodes"]]

        result = converter.convert(openjiuwen_export)

        new_schema = json.loads(result.workflow_data["schema"])
        new_node_ids = [node["id"] for node in new_schema["nodes"]]

        # IDs should be different
        assert set(original_node_ids) != set(new_node_ids)
        # Should have same count (3 nodes: start_1, llm_1, end_1)
        assert len(original_node_ids) == len(new_node_ids) == 3

    @staticmethod
    def test_convert_updates_timestamps(converter, openjiuwen_export):
        """Test that timestamps are updated"""
        original_create_time = openjiuwen_export["create_time"]

        result = converter.convert(openjiuwen_export)

        assert result.workflow_data["create_time"] != original_create_time
        assert result.workflow_data["update_time"] != openjiuwen_export["update_time"]
        assert result.workflow_data["create_time"] == result.workflow_data["update_time"]

    @staticmethod
    def test_convert_updates_edge_references(converter, openjiuwen_export):
        """Test that edge source/target IDs are updated to new node IDs"""
        result = converter.convert(openjiuwen_export)

        new_schema = json.loads(result.workflow_data["schema"])
        node_ids = {node["id"] for node in new_schema["nodes"]}

        # All edge sources and targets should reference new node IDs
        # openjiuwen_export has 2 edges: start_1->llm_1, llm_1->end_1
        assert len(new_schema["edges"]) == 2
        for edge in new_schema["edges"]:
            assert edge["sourceNodeID"] in node_ids
            assert edge["targetNodeID"] in node_ids

    @staticmethod
    def test_convert_updates_input_parameter_references(converter, minimal_workflow):
        """Test that ref-type inputParameters are updated"""
        result = converter.convert(minimal_workflow)

        new_schema = json.loads(result.workflow_data["schema"])
        node_ids = {node["id"] for node in new_schema["nodes"]}

        # Find LLM node (type "3")
        llm_node = next(n for n in new_schema["nodes"] if n["type"] == "3")
        # minimal_workflow has "input" parameter referencing start_1
        input_params = llm_node["data"]["inputs"]["inputParameters"]
        input_param = input_params["input"]

        assert input_param["type"] == "ref"
        # First element of content should be a valid node ID (updated from start_1)
        assert input_param["content"][0] in node_ids

    @staticmethod
    def test_convert_clears_version_fields(converter, openjiuwen_export):
        """Test that version fields are cleared"""
        # openjiuwen_export has workflow_version field
        assert "workflow_version" in openjiuwen_export

        result = converter.convert(openjiuwen_export)

        assert "workflow_version" not in result.workflow_data
        assert "latest_publish_version" not in result.workflow_data
        assert "latest_publish_time" not in result.workflow_data

    @staticmethod
    def test_convert_preserves_workflow_name(converter, openjiuwen_export):
        """Test that workflow name is preserved"""
        result = converter.convert(openjiuwen_export)
        # openjiuwen_export name is "check_weather"
        assert result.workflow_data["name"] == "check_weather"

    @staticmethod
    def test_convert_preserves_description(converter, openjiuwen_export):
        """Test that description is preserved"""
        result = converter.convert(openjiuwen_export)
        assert result.workflow_data["desc"] == openjiuwen_export["desc"]

    @staticmethod
    def test_convert_preserves_input_output_parameters(converter, openjiuwen_export):
        """Test that input/output parameters are preserved"""
        result = converter.convert(openjiuwen_export)

        # openjiuwen_export has city and date input parameters
        assert len(result.workflow_data["input_parameters"]) == 2
        assert result.workflow_data["input_parameters"] == openjiuwen_export["input_parameters"]
        assert result.workflow_data["output_parameters"] == openjiuwen_export["output_parameters"]

    @staticmethod
    def test_convert_handles_schema_as_dict(converter, openjiuwen_export):
        """Test conversion when schema is already a dict (not string)"""
        # openjiuwen_export.schema is already a dict
        assert isinstance(openjiuwen_export["schema"], dict)

        result = converter.convert(openjiuwen_export)

        # Should work and schema should be converted to string
        assert result.workflow_data is not None
        assert isinstance(result.workflow_data["schema"], str)

    @staticmethod
    def test_convert_includes_metadata(converter, openjiuwen_export):
        """Test that result includes conversion metadata"""
        result = converter.convert(openjiuwen_export)

        assert "original_workflow_id" in result.metadata
        assert "source_format" in result.metadata
        assert "regenerated_nodes" in result.metadata
        assert result.metadata["source_format"] == "openjiuwen_native"
        # Should have regenerated 3 nodes
        assert result.metadata["regenerated_nodes"] == 3

    @staticmethod
    def test_regenerate_canvas_ids_creates_mapping(converter, minimal_workflow):
        """Test that regenerate_canvas_ids creates correct ID mapping"""
        schema = minimal_workflow["schema"]

        new_schema, id_mapping = converter.regenerate_canvas_ids(schema)

        # minimal_workflow has 3 nodes: start_1, llm_1, end_1
        assert "start_1" in id_mapping
        assert "llm_1" in id_mapping
        assert "end_1" in id_mapping
        assert id_mapping["start_1"] != "start_1"
        assert id_mapping["llm_1"] != "llm_1"
        assert id_mapping["end_1"] != "end_1"

    @staticmethod
    def test_convert_partial_workflow_only_schema(converter, minimal_workflow):
        """Test that partial workflow with only schema field is accepted"""
        # minimal_workflow.json has only schema field
        assert "schema" in minimal_workflow
        assert "name" not in minimal_workflow
        assert "workflow_id" not in minimal_workflow

        result = converter.convert(minimal_workflow)

        # Should successfully convert
        assert result.workflow_data is not None

        # Should have all required fields with defaults
        assert result.workflow_data["workflow_id"]  # Should be generated
        assert result.workflow_data["name"] == "Imported Workflow"  # Default name
        assert result.workflow_data["desc"] == "Imported Workflow"  # Default description
        assert result.workflow_data["space_id"] == ""  # Default space_id (will be set by importer)
        assert result.workflow_data["url"] == ""  # Default url
        assert result.workflow_data["icon_uri"] == ""  # Default icon
        assert result.workflow_data["input_parameters"] == []  # Default empty list
        assert result.workflow_data["output_parameters"] == []  # Default empty list
        assert result.workflow_data["create_time"] > 0  # Should be set to current time
        assert result.workflow_data["update_time"] > 0  # Should be set to current time

        # Schema should still be present and valid
        schema = json.loads(result.workflow_data["schema"])
        assert len(schema["nodes"]) == 3  # start, llm, end
        assert len(schema["edges"]) == 2  # start->llm, llm->end

    @staticmethod
    def test_convert_partial_workflow_missing_schema_fails(converter):
        """Test that workflow without schema field fails"""
        workflow_without_schema = {
            "name": "Test Workflow",
            "desc": "This has no schema"
        }

        with pytest.raises(ValueError, match="Missing required field: 'schema'"):
            converter.convert(workflow_without_schema)

    @staticmethod
    def test_convert_ignores_source_space_id(converter, openjiuwen_export):
        """Test that space_id from source JSON is always ignored"""
        # openjiuwen_export has space_id "18630429"
        assert openjiuwen_export["space_id"] == "18630429"

        result = converter.convert(openjiuwen_export)

        # space_id should be cleared (empty string) - importer will set the target space_id
        assert result.workflow_data["space_id"] == ""
        # Metadata should track original workflow info
        assert "original_workflow_id" in result.metadata
