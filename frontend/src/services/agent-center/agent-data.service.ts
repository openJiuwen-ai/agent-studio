import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import {
  EPluginCategoryTabId, InputVarInfo,
  IVoiceInteraction, ReferenceResponse,
} from '@routes/agent-center/types/my-workspace.types';
import { IMemoParam } from '@routes/agent-center/app-agent/components/create-memo/types';
import { IWorkflowField } from '@routes/agent-center/app-flow/node.type';
import { IAgentVarCachedVal } from '@routes/agent-center/app-agent/components/var-config/var-config.component';
import { IContentReview } from '@routes/agent-center/app-flow/node.type';
import { IRefInfo, IWorkflowApp } from "@routes/agent-center/app-flow/app-flow.types";
import { MemoryVariableInputParamType } from '@routes/agent-center/interfaces/agent/app-agent.interface';
export interface AgentMemeryVar {
  variable_key: string,
  description: string,
  default_value: string
}
@Injectable({
  providedIn: 'root',
})
export class AgentDataService {
  private readonly optimizePromptText$ = new BehaviorSubject<string>('');

  // 调用插件列表接口分3种情况：刚进入Agent创编页，添加插件后，还是新建插件后。初始值是刚进入Agent创编页
  private readonly isClickAddPlugin$ = new BehaviorSubject<string>('init');

  // 存储用户新建个人插件之前，激活的tabId和已选中的插件数组
  private readonly pluginsAndTabIdClicked$ = new BehaviorSubject<any>({
    currentTabId: EPluginCategoryTabId.PERSONAL,
    plugins: [],
  });

  // 调用工作流列表接口分2种情况：刚进入Agent创编页，添加工作流后。初始值是刚进入Agent创编页
  private readonly isClickAddWorkflow$ = new BehaviorSubject<string>('init');

  // 调用知识库列表接口分2种情况：刚进入Agent创编页，添加知识库后。初始值是刚进入Agent创编页
  private readonly isClickAddKnowledge$ = new BehaviorSubject<string>('init');

  // 存储用户新建知识库之前，激活的tabId和已选中的知识库数组
  private readonly knowledgesAndTabIdClicked$ = new BehaviorSubject<any>({
    knowledges: [],
  });

  // 调用MCP列表接口分3种情况：刚进入Agent创编页，添加MCP后，还是新建MCP后。初始值是刚进入Agent创编页
  private readonly isClickAddMCP$ = new BehaviorSubject<string>('init');

  // 存储用户新建MCP服务之前，激活的tabId和已选中的MCP服务数组
  private readonly mcpsAndTabIdClicked$ = new BehaviorSubject<any>({
    currentTabId: EPluginCategoryTabId.MARKET,
    list: [],
  });

  // 存储开场白和推荐问题
  private readonly openTextAndQuestions$ = new BehaviorSubject<any>({
    prologue: '',
    suggest_queries: [],
  });

  // 存储应用名称和描述问题
  private readonly nameAndDescription$ = new BehaviorSubject<any>({
    name: '',
    descriptions:  '',
  });

  // 存储trigger save的时间，用于展示"自动保存于xx::yy:zz"
  private readonly autoSaveTime$ = new BehaviorSubject<string>('');

  // 存储模型配置
  private readonly promptAndModelConfig$ = new BehaviorSubject<any>({
    prompt: '',
    modelConfig: {},
  });

  // 存储
  private readonly agentConfig$ = new BehaviorSubject<any>({
    name: '',
    description: '',
    modelConfig: {}
  });

  // 存储应用名称和追问prompt配置
  private readonly nameAndPromptConfig$ = new BehaviorSubject<any>({
    name: '',
    prompt: '',
    enable: false,
  });

  private readonly voiceConfig$ = new BehaviorSubject<IVoiceInteraction>(null);

  private readonly referenceConfig$ = new BehaviorSubject<ReferenceResponse>(null);

  // 存储创建的触发器信息
  private readonly triggerAdded$ = new BehaviorSubject<any>({
    trigger_id: '',
    name: '',
    type: '',
    cron: '',
  });

  // 是否点击触发器的添加按钮
  private readonly triggerBtnClicked$ = new BehaviorSubject<boolean>(false);

  // 存储最新的插件列表。作用是检查插件列表是否存在代码解释器
  private readonly pluginList$ = new BehaviorSubject<any>([]);

  // 是否点击调试insight的按钮
  private readonly isClickInsight$ = new BehaviorSubject<boolean>(false);

  // 插件预览版本id
  private readonly versionId$ = new BehaviorSubject<{
    version_id: string;
    version_name: string;
  }>(undefined);

  // 发布的应用类型。枚举值为'agent'和'flow'
  private readonly appType$ = new BehaviorSubject<string>('');

  // 是否发布成功一个版本。用于在跳转到"发布管理"页面之前展示loading效果
  private readonly isVersionPublished$ = new BehaviorSubject<string>('');

  // 存储点击还原版本按钮对应的version_id
  private readonly rollbackVersionId$ = new BehaviorSubject<{
    version_id: string;
    version_name?: string;
    isFlowReadonly?: boolean;
    draft?: boolean;
  }>({ version_id: '' });

  // 是否存在一轮QA。用于判断长期记忆的生成按钮可点击
  private readonly hasQAHistory$ = new BehaviorSubject<boolean>(false);

  // 存储get接口和put接口返回的status值
  private readonly agentStatus$ = new BehaviorSubject<string>('');

  // 存储应用或工作流的历史版本列表
  private readonly historyVersionList$ = new BehaviorSubject<any>([]);

  // 记忆变量
  private readonly memos$ = new BehaviorSubject<IMemoParam[]>([]);

  // 存储已绑定的插件和工作流列表
  private readonly pluginAndFlowList$ = new BehaviorSubject<any>({});

  // 插件调测结果解析出来的响应参数
  private readonly pluginDebugRes$ = new BehaviorSubject<string>('');

  private readonly agentVars$ = new BehaviorSubject<IWorkflowField[]>([]);

  // 用户变量
  private readonly agentMemeryVars$ = new BehaviorSubject<AgentMemeryVar[]>([]);

  // 入参变量
  private readonly inputMemoryVars$ = new BehaviorSubject<InputVarInfo[]>([]);

  // 用户在预览调试更新入参变量的值
  private readonly inputMemoryInPreviewDebugger$ = new BehaviorSubject<MemoryVariableInputParamType[]>([]);

  private readonly agentCachedVarMap$ = new BehaviorSubject<
    Record<string, IAgentVarCachedVal>
  >({});

  private readonly agentInfo$ = new BehaviorSubject<any>({});

  public setAgentCachedVarMap(map: Record<string, IAgentVarCachedVal>) {
    this.agentCachedVarMap$.next(map);
  }

  public getAgentCachedVarMap() {
    return this.agentCachedVarMap$.getValue();
  }

  public setAgentVars(vars: IWorkflowField[]): void {
    this.agentVars$.next(vars);
  }

  public agentVarsUpdate$() {
    return this.agentVars$.asObservable();
  }

  public setAgentMemeryVars(vars: AgentMemeryVar[]): void {
    this.agentMemeryVars$.next(vars);
  }

  public agentMemeryVarsUpdate$() {
    return this.agentMemeryVars$.asObservable();
  }

  public setInputMemoryVars(vars: InputVarInfo[]): void {
    this.inputMemoryVars$.next(vars);
  }

  public inputMemoryVarsUpdate$() {
    return this.inputMemoryVars$.asObservable();
  }

  public setInputMemoryInPreviewDebugger(vars: MemoryVariableInputParamType[]) {
    this.inputMemoryInPreviewDebugger$.next(vars);
  }

  public inputMemoryInPreviewDebuggerUpdate$() {
    return this.inputMemoryInPreviewDebugger$.asObservable();
  }

  // 存储内容审核配置的值
  private readonly contentReviewConfig$ = new BehaviorSubject<IContentReview>({
    enabled: false,
    filter: { keywords: '' },
    replace: [],
    reply: [],
  });

  public setMemos(memos: IMemoParam[]): void {
    if (!Array.isArray(memos)) {
      return;
    }
    this.memos$.next([...memos]);
  }

  public memosUpdate$() {
    return this.memos$.asObservable();
  }

  public setPromptText(promptText: string): void {
    this.optimizePromptText$.next(promptText);
  }

  public promptTextUpdate$(): Observable<any> {
    return this.optimizePromptText$.asObservable();
  }

  /** 调用插件列表接口分3种情况：刚进入Agent创编页，添加插件后，还是新建插件后。初始值是刚进入Agent创编页 */
  public setClickFlagPlugin(clickFlag: string): void {
    this.isClickAddPlugin$.next(clickFlag);
  }

  public clickFlagPluginUpdate$(): Observable<string> {
    return this.isClickAddPlugin$.asObservable();
  }

  /** 调用工作流列表接口分2种情况：刚进入Agent创编页，添加工作流后。初始值是刚进入Agent创编页 */
  public setClickFlagWorkflow(clickFlag: string): void {
    this.isClickAddWorkflow$.next(clickFlag);
  }

  public clickFlagWorkflowUpdate$(): Observable<string> {
    return this.isClickAddWorkflow$.asObservable();
  }

  /** 调用知识库列表接口分2种情况：刚进入Agent创编页，添加知识库后。初始值是刚进入Agent创编页 */
  public setClickFlagKnowledge(clickFlag: string): void {
    this.isClickAddKnowledge$.next(clickFlag);
  }

  public clickFlagKnowledgeUpdate$(): Observable<string> {
    return this.isClickAddKnowledge$.asObservable();
  }

  /** 调用MCP列表接口分3种情况：刚进入Agent创编页，添加MCP后，还是新建MCP后。初始值是刚进入Agent创编页 */
  public setClickFlagMCP(clickFlag: string): void {
    this.isClickAddMCP$.next(clickFlag);
  }

  public clickFlagMCPUpdate$(): Observable<string> {
    return this.isClickAddMCP$.asObservable();
  }

  /** 用于记住用户新建插件之前，激活的tabId和已选中的插件数组 */
  public setPluginsAndTabId(tabId: string, plugins: any[]): void {
    this.pluginsAndTabIdClicked$.next({
      currentTabId: tabId,
      plugins: plugins,
    });
  }

  public pluginsAndTabIdUpdate$(): Observable<any[]> {
    return this.pluginsAndTabIdClicked$.asObservable();
  }

  /** 用于记住用户新建知识库之前，已选中的知识库数组 */
  public setKnowledges(knowledges: any[]): void {
    this.knowledgesAndTabIdClicked$.next({
      knowledges,
    });
  }

  public knowledgesUpdate$(): Observable<any[]> {
    return this.knowledgesAndTabIdClicked$.asObservable();
  }

  /** 用于记住用户新建MCP服务之前，激活的tabId和已选中的MCP服务数组 */
  public setMCPsAndTabId(tabId: string, list: any[]): void {
    this.mcpsAndTabIdClicked$.next({
      currentTabId: tabId,
      list,
    });
  }

  public mcpsAndTabIdUpdate$(): Observable<any[]> {
    return this.mcpsAndTabIdClicked$.asObservable();
  }

  /** 用于在调试预览实时显示开场白和推荐问题 */
  public setOpenTextAndQuestions(data: {
    prologue?: string;
    suggest_queries?: string[];
  }): void {
    const curVal = this.openTextAndQuestions$.getValue();
    this.openTextAndQuestions$.next({
      ...curVal,
      ...data,
    });
  }

  /** 用于在调试预览实时显示名称和描述 */
  public setNameAndDescription(data: {
    name?: string;
    description?: string;
  }): void {
    const curVal = this.nameAndDescription$.getValue();
    this.nameAndDescription$.next({
      ...curVal,
      ...data,
    });
  }

  public openTextAndQuestionsUpdate$(): Observable<any[]> {
    return this.openTextAndQuestions$.asObservable();
  }

  /** 自动保存于xx:yy:zz */
  public setAutoSaveTime(updateTime: string): void {
    this.autoSaveTime$.next(updateTime);
  }

  public autoSaveTimeUpdate$(): Observable<string> {
    return this.autoSaveTime$.asObservable();
  }

  public getAutoSaveTime(): string {
    return this.autoSaveTime$.getValue();
  }

  /** 用于保存模型配置 */
  public setPromptAndModelConfig(data: {
    prompt?: string;
    modelConfig?: any;
  }): void {
    const curVal = this.promptAndModelConfig$.getValue();
    this.promptAndModelConfig$.next({
      ...curVal,
      ...data,
    });
  }
  public promptAndModelConfigUpdate$(): Observable<any[]> {
    return this.promptAndModelConfig$.asObservable();
  }

  public getPromptAndModelConfig(): any {
    return this.promptAndModelConfig$.getValue()?.modelConfig;
  }

  /** 用于保存模型 */
  public setAgentConfig(data: {
    name?: string;
    description?: string;
    modelConfig?: any;
  }): void {
    this.agentConfig$.next({
      ...data,
    });
  }

  public agentConfigUpdate(): Observable<any[]> {
    return this.agentConfig$.asObservable();
  }

  /** 用于保存应用名称和追问prompt配置 */
  public setNameAndPromptConfig(data: {
    name?: string;
    prompt?: string;
    enable?: boolean;
  }): void {
    const curVal = this.nameAndPromptConfig$.getValue();
    this.nameAndPromptConfig$.next({
      ...curVal,
      ...data,
    });
  }

  public nameAndPromptConfigUpdate$(): Observable<any> {
    return this.nameAndPromptConfig$.asObservable();
  }

  public setVoiceConfig(data: IVoiceInteraction) {
    this.voiceConfig$.next(data);
  }

  public voiceConfigUpdate$() {
    return this.voiceConfig$.asObservable();
  }

  public getVoiceConfig() {
    return this.voiceConfig$.getValue();
  }

  /** 用于处理引用数据 **/
  public setReferenceConfig(data: ReferenceResponse) {
    this.referenceConfig$.next(data);
  }
  public referenceConfigUpdate$() {
    return this.referenceConfig$.asObservable();
  }

  /** 用于保存内容审核配置的值*/
  public setContentReviewConfig(data): void {
    const curVal = this.contentReviewConfig$.getValue();
    this.contentReviewConfig$.next({
      ...curVal,
      ...data,
    });
  }

  public contentReviewConfigUpdate$(): Observable<any> {
    return this.contentReviewConfig$.asObservable();
  }

  /** 设置添加好的触发器信息 */
  public setTrigger(trigger: {
    trigger_id: string;
    name: string;
    type: string;
    prompt: string;
    cron?: string;
    hook_url?: string;
  }) {
    let updatedTrigger: any = {
      trigger_id: trigger.trigger_id,
      name: trigger.name,
      type: trigger.type,
      prompt: trigger.prompt,
    };
    if (trigger.type === 'TIMER') {
      updatedTrigger.cron = trigger.cron ?? '';
    }
    if (trigger.type === 'EVENT') {
      updatedTrigger.hook_url = trigger.hook_url ?? '';
    }
    this.triggerAdded$.next(updatedTrigger);
  }

  public getTriggerUpdate$(): Observable<any> {
    return this.triggerAdded$.asObservable();
  }

  /** 记录是否点击触发器的添加按钮 */
  public setTriggerBtnClicked(isClicked: boolean): void {
    this.triggerBtnClicked$.next(isClicked);
  }

  public triggerBtnUpdate$(): Observable<boolean> {
    return this.triggerBtnClicked$.asObservable();
  }

  public setLatestPluginList(plugins: any[]): void {
    this.pluginList$.next([...plugins]);
  }

  public pluginListUpdate$() {
    return this.pluginList$.asObservable();
  }

  /** 记录是否点击调试insight */
  public setInsightBtnClicked(isClicked: boolean): void {
    this.isClickInsight$.next(isClicked);
  }

  public insightBtnUpdate$(): Observable<boolean> {
    return this.isClickInsight$.asObservable();
  }

  /** 记录当前调试会话的conversation_id */
  private currentConversationId = '';

  public setCurrentConversationId(id: string): void {
    this.currentConversationId = id;
  }

  public getCurrentConversationId(): string {
    return this.currentConversationId;
  }

  /** 记录发布的版本名称 */
  public setPreviewVersion(versionInfo: {
    version_id: string;
    version_name: string;
  }): void {
    this.versionId$.next(versionInfo);
  }

  public getPreviewVersion(): Observable<{
    version_id: string;
    version_name: string;
  }> {
    return this.versionId$.asObservable();
  }

  /** 记录点击还原版本对应的version_id */
  public setRollbackId(versionInfo): void {
    this.rollbackVersionId$.next(versionInfo);
  }

  public rollbackIdUpdate$(): Observable<any> {
    return this.rollbackVersionId$.asObservable();
  }

  /** 记录是否发布成功一个版本。用于在跳转到"发布管理"页面之前展示loading效果 */
  public setPublishStatus(status: string): void {
    this.isVersionPublished$.next(status);
  }

  public publishStatusUpdate$(): Observable<string> {
    return this.isVersionPublished$.asObservable();
  }

  /** 记录应用的status字段值 */
  public setAgentStatus(status: string): void {
    this.agentStatus$.next(status);
  }

  public agentStatusUpdate$(): Observable<string> {
    return this.agentStatus$.asObservable();
  }

  /** 存储应用或工作流的历史版本列表 */
  public setVersionList(list: any): void {
    this.historyVersionList$.next(list);
  }

  public versionListUpdate$(): Observable<any> {
    return this.historyVersionList$.asObservable();
  }

  /** 存储已绑定的插件和工作流列表 */
  public setPluginAndFlowList(newList: any) {
    const curList = this.pluginAndFlowList$.getValue();
    const latestList = { ...curList, ...newList };
    this.pluginAndFlowList$.next(latestList);
  }

  public pluginAndFlowListUpdate$(): Observable<any> {
    return this.pluginAndFlowList$.asObservable();
  }

  /** 记录是否存在一轮QA。用于判断长期记忆的生成按钮可点击 */
  public setHasQAFlag(flag: boolean): void {
    this.hasQAHistory$.next(flag);
  }

  public hasQAFlagUpdate$(): Observable<boolean> {
    return this.hasQAHistory$.asObservable();
  }

  /** 记录插件调测结果解析出来的响应参数 */
  public setPluginDebugRes(res: string) {
    this.pluginDebugRes$.next(res);
  }

  public pluginDebugResUpdate$() {
    return this.pluginDebugRes$.asObservable();
  }


  public addAgentInfo(info: any) {
    this.agentInfo$.next(info);
  }

  public refAgentUpdate$() {
    return this.agentInfo$.asObservable();
  }
  public showVarList(showVarListSubject$: Subject<boolean>) {
    showVarListSubject$.next(true);
  }
}
