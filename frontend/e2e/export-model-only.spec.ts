import { test, expect } from '@playwright/test';
import { ROUTES, I18N } from './fixtures/selectors';
import { mockExport, buildModelsOnlyJsonl, readDownloadText } from './fixtures/api-mocks';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-02 只导模型导出（详情页 ellipsis 菜单）— 对应测试方案 UI-04 / API-02。
 *
 * 验证点：
 *   - 先选 workspace「个人空间」
 *   - 详情页模型卡片右下角「⋯」ellipsis → 下拉菜单 → 「导出」
 *   - 导出请求 body: { model_ids:[id], include_provider:false }
 *   - 下载文件名 models.jsonl（model-management-detail.component.ts:667）
 *   - 行含 signature；payload 无 provider_metadata（@JsonInclude(NON_NULL) 省略）
 *
 * 前置：E2E_PROVIDER_ID 指向已存在供应商（详情页可加载模型）。
 *      导出端点 mock；详情页数据走真实后端。
 */
test.describe('L3-02 只导模型导出', () => {
  test('详情页 ellipsis→导出→下载 models.jsonl，行无 provider 元数据', async ({ page }) => {
    const providerId = process.env.E2E_PROVIDER_ID;
    test.skip(!providerId, '需 E2E_PROVIDER_ID 指向已存在供应商');

    const jsonl = buildModelsOnlyJsonl();
    await mockExport(page, jsonl, 'models.jsonl', (route) => {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      expect(body.include_provider).toBe(false);
      expect(Array.isArray(body.model_ids)).toBe(true);
      expect((body.model_ids as unknown[]).length).toBeGreaterThan(0);
    });

    // 关键：先选 workspace「个人空间」
    await selectPersonalSpace(page, { navigateFirst: true });

    await page.goto(ROUTES.detailPage(providerId!));

    // 等待第一个模型卡片渲染
    const card = page.locator('.model-card').first();
    await card.waitFor({ state: 'visible' });

    // 点击右下角 ellipsis 下拉触发器（a.ant-dropdown-trigger 内含 nztype="ellipsis" icon）
    const ellipsis = card.locator('a.ant-dropdown-trigger').first();
    await ellipsis.waitFor({ state: 'visible' });
    await ellipsis.click();

    // 下拉菜单：.ant-dropdown-menu 内 li.ant-dropdown-menu-item 包含 .operate-item-card 文本「导出」
    const exportItem = page
      .locator('.ant-dropdown:not(.ant-dropdown-hidden) .ant-dropdown-menu-item', { hasText: I18N.export })
      .first();
    await exportItem.waitFor({ state: 'visible' });

    // 重要：先挂 download listener 再 click，避免 race（a[download].click() 同步派发）
    const downloadPromise = page.waitForEvent('download', { timeout: 20_000 });
    await exportItem.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toBe('models.jsonl');

    const content = await readDownloadText(download);
    const lines = content.trim().split('\n');
    expect(lines.length).toBeGreaterThan(0);
    for (const line of lines) {
      const obj = JSON.parse(line);
      expect(obj).toHaveProperty('signature');
      expect(obj.payload.provider_metadata).toBeUndefined();
    }
  });
});
