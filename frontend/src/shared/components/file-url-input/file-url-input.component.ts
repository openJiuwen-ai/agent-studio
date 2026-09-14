import { Component, EventEmitter, Input, Output } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { fileUploadAcc } from 'src/pipes/upload-file.pipe';
import {
  checkFileUrl,
  FileUrlCheckError,
  isSupportedUrlType,
  splitUrlText,
} from '@routes/agent-center/file-url.utils';

/** 录入模式：本地上传 | URL 链接 */
export type FileUrlMode = 'upload' | 'url';

/**
 * file 参数 URL 录入子组件（特性：开始节点支持URL方式）。
 *
 * 职责（保守口径）：仅提供"本地上传 | URL链接"模式切换 + URL 模式的
 * 输入/校验/去重/条数限制；上传 UI 与条目列表保留在各宿主组件中，
 * 校验通过的新增 URL 通过 addUrls 事件交由宿主合成同构 FileItem 条目。
 *
 * 仅 image/video 子类型（含 array 形态）显示模式切换；其余 file 子类型
 * 组件整体不渲染（宿主无需按类型条件包裹）。
 */
@Component({
  selector: 'file-url-input',
  templateUrl: './file-url-input.component.html',
  styleUrls: ['./file-url-input.component.less'],
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class FileUrlInputComponent {
  /** 参数完整类型（file/image、array<file/video> 等，与 fileAcc 管道同键） */
  @Input() type = '';

  /** 当前模式（上传 | URL），宿主可双向绑定用于隐藏各自的上传入口 */
  @Input() mode: FileUrlMode = 'upload';

  /** 禁用（宿主上传中 / 已确认态） */
  @Input() disabled = false;

  /** 宿主当前已有条目的 URL 列表（用于全等去重） */
  @Input() existingUrls: string[] = [];

  /** array 形态条数上限（对齐上传 20 条） */
  @Input() maxCount = 20;

  @Output() modeChange = new EventEmitter<FileUrlMode>();

  /** 校验通过、去重后的新增 URL 列表 */
  @Output() addUrls = new EventEmitter<string[]>();

  public urlText = '';

  public error: FileUrlCheckError | 'url_single_only' | 'upload_max_files_tip' | null =
    null;

  public errorParams: { extensions?: string } | null = null;

  /** 本批次存在重复 URL 被自动去重的提示 */
  public dedupedTip = false;

  get showUrlTab(): boolean {
    return isSupportedUrlType(this.type);
  }

  get isMulti(): boolean {
    return (this.type || '').startsWith('array<');
  }

  /** 当前类型允许的扩展名白名单（提示用） */
  get acceptHint(): string {
    return fileUploadAcc[this.type] || '';
  }

  public switchMode(mode: FileUrlMode): void {
    if (this.disabled || mode === this.mode) {
      return;
    }
    this.mode = mode;
    // 两模式输入互斥：切换时清空未提交的 URL 输入内容
    this.urlText = '';
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
    this.modeChange.emit(mode);
  }

  public onAdd(): void {
    if (this.disabled) {
      return;
    }
    const urls = splitUrlText(this.urlText);
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
    if (!urls.length) {
      return;
    }
    if (!this.isMulti && urls.length > 1) {
      this.error = 'url_single_only';
      return;
    }

    // 逐条校验协议头 + 扩展名白名单：任一非法整批阻断，不提交宿主
    for (const url of urls) {
      const error = checkFileUrl(url, this.type);
      if (error) {
        this.error = error;
        this.errorParams =
          error === 'url_invalid_extension'
            ? { extensions: this.acceptHint }
            : null;
        return;
      }
    }

    // 批内 + 与宿主已有条目全等去重（去重后仍提交去重结果）
    const existing = new Set(
      (this.existingUrls || []).map((url) => (url || '').trim()).filter(Boolean),
    );
    const uniqueUrls: string[] = [];
    let deduped = false;
    for (const url of urls) {
      if (existing.has(url)) {
        deduped = true;
        continue;
      }
      existing.add(url);
      uniqueUrls.push(url);
    }
    if (!uniqueUrls.length) {
      this.urlText = '';
      this.dedupedTip = deduped;
      return;
    }

    // array 条数上限（对齐上传口径）
    if (
      this.isMulti &&
      (this.existingUrls?.length || 0) + uniqueUrls.length > this.maxCount
    ) {
      this.error = 'upload_max_files_tip';
      return;
    }

    this.urlText = '';
    this.dedupedTip = deduped;
    this.addUrls.emit(uniqueUrls);
  }
}
