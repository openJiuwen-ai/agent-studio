#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Native OpenJiuwen Workflow Convertor

Converts OpenJiuwen exported workflows to importable format.
Minimal transformation needed since it's already in the correct format.
"""

import json
import uuid
from typing import Dict, Any, List

from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.core.dsl_converter.convertor.convertor import WorkflowConvertor, WorkflowImportResult
from openjiuwen_studio.schemas.workflow import WorkflowBase
from openjiuwen_studio.core.database import milliseconds


class NativeWorkflowConvertor(WorkflowConvertor):
    """
    Converts OpenJiuwen native format workflows.

    Expected workflow schema (complete example that passes all 3 validation layers):
    {
        "workflow_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "workflow_version": "draft",
        "latest_publish_time": 1770718317014,
        "latest_publish_version": "v0.0.1",
        "name": "Customer Support Workflow",
        "desc": "Automated customer support with AI",
        "space_id": "18630429",
        "url": "test",
        "icon_uri": "",
        "schema": "{\"nodes\":[{\"id\":\"start_1\",\"type\":\"1\",\"data\":{\"title\":\"START\"}},{\"id\":\"llm_2\",\"type\":\"3\",\"data\":{\"title\":\"LLM\"}},{\"id\":\"end_3\",\"type\":\"2\",\"data\":{\"title\":\"END\"}}],\"edges\":[{\"source\":\"start_1\",\"target\":\"llm_2\"},{\"source\":\"llm_2\",\"target\":\"end_3\"}]}",
        "input_parameters": [{"name": "query", "type": "string"}],
        "output_parameters": [{"name": "response", "type": "string"}],
        "create_time": 1770709211479,
        "update_time": 1770718317014
    }

    Field transformations during conversion:
    - workflow_id: REGENERATED (new UUID) → avoid collisions
    - workflow_version: CLEARED (None) → import creates draft
    - latest_publish_*: CLEARED (None) → no version history
    - name: KEPT → importer adds "(imported)" suffix
    - desc, url, icon_uri: KEPT as-is
    - space_id: REPLACED with target space_id
    - schema: NODE IDS REGENERATED → start_1 becomes start_abc123
    - input/output_parameters: KEPT as-is
    - create_time, update_time: REGENERATED (current timestamp)

    Validation will PASS if:
    ✓ Required fields present: workflow_id, name, space_id, schema, create_time, update_time
    ✓ Field constraints: name (1-255 chars), desc (max 500), url (max 500)
    ✓ Schema has START node (type="1") and END node (type="2")
    ✓ Schema is valid JSON with nodes array and edges array

    Note: Convertor automatically handles:
    - Schema as object → converts to JSON string
    - Edges with sourceNodeID/targetNodeID → normalizes to source/target
    """

    def convert(self, json_data: Dict[str, Any]) -> WorkflowImportResult:
        """
        Convert OpenJiuwen native workflow for import.

        Steps:
        0. Pre-process schema field:
           - Convert schema from object to JSON string if needed (some exports have it as object)
           - Normalize edge format from sourceNodeID/targetNodeID to source/target if needed
        1. Validate structure matches WorkflowBase schema
        2. Generate new workflow_id (GUID) to avoid collisions with existing workflows
        3. Regenerate all node IDs in canvas schema to avoid conflicts
        4. Update timestamps (create_time, update_time) to current time
        5. Clear version fields (workflow_version, latest_publish_version, latest_publish_time)
        6. Check for missing resources (models, plugins, sub-workflows) - non-blocking

        Note: The actual workflow database record will be created by workflow_manager.workflow_create()
        which assigns a fresh workflow_id and auto-incrementing id field.

        Handles both schema formats:
        - String format: "schema": "{\"nodes\":[...],\"edges\":[...]}" (standard)
        - Object format: "schema": {"nodes":[...], "edges":[...]} (some exports)

        Handles both edge formats:
        - Standard: {"source": "node1", "target": "node2"}
        - Alternative: {"sourceNodeID": "node1", "targetNodeID": "node2"}

        Args:
            json_data: OpenJiuwen workflow JSON

        Returns:
            WorkflowImportResult with processed workflow data

        Raises:
            ValueError: If workflow structure is invalid
        """
        warnings = []

        # Store original workflow_id for metadata
        original_workflow_id = json_data.get("workflow_id", "unknown")

        # Pre-process: Normalize schema to string if it's an object
        # Some exports have schema as object, but WorkflowBase expects string
        schema_field = json_data.get("schema")
        if schema_field and not isinstance(schema_field, str):
            try:
                json_data["schema"] = json.dumps(schema_field)
                logger.info("Converted schema from object to JSON string")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Failed to convert schema to JSON string: {e}") from e

        # Pre-process: Normalize edge format if needed
        # Some exports use sourceNodeID/targetNodeID, but we need source/target
        if isinstance(json_data.get("schema"), str):
            try:
                schema_obj = json.loads(json_data["schema"])
                edges = schema_obj.get("edges", [])
                normalized = False
                for edge in edges:
                    if "sourceNodeID" in edge or "targetNodeID" in edge:
                        edge["source"] = edge.pop("sourceNodeID", edge.get("source"))
                        edge["target"] = edge.pop("targetNodeID", edge.get("target"))
                        normalized = True
                if normalized:
                    json_data["schema"] = json.dumps(schema_obj)
                    logger.info("Normalized edge format from sourceNodeID/targetNodeID to source/target")
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning(f"Failed to normalize edge format: {e}")

        # Step 1: Validate schema structure
        try:
            WorkflowBase.model_validate(json_data)
        except ValidationError as e:
            raise ValueError(f"Invalid OpenJiuwen workflow format: {e}") from e

        # Step 2: Generate new workflow_id (avoid collisions)
        new_workflow_id = str(uuid.uuid4())
        json_data["workflow_id"] = new_workflow_id
        logger.info(f"Regenerated workflow_id: {original_workflow_id} → {new_workflow_id}")

        # Step 3: Regenerate node IDs in canvas
        schema_str = json_data.get("schema")
        if schema_str:
            try:
                schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
                schema, id_mapping = self._regenerate_canvas_ids(schema)
                json_data["schema"] = json.dumps(schema)
                logger.info(f"Regenerated {len(id_mapping)} node IDs in canvas")
            except (json.JSONDecodeError, TypeError) as e:
                warnings.append(f"Failed to regenerate canvas IDs: {e}")
                logger.warning(f"Failed to regenerate canvas IDs: {e}")

        # Step 4: Update timestamps
        current_time = milliseconds()
        json_data["create_time"] = current_time
        json_data["update_time"] = current_time

        # Step 5: Clear version fields (import creates draft)
        json_data.pop("workflow_version", None)
        json_data.pop("latest_publish_version", None)
        json_data.pop("latest_publish_time", None)

        # Step 6: Check for missing resources (non-blocking)
        missing_resources = self._check_missing_resources(json_data)
        if missing_resources:
            for resource in missing_resources:
                warnings.append(f"Referenced resource may not exist: {resource}")

        return WorkflowImportResult(
            workflow_data=json_data,
            warnings=warnings,
            metadata={
                "original_workflow_id": original_workflow_id,
                "source_format": "openjiuwen_native",
                "regenerated_nodes": len(id_mapping) if 'id_mapping' in locals() else 0
            }
        )

    def _regenerate_canvas_ids(self, schema: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, str]]:
        """
        Regenerate all node IDs in canvas to avoid conflicts.

        Args:
            schema: Canvas schema dict

        Returns:
            Tuple of (updated_schema, id_mapping)
        """
        id_mapping = {}

        # Generate new IDs for nodes
        for node in schema.get("nodes", []):
            old_id = node.get("id")
            if not old_id:
                continue

            # Generate new ID based on node type
            node_type = node.get("type", "node")
            new_id = f"{node_type}_{uuid.uuid4().hex[:8]}"
            id_mapping[old_id] = new_id
            node["id"] = new_id

        # Update edges to use new IDs
        for edge in schema.get("edges", []):
            source = edge.get("source")
            target = edge.get("target")

            if source in id_mapping:
                edge["source"] = id_mapping[source]

            if target in id_mapping:
                edge["target"] = id_mapping[target]

        # Update references in node data (inputParameters, etc.)
        self._update_node_references(schema.get("nodes", []), id_mapping)

        return schema, id_mapping

    def _update_node_references(self, nodes: List[Dict], id_mapping: Dict[str, str]) -> None:
        """
        Update node ID references in inputParameters and other fields.

        Args:
            nodes: List of canvas nodes
            id_mapping: Mapping of old IDs to new IDs
        """
        for node in nodes:
            data = node.get("data", {})
            inputs = data.get("inputs", {})
            input_params = inputs.get("inputParameters", {})

            # Update ref-type parameters
            for param_name, param_value in input_params.items():
                if not isinstance(param_value, dict):
                    continue

                if param_value.get("type") == "ref":
                    content = param_value.get("content", [])
                    if isinstance(content, list) and len(content) > 0:
                        # First element is source node ID
                        old_ref_id = content[0]
                        if old_ref_id in id_mapping:
                            content[0] = id_mapping[old_ref_id]

            # Handle nested structures (loops, branches, sub-workflows)
            self._update_nested_references(node, id_mapping)

    def _update_nested_references(self, node: Dict, id_mapping: Dict[str, str]) -> None:
        """
        Update node references in nested structures like loops.

        Args:
            node: Canvas node
            id_mapping: Mapping of old IDs to new IDs
        """
        # Handle loop blocks
        blocks = node.get("blocks", [])
        if blocks:
            for block in blocks:
                if isinstance(block, dict):
                    # Recursively update block node IDs
                    old_id = block.get("id")
                    if old_id and old_id in id_mapping:
                        block["id"] = id_mapping[old_id]

                    # Update nested references
                    block_data = block.get("data", {})
                    if block_data:
                        block_inputs = block_data.get("inputs", {})
                        block_input_params = block_inputs.get("inputParameters", {})
                        for param_value in block_input_params.values():
                            if isinstance(param_value, dict) and param_value.get("type") == "ref":
                                content = param_value.get("content", [])
                                if isinstance(content, list) and len(content) > 0:
                                    old_ref_id = content[0]
                                    if old_ref_id in id_mapping:
                                        content[0] = id_mapping[old_ref_id]

        # Handle edges in loops
        edges = node.get("edges", [])
        if edges:
            for edge in edges:
                if isinstance(edge, dict):
                    source = edge.get("source")
                    target = edge.get("target")
                    if source in id_mapping:
                        edge["source"] = id_mapping[source]
                    if target in id_mapping:
                        edge["target"] = id_mapping[target]

    def _check_missing_resources(self, workflow_data: Dict[str, Any]) -> List[str]:
        """
        Check if referenced resources exist (models, plugins, sub-workflows).

        Note: This is a non-blocking check. Missing resources are reported as warnings.

        Args:
            workflow_data: Workflow data dict

        Returns:
            List of missing resource descriptions
        """
        missing = []
        schema_str = workflow_data.get("schema", "")

        try:
            schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str

            for node in schema.get("nodes", []):
                node_type = node.get("type")
                node_id = node.get("id", "unknown")
                data = node.get("data", {})
                inputs = data.get("inputs", {})

                # Check LLM model references (type=3)
                if str(node_type) == "3":
                    llm_param = inputs.get("llmParam", {})
                    model = llm_param.get("model", {})
                    model_id = model.get("id")
                    if model_id:
                        # Note: We don't actually check if model exists here
                        # This would require database access which violates separation of concerns
                        # The validator will handle this
                        pass

                # Check sub-workflow references (type=14)
                elif str(node_type) == "14":
                    configs = data.get("configs", {})
                    sub_workflow = configs.get("subWorkflow", {})
                    sub_wf_id = sub_workflow.get("workflowId") or sub_workflow.get("workflow_id")
                    if sub_wf_id:
                        missing.append(f"Sub-workflow reference in node {node_id}: {sub_wf_id}")

                # Check plugin references (type=19)
                elif str(node_type) == "19":
                    configs = data.get("configs", {})
                    tool = configs.get("tool", {})
                    plugin_id = tool.get("id") or tool.get("plugin_id")
                    if plugin_id:
                        missing.append(f"Plugin reference in node {node_id}: {plugin_id}")

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            logger.warning(f"Failed to check missing resources: {e}")

        return missing
