from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from fastapi import status
from sqlalchemy import and_, bindparam, func, or_
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    JiuwenBaseRepository, get_db_jw, get_val_from_dict)
from openjiuwen_studio.models.tag import TagDB
from openjiuwen_studio.schemas.common import ResponseModel


class TagRepository:
    """Tag data access layer for workflow tag management."""

    def __init__(self) -> None:
        pass

    def with_exception_handling(func_) -> dict:
        @wraps(func_)
        def wrapper(self, *args, **kwargs):
            try:
                return func_(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: Tag db data processing failed")
                logger.debug(f"Tag db processing exception: {type(e).__name__}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Error: Tag db data could not be processed: {type(e).__name__}"
                ).model_dump(exclude_none=True)
        return wrapper

    @with_exception_handling
    def tag_create(self, tag_data: dict) -> Callable:
        """Create a new tag.

        Args:
            tag_data: Tag creation data containing space_id and tag_name

        Returns:
            ResponseModel with created tag data
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            if not tag_data:
                logger.debug(f"No tag data to register: \ndata: {tag_data}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="No tag data to register"
                ).model_dump(exclude_none=True)

            # Check required fields
            required_fields = ["space_id", "tag_name"]
            for field in required_fields:
                if field not in tag_data or not tag_data[field]:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message=f"Missing required field: {field}"
                    ).model_dump(exclude_none=True)

            # Check if tag already exists in this space
            find_id = {
                "space_id": tag_data["space_id"],
                "tag_name": tag_data["tag_name"]
            }

            existing_tag = tag_db.get_dl_in_sql(find_id=find_id)
            if existing_tag.code == status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Tag '{tag_data['tag_name']}' already exists in space '{tag_data['space_id']}'"
                ).model_dump(exclude_none=True)

            # Set timestamps
            timestamp = milliseconds()
            if "create_time" not in tag_data:
                tag_data["create_time"] = timestamp
            if "update_time" not in tag_data:
                tag_data["update_time"] = timestamp

            # Set default values
            if "is_active" not in tag_data:
                tag_data["is_active"] = True
            if "usage_count" not in tag_data:
                tag_data["usage_count"] = 0

            return tag_db.register_dl_in_sql(find_id=find_id, dl=tag_data).model_dump(exclude_none=True)

    @with_exception_handling
    def tag_get(self, query_body: dict) -> dict:
        """Get tag by space_id and tag_name.

        Args:
            query_body: Query containing space_id and tag_name

        Returns:
            ResponseModel with tag data
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            find_id = {
                "space_id": get_val_from_dict(query_body, ["space_id"]),
                "tag_name": get_val_from_dict(query_body, ["tag_name"])
            }

            # Remove None values
            find_id = {k: v for k, v in find_id.items() if v is not None}

            if not find_id:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="At least space_id or tag_name is required"
                ).model_dump(exclude_none=True)
            db_res = tag_db.get_dl_in_sql(find_id=find_id)
            if db_res.data and len(db_res.data) == 1:
                db_res.data = db_res.data[0]
            return db_res.model_dump(exclude_none=True)

    @with_exception_handling
    def tag_list(self, query_body: dict) -> dict:
        """Get list of tags with filtering options.

        Args:
            query_body: Query containing space_id (required), and optional filters

        Returns:
            ResponseModel with list of tags
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            space_id = get_val_from_dict(query_body, ["space_id"])
            if not space_id:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="space_id is required"
                ).model_dump(exclude_none=True)

            # Build query filters
            find_id = {"space_id": space_id}

            # Add optional filters
            is_active = get_val_from_dict(query_body, ["is_active"])
            if is_active is not None:
                find_id["is_active"] = is_active

            # Get tags
            result = tag_db.get_dl_in_sql(find_id=find_id)

            return result.model_dump(exclude_none=True)

    @with_exception_handling
    def tag_update(self, tag_data: dict) -> dict:
        """Update an existing tag.

        Args:
            tag_data: Tag update data containing either:
                     - primary_id for direct lookup, or
                     - space_id, tag_name for legacy lookup

        Returns:
            ResponseModel with updated tag data
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            if not tag_data:
                logger.debug("No tag data to update")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="No tag data to update"
                ).model_dump(exclude_none=True)

            # Check if primary_id is provided (new method)
            primary_id = get_val_from_dict(tag_data, ["primary_id", "id"])
            if primary_id:
                # Use primary_id for lookup
                find_id = {"primary_id": primary_id}
            else:
                # Legacy method: use space_id + tag_name
                find_id = {
                    "space_id": get_val_from_dict(tag_data, ["space_id"]),
                    "tag_name": get_val_from_dict(tag_data, ["tag_name"])
                }
                # Remove None values
                find_id = {k: v for k, v in find_id.items() if v is not None}

                if not find_id:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message="Either primary_id or space_id+tag_name are required"
                    ).model_dump(exclude_none=True)

            # Check if tag exists
            existing_tag = tag_db.get_dl_in_sql(find_id=find_id)
            if existing_tag.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Tag not found"
                ).model_dump(exclude_none=True)

            # Prepare update data (exclude find_id fields)
            update_data = {}
            for key, value in tag_data.items():
                if key not in ["space_id"]:
                    update_data[key] = value

            # Set update timestamp
            timestamp = milliseconds()
            update_data["update_time"] = timestamp

            return tag_db.update_dl_in_sql(find_id=find_id, update_dl=update_data).model_dump(exclude_none=True)

    @with_exception_handling
    def tag_delete(self, query_body: dict) -> dict:
        """Delete a tag.

        Args:
            query_body: Query containing space_id and tag_name

        Returns:
            ResponseModel indicating deletion success
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            # Find the tag to delete
            find_id = {
                "space_id": get_val_from_dict(query_body, ["space_id"]),
                "tag_name": get_val_from_dict(query_body, ["tag_name"])
            }

            # Remove None values and validate
            find_id = {k: v for k, v in find_id.items() if v is not None}

            if not find_id or len(find_id) != 2:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="Both space_id and tag_name are required for deletion"
                ).model_dump(exclude_none=True)

            # Check if tag exists before deletion
            existing_tag = tag_db.get_dl_in_sql(find_id=find_id)
            if existing_tag.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Tag not found"
                ).model_dump(exclude_none=True)

            return tag_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)

    @with_exception_handling
    def tag_get_by_id(self, query_body: dict) -> dict:
        """Get tag by primary ID.

        Args:
            query_body: Query containing primary_id

        Returns:
            ResponseModel with tag data
        """
        with get_db_jw() as db:
            tag_db = JiuwenBaseRepository(db, TagDB)

            primary_id = get_val_from_dict(query_body, ["primary_id", "id"])
            if not primary_id:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="primary_id is required"
                ).model_dump(exclude_none=True)

            return tag_db.get_dl_in_sql(find_id={"primary_id": primary_id}, 
                                         return_first_item=True).model_dump(exclude_none=True)

    @with_exception_handling
    def tag_search(self, query_body: dict) -> dict:
        """Search tags by name pattern within a space.

        Args:
            query_body: Query containing space_id and search_pattern

        Returns:
            ResponseModel with matching tags
        """
        with get_db_jw() as db:
            space_id = get_val_from_dict(query_body, ["space_id"])
            search_pattern = get_val_from_dict(query_body, ["search_pattern", "pattern"])

            if not space_id:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="space_id is required"
                ).model_dump(exclude_none=True)

            if not search_pattern:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="search_pattern is required"
                ).model_dump(exclude_none=True)

            # Use direct query for pattern search
            try:
                query = db.query(TagDB).filter(
                    TagDB.space_id == bindparam('space_id'),
                    TagDB.tag_name.ilike(bindparam('search_pattern'))
                ).params(
                    space_id=space_id,
                    search_pattern=f"%{search_pattern}%"
                )

                # Add active filter if specified
                is_active = get_val_from_dict(query_body, ["is_active"])
                if is_active is not None:
                    query = query.filter(TagDB.is_active == is_active)

                tags = query.all()

                # Convert to dict format
                tag_list = []
                for tag in tags:
                    tag_dict = {
                        "primary_id": tag.primary_id,
                        "space_id": tag.space_id,
                        "tag_name": tag.tag_name,
                        "tag_color": tag.tag_color,
                        "is_active": tag.is_active,
                        "usage_count": tag.usage_count,
                        "create_time": tag.create_time,
                        "update_time": tag.update_time,
                        "create_user": tag.create_user,
                        "update_user": tag.update_user
                    }
                    tag_list.append(tag_dict)

                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Tags found",
                    data=tag_list
                ).model_dump(exclude_none=True)

            except Exception as e:
                logger.error("Searching tags failed")
                logger.debug(f"Tag search exception: {type(e).__name__}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Searching tags failed: {type(e).__name__}"
                ).model_dump(exclude_none=True)


# Create singleton instance
tag_repository = TagRepository()