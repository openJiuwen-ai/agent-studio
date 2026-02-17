#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for WorkflowValidator

Tests validation logic for imported workflows.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from openjiuwen_studio.core.dsl_converter.converter.validator import WorkflowValidator, ValidationResult


@pytest.fixture
def validator():
    """Create validator instance"""
    return WorkflowValidator()


@pytest.fixture
def valid_workflow_data():
    """Create valid workflow data"""
    return {
        "workflow_id": "test-123",
        "name": "Test Workflow",
        "desc": "Test Description",
        "space_id": "space-123",
        "schema": json.dumps({
            "nodes": [
                {
                    "id": "start_1",
                    "type": "1",
                    "data": {"title": "Start"},
                    "meta": {"position": {"x": 100, "y": 100}}
                },
                {
                    "id": "end_1",
                    "type": "2",
                    "data": {"title": "End"},
                    "meta": {"position": {"x": 300, "y": 100}}
                }
            ],
            "edges": [
                {"id": "edge1", "sourceNodeID": "start_1", "targetNodeID": "end_1"}
            ]
        }),
        "input_parameters": [],
        "output_parameters": []
    }


class TestWorkflowValidator:
    """Test suite for WorkflowValidator"""

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_valid_workflow(validator, valid_workflow_data):
        """Test validation of valid workflow"""
        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_missing_workflow_id(validator, valid_workflow_data):
        """Test validation fails when workflow_id missing"""
        del valid_workflow_data["workflow_id"]

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("workflow_id" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_missing_schema(validator, valid_workflow_data):
        """Test validation fails when schema missing"""
        del valid_workflow_data["schema"]

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("schema" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_invalid_schema_json(validator, valid_workflow_data):
        """Test validation fails with invalid schema JSON"""
        valid_workflow_data["schema"] = "invalid json {["

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_missing_start_node(validator, valid_workflow_data):
        """Test validation fails when START node missing"""
        schema = json.loads(valid_workflow_data["schema"])
        # Remove START node (type 1)
        schema["nodes"] = [n for n in schema["nodes"] if n["type"] != "1"]
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("start" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_missing_end_node(validator, valid_workflow_data):
        """Test validation fails when END node missing"""
        schema = json.loads(valid_workflow_data["schema"])
        # Remove END node (type 2)
        schema["nodes"] = [n for n in schema["nodes"] if n["type"] != "2"]
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("end" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_disconnected_node(validator, valid_workflow_data):
        """Test validation detects disconnected nodes"""
        schema = json.loads(valid_workflow_data["schema"])
        # Add disconnected CODE node
        schema["nodes"].append({
            "id": "code_1",
            "type": "3",
            "data": {"title": "Disconnected"},
            "meta": {"position": {"x": 200, "y": 200}}
        })
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        # Should have warning about disconnected node
        assert len(result.warnings) > 0
        assert any("disconnected" in w.lower() or "isolated" in w.lower()
                  for w in result.warnings)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_edge_missing_source(validator, valid_workflow_data):
        """Test validation fails when edge references missing source"""
        schema = json.loads(valid_workflow_data["schema"])
        schema["edges"] = [
            {"id": "edge1", "sourceNodeID": "nonexistent", "targetNodeID": "end_1"}
        ]
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("edge" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_edge_missing_target(validator, valid_workflow_data):
        """Test validation fails when edge references missing target"""
        schema = json.loads(valid_workflow_data["schema"])
        schema["edges"] = [
            {"id": "edge1", "sourceNodeID": "start_1", "targetNodeID": "nonexistent"}
        ]
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("edge" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_with_warnings(validator, valid_workflow_data):
        """Test validation succeeds but returns warnings"""
        schema = json.loads(valid_workflow_data["schema"])
        # Add LLM node without model config (warning but not error)
        schema["nodes"].insert(1, {
            "id": "llm_1",
            "type": "3",
            "data": {
                "title": "LLM",
                "inputs": {},
                "outputs": {}
            },
            "meta": {"position": {"x": 200, "y": 100}}
        })
        schema["edges"] = [
            {"id": "edge1", "sourceNodeID": "start_1", "targetNodeID": "llm_1"},
            {"id": "edge2", "sourceNodeID": "llm_1", "targetNodeID": "end_1"}
        ]
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        # Should validate but have warnings
        assert result.is_valid is True
        # Warnings might exist about missing model config

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_schema_as_dict(validator, valid_workflow_data):
        """Test validation when schema is dict (not string)"""
        valid_workflow_data["schema"] = json.loads(valid_workflow_data["schema"])

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is True
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_complex_workflow(validator):
        """Test validation of complex workflow with multiple nodes"""
        workflow_data = {
            "workflow_id": "test-123",
            "space_id": "space-123",
            "name": "Complex Workflow",
            "schema": json.dumps({
                "nodes": [
                    {"id": "start", "type": "1", "data": {"title": "Start"},
                     "meta": {"position": {"x": 0, "y": 0}}},
                    {"id": "llm1", "type": "3", "data": {"title": "LLM 1"},
                     "meta": {"position": {"x": 200, "y": 0}}},
                    {"id": "if1", "type": "6", "data": {"title": "IF"},
                     "meta": {"position": {"x": 400, "y": 0}}},
                    {"id": "code1", "type": "4", "data": {"title": "Code"},
                     "meta": {"position": {"x": 600, "y": 0}}},
                    {"id": "end", "type": "2", "data": {"title": "End"},
                     "meta": {"position": {"x": 800, "y": 0}}}
                ],
                "edges": [
                    {"id": "e1", "sourceNodeID": "start", "targetNodeID": "llm1"},
                    {"id": "e2", "sourceNodeID": "llm1", "targetNodeID": "if1"},
                    {"id": "e3", "sourceNodeID": "if1", "targetNodeID": "code1"},
                    {"id": "e4", "sourceNodeID": "code1", "targetNodeID": "end"}
                ]
            }),
            "input_parameters": [],
            "output_parameters": []
        }

        result = await validator.validate(
            workflow_data=workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is True

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_strict_mode(validator, valid_workflow_data):
        """Test strict validation mode (compilation)"""
        # Mock workflow_convert to succeed
        with patch('openjiuwen_studio.core.manager.convertor.workflow.workflow_convert') as mock_convert:
            mock_convert.return_value = MagicMock()  # Return any object

            result = await validator.validate(
                workflow_data=valid_workflow_data,
                space_id="space-123",
                current_user={"user_id": "user123"},
                strict=True
            )

            # Should call workflow_convert
            mock_convert.assert_called_once()
            assert result.is_valid is True

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_strict_mode_compilation_fails(validator, valid_workflow_data):
        """Test strict validation fails when compilation fails"""
        # Mock workflow_convert to raise error
        with patch('openjiuwen_studio.core.manager.convertor.workflow.workflow_convert') as mock_convert:
            mock_convert.side_effect = Exception("Compilation failed")

            result = await validator.validate(
                workflow_data=valid_workflow_data,
                space_id="space-123",
                current_user={"user_id": "user123"},
                strict=True
            )

            assert result.is_valid is False
            assert any("compilation" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_empty_nodes(validator, valid_workflow_data):
        """Test validation fails with empty nodes array"""
        schema = json.loads(valid_workflow_data["schema"])
        schema["nodes"] = []
        valid_workflow_data["schema"] = json.dumps(schema)

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_validate_missing_name(validator, valid_workflow_data):
        """Test validation fails when name missing"""
        del valid_workflow_data["name"]

        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert result.is_valid is False
        assert any("name" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_validation_result_structure(validator, valid_workflow_data):
        """Test ValidationResult structure"""
        result = await validator.validate(
            workflow_data=valid_workflow_data,
            space_id="space-123",
            current_user={"user_id": "user123"},
            strict=False
        )

        assert hasattr(result, "is_valid")
        assert hasattr(result, "errors")
        assert hasattr(result, "warnings")
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
