#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
N8N Workflow Converter

Converts n8n workflow format to OpenJiuwen format.

Features:
- Comprehensive node type mapping (60+ types)
- LLM/Agent node conversion with model detection
- Trigger merging into Start node
- Form field extraction
- Expression conversion ({{ $json.x }} → {{x}})
- AI sub-node embedding
- Loop and conditional support
- Sequential ID generation

Version: 2.0.0
"""

import json
import re
import uuid
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.dsl_converter.converter.converter import WorkflowConverter, WorkflowImportResult
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.database import milliseconds

from openjiuwen_studio.core.dsl_converter.converter.n8n_mappings import (
    N8N_TO_OPENJIUWEN,
    AI_SUBNODES,
    APP_NODE_PATTERNS,
)


# =============================================================================
# ID GENERATOR
# =============================================================================

class IDGenerator:
    """Generate sequential IDs like Jiuwen: start_1, llm_1, end_1"""
    
    def __init__(self):
        self.counters: Dict[str, int] = defaultdict(int)
    
    def next_id(self, prefix: str) -> str:
        """Generate next sequential ID for given prefix."""
        self.counters[prefix] += 1
        return f"{prefix}_{self.counters[prefix]}"
    
    def reset(self):
        """Reset all counters."""
        self.counters = defaultdict(int)


# =============================================================================
# TRANSFORMATION REPORT
# =============================================================================

@dataclass
class UnsupportedNode:
    """Track unsupported node details."""
    node_name: str
    node_type: str
    reason: str
    fallback: str


@dataclass
class TransformationReport:
    """Report of transformation results."""
    total_nodes: int = 0
    converted_nodes: int = 0
    skipped_nodes: int = 0
    unsupported_nodes: List[UnsupportedNode] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    n8n_type_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    jiuwen_type_counts: Dict[int, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    def add_unsupported(self, name: str, n8n_type: str, reason: str, fallback: str):
        """Add unsupported node to report."""
        self.unsupported_nodes.append(UnsupportedNode(name, n8n_type, reason, fallback))
    
    def add_warning(self, message: str):
        """Add warning to report."""
        self.warnings.append(message)
    
    def to_warnings_list(self) -> List[str]:
        """Convert to list of warning strings for WorkflowImportResult."""
        result = list(self.warnings)
        for node in self.unsupported_nodes:
            result.append(
                f"Node '{node.node_name}' ({node.node_type}): {node.reason}. {node.fallback}"
            )
        return result
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            "=" * 60,
            "TRANSFORMATION REPORT",
            "=" * 60,
            f"Total n8n nodes: {self.total_nodes}",
            f"Converted: {self.converted_nodes}",
            f"Skipped (embedded): {self.skipped_nodes}",
            f"Unsupported: {len(self.unsupported_nodes)}",
            ""
        ]
        
        if self.n8n_type_counts:
            lines.append("N8N NODE TYPES ENCOUNTERED:")
            for n8n_type, count in sorted(self.n8n_type_counts.items()):
                lines.append(f"  {n8n_type}: {count}")
            lines.append("")
        
        if self.jiuwen_type_counts:
            lines.append("CONVERTED TO OPENJIUWEN TYPES:")
            for jiuwen_type, nodes in sorted(self.jiuwen_type_counts.items()):
                type_name = self._get_type_name(jiuwen_type)
                lines.append(f"  Type {jiuwen_type} ({type_name}): {len(nodes)} nodes")
                for node in nodes:
                    lines.append(f"- {node}")
            lines.append("")
        
        if self.unsupported_nodes:
            lines.append("⚠️  UNSUPPORTED NODES:")
            for node in self.unsupported_nodes:
                lines.append(f"- {node.node_name}")
                lines.append(f"      Type: {node.node_type}")
                lines.append(f"      Reason: {node.reason}")
                lines.append(f"      Fallback: {node.fallback}")
            lines.append("")
        
        if self.warnings:
            lines.append("⚠️  WARNINGS:")
            for w in self.warnings:
                lines.append(f"- {w}")
            lines.append("")
        
        if not self.unsupported_nodes and not self.warnings:
            lines.append("✓ All nodes converted successfully!")
        
        return "\n".join(lines)
    
    @staticmethod
    def _get_type_name(type_num: int) -> str:
        """Get human-readable name for component type."""
        names = {
            1: "Start",
            2: "End",
            3: "LLM",
            4: "Selector/IF",
            5: "Loop",
            10: "Code",
            11: "Intent",
            12: "Variable",
            15: "Block Start",
            16: "Block End",
            19: "Plugin",
            20: "Workflow",
            21: "Questioner",
            22: "Text Editor",
            23: "Variable Merge",
        }
        return names.get(type_num, f"Unknown({type_num})")


# =============================================================================
# MAIN CONVERTER CLASS
# =============================================================================

class N8nWorkflowConverter(WorkflowConverter):
    """
    Converts n8n workflows to OpenJiuwen format.
    
    Features:
    - Comprehensive node type mapping (60+ types)
    - LLM/Agent node conversion with model detection
    - Trigger merging into Start node
    - Form field extraction
    - Expression conversion ({{ $json.x }} → {{x}})
    - AI sub-node embedding
    - Loop and conditional support
    - Sequential ID generation
    
    Usage:
        converter = N8nWorkflowConverter()
        result = converter.convert(n8n_workflow_json)
    """

    # Node type mapping imported from n8n_mappings module
    N8N_TO_OPENJIUWEN = N8N_TO_OPENJIUWEN

    # =========================================================================
    # INITIALIZATION
    # =========================================================================

    def __init__(self, locale: str = "en"):
        """Initialize converter with tracking state.

        Args:
            locale: UI language code. Supported values:
                    'en' (default) — English titles
                    'zh' (or 'zh-CN', 'zh_CN', 'chinese') — Chinese titles
        """
        self.locale = locale
        self._reset_state()

    # =========================================================================
    # LOCALISED TITLES
    # =========================================================================

    TITLES: Dict[str, Dict[str, str]] = {
        "en": {
            "start": "Start",
            "end": "End",
            "llm": "LLM {n}",
            "selector": "Selector",
            "loop": "Loop",
            "block_start": "Block Start",
            "block_end": "Block End",
            "merge": "Merge",
            "code": "Code",
        },
        "zh": {
            "start": "开始",
            "end": "结束",
            "llm": "大模型{n}",
            "selector": "选择器",
            "loop": "循环",
            "block_start": "块开始",
            "block_end": "块结束",
            "merge": "合并",
            "code": "代码",
        },
    }

    def get_title(self, key: str, n: int = 1) -> str:
        """Return a localised UI title for the given key."""
        lang = getattr(self, "locale", "en")
        # Normalise: accept 'zh-CN', 'zh_CN', 'chinese' etc. → 'zh'
        if lang.lower().startswith("zh") or lang.lower() in ("chinese", "cn"):
            lang = "zh"
        else:
            lang = "en"
        template = self.TITLES.get(lang, self.TITLES["en"]).get(key, key)
        return template.format(n=n)

    def _reset_state(self):
        """Reset converter state for new conversion."""
        # Preserve locale across resets (set once in __init__ or convert())
        if not hasattr(self, "locale"):
            self.locale = "en"
        self.id_gen = IDGenerator()
        self.node_id_map: Dict[str, str] = {}  # n8n_name → jiuwen_id
        self.nodes_by_name: Dict[str, Dict] = {}  # n8n_name → n8n_node
        self.n8n_connections: Dict[str, Any] = {}  # Original n8n connections
        self.trigger_node: Optional[Dict] = None
        self.trigger_nodes: List[Dict] = []
        self.start_node_id: Optional[str] = None
        self.end_node_id: Optional[str] = None
        self.field_name_map: Dict[str, str] = {}  # n8n field → jiuwen field
        self.report = TransformationReport()
        self.openjiuwen_nodes: List[Dict] = []
        self.openjiuwen_edges: List[Dict] = []
        self.last_llm_node_id: Optional[str] = None
        self.first_main_node: Optional[str] = None

    # =========================================================================
    # MAIN CONVERT METHOD
    # =========================================================================

    def convert(self, json_data: Dict[str, Any], locale: str = "") -> WorkflowImportResult:
        """
        Convert n8n workflow to OpenJiuwen format.

        Args:
            json_data: n8n workflow JSON

        Returns:
            WorkflowImportResult with converted workflow

        Raises:
            ValueError: If conversion fails
        """
        # Reset state for new conversion (honour per-call locale override)
        if locale:
            self.locale = locale
        self._reset_state()
        
        # Extract n8n workflow data
        n8n_name = json_data.get("name", "Imported n8n Workflow")
        n8n_nodes = json_data.get("nodes", [])
        self.n8n_connections = json_data.get("connections", {})

        if not n8n_nodes:
            raise ValueError("n8n workflow has no nodes")

        logger.info(f"Converting n8n workflow '{n8n_name}' with {len(n8n_nodes)} nodes")

        # Step 1: Index nodes by name and classify them
        self._index_nodes(n8n_nodes)
        
        # Step 2: Create Start node (from trigger or generic)
        self._create_start_node()
        
        # Step 3: Convert main nodes
        self._convert_main_nodes(n8n_nodes)
        
        # Step 4: Convert connections to edges
        self._convert_connections()
        
        # Step 5: Find last node and create End node
        last_node_id = self._find_last_node()
        self._create_end_node(last_node_id)
        
        # Step 6: Ensure proper edge connections
        self._ensure_edge_connections()

        # Step 7: Extract inputs/outputs
        inputs, outputs = self._extract_io_parameters()

        # Build workflow data
        workflow_id = str(uuid.uuid4())
        current_time = milliseconds()

        workflow_data = {
            "workflow_id": workflow_id,
            "name": f"{n8n_name}",
            "desc": f"Imported from n8n workflow: {n8n_name}",
            "space_id": "",  # Will be set by importer
            "schema": json.dumps({
                "nodes": self.openjiuwen_nodes,
                "edges": self.openjiuwen_edges
            }),
            "input_parameters": inputs,
            "output_parameters": outputs,
            "create_time": current_time,
            "update_time": current_time,
            "url": "",
            "icon_uri": ""
        }

        logger.info(self.report.summary())

        return WorkflowImportResult(
            workflow_data=workflow_data,
            warnings=self.report.to_warnings_list(),
            metadata={
                "source": "n8n",
                "source_format": "n8n",
                "original_name": n8n_name,
                "converted_nodes": self.report.converted_nodes,
                "original_nodes": self.report.total_nodes,
                "skipped_nodes": self.report.skipped_nodes
            }
        )

    def convert_to_schema(self, n8n_json: Dict[str, Any], locale: str = "") -> Dict[str, Any]:
        """
        Convert n8n workflow to OpenJiuwen schema (nodes and edges only).
        Args:
            n8n_json: n8n workflow JSON
        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        if locale:
            self.locale = locale
        self._reset_state()
        n8n_nodes = n8n_json.get("nodes", [])
        self.n8n_connections = n8n_json.get("connections", {})
        self._index_nodes(n8n_nodes)
        self._create_start_node()
        self._convert_main_nodes(n8n_nodes)
        self._convert_connections()
        last_node_id = self._find_last_node()
        self._create_end_node(last_node_id)
        self._ensure_edge_connections()
        return {
            "nodes": self.openjiuwen_nodes,
            "edges": self.openjiuwen_edges
        }
    
    # =========================================================================
    # NODE INDEXING AND CLASSIFICATION
    # =========================================================================

    def _index_nodes(self, n8n_nodes: List[Dict]):
        """Index nodes by name and classify triggers vs main nodes."""
        for node in n8n_nodes:
            name = node.get("name", "")
            node_type = node.get("type", "")
            
            self.nodes_by_name[name] = node
            self.report.total_nodes += 1
            self.report.n8n_type_counts[node_type] += 1
            
            # Identify triggers
            if self._is_trigger_node(node_type):
                self.trigger_nodes.append(node)
                if self.trigger_node is None:
                    self.trigger_node = node

    @staticmethod
    def _is_trigger_node(node_type: str) -> bool:
        """Check if node type is a trigger."""
        return (
            "Trigger" in node_type or 
            "trigger" in node_type or 
            node_type == "n8n-nodes-base.webhook" or
            node_type == "n8n-nodes-base.cron"
        )

    @staticmethod
    def _is_ai_subnode(node_type: str) -> bool:
        """Check if node type is an AI sub-node that should be embedded."""
        return node_type in AI_SUBNODES

    @staticmethod
    def _is_app_node(node_type: str) -> bool:
        """Check if node type is an app integration."""
        node_type_lower = node_type.lower()
        return any(pattern in node_type_lower for pattern in APP_NODE_PATTERNS)

    # =========================================================================
    # START NODE CREATION
    # =========================================================================

    def _create_start_node(self):
        """Create Start node from trigger or generic."""
        self.start_node_id = self.id_gen.next_id("start")
        
        if self.trigger_node:
            start_node = self._create_start_from_trigger(self.trigger_node)
            # Map all trigger names to start ID
            for trigger in self.trigger_nodes:
                self.node_id_map[trigger.get("name", "")] = self.start_node_id
        else:
            start_node = self._create_generic_start_node()
        
        self.openjiuwen_nodes.append(start_node)

    def _create_start_from_trigger(self, trigger_node: Dict) -> Dict:
        """Create Start node with outputs extracted from trigger."""
        outputs = self._build_trigger_outputs(trigger_node)
        
        return {
            "id": self.start_node_id,
            "type": str(ComponentType.COMPONENT_TYPE_START),
            "meta": {"position": {"x": 180, "y": 34}},
            "data": {
                "title": self.get_title("start"),
                "outputs": outputs
            }
        }

    def _create_generic_start_node(self) -> Dict:
        """Create generic Start node."""
        return {
            "id": self.start_node_id,
            "type": str(ComponentType.COMPONENT_TYPE_START),
            "meta": {"position": {"x": 180, "y": 34}},
            "data": {
                "title": self.get_title("start"),
                "outputs": {
                    "type": "object",
                    "properties": {
                        "input": {
                            "type": "string",
                            "default": "",
                            "description": "Workflow input"
                        }
                    },
                    "required": []
                }
            }
        }

    def _build_trigger_outputs(self, trigger_node: Dict) -> Dict:
        """Build output schema from trigger node."""
        node_type = trigger_node.get("type", "")
        params = trigger_node.get("parameters", {})

        # Manual trigger has no inputs/outputs — it just starts execution
        if "manual" in node_type.lower():
            return {
                "type": "object",
                "properties": {},
                "required": []
            }

        if "webhook" in node_type.lower():
            return {
                "type": "object",
                "properties": {
                    "body": {"type": "object"},
                    "headers": {"type": "object"},
                    "query": {"type": "object"}
                },
                "required": []
            }
        
        elif "chat" in node_type.lower():
            return {
                "type": "object",
                "properties": {
                    "chatInput": {
                        "type": "string",
                        "description": "User chat input"
                    }
                },
                "required": ["chatInput"]
            }
        
        elif "form" in node_type.lower():
            return self._build_form_trigger_outputs(params)
        
        else:
            return {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "default": "",
                        "description": "Trigger input"
                    }
                },
                "required": []
            }

    def _build_form_trigger_outputs(self, params: Dict) -> Dict:
        """Build output schema from form trigger fields."""
        properties = {}
        required = []
        form_fields = params.get("formFields", {}).get("values", [])
        
        for idx, f in enumerate(form_fields):
            field_label = f.get("fieldLabel", f"field_{idx}")
            
            # Map common field names to Jiuwen conventions
            field_lower = field_label.lower().strip()
            if field_lower in ["location", "city", "城市"]:
                jiuwen_name = "city"
            elif field_lower in ["date", "time", "日期", "时间"]:
                jiuwen_name = "date"
            else:
                # Sanitize: only keep alphanumeric, underscores, and CJK characters
                jiuwen_name = re.sub(r'[^a-z0-9_\u4e00-\u9fff]', '_', field_lower)
                jiuwen_name = re.sub(r'_+', '_', jiuwen_name).strip('_')
                if not jiuwen_name:
                    jiuwen_name = f"field_{idx}"
            
            # Store mapping for LLM prompt conversion
            self.field_name_map[field_label] = jiuwen_name
            
            prop = {
                "type": "string",
                "default": "",
                "description": f.get("placeholder", f"Input for {jiuwen_name}")
            }
            
            # Add extra.index for non-first fields (matching Jiuwen pattern)
            if idx > 0:
                prop["extra"] = {"index": idx + 1}
            
            properties[jiuwen_name] = prop
            
            if f.get("requiredField", False):
                required.append(jiuwen_name)
        
        # If no form fields found, create generic outputs
        if not properties:
            properties = {
                "input": {
                    "type": "string",
                    "default": "",
                    "description": "Form input"
                }
            }
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    # =========================================================================
    # MAIN NODE CONVERSION
    # =========================================================================

    def _convert_main_nodes(self, n8n_nodes: List[Dict]):
        """Convert all main (non-trigger, non-subnode) nodes."""
        x_pos = 640
        
        for node in n8n_nodes:
            node_name = node.get("name", "")
            node_type = node.get("type", "")
            
            # Skip triggers (already merged into Start)
            if node in self.trigger_nodes:
                continue
            
            # Skip AI sub-nodes (embedded into LLM nodes)
            if self._is_ai_subnode(node_type):
                self.report.skipped_nodes += 1
                continue
            
            # Optimise away pure passthrough Set nodes ---
            if self._is_passthrough_set_node(node):
                predecessor_id = self._find_predecessor_id(node_name)
                if predecessor_id:
                    # Map this node's name to its predecessor's ID so that
                    # _convert_connections will wire predecessor → successor directly
                    self.node_id_map[node_name] = predecessor_id
                    self.report.skipped_nodes += 1
                    self.report.add_warning(
                        f"Set node '{node_name}' is a passthrough – removed; "
                        f"connections merged into predecessor."
                    )
                    continue

            # Convert node
            try:
                jiuwen_node = self._convert_node(node, x_pos)
                if jiuwen_node:
                    self.openjiuwen_nodes.append(jiuwen_node)
                    self.node_id_map[node_name] = jiuwen_node["id"]
                    self.report.converted_nodes += 1
                    
                    jiuwen_type = int(jiuwen_node.get("type", 0))
                    self.report.jiuwen_type_counts[jiuwen_type].append(node_name)
                    
                    # Track last LLM node for End node reference
                    if jiuwen_type == ComponentType.COMPONENT_TYPE_LLM:
                        self.last_llm_node_id = jiuwen_node["id"]
                    
                    if self.first_main_node is None:
                        self.first_main_node = node_name
                    
                    x_pos += 460
            except Exception as e:
                # Fallback for conversion errors
                error_msg = f"Failed to convert node '{node_name}': {e}"
                self.report.add_warning(error_msg)
                logger.warning(error_msg)
                
                fallback = self._create_fallback_node(node, x_pos)
                self.openjiuwen_nodes.append(fallback)
                self.node_id_map[node_name] = fallback["id"]
                x_pos += 460

    def _convert_node(self, n8n_node: Dict, x_pos: int) -> Optional[Dict]:
        """Convert single n8n node to OpenJiuwen format."""
        node_type = n8n_node.get("type", "")
        node_name = n8n_node.get("name", "")
        
        # Determine OpenJiuwen component type
        if node_type in self.N8N_TO_OPENJIUWEN:
            component_type = self.N8N_TO_OPENJIUWEN[node_type]
        elif self._is_app_node(node_type):
            component_type = ComponentType.COMPONENT_TYPE_PLUGIN
        else:
            component_type = ComponentType.COMPONENT_TYPE_CODE
            self.report.add_unsupported(
                node_name, node_type,
                "No direct mapping exists",
                f"Converted to Code (type {ComponentType.COMPONENT_TYPE_CODE})"
            )
        
        # Generate sequential ID
        type_prefix = self._get_type_prefix(component_type)
        node_id = self.id_gen.next_id(type_prefix)
        
        # Convert based on type
        if component_type == ComponentType.COMPONENT_TYPE_LLM:
            return self._convert_llm_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_IF:
            return self._convert_if_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_LOOP:
            return self._convert_loop_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_CODE:
            return self._convert_code_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_PLUGIN:
            return self._convert_plugin_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            return self._convert_merge_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_SUB_WORKFLOW:
            return self._convert_workflow_node(n8n_node, node_id, x_pos)
        else:
            return self._create_fallback_node(n8n_node, x_pos)

    @staticmethod
    def _get_type_prefix(component_type: ComponentType) -> str:
        """Get ID prefix for component type."""
        prefixes = {
            ComponentType.COMPONENT_TYPE_START: "start",
            ComponentType.COMPONENT_TYPE_END: "end",
            ComponentType.COMPONENT_TYPE_LLM: "llm",
            ComponentType.COMPONENT_TYPE_CODE: "code",
            ComponentType.COMPONENT_TYPE_IF: "selector",
            ComponentType.COMPONENT_TYPE_LOOP: "loop",
            ComponentType.COMPONENT_TYPE_PLUGIN: "plugin",
            ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: "merge",
            ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: "workflow",
        }
        return prefixes.get(component_type, "node")

    # =========================================================================
    # LLM NODE CONVERSION
    # =========================================================================

    def _convert_llm_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Agent/LLM node to OpenJiuwen LLM component."""
        params = n8n_node.get("parameters", {})
        node_name = n8n_node.get("name", "")
        
        # Extract system prompt from various possible locations
        system_prompt = ""
        if params.get("options", {}).get("systemMessage"):
            system_prompt = params["options"]["systemMessage"]
        elif params.get("systemMessage"):
            system_prompt = params["systemMessage"]
        
        # Extract user prompt
        user_prompt = ""
        if params.get("text"):
            user_prompt = params["text"]
        elif params.get("promptType") == "define" and params.get("text"):
            user_prompt = params["text"]
        
        # Convert expressions with field mapping
        system_prompt = self._convert_expression_with_mapping(system_prompt)
        user_prompt = self._convert_expression_with_mapping(user_prompt)
        
        # Build default prompt from field map if no explicit prompt
        if not user_prompt and self.field_name_map:
            prompt_parts = [f"{{{{{name}}}}}" for name in self.field_name_map.values()]
            user_prompt = " ".join(prompt_parts)
        elif not user_prompt:
            user_prompt = "{{input}}"
        
        # Get model config from connected AI sub-node
        model_config = self._find_connected_model(node_name)
        
        # Extract template variables and build inputParameters.
        # Each {{var}} in the prompt needs a ref to the node that provides it.
        # Priority: immediate data-predecessor's declared output properties,
        #           falling back to start node for vars found there.
        template_vars = re.findall(r'\{\{(\w+)\}\}', user_prompt)
        input_parameters = {}

        pred_id = self._find_data_predecessor_id(node_name)
        pred_output_field = self._get_primary_output_field(pred_id) if pred_id else ""

        # Build a set of field names declared directly on the predecessor's outputs
        pred_direct_fields: set = set()
        if pred_id:
            pred_node = next((n for n in self.openjiuwen_nodes if n["id"] == pred_id), None)
            if pred_node:
                props = pred_node.get("data", {}).get("outputs", {}).get("properties", {})
                pred_direct_fields = set(props.keys())

        for idx, var_name in enumerate(template_vars):
            if var_name in pred_direct_fields and pred_id:
                # Predecessor declares this field directly — ref it by name
                content = [pred_id, var_name]
            elif pred_id and pred_output_field:
                # Predecessor is a code/plugin/etc. — pass its whole output
                content = [pred_id, pred_output_field]
            else:
                # No predecessor found — fall back to start node
                content = [self.start_node_id, var_name]

            param: Dict[str, Any] = {"type": "ref", "content": content}
            if idx == 0:
                param["extra"] = {"index": 0}
            input_parameters[var_name] = param
        
        # Check for connected tools
        tools = self._find_connected_tools(node_name)
        if tools:
            self.report.add_warning(
                f"Agent '{node_name}' has {len(tools)} tools: {', '.join(tools)}"
            )
        
        llm_count = self.id_gen.counters.get("llm", 1)
        
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_LLM),
            "meta": {"position": {"x": x_pos, "y": 0}},
            "data": {
                "title": self.get_title("llm", llm_count),
                "inputs": {
                    "llmParam": {
                        "systemPrompt": {
                            "type": "template",
                            "content": system_prompt
                        },
                        "prompt": {
                            "type": "template",
                            "content": user_prompt
                        },
                        "model": model_config
                    },
                    "inputParameters": input_parameters
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "extra": {"index": 1}
                        }
                    },
                    "required": ["output"]
                }
            }
        }

    def _find_connected_model(self, agent_name: str) -> Dict:
        """Find model configuration from connected AI sub-node."""
        # Search through connections for AI model sub-nodes
        for source_name, conn_types in self.n8n_connections.items():
            source_node = self.nodes_by_name.get(source_name)
            if not source_node:
                continue
            
            source_type = source_node.get("type", "")
            if source_type in AI_SUBNODES:
                conn_info = AI_SUBNODES[source_type]
                if conn_info[0] == "ai_languageModel":
                    # Check if this model connects to our agent
                    for conn_list in conn_types.get("ai_languageModel", []):
                        for conn in conn_list:
                            if conn.get("node") == agent_name:
                                params = source_node.get("parameters", {})
                                model_name = params.get("model", params.get("modelId", ""))
                                return self._map_model_to_jiuwen(model_name, conn_info[1])
        
        # Also check all nodes for AI model sub-nodes (they may not be in connections)
        for source_name, node in self.nodes_by_name.items():
            source_type = node.get("type", "")
            if source_type in AI_SUBNODES:
                conn_info = AI_SUBNODES[source_type]
                if conn_info[0] == "ai_languageModel":
                    params = node.get("parameters", {})
                    model_name = params.get("model", params.get("modelId", ""))
                    return self._map_model_to_jiuwen(model_name, conn_info[1])
        
        # Default model
        return {"id": "1", "name": "deepseek", "type": "deepseek-chat"}

    @staticmethod
    def _map_model_to_jiuwen(model_name: str, provider: str) -> Dict:
        """Map n8n model name to Jiuwen model configuration."""
        model_lower = model_name.lower()
        
        if "qwen" in model_lower:
            return {"id": "1", "name": "Qwen", "type": model_name}
        elif "gpt-4" in model_lower:
            return {"id": "1", "name": "openai", "type": model_name}
        elif "gpt-3" in model_lower:
            return {"id": "1", "name": "openai", "type": model_name}
        elif "claude" in model_lower:
            return {"id": "1", "name": "anthropic", "type": model_name}
        elif "deepseek" in model_lower:
            return {"id": "1", "name": "deepseek", "type": "deepseek-chat"}
        elif "gemini" in model_lower:
            return {"id": "1", "name": "gemini", "type": model_name}
        elif "llama" in model_lower:
            return {"id": "1", "name": "ollama", "type": model_name}
        elif provider == "ollama":
            return {"id": "1", "name": "ollama", "type": model_name}
        else:
            return {
                "id": "1", 
                "name": provider or "deepseek", 
                "type": model_name or "deepseek-chat"
            }

    def _find_connected_tools(self, agent_name: str) -> List[str]:
        """Find tools connected to agent."""
        tools = []
        
        for source_name, conn_types in self.n8n_connections.items():
            source_node = self.nodes_by_name.get(source_name)
            if not source_node:
                continue
            
            source_type = source_node.get("type", "")
            if source_type in AI_SUBNODES:
                conn_info = AI_SUBNODES[source_type]
                if conn_info[0] == "ai_tool":
                    for conn_list in conn_types.get("ai_tool", []):
                        for conn in conn_list:
                            if conn.get("node") == agent_name:
                                tools.append(f"{source_name} ({conn_info[1]})")
        
        return tools
    
    # =========================================================================
    # CROSS-REFERENCE HELPERS  ($('NodeName').first().json  patterns)
    # =========================================================================

    @staticmethod
    def _extract_js_cross_refs(code: str) -> List[Tuple[str, str]]:
        """
        Scan JS code for  $('NodeName').first().json  (or .all()) references.

        Returns a list of (variable_name, n8n_node_name) pairs where
        variable_name is the JS variable the result was assigned to
        (or '' when used inline), e.g.:

            const prev = $('Calculate Order').first().json;
            → ('prev', 'Calculate Order')
        """
        results: List[Tuple[str, str]] = []

        # Assignment pattern: const/let/var varName = $('NodeName').first().json
        assign_pat = re.compile(
            r"""(?:const|let|var)\s+(\w+)\s*=\s*\$\(['"]([^'"]+)['"]\)"""
            r"""\.(?:first|last)\(\)\.json\b"""
        )
        for m in assign_pat.finditer(code):
            results.append((m.group(1), m.group(2)))

        # Inline (unassigned) pattern: $('NodeName').first().json
        inline_pat = re.compile(
            r"""\$\(['"]([^'"]+)['"]\)\.(?:first|last)\(\)\.json\b"""
        )
        assigned_nodes = {node for _, node in results}
        for m in inline_pat.finditer(code):
            node_name = m.group(1)
            if node_name not in assigned_nodes:
                results.append(('', node_name))

        return results

    def _get_jiuwen_output_fields(self, n8n_node_name: str) -> List[str]:
        """
        Return the list of output field names that a *converted* node exposes.
        Looks up the already-converted OpenJiuwen node by the n8n node name.
        """
        jiuwen_id = self.node_id_map.get(n8n_node_name)
        if not jiuwen_id:
            return []
        node = next((n for n in self.openjiuwen_nodes if n["id"] == jiuwen_id), None)
        if not node:
            return []
        props = node.get("data", {}).get("outputs", {}).get("properties", {})
        return list(props.keys())

    def _find_predecessor_id(self, n8n_node_name: str) -> Optional[str]:
        """Find the Jiuwen ID of the main-connection predecessor of a given n8n node."""
        for source_name, conn_types in self.n8n_connections.items():
            for conn_type, target_lists in conn_types.items():
                if conn_type not in ["main"]:
                    continue
                for target_list in target_lists:
                    for target in target_list:
                        if target.get("node") == n8n_node_name:
                            return self.node_id_map.get(source_name)
        return None

    def _find_data_predecessor_id(self, n8n_node_name: str) -> Optional[str]:
        """
        Find the Jiuwen ID of the nearest predecessor that actually holds output data.

        Selector (IF) nodes route execution but don't produce new data fields —
        they pass the upstream payload through.  When a code/set node sits directly
        after a selector, its inputParameters must reference the node *before* the
        selector (the real data source), not the selector itself.
        """
        pred_id = self._find_predecessor_id(n8n_node_name)
        if not pred_id:
            return None

        # If the predecessor is a selector, look one level further back
        pred_jiuwen_node = next(
            (n for n in self.openjiuwen_nodes if n["id"] == pred_id), None
        )
        if pred_jiuwen_node and int(pred_jiuwen_node.get("type", 0)) == ComponentType.COMPONENT_TYPE_IF:
            # Find the n8n name that maps to this selector ID
            pred_n8n_name = next(
                (name for name, jid in self.node_id_map.items() if jid == pred_id), None
            )
            if pred_n8n_name:
                upstream_id = self._find_predecessor_id(pred_n8n_name)
                if upstream_id:
                    return upstream_id

        return pred_id

    def _get_primary_output_field(self, jiuwen_node_id: str) -> str:
        """
        Return the name of the primary output field declared by a converted node.

        Each node type exposes a different top-level output property:
          LLM          → "output"
          Plugin       → "data"
          Merge        → "merged"
          Start        → first declared property (usually "input" or first form field)
          Code / Set / Workflow / Fallback → "result"
          Selector     → no data output (routes only) → ""
        """
        node = next((n for n in self.openjiuwen_nodes if n["id"] == jiuwen_node_id), None)
        if not node:
            return "result"
        node_type = int(node.get("type", 0))
        if node_type == ComponentType.COMPONENT_TYPE_LLM:
            return "output"
        if node_type == ComponentType.COMPONENT_TYPE_PLUGIN:
            return "data"
        if node_type == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            return "merged"
        if node_type == ComponentType.COMPONENT_TYPE_IF:
            return ""  # selector has no data output; caller must skip up one level
        if node_type == ComponentType.COMPONENT_TYPE_START:
            props = node.get("data", {}).get("outputs", {}).get("properties", {})
            # If Start has no declared outputs (e.g. manualTrigger), return ""
            # so callers know there is nothing to reference.
            return next(iter(props), "")
        # CODE, SUB_WORKFLOW, fallback
        return "result"

    def _build_predecessor_input_ref(self, n8n_node_name: str,
                                     param_key: str = "input") -> Dict:
        """
        Build a single inputParameters entry pointing to the predecessor's
        primary output field.  Returns {} when no predecessor is found.

        Example result:
            {"input": {"type": "ref", "content": ["code_1", "result"],
                       "extra": {"index": 0}}}
        """
        pred_id = self._find_data_predecessor_id(n8n_node_name)
        if not pred_id:
            return {}
        output_field = self._get_primary_output_field(pred_id)
        # Empty string means the predecessor has no declared outputs (e.g. manual
        # trigger Start node, or a selector) — nothing to reference.
        if not output_field:
            return {}
        return {
            param_key: {
                "type": "ref",
                "content": [pred_id, output_field],
                "extra": {"index": 0}
            }
        }

    # =========================================================================
    # IF/SELECTOR NODE CONVERSION
    # =========================================================================

    # -------------------------------------------------------------------------
    # Operator mapping: n8n operator objects → OpenJiuwen operator strings
    # n8n stores operators as {"type": "string"|"number"|"boolean", "operation": "..."}
    # -------------------------------------------------------------------------
    N8N_OPERATOR_MAP: Dict[str, str] = {
        # generic equality
        "equals": "==",
        "notEquals": "!=",
        "equal": "==",
        "notEqual": "!=",
        # boolean
        "true": "==",   # paired with right=true
        "false": "==",   # paired with right=false
        "exists": "!=",   # paired with right=null
        "notExists": "==",   # paired with right=null
        # numeric
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "smaller": "<",
        "smallerEqual": "<=",
        "larger": ">",
        "largerEqual": ">=",
        # string
        "contains": "contains",
        "notContains": "not_contains",
        "startsWith": "starts_with",
        "endsWith": "ends_with",
        "regex": "regex",
        "empty": "==",
        "notEmpty": "!=",
    }

    def _map_n8n_operator(self, n8n_op: Any) -> Tuple[str, Any]:
        """
        Convert an n8n operator to (openjiuwen_operator_str, adjusted_right_value).

        n8n operators are objects like:
            {"type": "boolean", "operation": "true"}
            {"type": "string",  "operation": "equals"}
            {"type": "number",  "operation": "gt"}

        Returns a tuple (operator_str, right_override) where right_override is
        None unless the operation implies a specific right-hand value (e.g.
        "true" implies right=True, "false" implies right=False).
        """
        if isinstance(n8n_op, str):
            return self.N8N_OPERATOR_MAP.get(n8n_op, "=="), None

        if isinstance(n8n_op, dict):
            operation = n8n_op.get("operation", "equals")
            op_type = n8n_op.get("type", "string")

            mapped = self.N8N_OPERATOR_MAP.get(operation, "==")

            # Unary boolean checks — right side is implied by the operation
            if operation == "true":
                return mapped, True
            if operation == "false":
                return mapped, False
            if operation in ("exists", "notExists"):
                return mapped, None   # right=null / not-null

            return mapped, None

        return "==", None

    def _convert_if_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n IF/Switch to OpenJiuwen Selector component."""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        node_name = n8n_node.get("name", "")

        # Resolve actual predecessor so conditions can reference real data
        predecessor_id = self._find_predecessor_id(node_name)

        # ── Parse ALL n8n conditions for branch 0 ────────────────────────────
        n8n_conditions = params.get("conditions", {}).get("conditions", [])
        jiuwen_conditions = []
        input_parameters: Dict[str, Any] = {}

        for idx, cond in enumerate(n8n_conditions):
            # Left side: parse field name from $json expression
            left_val = str(cond.get("leftValue", ""))
            m = re.match(r'=?\{\{\s*\$json\.(\w+)\s*\}\}', left_val)
            condition_field = m.group(1) if m else f"value_{idx}"

            # Map the operator
            n8n_op = cond.get("operator", {})
            jiuwen_op, right_override = self._map_n8n_operator(n8n_op)

            # Right side value
            if right_override is not None:
                right_content = right_override
            else:
                right_content = cond.get("rightValue", "")

            # Infer schema type for the right-side constant
            if isinstance(right_content, bool):
                right_schema = {"type": "boolean"}
            elif isinstance(right_content, (int, float)):
                right_schema = {"type": "number"}
            elif right_content is None:
                right_schema = {"type": "null"}
            else:
                right_schema = {"type": "string"}

            # Find the best source node for this condition field.
            # The immediate predecessor may be a Code node whose outputs were
            # enriched via spread resolution — prefer that.  If the field is NOT
            # declared there, walk back through cross-ref nodes to find it.
            ref_node_id = self._find_condition_field_source(node_name, condition_field, predecessor_id)

            # Register this field in inputParameters
            if ref_node_id:
                input_parameters[condition_field] = {
                    "type": "ref",
                    "content": [ref_node_id, condition_field],
                    "extra": {"index": idx}
                }

            jiuwen_conditions.append({
                "left": {
                    "type": "ref",
                    "content": [ref_node_id or "", condition_field]
                },
                "operator": jiuwen_op,
                "right": {
                    "type": "constant",
                    "content": right_content,
                    "schema": right_schema
                }
            })

        # Ensure at least one (placeholder) condition so the schema is valid
        if not jiuwen_conditions:
            jiuwen_conditions.append({
                "left": {"type": "ref", "content": [predecessor_id or "", "value"]},
                "operator": "==",
                "right": {"type": "constant", "content": True,
                             "schema": {"type": "boolean"}}
            })

        branch_id_0 = f"branch_{uuid.uuid4().hex[:5]}"
        branch_id_1 = f"branch_{uuid.uuid4().hex[:5]}"

        combinator = params.get("conditions", {}).get("combinator", "and")
        logic = 1 if combinator == "or" else 2  # 1=OR, 2=AND

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_IF),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": node_name or self.get_title("selector"),
                "inputs": {
                    "inputParameters": input_parameters
                },
                "branches": [
                    {
                        "conditions": jiuwen_conditions,
                        "logic": logic,
                        "branchId": branch_id_0
                    },
                    {
                        "conditions": [],
                        "logic": logic,
                        "branchId": branch_id_1
                    }
                ]
            }
        }

    def _find_condition_field_source(
        self,
        if_node_name: str,
        condition_field: str,
        immediate_predecessor_id: Optional[str],
    ) -> Optional[str]:
        """
        Find the best OpenJiuwen node ID that exposes *condition_field*.

        Search order:
        1. Immediate predecessor — check its declared output properties.
        2. Any code node in the predecessor chain whose outputs were enriched
           by spread/cross-ref resolution (the field was injected from a
           cross-referenced node but lives on the Code node's output schema).
        3. Fallback to immediate predecessor regardless.
        """
        if not immediate_predecessor_id:
            return None

        # 1. Does the immediate predecessor declare the field?
        pred_node = next(
            (n for n in self.openjiuwen_nodes if n["id"] == immediate_predecessor_id), None
        )
        if pred_node:
            props = pred_node.get("data", {}).get("outputs", {}).get("properties", {})
            if condition_field in props:
                return immediate_predecessor_id

        # 2. Walk back one more level (in case predecessor is a selector pass-through)
        pred_n8n_name = next(
            (name for name, jid in self.node_id_map.items() if jid == immediate_predecessor_id),
            None,
        )
        if pred_n8n_name:
            upstream_id = self._find_predecessor_id(pred_n8n_name)
            if upstream_id:
                up_node = next(
                    (n for n in self.openjiuwen_nodes if n["id"] == upstream_id), None
                )
                if up_node:
                    props = up_node.get("data", {}).get("outputs", {}).get("properties", {})
                    if condition_field in props:
                        return upstream_id

        # 3. Fallback — return immediate predecessor so the schema at least has a ref
        return immediate_predecessor_id

    # =========================================================================
    # LOOP NODE CONVERSION
    # =========================================================================

    def _convert_loop_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Loop/SplitInBatches to OpenJiuwen Loop component."""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        node_name = n8n_node.get("name", "")

        batch_size = params.get("batchSize", 10)

        # Create internal block IDs
        block_start_id = f"block_start_{uuid.uuid4().hex[:5]}"
        block_end_id = f"block_end_{uuid.uuid4().hex[:5]}"

        # Resolve predecessor to build proper refs
        pred_id = self._find_data_predecessor_id(node_name)
        pred_output_field = self._get_primary_output_field(pred_id) if pred_id else "result"

        input_parameters = self._build_predecessor_input_ref(node_name)
        loop_param = {
            "type": "ref",
            "content": [pred_id, pred_output_field] if pred_id else []
        }

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_LOOP),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": n8n_node.get("name", self.get_title("loop")),
                "inputs": {
                    "inputParameters": input_parameters,
                    "loopParam": loop_param,
                    "batchSize": batch_size
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "results": {"type": "array", "extra": {"index": 1}}
                    }
                }
            },
            "blocks": [
                {
                    "id": block_start_id,
                    "type": str(ComponentType.COMPONENT_TYPE_BLOCK_START),
                    "data": {"title": self.get_title("block_start")}
                },
                {
                    "id": block_end_id,
                    "type": str(ComponentType.COMPONENT_TYPE_BLOCK_END),
                    "data": {"title": self.get_title("block_end")}
                }
            ],
            "edges": [
                {"sourceNodeID": block_start_id, "targetNodeID": block_end_id}
            ]
        }
    
    def _is_passthrough_set_node(self, n8n_node: Dict) -> bool:
        """
        Return True if the Set node is a pure passthrough:
        every assignment value is a simple {{ $json.X }} reference
        with no transformation logic.
        """
        if n8n_node.get("type") != "n8n-nodes-base.set":
            return False

        params = n8n_node.get("parameters", {})
        assignments = self._extract_set_assignments(params)

        if not assignments:
            return False

        for assignment in assignments:
            value = assignment.get("value", "")
            if not isinstance(value, str):
                return False
            # Strip leading '=' (n8n expression marker) then check for pure $json.X
            stripped = value.lstrip("=").strip()
            if not re.match(r'^\{\{\s*\$json\.\w+\s*\}\}$', stripped):
                return False

        return True
    
    @staticmethod
    def _normalize_python_main(code: str) -> str:
        """
        Ensure Python code has a 'def main(args):' entry point.

        Cases handled:
        - Code already has def main(  → leave untouched
        - Code has a different top-level def → rename it to main(args)
        - Code has no def at all → wrap entire code in def main(args):
        """
        # Already correct
        if re.search(r'^\s*def\s+main\s*\(', code, re.MULTILINE):
            return code

        # Find the first top-level function definition
        first_def = re.search(r'^(def\s+\w+\s*\([^)]*\)\s*:)', code, re.MULTILINE)
        if first_def:
            # Replace only that first function's signature with def main(args):
            return code[:first_def.start()] + \
                re.sub(
                    r'^def\s+\w+\s*\([^)]*\)\s*:',
                    'def main(args):',
                    code[first_def.start():],
                    count=1,
                    flags=re.MULTILINE
                )

        # No function at all – wrap the whole body
        indented = "\n".join("    " + line for line in code.splitlines())
        return f"def main(args):\n{indented}"

    @staticmethod
    def _extract_js_object_content(code: str, start_keyword: str) -> Optional[str]:
        """
        Find the first ``{...}`` block that appears after *start_keyword* in *code*
        and return its inner content.

        Uses brace-depth counting so it is not confused by:
        - Nested objects  { a: { b: 1 } }
        - Template literals  `${expr}`  ← the } inside these is skipped
        - Single- and double-quoted strings

        Returns None when no matching block is found.
        """
        idx = code.find(start_keyword)
        if idx == -1:
            return None
        idx += len(start_keyword)

        # Skip whitespace/newlines to find the opening brace
        while idx < len(code) and code[idx] in ' \t\r\n':
            idx += 1
        if idx >= len(code) or code[idx] != '{':
            return None

        depth = 0
        in_single = False   # inside '...'
        in_double = False   # inside "..."
        in_template = False # inside `...`
        template_depth = 0  # ${ nesting inside template
        i = idx
        start = idx + 1     # content starts after opening {
        while i < len(code):
            ch = code[i]
            if in_single:
                if ch == '\\':
                    i += 2
                    continue
                if ch == "'":
                    in_single = False
            elif in_double:
                if ch == '\\':
                    i += 2
                    continue
                if ch == '"':
                    in_double = False
            elif in_template:
                if ch == '\\':
                    i += 2
                    continue
                if ch == '$' and i + 1 < len(code) and code[i + 1] == '{':
                    template_depth += 1
                    i += 2
                    continue
                if template_depth > 0 and ch == '}':
                    template_depth -= 1
                    i += 1
                    continue
                if ch == '`':
                    in_template = False
            else:
                if ch == "'":
                    in_single = True
                elif ch == '"':
                    in_double = True
                elif ch == '`':
                    in_template = True
                elif ch == '{':
                    depth += 1
                elif ch == '}':
                    if depth == 0:
                        # Found the closing brace of our block
                        return code[start:i]
                    depth -= 1
            i += 1
        return None

    def _extract_return_field_names(self, n8n_node, language):
        """
        Extract declared output field names from a code/set node.

        For Set nodes   → reads directly from assignments parameters.
        For JS nodes    → parses the return object using brace-depth counting
                          (handles template literals like ``${expr}`` correctly).
        For Python nodes → scans result["field"] = ... and return {"key": ...}.
        """
        node_type = n8n_node.get('type', '')
        params = n8n_node.get('parameters', {})

        # ── Set node ────────────────────────────────────────────────────────
        if node_type == 'n8n-nodes-base.set':
            assignments = self._extract_set_assignments(params)
            return [a.get('name', '') for a in assignments if a.get('name')]

        # ── JavaScript ──────────────────────────────────────────────────────
        if language == 'javascript':
            original = params.get('jsCode', params.get('functionCode', params.get('code', '')))
            if original:
                # Build a map of varName → [fields from cross-referenced node]
                # so that spread operators like  ...prev  can be resolved.
                cross_refs = self._extract_js_cross_refs(original)
                spread_fields: List[str] = []
                var_to_fields: Dict[str, List[str]] = {}
                for var_name, ref_node_name in cross_refs:
                    ref_fields = self._get_jiuwen_output_fields(ref_node_name)
                    if var_name:
                        var_to_fields[var_name] = ref_fields
                    spread_fields.extend(ref_fields)

                # Pattern A: return [{ json: { ... } }]
                # Find the inner json object content using brace-depth parser
                content = None
                # Locate 'json:' or 'json :' after a 'return'
                for kw in ('json:', 'json :'):
                    content = self._extract_js_object_content(original, kw)
                    if content:
                        break

                if content:
                    # Extract top-level field names only (depth=0 inside content).
                    # A top-level key is: identifier followed by , or : or newline
                    # (shorthand  `field,`  or  key-value  `field: expr,`)
                    fields = re.findall(r'\b([A-Za-z_]\w*)\b\s*[,:\n]', content)
                    skip = {'json', 'true', 'false', 'null', 'undefined',
                            'const', 'let', 'var', 'return', 'function'}
                    cleaned = [f for f in fields
                               if f and not f.startswith('_') and f not in skip]

                    # Resolve spread operators: ...varName → inject that var's fields
                    for spread_var in re.findall(r'\.\.\.(\w+)', content):
                        if spread_var in var_to_fields:
                            for sf in var_to_fields[spread_var]:
                                if sf not in cleaned:
                                    cleaned.append(sf)
                        else:
                            # Unknown var — add all cross-ref fields as fallback
                            for sf in spread_fields:
                                if sf not in cleaned:
                                    cleaned.append(sf)

                    if cleaned:
                        return list(dict.fromkeys(cleaned))

                # Pattern B: plain return { key: val, ... }
                content = self._extract_js_object_content(original, 'return')
                if content:
                    fields = re.findall(r'\b([A-Za-z_]\w*)\s*:', content)
                    cleaned = [f for f in fields
                               if f and not f.startswith('_') and f not in {'json'}]
                    # Resolve spreads here too
                    for spread_var in re.findall(r'\.\.\.(\w+)', content):
                        if spread_var in var_to_fields:
                            for sf in var_to_fields[spread_var]:
                                if sf not in cleaned:
                                    cleaned.append(sf)
                        else:
                            for sf in spread_fields:
                                if sf not in cleaned:
                                    cleaned.append(sf)
                    if cleaned:
                        return list(dict.fromkeys(cleaned))

        # ── Python ──────────────────────────────────────────────────────────
        if language == 'python':
            original = params.get('pythonCode', '')
            if original:
                # result["field"] = ... assignments (generated by _convert_set_to_code)
                set_fields = re.findall(r'result\[[\'"](\w+)[\'"]\]\s*=', original)
                if set_fields:
                    return list(dict.fromkeys(set_fields))
                # return {"key": val, ...}
                m = re.search(r'return\s*\{([^}]+)\}', original, re.DOTALL)
                if m:
                    fields = re.findall(r'[\'"](\w+)[\'"]', m.group(1))
                    if fields:
                        return list(dict.fromkeys(fields))

        return []

    # N8N type string → JSON Schema type string
    N8N_TYPE_TO_JSON_SCHEMA: Dict[str, str] = {
        'string': 'string',
        'number': 'number',
        'boolean': 'boolean',
        'object': 'object',
        'array': 'array',
        'bool': 'boolean',
        'int': 'number',
        'float': 'number',
    }

    def _extract_return_field_types(self, n8n_node: Dict, language: str) -> Dict[str, str]:
        """
        Return a mapping of field_name → JSON-schema type for every field
        this node outputs.

        For Set nodes we read the assignment type directly from the n8n params.
        For JS code nodes we infer from the right-hand value in the return object.
        Falls back to 'string' for anything we cannot determine.
        """
        node_type = n8n_node.get('type', '')
        params = n8n_node.get('parameters', {})
        result: Dict[str, str] = {}

        # ── Set node ─────────────────────────────────────────────────────────
        if node_type == 'n8n-nodes-base.set':
            assignments = self._extract_set_assignments(params)
            for a in assignments:
                name = a.get('name', '')
                raw_type = str(a.get('type', 'string')).lower()
                if name:
                    result[name] = self.N8N_TYPE_TO_JSON_SCHEMA.get(raw_type, 'string')
            return result

        # ── JavaScript ───────────────────────────────────────────────────────
        if language == 'javascript':
            code = params.get('jsCode', params.get('functionCode', params.get('code', '')))
            if not code:
                return result

            # Find the json: { ... } return block
            content = None
            for kw in ('json:', 'json :'):
                content = self._extract_js_object_content(code, kw)
                if content:
                    break
            if not content:
                content = self._extract_js_object_content(code, 'return')
            if not content:
                return result

            # For each  key: <literal>  pair try to infer type from the literal
            for m in re.finditer(
                r'([A-Za-z_]\w*)\s*:\s*([^\n,}]+)',
                content
            ):
                fname = m.group(1)
                val_str = m.group(2).strip().rstrip(',').strip()
                if fname.startswith('_') or fname in {
                    'json', 'true', 'false', 'null', 'undefined',
                    'const', 'let', 'var', 'return', 'function'
                }:
                    continue

                # Infer type from value literal
                if val_str in ('true', 'false'):
                    ftype = 'boolean'
                elif re.match(r'^-?\d+(\.\d+)?$', val_str):
                    ftype = 'number'
                elif val_str.startswith(('"', "'", '`')):
                    ftype = 'string'
                elif val_str.startswith('['):
                    ftype = 'array'
                elif val_str.startswith('{'):
                    ftype = 'object'
                else:
                    # Variable reference or expression — look up from cross-refs
                    cross_refs = self._extract_js_cross_refs(code)
                    var_fields: Dict[str, str] = {}
                    for var_name, ref_node in cross_refs:
                        ref_id = self.node_id_map.get(ref_node)
                        if not ref_id:
                            continue
                        ref_node_obj = next(
                            (n for n in self.openjiuwen_nodes if n["id"] == ref_id), None
                        )
                        if ref_node_obj:
                            props = (
                                ref_node_obj.get("data", {})
                                .get("outputs", {})
                                .get("properties", {})
                            )
                            for pname, pval in props.items():
                                var_fields[pname] = pval.get("type", "string")
                    ftype = var_fields.get(fname, 'string')

                result[fname] = ftype

            return result

        # ── Python ───────────────────────────────────────────────────────────
        # For Python we don't try to infer — default to string for all fields
        return result

    @staticmethod
    def _build_code_outputs(extra_fields, field_types=None):
        """
        Build outputs schema: always 'result' plus each individual field.

        field_types: optional dict of field_name -> JSON-schema type string
                     (e.g. {'customerName': 'string', 'quantity': 'number'}).
                     Defaults to 'string' for any unknown field — avoids the
                     "expected dict, got str" error caused by declaring primitives
                     as type 'object'.
        """
        if field_types is None:
            field_types = {}

        properties = {
            'result': {'type': 'object', 'description': '代码执行结果', 'extra': {'index': 0}}
        }
        for idx, ffield in enumerate(extra_fields, start=1):
            if ffield != 'result':
                ftype = field_types.get(ffield, 'string')
                properties[ffield] = {'type': ftype, 'extra': {'index': idx}}
        required = ['result'] + [f for f in extra_fields if f != 'result']
        return {'type': 'object', 'properties': properties, 'required': required}

    # =========================================================================
    # CODE NODE CONVERSION
    # =========================================================================

    def _convert_code_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Code/Function/Set to OpenJiuwen Code component."""
        node_type = n8n_node.get("type", "")
        node_name = n8n_node.get("name", "")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        
        # Determine language and extract code
        language = "javascript"
        code = ""
        
        if node_type == "n8n-nodes-base.code":
            lang_param = params.get("language", "javaScript").lower()
            if lang_param in ["javascript", "js"]:
                language = "javascript"
                code = params.get("jsCode", "")
            else:
                language = "python"
                code = params.get("pythonCode", "")
        elif node_type in ["n8n-nodes-base.function", "n8n-nodes-base.functionItem"]:
            language = "javascript"
            code = params.get("functionCode", "") or params.get("code", "")
        elif node_type == "n8n-nodes-base.set":
            # Convert Set node to Python code with actual implementation
            language = "python"
            code = self._convert_set_to_code(n8n_node)
        elif node_type == "n8n-nodes-base.readWriteFile":
            # Convert Read/Write File node to Python code
            language = "python"
            code = self._convert_read_write_file_to_code(n8n_node)
        else:
            # Fallback for other node types
            language = "python"
            code = self._create_fallback_code(n8n_node)
        
        if not code:
            if language == "javascript":
                code = "function main(args) {\n  return { result: args.params };\n}"
            else:
                code = "def main(args):\n    return {'result': args.params}"
        elif language == "javascript":
            # Wrap raw n8n JS code in main(args).
            # The original code is run in an IIFE so its `return` doesn't exit
            # main() directly — we can post-process the value.
            # A minimal n8n-compat shim makes $input.first().json and friends work.
            # Cross-references via $('NodeName').first().json are resolved from
            # extra input parameters named  cross_ref_<safe_node_name>.
            indented = "\n".join("    " + line for line in code.splitlines())

            # Build cross-ref node name → safe param key mapping from the code
            cross_refs = self._extract_js_cross_refs(code)
            cross_ref_entries = ""
            for var_name, ref_node_name in cross_refs:
                safe_key = "cross_ref_" + re.sub(r'[^a-zA-Z0-9_]', '_', ref_node_name)
                cross_ref_entries += (
                    f'    _crossRefMap["{ref_node_name}"] = '
                    f'(params.{safe_key} || params["{safe_key}"] || {{}});\n'
                )

            code = (
                "function main(args) {\n"
                "// n8n-compat shim\n"
                "  const params = (args && args.params) ? args.params : {};\n"
                "  const _upstream = params.input || params || {};\n"
                "// Cross-reference map: node name -> data from that node\n"
                "  const _crossRefMap = {};\n"
                f"{cross_ref_entries}"
                "  const $input = {\n"
                "    first: function() { return { json: _upstream }; },\n"
                "    all: function() { return [{ json: _upstream }]; },\n"
                "    item: { json: _upstream },\n"
                "  };\n"
                "// $('NodeName') cross-reference support\n"
                "  function $(nodeName) {\n"
                "    const data = _crossRefMap[nodeName] || _upstream;\n"
                "    return {\n"
                "      first: function() { return { json: data }; },\n"
                "      last: function() { return { json: data }; },\n"
                "      all: function() { return [{ json: data }]; },\n"
                "      item: { json: data },\n"
                "    };\n"
                "  }\n"
                "// Run original n8n code in an IIFE and capture return value\n"
                "  const _n8nResult = (function() {\n"
                + indented + "\n"
                "  })();\n"
                "// Flatten n8n return format [{json:{...}}] -> {result:{...}, ...fields}\n"
                "  const _data = (Array.isArray(_n8nResult) && _n8nResult[0] && _n8nResult[0].json)\n"
                "    ? _n8nResult[0].json\n"
                "    : (_n8nResult && typeof _n8nResult === 'object' ? _n8nResult : {});\n"
                "  const _out = Object.assign({}, _data);\n"
                "  _out.result = _data;\n"
                "  return _out;\n"
                "}"
            )
        else:
            # Ensure Python code has def main(args): as entry point
            code = self._normalize_python_main(code)

        # Node title: use the n8n node name when present so the canvas label
        # matches what the user named it in n8n.  When there is no name, fall
        # back to "code" — a UI-translatable key (the platform renders it in
        # the active language, e.g. "代码" in Chinese, "Code" in English).
        title = node_name if node_name else "code"

        # Build input parameters from referenced fields
        input_parameters = self._extract_code_input_parameters(n8n_node, code)

        # Build outputs: extract every field this node returns so selectors and
        # downstream nodes can reference them individually.
        extra_fields = self._extract_return_field_names(n8n_node, language)
        field_types = self._extract_return_field_types(n8n_node, language)
        outputs = self._build_code_outputs(extra_fields, field_types)

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_CODE),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": title,
                "inputs": {
                    "language": language,
                    "code": code,
                    "inputParameters": input_parameters,
                },
                "outputs": outputs,
                "exceptionConfig": {
                    "retryTimes": 3,
                    "timeoutSeconds": 30,
                    "processType": "break",
                    "executeStep": {"defaultStep": "0", "errorStep": "1"}
                }
            }
        }

    def _convert_set_to_code(self, n8n_node: Dict) -> str:
        """
        Convert n8n Set node to Python code with actual implementation.
        
        Handles:
        - Manual mode with assignments
        - Raw JSON mode
        - Include/exclude options
        - Expression conversion
        """
        node_name = n8n_node.get("name", "Set")
        params = n8n_node.get("parameters", {})
        
        # Determine the mode
        mode = params.get("mode", "manual")
        
        # Get options
        options = params.get("options", {})
        dot_notation = options.get("dotNotation", True)
        
        # Check for keepOnlySet option (only keep the fields we're setting)
        keep_only_set = params.get("keepOnlySet", False)
        
        # Build the code
        code_lines = [
            'def main(args):',
            f'    """',
            f'    Converted from n8n Set node: {node_name}',
            f'    Mode: {mode}',
            f'    """',
            '    # Get input data',
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}',
            '    ',
        ]
        
        if mode == "raw":
            # Raw JSON mode
            raw_json = params.get("jsonOutput", "{}")
            raw_json_converted = self._convert_expression(raw_json)
            code_lines.extend([
                '    # Raw JSON mode - parse and return JSON directly',
                '    import json',
                f'    raw_json = """{raw_json_converted}"""',
                '    try:',
                '        result = json.loads(raw_json)',
                '    except json.JSONDecodeError:',
                '        result = {"raw": raw_json}',
            ])
        else:
            # Manual mode - process assignments
            if keep_only_set:
                code_lines.append('    # Keep only the fields we set (keepOnlySet=True)')
                code_lines.append('    result = {}')
            else:
                code_lines.append('    # Start with input data and add/modify fields')
                code_lines.append('    result = dict(input_data) if isinstance(input_data, dict) else {}')
            
            code_lines.append('    ')
            
            # Get assignments - n8n can store them in different places
            assignments = self._extract_set_assignments(params)
            
            if assignments:
                code_lines.append('    # Set field values')
                
                for assignment in assignments:
                    field_name = assignment.get("name", "")
                    field_value = assignment.get("value", "")
                    field_type = assignment.get("type", "string")
                    
                    if not field_name:
                        continue
                    
                    # Convert n8n expressions to Python variable references
                    converted_value = self._convert_set_value_to_python(
                        field_value, field_type
                    )
                    
                    # Handle dot notation for nested fields
                    if dot_notation and "." in field_name:
                        code_lines.extend(
                            self._generate_nested_set_code(field_name, converted_value)
                        )
                    else:
                        # Simple field assignment
                        safe_field_name = self._make_safe_field_name(field_name)
                        code_lines.append(f'    result["{safe_field_name}"] = {converted_value}')
            else:
                code_lines.append('    # No assignments defined - pass through input')
        
        code_lines.extend([
            '    ',
            '    # Return every field individually AND as a "result" bundle so that',
            '    # downstream nodes can ref either [this_id, "result"] (whole dict)',
            '    # or [this_id, "fieldName"] (a single field) - e.g. for IF conditions.',
            '    _output = dict(result) if isinstance(result, dict) else {}',
            '    _output["result"] = result',
            '    return _output',
        ])
        
        return '\n'.join(code_lines)

    @staticmethod
    def _extract_set_assignments(params: Dict) -> List[Dict]:
        """
        Extract field assignments from Set node parameters.
        
        n8n stores assignments in different formats depending on version:
        - assignments.assignments (newer format)
        - fields.values (older format)
        - values (legacy format)
        """
        assignments = []
        
        # Try newer format: assignments.assignments
        if "assignments" in params:
            assign_data = params["assignments"]
            if isinstance(assign_data, dict) and "assignments" in assign_data:
                assignments = assign_data["assignments"]
            elif isinstance(assign_data, list):
                assignments = assign_data
        
        # Try older format: fields.values
        if not assignments and "fields" in params:
            fields_data = params["fields"]
            if isinstance(fields_data, dict) and "values" in fields_data:
                assignments = fields_data["values"]
        
        # Try legacy format: values
        if not assignments and "values" in params:
            values_data = params["values"]
            if isinstance(values_data, list):
                assignments = values_data
            elif isinstance(values_data, dict) and "values" in values_data:
                assignments = values_data["values"]
        
        # Handle single-value format (string, number, boolean, etc.)
        if not assignments:
            for value_type in ["string", "number", "boolean", "array", "object"]:
                type_key = f"{value_type}Values"
                if type_key in params:
                    type_values = params[type_key]
                    if isinstance(type_values, list):
                        for item in type_values:
                            item["type"] = value_type
                            assignments.append(item)
        
        return assignments

    def _convert_set_value_to_python(self, value: Any, field_type: str) -> str:
        """
        Convert n8n Set node value to Python code.
        
        Handles:
        - Static values (strings, numbers, booleans)
        - n8n expressions ({{ $json.field }})
        - Complex expressions
        """
        if value is None:
            return "None"
        
        # Check if it's an expression
        if isinstance(value, str):
            # Strip leading = if present (n8n expression indicator)
            if value.startswith("="):
                value = value[1:]
            
            # Check for n8n expression patterns
            if "{{" in value and "}}" in value:
                return self._convert_expression_to_python_code(value)
            
            # Handle based on field type
            if field_type == "number":
                try:
                    # Try to parse as number
                    if "." in value:
                        return str(float(value))
                    else:
                        return str(int(value))
                except ValueError:
                    return f'"{value}"'
            elif field_type == "boolean":
                if value.lower() in ["true", "1", "yes"]:
                    return "True"
                elif value.lower() in ["false", "0", "no"]:
                    return "False"
                else:
                    return f'bool("{value}")'
            elif field_type == "object":
                # Try to parse as JSON
                return f'json.loads(\'{value}\')' if value.strip().startswith('{') else f'"{value}"'
            elif field_type == "array":
                return f'json.loads(\'{value}\')' if value.strip().startswith('[') else f'["{value}"]'
            else:
                # String - escape quotes
                escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                return f'"{escaped}"'
        
        elif isinstance(value, bool):
            return "True" if value else "False"
        
        elif isinstance(value, (int, float)):
            return str(value)
        
        elif isinstance(value, dict):
            return repr(value)
        
        elif isinstance(value, list):
            return repr(value)
        
        else:
            return f'"{value}"'

    def _convert_expression_to_python_code(self, expr: str) -> str:
        """
        Convert n8n expression to Python code that can be evaluated.
        
        Examples:
        - {{ $json.fieldName }} → input_data.get("fieldName", "")
        - {{ $json["field-name"] }} → input_data.get("field-name", "")
        - {{ $('Node').item.json.field }} → input_data.get("field", "")
        - Static text with {{ $json.x }} embedded → f"Static text {input_data.get('x', '')}"
        """
        
        # Check if it's a pure expression or mixed with text
        pure_expr_match = re.match(r'^\{\{\s*(.+?)\s*\}\}$', expr.strip())
        
        if pure_expr_match:
            # Pure expression - convert to Python
            inner = pure_expr_match.group(1)
            return self._convert_inner_expression(inner)
        else:
            # Mixed expression - use f-string
            def replace_expr(match):
                inner = match.group(1).strip()
                python_expr = self._convert_inner_expression(inner)
                return '{' + python_expr + '}'
            
            converted = re.sub(r'\{\{\s*(.+?)\s*\}\}', replace_expr, expr)
            # Escape any literal braces
            converted = converted.replace('{', '{{').replace('}', '}}')
            converted = converted.replace('{{{{', '{').replace('}}}}', '}')
            return f'f"{converted}"'

    @staticmethod
    def _convert_inner_expression(inner: str) -> str:
        """Convert the inner part of an n8n expression to Python."""
        
        # $json.fieldName or $json["fieldName"]
        json_dot_match = re.match(r'\$json\.(\w+)', inner)
        if json_dot_match:
            ffield = json_dot_match.group(1)
            return f'input_data.get("{ffield}", "")'
        
        json_bracket_match = re.match(r'\$json\[(["\'])(.+?)\1\]', inner)
        if json_bracket_match:
            ffield = json_bracket_match.group(2)
            return f'input_data.get("{ffield}", "")'
        
        # $('NodeName').item.json.field
        node_ref_match = re.match(r"\$\(['\"](.+?)['\"]\)\.item\.json\.(\w+)", inner)
        if node_ref_match:
            ffield = node_ref_match.group(2)
            return f'input_data.get("{ffield}", "")'
        
        # $input.item.json.field
        input_match = re.match(r'\$input\.item\.json\.(\w+)', inner)
        if input_match:
            ffield = input_match.group(1)
            return f'input_data.get("{ffield}", "")'
        
        # Fallback - try to make it Python-safe
        return f'"{inner}"'

    @staticmethod
    def _generate_nested_set_code(field_path: str, value: str) -> List[str]:
        """
        Generate Python code to set a nested field using dot notation.
        
        Example: "address.city" = "NYC" becomes:
        if "address" not in result:
            result["address"] = {}
        result["address"]["city"] = "NYC"
        """
        parts = field_path.split(".")
        lines = []
        
        # Build nested structure
        for i in range(len(parts) - 1):
            path_so_far = '"]["'.join(parts[:i + 1])
            parent_path = '"]["'.join(parts[:i]) if i > 0 else None
            
            if parent_path:
                lines.append(f'    if "{parts[i]}" not in result["{parent_path}"]:')
                lines.append(f'        result["{parent_path}"]["{parts[i]}"] = {{}}')
            else:
                lines.append(f'    if "{parts[i]}" not in result:')
                lines.append(f'        result["{parts[i]}"] = {{}}')
        
        # Set the final value
        if len(parts) > 1:
            path = '"]["'.join(parts[:-1])
            lines.append(f'    result["{path}"]["{parts[-1]}"] = {value}')
        else:
            lines.append(f'    result["{parts[0]}"] = {value}')
        
        return lines

    @staticmethod
    def _make_safe_field_name(field_name: str) -> str:
        """Make field name safe for use as a dictionary key."""
        # Escape quotes and backslashes
        return field_name.replace('\\', '\\\\').replace('"', '\\"')

    def _extract_code_input_parameters(self, n8n_node: Dict, code: str) -> Dict:
        """
        Build inputParameters for a Code/Set node.

        Base: a single "input" parameter pointing to the immediate predecessor's
        primary output field.

        Additionally: for every  $('NodeName').first().json  cross-reference in
        the JS code we add an extra input parameter so that the IF/selector nodes
        downstream can correctly resolve all fields (e.g. isVIP from a node two
        hops back).  The parameter key is sanitised to a safe identifier:
            'Calculate Order'  →  cross_ref_Calculate_Order
        """
        node_name = n8n_node.get("name", "")
        params: Dict[str, Any] = {}

        # Primary predecessor input
        primary = self._build_predecessor_input_ref(node_name, param_key="input")
        params.update(primary)

        # Cross-references via $('NodeName').first().json
        node_type = n8n_node.get("type", "")
        if node_type == "n8n-nodes-base.code":
            lang = n8n_node.get("parameters", {}).get("language", "javaScript").lower()
            raw_code = (
                n8n_node.get("parameters", {}).get("jsCode", "")
                if lang not in ["python"]
                else ""
            )
        elif node_type in ["n8n-nodes-base.function", "n8n-nodes-base.functionItem"]:
            raw_code = (
                n8n_node.get("parameters", {}).get("functionCode", "")
                or n8n_node.get("parameters", {}).get("code", "")
            )
        else:
            raw_code = ""

        if raw_code:
            cross_refs = self._extract_js_cross_refs(raw_code)
            seen_nodes: set = set()
            for idx, (_, ref_node_name) in enumerate(cross_refs):
                if ref_node_name in seen_nodes:
                    continue
                seen_nodes.add(ref_node_name)

                ref_jiuwen_id = self.node_id_map.get(ref_node_name)
                if not ref_jiuwen_id:
                    continue

                # Skip if this is the same node as the primary predecessor
                primary_pred_id = self._find_data_predecessor_id(node_name)
                if ref_jiuwen_id == primary_pred_id:
                    continue

                ref_output_field = self._get_primary_output_field(ref_jiuwen_id)
                if not ref_output_field:
                    ref_output_field = "result"

                # Build a safe parameter key
                safe_key = "cross_ref_" + re.sub(r'[^a-zA-Z0-9_]', '_', ref_node_name)
                params[safe_key] = {
                    "type": "ref",
                    "content": [ref_jiuwen_id, ref_output_field],
                    "extra": {"index": idx + 1}
                }

        return params

    def _convert_read_write_file_to_code(self, n8n_node: Dict) -> str:
        """
        Convert n8n Read/Write File node to Python code.
        
        Handles:
        - Read mode: reads file content from a given path
        - Write mode: writes data/content to a file path
        - Append option for write mode
        - Encoding settings
        """
        node_name = n8n_node.get("name", "Read/Write File")
        params = n8n_node.get("parameters", {})
        
        # Determine operation mode
        operation = params.get("operation", "read")
        file_path = self._convert_expression(params.get("filePath", ""))
        encoding = params.get("options", {}).get("encoding", "utf-8") or "utf-8"
        
        code_lines = [
            'def main(args):',
            f'    """',
            f'    Converted from n8n Read/Write File node: {node_name}',
            f'    Operation: {operation}',
            f'    """',
            '    import os',
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}',
            '    ',
        ]
        
        if operation == "write":
            # Write mode
            append = params.get("options", {}).get("append", False)
            content = self._convert_expression(params.get("fileContent", ""))
            
            mode_flag = '"a"' if append else '"w"'
            
            code_lines.extend([
                f'    file_path = """{file_path}""" if """{file_path}""" else input_data.get("filePath", "output.txt")',
                f'    file_content = """{content}""" if """{content}""" else input_data.get("fileContent", "")',
                f'    encoding = "{encoding}"',
                f'    append_mode = {append}',
                '    ',
                '    try:',
                '        # Ensure directory exists',
                '        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else ".", exist_ok=True)',
                f'        with open(file_path, {mode_flag}, encoding=encoding) as f:',
                '            f.write(file_content)',
                '        result = {',
                '            "success": True,',
                '            "filePath": file_path,',
                '            "operation": "write",',
                f'            "append": append_mode,',
                '            "bytesWritten": len(file_content.encode(encoding))',
                '        }',
                '    except Exception as e:',
                '        result = {"success": False, "error": str(e), "filePath": file_path}',
            ])
        else:
            # Read mode (default)
            code_lines.extend([
                f'    file_path = """{file_path}""" if """{file_path}""" else input_data.get("filePath", "")',
                f'    encoding = "{encoding}"',
                '    ',
                '    try:',
                '        with open(file_path, "r", encoding=encoding) as f:',
                '            content = f.read()',
                '        result = {',
                '            "success": True,',
                '            "filePath": file_path,',
                '            "operation": "read",',
                '            "content": content,',
                '            "size": len(content)',
                '        }',
                '    except FileNotFoundError:',
                '        result = {"success": False, "error": f"File not found: {file_path}", "filePath": file_path}',
                '    except Exception as e:',
                '        result = {"success": False, "error": str(e), "filePath": file_path}',
            ])
        
        code_lines.extend([
            '    ',
            '    _output = dict(result) if isinstance(result, dict) else {}',
            '    _output["result"] = result',
            '    return _output',
        ])
        
        return '\n'.join(code_lines)

    @staticmethod
    def _create_fallback_code(n8n_node: Dict) -> str:
        """Create fallback Python code for unsupported node."""
        node_type = n8n_node.get("type", "unknown")
        node_name = n8n_node.get("name", "Node")
        params = n8n_node.get("parameters", {})
        
        return f'''def main(args):
    """Converted from n8n node: {node_name} ({node_type})"""
    # Original params: {json.dumps(params, indent=2)}
    return {{"result": args.params}}
'''

    # =========================================================================
    # PLUGIN NODE CONVERSION
    # =========================================================================

    def _convert_plugin_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n HTTP Request or App node to OpenJiuwen Plugin component."""
        node_type = n8n_node.get("type", "")
        node_name = n8n_node.get("name", "")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        
        # Extract app name from node type
        app_name = node_type.split(".")[-1] if "." in node_type else node_type
        
        plugin_param = {
            "toolID": str(uuid.uuid4()),
            "toolName": node_name,
            "pluginID": str(uuid.uuid4()),
            "pluginName": app_name,
            "pluginVersion": "draft"
        }
        
        # Add HTTP-specific config
        if "httpRequest" in node_type.lower():
            plugin_param.update({
                "url": params.get("url", ""),
                "method": params.get("method", "GET"),
                "headers": self.convert_headers(params.get("headerParameters", {})),
                "body": params.get("body", "")
            })
        
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_PLUGIN),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": node_name,
                "inputs": {
                    "pluginParam": plugin_param,
                    "inputParameters": self._build_predecessor_input_ref(node_name),
                    "_n8n_type": node_type,
                    "_n8n_params": params
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "error_code": {"type": "integer", "extra": {"index": 1}},
                        "error_message": {"type": "string", "extra": {"index": 2}},
                        "data": {"type": "object", "extra": {"index": 3}, "properties": {}}
                    },
                    "required": ["error_code", "error_message", "data"]
                }
            }
        }

    # =========================================================================
    # MERGE NODE CONVERSION
    # =========================================================================

    def _convert_merge_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Merge to OpenJiuwen Variable Merge component."""
        position = n8n_node.get("position", [x_pos, 34])
        
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_VARIABLE_MERGE),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": n8n_node.get("name", self.get_title("merge")),
                "inputs": {"inputParameters": self._build_predecessor_input_ref(n8n_node.get("name", ""))},
                "outputs": {
                    "type": "object",
                    "properties": {
                        "merged": {"type": "object", "extra": {"index": 1}}
                    }
                },
                "configs": {"groups": []}
            }
        }

    # =========================================================================
    # WORKFLOW NODE CONVERSION
    # =========================================================================

    def _convert_workflow_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Execute Workflow to OpenJiuwen Workflow component."""
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_SUB_WORKFLOW),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": n8n_node.get("name", "工作流"),
                "inputs": {
                    "inputParameters": self._build_predecessor_input_ref(n8n_node.get("name", "")),
                    "workflowParam": {
                        "workflowId": params.get("workflowId", ""),
                        "mode": params.get("mode", "sync")
                    }
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "object", "extra": {"index": 1}}
                    },
                    "required": ["result"]
                }
            }
        }

    # =========================================================================
    # FALLBACK NODE CREATION
    # =========================================================================

    def _create_fallback_node(self, n8n_node: Dict, x_pos: int = 0) -> Dict:
        """Create fallback CODE node for unsupported n8n nodes."""
        node_id = self.id_gen.next_id("fallback")
        node_type = n8n_node.get("type", "unknown")
        node_name = n8n_node.get("name", "Node")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_CODE),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": f"{node_name} (TODO)",
                "inputs": {
                    "language": "python",
                    "code": f'''def main(args):
    """TODO: Implement logic from n8n node type: {node_type}"""
    # Original node parameters:
    # {json.dumps(params, indent=2)}
    return {{"result": "Not implemented"}}
''',
                    "inputParameters": self._build_predecessor_input_ref(node_name),
                    "exception_config": {
                        "process_type": "break"
                    }
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "result": {"type": "string", "extra": {"index": 1}}
                    },
                    "required": ["result"]
                }
            }
        }

    # =========================================================================
    # END NODE CREATION
    # =========================================================================

    def _create_end_node(self, last_node_id: Optional[str]):
        """Create End node with reference to last node output."""
        self.end_node_id = self.id_gen.next_id("end")
        x_pos = 180 + (len(self.openjiuwen_nodes) * 460)
        
        # Build input parameters
        input_params = {}
        content_template = None
        
        ref_node_id = self.last_llm_node_id or last_node_id
        if ref_node_id:
            # Resolve the correct output field for whatever the last node type is
            output_field = self._get_primary_output_field(ref_node_id)
            if not output_field:
                output_field = "result"  # fallback; shouldn't happen for non-selector last nodes
            input_params["result"] = {
                "type": "ref",
                "content": [ref_node_id, output_field],
                "extra": {"index": 0}
            }
            content_template = {
                "type": "template",
                "content": "{{result}}"
            }
        
        data = {
            "title": self.get_title("end"),
            "inputs": {
                "inputParameters": input_params,
                "streaming": False
            },
            "streaming": False
        }
        
        if content_template:
            data["inputs"]["content"] = content_template
        
        end_node = {
            "id": self.end_node_id,
            "type": str(ComponentType.COMPONENT_TYPE_END),
            "meta": {"position": {"x": x_pos, "y": 34}},
            "data": data
        }
        
        self.openjiuwen_nodes.append(end_node)

    # =========================================================================
    # CONNECTION CONVERSION
    # =========================================================================

    def _convert_connections(self):
        """Convert n8n connections to OpenJiuwen edges."""
        for source_name, conn_types in self.n8n_connections.items():
            source_id = self.node_id_map.get(source_name)
            if not source_id:
                continue
            
            for conn_type, target_lists in conn_types.items():
                # Skip AI sub-node connections (they're embedded)
                if conn_type in ["ai_languageModel", "ai_memory", "ai_tool", 
                                 "ai_embedding", "ai_document"]:
                    continue
                
                source_n8n_node = self.nodes_by_name.get(source_name, {})
                source_n8n_type = source_n8n_node.get("type", "")
                source_jiuwen_type = self.N8N_TO_OPENJIUWEN.get(source_n8n_type)
                is_code = source_jiuwen_type == ComponentType.COMPONENT_TYPE_CODE or \
                      source_jiuwen_type is None
                is_selector = source_jiuwen_type == ComponentType.COMPONENT_TYPE_IF

                # Pre-fetch branch IDs from the already-converted jiuwen node
                # so each output_index maps to its correct branchId
                selector_branch_ids = []
                if is_selector:
                    jiuwen_node = next((n for n in self.openjiuwen_nodes if n["id"] == source_id), None)
                    if jiuwen_node:
                        branches = jiuwen_node.get("data", {}).get("branches", [])
                        selector_branch_ids = [b.get("branchId", str(i)) for i, b in enumerate(branches)]
                
                
                for output_index, target_list in enumerate(target_lists):
                    for target in target_list:
                        target_name = target.get("node")
                        target_id = self.node_id_map.get(target_name)
                        
                        if target_id and source_id != target_id:
                            # Check for duplicate edges
                            edge_exists = any(
                                e.get("sourceNodeID") == source_id and 
                                e.get("targetNodeID") == target_id
                                for e in self.openjiuwen_edges
                            )
                            if not edge_exists:
                                edge = {
                                    "sourceNodeID": source_id,
                                    "targetNodeID": target_id,
                                }
                                if is_code:
                                    edge["sourcePortID"] = "0"
                                elif is_selector and output_index < len(selector_branch_ids):
                                    # output_index 0 → first branch (true/if)
                                    # output_index 1 → second branch (else)
                                    edge["sourcePortID"] = selector_branch_ids[output_index]
                                self.openjiuwen_edges.append(edge)

    def _find_last_node(self) -> Optional[str]:
        """Find one terminal node (no outgoing edges). Used for End-node ref."""
        terminals = self._find_all_terminal_nodes()
        return terminals[0] if terminals else None

    def _find_all_terminal_nodes(self) -> List[str]:
        """
        Return the IDs of ALL non-start/non-end nodes that have no outgoing edge.

        In branching workflows (e.g. VIP vs Standard confirmation) every leaf
        branch is a terminal node and must be connected to the End node.
        """
        sources = {e["sourceNodeID"] for e in self.openjiuwen_edges}
        terminals = []
        for node in self.openjiuwen_nodes:
            node_id = node["id"]
            node_type = int(node.get("type", 0))
            if node_type in [ComponentType.COMPONENT_TYPE_START,
                             ComponentType.COMPONENT_TYPE_END]:
                continue
            if node_id not in sources:
                terminals.append(node_id)
        return terminals

    def _ensure_edge_connections(self):
        """Ensure start and end nodes are properly connected."""
        # Connect start to first main node
        if self.first_main_node:
            target_id = self.node_id_map.get(self.first_main_node)
            if target_id and target_id != self.start_node_id:
                edge_exists = any(
                    e.get("sourceNodeID") == self.start_node_id and 
                    e.get("targetNodeID") == target_id
                    for e in self.openjiuwen_edges
                )
                if not edge_exists:
                    self.openjiuwen_edges.insert(0, {
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": self.start_node_id,
                        "targetNodeID": target_id,
                        "sourcePortID": "0",
                    })
        
        # Connect ALL terminal nodes (leaves) to End — handles branching workflows
        # where multiple branches each end at a different node.
        if self.end_node_id:
            for terminal_id in self._find_all_terminal_nodes():
                if terminal_id == self.end_node_id:
                    continue
                edge_exists = any(
                    e.get("sourceNodeID") == terminal_id and
                    e.get("targetNodeID") == self.end_node_id
                    for e in self.openjiuwen_edges
                )
                if not edge_exists:
                    self.openjiuwen_edges.append({
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": terminal_id,
                        "targetNodeID": self.end_node_id,
                        "sourcePortID": "0",
                    })
        
        if self.end_node_id:
            for node in self.openjiuwen_nodes:
                if int(node.get("type", 0)) != ComponentType.COMPONENT_TYPE_IF:
                    continue
                node_id = node["id"]
                branches = node.get("data", {}).get("branches", [])
                if len(branches) < 2:
                    continue
                else_branch_id = branches[1].get("branchId")
                if not else_branch_id:
                    continue
                # Check if the else branch already has an outgoing edge
                else_edge_exists = any(
                    e.get("sourceNodeID") == node_id and e.get("sourcePortID") == else_branch_id
                    for e in self.openjiuwen_edges
                )
                if not else_edge_exists:
                    self.openjiuwen_edges.append({
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": node_id,
                        "targetNodeID": self.end_node_id,
                        "sourcePortID": else_branch_id,
                    })

    # =========================================================================
    # I/O PARAMETER EXTRACTION
    # =========================================================================

    def _extract_io_parameters(self) -> Tuple[List[Dict], List[Dict]]:
        """Extract input/output parameters from Start/End nodes."""
        inputs = []
        outputs = []
        
        for node in self.openjiuwen_nodes:
            node_type = int(node.get("type", 0))
            
            if node_type == ComponentType.COMPONENT_TYPE_START:
                outputs_data = node.get("data", {}).get("outputs", {})
                properties = outputs_data.get("properties", {})
                required_list = outputs_data.get("required", [])
                
                for name, prop in properties.items():
                    inputs.append({
                        "name": name,
                        "type": prop.get("type", "string"),
                        "description": prop.get("description", ""),
                        "required": name in required_list
                    })
            
            elif node_type == ComponentType.COMPONENT_TYPE_END:
                outputs.append({
                    "name": "result",
                    "type": "string",
                    "description": "Workflow result"
                })
        
        return inputs, outputs

    # =========================================================================
    # EXPRESSION CONVERSION
    # =========================================================================

    @staticmethod
    def _convert_expression(text: str) -> str:
        """Convert n8n expressions to OpenJiuwen template format."""
        if not text:
            return text
        
        # Strip leading "=" that indicates an n8n expression
        if text.startswith("="):
            text = text[1:]
        
        # {{ $json["field name"] }} or {{ $json['field name'] }} → {{sanitized_field}}
        def _sanitize_bracket_field(match):
            raw = match.group(1)
            safe = re.sub(r'[^a-zA-Z0-9_\u4e00-\u9fff]', '_', raw)
            safe = re.sub(r'_+', '_', safe).strip('_').lower()
            return '{{' + (safe or 'field') + '}}'
        
        text = re.sub(
            r"""\{\{\s*\$json\[['"]([^'"]+)['"]\]\s*\}\}""",
            _sanitize_bracket_field, text
        )
        
        # {{ $json.field }} → {{field}}
        text = re.sub(r'\{\{\s*\$json\.(\w+)\s*\}\}', r'{{\1}}', text)
        
        # {{ $('Node').item.json["field"] }} → {{sanitized_field}}
        text = re.sub(
            r"""\{\{\s*\$\(['""][^'"]+['"]\)\.item\.json\[['"]([^'"]+)['"]\]\s*\}\}""",
            _sanitize_bracket_field, text
        )
        
        # {{ $('Node').item.json.field }} → {{field}}
        text = re.sub(
            r"\{\{\s*\$\(['\"]([^'\"]+)['\"]\)\.item\.json\.(\w+)\s*\}\}", 
            r'{{\2}}', 
            text
        )
        
        # ={{ $json.field }} → {{field}}
        text = re.sub(r'=\{\{\s*\$json\.(\w+)\s*\}\}', r'{{\1}}', text)
        
        # Escape literal display placeholders that aren't template variables.
        # e.g. {{Weather Phenomenon, e.g., Sunny to Cloudy}} → {Weather Phenomenon, e.g., Sunny to Cloudy}
        # Real template vars like {{city}} are pure \w+ and stay as double-brace.
        def _escape_display_placeholder(match):
            content = match.group(1)
            if re.search(r'[^\w]', content):
                return '{' + content + '}'
            return match.group(0)
        
        text = re.sub(r'\{\{(.+?)\}\}', _escape_display_placeholder, text)
        
        return text

    def _convert_expression_with_mapping(self, text: str) -> str:
        """Convert n8n expressions with field name mapping."""
        if not text:
            return text
        
        # First apply field mapping for known field names
        for n8n_name, jiuwen_name in self.field_name_map.items():
            # Handle {{ $json["Field Name"] }} bracket notation
            text = re.sub(
                rf"""\{{\{{\s*\$json\[['"]{re.escape(n8n_name)}['"]\]\s*\}}\}}""",
                f'{{{{{jiuwen_name}}}}}',
                text
            )
            # Handle {{ $json.FieldName }} dot notation
            text = re.sub(
                rf'\{{\{{\s*\$json\.{re.escape(n8n_name)}\s*\}}\}}',
                f'{{{{{jiuwen_name}}}}}',
                text
            )
            text = re.sub(
                rf'=\{{\{{\s*\$json\.{re.escape(n8n_name)}\s*\}}\}}',
                f'{{{{{jiuwen_name}}}}}',
                text
            )
        
        # Then apply general expression conversion
        return self._convert_expression(text)

    # =========================================================================
    # UTILITY METHODS (preserved from original)
    # =========================================================================

    @staticmethod
    def convert_headers(header_params: Any) -> Dict:
        """Convert n8n header parameters to dict."""
        if not header_params:
            return {}
        
        if isinstance(header_params, dict):
            return header_params
        
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
        """Generate unique node ID (legacy method for compatibility)."""
        if node_type.startswith("n8n-nodes-base."):
            simple_type = node_type.replace("n8n-nodes-base.", "")
        else:
            simple_type = node_type

        return f"{simple_type}_{uuid.uuid4().hex[:8]}"

    # Legacy method for backward compatibility
    @staticmethod
    def add_start_end_nodes(nodes: List[Dict], edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Add START and END nodes to workflow (legacy static method)."""
        # Find entry points (nodes with no incoming connections)
        all_targets = {edge["targetNodeID"] for edge in edges}
        entry_nodes = [n for n in nodes if n["id"] not in all_targets]

        # Create START node
        start_id = f"start_{uuid.uuid4().hex[:8]}"
        start_node = {
            "id": start_id,
            "type": str(ComponentType.COMPONENT_TYPE_START),
            "data": {
                "title": self.get_title("start"),
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
            })

        nodes.extend([start_node, end_node])
        return nodes, edges


# =============================================================================
# STANDALONE USAGE (for testing without SDK)
# =============================================================================

def convert_workflow_standalone(n8n_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert n8n workflow to OpenJiuwen format (standalone, no SDK).
    
    Args:
        n8n_json: n8n workflow JSON
        
    Returns:
        OpenJiuwen workflow JSON with nodes and edges
    """
    converter = N8nWorkflowConverter()
    
    return converter.convert_to_schema(n8n_json)

if __name__ == "__main__":
    # Example usage for testing
    import sys
    
    if len(sys.argv) < 2:
        logger.error("Usage: python converter_n8n.py <n8n_workflow.json> [output.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    with open(input_file, 'r', encoding='utf-8') as f:
        n8n_workflow = json.load(f)
    
    result = convert_workflow_standalone(n8n_workflow)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved to: {output_file}")
    else:
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))