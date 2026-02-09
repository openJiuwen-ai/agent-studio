#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
from typing import List, Any

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.common import dsl
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.core.manager.convertor.components.end import end_outputs_convert
from openjiuwen_studio.core.manager.convertor.components.start import start_inputs_convert
from openjiuwen_studio.core.manager.internal.workflow import WorkflowCanvas
from openjiuwen_studio.schemas.node import NodeData
from openjiuwen_studio.core.manager.utils.utils import convert_to_properties_format
from openjiuwen_studio.schemas.workflow import WorkflowBase
from openjiuwen_studio.core.manager.convertor.component import component_convert
from openjiuwen_studio.core.manager.convertor.connection import connection_convert
from pydantic import ValidationError

from openjiuwen_studio.core.common.exceptions import JiuWenComponentException
from openjiuwen_studio.core.common.status_code import StatusCode
from openjiuwen_studio.core.manager.convertor.validators import validate_canvas_nodes


def extract_inputs_and_outputs_from_canvas(canvas_data: dict) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    从原始canvas数据中提取inputs和outputs。

    Args:
        canvas_data: 原始的canvas字典数据

    Returns:
        tuple: (inputs, outputs)
    """
    try:
        nodes = canvas_data.get('nodes', [])

        inputs = []
        outputs = []

        for node in nodes:
            node_type = node.get('type')
            if node_type is None:
                continue

            try:
                node_type_int = int(node_type)

                if node_type_int == dsl.ComponentType.COMPONENT_TYPE_START:
                    data_dict = node.get('data', {})
                    # 将字典转换为NodeData对象
                    try:
                        node_data = NodeData(**data_dict)
                        inputs = start_inputs_convert(node_data)
                        logger.debug(f"Found start node, extracted inputs: {inputs}")
                    except ValidationError as e:
                        logger.warning(f"Failed to parse start node data: {e}, using empty inputs")
                        inputs = []

                elif node_type_int == dsl.ComponentType.COMPONENT_TYPE_END:
                    data_dict = node.get('data', {})
                    # 将字典转换为NodeData对象
                    try:
                        node_data = NodeData(**data_dict)
                        outputs = end_outputs_convert(node_data)
                        logger.debug(f"Found end node, extracted outputs: {outputs}")
                    except ValidationError as e:
                        logger.warning(f"Failed to parse end node data: {e}, using empty outputs")
                        outputs = []

            except (ValueError, TypeError) as e:
                logger.warning(f"Invalid node type '{node_type}', skipping: {e}")
                continue

        if not inputs:
            logger.warning("No start node found in workflow canvas data")
        if not outputs:
            logger.warning("No end node found in workflow canvas data")

        return inputs, outputs

    except Exception as e:
        logger.error(f"Failed to extract canvas data inputs/outputs: {e}")
        return [], []


def _friendly_validation_message(err: dict, schema: dict) -> tuple[str, str, int, str]:
    loc = err.get('loc', [])
    msg = err.get('msg', '')
    # 默认值
    component_id = ''
    component_type = 0
    field_path = '.'.join([str(p) for p in loc])
    # 提取node索引
    try:
        if 'nodes' in loc:
            idx = loc.index('nodes')
            node_idx = loc[idx + 1] if idx + 1 < len(loc) else None
            if isinstance(node_idx, int):
                node = schema.get('nodes', [])[node_idx]
                component_id = node.get('id', '')
                component_type = int(node.get('type', 0))
    except Exception as exc:
        logger.warning(
            "Failed to extract node info, use empty defaults | loc=%r node_idx=%r error=%s",
            loc, node_idx, exc
        )
        component_id = ''  # 与上面默认值保持一致
        component_type = 0

    def tuple_to_loc_str(tuple_path):
        return '_'.join(str(item) for item in tuple_path)

    err_loc = tuple_to_loc_str(loc)

    # 字段友好信息展示
    hint = msg + ", error location: " + err_loc
    is_missing_llm_model = (
            'llmParam' in field_path
            and field_path.endswith('model')
            and 'missing' in err.get('type', '')
    )
    if is_missing_llm_model:
        hint = '未配置模型，请在LLM组件中选择模型'
    elif msg.lower().startswith('field required'):
        hint = f"字段缺失: {field_path}"

    return hint, field_path, component_type, component_id


def workflow_convert(workflow_info: WorkflowBase, skip_validation: bool = False) -> dsl.Workflow:
    try:
        workflow_schema = json.loads(getattr(workflow_info, "workflow_schema", "{}") or "{}")
        try:
            canvas = WorkflowCanvas(**workflow_schema)
        except ValidationError as e:
            # 取第一条错误生成友好提示
            errs = e.errors() or []
            err = errs[0] if errs else {"msg": str(e), "loc": []}
            hint, field_path, component_type, component_id = _friendly_validation_message(err, workflow_schema)
            # 按组件类型选择错误码
            code = StatusCode.COMPONENT_CONFIG_INVALID.code
            if component_type == dsl.ComponentType.COMPONENT_TYPE_LLM:
                code = StatusCode.LLM_COMPONENT_CONFIG_INVALID.code
            raise JiuWenComponentException(
                code=code,
                message=StatusCode.COMPONENT_CONFIG_INVALID.errmsg.format(msg=hint),
                component_id=component_id,
                component_type=component_type,
                error_stage="validate"
            ) from e
        # 2. 业务逻辑校验（在 Pydantic 验证后、DSL 转换前）
        # 单组件调试时跳过全局校验，只验证被调试组件即可
        if not skip_validation:
            validate_canvas_nodes(canvas)

        # 3. DSL 转换
        nodes = canvas.nodes
        components = component_convert(canvas.edges, nodes, workflow_info.space_id, False)

        input_properties, input_requires = convert_to_properties_format(workflow_info.input_parameters)
        inputs = {
            "type": "object",
            "properties": input_properties,
            "required": input_requires
        }
        output_properties, output_requires = convert_to_properties_format(workflow_info.output_parameters)

        start_id: List[str] = []
        end_id: List[str] = []
        for component in components:
            if component.type == ComponentType.COMPONENT_TYPE_START:
                start_id.append(component.id)
            elif component.type == ComponentType.COMPONENT_TYPE_END:
                end_id.append(component.id)

        edges = canvas.edges
        connections = connection_convert(edges)

        version = getattr(workflow_info, "workflow_version", "1.0.0")

        workflow = dsl.Workflow(
            inputs=inputs,
            outputs=output_properties,
            start_id=start_id,
            end_id=end_id,
            id=getattr(workflow_info, "workflow_id", ""),
            name=getattr(workflow_info, "name", "Unnamed Workflow"),
            version=version,
            description=getattr(workflow_info, "desc", ""),
            components=components,
            connections=connections
        )

        return workflow
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        raise ValueError(f"Invalid workflow schema or input: {str(e)}") from e
