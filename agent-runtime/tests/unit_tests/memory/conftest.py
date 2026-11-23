# pylint: disable=protected-access
"""Shared fixtures for memory adapter unit tests.

Pre-loads sys.modules mocks for heavy jiuwen/agent_runtime dependencies
so adapter modules can be imported in isolation.
"""

import sys
from unittest.mock import AsyncMock, MagicMock

# Pre-mock heavy modules that agent_runtime.memory.__init__ imports.
#
# IMPORTANT: only stub LEAF modules here. Never stub a parent package
# (e.g. ``jiuwen.orchestration``, ``jiuwen.serve``) as a bare MagicMock — a
# MagicMock has no ``__path__``, so it leaks session-wide and breaks any later
# real ``from jiuwen.orchestration.utils import ...`` in the same session with
# ``'jiuwen.orchestration' is not a package``. Parent packages must stay real
# (their ``__init__`` is empty/light anyway) so other tests can still descend
# into their submodules; only the specific heavy leaves the memory SUT needs
# are stubbed below.
_mock_modules = [
    # agent_runtime.memory.__init__ imports CallbackHandlerManager from here.
    "jiuwen.orchestration.callbacks.manager",
    # SUT binds ``request as current_request`` from here.
    "jiuwen.serve.common.context",
    "jiuwen.serve.common.message",
    "agent_runtime.memory.global_vals_callback_handler",
    "utils",
    "utils.constants",
]

for mod_name in _mock_modules:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

import pytest


@pytest.fixture(autouse=True)
def reset_ltm_instance():
    """Reset the global _ltm_instance between tests."""
    import agent_runtime.memory.adapter.ltm_manager as mgr

    original = mgr._ltm_instance
    mgr._ltm_instance = None
    yield
    mgr._ltm_instance = original


@pytest.fixture
def mock_redis():
    """AsyncMock simulating redis.asyncio.Redis with decode_responses=False."""
    redis = AsyncMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[1])
    pipe.delete = MagicMock(return_value=pipe)
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


@pytest.fixture
def mock_opensearch_client():
    """AsyncMock simulating AsyncOpenSearch client."""
    client = AsyncMock()
    client.ping = AsyncMock(return_value=True)
    client.indices = AsyncMock()
    client.indices.create = AsyncMock()
    client.indices.delete = AsyncMock()
    client.indices.exists = AsyncMock(return_value=True)
    client.indices.get_mapping = AsyncMock()
    client.indices.put_mapping = AsyncMock()
    client.search = AsyncMock()
    client.delete_by_query = AsyncMock()
    client.cat = AsyncMock()
    client.cat.indices = AsyncMock(return_value=[])
    return client


@pytest.fixture
def mock_ltm():
    """AsyncMock simulating LongTermMemory."""
    ltm = AsyncMock()
    ltm.set_config = MagicMock()
    ltm.register_store = AsyncMock()
    ltm.get_scope_config = AsyncMock(return_value=None)
    ltm.set_scope_config = AsyncMock(return_value=True)
    ltm.delete_scope_config = AsyncMock(return_value=True)
    ltm.delete_mem_by_scope = AsyncMock(return_value=True)
    ltm.search_user_mem = AsyncMock(return_value=[])
    ltm.add_messages = AsyncMock()
    return ltm
