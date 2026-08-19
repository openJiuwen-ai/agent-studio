import { Page, Route } from '@playwright/test';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { URL_PATTERNS } from './selectors';

/* ----------------------------- 响应类型（与后端 DTO 对齐，snake_case） ----------------------------- */

export interface PreviewItem {
  id: string | null;
  service_name: string | null;
  provider_id: string | null;
  conflict: boolean;
  signature_valid: boolean;
  api_url_valid: boolean;
  env_var_valid: boolean;
  detail: string | null;
}

export interface PreviewRsp {
  total_count: number;
  conflict_count: number;
  items: PreviewItem[];
}

export interface ImportResultItem {
  id: string | null;
  name: string;
  type: string;
  status: string; // 'SUCCESS' | 'FAILED'
  detail: string;
}

export interface ImportRsp {
  succeed_len: number;
  failed_len: number;
  count: number;
  succeed_ids: string[];
  failed_ids: string[];
  import_list: ImportResultItem[];
}

/** 导出行（ModelExportLine，@JsonInclude(NON_NULL)）。 */
export interface ExportLine {
  import_type: string;
  payload: {
    provider_metadata?: unknown; // 供应商+模型模式才有；只导模型模式为 null（被 NON_NULL 省略）
    models: Array<{ id: string; service_name: string; provider_id: string; api_url: string }>;
  };
  signature: string | null;
}

/* ----------------------------- Mock 响应构造器 ----------------------------- */

export function buildPreviewRsp(opts: {
  total?: number;
  conflicts?: number;
  signatureValid?: boolean;
  envVarValid?: boolean;
  apiUrlValid?: boolean;
}): PreviewRsp {
  const total = opts.total ?? 2;
  const conflicts = opts.conflicts ?? 0;
  const items: PreviewItem[] = Array.from({ length: total }, (_, i) => ({
    id: `mdl-${1000 + i}`,
    service_name: `model-${i}`,
    provider_id: 'prov-target',
    conflict: i < conflicts,
    signature_valid: opts.signatureValid ?? true,
    api_url_valid: opts.apiUrlValid ?? true,
    env_var_valid: opts.envVarValid ?? true,
    detail: i < conflicts ? 'conflict' : null,
  }));
  return { total_count: total, conflict_count: conflicts, items };
}

export function buildImportRsp(opts: { succeed?: number; failed?: number }): ImportRsp {
  const succeed = opts.succeed ?? 2;
  const failed = opts.failed ?? 0;
  const importList: ImportResultItem[] = [
    ...Array.from({ length: succeed }, (_, i) => ({
      id: `mdl-${1000 + i}`,
      name: `model-${i}`,
      type: 'model_service',
      status: 'SUCCESS',
      detail: '',
    })),
    ...Array.from({ length: failed }, (_, i) => ({
      id: `mdl-fail-${i}`,
      name: `model-fail-${i}`,
      type: 'model_service',
      status: 'FAILED',
      detail: 'conflict skipped',
    })),
  ];
  return {
    succeed_len: succeed,
    failed_len: failed,
    count: succeed + failed,
    succeed_ids: Array.from({ length: succeed }, (_, i) => `mdl-${1000 + i}`),
    failed_ids: Array.from({ length: failed }, (_, i) => `mdl-fail-${i}`),
    import_list: importList,
  };
}

/* ----------------------------- 导出 JSONL 样本 ----------------------------- */

/** 供应商+模型导出文件：行含 provider_metadata。 */
export function buildProviderModelsJsonl(): string {
  const line: ExportLine = {
    import_type: 'model_service',
    payload: {
      provider_metadata: {
        provider_id: 'prov-src',
        provider_name: 'src-provider',
        // authInfo 经后端 maskProviderAuth 置空格（此处 mock 仅占位）
        auth_info: ' ',
      },
      models: [
        {
          id: 'mdl-1001',
          service_name: 'model-1',
          provider_id: 'prov-src',
          api_url: 'https://host-a/v1/chat',
        },
      ],
    },
    signature: 'mock-hmac-signature',
  };
  return JSON.stringify(line);
}

/** 只导模型导出文件：行内无 provider_metadata（NON_NULL 省略）。 */
export function buildModelsOnlyJsonl(): string {
  const line: ExportLine = {
    import_type: 'model_service',
    payload: {
      models: [
        {
          id: 'mdl-2002',
          service_name: 'model-2',
          provider_id: 'prov-src',
          api_url: '${_env.plugin_url_params.HOST}/v1/chat',
        },
      ],
    },
    signature: 'mock-hmac-signature',
  };
  // 删除 provider_metadata 键以模拟 NON_NULL 行为
  delete (line.payload as Record<string, unknown>).provider_metadata;
  return JSON.stringify(line);
}

/** 生成一个临时 .jsonl 文件供 nz-upload setInputFiles 使用。返回绝对路径。 */
export function writeTempJsonl(content: string, suffix = 'upload'): string {
  const tmp = path.join(os.tmpdir(), `e2e-${suffix}-${process.pid}-${content.length}.jsonl`);
  fs.writeFileSync(tmp, content, 'utf-8');
  return tmp;
}

/** 读取 Playwright 下载内容为文本。 */
export async function readDownloadText(download: {
  suggestedFilename: () => string;
  saveAs: (p: string) => Promise<void>;
}): Promise<string> {
  const tmp = path.join(os.tmpdir(), `e2e-dl-${process.pid}-${download.suggestedFilename()}`);
  await download.saveAs(tmp);
  return fs.readFileSync(tmp, 'utf-8');
}

/* ----------------------------- page.route Mock 处理器 ----------------------------- */

/** 谓词断言：拿到 Route 可读 url/postBody，断言后由本函数统一 fulfill。 */
type RouteAsserter = (route: Route) => void;

function urlOf(route: Route): URL {
  return new URL(route.request().url());
}

/** Mock 导出端点（octet-stream）。 */
export async function mockExport(
  page: Page,
  body: string,
  filename: string,
  assert?: RouteAsserter,
): Promise<void> {
  await page.route(URL_PATTERNS.export, async (route) => {
    assert?.(route);
    await route.fulfill({
      status: 200,
      contentType: 'application/octet-stream',
      headers: {
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
      body,
    });
  });
}

/** Mock 导入预检端点（JSON）。 */
export async function mockPreview(page: Page, rsp: PreviewRsp, assert?: RouteAsserter): Promise<void> {
  await page.route(URL_PATTERNS.preview, async (route) => {
    assert?.(route);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(rsp),
    });
  });
}

/** Mock 导入端点（JSON）。 */
export async function mockImport(page: Page, rsp: ImportRsp, assert?: RouteAsserter): Promise<void> {
  await page.route(URL_PATTERNS.import, async (route) => {
    assert?.(route);
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(rsp),
    });
  });
}

/** 计数器：记录某端点被触发的次数（file-type-guard 用：断言非法文件不触发预检）。 */
export class RouteCounter {
  count = 0;
  async install(page: Page, predicate: (u: URL) => boolean): Promise<void> {
    await page.route(predicate, async (route) => {
      this.count += 1;
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
  }
}

/** 从 Route 的 query 中读取 target_provider_id（page.route 侧断言用）。 */
export function targetProviderIdOf(route: Route): string | null {
  return urlOf(route).searchParams.get('target_provider_id');
}

/** 从 Route 的 query 中读取 conflict_strategy。 */
export function conflictStrategyOf(route: Route): string | null {
  return urlOf(route).searchParams.get('conflict_strategy');
}
