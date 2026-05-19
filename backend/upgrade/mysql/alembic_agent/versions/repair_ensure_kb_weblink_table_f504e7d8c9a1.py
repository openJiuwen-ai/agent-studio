#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
"""Repair: ensure knowledge_base_weblink exists (idempotent).

Some databases reached a later alembic revision without this table ever being
created. This revision re-applies the same DDL as feat_add_kb_weblink_d2e3f4a5b6c7.

Revision ID: f504e7d8c9a1
Revises: e6f7a8b9c0d1
Create Date: 2026-05-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from openjiuwen_studio.core.database.migration_utils import index_exists, table_exists

revision: str = "f504e7d8c9a1"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if table_exists("knowledge_base_weblink"):
        return
    op.create_table(
        "knowledge_base_weblink",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "space_id",
            sa.String(length=100),
            nullable=False,
            comment="空间ID，用于多租户隔离",
        ),
        sa.Column("kb_id", sa.String(length=100), nullable=False, comment="知识库ID"),
        sa.Column(
            "weblink_id",
            sa.String(length=100),
            nullable=False,
            comment="链接ID，唯一标识",
        ),
        sa.Column("url", sa.Text(), nullable=False, comment="源 URL"),
        sa.Column(
            "name",
            sa.String(length=500),
            nullable=False,
            comment="展示名（解析后可为标题）",
        ),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=True,
            comment="web_page / wechat_article",
        ),
        sa.Column("status", sa.String(length=50), nullable=False, comment="链接状态"),
        sa.Column("index_manager_type", sa.String(length=200), nullable=True),
        sa.Column("index_id", sa.String(length=200), nullable=True),
        sa.Column("index_name", sa.String(length=200), nullable=True),
        sa.Column("chunk_count", sa.BigInteger(), nullable=True),
        sa.Column("process_info", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("_rest_", sa.JSON(), nullable=True),
        sa.Column("create_time", sa.BigInteger(), nullable=True),
        sa.Column("update_time", sa.BigInteger(), nullable=True),
        sa.Column("indexed_time", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("weblink_id", name="uix_weblink_id"),
        comment="知识库网页链接表，存储链接元数据信息",
    )
    if not index_exists("knowledge_base_weblink", "idx_space_id"):
        op.create_index(
            "idx_space_id", "knowledge_base_weblink", ["space_id"], unique=False
        )
    if not index_exists("knowledge_base_weblink", "idx_kb_id"):
        op.create_index("idx_kb_id", "knowledge_base_weblink", ["kb_id"], unique=False)
    if not index_exists("knowledge_base_weblink", "idx_space_kb"):
        op.create_index(
            "idx_space_kb",
            "knowledge_base_weblink",
            ["space_id", "kb_id"],
            unique=False,
        )
    if not index_exists("knowledge_base_weblink", "idx_status"):
        op.create_index("idx_status", "knowledge_base_weblink", ["status"], unique=False)
    if not index_exists("knowledge_base_weblink", "idx_space_kb_weblink"):
        op.create_index(
            "idx_space_kb_weblink",
            "knowledge_base_weblink",
            ["space_id", "kb_id", "weblink_id"],
            unique=False,
        )


def downgrade() -> None:
    """No-op: do not drop table; may contain user data."""
    pass
