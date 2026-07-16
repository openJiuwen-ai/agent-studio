# -*- coding: utf-8 -*-
"""
Database utils — supports MySQL (pymysql) and GaussDB (py_opengauss).

Provides DBUtil (connection + execution) and DBTable (CRUD helpers).
Database type is determined by STORE_DB_TYPE env var: "mysql" or "gaussdb" (default: mysql).
Connection params are read from agent_builder.adapter.config_bridge.settings.db_config.
"""

import threading
from typing import List, Dict, Any

from agent_builder.common.exception.status_code import StatusCode
from agent_builder.common.logging.base import logger
from agent_builder.adapter.exception_bridge import JiuWenBaseException
from agent_builder.common.store.dialect import get_dialect, Dialect
from agent_builder.adapter.config_bridge import settings
from pydantic import BaseModel

VALID_TABLES = {"job_info", "optimize_info", "progress", "history", "cases"}

DEFAULT_WR_TIMEOUT: int = 60


def _is_gaussdb() -> bool:
    return settings.db_config.db_type == "gaussdb"


class DBUtil:
    """Database operation — supports MySQL and GaussDB."""

    _instance = None
    _singleton_lock = threading.Lock()
    _rw_lock = threading.Lock()

    @classmethod
    def instance(cls, reconnect=False):
        """Get a database connection instance."""
        if cls._instance is None or reconnect:
            with cls._singleton_lock:
                if cls._instance is None or reconnect:
                    db = settings.db_config
                    host = db.host
                    port = db.port
                    user = db.user
                    password = db.password
                    database = db.database

                    if not host or not user or not database:
                        raise JiuWenBaseException(
                            StatusCode.MYSQL_CHECK_CONFIG_ERROR.code,
                            StatusCode.MYSQL_CHECK_CONFIG_ERROR.errmsg.format(
                                errno=-1, reason="Database config incomplete, check STORE_DB_* env vars"
                            ),
                        )

                    try:
                        if _is_gaussdb():
                            import py_opengauss

                            hosts = [h.strip() for h in host.split(",") if h.strip()]
                            port_val = port or "5432"
                            host_list = ",".join([f"{h}:{port_val}" for h in hosts])
                            # 密码不进 URI：py_opengauss.open() 内部用 iri.parse() 不做百分号解码，
                            # 若用 quote_plus 编码后拼进 URI，含 # @ / ? 等特殊字符的密码会被破坏
                            # 导致认证失败。改为通过 password 关键字参数直传，规避 URI 编解码问题。
                            iri = f"opengauss://{user}@{host_list}/{database}"
                            if db.sslmode and db.sslmode != "disable":
                                iri += f"?sslmode={db.sslmode}"
                            # schema 模式（仅 GaussDB 生效）：通过 search_path 设置默认 schema，
                            # 之后不带前缀的表名按此路径解析。schema 为空则不传，使用数据库默认。
                            connect_kw = {"password": password}
                            if db.db_schema:
                                connect_kw["settings"] = {"search_path": db.db_schema}
                            cls._instance = py_opengauss.open(iri, **connect_kw)
                            logger.info(f"GaussDB connected (auto-primary): {host_list}")
                        else:
                            import pymysql

                            port_val = int(port or "3306")
                            single_host = host.split(",")[0].strip()
                            cls._instance = pymysql.connect(
                                host=single_host,
                                port=port_val,
                                user=user,
                                password=password,
                                database=database,
                                read_timeout=DEFAULT_WR_TIMEOUT,
                                write_timeout=DEFAULT_WR_TIMEOUT,
                            )
                            logger.info(f"MySQL connected: {single_host}:{port_val}")
                    except Exception as e:
                        cls._instance = None
                        raise JiuWenBaseException(
                            StatusCode.MYSQL_CHECK_CONFIG_ERROR.code,
                            StatusCode.MYSQL_CHECK_CONFIG_ERROR.errmsg.format(
                                errno=-1, reason=str(e)
                            ),
                        ) from e

        return cls._instance

    @classmethod
    def execute(cls, sql_str, fetch_all: bool = True, params=None):
        """Execute SQL command."""
        with cls._rw_lock:
            try:
                return cls._do_execute(sql_str, fetch_all, params)
            except Exception as first_error:
                logger.warning(f"SQL execution failed, reconnecting: {first_error}")
                try:
                    cls.instance(reconnect=True)
                    return cls._do_execute(sql_str, fetch_all, params)
                except Exception as e:
                    raise JiuWenBaseException(
                        error_code=StatusCode.MYSQL_EXECUTION_ERROR.code,
                        message=StatusCode.MYSQL_EXECUTION_ERROR.errmsg.format(
                            errno=-1, reason=str(e)
                        ),
                    ) from e

    @classmethod
    def _do_execute(cls, sql_str, fetch_all, params):
        if _is_gaussdb():
            return cls._do_execute_gaussdb(sql_str, fetch_all, params)
        else:
            return cls._do_execute_mysql(sql_str, fetch_all, params)

    @classmethod
    def _do_execute_mysql(cls, sql_str, fetch_all, params):
        cursor = cls._instance.cursor()
        cursor.execute(sql_str, params)
        cls._instance.commit()
        data = cursor.fetchall() if fetch_all else cursor.fetchone()
        cursor.close()
        return data

    @classmethod
    def _do_execute_gaussdb(cls, sql_str, fetch_all, params):
        stmt = cls._instance.prepare(sql_str)
        if params is not None:
            if isinstance(params, (list, tuple)):
                result = stmt(*params)
            else:
                result = stmt(params)
        else:
            result = stmt()

        if result is None:
            return [] if fetch_all else None

        try:
            rows = list(result)
        except TypeError:
            return [] if fetch_all else None

        if not rows:
            return [] if fetch_all else None

        for row in rows:
            if row is None or not isinstance(row, (tuple, list)):
                return [] if fetch_all else None

        if fetch_all:
            return [tuple(row) for row in rows]
        else:
            return tuple(rows[0])

    @classmethod
    def reset(cls):
        """Reset singleton instance for testing"""
        with cls._singleton_lock:
            cls._instance = None


class DBTable:
    """Table operation helpers — delegates SQL generation to Dialect."""

    class Field(BaseModel):
        name: str = ""
        type: str = ""
        is_not_null: bool = True
        others: List[str] = None

    def __init__(self, table_name: str, fields: List[Field], primary_keys: List[str]):
        self._table_name = table_name
        self._primary_keys = primary_keys
        self._fields = fields
        self._dialect: Dialect = get_dialect()

    @property
    def table_name(self) -> str:
        return self._table_name

    @property
    def fields(self) -> List[Field]:
        return self._fields

    @property
    def dialect(self) -> Dialect:
        return self._dialect

    def _q(self, name: str) -> str:
        return self._dialect.quote(self._dialect.col_alias(name))

    @staticmethod
    def _cast(field: "DBTable.Field", value):
        """Cast value to Python type based on field type (needed for GaussDB text-mode results)."""
        if value is None:
            return None
        if not isinstance(value, str):
            return value
        t = field.type.upper()
        if "INT" in t:
            try:
                return int(value)
            except (ValueError, TypeError):
                return value
        float_types = ("FLOAT", "DOUBLE", "DECIMAL", "NUMERIC", "REAL")
        if any(ft in t for ft in float_types):
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        if t == "BOOLEAN":
            return value.lower() in ("true", "1", "yes")
        return value

    def create(self):
        """create table"""
        check_sql = self._dialect.check_table_exists_sql(self._table_name)
        if check_sql:
            result = DBUtil.execute(check_sql)
            if result:
                return

        fields_str = ", ".join(
            [
                f"{self._q(f.name)} {f.type} {'NOT NULL' if f.is_not_null else ''}"
                for f in self._fields
            ]
        )
        pk_str = ", ".join([self._q(k) for k in self._primary_keys])
        sql = self._dialect.create_table_sql(self._table_name, fields_str, pk_str)
        DBUtil.execute(sql)

    def insert(self, values: Dict[str, Any]):
        """insert or upsert values"""
        self._validate_insert_values(values)
        cols = ", ".join([self._q(f.name) for f in self._fields])

        if self._dialect.supports_paramized():
            placeholders = ", ".join(["%s"] * len(self._fields))
            condition_values = tuple(values[f.name] for f in self._fields)
            conflict_cols = ", ".join([self._q(k) for k in self._primary_keys])
            update_cols = ", ".join(
                [f"{self._q(f.name)} = {self._q(f.name)}" for f in self._fields if f.name not in self._primary_keys]
            )
            sql = self._dialect.upsert_sql(self._table_name, cols, placeholders, conflict_cols, update_cols)
            DBUtil.execute(sql, params=condition_values)
        else:
            val_list = ", ".join([self._dialect.escape_value(values[f.name]) for f in self._fields])
            conflict_cols = ", ".join([self._q(k) for k in self._primary_keys])
            update_cols = ", ".join(
                [
                    f"{self._q(f.name)} = VALUES({self._q(f.name)})"
                    for f in self._fields
                    if f.name not in self._primary_keys
                ]
            )
            sql = self._dialect.upsert_sql(self._table_name, cols, val_list, conflict_cols, update_cols)
            DBUtil.execute(sql)

    def update(self, field: str, value: Any, **conditions: Dict[str, Any]):
        """update values"""
        if self._table_name not in VALID_TABLES:
            raise ValueError("database update failed caused by illegal table name")
        if field not in [f.name for f in self._fields]:
            raise ValueError("database update failed caused by illegal field name")

        if self._dialect.supports_paramized():
            set_clause = f"{self._q(field)} = %s"
            conditions_sql = " AND ".join([f"{self._q(k)} = %s" for k in conditions])
            sql = f"UPDATE {self._dialect.quote(self._table_name)} SET {set_clause} WHERE {conditions_sql};"
            params = (value,) + tuple(conditions.values())
            DBUtil.execute(sql, params=params)
        else:
            set_clause = f"{self._q(field)} = {self._dialect.escape_value(value)}"
            conditions_sql = " AND ".join(
                [f"{self._q(k)} = {self._dialect.escape_value(v)}" for k, v in conditions.items()]
            )
            sql = f"UPDATE {self._table_name} SET {set_clause} WHERE {conditions_sql};"
            DBUtil.execute(sql)

    def exists(self, **conditions: Dict[str, Any]) -> bool:
        """exists values"""
        if not conditions:
            return False

        if self._dialect.supports_paramized():
            condition_keys = []
            condition_values = []
            for key, value in conditions.items():
                condition_keys.append(f"{self._q(key)}=%s")
                condition_values.append(value)
            conditions_sql = " AND ".join(condition_keys)
            sql = f"SELECT * FROM {self._dialect.quote(self._table_name)} WHERE {conditions_sql}"
            result = DBUtil.execute(sql, params=condition_values)
        else:
            conditions_sql = " AND ".join(
                [f"{self._q(k)} = {self._dialect.escape_value(v)}" for k, v in conditions.items()]
            )
            sql = f"SELECT * FROM {self._table_name} WHERE {conditions_sql}"
            result = DBUtil.execute(sql)
        return len(result) > 0

    def query(self, target: str = "*", **conditions: Dict[str, Any]) -> Dict[str, Any]:
        """query values"""
        if target != "*" and target not in [field.name for field in self.fields]:
            raise ValueError("database query failed caused by illegal target")
        if not conditions:
            return {}

        if self._dialect.supports_paramized():
            condition_keys = []
            condition_values = []
            for key, value in conditions.items():
                condition_keys.append(f"{self._q(key)}=%s")
                condition_values.append(value)
            conditions_sql = " AND ".join(condition_keys)
            sql = f"SELECT {target} FROM {self._dialect.quote(self._table_name)} WHERE {conditions_sql}"
            result = DBUtil.execute(sql, params=condition_values, fetch_all=False)
        else:
            conditions_sql = " AND ".join(
                [f"{self._q(k)} = {self._dialect.escape_value(v)}" for k, v in conditions.items()]
            )
            col = "*" if target == "*" else self._q(target)
            sql = f"SELECT {col} FROM {self._table_name} WHERE {conditions_sql}"
            result = DBUtil.execute(sql, fetch_all=False)

        if not result:
            return {}

        output = {}
        if target == "*":
            for field, value in zip(self._fields, result):
                output[field.name] = self._cast(field, value)
        else:
            target_field = next((f for f in self._fields if f.name == target), None)
            output[target] = self._cast(target_field, result[0]) if target_field else result[0]

        return output

    def batch_query(
        self, target: str = "*", **conditions: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """query batch values"""
        if target != "*" and target not in [field.name for field in self.fields]:
            raise ValueError("database query failed caused by illegal target")
        if not conditions:
            return []

        if self._dialect.supports_paramized():
            condition_keys = []
            condition_values = []
            for key, value in conditions.items():
                condition_keys.append(f"{self._q(key)}=%s")
                condition_values.append(value)
            conditions_sql = " AND ".join(condition_keys)
            sql = f"SELECT {target} FROM {self._dialect.quote(self._table_name)} WHERE {conditions_sql}"
            results = DBUtil.execute(sql, params=condition_values)
        else:
            conditions_sql = " AND ".join(
                [f"{self._q(k)} = {self._dialect.escape_value(v)}" for k, v in conditions.items()]
            )
            col = "*" if target == "*" else self._q(target)
            sql = f"SELECT {col} FROM {self._table_name} WHERE {conditions_sql}"
            results = DBUtil.execute(sql)

        if not results:
            return []

        output = []
        for res in results:
            output.append(dict())
            for field, value in zip(self._fields, res):
                output[-1][field.name] = self._cast(field, value)

        return output

    def delete(self, **conditions: Dict[str, Any]):
        """delete values"""
        if not conditions:
            return

        if self._dialect.supports_paramized():
            condition_keys = []
            condition_values = []
            for key, value in conditions.items():
                condition_keys.append(f"{self._q(key)}=%s")
                condition_values.append(value)
            conditions_sql = " AND ".join(condition_keys)
            sql = f"DELETE FROM {self._dialect.quote(self._table_name)} WHERE {conditions_sql}"
            DBUtil.execute(sql, fetch_all=False, params=condition_values)
        else:
            conditions_sql = " AND ".join(
                [f"{self._q(k)} = {self._dialect.escape_value(v)}" for k, v in conditions.items()]
            )
            sql = f"DELETE FROM {self._table_name} WHERE {conditions_sql}"
            DBUtil.execute(sql, fetch_all=False)

    def _validate_insert_values(self, values: Dict[str, Any]) -> bool:
        """validate values"""
        if len(values) != len(self._fields):
            raise JiuWenBaseException(
                error_code=StatusCode.MYSQL_SQL_COMMAND_ERROR.code,
                message=StatusCode.MYSQL_SQL_COMMAND_ERROR.errmsg.format(
                    error_msg=f"table {self._table_name} expects {len(self._fields)} fields: {self._fields},"
                    f"but got {len(values)} values.",
                ),
            )

        for key in values:
            if key not in set([f.name for f in self._fields]):
                raise JiuWenBaseException(
                    error_code=StatusCode.MYSQL_SQL_COMMAND_ERROR.code,
                    message=StatusCode.MYSQL_SQL_COMMAND_ERROR.errmsg.format(
                        error_msg=f"table {self._table_name} has no column '{key}'"
                    ),
                )
        return True
