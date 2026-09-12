# 对话工作台 Skill 目录注入、按需激活与 `/` 推荐设计

## 1. 文档状态

- 日期：2026-08-17
- 状态：设计已确认，尚未进入实现
- 基线分支：`studio-2.0-dev-0804`
- 开发分支：`feat/wjx-conversation-skill-slash`
- 功能边界：仅扩展同事新增的对话工作台模块，不修改官方 Skill、Agent、IR 和通用 Runtime 实现

## 2. 背景与目标

对话工作台当前由前端独立路由、Manager 的 `conversation` 包和 Runtime 的 `supervisor` 模块组成。当前顶层默认 Agent 只能使用自身已有能力，无法发现当前工作空间组件库中的全部 Skill。

本次需求包含两层能力：

1. 默认能力发现：无需输入 `/`，本轮顶层执行 Agent 始终能看到当前工作空间全部可用 Skill 的名称和描述，并能自主决定是否使用一个或多个 Skill。
2. 显式推荐：用户通过 `/` 菜单选择一个或多个 Skill，向本轮顶层执行 Agent 表达“优先考虑这些 Skill”，但不强制使用。

Skill 只在本轮临时生效，不修改智能体的永久配置、不新增智能体与 Skill 的持久关联，也不要求重新发布智能体。

## 3. 已确认的产品规则

### 3.1 顶层执行者规则

Skill 目录和按需激活能力始终附着到本轮真正的顶层执行者：

- 未通过 `+` 选择智能体：附着到对话工作台默认 Agent。
- 通过 `+` 选择单智能体：附着到被选中的单智能体。
- 通过 `+` 选择多智能体：只附着到多智能体顶层协调者，不传播到全部子智能体。

被选智能体原来永久配置的 Skill 保持不变，本轮工作空间 Skill 作为额外临时能力存在。

### 3.2 `/` 推荐规则

- 用户输入 `/` 时打开 Skill 菜单，可继续输入关键词搜索。
- 只有从菜单选择的 Skill 才产生推荐效果；手写 `/skill-name` 只作为普通文本。
- 支持选择多个 Skill，相同 Skill 自动去重。
- 保留用户选择顺序，并在提示词的推荐区按该顺序展示。
- 推荐意味着优先考虑，不表示必须使用，也不要求所有推荐 Skill 都被激活。
- 不设置人为的单轮 Skill 数量上限。
- 消息成功建立执行连接后清空推荐选择；请求建立失败时保留，以便重试。

### 3.3 当前执行能力

第一阶段不按照 Skill 的能力类型进行发现、推荐或激活限制：

- 当前工作空间中符合目录校验规则的 Skill 均可被发现、推荐和按需激活。
- 激活时下载 Skill 制品、读取完整 `SKILL.md`，并将其指令返回给顶层 Agent。
- Skill 能否真正完成任务，取决于本轮顶层 Agent 实际注册的工具和当前运行环境，而不是由 Skill 目录或激活层预先判定。
- 当前运行环境尚未注册命令执行、代码执行、文件操作或沙箱工具。Skill 如果依赖这些能力，可被正常激活，但执行到相关步骤时应明确报告所缺能力和失败原因，不得伪造执行结果。
- 本次功能不负责新增上述执行工具；后续注册本地工具或沙箱环境后，现有 Skill 目录、推荐和按需激活协议无需改变，即可向具备相应能力的 Skill 提供真实执行条件。

## 4. 方案比较与决策

### 4.1 采用：统一 `activate_skill` 工具按需激活

向顶层执行 Agent 注入全部 Skill 元数据，并注册一个统一的 `activate_skill(skill_id)` 工具。Agent 自主选择或受到 `/` 推荐后，再激活具体 Skill。

优点：

- 不需要每轮预下载全部 Skill。
- 工具数量不会随 Skill 数量线性增长。
- 只需在对话工作台新增模块内扩展。
- 能自然支持多个 Skill 依次激活。
- 未来可在同一激活边界接入沙箱。

### 4.2 不采用：每个 Skill 注册成独立工具

该方案会导致工具列表随 Skill 数量膨胀，并存在工具名称冲突和动态注册成本，不适合工作空间全量 Skill。

### 4.3 不采用：每轮生成临时 Agent IR

该方案需要生成、上传并重新加载 IR，执行链过重，也会侵入官方发布和 IR 生成逻辑。

### 4.4 不采用：每轮预下载全部 Skill

该方案在 Skill 数量增加后会造成不必要的下载、解压和磁盘开销，与“描述常驻、制品按需激活”的需求不符。

## 5. 总体架构

```text
当前工作空间 Skill 列表
        │
        ▼
Manager 对话工作台模块
查询并校验 Skill 元数据
        │
        ├── skillCatalog：全部合法 Skill 元数据
        └── recommendedSkillIds：本轮菜单推荐项
        │
        ▼
Runtime 对话工作台模块
由智能体选择逻辑确定顶层执行者
        │
        ▼
skill_context.attach(topLevelAgent, catalog, recommendedIds)
        │
        ├── 注入 Skill 目录和推荐区
        └── 注册 activate_skill
        │
        ▼
Agent 自主选择或受推荐影响
        │
        ▼
activate_skill(skill_id)
        │
        ▼
按版本下载、校验、缓存、读取 SKILL.md
        │
        ▼
Agent 根据 Skill 指令继续完成任务
```

## 6. 模块边界与并行开发隔离

### 6.1 允许修改的范围

- `frontend/src/routes/conversation-workspace/**`
- `backend/studio-manager-service/src/main/java/com/openjiuwen/studio/conversation/**`
- `backend/studio-manager-service/src/test/java/com/openjiuwen/studio/conversation/**`
- `agent-runtime/agent_runtime/supervisor/**`
- 同事新增的 `agent-runtime/agent_runtime/serve/apis/conversation_team.py`
- 上述 Runtime 模块对应测试

### 6.2 只调用、不修改的官方代码

- 官方 `SkillApi` 和组件库 Skill 页面
- `SkillManagementService`
- `SkillMapper` 的现有查询能力
- `IrAdapterService`
- `react_agent_runner.py`
- openJiuwen SDK

### 6.3 与 `+` 智能体选择的隔离

前端维护两个独立状态：

- `+` 按钮维护智能体选择，由同事代码负责。
- `/` 菜单维护 `recommendedSkills`，由本功能负责。

两者互不读取、互不清空。请求中 Skill 使用独立字段 `recommended_skill_ids`，不改变同事定义的智能体字段。

Runtime 只要求智能体选择逻辑最终提供 `top_level_agent`。Skill 模块通过单一挂载入口工作：

```python
await skill_context.attach(top_level_agent, catalog, recommended_ids)
```

同事尚未推送 `+` 功能时，先完成默认 Agent 链路。其代码合入后，只在顶层执行者构建完成处增加挂载调用，不介入选择 UI 和路由规则。

## 7. Skill 目录与可信边界

Manager 每轮按照以下上下文查询全部可用 Skill：

- 当前 `project_id`
- 当前 `workspace_id`
- 当前用户 `domain_id`
- `status = developed`
- 未删除且制品路径有效

不包含其他工作空间、其他用户域、`developing` 状态或制品缺失的 Skill。查询通过分页读取全部结果，不设置业务数量上限。

浏览器只提交 Skill ID，不提交可信元数据。Manager 必须在写入用户消息和调用 Runtime 之前完成：

- 推荐 ID 去重并保留顺序。
- 校验每个推荐 ID 都属于本轮合法目录。
- 根据服务端数据解析名称、描述、版本和对象存储路径。
- 任一推荐 ID 已删除、不可用或越权时拒绝本轮请求。

对象存储路径只存在于 Manager 到 Runtime 的内部请求中，不能返回浏览器。

## 8. 接口契约

### 8.1 浏览器到 Manager

```json
{
  "query": "请整理并润色以下会议记录",
  "model_deployment_id": "模型部署ID",
  "recommended_skill_ids": [
    "meeting-minutes-skill-id",
    "professional-rewriter-skill-id"
  ]
}
```

未推荐 Skill 时传空数组或省略字段，Manager 统一归一化为空数组。

### 8.2 Manager 到 Runtime

```json
{
  "skillCatalog": [
    {
      "skillId": "Skill ID",
      "versionId": "版本ID",
      "name": "meeting-minutes-cn",
      "description": "将会议记录整理为结构清晰的会议纪要",
      "objectKey": "内部对象存储路径"
    }
  ],
  "recommendedSkillIds": [
    "meeting-minutes-skill-id"
  ]
}
```

该结构与同事的智能体选择字段并列存在，不使用共享可变字段，降低合并冲突。

## 9. 顶层 Agent 提示词

提示词分为两个区段：

1. 当前工作空间可用 Skill：列出全部 Skill 的 ID、名称和描述。
2. 本轮推荐 Skill：仅在推荐列表非空时生成，按用户选择顺序列出。

行为规则明确为：

- 可自主选择一个或多个适合任务的 Skill。
- 推荐 Skill 应优先考虑，但不强制使用。
- 决定使用某个 Skill 后，先调用 `activate_skill(skill_id)`。
- 只能激活本轮目录中的 Skill。
- 不得把“看过描述”等同于已经读取并遵循 `SKILL.md`。

## 10. `activate_skill` 设计

### 10.1 输入

```json
{
  "skill_id": "Skill ID"
}
```

### 10.2 执行流程

1. 校验 `skill_id` 位于本轮可信目录。
2. 使用 `skill_id + version_id` 检查本地版本缓存。
3. 缓存未命中时从对象存储下载 ZIP。
4. 校验 ZIP 路径穿越、目录结构和 `SKILL.md`。
5. 解压到版本隔离目录。
6. 读取并解析 `SKILL.md`。
7. 将完整 Skill 指令返回给 Agent；实际可用能力以本轮 Agent 已注册工具和运行环境为准。

### 10.3 输出

```json
{
  "skillId": "Skill ID",
  "name": "meeting-minutes-cn",
  "versionId": "版本ID",
  "instructions": "SKILL.md 完整正文"
}
```

Agent 一轮可以多次调用该工具，并组合多个 Skill 的规则完成任务。激活成功只表示 Skill 指令已加载，不表示其依赖的全部工具或执行环境已经就绪。

## 11. 缓存与并发

- 缓存键为 `skill_id + version_id`，不使用名称作为目录主键。
- 同一版本只下载和解压一次。
- Skill 版本更新后使用新缓存，不覆盖旧版本目录。
- 并发首次激活同一版本时使用进程内异步锁，避免重复下载和解压。
- 解压目标路径由服务端生成，不能直接拼接 Skill 名称。
- 第一阶段不增加复杂的缓存淘汰策略；旧版本清理由后续运维策略处理。

## 12. 前端交互

新增对话工作台内部 Skill 选择子组件，负责：

- `/` 触发、关键词过滤、上下键、Enter 和 Esc。
- Skill 多选、去重和单项删除。
- 将选择结果转换为有序 `recommended_skill_ids`。
- 消息成功建立执行连接后清空，连接前失败则保留。
- 工作空间切换时清空旧选择并重新加载目录。

已选 Skill 以标签展示，不把菜单展示文本作为服务端解析依据。`+` 智能体状态与该组件状态完全独立。

Agent 激活 Skill 后，当前页面展示“已激活技能：{name}”。前端不展示对象存储路径、本地目录或 `SKILL.md` 原文。

## 13. 异常与降级

- 目录加载失败且没有推荐项：允许普通对话继续，并提示本轮无法使用工作空间 Skill。
- 推荐 ID 失效或越权：Manager 在写用户消息前拒绝请求，前端刷新列表并保留用户输入。
- Skill 下载、校验或解压失败：`activate_skill` 返回结构化错误，Agent 可说明失败并尝试其他 Skill 或直接回答。
- 多个 Skill 中单个激活失败：不终止整轮，其他 Skill 仍可继续。
- 模型请求激活目录外 ID：Runtime 拒绝访问对象存储并返回非法 Skill 错误。

## 14. 历史记录边界

第一阶段不修改数据库结构：

- 用户原始问题照常落库。
- 推荐 ID 只存在于本轮执行上下文，不写入智能体配置。
- 当前页面可展示本轮选过和激活过的 Skill。
- 刷新历史会话后，只恢复问题和回答，不恢复推荐标签与激活轨迹。

后续若出现审计需求，再统一设计资源调用记录，同时覆盖 `+` 智能体选择和 `/` Skill 推荐，避免本阶段提前引入不完整的通用表结构。

## 15. 测试设计

### 15.1 前端

- `/` 触发、搜索、键盘导航和关闭。
- 多选、去重、删除和顺序保持。
- 手写 Skill 名称不触发推荐。
- 请求携带正确的 `recommended_skill_ids`。
- 与模拟的 `+` 智能体状态并存时互不影响。
- 工作空间切换清空旧状态。

### 15.2 Manager

- 分页查询当前工作空间全部 `developed` Skill。
- 推荐 ID 去重并保留顺序。
- 跨工作空间、跨用户域、删除和不可用 Skill 被拒绝。
- 校验失败时不会提前写入用户消息。
- Runtime 请求只包含服务端解析的可信元数据。

### 15.3 Runtime

- 全部 Skill 描述进入顶层执行者提示词。
- 推荐 Skill 进入独立推荐区但不转为强制指令。
- Agent 可以自主调用 `activate_skill`。
- 多个 Skill 可以依次激活。
- 相同版本只下载一次，版本更新产生新缓存。
- 未知 ID、路径穿越、非法 ZIP 和非法目录结构被拒绝。
- Skill 只附着到顶层执行者，不传播给多智能体子成员。

### 15.4 端到端验收

首轮联调使用已导入的三个纯文本测试 Skill，以便先验证目录、推荐和激活主链路：

- `meeting-minutes-cn`
- `requirement-clarifier-cn`
- `professional-rewriter-cn`

验收场景：

1. 不输入 `/` 发送会议整理任务，Agent 自主激活会议纪要 Skill。
2. 通过菜单推荐文本润色 Skill，回复体现该 Skill 的唯一标记。
3. 同时推荐会议纪要和文本润色 Skill，Agent 可依次激活并组合使用。
4. 通过 `+` 选择单智能体后，Skill 目录与推荐附着到该单智能体。
5. 通过 `+` 选择多智能体后，只附着到顶层协调者。
6. 切换工作空间后不能看到或激活原工作空间 Skill。
7. 全程不改变智能体永久 Skill 配置。

## 16. 实施顺序约束

1. 实现前重新获取并检查 `studio-2.0-dev-0804` 最新提交。
2. 先通过测试定义前端、Manager 和 Runtime 契约。
3. 将主要逻辑放入新子组件、新 Resolver 和新 `skill_context` 模块。
4. 对热点文件只做最小接线修改。
5. 默认 Agent 链路完成后先使用三个纯文本测试 Skill 独立联调；这只是首轮测试范围，不构成运行时的 Skill 类型限制。
6. 同事 `+` 功能合入后，在顶层执行者构建完成处挂载 Skill 上下文并补充组合测试。
7. 所有提交说明和开发文档使用中文。

## 17. 非目标

本次不包含：

- 修改官方 Skill 管理和 Agent 发布逻辑。
- 永久绑定工作空间 Skill 到智能体。
- 给多智能体所有子成员自动复制 Skill。
- 新增或部署代码执行、命令执行、文件操作和沙箱环境；如果本轮 Agent 已经注册相关工具，激活后的 Skill 不受本设计额外限制。
- 推荐或激活轨迹的数据库持久化。
- Skill 使用统计、审计报表和缓存运维后台。
