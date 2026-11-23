#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.constant import USER_FIELDS, WORKFLOW_CHAT_HISTORY
from jiuwen.orchestration.utils import Output
from utils.constants import RUNTIME_CONTEXT

from .base_parser import BaseParser


class QaNodeParser(BaseParser):
    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        result = outputs.get(USER_FIELDS, {}).get("response")
        if not result:
            return []
        config = kwargs.get("component_metadata", {}).get("component_config", {})
        if config.get("needReply", False):
            output = {"role": "user", "content": result}
            history = kwargs.get(RUNTIME_CONTEXT, {}).get(WORKFLOW_CHAT_HISTORY)
            if not history or len(history.get_all_messages()) < 2:
                return [output]
            last_assistant_message = history.get_all_messages()[-2]
            if last_assistant_message.get("content") in config.get("options", []):
                last_assistant_message.pop("intent", None)
                return [last_assistant_message, output]
            else:
                return [output]
        else:
            return [{"role": "assistant", "content": result}]

    @classmethod
    def get_type(cls):
        return "EI.qa"
