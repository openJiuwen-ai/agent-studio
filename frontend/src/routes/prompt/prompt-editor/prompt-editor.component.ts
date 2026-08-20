import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ComponentRef,
  ElementRef,
  EventEmitter,
  forwardRef,
  Input,
  NgZone,
  Output,
  Renderer2,
  SimpleChanges,
  ViewChild,
  ViewContainerRef,
} from '@angular/core';
import { NG_VALUE_ACCESSOR } from '@angular/forms';
import { VariableComponent } from '@routes/prompt/prompt-editor/variable/variable.component';
import { VariableInsertComponent } from '@routes/prompt/prompt-editor/variable-insert/variable-insert.component';
import { VariableService } from '@services/agent-center/prompt-optimize-task/prompt-editor.service';
import { COMMON_MODULES } from '@shared/modules';
import {
  IVariable,
  PromptType,
  VariableType,
} from '@interfaces/prompt/prompt-optimize-task.interface';

enum fieldTable {
  ClassName = 'className',
  LocalName = 'localName',
  InnerText = 'innerText',
  InnerHtml = 'innerHTML',
  Id = 'id',
  Length = 'length',
  localName = 'localName',
}

@Component({
  selector: 'meta-prompt-editor',
  standalone: true,
  imports: [VariableInsertComponent, COMMON_MODULES],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => PromptEditorComponent),
      multi: true,
    },
  ],
  templateUrl: './prompt-editor.component.html',
  styleUrl: './prompt-editor.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromptEditorComponent {
  // 最大长度
  @Input() maxLength?: number = 20000;

  @Input() promptType: PromptType = PromptType.MULTI;
  // 控制插入器显示
  @Input() showInserter = false;
  // 控制可编辑
  @Input() canEdit = true;
  // 控制编辑器模式,仅首次输入时有效
  @Input() onlyShow = false;
  // 样式传递
  @Input() style: any = 'height:400px';
  @Input() backgroundColor = '#fafafa';
  // 传入已有变量，仅用于变量类型解析（可选）
  @Input() variables: Array<IVariable> = [];
  @Input() initVariables: Array<IVariable> = [];
  // 高亮控制
  @Input() highlight? = false;
  @Input() compareContent?: string;
  @Input() diffColor? = '#e4f7e9';
  // 插入一个变量后触发，通知外部可以关闭插入器
  @Output() afterInsertVariable = new EventEmitter<void>();
  // 当变量有更新时触发
  @Output() variablesChange = new EventEmitter<
    Array<{ type: VariableType; value: string }>
  >();
  @Output() blur = new EventEmitter<any>();
  @ViewChild('editor', { read: ViewContainerRef, static: true })
  editorContainer: ViewContainerRef;
  @ViewChild('variableInsertRef', { read: ElementRef, static: true })
  variableInsertRef: ElementRef;
  // 变量插入器id，用于控制页面只显示一个插入器
  private variableInserterId = Math.random().toString(36).substring(2, 15);
  // 变量实例收集
  protected variableInstanceMap = new Map<
    string,
    ComponentRef<VariableComponent>
  >();
  // 标记有修改的变量，避免删除检测误删变量实例
  private variableChangeId = new Set<string>();
  // 重构提示词防抖
  private rebuildTimer: string | number | NodeJS.Timeout;
  // 提示词切片，初始时从文本构建dom
  public promptChunk: Array<{
    isDiff?: boolean;
    lineChunks: Array<{
      type: 'text' | 'variable' | 'lineBreak';
      value: string;
    }>;
  }> = [];
  // 提示词变量
  promptValue: string = '';
  // 变量map,便于操作
  variableMap = new Map<string, { type: VariableType; count: number }>();
  // 实际的插入器控制
  showInserterControl = false;
  // 编辑器模式控制
  onlyShowControl = false;
  // 删除检测
  observer: MutationObserver;

  // 定义meta-variable
  protected metaVariable = 'meta-variable';

  constructor(
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private variableServ: VariableService,
    protected renderer: Renderer2,
  ) {
    this.variableServ.variableId$.subscribe((id) => {
      if (this.variableInserterId === id) {
        return;
      }
      // 其他插入器被打开时，关闭当前插入器
      // 通知外部关闭
      this.afterInsertVariable.emit();
    });
  }

  ngOnInit() {
    this.editorContainer.element.nativeElement.style.setProperty(
      '--prompt-editor-background-color',
      this.backgroundColor,
    );
    // 初始化模式变量
    this.onlyShowControl = this.onlyShow;
    if (this.onlyShowControl) {
      this.canEdit = false;
    }
    // 建立变量map(此处针对初始时变量可用的情况）
    this.initVariables?.forEach((variable) => {
      const variableInfo = { type: variable.type, count: 0 };
      if (this.promptType === 'multi') {
        variableInfo.type = variable.type;
      } else {
        variableInfo.type = VariableType.TEXT;
      }
      this.variableMap.set(variable.value, variableInfo);
    });
  }

  ngAfterViewInit() {
    this.observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.removedNodes.length > 0) {
          // 处理被移除的节点
          this.processRemoveNode(mutation.removedNodes);
        }
      });
    });
    this.observer.observe(this.editorContainer.element.nativeElement, {
      childList: true, // 必须设为 true，才能检测子节点的添加/删除
      subtree: true, // 仅监听直接子节点（如果需要深层监听，设为 true）
    });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.showInserter) {
      this.showInserterControl = changes.showInserter.currentValue;
      if (this.showInserter) {
        // 如果是文本类型模板，直接插入，不选择类型
        if (this.promptType === 'multi') {
          this.setInserterPosition();
        } else {
          this.handleInsertVariable('text');
        }
      }
    }
    if (changes.highlight) {
      this.writeValue(this.promptValue);
    }
    if (changes.promptType) {
      this.variableServ.setId(undefined);
      this.variableInstanceMap.forEach((componentRef) => {
        componentRef.instance.setPromptType(this.promptType);
      });
      this.cdr.detectChanges();
    }
    if (changes.initVariables) {
      // 初始时可用不需要触发保存等逻辑，跟随提示词初始化完成
      // (此处针对初始时变量不可用的情况）
      // 变量在等待一段时间后才获取到
      // 外部可通过变更initVariables来控制类型
      if (changes.initVariables.isFirstChange()) {
        return;
      }
      this.initVariables?.forEach((variable) => {
        let variableInfo = this.variableMap.get(variable.value);
        if (!variableInfo) {
          variableInfo = { type: variable.type, count: 0 };
        }
        if (this.promptType === PromptType.MULTI) {
          variableInfo.type = variable.type;
        } else {
          variableInfo.type = VariableType.TEXT;
        }

        this.variableMap.set(variable.value, variableInfo);
      });
      // 触发一次变量更新事件，同步外部和内部
      this.updateVariable();
      setTimeout(() => {
        const prompt = this.html2prompt(
          this.editorContainer.element.nativeElement,
        );
        this.writeValue(prompt);
      });

    }
  }

  ngOnDestroy(): void {
    this.observer.disconnect();
  }

  protected createComponent() {
    // 创建变量节点
    return this.editorContainer.createComponent(VariableComponent);
  }

  onChange = (_: any) => {
  };
  onTouched = () => {
  };

  // 实现[(ngModel)]的相关方法
  writeValue(value: any): void {
    const editorEl = this.editorContainer.element.nativeElement as HTMLElement;
    const savedScrollTop = editorEl?.scrollTop || 0;
    this.ngZone.run(() => {
      this.renderer.setProperty(
        this.editorContainer.element.nativeElement,
        'innerHTML',
        '',
      );
      if (value === undefined || value === null) {
        value = '';
      }
      this.promptChunk = this.prompt2chunks(value);
      this.chunks2dom(this.promptChunk);
      setTimeout(() => {
        this.cdr.detectChanges();
        // 重建 DOM 后恢复滚动位置，避免 ngModel 回写触发的 DOM 重建重置 scrollTop
        if (editorEl && savedScrollTop > 0) {
          editorEl.scrollTop = savedScrollTop;
        }
      });
      value = value.replaceAll(this.CURSOR_MARK,'');
      // 此行代码置后，chunks2dom中的dom更新导致angular更新异常
      this.promptValue = String(value) + '';
    });
  }

  registerOnChange(fn: (value: any) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  public onInput(inputEvent: any | InputEvent) {
    const myPromptValue = this.html2prompt(this.editorContainer.element.nativeElement);
    if (myPromptValue.length > this.maxLength) {
      document.execCommand('delete');
      return;
    }

    if (inputEvent.data === '{' || inputEvent.data === '{}') {
      if (this.promptType === 'multi') {
        this.showInserterControl = true;
        this.setInserterPosition(true);
      } else {
        this.handleInsertVariable('text');
      }
    } else {
      if (this.showInserterControl) {
        this.showInserterControl = false;
      }
    }
    this.rebuildPrompt();
    this.scrollCursorToVisible();
  }

  public rebuildPrompt() {
    const promptValue = this.html2prompt(
      this.editorContainer.element.nativeElement,
    );
    if (promptValue === this.promptValue) {
      // 如果内容没有变化，则不触发外部事件
      return;
    }
    this.promptValue = promptValue;
    this.cdr.detectChanges();

    // 重构提示词
    if (!this.onlyShowControl) {
      if (this.rebuildTimer) {
        clearTimeout(this.rebuildTimer);
      }
      this.rebuildTimer = setTimeout(() => {
        if (promptValue.length > this.maxLength) {
          // 超过最大长度，不对外推送
          return;
        }
        this.onChange(this.promptValue);
      }, 300);
    }
  }

  public onblur() {
    this.rebuildPrompt();
    this.blur.emit();
  }

  public processRemoveNode(removeNodes: NodeList) {
    removeNodes.forEach((node) => {
      const localName = node[fieldTable.LocalName];
      if (localName === 'span') {
        this.processRemoveNode(node.childNodes);
      } else if (localName === 'div') {
        this.processRemoveNode(node.childNodes);
      } else if (localName === this.metaVariable) {
        const id = node[fieldTable.Id];
        if (this.variableChangeId.has(id)) {
          // 如果是被标记的id,直接跳过
          this.variableChangeId.delete(id);
          return;
        }
        this.rebuildPrompt();
        const componentRef = this.variableInstanceMap.get(id);
        if (componentRef) {
          componentRef.destroy();
          this.delVariable(componentRef.instance.variableNowValue);
        }
      } else {
        if (node?.childNodes) {
          this.processRemoveNode(node.childNodes);
        } else {
          return;
        }
      }
    });
  }

  public handleClick() {
    if (this.onlyShowControl) {
      return;
    }
    this.canEdit = true;
  }

  /**
   * 处理粘贴
   * @param clipboardEvent
   */
  public handlePaste(clipboardEvent: ClipboardEvent) {
    clipboardEvent.preventDefault();
    let clipboardContent =
      clipboardEvent.clipboardData?.getData('text/plain');
    // 先把内容直接插入到光标位置
    // 删除
    this.processDelete();
    // 插入剪贴板内容,直接以文本插入，然后重构dom实现变量的解析
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) {
      return;
    }
    const myPromptValue = this.html2prompt(this.editorContainer.element.nativeElement);
    // 判断是否超长,超长截断
    if (myPromptValue.length > this.maxLength) {
      return;
    }
    const leaveLength = this.maxLength - myPromptValue.length;
    let contentLength = clipboardContent.length;
    while (contentLength > leaveLength) {
      const extraCharactersNum = contentLength - leaveLength;
      clipboardContent = clipboardContent.slice(0, clipboardContent.length - extraCharactersNum);
      contentLength = clipboardContent.length;
    }
    const range = selection.getRangeAt(0);
    this.insertContentAtCursor(range, clipboardContent);
  }

  // 零宽空格字符，用于标记光标位置（刷新后会被保留）
  private readonly CURSOR_MARK = '\u200B';

  insertContentAtCursor(range: Range, content: string) {
    const textNode = document.createTextNode(content);
    range.insertNode(textNode);
    range.setStartAfter(textNode);
    // 插入特殊字符标记用于刷新后恢复光标位置
    const cursorMarkNode = document.createTextNode(this.CURSOR_MARK);
    range.insertNode(cursorMarkNode);
    range.setStartAfter(cursorMarkNode);
    // 刷新dom结构
    this.flushDom();
    // 刷新后查找特殊字符并恢复光标位置
    this.restoreCursorAfterFlush();
    // 通知外部
    this.onChange(this.promptValue);
  }
  /**
   * 在flushDom刷新DOM后恢复光标位置
   */
  private restoreCursorAfterFlush(): void {
    const editorElement = this.editorContainer.element.nativeElement;
    // 递归查找包含零宽空格字符的文本节点
    const markNode = this.findTextNodeContaining(editorElement, this.CURSOR_MARK);
    if (markNode) {
      const selection = document.getSelection();
      if (selection) {
        // 找到零宽空格的位置，将光标设置在该字符之后
        const textContent = markNode.textContent || '';
        const markIndex = textContent.indexOf(this.CURSOR_MARK);
        if (markIndex !== -1) {
          const range = document.createRange();
          range.setStart(markNode, markIndex );
          range.setEnd(markNode, markIndex + 1);
          selection.removeAllRanges();
          selection.addRange(range);
          range.deleteContents();
        }
      }
    }
    this.scrollCursorToVisible();
  }

  /**
   * 将编辑器滚动到光标可见位置
   * 通过当前 selection 的 range 位置计算 caret 相对于编辑器视区的偏移，
   * 超出可视区域时调整 scrollTop，避免用户看不到正在输入的内容。
   * 不插入临时元素，避免影响变量解析与 chunks2dom 重构。
   * 用 requestAnimationFrame 延迟到浏览器完成布局后再读 rect，避免读到旧值。
   */
  private scrollCursorToVisible(): void {
    // 用 setTimeout(0) 而非 requestAnimationFrame，确保在 Angular 变更检测之后执行
    setTimeout(() => {
      const editorElement = this.editorContainer.element
        .nativeElement as HTMLElement;
      if (!editorElement) {
        return;
      }
      const selection = document.getSelection();
      if (!selection || selection.rangeCount === 0) {
        return;
      }
      const range = selection.getRangeAt(0);
      let caretRect = range.getBoundingClientRect();

      // collapsed range 在部分浏览器下返回 zero-size rect，回退到容器元素位置
      if (caretRect.top === 0 && caretRect.bottom === 0) {
        let anchor: Node | null = range.endContainer;
        if (anchor && anchor.nodeType !== Node.ELEMENT_NODE) {
          anchor = anchor.parentElement;
        }
        if (anchor) {
          caretRect = (anchor as Element).getBoundingClientRect();
        }
      }
      if (!caretRect) {
        return;
      }

      // 从 editor 开始向上遍历所有可滚动祖先（含 editor 自身），
      // 对每一层判断 caret 是否落在该层可视区域外，超出则滚动。
      const margin = 20;
      let container: HTMLElement | null = editorElement;
      while (container) {
        // 快速跳过：scrollHeight 不大于 clientHeight 的容器肯定不可滚动，
        // 无需调 getComputedStyle，避免祖先链上无意义的 style recalc。
        if (container.scrollHeight <= container.clientHeight + 1) {
          container = container.parentElement;
          continue;
        }
        const style = getComputedStyle(container);
        const overflowY = style.overflowY;
        const scrollable = overflowY === 'auto' || overflowY === 'scroll';
        if (scrollable) {
          const containerRect = container.getBoundingClientRect();
          const relativeTop = caretRect.top - containerRect.top;
          const relativeBottom = caretRect.bottom - containerRect.top;
          const clientHeight = container.clientHeight;
          const viewportTop = margin;
          const viewportBottom = clientHeight - margin;

          let needsScroll = false;
          let newScrollTop = container.scrollTop;

          if (relativeBottom > viewportBottom) {
            newScrollTop =
              container.scrollTop + (relativeBottom - viewportBottom);
            needsScroll = true;
          } else if (relativeTop < viewportTop) {
            newScrollTop =
              container.scrollTop + (relativeTop - viewportTop);
            needsScroll = true;
          }

          if (needsScroll) {
            newScrollTop = Math.max(
              0,
              Math.min(
                newScrollTop,
                container.scrollHeight - container.clientHeight,
              ),
            );
            container.scrollTop = newScrollTop;
            container.scrollTo({ top: newScrollTop });

            // 滚动后 caret 视口坐标变化，更新以供上层祖先判断
            caretRect = range.getBoundingClientRect();
            if (caretRect.top === 0 && caretRect.bottom === 0) {
              let anchor: Node | null = range.endContainer;
              if (anchor && anchor.nodeType !== Node.ELEMENT_NODE) {
                anchor = anchor.parentElement;
              }
              if (anchor) {
                caretRect = (anchor as Element).getBoundingClientRect();
              }
            }
          }
        }
        container = container.parentElement;
      }
    });
  }
  /**
   * 递归查找包含指定字符的文本节点
   */
  private findTextNodeContaining(node: Node, char: string): Text | null {
    if (node.nodeType === Node.TEXT_NODE && node.textContent?.includes(char)) {
      return node as Text;
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
      const element = node as Element;
      // 跳过变量元素
      if (element.tagName?.toLowerCase() === this.metaVariable) {
        return null;
      }
      for (let i = 0; i < element.childNodes.length; i++) {
        const result = this.findTextNodeContaining(element.childNodes[i], char);
        if (result) {
          return result;
        }
      }
    }
    return null;
  }
  public handleCopy(clipboardEvent: ClipboardEvent) {
    clipboardEvent.preventDefault();
    // 获取选中的内容
    const selectedText = this.processCopy();
    // 将选中的内容复制到剪贴板
    clipboardEvent.clipboardData?.setData('text/plain', selectedText);
  }

  public handleCut(clipboardEvent: ClipboardEvent) {
    clipboardEvent.preventDefault();
    // 获取选中的内容
    const selectedText = this.processCopy();
    // 将选中的内容复制到剪贴板
    clipboardEvent.clipboardData?.setData('text/plain', selectedText);
    // 删除选中的内容
    this.processDelete();
  }

  private flushDom() {
    // 重构prompt
    let promptValue = this.html2prompt(
      this.editorContainer.element.nativeElement,
    );
    // 最后重新解析prompt
    this.writeValue(promptValue);
  }

  private processCopy(): any {
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) {
      return '';
    }

    const tempDiv = document.createElement('div');
    // 将选中的DOM片段放入临时元素
    selection
      .getRangeAt(0)
      .cloneContents()
      .childNodes.forEach((node) => {
      tempDiv.appendChild(node.cloneNode(true));
    });
    return this.html2prompt(tempDiv);
  }

  private processDelete() {
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    range.deleteContents();
    this.emptyFillDiv();
  }

  public updateVariable(variable: any = null) {
    if (variable) {
      // 如果传入了变量，则更新
      const oldVariable = variable.origin;
      const newVariable = variable.target;
      oldVariable.value = oldVariable.value.trim();
      newVariable.value = newVariable.value.trim();
      if (oldVariable.type !== newVariable.type) {
        // 类型有变化，更新类型
        // 需要更新该变量名的全部实例
        const variableInfo = this.variableMap.get(newVariable.value);
        this.variableInstanceMap.forEach((componentRef) => {
          if (componentRef.instance.variableNowValue === oldVariable.value) {
            // 同名变量都要更新类型
            componentRef.instance.setType(newVariable.type);
          }
        });
        variableInfo.type = newVariable.type;
      }
      if (oldVariable.value !== newVariable.value) {
        // 变量内容有变化，触发提示词重构
        this.rebuildPrompt();
        // 新增变量
        const newVariableInfo = this.variableMap.get(newVariable.value);
        if (newVariableInfo) {
          // 如果已经存在，则计数加一
          newVariableInfo.count++;
        } else {
          // 如果不存在，则新增
          this.variableMap.set(newVariable.value, {
            type: newVariable.type,
            count: 1,
          });
        }
        // 更新原变量计数
        const oldVariableInfo = this.variableMap.get(oldVariable.value);
        if (oldVariableInfo) {
          oldVariableInfo.count--;
        }
      }
    }
    // 触发变量更新事件
    const newVariables = Array.from(this.variableMap.entries())
      .map(([value, variableInfo]) => ({
        value,
        type: variableInfo.type,
        count: variableInfo.count,
      }))
      .filter((item) => item.count >= 1);
    this.variablesChange.emit(newVariables);
  }

  public delVariable(variable: any) {
    const variableInfo = this.variableMap.get(variable);
    if (variableInfo) {
      variableInfo.count--;
      if (variableInfo.count === 0) {
        this.variableMap.delete(variable);
      }
    }
    this.updateVariable();
  }

  public prompt2chunks(prompt: string): typeof this.promptChunk {
    const chunks = [];
    const variableRegex = /{{(.*?)}}/g;
    let match;
    let lastIndex = 0;
    let variableChange = false;
    let diffResult;
    // 按 \n 分割字符串
    const lines = prompt
      .replaceAll('\r\n', '\n')
      .replaceAll('\r', '\n')
      .split('\n');

    if (this.highlight && this.compareContent) {
      const compareLines = this.compareContent
        .replaceAll('\r\n', '\n')
        .replaceAll('\r', '\n')
        .split('\n');
      diffResult = this.calculateDiff(compareLines, lines);
    } else {
      diffResult = new Array(lines.length).fill(false);
    }

    // 处理每一行
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineChunks = [];

      chunks.push({
        isDiff: this.highlight && diffResult[i],
        lineChunks,
      });
      if (line === '') {
        // 添加行分隔符
        lineChunks.push({ type: 'lineBreak', value: '\n' });
        continue;
      }

      lastIndex = 0;
      while ((match = variableRegex.exec(line)) !== null) {
        const start = match.index;
        const end = variableRegex.lastIndex;

        if (start > lastIndex) {
          lineChunks.push({
            type: 'text',
            value: line.substring(lastIndex, start),
          });
        }

        lineChunks.push({ type: 'variable', value: match[1] });

        if (!this.variableMap.has(match[1].trim())) {
          // 如果提示词存在未传入的变量，则同步更新
          this.variableMap.set(match[1].trim(), { type: VariableType.TEXT, count: 1 });
          variableChange = true;
        } else {
          // 如果已经存在，则计数加一
          const variableInfo = this.variableMap.get(match[1]);
          variableInfo.count++;
        }
        lastIndex = end;
      }
      if (lastIndex < prompt.length) {
        lineChunks.push({ type: 'text', value: line.substring(lastIndex) });
      }
    }

    if (variableChange) {
      // 如果变量改变
      this.updateVariable();
    }
    return chunks;
  }

  /**
   * 将prompt切片转为dom结构
   * @param chunks
   */
  public chunks2dom(chunks: typeof this.promptChunk) {
    this.editorContainer.clear();
    this.renderer.setProperty(
      this.editorContainer.element.nativeElement,
      fieldTable.InnerHtml,
      '',
    );
    const selection = document.getSelection();
    const range = document.createRange();
    for (let i = 0; i < chunks.length; i++) {
      const lineChunks = chunks[i].lineChunks;
      const lineContainer = this.renderer.createElement('div');
      this.renderer.addClass(lineContainer, 'line');
      if (this.highlight && chunks[i].isDiff) {
        this.renderer.setStyle(
          lineContainer,
          'backgroundColor',
          this.diffColor,
        );
      }
      this.renderer.appendChild(
        this.editorContainer.element.nativeElement,
        lineContainer,
      );
      lineChunks.forEach((chunk) => {
        if (chunk.type === 'text') {
          if (chunk.value === '') {
            return;
          }
          // 创建文本节点
          const wrapper = this.renderer.createElement('span');
          this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
          const textNode = this.renderer.createText(chunk.value);
          this.renderer.appendChild(wrapper, textNode);
          this.renderer.appendChild(lineContainer, wrapper);
        } else if (chunk.type === 'lineBreak') {
          const wrapper = this.renderer.createElement('span');
          this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
          const br = this.renderer.createElement('br');
          this.renderer.appendChild(wrapper, br);
          this.renderer.appendChild(lineContainer, wrapper);
        } else if (chunk.type === 'variable') {
          // 创建变量节点
          const componentRef = this.createComponent();
          // 基本属性
          const id = `variable-${Math.random().toString(36).substring(2, 15)}`;
          componentRef.location.nativeElement.id = id;
          this.variableInstanceMap.set(id, componentRef);
          componentRef.location.nativeElement.style.display = 'inline-block';
          componentRef.location.nativeElement.contentEditable = 'false';
          componentRef.instance.variable = chunk.value;
          componentRef.instance.canEdit = false;
          componentRef.instance.type =
            this.variableMap.get(chunk.value)?.type ?? 'text';
          componentRef.instance.promptType = this.promptType;
          // 模式控制
          if (this.onlyShowControl) {
            // 设置为仅展示模式
            componentRef.instance.onlyShow = this.onlyShowControl;
          } else {
            // 可编辑模式
            // 添加取消变量编辑时的回调,箭头函数绑定this指向
            componentRef.instance.setOnBlur(() => {
              this.onVariableBlur(componentRef, selection);
            });
            // 添加变量更新的回调,箭头函数绑定this指向
            componentRef.instance.setOnChange((variable) => {
              this.updateVariable(variable);
            });
          }
          const wrapper = this.renderer.createElement('span');
          this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
          this.renderer.setAttribute(wrapper, 'contenteditable', 'false');
          this.renderer.appendChild(
            wrapper,
            componentRef.location.nativeElement,
          );
          this.renderer.appendChild(lineContainer, wrapper);
        } else {
          // do nothing
        }
      });
      if (lineContainer.innerHTML === '') {
        const wrapper = this.renderer.createElement('span');
        this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
        this.renderer.appendChild(lineContainer, wrapper);
      }

      this.cdr.markForCheck();
    }
    setTimeout(() => {
      this.cdr.detectChanges();
    }, 0);
  }

  public html2prompt(container) {
    const nodes = container.childNodes;
    let result = '';
    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      if (node.nodeType === Node.TEXT_NODE) {
        result += node.textContent;
      } else if (node.nodeType === Node.ELEMENT_NODE) {
        if (node.localName === this.metaVariable) {
          const variable = node
            .querySelector('.variable-input')
            ?.textContent?.trim();
          if (variable) {
            result += `{{${variable}}}`;
          }
        } else if (node.localName === 'div') {
          const subResult = this.html2prompt(node);
          if (subResult === '\n') {
            // 空行不要重复加换行符
            result += '\n';
          } else {
            result += subResult + '\n';
          }
        } else if (node.localName === 'br') {
          result += '\n';
        } else if (node.localName === 'span') {
          result += this.html2prompt(node);
        } else {
          // do nothing
        }
      }
    }
    if (container === this.editorContainer.element.nativeElement) {
      // 最终结果去掉结尾\n
      return result.slice(0, -1);
    }
    return result;
  }

  public calculateDiff(originLines: Array<string>, targetLines: Array<string>) {
    const result = [];
    let compareStartIndex = 0;
    for (let targetLine of targetLines) {
      if (targetLine === '') {
        result.push(false);
        continue;
      }
      let i: number;
      for (i = compareStartIndex; i < originLines.length; i++) {
        if (targetLine === originLines[i]) {
          result.push(false);
          compareStartIndex = i + 1;
          break;
        }
      }
      if (i >= originLines.length) {
        result.push(true);
      }
    }
    return result;
  }

  public onVariableBlur(componentRef, selection) {
    this.canEdit = true;
    this.editorContainer.element.nativeElement.focus();
    const range = document.createRange();
    range.setStartAfter(componentRef.location.nativeElement.parentNode);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  insertVariableAtCursor(type: VariableType = VariableType.TEXT) {
    if (this.onlyShowControl) {
      // 仅展示模式，不执行插入
      return;
    }
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) return;
    // 如果光标不在编辑器内，将光标放到编辑器末尾
    const editorElement = this.editorContainer.element.nativeElement;
    if (
      editorElement === selection.anchorNode || // 光标锚点需要在内部在编辑器内的子节点上
      !editorElement.contains(selection.anchorNode) ||
      !editorElement.contains(selection.focusNode) ||
      selection.anchorNode[fieldTable.ClassName] ===
      'variable-input cursor-text' ||
      selection.anchorNode.parentNode[fieldTable.ClassName] ===
      'variable-input cursor-text'
    ) {
      const range = document.createRange();
      range.setStart(
        editorElement.lastChild,
        editorElement.lastChild.childNodes.length,
      );
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    // 光标处于折叠状态（无选中内容），获取光标位置
    const range = selection.getRangeAt(0);
    const startContainer = range.startContainer; // 光标所在的节点
    let startOffset = range.startOffset; // 光标在节点中的偏移量

    // 仅处理文本节点（光标在文本中时）
    if (startContainer.nodeType === Node.TEXT_NODE) {
      // 输入左括号时,中文输入法自动补全右括号,
      // 因为文本类型提示词无需选择变量类型,直接插入变量,触发当前方法时光标还在{}后面
      // 多模态类型提示词,需要用户选择变量类型,中间有一个过程,此时光标已被浏览器或输入法移动到{}中间

      // 获取光标前两个字符
      const offset = Math.max(0, startOffset - 2);
      const aroundChar = startContainer.textContent?.slice(offset, startOffset);
      if (aroundChar.endsWith('{}')) {
        // 中文输入法,文本提示词的情况
        // 如果光标前是一组大括号，则一起删除
        range.setStart(startContainer, startOffset - 2);
        range.setEnd(startContainer, startOffset);
        // 删除选中的字符
        range.deleteContents();
      }
      if (aroundChar.endsWith('{')) {
        // 如果光标前是左括号
        if (startContainer.textContent?.slice(startOffset, startOffset + 1) === '}') {
          // 中文输入法,多模态提示词的情况
          // 如果后面是‘}’,一起删除
          range.setStart(startContainer, startOffset - 1);
          range.setEnd(startContainer, startOffset + 1);
          range.deleteContents();
        } else {
          // 其他情况
          // 只删除前面的一个{
          range.setStart(startContainer, startOffset - 1);
          range.setEnd(startContainer, startOffset);
          range.deleteContents();
        }
      }

      // 把文本span分成两span,文本span内有多个文本节点，先把目标文本分成两段，光标放中间，然后把光标后面放到下一个span
      startOffset = range.startOffset;
      const textAfterCursor = startContainer.textContent?.slice(startOffset);
      if (textAfterCursor !== '') {
        const textNodeAfterCursor = document.createTextNode(textAfterCursor);
        startContainer.parentNode.insertBefore(
          textNodeAfterCursor,
          startContainer.nextSibling,
        );
      }
      startContainer.textContent = startContainer.textContent?.slice(
        0,
        startOffset,
      );

      range.setStart(startContainer, startContainer[fieldTable.Length]);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
      // 将光标后面的文本节点移动到新的 span 中
      const wrapper = document.createElement('span');
      wrapper.style.letterSpacing = '0px';
      if (
        range.startContainer.parentNode.nodeType === Node.ELEMENT_NODE &&
        range.startContainer.parentNode[fieldTable.ClassName] === 'line'
      ) {
        range.startContainer.parentNode.appendChild(wrapper);
      } else {
        range.startContainer.parentNode.parentNode.insertBefore(
          wrapper,
          range.startContainer.parentNode.nextSibling,
        );
        while (startContainer.nextSibling) {
          wrapper.appendChild(startContainer.nextSibling);
        }
      }
    }
    const componentRef = this.createComponent();
    const id = `variable-${Math.random().toString(36).substring(2, 15)}`;
    componentRef.location.nativeElement.id = id;
    this.variableInstanceMap.set(id, componentRef);
    componentRef.location.nativeElement.style.display = 'inline-block';
    componentRef.location.nativeElement.contentEditable = 'false';
    componentRef.instance.variable = '';
    componentRef.instance.canEdit = true;
    componentRef.instance.type = type;
    componentRef.instance.promptType = this.promptType;
    componentRef.instance.setOnBlur(() => {
      this.onVariableBlur(componentRef, selection);
    });
    componentRef.instance.setOnChange((variable) => {
      this.updateVariable(variable);
    });
    this.canEdit = false;

    // 将组件插入到光标位置
    const wrapper = document.createElement('span');
    wrapper.style.letterSpacing = '0px';
    wrapper.contentEditable = 'false';
    wrapper.appendChild(componentRef.location.nativeElement);
    if (
      range.startContainer.nodeType === Node.ELEMENT_NODE &&
      range.startContainer[fieldTable.ClassName] === 'line'
    ) {
      if (
        range.startContainer.firstChild &&
        range.startContainer.firstChild[fieldTable.LocalName] === 'span' &&
        range.startContainer.firstChild.firstChild &&
        range.startContainer.firstChild.firstChild[fieldTable.LocalName] ===
        'br'
      ) {
        range.startContainer.removeChild(range.startContainer.firstChild);
      }
      range.insertNode(wrapper);
    } else if (
      range.startContainer.parentNode.nodeType === Node.ELEMENT_NODE &&
      range.startContainer.parentNode[fieldTable.ClassName] === 'line'
    ) {
      range.startContainer.parentNode.insertBefore(
        wrapper,
        range.startContainer,
      );
    } else if (range.startContainer.nodeType === Node.TEXT_NODE) {
      range.startContainer.parentNode.parentNode.insertBefore(
        wrapper,
        range.startContainer?.parentNode?.nextSibling,
      );
    } else {
      range.startContainer.parentNode.insertBefore(
        wrapper,
        range.startContainer,
      );
    }

    componentRef.instance.focus();
    if (this.variableMap.has('')) {
      this.variableMap.get('').count++;
    } else {
      this.variableMap.set('', { type: type, count: 1 });
    }
    // 插入变量后，dom已经更新，但是this.editorContainer没有及时更新，会导致placeholder没有立即隐藏，强制执行变更检测
    this.cdr.detectChanges();
  }

  // 其他方法
  handleInsertVariable(variable_type: any) {
    if (this.onlyShowControl) {
      // 仅展示模式，不执行插入
      return;
    }
    this.insertVariableAtCursor(variable_type);
    this.showInserterControl = false;
    this.afterInsertVariable.emit();
  }

  /**
   * 自带的处理逻辑无法正确处理变量标签，涉及到变量的操作需要特殊处理
   * @param event
   */
  handleKeyDown = (event: KeyboardEvent) => {
    // 阻止 Ctrl+Z (撤销)
    if (
      (event.ctrlKey && event.key === 'z') ||
      (event.ctrlKey && event.keyCode === 90)
    ) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }

    // 处理 Backspace 键
    if (event.key === 'Backspace' || event.keyCode === 8) {
      this.handleBackspace(event);
    }
    // 处理 Enter 键
    else if (event.key === 'Enter' || event.keyCode === 13) {
      this.handleEnter(event);
    }

    // 处理 Delete 键
    else if (event.key === 'Delete' || event.keyCode === 46) {
      this.handleDelete(event);
    }

    this.rebuildPrompt();
    this.scrollCursorToVisible();
  };

  private mergeLinesByBackspace(curNode, selection) {
    const preNode = curNode.previousSibling;
    if (!preNode) {
      return;
    }
    let startOffset = preNode.childNodes.length;
    // 合并两个节点
    while (preNode.lastChild) {
      if (
        preNode.lastChild?.firstChild[fieldTable.LocalName] === 'br' ||
        preNode.lastChild[fieldTable.InnerText] === ''
      ) {
        preNode.removeChild(preNode.lastChild);
        startOffset--;
        continue;
      }
      if (
        preNode.lastChild.firstChild[fieldTable.localName] === this.metaVariable
      ) {
        const id = preNode.lastChild.firstChild[fieldTable.Id];
        const componentRef = this.variableInstanceMap.get(id);
        this.variableChangeId.add(id);
        if (componentRef) {
          componentRef.location.nativeElement.remove(); // 从原位置移除
          preNode.removeChild(preNode.lastChild);
          const wrapper = document.createElement('span');
          wrapper.style.letterSpacing = '0px';
          wrapper.contentEditable = 'false';
          wrapper.appendChild(componentRef.location.nativeElement);
          curNode.insertBefore(wrapper, curNode.firstChild);
        } else {
          curNode.insertBefore(preNode.lastChild, curNode.firstChild);
        }
      } else {
        curNode.insertBefore(preNode.lastChild, curNode.firstChild);
      }
    }
    preNode.parentNode?.removeChild(preNode);
    // 恢复光标位置
    const range = document.createRange();
    range.setStart(curNode, startOffset);
    range.collapse(true);
    selection.removeAllRanges();
    selection.addRange(range);
  }

  private handleBackspace(event: KeyboardEvent) {
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) {
      return;
    }
    // 如果有选区，直接执行删除操作
    if (!selection.isCollapsed) {
      event.preventDefault();
      this.processDelete();
      return;
    }

    // 删除空节点，有光标位于span和位于div两种情况
    while (
      selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
      selection.anchorNode[fieldTable.LocalName] === 'span' &&
      selection.anchorNode[fieldTable.InnerHtml] === ''
      ) {
      // 位于span
      const child = selection.anchorNode;
      const range = document.createRange();
      if (
        child.previousSibling &&
        child.previousSibling.lastChild &&
        child.previousSibling.lastChild.nodeType === Node.TEXT_NODE
      ) {
        // 非空文本span
        range.setStart(
          child.previousSibling.lastChild,
          child.previousSibling.lastChild[fieldTable.Length],
        );
      } else if (
        child.previousSibling &&
        child.previousSibling.lastChild === null
      ) {
        // 空文本span
        range.setStart(child.previousSibling, 0);
      } else if (
        child.previousSibling &&
        child.previousSibling.lastChild &&
        child.previousSibling.lastChild[fieldTable.LocalName] ===
        this.metaVariable
      ) {
        // 变量span
        range.setStartAfter(child.previousSibling);
      } else {
        break;
      }
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
      child.parentNode.removeChild(child);
    }
    while (
      selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
      selection.anchorNode[fieldTable.ClassName] === 'line' &&
      selection.anchorNode.firstChild &&
      selection.anchorNode.firstChild[fieldTable.InnerHtml] === ''
      ) {
      // 位于div
      selection.anchorNode.removeChild(selection.anchorNode.firstChild);
    }
    if (
      selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
      selection.anchorNode[fieldTable.ClassName] === 'line' &&
      selection.anchorOffset === 0
    ) {
      // 光标处于行首，且行首是变量
      event.preventDefault();
      const curNode = selection.anchorNode;
      this.mergeLinesByBackspace(curNode, selection);
    } else if (
      selection.anchorNode.nodeType === Node.TEXT_NODE &&
      selection.anchorNode.previousSibling === null &&
      selection.anchorNode.parentNode[fieldTable.LocalName] === 'span' &&
      selection.anchorNode.parentNode.previousSibling === null &&
      selection.anchorOffset === 0
    ) {
      event.preventDefault();
      const curNode = selection.anchorNode.parentNode.parentNode;
      this.mergeLinesByBackspace(curNode, selection);
    } else if (
      selection.anchorNode.nodeType === Node.TEXT_NODE &&
      selection.anchorOffset === 1 &&
      selection.anchorNode[fieldTable.Length] === 1
    ) {
      event.preventDefault();
      selection.anchorNode.parentNode.removeChild(selection.anchorNode);
    } else if (
      selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
      selection.anchorNode[fieldTable.ClassName] === 'line'
    ) {
      // 先不阻止默认事件
      // 先清理空span
      let anchorOffset = selection.anchorOffset;
      while (anchorOffset > 0) {
        const child = selection.anchorNode.childNodes[anchorOffset - 1];
        if (child && child[fieldTable.InnerText] === '') {
          selection.anchorNode.removeChild(child);
          anchorOffset--;
        } else {
          break;
        }
      }
      const child = selection.anchorNode.childNodes[anchorOffset - 1];
      if (
        child &&
        child.lastChild &&
        child.lastChild[fieldTable.localName] === this.metaVariable
      ) {
        event.preventDefault();
        // 如果光标的位置是变量，执行移除逻辑
        selection.anchorNode.removeChild(
          selection.anchorNode.childNodes[anchorOffset - 1],
        );
      } else if (
        child &&
        child.lastChild &&
        child.lastChild.nodeType === Node.TEXT_NODE
      ) {
        // 是文本，交给默认逻辑
        const range = document.createRange();
        range.setStart(child.lastChild, child.lastChild[fieldTable.Length]);
        range.collapse(true);
        selection.removeAllRanges();
        selection.addRange(range);
      }
    } else {
      // 其他情况，交给默认逻辑
    }
    this.emptyFillDiv();
  }

  /**
   * 退格删除后编辑器为空需要补一个div
   * @private
   */
  protected emptyFillDiv() {
    setTimeout(() => {
      if (this.editorContainer.element.nativeElement.innerText === '') {
        // 为空则添加一个div
        const newLine = this.renderer.createElement('div');
        this.renderer.addClass(newLine, 'line');
        const wrapper = this.renderer.createElement('span');
        this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
        const br = this.renderer.createElement('br');
        this.renderer.appendChild(wrapper, br);
        this.renderer.appendChild(newLine, wrapper);
        this.renderer.setProperty(
          this.editorContainer.element.nativeElement,
          fieldTable.InnerHtml,
          '',
        );
        this.renderer.appendChild(
          this.editorContainer.element.nativeElement,
          newLine,
        );
      }
    }, 0);
  }

  protected handleEnter(event: KeyboardEvent) {
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) {
      return;
    }
    // 如果有选区，先执行删除操作
    if (!selection.isCollapsed) {
      this.processDelete();
    }
    if (
      selection.anchorNode.nodeType === Node.TEXT_NODE &&
      selection.anchorNode[fieldTable.Length] === selection.anchorOffset &&
      selection.anchorNode.nextSibling === null
    ) {
      // 光标处于文本span最后面，用div换行，把后面的元素移入
      event.preventDefault();
      event.stopPropagation();
      const curNode = selection.anchorNode.parentNode;
      const nextline = document.createElement('div');
      nextline.classList.add('line');
      curNode.parentNode?.parentNode?.insertBefore(
        nextline,
        curNode.parentNode.nextSibling,
      );
      while (curNode.nextSibling) {
        if (
          curNode.nextSibling[fieldTable.LocalName] === 'span' &&
          curNode.nextSibling[fieldTable.InnerText] === ''
        ) {
          curNode.parentNode.removeChild(curNode.nextSibling);
        } else if (
          curNode.nextSibling?.firstChild[fieldTable.LocalName] ===
          this.metaVariable
        ) {
          const id = curNode.nextSibling.firstChild[fieldTable.Id];
          const componentRef = this.variableInstanceMap.get(id);
          this.variableChangeId.add(id);
          if (componentRef) {
            // 关键：通过组件实例的location移动DOM，而非直接insertBefore
            componentRef.location.nativeElement.remove(); // 从原位置移除
            curNode.parentNode.removeChild(curNode.nextSibling);
            const wrapper = document.createElement('span');
            wrapper.style.letterSpacing = '0px';
            wrapper.contentEditable = 'false';
            wrapper.appendChild(componentRef.location.nativeElement); // 添加到新行
            nextline.appendChild(wrapper);
          } else {
            nextline.appendChild(curNode.nextSibling);
          }
        } else {
          nextline.appendChild(curNode.nextSibling);
        }
      }
      if (nextline.innerHTML === '') {
        // 为空添加一个换行符占位
        const wrapper = document.createElement('span');
        wrapper.style.letterSpacing = '0px';
        const br = document.createElement('br');
        wrapper.appendChild(br);
        nextline.appendChild(wrapper);
      }
      const range = document.createRange();
      range.setStart(nextline, 0);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    } else if (
      selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
      selection.anchorNode[fieldTable.ClassName] === 'line'
    ) {
      event.preventDefault();
      event.stopPropagation();
      const curNode = selection.anchorNode;
      const nextline = document.createElement('div');
      nextline.classList.add('line');
      curNode.parentNode?.insertBefore(nextline, curNode.nextSibling);
      const offset = selection.anchorOffset;
      while (curNode.childNodes.length > offset) {
        if (
          curNode.childNodes[offset]?.firstChild[fieldTable.LocalName] ===
          this.metaVariable
        ) {
          const id = curNode.childNodes[offset].firstChild[fieldTable.Id];
          const componentRef = this.variableInstanceMap.get(id);
          this.variableChangeId.add(id);
          if (componentRef) {
            // 关键：通过组件实例的location移动DOM，而非直接insertBefore
            componentRef.location.nativeElement.remove(); // 从原位置移除
            curNode.removeChild(curNode.childNodes[offset]);
            const wrapper = document.createElement('span');
            wrapper.style.letterSpacing = '0px';
            wrapper.contentEditable = 'false';
            wrapper.appendChild(componentRef.location.nativeElement); // 添加到新行
            nextline.appendChild(wrapper);
          } else {
            nextline.appendChild(curNode.childNodes[offset]);
          }
        } else {
          nextline.appendChild(curNode.childNodes[offset]);
        }
      }
      if (nextline.innerHTML === '') {
        // 为空添加一个换行符占位
        const wrapper = document.createElement('span');
        wrapper.style.letterSpacing = '0px';
        const br = document.createElement('br');
        wrapper.appendChild(br);
        nextline.appendChild(wrapper);
      }
      if (curNode[fieldTable.InnerHtml] === '') {
        // 为空添加一个换行符占位
        const wrapper = document.createElement('span');
        wrapper.style.letterSpacing = '0px';
        const br = document.createElement('br');
        wrapper.appendChild(br);
        curNode.appendChild(wrapper);
      }
      const range = document.createRange();
      range.setStart(nextline, 0);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    } else {
      event.preventDefault();
      if (
        selection.anchorNode.nodeType === Node.ELEMENT_NODE &&
        selection.anchorNode[fieldTable.ClassName] === 'line'
      ) {
        const wrapper = document.createElement('span');
        wrapper.style.letterSpacing = '0px';
        const br = document.createElement('br');
        wrapper.appendChild(br);
        selection.anchorNode.appendChild(wrapper);
        const range = document.createRange();
        range.setStartAfter(br);
        range.collapse(false);
        selection.removeAllRanges();
        selection.addRange(range);
      } else {
        const range = selection.getRangeAt(0);
        const br = document.createElement('br');
        range.insertNode(br);
        range.collapse(false);
      }
    }
  }

  private handleDelete(event: KeyboardEvent) {
    const selection = document.getSelection();
    if (!selection || !selection.rangeCount) {
      return;
    }

    // 如果有选区，直接执行删除操作
    if (!selection.isCollapsed) {
      event.preventDefault();
      this.processDelete();
      return;
    }

    let nextNode: ChildNode;
    if (selection.anchorNode.nodeType === Node.TEXT_NODE) {
      nextNode = selection.anchorNode?.parentNode?.nextSibling;
    } else {
      nextNode = selection.anchorNode?.nextSibling;
    }

    if (!nextNode) {
      // 光标处于每行最后面
      event.preventDefault();
      const curNode = selection.anchorNode.parentNode.parentNode;
      const nextNode = curNode.nextSibling;
      if (!nextNode) {
        return;
      }
      // 记录光标位置
      const startContainer = selection.anchorNode;
      const offset = selection.anchorOffset;
      // 合并两个节点
      while (curNode.lastChild) {
        if (
          curNode.nextSibling?.firstChild[fieldTable.LocalName] ===
          this.metaVariable
        ) {
          const id = curNode.nextSibling.firstChild[fieldTable.Id];
          const componentRef = this.variableInstanceMap.get(id);
          this.variableChangeId.add(id);
          if (componentRef) {
            // 关键：通过组件实例的location移动DOM，而非直接insertBefore
            componentRef.location.nativeElement.remove(); // 从原位置移除
            curNode.parentNode.removeChild(curNode.nextSibling);
            const wrapper = document.createElement('span');
            wrapper.style.letterSpacing = '0px';
            wrapper.contentEditable = 'false';
            wrapper.appendChild(componentRef.location.nativeElement); // 添加到新行
            nextNode.appendChild(wrapper);
          } else {
            nextNode.insertBefore(curNode.lastChild, nextNode.firstChild);
          }
        } else {
          nextNode.insertBefore(curNode.lastChild, nextNode.firstChild);
        }
      }
      curNode.parentNode?.removeChild(curNode);
      // 恢复光标位置
      const range = document.createRange();
      range.setStart(startContainer, offset);
      range.collapse(true);
      selection.removeAllRanges();
      selection.addRange(range);
    }
    this.emptyFillDiv();
  }

  /**
   * 设置插入器位置
   * @param isInSelection 是否定位在光标处
   */
  setInserterPosition(isInSelection: boolean = false) {
    // 广播当前打开的插入器id
    this.variableServ.setId(this.variableInserterId);
    if (isInSelection) {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        // 获取 variableInsertRef 的 ElementRef
        const insertRef = this.variableInsertRef.nativeElement;
        // 设置 variableInsertRef 的位置
        insertRef.style.position = 'fixed';
        insertRef.style.top = `${rect.bottom + 5}px`; // 在光标下方 5px
        insertRef.style.left = `${rect.left}px`; // 与光标对齐
      }
    } else {
      // 获取editorContainer的DOM节点
      const editorElement = this.editorContainer.element.nativeElement;
      // 获取editorContainer的位置
      const editorRect = editorElement.getBoundingClientRect();
      // 获取variableInsertRef的ElementRef
      const insertRef = this.variableInsertRef.nativeElement;
      // 设置variableInsertRef的位置，使其位于editorContainer右上角
      insertRef.style.position = 'fixed';
      insertRef.style.top = `${editorRect.top - 12}px`;
      insertRef.style.left = `${editorRect.right - 92}px`;
    }
  }
}
