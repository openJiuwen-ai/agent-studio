import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from openjiuwen_studio.core.database import get_db
from openjiuwen_studio.core.manager.model_manager.managers.embedding_model_config_manager import \
    EmbeddingModelConfigManager
from openjiuwen_studio.core.manager.model_manager.managers.embedding_model_test_manager import \
    EmbeddingModelTester
from openjiuwen_studio.core.exceptions import (
    ModelConfigNotFoundError,
    ModelTestError,
    ValidationError
)
from openjiuwen_studio.routers.auth import get_current_user
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.embedding_model_config import (
    EmbeddingModelConfigCreate, EmbeddingModelConfigList,
    EmbeddingModelConfigRequest, EmbeddingModelConfigResponse,
    EmbeddingModelConfigUpdate, EmbeddingModelConfigUpdateRequest,
    EmbeddingModelTestRequest, EmbeddingProtocol)

logger = logging.getLogger(__name__)

embedding_models_router = APIRouter(prefix="/embedding-models", tags=["embedding-models"])


def get_embedding_model_config_manager(db: Session = Depends(get_db)) -> EmbeddingModelConfigManager:
    return EmbeddingModelConfigManager(db)


def get_embedding_model_tester(db: Session = Depends(get_db)) -> EmbeddingModelTester:
    return EmbeddingModelTester(db)


def embedding_model_to_response(manager: EmbeddingModelConfigManager, model) -> EmbeddingModelConfigResponse:
    """转换为响应格式"""
    return manager._model_to_response(model)


@embedding_models_router.get("/{space_id}", response_model=ResponseModel[EmbeddingModelConfigList])
async def get_embedding_model_configs(
    space_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    protocol: Optional[EmbeddingProtocol] = Query(None, description="Filter by protocol"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in model_name, model_id"),
    sort_by: Optional[str] = Query("updated_at", description="Sort by field"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """获取 Embedding 模型配置列表"""
    try:
        models, total = manager.get_paginated_configs(
            space_id=space_id,
            page=page,
            size=size,
            protocol=protocol,
            is_active=is_active,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 转换为响应格式
        model_responses = [manager._model_to_response(model) for model in models]
        
        result = EmbeddingModelConfigList(
            items=model_responses,
            total=total,
            page=page,
            size=size
        )
        
        return ResponseModel(
            code=200,
            message="Embedding model configurations retrieved successfully",
            data=result
        )
    except Exception as e:
        logger.error(f"Error retrieving embedding model configs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@embedding_models_router.get("/", response_model=ResponseModel[EmbeddingModelConfigResponse])
async def get_embedding_model_config(
    config_id: int = Query(..., description="配置ID"),
    space_id: str = Query(..., description="空间ID"),
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """获取单个 Embedding 模型配置"""
    try:
        model = manager.get_config_by_id(config_id, space_id)
        return ResponseModel(
            code=200,
            message="Embedding model configuration retrieved successfully",
            data=manager._model_to_response(model)
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embedding model configuration not found"
            ) from e
        logger.error(f"Error retrieving embedding model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@embedding_models_router.post("/", response_model=ResponseModel[EmbeddingModelConfigResponse])
async def create_embedding_model_config(
    model_config: EmbeddingModelConfigCreate,
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """创建 Embedding 模型配置"""
    try:
        db_model = manager.create_config(model_config)
        return ResponseModel(
            code=200,
            message="Embedding model configuration created successfully",
            data=manager._model_to_response(db_model)
        )
    except Exception as e:
        logger.error(f"Error creating embedding model config: {str(e)}")
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embedding model configuration with this name already exists"
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error") from e


@embedding_models_router.post("/update", response_model=ResponseModel[EmbeddingModelConfigResponse])
async def update_embedding_model_config(
    request: EmbeddingModelConfigUpdateRequest,
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """更新 Embedding 模型配置"""
    try:
        # 创建更新对象（排除 config_id 和 space_id）
        update_data = request.model_dump(exclude={'config_id', 'space_id'}, exclude_unset=True)
        model_config_update = EmbeddingModelConfigUpdate(**update_data)
        
        # 更新配置
        model = manager.update_config(request.config_id, request.space_id, model_config_update)
        
        return ResponseModel(
            code=200,
            message="Embedding model configuration updated successfully",
            data=manager._model_to_response(model)
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embedding model configuration not found"
            ) from e
        elif "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Embedding model configuration with this model_name already exists"
            ) from e
        logger.error(f"Error updating embedding model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@embedding_models_router.delete("/", response_model=ResponseModel[dict])
async def delete_embedding_model_config(
    model_request: EmbeddingModelConfigRequest,
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """删除 Embedding 模型配置"""
    try:
        success = manager.delete_config(model_request.config_id, model_request.space_id)
        return ResponseModel(
            code=200,
            message="Embedding model configuration deleted successfully",
            data={"deleted_id": model_request.config_id}
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embedding model configuration not found"
            ) from e
        elif "in use" in str(e).lower() or "being used" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e
        logger.error(f"Error deleting embedding model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@embedding_models_router.post("/{config_id}/test", response_model=ResponseModel[dict])
async def test_embedding_model_config(
    config_id: int,
    test_request: EmbeddingModelTestRequest,
    tester: EmbeddingModelTester = Depends(get_embedding_model_tester),
    current_user: dict = Depends(get_current_user)
):
    """测试 Embedding 模型配置 - 直接返回 API 原始响应"""
    try:
        api_response = await tester.test_embedding_model(
            model_id=config_id,
            test_request=test_request,
            user_id=current_user["data"]["user_id_str"]
        )
        
        # 检查是否有错误
        if "error" in api_response:
            raise HTTPException(
                status_code=500,
                detail=api_response.get("error", "Embedding API call failed")
            )
        
        # 直接返回 API 的原始响应
        return ResponseModel(
            code=200,
            message="Embedding model test completed",
            data=api_response
        )
        
    except ModelConfigNotFoundError as e:
        # 模型配置不存在，透传错误信息
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ModelTestError as e:
        # 模型测试失败，透传错误信息（包含详细的配置问题，如 API key、model name、URL 等）
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValidationError as e:
        # 数据验证失败，透传错误信息
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e)) from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing embedding model configuration: {str(e)}", exc_info=True)
        # 透传异常信息，而不是通用的 "Internal server error"
        raise HTTPException(status_code=500, detail=str(e)) from e


@embedding_models_router.post("/toggle", response_model=ResponseModel[EmbeddingModelConfigResponse])
async def toggle_embedding_model_status(
    request: EmbeddingModelConfigRequest,
    manager: EmbeddingModelConfigManager = Depends(get_embedding_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """切换 Embedding 模型配置的激活状态"""
    try:
        updated_model = manager.toggle_status(request.config_id, request.space_id)
        return ResponseModel(
            code=200,
            message=f"Embedding model {'activated' if updated_model.is_active else 'deactivated'} successfully",
            data=manager._model_to_response(updated_model)
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embedding model configuration not found"
            ) from e
        logger.error(f"Error toggling embedding model status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e

