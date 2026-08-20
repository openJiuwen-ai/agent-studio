import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  Input,
  ViewChild,
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

@Component({
  selector: 'text-embedding',
  templateUrl: './text-embedding.component.html',
  styleUrls: ['./text-embedding.component.scss'],
  standalone: true,
  imports: [CommonModule, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.AGENT,
        I18nNamespace.MODEL_ACCESS,
      ],
    },
  ],
})
export class TextEmbeddingComponent {
  public changeUrl = cdnAssetUrl;

  @Input() serviceInfo: any = {
    name: '',
    id: '',
    logo: ''
  };

  @Input() settingInfo: any = {
    securityVerify: false,
    stream_val: true,
  };

  @Input() param: any = {
    content: '',
  };
  public isShowStopIcon = false;

  @ViewChild('chatContainerRef') chatContainerRef!: ElementRef;

  public isLoading = false;

  public uuid = uuidV4();

  public isRequesting = false;

  public isTimeoutOrError = false;

  public lang = CommonUtils.getLanguage();

  private destroy$ = new Subject<void>();

  private abortController: AbortController;

  private sseInstance: any;

  /** 表示用户是否向上滚动 */
  private isUserScrolling = false;
  /** 记录当前模型服务，修改配置时，不重置聊天*/
  private currentServiceId = '';
  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;


  public result = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private jiuwenModelServ: JiuwenModelService,
    private message: NzMessageService,
  ) {}

  ngOnInit() {}

  ngOnChanges(): void {
    if (this.currentServiceId !== this.serviceInfo?.id) {
      this.currentServiceId = this?.serviceInfo?.id ?? '';
      this.clearChat();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public copyToClipboard() {
    navigator.clipboard.writeText(this.result).then(() => {
      this.message.success(this.i18n.transform('copy_success'));
    });
  }

  public sendQuestion() {
    this.result = '';
    this.isUserScrolling = false;
    this.scrollToBottom();
    if (!this?.getDebugRunParam()) return;
    this.postChat();
    this.cdr.markForCheck();
  }

  public clearChat() {
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.isLoading = false;
    this.result = '';
  }

  private getChatParam() {
    return {
      model: this.serviceInfo.id,
      input: this.param.content,
      content_security_verify: {
        is_response_verify: this.settingInfo.securityVerify,
        is_request_verify: this.settingInfo.securityVerify,
      },
    };
  }

  private postChat() {
    this.isShowStopIcon = true;
    this.isTimeoutOrError = false;
    this.isUserScrolling = false;
    this.isRequesting = true;
    this.isLoading = true;
    const param = this.getChatParam();
    this.postMessage(param);
  }

  private postMessage(param) {
    this.abortController = new AbortController();
    this.jiuwenModelServ
      .modelTestEmbedding(param, this.abortController?.signal)
      .then((content) => {
        this.result = `[${String(content[0]?.embedding)}]`;
        this.scrollToBottom();
      })
      .catch((error) => {
        if (this.abortController?.signal?.aborted) { return; }
        this.result = this.extractErrorMsg(error);
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
    const content = this.param?.content || '';
    if (content === '') {
      this.message.error(this.i18n.transform('text_input'));
      return false;
    }
    return true;
  }

  private scrollToBottom() {
    if (!this.isUserScrolling) {
      setTimeout(() => {
        this.chatContainerRef.nativeElement.scrollTop =
          this.chatContainerRef?.nativeElement?.scrollHeight;
      }, 0);
    }
  }

  public stopChat() {
    this.sseInstance?.close();
    this.abortController?.abort();
    this.isRequesting = false;
    this.isLoading = false;
    this.isShowStopIcon = false;
    this?.scrollToBottom();
    this.cdr.markForCheck();
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    const current_scroll_top = target.scrollTop;

    if (this.lastScrollTop > current_scroll_top) {
      this.isUserScrolling = true; // 停止自动滚动
    } else if (
      current_scroll_top + target.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false; // 继续自动滚动（当用户手动滚动到最底部）
    }
    this.lastScrollTop = current_scroll_top;
  }
}
