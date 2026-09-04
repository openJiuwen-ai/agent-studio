import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { provideNzIcons } from 'ng-zorro-antd/icon';
import { AudioOutline, NumberOutline, SendOutline, UploadOutline } from '@ant-design/icons-angular/icons';
import { BehaviorSubject } from 'rxjs';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { HttpService } from '@services/http.service';
import { ConversationSkillItem } from './conversation-skill.model';
import { ConversationWorkspaceComponent } from './conversation-workspace.component';
import { ConversationWorkspaceService, SessionItem } from './conversation-workspace.service';
import { SSE } from '@shared/services/sse';

describe('ConversationWorkspaceComponent', () => {
  let fixture: ComponentFixture<ConversationWorkspaceComponent>;
  let component: ConversationWorkspaceComponent;
  let service: any;
  let http: { workspaceId: string; getWorkspaceId: () => string };
  let router: any;
  let routeParams: BehaviorSubject<any>;

  beforeEach(async () => {
    sessionStorage.removeItem('conversation-workspace-route-workspace');
    http = { workspaceId: 'workspace-1', getWorkspaceId: () => http.workspaceId };
    const activeSession$ = new BehaviorSubject<SessionItem | null>(null);
    const activeSessionState$ = new BehaviorSubject({ workspaceId: '', generation: 0, session: null as SessionItem | null });
    const nextActiveSession = activeSession$.next.bind(activeSession$);
    let activeSessionGeneration = 0;
    (activeSession$ as any).next = (item: SessionItem | null) => {
      nextActiveSession(item);
      activeSessionState$.next({ workspaceId: http.workspaceId, generation: ++activeSessionGeneration, session: item });
    };
    service = {
      sessions$: new BehaviorSubject<SessionItem[]>([]),
      sessionListState$: new BehaviorSubject({ workspaceId: 'workspace-1', generation: 0, sessions: [] }),
      activeSession$,
      activeSessionState$,
      createSession: jasmine.createSpy('createSession').and.resolveTo(session('new-session')),
      detailSession: jasmine.createSpy('detailSession').and.resolveTo({ messages: [] }),
      refreshSessions: jasmine.createSpy('refreshSessions').and.resolveTo(),
      clearSessions: jasmine.createSpy('clearSessions').and.callFake((workspaceId: string) => publishSessionList(service, workspaceId, [])),
      setActiveSession: jasmine.createSpy('setActiveSession').and.callFake((item: SessionItem | null) => service.activeSession$.next(item)),
      newDraftSession: jasmine.createSpy('newDraftSession'),
      listSkills: jasmine.createSpy('listSkills').and.resolveTo([skill('s1')]),
      chatSSE: jasmine.createSpy('chatSSE').and.returnValue({ close: jasmine.createSpy('close') }),
    };
    routeParams = new BehaviorSubject({});
    router = { navigate: jasmine.createSpy('navigate').and.resolveTo(true) };

    await TestBed.configureTestingModule({
      imports: [ConversationWorkspaceComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideNzIcons([AudioOutline, NumberOutline, SendOutline, UploadOutline]),
        { provide: ConversationWorkspaceService, useValue: service },
        {
          provide: ModelManagementService,
          useValue: { getAvailableModelList: jasmine.createSpy('getAvailableModelList').and.returnValue(new Promise(() => void 0)) },
        },
        {
          provide: AppAgentRepoService,
          useValue: { getAgentList: jasmine.createSpy('getAgentList').and.resolveTo({ agent_list: [] }) },
        },
        { provide: HttpService, useValue: http },
        { provide: ActivatedRoute, useValue: { queryParams: routeParams } },
        { provide: Router, useValue: router },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.selectedModel = 'model-1';
  });

  it('初始化独立加载工作空间 Skill，并把选择器保留在工具栏同级', async () => {
    await Promise.resolve();
    fixture.detectChanges();

    expect(service.listSkills).toHaveBeenCalled();
    expect(fixture.nativeElement.querySelector('app-skill-selector')).not.toBeNull();
    expect(fixture.nativeElement.querySelector('.chat-composer > .composer-toolbar')).not.toBeNull();
  });

  it('发送时只提交有序推荐 ID，并且只在 SSE open 后清空输入和选择', () => {
    (component as any).recommendedSkills = [skill('s2'), skill('s1')];
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();

    expect(service.chatSSE).toHaveBeenCalledWith('c1', jasmine.objectContaining({
      query: '整理会议',
      model_deployment_id: 'model-1',
      recommended_skill_ids: ['s2', 's1'],
    }), jasmine.any(Object));
    expect(component.inputText).toBe('整理会议');
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onOpen();
    expect(component.inputText).toBe('');
    expect((component as any).recommendedSkills).toEqual([]);
  });

  it('发送时携带本轮上传成功文件的 URL 和文件名', () => {
    component.currentSession = session('c1');
    component.inputText = '总结附件';
    (component as any).uploadedFiles = [
      { url: 'https://files.test/report.pdf', fileName: 'report.pdf', progress: 'succeeded' },
      { url: '', fileName: 'failed.txt', progress: 'failed' },
    ];

    component.send();

    expect(service.chatSSE).toHaveBeenCalledWith('c1', jasmine.objectContaining({
      file_ids: [{ url: 'https://files.test/report.pdf', fileName: 'report.pdf' }],
    }), jasmine.any(Object));
  });

  it('连接前失败保留输入和推荐以便重试，并刷新目录', () => {
    (component as any).recommendedSkills = [skill('s1')];
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onError();

    expect(component.inputText).toBe('整理会议');
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect(service.listSkills.calls.count()).toBeGreaterThan(1);
  });

  it('连接前 timeout 与错误相同地保留草稿并刷新目录', () => {
    (component as any).recommendedSkills = [skill('s1')];
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();
    service.chatSSE.calls.mostRecent().args[2].onTimeout();

    expect(component.inputText).toBe('整理会议');
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect(service.listSkills.calls.count()).toBeGreaterThan(1);
  });

  it('流已经打开后的失败不恢复已清除的草稿', () => {
    (component as any).recommendedSkills = [skill('s1')];
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onOpen();
    callbacks.onError();

    expect(component.inputText).toBe('');
    expect((component as any).recommendedSkills).toEqual([]);
    expect(service.listSkills.calls.count()).toBe(1);
  });

  it('SSE open 会通过子组件公开命令清除已渲染的推荐 chips', async () => {
    await Promise.resolve();
    fixture.detectChanges();
    const selector = (component as any).skillSelector;
    selector.onValueInput('/name-s1');
    selector.selectSkill(skill('s1'));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelectorAll('.skill-chip').length).toBe(1);

    component.currentSession = session('c1');
    component.inputText = '整理会议';
    component.send();
    service.chatSSE.calls.mostRecent().args[2].onOpen();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelectorAll('.skill-chip').length).toBe(0);
  });

  it('草稿创建异步完成后仍发送调用时的推荐快照', async () => {
    (component as any).recommendedSkills = [skill('s1')];
    component.currentSession = { conversation_id: '', title: '草稿', status: 'ACTIVE' };
    component.inputText = '整理会议';

    component.send();
    (component as any).recommendedSkills = [skill('s2')];
    await Promise.resolve();

    expect(service.createSession).toHaveBeenCalledWith({ title: '草稿' });
    expect(service.chatSSE).toHaveBeenCalledWith('new-session', jasmine.objectContaining({
      recommended_skill_ids: ['s1'],
    }), jasmine.any(Object));
    expect(service.setActiveSession).toHaveBeenCalledWith(session('new-session'));
    expect(service.refreshSessions).toHaveBeenCalled();
  });

  it('接收技能激活事件后只在当前页面显示按版本去重的标签', () => {
    const assistant = { role: 'assistant' as const, content: '', loading: true };

    dispatchSse(component, assistant, { event: 'skill_activated', data: { skillId: 's1', name: '会议纪要', versionId: 'v1' } });
    dispatchSse(component, assistant, { event: 'skill_activated', data: { skillId: 's1', name: '会议纪要', versionId: 'v1' } });
    dispatchSse(component, assistant, { event: 'skill_activated', data: { skillId: 's1', name: '会议纪要 v2', versionId: 'v2' } });

    expect((component as any).activatedSkills).toEqual([
      { skillId: 's1', name: '会议纪要', versionId: 'v1' },
      { skillId: 's1', name: '会议纪要 v2', versionId: 'v2' },
    ]);
  });

  it('流式轮次同时保留主输出、思考、工具、子 Agent 详情与 Skill 激活状态', () => {
    component.currentSession = session('c1');
    component.inputText = '执行任务';
    component.send();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];

    callbacks.onMessage({ data: JSON.stringify({ event: 'message', data: { delta: '主结果' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'reasoning', data: { content: '主思考' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'tool_call', data: { toolCallId: 'main-call', toolName: 'search' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'tool_result', data: { toolCallId: 'main-call', result: '工具结果' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'sub_start', data: { subExecutionId: 'sub-1', agentId: 'agent-1' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'message', data: { delta: '子结果', subExecutionId: 'sub-1' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'reasoning', data: { content: '子思考', subExecutionId: 'sub-1' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'tool_call', data: { toolCallId: 'sub-call', toolName: 'document', subExecutionId: 'sub-1' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'tool_result', data: { toolCallId: 'sub-call', result: '子工具结果', subExecutionId: 'sub-1' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'skill_activated', data: { skillId: 's1', name: '会议纪要', versionId: 'v1' } }) });

    expect(component.messages).toEqual([
      jasmine.objectContaining({
        userContent: '执行任务',
        segments: [{ type: 'message', content: '主结果' }],
        detailSegments: [
          { type: 'reasoning', content: '主思考' },
          { type: 'tool', content: '工具结果', toolId: 'search', toolCallId: 'main-call' },
        ],
        subAgents: [jasmine.objectContaining({
          subExecutionId: 'sub-1',
          agentId: 'agent-1',
          segments: [
            { type: 'message', content: '子结果' },
            { type: 'reasoning', content: '子思考' },
            { type: 'tool', content: '子工具结果', toolId: 'document', toolCallId: 'sub-call' },
          ],
          detailSegments: [],
        })],
      }),
    ]);
    expect((component as any).activatedSkills).toEqual([
      { skillId: 's1', name: '会议纪要', versionId: 'v1' },
    ]);
    fixture.detectChanges();
    const subAgentDetail = fixture.nativeElement.querySelector('.sub-agent-detail');
    expect(subAgentDetail.textContent).toContain('子结果');
    expect(subAgentDetail.textContent).toContain('子思考');
    expect(subAgentDetail.textContent).toContain('子工具结果');
  });

  it('主与子 Agent 的交错工具结果按 toolCallId 精确回填且互不串写', () => {
    const assistant: any = { role: 'assistant', segments: [], detailSegments: [], subAgents: [] };
    component.messages = [assistant];
    dispatchSse(component, assistant, { event: 'sub_start', data: { subExecutionId: 'sub-1', agentId: 'agent-1' } });

    dispatchSse(component, assistant, { event: 'tool_call', data: { toolCallId: 'main-a', toolName: 'mainA' } });
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolCallId: 'main-b', toolName: 'mainB' } });
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolCallId: 'sub-a', toolName: 'subA', subExecutionId: 'sub-1' } });
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolCallId: 'sub-b', toolName: 'subB', subExecutionId: 'sub-1' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolCallId: 'main-a', result: 'main-result-a' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolCallId: 'sub-a', result: 'sub-result-a', subExecutionId: 'sub-1' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolCallId: 'main-b', result: 'main-result-b' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolCallId: 'sub-b', result: 'sub-result-b', subExecutionId: 'sub-1' } });

    expect(assistant.detailSegments).toEqual([
      { type: 'tool', content: 'main-result-a', toolId: 'mainA', toolCallId: 'main-a' },
      { type: 'tool', content: 'main-result-b', toolId: 'mainB', toolCallId: 'main-b' },
    ]);
    expect(assistant.subAgents[0].segments).toEqual([
      { type: 'tool', content: 'sub-result-a', toolId: 'subA', toolCallId: 'sub-a' },
      { type: 'tool', content: 'sub-result-b', toolId: 'subB', toolCallId: 'sub-b' },
    ]);
  });

  it('旧协议工具结果缺少调用 ID 时只回填唯一安全候选，不覆盖已完成或歧义工具段', () => {
    const assistant: any = { role: 'assistant', segments: [], detailSegments: [], subAgents: [] };
    component.messages = [assistant];
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolName: 'search' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolName: 'search', result: '首次结果' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { toolName: 'search', result: '不得覆盖' } });
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolName: 'tool-a' } });
    dispatchSse(component, assistant, { event: 'tool_call', data: { toolName: 'tool-b' } });
    dispatchSse(component, assistant, { event: 'tool_result', data: { result: '歧义结果' } });

    expect(assistant.detailSegments).toEqual([
      { type: 'tool', content: '首次结果', toolId: 'search' },
      { type: 'tool', content: '', toolId: 'tool-a' },
      { type: 'tool', content: '', toolId: 'tool-b' },
    ]);
  });

  it('历史详情按 execution_id 恢复轮次段和子 Agent 归属', () => {
    const messages = (component as any).mapDetailToMessages([
      { role: 'user', content: '问题', execution_id: 'exec-1' },
      { role: 'assistant', event: 'message', content: '答案', execution_id: 'exec-1' },
      { role: 'assistant', event: 'reasoning', content: '思考', execution_id: 'exec-1' },
      { role: 'tool', content: '工具结果', tool_id: 'search', execution_id: 'exec-1' },
      {
        role: 'assistant', event: 'message', content: '子结果', execution_id: 'exec-1',
        sub_execution_id: 'sub-1', agent_id: 'agent-1',
      },
      {
        role: 'assistant', event: 'reasoning', content: '子思考', execution_id: 'exec-1',
        sub_execution_id: 'sub-1', agent_id: 'agent-1',
      },
      {
        role: 'tool', content: '子工具结果', tool_id: 'document', tool_call_id: 'sub-call', execution_id: 'exec-1',
        sub_execution_id: 'sub-1', agent_id: 'agent-1',
      },
    ]);

    expect(messages).toEqual([
      jasmine.objectContaining({
        userContent: '问题',
        segments: [{ type: 'message', content: '答案' }],
        detailSegments: [
          { type: 'reasoning', content: '思考' },
          { type: 'tool', content: '工具结果', toolId: 'search' },
        ],
        subAgents: [jasmine.objectContaining({
          subExecutionId: 'sub-1', agentId: 'agent-1',
          segments: [
            { type: 'message', content: '子结果' },
            { type: 'reasoning', content: '子思考' },
            { type: 'tool', content: '子工具结果', toolId: 'document', toolCallId: 'sub-call' },
          ],
        })],
      }),
    ]);
  });

  it('切换会话时清除推荐与激活标签，且不从历史恢复', async () => {
    (component as any).recommendedSkills = [skill('s1')];
    (component as any).activatedSkills = [{ skillId: 's1', name: '会议纪要', versionId: 'v1' }];

    service.activeSession$.next(session('c2'));
    await Promise.resolve();

    expect((component as any).recommendedSkills).toEqual([]);
    expect((component as any).activatedSkills).toEqual([]);
  });

  it('收到实际工作空间切换事件时立即清除状态并重载目录', () => {
    (component as any).recommendedSkills = [skill('s1')];
    (component as any).activatedSkills = [{ skillId: 's1', name: '会议纪要', versionId: 'v1' }];
    http.workspaceId = 'workspace-2';

    window.dispatchEvent(new Event('WorkspaceChange'));

    expect((component as any).recommendedSkills).toEqual([]);
    expect((component as any).activatedSkills).toEqual([]);
    expect(service.listSkills.calls.count()).toBeGreaterThan(1);
  });

  it('草稿创建请求占用发送权，双 send 只创建一个会话并禁用选择器', () => {
    const creation = deferred<SessionItem>();
    service.createSession.and.returnValue(creation.promise);
    component.currentSession = { conversation_id: '', title: '草稿', status: 'ACTIVE' };
    component.inputText = '整理会议';

    component.send();
    component.send();
    fixture.detectChanges();

    expect(service.createSession).toHaveBeenCalledTimes(1);
    expect(fixture.nativeElement.querySelector('.skill-input').disabled).toBeTrue();
    expect(fixture.nativeElement.querySelector('.send-btn').disabled).toBeTrue();
  });

  it('草稿创建期间的后续编辑不会被该 attempt 的 open 清除', async () => {
    const creation = deferred<SessionItem>();
    service.createSession.and.returnValue(creation.promise);
    component.currentSession = { conversation_id: '', title: '草稿', status: 'ACTIVE' };
    component.inputText = '第一轮';

    component.send();
    component.inputText = '下一轮草稿';
    (component as any).recommendedSkills = [skill('s2')];
    creation.resolve(session('created-1'));
    await Promise.resolve();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onOpen();

    expect(component.inputText).toBe('下一轮草稿');
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s2']);
  });

  it('草稿创建失败释放发送权并保留原输入与推荐', async () => {
    const creation = deferred<SessionItem>();
    service.createSession.and.returnValue(creation.promise);
    component.currentSession = { conversation_id: '', title: '草稿', status: 'ACTIVE' };
    component.inputText = '整理会议';
    (component as any).recommendedSkills = [skill('s1')];

    component.send();
    creation.reject(new Error('create failed'));
    await Promise.resolve();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.streaming).toBeFalse();
    expect(fixture.nativeElement.querySelector('.skill-input').disabled).toBeFalse();
    expect(component.inputText).toBe('整理会议');
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect(service.chatSSE).not.toHaveBeenCalled();
  });

  it('草稿创建完成前切换会话会使过期结果不能启动流或改当前会话', async () => {
    const creation = deferred<SessionItem>();
    service.createSession.and.returnValue(creation.promise);
    component.currentSession = { conversation_id: '', title: '草稿', status: 'ACTIVE' };
    component.inputText = '整理会议';

    component.send();
    service.activeSession$.next(session('c2'));
    creation.resolve(session('created-1'));
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('c2');
    expect(service.chatSSE).not.toHaveBeenCalled();
    expect(service.setActiveSession).not.toHaveBeenCalledWith(session('created-1'));
  });

  it('timeout 后重试时关闭旧 source，旧回调不会改写新 attempt', () => {
    const firstSource = { close: jasmine.createSpy('firstClose') };
    const secondSource = { close: jasmine.createSpy('secondClose') };
    service.chatSSE.and.returnValues(firstSource, secondSource);
    component.currentSession = session('c1');
    component.inputText = '第一轮';

    component.send();
    const firstCallbacks = service.chatSSE.calls.mostRecent().args[2];
    firstCallbacks.onTimeout();
    component.inputText = '第二轮';
    component.send();
    const secondCallbacks = service.chatSSE.calls.mostRecent().args[2];
    firstCallbacks.onOpen();
    firstCallbacks.onMessage({ data: JSON.stringify({ event: 'skill_activated', data: { skillId: 'old', name: '旧技能', versionId: 'v1' } }) });
    firstCallbacks.onDone();

    expect(firstSource.close).toHaveBeenCalledTimes(1);
    expect(component.streaming).toBeTrue();
    expect(component.inputText).toBe('第二轮');
    expect((component as any).activatedSkills).toEqual([]);
    secondCallbacks.onOpen();
  });

  it('同一 source 的 error 与 done 只收口一次', () => {
    const source = { close: jasmine.createSpy('close') };
    service.chatSSE.and.returnValue(source);
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onError();
    callbacks.onDone();

    expect(source.close).toHaveBeenCalledTimes(1);
    expect(service.refreshSessions).not.toHaveBeenCalled();
  });

  it('abort 终态关闭当前 source 并释放发送权', () => {
    const source = { close: jasmine.createSpy('close') };
    service.chatSSE.and.returnValue(source);
    component.currentSession = session('c1');
    component.inputText = '整理会议';

    component.send();
    service.chatSSE.calls.mostRecent().args[2].onAbort();

    expect(source.close).toHaveBeenCalledTimes(1);
    expect(component.isSending).toBeFalse();
  });

  it('流中会话切换先取消旧 attempt，再清空 Skill 状态且忽略旧事件', () => {
    const source = { close: jasmine.createSpy('close') };
    service.chatSSE.and.returnValue(source);
    component.currentSession = session('c1');
    component.inputText = '整理会议';
    (component as any).recommendedSkills = [skill('s1')];
    component.send();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];

    service.activeSession$.next({ conversation_id: '', title: '新草稿', status: 'ACTIVE' });
    callbacks.onMessage({ data: JSON.stringify({ event: 'skill_activated', data: { skillId: 'old', name: '旧技能', versionId: 'v1' } }) });

    expect(source.close).toHaveBeenCalledTimes(1);
    expect(component.streaming).toBeFalse();
    expect((component as any).recommendedSkills).toEqual([]);
    expect((component as any).activatedSkills).toEqual([]);
  });

  it('目录仅接受当前工作空间最新请求，且 refresh 失败不清空已恢复推荐', async () => {
    await Promise.resolve();
    const catalogA = deferred<ConversationSkillItem[]>();
    const catalogB = deferred<ConversationSkillItem[]>();
    service.listSkills.and.returnValues(catalogA.promise, catalogB.promise);
    (component as any).loadSkillCatalog();
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    catalogB.resolve([skill('b')]);
    await Promise.resolve();
    catalogA.resolve([skill('a')]);
    await Promise.resolve();

    expect(component.skillCatalog.map((item) => item.skillId)).toEqual(['b']);
    (component as any).recommendedSkills = [skill('b')];
    const refresh = deferred<ConversationSkillItem[]>();
    service.listSkills.and.returnValue(refresh.promise);
    component.currentSession = session('c2');
    component.inputText = '整理会议';
    component.send();
    service.chatSSE.calls.mostRecent().args[2].onError();
    refresh.reject(new Error('refresh failed'));
    await Promise.resolve();

    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['b']);
    expect(component.skillCatalog.map((item) => item.skillId)).toEqual(['b']);
  });

  it('同 workspace 的外部 WorkspaceChange 噪声不清理本轮状态', () => {
    (component as any).recommendedSkills = [skill('s1')];
    (component as any).activatedSkills = [{ skillId: 's1', name: '会议纪要', versionId: 'v1' }];
    const callsBefore = service.listSkills.calls.count();

    window.dispatchEvent(new Event('WorkspaceChange'));

    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect((component as any).activatedSkills).toEqual([{ skillId: 's1', name: '会议纪要', versionId: 'v1' }]);
    expect(service.listSkills.calls.count()).toBe(callsBefore);
  });

  it('草稿晋升不会加载详情，晚到详情也不会覆盖本轮气泡和 run_done', async () => {
    const oldDetail = deferred<any>();
    service.detailSession.and.returnValue(oldDetail.promise);
    service.activeSession$.next(session('old-session'));
    service.activeSession$.next({ conversation_id: '', title: '草稿', status: 'ACTIVE' });
    component.inputText = '整理会议';

    component.send();
    await Promise.resolve();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onMessage({ data: JSON.stringify({ event: 'message', data: { delta: '流式文本' } }) });
    callbacks.onMessage({ data: JSON.stringify({ event: 'run_done', data: { text: '最终文本' } }) });
    oldDetail.resolve({ messages: [] });
    await Promise.resolve();

    expect(service.detailSession).toHaveBeenCalledTimes(1);
    expect(component.messages).toEqual([
      jasmine.objectContaining({
        userContent: '整理会议',
        segments: [{ type: 'message', content: '流式文本' }],
        loading: false,
      }),
    ]);
  });

  it('仅接受当前会话最新详情，c1 的晚到结果不能覆盖 c2', async () => {
    const c1 = deferred<any>();
    const c2 = deferred<any>();
    service.detailSession.and.returnValues(c1.promise, c2.promise);

    service.activeSession$.next(session('c1'));
    service.activeSession$.next(session('c2'));
    c2.resolve({ messages: [{ role: 'assistant', event: 'message', content: 'c2', execution_id: 'e2' }] });
    await Promise.resolve();
    c1.resolve({ messages: [{ role: 'assistant', event: 'message', content: 'c1', execution_id: 'e1' }] });
    await Promise.resolve();

    expect(component.messages.map((message: any) => message.segments)).toEqual([
      [{ type: 'message', content: 'c2' }],
    ]);
  });

  it('切换工作空间或销毁后，旧详情的 resolve/reject 都不会写入页面', async () => {
    const detailA = deferred<any>();
    service.detailSession.and.returnValue(detailA.promise);
    service.activeSession$.next(session('c1'));
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    detailA.resolve({ messages: [{ role: 'assistant', content: 'workspace-a' }] });
    await Promise.resolve();

    expect(component.messages).toEqual([]);
    const detailB = deferred<any>();
    service.detailSession.and.returnValue(detailB.promise);
    service.activeSession$.next(session('c2'));
    component.ngOnDestroy();
    detailB.reject(new Error('late failure'));
    await Promise.resolve();

    expect(component.messages).toEqual([]);
  });

  it('A 到 B 后 A 的详情 reject 被消费且不影响 B 页面', async () => {
    const detailA = deferred<any>();
    service.detailSession.and.returnValue(detailA.promise);
    service.activeSession$.next(session('c1'));
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));

    detailA.reject(new Error('workspace-a late failure'));
    await Promise.resolve();

    expect(component.messages).toEqual([]);
    expect(component.currentSession).toBeNull();
  });

  it('chatSSE 同步抛错按连接前失败收口，保留输入和推荐', () => {
    service.chatSSE.and.throwError(() => new Error('bad region'));
    component.currentSession = session('c1');
    component.inputText = '整理会议';
    (component as any).recommendedSkills = [skill('s1')];

    component.send();

    expect(component.isSending).toBeFalse();
    expect(component.streaming).toBeFalse();
    expect(component.inputText).toBe('整理会议');
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect(service.listSkills.calls.count()).toBeGreaterThan(1);
  });

  it('source.close 抛错时 error、timeout、切换和销毁仍释放 attempt 与监听器', () => {
    const source = { close: jasmine.createSpy('close').and.throwError(new Error('close failed')) };
    service.chatSSE.and.returnValue(source);
    component.currentSession = session('c1');
    component.inputText = '第一轮';
    component.send();
    service.chatSSE.calls.mostRecent().args[2].onError();
    expect(component.isSending).toBeFalse();

    component.inputText = '第二轮';
    component.send();
    service.chatSSE.calls.mostRecent().args[2].onTimeout();
    expect(component.isSending).toBeFalse();

    component.inputText = '第三轮';
    component.send();
    service.activeSession$.next(session('c2'));
    expect(component.isSending).toBeFalse();

    component.inputText = '第四轮';
    component.send();
    expect(() => component.ngOnDestroy()).not.toThrow();
    expect(component.isSending).toBeFalse();
  });

  it('流中重复相同 conversation_id 通知不取消 attempt、不清 Skill 或重复加载详情', () => {
    const source = { close: jasmine.createSpy('close') };
    service.chatSSE.and.returnValue(source);
    service.activeSession$.next(session('c1'));
    const initialDetails = service.detailSession.calls.count();
    component.inputText = '整理会议';
    (component as any).recommendedSkills = [skill('s1')];
    component.send();
    (component as any).activatedSkills = [{ skillId: 's1', name: '会议纪要', versionId: 'v1' }];

    service.setActiveSession(session('c1'));

    expect(component.isSending).toBeTrue();
    expect(source.close).not.toHaveBeenCalled();
    expect((component as any).recommendedSkills.map((item: ConversationSkillItem) => item.skillId)).toEqual(['s1']);
    expect((component as any).activatedSkills).toEqual([{ skillId: 's1', name: '会议纪要', versionId: 'v1' }]);
    expect(service.detailSession.calls.count()).toBe(initialDetails);
  });

  it('同一 conversation_id 的 query-param 重发不取消正在运行的流', () => {
    const source = { close: jasmine.createSpy('close') };
    const route = TestBed.inject(ActivatedRoute).queryParams as BehaviorSubject<any>;
    service.chatSSE.and.returnValue(source);
    service.activeSession$.next(session('c1'));
    component.inputText = '整理会议';
    component.send();

    route.next({ conversation_id: 'c1' });

    expect(component.isSending).toBeTrue();
    expect(source.close).not.toHaveBeenCalled();
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('工作空间 A/c1 切到 B 后立即发送会创建 B 草稿，且不保留 A 会话', async () => {
    service.activeSession$.next(session('c1'));
    const detailsBeforeTransition = service.detailSession.calls.count();
    http.workspaceId = 'workspace-2';

    window.dispatchEvent(new Event('WorkspaceChange'));
    expect(component.currentSession).toBeNull();
    expect(service.activeSession$.value).toBeNull();
    component.inputText = 'B 空间的新问题';
    component.send();
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(service.activeSession$.value?.conversation_id).toBe('new-session');
    expect(service.createSession).toHaveBeenCalledWith({ title: '' });
    expect(service.chatSSE).toHaveBeenCalledWith('new-session', jasmine.any(Object), jasmine.any(Object));
    expect(service.chatSSE).not.toHaveBeenCalledWith('c1', jasmine.any(Object), jasmine.any(Object));
    expect(service.detailSession.calls.count()).toBe(detailsBeforeTransition);
  });

  it('A/c1 切到 B 会替换为新草稿路由，旧 URL 重放或按旧 URL 重建均不能重新打开 c1', async () => {
    service.activeSession$.next(session('c1'));
    const detailsBeforeTransition = service.detailSession.calls.count();
    http.workspaceId = 'workspace-2';

    window.dispatchEvent(new Event('WorkspaceChange'));
    expect(router.navigate).toHaveBeenCalledWith(['/home/conversation'], jasmine.objectContaining({
      queryParams: jasmine.objectContaining({ new: jasmine.any(Number) }),
      replaceUrl: true,
    }));
    routeParams.next({ conversation_id: 'c1' });
    component.inputText = 'B 空间重建后的问题';
    component.send();
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(service.detailSession.calls.count()).toBe(detailsBeforeTransition);
    expect(service.chatSSE).not.toHaveBeenCalledWith('c1', jasmine.any(Object), jasmine.any(Object));
    expect(service.chatSSE).toHaveBeenCalledWith('new-session', jasmine.any(Object), jasmine.any(Object));
  });

  it('A/c0→A/c1→B 后浏览器回退 c0 不会在 B 加载详情或发送旧会话', async () => {
    service.activeSession$.next(session('c0'));
    service.activeSession$.next(session('c1'));
    const detailsBeforeTransition = service.detailSession.calls.count();
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));

    routeParams.next({ conversation_id: 'c0' });
    component.inputText = 'B 空间问题';
    component.send();
    await Promise.resolve();

    expect(service.detailSession.calls.count()).toBe(detailsBeforeTransition);
    expect(service.chatSSE).not.toHaveBeenCalledWith('c0', jasmine.any(Object), jasmine.any(Object));
    expect(service.chatSSE).toHaveBeenCalledWith('new-session', jasmine.any(Object), jasmine.any(Object));
  });

  it('导航 resolve false 后按旧 URL 重建仍验证 B 空间归属，不打开 A 会话', async () => {
    router.navigate.and.resolveTo(false);
    service.activeSession$.next(session('c1'));
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    service.detailSession.calls.reset();
    component.ngOnDestroy();
    fixture.destroy();
    routeParams.next({ conversation_id: 'c1' });
    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.selectedModel = 'model-1';
    component.inputText = 'B 空间重建问题';
    component.send();
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(service.detailSession).not.toHaveBeenCalledWith('c1');
    expect(service.chatSSE).not.toHaveBeenCalledWith('c1', jasmine.any(Object), jasmine.any(Object));
  });

  it('导航 reject 后按旧 URL 重建仍验证 B 空间归属', () => {
    router.navigate.and.returnValue(Promise.reject(new Error('navigation rejected')));
    service.activeSession$.next(session('c1'));
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    service.detailSession.calls.reset();
    component.ngOnDestroy();
    fixture.destroy();
    routeParams.next({ conversation_id: 'c1' });
    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();

    expect(component.currentSession).toBeNull();
    expect(service.detailSession).not.toHaveBeenCalledWith('c1');
  });

  it('B 空间列表已验证的同 ID 会话可正常打开', () => {
    service.activeSession$.next(session('c1'));
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    publishSessionList(service, 'workspace-2', [session('c1')]);
    routeParams.next({ conversation_id: 'c1' });

    expect(component.currentSession?.conversation_id).toBe('c1');
    expect(service.detailSession).toHaveBeenCalledWith('c1');
  });

  it('历史 provenance 为 A、当前 B 的无标记旧路由须等待 B 会话列表验证', async () => {
    component.ngOnDestroy();
    fixture.destroy();
    sessionStorage.setItem('conversation-workspace-route-workspace', 'workspace-a');
    http.workspaceId = 'workspace-b';
    routeParams.next({ conversation_id: 'c1' });
    service.detailSession.calls.reset();

    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.selectedModel = 'model-1';
    component.inputText = 'B 空间新问题';
    component.send();
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(service.detailSession).not.toHaveBeenCalledWith('c1');
    expect(service.chatSSE).not.toHaveBeenCalledWith('c1', jasmine.any(Object), jasmine.any(Object));
  });

  it('A/c1 残留 active 回放不能清除 B 的同 ID pending 或以 B 请求旧会话', async () => {
    http.workspaceId = 'workspace-a';
    service.activeSession$.next(session('c1'));
    component.ngOnDestroy();
    fixture.destroy();
    sessionStorage.setItem('conversation-workspace-route-workspace', 'workspace-a');
    http.workspaceId = 'workspace-b';
    routeParams.next({ conversation_id: 'c1' });
    service.detailSession.calls.reset();
    service.chatSSE.calls.reset();

    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    component.selectedModel = 'model-1';
    component.inputText = 'B 空间新问题';
    component.send();
    await Promise.resolve();

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(service.detailSession).not.toHaveBeenCalledWith('c1');
    expect(service.chatSSE).not.toHaveBeenCalledWith('c1', jasmine.any(Object), jasmine.any(Object));
  });

  it('A/c2 残留 active 不抢占 B/c1 pending，B 列表证明后才打开 c1', () => {
    http.workspaceId = 'workspace-a';
    service.activeSession$.next(session('c2'));
    component.ngOnDestroy();
    fixture.destroy();
    sessionStorage.setItem('conversation-workspace-route-workspace', 'workspace-a');
    http.workspaceId = 'workspace-b';
    routeParams.next({ conversation_id: 'c1' });
    service.detailSession.calls.reset();

    fixture = TestBed.createComponent(ConversationWorkspaceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    publishSessionList(service, 'workspace-b', [session('c1')]);

    expect(component.currentSession?.conversation_id).toBe('c1');
    expect(service.detailSession).not.toHaveBeenCalledWith('c2');
    expect(service.detailSession).toHaveBeenCalledWith('c1');
  });

  it('无标记 B 路由早于列表到达时，在列表验证后只打开一次', () => {
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    service.detailSession.calls.reset();
    publishSessionList(service, 'workspace-1', [session('b1')]);
    publishSessionList(service, 'workspace-1', [session('b1')]);

    expect(component.currentSession?.conversation_id).toBe('b1');
    expect(service.detailSession).toHaveBeenCalledTimes(1);
    expect(service.detailSession).toHaveBeenCalledWith('b1');
  });

  it('显式 workspace_id 仍只接受当前空间并直接打开', () => {
    routeParams.next({ conversation_id: 'other', workspace_id: 'workspace-2' });
    expect(service.detailSession).not.toHaveBeenCalledWith('other');

    routeParams.next({ conversation_id: 'current', workspace_id: 'workspace-1' });
    expect(component.currentSession?.conversation_id).toBe('current');
    expect(service.detailSession).toHaveBeenCalledWith('current');
  });

  it('无标记 pending 路由不在后续列表缺失时加载详情或向旧 ID 发送', async () => {
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    publishSessionList(service, 'workspace-1', [session('b2')]);
    component.inputText = '新草稿问题';
    component.send();
    await Promise.resolve();

    expect(service.detailSession).not.toHaveBeenCalledWith('b1');
    expect(service.chatSSE).not.toHaveBeenCalledWith('b1', jasmine.any(Object), jasmine.any(Object));
    expect(service.chatSSE).toHaveBeenCalledWith('new-session', jasmine.any(Object), jasmine.any(Object));
  });

  it('pending 只接受带有当前 workspace 归属的会话列表', () => {
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    publishSessionList(service, 'workspace-a', [session('b1')]);

    expect(component.currentSession).toBeNull();
    expect(service.detailSession).not.toHaveBeenCalledWith('b1');

    publishSessionList(service, 'workspace-1', [session('b1')]);

    expect(component.currentSession?.conversation_id).toBe('b1');
    expect(service.detailSession).toHaveBeenCalledWith('b1');
  });

  it('新草稿发送会原子失效 pending，晚到列表不能抢占或取消新流', async () => {
    const source = { close: jasmine.createSpy('close') };
    service.chatSSE.and.returnValue(source);
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    component.inputText = '开始新草稿';
    component.send();
    await Promise.resolve();
    const callbacks = service.chatSSE.calls.mostRecent().args[2];
    callbacks.onOpen();
    publishSessionList(service, 'workspace-1', [session('b1')]);

    expect(component.currentSession?.conversation_id).toBe('new-session');
    expect(component.isSending).toBeTrue();
    expect(source.close).not.toHaveBeenCalled();
    expect(service.detailSession).not.toHaveBeenCalledWith('b1');
  });

  it('非 pending 验证引起的有效会话切换会失效旧 pending', () => {
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    service.activeSession$.next(session('c2'));
    publishSessionList(service, 'workspace-1', [session('b1')]);

    expect(component.currentSession?.conversation_id).toBe('c2');
    expect(service.detailSession).not.toHaveBeenCalledWith('b1');
  });

  it('路由更新、工作空间切换与销毁都会丢弃旧的 pending 路由', () => {
    (component as any).workspaceRouteProvenance = 'workspace-1';
    routeParams.next({ conversation_id: 'b1' });
    routeParams.next({ conversation_id: 'b2' });
    publishSessionList(service, 'workspace-1', [session('b1')]);
    expect(service.detailSession).not.toHaveBeenCalledWith('b1');

    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    publishSessionList(service, 'workspace-2', [session('b2')]);
    component.ngOnDestroy();
    publishSessionList(service, 'workspace-2', [session('b2')]);

    expect(component.currentSession).toBeNull();
    expect(service.detailSession).not.toHaveBeenCalledWith('b2');
  });

  it('导航 resolve false 在组件销毁后不触发旧视图变更检测', async () => {
    const navigation = deferred<boolean>();
    router.navigate.and.returnValue(navigation.promise);
    const markForCheck = spyOn((component as any).cdr, 'markForCheck');
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    markForCheck.calls.reset();
    component.ngOnDestroy();
    navigation.resolve(false);
    await Promise.resolve();

    expect(markForCheck).not.toHaveBeenCalled();
  });

  it('导航 reject 在组件销毁后不触发旧视图变更检测', async () => {
    const navigation = deferred<boolean>();
    router.navigate.and.returnValue(navigation.promise);
    const markForCheck = spyOn((component as any).cdr, 'markForCheck');
    http.workspaceId = 'workspace-2';
    window.dispatchEvent(new Event('WorkspaceChange'));
    markForCheck.calls.reset();
    component.ngOnDestroy();
    navigation.reject(new Error('navigation rejected'));
    await Promise.resolve();

    expect(markForCheck).not.toHaveBeenCalled();
  });

  it('组件销毁后，晚到 Skill 目录 resolve 不写入状态或触发变更检测', async () => {
    const catalog = deferred<ConversationSkillItem[]>();
    service.listSkills.and.returnValue(catalog.promise);
    const markForCheck = spyOn((component as any).cdr, 'markForCheck');
    const catalogBefore = component.skillCatalog;
    const unavailableBefore = component.skillCatalogUnavailable;
    (component as any).loadSkillCatalog();
    component.ngOnDestroy();
    catalog.resolve([skill('late')]);
    await Promise.resolve();

    expect(component.skillCatalog).toBe(catalogBefore);
    expect(component.skillCatalogUnavailable).toBe(unavailableBefore);
    expect(markForCheck).not.toHaveBeenCalled();
  });

  it('组件销毁后，晚到 Skill 目录 reject 不写不可用状态或触发变更检测', async () => {
    const catalog = deferred<ConversationSkillItem[]>();
    service.listSkills.and.returnValue(catalog.promise);
    const markForCheck = spyOn((component as any).cdr, 'markForCheck');
    const catalogBefore = component.skillCatalog;
    const unavailableBefore = component.skillCatalogUnavailable;
    (component as any).loadSkillCatalog();
    component.ngOnDestroy();
    catalog.reject(new Error('late catalog failure'));
    await Promise.resolve();

    expect(component.skillCatalog).toBe(catalogBefore);
    expect(component.skillCatalogUnavailable).toBe(unavailableBefore);
    expect(markForCheck).not.toHaveBeenCalled();
  });
});

describe('ConversationWorkspaceService', () => {
  it('当前会话状态携带设置时的 workspace 归属', () => {
    const workspace = { id: 'workspace-a' };
    const service = createWorkspaceService({ getWorkspaceId: () => workspace.id });

    service.setActiveSession(session('c1'));
    workspace.id = 'workspace-b';

    expect(service.activeSessionState$.value).toEqual(jasmine.objectContaining({
      workspaceId: 'workspace-a', session: session('c1'),
    }));
  });

  it('刷新列表只写入请求时仍为当前 workspace 的最新响应及其归属快照', async () => {
    const workspace = { id: 'workspace-a' };
    const responseA = deferred<any>();
    const responseB = deferred<any>();
    const http = {
      getWorkspaceId: () => workspace.id,
      getAsync: jasmine.createSpy('getAsync').and.callFake(({ query }: any) =>
        query.workspace_id === 'workspace-a' ? responseA.promise : responseB.promise),
    };
    const service = createWorkspaceService(http);

    const pendingA = service.refreshSessions();
    workspace.id = 'workspace-b';
    service.clearSessions();
    const pendingB = service.refreshSessions();
    responseA.resolve({ items: [session('c1')] });
    await pendingA;

    expect(service.sessions$.value).toEqual([]);
    expect(service.sessionListState$.value).toEqual(jasmine.objectContaining({
      workspaceId: 'workspace-b', sessions: [],
    }));

    responseB.resolve({ items: [session('b1')] });
    await pendingB;

    expect(service.sessions$.value.map((item) => item.conversation_id)).toEqual(['b1']);
    expect(service.sessionListState$.value).toEqual(jasmine.objectContaining({
      workspaceId: 'workspace-b', sessions: [session('b1')],
    }));
  });

  it('加载目录时只携带工作空间并映射最小浏览器字段', async () => {
    const http = {
      getWorkspaceId: jasmine.createSpy('getWorkspaceId').and.returnValue('workspace-1'),
      getAsync: jasmine.createSpy('getAsync').and.resolveTo([
        { skill_id: 's1', name: '会议纪要', description: '整理会议内容' },
      ]),
    };
    const service = createWorkspaceService(http);

    await expectAsync(service.listSkills()).toBeResolvedTo([
      { skillId: 's1', name: '会议纪要', description: '整理会议内容' },
    ]);
    expect(http.getAsync).toHaveBeenCalledWith({
      url: '/v1/project/conversation/sessions/skills',
      query: { workspace_id: 'workspace-1' },
    });
  });

  it('完整转发推荐 ID，并保留既有 SSE 地址、头、超时和九类回调注册', () => {
    sessionStorage.setItem('cfCurrentRegion', JSON.stringify('region-1'));
    spyOn(XMLHttpRequest.prototype, 'open').and.stub();
    spyOn(XMLHttpRequest.prototype, 'send').and.stub();
    spyOn(XMLHttpRequest.prototype, 'setRequestHeader').and.stub();
    const service = createWorkspaceService({ prefixPath: '/api', getWorkspaceId: () => 'workspace-1' });
    const source = service.chatSSE('conversation-1', {
      query: '整理会议',
      model_deployment_id: 'model-1',
      recommended_skill_ids: ['s2', 's1'],
    }, {});

    expect((source as any).url).toBe('/api/v1/project/conversation/sessions/conversation-1/messages?workspace_id=workspace-1');
    expect(JSON.parse((source as any).payload)).toEqual({
      query: '整理会议',
      model_deployment_id: 'model-1',
      recommended_skill_ids: ['s2', 's1'],
    });
    expect((source as any).headers).toEqual(jasmine.objectContaining({
      'Content-Type': 'application/json',
      stream: 'true',
      'X-Language': 'zh-cn',
      'X-Invoke-Mode': 'PUBLISHED',
    }));
    expect((source as any).timeout).toBe(3600000);
    expect((source as any).streamFirstChunkTimeout).toBe(180000);
    expect((source as any).streamTimeout).toBe(180000);
    expect(Object.keys((source as any).listeners).sort()).toEqual([
      'abort', 'done', 'error', 'message', 'moderation', 'open', 'readystatechange', 'status', 'timeout',
    ]);
  });
});

function skill(skillId: string): ConversationSkillItem {
  return { skillId, name: `name-${skillId}`, description: `description-${skillId}` };
}

function session(conversationId: string): SessionItem {
  return { conversation_id: conversationId, title: '会话', status: 'ACTIVE' };
}

function publishSessionList(service: any, workspaceId: string, sessions: SessionItem[]): void {
  const generation = service.sessionListState$.value.generation + 1;
  service.sessions$.next(sessions);
  service.sessionListState$.next({ workspaceId, generation, sessions });
}

function dispatchSse(component: ConversationWorkspaceComponent, assistant: any, payload: object): void {
  (component as any).handleMessage({ data: JSON.stringify(payload) }, assistant);
}

function createWorkspaceService(http: any): ConversationWorkspaceService {
  return new ConversationWorkspaceService(
    http,
    { baseUrl: '/v1/project', projectId: 'project' } as any,
    { getConfigs: () => ({}) } as any,
  );
}

function deferred<T>(): { promise: Promise<T>; resolve: (value: T) => void; reject: (reason: unknown) => void } {
  let resolve!: (value: T) => void;
  let reject!: (reason: unknown) => void;
  return { promise: new Promise<T>((resolvePromise, rejectPromise) => { resolve = resolvePromise; reject = rejectPromise; }), resolve, reject };
}
