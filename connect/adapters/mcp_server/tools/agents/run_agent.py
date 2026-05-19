from mcp.server.fastmcp import FastMCP

from connect.client.client import OpenJiuwenClient
from connect.client.agents.execute_agent import execute_agent as _execute_agent
from connect.client.agents.response_parser import parse_agent_response


def run_agent_tool(
    client: OpenJiuwenClient,
    agent_id: str,
    message: str,
    conversation_id: str = '',
) -> str:
    """
    Send a message to an agent and return its reply plus a conversation_id.

    Pass the returned conversation_id back on subsequent calls to continue the thread.
    """
    try:
        events, conversation_id = _execute_agent(client, agent_id, message, conversation_id)
        text, _, error = parse_agent_response(events, conversation_id)
        if error:
            return f"ERROR from agent: {error}"
        reply = text or "(no reply)"
        return f"Reply: {reply}\nConversation ID: {conversation_id}"
    except Exception as exc:
        return f"ERROR running agent: {exc}"


def register(mcp: FastMCP, client: OpenJiuwenClient) -> None:
    @mcp.tool()
    def run_agent(agent_id: str, message: str, conversation_id: str = '') -> str:
        """
        Send a message to an agent and get its reply.

        To maintain a multi-turn conversation pass the conversation_id returned
        by the previous call. Omit it (or pass '') to start a new conversation.

        Args:
            agent_id: The agent's ID (from list_agents or search_agents)
            message: The message to send to the agent
            conversation_id: Conversation ID for continuing a prior thread (optional)

        Returns:
            The agent's reply followed by the conversation_id to use in follow-up calls.
        """
        return run_agent_tool(client, agent_id, message, conversation_id)
