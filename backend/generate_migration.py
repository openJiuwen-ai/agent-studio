#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一生成 Alembic 迁移脚本工具
 
支持同时为 MySQL 和 SQLite 数据库生成迁移脚本，
避免分别为每个数据库执行迁移命令。

使用方法:
    python generate_migration.py -m "Add user status field"
    python generate_migration.py --autogenerate -m "Update schema"
    python generate_migration.py --manual -m "Custom migration"
"""

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# 配置日志
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)


class MigrationGenerator:
    """迁移脚本生成器"""

    def __init__(self):
        """
        初始化生成器
        """
        self.backend_dir = Path(__file__).parent.absolute()

        self.alembic_ini = self.backend_dir / "alembic.ini"

        # 定义所有需要生成迁移脚本的数据库配置
        self.databases = [
            {
                "name": "mysql_agent",
                "config": "alembic_mysql_agent",
                "description": "MySQL Agent Database"
            },
            {
                "name": "mysql_ops",
                "config": "alembic_mysql_ops",
                "description": "MySQL Ops Database"
            },
            {
                "name": "sqlite_agent",
                "config": "alembic_sqlite_agent",
                "description": "SQLite Agent Database"
            },
            {
                "name": "sqlite_ops",
                "config": "alembic_sqlite_ops",
                "description": "SQLite Ops Database"
            }
        ]

    def validate_environment(self) -> bool:
        """
        验证环境配置

        Returns:
            bool: 环境是否有效
        """
        # 检查 alembic.ini 是否存在
        if not self.alembic_ini.exists():
            logger.error(f"找不到 alembic.ini 文件: {self.alembic_ini}")
            return False

        return True

    def generate_migration(
        self,
        message: str,
        autogenerate: bool = False,
        database: str = None
    ) -> List[Tuple[str, bool, str]]:
        """
        生成迁移脚本

        Args:
            message: 迁移描述信息
            autogenerate: 是否自动生成（基于模型变化）
            database: 指定数据库，None 表示所有数据库

        Returns:
            List[Tuple[str, bool, str]]: (数据库名称, 是否成功, 文件路径/错误信息)
        """
        results = []

        # 确定要处理的数据库
        if database:
            target_databases = [db for db in self.databases if db["name"] == database]
            if not target_databases:
                logger.error(f"未找到数据库配置: {database}")
                return results
        else:
            target_databases = self.databases

        logger.info(f"{'='*60}")
        logger.info(f"开始生成迁移脚本: {message}")
        logger.info(f"模式: {'自动生成' if autogenerate else '手动创建'}")
        logger.info(f"数据库: {[db['description'] for db in target_databases]}")
        logger.info(f"{'='*60}")

        for db in target_databases:
            success, result = self._generate_single_migration(
                db["config"],
                message,
                autogenerate
            )

            results.append((db["name"], success, result))

            if success:
                logger.info(f"{db['description']}: {result}")
            else:
                logger.error(f"{db['description']}: {result}")

        return results

    def _generate_single_migration(
        self,
        config_name: str,
        message: str,
        autogenerate: bool
    ) -> Tuple[bool, str]:
        """
        为单个数据库生成迁移脚本

        Args:
            config_name: Alembic 配置名称
            message: 迁移描述
            autogenerate: 是否自动生成

        Returns:
            Tuple[bool, str]: (是否成功, 文件路径或错误信息)
        """
        try:
            # 根据配置名称确定数据库类型
            if "mysql" in config_name:
                db_type = "mysql"
            elif "sqlite" in config_name:
                db_type = "sqlite"
            else:
                db_type = "mysql"  # 默认

            # 准备环境变量，动态注入 DB_TYPE
            # 这对于模型代码中基于 DB_TYPE 的条件判断至关重要
            env = os.environ.copy()
            env["DB_TYPE"] = db_type

            # 构建 alembic 命令
            cmd = [
                "alembic",
                "-n", config_name,
                "revision",
                "-m", message
            ]

            if autogenerate:
                cmd.append("--autogenerate")

            # 执行命令时传入修改后的环境变量
            logger.info(f"执行: {' '.join(cmd)} (DB_TYPE={db_type})")
            result = subprocess.run(
                cmd,
                cwd=self.backend_dir,
                env=env,  # 传入包含正确 DB_TYPE 的环境变量
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                # 从输出中提取生成的文件路径
                output = result.stdout.strip()
                if "done" in output.lower() or "generating" in output.lower():
                    # 提取文件路径（通常在 "Generating <path> ... done" 中）
                    lines = output.split('\n')
                    for line in lines:
                        if 'Generating' in line or 'generating' in line:
                            file_path = line.split()[-1].rstrip('...')
                            return True, file_path
                    return True, "生成成功"
                else:
                    return True, output
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, f"命令失败: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, "命令执行超时"
        except Exception as e:
            return False, f"异常: {str(e)}"

    @staticmethod
    def print_summary(results: List[Tuple[str, bool, str]]) -> int:
        """
        打印生成结果摘要

        Args:
            results: 生成结果列表

        Returns:
            int: 0 表示全部成功，1 表示部分失败
        """
        logger.info(f"{'='*60}")
        logger.info("生成结果摘要")
        logger.info(f"{'='*60}")

        success_count = sum(1 for _, success, _ in results if success)
        total_count = len(results)

        for db_name, success, result in results:
            status = "成功" if success else "失败"
            if success:
                logger.info(f"{status:8} | {db_name:15} | {result}")
            else:
                logger.error(f"{status:8} | {db_name:15} | {result}")

        logger.info(f"总计: {success_count}/{total_count} 个数据库成功")

        if success_count == total_count:
            logger.info("所有迁移脚本生成成功！")
            return 0
        else:
            logger.warning(f"{total_count - success_count} 个数据库生成失败")
            return 1


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="统一生成 MySQL 和 SQLite 迁移脚本工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 为所有数据库自动生成迁移脚本
  python generate_migration.py --autogenerate -m "Add user status field"

  # 为所有数据库手动创建空白迁移脚本
  python generate_migration.py --manual -m "Custom migration logic"

  # 只为 MySQL Agent 数据库生成迁移脚本
  python generate_migration.py -d mysql_agent -m "Update agent schema"

  # 为 SQLite 数据库生成迁移脚本
  python generate_migration.py -d sqlite_agent -d sqlite_ops -m "Update SQLite schema"
        """
    )

    parser.add_argument(
        "-m", "--message",
        required=True,
        help="迁移描述信息"
    )

    parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="自动生成迁移脚本（基于模型变化）"
    )

    parser.add_argument(
        "--manual",
        action="store_true",
        help="手动创建空白迁移脚本"
    )

    parser.add_argument(
        "-d", "--database",
        action="append",
        choices=["mysql_agent", "mysql_ops", "sqlite_agent", "sqlite_ops"],
        help="指定数据库（可多次使用，默认为所有数据库）"
    )


    args = parser.parse_args()

    # 验证参数
    if not args.autogenerate and not args.manual:
        logger.error("请指定 --autogenerate 或 --manual")
        parser.print_help()
        return 1

    if args.autogenerate and args.manual:
        logger.error("--autogenerate 和 --manual 不能同时使用")
        return 1

    # 创建生成器
    generator = MigrationGenerator()

    # 验证环境
    if not generator.validate_environment():
        return 1

    # 生成迁移脚本
    autogenerate = args.autogenerate
    databases = args.database

    if databases and len(databases) == 1:
        results = generator.generate_migration(
            message=args.message,
            autogenerate=autogenerate,
            database=databases[0]
        )
    else:
        results = generator.generate_migration(
            message=args.message,
            autogenerate=autogenerate
        )

    # 打印摘要
    return MigrationGenerator.print_summary(results)


if __name__ == "__main__":
    sys.exit(main())
