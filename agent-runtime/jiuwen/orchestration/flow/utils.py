#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
"""
Contains a collection of utility functions
"""

import copy
import inspect
import json
import os
import re
import uuid
from collections import namedtuple
from typing import Generator, Union, Any, List, AsyncIterable, AsyncGenerator

import yaml
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.orchestration.flow.base_workflow import Node
from jiuwen.orchestration.flow.components.util import (
    format_pydantic_validation_error_message,
    OUTPUTS,
    ANSWER,
)
from jiuwen.orchestration.flow.constant import (
    SCHEMA_VALIDATION_WRONG_TYPE,
    SCHEMA_TYPE_NOT_SUPPORTED,
    SCHEMA_IN_WRONG_FORMAT,
    USER_FIELDS,
    STRUCTURE_POSITION_INPUTS,
    SYSTEM_FIELDS,
    STRING,
    INTEGER,
    NUMBER,
    BOOLEAN,
    OBJECT,
    ARRAY,
    SCHEMA,
    SIMPLE_TYPE_DICT,
    TYPE_DEFAULT_VALUE_DICT,
    ERROR,
    CONSTANT_ARRAY_LOOP_VAR,
    CONSTANT_NUM_LOOP_VAR,
)
from jiuwen.orchestration.flow.enum import NodeType, LoopType, WorkflowLLMResponseType
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.model.workflow_ir_validation import WorkflowIr
from jiuwen.orchestration.flow.stream.base import StreamCode, StreamData
from jiuwen.orchestration.flow.stream.workflow_streaming import WorkflowStreamCallback
from jiuwen.extension.workflow_node.utils import JiuWenBaseException as OpenjiuwenJiuWenBaseException
from lxml import etree
from pydantic import ValidationError

_ANSWER = "answer"
EMPTY_TYPE = "empty_type"

BPMN_MAP = {
    NodeType.BRANCH.value: "exclusiveGateway",
    NodeType.INTENT_DETECTION.value: "exclusiveGateway",
    NodeType.LOOP.value: "subProcess",
}

BPMN2 = "bpmn2"
WORKFLOW = "workflow"
XSI = "xsi"
BPMNDI = "bpmndi"
DC = "dc"
TYPE = "type"


def get_flow_config():
    """Get flow config."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flow_config.yaml")
    with open(path, encoding="utf-8") as file:
        # 加载配置文件
        flow_config = yaml.safe_load(file)
    return flow_config


config = get_flow_config()
default_nsmap = {
    BPMN2: config[WORKFLOW][BPMN2],
    BPMNDI: config[WORKFLOW][BPMNDI],
    DC: config[WORKFLOW][DC],
    XSI: config[WORKFLOW][XSI],
}


async def pre_process_inputs(inputs):
    """对于inputs中值为生成器类型的元素，遍历生成器获取最终结果，并更新原inputs"""
    if isinstance(inputs, dict):
        for key, value in inputs.items():
            inputs[key] = await pre_process_inputs(value)
    if isinstance(inputs, Generator):
        return get_final_result_of_flow_generator(inputs)
    if isinstance(inputs, AsyncGenerator):
        return await get_final_result_of_flow_async_generator(inputs)
    return inputs


def dict_with_generators_replaced(inputs: dict):
    """
    替换inputs中的生成器类型的值，并返回一个新的dict。
    :param inputs: 原始输入
    :return res: 不包含生成器类型值的新dict。
    """
    res = {}
    if isinstance(inputs, dict):
        for key, value in inputs.items():
            if isinstance(value, (Generator, AsyncGenerator)):
                res[key] = ""
            elif isinstance(value, dict):
                res[key] = dict_with_generators_replaced(value)
            else:
                res[key] = value
    return res


def get_final_result_of_llm_generator_json(origin_generator: Generator, key: str):
    """
    遍历生成器，修改 item.data 后返回新的生成器。
    用于需要动态修改生成器内容但保持生成器特性的场景。
    """
    for item in origin_generator:
        if isinstance(item, StreamData):
            outputs = item.data.get(OUTPUTS, {}).get(USER_FIELDS)
            new_answer = item.data.get(ANSWER, {}).get(key)
            new_data = dict(
                answer=new_answer,
                node_id=item.data.get("node_id"),
                node_name=item.data.get("node_name"),
                node_type=item.data.get("node_type"),
            ) | ({OUTPUTS: {USER_FIELDS: outputs}} if outputs else {})
            item.data = new_data
        yield item


def get_final_result_of_flow_generator(origin_generator: Generator):
    """
    遍历生成器，获取生成器执行结果。
    使用于无法解析流式输出，只能解析完整输出的组件遇到生成器输入的时候。
    """
    final_res = ""
    for item in origin_generator:
        if isinstance(item, str):
            final_res += item
        elif item.code == StreamCode.PARTIAL_CONTENT.value:
            if isinstance(item.data, dict):
                final_res += item.data.get(_ANSWER, "")
            else:
                final_res += str(item.data)
        elif item.code in [StreamCode.FINISH.value, StreamCode.ERROR.value]:
            break
    return final_res


async def get_final_result_of_flow_async_generator(origin_generator: AsyncGenerator):
    """get_final_result_of_async_generator"""
    final_res = ""
    async for item in origin_generator:
        if isinstance(item, str):
            final_res += item
        elif item.code == StreamCode.PARTIAL_CONTENT.value:
            if isinstance(item.data, dict):
                final_res += str(item.data.get(_ANSWER, ""))
            else:
                final_res += str(item.data)
        elif item.code in [StreamCode.FINISH.value, StreamCode.ERROR.value]:
            break
    return final_res


def is_model_output_json(node: Node) -> bool:
    """判断模型输出是否是Json格式"""
    if node.type == NodeType.LLM.value:
        return (
            node.configs.get("responseFormat", {}).get("type")
            == WorkflowLLMResponseType.JSON.value
        )
    return False


def validate_workflow_json(workflow_json: dict):
    """校验workflow ir"""
    try:
        WorkflowIr.model_validate(workflow_json)
    except ValidationError as e:
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.code,
            message=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.errmsg.format(
                reason=format_pydantic_validation_error_message(e)
            ),
        ) from e


def get_streaming_finish_stream_data(
    execution_id: str, node: Node, answer: str = "", user_fields: dict = None
):
    """构造一个只包含结束标识的流式数据，用于标识流式执行结束"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data=dict(
            answer=answer, node_id=node.id, user_fields=user_fields, node_type=node.type
        ),
        execution_id=execution_id,
    )


def get_streaming_single_component_stream_data(
    execution_id: str, answer: str = "", component_type: str = ""
):
    """构造单组件调试结束标识的流式数据，用于标识执行结束"""
    return StreamData(
        code=StreamCode.FINISH.value,
        msg=StreamDataMsg.FINISH.value,
        data=dict(answer=answer, node_type=component_type),
        execution_id=execution_id,
    )


async def send_stream_data_by_stream_callback(
    stream_callback: WorkflowStreamCallback, item: StreamData
):
    """借助stream_callback发送一条流式数据"""
    if stream_callback:
        await stream_callback.on_recv(item)


def force_convert(inputs: dict, inputs_definition: Union[list, dict]) -> (dict, list):
    """
    Force convert the inputs to match the inputs_definition.
    Returns the converted value and convert errors.
    """

    # 递归转换函数
    def _convert(data: Any, definition: dict, param_path: str = ""):
        # definition包括 id, type, schema，其中三个值均非必填
        # 1. 基础类型：使用definition中定义的类型做强转后直接return
        # 2. object：取schema，是list of definition: 把每一个definition和他的真实值放convert
        #   在外层定义res, res[expected_id] = _convert()，最终return res
        # 3. array：取schema，就是definition: enumerate array，对其中每个元素调用convert
        #   在外层定义res[None * len()], res[index] = _convert()，最终return res

        expected_type = definition.get("type", EMPTY_TYPE).lower()
        expected_key = definition.get("id", "")

        if expected_type == EMPTY_TYPE:
            # 如果未申明类型，则不做校验和强转
            return data

        current_path = f"{param_path}.{expected_key}".strip(".")

        # 做类型强转，转不成功会报错
        if expected_type == OBJECT:
            return _convert_object(data, definition, current_path)
        if expected_type == ARRAY:
            return _convert_array(data, definition, current_path)
        if expected_type in [STRING, INTEGER, NUMBER, BOOLEAN]:
            return _convert_simple(data, expected_type, current_path)
        if expected_type == "null":
            # null 类型：接受 None、空字符串，其他值原样返回
            if data is None or data == "":
                return None
            return data
        if "|" in expected_type:
            return _convert_one_of_type(data, expected_type, current_path, definition)

        # 不支持的其他类型
        res = None
        errors.append(SCHEMA_TYPE_NOT_SUPPORTED.format(k=current_path, t=expected_type))
        return res

    def _convert_one_of_type(data, expected_type, current_path, definition):
        """Oneof类型参数转换"""
        expected_types = [t.strip() for t in expected_type.split("|")]
        for sub_expected_type in expected_types:
            if sub_expected_type == OBJECT:
                try:
                    result = _convert_object(data, definition, current_path)
                    # oneOf schema 可能包含无法解析的子 schema（如嵌套的 oneOf 列表），
                    # 导致 _convert_object 返回非 dict 值（如原始字符串）。
                    # 此时应视为 object 转换失败，继续尝试下一个类型。
                    if isinstance(result, dict):
                        return result
                except JiuWenBaseException:
                    pass
                continue
            if sub_expected_type == ARRAY:
                try:
                    result = _convert_array(data, definition, current_path)
                    if isinstance(result, list):
                        return result
                except JiuWenBaseException:
                    pass
                continue
            if sub_expected_type in [STRING, INTEGER, NUMBER, BOOLEAN]:
                try:
                    return _convert_simple(data, sub_expected_type, current_path)
                except JiuWenBaseException:
                    continue
            if sub_expected_type == "null":
                if data is None or data == "":
                    return None
                # 数据非空，尝试其他类型
                continue
        return None

    def _convert_object(inputs, definition, current_path):
        object_schema = definition.get(SCHEMA)

        if not object_schema:
            return inputs

        if not isinstance(object_schema, list):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.code,
                message=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.errmsg.format(
                    reason=f"key: {current_path} is of object type and should have schema"
                ),
            )

        # 尝试转换object
        if inputs is None:
            return TYPE_DEFAULT_VALUE_DICT.get(OBJECT)
        if isinstance(inputs, str):
            try:
                converted_value = json.loads(inputs)
            except (ValueError, TypeError):
                errors.append(
                    SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=OBJECT)
                )
                return TYPE_DEFAULT_VALUE_DICT.get(ERROR)
            if not isinstance(converted_value, dict):
                errors.append(
                    SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=OBJECT)
                )
                return TYPE_DEFAULT_VALUE_DICT.get(ERROR)
        elif isinstance(inputs, dict):
            converted_value = inputs
        elif isinstance(inputs, (Generator, AsyncGenerator)):
            converted_value = inputs
            return converted_value
        else:
            errors.append(SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=OBJECT))
            return TYPE_DEFAULT_VALUE_DICT.get(ERROR)

        # 遍历转换object中的每一个属性及其definition，递归调用_convert()，并将结果存在res中
        # 防御性处理：oneOf/anyOf 类型（如 object|null）的 schema 中可能包含：
        # 1. 非 dict 项（如嵌套的 oneOf 子 schema 列表）→ 跳过
        # 2. dict 项但没有 "id" 字段（如 {"type": "null"}）→ 也要跳过
        #    否则 attr_key 会变成空字符串 ""，产生 {"": None} 这样的脏数据
        converted_object = {}
        for attr_definition in object_schema:
            if not isinstance(attr_definition, dict):
                continue
            if "id" not in attr_definition:
                continue
            attr_key = attr_definition["id"]
            attr_value = converted_value.get(attr_key)
            converted_object[attr_key] = _convert(
                attr_value, attr_definition, current_path
            )
        # 如果 schema 中没有任何可解析的属性定义（全是 oneOf 子 schema 之类），
        # 直接返回原始输入，不做子属性转换
        if not converted_object and object_schema:
            return converted_value
        return converted_object

    def _convert_array(inputs, definition, current_path):
        # array类型的参数必须定义schema，且schema是一个list，就是其中每一个元素的definition
        if isinstance(inputs, Generator):
            return inputs
        array_schema = definition.get(SCHEMA)
        if not isinstance(array_schema, dict):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.code,
                message=StatusCode.WORKFLOW_IR_VALIDATION_ERROR.errmsg.format(
                    reason=f"key: {current_path} is of array type and should have schema"
                ),
            )
        element_definition = array_schema

        # 尝试转换array
        if inputs is None:
            return TYPE_DEFAULT_VALUE_DICT.get(ARRAY)
        if isinstance(inputs, str):
            try:
                converted_value = json.loads(inputs)
            except (ValueError, TypeError):
                errors.append(
                    SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=ARRAY)
                )
                return TYPE_DEFAULT_VALUE_DICT.get(ERROR)
            if not isinstance(converted_value, list):
                errors.append(
                    SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=ARRAY)
                )
                return TYPE_DEFAULT_VALUE_DICT.get(ERROR)
        elif isinstance(inputs, list):
            converted_value = inputs
        else:
            errors.append(SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=ARRAY))
            return TYPE_DEFAULT_VALUE_DICT.get(ERROR)

        # 使用同一个definition循环转换array中的每个元素
        converted_array = [None] * len(converted_value)
        for index, element in enumerate(converted_value):
            converted_array[index] = _convert(
                element, element_definition, f"{current_path}[{index}]"
            )
        return converted_array

    def _convert_simple(actual_value, expected_type, current_path):
        # 流式的数据（expected_type为string）最后会被当作字符串处理，不做强转
        condition = (
            isinstance(actual_value, (Generator, AsyncGenerator, AsyncIterable))
            or inspect.isasyncgen(actual_value)
            or hasattr(actual_value, "__aiter__")
        )
        if condition:
            return actual_value
        if actual_value is None:
            return TYPE_DEFAULT_VALUE_DICT.get(expected_type)
        convert_action = SIMPLE_TYPE_DICT.get(expected_type, str)
        res = None
        # bool类型是一种特殊的int，需要额外做判断，确保其被强转
        if not isinstance(actual_value, convert_action) or (
            isinstance(actual_value, bool) and expected_type == INTEGER
        ):
            try:
                return convert_action(actual_value)
            except (ValueError, TypeError):
                errors.append(
                    SCHEMA_VALIDATION_WRONG_TYPE.format(k=current_path, t=expected_type)
                )
                return res
        return actual_value

    # 用来接收错误信息
    errors = []
    converted_value = {}
    if inputs_definition is None:
        # 兼容老IR：一般是引用前序节点输出值，没有任何schema定义（没有id，没有type，没有schema），不做校验和强转，直接返回原值
        converted_value = inputs
    elif isinstance(inputs_definition, list):
        for definition in inputs_definition:
            root = definition.get("id", "")
            if root not in inputs:
                continue
            data = inputs.get(root)
            converted_value[root] = _convert(data, definition, "")
    elif isinstance(inputs_definition, dict):
        root = inputs_definition.get("id", "")
        if root in inputs:
            data = inputs.get(root)
            converted_value[root] = _convert(data, inputs_definition, "")
    else:
        errors.append(SCHEMA_IN_WRONG_FORMAT.format(k=""))
    return converted_value, errors


def force_convert_component_by_schema_raise_openjiuwen_exception(
        inputs, node_configs, node_info: WorkflowMetadata, structure_pos: str = STRUCTURE_POSITION_INPUTS):
    """对 openjiuwen 工作流回调中的输入/输出值做类型强转，强转失败时抛出
    OpenjiuwenJiuWenBaseException（继承 ExecutionError → BaseError），
    使 openjiuwen 图引擎将其作为 BaseError 直接 re-raise。

    封装 force_convert_component_by_schema_raise_exception（整体替换语义），
    仅将异常类型从 JiuWenBaseException 转换为 OpenjiuwenJiuWenBaseException。

    对齐老版本逻辑：先整体替换 userFields，再对 End/Message 节点恢复 #end_ 前缀字段
    （老版本在 set_end_invoke_output 中强转后增量添加 #end_ 字段）。

    仅在 openjiuwen 工作流回调（BATCH_INPUT/BATCH_OUTPUT）中使用此函数。
    """
    # 强转前暂存 #end_ 前缀字段（整体替换后会丢失）
    original_uf = inputs.get(USER_FIELDS, {})
    end_fields = {k: v for k, v in original_uf.items() if k.startswith("#end_")}

    try:
        converted = force_convert_component_by_schema_raise_exception(
            inputs=inputs,
            node_configs=node_configs,
            node_info=node_info,
            structure_pos=structure_pos,
        )
    except JiuWenBaseException as e:
        raise OpenjiuwenJiuWenBaseException(
            error_code=e.error_code,
            message=e.message,
            node_id=e.node_id,
            node_name=e.node_name,
            node_type=e.node_type,
        ) from e

    # 强转后恢复 #end_ 前缀字段（对齐老版本 set_end_invoke_output）
    if end_fields:
        converted.setdefault(USER_FIELDS, {}).update(end_fields)

    return converted


def force_convert_component_by_schema_raise_exception(
    inputs,
    node_configs,
    node_info: WorkflowMetadata,
    structure_pos: str = STRUCTURE_POSITION_INPUTS,
):
    """
    校验 cur_invokable_node_inputs 是否符合其类型定义
    """
    try:
        user_converted_value, user_validation_errors = force_convert(
            inputs.get(USER_FIELDS, {}),
            node_configs.get(USER_FIELDS, {}).get(structure_pos),
        )
        sys_converted_value, sys_validation_errors = force_convert(
            inputs.get(SYSTEM_FIELDS, {}),
            node_configs.get(SYSTEM_FIELDS, {}).get(structure_pos),
        )
    except JiuWenBaseException as e:
        raise JiuWenBaseException(
            error_code=e.error_code, message=e.message + f" in {node_info.node_name}"
        ) from e

    all_converted_value = inputs
    all_converted_value.update(
        {USER_FIELDS: user_converted_value, SYSTEM_FIELDS: sys_converted_value}
    )

    all_errors = {
        USER_FIELDS: user_validation_errors,
        SYSTEM_FIELDS: sys_validation_errors,
    }

    if all_errors.get(USER_FIELDS) or all_errors.get(SYSTEM_FIELDS):
        raise JiuWenBaseException(
            error_code=StatusCode.WORKFLOW_COMPONENT_EXECUTE_ERROR.code,
            message=StatusCode.WORKFLOW_COMPONENT_EXECUTE_ERROR.errmsg.format(
                node_info.node_name,
                f"the {structure_pos} structure of the components does not match its definition in the IR: "
                f"{all_errors}",
            ),
        )
    return all_converted_value


def verify_the_security_of_variables_for_spiffworkflow(str_list: List[str]):
    """
    Verify the security of variables used for spiffworkflow eval calculations.
    @param str_list: Every str is only allowed to contain numbers, letters, _, ', ", [, ], -
    """
    safe_pattern = r"^[0-9A-Za-z_\-\u4e00-\u9fa5\[\]\"']+$"
    for variable_name in str_list:
        if not re.fullmatch(safe_pattern, variable_name):
            raise JiuWenBaseException(
                error_code=StatusCode.WORKFLOW_INVALID_ID_ERROR.code,
                message=StatusCode.WORKFLOW_INVALID_ID_ERROR.errmsg,
            )


class NodeFromIR:
    """方便从 IR 中读取/使用节点"""

    def __init__(self, node_config: dict):
        self.node_id = node_config["id"]
        self.node_type = node_config["type"]
        self.node_config = node_config
        self._get_inside_subprocess_nodes()

    @staticmethod
    def create_node_id(prefix: str = "node_"):
        """
        生成一个 node_id / task_id
        """
        return prefix + str(uuid.uuid4())

    def _get_inside_subprocess_nodes(self):
        if self.node_type == NodeType.LOOP.value:
            nodes_inside = self.node_config["configs"]["loopBody"]
            self.nodes_inside = nodes_inside
        else:
            self.nodes_inside = None


ParallelBranchIdTuple = namedtuple("ParallelBranchIdTuple", "from_src from_tgt")


class EdgeFromIR:
    """方便从 IR 中读取/使用边"""

    def __init__(self, edge_config: dict, source: str = None, target: str = None):
        self.source = (
            source if source else edge_config.get("source", {}).get("componentId")
        )
        self.target = (
            target if target else edge_config.get("target", {}).get("componentId")
        )
        self.edge_id = self.create_edge_id()

        self.non_para_id = edge_config.get("source", {}).get("branchId")  # 非并行分支
        self.condition = None

        self.para_id_tuple = self.get_parallel_branch_id(edge_config)

    @staticmethod
    def create_edge_id():
        """
        生成一个 edge id
        """
        return "edge" + str(uuid.uuid4())

    @staticmethod
    def get_parallel_branch_id(edge_config: dict) -> ParallelBranchIdTuple:
        """
        读取并行分支: parallelBranchId
        """
        para_id_from_src = edge_config.get("source", {}).get("parallelBranchId")
        para_id_from_tgt = edge_config.get("target", {}).get("parallelBranchId")
        return ParallelBranchIdTuple(para_id_from_src, para_id_from_tgt)

    @staticmethod
    def normalize_id(id_str):
        """
        将 id_str 转换为符合 bpmn 元素名称要求的格式。
        """
        return id_str.replace("-", "_")

    @staticmethod
    def get_source_id(edge_config: dict):
        """
        获取sourceId
        """
        return edge_config.get("source", {}).get("componentId")

    @staticmethod
    def get_target_id(edge_config: dict):
        """
        获取targetId
        """
        return edge_config.get("target", {}).get("componentId")

    def insert_node(self, node_id: str) -> tuple:
        """
        插入一个节点，变成两条相连的边。返回元组： (source所在边, target所在边)

        node_id 保留给 source 所在的那一边，target 所在一遍使用新的 node_id.
        即：保持 source 跟 edge_id 绑定不动。
        """
        new_edge = copy.deepcopy(self)
        self.target = node_id
        new_edge.source = node_id
        new_edge.edge_id = EdgeFromIR.create_edge_id()
        return self, new_edge


class GateFromIR:
    """记录网关的重要信息"""

    def __init__(self, gate_id: str):
        self.gate_id = gate_id
        self.incoming = set()
        self.outgoing = set()
        self.default = None  # 仅排他网关需要


class ProcessFromIR:
    """
    所有流程，包括（嵌套）子流程，如 Loop 内等。
    """

    def __init__(
        self,
        process_id: str,
        start_event: str,
        end_event: str,
        components: list[str] = None,
    ):
        self.process_id = process_id
        self.components = set(components) if components else set()  # node_id
        self.connections = set()  # edge_id
        self.xor_gates = set()
        self.and_gates = set()
        self.or_gates = set()
        self.start_event = start_event
        self.end_event = end_event

        self._adjacency = {}  # {src_node_id: {tgt_node_id, }}

    def index_adjacency(self, edge_src: str, edge_tgt: str):
        """
        将邻接边加入索引：从 source 索引所有可能的 target.
        """
        if edge_src in self._adjacency:
            self._adjacency[edge_src].add(edge_tgt)
        else:
            self._adjacency[edge_src] = {
                edge_tgt,
            }

    def node_cluster_from_start_to_end(
        self, start: str = None, end: str = None
    ) -> set[str]:
        """
        从 start_event 到 end_event 的图，不包含游离节点（子图）。

        返回：set(node_id)
        """
        start = self.start_event if start is None else start
        end = self.end_event if end is None else end

        cluster: set[str] = set()
        bfs_nodes: set[str] = {
            start,
        }
        while bfs_nodes:
            cluster.update(bfs_nodes)
            next_bfs_nodes = set()
            for item_ in bfs_nodes:
                if item_ == end:
                    continue
                next_bfs_nodes.update(
                    {
                        item_tgt
                        for item_tgt in self._adjacency.get(item_, {})
                        if item_tgt not in cluster
                    }
                )
            bfs_nodes = next_bfs_nodes
        return cluster


class Json2BpmnXmlParser:
    """
    IR 转 BPMNWorkflow xml：
    所有流程 (包含 SubProcess) 均支持循环、并行。

    对循环组件：
    - 生成一个 subProcess
    - 前面插入一个 exclusiveGateway, 不满足循环进入条件则跳过循环（BPMN 的循环是 do_while, 进入后至少执行一次）。

    对并行：
    - 并行开始的节点后，插入一个 parallelGateway.
    - 并行结束的节点（实际为含有并行的工作流，分支汇聚节点）前面，插入一个 inclusiveGateway;
        并在 inclusiveGateway 前（各个入边都）插入一个空 task, 保证并行执行时 inclusiveGateway 确在当执行任务完成后再触发
        （避免非串行执行时， task 为 Started 时可能尚未执行完毕，但 inclusiveGateway 已满足触发条件，导致重复触发）。

    对非并行分支（判断、意图识别等）：
    — 分支节点本身使用 exclusiveGateway;
    - 如工作流整体无并行，则分支收束处，无需加网关。
    """

    root_id = "root"
    root_process_id = "process_node"
    node_types_as_xor_gate = {
        NodeType.BRANCH.value,
        NodeType.INTENT_DETECTION.value,
    }  # 对应 exclusiveGateway 的外部节点
    node_types_as_sub_process = {
        NodeType.LOOP.value,
    }  # 对应 subProcess 的外部节点

    def __init__(
        self,
        workflow_json: dict,
        binding_node_maker: callable,
        get_condition_of_branch: callable,
    ):
        self.xml_nodes: dict[str, etree.Element] = {}  # node_id: etree.Element
        self.all_processes: dict[str, ProcessFromIR] = {}  # process_id: ProcessFromIR
        self.all_nodes: dict[str, NodeFromIR] = {}  # node_id: NodeFromIR
        self.nodes_ignored: dict[str, NodeFromIR] = {}  # 被删除的游离节点
        self.all_edges: dict[str, EdgeFromIR] = {}  # edge_id: EdgeFromIR
        self.all_xor_gates: dict[str, GateFromIR] = {}  # gate_id: GateFromIR
        self.all_and_gates: dict[str, GateFromIR] = {}
        self.all_or_gates: dict[str, GateFromIR] = {}

        # 对 node_config, 实例化一个外部节点的方法，入参：node_config
        self.binding_node_maker: callable = binding_node_maker
        # 分支节点根据 node_id 与 branch_id 获取条件的方法，入参：(node_id, branchId)
        self.get_condition_of_branch: callable = get_condition_of_branch

        self._pre_process(workflow_json)

    @staticmethod
    def loop2gate_before(loop_id: str):
        """
        Loop 前排他网关命名
        """
        return f"xor_gate_before_{loop_id}"

    @staticmethod
    def loop_gate_condition(node: NodeFromIR):
        """按循环类型，生成进入循环的条件"""
        loop_config = node.node_config["configs"]
        if loop_config["loopType"] == LoopType.ARRAY.value:
            return f"( len({node.node_id}['{CONSTANT_ARRAY_LOOP_VAR}']) > 0) and not {node.node_id}['is_break']"
        if loop_config["loopType"] == LoopType.NUMBER.value:
            return f"( {node.node_id}['{CONSTANT_NUM_LOOP_VAR}'] > 0) and not {node.node_id}['is_break']"
        return "False"

    @staticmethod
    def loop_end_condition(node: NodeFromIR):
        """按循环类型，生成退出循环的条件"""
        loop_config = node.node_config["configs"]
        if loop_config["loopType"] == LoopType.ARRAY.value:
            return f"( {node.node_id}['index'] >= {node.node_id}['loop_nums']) or {node.node_id}['is_break']"
        if loop_config["loopType"] == LoopType.NUMBER.value:
            return (
                f"( {node.node_id}['index'] >= {node.node_id}['{CONSTANT_NUM_LOOP_VAR}']) or"
                f" {node.node_id}['is_break']"
            )
        return "True"

    @staticmethod
    def twin_xor_gate_for_intent_node(node_id: str):
        """意图节点会伴生一个排他网关作分支"""
        return f"{node_id}_llm"

    @staticmethod
    def is_need_empty_task_before_or_gate():
        """
        inclusiveGateway 通过的条件是所有入边节点的状态都已 Started, 而非 Completed.

        若并行执行，inclusiveGateway 前入边最好都加一个空的 task (空的 task 都阻塞执行),
        确保 inclusiveGateway 触发时该执行的都已执行完毕。
        """
        return True

    @staticmethod
    def is_ir_need_reduce(workflow_json: dict):
        """
        是否需要删除 IR 中游离节点/集团：
        + 若为单节点调试，则不需要；
        + 其它情形，需要。
        """
        if Json2BpmnXmlParser.is_single_component_ir(workflow_json):
            return False
        return True

    @staticmethod
    def is_single_component_ir(workflow_json: dict):
        """
        是否单节点调试生成的 IR：components 只有一个元素、connections 中无元素。
        """
        return len(workflow_json["components"]) == 1

    def parsed(self, process: ProcessFromIR = None) -> etree.Element:
        """
        解析并返回 process 对应根节点。

        若 process 未提供，则返回当前 IR 最外层流程根节点。
        """
        if process is None:  # 最外层
            self._init_xml_root_node()
            process = self.all_processes[self.root_process_id]

        process_node = self.xml_nodes.get(process.process_id)
        for node_id in process.components:
            self._create_xml_node(node_id, process_node)
            if node_id in self.all_processes:  # 嵌套子流程，如 Loop 节点
                try:
                    self.parsed(process=self.all_processes[node_id])
                except Exception as e:
                    logger.error("Failed to parse sub_process (%s).", node_id)
                    raise e

        for gate_id in process.xor_gates:
            self._create_xml_xor_gate(gate_id, process_node)
        for gate_id in process.and_gates:
            self._create_xml_and_or_gate(gate_id, process_node, is_and_gate=True)
        for gate_id in process.or_gates:
            self._create_xml_and_or_gate(gate_id, process_node, is_and_gate=False)

        for edge_id in process.connections:
            self._create_xml_edge(edge_id, process_node)

        return self.xml_nodes[self.root_id]

    def _pre_process(self, workflow_json: dict):
        """
        遍历 components 与 connections, 完成：
        + 生成所有 node 配置的索引：self.all_nodes = {node_id: NodeFromIR}
        + 遍历 connections, 补充该加的 task 或 gate, 生成边的 id，生成索引: self.edges_config = {edge_id: EdgeFromIR}
        + 识别所有 Process，包括 Subprocess: self.all_processes = {"process_node": main_process,
                                                                    "node_loop": loop_process, }
        + 索引所有的网关：
            - exclusiveGateway: self.xor_gates = {gate_id: GateFromIR}
            - parallelGateway: self.and_gates,
            - inclusiveGateway: self.or_gates
        """
        root_process = ProcessFromIR(
            self.root_process_id, start_event="start", end_event="end"
        )
        self.all_processes[self.root_process_id] = root_process

        node_belongings: dict[str, ProcessFromIR] = {}  # node_id: ProcessFromIR
        for node_config in workflow_json.get("components"):
            node = NodeFromIR(node_config)
            self.all_nodes[node.node_id] = node

            if node.node_type in self.node_types_as_sub_process:  # 节点对应子流程
                sub_process = ProcessFromIR(
                    node.node_id,
                    start_event=f"{node.node_id}_input",
                    end_event=f"{node.node_id}_output",
                    components=node.nodes_inside,
                )
                self.all_processes[node.node_id] = sub_process
                node_belongings.update(
                    {item: sub_process for item in node.nodes_inside}
                )

        # 最外层流程节点
        nodes_of_root = set(self.all_nodes.keys()) - set(node_belongings.keys())
        self.all_processes[self.root_process_id].components = nodes_of_root
        node_belongings.update({item: root_process for item in nodes_of_root})
        if Json2BpmnXmlParser.is_ir_need_reduce(workflow_json):
            self._remove_trivial_nodes_and_sub_graphs(workflow_json, node_belongings)

        for node in self.all_nodes.values():  # 外部节点实例化
            self.binding_node_maker(node.node_config)

        self._pre_process_edges(workflow_json, node_belongings)

    def _remove_trivial_nodes_and_sub_graphs(
        self, workflow_json: dict, node_belongings: dict
    ):
        """
        删除游离节点/子图
        """
        for edge_config in workflow_json.get("connections"):
            edge_src, edge_tgt = (
                EdgeFromIR.get_source_id(edge_config),
                EdgeFromIR.get_target_id(edge_config),
            )
            from_process: ProcessFromIR = node_belongings.get(
                edge_src
            ) or node_belongings.get(edge_tgt)
            from_process.index_adjacency(edge_src, edge_tgt)

        for process in self.all_processes.values():
            start, end = (
                ("node_start", "node_end")
                if process.process_id == self.root_process_id
                else (None, None)
            )
            nontrivial_nodes = process.node_cluster_from_start_to_end(
                start=start, end=end
            )
            for node_id in process.components - nontrivial_nodes:
                self.nodes_ignored[node_id] = self.all_nodes.pop(
                    node_id
                )  # 删除游离节点，备份记入 self.nodes_ignored
                node_belongings.pop(node_id)
            process.components = nontrivial_nodes.intersection(process.components)

    def _pre_process_edges(self, workflow_json: dict, node_belongings: dict):
        """
        提前处理边：
        + 加并行网关
        + 加包容网关
        + 加排他网关（如 Loop 节点前）
        """
        next_if_skip: dict[str, str] = {}  # 索引下一个节点，以需前置排他网关者为 key
        xor_gates_to_complete: list[
            GateFromIR
        ] = []  # 插入的排他网关，需要补充 default 或其它边的条件

        added_or_gates_outgoing = {}  # gate_id: num, num = 0 表示待添加，>= 1 则表示已添加
        for edge_config in workflow_json.get("connections"):
            # 忽略游离节点/子图的边
            if not (
                EdgeFromIR.get_source_id(edge_config) in self.all_nodes
                or EdgeFromIR.get_target_id(edge_config) in self.all_nodes
            ):
                continue

            edge = EdgeFromIR(edge_config)  # source --> target
            original_edge = edge
            from_process: ProcessFromIR = node_belongings.get(
                edge.source
            ) or node_belongings.get(edge.target)

            if edge.non_para_id:  # 分支节点对应排他网关
                self._pre_process_node_as_xor_gate(edge, from_process)

            if edge.para_id_tuple.from_src:  # 并行开始网关
                edge = self._post_add_parallel_gateway(
                    edge, from_process
                )  # and_gate --> target

            if (
                edge.para_id_tuple.from_tgt
            ):  # 收束都用 inclusiveGate，可以与非并行分支混用
                edge = self._pre_add_inclusive_gateway(
                    edge, from_process
                )  # or_gate --> target
                added_or_gates_outgoing[edge.source] = (
                    added_or_gates_outgoing.get(edge.source, -1) + 1
                )

            if (
                edge.target in self.all_nodes
                and self.all_nodes[edge.target].node_type == NodeType.LOOP.value
            ):
                # 进入循环前先判断（循环 subProcess 实为 do-while）
                # 循环前的排他网关只需加一次，注意两种情况：
                # 1. Loop 前是并行，到此处 edge.source 必为 or_gate，无需重复处理
                # 2. Loop 前有非并行的多条边（即在外部连线构成的循环开头），加一次 xor_gate，后续只需将 target 置为 xor_gate
                if self.loop2gate_before(edge.target) not in self.all_xor_gates:
                    edge, _gate = self._pre_add_exclusive_gateway(edge, from_process)
                    xor_gates_to_complete.append(_gate)  # 待补充 default
                    edge.condition = self.loop_gate_condition(
                        self.all_nodes[edge.target]
                    )  # 进入循环的条件
                elif edge.source not in self.all_xor_gates:  # 有非并行的多条边
                    edge.target = self.loop2gate_before(edge.target)

            # 额外网关/节点插入完毕
            if (
                added_or_gates_outgoing.get(edge.source, -1) < 1
            ):  # 包容网关的出边只有一个
                self.all_edges[edge.edge_id] = edge
                from_process.connections.add(edge.edge_id)
            if (
                original_edge.source not in next_if_skip
                and self._is_edge_source_from_loop(original_edge)
            ):  # 循环节点的下一个节点，为前置排他网关的默认方向
                next_if_skip[original_edge.source] = original_edge.target

        # 补充循环前排他网关的 default
        self._determine_default_edge_before_loop(
            xor_gates_to_complete, next_if_skip, node_belongings
        )

    def _is_edge_source_from_loop(self, edge: EdgeFromIR) -> bool:
        """
        判断 source 是否 Loop
        """
        if (
            edge.source in self.all_nodes
            and self.all_nodes[edge.source].node_type == NodeType.LOOP.value
        ):
            return True
        return False

    def _add_empty_task_between_loop_and_gate(
        self, edge: EdgeFromIR, from_process: ProcessFromIR
    ) -> EdgeFromIR:
        """
        Loop 之后不能直接加 and_gate, 需加一个空 task 代替 and_gate（作为默认边）连接 Loop 前置 xor_gate.
        """
        edge_0, edge = edge.insert_node(
            f"empty_task_between_{edge.source}_and_following_gate"
        )
        self.all_edges[edge_0.edge_id] = edge_0
        from_process.components.add(edge_0.target)
        from_process.connections.add(edge_0.edge_id)
        return edge

    def _pre_process_node_as_xor_gate(
        self, edge: EdgeFromIR, from_process: ProcessFromIR
    ):
        """
        处理对应排他网关的节点（意图节点、判断节点等）
        """
        if edge.source in self.all_xor_gates:
            gate_node = self.all_xor_gates[edge.source]
        else:
            gate_node = GateFromIR(edge.source)
            self.all_xor_gates[edge.source] = gate_node
        if (
            gate_node.gate_id in from_process.components
        ):  # 从 components 中移到 xor_gates 中
            from_process.components.remove(gate_node.gate_id)
            from_process.xor_gates.add(gate_node.gate_id)
        if (
            "default" in edge.non_para_id and not gate_node.default
        ):  # default 后面也可能跟并行
            gate_node.default = edge.edge_id
        else:
            try:
                # 此处可能因为 IR 问题报错（例如：判断节点缺父节点），补充报错细节以便定位
                edge.condition = self.get_condition_of_branch(
                    gate_node.gate_id, edge.non_para_id
                )
            except Exception as e:
                node_name = (
                    "Unknown"
                    if gate_node.gate_id not in self.nodes_ignored
                    else self.nodes_ignored[gate_node.gate_id].node_config.get("name")
                )
                raise ValueError(
                    f"can't determine condition ('{edge.non_para_id}') of node (Branch/Intent type, "
                    f"id='{gate_node.gate_id}', name='{node_name}')."
                    f"Please check config of this node or weather its' parent exists."
                ) from e

    def _determine_default_edge_before_loop(
        self,
        xor_gates_to_complete: list[GateFromIR],
        next_if_skip: dict[str, str],
        node_belongings: dict[str, ProcessFromIR],
    ):
        """
        Loop 前置的排他网关，用于判定是否进入循环，其默认边为 Loop 后连接的节点。
        在此补全 Loop 前排他网关的 default 边。
        """
        for xor_gate in xor_gates_to_complete:
            try:
                node_to_skip = self.all_edges[list(xor_gate.outgoing)[0]].target
                default_edge = EdgeFromIR(
                    {}, source=xor_gate.gate_id, target=next_if_skip[node_to_skip]
                )
            except KeyError as e:
                logger.error(
                    "Failed to determine default edge of the exclusive gateway (%s) before loop.",
                    xor_gate.gate_id,
                )
                raise e
            self.all_edges[default_edge.edge_id] = default_edge
            node_belongings[node_to_skip].connections.add(default_edge.edge_id)

            xor_gate.default = default_edge.edge_id

    def _post_add_parallel_gateway(
        self, edge: EdgeFromIR, from_process: ProcessFromIR
    ) -> EdgeFromIR:
        """
        并行开始，加并行网关，所有出边从该网关出。
        如果并行开始节点是 Loop, Loop 前置 xor_gate 的默认边不能直接指向 and_gate, 需在 Loop 与 and_gate 间加一空 task.

        增加节点后，一条边变两条边，含原有 source 的边计入 self.all_edges, 含原有 target 的边返回。
        """
        # 分支节点后，并行网关定位到分支
        source_id = (
            edge.normalize_id(edge.non_para_id) if edge.non_para_id else edge.source
        )
        gate_id = "and_gate_after_" + source_id
        edge_0, edge = edge.insert_node(gate_id)

        if gate_id not in self.all_and_gates:
            if self._is_edge_source_from_loop(
                edge_0
            ):  # 若 source 是 Loop, 在 Loop 与 and_gate 加一个空 task.
                edge_0 = self._add_empty_task_between_loop_and_gate(
                    edge_0, from_process
                )

            self.all_and_gates[gate_id] = GateFromIR(gate_id)
            self.all_and_gates[gate_id].incoming.add(edge_0.edge_id)
            self.all_edges[edge_0.edge_id] = edge_0
            from_process.connections.add(edge_0.edge_id)
            from_process.and_gates.add(gate_id)

        self.all_and_gates[gate_id].outgoing.add(edge.edge_id)
        return edge

    def _pre_add_inclusive_gateway(
        self, edge: EdgeFromIR, from_process: ProcessFromIR
    ) -> EdgeFromIR:
        """
        并行结束，统一加包容网关，所有入边从该网关入。

        增加节点后，一条边变两条边，含原有 source 的边计入 self.all_edges, 含原有 target 的边返回。
        """
        if self.is_need_empty_task_before_or_gate():
            edge_0, edge = edge.insert_node(
                NodeFromIR.create_node_id(prefix="empty_task_")
            )
            self.all_edges[edge_0.edge_id] = edge_0
            from_process.components.add(edge_0.target)
            from_process.connections.add(edge_0.edge_id)

        gate_id = "or_gate_before_" + edge.target

        edge_0, edge = edge.insert_node(gate_id)
        self.all_edges[edge_0.edge_id] = edge_0
        from_process.connections.add(edge_0.edge_id)
        from_process.or_gates.add(gate_id)

        if gate_id not in self.all_or_gates:
            self.all_or_gates[gate_id] = GateFromIR(gate_id)
            self.all_or_gates[gate_id].outgoing.add(edge.edge_id)
        self.all_or_gates[gate_id].incoming.add(edge_0.edge_id)
        return edge

    def _pre_add_exclusive_gateway(
        self,
        edge: EdgeFromIR,
        from_process: ProcessFromIR,
        gate_id: str = None,
        target_default: str = None,
    ) -> tuple[EdgeFromIR, GateFromIR]:
        """
        在 edge 中甲插入排他网关，默认边指向 target_default. 仅两个分支.
        若不指定 gate_id （可对应外部节点），则参考 edge.target 构造。

        适用情况：
        + Loop 前判定是否要进入 Loop
        + Loop 中判定是否要跳出 Loop
        """
        gate_id = gate_id or self.loop2gate_before(edge.target)

        edge_0, edge = edge.insert_node(gate_id)
        self.all_edges[edge_0.edge_id] = edge_0
        from_process.connections.add(edge_0.edge_id)
        from_process.xor_gates.add(gate_id)

        xor_gate = GateFromIR(gate_id)
        self.all_xor_gates[gate_id] = xor_gate
        xor_gate.incoming.add(edge_0.edge_id)
        xor_gate.outgoing.add(edge.edge_id)  # 缺少一个出边
        xor_gate.default = target_default
        return edge, xor_gate

    def _init_xml_root_node(self):
        root = etree.Element(
            etree.QName(default_nsmap[BPMN2], "definitions"),
            nsmap=default_nsmap,
            targetNamespace=config[WORKFLOW]["target_namespace"],
        )
        self.xml_nodes[self.root_id] = root
        self.xml_nodes[self.root_process_id] = etree.SubElement(
            root,
            etree.QName(default_nsmap[BPMN2], "process"),
            nsmap=None,
            id="process_node",
            name="process",
        )
        self._add_start_end_event_to_process(self.root_process_id)

    def _add_start_end_event_to_process(self, process_id: str):
        process = self.all_processes.get(process_id)
        xml_node_of_process = self.xml_nodes.get(process_id)
        if process_id == self.root_process_id:
            start_name, end_name = "Start", "End"

            start_target = (
                "node_start"
                if len(process.components) > 1
                else list(process.components)[0]
            )
            start_edge = EdgeFromIR({}, source=process.start_event, target=start_target)
            end_source = "node_end" if len(process.components) > 1 else start_target
            end_edge = EdgeFromIR({}, source=end_source, target=process.end_event)

            for edge in [start_edge, end_edge]:
                self.all_edges[edge.edge_id] = edge
                process.connections.add(edge.edge_id)
        else:
            start_name, end_name = process.start_event, process.end_event

        etree.SubElement(
            xml_node_of_process,
            etree.QName(default_nsmap[BPMN2], "startEvent"),
            id=process.start_event,
            name=start_name,
        )
        etree.SubElement(
            xml_node_of_process,
            etree.QName(default_nsmap[BPMN2], "endEvent"),
            id=process.end_event,
            name=end_name,
        )

    def _create_xml_node(self, node_id: str, parent_node: etree.Element):
        """task 或 SubProcess"""
        node_name = (
            self.all_nodes[node_id].node_type
            if node_id in self.all_nodes
            else "empty_task"
        )
        if node_id not in self.all_processes:  # task
            etree.SubElement(
                parent_node,
                etree.QName(default_nsmap[BPMN2], "task"),
                id=node_id,
                name=node_name,
            )
        else:  # 当前所有 subProcess 均为 Loop 内流程
            xml_node = etree.SubElement(
                parent_node,
                etree.QName(default_nsmap[BPMN2], "subProcess"),
                id=node_id,
                name=node_name,
            )
            standard_loop = etree.SubElement(
                xml_node,
                etree.QName(default_nsmap[BPMN2], "standardLoopCharacteristics"),
            )
            standard_loop_condition = etree.SubElement(
                standard_loop, etree.QName(default_nsmap[BPMN2], "loopCondition")
            )
            standard_loop_condition.text = self.loop_end_condition(
                self.all_nodes.get(node_id)
            )
            self.xml_nodes[node_id] = xml_node
            self._add_start_end_event_to_process(node_id)

    def _create_xml_edge(self, edge_id: str, parent_node: etree.Element):
        edge = self.all_edges.get(edge_id)
        line = etree.SubElement(
            parent_node,
            etree.QName(default_nsmap[BPMN2], "sequenceFlow"),
            id=edge_id,
            sourceRef=edge.source,
            targetRef=edge.target,
        )
        if edge.condition and edge.source in self.all_xor_gates:
            condition_of_line = etree.SubElement(
                line,
                etree.QName(default_nsmap[BPMN2], "conditionExpression"),
                {etree.QName(default_nsmap[XSI], TYPE): "bpmn2:tFormalExpression"},
            )
            condition_of_line.text = edge.condition

    def _create_xml_xor_gate(self, gate_id: str, parent_node: etree.Element):
        """生成排他网关"""
        gate = self.all_xor_gates[gate_id]
        gate_xml = etree.SubElement(
            parent_node,
            etree.QName(default_nsmap[BPMN2], "exclusiveGateway"),
            id=gate_id,
            name="exclusiveGateway",
        )
        if gate.default:
            gate_xml.attrib["default"] = gate.default

    def _create_xml_and_or_gate(
        self, gate_id: str, parent_node: etree.Element, is_and_gate: bool
    ):
        """
        生成并行网关或包容网关。
        并行网关用作并行开始标志；包容网关用以收束（并行及非并行）分支。
        """
        if is_and_gate:
            gate = self.all_and_gates[gate_id]
            gate_tag = "parallelGateway"
        else:
            gate = self.all_or_gates[gate_id]
            gate_tag = "inclusiveGateway"
        gate_xml = etree.SubElement(
            parent_node,
            etree.QName(default_nsmap[BPMN2], gate_tag),
            id=gate_id,
            name=gate_tag,
        )
        for edge_in in gate.incoming:
            incoming_edge = etree.SubElement(
                gate_xml, etree.QName(default_nsmap[BPMN2], "incoming")
            )
            incoming_edge.text = edge_in
        for edge_out in gate.outgoing:
            outgoing_edge = etree.SubElement(
                gate_xml, etree.QName(default_nsmap[BPMN2], "outgoing")
            )
            outgoing_edge.text = edge_out
