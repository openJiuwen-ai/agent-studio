# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""intent_detection matcher 迁移回归锁（Phase 4 第五批）。

背景（断链根因）：老实现经 jiuwen 老 store 取连接——`DATASOURCE_REDIS_*` 独立
配置面 + SSL 默认开启，未配置环境（如 win-studio）下 `get_async_redis_instance()`
构造即抛 JiuWenBaseException（"ssl_passwd is necessary"），意图识别必失败。

迁移到 redis_spi accessor 后，本文件锁住三件事：
  1. 构造不依赖 DATASOURCE_REDIS_*（老实现的断链路径不再可达）；
  2. 客户端来自 accessor（redis_spi 单例）；
  3. 规则/示例/描述读取走 SPI 客户端语义（hgetall / hmget(list)）。
"""

import asyncio
import json
from unittest.mock import patch

import pytest

# 门禁环境未安装 fakeredis（且不按 pyproject dev 组装依赖）：缺包时跳过整个模块
# 而非 collect 失败；本地/装有 fakeredis 的环境照常执行
pytest.importorskip("fakeredis.aioredis")
import fakeredis.aioredis  # noqa: E402 依赖 importorskip 之后，确保缺包先跳过

from redis_native.client import NativeRedisClient

from jiuwen.common.intent_detection.config import LLMMatcherConfig, RuleMatcherConfig
from jiuwen.common.intent_detection.layers.llm_matcher import LLMMatcher
from jiuwen.common.intent_detection.layers.rule_matcher import RuleMatcher

#: 老实现的独立配置面环境变量——测试显式清空，证明新实现零依赖。
_DATASOURCE_REDIS_ENV = (
    "DATASOURCE_REDIS_HOST",
    "DATASOURCE_REDIS_PORT",
    "DATASOURCE_REDIS_PASSWORD",
    "DATASOURCE_REDIS_SSL_MODE",
    "DATASOURCE_REDIS_SSL_PASSWD",
    "DATASOURCE_REDIS_CLUSTER_NODE",
    "DATASOURCE_REDIS_MODE",
    "DATASOURCE_REDIS_TTL",
    "DATASOURCE_REDIS_DATABASE",
)


@pytest.fixture(autouse=True)
def _no_datasource_redis_env(monkeypatch):
    """清空老配置面：老实现在此环境下构造必炸（迁移回归锁的前提）。"""
    for name in _DATASOURCE_REDIS_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _jieba_tokenizer_pool():
    """RuleMatcher 构造依赖分词器池先初始化（生产链路由意图识别装配完成）。"""
    from jiuwen.common.intent_detection.utils.tokenizer import JiebaTokenizerPool

    JiebaTokenizerPool.initialize()
    yield


@pytest.fixture
def spi_client():
    """fakeredis 底座的 SPI 客户端（真实 NativeRedisClient 语义）。"""
    raw = fakeredis.aioredis.FakeRedis(decode_responses=False)
    return NativeRedisClient(raw), raw


class TestRuleMatcher:
    @staticmethod
    def test_construction_wired_to_accessor(spi_client):
        client, _ = spi_client
        with patch("redis_spi.accessor.get_redis", return_value=client):
            matcher = RuleMatcher(RuleMatcherConfig())
        assert matcher.redis_client is client

    @staticmethod
    def test_load_all_rules_reads_hash_via_spi(spi_client):
        client, raw = spi_client
        rules = {
            "greet": {"patterns": ["你好"], "responses": ["hi"]},
            "bye": {"patterns": ["再见"], "responses": ["bye"]},
        }
        asyncio.run(
            raw.hset(
                "intent_rules",
                mapping={k: json.dumps(v) for k, v in rules.items()},
            )
        )
        with patch("redis_spi.accessor.get_redis", return_value=client):
            matcher = RuleMatcher(RuleMatcherConfig())
        loaded = asyncio.run(getattr(matcher, "_load_all_rules")())
        assert loaded == rules

    @staticmethod
    def test_domain_rules_key_format(spi_client):
        client, _ = spi_client
        with patch("redis_spi.accessor.get_redis", return_value=client):
            matcher = RuleMatcher(RuleMatcherConfig())
        assert getattr(matcher, "_get_domain_rules_key")("sales") == "intent_rules:sales"


class TestLLMMatcher:
    @staticmethod
    def test_construction_wired_to_accessor(spi_client, monkeypatch):
        client, _ = spi_client
        # LLM 实例化与提示词模板不是本回归锁的对象（走模型配置/模板库）
        monkeypatch.setattr(LLMMatcher, "_get_llm_instance", lambda _: object())
        monkeypatch.setattr(LLMMatcher, "_get_prompt_template", lambda _: "tpl")

        with patch("redis_spi.accessor.get_redis", return_value=client):
            matcher = LLMMatcher(LLMMatcherConfig())
        assert matcher.redis_client is client

    @staticmethod
    def test_intent_examples_and_descriptions_read_via_hmget(spi_client, monkeypatch):
        client, raw = spi_client
        monkeypatch.setattr(LLMMatcher, "_get_llm_instance", lambda _: object())
        monkeypatch.setattr(LLMMatcher, "_get_prompt_template", lambda _: "tpl")

        with patch("redis_spi.accessor.get_redis", return_value=client):
            matcher = LLMMatcher(LLMMatcherConfig())

        example_key = matcher.llm_retrival_config.example_key
        description_key = matcher.llm_retrival_config.description_key
        asyncio.run(
            raw.hset(
                example_key,
                mapping={
                    "i1": json.dumps(["ex1", "ex2", "ex3", "ex4"]),
                    "i2": json.dumps(["ex5", "ex6", "ex7", "ex8"]),
                },
            )
        )
        asyncio.run(
            raw.hset(description_key, mapping={"i1": "意图一", "i2": "意图二"})
        )

        # hmget(list) 形态 + 缺失位语义
        examples = asyncio.run(getattr(matcher, "_get_intent_examples")(["i1", "missing", "i2"]))
        assert set(examples["i1"]) <= {"ex1", "ex2", "ex3", "ex4"}
        assert examples["missing"] == []
        assert set(examples["i2"]) <= {"ex5", "ex6", "ex7", "ex8"}

        descriptions = asyncio.run(getattr(matcher, "_get_intent_descriptions")(["i1", "missing"]))
        assert descriptions["i1"] == "意图一"
        assert descriptions["missing"] == ""
