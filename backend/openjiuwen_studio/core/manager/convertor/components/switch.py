#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from enum import IntEnum
from typing import List

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.schemas.node import Node, BranchCondition, Edge
from openjiuwen_studio.core.manager.convertor.components.common import base_value_convert
from openjiuwen_studio.core.common.dsl import ComponentType

logic_mapping = {
    1: " || ",
    2: " && "
}


class OperatorType(IntEnum):
    EQUAL = 1,
    NOT_EQUAL = 2,
    LEN_GREATER = 3,
    LEN_GREATER_OR_EQUAL = 4,
    LEN_LESS_THAN = 5,
    LEN_LESS_THAN_OR_EQUAL = 6,
    CONTAIN = 7,
    NOT_CONTAIN = 8,
    EMPTY = 9,
    NOT_EMPTY = 10,
    GREATER = 11,
    GREATER_OR_EQUAL = 12,
    LESS_THAN = 13,
    LESS_THAN_OR_EQUAL = 14,


operator_type_mapping = {
    "eq": OperatorType.EQUAL,
    "neq": OperatorType.NOT_EQUAL,
    "gt": OperatorType.GREATER,
    "gte": OperatorType.GREATER_OR_EQUAL,
    "lt": OperatorType.LESS_THAN,
    "lte": OperatorType.LESS_THAN_OR_EQUAL,
    "in": OperatorType.CONTAIN,
    "nin": OperatorType.NOT_CONTAIN,
    "contains": OperatorType.CONTAIN,
    "not_contains": OperatorType.NOT_CONTAIN,
    "is_empty": OperatorType.EMPTY,
    "is_not_empty": OperatorType.NOT_EMPTY,
}


def _needs_quoting(condition_value) -> bool:
    """Check if a constant value needs to be quoted in the expression."""
    if condition_value.type != "constant":
        return False
    if condition_value.schema is None:
        return False
    return condition_value.schema.type in ("string", "date-time")


def _bool_expression_assemble(left: str, right: str, operator: int) -> str:
    operator_map = {
        OperatorType.EQUAL: lambda left_operand, right_operand: f"{left_operand} == {right_operand}",
        OperatorType.NOT_EQUAL: lambda left_operand, right_operand: f"{left_operand} != {right_operand}",
        OperatorType.LEN_GREATER: lambda left_operand, right_operand: f"length({left_operand}) > {right_operand}",
        OperatorType.LEN_GREATER_OR_EQUAL: lambda left_operand,
                                                  right_operand: f"length({left_operand}) >= {right_operand}",
        OperatorType.LEN_LESS_THAN: lambda left_operand, right_operand: f"length({left_operand}) < {right_operand}",
        OperatorType.LEN_LESS_THAN_OR_EQUAL: lambda left_operand,
                                                    right_operand: f"length({left_operand}) <= {right_operand}",
        OperatorType.CONTAIN: lambda left_operand, right_operand: f"{right_operand} in {left_operand}",
        OperatorType.NOT_CONTAIN: lambda left_operand, right_operand: f"{right_operand} not_in {left_operand}",
        OperatorType.EMPTY: lambda left_operand, right_operand: f"is_empty({left_operand})",
        OperatorType.NOT_EMPTY: lambda left_operand, right_operand: f"is_not_empty({left_operand})",
        OperatorType.LESS_THAN: lambda left_operand, right_operand: f"{left_operand} < {right_operand}",
        OperatorType.LESS_THAN_OR_EQUAL: lambda left_operand, right_operand: f"{left_operand} <= {right_operand}",
        OperatorType.GREATER: lambda left_operand, right_operand: f"{left_operand} > {right_operand}",
        OperatorType.GREATER_OR_EQUAL: lambda left_operand, right_operand: f"{left_operand} >= {right_operand}",
    }

    return operator_map.get(operator, lambda left_operand, right_operand: "")(left, right)


def _switch_conditions_convert(logic: int, conditions: List[BranchCondition]) -> str:
    try:
        bool_expression = ""
        for num, condition in enumerate(conditions):
            if num != 0:
                if num == 1:
                    bool_expression = "(" + bool_expression + ")"
                bool_expression += logic_mapping[logic]

            left_type = condition.left.type
            if left_type != "ref":
                raise ValueError("left condition type is not ref")
            left_expression = base_value_convert(condition.left)
            is_right_array = False
            right_array_elements = []
            if condition.right is not None:
                # Check if right value is a constant array
                if (
                    condition.right.type == "constant"
                    and isinstance(condition.right.content, list)
                ):
                    is_right_array = True
                    right_array_elements = condition.right.content
            operator = 0
            if isinstance(condition.operator, int):
                operator = condition.operator
            elif isinstance(condition.operator, str):
                operator = operator_type_mapping.get(condition.operator)
                logger.info(operator)
            else:
                raise ValueError("invalid operator type, not int or string")

            expressions = []
            if is_right_array and operator in (OperatorType.CONTAIN, OperatorType.NOT_CONTAIN):
                # 只有 in / not_in 才按数组展开
                for element in right_array_elements:
                    # Handle element type, add quotes if string
                    element_expr = str(element)
                    if isinstance(element, str):
                        element_expr = f"\"{element_expr}\""
                    # Assemble sub-expression
                    sub_expr = _bool_expression_assemble(left_expression, element_expr, operator)
                    expressions.append(sub_expr)
            else:
                # Original logic for non-array right side
                right_expression = ""
                if condition.right is not None:
                    right_expression = base_value_convert(condition.right)
                    if _needs_quoting(condition.right):
                        # 转义字符串中的双引号，然后添加外层引号
                        escaped_expression = right_expression.replace('"', '\\"')
                        right_expression = f'"{escaped_expression}"'
                expressions.append(_bool_expression_assemble(left_expression, right_expression, operator))

            # Join expressions with 'and' if multiple
            if len(expressions) > 1:
                expression = " and ".join(f"({expr})" for expr in expressions)
            else:
                expression = expressions[0]

            if num != 0:
                expression = "(" + expression + ")"
            bool_expression += expression
        return bool_expression
    except Exception as e:
        raise e


def switch_convert(node: Node) -> dsl.Component:
    try:
        data = node.data
        branches = data.branches
        if not branches:
            raise TypeError("branches is empty")

        convert_branches: List[dsl.Branch] = []
        for branch in branches:
            expression = _switch_conditions_convert(branch.logic, branch.conditions)
            branch_id = branch.branch_id
            convert_branch = dsl.Branch(
                branch_id=branch_id,
                bool_expression=expression
            )
            convert_branches.append(convert_branch)

        return dsl.Component(
            id=node.id,
            type=ComponentType.COMPONENT_TYPE_IF,
            type_version="1.0.0",
            branches=convert_branches,
            description="",
            name=data.title
        )
    except Exception as e:
        raise ValueError(f"Failed to convert switch node: {str(e)}") from e
