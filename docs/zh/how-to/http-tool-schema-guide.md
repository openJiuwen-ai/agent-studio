# HTTP 工具 Schema 约定说明

> 本文说明 Studio 中 **HTTP / OpenAPI 插件工具** 的：  
> （1）创建/更新工具 **整份请求体字段**；（2）`input_schema` / `output_schema` 写法与校验规则。  
> 目标读者：通过 API、导入 JSON 或手工拼 schema 注册工具的开发者与实施同学。  
> 界面「创建工具」向导会自动生成合规 schema；本文覆盖向导背后的契约，避免试错。

关联能力：`call_mode = api` 的插件工具（把外部 HTTP API 登记为 Agent / 工作流可调用的工具）。  
自定义 Python 插件（`call_mode = custom`）请另见 [自定义插件开发指南](./custom-plugin-development-guide.md)。

---

## 一、创建 / 更新工具请求体字段

本节说明 **整份建工具请求**（不是某个业务工具实例）。  
接口分两条（校验同一套 `JsonSchemaUtils`）：

| 接口 | 路径 | 形态 |
|------|------|------|
| **v1 独立工具** | `POST/PUT /v1/{project_id}/agent-manager/tools` | 一条独立 Tool 记录 |
| **v2 插件工具** | `POST/PUT /v2/{project_id}/agent-manager/tools` | 挂在已有插件下（需 `plugin_id`）；UI「创建工具 / 更新工具」走这条 |

查询参数均需带 `workspace_id`。

### 1.1 顶层字段（CreateToolReq / CreatePluginToolReq）

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `plugin_id` | string | v2 **必填**；v1 可选 | 所属插件 ID。v2 创建/修改工具必须指向已有插件 |
| `tool_display_name` | string | **必填** | 英文标识。v1：`^[a-zA-Z0-9_]+$`，1–64；v2 插件工具常见 `^[a-zA-Z0-9_]{2,64}$`。UI「名称」 |
| `tool_chinese_name` | string | 视接口 | 中文展示名，1–64。UI「展示名称」。v2 创建时常为必填 |
| `tool_desc` | string | **必填**（多数路径） | 工具说明，1–600。UI「描述」（工具级，**不是**参数 `description`） |
| `icon` | string | 否 | 图标 URL 或资源名 |
| `request_info` | object | **是**（本文 HTTP/`api` 工具） | 见下表。须含合法 `url` / `method`；缺省返回业务错误（`02401001`），不会以 500 落库 |
| `auth_info` | object | 否 | 鉴权配置（Service / IAM / HIS_IAM 等）；结构见鉴权相关文档 |
| `visibility` | string | 否 | 可见性，如 `project` / `user` 等；不传时服务端默认 `project`；非法值会报错 |
| `intf_type` | string | 否 | 接口形态。常见：`blocking`（同步）、`streaming`（流式；流式时可能跳过出参 schema 校验）。UI/历史数据里也可能出现其它取值 |
| `call_mode` | string | 插件侧 | 多为 `api`（HTTP）或 `custom`（Python 等）。本文仅覆盖 `api` |
| `input_schema` | **JSON 字符串** | 否（空=无入参） | 入参契约，见第二节起。**最大约 200000 字符** |
| `output_schema` | **JSON 字符串** | 否（空=无出参） | 出参契约。**最大约 200000 字符** |
| `is_input_list` | boolean | 否 | 默认 `false`。为 `true` 时入参按列表封装（UI「参数封装」） |
| `is_output_list` | boolean | 否 | 默认 `false`。出参是否按列表 |
| `metadata` | string | 否 | 元数据 JSON 字符串，最长约 4096 |
| `auth_required` | boolean | 否 | 是否需要认证，默认 `false` |
| `test_status` | string | 否（修改工具） | 如 `SUCCESS` / `FAILED`；影响工具调试状态落库 |

### 1.2 `request_info` 子字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | **必填** | 完整 HTTP(S) URL，长度约 8–256；禁止内网地址等受 `UrlCheckUtils` 约束。v2 下常拼在插件 `basic_info`（protocol/host/path）之后，服务端再拆出工具 `path` |
| `method` | enum | **必填** | 当前 `RequestInfo.MethodEnum` 仅 **`GET`** / **`POST`** |
| `headers` | object\<string,string\> | 否 | 静态请求头，如 `{"Content-Type":"application/json"}` |
| `path_params` | string | 否 | 路径参数补充，最长约 2000 |
| `input_schema` | string | 否 | 少数路径会把 schema 挂在 `request_info` 内；**正式工具入参请用顶层 `input_schema`** |

### 1.3 Schema 字段传输注意

- `input_schema` / `output_schema` 存库与接口传输时是 **字符串**，内容本身是一段 JSON。写入前需正确转义，或由前端 `JSON.stringify` 后提交。
- 空串 / `null` 表示无参数，`JsonSchemaUtils` 会直接通过。
- 根节点必须是带 `type` 的 schema 节点；有属性时通常为：

```json
{
  "type": "object",
  "properties": { "...": "见下文" },
  "required": ["必填参数名列表"]
}
```

---

## 二、支持的类型

每个属性节点必须有 `type`。当前平台识别：

| `type` | 说明 |
|--------|------|
| `string` | 字符串 |
| `number` | 数值（可含小数） |
| `integer` | 整数 |
| `boolean` | 布尔 |
| `null` | 空（一般由示例反推生成；创建工具类型下拉里通常不直接选） |
| `object` | 对象，必须带 `properties` |
| `array` | 数组，必须带 `items` |
| `file/<子类型>` | 仅 **入参**（出参 UI 不支持 File）。后端按 `file/` 前缀放行 |

**`file/<子类型>`**（与创建工具 UI 级联一致，落库为完整字符串）：

| 落库 `type` | UI 叶子 | 说明 |
|-------------|---------|------|
| `file/default` | Default | 通用文件 |
| `file/doc` | Doc | 文档 |
| `file/txt` | Txt | 文本 |
| `file/excel` | Excel | 表格 |
| `file/ppt` | PPT | 演示文稿 |
| `file/image` | Image | 图片 |
| `file/audio` | Audio | 音频 |
| `file/video` | Video | 视频 |

含 `file/*` 入参时，调测/调用侧往往会按 **multipart/form-data** 处理，而不是纯 JSON Body。`file/*` **只能**放在 `location = Body`（Query / Headers / Path 上 UI 会禁用）。

**不支持**标准 JSON Schema 的：

- `additionalProperties`（出现即校验失败）
- `oneOf` / `anyOf` / `allOf` 等组合关键字（前端类型上有预留，后端校验不认）
- 数组嵌套数组（`items.type === "array"`）

UI 中常见的 `array<string>`、`array<object>` 等是界面扁平写法，**落库 / 接口提交时会转成** `type: "array"` + `items`。
---

## 三、入参属性必填与私有字段

对 `input_schema`：根节点（depth = 0）不校验私有字段；**`properties` 下每一个属性**（以及 object 嵌套下去的属性）需要满足下表。  
`items` 内的元素 schema **不强制** `description` / `location`（但 `items` 不能再是 array）。

### 3.1 标准 / 平台共有字段

| 字段 | 是否必填（入参属性） | 说明 |
|------|----------------------|------|
| `type` | 必填 | 见第二节 |
| `description` | **必填且非空** | 参数说明；缺省会报 `02401002` |
| `location` | **必填** | 仅允许：`Body` / `Headers` / `Query` / `Path`（大小写敏感，首字母大写） |
| `default` | 可选 | 有值时须与类型匹配：`number` / `integer` / `boolean` 会做格式检查；`file/*` 默认值按字符串放行 |
| `properties` | `type=object` 时必填 | 至少包含 1 个属性；不可用 `additionalProperties` 代替 |
| `items` | `type=array` 时必填 | 元素类型为标量、`object` 或 `file/*`，**不能**再是 `array` |
| `required` | 可选 | 字符串数组，列出本层必填属性名 |

### 3.2 平台私有字段（非标准 JSON Schema）

这些字段写在属性节点上，供 UI 校验、中文名展示、工作流绑定等使用；**后端 `JsonSchemaUtils` 创建/更新工具时强制的是 `description` + `location`（及 type/结构）**，下列私有字段不参与 02401002 结构校验，但 UI / 运行态会用到。

| 字段 | 含义 | 常见取值 |
|------|------|----------|
| `name_cn` | 参数中文名（展示用） | 字符串，可空；对应 UI「中文名称」 |
| `validated` | 是否启用参数校验 | `true` / `false`；对应 UI「参数校验」勾选 |
| `validate_type` | 校验类型 | 见下表；未启用校验时可空字符串 |
| `validate_rule` | 校验规则内容 | 随 `validate_type` 变化；可空 |
| `env_var_ref` | 绑定的环境变量名 | 有值时工作流侧可自动绑同名环境变量（Path 等场景常见） |

**`validate_type`（创建工具 UI）**

| `validate_type` | 适用参数 `type` | `validate_rule` 含义（UI） |
|-----------------|-----------------|---------------------------|
| `CHAR` | `string`（默认） | 字符类规则；常为空，或按产品配置填长度/正则等 |
| `ENUM` | `string` | 枚举可选值列表（由 UI 编辑） |
| `DATE` | `string` | 日期/时间格式约束 |
| `NUM` | `number` / `integer` | 数值类规则（范围等，由 UI 编辑） |

切换参数类型时，UI 会重置默认 `validate_type`（字符串→`CHAR`，数值→`NUM`；`object` / `array` / `file/*` 通常清空校验相关字段）。

出参（`output_schema`）**不要求** `description` / `location`，也一般不带上述入参私有字段。
### 3.3 `location` 与 UI / OpenAPI 导出注意

| location | UI 创建工具 | 说明 |
|----------|-----------|------|
| `Body` | 可选 string / number / integer / boolean / object / array&lt;*&gt; / file/* | 嵌套对象、数组主要放在 Body |
| `Headers` / `Query` / `Path` | 可选基础标量；object / array / file 在界面上禁用 | Path 常用于 URL 路径变量 |

导出 OpenAPI 时，Header / Query / Path 参数目前会落成 **string schema**（类型信息可能被收窄）。需要保留复杂结构时，请放在 `Body`。

---

## 四、数组与嵌套规则

### 4.1 合法示例：数组元素为标量

```json
{
  "type": "object",
  "properties": {
    "tags": {
      "type": "array",
      "description": "标签列表",
      "location": "Body",
      "name_cn": "标签",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": "",
      "items": { "type": "string" }
    }
  },
  "required": ["tags"]
}
```

### 4.2 合法示例：数组元素为对象

```json
{
  "type": "object",
  "properties": {
    "items": {
      "type": "array",
      "description": "明细行",
      "location": "Body",
      "name_cn": "明细",
      "validated": false,
      "validate_type": "",
      "validate_rule": "",
      "items": {
        "type": "object",
        "properties": {
          "sku": {
            "type": "string",
            "description": "SKU 编码",
            "location": "Body",
            "name_cn": "SKU",
            "validated": false,
            "validate_type": "CHAR",
            "validate_rule": ""
          },
          "qty": {
            "type": "integer",
            "description": "数量",
            "location": "Body",
            "name_cn": "数量",
            "validated": false,
            "validate_type": "NUM",
            "validate_rule": ""
          }
        },
        "required": ["sku", "qty"]
      }
    }
  }
}
```

### 4.3 非法：属性下的数组嵌套数组

嵌套数组校验在 `depth > 0` 时生效。入参属性挂在 `properties` 下时 depth ≥ 1，下列写法会失败：

```json
{
  "type": "object",
  "properties": {
    "matrix": {
      "type": "array",
      "description": "二维矩阵",
      "location": "Body",
      "items": {
        "type": "array",
        "items": { "type": "string" }
      }
    }
  },
  "required": ["matrix"]
}
```

错误细节类似：`The parameter [matrix] cannot be nested array.`

说明：若**根节点**即为 `type: array` 且 `items` 再为 `array`（无外层 object 属性），当前实现里 items 深度仍为 0，**不会**触发上述嵌套数组校验（历史行为）。实际工具入参几乎总是根 `object` + `properties`，请以本节属性级示例为准。

### 4.4 嵌套深度与属性数量

配置项（`studio-manager`）：

| 配置 | 环境变量 | 默认值 | 含义 |
|------|----------|--------|------|
| `tool.jsonschema.max-prop-num` | `tool_jsonschema_max_prop_num` | `1000` | 每一层 `properties` 的属性个数上限 |
| `tool.jsonschema.max-prop-depth` | `tool_jsonschema_max_prop_depth` | `4` | 最大嵌套深度 |

超限会在校验阶段抛错（错误码见下节）。

---

## 五、完整入参示例

```json
{
  "type": "object",
  "properties": {
    "Authorization": {
      "type": "string",
      "description": "Bearer Token",
      "location": "Headers",
      "name_cn": "鉴权头",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": ""
    },
    "page": {
      "type": "integer",
      "description": "页码",
      "location": "Query",
      "default": "1",
      "name_cn": "页码",
      "validated": false,
      "validate_type": "NUM",
      "validate_rule": ""
    },
    "orderId": {
      "type": "string",
      "description": "订单 ID",
      "location": "Path",
      "name_cn": "订单ID",
      "validated": false,
      "validate_type": "CHAR",
      "validate_rule": ""
    },
    "payload": {
      "type": "object",
      "description": "请求体",
      "location": "Body",
      "name_cn": "请求体",
      "validated": false,
      "validate_type": "",
      "validate_rule": "",
      "properties": {
        "name": {
          "type": "string",
          "description": "名称",
          "location": "Body",
          "name_cn": "名称",
          "validated": true,
          "validate_type": "CHAR",
          "validate_rule": ""
        }
      },
      "required": ["name"]
    }
  },
  "required": ["orderId", "payload"]
}
```

提交接口时，上述对象需要 **整体序列化为字符串** 赋给 `input_schema`。

---

## 六、出参示例

出参不要求 `location` / `description`，结构更接近标准 JSON Schema：

```json
{
  "type": "object",
  "properties": {
    "code": {
      "type": "integer",
      "description": "业务码"
    },
    "data": {
      "type": "object",
      "description": "业务数据",
      "properties": {
        "id": { "type": "string", "description": "主键" }
      },
      "required": ["id"]
    }
  },
  "required": ["code"]
}
```

流式工具（`intf_type = streaming`）可能跳过 `output_schema` 格式校验。

---

## 七、校验失败与错误码

工具创建 / 更新时，Manager 通过 `ToolManagementService.checkToolInfo` → `JsonSchemaUtils` 校验 schema：

- **v1** 独立工具：创建 / 修改时直接调用  
- **v2** 插件工具：`PluginService.addTool` / `updateTool`（含批量创建）同样调用，与 v1 对齐  

因此绕过前端、用 API 提交缺 `description` 的 schema，**v1 / v2 均应返回 `02401002`**。UI 参数表「描述」列的「输入不允许为空」是前端表单校验，规则一致、链路不同。

| 对外错误码 | 含义 | 常见原因 |
|------------|------|----------|
| `openjiuwen.02401002` | 入参格式错误（`TOOL_INPUT_SCHEMA_INVALID`） | 缺 `description` / `location` / `type` / `properties` / `items`、类型非法、嵌套超限、嵌套数组、带 `additionalProperties`、JSON 非法、`input_schema` 解析失败等 |
| `openjiuwen.02401003` | 出参格式错误（`TOOL_OUTPUT_SCHEMA_INVALID`） | 出参 JSON / 类型 / 结构不合法（如根 `properties` 为空） |

**对外文案会带上具体原因**（i18n 占位符 `{0}` + 响应 `details`），例如：

- `入参格式错误：The parameter [age] is missing required field [description].`
- `The parameter [age] is missing required field [location] (must be one of: Body, Headers, Query, Path).`
- `The parameter [age] is missing required field [type].`
- `The parameter [matrix] cannot be nested array.`
- `The schema root is missing required field [properties].` / `The schema root field [properties] cannot be empty.`
- `The schema is not valid JSON.`

排查时优先看错误消息里的参数名 `[...]` 与标明的缺失字段。
---

## 八、与「标准 JSON Schema」的差异速查

| 点 | 本平台 |
|----|--------|
| 根形态 | 通常为 `object` + `properties` |
| 入参属性 | 强制 `description` + `location` |
| 私有扩展 | `name_cn`、`validated`、`validate_type`、`validate_rule`、`env_var_ref` 等 |
| Map 型对象 | 不支持 `additionalProperties` |
| 嵌套数组 | 不支持 |
| 枚举 / 范围 | 不走标准 `enum` / `minimum`；字符串侧多用 `validate_type` + `validate_rule` |
| 传输形态 | 字段值为 JSON **字符串**，不是请求体里的嵌套对象 |

---

## 九、自查 Checklist

**请求体**

- [ ] 选对接口：独立工具用 **v1**，插件下工具用 **v2** 且带 `plugin_id`
- [ ] `tool_display_name` / `tool_desc`（及 v2 所需中文名）符合长度与字符约束
- [ ] `request_info.url` + `method` 合法；内网 URL 可能被拦截

**Schema**

- [ ] `input_schema` / `output_schema` 是合法 JSON，且已按接口要求转成字符串
- [ ] 根节点有 `type`；`object` 有非空 `properties`
- [ ] 每个入参属性有非空 `description`，且 `location` 为 `Body` / `Headers` / `Query` / `Path` 之一
- [ ] `array` 带 `items`，且 `items` 不是 `array`
- [ ] 未使用 `additionalProperties`
- [ ] 嵌套深度与每层属性个数未超配置上限
- [ ] 复杂结构 / `file/*` 放在 `Body`；Query / Header / Path 仅用标量（与 UI 一致）
- [ ] 若报 `02401002` / `02401003`，先看错误文案 / `details` 中的参数名 `[...]` 与缺失字段

---

## 十、实现参考（代码位置）

| 模块 | 路径 |
|------|------|
| 后端校验 | `backend/studio-manager-service/.../utils/JsonSchemaUtils.java` |
| 类型枚举 | `.../enums/JsonSchemaType.java`、`ToolParamLocation.java` |
| v1 创建/修改工具校验 | `.../service/ToolManagementService.java` → `checkToolInfo` / `buildToolEntity` |
| v2 插件下创建/修改工具校验 | `.../service/plugin/PluginService.java` → `validatePluginToolSchemas`（`addTool` / `updateTool`） |
| 请求体 DTO | `.../dto/CreateToolReq.java`、`CreatePluginToolReq.java`、`RequestInfo.java` |
| 前端拼装 / 解析 | `frontend/.../app-plugin/utils.ts`（`view2Schema` / `schema2View`） |
| 创建工具 UI（类型 / 校验下拉） | `frontend/.../app-plugin/create-tool/create-tool.ts` |

文档约定与上述实现保持一致；若行为变更，请同步更新本文。
