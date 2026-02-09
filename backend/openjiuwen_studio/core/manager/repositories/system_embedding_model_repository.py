from typing import Optional, List

from sqlalchemy.orm import Session

from openjiuwen_studio.core.manager.repositories import BaseRepository
from openjiuwen_studio.models import SystemEmbeddingModelDB


class SystemEmbeddingModelRepository(BaseRepository[SystemEmbeddingModelDB]):
    """System embedding model data access layer.

    Provides specialized database operations for system embedding models.
    """

    def __init__(self, db: Session):
        """Initialize system embedding model repository.

        Args:
            db: Database session
        """
        super().__init__(db, SystemEmbeddingModelDB)

    def check_model_exists(self, model_id: Optional[int] = None, name: Optional[str] = None) -> bool:
        """Check if model already exists.

        Args:
            model_id: model auto_increment id.
            name: user defined model name.

        Returns:
            Whether model exists
        """
        if not model_id and not name:
            return False
        query = self.query()
        if model_id:
            query = query.filter(SystemEmbeddingModelDB.id == model_id)
        if name:
            query = query.filter(SystemEmbeddingModelDB.model_name == name)

        return query.first() is not None

    def get_paginated(
            self,
            page: int = 1,
            size: int = 10,
            sort_by: Optional[str] = 'update_time',
            sort_order: Optional[str] = 'desc'
    ) -> tuple[List[SystemEmbeddingModelDB], int]:
        """Get paginated model configs.

        Args:
            page: Page number
            size: Page size
            sort_by: Sort field ('create_time', 'update_time', 'name')
            sort_order: Sort order ('asc', 'desc')

        Returns:
            (List of system llm models, total count)
        """
        query = self.query()

        # Apply sorting
        if sort_by == 'create_time':
            order_column = SystemEmbeddingModelDB.created_at
        elif sort_by == 'update_time':
            order_column = SystemEmbeddingModelDB.updated_at
        elif sort_by == 'name':
            order_column = SystemEmbeddingModelDB.model_name
        else:
            # Default to create time
            order_column = SystemEmbeddingModelDB.updated_at

        if sort_order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * size
        models = query.offset(offset).limit(size).all()

        return models, total
