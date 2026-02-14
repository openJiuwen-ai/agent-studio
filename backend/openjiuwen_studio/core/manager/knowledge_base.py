#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
import re
import uuid
import time
import inspect
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Union, Tuple
from dataclasses import asdict
from fastapi import status, UploadFile
from openjiuwen.core.common.logging import logger

from openjiuwen.core.retrieval.indexing.processor.parser.auto_file_parser import AutoFileParser
from openjiuwen.core.retrieval.indexing.processor.chunker.chunking import TextChunker
from openjiuwen.core.retrieval.indexing.processor.extractor.triple_extractor import TripleExtractor
from openjiuwen.core.retrieval.indexing.indexer.milvus_indexer import MilvusIndexer
from openjiuwen.core.retrieval.vector_store.milvus_store import MilvusVectorStore
from openjiuwen.core.retrieval.indexing.indexer.chroma_indexer import ChromaIndexer
from openjiuwen.core.retrieval.vector_store.chroma_store import ChromaVectorStore
from openjiuwen.core.retrieval.simple_knowledge_base import SimpleKnowledgeBase
from openjiuwen.core.retrieval.graph_knowledge_base import GraphKnowledgeBase
from openjiuwen.core.retrieval.common.config import (
    KnowledgeBaseConfig,
    EmbeddingConfig,
    VectorStoreConfig,
)
from openjiuwen.core.retrieval.common.document import Document
from openjiuwen.core.retrieval.embedding.openai_embedding import OpenAIEmbedding

from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import (
    knowledge_base_repository,
)
from openjiuwen_studio.core.manager.repositories.agent_repository import agent_repository
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.database import SessionLocal
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
    DocumentGetRequest,
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
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.models.knowledge_base_document import DocumentStatus
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.ops.modules.llm.llm_manager import get_llm_client_by_protocol
from openjiuwen_studio.core.manager.repositories.knowledge_base_repository import (
    KBDetails,
    KBDocument,
)

_CURR_INDEX_TYPE = os.getenv("INDEX_MANAGER_TYPE", "milvus")

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
    3. 在 "reason" 之前截断（如果存在）
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

    # 4. 在 "reason" 之前截断（如果存在）
    # 匹配 ", reason:" 或 ",reason:" 或 " reason:" 等变体
    reason_pattern = r",\s*reason\s*:"
    match = re.search(reason_pattern, result, re.IGNORECASE)
    if match:
        result = result[: match.start()].strip()

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


# ==================== 异常处理装饰器 ====================


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
                    message=f"Internal server error: {str(e)}",
                )

        return async_wrapper

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"[KNOWLEDGE_BASE] Error in {func.__name__}: {str(e)}", exc_info=True)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Internal server error: {str(e)}",
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

    # 4. 删除知识库
    delete_result = knowledge_base_repository.knowledge_base_delete(req)

    if delete_result.code != status.HTTP_200_OK:
        logger.error(f"[KB_DELETE] Delete failed - ID: {req.kb_id}, Error: {delete_result.message}")
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )

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

    # 6. 删除 Milvus | Chroma 向量索引（循环删除每个文档的索引）
    try:
        index_result = await _delete_kb_indices(req.kb_id, req.space_id)
        if index_result["success_count"] > 0:
            logger.info(
                f"[KB_DELETE] Indices successfully deleted - KB ID: {req.kb_id}, "
                f"Success: {index_result['success_count']}, Failed: {index_result['failed_count']}"
            )
        if index_result["errors"]:
            logger.warning(
                f"[KB_DELETE] Some indices failed to delete - KB ID: {req.kb_id}, "
                f"Errors: {index_result['errors']}"
            )
    except Exception as e:
        # Milvus | Chroma 删除失败不影响整体删除结果
        logger.error(
            f"[KB_DELETE] Failed to delete indices - KB ID: {req.kb_id}, Error: {str(e)}",
            exc_info=True,
        )

    # 7. 返回删除结果
    return ResponseModel(
        code=status.HTTP_200_OK, message="delete knowledge base success", data=None
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
    """检查 Milvus 连接性

    Returns:
        tuple[bool, str]: (是否连接成功, 错误信息)
    """
    try:
        from pymilvus import connections, utility

        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = os.getenv("MILVUS_PORT", "19530")
        milvus_token = os.getenv("MILVUS_TOKEN", None)

        # 尝试连接 Milvus
        alias = "kb_connection_test"
        try:
            # 如果连接已存在，先断开
            if connections.has_connection(alias):
                connections.disconnect(alias)
        except Exception as e:
            logger.warning(f"[MILVUS] Failed to disconnect connection: {alias}, Error: {str(e)}")

        # 建立新连接
        connections.connect(
            alias=alias, host=milvus_host, port=int(milvus_port), token=milvus_token
        )

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
    return VectorStoreConfig(collection_name="default", database_name="")


def _create_milvus_index_manager() -> MilvusIndexer:
    """Create Milvus index manager (used by _check_milvus_connection and _create_index_manager)."""
    milvus_host = os.getenv("MILVUS_HOST", "localhost")
    milvus_port = os.getenv("MILVUS_PORT", "19530")
    milvus_token = os.getenv("MILVUS_TOKEN", None)
    milvus_uri = f"http://{milvus_host}:{milvus_port}"
    return MilvusIndexer(
        config=_default_index_config(),
        milvus_uri=milvus_uri,
        milvus_token=milvus_token,
    )


def _create_index_manager() -> Union[MilvusIndexer, ChromaIndexer]:
    """
    Creates either a Milvus or Chroma index manager
    based on the `INDEX_MANAGER_TYPE` variable set in `.env`.
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
        return _create_milvus_index_manager()
    else:
        raise ValueError(f"Un-supported {index_manager_type=} for env variable INDEX_MANAGER_TYPE")


async def _delete_kb_indices(kb_id: str, space_id: str) -> dict:
    """删除知识库下所有文档的 chunks 和 triples 索引

    获取知识库下的所有文档，然后循环删除每个文档的 chunks 和 triples 索引数据
    """
    result = {"success_count": 0, "failed_count": 0, "errors": []}

    try:
        # 获取知识库下的所有文档（分页获取，每页最多100条）
        all_documents = []
        page = 1
        page_size = 100

        while True:
            doc_list_result = knowledge_base_repository.document_list(
                KBDocument(
                    KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE),
                    doc_id=None,
                    doc_status=None,
                    process_info=None,
                    index_name=None,
                    chunk_count=None,
                )
            )

            if doc_list_result.code != status.HTTP_200_OK or not doc_list_result.data:
                break

            items = doc_list_result.data.get("items", [])
            if not items:
                break

            all_documents.extend(items)

            # 如果返回的数量小于 page_size，说明已经是最后一页
            if len(items) < page_size:
                break

            page += 1

        if not all_documents:
            logger.debug(f"[KB_DELETE] No documents to delete indices for KB {kb_id}")
            return result

        documents = all_documents
        logger.info(f"[KB_DELETE] Deleting indices for {len(documents)} documents in KB {kb_id}")

        # 创建索引管理器
        index_manager = _create_index_manager()
        chunk_index = f"kb_{kb_id}_chunks"
        triple_index = f"kb_{kb_id}_triples"

        # 循环删除每个文档的索引
        for doc in documents:
            doc_id = doc.get("doc_id") or doc.get("id")
            if not doc_id:
                continue

            try:
                # 删除 chunks 索引
                await _delete_document_from_index(
                    index_manager=index_manager,
                    index_name=chunk_index,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    index_type="chunks",
                )

                # 删除 triples 索引（如果有图增强）
                await _delete_document_from_index(
                    index_manager=index_manager,
                    index_name=triple_index,
                    doc_id=doc_id,
                    kb_id=kb_id,
                    index_type="triples",
                )

                result["success_count"] += 1
            except Exception as e:
                result["failed_count"] += 1
                result["errors"].append(f"Doc {doc_id}: {str(e)}")
                logger.warning(f"[KB_DELETE] Failed to delete index for doc {doc_id}: {e}")

        logger.info(
            f"[KB_DELETE] Index deletion completed - KB: {kb_id}, "
            f"Success: {result['success_count']}, Failed: {result['failed_count']}"
        )

    except Exception as e:
        error_msg = f"Failed to delete KB indices: {str(e)}"
        result["errors"].append(error_msg)
        logger.error(f"[KB_DELETE] {error_msg}", exc_info=True)

    return result


def _create_vector_store(collection_name: str) -> Union[MilvusVectorStore, ChromaVectorStore]:
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
            collection_name=collection_name,
        )
        return ChromaVectorStore(config=vector_store_config, chroma_path=str(data_dir))

    elif index_manager_type == "milvus":
        milvus_host = os.getenv("MILVUS_HOST", "localhost")
        milvus_port = os.getenv("MILVUS_PORT", "19530")
        milvus_token = os.getenv("MILVUS_TOKEN", None)

        # 组合 Milvus URI (格式: http://host:port 或 tcp://host:port)
        # 默认使用 http:// 协议
        milvus_uri = f"http://{milvus_host}:{milvus_port}"

        vector_store_config = VectorStoreConfig(
            collection_name=collection_name,
        )
        return MilvusVectorStore(
            config=vector_store_config, milvus_uri=milvus_uri, milvus_token=milvus_token
        )

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
) -> dict:

    # 1. 更新状态为INDEXING
    update_indexing_result = knowledge_base_repository.document_update_status(
        KBDocument(
            kb=KBDetails(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE),
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
    index_manager = _create_index_manager()

    # 5.3 创建向量存储
    vector_store = _create_vector_store(
        collection_name=chunk_index,
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
    try:
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
    finally:
        # 清理资源
        try:
            await knowledge_base.close()
        except Exception as e:
            logger.warning(f"[INDEX] Failed to close knowledge base: {str(e)}")


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
):
    """在后台异步处理单个文档"""
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

    # 2. 验证知识库是否存在
    kb_get = KnowledgeBaseGet(space_id=space_id, kb_id=kb_id, index_manager_type=_CURR_INDEX_TYPE)
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(f"[DOC_UPLOAD] Knowledge base not found - KB ID: {kb_id}, User: {user_id}")
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

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

            logger.debug(f"[DOC_UPLOAD] File saved - Path: {file_path}, Size: {file_size} bytes")

            # 4.4 创建文档记录
            current_time = milliseconds()
            doc_data = {
                "space_id": space_id,
                "kb_id": kb_id,
                "doc_id": doc_id,
                "name": filename,
                "file_path": str(file_path),
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

    # 3. 转换数据格式，并检查是否有图增强文档
    items = []
    for kb_data in list_result.data.get("items", []):
        kb_id = kb_data.get("kb_id", "")
        # 检查是否有图增强文档
        has_graph_enhancement = knowledge_base_repository.has_graph_enhancement_documents(
            space_id=req.space_id, kb_id=kb_id
        )

        items.append(
            KnowledgeBaseListItem(
                name=kb_data.get("name", ""),
                desc=kb_data.get("description"),
                id=kb_id,
                type="text",
                embedding_model_config_id=kb_data.get("embedding_model_config_id"),
                created_at=_timestamp_to_date_str(kb_data.get("create_time")),
                updated_at=_timestamp_to_date_str(kb_data.get("update_time")),
                has_graph_enhancement=has_graph_enhancement,
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
def document_list(req: DocumentListRequest, current_user: dict) -> ResponseModel:
    """获取知识库文档列表（支持分页）"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_LIST] Getting document list - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Page: {req.page}, Size: {req.size}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 验证知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(f"[DOC_LIST] Knowledge base not found - KB ID: {req.kb_id}, User: {user_id}")
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

    # 3. 从数据库获取文档列表
    list_result = knowledge_base_repository.document_list(
        KBDocument(
            KBDetails(space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE),
        ),
        page=req.page,
        size=req.size,
    )

    if list_result.code != status.HTTP_200_OK:
        logger.error(
            f"[DOC_LIST] Database query failed - Space ID: {req.space_id}, "
            f"KB ID: {req.kb_id}, Error: {list_result.message}"
        )
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
            data={"items": [], "total": 0, "page": req.page, "size": req.size},
        )

    # 4. 转换数据格式
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

    # 5. 构建响应数据
    total = list_result.data.get("total", 0)
    response_data = DocumentListResponse(items=items, total=total, page=req.page, size=req.size)

    logger.info(
        f"[DOC_LIST] Document list retrieved - Space ID: {req.space_id}, "
        f"KB ID: {req.kb_id}, Count: {len(items)}/{total}, "
        f"User: {user_id}, Duration: {time.time() - start_time:.3f}s"
    )

    # 6. 返回列表结果
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

    # 2. 验证知识库是否存在
    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(
            f"[DOC_DELETE] Knowledge base not found - KB ID: {req.kb_id}, User: {user_id}"
        )
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

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
                index_manager = _create_index_manager()

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
def document_get_status_batch(req: DocumentStatusRequest, current_user: dict) -> ResponseModel:
    """批量查询文档状态"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")
    logger.info(
        f"[DOC_STATUS] Getting document status batch - User: {user_id}, "
        f"Space ID: {req.space_id}, KB ID: {req.kb_id}, Doc IDs: {len(req.doc_id_list)}"
    )

    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 批量查询文档状态
    status_items = []
    for doc_id in req.doc_id_list:
        doc_result = knowledge_base_repository.document_get(
            KBDocument(
                KBDetails(
                    space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
                ),
                doc_id=doc_id,
            )
        )

        if doc_result.code == status.HTTP_200_OK and doc_result.data:
            doc_data = doc_result.data
            status_value = doc_data.get("status", DocumentStatus.UPLOADING.value)
            doc_name = doc_data.get("name")

            # 从 process_info 中提取错误信息和图增强标识
            error_msg = None
            enable_graph_enhancement = None
            process_info = doc_data.get("process_info")
            if isinstance(process_info, dict):
                # 优先查找 "error" 字段（文档处理失败时设置），如果没有则查找 "message" 字段（导入时设置）
                error_msg = process_info.get("error") or process_info.get("message")
                # 从 indexing_strategy 中提取 enable_graph_enhancement
                indexing_strategy = process_info.get("indexing_strategy")
                if isinstance(indexing_strategy, dict):
                    enable_graph_enhancement = indexing_strategy.get(
                        "enable_graph_enhancement", False
                    )

            # 如果状态是 FAILED 但没有错误信息，提供默认错误信息
            if status_value == DocumentStatus.FAILED.value and not error_msg:
                error_msg = "Processing failed with unknown error"

            # 格式化错误信息供前端显示
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
        else:
            # 文档不存在，仍然返回但状态为空或标记为不存在
            logger.warning(
                f"[DOC_STATUS] Document not found - Space ID: {req.space_id}, "
                f"KB ID: {req.kb_id}, Doc ID: {doc_id}, User: {user_id}"
            )
            # 可以选择跳过不存在的文档，或者返回一个标记状态
            # 这里选择跳过，只返回存在的文档

    # 3. 构建响应数据
    response_data = DocumentStatusListResponse(items=status_items)

    logger.info(
        f"[DOC_STATUS] Document status batch retrieved - Space ID: {req.space_id}, "
        f"KB ID: {req.kb_id}, Requested: {len(req.doc_id_list)}, "
        f"Found: {len(status_items)}, User: {user_id}, "
        f"Duration: {time.time() - start_time:.3f}s"
    )

    # 4. 返回查询结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get document status success",
        data=response_data.model_dump(by_alias=False),
    )


@with_exception_handling
async def document_process(req: DocumentProcessRequest, current_user: dict) -> ResponseModel:
    """启动文档处理流程，使用 agentcore 的解析/分段/索引能力"""
    start_time = time.time()
    user_id = current_user.get("user_id", "unknown")

    logger.info(
        f"[DOC_PROCESS] Starting document processing - User: {user_id}, "
        f"KB ID: {req.kb_id}, Files: {len(req.doc_id_list)}"
    )

    _ = check_user_space(req.space_id, current_user)

    kb_get = KnowledgeBaseGet(
        space_id=req.space_id, kb_id=req.kb_id, index_manager_type=_CURR_INDEX_TYPE
    )
    kb_result = knowledge_base_repository.knowledge_base_get(kb_get)
    if kb_result.code != status.HTTP_200_OK or not kb_result.data:
        logger.warning(
            f"[DOC_PROCESS] Knowledge base not found - KB ID: {req.kb_id}, User: {user_id}"
        )
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Knowledge base not found")

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
            # 收集有效文档信息
            valid_documents.append({"doc_id": doc_id, "file_path": file_path, "name": doc_name})
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
    # 3. 查询该任务ID下的所有文档
    list_result = knowledge_base_repository.document_list(
        kbdoc=KBDocument(kb=kb_details),
        page=1,
        size=1000,
    )  # 假设一个任务不会超过1000个文档

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
            doc_id = doc_data.get("doc_id", "")
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
