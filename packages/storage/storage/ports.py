# -*- coding: utf-8 -*-
"""对象存储配置注入端口 — 宿主（agent_runtime / agent_builder）启动时注入 settings。

共享存储层不 import 任何宿主；OBS 连接参数（server/bucket/ak/sk/ssl/path_style）由宿主
经 ``set_settings(factory)`` 注入。未注入而调用 ``get_settings()`` 抛 RuntimeError（fail-fast）。
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol, runtime_checkable


@runtime_checkable
class ObjectStorageSettingsLike(Protocol):
    """OBS 配置协议（agent_runtime / agent_builder 的 settings.object_storage 均符合）。"""

    server: str
    bucket: str
    access_key: str
    secret_key: str
    enable_ssl: bool
    path_style: str
    # CUSTOM 存储类型 + Local 重构（对齐远程 OBS 存储扩展 f00cd2ba）
    type: str               # STORAGE_TYPE: OBS / LOCAL / CUSTOM
    custom_module: str      # STORAGE_CUSTOM_MODULE
    custom_class: str       # STORAGE_CUSTOM_CLASS
    local_base_path: str
    local_bucket: str


_settings_factory: Optional[Callable[[], ObjectStorageSettingsLike]] = None


def set_settings(factory: Optional[Callable[[], ObjectStorageSettingsLike]]) -> None:
    """注册 settings 工厂（每次 get_storage_provider 时调用）。"""
    global _settings_factory
    _settings_factory = factory


def get_settings() -> ObjectStorageSettingsLike:
    if _settings_factory is None:
        raise RuntimeError(
            "storage settings not registered; call storage.set_settings(...) at host startup"
        )
    return _settings_factory()
