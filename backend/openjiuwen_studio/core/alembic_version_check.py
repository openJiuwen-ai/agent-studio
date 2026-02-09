#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alembic 版本检测模块

在应用启动时检测数据库版本，并给出迁移提示
"""

import os
import logging
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from sqlalchemy import inspect, text, create_engine

from openjiuwen_studio.core.database import engine
from openjiuwen_studio.ops.config import settings as ops_settings

logger = logging.getLogger(__name__)

# 临时开启 DEBUG 日志（用于调试）
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class AlembicVersionChecker:
    """Alembic 版本检测器"""

    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent.parent.absolute()
        self.versions_dirs = {
            "mysql_agent": self.backend_dir / "upgrade" / "mysql" / "alembic_agent" / "versions",
            "mysql_ops": self.backend_dir / "upgrade" / "mysql" / "alembic_ops" / "versions",
            "sqlite_agent": self.backend_dir / "upgrade" / "sqlite" / "alembic_agent" / "versions",
            "sqlite_ops": self.backend_dir / "upgrade" / "sqlite" / "alembic_ops" / "versions",
        }

    def check_all_databases(self) -> bool:
        """
        检查所有数据库的版本

        Returns:
            bool: True 表示所有数据库都是最新版本，False 表示有数据库需要更新
        """
        db_type = os.getenv("DB_TYPE", "mysql").lower()

        logger.info("=" * 80)
        logger.info("📊 Alembic 版本检测")
        logger.info("=" * 80)

        all_up_to_date = True

        # 检查 agent 数据库
        agent_status = self._check_agent_database(db_type)
        if not agent_status["up_to_date"]:
            all_up_to_date = False
            AlembicVersionChecker._print_migration_guide("agent", db_type, agent_status)

        # 检查 ops 数据库
        ops_status = self._check_ops_database(db_type)
        if not ops_status["up_to_date"]:
            all_up_to_date = False
            AlembicVersionChecker._print_migration_guide("ops", db_type, ops_status)

        logger.info("=" * 80)

        if all_up_to_date:
            logger.info("✅ 所有数据库版本都是最新的")
        else:
            logger.warning("⚠️  检测到数据库版本需要更新，请按照上述提示执行迁移命令")

        return all_up_to_date

    def _check_agent_database(self, db_type: str) -> Dict:
        """检查 agent 数据库版本"""
        try:
            # 使用已有的 agent 数据库引擎
            return self._check_database_version(engine, "agent", db_type)
        except Exception as e:
            logger.error("检查 agent 数据库版本失败: %s", e)
            return {"up_to_date": False, "current": None, "latest": None, "table_exists": False}

    def _check_ops_database(self, db_type: str) -> Dict:
        """检查 ops 数据库版本"""
        try:
            # 创建 ops 数据库引擎连接
            from openjiuwen_studio.core.config import settings

            if settings.db_type.lower() == "sqlite":
                sqlite_db = ops_settings.SQLITE_DB if hasattr(ops_settings, 'SQLITE_DB') else "ops.db"
                sqlite_db_path = getattr(ops_settings, 'SQLITE_DB_PATH', 'data/databases')

                # 确保路径是绝对路径
                if not os.path.isabs(sqlite_db_path):
                    backend_dir = Path(__file__).parent.parent.parent.absolute()
                    sqlite_db_path = os.path.join(backend_dir, sqlite_db_path)

                if not os.path.isabs(sqlite_db):
                    sqlite_db = os.path.join(sqlite_db_path, sqlite_db)

                ops_url = f"sqlite:///{sqlite_db}"
            else:
                # MySQL
                db_user = getattr(ops_settings, 'DB_USER', None) or os.getenv("DB_USER")
                db_password = getattr(ops_settings, 'DB_PASSWORD', None) or os.getenv("DB_PASSWORD")
                db_host = getattr(ops_settings, 'DB_HOST', None) or os.getenv("DB_HOST")
                db_port = getattr(ops_settings, 'DB_PORT', None) or os.getenv("DB_PORT")
                db_name = getattr(ops_settings, 'OPS_DB_NAME', None) or os.getenv("OPS_DB_NAME")

                if all([db_user, db_password, db_host, db_port, db_name]):
                    ops_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                else:
                    raise ValueError("Missing database connection parameters")

            ops_engine = create_engine(ops_url)
            return self._check_database_version(ops_engine, "ops", db_type)
        except Exception as e:
            logger.error("检查 ops 数据库版本失败: %s", e)
            return {"up_to_date": False, "current": None, "latest": None, "table_exists": False}

    def _check_database_version(self, db_engine, db_name: str, db_type: str) -> Dict:
        """
        检查数据库版本

        Args:
            db_engine: SQLAlchemy engine（要检查的数据库引擎）
            db_name: 数据库名称 (agent/ops)
            db_type: 数据库类型 (mysql/sqlite)

        Returns:
            Dict: 版本信息
        """
        inspector = inspect(db_engine)

        # 检查 alembic_version 表是否存在
        if "alembic_version" not in inspector.get_table_names():
            logger.warning("❌ %s 数据库: 未找到 alembic_version 表", db_name)
            latest_version = self._get_latest_version(db_name, db_type)
            return {
                "up_to_date": False,
                "current": None,
                "latest": latest_version,
                "table_exists": False
            }

        # 查询当前版本
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.fetchone()
            current_version = row[0] if row else None

        # 获取最新版本
        latest_version = self._get_latest_version(db_name, db_type)

        if not latest_version:
            logger.error("❌ %s 数据库: 无法获取最新版本", db_name)
            return {
                "up_to_date": False,
                "current": current_version,
                "latest": None,
                "table_exists": True
            }

        # 对比版本
        if current_version == latest_version:
            logger.info("✅ %s 数据库: 版本已是最新 (%s)", db_name, current_version)
            return {
                "up_to_date": True,
                "current": current_version,
                "latest": latest_version,
                "table_exists": True
            }
        else:
            logger.warning("⚠️  %s 数据库: 当前版本 %s, 最新版本 %s", db_name, current_version, latest_version)
            return {
                "up_to_date": False,
                "current": current_version,
                "latest": latest_version,
                "table_exists": True
            }

    def _get_latest_version(self, db_name: str, db_type: str) -> Optional[str]:
        """
        获取最新的 Alembic 版本号

        优先使用 alembic heads 命令，失败时回退到文件扫描

        Args:
            db_name: 数据库名称 (agent/ops)
            db_type: 数据库类型 (mysql/sqlite)

        Returns:
            Optional[str]: 最新版本号
        """
        config_name = f"alembic_{db_type}_{db_name}"
        logger.info("正在获取 %s 的最新版本...", config_name)

        # 方案1：优先使用 alembic heads 命令（最准确）
        try:
            logger.debug("执行命令: alembic -n %s heads", config_name)
            result = subprocess.run(
                ["alembic", "-n", config_name, "heads"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.backend_dir
            )

            logger.debug("命令返回码: %s", result.returncode)
            if result.stdout:
                logger.debug("命令标准输出:\n%s", result.stdout)
            if result.stderr:
                logger.debug("命令标准错误:\n%s", result.stderr)

            if result.returncode == 0:
                # 解析输出: "7883f1b07bc2 (head)" 或 "Rev: 7883f1b07bc2 (head)"
                # 支持两种格式
                match = re.search(r'([a-f0-9]{12})\s*\(head\)', result.stdout)
                if match:
                    revision_id = match.group(1)
                    logger.info("✓ 使用 alembic heads 获取版本: %s -> %s", config_name, revision_id)
                    return revision_id
                else:
                    logger.warning("alembic heads 输出格式无法解析: %s", result.stdout)
            else:
                logger.warning("alembic heads 命令返回非零状态码: %s", result.returncode)
        except FileNotFoundError:
            logger.warning("alembic 命令未找到，回退到文件扫描")
        except subprocess.TimeoutExpired:
            logger.warning("alembic heads 命令超时，回退到文件扫描")
        except Exception as e:
            logger.warning("alembic heads 命令失败: %s: %s，回退到文件扫描", type(e).__name__, e)

        # 方案2：回退到文件扫描（基于依赖关系，兼容性更好）
        logger.info("回退到文件扫描方式获取版本...")
        key = f"{db_type}_{db_name}"
        versions_dir = self.versions_dirs.get(key)

        logger.debug("版本目录: %s", versions_dir)

        if not versions_dir or not versions_dir.exists():
            logger.error("版本目录不存在: %s", versions_dir)
            return None

        version_files = [
            f for f in versions_dir.glob("*.py")
            if f.name != "__init__.py"
        ]

        logger.debug("找到 %s 个版本文件", len(version_files))

        if not version_files:
            logger.error("未找到版本文件: %s", versions_dir)
            return None

        # 解析所有文件的 revision 并构建依赖关系
        revisions = {}
        for idx, version_file in enumerate(version_files):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                    # 提取 revision
                    revision_match = re.search(r"revision\s*[:=]\s*['\"]([^'\"]+)['\"]", content)
                    # 提取 down_revision
                    down_match = re.search(r"down_revision\s*[:=]\s*(.+)", content)

                    if revision_match:
                        revision_id = revision_match.group(1)
                        down_revision = None
                        if down_match:
                            down_val = down_match.group(1).strip()
                            # 处理 None 或 'revision_id'
                            if down_val != "None":
                                down_revision = down_val.strip("'\",")

                        revisions[revision_id] = {
                            'down_revision': down_revision,
                            'file': version_file
                        }
                        logger.debug(
                            "[%s/%s] 解析成功: %s (down: %s)",
                            idx + 1, len(version_files), revision_id, down_revision
                        )
            except Exception as e:
                logger.warning("读取版本文件失败 %s: %s", version_file, e)

        logger.info("成功解析 %s 个迁移版本", len(revisions))

        if not revisions:
            logger.error("没有成功解析任何迁移版本")
            return None

        # 找到所有 head（没有其他版本指向它的版本）
        all_down_revisions = {r['down_revision'] for r in revisions.values() if r['down_revision']}
        heads = [rev_id for rev_id in revisions.keys() if rev_id not in all_down_revisions]

        logger.debug("找到 %s 个 head 版本: %s", len(heads), heads)

        if heads:
            # 通常只有一个 head，如果有多个返回第一个
            head_id = heads[0]
            logger.info("✓ 通过文件扫描获取版本: %s -> %s", config_name, head_id)
            return head_id
        else:
            logger.error("无法通过依赖关系确定 head，迁移文件可能存在问题")
            logger.debug("所有版本: %s", list(revisions.keys()))
            logger.debug("所有 down_revision: %s", all_down_revisions)

        return None

    @staticmethod
    def _print_migration_guide(db_name: str, db_type: str, status: Dict):
        """
        打印迁移指南

        Args:
            db_name: 数据库名称 (agent/ops)
            db_type: 数据库类型 (mysql/sqlite)
            status: 版本状态
        """
        current = status.get("current")
        latest = status.get("latest")
        table_exists = status.get("table_exists", False)

        logger.info("\n📋 %s 数据库迁移指南:", db_name.upper())
        logger.info("-" * 80)

        if not table_exists:
            # 数据库没有 alembic_version 表，需要 stamp
            logger.info("状态: 数据库未初始化 Alembic 版本控制")
            logger.info("操作: 需要标记当前数据库版本，请检查数据库对应的版本id")
            logger.info("")
            logger.info("请执行以下命令:")
            logger.info("  alembic -n alembic_%s_%s stamp your_db_revision_id", db_type, db_name)
            logger.info("")
            logger.info("说明: 此命令将数据库标记为指定版本，不会执行任何迁移操作")

        elif current != latest:
            # 版本不是最新，需要 upgrade
            logger.info("状态: 数据库版本需要更新")
            logger.info("当前版本: %s", current)
            logger.info("最新版本: %s", latest)


def check_alembic_versions() -> bool:
    """
    检查所有数据库的 Alembic 版本

    Returns:
        bool: True 表示所有数据库都是最新版本
    """
    try:
        checker = AlembicVersionChecker()
        return checker.check_all_databases()
    except Exception as e:
        logger.error("Alembic 版本检测失败: %s", e)
        return False


if __name__ == "__main__":
    # 测试代码
    check_alembic_versions()
