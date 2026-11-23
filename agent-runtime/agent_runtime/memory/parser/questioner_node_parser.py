#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.components.util import convert_to_old_type
from jiuwen.orchestration.flow.constant import QuestionerKeyword
from jiuwen.orchestration.flow.enum import NodeType

from .base_parser import BaseParser
from ..cache.factory import CacheFactory
from ..utils import get_runtime_memory_key_ids


class QuestionerNodeParser(BaseParser):
    @classmethod
    def invoke_parse(cls, data: dict, *args: Any, **kwargs: Any):
        _, workflow_id, user_id, execution_id = get_runtime_memory_key_ids(**kwargs)
        if user_id is not None and execution_id is not None and workflow_id is not None:
            # 提问器会多报一次历史输入，需要过滤掉
            last_input = CacheFactory.get_chat_cache().read_tail(
                f"{workflow_id}:{execution_id}", 1
            )
            if (
                last_input
                and (last_input[0].get(QuestionerKeyword.ROLE) in data)
                and (
                    last_input[0].get(QuestionerKeyword.CONTENT)
                    == data.get(last_input[0].get(QuestionerKeyword.ROLE))
                )
            ):
                return []
        return [
            {QuestionerKeyword.ROLE: i, QuestionerKeyword.CONTENT: data.get(i)}
            for i in [QuestionerKeyword.USER, QuestionerKeyword.ASSISTANT]
            if i in data
        ]

    @classmethod
    def get_type(cls):
        return convert_to_old_type.get(NodeType.QUESTIONER.value)
