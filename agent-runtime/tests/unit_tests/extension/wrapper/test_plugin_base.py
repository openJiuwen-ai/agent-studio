# coding: utf-8
# pylint: disable=protected-access
"""PluginBase 基类单元测试。

覆盖修改点 A1-A4：
- A1: __init__ 实例化（params + **config）
- A2: params / config 属性访问
- A3: invoke() 抽象方法契约
- A4: stream() 默认实现（降级为 invoke + json.dumps）
"""

import json

import pytest

from jiuwen.extension.wrapper.plugin_base import PluginBase
from jiuwen.plugin.models.param import Param


# --------------------------------------------------------------------------- #
# 测试用插件子类
# --------------------------------------------------------------------------- #

class _DummyPlugin(PluginBase):
    """最小化插件子类，仅实现 invoke。"""

    def __init__(self, params=None, **config):
        super().__init__(params, **config)
        self.invoke_called = False

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        self.invoke_called = True
        return {"echo": inputs}


class _StreamingPlugin(PluginBase):
    """带 stream 实现的插件子类。"""

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        return {"data": "ok"}

    async def stream(self, inputs: dict, **kwargs):
        yield "chunk1"
        yield "chunk2"


# --------------------------------------------------------------------------- #
# A1: __init__ 实例化
# --------------------------------------------------------------------------- #

def test_init_with_params():
    """A1: PluginBase(params=[...]) 实例化，_params 正确存储。"""
    p1 = Param(name="city", description="city name", param_type="string")
    plugin = _DummyPlugin(params=[p1])
    assert len(plugin._params) == 1
    assert plugin._params[0].name == "city"


def test_init_with_default_params():
    """A1: PluginBase() 无参实例化，_params 为 []。"""
    plugin = _DummyPlugin()
    assert plugin._params == []


def test_init_with_config():
    """A1: PluginBase(config_key="value") 的 **config 存储。"""
    plugin = _DummyPlugin(config_key="value", extra=42)
    assert plugin._config["config_key"] == "value"
    assert plugin._config["extra"] == 42


# --------------------------------------------------------------------------- #
# A2: params / config 属性
# --------------------------------------------------------------------------- #

def test_params_property():
    """A2: plugin.params 返回参数列表。"""
    p1 = Param(name="x", description="x", param_type="string")
    p2 = Param(name="y", description="y", param_type="integer")
    plugin = _DummyPlugin(params=[p1, p2])
    assert plugin.params == [p1, p2]
    assert plugin.params[0].name == "x"


def test_config_property():
    """A2: plugin.config 返回配置字典。"""
    plugin = _DummyPlugin(timeout=30, retry=True)
    assert plugin.config == {"timeout": 30, "retry": True}


# --------------------------------------------------------------------------- #
# A3: invoke 抽象方法契约
# --------------------------------------------------------------------------- #

def test_invoke_is_abstract():
    """A3: 直接实例化 PluginBase 抛 TypeError（ABC 不能实例化）。"""
    with pytest.raises(TypeError, match="abstract method"):
        PluginBase()


# --------------------------------------------------------------------------- #
# A4: stream 默认实现
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_stream_default_delegates_to_invoke():
    """A4: 子类只实现 invoke，stream 默认调用 invoke 并 json.dumps 结果。"""
    plugin = _DummyPlugin()
    inputs = {"city": "shenzhen"}
    chunks = []
    async for chunk in plugin.stream(inputs):
        chunks.append(chunk)
    assert plugin.invoke_called is True
    assert len(chunks) == 1


@pytest.mark.asyncio
async def test_stream_default_returns_json_string():
    """A4: stream yield 的是 JSON 字符串，ensure_ascii=False。"""
    plugin = _DummyPlugin()
    inputs = {"city": "深圳"}
    chunks = []
    async for chunk in plugin.stream(inputs):
        chunks.append(chunk)
    expected = json.dumps({"echo": {"city": "深圳"}}, ensure_ascii=False)
    assert chunks[0] == expected
    # ensure_ascii=False 保证中文原样输出
    assert "深圳" in chunks[0]
