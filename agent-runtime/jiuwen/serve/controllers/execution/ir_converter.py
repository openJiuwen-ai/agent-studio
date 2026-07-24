# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.

"""This module contains an IRConverter."""

import json
import logging
import os
import re
import secrets
import copy
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, Iterable, List, NamedTuple, Optional

from agent_runtime.extension.workflow_node.flow_code import FlowCode
from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import FlowKnowledgeRetrieval
from agent_runtime.extension.workflow_node.ParamOutput import ParamOutput
from agent_runtime.extension.workflow_node.complex_intent_detection import ComplexIntentDetection
from agent_runtime.extension.workflow_node.questioner import (
    FieldInfo,
    Questioner,
    QuestionerConfig,
)
from jiuwen.common.configs.env_constants import (
    AGENT_CACHE_ENABLE_KEY,
    EXECUTION_SUPPORTED_IR_VERSIONS_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger, get_x_execution_id
from openjiuwen.core.common.logging import performance_logger
from jiuwen.common.utils.utils import safe_json_loads_raise_exception, timed_cache_op
from jiuwen.context.memory_engine.config.memory_ir_config import MemoryIrConfig
from jiuwen.controller.agent.agent import Agent
from jiuwen.controller.common.config import AgentConfig, AgentMetaData
from jiuwen.extension.patches.loop_body_session_cleanup_patch import (
    apply_loop_body_session_cleanup_patch,
    apply_loop_state_cleanup_patch,
)
from jiuwen.extension.patches.workflow_sub_stream_patch import (
    apply_workflow_sub_stream_patch,
)
from jiuwen.extension.workflow_node.end import End
from jiuwen.extension.workflow_node.exception_handler import (
    register_error_recovery_handler,
)
from jiuwen.extension.workflow_node.flow_agent import FlowAgent, FlowAgentConfig
from jiuwen.extension.workflow_node.flow_aggregate import Aggregate
from jiuwen.extension.workflow_node.flow_api import FlowApi
from jiuwen.extension.workflow_node.flow_card import FlowCard, FlowCardConfig
from jiuwen.extension.workflow_node.flow_exception import ExceptionInfo
from jiuwen.extension.workflow_node.flow_extractor import Extractor
from jiuwen.extension.workflow_node.flow_input import FlowInput
from jiuwen.extension.workflow_node.flow_mcp import FlowMcp
from jiuwen.extension.workflow_node.flow_message import Message
from jiuwen.extension.workflow_node.flow_qa import FlowQA, build_struct_input_schemas
from jiuwen.extension.workflow_node.flow_stream_transform import FlowStreamTransform
from jiuwen.extension.workflow_node.intent_detection import IntentDetection
from jiuwen.extension.workflow_node.llm_chain import LLMChain
from jiuwen.extension.workflow_node.loop_set_variable import LoopSetVariable
from jiuwen.extension.workflow_node.start import Start
from jiuwen.extension.workflow_node.sub_workflow import SubWorkflow
from jiuwen.extension.workflow.lazy_workflow import LazyWorkflow
from jiuwen.extension.wrapper.single_component_debug_wrapper import SingleComponentInfo
from jiuwen.multi_agent.agent_group.config import AgentGroupConfig, GroupSettings
from jiuwen.multi_agent.agent_group.hierarchical_group.agent_group import (
    HierarchicalAgentGroup,
)
from jiuwen.orchestration.flow.components.util import (
    format_pydantic_validation_error_message,
)
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.serve.controllers.execution.constants import DEFAULT_SUPPORTED_IR_VERSIONS
from jiuwen.serve.controllers.execution.enum import IRType
from jiuwen.serve.controllers.execution.manager import AsyncStateManager
from jiuwen.serve.controllers.execution.open_utils import (
    async_ir_load,
    deserialize_object,
    cache_agent_queue,
    cache_agent_group_queue,
)
from jiuwen.serve.controllers.execution.types import AgentIrValidator
from jiuwen.serve.controllers.execution.utils import AgentIrUtils, PluginIRConverter
from openjiuwen.core.common.exception.errors import (
    ValidationError as OpenjiuwenValidationError,
)
from openjiuwen.core.workflow import Workflow, WorkflowCard
from openjiuwen.core.workflow.components.base import ComponentAbility
from openjiuwen.core.workflow.components.component import WorkflowComponent
from openjiuwen.core.workflow.components.flow.branch_comp import BranchComponent
from openjiuwen.core.workflow.components.flow.branch_router import BranchRouter
from openjiuwen.core.workflow.components.flow.loop.loop_comp import (
    LoopComponent,
    LoopGroup,
    LoopBreakComponent,
)
from openjiuwen.core.workflow.workflow_config import ExceptionConfig
from pydantic import ValidationError

apply_workflow_sub_stream_patch()
apply_loop_body_session_cleanup_patch()
apply_loop_state_cleanup_patch()
from jiuwen.extension.workflow_node.utils import WorkflowMetadata

from jiuwen.serve.controllers.execution.ir_parallel_utils import (
    build_parallel_join_plan,
    collect_parallel_join_nodes,
)
from agent_runtime.common.ir_exceptions import IRBuildException

_AGENT_VERSION = "agentVersion"
_WORKFLOW_VERSION = "workflowVersion"
_USE_AGENT_CORE_MODEL_ENV = "USE_AGENT_CORE_MODEL"


class _LLMModelIdentifiers(NamedTuple):
    """创建 LLM 模型所需的标识集合（task/agent/conversation 三件套）。"""

    task_id: str
    agent_id: str
    conversation_id: str

_BASE_AGENT_SWITCH = "BASE_AGENT_SWITCH"
_AGENT_CORE_REGISTERED_MODEL_IDS = set()

# 可插拔的 ModelConfigProvider 工厂函数，默认使用 IRModelConfigProvider。
# WorkflowRunner 在初始化时根据 MODEL_CONFIG_STRATEGY 环境变量覆盖此函数，
# 使 IRConverter 内部的模型注册逻辑自动切换到对应的 Provider 实现。
_model_config_provider_factory = None


def set_model_config_provider_factory(factory):
    """设置全局 ModelConfigProvider 工厂函数。

    Args:
        factory: 无参可调用对象，返回 ModelConfigProvider 实例。
                 例如: lambda: OBSModelConfigProvider()
    """
    global _model_config_provider_factory
    _model_config_provider_factory = factory


def _get_model_config_provider():
    """获取当前 ModelConfigProvider 实例。"""
    from agent_runtime.common.model_providers import IRModelConfigProvider

    if _model_config_provider_factory is not None:
        return _model_config_provider_factory()
    return IRModelConfigProvider()
UNSUPPORTED_COMPONENT_DEBUG_LIST = [
    "jiuwen.start",
    "jiuwen.end",
    "jiuwen.message",
    "jiuwen.branch",
    "jiuwen.taskFlow",
]

_VALID_REF_PATH_CONTENT = r'[a-zA-Z_][a-zA-Z0-9_.]*'
_REFERENCE_PATTERN = re.compile(r"^\{(" + _VALID_REF_PATH_CONTENT + r")}$")
_REFERENCE_TOKEN_PATTERN = re.compile(r"(?<!\$)\{(" + _VALID_REF_PATH_CONTENT + r")}")
_OPEN_REFERENCE_PATTERN = re.compile(r"^\$\{([^{}]+)}$")
_OPEN_REFERENCE_TOKEN_PATTERN = re.compile(r"\$\{([^{}]+)}")
_NEGATION_PATTERN = re.compile(r"(?<![=!<>])!(?!=)")
_REFERENCE_ALIASES = {
    "system_fields": "systemFields",
    "user_fields": "userFields",
    "conversation_history": "conversationHistory",
    "dialogue_history": "dialogueHistory",
    "rawOutput": "raw_output",
}

_LOOP_TYPE_MAP = {
    "numLoop": "number",
    "arrayLoop": "array",
    "infiniteLoop": "always_true",
}

_SPECIAL_REF_ROOTS = frozenset(
    {
        "query",
        "sys",
        "memory",
        "conversationHistory",
        "dialogueHistory",
        "global",
        "_env",
        "_request",
    }
)

# Global variable reference pattern: ${node_start.memory.xxx}
_GLOBAL_REF_PATTERN_OLD = "${node_start.memory."
_GLOBAL_REF_PATTERN_NEW = "${MEMORY_VARIABLE."
_START_MEMORY_REF_TOKEN = re.compile(r"\$\{node_start\.memory\.([^{}]+)}")
_MEMORY_VARIABLE_REF_TOKEN = re.compile(r"\$\{MEMORY_VARIABLE\.([^{}]+)}")


def _convert_global_variable_refs_in_ir(ir_data: dict) -> dict:
    """Convert old global variable references to new format in IR data.

    Old format: ${node_start.memory.xxx}
    New format: ${MEMORY_VARIABLE.xxx}

    For start nodes, the memory dict in inputs contains actual values (not references),
    so it should be kept as-is.

    **COW (copy-on-write)**: avoids the previous ``copy.deepcopy(ir_data)``
    which dominated CPU on cache-hit paths. The top-level dict and the
    ``components`` list are shallow-copied as a safety net, while each
    component dict / configs sub-tree is only duplicated when a descendant
    string actually gets rewritten. Sub-trees without memory references
    keep their original references, so un-hit components cost zero copy.

    Args:
        ir_data: IR data dictionary containing workflow configuration.
            Treated as read-only; never mutated in place.

    Returns:
        dict: IR data with converted global variable references. May share
        un-modified sub-trees with the input.
    """
    if not ir_data or not isinstance(ir_data, dict):
        return ir_data

    # Only process workflow IR data (has 'components' field)
    components = ir_data.get("components", [])
    if not components:
        return ir_data

    # Top-level shallow copy as a safety net (≈ 1 dict + 1 list).
    new_ir = dict(ir_data)
    new_components = list(components)
    new_ir["components"] = new_components

    for i, component in enumerate(components):
        component_type = component.get("type", "")
        # Skip start nodes - their memory inputs contain actual values, not references
        if component_type == NodeType.START.value:
            continue

        # Mutable state holder for this iteration; passed into _cow_configs_field
        # to avoid closure-captured loop variables (G.FNM.02).
        state = {"comp": component, "configs": None}

        def _cow_configs_field(field_path: tuple, converter, comp, st) -> None:
            """COW-convert a sub-field under ``configs``.

            On hit, shallow-copies ``configs`` (and any intermediate dict
            along ``field_path``) and writes the converted value back. The
            component dict itself is shallow-copied the first time any
            field hits, so the original cached component is untouched.

            ``field_path`` is a tuple of dict keys, e.g.
            ``("branches",)`` or ``("io_configs", "inputs_schema")``.

            ``comp``/``st`` are required positional args (no defaults) to
            satisfy G.FNM.01 (no mutable default args) and G.FNM.02 (no
            closure-captured loop variables). Callers in the loop body
            pass the current iteration's ``component``/``state`` explicitly.
            """
            cur = comp.get("configs", {})
            for p in field_path:
                if not isinstance(cur, dict):
                    return
                cur = cur.get(p)
                if cur is None:
                    return
            if not cur:
                return

            converted = converter(cur)
            if converted is cur:
                return

            # Hit: shallow-copy the path configs → ... → field
            if st["configs"] is None:
                st["configs"] = dict(comp.get("configs", {}) or {})
            target = st["configs"]
            for p in field_path[:-1]:
                target[p] = dict(target[p])
                target = target[p]
            target[field_path[-1]] = converted

            if st["comp"] is comp:
                st["comp"] = dict(comp)
                st["comp"]["configs"] = st["configs"]
            else:
                st["comp"]["configs"] = st["configs"]

        if component_type == NodeType.SET_VARIABLE.value:
            config_settings = (component.get("configs") or {}).get("settings", [])
            if isinstance(config_settings, list):
                converted_settings = _convert_refs_in_schema(config_settings)
                if converted_settings is not config_settings:
                    if state["configs"] is None:
                        state["configs"] = dict(component.get("configs", {}) or {})
                    state["configs"]["settings"] = converted_settings
                    if state["comp"] is component:
                        state["comp"] = dict(component)
                        state["comp"]["configs"] = state["configs"]
                    else:
                        state["comp"]["configs"] = state["configs"]

        _cow_configs_field(("branches",), _convert_refs_in_schema, component, state)
        _cow_configs_field(("io_configs", "inputs_schema"), _convert_refs_in_schema, component, state)

        # Legacy inputs live directly under component (not under configs)
        inputs_orig = component.get("inputs", {})
        if inputs_orig:
            converted_inputs = _convert_refs_in_schema(inputs_orig)
            if converted_inputs is not inputs_orig:
                if state["comp"] is component:
                    state["comp"] = dict(component)
                state["comp"]["inputs"] = converted_inputs

        if state["comp"] is not component:
            new_components[i] = state["comp"]

    return new_ir


def _extract_start_memory_var(ref_str: str) -> str | None:
    if not isinstance(ref_str, str) or not ref_str.endswith("}"):
        return None
    if ref_str.startswith(_GLOBAL_REF_PATTERN_OLD):
        return ref_str[len(_GLOBAL_REF_PATTERN_OLD):-1]
    return None


def _convert_start_memory_refs_in_string(value: str) -> str:
    """Convert ${node_start.memory.xxx} → ${MEMORY_VARIABLE.xxx} in a string.

    Adds a C-level substring guard so that strings without the literal
    ``node_start.memory`` substring are returned as-is without invoking
    the regex engine — this is the dominant fast path on real IRs.
    """
    if not isinstance(value, str) or "node_start.memory" not in value:
        return value
    return _START_MEMORY_REF_TOKEN.sub(
        lambda match: f"${{MEMORY_VARIABLE.{match.group(1)}}}",
        value,
    )


def _convert_refs_in_schema(schema: dict | list) -> dict | list:
    """COW: convert ${node_start.memory.xxx} → ${MEMORY_VARIABLE.xxx} in schema.

    Returns a new dict/list when (and only when) some descendant string is
    actually rewritten. Sub-trees that contain no memory references keep
    their original reference, so the caller's cache is not mutated and
    untouched sub-trees are shared at zero copy cost.

    Args:
        schema: Input schema dict or list (treated read-only).

    Returns:
        The original ``schema`` reference if no replacement occurred, or a
        new dict/list sharing un-rewritten sub-trees with the original.
    """
    if isinstance(schema, dict):
        new = None
        for key, value in schema.items():
            if isinstance(value, str):
                converted = _convert_start_memory_refs_in_string(value)
                if converted is not value:
                    if new is None:
                        new = dict(schema)
                    new[key] = converted
            elif isinstance(value, (dict, list)):
                converted = _convert_refs_in_schema(value)
                if converted is not value:
                    if new is None:
                        new = dict(schema)
                    new[key] = converted
        return new if new is not None else schema
    if isinstance(schema, list):
        new = None
        for i, item in enumerate(schema):
            if isinstance(item, str):
                converted = _convert_start_memory_refs_in_string(item)
                if converted is not item:
                    if new is None:
                        new = list(schema)
                    new[i] = converted
            elif isinstance(item, (dict, list)):
                converted = _convert_refs_in_schema(item)
                if converted is not item:
                    if new is None:
                        new = list(schema)
                    new[i] = converted
        return new if new is not None else schema
    return schema


def _extract_memory_var_mappings(memory_section: dict) -> dict:
    """Recursively extract parent global variable mappings from a memory section.

    Each entry may be either:
      - "${MEMORY_VARIABLE.parent_var}" -> maps this key to parent_var
      - a nested dict -> recurse into it

    Args:
        memory_section: The 'memory' section of SubWorkflow input_schema.

    Returns:
        dict: Mapping from child key name to parent global variable name.
    """
    mappings = {}
    if not isinstance(memory_section, dict):
        return mappings

    for child_key, value in memory_section.items():
        if isinstance(value, str) and value.startswith("${MEMORY_VARIABLE.") and value.endswith("}"):
            # Extract parent variable name: ${MEMORY_VARIABLE.parent_var} -> parent_var
            parent_var = value[len("${MEMORY_VARIABLE."):-1]
            mappings[child_key] = parent_var
        elif isinstance(value, dict):
            # Recursively extract from nested dicts within memory section
            mappings.update(_extract_memory_var_mappings(value))

    return mappings


def _extract_global_var_mappings_from_schema(schema: dict) -> dict:
    """Extract global variable mappings from SubWorkflow input_schema.

    Only the 'memory' section contributes mappings. Fields under other
    sections (e.g., 'systemFields.query') must NOT be collected, because
    they reference parent workflow system fields and should not override
    the child workflow's own variable names.

    input_schema format:
        {"userFields": {...}, "memory": {"child_key": "${MEMORY_VARIABLE.parent_var}"}, ...}
    Returns mapping: {"child_key": "parent_var", ...}

    Args:
        schema: Input schema dict containing 'memory'/'userFields'/'systemFields' keys.

    Returns:
        dict: Mapping from child key name to parent global variable name.
    """
    if not isinstance(schema, dict):
        return {}

    memory_section = schema.get("memory")
    if not isinstance(memory_section, dict):
        return {}

    return _extract_memory_var_mappings(memory_section)


def _convert_subworkflow_global_var_refs(
        ir_data: dict,
        global_var_mappings: dict,
) -> dict:
    """Convert global variable references in sub-workflow IR using parent mappings.

    When SubWorkflow input_schema defines mappings like:
      {"sub_val": "${global.parent_var}"}
    The child workflow's internal operations should use parent variable names.

    This function converts all ${global.child_key} references to ${global.parent_var}
    in the sub-workflow IR.

    **COW (copy-on-write)**: avoids the previous ``copy.deepcopy(ir_data)``.
    Only components whose sub-trees actually contain a rewritten reference are
    duplicated; un-hit components keep their original references.

    Args:
        ir_data: Sub-workflow IR data. Treated as read-only; never mutated.
        global_var_mappings: Mapping from child key to parent global var name.

    Returns:
        dict: Converted sub-workflow IR data. May share un-modified sub-trees
        with the input.
    """
    if not ir_data or not isinstance(ir_data, dict) or not global_var_mappings:
        return ir_data

    components = ir_data.get("components", [])
    if not components:
        return ir_data

    # Top-level shallow copy as a safety net.
    new_ir = dict(ir_data)
    new_components = list(components)
    new_ir["components"] = new_components

    for i, component in enumerate(components):
        component_type = component.get("type", "")

        # Skip start nodes - they receive values, not references
        if component_type == NodeType.START.value:
            continue

        # Mutable state holder for this iteration; passed into _cow_configs_field
        # to avoid closure-captured loop variables (G.FNM.02).
        state = {"comp": component, "configs": None}

        def _cow_configs_field(field_path: tuple, converter, comp, st) -> None:
            """COW-convert a sub-field under ``configs`` for this component.

            ``comp``/``st`` are required positional args (no defaults) to
            satisfy G.FNM.01 (no mutable default args) and G.FNM.02 (no
            closure-captured loop variables). Callers in the loop body
            pass the current iteration's ``component``/``state`` explicitly.
            """
            cur = comp.get("configs", {})
            for p in field_path:
                if not isinstance(cur, dict):
                    return
                cur = cur.get(p)
                if cur is None:
                    return
            if not cur:
                return

            converted = converter(cur)
            if converted is cur:
                return

            if st["configs"] is None:
                st["configs"] = dict(comp.get("configs", {}) or {})
            target = st["configs"]
            for p in field_path[:-1]:
                target[p] = dict(target[p])
                target = target[p]
            target[field_path[-1]] = converted

            if st["comp"] is comp:
                st["comp"] = dict(comp)
                st["comp"]["configs"] = st["configs"]
            else:
                st["comp"]["configs"] = st["configs"]

        # SET_VARIABLE: only left.value (or left when it's a plain string) is
        # a writable reference target; right.value is a literal/source ref and
        # must NOT be mapped. COW along setting → left → value.
        if component_type == NodeType.SET_VARIABLE.value:
            config_settings = (component.get("configs") or {}).get("settings", [])
            if isinstance(config_settings, list):
                new_settings = None
                for idx, setting in enumerate(config_settings):
                    if not isinstance(setting, dict):
                        continue
                    left_obj = setting.get("left")
                    if isinstance(left_obj, dict) and "value" in left_obj:
                        original_value = left_obj["value"]
                        converted_value = _apply_global_var_mapping(original_value, global_var_mappings)
                        if converted_value is not original_value:
                            if new_settings is None:
                                new_settings = list(config_settings)
                            new_left = dict(left_obj)
                            new_left["value"] = converted_value
                            new_setting = dict(setting)
                            new_setting["left"] = new_left
                            new_settings[idx] = new_setting
                    elif isinstance(left_obj, str):
                        converted_left = _apply_global_var_mapping(left_obj, global_var_mappings)
                        if converted_left is not left_obj:
                            if new_settings is None:
                                new_settings = list(config_settings)
                            new_setting = dict(setting)
                            new_setting["left"] = converted_left
                            new_settings[idx] = new_setting
                if new_settings is not None:
                    if state["configs"] is None:
                        state["configs"] = dict(component.get("configs", {}) or {})
                    state["configs"]["settings"] = new_settings
                    if state["comp"] is component:
                        state["comp"] = dict(component)
                        state["comp"]["configs"] = state["configs"]
                    else:
                        state["comp"]["configs"] = state["configs"]

        _cow_configs_field(
            ("branches",),
            lambda s: _apply_global_var_mapping_to_schema(s, global_var_mappings),
            component,
            state,
        )
        _cow_configs_field(
            ("io_configs", "inputs_schema"),
            lambda s: _apply_global_var_mapping_to_schema(s, global_var_mappings),
            component,
            state,
        )

        # Legacy inputs live directly under component (not under configs)
        inputs_orig = component.get("inputs", {})
        if inputs_orig:
            converted_inputs = _apply_global_var_mapping_to_schema(inputs_orig, global_var_mappings)
            if converted_inputs is not inputs_orig:
                if state["comp"] is component:
                    state["comp"] = dict(component)
                state["comp"]["inputs"] = converted_inputs

        if state["comp"] is not component:
            new_components[i] = state["comp"]

    return new_ir


def _apply_global_var_mapping(ref_str: str, mappings: dict) -> str:
    """Apply global variable name mapping to a reference string.

    If ref_str is ${global.child_key} and mappings[child_key] = parent_var,
    return ${global.parent_var}.

    Adds a substring guard so that strings without either ``MEMORY_VARIABLE``
    or the legacy ``node_start.memory`` prefix bypass the regex engine —
    this is the dominant fast path on real IRs.

    Args:
        ref_str: Reference string (e.g., "${global.child_var}").
        mappings: Mapping from child key to parent var name.

    Returns:
        str: Converted reference string or original if no mapping exists.
    """
    if not isinstance(ref_str, str):
        return ref_str

    # Fast path: if the string has neither marker, no rewrite is possible.
    # 'in' on str is a C-level substring scan, ~ns; the regex sub below
    # would otherwise dominate CPU on schema-heavy IRs.
    if "MEMORY_VARIABLE" not in ref_str and _GLOBAL_REF_PATTERN_OLD not in ref_str:
        return ref_str

    def replace_memory_var(match: re.Match) -> str:
        child_var = match.group(1)
        parent_var = mappings.get(child_var)
        if parent_var:
            return f"${{MEMORY_VARIABLE.{parent_var}}}"
        return match.group(0)

    child_start_memory_var = _extract_start_memory_var(ref_str)
    if child_start_memory_var is not None:
        parent_var = mappings.get(child_start_memory_var)
        if parent_var:
            return f"${{MEMORY_VARIABLE.{parent_var}}}"

    mapped_ref = _MEMORY_VARIABLE_REF_TOKEN.sub(replace_memory_var, ref_str)
    if mapped_ref != ref_str:
        return mapped_ref

    return ref_str


def _apply_global_var_mapping_to_schema(schema: dict | list, mappings: dict) -> dict | list:
    """COW: recursively apply global var mapping to schema.

    Returns a new dict/list when (and only when) some descendant string is
    actually rewritten. Sub-trees with no mappable references keep their
    original reference, so the caller's cache is not mutated and un-hit
    sub-trees are shared at zero copy cost.

    Args:
        schema: Input schema dict or list (treated read-only).
        mappings: Mapping from child key to parent var name.

    Returns:
        The original ``schema`` reference if no replacement occurred, or a
        new dict/list sharing un-rewritten sub-trees with the original.
    """
    if isinstance(schema, dict):
        new = None
        for key, value in schema.items():
            if isinstance(value, str):
                converted = _apply_global_var_mapping(value, mappings)
                if converted is not value:
                    if new is None:
                        new = dict(schema)
                    new[key] = converted
            elif isinstance(value, (dict, list)):
                converted = _apply_global_var_mapping_to_schema(value, mappings)
                if converted is not value:
                    if new is None:
                        new = dict(schema)
                    new[key] = converted
        return new if new is not None else schema
    if isinstance(schema, list):
        new = None
        for i, item in enumerate(schema):
            if isinstance(item, str):
                converted = _apply_global_var_mapping(item, mappings)
                if converted is not item:
                    if new is None:
                        new = list(schema)
                    new[i] = converted
            elif isinstance(item, (dict, list)):
                converted = _apply_global_var_mapping_to_schema(item, mappings)
                if converted is not item:
                    if new is None:
                        new = list(schema)
                    new[i] = converted
        return new if new is not None else schema
    return schema


def _extract_source_component_ids(
    schema: dict, component_by_id: dict[str, Any]
) -> set[str]:
    """Extract source component IDs from reference paths in a schema.

    Parses the schema for reference patterns like ${node_id.field} and returns
    the set of source component IDs that exist in component_by_id.
    Skips special references (query, sys, global, etc.).
    """
    source_ids: set[str] = set()
    for ref_path in _iter_reference_paths(schema):
        source_id = ref_path.split(".", 1)[0]
        if not source_id or source_id in _SPECIAL_REF_ROOTS:
            continue
        if source_id in component_by_id:
            source_ids.add(source_id)
    return source_ids


class _LoopPassThroughComponent(WorkflowComponent):
    """空操作组件（对应官方文档的 EmptyNode），用作 break 条件路由流的循环体末端节点。
    无论 break 还是 continue 路径，迭代结束后都经过此节点。"""

    async def invoke(self, inputs, session, context):
        return {}


class _ParallelInvokeLaneDoneComponent(WorkflowComponent):
    """Control marker emitted when one parallel lane has completed."""

    async def invoke(self, inputs, session, context):
        return {}


class _ParallelTransformLaneDoneComponent(WorkflowComponent):
    """Stream-preserving control marker for a completed parallel lane."""

    async def transform(
        self, inputs: Any, session: Any, context: Any
    ) -> AsyncIterator[Any]:
        async for chunk in _iter_parallel_stream_inputs(inputs):
            yield chunk


async def _iter_parallel_stream_inputs(inputs: Any) -> AsyncIterator[Any]:
    if hasattr(inputs, "__aiter__"):
        async for chunk in inputs:
            yield chunk
        return
    if isinstance(inputs, dict):
        for value in inputs.values():
            async for chunk in _iter_parallel_stream_inputs(value):
                yield chunk
        return
    if isinstance(inputs, (list, tuple)):
        for value in inputs:
            async for chunk in _iter_parallel_stream_inputs(value):
                yield chunk
        return
    if inputs is not None:
        yield inputs


class _RoutedIntentDetection(IntentDetection):
    def __init__(self, configs: dict):
        super().__init__(configs)
        self._router = BranchRouter(True)

    def add_branch(
        self, condition: Any, target: str | list[str], branch_id: str | None = None
    ) -> None:
        self._router.add_branch(condition, target, branch_id=branch_id)

    async def invoke(
        self, inputs: Any, session: Any, context: Any, **kwargs: Any
    ) -> Any:
        self._router.set_session(session)
        return await super().invoke(inputs, session, context, **kwargs)

    def add_component(
        self, graph: Any, node_id: str, wait_for_all: bool = False
    ) -> None:
        graph.add_node(node_id, self.to_executable(), wait_for_all=wait_for_all)
        graph.add_conditional_edges(node_id, self._router)
        # Register branch targets for CNF barrier resolution at compile time
        if hasattr(graph, "register_branch_targets"):
            all_targets = self._router.all_targets
            if len(all_targets) > 1:
                graph.register_branch_targets(node_id, all_targets)


def _resolve_intent_fields(
    current_ir_data: Dict[str, Any],
    parent_intent: Optional[Dict[str, Any]],
) -> tuple[str, str]:
    """R-04: 父级 per-reference intent 覆盖,应用到 per-config metadata(不写缓存 IR 对象)。

    非空才覆盖(``or`` 短路),语义等价于旧实现的
    ``if child_intent.get("name"): ...`` / ``if child_intent.get("description"): ...``。
    parent_intent 非 dict 或字段为空时,回退子 IR 原值。
    """
    override = parent_intent if isinstance(parent_intent, dict) else {}
    intent_name = override.get("name") or current_ir_data.get("intent_name", "")
    intent_description = override.get("description") or current_ir_data.get(
        "intent_description", ""
    )
    return intent_name, intent_description


class IRConverter:
    """IR转换工具类。

    该类用于识别和转换中间表示(IR)数据，包括验证IR版本、创建Agent配置、
    从IR数据创建Agent和Agent Group配置、将IR数据转换为Agent或Agent Group实例等。
    """

    @staticmethod
    def extract_component_name_type_map(ir_data: dict) -> dict[str, dict]:
        """从 workflow IR 数据中提取 {component_id: {name, type}} 映射。

        用于在 TraceSchema → StreamData 转换时，用 IR 中定义的显示名称
        和类型覆盖 openjiuwen tracer 生成的 node_id 格式 componentName。

        Args:
            ir_data: Workflow IR 数据字典，包含 components 数组。

        Returns:
            dict: {component_id: {"name": str, "type": str}} 映射字典。
        """
        result: dict[str, dict] = {}
        components = ir_data.get("components") or []
        for comp in components:
            comp_id = comp.get("id")
            if not comp_id:
                continue
            result[comp_id] = {
                "name": comp.get("name", ""),
                "type": comp.get("type", ""),
            }
        return result

    @staticmethod
    async def extract_node_defs(ir_data: dict) -> dict[str, dict[str, dict]]:
        """从 workflow IR 数据中递归提取节点定义：{workflow_id: {node_id: {node_name, node_type, configs}}}。

        存入 session global_state 后供回调通过
        session.state().get_global("__node_defs__") 读取。

        为减少 checkpoint 序列化体积，configs 仅保留 type_convert 回调必需的
        userFields/systemFields 的 inputs/outputs 子字段，移除 model、
        templateContent、reference 等大字段。SubWorkflow 递归读取 reference
        在裁剪前从原始 configs 完成，不受裁剪影响。

        返回两层 dict，按 workflow_id 隔离，避免父子/嵌套工作流中
        相同 node_id 的映射互相覆盖。

        遇到 SubWorkflow 组件时，会递归加载子工作流 IR 并提取其内部节点定义，
        子工作流的定义以子工作流自身 workflowId 为 key 存储。

        Args:
            ir_data: Workflow IR 数据字典，包含 components 数组。

        Returns:
            dict: {workflow_id: {node_id: {node_name, node_type, configs}}} 两层映射字典。
        """
        workflow_id = ir_data.get("workflowId", "")
        result: dict[str, dict[str, dict]] = {}
        current_wf_defs: dict[str, dict] = {}
        components = ir_data.get("components") or []
        for comp in components:
            comp_id = comp.get("id")
            if not comp_id:
                continue
            # 原始 configs，用于递归读取 reference（裁剪前）
            raw_configs = comp.get("configs") or {}
            # 仅保留 type_convert 回调必需的 userFields/systemFields 子字段
            uf = raw_configs.get("userFields") or {}
            sf = raw_configs.get("systemFields") or {}
            node_def: dict = {
                "node_name": comp.get("name", ""),
                "node_type": comp.get("type", ""),
                "configs": {
                    "userFields": {
                        "inputs": uf.get("inputs", []),
                        "outputs": uf.get("outputs", []),
                    },
                    "systemFields": {
                        "inputs": sf.get("inputs", []),
                        "outputs": sf.get("outputs", []),
                    },
                },
            }
            current_wf_defs[comp_id] = node_def
            # 递归提取 SubWorkflow 子工作流内部节点
            ir_type = comp.get("type", "")
            if ir_type in {"jiuwen.subWorkflow", "jiuwen.workflowComposite"}:
                reference = raw_configs.get("reference") or {}
                child_path = reference.get("path", "")
                if child_path:
                    try:
                        child_ir = await async_ir_load(child_path)
                        child_defs = await IRConverter.extract_node_defs(child_ir)
                        result.update(child_defs)
                    except Exception:
                        logger.debug(
                            "Failed to load sub workflow IR from %s for node defs extraction",
                            child_path,
                        )
        if current_wf_defs and workflow_id:
            result[workflow_id] = current_wf_defs
        return result

    @staticmethod
    def node_defs_to_component_name_type_map(
        node_defs: dict[str, dict[str, dict]],
    ) -> dict[str, dict]:
        """从 extract_node_defs 的递归结果派生扁平的 {component_id: {name, type}} 映射。

        遍历所有 workflow_id 下的节点定义（含子工作流内部节点），
        展平为 component_id → {name, type}，用于在 TraceSchema → StreamData
        转换时覆盖 componentName/componentType。
        """
        result: dict[str, dict] = {}
        for wf_nodes in node_defs.values():
            for comp_id, node_def in wf_nodes.items():
                result[comp_id] = {
                    "name": node_def.get("node_name", ""),
                    "type": node_def.get("node_type", ""),
                }
        return result

    @staticmethod
    def validate_ir_version(ir_data: dict, ir_type: IRType):
        """
        Validate whether the IR data if of the supported version.
        :param ir_data: Dictionary parsed from JSON IR file.
        :param ir_type: IRType 'Agent' or 'Workflow'.
        """
        if ir_type == IRType.Agent and _AGENT_VERSION not in ir_data:
            raise JiuWenBaseException(
                error_code=StatusCode.IR_DATA_VALIDATION_ERROR.code,
                message=f"IR missing field - {_AGENT_VERSION}",
            )
        if ir_type == IRType.Workflow and _WORKFLOW_VERSION not in ir_data:
            raise JiuWenBaseException(
                error_code=StatusCode.IR_DATA_VALIDATION_ERROR.code,
                message=f"IR missing field - {_WORKFLOW_VERSION}",
            )

        supported_ir_version = os.environ.get(
            EXECUTION_SUPPORTED_IR_VERSIONS_KEY, DEFAULT_SUPPORTED_IR_VERSIONS
        )
        try:
            supported_ir_version_lst = safe_json_loads_raise_exception(
                supported_ir_version
            )
        except ValueError as e:
            raise JiuWenBaseException(
                error_code=StatusCode.IR_VERSION_INCORRECTLY_CONFIGURED.code,
                message=StatusCode.IR_VERSION_INCORRECTLY_CONFIGURED.errmsg,
            ) from e
        if not isinstance(supported_ir_version_lst, list):
            raise JiuWenBaseException(
                error_code=StatusCode.IR_VERSION_INCORRECTLY_CONFIGURED.code,
                message=StatusCode.IR_VERSION_INCORRECTLY_CONFIGURED.errmsg,
            )
        ir_version = ir_data.get(_AGENT_VERSION) or ir_data.get(_WORKFLOW_VERSION) or ""
        if ir_version not in supported_ir_version_lst:
            raise JiuWenBaseException(
                error_code=StatusCode.IR_VERSION_NOT_SUPPORTED.code,
                message=StatusCode.IR_VERSION_NOT_SUPPORTED.errmsg,
            )

    @staticmethod
    async def create_agent_config(
        ir_data, llm, task_model, task_id, conversation_id=""
    ):
        """
        Create agent configuration from IR data.
        """
        workflows = await AgentIrUtils.get_controller_workflow_configs(ir_data)
        intent_identification = AgentIrUtils.get_intent_identification_configs(ir_data)

        # 从 IR 中提取 plugins 配置
        agent_id = ir_data.get("agentId", "Default_Agent_Id")
        agent_version = ir_data.get("agentVersion", "Default_Agent_Version")
        agent_id_in_config = f"{agent_id}_{agent_version}"
        plugin_irs = ir_data.get("configs", {}).get("plugins")
        plugins = None
        logger.info(
            f"[PluginLoad] create_agent_config: plugin_irs count={len(plugin_irs) if plugin_irs else 0}, "
            f"agent_id={agent_id}, "
            f"configs keys="
            f"{list(ir_data.get('configs', {}).keys()) if isinstance(ir_data.get('configs'), dict) else 'N/A'}"
        )
        if plugin_irs:
            plugins = []
            for idx, plugin_ir in enumerate(plugin_irs):
                try:
                    plugin = PluginIRConverter.ir_to_plugin(plugin_ir, agent_id, conversation_id)
                    plugins.append(plugin)
                    logger.info(
                        f"[PluginLoad] create_agent_config: "
                        f"Successfully loaded plugin '{plugin_ir.get('name', 'unknown')}'"
                    )
                except Exception as e:
                    plugin_name = plugin_ir.get("name", plugin_ir.get("id", f"index_{idx}"))
                    logger.error(
                        f"[PluginLoad] create_agent_config: Failed to convert plugin '{plugin_name}': {e}. "
                        f"Skipping. IR keys: {list(plugin_ir.keys())}"
                    )

        # 从 IR 中提取 skills 配置
        skills_config = ir_data.get("configs", {}).get("skills", {})
        skill_dir = (
            skills_config.get("skill_dir", "")
            if isinstance(skills_config, dict)
            else ""
        )
        skill_info = (
            skills_config.get("skill_info", [])
            if isinstance(skills_config, dict)
            else []
        )

        return AgentConfig(
            model=llm,
            plan_config=task_model.configs.plan_config,
            plugins=plugins,
            workflows=workflows.normal,
            start_workflow=workflows.start,
            end_workflow=workflows.end,
            default_workflow=workflows.default,
            global_workflows=workflows.global_workflows,
            task_id=task_id,
            user_prompt=task_model.configs.sys_prompt_template,
            intent_workflows=workflows.intent,
            intent_identification=intent_identification,
            context=task_model.configs.context,
            memory_config=task_model.configs.memory_config,
            agent_id=agent_id_in_config,
            skill_dir=skill_dir,
            skill_info=skill_info,
        )

    @staticmethod
    async def create_all_agents_config_list(root_ir_data, conversation_id):
        """
        Create All agents config: List[AgentConfig]
        """
        all_configs: List[AgentConfig] = []
        agent_info_map: Dict[str, Dict[str, Any]] = {}

        async def _recursive_create(
            current_ir_data: Dict[str, Any],
            parent_metadata: Optional[AgentMetaData],
            parent_description: Optional[str] = None,
            parent_intent: Optional[Dict[str, Any]] = None,
        ) -> AgentConfig:
            """for each agent, return its child AgentConfig"""
            try:
                AgentIrValidator(**current_ir_data)
            except ValidationError as e:
                raise JiuWenBaseException(
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                    StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                        error_msg=f"Agent_ir validate failed, root_case={format_pydantic_validation_error_message(e)}"
                    ),
                ) from e
            # R-04: intent 覆盖写到 per-config metadata,不写缓存 IR 对象(避免污染 cache_ir_queue)
            _intent_name, _intent_description = _resolve_intent_fields(
                current_ir_data, parent_intent
            )
            current_metadata = AgentMetaData(
                id=current_ir_data.get("agentId"),
                name=current_ir_data.get("agentName"),
                description=parent_description
                or current_ir_data.get("description", ""),
                intent_name=_intent_name,
                intent_description=_intent_description,
                ir_path=current_ir_data.get("ir_path"),
                mode=current_ir_data.get("configs", {}).get("mode", "Controller"),
            )
            child_metadata_list: List[AgentMetaData] = []
            # check if current ir_data has child agents
            if current_ir_data.get("configs", {}).get("agents"):
                for child in current_ir_data.get("configs", {}).get("agents"):
                    logger.info(
                        f"loading ir data of {child.get('id')}",
                        simple_log="loading ir data of child",
                    )
                    # 支持从父Agent修改子Agent描述
                    parent_description = child.get("description", "")
                    child_ir_data = await async_ir_load(child.get("ir_path"))
                    # R-04: intent 覆盖通过参数下传到子的 current_metadata,不再原地写 child_ir_data
                    child_intent = child.get("intent") if isinstance(child.get("intent"), dict) else None
                    child_config = await _recursive_create(
                        child_ir_data,
                        current_metadata,
                        parent_description,
                        parent_intent=child_intent,
                    )
                    child_config.metadata.ir_path = child.get("ir_path")
                    child_config.metadata.mode = child.get(
                        "mode", child_config.metadata.mode
                    )
                    child_metadata_list.append(child_config.metadata)

            task_id = str(secrets.token_hex(24))
            logger.info(
                f"conversation_id: {conversation_id} generate task_id: {task_id} for this request",
                simple_log="conversation generate task",
            )
            task_model, model_configs = AgentIrUtils().get_task_model(
                current_ir_data, task_id
            )
            # 创建LLM模型（合并变量）
            if model_configs:
                llm = await IRConverter._create_llm_model(
                    model_configs,
                    cust_headers={},
                    project_id="",
                    identifiers=_LLMModelIdentifiers(
                        task_id=task_id,
                        conversation_id=conversation_id,
                        agent_id=current_metadata.id or "",
                    ),
                )
            else:
                llm = None
            logger.info(
                f"processing agent config of {current_metadata.id}",
                simple_log="processing agent config",
            )
            current_config = await IRConverter.create_agent_config(
                current_ir_data, llm, task_model, task_id
            )
            logger.info(
                f"get agent config of {current_metadata.id} success",
                simple_log="get agent config",
            )
            current_config.metadata = current_metadata
            current_config.parent_agent_metadata = parent_metadata
            current_config.child_agents_metadata = child_metadata_list
            current_config.ir_path = current_ir_data.get("ir_path")
            current_config.is_published = current_ir_data.get("is_published")

            agent_info_map[current_ir_data.get("agentId")] = {
                "task_id": task_id,
                "task_model": task_model,
            }
            all_configs.append(current_config)
            return current_config

        await _recursive_create(root_ir_data, parent_metadata=None)

        return all_configs, agent_info_map

    @staticmethod
    async def create_agent_group_config(root_ir_data, conversation_id):
        """
        Create agent group configuration from root IR data with cache
        """
        # 首先尝试从缓存获取
        cache_key = root_ir_data.get("ir_path", "")
        agent_group_config_result = None
        cache_enabled = str(
            os.environ.get("AGENT_GROUP_CACHE_ENABLE", "false")
        ).lower() == "true" and root_ir_data.get("is_published", False)
        if cache_enabled:
            agent_group_config_result = await timed_cache_op(
                "agent group config retrieval",
                cache_agent_group_queue.aget(cache_key),
                cache_key,
            )
            if agent_group_config_result:
                logger.info(
                    f"Cache hit for agent group config: {root_ir_data.get('agentId')}",
                    simple_log="Cache hit for agent group config",
                )
                return agent_group_config_result
            logger.info(
                f"Cache miss for agent group: {root_ir_data.get('agentId')}, need to create new config",
                simple_log="Cache miss for agent group, need to create new config",
            )

        agents_all, agent_info_map = await IRConverter.create_all_agents_config_list(
            root_ir_data, conversation_id
        )
        configs = root_ir_data.get("configs", {})
        max_agent_calls = configs.get("maxIteration")
        if max_agent_calls is None:
            max_agent_calls = root_ir_data.get("max_agent_calls", 10)
        if (
            not isinstance(max_agent_calls, int)
            or isinstance(max_agent_calls, bool)
            or max_agent_calls < 1
        ):
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg=f"Agent_ir validate failed, "
                    f"root_case= max_agent_calls is not a valid integer {max_agent_calls}"
                ),
            )

        agent_group_config_result = (
            AgentGroupConfig(
                group_id=root_ir_data.get("agentId"),
                group_name=root_ir_data.get("agentName"),
                description=root_ir_data.get("description", ""),
                main_agent=agents_all[-1],
                agents=agents_all,
                group_settings=GroupSettings(),
                max_agent_calls=max_agent_calls,
            ),
            agent_info_map,
        )
        if cache_enabled:
            await timed_cache_op(
                "Caching agent group config",
                cache_agent_group_queue.aput(cache_key, agent_group_config_result),
                cache_key,
            )
            logger.info(
                f"Cached agent group config for: {root_ir_data.get('agentId')}",
                simple_log="Caching agent group config",
            )

        return agent_group_config_result

    @staticmethod
    async def create_or_restore_agent(agent_config, conversation_id):
        """
        Create a new agent or restore from saved state.
        """
        cache_enabled = (
            str(os.environ.get(AGENT_CACHE_ENABLE_KEY, "false")).lower() == "true"
            and agent_config.is_published
        )
        agent = None
        if cache_enabled:
            agent = await timed_cache_op(
                "Agent instance retrieval",
                cache_agent_queue.aget(agent_config.ir_path),
                agent_config.ir_path,
            )

        if agent is None:
            agent = Agent(agent_config)
            if cache_enabled:
                await timed_cache_op(
                    "Caching agent instance",
                    cache_agent_queue.aput(agent_config.ir_path, agent),
                    agent_config.ir_path,
                )

        serialized_data = await AsyncStateManager().get_state(conversation_id)
        if not serialized_data:
            return agent
        agent_state = deserialize_object(serialized_data)
        await agent.load_state(agent_state)
        return agent

    @staticmethod
    def identify_ir(ir_data: dict) -> IRType:
        """
        识别IR数据是用于Agent还是Workflow。

        该方法通过检查IR数据中的特定字段（如'workflowId'和'agentId'）来判断IR数据的类型。
        如果IR数据中包含'workflowId'，则识别为Workflow类型；
        如果包含'agentId'，则进一步判断是否为多Agent(MultiAgents)类型；
        如果既不包含'workflowId'也不包含'agentId'，则抛出异常。

        在识别类型后，会调用validate_ir_version方法验证IR版本是否受支持。

        Args:
            ir_data (dict): 从JSON IR文件解析得到的字典数据。

        Returns:
            IRType: 返回IR类型，可能是'Agent'、'Workflow'或'MultiAgents'。

        Raises:
            JiuWenBaseException: 如果IR数据既不包含'workflowId'也不包含'agentId'时抛出异常。
        """
        if "workflowId" in ir_data:
            ir_type = IRType.Workflow
        elif "agentId" in ir_data:
            agents = ir_data.get("configs", {}).get("agents", [])
            if agents:
                # 有任何子 Agent 配置就走 MultiAgents（包括 PlanExecute 模式的子 Agent）
                ir_type = IRType.MultiAgents
            elif "deep_search_execute_mode" in ir_data.get("configs"):
                ir_type = IRType.DeepResearch
            else:
                ir_type = IRType.Agent
        else:
            raise JiuWenBaseException(
                error_code=StatusCode.IR_DATA_VALIDATION_ERROR.code,
                message=StatusCode.IR_DATA_VALIDATION_ERROR.errmsg,
            )
        IRConverter.validate_ir_version(ir_data, ir_type)
        return ir_type

    @staticmethod
    async def ir_to_agent(ir_data: dict, conversation_id="", **kwargs) -> Agent:
        """
        Convert IR data to an Agent instance.
        :param ir_data: Dictionary parsed from JSON IR file.
        :param conversation_id: Conversation ID for state management.
        :return: Agent instance.
        """
        IRConverter._validate_agent_ir(ir_data)

        task_id = get_x_execution_id()
        logger.info(
            f"conversation_id: {conversation_id} generate task_id: {task_id} for this request"
        )
        task_model, model_configs = AgentIrUtils().get_task_model(ir_data, task_id)
        cust_headers = kwargs.get("cust_headers", {})
        if model_configs:
            llm = await IRConverter._create_llm_model(
                model_configs,
                cust_headers,
                kwargs.get("project_id", ""),
                identifiers=_LLMModelIdentifiers(
                    task_id=task_id,
                    conversation_id=conversation_id,
                    agent_id=ir_data.get("agentId", ""),
                ),
            )
        else:
            llm = None
        agent_config = await IRConverter.create_agent_config(
            ir_data, llm, task_model, task_id, conversation_id
        )

        # 设置子Agent元数据（用于Controller模式判断是否有PE Agent）
        IRConverter._set_child_agents_metadata(agent_config, ir_data)

        # 创建或恢复agent
        agent = await IRConverter.create_or_restore_agent(agent_config, conversation_id)
        agent = IRConverter._finalize_agent(
            agent,
            agent_config,
            task_model,
            ir_data,
            cust_headers,
            conversation_id=conversation_id,
        )
        return IRConverter._wrap_agent_with_facade(agent)

    @staticmethod
    async def ir_to_agent_group(
        root_ir_data: dict, conversation_id="", **kwargs
    ) -> HierarchicalAgentGroup:
        """
        将IR数据转换为AgentGroup实例。

        该异步方法接收从JSON IR文件解析出的字典数据，创建或恢复Agent Group配置，并更新Agent Group的提示信息。
        它首先调用create_agent_group_config方法生成Agent Group配置和Agent信息映射，然后调用create_or_restore_agent_group方法创建或恢复Agent Group实例。
        最后，使用update_group_prompt方法更新Agent Group的提示信息。

        Args:
            root_ir_data (dict): 从JSON IR文件解析得到的字典数据。
            conversation_id (str): 用于状态管理的对话ID。
            **kwargs: 可变关键字参数，用于传递额外的信息。

        Returns:
            HierarchicalAgentGroup: 转换后的Agent Group实例。

        """
        (
            agent_group_config,
            agent_info_map,
        ) = await IRConverter.create_agent_group_config(root_ir_data, conversation_id)
        agent_group = await IRConverter.create_or_restore_agent_group(
            agent_group_config, conversation_id
        )
        agent_group.update_group_prompt(agent_info_map)
        return agent_group

    @staticmethod
    async def create_or_restore_agent_group(
        agent_group_config: AgentGroupConfig, conversation_id: str
    ) -> HierarchicalAgentGroup:
        """
        create_or_restore_agent_group
        Args:
            agent_group_config:
            conversation_id: String

        Returns:

        """
        agent_group = HierarchicalAgentGroup(agent_group_config)
        serialized_data = await AsyncStateManager().get_state(conversation_id)
        if not serialized_data:
            await agent_group.start()
            return agent_group
        group_state = deserialize_object(serialized_data)
        await agent_group.start(group_state)
        return agent_group

    @staticmethod
    async def ir_to_workflow(ir_data: dict, **kwargs) -> Workflow:
        """
        Convert IR data to a LazyWorkflow shell wrapping an openjiuwen Workflow.

        Returns a ``LazyWorkflow`` — a lightweight ``Workflow`` subclass whose
        ``invoke``/``stream`` defer the actual ``build_openjiuwen_workflow_from_ir``
        call to first execution. This avoids eagerly building the entire graph
        (and all child workflows) at registration time when only a subset of
        branches will actually be executed per request.

        :param ir_data: Dictionary parsed from JSON IR file.
        :param kwargs: Forwarded to ``build_openjiuwen_workflow_from_ir`` at
            instantiation time (preserved on the LazyWorkflow shell).
        :return: LazyWorkflow (subclass of Workflow).
        """
        # Convert old global variable references to new format
        converted_ir_data = _convert_global_variable_refs_in_ir(ir_data)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("param extra: parent converted_ir_data: %s", converted_ir_data)
        return LazyWorkflow(ir_data=converted_ir_data, build_kwargs=kwargs)

    @staticmethod
    async def async_ir_to_workflow(ir_data: dict, **kwargs) -> Workflow:
        """Async alias of :meth:`ir_to_workflow`.

        Returns a ``LazyWorkflow`` so that the actual Workflow build is deferred
        to the first ``invoke``/``stream`` call. Kept as async for backward
        compatibility with callers that use ``await``.

        Args:
            ir_data (dict): Dictionary parsed from JSON IR file.
            **kwargs: Forwarded to ``build_openjiuwen_workflow_from_ir`` at
                instantiation time.

        Returns:
            LazyWorkflow (subclass of Workflow).
        """
        # Convert old global variable references to new format
        converted_ir_data = _convert_global_variable_refs_in_ir(ir_data)
        return LazyWorkflow(ir_data=converted_ir_data, build_kwargs=kwargs)

    @staticmethod
    async def build_openjiuwen_workflow_from_ir(ir_data: dict, **kwargs) -> Workflow:
        """Core IR -> openjiuwen Workflow conversion.

        Public entry point for materializing an IR dict into an executable
        Workflow. Called directly by callers that need a fully-built graph
        (e.g. white-box tests inspecting ``_internal._workflow_spec``), and
        called by ``LazyWorkflow.instantiate`` on first ``invoke``/``stream``.
        """
        import time as _time

        t_total = _time.perf_counter()

        if not isinstance(ir_data, dict):
            raise ValueError("ir_data must be a dict")

        register_error_recovery_handler()

        card = WorkflowCard(
            id=ir_data.get("workflowId") or ir_data.get("agentId") or "",
            name=ir_data.get("workflowName")
                or ir_data.get("workflowId")
                or ir_data.get("agentName")
                or ir_data.get("agentId")
                or "",
            description=ir_data.get("description") or "",
        )
        workflow = Workflow(card=card)

        global_model = (ir_data.get("configs") or {}).get("model")

        components = ir_data.get("components") or []
        if not components:
            raise ValueError("ir_data.components is empty")

        node_by_id = {node.get("id"): node for node in components if node.get("id")}
        connections = _normalize_list(ir_data.get("connections") or [])
        parallel_join_nodes = collect_parallel_join_nodes(connections, node_by_id)
        parallel_join_plan = build_parallel_join_plan(connections, node_by_id)

        component_by_id: dict[str, Any] = {}

        # Pre-compute stream source IDs directly from IR data.
        # This local set is the single source of truth for stream-source
        # membership throughout this build; it avoids any cross-request
        # state leakage (the previous class-level _STREAM_SOURCE_IDS was
        # shared across concurrent builds and never reset).
        ir_stream_source_ids: set[str] = set()
        _llm_types = {
            "jiuwen.llm",
            "jiuwen.llm_chain",
            "jiuwen.llmChain",
            "jiuwen.LLMComponent",
        }
        for node in components:
            nid = node.get("id")
            ntype = node.get("type", "")
            cfgs = node.get("configs") or {}
            if ntype in _llm_types and bool(cfgs.get("stream", False)):
                ir_stream_source_ids.add(nid)
            elif ntype in IRConverter._STREAMING_API_TYPES and bool(
                cfgs.get("streaming", False)
            ):
                ir_stream_source_ids.add(nid)

        # Pre-compute stream connection targets from explicit IR connections.
        stream_input_target_ids: set[str] = set()
        for connection in connections:
            source = ((connection.get("source") or {}).get("componentId") or "").strip()
            target = ((connection.get("target") or {}).get("componentId") or "").strip()
            branch_id = ((connection.get("source") or {}).get("branchId") or "").strip()
            if not source or not target or branch_id:
                continue
            if parallel_join_plan.rewrite_target(source, target):
                continue
            target_type = node_by_id.get(target, {}).get("type", "")
            is_stream_capable = (
                target_type in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES
            )
            if is_stream_capable and source in ir_stream_source_ids:
                # Aggregate only accepts stream input when ALL its $ref inputs
                # come from stream sources; otherwise use regular INVOKE path.
                if target_type in IRConverter._AGGREGATE_TYPES:
                    continue
                stream_input_target_ids.add(target)

        parallel_stream_done_inputs: dict[str, dict] = {}
        for connection in connections:
            source = ((connection.get("source") or {}).get("componentId") or "").strip()
            target = ((connection.get("target") or {}).get("componentId") or "").strip()
            branch_id = ((connection.get("source") or {}).get("branchId") or "").strip()
            if not source or not target or branch_id:
                continue
            done_node = parallel_join_plan.rewrite_target(source, target)
            if not done_node:
                continue
            target_type = node_by_id.get(target, {}).get("type", "")
            is_stream_join_edge = (
                source in ir_stream_source_ids
                and target_type in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES
                and target_type not in IRConverter._AGGREGATE_TYPES
            )
            if is_stream_join_edge:
                parallel_stream_done_inputs[done_node] = {
                    "userFields": {"stream": "${" + source + "}"}
                }

        # Pre-collect all loop body component IDs so that root-level connection
        # processing can skip inter-body connections (they belong to LoopGroup, not main workflow).
        _loop_body_ids: set[str] = set()
        for _n in components:
            if _n.get("type") == "jiuwen.loop":
                for _bid in (_n.get("configs") or {}).get("loopBody") or []:
                    if isinstance(_bid, str) and _bid in node_by_id:
                        _loop_body_ids.add(_bid)

        pending_end_nodes: list[dict] = []
        pending_branch_nodes: list[dict] = []
        for idx, node in enumerate(components):
            node_id = node.get("id")
            is_stream_target = node_id in stream_input_target_ids
            component = await IRConverter._add_component(
                workflow,
                node,
                global_model,
                stream_inputs_schema=_convert_schema(node.get("inputs") or {})
                if is_stream_target
                else None,
                pending_end_nodes=pending_end_nodes,
                pending_branch_nodes=pending_branch_nodes,
                node_by_id=node_by_id,
                ir_connections=connections,
                stream_source_ids=ir_stream_source_ids,
                parallel_join_nodes=parallel_join_nodes,
            )
            if component is not None:
                component_by_id[node.get("id")] = component

        for done_node_id in parallel_join_plan.done_nodes:
            if done_node_id in component_by_id:
                continue
            stream_inputs_schema = parallel_stream_done_inputs.get(done_node_id)
            if stream_inputs_schema:
                lane_done = _ParallelTransformLaneDoneComponent()
                workflow.add_workflow_comp(
                    done_node_id,
                    lane_done,
                    stream_inputs_schema=stream_inputs_schema,
                    comp_ability=[ComponentAbility.TRANSFORM],
                    wait_for_all=True,
                )
            else:
                lane_done = _ParallelInvokeLaneDoneComponent()
                workflow.add_workflow_comp(done_node_id, lane_done, inputs_schema={})
            component_by_id[done_node_id] = lane_done
        end_node_ids = {p["node_id"] for p in pending_end_nodes}
        stream_connection_targets: set[str] = set()
        batch_connection_targets: set[str] = set()
        deferred_connections: list[tuple[str, str, bool]] = []
        branch_connections: list[tuple[str, str, str]] = []
        existing_connections: set[tuple[str, str]] = set()

        # Phase 1: wire branch routes before BranchComponent/IntentDetection join the
        # graph so add_workflow_comp → register_branch_targets sees populated routers.
        for connection in connections:
            source = ((connection.get("source") or {}).get("componentId") or "").strip()
            target = ((connection.get("target") or {}).get("componentId") or "").strip()
            branch_id = ((connection.get("source") or {}).get("branchId") or "").strip()
            if not source or not target:
                continue
            if source.endswith("_input") or target.endswith("_output"):
                continue
            if source in _loop_body_ids and target in _loop_body_ids:
                continue
            if not branch_id or "@@" in branch_id:
                continue
            target = (
                parallel_join_plan.rewrite_target(source, target, branch_id) or target
            )
            # Branch connections (default/non-default) are batch paths
            if target in end_node_ids:
                batch_connection_targets.add(target)
            branch_connections.append((source, target, branch_id))

        IRConverter._add_branch_connections_with_default_last(
            component_by_id, node_by_id, branch_connections
        )

        IRConverter._register_pending_branch_nodes(workflow, pending_branch_nodes)

        # Phase 2: batch/stream edges and non-branch connections
        for connection in connections:
            source = ((connection.get("source") or {}).get("componentId") or "").strip()
            target = ((connection.get("target") or {}).get("componentId") or "").strip()
            branch_id = ((connection.get("source") or {}).get("branchId") or "").strip()
            if not source or not target:
                continue
            if source.endswith("_input") or target.endswith("_output"):
                continue
            # Skip connections between loop body components — they belong to LoopGroup
            if source in _loop_body_ids and target in _loop_body_ids:
                continue
            if branch_id:
                continue
            is_stream = IRConverter._is_stream_connection(
                components, source, target, ir_stream_source_ids
            )
            rewritten_target = None
            rewritten_target = parallel_join_plan.rewrite_target(source, target)
            if rewritten_target:
                existing_connections.add((source, target))
                target = rewritten_target
            existing_connections.add((source, target))
            if is_stream:
                stream_connection_targets.add(target)
            if target in end_node_ids:
                if not is_stream:
                    batch_connection_targets.add(target)
                deferred_connections.append((source, target, is_stream))
            elif is_stream:
                workflow.add_stream_connection(source, target)
            else:
                workflow.add_connection(source, target)

        error_branch_groups: dict[str, list[tuple[str, str]]] = {}
        for connection in connections:
            _bid = ((connection.get("source") or {}).get("branchId") or "").strip()
            if _bid and "@@" in _bid:
                _src = (
                    (connection.get("source") or {}).get("componentId") or ""
                ).strip()
                _tgt = (
                    (connection.get("target") or {}).get("componentId") or ""
                ).strip()
                if _src and _tgt:
                    error_branch_groups.setdefault(_src, []).append((_tgt, _bid))

        for _src_id, _branches in error_branch_groups.items():
            _branch_comp = BranchComponent()
            _branch_node_id = f"{_src_id}_error_branch"
            _branches.sort(
                key=lambda item: IRConverter._branch_registration_sort_key(
                    _src_id, item[1], node_by_id
                )
            )
            for _target, _branch_id in _branches:
                _source_node = node_by_id.get(_src_id) or {}
                _source_type = _source_node.get("type", "")
                _cond = _resolve_branch_condition(
                    _source_node, _source_type, _branch_id
                )
                _branch_comp.add_branch(_cond, _target, branch_id=_branch_id)
            workflow.add_workflow_comp(
                _branch_node_id,
                _branch_comp,
                inputs_schema={"userFields": {"passthrough": "${" + _src_id + "}"}},
            )
            workflow.add_connection(_src_id, _branch_node_id)

        _parallel_join_has_stream_lane: dict[str, bool] = {}
        _parallel_stream_source_to_done: dict[str, str] = {}
        for join_spec in parallel_join_plan.joins.values():
            has_stream_lane = any(
                lane.done_node in parallel_stream_done_inputs
                for lane in join_spec.lanes
            )
            _parallel_join_has_stream_lane[join_spec.join_target] = has_stream_lane
            if join_spec.join_target in end_node_ids:
                batch_connection_targets.add(join_spec.join_target)
                if has_stream_lane:
                    stream_connection_targets.add(join_spec.join_target)
            if has_stream_lane:
                for lane in join_spec.lanes:
                    if lane.done_node in parallel_stream_done_inputs:
                        for terminal_source, _ in lane.terminals:
                            _parallel_stream_source_to_done[terminal_source] = lane.done_node

        for pending in pending_end_nodes:
            node_id = pending["node_id"]
            end = pending["end"]
            inputs_schema = pending["inputs_schema"]
            is_stream_out = pending["is_stream_out"]
            batch_schema, stream_schema = _split_inputs_schema_by_source(
                inputs_schema, ir_stream_source_ids
            )
            # Parallel join stream producer is _parallel_done, not the original source;
            # rewrite refs so StreamProcessor can resolve values by producer_id.
            if stream_schema and _parallel_stream_source_to_done:
                stream_schema = _rewrite_stream_schema_refs(
                    stream_schema, _parallel_stream_source_to_done
                )
            # Determine incoming edge types for this End node.
            # batch_schema may contain special refs (_env, _request, query, etc.) and
            # literal values in addition to component refs; all need the INVOKE path.
            has_stream = node_id in stream_connection_targets or stream_schema
            has_batch = node_id in batch_connection_targets or bool(batch_schema)

            if hasattr(end, "set_expect_mix"):
                end.set_expect_mix(has_batch and has_stream)

            set_end_kwargs: dict = {}
            if has_batch and has_stream:
                # Split schema by source type to avoid duplicate keys
                set_end_kwargs["inputs_schema"] = batch_schema if batch_schema else {}
                set_end_kwargs["stream_inputs_schema"] = (
                    stream_schema if stream_schema else {}
                )
            elif has_batch:
                set_end_kwargs["inputs_schema"] = inputs_schema
            elif has_stream:
                set_end_kwargs["stream_inputs_schema"] = inputs_schema
            else:
                set_end_kwargs["inputs_schema"] = inputs_schema
            if is_stream_out:
                set_end_kwargs["response_mode"] = "streaming"

            workflow.set_end_comp(node_id, end, **set_end_kwargs)

        for source, target, is_stream in deferred_connections:
            existing_connections.add((source, target))
            if is_stream:
                workflow.add_stream_connection(source, target)
            else:
                workflow.add_connection(source, target)
        for join_spec in parallel_join_plan.joins.values():
            lane_done_nodes = [lane.done_node for lane in join_spec.lanes]
            if len(lane_done_nodes) >= 2:
                has_stream_lane = _parallel_join_has_stream_lane.get(
                    join_spec.join_target, False
                )
                if has_stream_lane and join_spec.join_target in end_node_ids:
                    stream_done_nodes = [
                        n for n in lane_done_nodes
                        if n in parallel_stream_done_inputs
                    ]
                    invoke_done_nodes = [
                        n for n in lane_done_nodes
                        if n not in parallel_stream_done_inputs
                    ]
                    for n in stream_done_nodes:
                        workflow.add_stream_connection(n, join_spec.join_target)
                    if invoke_done_nodes:
                        workflow.add_connection(invoke_done_nodes, join_spec.join_target)
                else:
                    workflow.add_connection(lane_done_nodes, join_spec.join_target)

        # Add missing connections based on schema references.
        # Strategy:
        # - Auto-complete stream edges only when target supports stream input.
        # - Auto-complete batch edges for mix-mode targets (Message/End/Card/...)
        #   when schema references a stream source. Aggregate reads all $ref fields
        #   from io_state (incl. stream LLM via get_stream_output) and must not get
        #   extra batch triggers here. Do NOT auto-add batch edges to pure-batch
        #   nodes like Code — that bypasses intermediate nodes and can schedule them
        #   before the stream producer finishes.
        all_target_ids: set[str] = set()
        for connection in connections:
            s = ((connection.get("source") or {}).get("componentId") or "").strip()
            t = ((connection.get("target") or {}).get("componentId") or "").strip()
            bid = ((connection.get("source") or {}).get("branchId") or "").strip()
            if s and t and not bid:
                all_target_ids.add(t)

        for target_id in all_target_ids:
            target_node = node_by_id.get(target_id)
            if not target_node:
                continue
            schema = _convert_schema(target_node.get("inputs") or {})
            schema_source_ids = _extract_source_component_ids(schema, component_by_id)
            # Target participates in mix mode if its schema references any stream source
            has_stream_ref = any(
                sid in ir_stream_source_ids for sid in schema_source_ids
            )
            target_type = target_node.get("type", "")
            for source_id in schema_source_ids:
                if source_id == target_id:
                    continue
                if (source_id, target_id) in existing_connections:
                    continue
                is_stream = source_id in ir_stream_source_ids
                if (
                    is_stream
                    and target_type in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES
                    and target_type not in IRConverter._AGGREGATE_TYPES
                ):
                    workflow.add_stream_connection(source_id, target_id)
                    existing_connections.add((source_id, target_id))
                elif (
                    has_stream_ref
                    and target_type in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES
                    and target_type not in IRConverter._AGGREGATE_TYPES
                ):
                    workflow.add_connection(source_id, target_id)
                    existing_connections.add((source_id, target_id))

        performance_logger.info(
            f"ir_build_total|{round((_time.perf_counter() - t_total) * 1000)}"
        )
        # 统一为每个组件实例赋值同 workflow 的 node_id 集合，供 End 节点 ref 过滤使用
        # 用 dict（keys 为 node_id）兼容 EndRefInputFilterContext 的 isinstance(dict) 检查
        wf_node_ids = {nid: {} for nid in component_by_id.keys()}
        for comp in component_by_id.values():
            try:
                setattr(comp, "_workflow_node_ids", wf_node_ids)
            except Exception:
                logger.debug(
                    "Failed to attach _workflow_node_ids to component %r",
                    type(comp).__name__,
                    exc_info=True,
                )
        return workflow

    @staticmethod
    async def _try_load_sub_workflow(
            configs: dict,
            parent_global_var_mappings: dict | None = None,
    ) -> Optional[Workflow]:
        reference = configs.get("reference", {})
        child_path = reference.get("path", "")
        if not child_path:
            return None
        try:
            child_ir = await async_ir_load(child_path)
        except Exception as e:
            raise IRBuildException(f"从缓存或存储读取 IR 文件失败: {child_path}, {e}") from e
        # First convert old refs to new format
        converted_child_ir = _convert_global_variable_refs_in_ir(child_ir)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("param extra: child converted ir: %s", converted_child_ir)
        # Then apply parent's global variable mappings
        if parent_global_var_mappings:
            converted_child_ir = _convert_subworkflow_global_var_refs(
                converted_child_ir, parent_global_var_mappings
            )
        # Return a LazyWorkflow shell — child workflow graph is built lazily
        # on first invoke/stream, i.e. only when the parent actually reaches
        # this SubWorkflow node at runtime.
        return LazyWorkflow(ir_data=converted_child_ir, ir_path=child_path)

    @staticmethod
    async def _create_component(
        node: dict,
        global_model: dict | None,
        *,
        node_by_id: dict[str, dict] | None = None,
        ir_connections: list[dict] | None = None,
    ) -> tuple[Any, str, dict]:
        """纯组件创建，不依赖 Workflow。

        返回 (component_instance, node_type, configs)。
        """
        node_id = node.get("id")
        node_name = node.get("name")
        node_type = node.get("type")
        configs = dict(node.get("configs") or {})
        if "name" not in configs and node_name:
            configs["name"] = node_name
        inputs_schema = _convert_schema(node.get("inputs") or {})
        outputs_schema = _convert_schema(node.get("outputs") or {})
        # Add output field references with #end_ prefix only for End component,
        # which uses them to know which fields to include in the response.
        if node_type == "jiuwen.end":
            output_user_fields = outputs_schema.get("userFields", {})
            if isinstance(output_user_fields, dict):
                if "userFields" not in inputs_schema:
                    inputs_schema["userFields"] = {}
                if isinstance(inputs_schema["userFields"], list):
                    for user_field, value in output_user_fields.items():
                        inputs_schema["userFields"].append("#end_" + user_field)
                elif isinstance(inputs_schema["userFields"], dict):
                    for user_field, value in output_user_fields.items():
                        inputs_schema["userFields"]["#end_" + user_field] = value
        if node_type == "jiuwen.start":
            result = Start(configs)
            return result, node_type, configs

        if node_type == "jiuwen.end":
            result = End(_normalize_end_config(configs))
            return result, node_type, configs

        if node_type == "jiuwen.message":
            result = Message(configs)
            return result, node_type, configs

        if node_type in {
            "jiuwen.llm",
            "jiuwen.llm_chain",
            "jiuwen.llmChain",
            "jiuwen.LLMComponent",
        }:
            if global_model and "model" not in configs:
                configs["model"] = global_model
            elif "model" not in configs and "modelName" in configs:
                configs["model"] = {
                    "modelName": configs.pop("modelName"),
                    "modelType": configs.pop("modelType", "chat"),
                    "hyperParameters": configs.pop("hyperParameters", {}),
                    "extension": configs.pop("extension", {}),
                }
            result = LLMChain(configs)
            return result, node_type, configs

        if node_type == "jiuwen.questioner":
            return Questioner(_build_questioner_config(configs)), node_type, configs

        if node_type == "EI.qa":
            user_fields_config = configs.get("userFields")
            user_field_inputs = []
            if isinstance(user_fields_config, dict):
                user_field_inputs = user_fields_config.get("inputs") or []
            configs["struct_input_schemas"] = build_struct_input_schemas(
                node.get("inputs") or [],
                user_field_inputs,
                configs.get("struct_input_schemas") or {},
            )
            return FlowQA(configs), node_type, configs

        if node_type == "EI.ParamOutput":
            return ParamOutput(configs), node_type, configs

        if node_type == "jiuwen.code":
            return FlowCode(configs), node_type, configs

        if node_type == "jiuwen.knowledgeRetrieval":
            return FlowKnowledgeRetrieval(configs), node_type, configs

        if node_type == "jiuwen.intentDetection":
            return (
                _RoutedIntentDetection(_normalize_intent_detection_config(configs)),
                node_type,
                configs,
            )

        if node_type == "jiuwen.branch":
            return BranchComponent(), node_type, configs

        if node_type in {"jiuwen.input", "jiuwen.flowInput"}:
            return FlowInput(configs), node_type, configs

        if node_type in {
            "jiuwen.aggregate",
            "jiuwen.flowAggregate",
            "jiuwen.aggregation",
        }:
            return Aggregate(configs), node_type, configs

        if node_type in {"jiuwen.card", "jiuwen.flowCard"}:
            return FlowCard(FlowCardConfig.model_validate(configs)), node_type, configs

        if node_type in {"jiuwen.extractor", "jiuwen.infoExtraction"}:
            return Extractor(), node_type, configs

        if node_type in {"jiuwen.plugin", "jiuwen.api", "jiuwen.flowApi"}:
            return FlowApi(configs), node_type, configs

        if node_type in {"jiuwen.mcp", "jiuwen.flowMcp"}:
            return FlowMcp(configs), node_type, configs

        if node_type in {"jiuwen.agent", "jiuwen.flowAgent"}:
            return (
                FlowAgent(FlowAgentConfig.model_validate(configs)),
                node_type,
                configs,
            )

        if node_type in {"jiuwen.subWorkflow", "jiuwen.workflowComposite"}:
            return SubWorkflow({**configs, "node_id": node_id}), node_type, configs

        if node_type == "EI.ComplexIntentDetection":
            return (
                ComplexIntentDetection(configs, node_id=node_id, node_name=configs.get("name", "")),
                node_type,
                configs,
            )

        if node_type == "jiuwen.loop":
            loop_group = LoopGroup()
            loop_body = configs.get("loopBody") or []

            # Resolve string IDs to full node objects
            if loop_body and isinstance(loop_body[0], str):
                loop_body = [
                    node_by_id[bid] for bid in loop_body if bid in (node_by_id or {})
                ]
            loop_body_by_id = {n.get("id"): n for n in loop_body if n.get("id")}

            # Defer branch/intentDetection registration until loop body branch routes
            # are wired, so add_workflow_comp → register_branch_targets sees full routers.
            pending_loop_branch_nodes: list[dict] = []

            # Add loop body components
            loop_component_by_id = {}
            for body_node in loop_body:
                body_comp = await IRConverter._add_component(
                    loop_group,
                    body_node,
                    global_model,
                    pending_branch_nodes=pending_loop_branch_nodes,
                    node_by_id=node_by_id,
                    ir_connections=ir_connections,
                )
                if body_comp is not None:
                    loop_component_by_id[body_node.get("id")] = body_comp

            # Collect loop body branch connections from configs and top-level IR.
            loop_body_connections = configs.get("connections") or []
            loop_body_ids = set(loop_body_by_id.keys())
            loop_branch_connections: list[tuple[str, str, str]] = []
            loop_regular_connections: list[tuple[str, str]] = []
            for conn in loop_body_connections:
                src = ((conn.get("source") or {}).get("componentId") or "").strip()
                tgt = ((conn.get("target") or {}).get("componentId") or "").strip()
                bid = ((conn.get("source") or {}).get("branchId") or "").strip()
                if not src or not tgt:
                    continue
                if bid:
                    loop_branch_connections.append((src, tgt, bid))
                    continue
                loop_regular_connections.append((src, tgt))

            # The IR stores loop body inter-component connections at the root level, NOT inside
            # the loop node's configs. Without this, body components are disconnected in LoopGroup.
            for conn in ir_connections or []:
                src = ((conn.get("source") or {}).get("componentId") or "").strip()
                tgt = ((conn.get("target") or {}).get("componentId") or "").strip()
                bid = ((conn.get("source") or {}).get("branchId") or "").strip()
                if not src or not tgt:
                    continue
                # Skip virtual _input/_output connections (handled below for start/end nodes)
                if src == f"{node_id}_input" or tgt == f"{node_id}_output":
                    continue
                # Only process connections where both endpoints are loop body components
                if src not in loop_body_ids or tgt not in loop_body_ids:
                    continue
                if bid:
                    loop_branch_connections.append((src, tgt, bid))
                    continue
                loop_regular_connections.append((src, tgt))

            IRConverter._add_branch_connections_with_default_last(
                loop_component_by_id,
                loop_body_by_id,
                loop_branch_connections,
            )
            IRConverter._register_pending_branch_nodes(
                loop_group, pending_loop_branch_nodes
            )

            for src, tgt in loop_regular_connections:
                loop_group.add_connection(src, tgt)

            # Auto-determine start/end nodes
            start_nodes = [
                n.get("id") for n in loop_body if n.get("type") == "jiuwen.start"
            ]
            end_nodes = [
                n.get("id") for n in loop_body if n.get("type") == "jiuwen.end"
            ]

            # Determine from _input/_output virtual connections in top-level IR
            for conn in ir_connections or []:
                src = ((conn.get("source") or {}).get("componentId") or "").strip()
                tgt = ((conn.get("target") or {}).get("componentId") or "").strip()
                if src == f"{node_id}_input" and tgt in loop_body_by_id:
                    if tgt not in start_nodes:
                        start_nodes.append(tgt)
                if tgt == f"{node_id}_output" and src in loop_body_by_id:
                    if src not in end_nodes:
                        end_nodes.append(src)

            # Fallback: first body node is start, last is end
            if not start_nodes and loop_body:
                start_nodes = [loop_body[0].get("id")]
            if not end_nodes and loop_body:
                end_nodes = [loop_body[-1].get("id")]
            # Handle break condition: use BranchComponent + LoopBreakComponent (official pattern).
            #
            # Reference: test_workflow_with_loop_component_always_true test case.
            # Like test_workflow_with_loop_component_break, the branch and break components
            # are placed AFTER the original end_nodes (not replacing them). The end_nodes
            # remain unchanged — the break flag is set in the same PregelGraph superstep
            # and checked at the next iteration's condition node.
            #
            # Structure: original_end_node (end) → branch → break_comp
            #                                          └→ pass_through
            #
            # - branch evaluates break_expr via ExpressionCondition (BranchRouter built-in)
            # - True → LoopBreakComponent (sets broken flag, checked next iteration)
            # - False (catch-all via lambda: True) → pass_through (no-op)
            # - Body components run under SubWorkflowSession (parent_id=''), so external
            #   references like ${node_start.systemFields.query} can be resolved.
            break_expr = configs.get("breakCondition", "").strip()
            if break_expr:
                break_expr = _convert_start_memory_refs_in_string(break_expr)
                branch_id = f"_break_branch_{node_id}"
                break_comp_id = f"_break_{node_id}"
                pass_through_id = f"_loop_end_{node_id}"

                # Use standard BranchComponent with two branches:
                # 1. break_expr → LoopBreakComponent (break)
                # 2. lambda: True → pass_through (continue, always matches as fallback)
                branch_comp = BranchComponent()
                branch_comp.add_branch(break_expr, [break_comp_id])
                branch_comp.add_branch(lambda: True, [pass_through_id])

                loop_group.add_workflow_comp(branch_id, branch_comp)
                loop_group.add_workflow_comp(break_comp_id, LoopBreakComponent())
                loop_group.add_workflow_comp(
                    pass_through_id, _LoopPassThroughComponent()
                )

                # Connect original end nodes → branch (end_nodes remain unchanged)
                for end_id in end_nodes or []:
                    loop_group.add_connection(end_id, branch_id)

            if start_nodes:
                loop_group.start_nodes(start_nodes)
            if end_nodes:
                loop_group.end_nodes(end_nodes)

            # Build output_schema as dict for OutputCallback to properly aggregate results
            # OutputCallback.end_round calls get_inputs which resolves ref paths via IO state
            raw_output = node.get("outputs") or {}
            output_schema = _convert_schema(raw_output)

            try:
                loop_comp = LoopComponent(
                    loop_group,
                    output_schema=output_schema or None,
                )
            except OpenjiuwenValidationError as exc:
                raise ValueError(
                    f"unsupported workflow component type for openjiuwen workflow: {node_type}"
                ) from exc
            return loop_comp, node_type, configs

        if node_type == "jiuwen.setVariable":
            variable_mapping = {}
            operator_mapping = {}

            # 兼容新格式：settings
            settings = configs.get("settings") or []  # noqa: redefined-outer-name
            if settings:
                for item in settings:
                    left_val = item.get("left", {}).get("value", "")
                    right_val = item.get("right", {}).get("value", "")
                    operator = item.get("right", {}).get("operator", "")
                    if left_val:
                        variable_mapping[left_val] = right_val
                        if operator:
                            operator_mapping[left_val] = operator
            else:
                # 旧格式：variableMapping / variable_mapping
                for k, v in (
                    configs.get("variableMapping")
                    or configs.get("variable_mapping")
                    or {}
                ).items():
                    variable_mapping[_convert_reference_value(k)] = (
                        _convert_reference_value(v)
                    )
            return (
                LoopSetVariable(variable_mapping, operator_mapping),
                node_type,
                configs,
            )

        if node_type == "jiuwen.exception":
            return (
                ExceptionInfo(
                    node_id=node_id,
                    node_name=configs.get("name") or node_id,
                    node_type=node_type,
                ),
                node_type,
                configs,
            )

        if node_type == "jiuwen.streamTransform":
            metadata = WorkflowMetadata(
                node_id=node_id,
                node_type=node_type,
                node_name=configs.get("name") or node_id,
            )
            return FlowStreamTransform(configs, metadata), node_type, configs

        raise ValueError(
            f"unsupported workflow component type for openjiuwen workflow: {node_type}"
        )

    @staticmethod
    async def _add_component(
        workflow: Workflow,
        node: dict,
        global_model: dict | None,
        stream_inputs_schema: dict | None = None,
        *,
        pending_end_nodes: list[dict] | None = None,
        pending_branch_nodes: list[dict] | None = None,
        node_by_id: dict[str, dict] | None = None,
        ir_connections: list[dict] | None = None,
        stream_source_ids: set[str] | None = None,
        parallel_join_nodes: frozenset[str] | None = None,
    ) -> Any:
        """将组件注册到 Workflow。内部调用 _create_component 创建组件实例。"""

        node_id = node.get("id")
        node_type = node.get("type")

        inputs_schema = _convert_schema(node.get("inputs") or {})
        outputs_schema = _convert_schema(node.get("outputs") or {})

        exception_config = _parse_exception_config(node)
        if exception_config and node_type not in _NO_EXCEPTION_TYPES:
            _timeout = exception_config.timeout
            _max_retries = exception_config.retry_times
            if _max_retries > 0 and node_type in _NO_RETRY_TYPES:
                logger.warning(f"{node_type}_{node_id} not support retry")
                _max_retries = 0
        else:
            _timeout = -1.0
            _max_retries = 0
            exception_config = None
        _comp_reg: dict[str, Any] = {
            "timeout": _timeout,
            "max_retries": _max_retries,
            "exception_config": exception_config,
        }
        if parallel_join_nodes and node_id in parallel_join_nodes:
            _comp_reg["wait_for_all"] = True
        # Add output field references with #end_ prefix only for End component,
        # which uses them to know which fields to include in the response.
        if node_type == "jiuwen.end":
            output_user_fields = outputs_schema.get("userFields", {})
            if isinstance(output_user_fields, dict):
                if "userFields" not in inputs_schema:
                    inputs_schema["userFields"] = {}
                if isinstance(inputs_schema["userFields"], list):
                    for user_field, value in output_user_fields.items():
                        inputs_schema["userFields"].append("#end_" + user_field)
                elif isinstance(inputs_schema["userFields"], dict):
                    for user_field, value in output_user_fields.items():
                        inputs_schema["userFields"]["#end_" + user_field] = value

        # subWorkflow 加载子工作流
        if node_type in {"jiuwen.subWorkflow", "jiuwen.workflowComposite"}:
            configs = dict(node.get("configs") or {})
            # Extract global var mappings from input_schema
            # Format: {"userFields": {"child_key": "${global.parent_var}"}}
            # Maps child key to parent global variable name
            inputs_schema = _convert_schema(node.get("inputs") or {})
            global_var_mappings = _extract_global_var_mappings_from_schema(inputs_schema)
            child_workflow = await IRConverter._try_load_sub_workflow(
                configs, parent_global_var_mappings=global_var_mappings
            )
            component = SubWorkflow(
                {**configs, "node_id": node_id},
                sub_workflow=child_workflow,
            )
            _add_workflow_comp_with_exception(
                workflow,
                node_id,
                component,
                inputs_schema=inputs_schema,
                **_comp_reg,
            )
            _attach_node_def(component, node, configs)
            return component

        # ComplexIntentDetection 组件
        if node_type in {"EI.ComplexIntentDetection", "EI.complexIntentDetection"}:
            configs = dict(node.get("configs") or {})
            component = ComplexIntentDetection(
                configs,
                node_id=node_id,
                node_name=configs.get("name", ""),
            )
            _add_workflow_comp_with_exception(
                workflow,
                node_id,
                component,
                inputs_schema=inputs_schema,
                **_comp_reg,
            )
            _attach_node_def(component, node, configs)
            return component

        component, resolved_type, configs = await IRConverter._create_component(
            node,
            global_model,
            node_by_id=node_by_id,
            ir_connections=ir_connections,
        )
        _attach_node_def(component, node, configs)

        if resolved_type == "jiuwen.start":
            workflow.set_start_comp(
                node_id, component, inputs_schema=_build_start_inputs_schema(node)
            )
            return component

        if resolved_type in {"jiuwen.branch", "jiuwen.intentDetection"}:
            if pending_branch_nodes is not None:
                pending_branch_nodes.append(
                    {
                        "node_id": node_id,
                        "component": component,
                        "inputs_schema": inputs_schema,
                        "timeout": _timeout,
                        "max_retries": _max_retries,
                        "exception_config": exception_config,
                    }
                )
                return component

        if resolved_type == "jiuwen.end":
            ref = inputs_schema.get("userFields", {})
            for _v in ref.values():
                if (
                    isinstance(_v, str)
                    and _v.startswith("${")
                    and ".__stream_metadata__" not in _v
                ):
                    _upstream_id = _v.split(".")[0][2:]
                    if _upstream_id:
                        _upstream_type = (
                            (node_by_id or {}).get(_upstream_id, {}).get("type", "")
                        )
                        if _upstream_type in {
                            "jiuwen.plugin",
                            "jiuwen.api",
                            "jiuwen.flowApi",
                        }:
                            inputs_schema["userFields"]["__stream_metadata__"] = (
                                "${" + _upstream_id + ".__stream_metadata__}"
                            )
                            break
            if pending_end_nodes is not None:
                pending_end_nodes.append(
                    {
                        "node_id": node_id,
                        "end": component,
                        "inputs_schema": inputs_schema,
                        "is_stream_out": bool(configs.get("isStreamOut")),
                    }
                )
            elif bool(configs.get("isStreamOut")):
                workflow.set_end_comp(
                    node_id,
                    component,
                    stream_inputs_schema=inputs_schema,
                    response_mode="streaming",
                )
            else:
                workflow.set_end_comp(node_id, component, inputs_schema=inputs_schema)
            return component

        if resolved_type == "jiuwen.message":
            if stream_inputs_schema is not None:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    stream_inputs_schema=stream_inputs_schema,
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            return component

        if resolved_type in {"jiuwen.card", "jiuwen.flowCard"}:
            if stream_inputs_schema is not None:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    stream_inputs_schema=stream_inputs_schema,
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            return component

        if resolved_type in {
            "jiuwen.aggregate",
            "jiuwen.flowAggregate",
            "jiuwen.aggregation",
        }:
            agg_inputs_schema = _aggregate_inputs_schema(inputs_schema)
            if stream_inputs_schema is not None:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    stream_inputs_schema=_aggregate_inputs_schema(stream_inputs_schema),
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=agg_inputs_schema,
                    **_comp_reg,
                )
            return component

        if resolved_type == "jiuwen.streamTransform":
            if stream_inputs_schema is not None:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    stream_inputs_schema=stream_inputs_schema,
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            return component

        if resolved_type == "jiuwen.loop":
            loop_type_ir = configs.get("loopType", "")
            loop_type = _LOOP_TYPE_MAP.get(loop_type_ir, loop_type_ir)
            loop_inputs = {"loop_type": loop_type}
            node_inputs = node.get("inputs") or {}
            if "numLoopVar" in node_inputs:
                loop_inputs["loop_number"] = node_inputs["numLoopVar"]
            if "arrLoopVar" in node_inputs:
                loop_inputs["loop_array"] = {"arrLoopVar.item": node_inputs["arrLoopVar"]}
            if "intermediateLoopVar" in node_inputs:
                loop_inputs["intermediate_var"] = {"intermediateLoopVar": node_inputs["intermediateLoopVar"]}
            # 直接以 dict 作为 inputs_schema，交由 core 的标准 get_inputs 解析。
            # 标准路径走 io_state.get_by_prefix(schema, parent_id)，会按 parent_id
            # 深入到当前（子）工作流作用域后再解析 ${...} 引用。原先用自定义
            # callable transformer + get_by_schema(..., is_root=True) 从绝对根解析，
            # 在子工作流上下文中会绕过 parent_id 作用域，导致循环无法解析到同级
            # 子节点输出（如代码节点产出的数组），arrLoopVar 落地为字面量字符串而报错。
            _add_workflow_comp_with_exception(
                workflow,
                node_id,
                component,
                inputs_schema=loop_inputs,
                **_comp_reg,
            )
            return component

        if resolved_type in {
            "jiuwen.llm",
            "jiuwen.llm_chain",
            "jiuwen.llmChain",
            "jiuwen.LLMComponent",
        }:
            if configs.get("responseFormat", {}).get("type", "text") == "json":
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            elif bool(configs.get("stream", False)):
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    comp_ability=[ComponentAbility.STREAM],
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            return component

        if resolved_type in IRConverter._STREAMING_API_TYPES:
            if bool(configs.get("streaming", False)):
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    comp_ability=[ComponentAbility.STREAM],
                    **_comp_reg,
                )
            else:
                _add_workflow_comp_with_exception(
                    workflow,
                    node_id,
                    component,
                    inputs_schema=inputs_schema,
                    **_comp_reg,
                )
            return component

        _add_workflow_comp_with_exception(
            workflow,
            node_id,
            component,
            inputs_schema=inputs_schema,
            **_comp_reg,
        )
        return component

    @staticmethod
    def _is_default_branch_id(branch_id: str) -> bool:
        return branch_id.endswith("default")

    @staticmethod
    def _is_error_branch_id(branch_id: str, source: str = "") -> bool:
        if "@@" in branch_id:
            suffix = branch_id.split("@@", 1)[1]
            idx = suffix.split("_")[1] if "_" in suffix else "0"
            return idx == "1"

        normalized_suffix = branch_id
        prefix = f"{source}-"
        if source and branch_id.startswith(prefix):
            normalized_suffix = branch_id[len(prefix) :]
        return (
            normalized_suffix == "errorBranch"
            or branch_id.endswith("-errorBranch")
            or branch_id.endswith("errorBranch")
        )

    @staticmethod
    def _branch_connection_sort_key(
        source: str, branch_id: str, node_by_id: dict[str, dict]
    ) -> int:
        """Order if/elseIf branches using IR configs."""
        source_node = node_by_id.get(source) or {}
        branches = (source_node.get("configs") or {}).get("branches") or []
        normalized_suffix = branch_id
        prefix = f"{source}-"
        if branch_id.startswith(prefix):
            normalized_suffix = branch_id[len(prefix) :]

        for idx, branch in enumerate(branches):
            if not isinstance(branch, dict):
                continue
            current_id = str(branch.get("id") or "")
            if current_id in (branch_id, normalized_suffix):
                return idx

        if branch_id.endswith("-if") or normalized_suffix == "if":
            return 0
        match = re.search(r"-elseIf-(\d+)$", branch_id)
        if match:
            return int(match.group(1))
        return len(branches)

    @staticmethod
    def _branch_registration_sort_key(
        source: str, branch_id: str, node_by_id: dict[str, dict]
    ) -> tuple[int, int]:
        """Order branches as if, elseIf-1..N, errorBranch, default."""
        if IRConverter._is_default_branch_id(branch_id):
            return (2, 0)
        if IRConverter._is_error_branch_id(branch_id, source):
            return (1, 0)
        return (
            0,
            IRConverter._branch_connection_sort_key(source, branch_id, node_by_id),
        )

    @staticmethod
    def _add_branch_connections_with_default_last(
        component_by_id: dict[str, Any],
        node_by_id: dict[str, dict],
        branch_connections: list[tuple[str, str, str]],
    ) -> None:
        """Wire branch routes in if/elseIf/errorBranch/default order."""
        grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
        for source, target, branch_id in branch_connections:
            key = (source, branch_id)
            if target not in grouped[key]:
                grouped[key].append(target)

        ordered_items = [
            (source, branch_id, targets)
            for (source, branch_id), targets in grouped.items()
        ]
        ordered_items.sort(
            key=lambda item: (
                item[0],
                IRConverter._branch_registration_sort_key(
                    item[0], item[1], node_by_id
                ),
            )
        )
        for source, branch_id, targets in ordered_items:
            IRConverter._add_branch_connection(
                component_by_id, node_by_id, source, targets, branch_id
            )

    @staticmethod
    def _add_branch_connection(
        component_by_id: dict[str, Any],
        node_by_id: dict[str, dict],
        source: str,
        target: str | list[str],
        branch_id: str,
    ) -> None:
        component = component_by_id.get(source)
        if component is None:
            return
        source_node = node_by_id.get(source) or {}
        source_type = source_node.get("type")
        condition = _resolve_branch_condition(source_node, source_type, branch_id)
        if hasattr(component, "add_branch"):
            component.add_branch(condition, target, branch_id=branch_id)

    @staticmethod
    def _register_pending_branch_nodes(
        workflow: Workflow | LoopGroup, pending_branch_nodes: list[dict]
    ) -> None:
        """Register branch routers after IR branch connections are wired."""
        for pending in pending_branch_nodes:
            _add_workflow_comp_with_exception(
                workflow,
                pending["node_id"],
                pending["component"],
                inputs_schema=pending["inputs_schema"],
                timeout=pending["timeout"],
                max_retries=pending["max_retries"],
                exception_config=pending["exception_config"],
            )

    _AGGREGATE_TYPES = frozenset(
        {
            "jiuwen.aggregate",
            "jiuwen.flowAggregate",
            "jiuwen.aggregation",
        }
    )

    _STREAMING_API_TYPES = frozenset(
        {
            "jiuwen.plugin",
            "jiuwen.api",
            "jiuwen.flowApi",
            "jiuwen.agent",
            "jiuwen.flowAgent",
        }
    )

    _STREAM_INPUT_CAPABLE_TARGET_TYPES = frozenset(
        {
            "jiuwen.end",
            "jiuwen.flowAgent",
            "jiuwen.message",
            "jiuwen.card",
            "jiuwen.streamTransform",
            "jiuwen.aggregate",
            "jiuwen.flowAggregate",
            "jiuwen.aggregation",
        }
    )

    @staticmethod
    def _all_refs_from_stream_sources(
        schema: dict, stream_source_ids: set[str]
    ) -> bool:
        """Check if every $ref in *schema* points to a node in *stream_source_ids*.

        An empty schema or one with no ``$ref`` patterns returns ``True``
        (no non-stream source to reject).
        """
        if not isinstance(schema, dict):
            return True
        for value in schema.values():
            if isinstance(value, dict):
                if not IRConverter._all_refs_from_stream_sources(
                    value, stream_source_ids
                ):
                    return False
            elif isinstance(value, str) and "${" in value:
                ref = value.strip()
                if ref.startswith("${") and "}" in ref:
                    inner = ref[2 : ref.index("}")]
                    parts = inner.split(".", 1)
                    if parts and parts[0] not in stream_source_ids:
                        return False
        return True

    @staticmethod
    def _is_stream_connection(
        components: list[dict],
        source: str,
        target: str,
        stream_source_ids: set[str],
    ) -> bool:
        source_node = next(
            (item for item in components if item.get("id") == source), {}
        )
        target_node = next(
            (item for item in components if item.get("id") == target), {}
        )
        source_type = source_node.get("type")
        source_id = source_node.get("id")
        target_type = target_node.get("type")
        target_configs = target_node.get("configs") or {}
        if target_type in IRConverter._AGGREGATE_TYPES:
            # Legacy BPMN aggregate resolves ${node.field} refs from IO state after
            # upstream batch outputs are committed (including stream LLM via
            # get_stream_output).  Stream edges trigger COLLECT and skip that path.
            return False
        if target_type not in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES:
            return False
        if (
            target_type == "jiuwen.end"
            and target_configs.get("isStreamOut")
            and source_id in stream_source_ids
        ):
            return True
        if (
            source_id in stream_source_ids
            and target_type in IRConverter._STREAM_INPUT_CAPABLE_TARGET_TYPES
        ):
            return True
        return False

    @staticmethod
    def _add_normal_edge_spec_only(
        workflow: Workflow, source: str, target: str
    ) -> None:
        internal = getattr(workflow, "_internal", None)
        spec = getattr(internal, "_workflow_spec", None)
        if spec is None:
            return
        if source not in spec.edges:
            spec.edges[source] = [target]
        elif target not in spec.edges[source]:
            spec.edges[source].append(target)

    @staticmethod
    def create_single_component_ir(ir_data: dict, component_id: str) -> dict:
        """
        创建单个组件的中间表示(IR)数据。

        该方法用于生成单个组件的IR数据，适用于组件调试场景。
        它会验证IR数据的类型，并确保组件ID存在于IR数据中。
        如果组件类型不在支持的列表中，则会抛出异常。

        Args:
            ir_data (dict): 完整的工作流IR数据，从JSON IR文件解析得到的字典。
            component_id (str): 需要调试的组件ID。

        Returns:
            dict: 包含单个组件IR数据的字典。

        Raises:
            JiuWenBaseException: 如果IR类型不是工作流、找不到对应组件或组件类型不支持时抛出异常。
        """
        ir_type = IRConverter.identify_ir(ir_data)
        if ir_type != IRType.Workflow:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_IR_ILLEGAL.code,
                message=StatusCode.COMPONENT_IR_ILLEGAL.errmsg.format(
                    reason="single component ir_type must be workflow"
                ),
            )
        # 获取待调测组件对应信息
        node_component = [
            node for node in ir_data["components"] if node.get("id") == component_id
        ]
        if not node_component:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_IR_ILLEGAL.code,
                message=StatusCode.COMPONENT_IR_ILLEGAL.errmsg.format(
                    reason="cannot find the corresponding component,please check node_id is correct"
                ),
            )
        if node_component[0].get("type") in UNSUPPORTED_COMPONENT_DEBUG_LIST:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_TYPE_ERROR.code,
                message=StatusCode.COMPONENT_TYPE_ERROR.errmsg,
            )
        # 单组件调测场景下 ir_data仅保留所需调测组件信息，删去其它无关组件及组件间连接关系
        ir_data["components"] = node_component
        ir_data["connections"] = []
        return ir_data

    @staticmethod
    async def create_single_component(
        ir_data: dict, component_id: str
    ) -> SingleComponentInfo:
        """从 IR 中创建单个组件实例，用于单组件调测。

        复用 create_single_component_ir 的验证逻辑 + _create_component 的创建逻辑。

        Args:
            ir_data: 完整的工作流 IR 数据。
            component_id: 需要调测的组件 ID。

        Returns:
            SingleComponentInfo: 组件信息，包含 component 实例、node_id、node_type、configs、inputs_schema。

        Raises:
            JiuWenBaseException: IR 类型不是工作流、找不到组件、组件类型不支持时抛出。
        """
        ir_type = IRConverter.identify_ir(ir_data)
        if ir_type != IRType.Workflow:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_IR_ILLEGAL.code,
                message=StatusCode.COMPONENT_IR_ILLEGAL.errmsg.format(
                    reason="single component ir_type must be workflow"
                ),
            )
        node_component = [
            node
            for node in ir_data.get("components", [])
            if node.get("id") == component_id
        ]
        if not node_component:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_IR_ILLEGAL.code,
                message=StatusCode.COMPONENT_IR_ILLEGAL.errmsg.format(
                    reason="cannot find the corresponding component, please check node_id is correct"
                ),
            )
        node = node_component[0]
        node_type = node.get("type")
        if node_type in UNSUPPORTED_COMPONENT_DEBUG_LIST:
            raise JiuWenBaseException(
                error_code=StatusCode.COMPONENT_TYPE_ERROR.code,
                message=StatusCode.COMPONENT_TYPE_ERROR.errmsg,
            )
        global_model = (ir_data.get("configs") or {}).get("model")
        component, _, configs = await IRConverter._create_component(node, global_model)

        # SubWorkflow 需要加载子工作流
        if node_type in {"jiuwen.subWorkflow", "jiuwen.workflowComposite"}:
            child_workflow = await IRConverter._try_load_sub_workflow(configs)
            component = SubWorkflow(
                {**configs, "node_id": component_id}, sub_workflow=child_workflow
            )

        inputs_schema = _convert_schema(node.get("inputs") or {})
        return SingleComponentInfo(
            component=component,
            node_id=component_id,
            node_type=node_type,
            configs=configs,
            inputs_schema=inputs_schema,
            node_name=node.get("name", ""),
        )

    @staticmethod
    async def create_all_memory_config_list(root_ir_data):
        """
        Create All Memory configs: List[MemoryIrConfig]
        """
        all_configs: List[MemoryIrConfig] = []
        visited = set()

        async def _recursive_create(current_ir_data: dict[str, Any]):
            """for each agent|workflow, add its MemoryIrConfig into list"""
            if not current_ir_data or not isinstance(current_ir_data, dict):
                return
            node_id = current_ir_data.get("agentId", "") or current_ir_data.get(
                "workflowId", ""
            )
            if not node_id or node_id in visited:
                return
            visited.add(node_id)

            current_memory_ir_data = current_ir_data.get("configs", {}).get(
                "memory", {}
            )
            if current_memory_ir_data:
                all_configs.append(
                    MemoryIrConfig.from_config_dict(current_memory_ir_data)
                )

            current_ir_type = IRConverter.identify_ir(current_ir_data)
            if current_ir_type == IRType.Agent:
                for child_workflow_info in current_ir_data.get("configs", {}).get(
                    "workflows", []
                ):
                    child_workflow_ir_path = child_workflow_info.get("ir_path", "")
                    if child_workflow_ir_path:
                        child_workflow_ir_data = await async_ir_load(
                            child_workflow_ir_path
                        )
                        await _recursive_create(child_workflow_ir_data)
            elif current_ir_type == IRType.Workflow:
                for child_workflow_info in current_ir_data.get("components", {}):
                    if child_workflow_info.get("type") != NodeType.SUB_WORKFLOW.value:
                        continue
                    child_workflow_ir_path = (
                        child_workflow_info.get("configs", {})
                        .get("reference", {})
                        .get("path", "")
                    )
                    if child_workflow_ir_path:
                        child_workflow_ir_data = await async_ir_load(
                            child_workflow_ir_path
                        )
                        await _recursive_create(child_workflow_ir_data)
            elif current_ir_type == IRType.MultiAgents:
                for child_agent_info in current_ir_data.get("configs", {}).get(
                    "agents", []
                ):
                    child_agent_ir_path = child_agent_info.get("ir_path", "")
                    if child_agent_ir_path:
                        child_agent_ir_data = await async_ir_load(child_agent_ir_path)
                        await _recursive_create(child_agent_ir_data)
                for child_workflow_info in current_ir_data.get("configs", {}).get(
                    "workflows", []
                ):
                    child_workflow_ir_path = child_workflow_info.get("ir_path", "")
                    if child_workflow_ir_path:
                        child_workflow_ir_data = await async_ir_load(
                            child_workflow_ir_path
                        )
                        await _recursive_create(child_workflow_ir_data)

        await _recursive_create(root_ir_data)
        return all_configs

    @staticmethod
    async def get_memory_topics(root_ir_data) -> List[Dict[str, Any]]:
        """
        Recursively get and merge memory topics from the root IR data
        """
        if not root_ir_data or not isinstance(root_ir_data, dict):
            return []
        all_memory_configs = await IRConverter.create_all_memory_config_list(
            root_ir_data
        )

        # merge memory topics
        topic_lists: List[List[Dict[str, Any]]] = []
        for memory_config in all_memory_configs:
            if (
                memory_config.enable_memory
                and memory_config.enable_user_profile
                and memory_config.user_profile_topics
            ):
                topic_lists.append(memory_config.user_profile_topics)

        merged = defaultdict(dict)
        for topic_list in topic_lists:
            for item in topic_list:
                if not isinstance(item, dict):
                    continue
                topic_name = item.get("name")
                tags = item.get("tags")

                if topic_name is None or not isinstance(tags, list):
                    continue

                merged_tags = merged[topic_name]
                for tag in tags:
                    if not isinstance(tag, dict):
                        continue
                    tag_name = tag.get("name")
                    if tag_name is None:
                        continue
                    merged_tags.setdefault(tag_name, tag)

        return [
            {"name": topic_name, "tags": list(tag_map.values())}
            for topic_name, tag_map in merged.items()
        ]

    @staticmethod
    def _validate_agent_ir(ir_data: dict):
        """验证 Agent IR 数据"""
        try:
            AgentIrValidator(**ir_data)
        except ValidationError as e:
            error_message = format_pydantic_validation_error_message(e)
            raise JiuWenBaseException(
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.code,
                StatusCode.LLM_AGENT_IR_VALIDATE_ERROR.errmsg.format(
                    error_msg=f"Agent_ir validate failed, root_case={error_message}"
                ),
            ) from e

    @staticmethod
    async def _create_llm_model(
        model_configs: dict,
        cust_headers: dict,
        project_id: str,
        identifiers: "_LLMModelIdentifiers",
    ):
        """创建 LLM 模型"""
        if IRConverter._use_agent_core_model(model_configs):
            return await IRConverter._create_agent_core_llm_model(
                model_configs,
                identifiers.task_id,
                identifiers.agent_id,
                conversation_id=identifiers.conversation_id,
            )

        runtime_context = {
            "runtime_context": {
                "workflow_execute_requests_headers_name": {
                    "cust_headers": cust_headers
                },
                "workflow_execute_project_id": {"project_id": project_id},
            }
        }
        return ModelFactory().get_model(
            model_type=model_configs.get("modelType"),
            model_name=model_configs.get("modelName"),
            **(model_configs.get("hyperParameters", {})),
            **(model_configs.get("extension", {})),
            **runtime_context,
        )

    @staticmethod
    def _use_agent_core_model(model_configs: dict) -> bool:
        """Return whether the IR model dependency should be backed by openjiuwen."""
        extension = model_configs.get("extension", {}) or {}
        enabled = extension.get(
            "useAgentCoreModel", extension.get("use_agent_core_model")
        )
        if enabled is not None:
            return str(enabled).lower() == "true"
        if str(os.environ.get(_USE_AGENT_CORE_MODEL_ENV, "true")).lower() != "true":
            return False
        provider = IRConverter._normalize_agent_core_client_provider(
            IRConverter._first_non_empty(
                extension.get("agentCoreClientProvider"),
                extension.get("agent_core_client_provider"),
                extension.get("client_provider"),
                model_configs.get("modelType"),
            )
        )
        return provider in {
            "OpenAI",
            "DashScope",
            "OpenRouter",
            "SiliconFlow",
            "ContractMock",
            "LLM",
        }

    @staticmethod
    async def _create_agent_core_llm_model(
        model_configs: dict, task_id: str, agent_id: str, conversation_id: str = ""
    ):
        """Create jiuwen model contract layer backed by openjiuwen's ModelWrapper."""
        # Keep openjiuwen-related imports lazy so the legacy ModelFactory path remains unchanged.
        from jiuwen.extension.wrapper.model_wrapper import ModelWrapper
        from jiuwen.integration.agent_core_model_new import AgentCoreModelLayer

        extension = model_configs.get("extension", {}) or {}
        model_id = (
            extension.get("agentCoreModelId")
            or extension.get("agent_core_model_id")
            or extension.get("model_id")
            or model_configs.get("modelId")
            or model_configs.get("modelName")
            or ""
        )
        session_id = (
            extension.get("agentCoreSessionId")
            or extension.get("agent_core_session_id")
            or extension.get("session_id")
            or conversation_id
            or task_id
            or ""
        )
        resolved_agent_id = (
            extension.get("agentCoreAgentId")
            or extension.get("agent_core_agent_id")
            or extension.get("agent_id")
            or agent_id
            or ""
        )
        await IRConverter._register_agent_core_llm_model(model_id, model_configs)
        return AgentCoreModelLayer(
            runtime=ModelWrapper(),
            default_model_id=model_id,
            default_session_id=session_id,
            default_agent_id=resolved_agent_id,
        )

    @staticmethod
    async def _register_agent_core_llm_model(model_id: str, model_configs: dict) -> None:
        """Register an openjiuwen model resource from jiuwen IR model config.

        Uses the configured ModelConfigProvider (via _get_model_config_provider())
        for consistent model configuration across all components.
        """

        if not model_id:
            return
        if model_id in _AGENT_CORE_REGISTERED_MODEL_IDS:
            logger.info(
                f"Agent-core model resource already registered: model_id={model_id}",
                simple_log="agent-core model resource already registered",
            )
            return

        from agent_runtime.common.model_adapters import adapt_ir_converter_model_config
        from openjiuwen.core.foundation.llm import Model
        from openjiuwen.core.runner import Runner

        adapted_conf = adapt_ir_converter_model_config(model_configs, model_id)

        provider = _get_model_config_provider()
        llm_comp_config = await provider.get_llm_config(adapted_conf)

        # Extract model name for logging
        model_name = model_configs.get("modelName") or model_id

        try:
            model_instance = Model(
                model_client_config=llm_comp_config.model_client_config,
                model_config=llm_comp_config.model_config,
            )
        except Exception as e:
            logger.error(
                f"Failed to create agent-core model resource: model_id={model_id}, "
                f"model_name={model_name}, error={e}",
                simple_log=(
                    f"failed to create agent-core model resource: "
                    f"model_id={model_id}, model_name={model_name}, error={e}"
                ),
            )
            raise

        def model_factory():
            return model_instance

        add_result = Runner.resource_mgr.add_model(
            model_id=model_id, model=model_factory
        )

        # Check registration result
        is_ok = getattr(add_result, "is_ok", None)
        succeeded = bool(is_ok()) if callable(is_ok) else True

        if not succeeded:
            if "resource already exist" in str(add_result):
                _AGENT_CORE_REGISTERED_MODEL_IDS.add(model_id)
                logger.info(
                    f"Agent-core model resource already exists in runner: model_id={model_id}",
                    simple_log="agent-core model resource already exists",
                )
                return
            raise RuntimeError(
                f"Failed to register agent-core model resource: {add_result}"
            )

        _AGENT_CORE_REGISTERED_MODEL_IDS.add(model_id)
        logger.info(
            f"Registered agent-core model resource: model_id={model_id}, model={model_name}",
            simple_log="registered agent-core model resource",
        )

    @staticmethod
    def _resolve_legacy_model_config(model_configs: dict) -> dict:
        """Resolve jiuwen model config so the openjiuwen model can reuse existing settings."""
        model_factory = ModelFactory()
        model_type = model_configs.get("modelType")
        model_name = model_configs.get("modelName")
        extension = model_configs.get("extension", {}) or {}
        hyper_parameters = model_configs.get("hyperParameters", {}) or {}
        resolver_kwargs = {**hyper_parameters, **extension}
        resolved_config = None
        if model_factory.model_resolver:
            resolved_config = model_factory.model_resolver(
                model_type, model_name, **resolver_kwargs
            )
        if not resolved_config:
            resolved_config = model_factory.default_model_resolver(
                model_type, model_name, **resolver_kwargs
            )
        return dict(resolved_config or {})

    @staticmethod
    def _filter_model_config_kwargs(config_cls, values: dict) -> dict:
        """Keep only fields supported by the installed openjiuwen config class."""
        fields = getattr(config_cls, "model_fields", None) or getattr(
            config_cls, "__fields__", None
        )
        clean_values = {
            key: value for key, value in values.items() if value is not None
        }
        if not fields:
            return clean_values
        return {key: value for key, value in clean_values.items() if key in fields}

    @staticmethod
    def _normalize_agent_core_client_provider(provider: str) -> str:
        """Map jiuwen model types to openjiuwen client provider names."""
        provider_aliases = {
            "dashscope": "DashScope",
            "openai": "OpenAI",
            "openrouter": "OpenRouter",
            "qwen": "OpenAI",
            "deepseek": "OpenAI",
            "siliconflow": "SiliconFlow",
        }
        if not provider:
            return provider
        return provider_aliases.get(str(provider).lower(), provider)

    @staticmethod
    def _use_legacy_direct_model(client_provider: str, api_base: str) -> bool:
        """Return whether a legacy full chat-completions endpoint should be called directly."""
        if str(client_provider).lower() != "openai" or not api_base:
            return False
        normalized_path = str(api_base).split("?", 1)[0].replace("\\", "/").lower()
        return "/chat/completions/" in normalized_path

    @staticmethod
    def _resolve_agent_core_ssl_values(
        api_base: str, extension: dict, resolved_config: dict
    ) -> dict:
        """Translate legacy jiuwen SSL config to openjiuwen's strict SSL fields."""
        explicit_verify = IRConverter._first_non_empty(
            extension.get("verify_ssl"),
            extension.get("verifySSL"),
            extension.get("ssl_verify"),
            extension.get("sslVerify"),
            extension.get("ssl_mode"),
            extension.get("sslMode"),
            resolved_config.get("verify_ssl"),
            resolved_config.get("verifySSL"),
            resolved_config.get("ssl_verify"),
            resolved_config.get("sslVerify"),
            resolved_config.get("ssl_mode"),
            resolved_config.get("sslMode"),
        )
        ssl_cert = IRConverter._first_non_empty(
            extension.get("ssl_cert"),
            extension.get("sslCert"),
            extension.get("ssl_certificate"),
            extension.get("sslCertificate"),
            extension.get("cert_path"),
            extension.get("certPath"),
            resolved_config.get("ssl_cert"),
            resolved_config.get("sslCert"),
            resolved_config.get("ssl_certificate"),
            resolved_config.get("sslCertificate"),
            resolved_config.get("cert_path"),
            resolved_config.get("certPath"),
        )

        if explicit_verify is not None:
            verify_ssl = IRConverter._to_bool(explicit_verify)
        else:
            legacy_verify = ModelUtil.parse_ssl_verify()
            if isinstance(legacy_verify, str):
                verify_ssl = True
                ssl_cert = ssl_cert or legacy_verify
            else:
                verify_ssl = bool(legacy_verify)

        if (
            str(api_base or "").lower().startswith("http://")
            and explicit_verify is None
        ):
            verify_ssl = False
        if verify_ssl and not ssl_cert:
            verify_ssl = False
        return {"verify_ssl": verify_ssl, "ssl_cert": ssl_cert}

    @staticmethod
    def _to_bool(value) -> bool:
        """Convert legacy bool-like config values to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "on"}
        return bool(value)

    @staticmethod
    def _agent_core_resource_add_succeeded(add_result) -> bool:
        """Return whether openjiuwen resource registration returned Ok."""
        is_ok = getattr(add_result, "is_ok", None)
        return bool(is_ok()) if callable(is_ok) else True

    @staticmethod
    def _agent_core_resource_already_exists(add_result) -> bool:
        """Return whether openjiuwen resource registration failed because it already exists."""
        return "resource already exist" in str(add_result)

    @staticmethod
    def _first_non_empty(*values):
        """Return the first value that is not None and not an empty string."""
        for value in values:
            if value is not None and value != "":
                return value
        return None

    @staticmethod
    def _set_child_agents_metadata(agent_config, ir_data: dict):
        """设置子 Agent 元数据"""
        child_agents = ir_data.get("configs", {}).get("agents", [])
        if not child_agents:
            return
        child_metadata_list = []
        for child in child_agents:
            child_metadata = AgentMetaData(
                id=child.get("id"),
                name=child.get("name"),
                description=child.get("description", ""),
                ir_path=child.get("ir_path"),
                mode=child.get("mode", "Controller"),
            )
            child_metadata_list.append(child_metadata)
            logger.info(
                f"Added child agent metadata: id={child.get('id')}, mode={child.get('mode')}",
                simple_log="added child agent metadata",
            )
        agent_config.child_agents_metadata = child_metadata_list

    @staticmethod
    def _finalize_agent(
        agent,
        agent_config,
        task_model,
        ir_data: dict,
        cust_headers: dict,
        conversation_id: str = "",
    ):
        """完成 Agent 初始化"""
        if ir_data.get("configs").get("mode") == "ToolUse":
            AgentIrUtils.register_system_prompt(
                agent_config.task_id + "-toolUseAgent", "tool_use_agent"
            )
            AgentIrUtils.register_system_prompt(
                agent_config.task_id,
                "tool_use_planner",
                ir_data.get("configs").get("sysPromptTemplate"),
            )
            AgentIrUtils.update_plugins_from_ir(
                agent, ir_data, conversation_id=conversation_id
            )
            AgentIrUtils.update_mcps_from_ir(agent, ir_data, cust_headers=cust_headers)
            return agent
        return AgentIrUtils.update_prompt_plugin(
            agent_config.task_id,
            agent,
            task_model,
            ir_data,
            cust_headers=cust_headers,
            conversation_id=conversation_id,
        )

    @staticmethod
    def _wrap_agent_with_facade(agent):
        """Wrap the commercial agent with OpenJiuwenAgentFacade when enabled."""
        if os.getenv(_BASE_AGENT_SWITCH, "false").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            return agent

        from jiuwen.integration.openjiuwen_agent_facade import OpenJiuwenAgentFacade

        if isinstance(agent, OpenJiuwenAgentFacade):
            return agent
        return OpenJiuwenAgentFacade(agent)


def _normalize_end_config(configs: dict) -> dict | None:
    if not configs:
        return None
    if not configs.get("responseTemplate"):
        return None
    return configs


def _normalize_intent_detection_config(configs: dict) -> dict:
    normalized = dict(configs or {})
    llm_config = dict(normalized.get("llm") or {})
    model_config = dict(llm_config.get("model") or {})
    extension = dict(model_config.get("extension") or {})
    extension.setdefault("api_key", os.getenv("LLM_API_KEY", "mock-api-key"))
    extension.setdefault("api_base", os.getenv("LLM_API_BASE", "http://localhost/v1"))
    extension.setdefault(
        "verify_ssl", os.getenv("LLM_VERIFY_SSL", "false").lower() == "true"
    )
    model_config["extension"] = extension
    model_config["modelType"] = _normalize_model_provider(model_config.get("modelType"))
    llm_config["model"] = model_config
    normalized["llm"] = llm_config
    return normalized


def _normalize_model_provider(provider: Any) -> str:
    provider_text = str(provider or "").strip()
    if provider_text.startswith("llm_"):
        return provider_text
    return os.getenv("LLM_PROVIDER", "llm_OpenAI")


def _build_questioner_config(configs: dict) -> QuestionerConfig:
    model_config = configs.get("model") or {}
    return QuestionerConfig(
        model_name=model_config.get("modelName") or configs.get("modelName") or "",
        model_type=_normalize_model_provider(
            model_config.get("modelType") or configs.get("modelType")
        ),
        response_type=configs.get("responseType", "reply_directly"),
        extract_fields_from_response=bool(
            configs.get("extractFieldsFromResponse", True)
        ),
        with_chat_history=bool(configs.get("withChatHistory", False)),
        chat_history_max_rounds=int(
            configs.get("chatHistoryMaxRounds")
            or configs.get("chatHistoryMaxTurn")
            or 0
        ),
        extra_prompt_for_fields_extraction=configs.get("extraPromptForFieldsExtraction")
        or "",
        question_content=configs.get("questionContent") or "",
        question_construction_method=configs.get("questionConstructionMethod")
        or "rule_based",
        cn_fields_name=configs.get("cnFieldsName") or {},
        max_response=int(configs.get("maxResponse") or 3),
        option_content=configs.get("optionContent") or [],
        key_fields=_build_questioner_fields(configs),
        input_complement=bool(configs.get("inputComplement", False)),
        type_complement=configs.get("typeComplement") or "",
        hyper_parameters=model_config.get("hyperParameters")
        or configs.get("hyperParameters")
        or {},
        extension=model_config.get("extension") or configs.get("extension") or {},
        prompt_template=None,
        example_content=configs.get("exampleContent") or "",
        rails_config=configs.get("railsConfig") or {},
        accept_language=configs.get("acceptLanguage") or "zh",
        # 新增字段（补齐缺失的参数配置）
        allow_node_confirm=bool(configs.get("allowNodeConfirm", False)),
        need_user_confirm=bool(configs.get("needUserConfirm", True)),
        allow_node_break=bool(configs.get("allowNodeBreak", False)),
        enum_visible=bool(configs.get("enumVisible", False)),
        user_break=bool(configs.get("userBreak", False)),
        auto_ask_template=configs.get("autoAskTemplate") or "",
        mode=configs.get("mode") or "effect",
        assist_recognize=bool(configs.get("assistRecognize", False)),
        assist_example=configs.get("assistExample") or "",
        template_anthropomorphic=bool(configs.get("templateAnthropomorphic", False)),
    )


def _build_questioner_fields(configs: dict) -> list[FieldInfo]:
    raw_fields = configs.get("fieldNames") or configs.get("keyFields") or []
    if not raw_fields:
        raw_fields = (configs.get("userFields") or {}).get("inputs") or []
    fields = []
    for item in raw_fields:
        if not isinstance(item, dict):
            continue
        field_name = (
            item.get("fieldName")
            or item.get("field_name")
            or item.get("id")
            or item.get("name")
        )
        if not field_name:
            continue
        fields.append(
            FieldInfo(
                field_name=str(field_name),
                description=str(
                    item.get("description") or item.get("desc") or field_name
                ),
                type=str(item.get("type") or "string"),
                cn_field_name=str(
                    item.get("cnFieldName") or item.get("cn_field_name") or ""
                ),
                required=bool(item.get("required", False)),
                default_value=item.get("defaultValue")
                or item.get("default_value")
                or "",
                reflection=bool(item.get("reflection", False)),
            )
        )
    return fields


def _build_start_inputs_schema(node: dict) -> dict:
    inputs_schema = {
        "query": "${query}",
        "sys": "${sys}",
        "global_variables": "${global_variables}",
    }
    raw_inputs = _convert_schema(node.get("inputs") or {})
    for reference_path in _iter_reference_paths(raw_inputs):
        root = _resolve_start_input_name(reference_path)
        if not root or root in {"query", "sys", "global_variables"}:
            continue
        inputs_schema[root] = "${" + root + "}"
    configs = node.get("configs") or {}
    for field in (configs.get("userFields") or {}).get("inputs") or []:
        if not isinstance(field, dict):
            continue
        field_id = field.get("id")
        if not field_id:
            continue
        inputs_schema[str(field_id)] = "${" + str(field_id) + "}"
    return inputs_schema


def _attach_node_def(component, node: dict, configs: dict) -> None:
    """Attach trimmed node_def to component instance for callback use.

    仅保留 type_convert_inputs / node_perf_start 回调必需的字段，避免
    checkpoint 序列化冗余（component 实例不进 checkpoint，但保持轻量）。
    """
    if component is None:
        return
    uf = configs.get("userFields") or {}
    sf = configs.get("systemFields") or {}
    try:
        node_def = {
            "node_name": node.get("name", ""),
            "node_type": node.get("type", ""),
            "configs": {
                "userFields": {
                    "inputs": uf.get("inputs", []),
                    "outputs": uf.get("outputs", []),
                },
                "systemFields": {
                    "inputs": sf.get("inputs", []),
                    "outputs": sf.get("outputs", []),
                },
            },
        }
        setattr(component, "_node_def", node_def)
    except Exception:
        # 某些组件实例可能用 __slots__ 或限制属性设置，忽略以不阻塞主流程
        logger.debug(
            "Failed to attach _node_def to component %r",
            type(component).__name__,
            exc_info=True,
        )


def _add_workflow_comp_with_exception(
    workflow: Workflow | LoopGroup,
    comp_id: str,
    component,
    *,
    timeout: float,
    max_retries: int,
    exception_config: ExceptionConfig | None,
    inputs_schema=None,
    stream_inputs_schema=None,
    comp_ability=None,
    wait_for_all: bool | None = None,
) -> None:
    """Register a component on Workflow or LoopGroup.

    LoopGroup.add_workflow_comp does not accept exception-process kwargs; loop body
    components are registered via LoopGroup inside _create_component.
    """
    kwargs = {}
    if inputs_schema is not None:
        kwargs["inputs_schema"] = inputs_schema
    if stream_inputs_schema is not None:
        kwargs["stream_inputs_schema"] = stream_inputs_schema
    if comp_ability is not None:
        kwargs["comp_ability"] = comp_ability
    if wait_for_all:
        kwargs["wait_for_all"] = True
    if isinstance(workflow, LoopGroup):
        workflow.add_workflow_comp(comp_id, component, **kwargs)
    else:
        workflow.add_workflow_comp(
            comp_id,
            component,
            timeout=timeout,
            max_retries=max_retries,
            exception_config=exception_config,
            **kwargs,
        )


_NO_EXCEPTION_TYPES = frozenset({"jiuwen.loop", "jiuwen.exception"})
_NO_RETRY_TYPES = frozenset({"jiuwen.subWorkflow", "jiuwen.workflowComposite"})


def _parse_exception_config(node: dict) -> ExceptionConfig | None:
    """从 IR 节点的 configs.exceptionProcess 中解析异常处理配置。"""
    ep = (node.get("configs") or {}).get("exceptionProcess")
    if not ep:
        return None

    from jiuwen.orchestration.flow.constant import EXCEPTION_HANDLE_INTERRUPT

    node_type = node.get("type", "")
    outputs_schema = _convert_schema(node.get("outputs") or {})

    return ExceptionConfig(
        handle_type=ep.get("handleType", EXCEPTION_HANDLE_INTERRUPT).lower(),
        timeout=ep.get("timeout", 7200.0),
        retry_times=ep.get("retryTimes", 0),
        default_outputs=ep.get("defaultOutputs", {}),
        outputs_schema=outputs_schema,
        _node_type=node_type,
        is_config=True,
    )


def _resolve_branch_condition(
    source_node: dict, source_type: str, branch_id: str
) -> str:
    if "@@" in branch_id:
        parts = branch_id.split("@@")
        if len(parts) == 2:
            source_id = parts[0]
            idx = parts[1].split("_")[1] if "_" in parts[1] else "0"
            if idx == "1":
                return f"${{{source_id}.result}} == '1'"
            return f"${{{source_id}.result}} != '1'"

    if source_type == "jiuwen.branch":
        branch_config = _find_branch_config(source_node, branch_id)
        if branch_config is None:
            return "True"
        return _normalize_branch_expression(
            branch_config.get("boolExpression") or "True"
        )
    if source_type == "jiuwen.intentDetection":
        branch_config = _find_branch_config(source_node, branch_id)
        branch_class = _intent_branch_class(branch_config, branch_id)
        return f'${{{source_node.get("id")}.result}} == "{branch_class}"'
    return "True"


def _find_branch_config(source_node: dict, branch_id: str) -> dict | None:
    configs = source_node.get("configs") or {}
    branches = configs.get("branches") or []
    suffix = branch_id.replace(f"{source_node.get('id')}_", "", 1)
    for branch in branches:
        if not isinstance(branch, dict):
            continue
        current_id = str(branch.get("id") or "")
        if current_id == branch_id or current_id == suffix:
            return branch
    return None


def _intent_branch_class(branch_config: dict | None, branch_id: str) -> str:
    raw_id = str((branch_config or {}).get("id") or branch_id)
    match = re.search(r"branch_(\d+)", raw_id)
    if not match:
        return "\u5206\u7c7b0"
    return f"\u5206\u7c7b{match.group(1)}"


def _aggregate_inputs_schema(inputs_schema: dict) -> dict:
    """Aggregate reads group keys from userFields; flatten IR nesting for registration."""
    user_fields = inputs_schema.get("userFields")
    if isinstance(user_fields, dict):
        return dict(user_fields)
    return inputs_schema


def _normalize_list(value: Any) -> list:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _extract_ref_source_id(value: Any) -> str | None:
    """Extract source component ID from a variable reference like ${node_llm.userFields.raw_output}."""
    if (
        not isinstance(value, str)
        or not value.startswith("${")
        or not value.endswith("}")
    ):
        return None
    inner = value[2:-1]
    if not inner or "." not in inner:
        return None
    return inner.split(".")[0]


def _split_inputs_schema_by_source(
    schema: dict, stream_source_ids: set[str]
) -> tuple[dict | None, dict | None]:
    """Split input schema into batch and stream parts based on referenced source component type.

    Leaf fields referencing stream source components go to stream_schema.
    Others go to batch_schema.  This avoids duplicate keys between
    inputs_schema and stream_inputs_schema validation.

    Returns (batch_schema_or_None, stream_schema_or_None).
    """
    batch_schema: dict = {}
    stream_schema: dict = {}
    for category, fields in schema.items():
        if not isinstance(fields, dict):
            batch_schema[category] = fields
            continue
        batch_fields: dict = {}
        stream_fields: dict = {}
        for field_name, value in fields.items():
            source_id = _extract_ref_source_id(value)
            if source_id is not None and source_id in stream_source_ids:
                stream_fields[field_name] = value
            else:
                batch_fields[field_name] = value
        if batch_fields:
            batch_schema[category] = batch_fields
        if stream_fields:
            stream_schema[category] = stream_fields
    return (batch_schema or None), (stream_schema or None)


def _rewrite_stream_schema_refs(
    schema: dict, source_to_done: dict[str, str]
) -> dict:
    """Rewrite ${source_id.field} refs to use _parallel_done node IDs.

    In parallel joins the stream producer is the _parallel_done node, not the
    original source.  StreamProcessor routes chunks by producer_id, so schema
    refs must point to the _parallel_done node for value resolution.
    """
    if not isinstance(schema, dict) or not source_to_done:
        return schema
    result: dict = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            result[key] = _rewrite_stream_schema_refs(value, source_to_done)
        else:
            source_id = _extract_ref_source_id(value) if isinstance(value, str) else None
            if source_id and source_id in source_to_done:
                inner = value[2:-1]
                result[key] = "${" + source_to_done[source_id] + inner[len(source_id):] + "}"
            else:
                result[key] = value
    return result


def _convert_schema(value: Any) -> Any:
    if isinstance(value, dict):
        converted = {key: _convert_schema(item) for key, item in value.items()}
        if str(converted.get("sourceType") or "").lower() == "reference" and isinstance(
            converted.get("value"), str
        ):
            converted["value"] = _convert_reference_value(converted["value"])
        return converted
    if isinstance(value, list):
        converted_items = [_convert_schema(item) for item in value]
        compacted = _compact_named_input_items(converted_items)
        if compacted is not None:
            return compacted
        return converted_items
    if isinstance(value, str):
        return _convert_string_schema(value)
    return value


def _convert_string_schema(value: str) -> str:
    # If value already looks like a ref path (starts with ${), preserve it
    # _convert_reference_value would strip the ${} wrapper and break is_ref_path checks
    if value.startswith("${") and value.endswith("}"):
        return value
    match = _REFERENCE_PATTERN.match(value)
    if match:
        return _convert_reference_value(match.group(1))
    if "{" not in value or "}" not in value:
        return value
    return _REFERENCE_TOKEN_PATTERN.sub(
        lambda item: _convert_reference_value(item.group(1)),
        value,
    )


def _convert_reference_value(reference: str) -> str:
    normalized_path = _normalize_reference_path(reference)
    if normalized_path.startswith("${") and normalized_path.endswith("}"):
        return normalized_path
    return "${" + normalized_path + "}"


def _normalize_reference_path(reference: str) -> str:
    parts = [segment.strip() for segment in str(reference).split(".")]
    normalized_parts = [
        _REFERENCE_ALIASES.get(segment, segment) for segment in parts if segment
    ]
    return ".".join(normalized_parts)


def _iter_reference_paths(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for item in value.values():
            yield from _iter_reference_paths(item)
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_reference_paths(item)
        return
    if not isinstance(value, str):
        return
    open_match = _OPEN_REFERENCE_PATTERN.match(value)
    if open_match:
        yield _normalize_reference_path(open_match.group(1))
        return
    exact_match = _REFERENCE_PATTERN.match(value)
    if exact_match:
        yield _normalize_reference_path(exact_match.group(1))
        return
    for match in _OPEN_REFERENCE_TOKEN_PATTERN.finditer(value):
        yield _normalize_reference_path(match.group(1))
    for match in _REFERENCE_TOKEN_PATTERN.finditer(value):
        yield _normalize_reference_path(match.group(1))


def _resolve_start_input_name(reference_path: str) -> str | None:
    normalized = _normalize_reference_path(reference_path)
    if normalized in {"query", "sys", "memory", "conversationHistory"}:
        return normalized
    if normalized.startswith("start.userFields."):
        return normalized.split(".", 2)[-1] or None
    if normalized.startswith("start.systemFields."):
        field_name = normalized.split(".", 2)[-1]
        if field_name == "query":
            return "query"
        if field_name == "sys":
            return "sys"
        if field_name == "conversationHistory":
            return "conversationHistory"
        return field_name or None
    return normalized.split(".", 1)[0] or None


def _normalize_branch_expression(expression: str) -> str:
    converted = _convert_string_schema(expression)
    converted = converted.replace("&&", " and ").replace("||", " or ")
    converted = _NEGATION_PATTERN.sub(" not ", converted)
    return " ".join(converted.split())


def _compact_named_input_items(items: list[Any]) -> dict[str, Any] | None:
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    compacted: dict[str, Any] = {}
    for item in items:
        field_name = item.get("name") or item.get("id") or item.get("fieldName")
        if not field_name:
            return None
        if "value" in item:
            compacted[str(field_name)] = item["value"]
            continue
        if "default" in item:
            compacted[str(field_name)] = item["default"]
            continue
        return None
    return compacted
