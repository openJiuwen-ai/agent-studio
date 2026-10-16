#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.
import copy
import re
from dataclasses import dataclass
from typing import Any, Optional, Generator, AsyncGenerator

from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.context.history import ConversationHistory
from jiuwen.orchestration import Invokable
from jiuwen.orchestration.flow.components.util import (
    evaluate_expression,
    find_references,
)
from jiuwen.orchestration.flow.constant import (
    USER_FIELDS,
    BPMN_VARIABLE_POOL_SEPARATOR,
    MAXIMUM_LENGTH_OF_A_REGULAR_STRING,
    CONSTANT_NUM_LOOP_VAR,
    CONSTANT_ARRAY_LOOP_VAR,
    CONSTANT_INTERMEDIATE_LOOP_VAR,
    CONSTANT_NODE_VARIABLE,
    WORKFLOW_CHAT_HISTORY,
    LOOP_DEFAULT_LOOP_MAX_NUM,
    REQUEST_VARIABLES,
    REQUEST_PREFIX,
)
from jiuwen.orchestration.flow.enum import LoopType, ExecutionStatus
from jiuwen.orchestration.flow.model.workflow_data_class import WorkflowMetadata
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.flow.state import State
from jiuwen.orchestration.flow.stream.base import StreamCode
from jiuwen.orchestration.utils import Input, Output

LOOP_CONDITION_CHECKED = "_condition_checked"
PRE_DEFINED_FIELDS = "preDefinedFields"
CHAT_HISTORY = "chat_history"
INTERMEDIATE_LOOP_VAR = "intermediateLoopVar"


@dataclass
class LoopState(State):
    loop_index: int = 0
    loop_num: int = 0
    item: Optional = None
    array: Optional = None
    status: ExecutionStatus = ExecutionStatus.START


class Loop(Invokable):
    def __init__(self):
        self._conf = None
        self._runtime_context = None
        self.metadata = None
        self.node_state = LoopState()
        self.condition = ""
        self.is_break = False
        super().__init__()

    @staticmethod
    def find_shortest_length(list_of_lists):
        """
        检查输入是否为空
        :param list_of_lists: 输入列表
        :return: 列表最短长度
        """
        if not list_of_lists:
            return 0

        # 使用min函数和len函数结合，找出最短子列表的长度
        shortest_length = min(len(sublist) for sublist in list_of_lists)

        return shortest_length

    def init(self, conf: dict, **kwargs):
        runtime_context = kwargs.get("runtime_context")
        metadata = kwargs.get("metadata")

        if self.node_state.status not in [ExecutionStatus.START, ExecutionStatus.END]:
            return

        self._conf = conf
        self._runtime_context = runtime_context
        self.metadata = metadata
        self.node_state = LoopState()
        self.condition = self._conf.get("breakCondition", "")
        self.is_break = False

    def get_chat_history(self):
        """
        获取历史对话记录
        :return:
        """
        conversation_history = self._runtime_context.get(WORKFLOW_CHAT_HISTORY)
        if isinstance(conversation_history, ConversationHistory):
            return conversation_history.get_all_messages()
        return []

    def get_state(self):
        """
        get loop state
        """
        return self.node_state

    def load_state(self, state: LoopState):
        """
        load loop state from input state
        """
        self.node_state = copy.deepcopy(state)

    def refresh_node_state(self):
        """
        刷新循环组件的状态
        :return:
        """
        if self.node_state.status == ExecutionStatus.START:
            self.node_state.status = ExecutionStatus.LOOP_RUNNING
            if self.is_break:
                self.node_state.status = ExecutionStatus.END
        elif (
            int(self.node_state.loop_index) >= int(self.node_state.loop_num)
            or self.is_break
        ):
            # 如果循环中断，那么状态需要手动设置
            if self.node_state.status not in [
                ExecutionStatus.LOOP_FINISH,
                ExecutionStatus.END,
            ]:
                self.node_state.status = ExecutionStatus.LOOP_FINISH
            else:
                self.node_state.status = ExecutionStatus.END
        self.metadata.node_state = self.node_state

    def get_node_status(self):
        """
        返回节点状态
        :return:
        """
        return self.node_state.status

    def invoke(self, inputs: Input, **kwargs) -> Output:
        # 先从变量池里取参数，如果变量池为空，则使用inputs
        loop_type = self._conf.get("loopType")
        if self.node_state.status == ExecutionStatus.START:
            self._validate_inputs(inputs)
            if loop_type == LoopType.NUMBER.value:
                self.node_state.loop_num = int(inputs.get(CONSTANT_NUM_LOOP_VAR))
                # 防止类型不一致导致bpmn报错
                inputs[CONSTANT_NUM_LOOP_VAR] = self.node_state.loop_num
            else:
                arrs = inputs.get(CONSTANT_ARRAY_LOOP_VAR, []) or []
                self.node_state.array = arrs
                self.node_state.loop_num = len(arrs)
                if self.node_state.loop_index < len(arrs):
                    self.node_state.item = arrs[self.node_state.loop_index]
            # 检查循环次数
            self._loop_num_check(self.node_state.loop_num)
        else:
            # 中断条件，只能从False变为True；第一次是排他网关，不用进行判断
            if self.condition and not self.is_break:
                try:
                    eval_inputs = self._construct_inputs_of_loop_break_condition()
                    self.is_break = evaluate_expression(
                        self.condition, eval_inputs, logger
                    )
                except Exception as e:
                    logger.warning(str(e), simple_log=f"{type(e).__name__}")

            if loop_type == LoopType.ARRAY.value:
                if self.node_state.loop_index < len(self.node_state.array):
                    self.node_state.item = self.node_state.array[
                        self.node_state.loop_index
                    ]

        # 必须先更新_loop_num
        self.refresh_node_state()
        outputs = copy.deepcopy(inputs)
        inter_loop_var = (
            self._runtime_context.get(CONSTANT_NODE_VARIABLE)
            .get(self.metadata.node_id, {})
            .get(CONSTANT_INTERMEDIATE_LOOP_VAR, None)
        )

        outputs.update(
            {
                "index": self.node_state.loop_index,
                "loop_nums": self.node_state.loop_num,
                "is_break": self.is_break,
            }
        )
        if loop_type == LoopType.ARRAY.value and self.node_state.item is not None:
            outputs.update({CONSTANT_ARRAY_LOOP_VAR: {"item": self.node_state.item}})
        outputs[USER_FIELDS] = self._get_outputs()
        if inter_loop_var:
            outputs[CONSTANT_INTERMEDIATE_LOOP_VAR] = inter_loop_var
        self.node_state.loop_index += 1
        return outputs

    def _construct_inputs_of_loop_break_condition(self):
        inputs = {}
        params_set = set()
        references = find_references(self.condition)
        for each in references:
            if each not in params_set:
                match_str = get_ref_str(each)
                real_value = get_value_from_nested_structure_by_path_list(
                    nested_structure=self._runtime_context.get(CONSTANT_NODE_VARIABLE),
                    path=match_str,
                )
                inputs[each] = real_value
                params_set.add(each)
        return inputs

    def _validate_inputs(self, inputs):
        """
        Check whether the user has passed in all global_variables defined in the config.
        """

        def is_loop_type(value):
            return any(value == item.value for item in LoopType)

        loop_type = self._conf.get("loopType")
        if not is_loop_type(loop_type):
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_LOOP_UNSUPPORTED_TYPE_ERROR.code,
                StatusCode.WORKFLOW_LOOP_UNSUPPORTED_TYPE_ERROR.errmsg.format(
                    loop_type=loop_type
                ),
            )

        if loop_type == LoopType.NUMBER.value and CONSTANT_NUM_LOOP_VAR not in inputs:
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_LOOP_FIELD_EMPTY_TYPE_ERROR.code,
                StatusCode.WORKFLOW_LOOP_FIELD_EMPTY_TYPE_ERROR.errmsg.format(
                    field=CONSTANT_NUM_LOOP_VAR, loop_type=loop_type
                ),
            )

        if loop_type == LoopType.NUMBER.value and not isinstance(
            inputs[CONSTANT_NUM_LOOP_VAR], int
        ):
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_LOOP_FIELD_TYPE_ERROR.code,
                StatusCode.WORKFLOW_LOOP_FIELD_TYPE_ERROR.errmsg.format(
                    field=CONSTANT_NUM_LOOP_VAR,
                    loop_type=loop_type,
                    type=type(inputs[CONSTANT_NUM_LOOP_VAR]),
                ),
            )

        if loop_type == LoopType.ARRAY.value and CONSTANT_ARRAY_LOOP_VAR not in inputs:
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_LOOP_FIELD_EMPTY_TYPE_ERROR.code,
                StatusCode.WORKFLOW_LOOP_FIELD_EMPTY_TYPE_ERROR.errmsg.format(
                    field=CONSTANT_ARRAY_LOOP_VAR, loop_type=loop_type
                ),
            )

    def _loop_num_check(self, loop_num):
        """
        循环次数检查
        :return:
        """
        if loop_num < 1 or loop_num > LOOP_DEFAULT_LOOP_MAX_NUM:
            raise JiuWenBaseException(
                StatusCode.WORKFLOW_LOOP_NUM_ERROR.code,
                StatusCode.WORKFLOW_LOOP_NUM_ERROR.errmsg.format(loop_num=loop_num),
            )

    def _replace_loop_comp_id(self, ori_str: str):
        """
        替换循环体内组件的id
        :param ori_str: 原始字符串
        :return:
        """
        ori_list = split_string(ori_str)
        return ori_list[0] + "_loop", ori_str.replace(ori_list[0] + ".", "")

    def _get_outputs(self):
        """
        从config里取出相关引用值
        :return:
        """
        outputs = {}
        for conf in self._conf.get(USER_FIELDS, {}).get("outputs", []):
            field = conf.get("id", "")
            value = conf.get("value", "")
            match_str = get_ref_str(value)
            if match_str:
                # 获取真实的值
                if INTERMEDIATE_LOOP_VAR not in match_str:
                    # 如果是user_fields，要去对应组件的loop结果里找结果，返回结果为list
                    new_match_str, new_path = self._replace_loop_comp_id(match_str)
                    nested_dicts = self._runtime_context.get(
                        CONSTANT_NODE_VARIABLE
                    ).get(new_match_str)
                    if nested_dicts:
                        real_value = [
                            get_value_from_nested_structure_by_path_list(
                                nested_dict, new_path
                            )
                            for nested_dict in nested_dicts
                        ]
                    else:
                        real_value = None
                else:
                    # 否则为中间变量，只支持两种
                    real_value = get_value_from_nested_structure_by_path_list(
                        nested_structure=self._runtime_context.get(
                            CONSTANT_NODE_VARIABLE
                        ),
                        path=match_str,
                    )
                outputs.update({field: real_value})
        return outputs


def split_string(origin_str: str) -> list:
    """
    @param origin_str: 原始字符串，例如："a_1.b.c[1].d"
    @return: 原始字符串切分后的列表，对应参数示例的结果为：["a_1", "b", "c", 1, "d"]
    """
    # 使用正则表达式进行分割
    param_list = origin_str.split(BPMN_VARIABLE_POOL_SEPARATOR)
    final_list = []
    pattern = r"^([\w]+)((?:\[\d+\])*)$"
    for param in param_list:
        # 限制待匹配字符串长度，避免ReDos攻击
        match = re.match(pattern, param[:MAXIMUM_LENGTH_OF_A_REGULAR_STRING])
        if match:
            final_list.append(match.group(1))
            index = match.group(2)
            numbers = re.findall(r"\d+", index)
            final_list += [
                int(number) if str.isdigit(number) else number for number in numbers
            ]
    return final_list


def get_value_from_nested_structure_by_path_list(nested_structure: dict, path: str):
    """
    根据path路径从nested_structure中获取该路径对应的值
    @param nested_structure: 数据源
    @param path: 从节点ID开始的数据路径，例如node_start.systemFields.a[0]，表示node_start的key为systemFields下的key为a下的
                 第一个元素
    @return: 根据路径从数据源中获取到的值，未获取到的情况下返回 None
    """
    final_result = nested_structure
    path_list = split_string(path)
    for key in path_list:
        if isinstance(final_result, dict) and key in final_result:
            final_result = final_result.get(key)
        elif isinstance(final_result, list):
            if isinstance(key, int) and key < len(final_result):
                final_result = final_result[key]
            elif isinstance(key, str):
                # 对 list 中每个 dict 抽取同名字段（map 语义）。
                # 注意不能先覆盖 final_result 再遍历自身，否则恒返回空列表。
                mapped_result = []
                for item in final_result:
                    if isinstance(item, dict):
                        mapped_result.append(item.get(key, None))
                    else:
                        return None
                final_result = mapped_result
            else:
                return None

        else:
            return None
    return final_result


def create_nested_dict(path_list, value):
    """
    根据路径，设置对应的值
    :param path_list: 层级结构，形如[node_start, systemFields, query]
    :param value: 对应的value值
    :return: 新的数据字典
    """
    if len(path_list) == 0:
        return value
    return {path_list[0]: create_nested_dict(path_list[1:], value)}


def get_ref_str(origin_str: str):
    """
    从匹配形如"${start123.p2}"的字符串中提取引用字符串 "start123.p2"
    """
    pattern = re.compile(r"\$\{(.+?)\}")
    # 限制待匹配字符串长度，避免ReDos攻击
    match = pattern.search(origin_str[:MAXIMUM_LENGTH_OF_A_REGULAR_STRING])
    if match:
        return match.group(1)
    return ""


def merge_dicts(dict1, dict2):
    """
    合并两个字典，如果遇到相同的键，则用第二个字典中的值覆盖第一个字典中的值。
    如果值是字典类型，则递归地进行合并。

    :param dict1: 第一个字典，需要返回引用
    :param dict2: 第二个字典
    :return: 合并后的字典
    """
    for key in dict2:
        value2 = dict2[key]
        if key in dict1:
            value1 = dict1[key]
            # 类型检查放在递归调用前
            if isinstance(value1, dict) and isinstance(value2, dict):
                # 显式返回合并后的引用，保持代码结构一致性
                dict1[key] = merge_dicts(value1, value2)
            else:
                dict1[key] = value2
        else:
            dict1[key] = value2
    return dict1  # 始终返回修改后的原字典


class SetVariable(Invokable):
    """
    设置变量 组件，仅在循环体中使用
    """

    def __init__(
        self, conf: dict, runtime_context: RuntimeContext, metadata: WorkflowMetadata
    ):
        self.conf = conf
        self.runtime_context = runtime_context
        self.metadata = metadata

    def invoke(self, inputs: dict[str, Any], **kwargs):

        for setting in self.conf.get("settings", []):
            # 需要解析 ${.*}
            left_match_str = get_ref_str(setting.get("left", {}).get("value"))
            right = setting.get("right", {}).get("value")
            right_match_str = get_ref_str(right) if isinstance(right, str) else None
            right_value = right
            if right_match_str:
                # 获取真实的值
                # 根据前缀选择数据源：_request. 从 REQUEST_VARIABLES 取，否则从 node_variable 取
                if right_match_str.startswith(REQUEST_PREFIX):
                    data_source = self.runtime_context.get(REQUEST_VARIABLES) or {}
                    path = right_match_str[len(REQUEST_PREFIX) :]
                else:
                    data_source = self.runtime_context.get(CONSTANT_NODE_VARIABLE)
                    path = right_match_str
                right_value = get_value_from_nested_structure_by_path_list(
                    nested_structure=data_source, path=path
                )

                if isinstance(right_value, Generator):
                    final_res = ""
                    for item in right_value:
                        if isinstance(item, str):
                            final_res += item
                        elif not hasattr(item, "code"):
                            continue
                        elif item.code == StreamCode.PARTIAL_CONTENT.value:
                            final_res += item.data.get("answer", "")
                        elif item.code in [
                            StreamCode.FINISH.value,
                            StreamCode.ERROR.value,
                        ]:
                            break
                    right_value = final_res

            if left_match_str:
                # 检查是否为 _request. 开头的变量
                self._update_request_variable(left_match_str, right_value)

                path_list = split_string(left_match_str)
                right_data = create_nested_dict(path_list, right_value)

                self.runtime_context.set(
                    CONSTANT_NODE_VARIABLE,
                    merge_dicts(
                        self.runtime_context.get(CONSTANT_NODE_VARIABLE), right_data
                    ),
                )

        inputs_copy = copy.deepcopy(inputs)
        return inputs_copy

    async def ainvoke(self, inputs: dict[str, Any], **kwargs):

        for setting in self.conf.get("settings", []):
            # 需要解析 ${.*}
            left_match_str = get_ref_str(setting.get("left", {}).get("value"))
            right = setting.get("right", {}).get("value")
            right_match_str = get_ref_str(right) if isinstance(right, str) else None
            right_value = right
            if right_match_str:
                # 获取真实的值
                # 根据前缀选择数据源：_request. 从 REQUEST_VARIABLES 取，否则从 node_variable 取
                if right_match_str.startswith(REQUEST_PREFIX):
                    data_source = self.runtime_context.get(REQUEST_VARIABLES) or {}
                    path = right_match_str[len(REQUEST_PREFIX) :]
                else:
                    data_source = self.runtime_context.get(CONSTANT_NODE_VARIABLE)
                    path = right_match_str
                right_value = get_value_from_nested_structure_by_path_list(
                    nested_structure=data_source, path=path
                )

                if isinstance(right_value, Generator):
                    final_res = ""
                    for item in right_value:
                        if isinstance(item, str):
                            final_res += item
                        elif not hasattr(item, "code"):
                            continue
                        elif item.code == StreamCode.PARTIAL_CONTENT.value:
                            final_res += item.data.get("answer", "")
                        elif item.code in [
                            StreamCode.FINISH.value,
                            StreamCode.ERROR.value,
                        ]:
                            break
                    right_value = final_res
                elif isinstance(right_value, AsyncGenerator):
                    final_res = ""
                    async for item in right_value:
                        if isinstance(item, str):
                            final_res += item
                        elif not hasattr(item, "code"):
                            continue
                        elif item.code == StreamCode.PARTIAL_CONTENT.value:
                            final_res += item.data.get("answer", "")
                        elif item.code in [
                            StreamCode.FINISH.value,
                            StreamCode.ERROR.value,
                        ]:
                            break
                    right_value = final_res

            if left_match_str:
                # 检查是否为 _request. 开头的变量
                self._update_request_variable(left_match_str, right_value)

                path_list = split_string(left_match_str)
                right_data = create_nested_dict(path_list, right_value)

                self.runtime_context.set(
                    CONSTANT_NODE_VARIABLE,
                    merge_dicts(
                        self.runtime_context.get(CONSTANT_NODE_VARIABLE), right_data
                    ),
                )

        inputs_copy = copy.deepcopy(inputs)
        return inputs_copy

    def _update_request_variable(self, left_match_str: str, right_value: Any) -> None:
        """
        更新会话变量（如果左侧变量以 _request. 开头）

        Args:
            left_match_str: 左侧匹配字符串（已提取的引用路径）
            right_value: 右侧的值
        """
        if not left_match_str.startswith(REQUEST_PREFIX):
            return
        # 移除 _request. 前缀
        path_list = split_string(left_match_str[len(REQUEST_PREFIX) :])
        right_data = create_nested_dict(path_list, right_value)

        # 全局变量重新赋值后 写入到 REQUEST_VARIABLES
        request_variables = self.runtime_context.get(REQUEST_VARIABLES) or {}
        request_variables = merge_dicts(request_variables, right_data)
        self.runtime_context.set(REQUEST_VARIABLES, request_variables)
