"""Run agent (single message) slash command handler."""
import discord
from discord import app_commands

from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...client_session import get_backend_client


@app_commands.describe(agent_id="The agent ID", message="Message to send")
async def agent_execute_handler(interaction: discord.Interaction, agent_id: str, message: str) -> None:
    await interaction.response.defer(ephemeral=True)
    user_id = str(interaction.user.id)
    client, err = get_backend_client(user_id)
    if err:
        await interaction.followup.send(err)
        return
    try:
        await interaction.followup.send("🤖 Sending message to agent...")
        events, _ = execute_agent(client, agent_id, message)
        text_out, _, error = parse_agent_response(events)
        if error:
            await interaction.followup.send(f"❌ Agent error: {error}")
            return
        reply = f"🤖 **Agent Response:**\n\n{text_out}" if text_out else "🤖 Agent returned no response."
        await interaction.followup.send(reply)
    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")
