from functools import wraps
from typing import Callable

from fastapi import status
from sqlalchemy import bindparam, select
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    escape_like, get_db_jw, get_val_from_dict)
from openjiuwen_studio.core.manager.repositories.workflow_tag_repository import \
    workflow_tag_repository
from openjiuwen_studio.models.workflow import (WorkflowBaseDB, WorkflowBaseDBPd,
                                 WorkflowPublishDB, WorkflowPublishDBPd)
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.space import SpaceAWPQuery
from openjiuwen_studio.schemas.workflow import WorkflowId


class WorkflowRepository():
    def __init__(self) -> None:
        pass

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: workflow db data preprocessing error")
                logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Error: workflow db data preprocessing error: {type(e).__name__}")
        return wrapper

    '''
    description: 确保输入的数据, workflow_version必须为drfat版本
    param {dict} input_data 
    param {str} function_name   如果不是draft版本, 抛出异常的函数名
    return {*}
    '''

    @staticmethod
    def _check_workflow_is_draft(input_data: dict, function_name: str):
        workflow_version = get_val_from_dict(input_data, ['workflow_version'])
        if workflow_version and workflow_version != WorkflowBaseDB.__version_none__:
            raise ValueError(f"workflow must be draft version when call function {function_name}.")

    '''
    description: 确保输入的数据, workflow_version必须为publish版本
    param {dict} input_data
    param {str} function_name   如果不是publish版本, 抛出异常的函数名
    return {*}
    '''

    @staticmethod
    def _check_workflow_is_publish(input_data: dict, function_name: str):
        workflow_version = get_val_from_dict(input_data, ['workflow_version'])
        if not workflow_version or workflow_version == WorkflowBaseDB.__version_none__:
            raise ValueError(f"workflow must be publish version when call function {function_name}.")

    '''
    description: 对输入的workflow_id做修补转换
    param {WorkflowId} workflow_id
    return {*}
    '''
    @with_exception_handling
    def patch_workflow_id(self, workflow_id: WorkflowId, db_session: Session | None = None) -> WorkflowId:
        if not workflow_id.workflow_version:
            # 如果是draft版本，补全_version字段
            workflow_id.workflow_version = WorkflowBaseDB.__version_none__
        elif workflow_id.workflow_version == WorkflowPublishDB.__latest_publish_version__:
            with get_db_jw(db_session) as db: 
                # 如果是最后的发布版本
                latest_publish_version = self.get_workflow_latest_publish_version_db(workflow_id, db)
                if latest_publish_version:
                    workflow_id.workflow_version = latest_publish_version
        return workflow_id
    
    '''
    description: 返回workflow的最新发布版本
    param {*} self
    param {WorkflowId} workflow_id    workflow_id中的version无效
    param {Session} db_session  数据库会话，可选
    return {*}
    '''
    @with_exception_handling
    def get_workflow_latest_publish_version_db(self, workflow_id: WorkflowId, db_session: Session | None = None) -> str | None:
        with get_db_jw(db_session) as db: 
            find_id = workflow_id.model_dump()
            find_id.pop("workflow_version", None)
            query = JiuwenBaseRepository(db, WorkflowBaseDB)
            cols_find = ['latest_publish_version']
            db_res = query.get_dl_in_sql_with_cols(find_id=find_id, cols_find=cols_find, return_first_item=True)
            return db_res.data.get('latest_publish_version', None) if db_res.data else None
    
    '''
    description: 创建draft版本的workflow
    param {dict} workflow_data  待创建的workflow
    return {*}
    '''
    @with_exception_handling
    def workflow_create(self, workflow_data: WorkflowBaseDBPd, db_session: Session | None = None) -> ResponseModel[None]:
        WorkflowRepository._check_workflow_is_draft(workflow_data.model_dump(), "workflow_create")
        with get_db_jw(db_session) as db:
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            if not workflow_data:
                logger.debug(f"No workflow data to register: \ndata: {workflow_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No workflow data to register")
            find_id = {
                "space_id": workflow_data.space_id,
                "workflow_id": workflow_data.workflow_id,
            }
            workflow_data.workflow_version = WorkflowBaseDB.__version_none__
            timestamp = milliseconds()
            if not workflow_data.create_time:
                workflow_data.create_time = timestamp
            if not workflow_data.update_time:
                workflow_data.update_time = timestamp
            return workflow_db.register_dl_in_sql(find_id=find_id, 
                                                   dl=workflow_data.model_dump(exclude_none=True))

    '''
    description: 从数据库获取workflow的canvas数据，支持draft和publish版本
    param {WorkflowId} workflow_id  支持draft和publish版本
    param {Session} db_session  数据库会话，可选
    return {*}
    '''
    @with_exception_handling
    def workflow_canvas(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[dict | None]:
        # 移除强制draft版本检查，允许加载指定版本
        return self.workflow_get(workflow_id, db_session)
    
    '''
    description: 从数据库获取space的workflow, 无论是单个wf还是多个，最终返回均为List
    param {dict} query_body  有2个键值workflow_id和space_id, 2者至少需要传入一个数值才能进行查找
    return {*}
    '''
    @with_exception_handling
    def workflow_list(self, query_body: SpaceAWPQuery, db_session: Session | None = None) -> ResponseModel[dict]:
        WorkflowRepository._check_workflow_is_draft(query_body.model_dump(), "workflow_list")
        # 获取分页参数
        page = int(query_body.page)
        page_size = int(query_body.page_size or 10)
        offset = (page - 1) * page_size
        return_range = [offset, page_size]

        with get_db_jw(db_session) as db:
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)

            # 构建基础查询条件
            find_id = {"space_id": query_body.space_id}
            find_id = WorkflowBaseDB.filter_invalid_keys(find_id)

            # 处理状态过滤
            status_filter = query_body.status_filter
            if status_filter and status_filter != 'all':
                find_id["status"] = status_filter

            # 构建排序条件
            sort_by = query_body.sort_by or "update_time"
            sort_order = query_body.sort_order or "desc"

            if sort_order == "desc":
                order_cols_desc = [sort_by]
                order_cols_asc = []
            else:
                order_cols_asc = [sort_by]
                order_cols_desc = []

            # 获取总数
            count_result = workflow_db.count_dl_in_sql(find_id=find_id)
            total = count_result.data if count_result.code == status.HTTP_200_OK else 0

            # 获取分页数据
            if total > 0:
                result = workflow_db.get_dl_in_sql(
                    find_id=find_id,
                    searchs=None,
                    order_cols_desc=order_cols_desc,
                    order_cols_asc=order_cols_asc,
                    return_range=return_range
                )

                if result.code == status.HTTP_200_OK and result.data:
                    workflow_list = result.data if isinstance(result.data, list) else [result.data]
                else:
                    workflow_list = []
            else:
                workflow_list = []

            # 计算总页数
            total_pages = max(1, (total + page_size - 1) // page_size)

            # 构建返回数据
            return_data = {
                "workflow_list": workflow_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get workflow list success",
                data=return_data
            )
    
    '''
    description: 更新数据库的draft版本workflow
    param {dict} workflow_data  待更新的workflow, 2个键值workflow_id和space_id至少需要有一个有值
    return {*}
    '''
    @with_exception_handling
    def workflow_save(self, workflow_data: dict, db_session: Session | None = None) -> ResponseModel[None]:
        WorkflowRepository._check_workflow_is_draft(workflow_data, "workflow_save")
        with get_db_jw(db_session) as db:
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            if not workflow_data:
                logger.debug(f"No workflow data to update: \ndata: {workflow_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message="No workflow data to update")
            find_id = {
                "workflow_id": get_val_from_dict(workflow_data, ["workflow_id"]),
                "space_id": get_val_from_dict(workflow_data, ["space_id", "spaceId"]),
            }
            timestamp = milliseconds()
            if "update_time" not in workflow_data:
                workflow_data["update_time"] = timestamp
            return workflow_db.update_dl_in_sql(find_id=find_id, update_dl=workflow_data)
   
    '''
    description: 从数据库删除draft版本workflow
    param {dict} query_body  有2个键值workflow_id和space_id, 2者至少需要传入一个数值才能进行查找
    return {*}
    '''
    @with_exception_handling
    def workflow_draft_delete(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[None]:
        WorkflowRepository._check_workflow_is_draft(workflow_id.model_dump(), "workflow_draft_delete")
        with get_db_jw(db_session) as db:
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            # 删除操作需要谨慎，所以这里要求find_id必须所有值都非空
            workflow_id = self.patch_workflow_id(workflow_id, db)
            return workflow_db.unregister_dl_in_sql(find_id=workflow_id.model_dump())
    
    '''
    description: 发布workflow，往workflow_publish数据库中创建一条数据
    param {dict} workflow_data
    return {*}
    '''
    @with_exception_handling
    def workflow_publish(self, publish_data: WorkflowPublishDBPd, db_session: Session | None = None) -> ResponseModel[None]:
        WorkflowRepository._check_workflow_is_publish(publish_data.model_dump(exclude_none=True), "workflow_publish")
        with get_db_jw(db_session) as db:
            workflow_publish_db = JiuwenBaseRepository(db, WorkflowPublishDB)
            if not publish_data:
                logger.debug(f"No workflow data to publish: \ndata: {publish_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                     message="No workflow data to publish")
            find_id = {
                "workflow_id": publish_data.workflow_id,
                "space_id": publish_data.space_id,
                "workflow_version": publish_data.workflow_version
            }
            find_id = WorkflowPublishDB.filter_invalid_keys(find_id)
            timestamp = milliseconds()
            if not publish_data.create_time:
                publish_data.create_time = timestamp
            if not publish_data.update_time:
                publish_data.update_time = timestamp
            # 写入publish表
            register_res = workflow_publish_db.register_dl_in_sql(
                find_id=find_id, dl=publish_data.model_dump(exclude_none=True))
            if register_res.code != status.HTTP_200_OK:
                return register_res
            
            # 更新draft表
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            update_dl = {
                "latest_publish_version": find_id.pop("workflow_version", None),
                "latest_publish_time": publish_data.create_time,
                "update_time": publish_data.create_time
            }
            update_res = workflow_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl)
            if update_res.code != status.HTTP_200_OK:
                return update_res
            return register_res

    '''
    description: 返回某个publish版本的workflow数据; 如果workflow_version='latest_publish_version', 返回最新的发布版本
    param {*} self
    param {dict} query_body
    return {*}
    '''
    @with_exception_handling
    def workflow_publish_get(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[dict | None]:
        WorkflowRepository._check_workflow_is_publish(workflow_id.model_dump(), "workflow_publish_get")
        return self.workflow_get(workflow_id, db_session=db_session)

    '''
    description: 删除workflow_publish的数据
    param {dict} query_body
    return {*}
    '''
    @with_exception_handling
    def workflow_publish_delete(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[None]:
        WorkflowRepository._check_workflow_is_publish(workflow_id.model_dump(), "workflow_publish_delete")
        with get_db_jw(db_session) as db:
            workflow_publish_db = JiuwenBaseRepository(db, WorkflowPublishDB)
            # 删除操作需要谨慎，所以这里要求find_id必须所有值都非空
            workflow_id = self.patch_workflow_id(workflow_id, db)
            find_id = workflow_id.model_dump()
            delete_res = workflow_publish_db.unregister_dl_in_sql(find_id=find_id)
            if delete_res.code != status.HTTP_200_OK:
                return delete_res
            # 更新draft表中的最新发布版本信息
            find_id.pop("workflow_version")
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            workflow_draft_res = workflow_db.get_dl_in_sql(find_id=find_id, return_first_item=True, 
                                                        return_declarativebase=True)
            if workflow_draft_res.code != status.HTTP_200_OK:
                return workflow_draft_res
            workflow_draft: WorkflowBaseDB = workflow_draft_res.data
            # 更新workflow draft中的发布变量
            workflow_draft.update_workflow_latest_publish_version()
            # 更新至数据库
            workflow_db.update(workflow_draft, {})
            return delete_res

    '''
    description: 获取某workflow的所有发布过的版本list
    param {dict} query_body
    return {dict}      ResponseModel的dict数据, 其中返回的数据保存在data中,
                        data=[{"workflow_version":..., "version_description":..., "create_time":...}, ...]
    '''
    @with_exception_handling
    def get_workflow_publish_list(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[list[dict] | None]:
        with get_db_jw(db_session) as db:
            workflow_publish_db = JiuwenBaseRepository(db, WorkflowPublishDB)
            find_id = {
                "workflow_id": workflow_id.workflow_id,
                "space_id": workflow_id.space_id,
            }
            cols_find = ["workflow_version", "version_description", "create_time"]
            db_res = workflow_publish_db.get_dl_in_sql_with_cols(find_id=find_id, 
                                                                cols_find=cols_find,
                                                                order_cols_desc=["workflow_version"]
                                                                )
            if not db_res or db_res.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=status.HTTP_404_NOT_FOUND,
                    message="No published versions found for this workflow"
                )
            return db_res

    @with_exception_handling
    def workflow_get(self, workflow_id: WorkflowId, db_session: Session | None = None) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            workflow_id = self.patch_workflow_id(workflow_id, db)
            if workflow_id.workflow_version == WorkflowBaseDB.__version_none__:
                workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)
            else:
                workflow_db = JiuwenBaseRepository(db, WorkflowPublishDB)
            return workflow_db.get_dl_in_sql(find_id=workflow_id.model_dump(), 
                                              return_first_item=True,
                                              order_cols_desc=['primary_id']
                                              )

    '''
    description: 搜索工作流，支持按名称、描述、标签进行搜索
    param {dict} search_params  搜索参数，包含：
        - space_id: 工作空间ID (必需)
        - search_term: 搜索关键词（支持名称、描述、标签）
        - status_filter: 状态过滤 ('running', 'stopped', 'scheduled', 'error', 'completed', 'all')
        - sort_by: 排序字段 ('name', 'create_time', 'update_time')
        - sort_order: 排序方向 ('asc', 'desc')
        - page: 页码 (默认1)
        - page_size: 每页大小 (默认10)
    return {*}
    '''
    @with_exception_handling
    def workflow_search(self, search_params: dict, db_session: Session | None = None) -> ResponseModel[dict | None]:
        """工作流搜索主入口 - 支持多维度搜索和过滤"""

        # DFX: 开始搜索 - 记录搜索参数和性能监控
        start_time = milliseconds()
        space_id = search_params.get("space_id")
        search_term = search_params.get("search_term", "").strip()

        logger.info(
            f"[DFX:WORKFLOW_SEARCH_START] space_id={space_id}, search_term='{search_term}', params={search_params}")

        # 1. 参数验证
        validation_result = WorkflowRepository._validate_search_params(search_params)
        if validation_result.code != status.HTTP_200_OK:
            logger.warning(f"[DFX:WORKFLOW_SEARCH_INVALID_PARAMS] {validation_result.message}")
            return validation_result

        with get_db_jw(db_session) as db:
            workflow_db = JiuwenBaseRepository(db, WorkflowBaseDB)

            # 2. 构建基础查询条件
            find_id = {"space_id": space_id}

            # 3. 处理状态过滤
            status_filter = search_params.get("status_filter")
            if status_filter and status_filter != 'all':
                find_id["status"] = status_filter
                logger.debug(f"[DFX:WORKFLOW_SEARCH_STATUS_FILTER] status={status_filter}")

            # 4. 构建搜索条件和标签搜索
            search_conditions, tag_workflow_ids = WorkflowRepository._build_search_conditions(db, search_term, space_id)

            # 5. 构建排序条件
            sort_by, sort_order, order_cols_asc, order_cols_desc = WorkflowRepository._build_sort_conditions(search_params)

            # 6. 构建分页条件
            page, page_size, offset, return_range = WorkflowRepository._build_pagination_conditions(search_params)

            # 7. 获取总数（用于分页）
            count_result = workflow_db.count_dl_in_sql_with_search(find_id=find_id, searchs=search_conditions)
            if count_result.code != status.HTTP_200_OK:
                logger.error(f"[DFX:WORKFLOW_SEARCH_COUNT_ERROR] {count_result.message}")
                return count_result

            total = count_result.data

            # 8. 执行主搜索（获取所有匹配的结果，不应用分页）
            search_result = WorkflowRepository._execute_main_search(
                workflow_db, find_id, search_conditions,
                order_cols_asc, order_cols_desc, [0, total]  # 获取所有结果
            )

            # 9. 合并搜索结果（包括标签搜索）
            workflow_list, total = WorkflowRepository._merge_search_results(
                search_result, tag_workflow_ids, workflow_db, find_id,
                order_cols_asc, order_cols_desc, total, search_term
            )

            # 10. 应用额外的标签过滤
            workflow_list, total = WorkflowRepository._apply_additional_tag_filter(
                search_params, space_id, workflow_list, total
            )

            # 11. 对合并后的结果进行最终排序
            workflow_list = WorkflowRepository._sort_merged_results(
                workflow_list, sort_by, sort_order
            )

            # 12. 应用最终分页
            paginated_workflow_list = WorkflowRepository._apply_final_pagination(
                workflow_list, page, page_size
            )

            # 13. 计算最终分页信息
            total_pages = max(1, (total + page_size - 1) // page_size)

            # 14. 构建返回数据
            return_data = {
                "workflow_list": paginated_workflow_list,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

            # DFX: 搜索完成 - 记录性能指标和结果统计
            execution_time = milliseconds() - start_time
            logger.info(f"[DFX:WORKFLOW_SEARCH_SUCCESS] space_id={space_id}, search_term='{search_term}', "
                                f"results={len(workflow_list)}, execution_time={execution_time}ms, total={total}")

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Search workflow success",
            data=return_data
        )

    @staticmethod
    def _validate_search_params(search_params: dict) -> ResponseModel:
        """验证搜索参数"""
        space_id = search_params.get("space_id")
        if not space_id:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="space_id is required"
            )

        # 验证状态过滤参数
        status_filter = search_params.get("status_filter")
        valid_statuses = ['running', 'stopped', 'scheduled', 'error', 'completed', 'all']
        if status_filter and status_filter not in valid_statuses:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid status_filter: {status_filter}. Valid values: {valid_statuses}"
            )

        # 验证排序字段
        sort_by = search_params.get("sort_by", "updated_time")
        valid_sort_fields = ['name', 'create_time', 'update_time']
        if sort_by not in valid_sort_fields:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid sort_by: {sort_by}. Valid values: {valid_sort_fields}"
            )

        # 验证排序方向
        sort_order = search_params.get("sort_order", "desc")
        if sort_order not in ['asc', 'desc']:
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message=f"Invalid sort_order: {sort_order}. Valid values: ['asc', 'desc']"
            )

        # 验证分页参数 - 使用公共验证方法
        try:
            page = int(search_params.get("page", 1))
            page_size = int(search_params.get("page_size", 10))
            # OPTIMIZATION: 使用公共的安全分页计算方法
            safe_page, safe_page_size, _ = WorkflowRepository._calculate_safe_pagination(0, page, page_size)

            # 检查原始参数是否在合理范围内
            if page != safe_page or page_size != safe_page_size:
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="page must be >= 1 and page_size must be between 1 and 100"
                )
        except (ValueError, TypeError):
            return ResponseModel(
                code=status.HTTP_400_BAD_REQUEST,
                message="page and page_size must be valid integers"
            )

        return ResponseModel(code=status.HTTP_200_OK, message="Validation successful")

    @staticmethod
    def _search_tags_by_terms_batch(db: Session, search_terms: list, space_id: str) -> set:
        """批量搜索多个搜索词的标签 - 性能优化版本"""
        if not search_terms:
            return set()

        try:
            from sqlalchemy import or_
            from openjiuwen_studio.models.tag import TagDB

            # OPTIMIZATION: 批量查询所有搜索词的标签，escape_like 防止 LIKE 通配符注入
            search_conditions = [
                TagDB.tag_name.ilike(f"%{escape_like(term)}%", escape="\\") for term in search_terms
            ]

            tag_results = db.execute(
                select(TagDB).where(
                    TagDB.space_id == space_id,
                    TagDB.is_active,
                    or_(*search_conditions)
                )
            ).fetchall()

            if not tag_results:
                logger.debug(f"[DFX:WORKFLOW_TAG_BATCH_SEARCH] No tags found for terms: {search_terms}")
                return set()

            # 提取所有标签ID
            tag_ids = [tag_row[0].primary_id for tag_row in tag_results]
            logger.debug(
                f"[DFX:WORKFLOW_TAG_BATCH_SEARCH] Found {len(tag_ids)} tags for {len(search_terms)} terms: {tag_ids}")

            if not tag_ids:
                return set()

            # 获取包含这些标签的工作流ID - 批量获取
            tag_result = workflow_tag_repository.find_workflows_by_tags({
                "space_id": space_id,
                "tag_ids": tag_ids
            })

            if tag_result.get("code") == status.HTTP_200_OK and tag_result.get("data"):
                workflow_ids = set(tag_result.get("data"))
                logger.info(
                    f"[DFX:WORKFLOW_TAG_BATCH_SEARCH] Found {len(workflow_ids)} workflows via batch search")
                return workflow_ids
            else:
                logger.warning(f"[DFX:WORKFLOW_TAG_BATCH_SEARCH] Batch tag search failed: {tag_result}")
                return set()

        except Exception as e:
            logger.error(f"[DFX:WORKFLOW_TAG_BATCH_SEARCH_ERROR]: {type(e).__name__}")
            return set()

    @staticmethod
    def _build_search_conditions(db: Session, search_term: str, space_id: str) -> tuple[dict, set]:
        """构建搜索条件和执行标签搜索"""
        search_conditions = {}
        tag_workflow_ids = set()

        if not search_term:
            return search_conditions, tag_workflow_ids

        # 将搜索词按空格拆分，每个词都是一个独立的搜索条件
        # 例如："翻译助手 旅游" 拆分为 ["翻译助手", "旅游"]
        search_terms = [term.strip() for term in search_term.split() if term.strip()]

        # 为每个搜索词在name和desc字段中搜索
        for term in search_terms:
            search_conditions[term] = ["name", "desc"]

        tag_workflow_ids = WorkflowRepository._search_tags_by_terms_batch(db, search_terms, space_id)

        return search_conditions, tag_workflow_ids

    @staticmethod
    def _build_sort_conditions(search_params: dict) -> tuple[str, str, list, list]:
        """构建排序条件"""
        sort_by = search_params.get("sort_by", "updated_time")
        sort_order = search_params.get("sort_order", "desc")

        order_cols_asc = []
        order_cols_desc = [sort_by] if sort_order == "desc" else []
        if sort_order == "asc":
            order_cols_asc = [sort_by]
            order_cols_desc = []

        logger.debug(f"[DFX:WORKFLOW_SORT] sort_by={sort_by}, sort_order={sort_order}")

        return sort_by, sort_order, order_cols_asc, order_cols_desc

    @staticmethod
    def _build_pagination_conditions(search_params: dict) -> tuple[int, int, int, list]:
        """构建分页条件"""
        page = int(search_params.get("page", 1))
        page_size = int(search_params.get("page_size", 10))
        offset = (page - 1) * page_size
        return_range = [offset, page_size]

        logger.debug(f"[DFX:WORKFLOW_PAGINATION] page={page}, page_size={page_size}")

        return page, page_size, offset, return_range

    @staticmethod
    def _execute_main_search(workflow_db, find_id: dict, search_conditions: dict,
                           order_cols_asc: list, order_cols_desc: list, return_range: list) -> ResponseModel:
        """执行主搜索"""
        try:
            result = workflow_db.get_dl_in_sql_with_cols(
                find_id=find_id,
                cols_find=None,  # 获取所有字段
                searchs=search_conditions if search_conditions else None,
                order_cols_asc=order_cols_asc,
                order_cols_desc=order_cols_desc,
                return_range=return_range
            )

            logger.debug(
                f"[DFX:WORKFLOW_MAIN_SEARCH] status={result.code}, results_count={len(result.data) if result.data else 0}")
            if result.data and len(result.data) == 1:
                result.data = result.data[0]
            return result

        except Exception as e:
            logger.error(f"[DFX:WORKFLOW_MAIN_SEARCH_ERROR] {str(e)}")
            return ResponseModel(
                code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=f"Main search execution error: {str(e)}"
            )

    @staticmethod
    def _merge_search_results(search_result: ResponseModel, tag_workflow_ids: set,
                            workflow_db, find_id: dict, order_cols_asc: list,
                            order_cols_desc: list, total: int, search_term: str) -> tuple[list, int]:
        """合并主搜索结果和标签搜索结果"""
        workflow_list = []

        # 处理主搜索结果
        if search_result.code == status.HTTP_200_OK and search_result.data:
            workflow_list = search_result.data if isinstance(search_result.data, list) else [
                                                             search_result.data] if search_result.data else []
            logger.debug(f"[DFX:WORKFLOW_MERGE] Main search returned {len(workflow_list)} results")

        # 如果没有标签搜索结果，直接返回主搜索结果
        if not tag_workflow_ids:
            return workflow_list, total

        # 合并标签搜索结果
        merged_list = WorkflowRepository._merge_tag_results(
            workflow_list, tag_workflow_ids, workflow_db, find_id,
            order_cols_asc, order_cols_desc, search_term
        )

        # 更新总数
        total = len(merged_list)
        logger.info(
            f"[DFX:WORKFLOW_MERGE] Merged {len(workflow_list)} main + {len(tag_workflow_ids)} tag = {total} unique results")

        return merged_list, total

    @staticmethod
    def _merge_tag_results(workflow_list: list, tag_workflow_ids: set, workflow_db,
                         find_id: dict, order_cols_asc: list, order_cols_desc: list, search_term: str) -> list:
        """合并标签搜索结果到主搜索结果 - 性能优化版本"""
        # 如果没有标签搜索结果或主结果已包含所有
        if not tag_workflow_ids:
            return workflow_list

        existing_ids = {workflow.get("workflow_id") for workflow in workflow_list}
        # 如果主搜索结果已经包含所有标签结果，直接返回
        if tag_workflow_ids.issubset(existing_ids):
            logger.debug(f"[DFX:WORKFLOW_MERGE_OPTIMIZED] All tag results already in main search")
            return workflow_list

        # 获取缺失的工作流
        missing_ids = tag_workflow_ids - existing_ids

        if missing_ids:
            logger.debug(
                f"[DFX:WORKFLOW_MERGE_OPTIMIZED] Fetching {len(missing_ids)} missing workflows from tag search")

            missing_workflows_result = workflow_db.get_dl_in_sql_with_cols(
                find_id={"workflow_id": list(missing_ids)},  # 直接使用ID查询
                cols_find=None,
                searchs=None,  # 缺失的工作流不需要重新搜索
                order_cols_asc=order_cols_asc,
                order_cols_desc=order_cols_desc,
                return_range=[0, len(missing_ids)]
            )

            tag_workflows = missing_workflows_result.data if missing_workflows_result.code == status.HTTP_200_OK and missing_workflows_result.data else []

            return WorkflowRepository._merge_workflow_lists_with_priority(
                workflow_list, tag_workflows,
                order_cols_asc[0] if order_cols_asc else order_cols_desc[0],
                'asc' if order_cols_asc else 'desc'
            )
        else:
            return workflow_list

    @staticmethod
    def _merge_workflow_lists_with_priority(primary_list: list, secondary_list: list,
                                          sort_by: str, sort_order: str) -> list:
        """公共方法 - 合并两个工作流列表并保持优先级"""
        # 使用字典快速查找，避免重复遍历
        primary_dict = {w.get("workflow_id"): w for w in primary_list}
        secondary_dict = {w.get("workflow_id"): w for w in secondary_list}

        # 合并结果 - 保持主列表优先级
        all_workflow_ids = set(primary_dict.keys()) | set(secondary_dict.keys())
        merged_list = [
            primary_dict.get(wid) or secondary_dict.get(wid)
            for wid in all_workflow_ids if primary_dict.get(wid) or secondary_dict.get(wid)
        ]

        return merged_list

    @staticmethod
    def _calculate_safe_pagination(total: int, page: int, page_size: int) -> tuple[int, int, int]:
        """OPTIMIZATION: 公共方法 - 安全计算分页参数"""
        safe_page = max(1, min(page, 1000))  # 限制最大页码
        safe_page_size = max(1, min(page_size, 100))  # 限制每页大小
        safe_total_pages = max(1, (total + safe_page_size - 1) // safe_page_size)

        return safe_page, safe_page_size, safe_total_pages

    @staticmethod
    def _apply_additional_tag_filter(search_params: dict, space_id: str,
                                   workflow_list: list, total: int) -> tuple[list, int]:
        """应用额外的标签过滤（通过tags参数指定）"""
        tags_filter = search_params.get("tags", [])

        if not tags_filter:
            return workflow_list, total

        logger.debug(f"[DFX:WORKFLOW_TAG_FILTER] Applying filter for tags: {len(tags_filter)} items")

        # 获取包含指定标签的工作流ID列表
        tag_result = workflow_tag_repository.find_workflows_by_tags({
            "space_id": space_id,
            "tag_ids": tags_filter
        })

        if tag_result.code == status.HTTP_200_OK and tag_result.data:
            filtered_workflow_ids = set(tag_result.data)
            # 过滤工作流列表，只保留包含指定标签的工作流
            filtered_list = [
                workflow for workflow in workflow_list
                if workflow.get("workflow_id") in filtered_workflow_ids
            ]
            filtered_total = len(filtered_list)

            logger.info(f"[DFX:WORKFLOW_TAG_FILTER] Filtered {total} -> {filtered_total} workflows")

            return filtered_list, filtered_total
        else:
            # 如果没有找到包含指定标签的工作流，返回空列表
            logger.debug(f"[DFX:WORKFLOW_TAG_FILTER] No workflows found for tags: {len(tags_filter)} items")
            return [], 0

    @staticmethod
    def _sort_merged_results(workflow_list: list, sort_by: str, sort_order: str) -> list:
        """对合并后的结果进行最终排序 - 性能优化版本"""
        if not workflow_list:
            return workflow_list

        # OPTIMIZATION: 早期返回 - 如果只有一个元素或已排序
        if len(workflow_list) <= 1:
            return workflow_list

        # OPTIMIZATION: 检查是否已经排序（避免重复排序）
        if len(workflow_list) <= 2:
            # 对于小数据集，简单检查是否已排序
            is_sorted = True
            reverse_check = sort_order == 'desc'
            for i in range(len(workflow_list) - 1):
                current = workflow_list[i].get(sort_by, 0)
                next_val = workflow_list[i + 1].get(sort_by, 0)

                # 转换为可比较的类型
                if sort_by in ['create_time', 'update_time']:
                    current = int(current) if current else 0
                    next_val = int(next_val) if next_val else 0
                else:
                    current = str(current) if current is not None else ''
                    next_val = str(next_val) if next_val is not None else ''

                if reverse_check and current < next_val:
                    is_sorted = False
                    break
                elif not reverse_check and current > next_val:
                    is_sorted = False
                    break

            if is_sorted:
                logger.debug(f"[DFX:WORKFLOW_SORT_OPTIMIZED] Already sorted, skipping sort")
                return workflow_list

        def sort_key(workflow):
            value = workflow.get(sort_by, 0)
            # 处理时间字段和字符串字段的不同排序方式
            if sort_by in ['create_time', 'update_time']:
                return int(value) if value else 0
            return str(value) if value is not None else ''

        # OPTIMIZATION: 使用更高效的排序方法
        reverse_order = sort_order == 'desc'

        # 对于大数据集，考虑使用Python内置的sorted（更稳定）
        if len(workflow_list) > 1000:
            workflow_list = sorted(workflow_list, key=sort_key, reverse=reverse_order)
        else:
            workflow_list.sort(key=sort_key, reverse=reverse_order)

        logger.debug(
            f"[DFX:WORKFLOW_SORT_OPTIMIZED] Sorted {len(workflow_list)} results by {sort_by} {sort_order}")
        return workflow_list

    @staticmethod
    def _apply_final_pagination(workflow_list: list, page: int, page_size: int) -> list:
        """应用最终分页"""
        if not workflow_list:
            return workflow_list

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # 确保索引不越界
        start_idx = max(0, min(start_idx, len(workflow_list)))
        end_idx = max(0, min(end_idx, len(workflow_list)))

        paginated_list = workflow_list[start_idx:end_idx]

        return paginated_list


workflow_repository = WorkflowRepository()