# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""OpenAPI 文档归档器 — 服务启动后自动将 FastAPI 生成的 OpenAPI 文档转储到本地目录。

触发条件：
1. API_DOCS_ENABLED=true — 文档端点已开启（由调用方保证，仅当 docs_enabled 时调用）
2. docs/ 目录存在 — 从 CWD 向上查找（最多 5 级），找到则归档，否则视为 Docker 环境跳过

归档路径可通过 OPENAPI_ARCHIVE_DIR 环境变量配置，默认 docs/api/studio-runtime。
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

ARCHIVE_DIR = os.environ.get("OPENAPI_ARCHIVE_DIR", "docs/api/studio-runtime")


def _find_project_root():
    """从 CWD 向上查找包含 docs/ 的目录（项目根目录）。

    最多向上查找 5 级，找不到返回 None（Docker 环境无源码目录）。
    """
    p = Path.cwd()
    for _ in range(5):
        if (p / "docs").is_dir():
            return p
        if p.parent == p:
            break
        p = p.parent
    return None


def archive_openapi_docs(app):
    """归档 OpenAPI 文档（YAML）到本地目录。

    在 FastAPI lifespan 启动阶段调用，app 已就绪。
    从 CWD 向上查找 docs/ 目录，找不到则视为 Docker 环境静默跳过。
    """
    project_root = _find_project_root()
    if project_root is None:
        logger.info("[OpenAPI] docs/ not found, skipping archiving (likely Docker environment)")
        return

    archive_path = project_root / ARCHIVE_DIR
    archive_path.mkdir(parents=True, exist_ok=True)

    spec = app.openapi()

    yaml_file = archive_path / "openapi.yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(spec, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    logger.info(f"[OpenAPI] Archived: {yaml_file}")

    logger.info(f"[OpenAPI] Archive complete. Check git diff for changes: git diff --stat {archive_path}")
