import inspect
from agent_runtime.common.ir_interfaces import ModelConfigProvider


def test_get_llm_config_is_coroutine_function():
    """ModelConfigProvider.get_llm_config must be a coroutine function (async def)."""
    assert inspect.iscoroutinefunction(ModelConfigProvider.get_llm_config), \
        "get_llm_config must be async def"
