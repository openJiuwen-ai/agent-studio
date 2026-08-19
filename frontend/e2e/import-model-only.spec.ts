import { test, expect } from '@playwright/test';
import { ROUTES, I18N } from './fixtures/selectors';
import {
  mockPreview,
  mockImport,
  buildPreviewRsp,
  buildImportRsp,
  buildProviderModelsJsonl,
  writeTempJsonl,
  targetProviderIdOf,
  conflictStrategyOf,
} from './fixtures/api-mocks';
import { ImportModalPage } from './pages/import-modal.page';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-04 只导模型导入（详情页，带 targetProviderId）— 对应测试方案 UI-05 / API-06~08。
 *
 * 验证点：
 *   - 详情页「导入模型」打开弹窗，携带 nzData:{ targetProviderId: provider_id }
 *   - 预检请求 query 含 target_provider_id == provider_id
 *   - 导入请求 query: target_provider_id == provider_id, conflict_strategy=SKIP
 *
 * 前置：E2E_PROVIDER_ID 指向已存在供应商（详情页可加载）。预检/导入端点 mock。
 *      TODO: 确认详情页路由形态（此处用 ROUTES.detailPage）。
 */
test.describe('L3-04 只导模型导入', () => {
  test('详情页导入，携带 target_provider_id', async ({ page }) => {
    const providerId = process.env.E2E_PROVIDER_ID;
    test.skip(!providerId, '需 E2E_PROVIDER_ID 指向已存在供应商');

    const modal = new ImportModalPage(page);

    await mockPreview(page, buildPreviewRsp({ total: 1, conflicts: 0 }), (route) => {
      expect(targetProviderIdOf(route)).toBe(providerId);
    });
    await mockImport(page, buildImportRsp({ succeed: 1, failed: 0 }), (route) => {
      expect(targetProviderIdOf(route)).toBe(providerId);
      expect(conflictStrategyOf(route)).toBe('SKIP');
    });

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.detailPage(providerId!));
    // 详情页「导入模型」按钮（openImportModal 带 targetProviderId）
    await page.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });

    const jsonl = writeTempJsonl(buildProviderModelsJsonl(), 'l3-04');
    await modal.uploadFile(jsonl);
    await modal.waitForPreview();

    await modal.confirm();
    await modal.waitForResult();
    await expect(modal.resultTag('succeed')).toBeVisible();
  });
});
