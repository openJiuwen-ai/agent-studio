# -*- coding: utf-8 -*-
"""对象存储异常类型（agent_runtime / agent_builder 共用）。

迁移自 ``agent_runtime.common.ir_interfaces`` 的 Storage* 异常。``code`` 取 int 值，
与原 ``ExtensionStatusCode`` 一致：STORAGE_CONFIG_ERROR(188910) /
STORAGE_READ_ERROR(188911) / STORAGE_WRITE_ERROR(188912)，使宿主的全局异常 handler
返回的 ``code`` 字段保持不变。

不依赖任何宿主包（不 import agent_runtime / agent_builder）。
"""

from __future__ import annotations


class StorageConfigError(Exception):
    """存储配置异常 — 环境变量缺失或无效 / 未初始化。"""

    code = 188910

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(msg)


class StorageReadError(Exception):
    """存储读取异常 — 下载对象失败（传输层）。"""

    code = 188911

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(msg)


class StorageWriteError(Exception):
    """存储写入异常 — 上传对象失败。"""

    code = 188912

    def __init__(self, msg: str = "", **kwargs):
        super().__init__(msg)


class StorageNotFoundError(StorageReadError):
    """存储对象不存在（S3 404/NoSuchKey 或本地文件缺失）。

    继承 ``StorageReadError`` 以兼容既有 ``except StorageReadError`` 的调用方（404 仍被捕获）；
    上层（如 model_service.resolver）可按子类区分"未配置"（→None）与"OBS 不可达"（→读错误）。
    """
