#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from __future__ import annotations
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from typing import Any

from sqlalchemy import (JSON, BigInteger, Boolean, ForeignKey, ForeignKeyConstraint,
                        Index, Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import (Mapped, declarative_mixin,
                            declared_attr, mapped_column, relationship)

from openjiuwen_studio.models.db_fun_base import Base, DBFunBase
from openjiuwen_studio.ops.config import settings


@declarative_mixin
class PluginDBMixin:
    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        primary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    name: Mapped[str | None] = mapped_column(String(255), nullable=True, name="plugin_name")
    desc: Mapped[str | None] = mapped_column(String(512), nullable=True, name="desc")
    desc_mk: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    url: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    space_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon_uri: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    plugin_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # 通用 JSON，MySQL/PostgreSQL/SQLite 均支持
    tools: Mapped[list[dict] | None] = mapped_column(JSON, default=None, nullable=True)
    inputs: Mapped[list[dict] | None] = mapped_column(JSON, default=None, nullable=True, name="inputs")
    _rest_: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)

    create_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)


# ==================== tbl_plugin ====================
class PluginBaseDB(PluginDBMixin, Base, DBFunBase):
    __tablename__ = "plugin"
    __table_args__ = (
        UniqueConstraint(
            "plugin_id", "plugin_version",
            name="unique_plugin_id_version"
        ),
        Index("idx_space_id", "space_id"),
    )

    plugin_id: Mapped[str] = mapped_column(String(100), index=True, unique=True, nullable=False)
    plugin_version: Mapped[str | None] = mapped_column(String(100), default=DBFunBase.__version_none__)

    @declared_attr
    def plugin_publish_list(cls):
        return relationship(
            "PluginPublishDB",
            back_populates="plugin_draft",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )

    @declared_attr
    def tool_list(cls):
        return relationship(
            "ToolBaseDB",
            back_populates="plugin_info",
            cascade="all, delete-orphan",
            passive_deletes=True,
        )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"plugin_id={self.plugin_id}, "
            f"plugin_version={self.plugin_version}, "
            f"plugin_name='{self.name})>"
        )


# ==================== tbl_plugin_publish ====================
class PluginPublishDB(PluginDBMixin, Base, DBFunBase):
    __tablename__ = "plugin_publish"
    __table_args__ = (
        UniqueConstraint(
            "plugin_id", "plugin_version",
            name="unique_plugin_id_version"
        ),
        ForeignKeyConstraint(
            ['plugin_id'],  # 子表的列
            ['plugin.plugin_id'],  # 父表的列
            ondelete="CASCADE"  # 数据库级联删除
        ),
        Index("idx_space_id", "space_id"),
    )

    plugin_id: Mapped[str] = mapped_column(String(100),
                                    ForeignKey("plugin.plugin_id", ondelete="CASCADE"),
                                    nullable=False,
                                    index=True,
                                    )
    plugin_version: Mapped[str] = mapped_column(String(100), nullable=False)
    version_desc: Mapped[str | None] = mapped_column(String(512))

    plugin_draft: Mapped[PluginBaseDB] = relationship(
        "PluginBaseDB",
        foreign_keys=plugin_id,
        back_populates="plugin_publish_list",
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"workflow_id={self.plugin_id}, "
            f"workflow_version={self.plugin_version}, "
            f"workflow_name='{self.name})>"
        )


PluginBaseDBPd = PluginBaseDB.sqlalchemy_to_pydantic(exclude={"primary_id", })
PluginPublishDBPd = PluginPublishDB.sqlalchemy_to_pydantic(exclude={"primary_id", })


class ToolBaseDB(Base, DBFunBase):
    __tablename__ = "tool"
    __table_args__ = (
        UniqueConstraint(
            "tool_id", "plugin_version",
            name="unique_tool_id_version"
        ),
        ForeignKeyConstraint(
            ['plugin_id', 'plugin_version'],  # 子表的列
            ['plugin.plugin_id', 'plugin.plugin_version'],  # 父表的列
            ondelete="CASCADE"  # 数据库级联删除
        ),
        Index("idx_space_id", "space_id"),
    )

    if settings.DB_TYPE.lower() == "sqlite":
        primary_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, name="id")
    else:
        primary_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, name="id")

    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, name="tool_name")
    desc: Mapped[str | None] = mapped_column(String(512), nullable=True, name="desc")
    space_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False)
    plugin_type: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    plugin_version: Mapped[str | None] = mapped_column(String(100), default=DBFunBase.__version_none__)

    input_parameters: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=None, nullable=True)
    output_parameters: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, default=None, nullable=True)
    available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    _rest_: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True)

    create_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    update_time: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    plugin_info: Mapped[PluginBaseDB] = relationship(
        "PluginBaseDB",
        back_populates="tool_list",
        foreign_keys=[plugin_id, plugin_version]
    )

    def __repr__(self) -> str:
        return (
            f"<{self.__tablename__}("
            f"space_id='{self.space_id}', "
            f"tool_id={self.tool_id}, "
            f"plugin_version={self.plugin_version}, "
            f"tool_name='{self.name})>"
        )