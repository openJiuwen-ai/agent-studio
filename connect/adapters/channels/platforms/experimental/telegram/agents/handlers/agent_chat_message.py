from openjiuwen.core.common.logging import logger

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from connect.client.agents import execute_agent
from connect.client.agents import parse_agent_response

from .agent_chat import AGENT_CHAT
from ...auth import require_login


@require_login
async def agent_chat_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages in agent chat session."""
    backend_client = context.user_data.get('backend_client')
    try:
        user_message = update.message.text
        logger.info("agent_chat_message_handler called: user_id=%s, agent_id=%s, message=%r",
                    update.effective_user.id,
                    context.user_data.get('agent_chat', {}).get('agent_id'),
                    user_message)
        chat_data = context.user_data.get('agent_chat', {})
        agent_id = chat_data.get('agent_id')
        conversation_id = chat_data.get('conversation_id', '')

        if not agent_id:
            await update.message.reply_text(
                "❌ No active chat session. Use /agent_start_chat <agent_id> to start."
            )
            return ConversationHandler.END

        await update.message.reply_text("🤖 Processing...")
        events, conversation_id = execute_agent(backend_client, agent_id, user_message, conversation_id)
        context.user_data['agent_chat']['conversation_id'] = conversation_id
        text, _, error = parse_agent_response(events, conversation_id)

        if error:
            await update.message.reply_text(f"❌ Agent error: {error}")
            return AGENT_CHAT

        await update.message.reply_text(f"🤖 {text}" if text else "🤖 No response.")
        return AGENT_CHAT
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
        return AGENT_CHAT
