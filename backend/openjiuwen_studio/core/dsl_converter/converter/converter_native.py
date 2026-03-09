#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Native OpenJiuwen Workflow Converter

Converts OpenJiuwen exported workflows to importable format.
Minimal transformation needed since it's already in the correct format.
"""
import copy
import json
import uuid
from typing import Dict, Any, List

from openjiuwen.core.common.logging import logger
from pydantic import ValidationError

from openjiuwen_studio.core.dsl_converter.converter.converter import WorkflowConverter, WorkflowImportResult
from openjiuwen_studio.schemas.workflow import WorkflowBase
from openjiuwen_studio.core.database import milliseconds


class NativeWorkflowConverter(WorkflowConverter):
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
        "schema": "{\"nodes\":[{\"id\":\"start_1\",\"type\":\"1\",\"data\":{\"title\":\"START\"}},{\"id\":\"llm_2\",
                    \"type\":\"3\",\"data\":{\"title\":\"LLM\"}},{\"id\":\"end_3\",\"type\":\"2\",\"data\":
                    {\"title\":\"END\"}}],\"edges\":[{\"source\":\"start_1\",\"target\":\"llm_2\"},{\"source\":
                    \"llm_2\",\"target\":\"end_3\"}]}",
        "input_parameters": [{"name": "query", "type": "string"}],
        "output_parameters": [{"name": "response", "type": "string"}],
        "create_time": 1770709211479,
        "update_time": 1770718317014
    }

    Field transformations during conversion:
    - workflow_id: REGENERATED (new UUID) → avoid collisions
    - workflow_version: CLEARED (None) → import creates draft
    - latest_publish_*: CLEARED (None) → no version history
    - name: KEPT (or default "Imported Workflow") → importer may add suffix
    - desc, url, icon_uri: KEPT as-is (or defaults)
    - space_id: ALWAYS CLEARED → importer sets target space_id (source space_id ignored)
    - schema: NODE IDS REGENERATED → start_1 becomes start_abc123
    - input/output_parameters: KEPT as-is (or default empty arrays)
    - create_time, update_time: REGENERATED (current timestamp)

    Import Requirements (PARTIAL WORKFLOWS SUPPORTED):
    ✓ Supports two formats:
      - Format 1: Top-level 'nodes' and 'edges' (without 'schema')
      - Format 2: 'schema' field containing 'nodes' and 'edges'
    ✓ Schema has START node (type="1") and END node (type="2")
    ✓ Schema is valid JSON with nodes array and edges array
    ✓ Field constraints if provided: name (1-255 chars), desc (max 500), url (max 500)

    Missing fields get these defaults:
    - workflow_id: Generated UUID
    - space_id: ALWAYS cleared (set by importer from import context - source space_id is ignored)
    - name: "Imported Workflow"
    - desc: "Imported Workflow"
    - url: ""
    - icon_uri: ""
    - input_parameters: []
    - output_parameters: []
    - create_time: Current timestamp
    - update_time: Current timestamp

    Note: Converter automatically handles:
    - Schema as object → converts to JSON string
    - Missing fields → adds sensible defaults
    """

    def convert(self, json_data: Dict[str, Any]) -> WorkflowImportResult:
        """
        Convert OpenJiuwen native workflow for import.

        Supports PARTIAL workflows - supports two input formats:
        - Format 1: Top-level 'nodes' and 'edges' (without 'schema')
        - Format 2: 'schema' field containing 'nodes' and 'edges'

        Steps:
        0. Detect format and normalize to full format with 'schema' field
        1. Pre-process schema field:
           - Convert schema from object to JSON string if needed (some exports have it as object)
        2. Add default values for missing fields
        3. Validate structure matches WorkflowBase schema
        4. Generate new workflow_id (GUID) to avoid collisions with existing workflows
        5. Regenerate all node IDs in canvas schema to avoid conflicts
        6. Update timestamps (create_time, update_time) to current time
        7. Clear version fields (workflow_version, latest_publish_version, latest_publish_time)
        8. Check for missing resources (models, plugins, sub-workflows) - non-blocking

        Note: The actual workflow database record will be created by workflow_manager.workflow_create()
        which assigns a fresh workflow_id and auto-incrementing id field.

        Handles both schema formats:
        - String format: "schema": "{\"nodes\":[...],\"edges\":[...]}" (standard)
        - Object format: "schema": {"nodes":[...], "edges":[...]} (some exports)
        - Top-level format: {"nodes":[...], "edges":[...]} (without "schema" field)

        Default values for missing fields:
        - workflow_id: Generated UUID
        - space_id: ALWAYS cleared (source space_id ignored, set by importer from import context)
        - name: "Imported Workflow"
        - desc: "Imported Workflow"
        - url: ""
        - icon_uri: ""
        - input_parameters: []
        - output_parameters: []
        - create_time: Current timestamp
        - update_time: Current timestamp

        Args:
            json_data: OpenJiuwen workflow JSON (nodes/edges required, either top-level or in schema)

        Returns:
            WorkflowImportResult with processed workflow data

        Raises:
            ValueError: If neither 'schema' nor top-level 'nodes'/'edges' are present
        """
        warnings = []

        # Step 0: Detect format and normalize to full format with 'schema' field
        json_data = copy.deepcopy(json_data)

        # Format 1: Top-level nodes and edges (without schema)
        if "schema" not in json_data and "nodes" in json_data and "edges" in json_data:
            logger.info("Detected Format 1: Top-level nodes/edges. Converting to full format with schema.")
            # Wrap nodes and edges into schema field
            schema_obj = {
                "nodes": json_data.pop("nodes"),
                "edges": json_data.pop("edges")
            }
            json_data["schema"] = schema_obj
        # Format 2: Schema field exists
        elif "schema" not in json_data:
            raise ValueError(
                "Missing required fields: Either 'schema' field or top-level 'nodes' and 'edges' are required for "
                "import."
            )

        # Store original workflow_id for metadata
        original_workflow_id = json_data.get("workflow_id", "unknown")

        # Step 1: Pre-process: Normalize schema to string if it's an object
        # Some exports have schema as object, but WorkflowBase expects string
        schema_field = json_data.get("schema")
        if schema_field and not isinstance(schema_field, str):
            try:
                json_data["schema"] = json.dumps(schema_field)
                logger.info("Converted schema from object to JSON string")
            except (TypeError, ValueError) as e:
                raise ValueError(f"Failed to convert schema to JSON string: {e}") from e

        # Step 2: Add default values for missing fields
        current_time = milliseconds()

        # Generate workflow_id if missing
        if "workflow_id" not in json_data or not json_data["workflow_id"]:
            json_data["workflow_id"] = str(uuid.uuid4())

        # ALWAYS clear space_id - it must come from the import context (target space)
        # The space_id in the JSON is from the source system and should be ignored
        original_space_id = json_data.get("space_id")
        json_data["space_id"] = ""  # Will be set by importer to target space_id
        if original_space_id:
            logger.info(f"Ignoring source space_id '{original_space_id}' - will use target space_id from import "
                        f"context")

        # Set defaults for all optional fields
        defaults = {
            "name": "Imported Workflow",
            "desc": "Imported Workflow",
            "url": "",
            "icon_uri": "",
            "input_parameters": [],
            "output_parameters": [],
            "create_time": current_time,
            "update_time": current_time
        }

        for key, default_value in defaults.items():
            if key not in json_data or json_data[key] is None:
                json_data[key] = default_value
                if key in ["name", "desc"]:
                    logger.info(f"Added default value for missing field '{key}': {default_value}")

        # Step 3: Validate schema structure
        try:
            WorkflowBase.model_validate(json_data)
        except ValidationError as e:
            raise ValueError(f"Invalid OpenJiuwen workflow format: {e}") from e

        # Step 4: Regenerate workflow_id (avoid collisions with existing workflows)
        # Always regenerate to ensure no conflicts, even if one was provided/generated earlier
        new_workflow_id = str(uuid.uuid4())
        json_data["workflow_id"] = new_workflow_id
        logger.info(f"Regenerated workflow_id: {original_workflow_id} → {new_workflow_id}")

        # Step 5: Regenerate node IDs in canvas
        schema_str = json_data.get("schema")
        if schema_str:
            try:
                schema = json.loads(schema_str) if isinstance(schema_str, str) else schema_str
                schema, id_mapping = self.regenerate_canvas_ids(schema)
                json_data["schema"] = json.dumps(schema)
                logger.info(f"Regenerated {len(id_mapping)} node IDs in canvas")
            except (json.JSONDecodeError, TypeError) as e:
                warnings.append(f"Failed to regenerate canvas IDs: {e}")
                logger.warning(f"Failed to regenerate canvas IDs: {e}")

        # Step 6: Update timestamps (always regenerate to current time)
        current_time = milliseconds()
        json_data["create_time"] = current_time
        json_data["update_time"] = current_time

        # Step 7: Clear version fields (import creates draft)
        json_data.pop("workflow_version", None)
        json_data.pop("latest_publish_version", None)
        json_data.pop("latest_publish_time", None)

        # Step 8: Check for missing resources (non-blocking)
        # missing_resources = self._check_missing_resources(json_data)
        # if missing_resources:
        #     for resource in missing_resources:
        #         warnings.append(f"Referenced resource may not exist: {resource}")

        return WorkflowImportResult(
            workflow_data=json_data,
            warnings=warnings,
            metadata={
                "original_workflow_id": original_workflow_id,
                "source_format": "openjiuwen_native",
                "regenerated_nodes": len(id_mapping) if 'id_mapping' in locals() else 0
            }
        )

    def regenerate_canvas_ids(self, schema: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, str]]:
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
            source = edge.get("sourceNodeID")
            target = edge.get("targetNodeID")

            if source in id_mapping:
                edge["sourceNodeID"] = id_mapping[source]

            if target in id_mapping:
                edge["targetNodeID"] = id_mapping[target]

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

    @staticmethod
    def _update_nested_references(node: Dict, id_mapping: Dict[str, str]) -> None:
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
                    source = edge.get("sourceNodeID")
                    target = edge.get("targetNodeID")
                    if source in id_mapping:
                        edge["sourceNodeID"] = id_mapping[source]
                    if target in id_mapping:
                        edge["targetNodeID"] = id_mapping[target]

    @staticmethod
    def _check_missing_resources(workflow_data: Dict[str, Any]) -> List[str]:
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
