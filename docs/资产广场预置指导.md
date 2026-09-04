# 资产广场预置指导

- [一、应用模板](#一应用模板)
- [二、模型](#二模型)
- [三、MCP](#三mcp)
- [四、插件](#四插件)
- [五、提示词](#五提示词)
- [六、Skill](#六skill)

---

## 一、应用模板

将已发布的智能体或工作流上架到资产广场，供用户浏览、体验和复制。前提：资源已在系统中创建并发布版本。**当前不支持多智能体**。

### 单智能体

**步骤一：查询智能体信息**

```sql
SELECT agent_id, project_id, workspace_id, name, description, icon, prologue, suggest_queries
FROM t_agent WHERE (agent_id = '{agent_id}' OR name = '{agent_name}') AND deleted = 0;
```

**步骤二：查询已发布版本的 DSL/IR 路径**

```sql
SELECT version_id, dsl_path, ir_path FROM t_release_version
WHERE app_id = '{agent_id}' AND deleted = 0
ORDER BY released_on DESC LIMIT 1;
```

记录步骤一、二的查询结果，后续步骤需要使用。

**步骤三：上传 `_published.json` 到 OBS**

将步骤二中查到的 DSL/IR 文件复制一份，重命名为 `{id}_published.json`，放在同一目录下。路径以步骤二查出的 `dsl_path` 和 `ir_path` 为准。

> **说明**：runtime "立即体验"通过拼接路径读取 IR，固定为 `{id}_published.json`，不能带版本号。

**步骤四：插入 `t_agent_version`**

供"复制到工作台"读取 DSL 和 runtime 确认在线状态。

| 字段 | 说明 |
|------|------|
| `version_id` | 版本唯一标识，VARCHAR(64)，UUID |
| `agent_id` | 关联智能体ID，VARCHAR(64) |
| `project_id` | 项目ID，VARCHAR(64) |
| `ir_path` | IR文件OBS相对路径，即步骤三中的 `_published.json` 路径 |
| `dsl_path` | DSL文件OBS相对路径，即步骤三中的 `_published.json` 路径 |

```sql
INSERT INTO t_agent_version (version_id, agent_id, project_id, ir_path, dsl_path, is_online, creator,
    created_on, updated_on, published_on)
VALUES (UUID(), '{agent_id}', '{project_id}',
    'agent/ir/{agent_id}/{agent_id}_published.json',
    'agent/dsl/{agent_id}/{agent_id}_published.json',
    1, 'SYSTEM', NOW(), NOW(), NOW());
```

> 路径以步骤三操作结果为准，上方SQL中为示例值。

**步骤五：插入 `t_app`**

| 字段 | 说明 |
|------|------|
| `app_id` | 主键，VARCHAR(64)，UUID |
| `project_id` | 项目ID，VARCHAR(64) |
| `name` | 应用名称，VARCHAR(64)，支持模糊搜索 |
| `description` | 应用描述，VARCHAR(1024) |
| `icon` | 应用图标，MEDIUMTEXT，图标URL或Base64 |
| `tags` | 标签ID，VARCHAR(512)，**不可为 null**；值为 JSON 数组格式的 `t_tag.tag_id` 列表（标签数据由初始化SQL插入 `t_tag` 表），如 `["tag_id_1","tag_id_2"]`，无标签时设为 `[]` |
| `resource_id` | 关联的智能体ID，VARCHAR(64)，即 `agent_id` |

```sql
INSERT INTO t_app (app_id, project_id, workspace_id, name, description, icon, tags,
    app_type, resource_id, resource_type, creator, published_on, deleted)
VALUES (UUID(), '{project_id}', '{workspace_id}', '{name}', '{description}', '{icon}',
    '["tag_id_1","tag_id_2"]', 'chat', '{agent_id}', 'agent', 'SYSTEM', NOW(), 0);
```

### 工作流

**步骤一：查询工作流信息**

```sql
SELECT id, project_id, workspace_id, name, description, avatar, workflow_type
FROM t_agent_workflow WHERE (id = '{workflow_id}' OR name = '{workflow_name}') AND deleted = 0;
```

**步骤二：查询已发布版本**

```sql
SELECT version_id, version_name, dsl_path, ir_path FROM t_release_version
WHERE app_id = '{workflow_id}' AND deleted = 0
ORDER BY released_on DESC LIMIT 1;
```

记录步骤一、二的查询结果，后续步骤需要使用。

**步骤三：插入 `t_release_channel`**

工作流的"详情查看"和"复制到工作台"通过 `t_release_channel`（`channel_type='app_store'`）关联 `t_release_version` 获取 DSL/IR。

> **注意**：同一 `app_id` + `channel_type='app_store'` 只能有一条记录，否则查询报错。插入前先确认是否已存在，若已存在则更新而非重复插入。

| 字段 | 说明 |
|------|------|
| `id` | 主键，VARCHAR(64)，UUID |
| `app_id` | 工作流ID，VARCHAR(64) |
| `app_type` | 应用类型，VARCHAR(32)，设为 `workflow` |
| `version_id` | 关联版本ID，VARCHAR(64)，与 `t_release_version.version_id` 一致 |
| `version_name` | 版本名称，VARCHAR(64) |
| `channel_type` | 发布通道类型，VARCHAR(32)，**必须设为 `app_store`** |
| `project_id` | 项目ID，VARCHAR(64) |
| `workspace_id` | 工作空间ID，VARCHAR(64) |

```sql
INSERT INTO t_release_channel (id, app_id, app_type, version_id, version_name, channel_type,
    status, project_id, workspace_id)
VALUES (UUID(), '{workflow_id}', 'workflow', '{version_id}', '{version_name}', 'app_store',
    'released', '{project_id}', '{workspace_id}');
```

**步骤四：插入 `t_app`**

| 字段 | 说明 |
|------|------|
| `app_id` | 主键，VARCHAR(64)，UUID |
| `project_id` | 项目ID，VARCHAR(64) |
| `workspace_id` | 工作空间ID，VARCHAR(64) |
| `name` | 应用名称，VARCHAR(64)，支持模糊搜索 |
| `description` | 应用描述，VARCHAR(1024) |
| `icon` | 应用图标，MEDIUMTEXT，图标URL或Base64 |
| `tags` | 标签ID，VARCHAR(512)，**不可为 null**；值为 JSON 数组格式的 `t_tag.tag_id` 列表（标签数据由初始化SQL插入 `t_tag` 表），如 `["tag_id_1","tag_id_2"]`，无标签时设为 `[]` |
| `resource_id` | 关联的工作流ID，VARCHAR(64) |
| `workflow_type` | 工作流类型，VARCHAR(16)，枚举值：`chat`（对话型）、`task`（任务型） |

```sql
INSERT INTO t_app (app_id, project_id, workspace_id, name, description, icon, tags,
    app_type, resource_id, resource_type, workflow_type, creator, published_on, deleted)
VALUES (UUID(), '{project_id}', '{workspace_id}', '{name}', '{description}', '{icon}',
    '["tag_id_1","tag_id_2"]', 'scene', '{workflow_id}', 'workflow', '{workflow_type}', 'SYSTEM', NOW(), 0);
```

---

## 二、模型

模型预置需写入数据库和OBS两处。

### 步骤一：数据库写入

**字段说明**：

| 字段 | 说明 |
|------|------|
| `ID` | 主键，VARCHAR(80)，UUID |
| `SERVICE_NAME` | 服务名称，VARCHAR(64) |
| `SERVICE_KEY` | 模型服务关键字，VARCHAR(128)，格式 `publisher:maas:{modelName}` |
| `MODEL_NAME` | 模型名称，VARCHAR(64) |
| `MODEL_VERSION` | 模型版本，VARCHAR(64) |
| `MODEL_TYPE` | 模型功能类型，VARCHAR(32)，枚举值：`LLM`、`TEXT-TO-IMAGE`、`IMAGE-TO-TEXT`、`AUDIO-TO-TEXT`、`Text-Embedding`、`Text-Multimodal-Embedding`、`RERANK`、`TEXT-TO-VIDEO` |
| `API_URL` | API地址，VARCHAR(256) |
| `INTERFACE_PROTOCOL` | 接口协议，VARCHAR(32)，决定runtime调用模型API时的请求适配器。枚举值：`maasv2`（MaaS V2协议）、`maasv1`（MaaS V1协议）、`openai`（OpenAI兼容）、`baichuan`（百川）、`qwen`（通义千问）、`moonshot`（Moonshot）、`minimax`（MiniMax）、`zhipu`（智谱）、`maas_embedding`（MaaS Embedding）、`maas_rerank`（MaaS Rerank）、`multi_openai`（多OpenAI兼容） |
| `MODEL_DESCRIPTION` | 模型描述，TEXT |
| `MODEL_DESCRIPTION_EN` | 模型英文描述，TEXT |
| `MODEL_TAGS` | 模型标签，TEXT，逗号分隔 |
| `IS_REASONING` | 是否支持思考，TINYINT |
| `IS_SUPPORT_CLOSE_REASONING` | 深度思考开关，TINYINT |
| `CONTEXT_LENGTH` | 上下文长度，INT，大语言模型适用 |
| `LOGO` | LOGO，LONGTEXT，Base64 |

**预置SQL示例**：

```sql
INSERT INTO t_model_service (ID, PROVIDER_ID, SERVICE_NAME, SERVICE_KEY, MODEL_NAME, MODEL_VERSION,
    MODEL_TYPE, MODEL_DEPLOY_TYPE, MODEL_DESCRIPTION, MODEL_DESCRIPTION_EN, MODEL_TAGS,
    DOMAIN_ID, PROJECT_ID, WORKSPACE_ID, API_URL, IS_SUPPORT_FUNCTION, INTERFACE_PROTOCOL,
    IS_SUPPORT_STREAM, AUTH_METADATA_ID, PUBLISH_STATUS, MODEL_PRIORITY, THROTTLING_POLICY,
    LOGO, STATUS, IDENTITY_ID, IS_PUBLIC, SYNC_STATUS, IS_REASONING, IS_SUPPORT_CLOSE_REASONING,
    CREATED_BY_USER, LAST_UPDATED_BY_USER, CREATED_DATE, LAST_UPDATED_DATE)
VALUES ('{model_id}', '100', '{service_name}', '{service_key}', '{model_name}', '{model_version}',
    '{model_type}', 'PLATFORM-INTEGRATION', '{model_description}', '{model_description_en}', '{model_tags}',
    '0', 'SYSTEM', 'SYSTEM', '{api_url}', 1, '{interface_protocol}',
    1, '1022', 'online', 30, -1,
    '{logo}', 'success', UUID(), 0, 'finish', {is_reasoning}, {is_support_close_reasoning},
    'SYSTEM', 'SYSTEM', UNIX_TIMESTAMP(), UNIX_TIMESTAMP());
```

> **重要**：数据库和OBS内容必须一致。`PROVIDER_ID` 标识模型所属供应商，设为 `platform_provider_id` 配置值（默认 `'100'`）时，模型被识别为平台免费模型，免鉴权即可使用；`AUTH_METADATA_ID` 关联 `t_provider_auth_metadata` 表的鉴权元数据定义，`'1022'` 是初始化SQL为供应商 `'100'` 预置的 `API_KEY` 类型鉴权定义，两者配套使用。

### 步骤二：OBS写入

将 `ModelStrategy` JSON 上传到OBS，路径格式：`model-service/ir/{id}.json`

---

## 三、MCP

预置 MCP 只需向 `ws_mcp_server_def` 表插入记录，查询时通过 `type = 'inner'` 筛选官方预置MCP。

**字段说明**：

| 字段 | 说明 |
|------|------|
| `server_code` | MCP服务编码，VARCHAR(255) |
| `icon` | 图标，LONGTEXT |
| `name` | 中文名称，VARCHAR(255)，支持模糊搜索 |
| `name_en` | 英文名称，VARCHAR(255) |
| `description` | 中文描述，VARCHAR(2048) |
| `description_en` | 英文描述，VARCHAR(2048) |
| `readme` | 服务简介，LONGTEXT |
| `server_config` | 服务端配置，LONGTEXT，JSON格式 |
| `tools` | 工具列表，LONGTEXT，JSON格式 |
| `org_type` | 部署方式，VARCHAR(64)，枚举值：`SSE`、`NPX`、`UVX`、`streamable_http`；HCS场景需设为 `SSE` |
| `url` | MCP服务连接地址，VARCHAR(255) |
| `category` | 行业分类ID，VARCHAR(36)，外键关联 `t_pe_industry.id` |

**预置SQL示例**：

```sql
INSERT INTO ws_mcp_server_def (id, server_code, icon, name, name_en, description,
    description_en, readme, server_config, tools, type, org_type, url, category,
    tenant_id, created_date, last_updated_date)
VALUES (UUID(), '{server_code}', '{icon_url}', '{name}', '{name_en}',
    '{description}', '{description_en}',
    '{readme_content}', '{server_config_json}', '{tools_json}',
    'inner', '{org_type}', '{url}', '{category}',
    'SYSTEM', NOW(), NOW());
```

> **注意**：`server_config` 和 `tools` 为JSON格式，需提前定义好MCP服务连接参数和工具描述。`category` 外键关联 `t_pe_industry.id`，需确保行业分类数据已存在。

---

## 四、插件

预置插件需写入OBS和数据库两处，查询时通过 `type = 'inner'` 筛选官方预置插件。预置插件的 `workspace_id` 设为 `'default'`。

### 步骤一：OBS写入

将插件DSL JSON上传到OBS，路径格式：`plugin/dsl/{plugin_id}/{plugin_id}_{version_id}.json`

### 步骤二：数据库写入

**`t_tool` 字段说明**：

| 字段 | 说明 |
|------|------|
| `project_id` | 设为 `op.svc.project-id` 配置值（来源于环境变量 `op_svc_project_id`，默认为空）；若部署环境为该变量配置了其他值，需同步修改 |
| `tool_display_name` | 英文显示名，VARCHAR(64) |
| `tool_chinese_name` | 中文显示名，VARCHAR(64) |
| `tool_desc` | 描述，VARCHAR(600) |
| `icon` | 图标，MEDIUMTEXT |
| `icon_name` | 图标名称，VARCHAR(64) |
| `request_info` | 请求信息，MEDIUMTEXT，JSON格式 |
| `auth_info` | 鉴权信息，MEDIUMTEXT |
| `input_schema` | 入参JsonSchema，MEDIUMTEXT |
| `output_schema` | 出参JsonSchema，MEDIUMTEXT |
| `intf_type` | 接口类型，MEDIUMTEXT，枚举值：`blocking`（默认）、`streaming` |
| `call_mode` | 执行类型，VARCHAR(16)，枚举值：`api`（默认，API类型）、`functiongraph`（函数类型） |
| `is_free` | 是否免费，TINYINT，枚举值：`0`（未知/非免费）、`1`（免费额度插件）、`2`（付费） |
| `last_version_id` | 最新版本号，VARCHAR(64)，与 `t_release_version.version_id` 一致 |
| `category` | 分类ID，VARCHAR(36)，外键关联 `t_pe_industry.id` |
| `label` | 插件类型标签，VARCHAR(32)，枚举值：`normal`（默认，普通插件）、`deepsearch`（深度搜索） |

**`t_release_version` 字段说明**：

| 字段 | 说明 |
|------|------|
| `version_id` | 版本ID，VARCHAR(64)，时间戳 |
| `app_id` | 关联插件ID |
| `version_name` | 版本名称，VARCHAR(64) |
| `dsl_path` | OBS上版本DSL文件路径，即步骤一上传的路径，供 `getToolEntityByVersion` 等接口下载DSL |

**预置SQL示例**：

```sql
INSERT INTO t_tool (tool_id, project_id, workspace_id, tool_display_name, tool_chinese_name,
    tool_desc, icon, icon_name, visibility, request_info, auth_info,
    input_schema, output_schema, intf_type, type, published, call_mode,
    is_free, is_input_list, is_output_list, creator, last_version_id, category, label, is_share)
VALUES (UUID(), '', 'default', '{tool_display_name}', '{tool_chinese_name}',
    '{tool_desc}', '{icon}', '{icon_name}', 'global', '{request_info}', '{auth_info}',
    '{input_schema}', '{output_schema}', '{intf_type}', 'inner', 1, '{call_mode}',
    '{is_free}', '0', '0', 'SYSTEM', '{version_id}', '{category}', '{label}', 0);

INSERT INTO t_release_version (version_id, app_id, version_name, dsl_path, status)
VALUES ('{version_id}', '{plugin_id}', '{version_name}', 'plugin/dsl/{plugin_id}/{plugin_id}_{version_id}.json', 'released');
```

> **注意**：`published = 1` 是插件列表查询的必要条件；`t_release_version` 和 OBS 中的 DSL 文件为插件被智能体/工作流引用时提供版本定义，缺少则分享、关联、导入等功能会报错。

---

## 五、提示词

预置提示词只需向 `t_pe_prompt_library` 表插入记录，查询时通过 `source = 'PRESET'` 筛选官方预置提示词。

**字段说明**：

| 字段 | 说明 |
|------|------|
| `id` | 主键，VARCHAR(36)，UUID |
| `name` | 模板名称，VARCHAR(255)，支持模糊搜索 |
| `content` | 提示词内容，TEXT |
| `variables` | 变量定义，TEXT，JSON数组 |
| `pt_type` | 模板类型，VARCHAR(36) |
| `industry_id` | 行业分类ID，VARCHAR(36)，外键关联 `t_pe_industry.id` |
| `description` | 描述，VARCHAR(255) |

**预置SQL示例**：

```sql
INSERT INTO t_pe_prompt_library (id, project_id, workspace_id, domain_id, name, content,
    description, source, industry_id, pt_type, variables, creator, updater, is_share)
VALUES (UUID(), 'SYSTEM', 'SYSTEM', '0', '{name}', '{content}',
    '{description}', 'PRESET', '{industry_id}', NULL, '[]', 'SYSTEM', 'SYSTEM', 0);
```

**关联标签（可选）**：

| 表 | 说明 |
|------|------|
| `t_pe_tag` | 标签定义 |
| `t_mapping_pe_template_tag` | 模板-标签关联（`template_id` + `tag_id`） |
| `t_pe_industry` | 行业定义 |

```sql
INSERT INTO t_mapping_pe_template_tag (template_id, tag_id, workspace_id)
VALUES ('{template_id}', '{tag_id}', '{workspace_id}');
```

---

## 六、Skill

预置 Skill 需写入OBS和数据库两处，查询时通过 `published_asset = 1` 筛选资产广场预置Skill。

### 步骤一：OBS写入

将Skill制品包（ZIP）上传到OBS，路径格式：`skill/{skill_id}/{version_id}/package.zip`

### 步骤二：数据库写入

**`t_skill` 字段说明**：

| 字段 | 说明 |
|------|------|
| `skill_id` | 主键，VARCHAR(64)，UUID |
| `name` | 技能名称，VARCHAR(64)，支持模糊搜索 |
| `icon` | 图标，MEDIUMTEXT，Base64 |
| `description` | 技能描述，VARCHAR(1024) |
| `status` | 状态，VARCHAR(32)，枚举值：`developed`（可用）、`developing`（开发中） |
| `source` | 来源，VARCHAR(32)，枚举值：`custom`（自定义）、`import`（导入） |
| `published_asset` | 是否上架资产广场，VARCHAR(64)，**预置必须设为 `1`**，默认 `0` |
| `latest_version` | 最新版本号，VARCHAR(64)，与 `t_skill_version.id` 一致 |
| `used_version` | 启用的版本号，VARCHAR(64) |
| `project_id` | 项目ID，VARCHAR(64)，查询时按此过滤，需设为用户实际项目ID |
| `workspace_id` | 工作空间ID，VARCHAR(64)，查询时按此过滤，需设为用户实际工作空间ID |
| `tag_id` | 资产分类，VARCHAR(64) |

**`t_skill_version` 字段说明**：

| 字段 | 说明 |
|------|------|
| `id` | 版本唯一标识，VARCHAR(64)，UUID |
| `skill_id` | 关联Skill ID，VARCHAR(64) |
| `version_name` | 版本名称，VARCHAR(32) |
| `name` | 名称，VARCHAR(64) |
| `description` | 版本描述，VARCHAR(1024) |
| `obs_path` | 制品包OBS路径，即步骤一上传的路径，查询时用于生成临时下载URL |

**预置SQL示例**：

```sql
INSERT INTO t_skill (skill_id, domain_id, name, icon, description, status, source,
    published_asset, project_id, workspace_id, latest_version, used_version, tag_id,
    creator_id, creator_name, created_at, updated_at)
VALUES (UUID(), '0', '{name}', '{icon_base64}', '{description}',
    'developed', 'import', '1', '{project_id}', '{workspace_id}',
    '{version_id}', '{version_id}', '{tag_id}',
    'SYSTEM', 'SYSTEM', UNIX_TIMESTAMP(), UNIX_TIMESTAMP());

INSERT INTO t_skill_version (id, skill_id, version_name, name, description,
    obs_path, used, creator_id, creator_name, created_at)
VALUES ('{version_id}', '{skill_id}', '{version_name}', '{name}', '{description}',
    'skill/{skill_id}/{version_id}/package.zip', 0, 'SYSTEM', 'SYSTEM', UNIX_TIMESTAMP());
```

> **注意**：`obs_path` 中的路径需与步骤一实际上传路径一致。
