import base64
import binascii
import os

from dotenv import load_dotenv
from openjiuwen.core.common.logging import logger
from openjiuwen.core.foundation.llm import ModelRequestConfig, ModelClientConfig
from openjiuwen.core.foundation.store import DbBasedKVStore, DefaultDbStore, create_vector_store
from openjiuwen.core.memory import LongTermMemory, MemoryEngineConfig
from sqlalchemy.ext.asyncio import create_async_engine

from openjiuwen_studio.ops.modules.prompt.infra.database import get_database_url
from openjiuwen_studio.ops.modules.prompt.infra.database import get_async_database_url
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils


class MemoryEngineManager:
    _instance: LongTermMemory | None = None

    @classmethod
    async def init(cls):
        if cls._instance is not None:
            return cls._instance
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(current_file_dir, '../.env'))

        memory_data_path = os.getenv("MEMORY_DATA_PATH", "memory-data")

        if not os.path.isabs(memory_data_path):
            data_dir = os.path.join(current_file_dir, memory_data_path)
        else:
            data_dir = memory_data_path

        os.makedirs(data_dir, exist_ok=True)

        try:
            master_aes_key = base64.b64decode(os.getenv("SERVER_AES_MASTER_KEY_ENV", ""))
            if os.getenv('HUAWEICLOUD_KMS_ENABLED', 'false').lower() == 'true':
                master_aes_key = SecurityUtils(use_kms=True).get_initialized_master_key()
        except binascii.Error:
            master_aes_key = b''
        except Exception:
            master_aes_key = b''
        vector_db_type = os.getenv("INDEX_MANAGER_TYPE", "milvus")
        if vector_db_type == "milvus":
            milvus_token = SecurityUtils.get_decrypted_secret(
                "MILVUS_TOKEN",
                os.getenv("MILVUS_TOKEN", None),
            )
            milvus_host = os.getenv("MILVUS_HOST")
            milvus_port = os.getenv("MILVUS_PORT")
            vector_store = create_vector_store(
                store_type=vector_db_type,
                milvus_uri=f"http://{milvus_host}:{milvus_port}",
                milvus_token=milvus_token
            )
            logger.info("✅ milvus vector store created")
        elif vector_db_type == "chroma":
            vector_store = create_vector_store(vector_db_type, persist_directory=data_dir)
            logger.info("✅ chroma vector store created")
        else:
            raise ValueError(f"Unknown vector db type: {vector_db_type}, please set VECTOR_DB_TYPE to milvus or chroma")
        agent_database_url = get_database_url("agent")
        async_agent_database_url = get_async_database_url(agent_database_url)
        db_store = DefaultDbStore(create_async_engine(
            async_agent_database_url,
            pool_size=20,
            max_overflow=20
        ))
        kv_store = DbBasedKVStore(create_async_engine(
            async_agent_database_url,
            pool_pre_ping=True,
            echo=False,
        ))
        memory_engine = LongTermMemory()
        await memory_engine.register_store(
            kv_store=kv_store,
            db_store=db_store,
            vector_store=vector_store
        )
        memory_engine.set_config(MemoryEngineConfig(
            default_model_cfg=ModelRequestConfig(),
            default_model_client_cfg=ModelClientConfig(
                client_provider="SiliconFlow",
                api_key="default_api_key",
                api_base="default_api_base",
                verify_ssl=False
            ),
            crypto_key=master_aes_key
        ))
        cls._instance = memory_engine
        logger.info("✅ Memory engine created")
        return cls._instance

    @classmethod
    def get_instance(cls) -> LongTermMemory:
        if cls._instance is None:
            raise RuntimeError("MemoryEngine has not been initialized. Call 'init' first.")
        return cls._instance
