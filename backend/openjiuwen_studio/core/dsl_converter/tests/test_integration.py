#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Integration Tests for Workflow Import

End-to-end tests for the complete import workflow.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import status
import pytest

from openjiuwen_studio.core.dsl_converter.converter import (
    WorkflowImporter,
    WorkflowDetector,
    ConverterFactory,
    WorkflowValidator,
    WorkflowFormat,
    ImportOptions
)


class MockResponse:
    """Mock response object matching workflow manager response structure"""
    def __init__(self, code, data=None, message=""):
        self.code = code
        self.data = data or {}
        self.message = message


@pytest.fixture
def fixtures_dir():
    """Get fixtures directory path"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def openjiuwen_fixture(fixtures_dir):
    """Load OpenJiuwen fixture"""
    with open(fixtures_dir / "openjiuwen_export.json") as f:
        return json.load(f)


@pytest.fixture
def n8n_fixture(fixtures_dir):
    """Load n8n fixture"""
    with open(fixtures_dir / "n8n_workflow.json") as f:
        return json.load(f)


class TestWorkflowImportIntegration:
    """Integration test suite for complete import workflow"""

    @pytest.mark.asyncio
    @staticmethod
    async def test_end_to_end_openjiuwen_import(openjiuwen_fixture):
        """Test complete OpenJiuwen workflow import process"""
        # 1. Detect format
        detector = WorkflowDetector()
        format_type = detector.detect_format(openjiuwen_fixture)
        assert format_type == WorkflowFormat.OPENJIUWEN_NATIVE

        # 2. Convert
        converter = ConverterFactory.create(format_type)
        conversion_result = converter.convert(openjiuwen_fixture)
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

        # 4. Import (with mocked manager)
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "e2e-oj-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            import_result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )
            assert import_result.success is True
            assert import_result.workflow_id == "e2e-oj-123"

    @pytest.mark.asyncio
    @staticmethod
    async def test_end_to_end_n8n_import(n8n_fixture):
        """Test complete n8n workflow import process"""
        # 1. Detect format
        detector = WorkflowDetector()
        format_type = detector.detect_format(n8n_fixture)
        assert format_type == WorkflowFormat.N8N

        # 2. Convert
        converter = ConverterFactory.create(format_type)
        conversion_result = converter.convert(n8n_fixture)
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

        # 4. Import (with mocked manager)
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "e2e-n8n-456"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            import_result = await importer.import_workflow(
                json_data=n8n_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )
            assert import_result.success is True
            assert import_result.workflow_id == "e2e-n8n-456"

    @pytest.mark.asyncio
    @staticmethod
    async def test_pipeline_error_propagation(openjiuwen_fixture):
        """Test that errors propagate through the pipeline"""
        # Inject invalid data to cause conversion error
        invalid_fixture = {**openjiuwen_fixture, "schema": "invalid json"}

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "error-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=invalid_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            # Should fail due to conversion error
            assert result.success is False
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_pipeline_warning_propagation(n8n_fixture):
        """Test that warnings propagate through the pipeline"""
        # n8n workflow with unsupported node creates warnings
        n8n_with_warnings = {
            **n8n_fixture,
            "nodes": n8n_fixture["nodes"] + [{
                "id": "unsupported-node",
                "type": "n8n-nodes-base.unsupportedNodeType",
                "name": "Unsupported",
                "parameters": {},
                "position": [500, 500]
            }]
        }

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "warn-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=n8n_with_warnings,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            # Should succeed with warnings
            assert result.success is True
            assert len(result.warnings) > 0

    @pytest.mark.asyncio
    @staticmethod
    async def test_strict_validation_mode(openjiuwen_fixture):
        """Test import with strict validation enabled"""
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "strict-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            with patch('openjiuwen_studio.core.manager.convertor.workflow.workflow_convert') as mock_convert:
                mock_convert.return_value = MagicMock()  # Return any object

                importer = WorkflowImporter()
                result = await importer.import_workflow(
                    json_data=openjiuwen_fixture,
                    space_id="test-space",
                    current_user={"user_id": "test-user"},
                    options=ImportOptions(validate_strict=True)
                )

                assert result.success is True
                # Verify strict validation (workflow_convert) was called
                mock_convert.assert_called_once()

    @pytest.mark.asyncio
    @staticmethod
    async def test_format_detection_to_conversion_mapping(openjiuwen_fixture, n8n_fixture):
        """Test that format detection correctly maps to converter"""
        detector = WorkflowDetector()

        # Test OpenJiuwen
        oj_format = detector.detect_format(openjiuwen_fixture)
        oj_converter = ConverterFactory.create(oj_format)
        assert oj_converter is not None
        oj_result = oj_converter.convert(openjiuwen_fixture)
        assert oj_result.metadata["source_format"] == "openjiuwen_native"

        # Test n8n
        n8n_format = detector.detect_format(n8n_fixture)
        n8n_converter = ConverterFactory.create(n8n_format)
        assert n8n_converter is not None
        n8n_result = n8n_converter.convert(n8n_fixture)
        assert n8n_result.metadata["source_format"] == "n8n"

    @pytest.mark.asyncio
    @staticmethod
    async def test_conversion_to_validation_integration(openjiuwen_fixture):
        """Test that converted workflows pass validation"""
        # Convert
        converter = ConverterFactory.create(WorkflowFormat.OPENJIUWEN_NATIVE)
        conversion_result = converter.convert(openjiuwen_fixture)

        # Validate
        validator = WorkflowValidator()
        validation_result = await validator.validate(
            workflow_data=conversion_result.workflow_data,
            space_id="test-space",
            current_user={"user_id": "test-user"},
            strict=False
        )

        assert validation_result.is_valid is True

    @pytest.mark.asyncio
    @staticmethod
    async def test_id_regeneration_consistency(openjiuwen_fixture):
        """Test that IDs are properly regenerated during conversion"""
        original_id = openjiuwen_fixture["workflow_id"]

        converter = ConverterFactory.create(WorkflowFormat.OPENJIUWEN_NATIVE)
        result1 = converter.convert(openjiuwen_fixture)
        result2 = converter.convert(openjiuwen_fixture)

        # Each conversion should generate new IDs
        assert result1.workflow_data["workflow_id"] != original_id
        assert result2.workflow_data["workflow_id"] != original_id
        assert result1.workflow_data["workflow_id"] != result2.workflow_data["workflow_id"]

    @pytest.mark.asyncio
    @staticmethod
    async def test_metadata_tracking_through_pipeline(openjiuwen_fixture):
        """Test that metadata is tracked through the entire pipeline"""
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "meta-track-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            # Check metadata from all stages
            assert "source_format" in result.metadata  # From detection
            assert "original_name" in result.metadata  # From conversion
            assert "saved_to_db" in result.metadata  # From import
            assert "published" in result.metadata  # From import
            assert result.metadata["saved_to_db"] is True
            assert result.metadata["published"] is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_import_with_name_suffix(openjiuwen_fixture):
        """Test that imported workflow gets (imported) suffix"""
        original_name = openjiuwen_fixture["name"]

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "suffix-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            assert result.success is True
            assert result.workflow_name == f"{original_name} (imported)"
            assert result.metadata["original_name"] == original_name

    @pytest.mark.asyncio
    @staticmethod
    async def test_concurrent_imports_different_workflows(openjiuwen_fixture, n8n_fixture):
        """Test importing different workflows concurrently"""
        import asyncio

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            # Use side_effect to return different IDs for each call
            workflow_ids = iter(["concurrent-1", "concurrent-2"])
            mock_mgr.workflow_create = MagicMock(side_effect=lambda *args, **kwargs: MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": next(workflow_ids)}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()

            # Import concurrently
            results = await asyncio.gather(
                importer.import_workflow(
                    json_data=openjiuwen_fixture,
                    space_id="test-space-1",
                    current_user={"user_id": "test-user-1"},
                    options=ImportOptions()
                ),
                importer.import_workflow(
                    json_data=n8n_fixture,
                    space_id="test-space-2",
                    current_user={"user_id": "test-user-2"},
                    options=ImportOptions()
                )
            )

            assert all(r.success for r in results)
            assert len(set(r.workflow_id for r in results)) == 2  # Different IDs

    @pytest.mark.asyncio
    @staticmethod
    async def test_validation_failure_stops_pipeline(openjiuwen_fixture):
        """Test that validation failure prevents database save"""
        # Create invalid workflow (no START node)
        invalid = {**openjiuwen_fixture}

        # --- FIX START ---
        # Check if schema is a string before trying to parse it
        raw_schema = invalid.get("schema")
        if isinstance(raw_schema, str):
            schema = json.loads(raw_schema)
        else:
            schema = raw_schema  # It's already a dictionary
        # --- FIX END ---

        # Remove START node (type "1" is the Start node in OpenJiuwen)
        schema["nodes"] = [n for n in schema["nodes"] if str(n.get("type")) != "1"]

        # Re-serialize to string because the Importer expects the schema field to be a string
        invalid["schema"] = json.dumps(schema)

        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "should-not-create"}},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=invalid,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            # Should fail validation
            assert result.success is False
            # workflow_create should NOT have been called because validation failed first
            mock_mgr.workflow_create.assert_not_called()

    @pytest.mark.asyncio
    @staticmethod
    async def test_workflow_manager_integration(openjiuwen_fixture):
        """Test integration with workflow manager"""
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "mgr-int-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            assert result.success is True

            # Verify both manager methods were called
            assert mock_mgr.workflow_create.called
            assert mock_mgr.workflow_canvas_save.called

            # Verify create was called with (imported) suffix
            create_call_args = mock_mgr.workflow_create.call_args
            create_req = create_call_args[0][0]
            assert create_req.name.endswith(" (imported)")

    @pytest.mark.asyncio
    @staticmethod
    async def test_full_pipeline_with_all_components(n8n_fixture):
        """Test complete pipeline: detect → convert → validate → save"""
        # This test exercises all components
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "full-pipeline-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            # 1. Detection
            detector = WorkflowDetector()
            format_type = detector.detect_format(n8n_fixture)
            assert format_type == WorkflowFormat.N8N

            # 2. Conversion
            converter = ConverterFactory.create(format_type)
            conversion_result = converter.convert(n8n_fixture)
            assert conversion_result.workflow_data is not None
            assert "n8n" in conversion_result.metadata["source_format"]

            # 3. Validation
            validator = WorkflowValidator()
            validation_result = await validator.validate(
                workflow_data=conversion_result.workflow_data,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                strict=False
            )
            assert validation_result.is_valid is True

            # 4. Complete import (all steps together)
            importer = WorkflowImporter()
            final_result = await importer.import_workflow(
                json_data=n8n_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            assert final_result.success is True
            assert final_result.workflow_id == "full-pipeline-123"
            assert final_result.metadata["source_format"] == "n8n"
            assert final_result.metadata["saved_to_db"] is True
            assert final_result.metadata["published"] is False

    @pytest.mark.asyncio
    @staticmethod
    async def test_no_publishing_in_import(openjiuwen_fixture):
        """Test that import never attempts to publish (always draft)"""
        with patch('openjiuwen_studio.core.dsl_converter.converter.importer.workflow_mgr') as mock_mgr:
            mock_mgr.workflow_create = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={'workflow': {"workflow_id": "no-publish-123"}},
                message="Success"
            ))

            mock_mgr.workflow_canvas_save = MagicMock(return_value=MockResponse(
                code=status.HTTP_200_OK,
                data={},
                message="Success"
            ))

            # Add workflow_publish to ensure it's never called
            mock_mgr.workflow_publish = MagicMock()

            importer = WorkflowImporter()
            result = await importer.import_workflow(
                json_data=openjiuwen_fixture,
                space_id="test-space",
                current_user={"user_id": "test-user"},
                options=ImportOptions()
            )

            assert result.success is True
            assert result.metadata["published"] is False
            # Ensure publish was never called
            mock_mgr.workflow_publish.assert_not_called()
