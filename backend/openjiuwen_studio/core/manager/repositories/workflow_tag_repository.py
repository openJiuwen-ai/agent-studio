from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from fastapi import status
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    JiuwenBaseRepository, get_db_jw, get_val_from_dict)
from openjiuwen_studio.models.tag import TagDB, workflow_tag_association
from openjiuwen_studio.schemas.common import ResponseModel


class WorkflowTagRepository:
    """Workflow-Tag association data access layer."""

    def __init__(self) -> None:
        pass

    def with_exception_handling(func_) -> Callable:
        @wraps(func_)
        def wrapper(self, *args, **kwargs):
            try:
                return func_(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error: workflow-tag db data processing failed, {str(e)}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Error: workflow-tag db data processing failed, {str(e)}"
                ).model_dump(exclude_none=True)

        return wrapper

    @with_exception_handling
    def associate_tag(self, workflow_data: dict) -> dict:
        """Associate a tag with a workflow.

        Args:
            workflow_data: Association data containing workflow_id, workflow_version, tag_id, space_id

        Returns:
            ResponseModel indicating success/failure
        """
        with get_db_jw() as db:
            if not workflow_data:
                logger.debug(f"No tag data to register: \ndata: {workflow_data}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="No tag data to register"
                ).model_dump(exclude_none=True)

            # Check required fields
            required_fields = ["workflow_id", "workflow_version", "tag_id", "space_id"]
            for field in required_fields:
                if field not in workflow_data or not workflow_data[field]:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message=f"Missing required field: {field}"
                    ).model_dump(exclude_none=True)

            # Check if association already exists (including version)
            find_id = {
                "workflow_id": workflow_data["workflow_id"],
                "workflow_version": workflow_data["workflow_version"],
                "tag_id": workflow_data["tag_id"],
                "space_id": workflow_data["space_id"]
            }

            existing_assoc = WorkflowTagRepository._get_association(db, find_id)
            if existing_assoc.code == status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Association already exists"
                ).model_dump(exclude_none=True)

            # Set timestamps
            timestamp = milliseconds()
            if "create_time" not in workflow_data:
                workflow_data["create_time"] = timestamp
            if "workflow_version" not in workflow_data:
                workflow_data["workflow_version"] = ""

            # Create association
            try:
                db.execute(workflow_tag_association.insert().values(workflow_data))
                db.commit()
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Tag association created successfully"
                ).model_dump(exclude_none=True)
            except Exception as e:
                db.rollback()
                logger.error(f"Tag association creation failed: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Tag association creation failed: {str(e)}"
                ).model_dump(exclude_none=True)

    @with_exception_handling
    def get_workflow_tags(self, query_body: dict) -> dict:
        """Get all tags associated with a workflow.

        Args:
            query_body: Query containing workflow_id and space_id

        Returns:
            ResponseModel with list of associated tags
        """
        with get_db_jw() as db:
            workflow_id = get_val_from_dict(query_body, ["workflow_id"])
            space_id = get_val_from_dict(query_body, ["space_id"])
            workflow_version = get_val_from_dict(query_body, ["workflow_version"])

            if not workflow_id or not space_id:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="workflow_id and space_id are required"
                ).model_dump(exclude_none=True)

            try:
                # Get tag associations with version support
                query = select(workflow_tag_association.c.tag_id).where(
                    workflow_tag_association.c.workflow_id == workflow_id,
                    workflow_tag_association.c.space_id == space_id
                )

                # Add version filter if provided
                if workflow_version:
                    query = query.where(workflow_tag_association.c.workflow_version == workflow_version)

                associations = db.execute(query).fetchall()

                tag_ids = [assoc[0] for assoc in associations]

                if not tag_ids:
                    return ResponseModel(
                        code=status.HTTP_200_OK,
                        message="No tags found for workflow",
                        data=[]
                    ).model_dump(exclude_none=True)

                # Get tag details
                tags_result = db.execute(
                    select(TagDB).where(TagDB.primary_id.in_(tag_ids))
                ).fetchall()

                tag_list = []
                logger.info(f"Found {len(tags_result)} tags for tag_ids: {tag_ids}")

                for tag_row in tags_result:
                    logger.info(f"Processing tag: {tag_row}, type: {type(tag_row)}")
                    # Extract TagDB object from Row
                    tag = tag_row[0]  # First element in the row is the TagDB object
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
                    message="Tags found for workflow",
                    data=tag_list
                ).model_dump(exclude_none=True)

            except Exception as e:
                logger.error(f"Error getting workflow tags: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Error getting workflow tags: {str(e)}"
                ).model_dump(exclude_none=True)

    @with_exception_handling
    def remove_workflow_tags(self, query_body: dict) -> dict:
        """Remove all tag associations for a workflow.

        Args:
            query_body: Query containing workflow_id and space_id

        Returns:
            ResponseModel indicating success/failure
        """
        with get_db_jw() as db:
            try:
                workflow_id = get_val_from_dict(query_body, ["workflow_id"])
                space_id = get_val_from_dict(query_body, ["space_id"])
                workflow_version = get_val_from_dict(query_body, ["workflow_version"])

                if not workflow_id or not space_id:
                    return ResponseModel(
                        code=status.HTTP_400_BAD_REQUEST,
                        message="workflow_id and space_id are required"
                    ).model_dump(exclude_none=True)

                # Build delete query with version support
                delete_query = delete(workflow_tag_association).where(
                    workflow_tag_association.c.workflow_id == workflow_id,
                    workflow_tag_association.c.space_id == space_id,
                    workflow_tag_association.c.workflow_version == workflow_version
                )

                # # Add version filter if provided
                # if workflow_version:
                #     delete_query = delete_query.where(workflow_tag_association.c.workflow_version == workflow_version)

                db.execute(delete_query)
                db.commit()
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Workflow tags removed successfully"
                ).model_dump(exclude_none=True)
            except Exception as e:
                db.rollback()
                logger.error(f"Error removing workflow tags: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Error removing workflow tags: {str(e)}"
                ).model_dump(exclude_none=True)

    @with_exception_handling
    def remove_tag_association(self, query_body: dict) -> dict:
        """Remove specific tag associations from a workflow.

        Args:
            query_body: Query containing workflow_id, space_id, and tag_ids

        Returns:
            ResponseModel indicating success/failure
        """
        with get_db_jw() as db:
            workflow_id = get_val_from_dict(query_body, ["workflow_id"])
            space_id = get_val_from_dict(query_body, ["space_id"])
            tag_ids = get_val_from_dict(query_body, ["tag_ids"])

            if not workflow_id or not space_id or not tag_ids:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="workflow_id, space_id, and tag_ids are required"
                ).model_dump(exclude_none=True)

            if not isinstance(tag_ids, list):
                tag_ids = [tag_ids]

            try:
                db.execute(
                    delete(workflow_tag_association).where(
                        workflow_tag_association.c.workflow_id == workflow_id,
                        workflow_tag_association.c.space_id == space_id,
                        workflow_tag_association.c.tag_id.in_(tag_ids)
                    )
                )
                db.commit()
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Tag association removed successfully"
                ).model_dump(exclude_none=True)
            except Exception as e:
                db.rollback()
                logger.error("Error removing tag association")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Error removing tag association: {str(e)}"
                ).model_dump(exclude_none=True)

    @with_exception_handling
    def find_workflows_by_tags(self, query_body: dict) -> dict:
        """Get workflow IDs that have any of the specified tags.

        Args:
            query_body: Query containing space_id and tag_ids

        Returns:
            ResponseModel with list of workflow IDs that have the specified tags
        """
        with get_db_jw() as db:
            space_id = get_val_from_dict(query_body, ["space_id"])
            tag_ids = get_val_from_dict(query_body, ["tag_ids"])

            if not space_id or not tag_ids:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="space_id and tag_ids are required"
                ).model_dump(exclude_none=True)

            if not isinstance(tag_ids, list):
                tag_ids = [tag_ids]

            try:
                # Get workflow IDs that have any of the specified tags
                # We need to get distinct workflow_ids, ignoring workflow_version to get all versions
                query = select(workflow_tag_association.c.workflow_id).where(
                    workflow_tag_association.c.space_id == space_id,
                    workflow_tag_association.c.tag_id.in_(tag_ids)
                ).distinct()

                logger.info(f"Executing tag search query for space_id: {space_id}, tag_ids: {tag_ids}")
                associations = db.execute(query).fetchall()
                workflow_ids = [assoc[0] for assoc in associations]
                logger.info(f"Tag search returned {len(workflow_ids)} workflow IDs")

                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Workflows found for tags",
                    data=workflow_ids
                ).model_dump(exclude_none=True)

            except Exception as e:
                logger.error(
                    f"Error finding workflows by tags for space_id {space_id}, tag_ids {tag_ids}: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Error finding workflows by tags: {str(e)}"
                ).model_dump(exclude_none=True)

    @staticmethod
    def _get_association(db: Session, find_id: dict) -> ResponseModel:
        """Helper method to get tag association.

        Args:
            db: Database session
            find_id: Query parameters containing workflow_id, workflow_version, tag_id, space_id

        Returns:
            ResponseModel with association data if found
        """
        try:
            workflow_id = find_id.get("workflow_id")
            workflow_version = find_id.get("workflow_version")
            tag_id = find_id.get("tag_id")
            space_id = find_id.get("space_id")

            if not all([workflow_id, workflow_version, tag_id, space_id]):
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="workflow_id, workflow_version, tag_id, and space_id are required"
                )

            association = db.execute(
                select(workflow_tag_association).where(
                    workflow_tag_association.c.workflow_id == workflow_id,
                    workflow_tag_association.c.workflow_version == workflow_version,
                    workflow_tag_association.c.tag_id == tag_id,
                    workflow_tag_association.c.space_id == space_id
                )
            ).fetchone()

            if association:
                # Extract data from SQLAlchemy Row object by column name
                association_data = {
                    "workflow_id": association.workflow_id,
                    "workflow_version": association.workflow_version,
                    "tag_id": association.tag_id,
                    "space_id": association.space_id,
                    "create_time": association.create_time
                }
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Association found",
                    data=association_data
                )
            else:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="Association not found"
                )

        except Exception as e:
            logger.error(f"Error getting tag association: {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Error getting association: {str(e)}"
            )


# Create singleton instance
workflow_tag_repository = WorkflowTagRepository()
