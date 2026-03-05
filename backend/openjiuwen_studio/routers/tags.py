from fastapi import APIRouter, HTTPException, status, Depends, Query, Body
from typing import Optional, List

from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.tag import (
    TagCreateRequest, TagUpdateRequest, TagSearchRequest, TagListRequest,
    TagIdQuery, TagDeleteQuery, TagSearchQuery, TagQuery, TagGetOrCreateRequest,
    TagBatchCreateRequest, TagResponse, TagListResponse, TagGetOrCreateResponse,
    TagBatchCreateResponse
)
from openjiuwen_studio.core.manager.tag import (
    tag_create, tag_get, tag_list, tag_update, tag_delete,
    tag_get_by_id, tag_search, tag_get_or_create, tag_batch_create
)
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen.core.common.logging import logger

tags_router = APIRouter()


@tags_router.post("/create", response_model=ResponseModel[TagResponse])
async def create_tag(
        request: TagCreateRequest,
        current_user: dict = Depends(get_current_user)
):
    """Create a new tag.

    Args:
        request: Tag creation request containing tag data
        current_user: Current authenticated user

    Returns:
        Created tag information
    """
    try:
        tag_data = request.tag.dict()
        result = tag_create(tag_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create tag: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tag: an internal error occurred"
        ) from e


@tags_router.get("/search", response_model=ResponseModel[List[TagResponse]])
async def search_tags(
        space_id: str = Query(..., min_length=1, max_length=100, description="Space identifier"),
        pattern: str = Query(..., min_length=1, max_length=100, description="Search pattern"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(100, ge=1, le=1000, description="Page size"),
        current_user: dict = Depends(get_current_user)
):
    """Search tags by name pattern within a space.

    Args:
        space_id: Space identifier
        pattern: Search pattern to match tag names
        is_active: Optional filter for active status
        page: Page number for pagination
        page_size: Number of items per page
        current_user: Current authenticated user

    Returns:
        List of matching tags
    """
    try:
        query_data = {
            "space_id": space_id,
            "search_pattern": pattern,
            "is_active": is_active,
            "page": page,
            "page_size": page_size
        }

        result = tag_search(query_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search tags: {str(e)}"
        ) from e


@tags_router.get("/list", response_model=ResponseModel[TagListResponse])
async def list_tags(
        space_id: str = Query(..., min_length=1, max_length=100, description="Space identifier"),
        tag_name: Optional[str] = Query(None, max_length=100, description="Filter by tag name"),
        is_active: Optional[bool] = Query(None, description="Filter by active status"),
        page: int = Query(1, ge=1, description="Page number"),
        page_size: int = Query(100, ge=1, le=1000, description="Page size"),
        current_user: dict = Depends(get_current_user)
):
    """List tags in a space with filtering and pagination.

    Args:
        space_id: Space identifier
        tag_name: Optional filter by tag name
        is_active: Optional filter for active status
        page: Page number for pagination
        page_size: Number of items per page
        current_user: Current authenticated user

    Returns:
        Paginated list of tags
    """
    try:
        query_data = {
            "space_id": space_id,
            "tag_name": tag_name,
            "is_active": is_active,
            "page": page,
            "page_size": page_size
        }

        result = tag_list(query_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        # Convert result to TagListResponse format
        if result.data:
            tags = result.data
            total = len(tags)
            tag_list_response = TagListResponse(
                tags=tags,
                total=total,
                page=page,
                page_size=page_size
            )
            result.data = tag_list_response.dict()

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tags: {type(e).__name__}"
        ) from e


@tags_router.post("/get-or-create", response_model=ResponseModel[TagGetOrCreateResponse])
async def get_or_create_tag(
        request: TagGetOrCreateRequest,
        current_user: dict = Depends(get_current_user)
):
    """Get existing tag or create if it doesn't exist.

    Args:
        request: Tag get or create request
        current_user: Current authenticated user

    Returns:
        Tag information and creation status
    """
    try:
        tag_data = request.dict()
        result = tag_get_or_create(tag_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get or create tag: {type(e).__name__}"
        ) from e


@tags_router.post("/batch", response_model=ResponseModel[TagBatchCreateResponse])
async def batch_create_tags(
        request: TagBatchCreateRequest,
        current_user: dict = Depends(get_current_user)
):
    """Create multiple tags in batch.

    Args:
        request: Batch tag creation request
        current_user: Current authenticated user

    Returns:
        Batch creation results
    """
    try:
        tags_data = [tag.dict() for tag in request.tags]
        result = tag_batch_create(tags_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to batch create tags: {type(e).__name__}"
        ) from e


@tags_router.get("/{tag_id}", response_model=ResponseModel[TagResponse])
async def get_tag_by_id(
        tag_id: int,
        current_user: dict = Depends(get_current_user)
):
    """Get tag by primary ID.

    Args:
        tag_id: Primary tag ID
        current_user: Current authenticated user

    Returns:
        Tag information
    """
    try:
        query_data = {"primary_id": tag_id}
        result = tag_get_by_id(query_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tag: {type(e).__name__}"
        ) from e


@tags_router.get("/", response_model=ResponseModel[TagResponse])
async def get_tag(
        space_id: str = Query(..., min_length=1, max_length=100, description="Space identifier"),
        tag_name: str = Query(..., min_length=1, max_length=100, description="Tag name"),
        current_user: dict = Depends(get_current_user)
):
    """Get tag by space_id and tag_name.

    Args:
        space_id: Space identifier
        tag_name: Tag name
        current_user: Current authenticated user

    Returns:
        Tag information
    """
    try:
        query_data = {"space_id": space_id, "tag_name": tag_name}
        result = tag_get(query_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tag: {type(e).__name__}"
        ) from e


@tags_router.put("/{tag_id}", response_model=ResponseModel[TagResponse])
async def update_tag(
        tag_id: int,
        request: TagUpdateRequest,
        current_user: dict = Depends(get_current_user)
):
    """Update tag information.

    Args:
        tag_id: Primary tag ID
        request: Tag update request
        current_user: Current authenticated user

    Returns:
        Updated tag information
    """
    try:
        # First, get the tag to verify it exists and user has access
        query_data = {"primary_id": tag_id}
        existing_tag = tag_get_by_id(query_data, current_user)

        if existing_tag.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tag not found"
            )

        # Prepare update data
        update_data = request.tag_data.dict(exclude_unset=True)

        # Use primary_id for direct update (new method)
        update_data["primary_id"] = tag_id

        result = tag_update(update_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update tag: {type(e).__name__}"
        ) from e


@tags_router.delete("/delete", response_model=ResponseModel[dict])
async def delete_tag(
        space_id: str = Query(..., min_length=1, max_length=100, description="Space identifier"),
        tag_name: str = Query(..., min_length=1, max_length=100, description="Tag name"),
        current_user: dict = Depends(get_current_user)
):
    """Delete a tag by space_id and tag_name.

    Args:
        space_id: Space identifier
        tag_name: Tag name
        current_user: Current authenticated user

    Returns:
        Deletion confirmation
    """
    try:
        query_data = {"space_id": space_id, "tag_name": tag_name}
        result = tag_delete(query_data, current_user)

        if result.code != status.HTTP_200_OK:
            raise HTTPException(
                status_code=result.code,
                detail=result.message
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete tag: {type(e).__name__}"
        ) from e
