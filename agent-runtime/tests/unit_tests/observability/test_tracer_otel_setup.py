# -*- coding: UTF-8 -*-
# pylint: disable=protected-access  # 单测需直接验证内部函数与成员
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

"""setup_otel_tracer 导入隔离/回退单测。

M1 评审关注点固化：StudioOtelWorkflowHandler 子类导入失败（openjiuwen 升级后
私有符号缺失/改名）时，回退官方 OtelWorkflowHandler，OTel 不静默停用。
"""
import builtins
import threading
import time
from unittest.mock import MagicMock

import pytest

from openjiuwen.core.session.tracer import TracerHandlerRegistry
from openjiuwen.extensions.tracer_otel.handler import OtelWorkflowHandler

import agent_runtime.observability.tracer_otel as tracer_otel_mod

_real_import = builtins.__import__


def _block_studio_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    if (
        name == "agent_runtime.observability.tracer_otel_studio"
        and fromlist
        and "StudioOtelWorkflowHandler" in fromlist
    ):
        raise ImportError("simulated: upstream private symbol missing")
    return _real_import(name, gdict, ldict, fromlist, level)


@pytest.mark.asyncio
async def test_fallbacks_to_official_handler_when_studio_unavailable(monkeypatch):
    prev_enabled = tracer_otel_mod.settings.otel.enabled
    tracer_otel_mod.settings.otel.enabled = True
    monkeypatch.setattr(builtins, "__import__", _block_studio_import)
    try:
        TracerHandlerRegistry.clear()
        tracer_otel_mod.setup_otel_tracer()
        handlers = TracerHandlerRegistry.get_workflow_handlers()
        assert isinstance(handlers.get("otel_workflow"), OtelWorkflowHandler)
    finally:
        tracer_otel_mod.settings.otel.enabled = prev_enabled
        TracerHandlerRegistry.clear()


def _block_extension_import(name, gdict=None, ldict=None, fromlist=(), level=0):
    """模拟未安装 openjiuwen[tracer-otel] 扩展。"""
    if name == "openjiuwen.extensions.tracer_otel":
        raise ImportError("simulated: tracer-otel extension not installed")
    return _real_import(name, gdict, ldict, fromlist, level)


class TestSetupOtelTracerSingleton:
    """setup_otel_tracer 幂等单例、关闭降级、扩展缺失降级。"""

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        """每个用例前的全局单例/注册表复原，避免用例间相互污染。"""
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()

    @staticmethod
    def test_returns_none_without_creating_tracer_when_disabled(monkeypatch):
        """OTEL_ENABLED=false：返回 None、不创建 tracer，get_otel_tracer 同步为 None。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", False)
        init_mock = MagicMock()
        monkeypatch.setattr(
            "openjiuwen.extensions.tracer_otel.init_otel_tracer", init_mock
        )

        assert tracer_otel_mod.setup_otel_tracer() is None
        assert tracer_otel_mod.get_otel_tracer() is None
        init_mock.assert_not_called()

    @staticmethod
    def test_creates_once_and_returns_same_instance(monkeypatch):
        """首次调用创建 tracer 并按 settings 注册 handler；重复调用返回同一实例且只初始化一次。"""
        import openjiuwen.extensions.tracer_otel as extension

        fake_tracer = MagicMock(name="fake-otel-tracer")
        init_mock = MagicMock(return_value=fake_tracer)
        monkeypatch.setattr(extension, "init_otel_tracer", init_mock)
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)

        first = tracer_otel_mod.setup_otel_tracer()
        second = tracer_otel_mod.setup_otel_tracer()

        assert first is fake_tracer
        assert second is fake_tracer
        init_mock.assert_called_once()
        # 入参必须是按当前 settings 组装的配置，而不是默认值
        config = init_mock.call_args[0][0]
        assert isinstance(config, extension.OtelTracerConfig)
        assert config.service_name == tracer_otel_mod.settings.otel.service_name
        assert config.sample_rate == tracer_otel_mod.settings.otel.sample_rate
        assert tracer_otel_mod.get_otel_tracer() is fake_tracer
        assert "otel_agent" in TracerHandlerRegistry.get_agent_handlers()
        assert "otel_workflow" in TracerHandlerRegistry.get_workflow_handlers()

    @staticmethod
    def test_returns_none_when_extension_not_installed(monkeypatch):
        """扩展缺失（ImportError）：返回 None 而不是抛错，调用方跳过自建 span。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)
        monkeypatch.setattr(builtins, "__import__", _block_extension_import)

        assert tracer_otel_mod.setup_otel_tracer() is None
        assert tracer_otel_mod.get_otel_tracer() is None

    @staticmethod
    def test_skips_creation_when_handlers_already_registered(monkeypatch):
        """handler 已注册（进程内重复初始化）：直接返回、不再创建 tracer 与重复注册。"""
        monkeypatch.setattr(tracer_otel_mod.settings.otel, "enabled", True)
        init_mock = MagicMock()
        monkeypatch.setattr(
            "openjiuwen.extensions.tracer_otel.init_otel_tracer", init_mock
        )
        monkeypatch.setattr(
            TracerHandlerRegistry,
            "get_agent_handlers",
            classmethod(lambda cls: {"otel_agent": object()}),
        )

        assert tracer_otel_mod.setup_otel_tracer() is None
        init_mock.assert_not_called()


class TestSetupOtelTracerThreadSafety:
    """setup_otel_tracer 的双层检查锁：并发只创建一次、已缓存时不进锁也不重建。"""

    @pytest.fixture(autouse=True)
    def _clean_global_state(self, monkeypatch):
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", None)
        TracerHandlerRegistry.clear()
        yield
        TracerHandlerRegistry.clear()

    @staticmethod
    def test_create_runs_once_under_concurrent_calls(monkeypatch):
        """8 线程同时调用：_create_otel_tracer 只执行一次，所有调用方拿到同一实例。"""
        fake_tracer = MagicMock(name="thread-safe-tracer")
        create_calls = []
        counter_lock = threading.Lock()

        def fake_create():
            with counter_lock:
                create_calls.append(1)
            # 放大竞态窗口：若没有锁，其余线程会在这里再次进入创建逻辑
            time.sleep(0.05)
            tracer_otel_mod._otel_tracer = fake_tracer
            return fake_tracer

        monkeypatch.setattr(tracer_otel_mod, "_create_otel_tracer", fake_create)

        thread_count = 8
        barrier = threading.Barrier(thread_count)
        results = []
        errors = []

        def worker():
            try:
                barrier.wait(timeout=10)
                results.append(tracer_otel_mod.setup_otel_tracer())
            except BaseException as exc:  # noqa: BLE001 - 线程异常必须回传主线程
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=10)

        assert errors == []
        assert len(results) == thread_count
        assert len(create_calls) == 1
        assert all(result is fake_tracer for result in results)
        assert tracer_otel_mod.get_otel_tracer() is fake_tracer

    @staticmethod
    def test_cached_tracer_short_circuits_without_creating(monkeypatch):
        """已缓存实例：直接返回缓存并跳过创建（双层检查的外层快速路径）。"""
        cached = MagicMock(name="cached-tracer")
        create_mock = MagicMock(name="_create_otel_tracer")
        monkeypatch.setattr(tracer_otel_mod, "_otel_tracer", cached)
        monkeypatch.setattr(tracer_otel_mod, "_create_otel_tracer", create_mock)

        assert tracer_otel_mod.setup_otel_tracer() is cached
        assert tracer_otel_mod.setup_otel_tracer() is cached
        create_mock.assert_not_called()