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
from openjiuwen_studio.schemas.node import BaseType, BaseValue

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
        self.reset_state()

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

    def reset_state(self):
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
         # Maps synthetic compareDatasets selector_id → paired code_id so that
        # _find_data_predecessor_id returns the Code node (the real data source)
        # instead of skipping past the Selector to compareDatasets' own predecessor.
        self.compare_datasets_code_ids: Dict[str, str] = {}
        # Maps n8n compareDatasets node name → {port_index: selector_id}.
        # node_id_map[name] points to code_id (so Dataset A/B edges wire correctly
        # into the Code node).  Outgoing edges from compareDatasets (to Label nodes
        # etc.) must use the per-port Selector as source; this dict provides that
        # override inside _convert_connections.
        self.compare_datasets_selector_ids: Dict[str, Dict[int, str]] = {}
        # Maps compareDatasets guard selector_id → the Code node output field that
        # selector guards (e.g. selector_for_port_1 → "only_a").  Used by
        # _build_predecessor_input_ref so downstream nodes reference the right field.
        self.compare_datasets_port_fields: Dict[str, str] = {}
        # Maps n8n loop node name → {"loop_id": jiuwen_node_id}.
        # Populated in _convert_main_nodes when a LOOP component is created.
        # Used in _convert_connections to route edges to/from the Loop node.
        self.loop_node_registry: Dict[str, Dict[str, str]] = {}
        # Maps n8n node name → (code_id, field_name) for nodes that are directly
        # downstream of a compareDatasets node.  Populated during node conversion
        # (before _convert_connections runs) by inspecting n8n_connections so that
        # _build_predecessor_input_ref can inject the correct port-specific field
        # (e.g. "matched", "only_a") rather than the generic "result".
        self.compare_datasets_downstream_fields: Dict[str, tuple] = {}

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
        self.reset_state()
        
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
        self._fix_shared_merge_predecessors()

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
        self.reset_state()
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

        # Manual trigger has no form inputs — expose a generic "input" field so
        # downstream LLM nodes can build a valid inputParameters reference to it.
        if "manual" in node_type.lower():
            return {
                "type": "object",
                "properties": {
                    "input": {
                        "type": "string",
                        "default": "",
                        "description": "Manual trigger input"
                    }
                },
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
    
    def _topological_sort_nodes(self, n8n_nodes: List[Dict]) -> List[Dict]:
        """
        Sort n8n nodes in execution order using the connections graph so that
        every predecessor is converted before the nodes that depend on it.
        Nodes with no declared order (cycles, disconnected) are appended last.
        """
        from collections import deque

        name_to_node = {n.get("name", ""): n for n in n8n_nodes}
        in_degree: Dict[str, int] = {n.get("name", ""): 0 for n in n8n_nodes}

        for source, conn_types in self.n8n_connections.items():
            for targets in conn_types.get("main", []):
                for t in targets:
                    target_name = t.get("node", "")
                    if target_name in in_degree:
                        in_degree[target_name] += 1

        queue = deque(
            [n for n in n8n_nodes if in_degree.get(n.get("name", ""), 0) == 0]
        )
        sorted_nodes: List[Dict] = []

        while queue:
            node = queue.popleft()
            sorted_nodes.append(node)
            name = node.get("name", "")
            for targets in self.n8n_connections.get(name, {}).get("main", []):
                for t in targets:
                    target_name = t.get("node", "")
                    if target_name in in_degree:
                        in_degree[target_name] -= 1
                        if in_degree[target_name] == 0:
                            target_node = name_to_node.get(target_name)
                            if target_node:
                                queue.append(target_node)

        # Append any remaining nodes (cycles or fully disconnected)
        processed = {n.get("name", "") for n in sorted_nodes}
        for n in n8n_nodes:
            if n.get("name", "") not in processed:
                sorted_nodes.append(n)

        return sorted_nodes

    # =========================================================================
    # MAIN NODE CONVERSION
    # =========================================================================

    def _convert_main_nodes(self, n8n_nodes: List[Dict]):
        """Convert all main (non-trigger, non-subnode) nodes."""
        n8n_nodes = self._topological_sort_nodes(n8n_nodes)
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

            # Sticky notes — converted to Jiuwen note (type 99) and appended
            # directly, bypassing the regular conversion pipeline.
            # They have no edges, no ID mapping, and do not affect x_pos /
            # first_main_node tracking.
            if node_type == "n8n-nodes-base.stickyNote":
                note_node = self._convert_sticky_note(node)
                self.openjiuwen_nodes.append(note_node)
                self.report.converted_nodes += 1
                self.report.jiuwen_type_counts[99].append(node_name)
                continue

            # compareDatasets → two-node conversion: Code node + Selector node.
            # The Code node runs the comparison and exposes matched/only_a/only_b
            # as named output fields.  The Selector routes execution so that n8n's
            # two primary output ports (matched vs unmatched) map to Jiuwen's two
            # Selector branches.  node_id_map points to the Selector so that
            # _convert_connections routes downstream edges correctly (port 0/1 →
            # branch 0/1).  _compare_datasets_code_ids lets _find_data_predecessor_id
            # return the Code node (the actual data source) when a downstream node
            # asks "where does my input data come from?".
            if node_type == "n8n-nodes-base.compareDatasets":
                try:
                    code_node, selector_nodes = self._convert_compare_datasets_node(node, x_pos)
                    self.openjiuwen_nodes.append(code_node)

                    port_to_selector: Dict[int, str] = {}
                    # port_defs order: matched(0), only_a(1), only_b(2), union_excl(3)
                    port_fields = ["matched", "only_a", "only_b", "union_excl"]

                    for port_idx, sel_node in enumerate(selector_nodes):
                        self.openjiuwen_nodes.append(sel_node)
                        sel_id = sel_node["id"]
                        # Wire Code → each guard Selector independently
                        self.openjiuwen_edges.append({
                            "id": f"edge_{uuid.uuid4().hex[:8]}",
                            "sourceNodeID": code_node["id"],
                            "targetNodeID": sel_id,
                            "sourcePortID": "0",
                        })
                        port_to_selector[port_idx] = sel_id
                        # _compare_datasets_code_ids: selector → code (for
                        # _find_data_predecessor_id to skip past the guard)
                        self.compare_datasets_code_ids[sel_id] = code_node["id"]
                        # _compare_datasets_port_fields: selector → field name
                        # (so _build_predecessor_input_ref picks the right field)
                        self.compare_datasets_port_fields[sel_id] = port_fields[port_idx]

                    # node_id_map → code_node so incoming Dataset A/B edges land
                    # on the Code node, not on any Selector
                    self.node_id_map[node_name] = code_node["id"]
                    # Per-port selector map for _convert_connections outgoing routing
                    self.compare_datasets_selector_ids[node_name] = port_to_selector

                    # Map each n8n downstream node name → (code_id, field_name) so
                    # _build_predecessor_input_ref injects the port-specific field
                    # (e.g. "matched", "only_a") rather than the generic "result".
                    _cd_port_fields = ["matched", "only_a", "only_b", "union_excl"]
                    _cd_connections = self.n8n_connections.get(node_name, {}).get("main", [])
                    for _port_idx, _targets in enumerate(_cd_connections):
                        if _port_idx >= len(_cd_port_fields):
                            break
                        for _tgt in _targets:
                            _tgt_name = _tgt.get("node", "")
                            if _tgt_name:
                                self.compare_datasets_downstream_fields[_tgt_name] = (
                                    code_node["id"], _cd_port_fields[_port_idx]
                                )

                    self.report.converted_nodes += 1
                    self.report.jiuwen_type_counts[
                        int(code_node.get("type", 0))
                    ].append(node_name)
                    if self.first_main_node is None:
                        self.first_main_node = node_name
                    x_pos += 460
                except Exception as e:
                    error_msg = f"Failed to convert compareDatasets node '{node_name}': {e}"
                    self.report.add_warning(error_msg)
                    logger.warning(error_msg)
                    fallback = self._create_fallback_node(node, x_pos)
                    self.openjiuwen_nodes.append(fallback)
                    self.node_id_map[node_name] = fallback["id"]
                    x_pos += 460
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
                    
                    # Track last LLM node or react agent for End node reference
                    if jiuwen_type in (ComponentType.COMPONENT_TYPE_LLM, ComponentType.COMPONENT_TYPE_REACT_AGENT):
                        self.last_llm_node_id = jiuwen_node["id"]

                    # Register loop nodes so _convert_connections can route
                    # incoming/outgoing edges to the correct Loop component ID.
                    if jiuwen_type == ComponentType.COMPONENT_TYPE_LOOP:
                        self.loop_node_registry[node_name] = {"loop_id": jiuwen_node["id"]}
                    
                    if self.first_main_node is None:
                        self.first_main_node = node_name
                    
                    x_pos += 460
            except NotImplementedError:
                # Hard failure: propagate to the caller so it is never silently
                # swallowed as a warning.  PLUGIN nodes currently raise this.
                raise
            except Exception as e:
                # Soft failure: use a fallback node and continue conversion.
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
        
        # ── Data Transform nodes: always route through Code, regardless of what
        # N8N_TO_OPENJIUWEN says.  An incorrect mapping entry (e.g. sort →
        # SUB_WORKFLOW) would otherwise call _convert_workflow_node and produce a
        # node with an empty workflowId → OpenJiuwen error "<missing:workflow>".
        if node_type in self.DATA_TRANSFORM_HANDLERS:
            type_prefix = self._get_type_prefix(ComponentType.COMPONENT_TYPE_CODE)
            node_id = self.id_gen.next_id(type_prefix)
            return self._convert_code_node(n8n_node, node_id, x_pos)

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
            node_name = n8n_node.get("name", "unknown")
            raise NotImplementedError(
                f"Conversion of PLUGIN nodes is not supported. "
                f"Node '{node_name}' (id: {node_id}) cannot be converted."
            )
        elif component_type == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            return self._convert_merge_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_SUB_WORKFLOW:
            return self._convert_workflow_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_HTTP_REQUEST:
            return self._convert_http_request_node(n8n_node, node_id, x_pos)
        elif component_type == ComponentType.COMPONENT_TYPE_REACT_AGENT:
            return self._convert_react_agent_node(n8n_node, node_id, x_pos)
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
            ComponentType.COMPONENT_TYPE_HTTP_REQUEST: "http",
            ComponentType.COMPONENT_TYPE_REACT_AGENT: "react_agent",
        }
        return prefixes.get(component_type, "node")

    # Note (type 99) is not in ComponentType — handled by _convert_sticky_note
    # which calls id_gen.next_id("note") directly.

    # =========================================================================
    # LLM NODE CONVERSION
    # =========================================================================

    def _convert_llm_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Agent/LLM node to OpenJiuwen LLM component."""
        params = n8n_node.get("parameters", {})
        node_name = n8n_node.get("name", "")
        node_type = n8n_node.get("type", "")

        # ── OpenAI Assistant: uses assistantId instead of a model sub-node ───
        if "openAiAssistant" in node_type:
            raw_assistant = params.get("assistantId", params.get("assistant", {}))
            if isinstance(raw_assistant, dict):
                assistant_id = raw_assistant.get("value", raw_assistant.get("cachedResultName", ""))
            else:
                assistant_id = str(raw_assistant) if raw_assistant else ""
            model_config = {
                "id": "1",
                "name": "openai",
                "type": f"assistant:{assistant_id}" if assistant_id else "openai-assistant",
            }
            user_prompt = params.get("text", params.get("prompt", "{{input}}"))
            system_prompt = ""
            user_prompt = self._convert_expression_with_mapping(user_prompt)
        else:
            # ── All other chain types: delegate prompt extraction ─────────────
            system_prompt, user_prompt = self._extract_chain_prompts(n8n_node)
            system_prompt = self._convert_expression_with_mapping(system_prompt)
            user_prompt = self._convert_expression_with_mapping(user_prompt)
            # Get model config from connected AI sub-node
            model_config = self._find_connected_model(node_name)

        # ── Build default prompt when extraction yielded nothing ──────────────
        if not user_prompt and self.field_name_map:
            prompt_parts = [f"{{{{{name}}}}}" for name in self.field_name_map.values()]
            user_prompt = " ".join(prompt_parts)
        elif not user_prompt:
            pred_id_for_prompt = self._find_data_predecessor_id(node_name)
            if pred_id_for_prompt:
                primary = self._get_primary_output_field(pred_id_for_prompt)
                pred_node_for_prompt = next(
                    (n for n in self.openjiuwen_nodes if n["id"] == pred_id_for_prompt), None
                )
                direct_fields = list(
                    pred_node_for_prompt.get("data", {}).get("outputs", {})
                    .get("properties", {}).keys()
                ) if pred_node_for_prompt else []
                user_prompt = (
                    f"{{{{{direct_fields[0]}}}}}" if direct_fields
                    else f"{{{{{primary or 'input'}}}}}"
                )
            else:
                user_prompt = "{{input}}"

        # ── Extract template variables → build inputParameters ────────────────
        template_vars = re.findall(r'\{\{(\w+)\}\}', user_prompt)
        input_parameters: Dict[str, Any] = {}

        pred_id = self._find_data_predecessor_id(node_name)
        pred_output_field = self._get_primary_output_field(pred_id) if pred_id else ""

        pred_direct_fields: set = set()
        if pred_id:
            pred_node = next((n for n in self.openjiuwen_nodes if n["id"] == pred_id), None)
            if pred_node:
                props = pred_node.get("data", {}).get("outputs", {}).get("properties", {})
                pred_direct_fields = set(props.keys())

        for idx, var_name in enumerate(template_vars):
            if var_name in pred_direct_fields and pred_id:
                content = [pred_id, var_name]
            elif pred_id and pred_output_field:
                content = [pred_id, pred_output_field]
            else:
                content = [self.start_node_id, var_name]

            param: Dict[str, Any] = {"type": "ref", "content": content}
            if idx == 0:
                param["extra"] = {"index": 0}
            input_parameters[var_name] = param

        # ── Warn about connected tools ────────────────────────────────────────
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
                            "content": system_prompt,
                        },
                        "prompt": {
                            "type": "template",
                            "content": user_prompt,
                        },
                        "model": model_config,
                    },
                    "inputParameters": input_parameters,
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "extra": {"index": 1},
                        }
                    },
                    "required": ["output"],
                },
            },
        }

    @staticmethod
    def _extract_model_name(params: Dict) -> str:
        """
        Safely extract a plain model-name string from n8n model parameters.

        n8n's resource-locator widget stores model as a nested object:
            {"__rl": true, "value": "deepseek-chat", "mode": "list", ...}
        Calling .lower() on that dict raises AttributeError.  This helper
        unwraps the object and always returns a plain string.
        """
        raw = params.get("model", params.get("modelId", ""))
        if isinstance(raw, dict):
            # Resource-locator format — prefer "value", fall back to "cachedResultName"
            return str(raw.get("value", raw.get("cachedResultName", "")) or "")
        return str(raw) if raw else ""

    @staticmethod
    def _extract_chain_prompts(n8n_node: Dict) -> Tuple[str, str]:
        """
        Return (system_prompt, user_prompt) for any LLM chain/agent node type.

        Every node type stores its prompt in a different location.  This method
        centralises the per-type extraction so _convert_llm_node stays clean.

        Supported types and their param layouts:
          chainLlm / agent          text, messages.messageValues, options.systemMessage
          chainSummarization        summarizationMethodAndPrompts.values.prompt
          chainRetrievalQa          query / options.systemPrompt
          informationExtractor      text / schema.attributes[]
          textClassifier            inputText / categories.categories[]
          sentimentAnalysis         inputText  (fixed system prompt)
          aiTransform               prompt / systemPrompt
          openAiAssistant           handled separately (no chain prompts)
        """
        node_type = n8n_node.get("type", "")
        params = n8n_node.get("parameters", {})
        system_prompt = ""
        user_prompt = ""

        # ── chainLlm / agent ─────────────────────────────────────────────────
        if "chainLlm" in node_type or "agent" in node_type:
            # System prompt — check all known locations in priority order
            if params.get("options", {}).get("systemMessage"):
                system_prompt = params["options"]["systemMessage"]
            elif params.get("systemMessage"):
                system_prompt = params["systemMessage"]
            # chainLlm: system message in parameters.messages.messageValues[0].message
            if not system_prompt:
                msg_values = params.get("messages", {}).get("messageValues", [])
                if msg_values and isinstance(msg_values, list):
                    system_prompt = msg_values[0].get("message", "")
            if not system_prompt:
                system_prompt = n8n_node.get("notes", "")
            # User prompt
            if params.get("promptType") == "define" and params.get("text"):
                user_prompt = params["text"]
            elif params.get("text"):
                user_prompt = params["text"]

        # ── chainSummarization ───────────────────────────────────────────────
        elif "chainSummarization" in node_type:
            mode = params.get("chunkingMode", "map_reduce")
            method_cfg = params.get("summarizationMethodAndPrompts", {})
            custom_prompt = (
                method_cfg.get("values", {}).get("prompt")
                or method_cfg.get("prompt")
            )
            if custom_prompt:
                user_prompt = custom_prompt
            elif params.get("text"):
                user_prompt = params["text"]
            else:
                user_prompt = "{{input}}"
            system_prompt = f"Summarize the following text. Chunking mode: {mode}."

        # ── chainRetrievalQa ─────────────────────────────────────────────────
        elif "chainRetrievalQa" in node_type:
            user_prompt = params.get("query", params.get("text", "{{input}}"))
            system_prompt = params.get("options", {}).get("systemPrompt", "")

        # ── informationExtractor ─────────────────────────────────────────────
        elif "informationExtractor" in node_type:
            user_prompt = params.get("text", params.get("inputText", "{{input}}"))
            schema = params.get("schema", {})
            attributes = schema.get("attributes", [])
            if attributes:
                attr_parts = []
                for a in attributes:
                    attr_parts.append("{name} ({type}): {desc}".format(
                        name=a.get("name", "field"),
                        type=a.get("type", "string"),
                        desc=a.get("description", ""),
                    ))
                attr_desc = "; ".join(attr_parts)
                system_prompt = f"Extract the following fields from the text — {attr_desc}"
            else:
                system_prompt = "Extract structured information from the provided text."

        # ── textClassifier ───────────────────────────────────────────────────
        elif "textClassifier" in node_type:
            user_prompt = params.get("inputText", params.get("text", "{{input}}"))
            categories = params.get("categories", {}).get("categories", [])
            cat_names = []
            for c in categories:
                if c:
                    cat_names.append(c.get("category", c.get("name", "")))
            if cat_names:
                system_prompt = (
                    "Classify the text into exactly one of these categories: "
                    + ", ".join(cat_names)
                    + ". Return only the category name."
                )
            else:
                system_prompt = "Classify the text and return the category name."

        # ── sentimentAnalysis ────────────────────────────────────────────────
        elif "sentimentAnalysis" in node_type:
            user_prompt = params.get("inputText", params.get("text", "{{input}}"))
            system_prompt = (
                "Analyze the sentiment of the following text. "
                "Return exactly one of: Positive, Negative, or Neutral."
            )

        # ── aiTransform ──────────────────────────────────────────────────────
        elif "aiTransform" in node_type:
            user_prompt = params.get("prompt", params.get("text", "{{input}}"))
            system_prompt = params.get("systemPrompt", "")

        # ── openAiAssistant: no chain-style prompts (handled in _convert_llm_node)
        # ── vectorStore nodes: no prompt extraction needed

        return system_prompt, user_prompt

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
                                model_name = self._extract_model_name(params)
                                return self._map_model_to_jiuwen(model_name, conn_info[1])
        
        # Also check all nodes for AI model sub-nodes (they may not be in connections)
        for source_name, node in self.nodes_by_name.items():
            source_type = node.get("type", "")
            if source_type in AI_SUBNODES:
                conn_info = AI_SUBNODES[source_type]
                if conn_info[0] == "ai_languageModel":
                    params = node.get("parameters", {})
                    model_name = self._extract_model_name(params)
                    return self._map_model_to_jiuwen(model_name, conn_info[1])
        
        # Default model
        return {"id": "1", "name": "deepseek", "type": "deepseek-chat"}

    @staticmethod
    def _map_model_to_jiuwen(model_name: str, provider: str) -> Dict:
        """
        Map an n8n model name + provider string to a Jiuwen model config dict.

        Strategy:
          1. Provider-first: the AI_SUBNODES tuple carries the authoritative
             provider tag (e.g. "groq", "mistral") — use it as the primary key.
             This correctly handles providers whose model names contain no
             brand hint (llama-3.1-70b-versatile on Groq, command-r on Cohere…).
          2. Model-name fallback: when the provider string is absent or unknown,
             scan the model name for well-known brand keywords.
        """
        # ── 1. Provider-first lookup ─────────────────────────────────────────
        _defaults: Dict[str, str] = {
            "openai": "gpt-4o",
            "anthropic": "claude-3-5-sonnet-20241022",
            "azure-openai": "gpt-4o",
            "gemini": "gemini-1.5-pro",
            "google-vertex": "gemini-1.5-pro",
            "ollama": "llama3",
            "groq": "llama-3.3-70b-versatile",
            "mistral": "mistral-large-latest",
            "deepseek": "deepseek-chat",
            "cohere": "command-r-plus",
            "aws-bedrock": "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "openrouter": "openai/gpt-4o",
            "xai": "grok-2",
            "huggingface": "",
            "lemonade": "",
            "perplexity": "sonar-pro",
            "fireworks": "",
            "togetherai": "",
            "novita": "",
            "Qwen": "qwen-max",
        }
        if provider in _defaults:
            return {
                "id": "1",
                "name": provider,
                "type": model_name or _defaults[provider],
            }

        # ── 2. Model-name keyword fallback ───────────────────────────────────
        model_lower = model_name.lower()
        if "qwen" in model_lower:
            return {"id": "1", "name": "Qwen", "type": model_name}
        if any(p in model_lower for p in ("gpt-4", "gpt-3", "gpt-3.5", "o1-", "o3-")):
            return {"id": "1", "name": "openai", "type": model_name}
        if "claude" in model_lower:
            return {"id": "1", "name": "anthropic", "type": model_name}
        if "deepseek" in model_lower:
            return {"id": "1", "name": "deepseek", "type": model_name}
        if "gemini" in model_lower:
            return {"id": "1", "name": "gemini", "type": model_name}
        if any(p in model_lower for p in ("llama", "mixtral", "mistral")):
            return {"id": "1", "name": "ollama", "type": model_name}
        if "grok" in model_lower:
            return {"id": "1", "name": "xai", "type": model_name}
        if any(p in model_lower for p in ("command-r", "command-light")):
            return {"id": "1", "name": "cohere", "type": model_name}
        if "sonar" in model_lower:
            return {"id": "1", "name": "perplexity", "type": model_name}

        # ── 3. Final catch-all ───────────────────────────────────────────────
        return {
            "id": "1",
            "name": provider or "openai",
            "type": model_name or "gpt-4o",
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

    def _find_predecessor_by_input_index(
        self, n8n_node_name: str, input_index: int
    ) -> Optional[str]:
        """
        Find the Jiuwen ID of the predecessor connected to a specific input
        port (index) of the given n8n node.

        In n8n connections the ``index`` field on the target object indicates
        which input port of the target node the edge arrives on:

            "Dataset A": {"main": [[{"node": "Compare Datasets", "type": "main", "index": 0}]]}
            "Dataset B": {"main": [[{"node": "Compare Datasets", "type": "main", "index": 1}]]}

        This is used by ``_convert_compare_datasets_node`` to distinguish
        Input A (index 0) from Input B (index 1) so that both datasets are
        passed as separate ``inputParameters`` to the generated Code node.
        """
        for source_name, conn_types in self.n8n_connections.items():
            for conn_type, target_lists in conn_types.items():
                if conn_type != "main":
                    continue
                for target_list in target_lists:
                    for target in target_list:
                        if (
                            target.get("node") == n8n_node_name
                            and target.get("index", 0) == input_index
                        ):
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
            # Synthetic compareDatasets selector: return the paired Code node so
            # downstream nodes reference [code_id, "matched"/"only_a"/…] instead
            # of skipping all the way back to compareDatasets' own predecessor.
            if pred_id in self.compare_datasets_code_ids:
                return self.compare_datasets_code_ids[pred_id]
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
        if node_type == ComponentType.COMPONENT_TYPE_REACT_AGENT:
            return "output"
        if node_type == ComponentType.COMPONENT_TYPE_PLUGIN or node_type == ComponentType.COMPONENT_TYPE_HTTP_REQUEST:
            return "data"
        if node_type == ComponentType.COMPONENT_TYPE_VARIABLE_MERGE:
            # Output group is named "output" by the converter
            props = node.get("data", {}).get("outputs", {}).get("properties", {})
            if props:
                return next(iter(props))
            return "output"
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
        # Resolve the immediate predecessor first (before skipping selectors)
        # so we can detect if it is a compareDatasets guard.
        immediate_pred_id = self._find_predecessor_id(n8n_node_name)

        # ── compareDatasets downstream field special case ─────────────────────
        # If this n8n node is directly downstream of a compareDatasets node,
        # we know exactly which Code node field to reference (e.g. "matched",
        # "only_a").  This is resolved from n8n_connections at node-conversion
        # time, before _convert_connections runs, so it is always available.
        if n8n_node_name in self.compare_datasets_downstream_fields:
            cd_code_id, cd_field = self.compare_datasets_downstream_fields[n8n_node_name]
            return {
                param_key: {
                    "type": "ref",
                    "content": [cd_code_id, cd_field],
                    "extra": {"index": 0},
                }
            }

        pred_id = self._find_data_predecessor_id(n8n_node_name)
        if not pred_id:
            return {}
        # ── compareDatasets guard Selector special case ───────────────────────
        # immediate_pred_id is the guard Selector; pred_id is the Code node.
        # Use the port-specific field rather than the generic "result".
        if (immediate_pred_id
                and immediate_pred_id in self.compare_datasets_port_fields):
            port_field = self.compare_datasets_port_fields[immediate_pred_id]
            return {
                param_key: {
                    "type": "ref",
                    "content": [pred_id, port_field],
                    "extra": {"index": 0},
                }
            }
        
        output_field = self._get_primary_output_field(pred_id)
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
    # =========================================================================
    # DATA TRANSFORM DISPATCH TABLE
    # Maps n8n node type → handler method name.  To add a new Data Transform
    # node: (1) add one entry here, (2) write the _convert_X_to_code method.
    # No changes required anywhere else in _convert_code_node.
    # =========================================================================
    DATA_TRANSFORM_HANDLERS: Dict[str, str] = {
        # Set / passthrough
        "n8n-nodes-base.set": "_convert_set_to_code",
        "n8n-nodes-base.readWriteFile": "_convert_read_write_file_to_code",
        # Collection transforms
        "n8n-nodes-base.sort": "_convert_sort_to_code",
        "n8n-nodes-base.limit": "_convert_limit_to_code",
        "n8n-nodes-base.removeDuplicates": "_convert_remove_duplicates_to_code",
        "n8n-nodes-base.aggregate": "_convert_aggregate_to_code",
        # Expansion transforms
        "n8n-nodes-base.splitOut": "_convert_split_out_to_code",
        "n8n-nodes-base.itemLists": "_convert_item_lists_to_code",
        # Side-effect / control
        "n8n-nodes-base.noOp": "_convert_no_op_to_code",
        "n8n-nodes-base.wait": "_convert_wait_to_code",
        "n8n-nodes-base.respondToWebhook": "_convert_respond_to_webhook_to_code",
        "n8n-nodes-base.stopAndError": "_convert_stop_and_error_to_code",
        # Format / transformation
        "n8n-nodes-base.html": "_convert_html_to_code",
        "n8n-nodes-base.markdown": "_convert_markdown_to_code",
        "n8n-nodes-base.xml": "_convert_xml_to_code",
        "n8n-nodes-base.crypto": "_convert_crypto_to_code",
        "n8n-nodes-base.dateTime": "_convert_date_time_to_code",
        "n8n-nodes-base.compression": "_convert_compression_to_code",
        # File I/O
        "n8n-nodes-base.readBinaryFiles": "_convert_read_binary_files_to_code",
        "n8n-nodes-base.writeBinaryFile": "_convert_write_binary_file_to_code",
        "n8n-nodes-base.spreadsheetFile": "_convert_spreadsheet_file_to_code",
        "n8n-nodes-base.convertToFile": "_convert_convert_to_file_to_code",
        "n8n-nodes-base.extractFromFile": "_convert_extract_from_file_to_code",
    }

    # Maps each data-transform node type to the output style produced by its handler.
    # "list"  -> returns {"items": <list>, "result": <list>}  -- both typed as array
    # "field" -> returns a flat dict of named fields plus "result"
    # Absence means no predictable structured output (noOp, wait, etc.)
    DATA_TRANSFORM_OUTPUT_STYLES: Dict[str, str] = {
        "n8n-nodes-base.sort": "list",
        "n8n-nodes-base.limit": "list",
        "n8n-nodes-base.removeDuplicates": "list",
        "n8n-nodes-base.splitOut": "list",
        "n8n-nodes-base.itemLists": "list",
        "n8n-nodes-base.noOp": "list",
        "n8n-nodes-base.aggregate": "field",
        "n8n-nodes-base.html": "field",
        "n8n-nodes-base.markdown": "field",
        "n8n-nodes-base.xml": "field",
        "n8n-nodes-base.crypto": "field",
        "n8n-nodes-base.dateTime": "field",
        "n8n-nodes-base.compression": "field",
        "n8n-nodes-base.readWriteFile": "field",
        "n8n-nodes-base.spreadsheetFile": "field",
        "n8n-nodes-base.convertToFile": "field",
        "n8n-nodes-base.extractFromFile": "field",
    }
    N8N_OPERATOR_MAP: Dict[str, str] = {
    # generic equality
    "equals": "eq",
    "notEquals": "neq",
    "equal": "eq",
    "notEqual": "neq",
    # boolean
    "true": "eq",      # paired with right=true
    "false": "neq",     # paired with right=false
    "exists": "is_not_empty",    # paired with right=null
    "notExists": "is_empty", # paired with right=null
    # numeric
    "gt": "gt",
    "gte": "gte",
    "lt": "lt",
    "lte": "lte",
    "smaller": "lt",
    "smallerEqual": "lte",
    "larger": "gt",
    "largerEqual": "gte",
    # string
    "contains": "contains",
    "notContains": "not_contains",
    "startsWith": "starts_with",
    "endsWith": "ends_with",
    "regex": "regex",
    "empty": "is_empty",
    "notEmpty": "is_not_empty",
}

    def map_n8n_operator(self, n8n_op: Any) -> Tuple[str, Any]:
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
            jiuwen_op, right_override = self.map_n8n_operator(n8n_op)

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
            # Resolve the actual primary output field of the predecessor so the
            # condition left-side ref points to a field that really exists.
            # Fall back to "value" only when no predecessor is available.
            placeholder_field = "value"
            if predecessor_id:
                resolved = self._get_primary_output_field(predecessor_id)
                if resolved:
                    placeholder_field = resolved

            # Also register the field in inputParameters so the node knows
            # where to read the value from (previously this dict was left empty,
            # causing "input is undefined" in the target runtime).
            if predecessor_id:
                input_parameters[placeholder_field] = {
                    "type": "ref",
                    "content": [predecessor_id, placeholder_field],
                    "extra": {"index": 0}
                }

            jiuwen_conditions.append({
                "left": {"type": "ref", "content": [predecessor_id or "", placeholder_field]},
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

        Walks the full predecessor chain (not just one extra step) until it finds
        a node whose declared output properties contain *condition_field*.
        This is necessary when pass-through nodes (noOp, wait, etc.) sit between
        the IF node and the node that actually produces the field — those nodes
        only declare 'result'/'waited' etc. in their schemas, not the upstream
        data fields they forward.

        Search order:
        1. Walk back through predecessors until the field is found.
        2. Fallback to immediate predecessor so the ref is never empty.
        """
        if not immediate_predecessor_id:
            return None

        visited: set = set()
        current_id: Optional[str] = immediate_predecessor_id

        while current_id and current_id not in visited:
            visited.add(current_id)
            node = next(
                (n for n in self.openjiuwen_nodes if n["id"] == current_id), None
            )
            if node:
                props = node.get("data", {}).get("outputs", {}).get("properties", {})
                if condition_field in props:
                    return current_id

            # Resolve the n8n name for this jiuwen id so we can walk one step back
            n8n_name = next(
                (name for name, jid in self.node_id_map.items() if jid == current_id),
                None,
            )
            if n8n_name:
                current_id = self._find_predecessor_id(n8n_name)
            else:
                break

        # Fallback — return immediate predecessor so the schema at least has a ref
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
                    cleaned = []
                    for f in fields:
                        if f and not f.startswith('_') and f not in skip:
                            cleaned.append(f)

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
                    cleaned = []
                    for f in fields:
                        if f and not f.startswith('_') and f not in {'json'}:
                            cleaned.append(f)
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
                entry: Dict[str, Any] = {'type': ftype, 'extra': {'index': idx}}
                # OpenJiuwen requires object-typed outputs to carry a properties
                # sub-schema; omitting it causes a validation error at runtime.
                if ftype == 'object':
                    entry['properties'] = {}
                properties[ffield] = entry
        required = ['result'] + [f for f in extra_fields if f != 'result']
        return {'type': 'object', 'properties': properties, 'required': required}

    # =========================================================================
    # STICKY NOTE CONVERSION
    # =========================================================================

    def _convert_sticky_note(self, n8n_node: Dict) -> Dict:
        """
        Convert n8n stickyNote to an OpenJiuwen note (type 99).

        n8n format:
            {"type": "n8n-nodes-base.stickyNote",
             "position": [x, y],
             "parameters": {"content": "text", "width": 240, "height": 150}}

        OpenJiuwen format:
            {"id": "<uuid>", "type": "99",
             "meta": {"position": {"x": x, "y": y}},
             "data": {"size": {"width": 240, "height": 150}, "note": "text"}}

        Sticky notes are UI-only: they carry no edges and are never referenced
        by other nodes, so they bypass the regular node_id_map / x_pos pipeline.

        COORDINATE ALIGNMENT
        ────────────────────
        The trigger node is always repositioned to (180, 34) in Jiuwen regardless
        of where it lived in n8n.  All other nodes keep their raw n8n coordinates.
        To keep sticky notes spatially consistent with the Start node we apply the
        same translation delta:
            delta = (180 - trigger.x, 34 - trigger.y)
        When there is no trigger the raw n8n position is used as-is.
        """
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [0, 0])

        # n8n stores content as "content"; fall back to "name" when absent
        note_text = params.get("content", n8n_node.get("name", ""))

        # Dimensions — n8n defaults are 240 x 160
        width = int(params.get("width", 240))
        height = int(params.get("height", 160))

        raw_x = position[0] if len(position) > 0 else 0
        raw_y = position[1] if len(position) > 1 else 0

        # Apply the same coordinate offset used for the Start (trigger) node so
        # that sticky notes maintain their relative position on the canvas.
        if self.trigger_node:
            trig_pos = self.trigger_node.get("position", [180, 34])
            trig_x = trig_pos[0] if len(trig_pos) > 0 else 180
            trig_y = trig_pos[1] if len(trig_pos) > 1 else 34
            final_x = raw_x + (180 - trig_x)
            final_y = raw_y + (34 - trig_y)
        else:
            final_x, final_y = raw_x, raw_y

        note_id = self.id_gen.next_id("note")

        return {
            "id": note_id,
            "type": "99",
            "meta": {
                "position": {"x": final_x, "y": final_y}
            },
            "data": {
                "size": {"width": width, "height": height},
                "note": note_text,
            },
        }

    # =========================================================================
    # CODE NODE CONVERSION
    # =========================================================================

    def _convert_code_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Code/Function/Set to OpenJiuwen Code component."""
        node_type = n8n_node.get("type", "")
        node_name = n8n_node.get("name", "")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        
        # Determine language and extract code.
        # Default is Python — the vast majority of handlers (all Data Transform
        # nodes + fallback) generate Python.  Only the two native JS node types
        # override this to "javascript".
        language = "python"
        code = ""
        
        if node_type == "n8n-nodes-base.code":
            lang_param = params.get("language", "javaScript").lower()
            if lang_param in ["javascript", "js"]:
                language = "javascript"
                code = params.get("jsCode", "")
            else:
                code = params.get("pythonCode", "")
        elif node_type in ["n8n-nodes-base.function", "n8n-nodes-base.functionItem"]:
            language = "javascript"
            code = params.get("functionCode", "") or params.get("code", "")
        elif node_type == "n8n-nodes-base.set":
            # Convert Set node to Python code with actual implementation
            language = "python"
            code = self._convert_set_to_code(n8n_node)
        elif node_type in ("n8n-nodes-base.readWriteFile", "n8n-nodes-base.readBinaryFile"):
            # Convert Read/Write File node (and legacy binary-read) to Python code
            language = "python"
            code = self._convert_read_write_file_to_code(n8n_node)
        elif node_type == "n8n-nodes-base.writeBinaryFile":
            # Legacy binary write node — 'fileName' holds the destination path.
            # Normalise to the shape _convert_read_write_file_to_code expects.
            normalised = dict(n8n_node)
            norm_params = dict(n8n_node.get("parameters", {}))
            if "fileName" in norm_params and "filePath" not in norm_params:
                norm_params["filePath"] = norm_params.pop("fileName")
            norm_params["operation"] = "write"
            normalised["parameters"] = norm_params
            language = "python"
            code = self._convert_read_write_file_to_code(normalised)
        elif node_type in self.DATA_TRANSFORM_HANDLERS:
            # All Data Transform node types are registered in DATA_TRANSFORM_HANDLERS.
            # To add a new type: add one entry to that dict + write the handler method.
            handler = getattr(self, self.DATA_TRANSFORM_HANDLERS[node_type])
            code = handler(n8n_node)
        else:
            # Fallback for other node types
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
                "// Convert n8n [{json:{...}}, ...] array format to OpenJiuwen {items:[...], result:[...]}\n"
                "  let _items;\n"
                "  if (Array.isArray(_n8nResult) && _n8nResult.length > 0"
                " && _n8nResult[0] !== null && typeof _n8nResult[0] === 'object'"
                " && 'json' in _n8nResult[0]) {\n"
                "    _items = _n8nResult.map(function(i) { return i.json || i; });\n"
                "  } else if (Array.isArray(_n8nResult)) {\n"
                "    _items = _n8nResult;\n"
                "  } else if (_n8nResult && typeof _n8nResult === 'object') {\n"
                "    _items = [_n8nResult];\n"
                "  } else {\n"
                "    _items = [];\n"
                "  }\n"
                "  const _out = { items: _items, result: _items };\n"
                "  if (_items.length > 0 && _items[0] && typeof _items[0] === 'object') {\n"
                "    Object.assign(_out, _items[0]);\n"
                "  }\n"
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

        # Build outputs.
        # For data-transform nodes we know exactly what the handler returns, so
        # we build the schema directly instead of trying to parse generated code.
        transform_style = self.DATA_TRANSFORM_OUTPUT_STYLES.get(node_type)
        if transform_style == "list":
            # Sort / Limit / Remove Duplicates / SplitOut / ItemLists
            # -> {"items": <list-of-objects>, "result": <list-of-objects>}
            outputs = {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Sorted/filtered item list",
                        "extra": {"index": 0}
                    },
                    "result": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "代码执行结果",
                        "extra": {"index": 1}
                    }
                },
                "required": ["items", "result"]
            }
        elif transform_style == "field":
            # Aggregate / HTML / Markdown / XML / Crypto / DateTime / Compression
            # -> flat dict of named fields + "result" (object)
            extra_fields = self._extract_return_field_names(n8n_node, language)
            field_types = self._extract_return_field_types(n8n_node, language)
            # For aggregate the named fields are arrays; everything else is string.
            if node_type == "n8n-nodes-base.aggregate":
                params = n8n_node.get("parameters", {})
                agg_fields = []
                for fa in params.get("fieldsToAggregate", {}).get("fieldToAggregate", []):
                    if fa.get("fieldToAggregate"):
                        agg_fields.append(fa.get("fieldToAggregate", ""))
                agg_types = {f: "array" for f in agg_fields}
                agg_types.update(field_types)
                outputs = self._build_code_outputs(
                    agg_fields if agg_fields else extra_fields, agg_types
                )
            else:
                outputs = self._build_code_outputs(extra_fields, field_types)
        else:
            # Native Code / Function nodes and everything else.
            # If we applied the JS wrapper the runtime output is always
            # {items: array, result: array, ...firstItemFields}.
            # Override result+items to array so downstream nodes type-check correctly.
            extra_fields = self._extract_return_field_names(n8n_node, language)
            field_types = self._extract_return_field_types(n8n_node, language)
            outputs = self._build_code_outputs(extra_fields, field_types)
            if language == "javascript":
                # The JS wrapper always produces {items:[...], result:[...], ...fields}.
                # Patch result and add items as arrays; keep individual scalar fields.
                props = outputs.setdefault("properties", {})
                props["items"] = {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "All output items",
                    "extra": {"index": 0}
                }
                props["result"] = {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "代码执行结果",
                    "extra": {"index": 1}
                }
                # Re-index any extra scalar fields starting from 2
                for i, fname in enumerate(extra_fields, start=2):
                    if fname not in ("result", "items") and fname in props:
                        props[fname]["extra"] = {"index": i}
                req = outputs.get("required", [])
                if "items" not in req:
                    req.insert(0, "items")
                if "result" not in req:
                    req.insert(1, "result")
                outputs["required"] = req

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
            '    import datetime, json as _json',
            '    # Get input data',
            '    _raw = args.params.get("input", {}) if hasattr(args, "params") else {}',
            '    if isinstance(_raw, str):',
            '        try: _raw = _json.loads(_raw)',
            '        except Exception: _raw = {}',
            '    input_data = _raw if isinstance(_raw, dict) else (_raw[0] if isinstance(_raw, list) and _raw '
            '                 and isinstance(_raw[0], dict) else {})',
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
            elif isinstance(values_data, dict):
                if "values" in values_data:
                    assignments = values_data["values"]
                else:
                    # n8n v1 format: values.{type}: [{name, value}, ...]
                    # e.g. {"number": [{"name": "score", "value": 75}]}
                    for value_type in ["string", "number", "boolean", "array", "object"]:
                        if value_type in values_data:
                            type_values = values_data[value_type]
                            if isinstance(type_values, list):
                                for item in type_values:
                                    item_copy = dict(item)
                                    item_copy["type"] = value_type
                                    assignments.append(item_copy)
        
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

        # Bare $json — the entire input object (e.g. summary = {{ $json }})
        if re.match(r'^\$json$', inner.strip()):
            return 'dict(input_data)'

        # $now / $today date helpers  (e.g. {{ $now.toISO() }})
        # NOTE: _convert_set_to_code injects `import datetime` at function top.
        if re.match(r'^\$now', inner.strip()) or re.match(r'^\$today', inner.strip()):
            return 'datetime.datetime.now(datetime.timezone.utc).isoformat()'

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
    # COMPARE DATASETS NODE (Code + 4 independent guard Selectors)
    # =========================================================================

    def _convert_compare_datasets_node(
        self, n8n_node: Dict, x_pos: int
    ) -> Tuple[Dict, List[Dict]]:
        """
        Convert n8n compareDatasets to one Code node + four independent guard
        Selector nodes, one per n8n output port.

        Returns
        -------
        (code_node, [selector_port0, selector_port1, selector_port2, selector_port3])
        """
        node_name = n8n_node.get("name", "Compare Datasets")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        px = position[0] if len(position) > 0 else x_pos
        py = position[1] if len(position) > 1 else 34

        code_id = self.id_gen.next_id("code")

        # ── Extract merge-by field pairs ──────────────────────────────────────
        merge_fields_raw = params.get("mergeByFields", {}).get("values", [])
        merge_fields = []
        for f in merge_fields_raw:
            merge_fields.append({"input1": f.get("field1", ""), "input2": f.get("field2", "")})
        merge_fields_repr = repr(merge_fields)

        # ── Code body ─────────────────────────────────────────────────────────
        code_body = (
            'def main(args):\n'
            f'    """Converted from n8n Compare Datasets node: {node_name}\n'
            '    Computes four output sets mirroring n8n\'s four output ports:\n'
            '      matched    (port 0) — items whose key exists in both A and B\n'
            '      only_a     (port 1) — items whose key exists only in A\n'
            '      only_b     (port 2) — items whose key exists only in B\n'
            '      union_excl (port 3) — only_a + only_b (symmetric difference)\n'
            '    Input A is received as the "input_a" parameter (n8n input port 0).\n'
            '    Input B is received as the "input_b" parameter (n8n input port 1).\n'
            '    """\n'
            '    params = args.params if hasattr(args, "params") else {}\n'
            '    raw_a = params.get("input_a", [])\n'
            '    raw_b = params.get("input_b", [])\n'
            '    items_a = raw_a if isinstance(raw_a, list) else [raw_a] if raw_a else []\n'
            '    items_b = raw_b if isinstance(raw_b, list) else [raw_b] if raw_b else []\n'
            f'    merge_fields = {merge_fields_repr}\n'
            '    def get_key(item, fields, side):\n'
            '        if not fields:\n'
            '            return repr(sorted(item.items()) if isinstance(item, dict) else item)\n'
            '        return tuple(\n'
            '            item.get(f[side], "") if isinstance(item, dict) else ""\n'
            '            for f in fields\n'
            '        )\n'
            '    keys_a = {\n'
            '        get_key(item, merge_fields, "input1"): item\n'
            '        for item in items_a if isinstance(item, dict)\n'
            '    }\n'
            '    keys_b = {\n'
            '        get_key(item, merge_fields, "input2"): item\n'
            '        for item in items_b if isinstance(item, dict)\n'
            '    }\n'
            '    matched, only_a, only_b = [], [], []\n'
            '    for key, item in keys_a.items():\n'
            '        if key in keys_b:\n'
            '            merged = dict(keys_b[key])\n'
            '            merged.update(item)\n'
            '            matched.append(merged)\n'
            '        else:\n'
            '            only_a.append(item)\n'
            '    for key, item in keys_b.items():\n'
            '        if key not in keys_a:\n'
            '            only_b.append(item)\n'
            '    union_excl = only_a + only_b\n'
            '    result = {\n'
            '        "matched": matched,\n'
            '        "only_a": only_a,\n'
            '        "only_b": only_b,\n'
            '        "union_excl": union_excl,\n'
            '        "matched_count": len(matched),\n'
            '        "only_a_count": len(only_a),\n'
            '        "only_b_count": len(only_b),\n'
            '        "union_excl_count": len(union_excl),\n'
            '    }\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

        # ── Code node outputs schema ──────────────────────────────────────────
        outputs = {
            "type": "object",
            "properties": {
                "result": {"type": "object", "extra": {"index": 0}},
                "matched": {"type": "array", "extra": {"index": 1}},
                "only_a": {"type": "array", "extra": {"index": 2}},
                "only_b": {"type": "array", "extra": {"index": 3}},
                "union_excl": {"type": "array", "extra": {"index": 4}},
                "matched_count": {"type": "number", "extra": {"index": 5}},
                "only_a_count": {"type": "number", "extra": {"index": 6}},
                "only_b_count": {"type": "number", "extra": {"index": 7}},
                "union_excl_count": {"type": "number", "extra": {"index": 8}},
            },
            "required": ["result", "matched", "only_a", "only_b", "union_excl"],
        }

        # ── Resolve both input predecessors by n8n input port index ──────────
        pred_a_id = self._find_predecessor_by_input_index(node_name, 0)
        pred_b_id = self._find_predecessor_by_input_index(node_name, 1)
        input_parameters: Dict[str, Any] = {}
        if pred_a_id:
            field_a = self._get_primary_output_field(pred_a_id)
            input_parameters["input_a"] = {
                "type": "ref",
                "content": [pred_a_id, field_a or "result"],
                "extra": {"index": 0},
            }
        if pred_b_id:
            field_b = self._get_primary_output_field(pred_b_id)
            input_parameters["input_b"] = {
                "type": "ref",
                "content": [pred_b_id, field_b or "result"],
                "extra": {"index": 1},
            }

        code_node: Dict = {
            "id": code_id,
            "type": str(ComponentType.COMPONENT_TYPE_CODE),
            "meta": {"position": {"x": px, "y": py}},
            "data": {
                "title": node_name,
                "inputs": {
                    "language": "python",
                    "code": code_body,
                    "inputParameters": input_parameters,
                },
                "outputs": outputs,
                "exceptionConfig": {
                    "retryTimes": 3,
                    "timeoutSeconds": 30,
                    "processType": "break",
                    "executeStep": {"defaultStep": "0", "errorStep": "1"},
                },
            },
        }

        # ── Build 4 independent guard Selectors ───────────────────────────────
        # Each Selector is sourced directly from the Code node (not from each
        # other — no cascade).  Branch 0 fires when the set is non-empty;
        # Branch 1 (else) lets _ensure_edge_connections wire it to End/skip.
        #
        # Port 3 uses OR logic (logic=1) because union_excl is non-empty when
        # EITHER only_a OR only_b has items.

        def _ref(field_name: str) -> Dict:
            return {"type": "ref", "content": [code_id, field_name]}

        def _const(val: int) -> Dict:
            return {"type": "constant", "content": val, "schema": {"type": "number"}}

        port_defs = [
            # (port_index, title_suffix, input_param_key, condition_field,
            #  count_field, logic, extra_condition)
            (0, "matched", "matched_count", "matched_count", 2, None),
            (1, "only_a", "only_a_count", "only_a_count", 2, None),
            (2, "only_b", "only_b_count", "only_b_count", 2, None),
            # Port 3: only_a_count > 0 OR only_b_count > 0
            (3, "union_excl", "only_a_count", "only_a_count", 1,
             {"left": _ref("only_b_count"), "operator": ">", "right": _const(0)}),
        ]

        selector_nodes: List[Dict] = []
        for port_idx, field_name, param_key, cond_field, logic, extra_cond in port_defs:
            sel_id = self.id_gen.next_id("selector")

            branch_id_true = f"branch_{uuid.uuid4().hex[:5]}"
            branch_id_skip = f"branch_{uuid.uuid4().hex[:5]}"

            primary_cond = {
                "left": _ref(cond_field),
                "operator": ">",
                "right": _const(0),
            }
            conditions = [primary_cond]
            if extra_cond:
                conditions.append(extra_cond)

            ip: Dict[str, Any] = {
                param_key: {
                    "type": "ref",
                    "content": [code_id, param_key],
                    "extra": {"index": 0},
                }
            }
            if extra_cond and port_idx == 3:
                # Port 3 also references only_b_count for the OR clause
                ip["only_b_count"] = {
                    "type": "ref",
                    "content": [code_id, "only_b_count"],
                    "extra": {"index": 1},
                }

            sel_node: Dict = {
                "id": sel_id,
                "type": str(ComponentType.COMPONENT_TYPE_IF),
                "meta": {"position": {"x": px + 230 + port_idx * 230, "y": py}},
                "data": {
                    "title": f"{node_name} – {field_name} guard",
                    "inputs": {"inputParameters": ip},
                    "branches": [
                        {
                            # Branch 0: set is non-empty → run the downstream consumer
                            "conditions": conditions,
                            "logic": logic,
                            "branchId": branch_id_true,
                        },
                        {
                            # Branch 1: set is empty → skip (wired to End by
                            # _ensure_edge_connections)
                            "conditions": [],
                            "logic": 2,
                            "branchId": branch_id_skip,
                        },
                    ],
                },
            }
            selector_nodes.append(sel_node)

        self.report.add_warning(
            f"compareDatasets '{node_name}': converted to 1 Code node + "
            f"4 independent guard Selectors (one per n8n output port). "
            f"Port 0 (matched) → selector index 0; "
            f"Port 1 (only_a)  → selector index 1; "
            f"Port 2 (only_b)  → selector index 2; "
            f"Port 3 (union_excl, OR logic) → selector index 3. "
            f"Each guard's Branch 1 is wired to End when the set is empty."
        )

        return code_node, selector_nodes

    # =========================================================================
    # DATA TRANSFORM CODE-GENERATION HELPERS
    # =========================================================================

    @staticmethod
    def _wrap_transform_code(
        node_name: str,
        label: str,
        core_lines: str,
        output_style: str = "field",
    ) -> str:
        """
        Wrap core_lines with the standard def main(args): header and footer.

        Every generated transform function shares the same header::

            def main(args):
                # docstring: Converted from n8n {label} node: {node_name}
                input_data = args.params.get("input", {}) if hasattr(args, "params") else {}

        output_style controls the footer:
          "field" — result is a dict; exposes every key plus "result":
                      _output = dict(result) if isinstance(result, dict) else {"data": result}
                      _output["result"] = result
                      return _output
          "list"  — result is a list; exposes "items" alias + "result":
                      _output = {"items": result, "result": result}
                      return _output

        core_lines is the body between input_data and the footer, already
        4-space-indented.  It is responsible for setting `result`.
        """
        header = (
            'def main(args):\n'
            f'    """Converted from n8n {label} node: {node_name}"""\n'
            '    _raw_params = args.params if hasattr(args, "params") else {}\n'
            '    if isinstance(_raw_params, str):\n'
            '        import json as _json\n'
            '        try:\n'
            '            _raw_params = _json.loads(_raw_params)\n'
            '        except Exception:\n'
            '            _raw_params = {}\n'
            '    input_data = _raw_params.get("input", _raw_params) if isinstance(_raw_params, dict) else {}\n'
            '    if isinstance(input_data, str):\n'
            '        import json as _json\n'
            '        try:\n'
            '            input_data = _json.loads(input_data)\n'
            '        except Exception:\n'
            '            pass\n'
            '    if not isinstance(input_data, (dict, list)):\n'
            '        input_data = {}\n'
        )
        if output_style == "list":
            footer = (
                '    _output = {"items": result, "result": result}\n'
                '    return _output\n'
            )
        else: # "field"
            footer = (
                '    _output = dict(result) if isinstance(result, dict) else {"data": result}\n'
                '    _output["result"] = result\n'
                '    return _output\n'
            )
        return header + core_lines + footer

    @staticmethod
    def _extract_items_lines(flat: bool = False) -> str:
        """
        Return the standard 4-space-indented items-extraction snippet.

        flat=False (default) — tolerates both list and dict inputs:
            items = (
                input_data if isinstance(input_data, list)
                else input_data.get("items", [input_data])
            )

        flat=True — treats any non-list as a single-element list (used by
        splitOut which always works item-by-item):
            items = input_data if isinstance(input_data, list) else [input_data]
        """
        if flat:
            return '    items = input_data if isinstance(input_data, list) else [input_data]\n'
        return (
            '    items = (\n'
            '        input_data if isinstance(input_data, list)\n'
            '        else input_data.get("items", [input_data])\n'
            '    )\n'
        )

    # =========================================================================
    # DATA TRANSFORM NODE CODE GENERATORS
    # =========================================================================

    # ── Collection transforms ─────────────────────────────────────────────────

    def _convert_sort_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Sort node to Python code."""
        node_name = n8n_node.get("name", "Sort")
        params = n8n_node.get("parameters", {})
        sort_ui = params.get("sortFieldsUi", {})
        # n8n ≥1.64 / 2.x uses "sortField"; older builds used "values"
        sort_fields = sort_ui.get("sortField") or sort_ui.get("values") or []
        # Normalise order values: "ascending"/"descending" → "asc"/"desc"
        for sf in sort_fields:
            order = sf.get("order", "asc").lower()
            if order == "ascending":
                sf["order"] = "asc"
            elif order == "descending":
                sf["order"] = "desc"
        if not sort_fields:
            field_name = params.get("fieldName", "")
            order = params.get("order", "asc")
            if field_name:
                sort_fields = [{"fieldName": field_name, "order": order}]
        core = (
            self._extract_items_lines()
            + f'    sort_fields = {repr(sort_fields)}\n'
            + '    result = list(items)\n'
            + '    for sf in reversed(sort_fields):\n'
            + '        field = sf.get("fieldName", "")\n'
            + '        reverse = sf.get("order", "asc").lower() == "desc"\n'
            + '        if field:\n'
            + '            result.sort(\n'
            + '                key=lambda x: (x.get(field) is None, x.get(field, ""))\n'
            + '                    if isinstance(x, dict) else (False, x),\n'
            + '                reverse=reverse,\n'
            + '            )\n'
        )
        return self._wrap_transform_code(node_name, "Sort", core, output_style="list")

    def _convert_limit_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Limit node to Python code."""
        node_name = n8n_node.get("name", "Limit")
        params = n8n_node.get("parameters", {})
        max_items = params.get("maxItems", 1)
        keep = params.get("keep", "firstItems")
        core = (
            self._extract_items_lines()
            + f'    max_items = {max_items}\n'
            + f'    keep = "{keep}"\n'
            + '    result = list(items[-max_items:]) if keep == "lastItems" else list(items[:max_items])\n'
        )
        return self._wrap_transform_code(node_name, "Limit", core, output_style="list")

    def _convert_remove_duplicates_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Remove Duplicates node to Python code."""
        node_name = n8n_node.get("name", "Remove Duplicates")
        params = n8n_node.get("parameters", {})
        compare_type = params.get("compare", "allFields")
        # n8n ≥1.64 / 2.x (typeVersion 2): fieldsToCompare.fields[].fieldName
        # n8n <1.64 (typeVersion 1): fields.values[].fieldName
        raw_fields = (
            params.get("fieldsToCompare", {}).get("fields")
            or params.get("fields", {}).get("values")
            or []
        )
        compare_fields = [f.get("fieldName", "") for f in raw_fields if f.get("fieldName")]
        core = (
            self._extract_items_lines()
            + f'    compare_type = "{compare_type}"\n'
            + f'    compare_fields = {repr(compare_fields)}\n'
            + '    seen, result = [], []\n'
            + '    for item in items:\n'
            + '        if not isinstance(item, dict):\n'
            + '            if item not in seen:\n'
            + '                seen.append(item)\n'
            + '                result.append(item)\n'
            + '            continue\n'
            + '        if compare_type == "selectedFields" and compare_fields:\n'
            + '            key = tuple(item.get(f) for f in compare_fields)\n'
            + '        else:\n'
            + '            key = tuple(sorted(item.items()))\n'
            + '        if key not in seen:\n'
            + '            seen.append(key)\n'
            + '            result.append(item)\n'
        )
        return self._wrap_transform_code(node_name, "Remove Duplicates", core, output_style="list")

    def _convert_aggregate_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Aggregate node to Python code."""
        node_name = n8n_node.get("name", "Aggregate")
        params = n8n_node.get("parameters", {})
        aggregate_type = params.get("aggregate", "aggregateAllItemData")
        raw_fields = params.get("fieldsToAggregate", {}).get("fieldToAggregate", [])
        fields = [f.get("fieldToAggregate", "") for f in raw_fields if f.get("fieldToAggregate")]
        core = (
            self._extract_items_lines()
            + f'    aggregate_type = "{aggregate_type}"\n'
            + f'    fields = {repr(fields)}\n'
            + '    if aggregate_type == "aggregateAllItemData":\n'
            + '        result = {"data": [item for item in items if isinstance(item, dict)]}\n'
            + '    else:\n'
            + '        result = {}\n'
            + '        for field in fields:\n'
            + '            result[field] = [\n'
            + '                item.get(field) for item in items\n'
            + '                if isinstance(item, dict) and field in item\n'
            + '            ]\n'
        )
        return self._wrap_transform_code(node_name, "Aggregate", core, output_style="field")

    # ── Expansion transforms ──────────────────────────────────────────────────

    def _convert_split_out_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Split Out node to Python code."""
        node_name = n8n_node.get("name", "Split Out")
        params = n8n_node.get("parameters", {})
        field_name = self._convert_expression(params.get("fieldToSplitOut", ""))
        include = params.get("include", "noOtherFields")
        raw_extra = params.get("fieldsToInclude", {}).get("fields", [])
        extra_fields = [f.get("fieldName", "") for f in raw_extra if f.get("fieldName")]
        core = (
            self._extract_items_lines(flat=True)
            + f'    field = "{field_name}"\n'
            + f'    include = "{include}"\n'
            + f'    extra_fields = {repr(extra_fields)}\n'
            + '    result = []\n'
            + '    for item in items:\n'
            + '        if not isinstance(item, dict):\n'
            + '            result.append(item)\n'
            + '            continue\n'
            + '        array_val = item.get(field, [])\n'
            + '        if not isinstance(array_val, list):\n'
            + '            array_val = [array_val]\n'
            + '        for element in array_val:\n'
            + '            if include == "allOtherFields":\n'
            + '                new_item = {k: v for k, v in item.items() if k != field}\n'
            + '            elif include == "selectedOtherFields" and extra_fields:\n'
            + '                new_item = {k: item[k] for k in extra_fields if k in item}\n'
            + '            else:\n'
            + '                new_item = {}\n'
            + '            new_item[field] = element\n'
            + '            result.append(new_item)\n'
        )
        return self._wrap_transform_code(node_name, "Split Out", core, output_style="list")

    def _convert_item_lists_to_code(self, n8n_node: Dict) -> str:
        """
        Convert n8n Item Lists node to Python code.

        Item Lists is a legacy multi-operation node.  We generate a dispatcher
        that handles: splitOutItems, aggregateItems, removeDuplicates, summarize,
        sort, limit.
        """
        node_name = n8n_node.get("name", "Item Lists")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "splitOutItems")
        field_to_split = params.get("fieldToSplitOut", "")
        raw_cmp = params.get("fieldsToCompare", {}).get("fields", [])
        compare_fields = [f.get("fieldName", "") for f in raw_cmp if f.get("fieldName")]
        sort_ui = params.get("sortFieldsUi", {})
        raw_sort = sort_ui.get("sortField") or sort_ui.get("values") or []
        sort_fields = []
        for f in raw_sort:
            sort_fields.append({
                "field": f.get("fieldName", ""),
                "order": "desc" if f.get("order", "asc").lower() in ("desc", "descending") else "asc",
            })
        max_items = params.get("maxItems", 1)
        raw_sum = params.get("fieldsToSummarize", {}).get("values", [])
        summarize_fields = []
        for f in raw_sum:
            summarize_fields.append({"field": f.get("field", f.get("fieldToSummarize", "")), 
                                     "aggregation": f.get("aggregation", "count")})
        core = (
            self._extract_items_lines()
            + f'    operation = "{operation}"\n'
            + f'    field_to_split = "{field_to_split}"\n'
            + f'    compare_fields = {repr(compare_fields)}\n'
            + f'    sort_fields = {repr(sort_fields)}\n'
            + f'    max_items = {max_items}\n'
            + f'    summarize_fields = {repr(summarize_fields)}\n'
            + '    result = []\n'
            + '    if operation == "splitOutItems":\n'
            + '        for item in items:\n'
            + '            if not isinstance(item, dict):\n'
            + '                result.append(item); continue\n'
            + '            arr = item.get(field_to_split, [])\n'
            + '            if not isinstance(arr, list):\n'
            + '                arr = [arr]\n'
            + '            for el in arr:\n'
            + '                new = dict(item); new[field_to_split] = el\n'
            + '                result.append(new)\n'
            + '    elif operation == "aggregateItems":\n'
            + '        merged = {}\n'
            + '        for item in items:\n'
            + '            if isinstance(item, dict):\n'
            + '                merged.update(item)\n'
            + '        result = [merged]\n'
            + '    elif operation == "removeDuplicates":\n'
            + '        seen = []\n'
            + '        for item in items:\n'
            + '            key = (\n'
            + '                tuple(item.get(f) for f in compare_fields)\n'
            + '                if (compare_fields and isinstance(item, dict))\n'
            + '                else (tuple(sorted(item.items())) if isinstance(item, dict) else item)\n'
            + '            )\n'
            + '            if key not in seen:\n'
            + '                seen.append(key); result.append(item)\n'
            + '    elif operation == "sort":\n'
            + '        result = list(items)\n'
            + '        for sf in reversed(sort_fields):\n'
            + '            f2, rev = sf.get("field", ""), sf.get("order", "asc").lower() == "desc"\n'
            + '            if f2:\n'
            + '                result.sort(\n'
            + '                    key=lambda x: (x.get(f2) is None, x.get(f2, ""))\n'
            + '                        if isinstance(x, dict) else (False, x),\n'
            + '                    reverse=rev,\n'
            + '                )\n'
            + '    elif operation == "limit":\n'
            + '        result = list(items)[:max_items]\n'
            + '    elif operation == "summarize":\n'
            + '        summary = {}\n'
            + '        for sf in summarize_fields:\n'
            + '            f3, agg = sf.get("field", ""), sf.get("aggregation", "count")\n'
            + '            vals = [item.get(f3) for item in items if isinstance(item, dict) and f3 in item]\n'
            + '            nums = [v for v in vals if isinstance(v, (int, float))]\n'
            + '            if   agg == "count": summary[f3] = len(vals)\n'
            + '            elif agg == "sum": summary[f3] = sum(nums)\n'
            + '            elif agg == "average": summary[f3] = sum(nums) / len(nums) if nums else 0\n'
            + '            elif agg == "min": summary[f3] = min(nums) if nums else None\n'
            + '            elif agg == "max": summary[f3] = max(nums) if nums else None\n'
            + '            elif agg == "countUnique": summary[f3] = len(set(str(v) for v in vals))\n'
            + '            else: summary[f3] = vals\n'
            + '        result = [summary]\n'
            + '    else:\n'
            + '        result = list(items)\n'
        )
        return self._wrap_transform_code(node_name, "Item Lists", core, output_style="list")

    # ── Side-effect / control nodes ───────────────────────────────────────────

    def _convert_no_op_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n No-Op node: pure pass-through, normalised to a list."""
        node_name = n8n_node.get("name", "No Operation")
        core = (
            '    items = (\n'
            '        input_data if isinstance(input_data, list)\n'
            '        else input_data.get("items", [input_data]) if isinstance(input_data, dict) and input_data\n'
            '        else []\n'
            '    )\n'
            '    result = list(items)\n'
        )
        return self._wrap_transform_code(node_name, "No Op", core, output_style="list")

    @staticmethod
    def _convert_wait_to_code(n8n_node: Dict) -> str:
        """Convert n8n Wait node to Python code (time.sleep, capped at 60 s)."""
        node_name = n8n_node.get("name", "Wait")
        params = n8n_node.get("parameters", {})
        resume = params.get("resume", "timeInterval")
        amount = params.get("amount", 1)
        unit = params.get("unit", "hours")
        return (
            'def main(args):\n'
            f'    """Converted from n8n Wait node: {node_name}"""\n'
            '    import time\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    resume = "{resume}"\n'
            f'    amount = {amount}\n'
            f'    unit = "{unit}"\n'
            '    unit_seconds = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}\n'
            '    if resume == "timeInterval":\n'
            '        wait_secs = amount * unit_seconds.get(unit, 3600)\n'
            '        time.sleep(min(wait_secs, 60))  # cap at 60 s\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {"data": input_data}\n'
            '    result["waited"] = True\n'
            '    result["resume"] = resume\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    def _convert_respond_to_webhook_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Respond to Webhook node to Python code."""
        node_name = n8n_node.get("name", "Respond to Webhook")
        params = n8n_node.get("parameters", {})
        respond_with = params.get("respondWith", "allIncomingItems")
        response_body = self._convert_expression(params.get("responseBody", ""))
        response_code = params.get("options", {}).get("responseCode", 200)
        safe_body = response_body.replace('"""', '\\"\\"\\"')
        return (
            'def main(args):\n'
            f'    """Converted from n8n Respond to Webhook node: {node_name}"""\n'
            '    import json\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    respond_with = "{respond_with}"\n'
            f'    response_code = {response_code}\n'
            f'    static_body = """{safe_body}"""\n'
            '    if respond_with == "text":\n'
            '        body = static_body or str(input_data)\n'
            '    elif respond_with == "json":\n'
            '        body = json.dumps(input_data)\n'
            '    elif respond_with == "noData":\n'
            '        body = ""\n'
            '    else:\n'
            '        body = json.dumps(input_data)\n'
            '    result = {\n'
            '        "responded": True,\n'
            '        "responseCode": response_code,\n'
            '        "body": body,\n'
            '        "data": input_data,\n'
            '    }\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    @staticmethod
    def _convert_stop_and_error_to_code(n8n_node: Dict) -> str:
        """Convert n8n Stop and Error node: raises RuntimeError unconditionally."""
        node_name = n8n_node.get("name", "Stop and Error")
        params = n8n_node.get("parameters", {})
        error_message = params.get("errorMessage", f"Workflow stopped at node: {node_name}")
        safe_msg = error_message.replace('"""', '\\"\\"\\"')
        return (
            'def main(args):\n'
            f'    """Converted from n8n Stop and Error node: {node_name}"""\n'
            f'    raise RuntimeError("[StopAndError] {safe_msg}")\n'
        )

    # ── Format / transformation nodes ─────────────────────────────────────────

    def _convert_html_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n HTML node (generate / extractHtmlContent) to Python code."""
        node_name = n8n_node.get("name", "HTML")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "generate")
        value = self._convert_expression(params.get("value", ""))
        destination_key = params.get("destinationKey", "html")
        source_key = params.get("sourceKey", "data")
        safe_value = value.replace('"""', '\\"\\"\\"')
        core = (
            '    import re, html\n'
            f'    operation = "{operation}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    if operation == "generate":\n'
            f'        result["{destination_key}"] = """{safe_value}"""\n'
            '    elif operation == "extractHtmlContent":\n'
            f'        raw = input_data.get("{source_key}", str(input_data))\n'
            '        text = re.sub(r"<[^>]+>", "", str(raw))\n'
            '        text = html.unescape(text).strip()\n'
            f'        result["{destination_key}"] = text\n'
        )
        return self._wrap_transform_code(node_name, "HTML", core, output_style="field")

    def _convert_markdown_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Markdown node (markdownToHtml / htmlToMarkdown) to Python code."""
        node_name = n8n_node.get("name", "Markdown")
        params = n8n_node.get("parameters", {})
        operation = params.get("mode", "markdownToHtml")
        html_param = self._convert_expression(params.get("html", ""))
        markdown_param = self._convert_expression(params.get("markdown", ""))
        destination_key = params.get("destinationKey", "data")
        safe_md = markdown_param.replace('"""', '\\"\\"\\"')
        safe_html = html_param.replace('"""', '\\"\\"\\"')
        core = (
            '    import re\n'
            f'    operation = "{operation}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    if operation == "markdownToHtml":\n'
            f'        md = """{safe_md}""" or input_data.get("markdown", str(input_data))\n'
            '        out = re.sub(r"^# (.+)$",   r"<h1>\\1</h1>", md,  flags=re.MULTILINE)\n'
            '        out = re.sub(r"^## (.+)$",  r"<h2>\\1</h2>", out, flags=re.MULTILINE)\n'
            '        out = re.sub(r"^### (.+)$", r"<h3>\\1</h3>", out, flags=re.MULTILINE)\n'
            r'        out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)' + '\n'
            r'        out = re.sub(r"\*(.+?)\*",     r"<em>\1</em>",         out)' + '\n'
            '        out = out.replace("\\n", "<br>")\n'
            f'        result["{destination_key}"] = out\n'
            '    else:\n'
            f'        htm = """{safe_html}""" or input_data.get("html", str(input_data))\n'
            '        txt = re.sub(r"<h[1-6]>(.+?)</h[1-6]>", r"# \\1\\n", htm, flags=re.IGNORECASE)\n'
            r'        txt = re.sub(r"<strong>(.+?)</strong>",  r"**\1**",   txt, flags=re.IGNORECASE)' + '\n'
            r'        txt = re.sub(r"<em>(.+?)</em>",          r"*\1*",     txt, flags=re.IGNORECASE)' + '\n'
            '        txt = re.sub(r"<br\\s*/?>", "\\n", txt, flags=re.IGNORECASE)\n'
            '        txt = re.sub(r"<[^>]+>", "", txt).strip()\n'
            f'        result["{destination_key}"] = txt\n'
        )
        return self._wrap_transform_code(node_name, "Markdown", core, output_style="field")

    def _convert_xml_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n XML node (xmlToJson / jsonToXml) to Python code."""
        node_name = n8n_node.get("name", "XML")
        params = n8n_node.get("parameters", {})
        operation = params.get("mode", "xmlToJson")
        data_key = params.get("dataPropertyName", "data")
        core = (
            '    import xml.etree.ElementTree as ET\n'
            f'    operation = "{operation}"\n'
            f'    data_key = "{data_key}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    def _xml_to_dict(el):\n'
            '        d = {}\n'
            '        for child in el:\n'
            '            v = _xml_to_dict(child) if len(child) else (child.text or "")\n'
            '            if child.tag in d:\n'
            '                if not isinstance(d[child.tag], list):\n'
            '                    d[child.tag] = [d[child.tag]]\n'
            '                d[child.tag].append(v)\n'
            '            else:\n'
            '                d[child.tag] = v\n'
            '        return d or (el.text or "")\n'
            '    # Normalise list input: unwrap first item if it is a dict, else\n'
            '    # wrap the list so .get() calls below are always on a dict.\n'
            '    if isinstance(input_data, list):\n'
            '        input_data = (input_data[0] if input_data and isinstance(input_data[0], dict)\n'
            '                      else {"items": input_data})\n'
            '    if operation == "xmlToJson":\n'
            '        xml_str = input_data.get(data_key, "") if isinstance(input_data, dict) else ""\n'
            '        try:\n'
            '            root = ET.fromstring(str(xml_str))\n'
            '            result[data_key] = {root.tag: _xml_to_dict(root)}\n'
            '        except ET.ParseError as exc:\n'
            '            result[data_key] = {"error": str(exc), "raw": xml_str}\n'
            '    else:\n'
            '        def _dict_to_xml(tag, d):\n'
            '            el = ET.Element(tag)\n'
            '            if isinstance(d, dict):\n'
            '                for k, v in d.items():\n'
            '                    el.append(_dict_to_xml(k, v))\n'
            '            else:\n'
            '                el.text = str(d)\n'
            '            return el\n'
            '        data = (input_data.get(data_key, input_data) if isinstance(input_data, dict)\n'
            '                else input_data)\n'
            '        if isinstance(data, dict) and data:\n'
            '            root_tag = next(iter(data))\n'
            '            root_el = _dict_to_xml(root_tag, data[root_tag])\n'
            '        else:\n'
            '            root_el = _dict_to_xml("root", data)\n'
            '        result[data_key] = ET.tostring(root_el, encoding="unicode")\n'
        )
        return self._wrap_transform_code(node_name, "XML", core, output_style="field")

    def _convert_crypto_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Crypto node (hash / hmac / sign) to Python code."""
        node_name = n8n_node.get("name", "Crypto")
        params = n8n_node.get("parameters", {})
        action = params.get("action", "hash")
        value = self._convert_expression(params.get("value", ""))
        hash_type = params.get("type", "MD5")
        secret = self._convert_expression(params.get("secret", ""))
        encoding = params.get("encoding", "hex")
        property_name = params.get("dataPropertyName", "data")
        safe_val = value.replace('"""', '\\"\\"\\"')
        safe_sec = secret.replace('"""', '\\"\\"\\"')
        core = (
            '    import hashlib, hmac as _hmac, base64\n'
            f'    action = "{action}"\n'
            f'    _iv = (input_data.get("{property_name}", str(input_data))\n'
            f'           if isinstance(input_data, dict) else input_data)\n'
            f'    raw_value = """{safe_val}""" or str(_iv)\n'
            f'    hash_type = "{hash_type}".lower().replace("-", "")\n'
            f'    secret_str = """{safe_sec}"""\n'
            f'    encoding = "{encoding}"\n'
            f'    property_name = "{property_name}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    try:\n'
            '        data_bytes = raw_value.encode("utf-8")\n'
            '        secret_bytes = secret_str.encode("utf-8")\n'
            '        if action == "hash":\n'
            '            h = hashlib.new(hash_type, data_bytes)\n'
            '            digest = h.hexdigest() if encoding == "hex" else base64.b64encode(h.digest()).decode()\n'
            '        elif action == "hmac":\n'
            '            h = _hmac.new(secret_bytes, data_bytes, getattr(hashlib, hash_type, hashlib.sha256))\n'
            '            digest = h.hexdigest() if encoding == "hex" else base64.b64encode(h.digest()).decode()\n'
            '        elif action == "sign":\n'
            '            digest = base64.b64encode(data_bytes).decode()\n'
            '        else:\n'
            '            digest = raw_value\n'
            '        result[property_name] = digest\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
            '        result[property_name] = raw_value\n'
        )
        return self._wrap_transform_code(node_name, "Crypto", core, output_style="field")

    def _convert_date_time_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Date & Time node to Python code."""
        node_name = n8n_node.get("name", "Date & Time")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "formatDate")
        value = self._convert_expression(params.get("value", ""))
        to_format = params.get("toFormat", "YYYY-MM-DD HH:mm:ss")
        from_format = params.get("fromFormat", "")
        # typeVersion 2 uses "outputFieldName"; older v1 used "dataPropertyName"
        property_name = params.get("outputFieldName") or params.get("dataPropertyName", "data")
        # If _convert_expression produced a template placeholder like {{fieldName}},
        # the literal string must NOT be used as the date value — it must be resolved
        # from input_data at runtime.  Extract the field name and emit a dict lookup.
        _tpl_match = re.match(r'^\{\{(\w+)\}\}$', value.strip())
        if operation == "getCurrentDate":
            # getCurrentDate derives its value from the clock, not from input_data
            raw_value_expr = '""'
        elif _tpl_match:
            _input_field = _tpl_match.group(1)
            raw_value_expr = f'str(input_data.get("{_input_field}", ""))'
        else:
            safe_val = value.replace('"""', '\\"\\"\\"')
            raw_value_expr = f'"""{safe_val}""" or str(input_data.get("{property_name}", ""))'
        core = (
            '    from datetime import datetime, timedelta\n'
            f'    operation = "{operation}"\n'
            f'    raw_value = {raw_value_expr}\n'
            f'    property_name = "{property_name}"\n'
            '    def moment_to_strftime(fmt):\n'
            '        fmt = fmt.replace("YYYY", "%Y").replace("YY", "%y")\n'
            '        fmt = fmt.replace("MM",   "%m").replace("DD", "%d")\n'
            '        fmt = fmt.replace("HH",   "%H").replace("mm", "%M").replace("ss", "%S")\n'
            '        return fmt\n'
            f'    to_fmt = moment_to_strftime("{to_format}")\n'
            f'    from_fmt = moment_to_strftime("{from_format}") if "{from_format}" else None\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    try:\n'
            '        if operation == "formatDate":\n'
            '            if from_fmt:\n'
            '                dt = datetime.strptime(raw_value, from_fmt)\n'
            '            else:\n'
            '                for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S",\n'
            '                            "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]:\n'
            '                    try:\n'
            '                        dt = datetime.strptime(raw_value, fmt); break\n'
            '                    except ValueError:\n'
            '                        continue\n'
            '                else:\n'
            '                    dt = datetime.now()\n'
            '            result[property_name] = dt.strftime(to_fmt)\n'
            '        elif operation == "getCurrentDate":\n'
            '            result[property_name] = datetime.now().strftime(to_fmt)\n'
            '        elif operation == "addToDate":\n'
            '            amt = int(input_data.get("duration", 1))\n'
            '            result[property_name] = (datetime.now() + timedelta(days=amt)).strftime(to_fmt)\n'
            '        elif operation == "subtractFromDate":\n'
            '            amt = int(input_data.get("duration", 1))\n'
            '            result[property_name] = (datetime.now() - timedelta(days=amt)).strftime(to_fmt)\n'
            '        else:\n'
            '            result[property_name] = raw_value\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
            '        result[property_name] = raw_value\n'
        )
        return self._wrap_transform_code(node_name, "Date & Time", core, output_style="field")

    def _convert_compression_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Compression node (compress / decompress) to Python code."""
        node_name = n8n_node.get("name", "Compression")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "compress")
        file_format = params.get("fileFormat", "gzip")
        input_field = params.get("binaryPropertyName", "data")
        output_field = params.get("outputPrefix", "data")
        core = (
            '    import gzip, zipfile, io, base64\n'
            f'    operation = "{operation}"\n'
            f'    file_format = "{file_format}"\n'
            f'    input_field = "{input_field}"\n'
            f'    output_field = "{output_field}"\n'
            '    raw = input_data.get(input_field, "")\n'
            '    raw_bytes = (\n'
            '        raw.encode("utf-8") if isinstance(raw, str)\n'
            '        else (raw if isinstance(raw, bytes) else str(raw).encode("utf-8"))\n'
            '    )\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    try:\n'
            '        if operation == "compress":\n'
            '            if file_format == "gzip":\n'
            '                out = gzip.compress(raw_bytes)\n'
            '            else:\n'
            '                buf = io.BytesIO()\n'
            '                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:\n'
            '                    zf.writestr("data", raw_bytes)\n'
            '                out = buf.getvalue()\n'
            '            result[output_field] = base64.b64encode(out).decode("utf-8")\n'
            '        else:\n'
            '            decoded = base64.b64decode(raw_bytes) if not isinstance(raw, bytes) else raw_bytes\n'
            '            if file_format == "gzip":\n'
            '                out = gzip.decompress(decoded)\n'
            '            else:\n'
            '                buf = io.BytesIO(decoded)\n'
            '                with zipfile.ZipFile(buf, "r") as zf:\n'
            '                    out = zf.read(zf.namelist()[0])\n'
            '            result[output_field] = out.decode("utf-8", errors="replace")\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
        )
        return self._wrap_transform_code(node_name, "Compression", core, output_style="field")

    # ── File I/O nodes ────────────────────────────────────────────────────────

    def _convert_read_binary_files_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Read Binary Files node to Python code."""
        node_name = n8n_node.get("name", "Read Binary Files")
        params = n8n_node.get("parameters", {})
        file_selector = self._convert_expression(params.get("fileSelector", ""))
        property_name = params.get("dataPropertyName", "data")
        safe_sel = file_selector.replace('"""', '\\"\\"\\"')
        return (
            'def main(args):\n'
            f'    """Converted from n8n Read Binary Files node: {node_name}"""\n'
            '    import base64, glob, os\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    file_selector = """{safe_sel}""" or input_data.get("fileSelector", "")\n'
            f'    prop = "{property_name}"\n'
            '    files = []\n'
            '    try:\n'
            '        for path in (glob.glob(file_selector) if file_selector else []):\n'
            '            with open(path, "rb") as fh:\n'
            '                content = fh.read()\n'
            '            files.append({\n'
            '                "fileName": os.path.basename(path),\n'
            '                "filePath": path,\n'
            '                "mimeType": "application/octet-stream",\n'
            '                prop: base64.b64encode(content).decode("utf-8"),\n'
            '                "fileSize": len(content),\n'
            '            })\n'
            '        result = {"files": files, "count": len(files)}\n'
            '    except Exception as exc:\n'
            '        result = {"error": str(exc), "files": [], "count": 0}\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    def _convert_write_binary_file_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Write Binary File node to Python code."""
        node_name = n8n_node.get("name", "Write Binary File")
        params = n8n_node.get("parameters", {})
        file_name = self._convert_expression(params.get("fileName", "output.bin"))
        property_name = params.get("dataPropertyName", "data")
        safe_fn = file_name.replace('"""', '\\"\\"\\"')
        return (
            'def main(args):\n'
            f'    """Converted from n8n Write Binary File node: {node_name}"""\n'
            '    import base64, os\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    file_name = """{safe_fn}""" or input_data.get("fileName", "output.bin")\n'
            f'    binary_data = input_data.get("{property_name}", "")\n'
            '    result = {}\n'
            '    try:\n'
            '        parent = os.path.dirname(file_name)\n'
            '        os.makedirs(parent if parent else ".", exist_ok=True)\n'
            '        raw = base64.b64decode(binary_data) if isinstance(binary_data, str) else bytes(binary_data)\n'
            '        with open(file_name, "wb") as fh:\n'
            '            fh.write(raw)\n'
            '        result = {"success": True, "fileName": file_name, "bytesWritten": len(raw)}\n'
            '    except Exception as exc:\n'
            '        result = {"success": False, "error": str(exc), "fileName": file_name}\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    @staticmethod
    def _convert_spreadsheet_file_to_code(n8n_node: Dict) -> str:
        """Convert n8n Spreadsheet File node to Python code (CSV via stdlib; XLSX flagged)."""
        node_name = n8n_node.get("name", "Spreadsheet File")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "fromFile")
        file_format = params.get("fileFormat", "csv")
        binary_prop = params.get("binaryPropertyName", "data")
        return (
            'def main(args):\n'
            f'    """Converted from n8n Spreadsheet File node: {node_name}"""\n'
            '    import csv, io, base64, json\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    operation = "{operation}"\n'
            f'    file_format = "{file_format}"\n'
            f'    binary_prop = "{binary_prop}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    try:\n'
            '        if operation == "fromFile":\n'
            '            raw = input_data.get(binary_prop, "")\n'
            '            try:\n'
            '                content = base64.b64decode(raw).decode("utf-8", errors="replace") if raw else ""\n'
            '            except Exception:\n'
            '                content = str(raw)\n'
            '            if file_format == "csv":\n'
            '                rows = [dict(r) for r in csv.DictReader(io.StringIO(content))]\n'
            '                result["rows"] = rows\n'
            '                result["count"] = len(rows)\n'
            '            elif file_format in ("xls", "xlsx"):\n'
            '                result["rows"] = []\n'
            '                result["warning"] = (\n'
            '                    "XLSX parsing requires openpyxl. Install: pip install openpyxl"\n'
            '                )\n'
            '            else:\n'
            '                result["content"] = content\n'
            '        else:\n'
            '            items = input_data.get(\n'
            '                "items", [input_data] if isinstance(input_data, dict) else []\n'
            '            )\n'
            '            if file_format == "csv" and items:\n'
            '                buf = io.StringIO()\n'
            '                fieldnames = list(items[0].keys()) if isinstance(items[0], dict) else ["value"]\n'
            '                w = csv.DictWriter(buf, fieldnames=fieldnames)\n'
            '                w.writeheader()\n'
            '                for item in items:\n'
            '                    if isinstance(item, dict):\n'
            '                        w.writerow(item)\n'
            '                result[binary_prop] = base64.b64encode(buf.getvalue().encode()).decode()\n'
            '                result["fileName"] = "output.csv"\n'
            '            else:\n'
            '                result[binary_prop] = base64.b64encode(json.dumps(items).encode()).decode()\n'
            '                result["fileName"] = "output.json"\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    def _convert_convert_to_file_to_code(self, n8n_node: Dict) -> str:
        """Convert n8n Convert to File node to Python code."""
        node_name = n8n_node.get("name", "Convert to File")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "toText")
        file_name = self._convert_expression(params.get("fileName", "output"))
        mime_type = params.get("mimeType", "text/plain")
        binary_prop = params.get("binaryPropertyName", "data")
        safe_fn = file_name.replace('"""', '\\"\\"\\"')
        return (
            'def main(args):\n'
            f'    """Converted from n8n Convert to File node: {node_name}"""\n'
            '    import base64, csv, io, json\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    operation = "{operation}"\n'
            f'    file_name = """{safe_fn}""" or "output"\n'
            f'    binary_prop = "{binary_prop}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    try:\n'
            '        if operation in ("toText", "toJson"):\n'
            '            text = json.dumps(input_data, ensure_ascii=False)\n'
            '            result[binary_prop] = base64.b64encode(text.encode()).decode()\n'
            '            result["fileName"] = file_name + ".json"\n'
            '            result["mimeType"] = "application/json"\n'
            '        elif operation == "toCsv":\n'
            '            items = input_data.get(\n'
            '                "items", [input_data] if isinstance(input_data, dict) else []\n'
            '            )\n'
            '            buf = io.StringIO()\n'
            '            fieldnames = list(items[0].keys()) if items and isinstance(items[0], dict) else ["value"]\n'
            '            w = csv.DictWriter(buf, fieldnames=fieldnames)\n'
            '            w.writeheader()\n'
            '            for item in items:\n'
            '                if isinstance(item, dict):\n'
            '                    w.writerow(item)\n'
            '            result[binary_prop] = base64.b64encode(buf.getvalue().encode()).decode()\n'
            '            result["fileName"] = file_name + ".csv"\n'
            '            result["mimeType"] = "text/csv"\n'
            '        else:\n'
            '            text = base64.b64encode(str(input_data).encode()).decode()\n'
            '            result[binary_prop] = text\n'
            f'            result["fileName"] = file_name\n'
            f'            result["mimeType"] = "{mime_type}"\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

    @staticmethod
    def _convert_extract_from_file_to_code(n8n_node: Dict) -> str:
        """Convert n8n Extract From File node to Python code."""
        node_name = n8n_node.get("name", "Extract From File")
        params = n8n_node.get("parameters", {})
        operation = params.get("operation", "extractFromCsv")
        binary_prop = params.get("binaryPropertyName", "data")
        destination_key = params.get("destinationKey", "data")
        return (
            'def main(args):\n'
            f'    """Converted from n8n Extract From File node: {node_name}"""\n'
            '    import base64, csv, io, json, re\n'
            '    input_data = args.params.get("input", {}) if hasattr(args, "params") else {}\n'
            f'    operation = "{operation}"\n'
            f'    binary_prop = "{binary_prop}"\n'
            f'    destination_key = "{destination_key}"\n'
            '    result = dict(input_data) if isinstance(input_data, dict) else {}\n'
            '    raw = input_data.get(binary_prop, "")\n'
            '    try:\n'
            '        try:\n'
            '            content = base64.b64decode(raw).decode("utf-8", errors="replace") if raw else ""\n'
            '        except Exception:\n'
            '            content = str(raw)\n'
            '        if operation == "extractFromCsv":\n'
            '            result[destination_key] = [dict(r) for r in csv.DictReader(io.StringIO(content))]\n'
            '        elif operation == "extractFromJson":\n'
            '            result[destination_key] = json.loads(content)\n'
            '        elif operation == "extractFromHtml":\n'
            '            result[destination_key] = re.sub(r"<[^>]+>", "", content).strip()\n'
            '        else:\n'
            '            result[destination_key] = content\n'
            '    except Exception as exc:\n'
            '        result["error"] = str(exc)\n'
            '        result[destination_key] = raw\n'
            '    _output = dict(result)\n'
            '    _output["result"] = result\n'
            '    return _output\n'
        )

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
    # HTTP REQUEST NODE CONVERSION
    # =========================================================================
    def _convert_http_request_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n HTTP Request node to OpenJiuwen HTTP Request component."""
        params = n8n_node.get("parameters", {})
        node_name = n8n_node.get("name", "")
        position = n8n_node.get("position", [x_pos, 34])

        method = params.get("method", "GET")
        raw_url = params.get("url", "")

        # Resolve n8n expressions to a proper ref pointing to the predecessor node
        # that supplies the URL value, falling back to the start node if none is found.
        if raw_url.startswith("="):
            converted_url = self._convert_expression_with_mapping(raw_url)
            field_match = re.match(r'^\{\{(\w+)\}\}$', converted_url.strip())
            if field_match:
                field_name = field_match.group(1)
                pred_id = self._find_data_predecessor_id(node_name)
                source_id = pred_id if pred_id else self.start_node_id
                url_value = {
                    "type": "ref",
                    "content": [source_id, field_name],
                    "extra": {"index": 0}
                }
            else:
                url_value = BaseValue(
                    type='constant', content=converted_url,
                    schema=BaseType(type='string')
                ).model_dump()
            url = converted_url
        else:
            url = raw_url
            url_value = BaseValue(
                type='constant', content=url,
                schema=BaseType(type='string')
            ).model_dump()

        # Convert headers from n8n format (list of {name, value} dicts)
        headers_list = params.get("headerParameters", [])
        headers = {}
        for header in headers_list:
            if isinstance(header, dict) and "name" in header:
                headers[header["name"]] = header.get("value", "")

        # Convert query parameters from n8n format
        query_params_list = params.get("queryParameters", [])
        query_params = {}
        for qp in query_params_list:
            if isinstance(qp, dict) and "name" in qp:
                query_params[qp["name"]] = qp.get("value", "")

        # Convert body - n8n uses different formats based on content type
        body = None
        body_content_type = params.get("options", {}).get("bodyContentType")
        if body_content_type:
            if body_content_type == "json":
                body = params.get("body", {})
            elif body_content_type == "raw":
                body = params.get("body", {})
            elif body_content_type == "form-data":
                form_data = params.get("sendBody", {})
                if isinstance(form_data, dict) and "parameters" in form_data:
                    body = {}
                    for param in form_data["parameters"]:
                        if isinstance(param, dict) and "name" in param:
                            body[param["name"]] = param.get("value", "")
            elif body_content_type == "form-urlencoded":
                form_data = params.get("sendBody", {})
                if isinstance(form_data, dict) and "parameters" in form_data:
                    body = {}
                    for param in form_data["parameters"]:
                        if isinstance(param, dict) and "name" in param:
                            body[param["name"]] = param.get("value", "")

        # Build input parameters with BaseValue references
        input_params = self._build_predecessor_input_ref(node_name)

        if input_params.get("url") is None:
            input_params["url"] = url_value
        if input_params.get("method") is None:
            input_params["method"] = \
                BaseValue(type='constant', content=method, schema=BaseType(type='string')).model_dump()
        if input_params.get("headers") is None:
            input_params["headers"] = \
                BaseValue(type='constant', content=headers, schema=BaseType(type='object')).model_dump()
        if input_params.get("query") is None:
            input_params["query"] = \
                BaseValue(type='constant', content=query_params, schema=BaseType(type='object')).model_dump()
        if input_params.get("body") is None:
            input_params["body"] = \
                BaseValue(type='constant', content=body, schema=BaseType(type='object')).model_dump()

        # Auth configuration
        auth_config = {
            "type": "none",
            "username": "",
            "password": "",
            "token": "",
            "api_key": "",
            "api_key_location": "header",
            "api_key_param_name": "X-API-Key"
        }

        if params.get("options", {}).get("authentication"):
            auth_type = params["options"]["authentication"]
            if auth_type == "basicAuth":
                auth_config["type"] = "basic"
            elif auth_type == "headerAuth":
                auth_config["type"] = "api_key"
                auth_config["api_key_location"] = "header"
            elif auth_type == "queryAuth":
                auth_config["type"] = "api_key"
                auth_config["api_key_location"] = "query"

        input_params["auth"] = \
            BaseValue(type='constant', content=auth_config, schema=BaseType(type='object')).model_dump()

        # Build httpRequestParam structure
        http_request_params = {
            "url": url_value,
            "method": method,
            "headers": headers,
            "queryParams": query_params,
            "body": {
                "contentType": "application/json" if body_content_type == "json" else "text/plain",
                "content": body if body is not None else ""
            },
            "auth": {
                "authType": auth_config["type"],
                "username": auth_config["username"],
                "password": auth_config["password"],
                "token": auth_config["token"],
                "apiKey": auth_config["api_key"],
                "apiKeyLocation": auth_config["api_key_location"],
                "apiKeyParamName": auth_config["api_key_param_name"]
            },
            "response": {
                "responseFormat": "auto",
                "successStatusCodes": [200, 201, 202, 204],
                "failureStatusCodes": [],
                "responseMode": "full",
                "dataProperty": ""
            },
            "advanced": {
                "followRedirects": True,
                "ignoreSslIssues": False,
                "proxyUrl": "",
                "timeout": 60,
                "retry": {
                    "enabled": False,
                    "maxRetries": 3,
                    "retryOnStatusCodes": [429, 500, 502, 503, 504],
                    "retryDelayMs": 1000,
                    "backoffType": "exponential"
                },
                "rateLimit": {
                    "enabled": False,
                    "requestsPerUnit": 10,
                    "unit": "minute"
                }
            }
        }

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_HTTP_REQUEST),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": node_name,
                "inputs": {
                    "method": {
                        "type": "constant",
                        "content": method
                    },
                    "inputParameters": input_params,
                    "httpRequestParam": http_request_params,
                    "_n8n_type": n8n_node.get("type", ""),
                    "_n8n_params": params
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "error_code": {
                            "type": "integer",
                            "description": "Error code (0 for success)",
                            "extra": {"index": 1}
                        },
                        "error_msg": {
                            "type": "string",
                            "description": "Error message (empty for success)",
                            "extra": {"index": 2}
                        },
                        "data": {
                            "type": "object",
                            "description": "Response data (JSON object for 200 OK)",
                            "properties": {},        # ← add this
                            "extra": {"index": 3}
                        }
                    },
                    "required": ["error_code", "error_msg", "data"]
                },
                "exceptionConfig": {
                    "retryTimes": 0,
                    "timeoutSeconds": 60,
                    "processType": "break",
                    "executeStep": {
                        "defaultStep": "0",
                        "errorStep": "1"
                    }
                }
            }
        }

    # =========================================================================
    # REACT AGENT NODE CONVERSION
    # =========================================================================

    def _convert_react_agent_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n React Agent node to OpenJiuwen ReAct Agent component.

        n8n Agent nodes have:
        - Parameters with prompts (text, systemMessage in options)
        - Connected AI sub-nodes (ai_languageModel, ai_tool, ai_memory)

        The converted node structure matches ReactAgentConfig requirements:
        - llmParam with systemPrompt, prompt, and model
        - inputParameters for variable references
        - skillsParam with plugins and workflows
        - max_iterations for agent loop limit
        """
        params = n8n_node.get("parameters", {})
        node_name = n8n_node.get("name", "")
        position = n8n_node.get("position", [x_pos, 34])

        # Extract system prompt from n8n format (may be in options or empty)
        system_prompt = ""
        if params.get("options", {}).get("systemMessage"):
            system_prompt = params["options"]["systemMessage"]
        elif params.get("systemMessage"):
            system_prompt = params["systemMessage"]

        # Extract user prompt (text field in n8n agent)
        user_prompt = params.get("text", "")

        # Convert expressions with field mapping
        system_prompt = self._convert_expression_with_mapping(system_prompt)
        user_prompt = self._convert_expression_with_mapping(user_prompt)

        # Build default prompt if not provided
        if not user_prompt and self.field_name_map:
            prompt_parts = [f"{{{{{name}}}}}" for name in self.field_name_map.values()]
            user_prompt = " ".join(prompt_parts)
        elif not user_prompt:
            user_prompt = "{{query}}"

        # Get model config from connected AI sub-node (ai_languageModel connection)
        model_config = self._find_connected_model(node_name)

        # Build input parameters reference using "query" as the key for inputParameters
        input_parameters = self._build_predecessor_input_ref(node_name, param_key="query")

        # Find connected tools/plugins via ai_tool connection
        tools = self._find_connected_tools(node_name)

        # Build skillsParam from connected tools
        skills_param = {
            "plugins": [],
            "workflows": []
        }
        for tool_info in tools:
            # tool_info is in format "ToolName (tool_type)"
            # For now, we create placeholder entries; in production these would be resolved to actual plugin IDs
            tool_name = tool_info.split(" (")[0] if " (" in tool_info else tool_info
            skills_param["plugins"].append({
                "id": str(uuid.uuid4()),  # Placeholder ID - would be resolved at runtime
                "name": tool_name,
                "type": "plugin"
            })

        # Extract max_iterations from n8n params (default to 5)
        max_iterations = params.get("options", {}).get("maxIterations", 5)
        if not isinstance(max_iterations, int) or max_iterations < 1:
            max_iterations = 5

        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_REACT_AGENT),
            "meta": {
                "position": {
                    "x": position[0] if len(position) > 0 else x_pos,
                    "y": position[1] if len(position) > 1 else 34
                }
            },
            "data": {
                "title": node_name or "ReAct Agent",
                "max_iterations": max_iterations,
                "inputs": {
                    "llmParam": {
                        "systemPrompt": {
                            "type": "template",
                            "content": system_prompt or (
                                "You are a helpful ReAct agent that can "
                                "reason and use tools to solve problems."
                            )
                        },
                        "prompt": {
                            "type": "template",
                            "content": user_prompt
                        },
                        "model": model_config
                    },
                    "inputParameters": input_parameters,
                    "skillsParam": skills_param
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "output": {
                            "type": "string",
                            "description": "Agent response content",
                            "extra": {"index": 1}
                        }
                    },
                    "required": ["output"]
                }
            }
        }

    # =========================================================================
    # MERGE NODE CONVERSION
    # =========================================================================

    def _find_all_predecessor_ids(self, n8n_node_name: str) -> List[str]:
        """
        Return the Jiuwen IDs of ALL predecessors that feed into a given node,
        ordered by their n8n input index (index 0 first, then index 1, etc.).

        Unlike _find_predecessor_id which returns only one, this collects every
        source node — needed for Merge nodes that have multiple distinct inputs.
        """
        # Build a dict of {input_index: jiuwen_id} so we preserve order
        index_to_id: Dict[int, str] = {}
        for source_name, conn_types in self.n8n_connections.items():
            for conn_type, target_lists in conn_types.items():
                if conn_type != "main":
                    continue
                for output_index, target_list in enumerate(target_lists):
                    for target in target_list:
                        if target.get("node") == n8n_node_name:
                            pred_id = self.node_id_map.get(source_name)
                            if pred_id:
                                input_idx = target.get("index", output_index)
                                index_to_id[input_idx] = pred_id
        return [index_to_id[k] for k in sorted(index_to_id)]

    def _convert_merge_node(self, n8n_node: Dict, node_id: str, x_pos: int) -> Dict:
        """Convert n8n Merge node to OpenJiuwen Variable Merge component.

        n8n merge modes:
          - append         → mode: append
          - combine
              - mergeByFields  → mode: combine, combineBy: matchingFields
              - keepKeyMatches → mode: combine, combineBy: matchingFields (keepMatches output)
              - enrichInput1   → mode: combine, combineBy: matchingFields (enrichInput1 output)
              - mergeByPosition → mode: combine, combineBy: position
              - multiplex       → mode: combine, combineBy: allCombinations
          - chooseBranch   → mode: chooseBranch
          - sqlQuery       → mode: sqlQuery, sqlQuery: parameters.query
        """
        node_name = n8n_node.get("name", "")
        params = n8n_node.get("parameters", {})
        position = n8n_node.get("position", [x_pos, 34])
        px = position[0] if len(position) > 0 else x_pos
        py = position[1] if len(position) > 1 else 34

        n8n_mode = params.get("mode", "append")          # append | combine | chooseBranch
        combine_by_raw = params.get("combineBy", "mergeByFields")  # used when mode == combine
        output_type_raw = params.get("outputDataFrom", "both")  # chooseBranch: input1|input2|empty

        # ── Resolve input predecessors by port index ──────────────────────────
        pred1_id = self._find_predecessor_by_input_index(node_name, 0)
        pred2_id = self._find_predecessor_by_input_index(node_name, 1)

        def make_ref(pred_id: str, slot: str, group_index: int) -> Dict:
            out_field = self._get_primary_output_field(pred_id)
            return {
                slot: {
                    "type": "ref",
                    "content": [pred_id, out_field],
                    "extra": {"index": group_index},
                }
            }

        input_parameters: Dict = {}
        if pred1_id:
            input_parameters.update(make_ref(pred1_id, "input1", 0))
        if pred2_id:
            input_parameters.update(make_ref(pred2_id, "input2", 1))

        # ── Map n8n mode → OpenJiuwen mode + group config ─────────────────────
        if n8n_mode == "chooseBranch":
            # chooseBranch: output_type_raw is "input1" | "input2" | "empty"
            choose_index_map = {"input1": 0, "input2": 1, "empty": -1}
            choose_index = choose_index_map.get(output_type_raw, 0)
            group = {
                "name": "output",
                "type": "object",
                "items": list(input_parameters.keys()),
                "mode": "chooseBranch",
                "chooseIndex": choose_index,
            }

        elif n8n_mode == "combine":
            # Map n8n combineBy values to OpenJiuwen combineBy
            combine_by_map = {
                "mergeByFields": "matchingFields",
                "keepKeyMatches": "matchingFields",
                "enrichInput1": "matchingFields",
                "mergeByPosition": "position",
                "combineByPosition": "position",  # n8n typeVersion 3 alias
                "multiplex": "allCombinations",
                "combineAll": "allCombinations",    # n8n typeVersion 3 alias
                "combineByAll": "allCombinations",  # n8n typeVersion 3 alias
            }
            ojw_combine_by = combine_by_map.get(combine_by_raw, "matchingFields")

            # Map n8n combineBy to OpenJiuwen outputType for matchingFields
            output_type_map = {
                "mergeByFields": "keepMatches",
                "keepKeyMatches": "keepMatches",
                "enrichInput1": "enrichInput1",
            }
            ojw_output_type = output_type_map.get(combine_by_raw, "keepMatches")

            # Extract matching field names if present
            merge_fields_raw = params.get("mergeByFields", {}).get("values", [])
            match_field1 = merge_fields_raw[0].get("field1", "") if merge_fields_raw else ""
            match_field2 = merge_fields_raw[0].get("field2", "") if merge_fields_raw else ""

            # Clash handling options
            clash_handling = params.get("options", {})
            clash_when_clash_map = {
                "addSuffix": "addInputNumber",
                "preferInput1": "preferInput1",
                "preferInput2": "preferInput2",
            }
            ojw_clash = clash_when_clash_map.get(
                clash_handling.get("clashHandling", {}).get("values", {}).get("resolveClash", "addSuffix"),
                "addInputNumber"
            )
            merge_mode = clash_handling.get("clashHandling", {}).get("values", {}).get("mergeMode")
            ojw_merging_nested = "deepMerge" if merge_mode == "deepMerge" else "shallowMerge"
            keep_unpaired = bool(params.get("options", {}).get("includeUnpaired", False))
            fuzzy_compare = bool(params.get("options", {}).get("fuzzyCompare", False))

            group = {
                "name": "output",
                "type": "array",
                "items": list(input_parameters.keys()),
                "mode": "combine",
                "combineBy": ojw_combine_by,
                "matchField1": match_field1,
                "matchField2": match_field2,
                "outputType": ojw_output_type,
                "keepUnpaired": keep_unpaired,
                "fuzzyCompare": fuzzy_compare,
                "clashWhenClash": ojw_clash,
                "clashMergingNested": ojw_merging_nested,
                "clashMinimizeEmptyFields": False,
            }

        elif n8n_mode == "sqlQuery":
            sql_query = params.get("query", "")
            group = {
                "name": "output",
                "type": "array",
                "items": list(input_parameters.keys()),
                "mode": "sqlQuery",
                "sqlQuery": sql_query,
            }

        else:
            # append (default) — stack all inputs
            group = {
                "name": "output",
                "type": "array",
                "items": list(input_parameters.keys()),
                "mode": "append",
            }

        # ── Assemble node ─────────────────────────────────────────────────────
        return {
            "id": node_id,
            "type": str(ComponentType.COMPONENT_TYPE_VARIABLE_MERGE),
            "meta": {
                "position": {"x": px, "y": py}
            },
            "data": {
                "title": n8n_node.get("name", self.get_title("merge")),
                "inputs": {
                    "inputParameters": input_parameters,
                    "variableMerge": [group],
                },
                "outputs": {
                    "type": "object",
                    "properties": {
                        "output": {"type": group.get("type", "object"), "extra": {"index": 1}}
                    }
                },
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

    def _code_node_has_selector_source(self, code_node_id: str) -> bool:
        """Return True if code_node_id has at least one direct incoming edge from a
        Selector (IF) node — i.e. it is a genuine branch output.

        Pure fan-out Code nodes (fed from Start or other Code nodes) return False.
        Only branch outputs can trigger WORKFLOW_GRAPH_BRANCH_REDUCE_ERROR, so
        _fix_shared_merge_predecessors must skip any merge whose shared predecessors
        are all plain fan-out nodes.
        """
        selector_type = ComponentType.COMPONENT_TYPE_IF
        for edge in self.openjiuwen_edges:
            if edge.get("targetNodeID") == code_node_id:
                src_id = edge.get("sourceNodeID", "")
                src_node = next(
                    (n for n in self.openjiuwen_nodes if n["id"] == src_id), None
                )
                if src_node and int(src_node.get("type", 0)) == selector_type:
                    return True
        return False

    def _fix_shared_merge_predecessors(self):
        """Fix CBA fan-out error when multiple variable-merge nodes share code predecessors.

        OpenJiuwen's pregel graph adapter raises WORKFLOW_GRAPH_BRANCH_REDUCE_ERROR
        when a node receives edges from two different "branch ancestors" — i.e. two
        separate code-type fan-outs.  This happens when two merge nodes both connect
        to the same pair of code predecessors that are themselves on different selector
        branches (e.g. Selector→CodeA→Merge1, Selector→CodeB→Merge1, same for Merge2).

        IMPORTANT: This fix must NOT apply to pure fan-out patterns where the shared
        Code predecessors are fed directly from Start or other non-branching nodes
        (e.g. Input1→Merge1 and Input1→Merge2 as parallel consumers).  In those cases
        there is no branch-reduce and stripping the edges breaks both merges.

        Fix: keep the first merge's incoming edges intact, then for each subsequent
        merge that shares *branch-output* code predecessors, remove those conflicting
        edges and add a single ordering edge from the first merge node (or its direct
        successor) so that execution ordering is preserved while the data is still read
        from session state via inputParameters refs.
        """
        merge_type = ComponentType.COMPONENT_TYPE_VARIABLE_MERGE
        code_type = ComponentType.COMPONENT_TYPE_CODE

        merge_node_ids = []
        for n in self.openjiuwen_nodes:
            if int(n.get("type", 0)) == merge_type:
                merge_node_ids.append(n["id"])
        if len(merge_node_ids) < 2:
            return

        def _get_code_in_sources(merge_id: str):
            sources = set()
            for edge in self.openjiuwen_edges:
                if edge.get("targetNodeID") == merge_id:
                    src_id = edge.get("sourceNodeID", "")
                    src_node = next((n for n in self.openjiuwen_nodes if n["id"] == src_id), None)
                    if src_node and int(src_node.get("type", 0)) == code_type:
                        sources.add(src_id)
            return sources

        def _get_direct_successor(node_id: str):
            for edge in self.openjiuwen_edges:
                if edge.get("sourceNodeID") == node_id:
                    return edge.get("targetNodeID")
            return None

        # claimed_by: code_node_id → first merge_id that claimed it
        claimed_by: Dict[str, str] = {}

        for merge_id in merge_node_ids:
            sources = _get_code_in_sources(merge_id)
            conflicting = sources & set(claimed_by.keys())

            if not conflicting:
                for src in sources:
                    claimed_by.setdefault(src, merge_id)
            else:
                # Only apply the fix when at least one of the conflicting code
                # predecessors is a genuine branch output (fed from a Selector).
                # Pure fan-out merges (same Code node → multiple Merge nodes, with
                # no selector in between) do NOT cause BRANCH_REDUCE_ERROR and must
                # keep their edges intact so both merges receive their inputs and
                # both result nodes can reach End independently.
                if not any(self._code_node_has_selector_source(cid) for cid in conflicting):
                    # Plain fan-out: shared code predecessors without a Selector in
                    # between.  OpenJiuwen still raises BRANCH_REDUCE_ERROR in this
                    # case (e.g. Input1→MergeA and Input1→MergeB in the same flow).
                    # Fix: deep-clone each shared source node so every merge node
                    # gets its own exclusive predecessor chain.
                    for old_src_id in conflicting:
                        old_node = next(
                            (n for n in self.openjiuwen_nodes if n["id"] == old_src_id), None
                        )
                        if not old_node:
                            continue

                        # 1. Deep-clone the source node with a fresh ID
                        #    json round-trip avoids needing `import copy`
                        new_node = json.loads(json.dumps(old_node))
                        new_id = f"{old_src_id}_c{uuid.uuid4().hex[:6]}"
                        new_node["id"] = new_id
                        # Offset Y so the clone doesn't visually overlap the original
                        if "meta" in new_node and "position" in new_node["meta"]:
                            new_node["meta"]["position"]["y"] += 220
                        self.openjiuwen_nodes.append(new_node)

                        # 2. Replicate every incoming edge of the original → clone
                        incoming = []
                        for e in self.openjiuwen_edges:
                            if e.get("targetNodeID") == old_src_id:
                                incoming.append(e)
                        for e in incoming:
                            clone_edge: Dict = {
                                "id": f"edge_{uuid.uuid4().hex[:8]}",
                                "sourceNodeID": e["sourceNodeID"],
                                "targetNodeID": new_id,
                            }
                            if "sourcePortID" in e:
                                clone_edge["sourcePortID"] = e["sourcePortID"]
                            self.openjiuwen_edges.append(clone_edge)

                        # 3. Retarget the old_src→merge edge to new_id→merge
                        for e in self.openjiuwen_edges:
                            if (e.get("sourceNodeID") == old_src_id
                                    and e.get("targetNodeID") == merge_id):
                                e["sourceNodeID"] = new_id
                                break

                        # 4. Update the merge node's inputParameters refs
                        merge_node = next(
                            (n for n in self.openjiuwen_nodes if n["id"] == merge_id), None
                        )
                        if merge_node:
                            ip = (merge_node.get("data", {})
                                            .get("inputs", {})
                                            .get("inputParameters", {}))
                            for slot_val in ip.values():
                                if (isinstance(slot_val, dict)
                                        and slot_val.get("type") == "ref"):
                                    content = slot_val.get("content", [])
                                    if content and content[0] == old_src_id:
                                        content[0] = new_id

                        # 5. Register the clone as exclusively owned by this merge
                        claimed_by[new_id] = merge_id

                    # Claim non-conflicting sources for this merge
                    for src in sources - conflicting:
                        claimed_by.setdefault(src, merge_id)
                    continue

                # Find the first merge that already owns these sources
                first_merge_id = claimed_by.get(next(iter(conflicting)))
                if first_merge_id is None:
                    continue

                # Remove conflicting source→merge edges
                new_edges = []
                for e in self.openjiuwen_edges:
                    if not (e.get("targetNodeID") == merge_id and e.get("sourceNodeID") in conflicting):
                        new_edges.append(e)
                self.openjiuwen_edges = new_edges

                # Add ordering edge: first_merge (or its successor) → this merge
                predecessor = _get_direct_successor(first_merge_id) or first_merge_id
                already_exists = False
                for e in self.openjiuwen_edges:
                    if e.get("sourceNodeID") == predecessor and e.get("targetNodeID") == merge_id:
                        already_exists = True
                        break
                if not already_exists:
                    self.openjiuwen_edges.append({
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": predecessor,
                        "targetNodeID": merge_id,
                    })

    def _convert_connections(self):
        """Convert n8n connections to OpenJiuwen edges."""
        for source_name, conn_types in self.n8n_connections.items():
            source_id = self.node_id_map.get(source_name)
            if not source_id:
                continue

            # compareDatasets: node_id_map → code_id for incoming edges.
            # Outgoing edges must originate from the per-port guard Selector.
            # We defer the source_id override to the per-target-list loop below
            # because each output_index maps to a different Selector.
            is_compare_datasets = source_name in self.compare_datasets_selector_ids

            loop_source_info = self.loop_node_registry.get(source_name)

            for conn_type, target_lists in conn_types.items():
                if conn_type in ["ai_languageModel", "ai_memory", "ai_tool",
                                "ai_embedding", "ai_document"]:
                    continue

                source_n8n_node = self.nodes_by_name.get(source_name, {})
                source_n8n_type = source_n8n_node.get("type", "")

                for output_index, target_list in enumerate(target_lists):
                    # Resolve effective source for this port
                    if is_compare_datasets:
                        port_map = self.compare_datasets_selector_ids[source_name]
                        effective_source_id = port_map.get(output_index)
                        if not effective_source_id:
                            continue   # n8n port not mapped (shouldn't happen)
                        # Always treat as a selector: use branch 0 of this guard
                        sel_jw = None
                        for n in self.openjiuwen_nodes:
                            if n["id"] == effective_source_id:
                                sel_jw = n
                                break
                        cd_branch_ids = []
                        if sel_jw:
                            for b in sel_jw.get("data", {}).get("branches", []):
                                cd_branch_ids.append(b.get("branchId", "0"))
                        pending_port = cd_branch_ids[0] if cd_branch_ids else "0"
                        is_code = False
                        is_selector = True
                        selector_branch_ids = cd_branch_ids
                    else:
                        effective_source_id = source_id
                        source_jiuwen_type = self.N8N_TO_OPENJIUWEN.get(source_n8n_type)
                        is_code = (source_jiuwen_type == ComponentType.COMPONENT_TYPE_CODE
                                       or source_jiuwen_type is None)
                        is_selector = source_jiuwen_type == ComponentType.COMPONENT_TYPE_IF
                        selector_branch_ids = []
                        if is_selector:
                            jw_node = None
                            for n in self.openjiuwen_nodes:
                                if n["id"] == effective_source_id:
                                    jw_node = n
                                    break
                            if jw_node:
                                selector_branch_ids = []
                                branches = jw_node.get("data", {}).get("branches", [])
                                for i, b in enumerate(branches):
                                    selector_branch_ids.append(b.get("branchId", str(i)))
                        pending_port = (
                            str(output_index) if loop_source_info
                            else ("0" if is_code
                                  else (selector_branch_ids[output_index]
                                        if is_selector and output_index < len(selector_branch_ids)
                                        else None))
                        )

                    for target in target_list:
                        target_name = target.get("node")

                        target_loop_info = self.loop_node_registry.get(target_name)
                        if target_loop_info:
                            effective_target_id = target_loop_info["loop_id"]
                        else:
                            effective_target_id = self.node_id_map.get(target_name)

                        if not effective_target_id:
                            continue
                        if effective_source_id == effective_target_id:
                            continue

                        edge_exists = False
                        for e in self.openjiuwen_edges:
                            if (e.get("sourceNodeID") == effective_source_id
                                    and e.get("targetNodeID") == effective_target_id
                                    and e.get("sourcePortID") == pending_port):
                                edge_exists = True
                                break
                        if edge_exists:
                            continue

                        edge: Dict = {
                            "id": f"edge_{uuid.uuid4().hex[:8]}",
                            "sourceNodeID": effective_source_id,
                            "targetNodeID": effective_target_id,
                        }
                        if pending_port is not None:
                            edge["sourcePortID"] = pending_port

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
            # Sticky notes (type 99) are UI-only and must never receive edges
            if node_type == 99:
                continue
            # Selector (IF) nodes are never terminal leaf nodes: every branch is
            # wired explicitly in _ensure_edge_connections.
            if node_type == ComponentType.COMPONENT_TYPE_IF:
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
                edge_exists = False
                for e in self.openjiuwen_edges:
                    if e.get("sourceNodeID") == self.start_node_id and e.get("targetNodeID") == target_id:
                        edge_exists = True
                        break
                if not edge_exists:
                    self.openjiuwen_edges.insert(0, {
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": self.start_node_id,
                        "targetNodeID": target_id,
                    })
        
        # Connect ALL terminal nodes (leaves) to End — handles branching workflows
        # where multiple branches each end at a different node.
        if self.end_node_id:
            for terminal_id in self._find_all_terminal_nodes():
                if terminal_id == self.end_node_id:
                    continue
                edge_exists = False
                for e in self.openjiuwen_edges:
                    if e.get("sourceNodeID") == terminal_id and e.get("targetNodeID") == self.end_node_id:
                        edge_exists = True
                        break
                if not edge_exists:
                    terminal_node = next(
                        (n for n in self.openjiuwen_nodes if n["id"] == terminal_id), None
                    )
                    terminal_type = int(terminal_node.get("type", 0)) if terminal_node else 0
                    terminal_edge: Dict[str, Any] = {
                        "id": f"edge_{uuid.uuid4().hex[:8]}",
                        "sourceNodeID": terminal_id,
                        "targetNodeID": self.end_node_id,
                    }
                    # Only Code and Selector nodes use sourcePortID on outgoing edges
                    if terminal_type in (ComponentType.COMPONENT_TYPE_CODE,
                                        ComponentType.COMPONENT_TYPE_IF):
                        terminal_edge["sourcePortID"] = "0"
                    self.openjiuwen_edges.append(terminal_edge)
        
        if self.end_node_id:
            for node in self.openjiuwen_nodes:
                if int(node.get("type", 0)) != ComponentType.COMPONENT_TYPE_IF:
                    continue
                node_id = node["id"]
                branches = node.get("data", {}).get("branches", [])
                for branch in branches:
                    branch_id = branch.get("branchId")
                    if not branch_id:
                        continue
                    # Wire every branch that has no outgoing edge to End so that
                    # empty-set guards (compareDatasets ports 2/3 when unused) and
                    # regular else branches all get a clean skip path.
                    branch_edge_exists = False
                    for e in self.openjiuwen_edges:
                        if e.get("sourceNodeID") == node_id and e.get("sourcePortID") == branch_id:
                            branch_edge_exists = True
                            break
                    if not branch_edge_exists:
                        self.openjiuwen_edges.append({
                            "id": f"edge_{uuid.uuid4().hex[:8]}",
                            "sourceNodeID": node_id,
                            "targetNodeID": self.end_node_id,
                            "sourcePortID": branch_id,
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
    def add_start_end_nodes(self, nodes: List[Dict], edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
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