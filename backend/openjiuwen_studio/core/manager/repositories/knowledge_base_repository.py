from functools import wraps

from dataclasses import dataclass
from fastapi import status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.models import knowledge_base as kb_models
from openjiuwen_studio.models import knowledge_base_document as kb_doc_models
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.schemas.knowledge_base import KnowledgeBaseGet
from openjiuwen_studio.core.config import settings


@dataclass
class KBDetails:
    space_id: str  # 空间ID
    kb_id: str | None = None  # 知识库ID
    index_manager_type: str | None = None  # milvus or chroma


@dataclass
class KBDocument:
    kb: KBDetails  # Knowledge Base details
    doc_id: str | None = None  # 文档ID
    doc_status: str = None  # 新状态
    process_info: dict | None = None  # 处理信息（可选）
    index_name: str | None = None  #
    chunk_count: int | None = None  #


class KnowledgeBaseRepository:
    def __init__(self) -> None:
        pass

    def with_exception_handling(func_):
        @wraps(func_)
        def wrapper(self, *args, **kwargs):
            try:
                return func_(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: knowledge base db data preprocessing error")
                logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Error: knowledge base db data preprocessing error: {type(e).__name__}",
                )

        return wrapper

    """
    description: 创建知识库
    param {dict} kb_data  待创建的知识库数据
    return {*}
    """

    @with_exception_handling
    def knowledge_base_create(
        self, kb_data: dict, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)
            if not kb_data:
                logger.debug(f"No knowledge base data to register: \ndata: {kb_data}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST, message="No knowledge base data to register"
                )

            find_id = {
                "kb_id": kb_data["kb_id"],
            }
            timestamp = milliseconds()
            if "create_time" not in kb_data or not kb_data["create_time"]:
                kb_data["create_time"] = timestamp
            if "update_time" not in kb_data or not kb_data["update_time"]:
                kb_data["update_time"] = timestamp

            return kb_db.register_dl_in_sql(find_id=find_id, dl=kb_data)

    """
    description: 从数据库获取知识库
    param {KnowledgeBaseGet} kb_get  知识库查询条件
    return {*}
    """

    @with_exception_handling
    def knowledge_base_get(
        self, kb_get: KnowledgeBaseGet, db_session: Session | None = None
    ) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)
            find_id = {
                "space_id": kb_get.space_id,
                "kb_id": kb_get.kb_id,
                "index_manager_type": kb_get.index_manager_type,
            }
            if kb_get.index_manager_type:
                find_id["index_manager_type"] = kb_get.index_manager_type
            return kb_db.get_dl_in_sql(find_id=find_id, return_first_item=True)

    """
    description: 删除知识库
    param {KnowledgeBaseGet} kb_get  知识库查询条件
    return {*}
    """

    @with_exception_handling
    def knowledge_base_delete(
        self, kb_get: KnowledgeBaseGet, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)
            find_id = {
                "space_id": kb_get.space_id,
                "kb_id": kb_get.kb_id,
            }
            return kb_db.unregister_dl_in_sql(find_id=find_id)

    """
    description: 检查知识库名称是否已存在
    param {str} space_id  空间ID
    param {str} name  知识库名称
    param {str} exclude_kb_id  排除的知识库ID（用于更新时排除当前知识库）
    return {ResponseModel[bool]}  True表示名称已存在，False表示不存在
    """

    @with_exception_handling
    def knowledge_base_check_name_exists(
        self,
        space_id: str,
        name: str,
        exclude_kb_id: str | None = None,
        db_session: Session | None = None,
    ) -> ResponseModel[bool]:
        """检查知识库名称是否已存在（区分大小写）"""
        with get_db_jw(db_session) as db:
            # SQLite 默认区分大小写，MySQL 需要用 BINARY
            if settings.db_type.lower() == "sqlite":
                query = db.query(kb_models.KnowledgeBaseDB).filter(
                    kb_models.KnowledgeBaseDB.space_id == space_id,
                    kb_models.KnowledgeBaseDB.name == name,
                )
            else:
                query = db.query(kb_models.KnowledgeBaseDB).filter(
                    kb_models.KnowledgeBaseDB.space_id == space_id,
                    func.binary(kb_models.KnowledgeBaseDB.name) == func.binary(name),
                )
            if exclude_kb_id:
                query = query.filter(kb_models.KnowledgeBaseDB.kb_id != exclude_kb_id)

            exists = db.query(query.exists()).scalar()
            return ResponseModel(code=status.HTTP_200_OK, message="Success", data=exists)

    """
    description: 更新知识库
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    param {str} name  新的名字
    param {str} description  新的描述
    return {*}
    """

    @with_exception_handling
    def knowledge_base_update(
        self,
        kb: KBDetails,
        name: str,
        description: str | None,
        db_session: Session | None = None,
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)
            find_id = {
                "space_id": kb.space_id,
                "kb_id": kb.kb_id,
            }

            if kb.index_manager_type:
                find_id["index_manager_type"] = kb.index_manager_type

            # 由于 update_dl_in_sql 使用 exclude_invalid=True 会过滤 None 和空字符串，
            # 如果 description 是 None 或空字符串，我们需要直接使用 SQLAlchemy 的 update 语句
            if description is None or description == "":
                from sqlalchemy import update as sql_update

                stmt = (
                    sql_update(kb_models.KnowledgeBaseDB)
                    .values(
                        name=name,
                        description=None if description is None else "",
                        update_time=milliseconds(),
                    )
                    .where(
                        kb_models.KnowledgeBaseDB.space_id == kb.space_id,
                        kb_models.KnowledgeBaseDB.kb_id == kb.kb_id,
                        kb_models.KnowledgeBaseDB.index_manager_type == kb.index_manager_type,
                    )
                )
                db.execute(stmt)
                db.commit()
                return ResponseModel(
                    code=status.HTTP_200_OK, message="Knowledge base updated successfully"
                )
            else:
                # 如果 description 有值，使用正常的更新流程
                update_data = {
                    "name": name,
                    "description": description,
                    "update_time": milliseconds(),
                }
                return kb_db.update_dl_in_sql(find_id=find_id, update_dl=update_data)

    """
    description: 创建知识库文档
    param {dict} doc_data  待创建的文档数据
    return {*}
    """

    @with_exception_handling
    def document_create(
        self, doc_data: dict, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)
            if not doc_data:
                logger.debug(f"No document data to register: \ndata: {doc_data}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST, message="No document data to register"
                )

            find_id = {
                "doc_id": doc_data["doc_id"],
            }
            timestamp = milliseconds()
            if "create_time" not in doc_data or not doc_data["create_time"]:
                doc_data["create_time"] = timestamp
            if "update_time" not in doc_data or not doc_data["update_time"]:
                doc_data["update_time"] = timestamp

            return doc_db.register_dl_in_sql(find_id=find_id, dl=doc_data)

    """
    description: 从数据库获取知识库文档
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    param {str} doc_id  文档ID
    return {*}
    """

    @with_exception_handling
    def document_get(
        self,
        kbdoc: KBDocument,
        db_session: Session | None = None,
    ) -> ResponseModel[dict | None]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)
            find_id = {
                "space_id": kbdoc.kb.space_id,
                "kb_id": kbdoc.kb.kb_id,
                "doc_id": kbdoc.doc_id,
            }
            if kbdoc.kb.index_manager_type:
                find_id["index_manager_type"] = kbdoc.kb.index_manager_type
            return doc_db.get_dl_in_sql(find_id=find_id, return_first_item=True)

    """
    description: 删除知识库文档
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    param {str} doc_id  文档ID
    return {*}
    """

    @with_exception_handling
    def document_delete(
        self, kbdoc: KBDocument, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)
            find_id = {
                "space_id": kbdoc.kb.space_id,
                "kb_id": kbdoc.kb.kb_id,
                "doc_id": kbdoc.doc_id,
            }
            if kbdoc.kb.index_manager_type:
                find_id["index_manager_type"] = kbdoc.kb.index_manager_type
            return doc_db.unregister_dl_in_sql(find_id=find_id)

    @with_exception_handling
    def document_update_status(
        self, kbdoc: KBDocument, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)
            find_id = {
                "space_id": kbdoc.kb.space_id,
                "kb_id": kbdoc.kb.kb_id,
                "doc_id": kbdoc.doc_id,
            }
            if kbdoc.kb.index_manager_type:
                find_id["index_manager_type"] = kbdoc.kb.index_manager_type

            update_data = {
                "status": kbdoc.doc_status,
                "update_time": milliseconds(),
            }

            if kbdoc.process_info is not None:
                update_data["process_info"] = kbdoc.process_info

            # 如果提供了索引信息，一起更新
            if kbdoc.index_name is not None:
                update_data["index_id"] = None
                update_data["index_name"] = kbdoc.index_name
                update_data["indexed_time"] = milliseconds()

            if kbdoc.chunk_count is not None:
                update_data["chunk_count"] = kbdoc.chunk_count

            return doc_db.update_dl_in_sql(find_id=find_id, update_dl=update_data)

    """
    description: 更新文档信息（当前只支持更新文档名称）
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    param {str} doc_id  文档ID
    param {str} name  新的文档名称
    return {*}
    """

    @with_exception_handling
    def document_update(
        self, kbdoc: KBDocument, name: str, db_session: Session | None = None
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)
            find_id = {
                "space_id": kbdoc.kb.space_id,
                "kb_id": kbdoc.kb.kb_id,
                "doc_id": kbdoc.doc_id,
            }
            if kbdoc.kb.index_manager_type:
                find_id["index_manager_type"] = kbdoc.kb.index_manager_type
            update_data = {
                "name": name,
                "update_time": milliseconds(),
            }
            return doc_db.update_dl_in_sql(find_id=find_id, update_dl=update_data)

    """
    description: 查询知识库（查询词出现在名称或描述中，支持分页）
    param {str} space_id  空间ID
    param {str} query  查询词（查询词完整出现在知识库名称或描述中，大小写不敏感）
    param {int} page  页码，从1开始
    param {int} page_size  每页大小
    return {*}
    """

    @with_exception_handling
    def knowledge_base_search(
        self,
        space_id: str,
        query: str,
        page: int = 1,
        page_size: int = 10,
        db_session: Session | None = None,
    ) -> ResponseModel[dict]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)

            # 构建查询条件：查询词完整出现在名称或描述中（大小写不敏感）
            # 使用 func.lower() 实现大小写不敏感匹配
            query_lower = query.lower()
            search_conditions = or_(
                func.lower(kb_models.KnowledgeBaseDB.name).contains(query_lower),
                func.lower(kb_models.KnowledgeBaseDB.description).contains(query_lower),
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
            count_result = kb_db.get_dl_in_sql(
                find_id=find_id,
                other_sqlalchemy_limitations=[search_conditions],
                return_first_item=False,
            )

            # 如果返回 404 且消息是 "Data not found."，视为空结果
            if (
                count_result.code == status.HTTP_404_NOT_FOUND
                and count_result.message == "Data not found."
            ):
                total = 0
            elif count_result.code != status.HTTP_200_OK:
                return count_result
            else:
                total = len(count_result.data) if count_result.data else 0

            # 获取分页数据
            search_result = kb_db.get_dl_in_sql(
                find_id=find_id,
                other_sqlalchemy_limitations=[search_conditions],
                return_range=return_range,
                return_first_item=False,
            )

            # 如果返回 404 且消息是 "Data not found."，视为空结果
            if (
                search_result.code == status.HTTP_404_NOT_FOUND
                and search_result.message == "Data not found."
            ):
                knowledge_bases = []
            elif search_result.code != status.HTTP_200_OK:
                return search_result
            else:
                knowledge_bases = search_result.data or []

            # 计算总页数
            total_pages = max(1, (total + page_size - 1) // page_size) if total > 0 else 1

            # 返回分页结果
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Search knowledge bases successfully",
                data={
                    "knowledge_bases": knowledge_bases,
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": total_pages,
                },
            )

    """
    description: 获取知识库列表（支持分页）
    param {str} space_id  空间ID
    param {int} page  页码，从1开始
    param {int} size  每页大小
    return {*}
    """

    @with_exception_handling
    def knowledge_base_list(
        self,
        kb: KBDetails,
        page: int = 1,
        size: int = 10,
        db_session: Session | None = None,
    ) -> ResponseModel[dict]:
        with get_db_jw(db_session) as db:
            kb_db = JiuwenBaseRepository(db, kb_models.KnowledgeBaseDB)

            # 构建查询条件
            find_id = {
                "space_id": kb.space_id,
            }
            if kb.index_manager_type:
                find_id["index_manager_type"] = kb.index_manager_type
            # 计算分页参数
            offset = (page - 1) * size

            # 查询总数
            count_result = kb_db.get_dl_in_sql(find_id=find_id, return_first_item=False)
            if count_result.code == status.HTTP_404_NOT_FOUND:
                # 空数据是正常情况，返回空列表
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Get knowledge base list success",
                    data={"items": [], "total": 0},
                )
            elif count_result.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=count_result.code,
                    message=count_result.message,
                    data={"items": [], "total": 0},
                )

            total = len(count_result.data) if count_result.data else 0

            # 查询分页数据
            query = (
                db.query(kb_models.KnowledgeBaseDB)
                .filter(kb_models.KnowledgeBaseDB.space_id == kb.space_id)
                .filter(kb_models.KnowledgeBaseDB.index_manager_type == kb.index_manager_type)
                .order_by(kb_models.KnowledgeBaseDB.create_time.desc())
                .offset(offset)
                .limit(size)
            )

            kb_list = query.all()

            # 转换为字典列表
            items = []
            for kb in kb_list:
                items.append(
                    {
                        "kb_id": kb.kb_id,
                        "space_id": kb.space_id,
                        "name": kb.name,
                        "description": kb.description,
                        "embedding_model_config_id": kb.embedding_model_config_id,
                        "config": kb.config,
                        "create_time": kb.create_time,
                        "update_time": kb.update_time,
                    }
                )

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get knowledge base list success",
                data={"items": items, "total": total},
            )

    """
    description: 获取知识库文档列表（支持分页）
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    param {int} page  页码，从1开始
    param {int} size  每页大小
    return {*}
    """

    @with_exception_handling
    def document_list(
        self,
        kbdoc: KBDocument,
        page: int = 1,
        size: int = 10,
        db_session: Session | None = None,
    ) -> ResponseModel[dict]:
        with get_db_jw(db_session) as db:
            doc_db = JiuwenBaseRepository(db, kb_doc_models.KnowledgeBaseDocumentDB)

            # 构建查询条件
            find_id = {
                "space_id": kbdoc.kb.space_id,
                "kb_id": kbdoc.kb.kb_id,
            }

            # 如果传入 index_manager_type，则将其加入筛选条件（用于 count 和列表查询）
            if kbdoc.kb.index_manager_type:
                find_id["index_manager_type"] = kbdoc.kb.index_manager_type

            # 计算分页参数
            offset = (page - 1) * size

            # 查询总数
            count_result = doc_db.get_dl_in_sql(find_id=find_id, return_first_item=False)
            if count_result.code == status.HTTP_404_NOT_FOUND:
                # 空数据是正常情况，返回空列表
                return ResponseModel(
                    code=status.HTTP_200_OK,
                    message="Get document list success",
                    data={"items": [], "total": 0, "page": page, "size": size},
                )
            elif count_result.code != status.HTTP_200_OK:
                return ResponseModel(
                    code=count_result.code,
                    message=count_result.message,
                    data={"items": [], "total": 0, "page": page, "size": size},
                )

            total = len(count_result.data) if count_result.data else 0

            query = db.query(kb_doc_models.KnowledgeBaseDocumentDB).filter(
                kb_doc_models.KnowledgeBaseDocumentDB.space_id == kbdoc.kb.space_id,
                kb_doc_models.KnowledgeBaseDocumentDB.kb_id == kbdoc.kb.kb_id,
            )
            if kbdoc.kb.index_manager_type:
                query = query.filter(
                    kb_doc_models.KnowledgeBaseDocumentDB.index_manager_type
                    == kbdoc.kb.index_manager_type
                )
            query = (
                query.order_by(kb_doc_models.KnowledgeBaseDocumentDB.create_time.desc())
                .offset(offset)
                .limit(size)
            )

            doc_list = query.all()

            # 转换为字典列表
            items = []
            for doc in doc_list:
                items.append(
                    {
                        "doc_id": doc.doc_id,
                        "name": doc.name,
                        "status": doc.status,
                        "process_info": doc.process_info if doc.process_info else {},
                        "create_time": doc.create_time,
                        "update_time": doc.update_time,
                    }
                )

            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get document list success",
                data={"items": items, "total": total, "page": page, "size": size},
            )

    """
    description: 检查知识库是否有图增强构建的文档
    param {str} space_id  空间ID
    param {str} kb_id  知识库ID
    return {bool} 是否有图增强文档
    """

    @with_exception_handling
    def has_graph_enhancement_documents(
        self, space_id: str, kb_id: str, db_session: Session | None = None
    ) -> bool:
        """检查知识库中是否有图增强构建的文档"""
        with get_db_jw(db_session) as db:
            # 查询该知识库下所有已索引的文档
            docs = (
                db.query(kb_doc_models.KnowledgeBaseDocumentDB)
                .filter(
                    kb_doc_models.KnowledgeBaseDocumentDB.space_id == space_id,
                    kb_doc_models.KnowledgeBaseDocumentDB.kb_id == kb_id,
                    kb_doc_models.KnowledgeBaseDocumentDB.status == "indexed",
                )
                .all()
            )

            # 检查是否有文档使用了图增强
            for doc in docs:
                if doc.process_info and isinstance(doc.process_info, dict):
                    indexing_strategy = doc.process_info.get("indexing_strategy")
                    if isinstance(indexing_strategy, dict):
                        enable_graph_enhancement = indexing_strategy.get(
                            "enable_graph_enhancement", False
                        )
                        if enable_graph_enhancement:
                            return True

            return False


# 创建全局实例
knowledge_base_repository = KnowledgeBaseRepository()
