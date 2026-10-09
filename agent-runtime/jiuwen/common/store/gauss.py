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
            from psycopg2.pool import SimpleConnectionPool
            cls.ctx_pool = SimpleConnectionPool(
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
            retry_times:
            max_retry_times:
        Returns:

        """
        con = None
        cursor = None
        try:
            con = cls.ctx_pool.get_connection()
            cursor = con.cursor()
            yield cursor
            con.commit()
        except psycopg2.OperationalError:
            if retry_times < max_retry_times:
                return
            logger.error(
                "psycopg2.OperationalError: %s"
                % str(StatusCode.DATABASE_EXECUTE_ERROR),
                exc_info=True,
            )
            raise
        except psycopg2.Error:
            if retry_times < max_retry_times:
                return
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
            cls.ctx_pool.put_connection(con)

    @classmethod
    def execute_values(cls, sql, args_list, fetch=False):
        """
        多语句批量执行，每个对应args_list中的一组positional arguments
        """
        for times in range(3):
            with cls.get_cursor(times) as cur:
                return execute_values(cur, sql, args_list, fetch=fetch)

    @classmethod
    def execute(cls, sql, args):
        """
        单语句执行，无返回值
        """
        for times in range(3):
            with cls.get_cursor(times) as cur:
                return cur.execute(sql, args)

    @classmethod
    def query(cls, sql, args=None):
        """
        单语句查询，有返回值
        """
        for times in range(3):
            with cls.get_cursor(times) as cur:
                cur.execute(sql, args)
                rows = cur.fetchall()
                return rows

    @classmethod
    def query_return_cols(cls, sql, args=None):
        """
        单语句查询，返回值和列名
        """
        for times in range(3):
            with cls.get_cursor(times) as cur:
                cur.execute(sql, args)
                rows = cur.fetchall()
                return rows, [desc[0] for desc in cur.description]

    @classmethod
    def delete(cls, sql, args):
        """
        执行删除操作，返回被删除的行数
        """
        for times in range(3):
            with cls.get_cursor(times) as cur:
                cur.execute(sql, args)
                return cur.rowcount
