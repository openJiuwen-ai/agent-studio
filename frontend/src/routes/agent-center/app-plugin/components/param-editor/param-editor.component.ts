import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ComponentRef,
  forwardRef,
  Input,
  NgZone,
  Optional,
  Renderer2,
} from '@angular/core';
import { NG_VALUE_ACCESSOR } from '@angular/forms';
import { COMMON_MODULES } from '@shared/modules';
import { PromptEditorComponent } from '@routes/prompt/prompt-editor/prompt-editor.component';
import { ParamVariableComponent } from '@routes/agent-center/app-plugin/components/param-editor/param-variable.component';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { VariableService } from '@services/agent-center/prompt-optimize-task/prompt-editor.service';
import { VariableType } from '@interfaces/prompt/prompt-optimize-task.interface';

enum fieldTable {
  InnerHtml = 'innerHTML',
  Id = 'id',
  localName = 'localName'
}

@Component({
  selector: 'meta-param-editor',
  standalone: true,
  imports: [COMMON_MODULES],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ParamEditorComponent),
      multi: true,
    },
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
  templateUrl: './param-editor.component.html',
  styleUrl: './param-editor.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ParamEditorComponent extends PromptEditorComponent {
  @Input('placeholder') placeholder = this.i18n.transform('param-editor-1');
  @Input() override style: any;
  constructor(
    private readonly i18n: angularI18next.I18NextEagerPipe,
    @Optional() cdr?: ChangeDetectorRef,
    @Optional() ngZone?: NgZone,
    @Optional() variableServ?: VariableService,
    @Optional() renderer?: Renderer2,
  ) {
    super(cdr, ngZone, variableServ, renderer);
  }

  // 变量实例收集
  protected override variableInstanceMap = new Map<
    string,
    ComponentRef<ParamVariableComponent>
  >();
  override metaVariable = 'meta-param-variable';

  protected override handleEnter(event: KeyboardEvent) {
    event.preventDefault();
    event.stopPropagation();
  }

  protected override emptyFillDiv() {
    setTimeout(() => {
      if (this.editorContainer.element?.nativeElement.innerText === '') {
        //为空则添加一个div
        const newLine = this.renderer.createElement('div');
        this.renderer.addClass(newLine, 'line');
        const wrapper = this.renderer.createElement('span');
        this.renderer.setStyle(wrapper, 'letterSpacing', '0px');
        this.renderer.appendChild(newLine, wrapper);
        this.renderer.setProperty(
          this.editorContainer.element?.nativeElement,
          fieldTable.InnerHtml,
          '',
        );
        this.renderer.appendChild(
          this.editorContainer.element?.nativeElement,
          newLine,
        );
      }
    }, 0);
  }

  public override prompt2chunks(prompt: string): typeof this.promptChunk {
    const chunks = [];
    const variableRegex = /\{(.*?)}/g;
    let match;
    let lastIndex = 0;
    let variableChange = false;
    let diffResult;
    // 按 \n 分割字符串
    const lines = prompt
      .replaceAll('\r', '\n')
      .replaceAll('\r\n', '\n')
      .split('\n');

    if (this.highlight) {
      const compareLines = this.compareContent
        .replaceAll('\r', '\n')
        .replaceAll('\r\n', '\n')
        .split('\n');
      diffResult = this.calculateDiff(compareLines, lines);
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
        continue;
      }

      lastIndex = 0;
      while ((match = variableRegex.exec(line)) !== null) {
        const start = match.index;
        const end = variableRegex.lastIndex;

        if (start > lastIndex) {
          lineChunks.push({
            type: 'text',
            value: line?.substring(lastIndex, start),
          });
        }

        lineChunks.push({ type: 'variable', value: match[1] });

        if (!this.variableMap?.has(match[1].trim())) {
          // 如果提示词存在未传入的变量，则同步更新
          this.variableMap.set(match[1].trim(), {
            type: VariableType.TEXT,
            count: 1,
          });
          variableChange = true;
        } else {
          // 如果已经存在，则计数加一
          const variableInfo = this.variableMap.get(match[1]);
          variableInfo.count++;
        }
        lastIndex = end;
      }
      if (lastIndex < prompt.length) {
        lineChunks.push({ type: 'text', value: line?.substring(lastIndex) });
      }
    }

    if (variableChange) {
      //如果变量改变
      this.updateVariable();
    }
    return chunks;
  }

  public override html2prompt(container) {
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
            result += `{${variable}}`;
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
        }
      }
    }
    if (container === this.editorContainer.element.nativeElement) {
      // 最终结果去掉结尾\n
      return result.slice(0, -1);
    }
    return result;
  }

  protected override createComponent() {
    return this.editorContainer.createComponent(ParamVariableComponent);
  }
}
