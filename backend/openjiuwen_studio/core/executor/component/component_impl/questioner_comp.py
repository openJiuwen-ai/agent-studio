# coding: utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.

from typing import AsyncIterator

from openjiuwen.core.component.questioner_comp import QuestionerComponent as BaseQuestionerComponent
from openjiuwen.core.component.questioner_comp import QuestionerExecutable as BaseQuestionerExecutable
from openjiuwen.core.component.questioner_comp import QuestionerState, QuestionerEvent, ResponseType, QuestionerUtils
from openjiuwen.core.graph.executable import Input, Output, Executable
from openjiuwen.core.runtime.runtime import Runtime
from openjiuwen.core.context_engine.base import Context


class QuestionerExecutable(BaseQuestionerExecutable):
    SHARED_FIELDS_KEY = "questioner_shared_fields"

    async def stream(self, inputs: Input, runtime: Runtime, context: Context) -> AsyncIterator[Output]:
        result = await self.invoke(inputs, runtime, context)
        yield result

    async def invoke(self, inputs: Input, runtime: Runtime, context: Context) -> Output:
        state_from_runtime = self._load_state_from_runtime(runtime)
        if state_from_runtime.is_undergoing_interaction():
            current_state = state_from_runtime  # recover state from runtime
        else:
            current_state = QuestionerState()  # create new state
            # Recover shared fields from global state
            shared_fields = runtime.get_global_state(self.SHARED_FIELDS_KEY)
            if shared_fields and isinstance(shared_fields, dict):
                # Only take fields that are relevant to this component
                relevant_keys = {f.field_name for f in self._config.field_names}
                filtered_shared = {k: v for k, v in shared_fields.items() if k in relevant_keys}
                current_state.extracted_key_fields.update(filtered_shared)

        current_state = current_state.handle_event(QuestionerEvent.START_EVENT)

        # Check if we can skip execution (all fields collected and no specific question to ask)
        need_extract = (self._config.extract_fields_from_response and
                        len(self._config.field_names) > len(current_state.extracted_key_fields))
        is_set_question = isinstance(self._config.question_content, str) and len(self._config.question_content) > 0

        invoke_result = dict()
        if not need_extract and not is_set_question:
            # Already have all fields and no specific question to ask, skip execution
            questioner_input = QuestionerUtils.validate_inputs(inputs)
            current_state.user_response = questioner_input.query or ""
            current_state = current_state.handle_event(QuestionerEvent.END_EVENT)

            invoke_result = current_state.extracted_key_fields.copy()
            invoke_result['user_response'] = current_state.user_response
            invoke_result['question'] = current_state.question
        elif self._config.response_type == ResponseType.ReplyDirectly.value:
            invoke_result = await self._handle_questioner_direct_reply_safe(
                inputs, runtime, context, current_state
            )
            # handler might update state
            current_state = invoke_result.pop('_state', current_state)

        # Update shared fields to global state
        if current_state.extracted_key_fields:
            existing_shared = runtime.get_global_state(self.SHARED_FIELDS_KEY) or {}
            if not isinstance(existing_shared, dict):
                existing_shared = {}
            existing_shared.update(current_state.extracted_key_fields)
            runtime.update_global_state({self.SHARED_FIELDS_KEY: existing_shared})

        self._store_state_to_runtime(current_state, runtime)

        if current_state.is_undergoing_interaction():
            await runtime.interact(invoke_result.get("question", ""))

        return invoke_result


class QuestionerComponent(BaseQuestionerComponent):
    def to_executable(self) -> Executable:
        return QuestionerExecutable(self._questioner_config).state(QuestionerState())
