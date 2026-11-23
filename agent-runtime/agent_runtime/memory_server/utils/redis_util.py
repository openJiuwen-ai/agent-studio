import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional, Union, List, Dict

import redis
from memory_service.i18n.i18n_constant import I18nMessageCode
from memory_service.i18n.i18n_util import i18n_util
from redis.cluster import RedisCluster, ClusterNode
from redis.sentinel import Sentinel

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
    REDIS_SENTINEL_PASSWORD,
)
from memory_service.exception.memory_service_exception import MemoryServiceException
from memory_service.exception.error_code import ErrorCode

# 全局单例变量和锁，一个进程只允许初始化一个Redis客户端
_redis_client_instance: Optional["RedisClient"] = None
_redis_client_lock = threading.Lock()


class RedisConnectionManager(ABC):
    """Redis连接管理器抽象基类"""

    @abstractmethod
    def get_connection(self):
        """获取Redis连接"""
        pass

    @abstractmethod
    def close(self):
        """关闭连接"""
        pass


class SingleRedisManager(RedisConnectionManager):
    """单机Redis连接管理器"""

    def __init__(
        self,
        host="127.0.0.1",
        port=6379,
        db=0,
        password=None,
        max_connections=10,
        **kwargs,
    ):
        kwargs.setdefault("decode_responses", True)
        self.pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            max_connections=max_connections,
            **kwargs,
        )
        self.client = redis.Redis(connection_pool=self.pool)

        # 测试连接
        try:
            self.client.ping()
            logger.info("single Redis connection success.")
        except redis.ConnectionError as e:
            logger.error("single Redis connection failed: %s", e, exc_info=True)
            raise

    def get_connection(self):
        return self.client

    def close(self):
        if hasattr(self, "pool"):
            self.pool.disconnect()
        if hasattr(self, "client"):
            self.client.close()


class ClusterRedisManager(RedisConnectionManager):
    """Redis集群连接管理器"""

    def __init__(self, nodes: List[str], password=None, max_connections=10, **kwargs):
        kwargs.setdefault("decode_responses", True)
        self.nodes = nodes
        startup_nodes = []
        for node in nodes:
            host_port = node.split(":") if ":" in node else [node, "6379"]
            cluster_node = ClusterNode(host_port[0], int(host_port[1]))
            startup_nodes.append(cluster_node)

        try:
            self.client = RedisCluster(
                startup_nodes=startup_nodes,
                password=password,
                max_connections=max_connections,
                **kwargs,
            )
            # 测试连接
            self.client.ping()
            logger.info("Redis cluster connect success")
        except Exception as e:
            logger.error("Redis cluster connect failed: %s", e, exc_info=True)
            raise

    def get_connection(self):
        return self.client

    def close(self):
        if hasattr(self, "client"):
            self.client.close()


class SentinelRedisManager(RedisConnectionManager):
    """Redis哨兵连接管理器"""

    def __init__(
        self,
        sentinels: List[str],
        master_name="mymaster",
        password=None,
        sentinel_password=None,
        db=0,
        max_connections=10,
        **kwargs,
    ):
        kwargs.setdefault("decode_responses", True)
        sentinel_nodes = []
        for item in sentinels:
            host_port = item.split(":") if ":" in item else [item, "26379"]
            sentinel_nodes.append((host_port[0], int(host_port[1])))
        self.master_name = master_name
        self.sentinel = Sentinel(
            sentinel_nodes, sentinel_kwargs={"password": sentinel_password}, **kwargs
        )

        try:
            self.client = self.sentinel.master_for(
                master_name, password=password, db=db, max_connections=max_connections
            )
            # 测试连接
            self.client.ping()
            logger.info("Redis sentinel connect success")
        except Exception as e:
            logger.error("Redis sentinel connect failed: %s", e, exc_info=True)
            raise

    def get_connection(self):
        return self.client

    def close(self):
        if hasattr(self, "client"):
            self.client.close()


class RedisClient:
    """
    Redis客户端工具类，支持单机、集群、哨兵模式
    """

    def __init__(self):
        self._manager = None
        self._mode = None

    def initialize(self):
        """
        初始化Redis客户端
        """
        if self._manager is not None:
            logger.warning("RedisClient 已初始化，忽略重复初始化")
            return
        from memory_service.scc.crypto_utils import get_crypto_util

        if REDIS_CLUSTER_NODES:
            # 集群模式
            cluster_node = REDIS_CLUSTER_NODES.split(",")

            self._manager = ClusterRedisManager(
                nodes=cluster_node,
                password=get_crypto_util().decrypt(REDIS_PASSWORD)
                if REDIS_PASSWORD
                else "",
                max_connections=REDIS_MAX_CONNECTIONS,
            )
        elif REDIS_SENTINEL_NODES:
            # 哨兵模式
            sentinel_nodes = REDIS_SENTINEL_NODES.split(",")

            self._manager = SentinelRedisManager(
                sentinels=sentinel_nodes,
                master_name=REDIS_MASTER_NAME,
                password=REDIS_PASSWORD,
                sentinel_password=get_crypto_util().decrypt(REDIS_SENTINEL_PASSWORD)
                if REDIS_SENTINEL_PASSWORD
                else "",
                db=REDIS_DATABASE,
                max_connections=REDIS_MAX_CONNECTIONS,
            )
        else:
            # 单机模式
            self._manager = SingleRedisManager(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DATABASE,
                password=get_crypto_util().decrypt(REDIS_PASSWORD)
                if REDIS_PASSWORD
                else "",
                max_connections=REDIS_MAX_CONNECTIONS,
            )

    def _get_client(self):
        """获取Redis客户端实例"""
        if self._manager is None:
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
        return self._manager.get_connection()

    def set(self, key: str, value: Union[str], expire: Optional[int] = None) -> bool:
        """
        设置键值对

        Args:
            key: 键名
            value: 值，支持字符串、数字、字典、列表等类型
            expire: 过期时间（秒），None表示永不过期

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        client = self._get_client()

        result = client.set(key, value, ex=expire)
        return result is True

    def get(self, key: str) -> Optional[Union[str]]:
        """
        获取指定键的值

        Args:
            key: 键名

        Returns:
            值，如果键不存在返回None
        """
        client = self._get_client()
        return client.get(key)

    def update(self, key: str, value: Union[str], expire: Optional[int] = None) -> bool:
        """
        更新键值对（与set方法相同）

        Args:
            key: 键名
            value: 值
            expire: 过期时间（秒）

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        return self.set(key, value, expire)

    def delete(self, key: str) -> bool:
        """
        删除指定键

        Args:
            key: 键名

        Returns:
            bool: 删除成功返回True，失败返回False
        """
        client = self._get_client()
        result = client.delete(key)
        # 返回值为删除的键的数量，如果大于0表示删除成功
        return result > 0

    def exists(self, key: str) -> bool:
        """
        检查键是否存在

        Args:
            key: 键名

        Returns:
            bool: 键存在返回True，不存在返回False
        """
        client = self._get_client()
        return bool(client.exists(key))

    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间

        Args:
            key: 键名

        Returns:
            int: 剩余过期时间（秒），-1表示永不过期，-2表示键不存在
        """
        client = self._get_client()
        return client.ttl(key)

    def expire(self, key: str, time: int) -> bool:
        """
        设置键的过期时间

        Args:
            key: 键名
            time: 过期时间（秒）

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        client = self._get_client()
        return bool(client.expire(key, time))

    def mget(self, keys: List[str]) -> List[Optional[Union[str]]]:
        """
        批量获取多个键的值

        Args:
            keys: 键名列表

        Returns:
            值列表，对应每个键的值
        """
        client = self._get_client()
        values = client.mget(keys)
        result = []
        for value in values:
            if value is None:
                result.append(None)
            else:
                result.append(value)
        return result

    def mset(self, mapping: Dict[str, Union[str]]) -> bool:
        """
        批量设置多个键值对

        Args:
            mapping: 键值对映射

        Returns:
            bool: 设置成功返回True，失败返回False
        """
        client = self._get_client()
        # 处理非字符串值
        processed_mapping = {}
        for key, value in mapping.items():
            processed_mapping[key] = value

        result = client.mset(processed_mapping)
        return result is True

    def flush_db(self) -> bool:
        """
        清空当前数据库

        Returns:
            bool: 清空成功返回True，失败返回False
        """
        client = self._get_client()
        client.flushdb()
        return True

    def get_by_prefix(self, prefix: str) -> Dict[str, Union[str]]:
        """
        根据前缀获取所有匹配的键值对（使用SCAN命令，避免阻塞生产环境）

        Args:
            prefix: 键名前缀

        Returns:
            匹配的键值对字典
        """
        client = self._get_client()
        result = {}
        pattern = f"{prefix}*"

        # 使用SCAN进行游标式查询，避免阻塞
        if hasattr(client, "scan_iter"):
            # redis-py 2.6+ 使用 scan_iter
            for key in client.scan_iter(match=pattern):
                value = client.get(key)
                if value is not None:
                    # 统一处理键和值的 bytes 类型
                    key_str = key.decode() if isinstance(key, bytes) else key
                    value_str = value.decode() if isinstance(value, bytes) else value
                    result[key_str] = value_str
        else:
            # 兼容集群模式
            cursor = b"0"
            while True:
                cursor, keys = client.scan(cursor=cursor, match=pattern, count=100)
                for key in keys:
                    value = client.get(key)
                    if value is not None:
                        # 统一处理键和值的 bytes 类型
                        key_str = key.decode() if isinstance(key, bytes) else key
                        value_str = (
                            value.decode() if isinstance(value, bytes) else value
                        )
                        result[key_str] = value_str
                if cursor == b"0":
                    break

        return result

    def delete_by_pattern(self, pattern: str) -> int:
        """
        根据前缀删除所有匹配的键（使用SCAN命令，避免阻塞生产环境）

        Args:
            pattern: 匹配符

        Returns:
            int: 删除的键的数量
        """
        client = self._get_client()
        deleted_count = 0

        # 分批删除，避免一次性删除大量键带来的性能问题
        batch_size = 1000
        total_batch = 0

        while True:
            if hasattr(client, "scan_iter"):
                # redis-py 2.6+ 使用 scan_iter
                keys_batch = []
                for key in client.scan_iter(match=pattern):
                    keys_batch.append(key)
                    if len(keys_batch) >= batch_size:
                        break

                if not keys_batch:
                    break

                # 使用管道删除这一批键
                pipe = client.pipeline()
                for key in keys_batch:
                    pipe.delete(key)
                pipe_result = pipe.execute()
                deleted_count += sum(batch if batch else 0 for batch in pipe_result)

                # 如果这批获取的键少于批大小，说明已经遍历完毕
                if len(keys_batch) < batch_size:
                    break
            else:
                # 兼容集群模式
                cursor = b"0"
                while True:
                    cursor, keys_batch = client.scan(
                        cursor=cursor, match=pattern, count=batch_size
                    )
                    if not keys_batch:
                        break

                    # 使用管道删除这批键
                    pipe = client.pipeline()
                    for key in keys_batch:
                        pipe.delete(key)
                    pipe_result = pipe.execute()
                    deleted_count += sum(batch if batch else 0 for batch in pipe_result)

                    if cursor == b"0":
                        break

            total_batch += 1
            # 防无限循环的安全措施（最多100批）
            if total_batch > 100:
                logger.warning(
                    f"delete by prefix over limit batch num（100）, stop it.There maybe some keys exists for: prefix={prefix}"
                )
                break

        return deleted_count

    def close(self):
        """
        关闭Redis连接
        """
        try:
            self._manager.close()
        except Exception as e:
            logger.error("close redis connection failed: error=%s", e, exc_info=True)


def get_redis_client() -> RedisClient:
    """
    获取全局唯一的 RedisClient 实例（线程安全）
    """
    global _redis_client_instance
    if _redis_client_instance is None:
        with _redis_client_lock:
            if _redis_client_instance is None:
                _redis_client_instance = RedisClient()
                _redis_client_instance.initialize()
    return _redis_client_instance
