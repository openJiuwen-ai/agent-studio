# coding=utf-8
# Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""
This file is for Execute Engine runtime support.
"""

__all__ = ("executor", "USE_EXECUTE_ENGINE", "InvokableBase", "invokable_local")

import json
import os
import time
from abc import ABC
from collections.abc import Mapping
from os import environ
from threading import local
from typing import Callable, TypeVar, TYPE_CHECKING, Optional, no_type_check, final, Any

from jiuwen.common.configs.env_constants import RUNTIME_POD_IP_KEY
from jiuwen.common.exception.base import JiuWenBaseException
from jiuwen.common.exception.status_code import StatusCode
from jiuwen.common.log.base import logger
from jiuwen.executor_sdk.operator.impl.common.runtime_context_impl import (
    RuntimeContextImpl,
)
from jiuwen.executor_sdk.operator.impl.simple_execute_node import SimpleExecuteNode
from jiuwen.orchestration.callbacks.constants import TriggerEventName, OnInvokeEventType
from jiuwen.orchestration.callbacks.manager import CallbackHandlerManager
from jiuwen.orchestration.callbacks.models import AgentInfo, WorkflowInfo
from jiuwen.orchestration.callbacks.span import Span
from jiuwen.orchestration.flow.runtime_context import RuntimeContext
from jiuwen.orchestration.utils import Input, Output

if TYPE_CHECKING:
    from jiuwen.executor_sdk.operator.common.model.agent_ir import AgentIr

_MODE_DEFAULT_IN_ENV = "true"
invokable_local = local()
GLOBAL_SHARED_CACHE_KEY = "global_shared"
AGENT_INVO_CACHE_KEY = f"{GLOBAL_SHARED_CACHE_KEY}.agent_info"


def _get_runtime_state() -> bool:
    val = environ.get("TGF_ENABLE", _MODE_DEFAULT_IN_ENV).lower()
    if val not in ("true", "false"):
        raise JiuWenBaseException(
            error_code=StatusCode.ENV_VARIABLE_TGF_ENABLE_VALUE_ERROR.code,
            message=StatusCode.ENV_VARIABLE_TGF_ENABLE_VALUE_ERROR.errmsg,
        )
    return val == "true"


USE_EXECUTE_ENGINE = _get_runtime_state()
"""If JiuWen is running on Execute engine runtime, change this constant to `True`."""
_T = TypeVar("_T")

if TYPE_CHECKING:

    def executor(method: _T) -> _T:  # noqa
        """This method is only available with TGF runtime."""
else:

    @no_type_check
    class _Mux:
        def __init__(self, executor_method: Callable = None):
            self.__executor = executor_method

        def get(self) -> Optional[Callable]:
            """Get an executor."""
            return self.__executor

    @no_type_check
    def executor(method: Callable) -> _Mux:
        """
        This function is a decorator that wraps the provided method with a _Mux object.

        Parameters:
        method (Callable): The method to be wrapped.

        Returns:
        _Mux: A _Mux object that wraps the provided method.
        """
        return _Mux(method)


def _demux(cls):
    all_mux = [
        (name, mux) for name, mux in cls.__dict__.items() if isinstance(mux, _Mux)
    ]
    if USE_EXECUTE_ENGINE:
        for name, mux in all_mux:
            setattr(cls, name, mux.get())
    else:
        for name, _ in all_mux:
            delattr(cls, name)


if USE_EXECUTE_ENGINE:
    logger.info("Orchestration engine is running on the executor.")

    class _Barrier:
        """Used to mark the end of SimpleExecuteNode and its parents in the MRO chain."""

    class InvokableBase(SimpleExecuteNode, _Barrier, ABC):
        """Base class to support ExecuteEngine runtime."""

        def __init__(self, *args, **kwargs):
            # simulate a super call at the first line of `SimpleExecuteNode.__init__()`
            super(_Barrier, self).__init__(*args, **kwargs)
            super().__init__()

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            _demux(cls)

        def get_agent_info(
            self, runtime_context: RuntimeContextImpl
        ) -> Optional[AgentInfo]:
            """
            Get agent info.
            @param runtime_context: runtime context
            @return: AgentInfo
            """
            service = runtime_context.get_context()
            agent_info = service.get_session_ctx(AGENT_INVO_CACHE_KEY, is_remote=True)
            if not agent_info:
                return None
            if not isinstance(agent_info, dict):
                logger.error(
                    "Get agent info is not Map structure, real type is %s",
                    type(agent_info),
                )
                return None
            return AgentInfo(
                id=agent_info.get("agentId", ""),
                version=agent_info.get("agentVersion", ""),
            )

        def get_component_type(self):
            """
            Get component type.
            # Type has 3 scenes: (type, version) = test_ops.TestOpsForCallback:v0.0.1
            # 1. test_ops.TestOpsForCallback:v0.0.1
            # 2. test_ops.TestOpsForCallback:v0.0.1-
                    javaTestOperatorCallback-system_test_java_operator_callback_inner:v0.0.1
            # 3. jiuwen.planner.components.plan_modules.should_continue:ShouldContinue:v0.0.1
            """
            component = self.get_component_ir()
            if not component:
                return ""
            ori_type = self.get_component_ir().type
            if not ori_type or ":" not in ori_type:
                return ""
            index = ori_type.rindex(":")
            name_ele = ori_type[:index]
            return name_ele if name_ele else ""

        def get_component_version(self):
            """
            Get component version.
            """
            component = self.get_component_ir()
            if not component:
                return ""
            ori_type = self.get_component_ir().type
            if not ori_type or ":" not in ori_type:
                return ""
            index = ori_type.rindex(":")
            version_ele = ori_type[index + 1 :]
            version = version_ele.split("-")[0] if version_ele else ""
            return version if version else ""

        def get_component_exception_message(self) -> str:
            """
            Get component exception message.
            @return: format message.
            """
            return (
                f"componentId={self.get_component_ir().id if self.get_component_ir() else ''}, "
                f"componentType={self.get_component_type()}, "
                f"componentVersion={self.get_component_version()}, "
                f"schemaVersion={self.get_agent_ir().schemaVersion}, "
                f"ip={os.getenv(RUNTIME_POD_IP_KEY, '')}"
            )

        def get_workflow_info(
            self, runtime_context: RuntimeContextImpl
        ) -> Optional[WorkflowInfo]:
            """
            Get workflow info.
            @param runtime_context:
            @return: workflow info
            """
            agent_ir = self.get_agent_ir()
            if not agent_ir:
                return None
            agent_meta = agent_ir.metadata
            if isinstance(agent_meta, dict):
                workflow_info = agent_meta.get("workflowInfo")
                if isinstance(workflow_info, dict):
                    return WorkflowInfo(
                        id=workflow_info.get("id"),
                        version=workflow_info.get("version"),
                        name=workflow_info.get("name"),
                    )
            return WorkflowInfo(
                id=agent_ir.id,
                version=agent_ir.version,
                name=agent_ir.name,
            )

        def is_agent(self, runtime_context: RuntimeContextImpl) -> bool:
            """check ir is agent"""
            service = runtime_context.get_context()
            agent_info: dict = service.get_session_ctx(
                AGENT_INVO_CACHE_KEY, is_remote=True
            )
            return bool(agent_info)

        @final
        async def pre_process(self, node_input, runtime_context: RuntimeContextImpl):
            """
            Pre process method
            """
            node_input = self.pre_invoke(node_input, runtime_context)
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_PRE_INVOKE.value,
                action=self,
                inputs=node_input,
                runtime_context=runtime_context,
                supplement_info=self._construct_supplement_info(),
            )
            return node_input

        def pre_invoke(self, node_input):
            """
            Pre invoke.
            @param node_input: node input
            @param runtime_context: runtime context
            @return: modified node input
            """
            return node_input

        @final
        async def post_process(self, node_input, runtime_context: RuntimeContextImpl):
            """
            Post process method
            """
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_POST_INVOKE.value,
                action=self,
                outputs=node_input,
                runtime_context=runtime_context,
                supplement_info=self._construct_supplement_info(),
            )
            return self.post_invoke(node_input, runtime_context)

        def post_invoke(self, node_input):
            """
            @param node_input: node input
            @param runtime_context: runtime context
            @return: modifed node input
            """
            return node_input

        async def record_child_debug_info(
            self, inputs: dict[str, Any], runtime_context: RuntimeContextImpl
        ) -> None:
            """
            Record child debug info for subclass.
            """
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_INVOKE.value,
                action=self,
                data=inputs,
                runtime_context=runtime_context,
                type=OnInvokeEventType.RECORD_CHILD_DEBUG_INFO.value,
                supplement_info=self._construct_supplement_info(),
            )

        async def record_debug_info(
            self, inputs: dict[str, Any], runtime_context: RuntimeContextImpl
        ) -> None:
            """
            Record debug info.
            """
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_INVOKE.value,
                action=self,
                data=inputs,
                runtime_context=runtime_context,
                supplement_info=self._construct_supplement_info(),
            )

        def set_global_config(
            self, global_key: str, value: Any, runtime_context: RuntimeContextImpl
        ) -> None:
            """Set something to context"""
            runtime_context.get_context().put_session_ctx(global_key, value)

        def get_global_config_item(
            self, global_key: str, item_key: str, runtime_context: RuntimeContextImpl
        ) -> Any:
            """Get an item from a dict in context"""
            service = runtime_context.get_context()
            anything = service.get_session_ctx(global_key)
            if anything is None:
                return anything
            if isinstance(anything, dict):
                return anything.get(item_key)
            raise JiuWenBaseException(
                StatusCode.COMPONENT_CONTEXT_TYPE_ERROR.code,
                StatusCode.COMPONENT_CONTEXT_TYPE_ERROR.errmsg,
            )

        def set_global_config_item(
            self,
            global_key: str,
            item_key: str,
            value: Any,
            runtime_context: RuntimeContextImpl,
        ) -> None:
            """Set an item to a dict in context"""
            service = runtime_context.get_context()
            anything = service.get_session_ctx(global_key)
            if anything is None:
                service.put_session_ctx(global_key, {item_key: value})
            elif isinstance(anything, dict):
                anything[item_key] = value
                service.put_session_ctx(global_key, anything)
            else:
                raise JiuWenBaseException(
                    StatusCode.COMPONENT_CONTEXT_TYPE_ERROR.code,
                    StatusCode.COMPONENT_CONTEXT_TYPE_ERROR.errmsg,
                )

        def __get_manager_envs(self) -> Mapping[str, str]:
            ir: "AgentIr" = self.get_agent_ir()
            if (ir is None) or (ir.system_configs is None):
                logger.warning(
                    "This Invokable is set to run on Execute Engine, but cannot read its AgentIR"
                    " information. Using system environ instead."
                )
                return environ
            # ISSUE#194: replace conf operation from dict-type to dataclass-type (wait for TGF Runtime fix)
            envs = [conf for conf in ir.system_configs if conf.get("name") == "envs"]
            if not envs:
                logger.warning(
                    "This Invokable is set to run on Execute Engine, but cannot read environ info"
                    " from its AgentIR. Using system environ instead."
                )
            try:
                return json.loads(envs[0].get("value")) if envs else environ
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}", simple_log="JSON decode error")
                raise ValueError("JSON decode error") from e
            except TypeError as e:
                logger.error(f"Type error: {e}", simple_log="Type error")
                raise ValueError("Type error") from e
            except Exception as e:
                logger.error(f"Unexpected error: {e}", simple_log="Unexpected error")
                raise ValueError("Unexpected error") from e

        def _construct_supplement_info(self):
            return dict(current_time=int(time.time() * 1000))
else:
    logger.info("Orchestration engine is running without executor runtime.")

    class InvokableBase(ABC):
        """Base class to run orchestration engine without ExecuteEngine runtime."""

        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__(**kwargs)
            _demux(cls)

        def init(self, configs: dict, **kwargs):
            """User defined component init method."""
            return

        def pre_invoke(self, inputs: Input, runtime_context: RuntimeContext):
            """
            user defined invoke pre-function
            Args:
                inputs: input parameters
                runtime_context:  context information

            Returns:

            """
            return

        @final
        async def pre_process(
            self,
            node_input,
            runtime_context: RuntimeContext,
            component_metadata,
            span_instance: Span,
        ):
            """pre_process"""
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_PRE_INVOKE.value,
                inputs=node_input,
                component_metadata=component_metadata,
                span_instance=span_instance,
                runtime_context=runtime_context,
            )
            return self.pre_invoke(node_input, runtime_context)

        def post_invoke(self, outputs: Output, runtime_context: RuntimeContext):
            """
            user defined invoke post-function
            Args:
                outputs:  output parameters
                runtime_context: context information

            Returns:

            """
            pass

        @final
        async def post_process(
            self,
            node_output,
            node_input,
            runtime_context: RuntimeContext,
            component_metadata,
            span_instance: Span,
        ):
            """pre_process"""
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_POST_INVOKE.value,
                outputs=node_output,
                inputs=node_input,
                component_metadata=component_metadata,
                span_instance=span_instance,
                runtime_context=runtime_context,
            )
            try:
                self.post_invoke(node_output, runtime_context)
            except JiuWenBaseException as e:
                raise JiuWenBaseException(
                    120001, f"错误信息：{type(e).__name__}"
                ) from e

        @final
        async def post_interact_process(
            self, runtime_context: RuntimeContext, component_metadata
        ):
            """post_interact_process"""
            await CallbackHandlerManager().trigger_event(
                event_name=TriggerEventName.ON_POST_INTERACT_INVOKE.value,
                component_metadata=component_metadata,
                runtime_context=runtime_context,
            )

        def get_state(self):
            """
            Get state of invokable.
            """
            return

        def load_state(self, state):
            """
            Load state of invokable.
            """
            pass
