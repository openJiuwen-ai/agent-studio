#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.components.util import convert_to_old_type
from jiuwen.orchestration.flow.constant import GLOBAL_CONFIG
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output
from utils.constants import WORKFLOW_OPENING_WORDS, RUNTIME_CONTEXT

from .base_parser import BaseParser
from ..cache.factory import CacheFactory
from ..utils import get_runtime_memory_key_ids


class StartNodeParser(BaseParser):
    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        _, workflow_id, _, execution_id = get_runtime_memory_key_ids(**kwargs)
        record_ids = CacheFactory.get_call_workflow_cache().read_tail(execution_id)
        if workflow_id in record_ids:
            # 当前是子工作流，不再采集开始的对话，因为是父工作流传入的
            return []
        result = []
        opening_words = (
            kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(WORKFLOW_OPENING_WORDS)
        )
        if opening_words:
            result.append({"role": "assistant", "content": opening_words})
        result.extend(
            outputs.get("systemFields", {})
            .get("sys", {})
            .get("conversationHistory", [])
        )
        return result

    @classmethod
    def get_type(cls):
        return convert_to_old_type.get(NodeType.START.value)
