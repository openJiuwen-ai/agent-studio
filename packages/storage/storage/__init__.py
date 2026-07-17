# -*- coding: utf-8 -*-
"""对象存储共享层（agent_runtime / agent_builder 共用）。

机制层（S3/OBS 读取 + 本地降级 + 异常 + 配置注入）迁移自 ``agent_runtime.storage``，
去耦为共享包：不 import 任何宿主。OBS 配置由宿主经 ``storage.ports.set_settings``
注入；异常类型用本包 ``exceptions``（``code`` 与原 ExtensionStatusCode 一致）。

agent_runtime / agent_builder 在启动 lifespan 中：
    import storage
    storage.set_settings(lambda: settings.object_storage)   # 注入 OBS 配置
    await storage.S3StorageProvider.instance().initialize()
"""

from .exceptions import (
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
    StorageWriteError,
)
from .object_storage import (
    LocalStorageProvider,
    ObjectStorageProvider,
    S3StorageProvider,
    get_storage_provider,
)
from .ports import ObjectStorageSettingsLike, get_settings, set_settings

__all__ = [
    "StorageConfigError", "StorageNotFoundError", "StorageReadError", "StorageWriteError",
    "ObjectStorageProvider", "S3StorageProvider", "LocalStorageProvider",
    "get_storage_provider",
    "ObjectStorageSettingsLike", "get_settings", "set_settings",
]
