# -*- coding: UTF-8 -*-
"""adapt_react_agent_config 单测。"""

from agent_runtime.common.model_adapters import adapt_react_agent_config


class TestAdaptReactAgentConfig:
    @staticmethod
    def test_extracts_model_field():
        """LLMReAct 节点 configs.model → 标准化 {"configs":{"model":{...}}}。"""
        configs = {
            "systemPrompt": "{{user_query}}",
            "model": {"modelName": "maas-deeseek-v32|x", "extension": {"authId": "aid"}},
            "plugins": [],
            "maxIteration": 9,
        }
        result = adapt_react_agent_config(configs)
        assert result == {
            "configs": {
                "model": {
                    "modelName": "maas-deeseek-v32|x",
                    "extension": {"authId": "aid"},
                }
            }
        }

    @staticmethod
    def test_missing_model_returns_empty():
        """model 缺失 → model 为空 dict（不抛错，交给 provider 兜底）。"""
        result = adapt_react_agent_config({"systemPrompt": "x"})
        assert result == {"configs": {"model": {}}}

    @staticmethod
    def test_does_not_leak_other_fields():
        """systemPrompt/plugins/maxIteration 不进入 adapter 输出。"""
        result = adapt_react_agent_config(
            {
                "systemPrompt": "s",
                "plugins": [1],
                "maxIteration": 5,
                "model": {"modelName": "m"},
            }
        )
        assert "systemPrompt" not in result["configs"]
        assert "plugins" not in result["configs"]
        assert result["configs"]["model"] == {"modelName": "m"}
