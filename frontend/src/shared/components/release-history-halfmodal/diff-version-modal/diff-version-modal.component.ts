import { ChangeDetectorRef, Component, ElementRef, Input, NgZone, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { I18nNamespace } from '@i18n';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { serializeGraphDslForDiff } from './normalize-graph-dsl-for-diff';

@Component({
  selector: 'diff-version-modal',
  templateUrl: './diff-version-modal.component.html',
  styleUrls: ['./diff-version-modal.component.scss'],
  standalone: true,
  imports: [CommonModule, FormsModule, MODULES, MonacoEditorModule, NzSelectModule, NzTagModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.REVIEW],
    },
  ],
})
export class DiffVersionModalComponent implements OnDestroy {
  @Input() app_id = '';
  @Input() versionList: any[] = [];
  @Input() leftIndex = 0;
  @Input() rightIndex = 0;
  @Input() type = 'agent';

  lineAdd = 0;
  lineDel = 0;
  height = 500;

  originalValue = '';
  modifiedValue = '';

  // 复制按钮反馈（点击后短暂显示"已复制"）
  copiedOriginal = false;
  copiedModified = false;

  // 全屏：把 NzModal 撑满视口（操作 .ant-modal-wrap/.ant-modal/.ant-modal-content 内联样式）
  fullscreen = false;
  private fsSaved: { wrapPad?: string; modalTop?: string; modalWidth?: string; modalMaxWidth?: string; modalPadBottom?: string; contentHeight?: string } = {};

  // 自动换行：单行超过显示宽度时自动拆分到多行（Monaco wordWrap 选项切换）
  wordWrap: 'off' | 'bounded' = 'off';

  // Unit 3：Monaco 单 Model 更新路径 + 资源释放
  private diffEditor?: any;
  private diffUpdateDisposable?: { dispose(): void };
  private originalModel?: { getValue(): string; setValue(v: string): void; dispose(): void };
  private modifiedModel?: { getValue(): string; setValue(v: string): void; dispose(): void };
  private destroyed = false;

  // Unit 4：每侧独立异步治理（DiffSideState）。global dslTooLarge 由两侧 tooLarge 派生，不单独维护易失真状态。
  originalState: DiffSideState = makeSideState();
  modifiedState: DiffSideState = makeSideState();
  /** 大 DSL 字节阈值（实现期用代表性脱敏 fixture 压测后调，见 Open Questions）。用 Blob.size（字节，非 string.length 的 UTF-16 码元）。 */
  largeDslBytesThreshold = 2 * 1024 * 1024;

  get dslTooLarge(): boolean {
    return this.originalState.tooLarge || this.modifiedState.tooLarge;
  }

  leftSelectedId = 'latest';
  rightSelectedId = 'latest';
  leftOptions: VersionOption[] = [];
  rightOptions: VersionOption[] = [];

  diffOptions = {
    enableSplitViewResizing: true,
    renderSideBySide: true,
    renderIndicators: true,
    language: 'json',
    scrollBeyondLastLine: false,
    isInEmbeddedEditor: false,
    automaticLayout: true,
    // 大 DSL（如 9000+ 行工作流）默认 5s 预算会被超时，导致 Monaco 中途放弃剩余 diff 计算，
    // 表现为 minimap 有标记但文本窗部分差异不高亮。设 0 = 不限时，算完整 diff。
    maxComputationTime: 0,
    // minimap：9000+ 行超出等比缩略极限（min 行高 1px），Monaco 走"窗口放大"模式，
    // 滑块反映放大可视区而非全文比例（物理限制）。开 renderCharacters 显示真实代码，便于局部定位。
    minimap: { enabled: true, renderCharacters: true, maxColumn: 80, showSlider: 'always' as const },
  };

  constructor(
    private agentRepoServe: AppAgentRepoService,
    private appFlowRepoServ: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private el: ElementRef<HTMLElement>
  ) {}

  async ngOnInit() {
    const currentLabel = this.i18n.transform('current');
    const versionOptions: VersionOption[] = (this.versionList || []).map(item => ({
      id: item.version_id,
      label: item.version_name,
    }));
    const headOption: VersionOption = { id: 'latest', label: currentLabel };

    this.leftOptions = [headOption, ...versionOptions];
    this.rightOptions = [headOption, ...versionOptions];
    this.leftSelectedId = this.resolveSelectedId(this.leftOptions, this.leftIndex);
    this.rightSelectedId = this.resolveSelectedId(this.rightOptions, this.rightIndex);

    // 并发加载两侧，各自序号独立；失败由 loadSide 的 catch 维护该侧 error，不再吞错返 {}
    await Promise.all([
      this.loadSide('original', this.leftSelectedId),
      this.loadSide('modified', this.rightSelectedId),
    ]);
  }

  onDiffInit(editor: any) {
    if (this.destroyed) {
      return;
    }
    if (!editor?.onDidUpdateDiff) {
      return;
    }
    this.diffEditor = editor;
    // Monaco diff editor 对初始化 options 里的 minimap 支持不稳，创建后再显式设一次。
    editor.updateOptions?.({ minimap: { enabled: true, renderCharacters: true, maxColumn: 80, showSlider: 'always' } });
    const model = editor.getModel?.();
    this.originalModel = model?.original;
    this.modifiedModel = model?.modified;
    // 释放旧监听再挂新的，避免重复监听
    this.diffUpdateDisposable?.dispose?.();
    this.diffUpdateDisposable = editor.onDidUpdateDiff(() => {
      const changes = editor.getLineChanges?.() ?? [];
      const { lineAdd, lineDel } = this.calcChangeLines(changes);
      this.ngZone.run(() => {
        this.height = Math.min(((this.modifiedValue || '').split('\n').length + lineDel) * 19 + 100, document.documentElement.clientHeight * 0.7);
        this.lineAdd = lineAdd;
        this.lineDel = lineDel;
        this.cdr.detectChanges();
      });
    });
    this.applyValues();
  }

  /** 销毁后不再触发变更检测（避免 ViewDestroyedError）。 */
  private safeDetect() {
    if (!this.destroyed) {
      this.cdr.detectChanges();
    }
  }

  /** 单 Model 更新路径：用存的 originalModel/modifiedModel 直接 setValue，不依赖 Materia ngOnChanges（修 original 侧不刷新 + Model 泄漏）。幂等：仅当值不同且该侧未超限才写。 */
  private applyValues() {
    if (this.destroyed || !this.diffEditor) {
      return;
    }
    if (this.originalModel && !this.originalState.tooLarge && this.originalModel.getValue() !== this.originalValue) {
      this.originalModel.setValue(this.originalValue);
    }
    if (this.modifiedModel && !this.modifiedState.tooLarge && this.modifiedModel.getValue() !== this.modifiedValue) {
      this.modifiedModel.setValue(this.modifiedValue);
    }
  }

  ngOnDestroy() {
    this.destroyed = true;
    this.diffUpdateDisposable?.dispose?.();
    // 防御式：不依赖 Materia child 是否先销毁 editor——先 isDisposed 守卫再 setModel(null)
    if (this.diffEditor && !this.diffEditor.isDisposed?.()) {
      this.diffEditor.setModel?.(null);
    }
    this.originalModel?.dispose?.();
    this.modifiedModel?.dispose?.();
    this.diffEditor = undefined;
    this.originalModel = undefined;
    this.modifiedModel = undefined;
  }

  async changeLeft(id: string) {
    this.leftSelectedId = id;
    await this.loadSide('original', id);
  }

  async changeRight(id: string) {
    this.rightSelectedId = id;
    await this.loadSide('modified', id);
  }

  /** 重试入口：用当前选中版本复跑。 */
  retryOriginal() {
    return this.loadSide('original', this.leftSelectedId);
  }
  retryModified() {
    return this.loadSide('modified', this.rightSelectedId);
  }

  /** 编辑器高度：全屏时填满视口（减去标题+工具栏+banner），否则用按内容算的 height。 */
  get editorHeight(): number {
    if (this.fullscreen) {
      return Math.max((document.documentElement.clientHeight || 600) - 150, 240);
    }
    return this.height;
  }

  /** 切换全屏：操作 NzModal 的 .ant-modal-wrap/.ant-modal/.ant-modal-content 内联样式铺满视口。 */
  toggleFullscreen() {
    this.fullscreen = !this.fullscreen;
    const host = this.el?.nativeElement;
    const wrap = host?.closest('.ant-modal-wrap') as HTMLElement | null;
    const modal = host?.closest('.ant-modal') as HTMLElement | null;
    const content = modal?.querySelector('.ant-modal-content') as HTMLElement | null;
    if (this.fullscreen) {
      this.fsSaved = {
        wrapPad: wrap?.style.padding,
        modalTop: modal?.style.top,
        modalWidth: modal?.style.width,
        modalMaxWidth: modal?.style.maxWidth,
        modalPadBottom: modal?.style.paddingBottom,
        contentHeight: content?.style.height,
      };
      if (wrap) wrap.style.padding = '0';
      if (modal) {
        modal.style.top = '0';
        modal.style.width = '100vw';
        modal.style.maxWidth = 'none';
        modal.style.paddingBottom = '0';
      }
      if (content) content.style.height = '100vh';
    } else {
      if (wrap) wrap.style.padding = this.fsSaved.wrapPad ?? '';
      if (modal) {
        modal.style.top = this.fsSaved.modalTop ?? '';
        modal.style.width = this.fsSaved.modalWidth ?? '';
        modal.style.maxWidth = this.fsSaved.modalMaxWidth ?? '';
        modal.style.paddingBottom = this.fsSaved.modalPadBottom ?? '';
      }
      if (content) content.style.height = this.fsSaved.contentHeight ?? '';
    }
    this.cdr.detectChanges();
  }

  /** 切换自动换行：单行超过显示宽度时自动拆分到多行（Monaco wordWrap: 'bounded'）。 */
  toggleWordWrap() {
    this.wordWrap = this.wordWrap === 'bounded' ? 'off' : 'bounded';
    this.diffEditor?.updateOptions?.({ wordWrap: this.wordWrap });
    this.cdr.detectChanges();
  }

  /** 跳转到上一个差异块：根据 getLineChanges + revealLineInCenter 实现，到底后回到最后一个。 */
  previousDiff() {
    const changes = this.diffEditor?.getLineChanges?.() ?? [];
    if (!changes.length) return;
    const modifiedEditor = this.diffEditor?.getModifiedEditor?.();
    const originalEditor = this.diffEditor?.getOriginalEditor?.();
    if (!modifiedEditor) return;
    const visibleRange = modifiedEditor.getVisibleRanges?.()?.[0];
    const currentLine = visibleRange?.startLineNumber ?? 1;
    let targetChange: any = null;
    for (let i = changes.length - 1; i >= 0; i--) {
      const line = changes[i].modifiedStartLineNumber || changes[i].originalStartLineNumber;
      if (line && line < currentLine) {
        targetChange = changes[i];
        break;
      }
    }
    if (!targetChange) targetChange = changes[changes.length - 1]; // 到头则绕回最后一个
    if (targetChange) {
      if (targetChange.modifiedStartLineNumber > 0) {
        modifiedEditor.revealLineInCenter(targetChange.modifiedStartLineNumber);
      }
      if (originalEditor && targetChange.originalStartLineNumber > 0) {
        originalEditor.revealLineInCenter(targetChange.originalStartLineNumber);
      }
    }
    this.focusModified();
  }

  /** 跳转到下一个差异块：以视口底行为基准,找下一个差异(避免与 revealLineInCenter 的居中行为打转)。到底后绕回第一个。 */
  nextDiff() {
    const changes = this.diffEditor?.getLineChanges?.() ?? [];
    if (!changes.length) return;
    const modifiedEditor = this.diffEditor?.getModifiedEditor?.();
    const originalEditor = this.diffEditor?.getOriginalEditor?.();
    if (!modifiedEditor) return;
    const visibleRange = modifiedEditor.getVisibleRanges?.()?.[0];
    // 用视口底行当基准:revealLineInCenter 把目标放中央,底行会越过目标往下走,
    // 用底行做"已越过"判断,保证每次点击都前进
    const refLine = visibleRange?.endLineNumber ?? visibleRange?.startLineNumber ?? 1;
    let targetChange: any = null;
    for (const c of changes) {
      const line = c.modifiedStartLineNumber || c.originalStartLineNumber;
      if (line && line > refLine) {
        targetChange = c;
        break;
      }
    }
    if (!targetChange && changes.length > 0) targetChange = changes[0]; // 到头则绕回第一个
    if (targetChange) {
      if (targetChange.modifiedStartLineNumber > 0) {
        modifiedEditor.revealLineInCenter(targetChange.modifiedStartLineNumber);
      }
      if (originalEditor && targetChange.originalStartLineNumber > 0) {
        originalEditor.revealLineInCenter(targetChange.originalStartLineNumber);
      }
    }
    this.focusModified();
  }

  /** 跳转后把焦点设到 modified 编辑器（避免焦点停在不可见元素）。 */
  private focusModified() {
    try {
      this.diffEditor?.getModifiedEditor?.()?.focus?.();
    } catch {
      // 忽略
    }
  }

  /** 复制左侧（original）版本文本到剪贴板。 */
  copyOriginal() {
    const ok = this.copyText(this.originalValue);
    this.flashCopied('original', ok);
  }

  /** 复制右侧（modified）版本文本到剪贴板。 */
  copyModified() {
    const ok = this.copyText(this.modifiedValue);
    this.flashCopied('modified', ok);
  }

  /**
   * 复制文本到剪贴板。优先 clipboard API（需 secure context），
   * 否则走 execCommand('copy') 兜底（本环境为 http://100.90.140.57:4200 非 secure context，execCommand 是主路径）。
   */
  private copyText(text: string): boolean {
    try {
      if (navigator?.clipboard?.writeText && (window as any).isSecureContext) {
        navigator.clipboard.writeText(text).catch(() => this.legacyCopy(text));
        return true;
      }
    } catch {
      // 落到 legacy
    }
    return this.legacyCopy(text);
  }

  private legacyCopy(text: string): boolean {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.top = '-1000px';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    document.body.removeChild(ta);
    return ok;
  }

  private flashCopied(side: 'original' | 'modified', ok: boolean) {
    if (side === 'original') {
      this.copiedOriginal = ok;
    } else {
      this.copiedModified = ok;
    }
    this.cdr.detectChanges();
    setTimeout(() => {
      if (side === 'original') {
        this.copiedOriginal = false;
      } else {
        this.copiedModified = false;
      }
      this.safeDetect();
    }, 1500);
  }

  /**
   * 每侧异步治理：所有状态提交（成功/失败/超限/loading 结束）都过 commitIfCurrent 守卫，
   * 旧请求不得覆盖新选择。失败保留上次成功 value/sourceText；大 DSL 按侧 tooLarge，全局 dslTooLarge 派生。
   */
  async loadSide(side: 'original' | 'modified', versionId: string): Promise<void> {
    const isOriginal = side === 'original';
    const state = isOriginal ? this.originalState : this.modifiedState;
    const currentSelectedId = () => (isOriginal ? this.leftSelectedId : this.rightSelectedId);
    const seq = ++state.requestSeq;
    const commitIfCurrent = () => !this.destroyed && state.requestSeq === seq && currentSelectedId() === versionId;

    state.loading = true;
    state.error = null;
    state.tooLarge = false; // 新请求重置（大→小切换恢复）
    this.safeDetect();

    try {
      const dsl = await this.loadVersion(this.type, this.app_id, versionId);
      const text = serializeGraphDslForDiff(dsl);
      // 先用局部变量计算，不污染共享状态；过期响应在下面 return，不写 state
      const tooLarge = new Blob([text]).size > this.largeDslBytesThreshold;
      if (!commitIfCurrent()) {
        return;
      }
      // 确认仍是当前请求后，一次性提交该侧状态（tooLarge 含过期响应不再被写入）
      state.tooLarge = tooLarge;
      state.sourceText = text;
      if (!tooLarge) {
        if (isOriginal) {
          this.originalValue = text;
        } else {
          this.modifiedValue = text;
        }
        state.lastSuccessfulVersionId = versionId;
        this.applyValues();
      }
    } catch (e) {
      if (commitIfCurrent()) {
        state.error = e; // 保留上次成功 originalValue/modifiedValue、sourceText、lastSuccessfulVersionId
      }
    } finally {
      if (commitIfCurrent()) {
        state.loading = false;
        this.safeDetect();
      }
    }
  }

  /** 纯投影：按资源类型从响应提取可比较 DSL。字段缺失抛错，不返 {}。 */
  projectDsl(type: string, response: any): unknown {
    if (type === 'workflow') {
      const dsl = response?.workflow_details;
      if (dsl === undefined || dsl === null) {
        throw new Error('workflow_details 缺失，无法对比');
      }
      return dsl;
    }
    if (type === 'multi') {
      const dsl = response?.details;
      if (dsl === undefined || dsl === null) {
        throw new Error('details 缺失，无法对比');
      }
      return dsl;
    }
    throw new Error('unsupported in phase 1: ' + type);
  }

  /** 类型分派取数：agent 直接抛"不支持"且不发网络请求；workflow/multi 按 latest/版本 调对应接口再投影。 */
  async loadVersion(type: string, appId: string, versionId: string): Promise<unknown> {
    if (type === 'workflow') {
      const value =
        versionId === 'latest'
          ? await this.appFlowRepoServ.getFlow(appId)
          : await this.agentRepoServe.rollbackFlowVersion(appId, versionId);
      return this.projectDsl('workflow', value);
    }
    if (type === 'multi') {
      const value =
        versionId === 'latest'
          ? await this.agentRepoServe.getMultiAgent(appId)
          : await this.agentRepoServe.rollbackAgentVersion(appId, versionId);
      return this.projectDsl('multi', value);
    }
    // agent 及未知类型：阶段一显式拒绝，不误入 multi 的 details 提取
    throw new Error('unsupported in phase 1: ' + type);
  }

  /** 边界兜底：leftIndex/rightIndex 越界或 options 为空时回退 'latest'，避免弹窗初始化崩。 */
  resolveSelectedId(options: VersionOption[], index: number): string {
    return options[index + 1]?.id ?? 'latest';
  }

  /** 左右是否选了同一版本（用于同版本提示徽标）。 */
  get isSameVersion(): boolean {
    return this.leftSelectedId === this.rightSelectedId;
  }

  /** 任一侧失败期间，差异行统计不可信（下拉已显示新选择、editor 仍显示旧内容），模板据此隐藏 +N/-N。 */
  get hasError(): boolean {
    return !!this.originalState.error || !!this.modifiedState.error;
  }

  /** 该侧"当前实际显示"的版本名（lastSuccessfulVersionId → label），失败时用于"当前仍显示版本 X"提示。 */
  displayedVersionLabel(side: 'original' | 'modified'): string {
    const state = side === 'original' ? this.originalState : this.modifiedState;
    const options = side === 'original' ? this.leftOptions : this.rightOptions;
    const id = state.lastSuccessfulVersionId;
    if (id === null) {
      return '';
    }
    return options.find(o => o.id === id)?.label ?? id;
  }

  private calcChangeLines(changes: any[]) {
    let lineAdd = 0;
    let lineDel = 0;
    (changes || []).forEach(change => {
      if (change.modifiedEndLineNumber && change.modifiedStartLineNumber) {
        lineAdd += change.modifiedEndLineNumber - change.modifiedStartLineNumber + 1;
      }
      if (change.originalEndLineNumber && change.originalStartLineNumber) {
        lineDel += change.originalEndLineNumber - change.originalStartLineNumber + 1;
      }
    });
    return { lineAdd, lineDel };
  }
}

interface VersionOption {
  id: string;
  label: string;
}

interface DiffSideState {
  requestSeq: number;
  loading: boolean;
  error: unknown | null;
  tooLarge: boolean;
  sourceText: string;
  lastSuccessfulVersionId: string | null;
}

function makeSideState(): DiffSideState {
  return {
    requestSeq: 0,
    loading: false,
    error: null,
    tooLarge: false,
    sourceText: '',
    lastSuccessfulVersionId: null,
  };
}
