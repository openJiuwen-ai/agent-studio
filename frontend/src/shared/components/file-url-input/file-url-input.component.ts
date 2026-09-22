import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';
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
export class FileUrlInputComponent implements OnChanges {
  /** 参数完整类型（file/image、array<file/video> 等，与 fileAcc 管道同键） */
  @Input() type = '';

  /**
   * 当前模式（上传 | URL），宿主可双向绑定用于隐藏各自的上传入口。
   * 宿主回填参数的 urlMode 初始为 undefined，若不归一为 upload：
   * 1) 首开无 Tab 高亮（与 §4.1「默认选中本地上传」不符）；
   * 2) 点「本地上传」会绕过 switchMode 同值早退、照发 modeChange。
   */
  @Input()
  public set mode(mode: FileUrlMode) {
    this._mode = mode || 'upload';
  }

  public get mode(): FileUrlMode {
    return this._mode;
  }

  private _mode: FileUrlMode = 'upload';

  /** 禁用（宿主上传中 / 已确认态） */
  @Input() disabled = false;

  /**
   * 互斥：宿主已存在本地上传来源的条目时，URL 录入被阻断（提示先清空文件）。
   * 仅阻断 URL 录入，不影响页签切换（用户仍可切回本地上传）。
   */
  @Input() localEntriesExist = false;

  /** 宿主当前已有条目的 URL 列表（用于全等去重） */
  @Input() existingUrls: string[] = [];

  /** array 形态条数上限（对齐上传 20 条） */
  @Input() maxCount = 20;

  /**
   * 宿主发起的「编辑回填」请求（URL 条目编辑入口）：每次传入新对象触发，
   * 把被编辑条目的 URL 载入输入框待修改。条目保留在宿主列表中（原位编辑），
   * 用户修改后点「保存」提交（saveEdit），点「取消」或切换页签放弃编辑。
   */
  @Input()
  public set editRequest(req: { url: string } | null) {
    if (!req?.url) {
      return;
    }
    this.urlText = req.url;
    this.editingUrl = req.url;
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
  }

  @Output() modeChange = new EventEmitter<FileUrlMode>();

  /** 校验通过、去重后的新增 URL 列表 */
  @Output() addUrls = new EventEmitter<string[]>();

  /** 编辑态保存：originalUrl 定位被编辑条目，url 为修改后的值（宿主原位替换） */
  @Output() saveEdit = new EventEmitter<{
    originalUrl: string;
    url: string;
  }>();

  public urlText = '';

  /** 正在编辑的条目原 URL（null = 新增态） */
  public editingUrl: string | null = null;

  public error: FileUrlCheckError | 'url_single_only' | 'upload_max_files_tip' | null =
    null;

  public errorParams: { extensions?: string } | null = null;

  /** 本批次存在重复 URL 被自动去重的提示 */
  public dedupedTip = false;

  /**
   * 被编辑条目已从宿主列表移除（单条删除/清空文件）时自动退出编辑态，
   * 避免「保存」指向已不存在的条目（点击不生效）。
   * 宿主的 existingUrls 每轮变更检测新构造数组，此钩子随之触发，
   * 判定成本为一次 includes。
   */
  ngOnChanges(changes: SimpleChanges): void {
    if (
      this.editingUrl &&
      changes['existingUrls'] &&
      !(this.existingUrls || []).includes(this.editingUrl)
    ) {
      this.onCancelEdit();
    }
  }

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
    // 两模式输入互斥：切换时清空未提交的 URL 输入内容；
    // 编辑态随切换一并放弃（条目保留在宿主列表中，不丢数据）
    this.urlText = '';
    this.editingUrl = null;
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
    this.modeChange.emit(mode);
  }

  /** 取消编辑：放弃未保存的修改（被编辑条目保留原值，无需通知宿主） */
  public onCancelEdit(): void {
    this.urlText = '';
    this.editingUrl = null;
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
  }

  public onAdd(): void {
    if (this.disabled || this.localEntriesExist) {
      return;
    }
    const urls = splitUrlText(this.urlText);
    this.error = null;
    this.errorParams = null;
    this.dedupedTip = false;
    if (!urls.length) {
      return;
    }
    // 编辑态针对单条目，只允许提交一条；单文件类型同理
    if ((this.editingUrl || !this.isMulti) && urls.length > 1) {
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

    // 批内 + 与宿主已有条目全等去重（去重后仍提交去重结果）；
    // 编辑态排除被编辑条目的原 URL（允许不改原值直接保存）
    const existing = new Set(
      (this.existingUrls || []).map((url) => (url || '').trim()).filter(Boolean),
    );
    if (this.editingUrl) {
      existing.delete(this.editingUrl);
    }
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

    // 编辑态：原位保存被编辑条目（不增条数，跳过条数上限）
    if (this.editingUrl) {
      if (!uniqueUrls.length) {
        // 新值与其它条目重复：保留输入内容与编辑态，仅提示
        this.dedupedTip = deduped;
        return;
      }
      const originalUrl = this.editingUrl;
      this.urlText = '';
      this.editingUrl = null;
      this.saveEdit.emit({ originalUrl, url: uniqueUrls[0] });
      return;
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
