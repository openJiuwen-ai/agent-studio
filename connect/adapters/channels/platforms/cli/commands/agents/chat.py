"""Agent chat command."""
from openjiuwen.core.common.logging import logger
from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response

from ...session import require_client
from ...output import hr


def cmd_agent_chat(backend_url: str, agent_id: str) -> None:
    client = require_client(backend_url)
    conversation_id = ""

    hr()
    logger.info(f"🤖 Chat with agent {agent_id}")
    logger.info("   Type 'exit' or press Ctrl+C to quit.")
    hr()

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            logger.info("\n\n👋 Chat ended.")
            break

        if user_input.lower() in ("exit", "quit", "q"):
            logger.info("👋 Chat ended.")
            break
        if not user_input:
            continue

        try:
            events, conversation_id = execute_agent(client, agent_id, user_input, conversation_id)
            text, _, error = parse_agent_response(events, conversation_id)
            if error:
                logger.error(f"❌ {error}")
            else:
                logger.info(f"\nAgent: {text or '(no response)'}")
        except Exception as e:
            logger.error(f"❌ {e}")
