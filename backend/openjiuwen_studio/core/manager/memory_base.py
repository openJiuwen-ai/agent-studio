import asyncio
from typing import Callable, Any, Awaitable, Optional, Union
import uuid
import time
from functools import wraps
from pydantic import ValidationError
from fastapi import status

from openjiuwen_studio.core.manager.model_manager.managers import ModelConfigManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.utils.exception import log_exception
from openjiuwen_studio.schemas.memory_base import (
    MemoryBaseCreate, MemoryBaseResponseCreate, MemoryBaseGet,
    MemoryBaseUpdateRequest, MemoryBaseListRequest, MemoryBaseListResponse,
    MemoryBaseListItem, MemoryBaseSearchResponse, MemoryBaseSearchRequest
)
from openjiuwen_studio.core.manager.login_manager.space import check_user_space
from openjiuwen_studio.core.manager.repositories.memory_base_repository import memory_base_repository
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.core.database import SessionLocal, milliseconds
from openjiuwen.core.common.logging import logger
from openjiuwen.core.memory.config.config import MemoryScopeConfig
from openjiuwen.core.retrieval.common.config import EmbeddingConfig
from openjiuwen.core.foundation.llm.schema.config import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.memory.long_term_memory import LongTermMemory


def _get_llm_config_from_db(llm_model_id: int, space_id: str) -> tuple[ModelClientConfig, ModelRequestConfig]:
    """
    从数据库读取 LLM 模型配置，解密 API key。

    Args:
        llm_model_id: LLM 模型配置ID（必填）
        space_id: 空间ID，用于从数据库查询模型配置（必填）

    Returns:
        tuple[ModelClientConfig, ModelRequestConfig]

    Raises:
        ValueError: 如果数据库查询失败或配置无效
    """
    logger.info(f"[LLM_CLIENT] Creating LLM client from database - Model ID: {llm_model_id}, Space ID: {space_id}")

    # 从数据库获取模型配置
    with get_db_jw() as db:
        manager = ModelConfigManager(db)
        model_config = manager.get_config_by_id(int(llm_model_id), space_id)

        # 解密 API key
        security_utils = SecurityUtils()
        api_key = None
        if model_config.api_key:
            try:
                api_key = security_utils.decrypt_api_key(model_config.api_key)
            except Exception as e:
                logger.warning(f"[LLM_CLIENT] Failed to decrypt API key for model {llm_model_id}: {str(e)}")
                raise ValueError(f"Failed to decrypt API key for model {llm_model_id}: {str(e)}") from e
        if model_config.provider.lower() == 'openai':
            model_provider = 'OpenAI'
        elif model_config.provider == 'siliconflow':
            model_provider = 'SiliconFlow'
        # 使用数据库配置创建 ModelClientConfig 和 ModelRequestConfig
        model_client_config = ModelClientConfig(
            client_id=str(model_config.id),
            client_provider=model_provider,
            api_key=api_key,
            api_base=model_config.base_url,
            timeout=float(model_config.timeout),
            verify_ssl=False,
        )

        model_request_config = ModelRequestConfig(
            model=model_config.model_type,
            temperature=model_config.parameters.get("temperature", 0.95),
            top_p=model_config.parameters.get("top_p", 0.1),
            max_tokens=model_config.parameters.get("max_tokens", None),
        )
        logger.debug(f"[LLM_CLIENT] Get LLM model config from database successfully")
        return model_client_config, model_request_config


def _get_embedding_config_from_db(embedding_model_config_id: int) -> EmbeddingConfig:
    """
    从数据库读取向量模型配置，解密 API key。
    Args:
        embedding_model_config_id: 向量模型配置ID（必填）

    Returns:
        EmbeddingConfig

    Raises:
        ValueError: 如果数据库查询失败或配置无效
    """
    # 从数据库读取知识库的 embedding 模型配置
    db = SessionLocal()
    try:
        # 1. 查询 embedding 模型配置
        embed_repo = EmbeddingModelConfigRepository(db)
        embed_model_config = embed_repo.get_by_id(int(embedding_model_config_id))

        if not embed_model_config:
            raise ValueError(f"Embedding model config not found (ID: {embedding_model_config_id})")

        if not embed_model_config.is_active:
            raise ValueError(f"Embedding model config is not active (ID: {embedding_model_config_id})")

        # 2. 解密 API key
        security_utils = SecurityUtils()
        api_key = None
        if embed_model_config.api_key:
            try:
                api_key = security_utils.decrypt_api_key(embed_model_config.api_key)
            except Exception as e:
                raise ValueError(f"Failed to decrypt API key for model {embed_model_config.id}: {str(e)}") from e

        # 3. 使用数据库配置创建 EmbeddingConfig
        # 数据库字段：api_base, model_id, api_key, max_batch_size
        # APIEmbedding 需要：config (EmbeddingConfig), timeout, max_retries, max_batch_size
        embed_config = EmbeddingConfig(
            model_name=embed_model_config.model_id,  # 使用 model_id 作为模型名称
            api_key=api_key,
            base_url=embed_model_config.api_base,
        )
        logger.debug(f"[EMBED_MODEL] Get embed model config from database successfully")
        return embed_config

    finally:
        db.close()


def _parse_to_memory_scope_config(mdb_id: str) -> MemoryScopeConfig:
    """解析记忆库作用域配置字符串为MemoryScopeConfig对象"""
    logger.info(f"[MEMORY_SCOPE] Parsing memory scope config for scope_id: {mdb_id}")

    # 从数据库获取记忆库信息
    db = SessionLocal()
    try:
        # 1. 获取记忆库信息
        # get_result = memory_base_repository.memory_base_get(
        #     MemoryBaseGet(space_id="", mdb_id=mdb_id)
        # )
        get_result = memory_base_repository.memory_base_get_by_id(mdb_id)

        if get_result.code != status.HTTP_200_OK or not get_result.data:
            raise ValueError(f"Memory base not found (Scope ID: {mdb_id})")

        mdb_data = get_result.data
        embedding_model_config_id = mdb_data.get("embedding_model_config_id")
        llm_model_config_id = mdb_data.get("llm_model_config_id")
        space_id = mdb_data.get("space_id")

        if not embedding_model_config_id:
            raise ValueError(f"Memory base {mdb_id} has no embedding_model_config_id")

        # 2. 获取嵌入模型配置
        embedding_config = _get_embedding_config_from_db(embedding_model_config_id)

        # 3. 获取LLM模型配置
        llm_client_config, llm_request_config = _get_llm_config_from_db(llm_model_config_id, space_id)

        # 4. 创建并返回MemoryScopeConfig对象
        memory_scope_config = MemoryScopeConfig(
            embedding_cfg=embedding_config,
            model_client_cfg=llm_client_config,
            model_cfg=llm_request_config
        )

        logger.info(f"[MEMORY_SCOPE] Memory scope config parsed successfully for scope_id: {mdb_id}")
        return memory_scope_config
    finally:
        db.close()


def with_exception_handling(func):
    """同步/异步函数通用异常处理装饰器"""
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValidationError as e:
                log_exception(e)
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=type(e).__name__
                )
            except Exception as e:
                log_exception(e)
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=type(e).__name__
                )

        return async_wrapper

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=type(e).__name__
            )
        except Exception as e:
            log_exception(e)
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=type(e).__name__
            )

    return sync_wrapper


@with_exception_handling
async def memory_base_create(
        req: MemoryBaseCreate,
        current_user: dict
) -> ResponseModel:
    """创建新的记忆库"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)
    user_id = current_user.get('user_id', 'unknown')

    logger.info(
        f"MB_CREATE Creating Memory base - User: {user_id}, Name: {req.name}, "
        f"Embedding Model Config ID: {req.embedding_model_config_id}"
        f"LLM Model Config ID: {req.llm_model_config_id}")

    # 2. 检查记忆库名称是否已存在（区分大小写）
    name_exists_result = memory_base_repository.memory_base_check_name_exists(
        space_id=req.space_id,
        name=req.name
    )
    if name_exists_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=name_exists_result.code,
            message=name_exists_result.message,
        )
    if name_exists_result.data:
        return ResponseModel(
            code=status.HTTP_400_BAD_REQUEST,
            message=f"记忆库名称 '{req.name}' 已存在",
        )

    # 3. 验证 embedding_model_config_id 是否存在且属于该 space_id
    db = SessionLocal()
    try:
        embedding_repo = EmbeddingModelConfigRepository(db)
        embedding_model = embedding_repo.get_by_id(req.embedding_model_config_id)
        if not embedding_model:
            return ResponseModel(
                code=status.HTTP_404_NOT_FOUND,
                message=f"Embedding model config not found: {req.embedding_model_config_id}",
            )
        if embedding_model.space_id != req.space_id:
            return ResponseModel(
                code=status.HTTP_403_FORBIDDEN,
                message="Embedding model config does not belong to this space",
            )
        if not embedding_model.is_active:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="Embedding model config is not active",
            )
    finally:
        db.close()

    # 4. 生成记忆库ID（使用去掉连字符的 UUID，保证仅字母数字）
    mdb_id = uuid.uuid4().hex

    # 5. 准备记忆库数据
    mdb_data = {
        "space_id": req.space_id,
        "mdb_id": mdb_id,
        "name": req.name,
        "description": req.description,
        "embedding_model_config_id": req.embedding_model_config_id,
        "llm_model_config_id": req.llm_model_config_id,
        "create_time": milliseconds(),
        "update_time": milliseconds(),
    }

    # 6. 保存到数据库
    create_result = memory_base_repository.memory_base_create(mdb_data)

    if create_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=create_result.code,
            message=create_result.message,
        )

    # 7. 准备响应数据
    response_data = MemoryBaseResponseCreate(mdb_id=mdb_id)

    # 8. 更新记忆库作用域配置到LongTermMemory中
    memory_scope_config = _parse_to_memory_scope_config(mdb_id=mdb_id)
    await LongTermMemory().set_scope_config(scope_id=mdb_id, memory_scope_config=memory_scope_config)

    # 9. 返回创建结果
    return ResponseModel(
        code=status.HTTP_200_OK,
        message="create memory base success",
        data=response_data.model_dump(by_alias=True)
    )


@with_exception_handling
def memory_base_get(
        req: MemoryBaseGet,
        current_user: dict
) -> ResponseModel:
    """获取记忆库信息"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 从数据库获取记忆库信息
    get_result = memory_base_repository.memory_base_get(req)

    if get_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=get_result.code,
            message=get_result.message,
        )

    if not get_result.data:
        return ResponseModel(
            code=status.HTTP_404_NOT_FOUND,
            message="Memory base not found",
        )

    # 3. 转换为响应模型
    mdb_data = get_result.data
    create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb_data["create_time"] / 1000))
    update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb_data["update_time"] / 1000))

    memory_base_info = MemoryBaseListItem(
        mdb_id=mdb_data["mdb_id"],
        space_id=mdb_data["space_id"],
        name=mdb_data["name"],
        description=mdb_data["description"],
        embedding_model_config_id=mdb_data["embedding_model_config_id"],
        llm_model_config_id=mdb_data["llm_model_config_id"],
        created_at=create_time,
        updated_at=update_time,
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="get memory base success",
        data=memory_base_info.model_dump()
    )


@with_exception_handling
async def memory_base_delete(
        req: MemoryBaseGet,
        current_user: dict
) -> ResponseModel:
    """删除记忆库"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 从数据库删除记忆库
    delete_result = memory_base_repository.memory_base_delete(req)

    if delete_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=delete_result.code,
            message=delete_result.message,
        )
    # 3. 删除LongTermMemory中记忆库作用域配置和对应的记忆库
    await LongTermMemory().delete_scope_config(req.mdb_id)
    res = await LongTermMemory().scope_user_mapping_manager.get_by_scope_id(req.mdb_id)
    if res is not None:
        await LongTermMemory().delete_mem_by_scope(req.mdb_id)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="delete memory base success",
    )


@with_exception_handling
async def memory_base_update(
        req: MemoryBaseUpdateRequest,
        current_user: dict
) -> ResponseModel:
    """更新记忆库信息"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)
    user_id = current_user.get('user_id', 'unknown')

    # 2. 检测记忆库是否存在
    mb_get = MemoryBaseGet(space_id=req.space_id, mdb_id=req.mdb_id)
    get_result = memory_base_repository.memory_base_get(mb_get)
    if get_result.code == status.HTTP_404_NOT_FOUND or not get_result.data:
        logger.warning(f"[MB_UPDATE] Memory base not found - ID: {req.mdb_id}, User: {user_id}")
        return ResponseModel(code=status.HTTP_404_NOT_FOUND, message="Memory base not found")

    # 3. 检查名称是否已存在（如果更新了名称）
    if req.name:
        name_exists_result = memory_base_repository.memory_base_check_name_exists(
            space_id=req.space_id,
            name=req.name,
            exclude_mdb_id=req.mdb_id
        )
        if name_exists_result.code != status.HTTP_200_OK:
            return ResponseModel(
                code=name_exists_result.code,
                message=name_exists_result.message,
            )
        if name_exists_result.data:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"记忆库名称 '{req.name}' 已存在",
            )
    # 4. 准备更新数据
    update_data = {"update_time": milliseconds()}

    if req.name:
        update_data["name"] = req.name
    if req.description:
        update_data["description"] = req.description
    if req.llm_model_config_id is not None:
        update_data["llm_model_config_id"] = req.llm_model_config_id

    # 5. 更新数据库
    update_result = memory_base_repository.memory_base_update(update_data, mb_get)

    if update_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=update_result.code,
            message=update_result.message,
        )

    # 6、更新记忆库作用域配置到LongTermMemory中
    memory_scope_config = _parse_to_memory_scope_config(mdb_id=req.mdb_id)
    await LongTermMemory().set_scope_config(scope_id=req.mdb_id, memory_scope_config=memory_scope_config)

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="update memory base success",
    )


@with_exception_handling
def memory_base_list(
        req: MemoryBaseListRequest,
        current_user: dict
) -> ResponseModel:
    """获取记忆库列表"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 从数据库获取记忆库列表
    list_result = memory_base_repository.memory_base_list(
        space_id=req.space_id,
        page=req.page,
        size=req.page_size
    )

    if list_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=list_result.code,
            message=list_result.message,
        )

    # 3. 转换为响应模型
    memory_bases = list_result.data.get("items", [])
    total = list_result.data.get("total", 0)

    items = []
    for mdb in memory_bases:
        # 转换时间格式
        create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb["create_time"] / 1000))
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb["update_time"] / 1000))

        item = MemoryBaseListItem(
            mdb_id=mdb["mdb_id"],
            space_id=mdb["space_id"],
            name=mdb["name"],
            description=mdb["description"],
            llm_model_config_id=mdb["llm_model_config_id"],
            embedding_model_config_id=mdb["embedding_model_config_id"],
            created_at=create_time,
            updated_at=update_time
        )
        items.append(item)

    # 4. 准备响应数据
    response_data = MemoryBaseListResponse(
        items=items,
        total=total,
        page=req.page,
        size=req.page_size
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="list memory base success",
        data=response_data.model_dump()
    )


@with_exception_handling
def memory_base_search(
        req: MemoryBaseSearchRequest,
        current_user: dict
) -> ResponseModel:
    """搜索记忆库"""
    # 1. 验证用户空间权限
    _ = check_user_space(req.space_id, current_user)

    # 2. 从数据库搜索记忆库
    search_result = memory_base_repository.memory_base_search(
        space_id=req.space_id,
        query=req.query,
        page=req.page,
        page_size=req.page_size
    )

    if search_result.code != status.HTTP_200_OK:
        return ResponseModel(
            code=search_result.code,
            message=search_result.message,
        )

    # 3. 转换为响应模型
    memory_bases = search_result.data.get("memory_bases", [])
    total = search_result.data.get("total", 0)
    page = search_result.data.get("page", req.page)
    page_size = search_result.data.get("page_size", req.page_size)
    total_pages = search_result.data.get("total_pages", 1)

    items = []
    for mdb in memory_bases:
        # 转换时间格式
        create_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb["create_time"] / 1000))
        update_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mdb["update_time"] / 1000))

        item = MemoryBaseListItem(
            mdb_id=mdb["mdb_id"],
            space_id=mdb["space_id"],
            name=mdb["name"],
            description=mdb["description"],
            embedding_model_config_id=mdb["embedding_model_config_id"],
            llm_model_config_id=mdb["llm_model_config_id"],
            created_at=create_time,
            updated_at=update_time,
        )
        items.append(item)

    # 4. 准备响应数据
    response_data = MemoryBaseSearchResponse(
        memory_bases=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    return ResponseModel(
        code=status.HTTP_200_OK,
        message="search memory base success",
        data=response_data.model_dump()
    )
