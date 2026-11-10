#!/usr/bin/env python
# -*- coding: UTF-8 -*-



import uuid
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional

from agent_runtime.extension.workflow_node.flow_knowledge_retrieval import (
    FlowKnowledgeRetrieval,
)
from agent_runtime.extension.workflow_node.kb_adapter.base import KBSearchResult
from agent_runtime.extension.workflow_node.kb_adapter.factory import KBAdapterFactory
from jiuwen.plugin.common import constant
from jiuwen.plugin.models.function import Function
from jiuwen.plugin.models.param import Param
from openjiuwen.core.common.logging import workflow_logger
from openjiuwen.core.foundation.tool.base import Input, Output, Tool, ToolCard

try:
    from openjiuwen.core.session.tracer import TracerAgentUtils as _TracerAgentUtils
except ImportError:
    # 老版本 core 没有 retriever 事件助手：控制器路径检索自动降级为无 retrieval span
    _TracerAgentUtils = None

_RETRIEVAL_NAME = "retrieval"
_QUERY = "query"
_KNOWLEDGE_BASES = "knowledge_bases"
_TOP_K = "top_k"
_RECALL_THRESHOLD = "recall_threshold"
_FAQ_THRESHOLD = "faq_threshold"
_SEARCH_MODE = "search_mode"
_NEED_EXTRAS_FAQ_SEARCH = "need_extras_faq_search"
_RETRIEVE_IMAGE = "retrieve_image"
_SHOW_SOURCE = "show_source"


def is_knowledge_retrieval_ir(ir_data: dict) -> bool:
    """Return True when the plugin IR represents agent knowledge retrieval."""
    if not isinstance(ir_data, dict):
        return False
    if ir_data.get("name") != _RETRIEVAL_NAME:
        return False
    arguments = ir_data.get("arguments", [])
    matched = any(arg.get("name") == _KNOWLEDGE_BASES for arg in arguments)
    return matched


def _resolve_retrieval_params(ir_data: dict) -> Dict[str, Any]:
    """Extract connection_id / kb_ids / retrieval_config / tag_overrides from IR."""
    knowledge_bases = _get_argument_default(ir_data, _KNOWLEDGE_BASES, [])
    knowledge_config = ir_data.get("knowledgeConfig", {}) or {}
    retrieval_config = _build_retrieval_config(ir_data, knowledge_config)
    connection_id = str(knowledge_config.get("connectionId") or _resolve_connection_id(knowledge_bases))
    knowledge_base_ids = [
        str(kb_id)
        for kb_id in (knowledge_config.get("knowledgeBaseIds") or [])
        if kb_id
    ] or [
        str(kb.get("id"))
        for kb in knowledge_bases
        if isinstance(kb, dict) and kb.get("id")
    ]
    tag_overrides = {
        str(kb.get("id")): kb.get("tags", [])
        for kb in knowledge_bases
        if isinstance(kb, dict) and kb.get("id")
    }
    return {
        "connection_id": connection_id,
        "knowledge_base_ids": knowledge_base_ids,
        "retrieval_config": retrieval_config,
        "tag_overrides": tag_overrides,
    }


# --------------------------------------------------------------------------
# Retrieval trace events（agent 侧 retriever span，镜像 core APIEmbedding 范式）
# --------------------------------------------------------------------------


def _resolve_retrieval_tracer():
    """Session tracer for retrieval trace events, or None.

    _run_retrieval 无组件壳（workflow 的 jiuwen.knowledgeRetrieval 节点有自己的
    节点壳，不走这里）：agent 工具 / 插件函数路径下，会话上下文存在且 OTel
    handler 可用时才发 retriever 事件；无会话或 handler 未注册时静默跳过。
    """
    try:
        # 惰性导入：旧 core 缺该符号时按无会话降级，模块导入不得因此失败
        from openjiuwen.core.session import get_current_session

        session = get_current_session()
    except Exception:  # noqa: BLE001 - tracing must never break retrieval
        return None
    if session is None:
        return None
    try:
        tracer = session.tracer()
    except Exception:  # noqa: BLE001
        return None
    try:
        handler_valid = tracer is not None and tracer.agent_handler_valid()
    except Exception:  # noqa: BLE001 - tracing must never break retrieval
        return None
    return tracer if handler_valid else None


async def _trace_retrieval_event(tracer, event_name: str, span, **payload) -> bool:
    """Fire one tracer event; failures never propagate into the business flow.

    返回事件是否送达 handler（start 事件据此决定 span 生死，避免半开 span）。
    """
    try:
        # 惰性导入：旧 core 缺该符号时按事件失败降级，模块导入不得因此失败
        from openjiuwen.core.session.tracer.handler import TracerHandlerName

        await tracer.trigger(TracerHandlerName.TRACE_AGENT.value, event_name, span=span, **payload)
    except Exception as e:  # noqa: BLE001
        workflow_logger.warning("retrieval trace event '%s' failed: %s", event_name, e)
        return False
    return True


def _unregister_retrieval_span(tracer, span):
    """仅注销登记（_drop_retrieval_span 的内部原语）。

    注销 create_agent_span 留在 span manager 的登记（避免永不 start/end
    的悬空记录，last_span 也会被它污染）。start 失败路径不得只调本函数：
    core trigger 逐 handler 裸 await 不隔离异常，start「未送达」可能是
    「部分送达」——先成功的 handler 已开启 otel span，必须再走
    _drop_retrieval_span 收掉（drop_agent_span 对未开启 invoke_id 结构性
    幂等：内部 pop 缺失即返回，不发任何虚假事件）。
    """
    try:
        tracer.tracer_agent_span_manager.pop_span(span.invoke_id)
    except Exception:  # noqa: BLE001 - 注销失败不影响降级路径
        pass


def _drop_retrieval_span(tracer, span):
    """注销登记 + 尽力结束已开启的 otel span（start/end/error 失败路径通用）。

    start 部分送达（先成功的 handler 已开 otel span、后继 handler 抛错）与
    end/error 未送达同用本函数收口：若已注册 handler 暴露 drop_agent_span
    （core !3570/!3571 起），显式结束它（OK 状态 + drop 标记事件）——对
    未开启的 invoke_id 幂等 no-op，无虚假记录；否则半开 span 永久滞留。
    旧 core 无该接口时退化为仅注销登记。全部尽力而为，不得影响降级路径。
    """
    _unregister_retrieval_span(tracer, span)
    try:
        # 公共注册表遍历（TracerHandlerRegistry 为 core 公共 API）；
        # 逐 handler 探测，未提供 drop_agent_span 的实现直接跳过；
        # 逐 handler 隔离异常——一个 handler 清理失败不拖累其余
        # （jdfff 11-05：原单 try 会让首个抛错的 handler 中断整轮清理）
        from openjiuwen.core.session.tracer.tracer import TracerHandlerRegistry

        for handler in TracerHandlerRegistry.get_agent_handlers().values():
            try:
                drop = getattr(handler, "drop_agent_span", None)
                if callable(drop):
                    drop(span.invoke_id)
            except Exception:  # noqa: BLE001 - 单 handler 失败不拖累其余
                pass
    except Exception:  # noqa: BLE001 - 结束失败不影响降级路径
        pass


def _drop_retrieval_span_by_session(session, span):
    """kwargs 会话版尽力收尾：供 invoke 外壳在事件 await 被取消/未送达时使用。

    真实任务取消（Task.cancel / asyncio.timeout）下，except 块内的 await 会再次
    收到 CancelledError，无法再依赖任何异步收尾——只能同步地注销登记并探测
    drop_agent_span 结束半开 otel span。全部尽力而为，不得影响上抛路径。
    """
    try:
        tracer = session.tracer()
    except Exception:  # noqa: BLE001
        return
    if tracer is None:
        return
    _drop_retrieval_span(tracer, span)


def _resolve_session_tracer(session):
    """kwargs 会话版 tracer 解析（口径同 _resolve_retrieval_tracer）。

    invoke 外壳手里是 kwargs 注入的 session 而非 ambient contextvar：tracer
    取自该会话（同 _drop_retrieval_span_by_session 的取法），handler 不可用
    时同样按无追踪降级。
    """
    if session is None:
        return None
    try:
        tracer = session.tracer()
    except Exception:  # noqa: BLE001 - tracing must never break retrieval
        return None
    if tracer is None:
        return None
    try:
        handler_valid = tracer.agent_handler_valid()
    except Exception:  # noqa: BLE001 - tracing must never break retrieval
        return None
    return tracer if handler_valid else None


def _retriever_invoke_type():
    """core InvokeType.RETRIEVER 的惰性取值；旧 core 缺符号时返回 None。"""
    try:
        from openjiuwen.core.session.tracer.data import InvokeType

        return InvokeType.RETRIEVER.value
    except Exception:  # noqa: BLE001 - 旧 core 缺符号时省略 type 字段
        return None


async def _trace_retrieval_start(tracer, query: str, knowledge_base_ids, retrieval_config):
    """Open the retriever trace span; returns the tracer span handle.

    start 事件失败（trigger 抛错被吞 / 取消穿透）时返回 None：调用侧据
    None 跳过后续 end/error 事件，避免产生只有 end 没有 start 的半开
    span；同时注销登记并尽力 drop——core trigger 逐 handler 裸 await
    不隔离异常，失败可能是「部分送达」（先成功的 handler 已开启 otel
    span），只注销登记会漏半开 span；drop 对未开启 invoke_id 幂等。
    """
    span = tracer.tracer_agent_span_manager.create_agent_span()
    inputs: Dict[str, Any] = {"query": query}
    top_k = retrieval_config.get("topK") if isinstance(retrieval_config, dict) else None
    if top_k is not None:
        inputs["top_k"] = top_k
    if knowledge_base_ids:
        inputs["knowledge_base_ids"] = list(knowledge_base_ids)
    instance_info: Dict[str, Any] = {"class_name": "knowledge_retrieval_tool"}
    retriever_type = _retriever_invoke_type()
    if retriever_type is not None:
        # 与 TracerAgentUtils.trace_retriever_start 同口径补 RETRIEVER 类型
        # 标识：kwargs 兜底路径复用本函数后，两条路径的 instance_info 形态一致
        instance_info["type"] = retriever_type
    try:
        started = await _trace_retrieval_event(
            tracer,
            "on_retriever_start",
            span,
            inputs=inputs,
            instance_info=instance_info,
        )
    except BaseException:  # noqa: BLE001 - 取消等 BaseException 同样要收尾登记
        # CancelledError 不被 _trace_retrieval_event 的 except Exception 吞：
        # 注销登记 + drop 部分送达时已开的 otel span（同步原语、全兜底、必不
        # 抛），取消原样上抛
        _drop_retrieval_span(tracer, span)
        raise
    if not started:
        # start 未送达/部分送达：注销登记；已开的 otel span 由 drop 收口
        # （未开启的 handler 端幂等 no-op）
        _drop_retrieval_span(tracer, span)
        return None
    return span


async def _run_retrieval(
    query: str,
    connection_id: str,
    knowledge_base_ids: List[str],
    retrieval_config: Dict[str, Any],
    tag_overrides: Dict[str, Any],
) -> dict:
    if not query or not str(query).strip():
        return _format_output([])

    component = FlowKnowledgeRetrieval(
        {
            "connectionId": connection_id,
            "knowledgeBaseIds": knowledge_base_ids,
            "retrievalConfig": retrieval_config,
        }
    )
    kb_config = await component.ensure_kb_config()
    connection_config = kb_config.get("connection", {})
    loaded_kbs = _merge_tags(kb_config.get("knowledge_bases", []), tag_overrides)
    retrieval_params = kb_config.get("retrieval_params", {})

    connector_type = connection_config.get("connector_type", "LakeSearch")
    adapter = KBAdapterFactory.create(connector_type)
    trace_tracer = _resolve_retrieval_tracer()
    trace_span = None
    if trace_tracer is not None:
        # 开 span 同样不许打断检索：create_agent_span / 事件载荷准备任一步
        # 抛错都降级为无遥测继续业务（与 _trace_retrieval_event 同口径）
        try:
            trace_span = await _trace_retrieval_start(
                trace_tracer, str(query), knowledge_base_ids, retrieval_config
            )
        except Exception as e:  # noqa: BLE001 - tracing must never break retrieval
            workflow_logger.warning("retrieval trace start failed: %s", e)
            trace_span = None
    try:
        results = await component.search_knowledge_repo(
            adapter=adapter,
            query=str(query),
            connection_config=connection_config,
            knowledge_bases=loaded_kbs,
            retrieval_params=retrieval_params,
        )
        # CUSTOM 知识源不做 file_id 虚拟化 / 图片处理
        if not component.is_custom_source(connection_config):
            results = await component.normalize_results_like_java(
                results,
                loaded_kbs,
                retrieval_params,
            )
    except BaseException as e:  # noqa: BLE001 - CancelledError 是 BaseException
        if trace_tracer is not None and trace_span is not None:
            # error 事件未送达时兜底收尾已开启的 otel span；BaseException
            # 口径：asyncio 取消同样要走收尾，否则半开 span 滞留
            # （jdfff 11-05：原 except Exception 漏掉 CancelledError）
            try:
                delivered = await _trace_retrieval_event(
                    trace_tracer, "on_retriever_error", trace_span, error=e
                )
            except BaseException:  # noqa: BLE001 - 取消落在 trigger 内同样要收尾
                _drop_retrieval_span(trace_tracer, trace_span)
                raise
            if not delivered:
                _drop_retrieval_span(trace_tracer, trace_span)
        raise
    if trace_tracer is not None and trace_span is not None:
        try:
            delivered = await _trace_retrieval_event(
                trace_tracer,
                "on_retriever_end",
                trace_span,
                outputs={"document_count": len(results)},
            )
        except BaseException:  # noqa: BLE001 - 取消落在 trigger 内同样要收尾
            _drop_retrieval_span(trace_tracer, trace_span)
            raise
        if not delivered:
            _drop_retrieval_span(trace_tracer, trace_span)
    retrieval_id = uuid.uuid4().hex
    for index, result in enumerate(results, start=1):
        result.retrieval_id = retrieval_id
        if result.serial_number == 0:
            result.serial_number = index

    output_list = [_to_agent_output(result) for result in results]
    return _format_output(output_list)


def build_knowledge_retrieval_tool(ir_data: dict, params: List[Param]) -> Function:
    """Build an internal Function that replaces the old retrieval REST plugin."""
    resolved = _resolve_retrieval_params(ir_data)

    async def retrieve(query: str, **kwargs) -> dict:
        return await _run_retrieval(
            query=query,
            connection_id=resolved["connection_id"],
            knowledge_base_ids=resolved["knowledge_base_ids"],
            retrieval_config=resolved["retrieval_config"],
            tag_overrides=resolved["tag_overrides"],
        )

    return Function(
        name=ir_data.get("name", _RETRIEVAL_NAME),
        description=ir_data.get("description", ""),
        params=params,
        func=retrieve,
        plugin_name=ir_data.get("name", _RETRIEVAL_NAME),
        plugin_desc=ir_data.get("description", ""),
        related_info={"logo": ir_data.get("logo", "")},
    )


class KnowledgeRetrievalTool(Tool):
    """openjiuwen Tool subclass that wraps knowledge retrieval for single-agent use.

    Registered into ReActAgent.ability_manager so the agent invokes retrieval through
    FlowKnowledgeRetrieval directly (same path as the workflow's jiuwen.knowledgeRetrieval
    node), instead of going through RestfulApiToolNew/HTTP.
    """

    def __init__(
        self,
        card: ToolCard,
        connection_id: str,
        knowledge_base_ids: List[str],
        retrieval_config: Dict[str, Any],
        tag_overrides: Dict[str, Any],
    ):
        super().__init__(card)
        self._connection_id = connection_id
        self._knowledge_base_ids = knowledge_base_ids
        self._retrieval_config = retrieval_config
        self._tag_overrides = tag_overrides

    async def invoke(self, inputs: Input, **kwargs) -> Output:
        query = ""
        if isinstance(inputs, dict):
            query = inputs.get(_QUERY) or inputs.get("inputs", {}).get(_QUERY, "") if isinstance(
                inputs.get("inputs"), dict
            ) else inputs.get(_QUERY, "")
        elif isinstance(inputs, str):
            query = inputs
        # session 由 ability_manager 调用时注入；携带时在 execute_tool span 下
        # 补一对 retrieval 事件（核心侧 OTel handler 会开 retrieval 子 span）。
        # 与 _run_retrieval 内建 ambient 遥测互斥（见 _start_retrieval_span 守卫）
        session = kwargs.get("session")
        span = None
        try:
            span = await self._start_retrieval_span(session, query)
            result = await _run_retrieval(
                query=str(query or ""),
                connection_id=self._connection_id,
                knowledge_base_ids=self._knowledge_base_ids,
                retrieval_config=self._retrieval_config,
                tag_overrides=self._tag_overrides,
            )
        except BaseException as exc:
            # BaseException：asyncio.CancelledError（取消/超时）不属于 Exception，
            # 取消落在 start 或检索期间都先收尾 error 事件再抛出；start 阶段取消时
            # span 尚未开启（None），收尾为 no-op，避免 retrieval span 悬空
            await self._end_retrieval_span_error(session, span, exc)
            raise
        await self._end_retrieval_span(session, span, result)
        return result

    async def _start_retrieval_span(self, session, query) -> Optional[object]:
        """开启 retrieval 追踪；追踪不可用或失败时返回 None，不影响检索。"""
        if _TracerAgentUtils is None or session is None:
            return None
        if _resolve_retrieval_tracer() is not None:
            # ambient 会话上下文可达时由 _run_retrieval 内建遥测发射（inputs 携带
            # top_k / knowledge_base_ids，属性更全）；kwargs 会话仅兜底 ambient
            # 不可达的调用点（如跨线程同步桥的 contextvar 跳变），互斥不双计
            return None
        tracer = _resolve_session_tracer(session)
        if tracer is None:
            return None
        # 不经 TracerAgentUtils.trace_retriever_start：它先 create_agent_span
        # 登记再无保护 trigger，start 事件抛 Exception 时外壳吞掉异常返回
        # None，登记永久残留（悬空记录 + last_span 污染，部分 handler 已开
        # OTel span 时还留半开 span）。这里复用 _trace_retrieval_start 的
        # 收尾语义：start 未送达即注销登记；BaseException 注销后原样上抛
        # （由 invoke 的收尾伞接住）
        try:
            return await _trace_retrieval_start(
                tracer,
                str(query) if query else "",
                self._knowledge_base_ids,
                self._retrieval_config,
            )
        except Exception as e:  # noqa: BLE001 - tracing must never break retrieval
            # 能到这里的只剩登记前的同步异常：登记后的触发失败已在
            # _trace_retrieval_start 内部注销收尾
            workflow_logger.warning("knowledge retrieval trace start failed: %s: %s", type(e).__name__, e)
            return None

    async def _end_retrieval_span(self, session, span, result) -> None:
        if _TracerAgentUtils is None or span is None or session is None:
            return
        try:
            output_list = (result.get(constant.RESTFUL_DATA) or {}).get("output_list") or []
            # 只送 document_name（标识符），检索正文不进遥测属性——core handler 对
            # results 逐项 str() 无截断无脱敏，全量 text 直进 span 会泄露敏感内容
            documents = [
                item["document_name"]
                for item in output_list
                if isinstance(item, dict) and item.get("document_name")
            ]
            await _TracerAgentUtils.trace_retriever_end(session, span, documents=documents)
        except Exception as e:
            workflow_logger.warning("knowledge retrieval trace end failed: %s: %s", type(e).__name__, e)
            _drop_retrieval_span_by_session(session, span)
        except BaseException:
            # 真实任务取消下 end 事件的 await 会再收到 CancelledError：
            # 同步尽力收尾（注销登记 + drop 半开 span）后原样上抛，不留悬空
            _drop_retrieval_span_by_session(session, span)
            raise

    async def _end_retrieval_span_error(self, session, span, error) -> None:
        if _TracerAgentUtils is None or span is None or session is None:
            return
        try:
            await _TracerAgentUtils.trace_retriever_error(session, span, error)
        except Exception as e:
            workflow_logger.warning("knowledge retrieval trace error event failed: %s: %s", type(e).__name__, e)
            # 事件未送达：otel span 已开启且再无关闭时机，兜底收尾半开 span
            _drop_retrieval_span_by_session(session, span)
        except BaseException:
            _drop_retrieval_span_by_session(session, span)
            raise

    async def stream(self, inputs: Input, **kwargs) -> AsyncIterator[Output]:
        yield await self.invoke(inputs, **kwargs)


def build_knowledge_retrieval_openjiuwen_tool(
    ir_data: dict, input_params: Optional[Dict[str, Any]] = None
) -> KnowledgeRetrievalTool:
    """Build an openjiuwen Tool that performs knowledge retrieval via FlowKnowledgeRetrieval.

    The Tool name is set to "retrieval" so the openjiuwen tool-lifecycle tracer emits
    metaData.class_name="retrieval", which the Java side maps to KNOWLEDGE node type.
    """
    resolved = _resolve_retrieval_params(ir_data)
    tool_id = str(ir_data.get("id") or ir_data.get("name") or _RETRIEVAL_NAME)
    name = ir_data.get("name", _RETRIEVAL_NAME)
    card = ToolCard(
        id=tool_id,
        name=name,
        description=ir_data.get("description", ""),
        input_params=input_params or {
            "type": "object",
            "properties": {_QUERY: {"type": "string", "description": "Query for knowledge retrieval."}},
            "required": [_QUERY],
        },
    )
    return KnowledgeRetrievalTool(
        card=card,
        connection_id=resolved["connection_id"],
        knowledge_base_ids=resolved["knowledge_base_ids"],
        retrieval_config=resolved["retrieval_config"],
        tag_overrides=resolved["tag_overrides"],
    )


def _get_argument_default(ir_data: dict, name: str, default: Any = None) -> Any:
    for argument in ir_data.get("arguments", []):
        if argument.get("name") == name:
            return argument.get("default_value", default)
    return default


def _build_retrieval_config(ir_data: dict, knowledge_config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if isinstance(knowledge_config, dict):
        retrieval_config = dict(knowledge_config.get("retrievalConfig") or {})
    else:
        retrieval_config = {}
    mapping = {
        _TOP_K: "topK",
        _RECALL_THRESHOLD: "recallThreshold",
        _FAQ_THRESHOLD: "faqThreshold",
        _SEARCH_MODE: "searchMode",
        _NEED_EXTRAS_FAQ_SEARCH: "needExtrasFaqSearch",
        _RETRIEVE_IMAGE: "retrieveImage",
        _SHOW_SOURCE: "showSource",
    }
    for argument_name, config_name in mapping.items():
        value = _get_argument_default(ir_data, argument_name)
        if value is not None:
            retrieval_config[config_name] = value
    if "recallThreshold" in retrieval_config:
        retrieval_config["scoreThreshold"] = retrieval_config["recallThreshold"]
    return retrieval_config


def _resolve_connection_id(knowledge_bases: Iterable[dict]) -> str:
    for kb in knowledge_bases:
        if isinstance(kb, dict) and kb.get("connection_id"):
            return str(kb["connection_id"])
    return ""


def _merge_tags(loaded_kbs: List[dict], tag_overrides: Dict[str, Any]) -> List[dict]:
    merged = []
    for kb in loaded_kbs:
        item = dict(kb)
        kb_id = str(item.get("knowledge_base_id", ""))
        if kb_id in tag_overrides:
            tags = tag_overrides[kb_id]
            item["tags"] = tags if isinstance(tags, list) else []
        merged.append(item)
    return merged


def _to_agent_output(result: KBSearchResult) -> dict:
    return {
        "document_name": result.document_name,
        "score": result.score,
        "subtitle": result.subtitle,
        "content": result.text,
        "text": result.text,
        "knowledge_base_id": result.knowledge_base_id,
        "knowledge_base_type": result.knowledge_base_type,
        "file_id": result.file_id,
        "serial_number": result.serial_number,
        "retrieval_id": result.retrieval_id,
        "type": result.type,
        "source": result.source,
        "metadata": result.metadata,
    }


def _format_output(output_list: List[dict]) -> dict:
    return {
        constant.ERR_CODE: 0,
        constant.ERR_MESSAGE: "success",
        constant.RESTFUL_DATA: {"output_list": output_list},
    }
