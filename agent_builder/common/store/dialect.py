# -*- coding: utf-8 -*-
"""
Database dialect abstraction — handles SQL syntax differences between MySQL and GaussDB.

MySQL: backtick quoting, %s placeholders, REPLACE INTO, SHOW TABLES
GaussDB: no quoting, inline values, ON CONFLICT, CREATE IF NOT EXISTS
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class Dialect(ABC):
    """Abstract dialect — subclasses handle specific database SQL syntax."""

    @abstractmethod
    def quote(self, identifier: str) -> str:
        """Quote an identifier (table/column name)."""

    @abstractmethod
    def col_alias(self, name: str) -> str:
        """Map column name for reserved word compatibility (e.g. desc -> job_desc for GaussDB)."""

    @abstractmethod
    def from_alias(self, name: str) -> str:
        """Map alias back to original column name (e.g. job_desc -> desc for GaussDB)."""

    @abstractmethod
    def supports_paramized(self) -> bool:
        """Whether this dialect supports %s parameterized queries."""

    @abstractmethod
    def create_table_sql(self, table_name: str, fields_str: str, pk_str: str) -> str:
        """Generate CREATE TABLE SQL. Return empty string if table already exists check is done separately."""

    @abstractmethod
    def check_table_exists_sql(self, table_name: str) -> str:
        """Generate SQL to check if a table exists. Return empty string if CREATE IF NOT EXISTS handles it."""

    @abstractmethod
    def upsert_sql(
        self,
        table_name: str,
        cols: str,
        val_list: str,
        conflict_cols: str,
        update_cols: str,
    ) -> str:
        """Generate INSERT/UPSERT SQL."""

    @abstractmethod
    def alter_column_type_sql(self, table_name: str, column_name: str, new_type: str) -> str:
        """Generate ALTER COLUMN TYPE SQL."""

    @abstractmethod
    def describe_column_type_sql(self, table_name: str, column_name: str) -> str:
        """Generate SQL to get current column type."""

    def escape_value(self, value) -> str:
        """Escape a Python value for inline SQL usage."""
        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        if isinstance(value, int):
            return str(value)
        if isinstance(value, float):
            return str(value)
        if isinstance(value, str):
            escaped = value.replace("'", "''")
            return f"'{escaped}'"
        return f"'{str(value).replace(chr(39), chr(39)+chr(39))}'"


class MysqlDialect(Dialect):
    """MySQL dialect — backtick quoting, %s placeholders, REPLACE INTO."""

    def quote(self, identifier: str) -> str:
        return f"`{identifier}`"

    def col_alias(self, name: str) -> str:
        return name

    def from_alias(self, name: str) -> str:
        return name

    def supports_paramized(self) -> bool:
        return True

    def check_table_exists_sql(self, table_name: str) -> str:
        return f"SHOW TABLES LIKE '{table_name}';"

    def create_table_sql(self, table_name: str, fields_str: str, pk_str: str) -> str:
        return f"CREATE TABLE `{table_name}` ({fields_str}, PRIMARY KEY({pk_str}));"

    def upsert_sql(
        self,
        table_name: str,
        cols: str,
        val_list: str,
        conflict_cols: str,
        update_cols: str,
    ) -> str:
        return f"REPLACE INTO {table_name} ({cols}) VALUES ({val_list});"

    def alter_column_type_sql(self, table_name: str, column_name: str, new_type: str) -> str:
        return f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` {new_type}"

    def describe_column_type_sql(self, table_name: str, column_name: str) -> str:
        return f"DESCRIBE `{table_name}`"


class GaussDBDialect(Dialect):
    """GaussDB dialect — no quoting, inline values, ON CONFLICT upsert, CREATE IF NOT EXISTS."""

    _RESERVED_WORDS = {"desc"}

    def quote(self, identifier: str) -> str:
        return identifier

    def col_alias(self, name: str) -> str:
        if name in self._RESERVED_WORDS:
            return f"job_{name}"
        return name

    def from_alias(self, name: str) -> str:
        if name == "job_desc":
            return "desc"
        return name

    def supports_paramized(self) -> bool:
        return False

    def check_table_exists_sql(self, table_name: str) -> str:
        return ""

    def create_table_sql(self, table_name: str, fields_str: str, pk_str: str) -> str:
        return f"CREATE TABLE IF NOT EXISTS {table_name} ({fields_str}, PRIMARY KEY({pk_str}));"

    def upsert_sql(
        self,
        table_name: str,
        cols: str,
        val_list: str,
        conflict_cols: str,
        update_cols: str,
    ) -> str:
        if update_cols:
            return f"INSERT INTO {table_name} ({cols}) VALUES ({val_list}) ON DUPLICATE KEY UPDATE {update_cols};"
        return f"INSERT INTO {table_name} ({cols}) VALUES ({val_list}) ON DUPLICATE KEY UPDATE {update_cols};"

    def alter_column_type_sql(self, table_name: str, column_name: str, new_type: str) -> str:
        return f"ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {new_type}"

    def describe_column_type_sql(self, table_name: str, column_name: str) -> str:
        return (
            "SELECT data_type FROM information_schema.columns "
            f"WHERE table_name = '{table_name}' AND column_name = '{column_name}'"
        )


def get_dialect() -> Dialect:
    """Get the appropriate dialect based on STORE_DB_TYPE config."""
    from agent_builder.adapter.config_bridge import settings

    if settings.db_config.db_type == "gaussdb":
        return GaussDBDialect()
    return MysqlDialect()
