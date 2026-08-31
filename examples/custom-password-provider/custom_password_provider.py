# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""自定义 DataSourcePasswordProvider 示例：从环境变量获取数据库密码。

适用场景：数据库密码通过 K8s Secret 以环境变量注入，
配置文件中无需存储明文密码。

使用方式：
  1. 设置环境变量 DB_REAL_PASSWORD 为数据库真实密码
  2. 设置以下环境变量启用 CUSTOM 模式：
     export DATASOURCE_PASSWORD_PROVIDER_TYPE=CUSTOM
     export DATASOURCE_PASSWORD_PROVIDER_MODULE=/path/to/custom_password_provider.py
     export DATASOURCE_PASSWORD_PROVIDER_CLASS=EnvPasswordProvider
  3. 启动服务，密码将自动从 DB_REAL_PASSWORD 环境变量获取

与 Java 侧对齐：
  - Java  : 实现 DataSourcePasswordProvider 接口，打包为 JAR，通过 custom-classpath 加载
  - Python: 继承 DataSourcePasswordProvider，通过 DATASOURCE_PASSWORD_PROVIDER_MODULE 加载
"""

import os

from common_utils.password_provider import DataSourcePasswordProvider


class EnvPasswordProvider(DataSourcePasswordProvider):
    """从环境变量获取数据库密码的自定义实现。

    适用于容器化部署场景——密码通过 K8s Secret 以环境变量注入，
    配置文件中无需存储明文密码。
    """

    _ENV_KEY = "DB_REAL_PASSWORD"
    _LOG_PREFIX = "[EnvPasswordProvider]"

    def get_password(self, raw_password: str) -> str:
        password = os.environ.get(self._ENV_KEY, "")
        if not password:
            raise ValueError(
                f"{self._LOG_PREFIX} Environment variable '{self._ENV_KEY}' is not set, "
                "cannot obtain database password"
            )
        return password
