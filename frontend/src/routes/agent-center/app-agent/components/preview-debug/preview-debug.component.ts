import { TextFieldModule } from "@angular/cdk/text-field";
import { CommonModule } from "@angular/common";
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  Output,
  SimpleChanges,
  ViewChild
} from "@angular/core";
import { ActivatedRoute } from "@angular/router";
import * as angularI18next from "angular-i18next";
import { I18NEXT_NAMESPACE } from "angular-i18next";
import { Subject, takeUntil } from "rxjs";
import { v4 as uuidV4 } from "uuid";
import { NzMessageService } from "ng-zorro-antd/message";
import { isEmpty } from "lodash";
import { NzDrawerService } from "ng-zorro-antd/drawer";
import { I18nNamespace } from "@i18n";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { ChatItemUpdateComponent } from "@routes/agent-center/app-agent/components/chat-item-update/chat-item-update.component";
import { LongMemoryModalComponent } from "@routes/agent-center/app-agent/components/long-memory-modal/long-memory-modal.component";
import { VarMemoryModalComponent } from "@routes/agent-center/app-agent/components/var-memory-modal/var-memory-modal.component";
import { IWorkflowField } from "@routes/agent-center/app-flow/node.type";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { ContextService } from "@services/context.service";
import { AssetInterpreterIconComponent } from "@shared/components/assets/asset-interpreter-icon/asset-interpreter-icon.component";
import {
  SendData,
  SenderComponent
} from "@shared/components/sender/sender.component";
import { MODULES } from "@shared/modules";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { CommonUtils } from "src/utils/common.util";
import flowCommonLogic from "../../../../agent-center/app-flow/common-logic-workflow";
import { IMemoParam } from "../create-memo/types";
import { PreviewMemosComponent } from "../preview-memos/preview-memos.component";
import {
  AgentVal,
  IAgentVar,
  VarConfigComponent
} from "../var-config/var-config.component";
import { MemoryVariableInputParamType } from "@routes/agent-center/interfaces/agent/app-agent.interface";
import { PreviewDebugService } from "@routes/agent-center/app-agent/components/preview-debug/preview-debug.service";

@Component({
  selector: "preview-debug",
  templateUrl: "./preview-debug.component.html",
  styleUrls: [
    "./preview-debug.component.less",
    "../../../../../styles/text-field-prebuilt.css"
  ],
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    AssetInterpreterIconComponent,
    VarConfigComponent,
    SenderComponent,
    VarMemoryModalComponent,
    LongMemoryModalComponent,
    ChatItemUpdateComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.TRACE]
    }
  ]
})

export class PreviewDebugComponent {
  @Input() previewDebugData = {
    name: "",
    icon: "",
    openText: "",
    openQuestions: [],
    deploymentId: ""
  };
  @Input() dispatchSelectedType = "";
  @ViewChild("chatContainerRef") chatContainerRef!: ElementRef;
  @ViewChild("varMemoryModalView") varMemoryModal: any;
  @ViewChild("longMemoryModalView") longMemoryModal: any;
  @ViewChild("varConfRef") varConfRef!: VarConfigComponent;
  @ViewChild("prologueTextEl") prologueTextEl!: ElementRef;
  @Output() expandDialogEnv = new EventEmitter<boolean>();

  public isShowStopIcon = false;
  public dialogHistory: any[][] = [];
  public sendDisabled = false;
  public isRequesting = false;
  public isLoading = false;
  public getOpenTextAndQuestions = {
    openText: "",
    openQuestions: []
  };
  public prologueTextOverflow = false;
  public isQuestionOverflow: Record<string, boolean> = {};

  public modelSelected = "";
  public memos: IMemoParam[] = [];
  public isStopped = false;
  public isTimeoutOrError = false;
  public agentInfo: any = {
    name: "",
    icon: ""
  };

  public isQuestionsLoading = false;
  // 自动追问接口是否失败。若失败，则隐藏【你可以继续提问】
  public isQuestionsFailed = false;
  /** 追问prompt是否打开 */
  public enable = false;
  /** 最近一轮问答对应的自动追问列表是否可见。对于已展示的最近一轮自动追问列表，不受追问开关的影响 */
  public isRecentQuestionVisible = false;

  public showMemo = false;
  public uuid = uuidV4();
  public isCodeInterpreter = false;

  public isCodeInterpreterActive = true;
  public isHovered = false;
  public changeUrl = cdnAssetUrl;
  public isF1 = this.ctxServ.isF1ReqList();

  public userQueryLimit;
  public agentParams: IWorkflowField[] = [];
  public isCloseAgentParamsPanel = false;
  public chatParams: IAgentVar[] = [];
  public isParamValid = true;

  private codeInterpreterId = "";
  /** 知识型Agent的名称。作为自动追问接口的入参 */
  public agentName = "";
  public lang = CommonUtils.getLanguage();

  /** 追问prompt的内容。作为自动追问接口的入参 */
  private prompt = "";
  public destroy$ = new Subject<void>();
  public sseInstance: any;
  appId = "";
  public modelInfoSelected: any = {};
  public pluginAndFlowList = {
    plugins: [],
    flows: [],
    kbs: []
  };

  public versionId = "";
  /** 表示用户是否向上滚动 */
  public isUserScrolling = false;
  /** 表示纵向滚动条的当前位置 */
  public lastScrollTop = 0;
  private isAutoScrolling = false;
  public deploymentId: string;
  public isDisabledSenderBtn: boolean = false;
  public isExpandDialog: boolean = false; // 控制对话框的伸缩功能
  private inputParams: MemoryVariableInputParamType[] = [];

  get codeInterpretTip() {
    if (!this.isCodeInterpreter) {
      return this.i18n.transform("codeInterpretTip1");
    } else if (this.isCodeInterpreterActive) {
      return this.i18n.transform("codeInterpretTip2");
    } else {
      return this.i18n.transform("codeInterpretTip3");
    }
  }

  get isQuestionsVisible() {
    return (
      !this.isRequesting &&
      !this.isStopped &&
      !this.isTimeoutOrError &&
      this.isRecentQuestionVisible
    );
  }

  constructor(
    public readonly i18n: angularI18next.I18NextEagerPipe,
    public cdr: ChangeDetectorRef,
    public appAgentServe: AppAgentRepoService,
    public agentDataServe: AgentDataService,
    public route: ActivatedRoute,
    public drawerServ: NzDrawerService,
    public ctxServ: ContextService,
    public configServ: AgentConfigService,
    public previewDebugServ: PreviewDebugService,
    private message: NzMessageService
  ) {
    this.route.queryParams.subscribe((params: any) => {
      this.appId = params.agentId;
    });

    this.agentDataServe
      .openTextAndQuestionsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((openTextAndQuestions: any) => {
        const { prologue, suggest_queries } = openTextAndQuestions;
        this.getOpenTextAndQuestions = {
          openText: prologue,
          openQuestions: suggest_queries
        };
        this.cdr.markForCheck();
        this.checkPrologueTextOverflow();
      });

    this.agentDataServe
      .promptAndModelConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((promptAndModelConfig: any) => {
        const { modelConfig } = promptAndModelConfig;
        this.modelInfoSelected = modelConfig;
        if (modelConfig?.model_name) {
          this.modelSelected = modelConfig.model_name;
        }
        if (modelConfig?.model_deployment_id) {
          this.deploymentId = modelConfig.model_deployment_id;
        }
        this.canSend();
      });

    this.agentDataServe
      .pluginAndFlowListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list: any) => {
        this.pluginAndFlowList = list;
        this.canSend();
      });

    this.agentDataServe
      .memosUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((memos) => {
        this.memos = memos;
      });

    this.agentDataServe
      .nameAndPromptConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((nameAndPrompt: any) => {
        const { name, prompt, enable } = nameAndPrompt;
        this.agentName = name;
        this.prompt = prompt;
        this.enable = enable;
        this.cdr.markForCheck();
      });

    // 订阅还原版本的工作流详情
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version) => {
        this.versionId = version.version_id;
      });

    this.agentDataServe
      .pluginListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((pluginList: any) => {
        this.isCodeInterpreter = pluginList.some(
          (plugin: any) => plugin.tool_display_name === "python_interpreter"
        );
        if (this.isCodeInterpreter) {
          this.isCodeInterpreterActive = true;
          this.codeInterpreterId = pluginList.find(
            (plugin: any) => plugin.tool_display_name === "python_interpreter"
          ).tool_id;
        }
        this.cdr.markForCheck();
      });

    this.agentDataServe
      .agentVarsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list) => {
        this.agentParams = list;

        if (this.agentParams.length) {
          this.checkIsParamValid();
        }
      });

    this.agentDataServe.inputMemoryInPreviewDebuggerUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list) => {
        this.inputParams = [];
        for (let index = 0; index < list.length; index++) {
          this.inputParams.push(list[index]);
        }
      });
  }

  getVarModal() {
    this.varMemoryModal.open();
  }

  ngOnInit() {
    this.userQueryLimit =
      this.configServ.getConfigs().user_query_limit ?? 100000;

  }

  ngOnChanges(changes: SimpleChanges): void {
    const { previewDebugData } = changes;
    if (previewDebugData) {
      const { name, icon, openText, openQuestions, deploymentId } =
        previewDebugData.currentValue;
      this.getOpenTextAndQuestions = { openText, openQuestions };
      this.agentInfo = {
        name,
        icon
      };
      this.deploymentId = deploymentId;
      this.cdr.markForCheck();
      this.checkPrologueTextOverflow();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private checkPrologueTextOverflow(): void {
    setTimeout(() => {
      const el = this.prologueTextEl?.nativeElement;
      if (el) {
        this.prologueTextOverflow = el.scrollHeight > el.clientHeight;
      }
      this.isQuestionOverflow = {};
      const questionEls = document.querySelectorAll('.suggest-question-text-style');
      const questions = this.getOpenTextAndQuestions.openQuestions || [];
      questionEls.forEach((qEl, index) => {
        if (questions[index]) {
          this.isQuestionOverflow[questions[index]] = qEl.scrollWidth > qEl.clientWidth;
        }
      });
      this.cdr.markForCheck();
    });
  }

  public openMemoModal() {
    this.drawerServ.create({
      nzWidth: "700px",
      nzPlacement: "bottom",
      nzHeight: "auto",
      nzClosable: false,
      nzMaskClosable: false,
      nzBodyStyle: { padding: 0, top: "0px" },
      nzContent: PreviewMemosComponent,
      nzContentParams: {
        agentId: this.appId,
        conversationId: this.uuid
      }
    });
  }

  public submitQuestion(question: string) {
    const chatContent = {
      role: "user",
      content: question
    };
    const oneChat = [chatContent];
    this.dialogHistory.push(oneChat);
    this.scrollToBottom();

    const messages = this.getDebugRunParam(this.dialogHistory.length - 1);
    this.postStream(messages, this.dialogHistory.length - 1);
    this.cdr.markForCheck();
  }

  public sendQuestion(chatContent: SendData) {
    const oneChat = [chatContent];
    this.dialogHistory.push(oneChat);
    this.isUserScrolling = false;
    this.scrollToBottom();

    const messages = this.getDebugRunParam(this.dialogHistory.length - 1, true);
    this.postStream(messages, this.dialogHistory.length - 1);
    this.cdr.markForCheck();
  }

  public probeQuestions(question: string) {
    this.submitQuestion(question);
  }

  // 过滤出 role 等于 "followUpQuestions" 的对象
  public getFollowUpQuestions(currentConversationPair: any[]): any[] {
    return currentConversationPair.filter(
      (item) => item.role === "followUpQuestions"
    );
  }

  public canSend() {
    // 通过是否存在非空的model字段，判断是否为第三方模型
    const isThirdPartyModel =
      !!this.modelInfoSelected?.model &&
      this.modelInfoSelected.model !== "" &&
      false;
    const isPluginAndFlowBound =
      this.pluginAndFlowList?.plugins?.length > 0 ||
      this.pluginAndFlowList?.flows?.length > 0 ||
      this.pluginAndFlowList?.kbs?.length > 0;
    this.sendDisabled =
      (isThirdPartyModel && isPluginAndFlowBound) ||
      !this.modelSelected ||
      this.modelSelected === this.i18n.transform("model_nodata") ||
      !this.isParamValid;
  }

  /** 点击底部的清空对话，开启新聊天 */
  public clearChat() {
    this.sseInstance?.close(); // 作用：上一轮对话中，断开 (cancel) 最后一个问题的流式接口
    this.isShowStopIcon = false; // 隐藏"停止生成"按钮
    this.dialogHistory = []; // 置空页面主体的多轮对话
    this.isRequesting = false; // 在新一轮对话中，保证能发送输入的新问题
    this.isLoading = false;
    this.uuid = uuidV4();
    this.agentDataServe.setHasQAFlag(false);
  }

  public onMouseEnter() {
    this.isHovered = true;
  }

  public onMouseLeave() {
    this.isHovered = false;
  }

  public toggleCodePlugin() {
    if (!this.isCodeInterpreter) {
      this.isCodeInterpreterActive = false;
      return;
    }
    this.isCodeInterpreterActive = !this.isCodeInterpreterActive;
  }

  public openLogModal() {
    this.agentDataServe.setCurrentConversationId(this.uuid);
    this.agentDataServe.setInsightBtnClicked(true);
  }

  public varConfConfirm(params: IAgentVar[] | null) {
    if (params?.length) {
      this.chatParams = params;
      this.checkIsParamValid();
    }

    this.isCloseAgentParamsPanel = true;
  }

  public showVarConfPanel() {
    this.isCloseAgentParamsPanel = false;
  }

  private checkIsParamValid() {
    setTimeout(() => {
      this.isParamValid = this.varConfRef?.isFormValid();
    });
  }

  public sensitiveFlag = false;

  private uploadInputsInMessages() {
    let result = {};
    for (let index = 0; index < this.inputParams.length; index++) {
      result[this.inputParams[index].key] = this.inputParams[index].value;
    }
    return result;
  }

  public postStream(messages: any, currentIndex: number) {
    // 开始新一轮问答前，先清空追问问题
    this.dialogHistory = this.dialogHistory.map((conversation) =>
      conversation.filter((item) => item.role !== "followUpQuestions")
    );
    this.sensitiveFlag = false;
    this.isRequesting = true;
    this.isLoading = true;
    this.isShowStopIcon = true;
    this.isTimeoutOrError = false;
    this.isStopped = false;
    this.isUserScrolling = false;
    messages.model_deployment_id = this.deploymentId ?? "";
    if (this.inputParams.length) {
      messages.inputs = this.uploadInputsInMessages();
    }
    this.sseInstance = this.appAgentServe.knowledgeChatSSE(
      messages,
      this.appId,
      this.uuid,
      "DEBUG",
      this.lang,
      {
        onMessage: (token: any) => {
          try {
            const chunkDataObj =
              token.data && flowCommonLogic.stringToObject(token.data);
            const {
              event,
              content,
              plugin,
              latency,
              createdTime,
              data,
              reasoning_content
            } = chunkDataObj || {};
            if (event === "error") {
              let assistantMessage = this.dialogHistory[currentIndex].find(
                (item) => item.role === "assistant"
              );
              if (assistantMessage) {
                assistantMessage.content = this.i18n.transform("run_error");
              } else {
                assistantMessage = {
                  role: "assistant",
                  content: this.i18n.transform("run_error")
                };
                this.dialogHistory[currentIndex] = [
                  ...this.dialogHistory[currentIndex],
                  assistantMessage
                ];
                // 对话运行失败时不能点赞踩的标识
                this.dialogHistory[currentIndex][0].isError = true;
              }
              this.endThink(currentIndex);
            }

            if (event === "plugin_start") {
              const { memory_variables } = plugin || {};
              let thought = this.getThought(currentIndex);
              if (
                memory_variables &&
                Object.keys(memory_variables).length > 0
              ) {
                const info = chunkDataObj;
                this.dialogHistory[currentIndex] = [
                  ...this.dialogHistory[currentIndex],
                  { ...info, role: "memorySet" }
                ];
                // 触发变更检测：更新 dialogHistory 的引用！！！
                this.dialogHistory = [
                  ...this.dialogHistory.slice(0, currentIndex),
                  this.dialogHistory[currentIndex],
                  ...this.dialogHistory.slice(currentIndex + 1)
                ];
              }
              if (thought !== "" && thought !== "\n\n" && thought !== "\n") {
                this.handlePluginCalls(chunkDataObj, currentIndex, thought);
              } else {
                this.handlePluginCalls(chunkDataObj, currentIndex);
              }
              this.endThink(currentIndex);
            }
            if (event === "plugin_end") {
              this.handlePluginCalls(chunkDataObj, currentIndex);
              this.endThink(currentIndex);
            }

            if (event === "message") {
              // 思考
              let thinkMessage = this.dialogHistory[currentIndex].findLast(
                (item) => item?.role?.startsWith("think")
              );
              let modelMessage = this.dialogHistory[currentIndex].findLast(
                (item) => item?.role?.startsWith("model")
              );
              let assistantMessage = this.dialogHistory[currentIndex].find(
                (item) => item.role === "assistant"
              );
              if (!thinkMessage || !assistantMessage || !modelMessage) {
                this.isLoading = false;
              }
              if (reasoning_content || content) {
                this.isLoading = false;
              }
              if (thinkMessage && thinkMessage.outputting && content) {
                // 追加大模型的中间输出
                if (content !== "\n\n" && content !== "\n") {
                  thinkMessage.reasoning_content += content;
                }

              } else if (modelMessage && modelMessage.outputting && reasoning_content) {
                if (reasoning_content !== "\n\n" && reasoning_content !== "\n") {
                  modelMessage.reasoning_content += reasoning_content;
                }
              } else {
                if (reasoning_content !== undefined && reasoning_content !== "\n\n" && reasoning_content !== "\n") {
                  modelMessage = {
                    role: "model" + uuidV4(),
                    thinking: true,
                    reasoning_content,
                    outputting: true
                  };
                  if (thinkMessage) {
                    this.endThink(currentIndex, "think");
                  }
                  this.dialogHistory[currentIndex] = [
                    ...this.dialogHistory[currentIndex],
                    modelMessage
                  ];
                }
                if (content !== undefined && content !== "\n\n" && content !== "\n") {
                  thinkMessage = {
                    role: "think" + uuidV4(),
                    thinking: true,
                    reasoning_content: content,
                    outputting: true
                  };
                  if (modelMessage) {
                    this.endThink(currentIndex, "model");
                  }
                  this.dialogHistory[currentIndex] = [
                    ...this.dialogHistory[currentIndex],
                    thinkMessage
                  ];
                }
              }
              if (assistantMessage) {
                if (content !== undefined && content !== "\n\n" && content !== "\n") {
                  // 追加大模型的中间输出
                  assistantMessage.content += content;
                }
                thinkMessage.thinking = false;
              } else {
                if (content !== undefined) {
                  assistantMessage = {
                    role: "assistant",
                    content
                  };
                  this.dialogHistory[currentIndex] = [
                    ...this.dialogHistory[currentIndex],
                    assistantMessage
                  ];
                }
              }
              this.dialogHistory = [
                ...this.dialogHistory.slice(0, currentIndex),
                this.dialogHistory[currentIndex],
                ...this.dialogHistory.slice(currentIndex + 1)
              ];
            }

            if (event === "statistic_data") {
              let hasAssistant = false;
              const updatedItem = this.dialogHistory[currentIndex].map(
                (item) => {
                  if (item.role === "assistant") {
                    hasAssistant = true;
                    return { ...item, time_consumption: latency };
                  }
                  return item;
                }
              );
              // 规避大模型总结之前没有返回任何的中间过程
              if (!hasAssistant) {
                updatedItem.push({
                  role: "assistant",
                  time_consumption: latency
                });
              }
              this.dialogHistory = [
                ...this.dialogHistory.slice(0, currentIndex),
                updatedItem,
                ...this.dialogHistory.slice(currentIndex + 1)
              ];
              this.endThink(currentIndex);
            }

            if (event === "summary_response") {
              if (createdTime) {
                // 赞踩反馈需要的messageId
                this.dialogHistory[currentIndex][0].messageId = createdTime;
              }
              // 规避大模型总结之前没有返回任何的中间过程
              let hasAssistant = false;
              let quoteList = [];
              // 如果存在event:"plugin_start"并且plugin.name等于 "retrieval"
              const hasRetrieval = this.dialogHistory[currentIndex].some(
                (item) =>
                  item.event === "plugin_start" &&
                  item.plugin?.name === "retrieval"
              );
              if (hasRetrieval) {
                const pluginEndItem = this.dialogHistory[currentIndex].find(
                  (item) =>
                    item.event === "plugin_end" && item.content?.output_list
                );
                if (pluginEndItem) {
                  // 根据 document_name 去重
                  const uniqueDocuments = new Map();
                  pluginEndItem.content?.output_list.forEach((item) => {
                    if (!uniqueDocuments.has(item.document_name)) {
                      uniqueDocuments.set(item.document_name, item);
                    }
                  });
                  quoteList = Array.from(uniqueDocuments.values());
                }
              }
              const updatedItem = this.dialogHistory[currentIndex].map(
                (item) => {
                  if (item.role === "assistant") {
                    hasAssistant = true;
                    let res = content ?? item.content;
                    return {
                      ...item,
                      content: res,
                      res,
                      quoteList,
                      executionId: chunkDataObj.executionId,
                      tagNum: 0
                    };
                  }
                  return item;
                }
              );
              if (!hasAssistant) {
                updatedItem.push({
                  role: "assistant",
                  executionId: chunkDataObj.executionId,
                  tagNum: 0,
                  content: content ?? "",
                  quoteList
                });
              }
              this.dialogHistory = [
                ...this.dialogHistory.slice(0, currentIndex),
                updatedItem,
                ...this.dialogHistory.slice(currentIndex + 1)
              ];
              this.endThink(currentIndex);
            }

            if (event === "sensitive") {
              this.sensitiveFlag = true;
              const { offset, text } = data;
              let assistantMessage = this.dialogHistory[currentIndex].find(
                (item) => item.role === "assistant"
              );

              if (assistantMessage) {
                // 替换大模型回答中的敏感词
                const curAnsText = assistantMessage?.content ?? "";
                const safeOffset = Math.min(offset, curAnsText.length);
                assistantMessage.content =
                  curAnsText.slice(0, safeOffset) + (text ?? "");
              }

              // 替换完成后，更新对话历史
              this.dialogHistory.splice(
                currentIndex,
                1,
                this.dialogHistory[currentIndex]
              );
              this.endThink(currentIndex);
            }
          } catch (error) {
          }
          this.scrollToBottom();
          if (this.isRequesting) {
            this.isShowStopIcon = true;
          }
          this.cdr.markForCheck();
        },
        onDone: () => {
          this.isRequesting = false;
          this.isLoading = false;
          if (this.enable) {
            this.getNextQuestions(currentIndex);
          } else {
            this.isRecentQuestionVisible = false;
          }
          this.isShowStopIcon = false;
          this.showMemo = true;
          const hasHistory =
            this.dialogHistory.length > 0 &&
            this.dialogHistory[0].some((item) => item.role === "assistant");
          this.dialogHistory[currentIndex][0].isFinished = true;
          this.agentDataServe.setHasQAFlag(hasHistory);
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
        onError: (error: { data: string; status: any }) => {
          // 对话运行失败时不能点赞踩的标识
          this.dialogHistory[currentIndex][0].isError = true;
          this.isRequesting = false;
          this.isLoading = false;
          this.isShowStopIcon = false;
          this.isTimeoutOrError = true;
          if (error.data) {
            try {
              const errInfo = JSON.parse(error.data);
              const apiError = errInfo?.error_msg
                ? this.i18n.transform("ApiError", {
                  errCode: errInfo.error_code,
                  reason: errInfo.error_msg
                })
                : "";
              this.message.error(apiError, { nzDuration: 3000 });
            } catch {
              this.message.error(this.i18n.transform("NetErrorTips"), { nzDuration: 3000 });
            }
          }
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
        onTimeout: () => {
          this.isRequesting = false;
          this.isLoading = false;
          this.isShowStopIcon = false;
          this.isTimeoutOrError = true;
          this.message.error(this.i18n.transform("streaming_timeout"), { nzDuration: 3000 });
          this.scrollToBottom();
          this.cdr.markForCheck();
        }
      },
      this.versionId
    );
  }

  /** 获取预览调试的run接口入参 */
  private getDebugRunParam(currentIndex: number, isUserInput: boolean = false) {
    const { content, uploadData } = this.dialogHistory[currentIndex][0] || {};
    let query = content;
    let files = [];
    if (uploadData?.[0]?.url && isUserInput) {
      query = `${JSON.stringify(uploadData.map((item) => item.url))} ${query}`;
      files = uploadData.map((item) => item.url);
    }
    let inputs: Record<string, AgentVal> = null;
    if (this.chatParams.length) {
      inputs = {};
      this.chatParams.forEach((param) => {
        if (["array", "object"].includes(param.type)) {
          try {
            inputs[param.name] = JSON.parse(param.val as string);
          } catch {
            inputs[param.name] = null;
          }
        } else {
          inputs[param.name] = param.val;
        }
      });
    }

    const debugRunParam: {
      query: string;
      files: string[];
      inputs?: Record<string, AgentVal>;
      tool_switch_dict?: Record<string, any>;
      long_term_memory?: Record<string, any>;
    } = {
      query,
      files
    };

    if (inputs && !isEmpty(inputs)) {
      debugRunParam.inputs = inputs;
    }

    // 添加代码解释器插件并关闭的情况，要多传一个tool_switch_dict
    if (this.isCodeInterpreter && !this.isCodeInterpreterActive) {
      debugRunParam.tool_switch_dict = {
        [this.codeInterpreterId]: false
      };

      return debugRunParam;
    }
    return debugRunParam;
  }

  /**
   * 阶段思考结束
   * @param currentIndex
   */
  endThink(currentIndex, key?: string) {
    let thinkMessage = this.dialogHistory[currentIndex].findLast((item) =>
      item?.role?.startsWith("think")
    );
    let modelMessage = this.dialogHistory[currentIndex].findLast((item) =>
      item?.role?.startsWith("model")
    );
    if (thinkMessage) {
      thinkMessage.outputting = false;
    }
    if (modelMessage) {
      modelMessage.outputting = false;
    }

  }

  /** 回答完成 或 发送新问题时，页面滚动条到最底部 */
  public scrollToBottom() {
    if (!this.isUserScrolling) {
      this.isAutoScrolling = true;
      setTimeout(() => {
        this.chatContainerRef.nativeElement.scrollTop = this.chatContainerRef.nativeElement.scrollHeight + this.chatContainerRef.nativeElement.clientHeight;
        setTimeout(() => {
          this.isAutoScrolling = false;
        }, 50);
      }, 0);
    }
  }

  public stopChat() {
    this.sseInstance?.close();
    this.isRequesting = false;
    this.isLoading = false;
    this.isShowStopIcon = false;
    this.isStopped = true;
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  private handlePluginCalls(data: any, currentIndex: number, thought?: string) {
    const index = this.dialogHistory[currentIndex].findIndex(
      (item) => item.role === "assistant"
    );
    if (index !== -1) {
      this.dialogHistory[currentIndex].splice(index, 1);
    }
    let tool = { name: "" };
    if (data?.plugin?.name) {
      if (data.plugin.name !== "retrieval") {
        if (this.isUseSkill(data.plugin)) {
          data.type = "skill";
          tool.name = this.getSkillName(data.plugin.arguments);
        } else {
          tool = this.handlePluginInfo(data.plugin.name, data.type);
        }
      } else {
        let kbList = data?.result?.output_list || [];
        tool = this.handleKbs(kbList);
      }
    }

    // 添加 thought key
    let modifiedPlugin;
    if (thought) {
      modifiedPlugin = { ...data.plugin, thought };
    } else {
      modifiedPlugin = { ...data.plugin };
    }
    if (modifiedPlugin) {
      modifiedPlugin = { ...modifiedPlugin, ...tool };
    }
    const info = { ...data, plugin: modifiedPlugin };
    this.dialogHistory[currentIndex] = [
      ...this.dialogHistory[currentIndex],
      info
    ];
    // 触发变更检测：更新 dialogHistory 的引用！！！
    this.dialogHistory = [
      ...this.dialogHistory.slice(0, currentIndex),
      this.dialogHistory[currentIndex],
      ...this.dialogHistory.slice(currentIndex + 1)
    ];
  }

  public handlePluginInfo(name, type) {
    let tool;
    if (type === "plugin" && this.pluginAndFlowList?.plugins?.length) {
      tool = this.pluginAndFlowList.plugins.find(item => (item.plugin_display_name + item.tool_display_name) === name);
      if (tool) {
        return { name: this.lang === "zh-cn" ? tool.tool_chinese_name : tool.tool_display_name, icon: tool.tool_icon };
      }

    }
    if (type === "workflow" && this.pluginAndFlowList?.flows?.length) {
      tool = this.pluginAndFlowList.flows.find(item => item.code === name);
      if (tool) {
        return { name: this.lang === "zh-cn" ? tool.workflow_name : tool.code, icon: tool.tool_icon };
      }
    }
    if (type === "mcp") {
      return { name: name };
    }
    return { name: name };
  }

  public isUseSkill(plugin) {
    const skillTool = ["read_file"];
    return skillTool.indexOf(plugin.name) > -1;
  }

  public getSkillName(skillString) {
    const regex = /\/skills\/[^\/]+\/(.*?)\//;
    const match = skillString.match(regex);
    if (match && match[1]) {
      return match[1];
    } else {
      return "Skill";
    }
  }

  handleKbs(kbList) {
    let tool;
    if (this.pluginAndFlowList.kbs.length && kbList.length) {
      tool = this.pluginAndFlowList.kbs.find(item => item.knowledge_repo_id === kbList[0].knowledge_base_id);
      if (tool) {
        return { name: tool.knowledge_repo_name };
      }
    }
    return { name: "retrieval" };
  }

  /** 组装插件调用的thought字段值 */
  private getThought(currentIndex: number): string {
    const index = this.dialogHistory[currentIndex].findIndex(
      (item) => item.role === "assistant"
    );
    let thought = "";
    if (index !== -1) {
      thought =
        this.dialogHistory[currentIndex].find(
          (item) => item.role === "assistant"
        ).content ?? "";
      this.dialogHistory[currentIndex].splice(index, 1);
    }
    return thought;
  }

  /** 获取自动追问列表。该接口完成后，才能发送新一轮的问题 */
  public getNextQuestions(currentIndex: number) {
    this.isQuestionsLoading = true;
    this.isQuestionsFailed = false;
    this.isRecentQuestionVisible = true;
    const params = {
      name: this.agentName,
      enable: this.enable,
      prompt: this.prompt,
      version_id: this.versionId
    };
    this.appAgentServe
      .getNextQuestions(this.appId, this.uuid, params)
      .then((result) => {
        this.isQuestionsLoading = false;
        const { questions } = result;
        if (!questions.length) {
          this.isQuestionsFailed = true;
          this.cdr.markForCheck();
          return;
        }
        const followUpQuestions = {
          role: "followUpQuestions",
          questions
        };
        this.dialogHistory[currentIndex] = [
          ...this.dialogHistory[currentIndex],
          followUpQuestions
        ];
        // 更新 dialogHistory 的引用以触发变更检测
        this.dialogHistory = [
          ...this.dialogHistory.slice(0, currentIndex),
          this.dialogHistory[currentIndex],
          ...this.dialogHistory.slice(currentIndex + 1)
        ];
        this.cdr.markForCheck();
        this.scrollToBottom();
      })
      .catch(() => {
        this.isQuestionsLoading = false;
        this.isQuestionsFailed = true;
        this.cdr.markForCheck();
      });
  }

  @ViewChild("chatItem") chatItemRef;

  @HostListener("scroll", ["$event.target"])
  onScroll(target: any) {
    if (this.chatItemRef) {
      this.chatItemRef?.kbConfRef?.hide();
    }
    if (this.isAutoScrolling) {
      return;
    }
    const currentScrollTop = target.scrollTop;

    if (currentScrollTop < this.lastScrollTop) {
      this.isUserScrolling = true;
    } else if (
      currentScrollTop + target.clientHeight >=
      target.scrollHeight - 2
    ) {
      this.isUserScrolling = false;
    }
    this.lastScrollTop = currentScrollTop;
  }

  public onClear() {
    this.clearChat();
  }

  // 控制对话框伸缩或者扩展
  public handleClickExpandDialog() {
    this.isExpandDialog = !this.isExpandDialog;
    this.expandDialogEnv.emit(this.isExpandDialog);
  }

  public getDisableSender(event) {
    this.isDisabledSenderBtn = event;
  }

  public getIsExpandDialog() {
    if (this.isExpandDialog) {
      return this.i18n.transform("collapse", {
        ns: I18nNamespace.TRACE
      });

    } else {
      return this.i18n.transform("expand", {
        ns: I18nNamespace.TRACE
      });
    }
  }

}
