from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Query, Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.exceptions import ModelApiKeyDecryptError
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils

# Generic type variable for type safety
T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Generic data access base class.
    
    Provides standard CRUD operations and query building functionality.
    Supports generics to ensure type safety.
    """
    
    def __init__(self, db: Session, model_class: Type[T]):
        """Initialize repository.
        
        Args:
            db: Database session
            model_class: Model class
        """
        self.db = db
        self.model_class = model_class
    
    def create(self, obj_in: Dict[str, Any] | T) -> T:
        """Create new record.
        
        Args:
            obj_in: Creation data dictionary
            
        Returns:
            Created model instance
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            db_obj = obj_in if isinstance(obj_in, self.model_class) else self.model_class(**obj_in)
            self.db.add(db_obj)
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create database record: {type(e).__name__}")
            raise

    def get_by_id(self, id: int) -> Optional[T]:
        """Get record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Model instance or None
        """
        try:
            return self.db.query(self.model_class).filter(
                self.model_class.id == id
            ).first()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get record by ID: {type(e).__name__}")
            raise
    
    def get_multi(
        self, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = 'update_time'
    ) -> List[T]:
        """Get multiple records.
        
        Args:
            skip: Number of records to skip
            limit: Number of records to limit
            order_by: Order by field
            
        Returns:
            List of model instances
        """
        try:
            query = self.db.query(self.model_class)
            
            if order_by:
                if hasattr(self.model_class, order_by):
                    query = query.order_by(getattr(self.model_class, order_by))
            
            return query.offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get multiple database records: {type(e).__name__}")
            raise
    
    def update(self, db_obj: T, obj_in: Dict[str, Any]) -> T:
        """Update record.
        
        Args:
            db_obj: Database object
            obj_in: Update data dictionary
            
        Returns:
            Updated model instance
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            # Update fields
            for field, value in obj_in.items():
                if hasattr(db_obj, field):
                    setattr(db_obj, field, value)
            
            self.db.commit()
            self.db.refresh(db_obj)
            return db_obj
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to update database record: {type(e).__name__}")
            raise
    
    def delete(self, id: int) -> bool:
        """Delete record.
        
        Args:
            id: Record ID
            
        Returns:
            Whether deletion was successful
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            db_obj = self.get_by_id(id)
            if db_obj:
                self.db.delete(db_obj)
                self.db.commit()
                return True
            return False
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to delete database record: {type(e).__name__}")
            raise
    
    def delete_by_filter(self, **filters) -> int:
        """Batch delete records by filter conditions.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            Number of deleted records
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            query = self.db.query(self.model_class)
            
            # Apply filter conditions
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) == value)
            
            deleted_count = query.delete(synchronize_session=False)
            self.db.commit()
            return deleted_count
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to batch delete database records: {str(e)}")
            raise
    
    def count(self, **filters) -> int:
        """Count records.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            Total number of records
        """
        try:
            query = self.db.query(self.model_class)
            
            # Apply filter conditions
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) == value)
            
            return query.count()
        except SQLAlchemyError as e:
            logger.error(f"Failed to count database records: {type(e).__name__}")
            raise
    
    def exists(self, **filters) -> bool:
        """Check if record exists.
        
        Args:
            **filters: Filter conditions
            
        Returns:
            Whether record exists
        """
        try:
            query = self.db.query(self.model_class)
            
            # Apply filter conditions
            for field, value in filters.items():
                if hasattr(self.model_class, field):
                    query = query.filter(getattr(self.model_class, field) == value)
            
            return query.first() is not None
        except SQLAlchemyError as e:
            logger.error(f"Failed to check record existence: {type(e).__name__}")
            raise
    
    def query(self) -> Query:
        """Get query builder.
        
        Returns:
            SQLAlchemy query object
        """
        return self.db.query(self.model_class)
    
    def filter_by(self, **kwargs) -> Query:
        """Filter by conditions.
        
        Args:
            **kwargs: Filter conditions
            
        Returns:
            Filtered query object
        """
        return self.query().filter_by(**kwargs)
    
    def order_by(self, *args) -> Query:
        """Order by fields.
        
        Args:
            *args: Order by fields
            
        Returns:
            Ordered query object
        """
        return self.query().order_by(*args)
    
    def get_or_create(self, defaults: Optional[Dict[str, Any]] = None, **kwargs) -> tuple[T, bool]:
        """Get or create record.
        
        Args:
            defaults: Default values for creation
            **kwargs: Query conditions
            
        Returns:
            (Model instance, whether newly created)
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            instance = self.filter_by(**kwargs).first()
            if instance:
                return instance, False
            else:
                params = dict(kwargs)
                if defaults:
                    params.update(defaults)
                instance = self.create(params)
                return instance, True
        except SQLAlchemyError as e:
            logger.error(f"Failed to get or create record: {type(e).__name__}")
            raise
    
    def bulk_create(self, objects: List[Dict[str, Any]]) -> List[T]:
        """Bulk create records.
        
        Args:
            objects: List of creation data
            
        Returns:
            List of created model instances
            
        Raises:
            SQLAlchemyError: Database operation exception
        """
        try:
            db_objects = [self.model_class(**obj) for obj in objects]
            self.db.add_all(db_objects)
            self.db.commit()
            
            # Refresh all objects to get auto-generated fields like ID
            for obj in db_objects:
                self.db.refresh(obj)
            
            return db_objects
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Failed to create database records in bulk: {type(e).__name__}")
            raise