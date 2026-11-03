# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""redis_contract_tests：Provider 无关契约/一致性测试套件（设计文档 §七）。

用法（企业自研 Provider 接入验收——目标是注入的，套件本身零业务耦合）::

    REDIS_CONTRACT_TARGET=<target> python -m pytest --pyargs redis_contract_tests -v

目标四种形态（同 redis_spi.factory 解析规则）：

  =======================  ============================================  ==========
  后端                      REDIS_CONTRACT_TARGET                          依赖
  =======================  ============================================  ==========
  委托层替身（CI 默认）      redis_contract_tests.stub_backend:StubRedisProvider  redis-native
  demo·fakeredis 形态       acme_demo（entry_points）或 module:Class        redis-demo-provider
  demo·Wrapper 形态         redis_demo_provider.wrapper:WrapperDemoProvider redis-demo-provider
  native·真实实例           native（+ REDIS_HOST/PORT/PASSWORD 等连接 env）  redis-native + 实例
  企业自研实例              /path/provider.py:MyProvider 或 module:Class     企业提供
  =======================  ============================================  ==========

跑批口径：
  - 核心面（Key/String/Hash/List/Set/Scan/Pipeline/错误映射）全部后端必过；
  - 能力组（test_capability_contract）按 Provider ``supports()`` 声明跑批：
    声明的组必须通过，未声明的组自动 skip——"实现多少声明多少"的可测试承诺；
  - 坏端口连接错误用例自分类：离线后端（fakeredis/替身）自动 skip；
  - 每用例独立 key 前缀（contract:<uuid>:）+ 会话末全量清理（SCAN 到 0 + 分批 DEL）。

Phase 3 全量矩阵已落地：核心语义/TTL 哨兵/SCAN 游标不变量/Pipeline 事务
差异与入队期校验/错误映射（WRONGTYPE→RedisWrongTypeError、客户端校验
fail-fast、坏端口→RedisConnectionError）/八能力组（PubSub 独立订阅池冒烟、
Blocking 超时语义、Lua 引擎探测）。
"""
