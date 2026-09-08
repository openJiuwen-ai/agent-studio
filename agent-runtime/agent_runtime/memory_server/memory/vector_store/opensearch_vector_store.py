"""
OpenSearch 向量存储实现
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from memory_service.exception.error_code import ErrorCode
from memory_service.exception.memory_service_exception import MemoryServiceException
from memory_service.i18n.i18n_constant import I18nMessageCode
from memory_service.i18n.i18n_util import i18n_util
from memory_service.memory.vector_store.base_vector_store import BaseVectorStore
from memory_service.memory.vector_store.base_vector_store import ListDocsResult
from memory_service.memory.vector_store.base_vector_store import SearchDocsItem
from memory_service.memory.vector_store.opensearch_vector_index_config import (
    OpenSearchVectorIndexConfig,
)
from memory_service.utils.async_opensearch_util import get_async_opensearch_util
from opensearchpy import NotFoundError

logger = logging.getLogger(__name__)


class OpenSearchVectorStore(BaseVectorStore):
    """
    OpenSearch 向量存储实现

    基于 OpenSearch 实现的向量存储服务，支持集合管理、文档插入、向量搜索等功能
    """

    def __init__(self):
        """初始化 OpenSearch 向量存储实例"""
        self._opensearch_client = get_async_opensearch_util()

    async def create_collection(self, collection_name: str) -> None:
        try:
            # 构建 OpenSearch 索引映射（使用统一的配置）
            index_mapping = OpenSearchVectorIndexConfig.build_full_mapping()

            # 创建索引
            success = await self._opensearch_client.create_index(
                collection_name, index_mapping
            )
            if not success:
                raise Exception(f"Failed to create collection '{collection_name}'")

            logger.info(f"Collection '{collection_name}' created successfully")

        except Exception as e:
            logger.error(
                f"Create collection '{collection_name}' failed in openSearch: {e}",
                exc_info=True,
            )

    async def delete_collection(
        self,
        collection_name: str,
        **kwargs: Any,
    ) -> None:
        try:
            client = self._opensearch_client
            # 检查索引是否存在
            exists = await client.index_exists(collection_name)
            if not exists:
                logger.info(f"Collection '{collection_name}' does not exist")
                return

            # 删除索引
            success = await client.delete_index(collection_name)
            if not success:
                raise Exception(f"Failed to delete collection '{collection_name}'")

            logger.info(f"Collection '{collection_name}' deleted successfully")
        except Exception as e:
            logger.error(
                f"Delete collection '{collection_name}' failed: {e}", exc_info=True
            )

    async def collection_exists(self, collection_name: str) -> bool:
        """
        检查集合是否存在
        """
        try:
            exists = await self._opensearch_client.index_exists(collection_name)
            return exists
        except Exception as e:
            logger.error(
                f"Check collection existence '{collection_name}' failed: {e}",
                exc_info=True,
            )
            return False

    async def add_docs(self, collection_name: str, docs: List[Dict[str, Any]]) -> None:
        """
        向集合中添加文档
        """
        try:
            if not docs:
                logger.info("No documents to add")
                return

            batch_size = 100

            # 分批处理文档
            for i in range(0, len(docs), batch_size):
                batch_docs = docs[i : i + batch_size]
                success = await self._opensearch_client.insert_data(
                    collection_name, batch_docs
                )
                if not success:
                    raise Exception(
                        f"Failed to insert batch documents into collection {collection_name}"
                    )

            logger.info(
                f"Successfully inserted {len(docs)} documents into collection {collection_name}"
            )

        except Exception as e:
            logger.error(
                f"Add documents to collection {collection_name} failed: {e}",
                exc_info=True,
            )
            raise MemoryServiceException(
                error_code=ErrorCode.VECTOR_STORE_ADD_DOCUMENT_FAILED,
                error_message=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_ADD_DOCUMENT_FAILED_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_ADD_DOCUMENT_FAILED_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_ADD_DOCUMENT_FAILED_SUGGESTION
                ),
            )

    async def delete_docs_by_filters(
        self,
        collection_name: str,
        filters: Dict[str, Any],
    ) -> None:
        try:
            # 使用统一的 batch_size
            batch_size = 500  # 批量查询和删除的统一大小
            short_delay = 0.01  # 批量操作间的小延迟
            wait_delete_delay = 0.05  # 等待删除完成的小延迟

            total_deleted = 0

            logger.info(
                f"Starting to delete documents from collection '{collection_name}' by filters in openSearch"
            )

            last_query_ids = []
            while True:
                # 每次都从 offset=0 开始查询，因为上一批已经删除了
                query_result = await self.list_docs(
                    collection_name, filters=filters, limit=batch_size, offset=0
                )

                # 提取文档 ID
                doc_ids = [doc.id for doc in query_result.data]

                if not doc_ids:
                    # 没有更多文档，结束删除
                    break

                if last_query_ids and doc_ids[0] == last_query_ids[0]:
                    # 如果查询出来的结果和上次查询结果一致，说明还没有完成删除，等到一段时间后再重新查询
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(
                            f"Last query {len(last_query_ids)} document for delete not finished, wait for delete finished."
                        )
                    await asyncio.sleep(wait_delete_delay)
                    continue

                last_query_ids = doc_ids.copy()
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"Found {len(doc_ids)} documents to delete in openSearch")

                # 直接删除本批次的文档
                try:
                    await self.delete_docs_by_ids(collection_name, doc_ids)
                    total_deleted += len(doc_ids)
                    if logger.isEnabledFor(logging.INFO):
                        logger.info(
                            f"BATCH: Deleted {len(doc_ids)} documents in openSearch (total: {total_deleted})"
                        )

                    # 添加短暂延迟，避免系统负载过高
                    await asyncio.sleep(short_delay)

                except Exception as batch_error:
                    logger.error(
                        f"Failed to delete batch in openSearch: {batch_error}",
                        exc_info=True,
                    )
                    raise batch_error

            logger.info(
                f"Successfully deleted {total_deleted} documents from collection '{collection_name}' by filters in openSearch"
            )

        except Exception as e:
            logger.error(
                f"Delete documents by filters from collection '{collection_name}' in openSearch failed: {e}",
                exc_info=True,
            )
            raise MemoryServiceException(
                error_code=ErrorCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED,
                error_message=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_SUGGESTION
                ),
            )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        vector_field: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchDocsItem]:
        try:
            # 如果未指定向量字段，使用预定义的字段名
            if vector_field is None:
                vector_field = self.get_vector_field_name()

            # 构建搜索参数
            search_kwargs = {
                "size": top_k,
                "min_score": 0.0,
                "filter_query": self._build_filters(filters) if filters else None,
                "k": top_k,
            }

            # 执行向量搜索
            results = await self._opensearch_client.search_data(
                collection_name, query_vector, vector_field, **search_kwargs
            )

            # 转换为SearchDocsResult格式
            search_results = []
            for hit in results:
                # 创建SearchDocsResult实例，id保持为字符串类型
                search_result = SearchDocsItem(
                    id=str(hit["_id"]),  # 始终保持为字符串类型
                    score=float(hit["_score"]) if hit["_score"] is not None else 0.0,
                    data=hit["_source"],
                )
                search_results.append(search_result)

            logger.info(
                f"Vector search in collection '{collection_name}' executed successfully, found {len(search_results)} results"
            )
            return search_results
        except Exception as e:
            logger.error(
                f"Vector search in collection '{collection_name}' failed: {e}",
                exc_info=True,
            )
            raise MemoryServiceException(
                error_code=ErrorCode.VECTOR_STORE_SEARCH_FAILED,
                error_message=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_SUGGESTION
                ),
            )

    async def delete_docs_by_ids(
        self,
        collection_name: str,
        ids: List[str],
    ) -> None:
        try:
            if not ids:
                logger.info("No documents to delete")
                return

            success_count = 0
            for doc_id in ids:
                success = await self._opensearch_client.delete_data_by_id(
                    collection_name, doc_id
                )
                if success:
                    success_count += 1

            logger.info(
                f"Successfully deleted {success_count}/{len(ids)} documents from collection '{collection_name}'"
            )
        except NotFoundError as e:
            logger.warning(
                f"Delete documents from collection '{collection_name}' failed: {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"Delete documents by IDs from collection '{collection_name}' failed: {e}",
                exc_info=True,
            )
            raise MemoryServiceException(
                error_code=ErrorCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED,
                error_message=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_DELETE_DOCUMENTS_FAILED_SUGGESTION
                ),
            )

    async def list_docs(
        self,
        collection_name: str,
        offset: int = 0,
        limit: int = 10,
        order_field: Optional[str] = None,
        order_type: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        ids: Optional[List[str]] = None,
    ) -> ListDocsResult:
        """
        从索引中检索数据
        """
        try:
            # 如果提供了 ids 参数，使用 ids 查询
            if ids:
                # 构建 ids 查询
                ids_query = {"ids": {"values": ids}}

                # 执行 ids 查询
                result = await self._opensearch_client.query_data_list(
                    collection_name,
                    filters=ids_query,
                    offset=offset,
                    limit=limit,
                    sort_field=order_field,
                    sort_order=order_type.lower(),
                )
            else:
                # 使用普通的查询方式
                result = await self._opensearch_client.query_data_list(
                    collection_name,
                    filters=filters,
                    offset=offset,
                    limit=limit,
                    sort_field=order_field,
                    sort_order=order_type.lower(),
                )

            total = result.get("total", 0)
            data = result.get("data", [])

            # 构建返回结果
            results = []
            for item in data:
                results.append(
                    SearchDocsItem(
                        id=str(item["_id"]),  # 始终保持为字符串类型
                        score=(
                            float(item["_score"]) if item["_score"] is not None else 0.0
                        ),
                        data=item["_source"],
                    )
                )

            list_result = ListDocsResult(total=total, data=results)

            # 添加日志信息
            if ids:
                logger.info(
                    f"List documents by IDs in collection '{collection_name}' found {total} total documents, "
                    f"returning {len(data)} documents (offset={offset}, limit={limit})"
                )
            else:
                logger.info(
                    f"List documents in collection '{collection_name}' found {total} total documents, "
                    f"returning {len(data)} documents (offset={offset}, limit={limit})"
                )

            return list_result

        except Exception as e:
            logger.error(
                f"List documents in collection '{collection_name}' failed: {e}",
                exc_info=True,
            )
            raise MemoryServiceException(
                error_code=ErrorCode.VECTOR_STORE_SEARCH_FAILED,
                error_message=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.VECTOR_STORE_SEARCH_FAILED_SUGGESTION
                ),
            )

    def _build_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建过滤条件

        Args:
            filters: 过滤条件字典

        Returns:
            Dict[str, Any]: OpenSearch 查询过滤器
        """
        filter_conditions = []

        for field, value in filters.items():
            if isinstance(value, list):
                # 多值匹配
                filter_conditions.append({"terms": {field: value}})
            else:
                # 单值匹配
                filter_conditions.append({"term": {field: value}})

        # 如果只有一个过滤条件，直接返回
        if len(filter_conditions) == 1:
            return filter_conditions[0]

        # 如果有多个过滤条件，用bool查询组合
        return {"bool": {"must": filter_conditions}}

    def get_vector_field_name(self) -> str:
        """获取向量字段名称"""
        return OpenSearchVectorIndexConfig.get_vector_field_name()

    def get_text_field_name(self) -> str:
        """获取文本字段名称"""
        return OpenSearchVectorIndexConfig.get_text_field_name()

    def get_metadata_fields(self) -> List[str]:
        """获取元数据字段名称列表"""
        return OpenSearchVectorIndexConfig.get_metadata_fields()
