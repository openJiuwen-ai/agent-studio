#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
对象存储工具 — 用于从对象存储读取 IR 文件

提供可插拔的 ObjectStorageProvider 抽象类，内置实现：
- S3StorageProvider — 基于 aioboto3 的 S3 兼容存储（ OBS S3 端口、AWS S3、MinIO 等）
- LocalStorageProvider — 本地文件系统读取

配置项（通过 settings.object_storage 或环境变量）:
    DATASOURCE_OBS_SERVER      — S3 endpoint（如 https://obs.example.com:30443）
    DATASOURCE_OBS_BUCKET      — 桶名
    DATASOURCE_OBS_AK          — Access Key
    DATASOURCE_OBS_SK          — Secret Key
    DATASOURCE_OBS_PATH_STYLE  — 寻址方式："path"（默认，路径风格）或 "virtual"（虚拟托管风格）
"""

import asyncio
import os
import threading
from typing import Optional

import aioboto3
from agent_runtime.common.config import settings
from agent_runtime.common.ir_interfaces import (
    ObjectStorageProvider,
    StorageConfigError,
    StorageNotFoundError,
    StorageReadError,
)
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError
from openjiuwen.core.common.logging import workflow_logger


def _is_s3_not_found(client_error: ClientError) -> bool:
    """S3 对象不存在：NoSuchKey/404 code 或 HTTP 404 status。"""
    response = getattr(client_error, "response", {}) or {}
    code = (response.get("Error") or {}).get("Code", "")
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return code in ("NoSuchKey", "404", "NotFound") or status == 404


class S3StorageProvider(ObjectStorageProvider):
    """基于 aioboto3 的 S3 兼容存储提供者

    支持OBS S3 端口、AWS S3、MinIO 等兼容 S3 协议的对象存储。
    使用 aioboto3 原生异步 client 读取对象内容，无需线程池。

    生命周期管理：
        - initialize() 在 FastAPI lifespan 启动时调用，创建 aioboto3 client
        - close() 在 lifespan 关闭时调用，释放 client 资源
        - 如果未调用 initialize() 就读取，抛出 StorageConfigError
    """

    _singleton: Optional["S3StorageProvider"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._context = None      # aioboto3 ClientCreatorContext (async context manager)
        self._client = None       # actual S3 client returned by __aenter__
        self._initialized: bool = False
        self._bucket: Optional[str] = None

    @classmethod
    def instance(cls) -> "S3StorageProvider":
        """获取 S3StorageProvider 单例"""
        if cls._singleton is None:
            with cls._lock:
                if cls._singleton is None:
                    cls._singleton = S3StorageProvider()
        return cls._singleton

    @classmethod
    def _decrypt_sk(cls, sk: str) -> str:
        """SK 解密接口 — 当前返回明文

        预留后续替换为商用解密实现。
        当 agentBuilder-engine 部署到商用环境时，SK 可能为加密存储，
        届时替换此方法即可。
        """
        return sk

    async def initialize(self) -> None:
        """创建 aioboto3 S3 client — 在 FastAPI lifespan 启动时调用

        aioboto3.client() 返回 async context manager，必须调用 __aenter__()
        初始化内部 aiohttp session，__aexit__() 清理资源。
        """
        if self._initialized:
            return

        server = settings.object_storage.server
        bucket = settings.object_storage.bucket
        ak = settings.object_storage.access_key
        sk = settings.object_storage.secret_key

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
            verify=settings.object_storage.enable_ssl,
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": settings.object_storage.path_style},
                connect_timeout=5,
                read_timeout=30,
            ),
        )
        # __aenter__() returns the actual S3 client; the context is the wrapper
        self._client = await self._context.__aenter__()
        self._bucket = bucket
        self._initialized = True
        workflow_logger.info("S3 async client initialized for endpoint: {}", server)

    async def close(self) -> None:
        """关闭 aioboto3 S3 client — 在 FastAPI lifespan 关闭时调用"""
        if self._context is not None:
            await self._context.__aexit__(None, None, None)
            self._context = None
            self._client = None
            self._initialized = False
            self._bucket = None
            workflow_logger.info("S3 async client closed")

    def _ensure_initialized(self):
        """检查 client 是否已初始化，未初始化则抛出 StorageConfigError"""
        if not self._initialized:
            raise StorageConfigError(
                "S3StorageProvider not initialized. Call initialize() first."
            )

    @property
    def is_initialized(self) -> bool:
        """是否已初始化 — 供 get_storage_provider() 等外部代码检查"""
        return self._initialized

    async def get_object_bytes(self, object_key: str) -> bytes:
        """异步读取 S3 对象内容，返回原始字节

        Args:
            object_key: S3 对象 key

        Returns:
            bytes: 对象原始字节内容

        Raises:
            StorageConfigError: 配置缺失或未初始化
            StorageReadError: 读取失败
        """
        self._ensure_initialized()
        try:
            response = await self._client.get_object(
                Bucket=self._bucket, Key=object_key
            )
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
        """异步读取 S3 对象内容，返回 UTF-8 字符串

        Args:
            object_key: S3 对象 key（如 workflow/ir/xxx/xxx.json）

        Returns:
            str: 对象内容的 UTF-8 字符串

        Raises:
            StorageConfigError: 配置缺失或未初始化
            StorageReadError: 读取失败
        """
        data = await self.get_object_bytes(object_key)
        return data.decode("utf-8")

    async def list_keys(self, prefix: str) -> list[str]:
        """列出指定前缀下的所有对象 key

        Args:
            prefix: S3 对象 key 前缀

        Returns:
            list[str]: 匹配的对象 key 列表

        Raises:
            StorageConfigError: 未初始化
            StorageReadError: 列出失败
        """
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
        """重置单例 — 仅用于测试

        注意：此方法不会关闭已有的 aioboto3 client。
        如果 provider 已初始化，应先调用 close() 再 reset()，
        否则底层 aiohttp session 不会被释放。
        """
        with cls._lock:
            if cls._singleton is not None:
                if cls._singleton.is_initialized:
                    workflow_logger.warning(
                        "S3StorageProvider.reset() called on initialized singleton — "
                        "call close() first to avoid resource leaks"
                    )
                cls._singleton = None


class LocalStorageProvider(ObjectStorageProvider):
    """本地文件系统存储提供者"""

    async def get_content(self, object_key: str) -> str:
        """读取本地文件内容，返回 UTF-8 字符串

        Args:
            object_key: 文件路径

        Raises:
            StorageReadError: 文件不存在或读取失败
        """
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

    async def list_keys(self, prefix: str) -> list[str]:
        """列出本地目录下匹配前缀的文件"""
        import glob as glob_mod
        pattern = f"{prefix}*" if prefix.endswith("/") else f"{prefix}/*"
        return sorted(glob_mod.glob(pattern))


def get_storage_provider() -> ObjectStorageProvider:
    """根据配置获取存储提供者

    当 object_storage.server 已配置且 S3 client 已初始化时返回 S3StorageProvider，
    否则返回 LocalStorageProvider 作为降级。
    """
    if settings.object_storage.server:
        provider = S3StorageProvider.instance()
        if provider.is_initialized:
            return provider
        # S3 未初始化（lifespan 初始化失败）— 降级到本地存储
        workflow_logger.warning(
            "S3StorageProvider not initialized, falling back to LocalStorageProvider"
        )
        return LocalStorageProvider()
    return LocalStorageProvider()
