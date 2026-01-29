from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.models.embedding_model_config import EmbeddingModelConfig
from openjiuwen_studio.schemas.embedding_model_config import (
    EmbeddingModelConfigCreate,
    EmbeddingModelConfigUpdate,
    EmbeddingModelConfigResponse,
    EmbeddingProtocol
)
from openjiuwen_studio.core.manager.model_manager.utils import SecurityUtils
from openjiuwen_studio.core.exceptions import (
    ModelConfigNotFoundError,
    ModelConfigNameExistsError,
    ValidationError,
    EmbeddingModelInUseError
)


class EmbeddingModelConfigManager:
    """Embedding 模型配置管理器 - 简化版，借鉴LLM管理但不需要统计功能"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmbeddingModelConfigRepository(db)
        self.security_utils = SecurityUtils()
    
    def get_paginated_configs(
        self,
        space_id: str,
        page: int = 1,
        size: int = 10,
        protocol: Optional[EmbeddingProtocol] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        sort_by: Optional[str] = 'updated_at',
        sort_order: Optional[str] = 'desc'
    ) -> Tuple[List[EmbeddingModelConfig], int]:
        """分页获取配置列表"""
        try:
            models, total = self.repo.get_paginated(
                space_id=space_id,
                page=page,
                size=size,
                protocol=protocol,
                is_active=is_active,
                search=search,
                sort_by=sort_by,
                sort_order=sort_order
            )
            logger.info(f"Retrieved embedding model configs: page={page}, size={size}, total={total}")
            return models, total
        except Exception as e:
            logger.error(f"Failed to get embedding model configs: {str(e)}")
            raise ValidationError(f"Failed to get embedding model configs: {str(e)}") from e
    
    def get_config_by_id(self, config_id: int, space_id: str) -> EmbeddingModelConfig:
        """根据ID获取配置"""
        model = self.repo.get_by_id(config_id)
        if not model:
            raise ModelConfigNotFoundError(f"Embedding model config not found: {config_id}")
        
        if model.space_id != space_id:
            raise ModelConfigNotFoundError(f"Embedding model config not found in space: {space_id}")
        
        return model
    
    def create_config(self, config_data: EmbeddingModelConfigCreate) -> EmbeddingModelConfig:
        """创建配置"""
        try:
            # 检查名称是否已存在
            if self.repo.check_name_exists(config_data.space_id, config_data.model_name):
                raise ModelConfigNameExistsError(
                    f"Embedding model config name already exists: {config_data.model_name}"
                )
            
            # 加密API密钥
            encrypted_api_key = None
            if config_data.api_key:
                encrypted_api_key = self.security_utils.encrypt_api_key(config_data.api_key)
            
            # 创建配置
            config_dict = config_data.dict(exclude={'api_key'})
            config_dict['api_key'] = encrypted_api_key
            
            model = self.repo.create(config_dict)
            
            logger.info(f"Created embedding model config: {model.model_name} (ID: {model.id})")
            return model
            
        except (ModelConfigNameExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to create embedding model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to create embedding model config: {str(e)}") from e
    
    def update_config(
        self,
        config_id: int,
        space_id: str,
        config_data: EmbeddingModelConfigUpdate
    ) -> EmbeddingModelConfig:
        """更新配置"""
        try:
            # 获取现有配置
            model = self.get_config_by_id(config_id, space_id)
            
            # 检查名称冲突
            if config_data.model_name and config_data.model_name != model.model_name:
                if self.repo.check_name_exists(space_id, config_data.model_name, exclude_id=config_id):
                    raise ModelConfigNameExistsError(
                        f"Embedding model config name already exists: {config_data.model_name}"
                    )
            
            # 准备更新数据
            update_dict = config_data.dict(exclude_unset=True, exclude={'api_key'})
            update_dict['updated_at'] = datetime.now(timezone.utc).replace(tzinfo=None)
            
            # 处理API密钥加密
            if config_data.api_key is not None:
                if config_data.api_key:
                    update_dict['api_key'] = self.security_utils.encrypt_api_key(config_data.api_key)
                else:
                    update_dict['api_key'] = None
            
            # 更新配置
            updated_model = self.repo.update(model, update_dict)
            
            logger.info(f"Updated embedding model config: {updated_model.model_name} (ID: {config_id})")
            return updated_model
            
        except (ModelConfigNotFoundError, ModelConfigNameExistsError, ValidationError):
            raise
        except Exception as e:
            logger.error(f"Failed to update embedding model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to update embedding model config: {str(e)}") from e
    
    def delete_config(self, config_id: int, space_id: str) -> bool:
        """删除配置
        
        Raises:
            EmbeddingModelInUseError: 如果有知识库正在使用该模型配置
        """
        try:
            model = self.get_config_by_id(config_id, space_id)
            
            # 检查是否有知识库使用该模型配置
            knowledge_bases = self.repo.check_knowledge_bases_using_model(config_id)
            if knowledge_bases:
                kb_names = [kb["name"] for kb in knowledge_bases]
                kb_count = len(knowledge_bases)
                error_message = (
                    f"Cannot delete embedding model config '{model.model_name}' (ID: {config_id}) "
                    f"because it is being used by {kb_count} knowledge base(s): {', '.join(kb_names)}"
                )
                logger.warning(error_message)
                raise EmbeddingModelInUseError(error_message)
            
            success = self.repo.delete(config_id)
            
            if success:
                logger.info(f"Deleted embedding model config: {model.model_name} (ID: {config_id})")
            
            return success
            
        except (ModelConfigNotFoundError, EmbeddingModelInUseError):
            raise
        except Exception as e:
            logger.error(f"Failed to delete embedding model config: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to delete embedding model config: {str(e)}") from e
    
    def toggle_status(self, config_id: int, space_id: str) -> EmbeddingModelConfig:
        """切换激活状态"""
        try:
            model = self.get_config_by_id(config_id, space_id)
            updated_model = self.repo.toggle_status(config_id)
            
            if updated_model:
                status_text = "activated" if updated_model.is_active else "deactivated"
                logger.info(
                    f"Toggled embedding model status: {updated_model.model_name} (ID: {config_id}) -> {status_text}"
                )
            
            return updated_model
            
        except ModelConfigNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to toggle embedding model status: {str(e)}")
            self.db.rollback()
            raise ValidationError(f"Failed to toggle embedding model status: {str(e)}") from e
    
    def _model_to_response(self, model: EmbeddingModelConfig) -> EmbeddingModelConfigResponse:
        """转换为响应格式"""
        # 处理API密钥脱敏
        masked_api_key = None
        if model.api_key:
            try:
                decrypted_key = self.security_utils.decrypt_api_key(model.api_key)
                masked_api_key = self.security_utils.mask_api_key(decrypted_key)
            except Exception:
                masked_api_key = "***invalid***"
        
        return EmbeddingModelConfigResponse(
            id=model.id,
            model_name=model.model_name,
            space_id=model.space_id,
            protocol=EmbeddingProtocol(model.protocol),
            model_id=model.model_id,
            api_base=model.api_base,
            max_batch_size=model.max_batch_size,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            api_key_masked=masked_api_key,
            is_system_model=model.is_system_model,
            system_model_id=model.system_model_id
        )

