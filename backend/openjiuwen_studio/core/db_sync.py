#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.

"""
通用数据库模型同步工具
自动检测模型定义与数据库表结构的差异，并同步新增字段
"""

from typing import Any, Dict, List

from openjiuwen.core.common.logging import logger
from sqlalchemy import inspect, text

from openjiuwen_studio.core.database import engine
from openjiuwen_studio.models import (SystemLLMModelDB, SystemEmbeddingModelDB)


class DatabaseSync:
    """数据库模型同步器"""

    # 类型修改黑名单：跳过这些字段的自动类型修改
    # 格式: {"表名": ["字段名1", "字段名2", ...]}
    TYPE_SYNC_BLACKLIST = {
        "trace_detail": ["end_time_micros"],
    }

    def __init__(self, db_engine):
        self.engine = db_engine
        self.inspector = inspect(db_engine)

    def get_model_columns(self, model_class) -> Dict[str, Any]:
        """获取模型定义的列信息"""
        columns = {}
        for column in model_class.__table__.columns:
            columns[column.name] = {
                'type': str(column.type),
                'nullable': column.nullable,
                'default': column.default,
                'comment': getattr(column, 'comment', None)
            }
        return columns

    def get_table_columns(self, table_name: str) -> Dict[str, Any]:
        """获取数据库表的实际列信息"""
        try:
            columns = {}
            db_columns = self.inspector.get_columns(table_name)
            for column in db_columns:
                columns[column['name']] = {
                    'type': str(column['type']),
                    'nullable': column.get('nullable', True),
                    'default': column.get('default', None),
                    'comment': column.get('comment', None)
                }
            return columns
        except Exception as e:
            logger.warning(f"无法获取表 {table_name} 的列信息: {e}")
            return {}

    def get_missing_columns(self, model_class) -> List[str]:
        """获取模型中定义但数据库表中缺失的列"""
        table_name = model_class.__tablename__
        model_columns = self.get_model_columns(model_class)
        table_columns = self.get_table_columns(table_name)

        missing_columns = []
        for column_name in model_columns:
            if column_name not in table_columns:
                missing_columns.append(column_name)

        return missing_columns

    def get_type_mismatched_columns(self, model_class) -> Dict[str, Dict[str, str]]:
        """获取模型定义与数据库表类型不匹配的列

        返回: {列名: {'model_type': 模型中的类型, 'db_type': 数据库中的类型}}
        """
        table_name = model_class.__tablename__
        model_columns = self.get_model_columns(model_class)
        table_columns = self.get_table_columns(table_name)

        mismatched_columns = {}
        for column_name in model_columns:
            # 跳过黑名单中的字段
            if table_name in self.TYPE_SYNC_BLACKLIST and column_name in self.TYPE_SYNC_BLACKLIST[table_name]:
                continue

            if column_name in table_columns:
                model_type = model_columns[column_name]['type']
                db_type = table_columns[column_name]['type']
                # 类型规范化后比较
                if not self._types_match(model_type, db_type):
                    mismatched_columns[column_name] = {
                        'model_type': model_type,
                        'db_type': db_type
                    }

        return mismatched_columns

    @staticmethod
    def _types_match(model_type: str, db_type: str) -> bool:
        """比较两种类型是否匹配

        处理类型字符串的格式差异，如 "LONGTEXT" vs "longTEXT"
        忽略 COLLATE、CHARACTER SET 等修饰符
        """
        import re

        # 移除 COLLATE、CHARACTER SET 等修饰符
        def normalize_type(type_str: str) -> str:
            # 移除 COLLATE 子句
            type_str = re.sub(r'collate\s+"?\w+"?', '', type_str, flags=re.IGNORECASE)
            # 移除 CHARACTER SET 子句
            type_str = re.sub(r'character\s+set\s+\w+', '', type_str, flags=re.IGNORECASE)
            # 转换为小写并去除多余空格
            type_str = type_str.lower().strip()
            # 压缩多个空格为一个
            type_str = re.sub(r'\s+', ' ', type_str)
            return type_str

        model_normalized = normalize_type(model_type)
        db_normalized = normalize_type(db_type)

        # 处理等价类型映射
        # MySQL: BOOLEAN 就是 TINYINT(1) 的别名
        if set(['boolean', 'tinyint']) & set([model_normalized, db_normalized]):
            model_is_bool = 'boolean' in model_normalized
            db_is_bool = 'boolean' in db_normalized
            model_is_tinyint = 'tinyint' in model_normalized
            db_is_tinyint = 'tinyint' in db_normalized

            # 如果一个是 BOOLEAN 另一个是 TINYINT，视为等价
            if model_is_bool and db_is_tinyint:
                return True
            if model_is_tinyint and db_is_bool:
                return True

        # 直接比较核心类型
        return model_normalized == db_normalized

    def add_column_to_table(self, model_class, column_name: str):
        """向数据库表添加列"""
        table_name = model_class.__tablename__
        column = model_class.__table__.columns[column_name]

        # 获取数据库方言
        dialect_name = self.engine.dialect.name

        if dialect_name == 'mysql':
            # MySQL 使用反引号处理保留关键字
            alter_sql = f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {column.type}"
        elif dialect_name == 'postgresql':
            # PostgreSQL 使用双引号处理保留关键字
            alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {column.type}'
        else:
            # SQLite 等其他数据库
            alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column.type}"

        # 添加 NULL/NOT NULL 约束
        if not column.nullable:
            alter_sql += " NOT NULL"
        else:
            alter_sql += " NULL"

        # 添加默认值
        if column.default is not None:
            if hasattr(column.default, 'arg'):
                alter_sql += f" DEFAULT {column.default.arg}"
            else:
                alter_sql += f" DEFAULT {column.default}"

        # 添加注释（MySQL 支持）
        if dialect_name == 'mysql' and hasattr(column, 'comment') and column.comment:
            alter_sql += f" COMMENT '{column.comment}'"

        try:
            with self.engine.connect() as conn:
                conn.execute(text(alter_sql))
                conn.commit()
                logger.info(f"✅ 成功添加列 {column_name} 到表 {table_name}")
        except Exception as e:
            logger.error(f"❌ 添加列失败 {column_name} 到表 {table_name}: {e}")
            raise

    def modify_column_type(self, model_class, column_name: str, old_type: str, new_type: str):
        """修改数据库表中列的类型

        注意：类型转换可能导致数据丢失，请谨慎操作
        """
        table_name = model_class.__tablename__
        column = model_class.__table__.columns[column_name]

        # 获取数据库方言
        dialect_name = self.engine.dialect.name

        if dialect_name == 'mysql':
            # MySQL 使用 MODIFY COLUMN，需要加反引号处理保留关键字
            alter_sql = f"ALTER TABLE `{table_name}` MODIFY COLUMN `{column_name}` {column.type}"
        elif dialect_name == 'sqlite':
            # SQLite 不直接支持修改列类型，需要重建表
            # 这里抛出警告，建议使用其他方式处理
            logger.warning(
                f"⚠️ SQLite 不支持直接修改列类型 {table_name}.{column_name} "
                f"从 {old_type} 到 {new_type}。建议手动重建表或使用数据库迁移工具。"
            )
            return
        elif dialect_name == 'postgresql':
            # PostgreSQL 使用 ALTER COLUMN ... TYPE，使用双引号处理保留关键字
            alter_sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{column_name}" TYPE {column.type}'
        else:
            logger.warning(f"⚠️ 不支持的数据库方言: {dialect_name}")
            return

        try:
            with self.engine.connect() as conn:
                conn.execute(text(alter_sql))
                conn.commit()
                logger.info(f"✅ 成功修改列 {table_name}.{column_name} 类型: {old_type} -> {new_type}")
        except Exception as e:
            logger.error(f"❌ 修改列类型失败 {table_name}.{column_name}: {e}")
            raise

    def sync_model(self, model_class):
        """同步单个模型"""
        table_name = model_class.__tablename__

        try:
            # 检查表是否存在
            if not self.inspector.has_table(table_name):
                logger.info(f"📋 表 {table_name} 不存在，跳过字段同步")
                return

            # 获取缺失的列
            missing_columns = self.get_missing_columns(model_class)

            if missing_columns:
                logger.info(f"🔄 检测到表 {table_name} 缺少字段: {missing_columns}")

                # 添加缺失的列
                for column_name in missing_columns:
                    self.add_column_to_table(model_class, column_name)

                logger.info(f"✅ 表 {table_name} 字段同步完成")
            else:
                logger.info(f"✅ 表 {table_name} 字段已同步")

            # 检查并同步类型不匹配的列
            mismatched_columns = self.get_type_mismatched_columns(model_class)

            if mismatched_columns:
                logger.info(f"🔄 检测到表 {table_name} 字段类型不匹配: {mismatched_columns}")

                for column_name, type_info in mismatched_columns.items():
                    self.modify_column_type(
                        model_class,
                        column_name,
                        type_info['db_type'],
                        type_info['model_type']
                    )

                logger.info(f"✅ 表 {table_name} 字段类型同步完成")
            else:
                logger.info(f"✅ 表 {table_name} 字段类型已匹配")

        except Exception as e:
            logger.error(f"❌ 同步表 {table_name} 失败: {e}")
            raise

    def sync_all_models(self, model_classes: List):
        """同步所有模型"""
        logger.info("🔄 开始数据库模型同步...")

        for model_class in model_classes:
            try:
                self.sync_model(model_class)
            except Exception as e:
                logger.error(f"❌ 同步模型 {model_class.__name__} 失败: {e}")
                # 继续同步其他模型，不中断整个过程
                continue

        logger.info("✅ 数据库模型同步完成")


def get_all_model_classes():
    """动态获取所有模型类"""
    model_classes = []

    # 模型配置相关
    from openjiuwen_studio.models.model_config import ModelConfig, ModelUsageLog
    from openjiuwen_studio.models.embedding_model_config import EmbeddingModelConfig

    # 核心业务模型
    from openjiuwen_studio.models.agent import AgentBaseDB as _AgentBaseDB, AgentPublishDB
    from openjiuwen_studio.models.user import UserDB as _UserDB, SpaceDB as _SpaceDB, SpaceUserDB
    from openjiuwen_studio.models.workflow import WorkflowBaseDB as _WorkflowBaseDB, WorkflowPublishDB
    from openjiuwen_studio.models.plugin import PluginBaseDB as _PluginBaseDB, PluginPublishDB, ToolBaseDB

    # 执行相关模型
    from openjiuwen_studio.models.workflow_execution import WorkflowExecutionDB, WorkflowExecutionDetailsDB
    from openjiuwen_studio.models.agent_execution import AgentExecutionDB, AgentExecutionDetailsDB

    # 关联模型
    from openjiuwen_studio.models.prompt_relation import PromptRelationDB
    from openjiuwen_studio.models.tag import TagDB
    from openjiuwen_studio.models.awp_relation import AgentWorkflowRelationDB
    from openjiuwen_studio.models.reference import ReferenceDB

    # 追踪模型
    from openjiuwen_studio.models.trace_detail import TraceDetailDB
    from openjiuwen_studio.models.trace_summary import TraceSummaryDB

    # 知识库模型
    from openjiuwen_studio.models.knowledge_base import KnowledgeBaseDB
    from openjiuwen_studio.models.knowledge_base_document import KnowledgeBaseDocumentDB

    model_classes.extend([
        # 模型配置
        ModelConfig, ModelUsageLog, EmbeddingModelConfig,

        # 核心业务
        _AgentBaseDB, AgentPublishDB,
        _UserDB, _SpaceDB, SpaceUserDB,
        _WorkflowBaseDB, WorkflowPublishDB,
        _PluginBaseDB, PluginPublishDB, ToolBaseDB,

        # 执行相关
        WorkflowExecutionDB, WorkflowExecutionDetailsDB,
        AgentExecutionDB, AgentExecutionDetailsDB,

        # 关联模型
        PromptRelationDB, TagDB, AgentWorkflowRelationDB, ReferenceDB,

        # 追踪模型
        TraceDetailDB, TraceSummaryDB,

        # 知识库模型
        KnowledgeBaseDB, KnowledgeBaseDocumentDB,

        # 系统模型
        SystemLLMModelDB, SystemEmbeddingModelDB
    ])

    return model_classes


def run_database_sync():
    """运行数据库同步"""
    try:
        sync = DatabaseSync(engine)
        model_classes = get_all_model_classes()
        sync.sync_all_models(model_classes)

    except Exception as e:
        logger.error(f"❌ 数据库同步失败: {e}")
        raise


if __name__ == "__main__":
    run_database_sync()
