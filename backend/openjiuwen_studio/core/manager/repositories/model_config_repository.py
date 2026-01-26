from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import BaseRepository
from openjiuwen_studio.models.model_config import ModelConfig
from openjiuwen_studio.schemas.model_config import ModelProvider


class ModelConfigRepository(BaseRepository[ModelConfig]):
    """Model configuration data access layer.
    
    Provides specialized database operations for model configurations.
    """
    
    def __init__(self, db: Session):
        """Initialize model config repository.
        
        Args:
            db: Database session
        """
        super().__init__(db, ModelConfig)
    
    def get_by_name(self, name: str) -> Optional[ModelConfig]:
        """Get model config by name.
        
        Args:
            name: Model config name
            
        Returns:
            Model config instance or None
        """
        return self.filter_by(name=name).first()
    
    def get_active_models(self) -> List[ModelConfig]:
        """Get all active model configs.
        
        Returns:
            List of active model configs
        """
        return self.filter_by(is_active=True).all()
    
    def search_models(self, search_term: str) -> List[ModelConfig]:
        """Search model configs.
        
        Search for matching model configs in name, description, and model type.
        
        Args:
            search_term: Search keyword
            
        Returns:
            List of matching model configs
        """
        search_filter = or_(
            ModelConfig.name.ilike(f"%{search_term}%"),
            ModelConfig.description.ilike(f"%{search_term}%"),
            ModelConfig.model_type.ilike(f"%{search_term}%"),
            ModelConfig.space_id.ilike(f"%{search_term}%")
        )
        return self.query().filter(search_filter).all()
    
    def filter_by_provider(self, provider: ModelProvider) -> List[ModelConfig]:
        """Filter model configs by provider.
        
        Args:
            provider: Model provider
            
        Returns:
            List of model configs for specified provider
        """
        return self.filter_by(provider=provider.value).all()
    
    def filter_by_tags(self, tags: List[str]) -> List[ModelConfig]:
        """Filter model configs by tags.
        
        Args:
            tags: List of tags
            
        Returns:
            List of model configs containing specified tags
        """
        query = self.query()
        for tag in tags:
            query = query.filter(ModelConfig.tags.contains([tag]))
        return query.all()
    
    def get_paginated(
        self,
        space_id: str,
        page: int = 1,
        size: int = 10,
        id: Optional[int] = None,
        provider: Optional[ModelProvider] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        sort_by: Optional[str] = 'update_time',
        sort_order: Optional[str] = 'desc'
    ) -> tuple[List[ModelConfig], int]:
        """Get paginated model configs.

        Args:
            space_id: Space ID
            page: Page number
            size: Page size
            provider: Provider filter
            is_active: Active status filter
            search: Search keyword
            tags: Tags filter
            sort_by: Sort field ('create_time', 'update_time', 'name')
            sort_order: Sort order ('asc', 'desc')

        Returns:
            (List of model configs, total count)
        """
        query = self.query()
        
        # Apply filter conditions
        query = query.filter(ModelConfig.space_id == space_id)
        if id:
            query = query.filter(ModelConfig.id == id)
        if provider:
            query = query.filter(ModelConfig.provider == provider.value)
        
        if is_active is not None:
            query = query.filter(ModelConfig.is_active == is_active)
        
        if search:
            search_filter = or_(
                ModelConfig.name.ilike(f"%{search}%"),
                ModelConfig.description.ilike(f"%{search}%"),
                ModelConfig.model_type.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        if tags:
            for tag in tags:
                query = query.filter(ModelConfig.tags.contains([tag]))

        # Apply sorting
        if sort_by == 'create_time':
            order_column = ModelConfig.created_at
        elif sort_by == 'update_time':
            order_column = ModelConfig.updated_at
        elif sort_by == 'name':
            order_column = ModelConfig.name
        else:
            # Default to create time
            order_column = ModelConfig.created_at

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
    
    def check_name_exists(self, space_id: str,
                        name: Optional[str] = None,
                        config_id: Optional[int] = None,
                        exclude_id: Optional[int] = None) -> bool:
        """Check if model config name already exists.
        
        Args:
            name: Model config name
            space_id: Check in selected space
			config_id: Model config id
            exclude_id: ID to exclude (for update checks)
            
        Returns:
            Whether name exists
        """
        query = self.query().filter(ModelConfig.space_id == space_id)
        if name: 
            query = query.filter(ModelConfig.name == name)
        if config_id:
            query = query.filter(ModelConfig.id == config_id)
        
        if exclude_id:
            query = query.filter(ModelConfig.id != exclude_id)
        
        return query.first() is not None
    
    def get_models_by_ids(self, model_ids: List[int]) -> List[ModelConfig]:
        """Get model configs by ID list.
        
        Args:
            model_ids: List of model IDs
            
        Returns:
            List of model configs
        """
        return self.query().filter(ModelConfig.id.in_(model_ids)).all()
    
    def get_recently_used_models(self, days: int = 7, limit: int = 10) -> List[ModelConfig]:
        """Get recently used model configs.
        
        Args:
            days: Number of recent days
            limit: Limit count
            
        Returns:
            List of recently used model configs
        """
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
        
        return self.query().filter(
            and_(
                ModelConfig.last_used.isnot(None),
                ModelConfig.last_used >= cutoff_date
            )
        ).order_by(ModelConfig.last_used.desc()).limit(limit).all()
    
    def get_models_with_high_usage(self, min_requests: int = 100) -> List[ModelConfig]:
        """Get model configs with high usage.
        
        Args:
            min_requests: Minimum request count
            
        Returns:
            List of high usage model configs
        """
        return self.query().filter(
            ModelConfig.total_requests >= min_requests
        ).order_by(ModelConfig.total_requests.desc()).all()
    
    def get_models_by_success_rate(self, min_rate: float = 0.9) -> List[ModelConfig]:
        """Get model configs by success rate.
        
        Args:
            min_rate: Minimum success rate
            
        Returns:
            List of high success rate model configs
        """
        return self.query().filter(
            ModelConfig.success_rate >= min_rate
        ).order_by(ModelConfig.success_rate.desc()).all()
    
    def update_usage_stats(
        self,
        model_id: int,
        tokens_used: int,
        cost: float,
        response_time: float,
        success: bool
    ) -> Optional[ModelConfig]:
        """Update model usage statistics.
        
        Args:
            model_id: Model ID
            tokens_used: Number of tokens used
            cost: Cost
            response_time: Response time
            success: Whether successful
            
        Returns:
            Updated model config
        """
        model = self.get_by_id(model_id)
        if model:
            model.update_usage_stats(tokens_used, cost, response_time, success)
            try:
                self.db.commit()
                self.db.refresh(model)
            except Exception as e:
                logger.error(f"Failed to update usage stats for model {model_id}: {e}")
                self.db.rollback()
                raise
        return model
    
    def toggle_status(self, model_id: int) -> Optional[ModelConfig]:
        """Toggle model active status.
        
        Args:
            model_id: Model ID
            
        Returns:
            Updated model config
        """
        model = self.get_by_id(model_id)
        if model:
            model.is_active = not model.is_active
            model.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            try:
                self.db.commit()
                self.db.refresh(model)
            except Exception as e:
                logger.error(f"Failed to toggle stats for model {model_id}: {e}")
                self.db.rollback()
                raise
        return model