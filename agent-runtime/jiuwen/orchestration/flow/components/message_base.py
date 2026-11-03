#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from abc import ABC

from jiuwen.common.log.base import logger
from jiuwen.orchestration.flow.chat_manager import ChatManager
from jiuwen.orchestration.flow.components.interactive_base import InteractiveComponent
from jiuwen.orchestration.flow.components.util import (
    SPLIT_DELIMITER,
    get_data_of_streaming_with_metadata,
    pass_streaming_data_without_finish,
    process_output_of_interaction_component,
)
from jiuwen.orchestration.flow.enum import StreamDataMsg
from jiuwen.orchestration.flow.model.workflow_data_class import (
    WorkflowMetadata,
    WorkflowStreamingData,
)
from jiuwen.orchestration.flow.stream.base import StreamData, StreamCode
from jiuwen.prompt import Prompt, Template

STRUCT_OUTPUT_TEMPLATE = "struct_output_template"
ENABLE_STRUCT_MESSAGE = "isStructMessage"


class MessageComponentBase(ABC):
    """Base class for message components.

    The message dispatch in the workflow is mainly divided into two types:
        1. Direct message generation via a generator like message, card and end node, which is sent out through
           `pass_streaming_data_without_finish`.
        2. Intermediate result output from interaction nodes like questioner, QA node, via
           `process_output_of_interaction_component`.

    This class provides implementations for three primary message dispatch functions:
        1. format_message_output:
           Sends out messages directly specifically for workflow message and card node.
        2. format_workflow_end_output:
           Handles message sending specifically for workflow end node, including
           sending additional final messages.
        3. await_send_format_output:
           Sends interactive messages during the intermediate running process of nodes.
    """

    async def _format_output_answer(self, origin_output: str, struct_answer_item: dict):
        """format struct output answer
        Args:
            origin_output: origin output answer.
            struct_answer_item: a dict item which contains truct_output_template and variables.
        """
        template_answer = struct_answer_item.get(STRUCT_OUTPUT_TEMPLATE, "")
        variables = struct_answer_item.get("variables", {})
        if not template_answer:
            return ""

        # origin_output replace with default placeholder {{_NODE_OUTPUT}}
        variables["_NODE_OUTPUT"] = (
            origin_output.get("answer", "")
            if isinstance(origin_output, dict)
            else origin_output
        )
        return await Prompt(
            template=Template(name="struct_answer_template", content=template_answer)
        ).ainvoke(variables)

    @staticmethod
    def _split_answer_and_think(answer: str) -> tuple[str, str]:
        final_tmp = answer.split(SPLIT_DELIMITER)
        parsed_answer = final_tmp[0]
        think = final_tmp[1] if len(final_tmp) > 1 else ""
        return parsed_answer, think

    @staticmethod
    def _get_message_end_generator(
        answer: str,
        struct_answer: str,
        metadata: WorkflowMetadata,
        execution_id: str,
        outputs: dict = None,
        output_mode: str = None,
        enable_history: bool = True,
    ):
        """Construct a generator that yields only MESSAGE_END to indicate node execution completion."""
        answer, think = MessageComponentBase._split_answer_and_think(answer)
        data = get_data_of_streaming_with_metadata(
            answer=answer,
            metadata=metadata,
            outputs=outputs,
            think=think,
            output_mode=output_mode,
            struct_answer=struct_answer,
        )
        if not enable_history:
            data["enable_history"] = False
        yield StreamData(
            code=StreamCode.MESSAGE_END.value,
            msg=StreamDataMsg.MESSAGE_END.value,
            data=data,
            execution_id=execution_id,
            is_struct_message=bool(struct_answer),
        )

    async def format_message_output(
        self,
        origin_output: str,
        struct_answer_item: dict,
        metadata: WorkflowMetadata,
        stream_data: WorkflowStreamingData,
        outputs: dict = None,
        output_mode: str = None,
        enable_history: bool = True,
    ):
        """format workflow message node output directly"""
        struct_answer = (
            await self._format_output_answer(origin_output, struct_answer_item)
            if struct_answer_item
            else ""
        )
        end_generator = self._get_message_end_generator(
            answer=origin_output,
            struct_answer=struct_answer,
            metadata=metadata,
            execution_id=stream_data.execution_id,
            outputs=outputs,
            output_mode=output_mode,
            enable_history=enable_history,
        )
        await pass_streaming_data_without_finish(
            generator=end_generator,
            workflow_streaming_data=stream_data,
            metadata=metadata,
        )

    async def format_workflow_end_output(
        self,
        origin_output: str,
        struct_answer_item: dict,
        metadata: WorkflowMetadata,
        stream_data: WorkflowStreamingData,
        outputs: dict = None,
        output_mode: str = None,
    ):
        """format workflow end node output"""

        struct_answer = (
            self._format_output_answer(origin_output, struct_answer_item)
            if struct_answer_item
            else ""
        )

        def workflow_end_generator():
            parsed_answer, _ = self._split_answer_and_think(origin_output)
            yield from self._get_message_end_generator(
                answer=origin_output,
                struct_answer=struct_answer,
                metadata=metadata,
                execution_id=stream_data.execution_id,
                outputs=outputs,
                output_mode=output_mode,
            )
            data = get_data_of_streaming_with_metadata(
                answer=parsed_answer, metadata=metadata, output_mode=output_mode
            )
            yield StreamData(
                code=StreamCode.WORKFLOW_END.value,
                msg=StreamDataMsg.FINISH.value if parsed_answer else "",
                data=data,
                execution_id=stream_data.execution_id,
            )
            yield StreamData(
                code=StreamCode.FINISH.value,
                msg=StreamDataMsg.FINISH.value,
                data=data,
                execution_id=stream_data.execution_id,
            )

        await pass_streaming_data_without_finish(
            generator=workflow_end_generator(),
            workflow_streaming_data=stream_data,
            metadata=metadata,
        )

    async def await_send_format_output(
        self,
        origin_output: str,
        struct_answer_item: dict,
        metadata: WorkflowMetadata,
        stream_data: WorkflowStreamingData,
        chat_manager: ChatManager,
    ):
        """format workflow interaction message output"""
        struct_answer = await self._format_output_answer(origin_output, struct_answer_item)
        # check if interaction nodes should be interrupted
        if isinstance(self, InteractiveComponent):
            try:
                metadata.should_interrupt = self.should_interrupt()
            except Exception as e:
                logger.warning(f"Failed to call should_interrupt(): {e}")
        await process_output_of_interaction_component(
            stream_related_info=stream_data,
            origin_output=origin_output,
            chat_manager=chat_manager,
            metadata=metadata,
            struct_answer=struct_answer,
        )
