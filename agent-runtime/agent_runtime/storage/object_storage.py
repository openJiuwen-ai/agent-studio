#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
对象存储工具 — 用于从对象存储读取 IR 文件

提供可插拔的 ObjectStorageProvider 抽象类，内置实现：
- S3StorageProvider — 基于 aioboto3 的 S3 兼容存储（ OBS S3 端口、AWS S3、MinIO 等）
- LocalStorageProvider — 本地文件系统读取
- CUSTOM — 通过 importlib 动态加载自定义实现

配置项（通过 settings.object_storage 或环境变量）:
    STORAGE_TYPE                — 存储类型：OBS（默认）/ LOCAL / CUSTOM
    STORAGE_CUSTOM_MODULE       — CUSTOM 类型的模块路径或 .py 文件路径
    STORAGE_CUSTOM_CLASS        — CUSTOM 类型的实现类名
    DATASOURCE_OBS_SERVER       — S3 endpoint（如 https://obs.example.com:30443）
    DATASOURCE_OBS_BUCKET       — 桶名
    DATASOURCE_OBS_AK           — Access Key
    DATASOURCE_OBS_SK           — Secret Key
    DATASOURCE_OBS_PATH_STYLE   — 寻址方式："path"（默认，路径风格）或 "virtual"（虚拟托管风格）
"""

import asyncio
import inspect
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
    StorageWriteError,
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
                # 禁用可选 CRC32 校验和 — botocore 1.40+ 默认启用会触发 aws-chunked
                # 分块编码（Transfer-Encoding: chunked），要求必须提供 Content-Length
                # 添加以下参数后，就不会要求传入了
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
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

    async def download_to_file(self, object_key: str, local_path: str) -> None:
        """流式下载 S3 对象到本地文件

        Args:
            object_key: S3 对象 key
            local_path: 本地保存路径

        Raises:
            StorageConfigError: 配置缺失或未初始化
            StorageReadError: 读取或写入失败
        """
        self._ensure_initialized()
        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            response = await self._client.get_object(
                Bucket=self._bucket, Key=object_key
            )
            async with response["Body"] as stream:
                chunk = await stream.read()
                with open(local_path, "wb") as f:
                    f.write(chunk)
        except Exception as e:
            if isinstance(e, (StorageConfigError, StorageReadError)):
                raise
            workflow_logger.error(
                f"S3 download failed: object_key={object_key}, local_path={local_path}, {e}",
                exc_info=True,
            )
            raise StorageReadError(
                f"S3 download failed: object_key={object_key}, error={e}"
            ) from e
    
    
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

    async def put_object_bytes(
        self, object_key: str, data: bytes, bucket_name: Optional[str] = None
    ) -> None:
        """异步上传二进制内容到 S3/OBS

        Args:
            object_key: S3 对象 key
            data: 原始字节内容
            bucket_name: 目标桶名；None 时用默认桶

        Raises:
            StorageConfigError: 未初始化
            StorageWriteError: 上传失败
        """
        self._ensure_initialized()
        bucket = bucket_name or self._bucket
        try:
            await self._client.put_object(Bucket=bucket, Key=object_key, Body=data)
        except Exception as e:
            if isinstance(e, (StorageConfigError, StorageWriteError)):
                raise
            workflow_logger.error(
                f"S3 put failed: object_key={object_key}, bucket={bucket}, {e}",
                exc_info=True,
            )
            raise StorageWriteError(
                f"S3 put failed: object_key={object_key}, error={e}"
            ) from e

    async def get_presigned_url(
        self, object_key: str, expires_seconds: int, bucket_name: Optional[str] = None
    ) -> str:
        """生成临时签名下载 URL（纯本地计算，无网络 I/O）

        Args:
            object_key: S3 对象 key
            expires_seconds: URL 有效期（秒）
            bucket_name: 目标桶名；None 时用默认桶

        Returns:
            str: 预签名下载 URL

        Raises:
            StorageConfigError: 未初始化
        """
        self._ensure_initialized()
        bucket = bucket_name or self._bucket
        url = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": object_key},
            ExpiresIn=expires_seconds,
        )
        if inspect.isawaitable(url):
            url = await url
        return url

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
    """本地文件系统存储提供者

    路径规则与 Java 侧 LocalFileStoreImpl 对齐：
    实际文件路径 = local_base_path / local_bucket / object_key
    例如 object_key="ir/xxx.json" → /data/storage/default-bucket/ir/xxx.json
    """

    def __init__(self, base_path: str = "", bucket: str = ""):
        self._base_path = base_path or settings.object_storage.local_base_path
        self._bucket = bucket or settings.object_storage.local_bucket

    def _resolve(self, object_key: str) -> str:
        return os.path.join(self._base_path, self._bucket, object_key)

    async def get_content(self, object_key: str) -> str:
        """读取本地文件内容，返回 UTF-8 字符串

        Args:
            object_key: 对象 key（如 ir/xxx.json）

        Raises:
            StorageReadError: 文件不存在或读取失败
        """

        file_path = self._resolve(object_key)
        if not os.path.exists(file_path):
            workflow_logger.error(f"File not found: {file_path}")
            raise StorageReadError(f"File not found: {file_path}")

        try:
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                None,
                lambda: open(file_path, "r", encoding="utf-8").read(),
            )
            return content
        except Exception as e:
            workflow_logger.error(f"File read failed: {file_path}, {e}", exc_info=True)
            raise StorageReadError(f"File read failed: {file_path}, {e}") from e

    async def get_object_bytes(self, object_key: str) -> bytes:
        """读取本地文件内容，返回原始字节

        Args:
            object_key: 对象 key

        Raises:
            StorageReadError: 文件不存在或读取失败
        """
        file_path = self._resolve(object_key)
        if not os.path.exists(file_path):
            workflow_logger.error(f"File not found: {file_path}")
            raise StorageReadError(f"File not found: {file_path}")

        try:
            loop = asyncio.get_running_loop()
            content = await loop.run_in_executor(
                None,
                lambda: open(file_path, "rb").read(),
            )
            return content
        except Exception as e:
            workflow_logger.error(f"File read failed: {file_path}, {e}", exc_info=True)
            raise StorageReadError(f"File read failed: {file_path}, {e}") from e


def _load_custom_provider(module_path: str, class_name: str) -> ObjectStorageProvider:
    """通过 importlib 动态加载自定义存储实现

    Args:
        module_path: Python 模块路径或 .py 文件绝对路径
            - 文件路径：/opt/plugins/custom_storage（自动加 .py 后缀）
            - 模块名：my_package.custom_storage（需已安装到 site-packages）
        class_name: 实现类名（必须继承 ObjectStorageProvider）

    Returns:
        ObjectStorageProvider 实例

    Raises:
        StorageConfigError: 配置缺失或加载失败
    """
    import importlib
    import importlib.util
    from pathlib import Path

    if not module_path:
        raise StorageConfigError("STORAGE_CUSTOM_MODULE is required when STORAGE_TYPE=CUSTOM")
    if not class_name:
        raise StorageConfigError("STORAGE_CUSTOM_CLASS is required when STORAGE_TYPE=CUSTOM")

    p = Path(module_path)
    try:
        if p.suffix == ".py" or (p.exists() and p.is_file()):
            # 按文件路径加载
            py_path = p if p.suffix == ".py" else p.with_suffix(".py")
            if not py_path.exists():
                raise StorageConfigError(f"Custom storage module file not found: {py_path}")
            spec = importlib.util.spec_from_file_location(py_path.stem, str(py_path))
            if spec is None:
                raise StorageConfigError(f"Cannot load module spec from: {py_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            # 按 Python 模块名加载
            module = importlib.import_module(module_path)
    except Exception as e:
        raise StorageConfigError(
            f"Failed to load custom storage module '{module_path}': {e}"
        ) from e

    cls = getattr(module, class_name, None)
    if cls is None:
        raise StorageConfigError(
            f"Class '{class_name}' not found in module '{module_path}'"
        )
    if not issubclass(cls, ObjectStorageProvider):
        raise StorageConfigError(
            f"Class '{class_name}' must extend ObjectStorageProvider"
        )

    try:
        return cls()
    except Exception as e:
        raise StorageConfigError(
            f"Failed to instantiate custom storage class '{class_name}': {e}"
        ) from e

    async def list_keys(self, prefix: str) -> list[str]:
        """列出本地目录下匹配前缀的文件"""
        import glob as glob_mod
        pattern = f"{prefix}*" if prefix.endswith("/") else f"{prefix}/*"
        return sorted(glob_mod.glob(pattern))


def get_storage_provider() -> ObjectStorageProvider:
    """根据配置获取存储提供者

    STORAGE_TYPE 环境变量控制返回哪种实现：
    - OBS (默认): S3StorageProvider（需 S3 配置完整且已初始化）
    - LOCAL: LocalStorageProvider
    - CUSTOM: 通过 STORAGE_CUSTOM_MODULE + STORAGE_CUSTOM_CLASS 动态加载
    """
    storage_type = settings.object_storage.type.upper()

    if storage_type == "CUSTOM":
        return _load_custom_provider(
            settings.object_storage.custom_module,
            settings.object_storage.custom_class,
        )

    if storage_type == "LOCAL":
        return LocalStorageProvider()

    # OBS / S3 — 默认行为
    if settings.object_storage.server:
        provider = S3StorageProvider.instance()
        if provider.is_initialized:
            return provider
        workflow_logger.warning(
            "S3StorageProvider not initialized, falling back to LocalStorageProvider"
        )
        return LocalStorageProvider()
    return LocalStorageProvider()
