from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


async def handle_run(user_id, say, user_data, agent_id="", message=""):
    if not agent_id:
        await say("Please say: agent execute followed by the agent ID and your message.")
        return
    if not message:
        await say("Please include a message after the agent ID.")
        return
    client, err = get_backend_client(user_id)
    if err:
        await say(err)
        return
    try:
        events, _ = execute_agent(client, agent_id, message)
        text_out, _, error = parse_agent_response(events)
        if error:
            await say(f"Agent error: {error}")
            return
        await say(text_out if text_out else "The agent returned no response.")
    except Exception as e:
        await say(f"Error: {e}")
