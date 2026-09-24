# 可观测性治理

本目录存放 Manager、Runtime、Builder 共同使用的开发期可观测性契约与校验工具，不存放 Vector、Grafana 等部署配置。部署侧文件继续位于 `deploy/observability/`。

长期权威协议为 [`docs/zh/reference/observability-contract.md`](../../docs/zh/reference/observability-contract.md)。Manifest 的 `protocol_version` 必须与该协议版本一致。

## 错误码治理

`error-codes.yaml` 是三服务错误码的唯一治理事实源。新增或调整平台错误码时，应同时完成：

Manifest 根字段 `version` 表示 Manifest schema 版本，`protocol_version` 表示已同步的 Studio 2.0 可观测性协议版本，两者不得混用。`protocol_sha256` 绑定权威协议正文内容；修改协议时必须经版本化评审并同步 Manifest，禁止只改哈希掩盖未评审变更。

1. 登记 definition，明确唯一 Owner、模块、HTTP 状态、分类、默认日志级别、i18n 根键和生命周期；
2. 非 Owner 服务使用该码时登记 reference；
3. 在 Owner 服务补齐中英文 message、reason、suggestion；
4. 补充对应 HTTP/SSE 契约测试或 fixture；
5. 重新生成并提交中英文错误码目录。

生成文档：

```bash
python3 tools/observability/scripts/generate_error_code_docs.py
```

执行本地校验：

```bash
python3 tools/observability/scripts/check_error_codes.py
python3 -m unittest discover -s tools/observability/tests -p 'test_*.py'
```

执行与 GitCode 一致的提示式检查：

```bash
python3 tools/observability/scripts/run_error_code_advisory.py
```

提示式检查同时执行 Manifest/生成目录校验和首批存量增量扫描。首批扫描覆盖已识别定义、`openjiuwen.*` 字面引用、未声明跨服务字面引用、properties i18n 和定义源；不等同于已经覆盖 legacy 全形态、动态构建、HTTP/SSE fixture、代码属性和全部真实出口。

`error-code-advisory-baseline.json` 记录已评审存量问题的稳定指纹、处理 Owner、评审状态、目标里程碑和来源快照元数据，用于突出新增问题。基线中的问题消失时只报告，不会自动改写基线；只有完成人工评审后才能刷新。

GitCode 工作流位于 `.gitcode/workflows/error-code-governance.yml`。当前固定运行提示式入口：检查结果写入步骤摘要和保留 14 天的报告构件，即使发现问题也不会使流水线失败。`run_error_code_advisory.py --strict` 仅为后续阻断式 CI 预留，未经治理评审不得在流水线中启用。

当前治理范围仅为 `studio-2.0-dev`，该分支维护一份经目标分支源码树复核的基线。`.gitcode/CODEOWNERS` 当前由 `@zhuyechen` 负责 Manifest、基线、治理脚本、工作流、协议和生成目录；合入团队仓库前应结合实际维护职责，再评估是否增加或替换 Owner。仓库还必须在 GitCode 设置中启用 CODEOWNERS 审查门禁。CI 的基线变更策略禁止在同一变更中同时修改三服务源码和刷新已有基线；首次引入基线允许 bootstrap，但仍须 Owner 审批。push 检查按事件中的 `before` SHA 覆盖整批提交，PR 检查按目标分支与当前 HEAD 直接比较。

按目标分支生成或刷新基线：

```bash
python3 tools/observability/scripts/check_error_code_inventory.py \
  --write-baseline --target-branch studio-2.0-dev
```

生成目录位于：

- `docs/zh/reference/error-codes.md`
- `docs/en/reference/error-codes.md`

上述 Markdown 是生成物，不得直接维护码值、Owner 或 HTTP 状态。提示式 GitCode CI 已配置；处理存量问题并切换阻断模式仍属于后续治理任务。
