# -*- coding: utf-8 -*-
"""对象存储工具 — agent_runtime / agent_builder 共用。

迁移自 ``agent_runtime.storage.object_storage``，去耦为共享包：OBS 配置经
``storage.ports.set_settings`` 由宿主注入，异常用本包 ``exceptions``，logger 用
openjiuwen ``workflow_logger``。不 import 任何宿主。

- S3StorageProvider — 基于 aioboto3 的 S3 兼容存储（OBS / AWS S3 / MinIO）
- LocalStorageProvider — 本地文件系统（S3 未配置/初始化失败时降级）
- get_storage_provider() — 按 settings 返回 S3（已初始化）或 Local
"""

from __future__ import annotations

import asyncio
import os
import threading
from abc import ABC, abstractmethod
from typing import Optional

import aioboto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from openjiuwen.core.common.logging import workflow_logger

from .exceptions import StorageConfigError, StorageNotFoundError, StorageReadError
from .ports import get_settings


def _is_s3_not_found(client_error: ClientError) -> bool:
    """S3 对象不存在：NoSuchKey/404 code 或 HTTP 404 status。"""
    response = getattr(client_error, "response", {}) or {}
    code = (response.get("Error") or {}).get("Code", "")
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return code in ("NoSuchKey", "404", "NotFound") or status == 404


class ObjectStorageProvider(ABC):
    """对象存储提供者抽象类。扩展时继承此类并实现 get_content()。"""

    @abstractmethod
    async def get_content(self, object_key: str) -> str:
        """读取对象内容，返回 UTF-8 字符串。"""

    async def list_keys(self, prefix: str) -> "list[str]":
        """列出指定前缀下的对象 key；默认实现返回空列表，子类可覆写。"""
        return []


class S3StorageProvider(ObjectStorageProvider):
    """基于 aioboto3 的 S3 兼容存储提供者。

    生命周期：initialize() 在 lifespan 启动时调用创建 client；close() 在关闭时释放；
    未初始化就读取抛 StorageConfigError。
    """

    _singleton: Optional["S3StorageProvider"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._context = None      # aioboto3 ClientCreatorContext
        self._client = None       # actual S3 client returned by __aenter__
        self._initialized: bool = False
        self._bucket: Optional[str] = None

    @classmethod
    def instance(cls) -> "S3StorageProvider":
        if cls._singleton is None:
            with cls._lock:
                if cls._singleton is None:
                    cls._singleton = S3StorageProvider()
        return cls._singleton

    @classmethod
    def _decrypt_sk(cls, sk: str) -> str:
        """SK 解密接口 — 当前返回明文，预留商用环境加密 SK 替换。"""
        return sk

    async def initialize(self) -> None:
        """创建 aioboto3 S3 client（FastAPI lifespan 启动时调用）。"""
        if self._initialized:
            return

        cfg = get_settings()
        server = cfg.server
        bucket = cfg.bucket
        ak = cfg.access_key
        sk = cfg.secret_key

        if not server or not ak or not sk:
            workflow_logger.error(
                "S3 storage config incomplete: missing DATASOURCE_OBS_SERVER/AK/SK"
            )
            raise StorageConfigError(
                "S3 storage config incomplete, missing DATASOURCE_OBS_SERVER/AK/SK"
            )

        if not bucket:
            workflow_logger.error("S3 storage config incomplete: missing DATASOURCE_OBS_BUCKET")
            raise StorageConfigError(
                "S3 storage config incomplete, missing DATASOURCE_OBS_BUCKET"
            )

        sk = self._decrypt_sk(sk)

        self._context = aioboto3.Session().client(
            "s3",
            endpoint_url=server,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            verify=cfg.enable_ssl,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": cfg.path_style},
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        self._client = await self._context.__aenter__()
        self._bucket = bucket
        self._initialized = True
        workflow_logger.info("S3 async client initialized for endpoint: {}", server)

    async def close(self) -> None:
        if self._context is not None:
            await self._context.__aexit__(None, None, None)
            self._context = None
            self._client = None
            self._initialized = False
            self._bucket = None
            workflow_logger.info("S3 async client closed")

    def _ensure_initialized(self):
        if not self._initialized:
            raise StorageConfigError(
                "S3StorageProvider not initialized. Call initialize() first."
            )

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def get_object_bytes(self, object_key: str) -> bytes:
        """异步读取 S3 对象内容，返回原始字节。"""
        self._ensure_initialized()
        try:
            response = await self._client.get_object(Bucket=self._bucket, Key=object_key)
            async with response["Body"] as stream:
                return await stream.read()
        except StorageConfigError:
            raise
        except ClientError as e:
            if _is_s3_not_found(e):
                raise StorageNotFoundError(
                    f"S3 object not found: object_key={object_key}"
                ) from e
            workflow_logger.error(
                f"S3 read failed: object_key={object_key}, {e}", exc_info=True
            )
            raise StorageReadError(
                f"S3 read failed: object_key={object_key}, error={e}"
            ) from e
        except Exception as e:
            if isinstance(e, (StorageConfigError, StorageReadError)):
                raise
            workflow_logger.error(
                f"S3 read failed: object_key={object_key}, {e}", exc_info=True
            )
            raise StorageReadError(
                f"S3 read failed: object_key={object_key}, error={e}"
            ) from e

    async def get_content(self, object_key: str) -> str:
        """异步读取 S3 对象内容，返回 UTF-8 字符串。"""
        data = await self.get_object_bytes(object_key)
        return data.decode("utf-8")

    async def list_keys(self, prefix: str) -> "list[str]":
        """列出指定前缀下的所有对象 key。"""
        self._ensure_initialized()
        try:
            keys = []
            paginator = self._client.get_paginator("list_objects_v2")
            async for page in paginator.paginate(
                Bucket=self._bucket, Prefix=prefix, MaxKeys=1000
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
            return keys
        except Exception as e:
            workflow_logger.error("S3 list failed: prefix=%s, error=%s", prefix, e)
            raise StorageReadError(
                f"S3 list failed: prefix={prefix}, error={e}"
            ) from e

    @classmethod
    def reset(cls):
        """重置单例 — 仅用于测试。已初始化时先 close() 再 reset 以释放 aiohttp session。"""
        with cls._lock:
            if cls._singleton is not None:
                if cls._singleton.is_initialized:
                    workflow_logger.warning(
                        "S3StorageProvider.reset() called on initialized singleton — "
                        "call close() first to avoid resource leaks"
                    )
                cls._singleton = None


class LocalStorageProvider(ObjectStorageProvider):
    """本地文件系统存储提供者。"""

    async def get_content(self, object_key: str) -> str:
        if not os.path.exists(object_key):
            workflow_logger.error(f"File not found: {object_key}")
            raise StorageNotFoundError(f"File not found: {object_key}")

        try:
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                None,
                lambda: open(object_key, "r", encoding="utf-8").read(),
            )
            return content
        except Exception as e:
            workflow_logger.error(f"File read failed: {object_key}, {e}", exc_info=True)
            raise StorageReadError(f"File read failed: {object_key}, {e}") from e

    async def list_keys(self, prefix: str) -> "list[str]":
        import glob as glob_mod
        pattern = f"{prefix}*" if prefix.endswith("/") else f"{prefix}/*"
        return sorted(glob_mod.glob(pattern))


def get_storage_provider() -> ObjectStorageProvider:
    """获取 storage provider：server 已配置且 S3 client 已初始化 → S3；否则降级 Local。

    配置缺失时也降级到 Local（而非抛错），与原 agent_runtime 行为一致，避免启动硬失败。
    """
    try:
        cfg = get_settings()
    except RuntimeError:
        # settings 未注入（宿主未注册）— 降级 Local，避免阻塞未配 OBS 的场景。
        return LocalStorageProvider()

    if cfg.server:
        provider = S3StorageProvider.instance()
        if provider.is_initialized:
            return provider
        workflow_logger.warning(
            "S3StorageProvider not initialized, falling back to LocalStorageProvider"
        )
        return LocalStorageProvider()
    return LocalStorageProvider()
