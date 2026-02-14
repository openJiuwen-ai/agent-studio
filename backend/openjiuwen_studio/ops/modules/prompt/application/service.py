#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

from typing import List, Optional

from sqlalchemy import or_

from openjiuwen_studio.ops.common.date_time_util import get_china_datetime
from openjiuwen_studio.ops.modules.prompt.application.debug_service import logger
from openjiuwen_studio.ops.modules.prompt.domain import entities
from openjiuwen_studio.ops.modules.prompt.domain.entities import OptimizeTaskCreationRequest
from openjiuwen_studio.ops.modules.prompt.domain.repositories import PromptRepository, AgentRepository, JobRepository
from openjiuwen_studio.ops.modules.prompt.domain.services import DraftDomainService, CommitDomainService, \
    BatchPromptDomainService, GetPromptDetailService, JobDomainService
from openjiuwen_studio.ops.modules.prompt.domain.repositories import PromptUserDraftRepository, PromptSubmitRepository
from openjiuwen_studio.ops.modules.prompt.application.exception import NotFoundException, DuplicateException
from openjiuwen_studio.ops.modules.prompt.infra.repositories import orm_repo


class PromptService:
    def __init__(
            self,
            prompt_repo: PromptRepository,
            prompt_user_draft_repo: PromptUserDraftRepository,
            prompt_commit_repo: PromptSubmitRepository,
            agent_repo: AgentRepository,):
        self.prompt_repo = prompt_repo
        self.agent_repo = agent_repo
        self.draft_domain_service = DraftDomainService(prompt_user_draft_repo, prompt_commit_repo)
        self.commit_domain_service = CommitDomainService(prompt_user_draft_repo, prompt_commit_repo, agent_repo)
        self.batch_prompt_domain_service = BatchPromptDomainService(prompt_repo)
        self.get_prompt_detail_service = GetPromptDetailService(prompt_repo, agent_repo)

    def create_prompt(self, new_prompt: entities.CreatePromptRequest) -> entities.CreatePromptResponse:
        """
        初始创建prompt基础内容
        """
        # 检查名称是否已存在
        conditions = [orm_repo.PromptBasicModel.prompt_key == new_prompt.prompt_key]
        conditions.append(orm_repo.PromptBasicModel.space_id == new_prompt.workspace_id)
        conditions.append(orm_repo.PromptBasicModel.deleted_at.is_(None))
        existing = self.prompt_repo.get_all(conditions, orm_repo.PromptBasicModel)
        if existing:
            raise DuplicateException(f"Prompt with prompt_key '{new_prompt.prompt_key}' already exists")

        # 创建prompt数据
        db_prompt = orm_repo.PromptBasicModel(
            updated_by=new_prompt.updated_by,
            created_by=new_prompt.updated_by,
            space_id=new_prompt.workspace_id,
            prompt_key=new_prompt.prompt_key,
            name=new_prompt.prompt_name,
            description=new_prompt.prompt_description
        )
        prompt_res = self.prompt_repo.save(db_prompt)
        return entities.CreatePromptResponse(
            prompt_id=prompt_res,
        )

    def get_prompt(self, prompts: dict) -> entities.GetPromptResponse:
        """
        从所有关联表中获取prompt信息
        1、从prompt_basic中获取有关信息(deleted_at为null)
        2、用trans_promptbasic_to_prompts查询关联表并整合成prompt结构回传
        """
        conditions = [orm_repo.PromptBasicModel.id == prompts.get("prompt_id")]
        prompts_basic_model = self.prompt_repo.get_all(conditions, orm_repo.PromptBasicModel)
        if not prompts_basic_model:
            raise NotFoundException(f"Prompt with ID {prompts.get('prompt_id')} not found")
        prompts_basic_model = prompts_basic_model[0]
        prompt = self.get_prompt_detail_service.get_prompt_from_basic(prompts_basic_model, prompts)
        prompt_detail = self.prompt_repo.get_default_model_config()

        if not prompts.get("with_draft"):
            prompt.prompt_draft = None
        if not prompts.get("with_commit"):
            prompt.prompt_commit = None
        if not prompts.get("with_default_config"):
            prompt_detail = None
        return entities.GetPromptResponse(
            prompt=[prompt],
            default_config=prompt_detail
        )

    def list_prompts(self, list_prompt: entities.ListPromptRequest) -> entities.ListPromptResponse:
        """
        从prompt_basic中获取该用户prompts
        """
        conditions = [orm_repo.PromptBasicModel.deleted_at.is_(None)]
        if list_prompt.workspace_id:
            conditions.append(orm_repo.PromptBasicModel.space_id == list_prompt.workspace_id)
        if list_prompt.created_bys:
            conditions.append(orm_repo.PromptBasicModel.created_by == list_prompt.created_bys[0])
        if list_prompt.key_word:
            conditions.append(
                or_(
                    orm_repo.PromptBasicModel.prompt_key.contains(list_prompt.key_word),
                    orm_repo.PromptBasicModel.name.contains(list_prompt.key_word),
                    orm_repo.PromptBasicModel.description.contains(list_prompt.key_word)
                )
            )
        order_by = None
        use_max_updated_at_order = list_prompt.order_by == entities.ListPromptOrderBy.UPDATED_AT
        if use_max_updated_at_order:
            # 按 max(prompt_basic.updated_at, prompt_draft.updated_at) 排序
            prompts_basic, all_basic = self.prompt_repo.list_all_order_by_max_updated_at(
                list_prompt.page_num,
                list_prompt.page_size,
                conditions,
                asc=list_prompt.asc if list_prompt.asc is not None else False,
            )
        else:
            if list_prompt.order_by:
                order_by = getattr(orm_repo.PromptBasicModel, getattr(entities.PromptBasicMap, list_prompt.order_by))
                if list_prompt.asc:
                    order_by = order_by.asc()
                else:
                    order_by = order_by.desc()
            prompts_basic, all_basic = self.prompt_repo.list_all(
                list_prompt.page_num, list_prompt.page_size, conditions, order_by, orm_repo.PromptBasicModel)
        list_prompt_res = [self.get_prompt_detail_service.get_prompt_from_basic(k, {}) for k in prompts_basic]
        for item in list_prompt_res:
            # 返回的结果中可能不需要prompt_draft和prompt_commit，临时删除
            setattr(item, 'prompt_commit', None)
        user_list = [self.prompt_repo.trans_promptbasic_to_userinfo(k) for k in prompts_basic]
        return entities.ListPromptResponse(
            prompts=list_prompt_res,
            total=len(all_basic),
            users=user_list if user_list else None
        )

    def update_prompt(self, new_prompt: entities.UpdatePromptRequest) -> entities.UpdatePromptResponse:
        """
        更新prompts
        功能在detail也左上角，仅更新基础的name和description信息
        """
        ori_prompt = self.prompt_repo.find_by_id(new_prompt.prompt_id, orm_repo.PromptBasicModel)
        if not ori_prompt:
            raise NotFoundException(f"Prompt with ID {new_prompt.prompt_id} not found")
        ori_prompt.name = new_prompt.prompt_name
        ori_prompt.description = new_prompt.prompt_description
        self.prompt_repo.update(ori_prompt)

        # 同步更新agent中关联提示词模版名称
        try:
            update_field_dict = {"prompt_name":new_prompt.prompt_name}
            updated_result = self.agent_repo.update_field_by_prompt_id(new_prompt.prompt_id, update_field_dict, orm_repo.AgentModel)
            logger.info(f"Updated {new_prompt.prompt_id} num: {updated_result}")
        except Exception as e:
            logger.warning(f"Updated {new_prompt.prompt_id} prompt name in agent failed")

        return entities.UpdatePromptResponse(
            msg="",
            code=0,
        )

    def delete_prompt(self, prompts: entities.DeletePromptRequest) -> entities.DeletePromptResponse:
        """
        删除对应prompt_id的prompts
        逻辑删除，设置当前时间为deleted_at
        """
        prompt = self.prompt_repo.find_by_id(prompts.prompt_id, orm_repo.PromptBasicModel)
        if not prompt:
            return entities.DeletePromptResponse(
                msg=f"Prompt with ID {prompts} not found",
                code=501
            )

        agent_models = self.agent_repo.find_by_id(prompts.prompt_id, "", orm_repo.AgentModel)

        if agent_models:
            return entities.DeletePromptResponse(
                msg=f"Prompt with ID {prompts.prompt_id} has associated with other obj",
                code=501
            )

        self.prompt_repo.delete(prompts.prompt_id, orm_repo.PromptBasicModel)
        return entities.DeletePromptResponse(
            msg="",
            code=0
        )

    def clone_prompt(self, ori_prompt_id, new_prompt: entities.ClonePromptRequest) -> entities.ClonePromptResponse:
        """
        克隆当前详情页的prompt(仅基础内容)
        """
        # 检查原始数据是否存在
        prompt = self.prompt_repo.find_by_id(ori_prompt_id, orm_repo.PromptBasicModel)
        if not prompt:
            raise NotFoundException(f"Prompt with ID {ori_prompt_id} not found")
        # 检查名称是否已存在
        existing = self.prompt_repo.find_by_name(new_prompt.cloned_prompt_name, orm_repo.PromptBasicModel)
        if existing:
            raise DuplicateException(f"Prompt with name '{new_prompt.cloned_prompt_name}' already exists")

        # 创建prompt数据
        db_prompt = orm_repo.PromptBasicModel(
            updated_by=new_prompt.user_id,
            created_by=new_prompt.user_id,
            space_id=new_prompt.workspace_id,
            name=new_prompt.cloned_prompt_name,
            prompt_key=new_prompt.cloned_prompt_key,
            description=new_prompt.cloned_prompt_description
        )
        prompt_res = self.prompt_repo.save(db_prompt)

        # 克隆原commit数据，创建draft数据
        prompts_draft_conditions = [
            orm_repo.PromptCommitModel.prompt_id == ori_prompt_id,
            orm_repo.PromptCommitModel.space_id == new_prompt.workspace_id,
            orm_repo.PromptCommitModel.version == new_prompt.commit_version
        ]
        prompts_commit_ori = self.prompt_repo.get_all(prompts_draft_conditions, orm_repo.PromptCommitModel)

        if not prompts_commit_ori:
            self.prompt_repo.delete(prompt_res, orm_repo.PromptBasicModel)
            return entities.ClonePromptResponse(
                cloned_prompt_id=-1,
                msg="get prompts_commit info wrong",
                code=-1
            )

        prompts_commit_ori = prompts_commit_ori[0]
        db_prompt_draft = orm_repo.PromptUserDraftModel(
            space_id=prompts_commit_ori.space_id,
            prompt_id=prompt_res,
            user_id=new_prompt.user_id,
            template_type=prompts_commit_ori.template_type,
            messages=prompts_commit_ori.messages,
            prompt_model_config=prompts_commit_ori.prompt_model_config,
            variable_defs=prompts_commit_ori.variable_defs,
            tools=prompts_commit_ori.tools,
            tool_call_config=prompts_commit_ori.tool_call_config,
            base_version=prompts_commit_ori.base_version,
        )
        db_prompt_draft.is_draft_edited = True
        draft_res = self.prompt_repo.save(db_prompt_draft)
        if not draft_res:
            self.prompt_repo.delete(prompt_res, orm_repo.PromptBasicModel)
            return entities.ClonePromptResponse(
                cloned_prompt_id=-1,
                msg="write prompts_commit info wrong",
                code=-1
            )
        return entities.ClonePromptResponse(
            cloned_prompt_id=prompt_res,
        )

    def save_draft(self, prompt_id: int, draft_input: entities.PromptDraftInput) -> entities.DraftInfoOutput:
        """
        保存草稿
        """
        return self.draft_domain_service.save_draft(prompt_id, draft_input)

    def get_draft(self, prompt_id: int, user_id: str) -> Optional[entities.PromptDraftInput]:
        """
        查询草稿
        """
        return self.draft_domain_service.get_draft(prompt_id, user_id)

    def commit_draft(
            self,
            prompt_id: int,
            user_id: str,
            commit_version: str,
            commit_description: str
    ) -> None:
        """
        提交草稿为正式版本
        """
        prompt_basic = self.prompt_repo.find_by_id(prompt_id, orm_repo.PromptBasicModel)

        # 提交
        self.commit_domain_service.commit_draft(
            prompt_id, user_id, commit_version, commit_description, prompt_basic.prompt_key
        )

        # 更新prompt_basic
        if prompt_basic:
            prompt_basic.latest_version = commit_version
            prompt_basic.latest_commit_time = get_china_datetime()
            prompt_basic.updated_at = get_china_datetime()
            self.prompt_repo.update(prompt_basic)

        # 更新草稿表
        ori_prompt = self.prompt_repo.find_by_prompt_id(prompt_id, orm_repo.PromptUserDraftModel)
        if ori_prompt:
            ori_prompt.base_version = commit_version
            ori_prompt.is_draft_edited = False
            ori_prompt.updated_at = get_china_datetime()
            self.prompt_repo.update(ori_prompt)

    def revert_from_commit(
            self,
            prompt_id: int,
            user_id: str,
            commit_version: str
    ) -> None:
        """
        从提交记录恢复草稿
        """
        self.draft_domain_service.revert_from_commit(
            prompt_id, user_id, commit_version
        )

    def list_commits(self, prompt_id: int, page_size: int) -> List[entities.CommitInfo]:
        """
        获取提交记录列表
        """
        return self.commit_domain_service.list_commits(prompt_id, page_size)

    def batch_get_prompts(self, request: entities.BatchGetPromptRequest) -> entities.BatchGetPromptResponse:
        """
        批量获取prompt
        """
        return self.batch_prompt_domain_service.batch_get_prompts(request)


class JobService:
    def __init__(
            self,
            job_repo: JobRepository,
    ):
        self.job_service = JobDomainService(job_repo)

    def save_draft(self, space_id: str, user_id: str, draft_id: str, draft_input: OptimizeTaskCreationRequest):
        """
        保存任务草稿
        """
        return self.job_service.save_draft(space_id, user_id, draft_id, draft_input)

    def get_draft(self, space_id: str, user_id: str, draft_id: str) -> Optional[entities.JobDraftResponse]:
        """
        查询任务草稿
        """
        return self.job_service.get_draft(space_id, user_id, draft_id)

    def del_draft(self, space_id: str, user_id: str, draft_id: str):
        """
        保存任务草稿
        """
        return self.job_service.del_draft(space_id, user_id, draft_id)

    def get_drafts(self, space_id: str, user_id: str) -> Optional[List[entities.JobDraftResponse]]:
        """
        查询任务草稿,可能有多条
        """
        return self.job_service.get_drafts(space_id, user_id)

    def create_job(self, job_data: dict) -> None:
        """
        创建任务
        """
        return self.job_service.create_job(job_data)

    def update_job(self, job_id: str, space_id: str, user_id: str, update_data: dict):
        """
        更新任务
        """
        return self.job_service.update_job(job_id, space_id, user_id, update_data)

    def get_job_info(self, space_id: str, user_id: str, job_id: str) -> Optional[entities.OptimizeProgressResponse]:
        """
        查询任务草稿
        """
        return self.job_service.get_job_info(space_id, user_id, job_id)

    def get_jobs(
        self, space_id: str, user_id: str, job_ids: List[str]
    ) -> Optional[entities.OptimizeTaskGetInfoResponse]:
        """
        查询任务和草稿,可能有多条
        """
        return self.job_service.get_jobs(space_id, user_id, job_ids)

    def del_job(self, space_id: str, user_id: str, job_id: str):
        """
        删除任务
        """
        return self.job_service.del_job(space_id, user_id, job_id)