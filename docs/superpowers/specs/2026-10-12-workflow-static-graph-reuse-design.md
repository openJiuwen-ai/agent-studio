# Workflow 静态图复用与实例缓存设计（L1）

- 关联 issue: [GitCode openJiuwen/agent-studio #1555](https://gitcode.com/openJiuwen/agent-studio/issues/1555)
- 日期: 2026-10-12
- 分支: `feature/workflow-static-graph-reuse`（基于 `studio-2.0-dev` @ `907e6c2e5`）
- 状态: 待评审
- 交付范围: **L1 完整实现**——patch 三件套 + 组件全量无状态化 + 进程内实例缓存 + 配置开关（默认 off）+ 指标 + 结构断言自动降级。发布后零行为变化；L0（收益量化）与 L2（灰度切换）不在本设计范围。

## 1. 背景与问题

Workflow 执行链路中，`build_openjiuwen_workflow_from_ir`（`agent-runtime/jiuwen/serve/controllers/execution/ir_converter.py:1659`）每个请求都完整重建一次工作流图（组件实例化、pydantic 校验、连接/分支/并行 join 注册），即使同一份已发布 IR 被高频执行也无法复用。大图（多 LLM/子工作流/循环节点）的构建开销直接叠加到每个请求的首 token 延迟上（现有埋点 `ir_build_total` 可观测）。

根因：openjiuwen 执行引擎的对象模型是"图实例 = 图结构 + 会话运行态"的混合体，一次执行一个实例是当前最安全的用法——引擎把会话状态缓存在图实例上（`PregelGraph.compile` 首次 compile 绑定 `self.pregel/checkpointer/_session`，后续只换 `_session` 引用），Vertex 携带 `asyncio.Future` 与调用计数，组件实例覆写 `self._session`。因此直接缓存 Workflow 实例会导致跨会话 checkpoint 泄漏与并发污染。

解决思路（issue 已定稿，本文档细化）：**静态图模板 + 每次执行轻量物化**——缓存构建的贵重产物（组件实例、图结构、模型客户端），把每次执行会变的状态挪到 per-execution 对象和 ContextVar。不改 openjiuwen 包（安装依赖，版本 0.1.19，git develop 源），沿用仓库 monkey-patch 惯例。

## 2. 现状验证结论（设计依据）

以下结论已在 `studio-2.0-dev` @ `907e6c2e5` 与 venv 内 openjiuwen 0.1.19 逐一核实。行号为当前分支实测（issue 原文基于 `studio-2.0`，行号漂移 20~106 行，以本文档为准）。

### 2.1 每请求执行链路（现状）

| 步骤 | 位置 | 缓存情况 |
|---|---|---|
| ① 加载 IR dict | `async_ir_load`（`jiuwen/serve/controllers/execution/open_utils.py:671`，uncached 在 :692） | ✅ 请求级 memo + memory→redis→obs 三级缓存（仅 published IR 回写，`open_utils.py:748-749`） |
| ② extract_node_defs | `ir_converter.py:1018`（生产调用点 `workflow_runner.py:329`） | ❌ 每请求递归执行 |
| ③ IR 引用转换 + LazyWorkflow 壳 | `async_ir_to_workflow`（`ir_converter.py:1638-1656`） | COW 已优化，开销小 |
| ④ 首次 stream() 触发建图 | `lazy_workflow.py:116-118` → `build_openjiuwen_workflow_from_ir` | ❌ 每请求完整重建 |

`WorkflowRunner.run_streaming`（`agent_runtime/runner/workflow_runner.py:284`）：:304 加载 IR → :329 提取 node_defs → :337-345 调 `async_ir_to_workflow`（从 `_request_ctx` ContextVar 取 `cust_headers/project_id` 透传）→ :607 `workflow.stream(...)` → :611-613 `first_chunk_latency`。

**关键有利事实**：`build_openjiuwen_workflow_from_ir` 的 `**kwargs`（cust_headers/project_id）在函数体内**完全未使用**（全文仅命中局部变量 `set_end_kwargs`）——构建产物与请求凭证解耦，具备复用前提。

### 2.2 openjiuwen 引擎侧（venv 0.1.19，`site-packages/openjiuwen/`）

| 事实 | 位置 | 对设计的意义 |
|---|---|---|
| `PregelGraph.compile` 首次绑定 `self.pregel/checkpointer/_session`，后续只换 `_session` | `core/graph/graph.py:239-265`（`pregel is None` 分支在 :258） | Patch A 的改造对象 |
| `CompiledGraph._invoke(inputs, session, config)` 是执行树根、持有 session | `core/graph/graph.py:315`（入口包装 `core/graph/base.py:13-14`） | Patch B 的 ContextVar set 点 |
| `Vertex.__init__` 创建 `asyncio.Future`/调用计数；`init(session)` 覆写 `_session` | `core/graph/vertex.py:74-76`、:87-112 | Patch A 每执行新建 Vertex 的依据 |
| `TriggerChannel.messages`（list）/`BarrierChannel.received`（set）为实例共享可变状态，经 `PregelGraph.self.pregel` 跨 compile 复用 | `core/graph/pregel/channels.py:107/144`；`PregelBuilder`（`builder.py:14-16`）创建 | Patch A 每次 compile 全新 Pregel → 全新 channels |
| `_compile` 仅在 `pregel is None` 分支触发（新建 PregelBuilder） | `graph.py:267-303` | 现状第二次 compile 复用旧 channels 的根源 |
| 节点执行 `asyncio.create_task`（继承 context 快照） | `core/graph/pregel/task.py:27-30` | ContextVar 对执行树可见、并发隔离 |
| `Pregel.run` 每次新建 `PregelLoop` | `core/graph/pregel/engine.py:231-249` | 循环级状态已 per-run |
| `BranchRouter.__call__` 首行 `session = self._session`，被 `ConditionalRouter.dispatch` 裸调（无参） | `core/workflow/components/flow/branch_router.py:92-93`；`core/graph/pregel/router.py:32-46` | Patch C 的改造对象 |
| `BaseWorkflow.add_conditional_connection` 让 router 持有 `ProxySession`；每次 `BaseWorkflow.compile` 替换其 `_stub` | `core/workflow/_workflow.py:272-273`、:151、:306 | 缓存实例 + 并发下共享 swap 竞态——由 Patch C 的 ContextVar 优先封堵 |
| `WorkflowSession.config` / `NodeSession` / `GraphStore` 为 per-execution 薄视图 | `core/session/internal/workflow.py:18/104`；`core/graph/store/base.py:92` | spec 挂载在 per-execution Config 上，无进程级注册表 |
| `_create_workflow_session` 每次执行调用，内部 `auto_complete_abilities()` 原地改写共享 workflow spec | `core/workflow/workflow.py:707-745`（:715/:734）；`_workflow.py:336-346` | 幂等性需验证（见 §8 风险 3） |
| `CompiledGraph._invoke` 已被本仓 `workflow_sub_stream_patch.py:539` 替换（增加返回 run 结果、checkpoint scope、sub-workflow IO 清理） | `agent-runtime/jiuwen/extension/patches/workflow_sub_stream_patch.py:139-193` | Patch B 必须包装**已被补丁过的版本** |

**版本现状**：venv 实际安装 openjiuwen **0.1.19**（`pyproject.toml:11` 指向 `git+https://gitcode.com/openJiuwen/agent-core.git@develop`，无版本 pin）；`requirements.txt:20` pin 的 `0.1.17.post2` 已过期失真。因此降级保护**不做版本号检查**，用结构断言（§7.2）。

### 2.3 对 issue 原文的修正

issue 声称 `cache_workflow_queue`"从初始提交起只有失效逻辑、从未接上读写"——**部分不成立**：

- jiuwen BPMN 编排路径上有活跃读写：`jiuwen/orchestration/flow/workflow.py:373`（aput，缓存 spec）、:1181、:1283（aget），由 `jiuwen/controller/workflow`、`task_executor/handler/workflow_handler`、`async_execution` 等引用，是活代码；
- 仅在 **agent_runtime WorkflowRunner（openjiuwen）路径**上成立：`workflow_runner.py` 全程不触该队列，唯一触碰点是删除端点的 apop（`agent_runtime/serve/apis/orchestration.py:763`）。

**影响**：新实例缓存不能复用 `cache_workflow_queue` 队列对象（会与 BPMN spec 混装）；`MAX_WORKFLOW_CACHE_NUM`（`agent_runtime/common/config.py:261-263`，默认 100）已被 BPMN 队列占用，实例缓存使用独立容量配置（§7.1）。

### 2.4 现有补丁惯例（`jiuwen/extension/patches/`，5 个补丁模块 + 1 个 helper）

| 模块 | patch 目标 | 应用时机 |
|---|---|---|
| `workflow_sub_stream_patch.py` | `CompiledGraph._invoke`、`Workflow._sub_stream/_sub_invoke`、`QuestionerDirectReplyHandler._get_latest_chat_history` | import 时（`ir_converter.py:111`、`sub_workflow.py:1570`） |
| `loop_body_session_cleanup_patch.py`（含 2 个 patch） | `LoopGroup.on_invoke` + `AdvancedLoopComponent.on_invoke` | import 时（`sub_workflow.py:1571-1572`） |
| `global_memory_ref_resolution_patch.py` | `CommitState.get_inputs` | import 时（`sub_workflow.py:1573`） |
| `parallel_branch_grouping_patch.py` | `PregelGraph._resolve_barrier_groups` | build 时（`ir_converter.py:1675`，幂等） |
| `nested_branch_barrier_patch.py` | `PregelGraph` 4 个方法（须在 parallel patch 之后） | build 时（`ir_converter.py:1679`） |
| `aggregate_upstream_resolver.py` | 非 patch，纯 helper | — |

惯例：模块级 `_PATCH_APPLIED` flag + `apply_*() -> bool` 幂等入口；保留 `_original_*` 引用；防御式 `getattr/hasattr` + 语义降级；docstring 标注上游修复合并后移除。**结构断言 + 自动降级是本设计新增的惯例**（现有补丁没有）。

### 2.5 ContextVar 边界风险面（实测收窄）

本仓源码无 `asyncio.to_thread`；FlowCode（`jiuwen/extension/workflow_node/flow_code.py:121-159`）在事件循环内直接 `exec()`，不跨线程。真实风险集中在两类：

1. 裸 `run_in_executor`：`agent_runtime/extension/workflow_node/kb_adapter/lakesearch_adapter.py:330`（默认 executor，不拷贝 contextvars）；
2. worker 线程新建事件循环：`jiuwen/serve/controllers/async_execution/add_job.py:39-42/80`、`jiuwen/orchestration/flow/workflow.py:1293-1313`（`sync_build_workflow`）；APScheduler 默认 executor 20 线程（`aps_worker.py:77`）；另有若干 `ThreadPoolExecutor`（memory callback、milvus、insight handlers 等）。

在这些边界内 ContextVar 读到空值 → Patch C / 组件回退 `self._session`（与现状行为一致）。注意：BPMN 路径（`sync_build_workflow`）不在 static_graph 模式范围内，不受影响；agent_runtime 路径中 `lakesearch_adapter` 是唯一需要专项确认的 `run_in_executor` 点。

### 2.6 测试基础设施

pytest（`pyproject.toml:42-43`），`tests/unit_tests/`（含 `runner/test_workflow_runner.py` mock 型执行层测试、`runner/test_ir_concurrent_build_immutability.py` 并发构建测试、`serve/test_ir_converter_conditional_fork_join.py` 白盒 build 测试）+ `tests/integration_tests/`（现有 3 项，无 workflow 执行端到端）。openjiuwen 真实引擎在 venv 可用 → 可写"真实引擎 + stub LLM 组件"的并发隔离集成测试。

## 3. 方案总览

```
请求 → async_ir_load（不变）
     → 【新】workflow_instance_cache 查找，key = ir_path + sha256(canonical IR JSON)
         ├─ 命中：取回已构建的 LazyWorkflow（_workflow 已物化，组件实例共享）
         └─ 未命中：现有 async_ir_to_workflow 新建 LazyWorkflow → 存入缓存
     → workflow.stream(inputs, session, context)
         每次 stream：
           _create_workflow_session（per-execution session，不变）
           → BaseWorkflow.compile
               → Patch A：全新 Pregel/channels/checkpointer/GraphStore/after_step/Vertex
           → CompiledGraph._invoke
               → Patch B：ContextVar.set(session) … finally reset
           → 组件执行（asyncio.create_task 继承 context 快照）
               → Patch C / 组件改造：session 从 ContextVar 解析
```

三条不变式：

1. **off 模式 = 现状行为**：配置默认 `off`，缓存不启用；三件套 patch 始终应用，但每请求新实例下 patched 路径与现状严格等价（§4.4）；
2. **缓存条目内容寻址**：key 含 IR 内容 hash，重新发布即刻 miss，不存在旧图窗口；
3. **执行期状态不落在可复用对象上**：组件实例、图结构、模型客户端可跨执行共享；session、checkpointer、channels、Vertex、Future 全部 per-execution。

## 4. Patch 三件套设计

新模块 `jiuwen/extension/patches/static_graph_patch.py`；ContextVar 定义在独立模块 `jiuwen/extension/workflow/execution_session_ctx.py`（供 patch 与仓库组件共同 import，避免循环依赖）：

```python
# execution_session_ctx.py
_current_workflow_session: ContextVar[Optional[BaseSession]] = ContextVar(
    "jiuwen_current_workflow_session", default=None)

def current_workflow_session() -> Optional[BaseSession]:
    return _current_workflow_session.get()
```

### 4.1 Patch A — `PregelGraph.compile` 纯函数化

替换 `openjiuwen.core.graph.graph.PregelGraph.compile`。每次 compile：

1. 为每个节点**新建 Vertex** 包装共享 executable（从 `self.nodes` 的 `{node_id: vertex}` 提取 `{node_id: vertex.executable}`，构建局部 fresh-vertex map，对其执行 `init(session)`）——原 build 时创建的 Vertex 不再被 init、不被污染；
2. 走"全新构建"分支（不再判断 `self.pregel is None`）：`checkpointer = session.checkpointer()`、`GraphStore(checkpointer.graph_store())`、`after_step` 闭包**捕获 session 参数**（而非读 `self._session`）、经 `_compile` 得到全新 Pregel（全新 PregelBuilder → 全新 channels）；
3. **保留属性写入**（对 issue 定稿的偏离②）：`self.pregel/self.checkpointer/self._session` 仍被赋值（指向本次全新对象）——兼容 `_resolve_barrier_groups` 等可能读取这些属性的现有 patch 与引擎代码；off 模式下每请求新实例的首次 compile 本来就执行等价赋值，严格等价成立。实现时必须**逐一审计 `self.pregel/self.checkpointer/self._session` 的全部读取方**（含本仓 5 个补丁与 openjiuwen 引擎），确认"每次写入全新对象"不破坏任何读取方语义；
4. 返回 `CompiledGraph(本次 pregel, 本次 checkpointer)`。

**等价性论证**（patch 可始终应用的依据）：现状每个新 Workflow 的首次 compile 必然走 `pregel is None` 分支、必然创建全新 pregel/checkpointer/after_step；patched 版本只是无条件走该分支并使用局部 fresh-vertex map。对于"每请求新实例"的 off 模式，两条路径产物等价。

### 4.2 Patch B — `CompiledGraph._invoke` 入口 ContextVar

包装**当前已安装的** `CompiledGraph._invoke`（即 `workflow_sub_stream_patch._patched_compiled_invoke`）：

```python
_prev_invoke = CompiledGraph._invoke   # 必须已是 sub_stream 补丁版本（结构断言校验）

async def _invoke_with_session_ctx(self, inputs, session, config=None):
    token = _current_workflow_session.set(session)
    try:
        return await _prev_invoke(self, inputs, session, config)
    finally:
        _current_workflow_session.reset(token)

CompiledGraph._invoke = _invoke_with_session_ctx
```

嵌套子工作流天然正确：子工作流经 `Workflow._sub_stream/_sub_invoke` → 子图 `CompiledGraph._invoke` 时 set 为子 session，token 式 reset 在子执行结束后恢复父 session——与现状"子编译时 `set_session(子session)`"语义一致。

**应用顺序**：static_graph_patch 必须在 `apply_workflow_sub_stream_patch()` **之后**应用。应用点：`ir_converter.py`（紧跟 :111）与 `sub_workflow.py`（紧跟 :1570）两处，与现有 import 时应用惯例一致；`_PATCH_APPLIED` 幂等守卫防重复。

### 4.3 Patch C — `BranchRouter.__call__` ContextVar 优先

替换 `openjiuwen.core.workflow.components.flow.branch_router.BranchRouter.__call__` 的 session 解析：

```python
session = current_workflow_session() or self._session   # ContextVar 优先，实例回退
```

其余逻辑原样保留（基于 `_original_*` 引用重写或源码级替换）。`set_session` 方法保留（兼容层，非 static_graph 场景仍可用）。

同时封堵 §2.2 所述 `ProxySession._stub` 共享 swap 竞态：执行期间 ContextVar 恒有值，racy 的 `_stub` 永不被读到。

### 4.4 应用策略：始终应用

三件套在 import 时无条件应用（off 模式同样）。理由：off 模式下 patched 路径与现状严格等价（§4.1 论证；B 仅增加 set/reset 一个无人读取的 ContextVar；C 的回退分支命中同一 session）；生产流量持续验证同一份代码路径，灰度切换开关时不引入从未运行过的代码。三种模式（off / static_graph / 降级）跑同一份 patch 代码。

## 5. 仓库侧改造

### 5.1 组件无状态化全量审计（工作量大头）

**审计对象**：`_create_component`（`ir_converter.py:2273`）注册表全部类型：Start、End、Message、LLMChain、Questioner、FlowQA、FlowCode、`_RoutedIntentDetection`、BranchComponent、Aggregate、FlowCard、FlowAgent、FlowApi、FlowMcp、LLMReAct、SubWorkflow（及相关 sentinel/lane-done 辅助组件）。

**审计方法**：对每个类型检查 `__init__` / `invoke` / `stream` / `on_invoke` / 生命周期回调中**所有实例属性写入**，分类为：

- (a) 构建期一次性配置（可共享，保留）；
- (b) 执行期 per-execution 状态（必须消除：改方法内局部变量、参数传递或 ContextVar 读取）；
- (c) 懒初始化的昂贵资源（**保留共享**——`LLMChain._initialized/_llm` 模型客户端复用是本方案的额外收益，需确认线程/协程安全）。

**审计交付物**：组件 × 可变状态 × 处理方式 × 结论 的完整表格，作为本 spec 的附录 A 在实现过程中填充并随 PR 更新（验收标准 6）。

**已知必改项**（探索阶段已核实）：

| 项 | 位置 | 处理 |
|---|---|---|
| `LLMChain.invoke/stream` 覆写 `self._session/_context` | `jiuwen/extension/workflow_node/llm_chain.py:164-165`（invoke）、:208-209（stream） | 改为方法内局部变量/参数传递 |
| `LLMChain._stream_final_output` 实例属性 | `llm_chain.py:111`、:212 | 审计跨调用读写后改局部或 ContextVar |
| `_RoutedIntentDetection.invoke` 的 `self._router.set_session(session)` | `ir_converter.py:894` | 删除（Patch C 经 ContextVar 接管） |
| intent_detection 的 `set_session` 调用 | `jiuwen/extension/workflow_node/intent_detection.py:450` | 同上 |
| FlowApi/FlowMcp 工具注册 tag | 待审计 | 确认注册产物是否幂等、是否含 per-execution 数据 |
| Questioner `set_expect_mix/set_mix` | 待审计 | 确认幂等性与写入时机 |

**应急条款**：若某组件经审计确实无法安全无状态化（实现风险不可接受），回到讨论为该类型引入 blocklist（含该类型的工作流绕过缓存）——这是兜底手段，不是默认设计。

### 5.2 调用侧接入

`workflow_runner.py` 的 `async_ir_to_workflow` 调用（:337-345）改为：

```python
workflow = await workflow_instance_cache.aget_or_create(
    ir_path, ir_json,
    factory=lambda: self._ir_converter.async_ir_to_workflow(
        ir_json, cust_headers=..., project_id=...))
```

其余链路（:607 `workflow.stream(...)` 及之后）不变。

### 5.3 `auto_complete_abilities` 幂等性

每次执行 `_create_workflow_session` 都会调用 `BaseWorkflow.auto_complete_abilities()`（`_workflow.py:336-346`）对共享 spec 原地改写（loop/stream/invoke 能力补全、stream source 分组）。**验证其幂等性**（同输入重复应用结果不变）；若非幂等（如列表追加型写入），在 static_graph_patch 中为其加"已完成"守卫（首次完成后置位，后续 no-op）。守卫本身是共享 flag，但 set-once 语义下并发安全。

## 6. 实例缓存设计

**新模块** `jiuwen/serve/controllers/execution/workflow_instance_cache.py`。

- **缓存对象**：`LazyWorkflow` 实例（保留制——对 issue 定稿的偏离③）。命中时 `lazy.stream()` 经 `instantiate()`（`lazy_workflow.py:96-119`，双检锁）直接复用已物化的 `_workflow`。收益：构建时机不变（仍发生在首次 stream，不改变请求内时序）；LazyWorkflow 双检锁天然保证并发首调单次构建；子工作流 LazyWorkflow 被父组件实例持有，随父缓存自动保留；命中/未命中两路径对象类型统一；
- **key**：`f"{ir_path}:{sha256(canonical_json(ir_data))[:16]}"`，其中 `canonical_json = json.dumps(ir_data, sort_keys=True, ensure_ascii=False, default=str)`。IR dict 来自 `async_ir_load`（共享引用，只读哈希，无拷贝开销）；内容变化（重新发布）即刻 miss；
- **资格**：`ir_data["is_published"]` 为真（`open_utils.py:886-894` 的路径时间戳规则判定，加载时写入 :746/:877）**且** `settings.cache.workflow_instance_reuse_mode == "static_graph"` **且** 未降级（§7.2）。不满足任一条件时完全绕过缓存（现有路径原样执行）；
- **结构**：进程内 memory-only LRU（`OrderedDict` + `asyncio.Lock`，容量 `WORKFLOW_INSTANCE_CACHE_NUM`）。Workflow 实例不可序列化（Future/Lock/闭包），不进 Redis，不复用 `cache_workflow_queue`（BPMN spec 专用，§2.3）；
- **失效**：内容寻址 key 保证正确性（旧条目只会被 LRU 淘汰，永不被误用）。内存卫生：`delete_ir_execution_instance` 端点（`agent_runtime/serve/apis/orchestration.py:763`）顺带按 path 前缀驱逐实例缓存条目（与现有 `cache_workflow_queue` 的 apop 并列，非正确性需要）；
- **不缓存 `ir_convert` 前的产物**：`_convert_global_variable_refs_in_ir` 每次执行（COW，开销小，保持现状——转换结果封在缓存命中的 LazyWorkflow 内部，miss 路径行为不变）。

## 7. 配置、降级与观测

### 7.1 配置（`agent_runtime/common/config.py` 的 `CacheSettings`）

```python
workflow_instance_reuse_mode: Literal["off", "static_graph"] = Field(
    default="off", validation_alias="WORKFLOW_INSTANCE_REUSE_MODE")
workflow_instance_cache_num: int = Field(
    default=100, validation_alias="WORKFLOW_INSTANCE_CACHE_NUM")
```

- 默认 `off` = 现状行为，零风险发布；
- 启动读取、重启生效（不做每请求读 env）；
- `WORKFLOW_INSTANCE_CACHE_NUM` 为独立新配置（对 issue 定稿的偏离①）——`MAX_WORKFLOW_CACHE_NUM` 已被 BPMN 队列实际占用（§2.3），两缓存共用数值会互相干扰。默认值同样取 100。

### 7.2 结构断言与自动降级（内置安全网，非配置项）

`apply_static_graph_patch()` 应用前执行结构断言，任一失败 → **不应用对应 patch** + 置模块级 `STATIC_GRAPH_DOWNGRADED = True` + `logger.error`（含断言失败详情）+ 缓存强制关闭（即使配置为 static_graph）：

| 断言 | 防护目标 |
|---|---|
| `inspect.getsource(PregelGraph.compile)` 含 `self.pregel is None` 模式 | Patch A 基于的 compile 结构未变 |
| `CompiledGraph._invoke` 是 `workflow_sub_stream_patch._patched_compiled_invoke`（同一性或 `__module__` 校验） | Patch B 包装对象正确（应用顺序未被破坏） |
| `BranchRouter.__call__` 存在且源码读 `self._session`；`set_session` 存在 | Patch C 替换基础成立 |
| `Vertex` 具备 `_stream_done/_call_count/_stream_call_count`；`init` 签名兼容 | fresh-vertex 包装可行 |
| `PregelBuilder.add_node`/`add_branch` 签名兼容 | 全新构建分支可用 |

不做版本号检查：依赖是 git develop 无 pin 源（§2.2），结构断言比版本号可靠。降级后三模式归一：off 与降级均走"不启用缓存"路径；已应用成功的 patch 保留（对 off 模式等价无害）。

### 7.3 观测（performance_logger 现有风格）

| 指标 | 位置 | 含义 |
|---|---|---|
| `workflow_cache|hit` / `workflow_cache|miss` | `workflow_runner.py` 缓存查找处 | 与 `ir_build_total`（命中后应消失）、`first_chunk_latency` 对照 |
| `workflow_cache|downgrade` | 降级发生时（启动 + 首次查找） | 结构断言失败信号 |

## 8. 风险与缓解

| # | 风险 | 缓解 |
|---|---|---|
| 1 | patch 与 openjiuwen 版本强耦合（git develop 无 pin，升级即可能破坏结构假设） | §7.2 结构断言 + 自动降级 off + ERROR；触及执行核心，风险高于现有 5 个 patch，靠断言兜底而非版本 pin |
| 2 | ContextVar 边界：`run_in_executor`/worker 线程新事件循环不传播 contextvars | 风险面已实测收窄（§2.5）；`lakesearch_adapter.py:330` 专项确认（其在 agent_runtime 路径且执行期读 session 才受影响）；回退 `self._session` 与现状等价 |
| 3 | `auto_complete_abilities` 非幂等 → 并发执行下共享 spec 改写竞态 | §5.3：先验证幂等；非幂等则加守卫 |
| 4 | `PregelGraph.pregel/checkpointer/_session` 属性存在未知读取方，Patch A 的写入语义变化破坏读取 | 实现时全量审计读取方（引擎 + 5 个补丁 + 本仓）；保留写入、每次写全新对象使读取方最多个读到"最近一次 compile 的产物"（与现状第二次 compile 后的语义一致） |
| 5 | 组件审计遗漏 per-execution 状态 → 跨执行污染 | 全量审计表交付 + 真实引擎并发集成测试（§9）兜底；应急 blocklist 条款（§5.1） |
| 6 | 收益上限：省的是 `ir_build_total` 部分，若首 token 延迟大头在 LLM 推理则整体收益有限 | L0 量化（现有埋点）不在本范围；L2 灰度时以 `workflow_cache|hit` 与 `ir_build_total` 消失情况验证 |

## 9. 测试策略

### 9.1 单元测试（`tests/unit_tests/`，沿用现有组织）

- **缓存**：hit/miss/LRU 淘汰/key 计算（同 path 不同内容 → 不同 key）/重发布失效（内容变 → miss）/非 published IR 绕过；
- **配置门控**：`off` 模式断言缓存零触碰（mock 断言 `aget_or_create` 不被调用或直通 factory）、LazyWorkflow 每请求新建；`static_graph` 模式生效路径；
- **降级**：模拟断言失败（monkeypatch 引擎结构）→ patch 未应用 + 降级标志置位 + ERROR 日志 + 缓存关闭；
- **Patch A 纯度**：同一图两次 compile → 各自独立的 Pregel/checkpointer/Vertex 集合；原 `self.nodes` 的 Vertex 未被 init（`_session` 保持 None）；`after_step` 闭包捕获各自 session；
- **Patch B/C**：`_invoke` 执行期间 ContextVar 可见（嵌套 set/reset 栈式恢复）；`BranchRouter.__call__` 在 ContextVar 有值/无值两种情况下的解析路径。

### 9.2 集成测试（`tests/integration_tests/`，真实 openjiuwen 0.1.19 + stub LLM 组件）

- **并发隔离**（核心场景）：同一缓存实例 N 路并发执行、不同 session → 各自 checkpointer 隔离（无跨会话 checkpoint 泄漏）、分支路由按各自输入走向、join/aggregate 汇聚正确、无 channels 串扰；
- **中断/恢复**：缓存实例上的 interrupt/resume 语义与新鲜实例一致；
- **嵌套子工作流**：父缓存命中后子 LazyWorkflow 的复用语义、子 session 的 ContextVar 栈式解析；
- **等价性回归**：同一 IR 分别以"每请求新建（off）"与"缓存复用（static_graph）"执行，输出与事件序列等价。

### 9.3 回归

三件套始终应用（含 off）→ 现有全量测试必须全绿（这是"off = 现状"的机器验证）。

## 10. 验收标准

1. 默认配置（`WORKFLOW_INSTANCE_REUSE_MODE=off`）下，现有全部测试通过，执行路径与现状严格一致（缓存零触碰）；
2. `static_graph` 模式下：同一 published IR 的第二次及后续请求命中缓存（`workflow_cache|hit`），`ir_build_total` 不再出现在命中请求的日志中；
3. 重新发布 IR 后，新请求内容 hash 不匹配 → miss → 重建；
4. 篡改 openjiuwen 结构（测试中模拟）→ 启动 ERROR + 自动降级，行为回到 off；
5. 真实引擎并发集成测试通过（同实例不同 session 无串扰）；
6. 组件审计表完整覆盖 `_create_component` 注册表全部类型。

## 11. 非目标

- L0 收益量化（用现有埋点，运维侧动作）；
- L2 灰度切换与线上观测（发布后运维流程）；
- jiuwen BPMN 编排路径（`cache_workflow_queue`/spec 缓存体系不动）；
- openjiuwen 上游代码修改（若上游合入等价修复，补丁按现有惯例移除）；
- per-conversation 会话级复用模式（issue 已评估并排除）。

## 12. 对 issue #1555 的修正与偏离记录

| # | issue 原文 | 本设计 | 理由 |
|---|---|---|---|
| 1 | 复用 `MAX_WORKFLOW_CACHE_NUM`（默认 100）做容量上限 | 新增独立 `WORKFLOW_INSTANCE_CACHE_NUM`（默认 100） | 验证发现 `MAX_WORKFLOW_CACHE_NUM` 已被 BPMN 队列实际占用（§2.3），且新缓存不复用该队列对象 |
| 2 | Patch A "不再写 `self.pregel/checkpointer/_session`" | 保留属性写入（每次写全新对象） | 兼容潜在读取方；off 模式严格等价论证更稳（§4.1） |
| 3 | 调用侧（workflow_runner）接入实例缓存 | 缓存对象为 LazyWorkflow（保留制） | 构建时机不变、双检锁复用、子工作流自动保留、路径统一（§6） |
| 4 | `auto_complete_abilities` "需验证幂等" | 明确为：验证幂等 + 非幂等时加守卫 patch | 将开放问题落为确定动作（§5.3） |
| 5 | `cache_workflow_queue` "从未接上读写" | 修正为"仅 agent_runtime 路径成立"（BPMN 路径活跃使用） | 代码验证结论（§2.3） |

## 附录 A：组件无状态化审计表（实现过程填充）

> 本附录在实现阶段逐组件填充，每行对应 `_create_component` 注册表中的一个类型。分类口径见 §5.1 (a)/(b)/(c)。已知必改项已列入 §5.1 表格。

| 组件类型 | 实例属性写入清单 | 分类 (a/b/c) | 处理方式 | 结论（可复用/已修复/受阻） |
|---|---|---|---|---|
| （实现时填充） | | | | |
