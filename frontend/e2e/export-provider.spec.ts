import { test, expect } from '@playwright/test';
import { I18N, ROUTES } from './fixtures/selectors';
import { mockExport, buildProviderModelsJsonl, readDownloadText } from './fixtures/api-mocks';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-01 供应商+模型导出（列表页卡片 hover）— 对应测试方案 UI-01 / API-01。
 *
 * 验证点：
 *   - 先选 workspace「个人空间」（否则 workspace_id 为空导致列表空）
 *   - hover 供应商卡片 → hover footer 显示「导出」按钮，点击触发下载
 *   - 导出请求 body 含 provider_id（按供应商导出，exportModelsByProvider）
 *   - 下载文件名 provider-models.jsonl
 *   - 每行含 signature 字段 + payload.provider_metadata（供应商+模型模式）
 *
 * 关键实现细节：必须在 click() 之前挂起 waitForEvent('download')，否则
 * 前端同步触发的 a[download].click() 会在 listener 注册之前派发 download 事件，
 * 导致 Playwright 收不到事件（race condition）。
 */
test.describe('L3-01 供应商+模型导出', () => {
  test('hover 卡片→导出→下载 provider-models.jsonl，行含签名与 provider 元数据', async ({ page }) => {
    test.skip(!process.env.E2E_PROVIDER_ID, '需 E2E_PROVIDER_ID 指向已存在的供应商');

    const jsonl = buildProviderModelsJsonl();
    await mockExport(page, jsonl, 'provider-models.jsonl', (route) => {
      const body = route.request().postDataJSON() as Record<string, unknown>;
      // 卡片入口按供应商导出：body 为 { provider_id } 而非 model_ids
      expect(body.provider_id).toBeTruthy();
      expect(body.model_ids).toBeUndefined();
    });

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.listPage);

    await page.getByText('自定义模型').first().waitFor({ state: 'visible' });
    await page.waitForTimeout(1500);

    // 取第一个可用（非 disabled）的供应商卡片的导出按钮
    const cards = page.locator('.model-card');
    const cardCount = await cards.count();
    let exportBtn = cards.nth(0).locator('.card-footer-action-btn', { hasText: I18N.export }).first();
    for (let i = 0; i < Math.min(cardCount, 6); i++) {
      const c = cards.nth(i);
      await c.hover();
      await page.waitForTimeout(300);
      const btn = c.locator('.card-footer-action-btn', { hasText: I18N.export }).first();
      const visible = await btn.isVisible().catch(() => false);
      if (visible) {
        const disabled = await btn.isDisabled().catch(() => true);
        if (!disabled) {
          exportBtn = btn;
          break;
        }
      }
    }
    await expect(exportBtn).toBeVisible();
    await expect(exportBtn).toBeEnabled();

    // 重要：先挂 download listener 再 click，避免 race
    const downloadPromise = page.waitForEvent('download', { timeout: 20_000 });
    await exportBtn.click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toBe('provider-models.jsonl');

    const content = await readDownloadText(download);
    const lines = content.trim().split('\n');
    expect(lines.length).toBeGreaterThan(0);
    for (const line of lines) {
      const obj = JSON.parse(line);
      expect(obj).toHaveProperty('signature');
      expect(obj.payload.provider_metadata).toBeTruthy();
    }
  });
});
