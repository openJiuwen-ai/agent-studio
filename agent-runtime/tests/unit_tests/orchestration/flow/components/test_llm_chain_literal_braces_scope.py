# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""legacy orchestration LLM：allowLiteralBraces 不放宽校验（避免静默丢内容）。"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from jiuwen.orchestration.flow.components.llm_chain import LLMChain


def _make_chain(conf: dict | None = None) -> LLMChain:
    chain = object.__new__(LLMChain)
    setattr(chain, "_conf", conf or {})
    return chain


def _prompt_with_content(text: str):
    template = SimpleNamespace(content=text)
    return SimpleNamespace(template=template)


class TestLegacyValidateKeepsStrict:
    @staticmethod
    def test_rejects_non_safe_placeholder():
        chain = _make_chain({"allowLiteralBraces": True})
        with pytest.raises(ValueError, match="Invalid or dangerous placeholder"):
            getattr(chain, "_validate_prompt_instance")(
                _prompt_with_content("你好{{中文示例}}")
            )

    @staticmethod
    def test_rejects_empty_braces():
        chain = _make_chain({"allowLiteralBraces": True})
        with pytest.raises(ValueError, match="Invalid or dangerous placeholder"):
            getattr(chain, "_validate_prompt_instance")(_prompt_with_content("{{}}"))

    @staticmethod
    def test_allows_safe_identifier():
        chain = _make_chain({"allowLiteralBraces": True})
        getattr(chain, "_validate_prompt_instance")(
            _prompt_with_content("你好{{query}}")
        )

    @staticmethod
    def test_no_allow_literal_helper_on_legacy():
        chain = _make_chain()
        assert not hasattr(chain, "_allow_literal_braces")
