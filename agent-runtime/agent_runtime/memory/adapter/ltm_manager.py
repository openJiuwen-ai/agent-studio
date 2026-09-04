from typing import Optional

from openjiuwen.core.common.logging import memory_logger as logger
from openjiuwen.core.foundation.llm.schema.config import ModelClientConfig, ModelRequestConfig
from openjiuwen.core.foundation.store.base_embedding import EmbeddingConfig
from agent_runtime.memory.adapter.opensearch_vector_store import OpenSearchVectorStore
from agent_runtime.memory.adapter.redis_kv_store import RedisKVStore
from openjiuwen.core.memory.config.config import MemoryEngineConfig, MemoryScopeConfig
from openjiuwen.core.memory.long_term_memory import LongTermMemory
from openjiuwen.core.retrieval.embedding.api_embedding import APIEmbedding
from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

from agent_runtime.common.config import settings

_ltm_instance: Optional[LongTermMemory] = None


def _register_memory_usage_prompt_fallback() -> None:
    """Seed PromptApplier's cache with the memory usage prompt (bounded runtime-side fallback).

    The extension MemoryProxy (jiuwen/extension/memory/client/memory_proxy.py)
    formats retrieval results through agent-core's PromptApplier, which
    hard-codes its prompt dir to openjiuwen/core/memory/prompts/ and raises
    FileNotFoundError because memory_usage_prompt.md is not shipped there.
    PromptApplier checks its cache BEFORE the file lookup, so seeding the
    singleton cache here restores retrieval without touching the agent-core
    tree. Content comes from jiuwen's in-tree MEMORY_USAGE_PROMPT (the same
    prompt used by the workflow-path retrieval), with the bare MEMORY_CONTENT
    placeholder converted to PromptTemplate's {{...}} syntax.
    """
    try:
        from openjiuwen.core.foundation.prompt import PromptTemplate
        from openjiuwen.core.memory.prompts.prompt_applier import PromptApplier
        from jiuwen.context.memory_engine.prompt.memory_usage import (
            MEMORY_USAGE_PROMPT,
        )

        applier = PromptApplier()
        if "memory_usage_prompt" not in applier._prompt_cache:
            applier._prompt_cache["memory_usage_prompt"] = PromptTemplate(
                content=MEMORY_USAGE_PROMPT.replace(
                    "MEMORY_CONTENT", "{{MEMORY_CONTENT}}"
                )
            )
            logger.info(
                "Seeded PromptApplier cache for memory_usage_prompt "
                "(prompt file not shipped in agent-core)"
            )
    except Exception as e:
        logger.warning("Failed to seed memory_usage_prompt fallback: %s", e)


async def init_ltm(redis_client: Redis | RedisCluster) -> bool:
    """Initialize LongTermMemory with Redis KV store, OpenSearch vector store, and embedding model.

    Returns True if LTM was initialized successfully, False if degraded (memory disabled).
    """
    global _ltm_instance

    mem_settings = settings.memory

    if not mem_settings.enabled:
        logger.info("Memory library disabled by MEMORY_ENABLED=false")
        return False

    # 1. Redis KV store adapter
    kv_store = RedisKVStore(redis_client)

    # 2. OpenSearch vector store — ping first for graceful degradation
    os_settings = settings.opensearch
    hosts = [h.strip() for h in os_settings.hosts.split(",") if h.strip()]
    os_kwargs: dict = {}
    if os_settings.username:
        os_kwargs["http_auth"] = (os_settings.username, os_settings.password)

    # Auto-detect use_ssl from hosts URL scheme when not explicitly set
    use_ssl = os_settings.use_ssl
    if use_ssl is None:
        use_ssl = any(h.startswith("https://") for h in hosts)

    if use_ssl:
        os_kwargs["use_ssl"] = True
        os_kwargs["verify_certs"] = os_settings.ssl_verify
        if not os_settings.ssl_verify:
            os_kwargs["ssl_show_warn"] = False
    else:
        os_kwargs["use_ssl"] = False
        os_kwargs["verify_certs"] = False

    vector_store = OpenSearchVectorStore(hosts=hosts, **os_kwargs)
    try:
        alive = await vector_store.ping()
        if not alive:
            logger.warning(
                "OpenSearch ping returned False — memory library not available (non-critical)"
            )
            return False
    except Exception as e:
        logger.warning(
            "OpenSearch unreachable: %s — memory library not available (non-critical)", e
        )
        return False

    # 3. Embedding model
    embedding_model = None
    if mem_settings.embedding_base_url:
        emb_config = EmbeddingConfig(
            model_name=mem_settings.embedding_model,
            base_url=mem_settings.embedding_base_url,
            api_key=mem_settings.embedding_api_key,
        )
        embedding_model = APIEmbedding(config=emb_config)
    else:
        logger.warning(
            "MEMORY_EMBEDDING_BASE_URL not set — embedding disabled, search/extraction will fail"
        )

    # 4. Build MemoryEngineConfig with LLM settings for extraction
    engine_config = _build_engine_config(mem_settings)

    # 5. Initialize LTM singleton
    ltm = LongTermMemory()

    # 6a. Set custom memory index BEFORE register_store. register_store
    #     auto-registers the SDK default SimpleMemoryIndex only when
    #     memory_index is None, so pre-setting it preserves our custom index.
    #     The "default" index stores memory in a single 6-field OpenSearch index
    #     with content text in OpenSearch (no Redis KV for memory body).
    if mem_settings.index_type == "default":
        from agent_runtime.memory.adapter.ltm_default_index import (
            LongTermMemoryDefaultIndex,
        )

        custom_index = LongTermMemoryDefaultIndex(
            vector_store=vector_store,
            embedding_model=embedding_model,
            index_name=mem_settings.index_name,
        )
        ltm.memory_index = custom_index
        logger.info(
            "Registered LongTermMemoryDefaultIndex (6-field OpenSearch, index=%s)",
            mem_settings.index_name,
        )

    await ltm.register_store(
        kv_store=kv_store,
        vector_store=vector_store,
        embedding_model=embedding_model,
    )

    # set_config is synchronous — do NOT await
    ltm.set_config(engine_config)

    _ltm_instance = ltm
    # agent-core does not ship memory_usage_prompt.md; retrieval through the
    # jiuwen extension MemoryProxy needs it, so seed the PromptApplier cache.
    _register_memory_usage_prompt_fallback()
    logger.info(
        "Memory library enabled (embedding=%s, opensearch=%s)",
        mem_settings.embedding_model,
        os_settings.hosts,
    )
    return True


def get_ltm() -> Optional[LongTermMemory]:
    """Return the global LTM instance, or None if not initialized."""
    return _ltm_instance


def build_scope_config() -> MemoryScopeConfig:
    """Build a MemoryScopeConfig from current environment settings."""
    mem_settings = settings.memory
    scope_cfg = MemoryScopeConfig()

    if mem_settings.llm_model:
        scope_cfg.model_cfg = ModelRequestConfig(model=mem_settings.llm_model)
    if mem_settings.llm_base_url:
        scope_cfg.model_client_cfg = ModelClientConfig(
            client_provider="OpenAI",
            api_key=mem_settings.llm_api_key or "sk-placeholder",
            api_base=mem_settings.llm_base_url,
            verify_ssl=False,
        )
    if mem_settings.embedding_base_url:
        scope_cfg.embedding_cfg = EmbeddingConfig(
            model_name=mem_settings.embedding_model,
            base_url=mem_settings.embedding_base_url,
            api_key=mem_settings.embedding_api_key,
        )

    return scope_cfg


def _build_engine_config(mem_settings) -> MemoryEngineConfig:
    cfg = MemoryEngineConfig()
    if mem_settings.llm_model:
        cfg.default_model_cfg = ModelRequestConfig(model=mem_settings.llm_model)
    if mem_settings.llm_base_url:
        cfg.default_model_client_cfg = ModelClientConfig(
            client_provider="OpenAI",
            api_key=mem_settings.llm_api_key or "sk-placeholder",
            api_base=mem_settings.llm_base_url,
            verify_ssl=False,
        )
    return cfg
