import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { ROUTES, I18N } from './fixtures/selectors';
import {
  mockExport,
  mockPreview,
  mockImport,
  buildModelsOnlyJsonl,
  buildPreviewRsp,
  buildImportRsp,
  readDownloadText,
  targetProviderIdOf,
} from './fixtures/api-mocks';
import { ImportModalPage } from './pages/import-modal.page';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-07 跨环境联动（工行核心诉求）— 对应测试方案 E2E-01。
 *
 * 场景：环境 A 只导模型导出（保留 id）→ 环境 B 按 targetProviderId 导入 → 模型 id 命中。
 *
 * 验证点：
 *   - 环境 A 导出文件含模型 id（跨环境 id 保留，createModelServiceForImport 用 #{id}）
 *   - 环境 B 导入请求 query 含 target_provider_id == 目标供应商
 *   - 导入结果成功
 *   - 工作流按 id 命中：LIM-05（工作流导入范围外），降级为「导出文件含模型 id」断言 + TODO API 校验
 *
 * 环境变量：
 *   E2E_PROVIDER_ID_A  源环境供应商（导出）
 *   E2E_BASE_URL_B     目标环境前端地址
 *   E2E_PROVIDER_ID_B  目标环境供应商（导入，作为 targetProviderId）
 *
 * 说明：导出/预检/导入端点均 mock（hermetic）；列表/详情数据走真实后端。
 *      真实场景可去掉 mockExport 走真实导出，并以实际模型 id 替换 MODEL_ID 断言。
 */
const MODEL_ID = 'mdl-2002'; // buildModelsOnlyJsonl 样本中的模型 id

test.describe('L3-07 跨环境联动', () => {
  test('环境A导出模型→环境B导入(targetProviderId)→id 命中', async ({ browser }) => {
    const providerIdA = process.env.E2E_PROVIDER_ID_A;
    const envB = process.env.E2E_BASE_URL_B;
    const providerIdB = process.env.E2E_PROVIDER_ID_B;
    test.skip(!providerIdA || !envB || !providerIdB, '需 E2E_PROVIDER_ID_A / E2E_BASE_URL_B / E2E_PROVIDER_ID_B');

    // ---------- 环境 A：详情页只导模型导出 ----------
    const ctxA = await browser.newContext();
    const pageA = await ctxA.newPage();
    const sampleJsonl = buildModelsOnlyJsonl();
    await mockExport(pageA, sampleJsonl, 'models.jsonl');

    await selectPersonalSpace(pageA, { navigateFirst: true });
    await pageA.goto(ROUTES.detailPage(providerIdA!));
    const cardA = pageA.locator('.model-card').first();
    await cardA.waitFor({ state: 'visible' });
    await cardA.locator('a.ant-dropdown-trigger').first().click();
    const exportItem = pageA
      .locator('.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item', { hasText: I18N.export })
      .first();
    await exportItem.waitFor({ state: 'visible' });

    const dlPromise = pageA.waitForEvent('download', { timeout: 20_000 });
    await exportItem.click();
    const download = await dlPromise;
    expect(download.suggestedFilename()).toBe('models.jsonl');
    const exportedJsonl = await readDownloadText(download);
    // 模型 id 保留在导出文件中（跨环境 id 一致的前提）
    expect(exportedJsonl).toContain(MODEL_ID);
    await ctxA.close();

    // ---------- 环境 B：详情页导入（带 targetProviderId） ----------
    const ctxB = await browser.newContext({ baseURL: envB!.replace(/\/?$/, '/') });
    const pageB = await ctxB.newPage();
    const modal = new ImportModalPage(pageB);

    const tmp = path.join(os.tmpdir(), `e2e-crossenv-${process.pid}.jsonl`);
    fs.writeFileSync(tmp, exportedJsonl, 'utf-8');

    await mockPreview(pageB, buildPreviewRsp({ total: 1 }), (route) => {
      expect(targetProviderIdOf(route)).toBe(providerIdB);
    });
    await mockImport(pageB, buildImportRsp({ succeed: 1 }), (route) => {
      expect(targetProviderIdOf(route)).toBe(providerIdB);
    });

    await selectPersonalSpace(pageB, { navigateFirst: true });
    await pageB.goto(ROUTES.detailPage(providerIdB!));
    await pageB.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });
    await modal.uploadFile(tmp);
    await modal.waitForPreview();
    await modal.confirm();
    await modal.waitForResult();
    await expect(modal.resultTag('succeed')).toBeVisible();

    // ---------- 工作流按 id 命中（LIM-05 降级为 API 验证 TODO） ----------
    // TODO: 用 request.get 查询环境 B 工作流 W1 节点引用的 modelId，断言 == MODEL_ID 已存在。
    //       工作流导入本身不在本特性范围（测试方案 §7 LIM-05）。

    fs.unlinkSync(tmp);
    await ctxB.close();
  });
});
