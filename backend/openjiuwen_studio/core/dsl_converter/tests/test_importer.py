#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Tests for WorkflowImporter

Tests the main import orchestration logic.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from openjiuwen_studio.core.dsl_converter.convertor import (
    WorkflowImporter,
    ImportOptions,
    ImportResult,
    WorkflowFormat
)


class TestWorkflowImporter:
    """Test suite for WorkflowImporter"""

    @pytest.fixture
    def importer(self):
        """Create importer instance"""
        return WorkflowImporter()

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path"""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def openjiuwen_workflow_data(self, fixtures_dir):
        """Load OpenJiuwen fixture data"""
        fixture_file = fixtures_dir / "openjiuwen_export.json"
        with open(fixture_file) as f:
            return json.load(f)

    @pytest.fixture
    def n8n_workflow_data(self, fixtures_dir):
        """Load n8n fixture data"""
        fixture_file = fixtures_dir / "n8n_workflow.json"
        with open(fixture_file) as f:
            return json.load(f)

    @pytest.fixture
    def import_context(self):
        """Create import context"""
        return {
            "space_id": "test-space-123",
            "current_user": {"user_id": "test-user-123"}
        }

    @pytest.mark.asyncio
    async def test_import_openjiuwen_format_draft_mode(self, importer, openjiuwen_workflow_data, import_context):
        """Test importing OpenJiuwen format in draft mode"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
            mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            assert result.workflow_id is not None
            assert result.workflow_name == openjiuwen_workflow_data["name"]
            assert result.metadata["source_format"] == "openjiuwen_native"
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    async def test_import_n8n_format_draft_mode(self, importer, n8n_workflow_data, import_context):
        """Test importing n8n format in draft mode"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
            mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})

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

    # Test removed - dry_run is no longer supported

    @pytest.mark.asyncio
    async def test_import_always_draft_mode(self, importer, openjiuwen_workflow_data, import_context):
        """Test that import always uses draft mode (no publish)"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:

            mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    async def test_import_with_strict_validation(self, importer, openjiuwen_workflow_data, import_context):
        """Test import with strict validation (compilation)"""
        options = ImportOptions(validate_strict=True)

        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo, \
             patch('openjiuwen_studio.core.manager.workflow.flow_mgr') as mock_flow_mgr:

            mock_repo.workflow_create = MagicMock(return_value={"workflow_id": "new-123"})
            mock_flow_mgr.validate = AsyncMock(return_value=None)

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is True
            # Should have called strict validation
            mock_flow_mgr.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_import_unsupported_format(self, importer, import_context):
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
    async def test_import_validation_fails(self, importer, import_context):
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
    async def test_import_conversion_warnings(self, importer, import_context):
        """Test import succeeds but includes conversion warnings"""
        # n8n workflow with unsupported node type
        n8n_with_unsupported = {
            "name": "Test",
            "nodes": [{
                "id": "1",
                "type": "n8n-nodes-base.unsupportedType",
                "name": "Unsupported",
                "parameters": {}
            }],
            "connections": {}
        }
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=n8n_with_unsupported,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        # Should succeed but have warnings
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_import_database_error(self, importer, openjiuwen_workflow_data, import_context):
        """Test import handles database errors"""
        options = ImportOptions(validate_strict=False)

        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
            mock_repo.workflow_create = MagicMock(
                side_effect=Exception("Database connection failed")
            )

            result = await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=import_context["space_id"],
                current_user=import_context["current_user"],
                options=options
            )

            assert result.success is False
            assert any("database" in err.lower() or "failed" in err.lower()
                      for err in result.errors)

    # Test removed - publishing is no longer supported in import

    @pytest.mark.asyncio
    async def test_import_result_metadata(self, importer, openjiuwen_workflow_data, import_context):
        """Test import result contains expected metadata"""
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=openjiuwen_workflow_data,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert "source_format" in result.metadata
        assert "original_name" in result.metadata or "original_workflow_id" in result.metadata
        assert "saved_to_db" in result.metadata
        assert "published" in result.metadata

    @pytest.mark.asyncio
    async def test_import_preserves_workflow_name(self, importer, openjiuwen_workflow_data, import_context):
        """Test that workflow name is preserved"""
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=openjiuwen_workflow_data,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert result.workflow_name == openjiuwen_workflow_data["name"]

    @pytest.mark.asyncio
    async def test_import_generates_new_workflow_id(self, importer, openjiuwen_workflow_data, import_context):
        """Test that new workflow_id is generated"""
        original_id = openjiuwen_workflow_data["workflow_id"]
        options = ImportOptions(validate_strict=False)

        result = await importer.import_workflow(
            json_data=openjiuwen_workflow_data,
            space_id=import_context["space_id"],
            current_user=import_context["current_user"],
            options=options
        )

        assert result.workflow_id != original_id

    @pytest.mark.asyncio
    async def test_import_handles_missing_space_id(self, importer, openjiuwen_workflow_data):
        """Test import handles missing space_id"""
        options = ImportOptions(validate_strict=False)

        with pytest.raises((ValueError, TypeError)):
            await importer.import_workflow(
                json_data=openjiuwen_workflow_data,
                space_id=None,
                current_user={"user_id": "test-user"},
                options=options
            )

    @pytest.mark.asyncio
    async def test_import_options_defaults(self):
        """Test ImportOptions default values"""
        options = ImportOptions()

        assert options.validate_strict is False

    @pytest.mark.asyncio
    async def test_import_result_success_structure(self, importer, openjiuwen_workflow_data, import_context):
        """Test ImportResult structure for successful import"""
        options = ImportOptions(validate_strict=False)

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
    async def test_import_result_failure_structure(self, importer, import_context):
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
    async def test_import_multiple_workflows_sequentially(self, importer, openjiuwen_workflow_data,
                                                          n8n_workflow_data, import_context):
        """Test importing multiple workflows sequentially"""
        options = ImportOptions(validate_strict=False)

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
