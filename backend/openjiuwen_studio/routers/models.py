from typing import List, Optional

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from openjiuwen_studio.core.database import get_db
from openjiuwen_studio.models.model_config import ModelConfig
from openjiuwen_studio.schemas.model_config import (
    ModelConfigCreate, ModelConfigUpdate, ModelConfigResponse, 
    ModelConfigList, ModelTestRequest, ModelTestResponse,
    ModelUsageStats, ModelProvider, ModelConfigRequest
)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.model_manager.managers import (
    ModelConfigManager, ModelTester
)
from openjiuwen_studio.routers.auth import get_current_user
from openjiuwen_studio.core.manager.repositories import AgentRepository, PromptRelationRepository, \
        UserRepository, WorkflowRepository

models_router = APIRouter(tags=["models"])


def get_model_config_manager(db: Session = Depends(get_db)) -> ModelConfigManager:
    return ModelConfigManager(db)


def get_model_tester(db: Session = Depends(get_db)) -> ModelTester:
    return ModelTester(db)


def get_security_utils() -> SecurityUtils:
    return SecurityUtils()


def create_usage_stats_from_model(model: ModelConfig) -> ModelUsageStats:
    """Create usage stats object from model data"""
    return ModelUsageStats(
        total_requests=model.total_requests,
        total_tokens=model.total_tokens,
        total_cost=model.total_cost,
        success_rate=model.success_rate,
        avg_response_time=model.avg_response_time,
        last_used=model.last_used,
        daily_requests=model.daily_requests,
        daily_tokens=model.daily_tokens,
        daily_cost=model.daily_cost,
        monthly_requests=model.monthly_requests,
        monthly_tokens=model.monthly_tokens,
        monthly_cost=model.monthly_cost
    )


def model_to_response(model: ModelConfig) -> ModelConfigResponse:
    """Convert database model to response schema"""
    # Use security utils to handle API key masking
    masked_api_key = None
    if model.api_key:
        try:
            security_utils = get_security_utils()
            decrypted_key = security_utils.decrypt_api_key(model.api_key)
            masked_api_key = security_utils.mask_api_key(decrypted_key)
        except Exception:
            masked_api_key = "***invalid***"
    
    return ModelConfigResponse(
        id=model.id,
        name=model.name,
        space_id=model.space_id,
        provider=ModelProvider(model.provider),
        model_type=model.model_type,
        description=model.description,
        tags=model.tags or [],
        base_url=model.base_url,
        is_active=model.is_active,
        parameters=model.parameters or {},
        timeout=model.timeout,
        retry_count=model.retry_count,
        enable_streaming=model.enable_streaming,
        enable_function_calling=model.enable_function_calling,
        created_at=model.created_at,
        updated_at=model.updated_at or model.created_at,  # Fallback to created_at if updated_at is None
        usage_stats=create_usage_stats_from_model(model),
        api_key_masked=masked_api_key,
        is_system_model=model.is_system_model,
        system_model_id=model.system_model_id
    )


@models_router.get("/{space_id}", response_model=ResponseModel[ModelConfigList])
async def get_model_configs(
    space_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(10, ge=1, le=100, description="Page size"),
    provider: Optional[ModelProvider] = Query(None, description="Filter by provider"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name, description, model_type"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    sort_by: Optional[str] = Query("update_time", description="Sort by field (create_time, update_time, name)"),
    sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
): 
    """Get model configurations with pagination and filtering"""
    try:
        # Build filter conditions
        filters = {}
        filters['space_id'] = space_id
        if provider:
            filters['provider'] = provider.value
        if is_active is not None:
            filters['is_active'] = is_active
        if search:
            filters['search'] = search
        if tags:
            filters['tags'] = [tag.strip() for tag in tags.split(",") if tag.strip()]

        # Get paginated data
        models, total = manager.get_paginated_configs(
            page=page,
            size=size,
            filters=filters,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Convert to response format
        model_responses = [model_to_response(model) for model in models]
        
        result = ModelConfigList(
            items=model_responses,
            total=total,
            page=page,
            size=size
        )
        
        return ResponseModel(
            code=200,
            message="Model configurations retrieved successfully",
            data=result 
        )
    except Exception as e:
        logger.error(f"Failed to retrieve model configurations: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@models_router.get("/", response_model=ResponseModel[ModelConfigResponse])
async def get_model_config(
    model_request: ModelConfigRequest,
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """Get a specific model configuration by ID"""
    try:
        model = manager.get_config_by_id(model_request.config_id, model_request.space_id)
        
        return ResponseModel(
            code=200,
            message="Model configuration retrieved successfully",
            data=model_to_response(model)
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model configuration not found"
            ) from e
        logger.error(f"Failed to retrieve model configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@models_router.post("/", response_model=ResponseModel[ModelConfigResponse])
async def create_model_config(
    model_config: ModelConfigCreate, 
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """Create a new model configuration"""
    try:
        # Log the received data for debugging
        logger.info(f"Creating model config with data: {model_config.dict()}")
        db_model = manager.create_config(model_config)
        
        return ResponseModel(
            code=200,
            message="Model configuration created successfully",
            data=model_to_response(db_model)
        )
    except Exception as e:
        logger.error(f"Failed to create model configuration: {str(e)}")
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model configuration with this name already exists"
            ) from e
        raise HTTPException(status_code=500, detail="Internal server error") from e


@models_router.put("/", response_model=ResponseModel[ModelConfigResponse])
async def update_model_config(
    request_data: dict,
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """Update an existing model configuration"""
    try:
        # Extract config_id and space_id from request data
        config_id = request_data.get("config_id")
        space_id = request_data.get("space_id")
        
        if not config_id or not space_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="config_id and space_id are required"
            )
        
        # Remove config_id and space_id from request data to create update object
        update_data = {k: v for k, v in request_data.items() if k not in ["config_id", "space_id"]}
        
        # Create ModelConfigUpdate object from remaining data
        model_config_update = ModelConfigUpdate(**update_data)
        
        # Update the model configuration
        model = manager.update_config(config_id, space_id, model_config_update)
        
        return ResponseModel(
            code=200,
            message="Model configuration updated successfully",
            data=model_to_response(model)
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model configuration not found"
            ) from e
        elif "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model configuration with this name already exists"
            ) from e
        logger.error(f"Error updating model config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@models_router.delete("/", response_model=ResponseModel[dict])
async def delete_model_config(
    model_request: ModelConfigRequest,
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """Delete a model configuration and all related usage logs"""
    try:
        usage_logs_deleted = manager.delete_config(model_request.config_id, model_request.space_id)

        return ResponseModel(
            code=200,
            message=f"Model configuration and {usage_logs_deleted} usage logs deleted successfully",
            data={"deleted_id": model_request.config_id, "usage_logs_deleted": usage_logs_deleted}
        )
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Model configuration not found"
            ) from e
        logger.error(f"Failed to delete model configuration: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


@models_router.post("/{config_id}/test", response_model=ResponseModel[ModelTestResponse])
async def test_model_config(
    config_id: int,
    test_request: ModelTestRequest,
    request: Request,
    test_manager: ModelTester = Depends(get_model_tester),
    current_user: dict = Depends(get_current_user)
):
    """Test a model configuration with a sample prompt"""
    try:
        # Convert user_id_str to int for ModelTester
        user_id = int(current_user["data"]["user_id_str"])
        test_result = await test_manager.test_model_config(
            model_id=config_id,
            test_request=test_request,
            user_id=user_id
        )

        if test_result.success:
            return ResponseModel(
                code=200,
                message="Model test completed successfully",
                data=test_result
            )
        else:
            # Test failed - return appropriate error response
            return ResponseModel(
                code=400,  # Bad Request - indicates test failure
                message=f"Model test failed: {test_result.error or 'Unknown error'}",
                data=test_result
            )

    except ValueError as e:
        # ModelTester throws business logic errors
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Model configuration not found") from e
        else:
            raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error testing model configuration: {str(e)}")
        # Return error details to frontend instead of generic "Internal server error"
        error_msg = str(e)
        # Limit error message length to avoid too large responses
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        raise HTTPException(status_code=500, detail=error_msg) from e


@models_router.post("/{config_id}/toggle", response_model=ResponseModel[ModelConfigResponse])
async def toggle_model_status(
    config_id: int,
    manager: ModelConfigManager = Depends(get_model_config_manager),
    current_user: dict = Depends(get_current_user)
):
    """Toggle the active status of a model configuration"""
    try:
        # Convert user_id_str to int
        user_id = int(current_user["data"]["user_id_str"])
        updated_model_response = manager.toggle_model_status(config_id, user_id)
        
        return ResponseModel(
            code=200,
            message=f"Model {'activated' if updated_model_response.is_active else 'deactivated'} successfully",
            data=updated_model_response
        )
        
    except ValueError as e:
        # Business logic errors thrown by ModelConfigManager
        if "未找到" in str(e) or "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Model configuration not found") from e
        else:
            raise HTTPException(status_code=400, detail="Invalid request parameters") from e
    except Exception as e:
        logger.error(f"Failed to toggle model status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
