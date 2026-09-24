#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2026. All rights reserved.
"""Builder 日志初始化（DEF-05，SYNC-01 P3.3 从旧分支移植）。

构造唯一冻结的 Builder 日志配置并经 agent-core ``configure_log_config`` 落地，
主动实例化四个内建 Logger 并核验目标文件，安装 ``request_id`` LogRecordFactory
注入器，失败即阻断启动。进程内幂等：重复调用不叠加 Handler、不重复包装 factory。

不读取已失效的 ``config.yaml.logging`` 段——环境变量 ``LOGGING_LOG_PATH`` 是唯一
运行时输入；轮转值、文件名、输出方式、格式由冻结常量固定，不经环境变量开放覆盖。
（sync_01 依赖 ``agent_builder.adapter.config_bridge.settings.logging.log_path``
——BuilderLoggingSettings 已随本批从旧分支 DEF-05 移植。）
"""

import logging
import os
import sys
import threading

from openjiuwen.core.common.logging import LogManager
from openjiuwen.core.common.logging.log_config import (
    configure_log_config,
    get_log_config_snapshot,
)

from agent_builder.adapter.config_bridge import settings
from agent_builder.adapter.request_context_bridge import get_request_id

_LOCK = threading.Lock()
_initialized = False

# ---- 冻结常量（不可经环境变量覆盖；VEC-01） ----
_BUILTIN_FORMAT = (
    "%(asctime)s,%(msecs)03d|%(log_type)s|"
    "%(filename)s:%(lineno)d|%(funcName)s|"
    "%(trace_id)s|%(request_id)s|%(levelname)s|%(message)s"
)
_MAX_BYTES = 20 * 1024 * 1024
_BACKUP_COUNT = 20
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_OUTPUT_KEYS = ("output", "interface_output", "performance_output")
_VALID_OUTPUT_MEMBER = "file"

# request_id LogRecordFactory sentinel——设在 wrapper 函数对象上，
# 抗模块重新加载（不靠可能丢失的模块级布尔变量判断是否安装）。
_FACTORY_SENTINEL = "_builder_request_id_factory_installed"

_BUILTIN_LOG_TYPES = ("common", "interface", "prompt_builder", "performance")

# 复审2 §2: 共享 storage/model_service 组件直接导入 agent-core 全局 ``workflow_logger``
# （非 Builder 冻结的四个内建 Logger），在 Builder 场景会被 agent-core 按动态规则创建
# ``workflow.log``——违反"只允许四个冻结目标文件、未登记动态 Logger 不得生成文件"契约。
# 这些非内建命名 Logger 在 Builder 里一律别名为 ``common``：其日志写入 ``run/jiuwen.log``、
# 外层 ``log_type=common``、共用 common 的单 Handler，满足"服务自身日志进 common"语义，
# 且避免复审 §3 担心的 ``log_type=workflow`` 或双 Handler 共写问题。
_NON_BUILTIN_ALIASED_LOGGERS = ("workflow",)


def _alias_non_builtin_loggers_to_common() -> None:
    """把共享组件用到的非内建 agent-core Logger 注册为 common 的别名。

    不重定向文件名（那样会留 ``log_type=workflow`` 且产生双 Handler），而是直接把
    workflow 等 Logger 指向 common Logger 实例本身。
    """
    common_logger = LogManager.get_logger("common")
    for log_type in _NON_BUILTIN_ALIASED_LOGGERS:
        LogManager.register_logger(log_type, common_logger)


# 四个目标活动文件的冻结相对路径（DEF-05 §3.1：init 返回前用公开文件状态核验存在+可写）。
_TARGET_FILES = {
    "common": "run/jiuwen.log",
    "interface": "interface/jiuwen_interface.log",
    "prompt_builder": "interface/jiuwen_prompt_builder_interface.log",
    "performance": "performance/jiuwen_performance.log",
}


def _verify_target_files():
    """核验四个目标活动文件已创建且可写（公开文件状态，不访问 agent-core 私有属性）。

    仅注册 Logger 不够——Handler 创建可能静默失败或推迟，此处用文件状态作为
    初始化成功的前置条件，使文件/权限问题在启动期即暴露。
    """
    root = settings.logging.log_path
    for log_type, rel in _TARGET_FILES.items():
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise RuntimeError(f"目标日志文件 {log_type} 未创建: {path}")
        if not os.access(path, os.W_OK):
            raise RuntimeError(f"目标日志文件 {log_type} 不可写: {path}")


def _build_logging_config():
    """构造唯一冻结的 Builder 日志配置（结构示意，不要求机械照抄变量名）。"""
    return {
        "backend": "default",
        "level": settings.server.log_level,
        "structured_output_format": "json",
        "backup_count": _BACKUP_COUNT,
        "max_bytes": _MAX_BYTES,
        "format": _BUILTIN_FORMAT,
        "log_path": settings.logging.log_path,
        "log_file": "run/jiuwen.log",
        "output": ["file"],
        "interface_log_file": "interface/jiuwen_interface.log",
        "interface_output": ["file"],
        "prompt_builder_interface_log_file": "interface/jiuwen_prompt_builder_interface.log",
        "performance_log_file": "performance/jiuwen_performance.log",
        "performance_output": ["file"],
        "propagate": False,
    }


def _validate_config(cfg):
    """在修改 logging 全局状态前校验日志级别、output 值和日志根路径。

    非法值直接抛 ``ValueError`` 阻断启动，不采用 agent-core 默认等级回退，
    也不允许底层按成员判断静默创建零个或错误 Handler。
    """
    level = str(cfg.get("level", "")).upper()
    if not level or level not in _VALID_LEVELS:
        raise ValueError(
            f"LOG_LEVEL 非法值: {cfg.get('level')!r}; 合法等级: {sorted(_VALID_LEVELS)}"
        )
    for key in _OUTPUT_KEYS:
        val = cfg.get(key)
        if not isinstance(val, list) or not val:
            raise ValueError(f"output 配置项 {key} 必须是非空列表, 实际: {val!r}")
        bad = [m for m in val if m != _VALID_OUTPUT_MEMBER]
        if bad:
            raise ValueError(
                f"output 配置项 {key} 只允许 {_VALID_OUTPUT_MEMBER!r}, 含非法成员: {bad}"
            )
    if not cfg.get("log_path"):
        raise ValueError("LOGGING_LOG_PATH 不能为空")


def _install_request_id_factory():
    """安装 ``request_id`` LogRecordFactory 注入器。

    wrapper 函数对象携带 ``_FACTORY_SENTINEL`` 标记与前序 factory 引用；安装前
    检查当前 factory 的标记——已是 Builder wrapper 时直接复用，否则链式包装。
    不靠模块级布尔变量（模块重新加载会丢失），保证可重复调用不形成包装链。
    """
    prior = logging.getLogRecordFactory()
    if getattr(prior, _FACTORY_SENTINEL, False):
        return None  # 已安装，复用，不重复包装

    def _builder_factory(*args, **kwargs):
        record = prior(*args, **kwargs)
        # 按属性是否存在判断（hasattr），而非按值真值——否则前序 factory 显式写入的
        # 空字符串会被上下文值覆盖。仅在记录尚无 request_id 属性时写入。
        if not hasattr(record, "request_id"):
            record.request_id = get_request_id() or ""
        return record

    setattr(_builder_factory, _FACTORY_SENTINEL, True)
    setattr(_builder_factory, "_builder_prior_factory", prior)
    logging.setLogRecordFactory(_builder_factory)
    return _builder_factory


def _restore_factory(installed_wrapper):
    """仅当当前 factory 仍是本次安装的 wrapper 时恢复安装前 factory。"""
    if installed_wrapper is None:
        return
    if logging.getLogRecordFactory() is installed_wrapper:
        prior = getattr(installed_wrapper, "_builder_prior_factory")
        logging.setLogRecordFactory(prior)


def init_logger():
    """初始化 Builder 日志。进程内幂等，失败即阻断启动。"""
    global _initialized
    with _LOCK:
        if _initialized:
            return

        cfg = _build_logging_config()
        _validate_config(cfg)  # 全局状态变更前校验

        # 安装前快照——失败时恢复，避免留下半初始化的全局状态
        snapshot = get_log_config_snapshot()
        installed_factory = _install_request_id_factory()

        try:
            configure_log_config(cfg)
            LogManager.initialize()  # 主动创建四个内建 Logger 及 Handler
            all_loggers = LogManager.get_all_loggers()
            for log_type in _BUILTIN_LOG_TYPES:
                if log_type not in all_loggers:
                    raise RuntimeError(f"内建 Logger {log_type} 未注册")
            _verify_target_files()
            _alias_non_builtin_loggers_to_common()
            # COM-05 DEF-05：agent-core build_default_logger_config 不透传 propagate 键
            # （DefaultLogger.config.get("propagate", True) 拿不到根级配置 → 恒 True →
            # WARNING+ 写冻结文件后继续向 root 传播，lastResort 双写 stderr）。
            # 本进程内显式切断，不依赖 agent-core 透传该键。
            for _log_type in _BUILTIN_LOG_TYPES:
                logging.getLogger(_log_type).propagate = False
        except Exception:
            # 失败：恢复安装前配置快照（configure_log_config 内部 reset 会关闭
            # 本次已创建的部分 Logger/Handler）；仅当当前 factory 仍是本次
            # wrapper 时恢复安装前 factory。失败信息走 stderr（bootstrap.log），
            # 不得调用可能再次初始化失败的业务 Logger。
            _restore_factory(installed_factory)
            try:
                configure_log_config(snapshot)
            except Exception:
                LogManager.reset()  # 至少关闭残留，不掩盖原始错误
            _emit_failure_to_stderr()
            raise

        _initialized = True


def _emit_failure_to_stderr():
    """通过隔离的标准库 Logger 输出 bootstrap 失败，不依赖业务 LogManager。"""
    bootstrap_logger = logging.Logger("agent_builder.bootstrap", level=logging.ERROR)
    bootstrap_logger.propagate = False
    handler = logging.StreamHandler()
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter("%(message)s"))
    bootstrap_logger.addHandler(handler)
    try:
        bootstrap_logger.error("[builder-log-init] initialization failed; see traceback below")
    finally:
        bootstrap_logger.removeHandler(handler)
        handler.close()
