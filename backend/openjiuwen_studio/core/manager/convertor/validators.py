#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
"""
Workflow Canvas 节点业务逻辑校验模块

在 WorkflowCanvas Pydantic 验证后增加业务逻辑校验，将前端校验规则迁移到后端。
"""
from typing import Any

from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.schemas.node import (
    Node,
    Edge,
    BranchInfo,
)


# ============================================================================
# 公用校验函数
# ============================================================================

def validate_title(node: Node) -> None:
    """
    校验节点标题不能为空

    Args:
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当标题为空时
    """
    if not node.data.title or node.data.title.strip() == "":
        raise JiuWenComponentException(
            code=StatusCode.COMPONENT_CONFIG_INVALID.code,
            message=StatusCode.COMPONENT_CONFIG_INVALID.errmsg.format(
                msg=f"[{node.data.title or 'node'}] title is empty, please check!"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )


def validate_model(node: Node) -> None:
    """
    校验 LLM/Intent/Questioner 的 model.id 不能为空

    Args:
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当 model.id 为空时
    """
    component_name = node.data.title or "component"

    # 检查 inputs -> llmParam -> model -> id 链路
    if node.data.inputs is None:
        raise JiuWenComponentException(
            code=StatusCode.LLM_COMPONENT_CONFIG_INVALID.code,
            message=StatusCode.LLM_COMPONENT_CONFIG_INVALID.errmsg.format(
                msg=f"[{component_name}] model config is empty, please check!"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    llm_param = node.data.inputs.llm_param
    if llm_param is None:
        raise JiuWenComponentException(
            code=StatusCode.LLM_COMPONENT_CONFIG_INVALID.code,
            message=StatusCode.LLM_COMPONENT_CONFIG_INVALID.errmsg.format(
                msg=f"[{component_name}] model config is empty, please check!"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    if llm_param.model is None or llm_param.model.id is None or llm_param.model.id == "":
        raise JiuWenComponentException(
            code=StatusCode.LLM_COMPONENT_CONFIG_INVALID.code,
            message=StatusCode.LLM_COMPONENT_CONFIG_INVALID.errmsg.format(
                msg=f"[{component_name}] model config is empty, please check!"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )


def validate_input_parameters(node: Node, all_nodes: list[Node]) -> None:
    """
    校验输入参数：引用变量必须存在，常量不能为空（if required）

    Args:
        node: 待校验的节点
        all_nodes: 所有节点列表，用于验证引用是否存在

    Raises:
        JiuWenComponentException: 当输入参数校验失败时
    """
    if node.data.inputs is None or node.data.inputs.input_parameters is None:
        return

    node_ids = {n.id for n in all_nodes}

    for param_name, param in node.data.inputs.input_parameters.items():
        # 如果是 ref 类型，检查源节点是否存在
        if param.type == "ref":
            if param.content is None or len(param.content) == 0:
                continue
            source_node_id = param.content[0]
            if source_node_id not in node_ids:
                raise JiuWenComponentException(
                    code=StatusCode.COMPONENT_CONFIG_INVALID.code,
                    message=StatusCode.COMPONENT_CONFIG_INVALID.errmsg.format(
                        msg=f"[{node.data.title or 'node'}' "
                            f"ref parameter [{param_name}] "
                            f"source node [{source_node_id}] not found, please check!"),
                    component_id=node.id,
                    component_type=int(node.type),
                    error_stage="validate"
                )

        # 如果是 constant 类型，检查值是否为空
        elif param.type == "constant":
            # 检查 content 字段（BaseValue 使用 content 而不是 value）
            content = getattr(param, 'content', None)
            # 如果 content 为 None，跳过检查（可能是前端未设置）
            if content is None:
                continue
            # 检查空字符串
            if isinstance(content, str) and content.strip() == "":
                raise JiuWenComponentException(
                    code=StatusCode.COMPONENT_CONFIG_INVALID.code,
                    message=StatusCode.COMPONENT_CONFIG_INVALID.errmsg.format(
                        msg=f"[{node.data.title or 'node'}] parameter [{param_name}] is empty, please check!"),
                    component_id=node.id,
                    component_type=int(node.type),
                    error_stage="validate"
                )


def validate_exception_return_content(node: Node) -> None:
    """
    校验 Code 组件：当 process_type=return_content 时，必须包含 result

    Args:
        node: 待校验的节点

    Raises:f
        JiuWenComponentException: 当异常返回内容校验失败时
    """
    if node.data.exception_config is None:
        return

    # process_type == "return_content" 表示返回内容模式
    if node.data.exception_config.process_type.value == "return_content":
        return_content = node.data.exception_config.return_content
        # 检查 return_content 是否为 None、空字典或不包含 result
        if return_content is None or not return_content or "result" not in return_content:
            raise JiuWenComponentException(
                code=StatusCode.CODE_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.CODE_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Code component'}] "
                        f"return content must contain 'result' "
                        f"when process_type is return_content"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )


def validate_streaming_template(node: Node) -> None:
    """
    校验 End/Output 组件：开启流式输出时，输出模板不能为空

    Args:
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当流式输出模板为空时
    """
    if node.data.inputs is None:
        return

    if getattr(node.data.inputs, 'streaming', False):
        content = node.data.inputs.content
        if content is None or content.content is None or content.content.strip() == "":
            raise JiuWenComponentException(
                code=StatusCode.OUTPUT_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.OUTPUT_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title}] output template cannot be empty when streaming is enabled"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )


def validate_loop_num_range(node: Node, loop_num_value: Any) -> None:
    """
    校验循环次数必须是 1-1000 的整数

    Args:
        node: 待校验的节点
        loop_num_value: 循环次数值

    Raises:
        JiuWenComponentException: 当循环次数超出范围时
    """
    try:
        loop_num = int(loop_num_value)
        if loop_num < 1 or loop_num > 1000:
            raise JiuWenComponentException(
                code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Loop component'}] loop number must be an integer between 1 and 1000"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )
    except (ValueError, TypeError) as e:
        raise JiuWenComponentException(
            code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Loop component'}] loop number must be a valid integer"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        ) from e


def validate_array_variable(var_name: str, var_value: Any, node: Node) -> None:
    """
    校验数组变量：constant 类型必须是数组类型且不能为空

    Args:
        var_name: 变量名
        var_value: 变量值
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当数组变量校验失败时
    """
    # 只对 constant 类型进行校验，ref 类型由被引用节点决定类型
    if var_value.type != "constant":
        return

    # 检查 schema.type 是否为数组类型
    schema_type = var_value.schema.type if var_value.schema else None
    if schema_type != "array":
        raise JiuWenComponentException(
            code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Loop component'}] variable {var_name} must be of array type"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    # 检查 content 是否为空
    if var_value.content is None or (isinstance(var_value.content, list) and len(var_value.content) == 0):
        raise JiuWenComponentException(
            code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Loop component'}] array variable {var_name} cannot be empty"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )


def validate_max_response_range(node: Node, max_response: int) -> None:
    """
    校验 Questioner 最大提问次数：必须 >0 且 <=10

    Args:
        node: 待校验的节点
        max_response: 最大提问次数

    Raises:
        JiuWenComponentException: 当最大提问次数超出范围时
    """
    if max_response <= 0 or max_response > 10:
        raise JiuWenComponentException(
            code=StatusCode.QUESTION_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.QUESTION_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Questioner component'}] "
                    f"max response count must be an integer "
                    f"greater than 0 and not greater than 10"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )


def validate_outputs_count(node: Node, min_count: int) -> None:
    """
    校验输出变量数量：至少需要 min_count 个变量

    Args:
        node: 待校验的节点
        min_count: 最小变量数量

    Raises:
        JiuWenComponentException: 当输出变量数量不足时
    """
    outputs = node.data.outputs
    if outputs is None or len(outputs.properties) < min_count:
        raise JiuWenComponentException(
            code=StatusCode.QUESTION_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.QUESTION_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Questioner component'}] output requires at least {min_count} variables"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )


def validate_variable_merge(node: Node) -> None:
    """
    校验 Variable-merge 组件：至少需要一个分组，分组名称不能为空，每个分组至少包含一个变量

    Args:
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当变量聚合配置校验失败时
    """
    if node.data.inputs is None or node.data.inputs.variable_merge is None:
        return

    variable_merge = node.data.inputs.variable_merge
    if len(variable_merge) == 0:
        raise JiuWenComponentException(
            code=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Variable-merge component'}] at least one group is required"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    for group in variable_merge:
        if group.name is None or group.name.strip() == "":
            raise JiuWenComponentException(
                code=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Variable-merge component'}] group name cannot be empty"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )
        if group.items is None or len(group.items) == 0:
            raise JiuWenComponentException(
                code=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.VARIABLE_MERGE_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Variable-merge component'}] "
                        f"group {group.name} must contain "
                        f"at least one variable"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )


def validate_intermediate_vars(node: Node) -> None:
    """
    校验 Loop 组件中间变量不能为空

    Args:
        node: 待校验的节点

    Raises:
        JiuWenComponentException: 当中间变量为空时
    """
    if node.data.inputs is None or node.data.inputs.loop_param is None:
        return

    intermediate_var = node.data.inputs.loop_param.intermediate_var
    if intermediate_var is not None:
        for var_name, var in intermediate_var.items():
            if var.content is None or var.content == "":
                raise JiuWenComponentException(
                    code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
                    message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.errmsg.format(
                        msg=f"[{node.data.title or 'Loop component'}] "
                            f"intermediate variable {var_name} "
                            f"cannot be empty"),
                    component_id=node.id,
                    component_type=int(node.type),
                    error_stage="validate"
                )


def validate_branch_connection(branch: BranchInfo, all_edges: list[Edge], node_id: str, node_title: str) -> None:
    """
    校验 Condition 分支连线：分支必须连线到节点

    Args:
        branch: 分支信息
        all_edges: 所有边列表
        node_id: 当前节点 ID
        node_title: 当前节点标题

    Raises:
        JiuWenComponentException: 当分支未连线时
    """
    # 检查是否有从该分支端口出发的边
    branch_connected = False
    for edge in all_edges:
        if edge.source_node_id == node_id and edge.source_port_id == branch.branch_id:
            branch_connected = True
            break

    if not branch_connected:
        raise JiuWenComponentException(
            code=StatusCode.IF_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.IF_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node_title or 'Condition component'}] branch [{branch.branch_id}] must be connected to a node"),
            component_id=node_id,
            component_type=int(ComponentType.COMPONENT_TYPE_IF),
            error_stage="validate"
        )


# ============================================================================
# 各组件校验函数
# ============================================================================

def validate_llm_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """LLM 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_model(node)
    validate_input_parameters(node, all_nodes)


def validate_code_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Code 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_exception_return_content(node)
    validate_input_parameters(node, all_nodes)


def validate_loop_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Loop 组件校验"""
    _ = all_nodes, all_edges  # 未使用
    validate_title(node)

    if node.data.inputs is None or node.data.inputs.loop_param is None:
        return

    loop_param = node.data.inputs.loop_param

    # 计数循环校验
    if loop_param.loop_num is not None:
        validate_loop_num_range(node, loop_param.loop_num.content)

    # 数组循环校验
    if loop_param.loop_array is not None:
        for var_name, var_value in loop_param.loop_array.items():
            validate_array_variable(var_name, var_value, node)

    # 中间变量校验
    validate_intermediate_vars(node)

    # 循环体校验 - 检查 blocks 是否包含 type=15 和 type=16 的节点
    if node.blocks is not None and len(node.blocks) > 0:
        has_start = False
        has_end = False
        for block in node.blocks:
            if int(block.get('type', 0)) == ComponentType.COMPONENT_TYPE_EMPTY_START:  # 循环开始节点
                has_start = True
            elif int(block.get('type', 0)) == ComponentType.COMPONENT_TYPE_EMPTY_END:  # 循环结束节点
                has_end = True
        if not has_start or not has_end:
            raise JiuWenComponentException(
                code=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.LOOP_COMPONENT_CONVERT_FAILED.message.format(
                    msg=f"[{node.data.title or 'Loop component'}] loop body must contain start and end nodes"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )


def validate_intent_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Intent 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_model(node)

    # 检查 query 参数
    if node.data.inputs is not None and node.data.inputs.input_parameters is not None:
        if "query" not in node.data.inputs.input_parameters:
            raise JiuWenComponentException(
                code=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Intent component'}] query parameter must exist"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )

    # 校验意图列表
    intents = node.data.inputs.intents if node.data.inputs else None
    if intents is None or len(intents) == 0:
        raise JiuWenComponentException(
            code=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Intent component'}] at least one intent is required"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    for intent in intents:
        if intent.name is None or len(intent.name) > 50:
            raise JiuWenComponentException(
                code=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.code,
                message=StatusCode.INTENT_COMPONENT_CONVERT_FAILED.errmsg.format(
                    msg=f"[{node.data.title or 'Intent component'}] "
                        f"intent name cannot be empty "
                        f"and must not exceed 50 characters"),
                component_id=node.id,
                component_type=int(node.type),
                error_stage="validate"
            )

    validate_input_parameters(node, all_nodes)


def validate_branch_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Condition 组件校验"""
    _ = all_nodes  # 未使用
    validate_title(node)

    branches = node.data.branches
    if branches is None or len(branches) == 0:
        raise JiuWenComponentException(
            code=StatusCode.IF_COMPONENT_CONVERT_FAILED.code,
            message=StatusCode.IF_COMPONENT_CONVERT_FAILED.errmsg.format(
                msg=f"[{node.data.title or 'Condition component'}] at least one branch is required"),
            component_id=node.id,
            component_type=int(node.type),
            error_stage="validate"
        )

    for branch in branches:
        # 检查分支条件值不能为空
        if branch.conditions is not None:
            for condition in branch.conditions:
                # 检查 left 值
                if condition.left is not None and condition.left.type == "constant":
                    if condition.left.content is None or condition.left.content == "":
                        raise JiuWenComponentException(
                            code=StatusCode.IF_COMPONENT_CONVERT_FAILED.code,
                            message=StatusCode.IF_COMPONENT_CONVERT_FAILED.errmsg.format(
                                msg=f"[{node.data.title or 'Condition component'}/] "
                                    f"branch condition value cannot be empty"),
                            component_id=node.id,
                            component_type=int(node.type),
                            error_stage="validate"
                        )
                # 检查 right 值（如果存在）
                operator = condition.operator
                unary_operators = {"is_empty", "is_not_empty"}
                requires_right = operator not in unary_operators

                if requires_right and condition.right is not None and condition.right.type == "constant":
                    if condition.right.content is None or condition.right.content == "":
                        raise JiuWenComponentException(
                            code=StatusCode.IF_COMPONENT_CONVERT_FAILED.code,
                            message=StatusCode.IF_COMPONENT_CONVERT_FAILED.errmsg.format(
                                msg=f"[{node.data.title or 'Condition component'}/] "
                                    f"branch condition value cannot be empty"),
                            component_id=node.id,
                            component_type=int(node.type),
                            error_stage="validate"
                        )

        # 检查分支是否连线到节点
        validate_branch_connection(branch, all_edges, node.id, node.data.title)


def validate_start_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Start 组件校验"""
    _ = all_nodes, all_edges  # 未使用
    validate_title(node)


def validate_end_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """End 组件校验"""
    _ = all_edges  # 未使用
    validate_input_parameters(node, all_nodes)
    validate_streaming_template(node)


def validate_output_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Output 组件校验"""
    _ = all_edges  # 未使用
    validate_input_parameters(node, all_nodes)
    validate_streaming_template(node)


def validate_questioner_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Questioner 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_model(node)
    validate_input_parameters(node, all_nodes)

    # 校验最大提问次数
    if node.data.inputs is not None:
        max_response = node.data.inputs.max_response
        validate_max_response_range(node, max_response)

    # 校验输出变量数量
    validate_outputs_count(node, 2)


def validate_continue_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Continue 组件校验"""
    _ = all_edges, all_nodes  # 未使用
    validate_title(node)


def validate_variable_merge_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Variable-merge 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_input_parameters(node, all_nodes)
    validate_variable_merge(node)


def validate_plugin_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Plugin 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_input_parameters(node, all_nodes)


def validate_sub_workflow_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Sub-workflow 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_input_parameters(node, all_nodes)


def validate_text_editor_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Text-editor 组件校验"""
    _ = all_edges  # 未使用
    validate_title(node)
    validate_input_parameters(node, all_nodes)


def validate_input_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Input 组件校验"""
    _ = all_edges, all_nodes  # 未使用
    validate_title(node)


def validate_break_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Break 组件校验"""
    _ = all_edges, all_nodes  # 未使用
    validate_title(node)


def validate_set_variable_node(node: Node, all_nodes: list[Node], all_edges: list[Edge]) -> None:
    """Set-variable 组件校验"""
    _ = all_edges, all_nodes  # 未使用
    validate_title(node)


# ============================================================================
# 主入口函数
# ============================================================================

def validate_canvas_nodes(canvas) -> None:
    """
    校验 canvas 中的所有节点（入口函数）

    Args:
        canvas: WorkflowCanvas 实例

    Raises:
        JiuWenComponentException: 当校验失败时
    """
    # 构建已连接节点集合
    connected_ids = set()
    for edge in canvas.edges:
        connected_ids.add(edge.source_node_id)
        connected_ids.add(edge.target_node_id)

    # 组件类型 -> 校验函数 映射
    validators = {
        ComponentType.COMPONENT_TYPE_START: validate_start_node,
        ComponentType.COMPONENT_TYPE_END: validate_end_node,
        ComponentType.COMPONENT_TYPE_LLM: validate_llm_node,
        ComponentType.COMPONENT_TYPE_IF: validate_branch_node,
        ComponentType.COMPONENT_TYPE_LOOP: validate_loop_node,
        ComponentType.COMPONENT_TYPE_CODE: validate_code_node,
        ComponentType.COMPONENT_TYPE_OUTPUT: validate_output_node,
        ComponentType.COMPONENT_TYPE_INTENT: validate_intent_node,
        ComponentType.COMPONENT_TYPE_QUESTION: validate_questioner_node,
        ComponentType.COMPONENT_TYPE_INPUT: validate_input_node,
        ComponentType.COMPONENT_TYPE_TEXT_EDITOR: validate_text_editor_node,
        ComponentType.COMPONENT_TYPE_CONTINUE: validate_continue_node,
        ComponentType.COMPONENT_TYPE_BREAK: validate_break_node,
        ComponentType.COMPONENT_TYPE_SUB_WORKFLOW: validate_sub_workflow_node,
        ComponentType.COMPONENT_TYPE_SET_VARIABLE: validate_set_variable_node,
        ComponentType.COMPONENT_TYPE_VARIABLE_MERGE: validate_variable_merge_node,
        ComponentType.COMPONENT_TYPE_PLUGIN: validate_plugin_node,
    }

    # 遍历节点进行校验
    for node in canvas.nodes:
        # 只校验有连接的节点
        if node.id not in connected_ids:
            continue

        try:
            node_type = int(node.type)
        except (ValueError, TypeError):
            continue

        validator = validators.get(node_type)

        if validator is not None:
            # 所有 validator 统一使用三参数格式
            validator(node, canvas.nodes, canvas.edges)
