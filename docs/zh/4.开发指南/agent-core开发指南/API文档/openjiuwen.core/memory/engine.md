# openjiuwen.core.memory.engine

## class openjiuwen.core.memory.engine.MemoryEngine

```python
class MemoryEngine(config: SysMemConfig, kv_store: BaseKVStore, semantic_store: BaseSemanticStore, db_store: BaseDbStore, **kwargs)
```

记忆引擎类，是BaseMemoryEngine的派生类, 使用前需要先输入初始化配置和记忆存储对象，可通过MemoryEngine对记忆进行管理和操作。

**参数**：

* **config**(SysMemConfig)：记忆引擎初始化配置，默认值：无。
* **kv_store**(BaseKVStore)：KV存储实例，默认值：无。
* **semantic_store**(BaseSemanticStore)：语义存储实例，默认值：无。
* **db_store**(BaseDbStore)：关联DB存储实例，默认值：无。
* **kwargs**：可变参数，用于传递其他额外的配置参数。

### classmethod register_store

```python
register_store(kv_store: BaseKVStore, semantic_store: BaseSemanticStore | None = None, db_store: BaseDbStore | None = None)
```

注册记忆存储对象，MemoryEngine在调用create_mem_engine_instance时，会使用注册的存储对象初始化实例。

**参数**：

* **kv_store**(BaseKVStore)：KV存储实例。默认值：无。
* **semantic_store**(BaseSemanticStore )：语义存储实例。默认值：无。
* **db_store**(BaseDbStore )：关联DB存储实例。默认值：无。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
注册记忆存储对象
```

### classmethod async create_mem_engine_instance

```python
create_mem_engine_instance(config: SysMemConfig) -> BaseMemoryEngine | None
```

根据系统记忆配置创建记忆引擎单例，依赖register_store函数注册存储对象。

**参数：**

* **config** (SysMemConfig)：记忆引擎系统配置。

**返回：**
**BaseMemoryEngine | None**，创建成功时返回记忆引擎单例，失败时返回None。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     memory_engine = await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
返回根据系统记忆配置创建的记忆引擎单例
```

### classmethod get_mem_engine_instance

```python
get_mem_engine_instance(cls) -> BaseMemoryEngine | None
```

获取记忆引擎单例，该实例需要事先调用create_mem_engine_instance函数进行创建，创建后，可通过get_mem_engine_instance函数在任意位置获取该实例。

**返回：**
**BaseMemoryEngine**，记忆引擎单例，未创建时返回None。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
返回获取的记忆引擎单例
```

### init_base_llm

```python
init_base_llm(llm_config: ModelConfig) -> bool
```

初始化或更新默认LLM客户端。

**参数**：

* **llm_config**(ModelConfig)：模型配置信息。默认值：无。

**返回：**
**bool**，初始化成功返回True，失败返回False。

**样例：**

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
...     # llm相关环境变量和配置
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入模型配置信息
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...     		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...      	)
...      )
...     # 调用init_base_llm方法
...     result = memory_engine.init_base_llm(
...     	llm_config=llm_config
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
初始化成功返回True，失败返回False。
```

### set_group_config

```python
set_group_config(group_id: str, config: MemoryConfig) -> bool
```

注册或更新指定群组的记忆配置。

**参数：**

* **group_id** (str)：群组唯一标识，默认值：无。
* **config** (MemoryConfig)：群组级记忆设置（如窗口大小、话题画像等），默认值：无。

**返回：**
**bool**，设置成功返回True，失败返回False。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入群组唯一标识和群组级记忆设置
...     group_id = "group456"
...     config = MemoryConfig(
...     	mem_variables={
...     		"姓名":"用户姓名",
...     		"职业":"用户职业",
...     		"居住地":"用户居住地",
...     		"爱好":"用户爱好"
...     	},
...     	enable_long_term_mem=True
...     )
...     # 调用set_group_config方法
...     result = memory_engine.set_group_config(
...     	group_id=group_id,
...     	config=config
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
注册或更新指定群组的记忆配置，设置成功返回True，输入非法返回False。
```

### set_group_llm

```python
set_group_llm(group_id: str, model_name: str, llm: BaseModelClient) -> bool
```

为指定群组分配LLM客户端，用于记忆生成。

**参数：**

* **group_id** (str)：群组唯一标识，默认值：无。
* **model_name** (str)：模型名称，默认值：无。
* **llm** (BaseModelClient)：LLM客户端实例，默认值：无。

**返回：**
**bool**，分配成功返回True，失败返回False。

**样例：**

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
...     # llm相关环境变量和配置
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     
...     # 输入群组唯一标识、模型名称以及LLM客户端实例
...     group_id = "group456"
...     llm = ModelFactory().get_model(
...     	model_provider=model_provider,
...     	api_base=api_base,
...      	api_key=api_key
...     )
...     # 调用set_group_llm方法
...     result = memory_engine.set_group_llm(
...     	group_id=group_id,
...     	model_name=model_name, 
...     	llm=llm
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
为指定群组分配用于记忆生成的LLM客户端，分配成功返回True，失败返回False。
```

### set_group_llm_config

```python
set_group_llm_config(group_id: str, llm_config: ModelConfig) -> bool
```

为指定群组设置LLM客户端配置，用于记忆生成。

**参数：**

* **group_id** (str)：群组唯一标识，默认值：无。
* **llm_config** (ModelConfig)：LLM客户端配置，默认值：无。

**返回：**
**bool**，分配成功返回True，失败返回False。

**样例：**

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
...     # llm相关环境变量和配置
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入群组唯一标识和LLM客户端配置
...     group_id = "group456"
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...      		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...     	)
...     )
...     # 调用set_group_llm_config方法
...     result = memory_engine.set_group_llm_config(
...     	group_id=group_id,
...     	llm_config=llm_config
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
为指定群组设置LLM客户端配置，用于记忆生成，分配成功返回True，失败返回False。
```

### async add_conversation_messages

```python
add_conversation_messages(user_id: str, group_id: str, messages: list[BaseMessage], timestamp: datetime | None = None, session_id: str | None = None) -> str | None
```

接收一条或多条对话消息并触发记忆生成。
引擎将依次执行以下动作：
1. 存储原始消息到历史。
2. 根据配置提取或者更新用户变量和用户画像。
3. 返回最后一条消息的记忆ID。

**参数：**

* **user_id** (str)：用户唯一标识，默认值：无。
* **group_id** (str)：群组唯一标识，默认值：无。
* **messages** (list[BaseMessage])：非空消息列表，包含一至多条对话消息，默认值：无。
* **timestamp** (datetime | None)：消息时间戳，缺省取当前时间，默认值：无。
* **session_id** (str | None)：会话分组键，缺省则为全局消息，默认值：无。

**返回：**
**str | None**，最后一条添加的消息ID，失败（如空消息）返回"-1"。

**样例：**

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
...     # llm相关环境变量和配置
...     os.environ["LLM_SSL_VERIFY"] = "false"
...     os.environ["SSRF_PROTECT_ENABLED"] = "false"
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     os.environ["EMBEDDING_SSL_VERIFY"] = "false"
...     os.environ["EMBEDDING_SSL_CERT"] = "false"
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...
...     api_base = os.getenv("API_BASE", "your api base")
...     api_key = os.getenv("API_KEY", "your api key")
...     model_name = os.getenv("MODEL_NAME", "")
...     model_provider = os.getenv("MODEL_PROVIDER", "")
...     
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入模型配置信息
...     llm_config = ModelConfig(
...     	model_provider=model_provider,
...     	model_info=BaseModelInfo(
...     		model=model_name,
...     		api_base=api_base,
...     		api_key=api_key
...      	)
...     )
...     # 调用init_base_llm方法
...     result = memory_engine.init_base_llm(
...     	llm_config=llm_config
...     )
...     # 输入群组唯一标识和群组级记忆设置
...     group_id = "group456"
...     config = MemoryConfig(
...     	mem_variables={
...     		"姓名":"用户姓名",
...     		"职业":"用户职业",
...     		"居住地":"用户居住地",
...     		"爱好":"用户爱好"
...     	},
...     	enable_long_term_mem=True
...     )
...     # 调用set_group_config方法
...     result = memory_engine.set_group_config(
...     	group_id=group_id,
...     	config=config
...     )
...     # 输入用户唯一标识、群组唯一标识、非空消息列表、消息时间戳和会话分组键
...     user_id = "user123"
...     messages = [BaseMessage(role="user",
...     					    content="大家好，我是张明，现居上海")]	
...     timestamp = datetime.datetime.now()
...     session_id = "session789"
...     # 调用add_conversation_messages方法
...     msg_id = await memory_engine.add_conversation_messages(
...     	user_id=user_id,
...     	group_id=group_id,
...     	messages=messages,
...     	timestamp=timestamp,
...     	session_id=session_id,
...     )
...     print(msg_id)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
...     await embed_model.close()
>>> asyncio.run(run())
输出最后一条添加的消息ID，失败（如空消息）返回"-1"。
```

### async get_message_by_id

```python
get_message_by_id(msg_id: str) -> Tuple[BaseMessage, datetime] | None
```

根据消息ID获取单条消息及其时间戳。

**参数：**

* **msg_id** (str)：消息唯一标识。

**返回：**
**Tuple[BaseMessage, datetime]**，消息对象与时间戳，未找到时返回None。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入最后一条添加的消息ID
...     msg_id = "test_message_id"
...    
...     # 调用get_message_by_id方法
...     message_tuple = await memory_engine.get_message_by_id(
...    		msg_id=msg_id
...    	)
...     print(message_tuple)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
输出消息对象与时间戳。
```

### async delete_mem_by_id

```python
delete_mem_by_id(user_id: str, group_id: str, mem_id: str) -> bool
```

按ID删除一条记忆（消息、变量或画像片段）。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **mem_id** (str)：记忆唯一标识，默认值：无。

**返回：**
**bool**，已尝试/成功删除返回True（实现可决定是否检查存在性）。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig()) 
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识和记忆唯一标识
...     user_id = "user123"
...     group_id = "group456"
...     mem_id = "mem789"
...     # 调用delete_mem_by_id方法
...     result = await memory_engine.delete_mem_by_id(
...    		user_id=user_id,
...    		group_id=group_id,
...    		mem_id=mem_id
...    	)
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
已尝试/成功删除一条记忆则返回True，失败返回False。
```

### async delete_mem_by_user_id

```python
delete_mem_by_user_id(user_id: str, group_id: str) -> bool
```

删除某用户在指定群组内的全部记忆（消息、变量、画像）。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。

**返回：**
**bool**，删除成功返回True。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig()) 
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识
...     user_id = "user123"
...     group_id = "group456"
...     # 调用delete_mem_by_user_id方法
...     result = await memory_engine.delete_mem_by_user_id(
...     	user_id=user_id,
...      	group_id=group_id
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
删除成功返回True，失败返回False。
```

### async update_mem_by_id

```python
update_mem_by_id(user_id: str, group_id: str, mem_id: str, memory: str) -> bool
```

更新指定记忆条目的内容。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **mem_id** (str)：记忆标识，默认值：无。
* **memory** (str)：新的字符串内容，默认值：无。

**返回：**
**bool**，更新成功返回True。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识、记忆标识以及新的字符串内容
...     user_id = "user123"
...     group_id = "group456"
...     mem_id = "mem789"
...     memory = "content"
...     # 调用update_mem_by_id方法
...     result = await memory_engine.update_mem_by_id(
...     	user_id=user_id,
...     	group_id=group_id,
...     	mem_id=mem_id,
...     	memory=memory
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
更新指定记忆条目的内容，更新成功返回True，失败返回False。
```

### async get_user_variable

```python
get_user_variable(user_id: str, group_id: str, name: str) -> str
```

获取用户自定义变量的值。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **name** (str)：变量名，默认值：无。

**返回：**
**str**，变量当前值。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识以及变量名
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     # 调用get_user_variable方法
...     user_variable = await memory_engine.get_user_variable(
...    		user_id=user_id,
...    		group_id=group_id,
...    		name=name
...    	)
...     print(user_variable)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
输出用户自定义变量的值
```

### async list_user_variables

```python
list_user_variables(user_id: str, group_id: str) -> dict[str, str]
```

列举某用户在指定群组下的全部自定义变量。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。

**返回：**
**dict[str, str]**，变量名到字符串值的映射。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识
...     user_id = "user123"
...     group_id = "group456"
...     # 调用list_user_variables方法
...     user_dict = await memory_engine.list_user_variables(
...     	user_id=user_id,
...     	group_id=group_id
...     )
...     print(user_dict)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
输出用户在指定群组下的全部自定义变量
```

### async search_user_mem

```python
search_user_mem(user_id: str, group_id: str, query: str, num: int, threshold: float = 0.3) -> list[dict[str, Any]]
```

基于自然语言查询对用户记忆做语义相似度搜索。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **query** (str)：自然语言查询，默认值：无。
* **num** (int)：最大返回条数，默认值：无。
* **threshold** (float，可选)：最小相似度阈值（如余弦相似度）。默认值：0.3。

**返回：**
**list[dict[str, Any]]**，记忆记录列表，每条含 id、内容、类型、相似度分数等元数据。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识、自然语言查询、最大返回条数以及最小相似度阈值
...     user_id = "user123"
...     group_id = "group456"
...     query = "query"
...     num = 5
...     threshold = 0.3
...     # 调用search_user_mem方法
...     search_list = await memory_engine.search_user_mem(
...     	user_id=user_id,
...     	group_id=group_id,
...     	query=query,
...     	num=num,
...     	threshold=threshold
...     )
...     print(search_list)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
...     await embed_model.close()
>>> asyncio.run(run())
输出对用户记忆做语义相似度的搜索结果
```

### async list_user_mem

```python
list_user_mem(user_id: str,group_id: str,num: int,page: int) -> list[dict[str, Any]]
```

按页列举用户记忆条目（通常按时间顺序，非语义）。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **num** (int)：每页条目数，默认>0。
* **page** (int)：页码，通常从 1 开始。

**返回：**
**list[dict[str, Any]]**，对应页的记忆条目列表。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识、每页条目数以及页码
...     user_id = "user123"
...     group_id = "group456"
...     num = 5
...     page = 5
...     # 调用list_user_mem方法
...     user_mem_list = await memory_engine.list_user_mem(
...     	user_id=user_id,
...     	group_id=group_id,
...     	num=num,
...     	page=page
...     )
...     print(user_mem_list)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
输出按页列举用户记忆条目
```

### async update_user_variable

```python
update_user_variable(user_id: str,group_id: str,name: str,value: str) -> bool
```

新建或更新用户自定义变量。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **name** (str)：变量名，默认值：无。
* **value** (str)：变量值（以字符串存储），默认值：无。

**返回：**
**bool**，更新成功返回True。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识、变量名以及变量值
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     value = "var_value"
...     # 调用update_user_variable方法
...     result = await memory_engine.update_user_variable(
...     	user_id=user_id,
...     	group_id=group_id,
...     	name=name,
...     	value=value
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
新建或更新用户自定义变量，成功返回True，失败返回False。
```

### async delete_user_variable

```python
delete_user_variable(user_id: str, group_id: str, name: str) -> bool
```

按名称删除用户自定义变量。

**参数：**

* **user_id** (str)：用户标识，默认值：无。
* **group_id** (str)：群组标识，默认值：无。
* **name** (str)：待删除变量名，默认值：无。

**返回：**
**bool**，删除成功返回True。

**样例：**

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
...     # 创建kv数据库
...     dbm_test_dir = "test_dbm"
...     os.makedirs(dbm_test_dir, exist_ok=True)
...     dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
...     kv_store = DbmKVStore(dbm_kv_path)
...     # 创建embedding模型
...     embed_model = APIEmbedModel(
...	        model_name=os.getenv("EMBED_MODEL_NAME"),
...	        base_url=os.getenv("EMBED_API_BASE"),
...	        api_key=os.getenv("EMBED_API_KEY"),
...	        timeout=int(os.getenv("EMBED_TIMEOUT")),
...	        max_retries=int(os.getenv("EMBED_MAX_RETRIES"))
...	    )
...     # 创建semantic数据库
...     semantic_store = MilvusSemanticStore(
...	        milvus_host=os.getenv("MILVUS_HOST"),
...	        milvus_port=os.getenv("MILVUS_PORT"),
...	        collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
...	        embedding_dims=os.getenv("MILVUS_MODEL_DIMENSION", 1024),
...	        embed_model=embed_model,
...	        token=os.getenv("MILVUS_TOKEN", None)
...	    )
...     # 创建mysql数据库
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
...     # kv_store等存储对象的定义参考store.md
...     MemoryEngine.register_store(
...	        kv_store=kv_store,
...	        semantic_store=semantic_store,
...	        db_store=db_store
...	    )
...     # 只需调用一次create_mem_engine_instance方法，创建memory_engine实例后，通过get_mem_engine_instance获取实例
...     await MemoryEngine.create_mem_engine_instance(config=SysMemConfig())
...     memory_engine = MemoryEngine.get_mem_engine_instance()
...     # 输入用户标识、群组标识以及待删除变量值
...     user_id = "user123"
...     group_id = "group456"
...     name = "var_name"
...     # 调用delete_user_variable方法
...     result = await memory_engine.delete_user_variable(
...     	user_id=user_id,
...     	group_id=group_id,
...     	name=name
...     )
...     print(result)
...     # 显式释放连接池，避免loop关闭时再清理，在所有操作后再执行
...     await db_engine_instance.dispose()
>>> asyncio.run(run())
按名称删除用户自定义变量，成功返回True，失败返回False。
```
