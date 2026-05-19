"""Execute an agent with a single message."""
import asyncio
from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


async def handle_agent_execute(user_id: str, arg: str, say) -> None:
    parts = arg.split(None, 1)
    if len(parts) < 2:
        await say("Usage: agent run <agent_id> <message>")
        return
    agent_id, message = parts[0], parts[1]
    client, err = await get_backend_client(user_id, say)
    if err:
        return
    await say("Running agent...")
    try:
        events, _ = await asyncio.get_event_loop().run_in_executor(
            None, lambda: execute_agent(client, agent_id, message)
        )
        text, _, error = parse_agent_response(events)
    except Exception as exc:
        await say(f"Agent execution failed: {exc}")
        return
    if error:
        await say(f"Error: {error}")
    else:
        await say(text or "Agent returned no response.")
