# !/usr/bin/env python
# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
import re
from typing import Any

from jiuwen.common.llm_service.base import BaseChatModel
from jiuwen.common.llm_service.messages import BaseMessage
from jiuwen.common.log.base import logger
from jiuwen.context.memory_engine.config.config import (
    MemoryEngineConfig,
    ProfileTopicConfig,
    MemoryScopeConfig,
    ProcessMemoryMode,
)
from jiuwen.context.memory_engine.generation.conflict_resolution import (
    ConflictResolution,
)
from jiuwen.context.memory_engine.generation.memory_analyzer import (
    MemoryAnalyzer,
    MemoryAnalyzerResult,
)
from jiuwen.context.memory_engine.generation.user_memory_extractor import (
    UserMemoryExtractor,
)
from jiuwen.context.memory_engine.mem_unit.memory_type import MemoryType
from jiuwen.context.memory_engine.mem_unit.memory_unit import (
    BaseMemoryUnit,
    UserMemoryUnit,
    VariableUnit,
    TopicProfileUnit,
    ConflictType,
)
from jiuwen.context.memory_engine.prompt.semantic_validation import (
    SEMANTIC_VALIDATION_PROMPT,
)
from jiuwen.context.memory_engine.search.search_manager.search_manager import (
    SearchManager,
)

category_to_memory_type = {
    "user_profile": MemoryType.USER_PROFILE,
    "others": MemoryType.OTHERS,
}


async def _get_conflict_input(
    user_id: str, scope_id: str, new_message: str, search_manager: SearchManager
):
    historical_profiles = []
    search_results = await search_manager.search(
        user_id=user_id,
        scope_id=scope_id,
        query=new_message,
        top_k=5,
        search_type=MemoryType.USER_MEMORY.value,
    )
    for search_result in search_results:
        historical_profiles.append(
            (search_result["id"], search_result["mem"], search_result["score"])
        )
    input_memory_ids_map: dict[int, str] = {}
    input_memories: list[str] = []
    i = 1
    for historical in historical_profiles:
        mem_id, mem_content, _ = historical
        input_memories.append(mem_content)
        input_memory_ids_map[i] = mem_id
        i += 1
    return input_memories, input_memory_ids_map


def _process_conflict_info(
    conflict_info: list[dict], input_memory_ids_map: dict[int, str]
) -> list[dict]:
    process_conflict_info = []
    for conflict in conflict_info:
        conf_id = int(conflict["id"])
        conf_mem = conflict["text"]
        conf_event = conflict["event"]
        if conf_id == 0:
            process_conflict_info.append(
                {"id": "-1", "text": conf_mem, "event": conf_event}
            )
            continue
        map_id = input_memory_ids_map[conf_id]
        process_conflict_info.append(
            {"id": map_id, "text": conf_mem, "event": conf_event}
        )
    return process_conflict_info


async def _semantic_validate(
    obtained_memories: list[dict], old_memory: str, base_chat_model: BaseChatModel
) -> list[tuple[str, str]]:
    ret_ids = []
    for obtained_memory in obtained_memories:
        prompt = SEMANTIC_VALIDATION_PROMPT.format(
            old_mem=old_memory, obtained_mem=obtained_memory["mem"]
        )
        message = [{"role": "user", "content": prompt}]
        response = await base_chat_model.ainvoke(message)
        if re.search(r'\bCORRECT\b', response.content) and not re.search(r'\bWRONG\b', response.content):
            logger.debug(
                f"semantic_validate result: old_memory:{old_memory}, obtained_memory:{obtained_memory['mem']},"
                f" result: CORRECT"
            )
            ret_ids.append((obtained_memory["id"], obtained_memory["mem"]))
        else:
            logger.debug(
                f"semantic_validate result: old_memory:{old_memory}, obtained_memory:{obtained_memory['mem']},"
                f" result: WRONG"
            )
    return ret_ids


class Generator:
    def __init__(self, search_manager: SearchManager) -> None:
        self._search_manager = search_manager

    @staticmethod
    def _get_variable_units_from_memory_analyze(
        user_id: str, scope_id: str, result: MemoryAnalyzerResult
    ) -> list[BaseMemoryUnit]:
        variable_units = []
        for variable in result.variables:
            if not variable.variable_value or variable.variable_value == "":
                continue
            variable_units.append(
                VariableUnit(
                    user_id=user_id,
                    scope_id=scope_id,
                    mem_type=MemoryType.VARIABLE,
                    variable_name=variable.variable_key,
                    variable_mem=variable.variable_value,
                )
            )
        return variable_units

    @staticmethod
    def _get_user_profile_topic_from_memory_analyze(
        user_id: str,
        scope_id: str,
        engine_config: MemoryEngineConfig,
        profile_topics: list[ProfileTopicConfig],
        result: MemoryAnalyzerResult,
    ) -> list[BaseMemoryUnit]:
        topic_profile_units = []
        for user_profile_topic in result.user_profile_topics:
            tags = set()
            for dpt in engine_config.default_profile_topics:
                if dpt.topic == user_profile_topic.topic:
                    tags.update(tag.name for tag in dpt.tags)
            for pt in profile_topics:
                if pt.topic == user_profile_topic.topic:
                    tags.update(tag.name for tag in pt.tags)
            for tag in user_profile_topic.tags:
                if not tag.value or tag.value == "":
                    continue
                if not tags or tag.name not in tags:
                    continue
                topic_profile_units.append(
                    TopicProfileUnit(
                        topic_name=user_profile_topic.topic,
                        tag_name=tag.name,
                        tag_mem=tag.value,
                        mem_type=MemoryType.TOPIC_PROFILE,
                        user_id=user_id,
                        scope_id=scope_id,
                    )
                )
        return topic_profile_units

    async def gen_all_memory(self, **kwargs) -> list[BaseMemoryUnit]:
        """Generate all memory units based on input"""
        messages = kwargs.get("messages")
        engine_config = kwargs.get("engine_config")
        scope_config = kwargs.get("scope_config")
        model = kwargs.get("base_chat_model")
        user_id = kwargs.get("user_id")
        scope_id = kwargs.get("scope_id")
        history_messages = kwargs.get("history_messages")
        message_mem_id = kwargs.get("message_mem_id")
        profile_topics = kwargs.get("profile_topics")
        mode = kwargs.get("mode")

        all_memory_results = []
        memory_analyze_res = None
        if mode == ProcessMemoryMode.BATCH_MODE:
            memory_analyze_res = await MemoryAnalyzer.analyze(
                messages=messages,
                history_messages=history_messages,
                base_chat_model=model,
                engine_config=engine_config,
                scope_config=scope_config,
                profile_topics=profile_topics,
            )

            if not memory_analyze_res:
                logger.warning("Failed to analyze memory")
                return []

            all_memory_results += Generator._get_variable_units_from_memory_analyze(
                user_id=user_id,
                scope_id=scope_id,
                result=memory_analyze_res,
            )

            all_memory_results += Generator._get_user_profile_topic_from_memory_analyze(
                user_id=user_id,
                scope_id=scope_id,
                result=memory_analyze_res,
                engine_config=engine_config,
                profile_topics=profile_topics,
            )

        if not scope_config.enable_long_term_mem:
            logger.info("Not enable long term memory")
            return all_memory_results
        merged_units = await self._categories_to_memory_unit(
            categories=memory_analyze_res.category if memory_analyze_res else [],
            history_messages=history_messages,
            messages=messages,
            user_id=user_id,
            scope_id=scope_id,
            base_chat_model=model,
            message_mem_id=message_mem_id,
            scope_config=scope_config,
            mode=mode,
        )
        all_memory_results += merged_units
        return all_memory_results

    async def _resolve_conflict(
        self,
        user_profile_memory: list,
        user_id: str,
        scope_id: str,
        base_chat_model: BaseChatModel,
        message_mem_id: str,
    ) -> list[UserMemoryUnit]:
        user_profile_data = []
        for memory in user_profile_memory:
            profile = memory["mem_content"]
            input_memories, input_memory_ids_map = await _get_conflict_input(
                user_id, scope_id, profile, self._search_manager
            )
            tmp_conflict_info = await ConflictResolution.check_conflict(
                old_messages=input_memories,
                new_message=profile,
                base_chat_model=base_chat_model,
            )
            conflict_info = _process_conflict_info(
                tmp_conflict_info, input_memory_ids_map
            )
            cur_memory_confict_info = [
                info for info in conflict_info if info.get("id") == "-1"
            ]
            cur_memory_operation_type = None
            if len(cur_memory_confict_info):
                cur_memory_operation_type = cur_memory_confict_info[0].get("event")
            user_profile_data.append(
                UserMemoryUnit(
                    mem=memory["mem_content"],
                    user_id=user_id,
                    scope_id=scope_id,
                    conflict_info=conflict_info,
                    mem_type=category_to_memory_type.get(memory.get("mem_type")),
                    message_mem_id=message_mem_id,
                    operation_type=cur_memory_operation_type,
                )
            )
        return user_profile_data

    async def _categories_to_memory_unit(
        self,
        categories: list[str],
        history_messages: list[BaseMessage],
        messages: list[BaseMessage],
        user_id: str,
        scope_id: str,
        base_chat_model: BaseChatModel,
        message_mem_id: str,
        scope_config: MemoryScopeConfig,
        mode: ProcessMemoryMode,
    ) -> list[BaseMemoryUnit]:
        user_memory = await UserMemoryExtractor.get_user_memory(
            messages,
            history_messages,
            base_chat_model,
            categories,
            scope_config,
            mode,
        )
        logger.debug(f"Generated user memories: {user_memory}")
        add_memories = []
        for mem_dict in user_memory:
            if (
                mem_dict.get("mem_type", "") == "user_profile"
                and "mem_instruct" not in mem_dict
            ):
                add_memories.append(mem_dict)
            elif mem_dict.get("mem_instruct", "") == "ADD":
                add_memories.append(mem_dict)
        ret_memories = await self._resolve_conflict(
            add_memories, user_id, scope_id, base_chat_model, message_mem_id
        )
        ret_memories += await self._handle_memory_with_instruct(
            user_id=user_id,
            scope_id=scope_id,
            base_chat_model=base_chat_model,
            message_mem_id=message_mem_id,
            user_memories=user_memory,
        )
        logger.debug(f"Generated {len(ret_memories)} user memories: {ret_memories}")
        return ret_memories

    async def _handle_memory_with_instruct(
        self,
        user_id: str,
        scope_id: str,
        base_chat_model: BaseChatModel,
        message_mem_id: str,
        user_memories: list[dict[str, Any]],
    ) -> list[BaseMemoryUnit]:
        update_memories = []
        delete_memories = []
        for mem in user_memories:
            if mem.get("mem_instruct", "") == "UPDATE":
                update_memories.append(mem)
            elif mem.get("mem_instruct", "") == "DELETE":
                delete_memories.append(mem)
        ret_memories = []
        for memory in update_memories:
            old_mem = memory.get("old_mem")
            if not old_mem:
                logger.warning(
                    f"old_mem is empty when updating memory, skip this memory: {memory}"
                )
                continue
            obtained_mem = await self._search_manager.search(
                user_id, scope_id, old_mem, top_k=1
            )
            id_mems = await _semantic_validate(obtained_mem, old_mem, base_chat_model)
            for id_mem in id_mems:
                ret_memories.append(
                    UserMemoryUnit(
                        mem_type=category_to_memory_type.get(memory.get("mem_type")),
                        user_id=user_id,
                        scope_id=scope_id,
                        mem=memory["mem_content"],
                        conflict_info=[
                            {
                                "id": id_mem[0],
                                "text": id_mem[1],
                                "event": ConflictType.UPDATE.value,
                            }
                        ],
                        message_mem_id=message_mem_id,
                        operation_type=ConflictType.UPDATE.value,
                    )
                )
        for memory in delete_memories:
            old_mem = memory.get("old_mem")
            if not old_mem:
                logger.warning(
                    f"old_mem is empty when deleting memory, skip this memory: {memory}"
                )
                continue
            obtained_mem = await self._search_manager.search(
                user_id, scope_id, old_mem, top_k=1
            )
            id_mems = await _semantic_validate(obtained_mem, old_mem, base_chat_model)
            for id_mem in id_mems:
                ret_memories.append(
                    UserMemoryUnit(
                        mem_type=category_to_memory_type.get(memory.get("mem_type")),
                        user_id=user_id,
                        scope_id=scope_id,
                        mem=id_mem[1],
                        conflict_info=[
                            {
                                "id": id_mem[0],
                                "text": id_mem[1],
                                "event": ConflictType.DELETE.value,
                            }
                        ],
                        message_mem_id=message_mem_id,
                        operation_type=ConflictType.DELETE.value,
                    )
                )
        return ret_memories
