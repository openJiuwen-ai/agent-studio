# openjiuwen.core.memory.store

## class openjiuwen.core.memory.store.BaseKVStore

kv_store抽象基类, 包括以下接口。

### abstractmethod async set

```python
set(key: str, value: str)
```

set函数，用于设置key,value键值对。

​**参数**​：

* ​**key**​(str)：设置的键值。默认值：无。
* ​**value**​(str)：设置的value值。默认值：无。

### abstractmethod async exclusive_set

```python
exclusive_set(key: str, value: str, expiry: int | None = None) -> bool
```

原子性地设置key,value键值对，仅当该键不存在时才进行设置。

​**参数**​：

* ​**key**​(str)：设置的键值。默认值：无。
* ​**value**​(str)：设置的value值。默认值：无。
* ​**expiry**​(str)：键值对的过期时间，超过后值可被覆盖，可选。默认值：无。

**返回：**
​**bool**，如果键值对设置成功则返回True, 键已存在并且还未过期则返回False。

### abstractmethod async get

```python
get(key: str) -> str | None
```

从数据库获取指定的key值对应的value，如果没有则返回None。

​**参数**​：

* ​**key**​(str)：需要获取的key值。默认值：无。

**返回：**
​**str | None**​，返回key对应的value值，如果key不存在则返回None。

### abstractmethod async exists

```python
exists(key: str) -> bool
```

判断数据库中某个key值是否存在。

​**参数**​：

* ​**key**​(str)：键值。默认值：无。

**返回：**
​**bool**，如果存在则返回True, 否则返回False。

### abstractmethod async delete

```python
delete(key: str) -> bool
```

删除数据库中指定key值。

​**参数**​：

* ​**key**​(str)：键值。默认值：无。

**返回：**
​**bool**​，如果值存在且删除成功返回True，否则返回False。

### abstractmethod async get_by_prefix

```python
get_by_prefix(prefix: str) -> dict[str, str]
```

按照指定的前缀字符串从数据库获取匹配的若干key,value键值对。

​**参数**​：

* ​**prefix**​(str)：前缀匹配键值。默认值：无。

**返回：**
​**dict[str, str]​**​，返回前缀匹配的若干key,value键值对。

### abstractmethod async delete_by_prefix

```python
delete_by_prefix(prefix: str)
```

按照指定的前缀字符串删除数据库中匹配的key,value键值对。

​**参数**​：

* ​**prefix**​(str)：前缀匹配键值。默认值：无。

---

### abstractmethod async mget

```python
mget(keys: List[str]) -> List[str | None]
```

批量获取键值对，如果某个key不存在，返回的列表中，对应位置的值为None。

​**参数**​：

* ​**keys**​(List[str])：需要获取的key数组。默认值：无。

**返回：**
​**List[str | None]​**​，返回keys对应的value值，如果某个key不存在，则列表对应位置的值为None。

**样例：**

```python
import asyncio
import dbm
import json
import re
import time
from contextlib import asynccontextmanager
from typing import List

import portalocker

from openjiuwen.core.common.logging import logger
from openjiuwen.core.memory.store.base_kv_store import BaseKVStore


class DbmKVStore(BaseKVStore):
    """
    KV store based on dbm
    """
    def __init__(self, filename: str):
        self.filename = filename
        self._async_lock = asyncio.Lock()
        self._lock_file_path = filename + ".lock"

    @asynccontextmanager
    async def lock(self):
        await self._async_lock.acquire()
        try:
            lock_file = await asyncio.to_thread(open, self._lock_file_path, "w")
            try:
                await asyncio.to_thread(portalocker.lock, lock_file, portalocker.LOCK_EX)
                yield
            finally:
                await asyncio.to_thread(portalocker.unlock, lock_file)
                await asyncio.to_thread(lock_file.close)
        finally:
            self._async_lock.release()

    async def set(self, key: str, value: str):
        with dbm.open(self.filename, "c") as db:
            db[key.encode()] = value.encode()

    async def exclusive_set(self, key: str, val: str, expiry: int | None = None) -> bool:
        async with self.lock():
            def sync_op():
                try:
                    with dbm.open(self.filename, "c") as db:
                        key_b = key.encode()
                        now = time.time()
                        existing = db.get(key_b)
                        if existing:
                            try:
                                data = json.loads(existing.decode())
                                expire_at = data.get("expiry")
                                if expire_at is None or expire_at > now:
                                    return False
                            except json.JSONDecodeError:
                                return False
                        expire_at = now + expiry if expiry else None
                        db[key_b] = json.dumps({"value": val, "expiry": expire_at}).encode()
                        return True
                except Exception as e:
                    logger.error(f"[exclusive_set] DBM error: {e}")
                    return False
            return await asyncio.to_thread(sync_op)

    async def get(self, key: str) -> str | None:
        with dbm.open(self.filename, "c") as db:
            v = db.get(key)
            if v is None:
                return None
            return v.decode("utf-8")

    async def exists(self, key: str) -> bool:
        with dbm.open(self.filename, "c") as db:
            return key.encode() in db

    async def delete(self, key: str):
        with dbm.open(self.filename, "c") as db:
            key_b = key.encode()
            if key_b in db:
                del db[key_b]

    async def get_by_prefix(self, prefix: str) -> dict[str, str]:
        regex_str = re.escape(prefix) + ".*"
        pat = re.compile(regex_str)
        result = {}
        with dbm.open(self.filename, "c") as db:
            for key_b in db.keys():
                k = key_b.decode()
                if pat.search(k):
                    result[k] = db[key_b].decode()
        return result

    async def delete_by_prefix(self, prefix: str):
        regex_str = re.escape(prefix) + ".*"
        pat = re.compile(regex_str)
        delete_keys = []
        with dbm.open(self.filename, "c") as db:
            for key_b in db.keys():
                k = key_b.decode()
                if pat.search(k):
                    delete_keys.append(key_b)
            if delete_keys:
                for key_b in delete_keys:
                    del db[key_b]

    async def mget(self, keys: List[str]) -> List[str | None]:
        result = []
        for k in keys:
            v = await self.get(k)
            result.append(v if v else None)
        return result
```

## class openjiuwen.core.memory.store.BaseSemanticStore

语义召回semantic_store抽象基类，主包括以下接口。

### abstractmethod async add_docs

```python
add_docs(docs: List[Tuple[str, str]], table_name: str) -> bool
```

向指定表中添加文档。

​**参数**​：

* ​**docs**​(List[Tuple[str, str]])：(id, text)表示的文档列表。默认值：无。
* ​**table_name**(str)：指定表名。默认值：无。

**返回：**
​**bool**​，如果添加成功则返回True，否则返回False。

### abstractmethod async delete_docs

```python
delete_docs(ids: List[str], table_name: str) -> bool
```

从指定表中删除文档。

​**参数**​：

* ​**ids**​(List[str])：文档ID列表。默认值：无。
* ​**table_name**(str)：指定表名。默认值：无。

**返回：**
​**bool**​，如果删除成功则返回True，否则返回False。

### abstractmethod async search

```python
search(query: str, table_name: str, top_k: int) -> List[Tuple[str, float]]
```

从指定表中查询语义最相关的文档。

​**参数**​：

* ​**query**​(str)：查询语句。默认值：无。
* ​**table_name**(str)：指定表名。默认值：无。
* ​**top_k**(int)：返回数量。默认值：无。

**返回：**
​**List[Tuple[str, float]]​**​，查询结果列表，每组结果包含文档ID和相似度得分，文档ID为文档唯一标识，得分越高表示文档和query越相似。

---

### abstractmethod async delete_table

```python
delete_table(table_name: str) -> bool
```

删除指定表。

​**参数**​：

* ​**table_name**(str)：指定表名。默认值：无。

**返回：**
​**bool**​，如果删除成功则返回True，否则返回False。

**样例：**

```python
from typing import List, Tuple, Any

import numpy as np
from pymilvus import MilvusClient, FieldSchema, CollectionSchema, DataType, Collection, connections, utility

from openjiuwen.core.common.logging import logger
from openjiuwen.core.memory.store.base_semantic_store import BaseSemanticStore

TABLE_NAME_LENGTH = 128
MEMORY_ID_LENGTH = 36


def convert_milvus_result(results) -> List[List[Tuple[str, float]]]:
    final_results = []
    for hits_per_query in results:
        hits = []
        for hit in hits_per_query:
            memory_id = hit.entity.get("memory_id")  # 获取字段
            distance = hit.distance
            hits.append((memory_id, distance))
        final_results.append(hits)
    return final_results


class MilvusSemanticStore(BaseSemanticStore):
    def __init__(self, milvus_host: str, milvus_port: str, token: str | None,
                collection_name: str, embed_model: Any, embedding_dims: int):
        self.embed_model = embed_model
        self.embedding_dims = embedding_dims
        uri = f"http://{milvus_host}:{milvus_port}"
        self.milvus_client = MilvusClient(uri=uri, token=token)
        self.collection_name = collection_name
        self.milvus_host = milvus_host
        self.milvus_port = milvus_port
        self.collections = {}
        self._init_collection()

    def _init_collection(self):
        """
        create Milvus collection（if not exist
        """
        connections.connect(host=self.milvus_host, port=self.milvus_port, alias="default")
        existing_collections = utility.list_collections()
        if self.collection_name not in existing_collections:
            logger.info(f"Collection {self.collection_name} not found, creating...")
            fields = [
                FieldSchema(name="memory_id", dtype=DataType.VARCHAR, is_primary=True,
                            max_length=MEMORY_ID_LENGTH),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR,
                            dim=self.embedding_dims),
                FieldSchema(name="table_name", dtype=DataType.VARCHAR,
                            max_length=TABLE_NAME_LENGTH)
            ]
            schema = CollectionSchema(fields, description="embedding collection")
            collection = Collection(
                name=self.collection_name,
                schema=schema,
                using="default"
            )
            index_params = {
                "index_type": "IVF_FLAT",
                "metric_type": "IP",
                "params": {"nlist": 128}
            }
            collection.create_index(field_name="embedding", index_params=index_params)
            logger.info(f"Index created for collection {self.collection_name}")
        else:
            self.get_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} already exists.")

    def get_collection(self, table_name: str) -> Collection:
        if table_name in self.collections:
            return self.collections[table_name]
        connections.connect(host=self.milvus_host, port=self.milvus_port, alias="default")
        if not utility.has_collection(table_name):
            fields = [
                FieldSchema(name="memory_id", dtype=DataType.VARCHAR, is_primary=True, max_length=36),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.embedding_dims),
                FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=64)
            ]
            schema = CollectionSchema(fields, description="embedding collection")
            collection = Collection(name=table_name, schema=schema, using="default")
            index_params = {"index_type": "IVF_FLAT", "metric_type": "IP", "params": {"nlist": 128}}
            collection.create_index("embedding", index_params)
        else:
            collection = Collection(name=table_name, using="default")
        collection.load()
        self.collections[table_name] = collection
        return collection

    async def add_docs(self, docs: List[Tuple[str, str]], table_name: str) -> bool:
        memory_ids, memories = zip(*docs)
        memory_ids = list(memory_ids)
        memories = list(memories)
        embeddings = await self.embed_model.embed_queries(texts=memories)
        if len(memory_ids) != len(embeddings):
            raise ValueError(f"memory_ids and embeddings must have same length")
        collection = self.get_collection(self.collection_name)
        vectors_arr = np.array(embeddings, dtype=np.float32)
        collection.insert([
            memory_ids,
            vectors_arr.tolist(),
            [table_name] * len(memory_ids)
        ])
        return True

    async def delete_docs(self, ids: List[str], table_name: str) -> bool:
        if self.collection_name not in self.collections:
            return True  # collection not exist
        collection = self.collections[self.collection_name]
        ids_str = ','.join([f'"{i}"' for i in ids])
        expr = f'memory_id in [{ids_str}] && table_name == "{table_name}"'
        collection.delete(expr)
        return True

    async def search(self, query: str, table_name: str, top_k: int) -> List[Tuple[str, float]]:
        if self.collection_name not in self.collections:
            return []
        collection = self.collections[self.collection_name]
        query_vector = await self.embed_model.embed_queries(texts=[query])
        expr = f'table_name == "{table_name}"'
        results = collection.search(
            data=query_vector,
            anns_field="embedding",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=top_k,
            expr=expr
        )
        parsed_results = convert_milvus_result(results)
        return parsed_results[0] if parsed_results else []

    async def delete_table(self, table_name: str) -> bool:
        collection_name = self.collection_name
        if self.collection_name not in self.collections:
            return True
        collection = self.collections[collection_name]
        expr = f'table_name == "{table_name}"'
        collection.delete(expr)
        return True
```

## class openjiuwen.core.memory.store.BaseDbStore

db_store抽象基类, 包括以下接口。

### abstractmethod async get_async_engine

```python
get_async_engine(self) -> AsyncEngine
```

get_async_engine函数，用于获取异步DB Engine对象。

**返回：**
​**AsyncEngine**​，异步DB Engine对象。

**样例：**

```python
from sqlalchemy.ext.asyncio import AsyncEngine

from openjiuwen.core.memory.store.base_db_store import BaseDbStore


class DefaultDbStore(BaseDbStore):
    def __init__(self, async_conn: AsyncEngine):
        self.async_conn = async_conn

    def get_async_engine(self) -> AsyncEngine:
        return self.async_conn
```
