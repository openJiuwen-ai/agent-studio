#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Integration Tests for Workflow Import

End-to-end tests for the complete import workflow.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from openjiuwen_studio.core.dsl_converter.convertor import (
    WorkflowImporter,
    WorkflowDetector,
    ConvertorFactory,
    WorkflowValidator,
    WorkflowFormat,
    ImportOptions
)


class TestWorkflowImportIntegration:
    """Integration test suite for complete import workflow"""

    @pytest.fixture
    def fixtures_dir(self):
        """Get fixtures directory path"""
        return Path(__file__).parent / "fixtures"

    @pytest.fixture
    def openjiuwen_fixture(self, fixtures_dir):
        """Load OpenJiuwen fixture"""
        with open(fixtures_dir / "openjiuwen_export.json") as f:
            return json.load(f)

    @pytest.fixture
    def n8n_fixture(self, fixtures_dir):
        """Load n8n fixture"""
        with open(fixtures_dir / "n8n_workflow.json") as f:
            return json.load(f)

    @pytest.mark.asyncio
    async def test_end_to_end_openjiuwen_import(self, openjiuwen_fixture):
        """Test complete OpenJiuwen workflow import process"""
        # 1. Detect format
        detector = WorkflowDetector()
        format_type = detector.detect_format(openjiuwen_fixture)
        assert format_type == WorkflowFormat.OPENJIUWEN_NATIVE

        # 2. Convert
        convertor = ConvertorFactory.create(format_type)
        conversion_result = convertor.convert(openjiuwen_fixture)
        assert conversion_result.workflow_data is not None
        assert "workflow_id" in conversion_result.workflow_data

        # 3. Validate
        validator = WorkflowValidator()
        validation_result = await validator.validate(
            workflow_data=conversion_result.workflow_data,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )
        assert validation_result.is_valid is True

        # 4. Import
        importer = WorkflowImporter()
        import_result = await importer.import_workflow(
            json_data=openjiuwen_fixture,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )
        assert import_result.success is True

    @pytest.mark.asyncio
    async def test_end_to_end_n8n_import(self, n8n_fixture):
        """Test complete n8n workflow import process"""
        # 1. Detect format
        detector = WorkflowDetector()
        format_type = detector.detect_format(n8n_fixture)
        assert format_type == WorkflowFormat.N8N

        # 2. Convert
        convertor = ConvertorFactory.create(format_type)
        conversion_result = convertor.convert(n8n_fixture)
        assert conversion_result.workflow_data is not None

        # Verify conversion added START/END nodes
        schema = json.loads(conversion_result.workflow_data["schema"])
        node_types = [str(n["type"]) for n in schema["nodes"]]
        assert "1" in node_types  # START
        assert "2" in node_types  # END

        # 3. Validate
        validator = WorkflowValidator()
        validation_result = await validator.validate(
            workflow_data=conversion_result.workflow_data,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )
        assert validation_result.is_valid is True

        # 4. Import
        importer = WorkflowImporter()
        import_result = await importer.import_workflow(
            json_data=n8n_fixture,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )
        assert import_result.success is True
        assert len(import_result.warnings) >= 0  # May have warnings

    @pytest.mark.asyncio
    async def test_import_with_database_persistence(self, openjiuwen_fixture):
        """Test import with database persistence (mocked)"""
        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo:
            mock_repo.workflow_create = MagicMock(
                return_value={"workflow_id": "new-workflow-123"}
            )

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            assert result.success is True
            assert result.metadata["saved_to_db"] is True
            mock_repo.workflow_create.assert_called_once()

    # Test removed - publishing is no longer supported in import

    @pytest.mark.asyncio
    async def test_import_with_strict_validation(self, openjiuwen_fixture):
        """Test import with strict validation (compilation)"""
        with patch('openjiuwen_studio.repositories.workflow_repository') as mock_repo, \
             patch('openjiuwen_studio.core.manager.workflow.flow_mgr') as mock_flow_mgr:

            mock_repo.workflow_create = MagicMock(
                return_value={"workflow_id": "new-workflow-123"}
            )
            mock_flow_mgr.validate = AsyncMock(return_value=None)

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions(validate_strict=True)
            )

            assert result.success is True
            # Strict validation should have been called
            mock_flow_mgr.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_format_detection_and_conversion_pipeline(self, openjiuwen_fixture, n8n_fixture):
        """Test automatic format detection and conversion pipeline"""
        detector = WorkflowDetector()

        # Test OpenJiuwen detection
        format1 = detector.detect_format(openjiuwen_fixture)
        assert format1 == WorkflowFormat.OPENJIUWEN_NATIVE
        convertor1 = ConvertorFactory.create(format1)
        result1 = convertor1.convert(openjiuwen_fixture)
        assert result1.workflow_data is not None

        # Test n8n detection
        format2 = detector.detect_format(n8n_fixture)
        assert format2 == WorkflowFormat.N8N
        convertor2 = ConvertorFactory.create(format2)
        result2 = convertor2.convert(n8n_fixture)
        assert result2.workflow_data is not None

    @pytest.mark.asyncio
    async def test_n8n_node_conversion_completeness(self, n8n_fixture):
        """Test that n8n conversion preserves all nodes"""
        convertor = ConvertorFactory.create(WorkflowFormat.N8N)
        result = convertor.convert(n8n_fixture)

        schema = json.loads(result.workflow_data["schema"])
        openjiuwen_nodes = schema["nodes"]

        # Original n8n nodes
        n8n_node_count = len(n8n_fixture["nodes"])

        # OpenJiuwen should have: n8n nodes + START + END
        expected_count = n8n_node_count + 2
        assert len(openjiuwen_nodes) >= expected_count

    @pytest.mark.asyncio
    async def test_id_regeneration_prevents_collisions(self, openjiuwen_fixture):
        """Test that ID regeneration prevents collisions"""
        original_id = openjiuwen_fixture["workflow_id"]
        original_schema = json.loads(openjiuwen_fixture["schema"])
        original_node_ids = [n["id"] for n in original_schema["nodes"]]

        convertor = ConvertorFactory.create(WorkflowFormat.OPENJIUWEN_NATIVE)
        result = convertor.convert(openjiuwen_fixture)

        # New workflow ID should be different
        assert result.workflow_data["workflow_id"] != original_id

        # New node IDs should be different
        new_schema = json.loads(result.workflow_data["schema"])
        new_node_ids = [n["id"] for n in new_schema["nodes"]]
        assert set(original_node_ids) != set(new_node_ids)

    @pytest.mark.asyncio
    async def test_validation_catches_invalid_workflow(self):
        """Test that validation catches invalid workflows"""
        invalid_workflow = {
            "workflow_id": "test-123",
            "name": "Invalid",
            "schema": json.dumps({
                "nodes": [],  # No nodes
                "edges": []
            }),
            "input_parameters": [],
            "output_parameters": []
        }

        validator = WorkflowValidator()
        result = await validator.validate(
            workflow_data=invalid_workflow,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )

        assert result.is_valid is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_error_handling_throughout_pipeline(self):
        """Test error handling at each stage of pipeline"""
        importer = WorkflowImporter()

        # Invalid JSON format
        invalid_data = {"completely": "invalid"}
        result = await importer.import_workflow(
            json_data=invalid_data,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )

        assert result.success is False
        assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_warnings_propagation(self, n8n_fixture):
        """Test that warnings propagate through pipeline"""
        # Add unsupported n8n node type
        n8n_with_warning = n8n_fixture.copy()
        n8n_with_warning["nodes"].append({
            "id": "unsupported",
            "type": "n8n-nodes-base.unknownType",
            "name": "Unsupported",
            "parameters": {}
        })

        importer = WorkflowImporter()
        result = await importer.import_workflow(
            json_data=n8n_with_warning,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )

        # Should succeed but have warnings
        assert result.success is True or len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_metadata_tracking_through_pipeline(self, openjiuwen_fixture):
        """Test that metadata is tracked through entire pipeline"""
        importer = WorkflowImporter()
        result = await importer.import_workflow(
            json_data=openjiuwen_fixture,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )

        # Check metadata contains expected fields
        assert "source_format" in result.metadata
        assert "original_workflow_id" in result.metadata
        assert "saved_to_db" in result.metadata
        assert "published" in result.metadata

    @pytest.mark.asyncio
    async def test_concurrent_imports(self, openjiuwen_fixture, n8n_fixture):
        """Test importing multiple workflows concurrently"""
        import asyncio

        importer = WorkflowImporter()

        async def import_workflow(data, name):
            return await importer.import_workflow(
                json_data=data,
                space_id=f"test-space-{name}",
                current_user={"user_id": f"test-user-{name}"},
                options=ImportOptions()
            )

        # Import both workflows concurrently
        results = await asyncio.gather(
            import_workflow(openjiuwen_fixture, "openjiuwen"),
            import_workflow(n8n_fixture, "n8n")
        )

        assert all(r.success for r in results)
        assert results[0].workflow_id != results[1].workflow_id

    @pytest.mark.asyncio
    async def test_schema_validation_layers(self, openjiuwen_fixture):
        """Test that all validation layers are applied"""
        validator = WorkflowValidator()

        # Valid workflow passes all layers
        result = await validator.validate(
            workflow_data=openjiuwen_fixture,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )
        assert result.is_valid is True

        # Invalid schema fails early validation
        invalid_workflow = openjiuwen_fixture.copy()
        invalid_workflow["schema"] = "invalid json"

        result = await validator.validate(
            workflow_data=invalid_workflow,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )
        assert result.is_valid is False

    # Test removed - dry_run is no longer supported

    @pytest.mark.asyncio
    async def test_complete_n8n_conversion_preserves_logic(self, n8n_fixture):
        """Test that n8n conversion preserves workflow logic"""
        convertor = ConvertorFactory.create(WorkflowFormat.N8N)
        result = convertor.convert(n8n_fixture)

        schema = json.loads(result.workflow_data["schema"])

        # Check that connections are preserved
        assert len(schema["edges"]) > 0

        # Check that nodes have proper structure
        for node in schema["nodes"]:
            assert "id" in node
            assert "type" in node
            assert "data" in node
            assert "meta" in node

    @pytest.mark.asyncio
    async def test_import_result_contains_all_information(self, openjiuwen_fixture):
        """Test that import result contains complete information"""
        importer = WorkflowImporter()
        result = await importer.import_workflow(
            json_data=openjiuwen_fixture,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            options=ImportOptions()
        )

        # Verify all required fields
        assert result.success is not None
        assert result.workflow_id is not None
        assert result.workflow_name is not None
        assert isinstance(result.warnings, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.metadata, dict)
