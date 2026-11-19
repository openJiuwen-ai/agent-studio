import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  forwardRef,
  HostListener,
  Input,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import { MODULES } from '@shared/modules';
import { Observable } from 'rxjs';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';

const LIST_WIDTH = 128;
const LIST_ITEM_HEIGHT = 26;
const SAFE_OFFSET = 10;
const PANAEL_PADDING = 16;
const MAX_VIEW_ITEMS = 6;
const LEFT_OFFSET = 6;

// 撤销/重做：原生撤销栈会被 processContent/renderFromText 的 innerHTML
// 整体重写摧毁（且 Enter/退格/粘贴均为 preventDefault + 手动 DOM 手术），
// 因此基于纯文本快照自建历史栈。连续普通输入在时间窗内合并为一条撤销
// 记录，结构性编辑（回车/删除/粘贴/变量插入/缩进）单独成条。
const UNDO_LIMIT = 100;
const UNDO_COALESCE_MS = 1000;
const STRUCTURAL_KEYS = new Set([
  'Enter',
  'Backspace',
  'Delete',
  'Tab',
  'paste',
  'cut',
  'template',
]);

export interface CmdTextareaVariableItem {
  label: string;
  value: string;
}

export interface CmdTextareaVariableGroup {
  label: string;
  items: CmdTextareaVariableItem[];
}

@Component({
  selector: 'meta-cmd-textarea',
  templateUrl: './cmd-textarea.component.html',
  styleUrls: ['./cmd-textarea.component.less'],
  standalone: true,
  imports: [MODULES, ClickOutsideDirective],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => CmdTextareaComponent),
      multi: true,
    },
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class CmdTextareaComponent implements ControlValueAccessor {
  // CMDS由常量改为组件输入，方便自定义命令。同时设置默认值，以便不需要修改原来使用的地方
  @Input() CMDS?: string[] = ['/', '{'];

  @Input() variants: Array<
    CmdTextareaVariableGroup | CmdTextareaVariableItem | string
  > = [];
  // 最大长度
  @Input() maxLength?: number;

  // 传入一个订阅，触发时显示或关闭变量选择列表
  @Input() variantsTrigger?: Observable<boolean>;

  // 传入一个订阅，触发时以内联模式（{{{var}}}）显示变量选择列表
  @Input() inlineVariantsTrigger?: Observable<boolean>;

  @Input() placeholder = '';

  @Input() maxHeight = '480px';

  @Input() minHeight = '200px';

  /** 开启后仅高亮 variants 中已声明的 {{var}} / {{{var}}}，其余花括号按普通文本展示 */
  @Input() highlightKnownOnly = false;

  @Output() compositionstart = new EventEmitter<CompositionEvent>();

  @Output() compositionend = new EventEmitter<CompositionEvent>();

  @Output() blur = new EventEmitter<void>();

  @ViewChild('cmdEditor') editor: ElementRef<HTMLDivElement>;

  @ViewChild('list') list: ElementRef<HTMLDivElement>;

  isTriggerClick = false; //判断是否由点击生成list,是的话替换时不需要扣除 触发命令的长度，比如'{'

  // 当前插入模式：'double' = {{var}} 参数化，'triple' = {{{var}}} 内联
  private insertMode: 'double' | 'triple' = 'double';

  content = '';

  disabled = false;

  innerVariants: Array<CmdTextareaVariableGroup> = [];

  innerVariantsItems: Array<CmdTextareaVariableItem> = [];

  // 与 innerVariantsItems 逐项对应的坐标映射 [分组下标, 组内下标]。
  // innerVariantsItems 统一按列表 DOM 渲染顺序（默认分组在前）扁平化，
  // 本映射供滚动定位按坐标精确取 DOM 节点，不依赖全局平铺顺序。
  private flatItemCoords: Array<[number, number]> = [];

  private preVariantsHash: string = ''; // 当前变量的哈希值，用于判断变量是否真正发生了变化

  private preAction: string = ''; // 记录按键

  // ===== 撤销/重做 =====
  private undoStack: Array<{ text: string; offset: number }> = [];

  private redoStack: Array<{ text: string; offset: number }> = [];

  // 最近一次编辑事务后的编辑器状态，作为下一次编辑的"编辑前快照"
  private lastState: { text: string; offset: number } = { text: '', offset: 0 };

  private lastPushTime = 0; // 上次撤销记录入栈时间，用于连续输入合并

  private applyingHistory = false; // 撤销/重做回放中，emit 不再记录历史

  private onChange: (value: string) => void = () => {};

  private onTouched: () => void = () => {};

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  writeValue(value: string): void {
    const raw = value?.trim() ?? '';
    const escaped = this.escapeHTML(raw);
    setTimeout(() => {
      this.editor.nativeElement.innerHTML = `${escaped}<br>`;
      // 外部真实变更（节点回填/表单重置）时重建撤销基线。
      // 对比口径必须一致（lastState.text 同样 trim 比较），否则带末尾
      // 空格/首行缩进的 ngModel 回写会被误判为外部变更而清空撤销栈——
      // 正是本组件要修的问题复现。同值回写不重置历史。
      if (raw !== this.lastState.text.trim()) {
        this.lastState = { text: raw, offset: raw.length };
        this.undoStack = [{ ...this.lastState }];
        this.redoStack = [];
        // 基线重建后重置连续输入合并窗口：外部回填后的首次输入
        // 必须独立成条，不能被并入回填前的输入串
        this.lastPushTime = 0;
      } else if (raw !== this.lastState.text) {
        // 仅首尾空白差异：writeValue 渲染的是 trim 后文本，保留撤销栈，
        // 只把基线对齐到实际渲染内容
        this.lastState = { text: raw, offset: raw.length };
        this.lastPushTime = 0;
      }
      this.cdr.detectChanges();
    });
  }

  selection: Selection | null = null;

  left = 0;

  top = 0;

  _showList = false;

  public selectedIndex = 0;

  private varTriggerSubscribe = undefined;

  private inlineVarTriggerSubscribe = undefined;

  private editorObserver: MutationObserver;

  get range() {
    return this.selection?.rangeCount ? this.selection.getRangeAt(0) : null;
  }

  // processContent执行次数
  reRenderTimes: number = 0;
  // 在输入中，处理输入法组合输入
  inInput = false;

  constructor(private cdr: ChangeDetectorRef,) {
    this.editorObserver = new MutationObserver(() => {
      setTimeout(() => {
        if (!this.inInput) {
          this.processContent();
        }
      }, 5);
    });
  }

  ngOnInit() {
    this.varTriggerSubscribe = this.variantsTrigger?.subscribe((show) => {
      if (show) {
        this.insertMode = 'double';
        this.checkAndRestoreCursorPosition();
        this.scrollCursorToVisible();
        this.showVarList();
        this.isTriggerClick = true;
      } else {
        this.showList = false;
      }
    });
    this.inlineVarTriggerSubscribe = this.inlineVariantsTrigger?.subscribe(
      (show) => {
        if (show) {
          this.insertMode = 'triple';
          this.checkAndRestoreCursorPosition();
          this.scrollCursorToVisible();
          this.showVarList();
          this.isTriggerClick = true;
        } else {
          this.showList = false;
        }
      },
    );
  }

  ngAfterViewInit() {
    // 等待元素渲染完成后开始监听
    this.editorObserver.observe(this.editor.nativeElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    // 特殊要求，光标位置特殊处理
    document.addEventListener('selectionchange', this.processCursorPosition);
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.highlightKnownOnly && !changes.highlightKnownOnly.firstChange) {
      // 开关切换后按新策略重渲染高亮
      setTimeout(() => this.processContent());
    }
    if (changes.variants) {
      const newVariants: CmdTextareaVariableGroup[] = [
        { label: '', items: [] },
      ];

      this.variants?.forEach((item) => {
        // 无分组信息类型放到默认组
        // 有分组信息类型追加新分组
        if (typeof item === 'string') {
          const variantsItem: CmdTextareaVariableItem = {
            label: item,
            value: item,
          };
          newVariants[0].items.push(variantsItem);
        } else if (
          typeof item === 'object' &&
          'label' in item &&
          'value' in item
        ) {
          newVariants[0].items.push(item);
        } else if (
          typeof item === 'object' &&
          'label' in item &&
          'items' in item
        ) {
          newVariants.push(item);
        } else {
        }
      });

      // 扁平列表统一按列表 DOM 渲染顺序生成（默认分组恒在最前、其后
      // 按显式分组出现顺序）：高亮 getCandidateBGColor 以分组下标+组内
      // 下标累加计数，与 selectedIndex 导航、insertSelectedTemplate 插入
      // 使用的 innerVariantsItems 必须同序，否则混排时高亮与插入错位。
      this.innerVariantsItems.length = 0;
      this.flatItemCoords.length = 0;
      newVariants.forEach((group, groupIndex) => {
        group.items?.forEach((subItem, itemIndex) => {
          this.innerVariantsItems.push(subItem);
          this.flatItemCoords.push([groupIndex, itemIndex]);
        });
      });
      const newVariantsHash = this.getVariantsHash(newVariants);
      // 只有变量值真正发生变化时，才重新设置innerVariants
      if (newVariantsHash !== this.preVariantsHash) {
        this.preVariantsHash = newVariantsHash;
        this.innerVariants = newVariants || [];
      }
    }
  }

  ngOnDestroy() {
    this.varTriggerSubscribe?.unsubscribe();
    this.inlineVarTriggerSubscribe?.unsubscribe();
    document.removeEventListener('selectionchange', this.processCursorPosition);
  }

  onContentChange() {
    let content = this.getEditorTextContent();
    if (content === '\n') {
      // 清空 <br>
      this.editor.nativeElement.innerHTML = '';
    }
    if (this.maxLength && this.getLength() > this.maxLength) {
      // 超长时一次性截断：先断开 Observer 防止 innerText 触发 processContent 卡死
      const truncated = this.getEditorTextContent().replace(/\n$/, '').slice(0, this.maxLength);
      this.editorObserver.disconnect();
      this.editor.nativeElement.innerText = truncated;
      const selection = window.getSelection();
      const newRange = document.createRange();
      newRange.selectNodeContents(this.editor.nativeElement);
      newRange.collapse(false);
      selection?.removeAllRanges();
      selection?.addRange(newRange);
      this.editorObserver.observe(this.editor.nativeElement, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }
    this.emit();
    this.updateSelection();
    this.scrollCursorToVisible();
  }

  getLength() {
    let content = this.getEditorTextContent();
    if (content === '\n') {
      return 0;
    }
    // 去除末尾换行符，与 emit() 输出值保持一致，避免计数偏差
    content = content.replace(/\n$/, '');
    return Math.max(content.length, 0);
  }


  handlePaste(event: ClipboardEvent) {
    event.preventDefault();
    // 标记结构性编辑（右键粘贴无 keydown，这里兜底设置）
    this.preAction = 'paste';

    // 获取剪贴板中的文本内容
    let clipboardContent = event.clipboardData?.getData('text/plain') || '';
    // 处理不同操作系统的换行标记
    clipboardContent = clipboardContent
      .replaceAll('\r\n', '\n')
      .replaceAll('\r', '\n');
    // 选区优先：非折叠选区（如 Ctrl+A 全选）按 [start, end) 在纯文本模型中
    // 整体替换；折叠光标按 offset 插入。此前基于 live Range 的
    // deleteContents/insertNode 在全选+粘贴时因选区边界节点被重渲染移出
    // 文档而失效，表现为"内容未被覆盖、粘贴文本追加在开头"
    const sel = this.getCleanSelection();
    const { text: current, offset } = this.getCleanTextAndOffset();

    // 计算替换起点/终点：有有效非折叠选区用选区边界，否则用光标 offset
    let start = offset;
    let end = offset;
    if (sel) {
      start = sel.start;
      end = sel.end;
    }

    // 超过最大长度截断（粘贴会替换选区内容，需补回被替换长度）
    if (this.maxLength) {
      const leaveLength = Math.max(
        this.maxLength - (current.replace(/\n$/, '').length - (end - start)),
        0,
      );
      if (clipboardContent.length > leaveLength) {
        clipboardContent = clipboardContent.slice(0, leaveLength);
      }
    }

    // 纯文本模型拼接 + 一次权威渲染，光标落在粘贴内容之后（与 FB-4 的
    // insertSelectedTemplate 修复同路径，避开 highlight 包裹导致的
    // Range 边界容器失效问题）
    const merged =
      current.slice(0, start) + clipboardContent + current.slice(end);
    this.renderFromText(merged, start + clipboardContent.length);
    this.emit();
  }

  onKeyDown(event: KeyboardEvent) {
    if (this.handleUndoShortcut(event)) {
      return;
    }
    // Ctrl/Cmd+X、Ctrl/Cmd+V 标记为结构性编辑（剪切/粘贴），撤销时单独成条
    const mod = event.ctrlKey || event.metaKey;
    if (mod && event.key.toLowerCase() === 'x') {
      this.preAction = 'cut';
    } else if (mod && event.key.toLowerCase() === 'v') {
      this.preAction = 'paste';
    } else {
      this.preAction = event.key;
    }
    if (
      ['ArrowUp', 'ArrowDown', 'Enter'].includes(event.key) &&
      this.showList
    ) {
      event.preventDefault();
      return;
    }

    // Tab 失焦修复：contenteditable 按 Tab 的默认行为是把焦点移到下一个
    // 可聚焦控件，导致编辑中断且 blur 顺带触发保存。这里统一拦截：
    // 变量列表打开时 Tab/Shift+Tab 当导航键（与方向键共用 moveSelection）；
    // 关闭时 Tab 插入缩进、Shift+Tab 反缩进（与主流编辑器方向语义一致）。
    // 带 Ctrl/Meta/Alt 修饰键时放行，不劫持浏览器/系统组合快捷键；
    // 若调用方把 CMDS 配置为包含 'Tab'（保留原有按键开列表行为），
    // 也放行到下方 CMDS 分支，避免破坏公开输入的既有语义。
    if (
      event.key === 'Tab' &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.altKey &&
      !this.CMDS?.includes('Tab')
    ) {
      event.preventDefault();
      if (this.showList) {
        this.moveSelection(event.shiftKey ? -1 : 1);
      } else if (event.shiftKey) {
        // 非折叠选区：对选区覆盖的每一行行首删最多两格空格（主流
        // 编辑器的行级反缩进语义）；折叠光标退回单行反缩进。
        if (!this.outdentSelection()) {
          this.outdentAtCursor();
        }
      } else {
        // 非折叠选区：对选区覆盖的每一行行首加两格缩进——不做替换，
        // 选中内容不丢失；折叠光标退回光标处插入两格缩进。
        if (!this.indentSelection()) {
          this.insertTextAtCursor('  ');
        }
      }
      return;
    }

    // WCAG 2.1.2（无键盘陷阱）：Tab/Shift+Tab 已被拦截，键盘用户需要一条
    // 确定性退出通路——Escape：变量列表打开时先关列表，再按时把焦点
    // 交还页面（blur 顺带触发既有的保存逻辑）。
    if (event.key === 'Escape') {
      if (this.showList) {
        event.preventDefault();
        this.showList = false;
      } else {
        this.editor?.nativeElement?.blur();
      }
      return;
    }

    // 达到 maxLength 后阻止可见字符输入（事前拦截，避免快速连续敲击突破限制）
    if (
      this.maxLength &&
      this.getLength() >= this.maxLength &&
      event.key.length === 1 &&
      !event.ctrlKey &&
      !event.metaKey &&
      !event.altKey
    ) {
      event.preventDefault();
      return;
    }

    if (this.CMDS.includes(event.key)) {
      this.showVarList();
      return;
    }
    if (event.key === 'Enter') {
      this.handleEnter(event);
    }
    if (event.key === 'Backspace' || event.key === 'Delete') {
      this.handleBackspaceOrDelete(event);
      // 手动 DOM 手术（preventDefault 过）不会触发 input 事件，需要显式
      // emit；原生删除由 input 事件驱动 onContentChange，不再无条件重复
      // emit，结构上避免一次删除产生"编辑前+编辑后"两条撤销记录
      if (event.defaultPrevented) {
        this.onContentChange();
      }
    }
    this.showList = false;
  }

  set showList(value: boolean) {
    if (this._showList === value) {
      return;
    }
    this._showList = value;
    if (!this._showList) {
      // 如果是关闭列表，需要处理内容
      this.processContent();
    }
  }

  get showList() {
    return this._showList;
  }

  /**
   * 为方便dom解析与重渲染，手动换行
   * @param event
   */
  handleEnter(event: KeyboardEvent) {
    if (this.showList) {
      return;
    }
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      event.preventDefault();
      // 直接插入 <br> 标签
      const br = document.createElement('br');
      // 插入新节点到光标位置
      if (selection.anchorNode.nodeName === 'BR') {
        selection.anchorNode.parentNode.insertBefore(br, selection.anchorNode);
      } else {
        range.insertNode(br);
      }
      range.setStartAfter(br);
    }
    this.onContentChange();
  }

  /**
   * 光标位于变量块整体后面，整体删除变量
   * @param event
   */
  handleBackspaceOrDelete(event: KeyboardEvent) {
    if (this.showList) {
      return;
    }
    const selection = window.getSelection();
    if (selection.rangeCount === 0 || !selection.isCollapsed) {
      return;
    }
    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer;
    if (
      startContainer.nodeType === Node.TEXT_NODE &&
      startContainer.textContent[range.startOffset - 1] === '\u200B'
    ) {
      // 零宽空格前面必定是变量块
      startContainer.previousSibling.remove();
      event.preventDefault();
    } else if (
      startContainer.parentElement.className === 'highlight' ||
      startContainer.parentElement.className === 'highlight-inline'

    ) {
      if( range.startOffset === startContainer.parentElement.innerText.length){
        startContainer.parentElement.remove();
        event.preventDefault();
      }else if(range.startOffset === 0){
        const preNode= startContainer.parentElement.previousSibling
        range.setStart(preNode,1);
        range.collapse(true);
        this.handleBackspaceOrDelete(event);
      }
    } else if (startContainer === this.editor.nativeElement) {
      const targetNode: Element | undefined = startContainer.childNodes[
        range.startOffset - 1
      ] as Element | undefined;
      if (!targetNode) {
        return;
      }
      if (targetNode.nodeType === Node.TEXT_NODE) {
        if (targetNode.textContent === '\u200B') {
          targetNode.previousSibling.remove();
          event.preventDefault();
        }
        return;
      }
      if (targetNode.classList.contains('highlight') || targetNode.classList.contains('highlight-inline')) {
        // 整块删除变量：不要在此 emit——onKeyDown 在
        // handleBackspaceOrDelete 之后统一调用 onContentChange，
        // 双 emit 会往撤销栈压入一条与当前状态相同的记录，首次
        // Ctrl+Z 变成无操作
        targetNode.remove();
        event.preventDefault();
      }
    }
  }

  /**
   * 检查光标位置
   * 如果光标不在编辑器内部，强制将光标置于编辑器最后
   */
  checkAndRestoreCursorPosition() {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      this.moveCursorToEnd();
      return;
    }

    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer;

    // 判断光标是否在编辑器内部
    let isInsideEditor = false;

    if (startContainer.nodeType === Node.TEXT_NODE) {
      // 文本节点 → 检查其父节点是否在编辑器内
      const parentElement = startContainer.parentElement;
      if (parentElement) {
        isInsideEditor = this.editor.nativeElement.contains(parentElement);
      }
    } else {
      // 元素节点（如 div、p、b 等）→ 直接判断是否在编辑器内
      isInsideEditor = this.editor.nativeElement.contains(startContainer);
    }

    // 只要光标不在编辑器内，就移动到末尾
    if (!isInsideEditor) {
      this.moveCursorToEnd();
    }
  }

  /**
   * 移动光标到编辑器最后
   */
  moveCursorToEnd() {
    const newRange = document.createRange();
    const editor = this.editor.nativeElement;

    const lastChild = editor.lastChild;

    // 已知最后一个节点一定是 <br>
    if (lastChild && lastChild.nodeName === 'BR') {
      // 把光标定位在 <br> 的前面（偏移 0）
      newRange.setStartBefore(lastChild);
    } else {
      // 备用逻辑：如果意外不是 <br>，就放在 editor 末尾
      newRange.setStart(editor, editor.childNodes.length);
    }

    // 收缩光标
    newRange.collapse(true);

    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(newRange);
    this.selection = selection;
    editor.scrollTop = editor.scrollHeight;
  }

  private showVarList() {
    this.updateSelection();
    if (!this.range) {
      return;
    }
   const myPromise = new Promise(resolve => {
     resolve(null);
   });
   myPromise.then(() => {
     let clientRect: DOMRect;
     if (this.range?.getClientRects().length) {
       clientRect = this.range.getClientRects()[0];
     } else {
       // 创建临时的 span 来标记位置
       const span = document.createElement('span');
       span.style.cssText = 'visibility: hidden;';
       span.innerHTML = '\u200B'; // 零宽空格

       this.range.insertNode(span);
       if (this.range?.getClientRects().length) {
         clientRect = this.range.getClientRects()[0];
       }
       //清理
       span.parentNode.removeChild(span);
     }
     if (clientRect) {
       let { left, top } = clientRect;

       if (left + LIST_WIDTH + PANAEL_PADDING > window.innerWidth - SAFE_OFFSET) {
         left -= LIST_WIDTH + LEFT_OFFSET;
         top -= LIST_ITEM_HEIGHT * (this.innerVariants.length > MAX_VIEW_ITEMS ? MAX_VIEW_ITEMS : this.innerVariants.length) + SAFE_OFFSET;
       }

       this.left = left + LEFT_OFFSET;
       this.top = top;

       this.selectedIndex = 0;
       this.showList = true;
     }
   });
  }

  @HostListener('window:keydown', ['$event'])
  public handleSelectVar(event: KeyboardEvent): void {
    let len: number = 0;
    this.innerVariants.forEach((group) => {
      len += group?.items?.length;
    });

    if (!['ArrowUp', 'ArrowDown', 'Enter'].includes(event.key) || !len) {
      return;
    }

    if (this.showList) {
      if (['ArrowUp', 'ArrowDown'].includes(event.key)) {
        this.moveSelection(event.key === 'ArrowUp' ? -1 : 1);
        event.stopPropagation();
      }

      if (event.key === 'Enter') {
        this.insertSelectedTemplate(
          this.innerVariantsItems[this.selectedIndex],
        );
      }
    }
  }

  /**
   * 变量列表环形导航：dir=1 下移、dir=-1 上移。
   * 供 handleSelectVar 的方向键与 onKeyDown 的 Tab 导航共用，
   * 避免环形索引逻辑重复实现。
   */
  private moveSelection(dir: 1 | -1): void {
    const total = this.innerVariants.reduce(
      (n, g) => n + (g?.items?.length ?? 0),
      0,
    );
    if (!total) {
      return;
    }
    this.selectedIndex =
      dir === 1
        ? (this.selectedIndex + 1) % total
        : (this.selectedIndex - 1 + total) % total;
    this.scrollToVisibleArea();
  }

  public getCandidateBGColor(groupIndex: number, itemIndex: number): string {
    let cnt = 0;
    for (let index = 0; index < groupIndex; index++) {
      cnt += this.innerVariants[index].items.length;
    }
    cnt += itemIndex;
    return cnt === this.selectedIndex ? '#f5f5f5' : '';
  }

  updateSelection() {
    const selection = window.getSelection() as Selection;
    this.selection = selection;
  }

  insertSelectedTemplate(item: CmdTextareaVariableItem) {
    const editor = this.editor?.nativeElement;
    if (!editor || !item) {
      return;
    }
    // 标记结构性编辑（变量插入），撤销时单独成条
    this.preAction = 'template';
    // FB-4 修复：放弃 range/文本节点手术，改为基于字符偏移的纯文本模型插入。
    // 旧实现（对 startNode.textContent 做 slice、deleteContents+insertNode）在光标
    // 落在已 highlight 包裹的 {{var}} 块上/旁时，startContainer 会是元素节点而非干净
    // 文本节点，textContent 切片会把整棵子树拍平，拼出坏模板（占位符落到引号外、逗号
    // 重复），保存后过不了运行时 literal_eval 门 → body 静默丢失。
    let { text, offset } = this.getCleanTextAndOffset();
    if (!this.isTriggerClick) {
      // 删除打开变量列表的触发字符（如 '{' 或 '/'）
      const removeAt = Math.max(offset - 1, 0);
      text = text.slice(0, removeAt) + text.slice(offset);
      offset = removeAt;
    }
    const token =
      this.insertMode === 'triple'
        ? `{{{${item.value}}}}`
        : `{{${item.value}}}`;
    text = text.slice(0, offset) + token + text.slice(offset);
    // 直接置内部标志关闭列表，绕过 setter 避免二次 processContent；
    // renderFromText 是唯一权威渲染，随后 emit 触发 CD 隐藏列表。
    this._showList = false;
    this.isTriggerClick = false;
    this.renderFromText(text, offset + token.length);
    this.emit();
  }

  /**
   * 取非折叠选区在纯文本模型中的文本与起止偏移；折叠或选区不在编辑器
   * 内时返回 null。
   * 起止偏移不能用 Range.toString()：它只拼接 Text 节点字符，<br> 不计
   * 换行，跨行选区会少算；须与 saveCursorPosition 同口径（文本长度 +
   * <br> 计 1）分别计算起止原始偏移，再按 innerText 剔除零宽字符换算。
   */
  private getCleanSelection(): {
    text: string;
    start: number;
    end: number;
  } | null {
    const editor = this.editor?.nativeElement;
    if (!editor) {
      return null;
    }
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) {
      return null;
    }
    const range = selection.getRangeAt(0);
    const inside =
      range.commonAncestorContainer === editor ||
      editor.contains(range.commonAncestorContainer);
    if (range.collapsed || !inside) {
      return null;
    }
    const { text } = this.getCleanTextAndOffset();
    const rawText = editor.innerText;
    const rawStart = this.getRawOffsetBefore(
      editor,
      range.startContainer,
      range.startOffset,
    );
    const rawEnd = this.getRawOffsetBefore(
      editor,
      range.endContainer,
      range.endOffset,
    );
    if (rawStart < 0 || rawEnd < rawStart) {
      return null;
    }
    const from = Math.min(rawStart, rawText.length);
    const to = Math.min(rawEnd, rawText.length);
    let cleanStart = 0;
    let cleanEnd = 0;
    for (let i = 0; i < to; i++) {
      if (rawText[i] !== '\u200B') {
        cleanEnd++;
        if (i < from) {
          cleanStart++;
        }
      }
    }
    return { text, start: cleanStart, end: cleanEnd };
  }

  /**
   * 计算纯文本中选区 [start, end) 覆盖的各行行首偏移（升序）。
   * 行覆盖规则与主流编辑器一致：起点所在行始终计入；终点恰在下一行
   * 行首时该行不计入（避免“选到行首”多操作一行）。
   */
  private getCoveredLineStarts(
    text: string,
    start: number,
    end: number,
  ): number[] {
    const starts: number[] = [0];
    for (let i = 0; i < text.length; i++) {
      if (text[i] === '\n') {
        starts.push(i + 1);
      }
    }
    let s = 0;
    let e = 0;
    for (let i = 0; i < starts.length; i++) {
      if (starts[i] <= start) {
        s = i;
      }
      if (starts[i] <= end) {
        e = i;
      }
    }
    if (e > s && starts[e] === end) {
      e--;
    }
    const covered: number[] = [];
    for (let i = s; i <= e; i++) {
      covered.push(starts[i]);
    }
    return covered;
  }

  /**
   * 非折叠选区的行级缩进（Tab）：对选区覆盖的每一行行首插入两格空格，
   * 选中文本不丢失，选区随缩进整体右移并保留。
   * 超出 maxLength 时不做任何变更，选区原样保留。
   * 返回 false 表示当前无有效选区（调用方退回光标处插入）。
   */
  private indentSelection(): boolean {
    const sel = this.getCleanSelection();
    if (!sel) {
      return false;
    }
    const lines = this.getCoveredLineStarts(sel.text, sel.start, sel.end);
    if (!lines.length) {
      return false;
    }
    // 从最后一行往前插入，行首偏移不受前面插入的影响
    let merged = sel.text;
    for (let i = lines.length - 1; i >= 0; i--) {
      merged = merged.slice(0, lines[i]) + '  ' + merged.slice(lines[i]);
    }
    if (this.maxLength && merged.replace(/\n$/, '').length > this.maxLength) {
      return true;
    }
    // 起点所在行行首 ≤ 起点，起点右移两格；每个行首都 < 终点，
    // 终点右移 2 × 行数
    this.renderFromTextWithSelection(
      merged,
      sel.start + 2,
      sel.end + 2 * lines.length,
    );
    this.emit();
    return true;
  }

  /**
   * 非折叠选区的行级反缩进（Shift+Tab）：对选区覆盖的每一行行首删除
   * 最多两格空格（仅删空格，不碰其它字符），选区随删除整体左移并保留。
   * 返回 false 表示当前无有效选区（调用方退回单行反缩进）。
   */
  private outdentSelection(): boolean {
    const sel = this.getCleanSelection();
    if (!sel) {
      return false;
    }
    const lines = this.getCoveredLineStarts(sel.text, sel.start, sel.end);
    let merged = sel.text;
    let totalCut = 0;
    let startLineCut = 0;
    for (let i = lines.length - 1; i >= 0; i--) {
      let cut = 0;
      while (cut < 2 && merged[lines[i] + cut] === ' ') {
        cut++;
      }
      if (!cut) {
        continue;
      }
      if (i === 0) {
        startLineCut = cut;
      }
      merged = merged.slice(0, lines[i]) + merged.slice(lines[i] + cut);
      totalCut += cut;
    }
    if (!totalCut) {
      return true;
    }
    // 所有删除点都在选区之前或之内：起点扣除其所在行的删除量（若落入
    // 被删空格内则收敛到行首），终点扣除全部删除量
    const newStart = Math.max(lines[0], sel.start - startLineCut);
    this.renderFromTextWithSelection(merged, newStart, sel.end - totalCut);
    this.emit();
    return true;
  }

  private insertTextAtCursor(text: string): void {
    if (!text) {
      return;
    }
    const editor = this.editor?.nativeElement;
    if (!editor) {
      return;
    }
    // 前置条件：折叠光标（非折叠选区的 Tab 已在 onKeyDown 分派为
    // indentSelection 行级缩进，不走此处的替换语义，选中内容不丢失）。
    // 在纯文本模型中拼接后一次渲染，超出 maxLength 时静默不插入，
    // 与可见字符拦截口径一致。
    const { text: current, offset } = this.getCleanTextAndOffset();
    const merged = current.slice(0, offset) + text + current.slice(offset);
    if (this.maxLength && merged.replace(/\n$/, '').length > this.maxLength) {
      return;
    }
    this.renderFromText(merged, offset + text.length);
    this.emit();
  }

  /**
   * 折叠光标的单行反缩进（Shift+Tab）：删除光标所在行行首最多两个
   * 空格。非折叠选区的多行反缩进由 outdentSelection 承接，不走此处。
   * 与 insertTextAtCursor 同一套纯文本模型：独立统计该行行首的
   * 前导空格数——光标恰在行首（点击行首/按 Home）时也允许反缩进；
   * 仅当光标落在被删空格范围内时收敛到行首，其余位置左移 cut 格。
   */
  private outdentAtCursor(): void {
    const { text, offset } = this.getCleanTextAndOffset();
    const lineStart = text.lastIndexOf('\n', Math.max(offset - 1, 0)) + 1;
    let cut = 0;
    while (cut < 2 && text[lineStart + cut] === ' ') {
      cut++;
    }
    if (!cut) {
      return;
    }
    const merged = text.slice(0, lineStart) + text.slice(lineStart + cut);
    const rel = offset - lineStart;
    const newOffset = rel <= cut ? lineStart : offset - cut;
    this.renderFromText(merged, newOffset);
    this.emit();
  }

  clickOutsideOfList() {
    this.showList = false;
    this.isTriggerClick = false;
  }

  onCompositionStart(event: CompositionEvent) {
    this.inInput = true;
    this.compositionstart.emit(event);
  }

  onCompositionEnd(event: CompositionEvent) {
    this.inInput = false;
    this.compositionend.emit(event);
  }

  onBlur() {
    this.blur.emit();
  }

  /**
   * 取编辑器纯文本（剥零宽字符）及光标在其内的字符偏移。
   * saveCursorPosition 返回的原始偏移把 \u200B 计入、<br> 记 1，与 innerText 前缀
   * 一一对应；这里把落在 \u200B 上的计数扣除，换算成"剥零宽后 innerText"的偏移，
   * 供 insertSelectedTemplate 做纯文本字符串拼接。
   * 光标不在编辑器内时（saveCursorPosition 不回调）回退到文本末尾。
   */
  private getCleanTextAndOffset(): { text: string; offset: number } {
    const editor = this.editor?.nativeElement;
    if (!editor) {
      return { text: '', offset: 0 };
    }
    const compute = (): number => {
      let raw = -1;
      this.saveCursorPosition(editor, (o: number) => {
        raw = o;
      });
      return raw;
    };
    let rawOffset = compute();
    if (rawOffset < 0) {
      this.moveCursorToEnd();
      rawOffset = compute();
    }
    const rawText = editor.innerText;
    const text = rawText.replaceAll('\u200B', '');
    if (rawOffset < 0) {
      // 极端兜底：仍拿不到光标，置于纯文本末尾（去掉结尾换行）
      return { text, offset: text.replace(/\n$/, '').length };
    }
    let offset = 0;
    const limit = Math.min(rawOffset, rawText.length);
    for (let i = 0; i < limit; i++) {
      if (rawText[i] !== '\u200B') {
        offset++;
      }
    }
    return { text, offset };
  }

  /** 判断 {{var}} / {{{var}}} 是否落在已声明 variants 中 */
  private isKnownVariantToken(token: string): boolean {
    let inner = token;
    if (inner.startsWith('{{{') && inner.endsWith('}}}')) {
      inner = inner.slice(3, -3);
    } else if (inner.startsWith('{{') && inner.endsWith('}}')) {
      inner = inner.slice(2, -2);
    }
    const name = inner.trim();
    return this.innerVariantsItems.some((v) => v.value === name);
  }

  /** 将匹配到的花括号包成高亮；highlightKnownOnly 时未知变量保持字面量 */
  private wrapBraceToken(triple: string | undefined, dbl: string | undefined): string {
    const token = triple || dbl;
    if (!token) {
      return '';
    }
    if (this.highlightKnownOnly && !this.isKnownVariantToken(token)) {
      return token;
    }
    if (triple) {
      return `<span class="highlight-inline">${triple}</span>\u200B`;
    }
    return `<span class="highlight">${dbl}</span>\u200B`;
  }

  /**
   * 以纯文本为唯一数据源重渲染整个编辑区，遵循 processContent 的渲染约定：
   * escapeHTML → {{var}} 包 highlight span 并尾随 \u200B → \n 转 <br> → 末尾补 <br>。
   * 渲染后把光标恢复到 cursorOffset（纯文本字符偏移），不依赖 DOM 现状，
   * 因此规避了 processContent 里那套针对光标读回的脆弱启发式补偿。
   */
  private renderFromText(plainText: string, cursorOffset: number): void {
    const editor = this.editor?.nativeElement;
    if (!editor) {
      return;
    }
    this.editorObserver.disconnect();

    let processed = this.escapeHTML(plainText);
    const regex2 = new RegExp(
      `(\\{\\{\\{[^{}\\n\\r]+?\\}\\}\\})|({{[^{}\\n\\r]+?}})`,
      'gi',
    );
    processed = processed.replace(regex2, (match, triple, dbl) =>
      this.wrapBraceToken(triple, dbl),
    );
    processed = processed.replace(/\n/g, '<br>');
    if (!processed.endsWith('<br>')) {
      processed = `${processed}<br>`;
    }
    editor.innerHTML = processed;

    // restoreCursorPosition 的偏移空间 = 纯文本字符 + 每个 highlight 尾随的 1 个 \u200B；
    // 光标前的完整变量块数即需补的零宽字符数，换算成原始偏移。
    const before = plainText.slice(0, cursorOffset);
    const braceMatches =
      before.match(/\{\{\{[^{}\n\r]+?\}\}\}|{{[^{}\n\r]+?}}/g) || [];
    const zwCount = this.highlightKnownOnly
      ? braceMatches.filter((m) => this.isKnownVariantToken(m)).length
      : braceMatches.length;
    this.reRenderTimes++;
    this.restoreCursorPosition(editor, cursorOffset + zwCount);
    this.updateSelection();
    this.scrollCursorToVisible();

    this.editorObserver.observe(editor, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  /**
   * 渲染纯文本并把 [selStart, selEnd) 恢复为选区（而非折叠光标），
   * 供多行缩进/反缩进保留用户选区。
   * 渲染与零宽字符换算复用 renderFromText 同一套口径；渲染后光标已在
   * selStart，这里再把终点定位到 selEnd 展开成选区。终点定位失败时
   * （如恰好落在 <br> 边界上）退化为折叠光标，可接受。
   */
  private renderFromTextWithSelection(
    plainText: string,
    selStart: number,
    selEnd: number,
  ): void {
    this.renderFromText(plainText, selStart);
    if (selEnd <= selStart) {
      // 反缩进把覆盖空格全删后选区可能坍缩，保持折叠光标即可
      return;
    }
    const editor = this.editor?.nativeElement;
    const selection = window.getSelection();
    if (!editor || !selection) {
      return;
    }
    // 与 renderFromText 相同的零宽换算：光标前每个（已知）变量块补 1
    const toRawOffset = (off: number): number => {
      const before = plainText.slice(0, off);
      const matches =
        before.match(/\{\{\{[^{}\n\r]+?\}\}\}|{{[^{}\n\r]+?}}/g) || [];
      const zwCount = this.highlightKnownOnly
        ? matches.filter((m) => this.isKnownVariantToken(m)).length
        : matches.length;
      return off + zwCount;
    };
    const rawStart = toRawOffset(selStart);
    const rawEnd = toRawOffset(selEnd);
    // 与 restoreCursorPosition 同口径遍历：文本节点按长度计数、<br> 计 1
    const walker = document.createTreeWalker(
      editor,
      NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
      null,
    );
    let currentOffset = 0;
    let startPt: { node: Node; offset: number } | null = null;
    let endPt: { node: Node; offset: number } | null = null;
    let node: Node;
    while ((node = walker.nextNode()) && !(startPt && endPt)) {
      if (node.nodeType === Node.TEXT_NODE) {
        const textLen = (node as Text).length;
        if (
          !startPt &&
          rawStart >= currentOffset &&
          rawStart < currentOffset + textLen
        ) {
          startPt = { node, offset: rawStart - currentOffset };
        }
        if (
          !endPt &&
          rawEnd >= currentOffset &&
          rawEnd < currentOffset + textLen
        ) {
          endPt = { node, offset: rawEnd - currentOffset };
        }
        currentOffset += textLen;
      } else if (
        node.nodeType === Node.ELEMENT_NODE &&
        node.nodeName === 'BR'
      ) {
        currentOffset++;
      }
    }
    if (startPt && endPt) {
      const range = document.createRange();
      range.setStart(startPt.node, startPt.offset);
      range.setEnd(endPt.node, endPt.offset);
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }

  private getEditorTextContent() {
    if (this.editor) {
      return this.editor.nativeElement.innerText.replaceAll('\u200B','');
    }
    return '\n';
  }

  private emit(): void {
    this.pushUndo();
    // innerText 只读一次，复用给 onChange 与 syncLastState，避免每次按键
    // 的热点路径重复读取。必须读原始 innerText（含变量块后的 \u200B
    // 零宽字符）：syncLastState 的光标偏移换算与 saveCursorPosition 的
    // DOM 文本计数同口径，若传入去零宽后的文本，偏移会按去零宽下标
    // 错算，多出光标前的变量块数
    const rawText = this.editor?.nativeElement.innerText ?? '\n';
    this.onChange(rawText.replaceAll('\u200B', '').replace(/\n$/, ''));
    this.onTouched();
    this.syncLastState(rawText);
  }

  /**
   * 撤销/重做快捷键拦截：Ctrl/Cmd+Z 撤销，Ctrl/Cmd+Shift+Z、Ctrl/Cmd+Y 重做。
   * 原生撤销栈已被 innerHTML 整体重写摧毁，必须接管；输入法组合期间不劫持
   * （交给输入法自行处理）。返回 true 表示已消费该按键。
   */
  private handleUndoShortcut(event: KeyboardEvent): boolean {
    if (this.inInput || !(event.ctrlKey || event.metaKey) || event.altKey) {
      return false;
    }
    const key = event.key.toLowerCase();
    if (key === 'z' && !event.shiftKey) {
      event.preventDefault();
      this.undo();
      return true;
    }
    if (key === 'y' || (key === 'z' && event.shiftKey)) {
      event.preventDefault();
      this.redo();
      return true;
    }
    return false;
  }

  /** 撤销：弹出编辑前快照并渲染，当前状态压入重做栈 */
  private undo(): void {
    const snap = this.undoStack.pop();
    if (!snap) {
      return;
    }
    this.redoStack.push({ ...this.lastState });
    // 重置连续输入合并窗口：撤销后的下一次编辑必须独立成条，
    // 否则会被合并进撤销前的输入串，且重做会覆盖新输入
    this.lastPushTime = 0;
    // 直接置内部标志关闭变量列表，绕过 setter 避免二次 processContent
    this._showList = false;
    this.applyingHistory = true;
    try {
      this.renderFromText(snap.text, snap.offset);
      this.emit();
    } finally {
      this.applyingHistory = false;
    }
  }

  /** 重做：弹出重做快照并渲染，当前状态压回撤销栈 */
  private redo(): void {
    const snap = this.redoStack.pop();
    if (!snap) {
      return;
    }
    this.undoStack.push({ ...this.lastState });
    // 重置连续输入合并窗口：重做后的下一次编辑必须独立成条，
    // 否则会被合并进重做前的输入串，再次撤销会一次性吞掉过多内容
    this.lastPushTime = 0;
    this._showList = false;
    this.applyingHistory = true;
    try {
      this.renderFromText(snap.text, snap.offset);
      this.emit();
    } finally {
      this.applyingHistory = false;
    }
  }

  /**
   * 把"编辑前快照"（lastState）压入撤销栈。
   * 栈顶已记录该状态（文本与光标偏移均一致）时跳过（同一事务的
   * 重复 emit，如删除键的 keydown 预处理 + input 事件双触发；
   * 偏移也须一致，否则纯光标移动后的首次撤销无法回到真实编辑
   * 前位置）；连续普通输入（含输入法组合中间态）在时间窗内合并
   * 为一条；结构性编辑单独成条。任何新编辑都会清空重做栈。
   */
  private pushUndo(): void {
    if (this.applyingHistory) {
      return;
    }
    // 任何新编辑都使重做栈失效——必须放在合并/去重的提前返回之前：
    // 否则"撤销后立即输入（该条被合并跳过入栈）→ 重做"会用旧内容
    // 覆盖掉刚输入的新内容
    this.redoStack = [];
    const top = this.undoStack[this.undoStack.length - 1];
    if (
      top &&
      top.text === this.lastState.text &&
      top.offset === this.lastState.offset
    ) {
      this.lastPushTime = Date.now();
      return;
    }
    const now = Date.now();
    const structural = STRUCTURAL_KEYS.has(this.preAction);
    const typingLike =
      !structural &&
      (this.inInput || this.preAction === 'Process' || this.preAction?.length === 1);
    if (typingLike && now - this.lastPushTime < UNDO_COALESCE_MS) {
      this.lastPushTime = now;
      return;
    }
    this.undoStack.push({ ...this.lastState });
    if (this.undoStack.length > UNDO_LIMIT) {
      this.undoStack.shift();
    }
    // 结构性编辑单独成条：入栈后清零合并窗口，紧随其后的普通输入
    // 独立成条，避免一次 Ctrl+Z 连结构编辑带后续输入一起回退；
    // 普通输入入栈后维持窗口，继续合并后续连续输入
    this.lastPushTime = structural ? 0 : now;
  }

  /**
   * 只读同步当前编辑器纯文本与光标偏移到 lastState，作为下一次编辑
   * 事务的"编辑前快照"。不做任何光标/DOM 副作用；光标不在编辑器内
   * 时（理论上不会发生）偏移退化为文本末尾。文本未变时（如删除键的
   * keydown 预处理、末尾回车）跳过克隆选区的测量开销，保留上次偏移。
   */
  private syncLastState(rawText?: string): void {
    const editor = this.editor?.nativeElement;
    if (!editor) {
      return;
    }
    // 复用 emit 已读取的原始 innerText（含 \u200B），避免热点路径（每次
    // 按键）重复读取；偏移换算与 saveCursorPosition 的 DOM 文本计数同口径
    const innerText = rawText ?? editor.innerText;
    const text = innerText.replaceAll('\u200B', '').replace(/\n$/, '');
    if (!this.applyingHistory && text === this.lastState.text) {
      return;
    }
    let raw = -1;
    this.saveCursorPosition(editor, (o: number) => {
      raw = o;
    });
    let offset = text.length;
    if (raw >= 0) {
      offset = 0;
      const limit = Math.min(raw, innerText.length);
      for (let i = 0; i < limit; i++) {
        if (innerText[i] !== '\u200B') {
          offset++;
        }
      }
      offset = Math.min(offset, text.length);
    }
    this.lastState = { text, offset };
  }

  /**
   * selectionchange 光标追踪：纯光标移动（无内容变化）时把换算后的
   * 偏移同步到 lastState，使下一次编辑的撤销快照记录真实编辑前光标
   * 位置。文本已变化（编辑尚未 emit）时跳过，交由 syncLastState 全量
   * 同步，避免快照出现"旧文本+新光标"的错配。
   */
  private trackCursorOffset(editor: HTMLElement, raw: number): void {
    if (this.applyingHistory || raw < 0) {
      return;
    }
    const rawText = editor.innerText;
    const text = rawText.replaceAll('\u200B', '').replace(/\n$/, '');
    if (text !== this.lastState.text) {
      return;
    }
    let offset = 0;
    const limit = Math.min(raw, rawText.length);
    for (let i = 0; i < limit; i++) {
      if (rawText[i] !== '\u200B') {
        offset++;
      }
    }
    this.lastState.offset = Math.min(offset, text.length);
  }

  private scrollToVisibleArea(): void {
    const listWrapper = this.list?.nativeElement;
    if (!listWrapper) {
      return;
    }

    // innerVariantsItems 已统一按列表 DOM 渲染顺序（默认分组在前）扁平化，
    // 与高亮 getCandidateBGColor、插入 insertSelectedTemplate 共用同一套
    // 索引模型；这里仍用 [分组下标, 组内下标] 坐标定位选中项，
    // 不依赖 querySelectorAll 的全局平铺顺序。
    const coords = this.flatItemCoords[this.selectedIndex];
    const groupEl = coords
      ? (listWrapper.querySelectorAll<HTMLElement>('.group')[coords[0]] ??
        null)
      : null;
    const selectedElement = coords
      ? (groupEl?.querySelectorAll<HTMLElement>('.item')[coords[1]] ?? null)
      : null;
    if (!selectedElement) {
      return;
    }

    const listWrapperRect = listWrapper.getBoundingClientRect();
    const selectedRect = selectedElement.getBoundingClientRect();

    if (
      selectedRect.top < listWrapperRect.top ||
      selectedRect.bottom > listWrapperRect.bottom
    ) {
      listWrapper.scrollTop = selectedElement.offsetTop;
    }
  }

  /**
   * 获取变量的哈希值,这里简单拼接即可，复杂算法会导致卡顿
   * @param variants
   * @private
   */
  private getVariantsHash(variants: Array<CmdTextareaVariableGroup>): string {
    return variants
      .map((group) => {
        const itemsHash = group?.items
          ?.map((item) => {
            return `${item.label}${item.value}`;
          })
          .join('-');
        return `${group.label}:${itemsHash}`;
      })
      .join('|');
  }

  /**
   * 内容渲染
   * 处理编辑区内容，为 特定模式串：{{var}} 添加标签背景
   */
  processContent() {
    if (this.showList) {
      return;
    }
    this.editorObserver.disconnect();

    // A. 保存当前光标位置（字符偏移量）
    let charOffset = 0;
    this.saveCursorPosition(this.editor.nativeElement, (offset: number) => {
      charOffset = offset;
    });

    const regex1 = new RegExp(`\n`, 'gi');
    const regex2 = new RegExp(
      `(\\{\\{\\{[^{}\\n\\r]+?\\}\\}\\})|({{[^{}\\n\\r]+?}})`,
      'gi',
    );
    const regex3 = new RegExp(`(\\{\\{\\{[^}]*\\}\\}\\}|{{[^}]*}})$`);
    let processedText = this.editor.nativeElement.innerText;
    const subProcessedText=processedText.substring(0, charOffset);
    if (regex3.test(subProcessedText)) {
      // 如果光标在 {{var}} 或 {{{var}}} 后面，将charOffset+1
      charOffset++;
    }
    if(subProcessedText.length>=1&&subProcessedText[0]==='\u200B'){
      // 最前面是零宽字符
      charOffset--;
    }
    if(subProcessedText.length>=2&&subProcessedText.endsWith('\u200B\u200B')){
      // 最后连续两个零宽字符
      charOffset--;
    }
    processedText = processedText.replaceAll('\u200B', '');
    processedText = this.escapeHTML(processedText);
    processedText = processedText.replace(regex2, (match, triple, dbl) =>
      this.wrapBraceToken(triple, dbl),
    );
    processedText = processedText.replace(regex1, '<br>');
    if (!processedText.endsWith('<br>')) {
      processedText = `${processedText}<br>`;
    }

    if (this.editor.nativeElement.innerHTML !== processedText) {
      // C. 重写 DOM
      this.editor.nativeElement.innerHTML = processedText;
      // D. 恢复光标（基于字符偏移量）
      if (this.reRenderTimes !== 0) {
        // 首次渲染（初始化）不需要恢复光标位置
        this.restoreCursorPosition(this.editor.nativeElement, charOffset);
        this.updateSelection();
        this.scrollCursorToVisible();
      }
    }

    // E. 重新连接 observer
    this.editorObserver.observe(this.editor.nativeElement, {
      childList: true,
      subtree: true,
      characterData: true,
    });
    // 更新重渲染次数
    this.reRenderTimes++;
  }

  /**
   * 保存光标在编辑区内的字符数数偏移
   */
  saveCursorPosition(containerEl: HTMLElement, callback: CallableFunction) {
    const selection = window.getSelection();
    if (selection.rangeCount === 0) {
      return;
    }
    const range = selection.getRangeAt(0);

    if (!containerEl.contains(range.startContainer)) {
      return;
    }
    // 获取光标前所有文本的内容
    const preCaretRange = range.cloneRange();
    preCaretRange.selectNodeContents(containerEl);
    preCaretRange.setEnd(range.startContainer, range.startOffset);

    const tempDiv = document.createElement('div');
    const fragment = preCaretRange.cloneContents();
    tempDiv.appendChild(fragment);
    const treeWalker = document.createTreeWalker(
      tempDiv,
      NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
      null,
    );
    let node: Node;
    let offset = 0;
    while ((node = treeWalker.nextNode())) {
      if (node.nodeType === Node.TEXT_NODE) {
        offset += node.textContent.length;
      } else if (
        node.nodeType === Node.ELEMENT_NODE &&
        node.nodeName === 'BR'
      ) {
        offset++;
      }
    }
    callback(offset);
  }

  /**
   * 计算编辑器内某边界点 (node, offset) 之前的字符偏移，与
   * saveCursorPosition 同口径：文本节点按 textContent 长度计数，
   * <br> 计 1（innerText 中对应一个换行符）。
   * 边界点不在编辑器内时返回 -1。
   */
  private getRawOffsetBefore(
    containerEl: HTMLElement,
    node: Node,
    offset: number,
  ): number {
    if (node !== containerEl && !containerEl.contains(node)) {
      return -1;
    }
    const preCaretRange = document.createRange();
    preCaretRange.selectNodeContents(containerEl);
    preCaretRange.setEnd(node, offset);
    const tempDiv = document.createElement('div');
    tempDiv.appendChild(preCaretRange.cloneContents());
    const treeWalker = document.createTreeWalker(
      tempDiv,
      NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
      null,
    );
    let cur: Node;
    let cnt = 0;
    while ((cur = treeWalker.nextNode())) {
      if (cur.nodeType === Node.TEXT_NODE) {
        cnt += cur.textContent.length;
      } else if (
        cur.nodeType === Node.ELEMENT_NODE &&
        cur.nodeName === 'BR'
      ) {
        cnt++;
      }
    }
    return cnt;
  }

  /**
   * 根据字符数偏移，恢复光标的位置
   * 编辑器重渲染后，会丢失光标位置
   */
  restoreCursorPosition(containerEl: HTMLElement, charOffset: number) {
    const selection = window.getSelection();
    if (!selection) {
      return;
    }
    try {
      let currentOffset = 0;
      const walker = document.createTreeWalker(
        containerEl,
        NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT,
        null,
      );

      let node: Node;
      while ((node = walker.nextNode())) {
        // 处理文本节点
        if (node.nodeType === Node.TEXT_NODE) {
          const textLen = (node as Text).length;

          // 检查目标偏移量是否在这个文本节点内
          if (
            charOffset >= currentOffset &&
            charOffset < currentOffset + textLen
          ) {
            const range = document.createRange();
            range.setStart(node, charOffset - currentOffset);
            range.collapse(true);

            selection.removeAllRanges();
            selection.addRange(range);

            // 平滑滚动到光标位置
            containerEl.scrollIntoView({
              behavior: 'smooth',
              block: 'nearest',
            });
            return;
          }

          currentOffset += textLen;
        }
        // br标签
        else if (
          node.nodeType === Node.ELEMENT_NODE &&
          node.nodeName === 'BR'
        ) {
          if (charOffset === currentOffset) {
            // 光标在换行符之前，将光标放在换行符前
            const range = document.createRange();
            range.setStartBefore(node);
            range.collapse(true);

            selection.removeAllRanges();
            selection.addRange(range);

            // 平滑滚动到光标位置
            containerEl.scrollIntoView({
              behavior: 'smooth',
              block: 'nearest',
            });
            return;
          } else if (charOffset === currentOffset + 1) {
            // 光标在换行符之后，将光标放在换行符后
            const range = document.createRange();
            range.setStartAfter(node);
            range.collapse(true);

            selection.removeAllRanges();
            selection.addRange(range);

            // 平滑滚动到光标位置
            containerEl.scrollIntoView({
              behavior: 'smooth',
              block: 'nearest',
            });
            return;
          } else {
            currentOffset++;
          }
        }
      }

      // 如果偏移量超出文本总长度，将光标放在最后
      try {
        const lastText = containerEl.lastChild;
        if (lastText && lastText.nodeType === Node.TEXT_NODE) {
          const range = document.createRange();
          range.setStart(lastText, (lastText as Text).length);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        } else if (containerEl.lastChild) {
          // 如果最后不是文本节点，放在最后一个元素后
          const range = document.createRange();
          range.setStartAfter(containerEl.lastChild);
          range.collapse(true);
          selection.removeAllRanges();
          selection.addRange(range);
        }
      } catch (e) {
        // 放置光标在最后位置失败
      }
    } catch (e) {
      // 恢复光标失败
      // 最终回退：将光标放在容器末尾
      try {
        const range = document.createRange();
        range.selectNodeContents(containerEl);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
      } catch (fallbackError) {
        // 恢复光标最终回退失败
      }
    }
  }

  /**
   * 将编辑器滚动到光标可见位置
   * 确保光标始终在用户可视区域内，提供最佳的用户体验
   */
  private scrollCursorToVisible(): void {
    if (!this.selection || !this.range || !this.editor?.nativeElement) {
      return;
    }

    const editorElement = this.editor.nativeElement;

    // 创建临时元素来获取精确的光标位置
    const tempElement = document.createElement('span');
    tempElement.style.visibility = 'hidden';
    tempElement.innerHTML = '\u200B'; // 零宽空格

    // 将临时元素插入到光标位置
    this.range.insertNode(tempElement);

    // 获取临时元素的位置信息
    const tempRect = tempElement.getBoundingClientRect();
    const editorRect = editorElement.getBoundingClientRect();

    // 计算临时元素相对于编辑器的位置
    const relativeTop = tempRect.top - editorRect.top;
    const relativeBottom = tempRect.bottom - editorRect.top;

    // 获取编辑器的滚动信息
    const scrollTop = editorElement.scrollTop;
    const scrollHeight = editorElement.scrollHeight;
    const clientHeight = editorElement.clientHeight;

    // 计算可视区域边界（添加边距，避免紧贴边缘）
    const margin = 20; // 光标与视区边缘的最小距离
    const viewportTop = margin;
    const viewportBottom = clientHeight - margin;

    // 判断是否需要滚动
    let needsScroll = false;
    let newScrollTop = scrollTop;

    // 如果光标顶部低于可视区域底部
    if (relativeBottom > viewportBottom) {
      newScrollTop = scrollTop + (relativeBottom - viewportBottom);
      needsScroll = true;
    }
    // 如果光标底部高于可视区域顶部
    else if (relativeTop < viewportTop) {
      newScrollTop = scrollTop + (relativeTop - viewportTop);
      needsScroll = true;
    }

    // 应用新的滚动位置，但限制在合理范围内
    if (needsScroll) {
      // 确保滚动位置不超出边界
      newScrollTop = Math.max(
        0,
        Math.min(newScrollTop, scrollHeight - clientHeight),
      );

      // 不要使用平滑滚动
      editorElement.scrollTo({
        top: newScrollTop,
      });
    }

    // 移除临时元素
    if (tempElement.parentNode) {
      tempElement.parentNode.removeChild(tempElement);
    }
  }

  /**
   * 特殊处理光标位置
   * 当光标变量块{{var}}的后面时，根据上一次按键操作设置，强制光标位置
   */
  private processCursorPosition = () => {
    if (!this.editor?.nativeElement?.contains(document.activeElement)) {
      return;
    }
    const selection = window.getSelection();
    if (selection.rangeCount === 0) return;

    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer;

    // 获取光标所在位置的文本内容
    let textNode = null;

    if (startContainer.nodeType === Node.TEXT_NODE) {
      textNode = startContainer;
    } else if (startContainer.textContent) {
      textNode = startContainer;
    }

    if (!textNode) return;

    const text = textNode.textContent;
    const offset = range.startOffset;

    // 截取光标前的文本（从文本节点开头到光标位置）
    const prefix = text.slice(0, offset);

    // 判断光标是否在 {{var}} 或 {{{var}}} 的末尾之后
    const regex = /\{\{\{[^}]*\}\}\}$|{{[^}]*}}$/;

    if (regex.test(prefix)) {
      // 不能停留在这个位置，根据上一次按键向前或向后偏移一位
      let charOffset = 0;
      this.saveCursorPosition(this.editor.nativeElement, (offset: number) => {
        if (this.preAction === 'ArrowLeft') {
          charOffset = offset - 1;
        } else {
          charOffset = offset + 1;
        }
      });
      this.restoreCursorPosition(this.editor.nativeElement, charOffset);
    }

    // 纯光标移动（无内容变化）时把换算后的偏移同步到 lastState，
    // 使下一次编辑的撤销快照记录真实编辑前光标位置；文本已变化
    // （编辑尚未 emit）时由 trackCursorOffset 内部跳过，交由
    // syncLastState 全量同步
    let rawOffset = -1;
    this.saveCursorPosition(this.editor.nativeElement, (o: number) => {
      rawOffset = o;
    });
    this.trackCursorOffset(this.editor.nativeElement, rawOffset);
  };

  applyStyle(content: string): string {
    // 匹配##语法
    const regExp = /(?<var>#+?\s.*?)\n/g;
    content = content.replace(regExp, '<span class="title">$<var></span>\n');
    return content;
  }

  escapeHTML(content: string): string {
    return content
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;')
      .replace(/\\/g, '&#92;');
  }
}
