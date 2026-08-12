import { TextFieldModule } from '@angular/cdk/text-field';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  OnInit,
  Output, Renderer2,
  SimpleChanges,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Graph } from '@antv/x6';
import { MessageComponent } from '@shared/services/cfdata.service';
import { NzDrawerModule, NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzPopoverModule } from 'ng-zorro-antd/popover';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzTooltipModule } from 'ng-zorro-antd/tooltip';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { I18nNamespace } from '@i18n';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { FeedbackType } from '@routes/agent-center/app-agent/components/chat-item/chat-item.enum';
import { CHAT_FILTER_KEYS } from '@routes/agent-center/types/common.types';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { SessioMgnService } from '@services/agent-observatory/session-service';
import { KbAnswerResolverService } from '@services/knowledge-center/kb-answer-resolver.service';
import { AppConversationRepoService } from '@services/repositories/app-conversation-repo.service';
import { TtsPlayerService, TtsState } from '@services/tts-player.service';
import { WorkflowChatBaseComponent } from '@shared/base/workflow-chat-base.service';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AssetClearIconComponent } from '@shared/components/assets/asset-clear-icon/asset-clear-icon.component';
import { AssetConfigIconComponent } from '@shared/components/assets/asset-config-icon/asset-config-icon.component';
import { AssetDisabledClearIconComponent } from '@shared/components/assets/asset-disabled-chat-icon/asset-disabled-chat-icon.component';
import { CustomPopconfirmComponent } from '@shared/components/custom-popconfirm/custom-popconfirm.component';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { InlineSvgComponent } from '@shared/components/inline-svg.component';
import { InputNodeParamsComponent } from '@shared/components/input-node-params/input-node-params.component';
import { MemoryManagementComponent } from '@shared/components/memory-management/memory-management.component';
import { ConversationState, IMemoryManagementData } from '@shared/components/memory-management/memory-management.interface';
import { MemoryUpdatedComponent } from '@shared/components/memory-updated/memory-updated.component';
import {
  SenderComponent
} from '@shared/components/sender/sender.component';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep, isNaN, isNil } from 'lodash';
import { takeUntil } from 'rxjs';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { isDevelpor } from 'src/utils/utils';
import { v4 as uuidV4 } from 'uuid';
import CommonLogic from '../../../../app-center/common-logic-app-center';
import { AppFlowService } from '../../app-flow.service';
import type { IPluginConfig, IWorkflow } from '../../app-flow.types';
import { EViewType } from '../../app-flow.types';
import flowCommonLogic from '../../common-logic-workflow';
import { WORKFLOW_SVGS } from '../../flow.const';
import { type IStartNode } from '../../node.type';
import { StartImportJsonModalComponent } from '../start-import-json-modal/start-import-json-modal.component';

@Component({
  selector: 'dialog-halfmodal',
  templateUrl: './dialog-halfmodal.component.html',
  styleUrls: [
    './dialog-halfmodal.component.scss',
    '../../../../../styles/text-field-prebuilt.css',
  ],
  standalone: true,
  imports: [
    MODULES,
    DynamicNodeParamsComponent,
    TextFieldModule,
    AppMarkdownAnswerComponent,
    CustomPopconfirmComponent,
    InputNodeParamsComponent,
    AssetConfigIconComponent,
    AssetClearIconComponent,
    AssetDisabledClearIconComponent,
    ClickOutsideDirective,
    SenderComponent,
    InlineSvgComponent,
    MemoryManagementComponent,
    MemoryUpdatedComponent,
    NzDrawerModule,
    NzPopoverModule,
    NzIconModule,
    NzButtonModule,
    NzTooltipModule,
    NzSpinModule,
    NzCollapseModule,
    NzFormModule,
    NzInputModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.TRACE, I18nNamespace.AGENT],
    },
    NzDrawerService,
    NzModalService,
  ],
})
export class DialogHalfmodalComponent
  extends WorkflowChatBaseComponent
  implements OnInit, OnDestroy
{
  @Input() inputWorkflowId?: string;

  @Input() halfModalTopClass?: string;

  @Input() override graph!: Graph;

  @Input() override currWorkflow!: IWorkflow;

  @Input() conversationId!: string;

  @Input() versionName!: string;

  @Input() isShow: boolean;

  @Input() environment_id: string;

  @Input() fromComponent: string;

  @Input() isDrawerVisible: boolean = false; // 抽屉是否可见

  @Output('close') close = new EventEmitter<void>();

  @Output('clickErrorInfo') clickErrorInfo = new EventEmitter<void>();

  @Output() conversationIdChange = new EventEmitter<string>();

  @ViewChild('dynamicNodeParams')
  override dynamicNodeParams!: DynamicNodeParamsComponent;

  @ViewChild('globalParams')
  override globalParams!: DynamicNodeParamsComponent;

  @ViewChild('inputNodeParams')
  inputNodeParamsComp!: InputNodeParamsComponent;
  // 引用输入组件
  @ViewChild('metaSenderComponent') metaSenderRef: SenderComponent;

  @ViewChild('pluginAreaRef') pluginAreaRef!: ElementRef;

  @ViewChild('pluginForm') override pluginForm: NgForm;

  @ViewChild('chatContainerRef') override chatContainerRef!: ElementRef;

  @ViewChild('chatFlowTextarea') override chatTextarea!: ElementRef;

  @ViewChild('runTestHalfModel', { static: true }) runTestHalfModel: NzDrawerRef;


  public flowInfo: any = {};

  // 用户输入的问题
  public questionInputed = '';

  public validateAlertIcon = WORKFLOW_SVGS.ValidateAlert;
  public exceptionIcon = WORKFLOW_SVGS.exception;

  // 底部的textarea框是否存在渐变框动效
  public isAnimating = false;

  public prologue = '';

  public questions: string[] = [];

  public supportFeedback =
    this.configServ.getConfigs()?.feedback_enable ?? false;

  // textarea框是否聚焦
  private isFocusState = false;

  public isDevelporFlag = isDevelpor();

  public supportAnnotation = this.configServ.getConfigs()?.agentops_evaluation_display && this.configServ.getConfigs().agentops_menu_display;

  // 试运行接口的入参version
  private version: number = 0;

  /** 表示纵向滚动条的当前位置 */
  private lastScrollTop = 0;

  public start_time: number;

  public voiceEnable = false;

  public soundState = TtsState.Idle;

  public voiceInteraction = {
    language: '',
    timbre: '',
    domain: '',
  };
  public voiceInteractionTip = this.i18n.transform('read_aloud_tip');
  public voiceInteractionDisabled = true;

  public isAB = false; //是否是盘古助手场景

  conversationState: ConversationState = {
    isExtract: true,
    isRetrieve: true,
  };

  // 自动追问接口是否失败。若失败，则隐藏【你可以继续提问】
  public isQuestionsFailed = false;
  public isQuestionsLoading = false;
  public isRecentQuestionVisible = false;
  private nodeModalTop: number | null = null;
  // 追问列表
  public followUpQuestions = [];

  isFirstClickTest: boolean = false; // 是否点击试运行重新打开的侧边弹窗，是的话点击配置项关闭按钮直接关闭，否则进入对话页面

  public get memoryLibId() {
    return this.currWorkflow?.memory_config?.memory_repo_id ??
      this.currWorkflow?.workflow_details?.configs?.memory_config?.memory_repo_id ??
      this.currWorkflow?.workflow_details?.memory_config?.memory_repo_id ?? '';
  }

  constructor(
    protected override appFlowServe: AppFlowService,
    protected override appAgentServe: AppAgentRepoService,
    protected override configServ: AgentConfigService,
    public override i18n: I18NextEagerPipe,
    protected override cdr: ChangeDetectorRef,
    protected override commonLogic: agentCommonLogic,
    protected override monacoLoader: MonacoEditorLoaderService,
    private route: ActivatedRoute,
    private fb: FormBuilder,
    private ttsPlayerServe: TtsPlayerService,
    protected override agentDataServe: AgentDataService,
    protected override pluginRepoServe: AppPluginRepoService,
    private conversationServe: AppConversationRepoService,
    private kbAnswerResolverService: KbAnswerResolverService,
    public sessioMgnService : SessioMgnService,
    private drawerService: NzDrawerService,
    private renderer: Renderer2,
    ) {
    super(
      appFlowServe,
      appAgentServe,
      configServ,
      commonLogic,
      monacoLoader,
      i18n,
      cdr,
      agentDataServe,
      pluginRepoServe,
    );

    this.ttsPlayerServe.state$.pipe(takeUntil(this.destroy$)).subscribe(state => (this.soundState = state));

    /** 订阅试运行按钮是否被点击 */
    this.appFlowServe
      .runBtnClickedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (isClicked: boolean) => {
        this.isRetryRunning = isClicked;
        if (isClicked) {
          this.isFirstClickTest = true;
          setTimeout(() => { this.adjustTopForNodeModal(); });
          // 存储已填的插件入参，并组装插件节点的输入参数
          this.appFlowServe?.setRunSettings(this.settingsList);
          await this?.buildSettingsData();
          if (!this.startNodeParams.length && !this.settingsList.length && !this.globalConfigParams.length) {
            this?.updateCurAndChatView();
          } else {
            this.curView = EViewType.CONFIG;
          }
        }
      });

    /** 订阅自动保存接口返回的updated_on值，作为version字段的value */
    this.appFlowServe
      .versionInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version: number) => {
        this.version = version;
        this.versionId = '';
      });

    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(version => {
        this.versionId = version?.version_id;
        this.isFlowReadonly = version?.isFlowReadonly;
      });

    this.route?.queryParams.subscribe(params => {
      const { id, type, versionId } = params;
      this.workflow_id = id || this.inputWorkflowId;
      this.type = type;
      this.versionId = versionId;
    });

    /** 订阅开始节点配置弹窗的确定按钮是否被点击 */
    this.appFlowServe
      .startNodeBtnUpdate$()
      .pipe(takeUntil(this?.destroy$))
      .subscribe((isClicked: boolean) => {
        if (isClicked) {
          const graphValue = this?.graph;
          const workflowDetailValue = this.currWorkflow;
          this.updateInputParams(graphValue, workflowDetailValue);
          this.registerJSONValidationSchema(true, true);
        }
      });

    this.appFlowServe
      .flowInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info?: any) => {
        const { avatar, name } = info || {};
        this.flowInfo = {
          avatar,
          name,
        };
      });

    // 只有当删除或新增插件节点时，才会更新插件鉴权参数
    this.appFlowServe
      .refreshFlagUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isRefresh: boolean) => {
        if (isRefresh) {
          this.appFlowServe?.setRunSettings(this.settingsList);
          this.buildSettingsData();
        }
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    // 解决maxLine不生效问题
    if (this.isShow) {
      const tempPrologue = this?.prologue;
      this.prologue = '';
      setTimeout(() => {
        this.prologue = tempPrologue;
      }, 120);
      return;
    }
    const graphValue = changes.graph ? changes.graph.currentValue : this.graph;
    const workflowDetailValue = changes.currWorkflow
      ? changes.currWorkflow.currentValue
      : this.currWorkflow;
    this.currWorkflow = workflowDetailValue;
    this.updateInputParams(graphValue, workflowDetailValue);
    this.registerJSONValidationSchema(true, true);

    // 设置对话型工作流空状态时，展示的工作流icon和名称
    if (changes.currWorkflow?.currentValue) {
      const { avatar, name, icon } = changes?.currWorkflow?.currentValue || {};
      this.flowInfo = {
        name,
        avatar: avatar || icon,
      };
    }

    this.prologue =
      this.currWorkflow?.workflow_details?.configs?.prologue ?? '';
    this.questions =
      this.currWorkflow?.workflow_details?.configs?.suggest_queries ?? [];

    if (this.currWorkflow?.workflow_details?.configs?.voice_interaction) {
      this.voiceInteraction =
        this.currWorkflow?.workflow_details?.configs.voice_interaction;
      const { language, timbre, domain } =
        this.currWorkflow?.workflow_details?.configs?.voice_interaction;
      if (language && timbre && domain) {
        this.voiceInteractionTip = this.i18n.transform('read_aloud');
        this.voiceInteractionDisabled = false;
      } else {
        this.voiceInteractionTip = this.i18n.transform('read_aloud_tip');
        this.voiceInteractionDisabled = true;
      }
    } else {
      this.voiceInteractionTip = this.i18n.transform('read_aloud_tip');
      this.voiceInteractionDisabled = true;
    }

    if (this.type !== 'multi') {
      //局点支持语音
      this.voiceEnable = this.configServ.voiceEnable();
    }

    if (changes.versionName && changes.versionName.currentValue) {
      this.curView = EViewType.CONFIG;
      this.chatLoop = [];
    }

    if (changes.inputWorkflowId && changes.inputWorkflowId.currentValue) {
      this.workflow_id = changes.inputWorkflowId.currentValue;
    }

    this.isAB = this.configServ.getConfigs().site === 'ab';
  }

  getIcon(url: string) {
    if (url) {
      if (url.startsWith('data:image/')) {
        return url;
      } else {
        return cdnAssetUrl(url);
      }
    }
    return '';
  }

  // 重写onDone方法，对话完成时主动聚焦输入框
  override onDone(curIndex: number, token: any) {
    super.onDone(curIndex, token);
    this.metaSenderRef?.onFocus();
  }

  override onParamsValid() {
    this.updateCurAndChatView();
    this.isFirstClickTest = false;
  }

  public importStartJson(): void {
    const originFormData = this.getRunWorkflowParams(true) || {};
    const drawerRef = this.drawerService.create({
      nzTitle: undefined,
      nzContent: StartImportJsonModalComponent,
      nzContentParams: {
        defaultJson: this.formatToJsonData(originFormData),
        defaultDataList: cloneDeep(this.startNodeParams),
        showDefaultValue: false,
      },
      nzWidth: 480,
      nzPlacement: 'right',
      nzMaskClosable: false,
      nzCloseOnNavigation: false,
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      if (instance) {
        const subscription = instance.confirm.subscribe((newInputList) => {
          this?.dynamicNodeParams?.patchFormValue(
            this.getNewJSONFormData(originFormData, newInputList),
            newInputList,
          );
          drawerRef.close();
          subscription.unsubscribe();
        });
      }
    });
  }

  public importConfigJson(): void {
    const originFormData = this.getRunWorkflowGlobalParams(true) || {};
    const drawerRef = this.drawerService.create({
      nzTitle: undefined,
      nzContent: StartImportJsonModalComponent,
      nzContentParams: {
        defaultJson: this.formatToJsonData(originFormData),
        defaultDataList: cloneDeep(this.globalConfigParams),
      },
      nzWidth: 480,
      nzPlacement: 'right',
      nzMaskClosable: false,
      nzCloseOnNavigation: false,
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      if (instance) {
        const subscription = instance.confirm.subscribe((newInputList) => {
          this?.globalParams?.patchFormValue(
            this.getNewJSONFormData(originFormData, newInputList),
            newInputList,
          );
          drawerRef.close();
          subscription.unsubscribe();
        });
      }
    });
  }

  public getText(content: any): string {
    return content?.trim() ?? '';
  }

  public onSoundOut(content: any) {
    this.testStatusObj.show = false;
    this.testStatusObj.status = '';
    this.testStatusObj.text = '';
    if (this.soundState === TtsState.Playing) {
      this.ttsPlayerServe?.stop();
      return;
    }
    const { language, timbre, domain } =
      this.currWorkflow?.workflow_details?.configs?.voice_interaction;
    if (!timbre) {
      MessageComponent?.showError(
        this.i18n.transform('stopped_generating'),
        3000,
      );
      return;
    }
    this.ttsPlayerServe?.play(this.getText(content), {
      property: `${language}_${timbre}_${domain}`,
    });
  }

  public get runFlowButtonText(): string {
    return this.commonLogic?.runFlowButtonText(
      this.isRetryRunning,
      this.isStreamFail,
      this.isRequesting,
    );
  }

  public goToConfigView() {
    this.curView = EViewType?.CONFIG;
  }

  public onClose() {
    this.isDrawerVisible = false;
    this.isFirstClickTest = false;
    this.appFlowServe.setRunSettings(this.settingsList);
    this.close?.emit();
    this.curView = EViewType.CONFIG;
  }

  public getTrimmedQuestion(question: string) {
    return question?.trim();
  }

  /** 对话的相关函数 */
  public canClear() {
    return (
      this.chatLoop.length !== 0 && this.chatLoop[0]?.showAnswer !== undefined
    );
  }

  /** 点击底部的清空对话，开启新聊天 */
  public clearChat() {
    if (!this.canClear()) {
      return;
    }
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.chatView = EViewType?.CHAT_EMPTY;
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.questionInputed = ''; // 置空textarea中的问题
    this.chatLoop = []; // 置空页面主体的多轮对话
    this.appFlowServe.setTokenData({}); // 置空画布对应节点的运行状态
    this.conversationId = uuidV4();
    this.conversationIdChange.emit(this.conversationId);
    this.appFlowServe?.setAnswerInputForm(this.fb.group({}));
    this.testStatusObj.show = false;
    this.testStatusObj.status = '';
    this.testStatusObj.text = '';
  }

  public stopChat() {
    this.testStatusObj.show = false;
    this.testStatusObj.status = '';
    this.testStatusObj.text = '';
    this.sseInstance?.close();
    this.isRequesting = false;
    const lastIndex = this.chatLoop.length - 1;
    this.chatLoop[lastIndex].thinkLoading = false;
    this.chatLoop[lastIndex].terminate = true;

    this.appFlowServe.setTokenData({
      event: 'user_stop' // 用户手动停止
    })

    const currentAns = this.chatLoop[lastIndex].showAnswer[this.index];
    if (this.type === 'multi') {
      const end_time = new Date().getTime();
      currentAns.loading = false;
      this.chatLoop[lastIndex].latency = flowCommonLogic.calcElapsedTime(
        this.start_time,
        end_time,
      );
    } else {
      const end_time = new Date()?.getTime();
      currentAns.text = `${currentAns.text || ''}${currentAns.text ? '<br>': ''}${this.i18n.transform('stopped_generating')}`;
      currentAns.loading = false;
      this.chatLoop[lastIndex].latency = flowCommonLogic?.calcElapsedTime(
        this.start_time,
        end_time,
      );
    }
    this?.scrollToBottom();
    this.cdr.markForCheck();
  }

  public handleFocusStart() {
    this.isFocusState = true;
  }

  public handleInputStart() {
    if (this?.isFocusState) {
      this.isAnimating = true;
      this.isFocusState = false;
      this.cdr.markForCheck();
      setTimeout(() => {
        this.isAnimating = false;
        this.cdr?.markForCheck();
      }, 4000);
    }
  }

  public handleCollapsedStep(item) {
    item.collapsed = !item?.collapsed
  }

  public canSend(): boolean {
    const hasUnconfirmedAnswers = this?.chatLoop.some((item: any) =>
      item.showAnswer.some(
        (answer: any) => answer.isConfirmed === 'not-confirmed',
      ),
    );
    if (hasUnconfirmedAnswers) {
      return false;
    }

    return !this.isRequesting && !!this.questionInputed?.trim();
  }

  public quickSend(content: string): void {
    this.sendQuestion({ content });
  }

  public sendQuestion(e: any): void {
    this.questionInputed = e.content;
    if (!this.canSend()) {
      return;
    }
    this.curView = EViewType?.CHAT;
    this.chatView = EViewType?.CHAT_NOT_EMPTY;
    this.chatLoop.push(
      CommonLogic?.createFlowChatItem({
        query: this.questionInputed,
        dialogId: uuidV4(),
      })
    );
    // 把开始节点输入参数列表key-value，组装成流式接口入参
    let startInputs = this?.getRunWorkflowParams() || {};
    let globalInputs = this?.getRunWorkflowGlobalParams() || {};
    // 试运行里，针对非必填参数，若不填，则body体不带。避免出现{ 可选变量名:null }或{ 可选变量名:'' }
    startInputs = Object?.entries(startInputs).reduce((acc, [key, value]) => {
      if (!(isNil(value) || value === '' || isNaN(value))) {
        acc[key] = value;
      }
      return acc;
    }, {});
    globalInputs = Object.entries(globalInputs).reduce((acc, [key, value]) => {
      if (!(isNil(value) || value === '' || isNaN(value))) {
        acc[key] = value;
      }
      return acc;
    }, {});
    startInputs.query = this.questionInputed;
    const pluginConfs = this.buildPluginConfigs();
    this.debugWorkflow(startInputs, pluginConfs, this.chatLoop.length - 1, globalInputs);
    this.questionInputed = '';
    this?.scrollToBottom();
    this.cdr.markForCheck();
  }

  public changeCollapsedState(pluginForm: any) {
    const collapsed = pluginForm?.collapsed;
    pluginForm.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  /** 点赞按钮 */
  public likeAnswer(answer: any) {
    // 检查当前想点赞的回答是否已经点赞，如果是，则取消点赞
    if (answer?.isLike) {
      this.cancelFeedback(answer);
    } else {
      const params = {
        rating: FeedbackType.UPVOTE,
        app_name: this.flowInfo?.name,
      };
      this.appAgentServe
        .conversationFeedback(
          this.workflow_id,
          this.conversationId,
          answer.messageId,
          'workflow',
          params,
        )
        .then(() => {
          // 将点赞按钮设置为实心状态
          answer.isLike = true;
          answer.isDislike = false;
          this.cdr?.detectChanges();
        });
    }
  }

  /** 点踩抽屉的取消按钮 */
  public cancelDislike() {
    const scrollEvent = new Event('scroll');
    document.dispatchEvent(scrollEvent);
  }

  /** 点踩按钮 - 踩 or 取消踩 */
  public submitDislike(answer: any) {
    // 检查当前想点踩的回答是否已经点赞，如果是，则取消点赞
    if (answer.isDislike) {
      this.cancelFeedback(answer);
    } else {
      const params = {
        rating: FeedbackType.DOWNVOTE,
        app_name: this.flowInfo.name,
      };
      this.appAgentServe
        .conversationFeedback(
          this.workflow_id,
          this.conversationId,
          answer.messageId,
          'workflow',
          params,
        )
        .then((res) => {
          answer.isLike = false;
          answer.isDislike = true;
          this.cdr.detectChanges();
        });
    }
  }

  /** 点踩后提交反馈问题 */
  public submitDisLikeFeedback(params, answer) {
    const { selected, suggestions } = params;
    if (!selected?.length && !suggestions) {
      return;
    }
    const feedback = {
      rating: FeedbackType.DOWNVOTE,
      reason: {
        tags: selected.map((item) => item.label),
        content: suggestions,
      },
      app_name: this.flowInfo.name,
    };
    this.appAgentServe
      .conversationFeedback(
        this.workflow_id,
        this.conversationId,
        answer.messageId,
        'workflow',
        feedback,
      )
      .then((res) => {
        MessageComponent.showSuccess(
          this.i18n.transform('feedback_successful'),
        );
        this.closeDislikeTip();
      });
  }

  /** 点击输入节点的确定按钮 */
  public onConfirm(ans: any, item: any) {
    // 根据输入节点必填 非必填，动态进行校验
    let isInputNodeParamsPass = true;

    let inputs;
    item.showAnswer?.forEach(item => {
      if (item?.inputList && item?.inputList.length > 0) {
        inputs = item?.inputList;
      }
    });
    isInputNodeParamsPass = this.inputNodeParamsComp
      ? this.inputNodeParamsComp.checkInput(inputs)
      : true;
    if (!isInputNodeParamsPass) {
      return;
    }

    const allInputsFormGroup = this.appFlowServe?.getAnswerInputForm();
    this.appFlowServe.setAnswerInputForm(allInputsFormGroup);

    ans.isConfirmed = 'confirmed';
    const inputData = this.inputNodeParamsComp?.getDynamicParams(item.dialogId);
    const keys = Object?.keys(inputData || {});
    keys.forEach(key => {
      const param = inputData[key];
      if (param instanceof Array) {
        inputData[key] = JSON.stringify(inputData[key].map(obj => obj.url));
      }
    });

    this?.chatLoop.push(
      CommonLogic?.createFlowChatItem({
        query: this.getFormattedData(inputData),
        dialogId: uuidV4(),
      })
    );
    const pluginConfs = this?.buildPluginConfigs();
    this.debugWorkflow(
      { query: this.getFormattedData(inputData) },
      pluginConfs,
      this.chatLoop.length - 1,
    );
    this.scrollToBottom();
    this.cdr?.markForCheck();
  }

  /** 当调用点踩接口完成时，关闭Tip弹窗 */
  public closeDislikeTip() {
    const scrollEvent = new Event('scroll');
    document.dispatchEvent(scrollEvent);
  }

  public onFileUploadStatus(state: string, ans: any) {
    if (state === 'loading') {
      ans.isConfirmed = 'not-prepared';
    } else if (state === 'failed') {
      ans.isConfirmed = 'failed';
    } else {
      ans.isConfirmed = this?.inputList.some((inputItem) => inputItem.failed)
        ? 'failed'
        : 'not-confirmed';
    }
  }

  private formatToJsonData(formData) {
    return JSON.stringify(
      formData,
      (key, value) => {
        // 如果值是 undefined，返回 null
        if (value === undefined) {
          return null;
        }
        return value;
      },
      2
    );
  }

  private getNewJSONFormData(originFormData, newInputList) {
    const originKeys = Object.keys(originFormData);
    const formData = {};
    newInputList.forEach(item => {
      if (originKeys.includes(item.name)) {
        formData[item.name] = item.value?.default;
      }
    });
    return formData;
  }

  /** 更新开始节点的入参列表 */
  private updateInputParams(graphValue: any, workflowDetailValue: any) {
    const { nodes, configs } = this.appFlowServe.getUpdateGraphData(graphValue, workflowDetailValue).workflow_details;

    if (this.type === 'multi') {
      const { inputs } = workflowDetailValue?.details ?? {};
      if (!inputs) {
        return;
      }

      this.startNodeParams = this.getDebugConfigParams(inputs, CHAT_FILTER_KEYS);
    } else {
      // 存储已填的开始节点入参，确保在自动更新时不会丢失数据
      const startNode = nodes?.find(node => node?.type === 'Start') as IStartNode;
      if (!startNode) {
        return;
      }

      this.startNodeParams = this?.getDebugConfigParams(startNode.outputs, CHAT_FILTER_KEYS);

      this.globalConfigParams = this.getDebugConfigParams(cloneDeep(configs?.memory), CHAT_FILTER_KEYS) ?? [];
      this.globalConfigParams?.forEach(memo => {
        memo.required = false;
      });
    }
    this.startNodeParams = this?.addControlValueField(this.startNodeParams);

    // 若开始节点仅有一个系统入参query并且没有【插件鉴权参数】，直接展示对话页面，否则先展示配置页面
    if (!this.startNodeParams.length && !this.settingsList.length && !this.globalConfigParams.length) {
      this?.updateCurAndChatView();
    }
  }

  /** 开始节点的输入参数列表通过校验后，点击【开始运行】，获取表单key-value，作为run接口的入参 */
  private getRunWorkflowParams(skipFiles = false) {
    return this?.dynamicNodeParams?.getDynamicParams(skipFiles);
  }

  /** 开始节点的输入参数列表通过校验后，点击【开始运行】，获取表单key-value，作为run接口的入参 */
  private getRunWorkflowGlobalParams(skipFiles = false) {
    return this.globalParams?.getDynamicParams(skipFiles);
  }

  private debugWorkflow(inputs: any, pluginConfigs: IPluginConfig[], curIndex: number, memory_inputs?: any) {
    this.initializeNodeStatus();
    this.isRequesting = true;
    this.index = 0;
    this.isStreamFail = false;
    if (this?.isClearRunStatus) {
      this.appFlowServe?.setTokenData({});
    }
    this.nodeIdBlock = {};
    this.previousNodeId = '';
    this.isUserScrolling = false;
    this.hasSetPreviousNodeId = false;
    this.inputList = [];
    this.start_time = new Date().getTime();
    this.followUpQuestions = [];
    const longTermMemory = this.configServ.isSupportUserPersona()
      ? {
          long_term_memory: {
            // 记忆提取配置：未关联记忆库时关闭 retrieve/extract，避免后端空ID报错
            enable_retrieve: this.memoryLibId ? this.conversationState.isRetrieve : false,
            enable_extract: this.memoryLibId ? this.conversationState.isExtract : false,
            memory_repo_id: this.memoryLibId,
          },
        }
      : {};
    if (this.type === 'multi') {
      this.sseInstance = this.appAgentServe?.debugMultiAgentSSE(
        {
          inputs,
          ...longTermMemory,
          environment_id: this.environment_id,
        },
        this.workflow_id,
        this.conversationId,
        this.lang,
        this?.handleSSEEvents(curIndex),
        this.versionId
      );
    } else {
      if (this.chatLoop.length > 1) {
        memory_inputs = null;
      }
      const longTermMemory = this.configServ.isSupportUserPersona()
        ? {
          long_term_memory: {
            // 记忆提取配置：未关联记忆库时关闭 retrieve/extract，避免后端空ID报错
            enable_retrieve: this.memoryLibId ? this.conversationState.isRetrieve : false,
            enable_extract: this.memoryLibId ? this.conversationState.isExtract : false,
            memory_repo_id: this.memoryLibId,
          },
        }
        : {};
      const params: any = {
        inputs,
        memory_inputs: memory_inputs ?? {},
        globals: {},
        plugin_configs: pluginConfigs,
        version: this.version,
        ...longTermMemory,
      };
      if (this.environment_id) {
        params.environment_id = this.environment_id;
      }
      this.sseInstance = this.conversationServe.debugWorkflowSSE(
        params,
        this.workflow_id,
        this.conversationId,
        'DEBUG',
        this.lang,
        this?.handleSSEEvents(curIndex, () => {
          if (this.currWorkflow.workflow_details?.configs.additional_questions_config?.enable && this.nodeSet.size === 0) {
            this.isRecentQuestionVisible = true;
            return this.getNextQuestions();
          } else {
            this.isRecentQuestionVisible = false;
            return null;
          }
        }),
        this.versionId
      );
    }
  }

  /** 获取自动追问列表。该接口完成后，才能发送新一轮的问题 */
  private getNextQuestions() {
    this.isQuestionsLoading = true;
    this.isQuestionsFailed = false;
    const enable = this.currWorkflow.workflow_details?.configs.additional_questions_config?.enable;
    const params = {
      name: this.currWorkflow.workflow_details?.name,
      enable,
      prompt: enable ? this.currWorkflow.workflow_details?.configs.additional_questions_config?.prompt : '',
      version_id: this.versionId,
      model_name: this.currWorkflow.workflow_details?.configs?.default_model?.model_name,
      model_id: this.currWorkflow.workflow_details?.configs?.default_model?.model_deployment_id,
    };
    this.appAgentServe
      .getFlowNextQuestions(this.workflow_id, this.conversationId, params)
      .then(result => {
        this.isQuestionsLoading = false;
        const { questions } = result;
        if (!questions.length) {
          this.followUpQuestions = [];
          this.isQuestionsFailed = true;
          this.cdr.markForCheck();
          return;
        }
        this.followUpQuestions = questions;
        this.cdr.markForCheck();
        this.scrollToBottom();
      })
      .catch(() => {
        this.isQuestionsLoading = false;
        this.isQuestionsFailed = true;
        this.cdr.markForCheck();
      });
  }

  /** 取消反馈 */
  private cancelFeedback(content) {
    this.appAgentServe.cancelFeedback(this.workflow_id, this.conversationId, content.messageId).then(() => {
      content.isDislike = false;
      content.isLike = false;
      this.cdr.detectChanges();
    });
  }

  @HostListener('scroll', ['$event.target'])
  onScroll(target: any) {
    this.kbConfRef._results.forEach(element => {
      element.hide();
    });
    const currentScrollTop = target.scrollTop;

    // 判断是否向上滚动
    if (currentScrollTop < this?.lastScrollTop) {
      this.isUserScrolling = true;
    } else if (currentScrollTop + target?.clientHeight >= target.scrollHeight - 2) {
      this.isUserScrolling = false; // 滚动条手动滚到底部，再次自动滚动
    }
    this.lastScrollTop = currentScrollTop - 3;
  }

  public cdnUrl = cdnAssetUrl;
  tipContext: any = {};
  @ViewChildren('kbConfRef') kbConfRef;
  public onShowKbConfTip(e, row, i) {
    let arr = this.chatLoop.filter(item => item.execution_id && !item.showAnswer.some(ele => ele.isError));
    let tipIndex;
    arr.forEach((item, index) => {
      if (item.execution_id === row.execution_id && item.dialogId === row.dialogId) {
        tipIndex = index;
      }
    });
    this.kbConfRef._results.forEach(element => {
      element.hide();
    });
    e.stopPropagation();
    this.tipContext = {
      traceId: row.execution_id,
      outputs: {
        ok: ($event: string): void => {
          row.tagNum = Number($event);
          this.closeTag(tipIndex);
        },
      },
    };
    setTimeout(() => {
      this.kbConfRef._results[tipIndex].show();
    });
  }

  public like(e, row) {
    e.stopPropagation();
    let param = {
      span_Id: row.execution_id,
      vote: row.vote === 1 ? 0 : 1,
      data_type: 'trace',
    };
    this.sessioMgnService.vote(param).then(res => {
      row.vote = row.vote === 1 ? 0 : 1;
    });
  }

  public disLike(e, row) {
    e.stopPropagation();
    let param = {
      span_Id: row.execution_id,
      vote: row.vote === -1 ? 0 : -1,
      data_type: 'trace',
    };
    this.sessioMgnService.vote(param).then(res => {
      row.vote = row.vote === -1 ? 0 : -1;
    });
  }

  closeTag(i) {
    this.kbConfRef._results[i].hide();
  }

  override ngOnDestroy() {
    super.ngOnDestroy();
    this.kbAnswerResolverService.clear();
  }

  memoryConfirm(memoryData: IMemoryManagementData) {
    this.conversationState.isRetrieve = memoryData?.enable_retrieve ?? true;
    this.conversationState.isExtract = memoryData?.enable_extract ?? true;
  }

  get isQuestionsVisible() {
    return !this.isRequesting && !this.isStreamFail && this.isRecentQuestionVisible;
  }

  private adjustTopForNodeModal() {
    if (!this.nodeModalTop) {
      this.nodeModalTop = this.getContainerclientTop();
    }

    const modal = document.getElementById('runTestHalfModel');

    if (modal) {
      this.renderer.setStyle(modal, 'top', `${this.nodeModalTop}px`);
    }
  }
  private getContainerclientTop() {
    const container = document.getElementById('app-flow-container');
    return container?.getBoundingClientRect()?.top ?? 113;
  }

  showRunErrorTest() {
    this.clickErrorInfo.emit(null);
  }

  getStatusClassStr(status) {
    if (status === 'error') {
      return 'test-run-error';
    } else if (status === 'success') {
      return 'test-run-success';
    } else {
      return 'test-run-run';
    }
  }

  getStatusSrc(status) {
    if (status === 'error') {
      return this.cdnUrl('assets/agent-center/flow/testrun-error.svg');
    } else if (status === 'success') {
      return this.cdnUrl('assets/agent-center/flow/testrun-success.svg');
    } else {
      return this.cdnUrl('assets/agent-center/flow/testrun-run.svg');
    }
  }
}
