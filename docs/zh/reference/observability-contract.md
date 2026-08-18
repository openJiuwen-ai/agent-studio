# Studio 2.0 可观测性统一协议（独立版）

> 版本：v1.2
> 状态：已冻结
> 创建日期：2026-08-13
> 修订冻结日期：2026-08-18
> 性质：规范性协议
> 长期权威位置：`agent-studio/docs/zh/reference/observability-contract.md`
> 适用对象：Manager、Runtime、Builder 三个服务，以及日志采集与入库链路
> 代码基线：`agent-studio/backend`、`agent-studio/agent-runtime`、`agent-studio/agent_builder`、`agent-core`

本文统一定义关联 ID、跨服务 Header、日志格式、采集字段、错误码、错误响应、Builder N2L 可观测事件和上下文生命周期。本文可独立作为开发、联调、测试和验收依据；本文中的全部可观测性强制要求均在正文中给出，不依赖其他设计文档补充定义。

---

## 1. 约束级别

- **MUST / 必须 / 禁止**：硬约束；实现不满足即视为缺陷。
- **SHOULD / 应当**：强烈建议；如确需偏离，必须在变更说明中写明原因、影响和替代措施。

---

## 2. 目标、范围与服务边界

本协议解决以下问题：

- 三服务对 `trace_id`、`request_id`、`execution_id` 和 `conversation_id` 的语义不一致；
- Manager 出站调用和异步线程中的关联上下文传播不完整；
- Runtime 曾以会话 ID 或执行 ID 派生 `trace_id`；
- Builder 缺少稳定的 `request_id` 日志位和日志落盘配置；
- 三服务错误响应形态、错误码定义和下游错误保留方式不一致；
- N2L 缺少可稳定采集的会话关联、阶段事件和首消息指标。

| 服务 | 平台部署端口 | 技术栈 | 日志上下文机制 |
|---|---:|---|---|
| Manager | 31111 | Java / Spring Boot | Log4j2 MDC |
| Runtime | 31014 | Python / FastAPI | ContextVar + logging |
| Builder | 31015 | Python / FastAPI + Flask | ContextVar + logging |

Runtime 和 Builder 的代码默认端口均为 `8000`，平台部署通过 `SERVER_PORT` 等环境配置覆盖为表中端口；本表描述平台标准部署值，不描述脱离部署配置直接启动时的代码默认值。

本期不要求完成全部性能埋点、动态日志调级和 OTel Metrics 告警实现，但相关实现不得违反本文字段、安全和生命周期约束。采集器不在本平台仓库中实现；本文只规定目标日志对应的采集、解析和入库设计要求，不要求采集器兼容改造前的旧日志格式。

---

## 3. 关联 ID 与 Header 契约

### 3.1 字段定义

| 字段 | 权威语义 | 生命周期与来源 | 传输方式 | 统一日志字段 |
|---|---|---|---|---|
| `trace_id` | 一次跨服务业务调用链 | 入站读取合法 `TraceID`；缺失或非法时回退本请求 `request_id` | Header `TraceID` | `trace_id` |
| `request_id` | 一次顶层请求及其直接、间接下游调用树 | 顶层入口接收合法 `X-Request-Id`，否则生成 UUID；调用树内原值透传 | Header `X-Request-Id` | `request_id` |
| `execution_id` | 一次 Agent、Workflow 或节点执行 | 三服务处理方式不同，见下表 | 执行调用使用 Header `X-Execution-Id`；执行查询使用路径参数 `{execution_id}` | `execution_id` |
| `conversation_id` | 一次多轮会话 | 三服务处理方式不同，见下表 | 会话型接口的路径参数；Runtime 直接编排接口的请求体字段 | `conversation_id` |
| `task_id` | Manager Workflow 异步任务实体 ID | 创建异步任务时生成 UUID，只在 Manager 内使用，不传给 Runtime 或 Builder | Manager 任务 API 的路径参数及请求/响应 DTO | `task_id` |
| `job_id` | Builder 后台任务 ID | Builder 创建 Prompt 优化或 MMAPO 任务时生成。Manager 不生成该值，只将 Builder 返回的值保存为 `jiuwenTaskId` | Builder 在创建任务响应返回给 Manager；Manager 后续通过 Builder 任务 API 的路径参数或批量请求体传回 | `job_id` |

`task_id` 和 `job_id` 是不同实体，不得合并。Manager 调用 Runtime 执行异步任务时，传递的是 `conversation_id` 和 `X-Execution-Id`，不传递 `task_id`。`job_id` 仅在 Builder Job 已创建且当前日志与该 Job 有关时输出；Manager 和 Builder 都可按需输出该字段，但不将其加入所有日志的固定管道位。Manager MDC 的目标 key 为 `execution-id`；当前代码中语义相同的历史 key `task-id` 必须迁移。Builder N2L 代码中名为 `task_id` 的局部变量实际承载 `conversation_id`，不是本协议的 `task_id`。`request_id` 不是每个 HTTP hop 都重新生成的 hop ID；同一调用树的 Manager、Runtime、Builder 必须保留同一个 `request_id`。

**`execution_id` 按服务分别定义：**

下表是改造完成后必须达到的目标契约，不表示当前代码已经满足。当前代码仍存在恢复执行保存键与查询键不一致、使用 `request_id` 回退 `execution_id`、MDC 命名和生命周期不符合目标等差距；验收以本表为准。

| 服务 | 来源与处理规则 |
|---|---|
| Manager | Manager 是调用 Runtime 时 `execution_id` 的选值和透传方。优先级固定为：<br>① 恢复执行时从持久化记录或 Redis 读取原值；<br>② Manager 内部执行参数对象中已经选定并校验的值；<br>③ 入站 `X-Execution-Id` 中的合法值；<br>④ 以上均无值时为新执行生成 UUID。<br>内部执行参数对象只是承载已选定结果，不是新的外部输入来源。选定后写入 MDC `execution-id`，并通过出站 `X-Execution-Id` 传给 Runtime。<br>禁止使用 `request_id` 作为回退值。 |
| Runtime | 来源只有两类：<br>① 入站 HTTP Header `X-Execution-Id` 传入合法值；<br>② Header 缺失或值非法时自动生成 UUID。<br>`RequestContextMiddleware` 是请求内的唯一建立点，确定后写入 `request.state` 和请求 ContextVar；后续代码不得重新取值或生成新值。<br>禁止使用 `conversation_id`、`request_id` 或其他字段代替或推断 `execution_id`。 |
| Builder | **不存在 `execution_id`。**<br>Builder 不读取 `X-Execution-Id`，日志不输出 `execution_id`，入库时该字段缺失或为 `null`。<br>Prompt 优化和 MMAPO 任务使用 `job_id`，不得用其代替 `execution_id`。 |

一次执行的 `execution_id` 建立后，后续下游调用和恢复过程必须沿用原值；不得因跨服务、重试或恢复而重新生成。只有负责创建新执行的一方在确认不存在可沿用值时才可生成 UUID。

当前代码中的 Agent/Workflow 执行请求体模型均没有直接的 `execution_id` 字段，因此本协议不定义“通过业务请求 DTO 传递 `execution_id`”的渠道。Manager 的 `ExecuteParams`、`AgentExecuteParams` 是内部对象；响应、SSE 事件和执行详情对象中的 `executionId` 是输出字段。查询已有执行时，`execution_id` 来自接口路径参数，不参与新执行的选值流程。

**`conversation_id` 按服务分别定义：**

| 服务 | 来源与处理规则 |
|---|---|
| Manager | 有效来源只有两类：<br>① 调用方通过 URL 路径 `{conversation_id}` 传入，Manager 校验后原样转发给 Runtime；<br>② 创建 Workflow 异步任务时，由 `TaskManagementService.createTask()` 生成 UUID。<br>无会话 ID 的 Agent 接口不构成有效来源：Manager 不生成 ID，当前 Runtime 也没有对应路由，因此该链路不能完成执行。Manager 不从 Header 或请求体获取 `conversation_id`。 |
| Runtime | 来源为入站请求：<br>① 常规接口从 URL 路径 `{conversation_id}` 取得；<br>② 直接编排及组件执行接口从请求体 `conversationId` 取得。<br>最终值必须写入请求上下文，不得从其他关联 ID 推断。路径与请求体同时存在时，两者不同应拒绝。 |
| Builder | **N2L 存在 `conversation_id`。**<br>值来自路由 `/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat` 的 `{cid}`。N2L 使用 Builder common 日志；`conversation_id` 不进入 common 固定管道位，而是由同一 common 日志中的 `[N2L_EVENT]` 结构化消息输出。当前 N2L 已使用 common logger，`[N2L_EVENT]` 输出属于待开发的目标能力。请求体中的兼容字段 `conversationId` 应删除；暂时保留时必须与 `{cid}` 相同，冲突返回 400。<br>**其他 Builder 功能不存在 `conversation_id`。**<br>Prompt 优化和 MMAPO 使用 `job_id`。非 N2L 记录入库时 `conversation_id` 缺失或为 `null`，不得写空字符串或用其他 ID 补值。 |

N2L 与其他 Builder 功能使用同一 common 日志能力。由于只有 N2L 具有 `conversation_id`，common 固定管道仅保留通用关联字段；N2L 通过 common 日志 `message` 中带固定前缀的结构化事件记录 `conversation_id`。这不是一套独立日志系统。

### 3.2 Header 关联 ID 合法性与入口算法

本节只适用于 Header `X-Request-Id`、`TraceID` 和 `X-Execution-Id`，不适用于路径或请求体中的 `conversation_id`，也不适用于业务字段 `task_id` 和 `job_id`。

Header 关联 ID 长度为 1 至 64，只允许字符 `[A-Za-z0-9._:-]`，不得包含空白、换行或控制字符。非法值按缺失处理，不记录非法原值。

三服务入口都必须执行：

```text
request_id = valid(X-Request-Id) ? X-Request-Id : UUID
trace_id   = valid(TraceID)      ? TraceID      : request_id
```

Manager 读取 `X-Execution-Id` 时先按本节规则校验，再按 Manager 的 `execution_id` 选值优先级处理；非法值视为未传入。

Runtime 读取合法的 `X-Execution-Id` 时原样使用，缺失或非法时生成 UUID。Builder 不读取 `X-Execution-Id`。

`conversation_id`、`task_id` 和 `job_id` 分别按各自接口与业务模型的规则校验，不使用本节的 Header 入口算法。

Builder N2L 路由 `/v1/{project_id}/{agent_type}/generator/conversations/{cid}/chat` 的 `{cid}` 是该请求唯一权威的 `conversation_id`，长度为 1 至 128，只允许 `[A-Za-z0-9._:-]`。目标请求体不再声明 `conversationId`；兼容期如暂时保留，存在时必须与 `{cid}` 完全相同，冲突必须拒绝，禁止静默覆盖。

Manager 必须将 `request_id` 和 `trace_id` 写入 MDC，并在响应中回写 `X-Request-Id`；应当回写 `TraceID` 便于排障。Runtime 和 Builder 的异常响应路径也必须保留并回写 `X-Request-Id`。

### 3.3 Manager MDC 命名

Manager 目标态统一使用以下 MDC key：

- `request-id`：对外归一为 `request_id`；
- `execution-id`：对外归一为 `execution_id`；
- `conversation-id`：对外归一为 `conversation_id`；
- `trace_id`：对外仍为 `trace_id`。

前三个 MDC key 延续 Manager 既有的 kebab-case 风格；`trace_id` 为明确例外，目的是与三服务统一日志字段名保持一致，避免在应用日志配置和出站 Header 提供器中再维护一层 `trace-id` 到 `trace_id` 的命名映射。不得同时引入 `trace-id` 形成双 key。

当前代码和 Log4j2 Pattern 中的历史 key `task-id` 实际承载 `execution_id`，开发时必须将其写入、读取、日志 Pattern 和测试同批迁移为 `execution-id`。异步任务实体 `TaskEntity.id` 使用 `task_id`，不写入调用链 MDC 的 `execution-id`，也不等于 `execution_id`。

### 3.4 禁止规则

1. 禁止使用 `conversation_id`、`execution_id`、`task_id` 或 `job_id` 生成或代替 `trace_id`。
2. 禁止使用 `request_id`、`conversation_id`、`task_id`、`job_id` 或其他字段生成、回退或代替 `execution_id`。新执行无可沿用值时必须生成 UUID。
3. `task_id` 和 `job_id` 是不同的业务任务 ID，不得相互代替，也不得使用 `execution_id`、`conversation_id`、Manager MDC `execution-id` 或其他字段补值。
4. 禁止为 `conversation_id` 新增 Header。Manager 和 Runtime 常规会话接口通过 URL 路径传递；Runtime 直接编排接口通过请求体传递；Builder N2L 通过 URL 路径 `{cid}` 传递。
5. 资源对象中用于导入同源判断的 `traceId` 是业务字段，不是可观测性字段；不得将其写入 `trace_id`、`request_id` 或其他统一日志字段。
6. 禁止应用或采集器通过复制、推断其他字段来补造缺失的关联 ID。
7. 禁止采集器从自由日志文本中的 `taskId`、`jiuwenTaskId`、`job_id` 等名称猜测统一字段；`task_id` 和 `job_id` 只能从后续方案冻结的结构化事件中提取。

### 3.5 Manager 出站 Header 注入

Manager 的 Feign、OkHttp、RestTemplate 和 WebClient 必须复用统一的关联 Header 提供器。提供器只读取当前上下文中已经确定的值，不负责选择、生成或推断关联 ID。

Manager 调用 Runtime 或 Builder 时统一注入：

```text
X-Request-Id <- MDC[request-id]
TraceID      <- MDC[trace_id]
```

Manager 发起 Agent、Workflow 或节点执行调用时，仅向 Runtime 额外注入：

```text
X-Execution-Id <- MDC[execution-id]
```

具体规则：

1. Runtime 执行调用通过 `X-Execution-Id` 传递 `execution_id`。
2. 查询已有执行时，`execution_id` 使用路径参数 `{execution_id}`，不依赖 `X-Execution-Id`。
3. Builder 不读取 `X-Execution-Id`，Manager 调用 Builder 时不得注入该 Header。
4. `conversation_id` 按接口定义通过 URL 路径或请求体传递，不通过 Header。
5. `task_id` 和 `job_id` 不通过 Header 传递。
6. 出站提供器必须使用 Manager 已校验并写入 MDC 的权威值，覆盖业务代码中同名的非权威 Header，不得从请求体或其他 ID 重新选值。
7. 关联 Header 仅允许发送给本协议明确覆盖的 Runtime 和 Builder。其他内部服务必须另行定义契约；禁止发送给模型、插件或其他第三方。
8. MDC 中缺少应有字段时，不得由出站提供器临时生成或使用其他字段补值，应进入明确的异常处理。

### 3.6 上下文生命周期

通用规则：

- 每个入口只建立一次上下文；后续代码只能读取或传播已经确定的值，不得重新选择关联 ID。
- 使用 token、可关闭 scope 或上下文快照成对恢复；正常、异常、超时和取消路径均必须执行。
- 线程池任务开始时先保存工作线程原上下文，安装任务快照；结束时恢复工作线程原值，不得仅调用 `clear()` 破坏嵌套上下文。
- 只传播当前服务适用且本协议已定义的字段，禁止复制未知 MDC 或 ContextVar 集合。
- `task_id` 和 `job_id` 不进入通用 MDC 或 ContextVar，只作为后续方案冻结的结构化任务事件显式参数传入。

#### Manager

- HTTP 请求入口使用可关闭的 MDC scope，建立 `request-id`、`trace_id` 以及当前接口适用的 `execution-id`、`conversation-id`；结束时恢复旧值或删除本次新值。
- 当前请求的异步延续只捕获 `request-id`、`trace_id` 以及适用的 `execution-id`、`conversation-id`。承载这类任务的 `ThreadPoolTaskExecutor` 必须使用能捕获、安装并恢复 MDC 的 `TaskDecorator`。
- `CompletableFuture` 必须显式使用上述包装后的 executor，不得依赖默认 ForkJoinPool 传播 MDC。
- OkHttp SSE 回调运行在 dispatcher 线程，必须在 Listener 构造时捕获允许的上下文快照，在每个回调入口安装，并在回调结束时恢复 dispatcher 线程原上下文。
- 延迟执行、定时调度或恢复的独立后台任务不得继承调度线程或历史 HTTP 请求的 MDC；必须在任务入口从持久化数据恢复可沿用的 `execution_id`、`conversation_id`，并为本次顶层任务建立 `request_id` 和 `trace_id`。`task_id` 仍为显式业务参数，不写入 MDC `execution-id`。

#### Runtime

- `RequestContextMiddleware` 是请求上下文的唯一建立点；同一个已确定上下文同时供 `request.state` 和请求 ContextVar 使用，路由、执行器和异常处理器不得建立第二套上下文。
- 每条相关 `LogRecord` 必须从请求 ContextVar 注入 `trace_id`、`execution_id`、`request_id` 和 `conversation_id`；不适用的字段保持为空，不得沿用其他请求的值。
- `_request_ctx.set(ctx)` 和 `set_session_id(trace_id)` 必须分别保存 token，并在 `finally` 中按与建立相反的顺序调用公开的 reset 方法。
- 禁止用 `set_session_id("default_trace_id")` 伪装清理，禁止直接操作日志库私有 ContextVar。
- 如异步任务超过 HTTP 请求生命周期，必须使用显式且只读的上下文快照，不得继续引用请求结束后的可变 `request.state` 或上下文对象。

#### Builder

- FastAPI middleware 是 FastAPI 请求上下文的唯一建立点；必须保存 ContextVar token，并在 `finally` 中 reset。
- Flask `before_request` 是 Flask 请求上下文的唯一建立点；必须将 token 放入 `g`，并由 `teardown_request` 负责 reset。
- 每条相关 `LogRecord` 必须从当前 ContextVar 注入 `trace_id` 和 `request_id`；日志初始化必须使日志写入第 4.2.1 节规定的采集目录。
- Prompt 优化或 MMAPO 后台线程作为创建请求的异步延续时，必须通过 `contextvars.copy_context().run` 传播 `request_id`、`trace_id`；如依赖 Flask request context，同时组合 `copy_current_request_context`。`copy_current_request_context` 不能代替日志 ContextVar 的复制和恢复。
- `job_id` 不写入通用 ContextVar，只作为结构化 Job 事件的显式参数。查询、停止、重启和删除请求使用各自入口建立的 `request_id`、`trace_id`，再通过相同 `job_id` 关联，不沿用创建请求的上下文。

---

## 4. 统一日志格式

### 4.1 改造前现状（仅作为背景）

| 服务 | 日志类别 | 当前主要布局 | 当前文件 |
|---|---|---|---|
| Manager | main | 时间、级别、request-id、task-id、线程、logger、message；无会话和 trace 槽 | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` |
| Runtime | workflow/graph/llm/sys_operation | <code>time&#124;log_type&#124;file:line&#124;func&#124;trace_id&#124;execution_id&#124;request_id&#124;level&#124;msg</code> | `/opt/cloud/logs/jiuwen.log/**` |
| Builder | common/interface/performance | <code>time&#124;log_type&#124;trace_id&#124;level&#124;msg</code>，且部分代码仍写 `./logs/` | `./logs/` |

本节只用于说明平台日志改造前的代码现状，不作为采集器设计输入。采集器只需按后续目标格式设计，不承担旧格式识别和兼容责任。

### 4.2 目标格式

目标日志分为“固定外层布局”和“带固定前缀的结构化消息”两层。固定外层承载通用关联字段；结构化消息承载 access、performance、N2L 以及后续任务事件字段。采集器必须先解析外层，再仅对已冻结前缀的 `message` 解析 JSON。

#### 4.2.1 固定外层布局

| 服务 | `log_kind` | 目标布局 | 目标文件 |
|---|---|---|---|
| Manager | `main` | `[%d] [level] [request-id] [execution-id] [conversation-id] [trace_id] [thread] [logger:L] - [msg]` | `/opt/cloud/studio-manager/logs/studio-agent-manager.log` |
| Manager | `access` | 与 Manager `main` 外层相同，`msg` 为 `[AccessLog] {JSON}` | 混入 Manager main |
| Manager | `performance` | `[%d] [level] [request-id] [execution-id] [conversation-id] [trace_id] - [msg]` | `/opt/cloud/studio-manager/logs/perform.log` |
| Manager | `audit` | 单行 JSON（以下仅为换行展示）：<br><code>{"timestamp":"...","level":"...",</code><br><code>"request_id":"...","trace_id":"...",</code><br><code>"operation_type":"...","resource_type":"...",</code><br><code>"success":true,"message":"...",</code><br><code>"resource_id":"...","resource_name":"...",</code><br><code>"method":"...","user_id":"...",</code><br><code>"user_name":"...","error_code":"..."}</code><br>`resource_id`、`resource_name`、`method`、`user_id`、`user_name`、`error_code` 为可选字段 | `/opt/cloud/studio-manager/logs/audit/trace.log` |
| Runtime | `common` / `access` | <code>time&#124;log_type&#124;file:line&#124;func&#124;trace_id&#124;execution_id&#124;request_id&#124;conversation_id&#124;level&#124;msg</code> | `/opt/cloud/logs/common.log` |
| Runtime | `workflow` / `graph` / `llm` / `sys_operation` | <code>time&#124;log_type&#124;file:line&#124;func&#124;trace_id&#124;execution_id&#124;request_id&#124;conversation_id&#124;level&#124;msg</code> | `/opt/cloud/logs/jiuwen.log/workflow.log`、`graph.log`、`llm.log`、`sys_operation.log` |
| Runtime | `performance` | <code>time&#124;log_type&#124;trace_id&#124;execution_id&#124;request_id&#124;conversation_id&#124;level&#124;msg</code> | `/opt/cloud/logs/jiuwen.log/performance/jiuwen_performance.log` |
| Builder | `common` | <code>time&#124;log_type&#124;file:line&#124;func&#124;trace_id&#124;request_id&#124;level&#124;msg</code> | `/opt/cloud/logs/agent-builder/run/jiuwen.log` |
| Builder | `interface` | 与 Builder `common` 外层相同 | `/opt/cloud/logs/agent-builder/interface/jiuwen_interface.log`、`jiuwen_prompt_builder_interface.log` |
| Builder | `performance` | 与 Builder `common` 外层相同 | `/opt/cloud/logs/agent-builder/performance/jiuwen_performance.log` |

固定位从 0 开始：

- Manager `main` / `access`：`0=time, 1=level, 2=request_id, 3=execution_id, 4=conversation_id, 5=trace_id, 6=thread, 7=logger:line, 8=msg`。
- Manager `performance`：`0=time, 1=level, 2=request_id, 3=execution_id, 4=conversation_id, 5=trace_id, 6=msg`。
- Runtime `common` / `access` / `workflow` / `graph` / `llm` / `sys_operation`：`0=time, 1=log_type, 2=file:line, 3=func, 4=trace_id, 5=execution_id, 6=request_id, 7=conversation_id, 8=level, 9=msg`。
- Runtime `performance`：`0=time, 1=log_type, 2=trace_id, 3=execution_id, 4=request_id, 5=conversation_id, 6=level, 7=msg`。
- Builder `common` / `interface` / `performance`：`0=time, 1=log_type, 2=file:line, 3=func, 4=trace_id, 5=request_id, 6=level, 7=msg`。

Manager `audit` 的目标 JSON 必须分别输出 `request_id` 和 `trace_id`，不得继续用一个 `traceId` 承载 `request_id`。必填字段为 `timestamp`、`level`、`request_id`、`trace_id`、`operation_type`、`resource_type`、`success`、`message`；`resource_id`、`resource_name`、`method`、`user_id`、`user_name`、`error_code` 为可选字段。默认不输出完整方法参数或请求体。

解析管道日志时，`msg` 取冻结前缀位之后的全部剩余文本；正文中的 `|` 不得造成再次拆分。Python traceback 必须与首行合并后作为同一事件处理。

#### 4.2.2 结构化消息

**通用消息格式**

保留前缀的精确形式为 `[AccessLog] `、`[PERF_EVENT] ` 和 `[N2L_EVENT] `，右方均包含一个结尾空格。前缀后必须是一个 JSON object，不得是数组、字符串、数字、布尔值或 `null`。JSON 禁止重复 key 和未登记字段；字符串中的换行必须转义，不得破坏单行日志边界。

应用必须通过后续方案定义的专用封装产生保留前缀消息。普通日志中的用户输入、异常文案或下游响应不得原样作为以保留前缀开头的 `message`，避免伪造平台事件。结构化消息不得包含完整请求体、模型输入输出、Token、密码或自定义敏感 Header。

**Access 事件**

Manager access 使用 `[AccessLog] {JSON}`。JSON 必填 `event`、`method`、`route`、`status_code`、`duration_ms`、`result`；`event` 固定为 `access`，`method` 和 `route` 为非空字符串，`status_code` 为 100 至 599 的严格整数且拒绝 bool，`duration_ms` 为有限非负数且拒绝 bool，`result` 只允许 `success`、`failure`。`error_code` 仅在 `result=failure` 时可选。采集器根据前缀将 Manager main 文件中的该记录归一为 `log_kind=access`。

**Performance 事件**

三服务性能事件统一使用 `[PERF_EVENT] {JSON}`。JSON 必填 `event`、`operation`、`phase`、`duration_ms`、`result`；`event` 固定为 `performance`，`operation` 和 `phase` 为非空稳定标识，`duration_ms` 为有限非负数且拒绝 bool，`result` 只允许 `success`、`failure`、`cancelled`。`error_code` 仅在 `result=failure` 时可选。各服务的 `operation`、`phase` 注册表、必须埋点范围和生成点需在后续需求及方案设计中冻结；本节只冻结通用外层和基础 schema。

**N2L 事件**

Builder N2L 使用 `[N2L_EVENT] {JSON}`，规则如下：

- **基础字段**：必填 `event`、`conversation_id`、`phase`、`status`。`event` 固定为 `n2l_chat`；`conversation_id` 等于合法 URL `{cid}`；`phase` 只允许 `start`、`message`、`end`、`error`、`cancel`。
- **阶段与状态**：`start`、`message`、`end` 对应 `status=ok`；`error` 对应 `status=error`；`cancel` 对应 `status=cancelled`。
- **事件序列**：每次请求只允许 `start -> end`、`start -> message -> end`、`start -> error`、`start -> message -> error`、`start -> cancel` 或 `start -> message -> cancel`。`start` 和终态各至多一条，三个终态互斥；`message` 是整次请求的汇总事件，至多一条。
- **阶段含义**：`start` 表示流开始实际生成；请求在进入流生成前即被拒绝时不输出该事件。请求至少发送过一条非空业务消息时，在终态前输出一条汇总 `message`；`end`、`error`、`cancel` 分别表示成功结束、失败结束和取消结束。
- **条件字段**：`phase=message` 时必须同时包含严格整数且 `>=1` 的 `message_count`，以及有限非负数 `first_message_latency_ms`，两者均拒绝 bool；其他 phase 禁止出现这两个字段。`phase=error` 时可选 `normalization_failure_reason`，只允许 `unknown_item_type`、`invalid_schema`、`unregistered_message_type`、`reserved_message_type`、`non_json_value`、`invalid_control_schema`，其他 phase 禁止出现。

**尚未冻结的任务事件**

`task_id` 和 `job_id` 不占固定外层位。它们仅能从后续需求及方案设计冻结的结构化任务事件中提取；在该方案冻结前，采集结果中两字段保持缺失或 `null`。无已知前缀的 `msg` 按普通文本保留，不对其中的 `key=value`、`taskId`、`jiuwenTaskId` 或其他名称做语义猜测。

**采集解析结果**

结构化消息统一按以下结果处理：

- 固定外层和结构化 JSON/schema 均合法：`parse_status=parsed`，提取已登记字段。
- 固定外层合法，但已知前缀后的 JSON 损坏或 schema 非法：`parse_status=partial`，不提取该 JSON 字段。
- 固定外层无法解析：`parse_status=unparsed`。
- 三种情况均保留经安全处理的原始 `message`，不得静默丢弃。

### 4.3 格式样例

Manager main：

```text
[2026-08-13 10:00:00.123] [INFO ] [req-9f3a] [exec-7c1d] [conv-abc] [tr-550e] [http-nio-1] [AgentServiceProxyService:42] - [workflow stream started]
```

Runtime workflow：

```text
2026-08-13,123|workflow|middleware.py:138|dispatch|tr-550e|exec-7c1d|req-9f3a|conv-abc|INFO|workflow stream started
```

Builder common：

```text
2026-08-13,200|common|server_fastapi.py:88|set_trace_id|tr-550e|req-9f3a|INFO|trace context set
```

Runtime performance：

```text
2026-08-13,300|performance|tr-550e|exec-7c1d|req-9f3a|conv-abc|INFO|[PERF_EVENT] {"event":"performance","operation":"node_executed","phase":"llm","duration_ms":120.5,"result":"success"}
```

Runtime performance 使用独立布局，采集器不得套用 Runtime common/workflow 的字段位置。

Manager access：

```text
[2026-08-13 10:00:00.400] [INFO ] [req-9f3a] [] [] [tr-550e] [http-nio-1] [AccessLogFilter:88] - [[AccessLog] {"event":"access","method":"POST","route":"/v1/{project_id}/workflows/{workflow_id}/execute","status_code":200,"duration_ms":15.2,"result":"success"}]
```

Manager audit：

```json
{"timestamp":"2026-08-13T10:00:00.500Z","level":"INFO","request_id":"req-9f3a","trace_id":"tr-550e","operation_type":"UPDATE","resource_type":"WORKFLOW","resource_id":"wf-1","success":true,"message":"workflow updated"}
```

Manager performance：

```text
[2026-08-13 10:00:00.600] [INFO ] [req-9f3a] [exec-7c1d] [conv-abc] [tr-550e] - [[PERF_EVENT] {"event":"performance","operation":"workflow_execute","phase":"end","duration_ms":130.2,"result":"success"}]
```

Builder N2L common：

```text
2026-08-13,700|common|n2l.py:120|chat|tr-550e|req-9f3a|INFO|[N2L_EVENT] {"event":"n2l_chat","conversation_id":"conv-abc","phase":"message","status":"ok","message_count":1,"first_message_latency_ms":85.4}
```

---

## 5. 采集与归一契约

### 5.1 统一入库字段

| 字段 | 类型 | 产生方 | 适用范围 | 必填规则 | 归一与缺失处理 |
|---|---|---|---|---|---|
| `service` | string | 采集器 | 全部日志 | 必填 | 从部署元数据补充；应用不得伪造 |
| `host` | string | 采集器 | 全部日志 | 必填 | 从采集 Source 或部署元数据补充 |
| `log_kind` | string | 应用与采集器 | 全部日志 | 必填 | 按第 4.2.1 节的文件、日志类别及已冻结前缀确定，不从自由文本猜测 |
| `level` | string | 应用 | 全部日志 | 必填 | 从固定外层或 Manager audit JSON 提取并归一大小写 |
| `timestamp` | timestamp | 应用 | 全部日志 | 必填 | 从固定外层或 Manager audit JSON 提取；统一时区和存储格式由采集方案规定 |
| `trace_id` | string | 应用 | 三服务 | 条件必填 | 固定外层槽位必须存在；请求及独立后台任务相关日志必须有值，明确不属于请求或任务上下文的应用生命周期日志允许为空；只校验和改名，不得派生 |
| `request_id` | string | 应用 | 三服务 | 条件必填 | 固定外层槽位必须存在；请求及独立后台任务相关日志必须有值，明确不属于请求或任务上下文的应用生命周期日志允许为空；只校验和改名，不得派生 |
| `execution_id` | string | 应用 | Manager、Runtime | 条件必填 | 当前日志不涉及执行时为空；Builder 缺失或为 `null`，不得补值 |
| `conversation_id` | string | 应用 | Manager、Runtime 的会话相关日志及 Builder N2L | 条件必填 | Manager、Runtime 从固定外层提取；Builder 仅从合法 `[N2L_EVENT]` 提取；其他记录缺失或为 `null` |
| `job_id` | string | 应用结构化事件 | Manager、Builder 的 Builder Job 相关日志 | 可选 | 结构化任务事件方案冻结前缺失或为 `null`；不得从自由文本推断 |
| `task_id` | string | 应用结构化事件 | Manager Workflow 异步任务相关日志 | 可选 | 结构化任务事件方案冻结前缺失或为 `null`；不得从 MDC 或自由文本推断 |
| `operation` | string | 应用结构化事件 | Performance 事件 | 条件必填 | 仅从合法 `[PERF_EVENT]` 提取；其他记录缺失或为 `null` |
| `phase` | string | 应用结构化事件 | Performance、N2L 事件 | 条件必填 | 仅从合法结构化事件提取；取值按对应事件契约校验 |
| `duration_ms` | number | 应用结构化事件 | Access、Performance 事件 | 条件必填 | 必须为有限非负数并拒绝 bool；其他记录缺失或为 `null` |
| `result` | string | 应用结构化事件 | Access、Performance 事件 | 条件必填 | 仅从合法结构化事件提取；取值按对应事件契约校验 |
| `message_count` | integer | 应用结构化事件 | N2L `phase=message` | 条件必填 | 必须 `>=1` 并拒绝 bool；其他 N2L phase 及非 N2L 记录缺失或为 `null` |
| `first_message_latency_ms` | number | 应用结构化事件 | N2L `phase=message` | 条件必填 | 必须为有限非负数并拒绝 bool；其他 N2L phase 及非 N2L 记录缺失或为 `null` |
| `normalization_failure_reason` | string | 应用结构化事件 | N2L `phase=error` | 可选 | 仅允许第 4.2.2 节枚举；其他 phase 和非 N2L 记录缺失或为 `null` |
| `error_code` | string | 应用 | Access、Performance、audit 及其他相关错误日志 | 可选 | 仅从已登记结构化字段提取；不得从异常文案猜测 |
| `downstream_service` | string | 应用结构化错误事件 | 直接下游调用失败的内部诊断日志 | 可选 | 只允许 `runtime`、`builder`、`external`；结构化错误事件方案冻结前缺失或为 `null`，不得从自由文本推断 |
| `downstream_error_code` | string | 应用结构化错误事件 | 直接下游返回可识别错误码的内部诊断日志 | 可选 | 必须与 `downstream_service` 配套；结构化错误事件方案冻结前缺失或为 `null`，不得从 HTTP 状态或响应文本推断 |
| `parse_status` | string | 采集器 | 全部日志 | 必填 | 只允许 `parsed`、`partial`、`unparsed`，按第 4.2.2 和 5.2 节确定 |
| `observability_version` | string | 构建、部署流水线与采集器 | 全部日志 | 应提供 | 采集器从可信部署元数据补充；无法确认时缺失或为 `unknown`，不得推断 |
| `error_code_format` | string | 采集器 | 存在且可分类的 `error_code` | 条件必填 | 只允许 `canonical8`、`legacy6`、`legacy_symbolic`、`legacy_other`；无错误码或无法分类时缺失 |
| `message` | string | 应用 | 全部日志 | 必填 | 保留安全处理后的完整消息；管道正文中的 <code>&#124;</code> 不得导致再次拆分 |

其中两个入库元数据字段的可信来源进一步规定如下：

- `observability_version`：表示产生日志的服务构建产物遵循哪一版可观测性协议。同一个服务镜像部署出的所有实例必须使用相同值；该字段不用于区分实例、环境或部署批次。
  - 本次冻结版本的标准值为 `v1.2`；构建产物只有在满足本协议 v1.2 的适用条款后才能声明该值。
  - 构建流水线确定该值，并写入与镜像 digest 绑定的构建清单；禁止部署人员为同一镜像任意指定不同值。
  - 部署流水线从构建清单取值，写入 Pod annotation `observability.openjiuwen.io/version`；非 Kubernetes 环境须提供语义等价的不可变部署元数据。
  - 采集器通过 Kubernetes metadata enrichment 读取该 annotation，并补充到入库记录；不得根据日志布局、镜像 tag、部署时间或采集器自身版本推断。
  - annotation 缺失、值为空或无法与构建产物可靠关联时，入库字段应缺失或为 `unknown`，不得猜测。
- `error_code_format`：表示当前 `error_code` 使用哪种编码格式。仅当错误码已在第 7 章治理清单登记且能够成功分类时由采集器写入，取值为 `canonical8`、`legacy6`、`legacy_symbolic` 或 `legacy_other`；没有错误码、未登记或无法分类时不得补造该字段。

### 5.2 字段归一规则

- Manager `execution-id` 归一为 `execution_id`，不是 `task_id`；不再支持历史 MDC key `task-id`。
- Manager、Runtime 和 Builder 按本协议对应 `service + log_kind` 的冻结外层解析；只对已冻结前缀的结构化消息解析 JSON，不使用自由文本或 `key=value` 猜测字段。
- `trace_id`、`request_id`、`execution_id` 和 `conversation_id` 由应用输出；采集器只校验和改统一字段名，不做语义派生。
- `service`、`host` 由部署元数据和采集 Source 补充，禁止应用伪造节点身份。
- `parse_status` 取 `parsed`、`partial`、`unparsed`；解析失败时保留经过安全处理的原始 `message`，不得静默丢弃。
- `job_id` 和 `task_id` 是两个独立可选字段；后续结构化任务事件方案冻结前，两字段保持缺失或 `null`。
- `downstream_service` 和 `downstream_error_code` 只能从后续方案冻结的结构化错误事件提取；方案冻结前保持缺失或 `null`，不得从异常文案、URL、HTTP 状态或原始响应正文猜测。
- Builder 非 N2L 记录的 `conversation_id` 保持缺失或 `null`；采集器不得将空字符串、`job_id`、`task_id` 或其他字段归一为会话 ID。
- Builder common 日志无 `[N2L_EVENT] ` 前缀时按普通日志处理，不尝试解析 N2L 字段；前缀及 schema 全部合法时提取 `conversation_id`、`phase` 及条件字段，标记 `parsed`；JSON 损坏、缺字段、枚举非法或条件字段位置/类型错误时不提取 N2L 字段，标记 `partial`。

### 5.3 敏感信息

应用侧先避免输出敏感值，采集侧再统一遮盖 `Authorization`、密码、Token、API key、access key、private key 和自定义敏感 Header。禁止记录完整请求体、模型输入输出、未脱敏 URL 参数和非法关联 ID 原值。N2L 的 `normalization_failure_reason` 只能记录稳定枚举值，不得包含原始输入、异常对象或其他敏感内容。

---

## 6. 错误响应契约

### 6.1 普通 HTTP 错误

本节适用于三服务所有尚未开始流式传输的对外 HTTP 错误，包括框架校验、路由处理、业务处理和未知异常。SSE 响应头发出前仍可按本节返回普通 HTTP 错误；响应头发出后必须按第 6.3 节处理。

目标响应的 `Content-Type` 为 `application/json`，结构统一为：

```json
{
  "error_code": "openjiuwen.02200001",
  "error_msg": "Workflow execution failed",
  "error_reason": "Runtime request timed out",
  "error_suggestion": "Retry later",
  "request_id": "req-9f3a",
  "details": []
}
```

| 字段 | 类型 | 必填规则 | 约束 |
|---|---|---|---|
| `error_code` | string | 必填 | 本服务对外稳定错误码。新码使用第 7.1 节的 canonical8 格式；已登记 legacy 码保持原值，不补零、不改义 |
| `error_msg` | string | 必填 | 面向调用方的简短错误说明，必须来自错误目录和 i18n 资源 |
| `error_reason` | string | 必填 | 对错误原因的安全说明；不得直接使用异常字符串或下游响应正文 |
| `error_suggestion` | string | 必填 | 调用方可以采取的安全、可执行建议；不得泄露内部实现信息 |
| `request_id` | string | 必填 | 从当前请求上下文取得，必须与响应 Header `X-Request-Id` 完全相同 |
| `details` | array | 可选 | 存在时必须是下述 `ErrorDetail` 对象数组；没有安全详情时应省略或输出空数组，不得输出 `null` |

`ErrorDetail` 结构固定为：

```json
{
  "error_code": "openjiuwen.02000001",
  "error_msg": "Invalid parameter: name"
}
```

`ErrorDetail.error_code` 和 `ErrorDetail.error_msg` 均为必填非空字符串。详情只用于表达已经登记且适合对外公开的子错误，不得包含异常堆栈、类名、文件路径、SQL、完整请求体、模型输入输出、下游原始响应或密钥等敏感内容；未通过安全映射的下游详情不得放入 `details.error_msg`。

HTTP 状态码必须取错误目录中该错误定义的 `http_status`，不得根据错误码字符串、异常文案或下游 HTTP 状态临时推断。下游状态只有在本服务映射规则明确允许时才能影响本服务的 `http_status`。

响应构建器必须一次性确定 HTTP 状态码、响应字段和响应 Header。`request_id` 不得在异常处理器中重新生成；如果请求携带的 `X-Request-Id` 非法，应使用入口已经生成的替代值，并在 Header 和 JSON 中返回同一个值。

旧客户端应忽略未知字段；服务不得删除已发布字段、改变字段类型或改变已发布错误码语义。统一响应结构不等于重编号：存量 legacy 码继续按第 7.1 节处理，新路径不得继续产生新的 legacy 码。

### 6.2 下游错误映射与内部诊断字段

本节适用于 Manager、Runtime 或 Builder 调用直接下游服务失败的场景。每个服务只处理和记录自己的直接下游：例如 Manager 调用 Runtime、Runtime 再调用 Builder 时，Manager 的直接下游是 Runtime，Runtime 的直接下游是 Builder。内部诊断字段不得随 HTTP 或 SSE 响应继续向上游传播。

| 字段 | 含义 | 对外可见性 |
|---|---|---|
| `error_code` | 当前服务经过透传判定或映射后确定的稳定错误码 | 按第 6.1 或 6.3 节输出 |
| `downstream_error_code` | 直接下游响应中可可靠识别的原始错误码 | 仅内部 descriptor 和后续冻结的结构化错误事件 |
| `downstream_service` | 直接下游类别，只允许 `runtime`、`builder`、`external` | 仅内部 descriptor 和后续冻结的结构化错误事件 |

下游错误按以下规则处理：

| 下游结果 | 当前服务 `error_code` | 内部诊断字段 | HTTP 状态来源 |
|---|---|---|---|
| 返回双方已登记且语义一致的错误码 | 可以沿用该码 | 记录直接下游类别和原始码 | 当前服务错误目录中对该码登记的 `http_status` |
| 返回未知码、未登记码或码义不一致 | 映射为当前服务已登记的依赖错误码 | 原始码可可靠识别且符合安全约束时记录，否则省略；记录直接下游类别 | 映射后错误码在当前服务错误目录中的 `http_status` |
| 响应缺少错误码、结构损坏或无法识别 | 映射为当前服务已登记的依赖错误码 | `downstream_error_code` 缺失或为 `null`；记录直接下游类别 | 映射后错误码在当前服务错误目录中的 `http_status` |
| 连接、超时、TLS、DNS 等传输失败 | 映射为当前服务已登记的对应依赖错误码 | `downstream_error_code` 缺失或为 `null`；记录直接下游类别 | 映射后错误码在当前服务错误目录中的 `http_status` |

下游错误码只有同时满足以下条件时才可以沿用为当前服务的 `error_code`：

1. 错误码已进入跨服务治理清单，并由唯一 `code_owner` 管理；
2. 当前服务已显式引用该错误定义，不是仅通过 `openjiuwen.` 前缀或位数判断；
3. 两端对错误语义和 `http_status` 的定义一致；
4. 当前服务能够使用自身错误目录和 i18n 资源生成安全的四段文案；
5. 对外返回不会暴露下游实现、租户信息或其他敏感数据。

任一条件不满足时必须映射为当前服务错误码。不得把下游 HTTP 状态码当作 `downstream_error_code`，不得从响应文本、异常字符串或 URL 猜测错误码；下游 HTTP 状态也不得绕过第 6.1 节直接成为当前服务响应状态。

响应适配器必须将“解析下游响应并形成内部错误 descriptor”与“选择传输出口”分开。同步 HTTP、代理响应和 SSE 可以复用解析与映射内核，但必须分别由普通 HTTP 构建器或流式错误适配器输出，不能在响应头发出后改写为普通 HTTP JSON。

`downstream_error_code` 和 `downstream_service` 必须进入内部 descriptor，但不得进入普通 HTTP JSON、`details` 或 SSE 对外事件。它们只有通过后续方案冻结的结构化错误事件才能进入第 5.1 节的统一入库字段；在该方案冻结前，采集结果保持缺失或 `null`，不得从自由错误日志提取。原始下游响应正文不得写入 descriptor 的对外文案或结构化日志字段。

### 6.3 SSE 错误

SSE 响应头发出前发生的错误按第 6.1 节返回普通 HTTP 错误。响应头或任一 SSE 帧发出后，HTTP 状态和响应 Header 已不能修改，只能由流式错误适配器生成错误终态。

SSE 传输层的 `event: error` 行与 `data:` JSON 中的 `event="error"` 是两个不同层次：

- 已发布接口可以继续使用命名 SSE 事件，也可以继续使用未命名 `data:` 帧，不得在未完成客户端兼容评估时改变既有 framing。
- 所有接口均以 `data:` 解码后的 JSON 业务 envelope 作为错误语义的权威表示，其 `event` 必须为 `error`。
- 使用命名 SSE 事件时，传输层事件名也必须为 `error`，不得与 JSON 中的 `event` 冲突。

统一的最小业务 envelope 为：

```json
{
  "event": "error",
  "data": {
    "error_code": "openjiuwen.02200001",
    "error_msg": "Workflow execution failed",
    "error_reason": "Runtime request timed out",
    "error_suggestion": "Retry later",
    "request_id": "req-9f3a"
  }
}
```

`data` 中五个字段均为必填非空字符串，字段语义、安全要求和 legacy 错误码规则与第 6.1 节一致；`request_id` 必须与该流响应 Header `X-Request-Id` 完全相同。`conversation_id`、`execution_id`、`createdTime` 和节点信息等已发布的接口上下文字段可以继续保留，但不得替代这五个字段，也不得改变错误映射结果。

已发布接口当前使用的 `code`、`message` 可以在兼容期作为别名与标准字段同时存在，但必须由同一个内部错误 descriptor 生成，禁止独立选码或直接写入异常字符串。新接口不得只输出 `code`、`message`；删除兼容别名必须经过客户端盘点、版本化迁移和兼容性测试。Builder N2L 的别名迁移及具体 wire 字段在 N2L SSE 专项方案中冻结。

错误事件是流的唯一失败终态：每个流最多输出一次；输出后必须停止业务消息，不得再发送成功 `END` 或其他成功终态。客户端取消和正常断开走取消或清理路径，不得转换为对外错误事件。若连接已经不可写，或错误事件序列化、发送失败，只记录安全的内部日志并关闭流，不得递归生成第二个错误事件。

Manager 代理 Runtime 或 Builder 流时，必须先复用第 6.2 节的解析与映射内核形成 Manager 错误 descriptor，再生成 Manager 对外 SSE 错误事件；不得原样转发未知下游错误结构、原始响应正文或异常字符串。`downstream_error_code`、`downstream_service`、异常堆栈、模型输入输出和其他敏感数据不得进入 SSE 对外事件。

### 6.4 错误处理组件与出口职责

三服务可以使用不同的类名和代码组织，但每个服务必须具备职责等价的以下组件：

| 组件职责 | 输入 | 输出与约束 |
|---|---|---|
| 错误目录 | 稳定错误定义 | 提供 `full_code`、`http_status`、i18n key、级别、owner 等第 7 章字段 |
| 错误 descriptor 构建 | 已知业务错误、框架错误或未知异常 | 形成一次确定的本服务错误码、HTTP 状态、安全文案、`request_id` 和可选内部诊断字段 |
| 下游响应适配 | 直接下游响应或调用异常 | 按第 6.2 节解析、沿用或映射，形成内部 descriptor；不得直接写响应 |
| HTTP 错误响应构建 | 已确定的 descriptor | 按第 6.1 节生成 HTTP 状态、Header 和 JSON，不再选码或读取原始异常 |
| SSE 错误事件构建 | 已确定的 descriptor | 按第 6.3 节生成错误终态，不复用普通 HTTP DTO 或写出方法 |
| 框架出口适配 | Filter、Interceptor、middleware、exception handler、路由或流式回调捕获的失败 | 将框架异常归类后交给 descriptor 构建及对应传输出口 |

普通 HTTP 和 SSE 必须共用错误目录、i18n、映射规则和 descriptor 语义，但分别使用 HTTP 与 SSE 输出构建器。内部 descriptor 不是对外 DTO；`downstream_*` 等内部字段不得因复用 descriptor 而进入对外响应。

**Manager 接入范围**

- 全局异常 handler、认证和工作空间等 Filter/Interceptor、Controller 或 Service 中的主动失败，以及 Prompt Engineering 等当前非统一响应出口，必须接入同一错误目录和 descriptor 构建流程。
- Feign、OkHttp、RestTemplate 和 WebClient 的 Runtime/Builder 失败必须先经过对应下游响应适配器；普通代理响应和 SSE 代理流复用映射结果，但分别走 HTTP 与 SSE 出口。
- Manager 的 HTTP 输出使用扩展后的 `ErrorRsp` 等价模型，必须包含第 6.1 节的 `request_id`；不得继续输出 `{status,message}`、裸字符串或未经映射的下游响应。

**Runtime 接入范围**

- `RequestValidationError`、`HTTPException`、已知业务异常、存储异常、Builder 调用异常和未知异常必须接入统一 descriptor 构建流程。
- 路由中主动返回的错误 `JSONResponse` 也必须由 HTTP 错误响应构建器产生，不得手写 `{error:...}`、`{code,message}` 或裸错误文本。
- Agent、Workflow、直接编排和其他 Runtime 流式接口的错误必须由 SSE 错误事件构建器产生。

**Builder 接入范围**

- FastAPI 和 Flask 可以保留各自的框架适配器，但必须共用同一 Builder 错误目录、descriptor 语义和映射规则。
- 框架校验、认证、模型服务、Prompt 优化、MMAPO、N2L 和未知异常均须接入；普通 HTTP 与 SSE 分别使用对应输出构建器。
- 基础业务异常必须由已知异常分支处理，不能退化为未知异常；N2L 的 wire 兼容和生成器收口按专项方案实施，但不得偏离第 6.3 节。

**禁止绕过与一次映射规则**

1. 错误在本服务边界只映射一次。下游适配器或本地异常映射器确定 descriptor 后，HTTP/SSE 输出构建器只能校验和序列化，不得再根据异常文本、HTTP 状态或错误码前缀重新选码。
2. 禁止 Filter、Interceptor、middleware、handler、路由、回调或业务代码手写对外错误 JSON/SSE，禁止直接返回 `str(exception)`、下游响应正文或堆栈。
3. 未知异常必须映射为本服务已登记的安全兜底码，同时在内部日志保留关联 ID；不得产生 `-1`、`internal_error` 或临时字符串码。
4. 同一失败不得由多个层级重复记录为多个对外错误终态；已写出响应的下层异常只能用于安全内部诊断和资源清理。

当前代码尚未完成上述收口：Manager `ErrorRsp` 尚无 `request_id`，Runtime 仍存在多种直接错误响应，Builder 的 FastAPI、Flask 和 N2L 仍使用不同错误结构。这些均是开发差距，不代表允许长期兼容的目标行为。

### 6.5 接口兼容与迁移

第 6.1 至 6.4 节定义最终必须达到的目标契约，不表示所有已发布接口可以无过渡地改变 wire 行为。迁移前必须按具体接口盘点前端、SDK、服务间调用、网关、自动化任务和外部调用方，并保存当前 HTTP/SSE 响应 fixture 作为兼容基线。

兼容性按以下规则判断：

| 变化 | 兼容性判断 | 迁移要求 |
|---|---|---|
| 增加 `request_id` 或其他标准字段 | 通常为增量兼容，但严格 schema 客户端可能失败 | 验证消费者能忽略未知字段后原位增加；否则使用版本化响应 |
| 将缺失或 `null` 的字段改为必填非空 | 可能不兼容 | 先由统一构建器稳定补齐并完成消费者回归，再将其作为强制验收项 |
| 改变 `details` 的省略、`null`、空数组行为 | 可能不兼容 | 存量接口在迁移期保持原行为，或通过版本化契约切换；新接口直接遵循第 6.1 节 |
| 改变错误响应外层或字段类型 | 不兼容 | 必须版本化，或完成全部消费者协同迁移后同批切换 |
| 改变已发布错误码的值、前缀大小写或语义 | 不兼容 | 禁止原位修改；已发布码按精确字符串登记为 legacy，新码才使用 canonical8 |
| 改变 HTTP 状态码 | 行为不兼容 | 评估前端分支、网关、监控和重试策略；通过版本化或已批准的协同发布迁移 |
| SSE 同时增加标准字段并保留 `code`、`message` | 兼容期双写 | 标准字段与别名必须来自同一 descriptor，并提供一致性测试 |
| 删除 SSE legacy 字段或改变 `event:` framing | 不兼容 | 完成消费者盘点、版本化迁移和兼容性测试后才能执行 |
| 错误后停止发送成功 `END` | 状态机不兼容 | 先修正并验证客户端以 `error` 作为终态；无法同批迁移时使用版本化流式接口 |

错误码比较区分大小写。当前已经发布且被客户端使用的 `Openjiuwen.*`、其他大小写形式或 legacy 数字/符号码必须按原字符串登记和保留，不得仅为符合第 7.1 节的新码格式而改写；只有新登记的错误码使用 `openjiuwen.<8 位数字>`。

迁移必须遵循以下步骤：

1. 建立“服务、接口、传输类型、当前响应 fixture、消费者、目标变化、兼容等级、迁移方式”清单；未识别消费者的已发布接口按存在外部消费者处理。
2. 对只增加字段的变化，先验证客户端是否允许未知字段，再实施原位扩展；不能证明兼容时按不兼容变化处理。
3. 对不兼容变化选择新接口版本、显式协议版本或调用方与服务端同批切换，不允许服务端单边发布。
4. 兼容期允许标准字段与已发布别名双写，但必须同源且值一致；禁止维护两套独立选码和文案逻辑。
5. 使用契约测试同时覆盖当前 fixture 和目标 fixture，并观察未知字段解析失败、错误码分支、HTTP 重试及 SSE 终态异常。
6. 只有已登记消费者完成迁移、兼容观测无异常并经过评审后，才能删除 legacy 外层、字段或状态机行为。

安全要求不因兼容期而放宽。异常堆栈、下游原始响应、Token、模型输入输出或其他敏感信息必须停止对外输出，不得为兼容旧客户端继续双写；若安全修复必然改变接口行为，应按安全变更流程通知调用方并提供不泄露敏感信息的替代字段。

---

## 7. 错误码目录

### 7.1 新码格式与 legacy 分类

新登记错误码的 canonical 格式固定为：

```text
^openjiuwen\.[0-9]{8}$
```

八位数字由四位模块码和四位模块内码组成。错误码在代码、配置、manifest、日志和响应中始终按字符串处理，不得转换为整数，不得丢失前导零，也不得改变 `openjiuwen.` 的大小写。

不满足 canonical 格式但已经发布或被消费者使用的错误码均属于 legacy，包括六位数字码、其他位数的纯数字码、`Openjiuwen.*` 等不同大小写或服务前缀，以及 `internal_error`、`-1` 等符号码。legacy 码必须按已发布的精确字符串登记和保留，不补零、不拆分、不自动转小写、不改变语义；新接口和新错误定义不得继续创建 legacy 码。

错误码格式分类为：

| `code_format` | 判定 |
|---|---|
| `canonical8` | 精确匹配 `^openjiuwen\.[0-9]{8}$` |
| `legacy6` | 已登记且精确匹配 `^[0-9]{6}$` 的 legacy 码 |
| `legacy_symbolic` | 已登记、未命中 `legacy6`，且精确匹配 `^-?[0-9]+$` 或 `^[A-Za-z_][A-Za-z0-9_-]*$`，例如其他位数的纯数字、`-1`、`internal_error` |
| `legacy_other` | 已登记但不属于以上类别的其他格式，包括前缀大小写或位数不符合 canonical 规则的带前缀错误码 |

不得仅凭格式把未登记字符串认定为有效 legacy 码。

当前 Runtime 的 `121007` 是常量、事件轨迹和 i18n 查询使用的内部键；`ErrorContextBuilder` 在错误事件出口固定生成完整值 `openjiuwen.121007`。因此错误目录 `full_code`、内部 descriptor 和标准 `error_code` 字段的唯一精确值冻结为字符串 `"openjiuwen.121007"`，并按 `legacy_other` 登记。i18n 资源根键可继续使用 `"121007"` 作为内部查询键；已发布 SSE 的 legacy 别名字段 `code` 可按第 6.5 节在兼容期暂时保留数值 `121007`，但必须与标准字段来自同一 descriptor，且不得把该别名登记成第二个错误码。裸值 `"121007"` 不得作为 `error_code` 或 Manifest `full_code`，也不得补零、重编号或改成 canonical 码。

`openjiuwen.121007` 在 Manifest 中的 `http_status=500` 表示事件封装失败的语义状态。SSE 响应尚未开始时应使用 HTTP 500；SSE 已开始时运输层可保持 HTTP 200，但 `error` 事件必须携带该精确错误码。Builder 中的 `-1`、`internal_error` 等现有值仍必须先按精确字符串评审，是否继续对外兼容按第 6.5 节评估。

### 7.2 模块号段治理

| 模块码 | 模块 | 号段治理方 | 状态 | 说明 |
|---|---|---|---|---|
| `0200` | COMMON | Manager | 冻结 | Studio 通用能力 |
| `0210` | AGENT | Manager | 冻结 | 单智能体 |
| `0220` | WORKFLOW | Manager | 冻结 | 工作流 |
| `0230` | MULTI_AGENT | Manager | 冻结 | 多智能体 |
| `0240` | COMPONENT | Manager | 冻结 | 组件、插件、MCP 与提示词 |
| `0250` | MODEL | Manager | 暂定 | Manager/Builder 定义和 HTTP 状态冲突未收口 |
| `0260` | CONFIG | Manager | 冻结 | 配置管理 |
| `0270` | PROMPT_ENGINEERING | Manager | 冻结 | 提示词工程 |
| `0280` | ASSET | Manager | 冻结 | 资产中心 |
| `0290` | WORKSPACE | Manager | 冻结 | 团队空间 |
| `0300` | KNOWLEDGE_BASE | Manager | 冻结 | 知识库 |
| `0310` | ENVIRONMENT_MANAGER | Manager | 冻结 | 环境管理 |
| `0320` | LICENSE | Manager | 冻结 | License |
| `0330` | SHARE_RESOURCE | Manager | 暂定 | Manager/Runtime 存在同码异义冲突 |
| `0340` | MEMORY | Manager | 冻结 | 记忆管理 |
| `0350` | IMPORT | Manager | 冻结 | 导入 |
| `0360` | EXPORT | Manager | 冻结 | 导出管理 |
| `0370` | CODE_AGENT | Manager | 冻结 | 高代码智能体 |
| `1210` | RUNTIME_EXECUTION | Runtime | 预留 | 仅供未来 canonical 新码；`openjiuwen.121007` 是 legacy，不占用该号段分配 |

`module_steward` 管理模块号段及分配规则；`code_owner` 定义和维护具体错误码；`owning_module` 表示错误所属业务模块。号段治理方可以把具体码分配给其他服务，但同一 `full_code` 只能有一个 `code_owner`。

表中“冻结”状态与统一错误码 Manifest 的 `modules[].allocation_status=frozen` 同步；“暂定”号段完成冲突收口前不得新增对外错误码，“预留”号段不得提前分配。新增或变更模块码必须经过跨服务协议评审，并同版本更新本表和 Manifest。

### 7.3 错误定义字段

三服务导出的错误定义必须使用同构字段：

| 字段 | 类型 | 必填 | 约束 |
|---|---|---|---|
| `full_code` | string | 是 | canonical 新码或治理清单中精确登记的 legacy 码；全局唯一 |
| `code_format` | enum | 是 | `canonical8`、`legacy6`、`legacy_symbolic`、`legacy_other` |
| `name` | string | 是 | 稳定、非空的程序标识，不承担对外文案职责 |
| `summary_zh_cn` / `summary_en_us` | string | 是 | 可读目录使用的双语安全摘要，均不得为空 |
| `http_status` | integer | 是 | 400 至 599 的严格整数；同一错误码的所有引用必须一致。SSE 已开始后传输层保持 HTTP 200 不改变错误定义的语义状态 |
| `category` | enum | 是 | `system`、`business`、`security`、`dependency` |
| `code_owner` | enum | 是 | `manager`、`runtime`、`builder`；具体码唯一所有者 |
| `module_steward` | enum | 是 | 负责该模块号段治理的服务 |
| `owning_module` | string | 是 | 已登记的业务模块稳定标识 |
| `default_level` | enum | 是 | `DEBUG`、`INFO`、`WARN`、`ERROR`；表示默认日志级别 |
| `i18n_key` | string | 是 | 指向四段安全文案；支持语言必须具有完整资源 |
| `lifecycle_status` | enum | 是 | `active`、`deprecated`、`reserved` |
| `definition_source` | object | 是 | 至少包含仓库相对 `path` 和 `symbol`，用于追溯唯一代码定义 |
| `compatibility_note` | string | 否 | 已发布 legacy、别名或替代关系的安全说明 |
| `governance_authorization` | string | 条件必填 | definition 来源服务与 `code_owner` 不一致时，记录已评审授权；无授权必须拒绝 |

`active` 可以用于新响应；`deprecated` 只为兼容既有调用保留，不得用于新路径；`reserved` 尚未发布且不得对外返回。已发布错误码只能标记为 `deprecated`，不得删除后把同一码重新分配给其他语义。

### 7.4 定义、引用与兼容边界

治理清单必须区分：

- **definition**：仅由 `code_owner` 提供，包含第 7.3 节的完整字段和 i18n 资源；
- **reference**：其他服务声明自己会接收、沿用或映射该码，只引用 `full_code` 和预期 owner，不得复制一份独立定义。

服务引用其他服务拥有的码时，必须校验 owner、语义、`http_status` 和生命周期；是否可以对外沿用还必须满足第 6.2 节全部条件。legacy 码的精确字符串、大小写和既有语义受第 6.5 节兼容规则保护。

错误码不得因下游服务、接口或语言不同而改变语义。文案可以国际化，但不能用同一码表达不同原因；确需新语义时必须申请新码。

### 7.5 Manifest 与跨服务 CI 校验

根仓库必须维护轻量治理清单，或由 CI 汇总三服务导出的 manifest。manifest 必须记录协议版本和权威正文 SHA-256，并至少分为 `definitions` 和 `references`；协议版本或正文内容变化时必须经版本化评审并同步。CI 执行：

- 同一 `full_code` 出现多个 definition：失败；
- definition 的 `code_owner` 与导出服务不一致且无显式治理授权：失败；
- reference 指向未知码、错误 owner 或未登记模块：失败；
- canonical 新码格式错误、模块码未冻结或模块内码重复：失败；
- 缺少 `http_status`、category、默认级别、i18n 或生命周期：失败；
- 同一码在 definition 与 reference 中的 `http_status` 或语义声明冲突：失败；
- `deprecated` 码被新接口引用，或 `reserved` 码出现在运行时响应：失败；
- legacy 码未精确登记却出现在响应 fixture，或迁移过程改变其大小写和字符串值：失败。

CI 还必须校验第 6.1、6.3 和 6.5 节的 HTTP/SSE fixture，避免目录正确但实际出口仍产生临时码或不兼容响应。

治理可以先以提示式模式分批接入，但每批检查必须公开准确的覆盖矩阵；“相对基线新增为零”只表示已实现规则未发现增量，不等于上述全部规则已经实现。切换阻断模式前，必须补齐 legacy 引用、跨服务未声明引用、代码定义属性、HTTP/SSE fixture、生命周期使用和真实出口检查。

---

## 8. 性能事件与告警职责边界

### 8.1 性能事件适用范围

正式性能事件是第 4.2.2 节定义的 `[PERF_EVENT] {JSON}`，必须写入第 4.2.1 节对应服务的 `performance` 日志类别，并按固定外层和结构化消息两层解析。关联 ID 从固定外层取得，不在 JSON 中重复或推断。

Access 事件中的 `duration_ms` 属请求访问耗时；N2L `[N2L_EVENT]` 中的 `message_count` 和 `first_message_latency_ms` 属 N2L 可观测指标。二者都不因此成为 `log_kind=performance`，采集器必须按各自事件前缀和日志类别解析。

应用负责输出目标文件、外层布局和 `[PERF_EVENT]`；外部采集方案负责依据这些信息配置文件匹配、Source 和解析规则。本文不强制采集器内部采用独立 Source，但不得把不同外层布局套用同一位置解析规则。

### 8.2 计时、字段与结果规则

- `duration_ms` 单位固定为毫秒，必须是有限非负数并拒绝 bool。
- 同一测量范围的开始和结束必须使用同一种单调时钟：Java 使用 `System.nanoTime()`，Python 使用 `time.perf_counter()` 或等价单调时钟。墙上时钟只生成事件 `timestamp`，不得用于计算耗时。
- 毫秒换算和精度策略必须由公共事件封装统一；业务埋点不得各自混用秒、毫秒或纳秒，也不得自行产生负值、NaN 或 Infinity。
- `operation` 表示被测操作，`phase` 表示该操作中已经完成的测量阶段；合法组合必须来自后续冻结的服务注册表，不允许任意自由命名。
- 当前基础 schema 只描述已经完成的测量区间，每条事件都必须包含 `duration_ms` 和终态 `result`。如后续需要无耗时的 start 事件，必须先扩展协议 schema，不得复用当前格式省略必填字段。
- `result=success` 时禁止 `error_code`；`result=failure` 时可以携带已登记且适合该失败语义的 `error_code`；`result=cancelled` 时禁止用 failure 或错误码伪装取消。
- 同一测量范围只产生一个完成事件和一个结果。正常、失败和取消路径必须通过 `finally`、可关闭 scope 或等价机制收口，禁止重复结束或漏记。
- `task_id`、`job_id` 当前不属于 `[PERF_EVENT]` 基础 schema；需要关联任务性能时，必须在后续方案中显式扩展字段白名单和采集 fixture。

### 8.3 当前日志的改造边界

当前 Runtime 中的 `first_token<llm>|123`、`workflow_init|50` 等自由文本，以及其他服务现有的非统一 performance 消息，只是改造前代码现状，不是目标结构化事件。采集器不得从这些自由文本提取 `operation`、`phase`、`duration_ms` 或 `result`，也不承担兼容责任。

当前 Runtime performance logger 可能输出 `log_type=perf`，而目标协议固定为 `performance`；应用改造时必须统一 logger、formatter、配置和测试。采集器不得自行把 `perf` 当作目标 `performance` 的别名。

在 operation/phase 注册表和公共事件封装冻结前，现有自由文本不得仅通过添加 `[PERF_EVENT]` 前缀升级为正式事件。改造必须逐项确认测量边界、单位、结果和关联上下文，并提供正反例 fixture。

### 8.4 指标与告警职责

性能日志用于明细检索、离线分析和问题定位，不直接充当告警消息队列。告警由 Metrics、规则引擎和通知平台实现，不新增“告警日志”类别或“写日志即发送通知”的应用链路。

具体的指标名称、聚合维度、标签基数、阈值、统计窗口、抑制、通知路由和 SLO 不在本协议中冻结，必须在后续需求与方案设计中定义。指标实现可以消费应用埋点或独立测量，但不得改变本文的 ID 语义、安全边界和耗时口径。

性能事件和指标标签不得包含 Token、完整请求体、模型输入输出、未脱敏 URL 参数、错误堆栈或高基数自由文本。

---

## 9. 开发与验收清单

### 9.1 关联 ID

- [ ] 三服务入口按统一算法建立 `request_id` 和 `trace_id`。
- [ ] Manager 按恢复值、内部已选定执行参数、入站 Header、新 UUID 的顺序选择 `execution_id`，不回退为 `request_id`；Runtime 合法 Header 原样使用、缺失或非法才生成；Builder 不使用该字段。
- [ ] 删除 Manager 中 `request_id` 作为 `execution_id` 回退的改动，必须先于“单独部署或启用 Manager 入站 request_id 写入 MDC”；两项允许作为同一原子变更发布，但禁止出现只启用后者的中间版本。
- [ ] Runtime middleware 是每个请求中 `execution_id` 的唯一建立点；路由和执行函数只使用 `request.state`/ContextVar 中的值，不从请求体 `headers` 重读，也不生成第二个 UUID。
- [ ] Runtime 不再从 `conversation_id` 或 `execution_id` 派生 trace。
- [ ] Manager 的 Feign、OkHttp、RestTemplate 和 WebClient 使用同一 Header 注入器和 Runtime/Builder 目标白名单；`X-Execution-Id` 仅注入 Runtime 执行调用，不注入 Builder、查询调用或第三方调用。
- [ ] `conversation_id` 按服务规则建立：Manager/Runtime 常规会话接口使用路径，Runtime 直接编排接口使用 schema 校验后的请求体，Builder N2L 使用路径 `{cid}`；路径与兼容请求体值冲突时拒绝。
- [ ] Manager 只接受 URL 路径传入的 `conversation_id`，或在创建 Workflow 异步任务时自行生成；无会话 ID 的 Agent 无效接口应删除或禁用。
- [ ] Manager 将历史 MDC key `task-id` 的写入、读取、Log4j2 Pattern 和测试同批迁移为 `execution-id`，不保留混用。
- [ ] `task_id` 只由 Manager 创建 Workflow 异步任务时生成，只用于 Manager 任务生命周期；调用 Runtime 时不传递该值，不将 MDC `execution-id` 或 Builder N2L 局部变量归一为 `task_id`。
- [ ] Builder 非 N2L 功能不生成或借用 `conversation_id`，Prompt 优化和 MMAPO 任务使用 `job_id`；入库 `conversation_id` 缺失或为 `null`，不写空字符串，不用其他 ID 补值。
- [ ] MDC、ContextVar、异步线程、SSE 回调在正常、异常、超时和取消路径均成对恢复；线程池任务结束后恢复工作线程原上下文，不仅执行 `clear()`。
- [ ] Manager 区分请求异步延续与独立后台任务；后者不继承调度线程或历史请求 MDC，而是在任务入口建立新的顶层上下文。
- [ ] Runtime 和 Builder 的每种 HTTP 框架都只有一个请求上下文建立点；所有 token 按与建立相反的顺序 reset。
- [ ] `task_id` 和 `job_id` 不写入通用 MDC/ContextVar；结构化任务事件方案冻结前不从日志提取，方案冻结并纳入开发范围后才由专用事件显式承载。
- [ ] 并发请求、线程池复用和嵌套上下文测试证明无串号、无陈旧值。

### 9.2 日志与采集

**平台应用与构建产物验收：**

- [ ] 各 `service + log_kind` 严格使用对应冻结位。
- [ ] Manager main/access/performance 外层、Manager audit JSON、Runtime common/access/业务/performance 管道和 Builder common/interface/performance 管道均提供解析 fixture，覆盖空槽、正文分隔符和 traceback 合并；使用相同外层的类别可以共用 fixture，但必须分别覆盖日志类别判定。
- [ ] Manager audit 将历史 `traceId=request-id` 改为独立 `request_id` 和 `trace_id`，默认不记录完整方法参数或请求体。
- [ ] Runtime performance 包含 `conversation_id` 固定位；Builder common/interface/performance 全部使用同一冻结外层布局。
- [ ] 正式性能事件只接受 `log_kind=performance` 中的合法 `[PERF_EVENT]`；Access 和 N2L 指标按各自事件解析，不归类为 performance。
- [ ] 本期纳入改造范围的 Runtime `log_type=perf` 和三服务自由文本性能日志迁移为目标 `performance` 类别及 `[PERF_EVENT]`；未纳入本期的旧性能消息继续作为普通文本，不得仅添加前缀冒充正式事件。
- [ ] 本期纳入改造范围的性能事件具有已冻结的 operation/phase 注册表，并测试单调时钟、毫秒换算、有限非负耗时、三个 result 分支、错误码条件和单一完成事件；未纳入本期的性能埋点不要求本次迁移。
- [ ] 构建清单中的 `observability_version` 与镜像 digest 绑定，部署流水线将其写入 Pod annotation `observability.openjiuwen.io/version`；同一镜像的所有实例取值一致，无法确认时入库值为缺失或 `unknown`。
- [ ] Builder 日志写入采集目录，不再只写 `./logs/`。
- [ ] 应用输出测试覆盖保留前缀伪造、非法 JSON 数值、重复字段、真实换行和敏感信息，证明普通日志不能伪装为平台结构化事件。

**采集设计交付验收：**

- [ ] 平台日志格式改造时，同步交付各目标文件、字段位置、日志类别判定、结构化 schema、解析状态和正反例 parser fixture；交付内容与第 4、5 章逐字段一致。
- [ ] 采集设计只对 `[AccessLog]`、`[PERF_EVENT]`、`[N2L_EVENT]` 和以后已经冻结且纳入范围的事件前缀解析 JSON；无前缀自由文本以及未冻结的任务、下游错误事件不做字段猜测。
- [ ] 采集设计规定解析失败时保留安全 `message`，并通过 fixture 正确区分 `partial` 与 `unparsed`；不提供旧日志布局、`perf` 类别或自由文本性能消息的兼容解析。
- [ ] 采集设计包含敏感字段遮盖、伪造前缀和非法结构化消息的正反例 fixture。
- [ ] 平台仓库只验收采集设计要求和 fixture 的完整性，不以外部采集器代码已经实现或部署作为平台开发任务的完成条件。

### 9.3 错误处理

- [ ] canonical 新码精确匹配 `^openjiuwen\.[0-9]{8}$` 并始终按字符串处理，具体码所有者唯一。
- [ ] 所有 legacy 码按精确字符串和格式分类登记，不补零、不改义、不改变大小写；新路径不再产生 legacy 码。
- [ ] Runtime 将内部键 `121007` 在 descriptor 和标准 `error_code` 字段统一为 `"openjiuwen.121007"`；i18n 可保留内部根键 `"121007"`，兼容期 legacy `code=121007` 必须同源且有一致性测试。
- [ ] 错误定义包含第 7.3 节全部字段，生命周期符合 active/deprecated/reserved 规则；definition 与 reference 明确分离。
- [ ] 三服务构建器输出统一 HTTP 字段；五个必填字段均为非空字符串，`request_id` 与响应 Header `X-Request-Id` 完全相同。
- [ ] HTTP 状态码取错误目录的 `http_status`；框架校验、路由错误、业务错误和未知异常均通过统一构建器处理。
- [ ] `details` 缺失、空数组及合法 `ErrorDetail` 均有测试；原始异常、下游响应和敏感值不能进入对外详情。
- [ ] 下游错误测试覆盖认可码、未知码、缺失或损坏错误码及传输失败；最终 HTTP 状态均来自映射后错误定义。
- [ ] 下游诊断字段只记录直接下游并进入内部 descriptor，不进入普通 HTTP、`details` 或 SSE；结构化错误事件冻结前不从自由日志提取。
- [ ] 普通 HTTP 与 SSE 共用错误目录和映射内核，但保留各自传输外层；SSE `data:` JSON 的五个标准字段完整且 `request_id` 与响应 Header 一致。
- [ ] SSE 测试覆盖命名与未命名 framing、legacy 别名兼容、首帧前失败、首帧后失败、下游错误映射、客户端取消以及错误事件发送失败。
- [ ] 每个失败流最多一个错误终态；错误后不再发送业务消息、成功 `END` 或其他成功终态。
- [ ] 三服务均具备错误目录、descriptor 构建、下游适配、HTTP 构建、SSE 构建和框架出口适配等价职责；组件边界测试证明只映射一次。
- [ ] Manager、Runtime、Builder 本节列出的所有错误出口均已接入，不再手写错误 JSON/SSE、返回异常字符串或原样转发下游错误体。
- [ ] 每个已发布错误接口均有消费者、当前 fixture、目标变化和兼容等级清单；未知消费者按外部消费者处理。
- [ ] 增量字段经过严格 schema 客户端验证；不兼容的响应外层、错误码、HTTP 状态、SSE framing 和终态变化具有版本化或协同发布方案。
- [ ] 兼容期标准字段与 legacy 别名同源且值一致；legacy 删除具备消费者迁移完成和兼容观测证据。
- [ ] 安全敏感内容不因兼容要求继续对外输出，也不进入 legacy 双写字段。
- [ ] CI 能发现跨服务重复 definition、未知或错误 owner 引用、格式或号段错误、字段及 i18n 缺失、HTTP 状态冲突和非法生命周期使用。

### 9.4 N2L 可观测性

- [ ] N2L 路径 `{cid}` 的长度、字符集和请求体兼容字段一致性校验符合第 3 章定义，非法原值不进入日志。
- [ ] `[N2L_EVENT]` 覆盖有消息、无消息、首消息前后失败及取消，事件序列、phase/status 组合和数量约束符合第 4 章定义。
- [ ] `message_count`、`first_message_latency_ms` 和 `normalization_failure_reason` 的类型、出现条件、统计口径和安全边界均有正反例测试。
- [ ] Builder common 解析 fixture 覆盖无前缀、合法事件、非法 JSON、缺字段、非法枚举、额外字段和非法数值，并正确区分 `parsed` 与 `partial`。

---

## 10. 实施发布门槛

以下条件用于判断 Studio 2.0 可观测性改造能否进入生产发布，不作为本协议完成设计审视和冻结的前置条件。协议冻结后，实施不得改变已经冻结的语义；尚未冻结的专项方案只有在完成设计评审并明确纳入本期范围后，才成为本次实施发布的必达项。

1. 三服务入口、出站、异步传播和清理均有自动化测试，`trace_id` 只有单一语义。
2. 平台应用输出满足目标日志格式；构建产物稳定提供 `observability_version`；采集设计要求和 parser fixture 已完成评审并与目标格式逐字段一致。外部采集器的实际实现、部署和上线验收由其所属团队负责，不属于平台仓库开发完成条件。
3. 三服务现有错误码完成全量盘点，模块号段状态与 Manifest 一致；definition、reference、owner、i18n、生命周期和 legacy 精确分类明确；Runtime 内部 `121007` 在 descriptor 和标准 `error_code` 字段统一为 `"openjiuwen.121007"`，兼容别名 `code=121007` 同源可验证，不补零、不改码。
4. 跨服务错误码 manifest 或治理清单及第 7.5 节 CI 校验可运行，并能阻止未登记码、重复定义、非法引用和不兼容 legacy 变化进入发布版本。
5. 普通 HTTP、SSE、下游映射和未知异常的安全边界通过联调；第 6.4 节列出的三服务错误出口全部接入统一 descriptor 流程，SSE framing、标准错误字段、legacy 别名和唯一错误终态符合第 6.3 节；第 6.5 节的消费者清单、兼容测试和不兼容变更迁移方案已经评审。
6. N2L 可观测事件状态机、条件字段、统计口径和采集设计 fixture 通过测试；SSE 消息归一与生成器资源回收只有在专项方案冻结并纳入本期实施范围时，才要求在本次发布前完成真实异步测试。
7. 本期纳入的性能事件具有冻结的 operation/phase 注册表、公共封装和 parser fixture，并符合第 8.2 节计时及结果规则；未纳入本期的旧性能消息保持普通文本，采集设计不会把自由文本或 `perf` 类别识别为目标事件。
8. 尚未冻结的结构化任务事件和下游错误事件不作为本次发布必达能力；在其方案冻结前，`task_id`、`job_id` 和 `downstream_*` 不得从自由文本或未登记结构中提取。
9. 应用日志脱敏、非法输入不回显和结构化前缀防伪通过安全验收；采集设计包含失败保留、安全遮盖和正反例 fixture。Metrics 告警实现不属于本期发布门槛，但本期产生的性能事件和指标不得违反第 8 章的字段、计时和安全边界。

本文的协议性修改必须评审并更新版本号。实现可以调整内部类名和代码组织，但不得改变本文冻结的字段语义、Header、日志位、错误响应和 N2L 可观测事件状态机；如确需改变，必须先修改本协议并完成兼容性评估。协议审视结果、冻结日期和内容校验值在设计修改记录中管理，与本章的实施发布判定分开。

`v1.2` 将长期权威正文迁入 `agent-studio` 仓库，明确关联字段“槽位必备、值条件必填”，把目标日志文件收口为精确路径，将错误定义 HTTP 状态限制为 4xx/5xx，并补齐 Manifest 实际使用的追溯与目录展示字段；Runtime `openjiuwen.121007` 及既有 ID、Header、错误响应 wire 语义不变。
