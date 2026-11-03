# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""registry.py 注册表契约测试。"""

import pytest

from redis_spi import registry
from redis_spi.exceptions import RedisConfigError


def _noop_factory():
    return object()


class TestRegister:
    @staticmethod
    def test_register_and_lookup():
        registry.register_provider("my-plugin", _noop_factory)
        assert registry.lookup("my-plugin") is _noop_factory

    @staticmethod
    def test_reserved_name_rejected():
        with pytest.raises(RedisConfigError):
            registry.register_provider("native", _noop_factory)

    @staticmethod
    def test_duplicate_rejected_without_force():
        registry.register_provider("dup", _noop_factory)
        with pytest.raises(RedisConfigError):
            registry.register_provider("dup", _noop_factory)

    @staticmethod
    def test_force_overrides():
        def replacement():
            return "replaced"

        registry.register_provider("dup", _noop_factory)
        registry.register_provider("dup", replacement, force=True)
        assert registry.lookup("dup") is replacement

    @staticmethod
    def test_non_callable_rejected():
        with pytest.raises(RedisConfigError):
            registry.register_provider("bad", "not-callable")  # type: ignore[arg-type]

    @staticmethod
    def test_empty_or_padded_name_rejected():
        with pytest.raises(RedisConfigError):
            registry.register_provider("", _noop_factory)
        with pytest.raises(RedisConfigError):
            registry.register_provider(" padded ", _noop_factory)

    @staticmethod
    def test_unregister():
        registry.register_provider("temp", _noop_factory)
        registry.unregister_provider("temp")
        assert registry.lookup("temp") is None
        # 未注册名 unregister 静默（幂等）
        registry.unregister_provider("never-registered")


class TestLookupPriority:
    @staticmethod
    def test_entry_points_beat_manual(monkeypatch):
        # 1030 亮点吸收口径：entry_points 注册表优先于手动注册
        def entry_point_factory():
            return "from-entry-points"

        registry.register_provider("same-name", _noop_factory)
        monkeypatch.setattr(
            registry, "_entry_points", lambda: {"same-name": _FakeEP(entry_point_factory)}
        )
        assert registry.lookup("same-name") is entry_point_factory

    @staticmethod
    def test_unknown_returns_none():
        assert registry.lookup("no-such-provider") is None


class TestAvailableNames:
    @staticmethod
    def test_includes_reserved_manual_and_entry_points(monkeypatch):
        registry.register_provider("z-manual", _noop_factory)
        monkeypatch.setattr(
            registry,
            "_entry_points",
            lambda: {"a-entrypoint": _FakeEP(_noop_factory)},
        )
        names = registry.available_names()
        assert "native" in names  # 保留名
        assert "z-manual" in names
        assert "a-entrypoint" in names
        assert names == sorted(names)


class TestEntryPointLoading:
    @staticmethod
    def test_reserved_name_entry_point_filtered(monkeypatch):
        # native 保留名不可被插件 entry_point 覆盖：发现期即过滤，永不加载
        class EvilEP:
            name = "native"
            value = "evil_module:NativeProvider"

            @staticmethod
            def load():
                raise AssertionError("reserved-name entry point must never load")

        monkeypatch.setattr(
            registry.metadata,
            "entry_points",
            lambda **kw: [EvilEP()] if kw.get("group") == registry.ENTRY_POINT_GROUP else [],
        )
        assert "native" not in getattr(registry, "_entry_points")()
        assert registry.lookup("native") is None

    @staticmethod
    def test_broken_entry_point_raises_config_error(monkeypatch):
        class BrokenEP:
            name = "broken"
            value = "bad_module:thing"

            @staticmethod
            def load():
                raise ImportError("no module named bad_module")

        monkeypatch.setattr(registry, "_entry_points", lambda: {"broken": BrokenEP()})
        with pytest.raises(RedisConfigError) as excinfo:
            registry.lookup("broken")
        # 报错自描述：含插件名与底层原因
        assert "broken" in str(excinfo.value)
        assert "bad_module" in str(excinfo.value)

    @staticmethod
    def test_non_callable_entry_point_rejected(monkeypatch):
        class NonCallableEP:
            name = "nc"
            value = "mod:VALUE"

            @staticmethod
            def load():
                return 42  # 非 callable

        monkeypatch.setattr(registry, "_entry_points", lambda: {"nc": NonCallableEP()})
        with pytest.raises(RedisConfigError):
            registry.lookup("nc")


class _FakeEP:
    """metadata.EntryPoint 替身（仅 load()）。"""

    def __init__(self, loaded):
        self.name = "fake"
        self.value = "fake_module:factory"
        self._loaded = loaded

    def load(self):
        return self._loaded
