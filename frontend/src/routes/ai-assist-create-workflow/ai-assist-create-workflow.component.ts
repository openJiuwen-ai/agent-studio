import { CommonModule } from '@angular/common';
import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  AfterViewChecked,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject, takeUntil } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { CommonService } from '@services/common.service';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { IconUploadComponent } from '@routes/knowledge-center/knowledge/icon-upload.component';
import { ModelImageDataService } from '@routes/agent-center/app-agent/components/info-and-prompt-builder/model-image-src.service';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { AiAssistCreateHomeService } from '@routes/ai-assist-create-home/ai-assist-create-home.service';
import { AiAssistCreateWorkflowService } from '@routes/ai-assist-create-workflow/ai-assist-create-workflow.service';
import { AppMermaidDiagramComponent } from './app-mermaid-diagram.component';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService, NzModalRef } from 'ng-zorro-antd/modal';

import { CommonUtils } from 'src/utils/common.util';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { PublishVersionModalComponent } from '@shared/components/publish-version-modal/publish-version-modal.component';
import { AiAssistWorkflowPreviewComponent } from './components/flow-preview.component';
import { EditWorkflowNameComponent } from '@routes/ai-assist-create-workflow/edit-workflow-name/edit-workflow-name.component';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { FlowHelperService } from '@routes/agent-center/app-flow/utils/flow-helper.service';

const MERMAID_REGEX =
  /(?<definition>flowchart\s+[\s\S]*|graph\s+[\s\S]*|sequenceDiagram[\s\S]*)/i;

interface QuestionItem {
  question: string;
  options: string[];
  selected?: string;
}

interface TimelineGroup {
  type: 'states' | 'text';
  states?: any[];
  text?: string;
}

interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sopContent?: string;
  mermaidAnswer?: string;
  mermaidCode?: string;
  mermaidInfo?: any;
  questions?: QuestionItem[];
  directQuestions?: string[];
  time: Date;
  state0Messages?: any[];
  state4Messages?: string[];
  modifyPromptMessages?: string[];
  timelineGroups?: TimelineGroup[];
  isExpanded?: boolean;
  isStopped?: boolean;
  isPromptExpanded?: boolean;
}

@Component({
  selector: 'ai-assist-create-workflow',
  templateUrl: './ai-assist-create-workflow.component.html',
  styleUrls: ['./ai-assist-create-workflow.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    IconUploadComponent,
    LLMSelectComponent,
    AppMarkdownAnswerComponent,
    AppMermaidDiagramComponent,
    AiAssistWorkflowPreviewComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.COMMON,
        I18nNamespace.GUIDE,
        I18nNamespace.REVIEW,
      ],
    },
  ],
})
export class AiAssistCreateWorkflowComponent
  implements OnInit, OnDestroy, AfterViewChecked
{
  @ViewChild('textElement') textElement!: ElementRef<HTMLTextAreaElement>;
  @ViewChild('scrollContainer') scrollContainer!: ElementRef<HTMLElement>;
  @ViewChild('mermaidDiagramRef')
  mermaidDiagramRef!: AppMermaidDiagramComponent;

  private readonly DESTROY$ = new Subject<void>();
  public promptValue = '';
  public iconLoading = false;
  public workflowLogo = '';
  public iconValue = '';
  public chatHistory: ChatMessage[] = [];
  public isRunning = false;
  public lastUserQuery = '';
  public workflowUuid = uuidV4();
  public sseInstance: any;
  public lang = CommonUtils.getLanguage();
  public modelSelected = '';
  public changeUrl = cdnAssetUrl;
  public workflowName = '';
  public activeTab: 'flow' | 'preview' = 'flow';

  public currentNodeProcessData: any = null;
  public processLogs: any[] = [];
  public workflowRes: any;
  public workflow_id = '';
  public isPublished = false;
  public previewShow = false;
  public modifyPromptAnswer: any = null;
  public flowRetryCount = 0;
  public isUserScrolledUp = false;
  public isFullScreen = false;

  private latestIrDataStr = '';

  get latestMermaidCode(): string | undefined {
    const lastAssistantMsg = [...this.chatHistory]
      .reverse()
      .find((m) => m.mermaidCode);
    return lastAssistantMsg?.mermaidCode;
  }

  get latestMermaidName(): string | undefined {
    const lastAssistantMsg = [...this.chatHistory]
      .reverse()
      .find((m) => m.mermaidCode);
    return lastAssistantMsg?.mermaidInfo?.name;
  }

  constructor(
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private cdr: ChangeDetectorRef,
    private aiAssistCreateHomeService: AiAssistCreateHomeService,
    private aiAssistCreateWorkflowService: AiAssistCreateWorkflowService,
    private modelImageDataService: ModelImageDataService,
    private flowService: AppFlowRepoService,
    private commonService: CommonService,
    private i18n: I18NextEagerPipe,
    private router: Router,
    private route: ActivatedRoute,
    private tiMessage: NzMessageService,
    private tiModal: NzModalService,
    private appFlowServe: AppFlowService,
  ) {
    this.route.queryParams
      .pipe(takeUntil(this.DESTROY$))
      .subscribe((params) => {
        if (params.promptValue?.trim()) {
          this.promptValue = params.promptValue;
          if (false) {
            this.generationImage(this.promptValue);
          }
          this.onSend();
        }
      });
  }

  ngOnInit(): void {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.modelSelected = this.aiAssistCreateHomeService.modelName;
  }

  ngOnDestroy(): void {
    this.onStopGeneration();
    this.DESTROY$.next();
    this.DESTROY$.complete();
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
  }

  ngAfterViewChecked(): void {
    if (this.isRunning) {
      this.scrollToBottom();
    }
  }

  onScroll(): void {
    const element = this.scrollContainer?.nativeElement;
    if (element) {
      const distanceFromBottom =
        element.scrollHeight - element.scrollTop - element.clientHeight;
      this.isUserScrolledUp = distanceFromBottom > 50;
    }
  }

  public isGenerateGraph(): boolean {
    return this.activeTab === 'preview' && this.isRunning;
  }

  public changeToFlow(): void {
    if (!this.isGenerateGraph()) {
      this.activeTab = 'flow';
    }
  }

  private appendTextToTimeline(msg: ChatMessage, text: string) {
    if (!msg.timelineGroups) msg.timelineGroups = [];
    let lastGroup = msg.timelineGroups[msg.timelineGroups.length - 1];
    if (lastGroup && lastGroup.type === 'text') {
      lastGroup.text += text;
    } else {
      msg.timelineGroups.push({ type: 'text', text: text });
    }
  }

  private appendStateToTimeline(msg: ChatMessage, state: any) {
    if (!msg.timelineGroups) msg.timelineGroups = [];
    let lastGroup = msg.timelineGroups[msg.timelineGroups.length - 1];
    if (lastGroup && lastGroup.type === 'states') {
      lastGroup.states!.push(state);
    } else {
      msg.timelineGroups.push({ type: 'states', states: [state] });
    }
  }

  private async handleWorkflowIrData(irDataString: string): Promise<void> {
    if (!irDataString) return;
    try {
      const irData = JSON.parse(irDataString);
      const irParsed = JSON.parse(irData.ir);

      const result = await this.flowService.createFlow({
        code: irData.name_en,
        description: irData.description,
        name: irData.name,
        type: 'chat',
      } as any);

      this.workflowRes = result;
      this.workflowRes.workflow_details.edges = irParsed.edges;
      this.workflowRes.workflow_details.layouts = irParsed.layouts;
      this.workflowRes.workflow_details.nodes = irParsed.nodes;
      if (!this.workflowRes.workflow_details.configs) {
        this.workflowRes.workflow_details.configs = {};
      }
      this.workflowRes.workflow_details.configs.nl2workflow_first = true;
      this.workflowRes.name = this.workflowName || this.workflowRes.name;
      const { avatar, ...workflowDataWithoutAvatar } = this.workflowRes;

      if (this.iconValue) {
        this.workflowRes.avatar = this.iconValue;
      }

      const modifyRes = await this.flowService.modifyFlow(
        this.iconValue ? this.workflowRes : workflowDataWithoutAvatar,
      );

      this.workflow_id = modifyRes.workflow_id;
      this.workflowName = modifyRes.name;
      this.tiMessage.success(
        this.i18n.transform('workflow_success_create'),
      );

      const lastMsg = this.chatHistory[this.chatHistory.length - 1];
      if (lastMsg && lastMsg.role === 'assistant') {
        const prefix = lastMsg.content ? '\n\n' : '';
        lastMsg.content += `${prefix}已为您生成 ${modifyRes.name} 工作流`;

        if (!lastMsg.state4Messages) {
          lastMsg.state4Messages = [];
        }
        const workflowCreatedText = this.i18n.transform('workflow_created');
        lastMsg.state4Messages.push(workflowCreatedText);
        this.appendStateToTimeline(lastMsg, workflowCreatedText);
        this.cdr.markForCheck();

        setTimeout(() => {
          this.scrollToBottom();
        }, 50);
      }
    } catch (error) {
      console.error('处理工作流数据失败:', error);
    }
  }

  private displayErrorMsg(errData: any) {
    if (!errData) return;

    const lastMsg = this.chatHistory[this.chatHistory.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      const errMsg = errData.error_msg
        ? `错误信息：${errData.error_msg}  \n`
        : '';
      const errReason = errData.error_reason
        ? `错误原因：${errData.error_reason}  \n`
        : '';
      const errSuggest = errData.error_suggestion
        ? `修改建议：${errData.error_suggestion}  \n`
        : '';
      const errDetail = errData.message
        ? `错误详情：${errData.message}  \n`
        : '';
      const fullErrorText = `\n\n${errMsg}${errReason}${errSuggest}${errDetail}`;

      if (errMsg || errReason || errSuggest) {
        lastMsg.content += fullErrorText;
      } else if (errData.message || typeof errData === 'string') {
        const fallbackText =
          typeof errData === 'string' ? errData : errData.message;
        lastMsg.content += `错误：${fallbackText}`;
      }
    }

    this.isRunning = false;
    this.sseInstance?.close?.();
    this.handleStreamEnd();
    this.cdr.markForCheck();
  }

  private startStreaming(query: string) {
    this.isRunning = true;
    this.latestIrDataStr = '';
    this.currentNodeProcessData = null;
    this.processLogs = [];
    this.modifyPromptAnswer = null;

    const param: any = {
      query,
      model: {
        modelName: this.aiAssistCreateHomeService.modelName,
        modelExplicitName: this.aiAssistCreateHomeService.modelExplicitName,
        extension: {
          safetyBarrier: false,
          deploymentId: this.aiAssistCreateHomeService.modelName,
        },
        modelType: this.aiAssistCreateHomeService.modelType,
        modelInterfaceProtocol:
        this.aiAssistCreateHomeService.modelInterfaceProtocol,
      },
    };

    if (this.aiAssistCreateHomeService.authId) {
      param.model.extension.authId = this.aiAssistCreateHomeService.authId;
    }
    try {
      this.sseInstance = this.aiAssistCreateWorkflowService.createWorkflowChat(
        this.workflowUuid,
        param,
        this.lang,
        {
          onMessage: (event: any) => {
            let outerJson;
            try {
              outerJson = JSON.parse(event.data);
            } catch (e) {
              return;
            }

            const lastMsg = this.chatHistory[this.chatHistory.length - 1];
            if (lastMsg?.role !== 'assistant') return;

            if (outerJson.event === 'MESSAGE' && outerJson.data) {
              const { message_type, answer = '' } = outerJson.data;

              switch (message_type) {
                case 'message':
                case 'chitchat_chunk':
                  lastMsg.content += answer;
                  break;
                case 'sop_chunk':
                  lastMsg.sopContent = (lastMsg.sopContent || '') + answer;
                  this.appendTextToTimeline(lastMsg, answer);
                  break;
                case 'mermaid': {
                  lastMsg.mermaidAnswer =
                    (lastMsg.mermaidAnswer || '') + answer;
                  const match = lastMsg.mermaidAnswer.match(MERMAID_REGEX);
                  if (match) {
                    lastMsg.mermaidCode = match[0]
                      .replace(/```mermaid|```/gi, '')
                      .trim();
                  }

                  if (outerJson.data.mermaid_info) {
                    lastMsg.mermaidInfo = outerJson.data.mermaid_info;
                  }
                  this.appendTextToTimeline(lastMsg, answer);
                  break;
                }
                case 'question':
                  try {
                    lastMsg.questions = JSON.parse(answer);
                  } catch {
                    lastMsg.content += answer;
                  }
                  break;
                case 'question_no_opt':
                  if (!lastMsg.directQuestions) {
                    lastMsg.directQuestions = [];
                  }
                  try {
                    const parsedQuestions = JSON.parse(answer);
                    if (Array.isArray(parsedQuestions)) {
                      lastMsg.directQuestions.push(...parsedQuestions.map((q: any) => q.question));
                    } else {
                      lastMsg.directQuestions.push(answer);
                    }
                  } catch {
                    lastMsg.directQuestions.push(answer);
                  }
                  break;
                case 'state_0': {
                  if (!lastMsg.state0Messages) {
                    lastMsg.state0Messages = [];
                  }
                  const s0Text =
                    typeof answer === 'object' ? answer.answer : answer;
                  const statusId = outerJson.data.status_id;

                  if (s0Text) {
                    const isExist = lastMsg.state0Messages.some((m: any) => {
                      if (typeof m === 'string') return m === s0Text;
                      return m.text === s0Text;
                    });
                    if (!isExist) {
                      const stateObj = statusId ? { id: statusId, text: s0Text } : s0Text;
                      lastMsg.state0Messages.push(stateObj);
                      this.appendStateToTimeline(lastMsg, stateObj);
                    }
                  }
                  break;
                }
                case 'state_4': {
                  if (!lastMsg.state4Messages) {
                    lastMsg.state4Messages = [];
                  }
                  const s4Text =
                    typeof answer === 'object' ? answer.answer : answer;
                  if (s4Text && !lastMsg.state4Messages.includes(s4Text)) {
                    lastMsg.state4Messages.push(s4Text);
                    this.appendStateToTimeline(lastMsg, s4Text);
                  }
                  break;
                }
                case 'node_process':
                  this.currentNodeProcessData = outerJson.data;
                  this.currentNodeProcessData.remainTimeStr =
                    this.formatSeconds(
                      this.currentNodeProcessData?.details?.remaining_time,
                    );
                  this.processLogs.push(outerJson.data);
                  break;
                case 'workflow_agent_ir':
                  this.latestIrDataStr = answer;
                  break;
                case 'modify_prompt':
                  if (this.activeTab === 'preview') {
                    this.flowRetryCount = this.flowRetryCount + 1;
                  }
                  this.modifyPromptAnswer = answer;
                  this.currentNodeProcessData = null;
                  this.processLogs = [];

                  if (!lastMsg.modifyPromptMessages) {
                    lastMsg.modifyPromptMessages = [];
                  }
                  try {
                    const parsedAnswer = JSON.parse(answer);
                    if (Array.isArray(parsedAnswer)) {
                      lastMsg.modifyPromptMessages.push(...parsedAnswer);
                    } else {
                      lastMsg.modifyPromptMessages.push(answer);
                    }
                  } catch (e) {
                    lastMsg.modifyPromptMessages.push(answer);
                  }
                  break;
                default:
                  break;
              }
            }

            if (outerJson.event === 'error' && outerJson.data) {
              this.displayErrorMsg(outerJson.data);
              return;
            }

            if (outerJson.event === 'END') {
              this.isRunning = false;
              if (this.latestIrDataStr) {
                this.handleWorkflowIrData(this.latestIrDataStr);
              }
              this.handleStreamEnd();
            }
            this.cdr.markForCheck();
          },
          onDone: () => this.handleStreamEnd(),
          onError: (err: any) => {
            let errData = err;
            if (err && err.error) {
              errData = err.error;
            } else if (typeof err?.data === 'string') {
              try {
                errData = JSON.parse(err.data);
              } catch (e) {
                errData = err.data;
              }
            } else if (typeof err === 'string') {
              errData = JSON.parse(err);
            }
            const hasErrorDetails = errData?.error_code || errData?.error_msg || errData?.error_reason;
            if (hasErrorDetails) {
              this.displayErrorMsg(errData);
            } else if (
              errData &&
              (errData.message || typeof errData === 'string')
            ) {
              this.displayErrorMsg(errData);
            } else {
              this.handleStreamEnd();
            }
          },
        },
      );

      if (this.sseInstance && typeof this.sseInstance.catch === 'function') {
        this.sseInstance.catch((err: any) => {
          let errData = err?.error || err?.data || err;
          if (typeof errData === 'string') {
            errData = JSON.parse(errData);
          }
          this.displayErrorMsg(errData);
        });
      }
    } catch (err: any) {
      let errData = err?.error || err?.data || err;
      if (typeof errData === 'string') {
        try {
          errData = JSON.parse(errData);
        } catch (e) {}
      }
      this.displayErrorMsg(errData);
    }
  }

  onSend(): void {
    const text = this.promptValue.trim();
    if (this.isRunning || !text) return;

    if (this.workflow_id) {
      this.workflowUuid = uuidV4();
      this.workflow_id = '';
      this.workflowName = '';
      this.workflowRes = null;
      this.isPublished = false;

      this.chatHistory = [];
      this.activeTab = 'flow';
      this.previewShow = false;
      this.currentNodeProcessData = null;
      this.processLogs = [];
      this.flowRetryCount = this.flowRetryCount + 1;
      this.modifyPromptAnswer = null;

      this.latestIrDataStr = '';
      this.iconValue = '';
      this.workflowLogo = '';
    }

    this.isUserScrolledUp = false;

    this.lastUserQuery = text;
    this.chatHistory.push({
      id: uuidV4(),
      role: 'user',
      content: text,
      time: new Date(),
    });
    this.promptValue = '';

    setTimeout(() => {
      this.autoGrow();
    });

    this.chatHistory.push({
      id: uuidV4(),
      role: 'assistant',
      content: '',
      timelineGroups: [],
      time: new Date(),
      isExpanded: true,
    });
    this.startStreaming(text);
  }

  private handleStreamEnd() {
    this.isRunning = false;
    this.cdr.markForCheck();
    setTimeout(() => {
      this.scrollToBottom();
    }, 100);
  }

  onStopGeneration(): void {
    if (this.isRunning) {
      this.sseInstance?.close?.();
      const lastMsg = this.chatHistory[this.chatHistory.length - 1];
      if (lastMsg && lastMsg.role === 'assistant') {
        lastMsg.isStopped = true;
      }
    }
    this.isRunning = false;
    this.cdr.markForCheck();
  }

  autoGrow(): void {
    const textarea = this.textElement?.nativeElement;
    if (!textarea) {
      return;
    }
    textarea.style.height = 'auto';
    const newHeight = textarea.scrollHeight;

    if (newHeight > 200) {
      textarea.style.height = '200px';
      textarea.style.overflowY = 'auto';
    } else {
      const finalHeight = Math.max(24, newHeight);
      textarea.style.height = `${finalHeight}px`;
      textarea.style.overflowY = 'hidden';
    }
    this.cdr.markForCheck();
  }

  private scrollToBottom(force: boolean = false): void {
    if (!force && this.isUserScrolledUp) {
      return;
    }
    const element = this.scrollContainer?.nativeElement;
    if (element) {
      requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight;
      });
    }
  }

  changeModelSelected(e: any): void {
    this.aiAssistCreateHomeService.modelName = this.modelSelected =
      e.modelInfo.id;
    this.aiAssistCreateHomeService.authId = e.modelInfo.auth_id;
    this.aiAssistCreateHomeService.modelExplicitName = e.modelInfo.model_name;
    this.aiAssistCreateHomeService.modelType = e.modelInfo.model_type;
    this.aiAssistCreateHomeService.modelInterfaceProtocol =
      e.modelInfo.interface_protocol;
  }

  onToggleOption(q: QuestionItem, opt: string): void {
    q.selected = q.selected === opt ? undefined : opt;
  }

  async generationImage(prompt: string): Promise<void> {
    const cleanName = prompt.slice(0, 64).trim().replace(/[^\w\u4e00-\u9fff]/g, '');
    if (!cleanName) return;
    this.iconLoading = true;
    try {
      const res = await this.modelImageDataService.getModelImageData({
        name: cleanName,
        description: cleanName,
      });
      if (res?.icons) {
        this.iconValue = res.icons.icon;
        this.workflowLogo = res.icons.icon_detail;
      }
    } finally {
      this.iconLoading = false;
      this.cdr.markForCheck();
    }
  }

  trackByFn(index: number, item: ChatMessage) {
    return item.id || index;
  }

  onSubmitSelections(m: ChatMessage) {
    const sel = m.questions
      ?.filter((q) => q.selected)
      .map((q) => `${q.question}: ${q.selected}`);
    if (sel?.length) {
      this.promptValue = sel.join('; ');
      this.onSend();
    }
  }

  onRefresh() {
    if (
      this.isRunning ||
      this.chatHistory.length === 0 ||
      !this.lastUserQuery
    ) {
      return;
    }

    this.isUserScrolledUp = false;

    this.onStopGeneration();
    const lastMsg = this.chatHistory[this.chatHistory.length - 1];
    if (lastMsg?.role === 'assistant') {
      lastMsg.content = '';
      lastMsg.sopContent = '';
      lastMsg.mermaidAnswer = '';
      lastMsg.mermaidCode = '';
      lastMsg.mermaidInfo = undefined;
      lastMsg.questions = [];
      lastMsg.directQuestions = [];
      lastMsg.state0Messages = [];
      lastMsg.state4Messages = [];
      lastMsg.modifyPromptMessages = [];
      lastMsg.timelineGroups = [];
      lastMsg.isExpanded = true;
      lastMsg.isStopped = false;
      lastMsg.isPromptExpanded = false;
      this.startStreaming(this.lastUserQuery);
    }
  }

  onMermaidRefresh() {
    if (
      this.isRunning ||
      this.chatHistory.length === 0 ||
      !this.lastUserQuery
    ) {
      return;
    }

    this.isUserScrolledUp = false;

    this.onStopGeneration();

    // 重新生成 workflowUuid，开启新一轮会话
    this.workflowUuid = uuidV4();

    const lastMsg = this.chatHistory[this.chatHistory.length - 1];
    if (lastMsg?.role === 'assistant') {
      lastMsg.content = '';
      lastMsg.sopContent = '';
      lastMsg.mermaidAnswer = '';
      lastMsg.mermaidCode = '';
      lastMsg.mermaidInfo = undefined;
      lastMsg.questions = [];
      lastMsg.directQuestions = [];
      lastMsg.state0Messages = [];
      lastMsg.state4Messages = [];
      lastMsg.modifyPromptMessages = [];
      lastMsg.timelineGroups = [];
      lastMsg.isExpanded = true;
      lastMsg.isStopped = false;
      lastMsg.isPromptExpanded = false;

      // 使用新的 workflowUuid 重新发起流式请求
      this.startStreaming(this.lastUserQuery);
    }
  }

  backCreateHome() {
    if (!this.workflow_id) {
      this.tiModal.confirm({
        nzTitle: this.i18n.transform('exit_interrupt_workflow'),
        nzOnOk: (): void => {
          this.router.navigate(['/home/ai-assist-create-home'], {
            queryParams: { appType: 'workflow' },
          });
        },
      });
    } else {
      this.router.navigate(['/home/ai-assist-create-home'], {
        queryParams: { appType: 'workflow' },
      });
    }
  }

  determineGeneration() {
    this.promptValue = this.i18n.transform('confirm_and_generate');
    this.previewShow = true;
    this.activeTab = 'preview';
    this.onSend();
  }

  toEditWorkflow() {
    FlowHelperService.toEditWorkflow(this.router, { id: this.workflow_id });
  }

  public publishWorkflow() {
    const modalRef = this.tiModal.create({
      nzContent: PublishVersionModalComponent,
      nzWidth: 600,
      nzMaskClosable: false,
      nzFooter: null,
    });
    Object.assign(modalRef.componentInstance, {
      app_id: this.workflow_id,
      app_type: 'flow',
      workflowType: 'chat',
      title: this.i18n.transform('submit_version'),
    });
    (modalRef.componentInstance as any).outputs = {
      publishSuccess: () => {
        this.isPublished = true;
      },
      clickShare: () => {
        const cur_space_options = JSON.parse(
          StorageService.getSessionStorage('CUR_SPACE_OPTIONS'),
        );
        let cur_space_id = cur_space_options.id;
        const queryParams = {
          id: this.workflow_id,
          workspace_id: cur_space_id,
          tabId: 'releaseManage',
        };
        FlowHelperService.toEditWorkflow(this.router, queryParams);
      },
    };
  }

  handleLogoChange() {
    if (this.workflow_id) {
      this.flowService
        .modifyFlow({
          workflow_id: this.workflow_id,
          avatar: this.iconValue,
        })
        .then(() => {
          this.tiMessage.success(
            this.i18n.transform('workflow_success_create'),
          );
        });
    } else {
      this.iconValue = this.getIconPng();
    }
  }

  getIconPng() {
    if (this.workflowLogo.startsWith('data:image/png;base64')) {
      return this.iconValue;
    } else {
      return this.workflowLogo;
    }
  }

  editName() {
    this.tiModal.create({
      nzContent: EditWorkflowNameComponent,
      nzData: {
        workflowName: this.workflowName,
        outputs: {
          editName: (val) => {
            this.workflowName = val;
            if (this.workflow_id) {
              this.flowService
                .modifyFlow({
                  name: this.workflowName,
                  workflow_id: this.workflow_id,
                  update_time: this.appFlowServe.getVersionInfo(),
                }).then((res) => {
                this.tiMessage.success('修改成功');
                this.appFlowServe.setVersionInfo(res.update_time);
              });
            }
          },
        },
      },
      nzFooter: null,
    });
  }

  private formatSeconds(seconds = 0): string {
    seconds = Math.max(0, Math.floor(seconds));

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    seconds = seconds % 60;

    let result = '';

    if (hours > 0) {
      result += this.i18n.transform('hour_unit', { count: hours });
      result += this.i18n.transform('minute_unit', { count: minutes });
      result += this.i18n.transform('second_unit', { count: seconds });
    } else if (minutes > 0) {
      result += this.i18n.transform('minute_unit', { count: minutes });
      result += this.i18n.transform('second_unit', { count: seconds });
    } else {
      result += this.i18n.transform('second_unit', { count: seconds });
    }

    return result;
  }

  public toggleFullscreen(): void {
    this.isFullScreen = !this.isFullScreen;

    setTimeout(() => {
      window.dispatchEvent(new Event('resize'));
    }, 100);
  }
}
