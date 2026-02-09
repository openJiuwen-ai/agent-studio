from typing import List, Optional

from openjiuwen.core.common.logging import logger
from sqlalchemy import or_
from sqlalchemy.orm import Session

from openjiuwen_studio.core.manager.repositories import BaseRepository
from openjiuwen_studio.models.embedding_model_config import EmbeddingModelConfig
from openjiuwen_studio.models.knowledge_base import KnowledgeBaseDB
from openjiuwen_studio.schemas.embedding_model_config import EmbeddingProtocol


class EmbeddingModelConfigRepository(BaseRepository[EmbeddingModelConfig]):
    """Embedding 模型配置数据访问层"""

    def __init__(self, db: Session):
        super().__init__(db, EmbeddingModelConfig)

    def get_by_name(self, model_name: str, space_id: str) -> Optional[EmbeddingModelConfig]:
        """根据名称和空间ID获取配置"""
        return self.query().filter(
            EmbeddingModelConfig.model_name == model_name,
            EmbeddingModelConfig.space_id == space_id
        ).first()

    def get_active_models(self, space_id: str) -> List[EmbeddingModelConfig]:
        """获取所有激活的配置"""
        return self.query().filter(
            EmbeddingModelConfig.space_id == space_id,
            EmbeddingModelConfig.is_active
        ).all()

    def get_by_space_id_and_system_model_id(self, space_id: str, system_model_id: int) -> Optional[
        EmbeddingModelConfig]:
        """Get model config by space_id and system_model_id.

        Args:
            space_id: user space id
            system_model_id: related system model id

        Returns:
            Embedding model config instance or None
        """
        return self.query().filter(EmbeddingModelConfig.space_id == space_id,
                                   EmbeddingModelConfig.system_model_id == system_model_id).first()

    def get_paginated(
            self,
            space_id: str,
            page: int = 1,
            size: int = 10,
            protocol: Optional[EmbeddingProtocol] = None,
            is_active: Optional[bool] = None,
            search: Optional[str] = None,
            sort_by: Optional[str] = 'updated_at',
            sort_order: Optional[str] = 'desc'
    ) -> tuple[List[EmbeddingModelConfig], int]:
        """分页查询配置"""
        query = self.query().filter(EmbeddingModelConfig.space_id == space_id)

        if protocol:
            query = query.filter(EmbeddingModelConfig.protocol == protocol.value)

        if is_active is not None:
            query = query.filter(EmbeddingModelConfig.is_active == is_active)

        if search:
            search_filter = or_(
                EmbeddingModelConfig.model_name.ilike(f"%{search}%"),
                EmbeddingModelConfig.model_id.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        # 排序
        if sort_by == 'created_at':
            order_column = EmbeddingModelConfig.created_at
        elif sort_by == 'model_name':
            order_column = EmbeddingModelConfig.model_name
        else:
            order_column = EmbeddingModelConfig.updated_at

        if sort_order == 'desc':
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

        # 总数
        total = query.count()

        # 分页
        offset = (page - 1) * size
        models = query.offset(offset).limit(size).all()

        return models, total

    def check_name_exists(
            self,
            space_id: str,
            model_name: str,
            exclude_id: Optional[int] = None
    ) -> bool:
        """检查名称是否已存在"""
        query = self.query().filter(
            EmbeddingModelConfig.space_id == space_id,
            EmbeddingModelConfig.model_name == model_name
        )

        if exclude_id:
            query = query.filter(EmbeddingModelConfig.id != exclude_id)

        return query.first() is not None

    def toggle_status(self, config_id: int) -> Optional[EmbeddingModelConfig]:
        """切换激活状态"""
        model = self.get_by_id(config_id)
        if model:
            model.is_active = not model.is_active
            try:
                self.db.commit()
                self.db.refresh(model)
            except Exception as e:
                logger.error(f"Failed to toggle status for embedding model {config_id}: {e}")
                self.db.rollback()
                raise
        return model

    def check_knowledge_bases_using_model(self, config_id: int) -> List[dict]:
        """检查是否有知识库使用该 embedding 模型配置
        
        Args:
            config_id: Embedding 模型配置ID
            
        Returns:
            使用该模型的知识库列表，每个元素包含 kb_id, space_id, name
        """
        knowledge_bases = self.db.query(KnowledgeBaseDB).filter(
            KnowledgeBaseDB.embedding_model_config_id == config_id
        ).all()

        return [
            {
                "kb_id": kb.kb_id,
                "space_id": kb.space_id,
                "name": kb.name
            }
            for kb in knowledge_bases
        ]
