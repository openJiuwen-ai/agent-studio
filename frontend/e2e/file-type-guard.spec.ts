import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { I18N, ROUTES } from './fixtures/selectors';
import { RouteCounter, buildProviderModelsJsonl, writeTempJsonl } from './fixtures/api-mocks';
import { ImportModalPage } from './pages/import-modal.page';
import { selectPersonalSpace } from './fixtures/workspace';

/**
 * L3-06 文件类型双重校验 — 对应测试方案 UI-06。
 *
 * 验证点：
 *   - 上传非 .jsonl 文件（.txt）被拒
 *   - 弹出错误提示「仅支持 .jsonl 文件」（import-modal.component.ts:87 beforeUpload）
 *   - 不触发预检请求（RouteCounter 计数为 0）
 *
 * 前置：列表页可加载（导入按钮在顶部，不依赖卡片数据）。
 */
test.describe('L3-06 文件类型校验', () => {
  test('上传 .txt 被拒，不触发预检', async ({ page }) => {
    const modal = new ImportModalPage(page);
    const counter = new RouteCounter();
    await counter.install(page, (u) => u.pathname.endsWith('/model-services/import/preview'));

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.listPage);

    // 打开导入弹窗（列表页顶部「导入模型」按钮）
    await page.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });

    // 构造非法 .txt 文件
    const txt = path.join(os.tmpdir(), `e2e-invalid-${process.pid}.txt`);
    fs.writeFileSync(txt, 'not a jsonl', 'utf-8');

    await modal.uploadFile(txt);

    // 错误提示出现
    await modal.expectToastVisible(I18N.fileTypeInvalid);
    // 预检未触发
    expect(counter.count).toBe(0);

    // 清理
    fs.unlinkSync(txt);
  });

  test('上传合法 .jsonl 触发预检', async ({ page }) => {
    const modal = new ImportModalPage(page);
    const counter = new RouteCounter();
    await counter.install(page, (u) => u.pathname.endsWith('/model-services/import/preview'));

    await selectPersonalSpace(page, { navigateFirst: true });
    await page.goto(ROUTES.listPage);
    await page.getByRole('button', { name: I18N.importModels }).click();
    await modal.dialog().waitFor({ state: 'visible' });

    const jsonl = writeTempJsonl(buildProviderModelsJsonl(), 'valid');
    await modal.uploadFile(jsonl);

    await modal.waitForPreview();
    expect(counter.count).toBe(1);
  });
});
