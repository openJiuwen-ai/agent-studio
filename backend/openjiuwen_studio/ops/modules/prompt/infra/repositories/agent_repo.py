#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.


from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from openjiuwen_studio.ops.modules.prompt.domain.repositories import AgentRepository
from openjiuwen_studio.ops.modules.prompt.infra.database import BaseAgent


class SQLAgentRepository(AgentRepository):
    def __init__(self, db: Session):
        self.db = db

    def find_by_id(self, prompt_id: int, prompt_version: str, agentmodel: BaseAgent) -> Optional[List[BaseAgent]]:
        query = self.db.query(agentmodel).filter(agentmodel.prompt_id == str(prompt_id),
                                                 agentmodel.is_active.is_(True))
        if prompt_version:
            query = query.filter(agentmodel.prompt_version == prompt_version)
        result = query.all()
        return result

    def find_user_name_by_id(self, user_id: str, agentmodel: BaseAgent) -> Optional[BaseAgent]:
        query = self.db.query(agentmodel).filter(agentmodel.user_id == user_id)
        result = query.first()
        return result

    def find_model_config_by_modelid(self, model_id: int, agentmodel: BaseAgent) \
            -> Optional[BaseAgent]:
        query = self.db.query(agentmodel).filter(agentmodel.id == model_id, agentmodel.is_active)
        result = query.first()
        return result

    def find_model_config_by_spaceid(self, space_id: str,
                                     agentmodel: BaseAgent,
                                     is_active: bool = True,
                                     page_num: int = 1,
                                     page_size: int = 100) -> Optional[List[BaseAgent]]:

        query = self.db.query(agentmodel).filter(agentmodel.space_id == space_id, agentmodel.is_active == is_active)

        # 计算偏移量（offset）
        offset = (page_num - 1) * page_size
        result = query.offset(offset).limit(page_size).all()
        return result


    def update_field_by_prompt_id(self, prompt_id: int, field_updates: Dict[str, Any], agentmodel: BaseAgent,
                     prompt_version: str = None) -> int:
        """
        更新prompt_id记录的特定字段
        """
        # 构建基础查询条件
        query = self.db.query(agentmodel).filter(agentmodel.prompt_id == str(prompt_id))

        # 如果指定了版本号，只更新该版本
        if prompt_version:
            query = query.filter(agentmodel.prompt_version == prompt_version)

        result = query.update(field_updates)
        self.db.commit()
        return result
