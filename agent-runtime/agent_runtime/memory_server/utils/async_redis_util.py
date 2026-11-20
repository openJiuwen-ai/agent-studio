import logging
from typing import Dict, List, Optional, Union

from redis_spi import RedisMode
from redis_spi.config import RedisProviderSettings
from redis_spi.factory import RedisProviderFactory
from redis_spi.protocols import RedisClient as SpiRedisClient
from redis_spi.types import Duration

# 创建logger实例
logger = logging.getLogger(__name__)
from memory_service.config.settings import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_PASSWORD,
    REDIS_DATABASE,
    REDIS_MAX_CONNECTIONS,
    REDIS_CLUSTER_NODES,
    REDIS_SENTINEL_NODES,
    REDIS_MASTER_NAME,
)
from memory_service.exception.memory_service_exception import MemoryServiceException
from memory_service.exception.error_code import ErrorCode
from memory_service.i18n.i18n_util import i18n_util
from memory_service.i18n.i18n_constant import I18nMessageCode

# 全局单例变量，一个进程只允许初始化一个Redis客户端
_redis_client_instance: Optional["RedisClient"] = None


class RedisClient:
    """Redis 客户端工具类（redis_spi 适配层装配）。

    Phase 4 迁移（设计文档 §六 第四批）：连接创建由 redis_spi.RedisProviderFactory
    统一（native = redis-py 直连），自带 single/cluster/sentinel 三套 Manager 删除；
    本类退化为「memory_service 配置 → Provider 装配 + 服务习惯 API 形态」的薄壳。

    口径说明：
      - 值形态：text_mode=True 视图（str 出入，与旧 decode_responses=True 一致）；
      - 同步版 redis_util.py 已删除（服务内零调用方；SPI 无同步面）；
      - flush_db 已删除（服务内零调用方；SPI 核心面无 FLUSHDB，管理操作走运维通道）；
      - 哨兵模式的 sentinel 节点独立密码（REDIS_SENTINEL_PASSWORD）已建模
        （RedisProviderSettings.sentinel_password，经 native 哨兵构造透传）；
        注意：新路径按环境变量原值透传，不做 crypto 解密——若部署以密文
        形态存储该变量，装配期将得到明确连接错误（fail-fast，非静默）；
      - 装配惰性：initialize() 仅固化配置（同步），首个命令时经工厂建连并 ping 首检。
    """

    def __init__(self):
        self._settings: Optional[RedisProviderSettings] = None
        self._client: Optional[SpiRedisClient] = None

    def initialize(self):
        """
        初始化Redis客户端（仅固化配置；实际建连在首个命令时经 Provider 工厂完成）
        """
        if self._settings is not None:
            logger.warning("RedisClient 已初始化，忽略重复初始化")
            return
        from memory_service.scc.crypto_utils import get_crypto_util

        if REDIS_CLUSTER_NODES:
            mode = RedisMode.CLUSTER
        elif REDIS_SENTINEL_NODES:
            mode = RedisMode.SENTINEL
        else:
            mode = RedisMode.SINGLE

        self._settings = RedisProviderSettings(
            _env_file=None,
            mode=mode,
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DATABASE,
            password=get_crypto_util().decrypt(REDIS_PASSWORD)
            if REDIS_PASSWORD
            else None,
            max_connections=REDIS_MAX_CONNECTIONS,
            cluster_nodes=REDIS_CLUSTER_NODES or "",
            sentinel_nodes=REDIS_SENTINEL_NODES or "",
            sentinel_master=REDIS_MASTER_NAME or "mymaster",
            text_mode=True,
        )
        logger.info(
            "Redis client initialized via redis_spi provider (mode=%s).", mode.value
        )

    async def _get_client(self) -> SpiRedisClient:
        """获取Redis客户端实例（首命令时装配：工厂建连 + ping 首检 fail-fast）"""
        if self._settings is None:
            logger.warning("RedisClient is not init，call initialize() to init it")
            raise MemoryServiceException(
                error_code=ErrorCode.SERVER_INTERNAL_ERROR,
                error_message=i18n_util.get_message(
                    I18nMessageCode.REDIS_NOT_INIT_MESSAGE
                ),
                error_reason=i18n_util.get_message(
                    I18nMessageCode.REDIS_NOT_INIT_REASON
                ),
                error_suggestion=i18n_util.get_message(
                    I18nMessageCode.REDIS_NOT_INIT_SUGGESTION
                ),
            )
        if self._client is None:
            self._client = await RedisProviderFactory.create(self._settings)
        return self._client

    async def set(
        self, key: str, value: Union[str], expire: Optional[int] = None
    ) -> bool:
        """
        设置键值对

        Args:
            key: 键名
            value: 值，支持字符串、数字、字典、列表等类型
            expire: 过期时间（秒），None表示永不过期

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        client = await self._get_client()
        result = await client.set(
            key,
            value,
            duration=Duration.seconds(expire) if expire is not None else None,
        )
        # SPI set：成功返回 "OK"（text_mode），条件不满足返回 None
        return result is not None

    async def get(self, key: str) -> Optional[Union[str]]:
        """
        获取指定键的值

        Args:
            key: 键名

        Returns:
            键对应的值；不存在返回 None
        """
        client = await self._get_client()
        return await client.get(key)

    async def update(
        self, key: str, value: Union[str], expire: Optional[int] = None
    ) -> bool:
        """
        更新键值对（与set方法相同）

        Args:
            key: 键名
            value: 值
            expire: 过期时间（秒）

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        return await self.set(key, value, expire)

    async def delete(self, key: str) -> bool:
        """
        删除指定键

        Args:
            key: 键名

        Returns:
            bool: 删除成功返回True，失败返回False
        """
        client = await self._get_client()
        result = await client.delete(key)
        # 返回值为删除的键的数量，如果大于0表示删除成功
        return result > 0

    async def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 键存在返回True，不存在返回False
        """
        client = await self._get_client()
        return bool(await client.exists(key))

    async def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 键名

        Returns:
            int: 剩余过期时间（秒），-1表示永不过期，-2表示键不存在
        """
        client = await self._get_client()
        return await client.ttl(key)

    async def expire(self, key: str, time: int) -> bool:
        """
        设置键的剩余过期时间（秒）
        """
        client = await self._get_client()
        return bool(await client.expire(key, Duration.seconds(time)))

    async def mget(self, keys: List[str]) -> List[Optional[Union[str]]]:
        """
        批量获取多个键的值

        Args:
            keys: 键名列表

        Returns:
            值列表，对应每个键的值
        """
        client = await self._get_client()
        values = await client.mget(keys)
        result = []
        for value in values:
            if value is None:
                result.append(None)
            else:
                result.append(value)
        return result

    async def mset(self, mapping: Dict[str, Union[str]]) -> bool:
        """
        批量设置多个键值对

        Args:
            mapping: 键值对映射

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        client = await self._get_client()
        processed_mapping = {}
        for key, value in mapping.items():
            processed_mapping[key] = value

        await client.mset(processed_mapping)
        return True

    async def get_by_prefix(self, prefix: str) -> Dict[str, Union[str]]:
        """
        根据前缀获取所有匹配的键值对（SCAN 游标遍历，避免阻塞生产环境；
        集群模式由 native 实现聚合全节点，无需服务侧分支）
        """

        client = await self._get_client()
        result = {}
        pattern = f"{prefix}*"

        async for key in client.scan_iter(match=pattern):
            value = await client.get(key)
            if value is not None:
                # 统一处理键和值的 bytes 类型（text_mode 视图本为 str，防御双形态）
                key_str = key.decode() if isinstance(key, bytes) else key
                value_str = value.decode() if isinstance(value, bytes) else value
                result[key_str] = value_str

        return result

    async def delete_by_pattern(self, pattern: str) -> int:
        """
        根据前缀删除所有匹配的键（SCAN 游标 + pipeline 分批删除）

        Args:
            pattern: 匹配符

        Returns:
            int: 删除的键的数量
        """

        client = await self._get_client()
        deleted_count = 0

        # 分批删除，避免一次性删除大量键带来的性能问题
        batch_size = 1000
        total_batch = 0

        while True:
            keys_batch = []
            async for key in client.scan_iter(match=pattern):
                keys_batch.append(key)
                if len(keys_batch) >= batch_size:
                    break

            if not keys_batch:
                break

            # 使用管道删除这一批键
            pipe = client.pipeline(transaction=False)
            for key in keys_batch:
                pipe.delete(key)
            pipe_result = await pipe.execute()
            deleted_count += sum(int(batch) for batch in pipe_result)

            # 如果这批获取的键少于批大小，说明已经遍历完毕
            if len(keys_batch) < batch_size:
                break

            total_batch += 1
            # 防无限循环的安全措施（最多100批）
            if total_batch > 100:
                logger.warning(
                    f"delete by pattern over limit batch num（100）, stop it."
                    f"There maybe some keys exists for: pattern={pattern}"
                )
                break

        return deleted_count

    async def close(self):
        """
        关闭Redis连接
        """
        try:
            if self._client is not None:
                client, self._client = self._client, None
                await client.aclose()
        except Exception as e:
            logger.error("close redis connection failed: error=%s", e, exc_info=True)

    async def test_connection(self):
        """
        测试redis连接（装配后 ping 首检）
        """
        try:
            client = await self._get_client()
            ok = await client.ping()
            logger.info("Redis connect success")
            return ok
        except Exception as e:
            logger.error("Redis connect failed: %s", e, exc_info=True)
            raise


def get_async_redis_client() -> RedisClient:
    """
    获取全局唯一的 RedisClient 实例（线程安全）
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        _redis_client_instance = RedisClient()
        _redis_client_instance.initialize()
    return _redis_client_instance
