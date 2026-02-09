Memory Engine is the core component of the openJiuwen framework, primarily responsible for managing an agent’s memory. It provides standardized capabilities for recording, retrieving, and filtering information such as user conversation content, session variables, and user profiles. This helps developers more efficiently process and utilize user memory when building Agents.

In intelligent dialogue scenarios, users generate a large amount of conversation data containing valuable information such as personal characteristics, interests, and behavioral habits. By intelligently managing this information, the Memory Engine helps agents better understand users and provide personalized services.

The development process of the Memory Engine consists of two steps:

1. Obtain a Memory Engine instance: Use the ```create_mem_engine_instance``` method to get a Memory Engine instance, with customizable configurations such as whether to record messages, the maximum length of AI messages used to generate memories, and the historical window size for generating memories, thereby initializing memory functionality.
2. Use the Memory Engine instance: Supports adding conversation messages and extracting session variable memories and user profiles (long-term memories), as well as searching and displaying memories to help agents better understand and serve users.

# Creating a Memory Engine Instance

Obtain a Memory Engine instance via the ```create_mem_engine_instance``` method by passing the appropriate configuration parameters. Configurations include whether to record messages, the maximum length of AI messages used to generate memories, and the size of the historical message window for generating memories. Data storage within the Memory Engine involves `kv_store`, `semantic_store`, and a relational database, which should be registered during initialization. Default implementations are provided under `openjiuwen.core.memory.store.impl`, and custom implementations can be created by inheriting from `openjiuwen.core.memory.store.base_kv_store.BaseKVStore`, `openjiuwen.core.memory.store.base_semantic_store.BaseSemanticStore`, and `openjiuwen.core.memory.store.base_db_store`. The `semantic_store` uses embeddings to compute semantic similarity; users can set up an embedding service or purchase one. In addition to configuring api_key, url, model name, and model dimensions, it is recommended to enable SSL verification by setting `EMBEDDING_SSL_VERIFY` to `true` in environment variables and configuring the certificate path in `EMBEDDING_SSL_CERT` to ensure secure communication.

Below is an example of creating a Memory Engine instance using the default `DbmKVStore`, `MilvusSemanticStore`, and `DefaultDbStore`.

```python
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from openjiuwen.core.component.common.configs.model_config import ModelConfig, BaseModelInfo
from openjiuwen.core.memory.config.config import SysMemConfig, MemoryConfig
from openjiuwen.core.memory.engine.memory_engine import MemoryEngine, BaseMemoryEngine
from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
from openjiuwen.core.memory.embed_models.api import APIEmbedModel
from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
from openjiuwen.core.utils.llm.messages import BaseMessage

async def run() -> None:
    # Define system configuration. If encryption is needed, configure the crypto_key parameter. Refer to SysMemConfig defaults.
    sys_config_dict = {
        "record_message": True,
        "ai_msg_gen_max_len": 64,
        "history_window_size_to_gen_mem": 5,
    }
    sys_config = SysMemConfig(**sys_config_dict)
    # LLM-related environment variables and configuration
    os.environ["LLM_SSL_VERIFY"] = "false"
    os.environ["RESTFUL_SSL_VERIFY"] = "false"
    os.environ["SSRF_PROTECT_ENABLED"] = "false"
    # Embedding-related environment variables
    os.environ["EMBEDDING_SSL_VERIFY"] = "false"
    
    base_model_config = ModelConfig(
        model_provider="xxx",
        model_info=BaseModelInfo(
            api_key="xxx",
            api_base="xxx",
            model="xxx",
        )
    )
    # Create a MySQL database
    # db_user: database username, db_passport: database password, db_host: MySQL host, db_port: MySQL port, agent_db_name: database name
    db_user = "xxxx"
    db_passport = "xxxx"
    db_host = "xxxx"
    db_port = "xxxx"
    agent_db_name = "xxxx"
    db_engine_instance = create_async_engine(
        f"mysql+aiomysql://{db_user}:{db_passport}@{db_host}:{db_port}/{agent_db_name}?charset=utf8mb4",
        pool_size=20,
        max_overflow=20
    )
    db_store = DefaultDbStore(db_engine_instance)
    # Create a KV database
    dbm_test_dir = "test_dbm"
    os.makedirs(dbm_test_dir, exist_ok=True)
    dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
    dbm_kv_store = DbmKVStore(dbm_kv_path)
    # Create an embedding model
    # model_name: embedding model name, base_url: embedding API endpoint, api_key: secret key, max_retries: max retries, timeout: request timeout
    embed_model = APIEmbedModel(model_name="xxxx", base_url=r'https://xxxx', api_key='xxxx', max_retries=3, timeout=60)
    # Create a Milvus Semantic database
    # milvus_host: Milvus host address, milvus_port: Milvus port, token: authentication key
    # embed_model: client instance used to generate vectors, collection_name: name of the collection storing vectors, embedding_dims: vector dimensions (must match embed_model output)
    sem_store = MilvusSemanticStore(milvus_host="xxxx", milvus_port="xxxx", token="xxxx", embed_model=embed_model, collection_name="xxxx", embedding_dims=1024)
    # Register stores and create a Memory Engine instance
    memory_engine = await MemoryEngine.register_store(kv_store=dbm_kv_store, semantic_store=sem_store, db_store=db_store).create_mem_engine_instance(sys_config)
    # Set base LLM configuration
    # The memory engine also provides set_group_llm_config/set_group_llm to set group-level LLM (higher priority)
    memory_engine.init_base_llm(base_model_config)

```

# Using the Memory Engine Instance

The Memory Engine supports major operations such as adding conversation messages, querying variable memories and long-term memories, retrieving memories with high semantic similarity to a query, and updating or deleting memories.

## Adding Messages

Use the ```add_conversation_messages``` method to add conversation messages, and the Memory Engine will analyze and extract memory information.

```python
user_id = "user1"
group_id = "group1"
mem_config_dict = {
    "mem_variables": {
        "Name": "User name",
        "Occupation": "User occupation",
        "Residence": "User residence",
        "Hobby": "User hobby"
    },
    "enable_long_term_mem": True,
}
mem_config = MemoryConfig(**mem_config_dict)
memory_engine.set_group_config(group_id, mem_config)

message1 = BaseMessage(role="user",
                       content="My name is Zhang San, and I like playing badminton")
message2 = BaseMessage(role="assistant",
                       content="Hello Zhang San, nice to meet you")

timestamp = datetime.now(timezone.utc)
message_id = await memory_engine.add_conversation_messages(user_id=user_id, group_id=group_id, messages=[message1, message2], timestamp=timestamp)

```

## Query Variable Memories and Long-Term Memories

You can query extracted variable memories and long-term memories via the list_user_variables and list_user_mem interfaces.

```python
# Query variable memories
user_variables = await memory_engine.list_user_variables(user_id, group_id)
# Query long-term memories
user_mem = await memory_engine.list_user_mem(user_id=user_id, group_id=group_id, num=10, page=1)
```

## Retrieve Memories Most Similar to a Query
You can search memories using the search_user_mem interface. The Memory Engine encodes the query via embeddings and retrieves the top num memory items with the highest semantic similarity.

```python
# Get the user's hobby
search_hobby = await memory_engine.search_user_mem(user_id=user_id, group_id=group_id, query="User's hobby", num=1)
```

## Update Variable Memories and Long-Term Memories
You can update variable memories and long-term memories via the update_user_variable and update_mem_by_id interfaces.

```python
# Update variable memory
await memory_engine.update_user_variable(user_id=user_id, group_id=group_id, name="Hobby", value="Basketball")
# Update long-term memory
await memory_engine.update_mem_by_id(user_id=user_id, group_id=group_id, mem_id=mem_id, memory="The user's hobby is basketball")
```

## Delete Variable Memories and Long-Term Memories
You can delete variable memories and long-term memories via the delete_user_variable and delete_mem_by_id interfaces.

```python
# Delete variable memory
await memory_engine.delete_user_variable(user_id=user_id, group_id=group_id, name="Hobby")
# Delete long-term memory
await memory_engine.delete_mem_by_id(user_id=user_id, group_id=group_id, mem_id=mem_id)

```

Output example

```
user_mem: [{'id': '019b35f578d9d2febbcf474e', ..., 'profile_type': 'personal_information', 'mem': 'The user's name is Zhang San', ...}, {'id': '019b360491e11ca26f505123', ..., 'profile_type': 'interest_hobbies', 'mem': 'The user's hobby is playing badminton', ...}]
user_variables: {'Name': 'Zhang San', 'Hobby': 'playing badminton'}
search_hobby: [{'id': '019b35f578d9d2febbcf474e', ..., 'profile_type': 'personal_information', 'mem': 'The user's name is Zhang San', ...]
```

# Complete Example of Using the Memory Engine

```python
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from openjiuwen.core.component.common.configs.model_config import ModelConfig, BaseModelInfo
from openjiuwen.core.memory.config.config import SysMemConfig, MemoryConfig
from openjiuwen.core.memory.engine.memory_engine import MemoryEngine, BaseMemoryEngine
from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
from openjiuwen.core.memory.store.impl.milvus_semantic_store import MilvusSemanticStore
from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
from openjiuwen.core.memory.embed_models.api import APIEmbedModel
from openjiuwen.core.utils.llm.messages import BaseMessage


async def run() -> None:
    sys_config_dict = {
        "record_message": True,
        "ai_msg_gen_max_len": 64,
        "history_window_size_to_gen_mem": 5,
    }
    sys_config = SysMemConfig(**sys_config_dict)
    os.environ["LLM_SSL_VERIFY"] = "false"
    os.environ["RESTFUL_SSL_VERIFY"] = "false"
    os.environ["SSRF_PROTECT_ENABLED"] = "false"
    os.environ["EMBEDDING_SSL_VERIFY"] = "false"
    base_model_config = ModelConfig(
        model_provider="xxx",
        model_info=BaseModelInfo(
            api_key="xxx",
            api_base="xxx",
            model="xxx",
        )
    )
    # Create MySQL database tables
    db_user = "xxxx"
    db_passport = "xxxx"
    db_host = "xxxx"
    db_port = "xxxx"
    agent_db_name = "xxxx"
    db_engine_instance = create_async_engine(
        f"mysql+aiomysql://{db_user}:{db_passport}@{db_host}:{db_port}/{agent_db_name}?charset=utf8mb4",
        pool_size=20,
        max_overflow=20
    )
    db_store = DefaultDbStore(db_engine_instance)

    dbm_test_dir = "test_dbm"
    os.makedirs(dbm_test_dir, exist_ok=True)
    dbm_kv_path = os.path.join(dbm_test_dir, "testdb")
    dbm_kv_store = DbmKVStore(dbm_kv_path)
    # Create an embedding model
    embed_model = APIEmbedModel(model_name="xxxx", base_url=r'https://xxxx', api_key='xxxx', max_retries=3, timeout=60)
    sem_store = MilvusSemanticStore(milvus_host="xxxx", milvus_port="xxxx", token="xxxx", embed_model=embed_model, collection_name="xxxx", embedding_dims=1024)
    memory_engine = await MemoryEngine.register_store(kv_store=dbm_kv_store, semantic_store=sem_store, db_store=db_store).create_mem_engine_instance(sys_config)
    memory_engine.init_base_llm(base_model_config)

    user_id = "user1"
    group_id = "group1"
    mem_config_dict = {
        "mem_variables": {
            "Name": "User name",
            "Occupation": "User occupation",
            "Residence": "User residence",
            "Hobby": "User hobby"
        },
        "enable_long_term_mem": True,
    }
    mem_config = MemoryConfig(**mem_config_dict)
    memory_engine.set_group_config(group_id, mem_config)

    message1 = BaseMessage(role="user",
                           content="My name is Zhang San, and I like playing badminton")
    message2 = BaseMessage(role="assistant",
                           content="Hello Zhang San, nice to meet you")

    timestamp = datetime.now(timezone.utc)
    message_id = await memory_engine.add_conversation_messages(user_id=user_id, group_id=group_id, messages=[message1, message2], timestamp=timestamp)
    user_variables = await memory_engine.list_user_variables(user_id, group_id)
    user_mem = await memory_engine.list_user_mem(user_id=user_id, group_id=group_id, num=10, page=1)
    search_hobby = await memory_engine.search_user_mem(user_id=user_id, group_id=group_id, query="User's hobby", num=1)
    print(f"message_id: {message_id}\n"
          f"user_mem: {user_mem}\n"
          f"user_variables: {user_variables}\n"
          f"search_hobby: {search_hobby}\n")
    
    await memory_engine.update_user_variable(user_id=user_id, group_id=group_id, name="Hobby", value="Basketball")
    if len(search_hobby) == 1:
        await memory_engine.update_mem_by_id(user_id=user_id, group_id=group_id, mem_id=search_hobby[0]['id'], memory="The user's hobby is basketball")
    user_variables = await memory_engine.list_user_variables(user_id, group_id)
    user_mem = await memory_engine.list_user_mem(user_id=user_id, group_id=group_id, num=10, page=1)
    print(f"after update user_mem: {user_mem}, user_variables: {user_variables}")

    await memory_engine.delete_user_variable(user_id=user_id, group_id=group_id, name="Hobby")
    if len(search_hobby) == 1:
        await memory_engine.delete_mem_by_id(user_id=user_id, group_id=group_id, mem_id=search_hobby[0]['id'])
    user_variables = await memory_engine.list_user_variables(user_id, group_id)
    user_mem = await memory_engine.list_user_mem(user_id=user_id, group_id=group_id, num=10, page=1)
    print(f"after delete user_mem: {user_mem}, user_variables: {user_variables}")
    # Dispose the database engine
    await db_engine_instance.dispose()

    # Close any aiohttp session opened by the embedding model
    if hasattr(embed_model, '_session') and embed_model._session:
        await embed_model._session.close()


if __name__ == '__main__':
    asyncio.run(run())
```