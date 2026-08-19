import { test, expect } from '@playwright/test';
import { I18N, ROUTES } from './fixtures/selectors';
import {
  mockPreview,
  mockImport,
  buildPreviewRsp,
  buildImportRsp,
  buildProviderModelsJsonl,
  writeTempJsonl,
  conflictStrategyOf,
} from './fixtures/api-mocks';
import { ImportModalPage } from './pages/import-modal.page';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-05 冲突策略 COVER 警告 — 对应测试方案 UI-07 / API-11。
 *
 * 验证点：
 *   - 预检含冲突（conflict_count>0）→ 切 COVER → 显示警告文案
 *   - 导入请求 query: conflict_strategy=COVER（非默认 SKIP）
 *   - 结果正常渲染
 *
 * 前置：列表页可加载。预检/导入端点 mock。
 */
test.describe('L3-05 冲突策略 COVER', () => {
  test('预检有冲突→切 COVER→警告显示→导入 strategy=COVER', async ({ page }) => {
    const modal = new ImportModalPage(page);

    await mockPreview(page, buildPreviewRsp({ total: 2, conflicts: 1 }));
    await mockImport(page, buildImportRsp({ succeed: 1, failed: 0 }), (route) => {
      expect(conflictStrategyOf(route)).toBe('COVER');
    });

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.listPage);
    await page.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });

    const jsonl = writeTempJsonl(buildProviderModelsJsonl(), 'l3-05');
    await modal.uploadFile(jsonl);
    await modal.waitForPreview();

    // 预检冲突汇总可见
    await expect(modal.dialog()).toContainText(I18N.previewConflict);

    // 切 COVER → 警告出现
    await modal.selectStrategy('COVER');
    await expect(modal.coverWarning()).toBeVisible();

    await modal.confirm();
    await modal.waitForResult();
    await expect(modal.resultTag('succeed')).toBeVisible();
  });
});
