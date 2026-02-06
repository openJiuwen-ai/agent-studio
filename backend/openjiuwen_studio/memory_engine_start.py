import base64
import binascii
import os

from dotenv import load_dotenv
from openjiuwen.core.common.logging import logger
from openjiuwen.core.memory.config.config import SysMemConfig
from openjiuwen.core.memory.embed_models.api import APIEmbedModel
from openjiuwen.core.memory.engine.memory_engine import MemoryEngine
from openjiuwen.core.memory.store.impl.chroma_semantic_store import ChromaSemanticStore
from openjiuwen.core.memory.store.impl.dbm_kv_store import DbmKVStore
from openjiuwen.core.memory.store.impl.default_db_store import DefaultDbStore
from openjiuwen.core.memory.store.impl.milvus_semantic_store import \
    MilvusSemanticStore
from sqlalchemy.ext.asyncio import create_async_engine

from openjiuwen_studio.ops.modules.prompt.infra.database import get_database_url
from openjiuwen_studio.ops.modules.prompt.infra.database import get_async_database_url
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils


class MemoryEngineManager:
    _instance: MemoryEngine | None = None

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
        kv_db_path = os.path.join(data_dir, 'dbmstore')

        try:
            master_aes_key = base64.b64decode(os.getenv("SERVER_AES_MASTER_KEY_ENV", ""))
            if os.getenv('HUAWEICLOUD_KMS_ENABLED', 'false').lower() == 'true':
                master_aes_key = SecurityUtils(use_kms=True).get_initialized_master_key()
        except binascii.Error:
            master_aes_key = b''
        except Exception:
            master_aes_key = b''
        config = SysMemConfig(
            crypto_key=master_aes_key
        )
        embed_model = APIEmbedModel(
            base_url=os.getenv("EMBED_API_BASE"),
            model_name=os.getenv("EMBED_MODEL_NAME"),
            api_key=os.getenv("EMBED_API_KEY"),
            timeout=int(os.getenv("EMBED_TIMEOUT", 60)),
            max_retries=int(os.getenv("EMBED_MAX_RETRIES", 3)),
        )
        vector_db_type = os.getenv("INDEX_MANAGER_TYPE", "chroma")
        semantic_store = None
        if vector_db_type == "milvus":
            semantic_store = MilvusSemanticStore(
                milvus_host=os.getenv("MILVUS_HOST"),
                milvus_port=os.getenv("MILVUS_PORT"),
                collection_name=os.getenv("MILVUS_COLLECTION_NAME"),
                embedding_dims=os.getenv("EMBEDDING_MODEL_DIMENTION", 1024),
                embed_model=embed_model,
                token=os.getenv("MILVUS_TOKEN", None)
            )
            logger.info("✅ milvus semantic store created")
        elif vector_db_type == "chroma":
            semantic_store = ChromaSemanticStore(
                persist_directory=data_dir,
                embed_model=embed_model,
            )
            logger.info("✅ chroma semantic store created")
        else:
            logger.error(f"Unknown vector db type: {vector_db_type}, please set INDEX_MANAGER_TYPE to milvus or chroma")

        agent_database_url = get_database_url("agent")
        async_agent_database_url = get_async_database_url(agent_database_url)
        db_store = DefaultDbStore(create_async_engine(
            async_agent_database_url,
            pool_size=20,
            max_overflow=20
        ))
        MemoryEngine.register_store(
            kv_store=DbmKVStore(kv_db_path),
            db_store=db_store,
            semantic_store=semantic_store
        )
        cls._instance = await MemoryEngine.create_mem_engine_instance(config)
        logger.info("✅ Memory engine created")
        return cls._instance

    @classmethod
    def get_instance(cls) -> MemoryEngine:
        if cls._instance is None:
            raise RuntimeError("MemoryEngine has not been initialized. Call 'init' first.")
        return cls._instance
