#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from pathlib import Path
from typing import List, Optional, Any, Tuple, Union
import yaml
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, case

from openjiuwen_studio.ops.common.date_time_util import get_china_datetime
from openjiuwen_studio.ops.modules.prompt.domain import entities
from openjiuwen_studio.ops.modules.prompt.domain.repositories import PromptRepository, PromptVersionRepository, \
    PromptUserDraftRepository, PromptSubmitRepository
from openjiuwen_studio.ops.modules.prompt.infra.database import Base
from openjiuwen_studio.ops.modules.prompt.infra.repositories import orm_repo


class SQLPromptRepository(PromptRepository):
    def __init__(self, db: Session):
        self.db = db

    def save(self, db_prompt: Base) -> int:
        if not db_prompt.updated_at:
            db_prompt.created_at = get_china_datetime()
            db_prompt.updated_at = get_china_datetime()
        self.db.add(db_prompt)
        self.db.commit()
        self.db.refresh(db_prompt)
        return db_prompt.id

    def update(self, new_prompt: Base) -> None:
        if new_prompt:
            new_prompt.updated_at = get_china_datetime()
        self.db.commit()
        self.db.refresh(new_prompt)

    def find_by_id(self, prompt_id: int, promptmodel: Base) -> Optional[Base]:
        db_prompt = self.db.query(promptmodel).filter(
            promptmodel.id == prompt_id,
            promptmodel.deleted_at.is_(None)
        ).first()
        return db_prompt if db_prompt else None

    def find_by_prompt_id(self, prompt_id: int, promptmodel: Base) -> Optional[Base]:
        db_prompt = self.db.query(promptmodel).filter(
            promptmodel.prompt_id == prompt_id,
            promptmodel.deleted_at == 0
        ).first()
        return db_prompt if db_prompt else None

    def find_by_name(self, name: str, promptmodel: Base) -> Optional[entities.Prompt]:
        db_prompt = self.db.query(promptmodel).filter(
            promptmodel.name == name,
            promptmodel.deleted_at.is_(None)
        ).first()
        return db_prompt if db_prompt else None

    def trans_promptbasic_to_userinfo(self, db_prompts: Base):
        """trans promptbasic to userinfo"""
        user_info = self.db.query(orm_repo.UserModel).filter(
            or_(
                orm_repo.UserModel.id == db_prompts.created_by,
                orm_repo.UserModel.id == db_prompts.updated_by
            )
        ).all()
        if user_info:
            return entities.UserInfoDetail(
                user_id=db_prompts.created_by,
                name=user_info.name,
                nick_name=user_info.name,
                avatar_url=user_info.icon_uri,
                email=user_info.email,
                mobile=user_info.mobile
            )
        return entities.UserInfoDetail(
            user_id=db_prompts.created_by,
        )

    def get_all(self, conditions: list, promptmodel: Base) -> Base:
        prompts = self.db.query(promptmodel).filter(
            and_(*conditions)
        ).all()
        return prompts

    def get_default_model_config(self) -> Optional[entities.PromptDetail]:
        model_config_path = Path(__file__).parent.parent.parent.parent.parent / "conf" / "default_model_config.yaml"
        with open(model_config_path, "r", encoding="utf-8") as f:
            default_model_config = yaml.safe_load(f)
        return entities.PromptDetail(**default_model_config)

    def list_all(self, page_num: int, page_size: int, conditions: list, order_by: Optional[Union[Any, List[Any]]],
                 promptmodel: Base) -> Tuple[List[Base], List[Base]]:
        skip = (page_num - 1) * page_size
        query = self.db.query(promptmodel).filter(and_(*conditions))
        if order_by is not None:
            query = query.order_by(order_by)
        prompts_basic = query.offset(skip).limit(page_size).all()
        all_basic = self.db.query(promptmodel).filter(and_(*conditions)).all()
        return prompts_basic, all_basic

    def list_all_order_by_max_updated_at(
        self,
        page_num: int,
        page_size: int,
        conditions: list,
        asc: bool,
    ) -> Tuple[List[Base], List[Base]]:
        """
        按 max(prompt_basic.updated_at, prompt_user_draft.updated_at) 排序分页查询。
        使用左连接 draft 子查询（按 prompt_id 取 max(updated_at)），排序键为两者较大值。
        """
        Basic = orm_repo.PromptBasicModel
        Draft = orm_repo.PromptUserDraftModel
        draft_subq = (
            self.db.query(
                Draft.prompt_id,
                func.max(Draft.updated_at).label("max_draft_updated_at"),
            )
            .filter(Draft.deleted_at == 0)
            .group_by(Draft.prompt_id)
            .subquery()
        )
        # 排序键: max(basic.updated_at, coalesce(draft.max_updated_at, basic.updated_at))
        order_col = case(
            (
                Basic.updated_at >= func.coalesce(draft_subq.c.max_draft_updated_at, Basic.updated_at),
                Basic.updated_at,
            ),
            else_=func.coalesce(draft_subq.c.max_draft_updated_at, Basic.updated_at),
        )
        order_by_clause = order_col.asc() if asc else order_col.desc()
        skip = (page_num - 1) * page_size
        query = (
            self.db.query(Basic)
            .outerjoin(draft_subq, Basic.id == draft_subq.c.prompt_id)
            .filter(and_(*conditions))
            .order_by(order_by_clause)
        )
        prompts_basic = query.offset(skip).limit(page_size).all()
        all_basic = (
            self.db.query(Basic)
            .outerjoin(draft_subq, Basic.id == draft_subq.c.prompt_id)
            .filter(and_(*conditions))
            .order_by(order_by_clause)
            .all()
        )
        return prompts_basic, all_basic

    def delete(self, prompt_id: int, promptmodel: Base) -> None:
        db_prompt = self.db.query(promptmodel).filter(promptmodel.id == prompt_id).first()
        if db_prompt:
            if isinstance(db_prompt, orm_repo.PromptBasicModel):
                db_prompt.updated_at = get_china_datetime()
                db_prompt.deleted_at = get_china_datetime()
            else:
                db_prompt.is_deleted = True
            self.db.commit()
            self.db.refresh(db_prompt)

    def find_commit_by_id_version(self, prompt_id: int, version: str, promptmodel: Base) -> Optional[Base]:
        """获取prompt从提交表"""
        commit_prompt = self.db.query(orm_repo.PromptCommitModel).filter(
            orm_repo.PromptCommitModel.prompt_id == prompt_id,
            orm_repo.PromptCommitModel.version == version
        ).first()
        return commit_prompt if commit_prompt else None

    def find_draft_by_id(self, prompt_id: int, promptmodel: Base) -> Optional[Base]:
        """获取prompt从草稿表"""

        prompt_draft = self.db.query(promptmodel).filter(
            orm_repo.PromptUserDraftModel.prompt_id == prompt_id
        ).first()
        return prompt_draft if prompt_draft else None


class SQLPromptVersionRepository(PromptVersionRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_version(self, version: entities.PromptVersionBase) -> entities.PromptVersion:
        db_version = orm_repo.PromptVersionModel(
            prompt_id=version.prompt_id,
            name=version.name,
            version=version.version,
            content=version.content,
            description=version.description,
            created_by=version.created_by,
            is_current=True
        )

        self.db.add(db_version)
        self.db.commit()
        self.db.refresh(db_version)
        return entities.PromptVersion.model_validate(db_version)

    def find_versions_by_prompt(self, prompt_id: int) -> List[entities.PromptVersion]:
        db_versions = self.db.query(orm_repo.PromptVersionModel).filter(
            orm_repo.PromptVersionModel.prompt_id == prompt_id
        ).order_by(orm_repo.PromptVersionModel.version.desc()).all()
        return [entities.PromptVersion.model_validate(v) for v in db_versions]

    def find_version(self, prompt_id: int, version: int) -> Optional[entities.PromptVersion]:
        db_version = self.db.query(orm_repo.PromptVersionModel).filter(
            orm_repo.PromptVersionModel.prompt_id == prompt_id,
            orm_repo.PromptVersionModel.version == version
        ).first()
        return entities.PromptVersion.model_validate(db_version) if db_version else None

    def set_current_version(self, prompt_id: int, version: int) -> None:
        # 重置所有版本为非当前
        self.db.query(orm_repo.PromptVersionModel).filter(
            orm_repo.PromptVersionModel.prompt_id == prompt_id
        ).update({"is_current": False})

        # 设置指定版本为当前
        self.db.query(orm_repo.PromptVersionModel).filter(
            orm_repo.PromptVersionModel.prompt_id == prompt_id,
            orm_repo.PromptVersionModel.version == version
        ).update({"is_current": True})

        self.db.commit()


class SQLPromptUserDraftRepository(PromptUserDraftRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_draft(
            self,
            draft_po: entities.DraftPO
    ) -> entities.DraftInfoOutput:
        # 尝试查找现有草稿
        existing_draft = self.db.query(orm_repo.PromptUserDraftModel).filter(
            orm_repo.PromptUserDraftModel.prompt_id == draft_po.prompt_id,
            orm_repo.PromptUserDraftModel.user_id == draft_po.user_id,
            orm_repo.PromptUserDraftModel.deleted_at == 0
        ).first()

        cur_datetime = get_china_datetime()

        if existing_draft:
            # 更新现有草稿
            existing_draft.template_type = draft_po.template_type
            existing_draft.messages = draft_po.messages
            existing_draft.prompt_model_config = draft_po.prompt_model_config
            existing_draft.variable_defs = draft_po.variable_defs
            existing_draft.tools = draft_po.tools
            existing_draft.tool_call_config = draft_po.tool_call_config
            existing_draft.base_version = draft_po.base_version
            existing_draft.is_draft_edited = draft_po.is_draft_edited
            existing_draft.updated_at = cur_datetime

            self.db.commit()
            self.db.refresh(existing_draft)
            return entities.DraftInfoOutput(
                base_version=existing_draft.base_version,
                created_at=str(int(existing_draft.created_at.timestamp())),
                is_draft_edited=True,
                updated_at=str(int(existing_draft.updated_at.timestamp())),
                user_id=existing_draft.user_id,
                space_id=draft_po.space_id
            )

        # 创建新草稿
        new_draft = orm_repo.PromptUserDraftModel(
            prompt_id=draft_po.prompt_id,
            user_id=draft_po.user_id,
            space_id=int(draft_po.space_id),
            template_type=draft_po.template_type,
            messages=draft_po.messages,
            prompt_model_config=draft_po.prompt_model_config,
            variable_defs=draft_po.variable_defs,
            tools=draft_po.tools,
            tool_call_config=draft_po.tool_call_config,
            base_version=draft_po.base_version,
            is_draft_edited=draft_po.is_draft_edited,
            deleted_at=0,
            created_at=cur_datetime,
            updated_at=cur_datetime
        )

        self.db.add(new_draft)
        self.db.commit()
        self.db.refresh(new_draft)

        return entities.DraftInfoOutput(
            base_version=new_draft.base_version,
            created_at=str(int(new_draft.created_at.timestamp())),
            is_draft_edited=True,
            updated_at=str(int(new_draft.updated_at.timestamp())),
            user_id=draft_po.user_id,
            space_id=draft_po.space_id
        )

    def get_draft(self, prompt_id: int, user_id: str) -> Optional[Any]:
        """获取草稿数据的原子操作"""
        return self.db.query(orm_repo.PromptUserDraftModel).filter(
            orm_repo.PromptUserDraftModel.prompt_id == prompt_id,
            orm_repo.PromptUserDraftModel.user_id == user_id,
            orm_repo.PromptUserDraftModel.deleted_at == 0
        ).first()


class SQLPromptSubmitRepository(PromptSubmitRepository):
    def __init__(self, db: Session):
        self.db = db

    def save_commit(self, commit: entities.PromptSubmit) -> entities.PromptSubmit:
        db_commit = orm_repo.PromptCommitModel(
            space_id=commit.space_id,
            prompt_id=commit.prompt_id,
            prompt_key=commit.prompt_key,
            template_type=commit.template_type,
            messages=commit.messages,
            prompt_model_config=commit.prompt_model_config,
            variable_defs=commit.variable_defs,
            tools=commit.tools,
            tool_call_config=commit.tool_call_config,
            version=commit.version,
            base_version=commit.base_version,
            committed_by=commit.committed_by,
            description=commit.description,
            created_at=get_china_datetime(),
            updated_at=get_china_datetime()
        )

        self.db.add(db_commit)
        self.db.commit()
        self.db.refresh(db_commit)
        return commit

    def find_commit_by_version(self, prompt_id: int, version: str) -> Optional[entities.PromptSubmit]:
        db_commit = self.db.query(orm_repo.PromptCommitModel).filter(
            orm_repo.PromptCommitModel.prompt_id == prompt_id,
            orm_repo.PromptCommitModel.version == version
        ).first()

        if not db_commit:
            return None

        return entities.PromptSubmit(
            id=db_commit.id,
            space_id=db_commit.space_id,
            prompt_id=db_commit.prompt_id,
            prompt_key=db_commit.prompt_key,
            template_type=db_commit.template_type,
            messages=db_commit.messages,
            prompt_model_config=db_commit.prompt_model_config,
            variable_defs=db_commit.variable_defs,
            tools=db_commit.tools,
            tool_call_config=db_commit.tool_call_config,
            version=db_commit.version,
            base_version=db_commit.base_version,
            committed_by=db_commit.committed_by,
            description=db_commit.description,
            created_at=db_commit.created_at,
            updated_at=db_commit.updated_at
        )

    def list_commits_by_prompt_id(self, prompt_id: int, limit: int) -> List[Any]:
        """根据 prompt_id 查询提交记录，按版本号逆序排列"""
        commits = self.db.query(orm_repo.PromptCommitModel).filter(
            orm_repo.PromptCommitModel.prompt_id == prompt_id
        ).order_by(
            # 按版本号逆序排列
            orm_repo.PromptCommitModel.version.desc()
        ).limit(limit).all()

        return commits
