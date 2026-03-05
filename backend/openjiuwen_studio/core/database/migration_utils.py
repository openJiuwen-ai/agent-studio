#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from alembic import op
from sqlalchemy import inspect


def table_exists(table_name: str) -> bool:
    """Check if table exists in current database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return inspector.has_table(table_name)


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if column exists in table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    columns = [c['name'] for c in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(table_name: str, index_name: str) -> bool:
    """Check if index exists on table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    indexes = [i['name'] for i in inspector.get_indexes(table_name)]
    return index_name in indexes


def unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    """Check if unique constraint exists on table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return False
    constraints = inspector.get_unique_constraints(table_name)
    return any(c['name'] == constraint_name for c in constraints)
