# 模型导入导出 — 端到端自动化（L3 / Playwright）

对应测试方案文档：`设计文档/模型导入导出与环境变量配置-端到端测试方案.md` 第 6 章。

覆盖 7 个关键 UI 流程回归用例（共 8 个 test），所有用例的 `file:line` 验证点与验证逻辑见测试方案 §4/§8。

**本地实跑验证结果（2026-08-12）**：
- 7 passed（L3-01/02 导出 × 2、L3-03/04/05 导入 × 3、L3-06 文件类型 × 2）
- 1 skipped（L3-07 跨环境，需第二个环境）
- 0 failed

## 前置

### 1. 安装 Playwright（首次）

```bash
cd agent-studio/frontend
npm i -D @playwright/test --legacy-peer-deps
# 国内网络走 npmmirror 镜像下载浏览器
$env:PLAYWRIGHT_DOWNLOAD_HOST="https://cdn.npmmirror.com/binaries/playwright"; npx playwright install chromium
```

### 2. 启动被测系统

按 `部署指导/win-studio/` 文档启动：
1. SSH 隧道（MySQL/Redis/OpenSearch 转发到 `113.44.224.121:2022`，用 `ssh_tunnel_guard.sh` 守护常驻）
2. `studio-manager`（Java 17，监听 `127.0.0.1:31111`）
3. `ng serve`（Angular 20 dev server，默认 `http://localhost:4200/openjiuwen`，**hash 路由**）

> `agent-runtime` / `studio-builder` 在 L3 用例中不需要（所有导入/导出/预检 API 均在前端 `page.route` 层 mock 掉）。

### 3. 测试数据（按测试方案 §2.2 预置）

真实后端需存在至少一个非 `cdi-` 前缀的供应商（列表页 hover 导出按钮在 `id.startsWith('cdi-')` 时 disabled，见 `model-management.component.html:125-130`）：
- 供应商 P1（源）+ P2（目标，跨环境用例）
- 模型 M1（字面量 apiUrl）/ M2（占位符 apiUrl）

**无测试数据时可跑**：L3-03、L3-05、L3-06（不依赖具体卡片数据，只需要列表页按钮可点，`subscribeBtnStatus` 由 `common.service.getSubscribeStatus()` 硬编码返回 `true`）。

### 4. 鉴权

**agent-studio 前端无登录页/守卫/鉴权头**（`HttpService.buildHeaders` 仅设置 X-Language，鉴权由部署态网关注入）。本套件不做登录，`storageState` 不使用，原 `auth.setup.ts` 已删除。

### 5. Workspace 必选（关键）

页面刷新后即使 UI 上显示"个人空间"文字，若未**主动点选一次** workspace 下拉，发往后端的 `workspace_id` 会是空字符串，导致 `custom-models/provider`、`custom-models/search` 等接口返回 400/空数组，列表/详情页显示"暂无数据"。每个 spec 开头均调用 `selectPersonalSpace(page, { navigateFirst: true })` 显式选中"个人空间"（fixtures/workspace.ts）。

### 6. download 事件时序

导出用例通过 `URL.createObjectURL(blob) + a.click()` 触发下载（见 `model-management.component.ts:249` / `model-management-detail.component.ts:667`），`a.click()` 是**同步**派发 download 事件的，必须**先** `const p = page.waitForEvent('download')` 挂 listener、**再** `.click()`、**最后** `await p`；顺序反了会错过事件导致 timeout。

## 环境变量

| 变量 | 用途 | 默认 |
|:---|:---|:---|
| `E2E_BASE_URL` | 源环境前端地址（**必须带尾 `/`**） | `http://localhost:4200/openjiuwen/` |
| `E2E_PROVIDER_ID` | 源环境已存在供应商 id（L3-01/02/04） | —（未设则 skip） |
| `E2E_BASE_URL_B` | 目标环境前端地址（L3-07，带尾 `/`） | —（未设则 skip） |
| `E2E_PROVIDER_ID_A` | 源环境供应商（L3-07 导出） | — |
| `E2E_PROVIDER_ID_B` | 目标环境供应商（L3-07 导入 targetProviderId） | — |

## 重要路径事实

- **base href**：dev 环境 `/openjiuwen/`（`index.html` `<base href>` 由 `.staging/index.html` 在 patch-proxy 阶段生成；POC_BASE_HREF 在 `app.component.ts:229`）。
- **路由策略**：**HashLocationStrategy**，URL 形如 `http://localhost:4200/openjiuwen/#/home/model/management`。所有 spec 用相对路径 `goto(ROUTES.xxx)`，`baseURL` 带尾 `/` 时 Playwright 会正确拼接。错误使用绝对 `/path` 会被踢回 `#/home/overview`。
- **模型管理列表页**：`#/home/model/management`
- **模型管理详情页**：`#/home/model/management-detail?provider_id=xxx`

## 运行

```bash
cd agent-studio/frontend

# 全部（无 E2E_PROVIDER_ID 时自动 skip 4 个数据依赖用例）
npx playwright test

# 单个用例
npx playwright test file-type-guard       # L3-06 文件类型校验（最快，不依赖数据）
npx playwright test import-conflict-cover # L3-05 COVER 警告
npx playwright test import-provider       # L3-03 列表导入 SKIP

# 带 UI 调试
npx playwright test --ui

# 查看报告（失败自动录屏/截图/trace）
npx playwright show-report e2e/.report
```

## 用例清单

| 文件 | 用例 | 测试方案编号 | 验证要点 | 数据依赖 |
|:---|:---|:---|:---|:---|
| `export-provider.spec.ts` | L3-01 | UI-01 / API-01 | 列表 hover 导出 → `provider-models.jsonl`，行含签名+provider_metadata | 需要 provider 卡片 |
| `export-model-only.spec.ts` | L3-02 | UI-04 / API-02 | 详情 ellipsis 导出 → `models.jsonl`，行无 provider_metadata（include_provider=false） | 需要 provider_id |
| `import-provider.spec.ts` | L3-03 | UI-03 / API-15 | 列表导入，无 target_provider_id，默认 SKIP | 无 |
| `import-model-only.spec.ts` | L3-04 | UI-05 / API-06~08 | 详情导入，含 target_provider_id == provider_id | 需要 provider_id |
| `import-conflict-cover.spec.ts` | L3-05 | UI-07 / API-11 | 预检有冲突 → 切 COVER → 警告"覆盖将删除目标环境同名旧记录"显示 → strategy=COVER | 无 |
| `file-type-guard.spec.ts` | L3-06 test 1 | UI-06 | 上传 .txt 被拒，toast "仅支持 .jsonl 文件"，不触发预检 | 无 |
| `file-type-guard.spec.ts` | L3-06 test 2 | UI-06 | 上传 .jsonl 触发预检（preview 请求计数=1） | 无 |
| `cross-env-linkage.spec.ts` | L3-07 | E2E-01 | 环境 A 导出 → 环境 B 导入（targetProviderId）→ id 命中 | 需要 envB + 两 provider |

## Hermetic 策略

- **Mock 端点**（验证点所在，响应形态已与后端 DTO 对齐）：
  - `POST .../model-services/export`（octet-stream）
  - `POST .../model-services/import/preview`（JSON）
  - `POST .../model-services/import`（JSON）
- **真实后端**：列表/详情页面初始加载（`workspace/init`、`system/settings`、`apps`、`custom-models/provider`、`custom-models/search`）走真实后端，依赖 studio-manager 起来。
- `page.route` 谓词用 `URL.pathname.endsWith()` 精确匹配，避免 `/import` 与 `/import/preview` 互串。
- 下载读取：前端 `a.click()` 触发的下载由 `waitForEvent('download')` 捕获并 `saveAs` 到临时文件。
- 预检/导入 mock 响应通过 `RouteAsserter` 回调对 query 参数（`target_provider_id` / `conflict_strategy`）做断言。

## 已知限制（测试方案 §7）

- **ir 策略占位符**（LIM-01）：`model_bridge.py` 三处 custom_headers 不含 X-Environment-Id，本套件不覆盖 ir 路径，仅测 obs。
- **工作流联动**（LIM-05）：L3-07 工作流按 id 命中降级为「导出文件含模型 id」断言 + TODO API 校验。
- **跨环境**（L3-07）：需要两个独立部署的 frontend + manager，单环境下自动 skip。

## 目录结构

```
frontend/
├── playwright.config.ts
└── e2e/
    ├── README.md（本文件）
    ├── tsconfig.json
    ├── .gitignore
    ├── fixtures/
    │   ├── selectors.ts      # i18n 文案 / ROUTES / URL_PATTERNS
    │   ├── api-mocks.ts      # 响应类型、mock 构造器、RouteCounter、writeTempJsonl
    │   └── workspace.ts      # selectPersonalSpace helper（必须先选 workspace 否则接口返回空）
    ├── pages/
    │   └── import-modal.page.ts   # meta-model-import-modal 页面对象
    ├── export-provider.spec.ts    # L3-01
    ├── export-model-only.spec.ts  # L3-02
    ├── import-provider.spec.ts    # L3-03
    ├── import-model-only.spec.ts  # L3-04
    ├── import-conflict-cover.spec.ts  # L3-05
    ├── file-type-guard.spec.ts    # L3-06
    └── cross-env-linkage.spec.ts  # L3-07
```
