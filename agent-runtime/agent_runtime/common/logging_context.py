import copy
import logging
import re

from agent_runtime.common.session_state_access import get_state_info
from agent_runtime.context.request_context import _request_ctx
from openjiuwen.core.common.logging import get_session_id

COMMON_LOG_FORMAT = (
    "%(asctime)s,%(msecs)03d|%(log_type)s|%(filename)s:%(lineno)d|%(funcName)s|"
    "%(trace_id)s|%(execution_id)s|%(request_id)s|%(levelname)s|%(message)s"
)
PERFORMANCE_LOG_FORMAT = (
    "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(execution_id)s|%(request_id)s|"
    "%(levelname)s|%(message)s"
)
DEFAULT_LOG_FORMAT = "%(asctime)s,%(msecs)03d|%(log_type)s|%(trace_id)s|%(levelname)s|%(message)s"

_INSTALLED = False
_FORMATTER_PATCH_INSTALLED = False
_OPENJIUWEN_LOGGING_MANAGED = False


def get_log_format(log_type: str) -> str:
    if log_type == "performance":
        return PERFORMANCE_LOG_FORMAT
    return COMMON_LOG_FORMAT


def mask_secret_envs_in_obj(obj, secret_keys):
    """Recursively mask secret env vars under plugin_url_params keys."""
    if not secret_keys:
        return obj
    if isinstance(obj, dict):
        if "plugin_url_params" in obj and isinstance(obj["plugin_url_params"], dict):
            for sk in secret_keys:
                if sk in obj["plugin_url_params"]:
                    obj["plugin_url_params"][sk] = "***"
        for v in obj.values():
            mask_secret_envs_in_obj(v, secret_keys)
    elif isinstance(obj, list):
        for item in obj:
            mask_secret_envs_in_obj(item, secret_keys)
    return obj


# Pattern to match ${_env.plugin_url_params.xxx} references in node configs
_ENV_REF_PATTERN = re.compile(r'\$\{_env\.plugin_url_params\.([^}]+)\}')


def find_secret_env_field_names(config, secret_keys):
    """Find field names that reference encrypted env vars in node config.

    Walks the node config recursively. When a string value matches
    ${_env.plugin_url_params.xxx} and xxx is in secret_keys, the field name
    is collected as a key in the returned dict, with the referenced env var
    key as the value: {field_name: env_var_key}.

    This is flag-based: it checks if the referenced env var key is in secretKeys,
    not value matching. The returned mapping enables node-level filtering of
    which secret values to mask (only secrets referenced by this node).
    """
    if not secret_keys or not config:
        return {}

    secret_keys_set = set(secret_keys)
    secret_fields: dict[str, str] = {}

    def walk(obj, current_field=None):
        if isinstance(obj, dict):
            # Find the field name from id/fieldName/name keys
            field_name = current_field
            for k in ("id", "fieldName", "name", "field_name"):
                if k in obj and isinstance(obj[k], str):
                    field_name = obj[k]
                    break
            # Walk all key-value pairs
            for k, v in obj.items():
                # If the value is a secret env ref, the key itself is a field name
                # (e.g. inputs.userFields = {"value3": "${_env.plugin_url_params.passwd}"})
                if isinstance(v, str):
                    m = _ENV_REF_PATTERN.search(v)
                    if m and m.group(1) in secret_keys_set:
                        secret_fields[k] = m.group(1)
                walk(v, field_name)
        elif isinstance(obj, list):
            for item in obj:
                walk(item, current_field)
        elif isinstance(obj, str):
            m = _ENV_REF_PATTERN.search(obj)
            if m and m.group(1) in secret_keys_set:
                if current_field:
                    secret_fields[current_field] = m.group(1)

    walk(config)
    return secret_fields


def mask_fields_by_name(obj, field_names):
    """Recursively mask values of specific field names.

    Walks the object and replaces values of keys that are in field_names with "***".
    Used to mask resolved values of encrypted env vars that appear under
    user-defined field names (e.g. value3='huawei@123') in trace data.
    """
    if not field_names:
        return obj
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in field_names:
                obj[k] = "***"
            else:
                mask_fields_by_name(v, field_names)
    elif isinstance(obj, list):
        for item in obj:
            mask_fields_by_name(item, field_names)
    return obj


def mask_inputs_for_rendering(inputs, secret_field_names):
    """创建 inputs 的掩码副本，仅用于模板渲染。

    基于 flag（字段名）判断，不基于值匹配。将引用了加密环境变量的字段值
    替换为 '***'，其他字段保持不变。生成器（同步/异步）跳过（不掩码），
    交由 _consume_all_iterators 统一消费。原始 inputs 不被修改，不影响工作流后续使用。
    """
    if not secret_field_names or not isinstance(inputs, dict) or not inputs:
        return inputs
    import inspect
    render_inputs = dict(inputs)
    for field_name in secret_field_names:
        if field_name in render_inputs:
            val = render_inputs[field_name]
            if inspect.isasyncgen(val) or hasattr(val, "__aiter__") or inspect.isgenerator(val):
                continue
            if isinstance(val, dict):
                render_inputs[field_name] = {k: "***" for k in val}
            else:
                render_inputs[field_name] = "***"
    return render_inputs


def mask_debug_data(data, secret_field_names=None):
    """Deep copy data and mask secret env vars. Safe for shared references."""
    if data is None:
        return None
    try:
        ctx = _request_ctx.get()
        secret_keys = ctx.secret_env_keys
    except Exception:
        secret_keys = []
    if not secret_keys and not secret_field_names:
        return data
    data = copy.deepcopy(data)
    mask_secret_envs_in_obj(data, secret_keys)
    if secret_field_names:
        mask_fields_by_name(data, secret_field_names)
    return data


def _is_masking_enabled():
    import os
    return os.getenv("LOG_MASKED_ENABLED", "false").lower() == "true"


def _get_sensitive_patterns():
    from jiuwen.common.log.base import get_list_from_env
    return get_list_from_env("LOG_MASKED_PATTERNS")


def _get_sensitive_words():
    from jiuwen.common.log.base import get_list_from_env
    return get_list_from_env("LOG_MASKED_SENS_WORDS")


def install_log_formatter_patch() -> None:
    """Make openjiuwen default backend choose formats by logger type."""
    global _FORMATTER_PATCH_INSTALLED, _OPENJIUWEN_LOGGING_MANAGED
    if _FORMATTER_PATCH_INSTALLED:
        return

    from jiuwen.common.log.base import MaskingFormatter
    from openjiuwen.core.common.logging.default.default_impl import DefaultLogger

    if _is_masking_enabled():
        sensitive_words = _get_sensitive_words()
        sensitive_patterns = _get_sensitive_patterns()
    else:
        sensitive_words = None
        sensitive_patterns = None

    def get_formatter(self):
        return MaskingFormatter(
            fmt=get_log_format(self.log_type),
            datefmt="%Y-%m-%d %H:%M:%S",
            sensitive_words=sensitive_words,
            sensitive_patterns=sensitive_patterns,
            truncate_for_console=True,
        )

    DefaultLogger._get_formatter = get_formatter
    _FORMATTER_PATCH_INSTALLED = True
    _OPENJIUWEN_LOGGING_MANAGED = True


def install_request_id_log_record_factory() -> None:
    """Add request_id to stdlib LogRecords used by openjiuwen formatters."""
    global _INSTALLED
    if _INSTALLED:
        return

    previous_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = previous_factory(*args, **kwargs)
        if not hasattr(record, "trace_id"):
            record.trace_id = get_session_id()
        if not hasattr(record, "execution_id"):
            record.execution_id = _request_ctx.get().execution_id
        if not hasattr(record, "request_id"):
            record.request_id = _request_ctx.get().request_id
        return record

    logging.setLogRecordFactory(record_factory)
    _INSTALLED = True


_TEMPLATE_MASKING_PATCHED = False


def get_secret_field_names_from_session(session):
    """通过 session 获取当前节点引用了加密环境变量的字段名映射。

    Returns:
        dict: {field_name: env_var_key}，如果无加密引用则返回 {}
    """
    try:
        ctx = _request_ctx.get()
        secret_keys = ctx.secret_env_keys
    except Exception:
        return {}
    if not secret_keys:
        return {}
    try:
        # 引用式路径访问替代 get_global_state：后者每次 deepcopy 全部工作流的
        # node-def 树，而该函数在每个节点的观察者回调中触发。
        node_defs = get_state_info(session, "global_state.__node_defs__")
        if not isinstance(node_defs, dict):
            return {}
        workflow_id = session.get_workflow_id()
        node_id = session.get_component_id()
        wf_defs = node_defs.get(workflow_id, {})
        node_def = wf_defs.get(node_id, {})
        if not node_def:
            return {}
        return find_secret_env_field_names(node_def, secret_keys)
    except Exception:
        return {}


def apply_template_masking_patch():
    """注册观察者回调 + patch 模板渲染方法，对加密环境变量字段做掩码。

    - 注册 COMPONENT_BATCH_INPUT / COMPONENT_STREAM_INPUT 观察者回调：
      在节点执行入口将 secret_field_names 存入 _request_ctx（仅写 ContextVar，
      不修改 on_* 入参；观察者路径，回调返回值被忽略）
    - Patch TemplateProcessor.render_stream：从 _request_ctx 读取并掩码 inputs 副本
    - Patch TemplateUtils.render_template：从 _request_ctx 读取并掩码 inputs 副本

    这样不关注节点类型，任何节点调用模板渲染都会经过同一个掩码逻辑。
    原始 inputs 不被修改，不影响工作流后续使用。

    注意：之前用 monkey-patch 覆盖 on_* 会把 session 从 keyword 改成 positional，
    触发回调框架 transform_io 路径的 _inject_session_if_needed 注入 session=None
    并丢弃真实位置参数，导致 100053 错误。改用 _fw.on() 观察者回调从根本上消除
    该副作用——emit_before 路径原 args/kwargs 透传给真正的 on_*，不注入不丢弃。
    """
    global _TEMPLATE_MASKING_PATCHED
    if _TEMPLATE_MASKING_PATCHED:
        return
    _TEMPLATE_MASKING_PATCHED = True

    from openjiuwen.core.workflow.components.flow.end_comp import (
        TemplateProcessor,
        TemplateUtils,
    )
    from openjiuwen.core.session.internal.workflow import NodeSession
    from openjiuwen.core.session.node import Session
    from openjiuwen.core.runner.callback.utils import get_callback_framework
    from openjiuwen.core.runner.callback.events import WorkflowEvents

    def _set_secret_fields(base_session):
        """从 NodeSession 提取 secret_field_names 并存入 _request_ctx"""
        try:
            if isinstance(base_session, NodeSession):
                sess = Session(base_session, False)
                sf = get_secret_field_names_from_session(sess)
                _request_ctx.get().current_secret_field_names = sf
        except Exception:
            logging.debug("Failed to set secret field names for masking", exc_info=True)

    # --- 注册观察者回调（替代原 monkey-patch on_*）---
    # emit_before 路径把 on_*(self, inputs, session=..., context=...) 的 args/kwargs
    # 原样传给回调：kwargs.get("session") 拿 NodeSession；位置参数形式 fallback args[2]
    # （on_*(self, inputs, session, ...) 签名）。回调仅写 ContextVar，返回 None，
    # 不影响 on_* 入参。不指定 callback_type="transform"，默认为观察者，走
    # framework.trigger 路径，回调返回值被忽略。
    _fw = get_callback_framework()

    # on_invoke / on_stream 入口（emit_before 在 transform_io 之前触发）
    @_fw.on(WorkflowEvents.COMPONENT_BATCH_INPUT)
    async def _secret_fields_before_batch_input(*args, **kwargs):
        session = kwargs.get("session")
        if session is None and len(args) >= 3:
            session = args[2]
        _set_secret_fields(session)

    # on_collect / on_transform 入口
    @_fw.on(WorkflowEvents.COMPONENT_STREAM_INPUT)
    async def _secret_fields_before_stream_input(*args, **kwargs):
        session = kwargs.get("session")
        if session is None and len(args) >= 3:
            session = args[2]
        _set_secret_fields(session)

    # --- Patch TemplateProcessor.render_stream ---
    _orig_render_stream = TemplateProcessor.render_stream

    async def _patched_render_stream(self, inputs, session, timeout=0.2):
        sf = _request_ctx.get().current_secret_field_names if _request_ctx else {}
        render_inputs = mask_inputs_for_rendering(inputs, sf)
        async for frame in _orig_render_stream(self, render_inputs, session, timeout):
            yield frame

    TemplateProcessor.render_stream = _patched_render_stream

    # --- Patch TemplateUtils.render_template ---
    _orig_render_template = TemplateUtils.render_template

    def _patched_render_template(template, inputs):
        sf = _request_ctx.get().current_secret_field_names if _request_ctx else {}
        render_inputs = mask_inputs_for_rendering(inputs, sf)
        return _orig_render_template(template, render_inputs)

    TemplateUtils.render_template = _patched_render_template
