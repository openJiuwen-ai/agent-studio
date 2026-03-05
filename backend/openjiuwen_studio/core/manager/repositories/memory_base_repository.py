from functools import wraps

from fastapi import status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from openjiuwen_studio.core.database import milliseconds
from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import escape_like, get_db_jw
from openjiuwen_studio.models import memory_base as mb_models
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.memory_base import MemoryBaseGet
from openjiuwen_studio.core.config import settings


class MemoryBaseRepository:
    def __init__(self) -> None:
        pass

    @staticmethod
    def with_exception_handling(func_):
        @wraps(func_)
        def wrapper(self, *args, **kwargs):
            try:
                return func_(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: memory base db data preprocessing error")
                logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Error: memory base db data preprocessing error: {type(e).__name__}"
                )

        return wrapper

    '''
    description: 创建记忆库
    param {dict} mb_data  待创建的记忆库数据
    return {*}
    '''

    @with_exception_handling
    def memory_base_create(self, mb_data: dict, db_session: Session | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)
            if not mb_data:
                logger.debug(f"No memory base data to register: \ndata: {mb_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No memory base data to register")

            find_id = {
                "mdb_id": mb_data["mdb_id"],
            }
            timestamp = milliseconds()
            if "create_time" not in mb_data or not mb_data["create_time"]:
                mb_data["create_time"] = timestamp
            if "update_time" not in mb_data or not mb_data["update_time"]:
                mb_data["update_time"] = timestamp

            return mb_db.register_dl_in_sql(find_id=find_id, dl=mb_data)

    '''
    description: 从数据库获取记忆库
    param {MemoryBaseGet} mb_get  记忆库查询条件
    return {*}
    '''

    @with_exception_handling
    def memory_base_get(
        self, mb_get: MemoryBaseGet, db_session: Session | None = None
    ) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)
            find_id = {
                "space_id": mb_get.space_id,
                "mdb_id": mb_get.mdb_id,
            }
            return mb_db.get_dl_in_sql(find_id=find_id, return_first_item=True)

    '''
    description: 根据数据库id从数据库获取记忆库
    param  mdb_id  记忆库查询条件
    return {*}
    '''

    @with_exception_handling
    def memory_base_get_by_id(
        self, mdb_id: str, db_session: Session | None = None
    ) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)
            find_id = {
                "mdb_id": mdb_id,
            }
            return mb_db.get_dl_in_sql(find_id=find_id, return_first_item=True)

    '''
    description: 删除记忆库
    param {MemoryBaseGet} mb_get  记忆库查询条件
    return {*}
    '''

    @with_exception_handling
    def memory_base_delete(self, mb_get: MemoryBaseGet, db_session: Session | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)
            find_id = {
                "space_id": mb_get.space_id,
                "mdb_id": mb_get.mdb_id,
            }
            return mb_db.unregister_dl_in_sql(find_id=find_id)

    '''
    description: 检查记忆库名称是否已存在
    param {str} space_id  空间ID
    param {str} name  记忆库名称
    param {str} exclude_mdb_id  排除的记忆库ID（用于更新时排除当前记忆库）
    return {ResponseModel[bool]}  True表示名称已存在，False表示不存在
    '''

    @with_exception_handling
    def memory_base_check_name_exists(
        self,
        space_id: str,
        name: str,
        exclude_mdb_id: str | None = None,
        db_session: Session | None = None,
    ) -> ResponseModel[bool]:
        with get_db_jw(db_session) as db:
            query = db.query(mb_models.MemoryBaseDB).filter(
                mb_models.MemoryBaseDB.space_id == space_id
            )

            # 根据数据库类型选择不同的比较方式
            if settings.db_type.lower() == "sqlite":
                # SQLite 默认不区分大小写，所以需要特殊处理
                query = query.filter(func.lower(mb_models.MemoryBaseDB.name) == func.lower(name))
            else:
                # MySQL 等数据库默认区分大小写
                query = query.filter(mb_models.MemoryBaseDB.name == name)

            # 如果提供了排除的记忆库ID，则排除该记录
            if exclude_mdb_id:
                query = query.filter(mb_models.MemoryBaseDB.mdb_id != exclude_mdb_id)

            # 检查是否存在匹配的记录
            exists = db.query(query.exists()).scalar()

            return ResponseModel(code=status.HTTP_200_OK, message="Success", data=exists)

    '''
    description: 更新记忆库
    param {dict} mb_data  待更新的记忆库数据
    param {MemoryBaseGet} mb_get  记忆库查询条件
    return {*}
    '''

    @with_exception_handling
    def memory_base_update(self, mb_data: dict, mb_get: MemoryBaseGet, db_session: Session | None = None) -> \
        ResponseModel[None]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)
            if not mb_data:
                logger.debug(f"No memory base data to update: \ndata: {mb_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, message="No memory base data to update")

            # 更新时间戳
            mb_data["update_time"] = milliseconds()

            find_id = {
                "space_id": mb_get.space_id,
                "mdb_id": mb_get.mdb_id,
            }

            return mb_db.update_dl_in_sql(find_id=find_id, update_dl=mb_data)

    '''
    description: 获取记忆库列表（支持分页）
    param {str} space_id  空间ID
    param {int} page  页码，从1开始
    param {int} size  每页大小
    return {*}
    '''

    @with_exception_handling
    def memory_base_list(
        self,
        space_id: str,
        page: int = 1,
        size: int = 10,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)

            # 构建查询条件
            find_id = {
                "space_id": space_id,
            }

            # 计算分页参数
            offset = (page - 1) * size

            # 查询总数
            count_result = mb_db.get_dl_in_sql(find_id=find_id, return_first_item=False)
            if count_result.code == status.HTTP_404_NOT_FOUND:
                # 空数据是正常情况，返回空列表
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Get memory base list success",
                    data={"items": [], "total": 0}
                )
            elif count_result.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=count_result.code,
                    message=count_result.message,
                    data={"items": [], "total": 0}
                )

            total = len(count_result.data) if count_result.data else 0

            # 查询分页数据
            query = db.query(mb_models.MemoryBaseDB).filter(
                mb_models.MemoryBaseDB.space_id == space_id
            ).order_by(
                mb_models.MemoryBaseDB.update_time.desc()
            ).offset(offset).limit(size)

            mb_list = query.all()

            # 转换为字典列表
            items = []
            for mb in mb_list:
                items.append({
                    "mdb_id": mb.mdb_id,
                    "space_id": mb.space_id,
                    "name": mb.name,
                    "description": mb.description,
                    "embedding_model_config_id": mb.embedding_model_config_id,
                    "llm_model_config_id": mb.llm_model_config_id,
                    "create_time": mb.create_time,
                    "update_time": mb.update_time,
                })

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get memory base list success",
                data={
                    "items": items,
                    "total": total
                }
            )

    '''
    description: 搜索记忆库（支持按名称和描述模糊查询，分页）
    param {str} space_id  空间ID
    param {str} query  查询词（查询词完整出现在记忆库名称或描述中，大小写不敏感）
    param {int} page  页码，从1开始
    param {int} page_size  每页大小，最大100
    return {*}
    '''

    @with_exception_handling
    def memory_base_search(
        self,
        space_id: str,
        query: str,
        page: int = 1,
        page_size: int = 10,
        db_session: Session | None = None
    ) -> ResponseModel[dict]:
        with get_db_jw(db_session) as db:
            mb_db = JiuwenBaseRepository(db, mb_models.MemoryBaseDB)

            # 构建查询条件：查询词完整出现在名称或描述中（大小写不敏感）
            # 使用 func.lower() + ilike 实现大小写不敏感匹配，escape_like 防止 LIKE 通配符注入
            query_lower = query.lower()
            escaped_query = escape_like(query_lower)
            search_conditions = or_(
                func.lower(mb_models.MemoryBaseDB.name).ilike(f"%{escaped_query}%", escape="\\"),
                func.lower(mb_models.MemoryBaseDB.description).ilike(f"%{escaped_query}%", escape="\\")
            )

            # 构建基础查询条件
            find_id = {
                "space_id": space_id,
            }

            # 验证分页参数
            page = max(1, page)
            page_size = max(1, min(page_size, 100))  # 限制最大100

            # 计算 offset 和 limit
            offset = (page - 1) * page_size
            return_range = [offset, page_size]

            # 先获取总数（不分页）
            count_result = mb_db.get_dl_in_sql(
                find_id=find_id,
                other_sqlalchemy_limitations=[search_conditions],
                return_first_item=False
            )

            # 如果返回 404 且消息是 "Data not found."，视为空结果
            if count_result.code == status.HTTP_404_NOT_FOUND and count_result.message == "Data not found.":
                total = 0
            elif count_result.code != status.HTTP_200_OK:
                return count_result
            else:
                total = len(count_result.data) if count_result.data else 0

            # 获取分页数据
            search_result = mb_db.get_dl_in_sql(
                find_id=find_id,
                other_sqlalchemy_limitations=[search_conditions],
                return_range=return_range,
                return_first_item=False,
                order_cols_desc=["update_time"]  # 添加排序参数
            )

            # 如果返回 404 且消息是 "Data not found."，视为空结果
            if search_result.code == status.HTTP_404_NOT_FOUND and search_result.message == "Data not found.":
                memory_bases = []
            elif search_result.code != status.HTTP_200_OK:
                return search_result
            else:
                memory_bases = search_result.data or []

            # 计算总页数
            total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

            # 返回分页结果
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Search memory bases successfully",
                data={
                    "memory_bases": memory_bases,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages
                }
            )

# 创建全局实例
memory_base_repository = MemoryBaseRepository()