#  Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
import json
import threading
from abc import ABC
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from typing import Union, Any, Type

from jiuwen.common.exception import JiuWenException
from jiuwen.common.llm_service.base import ModelFactory
from jiuwen.common.llm_service.language_model.base import LanguageModelInput
from jiuwen.common.llm_service.model_util import ModelUtil
from jiuwen.common.log.base import logger
from jiuwen.common.store.redis import get_redis_instance, RedisUtils
from jiuwen.orchestration.callbacks.base import BaseCallbackHandler
from jiuwen.orchestration.callbacks.constants import TriggerEventName
from jiuwen.orchestration.flow.bpmn_workflow import convert_to_old_type
from jiuwen.orchestration.flow.constant import (
    WORKFLOW_EXECUTE_DEBUG_INFO,
    WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME,
    WORKFLOW_API_CONFIGS,
    GLOBAL_CONFIG,
    WORKFLOW_CHAT_HISTORY,
    QuestionerKeyword,
)
from jiuwen.orchestration.flow.enum import NodeType
from jiuwen.orchestration.utils import Output, Input
from jiuwen.planner.planning_modules.base import ChatContent, PromptPlanningModule
from jiuwen.prompt import TemplateManager
from jiuwen.prompt.selector.base import MemoryVariableExtractor
from utils.constants import (
    RUNTIME_CONTEXT,
    DEFAULT_MODEL_CONTEXT,
    LONG_TREM_MEMORY_VALUES,
    IR_LONG_TREM_MEMORY_ENABLE,
    REDIS_LTM_VALS_PREFIX,
    DEFAULT_PERMANENT_STORE_TIME,
    REDIS_LTM_CHAT_PREFIX,
    DEFAULT_CONVERSATION_STORE_TIME,
)

from .cache.factory import CacheFactory
from .config import long_memory_config
from .parser.base_parser import BaseParser
from .storage.vector_db_factory import VectorDbFactory
from .utils import handle_exceptions, get_runtime_memory_key_ids

LOCK_TIME_OUT = 60
redis_client: RedisUtils = get_redis_instance()


@handle_exceptions
def persist_conversion_cache(workflow_id, user_id, execution_id):
    """
    把本轮在当前pod内的对话历史持久化到redis中
    """
    record = {}
    cache_key = f"{workflow_id}:{execution_id}"
    for i in CacheFactory.get_chat_cache().get_all(cache_key):
        if "relate_workflows" not in i:
            continue
        for j in i.pop("relate_workflows", []):
            record.setdefault(j, []).append(json.dumps(i, ensure_ascii=False))

    for k, v in record.items():
        store_key = f"{REDIS_LTM_CHAT_PREFIX}:{k}:{user_id}"
        redis_client.list_append(store_key, *v, ttl=DEFAULT_CONVERSATION_STORE_TIME)
        current_length = redis_client.list_length(store_key)
        if current_length > long_memory_config.max_chat_length:
            redis_client.ltrim(
                store_key, current_length - long_memory_config.max_chat_length
            )
    CacheFactory.get_chat_cache().delete(cache_key)


class Memory4CallbackHandler(BaseCallbackHandler, ABC):
    """
    长期记忆处理类
    复用Callback机制获取数据，但是由于存在模型解析步骤，所以得放到异步线程里处理
    """

    _parser: dict[str, Type[BaseParser]] = {}
    _executor = ThreadPoolExecutor(max_workers=20)
    _locks = defaultdict(threading.Lock)

    @classmethod
    def register(cls, parser_class):
        cls._parser[parser_class.get_type()] = parser_class

    @classmethod
    def get_parser(cls):
        return cls._parser

    @classmethod
    def exec_memory(cls, func, func_type, **kwargs: Any):
        if (
            not kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(IR_LONG_TREM_MEMORY_ENABLE)
        ):
            return
        node_type = kwargs.get("component_metadata", {}).get("component_type")
        if not (node_type and node_type in Memory4CallbackHandler.get_parser()):
            return
        conversations = func(node_type)
        conversation_id, workflow_id, _, execution_id = get_runtime_memory_key_ids(
            **kwargs
        )

        workflow_ids = CacheFactory.get_call_workflow_cache().get_all(execution_id) or [
            workflow_id
        ]
        conversations = [
            i
            | {
                "currentTime": int(datetime.now(timezone.utc).timestamp() * 1000),
                "relate_workflows": workflow_ids,
            }
            for i in conversations
        ]
        if conversations and conversation_id and workflow_id and execution_id:
            [
                CacheFactory.get_chat_cache().save(f"{workflow_id}:{execution_id}", i)
                for i in conversations
            ]

        if (
            convert_to_old_type.get(NodeType.END.value)
            == kwargs.get("component_metadata", {}).get("component_type")
            and func_type == TriggerEventName.ON_POST_INVOKE.value
        ):
            # 执行到结束节点，保存当前全局变量
            Memory4CallbackHandler._finish_invoke(**kwargs)

    async def on_pre_invoke(self, inputs: Input, *args: Any, **kwargs: Any) -> Any:
        Memory4CallbackHandler.exec_memory(
            lambda t: Memory4CallbackHandler._parser.get(t).pre_parse(
                inputs, *args, **kwargs
            ),
            TriggerEventName.ON_PRE_INVOKE.value,
            **kwargs,
        )

    async def on_post_invoke(self, outputs: Output, *args: Any, **kwargs: Any) -> Any:
        Memory4CallbackHandler.exec_memory(
            lambda t: Memory4CallbackHandler._parser.get(t).post_parse(
                outputs, *args, **kwargs
            ),
            TriggerEventName.ON_POST_INVOKE.value,
            **kwargs,
        )

    async def on_invoke(
        self, data: Union[JiuWenException, dict], *args: Any, **kwargs: Any
    ) -> Any:
        if isinstance(data, JiuWenException):
            Memory4CallbackHandler._finish_invoke(**kwargs)
        else:
            Memory4CallbackHandler.exec_memory(
                lambda t: Memory4CallbackHandler._parser.get(t).invoke_parse(
                    data, *args, **kwargs
                ),
                TriggerEventName.ON_INVOKE.value,
                **kwargs,
            )

    def on_post_interact_invoke(self, **kwargs: Any) -> Any:
        if (
            not kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(IR_LONG_TREM_MEMORY_ENABLE)
        ):
            return
        conversation_id, workflow_id, user_id, execution_id = (
            get_runtime_memory_key_ids(**kwargs)
        )
        if not (workflow_id and user_id and execution_id):
            return
        Memory4CallbackHandler._executor.submit(
            Memory4CallbackHandler.handle_interact,
            conversation_id,
            workflow_id,
            user_id,
            execution_id,
        )

    @classmethod
    @handle_exceptions
    def handle_interact(cls, conversation_id, workflow_id, user_id, execution_id):
        persist_conversion_cache(workflow_id, user_id, execution_id)
        cls.free_resource(conversation_id, execution_id, workflow_id)

    @classmethod
    def free_resource(cls, conversation_id, execution_id, workflow_id):
        record_workflow_ids = CacheFactory.get_call_workflow_cache().get_all(
            execution_id
        )
        # 如果当前没有记录workflow调用栈或者当前就是主工作流，则释放内存
        if not record_workflow_ids or workflow_id == record_workflow_ids[0]:
            CacheFactory.get_call_workflow_cache().delete(execution_id)
            cls._locks.pop(conversation_id, None)

    @classmethod
    def _finish_invoke(cls, **kwargs: Any):
        if (
            not kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(IR_LONG_TREM_MEMORY_ENABLE)
        ):
            return
        model_config = (
            kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(DEFAULT_MODEL_CONTEXT)
        )
        long_memory_vals = (
            kwargs.get(RUNTIME_CONTEXT, {})
            .get(GLOBAL_CONFIG, {})
            .get(LONG_TREM_MEMORY_VALUES)
        )
        context = kwargs.get(RUNTIME_CONTEXT, {})
        new_context = {
            WORKFLOW_EXECUTE_DEBUG_INFO: context.get(WORKFLOW_EXECUTE_DEBUG_INFO),
            WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME: context.get(
                WORKFLOW_EXECUTE_REQUESTS_HEADERS_NAME
            ),
            WORKFLOW_API_CONFIGS: context.get(WORKFLOW_API_CONFIGS),
            WORKFLOW_CHAT_HISTORY: context.get(WORKFLOW_CHAT_HISTORY),
        }

        Memory4CallbackHandler._executor.submit(
            Memory4CallbackHandler._collect_memory,
            model_config=deepcopy(model_config),
            long_memory_vals=deepcopy(long_memory_vals),
            runtime_context=deepcopy(new_context),
        )

    @classmethod
    @handle_exceptions
    def _collect_memory(cls, **kwargs):
        conversation_id, workflow_id, user_id, execution_id = (
            get_runtime_memory_key_ids(**kwargs)
        )
        if not (conversation_id and workflow_id and user_id):
            logger.error(f"invalid params {conversation_id} {workflow_id} {user_id}")
            return

        lock = cls._locks[conversation_id]
        if lock.acquire(timeout=LOCK_TIME_OUT):
            try:
                cls._collect_memory_vals(execution_id, user_id, workflow_id, **kwargs)
                cls._collect_memory_summary(user_id, workflow_id, **kwargs)
            finally:
                lock.release()
        cls.free_resource(conversation_id, execution_id, workflow_id)

    @classmethod
    def _collect_memory_vals(cls, execution_id, user_id, workflow_id, **kwargs):
        history_store_key = f"{REDIS_LTM_CHAT_PREFIX}:{workflow_id}:{user_id}"
        # 本轮引擎内执行新生成的对话历史
        current_runtime_chat = [
            x
            for x in CacheFactory.get_chat_cache().get_all(
                f"{workflow_id}:{execution_id}"
            )
            if workflow_id in x.get("relate_workflows", [])
        ]
        history_chat = [json.loads(x) for x in redis_client.list_get(history_store_key)]
        history_chat.extend(current_runtime_chat if current_runtime_chat else [])
        Memory4CallbackHandler.analysis_global_vals(
            history_chat, workflow_id, user_id, **kwargs
        )
        persist_conversion_cache(workflow_id, user_id, execution_id)

    @classmethod
    def _collect_memory_summary(cls, user_id, workflow_id, **kwargs):
        raw_history = redis_client.list_get(
            f"{REDIS_LTM_CHAT_PREFIX}:{workflow_id}:{user_id}",
            -long_memory_config.max_summary_period,
        )
        chat_history = [json.loads(x) for x in raw_history]
        dig_history = [f"{x.get('role')}:{x.get('content')}" for x in chat_history]
        summary = cls._summary_chat({"dig_history": dig_history}, **kwargs)
        logger.info(f"store chat data, current id {workflow_id}, summary {summary}")
        VectorDbFactory.get_storage().save(
            [summary], category=user_id, tags=[workflow_id]
        )

        summary = VectorDbFactory.get_storage().pop_old_data(user_id, workflow_id)
        if summary:
            zip_summary = cls._summary_chat({"relate_summary": summary}, **kwargs)
            VectorDbFactory.get_storage().save(
                [zip_summary], category=user_id, tags=[workflow_id]
            )

    @classmethod
    def _summary_chat(cls, keywords, **kwargs):
        model_config = kwargs.get("model_config")
        model = ModelFactory().get_model(
            runtime_context=kwargs.get(RUNTIME_CONTEXT, {}),
            model_type=model_config.get("modelType"),
            model_name=model_config.get("modelName"),
        )
        prompt = TemplateManager().get(
            name="history_summary",
            filters={"model_name": model_config.get("modelName")},
        )
        prompt_template = [
            ChatContent(
                role=p.get(QuestionerKeyword.ROLE),
                content=p.get(QuestionerKeyword.CONTENT),
            )
            for p in prompt.content
        ]
        prompt = PromptPlanningModule().format(
            keywords=keywords, prompt_template=prompt_template
        )
        llm_inputs = LanguageModelInput(
            messages=ModelUtil.switch_message(prompt), tools=[]
        )
        return cls.invoke_llm(model, llm_inputs)

    @classmethod
    # 如果存在记忆变量且解析出了用户输入，则使用本轮的对话尝试解析变量，如果能解释成功就保存
    def analysis_global_vals(cls, history, workflow_id, user_id, **kwargs):
        model_config = kwargs.get("model_config")
        long_memory_vals = kwargs.get("long_memory_vals")
        context = kwargs.get("runtime_context")
        if not (model_config and long_memory_vals and context):
            return

        extractor = MemoryVariableExtractor(
            conversation_history=history,
            summaries_params=[
                {
                    "name": x.get("id"),
                    "description": x.get("description"),
                    "default_value": x.get("default_value"),
                }
                for x in long_memory_vals
            ],
            model_info={
                "model": model_config.get("modelName"),
                "model_source": model_config.get("modelType"),
                "temperature": 0.2,
                "top_p": 0.5,
                "runtime_context": context,
            },
            validation="none",
            params_value=[],
        )
        analysis_value = extractor.run().get("data", {})
        if analysis_value and workflow_id and user_id:
            exist_values_data = cls.load_exist_data(workflow_id, user_id)
            store_key = f"{REDIS_LTM_VALS_PREFIX}:{workflow_id}:{user_id}"
            redis_client.set(
                store_key,
                json.dumps(exist_values_data | analysis_value, ensure_ascii=False),
                DEFAULT_PERMANENT_STORE_TIME,
            )

    @classmethod
    def load_exist_data(cls, workflow_id, user_id):
        store_key = f"{REDIS_LTM_VALS_PREFIX}:{workflow_id}:{user_id}"
        data = redis_client.get(store_key)
        return json.loads(data) if data else {}

    @classmethod
    def invoke_llm(cls, model, inputs):
        try:
            return model.invoke(inputs).content
        except Exception as e:
            logger.info("invoke llm error", e)
            return ""
