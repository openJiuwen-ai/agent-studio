#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import Any

from jiuwen.orchestration.utils import Output, Input


class BaseParserMeta(type):
    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        if name != "BaseParser":
            from ..memory_callback_handler import Memory4CallbackHandler

            Memory4CallbackHandler.register(new_class)
        return new_class


class BaseParser(metaclass=BaseParserMeta):
    @classmethod
    def pre_parse(cls, inputs: Input, *args: Any, **kwargs: Any):
        return []

    @classmethod
    def invoke_parse(cls, data: dict, *args: Any, **kwargs: Any):
        return []

    @classmethod
    def post_parse(cls, outputs: Output, *args: Any, **kwargs: Any):
        return []

    @classmethod
    def get_type(cls):
        return None
