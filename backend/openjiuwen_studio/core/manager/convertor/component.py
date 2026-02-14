#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Dict, List, Callable

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.manager.convertor.components.code import code_convert
from openjiuwen_studio.core.manager.convertor.components.empty import empty_convert
from openjiuwen_studio.core.manager.convertor.components.end import end_convert
from openjiuwen_studio.core.manager.convertor.components.input import input_convert
from openjiuwen_studio.core.manager.convertor.components.intent import intent_convert
from openjiuwen_studio.core.manager.convertor.components.llm import llm_convert
from openjiuwen_studio.core.manager.convertor.components.loop import loop_convert, loop_continue_convert, \
    loop_break_convert
from openjiuwen_studio.core.manager.convertor.components.output import output_convert
from openjiuwen_studio.core.manager.convertor.components.plugin import plugin_convert
from openjiuwen_studio.core.manager.convertor.components.questioner import questioner_convert
from openjiuwen_studio.core.manager.convertor.components.set_variable import set_variable_convert
from openjiuwen_studio.core.manager.convertor.components.start import start_convert
from openjiuwen_studio.core.manager.convertor.components.sub_workflow import sub_workflow_convert
from openjiuwen_studio.core.manager.convertor.components.switch import switch_convert
from openjiuwen_studio.core.manager.convertor.connection import connection_convert
from openjiuwen_studio.core.manager.convertor.components.text_editor import text_editor_convert
from openjiuwen_studio.core.manager.convertor.components.variable_merge import variable_merge_convert
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.schemas.node import Node, Edge
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException


def _loop_sub_components_convert(node: Node, space_id: str) -> List[dsl.Component]:
    blocks = node.blocks
    if not blocks:
        raise ValueError("loop blocks is empty")
    nodes = [Node(**block) for block in blocks]
    return component_convert(node.edges, nodes, space_id, True)


def _loop_configs_convert(node: Node, space_id: str) -> dsl.LoopConfig:
    sub_components = _loop_sub_components_convert(node, space_id)

    start_id: List[str] = []
    end_id: List[str] = []
    for block in node.blocks:
        sub_node = Node(**block)
        node_type = int(sub_node.type)
        if node_type == dsl.ComponentType.COMPONENT_TYPE_EMPTY_START:
            start_id.append(sub_node.id)
        elif node_type == dsl.ComponentType.COMPONENT_TYPE_EMPTY_END:
            end_id.append(sub_node.id)

    edges = node.edges
    if not edges:
        raise ValueError("loop edges is empty")
    sub_edges = connection_convert(edges)

    return dsl.LoopConfig(
        loop_body=dsl.BaseFlow(
            start_id=start_id,
            end_id=end_id,
            components=sub_components,
            connections=sub_edges,
        )
    )


def component_convert(edges: List[Edge], nodes: list[Node], space_id: str, sub_convert: bool) -> List[dsl.Component]:
    try:
        components: List[dsl.Component] = []

        def _convert_loop(node: Node, space_id: str, sub_convert: bool) -> dsl.Component:
            if sub_convert:
                raise TypeError("loop component can not contain sub loop component")
            c = loop_convert(node)
            configs = _loop_configs_convert(node, space_id)
            c.configs = configs.model_dump()
            return c

        converters: Dict[int, Callable[[Node, str, bool], dsl.Component]] = {
            dsl.ComponentType.COMPONENT_TYPE_START: lambda n, s, sub: start_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_LLM: lambda n, s, sub: llm_convert(n, s),
            dsl.ComponentType.COMPONENT_TYPE_END: lambda n, s, sub: end_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_IF: lambda n, s, sub: switch_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_LOOP: _convert_loop,
            dsl.ComponentType.COMPONENT_TYPE_INPUT: lambda n, s, sub: input_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_OUTPUT: lambda n, s, sub: output_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_QUESTION: lambda n, s, sub: questioner_convert(n, s),
            dsl.ComponentType.COMPONENT_TYPE_CONTINUE: lambda n, s, sub: loop_continue_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_BREAK: lambda n, s, sub: loop_break_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_TEXT_EDITOR: lambda n, s, sub: text_editor_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_INTENT: lambda n, s, sub: intent_convert(n, s),
            dsl.ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: lambda n, s, sub: sub_workflow_convert(n, s),
            dsl.ComponentType.COMPONENT_TYPE_EMPTY_START: lambda n, s, sub: empty_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_EMPTY_END: lambda n, s, sub: empty_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_CODE: lambda n, s, sub: code_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: lambda n, s, sub: variable_merge_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_SET_VARIABLE: lambda n, s, sub: set_variable_convert(n),
            dsl.ComponentType.COMPONENT_TYPE_PLUGIN: lambda n, s, sub: plugin_convert(n, s),
        }

        error_code_map: Dict[int, int] = {
            dsl.ComponentType.COMPONENT_TYPE_START: StatusCode.START_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_LLM: StatusCode.LLM_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_END: StatusCode.END_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_IF: StatusCode.IF_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_LOOP: StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_INPUT: StatusCode.INPUT_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_OUTPUT: StatusCode.OUTPUT_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_QUESTION: StatusCode.QUESTION_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_CONTINUE: StatusCode.CONTINUE_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_BREAK: StatusCode.BREAK_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_TEXT_EDITOR: StatusCode.TEXTEDITOR_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_INTENT: StatusCode.INTENT_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: StatusCode.SUBWORKFLOW_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_EMPTY_START: StatusCode.EMPTY_START_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_EMPTY_END: StatusCode.EMPTY_END_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_CODE: StatusCode.CODE_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_SET_VARIABLE: StatusCode.SET_VARIABLE_COMPONENT_CONVERT_FAILED.code,
            dsl.ComponentType.COMPONENT_TYPE_PLUGIN: StatusCode.PLUGIN_COMPONENT_CONVERT_FAILED.code,
        }

        for node in nodes:
            node_type = int(node.type)
            try:
                converter = converters.get(node_type)
                if not converter:
                    logger.error(f'Unsupported component type in {node_type}')
                    continue
                component = converter(node, space_id, sub_convert)
            except Exception as ce:
                code = error_code_map.get(node_type, StatusCode.COMPONENT_CONVERT_FAILED.code)
                raise JiuWenComponentException(
                    code=code,
                    message=str(ce),
                    component_id=node.id,
                    component_type=node_type,
                    error_stage="convert"
                ) from ce
            if component:
                components.append(component)

        return components
    except (TypeError, ValueError, AttributeError) as e:
        log_exception(e)
        raise ValueError(f"Invalid workflow schema or input: {e}") from e
