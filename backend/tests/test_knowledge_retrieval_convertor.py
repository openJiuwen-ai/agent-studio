#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""知识检索节点转换：min_match_score=0 必须按 0 编译，不得被默认值 0.5 覆盖。"""

from __future__ import annotations

import os
from pathlib import Path

# 先于 openjiuwen_studio 导入设置 Settings 必需环境变量（与 test_vlm_model_config.py 一致）
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("SQLITE_DB_PATH", str(Path(__file__).resolve().parent / ".tmp-db"))
os.environ.setdefault("OPS_SQLITE_DB", "ops-test.db")
os.environ.setdefault("AGENT_SQLITE_DB", "agent-test.db")

from openjiuwen_studio.core.manager.convertor.components.knowledge_retrieval import (
    knowledge_retrieval_convert,
)
from openjiuwen_studio.schemas.node import Node


def _make_node(min_match_score) -> Node:
    return Node.model_validate(
        {
            "id": "kr_1",
            "meta": {"position": {"x": 0, "y": 0}},
            "data": {
                "title": "kb",
                "inputs": {
                    "knowledge_retrieval_param": {
                        "kb_ids": ["kb-1"],
                        "max_recall_count": 5,
                        "min_match_score": min_match_score,
                        "use_graph": False,
                        "agentic": False,
                    },
                    "input_parameters": {},
                },
                "outputs": {"type": "string"},
            },
        }
    )


def test_zero_score_threshold_is_preserved():
    """前端滑块允许 0；0 表示不过滤，不能被 or 兜底成 0.5。"""
    component = knowledge_retrieval_convert(_make_node(0), space_id="space-1")
    assert component.configs["retrieval_config"]["score_threshold"] == 0


def test_missing_score_threshold_falls_back_to_default():
    """未配置（None）时仍取默认 0.5。"""
    component = knowledge_retrieval_convert(_make_node(None), space_id="space-1")
    assert component.configs["retrieval_config"]["score_threshold"] == 0.5


def test_explicit_score_threshold_is_preserved():
    component = knowledge_retrieval_convert(_make_node(0.8), space_id="space-1")
    assert component.configs["retrieval_config"]["score_threshold"] == 0.8
