import copy
from functools import wraps
from typing import Callable

from fastapi import status
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.agent_repository import agent_repository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.core.manager.repositories.workflow_repository import \
    workflow_repository
from openjiuwen_studio.models.awp_relation import AgentWorkflowRelationDB
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.workflow import WorkflowId


class AwpRelationRepository():
    def __init__(self) -> None:
        pass
    # def __init__(self, db: Session) -> None:
    #     # 关键：显式写出 [A] 和 [B]
    #     self._prompt_relation_db: JiuwenBaseRepository[PromptRelationDB] = JiuwenBaseRepository(db, PromptRelationDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error("Data preprocessing error for relation of agent/workflow/plugin")
                logger.debug(f"Relationship processing exception: {type(e).__name__}", exc_info=True)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Error: Data preprocessing error for relation of agent/workflow/plugin. \
                                                Exception details: {type(e).__name__}")
        return wrapper

    '''
    description: 为某个agent增加与workflow的关联
    param {AgentId} agent_id
    param {WorkflowId} workflow_id
    param {Session} db_session
    return {*}
    '''
    @with_exception_handling
    def create_agent_workflow_relation(self, agent_id: AgentId, workflow_id: WorkflowId, 
                                       db_session: Session | None = None) -> ResponseModel[None]:
        if agent_id.space_id != workflow_id.space_id:
            raise ValueError(f"agent_id and workflow_id must be in the same space, but got agent_id.space_id({agent_id.space_id}) \
                             != workflow_id.space_id({workflow_id.space_id})")
        with get_db_jw(db_session) as db:
            agent_id = agent_repository.patch_agent_id(agent_id, db)
            workflow_id = workflow_repository.patch_workflow_id(workflow_id, db)
            timestamp = milliseconds()
            aw_relation = AgentWorkflowRelationDB(
                space_id=agent_id.space_id,
                agent_id=agent_id.agent_id,
                agent_version=agent_id.agent_version,
                workflow_id=workflow_id.workflow_id,
                workflow_version=workflow_id.workflow_version,
                create_time=timestamp,
                update_time=timestamp,
            )
            aw_relation_db = JiuwenBaseRepository(db, AgentWorkflowRelationDB)
            return aw_relation_db.register_dl_in_sql(None, aw_relation)

    '''
    description: 删除某个agent-workflow的关联
    param {AgentId} agent_id
    param {WorkflowId} workflow_id
    param {Session} db_session
    return {*}
    '''
    @with_exception_handling
    def delete_agent_workflow_relation(self, agent_id: AgentId, workflow_id: WorkflowId, 
                                       db_session: Session | None = None) -> ResponseModel[None]:
        if agent_id.space_id != workflow_id.space_id:
            raise ValueError(f"agent_id and workflow_id must be in the same space, but got agent_id.space_id({agent_id.space_id}) \
                             != workflow_id.space_id({workflow_id.space_id})")
        with get_db_jw(db_session) as db:
            agent_id = agent_repository.patch_agent_id(agent_id, db)
            workflow_id = workflow_repository.patch_workflow_id(workflow_id, db)
            find_id = {
                "space_id": agent_id.space_id,
                "agent_id": agent_id.agent_id,
                "agent_version": agent_id.agent_version,
                "workflow_id": workflow_id.workflow_id,
                "workflow_version": workflow_id.workflow_version,
            }
            aw_relation_db = JiuwenBaseRepository(db, AgentWorkflowRelationDB)
            return aw_relation_db.unregister_dl_in_sql(find_id=find_id)
    
    '''
    description: 复制关联项: 需要发布agent或者复制agent, 将原版本agent的所有关联项复制后关联到新版本的agent中。
    param {AgentId} agent_id_source     原版本agent
    param {AgentId} agent_id_target     目标版本agent
    param {Session} db_session
    return {*}
    '''
    @with_exception_handling
    def copy_agent_workflow_relation(self, agent_id_source: AgentId, agent_id_target: AgentId, 
                                     db_session: Session | None = None) -> ResponseModel[None]:
        if agent_id_source.space_id != agent_id_target.space_id:
            raise ValueError(f"agent_id_source and agent_id_target must be in the same space, but got agent_id_source.space_id({agent_id_source.space_id}) \
                             != agent_id_target.space_id({agent_id_target.space_id})")
        with get_db_jw(db_session) as db:
            agent_id_source = agent_repository.patch_agent_id(agent_id_source, db)
            agent_id_target = agent_repository.patch_agent_id(agent_id_target, db)
            # 判断目标agent与源版本是否完全相同，完全相同则抛出异常
            if agent_id_source.agent_id == agent_id_target.agent_id and agent_id_source.agent_version == agent_id_target.agent_version:
                raise ValueError(f"agent_id_source and agent_id_target must be different, but got same agent_id({agent_id_source.agent_id}) \
                             and same agent_version({agent_id_source.agent_version}).")
            aw_relation_db = JiuwenBaseRepository(db, AgentWorkflowRelationDB)
            # 获取agent-workflow的所有关联数据
            db_res = aw_relation_db.get_dl_in_sql(find_id=agent_id_source.model_dump())
            if db_res.code != status.HTTP_200_OK:
                return db_res
            aw_relation_list: list[dict] = db_res.data
            # 更新关联数据
            for relation in aw_relation_list:
                relation.pop('primary_id', None)
                relation['agent_id'] = agent_id_target.agent_id
                relation['agent_version'] = agent_id_target.agent_version
            return aw_relation_db.bulk_register_dl(aw_relation_list)
    
    '''
    description: 发布agent, 根据发布的agent_id来复制相应的aw关系到新版本的agent中。
    param {AgentId} agent_id_publish    待发布的agent_id
    param {Session} db_session          数据库会话(可选)
    return {*}
    '''
    @with_exception_handling
    def copy_agent_workflow_relation_for_publish(self, agent_id_publish: AgentId, 
                                                 db_session: Session | None = None) -> ResponseModel[None]:
        agent_id_draft = copy.deepcopy(agent_id_publish)
        agent_id_draft.agent_version = None
        return self.copy_agent_workflow_relation(agent_id_draft, agent_id_publish, db_session)

    '''
    description: 查询关联项: 根据输入的agent/workflow id, 查询所有的agent/workflow关联项
    param {*} self
    param {AgentId} query_id
    param {Session} db_session
    return {*}
    '''
    @with_exception_handling
    def get_agent_workflow_relation(self, query_id: AgentId | WorkflowId, 
                                    db_session: Session | None = None) -> ResponseModel[list[dict] | None]:
        with get_db_jw(db_session) as db:
            if isinstance(query_id, AgentId):
                query_id = agent_repository.patch_agent_id(query_id, db)
            else:
                query_id = workflow_repository.patch_workflow_id(query_id, db)
            aw_relation_db = JiuwenBaseRepository(db, AgentWorkflowRelationDB)
            return aw_relation_db.get_dl_in_sql(find_id=query_id.model_dump())


awp_relation_repository = AwpRelationRepository()