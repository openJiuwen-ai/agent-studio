from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import ModelConfigRepository, ModelUsageRepository
from openjiuwen_studio.models.model_config import ModelConfig
from openjiuwen_studio.schemas.model_config import (
    ModelConfigCreate,
    ModelConfigUpdate,
    ModelConfigResponse,
    ModelProvider
)
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.exceptions import (
    ModelConfigNotFoundError,
    ModelConfigNameExistsError,
    ValidationError
)


class ModelConfigManager:
    """Manages model configuration operations including CRUD and validation."""
    
    def __init__(self, db: Session):
        """Initialize model configuration manager.
        
        Args:
            db: Database session
        """
        self.db = db
        self.model_repo = ModelConfigRepository(db)
        self.usage_repo = ModelUsageRepository(db)
        self.security_utils = SecurityUtils()
    
    def get_config_by_id(self, model_id: int, space_id: str) -> ModelConfig:
        """Get model configuration by ID (returns raw model object).
        
        Args:
            model_id: Model ID
            space_id: Space ID
            
        Returns:
            Model configuration object
            
        Raises:
            ModelConfigNotFoundError: Model config not found
        """
        if not self.model_repo.check_name_exists(space_id=space_id, config_id=model_id):
            raise ModelConfigNotFoundError(f"Space {space_id} not include Model config: {model_id}")

        model = self.model_repo.get_by_id(model_id)
        if not model:
            raise ModelConfigNotFoundError(f"Model config not found: {model_id}")
        
        return model
    
    def update_config(self, model_id: int, space_id: str, model_data: 'ModelConfigUpdate') -> ModelConfig:
        """Update model configuration (alias method).
        
        Args:
            model_id: Model ID
            space_id: Space ID
            model_data: Model configuration update data
            
        Returns:
            Updated model configuration object
        """
        if not self.model_repo.check_name_exists(space_id=space_id, config_id=model_id):
            raise ModelConfigNotFoundError("Space not include Model config")
        # Call update_model_config and return raw model object
        self.update_model_config(model_id, model_data, space_id)  # Pass space_id correctly
        # Re-fetch model object
        return self.model_repo.get_by_id(model_id)
    
    def create_config(self, model_config: 'ModelConfigCreate') -> ModelConfig:
        """Create model configuration (alias method).
        
        Args:
            model_config: Model configuration creation data
            
        Returns:
            Created model configuration object
        """
        # Call create_model_config and return raw model object instead of response
        response = self.create_model_config(model_config)
        logger.info(response)
        # Need to re-fetch model object from database
        return self.model_repo.get_by_name(model_config.name)
    
    def delete_config(self, model_id: int, space_id: str) -> int:
        """Delete model configuration (alias method).
        
        Args:
            model_id: Model ID

            
        Returns:
            Number of deleted usage records
        """
        try:
            # Check if model configuration exists
            model = self.get_config_by_id(model_id, space_id)
            if not model:
                raise ModelConfigNotFoundError(f"Model config not found: {model_id}")
            
            # Delete related usage records
            deleted_logs = self.usage_repo.delete_by_model_id(model_id)
            
            # Delete model configuration
            success = self.model_repo.delete(model_id)
            
            if success:
                logger.info(
                    f"Deleted model config: {model.name} (ID: {model_id}), also deleted {deleted_logs} usage records")
                return deleted_logs
            
            return 0
            
        except ModelConfigNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to delete model config: {str(e)}") from e
    
    def create_model_config(
        self,
        model_data: ModelConfigCreate,
    ) -> ModelConfigResponse:
        """Create model configuration.
        
        Args:
            model_data: Model configuration creation data
            
        Returns:
            Created model configuration response
            
        Raises:
            ModelConfigNameExistsError: Model config name already exists
            ValidationError: Data validation failed
        """
        try:
            # Check if name already exists
            if self.model_repo.check_name_exists(model_data.space_id, model_data.name):
                raise ModelConfigNameExistsError(f"Model config name already exists: {model_data.name}")
            
            # Encrypt API key
            encrypted_api_key = self.security_utils.encrypt_api_key(model_data.api_key) if model_data.api_key else None
            
            # Create model configuration
            model_dict = model_data.dict(exclude={'api_key'})
            model_dict.update({
                'api_key': encrypted_api_key
            })
            
            model = self.model_repo.create(model_dict)
            
            logger.info(f"Created model config: {model.name} (ID: {model.id})")
            return ModelConfigManager._model_to_response(model)
            
        except (ModelConfigNameExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to create model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create model config: {str(e)}") from e
    
    def update_model_config(
        self,
        model_id: int,
        model_data: ModelConfigUpdate,
        space_id: str
    ) -> ModelConfigResponse:
        """Update model configuration.
        
        Args:
            model_id: Model ID
            model_data: Model configuration update data
            space_id: Updater space ID
            
        Returns:
            Updated model configuration response
            
        Raises:
            ModelConfigNotFoundError: Model config not found
            ModelConfigNameExistsError: Model config name already exists
            ValidationError: Data validation failed
        """
        try:
            # Get existing model configuration
            model = self.model_repo.get_by_id(model_id)
            if not model:
                raise ModelConfigNotFoundError(f"Model config not found: {model_id}")
            
            # Check name conflict (if name has changed)
            if model_data.name and model_data.name != model.name:
                if self.model_repo.check_name_exists(space_id, model_data.name, exclude_id=model_id):
                    raise ModelConfigNameExistsError(f"Model config name already exists: {model_data.name}")
            
            # Prepare update data
            update_dict = model_data.dict(exclude_unset=True)
            # Only update api_key if it has a value, prevent clearing existing api_key with None
            if 'api_key' in update_dict:
                if update_dict['api_key'] is None:
                    # Remove None api_key to preserve existing value
                    del update_dict['api_key']
                else:
                    # Encrypt api_key before updating
                    update_dict['api_key'] = self.security_utils.encrypt_api_key(update_dict['api_key'])
            update_dict['updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # Get existing model configuration
            existing_model = self.model_repo.get_by_id(model_id)
            if not existing_model:
                raise ModelConfigNotFoundError(f"Model config not found: {model_id}")
            
            # Update model configuration
            updated_model = self.model_repo.update(existing_model, update_dict)
            
            logger.info(f"Updated model config: {updated_model.name} (ID: {model_id})")
            return ModelConfigManager._model_to_response(updated_model)
            
        except (ModelConfigNotFoundError, ModelConfigNameExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update model config: {str(e)}") from e
    
    def toggle_model_status(self, model_id: int, user_id: int) -> ModelConfigResponse:
        """Toggle model activation status.
        
        Args:
            model_id: Model ID
            user_id: Operator user ID
            
        Returns:
            Updated model configuration response
            
        Raises:
            ModelConfigNotFoundError: Model config not found
        """
        try:
            model = self.model_repo.toggle_status(model_id)
            if not model:
                raise ModelConfigNotFoundError(f"Model config not found: {model_id}")
            
            status_text = "activated" if model.is_active else "deactivated"
            logger.info(f"Toggled model status: {model.name} (ID: {model_id}) -> {status_text}")
            
            return ModelConfigManager._model_to_response(model)
            
        except ModelConfigNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to toggle model status: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to toggle model status: {str(e)}") from e
    
    @staticmethod
    def get_parameter_definitions() -> List[Dict[str, Any]]:
        """Get parameter definitions list.
        
        Returns:
            Parameter definitions list
        """
        # Return predefined parameter definitions
        # In actual projects, these might be loaded from config files or database
        return [
            {
                "name": "temperature",
                "type": "float",
                "description": "Controls output randomness, higher values make output more random",
                "default_value": 0.7,
                "min_value": 0.0,
                "max_value": 2.0
            },
            {
                "name": "max_tokens",
                "type": "integer",
                "description": "Maximum number of tokens to generate",
                "default_value": 1000,
                "min_value": 1,
                "max_value": 4000
            },
            {
                "name": "top_p",
                "type": "float",
                "description": "Nucleus sampling parameter, controls output diversity",
                "default_value": 1.0,
                "min_value": 0.0,
                "max_value": 1.0
            },
            {
                "name": "frequency_penalty",
                "type": "float",
                "description": "Frequency penalty, reduces repetitive content",
                "default_value": 0.0,
                "min_value": -2.0,
                "max_value": 2.0
            },
            {
                "name": "presence_penalty",
                "type": "float",
                "description": "Presence penalty, encourages talking about new topics",
                "default_value": 0.0,
                "min_value": -2.0,
                "max_value": 2.0
            }
        ]
    
    def get_configs_by_ids(self, model_ids: List[int]) -> List[ModelConfig]:
        """Batch get model configurations by IDs.
        
        Args:
            model_ids: List of Model IDs
            
        Returns:
            List of Model configuration objects
        """
        if not model_ids:
            return []
            
        try:
            return self.model_repo.get_by_ids(model_ids)
        except Exception as e:
            logger.error(f"Failed to batch get model configs: {str(e)}")
            raise ValidationError(f"Failed to batch get model configs: {str(e)}") from e

    def get_paginated_configs(
        self,
        page: int = 1,
        size: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: Optional[str] = 'update_time',
        sort_order: Optional[str] = 'desc'
    ) -> tuple[List[ModelConfig], int]:
        """Get paginated model configurations
        
        Args:
            page: Page number
            size: Page size
            filters: Filter conditions dictionary
            
        Returns:
            (Model configuration list, total count)
        """
        try:
            # Parse filter conditions
            provider = None
            is_active = None
            search = None
            tags = None
            space_id = None
            
            if filters:
                provider_str = filters.get('provider')
                if provider_str:
                    try:
                        provider = ModelProvider(provider_str)
                    except ValueError:
                        logger.warning(f"Invalid provider type: {provider_str}")
                        
                is_active = filters.get('is_active')
                search = filters.get('search')
                tags = filters.get('tags')
                space_id = filters.get('space_id')
                id = filters.get('id')
            
            # Call repository layer method
            models, total = self.model_repo.get_paginated(
                space_id=space_id,
                page=page,
                size=size,
                id=id,
                provider=provider,
                is_active=is_active,
                search=search,
                tags=tags,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Paginated model config query successful: page={page}, size={size}, total={total}")
            return models, total
            
        except Exception as e:
            logger.error(f"Paginated model config query failed: {str(e)}")
            raise ValidationError(f"Paginated model config query failed: {str(e)}") from e
    
    @staticmethod
    def _model_to_response(model: ModelConfig) -> ModelConfigResponse:
        """Convert model configuration to response format
        
        Args:
            model: Model configuration instance
            
        Returns:
            Model configuration response
        """
        # Handle API key masking
        masked_api_key = None
        if hasattr(model, 'api_key') and model.api_key:
            # Simple masking, show first 4 and last 4 characters
            if len(model.api_key) > 8:
                masked_api_key = model.api_key[:4] + "*" * (len(model.api_key) - 8) + model.api_key[-4:]
            else:
                masked_api_key = "*" * len(model.api_key)
        
        return ModelConfigResponse(
            id=model.id,
            name=model.name,
            space_id=model.space_id,
            provider=model.provider,
            model_type=model.model_type,
            description=model.description,
            is_active=model.is_active,
            base_url=model.base_url,
            parameters=model.parameters or {},
            tags=model.tags or [],
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_used=model.last_used,
            total_requests=model.total_requests,
            total_tokens=model.total_tokens,
            total_cost=model.total_cost,
            success_rate=model.success_rate,
            avg_response_time=model.avg_response_time,
            api_key_masked=masked_api_key,
            is_system_model=model.is_system_model,
            system_model_id=model.system_model_id
        )
    
    def _validate_parameters(self, parameters: Dict[str, Any], model_type: str) -> None:
        """Validate model parameters
        
        Args:
            parameters: Parameters dictionary
            model_type: Model type
            
        Raises:
            ValidationError: Parameter validation failed
        """
        # Get parameter definitions
        param_definitions = {param.name: param for param in ModelConfigManager.get_parameter_definitions()}
        
        # Validate each parameter
        for param_name, param_value in parameters.items():
            if param_name not in param_definitions:
                continue  # Allow undefined parameters
            
            param_def = param_definitions[param_name]
            
            # Type validation
            if param_def.type == "float" and not isinstance(param_value, (int, float)):
                raise ValidationError(f"Parameter {param_name} must be numeric type")
            elif param_def.type == "integer" and not isinstance(param_value, int):
                raise ValidationError(f"Parameter {param_name} must be integer type")
            elif param_def.type == "string" and not isinstance(param_value, str):
                raise ValidationError(f"Parameter {param_name} must be string type")
            
            # Range validation
            if param_def.min_value is not None and param_value < param_def.min_value:
                raise ValidationError(f"Parameter {param_name} cannot be less than {param_def.min_value}")
            if param_def.max_value is not None and param_value > param_def.max_value:
                raise ValidationError(f"Parameter {param_name} cannot be greater than {param_def.max_value}")