# coding: utf-8
# pylint: disable=protected-access
"""模板转换节点必须能从 IR 创建出来，否则单节点调试会报 101040。"""

import asyncio
import sys
from unittest.mock import MagicMock

for _mod_name in ("model_service", "model_service.env_resolver"):
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock()

from agent_runtime.extension.workflow_node.flow_template_transform import FlowTemplateTransform
from jiuwen.serve.controllers.execution.ir_converter import IRConverter


def test_create_component_maps_template_transform():
    node = {
        "id": "node_tt",
        "name": "模板转换",
        "type": "jiuwen.templateTransform",
        "configs": {
            "template": "用户名称：{{ data.get('customerName') }}",
            "userFields": {
                "inputs": [{"id": "data", "type": "object"}],
                "outputs": [{"id": "output", "type": "string"}],
            },
        },
    }

    component, node_type, configs = asyncio.run(IRConverter._create_component(node, None))

    assert node_type == "jiuwen.templateTransform"
    assert isinstance(component, FlowTemplateTransform)
    assert component.component_type() == "jiuwen.templateTransform"
    assert configs.get("template") == "用户名称：{{ data.get('customerName') }}"
    assert configs.get("userFields", {}).get("inputs", [])[0]["id"] == "data"
