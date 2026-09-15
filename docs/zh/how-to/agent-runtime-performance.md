# Agent Runtime 性能优化

本文记录 agent-runtime 当前已落地的热路径优化、依赖基线和回退开关。

## 依赖基线

运行时统一使用 `openjiuwen==0.1.18`。本地项目依赖在
`agent-runtime/pyproject.toml` 中声明，容器安装依赖在
`agent-runtime/requirements.txt` 中声明；两者应保持同一版本。

开发镜像由 CI 显式移除 requirements 中的 `openjiuwen` 行，再安装指定的
`agent-core` 源码。这是开发镜像的源码覆盖流程，不改变正式运行时的版本基线。

## 已启用的热路径优化

### 工作流组件注册

openjiuwen 0.1.18 的 `Workflow` 和 `LoopGroup` 都支持 `name` 参数，IR 转换时
直接转发节点名称，不再为每个组件调用 `inspect.signature`。工作流起止组件的
兼容性反射逻辑仍保留。

### IR 缓存命中日志

内存、Redis 和 OBS 的正常缓存命中只记录 DEBUG；慢的 Redis/OBS 命中（默认超过
50 ms）额外记录 INFO。`ir_load|耗时|来源` 性能指标仍保持 INFO，用于持续观测，
其中来源为 `memory`、`redis` 或 `obs`。

### AdvancedLoop 状态提交

AdvancedLoop 的每轮状态清理和初始化可使用 openjiuwen 0.1.18 提供的
`update_by_id_and_commit`，绕过 staging 队列中不必要的 deepcopy。该路径默认关闭，
完成灰度验证后可通过以下环境变量启用：

```text
LOOP_STATE_DIRECT_COMMIT_ENABLED=true
```

修改环境变量后需重启 runtime 进程；设为 `false` 可随时回退到原有路径。启用前应在目标部署上验证普通循环、嵌套循环、
跳过分支、异常、interrupt/resume、Redis 恢复以及提交前输入对象变更隔离。

## 暂不纳入本批次

节点级性能明细日志采样和 openjiuwen core 的 `copy=False` API 改造暂不在本批次中
启用，避免在缺少完整 P95/P99 基线和跨版本验证时改变观测语义或公共 API。

## 验证与复测

代码回归至少运行 `agent-runtime/tests/unit_tests/serve/test_performance_optimizations.py`。
上线前应使用与基线相同的并发、工作流和数据集复测 TPS、P95/P99、错误率及日志量，
再决定是否扩大 AdvancedLoop 开关的灰度范围。
