import logging
import os
from typing import Optional

from fastapi import APIRouter, Security, HTTPException
from fastapi import status
from fastapi.params import Depends, Query
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from openjiuwen_studio.core.database import get_db
from openjiuwen_studio.core.exceptions import ModelConfigNameExistsError, ValidationError, ModelConfigNotFoundError
from openjiuwen_studio.core.manager.model_manager.managers.system_embedding_model_manager import \
    SystemEmbeddingModelManager
from openjiuwen_studio.core.manager.model_manager.managers.system_llm_model_manager import SystemLLMModelManager
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.models import SystemLLMModelDB, SystemEmbeddingModelDB
from openjiuwen_studio.schemas import ResponseModel
from openjiuwen_studio.schemas.embedding_model_config import EmbeddingProtocol
from openjiuwen_studio.schemas.system_embedding_model import SystemEmbeddingModelResponse, SystemEmbeddingModelCreate, \
    SystemEmbeddingModelUpdate, SystemEmbeddingModelRespList
from openjiuwen_studio.schemas.system_llm_model import SystemLLMModelCreate, SystemLLMModelUpdate, \
    SystemLLMModelResponse, SystemLLMModelRespList

logger = logging.getLogger(__name__)

system_router = APIRouter()

api_key_header = APIKeyHeader(name="X-System-Token")


def get_system_llm_model_manager(db: Session = Depends(get_db)) -> SystemLLMModelManager:
    return SystemLLMModelManager(db)


def get_system_embedding_model_manager(db: Session = Depends(get_db)) -> SystemEmbeddingModelManager:
    return SystemEmbeddingModelManager(db)


def get_security_utils() -> SecurityUtils:
    return SecurityUtils()


async def verify_system_token(api_key: str = Security(api_key_header)):
    """Check system token"""
    system_admin_token = os.getenv("SYSTEM_ADMIN_TOKEN", "")
    if api_key != system_admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid system token")


@system_router.post("/models", response_model=ResponseModel[SystemLLMModelResponse],
                    dependencies=[Depends(verify_system_token)])
async def create_system_model(
        model: SystemLLMModelCreate,
        manager: SystemLLMModelManager = Depends(get_system_llm_model_manager)
):
    """Create a system LLM model"""
    try:
        logger.info(f"Creating system model for {model.name}")
        system_model = manager.create_system_llm_model(model)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="System llm model created successfully",
            data=_llm_model_to_response(system_model)
        )
    except ModelConfigNameExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@system_router.put("/models", response_model=ResponseModel[SystemLLMModelResponse],
                   dependencies=[Depends(verify_system_token)])
async def update_system_model(
        model: SystemLLMModelUpdate,
        manager: SystemLLMModelManager = Depends(get_system_llm_model_manager)
):
    """Update system LLM model"""
    try:
        logger.info(f"Updating system model for {model.id}")
        system_model = manager.update_system_llm_model(model)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"System llm model update successfully for id: {model.id}",
            data=_llm_model_to_response(system_model)
        )
    except (ModelConfigNotFoundError, ModelConfigNameExistsError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@system_router.get("/models", response_model=ResponseModel[SystemLLMModelRespList],
                   dependencies=[Depends(verify_system_token)])
async def get_system_models(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Page size"),
        sort_by: Optional[str] = Query("update_time", description="Sort by field (create_time, update_time, name)"),
        sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
        manager: SystemLLMModelManager = Depends(get_system_llm_model_manager)
):
    """Get system LLM model list with pagination"""
    try:
        models, total = manager.get_system_llm_model_with_pagination(
            page=page,
            size=size,
            filters={},
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Convert to response format
        model_responses = [_llm_model_to_response(model) for model in models]

        result = SystemLLMModelRespList(
            items=model_responses,
            total=total,
            page=page,
            size=size
        )

        return ResponseModel(
            code=200,
            message="System llm models retrieved successfully",
            data=result
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@system_router.post("/embedding-models", response_model=ResponseModel[SystemEmbeddingModelResponse],
                    dependencies=[Depends(verify_system_token)])
async def create_system_embedding_model(
        model: SystemEmbeddingModelCreate,
        manager: SystemEmbeddingModelManager = Depends(get_system_embedding_model_manager)
):
    """Create a system embedding model"""
    try:
        logger.info(f"Creating system model for {model.model_name}")
        system_model = manager.create_system_embedding_model(model)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="System llm model created successfully",
            data=_embedding_model_to_response(system_model)
        )
    except ModelConfigNameExistsError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@system_router.put("/embedding-models", response_model=ResponseModel[SystemEmbeddingModelResponse],
                   dependencies=[Depends(verify_system_token)])
async def update_system_embedding_model(
        model: SystemEmbeddingModelUpdate,
        manager: SystemEmbeddingModelManager = Depends(get_system_embedding_model_manager)
):
    """Update system embedding model"""
    try:
        logger.info(f"Updating system embedding model for {model.id}")
        system_model = manager.update_system_embedding_model(model)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message=f"System llm model update successfully for id: {model.id}",
            data=_embedding_model_to_response(system_model)
        )
    except (ModelConfigNotFoundError, ModelConfigNameExistsError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@system_router.get("/embedding-models", response_model=ResponseModel[SystemEmbeddingModelRespList],
                   dependencies=[Depends(verify_system_token)])
async def get_system_embedding_models(
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(10, ge=1, le=100, description="Page size"),
        sort_by: Optional[str] = Query("update_time", description="Sort by field (create_time, update_time, name)"),
        sort_order: Optional[str] = Query("desc", description="Sort order (asc, desc)"),
        manager: SystemEmbeddingModelManager = Depends(get_system_embedding_model_manager)
):
    """Get system embedding model list with pagination"""
    try:
        models, total = manager.get_system_embedding_model_with_pagination(
            page=page,
            size=size,
            filters={},
            sort_by=sort_by,
            sort_order=sort_order
        )

        # Convert to response format
        model_responses = [_embedding_model_to_response(model) for model in models]

        result = SystemEmbeddingModelRespList(
            items=model_responses,
            total=total,
            page=page,
            size=size
        )

        return ResponseModel(
            code=200,
            message="System embedding models retrieved successfully",
            data=result
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


def _llm_model_to_response(model: SystemLLMModelDB) -> SystemLLMModelResponse:
    """Convert system llm model to response format

    Args:
        model: System model instance

    Returns:
        System model response
    """
    # Use security utils to handle API key masking
    masked_api_key = None
    if model.api_key:
        try:
            security_utils = get_security_utils()
            decrypted_key = security_utils.decrypt_api_key(model.api_key)
            masked_api_key = security_utils.mask_api_key(decrypted_key)
        except Exception:
            masked_api_key = "***invalid***"

    return SystemLLMModelResponse(
        id=model.id,
        name=model.name,
        provider=model.provider,
        model_type=model.model_type,
        description=model.description,
        is_active=model.is_active,
        base_url=model.base_url,
        parameters=model.parameters or {},
        timeout=model.timeout,
        created_at=model.created_at,
        updated_at=model.updated_at,
        api_key_masked=masked_api_key,
        space_id=''
    )


def _embedding_model_to_response(model: SystemEmbeddingModelDB) -> SystemEmbeddingModelResponse:
    """Convert system embedding model to response format

    Args:
        model: System model instance

    Returns:
        System model response
    """
    # Use security utils to handle API key masking
    masked_api_key = None
    if model.api_key:
        try:
            security_utils = get_security_utils()
            decrypted_key = security_utils.decrypt_api_key(model.api_key)
            masked_api_key = security_utils.mask_api_key(decrypted_key)
        except Exception:
            masked_api_key = "***invalid***"

    return SystemEmbeddingModelResponse(
        id=model.id,
        model_name=model.model_name,
        protocol=EmbeddingProtocol(model.protocol),
        model_id=model.model_id,
        api_base=model.api_base,
        max_batch_size=model.max_batch_size,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
        api_key_masked=masked_api_key,
        space_id=''
    )
