import { test, expect } from '@playwright/test';
import { I18N, ROUTES } from './fixtures/selectors';
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
 * L3-03 供应商+模型导入（列表页，不传 targetProviderId）— 对应测试方案 UI-03 / API-15。
 *
 * 验证点：
 *   - 列表页「导入模型」打开弹窗，不传 targetProviderId
 *   - 预检请求 query 不含 target_provider_id（走供应商+模型 upsert 路径）
 *   - 导入请求 query: conflict_strategy=SKIP（默认），无 target_provider_id
 *   - 预检表/结果表正常渲染
 *
 * 前置：列表页可加载。预检/导入端点 mock。
 */
test.describe('L3-03 供应商+模型导入', () => {
  test('列表页导入，不传 target_provider_id，默认 SKIP', async ({ page }) => {
    const modal = new ImportModalPage(page);

    await mockPreview(page, buildPreviewRsp({ total: 2, conflicts: 0 }), (route) => {
      expect(targetProviderIdOf(route)).toBeNull();
    });
    await mockImport(page, buildImportRsp({ succeed: 2, failed: 0 }), (route) => {
      expect(targetProviderIdOf(route)).toBeNull();
      expect(conflictStrategyOf(route)).toBe('SKIP');
    });

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.listPage);
    await page.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });

    const jsonl = writeTempJsonl(buildProviderModelsJsonl(), 'l3-03');
    await modal.uploadFile(jsonl);
    await modal.waitForPreview();

    // 默认 SKIP，确认可点
    await expect(modal.confirmButton()).toBeEnabled();
    await modal.confirm();
    await modal.waitForResult();
    await expect(modal.resultTag('succeed')).toBeVisible();
  });
});
