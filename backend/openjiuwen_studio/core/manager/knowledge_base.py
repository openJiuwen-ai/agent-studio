#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import asyncio
import inspect
import json
import os
import re
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Union, Tuple, Optional
from typing import List

from fastapi import status, UploadFile
from openjiuwen.core.common.logging import logger
from openjiuwen.core.retrieval.common.config import (
    KnowledgeBaseConfig,
    EmbeddingConfig,
    StoreType,
    VectorStoreConfig,
)
from openjiuwen.core.retrieval.common.document import Document
from openjiuwen.core.retrieval.embedding.openai_embedding import OpenAIEmbedding
from openjiuwen.core.retrieval.graph_knowledge_base import GraphKnowledgeBase
from openjiuwen.core.retrieval.indexing.indexer.chroma_indexer import ChromaIndexer
from openjiuwen.core.retrieval.indexing.indexer.milvus_indexer import MilvusIndexer
from openjiuwen.core.retrieval.indexing.processor.chunker.chunking import TextChunker
from openjiuwen.core.retrieval.indexing.processor.extractor.triple_extractor import TripleExtractor
from openjiuwen.core.retrieval.indexing.processor.parser.auto_file_parser import AutoFileParser
from openjiuwen.core.retrieval.indexing.processor.parser.auto_link_parser import AutoLinkParser
from openjiuwen.core.retrieval.simple_knowledge_base import SimpleKnowledgeBase
from openjiuwen.core.retrieval.vector_store.chroma_store import ChromaVectorStore
from openjiuwen.core.retrieval.vector_store.milvus_store import MilvusVectorStore
from openjiuwen.core.foundation.store.object.aioboto_storage_client import AioBotoClient

from openjiuwen_studio.core.database import SessionLocal
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.core.manager.repositories.agent_repository import agent_repository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import (
    KBDetails,
    KBDocument,
    KBWeblink,
)
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import (
    knowledge_base_repository,
)
from openjiuwen_studio.core.thirdparty_client import DeepSearchAgentClient
from openjiuwen_studio.models.knowledge_base_document import DocumentStatus
from openjiuwen_studio.ops.modules.llm.llm_manager import get_llm_client_by_protocol
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseResponseCreate,
    KnowledgeBaseGet,
    KnowledgeBaseUpdateRequest,
    KnowledgeBaseInfo,
    DocumentUploadResponse,
    DocumentUploadBatchResponse,
    KnowledgeBaseSearchRequest,
    KnowledgeBaseSearchResponse,
    KnowledgeBaseListRequest,
    KnowledgeBaseListResponse,
    KnowledgeBaseListItem,
    DocumentStatusRequest,
    DocumentStatusResponse,
    DocumentStatusListResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
    DocumentListRequest,
    DocumentListResponse,
    DocumentListItem,
    DocumentUpdateRequest,
    DocumentDeleteRequest,
    TaskProgressRequest,
    TaskProgressResponse,
    TaskProgressItem,
    WeblinkAddRequest,
    WeblinkAddBatchResponse,
    WeblinkAddItem,
    WeblinkListRequest,
    WeblinkListResponse,
    WeblinkListItem,
    WeblinkStatusRequest,
    WeblinkProcessRequest,
    WeblinkProcessResponse,
    WeblinkUpdateRequest,
    WeblinkDeleteRequest,
)

_CURR_INDEX_TYPE = os.getenv("INDEX_MANAGER_TYPE", "milvus")
# 每个 weblink 类型知识库允许的最大链接条数（含已存在 + 本次提交）
WEBLINK_KB_MAX_LINKS = 50


@dataclass
class WeblinkProcessContext:
    space_id: str
    kb_id: str
    parsing_strategy: Any
    segmentation_strategy: Any
    indexing_strategy: Any


@dataclass
class WeblinkProcessTask:
    weblink_id: str
    url: str
    process_info: dict


class OBSDocumentManager:
    """
    Manages OBS documents and uploads/downloads them to/from OBS
    """

    backend_dir = Path(__file__).resolve().parent.parent.parent.parent

    def __init__(self, bucket: str = None):
        self.bucket = bucket or os.getenv("OBS_BUCKET")
        if not self.bucket:
            logger.warning("[OBS] OBS_BUCKET not set, skipping upload_document")

        server = os.getenv("OBS_SERVER")
        region_name = os.getenv("OBS_REGION")
        access_key_id = SecurityUtils.get_decrypted_secret(
            "OBS_ACCESS_KEY_ID",
            os.getenv("OBS_ACCESS_KEY_ID", None)
        )
        secret_access_key = SecurityUtils.get_decrypted_secret(
            "OBS_SECRET_ACCESS_KEY",
            os.getenv("OBS_SECRET_ACCESS_KEY", None)
        )
        self.obs_client = AioBotoClient(
            server=server,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region_name=region_name,
        )

    @staticmethod
    def obs_name(space_id: str, kb_id: str, file_name: str) -> str:
        return f"{space_id}/{kb_id}/{file_name}"

    @classmethod
    def local_path(cls, space_id: str, kb_id: str, file_name: str) -> Path:
        storage_path = cls.backend_dir / "data" / "knowledge_base" / space_id / kb_id
        storage_path.mkdir(parents=True, exist_ok=True)
        return storage_path / file_name

    async def delete_document(self, object_name: str):
        if not self.bucket:
            return
        await self.obs_client.delete_object(self.bucket, object_name)

    async def download_document(
        self,
        object_name: str,
        file_path: str | Path,
    ):
        if not self.bucket:
            return
        file_path = Path(file_path)

        # Create file path directory if it does not exist
        file_dir = file_path.parent
        if not os.path.isdir(file_dir):
            file_dir.mkdir(parents=True, exist_ok=True)

        await self.obs_client.download_file(self.bucket, object_name, file_path)

    async def upload_document(
        self,
        object_name: str,
        file_path: str | Path,
    ):
        if not self.bucket:
            return
        await self.obs_client.upload_file(self.bucket, object_name, file_path)

    async def download_if_updated(
        self,
        object_name: str,
        file_path: str,
    ):
        listed_objects = await self.obs_client.list_objects(
            self.bucket, object_prefix=object_name, max_objects=1
        )
        if not listed_objects:
            logger.info("No matching objects found on OBS, skipping download.")
            return

        obs_last_modified = listed_objects[0].get("LastModified")
        if not obs_last_modified:
            logger.info("OBS object missing LastModified, skipping download.")
            return

        # If local file does not exist, download directly
        if not os.path.exists(file_path):
            await self.download_document(object_name, file_path)
            logger.info("Local file missing, downloaded from OBS.")
            return

        # Check local file mtime
        local_mtime = os.path.getmtime(file_path)
        local_modified = datetime.fromtimestamp(local_mtime, tz=timezone.utc)

        if obs_last_modified <= local_modified:
            logger.info("Local file is up to date, skipping download.")
            return

        await self.download_document(object_name, file_path)
        logger.info("Downloaded updated file.")


# ==================== GraphRAG 配置和模型管理 ====================

def _extract_full_error_message(error: Exception) -> str:
    """提取完整的错误信息，包括异常链中的所有错误

    用于提取 openjiuwen 包抛出的异常信息，因为 openjiuwen 包内部可能捕获异常后
    使用 cause 参数重新抛出，形成异常链。

    Args:
        error: 异常对象

    Returns:
        完整的错误信息字符串，包含所有异常链中的错误
    """
    error_parts = []
    current_error = error

    # 遍历异常链，收集所有错误信息
    while current_error is not None:
        error_str = str(current_error)
        if error_str:
            error_parts.append(error_str)

        # 检查是否有 __cause__ (异常链)
        if hasattr(current_error, "__cause__") and current_error.__cause__:
            current_error = current_error.__cause__
        # 检查是否有 __context__ (异常上下文)
        elif hasattr(current_error, "__context__") and current_error.__context__:
            current_error = current_error.__context__
        else:
            break

    # 如果只有一个错误，直接返回
    if len(error_parts) == 1:
        return error_parts[0]

    # 如果有多个错误，用 " -> " 连接
    return " -> ".join(error_parts)


def _format_error_message_for_frontend(error_msg: str) -> str:
    """格式化错误信息供前端显示

    改写规则：
    1. 固定错误消息保持不变
    2. 带前缀的错误：去掉前缀、状态码、箭头（替换为分号）
    3. 若含 ", reason:" 且其后有内容，保留其后（具体原因）；否则去掉 reason 段
    4. 确保首字母大写

    Args:
        error_msg: 原始错误信息

    Returns:
        格式化后的错误信息
    """
    if not error_msg:
        return error_msg

    # 固定错误消息列表（保持不变）
    fixed_messages = {
        "Document not found",
        "Document status invalid",
        "File path not found",
        "Failed to update document status",
        "Document validation failed",
        "Processing failed with unknown error",
        "Failed to update status to INDEXED",
        "Not found",  # weblink 状态查询时链接不存在
        "Weblink status invalid",  # weblink 处理时状态无效
    }

    # 如果是固定错误消息，直接返回（首字母已大写）
    if error_msg in fixed_messages:
        return error_msg

    # 需要改写的错误信息
    result = error_msg

    # 1. 去掉前缀
    prefixes = [
        "File parsing failed: ",
        "Index building failed: ",
        "Failed to update status to INDEXING: ",
    ]
    for prefix in prefixes:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break

    # 2. 去掉状态码 [155xxx]
    result = re.sub(r"\[\d+\]\s*", "", result)

    # 3. 去掉箭头 -> 和前后空格，用分号替换
    result = re.sub(r"\s*->\s*", "; ", result)

    # 4. StatusCode / LLM 错误模板多为 "... , reason: {具体原因}"，具体原因在 reason 之后；
    #    若截断丢弃 reason 之后的内容，前端只能看到泛化前缀（用户无法排查限流、API 报错等）。
    #    因此：若存在 ", reason:" 且其后有非空内容，优先展示其后内容；否则保留原逻辑。
    reason_pattern = r",\s*reason\s*:\s*"
    match = re.search(reason_pattern, result, re.IGNORECASE)
    if match:
        after_reason = result[match.end():].strip()
        before_reason = result[:match.start()].strip()
        if after_reason:
            result = after_reason
        else:
            result = before_reason

    # 5. 清理多余的空格
    result = " ".join(result.split())

    # 6. 确保首字母大写
    if result:
        result = result[0].upper() + result[1:] if len(result) > 1 else result.upper()

    return result


def _create_llm_client_from_db(llm_model_id: str, space_id: str):
    """从数据库创建 LLM 客户端

    从数据库读取 LLM 模型配置，解密 API key，并创建 LLM 客户端实例。

    Args:
        llm_model_id: LLM 模型配置ID（必填）
        space_id: 空间ID，用于从数据库查询模型配置（必填）

    Returns:
        Tuple[LLM客户端实例, model_type]: (LLM客户端, 模型类型名称)

    Raises:
        ValueError: 如果数据库查询失败或配置无效
    """
    logger.info(
        f"[LLM_CLIENT] Creating LLM client from database - Model ID: {llm_model_id}, Space ID: {space_id}"
    )

    # 从数据库获取模型配置
    with get_db_jw() as db:
        manager = ModelConfigManager(db)
        model_config = manager.get_config_by_id(int(llm_model_id), space_id)

        # 检查模型是否激活
        if not model_config.is_active:
            raise ValueError(
                f"LLM model '{model_config.name}' (ID: {llm_model_id}) is not active. "
                f"Please activate the model before starting document processing."
            )

        # 解密 API key
        security_utils = SecurityUtils()
        api_key = None
        if model_config.api_key:
            try:
                api_key = security_utils.decrypt_api_key(model_config.api_key)
            except Exception as e:
                logger.warning(
                    f"[LLM_CLIENT] Failed to decrypt API key for model {llm_model_id}: {str(e)}"
                )
                raise ValueError(
                    f"Failed to decrypt API key for model {llm_model_id}: {str(e)}"
                ) from e

        # 获取 timeout 配置，图增强索引时最小 120s
        timeout = model_config.timeout or 60
        if timeout < 120:
            logger.warning(
                f"[LLM_CLIENT] Timeout {timeout}s may be too short for graph indexing, using 120s instead"
            )
            timeout = 120

        protocol = {
            "provider": model_config.provider,
            "api_key": api_key or "",
            "base_url": model_config.base_url or "",
            "timeout": timeout,
        }
        llm_client = get_llm_client_by_protocol(protocol)
        # TripleExtractor 调用 invoke 时不传 model，依赖 client 的 model_config.model_name
        if getattr(llm_client, "model_config", None) and model_config.model_type:
            llm_client.model_config.model_name = model_config.model_type
        logger.info(
            f"[LLM_CLIENT] LLM client created from database - "
            f"Model Type: {model_config.model_type}, Timeout: {timeout}s"
        )

        return llm_client, model_config.model_type


def _create_embed_model(kb_id: str, space_id: str) -> OpenAIEmbedding:
    """创建 Embedding 模型

    从数据库读取知识库关联的 embedding 模型配置。

    Args:
        kb_id: 知识库ID，用于从数据库查询 embedding 模型配置（必填）
        space_id: 空间ID，用于从数据库查询知识库和 embedding 模型配置（必填）

    Returns:
        OpenAIEmbedding 实例

    Raises:
        ValueError: 如果数据库查询失败或配置无效
    """
    # 默认的 timeout 和 max_retries（与 APIEmbedClient 的默认值一致）
    default_timeout = 60
    default_max_retries = 3

    # 从数据库读取知识库的 embedding 模型配置
    db = SessionLocal()
    try:
        # 1. 查询知识库，获取 embedding_model_config_id
        kb_details = KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
        kb_get = KnowledgeBaseGet(**asdict(kb_details))
        kb_result = knowledge_base_repository.knowledge_base_get(kb_get)

        if kb_result.code != status.HTTP_200_OK or not kb_result.data:
            raise ValueError(f"Knowledge base not found (KB: {kb_id}, Space: {space_id})")

        embedding_model_config_id = kb_result.data.get("embedding_model_config_id")

        if not embedding_model_config_id:
            raise ValueError(f"Knowledge base {kb_id} has no embedding_model_config_id")

        # 2. 查询 embedding 模型配置
        embed_repo = EmbeddingModelConfigRepository(db)
        embed_model_config = embed_repo.get_by_id(embedding_model_config_id)

        if not embed_model_config:
            raise ValueError(f"Embedding model config not found (ID: {embedding_model_config_id})")

        if embed_model_config.space_id != space_id:
            raise ValueError(f"Embedding model config does not belong to this space (ID: {embedding_model_config_id})")

        if not embed_model_config.is_active:
            raise ValueError(
                f"Embedding model config is not active (ID: {embedding_model_config_id})"
            )

        logger.info(
            f"[EMBED_MODEL] Using embedding model from database - "
            f"KB: {kb_id}, Model: {embed_model_config.model_name} (ID: {embed_model_config.id})"
        )

        # 3. 解密 API key
        security_utils = SecurityUtils()
        api_key = None
        if embed_model_config.api_key:
            try:
                api_key = security_utils.decrypt_api_key(embed_model_config.api_key)
            except Exception as e:
                raise ValueError(
                    f"Failed to decrypt API key for model {embed_model_config.id}: {str(e)}"
                ) from e

        # 4. 使用数据库配置创建 Embedding 模型
        # 数据库字段：api_base, model_id, api_key, max_batch_size
        # OpenAIEmbedding 需要：config (EmbeddingConfig), timeout, max_retries, max_batch_size
        # timeout 和 max_retries 使用默认值（60 和 3）
        embed_config = EmbeddingConfig(
            model_name=embed_model_config.model_id,  # 使用 model_id 作为模型名称
            api_key=api_key,
            base_url=embed_model_config.api_base,
        )
        embed_model = OpenAIEmbedding(
            config=embed_config,
            timeout=default_timeout,  # 使用默认值
            max_retries=default_max_retries,  # 使用默认值
            max_batch_size=embed_model_config.max_batch_size,
        )
        logger.debug(f"[EMBED_MODEL] Embed model created from database successfully")
        return embed_model

    finally:
        db.close()


def get_embed_model_config(kb_id: str, space_id: str) -> EmbeddingConfig:
    """Return the EmbeddingConfig for a knowledge base.

    Args:
        kb_id: Knowledge base ID used to look up the embedding model config.
        space_id: Space ID for scoping the database query.

    Returns:
        EmbeddingConfig instance.

    Raises:
        ValueError: If the knowledge base or embedding model config is not found.
    """
    db = SessionLocal()
    try:
        # 1. Query the knowledge base to obtain embedding_model_config_id
        kb_details = KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
        kb_get = KnowledgeBaseGet(**asdict(kb_details))
        kb_result = knowledge_base_repository.knowledge_base_get(kb_get)

        if kb_result.code != status.HTTP_200_OK or not kb_result.data:
            raise ValueError(f"Knowledge base not found (KB: {kb_id}, Space: {space_id})")

        embedding_model_config_id = kb_result.data.get("embedding_model_config_id")
        if not embedding_model_config_id:
            raise ValueError(f"Knowledge base {kb_id} has no embedding_model_config_id")

        # 2. Query the embedding model configuration
        embed_repo = EmbeddingModelConfigRepository(db)
        embed_model_config = embed_repo.get_by_id(embedding_model_config_id)

        if not embed_model_config:
            raise ValueError(f"Embedding model config not found (ID: {embedding_model_config_id})")

        if embed_model_config.space_id != space_id:
            raise ValueError(f"Embedding model config does not belong to this space (ID: {embedding_model_config_id})")

        if not embed_model_config.is_active:
            raise ValueError(
                f"Embedding model config is not active (ID: {embedding_model_config_id})"
            )

        # 3. Decrypt the API key
        security_utils = SecurityUtils()
        api_key = None
        if embed_model_config.api_key:
            try:
                api_key = security_utils.decrypt_api_key(embed_model_config.api_key)
            except Exception as e:
                raise ValueError(
                    f"Failed to decrypt API key for model {embed_model_config.id}: {str(e)}"
                ) from e

        # 4. Build and return the EmbeddingConfig
        embed_config = EmbeddingConfig(
            model_name=embed_model_config.model_id,
            api_key=api_key,
            base_url=embed_model_config.api_base,
        )

        logger.debug(
            f"[EMBED_CONFIG] Built EmbeddingConfig from database - "
            f"KB: {kb_id}, Model: {embed_model_config.model_name} (ID: {embed_model_config.id})"
        )
        return embed_config

    finally:
        db.close()


# ==================== 异常处理装饰器 ==


def with_exception_handling(func):
    """异常处理装饰器，支持同步和异步函数"""
    if inspect.iscoroutinefunction(func):

        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[KNOWLEDGE_BASE] Error in {func.__name__}: {str(e)}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Internal server error",
                )

        return async_wrapper

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[KNOWLEDGE_BASE] Error in {func.__name__}: {str(e)}", exc_info=True)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Internal server error",
            )

    return wrapper


@with_exception_handling
def knowledge_base_create(req: KnowledgeBaseCreate, current_user: dict) -> ResponseModel:
    """创建新的知识库"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[KB_CREATE] Creating knowledge base - User: {user_id}, Name: {req.name}, "
        f"Embedding Model Config ID: {req.embedding_model_config_id}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 检查知识库名称是否已存在（区分大小写）
    name_exists_result = knowledge_base_repository.knowledge_base_check_name_exists(
        space_id=req.space_id, name=req.name
    )
    if name_exists_result.code != status.HTTP_200_OK:
        logger.error(
            f"[KB_CREATE] Failed to check name existence - Error: {name_exists_result.message}"
        )
        return ResponseModel(
            code=name_exists_result.code,
            message=name_exists_result.message,
        )
    if name_exists_result.data:
        logger.warning(
            f"[KB_CREATE] Knowledge base name already exists - Name: {req.name}, Space: {req.space_id}"
        )
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"知识库名称 '{req.name}' 已存在",
        )

    # 3. 验证 embedding_model_config_id 是否存在且属于该 space_id
    db = SessionLocal()
    try:
        embedding_repo = EmbeddingModelConfigRepository(db)
        embedding_model = embedding_repo.get_by_id(req.embedding_model_config_id)
        if not embedding_model:
            logger.error(
                f"[KB_CREATE] Embedding model config not found - ID: {req.embedding_model_config_id}"
            )
            return ResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message=f"Embedding model config not found: {req.embedding_model_config_id}",
            )
        if embedding_model.space_id != req.space_id:
            logger.error(
                f"[KB_CREATE] Embedding model config space mismatch - "
                f"Config Space: {embedding_model.space_id}, Request Space: {req.space_id}"
            )
            return ResponseModel(
                code=status.HTTP_403_FORBIDDEN,
                message="Embedding model config does not belong to this space",
            )
        if not embedding_model.is_active:
            logger.error(
                f"[KB_CREATE] Embedding model config is not active - ID: {req.embedding_model_config_id}"
            )
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Embedding model config is not active",
            )
        logger.info(
            f"[KB_CREATE] Embedding model config validated - ID: {req.embedding_model_config_id}, "
            f"Model: {embedding_model.model_name}"
        )
    finally:
        db.close()

    # 4. Checking index connection
    index_conn = _check_index_connection()
    if index_conn is not None:
        return index_conn

    # 5. 生成知识库ID（使用去掉连字符的 UUID，保证仅字母数字，Milvus 索引名合规）
    kb_id = uuid.uuid4().hex
    logger.debug(f"[KB_CREATE] Generated KB ID: {kb_id}")

    # 6. 准备知识库数据
    kb_data = {
        "space_id": req.space_id,
        "kb_id": kb_id,
        "name": req.name,
        "description": req.description,
        "index_manager_type": _CURR_INDEX_TYPE,
        "embedding_model_config_id": req.embedding_model_config_id,
        "config": req.config,
        "create_time": milliseconds(),
        "update_time": milliseconds(),
    }

    # 7. 保存到数据库
    create_result = knowledge_base_repository.knowledge_base_create(kb_data)

    if create_result.code != status.HTTP_200_OK:
        logger.error(
            f"[KB_CREATE] Database save failed - ID: {kb_id}, Error: {create_result.message}"
        )
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    # 8. 准备响应数据
    response_data = KnowledgeBaseResponseCreate(id=kb_id)

    logger.info(
        f"[KB_CREATE] Knowledge base created - ID: {kb_id}, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 9. 返回创建结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create knowledge base success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def knowledge_base_get_referencing_agents(
    req: KnowledgeBaseGet, current_user: dict
) -> ResponseModel:
    """获取引用该知识库的智能体列表"""
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[KB_GET_REF_AGENTS] Getting agents referencing KB - User: {user_id}, KB ID: {req.kb_id}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 获取引用该知识库的智能体列表
    result = agent_repository.get_agents_referencing_knowledge_base(
        space_id=req.space_id, kb_id=req.kb_id
    )

    if result.code != status.HTTP_200_OK:
        logger.error(
            f"[KB_GET_REF_AGENTS] Failed to get referencing agents - Error: {result.message}"
        )
        return result

    agent_names = result.data.get("agent_names", []) if result.data else []
    count = result.data.get("count", 0) if result.data else 0

    logger.info(f"[KB_GET_REF_AGENTS] Found {count} agent(s) referencing KB {req.kb_id}")

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Get agents referencing knowledge base successfully",
        data={"agent_names": agent_names, "count": count},
    )


@with_exception_handling
async def knowledge_base_delete(req: KnowledgeBaseGet, current_user: dict) -> ResponseModel:
    """删除知识库"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(f"[KB_DELETE] Deleting knowledge base - User: {user_id}, KB ID: {req.kb_id}")

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 检查知识库是否存在
    get_result = knowledge_base_repository.knowledge_base_get(req)
    if get_result.code == status.HTTP_404_NOT_FOUND:
        logger.warning(f"[KB_DELETE] Knowledge base not found - ID: {req.kb_id}, User: {user_id}")
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    # 3. 从所有包含该知识库的agent中移除该知识库信息
    try:
        logger.info(
            f"[KB_DELETE] Removing KB {req.kb_id} from related agents - Space: {req.space_id}"
        )
        remove_result = agent_repository.remove_knowledge_base_from_agents(req.space_id, req.kb_id)

        if remove_result.code == status.HTTP_200_OK and remove_result.data:
            updated_count = remove_result.data.get("updated_count", 0)
            failed_count = remove_result.data.get("failed_count", 0)
            if updated_count > 0:
                logger.info(
                    f"[KB_DELETE] Removed KB {req.kb_id} from {updated_count} agent(s) - "
                    f"Space: {req.space_id}, Failed: {failed_count}"
                )
            if failed_count > 0:
                errors = remove_result.data.get("errors", [])
                logger.warning(
                    f"[KB_DELETE] Failed to remove KB {req.kb_id} from {failed_count} agent(s) - "
                    f"Errors: {errors}"
                )
        else:
            logger.warning(
                f"[KB_DELETE] Failed to remove KB {req.kb_id} from agents - "
                f"Error: {remove_result.message}"
            )
    except Exception as e:
        # 即使移除agent中的知识库信息失败，也继续删除知识库
        logger.error(
            f"[KB_DELETE] Exception while removing KB {req.kb_id} from agents - "
            f"Error: {str(e)}",
            exc_info=True,
        )

    # 4. 删除知识库：删「同步后的知识库」仅删该条并调 DS 接口；删「Studio 知识库」时同时删 DS 同步后的知识库
    ds_kb_id: Optional[str] = None
    ds_kb_id_resp = knowledge_base_repository.knowledge_base_get_ds_kb_id(
        space_id=req.space_id, kb_id=req.kb_id
    )
    if ds_kb_id_resp.code == status.HTTP_200_OK and ds_kb_id_resp.data is not None:
        ds_kb_id = ds_kb_id_resp.data
    is_studio_row = bool(ds_kb_id and ds_kb_id != req.kb_id)
    logger.info(f"[KB_DELETE] is_studio_row: {is_studio_row}, ds_kb_id: {ds_kb_id}, req.kb_id: {req.kb_id}")

    ds_client = DeepSearchAgentClient()
    deleted_kb_ids: List[str] = []

    if is_studio_row:
        # 删除的是 Studio 知识库：先调 DS 删除同步后的知识库，再删 Studio 行和共享表里的 DS 行
        try:
            await ds_client.delete_knowledge_base(space_id=req.space_id, ds_kb_id=ds_kb_id)
            logger.info(f"[KB_DELETE] DeepSearch KB deleted (Studio delete) - ds_kb_id: {ds_kb_id}")
        except Exception as e:
            logger.warning(
                f"[KB_DELETE] DeepSearch delete failed (ds_kb_id={ds_kb_id}), continuing - Error: {str(e)}",
                exc_info=True,
            )
        delete_result = knowledge_base_repository.knowledge_base_delete(req)
        if delete_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=delete_result.code,
                message=delete_result.message,
            )
        # 同步删除共享表中 kb_id=ds_kb_id 的 DeepSearch 行
        ds_row_get = KnowledgeBaseGet(
            space_id=req.space_id,
            kb_id=ds_kb_id,
            index_manager_type=_CURR_INDEX_TYPE,
        )
        knowledge_base_repository.knowledge_base_delete(ds_row_get)
        deleted_kb_ids = [req.kb_id, ds_kb_id]
        logger.info(f"[KB_DELETE] Deleted Studio row and DS-created row - kb_id: {req.kb_id}, ds_kb_id: {ds_kb_id}")
    else:
        # 删除的是同步后的知识库：调 DS 删除、删当前行，并清空原始 Studio 行的 ds_kb_id，以便用户可再次点击同步
        try:
            await ds_client.delete_knowledge_base(space_id=req.space_id, ds_kb_id=req.kb_id)
            logger.info(f"[KB_DELETE] DeepSearch KB deleted (synced KB only) - kb_id: {req.kb_id}")
        except Exception as e:
            logger.warning(
                f"[KB_DELETE] DeepSearch delete failed (kb_id={req.kb_id}), continuing - Error: {str(e)}",
                exc_info=True,
            )
        delete_result = knowledge_base_repository.knowledge_base_delete(req)
        if delete_result.code not in (status.HTTP_200_OK, status.HTTP_404_NOT_FOUND):
            return ResponseModel(
                code=delete_result.code,
                message=delete_result.message,
            )
        if delete_result.code == status.HTTP_404_NOT_FOUND:
            logger.info(
                f"[KB_DELETE] Local row already removed (likely by DeepSearch) - kb_id: {req.kb_id}"
            )
        # 清空原始知识库的 ds_kb_id，使再次同步时可新建 DS 知识库
        clear_resp = knowledge_base_repository.knowledge_base_clear_ds_kb_id_by_ds_kb_id(
            space_id=req.space_id, ds_kb_id=req.kb_id
        )
        if clear_resp.code == status.HTTP_200_OK:
            logger.info(
                f"[KB_DELETE] Cleared ds_kb_id on original KB (synced kb_id={req.kb_id}) for re-sync"
            )
        deleted_kb_ids = [req.kb_id]

    logger.info(
        f"[KB_DELETE] Knowledge base deleted - ID: {req.kb_id}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 删除本地知识库文件
    kb_storage_path = _get_storage_path(req.space_id, req.kb_id)
    try:
        if kb_storage_path.exists():
            # 删除整个知识库目录及其所有内容
            import shutil

            shutil.rmtree(kb_storage_path)
            logger.info(
                f"[KB_DELETE] Local knowledge base directory deleted - Path: {kb_storage_path}"
            )
        else:
            logger.warning(
                f"[KB_DELETE] Local knowledge base directory not found - Path: {kb_storage_path}"
            )
    except Exception as e:
        # 知识库记录已删除，但本地文件删除失败，记录错误但返回成功
        logger.error(
            f"[KB_DELETE] Failed to delete local knowledge base directory - Path: {kb_storage_path}, Error: {str(e)}",
            exc_info=True,
        )

    # 6. Delete Milvus | Chroma vector collection (chunks + triples collections)
    try:
        index_result = await _delete_kb_indices(req.kb_id, req.space_id)
        if index_result["errors"]:
            logger.warning(
                f"[KB_DELETE] Failed to delete indices - KB ID: {req.kb_id}, "
                f"Errors: {index_result['errors']}"
            )
    except Exception as e:
        # Milvus | Chroma 删除失败不影响整体删除结果
        logger.error(
            f"[KB_DELETE] Failed to delete indices - KB ID: {req.kb_id}, Error: {str(e)}",
            exc_info=True,
        )

    # 7. 删除 knowledge_base_document 和 knowledge_base_weblink 行（索引已删，避免孤儿数据）
    try:
        knowledge_base_repository.delete_documents_by_kb_id(req.space_id, req.kb_id)
        knowledge_base_repository.delete_weblinks_by_kb_id(req.space_id, req.kb_id)
        logger.info(
            f"[KB_DELETE] Document and weblink rows cleaned - KB ID: {req.kb_id}"
        )
    except Exception as e:
        logger.error(
            f"[KB_DELETE] Failed to clean document/weblink rows - KB ID: {req.kb_id}, Error: {str(e)}",
            exc_info=True,
        )

    # 8. 返回删除结果（含 deleted_kb_ids 供前端从列表移除所有相关卡片）
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete knowledge base success",
        data={"deleted_kb_ids": deleted_kb_ids},
    )


@with_exception_handling
def knowledge_base_update(req: KnowledgeBaseUpdateRequest, current_user: dict) -> ResponseModel:
    """更新知识库"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[KB_UPDATE] Updating knowledge base - User: {user_id}, KB ID: {req.kb_id}, "
        f"Name: {req.name}, Desc: {repr(req.desc)}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 检查知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    get_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if get_result.code == status.HTTP_404_NOT_FOUND or not get_result.data:
        logger.warning(f"[KB_UPDATE] Knowledge base not found - ID: {req.kb_id}, User: {user_id}")
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    # 获取当前知识库的信息
    current_kb = get_result.data
    current_name = current_kb.get("name", "")
    current_desc = current_kb.get("description", "")
    logger.info(
        f"[KB_UPDATE] Current description: {repr(current_desc)}, New description: {repr(req.desc)}"
    )

    # 3. 如果名称改变，检查新名称是否已存在（排除当前知识库，区分大小写）
    if req.name != current_name:
        name_exists_result = knowledge_base_repository.knowledge_base_check_name_exists(
            space_id=req.space_id, name=req.name, exclude_kb_id=req.kb_id
        )
        if name_exists_result.code != status.HTTP_200_OK:
            logger.error(
                f"[KB_UPDATE] Failed to check name existence - Error: {name_exists_result.message}"
            )
            return ResponseModel(
                code=name_exists_result.code,
                message=name_exists_result.message,
            )
        if name_exists_result.data:
            logger.warning(
                f"[KB_UPDATE] Knowledge base name already exists - Name: {req.name}, "
                f"Space: {req.space_id}, KB ID: {req.kb_id}"
            )
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"知识库名称 '{req.name}' 已存在",
            )

    # 4. 更新知识库
    # 如果 desc 是空字符串，转换为 None 以便正确清空数据库字段
    description_value = req.desc if req.desc else None
    update_result = knowledge_base_repository.knowledge_base_update(
        KBDetails(
            space_id=req.space_id,
            kb_id=req.kb_id,
            index_manager_type=_CURR_INDEX_TYPE,
        ),
        name=req.name,
        description=description_value,
    )

    if update_result.code != status.HTTP_200_OK:
        logger.error(f"[KB_UPDATE] Update failed - ID: {req.kb_id}, Error: {update_result.message}")
        return ResponseModel(
            code=update_result.code,
            message=update_result.message,
        )

    logger.info(
        f"[KB_UPDATE] Knowledge base updated - ID: {req.kb_id}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回更新结果
    return ResponseModel(
        code=status.HTTP_200_OK, message="update knowledge base message success", data=None
    )


def _safe_synthetic_filename(name: str, suffix: str) -> str:
    """构造同步到 DeepSearch 的 weblink 合成文件名。

    weblink 在 Studio 侧没有落盘文件，同步时会按 URL 重新解析并以一份 Markdown
    上传到 DeepSearch，因此需要一个安全的合成文件名（去除路径分隔与控制字符、
    限长，并强制带后缀）。
    """
    safe = re.sub(r"[\\/\x00-\x1f]+", "_", name or "").strip()
    if not safe:
        safe = "weblink"
    if len(safe) > 150:
        safe = safe[:150]
    if not safe.lower().endswith(suffix.lower()):
        safe = f"{safe}{suffix}"
    return safe


async def _collect_weblink_files_for_sync(
    space_id: str, kb_id: str
) -> Tuple[List[Tuple[str, bytes, str]], List[str], int, Optional[ResponseModel]]:
    """收集 weblink 知识库要同步到 DeepSearch 的「合成文件」列表。

    复用 `_parse_url` 重新解析每个链接，把解析出的 Document 拼成一份 Markdown
    文件（保留标题、源 URL、正文），以与文档库相同的 multipart 上传路径上传。
    解析失败的链接被跳过并记录 warning，不阻断整体同步。

    Returns:
        (files_for_ds, doc_id_list, source_total, error_resp)：
          - files_for_ds: 形如 [(filename, content_bytes, content_type), ...]
          - doc_id_list:  与 files_for_ds 一一对应的 Studio 侧合成 doc_id，
                          供后续 sync_process 透传给 DeepSearch /api/kb/process。
          - source_total: 该知识库下的链接总数（用于空集时区分日志）
          - error_resp:   非 None 表示列出链接阶段失败，调用方应直接返回该响应
    """
    list_result = knowledge_base_repository.weblink_list(
        KBWeblink(
            kb=KBDetails(
                space_id=space_id,
                kb_id=kb_id,
                index_manager_type=_CURR_INDEX_TYPE,
            )
        ),
        page=1,
        size=WEBLINK_KB_MAX_LINKS,
    )
    if list_result.code != status.HTTP_200_OK:
        logger.warning(
            f"[KB_SYNC_UPLOAD] Failed to list weblinks - kb_id={kb_id}, "
            f"error={list_result.message}"
        )
        return [], [], 0, ResponseModel(
            code=list_result.code,
            message=list_result.message or "Failed to list weblinks",
        )

    weblinks = (list_result.data or {}).get("items", []) or []
    files_for_ds: List[Tuple[str, bytes, str]] = []
    doc_id_list: List[str] = []

    for w in weblinks:
        weblink_id = w.get("weblink_id")
        url = (w.get("url") or "").strip()
        name = (w.get("name") or url or weblink_id or "weblink").strip()
        if not url:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Weblink missing url, skip - kb_id={kb_id}, "
                f"weblink_id={weblink_id}"
            )
            continue
        try:
            documents = await _parse_url(url, weblink_id or str(uuid.uuid4()))
        except Exception as e:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Failed to parse weblink, skip - kb_id={kb_id}, "
                f"weblink_id={weblink_id}, url={url}, error={e}"
            )
            continue

        # 提取标题：与 weblink_get_status_batch(refresh_names=True) 同源逻辑
        # 当源 KB 的 name 还是 URL（尚未触发过 refresh_names 流程）时用解析得到的 title 替代，
        # 避免镜像里看到 URL.md，同时回写 weblink 表让源 KB 列表也立即显示标题
        parsed_title: Optional[str] = None
        for d in documents:
            md = getattr(d, "metadata", None)
            if isinstance(md, dict):
                t = md.get("title")
                if t and isinstance(t, str) and t.strip():
                    parsed_title = t.strip()
                    break
        name_is_url_like = (
            (not name)
            or name.strip() == url
            or name.strip().lower().startswith(("http://", "https://"))
        )
        if parsed_title and name_is_url_like:
            name = parsed_title
            if weblink_id:
                try:
                    knowledge_base_repository.weblink_update(
                        KBWeblink(
                            kb=KBDetails(
                                space_id=space_id,
                                kb_id=kb_id,
                                index_manager_type=_CURR_INDEX_TYPE,
                            ),
                            weblink_id=weblink_id,
                        ),
                        name=parsed_title,
                    )
                except Exception as e:
                    logger.debug(
                        f"[KB_SYNC_UPLOAD] Failed to backfill weblink name - "
                        f"kb_id={kb_id}, weblink_id={weblink_id}, error={e}"
                    )

        body_parts: List[str] = []
        for d in documents:
            text = getattr(d, "text", None)
            if text and isinstance(text, str) and text.strip():
                body_parts.append(text.strip())
        body = "\n\n".join(body_parts).strip()
        if not body:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Weblink parsed to empty content, skip - "
                f"kb_id={kb_id}, weblink_id={weblink_id}, url={url}"
            )
            continue

        markdown = f"# {name}\n\n源链接：{url}\n\n{body}\n"
        filename = _safe_synthetic_filename(name, ".md")
        files_for_ds.append((filename, markdown.encode("utf-8"), "text/markdown"))
        doc_id_list.append(str(uuid.uuid4()))

    logger.info(
        f"[KB_SYNC_UPLOAD] Weblink files prepared - kb_id={kb_id}, "
        f"weblink_count={len(weblinks)}, prepared_count={len(files_for_ds)}"
    )
    return files_for_ds, doc_id_list, len(weblinks), None


@with_exception_handling
async def knowledge_base_sync_upload(
    space_id: str,
    kb_id: str,
    current_user: dict,
    deepsearch_embedding_model_config_id: Optional[int] = None,
) -> ResponseModel:
    """同步上传：在 DeepSearch 创建/复用知识库，并上传 Studio 当前知识库下全部文档。

    支持两类 Studio 知识库：
      - 文档知识库（document）：直接读取每个文档的本地文件并上传。
      - 网页链接知识库（weblink）：按 URL 重新解析后，以合成 Markdown 上传。

    deepsearch_embedding_model_config_id: 可选，DeepSearch 侧嵌入模型配置 ID。
    """
    # 1. 验证用户空间权限
    _ = check_user_space(space_id, current_user)

    # 2. 检查知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found"
        )
    kb_data = kb_result.data

    # 3. 获取 ds_kb_id，判断首次同步或更新同步
    ds_kb_id = kb_data.get("ds_kb_id")
    ds_kb_id_resp = knowledge_base_repository.knowledge_base_get_ds_kb_id(
        space_id=space_id, kb_id=kb_id
    )
    if ds_kb_id_resp.code == status.HTTP_200_OK and ds_kb_id_resp.data is not None:
        ds_kb_id = ds_kb_id_resp.data

    embed_id = (
        deepsearch_embedding_model_config_id
        if deepsearch_embedding_model_config_id is not None
        else (kb_data.get("embedding_model_config_id") or 0)
    )
    ds_name = f"deepsearch_{kb_data.get('name', '') or 'kb'}"
    ds_client = DeepSearchAgentClient()

    if not ds_kb_id:
        # 4a. 首次同步：验证 embedding、创建 DS 知识库、更新 Studio、创建同步记录
        db = SessionLocal()
        try:
            embed_repo = EmbeddingModelConfigRepository(db)
            embed_model = embed_repo.get_by_id(embed_id)
            if not embed_model:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message=f"Embedding model config not found: {embed_id}",
                )
            if embed_model.space_id != space_id:
                return ResponseModel(
                    code=status.HTTP_403_FORBIDDEN,
                    message="Embedding model config does not belong to this space",
                )
            if not embed_model.is_active:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Embedding model config is not active: {embed_id}",
                )
            embed_model_config, llm_config = _build_ds_stored_kb_model_configs(embed_model)
        finally:
            db.close()

        create_payload = {
            "space_id": space_id,
            "name": ds_name,
            "description": kb_data.get("description") or "",
            "embed_model_config": embed_model_config,
            "llm_config": llm_config,
            "config": kb_data.get("config") or {},
            "index_manager_type": kb_data.get("index_manager_type") or _CURR_INDEX_TYPE,
        }
        try:
            create_resp = await ds_client.create_knowledge_base(create_payload)
        except Exception as e:
            logger.error(
                f"[KB_SYNC_UPLOAD] DeepSearch create KB failed - kb_id={kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch create knowledge base failed: {str(e)}",
            )
        data = create_resp.get("data") or create_resp
        ds_kb_id = data.get("id")
        if not ds_kb_id:
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message="DeepSearch did not return knowledge base id",
            )

        update_result = knowledge_base_repository.knowledge_base_update_ds_kb_id(
            kb=KBDetails(
                space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE
            ),
            ds_kb_id=ds_kb_id,
        )
        if update_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=update_result.code,
                message=update_result.message or "Failed to save ds_kb_id",
            )

        synced_kb_data = {
            "space_id": space_id,
            "kb_id": ds_kb_id,
            "ds_kb_id": ds_kb_id,
            "name": ds_name,
            "description": kb_data.get("description") or "",
            "index_manager_type": kb_data.get("index_manager_type") or _CURR_INDEX_TYPE,
            "embedding_model_config_id": embed_id,
            "config": kb_data.get("config") or {},
            "create_time": milliseconds(),
            "update_time": milliseconds(),
        }
        create_synced_result = knowledge_base_repository.knowledge_base_create(
            synced_kb_data
        )
        if create_synced_result.code != status.HTTP_200_OK:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Failed to create synced KB row - ds_kb_id={ds_kb_id}, "
                f"error={create_synced_result.message}"
            )
    else:
        # 4b. 更新同步：更新 DS 知识库 config、清空 DS 侧文档
        db = SessionLocal()
        try:
            embed_repo = EmbeddingModelConfigRepository(db)
            embed_model = embed_repo.get_by_id(embed_id)
            if embed_model and embed_model.space_id == space_id and embed_model.is_active:
                embed_model_config, llm_config = _build_ds_stored_kb_model_configs(
                    embed_model
                )
                update_payload = {
                    "space_id": space_id,
                    "kb_id": ds_kb_id,
                    "name": ds_name,
                    "desc": kb_data.get("description") or "",
                    "embed_model_config": embed_model_config,
                    "llm_config": llm_config,
                    "config": kb_data.get("config") or {},
                }
                try:
                    await ds_client.update_knowledge_base(update_payload)
                    logger.info(
                        f"[KB_SYNC_UPLOAD] Updated DS KB config for overwrite - ds_kb_id={ds_kb_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[KB_SYNC_UPLOAD] Failed to update DS KB config (continuing) - "
                        f"ds_kb_id={ds_kb_id}, error={e}",
                        exc_info=True,
                    )
            else:
                logger.warning(
                    f"[KB_SYNC_UPLOAD] Embedding not found/inactive (embed_id={embed_id}), "
                    f"skip config update - ds_kb_id={ds_kb_id}"
                )
        finally:
            db.close()

        # 4b.2 清空 DS 侧文档（覆盖同步前需先清空）
        try:
            ds_doc_ids = []
            page, size = 1, 100
            while True:
                ds_resp = await ds_client.list_documents(
                    space_id=space_id, kb_id=ds_kb_id, page=page, size=size
                )
                ds_data = ds_resp.get("data") if isinstance(ds_resp, dict) else ds_resp or {}
                items = ds_data.get("items") or []
                total = ds_data.get("total") or 0
                for doc in items:
                    doc_id = doc.get("id") or doc.get("doc_id")
                    if doc_id:
                        ds_doc_ids.append(doc_id)
                if len(ds_doc_ids) >= total or len(items) < size:
                    break
                page += 1
            if ds_doc_ids:
                await ds_client.delete_documents(
                    space_id=space_id, kb_id=ds_kb_id, document_ids=ds_doc_ids
                )
                logger.info(
                    f"[KB_SYNC_UPLOAD] Cleared {len(ds_doc_ids)} documents from DS KB - ds_kb_id={ds_kb_id}"
                )
        except Exception as e:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Failed to clear DS KB documents (continuing) - "
                f"ds_kb_id={ds_kb_id}, error={e}",
                exc_info=True,
            )

    # 5a. weblink 知识库走独立分支：按 URL re-parse 后以合成 .md 上传到 DeepSearch
    # （文档库分支保持原逻辑不变）
    kb_type = (kb_data.get("config") or {}).get("type") or "document"
    if kb_type == "weblink":
        wl_files, wl_doc_id_list, wl_total, wl_error_resp = (
            await _collect_weblink_files_for_sync(space_id=space_id, kb_id=kb_id)
        )
        if wl_error_resp is not None:
            return wl_error_resp
        logger.info(
            f"[KB_SYNC_UPLOAD] Weblink files prepared - kb_id={kb_id}, "
            f"ds_kb_id={ds_kb_id}, weblink_count={wl_total}, uploaded_count={len(wl_files)}"
        )
        if not wl_files:
            if wl_total:
                logger.warning(
                    f"[KB_SYNC_UPLOAD] All {wl_total} weblink(s) skipped - kb_id={kb_id}"
                )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="sync upload success",
                data={"ds_kb_id": ds_kb_id, "uploaded_count": 0, "doc_id_list": []},
            )
        try:
            ds_upload_resp = await ds_client.upload_knowledge_base_files(
                space_id=space_id,
                ds_kb_id=ds_kb_id,
                files=wl_files,
                metadata={"doc_list": wl_doc_id_list},
            )
            # 把 DS 端返回的原始响应落日志：DS 即便返回 2xx 也可能在响应体里
            # 表达「文件被丢弃 / 解析失败」，没这行的话「上传 OK 但 DS KB 仍空」会无从定位
            logger.info(
                f"[KB_SYNC_UPLOAD] DeepSearch upload response (weblink) - "
                f"ds_kb_id={ds_kb_id}, file_count={len(wl_files)}, "
                f"doc_id_list={wl_doc_id_list}, response={ds_upload_resp}"
            )
        except Exception as e:
            logger.error(
                f"[KB_SYNC_UPLOAD] DeepSearch upload failed (weblink) - "
                f"ds_kb_id={ds_kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch upload failed: {str(e)}",
            )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="sync upload success",
            data={
                "ds_kb_id": ds_kb_id,
                "uploaded_count": len(wl_files),
                "doc_id_list": wl_doc_id_list,
            },
        )

    # 5. 获取待同步文档列表（空知识库也允许完成第一步：已创建/更新 DS，上传数为 0）
    kbdoc = KBDocument(
        kb=KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=None)
    )
    docs_result = knowledge_base_repository.document_list_all_for_sync(kbdoc)
    if docs_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=docs_result.code,
            message=docs_result.message or "Failed to list documents",
        )
    doc_list = docs_result.data or []
    if not doc_list:
        logger.warning(
            f"[KB_SYNC_UPLOAD] No documents to sync - kb_id={kb_id}, ds_kb_id={ds_kb_id}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="sync upload success",
            data={"ds_kb_id": ds_kb_id, "uploaded_count": 0, "doc_id_list": []},
        )

    # 6. 准备文件并上传到 DeepSearch
    files_for_ds = []
    doc_id_list = []
    storage_path = _get_storage_path(space_id, kb_id)
    for doc in doc_list:
        studio_doc_id = doc.get("doc_id")
        file_path_str = doc.get("file_path")
        name = doc.get("name") or studio_doc_id
        if not file_path_str:
            continue
        path = Path(file_path_str)
        if not path.is_absolute():
            path = storage_path / path.name
        if not path.exists():
            logger.warning(
                f"[KB_SYNC_UPLOAD] File not found, skip - doc_id={studio_doc_id}, path={path}"
            )
            continue
        try:
            content = path.read_bytes()
        except Exception as e:
            logger.warning(
                f"[KB_SYNC_UPLOAD] Failed to read file, skip - doc_id={studio_doc_id}, error={e}"
            )
            continue
        ext = path.suffix.lower() or ".bin"
        ct = _get_mime_type(ext.lstrip(".")) if ext != ".bin" else "application/octet-stream"
        files_for_ds.append((name, content, ct))
        doc_id_list.append(str(uuid.uuid4()))

    logger.info(
        f"[KB_SYNC_UPLOAD] Files prepared - kb_id={kb_id}, ds_kb_id={ds_kb_id}, "
        f"doc_count={len(doc_list)}, uploaded_count={len(files_for_ds)}"
    )
    if not files_for_ds:
        if doc_list:
            logger.warning(
                f"[KB_SYNC_UPLOAD] All {len(doc_list)} document(s) skipped - kb_id={kb_id}"
            )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="sync upload success",
            data={"ds_kb_id": ds_kb_id, "uploaded_count": 0, "doc_id_list": []},
        )

    try:
        await ds_client.upload_knowledge_base_files(
            space_id=space_id,
            ds_kb_id=ds_kb_id,
            files=files_for_ds,
            metadata={"doc_list": doc_id_list},
        )
    except Exception as e:
        logger.error(
            f"[KB_SYNC_UPLOAD] DeepSearch upload failed - ds_kb_id={ds_kb_id}, error={e}",
            exc_info=True,
        )
        return ResponseModel(
            code=status.HTTP_502_BAD_GATEWAY,
            message=f"DeepSearch upload failed: {str(e)}",
        )

    # 7. 返回结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="sync upload success",
        data={
            "ds_kb_id": ds_kb_id,
            "uploaded_count": len(files_for_ds),
            "doc_id_list": doc_id_list,
        },
    )


@with_exception_handling
async def knowledge_base_sync_process(
    payload: Dict[str, Any], current_user: dict
) -> ResponseModel:
    """同步处理/建索引：透传请求到 DeepSearch /api/kb/process。"""
    space_id = payload.get("space_id")
    if space_id:
        check_user_space(space_id, current_user)
    # DeepSearch 接口要求 kb_id，前端传的是 ds_kb_id
    process_payload = {k: v for k, v in payload.items() if k != "ds_kb_id"}
    process_payload["kb_id"] = payload.get("ds_kb_id") or payload.get("kb_id", "")
    doc_ids = process_payload.get("doc_id_list") or []
    if not doc_ids:
        logger.info(
            f"[KB_SYNC_PROCESS] No documents to process, skip DeepSearch - "
            f"kb_id={process_payload.get('kb_id')}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="sync process skipped (no documents)",
            data={"skipped": True, "processed_count": 0},
        )
    try:
        _apply_ds_process_llm_config(process_payload, space_id)
    except ValueError as e:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )
    ds_client = DeepSearchAgentClient()
    try:
        result = await ds_client.process_knowledge_base_documents(process_payload)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="sync process success",
            data=result.get("data") if isinstance(result, dict) else result,
        )
    except Exception as e:
        logger.error(
            f"[KB_SYNC_PROCESS] DeepSearch process failed - payload={payload}, error={e}",
            exc_info=True,
        )
        return ResponseModel(
            code=status.HTTP_502_BAD_GATEWAY,
            message=f"DeepSearch process failed: {str(e)}",
        )


@with_exception_handling
async def knowledge_base_ds_list(
    space_id: str, page: int, size: int, current_user: dict
) -> ResponseModel:
    """DeepSearch 知识库列表，含索引状态；仅返回已同步到 DeepSearch 的项，不包含 Studio 原始知识库。"""
    check_user_space(space_id, current_user)
    ds_client = DeepSearchAgentClient()
    try:
        result = await ds_client.list_knowledge_bases(
            {"space_id": space_id, "page": page, "size": size}
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get ds knowledge base list success",
            data=result.get("data") if isinstance(result, dict) else result,
        )
    except Exception as e:
        logger.error(
            f"[KB_DS_LIST] DeepSearch list failed - space_id={space_id}, error={e}",
            exc_info=True,
        )
        return ResponseModel(
            code=status.HTTP_502_BAD_GATEWAY,
            message=f"DeepSearch list failed: {str(e)}",
        )


def _ds_stored_llm_config_placeholder() -> dict:
    """DeepSearch 知识库落库用的 llm_config 占位（空密钥，仅占结构）。"""
    return {
        "model_name": "",
        "model_type": "openai",
        "base_url": "",
        "api_key": "",
        "hyper_parameters": {},
        "extension": {},
    }


def _build_ds_stored_embed_config_dict(embed_model) -> dict:
    """从 Studio EmbeddingModelConfig 构建写入 DeepSearch 知识库的 embed_model_config。"""
    security_utils = SecurityUtils()
    api_key = ""
    if embed_model.api_key:
        try:
            api_key = security_utils.decrypt_api_key(embed_model.api_key) or ""
        except Exception as e:
            logger.warning(f"[KB_SYNC] Failed to decrypt embedding api_key: {e}")
    return {
        "model_name": embed_model.model_id or embed_model.model_name or "",
        "api_key": api_key,
        "base_url": embed_model.api_base or "",
        "max_batch_size": getattr(embed_model, "max_batch_size") or 8,
    }


def _build_ds_stored_kb_model_configs(embed_model) -> Tuple[dict, dict]:
    """供 DeepSearch 建库/更新接口使用的 (embed_model_config, llm_config)。

    llm_config 恒为占位；真实 LLM 仅出现在 process 请求体（见 _apply_ds_process_llm_config）。
    """
    return (
        _build_ds_stored_embed_config_dict(embed_model),
        _ds_stored_llm_config_placeholder(),
    )


def _build_ds_process_llm_config_dict(llm_model_id: int, space_id: str) -> dict:
    """从 Studio model_configs 构建 DeepSearch /api/kb/process 请求体中的 llm_config（含解密 api_key）。"""
    with get_db_jw() as db:
        manager = ModelConfigManager(db)
        model_config = manager.get_config_by_id(int(llm_model_id), space_id)
    if not model_config.is_active:
        raise ValueError(
            f"LLM 模型未激活（id={llm_model_id}），请先在模型管理中启用后再进行图增强建索引。"
        )
    security_utils = SecurityUtils()
    api_key = ""
    if model_config.api_key:
        try:
            api_key = security_utils.decrypt_api_key(model_config.api_key) or ""
        except Exception as e:
            raise ValueError(
                f"解密 LLM API Key 失败（model_id={llm_model_id}）: {e}"
            ) from e
    if not str(api_key).strip():
        raise ValueError(
            f"图增强建索引需要可用的 LLM API Key；请在模型管理中为模型（id={llm_model_id}）配置密钥。"
        )
    params = model_config.parameters if isinstance(model_config.parameters, dict) else {}
    hyper_parameters: Dict[str, Any] = {}
    for key in ("temperature", "top_p", "max_tokens"):
        if key in params and params[key] is not None:
            hyper_parameters[key] = params[key]
    provider = (model_config.provider or "openai").strip().lower()
    ds_model_type = "siliconflow" if provider == "siliconflow" else "openai"
    deployment_name = (model_config.model_type or "").strip()
    if not deployment_name:
        raise ValueError(
            f"LLM 未配置模型部署名（model_type 为空），无法在图增强中调用。请在模型管理中补全 model_id={llm_model_id} 的实际模型名。"
        )
    return {
        "model_name": deployment_name,
        "model_type": ds_model_type,
        "base_url": model_config.base_url or "",
        "api_key": api_key,
        "hyper_parameters": hyper_parameters,
        "extension": {},
    }


def _apply_ds_process_llm_config(
    process_payload: dict, space_id: str
) -> None:
    """转发 DeepSearch process 前：若启用图增强，则写入解密后的 llm_config（与知识库存储占位无关）。"""
    idx = process_payload.get("indexing_strategy")
    if not isinstance(idx, dict):
        return
    if not idx.get("enable_graph_enhancement"):
        return
    llm_mid = idx.get("llm_model_id")
    if llm_mid is None:
        raise ValueError("已启用图增强建索引，但未提供 llm_model_id。")
    try:
        mid = int(llm_mid)
    except (TypeError, ValueError) as e:
        raise ValueError(f"无效的 llm_model_id: {llm_mid}") from e
    process_payload["llm_config"] = _build_ds_process_llm_config_dict(mid, space_id)


def _get_storage_path(space_id: str, kb_id: str) -> Path:
    """获取知识库文件存储路径"""
    # 获取后端目录的绝对路径
    backend_dir = Path(__file__).resolve().parent.parent.parent.parent
    # 构建存储路径: backend/data/knowledge_base/{space_id}/{kb_id}/
    storage_path = backend_dir / "data" / "knowledge_base" / space_id / kb_id
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def _get_file_type(filename: str) -> str:
    """根据文件名获取文件类型"""
    return Path(filename).suffix.lower().lstrip(".")


def _get_mime_type(file_type: str) -> str:
    """根据文件类型获取 MIME 类型"""
    mime_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "txt": "text/plain",
        "md": "text/markdown",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "ppt": "application/vnd.ms-powerpoint",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    return mime_types.get(file_type.lower(), "application/octet-stream")


def _detect_real_file_type(file_path: str) -> str:
    """检测文件的真实格式（通过文件头魔数）。

    Args:
        file_path: 文件路径

    Returns:
        检测到的真实文件扩展名，如 '.docx', '.doc', '.pdf' 等
        如果无法识别则返回原扩展名
    """
    try:
        with open(file_path, "rb") as f:
            header = f.read(8)

        # ZIP 格式（包括 .docx, .xlsx, .pptx 等 Office 2007+ 格式）
        if header[:4] == b"PK\x03\x04":
            return ".docx"

        # 旧版 DOC 格式（OLE Compound Document）
        if header[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            return ".doc"

        # PDF 格式
        if header[:4] == b"%PDF":
            return ".pdf"

    except Exception as e:
        logger.warning(f"[PARSE] Failed to detect file type: {file_path}, Error: {e}")

    # 无法识别时返回原扩展名
    return Path(file_path).suffix.lower()


def _get_corrected_file_path(original_path: str) -> str:
    """根据文件真实格式返回正确扩展名的文件路径。

    如果文件扩展名与真实格式不符，会创建一个正确扩展名的临时副本文件。

    Args:
        original_path: 原始文件路径

    Returns:
        正确扩展名的文件路径（可能是临时副本）
    """
    original_ext = Path(original_path).suffix.lower()
    real_ext = _detect_real_file_type(original_path)

    # 扩展名一致，直接返回
    if original_ext == real_ext:
        return original_path

    # 特别处理：.doc 文件实际是 .docx 格式
    if original_ext == ".doc" and real_ext == ".docx":
        logger.info(
            f"[PARSE] File format mismatch detected - "
            f"Extension: {original_ext}, Real format: {real_ext}, "
            f"Path: {original_path}"
        )

        # 创建带正确扩展名的临时副本文件
        original_path_obj = Path(original_path)
        corrected_path = original_path_obj.with_suffix(real_ext)

        # 如果临时副本不存在，创建它
        if not corrected_path.exists():
            try:
                import shutil

                shutil.copy2(original_path, corrected_path)
                logger.info(
                    f"[PARSE] Created temporary file with correct extension: {corrected_path}"
                )
            except Exception as e:
                logger.warning(
                    f"[PARSE] Failed to create temporary file with correct extension: {str(e)}. "
                    f"Using original path: {original_path}"
                )
                return original_path

        return str(corrected_path)

    return original_path


async def _parse_file(
    doc_path: str, parsing_strategy, doc_id: str, file_name: str = None
) -> List[Document]:
    """调用新的知识库系统解析文件，返回Document列表"""
    logger.debug(
        f"[PARSE] Parsing file - Path: {doc_path}, "
        f"Strategy type: {parsing_strategy.strategy_type}"
    )

    if not doc_path:
        raise ValueError("File path is empty")

    # 检测并修正文件扩展名
    corrected_path = _get_corrected_file_path(doc_path)
    temp_file_created = False

    if corrected_path != doc_path:
        logger.info(
            f"[PARSE] Using corrected file path - "
            f"Original: {doc_path}, Corrected: {corrected_path}"
        )
        temp_file_created = True

    try:
        # 使用新的 AutoFileParser 解析文件
        parser = AutoFileParser()
        documents = await parser.parse(
            doc=corrected_path, doc_id=doc_id, file_name=file_name or Path(corrected_path).name
        )

        if not documents:
            raise ValueError(f"No content parsed from file: {doc_path}")

        logger.debug(f"[PARSE] Parsed file - Path: {doc_path}, Documents: {len(documents)}")
        return documents
    finally:
        # 清理临时文件
        if temp_file_created:
            try:
                corrected_path_obj = Path(corrected_path)
                if corrected_path_obj.exists() and corrected_path_obj != Path(doc_path):
                    corrected_path_obj.unlink()
                    logger.debug(f"[PARSE] Cleaned up temporary file: {corrected_path}")
            except Exception as e:
                logger.warning(
                    f"[PARSE] Failed to clean up temporary file {corrected_path}: {str(e)}"
                )


async def _parse_url(url: str, doc_id: str) -> List[Document]:
    """解析 URL 为 Document 列表（weblink KB）"""
    logger.debug(f"[PARSE] Parsing URL - url: {url}, doc_id: {doc_id}")
    if not url or not url.strip():
        raise ValueError("URL is empty")
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    parser = AutoLinkParser()
    if not parser.supports(url):
        raise ValueError(f"Parser does not support URL: {url}")
    documents = await parser.parse(doc=url, doc_id=doc_id, verify=False)
    if not documents:
        raise ValueError(f"No content parsed from URL: {url}")
    logger.debug(f"[PARSE] Parsed URL - url: {url}, documents: {len(documents)}")
    return documents


def _resolve_chunking_config(segmentation_strategy) -> tuple[int, float, Dict[str, bool]]:
    """提取分段配置，兼容前端字段命名"""
    cfg = segmentation_strategy.strategy_config or {}
    chunk_size = int(cfg.get("max_tokens") or cfg.get("chunk_size") or 512)
    overlap_percent = float(cfg.get("chunk_overlap_percent") or cfg.get("chunk_overlap") or 0)
    preprocess_options = {
        "normalize_whitespace": bool(
            cfg.get("remove_extra_spaces") or cfg.get("normalize_whitespace") or False
        ),
        "remove_url_email": bool(
            cfg.get("remove_urls_emails") or cfg.get("remove_url_email") or False
        ),
    }
    return chunk_size, overlap_percent, preprocess_options


def _create_chunker(segmentation_strategy, embed_model=None) -> TextChunker:
    """创建 Chunker 实例"""
    chunk_size, overlap_percent, preprocess_options = _resolve_chunking_config(
        segmentation_strategy
    )

    # 根据 strategy_type 确定 chunk_unit
    # strategy_type="1" 表示自动分段，使用字符分块
    # strategy_type="2" 表示自定义，需要检查配置
    chunk_unit = "char"  # 默认使用字符分块
    strategy_config = segmentation_strategy.strategy_config or {}
    if "chunk_unit" in strategy_config:
        chunk_unit = strategy_config.get("chunk_unit", "char")

    # 计算 chunk_overlap（绝对值，不是百分比）
    chunk_overlap = int(chunk_size * (overlap_percent / 100)) if overlap_percent > 0 else 0

    logger.debug(
        f"[CHUNK] Creating chunker - Chunk size: {chunk_size}, Overlap: {chunk_overlap} ({overlap_percent}%), "
        f"Unit: {chunk_unit}, Preprocess: {preprocess_options}"
    )

    # 如果使用 token 分块，需要提供 embed_model
    chunker = TextChunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_unit=chunk_unit,
        embed_model=embed_model if chunk_unit == "token" else None,
        preprocess_options=preprocess_options if any(preprocess_options.values()) else None,
    )

    return chunker


def _check_milvus_connection() -> Tuple[bool, str]:
    """创建知识库前的 Milvus 连通性预检：使用独立 alias 连接后验证并断开，不占用 default。

    Returns:
        tuple[bool, str]: (是否连接成功, 错误信息)
    """
    try:
        from pymilvus import connections, utility

        host, port, token = _get_milvus_connection_params()
        alias = "kb_connection_test"
        try:
            if connections.has_connection(alias):
                connections.disconnect(alias)
        except Exception as e:
            logger.warning(f"[MILVUS] Failed to disconnect connection: {alias}, Error: {str(e)}")

        connections.connect(alias=alias, host=host, port=port, token=token)

        # 验证连接是否有效（尝试列出集合）
        try:
            _ = utility.list_collections(using=alias)
        except Exception as e:
            try:
                connections.disconnect(alias)
            except Exception as disconnect_error:
                logger.warning(
                    f"[MILVUS] Failed to disconnect connection: {alias}, Error: {str(disconnect_error)}"
                )
            return False, f"无法访问 Milvus 服务: {str(e)}"

        # 断开测试连接
        try:
            connections.disconnect(alias)
        except Exception as e:
            logger.warning(f"[MILVUS] Failed to disconnect connection: {alias}, Error: {str(e)}")
        return True, ""

    except ImportError:
        # 如果没有 pymilvus，尝试使用 MilvusIndexer 来测试
        try:
            index_manager = _create_index_manager()
            # 如果 MilvusIndexer 创建成功，假设连接可用
            # 注意：这是一个简化的检查，实际连接可能在后续操作时才验证
            return True, ""
        except Exception as e:
            return False, f"无法连接到 Milvus: {str(e)}"
    except Exception as e:
        error_msg = str(e)
        # 清理连接
        try:
            alias = "kb_connection_test"
            from pymilvus import connections

            if connections.has_connection(alias):
                connections.disconnect(alias)
        except Exception as disconnect_error:
            logger.warning(
                f"[MILVUS] Failed to disconnect connection: {alias}, Error: {str(disconnect_error)}"
            )
        return False, f"Milvus 连接失败: {error_msg}"


def _check_index_connection() -> Union[ResponseModel, None]:
    """
    Function for wrapping index connection type
    based on the `INDEX_MANAGER_TYPE` variable set in `.env`.
    Returns:
        _type_: `Union[ResponseModel, None]`
    """
    index_manager_type = _CURR_INDEX_TYPE
    if index_manager_type == "milvus":
        logger.info(f"[KB_CREATE] Checking Milvus connection...")
        milvus_connected, milvus_error = _check_milvus_connection()
        if not milvus_connected:
            logger.error(f"[KB_CREATE] Milvus connection check failed - Error: {milvus_error}")
            return ResponseModel(
                code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=(
                    f"无法连接到 Milvus 服务，请检查 Milvus 配置和连接状态。"
                    f"错误信息: {milvus_error}"
                ),
            )
        logger.info(f"[KB_CREATE] Milvus connection check passed")
        return None
    else:
        # No index connection check is required by any other index type afaik.
        return None


def _get_chroma_data_dir() -> Path:
    """
    获取 Chroma 数据目录路径并确保目录存在

    Returns:
        Path: Chroma 数据目录路径
    """
    backend_dir = Path(
        __file__
    ).parent.parent.parent.parent  # 从 knowledge_base.py 回到 backend 目录
    data_dir = backend_dir / "data" / "knowledge_base"
    data_dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在
    return data_dir


def _default_index_config() -> VectorStoreConfig:
    """Default VectorStoreConfig for index manager."""
    store_provider = StoreType.Chroma if _CURR_INDEX_TYPE == "chroma" else StoreType.Milvus
    return VectorStoreConfig(
        store_provider=store_provider, collection_name="default", database_name=""
    )


def _get_milvus_connection_params() -> Tuple[str, int, Optional[str]]:
    """从环境读取 Milvus 连接参数，供连接校验与索引入口复用。返回 (host, port, token)。"""
    host = os.getenv("MILVUS_HOST", "localhost")
    port = int(os.getenv("MILVUS_PORT", "19530"))
    token = SecurityUtils.get_decrypted_secret(
        "MILVUS_TOKEN",
        os.getenv("MILVUS_TOKEN", None),
    )
    return host, port, token


def _create_milvus_index_manager(kb_id: str = "", doc_id: str = "") -> MilvusIndexer:
    """Create Milvus index manager."""
    host, port, token = _get_milvus_connection_params()
    milvus_uri = f"http://{host}:{port}"
    alias = f"idx_{kb_id}_{doc_id}" if kb_id else None
    return MilvusIndexer(
        config=_default_index_config(),
        milvus_uri=milvus_uri,
        milvus_token=token,
        milvus_alias=alias,
    )


def _create_index_manager(kb_id: str = "", doc_id: str = "") -> Union[MilvusIndexer, ChromaIndexer]:
    """
    Creates either a Milvus or Chroma index manager based on INDEX_MANAGER_TYPE.
    Returns:
        MilvusIndexer | ChromaIndexer
    """
    index_manager_type = _CURR_INDEX_TYPE
    if index_manager_type == "chroma":
        data_dir = _get_chroma_data_dir()
        return ChromaIndexer(
            config=_default_index_config(),
            chroma_path=str(data_dir),
        )
    elif index_manager_type == "milvus":
        return _create_milvus_index_manager(kb_id=kb_id, doc_id=doc_id)
    else:
        raise ValueError(f"Un-supported {index_manager_type=} for env variable INDEX_MANAGER_TYPE")


def ensure_milvus_connection_for_indexing() -> None:
    """在索引入口确保 pymilvus 的 default 连接已建立，仅当 INDEX_MANAGER_TYPE=milvus 时执行。

    文档处理与 KB 导入等异步/后台路径可能未持有 default 连接，导致 build_index 等抛出
    ConnectionNotExistException。在每次索引入口调用本函数可避免该问题；若已存在 default 连接则
    直接返回，无额外开销。
    """
    if _CURR_INDEX_TYPE != "milvus":
        return
    try:
        from pymilvus import connections
    except ImportError:
        return
    if connections.has_connection("default"):
        return
    host, port, token = _get_milvus_connection_params()
    connections.connect(alias="default", host=host, port=port, token=token)
    logger.info("[MILVUS] Ensured default connection for indexing.")


async def _delete_kb_indices(kb_id: str, space_id: str) -> dict:
    """Delete the chunks and triples collection of the knowledge base"""
    result = {"success_count": 0, "failed_count": 0, "errors": []}

    chunk_index = f"kb_{kb_id}_chunks"
    triple_index = f"kb_{kb_id}_triples"

    for collection_name in (chunk_index, triple_index):
        try:
            vector_store = _create_vector_store(
                collection_name=collection_name, kb_id=kb_id,
            )
            await vector_store.delete_table(collection_name)
            result["success_count"] += 1
            logger.info(
                f"[KB_DELETE] Collection {collection_name} dropped successfully"
            )
        except Exception as e:
            error_msg = str(e)
            # Collection not existing is not an error during deletion
            if "not exist" in error_msg.lower() or "not found" in error_msg.lower():
                logger.debug(
                    f"[KB_DELETE] Collection {collection_name} does not exist, skipping"
                )
            else:
                result["failed_count"] += 1
                result["errors"].append(f"Drop collection {collection_name}: {error_msg}")
                logger.warning(
                    f"[KB_DELETE] Failed to drop collection {collection_name}: {e}"
                )

    logger.info(
        f"[KB_DELETE] Index deletion completed - KB: {kb_id}, "
        f"Success: {result['success_count']}, Failed: {result['failed_count']}"
    )

    return result


def _create_vector_store(
    collection_name: str,
    kb_id: str = "",
    doc_id: str = "",
    for_retrieval: bool = False,
) -> Union[MilvusVectorStore, ChromaVectorStore]:
    """
    Creates either a Milvus or Chroma vector store
    based on the `INDEX_MANAGER_TYPE` variable set in `.env`.

    Args:
        collection_name: 集合名称

    Returns:
        MilvusVectorStore | ChromaVectorStore
    """
    index_manager_type = _CURR_INDEX_TYPE

    if index_manager_type == "chroma":
        data_dir = _get_chroma_data_dir()
        vector_store_config = VectorStoreConfig(
            store_provider=StoreType.Chroma,
            collection_name=collection_name,
        )
        return ChromaVectorStore(config=vector_store_config, chroma_path=str(data_dir))

    elif index_manager_type == "milvus":
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = os.getenv("MILVUS_PORT", "19530")
        milvus_token = SecurityUtils.get_decrypted_secret(
            "MILVUS_TOKEN",
            os.getenv("MILVUS_TOKEN", None),
        )

        # 组合 Milvus URI (格式: http://host:port 或 tcp://host:port)
        # 默认使用 http:// 协议
        milvus_uri = f"http://{milvus_host}:{milvus_port}"

        vector_store_config = VectorStoreConfig(
            store_provider=StoreType.Milvus,
            collection_name=collection_name,
        )
        alias = None
        if kb_id:
            alias = f"ret_{kb_id}_{collection_name}" if for_retrieval else f"vs_{kb_id}_{doc_id}_{collection_name}"
        return MilvusVectorStore(
            config=vector_store_config,
            milvus_uri=milvus_uri,
            milvus_token=milvus_token,
            milvus_alias=alias,
        )

    else:
        raise ValueError(f"Un-supported {index_manager_type=} for env variable INDEX_MANAGER_TYPE")


def get_vector_store_config(collection_name: str) -> VectorStoreConfig:
    """Return the VectorStoreConfig based on the `INDEX_MANAGER_TYPE` variable set in `.env`.

    Args:
        collection_name: Collection name

    Returns:
        VectorStoreConfig

    Raises:
        ValueError: If the configured INDEX_MANAGER_TYPE is not supported.
    """
    index_manager_type = _CURR_INDEX_TYPE

    if index_manager_type == "chroma":
        vector_store_config = VectorStoreConfig(
            store_provider=StoreType.Chroma,
            collection_name=collection_name,
        )
        return vector_store_config

    elif index_manager_type == "milvus":
        vector_store_config = VectorStoreConfig(
            store_provider=StoreType.Milvus,
            collection_name=collection_name,
        )
        return vector_store_config

    else:
        raise ValueError(f"Un-supported {index_manager_type=} for env variable INDEX_MANAGER_TYPE")
    
    
def get_vector_store_connection_config() -> Dict[str, Any]:
    """Return the vector store connection parameters
    based on the `INDEX_MANAGER_TYPE` variable set in `.env`.

    Returns:
        A dictionary containing backend-specific connection parameters

    Raises:
        ValueError: If the configured INDEX_MANAGER_TYPE is not supported.
    """
    index_manager_type = _CURR_INDEX_TYPE

    if index_manager_type == "chroma":
        data_dir = _get_chroma_data_dir()
        connection_config = {
            "chroma_path": str(data_dir),
        }
        return connection_config

    elif index_manager_type == "milvus":
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = os.getenv("MILVUS_PORT", "19530")
        milvus_token = SecurityUtils.get_decrypted_secret(
            "MILVUS_TOKEN",
            os.getenv("MILVUS_TOKEN", None),
        )
        milvus_uri = f"http://{milvus_host}:{milvus_port}"

        connection_config = {
            "milvus_uri": milvus_uri,
            "milvus_token": milvus_token,
        }
        return connection_config

    else:
        raise ValueError(f"Un-supported {index_manager_type=} for env variable INDEX_MANAGER_TYPE")


async def create_knowledge_base_for_retrieval(
    kb_id: str, space_id: str, use_graph: bool, llm_client=None, model_name: str = None
) -> Union[SimpleKnowledgeBase, GraphKnowledgeBase]:
    """创建知识库实例用于检索

    从数据库读取知识库配置，创建知识库实例用于检索操作。

    Args:
        kb_id: 知识库ID
        space_id: 空间ID
        use_graph: 是否启用图检索
        llm_client: LLM客户端（可选，如果知识库有图增强文档则需要）
        model_name: LLM模型名称（可选，用于初始化TripleExtractor，如果未提供则使用默认值）

    Returns:
        SimpleKnowledgeBase 或 GraphKnowledgeBase 实例

    Raises:
        ValueError: 如果知识库不存在或配置无效
    """
    # 1. 从数据库获取知识库信息
    kb_get = KnowledgeBaseGet(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)

    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        raise ValueError(f"Knowledge base not found (KB: {kb_id}, Space: {space_id})")

    # 3. 创建 embedding 模型
    embed_model = _create_embed_model(kb_id=kb_id, space_id=space_id)
    if not embed_model:
        raise ValueError(f"Failed to create embedding model for knowledge base {kb_id}")

    # 4. 创建向量存储
    chunk_index = f"kb_{kb_id}_chunks"
    vector_store = _create_vector_store(
        collection_name=chunk_index,
        kb_id=kb_id,
        for_retrieval=True,
    )

    # 5. 创建三元组提取器（如果使用图索引）
    extractor = None
    if use_graph:
        if not llm_client:
            raise ValueError(
                f"LLM client is required for knowledge base {kb_id} with graph enhancement"
            )
        # 使用传入的 model_name；未提供时从 llm_client 的 model_info 取配置值，再否则用默认空字符串
        resolved_model_name = model_name
        if resolved_model_name is None and llm_client is not None:
            model_info = getattr(llm_client, "model_info", None)
            if model_info is not None:
                resolved_model_name = getattr(model_info, "model_name", None)
            if resolved_model_name is None:
                model_config = getattr(llm_client, "model_config", None)
                resolved_model_name = getattr(model_config, "model_name", None) if model_config else None
        if resolved_model_name is None:
            resolved_model_name = ""
        extractor = TripleExtractor(
            llm_client=llm_client,
            model_name=resolved_model_name,
        )

    # 6. 创建知识库配置
    # 索引类型为 vector（使用 Milvus 向量存储）
    kb_config = KnowledgeBaseConfig(
        kb_id=kb_id,
        index_type="vector",
        use_graph=use_graph,
        chunk_size=512,  # 检索时不需要，使用默认值
        chunk_overlap=50,  # 检索时不需要，使用默认值
    )

    # 8. 创建知识库实例（检索时不需要 parser 和 chunker）
    if use_graph:
        knowledge_base = GraphKnowledgeBase(
            config=kb_config,
            vector_store=vector_store,
            embed_model=embed_model,
            parser=None,
            chunker=None,
            extractor=extractor,
            index_manager=None,
            llm_client=llm_client,
            llm_model_name=resolved_model_name,
        )
    else:
        knowledge_base = SimpleKnowledgeBase(
            config=kb_config,
            vector_store=vector_store,
            embed_model=embed_model,
            parser=None,
            chunker=None,
            index_manager=None,
            llm_client=llm_client,
        )

    logger.debug(
        f"[KB_RETRIEVAL] Created knowledge base instance for retrieval - KB ID: {kb_id}, Has graph: {use_graph}"
    )
    return knowledge_base


async def _delete_document_from_index(
    index_manager: Union[MilvusIndexer, ChromaIndexer],
    index_name: str,
    doc_id: str,
    kb_id: str,
    index_type: str = "chunks",
) -> bool:
    """从索引中删除指定 doc_id 的数据

    Args:
        index_manager: MilvusIndexer | ChromaIndexer
        index_name: 索引名称
        doc_id: 文档ID
        kb_id: 知识库ID
        index_type: 索引类型（"chunks" 或 "triples"），用于日志

    Returns:
        bool: 是否成功删除（如果索引不存在或数据不存在，返回 True）
    """
    try:
        # 检查索引是否存在
        index_exists = await index_manager.index_exists(index_name)
        if not index_exists:
            logger.debug(
                f"[DOC_DELETE] {index_type.capitalize()} index does not exist: {index_name}"
            )
            return True

        # Using `delete_index` from the provided `index_manager`
        deleted = await index_manager.delete_index(doc_id=doc_id, index_name=index_name)

        if deleted:
            logger.info(
                f"[DOC_DELETE] Deleted {index_type} from index - Index: {index_name}, Doc ID: {doc_id}"
            )
        else:
            logger.debug(
                f"[DOC_DELETE] No {index_type} found for doc_id: {doc_id} in index: {index_name}"
            )

        return True

    except Exception as delete_error:
        error_msg = str(delete_error)
        # 如果数据不存在，不算错误
        if "not exist" in error_msg.lower() or "not found" in error_msg.lower():
            logger.debug(
                f"[DOC_DELETE] No {index_type} found for doc_id: {doc_id} in index: {index_name}"
            )
            return True
        else:
            logger.warning(
                f"[DOC_DELETE] Failed to delete {index_type} - Doc ID: {doc_id}, KB ID: {kb_id}, Error: {delete_error}"
            )
            return False


async def _index_documents(
    documents: List[Document],
    indexing_strategy,
    segmentation_strategy,
    space_id: str,
    kb_id: str,
    doc_id: str,
    process_info: dict,
    is_weblink: bool = False,
) -> dict:
    kb_details = KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)

    # 1. 更新状态为INDEXING
    if is_weblink:
        update_indexing_result = knowledge_base_repository.weblink_update_status(
            KBWeblink(
                kb=kb_details,
                weblink_id=doc_id,
                doc_status=DocumentStatus.INDEXING.value,
                process_info={
                    **process_info,
                    "parsing_completed": True,
                    "document_count": len(documents),
                },
            )
        )
    else:
        update_indexing_result = knowledge_base_repository.document_update_status(
            KBDocument(
                kb=kb_details,
                doc_id=doc_id,
                doc_status=DocumentStatus.INDEXING.value,
                process_info={
                    **process_info,
                    "parsing_completed": True,
                    "document_count": len(documents),
                },
            )
        )

    if update_indexing_result.code != status.HTTP_200_OK:
        raise Exception(f"Failed to update status to INDEXING: {update_indexing_result.message}")

    logger.info(f"[INDEX] Document status updated to INDEXING - Doc ID: {doc_id}")

    ensure_milvus_connection_for_indexing()

    # 2. 加载配置
    use_graph = bool(getattr(indexing_strategy, "enable_graph_enhancement", False))
    chunk_index = f"kb_{kb_id}_chunks"
    triple_index = f"kb_{kb_id}_triples" if use_graph else None

    logger.debug(
        f"[INDEX] Indexing documents - KB ID: {kb_id}, Doc ID: {doc_id}, "
        f"Documents: {len(documents)}, Use graph: {use_graph}, "
        f"Chunk index: {chunk_index}, Triple index: {triple_index}"
    )

    # 3. 创建模型客户端（仅在需要时创建）
    llm_client = None
    model_name = None
    if use_graph:
        llm_client, model_name = _create_llm_client_from_db(
            indexing_strategy.llm_model_id, space_id
        )
        logger.info(
            f"[INDEX] LLM client created successfully from database - "
            f"Model ID: {indexing_strategy.llm_model_id}, Model Type: {model_name}"
        )
        if not llm_client:
            raise ValueError("llm_client is required when use_graph=True")

    # 4. 创建 embedding 模型（vector 索引类型需要）
    embed_model = _create_embed_model(kb_id=kb_id, space_id=space_id)

    # 验证 embedding 模型是否创建成功（对于 vector 索引类型，embedding 模型是必需的）
    if not embed_model:
        raise ValueError(
            f"Failed to create embedding model for knowledge base {kb_id}. "
            f"Embedding model is required for vector index type."
        )

    # 5. 创建组件
    # 5.1 创建分块器（用于 add_documents 内部自动分块）
    strategy_config = segmentation_strategy.strategy_config or {}
    chunk_unit = strategy_config.get("chunk_unit", "char")
    chunker = _create_chunker(
        segmentation_strategy, embed_model=embed_model if chunk_unit == "token" else None
    )

    # 5.2 创建索引管理器
    index_manager = _create_index_manager(kb_id=kb_id, doc_id=doc_id)

    # 5.3 创建向量存储
    vector_store = _create_vector_store(
        collection_name=chunk_index,
        kb_id=kb_id,
        doc_id=doc_id,
        for_retrieval=False,
    )

    # 5.4 创建三元组提取器（如果使用图索引）
    # model_name 来自配置（_create_llm_client_from_db 返回的 model_config.model_type）；若未提供则用默认空字符串
    extractor = None
    if use_graph and llm_client:
        extractor = TripleExtractor(
            llm_client=llm_client,
            model_name=model_name or "",
        )

    # 6. 创建知识库配置
    kb_config = KnowledgeBaseConfig(
        kb_id=kb_id,
        index_type="vector",
        use_graph=use_graph,
        chunk_size=chunker.chunk_size,
        chunk_overlap=chunker.chunk_overlap,
    )

    # 7. 创建知识库实例
    if use_graph:
        knowledge_base = GraphKnowledgeBase(
            config=kb_config,
            vector_store=vector_store,
            embed_model=embed_model,
            parser=None,
            chunker=chunker,
            extractor=extractor,
            index_manager=index_manager,
            llm_client=llm_client,
        )
    else:
        knowledge_base = SimpleKnowledgeBase(
            config=kb_config,
            vector_store=vector_store,
            embed_model=embed_model,
            parser=None,
            chunker=chunker,
            index_manager=index_manager,
            llm_client=llm_client,
        )

    # 8. 调用 add_documents 构建索引（会自动进行分块和索引构建）
    doc_ids = await knowledge_base.add_documents(documents)

    if not doc_ids:
        raise RuntimeError("Index build failed: no document IDs returned")

    # 获取实际创建的chunk数量
    chunk_count = 0
    try:
        # 尝试通过分块器估算chunk数量
        # 注意：这里只是估算，实际数量可能因为分块策略而有所不同
        total_text_length = sum(len(doc.text) for doc in documents)
        if chunker.chunk_size > 0:
            # 粗略估算：总文本长度 / chunk_size（不考虑重叠）
            estimated_chunks = max(1, total_text_length // chunker.chunk_size)
            chunk_count = estimated_chunks
            logger.debug(
                f"[INDEX] Estimated chunk count: {chunk_count} "
                f"(text length: {total_text_length}, chunk_size: {chunker.chunk_size})"
            )
    except Exception as e:
        logger.warning(f"[INDEX] Failed to estimate chunk count: {str(e)}")
        # 如果估算失败，使用文档数量作为fallback
        chunk_count = len(documents)

    logger.debug(
        f"[INDEX] Indexing completed - KB ID: {kb_id}, Doc ID: {doc_id}, "
        f"Chunk index: {chunk_index}, Triple index: {triple_index}, "
        f"Estimated chunks: {chunk_count}"
    )

    return {
        "chunk_index": chunk_index,
        "triple_index": triple_index,
        "chunk_count": chunk_count,
    }


async def process_single_document(
    space_id: str,
    kb_id: str,
    doc_id: str,
    file_path: str,
    parsing_strategy,
    segmentation_strategy,
    indexing_strategy,
    process_info: dict,
    file_name: str = None,
    obs_name: str = None,
):
    """在后台异步处理单个文档"""
    if not file_path:
        raise ValueError("file_path is required for process_single_document")
    kb_details = KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
    try:
        logger.info(
            f"[DOC_PROCESS_BG] Starting background processing - Doc ID: {doc_id}, KB ID: {kb_id}"
        )

        # Skip if stored index_manager_type != current running INDEX_MANAGER_TYPE
        try:
            stored = knowledge_base_repository.document_get(
                KBDocument(kb=kb_details, doc_id=doc_id)
            )
            if stored and stored.code == status.HTTP_200_OK and stored.data:
                stored_type = stored.data.get("index_manager_type")
                if stored_type and stored_type != _CURR_INDEX_TYPE:
                    reason = f"index_manager_type_mismatch: stored={stored_type}, current={_CURR_INDEX_TYPE}"
                    logger.info(f"[DOC_PROCESS_BG] Skipping doc {doc_id}: {reason}")
                    # mark as FAILED (or choose another status) with reason so frontend/admins see why
                    try:
                        knowledge_base_repository.document_update_status(
                            KBDocument(
                                kb=kb_details,
                                doc_id=doc_id,
                                doc_status=DocumentStatus.FAILED.value,
                                process_info={
                                    **process_info,
                                    "error": reason,
                                    "failed_time": milliseconds(),
                                },
                            )
                        )
                    except Exception:
                        logger.warning(
                            f"[DOC_PROCESS_BG] Failed to update status for skipped doc {doc_id}"
                        )
                    return
        except Exception:
            # Ignore repository read errors here and proceed; later steps will fail and set status
            logger.debug(
                f"[DOC_PROCESS_BG] Could not verify index_manager_type for doc {doc_id}, proceeding"
            )

        # 1. 解析文件
        try:
            if not file_name:
                file_name = Path(file_path).name

            # When local file is missing, fetch from OBS only if OBS is configured.
            if not os.path.exists(file_path) and obs_name and os.getenv("OBS_BUCKET"):
                logger.info(
                    f'[DOC_PROCESS_BG] Local file missing, downloading from OBS - "{obs_name}" -> "{file_path}"'
                )
                obs_manager = OBSDocumentManager()
                await obs_manager.download_document(object_name=obs_name, file_path=file_path)


        except Exception as parse_error:
            # 提取 openjiuwen 包的完整错误信息（可能包含异常链）
            full_error_msg = _extract_full_error_message(parse_error)
            error_message = f"OBS download failed: {full_error_msg}"
            logger.error(
                f"[DOC_PROCESS_BG] OBS file download failed - {file_name=}, {obs_name=}, Error: {error_message}",
                exc_info=True,
            )
            raise Exception(error_message) from parse_error

        try:
            documents = await _parse_file(file_path, parsing_strategy, doc_id, file_name=file_name)
        except Exception as parse_error:
            # 提取 openjiuwen 包的完整错误信息（可能包含异常链）
            full_error_msg = _extract_full_error_message(parse_error)
            error_message = f"File parsing failed: {full_error_msg}"
            logger.error(
                f"[DOC_PROCESS_BG] File parsing failed - Doc ID: {doc_id}, KB ID: {kb_id}, Error: {error_message}",
                exc_info=True,
            )
            raise Exception(error_message) from parse_error

        # 2. 索引文档（内部会进行分块和索引构建，并更新状态为INDEXING）
        try:
            index_result = await _index_documents(
                documents=documents,
                indexing_strategy=indexing_strategy,
                segmentation_strategy=segmentation_strategy,
                space_id=space_id,
                kb_id=kb_id,
                doc_id=doc_id,
                process_info=process_info,
            )
        except Exception as index_error:
            # 提取 openjiuwen 包的完整错误信息（可能包含异常链）
            full_error_msg = _extract_full_error_message(index_error)
            error_message = f"Index building failed: {full_error_msg}"
            logger.error(
                f"[DOC_PROCESS_BG] Index building failed - Doc ID: {doc_id}, KB ID: {kb_id}, Error: {error_message}",
                exc_info=True,
            )
            raise Exception(error_message) from index_error

        # 4. 更新文档状态为INDEXED，同时更新索引字段
        final_process_info = {
            **process_info,
            "chunking_completed": True,
            "indexing_completed": True,
            "index_result": index_result,
        }

        update_indexed_result = knowledge_base_repository.document_update_status(
            KBDocument(
                kb=kb_details,
                doc_id=doc_id,
                doc_status=DocumentStatus.INDEXED.value,
                process_info=final_process_info,
                index_name=index_result.get("chunk_index"),
                chunk_count=index_result.get("chunk_count"),
            )
        )

        if update_indexed_result.code != status.HTTP_200_OK:
            raise Exception("Failed to update status to INDEXED")

        logger.info(
            f"[DOC_PROCESS_BG] Document indexing completed - Doc ID: {doc_id}, "
            f"Chunk index: {index_result.get('chunk_index')}, "
            f"Chunks: {index_result.get('chunk_count')}, KB ID: {kb_id}"
        )

    except Exception as e:
        # 提取错误信息
        # 注意：e 是我们新创建的异常，它的消息已经包含了原始错误信息
        # 不需要遍历异常链，因为我们在创建异常时已经提取了完整的错误信息
        error_message = str(e)
        logger.error(
            f"[DOC_PROCESS_BG] Document processing failed - Doc ID: {doc_id}, "
            f"KB ID: {kb_id}, Error: {error_message}",
            exc_info=True,
        )

        # 更新状态为FAILED，记录完整的错误信息
        try:
            knowledge_base_repository.document_update_status(
                kbdoc=KBDocument(
                    kb=kb_details,
                    doc_id=doc_id,
                    doc_status=DocumentStatus.FAILED.value,
                    process_info={
                        **process_info,
                        "error": error_message,
                        "failed_time": milliseconds(),
                    },
                )
            )
        except Exception as update_error:
            logger.error(
                f"[DOC_PROCESS_BG] Failed to update status to FAILED - Doc ID: {doc_id}, "
                f"Error: {str(update_error)}"
            )


async def _process_documents_sequentially(
    space_id: str,
    kb_id: str,
    documents: list[dict],
    parsing_strategy,
    segmentation_strategy,
    indexing_strategy,
    task_id: str,
    process_info_base: dict,
):
    """串行处理多个文档（后台任务）"""
    logger.info(
        f"[DOC_PROCESS_SEQ] Starting sequential processing - Task ID: {task_id}, "
        f"KB ID: {kb_id}, Total documents: {len(documents)}"
    )

    for idx, doc_info in enumerate(documents, 1):
        doc_id = doc_info.get("doc_id")
        file_path = doc_info.get("file_path")
        obs_name = doc_info.get("obs_name")
        doc_name = doc_info.get("name")
        try:
            logger.info(
                f"[DOC_PROCESS_SEQ] Processing document {idx}/{len(documents)} - "
                f"Doc ID: {doc_id}, Task ID: {task_id}"
            )

            # 使用基础 process_info，确保包含 task_id
            process_info = {
                **process_info_base,
                "task_id": task_id,
                "current_index": idx,
                "total_count": len(documents),
            }

            # 处理单个文档
            await process_single_document(
                space_id=space_id,
                kb_id=kb_id,
                doc_id=doc_id,
                file_path=file_path,
                parsing_strategy=parsing_strategy,
                segmentation_strategy=segmentation_strategy,
                indexing_strategy=indexing_strategy,
                process_info=process_info,
                file_name=doc_name,
                obs_name=obs_name
            )

            logger.info(
                f"[DOC_PROCESS_SEQ] Completed document {idx}/{len(documents)} - "
                f"Doc ID: {doc_id}, Name: {doc_name}, Task ID: {task_id}"
            )

        except Exception as e:
            logger.error(
                f"[DOC_PROCESS_SEQ] Failed to process document {idx}/{len(documents)} - "
                f"Doc ID: {doc_id}, Task ID: {task_id}, Error: {str(e)}",
                exc_info=True,
            )
            continue

    logger.info(
        f"[DOC_PROCESS_SEQ] Sequential processing completed - Task ID: {task_id}, "
        f"KB ID: {kb_id}, Total documents: {len(documents)}"
    )


async def process_single_weblink(context: WeblinkProcessContext, task: WeblinkProcessTask):
    """在后台异步处理单个链接"""
    space_id = context.space_id
    kb_id = context.kb_id
    weblink_id = task.weblink_id
    url = task.url
    segmentation_strategy = context.segmentation_strategy
    indexing_strategy = context.indexing_strategy
    process_info = task.process_info
    kb_details = KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
    parsed_name = None
    try:
        logger.info(
            f"[WEBLINK_PROCESS_BG] Starting - Weblink ID: {weblink_id}, KB ID: {kb_id}"
        )
        documents = await _parse_url(url, weblink_id)
        for d in documents:
            if d.metadata and isinstance(d.metadata, dict):
                t = d.metadata.get("title")
                if t and isinstance(t, str) and t.strip():
                    parsed_name = t.strip()
                    break

        index_result = await _index_documents(
            documents=documents,
            indexing_strategy=indexing_strategy,
            segmentation_strategy=segmentation_strategy,
            space_id=space_id,
            kb_id=kb_id,
            doc_id=weblink_id,
            process_info=process_info,
            is_weblink=True,
        )
        final_process_info = {
            **process_info,
            "chunking_completed": True,
            "indexing_completed": True,
            "index_result": index_result,
        }
        update_data = {
            "doc_status": DocumentStatus.INDEXED.value,
            "process_info": final_process_info,
            "index_name": index_result.get("chunk_index"),
            "chunk_count": index_result.get("chunk_count"),
        }
        update_result = knowledge_base_repository.weblink_update_status(
            KBWeblink(
                kb=kb_details,
                weblink_id=weblink_id,
                doc_status=DocumentStatus.INDEXED.value,
                process_info=final_process_info,
                index_name=index_result.get("chunk_index"),
                chunk_count=index_result.get("chunk_count"),
            )
        )
        if update_result.code != status.HTTP_200_OK:
            raise Exception("Failed to update status to INDEXED")
        if parsed_name:
            knowledge_base_repository.weblink_update(
                KBWeblink(kb=kb_details, weblink_id=weblink_id),
                name=parsed_name,
            )
        logger.info(
            f"[WEBLINK_PROCESS_BG] Completed - Weblink ID: {weblink_id}, KB ID: {kb_id}"
        )
    except Exception as e:
        error_message = str(e)
        logger.error(
            f"[WEBLINK_PROCESS_BG] Failed - Weblink ID: {weblink_id}, KB ID: {kb_id}, Error: {error_message}",
            exc_info=True,
        )
        try:
            knowledge_base_repository.weblink_update_status(
                KBWeblink(
                    kb=kb_details,
                    weblink_id=weblink_id,
                    doc_status=DocumentStatus.FAILED.value,
                    process_info={
                        **process_info,
                        "error": error_message,
                        "failed_time": milliseconds(),
                    },
                )
            )
            # 即使索引失败，若解析阶段已提取到标题，也更新名称便于列表展示
            if parsed_name:
                try:
                    knowledge_base_repository.weblink_update(
                        KBWeblink(kb=kb_details, weblink_id=weblink_id),
                        name=parsed_name,
                    )
                except Exception:
                    pass
        except Exception as update_error:
            logger.error(
                f"[WEBLINK_PROCESS_BG] Failed to update FAILED status - Weblink ID: {weblink_id}, Error: {update_error}"
            )


async def _process_weblinks_sequentially(
    context: WeblinkProcessContext,
    weblinks: list[dict],
    task_id: str,
    process_info_base: dict,
):
    """串行处理多个链接"""
    kb_id = context.kb_id
    logger.info(
        f"[WEBLINK_PROCESS_SEQ] Starting - Task ID: {task_id}, KB ID: {kb_id}, Total: {len(weblinks)}"
    )
    for idx, w in enumerate(weblinks, 1):
        weblink_id = w.get("weblink_id")
        url = w.get("url")
        try:
            process_info = {
                **process_info_base,
                "task_id": task_id,
                "current_index": idx,
                "total_count": len(weblinks),
            }
            await process_single_weblink(
                context=context,
                task=WeblinkProcessTask(
                    weblink_id=weblink_id,
                    url=url,
                    process_info=process_info,
                ),
            )
        except Exception as e:
            logger.error(
                f"[WEBLINK_PROCESS_SEQ] Failed - Weblink ID: {weblink_id}, Error: {str(e)}",
                exc_info=True,
            )


async def document_upload(
    space_id: str,
    kb_id: str,
    files: List[UploadFile],
    metadata: Dict[str, Any] | None,
    current_user: dict,
) -> ResponseModel:
    """上传文档到知识库（支持多文件）

    注意：此函数是异步的，异常处理在 Router 层完成
    """
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_UPLOAD] Uploading documents - User: {user_id}, KB ID: {kb_id}, Files: {len(files)}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(space_id, current_user)

    # 2. 判断知识库来源：kb_id == ds_kb_id 时为 DeepSearch 知识库，转发到 DS 上传接口
    kb_get = KnowledgeBaseGet(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    kb_data = kb_result.data if (kb_result.code == status.HTTP_200_OK and kb_result.data) else None
    is_ds_kb = (
        kb_data is not None
        and kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )
    if not kb_data or is_ds_kb:
        # DeepSearch 知识库：转发到 DeepSearch 上传接口
        try:
            file_parts: List[Tuple[str, bytes, str]] = []
            for file in files:
                content = await file.read()
                fn = file.filename or "unnamed"
                ct = file.content_type or "application/octet-stream"
                file_parts.append((fn, content, ct))
            if not file_parts:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="No file content to upload",
                )
            ds_client = DeepSearchAgentClient()
            ds_resp = await ds_client.upload_knowledge_base_files(
                space_id=space_id,
                ds_kb_id=kb_id,
                files=file_parts,
                metadata=metadata,
            )
            if not isinstance(ds_resp, dict):
                return ResponseModel(
                    code=status.HTTP_502_BAD_GATEWAY,
                    message="DeepSearch upload returned invalid response",
                )
            if ds_resp.get("code") not in (None, status.HTTP_200_OK):
                return ResponseModel(
                    code=ds_resp.get("code", status.HTTP_502_BAD_GATEWAY),
                    message=ds_resp.get("message", "DeepSearch upload failed"),
                )
            data = ds_resp.get("data") or {}
            docs = data.get("documents") or []
            uploaded_docs = [
                DocumentUploadResponse(
                    doc_id=d.get("id") or d.get("doc_id", ""),
                    name=d.get("name", ""),
                    file_size=int(d.get("file_size", 0)),
                    status=d.get("status", DocumentStatus.UPLOADED.value),
                )
                for d in docs
            ]
            response_data = DocumentUploadBatchResponse(
                success_count=data.get("success_count", len(uploaded_docs)),
                failed_count=data.get("failed_count", 0),
                documents=uploaded_docs,
            )
            logger.info(
                f"[DOC_UPLOAD] Upload (DeepSearch) - KB ID: {kb_id}, "
                f"Success: {response_data.success_count}, Failed: {response_data.failed_count}, User: {user_id}"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Upload completed: {response_data.success_count} success, {response_data.failed_count} failed",
                data=response_data.model_dump(by_alias=False),
            )
        except Exception as e:
            logger.warning(
                f"[DOC_UPLOAD] DeepSearch upload failed - KB ID: {kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch upload failed: {str(e)}",
            )

    # 3. 获取存储路径
    storage_path = _get_storage_path(space_id, kb_id)

    # 4. 允许的文件类型
    allowed_file_extensions = {".pdf", ".doc", ".docx", ".txt", ".md"}

    # 文件大小限制：50MB
    max_file_size = 50 * 1024 * 1024  # 50MB in bytes

    # 5. 处理每个文件
    uploaded_docs = []
    success_count = 0
    failed_count = 0

    for file in files:
        try:
            # 5.1 生成文档ID
            doc_id = str(uuid.uuid4())

            # 5.2 获取文件信息并验证文件类型
            filename = file.filename or f"unnamed_{doc_id}"
            file_ext = Path(filename).suffix.lower()

            # 验证文件类型
            if file_ext not in allowed_file_extensions:
                failed_count += 1
                logger.warning(
                    f"[DOC_UPLOAD] Unsupported file type - File: {filename}, Extension: {file_ext}, "
                    f"User: {user_id}, KB ID: {kb_id}"
                )
                continue

            file_type = _get_file_type(filename)
            mime_type = _get_mime_type(file_type)

            # 4.3 保存文件到服务器
            # 使用 doc_id 作为文件名，保留原始扩展名
            safe_filename = f"{doc_id}{Path(filename).suffix}"
            file_path = storage_path / safe_filename

            # 读取文件内容并保存（异步读取）
            file_content = await file.read()
            file_size = len(file_content)

            # 验证文件大小
            if file_size > max_file_size:
                failed_count += 1
                file_size_mb = file_size / (1024 * 1024)
                max_size_mb = max_file_size / (1024 * 1024)
                logger.warning(
                    f"[DOC_UPLOAD] File size exceeds limit - File: {filename}, Size: {file_size_mb:.2f}MB, "
                    f"Limit: {max_size_mb}MB, User: {user_id}, KB ID: {kb_id}"
                )
                continue

            with open(file_path, "wb") as f:
                f.write(file_content)

            # Compute OBS object name (stored in DB even if OBS upload is disabled/unavailable)
            obs_manager = OBSDocumentManager()
            object_name = obs_manager.obs_name(
                space_id=space_id, kb_id=kb_id, file_name=file_path.name
            )

            # uploading document to OBS (best-effort; local file is source-of-truth for indexing)
            try:
                await obs_manager.upload_document(object_name=object_name, file_path=file_path)
            except Exception as obs_error:
                # Do not fail the upload request; indexing can still proceed from local storage.
                logger.warning(
                    f"[DOC_UPLOAD] OBS upload failed (continuing with local file) - "
                    f"File: {filename}, Doc ID: {doc_id}, KB ID: {kb_id}, Error: {str(obs_error)}",
                    exc_info=True,
                )

            logger.debug(f"[DOC_UPLOAD] File saved - Path: {file_path}, Size: {file_size} bytes")

            # 4.4 创建文档记录
            current_time = milliseconds()
            doc_data = {
                "space_id": space_id,
                "kb_id": kb_id,
                "doc_id": doc_id,
                "name": filename,
                "file_path": str(file_path),
                "obs_name": object_name,
                "file_size": file_size,
                "file_type": file_type,
                "mime_type": mime_type,
                "index_manager_type": _CURR_INDEX_TYPE,
                "status": DocumentStatus.UPLOADED.value,
                "doc_metadata": metadata or {},
                "create_time": current_time,
                "update_time": current_time,
            }

            create_result = knowledge_base_repository.document_create(doc_data)

            if create_result.code == status.HTTP_200_OK:
                success_count += 1
                uploaded_docs.append(
                    DocumentUploadResponse(
                        id=doc_id,
                        name=filename,
                        file_size=file_size,
                        status=DocumentStatus.UPLOADED.value,
                    )
                )
                logger.info(f"[DOC_UPLOAD] Document created - Doc ID: {doc_id}, Name: {filename}")
            else:
                failed_count += 1
                # 删除已保存的文件
                if file_path.exists():
                    file_path.unlink()
                logger.error(
                    f"[DOC_UPLOAD] Failed to create document record - Doc ID: {doc_id}, Error: {create_result.message}"
                )

        except Exception as e:
            failed_count += 1
            logger.error(
                f"[DOC_UPLOAD] Error uploading file {file.filename}: {str(e)}", exc_info=True
            )
            # 如果文件已保存，尝试删除
            try:
                if "file_path" in locals() and file_path.exists():
                    file_path.unlink()
            except Exception:
                pass

    # 5. 准备响应数据
    response_data = DocumentUploadBatchResponse(
        success_count=success_count, failed_count=failed_count, documents=uploaded_docs
    )

    logger.info(
        f"[DOC_UPLOAD] Upload completed - KB ID: {kb_id}, User: {user_id}, "
        f"Success: {success_count}, Failed: {failed_count}, Duration: {time.time() - start_time:.3f}s"
    )

    # 6. 返回上传结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message=f"Upload completed: {success_count} success, {failed_count} failed",
        data=response_data.model_dump(by_alias=False),
    )


def _timestamp_to_date_str(timestamp: int | None) -> str:
    """将时间戳（毫秒）转换为日期时间字符串（YYYY-MM-DD HH:MM:SS）"""
    if not timestamp:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 时间戳是毫秒，需要除以1000
    dt = datetime.fromtimestamp(timestamp / 1000)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@with_exception_handling
def knowledge_base_search(req: KnowledgeBaseSearchRequest, current_user: dict) -> ResponseModel:
    """查询知识库（支持分页）"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    # 获取分页参数，设置默认值
    page = req.page or 1
    page_size = req.page_size or 10

    logger.info(
        f"[KB_SEARCH] Searching knowledge bases - User: {user_id}, "
        f"Query: '{req.query}', Page: {page}, PageSize: {page_size}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 执行查询（带分页）
    search_result = knowledge_base_repository.knowledge_base_search(
        space_id=req.space_id,
        query=req.query,
        page=page,
        page_size=page_size,
        index_manager_type=_CURR_INDEX_TYPE,
    )

    if search_result.code != status.HTTP_200_OK:
        logger.error(f"[KB_SEARCH] Search failed - Error: {search_result.message}")
        return search_result

    # 3. 提取分页信息
    result_data = search_result.data
    knowledge_bases_data = result_data.get("knowledge_bases", [])
    total = result_data.get("total", 0)
    total_pages = result_data.get("total_pages", 1)

    # 4. 转换响应数据，并检查是否有图增强文档
    knowledge_bases = []
    for kb in knowledge_bases_data:
        kb_id = kb.get("kb_id", "")
        # 检查是否有图增强文档
        has_graph_enhancement = knowledge_base_repository.has_graph_enhancement_documents(
            space_id=req.space_id, kb_id=kb_id
        )
        knowledge_bases.append(
            KnowledgeBaseInfo(
                id=kb_id,
                space_id=kb.get("space_id", ""),
                name=kb.get("name", ""),
                description=kb.get("description"),
                embedding_model_config_id=kb.get("embedding_model_config_id"),
                config=kb.get("config"),
                create_time=kb.get("create_time"),
                update_time=kb.get("update_time"),
                has_graph_enhancement=has_graph_enhancement,
            )
        )

    response_data = KnowledgeBaseSearchResponse(
        knowledge_bases=knowledge_bases,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    logger.info(
        f"[KB_SEARCH] Search completed - User: {user_id}, "
        f"Found: {len(knowledge_bases)}/{total} knowledge bases, "
        f"Page: {page}/{total_pages}, Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回查询结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Search knowledge bases successfully",
        data=response_data.model_dump(
            by_alias=True
        ),  # 使用 by_alias=True 以返回 "id" 而不是 "kb_id"
    )


@with_exception_handling
def knowledge_base_list(req: KnowledgeBaseListRequest, current_user: dict) -> ResponseModel:
    """获取知识库列表（支持分页）"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[KB_LIST] Getting knowledge base list - User: {user_id}, Space ID: {req.space_id} ({_CURR_INDEX_TYPE=})"
        f"Page: {req.page}, Size: {req.size}"
    )

    # 1. 验证用户空间权限（如果 space_id 为空或验证失败，返回空列表）
    if not req.space_id:
        logger.info(f"[KB_LIST] Empty space_id, returning empty list - User: {user_id}")
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get knowledge base list success",
            data=KnowledgeBaseListResponse(
                items=[], total=0, page=req.page, size=req.size
            ).model_dump(by_alias=False),
        )

    try:
        _ = check_user_space(req.space_id, current_user)
    except Exception as e:
        logger.warning(
            f"[KB_LIST] Space check failed, returning empty list - Space ID: {req.space_id}, Error: {str(e)}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get knowledge base list success",
            data=KnowledgeBaseListResponse(
                items=[], total=0, page=req.page, size=req.size
            ).model_dump(by_alias=False),
        )

    # 2. 从数据库获取知识库列表
    list_result = knowledge_base_repository.knowledge_base_list(
        kb=KBDetails(space_id=req.space_id, index_manager_type=_CURR_INDEX_TYPE),
        page=req.page,
        size=req.size,
    )

    if list_result.code != status.HTTP_200_OK:
        logger.warning(
            f"[KB_LIST] Database query failed, returning empty list - "
            f"Space ID: {req.space_id}, Error: {list_result.message}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get knowledge base list success",
            data=KnowledgeBaseListResponse(
                items=[], total=0, page=req.page, size=req.size
            ).model_dump(by_alias=False),
        )

    # 3. 转换数据格式，并检查是否有图增强
    items = []
    for kb_data in list_result.data.get("items", []):
        kb_id = kb_data.get("kb_id", "")
        config = kb_data.get("config") or {}
        kb_type = config.get("type", "document")
        # 按 KB 类型检查图增强：weblink 查 weblink 表，document 查 document 表
        if kb_type == "weblink":
            has_graph_enhancement = knowledge_base_repository.has_graph_enhancement_weblinks(
                space_id=req.space_id, kb_id=kb_id
            )
        else:
            has_graph_enhancement = knowledge_base_repository.has_graph_enhancement_documents(
                space_id=req.space_id, kb_id=kb_id
            )

        items.append(
            KnowledgeBaseListItem(
                name=kb_data.get("name", ""),
                desc=kb_data.get("description"),
                id=kb_id,
                type=kb_type,
                embedding_model_config_id=kb_data.get("embedding_model_config_id"),
                created_at=_timestamp_to_date_str(kb_data.get("create_time")),
                updated_at=_timestamp_to_date_str(kb_data.get("update_time")),
                has_graph_enhancement=has_graph_enhancement,
                ds_kb_id=kb_data.get("ds_kb_id"),
            )
        )

    # 4. 获取分页信息
    total = list_result.data.get("total", 0)

    # 5. 构建响应数据
    response_data = KnowledgeBaseListResponse(
        items=items, total=total, page=req.page, size=req.size
    )

    logger.info(
        f"[KB_LIST] Knowledge base list retrieved - Space ID: {req.space_id}, "
        f"Total: {total}, Count: {len(items)}, Page: {req.page}, Size: {req.size}, "
        f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 6. 返回列表结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get knowledge base list success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
async def document_list(req: DocumentListRequest, current_user: dict) -> ResponseModel:
    """获取知识库文档列表（支持分页）。Studio 知识库从 Studio 表取；DeepSearch 知识库从 DeepSearch 接口取。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_LIST] Getting document list - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Page: {req.page}, Size: {req.size}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 验证知识库是否存在且判断来源：kb_id == ds_kb_id 时为 DS 知识库，文档从 DS 接口拉取；否则从 Studio 表获取
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    kb_data = kb_result.data if (kb_result.code == status.HTTP_200_OK and kb_result.data) else None
    is_ds_kb = (
        kb_data is not None
        and kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )

    if kb_data and not is_ds_kb:
        # Studio 知识库：从 Studio 数据库获取文档列表
        list_result = knowledge_base_repository.document_list(
            KBDocument(
                KBDetails(
                    space_id=req.space_id,
                    kb_id=req.kb_id,
                    index_manager_type=_CURR_INDEX_TYPE,
                ),
            ),
            page=req.page,
            size=req.size,
        )
        if list_result.code != status.HTTP_200_OK:
            logger.error(
                f"[DOC_LIST] Studio document list failed - Space ID: {req.space_id}, "
                f"KB ID: {req.kb_id}, Error: {list_result.message}"
            )
            return ResponseModel(
                code=list_result.code,
                message=list_result.message,
                data={"items": [], "total": 0, "page": req.page, "size": req.size},
            )

        # 转换数据格式
        items = []
        for doc_data in list_result.data.get("items", []):
            items.append(
                DocumentListItem(
                    name=doc_data.get("name", ""),
                    id=doc_data.get("doc_id", ""),
                    created_at=_timestamp_to_date_str(doc_data.get("create_time")),
                    updated_at=_timestamp_to_date_str(doc_data.get("update_time")),
                )
            )
        total = list_result.data.get("total", 0)
        response_data = DocumentListResponse(
            items=items, total=total, page=req.page, size=req.size
        )
        logger.info(
            f"[DOC_LIST] Document list (Studio) - Space ID: {req.space_id}, "
            f"KB ID: {req.kb_id}, Count: {len(items)}/{total}, User: {user_id}, "
            f"Duration: {time.time() - start_time:.3f}s"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get documents success",
            data=response_data.model_dump(by_alias=False),
        )

    # 3. DeepSearch 知识库（kb_id == ds_kb_id 或未在 Studio 找到）：从 DeepSearch 接口拉取文档列表
    try:
        ds_client = DeepSearchAgentClient()
        ds_resp = await ds_client.list_documents(
            space_id=req.space_id,
            kb_id=req.kb_id,
            page=req.page,
            size=req.size,
        )
    except Exception as e:
        logger.warning(
            f"[DOC_LIST] DeepSearch document list failed - space_id={req.space_id}, "
            f"kb_id={req.kb_id}, error={e}"
        )
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Knowledge base not found or document list unavailable",
        )

    if not isinstance(ds_resp, dict):
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Knowledge base not found or document list unavailable",
        )
    if ds_resp.get("code") not in (None, status.HTTP_200_OK):
        return ResponseModel(
            code=ds_resp.get("code", status.HTTP_404_NOT_FOUND),
            message=ds_resp.get("message", "Knowledge base not found or document list unavailable"),
        )
    data = ds_resp.get("data")
    if not isinstance(data, dict):
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Knowledge base not found or document list unavailable",
        )

    ds_items = data.get("items") or []
    total = data.get("total", 0)
    items = []
    for doc in ds_items:
        doc_id = doc.get("id") or doc.get("doc_id") or ""
        created_at = doc.get("created_at") or ""
        updated_at = doc.get("updated_at") or ""
        if not created_at and doc.get("create_time") is not None:
            created_at = _timestamp_to_date_str(doc.get("create_time"))
        if not updated_at and doc.get("update_time") is not None:
            updated_at = _timestamp_to_date_str(doc.get("update_time"))
        items.append(
            DocumentListItem(
                name=doc.get("name", ""),
                id=doc_id,
                created_at=created_at,
                updated_at=updated_at,
            )
        )

    response_data = DocumentListResponse(
        items=items, total=total, page=req.page, size=req.size
    )
    logger.info(
        f"[DOC_LIST] Document list (DeepSearch) - Space ID: {req.space_id}, "
        f"KB ID: {req.kb_id}, Count: {len(items)}/{total}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )
    # 4. 返回列表结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get documents success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def document_update(req: DocumentUpdateRequest, current_user: dict) -> ResponseModel:
    """更新文档信息（当前只支持更新文档名称）"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[DOC_UPDATE] Updating document - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Doc ID: {req.document_id}, Name: {req.document_name}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 验证知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(
            f"[DOC_UPDATE] Knowledge base not found - KB ID: {req.kb_id}, User: {user_id}"
        )
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    kb_details = KBDetails(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )

    # 3. 验证文档是否存在
    kb_doc = KBDocument(
        kb=kb_details,
        doc_id=req.document_id,
    )
    doc_get_result = knowledge_base_repository.document_get(kbdoc=kb_doc)
    if doc_get_result.code != status.HTTP_200_OK or not doc_get_result.data:
        logger.warning(
            f"[DOC_UPDATE] Document not found - Doc ID: {req.document_id}, KB ID: {req.kb_id}, User: {user_id}"
        )
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Document not found")

    # 4. 更新文档名称
    update_result = knowledge_base_repository.document_update(kbdoc=kb_doc, name=req.document_name)

    if update_result.code != status.HTTP_200_OK:
        logger.error(
            f"[DOC_UPDATE] Update failed - Doc ID: {req.document_id}, KB ID: {req.kb_id}, "
            f"Error: {update_result.message}"
        )
        return ResponseModel(
            code=update_result.code,
            message=update_result.message,
        )

    logger.info(
        f"[DOC_UPDATE] Document updated - Doc ID: {req.document_id}, KB ID: {req.kb_id}, "
        f"New Name: {req.document_name}, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 5. 返回更新结果
    return ResponseModel(
        code=status.HTTP_200_OK, message="update document message success", data=None
    )


@with_exception_handling
async def document_delete(req: DocumentDeleteRequest, current_user: dict) -> ResponseModel:
    """删除文档（支持批量删除）"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_DELETE] Deleting documents - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Doc IDs: {req.document_ids}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 判断知识库来源：kb_id == ds_kb_id 时为 DeepSearch 知识库，转发到 DS 删除接口
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    kb_data = kb_result.data if (kb_result.code == status.HTTP_200_OK and kb_result.data) else None
    is_ds_kb = (
        kb_data is not None
        and kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )
    if not kb_data or is_ds_kb:
        # DeepSearch 知识库：转发到 DeepSearch 删除接口
        try:
            ds_client = DeepSearchAgentClient()
            ds_resp = await ds_client.delete_documents(
                space_id=req.space_id,
                kb_id=req.kb_id,
                document_ids=req.document_ids,
            )
            if not isinstance(ds_resp, dict):
                return ResponseModel(
                    code=status.HTTP_502_BAD_GATEWAY,
                    message="DeepSearch delete returned invalid response",
                )
            if ds_resp.get("code") not in (None, status.HTTP_200_OK):
                return ResponseModel(
                    code=ds_resp.get("code", status.HTTP_502_BAD_GATEWAY),
                    message=ds_resp.get("message", "DeepSearch delete failed"),
                )
            logger.info(
                f"[DOC_DELETE] Delete (DeepSearch) - KB ID: {req.kb_id}, "
                f"Doc IDs: {len(req.document_ids)}, User: {user_id}"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Documents deleted successfully",
                data=None,
            )
        except Exception as e:
            logger.warning(
                f"[DOC_DELETE] DeepSearch delete failed - KB ID: {req.kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch delete failed: {str(e)}",
            )

    # 3. 批量删除文档
    success_count = 0
    failed_count = 0
    failed_doc_ids = []

    for doc_id in req.document_ids:
        # 验证文档是否存在
        doc_get_result = knowledge_base_repository.document_get(
            KBDocument(
                KBDetails(
                    space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
                ),
                doc_id=doc_id,
            )
        )
        if doc_get_result.code != status.HTTP_200_OK or not doc_get_result.data:
            logger.warning(
                f"[DOC_DELETE] Document not found - Doc ID: {doc_id}, KB ID: {req.kb_id}, User: {user_id}"
            )
            failed_count += 1
            failed_doc_ids.append(doc_id)
            continue

        # 获取文件路径，用于删除本地文件
        file_path = doc_get_result.data.get("file_path")
        obs_name = doc_get_result.data.get("obs_name")

        # 删除文档
        delete_result = knowledge_base_repository.document_delete(
            KBDocument(
                KBDetails(
                    space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
                ),
                doc_id=doc_id,
            )
        )

        if delete_result.code != status.HTTP_200_OK:
            logger.error(
                f"[DOC_DELETE] Delete failed - Doc ID: {doc_id}, KB ID: {req.kb_id}, "
                f"Error: {delete_result.message}"
            )
            failed_count += 1
            failed_doc_ids.append(doc_id)
        else:
            success_count += 1

            # 删除本地文件
            if file_path:
                try:
                    file_path_obj = Path(file_path)
                    if file_path_obj.exists():
                        file_path_obj.unlink()
                        logger.info(f"[DOC_DELETE] Local file deleted - Path: {file_path}")
                    else:
                        logger.warning(f"[DOC_DELETE] Local file not found - Path: {file_path}")
                except Exception as e:
                    logger.warning(
                        f"[DOC_DELETE] Failed to delete local file - Path: {file_path}, Error: {str(e)}"
                    )

            # deleting document from OBS (skip if no obs_name or OBS not configured)
            if obs_name and os.getenv("OBS_BUCKET"):
                obs_manager = OBSDocumentManager()
                await obs_manager.delete_document(obs_name)

            # 同步删除索引中的数据（使用新的知识库系统）
            try:
                # 获取文档的索引信息，判断是否使用图增强
                doc_data = doc_get_result.data
                process_info = doc_data.get("process_info", {})
                indexing_strategy = (
                    process_info.get("indexing_strategy", {})
                    if isinstance(process_info, dict)
                    else {}
                )
                use_graph = (
                    indexing_strategy.get("enable_graph_enhancement", False)
                    if isinstance(indexing_strategy, dict)
                    else False
                )

                # 创建索引管理器并删除索引数据
                index_manager = _create_index_manager(kb_id=req.kb_id)

                # 删除chunk索引中的数据
                chunk_index = f"kb_{req.kb_id}_chunks"
                await _delete_document_from_index(
                    index_manager=index_manager,
                    index_name=chunk_index,
                    doc_id=doc_id,
                    kb_id=req.kb_id,
                    index_type="chunks",
                )

                # 如果使用图增强，还需要删除triple索引中的数据
                if use_graph:
                    triple_index = f"kb_{req.kb_id}_triples"
                    await _delete_document_from_index(
                        index_manager=index_manager,
                        index_name=triple_index,
                        doc_id=doc_id,
                        kb_id=req.kb_id,
                        index_type="triples",
                    )
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    f"[DOC_DELETE] Index cleanup failed - Doc ID: {doc_id}, KB ID: {req.kb_id}, Error: {e}"
                )

    logger.info(
        f"[DOC_DELETE] Documents deletion completed - KB ID: {req.kb_id}, "
        f"Success: {success_count}, Failed: {failed_count}, "
        f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 4. 返回删除结果
    if success_count > 0:
        return ResponseModel(code=status.HTTP_200_OK, message="delete documents success", data=None)
    else:
        # 如果所有文档都删除失败，返回错误
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"Failed to delete documents: {failed_doc_ids}",
            data=None,
        )


@with_exception_handling
async def document_get_status_batch(req: DocumentStatusRequest, current_user: dict) -> ResponseModel:
    """批量查询文档状态。Studio 知识库查 Studio 表；DeepSearch 知识库调 DeepSearch 接口。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[DOC_STATUS] Getting document status batch - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Doc IDs: {len(req.doc_id_list)}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 判断是否为 Studio 知识库
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)

    kb_data = kb_result.data if (kb_result.code == status.HTTP_200_OK and kb_result.data) else None
    is_ds_kb = (
        kb_data is not None
        and kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )

    if kb_data and not is_ds_kb:
        # Studio 知识库：从 Studio 文档表查状态
        status_items = []
        for doc_id in req.doc_id_list:
            doc_result = knowledge_base_repository.document_get(
                KBDocument(
                    KBDetails(
                        space_id=req.space_id,
                        kb_id=req.kb_id,
                        index_manager_type=_CURR_INDEX_TYPE,
                    ),
                    doc_id=doc_id,
                )
            )
            if doc_result.code == status.HTTP_200_OK and doc_result.data:
                doc_data = doc_result.data
                status_value = doc_data.get("status", DocumentStatus.UPLOADING.value)
                doc_name = doc_data.get("name")
                error_msg = None
                enable_graph_enhancement = None
                process_info = doc_data.get("process_info")
                if isinstance(process_info, dict):
                    error_msg = process_info.get("error") or process_info.get("message")
                    indexing_strategy = process_info.get("indexing_strategy")
                    if isinstance(indexing_strategy, dict):
                        enable_graph_enhancement = indexing_strategy.get(
                            "enable_graph_enhancement", False
                        )
                if status_value == DocumentStatus.FAILED.value and not error_msg:
                    error_msg = "Processing failed with unknown error"
                if error_msg:
                    error_msg = _format_error_message_for_frontend(error_msg)
                status_items.append(
                    DocumentStatusResponse(
                        id=doc_id,
                        status=status_value,
                        name=doc_name,
                        error_msg=error_msg,
                        enable_graph_enhancement=enable_graph_enhancement,
                    )
                )
        response_data = DocumentStatusListResponse(items=status_items)
        logger.info(
            f"[DOC_STATUS] Document status (Studio) - Space ID: {req.space_id}, "
            f"KB ID: {req.kb_id}, Requested: {len(req.doc_id_list)}, Found: {len(status_items)}, "
            f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get document status success",
            data=response_data.model_dump(by_alias=False),
        )

    # 3. DeepSearch 知识库：调 DeepSearch 文档状态接口
    try:
        ds_client = DeepSearchAgentClient()
        ds_resp = await ds_client.get_document_status(
            space_id=req.space_id,
            kb_id=req.kb_id,
            doc_id_list=req.doc_id_list,
        )
    except Exception as e:
        logger.warning(
            f"[DOC_STATUS] DeepSearch document status failed - space_id={req.space_id}, "
            f"kb_id={req.kb_id}, error={e}"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get document status success",
            data=DocumentStatusListResponse(items=[]).model_dump(by_alias=False),
        )

    if not isinstance(ds_resp, dict) or ds_resp.get("code") not in (None, status.HTTP_200_OK):
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get document status success",
            data=DocumentStatusListResponse(items=[]).model_dump(by_alias=False),
        )
    data = ds_resp.get("data")
    if not isinstance(data, dict):
        data = {}
    ds_items = data.get("items") or []
    status_items = []
    for item in ds_items:
        doc_id = item.get("id") or item.get("doc_id") or ""
        status_items.append(
            DocumentStatusResponse(
                id=doc_id,
                status=item.get("status", DocumentStatus.UPLOADING.value),
                name=item.get("name"),
                error_msg=item.get("error_msg"),
                enable_graph_enhancement=item.get("enable_graph_enhancement"),
            )
        )
    response_data = DocumentStatusListResponse(items=status_items)
    logger.info(
        f"[DOC_STATUS] Document status (DeepSearch) - Space ID: {req.space_id}, "
        f"KB ID: {req.kb_id}, Requested: {len(req.doc_id_list)}, Found: {len(status_items)}, "
        f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get document status success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
async def document_process(req: DocumentProcessRequest, current_user: dict) -> ResponseModel:
    """启动文档处理流程。Studio 知识库走本地 _process_documents_sequentially；DeepSearch 知识库转发到 DeepSearch /api/kb/process 建索引。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_PROCESS] Starting document processing - User: {user_id}, "
        f"KB ID: {req.kb_id}, Files: {len(req.doc_id_list)}"
    )

    _ = check_user_space(req.space_id, current_user)

    # 判断知识库来源：kb_id == ds_kb_id 时为 DeepSearch 知识库，转发到 DS 建索引接口
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    kb_data = kb_result.data if (kb_result.code == status.HTTP_200_OK and kb_result.data) else None
    is_ds_kb = (
        kb_data is not None
        and kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )
    if not kb_data or is_ds_kb:
        # DeepSearch 知识库：转发到 DeepSearch 建索引接口
        try:
            process_payload = {
                "space_id": req.space_id,
                "kb_id": req.kb_id,
                "doc_id_list": req.doc_id_list,
                "parsing_strategy": req.parsing_strategy.model_dump()
                if hasattr(req.parsing_strategy, "model_dump")
                else (req.parsing_strategy or {}),
                "segmentation_strategy": req.segmentation_strategy.model_dump()
                if hasattr(req.segmentation_strategy, "model_dump")
                else (req.segmentation_strategy or {}),
                "indexing_strategy": req.indexing_strategy.model_dump()
                if hasattr(req.indexing_strategy, "model_dump")
                else (req.indexing_strategy or {}),
            }
            try:
                _apply_ds_process_llm_config(
                    process_payload, req.space_id
                )
            except ValueError as e:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=str(e),
                )
            ds_client = DeepSearchAgentClient()
            result = await ds_client.process_knowledge_base_documents(process_payload)
            if not isinstance(result, dict):
                return ResponseModel(
                    code=status.HTTP_502_BAD_GATEWAY,
                    message="DeepSearch process returned invalid response",
                )
            if result.get("code") not in (None, status.HTTP_200_OK):
                return ResponseModel(
                    code=result.get("code", status.HTTP_502_BAD_GATEWAY),
                    message=result.get("message", "DeepSearch process failed"),
                )
            data = result.get("data") or {}
            logger.info(
                f"[DOC_PROCESS] DeepSearch process submitted - KB ID: {req.kb_id}, "
                f"task_id: {data.get('task_id')}, User: {user_id}"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Document process submitted",
                data=data,
            )
        except Exception as e:
            logger.warning(
                f"[DOC_PROCESS] DeepSearch process failed - KB ID: {req.kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch process failed: {str(e)}",
            )

    processed_count = 0
    failed_count = 0
    failed_docs: list[str] = []
    task_id = str(uuid.uuid4())
    current_time = milliseconds()

    # 构建基础 process_info（用于所有文档）
    process_info_base = {
        "task_id": task_id,
        "parsing_strategy": req.parsing_strategy.model_dump(),
        "segmentation_strategy": req.segmentation_strategy.model_dump(),
        "indexing_strategy": req.indexing_strategy.model_dump(),
        "start_time": current_time,
    }

    # 收集有效文档信息（用于串行处理）
    valid_documents: list[dict] = []

    kb_details = KBDetails(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )

    # 第一阶段：验证所有文档并更新状态
    for doc_id in req.doc_id_list:
        try:
            doc_result = knowledge_base_repository.document_get(
                KBDocument(
                    kb=kb_details,
                    doc_id=doc_id,
                )
            )

            if doc_result.code != status.HTTP_200_OK or not doc_result.data:
                failed_count += 1
                failed_docs.append(doc_id)
                logger.warning(f"[DOC_PROCESS] Document not found - Doc ID: {doc_id}")
                # 尝试更新状态为FAILED（如果文档存在但查询失败）
                try:
                    knowledge_base_repository.document_update_status(
                        KBDocument(
                            kb=kb_details,
                            doc_id=doc_id,
                            doc_status=DocumentStatus.FAILED.value,
                            process_info={
                                **process_info_base,
                                "error": "Document not found",
                                "failed_time": milliseconds(),
                            },
                        )
                    )
                except Exception:
                    # 如果文档不存在，无法更新状态，这是正常的
                    pass
                continue

            current_status = doc_result.data.get("status")
            if current_status != DocumentStatus.UPLOADED.value:
                failed_count += 1
                failed_docs.append(doc_id)
                logger.warning(
                    f"[DOC_PROCESS] Document status invalid - Doc ID: {doc_id}, Current status: {current_status}"
                )
                try:
                    knowledge_base_repository.document_update_status(
                        KBDocument(
                            kb=kb_details,
                            doc_id=doc_id,
                            doc_status=DocumentStatus.FAILED.value,
                            process_info={
                                **process_info_base,
                                "error": "Document status invalid",
                                "failed_time": milliseconds(),
                            },
                        )
                    )
                except Exception as update_error:
                    logger.error(
                        f"[DOC_PROCESS] Failed to update FAILED status - Doc ID: {doc_id}, Error: {str(update_error)}"
                    )
                continue

            file_path = doc_result.data.get("file_path")
            if not file_path:
                failed_count += 1
                failed_docs.append(doc_id)
                logger.error(f"[DOC_PROCESS] File path not found for document {doc_id}")
                knowledge_base_repository.document_update_status(
                    KBDocument(
                        kb=kb_details,
                        doc_id=doc_id,
                        doc_status=DocumentStatus.FAILED.value,
                        process_info={
                            **process_info_base,
                            "error": "File path not found",
                            "failed_time": milliseconds(),
                        },
                    )
                )
                continue

            # 更新文档状态为 PROCESSING
            kb_details = KBDetails(
                space_id=req.space_id,
                kb_id=req.kb_id,
                index_manager_type=_CURR_INDEX_TYPE,
            )
            update_result = knowledge_base_repository.document_update_status(
                kbdoc=KBDocument(
                    kb=kb_details,
                    doc_id=doc_id,
                    doc_status=DocumentStatus.PROCESSING.value,
                    process_info=process_info_base,
                )
            )

            if update_result.code != status.HTTP_200_OK:
                failed_count += 1
                failed_docs.append(doc_id)
                logger.error(
                    f"[DOC_PROCESS] Failed to update document status - "
                    f"Doc ID: {doc_id}, Error: {update_result.message}"
                )
                try:
                    knowledge_base_repository.document_update_status(
                        KBDocument(
                            kb=kb_details,
                            doc_id=doc_id,
                            doc_status=DocumentStatus.FAILED.value,
                            process_info={
                                **process_info_base,
                                "error": "Failed to update document status",
                                "failed_time": milliseconds(),
                            },
                        )
                    )
                except Exception as update_error:
                    logger.error(
                        f"[DOC_PROCESS] Failed to update FAILED status - Doc ID: {doc_id}, Error: {str(update_error)}"
                    )
                continue
            doc_name = doc_result.data.get("name")
            doc_obs_name = doc_result.data.get("obs_name")
            # 收集有效文档信息
            valid_documents.append(
                {
                    "doc_id": doc_id,
                    "file_path": file_path,
                    "name": doc_name,
                    "obs_name": doc_obs_name,
                }
            )
            processed_count += 1
            logger.info(
                f"[DOC_PROCESS] Document validated and status updated to PROCESSING - Doc ID: {doc_id}"
            )

        except Exception as e:
            failed_count += 1
            failed_docs.append(doc_id)
            logger.error(
                f"[DOC_PROCESS] Failed to validate document - Doc ID: {doc_id}, "
                f"KB ID: {req.kb_id}, Error: {str(e)}",
                exc_info=True,
            )

            try:
                knowledge_base_repository.document_update_status(
                    KBDocument(
                        kb=kb_details,
                        doc_id=doc_id,
                        doc_status=DocumentStatus.FAILED.value,
                        process_info={
                            **process_info_base,
                            "error": "Document validation failed",
                            "failed_time": milliseconds(),
                        },
                    )
                )
            except Exception as update_error:
                logger.error(
                    f"[DOC_PROCESS] Failed to update FAILED status - Doc ID: {doc_id}, Error: {str(update_error)}",
                    exc_info=True,
                )

    # 第二阶段：如果有有效文档，创建后台任务串行处理
    if valid_documents:
        logger.info(
            f"[DOC_PROCESS] Creating sequential processing task - Task ID: {task_id}, "
            f"Valid documents: {len(valid_documents)}, KB ID: {req.kb_id}"
        )

        # 创建后台任务，串行处理所有文档
        asyncio.create_task(
            _process_documents_sequentially(
                space_id=req.space_id,
                kb_id=req.kb_id,
                documents=valid_documents,
                parsing_strategy=req.parsing_strategy,
                segmentation_strategy=req.segmentation_strategy,
                indexing_strategy=req.indexing_strategy,
                task_id=task_id,
                process_info_base=process_info_base,
            )
        )

        logger.info(
            f"[DOC_PROCESS] Sequential processing task created - Task ID: {task_id}, "
            f"KB ID: {req.kb_id}, Documents to process: {len(valid_documents)}"
        )

    response_data = DocumentProcessResponse(
        task_id=task_id,
        processed_count=processed_count,
        failed_count=failed_count,
        failed_docs=failed_docs,
    )

    logger.info(
        f"[DOC_PROCESS] Document processing tasks started - Task ID: {task_id}, "
        f"KB ID: {req.kb_id}, User: {user_id}, "
        f"Processed: {processed_count}, Failed: {failed_count}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Document processing tasks started",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
def task_progress(req: TaskProgressRequest, current_user: dict) -> ResponseModel:
    """查询任务处理进度"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[TASK_PROGRESS] Querying task progress - User: {user_id}, "
        f"Task ID: {req.task_id}, KB ID: {req.kb_id}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 验证知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(
            f"[TASK_PROGRESS] Knowledge base not found - KB ID: {req.kb_id}, User: {user_id}"
        )
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    kb_details = KBDetails(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    # 3. 按 KB 类型查询：weblink 查 weblink_list，否则查 document_list
    config = kb_result.data.get("config") or {}
    kb_type = config.get("type", "document")
    if kb_type == "weblink":
        list_result = knowledge_base_repository.weblink_list(
            kb_weblink=KBWeblink(kb=kb_details),
            page=1,
            size=1000,
        )
        id_key = "weblink_id"
    else:
        list_result = knowledge_base_repository.document_list(
            kbdoc=KBDocument(kb=kb_details),
            page=1,
            size=1000,
        )
        id_key = "doc_id"

    if list_result.code != status.HTTP_200_OK:
        logger.error(
            f"[TASK_PROGRESS] Failed to query documents - Space ID: {req.space_id}, "
            f"KB ID: {req.kb_id}, Error: {list_result.message}"
        )
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    # 4. 筛选出属于该任务的文档并计算进度
    task_items = []
    total_count = 0
    processed_count = 0
    success_count = 0
    failed_count = 0

    for doc_data in list_result.data.get("items", []):
        process_info = doc_data.get("process_info", {})
        if isinstance(process_info, dict) and process_info.get("task_id") == req.task_id:
            total_count += 1
            doc_id = doc_data.get(id_key, doc_data.get("doc_id", ""))
            doc_name = doc_data.get("name", "")
            doc_status = doc_data.get("status", "")

            # 统计计数
            if doc_status == DocumentStatus.INDEXED.value:
                success_count += 1
            elif doc_status == DocumentStatus.FAILED.value:
                failed_count += 1

            if doc_status in [
                DocumentStatus.PROCESSING.value,
                DocumentStatus.INDEXING.value,
                DocumentStatus.INDEXED.value,
            ]:
                processed_count += 1

            error = None
            if doc_status == DocumentStatus.FAILED.value:
                error = process_info.get("error", "Unknown error")

            task_items.append(
                TaskProgressItem(doc_id=doc_id, doc_name=doc_name, status=doc_status, error=error)
            )

    # 5. 构建响应数据
    response_data = TaskProgressResponse(
        task_id=req.task_id,
        total_count=total_count,
        processed_count=processed_count,
        success_count=success_count,
        failed_count=failed_count,
        items=task_items,
    )

    logger.info(
        f"[TASK_PROGRESS] Task progress retrieved - Task ID: {req.task_id}, "
        f"KB ID: {req.kb_id}, Total: {total_count}, Processed: {processed_count}, "
        f"Success: {success_count}, Failed: {failed_count}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    # 6. 返回查询结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get task progress success",
        data=response_data.model_dump(by_alias=False),
    )


# ==================== Weblink Manager ====================


@with_exception_handling
async def weblink_add(req: WeblinkAddRequest, current_user: dict) -> ResponseModel:
    """添加链接到知识库。

    - Studio 知识库：URL 落 weblink 表，等待用户在 step2 触发 weblink_process 解析+索引。
    - DS 镜像知识库：直接解析每条 URL → 合成 .md → 上传到 DS（与同步语义一致），
      返回 DS 文档 id 列表，供前端在 step2 调 weblink_process 触发 DS 建索引。
    """
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[WEBLINK_ADD] Adding weblinks - User: {user_id}, KB ID: {req.kb_id}, URLs: {len(req.urls)}"
    )
    _ = check_user_space(req.space_id, current_user)
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    kb_data_for_mirror = kb_result.data
    is_ds_kb = bool(
        kb_data_for_mirror.get("kb_id")
        and kb_data_for_mirror.get("kb_id") == kb_data_for_mirror.get("ds_kb_id")
    )
    if is_ds_kb:
        # 镜像 KB：解析 URL → .md → DS upload，返回 DS 文档 id（前端继续走 weblink_process 触发 DS 建索引）
        valid_urls_mirror: list[str] = []
        invalid_count = 0
        for url in req.urls:
            u = (url or "").strip()
            if not u or not u.lower().startswith(("http://", "https://")):
                invalid_count += 1
                continue
            valid_urls_mirror.append(u)
        if not valid_urls_mirror:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="No valid URLs to add",
            )
        files_for_ds: List[Tuple[str, bytes, str]] = []
        new_doc_ids: List[str] = []
        url_for_id: List[str] = []
        for u in valid_urls_mirror:
            try:
                docs = await _parse_url(u, str(uuid.uuid4()))
            except Exception as e:
                logger.warning(
                    f"[WEBLINK_ADD] Failed to parse weblink (mirror), skip - "
                    f"kb_id={req.kb_id}, url={u}, error={e}"
                )
                continue
            title: Optional[str] = None
            for d in docs:
                md = getattr(d, "metadata", None)
                if isinstance(md, dict):
                    t = md.get("title")
                    if t and isinstance(t, str) and t.strip():
                        title = t.strip()
                        break
            body_parts: List[str] = []
            for d in docs:
                txt = getattr(d, "text", None)
                if txt and isinstance(txt, str) and txt.strip():
                    body_parts.append(txt.strip())
            body = "\n\n".join(body_parts).strip()
            if not body:
                logger.warning(
                    f"[WEBLINK_ADD] Weblink parsed to empty content (mirror), skip - "
                    f"kb_id={req.kb_id}, url={u}"
                )
                continue
            display_name = title or u
            markdown = f"# {display_name}\n\n源链接：{u}\n\n{body}\n"
            filename = _safe_synthetic_filename(display_name, ".md")
            files_for_ds.append((filename, markdown.encode("utf-8"), "text/markdown"))
            new_doc_ids.append(str(uuid.uuid4()))
            url_for_id.append(u)
        if not files_for_ds:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="All URLs failed to parse",
            )
        try:
            ds_client = DeepSearchAgentClient()
            # 注意: DS 的 /api/kb/upload 当传 metadata.doc_list 时,
            # 会把"不在 doc_list 里的现有文档"全部删掉(覆盖同步语义,
            # sync_upload 走的就是这条路径).
            # 镜像 KB 上的"add"是纯追加,绝不能传 doc_list,否则会把
            # 上一次同步过来的链接全部清掉.
            ds_resp = await ds_client.upload_knowledge_base_files(
                space_id=req.space_id,
                ds_kb_id=req.kb_id,
                files=files_for_ds,
                metadata=None,
            )
        except Exception as e:
            logger.warning(
                f"[WEBLINK_ADD] DeepSearch upload failed (mirror) - "
                f"kb_id={req.kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch upload failed: {str(e)}",
            )
        # 优先用 DS 返回的 id（更准确）；否则退回我们生成的占位 id
        returned_ids: List[str] = []
        if isinstance(ds_resp, dict):
            data_ds = ds_resp.get("data") or {}
            for d in data_ds.get("documents") or []:
                rid = d.get("id") or d.get("doc_id")
                if rid:
                    returned_ids.append(rid)
        if len(returned_ids) != len(new_doc_ids):
            returned_ids = new_doc_ids
        links = [
            WeblinkAddItem(
                id=returned_ids[i],
                url=url_for_id[i],
                name=files_for_ds[i][0],
                status=DocumentStatus.UPLOADED.value,
            )
            for i in range(len(returned_ids))
        ]
        logger.info(
            f"[WEBLINK_ADD] Add (DeepSearch mirror) - KB ID: {req.kb_id}, "
            f"Success: {len(links)}, Skipped: {len(req.urls) - len(links)}, "
            f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="add weblinks success",
            data=WeblinkAddBatchResponse(
                success_count=len(links),
                failed_count=invalid_count + (len(valid_urls_mirror) - len(links)),
                links=links,
            ).model_dump(by_alias=False),
        )

    config = kb_result.data.get("config") or {}
    if config.get("type") != "weblink":
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Knowledge base is not a weblink type",
        )
    if len(req.urls) > WEBLINK_KB_MAX_LINKS:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=(
                f"At most {WEBLINK_KB_MAX_LINKS} URL lines per request "
                f"(received {len(req.urls)})"
            ),
        )
    valid_urls: list[str] = []
    for url in req.urls:
        u = (url or "").strip()
        if not u or not u.lower().startswith(("http://", "https://")):
            continue
        valid_urls.append(u)
    if valid_urls:
        list_result = knowledge_base_repository.weblink_list(
            KBWeblink(
                kb=KBDetails(
                    space_id=req.space_id,
                    kb_id=req.kb_id,
                    index_manager_type=_CURR_INDEX_TYPE,
                )
            ),
            page=1,
            size=1,
        )
        existing = 0
        if list_result.code == status.HTTP_200_OK and list_result.data:
            existing = int(list_result.data.get("total") or 0)
        if existing + len(valid_urls) > WEBLINK_KB_MAX_LINKS:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=(
                    f"Weblink knowledge base allows at most {WEBLINK_KB_MAX_LINKS} links "
                    f"({existing} existing; cannot add {len(valid_urls)} in this batch)"
                ),
            )
    links = []
    success_count = 0
    failed_count = 0
    for url in req.urls:
        url = (url or "").strip()
        if not url:
            failed_count += 1
            continue
        if not url.lower().startswith(("http://", "https://")):
            failed_count += 1
            continue
        weblink_id = str(uuid.uuid4())
        weblink_data = {
            "space_id": req.space_id,
            "kb_id": req.kb_id,
            "weblink_id": weblink_id,
            "url": url,
            "name": url,
            "status": DocumentStatus.UPLOADED.value,
            "index_manager_type": _CURR_INDEX_TYPE,
        }
        create_result = knowledge_base_repository.weblink_create(weblink_data)
        if create_result.code == status.HTTP_200_OK:
            success_count += 1
            links.append(
                WeblinkAddItem(
                    id=weblink_id,
                    url=url,
                    name=url,
                    status=DocumentStatus.UPLOADED.value,
                )
            )
        else:
            failed_count += 1
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="add weblinks success",
        data=WeblinkAddBatchResponse(
            success_count=success_count,
            failed_count=failed_count,
            links=links,
        ).model_dump(by_alias=False),
    )


@with_exception_handling
async def weblink_list(req: WeblinkListRequest, current_user: dict) -> ResponseModel:
    """获取链接列表。Studio 知识库从 Studio 表取；DeepSearch 镜像知识库从 DS 接口取
    （weblink 同步时把每条链接合成成一个 .md 文件上传到 DS，所以镜像里看到的是这些合成文件）。
    """
    _ = check_user_space(req.space_id, current_user)
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    kb_data = kb_result.data
    is_ds_kb = bool(
        kb_data.get("kb_id")
        and kb_data.get("kb_id") == kb_data.get("ds_kb_id")
    )

    # DS 镜像 KB：转发到 DS 文档列表，否则用户在镜像 KB 里永远看不到同步过去的内容
    if is_ds_kb:
        try:
            ds_client = DeepSearchAgentClient()
            ds_resp = await ds_client.list_documents(
                space_id=req.space_id,
                kb_id=req.kb_id,
                page=req.page,
                size=req.size,
            )
        except Exception as e:
            logger.warning(
                f"[WEBLINK_LIST] DeepSearch document list failed (mirror weblink KB) - "
                f"space_id={req.space_id}, kb_id={req.kb_id}, error={e}"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="get weblink list success",
                data=WeblinkListResponse(
                    items=[], total=0, page=req.page, size=req.size
                ).model_dump(by_alias=False),
            )
        data = ds_resp.get("data") if isinstance(ds_resp, dict) else None
        if not isinstance(data, dict):
            data = {}
        ds_items = data.get("items") or []
        items = []
        for doc in ds_items:
            doc_id = doc.get("id") or doc.get("doc_id") or ""
            created_at = doc.get("created_at") or ""
            updated_at = doc.get("updated_at") or ""
            if not created_at and doc.get("create_time") is not None:
                created_at = _timestamp_to_date_str(doc.get("create_time"))
            if not updated_at and doc.get("update_time") is not None:
                updated_at = _timestamp_to_date_str(doc.get("update_time"))
            items.append(
                WeblinkListItem(
                    name=doc.get("name", ""),
                    id=doc_id,
                    # DS 不保存原始 URL；展示一个空串，前端据此判断"镜像项不可访问 URL"即可
                    url="",
                    created_at=created_at,
                    updated_at=updated_at,
                )
            )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get weblink list success",
            data=WeblinkListResponse(
                items=items,
                total=data.get("total", len(items)),
                page=req.page,
                size=req.size,
            ).model_dump(by_alias=False),
        )

    list_result = knowledge_base_repository.weblink_list(
        KBWeblink(kb=KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE)),
        page=req.page,
        size=req.size,
    )
    if list_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
            data={"items": [], "total": 0, "page": req.page, "size": req.size},
        )
    data = list_result.data
    items = [
        WeblinkListItem(
            name=w.get("name", ""),
            id=w.get("weblink_id", ""),
            url=w.get("url", ""),
            created_at=_timestamp_to_date_str(w.get("create_time")),
            updated_at=_timestamp_to_date_str(w.get("update_time")),
        )
        for w in data.get("items", [])
    ]
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get weblink list success",
        data=WeblinkListResponse(
            items=items,
            total=data.get("total", 0),
            page=data.get("page", req.page),
            size=data.get("size", req.size),
        ).model_dump(by_alias=False),
    )


@with_exception_handling
async def weblink_process(req: WeblinkProcessRequest, current_user: dict) -> ResponseModel:
    """处理链接（解析并索引）。Studio 知识库走本地解析+索引；DS 镜像知识库转发 DS 建索引。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[WEBLINK_PROCESS] Starting weblink processing - User: {user_id}, "
        f"KB ID: {req.kb_id}, Links: {len(req.weblink_id_list)}"
    )
    _ = check_user_space(req.space_id, current_user)
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")
    kb_data_for_mirror = kb_result.data
    is_ds_kb = bool(
        kb_data_for_mirror.get("kb_id")
        and kb_data_for_mirror.get("kb_id") == kb_data_for_mirror.get("ds_kb_id")
    )
    if is_ds_kb:
        # 镜像 KB：转发 DS 建索引；req.weblink_id_list 在镜像里实际是 DS 的 doc_id
        try:
            process_payload: Dict[str, Any] = {
                "space_id": req.space_id,
                "kb_id": req.kb_id,
                "doc_id_list": req.weblink_id_list,
                "parsing_strategy": req.parsing_strategy.model_dump()
                if hasattr(req.parsing_strategy, "model_dump")
                else (req.parsing_strategy or {}),
                "segmentation_strategy": req.segmentation_strategy.model_dump()
                if hasattr(req.segmentation_strategy, "model_dump")
                else (req.segmentation_strategy or {}),
                "indexing_strategy": req.indexing_strategy.model_dump()
                if hasattr(req.indexing_strategy, "model_dump")
                else (req.indexing_strategy or {}),
            }
            try:
                _apply_ds_process_llm_config(process_payload, req.space_id)
            except ValueError as e:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=str(e),
                )
            ds_client = DeepSearchAgentClient()
            result = await ds_client.process_knowledge_base_documents(process_payload)
            if not isinstance(result, dict):
                return ResponseModel(
                    code=status.HTTP_502_BAD_GATEWAY,
                    message="DeepSearch process returned invalid response",
                )
            if result.get("code") not in (None, status.HTTP_200_OK):
                return ResponseModel(
                    code=result.get("code", status.HTTP_502_BAD_GATEWAY),
                    message=result.get("message", "DeepSearch process failed"),
                )
            data = result.get("data") or {}
            logger.info(
                f"[WEBLINK_PROCESS] DeepSearch process submitted (mirror) - "
                f"KB ID: {req.kb_id}, task_id: {data.get('task_id')}, "
                f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="weblink process submitted",
                data={
                    "task_id": data.get("task_id"),
                    "processed_count": len(req.weblink_id_list),
                    "failed_count": 0,
                    "failed_links": [],
                },
            )
        except Exception as e:
            logger.warning(
                f"[WEBLINK_PROCESS] DeepSearch process failed (mirror) - "
                f"KB ID: {req.kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch process failed: {str(e)}",
            )
    config = kb_result.data.get("config") or {}
    if config.get("type") != "weblink":
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message="Knowledge base is not a weblink type",
        )
    task_id = str(uuid.uuid4())
    process_info_base = {
        "task_id": task_id,
        "parsing_strategy": req.parsing_strategy.model_dump(),
        "segmentation_strategy": req.segmentation_strategy.model_dump(),
        "indexing_strategy": req.indexing_strategy.model_dump(),
        "start_time": milliseconds(),
    }
    valid_weblinks = []
    failed_count = 0
    failed_links = []
    kb_details = KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE)
    for weblink_id in req.weblink_id_list:
        get_result = knowledge_base_repository.weblink_get(KBWeblink(kb=kb_details, weblink_id=weblink_id))
        if get_result.code != status.HTTP_200_OK or not get_result.data:
            failed_count += 1
            failed_links.append(weblink_id)
            continue
        w = get_result.data
        if w.get("status") != DocumentStatus.UPLOADED.value:
            failed_count += 1
            failed_links.append(weblink_id)
            # 状态无效时更新为 FAILED
            try:
                knowledge_base_repository.weblink_update_status(
                    KBWeblink(kb=kb_details, weblink_id=weblink_id),
                    doc_status=DocumentStatus.FAILED.value,
                    process_info={
                        **process_info_base,
                        "error": "Weblink status invalid",
                        "failed_time": milliseconds(),
                    },
                )
            except Exception:
                pass
            continue
        knowledge_base_repository.weblink_update_status(
            KBWeblink(
                kb=kb_details,
                weblink_id=weblink_id,
                doc_status=DocumentStatus.PROCESSING.value,
                process_info=process_info_base,
            )
        )
        valid_weblinks.append({"weblink_id": weblink_id, "url": w.get("url", "")})
    asyncio.create_task(
        _process_weblinks_sequentially(
            context=WeblinkProcessContext(
                space_id=req.space_id,
                kb_id=req.kb_id,
                parsing_strategy=req.parsing_strategy,
                segmentation_strategy=req.segmentation_strategy,
                indexing_strategy=req.indexing_strategy,
            ),
            weblinks=valid_weblinks,
            task_id=task_id,
            process_info_base=process_info_base,
        )
    )
    logger.info(
        f"[WEBLINK_PROCESS] Weblink processing tasks started - Task ID: {task_id}, "
        f"KB ID: {req.kb_id}, User: {user_id}, "
        f"Processed: {len(valid_weblinks)}, Failed: {failed_count}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="Weblink processing started",
        data=WeblinkProcessResponse(
            task_id=task_id,
            processed_count=len(valid_weblinks),
            failed_count=failed_count,
            failed_links=failed_links,
        ).model_dump(by_alias=False),
    )


def _name_needs_refresh(name: str, url: str) -> bool:
    """判断链接名称是否需要从 URL 重新解析（当前仍是 URL 或空）"""
    if not name or not name.strip():
        return True
    n, u = (name or "").strip(), (url or "").strip()
    if n == u:
        return True
    if n.lower().startswith(("http://", "https://")):
        return True
    return False


@with_exception_handling
async def weblink_get_status_batch(req: WeblinkStatusRequest, current_user: dict) -> ResponseModel:
    """批量查询链接状态。Studio 知识库查 Studio 表；DS 镜像知识库调 DS 文档状态接口。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[WEBLINK_STATUS] Getting weblink status batch - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Weblink IDs: {len(req.weblink_id_list)}"
    )
    _ = check_user_space(req.space_id, current_user)
    kb_details = KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE)

    # DS 镜像 KB:状态从 DS 拉取（id 是 DS doc_id，不在 Studio weblink 表里）
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result_for_mirror = knowledge_base_repository.knowledge_base_get(kb_get)
    kb_data_for_mirror = (
        kb_result_for_mirror.data
        if (kb_result_for_mirror.code == status.HTTP_200_OK and kb_result_for_mirror.data)
        else None
    )
    is_ds_kb = bool(
        kb_data_for_mirror
        and kb_data_for_mirror.get("kb_id")
        and kb_data_for_mirror.get("kb_id") == kb_data_for_mirror.get("ds_kb_id")
    )
    if is_ds_kb:
        try:
            ds_client = DeepSearchAgentClient()
            ds_resp = await ds_client.get_document_status(
                space_id=req.space_id,
                kb_id=req.kb_id,
                doc_id_list=req.weblink_id_list,
            )
        except Exception as e:
            logger.warning(
                f"[WEBLINK_STATUS] DeepSearch document status failed (mirror weblink KB) - "
                f"space_id={req.space_id}, kb_id={req.kb_id}, error={e}"
            )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="get weblink status success",
                data=DocumentStatusListResponse(items=[]).model_dump(by_alias=False),
            )
        if not isinstance(ds_resp, dict) or ds_resp.get("code") not in (None, status.HTTP_200_OK):
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="get weblink status success",
                data=DocumentStatusListResponse(items=[]).model_dump(by_alias=False),
            )
        data = ds_resp.get("data") if isinstance(ds_resp, dict) else None
        if not isinstance(data, dict):
            data = {}
        ds_items = data.get("items") or []
        status_items = []
        for item in ds_items:
            doc_id = item.get("id") or item.get("doc_id") or ""
            status_items.append(
                DocumentStatusResponse(
                    id=doc_id,
                    status=item.get("status", DocumentStatus.UPLOADING.value),
                    name=item.get("name"),
                    error_msg=item.get("error_msg"),
                    enable_graph_enhancement=item.get("enable_graph_enhancement"),
                )
            )
        logger.info(
            f"[WEBLINK_STATUS] Weblink status (mirror DS KB) - Space ID: {req.space_id}, "
            f"KB ID: {req.kb_id}, Requested: {len(req.weblink_id_list)}, Found: {len(status_items)}, "
            f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
        )
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="get weblink status success",
            data=DocumentStatusListResponse(items=status_items).model_dump(by_alias=False),
        )

    items = []
    for weblink_id in req.weblink_id_list:
        get_result = knowledge_base_repository.weblink_get(
            KBWeblink(kb=kb_details, weblink_id=weblink_id)
        )
        if get_result.code == status.HTTP_200_OK and get_result.data:
            w = get_result.data
            display_name = w.get("name") or ""

            # 仅当用户点击刷新且名称仍为 URL 时，从 URL 解析标题
            if req.refresh_names:
                url = w.get("url", "")
                if url and _name_needs_refresh(display_name, url):
                    try:
                        documents = await asyncio.wait_for(
                            _parse_url(url, weblink_id),
                            timeout=10.0,
                        )
                        for d in documents:
                            if d.metadata and isinstance(d.metadata, dict):
                                t = d.metadata.get("title")
                                if t and isinstance(t, str) and t.strip():
                                    display_name = t.strip()
                                    knowledge_base_repository.weblink_update(
                                        KBWeblink(kb=kb_details, weblink_id=weblink_id),
                                        name=display_name,
                                    )
                                    break
                    except Exception as e:
                        logger.debug(f"[WEBLINK_STATUS] Failed to refresh name for {weblink_id}: {e}")
                    if not display_name:
                        display_name = url
            if not display_name:
                display_name = w.get("url", "")

            process_info = w.get("process_info") or {}
            error_msg = (
                process_info.get("error") or process_info.get("message")
                if isinstance(process_info, dict)
                else None
            )
            status_value = w.get("status", "")
            # 如果状态是 FAILED 但没有错误信息，提供默认错误信息
            if status_value == DocumentStatus.FAILED.value and not error_msg:
                error_msg = "Processing failed with unknown error"
            # 格式化错误信息供前端显示
            if error_msg:
                error_msg = _format_error_message_for_frontend(error_msg)
            # 从 indexing_strategy 中提取图增强标识
            enable_graph_enhancement = None
            if isinstance(process_info, dict):
                indexing_strategy = process_info.get("indexing_strategy")
                if isinstance(indexing_strategy, dict):
                    enable_graph_enhancement = indexing_strategy.get("enable_graph_enhancement", False)
            items.append(
                DocumentStatusResponse(
                    id=weblink_id,
                    status=status_value,
                    name=display_name,
                    error_msg=error_msg,
                    enable_graph_enhancement=enable_graph_enhancement,
                )
            )
        else:
            items.append(
                DocumentStatusResponse(
                    id=weblink_id,
                    status=DocumentStatus.FAILED.value,
                    error_msg=_format_error_message_for_frontend("Not found"),
                )
            )
    logger.info(
        f"[WEBLINK_STATUS] Weblink status batch retrieved - Space ID: {req.space_id}, "
        f"KB ID: {req.kb_id}, Requested: {len(req.weblink_id_list)}, "
        f"Found: {len(items)}, User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get weblink status success",
        data=DocumentStatusListResponse(items=items).model_dump(by_alias=False),
    )


@with_exception_handling
def weblink_update(req: WeblinkUpdateRequest, current_user: dict) -> ResponseModel:
    """更新链接名称"""
    _ = check_user_space(req.space_id, current_user)
    kb_details = KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE)
    update_result = knowledge_base_repository.weblink_update(
        KBWeblink(kb=kb_details, weblink_id=req.weblink_id),
        name=req.weblink_name,
    )
    if update_result.code != status.HTTP_200_OK:
        return ResponseModel(code=update_result.code, message=update_result.message)
    return ResponseModel(code=status.HTTP_200_OK, message="update weblink success")


@with_exception_handling
async def weblink_delete(req: WeblinkDeleteRequest, current_user: dict) -> ResponseModel:
    """批量删除链接。Studio 知识库走 Studio 表 + 索引删除；DS 镜像知识库转发 DS 文档删除。"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[WEBLINK_DELETE] Deleting weblinks - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Weblink IDs: {req.weblink_ids}"
    )

    _ = check_user_space(req.space_id, current_user)
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    kb_data_for_mirror = kb_result.data
    is_ds_kb = bool(
        kb_data_for_mirror.get("kb_id")
        and kb_data_for_mirror.get("kb_id") == kb_data_for_mirror.get("ds_kb_id")
    )
    if is_ds_kb:
        try:
            ds_client = DeepSearchAgentClient()
            ds_resp = await ds_client.delete_documents(
                space_id=req.space_id,
                kb_id=req.kb_id,
                document_ids=req.weblink_ids,
            )
            if not isinstance(ds_resp, dict):
                return ResponseModel(
                    code=status.HTTP_502_BAD_GATEWAY,
                    message="DeepSearch delete returned invalid response",
                )
            if ds_resp.get("code") not in (None, status.HTTP_200_OK):
                return ResponseModel(
                    code=ds_resp.get("code", status.HTTP_502_BAD_GATEWAY),
                    message=ds_resp.get("message", "DeepSearch delete failed"),
                )
            logger.info(
                f"[WEBLINK_DELETE] Delete (DeepSearch mirror) - KB ID: {req.kb_id}, "
                f"Doc IDs: {len(req.weblink_ids)}, User: {user_id}, "
                f"Duration: {time.time() - start_time:.3f}s"
            )
            return ResponseModel(code=status.HTTP_200_OK, message="delete weblinks success")
        except Exception as e:
            logger.warning(
                f"[WEBLINK_DELETE] DeepSearch delete failed (mirror) - "
                f"KB ID: {req.kb_id}, error={e}",
                exc_info=True,
            )
            return ResponseModel(
                code=status.HTTP_502_BAD_GATEWAY,
                message=f"DeepSearch delete failed: {str(e)}",
            )

    kb_details = KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE)
    success_count = 0
    failed_count = 0
    failed_weblink_ids = []
    index_manager = _create_index_manager()
    chunk_index = f"kb_{req.kb_id}_chunks"
    triple_index = f"kb_{req.kb_id}_triples"
    for weblink_id in req.weblink_ids:
        get_result = knowledge_base_repository.weblink_get(
            KBWeblink(kb=kb_details, weblink_id=weblink_id)
        )
        if get_result.code != status.HTTP_200_OK or not get_result.data:
            failed_count += 1
            failed_weblink_ids.append(weblink_id)
            continue
        w = get_result.data
        process_info = w.get("process_info") or {}
        indexing_strategy = (
            process_info.get("indexing_strategy", {}) if isinstance(process_info, dict) else {}
        )
        use_graph = (
            indexing_strategy.get("enable_graph_enhancement", False)
            if isinstance(indexing_strategy, dict)
            else False
        )
        try:
            await _delete_document_from_index(
                index_manager=index_manager,
                index_name=chunk_index,
                doc_id=weblink_id,
                kb_id=req.kb_id,
                index_type="chunks",
            )
            if use_graph:
                await _delete_document_from_index(
                    index_manager=index_manager,
                    index_name=triple_index,
                    doc_id=weblink_id,
                    kb_id=req.kb_id,
                    index_type="triples",
                )
        except Exception as e:
            logger.warning(f"[WEBLINK_DELETE] Index delete failed - Weblink ID: {weblink_id}, Error: {e}")
        knowledge_base_repository.weblink_delete_batch(
            space_id=req.space_id,
            kb_id=req.kb_id,
            weblink_ids=[weblink_id],
            index_manager_type=_CURR_INDEX_TYPE,
        )
        success_count += 1

    logger.info(
        f"[WEBLINK_DELETE] Weblink deletion completed - KB ID: {req.kb_id}, "
        f"Success: {success_count}, Failed: {failed_count}, "
        f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )
    if success_count > 0:
        return ResponseModel(code=status.HTTP_200_OK, message="delete weblinks success")
    return ResponseModel(
        code=status.HTTP_400_BAD_REQUEST,
        message=f"Failed to delete weblinks: {failed_weblink_ids}",
        data=None,
    )
