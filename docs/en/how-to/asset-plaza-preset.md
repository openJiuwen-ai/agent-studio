# Asset Plaza Preset Guide

- [1. Application Templates](#1-application-templates)
- [2. Models](#2-models)
- [3. MCP](#3-mcp)
- [4. Plugins](#4-plugins)
- [5. Prompts](#5-prompts)
- [6. Skill](#6-skill)

---

## 1. Application Templates

List published agents or workflows to the Asset Plaza for users to browse, experience, and copy. Prerequisite: resources have been created in the system and versions published. **Multi-agent is not currently supported**.

### Single-agent

**Step 1: Query agent information**

```sql
SELECT agent_id, project_id, workspace_id, name, description, icon, prologue, suggest_queries
FROM t_agent WHERE (agent_id = '{agent_id}' OR name = '{agent_name}') AND deleted = 0;
```

**Step 2: Query published version DSL/IR paths**

```sql
SELECT version_id, dsl_path, ir_path FROM t_release_version
WHERE app_id = '{agent_id}' AND deleted = 0
ORDER BY released_on DESC LIMIT 1;
```

Record the query results from Steps 1 and 2; they are needed in subsequent steps.

**Step 3: Upload `_published.json` to OBS**

Copy the DSL/IR file found in Step 2, rename it to `{id}_published.json`, and place it in the same directory. The path is based on the `dsl_path` and `ir_path` found in Step 2.

> **Note**: Runtime "instant experience" reads IR by concatenating the path, fixed as `{id}_published.json`, without version numbers.

**Step 4: Insert into `t_agent_version`**

For "copy to workspace" to read DSL and for runtime to confirm online status.

| Field | Description |
|-------|-------------|
| `version_id` | Version unique identifier, VARCHAR(64), UUID |
| `agent_id` | Associated agent ID, VARCHAR(64) |
| `project_id` | Project ID, VARCHAR(64) |
| `ir_path` | IR file OBS relative path, i.e. the `_published.json` path from Step 3 |
| `dsl_path` | DSL file OBS relative path, i.e. the `_published.json` path from Step 3 |

```sql
INSERT INTO t_agent_version (version_id, agent_id, project_id, ir_path, dsl_path, is_online, creator,
    created_on, updated_on, published_on)
VALUES (UUID(), '{agent_id}', '{project_id}',
    'agent/ir/{agent_id}/{agent_id}_published.json',
    'agent/dsl/{agent_id}/{agent_id}_published.json',
    1, 'SYSTEM', NOW(), NOW(), NOW());
```

> The path is based on the actual result of Step 3; the above SQL uses example values.

**Step 5: Insert into `t_app`**

| Field | Description |
|-------|-------------|
| `app_id` | Primary key, VARCHAR(64), UUID |
| `project_id` | Project ID, VARCHAR(64) |
| `name` | Application name, VARCHAR(64), supports fuzzy search |
| `description` | Application description, VARCHAR(1024) |
| `icon` | Application icon, MEDIUMTEXT, icon URL or Base64 |
| `tags` | Tag IDs, VARCHAR(512), **cannot be null**; value is a JSON array of `t_tag.tag_id` list (tag data is inserted into `t_tag` table by initialization SQL), e.g. `["tag_id_1","tag_id_2"]`; set to `[]` when no tags |
| `resource_id` | Associated agent ID, VARCHAR(64), i.e. `agent_id` |

```sql
INSERT INTO t_app (app_id, project_id, workspace_id, name, description, icon, tags,
    app_type, resource_id, resource_type, creator, published_on, deleted)
VALUES (UUID(), '{project_id}', '{workspace_id}', '{name}', '{description}', '{icon}',
    '["tag_id_1","tag_id_2"]', 'chat', '{agent_id}', 'agent', 'SYSTEM', NOW(), 0);
```

### Workflow

**Step 1: Query workflow information**

```sql
SELECT id, project_id, workspace_id, name, description, avatar, workflow_type
FROM t_agent_workflow WHERE (id = '{workflow_id}' OR name = '{workflow_name}') AND deleted = 0;
```

**Step 2: Query published version**

```sql
SELECT version_id, version_name, dsl_path, ir_path FROM t_release_version
WHERE app_id = '{workflow_id}' AND deleted = 0
ORDER BY released_on DESC LIMIT 1;
```

Record the query results from Steps 1 and 2; they are needed in subsequent steps.

**Step 3: Insert into `t_release_channel`**

Workflow "view details" and "copy to workspace" use `t_release_channel` (`channel_type='app_store'`) to associate with `t_release_version` to get DSL/IR.

> **Note**: Only one record can exist per `app_id` + `channel_type='app_store'`, otherwise the query will error. Confirm whether it already exists before inserting; if it exists, update instead of inserting again.

| Field | Description |
|-------|-------------|
| `id` | Primary key, VARCHAR(64), UUID |
| `app_id` | Workflow ID, VARCHAR(64) |
| `app_type` | Application type, VARCHAR(32), set to `workflow` |
| `version_id` | Associated version ID, VARCHAR(64), matches `t_release_version.version_id` |
| `version_name` | Version name, VARCHAR(64) |
| `channel_type` | Release channel type, VARCHAR(32), **must be set to `app_store`** |
| `project_id` | Project ID, VARCHAR(64) |
| `workspace_id` | Workspace ID, VARCHAR(64) |

```sql
INSERT INTO t_release_channel (id, app_id, app_type, version_id, version_name, channel_type,
    status, project_id, workspace_id)
VALUES (UUID(), '{workflow_id}', 'workflow', '{version_id}', '{version_name}', 'app_store',
    'released', '{project_id}', '{workspace_id}');
```

**Step 4: Insert into `t_app`**

| Field | Description |
|-------|-------------|
| `app_id` | Primary key, VARCHAR(64), UUID |
| `project_id` | Project ID, VARCHAR(64) |
| `workspace_id` | Workspace ID, VARCHAR(64) |
| `name` | Application name, VARCHAR(64), supports fuzzy search |
| `description` | Application description, VARCHAR(1024) |
| `icon` | Application icon, MEDIUMTEXT, icon URL or Base64 |
| `tags` | Tag IDs, VARCHAR(512), **cannot be null**; value is a JSON array of `t_tag.tag_id` list, e.g. `["tag_id_1","tag_id_2"]`; set to `[]` when no tags |
| `resource_id` | Associated workflow ID, VARCHAR(64) |
| `workflow_type` | Workflow type, VARCHAR(16), enum: `chat` (conversational), `task` (task-oriented) |

```sql
INSERT INTO t_app (app_id, project_id, workspace_id, name, description, icon, tags,
    app_type, resource_id, resource_type, workflow_type, creator, published_on, deleted)
VALUES (UUID(), '{project_id}', '{workspace_id}', '{name}', '{description}', '{icon}',
    '["tag_id_1","tag_id_2"]', 'scene', '{workflow_id}', 'workflow', '{workflow_type}', 'SYSTEM', NOW(), 0);
```

---

## 2. Models

Model preset requires writing to both database and OBS.

### Step 1: Database Write

**Field descriptions**:

| Field | Description |
|-------|-------------|
| `ID` | Primary key, VARCHAR(80), UUID |
| `SERVICE_NAME` | Service name, VARCHAR(64) |
| `SERVICE_KEY` | Model service key, VARCHAR(128), format `publisher:maas:{modelName}` |
| `MODEL_NAME` | Model name, VARCHAR(64) |
| `MODEL_VERSION` | Model version, VARCHAR(64) |
| `MODEL_TYPE` | Model function type, VARCHAR(32), enum: `LLM`, `TEXT-TO-IMAGE`, `IMAGE-TO-TEXT`, `AUDIO-TO-TEXT`, `Text-Embedding`, `Text-Multimodal-Embedding`, `RERANK`, `TEXT-TO-VIDEO` |
| `API_URL` | API address, VARCHAR(256) |
| `INTERFACE_PROTOCOL` | Interface protocol, VARCHAR(32), determines the request adapter when runtime calls the model API. Enum: `maasv2` (MaaS V2 protocol), `maasv1` (MaaS V1 protocol), `openai` (OpenAI compatible), `baichuan` (Baichuan), `qwen` (Tongyi Qwen), `moonshot` (Moonshot), `minimax` (MiniMax), `zhipu` (Zhipu), `maas_embedding` (MaaS Embedding), `maas_rerank` (MaaS Rerank), `multi_openai` (Multi-OpenAI compatible) |
| `MODEL_DESCRIPTION` | Model description, TEXT |
| `MODEL_DESCRIPTION_EN` | Model English description, TEXT |
| `MODEL_TAGS` | Model tags, TEXT, comma-separated |
| `IS_REASONING` | Whether reasoning is supported, TINYINT |
| `IS_SUPPORT_CLOSE_REASONING` | Deep thinking switch, TINYINT |
| `CONTEXT_LENGTH` | Context length, INT, applicable to LLMs |
| `LOGO` | LOGO, LONGTEXT, Base64 |

**Preset SQL example**:

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

> **Important**: Database and OBS content must be consistent. `PROVIDER_ID` identifies the model's provider; when set to `platform_provider_id` config value (default `'100'`), the model is recognized as a platform free model and can be used without authentication; `AUTH_METADATA_ID` associates the auth metadata definition in the `t_provider_auth_metadata` table; `'1022'` is the `API_KEY` type auth definition preset by the initialization SQL for provider `'100'`; the two are used together.

### Step 2: OBS Write

Upload the `ModelStrategy` JSON to OBS, path format: `model-service/ir/{id}.json`

---

## 3. MCP

Presetting MCP only requires inserting records into the `ws_mcp_server_def` table; query with `type = 'inner'` to filter official preset MCPs.

**Field descriptions**:

| Field | Description |
|-------|-------------|
| `server_code` | MCP service code, VARCHAR(255) |
| `icon` | Icon, LONGTEXT |
| `name` | Chinese name, VARCHAR(255), supports fuzzy search |
| `name_en` | English name, VARCHAR(255) |
| `description` | Chinese description, VARCHAR(2048) |
| `description_en` | English description, VARCHAR(2048) |
| `readme` | Service introduction, LONGTEXT |
| `server_config` | Server-side config, LONGTEXT, JSON format |
| `tools` | Tool list, LONGTEXT, JSON format |
| `org_type` | Deployment type, VARCHAR(64), enum: `SSE`, `NPX`, `UVX`, `streamable_http`; HCS scenario must be set to `SSE` |
| `url` | MCP service connection address, VARCHAR(255) |
| `category` | Industry category ID, VARCHAR(36), foreign key to `t_pe_industry.id` |

**Preset SQL example**:

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

> **Note**: `server_config` and `tools` are in JSON format; MCP service connection parameters and tool descriptions must be defined in advance. `category` foreign key references `t_pe_industry.id`; ensure industry category data already exists.

---

## 4. Plugins

Presetting plugins requires writing to both OBS and database; query with `type = 'inner'` to filter official preset plugins. The `workspace_id` for preset plugins is set to `'default'`.

### Step 1: OBS Write

Upload the plugin DSL JSON to OBS, path format: `plugin/dsl/{plugin_id}/{plugin_id}_{version_id}.json`

### Step 2: Database Write

**`t_tool` field descriptions**:

| Field | Description |
|-------|-------------|
| `project_id` | Set to `op.svc.project-id` config value (from env var `op_svc_project_id`, default empty); if the deployment environment has a different value configured, modify accordingly |
| `tool_display_name` | English display name, VARCHAR(64) |
| `tool_chinese_name` | Chinese display name, VARCHAR(64) |
| `tool_desc` | Description, VARCHAR(600) |
| `icon` | Icon, MEDIUMTEXT |
| `icon_name` | Icon name, VARCHAR(64) |
| `request_info` | Request info, MEDIUMTEXT, JSON format |
| `auth_info` | Auth info, MEDIUMTEXT |
| `input_schema` | Input JsonSchema, MEDIUMTEXT |
| `output_schema` | Output JsonSchema, MEDIUMTEXT |
| `intf_type` | Interface type, MEDIUMTEXT, enum: `blocking` (default), `streaming` |
| `call_mode` | Execution type, VARCHAR(16), enum: `api` (default, API type), `functiongraph` (function type) |
| `is_free` | Whether free, TINYINT, enum: `0` (unknown/non-free), `1` (free quota plugin), `2` (paid) |
| `last_version_id` | Latest version number, VARCHAR(64), matches `t_release_version.version_id` |
| `category` | Category ID, VARCHAR(36), foreign key to `t_pe_industry.id` |
| `label` | Plugin type tag, VARCHAR(32), enum: `normal` (default, regular plugin), `deepsearch` (deep search) |

**`t_release_version` field descriptions**:

| Field | Description |
|-------|-------------|
| `version_id` | Version ID, VARCHAR(64), timestamp |
| `app_id` | Associated plugin ID |
| `version_name` | Version name, VARCHAR(64) |
| `dsl_path` | OBS path to version DSL file, i.e. the path uploaded in Step 1, used by `getToolEntityByVersion` and similar APIs to download DSL |

**Preset SQL example**:

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

> **Note**: `published = 1` is a required condition for plugin list queries; `t_release_version` and the DSL file in OBS provide version definitions when plugins are referenced by agents/workflows; missing these will cause errors in sharing, association, import and other features.

---

## 5. Prompts

Presetting prompts only requires inserting records into the `t_pe_prompt_library` table; query with `source = 'PRESET'` to filter official preset prompts.

**Field descriptions**:

| Field | Description |
|-------|-------------|
| `id` | Primary key, VARCHAR(36), UUID |
| `name` | Template name, VARCHAR(255), supports fuzzy search |
| `content` | Prompt content, TEXT |
| `variables` | Variable definitions, TEXT, JSON array |
| `pt_type` | Template type, VARCHAR(36) |
| `industry_id` | Industry category ID, VARCHAR(36), foreign key to `t_pe_industry.id` |
| `description` | Description, VARCHAR(255) |

**Preset SQL example**:

```sql
INSERT INTO t_pe_prompt_library (id, project_id, workspace_id, domain_id, name, content,
    description, source, industry_id, pt_type, variables, creator, updater, is_share)
VALUES (UUID(), 'SYSTEM', 'SYSTEM', '0', '{name}', '{content}',
    '{description}', 'PRESET', '{industry_id}', NULL, '[]', 'SYSTEM', 'SYSTEM', 0);
```

**Associated tags (optional)**:

| Table | Description |
|-------|-------------|
| `t_pe_tag` | Tag definitions |
| `t_mapping_pe_template_tag` | Template-tag association (`template_id` + `tag_id`) |
| `t_pe_industry` | Industry definitions |

```sql
INSERT INTO t_mapping_pe_template_tag (template_id, tag_id, workspace_id)
VALUES ('{template_id}', '{tag_id}', '{workspace_id}');
```

---

## 6. Skill

Presetting Skill requires writing to both OBS and database; query with `published_asset = 1` to filter Asset Plaza preset Skills.

### Step 1: OBS Write

Upload the Skill artifact package (ZIP) to OBS, path format: `skill/{skill_id}/{version_id}/package.zip`

### Step 2: Database Write

**`t_skill` field descriptions**:

| Field | Description |
|-------|-------------|
| `skill_id` | Primary key, VARCHAR(64), UUID |
| `name` | Skill name, VARCHAR(64), supports fuzzy search |
| `icon` | Icon, MEDIUMTEXT, Base64 |
| `description` | Skill description, VARCHAR(1024) |
| `status` | Status, VARCHAR(32), enum: `developed` (available), `developing` (in development) |
| `source` | Source, VARCHAR(32), enum: `custom` (custom), `import` (imported) |
| `published_asset` | Whether listed on Asset Plaza, VARCHAR(64), **preset must be set to `1`**, default `0` |
| `latest_version` | Latest version number, VARCHAR(64), matches `t_skill_version.id` |
| `used_version` | Active version number, VARCHAR(64) |
| `project_id` | Project ID, VARCHAR(64), filtered by this in queries; must be set to the user's actual project ID |
| `workspace_id` | Workspace ID, VARCHAR(64), filtered by this in queries; must be set to the user's actual workspace ID |
| `tag_id` | Asset category, VARCHAR(64) |

**`t_skill_version` field descriptions**:

| Field | Description |
|-------|-------------|
| `id` | Version unique identifier, VARCHAR(64), UUID |
| `skill_id` | Associated Skill ID, VARCHAR(64) |
| `version_name` | Version name, VARCHAR(32) |
| `name` | Name, VARCHAR(64) |
| `description` | Version description, VARCHAR(1024) |
| `obs_path` | Artifact package OBS path, i.e. the path uploaded in Step 1; used to generate temporary download URL in queries |

**Preset SQL example**:

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

> **Note**: The path in `obs_path` must match the actual upload path in Step 1.
