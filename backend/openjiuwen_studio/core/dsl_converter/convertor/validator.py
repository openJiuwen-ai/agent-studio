#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Workflow Validator

Validates converted workflows before import.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, Any, List

from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.schemas.workflow import WorkflowBase
from openjiuwen_studio.core.manager.internal.workflow import WorkflowCanvas


@dataclass
class ValidationResult:
    """Result of workflow validation"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class WorkflowValidator:
    """Validates workflows before import"""

    async def validate(
        self,
        workflow_data: Dict[str, Any],
        space_id: str,
        current_user: Dict[str, Any],
        strict: bool = False
    ) -> ValidationResult:
        """
        Validate workflow data.

        Validation layers:
        1. Schema validation (WorkflowBase)
        2. Canvas validation (WorkflowCanvas)
        3. Strict validation (compile workflow) - optional

        Args:
            workflow_data: Workflow data dict
            space_id: Target space ID
            current_user: Current user info
            strict: If True, also compile workflow to validate

        Returns:
            ValidationResult with validation status and messages
        """
        errors = []
        warnings = []

        # Layer 1: Validate WorkflowBase schema
        try:
            WorkflowBase.model_validate(workflow_data)
            logger.debug("WorkflowBase schema validation passed")
        except ValidationError as e:
            for error in e.errors():
                error_msg = f"Schema validation failed: {error['msg']} at {error['loc']}"
                errors.append(error_msg)
            logger.error(f"WorkflowBase validation failed: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Layer 2: Validate Canvas structure
        schema_str = workflow_data.get("schema")
        if schema_str:
            try:
                schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
                WorkflowCanvas.model_validate(schema)
                logger.debug("Canvas schema validation passed")
            except (json.JSONDecodeError, TypeError) as e:
                errors.append(f"Canvas JSON parsing failed: {e}")
                logger.error(f"Canvas parsing failed: {e}")
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)
            except ValidationError as e:
                for error in e.errors():
                    error_msg = f"Canvas validation failed: {error['msg']} at {error['loc']}"
                    errors.append(error_msg)
                logger.error(f"Canvas validation failed: {e}")
                return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

            # Check for common issues
            nodes = schema.get("nodes", [])
            edges = schema.get("edges", [])

            if len(nodes) == 0:
                warnings.append("Workflow has no nodes")

            # Check for START/END nodes
            has_start = any(str(node.get("type")) == "1" for node in nodes)
            has_end = any(str(node.get("type")) == "2" for node in nodes)

            if not has_start:
                errors.append("Workflow has no START node")
            if not has_end:
                errors.append("Workflow has no END node")

            # Check for disconnected nodes
            connected_ids = set()
            for edge in edges:
                connected_ids.add(edge.get("source"))
                connected_ids.add(edge.get("target"))

            disconnected = []
            for node in nodes:
                node_id = node.get("id")
                node_type = str(node.get("type"))
                # START and END can be disconnected in certain cases
                if node_id not in connected_ids and node_type not in ["1", "2"]:
                    node_title = node.get("data", {}).get("title", node_id)
                    disconnected.append(node_title)

            if disconnected:
                warnings.append(f"Disconnected nodes found: {', '.join(disconnected)}")

        # Layer 3: Strict validation (DSL conversion and compilation)
        if strict and len(errors) == 0:
            try:
                # Convert Canvas → DSL to validate compilation
                import openjiuwen_studio.core.manager.convertor.workflow as convert

                # Create WorkflowBase object for conversion
                workflow_obj = WorkflowBase(**workflow_data)

                # This will validate:
                # - Canvas → DSL conversion
                # - Component validation
                # - Connection validation
                # - Business logic rules
                dsl_workflow = convert.workflow_convert(workflow_obj, skip_validation=False)

                logger.info("DSL validation passed - workflow can be compiled and executed")

            except Exception as e:
                errors.append(f"Workflow compilation failed: {str(e)}")
                logger.error(f"DSL validation failed: {e}")

        is_valid = len(errors) == 0
        return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)

    def validate_sync(
        self,
        workflow_data: Dict[str, Any],
        space_id: str,
        current_user: Dict[str, Any],
        strict: bool = False
    ) -> ValidationResult:
        """
        Synchronous version of validate (for non-async contexts).

        Args:
            workflow_data: Workflow data dict
            space_id: Target space ID
            current_user: Current user info
            strict: If True, also compile workflow to validate

        Returns:
            ValidationResult with validation status and messages
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.validate(workflow_data, space_id, current_user, strict)
        )
