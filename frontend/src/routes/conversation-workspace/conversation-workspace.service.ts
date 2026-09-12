import { Injectable } from '@angular/core';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { SSE } from '@shared/services/sse';
import { BehaviorSubject } from 'rxjs';
import dayjs from 'dayjs';
import { ConversationSendRequest, ConversationSkillItem, ConversationSseCallbacks } from './conversation-skill.model';

export interface SessionItem {
  conversation_id: string;
  title: string;
  status: string;
  updated_at?: string;
  created_at?: string;
}

export interface SessionListState {
  workspaceId: string;
  generation: number;
  sessions: SessionItem[];
}

export interface ActiveSessionState {
  workspaceId: string;
  generation: number;
  session: SessionItem | null;
}

/**
 * 对话工作台服务：会话 CRUD API + 发送消息 SSE 薄封装 + 会话列表/当前会话状态
 * （SSE 事件注册模式与平台 webPageChatSSE 一致，URL 指向对话工作台新端点，不改共享 service）
 */
@Injectable({
  providedIn: 'root',
})
export class ConversationWorkspaceService {
  /** 会话列表（左菜单 + 工作台共享） */
  public sessions$ = new BehaviorSubject<SessionItem[]>([]);
  /** 带工作空间归属的会话列表快照，供路由归属校验使用。 */
  public sessionListState$ = new BehaviorSubject<SessionListState>({
    workspaceId: '',
    generation: 0,
    sessions: [],
  });
  /** 当前打开的会话（可为无 id 的本地草稿） */
  public activeSession$ = new BehaviorSubject<SessionItem | null>(null);
  /** 带工作空间归属的当前会话状态，避免根级残留会话跨空间重放。 */
  public activeSessionState$ = new BehaviorSubject<ActiveSessionState>({
    workspaceId: '',
    generation: 0,
    session: null,
  });
  private sessionListGeneration = 0;
  private sessionListRequestId = 0;
  private activeSessionGeneration = 0;

  constructor(
    private http: HttpService,
    private ctxServ: ContextService,
    private configServ: AgentConfigService,
  ) {}

  /** 刷新会话列表并广播 */
  public refreshSessions(): Promise<void> {
    const requestWorkspaceId = this.http.getWorkspaceId();
    const requestId = ++this.sessionListRequestId;
    return this.listSessions(0, 100, requestWorkspaceId).then((res) => {
      if (!this.isCurrentSessionListRequest(requestWorkspaceId, requestId)) {
        return;
      }
      this.publishSessionList(requestWorkspaceId, res?.items ?? []);
    });
  }

  /** 工作空间切换时清空共享列表，并使旧刷新请求失效。 */
  public clearSessions(workspaceId = this.http.getWorkspaceId()): void {
    this.sessionListRequestId += 1;
    this.publishSessionList(workspaceId, []);
  }

  /** 新建本地草稿会话（标题=当前时间到分钟，未落库） */
  public newDraftSession(): void {
    const title = dayjs().format('YYYY-MM-DD HH:mm');
    this.setActiveSession({ conversation_id: '', title, status: 'ACTIVE' });
  }

  /** 设置当前打开的会话 */
  public setActiveSession(session: SessionItem | null): void {
    this.activeSession$.next(session);
    this.activeSessionState$.next({
      workspaceId: this.http.getWorkspaceId(),
      generation: ++this.activeSessionGeneration,
      session,
    });
  }

  private get sessionsUrl(): string {
    // 相对路径：HttpService.mergeConfig 会自动前置 prefixPath，传绝对路径会双重前缀导致 URL 非法
    return `${this.ctxServ.baseUrl}/conversation/sessions`;
  }

  /** 创建会话 */
  public createSession(params: any = {}): Promise<any> {
    return this.http.postAsync({
      url: this.sessionsUrl,
      params,
      query: { workspace_id: this.http.getWorkspaceId() },
    });
  }

  /** 会话列表（updated_on 倒序，分页） */
  public listSessions(page = 0, size = 100, workspaceId = this.http.getWorkspaceId()): Promise<any> {
    return this.http.getAsync({
      url: this.sessionsUrl,
      query: {
        workspace_id: workspaceId,
        page,
        size,
      },
    });
  }

  private isCurrentSessionListRequest(workspaceId: string, requestId: number): boolean {
    return workspaceId === this.http.getWorkspaceId() && requestId === this.sessionListRequestId;
  }

  private publishSessionList(workspaceId: string, sessions: SessionItem[]): void {
    const state: SessionListState = {
      workspaceId,
      generation: ++this.sessionListGeneration,
      sessions,
    };
    this.sessions$.next(sessions);
    this.sessionListState$.next(state);
  }

  /** 工作空间内可供对话推荐的最小 Skill 目录。 */
  public listSkills(): Promise<ConversationSkillItem[]> {
    return this.http
      .getAsync<any[]>({
        url: `${this.sessionsUrl}/skills`,
        query: { workspace_id: this.http.getWorkspaceId() },
      })
      .then((items) =>
        (items ?? []).map((item) => ({
          skillId: item.skill_id,
          name: item.name,
          description: item.description,
        })),
      );
  }

  /** 会话详情（含全部消息） */
  public detailSession(conversationId: string): Promise<any> {
    return this.http.getAsync({
      url: `${this.sessionsUrl}/${conversationId}`,
      query: { workspace_id: this.http.getWorkspaceId() },
    });
  }

  /** 删除会话（软删除） */
  public deleteSession(conversationId: string): Promise<any> {
    return this.http.deleteAsync({
      url: `${this.sessionsUrl}/${conversationId}`,
      query: { workspace_id: this.http.getWorkspaceId() },
    });
  }

  /**
   * 发送消息（多轮对话入口，SSE 流式返回）
   * 薄封装复用 webPageChatSSE 的完整事件注册模式
   */
  public chatSSE(
    conversationId: string,
    params: ConversationSendRequest,
    callbacks: ConversationSseCallbacks = {},
  ): any {
    const {
      onStatus,
      onOpen,
      onMessage,
      onModeration,
      onTimeout,
      onDone,
      onError,
      onAbort,
      onReadyStateChange,
    } = callbacks;
    const nilFunc = () => void 0;
    const url = `${this.http.prefixPath}/v1/${this.ctxServ.projectId}/conversation/sessions/${conversationId}/messages?workspace_id=${this.http.getWorkspaceId()}`;

    const { stream_first_chunk_timeout, stream_interval_timeout } =
      this.configServ.getConfigs();

    const source = new SSE(url, {
      headers: {
        'Content-Type': 'application/json',
        stream: 'true',
        'X-Language': 'zh-cn',
        'X-Invoke-Mode': 'PUBLISHED',
        projectname: JSON.parse(sessionStorage.getItem('cfCurrentRegion')),
        region: JSON.parse(sessionStorage?.getItem('cfCurrentRegion')),
      },
      payload: JSON.stringify({ ...params }),
      method: 'POST',
      withCsrf: true,
      timeout: 3600000,
      streamFirstChunkTimeout: stream_first_chunk_timeout ?? 180000,
      streamTimeout: stream_interval_timeout ?? 180000,
    });
    source.addEventListener('status', onStatus ?? nilFunc);
    source.addEventListener('open', onOpen ?? nilFunc);
    source.addEventListener('message', (onMessage as unknown as EventListener) ?? nilFunc);
    source.addEventListener('error', onError ?? nilFunc);
    source.addEventListener('abort', onAbort ?? nilFunc);
    source.addEventListener('readystatechange', onReadyStateChange ?? nilFunc);
    source.addEventListener('moderation', onModeration ?? nilFunc);
    source.addEventListener('timeout', onTimeout ?? nilFunc);
    source.addEventListener('done', onDone ?? nilFunc);

    source.stream();

    return source;
  }
}
