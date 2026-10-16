#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from copy import deepcopy
from typing import Dict, Any, Optional, List, Union

from jiuwen.controller.common.constants import FUNCTION_ROLE
from jiuwen.serve.controllers.execution.enum import MessageRole
from pydantic import BaseModel


class ConversationMessage(BaseModel):
    role: str
    content: str
    files: Optional[List[Dict[str, Any]]] = None
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    function_call: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    intent: Optional[List[str]] = None
    enable_history: Optional[bool] = True
    agent_id: Optional[str] = None


class ConversationHistory:
    def __init__(self, conversation_history=None):
        self.model_config: Optional[dict] = None
        self._msgs: List[ConversationMessage] = []
        self._result_message: str = ""
        if conversation_history:
            self.add_messages(conversation_history)

    @property
    def msgs(self):
        """get msg history"""
        return self._msgs

    @msgs.setter
    def msgs(self, msgs):
        """set msgs"""
        self._msgs = msgs

    @property
    def result_message(self):
        """get msg history"""
        return self._result_message

    @staticmethod
    def convert_messages_to_chat_history_dict(
        latest_messages, filter_history: bool = True
    ):
        """convert conversation messages to array of dict

        Args:
            latest_messages: 待转换的消息列表
            filter_history: 是否过滤enable_history=False的消息；持久化场景
                （intermediate_message）需保留这些消息并携带标志位，应传False，
                否则下一轮加载时标志位丢失会被默认补True
        """
        formatted_messages = []
        for msg in latest_messages:
            if filter_history and not msg.enable_history:
                continue
            message_dict = {"role": msg.role, "content": msg.content}
            if msg.enable_history is False:
                message_dict["enable_history"] = False
            if msg.files:
                message_dict["files"] = msg.files
            if msg.agent_id:
                message_dict["agent_id"] = msg.agent_id
            if msg.function_call:
                message_dict["function_call"] = msg.function_call
            function_name = msg.name
            if function_name:
                message_dict["name"] = function_name
            tool_call_id = msg.tool_call_id
            if tool_call_id:
                message_dict.update(dict(tool_call_id=tool_call_id))
            else:
                if msg.role and msg.role == FUNCTION_ROLE:
                    message_dict.update(dict(tool_call_id=""))

            # 如果有函数调用信息，添加到消息中
            tool_calls, function_call_list = [], []
            function_call = msg.function_call
            if function_call:
                if isinstance(function_call, list):
                    function_call_list.extend(function_call)
                if isinstance(function_call, dict):
                    function_call_list = [function_call]

            for _ in function_call_list:
                item = deepcopy(_)
                tool_call_id = item.pop("tool_call_id", None)
                if "args" in item and "arguments" not in item:
                    item["arguments"] = item.pop("args")
                tool_call_item = dict(type="function", id="", function=item)
                if tool_call_id:
                    tool_call_item.update(id=tool_call_id)
                tool_calls.append(tool_call_item)
            if tool_calls:
                message_dict.update(tool_calls=tool_calls)

            formatted_messages.append(message_dict)

        return formatted_messages

    @staticmethod
    def _convert_tool_calls_to_function_calls(
        tool_calls,
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        ReactAgent Mode: convert tool calls to function_calls
        :param tool_calls:
        :return:
        """
        result = list()
        if isinstance(tool_calls, list):
            for tool_call in tool_calls:
                tool_call_id = tool_call.get("id", "")
                func_name = tool_call.get("function", dict()).get("name", "")
                func_args = tool_call.get("function", dict()).get("arguments", "")
                function_call = dict(
                    name=func_name, args=func_args, tool_call_id=tool_call_id
                )
                result.append(function_call)
        return result

    @staticmethod
    def _msgs_safe_truncat(
        history: List[ConversationMessage],
    ) -> List[ConversationMessage]:
        if len(history) > 0 and history[0].role != FUNCTION_ROLE:
            return history
        # 避免tool消息无法溯源错误，过滤开头连续的ToolMessage，截断处理
        for idx, msg in enumerate(history):
            if msg.role != FUNCTION_ROLE:
                return history[idx:]
        return []

    def add_messages(self, messages: Union[List[Dict], List[ConversationMessage]]):
        """
        直接设置消息上下文中的消息列表，接收字典列表格式的消息

        Args:
            messages: 要设置的消息列表，可以传入两种格式，
                1. List[ConversationMessage]可以直接写入
                2. List[Dict]，格式为[{"role":"user", "content":"xxx"}, ...]，转化后写入
        """
        # 将字典列表转换为Message对象列表
        for msg in messages:
            if isinstance(msg, ConversationMessage):
                self.add(msg)
                continue
            if isinstance(msg, dict):
                tool_calls = msg.get("tool_calls")
                function_call = self._convert_tool_calls_to_function_calls(tool_calls)
                if not function_call:
                    function_call = msg.get("function_call")
                raw_content = msg.get("content")
                content = str(raw_content) if raw_content is not None else None
                message = ConversationMessage(
                    role=msg.get("role"),
                    content=content,
                    files=msg.get("files"),
                    name=msg.get("name"),
                    intent=msg.get("intent"),
                    tool_call_id=msg.get("tool_call_id", None),
                    function_call=function_call,
                    enable_history=msg.get("enable_history", True),
                    agent_id=msg.get("agent_id"),
                )
                self.add(message)

    def clear(self):
        """
        clear message context
        """
        self._msgs = []

    def add(self, msg: ConversationMessage):
        """
        add a message
        """
        self._msgs.append(msg)

    def get_all_messages(self) -> List[ConversationMessage]:
        """
        返回所有对话历史
        """
        return self._msgs

    def get_messages(
        self,
        agent_id: str = None,
        intent: str = None,
        enable_history: bool = True,
        num: int = -1,
    ) -> List[ConversationMessage]:
        """
        get messages by filter stratergy
        Args:
            agent_id: 通过agent_id筛选上下文
            intent: 通过intent筛选上下文
            enable_history: 通过enable_history筛选上下文
            num: 上下文消息截断，最多返回num数量消息
        Returns:
            上下文会话历史消息
        """
        filtered_history = []
        for message in self._msgs:
            # filter by agent_id
            if agent_id and message.agent_id != agent_id:
                continue
            # filter by intent
            if intent and intent not in (message.intent or []):
                continue
            # filter by enable_history
            if not enable_history and not message.enable_history:
                continue
            filtered_history.append(message)
        # truncat by number
        if len(filtered_history) >= num > 0:
            return self._msgs_safe_truncat(filtered_history[-num:])
        return filtered_history

    def get_messages_by_turn(self, num_turns: int) -> List[ConversationMessage]:
        """
        获取最近 num_turns 轮对话的消息。

        1 轮 = 1 条 user 消息 + 其对应的所有回复 (assistant/function/tool 等)。
        从后往前按 user 消息计数，确保截断起点一定是 user 消息，
        避免残留孤立的 function/tool 消息导致模型上下文不完整。

        Args:
            num_turns: 对话轮数，最多返回最近 num_turns 轮的所有消息

        Returns:
            最近 num_turns 轮的所有消息（包含中间的工具调用消息）
        """
        if not self._msgs or num_turns <= 0:
            return []

        start_index = 0
        user_count = 0
        for i in range(len(self._msgs) - 1, -1, -1):
            if self._msgs[i].role == "user":
                user_count += 1
                if user_count == num_turns:
                    start_index = i
                    break

        if user_count < num_turns:
            return self._msgs.copy()

        return self._msgs_safe_truncat(self._msgs[start_index:])

    def get_conversation_history(self, filter_history: bool = False) -> List[Dict]:
        """
        过滤工具调用命令消息和工具执行结果消息， 只保留用户输入和Agent回复

        Args:
            filter_history: 是否开启enable_history筛选消息

        Returns:
            上下文会话历史消息
        """
        filtered_history = []
        for msg in self._msgs:
            if filter_history and not msg.enable_history:
                continue
            role = msg.role
            if role in [MessageRole.USER.value, MessageRole.ASSISTANT.value]:
                filtered_history.append(msg.model_dump(exclude_none=True))
        return filtered_history

    def set_result_msg(self, content: str):
        """set msgs"""
        self._result_message = content

    def delete_latest_message(self):
        """eliminate latest message"""
        return self._msgs.pop()

    def set_latest_intent(self, intent_str: str):
        """set intent for latest message"""
        if len(self._msgs) > 0:
            if self._msgs[-1].intent:
                # 只有当intent不在列表中时才添加
                if intent_str not in self._msgs[-1].intent:
                    self._msgs[-1].intent.append(intent_str)
            else:
                self._msgs[-1].intent = [intent_str]

    def set_latest_intent_list(self, intent_list: List):
        """set intent for latest message"""
        if len(self._msgs) > 0:
            if not self._msgs[-1].intent:
                self._msgs[-1].intent = []

            for item in intent_list:
                # 只有当intent不在列表中时才添加
                if item not in self._msgs[-1].intent:
                    self._msgs[-1].intent.append(item)

    def get_latest_intent(self) -> Optional[List[str]]:
        """获取最新消息的意图"""
        latest_msg = self._msgs[-1]
        if latest_msg.intent is None:
            return []  # 返回空列表而不是None
        if isinstance(latest_msg.intent, list):
            return latest_msg.intent
        # 如果不是列表，确保返回列表
        return [latest_msg.intent] if latest_msg.intent else []

    def get_second_latest_user_intent(self) -> Optional[str]:
        """获取上上条user message的最新意图（intent列表的最后一个元素）

        Returns:
            str 或 None: 如果找到倒数第二条user消息且有intent，返回其intent列表的最后一个；否则返回None
        """
        # 从后往前找user消息
        user_msgs = []
        for msg in reversed(self._msgs):
            if msg.role == "user":
                user_msgs.append(msg)
                if len(user_msgs) == 2:  # 找到第二条user消息
                    break

        # 如果没有找到第二条user消息，返回None
        if len(user_msgs) < 2:
            return None

        second_latest_user_msg = user_msgs[1]  # 倒数第二条user消息
        if second_latest_user_msg.intent is None:
            return None

        # 确保intent是列表
        intent_list = (
            second_latest_user_msg.intent
            if isinstance(second_latest_user_msg.intent, list)
            else [second_latest_user_msg.intent]
        )

        # 返回列表中的最后一个元素，如果列表为空则返回None
        return intent_list[-1] if intent_list else None

    def add_global_intent(self, intent):
        """为上下文添加全局意图"""
        for msg in self._msgs:
            if msg.intent:
                # 只有当global_intent不在列表中时才添加
                if intent not in msg.intent:
                    msg.intent.append(intent)
            else:
                msg.intent = [intent]

    def has_intent_in_history(self, intent) -> bool:
        """
        Check if the intent is in the historical intent list

        Parameters:
            intent (str): The intent to check.

        Returns:
            bool: True if the intent is in the historical intent list; otherwise, False.
        """
        for msg in self._msgs:
            if msg.intent and intent in msg.intent:
                return True
        return False
