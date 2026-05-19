"""Run agent (single message) command handler."""
from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


async def handle_run(user_id: str, say, user_data: dict, agent_id: str = '', message: str = '') -> None:
    if not agent_id:
        await say("Usage: `agent run <agent-id> <message>`")
        return
    if not message:
        await say("Usage: `agent run <agent-id> <message>`\n\nExample: `agent run abc123 Hello, how are you?`")
        return
    client, err = get_backend_client(user_id)
    if err:
        await say(err)
        return
    try:
        await say("🤖 Sending message to agent...")
        events, _ = execute_agent(client, agent_id, message)
        text_out, _, error = parse_agent_response(events)
        if error:
            await say(f"❌ Agent error: {error}")
            return
        reply = f"🤖 **Agent Response:**\n\n{text_out}" if text_out else "🤖 Agent returned no response."
        await say(reply)
    except Exception as e:
        await say(f"❌ Error: {e}")
