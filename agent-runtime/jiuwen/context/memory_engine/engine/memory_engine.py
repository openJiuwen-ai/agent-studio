#!/usr/bin/env python
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
import json
from typing import List, Any

from jiuwen.common.llm_service.base import BaseChatModel
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.log.base import logger
from jiuwen.common.utils.singleton import Singleton
from jiuwen.context.memory_engine.common.base import (
    ProcessedMemResult,
    ProfileTopicResult,
    ProfileTopicTagResult,
    VariableResult,
    UserMemoryResult,
)
from jiuwen.context.memory_engine.config.config import (
    MemoryScopeConfig,
    MemoryEngineConfig,
    ProfileTopicTag,
    ProfileTopicConfig,
    ProcessMemoryMode,
    Variable,
)
from jiuwen.context.memory_engine.generation.generation import Generator
from jiuwen.context.memory_engine.manage.data_id_manager import DataIdManager
from jiuwen.context.memory_engine.manage.message_manager import MessageManager
from jiuwen.context.memory_engine.manage.topic_profile_manager import (
    TopicProfileManager,
)
from jiuwen.context.memory_engine.manage.user_memory_manager import UserMemoryManager
from jiuwen.context.memory_engine.manage.variable_manager import VariableManager
from jiuwen.context.memory_engine.manage.write_manager import WriteManager
from jiuwen.context.memory_engine.mem_unit.memory_type import MemoryType
from jiuwen.context.memory_engine.mem_unit.memory_unit import (
    BaseMemoryUnit,
    TopicProfileUnit,
    VariableUnit,
    UserMemoryUnit,
)
from jiuwen.context.memory_engine.search.search_manager.search_manager import (
    SearchManager,
)
from jiuwen.context.memory_engine.store.base_db_store import BaseDbStore
from jiuwen.context.memory_engine.store.base_kv_store import BaseKVStore
from jiuwen.context.memory_engine.store.base_memory_index import BaseMemoryIndex
from jiuwen.context.memory_engine.store.kv_store_wrapper import KVStoreWrapper
from jiuwen.context.memory_engine.store.sql_db_store import SqlDbStore
from jiuwen.context.memory_engine.store.user_mem_store import UserMemStore


class MemoryEngine(metaclass=Singleton):
    """
    Memory engine implementation with singleton pattern.

    Defines the core interface for memory storage and retrieval operations.
    Provides unified memory management functionality including conversation memory,
    user variables, semantic search, and persistence.

    Concrete implementations should handle memory operations across multiple storage
    backends (KV store, semantic store, database store).
    """

    DEFAULT_VALUE: str = "__default__"
    USER_VAR_CONFIG_KEY: str = "user_var_config"
    MEMORY_FLAGS_CONFIG_KEY: str = "memory_flags_config"
    TOPIC_PROFILE_CONFIG_KEY: str = "topic_profile_config"
    SEPARATOR: str = "/"
    MAX_ID_LENGTH: int = 256

    def __init__(self):
        """
        Initialize the memory engine
        """
        self.user_memory_manager = None
        self.kv_store: BaseKVStore | None = None
        self.kv_store_wrapper: KVStoreWrapper | None = None
        self.message_manager: MessageManager | None = None
        self.topic_profile_manager: TopicProfileManager | None = None
        self.variable_manager: VariableManager | None = None
        self.write_manager: WriteManager | None = None
        self.search_manager: SearchManager | None = None
        self.generator: Generator | None = None
        # config
        self._memory_engine_config: MemoryEngineConfig = MemoryEngineConfig()
        # llm
        self._base_llm: BaseChatModel | None = None
        self._scope_llm: dict[str, BaseChatModel] = {}
        self._semantic_index: BaseMemoryIndex | None = None

    @staticmethod
    def _fill_processed_mem_result(
        all_memory: list[BaseMemoryUnit],
    ) -> ProcessedMemResult:
        processed_mem_result: ProcessedMemResult = ProcessedMemResult()
        profile_topics_dict: dict[str, dict[str, ProfileTopicTagResult]] = {}
        for memory_unit in all_memory:
            if isinstance(memory_unit, TopicProfileUnit):
                if memory_unit.topic_name not in profile_topics_dict:
                    profile_topics_dict[memory_unit.topic_name] = {}
                if memory_unit.tag_name in profile_topics_dict[memory_unit.topic_name]:
                    profile_topics_dict[memory_unit.topic_name][
                        memory_unit.tag_name
                    ].value += f",{memory_unit.tag_mem}"
                else:
                    profile_topics_dict[memory_unit.topic_name][
                        memory_unit.tag_name
                    ] = ProfileTopicTagResult(
                        name=memory_unit.tag_name, value=memory_unit.tag_mem
                    )
            if isinstance(memory_unit, VariableUnit):
                processed_mem_result.variables.append(
                    VariableResult(
                        variable_key=memory_unit.variable_name,
                        variable_value=memory_unit.variable_mem,
                    )
                )
            if isinstance(memory_unit, UserMemoryUnit):
                processed_mem_result.user_memory.append(
                    UserMemoryResult(
                        memory_type=memory_unit.mem_type.value,
                        memory_content=memory_unit.mem,
                        operation_type=memory_unit.operation_type,
                    )
                )
        processed_mem_result.profile_topics = [
            ProfileTopicResult(topic=topic_name, tags=list(tag_result.values()))
            for topic_name, tag_result in profile_topics_dict.items()
        ]
        return processed_mem_result

    @staticmethod
    def _fill_profile_topic_result(
        topic_profiles: dict[str, Any],
    ) -> list[ProfileTopicResult]:
        profile_topic_results: list[ProfileTopicResult] = []
        for topic_name, tag_results in topic_profiles.items():
            if not tag_results:
                continue
            profile_topic_tag_results: list[ProfileTopicTagResult] = []
            for tag_name, tag_value in tag_results.items():
                profile_topic_tag_results.append(
                    ProfileTopicTagResult(name=tag_name, value=tag_value)
                )
            profile_topic_results.append(
                ProfileTopicResult(topic=topic_name, tags=profile_topic_tag_results)
            )
        return profile_topic_results

    def register_store(
        self, kv_store: BaseKVStore, db_store: BaseDbStore | None = None
    ):
        """
        Register store instance.

        Args:
            kv_store: Key-value store for fast structured data access
            db_store: Database store for persistent data storage
        """
        self.kv_store = kv_store
        self.kv_store_wrapper = KVStoreWrapper(kv_store)
        data_id_generator = DataIdManager()
        user_mem_store = UserMemStore(kv_store)
        if db_store:
            sql_db_store = SqlDbStore(db_store)
            self.message_manager = MessageManager(sql_db_store, data_id_generator)
        self.topic_profile_manager = TopicProfileManager(kv_store)
        self.variable_manager = VariableManager(kv_store)
        self.user_memory_manager = UserMemoryManager(
            data_id_generator=data_id_generator,
        )
        if self._semantic_index:
            self.user_memory_manager.memory_index = self._semantic_index
        managers = {
            MemoryType.USER_MEMORY.value: self.user_memory_manager,
            MemoryType.TOPIC_PROFILE.value: self.topic_profile_manager,
            MemoryType.VARIABLE.value: self.variable_manager,
        }
        self.write_manager = WriteManager(managers, user_mem_store)
        self.search_manager = SearchManager(managers)
        self.generator = Generator(self.search_manager)

    def register_plugin(self, name: str, cls: type, params: dict[str, Any]):
        """
        Register plugin.

        Args:
            name: plugin name
            cls: class name of plugin
            params: plugin class parameters
        """
        if name != "semantic_index":
            raise ValueError(f"Unsupported plugin: {name}")
        self._semantic_index = cls(**params)
        if self.user_memory_manager:
            self.user_memory_manager.memory_index = self._semantic_index

    def init_base_llm(self, llm: BaseChatModel) -> bool:
        """
        Initialize the default LLM for memory processing tasks.

        Args:
            llm: Language model client
        Returns:
            True if initialization succeeded
        """
        self._base_llm = llm
        return True

    def set_config(self, config: MemoryEngineConfig):
        """
        Set configuration.

        Args:
            config: memory engine configuration parameters
        """
        # validate
        for forbidden_tag in config.user_profile_forbidden_topic:
            if not forbidden_tag.name:
                logger.error(
                    "set config failed due to invalid tag name for field user_profile_forbidden_topic."
                )
                return
        for profile_topic in config.default_profile_topics:
            if not profile_topic.topic:
                logger.error(
                    "set config failed due to invalid topic name for field profile_topics."
                )
                return
            for tag in profile_topic.tags:
                if not tag.name:
                    logger.error(
                        "set config failed due to invalid tag name for field profile_topics."
                    )
                    return

        self._memory_engine_config = config

    async def set_scope_config(self, scope_id: str, config: MemoryScopeConfig) -> bool:
        """
        Set memory configuration for a specified scope.

        Allows different scopes to have customized memory retention policies,
        storage limits, and behavior settings.

        Args:
            scope_id: Unique identifier for the scope
            config: scope-specific memory configuration
        Returns:
            True if setting succeeded
        """
        if not self._validate_id(scope_id, "scope_id"):
            logger.error("set scope config failed due to invalid id.")
            return False
        for variable in config.mem_variables:
            if not variable.name:
                logger.error(
                    "set scope config failed due to invalid variable name for field mem_variables."
                )
                return False
        if not self.kv_store:
            logger.warning(f"kv store is None, skip setting scope config: {scope_id}")
            return True
        # set user variable config
        var_key = (
            f"{MemoryEngine.USER_VAR_CONFIG_KEY}{MemoryEngine.SEPARATOR}{scope_id}"
        )
        # set flag key config
        flag_key = (
            f"{MemoryEngine.MEMORY_FLAGS_CONFIG_KEY}{MemoryEngine.SEPARATOR}{scope_id}"
        )
        flag_val = json.dumps(config.model_dump(exclude={"mem_variables"}))
        await self.kv_store.set(flag_key, flag_val)
        if config.mem_variables:
            var_dict = {
                variable.name: variable.description for variable in config.mem_variables
            }
            var_json_str = json.dumps(var_dict, ensure_ascii=False)
            await self.kv_store.set(var_key, var_json_str)
        else:
            # delete old user variable config when setting up with an empty configuration
            if await self.kv_store.exists(var_key):
                await self.kv_store.delete(var_key)

        return True

    async def set_user_profile_tag(self, topic_name: str, tag: ProfileTopicTag):
        """set tag config of user profile"""
        if not topic_name:
            logger.error("set user profile tag failed due to invalid topic name.")
            return
        if not tag.name:
            logger.error("set user profile tag failed due to invalid tag name.")
            return
        payload = {
            "description": tag.description,
            "update_policy": tag.update_policy,
        }
        payload_str = json.dumps(payload, ensure_ascii=False)
        await self.kv_store_wrapper.set(
            main_key=[MemoryEngine.TOPIC_PROFILE_CONFIG_KEY, topic_name],
            sub_key=[tag.name],
            value=payload_str,
        )

    async def delete_user_profile_tag(self, topic_name: str, tag_name: str):
        """delete tag config of user profile"""
        if not topic_name:
            logger.error("delete user profile tag failed due to invalid topic name.")
            return
        if not tag_name:
            logger.error("delete user profile tag failed due to invalid tag name.")
            return
        main_key = [MemoryEngine.TOPIC_PROFILE_CONFIG_KEY, topic_name]
        sub_key = [tag_name]
        if not await self.kv_store_wrapper.exists(main_key, sub_key):
            logger.warning(
                "delete user profile tag failed due to this tag may not exist."
            )
            return
        await self.kv_store_wrapper.delete(main_key, sub_key)
        # delete all user topic profiles corresponding to the topic and tag
        for default_profile_topic in self._memory_engine_config.default_profile_topics:
            if default_profile_topic.topic == topic_name:
                default_tag_names = [t.name for t in default_profile_topic.tags]
                if tag_name in default_tag_names:
                    logger.warning(
                        "cannot delete corresponding memory due to the default "
                        "config contains topics and tags with the same name."
                    )
                    return
        await self._delete_all_topic_profile_by_tag(topic_name, tag_name)

    async def get_user_profile_tag(
        self, topic_names: List[str] | None
    ) -> List[ProfileTopicConfig]:
        """get tag config of user profile"""
        ret = []
        if not topic_names:
            topics = await self.kv_store_wrapper.get_next_key_of_main(
                [MemoryEngine.TOPIC_PROFILE_CONFIG_KEY]
            )
        else:
            topics = topic_names
        for topic_name in topics:
            sub_profile = await self.kv_store_wrapper.get_all_value(
                main_key=[MemoryEngine.TOPIC_PROFILE_CONFIG_KEY, topic_name]
            )
            tags = []
            for sub_name, sub_value in sub_profile.items():
                parsed = json.loads(sub_value)
                sub_tag = ProfileTopicTag(
                    name=sub_name,
                    description=parsed.get("description", ""),
                    update_policy=parsed.get("update_policy", "OVERWRITE"),
                )
                tags.append(sub_tag)
            sub_config = ProfileTopicConfig(topic=topic_name, tags=tags)
            ret.append(sub_config)
        return ret

    async def get_scope_config(self, scope_id: str) -> MemoryScopeConfig:
        """
        Get memory configuration for a specified scope.

        Args:
            scope_id: Unique identifier for the scope
        Returns:
            MemoryScopeConfig: scope-specific memory configuration
        """
        if not self._validate_id(scope_id, "scope_id"):
            logger.error("get scope config failed due to invalid id.")
            return MemoryScopeConfig()
        if not self.kv_store:
            logger.warning(
                f"kv store is None, skip getting scope config from store: {scope_id}"
            )
            return MemoryScopeConfig()

        # get user variable config from kv store
        var_json_str = await self.kv_store.get(
            f"{MemoryEngine.USER_VAR_CONFIG_KEY}{MemoryEngine.SEPARATOR}{scope_id}"
        )
        # get flag config from kv store
        flag_json_str = await self.kv_store.get(
            f"{MemoryEngine.MEMORY_FLAGS_CONFIG_KEY}{MemoryEngine.SEPARATOR}{scope_id}"
        )
        flag_dict = {}
        if flag_json_str:
            try:
                flag_dict = json.loads(flag_json_str)
            except json.JSONDecodeError as e:
                logger.error(f"memory scope config format error: {e.msg}")

        var_list = []
        if var_json_str:
            var_dict = json.loads(var_json_str)
            var_list = [Variable(name=k, description=v) for k, v in var_dict.items()]

        return MemoryScopeConfig(
            mem_variables=var_list,
            enable_long_term_mem=flag_dict.get("enable_long_term_mem", True),
            enable_user_profile=flag_dict.get("enable_user_profile", True),
        )

    def set_scope_llm(self, scope_id: str, llm: BaseChatModel) -> bool:
        """
        Set a dedicated LLM for a specific scope.

        Enables scopes to use different language models tailored to their
        specific needs or domains.

        Args:
            scope_id: Unique identifier for the scope
            llm: Language model client instance
        Returns:
            True if setting succeeded
        """
        if not self._validate_id(scope_id, "scope_id"):
            logger.error("set scope llm failed due to invalid id.")
            return False

        self._scope_llm[scope_id] = llm
        return True

    async def process_messages(
        self,
        messages: list[BaseMessage],
        topics: list[ProfileTopicConfig] | None = None,
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
        session_id: str = DEFAULT_VALUE,
        mode: ProcessMemoryMode = ProcessMemoryMode.BATCH_MODE,
    ) -> ProcessedMemResult:
        """
        process messages to memory storage.

        Args:
            messages: List of message objects to store
            topics: user profile topic list
            user_id: Unique identifier for the user
            scope_id: Unique identifier for the scope
            session_id: Optional session identifier for scope related messages
            mode: Mode of processing
                REALTIME_MODE: Only extract memory instruct
                BATCH_MODE: Extract user memory without memory instruct
        Returns:
            ProcessedMemResult: the memory content generated this time.
        """
        if (
            not self._validate_id(user_id, "user_id")
            or not self._validate_id(scope_id, "scope_id")
            or not self._validate_id(session_id, "session_id")
        ):
            logger.error("process messages failed due to invalid id.")
            return ProcessedMemResult()
        if not isinstance(mode, ProcessMemoryMode):
            logger.error(f"process messages invalid mode: {mode}")
            return ProcessedMemResult()
        if len(messages) == 0:
            logger.info("No messages to process")
            return ProcessedMemResult()
        llm = self._get_scope_llm(scope_id=scope_id)
        if not llm:
            logger.error("llm is not initialized.")
            return ProcessedMemResult()

        scope_mem_config = await self.get_scope_config(scope_id=scope_id)
        if scope_mem_config.enable_long_term_mem and (not self._semantic_index):
            logger.error(
                "Long term memory cannot be enabled when semantic_index is empty."
                " Skip long term memory this time"
            )
            scope_mem_config.enable_long_term_mem = False

        profile_topics = await self._get_user_profile_config(topics=topics)

        # when multi messages, use last msg_id
        msg_id = messages[-1].id if messages else None

        all_memory: list[BaseMemoryUnit] = await self.generator.gen_all_memory(
            scope_id=scope_id,
            user_id=user_id,
            messages=messages,
            history_messages=[],
            session_id=session_id,
            engine_config=self._memory_engine_config,
            scope_config=scope_mem_config,
            base_chat_model=llm,
            message_mem_id=msg_id,
            profile_topics=profile_topics,
            mode=mode,
        )
        await self.write_manager.add_mem(mem_units=all_memory)
        return self._fill_processed_mem_result(all_memory)

    async def search_user_mem(
        self, user_id: str, scope_id: str, query: str, num: int
    ) -> list[dict[str, Any]]:
        """
        Search user memory based on query, user_id and scope_id; return top-num results.
        """
        if not self._semantic_index:
            logger.info(
                "semantic index is None, skip search long term memory, return []"
            )
            return []
        if not user_id or not user_id.strip():
            raise ValueError("Search user memory failed, user ID is empty")
        if not scope_id or not scope_id.strip():
            raise ValueError("Search user memory failed, scope ID is empty")
        if not query or not query.strip():
            raise ValueError("Search user memory failed, query is empty")
        if num is None or num <= 0:
            raise ValueError(
                f"Search user memory failed, num should be greater than zero, but get {num}"
            )
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            raise ValueError(
                "Search user memory failed, user_id or scope_id is illegal"
            )
        return await self.search_manager.search(
            query=query, top_k=num, user_id=user_id, scope_id=scope_id
        )

    async def list_user_mem(
        self, user_id: str, scope_id: str, offset: int = 0, size: int = 10
    ) -> list[dict[str, Any]]:
        """
        List user memories with pagination support.

        Retrieves memories in chronological order, suitable for displaying
        conversation history or memory browsing interfaces.

        Args:
            user_id: User identifier to search within
            scope_id: Unique identifier for the scope
            offset: Start index for listing memories
            size: Number of memories to list

        Returns:
            List of memory information
        """
        if not user_id or not user_id.strip():
            raise ValueError("List user memory failed, user ID is empty")
        if not scope_id or not scope_id.strip():
            raise ValueError("List user memory failed, scope ID is empty")
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            raise ValueError("List user memory failed, user_id or scope_id is illegal")
        if offset < 0:
            raise ValueError("List user memory failed, offset is invalid")
        if size <= 0:
            raise ValueError("List user memory failed, size is invalid")
        if not self.search_manager:
            raise ValueError("List user memory failed, search manager is not inited")
        return await self.search_manager.list_user_mem(
            user_id=user_id, scope_id=scope_id, offset=offset, size=size
        )

    async def delete_mem_by_id(
        self, mem_id: str, user_id: str = DEFAULT_VALUE, scope_id: str = DEFAULT_VALUE
    ):
        """
        Delete a specific memory by ID.

        Args:
            user_id: Unique identifier for the user
            scope_id: Unique identifier for the scope
            mem_id: Unique identifier of the memory to delete
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("delete mem by id failed due to invalid id.")
            return False
        if not self.write_manager:
            raise ValueError("Write manager is not initialized.")
        if not self._semantic_index:
            raise ValueError("semantic index is not initialized.")
        await self.write_manager.delete_mem_by_id(
            user_id=user_id, scope_id=scope_id, mem_id=mem_id
        )
        return True

    async def delete_mem_by_user_id(
        self, user_id: str = DEFAULT_VALUE, scope_id: str = DEFAULT_VALUE
    ):
        """
        Delete all type memories for a user with scope id.

        Useful for implementing "forget me" functionality or cleaning up user data.

        Args:
            user_id: User identifier whose memories should be deleted
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("delete mem by user id failed due to invalid id.")
            return False
        if not self.write_manager:
            raise ValueError("Write manager is not initialized.")
        await self.write_manager.delete_mem_by_user_id(
            user_id=user_id, scope_id=scope_id
        )
        return True

    async def delete_memory_by_scope_id(self, scope_id: str):
        """
        Delete all type memories for a scope id.

        Args:
            scope_id: Unique identifier for the scope
        """
        if not scope_id or not self._validate_id(scope_id, "scope_id"):
            logger.error(
                f"delete mem by scope id failed due to invalid id : {scope_id}"
            )
            return False
        if not self.write_manager:
            raise ValueError("Write manager is not initialized.")
        await self.write_manager.delete_mem_by_scope_id(scope_id=scope_id)
        return True

    async def update_mem_by_id(
        self,
        mem_id: str,
        memory: str,
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ):
        """
        Update the content of an existing memory entry.

        Args:
            mem_id: Unique identifier of the memory to update
            memory: New content for the memory
            user_id: Unique identifier for the user
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("update mem by id failed due to invalid id.")
            return False
        if not self.write_manager:
            raise ValueError("Write manager is not initialized.")
        if not self._semantic_index:
            raise ValueError("semantic index is not initialized.")
        await self.write_manager.update_mem_by_id(
            user_id=user_id, scope_id=scope_id, mem_id=mem_id, memory=memory
        )
        return True

    async def get_user_variables(
        self,
        names: list[str] | str | None = None,
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ) -> dict[str, str]:
        """
        Retrieve a specific user variable by name.

        User variables store persistent user preferences, settings, or context
        that should be maintained across conversations.

        Args:
            names: Name of the variable(s) to get, return all variables when is None
            user_id: User identifier
            scope_id: Unique identifier for the scope

        Returns:
            Value of the user variable as string
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("get user variables failed due to invalid id.")
            return {}
        if not self.search_manager:
            raise ValueError("Search manager is not initialized.")
        if not names:
            all_variables = await self.search_manager.get_all_user_variable(
                user_id, scope_id
            )
            return all_variables

        if isinstance(names, str):
            variable = await self.search_manager.get_user_variable(
                user_id, scope_id, names
            )
            return {names: variable}

        if isinstance(names, list):
            all_variables = {}
            for name in names:
                if not name:
                    logger.warning("invalid variable name, skip get.")
                    continue
                variable = await self.search_manager.get_user_variable(
                    user_id, scope_id, name
                )
                all_variables[name] = variable
            return all_variables

        logger.warning(f"Unknown user variable name {names}.")
        return {}

    async def get_topic_profile_by_topics(
        self,
        user_id: str,
        scope_id: str,
        topics: list[str],
        enable_default_topics: bool = False,
    ) -> list[ProfileTopicResult]:
        """
        Get topic profile by topic list.
        Args:
            user_id: User identifier.
            scope_id: scope identifier.
            topics: user profile topic list.
            enable_default_topics: decide whether to return to the default topics.
        Returns:
            dict[str, dict[str, str]]: list of profile topic results.
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("get topic profile by topics failed due to invalid id.")
            return []
        if not self.search_manager:
            raise ValueError("Search manager is not initialized")
        if not topics:
            # if topics is empty, get all topic profile by the user and scope id
            topic_profiles = await self.search_manager.get_all_topic_profile(
                user_id, scope_id
            )
        else:
            useful_topics = set(topics)
            useful_topics.update(
                {
                    t.topic
                    for t in self._memory_engine_config.default_profile_topics
                    if enable_default_topics or t.topic in topics
                }
            )
            useful_topics = list(useful_topics)
            topic_profiles = {}
            for topic in useful_topics:
                topic_profiles[topic] = await self.search_manager.get_topic_profile(
                    user_id, scope_id, topic
                )

        return self._fill_profile_topic_result(topic_profiles)

    async def update_topic_profile(
        self,
        topic: str,
        tag_values: dict[str, str],
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ):
        """
        Update topic profile.

        Args:
            topic: user profile topic.
            tag_values: tag name to value pairs
            user_id: User identifier to update
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("update topic profile failed due to invalid id.")
            return
        if not topic:
            logger.error("update topic profile failed due to invalid topic name.")
            return
        if not self.topic_profile_manager:
            raise ValueError("TopicProfileManager is not initialized.")

        for key, value in tag_values.items():
            if not key:
                logger.warning("invalid topic profile tag, skip update.")
                continue
            await self.topic_profile_manager.update_topic_profile(
                user_id=user_id,
                scope_id=scope_id,
                topic_name=topic,
                tag_name=key,
                tag_desc=value,
            )

    async def delete_topic_profile(
        self,
        topic: str,
        tags: list[str],
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ):
        """
        Delete topic profile.

        Args:
            topic: user profile topic.
            tags: tag name list
            user_id: User identifier to delete
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("delete topic profile failed due to invalid id.")
            return
        if not topic:
            logger.error("delete topic profile failed due to invalid topic name.")
            return
        if not self.topic_profile_manager:
            raise ValueError("TopicProfileManager is not initialized.")

        if not tags:
            await self.topic_profile_manager.delete_topic_profile_by_topic(
                user_id=user_id, scope_id=scope_id, topic_name=topic
            )
            return

        for tag in tags:
            if not tag:
                logger.warning("invalid topic profile tag, skip delete.")
                continue
            await self.topic_profile_manager.delete_topic_profile_by_tag(
                user_id=user_id, scope_id=scope_id, topic_name=topic, tag_name=tag
            )

    async def update_user_variables(
        self,
        variables: dict[str, str],
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ):
        """
        Update user variables.

        Args:
            variables: variable name to value pairs
            user_id: User identifier to update
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("update user variables failed due to invalid id.")
            return
        if not self.variable_manager:
            raise ValueError("Variable manager is not initialized.")
        for name, value in variables.items():
            if not name:
                logger.warning("invalid variable name, skip update.")
                continue
            await self.variable_manager.update_user_variable(
                user_id=user_id, scope_id=scope_id, var_name=name, var_mem=value
            )

    async def delete_user_variables(
        self,
        names: list[str],
        user_id: str = DEFAULT_VALUE,
        scope_id: str = DEFAULT_VALUE,
    ):
        """
        Delete user variables.

        Args:
            names: Name of the variables to delete
            user_id: User identifier to delete
            scope_id: Unique identifier for the scope
        """
        if not self._validate_id(user_id, "user_id") or not self._validate_id(
            scope_id, "scope_id"
        ):
            logger.error("delete user variables failed due to invalid id.")
            return
        for name in names:
            if not name:
                logger.warning("invalid variable name, skip delete.")
                continue
            await self.variable_manager.delete_user_variable(
                user_id=user_id, scope_id=scope_id, var_name=name
            )

    def _get_scope_llm(self, scope_id: str) -> BaseChatModel | None:
        if scope_id not in self._scope_llm:
            return self._base_llm
        return self._scope_llm[scope_id]

    def _validate_id(self, input_id: str, id_desc: str) -> bool:
        if len(input_id) > self.MAX_ID_LENGTH:
            logger.error(
                f"{id_desc} must be less than or equal to {self.MAX_ID_LENGTH} characters."
            )
            return False
        if self.SEPARATOR in input_id:
            logger.error(f"{id_desc} must not contain '{self.SEPARATOR}'.")
            return False
        return True

    async def _delete_all_topic_profile_by_tag(self, topic_name: str, tag_name: str):
        if not self.topic_profile_manager:
            logger.debug("topic profile manager is None, skip delete.")
            return
        await self.topic_profile_manager.delete_all_topic_profile_by_tag(
            topic_name, tag_name
        )

    async def _get_user_profile_config(
        self, topics: list[ProfileTopicConfig] | None = None
    ) -> List[ProfileTopicConfig]:
        if isinstance(topics, list) and len(topics) == 0:
            return []
        if topics is None:
            # return all stored topic config, if the topics is empty
            profile_topics = await self.get_user_profile_tag(topic_names=[])
            return profile_topics

        # the specified topics are preferentially used, if the corresponding tag is empty, using stored topic config
        profile_topics: List[ProfileTopicConfig] = []
        query_topic_names: List[str] = []
        for topic in topics:
            if topic.tags:
                profile_topics.append(topic)
            else:
                query_topic_names.append(topic.topic)
        if query_topic_names:
            query_topics = await self.get_user_profile_tag(query_topic_names)
            for query_topic in query_topics:
                if query_topic.tags:
                    profile_topics.append(query_topic)
                else:
                    # if the specified topic has not been stored, skip it and log it
                    logger.warning(f"Non-existent topic: {query_topic.topic}")
        return profile_topics
