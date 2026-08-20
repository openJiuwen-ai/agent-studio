# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
"""ReactFileReaderAdapter._read_pdf 单测 — 覆盖 G.PRM.03：pymupdf.open 后 doc.close() 成对释放。"""

import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from agent_runtime.runner.react_file_reader_adapter import ReactFileReaderAdapter


def _install_fake_pymupdf(doc):
    """注入伪造 pymupdf 模块，其 open() 返回 doc（MagicMock）。"""
    fake = ModuleType("pymupdf")

    def _open(path):
        return doc

    fake.open = _open
    sys.modules["pymupdf"] = fake
    return fake


def _make_doc(pages):
    """构造一个可迭代的 doc 伪对象。"""
    doc = MagicMock()
    doc.__iter__.return_value = iter(pages)
    return doc


@pytest.fixture(autouse=True)
def _remove_pymupdf():
    """每个用例前后清理 pymupdf 模块，避免真实/伪造模块互相干扰。"""
    sys.modules.pop("pymupdf", None)
    yield
    sys.modules.pop("pymupdf", None)


class TestReadPdfClosesDoc:
    def test_close_called_after_read(self):
        page = MagicMock()
        page.get_text.return_value = "page1"
        doc = _make_doc([page])
        _install_fake_pymupdf(doc)
        adapter = ReactFileReaderAdapter()
        text = adapter._read_pdf("dummy.pdf")
        assert text == "page1"
        doc.close.assert_called_once()

    def test_close_called_even_when_page_get_text_raises(self):
        # 读取过程抛异常时，finally 仍必须 close（G.PRM.03 异常场景）
        page = MagicMock()
        page.get_text.side_effect = RuntimeError("boom")
        doc = _make_doc([page])
        _install_fake_pymupdf(doc)
        adapter = ReactFileReaderAdapter()
        with pytest.raises(RuntimeError):
            adapter._read_pdf("dummy.pdf")
        doc.close.assert_called_once()

    def test_returns_message_when_pymupdf_missing(self):
        # pymupdf 未安装 → ImportError 友好提示，不应抛异常
        adapter = ReactFileReaderAdapter()
        text = adapter._read_pdf("dummy.pdf")
        assert "pymupdf" in text
