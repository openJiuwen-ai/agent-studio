# openjiuwen.core.memory.store

## class openjiuwen.core.memory.store.BaseKVStore

Abstract base class for a key-value store, including the following interfaces.

### abstractmethod async set

```python
set(key: str, value: str)
```

The set function is used to set a key-value pair.

**Parameters**:
- **key** (str): The key to set. Default: None.
- **value** (str): The value to set. Default: None.

### abstractmethod async exclusive_set

```python
exclusive_set(key: str, value: str, expiry: int | None = None) -> bool
```

Atomically set a key-value pair only if the key does not already exist.

**Parameters**:
- **key** (str): The key to set. Default: None.
- **value** (str): The value to set. Default: None.
- **expiry** (int | None): Expiration time for the key-value pair; after expiry, the value can be overwritten; optional. Default: None.

**Returns**:
- **bool**: True if the pair was set successfully; False if the key already exists and has not expired.

### abstractmethod async get

```python
get(key: str) -> str | None
```

Retrieve the value for the specified key from the database. Returns None if it does not exist.

**Parameters**:
- **key** (str): The key to retrieve. Default: None.

**Returns**:
- **str** | None: The value for the key, or None if the key does not exist.

### abstractmethod async exists

```python
exists(key: str) -> bool
```

Check whether a key exists in the database.

**Parameters**:
- **key** (str): The key. Default: None.

**Returns**:
- **bool**: True if it exists; otherwise False.

### abstractmethod async delete

```python
delete(key: str) -> bool
```

Delete the specified key from the database.

**Parameters**:
- **key** (str): The key. Default: None.

**Returns**:
- **bool**: True if the key existed and was deleted successfully; otherwise False.

### abstractmethod async get_by_prefix

```python
get_by_prefix(prefix: str) -> dict[str, str]
```

Retrieve key-value pairs from the database that match the specified prefix.

**Parameters**:
- **prefix** (str): The prefix to match. Default: None.

**Returns**:
- **dict[str, str]**: The key-value pairs matching the prefix.

### abstractmethod async delete_by_prefix

```python
delete_by_prefix(prefix: str)
```

Delete key-value pairs from the database that match the specified prefix.

**Parameters**:
- **prefix** (str): The prefix to match. Default: None.

---

### abstractmethod async mget

```python
mget(keys: List[str]) -> List[str | None]
```

Batch retrieve values for multiple keys. If a key does not exist, the corresponding position in the returned list is None.

**Parameters**:
- **keys** (List[str]): The list of keys to retrieve. Default: None.

**Returns**:
- **List[str | None]**: The values corresponding to the keys. If a key does not exist, the corresponding position is None.

**Example**:

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

Abstract base class for a semantic retrieval store (semantic_store), including the following interfaces.

### abstractmethod async add_docs

```python
add_docs(docs: List[Tuple[str, str]], table_name: str) -> bool
```

Add documents to the specified table.

**Parameters**:
- **docs** (List[Tuple[str, str]]): A list of documents as (id, text).
- **table_name** (str): The target table name.

**Returns**:
- **bool**: True if added successfully; otherwise False.

### abstractmethod async delete_docs

```python
delete_docs(ids: List[str], table_name: str) -> bool
```

Delete documents from the specified table.

**Parameters**:
- **ids** (List[str]): The list of document IDs.
- **table_name** (str): The target table name.

**Returns**:
- **bool**: True if deleted successfully; otherwise False.

### abstractmethod async search

```python
search(query: str, table_name: str, top_k: int) -> List[Tuple[str, float]]
```

Search for the most semantically relevant documents from the specified table.

**Parameters**:
- **query** (str): The query string.
- **table_name** (str): The target table name.
- **top_k** (int): Number of results to return.

**Returns**:
- **List[Tuple[str, float]]**: A list of results, each containing a document ID and a similarity score. The ID uniquely identifies the document; higher scores indicate greater similarity to the query.

---

### abstractmethod async delete_table

```python
delete_table(table_name: str) -> bool
```

Delete the specified table.

**Parameters**:
- **table_name** (str): The table name.

**Returns**:
- **bool**: True if deleted successfully; otherwise False.

**Example**:

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
            memory_id = hit.entity.get("memory_id")  # Retrieve field
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

Abstract base class for db_store, including the following interface.

### abstractmethod async get_async_engine

```python
get_async_engine(self) -> AsyncEngine
```

The get_async_engine function returns the asynchronous DB Engine.

**Returns**:
- **AsyncEngine**: The asynchronous DB Engine.

**Example**:

```python
from sqlalchemy.ext.asyncio import AsyncEngine

from openjiuwen.core.memory.store.base_db_store import BaseDbStore


class DefaultDbStore(BaseDbStore):
    def __init__(self, async_conn: AsyncEngine):
        self.async_conn = async_conn

    def get_async_engine(self) -> AsyncEngine:
        return self.async_conn
```