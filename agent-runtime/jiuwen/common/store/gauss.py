#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2023. All rights reserved.

"""
Database utils
"""

from contextlib import contextmanager

import psycopg2
from jiuwen.common.exception import JiuWenException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.common.store.config import GaussDBConfig
from psycopg2.extras import execute_values

DEFAULT_POOL_SIZE = 10


class DBUtil:
    """
    Database utils
    """

    db_config = None
    ctx_pool = None

    @classmethod
    def __new__(cls):
        raise JiuWenException("class DBUtil should not be instantiated")

    @classmethod
    def init(cls):
        """
        DButil init function
        Returns:

        """
        cls.db_config = cls.db_config or GaussDBConfig()
        if cls.ctx_pool is None:
            # ThreadedConnectionPool 线程安全，构造签名与 SimpleConnectionPool 一致；
            # DBUtil 为公共 store，execute/query 等会被并发调用，不能用非线程安全的 SimpleConnectionPool
            from psycopg2.pool import ThreadedConnectionPool
            cls.ctx_pool = ThreadedConnectionPool(
                minconn=cls.db_config.minconn,
                maxconn=cls.db_config.maxconn,
                host=cls.db_config.host,
                port=cls.db_config.port,
                user=cls.db_config.user,
                password=cls.db_config.password,
                dbname=cls.db_config.dbname,
                sslmode=cls.db_config.ssl_mode,
                sslrootcert=cls.db_config.ssl_root_cert,
                sslcert=cls.db_config.ssl_cert,
                sslkey=cls.db_config.ssl_key,
                connect_timeout=10,
                keepalives=cls.db_config.keepalives,
                keepalives_idle=cls.db_config.keepalives_idle,
                keepalives_interval=cls.db_config.keepalives_interval,
                keepalives_count=cls.db_config.keepalives_count,
            )

    @classmethod
    @contextmanager
    def get_cursor(cls, retry_times, max_retry_times=2):
        """
        get cursor of table
        Args:
            retry_times: 当前已重试次数，由调用方重试循环传入，仅用于决定日志级别
            max_retry_times:
        Returns:

        """
        con = None
        cursor = None
        committed = False
        try:
            # psycopg2 连接池的公开接口为 getconn/putconn，原 get_connection 并不存在
            con = cls.ctx_pool.getconn()
            cursor = con.cursor()
            yield cursor
            con.commit()
            committed = True
        except psycopg2.OperationalError:
            # 注意：@contextmanager 生成器在 yield 之前 return 会抛
            # RuntimeError: generator didn't yield，掩盖真实异常并使外层重试失效，
            # 因此所有异常分支必须 re-raise，由调用方捕获后重试
            if retry_times >= max_retry_times:
                logger.error(
                    "psycopg2.OperationalError: %s"
                    % str(StatusCode.DATABASE_EXECUTE_ERROR),
                    exc_info=True,
                )
            raise
        except psycopg2.Error:
            if retry_times >= max_retry_times:
                logger.error(
                    "execute sql error: %s" % str(StatusCode.DATABASE_EXECUTE_ERROR),
                    exc_info=True,
                )
            raise
        except Exception:
            logger.error("get_cursor unknown error", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            # 连接获取失败时 con 为 None，归还 None 会掩盖原始异常
            if con is not None:
                # psycopg2 连接池不会自动回滚，异常路径必须回滚，
                # 否则 aborted 事务状态的连接被复用导致后续 SQL 持续失败
                if not committed:
                    try:
                        con.rollback()
                    except Exception:
                        logger.warning(
                            "rollback failed before returning connection",
                            exc_info=True,
                        )
                cls.ctx_pool.putconn(con)

    @classmethod
    def execute_values(cls, sql, args_list, fetch=False):
        """
        多语句批量执行，每个对应args_list中的一组positional arguments
        """
        for times in range(3):
            try:
                with cls.get_cursor(times) as cur:
                    return execute_values(cur, sql, args_list, fetch=fetch)
            except psycopg2.Error:
                # get_cursor 现在正确抛出原始异常（不再 RuntimeError 掩盖），
                # 重试逻辑在此实现；psycopg2.OperationalError 是 psycopg2.Error 子类，一并重试
                if times >= 2:
                    raise

    @classmethod
    def execute(cls, sql, args):
        """
        单语句执行，无返回值
        """
        for times in range(3):
            try:
                with cls.get_cursor(times) as cur:
                    return cur.execute(sql, args)
            except psycopg2.Error:
                if times >= 2:
                    raise

    @classmethod
    def query(cls, sql, args=None):
        """
        单语句查询，有返回值
        """
        for times in range(3):
            try:
                with cls.get_cursor(times) as cur:
                    cur.execute(sql, args)
                    rows = cur.fetchall()
                    return rows
            except psycopg2.Error:
                if times >= 2:
                    raise

    @classmethod
    def query_return_cols(cls, sql, args=None):
        """
        单语句查询，返回值和列名
        """
        for times in range(3):
            try:
                with cls.get_cursor(times) as cur:
                    cur.execute(sql, args)
                    rows = cur.fetchall()
                    return rows, [desc[0] for desc in cur.description]
            except psycopg2.Error:
                if times >= 2:
                    raise

    @classmethod
    def delete(cls, sql, args):
        """
        执行删除操作，返回被删除的行数
        """
        for times in range(3):
            try:
                with cls.get_cursor(times) as cur:
                    cur.execute(sql, args)
                    return cur.rowcount
            except psycopg2.Error:
                if times >= 2:
                    raise
