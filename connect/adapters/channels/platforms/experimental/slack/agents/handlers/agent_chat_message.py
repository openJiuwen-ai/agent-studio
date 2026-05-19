from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


def on_agent_message(user_id: str, text: str, say, user_data: dict) -> None:
    """Called from the message router when state == 'agent_chat'."""
    chat_data = user_data.get('agent_chat', {})
    agent_id = chat_data.get('agent_id')
    if not agent_id:
        user_data['state'] = 'idle'
        say("❌ No active chat session. Use `/agent_chat <id>` to start.")
        return

    client = get_backend_client(user_id, say)
    if not client:
        return
    try:
        say("🤖 Processing...")
        events, conversation_id = execute_agent(client, agent_id, text, chat_data.get('conversation_id', ''))
        user_data['agent_chat']['conversation_id'] = conversation_id
        text_out, _, error = parse_agent_response(events, conversation_id)

        if error:
            say(f"❌ Agent error: {error}")
            return
        say(f"🤖 {text_out}" if text_out else "🤖 No response.")
    except Exception as e:
        say(f"❌ Error: {e}")
