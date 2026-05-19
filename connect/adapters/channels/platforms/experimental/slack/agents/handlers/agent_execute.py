from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


def handle_run(ack, respond, command):
    ack()
    user_id = command['user_id']
    text = (command.get('text') or '').strip()
    parts = text.split(None, 1)
    if len(parts) < 2:
        respond("❌ Usage: `/agent_run <agent_id> <message>`")
        return
    agent_id, message = parts
    client = get_backend_client(user_id, respond)
    if not client:
        return
    try:
        respond("🤖 Sending message to agent...")
        events, _ = execute_agent(client, agent_id, message)
        text_out, _, error = parse_agent_response(events)
        if error:
            respond(f"❌ Agent error: {error}")
            return
        respond(f"🤖 *Agent Response:*\n\n{text_out}" if text_out else "🤖 Agent returned no response.")
    except Exception as e:
        respond(f"❌ Error: {e}")
