"""Run agent endpoint."""
from connect.client import OpenJiuwenClient
from connect.client.agents import execute_agent, parse_agent_response
from ...auth import client_dep
from .models import RunRequest


def agent_run(
    body: RunRequest,
    client: OpenJiuwenClient = client_dep,
):
    """Run an agent with a single message and return the text response.

    Pass `conversation_id` from a previous response to continue a conversation.
    The call blocks until the agent replies.
    """
    try:
        events, conversation_id = execute_agent(client, body.agent_id, body.message, body.conversation_id)
        text, conversation_id, error = parse_agent_response(events, conversation_id)
        if error:
            return {"success": False, "text": None, "conversation_id": None, "error": error}
        return {"success": True, "text": text, "conversation_id": conversation_id, "error": None}
    except Exception as e:
        return {"success": False, "text": None, "conversation_id": None, "error": str(e)}
