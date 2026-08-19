import { expect, Locator, Page } from '@playwright/test';
import { I18N } from '../fixtures/selectors';

/**
 * 导入弹窗页面对象（meta-model-import-modal）。
 *
 * 弹窗结构（import-modal.component.html）：
 *   - 文件上传：nz-upload.import-upload（内含 input[type=file]）
 *   - 预检：preview 表（service_name/provider_id/冲突/签名/API URL/环境变量/详情）+ 总数/冲突汇总
 *   - 冲突策略：nz-radio-group（同名跳过 / 同名覆盖，COVER 显示警告）
 *   - 结果：成功/失败 tag + 结果表
 *   - footer：取消 / 确认导入（成功后变 确定）
 */
export class ImportModalPage {
  constructor(private readonly page: Page) {}

  /** 弹窗根 locator。 */
  dialog(): Locator {
    return this.page.locator('meta-model-import-modal');
  }

  /** 隐藏的文件 input（nz-upload 内）。 */
  uploadInput(): Locator {
    return this.dialog().locator('nz-upload.import-upload input[type="file"]');
  }

  /** 上传文件，触发 beforeUpload → runPreview。 */
  async uploadFile(filePath: string): Promise<void> {
    await this.uploadInput().setInputFiles(filePath);
  }

  /** 等待预检结果出现（preview 总数/冲突汇总）。 */
  async waitForPreview(): Promise<void> {
    await this.dialog().getByText(I18N.previewTotal).waitFor({ state: 'visible' });
  }

  /** 预检冲突数文本（用于断言 conflict_count）。 */
  previewConflictText(): Locator {
    return this.dialog().locator('.preview-summary');
  }

  /** 切换冲突策略。 */
  async selectStrategy(strategy: 'SKIP' | 'COVER'): Promise<void> {
    const label = strategy === 'COVER' ? I18N.cover : I18N.skip;
    const radio = this.dialog().locator('label[nz-radio-button]', { hasText: label }).first();
    await radio.waitFor({ state: 'visible' });
    await radio.click();
  }

  /** COVER 警告文案 locator（仅选 COVER 后可见）。 */
  coverWarning(): Locator {
    return this.dialog().getByText(I18N.coverWarn);
  }

  /** 确认导入按钮。 */
  confirmButton(): Locator {
    return this.dialog().getByRole('button', { name: I18N.confirmImport });
  }

  /** 点击确认导入。 */
  async confirm(): Promise<void> {
    await this.confirmButton().click();
  }

  /** 等待导入结果出现。 */
  async waitForResult(): Promise<void> {
    await this.dialog().getByText(I18N.importResult).waitFor({ state: 'visible' });
  }

  /** 结果中成功/失败 tag 文本（含数量）。 */
  resultTag(kind: 'succeed' | 'failed'): Locator {
    const text = kind === 'succeed' ? I18N.importResultSucceed : I18N.importResultFailed;
    return this.dialog().locator('.result-summary').getByText(text);
  }

  /** 关闭弹窗（确定/取消）。 */
  async close(): Promise<void> {
    await this.dialog().getByRole('button', { name: I18N.ok }).click().catch(async () => {
      await this.dialog().getByRole('button', { name: I18N.cancel }).click();
    });
  }

  /** 全局消息提示（NzMessage，body 末尾）。 */
  toast(text: string): Locator {
    return this.page.locator('body').getByText(text, { exact: false });
  }

  async expectToastVisible(text: string): Promise<void> {
    await expect(this.toast(text)).toBeVisible({ timeout: 10_000 });
  }
}
