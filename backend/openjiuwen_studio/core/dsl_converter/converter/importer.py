#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Workflow Importer

Orchestrates the workflow import process:
1. Detect format
2. Convert to OpenJiuwen format
3. Validate
4. Save to database
5. Optionally publish
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from openjiuwen.core.common.logging import logger
from fastapi import status

from openjiuwen_studio.core.dsl_converter.converter.detector import WorkflowDetector, WorkflowFormat
from openjiuwen_studio.core.dsl_converter.converter.converter import ConverterFactory
from openjiuwen_studio.core.dsl_converter.converter.validator import WorkflowValidator
from openjiuwen_studio.schemas.workflow import WorkflowCreate, WorkflowSave, WorkflowPublish
import openjiuwen_studio.core.manager.workflow as workflow_mgr


@dataclass
class ImportOptions:
    """Options for workflow import"""
    validate_strict: bool = False     # Compile + validate
    auto_fix: bool = True            # Try to fix issues (not implemented yet)


@dataclass
class ImportResult:
    """Result of workflow import"""
    success: bool
    workflow_id: Optional[str] = None
    workflow_name: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowImporter:
    """Orchestrates workflow import process"""

    def __init__(self):
        self.detector = WorkflowDetector()
        self.validator = WorkflowValidator()

    async def import_workflow(
        self,
        json_data: Dict[str, Any],
        space_id: str,
        current_user: Dict[str, Any],
        options: Optional[ImportOptions] = None
    ) -> ImportResult:
        """
        Import workflow from JSON data.

        Complete workflow import process:
        1. Detect format (OpenJiuwen native, n8n, etc.)
        2. Convert to OpenJiuwen format:
           - Generate new workflow_id (GUID) to avoid collisions
           - Regenerate all canvas node IDs
           - Update timestamps to current time
           - Clear version fields (creates as draft)
        3. Validate workflow structure and optionally compile/execute test
        4. Create workflow in database via manager:
           - Assigns fresh workflow_id and auto-incrementing id
           - Appends " (imported)" to workflow name to distinguish from original
           - Sets proper permissions and space_id
        5. Save canvas schema with regenerated node IDs
        6. (Publishing removed - always imports as draft only)

        Important: The imported workflow will have:
        - A NEW workflow_id (different from the exported workflow)
        - A NEW auto-incrementing id field
        - Name with " (imported)" suffix (e.g., "My Workflow (imported)")
        - Current timestamps
        - No version history (starts as draft)

        Args:
            json_data: Workflow JSON data
            space_id: Target space ID
            current_user: Current user info
            options: Import options (validate_strict)

        Returns:
            ImportResult with import status, new workflow_id, name, warnings, and metadata
        """
        if options is None:
            options = ImportOptions()

        all_warnings = []
        all_errors = []

        # Step 1: Detect format
        try:
            format_type = self.detector.detect_format(json_data)
            logger.info(f"Detected workflow format: {format_type}")

            if format_type == WorkflowFormat.UNSUPPORTED:
                return ImportResult(
                    success=False,
                    errors=["Unsupported workflow format. Supported formats: OpenJiuwen native, n8n"]
                )

        except Exception as e:
            logger.error(f"Format detection failed: {e}")
            return ImportResult(
                success=False,
                errors=[f"Format detection failed: {e}"]
            )

        # Step 2: Convert to OpenJiuwen format
        try:
            converter = ConverterFactory.create(format_type)
            conversion_result = converter.convert(json_data)

            workflow_data = conversion_result.workflow_data
            all_warnings.extend(conversion_result.warnings)

            # Set space_id
            workflow_data["space_id"] = space_id

            logger.info(f"Conversion completed: {conversion_result.metadata}")

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return ImportResult(
                success=False,
                errors=[f"Conversion failed: {e}"],
                warnings=all_warnings
            )

        # Step 3: Validate
        try:
            validation_result = await self.validator.validate(
                workflow_data,
                space_id,
                current_user,
                strict=options.validate_strict
            )

            all_warnings.extend(validation_result.warnings)

            if not validation_result.is_valid:
                logger.error(f"Validation failed: {validation_result.errors}")
                return ImportResult(
                    success=False,
                    errors=validation_result.errors,
                    warnings=all_warnings,
                    workflow_id=workflow_data.get("workflow_id"),
                    workflow_name=workflow_data.get("name")
                )

            logger.info("Validation passed")

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return ImportResult(
                success=False,
                errors=[f"Validation error: {e}"],
                warnings=all_warnings
            )

        # Step 4: Create workflow via manager (gets permissions, tags, etc.)
        # Add " (imported)" suffix to distinguish from original
        try:
            original_name = workflow_data["name"]
            imported_name = f"{original_name} (imported)"

            create_req = WorkflowCreate(
                name=imported_name,
                desc=workflow_data.get("desc", ""),
                space_id=space_id,
                icon_uri=workflow_data.get("icon_uri")
            )

            create_result = workflow_mgr.workflow_create(create_req, current_user)

            if create_result.code != status.HTTP_200_OK:
                logger.error(f"Workflow creation failed: {create_result.message}")
                return ImportResult(
                    success=False,
                    errors=[f"Workflow creation failed: {create_result.message}"],
                    warnings=all_warnings
                )

            workflow_id = create_result.data['workflow']["workflow_id"]
            logger.info(f"Workflow created via manager: {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return ImportResult(
                success=False,
                errors=[f"Failed to create workflow: {e}"],
                warnings=all_warnings
            )

        # Step 5: Save the imported canvas schema (replacing default)
        try:
            save_req = WorkflowSave(
                workflow_id=workflow_id,
                space_id=space_id,
                schema=workflow_data["schema"]  # Converted Canvas JSON string
            )

            save_result = workflow_mgr.workflow_canvas_save(save_req, current_user)

            if save_result.code != status.HTTP_200_OK:
                logger.error(f"Canvas save failed: {save_result.message}")
                return ImportResult(
                    success=False,
                    errors=[f"Canvas save failed: {save_result.message}"],
                    warnings=all_warnings,
                    workflow_id=workflow_id
                )

            logger.info(f"Canvas saved for workflow: {workflow_id}")

        except Exception as e:
            logger.error(f"Failed to save canvas: {e}")
            return ImportResult(
                success=False,
                errors=[f"Failed to save canvas: {e}"],
                warnings=all_warnings,
                workflow_id=workflow_id
            )

        # Success!
        return ImportResult(
            success=True,
            workflow_id=workflow_id,
            workflow_name=imported_name,
            warnings=all_warnings,
            metadata={
                **conversion_result.metadata,
                "original_name": original_name,
                "saved_to_db": True,
                "published": False
            }
        )
