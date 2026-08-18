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
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import flowCommonLogic from '../../../../../agent-center/app-flow/common-logic-workflow';
import { v4 as uuidV4 } from 'uuid';
import { cdnAssetUrl } from '../../../../../../single-spa/assets-url';
import { CommonUtils } from '../../../../../../utils/common.util';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'image2text-output',
  templateUrl: './image2text-output.component.html',
  styleUrls: ['./image2text-output.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    AppMarkdownAnswerComponent,
  ],
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
export class Image2textOutputComponent {
  public changeUrl = cdnAssetUrl;

  @Input() serviceInfo: any = {
    name: '',
    logo: '',
    id: '',
  };

  @Input() settingInfo: any = {
    stream_val: true,
    securityVerify: false,
  };

  @Input() param: any = {
    uploadData: [],
    content: '',
  };

  @ViewChild('chatContainerRef') chatContainerRef!: ElementRef;

  public isShowStopIcon = false;

  public isRequesting = false;

  public isLoading = false;

  public uuid = uuidV4();

  public isTimeoutOrError = false;

  public lang = CommonUtils.getLanguage();

  private destroy$ = new Subject<void>();

  private sseInstance: any;

  private abortController: AbortController;

  /** 表示用户是否向上滚动 */
  private isUserScrolling = false;

  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;
  /** 记录当前模型服务，修改配置时，不重置聊天*/
  private currentServiceId = '';

  public result = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private jiuwenModelServ: JiuwenModelService,
    private message: NzMessageService,
  ) {}

  uploadData = [];

  ngOnInit() {}

  ngOnChanges(): void {
    if (this.currentServiceId !== this.serviceInfo?.id) {
      this.currentServiceId = this.serviceInfo?.id ?? '';
      this.clearChat();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public sendQuestion() {
    if (this.param.uploadData) {
      this.uploadData = [...this.param.uploadData];
    }
    this.clearChat();
    this.result = '';
    this.isUserScrolling = false;
    this.scrollToBottom();
    const messages = this.getDebugRunParam();
    this.postChat(messages);
    this.cdr.markForCheck();
  }

  public clearChat() {
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.isLoading = false;
  }

  private getDefaultConfig() {
    return {
      max_tokens: 2048,
      temperature: 0.5,
      top_p: 0.5,
      presence_penalty: 0,
      frequency_penalty: 0,
    };
  }

  private getChatParam(msg: any) {
    const messages = [];
    messages.push(msg);
    let thinking = {type: ''}
    if (this.settingInfo.thinking) {
      thinking.type = 'enabled'
    }else{
      thinking.type = 'disabled'
    }
    const params:any = {
      model: this.serviceInfo.id,
      stream: this.settingInfo.stream_val,
      messages,
      ...this.getDefaultConfig(),
      content_security_verify: {
        is_response_verify: this.settingInfo.securityVerify,
        is_request_verify: this.settingInfo.securityVerify,
      },
    }
    if(this.serviceInfo.is_reasoning){
      params.thinking = thinking
    }
    return params;
  }

  private postChat(messages) {
    this.isRequesting = true;
    this.isLoading = true;
    this.isShowStopIcon = true;
    this.isTimeoutOrError = false;
    this.isUserScrolling = false;
    const param = this.getChatParam(messages);
    if (this.settingInfo.stream_val) {
      this.postStream(param);
    } else {
      this.postMessage(param);
    }
  }
  private scrollToBottom() {
    if (!this.isUserScrolling) {
      setTimeout(() => {
        this.chatContainerRef.nativeElement.scrollTop =
          this.chatContainerRef.nativeElement.scrollHeight;
      }, 0);
    }
  }
  private postMessage(param) {
    this.abortController = new AbortController();
    this.jiuwenModelServ
      .modelTestChat(param, this.abortController?.signal)
      .then(({ content }) => {
        this.result = content;
        this.scrollToBottom();
      })
      .finally(() => {
        this.isRequesting = false;
        this.isLoading = false;
        this.isShowStopIcon = false;
        this.cdr.markForCheck();
      });
  }

  private postStream(param) {
    this.sseInstance = this.jiuwenModelServ.modelTestChatSSE(
      param,
      this.lang,
      {
        onMessage: (token: any) => {
          try {
            const chunkDataObj =
              token.data && flowCommonLogic.stringToObject(token?.data);
            const event = chunkDataObj.choices ? 'message' : 'error';
            const info = chunkDataObj?.choices[0]?.delta || chunkDataObj?.choices[0]?.message
            const content =
              info?.content ??
              info?.reasoning_content ?? '';

            if (event === 'error') {
              this.result += content;
            }

            if (event === 'message') {
              if (content) {
                this.isLoading = false;
              }
              this.result += content;
            }
          } catch (error) {}
          this.scrollToBottom();
          if (this.isRequesting) {
            this.isShowStopIcon = true;
          }
          this.cdr?.markForCheck();
        },
        onDone: () => {
          this.isRequesting = false;
          this.isLoading = false;
          this.isShowStopIcon = false;
          this.cdr.markForCheck();
        },
        onError: (error: { data: string; status: any }) => {
          this.isRequesting = false;
          this.isLoading = false;
          this.isShowStopIcon = false;
          this.isTimeoutOrError = true;
          // SSE 基类 dispatchEvent 已对含 error_code 的错误统一弹窗，
          // 此处仅当无响应体（纯网络层错误）时显示通用错误提示
          if (!error?.data) {
            this.message.error(this.i18n.transform('NetErrorTips'));
          }
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
        onTimeout: () => {
          this.isRequesting = false;
          this.isLoading = false;
          this.isShowStopIcon = false;
          this.isTimeoutOrError = true;
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
      },
    );
  }

  private getDebugRunParam():any {
    const { content, uploadData } = this.param || {};
    if (!uploadData.length) {
      this.message.error(this.i18n.transform('upload_image_first'));
      this.stopChat();
      return null;
    }
    const visionContent = [];
    uploadData.forEach((u) => {
      if (u.url) {
        if (u.type.includes('image')) {
          visionContent.push({
            type: 'image_url',
            image_url: {
              url: u.url,
            },
          });
        } else if (u.type.includes('video')) {
          visionContent.push({
            type: 'video_url',
            video_url: {
              url: u.url,
            },
          });
        }
      }
    });
    visionContent.push({
      type: 'text',
      text: content,
    });
    return {
      role: 'user',
      content: visionContent,
    };
  };

  public stopChat() {
    this.sseInstance?.close();
    this.abortController?.abort();
    this.isRequesting = false;
    this.isLoading = false;
    this.isShowStopIcon = false;
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    const currentScrollTop = target.scrollTop;

    // 判断是否向上滚动
    if (currentScrollTop < this.lastScrollTop) {
      this.isUserScrolling = true; // 停止自动滚动
    } else if (
      currentScrollTop + target?.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false; // 继续自动滚动（当用户手动滚动到最底部）
    }
    this.lastScrollTop = currentScrollTop;
  }
}
