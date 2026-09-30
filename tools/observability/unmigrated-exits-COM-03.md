# COM-03 未迁移出口清单

> 生成日期：2026-09-15（复审8 §8.2.3 刷新）
> 代码基线：`debug_log_20260818` 分支 COM-03 收口系列（前置实现 `5a621432`，收口提交为本清单所在分支 HEAD，见 `git log --oneline` 中 `feat(error-contract): COM-03 收口` 系列）
> 规划依据：工作记录《代码修改规划-COM-03-三服务descriptor-HTTP-SSE构建器与框架出口》§8（文档位于工作区根仓库 工作记录/20260818-日志机制整改/代码修改规划/，不在本仓库内）
> 复审6 §6.3 要求列：服务 / 文件与符号 / HTTP或SSE / 当前 fixture / 目标 profile / 后续任务 / 启用或删除条件

## 1. 已接入统一底座的出口（COM-03 范围内完成）

| 服务 | 文件 | 符号 | 类型 | 当前 fixture | 目标 profile | 后续任务 | 启用/删除条件 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Manager | MgGlobalExceptionHandler.java | 10 个 @ExceptionHandler + AgentBaseException + FeignException + 405 + BindException + DataAccessException + Exception.class | HTTP | 标准五字段 via factory→safeBuild | STANDARD_HTTP_V1 | — | — |
| Manager | WorkspaceInterceptor.java | preHandle 参数校验 | HTTP | throw AgentStudioException→统一 Advice | STANDARD_HTTP_V1 | — | — |
| Manager | ProxyEventSourceListener.java | onFailure + createErrorRsp + sendErrorEvent | SSE+HTTP | tryHttpFailure/trySendError 原子二选一 + factory builder + locale 快照 | STANDARD_SSE_V1 | — | — |
| Runtime | server.py | validation/HTTPException/AgentBuilderError/Storage/generic error handler | HTTP | factory→build_json_response | STANDARD_HTTP_V1 | — | — |
| Runtime | error_response.py | build_unhandled_error_response | HTTP | factory→build_json_response | STANDARD_HTTP_V1 | — | — |
| Runtime | middleware.py | _conflict_response | HTTP | factory→build_json_response | STANDARD_HTTP_V1 | — | — |
| Runtime | orchestration.py | ir_execute 首帧预取 | SSE+HTTP | 预取失败→HTTP error;成功→_prefetched_stream + stream_response 内部 SSE error guard | STANDARD_SSE_V1 | — | — |
| Runtime | orchestration.py | stream_response 首帧后异常 | SSE | build_sse_error_event + guard | STANDARD_SSE_V1 | — | — |
| Builder | server_fastapi.py | JiuWenException + RequestValidationError + HTTPException + generic Exception | HTTP | factory→build_json_response | STANDARD_HTTP_V1 | — | — |
| Builder | error_response.py | build_unhandled_error_response | HTTP | factory→build_json_response | STANDARD_HTTP_V1 | — | — |
| Builder | server.py | WerkzeugHTTPException + Exception errorhandler | HTTP | factory→build_flask_error | STANDARD_HTTP_V1 | — | — |
| Builder | exception_handler.py | catch_exception 装饰器 3 分支 | HTTP | factory→build_flask_error | STANDARD_HTTP_V1 | — | — |
| Builder | model_service_api.py | _error_response | HTTP | ErrorRsp 四字段(无 raw upstream body) | STANDARD_HTTP_V1 | DEF-08/09 精细映射 | — |
| Builder | nl2.py | _generate 异常路径 | SSE | build_sse_error_event + guard, locale 从上下文 | STANDARD_SSE_V1 | COM-07 完整资源回收 | — |
| Manager | MgGlobalExceptionHandler.java | handleDownstreamFailure + handleFeignException(重写) | HTTP | DownstreamFailure→mapper 一次→safeBuild；transport/未分类→EXTERNAL 统一 | STANDARD_HTTP_V1 | COM-04 响应 | — |
| Manager | RuntimeCorrelationFeignConfig / BuilderCorrelationFeignConfig | ErrorDecoder bean | HTTP | 非2xx body→parser(RUNTIME/BUILDER)→DownstreamFailureException | STANDARD_HTTP_V1 | COM-04 响应 | — |
| Manager | ClientTemplateConfig.java | builderClientTemplate ResponseErrorHandler | HTTP | 全部非2xx→受限读 body→parser(BUILDER)→DownstreamFailureException | STANDARD_HTTP_V1 | COM-04 响应 | — |
| Manager | JiuWenPromptTaskJob.java | generatePrompt/optimizeFeedback onStatus+onErrorResume | HTTP | DownstreamWebClientAdapter(BUILDER)——删原文日志+catch-all | STANDARD_HTTP_V1 | COM-04 响应 | — |
| Manager | JiuWenService.java | callModelStream/generatorAgentOrWorkflow onStatus | HTTP+SSE | DownstreamWebClientAdapter(RUNTIME/BUILDER)；chunk 解析失败只记长度 | STANDARD_HTTP_V1 | COM-04 响应 | — |
| Manager | BaseEventListener.java | handleTerminalFailure + buildDownstreamDescriptor | SSE+HTTP | SseTerminalGuard 原子终态+parser/mapper 一次；删四透传行为 | STANDARD_SSE_V1 | COM-04 响应 | — |
| Manager | WorkflowListener/LLMAgentListener/ControllerAgentListener | onFailureInternal(经 base) | SSE+HTTP | 共享 base 统一 adapter | STANDARD_SSE_V1 | COM-04 响应 | — |
| Manager | AsyncWorkflowListener.java | onFailureInternal 重写 | 异步任务终态 | buildDownstreamDescriptor→安全任务状态（无 HTTP/SSE builder，errorInfo=稳定码） | STANDARD_SSE_V1 | COM-04 响应 | — |
| Manager | TaskRuntimeService.java | executeWorkflow catch-all | 异步任务文案 | DownstreamFailure 稳定事实替代 e.getMessage() | STANDARD_HTTP_V1 | COM-04 响应 | — |

## 2. 未迁移出口（明确延期，后续任务归属）

| 服务 | 文件 | 符号 | 类型 | 当前 fixture | 目标 profile | 后续任务 | 启用/删除条件 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Manager | AuthController.java / ResourceInstInternController.java（位于 common/service/contrlller 路径） | 手写 ResponseEntity/JSONResponse | HTTP | 业务手写 | STANDARD_HTTP_V1 | COM-06 | 扫描证据：`grep -rl "JSONResponse\|ResponseEntity" --include="*Controller.java" backend/studio-manager-service/src/main/java/ backend/studio-common/src/main/java/` → 仅 2 文件；逐方法迁移 |
| Manager | SamlController.java | handleSamlResponse 4 分支 | HTTP | plain text / {error,message} | STANDARD_HTTP_V1 | COM-06 | SAML 路由消费方确认 |
| Manager | SamlAuthFilter.java | redirectToSamlLogin | HTTP | {code,message,redirectUrl} | STANDARD_HTTP_V1 | COM-06 | — |
| Manager | SsoAuthenticationFilter.java | handleAuthException | HTTP | {code,message} | STANDARD_HTTP_V1 | COM-06 | — |
| Manager | OAuth2SecurityConfig.java | entryPoint + accessDenied | HTTP | {code,message} | STANDARD_HTTP_V1 | COM-06 | — |
| Manager | AgentSpaceControllerAdvice.java | handleControllerException | HTTP | BaseResp{code,message,data} | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | orchestration.py | component_debug_execute | SSE+HTTP | 已撤回半接入,恢复为 plain StreamingResponse | STANDARD_SSE_V1 | COM-06 | 首帧预取+首帧后 error/guard/资源回收待补 |
| Runtime | orchestration.py | ir_execute/additional_questions 等 9 处路由直返 | HTTP | {error,details} / {code,message} / {error:{code,message}} | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | orchestration.py | _build_runtime_execution_headers 保留 header 冲突 | HTTP | 不拦截(死代码 except ValueError 已删) | STANDARD_HTTP_V1 | COM-06 | body.headers 冲突检测+400 五字段 |
| Runtime | release_api.py | create/delete_release_info 3 处 | HTTP | {error:"str"} | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | app_run.py | _execute_workflow_run / _execute_agent_run 3 处 | HTTP | {error:"str"} | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | app_release.py / run_check.py / conversation_variable_api.py | _build_error_response 8 处 | HTTP | ErrorRsp-style 四字段 | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | inner_tools.py | HTTPException 5 处 | HTTP | {detail} | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | memory/internal_routes.py | 16 处路由直返 | HTTP | {status,reason} (HTTP 200) | STANDARD_HTTP_V1 | COM-06 | — |
| Runtime | workflow_runner.py | 8 处 SSE error yield | SSE | {response} / {code,message,node_*} | STANDARD_SSE_V1 | COM-06 | 逐路由迁移 |
| Runtime | controller_runner.py + react_agent_runner.py | 10 处 SSE error via adapter | SSE | {code,message,node_name} | STANDARD_SSE_V1 | COM-06 | — |
| Runtime | event_handler.py / base_events.py / field_processor.py | 3 处 SSE error | SSE | {code,message,error_msg,...} | STANDARD_SSE_V1 | COM-06 | — |
| Runtime | stream_moderation.py | 2 处 block/interrupt | SSE | block event + message_end + workflow_end | STANDARD_SSE_V1 | COM-06 | — |
| Builder | prompt.py | 5 处 Flask jsonify | HTTP | {code,message} (HTTP 200) | STANDARD_HTTP_V1 | COM-06 | — |
| Builder | mmapo.py | 3 处 Flask jsonify | HTTP | {code,message} (HTTP 200) | STANDARD_HTTP_V1 | COM-06 | — |
| Builder | llm_service.py | 4 处 streaming_chat error | SSE | {code,message,data:""} | STANDARD_SSE_V1 | COM-06 | — |
| Builder | nl2.py | _generate 单 guard 状态机 + COM-03 builder(已删 _error_sse_generator/to_error_sse/SSEEvent/_nl2_get_error 死代码) | SSE | START→MESSAGE→END / →error 五字段(无 conversationId) | STANDARD_SSE_V1 | COM-07A 实施中(待最新复审) | N2L 完整生命周期实施中,待复审通过后标记完成 |
| Builder | async_server.py | PatchedvLLMServer.chat_completion | HTTP | vllm ErrorResponse passthrough | STANDARD_HTTP_V1 | COM-06 | — |

## 3. 项目决策豁免项

| 项目 | 决策 | 条件 |
| --- | --- | --- |
| Runtime memory_server | 当前未使用，不阻塞 COM-03 | 重新启用前另立任务完成统一 error contract 接入和出口测试 |
| Builder N2L 完整 framing/取消/生成器关闭 | 归 COM-07A(实施中,待最新复审) | _generate 已接入 SSE builder + 单 guard 状态机 + 幂等有界 cleanup + Executor 迭代器 aclose 传播 |
| Runtime 首帧前 runner 异常预取 | 已实现 | _prefetched_stream + stream_response 内部 SSE error guard |

## 4. COM-07A 消费者可见兼容变化

| 变化 | 旧 wire | 目标 wire | 受影响入口 | 消费者迁移方式 |
| --- | --- | --- | --- | --- |
| 旧 `_error_sse_generator()` error 帧移除顶层 `conversationId` | `{data:{code,message}, event:error, conversationId}` | COM-03 `{event:error, data:{error_code,error_msg,error_reason,error_suggestion,request_id}}` 无顶层 `conversationId` | `_chat()` 建流前异常(ValidationError/Executor 建立失败) → 薄 `_preflight_error_stream` | error 帧关联查询改用 `request_id`(五字段),消费者依赖 `conversationId` 的由 COM-06 发布说明承接 |
| 旧 `100029 + Model response error → DeepSeek-V3` 硬编码文案 | 异常文本匹配 → "recommended to use DeepSeek-V3" 英文文案 | COM-03 descriptor 安全三段文案(canonical 码),不按异常文本识别 | `_error_sse_generator()` 已删除 | 产品若继续提供模型切换建议,须先转化为已登记错误定义+中英文目录文案,由统一 builder 输出;DEF-08 复核模型失败分类时读取本登记 |
| 旧 `to_error_sse()` 流内 `{code,message}` | `{data:{code,message}, event:MESSAGE, conversationId}`(item 为 Exception 时) | COM-03 builder 五字段 error 终态(无 conversationId) | `_generate()` 流内 item-Exception 路径 | 已删除,统一走 `build_sse_error_event()` + guard |

## 5. 统计

| 类别 | 数量 |
| --- | --- |
| 已接入统一底座 | 23（+9 COM-04 响应） |
| 未迁移（明确延期） | 21（BaseEventListener 销账） |
| 项目决策豁免 | 3 |
| **合计** | **39** |
