from openjiuwen.core.common.logging import logger

from telegram import Update
from telegram.ext import ContextTypes

from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response
from ...auth import require_login


@require_login
async def agent_execute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute agent with a message - /agent_execute <agent_id> <message>"""
    logger.info("agent_execute_handler called: user_id=%s, args=%s", update.effective_user.id, context.args)
    backend_client = context.user_data.get('backend_client')
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Usage: /agent_execute <agent_id> <message>\n"
                "Example: /agent_execute 12345 Hello, how can you help?"
            )
            return

        agent_id = context.args[0]
        message = ' '.join(context.args[1:])

        await update.message.reply_text("🤖 Sending message to agent...")
        events, _ = execute_agent(backend_client, agent_id, message)
        text, _, error = parse_agent_response(events)

        if error:
            await update.message.reply_text(f"❌ Agent error: {error}")
            return

        reply = f"🤖 *Agent Response:*\n\n{text}" if text else "🤖 Agent returned no response."
        await update.message.reply_text(reply, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
