# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Private, in-process execution events; never an HTTP response body by itself."""

import json
from dataclasses import dataclass
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class ExecutionEventStream:
    """Carry prefetched events to EventHandler without an intermediate SSE codec."""

    body_iterator: AsyncIterator[Any]


def copy_json_event(event: dict) -> dict:
    """Preserve JSON round-trip isolation without copying immutable text buffers.

    Normalize mutable containers, tuples and object keys like json.dumps/loads.
    Validate unsupported values before yielding, preserving the prefetch boundary.
    """
    ancestors = set()

    def copy_value(value):
        if value is None or isinstance(value, bool):
            return value
        if isinstance(value, str):
            return str.__str__(value)
        if isinstance(value, int):
            return int.__int__(value)
        if isinstance(value, float):
            return float.__float__(value)
        if isinstance(value, (dict, list, tuple)):
            identity = id(value)
            if identity in ancestors:
                raise ValueError("Circular reference detected")
            ancestors.add(identity)
            try:
                if isinstance(value, dict):
                    result = {}
                    for key, item in value.items():
                        if isinstance(key, str):
                            key = str.__str__(key)
                        elif key is None or isinstance(key, (bool, int, float)):
                            key = json.dumps(key)
                        else:
                            raise TypeError(
                                f"keys must be str, int, float, bool or None, not {type(key).__name__}"
                            )
                        result[key] = copy_value(item)
                    return result
                return [copy_value(item) for item in value]
            finally:
                ancestors.remove(identity)
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    return copy_value(event)
