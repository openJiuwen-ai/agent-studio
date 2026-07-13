# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.

from enum import Enum
from typing import Literal, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from agent_runtime.utils.crypto_tool import decrypt


def _decrypt(v):
    """通用解密验证器：尝试解密，失败则返回原文（明文兼容）。"""
    return decrypt(v)


class ServerSettings(BaseSettings):
    host: str = Field(default="127.0.0.1", validation_alias="SERVER_HOST")
    port: int = Field(default=8000, validation_alias="SERVER_PORT")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    # HTTPS 配置（参考 agentBuilder-engine）
    https: bool = Field(default=False, validation_alias="HTTPS")
    tls_cert_path: str = Field(default="", validation_alias="TLS_CERT_PATH")
    tls_key_path: str = Field(default="", validation_alias="TLS_CERT_KEY_PATH")
    tls_key_password: str = Field(default="", validation_alias="TLS_CERT_KEY_PASSWD")
    tls_ciphers: str = Field(default="TLSv1.2 TLSv1.3", validation_alias="TLS_CIPHERS")
    # Uvicorn worker 数量。未设置时由 _get_workers() 回退到 CPU 核心数 + 1
    workers: Optional[int] = Field(default=None, validation_alias="GUNICORN_WORK_NUM")
    # Nginx 负载均衡模式。启用时 uvicorn 以单 worker 运行，由 Nginx 做负载均衡
    nginx_load_balancing: bool = Field(default=False, validation_alias="NGINX_LOAD_BALANCING")

    @field_validator("nginx_load_balancing", mode="before")
    @classmethod
    def _empty_str_to_false(cls, v):
        """K8s YAML 中空字符串 value: '' 会导致 bool 解析失败，需转为 False。"""
        if v == "" or v is None:
            return False
        return v

    @field_validator("workers", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        """K8s YAML 中空字符串 value: '' 会导致 Pydantic 类型转换失败，需转为 None。"""
        if v == "":
            return None
        return v

    @field_validator("workers")
    @classmethod
    def _validate_workers(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("GUNICORN_WORK_NUM must be >= 1")
        return v

    @field_validator("tls_key_password", mode="after")
    @classmethod
    def _decrypt_tls_key_password(cls, v):
        return _decrypt(v)


class RedisMode(Enum):
    """Redis 连接模式。"""

    SINGLE = "single"
    CLUSTER = "cluster"
    SENTINEL = "sentinel"


class RedisSettings(BaseSettings):
    """Redis 配置。环境变量前缀统一为 REDIS_。"""

    # 模式配置
    mode: RedisMode = Field(default=RedisMode.SINGLE, validation_alias="REDIS_MODE")

    # 单机/哨兵模式配置
    host: str = Field(default="127.0.0.1", validation_alias="REDIS_HOST")
    port: int = Field(default=6379, validation_alias="REDIS_PORT")
    db: int = Field(default=0, validation_alias="REDIS_DATABASE")
    password: Optional[str] = Field(default=None, validation_alias="REDIS_PASSWORD")

    # 集群模式配置
    cluster_nodes: str = Field(default="", validation_alias="REDIS_CLUSTER_NODES")

    # 哨兵模式配置
    sentinel_master: str = Field(
        default="mymaster", validation_alias="REDIS_SENTINEL_MASTER"
    )
    sentinel_nodes: str = Field(default="", validation_alias="REDIS_SENTINEL_NODES")

    # 连接池配置
    max_connections: int = Field(default=50, validation_alias="REDIS_MAX_CONNECTIONS")
    socket_timeout: int = Field(default=5, validation_alias="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(
        default=5, validation_alias="REDIS_SOCKET_CONNECT_TIMEOUT"
    )

    # SSL 配置（建议直接使用默认值就可以）
    ssl_enabled: bool = Field(default=False, validation_alias="REDIS_SSL_ENABLED")
    ssl_ca_cert: str = Field(default="", validation_alias="REDIS_SSL_CA_CERT")
    ssl_cert_file: str = Field(default="", validation_alias="REDIS_SSL_CERT_FILE")
    ssl_key_file: str = Field(default="", validation_alias="REDIS_SSL_KEY_FILE")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("password", mode="after")
    @classmethod
    def _decrypt_password(cls, v):
        return _decrypt(v)


class ModelConfigStrategyType(str, Enum):
    """模型配置来源策略"""
    ENV = "env"
    IR = "ir"
    OBS = "obs"


class LLMSettings(BaseSettings):
    api_key: str = Field(default="sk-placeholder", validation_alias="IR_LLM_API_KEY")
    api_base: str = Field(default="", validation_alias="MODEL_ROUTER_API")
    ssl_verify: bool = Field(default=False, validation_alias="IR_LLM_SSL_VERIFY")
    # LLM 调用读取超时（秒），与原版 agentBuilder-engine 的 STREAM_READ_TIMEOUT 保持一致
    timeout: float = Field(default=900.0, validation_alias="STREAM_READ_TIMEOUT")

    # Model configuration defaults
    model_name: str = Field(default="", validation_alias="IR_LLM_MODEL_NAME")
    temperature: float = Field(default=0.5, validation_alias="IR_LLM_TEMPERATURE")
    top_p: float = Field(default=0.5, validation_alias="IR_LLM_TOP_P")
    max_tokens: int = Field(default=4096, validation_alias="IR_LLM_MAX_TOKENS")

    # 模型配置来源策略: env / ir / obs（默认 obs：OBS 直连，绕过模型路由）
    model_config_strategy: ModelConfigStrategyType = Field(
        default=ModelConfigStrategyType.OBS, validation_alias="MODEL_CONFIG_STRATEGY"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=("settings_",),
    )

    @field_validator("api_key", mode="after")
    @classmethod
    def _decrypt_api_key(cls, v):
        return _decrypt(v)


class ObjectStorageSettings(BaseSettings):
    server: str = Field(default="", validation_alias="DATASOURCE_OBS_SERVER")
    bucket: str = Field(default="", validation_alias="DATASOURCE_OBS_BUCKET")
    access_key: str = Field(default="", validation_alias="DATASOURCE_OBS_AK")
    secret_key: str = Field(default="", validation_alias="DATASOURCE_OBS_SK")
    enable_ssl: bool = Field(
        default=False, validation_alias="DATASOURCE_OBS_ENABLE_SSL"
    )
    path_style: Literal["path", "virtual"] = Field(
        default="path", validation_alias="DATASOURCE_OBS_PATH_STYLE"
    )
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("secret_key", mode="after")
    @classmethod
    def _decrypt_keys(cls, v):
        return _decrypt(v)


class HealthCheckSettings(BaseSettings):
    """健康检查配置。"""

    custom_rsp: str = Field(default="", validation_alias="CUSTOM_HEALTH_CHECK_RSP")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class SecuritySandboxSettings(BaseSettings):
    """Security sandbox configuration for code execution."""

    server: str = Field(default="", validation_alias="SECURITY_SANDBOX_SERVER")
    ssl_verify: bool = Field(
        default=False, validation_alias="SECURITY_SANDBOX_SSL_VERIFY"
    )
    idle_ttl_seconds: int = Field(
        default=600, validation_alias="SECURITY_SANDBOX_IDLE_TTL"
    )
    timeout_seconds: int = Field(
        default=300, validation_alias="SECURITY_SANDBOX_TIMEOUT"
    )
    sandbox_type: str = Field(
        default="aio", validation_alias="SECURITY_SANDBOX_TYPE"
    )
    scope: str = Field(default="system", validation_alias="SECURITY_SANDBOX_SCOPE")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class WorkflowLogSettings(BaseSettings):
    """Workflow logger configuration."""

    level: str = Field(default="WARNING", validation_alias="WORKFLOW_LOG_LEVEL")
    graph_level: str = Field(default="WARNING", validation_alias="GRAPH_LOG_LEVEL")
    llm_level: str = Field(default="WARNING", validation_alias="LLM_LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class OtelSettings(BaseSettings):
    """OpenTelemetry tracer configuration.

    All fields are optional with sensible defaults. Set ``OTEL_ENABLED=true``
    and ``OTEL_EXPORTER_ENDPOINT`` to activate OTel span export.
    """

    enabled: bool = Field(default=False, validation_alias="OTEL_ENABLED")
    exporter_type: str = Field(default="console", validation_alias="OTEL_EXPORTER_TYPE")
    exporter_endpoint: str = Field(default="", validation_alias="OTEL_EXPORTER_ENDPOINT")
    protocol: str = Field(default="grpc", validation_alias="OTEL_PROTOCOL")
    headers: dict[str, str] = Field(default_factory=dict, validation_alias="OTEL_HEADERS")
    service_name: str = Field(
        default="agent-runtime", validation_alias="OTEL_SERVICE_NAME"
    )
    service_version: str = Field(default="", validation_alias="OTEL_SERVICE_VERSION")
    sample_rate: float = Field(default=1.0, validation_alias="OTEL_SAMPLE_RATE")
    schedule_delay_millis: int = Field(
        default=5000, validation_alias="OTEL_SCHEDULE_DELAY_MILLIS"
    )
    export_timeout_ms: int = Field(default=30000, validation_alias="OTEL_EXPORT_TIMEOUT_MS")
    max_export_batch_size: int = Field(
        default=512, validation_alias="OTEL_MAX_EXPORT_BATCH_SIZE"
    )
    redaction_enabled: bool = Field(
        default=True, validation_alias="OTEL_REDACTION_ENABLED"
    )
    redact_prompts: Optional[bool] = Field(
        default=None, validation_alias="OTEL_REDACT_PROMPTS"
    )
    redact_completions: Optional[bool] = Field(
        default=None, validation_alias="OTEL_REDACT_COMPLETIONS"
    )
    max_attr_length: int = Field(default=4096, validation_alias="OTEL_MAX_ATTR_LENGTH")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class CacheSettings(BaseSettings):
    """多级缓存配置（L1 内存 LRU + L2 Redis）。"""

    max_ir_cache_num: int = Field(default=100, validation_alias="MAX_IR_CACHE_NUM")
    max_workflow_cache_num: int = Field(
        default=100, validation_alias="MAX_WORKFLOW_CACHE_NUM"
    )
    max_agent_cache_num: int = Field(
        default=100, validation_alias="MAX_AGENT_CACHE_NUM"
    )
    max_agent_group_cache_num: int = Field(
        default=100, validation_alias="MAX_AGENT_GROUP_CACHE_NUM"
    )
    max_intent_rule_cache_num: int = Field(
        default=100, validation_alias="MAX_AGENT_RULE_CACHE_NUM"
    )
    cache_ttl_seconds: int = Field(default=3600, validation_alias="CACHE_TTL_SECONDS")
    mem_cache_ttl_seconds: int = Field(
        default=3600, validation_alias="MEM_CACHE_TTL_SECONDS"
    )
    max_cache_data_size: int = Field(
        default=2 * 1024 * 1024, validation_alias="MAX_CACHE_DATA_SIZE"
    )
    ir_cache_enable: bool = Field(default=True, validation_alias="IR_CACHE_ENABLE")
    max_model_service_cache_num: int = Field(
        default=500, validation_alias="MAX_MODEL_SERVICE_CACHE_NUM"
    )
    max_model_auth_cache_num: int = Field(
        default=500, validation_alias="MAX_MODEL_AUTH_CACHE_NUM"
    )
    model_cache_mem_ttl: int = Field(
        default=60, validation_alias="MODEL_CACHE_MEM_TTL"
    )
    model_cache_redis_ttl: int = Field(
        default=300, validation_alias="MODEL_CACHE_REDIS_TTL"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class SkillStorageSettings(BaseSettings):
    """Skill 文件存储路径配置。

    生产环境：work_dir（如 /opt/tmp/agent）由 Dockerfile 预创建，路径已存在，不需要此变量。
    开发环境：本地不存在容器路径，通过 SKILL_STORAGE_DIR 环境变量指定本地存储目录。
    """

    skill_storage_dir: str = Field(
        default="/opt/tmp/agent", validation_alias="SKILL_STORAGE_DIR"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class OpenSearchSettings(BaseSettings):
    """OpenSearch connection settings for memory library."""

    hosts: str = Field(default="localhost:9200", validation_alias="OPENSEARCH_HOSTS")
    use_ssl: Optional[bool] = Field(default=None, validation_alias="OPENSEARCH_USE_SSL")
    ssl_verify: bool = Field(default=False, validation_alias="OPENSEARCH_SSL_VERIFY")
    username: str = Field(default="admin", validation_alias="OPENSEARCH_USERNAME")
    password: str = Field(default="admin", validation_alias="OPENSEARCH_PASSWORD")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("password", mode="after")
    @classmethod
    def _decrypt_password(cls, v):
        return _decrypt(v)


class MemorySettings(BaseSettings):
    """Memory library feature settings."""

    enabled: bool = Field(default=False, validation_alias="MEMORY_ENABLED")
    embedding_model: str = Field(
        default="bge-m3", validation_alias="MEMORY_EMBEDDING_MODEL"
    )
    embedding_base_url: str = Field(
        default="", validation_alias="MEMORY_EMBEDDING_BASE_URL"
    )
    embedding_api_key: str = Field(
        default="", validation_alias="MEMORY_EMBEDDING_API_KEY"
    )
    llm_model: str = Field(default="", validation_alias="MEMORY_LLM_MODEL")
    llm_base_url: str = Field(default="", validation_alias="MEMORY_LLM_BASE_URL")
    llm_api_key: str = Field(default="", validation_alias="MEMORY_LLM_API_KEY")

    # Memory index implementation: "default" (6-field OpenSearch, content in OS)
    # or "simple" (SDK SimpleMemoryIndex, 2-field, content in Redis KV).
    index_type: str = Field(default="default", validation_alias="MEMORY_INDEX_TYPE")
    # OpenSearch index name used by the "default" index implementation.
    index_name: str = Field(
        default="long_term_memory_default",
        validation_alias="VECTOR_STORE_DEFAULT_INDEX_NAME",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("embedding_api_key", "llm_api_key", mode="after")
    @classmethod
    def _decrypt_api_keys(cls, v):
        return _decrypt(v)


class CheckpointerSettings(BaseSettings):
    """Checkpointer feature toggles."""

    fast_checkpointer_enabled: bool = Field(
        default=True, validation_alias="FAST_CHECKPOINTER_ENABLED"
    )
    sentinel_ttl_seconds: int = Field(
        default=86400, validation_alias="FAST_CHECKPOINTER_SENTINEL_TTL_SECONDS"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


class CodeExecutionSettings(BaseSettings):
    """代码节点本地执行模式配置。

    LOCAL_CODE_EXEC_MODE 环境变量控制代码节点的本地执行方式：
    - inprocess: 进程内 exec() 执行（默认，高性能，无隔离）
    - subprocess: 子进程执行（有进程级隔离，但启动开销约 50-200ms）
    """

    local_exec_mode: Literal["inprocess", "subprocess"] = Field(
        default="inprocess",
        validation_alias="LOCAL_CODE_EXEC_MODE",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

class DataBaseSettings(BaseSettings):
    db_type: Literal["mysql", "gaussdb"] = Field(
        default="mysql", validation_alias="STORE_DB_TYPE"
    )
    host: str = Field(default="", validation_alias="STORE_DB_HOST")
    port: str = Field(default="", validation_alias="STORE_DB_PORT")
    user: str = Field(default="", validation_alias="STORE_DB_USER")
    password: str = Field(default="", validation_alias="STORE_DB_PASSWORD")
    database: str = Field(default="", validation_alias="STORE_DB_DATABASE")
    db_schema: str = Field(default="", validation_alias="STORE_DB_SCHEMA")
    sslmode: str = Field(default="disable", validation_alias="STORE_DB_SSLMODE")
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @field_validator("password", mode="after")
    @classmethod
    def _decrypt_password(cls, v):
        return _decrypt(v)


class Settings:
    server = ServerSettings()
    redis = RedisSettings()
    llm = LLMSettings()
    object_storage = ObjectStorageSettings()
    health_check = HealthCheckSettings()
    security_sandbox = SecuritySandboxSettings()
    workflow_log = WorkflowLogSettings()
    cache = CacheSettings()
    skill_storage = SkillStorageSettings()
    opensearch = OpenSearchSettings()
    memory = MemorySettings()
    checkpointer = CheckpointerSettings()
    otel = OtelSettings()
    code_execution = CodeExecutionSettings()
    db_config = DataBaseSettings()

settings = Settings()
