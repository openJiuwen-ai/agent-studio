# 自定义插件开发指南

> 本指南面向插件开发者，详细说明如何从零开发并集成一个自定义插件。

## 目录

- [一、什么是自定义插件](#一什么是自定义插件)
- [二、插件开发](#二插件开发)
- [三、插件集成](#三插件集成)
- [四、已实现插件参考](#四已实现插件参考)
- [附录、自查 Checklist](#附录自查-checklist)

---

## 一、什么是自定义插件

### 1.1 何时需要自定义插件

平台支持两种插件类型：

| 类型 | `call_mode` | 适用场景 | 开发方式 |
|------|-------------|----------|----------|
| **HTTP API 插件** | `api` | 对接外部 HTTP 接口（RESTful API） | 在 UI 上配置 URL/method/headers/鉴权即可，无需写代码 |
| **自定义插件** | `custom` | 非 HTTP 场景：数据库直连、文件处理、画布交互、本地计算等 | 编写 Python 代码，实现自定义执行逻辑 |

**简单判断**：如果你的需求可以通过 HTTP API 对接解决，用 HTTP API 插件，不需要自定义开发。如果需要 Python 代码才能完成（如查询数据库后做数据处理、读取本地文件、复杂计算等），就需要自定义插件。

### 1.2 自定义插件的优势

自定义插件只需 **Python 代码 + JSON 配置**，即可获得平台完整能力：

- **Schema 驱动表单**：参数配置界面由 `input_schema` 自动生成，无需写前端代码
- **工作流 + 智能体通用**：一个插件同时支持工作流画布和智能体调用

### 1.3 生命周期

自定义插件从开发到用户可用，经历三个阶段：

1. **自定义插件开发** → 详见[第二章](#二插件开发)
2. **自定义插件集成** → 详见[第三章](#三插件集成)
3. **自定义插件使用** → 平台自动完成，插件集成后用户可在工作流画布和智能体配置中发现并使用

---

## 二、插件开发

### 2.1 目录结构

一个插件 = 一个目录，放在 `agent-runtime/extensions/components/` 下：

```
agent-runtime/extensions/components/
├── my-plugin/
│   ├── component.json
│   ├── my_plugin.py
│   ├── init.sql
│   └── requirements.txt
└── ...
```

各文件职责：

| 文件 | 文件名 | 作用 | 必须 | 详见 |
|------|--------|------|------|------|
| `component.json` | 固定 | 声明组件类型和入口类 | 是 | [2.2](#22-componentjson) |
| `my_plugin.py` | 自定义 | Python 执行组件，继承 `PluginBase`，实现 `invoke()` | 是 | [2.3](#23-python-组件) |
| `init.sql` | 固定 | 插件定义写入 `t_tool` 表的标准 INSERT 语句 | 是 | [2.4](#24-initsql) |
| `requirements.txt` | 固定 | 声明插件第三方 Python 依赖 | 是 | [2.5](#25-依赖声明) |

> `component.json` 推荐固定命名。runtime 启动时扫描插件目录下的 `.json` 文件加载组件声明，每个插件目录只应有一个 `.json` 文件。

### 2.2 component.json

| 字段 | 类型 | 说明 | 约束 |
|------|------|------|------|
| `type` | string | 组件类型标识 | 使用 `custom.` 前缀 |
| `classInfo.className` | string | Python 类名 | 与 `.py` 文件中的 class 名一致 |
| `classInfo.filePath` | string | Python 文件相对路径 | 相对于 app 根目录，不含 `..`，不能是绝对路径 |

示例：

```json
{
  "type": "custom.my_plugin",
  "classInfo": {
    "className": "MyPlugin",
    "filePath": "extensions/components/my-plugin/my_plugin.py"
  }
}
```

### 2.3 Python 组件

#### PluginBase 基类

`PluginBase` 是所有自定义插件的基类：

| 方法/属性 | 签名 | 说明 |
|-----------|------|------|
| `__init__` | `(self, params: List[Param] = None, **config)` | 框架自动传入参数定义和运行配置 |
| `params` | `@property → List[Param]` | 参数定义列表，可通过 `self.params` 访问参数名、类型、描述等信息 |
| `config` | `@property → dict` | 框架传入的配置信息，按需取用 |
| `invoke` | `async def invoke(self, inputs: dict, **kwargs) -> dict` | **必须实现**。接收输入参数，返回结果 dict |
| `stream` | `async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]` | 可选覆写。默认调用 `invoke()` 并 yield 单条 JSON |

> `invoke` 为抽象方法，必须实现，否则插件无法实例化。

#### 开发示例

```python
from jiuwen.extension.wrapper.plugin_base import PluginBase

class MyPlugin(PluginBase):
    """自定义插件示例"""

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        # inputs 来自前端 Schema 表单，key 与 input_schema 中定义的参数 id 一致
        query = inputs.get("query", "")
        result = self._process(query)
        return {"output": result}

    def _process(self, query):
        # 业务逻辑
        return f"processed: {query}"
```

> 如需流式输出，覆写 `stream()` 方法：
>
> ```python
> async def stream(self, inputs: dict, **kwargs) -> AsyncIterator[str]:
>     query = inputs.get("query", "")
>     yield f"正在处理: {query}...\n"
>     result = self._process(query)
>     yield json.dumps({"output": result}, ensure_ascii=False)
> ```

#### 返回值约定

- 返回的 dict **不含** `errCode` 键 → 框架包装为 `{"data": result, "errCode": 0, "errMessage": ""}`
- 返回的 dict **含** `errCode` 键 → 框架原样透传
- `invoke()` 抛异常 → 框架捕获并包装为 `{"data": None, "errCode": 105001, "errMessage": str(e)}`

> 建议在 `invoke()` 内部处理可预期的业务异常，返回包含错误信息的 dict，而不是直接抛异常。

> **LLM 字符串输入兼容**：当插件参数类型为 `array` 或 `object` 时，LLM 可能将其作为 JSON 字符串传入（而非原生 Python 对象）。建议在 `invoke()` 中增加类型检查：
> ```python
> coordinates = inputs.get("coordinates", [])
> if isinstance(coordinates, str):
>     coordinates = json.loads(coordinates)
> ```

### 2.4 init.sql

#### t_tool 表字段要求

| 字段 | 值 | 说明 |
|------|-----|------|
| `call_mode` | `custom` | 区分 HTTP API 插件（`api`）和自定义插件 |
| `metadata` | `{"component_type": "custom.xxx"}` | JSON 字符串，`component_type` 与 `component.json` 中 `type` 一致 |
| `input_schema` | JSON | 驱动前端表单渲染的参数声明，参数 id 需与 Python `invoke()` 中 `inputs.get()` 的 key 一致 |
| `output_schema` | JSON | 输出参数声明。**所有 `type: "object"` 的参数必须包含 `properties` 字段**，否则 runtime 校验失败 |
| `tool_chinese_name` | 中文名称 | 与 `tool_display_name` 保持一致即可 |

#### SQL 写法

使用标准 `INSERT` 语句，固定主键，无需数据库专有幂等语法（`ON DUPLICATE KEY UPDATE` / `ON CONFLICT DO UPDATE`），兼容 MySQL、PostgreSQL 等所有数据库。`init.sql` 和 `dml.sql` 写法一致，合并时直接复制即可。开发迭代时如需清除旧数据，开发者自行添加 `DELETE` 即可。

> **关键字段说明**：
> - `type`：预置插件用 `'inner'`（跨工作空间可见），用户自行创建的用 `'custom'`（按 workspace 过滤）。
> - `project_id`：`type='inner'` 时填空字符串 `''`；`type='custom'` 时填实际项目 ID。
> - `call_mode`：`'custom'` 表示自定义 Python 组件执行，`'api'` 表示 HTTP API 执行。与 `type` 是不同维度。
> - `icon`：建议提供 `data:image/svg+xml;base64,...` 格式的 SVG 图标。

以下以 DrawBox Demo 为例（完整实现参见 `agent-runtime/extensions/components/draw-box/init.sql`）：

```sql
INSERT INTO t_tool (tool_id, project_id, tool_display_name, tool_chinese_name, tool_desc, icon, type, metadata, call_mode, input_schema, output_schema, visibility, published, customize_node, creator, creator_id, is_share)
VALUES (
    'draw-box',
    '',
    '框选插件',
    '框选插件',
    '画布框选交互插件，支持区域面积计算、重叠检测和框选合并操作',
    'data:image/svg+xml;base64,PHN2ZyB3...',
    'inner',
    '{"component_type": "custom.draw_box"}',
    'custom',
    '{"type":"object","properties":{"operation":{"type":"string","enum":["calculate_area","find_overlaps","merge_boxes"],"description":"框选数据操作类型：calculate_area=计算面积, find_overlaps=检测重叠, merge_boxes=合并框选","default":"calculate_area"},"coordinates":{"type":"array","description":"坐标点列表（calculate_area 操作时为坐标点数组 [{x,y},...]；find_overlaps/merge_boxes 操作时为多组坐标点数组的数组 [[{x,y},...],...]）","items":{"type":"object","properties":{"x":{"type":"number","description":"X坐标"},"y":{"type":"number","description":"Y坐标"}},"required":["x","y"]}}},"required":["coordinates"]}',
    '{"type":"object","properties":{"output":{"type":"object","description":"处理结果","properties":{"operation":{"type":"string","description":"执行的操作类型"},"area":{"type":"number","description":"框选区域面积（calculate_area）"},"center":{"type":"object","description":"中心点坐标（calculate_area）","properties":{"x":{"type":"number","description":"X坐标"},"y":{"type":"number","description":"Y坐标"}}},"bounds":{"type":"object","description":"边界范围（calculate_area）","properties":{"min_x":{"type":"number","description":"最小X坐标"},"max_x":{"type":"number","description":"最大X坐标"},"min_y":{"type":"number","description":"最小Y坐标"},"max_y":{"type":"number","description":"最大Y坐标"}}},"point_count":{"type":"integer","description":"坐标点数量（calculate_area）"},"overlap_pairs":{"type":"array","description":"重叠对列表（find_overlaps）","items":{"type":"object","properties":{"box_a":{"type":"integer","description":"框选组A序号"},"box_b":{"type":"integer","description":"框选组B序号"}}}},"overlap_count":{"type":"integer","description":"重叠对数量（find_overlaps）"},"merged_boxes":{"type":"array","description":"合并后的框选区域列表（merge_boxes）","items":{"type":"object","properties":{"min_x":{"type":"number","description":"最小X坐标"},"max_x":{"type":"number","description":"最大X坐标"},"min_y":{"type":"number","description":"最小Y坐标"},"max_y":{"type":"number","description":"最大Y坐标"}}}},"box_count":{"type":"integer","description":"合并后框选区域数量（merge_boxes）"}}}}}',
    'global',
    1,
    1,
    'system',
    'system',
    0
);
```

> **重要**：`output_schema` 中所有 `type: "object"` 的参数必须包含 `properties` 字段，否则 runtime 校验会报 `The schema field is missing for object parameter` 错误，导致插件注册失败。

### 2.5 依赖声明

插件用到的第三方 Python 依赖需在开发阶段声明（`requirements.txt`），集成阶段根据此声明修改构建配置，详见[第三章](#三插件集成)。

示例（`requirements.txt`）：

```
requests>=2.28.0
pandas>=1.5.0
```

> 开发完成后，请按[附录自查 Checklist](#附录自查-checklist) 逐项检查。

---

## 三、插件集成

### 3.1 方式选择

平台支持以下两种集成方式，可根据实际场景对比选择：

| | 源码集成 | 镜像集成 |
|---|---|---|
| **适用场景** | 通用、稳定、长期维护的插件 | 应用面窄、调测中或临时性需求 |
| **代码位置** | `agent-runtime/extensions/components/` | 客户自建镜像层覆盖追加 |
| **Python 依赖** | 写入仓库 `requirements.txt` 和 `pyproject.toml` | 客户 Dockerfile 中 `pip install` |
| **SQL 注册** | 合并到 `dml.sql`，manager 启动自动执行 | 连库手动执行 `init.sql` |
| **升级路径** | 随版本发布 | 验证成熟后可提交社区合入，升级为源码集成 |
| **详见** | [3.2](#32-源码集成) | [3.3](#33-镜像集成) |

### 3.2 源码集成

1. 将插件目录放入 `agent-runtime/extensions/components/`

2. 将插件 Python 依赖追加到 `agent-runtime/requirements.txt` 和 `agent-runtime/pyproject.toml`

3. 将 `init.sql` 内容合并到 `backend/studio-manager-service/src/main/resources/sql/dml.sql`

4. 本地启动 manager 和 runtime 验证：manager 启动时自动执行 `dml.sql` 注册插件，runtime 启动时扫描 `extensions/components/` 加载插件代码。启动后在平台 UI 中创建智能体、添加插件、对话测试。验证通过后代码合入进行出包

### 3.3 镜像集成

1. 编写 `Dockerfile.runtime.custom`，将插件代码叠加到基础镜像并安装依赖

   ```dockerfile
   FROM studio-runtime:<version>
   # 仅复制你的插件目录，不影响基础镜像中已有的插件
   COPY extensions/components/my-plugin/ /opt/cloud/agent-runtime/app/extensions/components/my-plugin/
   RUN pip install -r /opt/cloud/agent-runtime/app/extensions/components/my-plugin/requirements.txt
   ```

   > 如有多个插件，可逐条 COPY 各插件目录，或 `COPY extensions/components/ /opt/cloud/agent-runtime/app/extensions/components/` 但注意这会覆盖该目录下已有的全部插件。

2. 构建自定义 runtime 镜像（在 extensions/ 目录的父目录执行，确保构建上下文含 extensions/）

   ```bash
   docker build -t studio-runtime-custom:<version> -f Dockerfile.runtime.custom .
   ```

3. 连接数据库执行 `init.sql`（在插件目录的父目录执行，路径指向本地 init.sql 文件）

   ```bash
   mysql -h <db_host> -u <user> -p <db> < extensions/components/my-plugin/init.sql
   ```

4. 修改 studio-runtime 服务镜像版本为 `studio-runtime-custom:<version>`，重启服务

5. 在平台 UI 中创建智能体、添加插件、对话测试

验证成熟后可提交社区合入下一版本，升级为源码集成。

> 集成完成后，请按[附录自查 Checklist](#附录自查-checklist) 逐项检查。

---

## 四、已实现插件参考

以下插件已按本指南完成开发与集成，可作为参考：

| 插件 | component_type | 说明 | 实现文档 |
|------|----------------|------|----------|
| DrawBox | `custom.draw_box` | 画布框选交互插件，支持区域面积计算、重叠检测和框选合并操作。Schema 驱动表单 + 非 HTTP 执行 + 端到端完整链路验证 | `agent-runtime/extensions/components/draw-box/` |

> 新增插件实现后，在此表追加一行并链接到对应的实现文档。

---

## 附录、自查 Checklist

### A.1 开发自查

插件开发完成后，提交前须逐项自查：

**文件完整性**：
- [ ] `component.json` 存在且 JSON 格式合法
- [ ] `.py` 文件存在且语法无误
- [ ] `init.sql` 存在且使用标准 `INSERT` 语句（固定主键，无需数据库专有幂等语法）

**命名与约束**：
- [ ] `component.json` 中 `type` 使用 `custom.` 前缀
- [ ] `classInfo.className` 与 `.py` 文件中的类名一致
- [ ] `classInfo.filePath` 不含 `..`，不是绝对路径

**接口契约**：
- [ ] Python 类继承 `PluginBase`
- [ ] 实现 `async def invoke(self, inputs: dict, **kwargs) -> dict`
- [ ] 如需流式输出，覆写 `async def stream(self, inputs: dict, **kwargs)` 返回 `AsyncIterator[str]`
- [ ] `invoke()` 返回值为 `dict` 类型
- [ ] `invoke()` 中对 `array`/`object` 类型参数增加 `isinstance(str)` + `json.loads()` 兼容处理

**数据库注册**：
- [ ] `t_tool` 表字段完整：`call_mode` 填 `custom`，`metadata` 列写入 `{"component_type": "custom.xxx"}`
- [ ] `input_schema` 中定义的参数与 Python `invoke()` 方法中 `inputs.get()` 的 key 一致
- [ ] `output_schema` 中所有 `type: "object"` 的参数包含 `properties` 字段

### A.2 集成自查

集成完成后，提交前须逐项自查：

- [ ] 已确定集成方式（源码集成 / 镜像集成）
- [ ] 服务启动后插件在平台 UI 中可见、可添加到智能体、对话调用正常
- [ ] **若选源码集成**：插件代码已放入 `agent-runtime/extensions/components/`，Python 依赖已追加到仓库 `requirements.txt` 和 `pyproject.toml`，`init.sql` 内容已合并到 `dml.sql`
- [ ] **若选镜像集成**：已准备 `Dockerfile.runtime.custom`（含 `COPY` + `pip install`）并完成连库执行 `init.sql`
