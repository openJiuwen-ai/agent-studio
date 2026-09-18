import {
  Component,
  OnInit,
  Input,
  ViewChild,
  ElementRef,
  Output,
  EventEmitter,
  SimpleChanges,
  HostListener,
  TemplateRef,
  AfterViewInit,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAnswerResolverService } from '@services/knowledge-center/kb-answer-resolver.service';
import { MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { marked } from 'marked';
import hljs from 'highlight.js';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { katexExtends } from 'src/utils/render-LaTeX-Markdown';
import { NzModalService } from 'ng-zorro-antd/modal';
import { Clipboard } from '@angular/cdk/clipboard';
import DOMPurify from 'dompurify';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import {
  messageSourceFileMap,
  getFileExtension,
} from '@routes/agent-center/app-agent/components/chat-item/chat-item.enum';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';

type EventListener = (event: Event) => void;

@Component({
  selector: 'app-markdown-answer',
  templateUrl: './app-markdown-answer.component.html',
  styleUrls: ['./app-markdown-answer.component.less'],
  standalone: true,
  imports: [CommonModule, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AppMarkdownAnswerComponent
  implements OnInit, AfterViewInit, OnDestroy
{
  @Input() isThought = false;
  @Input() answer = '';

  @Input() sourceMessage;

  @Input() isError? = false;

  // 是否支持对回答的知识库相关内容进行解析
  @Input() isSupKBResolver = false;

  @Input() typewriter=false;

  // 是否是发布态
  @Input() isRuntime = false;

  @Output() emitOutput = new EventEmitter();

  @Output() answerChange = new EventEmitter();

  @ViewChild('textareaRef', { static: false }) textareaRef!: ElementRef;

  @ViewChild('alertModal')
  readonly alertModal?: TemplateRef<HTMLDivElement>;

  transformedAnswer: SafeHtml;

  isEditing = false;

  url: any = '';

  private updateSubject = new Subject<void>();

  firstChange = true; //首次直接渲染，防止先出现空白对话框

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.typewriter) {
      this.typewriter = changes.typewriter.currentValue
    }
    if (changes.answer) {
      if (this.firstChange) {
        if (this.typewriter) {
          let currentAns=''
          for (let i = 0; i < this.answer.length; i++) {
            const char = this.answer[i]
            currentAns += char;
            setTimeout(() => {
              this.transform(currentAns);
            }, 50);
          }
        } else {
          this.transform();
        }

        this.onNewResponseReceived();
        this.firstChange = false;
      } else {
        this.updateSubject.next();
      }
    }
  }

  ngOnInit() {}

  copyCode(event: any, numOfCopyIcon: number, code: any) {
    this.clipboard.copy(code);
    const parentElement = event.parentElement;
    const copySuccessTooltip = parentElement?.querySelector(
      '.copy-success-tooltip',
    );

    if (copySuccessTooltip) {
      copySuccessTooltip.style.display = 'block';
      setTimeout(() => {
        copySuccessTooltip.style.display = 'none';
      }, 600);
    }
  }

  private tooltip: HTMLElement | null = null;
  private eventListeners: Map<
    Element,
    {
      mouseenter: EventListener;
      mouseleave: EventListener;
      mousemove: EventListener;
    }
  > = new Map();

  ngAfterViewInit() {
    this.bindReferenceEventListeners(); // 初始绑定
  }

  onNewResponseReceived() {
    // 等待 DOM 更新完成提示词
    setTimeout(() => {
      this.bindReferenceEventListeners();
    }, 0);
  }

  private bindReferenceEventListeners() {
    const targetElements = document.querySelectorAll('span[id^="reference"]');
    this.tooltip = document.getElementById('tooltip');

    if (!this.tooltip) {
      this.tooltip = document.createElement('div');
      this.tooltip.id = 'tooltip';
      this.tooltip.className = 'tooltip';
      document.body.appendChild(this.tooltip);
    }

    // 清除旧的监听器（防止重复绑定）
    this.removeEventListeners();

    targetElements.forEach((element: any) => {
      element.style.marginLeft = '3px';
      element.style.display = 'inline-flex';
      element.style.justifyContent = 'center';
      element.style.width = '16px';
      element.style.height = '16px';
      element.style.lineHeight = '23px';
      element.style.fontSize = '16px';
      element.style.borderRadius = '50%';
      element.style.fontWeight = '600';
      element.style.backgroundColor = 'rgba(0, 0, 0, 0.04)';
      element.style.transform = 'translateY(4px)';
      element.addEventListener('mouseenter', () => {
        element.style.color = '#1476FF';
        element.style.backgroundColor = 'rgba(20, 118, 255, 0.1)';
      });
      element.addEventListener('mouseleave', () => {
        element.style.color = 'black';
        element.style.backgroundColor = 'rgba(0, 0, 0, 0.04)';
      });

      const mouseenterHandler: EventListener = (e: Event) => {
        const target = e.target as HTMLElement; // 推荐：获取实际触发事件的元素
        const id = target.id;
        let retrievalId = '';
        target.classList.forEach((item) => {
          const id = this.getRetrievalIds(item);
          if (id) {
            retrievalId = id;
          }
        });
        const sourceFile = this.findSourceFile(
          this.sourceMessage,
          this.getIdAfterUnderscore(id),
          retrievalId,
        );
        if (!sourceFile?.length) {
          return;
        }
        let name = sourceFile?.[0]?.document_name;
        let mainContent = this.resolveKbImage(sourceFile?.[0]?.content ?? '');
        let score = parseFloat(sourceFile?.[0]?.score.toFixed(2));
        let imgurl = this.cdnUrl(
          this.messageSourceFileMap.get(this.getFileExtension(name)),
        );
        this.tooltip!.innerHTML = `<div><div style="display: flex;margin-bottom: 12px"><img src="${imgurl}" style="width: 24px;height: 24px;margin-right: 8px" alt="" /><span style="margin-top: 3px;line-height: 1.6; display: -webkit-box;-webkit-line-clamp: 1;-webkit-box-orient: vertical;overflow: hidden;text-overflow: ellipsis;">${name}</span></div>
<div style="line-height: 1.6; display: -webkit-box;-webkit-line-clamp: 5;-webkit-box-orient: vertical;overflow: hidden;text-overflow: ellipsis;">${mainContent}</div>
<div style="margin-top: 12px;display: flex"><div style="margin-right: 12px"><span style="color:#808080;margin-right: 4px;">${this.i18n.transform(
          'hit_score',
        )}</span><span style="font-weight: 700">${score}</span></div><div><span style="color:#808080;margin-right: 4px;">${this.i18n.transform(
          'word_count',
        )}</span><span style="font-weight: 700;color: #191919">${
          mainContent?.length
        }</span></div></div></div>`;
        this.tooltip!.classList.add('visible');
      };

      const mouseleaveHandler: EventListener = () => {
        this.tooltip!.classList.remove('visible');
      };

      const mousemoveHandler: EventListener = (e: Event) => {
        const mouseEvent = e as MouseEvent;
        const tooltipElement = this.tooltip!;
        const tooltipRect = tooltipElement.getBoundingClientRect();
        const mouseX = mouseEvent.clientX;
        const mouseY = mouseEvent.clientY;

        // 左侧 + 下方定位
        tooltipElement.style.left = `${mouseX - tooltipRect.width - 10}px`;
        tooltipElement.style.top = `${mouseY + 10}px`;
      };

      element.addEventListener('mouseenter', mouseenterHandler);
      element.addEventListener('mouseleave', mouseleaveHandler);
      element.addEventListener('mousemove', mousemoveHandler);

      // 存储监听器以便后续移除
      this.eventListeners.set(element, {
        mouseenter: mouseenterHandler,
        mouseleave: mouseleaveHandler,
        mousemove: mousemoveHandler,
      });
    });
  }

  private getRetrievalIds(str: string): string {
    if (str?.includes('retrieval-id')) {
      return str.split('-')[2];
    }
    return '';
  }

  // 清除所有监听器
  private removeEventListeners() {
    this.eventListeners.forEach((listeners, element) => {
      element.removeEventListener('mouseenter', listeners.mouseenter);
      element.removeEventListener('mouseleave', listeners.mouseleave);
      element.removeEventListener('mousemove', listeners.mousemove);
    });
    this.eventListeners.clear();
  }

  ngOnDestroy() {
    this.removeEventListeners();
    if (this.tooltip && this.tooltip.parentNode) {
      this.tooltip.parentNode.removeChild(this.tooltip);
    }
  }

  constructor(
    private el: ElementRef,
    private i18n: angularI18next.I18NextEagerPipe,
    private sanitizer: DomSanitizer,
    private nzModalService: NzModalService,
    private clipboard: Clipboard,
    private knowledgeRepoService: KnowledgeRepoService,
    private kbAnswerResolverService: KbAnswerResolverService,
  ) {
    this.updateSubject.pipe(debounceTime(5)).subscribe((searchTerm) => {
      this.transform();
      this.onNewResponseReceived();
    });
  }

  findSourceFile(array, targetSerialNumber, retrievalId) {
    return array?.filter(
      (item) =>
        item.serial_number === targetSerialNumber &&
        item.retrieval_id === retrievalId,
    );
  }

  getInsideBrackets(str) {
    const start = str.indexOf('[');
    const end = str.indexOf(']');
    return str.substring(start + 1, end);
  }

  getIdAfterUnderscore(str) {
    return Number(str.split('_')[1]);
  }

  transform(typeAnswer?:string) {
    // 注册KaTeX渲染功能
    const { extensions } = katexExtends();
    // 自定义 marked 解析规则，禁止单 `~` 被解析为删除线
    const delRule: any = {
      name: 'no-single-tilde',
      level: 'inline',
      start(src) {
        return src.match(/~[^~]/)?.index; // 查找单个 `~`
      },
      tokenizer(src, tokens) {
        const match = src.match(/^~([^~]+)~/);
        if (match) {
          return {
            type: 'text',
            raw: match[0],
            text: match[0], // 让 `~xxx~` 保持原样
          };
        }
        return undefined;
      },
    };
    extensions.push(delRule);
    marked.use({ extensions });
    // 创建一个新的渲染器
    let renderer = new marked.Renderer();
    let codeBlockCounter = 0;

    // 重写代码块的渲染方法
    renderer.code = (code: any, language: any) => {
      // 使用highlight.js进行代码高亮
      const validLanguage = hljs.getLanguage(language) ? language : 'plaintext';
      const highlightedCode = hljs.highlight(validLanguage, code).value;

      // 分割代码为多行
      let lines = highlightedCode.split('\n');

      // 若language存在，为每一行添加行号
      let numberedCode = language
        ? lines
            .map((line: any, index: any) => {
              return `<span class="line-numbers">${index + 1}</span> ${line}`;
            })
            .join('\n')
        : highlightedCode;

      // <code>标签可能表示代码，也可能表示表格。通过language的值是否存在进行区分
      let customCodeStyle = language
        ? `${language} custom-code-content`
        : `table-code`;

      const copiedText = this.i18n.transform('replicated_tip');
      const copyText = this.i18n.transform('base_copy');
      // 如果language存在，返回带有语言类型、复制图标和行号的代码块；反之，不展示语言类型、复制图标和行号
      let result = language
        ? `<pre class="code-wrapper">
           <div class="code-header">
           <span class="language-type">${language}</span>
           <span class="copy-container-markdown"><span class="copy-success-tooltip">${copiedText}</span><span class="copy-icon copy-${language}-${codeBlockCounter}" data-code="${encodeURIComponent(
            code,
          )}">${copyText}</span></span>
           </div>
           <code class="${customCodeStyle}">${numberedCode}</code>
           </pre>`
        : `<pre class="not-code-wrapper">
           <code class="${customCodeStyle}">${numberedCode}</code>
           </pre>`;

      codeBlockCounter++;
      return result;
    };

    renderer.table = (header: string, body: string) => {
      return `<div class="custom-table-container">
        <table class="custom-table-style">
          <thead>${header}</thead>
          <tbody>${body}</tbody>
        </table>
      </div>`;
    };

    renderer.link = (href, title, text) => {
      return `<a href="${href}" target="_blank" class="custom-link">${text}</a>`;
    };

    // 设置自定义渲染器
    marked.setOptions({ renderer, breaks: true });
    let currentAns;
    if(typeAnswer){
      currentAns = typeAnswer
    }else{
      currentAns = this.answer;
    }


    // 对知识库相关引用进行处理
    if (this.isSupKBResolver) {
      currentAns = this.resolveKbImage(currentAns);
    }

    currentAns = currentAns.replaceAll(/\\/g, '\\\\');

    let intermediateValue;
    // 暂无可用的增量markdown解析库，先保证50000字符内的正确解析和长文本不卡死,排除base64
    const chunkSize = 50000;
    if (
      currentAns.length <= chunkSize ||
      currentAns.includes('common-image-in-kb') ||
      this.containsBase64Image(currentAns)
    ) {
      intermediateValue = marked(currentAns);
    } else {
      const parts = this.splitAnswer(currentAns, chunkSize);
      intermediateValue = parts.map((item) => marked(item)).join('');
    }

    // 使用DOMPurify消除XSS攻击
    const purifiedHtml = DOMPurify.sanitize(intermediateValue);
    this.transformedAnswer =
      this.sanitizer.bypassSecurityTrustHtml(purifiedHtml);
  }

  /** 使用 HostListener 监听每个代码块的点击事件 */
  @HostListener('click', ['$event'])
  onClick(event: MouseEvent) {
    const target = event.target as HTMLElement;

    if (target.classList.contains('copy-icon')) {
      const code = decodeURIComponent(target.getAttribute('data-code') || '');
      const copyIcons = this.el.nativeElement.querySelectorAll('.copy-icon');
      if (code) {
        this.copyCode(target, copyIcons.length, code);
      }
    }
  }

  public onClickHref(href: string) {
    this.nzModalService.create({
      nzTitle: '',
      nzContent: this.alertModal,
      nzData: {
        href,
      },
      nzFooter: null,
    });
  }

  public openHrefInNewTab(link: string) {
    window.open(link, '_blank');
  }

  resolveKbImage(content: string): string {
    return this.kbAnswerResolverService.resolveImage(content, (imgId) =>
      this.knowledgeRepoService.queryImage(imgId),
    );
  }

  /** 按照最大限制，拆分输入字符串 */
  private splitAnswer(answer: string, maxSize: number) {
    const parts = [];
    for (let start = 0; start < answer.length; start += maxSize) {
      parts.push(answer.slice(start, start + maxSize));
    }
    return parts;
  }

  /** 检查是否有base64字符串 */
  private containsBase64Image(text: string) {
    // 匹配常见的 Base64 图片格式
    const pattern =
      /data:image\/(?:png|jpeg|jpg|gif|bmp|webp|svg\+xml);base64,[A-Za-z0-9+/=]+/i;
    return pattern.test(text);
  }

  public cdnUrl = cdnAssetUrl;

  public async typeWriter(text, curText, index, delay) {

  }

  protected readonly messageSourceFileMap = messageSourceFileMap;
  protected readonly getFileExtension = getFileExtension;
}
