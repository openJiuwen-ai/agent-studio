#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for WorkflowImporter

Tests the main import orchestration logic.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from fastapi import status
import pytest

from openjiuwen_studio.core.dsl_converter.converter import (
    WorkflowImporter,
    ImportOptions,
    ImportResult,
    WorkflowFormat
)


class MockResponse:
    """Mock response object matching workflow manager response structure"""
    def __init__(self, code, data=None, message=""):
        self.code = code
        self.data = data or {}
        self.message = message


@pytest.fixture
def importer():
    """Create importer instance"""
    return WorkflowImporter()


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def openjiuwen_workflow_data(fixtures_dir):
    """Load OpenJiuwen fixture data"""
    fixture_file = fixtures_dir / "openjiuwen_export.json"
    with open(fixture_file) as f:
        return json.load(f)


@pytest.fixture
def n8n_workflow_data(fixtures_dir):
    """Load n8n fixture data"""
    fixture_file = fixtures_dir / "n8n_workflow.json"
    with open(fixture_file) as f:
        return json.load(f)


@pytest.fixture
def import_context():
    """Create import context"""
    return {
        "space_id": "test-space-123",
        "current_user": {"user_id": "test-user-123"}
    }


class TestWorkflowImporter:
    """Test suite for WorkflowImporter"""

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_openjiuwen_format_draft_mode(importer, openjiuwen_workflow_data, import_context):
        """Test importing OpenJiuwen format in draft mode"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            # Mock workflow_create response
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-123"}},
                message="Success"
            ))

            # Mock workflow_canvas_save response
            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            assert result.workflow_id is not None
            assert result.workflow_id == "new-123"
            assert result.workflow_name.endswith(" (imported)")
            assert result.metadata["source_format"] == "openjiuwen_native"
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_n8n_format_draft_mode(importer, n8n_workflow_data, import_context):
        """Test importing n8n format in draft mode"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-456"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=n8n_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            assert result.workflow_id is not None
            assert result.metadata["source_format"] == "n8n"
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_always_draft_mode(importer, openjiuwen_workflow_data, import_context):
        """Test that import always uses draft mode (no publish)"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-789"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False
            # Verify workflow_publish was never called (it doesn't exist in the new code)
            assert not hasattr(mock_mgr, 'workflow_publish') or not mock_mgr.workflow_publish.called

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_with_strict_validation(importer, openjiuwen_workflow_data, import_context):
        """Test import with strict validation (compilation)"""
        options = ImportOptions(validate_strict=True)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-strict-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            # Mock workflow_convert for strict validation
            with patch('openjiuwen_studio.core.manager.convertor.workflow.workflow_convert') as mock_convert:
                mock_convert.return_value = MagicMock()  # Return any object, we just need it not to raise

                result = await importer.import_workflow(
                    json_data=openjiuwen_workflow_data,
                    space_id=import_context["space_id"],
                    current_user=import_context["current_user"],
                    options=options
                )

                assert result.success is True
                # Strict validation (workflow_convert) should have been called
                mock_convert.assert_called_once()

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_unsupported_format(importer, import_context):
        """Test import fails with unsupported format"""
        invalid_data = {"unknown": "format"}
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=invalid_data,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert result.success is False
        assert any("unsupported" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_validation_fails(importer, import_context):
        """Test import fails when validation fails"""
        # Workflow without START node
        invalid_workflow = {
            "workflow_id": "test-123",
            "name": "Invalid",
            "schema": json.dumps({
                "nodes": [
                    {"id": "end", "type": "2", "data": {"title": "End"},
                     "meta": {"position": {"x": 0, "y": 0}}}
                ],
                "edges": []
            }),
            "input_parameters": [],
            "output_parameters": []
        }
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=invalid_workflow,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert result.success is False
        assert any("start" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_conversion_warnings(importer, import_context):
        """Test import succeeds but includes conversion warnings"""
        # n8n workflow with unsupported node type
        n8n_with_unsupported = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "type": "n8n-nodes-base.unsupportedType",
                "name": "Unsupported",
                "parameters": {},
                "position": [0, 0]
            }],
            "connections": {}
        }
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-warn-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=n8n_with_unsupported,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            # Should succeed but have warnings about unsupported node
            assert result.success is True
            assert len(result.warnings) > 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_workflow_create_error(importer, openjiuwen_workflow_data, import_context):
        """Test import handles workflow creation errors"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={},
                message="Database connection failed"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is False
            assert any("creation failed" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_canvas_save_error(importer, openjiuwen_workflow_data, import_context):
        """Test import handles canvas save errors"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                data={},
                message="Canvas save failed"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is False
            assert any("canvas save failed" in err.lower() for err in result.errors)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_result_metadata(importer, openjiuwen_workflow_data, import_context):
        """Test import result contains expected metadata"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-meta-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert "source_format" in result.metadata
            assert "original_name" in result.metadata
            assert "saved_to_db" in result.metadata
            assert "published" in result.metadata
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_preserves_workflow_name_with_suffix(importer, openjiuwen_workflow_data, import_context):
        """Test that workflow name gets (imported) suffix"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "new-name-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            original_name = openjiuwen_workflow_data["name"]
            assert result.workflow_name == f"{original_name} (imported)"
            assert result.metadata["original_name"] == original_name

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_generates_new_workflow_id(importer, openjiuwen_workflow_data, import_context):
        """Test that new workflow_id is generated"""
        original_id = openjiuwen_workflow_data["workflow_id"]
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "completely-new-id"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.workflow_id == "completely-new-id"
            assert result.workflow_id != original_id

    @pytest.mark.asyncio
    async def test_import_options_defaults(self):
        """Test ImportOptions default values"""
        options = ImportOptions()

        assert options.validate_strict is False
        assert options.auto_fix is True

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_result_success_structure(importer, openjiuwen_workflow_data, import_context):
        """Test ImportResult structure for successful import"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "struct-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert hasattr(result, "success")
            assert hasattr(result, "workflow_id")
            assert hasattr(result, "workflow_name")
            assert hasattr(result, "warnings")
            assert hasattr(result, "errors")
            assert hasattr(result, "metadata")
            assert isinstance(result.warnings, list)
            assert isinstance(result.errors, list)
            assert isinstance(result.metadata, dict)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_result_failure_structure(importer, import_context):
        """Test ImportResult structure for failed import"""
        invalid_data = {"invalid": "data"}
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=invalid_data,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert isinstance(result.errors, list)

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_multiple_workflows_sequentially(importer, openjiuwen_workflow_data,
                                                          n8n_workflow_data, import_context):
        """Test importing multiple workflows sequentially"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            # Setup mocks for both imports
            mock_mgr.workflow_create = MagicMock(side_effect=[
                MockResponse(code=status.HTTP_200_OK, data={'workflow': {"workflow_id": "seq-1"}}, message="Success"),
                MockResponse(code=status.HTTP_200_OK, data={'workflow': {"workflow_id": "seq-2"}}, message="Success")
            ])

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            # Import OpenJiuwen workflow
            result1 = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            # Import n8n workflow
            result2 = await importer.import_workflow(
                json_data=n8n_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result1.success is True
            assert result2.success is True
            assert result1.workflow_id != result2.workflow_id
