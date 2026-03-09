#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
N8N Workflow Converter

Converts n8n workflow format to OpenJiuwen format.
"""

import json
import uuid
from typing import Dict, Any, List, Tuple

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.dsl_converter.converter.converter import WorkflowConverter, WorkflowImportResult
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.database import milliseconds


class N8nWorkflowConverter(WorkflowConverter):
    """Converts n8n workflows to OpenJiuwen format"""

    # Node type mapping: n8n → OpenJiuwen
    N8N_TO_OPENJIUWEN = {
        "n8n-nodes-base.httpRequest": ComponentType.COMPONENT_TYPE_PLUGIN,
        "n8n-nodes-base.code": ComponentType.COMPONENT_TYPE_CODE,
        "n8n-nodes-base.function": ComponentType.COMPONENT_TYPE_CODE,
        "n8n-nodes-base.functionItem": ComponentType.COMPONENT_TYPE_CODE,
        "n8n-nodes-base.if": ComponentType.COMPONENT_TYPE_IF,
        "n8n-nodes-base.switch": ComponentType.COMPONENT_TYPE_IF,
        "n8n-nodes-base.merge": ComponentType.COMPONENT_TYPE_VARIABLE_MERGE,
        "n8n-nodes-base.set": ComponentType.COMPONENT_TYPE_TEXT_EDITOR,
        # Add more mappings as needed
    }

    def convert(self, json_data: Dict[str, Any]) -> WorkflowImportResult:
        """
        Convert n8n workflow to OpenJiuwen format.

        Args:
            json_data: n8n workflow JSON

        Returns:
            WorkflowImportResult with converted workflow

        Raises:
            ValueError: If conversion fails
        """
        warnings = []

        # Extract n8n workflow data
        n8n_name = json_data.get("name", "Imported n8n Workflow")
        n8n_nodes = json_data.get("nodes", [])
        n8n_connections = json_data.get("connections", {})

        if not n8n_nodes:
            raise ValueError("n8n workflow has no nodes")

        logger.info(f"Converting n8n workflow '{n8n_name}' with {len(n8n_nodes)} nodes")

        # Convert nodes
        # Convert nodes
        openjiuwen_nodes = []
        node_name_to_id = {}

        for n8n_node in n8n_nodes:
            node_name = n8n_node.get("name", n8n_node.get("id", "unknown"))
            node_type = n8n_node.get("type", "unknown")

            try:
                # --- CHANGE START ---
                # Check if the node type is known in our mapping
                if node_type not in self.N8N_TO_OPENJIUWEN:
                    # Log a warning to satisfy the 'conversion_warnings' test
                    msg = f"Node type '{node_type}' is not supported. Converted to fallback node."
                    warnings.append(msg)
                    logger.warning(msg)

                    # Force the fallback logic
                    fallback = self._create_fallback_node(n8n_node)
                    openjiuwen_nodes.append(fallback)
                    node_name_to_id[node_name] = fallback["id"]
                    continue

                    # Original logic for supported nodes
                converted = self._convert_node(n8n_node)
                openjiuwen_nodes.append(converted)
                node_name_to_id[node_name] = converted["id"]
                # --- CHANGE END ---

            except Exception as e:
                # Existing catch-all for unexpected crashes
                error_msg = f"Failed to convert node '{node_name}': {e}"
                if error_msg not in warnings:
                    warnings.append(error_msg)
                logger.warning(error_msg)

                fallback = self._create_fallback_node(n8n_node)
                openjiuwen_nodes.append(fallback)
                node_name_to_id[node_name] = fallback["id"]

        # Convert connections to edges
        edges = self._convert_connections(n8n_connections, n8n_nodes, node_name_to_id)

        # Add START and END nodes
        openjiuwen_nodes, edges = self.add_start_end_nodes(openjiuwen_nodes, edges)

        # Extract inputs/outputs
        inputs, outputs = self._extract_io_parameters(openjiuwen_nodes)

        # Build workflow data
        workflow_id = str(uuid.uuid4())
        current_time = milliseconds()

        workflow_data = {
            "workflow_id": workflow_id,
            "name": f"{n8n_name} (Imported)",
            "desc": f"Imported from n8n workflow: {n8n_name}",
            "space_id": "",  # Will be set by importer
            "schema": json.dumps({
                "nodes": openjiuwen_nodes,
                "edges": edges
            }),
            "input_parameters": inputs,
            "output_parameters": outputs,
            "create_time": current_time,
            "update_time": current_time,
            "url": "",
            "icon_uri": ""
        }

        return WorkflowImportResult(
            workflow_data=workflow_data,
            warnings=warnings,
            metadata={
                "source": "n8n",
                "source_format": "n8n",
                "original_name": n8n_name,
                "converted_nodes": len(openjiuwen_nodes),
                "original_nodes": len(n8n_nodes),
                "skipped_nodes": len(warnings)
            }
        )

    def _convert_node(self, n8n_node: Dict[str, Any]) -> Dict[str, Any]:
        """Convert single n8n node to OpenJiuwen format"""
        n8n_type = n8n_node.get("type", "")
        n8n_name = n8n_node.get("name", "Node")
        node_id = self.generate_node_id(n8n_type)

        # Get OpenJiuwen component type
        openjiuwen_type = self.N8N_TO_OPENJIUWEN.get(
            n8n_type,
            ComponentType.COMPONENT_TYPE_CODE  # Default fallback
        )

        # Convert based on type
        if openjiuwen_type == ComponentType.COMPONENT_TYPE_PLUGIN:
            return self._convert_http_request_node(n8n_node, node_id)
        elif openjiuwen_type == ComponentType.COMPONENT_TYPE_CODE:
            return self._convert_code_node(n8n_node, node_id)
        elif openjiuwen_type == ComponentType.COMPONENT_TYPE_IF:
            return self._convert_if_node(n8n_node, node_id)
        elif openjiuwen_type == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            return self._convert_merge_node(n8n_node, node_id)
        else:
            # Generic conversion
            return self._create_generic_node(n8n_node, node_id, openjiuwen_type)

    def _convert_http_request_node(self, n8n_node: Dict, node_id: str) -> Dict:
        """Convert n8n HTTP Request to OpenJiuwen Plugin (Service)"""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [0, 0])

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_PLUGIN),
            "data": {
                "title": n8n_node.get("name", "API Call"),
                "inputs": {
                    "inputParameters": {}
                },
                "configs": {
                    "type": "service",
                    "tool": {
                        "url": params.get("url", ""),
                        "method": params.get("method", "GET"),
                        "headers": self.convert_headers(params.get("headerParameters", {})),
                        "body": params.get("body", "")
                    }
                }
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    @staticmethod
    def _convert_code_node(n8n_node: Dict, node_id: str) -> Dict:
        """Convert n8n Code/Function to OpenJiuwen Code component"""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [0, 0])

        # n8n stores code in different fields depending on node type
        code = (params.get("code") or
                params.get("functionCode") or
                params.get("jsCode") or
                "// No code found")

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_CODE),
            "data": {
                "title": n8n_node.get("name", "Code"),
                "inputs": {
                    "inputParameters": {}
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                },
                "configs": {
                    "language": "javascript",  # n8n uses JavaScript
                    "code": code
                },
                "exception_config": {
                    "process_type": "break"
                }
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    @staticmethod
    def _convert_if_node(n8n_node: Dict, node_id: str) -> Dict:
        """Convert n8n IF/Switch to OpenJiuwen Branch component"""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [0, 0])

        # Extract condition
        conditions = params.get("conditions", {})
        condition_str = str(conditions) if conditions else "true"

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_IF),
            "data": {
                "title": n8n_node.get("name", "Branch"),
                "inputs": {
                    "inputParameters": {}
                },
                "branches": [
                    {
                        "branch_id": f"branch_true_{uuid.uuid4().hex[:8]}",
                        "bool_expression": condition_str
                    },
                    {
                        "branch_id": f"branch_false_{uuid.uuid4().hex[:8]}",
                        "bool_expression": "True"  # Else branch
                    }
                ]
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    @staticmethod
    def _convert_merge_node(n8n_node: Dict, node_id: str) -> Dict:
        """Convert n8n Merge to OpenJiuwen Variable Merge component"""
        position = n8n_node.get("position", [0, 0])

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_VARIABLE_MERGE),
            "data": {
                "title": n8n_node.get("name", "Merge"),
                "inputs": {
                    "inputParameters": {}
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "merged": {"type": "object"}
                    }
                },
                "configs": {
                    "groups": []
                }
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    @staticmethod
    def _create_generic_node(n8n_node: Dict, node_id: str, component_type: ComponentType) -> Dict:
        """Create generic OpenJiuwen node"""
        position = n8n_node.get("position", [0, 0])

        return {
            "id": node_id,
            "type": str(component_type),
            "data": {
                "title": n8n_node.get("name", "Node"),
                "inputs": {
                    "inputParameters": {}
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                }
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    def _create_fallback_node(self, n8n_node: Dict) -> Dict:
        """Create fallback CODE node for unsupported n8n nodes"""
        node_id = self.generate_node_id("fallback")
        position = n8n_node.get("position", [0, 0])
        n8n_type = n8n_node.get("type", "unknown")

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_CODE),
            "data": {
                "title": f"{n8n_node.get('name', 'Node')} (TODO)",
                "inputs": {
                    "inputParameters": {}
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string"}
                    }
                },
                "configs": {
                    "language": "python3",
                    "code": f"# TODO: Implement logic from n8n node type: {n8n_type}\n# Original node parameters: "
                            f"{json.dumps(n8n_node.get('parameters', {}), indent=2)}\nresult = "
                            f"'Not implemented'"
                },
                "exception_config": {
                    "process_type": "break"
                }
            },
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else 0,
                    "y": position[1] if len(position) > 1 else 0
                }
            }
        }

    # 1. Add node_name_to_id to the arguments
    @staticmethod
    def _convert_connections(n8n_connections: Dict, n8n_nodes: List[Dict], node_name_to_id: Dict[str, str]) \
            -> List[Dict]:
        """Convert n8n connections to OpenJiuwen edges"""
        edges = []

        # --- DELETE the old node_name_to_id mapping logic here ---
        # We now use the one passed from the caller to ensure IDs match.

        for source_name, conn_types in n8n_connections.items():
            source_id = node_name_to_id.get(source_name)
            if not source_id:
                continue

            for conn_type, target_lists in conn_types.items():
                # n8n connections are nested lists: main -> [ [targets], [targets] ]
                for target_list in target_lists:
                    for target in target_list:
                        target_name = target.get("node")
                        target_id = node_name_to_id.get(target_name)

                        if target_id:
                            edges.append({
                                "id": f"edge_{uuid.uuid4().hex[:8]}",
                                "sourceNodeID": source_id,
                                "targetNodeID": target_id,
                                "sourceHandle": "output",
                                "targetHandle": "input"
                            })

        return edges

    @staticmethod
    def add_start_end_nodes(nodes: List[Dict], edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Add START and END nodes to workflow"""
        # Find entry points (nodes with no incoming connections)
        all_targets = {edge["targetNodeID"] for edge in edges}
        entry_nodes = [n for n in nodes if n["id"] not in all_targets]

        # Create START node
        start_id = f"start_{uuid.uuid4().hex[:8]}"
        start_node = {
            "id": start_id,
            "type": str(ComponentType.COMPONENT_TYPE_START),
            "data": {
                "title": "Start",
                "outputs": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "default": ""
                        }
                    }
                }
            },
            "meta": {
                "position": {"x": 100, "y": 100}
            }
        }

        # Connect START to all entry nodes
        for entry in entry_nodes:
            edges.append({
                "id": f"edge_{uuid.uuid4().hex[:8]}",
                "sourceNodeID": start_id,
                "targetNodeID": entry["id"],
                "sourceHandle": "output",
                "targetHandle": "input"
            })

        # Find exit points (nodes with no outgoing connections)
        all_sources = {edge["sourceNodeID"] for edge in edges}
        exit_nodes = [n for n in nodes if n["id"] not in all_sources]

        # Create END node
        end_id = f"end_{uuid.uuid4().hex[:8]}"
        end_node = {
            "id": end_id,
            "type": str(ComponentType.COMPONENT_TYPE_END),
            "data": {
                "title": "End",
                "inputs": {
                    "inputParameters": {
                        "result": {
                            "type": "ref",
                            "content": []
                        }
                    }
                }
            },
            "meta": {
                "position": {"x": 1000, "y": 100}
            }
        }

        # Connect all exit nodes to END
        for exit_node in exit_nodes:
            edges.append({
                "id": f"edge_{uuid.uuid4().hex[:8]}",
                "sourceNodeID": exit_node["id"],
                "targetNodeID": end_id,
                "sourceHandle": "output",
                "targetHandle": "input"
            })

        nodes.extend([start_node, end_node])
        return nodes, edges

    @staticmethod
    def _extract_io_parameters(nodes: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Extract input/output parameters from START/END nodes"""
        inputs = []
        outputs = []

        for node in nodes:
            if str(node.get("type")) == str(ComponentType.COMPONENT_TYPE_START):
                outputs_data = node.get("data", {}).get("outputs", {})
                properties = outputs_data.get("properties", {})
                for name, prop in properties.items():
                    inputs.append({
                        "name": name,
                        "type": prop.get("type", "string"),
                        "description": prop.get("description", ""),
                        "required": False
                    })

            elif str(node.get("type")) == str(ComponentType.COMPONENT_TYPE_END):
                # END node defines workflow outputs
                outputs.append({
                    "name": "result",
                    "type": "string",
                    "description": "Workflow result"
                })

        return inputs, outputs

    @staticmethod
    def convert_headers(header_params: Dict) -> Dict:
        """Convert n8n header parameters to dict"""
        if not header_params:
            return {}

        # n8n can have headers in different formats
        if isinstance(header_params, dict):
            return header_params

        # Handle array format
        if isinstance(header_params, list):
            headers = {}
            for item in header_params:
                if isinstance(item, dict):
                    name = item.get("name")
                    value = item.get("value")
                    if name and value:
                        headers[name] = value
            return headers

        return {}

    @staticmethod
    def generate_node_id(node_type: str) -> str:
        """Generate unique node ID"""
        # Extract simple type name
        if node_type.startswith("n8n-nodes-base."):
            simple_type = node_type.replace("n8n-nodes-base.", "")
        else:
            simple_type = node_type

        return f"{simple_type}_{uuid.uuid4().hex[:8]}"

    def _get_converted_node_id(self, n8n_node: Dict) -> str:
        """Get the ID that would be assigned to this n8n node after conversion"""
        # This is a simplified version - in practice, we'd need to track IDs during conversion
        return self.generate_node_id(n8n_node.get("type", "node"))
