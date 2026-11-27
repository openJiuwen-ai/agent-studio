# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""RedisProvider 基类 + RedisProviderFactory（设计文档 5.1）。

职责：
  - RedisProvider（ABC）：企业自研 Provider 的唯一继承基类；
  - RedisProviderFactory.create()：按 RedisProviderSettings 解析并装配客户端，
    解析优先级（1030 亮点吸收）::

        显式配置（native / 模块：Class / 文件路径）
          > entry_points 注册表（同名可覆盖内置实现）
          > 内置保留实现（native 为保留名，不可被插件覆盖）

  - 报错自描述（1030 亮点吸收）：名字解析失败必须列出可用名全集与注入方式提示；
    插件加载失败按（模块不存在 / 类不存在 / 未继承基类 / 实例化失败）分列原因。
  - 装配后 ping fail-fast：ping 不通即抛错并回收 Provider（不留半初始化状态）。

导入方向约束：redis_spi 不依赖 redis_native / redis-py；native 为延迟导入
（运行环境需安装 redis-native 包，缺失时报可操作错误）。
"""

from __future__ import annotations

import importlib
import importlib.util
import re
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from redis_spi import registry
from redis_spi.config import RedisProviderSettings
from redis_spi.exceptions import (
    CapabilityNotSupportedError,
    RedisConfigError,
    RedisConnectionError,
    RedisError,
)
from redis_spi.protocols import RedisClient

#: "path/to/file.py:ClassName" 形态的类名后缀。
_INLINE_CLASS_RE = re.compile(r"^(?P<path>.*\.py):(?P<cls>[A-Za-z_]\w*)$")


class RedisProvider(ABC):
    """企业自研 Provider 基类。

    生命周期：factory 调用 start() 产出客户端；ping 失败或服务下线时调 stop()
    回收。实现必须可在无 Redis 连接的环境下 import（延迟建连放在 start 内）。
    """

    @abstractmethod
    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        """创建并返回客户端（含连接池初始化）。

        实现须把 settings.text_mode 固化到客户端；settings.raw_provider_config()
        透传实现专属参数。抛出 RedisError 体系异常（配置类错误用 RedisConfigError）。
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """回收全部资源（幂等；factory 在 ping 失败/服务下线时调用）。"""
        ...

    def capabilities(self) -> list[type]:
        """声明支持的可选能力组（capabilities.py 中的 Protocol 类）。默认无。"""
        return []

    def native_client(self) -> Any:
        """暴露底层原生客户端（过渡期 agent-core 兼容注入用，Q3）。

        默认抛 CapabilityNotSupportedError——仅提供 native 兼容注入的实现覆写。
        """
        raise CapabilityNotSupportedError(
            f"provider {type(self).__name__} does not expose a native client",
            capability="native_client",
        )


class RedisProviderFactory:
    """按配置解析 Provider 并装配客户端（唯一装配入口）。"""

    @staticmethod
    async def create(settings: RedisProviderSettings | None = None) -> RedisClient:
        """解析 Provider → start() → ping() 校验 → 返回客户端。

        - 未显式传 settings 时从环境构造（REDIS_PROVIDER 等）；
        - ping 失败自动 stop() 回收 Provider 后抛错（不留半初始化）；
        - start/ping 的非 RedisError 异常分别包装为 RedisConfigError /
          RedisConnectionError（保留 __cause__）。
        """
        effective = settings if settings is not None else RedisProviderSettings()
        provider = _resolve_provider(effective)
        try:
            client = await provider.start(effective)
        except RedisError:
            raise
        except Exception as exc:  # noqa: BLE001 - 边界统一包装
            raise RedisConfigError(
                f"provider {type(provider).__name__} failed to start: {exc}"
            ) from exc
        missing = _client_missing_members(client)
        if missing:
            await _safe_stop(provider)
            raise RedisConfigError(
                f"provider {type(provider).__name__}.start() returned "
                f"{type(client).__name__} which is not a usable RedisClient "
                f"(missing: {', '.join(missing)})"
            )
        try:
            ping_ok = await client.ping()
        except RedisError:
            await _safe_stop(provider)
            raise
        except Exception as exc:  # noqa: BLE001
            await _safe_stop(provider)
            raise RedisConnectionError(
                f"provider {type(provider).__name__} ping check failed: {exc}"
            ) from exc
        if ping_ok is not True:
            # ping 返回非 True（如 False）同样视为不健康：fail-fast，不留半初始化
            await _safe_stop(provider)
            raise RedisConnectionError(
                f"provider {type(provider).__name__} ping check returned "
                f"{ping_ok!r} (expected True)"
            )
        return client


# ---------------------------------------------------------------- internal


def _resolve_provider(settings: RedisProviderSettings) -> RedisProvider:
    """按 REDIS_PROVIDER 取值形态解析 Provider 实例（5.1 优先级）。"""
    spec = (settings.provider or "").strip()
    if not spec:
        spec = "native"

    if spec == "native":
        if settings.provider_class:
            raise RedisConfigError(
                "REDIS_PROVIDER=native 与 REDIS_PROVIDER_CLASS 互斥："
                "native 为内置实现，无需指定类名（请清空 REDIS_PROVIDER_CLASS）"
            )
        return _load_native()

    if _looks_like_path(spec):
        match = _INLINE_CLASS_RE.match(spec)
        if match:
            path_part, inline_cls = match.group("path"), match.group("cls")
            _check_class_conflict(inline_cls, settings.provider_class)
            return _load_from_path(Path(path_part), inline_cls)
        return _load_from_path(Path(spec), settings.provider_class or None)

    if ":" in spec:
        module_part, _, inline_cls = spec.partition(":")
        if not module_part or not inline_cls:
            raise RedisConfigError(
                f"invalid REDIS_PROVIDER '{spec}': 'module:Class' 形态要求"
                f"模块名与类名均非空"
            )
        _check_class_conflict(inline_cls, settings.provider_class)
        return _load_importlib(module_part, inline_cls)

    if settings.provider_class:
        # OBS 命名对齐：模块名（REDIS_PROVIDER）+ 类名（REDIS_PROVIDER_CLASS）分置。
        return _load_importlib(spec, settings.provider_class)

    return _lookup_registered(spec)


def _looks_like_path(spec: str) -> bool:
    """路径形态判定：``.py:Class`` 后缀 / 绝对路径 / 含路径分隔符 / .py 后缀。

    ``.py:Class`` 必须显式判定——形如 ``my_provider.py:Cls``（无目录分隔符）
    否则会落入 module:Class 分支被 import_module 误解析。
    """
    return (
        bool(_INLINE_CLASS_RE.match(spec))
        or spec.endswith(".py")
        or "/" in spec
        or "\\" in spec
    )


def _check_class_conflict(inline_cls: str, provider_class: str) -> None:
    if provider_class and provider_class != inline_cls:
        raise RedisConfigError(
            f"REDIS_PROVIDER 内联类名 '{inline_cls}' 与 "
            f"REDIS_PROVIDER_CLASS='{provider_class}' 不一致，请只保留一处"
        )


def _load_native() -> RedisProvider:
    """内置 native 短路（保留名；redis_native 延迟导入）。"""
    try:
        from redis_native import NativeRedisProvider  # 延迟导入避免包依赖环
    except ImportError as exc:
        raise RedisConfigError(
            "native provider 需要 redis-native 包（内置 redis-py 实现）："
            "请安装 redis-native，或将 packages/redis_native 加入运行路径；"
            "企业自研实现请设置 REDIS_PROVIDER 指向你的插件"
        ) from exc
    return NativeRedisProvider()


def _load_from_path(path: Path, class_name: str | None) -> RedisProvider:
    """从 .py 文件加载 Provider 类（缺 .py 后缀自动补；/opt/plugins 约定对齐）。"""
    # 追加而非替换后缀（Path.with_suffix 会把 my.plugin 变成 my.py）
    candidates = [path] if path.suffix == ".py" else [path.with_name(path.name + ".py"), path]
    file_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if file_path is None:
        raise RedisConfigError(
            f"REDIS_PROVIDER 文件不存在：尝试过 {', '.join(str(c) for c in candidates)}"
        )
    if not class_name:
        raise RedisConfigError(
            f"从文件加载 Provider 需要类名：请在 REDIS_PROVIDER 中内联"
            f"（{str(file_path)}:ClassName）或设置 REDIS_PROVIDER_CLASS"
        )
    # 模块名带路径指纹：同 stem 不同目录的插件不得互相覆盖 sys.modules
    sanitized_stem = re.sub(r"\W", "_", file_path.stem)
    path_tag = hash(str(file_path.resolve())) & 0xFFFFFFFF
    module_name = f"redis_spi_plugin_{sanitized_stem}_{path_tag:x}"
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RedisConfigError(f"无法为插件文件创建导入 spec：{file_path}")
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        sys.modules.pop(module_name, None)
        raise RedisConfigError(f"插件文件执行失败 {file_path}: {exc}") from exc
    return _instantiate(getattr(module, class_name, None), class_name, f"file {file_path}")


def _load_importlib(module_name: str, class_name: str) -> RedisProvider:
    """从已安装模块加载 Provider 类。"""
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RedisConfigError(
            f"REDIS_PROVIDER 模块不存在或导入失败：'{module_name}'（{exc}）。"
            f"可用 Provider 名：{registry.available_names()}"
        ) from exc
    except Exception as exc:  # noqa: BLE001 - 插件导入期崩溃统一收口（含原生异常）
        raise RedisConfigError(
            f"REDIS_PROVIDER 模块 '{module_name}' 导入时抛出异常："
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return _instantiate(getattr(module, class_name, None), class_name, f"module {module_name}")


def _lookup_registered(name: str) -> RedisProvider:
    """注册名解析（entry_points > 手动注册；未知名自描述报错）。"""
    factory = registry.lookup(name)
    if factory is None:
        raise RedisConfigError(
            f"未知的 Redis Provider：'{name}'。"
            f"可用：{registry.available_names()}。"
            "REDIS_PROVIDER 支持四种形态：native / module:Class / "
            "/path/file.py:Class（文件路径）/ entry_points 注册名"
            f"（组 {registry.ENTRY_POINT_GROUP}，或测试用 register_provider 注入）"
        )
    try:
        instance = factory()
    except Exception as exc:  # noqa: BLE001
        raise RedisConfigError(
            f"Provider '{name}' 工厂实例化失败：{exc}"
        ) from exc
    return _validate_provider(instance, name)


def _instantiate(cls: Any, class_name: str, source: str) -> RedisProvider:
    """定位到的类 → 校验继承 → 无参实例化（错误分列：类不存在/未继承/实例化失败）。"""
    if cls is None:
        raise RedisConfigError(f"Provider 类不存在：'{class_name}'（{source}）")
    if not (isinstance(cls, type) and issubclass(cls, RedisProvider)):
        raise RedisConfigError(
            f"'{class_name}'（{source}）未继承 redis_spi.RedisProvider"
        )
    try:
        instance = cls()
    except Exception as exc:  # noqa: BLE001
        raise RedisConfigError(
            f"Provider '{class_name}'（{source}）无参实例化失败：{exc}"
        ) from exc
    return _validate_provider(instance, class_name)


def _validate_provider(instance: Any, name: str) -> RedisProvider:
    if not isinstance(instance, RedisProvider):
        raise RedisConfigError(
            f"Provider '{name}' 实例类型 {type(instance).__name__} 未继承 "
            f"redis_spi.RedisProvider"
        )
    return instance


def _client_missing_members(client: Any) -> list[str]:
    """客户端可用性轻校验（生命周期面）。

    只校验工厂运行所需的最小面（ping/aclose/supports/as_capability/text_mode）；
    完整方法面与语义正确性由契约套件（redis_contract_tests）跑批验证——
    语义校验不是装配边界的职责。
    """
    missing = [
        name
        for name in ("ping", "aclose", "supports", "as_capability")
        if not callable(getattr(client, name, None))
    ]
    if not hasattr(client, "text_mode"):
        missing.append("text_mode")
    return missing


async def _safe_stop(provider: RedisProvider) -> None:
    """回收 Provider；stop 自身异常不吞掉原错误（附注在 __cause__ 链外）。"""
    try:
        await provider.stop()
    except Exception:  # noqa: BLE001 - 回收失败不应掩盖装配错误
        pass
