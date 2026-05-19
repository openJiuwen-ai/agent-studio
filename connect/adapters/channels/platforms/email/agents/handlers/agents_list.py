"""List agents command handler."""
from connect.client.agents import list_agents
from ...client_session import get_backend_client


async def handle_list(user_id: str, say, user_data: dict) -> None:
    client, err = get_backend_client(user_id)
    if err:
        await say(err)
        return
    try:
        page = user_data.get("page", 1)
        page_size = user_data.get("page_size", 20)
        result = list_agents(client, page=page, page_size=page_size)
        data = result.get("data", {})
        agents = data.get("agent_items", [])
        total = data.get("pagination", {}).get("total", len(agents))
        if not agents:
            await say("No agents found.")
            return
        lines = [f"Found {total} agent(s):\n"]
        for i, agent in enumerate(agents[:10], 1):
            name = agent.get("agent_name", "Unnamed")
            agent_id = agent.get("agent_id", "N/A")
            desc = agent.get("description", "")
            lines.append(f"{i}. {name}  |  ID: {agent_id}")
            if desc:
                lines.append(f"   {desc[:60]}{'...' if len(desc) > 60 else ''}")
        if total > 10:
            lines.append(f"...and {total - 10} more")
        lines.append("\nTo chat: agent start <id>  |  Single message: agent execute <id> <msg>")
        await say("\n".join(lines))
    except Exception as e:
        await say(f"Error: {e}")
