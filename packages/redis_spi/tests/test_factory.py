# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""factory.py 装配契约测试：四形态解析、错误分列、ping fail-fast。"""

import asyncio
import sys
import textwrap

import pytest

from redis_spi import registry
from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import RedisConfigError, RedisConnectionError
from redis_spi.factory import RedisProviderFactory, _looks_like_path
from redis_spi.protocols import RedisClient

from redis_spi_test_fakes import FakeRedisClient, FakeRedisProvider, FullSurfaceFakeClient

# ---------------------------------------------------------------- 协议可 fake（Phase 1 验收点）

PLUGIN_SOURCE = textwrap.dedent(
    """
    from redis_spi import RedisProvider
    from redis_spi.protocols import RedisClient


    class FromFileClient:
        text_mode = False

        async def ping(self):
            return True

        async def aclose(self):
            pass

        def supports(self, capability):
            return False

        def as_capability(self, capability):
            raise RuntimeError("not supported")


    class FromFileProvider(RedisProvider):
        async def start(self, settings):
            return FromFileClient()

        async def stop(self):
            pass
    """
)

# 无参实例化失败的 Provider（错误分列测试用）。
BAD_INIT_SOURCE = textwrap.dedent(
    """
    from redis_spi import RedisProvider


    class BadInitProvider(RedisProvider):
        def __init__(self):
            raise RuntimeError("init boom")

        async def start(self, settings):
            raise AssertionError("never started")

        async def stop(self):
            pass
    """
)


def test_fake_client_satisfies_protocol():
    # Phase 1 验收：Protocol 可被第三方 fake 实现（结构化满足，无需继承实现类）
    assert isinstance(FullSurfaceFakeClient(), RedisClient)


class TestLooksLikePath:
    @pytest.mark.parametrize(
        "spec",
        [
            "/opt/plugins/my_provider.py",
            "/opt/plugins/my_provider",
            r"D:\plugins\my_provider.py",
            "plugins/my_provider.py",
            "my_provider.py",
            # ".py:Class" 内联形态必须按路径处理（否则落入 module:Class 分支）
            "my_provider.py:Cls",
            "plugins/my_provider.py:Cls",
            # 盘符相对路径 + 内联类名（贪婪回溯后 path="D:x.py"）
            r"D:x.py:Cls",
        ],
    )
    def test_path_forms(self, spec):
        assert _looks_like_path(spec) is True

    @pytest.mark.parametrize(
        "spec", ["native", "my_plugin", "my_pkg.providers:MyProvider", "single:word"]
    )
    def test_non_path_forms(self, spec):
        assert _looks_like_path(spec) is False


class TestCreateWithRegisteredProvider:
    @staticmethod
    def test_create_via_registered_name():
        registry.register_provider("fake-registered", FakeRedisProvider)
        settings = RedisProviderSettings(REDIS_PROVIDER="fake-registered")
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert isinstance(client, FakeRedisClient)
        assert client.ping_calls == 1  # ping fail-fast 已执行

    @staticmethod
    def test_create_defaults_reads_env(monkeypatch):
        monkeypatch.setenv("REDIS_PROVIDER", "fake-registered")
        registry.register_provider("fake-registered", FakeRedisProvider)
        client = asyncio.run(RedisProviderFactory.create())
        assert isinstance(client, FakeRedisClient)

    @staticmethod
    def test_unknown_name_error_is_self_describing():
        registry.register_provider("known-one", FakeRedisProvider)
        settings = RedisProviderSettings(REDIS_PROVIDER="never-heard-of")
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        message = str(excinfo.value)
        # 1030 亮点吸收：报错必须带可用名全集 + 配置项与四种形态提示
        assert "never-heard-of" in message
        assert "native" in message
        assert "known-one" in message
        assert "REDIS_PROVIDER" in message


class TestCreateFromFileProvider:
    @staticmethod
    def test_explicit_py_suffix_with_provider_class(tmp_path):
        plugin = tmp_path / "file_provider.py"
        plugin.write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(
            REDIS_PROVIDER=str(plugin), REDIS_PROVIDER_CLASS="FromFileProvider"
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_inline_class_suffix(tmp_path):
        plugin = tmp_path / "file_provider.py"
        plugin.write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(
            REDIS_PROVIDER=f"{plugin}:FromFileProvider"
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_auto_py_suffix_appended(tmp_path):
        # /opt/plugins 约定：插件名不带 .py 时自动补后缀
        tmp_path.joinpath("auto_suffix.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(
            REDIS_PROVIDER=str(tmp_path / "auto_suffix"),
            REDIS_PROVIDER_CLASS="FromFileProvider",
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_bare_relative_file_resolved_from_cwd(tmp_path):
        # 裸相对文件名（无目录分隔符）：按 CWD 解析（conftest 已 chdir 到 tmp_path）
        (tmp_path / "my_provider.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(
            REDIS_PROVIDER="my_provider.py:FromFileProvider"
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_missing_file_lists_candidates(tmp_path):
        settings = RedisProviderSettings(
            REDIS_PROVIDER=str(tmp_path / "ghost"),
            REDIS_PROVIDER_CLASS="Whatever",
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "ghost" in str(excinfo.value)

    @staticmethod
    def test_missing_class_name_hint(tmp_path):
        plugin = tmp_path / "no_cls.py"
        plugin.write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(REDIS_PROVIDER=str(plugin))
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        message = str(excinfo.value)
        assert "类名" in message
        assert "REDIS_PROVIDER_CLASS" in message

    @staticmethod
    def test_class_not_found_in_file(tmp_path):
        plugin = tmp_path / "wrong_cls.py"
        plugin.write_text(PLUGIN_SOURCE, encoding="utf-8")
        settings = RedisProviderSettings(
            REDIS_PROVIDER=f"{plugin}:NoSuchClass"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "NoSuchClass" in str(excinfo.value)

    @staticmethod
    def test_class_not_inheriting_base(tmp_path):
        plugin = tmp_path / "bad_base.py"
        plugin.write_text(
            textwrap.dedent(
                """
                class NotAProvider:
                    pass
                """
            ),
            encoding="utf-8",
        )
        settings = RedisProviderSettings(
            REDIS_PROVIDER=f"{plugin}:NotAProvider"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "RedisProvider" in str(excinfo.value)


class TestCreateFromModule:
    @staticmethod
    def test_module_colon_class(tmp_path, monkeypatch):
        module_name = "_spi_factory_test_plugin"
        (tmp_path / f"{module_name}.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, module_name, raising=False)
        settings = RedisProviderSettings(
            REDIS_PROVIDER=f"{module_name}:FromFileProvider"
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_module_name_plus_class_env(tmp_path, monkeypatch):
        # OBS 命名对齐：模块名 + 类名分置两个 env
        module_name = "_spi_factory_test_plugin_obs"
        (tmp_path / f"{module_name}.py").write_text(PLUGIN_SOURCE, encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, module_name, raising=False)
        settings = RedisProviderSettings(
            REDIS_PROVIDER=module_name, REDIS_PROVIDER_CLASS="FromFileProvider"
        )
        client = asyncio.run(RedisProviderFactory.create(settings))
        assert type(client).__name__ == "FromFileClient"

    @staticmethod
    def test_missing_module_error_lists_available():
        settings = RedisProviderSettings(
            REDIS_PROVIDER="no_such_module_at_all:Cls"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "no_such_module_at_all" in str(excinfo.value)

    @staticmethod
    def test_module_import_crash_wrapped(tmp_path, monkeypatch):
        # 插件模块顶层抛异常（导入期崩溃）必须收口为 RedisConfigError，不得裸抛
        module_name = "_spi_factory_test_crash"
        (tmp_path / f"{module_name}.py").write_text(
            "raise RuntimeError('plugin top-level boom')\n", encoding="utf-8"
        )
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, module_name, raising=False)
        settings = RedisProviderSettings(REDIS_PROVIDER=f"{module_name}:Cls")
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        message = str(excinfo.value)
        assert module_name in message
        assert "导入时抛出异常" in message
        assert "boom" in message

    @staticmethod
    def test_module_class_instantiation_failure(tmp_path, monkeypatch):
        # 错误分列：类定位成功但无参实例化失败
        module_name = "_spi_factory_test_init_fail"
        (tmp_path / f"{module_name}.py").write_text(BAD_INIT_SOURCE, encoding="utf-8")
        monkeypatch.syspath_prepend(str(tmp_path))
        monkeypatch.delitem(sys.modules, module_name, raising=False)
        settings = RedisProviderSettings(
            REDIS_PROVIDER=f"{module_name}:BadInitProvider"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        message = str(excinfo.value)
        assert "实例化失败" in message
        assert "init boom" in message


class TestSpecConflicts:
    @staticmethod
    def test_native_with_class_env_rejected():
        settings = RedisProviderSettings(
            REDIS_PROVIDER="native", REDIS_PROVIDER_CLASS="Something"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "互斥" in str(excinfo.value)

    @staticmethod
    def test_inline_class_conflicts_with_class_env():
        settings = RedisProviderSettings(
            REDIS_PROVIDER="some_module:ClsA", REDIS_PROVIDER_CLASS="ClsB"
        )
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        assert "不一致" in str(excinfo.value)


class TestNativeShortCircuit:
    @staticmethod
    def test_native_missing_package_reports_install_hint(monkeypatch):
        # sys.modules[...] = None 强制 import 抛 ImportError（与是否真实安装无关）
        monkeypatch.setitem(sys.modules, "redis_native", None)
        settings = RedisProviderSettings(REDIS_PROVIDER="native")
        with pytest.raises(RedisConfigError) as excinfo:
            asyncio.run(RedisProviderFactory.create(settings))
        message = str(excinfo.value)
        assert "redis-native" in message
        assert "REDIS_PROVIDER" in message


class TestPingFailFast:
    @staticmethod
    def test_ping_failure_stops_provider():
        provider = _PingFailProvider()

        async def run():
            from redis_spi.factory import RedisProviderFactory as Factory

            return await Factory.create(
                RedisProviderSettings(REDIS_PROVIDER="ping-fail")
            )

        registry.register_provider("ping-fail", lambda: provider)
        with pytest.raises(RedisConnectionError):
            asyncio.run(run())
        # fail-fast：ping 失败必须回收 Provider（不留半初始化）
        assert provider.stopped is True

    @staticmethod
    def test_ping_returning_false_stops_provider():
        # ping 返回非 True（如 False）同样视为不健康，fail-fast 回收
        provider = _PingFalseProvider()

        async def run():
            return await RedisProviderFactory.create(
                RedisProviderSettings(REDIS_PROVIDER="ping-false")
            )

        registry.register_provider("ping-false", lambda: provider)
        with pytest.raises(RedisConnectionError) as excinfo:
            asyncio.run(run())
        assert provider.stopped is True
        assert "ping check returned" in str(excinfo.value)

    @staticmethod
    def test_start_returning_non_client_stops_provider():
        provider = _BadStartProvider()
        registry.register_provider("bad-start", lambda: provider)

        async def run():
            return await RedisProviderFactory.create(
                RedisProviderSettings(REDIS_PROVIDER="bad-start")
            )

        with pytest.raises(RedisConfigError):
            asyncio.run(run())
        assert provider.stopped is True


class _PingFailProvider(FakeRedisProvider):
    async def start(self, settings):
        client = FakeRedisClient()
        client.ping_error = ValueError("connection refused")
        return client


class _PingFalseProvider(FakeRedisProvider):
    async def start(self, settings):
        client = FakeRedisClient()
        client.ping_result = False
        return client


class _BadStartProvider(FakeRedisProvider):
    async def start(self, settings):
        return "not-a-client"  # type: ignore[return-value]
