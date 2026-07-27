import asyncio
import json
import os
import time
from dataclasses import dataclass, asdict
from typing import Optional

from openjiuwen.core.common.logging import memory_logger as logger
from openjiuwen.core.memory.config.config import AgentMemoryConfig

from openjiuwen.core.foundation.llm import UserMessage, AssistantMessage, BaseMessage
from jiuwen.serve.common.context import request as current_request
from jiuwen.serve.controllers.execution.ir_converter import IRConverter

from agent_runtime.memory.adapter.ltm_manager import get_ltm


@dataclass
class UserProfileExtractMessageReq:
    role: str
    content: str
    conversation_id: str
    timestamp: Optional[int] = None


@dataclass
class UserProfileExtractTagConfigReq:
    name: str
    description: str


@dataclass
class UserProfileExtractTopicConfigReq:
    name: str
    tags: list[UserProfileExtractTagConfigReq]


@dataclass
class UserProfileExtractRequestBody:
    messages: list[UserProfileExtractMessageReq]
    topics: list[UserProfileExtractTopicConfigReq]

    def to_json(self) -> str:
        def default_encoder(obj):
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        return json.dumps(asdict(self), ensure_ascii=False, default=default_encoder)


@dataclass
class TagValue:
    topic: str
    name: str
    value: str


@dataclass
class UserProfileExtractResponseBody:
    tags: list[TagValue]


@dataclass
class UserProfileMemoryExtractorConfig:
    extract_max_turns: Optional[int] = None
    extract_time_windows: Optional[int] = None
    user_profile_enable: bool = False


@dataclass
class UserProfileMemoryHistoryMessage:
    role: str
    content: str


@dataclass
class MessageChatTurn:
    messages: Optional[list[UserProfileMemoryHistoryMessage]] = None


@dataclass
class ChatHistoryConversationCache:
    user_id: str
    memory_repo_id: str
    conversation_id: str
    last_update_time: Optional[int] = None
    chat_turns: Optional[list[MessageChatTurn]] = None

    def add_chat_turn(self, chat_turn: MessageChatTurn):
        if not self.chat_turns:
            self.chat_turns = []
        self.chat_turns.append(chat_turn)
        self.last_update_time = int(time.time())

    @classmethod
    def from_json(cls, json_str: str):
        data = json.loads(json_str)

        chat_turns = []
        for chat_data in data.get("chat_turns", []):
            messages = []
            for msg_data in chat_data.get("messages", []):
                messages.append(UserProfileMemoryHistoryMessage(**msg_data))
            chat_turns.append(MessageChatTurn(messages=messages))

        return cls(
            user_id=data["user_id"],
            memory_repo_id=data.get("memory_repo_id") or data.get("app_id", ""),
            conversation_id=data["conversation_id"],
            last_update_time=data["last_update_time"],
            chat_turns=chat_turns,
        )

    def to_json(self) -> str:
        def default_encoder(obj):
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return str(obj)

        return json.dumps(asdict(self), ensure_ascii=False, default=default_encoder)


class UserProfileMemoryExtractor:
    _instance = None
    _initialized = False
    _user_profile_enable = (
        os.getenv("MEMORY_USER_PROFILE_ENABLE", "false").lower() == "true"
    )
    _extract_max_turns = int(os.getenv("MEMORY_USER_PROFILE_EXTRACT_MAX_TURN", 5))
    _extract_time_windows = int(
        os.getenv("MEMORY_USER_PROFILE_EXTRACT_TIME_WINDOWS", 10)
    )
    _memory_extract_delay_task: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            from common_utils.redis_manager import RedisClientManager

            self._redis_client = RedisClientManager.get_instance().get_client()
            self._initialized = True
            logger.info(
                f"Init user profile memory extractor with enable:{self._user_profile_enable}, "
                f"default extract max turns: {self._extract_max_turns}, "
                f"default extract time windows: {self._extract_time_windows}"
            )

    async def async_add_chat_turn(
        self,
        user_id: str,
        memory_repo_id: str,
        conversation_id: str,
        ir_data: dict,
        messages: list[BaseMessage],
    ):
        """
        Store chat turns for user profile memory extraction.
        Args:
            user_id: User ID
            memory_repo_id: Memory repo ID (from IR configs.memory.memory_repo_id)
            conversation_id: Conversation ID
            ir_data: Agent or workflow IR data
            messages: Messages from this conversation turn
        """
        try:
            extractor_config = self._convert_memory_extract_config(ir_data)
            if not extractor_config.user_profile_enable:
                return

            real_extract_config = UserProfileMemoryExtractorConfig(
                extract_max_turns=self._extract_max_turns,
                extract_time_windows=self._extract_time_windows,
            )
            if extractor_config and extractor_config.extract_max_turns:
                real_extract_config.extract_max_turns = (
                    extractor_config.extract_max_turns
                )
            if extractor_config and extractor_config.extract_time_windows:
                real_extract_config.extract_time_windows = (
                    extractor_config.extract_time_windows
                )

            task = asyncio.create_task(
                self._async_add_chat_turn_task(
                    user_id,
                    memory_repo_id,
                    conversation_id,
                    real_extract_config,
                    messages,
                    ir_data,
                )
            )
            await task
        except Exception as e:
            logger.error(
                f"Add chat history to user profile memory cache error: {e}",
                exc_info=True,
            )

    async def _async_add_chat_turn_task(
        self,
        user_id: str,
        memory_repo_id: str,
        conversation_id: str,
        extractor_config: UserProfileMemoryExtractorConfig,
        messages: list[BaseMessage],
        ir_data: dict,
    ):
        try:
            await self._cache_chat_message(
                user_id, memory_repo_id, conversation_id, extractor_config, messages, ir_data
            )
        except Exception as e:
            logger.error(
                f"Add chat history to user profile memory cache error: {e}",
                exc_info=True,
            )

    async def _cache_chat_message(
        self,
        user_id: str,
        memory_repo_id: str,
        conversation_id: str,
        extractor_config: UserProfileMemoryExtractorConfig,
        messages: list[BaseMessage],
        ir_data: dict,
    ):
        if not messages:
            return

        message_in_turn = []
        for message in messages:
            message_in_turn.append(
                UserProfileMemoryHistoryMessage(
                    role=message.role, content=message.content
                )
            )
        chat_turn = MessageChatTurn(messages=message_in_turn)

        history_message = await self._redis_client.get(
            self._obtain_user_memory_key(user_id, memory_repo_id, conversation_id)
        )

        if not history_message:
            logger.info(
                f"Cached user memory is empty. Create userMemory for user: {user_id}."
            )
            cache_conversation = ChatHistoryConversationCache(
                user_id=user_id, memory_repo_id=memory_repo_id, conversation_id=conversation_id
            )
            cache_conversation.add_chat_turn(chat_turn)
        else:
            cache_conversation = ChatHistoryConversationCache.from_json(
                history_message.decode("utf-8")
            )
            cache_conversation.add_chat_turn(chat_turn)

        if len(cache_conversation.chat_turns) >= extractor_config.extract_max_turns:
            logger.info(
                f"Cached chatTurns exceeds maxCachedTurn count. Extract user memory for user: {user_id}, conversation: {conversation_id}."
            )
            await self._extract_memory(
                user_id, memory_repo_id, conversation_id, ir_data, cache_conversation
            )
        else:
            message_json_str = ChatHistoryConversationCache.to_json(cache_conversation)
            await self._redis_client.set(
                self._obtain_user_memory_key(user_id, memory_repo_id, conversation_id),
                message_json_str.encode("utf-8"),
            )
            logger.info(
                "Cached chatTurns within maxCachedTurn. "
                "Scheduling delayed memory extraction for user: %s, conversation: %s.",
                user_id, conversation_id,
            )
            # Cancel existing delay task for this conversation to reset the timer (T-02)
            existing_task = self._memory_extract_delay_task.pop(conversation_id, None)
            if existing_task is not None:
                existing_task.cancel()
                logger.info(
                    f"Cancelled previous delay task for conversation: {conversation_id}, will reschedule."
                )
            task = asyncio.create_task(
                self._extract_memory_delay(
                    user_id,
                    memory_repo_id,
                    conversation_id,
                    extractor_config.extract_time_windows,
                    ir_data,
                )
            )
            self._memory_extract_delay_task[conversation_id] = task

    async def _extract_memory_delay(
        self,
        user_id: str,
        memory_repo_id: str,
        conversation_id: str,
        delay_minutes: int,
        ir_data: dict,
    ):
        try:
            await asyncio.sleep(delay_minutes * 60)
            await self._extract_memory(user_id, memory_repo_id, conversation_id, ir_data)
        except asyncio.CancelledError:
            logger.info(
                f"Delay extraction task cancelled for conversation: {conversation_id}"
            )
        except Exception as e:
            logger.error(
                f"Add chat history to user profile memory cache error: {e}",
                exc_info=True,
            )

    async def _extract_memory(
        self,
        user_id: str,
        memory_repo_id: str,
        conversation_id: str,
        ir_data: dict,
        cached_conversation: Optional[ChatHistoryConversationCache] = None,
    ):
        cached_conversation_to_extract = cached_conversation
        if not cached_conversation:
            conversation_str = await self._redis_client.get(
                self._obtain_user_memory_key(user_id, memory_repo_id, conversation_id)
            )
            if not conversation_str:
                logger.info(
                    f"There is no message cache. Skip extract user memory for user: {user_id}, conversation: {conversation_id}."
                )
                return
            cached_conversation_to_extract = ChatHistoryConversationCache.from_json(
                conversation_str.decode("utf-8")
            )
        if not cached_conversation_to_extract.chat_turns:
            logger.warning(
                f"Cached conversation is empty. Skip extract user memory for user: {user_id}, conversation: {conversation_id}."
            )
            return
        await self._redis_client.delete(
            self._obtain_user_memory_key(user_id, memory_repo_id, conversation_id)
        )

        all_tags = await IRConverter.get_memory_topics(ir_data)
        topics_to_extract = []
        if all_tags:
            for topic in all_tags:
                topic_to_extract = UserProfileExtractTopicConfigReq(
                    name=topic.get("name"), tags=[]
                )
                if topic.get("tags"):
                    for tag in topic.get("tags"):
                        tag_to_extract = UserProfileExtractTagConfigReq(
                            name=tag.get("name"), description=tag.get("description")
                        )
                        topic_to_extract.tags.append(tag_to_extract)
                topics_to_extract.append(topic_to_extract)

        # Extract memory via LTM (replaces HTTP POST to memory-service)
        try:
            ltm = get_ltm()
            if ltm is None:
                logger.info(
                    "LTM not initialized, skipping memory extraction for user: %s",
                    user_id,
                )
                return

            # Ensure scope config exists with strategy prompts from IR
            try:
                existing_cfg = await ltm.get_scope_config(memory_repo_id)
                if existing_cfg is None:
                    from agent_runtime.memory.adapter.ltm_manager import build_scope_config
                    scope_cfg = build_scope_config()
                    configs = ir_data.get("configs") if ir_data.get("configs") else {}
                    memory_config = configs.get("memory") if configs.get("memory") else {}
                    strategies = memory_config.get("strategies") if memory_config.get("strategies") else []
                    for strategy in strategies:
                        strategy_type = strategy.get("type", "")
                        prompt = strategy.get("prompt", "")
                        if not prompt:
                            continue
                        if strategy_type == "user_profile":
                            scope_cfg.user_profile_definition = prompt
                        elif strategy_type == "semantic_memory":
                            scope_cfg.semantic_memory_definition = prompt
                        elif strategy_type == "episodic_memory":
                            scope_cfg.episodic_memory_definition = prompt
                    await ltm.set_scope_config(memory_repo_id, scope_cfg)
            except Exception as e:
                logger.warning("Failed to ensure scope config for %s (non-blocking): %s", memory_repo_id, e)

            base_messages: list[BaseMessage] = []
            for chat_turn in cached_conversation_to_extract.chat_turns:
                for msg in chat_turn.messages:
                    if msg.role == "user":
                        base_messages.append(UserMessage(content=msg.content))
                    else:
                        base_messages.append(AssistantMessage(content=msg.content))

            if not base_messages:
                return

            agent_config = AgentMemoryConfig()

            configs = ir_data.get("configs") if ir_data.get("configs") else {}
            memory_config = configs.get("memory") if configs.get("memory") else {}
            strategies = memory_config.get("strategies") if memory_config.get("strategies") else []
            strategy_types = {s.get("type") for s in strategies if s.get("type")}
            if strategy_types:
                agent_config.enable_user_profile = "user_profile" in strategy_types
                agent_config.enable_semantic_memory = "semantic_memory" in strategy_types
                agent_config.enable_episodic_memory = "episodic_memory" in strategy_types

            await ltm.add_messages(
                messages=base_messages,
                agent_config=agent_config,
                user_id=user_id.lower(),
                scope_id=memory_repo_id,
                session_id=conversation_id,
            )
            logger.info(
                "LTM memory extraction completed for user: %s, conversation: %s",
                user_id,
                conversation_id,
            )

        except Exception as e:
            logger.error(
                "LTM memory extraction failed for user: %s, conversation: %s. Error: %s",
                user_id,
                conversation_id,
                e,
                exc_info=True,
            )
        finally:
            self._memory_extract_delay_task.pop(conversation_id, None)

    def _convert_message_for_memory_extract(
        self, history_messages: ChatHistoryConversationCache
    ) -> UserProfileExtractRequestBody:
        if not history_messages.chat_turns:
            return UserProfileExtractRequestBody(messages=[], topics=[])

        request_body = UserProfileExtractRequestBody(messages=[], topics=[])
        for chat_turn in history_messages.chat_turns:
            for message in chat_turn.messages:
                msg = UserProfileExtractMessageReq(
                    role=message.role,
                    content=message.content,
                    conversation_id=history_messages.conversation_id,
                )
                request_body.messages.append(msg)

        return request_body

    def _convert_memory_extract_config(
        self, ir_data: dict
    ) -> UserProfileMemoryExtractorConfig:
        configs = ir_data.get("configs") if ir_data.get("configs") else {}
        memory_config = configs.get("memory") if configs.get("memory") else {}

        # Prefer new IR structure: extract_config + strategies
        extract_config = memory_config.get("extract_config") or {}
        strategies = memory_config.get("strategies") or []

        if extract_config or strategies:
            strategy_types = {s.get("type") for s in strategies if s.get("type")}
            memory_enabled = len(strategy_types) > 0
            return UserProfileMemoryExtractorConfig(
                extract_max_turns=extract_config.get("max_chat_turn")
                if extract_config.get("max_chat_turn")
                else self._extract_max_turns,
                extract_time_windows=extract_config.get("time_window")
                if extract_config.get("time_window")
                else self._extract_time_windows,
                user_profile_enable=memory_enabled,
            )

        # Fallback: old IR structure configs.memory.userProfile
        user_profile_config = (
            memory_config.get("userProfile") if memory_config.get("userProfile") else {}
        )
        user_profile_enable = (
            user_profile_config.get("enable")
            if user_profile_config.get("enable")
            else bool(memory_config.get("memory_repo_id"))
        )
        user_profile_extract_config = (
            user_profile_config.get("extractConfig")
            if user_profile_config.get("extractConfig")
            else {}
        )
        return UserProfileMemoryExtractorConfig(
            extract_max_turns=user_profile_extract_config.get("maxChatTurn")
            if user_profile_extract_config.get("maxChatTurn")
            else self._extract_max_turns,
            extract_time_windows=user_profile_extract_config.get("timeWindow")
            if user_profile_extract_config.get("timeWindow")
            else self._extract_time_windows,
            user_profile_enable=user_profile_enable,
        )

    @staticmethod
    def _obtain_user_memory_key(user_id: str, memory_repo_id: str, conversation_id: str):
        return f"memory_chat_cache:{user_id}:{memory_repo_id}:{conversation_id}"


def get_instance():
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = UserProfileMemoryExtractor()
    return _extractor_instance


_extractor_instance = None
