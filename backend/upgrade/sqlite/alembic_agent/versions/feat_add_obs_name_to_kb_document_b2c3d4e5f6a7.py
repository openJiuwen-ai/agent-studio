#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2026. All rights reserved.
"""add obs_name to knowledge_base_document (OBS support for KB)

Revision ID: b2c3d4e5f6a7
Revises: 8f4846812221
Create Date: 2026-03-02

"""
from typing import Sequence, Union

from alembic import op
from openjiuwen_studio.core.database.migration_utils import column_exists, table_exists
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "8f4846812221"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add obs_name column for OBS object path (distributed KB)."""
    if not table_exists("knowledge_base_document"):
        return
    if column_exists("knowledge_base_document", "obs_name"):
        return
    with op.batch_alter_table("knowledge_base_document", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "obs_name",
                sa.String(length=1000),
                nullable=False,
                server_default=sa.text("''"),
            )
        )


def downgrade() -> None:
    """Remove obs_name column."""
    if not table_exists("knowledge_base_document"):
        return
    if not column_exists("knowledge_base_document", "obs_name"):
        return
    with op.batch_alter_table("knowledge_base_document", schema=None) as batch_op:
        batch_op.drop_column("obs_name")
