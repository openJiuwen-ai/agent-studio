import { expect, type Page } from '@playwright/test';

/**
 * Workspace 选择 helper。
 *
 * 关键点：页面刷新后即使 UI 上显示某 workspace 文字，若未主动点选过一次，
 * 发往后端的 workspace_id 会是空字符串，导致 custom-models/provider/search 等
 * 接口返回 400/空数组，列表/详情页出现"暂无数据"。此 helper 显式点一次 workspace
 * nz-select，选中目标工作空间并等待切换完成。
 *
 * @param page Playwright Page
 * @param opts.name 目标 workspace 名（按选项文本 contains 匹配，因选项后缀带" 空间所有者"）；默认"个人空间"
 * @param opts.navigateFirst true 时先 goto `#/home/overview` 确保应用已加载
 */
export async function selectWorkspace(
  page: Page,
  opts: { name?: string; navigateFirst?: boolean } = {},
): Promise<void> {
  const targetName = opts.name ?? '个人空间';
  if (opts.navigateFirst) {
    await page.goto('#/home/overview');
  } else {
    const url = page.url();
    if (!url.includes('/home/') && !url.includes('#/home')) {
      await page.goto('#/home/overview');
    }
  }
  // 等 Angular app 完成 boot（左侧菜单"总览"出现）
  await page.getByText('总览', { exact: true }).first().waitFor({ state: 'visible', timeout: 60_000 });
  await page.waitForTimeout(500);

  const sel = page.locator('nz-select,.ant-select').first();
  await sel.waitFor({ state: 'visible', timeout: 20_000 });

  // 带重试地打开下拉并选中目标项：onBeforeOpen 首次触发 workspace/init 可能慢，
  // 一次点不开/没选项时最多重试 3 次。
  const maxAttempts = 3;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      // 若下拉已打开先关闭再点（避免前一轮残留）
      const dropdownVisible = await page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)').count()
        .then(c => c > 0)
        .catch(() => false);
      if (!dropdownVisible) {
        await sel.click({ timeout: 5_000 });
        await page.waitForTimeout(800);
      }
      const opt = page
        .locator('.ant-select-dropdown .ant-select-item-option, nz-option-container nz-option-item')
        .filter({ hasText: targetName })
        .first();
      await opt.waitFor({ state: 'visible', timeout: attempt === 1 ? 8_000 : 15_000 });
      await opt.click();
      await expect(page.locator('.ant-select-dropdown').last()).toBeHidden({ timeout: 5_000 }).catch(() => {});
      await page.waitForTimeout(1500);
      return;
    } catch (e) {
      console.log(`[workspace] select "${targetName}" attempt ${attempt} failed: ${(e as Error).message.slice(0, 120)}`);
      // 按 ESC 关掉可能半开的下拉，准备重试
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(500);
      await page.keyboard.press('Escape').catch(() => {});
      await page.waitForTimeout(500);
    }
  }
  throw new Error(`[selectWorkspace] failed to select "${targetName}" after ${maxAttempts} attempts`);
}

/** 选"个人空间"（最常用场景的糖方法）。 */
export async function selectPersonalSpace(
  page: Page,
  opts: { navigateFirst?: boolean } = {},
): Promise<void> {
  await selectWorkspace(page, { name: '个人空间', navigateFirst: opts.navigateFirst });
}
