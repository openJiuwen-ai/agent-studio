# -*- coding: utf-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""数据库密码获取抽象层。

与 Java 侧 DataSourcePasswordProvider 概念对齐，
与 Python 侧 OBS 自定义存储加载方式一致（STORAGE_CUSTOM_MODULE + STORAGE_CUSTOM_CLASS）：
  - DefaultDataSourcePasswordProvider: 默认实现，调用 crypto_tool.decrypt 解密
  - 自定义实现: 通过 DataBaseSettings 中的 password_provider_* 字段配置
    DATASOURCE_PASSWORD_PROVIDER_TYPE: DEFAULT（默认）/ CUSTOM
    DATASOURCE_PASSWORD_PROVIDER_MODULE: Python 模块路径或 .py 文件路径
    DATASOURCE_PASSWORD_PROVIDER_CLASS: 实现类名
"""

import importlib
import importlib.util
from abc import ABC, abstractmethod
from pathlib import Path

from .crypto_tool import decrypt as _crypto_decrypt


class DataSourcePasswordProvider(ABC):
    """数据库密码获取接口。"""

    @abstractmethod
    def get_password(self, raw_password: str) -> str:
        """获取数据库密码（明文）。

        Args:
            raw_password: 配置文件中的原始密码（可能为加密密文，也可能为明文）

        Returns:
            解密后的明文密码
        """
        ...


class DefaultDataSourcePasswordProvider(DataSourcePasswordProvider):
    """默认实现，使用 crypto_tool.decrypt 解密。"""

    def get_password(self, raw_password: str) -> str:
        if not raw_password:
            return raw_password
        return _crypto_decrypt(raw_password)


def get_password_provider(
    custom_module: str = "",
    custom_class: str = "",
) -> DataSourcePasswordProvider:
    """获取 DataSourcePasswordProvider 实例。

    Args:
        custom_module: 自定义模块路径或 .py 文件路径
        custom_class: 实现类名

    未配置时返回 DefaultDataSourcePasswordProvider。
    """
    if not custom_module and not custom_class:
        return DefaultDataSourcePasswordProvider()

    if not custom_module:
        raise ValueError(
            "DATASOURCE_PASSWORD_PROVIDER_MODULE is required when "
            "DATASOURCE_PASSWORD_PROVIDER_CLASS is specified"
        )
    if not custom_class:
        raise ValueError(
            "DATASOURCE_PASSWORD_PROVIDER_CLASS is required when "
            "DATASOURCE_PASSWORD_PROVIDER_MODULE is specified"
        )

    return _load_custom_provider(custom_module, custom_class)


def _load_custom_provider(module_path: str, class_name: str) -> DataSourcePasswordProvider:
    """通过 importlib 动态加载自定义密码获取实现。

    Args:
        module_path: Python 模块路径或 .py 文件路径
            - 文件路径：/opt/plugins/custom_password_provider（自动加 .py 后缀）
            - 模块名：my_package.custom_provider（需已安装到 site-packages）
        class_name: 实现类名（必须继承 DataSourcePasswordProvider）

    Returns:
        DataSourcePasswordProvider 实例
    """
    p = Path(module_path)
    try:
        py_path = p if p.suffix == ".py" else p.with_suffix(".py")
        if py_path.exists() and py_path.is_file():
            spec = importlib.util.spec_from_file_location(py_path.stem, str(py_path))
            if spec is None:
                raise ImportError(f"Cannot load module spec from: {py_path}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        else:
            module = importlib.import_module(module_path)
    except Exception as e:
        raise ImportError(
            f"Failed to load custom password provider module '{module_path}': {e}"
        ) from e

    cls = getattr(module, class_name, None)
    if cls is None:
        raise AttributeError(
            f"Class '{class_name}' not found in module '{module_path}'"
        )

    if not issubclass(cls, DataSourcePasswordProvider):
        raise TypeError(
            f"Class '{class_name}' does not inherit from DataSourcePasswordProvider"
        )

    try:
        return cls()
    except Exception as e:
        raise RuntimeError(
            f"Failed to instantiate custom password provider '{class_name}': {e}"
        ) from e
