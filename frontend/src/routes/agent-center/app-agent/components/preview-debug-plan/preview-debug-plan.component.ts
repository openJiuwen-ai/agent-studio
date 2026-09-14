import {
  Component,
  Input,
  SimpleChanges,
  ViewChild,
  inject
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { AgentBotPageService } from "@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.service";
import { MemoryManagementComponent } from "@shared/components/memory-management/memory-management.component";
import {
  ConversationState,
  IMemoryManagementData
} from "@shared/components/memory-management/memory-management.interface";
import { MODULES } from "@shared/modules";
import { I18nNamespace } from "@i18n";
import { I18NEXT_NAMESPACE } from "angular-i18next";
import { TextFieldModule } from "@angular/cdk/text-field";
import flowCommonLogic from "../../../../agent-center/app-flow/common-logic-workflow";

import { AssetInterpreterIconComponent } from "@shared/components/assets/asset-interpreter-icon/asset-interpreter-icon.component";
import { AssetLogAgentIconComponent } from "@shared/components/assets/asset-log-agent-icon/asset-log-agent-icon.component";
import {
  VarConfigComponent
} from "../var-config/var-config.component";
import {
  SenderComponent
} from "@shared/components/sender/sender.component";
import { VarMemoryModalComponent } from "@routes/agent-center/app-agent/components/var-memory-modal/var-memory-modal.component";
import { LongMemoryModalComponent } from "@routes/agent-center/app-agent/components/long-memory-modal/long-memory-modal.component";
import { PreviewDebugComponent } from "@routes/agent-center/app-agent/components/preview-debug/preview-debug.component";
import { ChatItemPlanComponent } from "@routes/agent-center/app-agent/components/chat-item-plan/chat-item-plan.component";
import { PrologueQuestionsAreaComponent } from "@routes/app-center/components/prologue-questions-area/prologue-questions-area.component";
import { takeUntil } from "rxjs";
import { sceneMessageType, waitNodeType, SummaryResponse } from "@routes/agent-center/app-agent/components/preview-debug-plan/preview-debug-plan.interface";
import { NzMessageService } from "ng-zorro-antd/message";

@Component({
  selector: "preview-debug-plan",
  templateUrl: "./preview-debug-plan.component.html",
  styleUrls: ["./preview-debug-plan.component.less", "../../../../../styles/text-field-prebuilt.css"],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    AssetInterpreterIconComponent,
    VarConfigComponent,
    SenderComponent,
    VarMemoryModalComponent,
    LongMemoryModalComponent,
    ChatItemPlanComponent,
    PrologueQuestionsAreaComponent,
    MemoryManagementComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.TRACE, I18nNamespace.MEMORY_LIB]
    }
  ]
})
export class PreviewDebugPlanComponent extends PreviewDebugComponent {
  @ViewChild("sender") sender!: SenderComponent;
  @Input() shortCode?: string = "";
  @Input() agentWebInfo: any;

  agentBotPageService = inject(AgentBotPageService);

  msgServ = inject(NzMessageService);

  /**
   * 重写停止方法：关闭SSE后更新PlanExecute模式的状态为finished
   * 父类stopChat只处理了普通对话模式，没有更新sceneMessage.status和isFinished
   */
  override stopChat() {
    super.stopChat();
    const currentIndex = this.dialogHistory.length - 1;
    if (currentIndex >= 0) {
      this.updateStatus(currentIndex, "finished", true);
      if (this.dialogHistory[currentIndex]?.[0]) {
        this.dialogHistory[currentIndex][0].isFinished = true;
      }
      // super 只标记了第一条 assistant（sceneMessage），带 plans 的消息不走 summary 底部，
      // 这里补齐本轮全部 assistant 消息，确保最终答案消息也能展示"已停止生成"
      this.dialogHistory[currentIndex].forEach((item) => {
        if (item?.role === "assistant") {
          item.terminate = true;
        }
      });
      this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
    }
  }

  //上一次会话以中断节点结束，记录中断节点的index 跟当前index 比较 相邻则提取 思考ing
  public waitNode = {
    index: -1,
    sceneMessage: { role: "assistant", status: "loading", plans: [] }
  };
  public inputList = [];

  public step_idx = 0;

  conversationState: ConversationState = {
    isExtract: true,
    isRetrieve: true
  };

  get memoryLibId() {
    return this.agentWebInfo?.memoryLibId || this.agentBotPageService?.getMemoryLib()?.memory_repo_id || "";
  }

  override ngOnInit() {
    this.userQueryLimit =
      this.configServ.getConfigs().user_query_limit ?? 100000;

    this.previewDebugServ
      .updateSendMeta()
      .pipe(takeUntil(this.destroy$))
      .subscribe((res: boolean) => {
        if (res) {
          this.sendDisabled = false;
        }

      });
  }

  override ngOnChanges(changes: SimpleChanges): void {
    const { shortCode, agentWebInfo } = changes;
    if (shortCode && shortCode.currentValue) {
      this.canSend();
    }
    super.ngOnChanges(changes);
  }

  override canSend() {
    // 通过是否存在非空的model字段，判断是否为第三方模型
    if (this.shortCode) {
      this.sendDisabled = false;
    } else {
      super.canSend();
    }

  }

  override postStream(messages: any, currentIndex: number) {
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
    if (this.configServ.isSupportUserPersona() && this.configServ.isSupportMemoryInSingleAgent()) {
      messages.long_term_memory = { // 记忆提取配置
        enable_retrieve: this.conversationState.isRetrieve,
        enable_extract: this.conversationState.isExtract,
        memory_repo_id: this.memoryLibId
      };
    }
    if (this.shortCode) {
      this.sseInstance = this.appAgentServe.webPageChatSSE(
        messages,
        "agents",
        this.shortCode,
        this.uuid,
        "PUBLISHED",
        this.lang,
        this.getPlanSSECallbacks(currentIndex, false),
        "plan"
      );
    } else {
      this.sseInstance = this.appAgentServe.knowledgeChatSSE(
        messages,
        this.appId,
        this.uuid,
        "DEBUG",
        this.lang,
        this.getPlanSSECallbacks(currentIndex, false),
        this.versionId,
        "agents",
        false,
        "plan"
      );
    }
  }

  private getPlanSSECallbacks(currentIndex: number, isRegenerate: boolean) {
    return {
      onMessage: (token: any) => {
        try {
          const chunkDataObj =
            token.data && flowCommonLogic.stringToObject(token.data);
          this.handleMessage(chunkDataObj, currentIndex);
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
        // 兜底更新sceneMessage.status，确保SSE流结束时状态一定为finished
        const sceneMessage = this.getSceneMessage(currentIndex);
        if (sceneMessage && sceneMessage.status !== "finished") {
          sceneMessage.status = "finished";
          this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
        }
        this.agentDataServe.setHasQAFlag(hasHistory);
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      onError: (error: any) => {
        this.dialogHistory[currentIndex][0].reqErrorStatus = String(error?.source?.xhr?.status);
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
            this.msgServ.error(apiError, { nzDuration: 3000 });
          } catch {
            this.msgServ.error(this.i18n.transform("NetErrorTips"), { nzDuration: 3000 });
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
        // SSE超时：使用分类错误提示替代硬编码文案
        this.msgServ.error(this.i18n.transform("sse_timeout_model"), { nzDuration: 3000 });
        // 在dialogHistory中写入超时错误消息
        const currentIndex = this.dialogHistory.length - 1;
        if (currentIndex >= 0) {
          const errorItem = {
            event: "error",
            role: "assistant",
            content: this.i18n.transform("sse_timeout_model")
          };
          this.dialogHistory[currentIndex] = [
            ...this.dialogHistory[currentIndex],
            errorItem
          ];
          if (this.dialogHistory[currentIndex]?.[0]) {
            this.dialogHistory[currentIndex][0].isError = true;
          }
          this.updateStatus(currentIndex, "finished", true);
        }
        this.sseInstance?.close();
        this.scrollToBottom();
        this.cdr.markForCheck();
      }
    };
  }

  handleMessage(chunkDataObj: any, currentIndex: number): void {
    try {
      const { event, data, latency, content, createdTime } = chunkDataObj || {};
      const effectiveContent = content || (data && data.text);
      switch (event) {
        case "scene_match":
          this.handleSceneMatch(data, currentIndex);
          break;
        case "plan_end":
          this.handlePlanEnd(data, currentIndex);
          break;
        case "step_start":
          this.handleStepStart(data, currentIndex);
          break;
        case "step_end":
          this.handleStepEnd(data, currentIndex);
          break;
        case "plugin_start":
          this.handlePluginStart(chunkDataObj, currentIndex);
          break;
        case "plugin_end":
          this.handlePluginEnd(chunkDataObj, currentIndex);
          break;
        case "task_complete":
          this.handleTaskComplete(currentIndex);
          break;
        case "message":
          this.handleMessageEvent(effectiveContent, currentIndex, chunkDataObj);
          break;
        case "agent_interrupted":
          this.handleAgentInterrupted(currentIndex);
          break;
        case "statistic_data":
          this.handleStatisticData(latency, currentIndex);
          break;
        case "summary_response":
          this.handleSummaryResponse(content, createdTime, currentIndex, chunkDataObj);
          break;
        case "sensitive":
          this.handleSensitiveData(data, currentIndex);
          break;
        case "error":
          this.handleEventError(currentIndex, chunkDataObj);
          break;
        default:
          break;
      }
    } finally {
      this.isLoading = false;
    }
  }

  /**
   * 处理场景匹配事件
   */
  private handleSceneMatch(data: any, currentIndex: number): void {
    const sceneMessage: sceneMessageType = {
      plans: [{
        title: data?.scene_name ? this.i18n.transform("plan_model.tip_1") + data.scene_name : this.i18n.transform("plan_model.tip_4"),
        status: "finished"
      }, {
        id: "plan",
        title: this.i18n.transform("plan_model.tip_2"),
        status: "loading",
        steps: []
      }],
      role: "assistant",
      status: ""
    };

    this.dialogHistory[currentIndex] = [
      ...this.dialogHistory[currentIndex],
      sceneMessage
    ];
  }

  /**
   * 处理计划结束事件
   */
  private handlePlanEnd(data: any, currentIndex: number): void {
    if (data?.steps?.length) {
      const sceneMessage = this.getSceneMessage(currentIndex);
      if (sceneMessage) {
        const lastPlan = sceneMessage.plans[sceneMessage.plans.length - 1];
        lastPlan.steps = data.steps;
        lastPlan.status = "finished";
        this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
      }
    }
  }

  /**
   * 处理步骤开始事件
   */
  private handleStepStart(stepData: any, currentIndex: number): void {
    const sceneMessage = this.getSceneMessage(currentIndex);
    this.step_idx = stepData.step_idx;

    if (!stepData?.step_idx) return;
    if (stepData.step_idx === 1 && sceneMessage) {
      // 第一个步骤开始时创建新计划
      sceneMessage.plans.push({
        title: this.i18n.transform("plan_model.tip_3"),
        status: "loading",
        actionSteps: [
          { title: `1.${stepData?.step_name}`, actions: [] }
        ]
      });
    } else if (this.isNeedExtractNode(currentIndex)) {
      // 处理节点提取场景
      const extractSceneMessage = this.waitNode.sceneMessage;
      extractSceneMessage.plans.push({
        title: this.i18n.transform("plan_model.tip_3"),
        status: "loading",
        actionSteps: [
          { title: `1.${stepData?.step_name}`, actions: [] }
        ]
      });
      this.waitNode.index = -1;
      this.waitNode.sceneMessage = { role: "assistant", status: "loading", plans: [] };
      this.dialogHistory[currentIndex] = [
        ...this.dialogHistory[currentIndex],
        extractSceneMessage
      ];
    } else {
      // 添加到现有计划的步骤
      const lastPlan = sceneMessage.plans[sceneMessage.plans.length - 1];
      lastPlan.actionSteps.push({
        title: `${lastPlan.actionSteps.length + 1}.${stepData?.step_name}`,
        actions: []
      });
    }
    this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
  }

  /**
   * 处理步骤结束事件
   */
  private handleStepEnd(stepData: any, currentIndex: number): void {
    const sceneMessage = this.getSceneMessage(currentIndex);
    this.step_idx = stepData.step_idx;
    const lastPlan = sceneMessage.plans[sceneMessage.plans.length - 1];
    let action = lastPlan.actionSteps[lastPlan.actionSteps.length - 1];
    action.result_summary = stepData.result_summary;
    // 步骤错误标记：当步骤结果包含错误信息时标记步骤为错误状态
    if (stepData.result_summary && (
      stepData.result_summary.includes("失败") ||
      stepData.result_summary.includes("error") ||
      stepData.result_summary.includes("超时") ||
      stepData.result_summary.includes("终止")
    )) {
      action.status = "error";
    }
    this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
  }

  /**
   * 处理插件开始事件
   */
  private handlePluginStart(chunkDataObj: any, currentIndex: number): void {
    let tool = { name: "" };
    let type = "plugin";
    if (this.isUseSkill(chunkDataObj.plugin)) {
      type = "skill";
      tool.name = this.getSkillName(chunkDataObj.plugin.arguments);
    } else {
      tool = this.handlePluginInfo(chunkDataObj.plugin.name, chunkDataObj.type);
    }
    this.handleToolOrNode(currentIndex, tool.name, type);
  }


  /**
   * 处理插件结束事件
   */
  private handlePluginEnd(chunkDataObj: any, currentIndex: number): void {
    // 获取当前插件调用的结果
    const content = chunkDataObj?.content;
    const latency = chunkDataObj?.latency;
    
    // 获取当前的actions数组
    let actions = this.getAtions(currentIndex);
    if (actions && actions.length > 0) {
      // 更新最后一个action的内容和状态
      let lastAction = actions[actions.length - 1];
      
      // 如果有内容结果，判断成功/失败并显示简化信息
      if (content !== undefined && content !== null) {
        let displayContent = '';
        
        // 尝试解析content（可能是JSON数组格式）
        try {
          const parsedContent = typeof content === 'string' ? JSON.parse(content) : content;
          // 检查是否有error_code（错误码存在表示失败）
          const errorCode = this.extractErrorCode(parsedContent);
          
          if (errorCode) {
            // 失败情况：显示"调用失败，错误码：xxx"
            displayContent = `调用失败，错误码：${errorCode}`;
            lastAction.status = "error";
          } else {
            // 成功情况：显示"调用成功"
            displayContent = '调用成功';
            lastAction.status = "finished";
          }
        } catch {
          // 解析失败，当作成功处理
          displayContent = '调用成功';
          lastAction.status = "finished";
        }
        
        lastAction.content = displayContent;
      } else {
        lastAction.status = "finished";
      }
      
      // 如果有延迟信息，可以选择显示
      if (latency) {
        lastAction.latency = latency;
      }
      
      this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
    }
  }

  /**
   * 从content中提取错误码
   */
  private extractErrorCode(content: any): string | null {
    if (!content) return null;
    
    // 如果是数组，遍历查找error_code
    if (Array.isArray(content)) {
      for (const item of content) {
        if (item?.error_code) {
          return item.error_code;
        }
      }
    } else if (content?.error_code) {
      return content.error_code;
    }
    
    return null;
  }

  /**
   * 处理任务完成事件
   */
  private handleTaskComplete(currentIndex: number): void {
    this.updateStatus(currentIndex, "finished", true);
  }

  /**
   * 处理消息事件
   */
  private handleMessageEvent(content: string, currentIndex: number, chunkDataObj: any): void {
    if (this.dialogHistory[currentIndex]?.[0]) {
      this.dialogHistory[currentIndex][0].isFinished = true;
    }

    const hasExistingMessage = this.dialogHistory[currentIndex].some(
      (item) => item.role === "assistant" && (item.event === "message" || item.event === "sensitive")
    );

    if (hasExistingMessage) {
      this.updateStatus(currentIndex, "finished", true);
      this.handleWorkFlowEvent(currentIndex, chunkDataObj);
      return;
    }

    this.updateStatus(currentIndex, "finished", true);
    if (content && content.trim()) {
      const sceneMessage = this.getSceneMessage(currentIndex);
      if (sceneMessage) {
        // 如果已经通过sensitive事件更新过内容，不应再覆盖（避免敏感词过滤后的内容被未过滤的message内容覆盖）
        if (!this.sensitiveFlag) {
          sceneMessage.content = content;
          this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
        }
      } else {
        this.dialogHistory[currentIndex].push({
          role: "assistant",
          content: content,
          event: "message"
        });
      }
    }
    this.handleWorkFlowEvent(currentIndex, chunkDataObj);
  }

  /**
   * 处理代理中断事件
   */
  private handleAgentInterrupted(currentIndex: number): void {
    this.waitNode.index = currentIndex;
  }

  /**
   * 处理统计数据事件
   */
  private handleStatisticData(latency: number, currentIndex: number): void {
    const sceneMessage = this.dialogHistory[currentIndex].find(
      (item) => item.role === "assistant" && item.event === "error"
    );

    if (sceneMessage) {
      sceneMessage.time_consumption = latency;
    } else {
      const newItem = { role: "assistant", time_consumption: latency };
      this.dialogHistory[currentIndex] = [
        ...this.dialogHistory[currentIndex],
        newItem
      ];
    }

    this.endThink(currentIndex);
  }

  /**
   * 处理敏感词检测事件
   */
  private handleSensitiveData(data: any, currentIndex: number): void {
    this.sensitiveFlag = true;
    const { offset, text } = data;

    if (text && text.trim()) {
      const sceneMessage = this.getSceneMessage(currentIndex);

      if (sceneMessage && sceneMessage.content !== undefined) {
        const currentContent = sceneMessage.content;
        const safeOffset = Math.min(offset, currentContent.length);
        sceneMessage.content = currentContent.slice(0, safeOffset) + (text ?? "");
        sceneMessage.isFallbackReply = true;
        this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
      } else {
        this.dialogHistory[currentIndex].push({
          role: "assistant",
          content: text,
          event: "sensitive",
          isFallbackReply: true
        });
      }
    }

    this.endThink(currentIndex);
  }

  /**
   * 处理总结响应事件
   */
  private handleSummaryResponse(content: string, createdTime: string, currentIndex: number, chunkDataObj: any): void {
    if (createdTime) {
      this.dialogHistory[currentIndex][0].messageId = createdTime;
    }

    const quoteList = [];
    const finalContent = this.sensitiveFlag ? this.getLastMessageContent(currentIndex) : content;
    const sceneMessage = this.getSceneMessage(currentIndex);

    if (sceneMessage) {
      sceneMessage.status = "finished";
    }

    const existingSummary = this.dialogHistory[currentIndex].find(
      (item) => item.role === "assistant" && item.event === "summary_response"
    );

    if (existingSummary) {
      existingSummary.content = finalContent;
      existingSummary.res = finalContent;
      existingSummary.quoteList = quoteList;
      existingSummary.executionId = chunkDataObj.executionId;
      existingSummary.tagNum = 0;
    } else {
      this.dialogHistory[currentIndex].push({
        role: "assistant",
        event: "summary_response",
        content: finalContent,
        res: finalContent,
        quoteList,
        executionId: chunkDataObj.executionId,
        tagNum: 0,
        hasAssistant: true
      });
    }

    this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
    this.endThink(currentIndex);
  }

  /**
   * 处理错误事件
   */
  private handleEventError(currentIndex: number, chunkDataObj?: any): void {
    const existingMessage = this.dialogHistory[currentIndex].find(
      (item) => item.role === "assistant" && !item.plans && !item.content
    );

    // 从SSE error事件提取结构化错误信息
    const errorData = chunkDataObj?.data || chunkDataObj;
    const errorType = errorData?.error_reason || errorData?.error_type || "";
    const errorCode = errorData?.error_code || "";
    const userMessage = errorData?.error_msg || errorData?.message || "";

    // 根据error_type选择对应的i18n文案
    let errorMessage: string;
    if (errorType) {
      const i18nKeyMap: Record<string, string> = {
        "model_timeout": "sse_timeout_model",
        "gateway_timeout": "sse_timeout_gateway",
        "network_error": "sse_timeout_network",
        "iteration_exceeded": "sse_timeout_iteration",
      };
      const i18nKey = i18nKeyMap[errorType] || "sse_timeout_default";
      errorMessage = this.i18n.transform(i18nKey);
    } else if (userMessage) {
      // 如果有user_message但没有error_type，直接使用user_message
      errorMessage = userMessage;
    } else {
      errorMessage = this.i18n.transform("run_error");
    }

    if (existingMessage) {
      existingMessage.event = "error";
      existingMessage.content = errorMessage;
    } else {
      const errorItem = {
        event: "error",
        role: "assistant",
        content: errorMessage
      };
      this.dialogHistory[currentIndex] = [
        ...this.dialogHistory[currentIndex],
        errorItem
      ];
    }

    this.updateStatus(currentIndex, "finished", true);
    if (this.dialogHistory[currentIndex]?.[0]) {
      this.dialogHistory[currentIndex][0].isError = true;
    }
  }

  /**
   * 获取最后一条消息的内容
   */
  private getLastMessageContent(currentIndex: number): string {
    const lastMessage = this.dialogHistory[currentIndex]
      ?.filter((item) => item.role === "assistant" && item.content)
      ?.pop();
    return lastMessage?.content || "";
  }

  public getSceneMessage(currentIndex) {
    let sceneMessage: sceneMessageType = this.dialogHistory[currentIndex].find(
      (item) => item.role === "assistant" && item.plans
    );
    return sceneMessage;
  }

  public handleClickQuestion(questionItem: string) {
    this.sender.setContent(questionItem);
  }

  updateStatus(currentIndex, status, isScene?: boolean) {
    let sceneMessage = this.getSceneMessage(currentIndex);
    if (!sceneMessage) return;
    // 即使plans为空，也需要更新sceneMessage.status（如task_complete事件到达时plans可能尚未创建）
    if (isScene) {
      sceneMessage.status = status;
    }
    if (sceneMessage.plans?.length) {
      let plan = sceneMessage.plans[sceneMessage.plans.length - 1];
      plan.status = status;
    }
    this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
  }

  isNeedExtractNode(currentIndex) {
    return this.waitNode?.index >= 0 && currentIndex - this.waitNode?.index === 1;

  }

  handleWorkFlowEvent(currentIndex, chunkDataObj) {
    const {
      data
    } = chunkDataObj || {};
    if (data) {
      let { text, card, node_type, node_name, is_finished } = data;
      let hasAssistant = false;

      const updatedItem = this.dialogHistory[currentIndex].map(
        (item) => {
          return item;
        }
      );

      // 新增一个卡片消息
      if (node_type === "Card") {
        this.handleCards(currentIndex, data);
      }

      if (text && node_type !== "Input" && node_type !== "End" && node_type !== "Message" && !is_finished) {
        if (node_name) {
          this.handleToolOrNode(currentIndex, node_name, "workflow");
        }
        const hasSummary = this.updateSummary(updatedItem);
        updatedItem.push({
          event: "summary_response",
          role: "assistant",
          executionId: chunkDataObj.executionId,
          tagNum: 0,
          hasAssistant: hasAssistant,
          content: text,
          hasSummary: hasSummary
        });
      }

      if (!is_finished) {
        if (text && (node_type === "End" || node_type === "Message")) {
          if (this.hasEndNode(data)) {
            if (this.step_idx !== updatedItem[updatedItem.length - 1].step_idx) {
              updatedItem[updatedItem.length - 1].step_idx = this.step_idx;
              this.handleToolOrNodeAndContent(currentIndex, node_name, "workflow", node_type);
            }
            this.addContent(currentIndex, node_type, text);
          } else {
            if (node_name) {
              updatedItem[updatedItem.length - 1].step_idx = this.step_idx;
              this.handleToolOrNodeAndContent(currentIndex, node_name, "workflow", node_type);
            }
            this.addContent(currentIndex, node_type, text);
          }
        }
      }


      if (text && node_type === "Input") {
        const { inputs } = text && flowCommonLogic.stringToObject(text);
        this.inputList = inputs?.map((item) => {
          return {
            ...item,
            uniqueId: `${currentIndex}-${item.name}`
          };
        });
      }

      // 遇到最后一个node_type等于'Input'时，回答中出现表单
      if (node_type === "Input" && is_finished === true) {
        const hasSummary = this.updateSummary(updatedItem);
        updatedItem.push({
          event: "summary_response",
          role: "assistant",
          executionId: chunkDataObj.executionId,
          tagNum: 0,
          isConfirmed: "init",
          isShowInputParams: true,
          inputList: this.inputList,
          hasSummary: hasSummary
        });
        this.sendDisabled = true;
      }

      this.dialogHistory = [
        ...this.dialogHistory.slice(0, currentIndex),
        updatedItem,
        ...this.dialogHistory.slice(currentIndex + 1)
      ];
    }
  }

  updateSummary(updatedItem) {
    const hasSummary = updatedItem.find(item => {
      return item.event === "summary_response";
    });
    return !!hasSummary;
  }

  handleToolOrNode(currentIndex, name, type) {
    let actions = this.getAtions(currentIndex);
    actions.push({
      title: this.i18n.transform(this.getActionTitle(type), { name: name }),
      content: ""
    });
    this.dialogHistory[currentIndex] = [...this.dialogHistory[currentIndex]];
  }

  handleToolOrNodeAndContent(currentIndex, name, type, nodeType) {
    let actions = this.getAtions(currentIndex);
    actions.push({
      title: this.i18n.transform(this.getActionTitle(type), { name: name }),
      nodeType: nodeType,
      content: ""
    });
  }

  getActionTitle(type) {
    switch (type) {
      case "plugin":
        return "plan_model.action_1";
      case "skill":
        return "plan_model.action_3";
      default:
        return "plan_model.action_2";
    }
  }

  addContent(currentIndex, nodeType, content) {
    let actions = this.getAtions(currentIndex);
    let node = actions[actions.length - 1];
    if (nodeType === node.nodeType) {
      node.content = node.content + content;
    }
  }

  getAtions(currentIndex) {
    let sceneMessage = this.getSceneMessage(currentIndex);
    let plan = sceneMessage.plans[sceneMessage.plans.length - 1];
    let actionSteps = plan.actionSteps[plan.actionSteps.length - 1];
    let actions = actionSteps?.actions;
    return actions || [];
  }

  hasEndNode(data) {
    return data.index !== 0;
  }

  inputConfirm(event, currentIndex) {
    this.sendQuestion(
      event
    );
  }

  memoryConfirm(memoryData: IMemoryManagementData) {
    this.conversationState.isRetrieve = memoryData?.enable_retrieve ?? true;
    this.conversationState.isExtract = memoryData?.enable_extract ?? true;
  }

  handleCards(currentIndex, data) {
    let { card, is_finished } = data;
    const updatedItem = this.dialogHistory[currentIndex].map(
      (item) => {
        return item;
      }
    );
    let sceneMessage: SummaryResponse = {
      event: "summary_response",
      role: "assistant"
    };

    sceneMessage.isCard = true;
    //流会返回 两个card message

    if (!is_finished) {
      if (!sceneMessage?.cards) {
        sceneMessage.cards = [];
      }
      const is_card = sceneMessage.cards.find(
        (item) => item.node_id === data.node_id
      );
      if (!is_card) {
        sceneMessage.cards.push(data);
      }
      sceneMessage.cards.forEach((item, index) => {
        if (item.node_id === data.node_id) {
          if (card.context?.desc) {
            if (card.context.desc?.stream === "true") {
              sceneMessage.cards[index].desc =
                `${sceneMessage.cards[index].desc ?? ""}` +
                data.card.context.desc.answer;
            } else {
              sceneMessage.cards[index].desc =
                data.card.context.desc ?? "";
            }
          } else {
            sceneMessage.cards[index].desc =
              is_card?.card.context.desc ?? "";
          }

          if (card.context?.title) {
            if (card.context.title?.stream === "true") {
              sceneMessage.cards[index].title = `${
                sceneMessage.cards[index].title ?? ""
              }${data.card.context.title.answer}`;
            } else {
              sceneMessage.cards[index].title =
                data.card.context.title ?? "";
            }
          } else {
            sceneMessage.cards[index].title =
              is_card?.card.context.title ?? "";
          }
        }
      });
      const hasSummary = this.updateSummary(updatedItem);
      updatedItem.push({ ...sceneMessage, hasSummary: hasSummary });
    }
  }
}
