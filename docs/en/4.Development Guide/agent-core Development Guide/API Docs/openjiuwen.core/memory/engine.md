# openjiuwen.core.memory.engine

## class openjiuwen.core.memory.engine.MemoryEngine

```python
class MemoryEngine(config: SysMemConfig, kv_store: BaseKVStore, semantic_store: BaseSemanticStore, db_store: BaseDbStore, **kwargs)
```

Memory engine class, derived from BaseMemoryEngine. Before use, you must provide the initialization configuration and memory storage objects. Use MemoryEngine to manage and operate memory.

**Parameters**:

- **config** (SysMemConfig): Memory engine initialization configuration. Default: None.
- **kv_store** (BaseKVStore): KV storage instance. Default: None.
- **semantic_store** (BaseSemanticStore): Semantic storage instance. Default: None.
- **db_store** (BaseDbStore): Associated DB storage instance. Default: None.
- **kwargs**: Variadic parameters for additional configuration.

### classmethod register_store

```python
register_store(kv_store: BaseKVStore, semantic_store: BaseSemanticStore | None = None, db_store: BaseDbStore | None = None)
```

Register memory storage objects. When create_mem_engine_instance is called, MemoryEngine will use the registered storage objects to initialize the instance.

**Parameters**:

- **kv_store** (BaseKVStore): KV storage instance. Default: None.
- **semantic_store** (BaseSemanticStore): Semantic storage instance. Default: None.
- **db_store** (BaseDbStore): Associated DB storage instance. Default: None.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Register memory storage objects
```

### classmethod async create_mem_engine_instance

```python
create_mem_engine_instance(config: SysMemConfig) -> BaseMemoryEngine | None
```

Create the memory engine singleton based on the system memory configuration. Depends on register_store being called to register storage objects beforehand.

**Parameters**:

- **config** (SysMemConfig): System configuration for the memory engine.

**Returns**:
**BaseMemoryEngine | None**. Returns the memory engine singleton on success, otherwise None.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     memory_engine = await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Returns the memory engine singleton created based on the system memory configuration
```

### classmethod get_mem_engine_instance

```python
get_mem_engine_instance(cls) -> BaseMemoryEngine | None
```

Retrieve the memory engine singleton. You need to call create_mem_engine_instance to create it beforehand. After creation, you can obtain this instance anywhere via get_mem_engine_instance.

**Returns**:
**BaseMemoryEngine**, the memory engine singleton. Returns None if not created.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Returns the retrieved memory engine singleton
```

### init_base_llm

```python
init_base_llm(llm_config: ModelConfig) -> bool
```

Initialize or update the default LLM client.

**Parameters**:

- **llm_config** (ModelConfig): Model configuration. Default: None.

**Returns**:
**bool**. True if initialized successfully, otherwise False.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> async def run():
...     # LLM-related environment variables and configuration
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide the model configuration
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...     		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...      	)
...      )
...     # Call init_base_llm
...     result = memory_engine.init_base_llm(
...     	llm_config=llm_config
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Returns True on success, False on failure.
```

### set_group_config

```python
set_group_config(group_id: str, config: MemoryConfig) -> bool
```

Register or update memory configuration for a specific group.

**Parameters**:

- **group_id** (str): Group unique identifier. Default: None.
- **config** (MemoryConfig): Group-level memory settings (e.g., window size, topic profile). Default: None.

**Returns**:
**bool**. True if the setting is successful, otherwise False.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import MemoryConfig, SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide group ID and group-level memory settings
...     group_id = "group456"
...     config = MemoryConfig(
...     	mem_variables={
...     		"Name": "User name",
...     		"Occupation": "User occupation",
...     		"Residence": "User residence",
...     		"Hobbies": "User hobbies"
...     	},
...     	enable_long_term_mem=True
...     )
...     # Call set_group_config
...     result = memory_engine.set_group_config(
...     	group_id=group_id,
...     	config=config
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Register or update the memory configuration for the specified group. Returns True on success, False on invalid input.
```

### set_group_llm

```python
set_group_llm(group_id: str, model_name: str, llm: BaseModelClient) -> bool
```

Assign an LLM client to a specific group for memory generation.

**Parameters**:

- **group_id** (str): Group unique identifier. Default: None.
- **model_name** (str): Model name. Default: None.
- **llm** (BaseModelClient): LLM client instance. Default: None.

**Returns**:
**bool**. True on success, otherwise False.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> from openjiuwen.core.utils.llm.model_utils.model_factory import ModelFactory
>>> 
>>> async def run():
...     # LLM-related environment variables and configuration
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     
...     # Provide group ID, model name, and the LLM client instance
...     group_id = "group456"
...     llm = ModelFactory().get_model(
...     	model_provider=model_provider,
...     	api_base=api_base,
...      	api_key=api_key
...     )
...     # Call set_group_llm
...     result = memory_engine.set_group_llm(
...     	group_id=group_id,
...     	model_name=model_name, 
...     	llm=llm
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Assign an LLM client for memory generation to the specified group. Returns True on success, False on failure.
```

### set_group_llm_config

```python
set_group_llm_config(group_id: str, llm_config: ModelConfig) -> bool
```

Set the LLM client configuration for a specific group, used for memory generation.

**Parameters**:

- **group_id** (str): Group unique identifier. Default: None.
- **llm_config** (ModelConfig): LLM client configuration. Default: None.

**Returns**:
**bool**. True on success, otherwise False.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> 
>>> async def run():
...     # LLM-related environment variables and configuration
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide group ID and LLM client configuration
...     group_id = "group456"
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...      		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...     	)
...     )
...     # Call set_group_llm_config
...     result = memory_engine.set_group_llm_config(
...     	group_id=group_id,
...     	llm_config=llm_config
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Set the LLM client configuration for the specified group used for memory generation. Returns True on success, False on failure.
```

### async add_conversation_messages

```python
add_conversation_messages(user_id: str, group_id: str, messages: list[BaseMessage], timestamp: datetime | None = None, session_id: str | None = None) -> str | None
```

Accept one or more conversation messages and trigger memory generation.
The engine will perform the following actions in order:
1. Store the raw messages to history.
2. Extract or update user variables and user profile based on configuration.
3. Return the memory ID of the last message.

**Parameters**:

- **user_id** (str): User unique identifier. Default: None.
- **group_id** (str): Group unique identifier. Default: None.
- **messages** (list[BaseMessage]): Non-empty list containing one or more conversation messages. Default: None.
- **timestamp** (datetime | None): Message timestamp. Defaults to current time. Default: None.
- **session_id** (str | None): Conversation grouping key. Defaults to global messages. Default: None.

**Returns**:
**str | None**. The ID of the last added message. Returns "-1" on failure (e.g., empty messages).

**Example**:

```python
>>> import asyncio
>>> import datetime
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.component.common.configs.model_config import ModelConfig
>>> from openjiuwen.core.memory.config.config import MemoryConfig, SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> from openjiuwen.core.utils.llm.base import BaseModelInfo
>>> from openjiuwen.core.utils.llm.messages import BaseMessage
>>> 
>>> async def run():
...     # LLM-related environment variables and configuration
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     os.environ["EMBEDDING_SSL_VERIFY"] = "false"
...     os.environ["EMBEDDING_SSL_CERT"] = "false"
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide model configuration
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...     		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...      	)
...     )
...     # Call init_base_llm
...     result = memory_engine.init_base_llm(
...     	llm_config=llm_config
...     )
...     # Provide group ID and group-level memory settings
...     group_id = "group456"
...     config = MemoryConfig(
...     	mem_variables={
...     		"Name": "User name",
...     		"Occupation": "User occupation",
...     		"Residence": "User residence",
...     		"Hobbies": "User hobbies"
...     	},
...     	enable_long_term_mem=True
...     )
...     # Call set_group_config
...     result = memory_engine.set_group_config(
...     	group_id=group_id,
...     	config=config
...     )
...     # Provide user ID, group ID, non-empty messages list, timestamp, and session ID
...     user_id = "user123"
...     messages = [BaseMessage(role="user",
...     					    content="Hi everyone, I'm Zhang Ming, currently living in Shanghai")]	
...     timestamp = datetime.datetime.now()
...     session_id = "session789"
...     # Call add_conversation_messages
...     msg_id = await memory_engine.add_conversation_messages(
...     	user_id=user_id,
...     	group_id=group_id,
...     	messages=messages,
...     	timestamp=timestamp,
...     	session_id=session_id,
...     )
...     print(msg_id)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
...     await embed_model.close()
>>> asyncio.run(run())
Outputs the ID of the last added message. Returns "-1" on failure (e.g., empty messages).
```

### async get_message_by_id

```python
get_message_by_id(msg_id: str) -> Tuple[BaseMessage, datetime]
```

Get a single message and its timestamp by message ID.

**Parameters**:

- **msg_id** (str): Message unique identifier.

**Returns**:
**Tuple[BaseMessage, datetime]**, the message object and timestamp.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide the ID of the last added message
...     msg_id = "test_message_id"
...    
...     # Call get_message_by_id
...     message_tuple = await memory_engine.get_message_by_id(
...    		msg_id=msg_id
...    	)
...     print(message_tuple)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Outputs the message object and timestamp.
```

### async delete_mem_by_id

```python
delete_mem_by_id(user_id: str, group_id: str, mem_id: str) -> bool
```

Delete a memory entry (message, variable, or profile fragment) by ID.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **mem_id** (str): Memory unique identifier. Default: None.

**Returns**:
**bool**. True if deletion was attempted/succeeded (implementations may decide whether to check existence).

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig()) 
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, and memory ID
...     user_id = "user123"
...     group_id = "group456"
...     mem_id = "mem789"
...     # Call delete_mem_by_id
...     result = await memory_engine.delete_mem_by_id(
...    		user_id=user_id,
...    		group_id=group_id,
...    		mem_id=mem_id
...    	)
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Returns True if a memory entry was attempted/successfully deleted, False on failure.
```

### async delete_mem_by_user_id

```python
delete_mem_by_user_id(user_id: str, group_id: str) -> bool
```

Delete all memories (messages, variables, profiles) of a user in the specified group.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.

**Returns**:
**bool**. True on success.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig()) 
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID and group ID
...     user_id = "user123"
...     group_id = "group456"
...     # Call delete_mem_by_user_id
...     result = await memory_engine.delete_mem_by_user_id(
...     	user_id=user_id,
...      	group_id=group_id
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Returns True on successful deletion, False on failure.
```

### async update_mem_by_id

```python
update_mem_by_id(user_id: str, group_id: str, mem_id: str, memory: str) -> bool
```

Update the content of a specified memory entry.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **mem_id** (str): Memory identifier. Default: None.
- **memory** (str): New string content. Default: None.

**Returns**:
**bool**. True on success.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, memory ID, and new content
...     user_id = "user123"
...     group_id = "group456"
...     mem_id = "mem789"
...     memory = "content"
...     # Call update_mem_by_id
...     result = await memory_engine.update_mem_by_id(
...     	user_id=user_id,
...     	group_id=group_id,
...     	mem_id=mem_id,
...     	memory=memory
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Update the specified memory entry. Returns True on success, False on failure.
```

### async get_user_variable

```python
get_user_variable(user_id: str, group_id: str, name: str) -> str
```

Get the value of a user-defined variable.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **name** (str): Variable name. Default: None.

**Returns**:
**str**. The current value of the variable.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, and variable name
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     # Call get_user_variable
...     user_variable = await memory_engine.get_user_variable(
...    		user_id=user_id,
...    		group_id=group_id,
...    		name=name
...    	)
...     print(user_variable)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Outputs the value of the user-defined variable.
```

### async list_user_variables

```python
list_user_variables(user_id: str, group_id: str) -> dict[str, str]
```

List all user-defined variables of a user under the specified group.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.

**Returns**:
**dict[str, str]**, a mapping from variable name to string value.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID and group ID
...     user_id = "user123"
...     group_id = "group456"
...     # Call list_user_variables
...     user_dict = await memory_engine.list_user_variables(
...     	user_id=user_id,
...     	group_id=group_id
...     )
...     print(user_dict)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Outputs all user-defined variables under the specified group.
```

### async search_user_mem

```python
search_user_mem(user_id: str, group_id: str, query: str, num: int, threshold: float = 0.3) -> list[dict[str, Any]]
```

Perform semantic similarity search over a user's memories using a natural language query.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **query** (str): Natural language query. Default: None.
- **num** (int): Maximum number of results to return. Default: None.
- **threshold** (float, optional): Minimum similarity threshold (e.g., cosine similarity). Default: 0.3.

**Returns**:
**list[dict[str, Any]]**, a list of memory records. Each record includes id, content, type, similarity score, and other metadata.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, natural language query, max return count, and minimum similarity threshold
...     user_id = "user123"
...     group_id = "group456"
...     query = "query"
...     num = 5
...     threshold = 0.3
...     # Call search_user_mem
...     search_list = await memory_engine.search_user_mem(
...     	user_id=user_id,
...     	group_id=group_id,
...     	query=query,
...     	num=num,
...     	threshold=threshold
...     )
...     print(search_list)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
...     await embed_model.close()
>>> asyncio.run(run())
Outputs the semantic similarity search results over a user's memories.
```

### async list_user_mem

```python
list_user_mem(user_id: str,group_id: str,num: int,page: int) -> list[dict[str, Any]]
```

List user memory entries by page (typically by chronological order, not semantic).

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **num** (int): Number of items per page, must be > 0.
- **page** (int): Page number, typically starting from 1.

**Returns**:
**list[dict[str, Any]]**, the list of memory entries for the specified page.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, items per page, and page number
...     user_id = "user123"
...     group_id = "group456"
...     num = 5
...     page = 5
...     # Call list_user_mem
...     user_mem_list = await memory_engine.list_user_mem(
...     	user_id=user_id,
...     	group_id=group_id,
...     	num=num,
...     	page=page
...     )
...     print(user_mem_list)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Outputs user memory entries listed by page.
```

### async update_user_variable

```python
update_user_variable(user_id: str,group_id: str,name: str,value: str) -> bool
```

Create or update a user-defined variable.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **name** (str): Variable name. Default: None.
- **value** (str): Variable value (stored as string). Default: None.

**Returns**:
**bool**. True on successful update.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, variable name, and variable value
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     value = "var_value"
...     # Call update_user_variable
...     result = await memory_engine.update_user_variable(
...     	user_id=user_id,
...     	group_id=group_id,
...     	name=name,
...     	value=value
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Create or update a user-defined variable. Returns True on success, False on failure.
```

### async delete_user_variable

```python
delete_user_variable(user_id: str, group_id: str, name: str) -> bool
```

Delete a user-defined variable by name.

**Parameters**:

- **user_id** (str): User identifier. Default: None.
- **group_id** (str): Group identifier. Default: None.
- **name** (str): Variable name to delete. Default: None.

**Returns**:
**bool**. True on successful deletion.

**Example**:

```python
>>> import asyncio
>>> import os
>>> from sqlalchemy.ext.asyncio import create_async_engine
>>> from openjiuwen.core.memory.config.config import SysMemConfig
>>> from openjiuwen.core.memory.embed_models.api import APIEmbedModel
>>> from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
>>> from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
>>> from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
>>> from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
>>> 
>>> async def run():
...     # Create KV database
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # Create embedding model
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # Create semantic database
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # Create MySQL database
...     db_user = os.getenv("DB_USER")
...     db_password = os.getenv("DB_PASSWORD")
...     db_host = os.getenv("DB_HOST")
...     db_port = os.getenv("DB_PORT")
...     db_name = os.getenv("DB_NAME")
...     db_engine_instance = create_async_engine(
...	    	url=f"mysql+aiomysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}?charset=utf8mb4",
...	    	pool_size=20,
...	    	max_overflow=20
...	    )
...     db_store = DefaultDbStore(db_engine_instance)
...     # See store.md for KV store and other storage object definitions
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # Call create_mem_engine_instance once, then use get_mem_engine_instance to retrieve it
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # Provide user ID, group ID, and variable name to delete
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     # Call delete_user_variable
...     result = await memory_engine.delete_user_variable(
...     	user_id=user_id,
...     	group_id=group_id,
...     	name=name
...     )
...     print(result)
...     # Explicitly release the connection pool after all operations to avoid cleanup on loop close
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
Delete a user-defined variable by name. Returns True on success, False on failure.
```