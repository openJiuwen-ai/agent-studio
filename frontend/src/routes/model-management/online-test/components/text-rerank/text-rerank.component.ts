import {
  Component,
  Input,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  HostListener,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { CommonUtils } from '../../../../../utils/common.util';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzTableModule } from 'ng-zorro-antd/table';

@Component({
  selector: 'text-rerank',
  templateUrl: './text-rerank.component.html',
  styleUrls: ['./text-rerank.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    NzTableModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.MODEL_ACCESS,
      ],
    },
  ],
})
export class TextRerankComponent {
  @Input() settingInfo: any = {
    stream_val: true,
    securityVerify: false,
  };

  @Input() serviceInfo: any = {
    name: '',
    logo: '',
    id: '',
  };

  @Input() param: any = {
    textsToRerank: [
      {
        content: '',
      },
    ],
    numOfDisplay: 1,
    question: String,
  };

  @ViewChild('chatContainerRef') chatContainerRef!: ElementRef;

  public isShowStopIcon = false;

  public isRequesting = false;

  public isLoading = false;

  public uuid = uuidV4();

  public isTimeoutOrError = false;

  /** 表示用户是否向上滚动 */
  private isUserScrolling = false;

  public lang = CommonUtils.getLanguage();

  private destroy$ = new Subject<void>();

  private sseInstance: any;

  private abortController: AbortController;

  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;
  /** 记录当前模型服务，修改配置时，不重置聊天*/
  private currentServiceId = '';

  public result: any = '';

  public errorMessage = '';

  public displayedData = [];
  public srcData = {
    data: [],
    state: {
      sorted: true,
      searched: true,
      paginated: true,
    },
  };

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private jiuwenModelServ: JiuwenModelService,
    private message: NzMessageService,
  ) {}
  ngOnInit() {}

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
  ngOnChanges(): void {
    if (this.currentServiceId !== this.serviceInfo?.id) {
      this.currentServiceId = this.serviceInfo?.id ?? '';
      this.clearChat();
    }
  }
  public sendQuestion() {
    this.result = '';
    this.srcData.data = [];
    this.errorMessage = '';
    this.isUserScrolling = false;
    this.scrollToBottom();
    if (!this.getDebugRunParam()) return;
    this.postChat();
    this.cdr.markForCheck();
  }

  public clearChat() {
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.isLoading = false;
  }

  private getChatParam() {
    let docs: Array<String> = [];
    this.param.textsToRerank.forEach((text) => {
      if (text.content?.trim() === '') return;
      docs.push(text.content);
    });
    return {
      model: this.serviceInfo.id,
      query: this.param.question,
      top_n: this.param.numOfDisplay,
      docs: docs,
      content_security_verify: {
        is_response_verify: this.settingInfo.securityVerify,
        is_request_verify: this.settingInfo.securityVerify,
      },
    };
  }

  private postChat() {
    this.isRequesting = true;
    this.isLoading = true;
    this.isShowStopIcon = true;
    this.isTimeoutOrError = false;
    this.isUserScrolling = false;
    const param = this.getChatParam();
    this.postMessage(param);

  }

  private postMessage(param) {
    this.abortController = new AbortController();
    this.jiuwenModelServ
      .modelTestReRank(param, this.abortController?.signal)
      .then((content) => {
        this.result = content;
        const newData = [];
        this.result.forEach((item) => {
          newData.push({
            index: item.index,
            text: item.document.text,
            relevance_score: item.relevance_score,
          });
        });
        this.srcData.data = [...this.srcData.data, ...newData];

        this.scrollToBottom();
      })
      .catch((error) => {
        if (this.abortController?.signal?.aborted) { return; }
        this.result = null;
        this.srcData.data = [];
        this.errorMessage = this.extractErrorMsg(error);
        this.scrollToBottom();
      })
      .finally(() => {
        this.isRequesting = false;
        this.isLoading = false;
        this.isShowStopIcon = false;
        this.cdr.markForCheck();
      });
  }

  /**
   * 从错误响应中提取可展示的错误信息（含上游 details）。
   */
  private extractErrorMsg(error: any): string {
    try {
      const errInfo =
        typeof error?.error === 'string'
          ? JSON.parse(error.error)
          : error?.error || error;
      const errMsg = errInfo?.error_msg || errInfo?.message || '';
      const details = errInfo?.details;
      let detailStr = '';
      if (Array.isArray(details) && details.length > 0) {
        detailStr = details
          .map((d) => d?.error_msg || '')
          .filter((m) => m)
          .join('\n');
      }
      return detailStr || errMsg || this.i18n.transform('NetErrorTips');
    } catch {
      return this.i18n.transform('NetErrorTips');
    }
  }

  private getDebugRunParam() {
    if (this.param?.question.trim() === '') {
      this.message.error(this.i18n.transform('rerank_query_empty'));
      return false;
    }
    let legalAmount = 0;
    for (let item of this.param.textsToRerank) {
      if (item.content?.trim() !== '') {
        legalAmount++;
      }
    }
    if (legalAmount === 0) {
      this.message.error(this.i18n.transform('cannot_sort_empty_text'));
      return false;
    }
    return true;
  }

  public stopChat() {
    this.sseInstance?.close();
    this.abortController?.abort();
    this.isRequesting = false;
    this.isLoading = false;
    this.isShowStopIcon = false;
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  private scrollToBottom() {
    if (!this.isUserScrolling) {
      setTimeout(() => {
        this.chatContainerRef.nativeElement.scrollTop =
          this.chatContainerRef.nativeElement.scrollHeight;
      }, 0);
    }
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    const scrollTop = target.scrollTop;

    // 判断是否向上滚动
    if (scrollTop < this.lastScrollTop) {
      this.isUserScrolling = true; // 停止自动滚动
    } else if (
      scrollTop + target.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false; // 继续自动滚动（当用户手动滚动到最底部）
    }
    this.lastScrollTop = scrollTop;
  }

  public changeUrl = cdnAssetUrl;
}
