import {
  Component,
  Input,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  HostListener,
  OnChanges,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';
import { CommonUtils } from 'src/utils/common.util';
import { TextFieldModule } from '@angular/cdk/text-field';
import flowCommonLogic from '../../../../agent-center/app-flow/common-logic-workflow';
import { ModelChatItemComponent } from '@routes/model-management/online-test/components/chat-item/chat-item.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { ModelSenderComponent } from '@routes/model-management/online-test/components/sender/sender.component';
import { ModelType } from '@enums/jiuwen-model.enum';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzGridModule } from 'ng-zorro-antd/grid';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzIconModule } from 'ng-zorro-antd/icon';

@Component({
  selector: 'model-service-compare-router',
  templateUrl: './model-service-compare-router.component.html',
  styleUrls: ['./model-service-compare-router.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    ModelChatItemComponent,
    ModelSenderComponent,
    NzGridModule,
    NzToolTipModule,
    NzIconModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT,
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.MODEL_ACCESS,
        I18nNamespace.AGENT_CENTER,
      ],
    },
  ],
})
export class ModelServiceCompareRouter implements OnChanges, OnInit {
  public changeUrl = cdnAssetUrl;

  @Input() serviceInfo: any = [
    {
      name: '',
      logo: '',
      id: '',
      is_reasoning:false
    },
  ];
  @Input() modelType: string = ModelType.LLM;

  @Input() config = [];
  @Input() securityVerify = false;

  @Input() settingInfo = {
    stream_val: true,
    securityVerify: false,
    thinking:false
  };

  @ViewChild('chatContainerLeftRef') chatContainerLeftRef!: ElementRef;
  @ViewChild('chatContainerRightRef') chatContainerRightRef!: ElementRef;

  public isShowStopIcon = false;

  /** 预置的prompt */
  public presetPrompt = this.i18n.transform('vm_preset_prompt', {
    ns: I18nNamespace.JIUWEN_MODEL,
  });
  public dialogHistory: any[][][] = [
    [
      [
        {
          role: 'system',
          content: this.presetPrompt,
        },
      ],
    ],
    [
      [
        {
          role: 'system',
          content: this.presetPrompt,
        },
      ],
    ],
  ];

  public sendDisabled = false;

  public isRequesting = false;

  public isLoading: Array<boolean> = [false, false];

  public uuid = uuidV4();

  public isTimeoutOrError = false;

  public userQueryLimit: number;

  public lang = CommonUtils.getLanguage();

  private destroy$ = new Subject<void>();

  private sseInstance: Array<any> = [];

  private abortController: AbortController;

  /** 表示用户是否向上滚动 */
  private isUserScrolling = false;

  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private jiuwenModelServ: JiuwenModelService,
    private configServ: AgentConfigService,
    private message: NzMessageService,
  ) {}

  ngOnInit() {
    this.userQueryLimit =
      this.configServ.getConfigs().user_query_limit ?? 100000;
    this.serviceInfo = [];
  }

  ngOnChanges(changes): void {
    if (changes.serviceInfo) {
      this.clearChat();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public sendQuestion(chatContent: any) {
    const oneChat = [chatContent];
    this.dialogHistory[0].push(oneChat);
    this.dialogHistory[1].push(oneChat);
    this.isUserScrolling = false;
    this.scrollToBottom();
    if (!this.getDebugRunParam()) return;
    this.postChat(this.dialogHistory[0].length - 1);
    this.cdr.markForCheck();
  }

  /** 点击底部的清空对话，开启新聊天 */
  public clearChat() {
    this.sseInstance.forEach((item) => item.close()); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.dialogHistory = [
      [
        [
          {
            role: 'system',
            content: this.presetPrompt,
          },
        ],
      ],
      [
        [
          {
            role: 'system',
            content: this.presetPrompt,
          },
        ],
      ],
    ]; // 置空页面主体的多轮对话
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.isLoading = [false, false];
  }

  private getChatConfig() {
    const result = {};
    this.config.forEach((c) => {
      result[c.name] = c.value;
    });
    return result;
  }

  private getChatParam() {
    const configObj = this.getChatConfig();
    const messages = [];
    const returnArr = [];
    this.serviceInfo.forEach((service, currentWindow) => {
      messages.push([]);
      this.dialogHistory[currentWindow].forEach((his, index) => {
        // 第一个系统提示词不加入对话历史
        if (index >= 1) {
          his.forEach((h) => {
            messages[currentWindow].push({
              role: h.role,
              content: h.content,
            });
          });
        }
      });
      let thinking = {type: ''}
      if (this.settingInfo.thinking) {
        thinking.type = 'enabled'
      }else{
        thinking.type = 'disabled'
      }
      const m:any = {
        model: service.id,
        stream: this.settingInfo.stream_val,
        messages: messages[currentWindow],
        ...configObj,
        content_security_verify: {
          is_response_verify: this.settingInfo.securityVerify,
          is_request_verify: this.settingInfo.securityVerify,
        },
      }
      if(service.is_reasoning){
        m.thinking = thinking
      }
      returnArr.push(m);
    });
    return returnArr;
  }

  private postChat(currentIndex: number) {
    this.isRequesting = true;
    this.isShowStopIcon = true;
    this.isTimeoutOrError = false;
    this.isUserScrolling = false;
    const param = this.getChatParam();
    if (this.settingInfo.stream_val) {
      this.postStream(param, currentIndex);
    } else {
      this.postMessage(param, currentIndex);
    }
  }

  progressError(error, currentIndex, currentWindow) {
    // 兼容 SSE 路径（error.data）和非流式路径（HttpErrorResponse，数据在 error.error）
    const errorData = error?.data ?? error?.error;
    if (errorData) {
      try {
        let errInfo;
        if (typeof errorData === 'string') {
          errInfo = JSON.parse(errorData);
        } else {
          errInfo = errorData;
        }
        const content = errInfo.error_msg;
        let assistantMessage = this.dialogHistory[currentWindow][
          currentIndex
        ].find((item) => item.role === 'assistant');
        if (assistantMessage) {
          assistantMessage.content = content;
          assistantMessage.isError = true;
          assistantMessage.errorContent = JSON.stringify(
            errInfo.details || this.i18n.transform('unknown_reason')
          );
          assistantMessage.errorIsOpen = true;
        } else {
          assistantMessage = {
            role: 'assistant',
            content,
            isError: true,
            errorContent: JSON.stringify(errInfo.details || this.i18n.transform('unknown_reason')),
            errorIsOpen: true,
          };
          this.dialogHistory[currentWindow][currentIndex] = [
            ...this.dialogHistory[currentWindow][currentIndex],
            assistantMessage,
          ];
        }
      } catch {
        const errRaw = error?.data ?? error?.error ?? error;
        const content = errRaw?.error_msg || this.i18n.transform('third_party_model_call_error');
        let assistantMessage = this.dialogHistory[currentWindow][
          currentIndex
        ].find((item) => item.role === 'assistant');
        if (assistantMessage) {
          assistantMessage.content = content;
          assistantMessage.isError = true;
          assistantMessage.errorContent = JSON.stringify(
            errRaw?.details || this.i18n.transform('unknown_reason'),
          );
          assistantMessage.errorIsOpen = true;
        } else {
          assistantMessage = {
            role: 'assistant',
            content,
            isError: true,
            errorContent: JSON.stringify(errRaw?.details || this.i18n.transform('unknown_reason')),
            errorIsOpen: true,
          };
          this.dialogHistory[currentWindow][currentIndex] = [
            ...this.dialogHistory[currentWindow][currentIndex],
            assistantMessage,
          ];
        }

        this.message.error(this.i18n.transform('NetErrorTips'));
      }
    }
  }

  private postMessage(params: Array<Object>, currentIndex: number) {
    params.forEach((param, currentWindow) => {
      this.abortController = new AbortController();
      this.isLoading[currentWindow] = true;
      this.jiuwenModelServ
        .modelTestChat(param, this.abortController?.signal)
        .then(({ content, reasoning_content }) => {
          let assistantMessage = {
            role: 'assistant',
            content,
            reasoning_content,
            done: true,
          };
          this.dialogHistory[currentWindow][currentIndex] = [
            ...this.dialogHistory[currentWindow][currentIndex],
            assistantMessage,
          ];
          this.dialogHistory[currentWindow] = [
            ...this.dialogHistory[currentWindow].slice(0, currentIndex),
            this.dialogHistory[currentWindow][currentIndex],
            ...this.dialogHistory[currentWindow].slice(currentIndex + 1),
          ];
          this.scrollToBottom();
        })
        .catch((e) => {
          this.progressError(e, currentIndex, currentWindow);
        })
        .finally(() => {
          this.isLoading[currentWindow] = false;
          if (!this.isLoading[1 - currentWindow]) {
            this.isShowStopIcon = false;
            this.isRequesting = false;
          }
          this.cdr.markForCheck();
        });
    });
  }

  private postStream(params: Array<Object>, currentIndex: number) {
    params.forEach((param, currentWindow: number) => {
      this.isLoading[currentWindow] = true;
      this.sseInstance.push(
        this.jiuwenModelServ.modelTestChatSSE(param, this.lang, {
          onMessage: (token: any) => {
            try {
              const chunkDataObj =
                token.data && flowCommonLogic.stringToObject(token.data);
              const event = chunkDataObj.choices ? 'message' : 'error';
              const info = chunkDataObj?.choices[0]?.delta || chunkDataObj?.choices[0]?.message
              const content = info?.content ?? '';
              const reasoning_content =
                info?.reasoning_content ?? '';

              if (event === 'error') {
                let assistantMessage = this.dialogHistory[currentWindow][
                  currentIndex
                ].find((item) => item.role === 'assistant');
                if (assistantMessage) {
                  assistantMessage.content = content;
                  assistantMessage.reasoning_content = reasoning_content;
                } else {
                  assistantMessage = {
                    role: 'assistant',
                    content,
                    reasoning_content,
                  };
                  this.dialogHistory[currentWindow][currentIndex] = [
                    ...this.dialogHistory[currentWindow][currentIndex],
                    assistantMessage,
                  ];
                }
              }

              if (event === 'message') {
                let assistantMessage = this.dialogHistory[currentWindow][
                  currentIndex
                ].find((item) => item.role === 'assistant');
                if (assistantMessage) {
                  // 追加大模型的中间输出
                  assistantMessage.content += content;
                  assistantMessage.reasoning_content += reasoning_content;
                  assistantMessage.reason_hidden = !reasoning_content;
                } else {
                  assistantMessage = {
                    role: 'assistant',
                    content,
                    reasoning_content,
                  };
                  this.dialogHistory[currentWindow][currentIndex] = [
                    ...this.dialogHistory[currentWindow][currentIndex],
                    assistantMessage,
                  ];
                }
                this.dialogHistory[currentWindow] = [
                  ...this.dialogHistory[currentWindow].slice(0, currentIndex),
                  this.dialogHistory[currentWindow][currentIndex],
                  ...this.dialogHistory[currentWindow].slice(currentIndex + 1),
                ];
              }
            } catch (error) {
              let data = JSON.parse(token.source.xhr.responseText);
              data = JSON.parse(data?.model_response);
              let errMsg = data?.error?.message;
              this.dialogHistory[currentWindow][currentIndex] = [
                ...this.dialogHistory[currentWindow][currentIndex],
                {
                  role: 'assistant',
                  content: errMsg,
                },
              ];

              this.isLoading[currentWindow] = false;
              if (!this.isLoading[1 - currentWindow]) {
                this.isShowStopIcon = false;
                this.isRequesting = false;
              }
              this.sseInstance[currentWindow]?.close();
            }
            this.scrollToBottom();
            if (this.isRequesting) {
              this.isShowStopIcon = true;
            }
            this.cdr.markForCheck();
          },
          onDone: () => {
            this.isLoading[currentWindow] = false;
            if (!this.isLoading[1 - currentWindow]) {
              this.isShowStopIcon = false;
              this.isRequesting = false;
            }
            let assistantMessage = this.dialogHistory[currentWindow][
              currentIndex
            ].find((item) => item.role === 'assistant');
            if (assistantMessage) {
              assistantMessage.done = true;
            }
            this.cdr.markForCheck();
          },
          onError: (error: { data: string; status: any }) => {
            this.isLoading[currentWindow] = false;
            if (!this.isLoading[1 - currentWindow]) {
              this.isShowStopIcon = false;
              this.isRequesting = false;
            }
            this.isTimeoutOrError = true;
            if (error.data) {
              this.progressError(error, currentIndex, currentWindow);
            }
            this.scrollToBottom();
            this.cdr.markForCheck();
          },
          onTimeout: () => {
            this.isLoading[currentWindow] = false;
            if (!this.isLoading[1 - currentWindow]) {
              this.isShowStopIcon = false;
              this.isRequesting = false;
            }
            this.isTimeoutOrError = true;
            this.scrollToBottom();
            this.cdr.markForCheck();
          },
          onAbort: () => {
            let assistantMessage = this.dialogHistory[currentWindow][
              currentIndex
            ].find((item) => item.role === 'assistant');
            if (assistantMessage) {
              assistantMessage.abort = true;
            }
            this.cdr.markForCheck();
          },
        }),
      );
    });
  }

  private getDebugRunParam() {
    return true;
  }

  /** 回答完成 或 发送新问题时，页面滚动条到最底部 */
  private scrollToBottom() {
    if (!this.isUserScrolling) {
      setTimeout(() => {
        this.chatContainerLeftRef.nativeElement.scrollTop =
          this.chatContainerLeftRef.nativeElement.scrollHeight;
        if (this.serviceInfo.length === 2) {
          this.chatContainerRightRef.nativeElement.scrollTop =
            this.chatContainerRightRef.nativeElement.scrollHeight;
        }
      }, 0);
    }
  }

  public stopChat() {
    this.sseInstance.forEach((item) => item.close());
    this.abortController?.abort();
    this.isRequesting = false;
    this.isLoading = [false, false];
    this.isShowStopIcon = false;
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    const currentScrollTop = target.scrollTop;

    // 判断是否向上滚动
    if (this.lastScrollTop> currentScrollTop ) {
      this.isUserScrolling = true; // 停止自动滚动
    } else if (
      currentScrollTop + target.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false; // 继续自动滚动（当用户手动滚动到最底部）
    }
    this.lastScrollTop = currentScrollTop;
  }
}
