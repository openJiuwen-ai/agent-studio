import { CommonModule } from '@angular/common';
import {
  Component,
  OnInit,
  OnDestroy,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
  AfterViewChecked,
  ViewChildren,
  QueryList,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { IconUploadComponent } from '@routes/knowledge-center/knowledge/icon-upload.component';
import { ModelImageDataService } from '@routes/agent-center/app-agent/components/info-and-prompt-builder/model-image-src.service';
import { cdnAssetUrl } from '../../single-spa/assets-url';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { AiAssistCreateHomeService } from '@routes/ai-assist-create-home/ai-assist-create-home.service';
import { Subject, takeUntil } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';
import { AiAssistCreateAgentService } from '@routes/ai-assist-create-agent/ai-assist-create-agent.service';
import { CommonUtils } from '../../utils/common.util';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { StorageService } from '@shared/services/cfdata.service';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService, NzModalRef } from 'ng-zorro-antd/modal';
import { PublishVersionModalComponent } from '@shared/components/publish-version-modal/publish-version-modal.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { ContextService } from '@services/context.service';
import { CommonService } from '@services/common.service';
import { AiAssistAgentPreviewComponent } from '@routes/ai-assist-agent-preview/ai-assist-agent-preview.component';
import { EditAgentNameComponent } from '@routes/ai-assist-create-agent/edit-agent-name/edit-agent-name.component';

interface QuestionItem {
  question: string;
  options: string[];
  selected?: string;
}

interface TimelineGroup {
  type: 'states' | 'text';
  states?: string[];
  text?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string; // 存放最终答复内容（chitchat_chunk）
  questions?: QuestionItem[];
  agentConfig?: any;
  time: Date;
  isStopped?: boolean;
  state4Messages?: string[]; // 保留作历史兼容
  timelineGroups?: TimelineGroup[]; // 按时间线记录思考过程
  isExpanded?: boolean;
  isChitchat?: boolean;
  hasThinkingData?: boolean;
}

@Component({
  selector: 'ai-assist-create-agent',
  templateUrl: './ai-assist-create-agent.component.html',
  styleUrls: ['./ai-assist-create-agent.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    IconUploadComponent,
    LLMSelectComponent,
    AppMarkdownAnswerComponent,
    AiAssistAgentPreviewComponent,
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
        I18nNamespace.AGENT,
      ],
    },
  ],
})
export class AiAssistCreateAgentComponent
  implements OnInit, OnDestroy, AfterViewChecked
{
  @ViewChild('textElement') textElement!: ElementRef;
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  @ViewChildren('messageItem') messageItems!: QueryList<ElementRef>;

  private readonly DESTROY$ = new Subject<void>();
  public promptValue = '';
  public iconLoading = false;
  public agentLogo = '';
  public iconValue = '';
  public chatHistory: ChatMessage[] = [];
  public isTyping = false;
  public lastUserQuery = '';
  public agentUuid = uuidV4();
  public sseInstance: any;
  public lang = CommonUtils.getLanguage();
  public modelSelected = '';
  public changeUrl = cdnAssetUrl;
  public agentName = '';
  public agentId = '';
  public isLoading = false;
  public isPublished = false;
  private previousScrollHeight = 0;
  public isUserScrolledUp = false;

  agentInfo: any = {
    agentId: '',
    name: '',
    icon: '',
    description: '',
    prompt: '',
    modelDeploymentId: '',
    enable: false,
    openText: '',
    openQuestions: [],
  };

  isExpandDialog: boolean = false;

  constructor(
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private modelImageDataService: ModelImageDataService,
    public router: Router,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private aiAssistCreateHomeService: AiAssistCreateHomeService,
    private aiAssistCreateAgentService: AiAssistCreateAgentService,
    private appService: AppAgentRepoService,
    public agentDataServe: AgentDataService,
    public configServ: AgentConfigService,
    private commonService: CommonService,
    private i18n: I18NextEagerPipe,
    private tiModal: NzModalService,
    private nzMessageService: NzMessageService,
    public ctxServ: ContextService,
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

    this.messageItems?.changes.pipe(takeUntil(this.DESTROY$)).subscribe(() => {
      this.scrollToBottom();
    });
  }

  ngOnDestroy(): void {
    this.onStopGeneration();
    this.DESTROY$.next();
    this.DESTROY$.complete();
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.aiAssistCreateHomeService.clearPersistedConfig();
  }

  ngAfterViewChecked(): void {
    if (this.isTyping) {
      const element = this.scrollContainer?.nativeElement;
      if (element && element.scrollHeight !== this.previousScrollHeight) {
        this.previousScrollHeight = element.scrollHeight;
        this.scrollToBottom();
      }
    }
  }

  onScroll(): void {
    const element = this.scrollContainer?.nativeElement;
    if (element) {
      const distanceFromBottom = element.scrollHeight - element.scrollTop - element.clientHeight;
      this.isUserScrolledUp = distanceFromBottom > 50;
    }
  }

  async generationImage(prompt: string): Promise<void> {
    this.iconLoading = true;
    try {
      const res = await this.modelImageDataService.getModelImageData({
        name: prompt.replace(/\s+/g, '').slice(0, 64).trim(),
        description: prompt.replace(/\s+/g, '').slice(0, 64).trim(),
      });
      if (res?.icons) {
        this.iconValue = res.icons.icon;
        this.agentLogo = res.icons.icon_detail;
      }
    } finally {
      this.iconLoading = false;
      this.cdr.markForCheck();
    }
  }

  onSend(): void {
    const text = this.promptValue.trim();
    if (this.isTyping || !text) {
      return;
    }

    if (this.agentId) {
      this.resetStateForNewConversation();
    }

    this.isUserScrolledUp = false;
    this.lastUserQuery = text;
    this.chatHistory.push({ role: 'user', content: text, time: new Date() });

    this.promptValue = '';
    setTimeout(() => {
      this.autoGrow();
    });

    this.chatHistory.push({
      role: 'assistant',
      content: '',
      timelineGroups: [],
      time: new Date(),
      isExpanded: true,
      hasThinkingData: false,
    });
    this.startStreaming(text);
  }

  private displayErrorMsg(errData: any) {
    if (!errData) {
      return;
    }
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

    this.isTyping = false;
    this.sseInstance?.close?.();
    this.cdr.markForCheck();
    setTimeout(() => this.scrollToBottom(), 100);
  }

  private startStreaming(query: string) {
    this.isTyping = true;
    const param:any = {
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
      this.sseInstance = this.aiAssistCreateAgentService.createAgentChat(
        this.agentUuid,
        param,
        this.lang,
        {
          onMessage: (event: any) => {
            if (!event?.data) {
              return;
            }

            let outerJson: any;
            try {
              outerJson = JSON.parse(event.data);
            } catch (error) {
              return;
            }

            // 捕获后端的 Error 事件并分发给格式化方法
            if (outerJson.event === 'error') {
              this.displayErrorMsg(outerJson.data || outerJson);
              return;
            }

            const lastMsg = this.chatHistory[this.chatHistory.length - 1];
            if (lastMsg?.role !== 'assistant') {
              return;
            }

            if (outerJson.event === 'MESSAGE' && outerJson.data) {
              const { message_type, answer } = outerJson.data;

              if (message_type === 'llm_agent_ir_chunk') {
                lastMsg.hasThinkingData = true;

                if (!lastMsg.timelineGroups) lastMsg.timelineGroups = [];
                let lastGroup = lastMsg.timelineGroups[lastMsg.timelineGroups.length - 1];
                if (lastGroup && lastGroup.type === 'text') {
                  lastGroup.text += answer || '';
                } else {
                  lastMsg.timelineGroups.push({ type: 'text', text: answer || '' });
                }
              } else if (message_type === 'chitchat_chunk') {
                lastMsg.isChitchat = true;
                lastMsg.content += answer || '';
              } else if (message_type === 'question') {
                try {
                  lastMsg.questions =
                    typeof answer === 'string' ? JSON.parse(answer) : answer;
                } catch {
                  lastMsg.content += answer || '';
                }
              } else if (message_type === 'llm_agent_ir') {
                try {
                  const config =
                    typeof answer === 'string' ? JSON.parse(answer) : answer;
                  lastMsg.agentConfig = config;

                  if (!this.agentId) {
                    this.createAgentApp(config);
                  }

                  setTimeout(() => this.scrollToBottom(), 0);
                } catch (error: any) {}
              } else if (message_type === 'state_4') {
                lastMsg.hasThinkingData = true;

                if (!lastMsg.state4Messages) {
                  lastMsg.state4Messages = [];
                }
                const s4Text =
                  typeof answer === 'object' ? answer.answer : answer;
                if (s4Text && !lastMsg.state4Messages.includes(s4Text)) {
                  lastMsg.state4Messages.push(s4Text);

                  if (!lastMsg.timelineGroups) lastMsg.timelineGroups = [];
                  let lastGroup = lastMsg.timelineGroups[lastMsg.timelineGroups.length - 1];
                  if (lastGroup && lastGroup.type === 'states') {
                    lastGroup.states!.push(s4Text);
                  } else {
                    lastMsg.timelineGroups.push({ type: 'states', states: [s4Text] });
                  }
                }
              }
            }
            if (outerJson.event === 'END') {
              this.isTyping = false;
              setTimeout(() => this.scrollToBottom(), 100);
            }
            this.cdr.markForCheck();
            this.scrollToBottom();
          },
          onDone: () => {
            this.isTyping = false;
            this.cdr.markForCheck();
          },
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
              try {
                errData = JSON.parse(err);
              } catch(e) {}
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
              this.isTyping = false;
              this.cdr.markForCheck();
            }
          },
        },
      );

      // 捕获可能的同步/初始化错误
      if (this.sseInstance && typeof this.sseInstance.catch === 'function') {
        this.sseInstance.catch((err: any) => {
          let errData = err?.error || err?.data || err;
          if (typeof errData === 'string') {
            try {
              errData = JSON.parse(errData);
            } catch (e) {}
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

  onStopGeneration(): void {
    if (this.isTyping) {
      this.sseInstance?.close?.();
      const lastMsg = this.chatHistory[this.chatHistory.length - 1];
      if (lastMsg?.role === 'assistant') {
        lastMsg.isStopped = true;
      }
    }
    this.isTyping = false;
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
    const element = this.scrollContainer?.nativeElement;
    if (element && (!this.isUserScrolledUp || force)) {
      requestAnimationFrame(() => {
        element.scrollTop = element.scrollHeight;
      });
    }
  }

  changeModelSelected(e: any): void {
    this.aiAssistCreateHomeService.modelName = this.modelSelected = e.modelInfo.id;
    this.aiAssistCreateHomeService.authId = e.modelInfo.auth_id;
    this.aiAssistCreateHomeService.modelExplicitName = e.modelInfo.model_name;
    this.aiAssistCreateHomeService.modelType = e.modelInfo.model_type;
    this.aiAssistCreateHomeService.modelInterfaceProtocol =
      e.modelInfo.interface_protocol;
  }

  onToggleOption(q: any, opt: string): void {
    q.selected = q.selected === opt ? undefined : opt;
  }

  async createAgentApp(config: any) {
    this.isLoading = true;
    const res = await this.appService.createAgent({
      name: config.name || '',
      description: config.description || '',
    });
    if (res?.agent_id) {
      let params: any = {
        instructions: config.instructions,
        model_name: config.model_name,
        model_deployment_id: config.model_deployment_id,
        model_config: config.model_config || {},
        tool_details: config.tools || [],
        knowledge_repos: config.knowledge_repos || [],
        workflow_details: config.workflows || [],
        scheduling_mode: 'ReAct',
      };

      if (this.iconValue) {
        params.icon = this.iconValue;
      }
      this.appService
        .triggerSave(res.agent_id, params)
        .then(async (result) => {
          this.agentId = result.agent_id;
          this.agentName = this.agentName || result.name;
          this.nzMessageService.success(
            this.i18n.transform('agent_success_create'),
          );

          const lastMsg = this.chatHistory[this.chatHistory.length - 1];
          const successMsg = `已为您生成${result.name}智能体`;
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.content = lastMsg.content ? lastMsg.content + `\n\n${successMsg}` : successMsg;
          }
          this.cdr.markForCheck();

          this.agentInfo = {
            agentId: result.agent_id,
            name: result.name,
            icon: result.icon,
            prompt: result?.additional_questions_config?.prompt || '',
            modelDeploymentId: result.model_deployment_id,
            enable: result?.additional_questions_config?.enable || false,
            openText: '',
            openQuestions: [],
          };

          // 生成开场白
          const generateRes = await Promise.all([
            this.appService.generatePrologue(this.agentId),
            this.appService.generateQuestions(this.agentId),
          ]);
          const [prologueRes, questionRes] = generateRes;
          this.agentInfo.openText = prologueRes?.prologue || '';
          if (
            questionRes &&
            Array.isArray(questionRes.questions) &&
            questionRes.questions.length
          ) {
            this.agentInfo.openQuestions = [...questionRes.questions];
          }
          // 更新开场白到智能体
          this.appService.triggerSave(this.agentId, {
            suggest_queries: this.agentInfo.openQuestions || [],
            prologue: this.agentInfo.openText || '',
          });

        })
        .finally(() => {
          this.isLoading = false;
        });
    }
  }

  onSubmitSelections(m: any) {
    const sel = m.questions
      .filter((q: any) => q.selected)
      .map((q: any) => `${q.question}：${q.selected}；`);

    if (sel.length) {
      this.promptValue = sel.join('\n');
      this.onSend();
    }
  }

  onRefresh() {
    if (this.isTyping || !this.lastUserQuery) {
      return;
    }

    this.isUserScrolledUp = false;

    this.onStopGeneration();
    const last = this.chatHistory[this.chatHistory.length - 1];
    if (last?.role === 'assistant') {
      last.content = '';
      last.questions = [];
      last.agentConfig = null;
      last.isStopped = false;
      last.state4Messages = [];
      last.timelineGroups = [];
      last.isExpanded = true;
      last.isChitchat = false;
      last.hasThinkingData = false;
    }
    this.startStreaming(this.lastUserQuery);
  }

  backCreateHome() {
    if (!this.agentId) {
      this.tiModal.confirm({
        nzTitle: this.i18n.transform('exit_interrupt'),
        nzOnOk: (): void => {
          this.router.navigate(['/home/ai-assist-create-home'], {
            queryParams: { appType: 'agent' },
          });
        },
      });
    } else {
      this.router.navigate(['/home/ai-assist-create-home'], {
        queryParams: { appType: 'agent' },
      });
    }
  }

  handleLogoChange() {
    if (this.agentId) {
      this.appService
        .triggerSave(this.agentId, { icon: this.getIconPng() })
        .then(() => {
          this.nzMessageService.success('修改成功');
        });
    } else {
      this.iconValue = this.getIconPng();
    }
  }

  getIconPng() {
    if (this.agentLogo.startsWith('data:image/png;base64')) {
      return this.iconValue;
    } else {
      return this.agentLogo;
    }
  }

  toEditAgent() {
    if (this.agentId) {
      this.router.navigate(['/home/agent-center/app-agent/detail'], {
        queryParams: { agentId: this.agentId },
      });
    }
  }

  public publishAgent() {
    const modalRef = this.tiModal.create({
      nzContent: PublishVersionModalComponent,
      nzWidth: 600,
      nzMaskClosable: false,
      nzFooter: null,
    });
    Object.assign(modalRef.componentInstance, {
      app_id: this.agentId,
      app_type: 'agent',
      isFromDevelopSpace: false,
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
          agentId: this.agentId,
          workspace_id: cur_space_id,
          tabId: 'releaseManage',
        };
        this.router.navigate(['/home/agent-center/app-agent/detail'], {
          queryParams: queryParams,
        });
      },
    };
  }

  editName() {
    this.tiModal.create({
      nzContent: EditAgentNameComponent,
      nzData: {
        agentName: this.agentName,
        outputs: {
          editName: (val) => {
            this.agentName = val;
            if (this.agentId) {
              this.appService
                .triggerSave(this.agentId, { name: this.agentName })
                .then(() => {
                  this.nzMessageService.success('修改成功');
                });
            }
          },
        },
      },
      nzFooter: null,
    });
  }

  public handleClickExpandDialog(data) {
    this.isExpandDialog = data;
  }

  private resetStateForNewConversation(): void {
    if (this.isTyping) {
      this.onStopGeneration();
    }

    this.agentId = '';
    this.agentName = '';
    this.agentLogo = '';
    this.iconValue = '';
    this.isPublished = false;
    this.isExpandDialog = false;

    this.agentInfo = {
      agentId: '',
      name: '',
      icon: '',
      description: '',
      prompt: '',
      modelDeploymentId: '',
      enable: false,
      openText: '',
      openQuestions: [],
    };

    this.chatHistory = [];
    this.lastUserQuery = '';
    this.isUserScrolledUp = false;

    this.agentUuid = uuidV4();
  }
}
