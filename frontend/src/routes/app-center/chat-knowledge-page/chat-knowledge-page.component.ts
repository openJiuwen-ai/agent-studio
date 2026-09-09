import { Clipboard } from '@angular/cdk/clipboard';
import { TextFieldModule } from '@angular/cdk/text-field';
import { CommonModule } from '@angular/common';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  OnInit,
  ViewChild
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageComponent } from '@shared/services/cfdata.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';
import { Network } from '@model';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { AGENT_MODE_CODE } from "@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.constant";
import {
  LongMemoryModalComponent
} from "@routes/agent-center/app-agent/components/long-memory-modal/long-memory-modal.component";
import { PreviewDebugPlanComponent } from "@routes/agent-center/app-agent/components/preview-debug-plan/preview-debug-plan.component";
import {
  VarMemoryModalComponent
} from "@routes/agent-center/app-agent/components/var-memory-modal/var-memory-modal.component";
import { AgentDeepResearchRuntime } from "@routes/agent-center/app-deep-research/runtime/agent-deep-research-runtime";
import {
  DeepResearchTaskListComponent
} from "@routes/agent-center/app-deep-research/runtime/components/deep-research-task-list/deep-research-task-list.component";
import { IChatFlowAppDetail } from '@routes/agent-center/app-flow/app-flow.types';
import { AppExceedModalComponent } from '@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { SendQuestionService } from '@services/app-library/send-question.service';
import { CommonService } from '@services/common.service';
import { HttpService } from "@services/http.service";
import { PermissionService } from '@services/permission.service';
import { TtsPlayerService, TtsState } from '@services/tts-player.service';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import {
  SendData,
  SenderComponent,
} from '@shared/components/sender/sender.component';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { Subject, Subscription, finalize, from, takeUntil, tap } from 'rxjs';
import { CommonUtils } from 'src/utils/common.util';
import { v4 as uuidV4 } from 'uuid';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import flowCommonLogic from '../../agent-center/app-flow/common-logic-workflow';
import { PrologueQuestionsAreaComponent } from '../components/prologue-questions-area/prologue-questions-area.component';
import { RightOpPanelComponent } from '../components/right-op-panel/right-op-panel.component';
import { getUsedUp } from '@routes/agent-center/utils';
import { ERROR_CODE } from '@routes/agent-center/types/common.types';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';

@Component({
  selector: 'chat-knowledge-page',
  templateUrl: './chat-knowledge-page.component.html',
  styleUrls: [
    './chat-knowledge-page.component.scss',
    '../../../styles/text-field-prebuilt.css',
  ],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    NzIconModule,
    NzButtonModule,
    NzAlertModule,
    NzToolTipModule,
    NzSpinModule,
    NzCollapseModule,
    AppMarkdownAnswerComponent,
    PrologueQuestionsAreaComponent,
    RightOpPanelComponent,
    SenderComponent,
    UploadFileIconComponent,
    VarMemoryModalComponent,
    LongMemoryModalComponent,
    DeepResearchTaskListComponent,
    AgentDeepResearchRuntime,
    AppExceedModalComponent,
    PreviewDebugPlanComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER,I18nNamespace.PLATFORM_MANAGEMENT, I18nNamespace.COMMON, I18nNamespace.AGENT],
    },
  ],
})
export class ChatKnowledgePageComponent implements OnInit {
  public changeUrl = cdnAssetUrl;
  @ViewChild('chatContainerRef') chatContainerRef!: ElementRef;
  @ViewChild('varMemoryModalView') varMemoryModal: any;
  @ViewChild('longMemoryModalView') longMemoryModal: any;
  @ViewChild('sender') sender!: SenderComponent;
  @ViewChild('appExceedModalKnow') appExceedModalKnow: AppExceedModalComponent;

  public knowledgeBotInfo: IChatFlowAppDetail = {
    title: '',
    prologue: '',
    icon: '',
    cardList: [],
    tags: [],
    model_name: '',
    workflows: [],
    tools: [],
    creator: '',
    description: '',
    knowledge_repos: [],
    published_on: '',
    publish_time: '',
    free_trial_quota: null,
    memoryLibId: '',
  };
  dialogWidth: string = '100%';
  articleWidth: string = '0%';
  public usedUp = false;
  public memoryItems = [
    {id: 'var', label: this.i18n.transform('chatknowledgepagecomponent_3')},
  ]
  public isShowStopIcon = false;
  /** 默认关闭内容审核 */
  public isOpenReview = false;
  /** 页面底部，用户输入的问题 */
  public questionInputed = '';
  /** 页面主体，问题+答案区域 */
  public chatLoop: any = [];

  public isRequesting = false;

  /** 是否显示历史记录的半屏弹窗。true代表显示 */
  public isShowHistory = false;
  /** 底部的textarea框是否存在渐变框动效 */
  public isAnimating = false;

  public isLoading = false;
  public currentPermissions: any;
  private permissionSubscription: Subscription;
  public gradientLoadingIcon = `${Network.ASSETS_PATH}app-library/chating.gif`;

  // 根据浏览器导航栏内的URL，控制返回icon的显隐
  public showBackIcon = false;

  public lang = CommonUtils.getLanguage();

  private destroy$ = new Subject<void>();

  private sseInstance: any;
  /** 点击停止生成按钮时，记录停止的是第activeCurrentIdx个问答对 */
  private activeCurrentIdx: number | null = null;
  /** 点击停止生成按钮时，记录属于新问题，还是重新生成答案。重新生成答案时，无需滚动 */
  private isRegenerateActive: boolean = false;
  /** textarea框是否聚焦 */
  private isFocusState = false;

  private appId = '';

  public uuid = uuidV4();

  private hasExceptionOccurred = false;

  private routeType = '';

  shortCode = '';

  public userQueryLimit;

  public voiceEnable = false;

  public soundState = TtsState.Idle;

  public timbre = '';

  public isLoadeSuccess = true;

  private isFromDevelopSpace: boolean = false;

  private isFromOverview: boolean = false;

  public current_workspace_id = '';

  public isLoadingCopyBtn: boolean = false;

  public isDeepResearch: boolean = false

  public articleContent:string =''

  public is_agreement = true ;// 表示用户是否已经知晓风险
  public curAgentModeCode: AGENT_MODE_CODE = AGENT_MODE_CODE.GENERAL_MODE;

  constructor(
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private clipboard: Clipboard,
    private appLibraryRepoServe: AppLibraryRepoService,
    private agentRepoServe: AppAgentRepoService,
    private sendQuestionServe: SendQuestionService,
    private router: Router,
    private route: ActivatedRoute,
    private configServ: AgentConfigService,
    private ttsPlayerServe: TtsPlayerService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private permissionService: PermissionService,
    private readonly http: HttpService,
    private modalService: NzModalService,
    private appAgentRepoServ: AppAgentRepoService,
    private readonly commonService: CommonService,
  ) {
    this.route.queryParams.subscribe((params: any) => {
      if (params.appId) {
        this.appId = params.appId;
      } else if (params.workspace_id) {
        this.current_workspace_id = params.workspace_id;
      } else {
        this.route.params.subscribe((routeParams: any) => {
          this.appId = routeParams.id;
        });
      }
      this.showBackIcon = this.router.url.includes('app-library');
    });

    this.voiceEnable = this.configServ.voiceEnable();

    this.ttsPlayerServe.state$
      .pipe(takeUntil(this.destroy$))
      .subscribe((state) => (this.soundState = state));

  }

  async ngOnInit() {

    this.route.queryParams.subscribe((params) => {
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
      if (params.from && params.from === 'overview') {
        this.isFromOverview = true;
      }
    });
    this.permissionSubscription = this.permissionService.permissions$.subscribe(
      (permissions) => {
        this.currentPermissions = permissions;
      },
    );
    const url = this.router.url;
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    // 查询已发布的网页版应用详情
    if (url.includes('chat')) {
      this.routeType = 'web-page';
      this.shortCode = this.route.snapshot.params.id;
      this.getWebPageInfo(this.shortCode)
        .pipe(finalize(() => {

        }))
        .subscribe(()=>{});
    }
    // 查询百宝箱中，对话型应用详情
    if (url.includes('knowledge-bot')) {
      this.routeType = 'knowledge-bot';
      this.getKnowledgeBotInfo()
        .pipe(finalize(() => {}))
        .subscribe(()=>{});
    }
    this.userQueryLimit =
      this.configServ.getConfigs().user_query_limit ?? 100000;

  }

  onSelectMemoryItem(event) {
    if (event.id === 'var') {
      this.varMemoryModal.open();
      return;
    }
    if (event.id === 'long_memory') {
      this.longMemoryModal.open();
      return;
    }
  }

  ngOnDestroy(): void {
    this.isLoadingCopyBtn = false;
    this.sendQuestionServe.setQuestionAndFlag('');
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  // 复制到工作台
  async copyToWorkbench(): Promise<void> {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    if (this.isLoadingCopyBtn) {
      return;
    }
    this.isLoadingCopyBtn = true;
    this.appLibraryRepoServe
      .copyToWorkbench(this.appId, 'agent')
      .then((res: any) => {
        if (res.resource_id){
          const modalInstance = this.modalService.create({
            nzTitle: this.i18n.transform('copy_tip2'),
            nzContent: '',
            nzFooter: [
              {
                label: this.i18n.transform('cancel'),
                onClick: () => modalInstance.destroy()
              },
              {
                label: this.i18n.transform('confirm'),
                type: 'primary',
                onClick: () => {
                  this.router.navigate(['/home/agent-center/app-agent/detail'], {
                    queryParams: {
                      agentId: res.resource_id,
                    },
                  });
                  modalInstance.destroy();
                },
              },
            ],
          });
        }
      }).finally(() => {
        this.isFromDevelopSpace = false;
        this.isLoadingCopyBtn = false;
    });
  }

  async isResourceExceed() {
    const res = await this.appAgentRepoServ.getResourceQuantity('agent');
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount };
        this.appExceedModalKnow.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }


  public onClickBack() {
    if (this.isFromOverview) {
      this.router.navigate(['/home/overview']);
      return;
    }
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space']);
      return;
    }
    this.router.navigate([`home/app-library`]);
  }
  public hasPermission(): boolean {
    return (
      this.currentPermissions &&
      this.currentPermissions.OPERATOR
    );
  }
  public getText(content: any): string {
    return content?.showAnswer?.trim() ?? '';
  }

  public onSoundOut(content: any) {
    if (this.soundState === TtsState.Playing) {
      this.ttsPlayerServe.stop();
      return;
    }
    this.ttsPlayerServe.play(this.getText(content), {
      property: this.timbre,
    });
  }

  public sendQuestion(data: SendData) {
    const { content, uploadData } = data;
    this.chatLoop.push({
      loading: true,
      showQuestion: content,
      showAnswer: undefined,
      showBottomBtns: false,
      isTimeoutOrError: false,
      chunkIds: [],
      showCopiedTip: false,
      passContentReview: true,
      isPopconfirmOpen: false,
      isClickLikeBtn: false,
      isClickDislikeBtn: false,
      isLike: false,
      isDislike: false,
      uploadData,
    });
    this.scrollToBottom();

    const messages = this.getDebugRunParam(this.chatLoop.length - 1, true);
    this.postStream(messages, this.chatLoop.length - 1);
    this.questionInputed = '';
    this.cdr.markForCheck();
  }

  postStream(messages: any, currentIndex: number, isRegenerate = false) {
    this.isRequesting = true;
    this.activeCurrentIdx = currentIndex; // 更新停止生成的是第几轮问答
    this.isRegenerateActive = isRegenerate; // 更新停止生成时，是新问题还是重新生成答案
    this.isShowStopIcon = true;
    this.chatLoop[currentIndex].chunkIds = [];

    if (this.routeType === 'knowledge-bot') {
      this.sseInstance = this.agentRepoServe.knowledgeChatSSE(
        messages,
        this.appId,
        this.uuid,
        'PUBLISHED',
        this.lang,
        this.getSSECallbacks(currentIndex, isRegenerate),
        '',
        'agents',
        true
      );
    } else if (this.routeType === 'web-page') {
      if(this.curAgentModeCode ===AGENT_MODE_CODE.GENERAL_MODE){
        this.sseInstance = this.agentRepoServe.webPageChatSSE(
          messages,
          'agents',
          this.shortCode,
          this.uuid,
          'PUBLISHED',
          this.lang,
          this.getSSECallbacks(currentIndex, isRegenerate),
        );
      }
    }
  }


  private getSSECallbacks(currentIndex: number, isRegenerate: boolean) {
    return {
      onMessage: (token: any) => {
        if (this.chatLoop[currentIndex]?.showAnswer === undefined) {
          this.chatLoop[currentIndex].showAnswer = '';
        }

        try {
          let { event, content, data, reasoning_content} =
            token.data && flowCommonLogic.stringToObject(token.data);

          const { text, offset} = data || {};

          if (event === 'message' && reasoning_content) {
            this.chatLoop[currentIndex].thinkLoading = false;
            if (this.chatLoop[currentIndex].thinkValue === undefined) {
              this.chatLoop[currentIndex].thinkValue = '';
            }
            this.chatLoop[currentIndex].thinkValue =
              this.chatLoop[currentIndex].thinkValue + reasoning_content;
            this.chatLoop[currentIndex].thinking = true;
          } else if (content) {
            this.chatLoop[currentIndex].thinking = false;
          }

          if(content === undefined){
            content = '';
          }

          if ((text || content) && event !== 'plugin_end') {
            this.chatLoop[currentIndex].loading = false;
          }

          if (event === 'plugin_end' && content && typeof content === 'string') {
            this.chatLoop[currentIndex].showAnswer += content;
          }

          if (event === 'message' && content) {
            this.chatLoop[currentIndex].showAnswer += content;
          }

          if (event === 'error') {
            this.chatLoop[currentIndex].showAnswer = this.i18n.transform('run_error');
            this.chatLoop[currentIndex].loading = false;
          }

          if (event === 'summary_response') {
            if (!this.chatLoop[currentIndex]?.showAnswer) {
              this.chatLoop[currentIndex].showAnswer = content;
            }
          }
          if (event === 'sensitive') {
            // 替换大模型回答中的敏感词
            let curAnsText = this.chatLoop[currentIndex]?.showAnswer ?? '';
            const safeOffset = Math.min(offset, curAnsText.length);
            this.chatLoop[currentIndex].showAnswer =
              curAnsText.slice(0, safeOffset) + (text ?? '');
          }
        } catch (error) {
          // do nth
        }
        if (!isRegenerate) {
          this.scrollToBottom();
        }
        this.isShowStopIcon = true;
        this.cdr.markForCheck();
      },
      onDone: () => {
        this.isRequesting = false;
        // 修复模型返回空输出的情况
        if (!this.chatLoop[currentIndex].showAnswer) {
          this.chatLoop[currentIndex].showAnswer = ' ';
          this.chatLoop[currentIndex].loading = false;
        }

        this.chatLoop[currentIndex].showBottomBtns = true;
        this.chatLoop[currentIndex].isTimeoutOrError = false;
        if (!this.hasExceptionOccurred) {
          this.chatLoop[currentIndex].isShowRed = false;
        } else {
          this.chatLoop[currentIndex].isShowRed = true;
        }
        this.isShowStopIcon = false;
        this.cdr.markForCheck();
      },
      onError: (error: { data: string; status: any }) => {
        this.chatLoop[currentIndex].loading = false;
        this.isRequesting = false;
        let responseError = '';
        let reason = '';
        let quotaUsedUp = false;
        if (error.data) {
          try {
            const err = JSON.parse(error.data);
            quotaUsedUp = err?.error_code === ERROR_CODE.QUOTA_USED_UP;
            reason = err.error_msg || err.error?.message;
            if (err.error_code && err.error_msg) {
              // 适配外部的错误格式，可能是网络不通等
              responseError = this.i18n.transform('ApiError', {
                errCode: err.error_code,
                reason: err.error_msg,
              });
            } else if (err.error) {
              // 适配经过模型内部处理后，返回的错误格式
              responseError = this.i18n.transform('ApiError', {
                errCode: err.error?.code,
                reason: err.error?.message,
              });
            } else {
              responseError = this.i18n.transform('ApiError', {
                errCode: 'UNKNOWN_FORMAT',
                reason: 'The error format is unknown.',
              });
            }
          } catch {
            responseError = this.i18n.transform('ApiError', {
              errCode: error.status,
              reason: this.i18n.transform('NetErrorTips'),
            });
          }
        }
        this.usedUp = quotaUsedUp;
        this.chatLoop[currentIndex].showAnswer = quotaUsedUp ? reason :
          this.i18n.transform('NetErrorTips') + responseError;
        this.chatLoop[currentIndex].isShowRed = !quotaUsedUp;
        this.chatLoop[currentIndex].showBottomBtns = !quotaUsedUp;
        this.chatLoop[currentIndex].isTimeoutOrError = true;
        this.chatLoop[currentIndex].chunkIds = [];
        this.isShowStopIcon = false;
        this.commonOprsForTimeoutAndError(isRegenerate);
        this.cdr.markForCheck();
      },
      onTimeout: () => {
        this.chatLoop[currentIndex].loading = false;
        this.isRequesting = false;
        MessageComponent.showError(
          this.i18n.transform('streaming_timeout'),
          3000,
        );
        this.sseInstance.close();
        /** 如果没有之前的回答 */
        if (!this.chatLoop[currentIndex].showAnswer) {
          this.chatLoop[currentIndex].showAnswer =
            this.i18n.transform('streaming_timeout');
          this.chatLoop[currentIndex].isShowRed = true;
        }
        this.chatLoop[currentIndex].showBottomBtns = true;
        this.chatLoop[currentIndex].isTimeoutOrError = true;
        this.chatLoop[currentIndex].chunkIds = [];
        this.isShowStopIcon = false;
        this.commonOprsForTimeoutAndError(isRegenerate);
        this.cdr.markForCheck();
      },
    };
  }

  public handleFocusStart() {
    this.isFocusState = true;
  }

  public handleInputStart() {
    if (this.isFocusState) {
      this.isAnimating = true;
      this.isFocusState = false;
      this.cdr.markForCheck();
      setTimeout(() => {
        this.isAnimating = false;
        this.cdr.markForCheck();
      }, 4000);
    }
  }

  /**
   * 每轮问答的【重新生成】按钮是否可以点击。
   * 原则是当前页面中，只能有一个流式请求/chat/completions
   */
  public canRegenerate(item: any): boolean {
    return !this.isRequesting && !!item.showQuestion.trim();
  }

  public regenerate(item: any, index: number) {
    if (!this.canRegenerate(item)) {
      return;
    }
    this.chatLoop[index].loading = true;
    if (this.chatLoop[index]) {
      // 若当前想重新生成模型回答的问题，上一次调流式接口超时或错误，需清除上一轮问答的状态
      this.chatLoop[index].isShowRed = false;
      this.chatLoop[index].showAnswer = undefined;
      this.chatLoop[index].showBottomBtns = false;
      // 重新生成某一轮回答时，需要重置点赞点踩的选中状态
      this.chatLoop[index].isClickLikeBtn = false;
      this.chatLoop[index].isClickDislikeBtn = false;
    }

    const messages = this.getDebugRunParam(index);
    this.postStream(messages, index, true);
  }

  public getTrimmedQuestion(question: string) {
    return question.trim();
  }

  /** 复制、点赞和点踩按钮是否可见。大模型的回答可能是空字符串，不能调用反馈接口 */
  public isVisibleOfLastBtns(item: any): boolean {
    return (
      item.showBottomBtns &&
      !item.isTimeoutOrError &&
      item.showAnswer?.trim() !== ''
    );
  }


  /** 复制整体答案 */
  copyAllAnswer(messages: any, currentIndex: number) {
    // 直接复制原始 markdown，保留段落分隔与结构（原 replace 会吞掉第一个段落分隔）
    this.clipboard.copy(messages?.showAnswer ?? '');
    MessageComponent.showSuccess(this.i18n.transform('copy_success'), 3000);
  }

  /** 点击底部的清空对话，开启新聊天 */
  public clearChat() {
    this.uuid = uuidV4();
    this.sseInstance.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.questionInputed = ''; // 置空textarea中的问题

    // 在上一轮对话中，点击清空对话时存在的最后一个流式接口问答对（包含新问题或重新生成），存入localStorage中
    if (this.activeCurrentIdx !== null) {
      if (this.chatLoop[this.activeCurrentIdx].showAnswer === undefined) {
        this.chatLoop[this.activeCurrentIdx].showAnswer = '';
      }
      this.commonOprsForTimeoutAndError(this.isRegenerateActive);
      this.activeCurrentIdx = null;
    }
    this.chatLoop = []; // 置空页面主体的多轮对话
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
  }

  public handleClickQuestion(questionItem: string) {
    this.sendQuestion({
      role: 'user',
      content: questionItem,
      uploadData: [],
    });
  }

  /** 获取知识型应用的run接口入参 */
  private getDebugRunParam(currentIndex: number, isUserInput: boolean = false) {
    const { showQuestion, uploadData } = this.chatLoop[currentIndex] || {};
    let query = showQuestion;
    let files = []
    if (uploadData[0]?.url && isUserInput) {
      query = `${JSON.stringify(uploadData.map((item) => item.url))} ${query}`;
      files = uploadData.map((item) => item.url)
    }
    return {
      query,
      files
    };
  }

  /** 回答完成 或 发送新问题时，页面滚动条到最底部 */
  private scrollToBottom() {
    setTimeout(() => {
      this.chatContainerRef.nativeElement.scrollTop =
        this.chatContainerRef.nativeElement.scrollHeight;
    }, 0);
  }

  public stopChat() {
    this.sseInstance.close();
    this.isRequesting = false;
    if (this.activeCurrentIdx !== null) {
      this.chatLoop[this.activeCurrentIdx].loading = false;
      // 如果被停止问答对的showAnswer为undefined，则将其设置为空字符串
      if (this.chatLoop[this.activeCurrentIdx].showAnswer === undefined) {
        this.chatLoop[this.activeCurrentIdx].showAnswer = '';
      }
      this.chatLoop[this.activeCurrentIdx].isShowRed = false;
      this.chatLoop[this.activeCurrentIdx].showBottomBtns = true;
      // 停止生成的这一轮没有复制、点赞和点踩按钮。只有重新生成按钮
      this.chatLoop[this.activeCurrentIdx].isTimeoutOrError = true;
      this.chatLoop[this.activeCurrentIdx].chunkIds = [];
      this.isShowStopIcon = false;
      // 流式接口超时 或 报错的共有逻辑，将这3类存入历史记录中
      this.commonOprsForTimeoutAndError(this.isRegenerateActive);
      this.activeCurrentIdx = null;
    }
    this.cdr.markForCheck();
  }

  /** 抽离流式接口超时和失败时，共有逻辑 */
  private commonOprsForTimeoutAndError(isRegenerate: boolean) {
    if (!isRegenerate) {
      this.scrollToBottom();
    }
  }

  private getKnowledgeBotInfo() {
    this.isLoading = true;
    return from(this.appLibraryRepoServe.getKnowledgeBot(this.appId)).pipe(
      tap({
        next: (value) => {
          this.isLoading = false;
          const {
            icon,
            name,
            prologue,
            suggest_queries,
            tags,
            model_name,
            workflows,
            tools,
            creator,
            description,
            knowledge_repos,
            publish_time,
            voice_interaction,
            free_trial_quota,
            memory_repo_id = '',
          } = value;
          this.knowledgeBotInfo = {
            icon,
            title: name,
            prologue: prologue || '',
            cardList: suggest_queries?.map((item: any) => ({
              isOverflow: false,
              question: item,
            })),
            model_name,
            tags: tags || [],
            workflows: workflows || [],
            tools: tools || [],
            creator,
            description,
            knowledge_repos: knowledge_repos || [],
            publish_time,
            free_trial_quota,
            memoryLibId: memory_repo_id,
          };
          this.usedUp = getUsedUp(free_trial_quota);
          if (voice_interaction) {
            const { language, timbre, domain } = voice_interaction;
            this.timbre = `${language}_${timbre}_${domain}`;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
          this.showErrorModal();
        },
      }),
    );
  }

  private getWebPageInfo(shortCode: string) {
    this.isLoading = true;
    return from(
      this.agentRepoServe.getWebPageInfo(shortCode, 'short_code', 'WEB_PAGE',this.current_workspace_id),
    ).pipe(
      tap({
        next: (value) => {
          this.isLoading = false;
          this.appId = value.app_id;
          this.isDeepResearch = value.sub_type ==='deepresearch'
          if(!this.isDeepResearch){
            const agentSubType =  value.sub_type as AGENT_MODE_CODE;
            this.curAgentModeCode =
              agentSubType === AGENT_MODE_CODE.PLANNING_MODE
                ? AGENT_MODE_CODE.PLANNING_MODE
                : AGENT_MODE_CODE.GENERAL_MODE;
          }

          const {
            icon,
            name,
            prologue,
            suggest_queries,
            model_name,
            tags,
            workflows,
            tools,
            creator,
            description,
            knowledge_repos,
            published_on,
            voice_interaction,
            free_trial_quota,
            memory_repo_id = '',
          } = value;
          this.knowledgeBotInfo = {
            icon,
            title: name,
            prologue: prologue || '',
            cardList: suggest_queries?.map((item: any) => ({
              isOverflow: false,
              question: item,
            })),
            model_name,
            tags,
            workflows,
            tools,
            creator,
            description,
            knowledge_repos,
            published_on,
            free_trial_quota,
            memoryLibId: memory_repo_id,
          };
          this.usedUp = getUsedUp(free_trial_quota);
          if (voice_interaction) {
            const { language, timbre, domain } = voice_interaction;
            this.timbre = `${language}_${timbre}_${domain}`;
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.isLoading = false;
          this.cdr.markForCheck();
          this.showErrorModal();
        },
      }),
    );
  }

  public showErrorModal() {
    this.isLoadeSuccess = false;
    this.modalService.create({
      nzTitle: this.i18n.transform('urlError'),
      nzContent: this.i18n.transform('urlErrorMsg'),
      nzFooter: null,
    });
  }

  isExpandRuntimeArea(data: any){

  }



  handleClickViewArticle(data: any): void {
    this.articleContent = data.content
    if (data.show) {
      this.articleWidth = '40%';
      this.dialogWidth = '60%';
    } else {
      this.articleWidth = '0%';
      this.dialogWidth = '100%';
    }
  }

  handleClickCloseArticle(): void {
    this.articleWidth = '0%';
    this.dialogWidth = '100%';
  }

  public changeCollapsedState(pluginForm: any) {
    const collapsed = pluginForm?.collapsed;
    pluginForm.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  protected readonly AGENT_MODE_CODE = AGENT_MODE_CODE;
}
