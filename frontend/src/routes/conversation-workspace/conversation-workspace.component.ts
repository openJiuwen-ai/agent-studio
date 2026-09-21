import {
  Component,
  OnDestroy,
  OnInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  ViewChild,
  ElementRef,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { COMMON_MODULES, LIB_MODULES } from '@shared/modules';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ApplicationType } from '@enums/agent-center.enum';
import { HttpService } from '@services/http.service';
import {
  ConversationExecutionTarget,
  ConversationSendRequest,
  ConversationSkillItem,
  ConversationFileReference,
} from './conversation-skill.model';
import {
  ActiveSessionState,
  ConversationWorkspaceService,
  SessionItem,
  SessionListState,
} from './conversation-workspace.service';
import { SkillSelectorComponent } from './skill-selector/skill-selector.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import { v4 as uuidV4 } from 'uuid';

/** 消息段：message 输出段 / reasoning 思考段 / tool 工具轨迹（按轮持久化的行形态） */
interface ChatSegment {
  type: 'message' | 'reasoning' | 'tool';
  content: string;
  /** 工具名（仅 type=tool） */
  toolId?: string;
  /** 工具调用关联标识（仅 type=tool，用于交错结果精确回填） */
  toolCallId?: string;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  segments: ChatSegment[];
  userContent?: string;
  userFiles?: Array<Pick<ConversationFileReference, 'fileName'>>;
  /** 非主 Agent 内容默认折叠，不主动展示 */
  detailSegments?: ChatSegment[];
  subAgents?: ChatMessage[];
  loading?: boolean;
  error?: boolean;
  subExecutionId?: string;
  agentId?: string;
  isSubAgent?: boolean;
}

interface ActivatedSkill {
  skillId: string;
  name: string;
  versionId: string;
}

interface ConversationAttempt {
  id: number;
  workspaceId: string;
  initialSessionId: string;
  conversationId?: string;
  query: string;
  inputSnapshot: string;
  recommendationSnapshot: ConversationSkillItem[];
  phase: 'creating' | 'running';
  opened: boolean;
  settled: boolean;
  source?: { close?: () => void };
  assistantMsg?: ChatMessage;
}

interface PendingRouteConversation {
  conversationId: string;
  workspaceId: string;
}

interface PendingActiveSession {
  session: SessionItem;
  workspaceId: string;
}

@Component({
  selector: 'app-conversation-workspace',
  templateUrl: './conversation-workspace.component.html',
  styleUrls: ['./conversation-workspace.component.less'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [COMMON_MODULES, LIB_MODULES, SkillSelectorComponent, AppMarkdownAnswerComponent, UploadFileIconComponent],
  standalone: true,
})
export class ConversationWorkspaceComponent implements OnInit, OnDestroy {
  currentSession: SessionItem | null = null;
  messages: ChatMessage[] = [];
  inputText = '';
  streaming = false;
  selectedModel = '';
  modelOptions: any[] = [];
  executionTargets: ConversationExecutionTarget[] = [
    { id: 'default-team', name: '默认团队', type: 'SUPERVISOR' },
  ];
  selectedExecutionTarget = 'default-team';
  selectedExecutionPath: string[] = ['default-team'];
  executionTargetOptions: any[] = [
    { value: 'default-team', label: '默认团队', isLeaf: true },
    { value: 'digital-employees', label: '数字员工', children: [] },
    { value: 'digital-squads', label: '数字小队', children: [] },
  ];
  skillCatalog: ConversationSkillItem[] = [];
  skillCatalogUnavailable = false;
  recommendedSkills: ConversationSkillItem[] = [];
  activatedSkills: ActivatedSkill[] = [];
  uploadedFiles: ConversationFileReference[] = [];
  readonly acceptedFileTypes = '.txt,.md,.json,.xml,.html,.docx,.pdf,.xlsx,.xls,.csv';
  private readonly maxFiles = 10;
  private readonly maxFileSize = 60 * 1024 * 1024;
  @ViewChild('fileInput') private fileInput?: ElementRef<HTMLInputElement>;
  @ViewChild(SkillSelectorComponent) private skillSelector?: SkillSelectorComponent;
  private modelAbortController: AbortController | null = null;
  private subscriptions = new Subscription();
  private workspaceId = '';
  private catalogRequestId = 0;
  private detailRequestId = 0;
  private nextAttemptId = 0;
  private activeAttempt: ConversationAttempt | null = null;
  private destroyed = false;
  private readonly workspaceRouteProvenanceKey = 'conversation-workspace-route-workspace';
  private workspaceRouteProvenance = '';
  private sessionListState: SessionListState = { workspaceId: '', generation: 0, sessions: [] };
  private pendingRouteConversation: PendingRouteConversation | null = null;
  private pendingActiveSession: PendingActiveSession | null = null;
  private readonly workspaceChangeHandler = () => this.handleWorkspaceChange();

  constructor(
    private conversationWorkspaceService: ConversationWorkspaceService,
    private modelManagementService: ModelManagementService,
    private appAgentRepoService: AppAgentRepoService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private http: HttpService,
  ) {}

  ngOnInit(): void {
    this.workspaceId = this.http.getWorkspaceId();
    this.workspaceRouteProvenance = sessionStorage.getItem(this.workspaceRouteProvenanceKey) ?? '';
    this.loadSkillCatalog();
    window.addEventListener('WorkspaceChange', this.workspaceChangeHandler);
    this.loadModels();
    this.loadExecutionTargets();
    this.subscribeToSessionListState();
    this.subscribeToRoute();
    this.subscribeToActiveSession();
  }

  /** Skill 目录失败不影响普通对话。 */
  private loadSkillCatalog(preserveCatalogOnFailure = false): void {
    const requestWorkspaceId = this.workspaceId;
    const requestId = ++this.catalogRequestId;
    this.conversationWorkspaceService
      .listSkills()
      .then((skills) => {
        if (!this.isCurrentCatalogRequest(requestWorkspaceId, requestId)) {
          return;
        }
        this.skillCatalog = skills;
        this.skillCatalogUnavailable = false;
        this.cdr.markForCheck();
      })
      .catch(() => {
        if (!this.isCurrentCatalogRequest(requestWorkspaceId, requestId)) {
          return;
        }
        if (!preserveCatalogOnFailure) {
          this.skillCatalog = [];
        }
        this.skillCatalogUnavailable = true;
        this.cdr.markForCheck();
      });
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.clearPendingRouteConversation();
    this.clearPendingActiveSession();
    this.invalidateCatalogRequests();
    this.invalidateDetailRequests();
    try {
      this.cancelActiveAttempt();
    } finally {
      try {
        this.modelAbortController?.abort();
      } finally {
        try {
          this.subscriptions.unsubscribe();
        } finally {
          window.removeEventListener('WorkspaceChange', this.workspaceChangeHandler);
        }
      }
    }
  }

  /** 模型列表（复用平台 getAvailableModelList） */
  private loadModels(): void {
    this.modelAbortController?.abort();
    this.modelAbortController = new AbortController();
    this.modelManagementService
      .getAvailableModelList(
        {
          groupby: 'provider',
          publish_status: 'online',
          model_type: 'LLM,IMAGE-TO-TEXT',
          with_router: false,
        },
        this.modelAbortController.signal,
      )
      .then((res) => {
        const options: any[] = [];
        res?.data?.forEach((provider: any) => {
          (provider.models ?? []).forEach((model: any) => {
            options.push({
              deployment_id: model.id,
              label: `${provider.provider_name || ''} / ${model.model_name || model.id}`,
            });
          });
        });
        this.modelOptions = options;
        this.selectedModel = options[0]?.deployment_id ?? '';
        this.cdr.markForCheck();
      })
      .catch(() => void 0);
  }

  /** 复用 AgentCenter 现有资源接口，映射工作台执行目标。
   *  该接口 type 为精确匹配（不支持逗号多值），故按单/多智能体各查一次再合并去重。 */
  private loadExecutionTargets(): void {
    Promise.all([
      this.appAgentRepoService.getAgentList(
        { type: ApplicationType.SINGLE_AGENT, status: 'published' },
        0,
        100,
      ),
      this.appAgentRepoService.getAgentList(
        { type: ApplicationType.MULTI_AGENT, status: 'published' },
        0,
        100,
      ),
    ])
      .then(([single, multi]) => {
        const seen = new Set<string>();
        const targets: ConversationExecutionTarget[] = [];
        [single, multi].forEach((res) => {
          (res?.agent_list ?? []).forEach((agent: any) => {
            if (
              ![ApplicationType.SINGLE_AGENT, ApplicationType.MULTI_AGENT].includes(agent.type)
            ) {
              return;
            }
            const id = String(agent.id ?? agent.agent_id);
            const name = agent.name ?? agent.agent_name ?? id;
            if (!id || !name || seen.has(id)) {
              return;
            }
            seen.add(id);
            targets.push({
              id,
              name,
              type: agent.type === ApplicationType.MULTI_AGENT ? 'MULTI_AGENT' : 'SINGLE_AGENT',
            });
          });
        });
        this.executionTargets = [
          { id: 'default-team', name: '默认团队', type: 'SUPERVISOR' },
          ...targets,
        ];
        this.executionTargetOptions = [
          { value: 'default-team', label: '默认团队', isLeaf: true },
          {
            value: 'digital-employees',
            label: '数字员工',
            children: targets
              .filter((target) => target.type === 'SINGLE_AGENT')
              .map((target) => ({ value: target.id, label: target.name, isLeaf: true })),
          },
          {
            value: 'digital-squads',
            label: '数字小队',
            children: targets
              .filter((target) => target.type === 'MULTI_AGENT')
              .map((target) => ({ value: target.id, label: target.name, isLeaf: true })),
          },
        ];
        this.cdr.markForCheck();
      })
      .catch(() => void 0);
  }

  /** 路由 queryParams：conversation_id 打开会话 / new 新建草稿 / 兜底新建草稿 */
  private subscribeToRoute(): void {
    this.subscriptions.add(
      this.route.queryParams.subscribe((params) => {
        if (params['conversation_id']) {
          this.handleConversationRoute(params['conversation_id'], params['workspace_id']);
        } else if (params['new']) {
          this.clearPendingRouteConversation();
          this.conversationWorkspaceService.newDraftSession();
        } else if (!this.conversationWorkspaceService.activeSession$.value) {
          this.clearPendingRouteConversation();
          this.conversationWorkspaceService.newDraftSession();
        }
      }),
    );
  }

  /** 带 workspace 归属的共享会话列表是无 workspace_id 历史路由的唯一证明。 */
  private subscribeToSessionListState(): void {
    this.subscriptions.add(
      this.conversationWorkspaceService.sessionListState$.subscribe((state) => {
        this.sessionListState = state;
        this.resolvePendingRouteConversation();
        this.resolvePendingActiveSession();
      }),
    );
  }

  /** 订阅带 workspace 归属的当前会话：旧空间残留须先由列表证明。 */
  private subscribeToActiveSession(): void {
    this.subscriptions.add(
      this.conversationWorkspaceService.activeSessionState$.subscribe((state) => {
        const workspaceChanged = this.transitionWorkspace(this.http.getWorkspaceId());
        if (!this.isCurrentWorkspaceActiveState(state)) {
          this.queuePendingActiveSession(state.session);
          return;
        }
        this.clearPendingActiveSession();
        this.clearPendingRouteConversation();
        this.applyActiveSession(state.session, workspaceChanged);
      }),
    );
  }

  private applyActiveSession(session: SessionItem | null, workspaceChanged: boolean): void {
    if (this.isDraftPromotion(session)) {
      this.currentSession = session;
      this.cdr.markForCheck();
      return;
    }
    if (!workspaceChanged && this.isSameConversation(session, this.currentSession)) {
      this.currentSession = session;
      this.cdr.markForCheck();
      return;
    }
    this.cancelActiveAttempt();
    this.invalidateDetailRequests();
    this.clearSkillRoundState();
    this.currentSession = session;
    const id = session?.conversation_id;
    if (!id) {
      this.messages = [];
    } else {
      this.messages = [];
      this.loadSessionDetail(id);
    }
    this.cdr.markForCheck();
  }

  /** 打开会话（列表命中直接用；深链则先占位、详情加载后补标题） */
  private openConversation(id: string): void {
    const existing = this.conversationWorkspaceService.sessions$.value.find(
      (s) => s.conversation_id === id,
    );
    this.conversationWorkspaceService.setActiveSession(
      existing ?? { conversation_id: id, title: '', status: 'ACTIVE' },
    );
  }

  /** 发送消息（多轮对话入口；草稿先落库，仅首次真正交互才创建会话） */
  public send(): void {
    const inputSnapshot = this.inputText;
    const query = inputSnapshot.trim();
    const recommendationSnapshot = [...this.recommendedSkills];
    if (!query || this.isSending || !this.selectedModel) {
      return;
    }
    if (!this.currentSession?.conversation_id) {
      this.clearPendingRouteConversation();
      this.clearPendingActiveSession();
    }
    const attempt = this.createAttempt(query, inputSnapshot, recommendationSnapshot);
    if (!this.currentSession?.conversation_id) {
      this.conversationWorkspaceService
        .createSession({ title: this.currentSession?.title ?? '' })
        .then((session) => {
          if (!this.isCurrentAttempt(attempt) || attempt.phase !== 'creating') {
            return;
          }
          attempt.conversationId = session.conversation_id;
          this.currentSession = session;
          this.conversationWorkspaceService.setActiveSession(session);
          this.conversationWorkspaceService.refreshSessions();
          this.startRun(attempt, session.conversation_id);
        })
        .catch(() => {
          if (this.isCurrentAttempt(attempt) && attempt.phase === 'creating') {
            this.releaseAttempt(attempt);
          }
        });
      return;
    }
    attempt.conversationId = this.currentSession.conversation_id;
    this.startRun(attempt, attempt.conversationId);
  }

  /** Enter 发送（Shift+Enter 换行） */
  public onKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Enter' || event.shiftKey) {
      return;
    }
    event.preventDefault();
    this.send();
  }

  public openFilePicker(): void {
    if (this.isSending || this.uploadedFiles.length >= this.maxFiles) {
      return;
    }
    this.fileInput?.nativeElement.click();
  }

  public onFilesSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = '';
    const remaining = this.maxFiles - this.uploadedFiles.length;
    files.slice(0, remaining).forEach((file) => this.uploadFile(file));
  }

  public removeUploadedFile(fileId: string): void {
    this.uploadedFiles = this.uploadedFiles.filter((file) => file.fileId !== fileId);
    this.cdr.markForCheck();
  }

  private uploadFile(file: File): void {
    const extension = file.name.split('.').pop()?.toLowerCase() ?? '';
    const accepted = this.acceptedFileTypes
      .split(',')
      .map((item) => item.replace('.', ''));
    if (!accepted.includes(extension) || file.size > this.maxFileSize) {
      this.uploadedFiles = [
        ...this.uploadedFiles,
        { fileId: uuidV4(), fileName: file.name, url: '', progress: 'failed' },
      ];
      this.cdr.markForCheck();
      return;
    }

    const fileId = uuidV4();
    const item: ConversationFileReference = {
      fileId,
      fileName: file.name,
      url: '',
      progress: 'loading',
    };
    this.uploadedFiles = [...this.uploadedFiles, item];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('is_image', 'false');
    this.appAgentRepoService.uploadFile(formData)
      .then((result) => {
        this.uploadedFiles = this.uploadedFiles.map((current) =>
          current.fileId === fileId
            ? { ...current, url: result?.url ?? '', fileName: result?.file_name ?? current.fileName, progress: result?.url ? 'succeeded' : 'failed' }
            : current,
        );
      })
      .catch(() => {
        this.uploadedFiles = this.uploadedFiles.map((current) =>
          current.fileId === fileId ? { ...current, progress: 'failed' } : current,
        );
      })
      .finally(() => this.cdr.markForCheck());
  }

  public onExecutionPathChange(path: string[]): void {
    this.selectedExecutionPath = path;
    const selectedId = path[path.length - 1];
    const target = this.executionTargets.find((item) => item.id === selectedId);
    if (target) {
      this.selectedExecutionTarget = target.id;
      this.cdr.markForCheck();
    }
  }

  public get hasPendingUploads(): boolean {
    return this.uploadedFiles.some((file) => file.progress === 'loading');
  }

  public get isSending(): boolean {
    return Boolean(this.activeAttempt && !this.activeAttempt.settled);
  }

  private createAttempt(
    query: string,
    inputSnapshot: string,
    recommendationSnapshot: ConversationSkillItem[],
  ): ConversationAttempt {
    const attempt: ConversationAttempt = {
      id: ++this.nextAttemptId,
      workspaceId: this.workspaceId,
      initialSessionId: this.currentSession?.conversation_id ?? '',
      query,
      inputSnapshot,
      recommendationSnapshot,
      phase: this.currentSession?.conversation_id ? 'running' : 'creating',
      opened: false,
      settled: false,
    };
    this.activeAttempt = attempt;
    this.cdr.markForCheck();
    return attempt;
  }

  private startRun(attempt: ConversationAttempt, conversationId: string): void {
    if (!this.isCurrentAttempt(attempt)) {
      return;
    }
    attempt.phase = 'running';
    attempt.conversationId = conversationId;
    this.activatedSkills = [];
    const assistantMsg: ChatMessage = {
      role: 'assistant',
      userContent: attempt.query,
      userFiles: this.uploadedFiles
        .filter((file) => file.progress === 'succeeded' && file.fileName)
        .map(({ fileName }) => ({ fileName })),
      segments: [],
      detailSegments: [],
      subAgents: [],
      loading: true,
    };
    attempt.assistantMsg = assistantMsg;
    this.messages.push(assistantMsg);
    this.streaming = true;
    this.cdr.markForCheck();

    let source: { close?: () => void } | undefined;
    const selectedTarget = this.executionTargets.find(
      (target) => target.id === this.selectedExecutionTarget,
    );
    const request: ConversationSendRequest = {
      query: attempt.query,
      recommended_skill_ids: attempt.recommendationSnapshot.map((item) => item.skillId),
      select_type: selectedTarget?.type === 'SUPERVISOR' ? 'SUPERVISOR' : 'APP',
      ...(selectedTarget?.type === 'SUPERVISOR'
        ? { model_deployment_id: this.selectedModel }
        : { app_id: selectedTarget?.id }),
      ...this.buildFileReferences(),
    };
    try {
      source = this.conversationWorkspaceService.chatSSE(
        conversationId,
        request,
        {
          onOpen: () => {
            if (!this.isCurrentAttempt(attempt)) {
              return;
            }
            attempt.opened = true;
            if (this.inputText === attempt.inputSnapshot && this.sameSkills(this.recommendedSkills, attempt.recommendationSnapshot)) {
              this.inputText = '';
              this.recommendedSkills = [];
              this.uploadedFiles = [];
              this.skillSelector?.clearRecommendations();
            }
            this.cdr.markForCheck();
          },
          onMessage: (token: any) => {
            if (this.isCurrentAttempt(attempt)) {
              this.handleMessage(token, assistantMsg);
            }
          },
          onDone: () => {
            this.settleRun(attempt, 'done');
          },
          onError: () => {
            this.settleRun(attempt, 'failed');
          },
          onTimeout: () => {
            this.settleRun(attempt, 'failed');
          },
          onAbort: () => {
            this.settleRun(attempt, 'failed');
          },
        },
      );
    } catch {
      this.settleRun(attempt, 'failed');
      return;
    }
    if (!this.isCurrentAttempt(attempt)) {
      this.safeClose(source);
      return;
    }
    attempt.source = source;
  }

  /** 只发送上传成功且包含服务端引用的当前轮附件。 */
  private buildFileReferences(): Pick<ConversationSendRequest, 'file_ids'> {
    const file_ids = this.uploadedFiles
      .filter((file) => file.progress === 'succeeded' && file.url && file.fileName)
      .map(({ url, fileName }) => ({ url, fileName }));
    return file_ids.length ? { file_ids } : {};
  }

  private settleRun(attempt: ConversationAttempt, outcome: 'done' | 'failed'): void {
    if (!this.isCurrentAttempt(attempt)) {
      return;
    }
    attempt.settled = true;
    try {
      this.safeClose(attempt.source);
    } finally {
      if (attempt.assistantMsg) {
        attempt.assistantMsg.loading = false;
        attempt.assistantMsg.error = outcome === 'failed';
      }
      this.activeAttempt = null;
      this.streaming = false;
      if (outcome === 'done') {
        this.conversationWorkspaceService.refreshSessions();
      } else if (!attempt.opened) {
        this.loadSkillCatalog(true);
      }
      this.cdr.markForCheck();
    }
  }

  /**
   * 流式消息处理（按轮持久化协议）：
   * message/reasoning 增量按 subExecutionId 路由主/子气泡并追加到对应段；
   * sub_start 新建子 Agent 气泡；tool_call 建工具段、tool_result 回填结果；
   * sub_done/run_done 仅收尾（结束 loading，不替换内容——入库即流式聚合，"所见即所存"）；
   * error 标记失败；user_message/usage 忽略。
   */
  private handleMessage(token: any, assistantMsg: ChatMessage): void {
    try {
      const { event, data } = JSON.parse(token.data);
      const d = data ?? {};
      switch (event) {
        case 'message': {
          const delta = d.delta ?? '';
          const target = d.subExecutionId
            ? (this.findSubBubble(d.subExecutionId) ?? assistantMsg)
            : assistantMsg;
          if (target && delta) {
            this.appendVisibleOrDetailSegment(target, 'message', delta);
            target.loading = false;
          }
          break;
        }
        case 'reasoning': {
          const content = d.content ?? '';
          const target = d.subExecutionId
            ? (this.findSubBubble(d.subExecutionId) ?? assistantMsg)
            : assistantMsg;
          if (target && content) {
            this.appendExecutionDetailSegment(target, 'reasoning', content);
          }
          break;
        }
        case 'sub_start': {
          // 子 Agent 内容挂在当前主 Agent 交互框内，默认折叠
          const sub: ChatMessage = {
            role: 'assistant',
            segments: [],
            detailSegments: [],
            loading: true,
            subExecutionId: d.subExecutionId,
            agentId: d.agentId,
            isSubAgent: true,
          };
          assistantMsg.subAgents ??= [];
          assistantMsg.subAgents.push(sub);
          break;
        }
        case 'sub_done': {
          const sub = this.findSubBubble(d.subExecutionId);
          if (sub) {
            sub.loading = false; // 完成信号，不替换内容（入库即流式聚合）
          }
          break;
        }
        case 'run_done': {
          assistantMsg.loading = false;
          break;
        }
        case 'tool_call': {
          // 工具轨迹默认折叠，不主动暴露
          const target = d.subExecutionId
            ? (this.findSubBubble(d.subExecutionId) ?? assistantMsg)
            : assistantMsg;
          if (target && d.toolName) {
            const toolSegment: ChatSegment = { type: 'tool', content: '', toolId: d.toolName };
            const toolCallId = d.toolCallId ?? d.tool_call_id;
            if (toolCallId) {
              toolSegment.toolCallId = toolCallId;
            }
            this.executionDetailSegments(target).push(toolSegment);
          }
          break;
        }
        case 'tool_result': {
          const target = d.subExecutionId
            ? (this.findSubBubble(d.subExecutionId) ?? assistantMsg)
            : assistantMsg;
          if (target) {
            const segments = this.executionDetailSegments(target);
            const toolCallId = d.toolCallId ?? d.tool_call_id;
            const toolSeg = toolCallId
              ? [...segments].reverse().find((segment) =>
                  segment.type === 'tool'
                  && segment.toolCallId === toolCallId
                  && !segment.content)
              : this.findLegacyToolResultTarget(segments, d.toolName);
            if (toolSeg) {
              toolSeg.content = d.result ?? '';
            }
          }
          break;
        }
        case 'error': {
          assistantMsg.error = true;
          assistantMsg.loading = false;
          break;
        }
        case 'skill_activated': {
          if (!this.activatedSkills.some((item) => item.skillId === d.skillId && item.versionId === d.versionId)) {
            this.activatedSkills.push({ skillId: d.skillId, name: d.name, versionId: d.versionId });
          }
          break;
        }
        default:
          // user_message/run_start/usage 仅透传不渲染
          break;
      }
    } catch (e) {
      // 非 JSON 数据（如 [DONE]），忽略
    }
    this.cdr.markForCheck();
  }

  /** 追加主 Agent 可见输出；reasoning/tool 进入默认折叠详情。 */
  private appendVisibleOrDetailSegment(message: ChatMessage, type: 'message', delta: string): void {
    this.appendSegment(message, type, delta);
  }

  private appendSegment(message: ChatMessage, type: 'message' | 'reasoning', delta: string): void {
    const last = message.segments[message.segments.length - 1];
    if (last && last.type === type) {
      last.content += delta;
    } else {
      message.segments.push({ type, content: delta });
    }
  }

  private appendExecutionDetailSegment(message: ChatMessage, type: 'reasoning', content: string): void {
    const segments = this.executionDetailSegments(message);
    const last = segments[segments.length - 1];
    if (last && last.type === type) {
      last.content += content;
    } else {
      segments.push({ type, content });
    }
  }

  /** 子 Agent 整体已位于折叠详情内；主 Agent 的执行段则进入自身折叠集合。 */
  private executionDetailSegments(message: ChatMessage): ChatSegment[] {
    if (message.isSubAgent) {
      return message.segments;
    }
    message.detailSegments ??= [];
    return message.detailSegments;
  }

  /** 兼容缺少调用 ID 的旧事件：只能回填唯一未完成候选，避免猜测导致串写。 */
  private findLegacyToolResultTarget(segments: ChatSegment[], toolName?: string): ChatSegment | undefined {
    const candidates = segments.filter((segment) =>
      segment.type === 'tool'
      && !segment.toolCallId
      && !segment.content
      && (!toolName || segment.toolId === toolName));
    return candidates.length === 1 ? candidates[0] : undefined;
  }

  /** 按 execution_id 恢复：每次用户交互生成一个独立框。 */
  private mapDetailToMessages(rows: any[]): ChatMessage[] {
    const turns = new Map<string, ChatMessage>();
    for (const row of rows ?? []) {
      const executionId = row.execution_id ?? `legacy-${row.created_at ?? Math.random()}`;
      let turn = turns.get(executionId);
      if (!turn) {
        turn = { role: 'assistant', segments: [], detailSegments: [], subAgents: [] };
        turns.set(executionId, turn);
      }
      if (row.role === 'user') {
        turn.userContent = row.content ?? '';
        turn.userFiles = this.parseUserFiles(row.file_ids ?? row.fileIds);
        continue;
      }
      const seg = this.rowToSegment(row);
      if (!seg) {
        continue;
      }
      if (row.sub_execution_id) {
        let sub = turn.subAgents!.find((item) => item.subExecutionId === row.sub_execution_id);
        if (!sub) {
          sub = {
            role: 'assistant',
            segments: [],
            detailSegments: [],
            subExecutionId: row.sub_execution_id,
            agentId: row.agent_id,
            isSubAgent: true,
          };
          turn.subAgents!.push(sub);
        }
        sub.segments.push(seg);
      } else if (seg.type === 'message') {
        turn.segments.push(seg);
      } else {
        turn.detailSegments!.push(seg);
      }
    }
    return Array.from(turns.values());
  }

  private parseUserFiles(value: unknown): Array<Pick<ConversationFileReference, 'fileName'>> {
    if (!value) {
      return [];
    }
    try {
      const parsed = typeof value === 'string' ? JSON.parse(value) : value;
      if (!Array.isArray(parsed)) {
        return [];
      }
      return parsed
        .map((item) => {
          if (typeof item === 'string') {
            return { fileName: item };
          }
          return { fileName: item?.fileName ?? item?.file_name ?? '' };
        })
        .filter((item) => Boolean(item.fileName));
    } catch {
      return [];
    }
  }

  /** run 表 handoff 工具进入详情；主界面只展示 message。 */
  private rowToSegment(row: any): ChatSegment | null {
    if (row.role === 'tool') {
      const segment: ChatSegment = { type: 'tool', content: row.content ?? '', toolId: row.tool_id };
      const toolCallId = row.tool_call_id ?? row.toolCallId;
      if (toolCallId) {
        segment.toolCallId = toolCallId;
      }
      return segment;
    }
    if (row.event === 'reasoning') {
      return { type: 'reasoning', content: row.content ?? '' };
    }
    if (row.event === 'message') {
      return { type: 'message', content: row.content ?? '' };
    }
    return null;
  }

  private findSubBubble(subExecutionId: string): ChatMessage | undefined {
    for (const message of this.messages) {
      const sub = message.subAgents?.find((item) => item.subExecutionId === subExecutionId);
      if (sub) {
        return sub;
      }
    }
    return undefined;
  }

  private clearSkillRoundState(): void {
    this.recommendedSkills = [];
    this.activatedSkills = [];
    this.skillSelector?.clearRecommendations();
  }

  private handleWorkspaceChange(): void {
    const nextWorkspaceId = this.http.getWorkspaceId();
    if (!this.transitionWorkspace(nextWorkspaceId, true)) {
      return;
    }
    this.workspaceRouteProvenance = nextWorkspaceId;
    sessionStorage.setItem(this.workspaceRouteProvenanceKey, nextWorkspaceId);
    this.conversationWorkspaceService.clearSessions(nextWorkspaceId);
    this.router.navigate(['/home/conversation'], {
      queryParams: { new: Date.now(), workspace_id: nextWorkspaceId },
      replaceUrl: true,
    }).then(
      (navigated) => {
        if (!navigated) {
          this.markForCheckIfAlive();
        }
      },
      () => this.markForCheckIfAlive(),
    );
  }

  private transitionWorkspace(nextWorkspaceId: string, invalidateActiveSession = false): boolean {
    if (nextWorkspaceId === this.workspaceId) {
      return false;
    }
    this.clearPendingRouteConversation();
    this.clearPendingActiveSession();
    this.cancelActiveAttempt();
    this.invalidateDetailRequests();
    this.workspaceId = nextWorkspaceId;
    this.currentSession = null;
    this.skillCatalog = [];
    this.messages = [];
    this.clearSkillRoundState();
    this.loadSkillCatalog();
    if (invalidateActiveSession) {
      this.conversationWorkspaceService.setActiveSession(null);
    }
    this.cdr.markForCheck();
    return true;
  }

  private isCurrentCatalogRequest(workspaceId: string, requestId: number): boolean {
    return !this.destroyed && workspaceId === this.workspaceId && requestId === this.catalogRequestId;
  }

  private isDraftPromotion(session: SessionItem | null): boolean {
    const attempt = this.activeAttempt;
    return Boolean(
      attempt &&
      !attempt.settled &&
      attempt.phase === 'creating' &&
      attempt.conversationId &&
      session?.conversation_id === attempt.conversationId &&
      attempt.workspaceId === this.workspaceId,
    );
  }

  private isSameConversation(next: SessionItem | null, current: SessionItem | null): boolean {
    return Boolean(next?.conversation_id && next.conversation_id === current?.conversation_id);
  }

  private handleConversationRoute(conversationId: string, routeWorkspaceId: unknown): void {
    const routeWorkspace = typeof routeWorkspaceId === 'string' ? routeWorkspaceId : '';
    this.clearPendingRouteConversation();
    this.clearPendingActiveSession();
    if (routeWorkspace) {
      if (routeWorkspace === this.workspaceId) {
        this.openConversation(conversationId);
      }
      return;
    }

    // 没有任何历史归属时，保留旧版首次深链的兼容入口；其余情况必须经当前空间列表验证。
    if (!this.workspaceRouteProvenance) {
      this.openConversation(conversationId);
      return;
    }

    this.pendingRouteConversation = {
      conversationId,
      workspaceId: this.workspaceId,
    };
    this.resolvePendingRouteConversation();
  }

  private resolvePendingRouteConversation(): void {
    const pending = this.pendingRouteConversation;
    if (!pending || this.destroyed || pending.workspaceId !== this.workspaceId ||
      this.sessionListState.workspaceId !== pending.workspaceId) {
      return;
    }
    const belongsToCurrentWorkspace = this.sessionListState.sessions.some(
      (session) => session.conversation_id === pending.conversationId,
    );
    if (!belongsToCurrentWorkspace) {
      return;
    }
    this.pendingRouteConversation = null;
    this.openConversation(pending.conversationId);
  }

  private clearPendingRouteConversation(): void {
    this.pendingRouteConversation = null;
  }

  private isCurrentWorkspaceActiveState(state: ActiveSessionState): boolean {
    return state.workspaceId === this.workspaceId;
  }

  private queuePendingActiveSession(session: SessionItem | null): void {
    if (session?.conversation_id) {
      this.pendingActiveSession = { session, workspaceId: this.workspaceId };
    }
  }

  private resolvePendingActiveSession(): void {
    const pending = this.pendingActiveSession;
    if (!pending || this.destroyed || pending.workspaceId !== this.workspaceId ||
      this.sessionListState.workspaceId !== pending.workspaceId ||
      !this.sessionListState.sessions.some((session) => session.conversation_id === pending.session.conversation_id)) {
      return;
    }
    this.pendingActiveSession = null;
    this.conversationWorkspaceService.setActiveSession(pending.session);
  }

  private clearPendingActiveSession(): void {
    this.pendingActiveSession = null;
  }

  private markForCheckIfAlive(): void {
    if (!this.destroyed) {
      this.cdr.markForCheck();
    }
  }

  private loadSessionDetail(conversationId: string): void {
    const requestWorkspaceId = this.workspaceId;
    const requestId = ++this.detailRequestId;
    this.conversationWorkspaceService
      .detailSession(conversationId)
      .then((detail) => {
        if (!this.isCurrentDetailRequest(requestWorkspaceId, conversationId, requestId)) {
          return;
        }
        this.messages = this.mapDetailToMessages(detail?.messages ?? []);
        if (!this.currentSession?.title) {
          this.currentSession = { ...this.currentSession!, title: detail?.title ?? '' };
        }
        this.cdr.markForCheck();
      })
      .catch(() => void 0);
  }

  private invalidateDetailRequests(): void {
    this.detailRequestId += 1;
  }

  private invalidateCatalogRequests(): void {
    this.catalogRequestId += 1;
  }

  private isCurrentDetailRequest(workspaceId: string, conversationId: string, requestId: number): boolean {
    return !this.destroyed &&
      workspaceId === this.workspaceId &&
      requestId === this.detailRequestId &&
      this.currentSession?.conversation_id === conversationId;
  }

  private isCurrentAttempt(attempt: ConversationAttempt): boolean {
    if (this.activeAttempt !== attempt || attempt.settled || attempt.workspaceId !== this.workspaceId) {
      return false;
    }
    const expectedSessionId = attempt.conversationId ?? attempt.initialSessionId;
    return (this.currentSession?.conversation_id ?? '') === expectedSessionId;
  }

  private cancelActiveAttempt(): void {
    const attempt = this.activeAttempt;
    if (!attempt || attempt.settled) {
      return;
    }
    attempt.settled = true;
    try {
      this.safeClose(attempt.source);
    } finally {
      if (attempt.assistantMsg) {
        attempt.assistantMsg.loading = false;
      }
      this.activeAttempt = null;
      this.streaming = false;
    }
  }

  private safeClose(source?: { close?: () => void }): void {
    try {
      source?.close?.();
    } catch {
      // 关闭失败不应阻断本地运行态和订阅的收口。
    }
  }

  private releaseAttempt(attempt: ConversationAttempt): void {
    attempt.settled = true;
    if (this.activeAttempt === attempt) {
      this.activeAttempt = null;
      this.streaming = false;
    }
    this.cdr.markForCheck();
  }

  private sameSkills(left: ConversationSkillItem[], right: ConversationSkillItem[]): boolean {
    return left.length === right.length && left.every((item, index) => item.skillId === right[index].skillId);
  }

  /** 气泡角色标签：我 / 助手 / 子Agent·{agentId前8位} */
  public roleLabel(message: ChatMessage): string {
    if (message.role === 'user') {
      return '我';
    }
    if (message.isSubAgent) {
      return `子Agent${message.agentId ? '·' + message.agentId.slice(0, 8) : ''}`;
    }
    return '助手';
  }
}
