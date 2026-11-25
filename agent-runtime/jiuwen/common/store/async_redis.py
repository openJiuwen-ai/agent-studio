#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.
"""the redis utils for the action about redis"""

import os
import ssl
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import redis.asyncio as redis
from jiuwen.common.configs.env_constants import (
    DATASOURCE_REDIS_HOST_KEY,
    DATASOURCE_REDIS_PORT_KEY,
    DATASOURCE_REDIS_PASSWORD_KEY,
    DATASOURCE_REDIS_SSL_MODE_KEY,
    DATASOURCE_REDIS_SSL_PASSWD_KEY,
    DATASOURCE_REDIS_CLUSTER_NODE_KEY,
    DATASOURCE_REDIS_SSL_CA_CERTS_KEY,
    DATASOURCE_REDIS_SSL_CERTFILE_KEY,
    DATASOURCE_REDIS_SSL_KEYFILE_KEY,
    DATASOURCE_REDIS_TTL_KEY,
    DATASOURCE_REDIS_DATABASE_KEY,
    DATASOURCE_REDIS_MAX_CONNECTIONS_KEY,
    DATASOURCE_REDIS_MODE_KEY,
    DATASOURCE_REDIS_SOCKET_TIMEOUT_KEY,
    DATASOURCE_REDIS_SOCKET_CONNECT_TIMEOUT_KEY,
    DATASOURCE_REDIS_PREFIX_KEY,
    DATASOURCE_REDIS_CALLBACKS_KEY,
)
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.security.cryptor import Crypt
from jiuwen.common.store.utils import StoreHandler, StoreCallbacks
from redis.asyncio.cluster import RedisCluster, ClusterNode

DEFAULT_REDIS_TTL = 259200
DEFAULT_REDIS_DB = 0
DEFAULT_REDIS_MAX_CONNECTIONS = 10
DEFAULT_REDIS_SSL_MODE = "true"
DEFAULT_SOCKET_TIMEOUT = 5
DEFAULT_SOCKET_CONNECT_TIMEOUT = 5
DEFAULT_REDIS_HOST = "localhost"
DEFAULT_REDIS_PORT = 6379
DEFAULT_PREFIX = ""

redis_call_handler = StoreHandler()


def register_redis_callbacks(handler: StoreCallbacks = None, env_var: str = ""):
    """register callbacks to wrapper"""
    redis_call_handler.set_callbacks(handler, env_var)


class RedisMode(Enum):
    CLUSTER: str = "cluster"
    SINGLE: str = "single"


@dataclass
class RedisConfig:
    host: str
    port: str
    passwd: str
    ssl_mode: str
    ssl_passwd: str
    cluster_node: str
    ssl_ca_certs: str
    ssl_certfile: str
    ssl_keyfile: str
    ttl: int
    db: int
    max_connections: int
    mode: str
    socket_timeout: int
    socket_connect_timeout: int
    prefix: str


class AsyncRedisUtils:
    """
    Redis operation tool class.
    """

    # Class variable used to store connection pool instances
    _connection_pool = None
    _cluster = None

    def __init__(self, config: RedisConfig):
        try:
            # During initialization, the system checks whether the connection pool exists. If the connection pool
            # does not exist, the system creates the connection pool.
            ssl_mode = config.ssl_mode
            if config.mode == RedisMode.CLUSTER.value:
                # 集群配置
                if AsyncRedisUtils._cluster is None:
                    if str(ssl_mode).lower() == "false":
                        # 关闭ssl认证
                        AsyncRedisUtils._cluster = self._get_redis_cluster_without_ssl(
                            config
                        )
                    else:
                        AsyncRedisUtils._cluster = self._get_redis_cluster_with_ssl(
                            config
                        )
                    register_redis_callbacks(env_var=DATASOURCE_REDIS_CALLBACKS_KEY)
                self._redis = AsyncRedisUtils._cluster
            else:
                # 单服务配置
                if AsyncRedisUtils._connection_pool is None:
                    if str(ssl_mode).lower() == "false":
                        # 关闭ssl认证
                        AsyncRedisUtils._connection_pool = (
                            self._get_connection_pool_without_ssl(config)
                        )
                    else:
                        AsyncRedisUtils._connection_pool = (
                            self._get_connection_pool_with_ssl(config)
                        )
                    register_redis_callbacks(env_var=DATASOURCE_REDIS_CALLBACKS_KEY)
                self._redis = redis.Redis(
                    connection_pool=AsyncRedisUtils._connection_pool
                )
            self._prefix = config.prefix
            # 清理掉内存中的密码信息
            config.passwd = ""
            config.ssl_passwd = ""
        except redis.ConnectionError as e:
            logger.error(f"failed to async connect to the redis: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_SERVICE_NOT_FOUND.code,
                StatusCode.REDIS_SERVICE_NOT_FOUND.errmsg,
            ) from e
        except Exception as e:
            logger.error(f"An error occurred while initializing the async Redis.: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_SERVICE_NOT_FOUND.code,
                StatusCode.REDIS_SERVICE_NOT_FOUND.errmsg,
            ) from e

    @staticmethod
    def get_cluster_nodes():
        """
        获取集群节点信息
        """
        try:
            return (
                AsyncRedisUtils._cluster.get_nodes() if AsyncRedisUtils._cluster else []
            )
        except Exception as e:
            logger.error(f"Error adding element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_CLUSTER_NODES_GET_ERROR.code,
                StatusCode.REDIS_CLUSTER_NODES_GET_ERROR.errmsg,
            ) from e

    @staticmethod
    def _get_connection_pool_with_ssl(config: RedisConfig):
        """Obtaining the Secure Connection Pool"""
        if config is None:
            config = {}
        return redis.ConnectionPool(
            connection_class=redis.SSLConnection,
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.passwd,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=config.ssl_ca_certs,
            ssl_certfile=config.ssl_certfile,
            ssl_keyfile=config.ssl_keyfile,
            ssl_password=config.ssl_passwd,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
        )

    @staticmethod
    def _get_redis_cluster_with_ssl(config: RedisConfig):
        if config is None:
            config = {}
        return RedisCluster(
            startup_nodes=AsyncRedisUtils._get_startup_nodes_of_redis_cluster(config),
            password=config.passwd,
            ssl_cert_reqs=ssl.CERT_REQUIRED,
            ssl_ca_certs=config.ssl_ca_certs,
            ssl_certfile=config.ssl_certfile,
            ssl_keyfile=config.ssl_keyfile,
            ssl_password=config.ssl_passwd,
            decode_responses=False,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            max_connections=config.max_connections,
        )

    @staticmethod
    def _get_startup_nodes_of_redis_cluster(config: RedisConfig) -> List[ClusterNode]:
        """
        获取Redis集群节点host与port配置列表
        """
        startup_nodes_str = config.cluster_node
        startup_nodes_list = [
            startup_node.strip() for startup_node in startup_nodes_str.split(",")
        ]
        startup_nodes = []
        try:
            for startup_node in startup_nodes_list:
                host, port = startup_node.split(":")
                startup_nodes.append(ClusterNode(host=host, port=int(port)))
            return startup_nodes
        except Exception as e:
            raise JiuWenBaseException(
                error_code=StatusCode.REDIS_CLUSTER_NODES_CONFIGURATION_ERROR.code,
                message=StatusCode.REDIS_CLUSTER_NODES_CONFIGURATION_ERROR.errmsg,
            ) from e

    @staticmethod
    def _get_connection_pool_without_ssl(config: RedisConfig):
        """Get connection pool without ssl"""
        if config is None:
            config = {}
        return redis.ConnectionPool(
            host=config.host,
            port=config.port,
            db=config.db,
            password=config.passwd,
            max_connections=config.max_connections,
            socket_timeout=config.socket_timeout,
        )

    @staticmethod
    def _get_redis_cluster_without_ssl(config: RedisConfig):
        if config is None:
            config = {}
        return RedisCluster(
            startup_nodes=AsyncRedisUtils._get_startup_nodes_of_redis_cluster(config),
            password=config.passwd,
            decode_responses=False,
            socket_timeout=config.socket_timeout,
            socket_connect_timeout=config.socket_connect_timeout,
            max_connections=config.max_connections,
        )

    async def init(self):
        """init"""
        pass

    @redis_call_handler.handle
    async def list_append(self, key, *values, ttl):
        """
        向列表尾部添加一个或多个值
        """
        try:
            await self._redis.expire(self._process_key(key), ttl)
            return await self._redis.rpush(self._process_key(key), *values)
        except Exception as e:
            logger.error(
                f"Error adding element: {e}", simple_log="Error adding element"
            )
            raise JiuWenBaseException(
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.code,
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_insert(self, key, index, value):
        """
        在列表的指定位置插入值
        """
        try:
            return await self._redis.linsert(
                self._process_key(key), "AFTER", index, value
            )
        except Exception as e:
            logger.error(f"error inserting element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.code,
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_remove(self, key, count, value):
        """
        从列表中移除元素
        """
        try:
            return await self._redis.lrem(self._process_key(key), count, value)
        except Exception as e:
            logger.error(
                f"Error removing element: {e}", simple_log="Error removing element."
            )
            raise JiuWenBaseException(
                StatusCode.REDIS_REMOVE_ELEMENTS_FAILED.code,
                StatusCode.REDIS_REMOVE_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_set(self, key, index, value):
        """
        设置列表在指定位置的值
        """
        try:
            await self._redis.lset(self._process_key(key), index, value)
            return True
        except redis.RedisError as e:
            logger.error(f"Error setting element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_SET_SPECIFIED_ELEMENTS_FAILED.code,
                StatusCode.REDIS_SET_SPECIFIED_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_get(self, key, start=0, end=-1):
        """
        获取列表中一段元素
        """
        try:
            return await self._redis.lrange(self._process_key(key), start, end)
        except Exception as e:
            logger.error(f"Error getting list: {e}", simple_log="Error getting list.")
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_LIST_ELEMENTS_FAILED.code,
                StatusCode.REDIS_GET_LIST_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_contain(self, key):
        """
        确认是否存在某个key
        """
        try:
            return await self._redis.exists(self._process_key(key))
        except Exception as e:
            logger.error(f"Error getting list: {e}", simple_log="Error getting list")
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_LIST_ELEMENTS_FAILED.code,
                StatusCode.REDIS_GET_LIST_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_pop(self, key):
        """
        从列表头部弹出元素
        """
        try:
            return await self._redis.lpop(self._process_key(key))
        except Exception as e:
            logger.error(f"Error ejecting element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_POP_ELEMENTS_FAILED.code,
                StatusCode.REDIS_POP_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_tail_pop(self, key):
        """
        从列表尾部弹出元素, 栈
        """
        try:
            return await self._redis.rpop(self._process_key(key))
        except Exception as e:
            logger.error(f"Error ejecting tail element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_POP_ELEMENTS_FAILED.code,
                StatusCode.REDIS_POP_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def list_length(self, key):
        """
        获取列表长度
        """
        try:
            return await self._redis.llen(self._process_key(key))
        except Exception as e:
            logger(f"获取列表长度时出错: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_LENGTH_ELEMENTS_FAILED.code,
                StatusCode.REDIS_GET_LENGTH_ELEMENTS_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def get(self, key):
        """
        根据k获取Redis中的元素
        """
        try:
            logger.info("start to get element from redis")
            return await self._redis.get(self._process_key(key))
        except Exception as e:
            logger.error(
                f"Error getting element from redis, the key is {self._process_key(key)}",
                simple_log="Error getting element from redis.",
            )
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_ELEMENT_FAILED.code,
                StatusCode.REDIS_GET_ELEMENT_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def set(
        self,
        key,
        value,
        ex=int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL)),
        nx=False,
    ):
        """
        向Redis中的添加元素
        """
        try:
            logger.info("start to set element to redis")
            return await self._redis.set(self._process_key(key), value, ex, None, nx)
        except Exception as e:
            logger.error(
                f"Error setting element to redis, the key is {self._process_key(key)}",
                simple_log="Error setting element to redis.",
            )
            raise JiuWenBaseException(
                StatusCode.REDIS_SET_ELEMENT_FAILED.code,
                StatusCode.REDIS_SET_ELEMENT_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def delete(self, key):
        """
        从Redis中的删除元素
        """
        try:
            return await self._redis.delete(self._process_key(key))
        except Exception as e:
            logger.error(
                f"Error deleting element from redis, the key is {self._process_key(key)}"
            )
            raise JiuWenBaseException(
                StatusCode.REDIS_DELETE_ELEMENT_FAILED.code,
                StatusCode.REDIS_DELETE_ELEMENT_FAILED.errmsg,
            ) from e

    @redis_call_handler.handle
    async def ping(self):
        """
        测试Redis是否正常连接
        """
        try:
            return await self._redis.ping()
        except Exception as e:
            logger.error("Error ping redis")
            raise JiuWenBaseException(
                StatusCode.REDIS_SERVICE_NOT_FOUND.code,
                StatusCode.REDIS_SERVICE_NOT_FOUND.errmsg,
            ) from e

    async def hash_set(self, name, key=None, value=None, mapping=None, ex: int = None):
        """
        redis hset() 方法的定时过期封装。
        """
        try:
            ex = ex or int(os.getenv(DATASOURCE_REDIS_TTL_KEY, DEFAULT_REDIS_TTL))
            num = await self._redis.hset(name, key, value, mapping)
            await self._redis.expire(name, ex)
            return num
        except Exception as e:
            logger.error(f"Error adding element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.code,
                StatusCode.REDIS_INSERT_ELEMENTS_FAILED.errmsg,
            ) from e

    async def hash_get(self, name, key):
        """
        redis hget() 方法的封装。
        """
        try:
            return await self._redis.hget(name, key)
        except Exception as e:
            logger.error(f"Error adding element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_ELEMENT_FAILED.code,
                StatusCode.REDIS_GET_ELEMENT_FAILED.errmsg,
            ) from e

    async def hash_getall(self, name):
        """
        redis hgetall() 方法的封装。
        """
        try:
            return await self._redis.hgetall(name)
        except Exception as e:
            logger.error(f"Error adding element: {e}")
            raise JiuWenBaseException(
                StatusCode.REDIS_GET_ELEMENT_FAILED.code,
                StatusCode.REDIS_GET_ELEMENT_FAILED.errmsg,
            ) from e

    def get_redis_client(self):
        """
        返回redis client实例
        """
        return self._redis

    def _process_key(self, key: str):
        """
        为Redis key添加前缀
        """
        return key if not self._prefix else self._prefix + key


def get_redis_config() -> RedisConfig:
    """
    Get redis config from the environment.
    """
    redis_config = RedisConfig(
        host=os.getenv(DATASOURCE_REDIS_HOST_KEY) or DEFAULT_REDIS_HOST,
        port=os.getenv(DATASOURCE_REDIS_PORT_KEY) or DEFAULT_REDIS_PORT,
        passwd=os.getenv(DATASOURCE_REDIS_PASSWORD_KEY),
        ssl_mode=str(
            os.environ.get(DATASOURCE_REDIS_SSL_MODE_KEY, DEFAULT_REDIS_SSL_MODE)
        ).lower(),
        ssl_passwd=os.getenv(DATASOURCE_REDIS_SSL_PASSWD_KEY, ""),
        cluster_node=os.getenv(DATASOURCE_REDIS_CLUSTER_NODE_KEY, ""),
        ssl_ca_certs=os.environ.get(DATASOURCE_REDIS_SSL_CA_CERTS_KEY, ""),
        ssl_certfile=os.environ.get(DATASOURCE_REDIS_SSL_CERTFILE_KEY, ""),
        ssl_keyfile=os.environ.get(DATASOURCE_REDIS_SSL_KEYFILE_KEY, ""),
        ttl=int(os.getenv(DATASOURCE_REDIS_TTL_KEY) or DEFAULT_REDIS_TTL),
        db=int(os.getenv(DATASOURCE_REDIS_DATABASE_KEY) or DEFAULT_REDIS_DB),
        max_connections=int(
            os.getenv(DATASOURCE_REDIS_MAX_CONNECTIONS_KEY)
            or DEFAULT_REDIS_MAX_CONNECTIONS
        ),
        mode=os.getenv(DATASOURCE_REDIS_MODE_KEY) or RedisMode.SINGLE.value,
        socket_timeout=int(
            os.getenv(DATASOURCE_REDIS_SOCKET_TIMEOUT_KEY) or DEFAULT_SOCKET_TIMEOUT
        ),
        socket_connect_timeout=int(
            os.getenv(DATASOURCE_REDIS_SOCKET_CONNECT_TIMEOUT_KEY)
            or DEFAULT_SOCKET_CONNECT_TIMEOUT
        ),
        prefix=os.getenv(DATASOURCE_REDIS_PREFIX_KEY) or DEFAULT_PREFIX,
    )
    return redis_config


def get_async_redis_instance(redis_config: Optional[RedisConfig] = None):
    """
    获取Redis实例
    根据配置
    """
    if redis_config is None:
        redis_config = get_redis_config()
    ssl_passwd = redis_config.ssl_passwd
    ssl_mode = redis_config.ssl_mode
    curr_work_api = Crypt()
    redis_config.passwd = curr_work_api.decrypt(redis_config.passwd)
    if ssl_mode != "false":
        # 当用户未关闭ssl加密认证的时候，ssl_passwd为必填项
        if ssl_passwd:
            redis_config.ssl_passwd = curr_work_api.decrypt(ssl_passwd)
        else:
            logger.error(
                "An error occurred while initializing the Redis: ssl_passwd is necessary when SSL is enabled."
            )
            raise JiuWenBaseException(
                error_code=StatusCode.REDIS_SERVICE_INIT_FAILED.code,
                message=StatusCode.REDIS_SERVICE_INIT_FAILED.errmsg,
            )

    return AsyncRedisUtils(redis_config)
