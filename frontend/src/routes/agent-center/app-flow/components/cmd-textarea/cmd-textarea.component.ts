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

  @Input() placeholder = '';

  @Input() maxHeight = '480px';

  @Input() minHeight = '200px';

  @Output() compositionstart = new EventEmitter<CompositionEvent>();

  @Output() compositionend = new EventEmitter<CompositionEvent>();

  @Output() blur = new EventEmitter<void>();

  @ViewChild('cmdEditor') editor: ElementRef<HTMLDivElement>;

  @ViewChild('list') list: ElementRef<HTMLDivElement>;

  isTriggerClick = false; //判断是否由点击生成list,是的话替换时不需要扣除 触发命令的长度，比如'{'

  content = '';

  disabled = false;

  innerVariants: Array<CmdTextareaVariableGroup> = [];

  innerVariantsItems: Array<CmdTextareaVariableItem> = [];

  private preVariantsHash: string = ''; // 当前变量的哈希值，用于判断变量是否真正发生了变化

  private preAction: string = ''; // 记录按键

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
    value=value?.trim()??''
    value=this.escapeHTML(value);
      setTimeout(()=>{

        this.editor.nativeElement.innerHTML = `${value}<br>` || '<br>'
        this.cdr.detectChanges();
      })
  }

  selection: Selection | null = null;

  left = 0;

  top = 0;

  _showList = false;

  public selectedIndex = 0;

  private varTriggerSubscribe = undefined;

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
        this.checkAndRestoreCursorPosition();
        // 滚动到光标可见位置
        this.scrollCursorToVisible();
        this.showVarList();
        this.isTriggerClick = true;
      } else {
        this.showList = false;
      }
    });
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
    if (changes.variants) {
      const newVariants: CmdTextareaVariableGroup[] = [
        { label: '', items: [] },
      ];
      this.innerVariantsItems.length = 0;

      this.variants?.forEach((item) => {
        // 无分组信息类型放到默认组
        // 有分组信息类型追加新分组
        if (typeof item === 'string') {
          const variantsItem: CmdTextareaVariableItem = {
            label: item,
            value: item,
          };
          newVariants[0].items.push(variantsItem);
          this.innerVariantsItems.push(variantsItem);
        } else if (
          typeof item === 'object' &&
          'label' in item &&
          'value' in item
        ) {
          newVariants[0].items.push(item);
          this.innerVariantsItems.push(item);
        } else if (
          typeof item === 'object' &&
          'label' in item &&
          'items' in item
        ) {
          item?.items?.forEach((subItem, index) => {
            this.innerVariantsItems.push(subItem);
          });
          newVariants.push(item);
        } else {
        }
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
    document.removeEventListener('selectionchange', this.processCursorPosition);
  }

  onContentChange() {
    let content = this.getEditorTextContent();
    if (content === '\n') {
      // 清空 <br>
      this.editor.nativeElement.innerHTML = '';
    }
    if (this.maxLength && this.getLength() > this.maxLength) {
      document.execCommand('delete');
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
    return Math.max(
      this.getEditorTextContent().length,
      0,
    );
  }

  handlePaste(event: ClipboardEvent) {
    event.preventDefault();

    // 获取剪贴板中的文本内容
    let clipboardContent = event.clipboardData?.getData('text/plain') || '';
    // 处理不同操作系统的换行标记
    clipboardContent = clipboardContent
      .replaceAll('\r\n', '\n')
      .replaceAll('\r', '\n');
    // 获取当前选区和光标位置
    this.updateSelection();
    if (!this.selection || !this.range) {
      return;
    }

    // 超过最大长度截断
    if (this.maxLength) {
      let contentLength = clipboardContent.length;
      const leaveLength = this.maxLength - this.getLength();
      while (contentLength > leaveLength) {
        const extraCharactersNum = contentLength - leaveLength;
        clipboardContent = clipboardContent.slice(
          0,
          clipboardContent.length - extraCharactersNum,
        );
        contentLength = clipboardContent.length;
      }
    }

    // 创建文本节点
    const textNode = document.createTextNode(clipboardContent);

    // 插入文本到光标位置
    this.range.insertNode(textNode);
    // 移动光标到插入内容之后
    this.range.setStartAfter(textNode);

    // 触发内容更新
    this.emit();
  }

  onKeyDown(event: KeyboardEvent) {
    this.preAction = event.key;
    if (
      ['ArrowUp', 'ArrowDown', 'Enter'].includes(event.key) &&
      this.showList
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
      this.onContentChange();
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
      startContainer.parentElement.className === 'highlight'

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
      if (targetNode.classList.contains('highlight')) {
        targetNode.remove();
        event.preventDefault();
        this.onContentChange();
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
        this.selectedIndex =
          event.key === 'ArrowUp'
            ? (this.selectedIndex - 1 + len) % len
            : (this.selectedIndex + 1) % len;

        event.stopPropagation();
        this.scrollToVisibleArea();
      }

      if (event.key === 'Enter') {
        this.insertSelectedTemplate(
          this.innerVariantsItems[this.selectedIndex],
        );
      }
    }
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
    const preStartOffset = this.range?.startOffset;
    const startNode = this.range?.startContainer;
    if (!this.isTriggerClick) {
      startNode.textContent = startNode.textContent
        .slice(0, Math.max(preStartOffset - 1, 0))
        .concat(startNode.textContent.slice(preStartOffset));
      this.range?.setStart(startNode, Math.max(preStartOffset - 1, 0));
    }

    const node = this.getTmplNode(item.value);
    this.range?.deleteContents();
    this.range?.insertNode(node);
    this.selection?.removeAllRanges();
    this.selection?.collapse(node, 1);
    this.showList = false;
    this.isTriggerClick = false;
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

  private getTmplNode(content: string) {
    const node = document.createElement('span');
    node.textContent = `{{${content}}}`;

    return node;
  }

  private getEditorTextContent() {
    if (this.editor) {
      return this.editor.nativeElement.innerText.replaceAll('\u200B','');
    }
    return '\n';
  }

  private emit(): void {
    this.onChange(this.getEditorTextContent().replace(/\n$/, ''));
    this.onTouched();
  }

  private scrollToVisibleArea(): void {
    const listWrapper = this.list?.nativeElement;
    const selectedElement = listWrapper.children[
      this.selectedIndex
    ] as HTMLDivElement;

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
    const regex2 = new RegExp(`(?<var>{{[^{}\\n\\r]+?}})`, 'gi');
    const regex3 = new RegExp(`{{[^}]*}}$`);
    let processedText = this.editor.nativeElement.innerText;
    const subProcessedText=processedText.substring(0, charOffset);
    if (regex3.test(subProcessedText)) {
      // 如果光标在{{var}}后面，将charOffset+1
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
    processedText = processedText.replace(
      regex2,
      '<span class="highlight">$<var></span>\u200B',
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

    // 判断光标是否在 {{var}} 的末尾之后
    const regex = /{{[^}]*}}$/; // 匹配以 }} 结尾的 {{var}} 结构

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
