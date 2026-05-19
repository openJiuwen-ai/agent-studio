"""Agent list command."""
from openjiuwen.core.common.logging import logger
from connect.client.agents import list_agents

from ...session import require_client
from ...output import print_agents


def cmd_agent_list(backend_url: str, page: int = 1, page_size: int = 20) -> None:
    client = require_client(backend_url)
    try:
        result = list_agents(client, page=page, page_size=page_size)
        data = result.get('data', {})
        agents = data.get('agent_items', [])
        total = data.get('pagination', {}).get('total', len(agents))
        if not agents:
            logger.info("ℹ️  No agents found.")
            return
        print_agents(agents, total)
    except Exception as e:
        error = f"❌ {e}"
        logger.error(error)
        raise RuntimeError(error) from e

