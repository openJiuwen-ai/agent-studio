import asyncio
from typing import Any

from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage
from jiuwen.serve.common.message import StreamingCollector
from jiuwen.serve.controllers.execution.enum import ConversationEvent
from memory.storage.memory_extractor import get_instance


class UserProfileMemoryMessageCollector(StreamingCollector):
    def __init__(
        self,
        user_query: str,
        user_id: str,
        app_id: str,
        conversation_id: str,
        ir_data: dict,
    ):
        super().__init__()
        self.user_query: str = user_query
        self.user_id: str = user_id
        self.app_id: str = app_id
        self.conversation_id: str = conversation_id
        self.ir_data: dict = ir_data
        # Extract memory_repo_id from IR configs for proper scope isolation
        configs = ir_data.get("configs") if ir_data.get("configs") else {}
        memory_config = configs.get("memory") if configs.get("memory") else {}
        self.memory_repo_id: str = memory_config.get("memory_repo_id") or app_id

    def filter(self, message: Any) -> bool:
        return message.event == ConversationEvent.MESSAGE_END

    async def done(self) -> None:
        filter_messages = self.messages()

        messages_to_extract_memory = [UserMessage(content=self.user_query)]
        for msg in filter_messages:
            answer = msg.data.get("answer")
            messages_to_extract_memory.append(AssistantMessage(content=answer))
        asyncio.create_task(
            get_instance().async_add_chat_turn(
                self.user_id,
                self.memory_repo_id,
                self.conversation_id,
                self.ir_data,
                messages_to_extract_memory,
            )
        )
