#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from typing import Any

from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output

from .base_parser import BaseParser


class InputNodeParser(BaseParser):
    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        input_vals = (
            kwargs.get("component_metadata", {})
            .get("component_config", {})
            .get("userFields", {})
            .get("inputs")
        )
        if not input_vals:
            return []
        result = []
        val_desc = "请输入\n" + "\n".join(
            [
                f"参数名称:{i.get('id')}, 参数描述:{i.get('description')}"
                for i in input_vals
            ]
        )
        result.append({"role": "assistant", "content": val_desc})
        result.append(
            {
                "role": "user",
                "content": "\n".join(
                    [
                        f"参数名称:{k}, 输入值:{v}"
                        for k, v in outputs.get("userFields", {}).items()
                    ]
                ),
            }
        )
        return result

    @classmethod
    def get_type(cls):
        return NodeType.INPUT.value
