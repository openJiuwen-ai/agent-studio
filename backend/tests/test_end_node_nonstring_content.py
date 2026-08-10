# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""Unit tests for End node conversion with non-string content (issue #1282).

A plugin node may emit a non-string payload (dict / list / number) into the
End node's ``content``. ``end_convert`` must normalize it to a string so the
``response_template`` stays serializable and the second dialogue round loads.
"""

import pytest

from openjiuwen_studio.core.manager.convertor.components.end import end_convert
from openjiuwen_studio.core.common.dsl import ComponentType
from openjiuwen_studio.schemas.node import (
    Content,
    Inputs,
    Meta,
    Node,
    NodeData,
    NodePosition,
)


def _make_end_node(content_value) -> Node:
    """Build an End node whose content carries the given payload."""
    return Node(
        id="end-1",
        meta=Meta(position=NodePosition(x=0, y=0), node_id="end-1", name="End", type="end"),
        data=NodeData(
            title="End",
            inputs=Inputs(
                input_parameters={},
                content=Content(content=content_value),
                streaming=False,
            ),
        ),
    )


def test_end_convert_accepts_string_content():
    node = _make_end_node("hello world")
    component = end_convert(node)
    assert component.type == ComponentType.COMPONENT_TYPE_END
    assert component.configs["response_template"] == "hello world"


def test_end_convert_normalizes_dict_content_to_string():
    node = _make_end_node({"key": "value"})
    component = end_convert(node)
    assert component.type == ComponentType.COMPONENT_TYPE_END
    template = component.configs["response_template"]
    assert isinstance(template, str)
    assert "key" in template


def test_end_convert_normalizes_number_content_to_string():
    node = _make_end_node(12345)
    component = end_convert(node)
    template = component.configs["response_template"]
    assert isinstance(template, str)
    assert template == "12345"


def test_end_convert_handles_none_content_gracefully():
    node = _make_end_node(None)
    component = end_convert(node)
    assert component.configs["response_template"] == ""


def test_end_convert_keeps_serializable_configs_for_non_string_content():
    # Regression guard: the dumped configs must be JSON-serializable even when
    # the raw payload was a dict (the second dialogue round re-reads these).
    import json

    node = _make_end_node({"a": [1, 2, 3]})
    component = end_convert(node)
    json.dumps(component.configs)  # must not raise
    assert isinstance(component.configs["response_template"], str)
