#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.bpmn_workflow import convert_to_old_type
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output

from .base_parser import BaseParser


class EndNodeParser(BaseParser):
    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        result = outputs.get("responseContent")
        if not result:
            return []
        return [{"role": "assistant", "content": result}]

    @classmethod
    def get_type(cls):
        return convert_to_old_type.get(NodeType.END.value)
