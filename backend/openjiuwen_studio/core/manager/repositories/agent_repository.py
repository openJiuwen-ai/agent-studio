import json
from functools import wraps
from typing import Callable

from fastapi import status
from sqlalchemy import func, literal
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    get_db_jw, get_val_from_dict)
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.models import agent as agent
from openjiuwen_studio.schemas.agent import AgentId
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.space import SpaceAWPQuery


class AgentRepository():
    def __init__(self) -> None:
        pass

    # def __init__(self, db: Session) -> None:
    #     # 关键：显式写出 [A] 和 [B]
    #     self._agent_db: JiuwenBaseRepository[agent.AgentBaseDB] = JiuwenBaseRepository(db, agent.AgentBaseDB)
    #     self._agent_publish_db: JiuwenBaseRepository[agent.AgentPublishDB] = \
    #         JiuwenBaseRepository(db, agent.AgentPublishDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: agent db data preprocessing error")
                logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Error: agent db data preprocessing error: {type(e).__name__}")
        return wrapper
        
    '''
    description: 确保输入的数据, agent_version必须为drfat版本
    param {dict} input_data 
    param {str} function_name   如果不是draft版本, 抛出异常的函数名
    return {*}
    '''

    @staticmethod
    def _check_agent_is_draft(input_data: dict, function_name: str):
        agent_version = get_val_from_dict(input_data, ['agent_version'])
        if agent_version and agent_version != agent.AgentBaseDB.__version_none__:
            raise ValueError(f"agent must be draft version when call function {function_name}.")

    '''
    description: 确保输入的数据, agent_version必须为publish版本
    param {dict} input_data
    param {str} function_name   如果不是publish版本, 抛出异常的函数名
    return {*}
    '''

    @staticmethod
    def _check_agent_is_publish(input_data: dict, function_name: str):
        agent_version = get_val_from_dict(input_data, ['agent_version'])
        if not agent_version or agent_version == agent.AgentBaseDB.__version_none__:
            raise ValueError(f"agent must be publish version when call function {function_name}.")

    '''
    description: 对输入的agent_id做修补转换
    param {AgentId} agent_id
    return {*}
    '''
    @with_exception_handling
    def patch_agent_id(self, agent_id: AgentId, db_session: Session | None = None) -> AgentId:
        if not agent_id.agent_version:
            # 如果是draft版本，补全_version字段
            agent_id.agent_version = agent.AgentBaseDB.__version_none__
        elif agent_id.agent_version == agent.AgentPublishDB.__latest_publish_version__:
            with get_db_jw(db_session) as db: 
                # 如果是最后的发布版本
                latest_publish_version = self.get_agent_latest_publish_version_db(agent_id, db)
                if latest_publish_version:
                    agent_id.agent_version = latest_publish_version
        return agent_id

    '''
    description: 创建draft版本的agent
    param {agent} agent_info
    return {*}
    '''
    @with_exception_handling
    def create_agent_db(
        self,
        agent_info: agent.AgentBaseDBPd,
        db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            agent_info_dict = agent_info.model_dump()
            if not agent_info_dict.get("agent_version", None):
                agent_info_dict["agent_version"] = agent.AgentBaseDB.__version_none__
            self._check_agent_is_draft(agent_info_dict, "create_agent_db")
            find_id = AgentId.model_validate(agent_info_dict).model_dump(exclude_none=True)
            _agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            return _agent_db.register_dl_in_sql(find_id=find_id, dl=agent_info_dict)
    
    '''
    description: 获取某个agent数据(draft/publish版本)
    param {*} self
    param {AgentId} agent_query
    return {*}
    '''
    @with_exception_handling
    def get_agent_db(self, agent_query: AgentId, db_session: Session | None = None) -> ResponseModel[dict]:
        """由agent_query来获取单个智能体信息"""
        with get_db_jw(db_session) as db: 
            agent_query = self.patch_agent_id(agent_query, db)
            model_class = agent.AgentPublishDB if agent_query.agent_version != agent.AgentBaseDB.__version_none__ \
                                    else agent.AgentBaseDB
            find_id = agent_query.model_dump()
            query = JiuwenBaseRepository(db, model_class)
            return query.get_dl_in_sql(find_id=find_id, return_first_item=True)
    
    '''
    description: 返回agent的最新发布版本
    param {*} self
    param {AgentId} agent_id    agent_id中的version无效
    param {Session} db_session  数据库会话，可选
    return {*}
    '''
    @with_exception_handling
    def get_agent_latest_publish_version_db(self, agent_id: AgentId, db_session: Session | None = None) -> str | None:
        with get_db_jw(db_session) as db: 
            agent_id.agent_version = agent.AgentBaseDB.__version_none__
            find_id = agent_id.model_dump()
            query = JiuwenBaseRepository(db, agent.AgentBaseDB)
            cols_find = ['latest_publish_version']
            db_res = query.get_dl_in_sql_with_cols(find_id=find_id, cols_find=cols_find, return_first_item=True)
            return db_res.data.get('latest_publish_version', None) if db_res.data else None
    
    '''
    description: 保存更新draft版本的agent
    param {*} self
    param {agent} agent_info
    return {*}
    '''
    @with_exception_handling
    def save_agent_db(self, agent_info: agent.AgentBaseDBPd, db_session: Session | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            dl = agent_info.model_dump()
            self._check_agent_is_draft(dl, "save_agent_db")
            if not dl.get("agent_version", None):
                dl["agent_version"] = agent.AgentBaseDB.__version_none__
            find_id = AgentId.model_validate(dl).model_dump()
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            return agent_db.update_dl_in_sql(find_id=find_id, update_dl=dl)
    
    '''
    description: 获取某空间space中所有的agent的总结信息
    param {agent} space_agent_query
    return {*}
    '''
    @with_exception_handling
    def get_space_agent_list_db(
        self, space_agent_query: SpaceAWPQuery, db_session: Session | None = None
    ) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            page = space_agent_query.page
            page_size = space_agent_query.page_size
            offset = (page - 1) * page_size
            return_range = [offset, page_size]

            # 获取分页和排序参数
            query_body = space_agent_query.model_dump(exclude_none=True)

            # 构建基础查询条件（只包含数据库字段）
            find_id = {"space_id": query_body.get("space_id")}
            find_id = agent.AgentBaseDB.filter_invalid_keys(find_id)

            # 处理状态过滤
            status_filter = query_body.get("status_filter")
            if status_filter and status_filter != 'all':
                find_id["status"] = status_filter

            # 构建搜索条件
            search_term = query_body.get("search_term", "").strip()
            searchs = None
            if search_term:
                searchs = {search_term: ["agent_name", "description"]}

            # 构建排序条件 - 从原始查询中获取
            sort_by = query_body.get("sort_by", "update_time")
            sort_order = query_body.get("sort_order", "desc")

            if sort_order == "desc":
                order_cols_desc = [sort_by]
                order_cols_asc = []
            else:
                order_cols_asc = [sort_by]
                order_cols_desc = []

            # 定义需要返回的字段，包含必要的JSON字段（如model）
            # 基础元数据字段 + 重要的JSON字段
            meta_data_keys = agent.AgentBaseDB.get_meta_data_keys()
            cols_find = meta_data_keys + ["model"]

            res = agent_db.get_dl_in_sql_with_cols(find_id=find_id, cols_find=cols_find,
                                                   order_cols_desc=order_cols_desc, order_cols_asc=order_cols_asc,
                                                   return_range=return_range, searchs=searchs)
            
            # 处理查询结果
            if res.code == status.HTTP_200_OK:
                # 查询成功，有数据返回
                items = res.data
                # 获取记录总数
                if searchs:
                    count = agent_db.count_dl_in_sql_with_search(find_id=find_id, searchs=searchs)
                else:
                    count = agent_db.count_dl_in_sql(find_id=find_id)
                
                if count.code != status.HTTP_200_OK:
                    # 计数查询失败，返回计数错误
                    return count
                
                total = count.data
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Get agent list success",
                    data={
                        "items": items,
                        "total": total,
                    }
                )
            elif res.code == status.HTTP_404_NOT_FOUND and res.message == "Data not found.":
                # 查询成功，但没有查到内容，返回空结果
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Get null agent list",
                    data={
                        "items": [],
                        "total": 0,
                    }
                )
            else:
                # 查询有异常错误，直接报出来
                return res
    
    '''
    description: 获取某agent的所有发布过的版本list
    param {AgentId}    query_body, 其中的agent_version失效
    return {dict}      ResponseModel的dict数据, 其中返回的数据保存在data中,
                        data={"agent_version":...,   "version_description":...}
    '''
    @with_exception_handling
    def get_agent_publish_list(
        self, query_body: dict, db_session: Session | None = None
    ) -> ResponseModel[list[dict] | None]:
        """获取智能体的所有发布版本列表"""
        with get_db_jw(db_session) as db:
            agent_publish_db = JiuwenBaseRepository(db, agent.AgentPublishDB)
            find_id = {
                "space_id": query_body.get("space_id"),
                "agent_id": query_body.get("agent_id")
            }
            cols_find = ["agent_version", "version_description", "create_time"]
            # 获取所有发布版本并按版本号降序排序
            return agent_publish_db.get_dl_in_sql_with_cols(
                find_id=find_id,
                cols_find=cols_find,
                order_cols_desc=["agent_version"]  # 按版本号降序排列
            )

    '''
    description: 发布agent
    param {*} self
    param {agent} publish_data
    return {*}
    '''
    @with_exception_handling
    def publish_agent_db(
        self, publish_data: agent.AgentPublishDBPd, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            publish_dict = publish_data.model_dump(exclude_none=True)
            self._check_agent_is_publish(publish_dict, "publish_agent_db")
            agent_publish_db = JiuwenBaseRepository(db, agent.AgentPublishDB)
            find_id = AgentId.model_validate(publish_dict).model_dump()
            timestamp = milliseconds()
            if "create_time" not in publish_dict:
                publish_dict["create_time"] = timestamp
            if "update_time" not in publish_dict:
                publish_dict["update_time"] = timestamp
            register_res = agent_publish_db.register_dl_in_sql(find_id=find_id, dl=publish_dict)
            if register_res.code != status.HTTP_200_OK:
                return register_res
            
            # 更新draft表
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            update_dl = {
                "latest_publish_version": find_id.pop("agent_version", None),
                "latest_publish_time": publish_dict["create_time"],
                "update_time": publish_dict["create_time"],
            }
            update_res = agent_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl)
            if update_res.code != status.HTTP_200_OK:
                return update_res
            return register_res

    '''
    description: 删除draft版本的agent, 会自动连带删除所有的publish版本, 慎用
    param {AgentId} agent_query
    return {*}
    '''
    @with_exception_handling
    def delete_agent_db(self, agent_query: AgentId, db_session: Session | None = None) -> ResponseModel[None]:
        self._check_agent_is_draft(agent_query.model_dump(), "delete_agent_db")
        with get_db_jw(db_session) as db: 
            find_id = self.patch_agent_id(agent_query, db).model_dump()
            query = JiuwenBaseRepository(db, agent.AgentBaseDB)
            return query.unregister_dl_in_sql(find_id=find_id)

    '''
    description: 删除某个版本的agent
    param {AgentId} agent_query
    return {*}
    '''
    @with_exception_handling
    def delete_agent_publish_db(self, agent_query: AgentId, db_session: Session | None = None) -> ResponseModel[None]:
        self._check_agent_is_publish(agent_query.model_dump(), "delete_agent_publish_db")
        with get_db_jw(db_session) as db: 
            find_id = self.patch_agent_id(agent_query, db).model_dump()
            query = JiuwenBaseRepository(db, agent.AgentPublishDB)
            delete_res = query.unregister_dl_in_sql(find_id=find_id)
            if delete_res.code != status.HTTP_200_OK:
                return delete_res
            # 更新draft表中的最新发布版本信息
            find_id.pop("agent_version")
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            agent_draft_res = agent_db.get_dl_in_sql(find_id=find_id, return_first_item=True, 
                                                        return_declarativebase=True)
            if agent_draft_res.code != status.HTTP_200_OK:
                return agent_draft_res
            agent_draft: agent.AgentBaseDB = agent_draft_res.data
            # 更新workflow draft中的发布变量
            agent_draft.update_agent_latest_publish_version()
            # 更新至数据库
            agent_db.update(agent_draft, {})
            return delete_res

    def _build_knowledge_base_query_condition(self, kb_id: str, knowledge_col):
        """构建查询引用指定知识库的agent的条件"""
        if settings.db_type.lower() == "sqlite":
            # SQLite: 用 LIKE 模糊匹配（JSON数组中包含该ID）
            return knowledge_col.like(f'%"{kb_id}"%')
        else:
            # MySQL: 用 JSON_CONTAINS
            json_value = literal(json.dumps(kb_id))
            return func.json_contains(knowledge_col, json_value)

    @staticmethod
    def _build_tool_query_condition(tool_id: str, plugins_col):
        """构建查询引用指定工具的agent的条件"""
        if settings.db_type.lower() == "sqlite":
            # SQLite: 用 LIKE 模糊匹配
            return plugins_col.like(f'%"{tool_id}"%')
        else:
            # MySQL: 用 JSON_CONTAINS
            # plugins 存储结构: [{"tool_id": "...", ...}]
            # 构造包含 tool_id 的局部对象进行匹配
            json_value = literal(json.dumps({"tool_id": tool_id}))
            return func.json_contains(plugins_col, json_value)

    def _query_agents_referencing_kb(self, db, space_id: str, kb_id: str, cols_find: list, agent_db, knowledge_col):
        """查询引用指定知识库的agent"""
        find_id = {"space_id": space_id}
        json_contains_condition = self._build_knowledge_base_query_condition(kb_id, knowledge_col)

        result = agent_db.get_dl_in_sql_with_cols(
            find_id=find_id,
            cols_find=cols_find,
            other_sqlalchemy_limitations=[json_contains_condition],
            return_first_item=False
        )
        return result

    '''
    description: 从所有包含指定知识库ID的agent中移除该知识库ID（包括draft和publish版本）
    param {str} space_id 空间ID
    param {str} kb_id 要移除的知识库ID
    param {Session} db_session 数据库会话，可选
    return {ResponseModel} 更新结果
    '''
    @with_exception_handling
    def remove_knowledge_base_from_agents(
        self,
        space_id: str,
        kb_id: str,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        """从所有包含该知识库的agent中移除该知识库ID"""
        with get_db_jw(db_session) as db:
            updated_count = 0
            failed_count = 0
            errors = []

            cols_find = ["agent_id", "agent_version", "agent_name", "knowledge"]

            # 查询并更新draft版本的agent
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            knowledge_col = agent.AgentBaseDB.knowledge
            result = self._query_agents_referencing_kb(db, space_id, kb_id, cols_find, agent_db, knowledge_col)

            if result.code == status.HTTP_200_OK and result.data:
                for agent_data in result.data:
                    try:
                        agent_id = agent_data.get("agent_id")
                        agent_version = agent_data.get("agent_version")
                        knowledge_list = agent_data.get("knowledge", [])

                        if not isinstance(knowledge_list, list):
                            knowledge_list = []

                        # 移除指定的知识库ID
                        if kb_id in knowledge_list:
                            knowledge_list.remove(kb_id)

                            # 更新draft版本 - 需要先获取完整的agent数据以确保所有字段都被保留
                            agent_query = AgentId(
                                space_id=space_id,
                                agent_id=agent_id,
                                agent_version=agent.AgentBaseDB.__version_none__
                            )
                            get_result = self.get_agent_db(agent_query, db)

                            if get_result.code == status.HTTP_200_OK and get_result.data:
                                agent_full_data = get_result.data
                                # 更新knowledge字段，确保空列表也能被正确更新
                                agent_full_data["knowledge"] = knowledge_list  # 直接使用列表，即使是空列表
                                agent_full_data["update_time"] = milliseconds()

                                # 使用update_dl_in_sql更新，确保knowledge字段被正确更新
                                agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
                                find_id = {
                                    "space_id": space_id,
                                    "agent_id": agent_id,
                                    "agent_version": agent.AgentBaseDB.__version_none__
                                }
                                # 只更新knowledge和update_time字段，确保空列表也能被更新
                                update_dl = {
                                    "knowledge": knowledge_list,
                                    "update_time": milliseconds()
                                }
                                update_result = agent_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl)
                            else:
                                update_result = ResponseModel(
                                    code=status.HTTP_404_NOT_FOUND,
                                    message=f"Agent not found: {agent_id}"
                                )

                            if update_result.code == status.HTTP_200_OK:
                                updated_count += 1
                                logger.info(
                                    f"[KB_DELETE] Removed KB {kb_id} from agent {agent_id} (draft version)"
                                )
                            else:
                                failed_count += 1
                                error_msg = f"Failed to update agent {agent_id} (draft): {update_result.message}"
                                errors.append(error_msg)
                                logger.error(f"[KB_DELETE] {error_msg}")

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Error processing agent {agent_data.get('agent_id', 'unknown')} (draft): {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"[KB_DELETE] {error_msg}", exc_info=True)

            # 查询并更新publish版本的agent
            agent_publish_db = JiuwenBaseRepository(db, agent.AgentPublishDB)
            knowledge_col_publish = agent.AgentPublishDB.knowledge
            result_publish = self._query_agents_referencing_kb(
                db, space_id, kb_id, cols_find, agent_publish_db, knowledge_col_publish
            )

            if result_publish.code == status.HTTP_200_OK and result_publish.data:
                for agent_data in result_publish.data:
                    try:
                        agent_id = agent_data.get("agent_id")
                        agent_version = agent_data.get("agent_version")
                        knowledge_list = agent_data.get("knowledge", [])

                        if not isinstance(knowledge_list, list):
                            knowledge_list = []

                        # 移除指定的知识库ID
                        if kb_id in knowledge_list:
                            knowledge_list.remove(kb_id)

                            # 更新publish版本 - 直接更新knowledge字段，确保空列表也能被正确更新
                            # 构建find_id用于定位记录
                            find_id_publish = {
                                "space_id": space_id,
                                "agent_id": agent_id,
                                "agent_version": agent_version
                            }
                            # 只更新knowledge和update_time字段，确保空列表也能被更新
                            update_dl = {
                                "knowledge": knowledge_list,  # 直接使用列表，即使是空列表
                                "update_time": milliseconds()
                            }
                            update_result = agent_publish_db.update_dl_in_sql(
                                find_id=find_id_publish,
                                update_dl=update_dl
                            )

                            if update_result.code == status.HTTP_200_OK:
                                updated_count += 1
                                logger.info(
                                    f"[KB_DELETE] Removed KB {kb_id} from agent {agent_id} "
                                    f"(publish version: {agent_version})"
                                )
                            else:
                                failed_count += 1
                                error_msg = (
                                    f"Failed to update agent {agent_id} version {agent_version} "
                                    f"(publish): {update_result.message}"
                                )
                                errors.append(error_msg)
                                logger.error(f"[KB_DELETE] {error_msg}")

                    except Exception as e:
                        failed_count += 1
                        error_msg = (
                            f"Error processing agent {agent_data.get('agent_id', 'unknown')} "
                            f"(publish): {str(e)}"
                        )
                        errors.append(error_msg)
                        logger.error(f"[KB_DELETE] {error_msg}", exc_info=True)

            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Removed knowledge base from agents: {updated_count} updated, {failed_count} failed",
                data={
                    "updated_count": updated_count,
                    "failed_count": failed_count,
                    "errors": errors if errors else None
                }
            )

    '''
    description: 获取所有引用指定知识库ID的智能体列表（只查询，不删除）
    param {str} space_id 空间ID
    param {str} kb_id 知识库ID
    param {Session} db_session 数据库会话，可选
    return {ResponseModel} 包含智能体名称列表的响应
    '''
    @with_exception_handling
    def get_agents_referencing_knowledge_base(
        self,
        space_id: str,
        kb_id: str,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        """获取所有引用该知识库的智能体名称列表"""
        with get_db_jw(db_session) as db:
            cols_find = ["agent_id", "agent_name"]

            # 查询draft版本的agent
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            knowledge_col = agent.AgentBaseDB.knowledge
            result = self._query_agents_referencing_kb(db, space_id, kb_id, cols_find, agent_db, knowledge_col)

            agent_names = []
            if result.code == status.HTTP_200_OK and result.data:
                # 收集draft版本的智能体名称（去重）
                seen_agent_ids = set()
                for agent_data in result.data:
                    agent_id = agent_data.get("agent_id")
                    agent_name = agent_data.get("agent_name", "")
                    if agent_id and agent_id not in seen_agent_ids:
                        agent_names.append(agent_name or f"智能体 {agent_id}")
                        seen_agent_ids.add(agent_id)

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get agents referencing knowledge base successfully",
                data={
                    "agent_names": agent_names,
                    "count": len(agent_names)
                }
            )

    def _query_agents_referencing_tool(self, space_id: str, tool_id: str, cols_find: list, agent_db, plugins_col):
        """查询引用指定工具的agent"""
        find_id = {"space_id": space_id}
        tool_condition = self._build_tool_query_condition(tool_id, plugins_col)

        result = agent_db.get_dl_in_sql_with_cols(
            find_id=find_id,
            cols_find=cols_find,
            other_sqlalchemy_limitations=[tool_condition],
            return_first_item=False
        )
        return result

    @staticmethod
    def _build_plugin_query_condition(plugin_id: str, plugins_col):
        """构建查询引用指定插件的agent的条件"""
        if settings.db_type.lower() == "sqlite":
            # SQLite: 用 LIKE 模糊匹配
            return plugins_col.like(f'%"{plugin_id}"%')
        else:
            # MySQL: 用 JSON_CONTAINS
            # plugins 存储结构: [{"plugin_id": "...", ...}]
            # 构造包含 plugin_id 的局部对象进行匹配
            json_value = literal(json.dumps({"plugin_id": plugin_id}))
            return func.json_contains(plugins_col, json_value)

    def _query_agents_referencing_plugin(self, space_id: str, plugin_id: str, cols_find: list, agent_db, plugins_col):
        """查询引用指定插件的agent"""
        find_id = {"space_id": space_id}
        plugin_condition = self._build_plugin_query_condition(plugin_id, plugins_col)

        result = agent_db.get_dl_in_sql_with_cols(
            find_id=find_id,
            cols_find=cols_find,
            other_sqlalchemy_limitations=[plugin_condition],
            return_first_item=False
        )
        return result

    @with_exception_handling
    def update_plugin_name_in_agents(
        self,
        space_id: str,
        plugin_id: str,
        new_plugin_name: str,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        """更新引用了指定插件的agent中的插件名称"""
        with get_db_jw(db_session) as db:
            updated_count = 0
            failed_count = 0
            errors = []

            cols_find = ["agent_id", "agent_version", "plugins"]

            # 查询并更新draft版本的agent
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            plugins_col = agent.AgentBaseDB.plugins
            result = self._query_agents_referencing_plugin(space_id, plugin_id, cols_find, agent_db, plugins_col)

            if result.code == status.HTTP_200_OK and result.data:
                for agent_data in result.data:
                    try:
                        agent_id = agent_data.get("agent_id")
                        plugins_list = agent_data.get("plugins", [])

                        if not isinstance(plugins_list, list):
                            continue

                        updated = False
                        for plugin in plugins_list:
                            if plugin.get("plugin_id") == plugin_id:
                                if plugin.get("plugin_name") != new_plugin_name:
                                    plugin["plugin_name"] = new_plugin_name
                                    updated = True
                        
                        if updated:
                            # 更新draft版本
                            find_id = {
                                "space_id": space_id,
                                "agent_id": agent_id,
                                "agent_version": agent.AgentBaseDB.__version_none__
                            }
                            update_dl = {
                                "plugins": plugins_list,
                                "update_time": milliseconds()
                            }
                            update_result = agent_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl)

                            if update_result.code == status.HTTP_200_OK:
                                updated_count += 1
                                logger.info(f"[PLUGIN_UPDATE] Updated plugin name for agent {agent_id} (draft)")
                            else:
                                failed_count += 1
                                error_msg = f"Failed to update agent {agent_id} (draft): {update_result.message}"
                                errors.append(error_msg)
                                logger.error(f"[PLUGIN_UPDATE] {error_msg}")

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Error processing agent {agent_data.get('agent_id', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"[PLUGIN_UPDATE] {error_msg}", exc_info=True)

            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Updated plugin name in agents: {updated_count} updated, {failed_count} failed",
                data={
                    "updated_count": updated_count,
                    "failed_count": failed_count,
                    "errors": errors if errors else None
                }
            )

    @with_exception_handling
    def update_tool_name_in_agents(
        self,
        space_id: str,
        tool_id: str,
        new_tool_name: str,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        """更新引用了指定工具的agent中的工具名称"""
        with get_db_jw(db_session) as db:
            updated_count = 0
            failed_count = 0
            errors = []

            cols_find = ["agent_id", "agent_version", "plugins"]

            # 查询并更新draft版本的agent
            agent_db = JiuwenBaseRepository(db, agent.AgentBaseDB)
            plugins_col = agent.AgentBaseDB.plugins
            result = self._query_agents_referencing_tool(space_id, tool_id, cols_find, agent_db, plugins_col)

            if result.code == status.HTTP_200_OK and result.data:
                for agent_data in result.data:
                    try:
                        agent_id = agent_data.get("agent_id")
                        plugins_list = agent_data.get("plugins", [])

                        if not isinstance(plugins_list, list):
                            continue

                        updated = False
                        for plugin in plugins_list:
                            if plugin.get("tool_id") == tool_id:
                                if plugin.get("tool_name") != new_tool_name:
                                    plugin["tool_name"] = new_tool_name
                                    updated = True
                        
                        if updated:
                            # 更新draft版本
                            find_id = {
                                "space_id": space_id,
                                "agent_id": agent_id,
                                "agent_version": agent.AgentBaseDB.__version_none__
                            }
                            update_dl = {
                                "plugins": plugins_list,
                                "update_time": milliseconds()
                            }
                            update_result = agent_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl)

                            if update_result.code == status.HTTP_200_OK:
                                updated_count += 1
                                logger.info(f"[TOOL_UPDATE] Updated tool name for agent {agent_id} (draft)")
                            else:
                                failed_count += 1
                                error_msg = f"Failed to update agent {agent_id} (draft): {update_result.message}"
                                errors.append(error_msg)
                                logger.error(f"[TOOL_UPDATE] {error_msg}")

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Error processing agent {agent_data.get('agent_id', 'unknown')}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(f"[TOOL_UPDATE] {error_msg}", exc_info=True)

            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Updated tool name in agents: {updated_count} updated, {failed_count} failed",
                data={
                    "updated_count": updated_count,
                    "failed_count": failed_count,
                    "errors": errors if errors else None
                }
            )


agent_repository = AgentRepository()