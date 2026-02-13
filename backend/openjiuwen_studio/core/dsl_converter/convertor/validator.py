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
        3. Referential integrity (Edge source/target existence)
        4. Strict validation (compile workflow) - optional
        """
        errors = []
        warnings = []

        # Layer 1: Data Normalization & WorkflowBase validation
        # Fix for test_validate_schema_as_dict: ensure schema is string for WorkflowBase
        if isinstance(workflow_data.get("schema"), dict):
            workflow_data["schema"] = json.dumps(workflow_data["schema"])

        # Ensure space_id is present in the dict if not already (Fix for complex_workflow test)
        if "space_id" not in workflow_data:
            workflow_data["space_id"] = space_id

        try:
            WorkflowBase.model_validate(workflow_data)
            logger.debug("WorkflowBase schema validation passed")
        except ValidationError as e:
            for error in e.errors():
                error_msg = f"Schema validation failed: {error['msg']} at {error['loc']}"
                errors.append(error_msg)
            logger.error(f"WorkflowBase validation failed: {e}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # Layer 2: Validate Canvas structure & Referential Integrity
        schema_str = workflow_data.get("schema")
        if schema_str:
            try:
                schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
                WorkflowCanvas.model_validate(schema)
                logger.debug("Canvas schema validation passed")
            except (json.JSONDecodeError, TypeError) as e:
                errors.append(f"Canvas JSON parsing failed: {e}")
                return ValidationResult(is_valid=False, errors=errors)
            except ValidationError as e:
                for error in e.errors():
                    errors.append(f"Canvas validation failed: {error['msg']} at {error['loc']}")
                return ValidationResult(is_valid=False, errors=errors)

            nodes = schema.get("nodes", [])
            edges = schema.get("edges", [])

            # --- Referential Integrity Check ---
            # Fixes test_validate_edge_missing_source/target
            node_ids = {str(node.get("id")) for node in nodes}
            for edge in edges:
                edge_id = edge.get("id", "unknown")
                source = str(edge.get("sourceNodeID"))
                target = str(edge.get("targetNodeID"))

                if source not in node_ids:
                    errors.append(f"Edge {edge_id} references missing source node: {source}")
                if target not in node_ids:
                    errors.append(f"Edge {edge_id} references missing target node: {target}")

            # --- Node Count & Type Validation ---
            if len(nodes) == 0:
                errors.append("Workflow must have at least one node")  # Upgrade to error for empty nodes test

            has_start = any(str(node.get("type")) == "1" for node in nodes)
            has_end = any(str(node.get("type")) == "2" for node in nodes)

            if not has_start:
                errors.append("Workflow has no START node")
            if not has_end:
                errors.append("Workflow has no END node")

            # --- Disconnected Node Check ---
            connected_ids = set()
            for edge in edges:
                connected_ids.add(str(edge.get("sourceNodeID")))
                connected_ids.add(str(edge.get("targetNodeID")))

            disconnected = []
            for node in nodes:
                node_id = str(node.get("id"))
                node_type = str(node.get("type"))
                # Logic: Non-START/END nodes must be connected
                if node_id not in connected_ids and node_type not in ["1", "2"]:
                    node_title = node.get("data", {}).get("title", node_id)
                    disconnected.append(node_title)

            if disconnected:
                warnings.append(f"Disconnected nodes found: {', '.join(disconnected)}")

        # Layer 3: Strict validation (Compilation)
        if strict and not errors:
            try:
                import openjiuwen_studio.core.manager.convertor.workflow as convert
                workflow_obj = WorkflowBase(**workflow_data)
                # Conversion triggers full business logic and component validation
                convert.workflow_convert(workflow_obj, skip_validation=False)
                logger.info("DSL validation passed")
            except Exception as e:
                errors.append(f"Workflow compilation failed: {str(e)}")
                logger.error(f"DSL validation failed: {e}")

        return ValidationResult(is_valid=(len(errors) == 0), errors=errors, warnings=warnings)

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
