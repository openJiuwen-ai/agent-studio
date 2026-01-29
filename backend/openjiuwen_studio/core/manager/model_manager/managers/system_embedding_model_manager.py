import logging
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from openjiuwen_studio.core.exceptions import ModelConfigNameExistsError, ValidationError, ModelConfigNotFoundError
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository, \
    JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.system_embedding_model_repository import SystemEmbeddingModelRepository
from openjiuwen_studio.models import SpaceDB, SystemEmbeddingModelDB
from openjiuwen_studio.schemas.system_embedding_model import SystemEmbeddingModelCreate, SystemEmbeddingModelUpdate

logger = logging.getLogger(__name__)


class SystemEmbeddingModelManager:
    """Manages system embedding model operations including CRUD and validation."""

    def __init__(self, db: Session):
        """Initialize system model manager.

        Args:
            db: Database session
        """
        self.db = db
        self.system_model_repo = SystemEmbeddingModelRepository(db)
        self.model_repo = EmbeddingModelConfigRepository(db)
        self.space_repo = JiuwenBaseRepository(db, SpaceDB)
        self.security_utils = SecurityUtils()

    def create_system_embedding_model(self, model: SystemEmbeddingModelCreate) -> SystemEmbeddingModelDB:
        """Add a system embedding model to the database.
        Args:
            model: SystemEmbeddingModelCreate
        Returns:
            Created system embedding model obj
        """
        try:
            # check if model exists
            if self.system_model_repo.check_model_exists(name=model.model_name):
                raise ModelConfigNameExistsError(f"System embedding model name already exists: {model.model_name}")

            model_dict = model.model_dump(exclude_unset=True)

            # Encrypt API key
            encrypted_api_key = self.security_utils.encrypt_api_key(model.api_key) if model.api_key else None
            if encrypted_api_key:
                model_dict.update({'api_key': encrypted_api_key})

            # add system model
            system_model = self.system_model_repo.create(model_dict)
            logger.info(f"Created system embedding model name: {system_model.model_name}, id: {system_model.id}")

            # add this model for all users
            model_dict.update({'is_system_model': True})
            model_dict.update({'system_model_id': system_model.id})

            all_spaces = self.space_repo.query().all()
            for space in all_spaces:
                if self.model_repo.check_name_exists(space_id=space.space_id, model_name=model.model_name):
                    logger.warning(
                        f"System embedding model name {model.model_name} already exists in space: {space.space_id}")
                    continue
                model_dict.update({'space_id': space.space_id})
                model_config = self.model_repo.create(model_dict)
                logger.info(
                    f"Created embedding model config: {model_config.model_name}, id: {model_config.id} "
                    f"in space: {space.space_id}")

            return system_model
        except ModelConfigNameExistsError:
            raise
        except Exception as e:
            logger.error(f"Failed to create system embedding model: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create system embedding model: {str(e)}") from e

    def update_system_embedding_model(self, model: SystemEmbeddingModelUpdate) -> SystemEmbeddingModelDB:
        """Update system embedding model to the database.
        Args:
            model: SystemEmbeddingModelUpdate
        Returns:
            Updated system embedding model obj
        """
        try:
            # check system model exists
            if not self.system_model_repo.check_model_exists(model_id=model.id):
                raise ModelConfigNotFoundError("System embedding model id not exists")

            model_in_db = self.system_model_repo.get_by_id(model.id)

            # check model name conflict
            name_changed = model.model_name and model_in_db.model_name != model.model_name
            if name_changed:
                if self.system_model_repo.check_model_exists(name=model.model_name):
                    raise ModelConfigNameExistsError(f"System embedding model name already exists: {model.model_name}")

            model_dict = model.model_dump(exclude_unset=True)

            # Encrypt API key
            encrypted_api_key = self.security_utils.encrypt_api_key(model.api_key) if model.api_key else None
            if encrypted_api_key:
                model_dict.update({'api_key': encrypted_api_key})

            # update system model
            updated_model = self.system_model_repo.update(model_in_db, model_dict)
            logger.info(f"Created system embedding model name: {updated_model.model_name}, id: {updated_model.id}")

            # update this model for all users
            model_dict.update({'is_system_model': True})
            model_dict.update({'system_model_id': updated_model.id})

            all_spaces = self.space_repo.query().all()
            for space in all_spaces:
                if name_changed and self.model_repo.check_name_exists(space.space_id, model.model_name):
                    logger.warning(
                        f"System embedding model name {model.model_name} already exists in space: {space.space_id}")
                    continue

                model_config_in_db = self.model_repo.get_by_space_id_and_system_model_id(
                    space_id=space.space_id,
                    system_model_id=updated_model.id
                )
                if model_config_in_db:
                    updated_model_config = self.model_repo.update(model_config_in_db, model_dict)
                    logger.info(
                        f"Updated embedding model config: {updated_model_config.model_name}, "
                        f"id: {updated_model_config.id} in space: {updated_model_config.space_id}")
                else:
                    copy_dict = model_dict.copy()
                    copy_dict.update({'space_id': space.space_id})
                    model_config = self.model_repo.create(copy_dict)
                    logger.info(
                        f"Created embedding model config: {model_config.model_name}, id: {model_config.id} "
                        f"in space: {model_config.space_id}")

            return updated_model
        except (ModelConfigNotFoundError, ModelConfigNameExistsError):
            raise
        except Exception as e:
            logger.error(f"Failed to update system embedding model: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update system embedding model: {str(e)}") from e

    def get_system_embedding_model_with_pagination(
            self,
            page: int = 1,
            size: int = 10,
            filters: Optional[Dict[str, Any]] = None,
            sort_by: Optional[str] = 'update_time',
            sort_order: Optional[str] = 'desc'
    ) -> tuple[List[SystemEmbeddingModelDB], int]:
        """Get system embedding model list with pagination

        Args:
            page: Page number
            size: Page size
            filters: Filter conditions dictionary (Temporary not supported)
            sort_by: Sort by
            sort_order: Sort order (asc or desc)
        Returns:
            (System embedding model list, total count)
        """
        try:
            models, total = self.system_model_repo.get_paginated(
                page=page,
                size=size,
                sort_by=sort_by,
                sort_order=sort_order
            )

            logger.info(f"Paginated system embedding model query successful: page={page}, size={size}, total={total}")
            return models, total

        except Exception as e:
            logger.error(f"Paginated system embedding model query failed: {str(e)}")
            raise ValidationError(f"Paginated system llm model query failed: {str(e)}") from e
