#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
低代码模式Agent加载模块

提供将导出的Agent JSON配置转换为可执行实例的功能

主要接口：
- AgentCompiler: Runtime SDK调用的主要入口
  - compile(): 编译配置并返回可执行的Agent实例（依赖数据库）
  - compile_config(): 仅编译配置，不创建实例
  - compile_from_file(): 从文件编译并返回Agent实例
  - compile_from_file_config(): 从文件编译配置
  - compile_with_overrides(): 使用模型覆盖编译并返回Agent实例（依赖数据库）
  - compile_with_overrides_config(): 使用模型覆盖编译配置
  - compile_for_runtime(): 编译配置用于 Runtime 环境（不依赖数据库，推荐）
  - validate(): 验证配置
"""

from openjiuwen_studio.lowcode.compiler import AgentCompiler
from openjiuwen_studio.lowcode.loader import LowCodeAgentLoader
from openjiuwen_studio.lowcode.schemas import (
    AgentExportData,
    ModelOverride,
    ModelReference,
    AgentDependencies,
    CompileRequest,
    CompileResponse,
    RunRequest,
    ValidateRequest,
    ValidationResult,
    ValidationError,
    ExecuteResponse,
)

__version__ = "1.0.0"

__all__ = [
    "AgentCompiler",
    "LowCodeAgentLoader",
    "AgentExportData",
    "ModelOverride",
    "ModelReference",
    "AgentDependencies",
    "CompileRequest",
    "CompileResponse",
    "RunRequest",
    "ValidateRequest",
    "ValidationResult",
    "ValidationError",
    "ExecuteResponse",
    "__version__",
]
