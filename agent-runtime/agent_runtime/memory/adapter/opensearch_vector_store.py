import logging
from typing import Any, Dict, List, Optional, Union

from openjiuwen.core.foundation.store.base_vector_store import (
    BaseVectorStore,
    CollectionSchema,
    FieldSchema,
    VectorDataType,
    VectorSearchResult,
)
from opensearchpy import AsyncOpenSearch
from opensearchpy.helpers import async_bulk

logger = logging.getLogger(__name__)


def _ml():
    """lazy memory_logger (写 memory.log, 实时持久, 不被 stdout 缓冲)"""
    from openjiuwen.core.common.logging import memory_logger
    return memory_logger

_TYPE_MAP: dict[VectorDataType, dict] = {
    VectorDataType.VARCHAR: {"type": "text"},
    VectorDataType.INT64: {"type": "long"},
    VectorDataType.INT32: {"type": "integer"},
    VectorDataType.INT16: {"type": "short"},
    VectorDataType.INT8: {"type": "byte"},
    VectorDataType.FLOAT: {"type": "float"},
    VectorDataType.DOUBLE: {"type": "double"},
    VectorDataType.BOOL: {"type": "boolean"},
    VectorDataType.JSON: {"type": "object", "enabled": False},
    VectorDataType.ARRAY: {"type": "object", "enabled": False},
}


def _field_to_mapping(field: FieldSchema) -> dict:
    if field.dtype == VectorDataType.FLOAT_VECTOR:
        return {
            "type": "knn_vector",
            "dimension": field.dim,
            "method": {
                "name": "hnsw",
                "space_type": "cosinesimil",
                "engine": "faiss",
            },
        }
    base = _TYPE_MAP.get(field.dtype, {"type": "text"}).copy()
    if field.dtype == VectorDataType.VARCHAR and field.is_primary:
        # primary key stored as keyword for exact match
        base = {"type": "keyword"}
    # Honor extra mapping options carried in default_value (e.g. {"index": False, "doc_values": False})
    # so that text fields like `content` can be stored without an inverted index.
    if isinstance(field.default_value, dict):
        base.update(field.default_value)
    return base


def _build_mappings(schema: CollectionSchema) -> dict:
    properties: dict[str, Any] = {}
    for field in schema.fields:
        properties[field.name] = _field_to_mapping(field)
    return {"properties": properties}


class OpenSearchVectorStore(BaseVectorStore):
    """Agent-core BaseVectorStore backed by OpenSearch."""

    def __init__(
        self,
        hosts: list[str] | str,
        **kwargs: Any,
    ):
        self._client = AsyncOpenSearch(hosts=hosts, **kwargs)

    async def ping(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def create_collection(
        self,
        collection_name: str,
        schema: Union[CollectionSchema, Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        if isinstance(schema, dict):
            schema = CollectionSchema.from_dict(schema)

        body: dict[str, Any] = {"mappings": _build_mappings(schema)}
        has_vector = any(f.dtype == VectorDataType.FLOAT_VECTOR for f in schema.fields)
        if has_vector:
            body["settings"] = {"index": {"knn": True}}

        try:
            await self._client.indices.create(index=collection_name, body=body)
        except Exception as e:
            err_str = str(e).lower()
            if "resource_already_exists_exception" in err_str or "already exists" in err_str:
                logger.debug("Index %s already exists, skipping creation", collection_name)
            else:
                raise

    async def delete_collection(self, collection_name: str, **kwargs: Any) -> None:
        try:
            await self._client.indices.delete(index=collection_name, ignore=[404])
        except Exception as e:
            if "index_not_found_exception" not in str(e).lower():
                raise

    async def collection_exists(self, collection_name: str, **kwargs: Any) -> bool:
        return bool(await self._client.indices.exists(index=collection_name))

    async def get_schema(self, collection_name: str, **kwargs: Any) -> CollectionSchema:
        mapping = await self._client.indices.get_mapping(index=collection_name)
        idx_data = mapping[collection_name]["mappings"]
        fields: list[FieldSchema] = []
        props = idx_data.get("properties", {})
        for name, cfg in props.items():
            typ = cfg.get("type", "text")
            if typ == "knn_vector":
                fields.append(FieldSchema(
                    name=name,
                    dtype=VectorDataType.FLOAT_VECTOR,
                    dim=cfg.get("dimension"),
                ))
            else:
                dtype = _os_type_to_vector_data_type(typ)
                fields.append(FieldSchema(name=name, dtype=dtype))
        return CollectionSchema(fields=fields)

    async def add_docs(
        self,
        collection_name: str,
        docs: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        if not docs:
            return
        actions = []
        for doc in docs:
            action = {"_index": collection_name, "_source": dict(doc)}
            doc_id = doc.get("id")
            if doc_id is not None:
                action["_id"] = str(doc_id)
            actions.append(action)
        success, errors = await async_bulk(self._client, actions, raise_on_error=False)
        if errors:
            logger.warning(
                "add_docs to %s: %d errors out of %d",
                collection_name,
                len(errors) if isinstance(errors, list) else errors,
                len(docs),
            )

    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        vector_field: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> List[VectorSearchResult]:
        knn_query: dict[str, Any] = {
            "vector": query_vector,
            "k": top_k,
        }
        if filters:
            # Filter on keyword fields directly (our index mapping uses keyword
            # type for user_id/app_id/memory_type). For dynamically created
            # indexes that use text+keyword, the term query on the base field
            # still works via the keyword sub-field analyzer fallback.
            must = [{"term": {k: v}} for k, v in filters.items()]
            query = {
                "bool": {
                    "must": [{"knn": {vector_field: knn_query}}],
                    "filter": must,
                }
            }
        else:
            query = {"knn": {vector_field: knn_query}}

        body = {"size": top_k, "query": query}
        resp = await self._client.search(index=collection_name, body=body)

        results: list[VectorSearchResult] = []
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]
            source["id"] = hit["_id"]
            results.append(VectorSearchResult(score=hit["_score"], fields=source))
        return results

    async def delete_docs_by_ids(
        self,
        collection_name: str,
        ids: List[str],
        **kwargs: Any,
    ) -> None:
        if not ids:
            return
        body = {
            "query": {
                "terms": {"_id": [str(i) for i in ids]}
            }
        }
        # conflicts=proceed: 按 id 删除同样幂等，并发重复删除时忽略版本冲突。
        await self._client.delete_by_query(
            index=collection_name, body=body, ignore=[404], conflicts="proceed"
        )

    async def delete_docs_by_filters(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        must = [{"term": {k: v}} for k, v in filters.items()]
        body = {"query": {"bool": {"filter": must}}}
        # conflicts=proceed: write_manager 会按记忆类型逐个 manager 重复执行同一
        # user+scope 的 delete_by_query；后到的 manager 搜索视图尚未刷新（默认 1s），
        # 仍会命中已被前一个 manager 删除的文档，触发 if_seq_no 版本冲突 409。
        # 忽略冲突继续执行（幂等删除：仍在的删掉、已删的跳过）。
        await self._client.delete_by_query(
            index=collection_name, body=body, ignore=[404], conflicts="proceed"
        )

    async def list_collection_names(self) -> List[str]:
        indices = await self._client.cat.indices(format="json")
        return [
            idx["index"]
            for idx in indices
            if not idx["index"].startswith(".")
        ]

    async def create_index_with_mapping(
        self,
        index_name: str,
        mappings: Dict[str, Any],
        settings: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Create an OpenSearch index with a fully custom mapping (bypass CollectionSchema).

        Used by LongTermMemoryDefaultIndex to define the 6-field `long_term_memory_default`
        index where `content` must be `text` with `index=False, doc_values=False`.
        """
        body: Dict[str, Any] = {"mappings": mappings}
        if settings:
            body["settings"] = settings
        try:
            await self._client.indices.create(index=index_name, body=body)
        except Exception as e:
            err_str = str(e).lower()
            if "resource_already_exists_exception" in err_str or "already exists" in err_str:
                # 索引已存在：校验 content_vector 类型，若被动态映射污染成 float 则删重建
                # （OpenSearch mapping 不可变，float 无法直接改回 knn_vector，只能删重建）
                try:
                    existing = await self._client.indices.get_mapping(index=index_name)
                    cv_type = (
                        existing[index_name]["mappings"]["properties"]
                        .get("content_vector", {})
                        .get("type")
                    )
                except Exception:
                    cv_type = None
                expected_cv = mappings.get("properties", {}).get("content_vector", {}).get("type")
                if cv_type and expected_cv and cv_type != expected_cv:
                    _ml().warning(
                        "Index %s content_vector is %s (expected %s); recreating index",
                        index_name, cv_type, expected_cv,
                    )
                    await self._client.indices.delete(index=index_name, ignore=[404])
                    await self._client.indices.create(index=index_name, body=body)
            else:
                raise

    async def list_docs_by_filter(
        self,
        collection_name: str,
        filters: Dict[str, Any],
        offset: int = 0,
        limit: int = 100,
        sort: Optional[tuple] = None,
    ) -> List[VectorSearchResult]:
        """List documents matching filter conditions (non-vector query) with pagination.

        Args:
            collection_name: OpenSearch index name.
            filters: Dict of field→value term filters.
            offset: Pagination offset.
            limit: Page size.
            sort: Optional ``(field, order)`` tuple, e.g. ``("last_updated", "desc")``.
        """
        must = [{"term": {k: v}} for k, v in filters.items()]
        body: Dict[str, Any] = {
            "from": offset,
            "size": limit,
            "query": {"bool": {"filter": must}},
        }
        if sort:
            body["sort"] = [{sort[0]: {"order": sort[1]}}]
        resp = await self._client.search(index=collection_name, body=body)
        results: list[VectorSearchResult] = []
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]
            source["id"] = hit["_id"]
            # Non-vector queries return _score=null; coerce to 0.0 for VectorSearchResult
            score = hit.get("_score")
            results.append(VectorSearchResult(score=score if score is not None else 0.0, fields=source))
        return results

    async def count_docs(
        self,
        collection_name: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Count documents in an index, optionally filtered."""
        body: Dict[str, Any]
        if filters:
            must = [{"term": {k: v}} for k, v in filters.items()]
            body = {"query": {"bool": {"filter": must}}}
        else:
            body = {"query": {"match_all": {}}}
        resp = await self._client.count(index=collection_name, body=body)
        return resp.get("count", 0)

    async def update_doc(
        self,
        collection_name: str,
        doc_id: str,
        partial_doc: Dict[str, Any],
    ) -> None:
        """Partially update a document by id."""
        await self._client.update(
            index=collection_name, id=str(doc_id), body={"doc": partial_doc}
        )

    async def delete_by_query(
        self,
        collection_name: str,
        body: Dict[str, Any],
    ) -> None:
        """Delete documents matching a query body."""
        # conflicts=proceed: 同 delete_docs_by_filters，忽略重复删除的版本冲突。
        await self._client.delete_by_query(
            index=collection_name, body=body, ignore=[404], conflicts="proceed"
        )

    async def raw_search(
        self,
        collection_name: str,
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a raw OpenSearch search query and return the full response."""
        return await self._client.search(index=collection_name, body=body)

    async def update_schema(
        self, collection_name: str, operations: List[Any]
    ) -> None:
        raise NotImplementedError("update_schema not supported for OpenSearch adapter")

    async def update_collection_metadata(
        self, collection_name: str, metadata: Dict[str, Any]
    ) -> None:
        # OpenSearch doesn't have a separate metadata concept; store as _meta
        body = {"_meta": metadata}
        await self._client.indices.put_mapping(index=collection_name, body=body, ignore=[404])

    async def get_collection_metadata(self, collection_name: str) -> Dict[str, Any]:
        mapping = await self._client.indices.get_mapping(index=collection_name)
        idx_data = mapping[collection_name]["mappings"]
        return idx_data.get("_meta", {})


def _os_type_to_vector_data_type(os_type: str) -> VectorDataType:
    mapping = {
        "text": VectorDataType.VARCHAR,
        "keyword": VectorDataType.VARCHAR,
        "long": VectorDataType.INT64,
        "integer": VectorDataType.INT32,
        "short": VectorDataType.INT16,
        "byte": VectorDataType.INT8,
        "float": VectorDataType.FLOAT,
        "double": VectorDataType.DOUBLE,
        "boolean": VectorDataType.BOOL,
        "object": VectorDataType.JSON,
    }
    return mapping.get(os_type, VectorDataType.VARCHAR)
