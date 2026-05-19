"""Agent run command."""
from openjiuwen.core.common.logging import logger
from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response

from ...session import require_client
from ...output import hr


def cmd_agent_run(backend_url: str, agent_id: str, message: str) -> None:
    client = require_client(backend_url)
    try:
        events, _ = execute_agent(client, agent_id, message)
        text, _, error = parse_agent_response(events)
    except Exception as e:
        error_msg = f"❌ {e}"
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e
    if error:
        raise RuntimeError(f"Agent error: {error}")
    hr()
    logger.info(text or "(no response)")
    hr()
