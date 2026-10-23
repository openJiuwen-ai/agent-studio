# Studio 2.0 错误码基线评审记录

## 评审结论

- 治理目标分支：`studio-2.0-dev`
- 协议版本：`v1.2`
- 初始源码基线提交：`4d21655300ea789b1b1e38141b7761acefb9ee69`
- 候选总数：1506；已登记 definition：846；已登记跨服务 reference：4；未登记候选：660
- `0200`～`0240`、`0260`～`0320` 已冻结；`0250`、`0330` 暂定；`1210` 预留
- Runtime 已验证的精确对外值 `openjiuwen.121007` 作为 `legacy_other` 例外登记

未登记候选不代表允许继续新增或复用。现有问题以 `error-code-advisory-baseline.json` 的稳定指纹记录为 `accepted_existing`，须在切换阻断式治理前按 Owner 和目标里程碑处理。

## 维护规则

Manifest 是错误码治理事实源，可读目录由脚本生成。刷新存量基线时，当前三服务源码树必须与 `studio-2.0-dev` 一致，且基线刷新不得与三服务源码修改处于同一变更中：

```bash
python3 tools/observability/scripts/check_error_code_inventory.py \
  --write-baseline --target-branch studio-2.0-dev
```

当前治理 Owner 为 `@zhuyechen`；合入团队仓库前，应按实际长期维护职责评估是否增加或替换 Owner。

## DEF-06 变更记录（2026-09-15）

DEF-06「Builder 异常 Handler 业务码与异常栈处理」登记 8 个 **Builder 专属 canonical 码**
（`openjiuwen.13100006~13100013`，`code_format=canonical8`、`code_owner=builder`、
`default_level=ERROR`、`lifecycle_status=active`），用于 Prompt/MMAPO 业务异常的 HTTP 边界输出。

**设计决策（方案A，无跨服务 Owner 冲突）**：Builder 不登记 legacy 整数码 `102154` 等
（Runtime 的 `jiuwen` 包亦独立持有这些 legacy 码副本）。`from_builder_exception` 把异常
携带的 legacy 整数码映射到 Builder 专属 canonical 定义输出。Builder 的 canonical 码
不与 Runtime 的 legacy 码冲突 → **无 `definition_owner_mismatch`，无需跨服务 Owner 决策**。

| canonical 码 | ← legacy 整数 | 语义 | HTTP |
| --- | --- | --- | --- |
| openjiuwen.13100006 | 102154 | 优化参数非法 | 400 |
| openjiuwen.13100007 | 102155 | 优化任务不存在 | 404 |
| openjiuwen.13100008 | 102156 | 任务状态不允许当前操作 | 409 |
| openjiuwen.13100009 | 102158 | 优化任务启动失败 | 500 |
| openjiuwen.13100010 | 102159 | 优化任务重启失败 | 500 |
| openjiuwen.13100011 | 102170 | 优化任务存储失败 | 500 |
| openjiuwen.13100012 | 102213 | 反馈优化失败 | 500 |
| openjiuwen.13100013 | 102214 | Badcase 优化失败 | 500 |

### fixture 三态演进

| 阶段 | 响应 error_code | HTTP 状态 |
| --- | --- | --- |
| COM-03 前历史接口 | `102xxx`（legacy 整数，`{code,message}` 外层） | 全 500 |
| COM-03 基线 `2fa44b5d` | `openjiuwen.13100004`（标准五字段，全部 mask） | 500 |
| DEF-06 目标 | `openjiuwen.13100006~13`（标准五字段，canonical 映射） | 400/404/409/500 按语义 |

### 决策记录（用户确认，2026-09-15）

1. **八码重编号（legacy→canonical）**：用户明确确认采用受控 canonical 迁移（`102xxx → openjiuwen.13100006~13`），不回退 `_LEGACY_TO_CANONICAL`。此为区别于原规划默认"legacy 精确保留"的显式规划变更。
2. **HTTP 500→4xx**：用户单独确认接受 `102154/102155/102156` 对应 canonical 码的 HTTP `400/404/409`（语义正确）。与重编号是两项不同的兼容决策，分别确认。
3. **消费者迁移**：前端/Manager 兼容确认作为**发布前置条件**（非 DEF-06 代码收口阻断）；当前未完成消费者契约核实，按外部消费者处理。
4. **回滚方式**：`from_builder_exception` 临时回退为 `from_internal` 即恢复 `13100004/500` 全量 mask，无需改 catalog/Manifest。

### 跨服务现状（无冲突）

- **Builder**：登记 8 个 canonical 码（`13100006~13`），`definition_source` 指向 `agent_builder/common/error_contract/catalog.py`，Builder 全局唯一 owner，无 Runtime 副本 → 无 mismatch。
- **Runtime**：`jiuwen` 包的 `agent-runtime/jiuwen/common/exception/status_code.py` 独立持有 legacy 整数码 `102154` 等副本（Builder 的 `agent_builder/common/exception/status_code.py` 亦持一份 fork 副本）。这些 legacy 整数码**不登记**（Builder 不登记、Runtime 未登记），保持 `unregistered_definition` accepted_existing 债务（DEF-06 前既存状态）。Runtime 代码**完全不动**。
- **协议合规**：Builder 只登记自己的 canonical definition（§7.3-7.4 合规）；legacy 整数码副本作为既有未登记债务延期（`before_strict_ci`），根治方式为 Runtime/Builder 将 legacy 副本改为 reference 或迁移共享 SDK——不在 DEF-06 范围。

### advisory baseline 变更

- **8 个 canonical 码**（`13100006~13`）：干净登记，无 issue。
- **DEF-06 引入并修复的 `unknown_literal_reference`**：`catalog.py` docstring 中的伪字面量 `openjiuwen.13100xxx` 曾触发 1 条新 issue 并被误纳入 baseline；已修复 docstring 并从 baseline 撤销该指纹。
- **legacy 整数码**（`102154` 等）：保持 DEF-06 前既存的 `unregistered_definition` accepted_existing 状态，不新增不消解。
- **基线指纹**：`1771 → 1771`（DEF-06 不引入净新增治理问题；8 canonical 干净登记 + docstring 伪字面量修复后回归原始基线）；`EXPECTED_ISSUE_COUNT` 同步为 1771。
- **边界**：未登记/不可信/`-1`/动态码仍稳定映射 `openjiuwen.13100004`；流式异常、N2L 资源回收归 COM-07A。
