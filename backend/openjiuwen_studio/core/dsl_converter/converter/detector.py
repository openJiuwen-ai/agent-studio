#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
Workflow Format Detector

Detects the format of workflow JSON to determine which converter to use.
"""

from enum import Enum
from typing import Dict, Any

from openjiuwen.core.common.logging import logger


class WorkflowFormat(str, Enum):
    """Supported workflow formats"""
    OPENJIUWEN_NATIVE = "openjiuwen"
    N8N = "n8n"
    UNSUPPORTED = "unsupported"


class WorkflowDetector:
    """Detects workflow format from JSON structure"""

    def detect_format(self, json_data: Dict[str, Any]) -> WorkflowFormat:
        """
        Detects workflow format from JSON structure.

        Args:
            json_data: Workflow JSON data

        Returns:
            WorkflowFormat enum indicating the detected format
        """
        if not isinstance(json_data, dict):
            logger.warning("Invalid workflow data: not a dictionary")
            return WorkflowFormat.UNSUPPORTED

        # Check for OpenJiuwen native format
        if self.is_openjiuwen_format(json_data):
            logger.info("Detected OpenJiuwen native workflow format")
            return WorkflowFormat.OPENJIUWEN_NATIVE

        # Check for n8n format
        if self.is_n8n_format(json_data):
            logger.info("Detected n8n workflow format")
            return WorkflowFormat.N8N

        logger.warning("Unsupported workflow format")
        return WorkflowFormat.UNSUPPORTED

    @staticmethod
    def is_openjiuwen_format(data: Dict[str, Any]) -> bool:
        """
        Check if data matches OpenJiuwen native format.

        OpenJiuwen signature:
        - Has 'workflow_id' field
        - Has 'schema' field (canvas JSON string)
        - Schema contains 'nodes' and 'edges'
        """
        # Check for required top-level fields
        if "schema" not in data:
            return False

        # Optionally verify schema structure
        schema = data.get("schema")
        if isinstance(schema, str):
            # Schema is JSON string - this is the expected format
            try:
                import json
                schema_obj = json.loads(schema)
                if not isinstance(schema_obj, dict):
                    return False
                # Check for nodes/edges structure
                if "nodes" not in schema_obj or "edges" not in schema_obj:
                    return False
            except (json.JSONDecodeError, TypeError):
                return False
        elif isinstance(schema, dict):
            # Schema is already a dict (alternative format)
            if "nodes" not in schema or "edges" not in schema:
                return False
        else:
            return False

        return True

    @staticmethod
    def is_n8n_format(data: Dict[str, Any]) -> bool:
        """
        Check if data matches n8n workflow format.

        n8n signature:
        - Has 'nodes' array at top level
        - Has 'connections' dict at top level
        - Nodes have 'type' starting with 'n8n-nodes-base.'
        """
        # Check for required top-level fields
        if "nodes" not in data or "connections" not in data:
            return False

        nodes = data.get("nodes", [])
        if not isinstance(nodes, list) or len(nodes) == 0:
            return False

        # Check if at least one node has n8n-specific type
        for node in nodes[:5]:  # Check first 5 nodes
            if not isinstance(node, dict):
                continue

            node_type = node.get("type", "")
            if isinstance(node_type, str) and node_type.startswith("n8n-nodes-base."):
                return True

            # Also check for @n8n/ prefix (newer n8n versions)
            if isinstance(node_type, str) and node_type.startswith("@n8n/"):
                return True

        return False
