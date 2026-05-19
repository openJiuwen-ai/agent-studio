#!/usr/bin/python3.10
# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


def find_env_file():
    current_dir_env = Path(__file__).parent / ".env"
    parent_dir_env = Path(__file__).parent.parent / ".env"
    for env_path in [parent_dir_env, current_dir_env]:
        if env_path.exists():
            return env_path

    return None


class Settings(BaseSettings):
    # 数据库类型配置 (mysql/sqlite)
    DB_TYPE: Optional[str] = Field(default=None, env="DB_TYPE")

    # mysql配置
    DB_HOST: Optional[str] = Field(default=None, env="DB_HOST")
    DB_PORT: Optional[int] = Field(default=None, env="DB_PORT")
    DB_USER: Optional[str] = Field(default=None, env="DB_USER")
    DB_PASSWORD: Optional[str] = Field(default=None, env="DB_PASSWORD")
    OPS_DB_NAME: Optional[str] = Field(default=None, env="OPS_DB_NAME")
    AGENT_DB_NAME: Optional[str] = Field(default=None, env="AGENT_DB_NAME")

    # sqlite配置
    SQLITE_DB_PATH: Optional[str] = Field(default=None, env="SQLITE_DB_PATH")
    OPS_SQLITE_DB: Optional[str] = Field(default=None, env="OPS_SQLITE_DB")
    AGENT_SQLITE_DB: Optional[str] = Field(default=None, env="AGENT_SQLITE_DB")

    # 应用配置
    DEBUG: bool = Field(False, env="DEBUG")
    AUTO_SYNC_DB: bool = Field(False, env="AUTO_SYNC_DB")

     # 按 DB_TYPE 校验必选字段
    @model_validator(mode="after")
    def validate_db_config(self):
        db_type = self.DB_TYPE.lower()

        # MySQL 场景：校验 MySQL 配置必选
        if db_type == "mysql":
            required_fields = [
                ("DB_HOST", self.DB_HOST),
                ("DB_PORT", self.DB_PORT),
                ("DB_USER", self.DB_USER),
                ("DB_PASSWORD", self.DB_PASSWORD),
                ("OPS_DB_NAME", self.OPS_DB_NAME),
                ("AGENT_DB_NAME", self.AGENT_DB_NAME)
            ]
            for field_name, field_value in required_fields:
                if field_value is None:
                    raise ValueError(f"【MySQL】字段 {field_name} 为必选，请配置环境变量")

        # SQLite 场景：校验 SQLite 配置必选
        elif db_type == "sqlite":
            required_fields = [
                ("SQLITE_DB_PATH", self.SQLITE_DB_PATH),
                ("OPS_SQLITE_DB", self.OPS_SQLITE_DB),
                ("AGENT_SQLITE_DB", self.AGENT_SQLITE_DB)
            ]
            for field_name, field_value in required_fields:
                if field_value is None:
                    raise ValueError(f"【SQLite】字段 {field_name} 为必选，请配置环境变量")

        # 无数据库场景：不需要校验
        elif db_type == "none":
            pass

        # 不支持的数据库类型
        else:
            raise ValueError(f"不支持的数据库类型：{self.DB_TYPE}，仅支持 mysql/sqlite/none")

        return self

    class Config:
        env_file = find_env_file()
        extra = "allow"


@lru_cache()
def get_settings():
    """
    环境设置
    """
    return Settings()

settings = get_settings()


class ModelConfigManager:
    def __init__(self):
        self.model_config_path = Path(__file__).parent / "conf" / "model_config.yaml"
        self._load_model_config()

    def get_model_config(self, model_id: str):
        """
        获取指定模型配置
        """
        for model in self.model_config.get('models', []):
            if str(model.get('openModel', {}).get('model_id', '')) == str(model_id):
                return model
        return None

    def list_models(self) -> List[Dict[str, Any]]:
        """
        获取所有模型配置
        """
        return list(self.model_config.get('models', []))

    def _load_model_config(self):
        self.model_config = {}
        if os.path.exists(self.model_config_path):
            with open(self.model_config_path, "r", encoding="utf-8") as f:
                self.model_config = yaml.safe_load(f)