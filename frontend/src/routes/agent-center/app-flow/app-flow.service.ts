import { ElementRef, Injectable } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Graph, Node, NodeProperties, Shape } from '@antv/x6';
import { I18nNamespace } from '@i18n';
import { MCPService } from '@services/agent-center/mcp.service';
import { CommonService } from '@services/common.service';
import { I18NextEagerPipe } from 'angular-i18next';
import i18next from 'i18next';
import { cloneDeep, isEqual, isNil, uniqWith } from 'lodash';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { environment } from 'src/environment/environment';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AgentConfigService } from '../agent-config.service';
import { reqSchemaStrMCPField } from '../app-mcp-service/utils';
import { reqSchemaStr2Field, resSchemaStr2Field } from '../app-plugin/utils';
import { DEFAULT_CODE } from '../constants/workflow-http-response-code.const';
import { isSystemTypeWithNames } from '../utils';
import {
  CellData,
  EdgeData,
  EHalfmodalType,
  IApiSetting,
  IConnection,
  IFlowConfigs,
  ILayouts,
  IMCPService,
  IModel,
  IModelParamInfo,
  IModeOfIntentNode,
  INameId,
  IPluginConfig,
  IRefWorkflows,
  IWorkflow,
  IWorkflowDetail,
  IWorkflowEdge,
  NodeData,
  Position,
  PublishedWorkflow,
  WorkFlowBriefInfo,
  WorkFlowType,
} from './app-flow.types';
import {
  appFlowOutput,
  FLOW_COLORS,
  getInitInputParamConfig,
  getInitInputParamRefConfig,
  getInitOutputParamConfig,
  NODE_SIZE,
  PORT_CONNECTED,
  PORT_CONNECTED_ATTR
} from './flow.const';
import {
  CANT_EMBEDDING_NODES,
  IAgentRepo,
  IAggregationNode,
  IBranchNode,
  ICardNode,
  ICodeNode,
  ICommentNode,
  IDataQueryNode,
  IEndNode,
  IExceptionNode,
  IFlowNode,
  IHttpRepo,
  IInputNode,
  IIntentContainerNode,
  IIntentNode,
  IKnowledgeRepo,
  ILLMNode,
  ILoopNode,
  ILTMNode,
  IMcpNode,
  IMessageNode,
  INodeType,
  INTERACTION_NODES,
  IParamExtractionNode,
  IPluginNode,
  IQANode,
  IQuesRewriteChain,
  IQuestionerNode,
  ISetVariableNode,
  ISqlNode,
  IStartNode,
  IViewNodeData,
  IWorkflowConfigs,
  IWorkflowField,
  IWorkflowFieldValue,
  IWorkflowNode,
  NodeInfo
} from './node.type';
import { FlowUtils, TargetMarker } from './utils/flow-utils';
import { MCP_SERVER } from '../types/common.types';

interface IStatusConfig {
  icon: string;
  status: string;
  text: string;
}

export interface INodeAction {
  type: 'delete' | 'copy' | 'update' | 'test' | 'connect_end';
  id: string;
}

interface IControlParams {
  pos: 'top' | 'right' | 'bottom' | 'left';
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  c: number;
}

type PageStatus = 'editable' | 'preview';

export interface ILoopInnerRalAction {
  loopNodeId: string;
  childNodeId: string;
  action: 'delete' | 'add';
}

export interface INodeHeightUpdate {
  id: string;
  height: number;
  nodeType?: INodeType;
  isExpand?: boolean;
  hasTips?: boolean;
}

export interface IExceptionPortUpdate {
  nodeId: string;
  operate: 'add' | 'remove';
}

type NodeHeightUpdateExtraInfo = Omit<INodeHeightUpdate, 'id' | 'height'>;

export interface IUpdateNodeData {
  nodeInfo: NodeInfo;
  successCb?: () => void;
  faildCb?: () => void;
}

@Injectable({
  providedIn: 'root',
})
export class AppFlowService {
  private readonly codeNode$ = new BehaviorSubject<object>({});

  private readonly nodeAction$ = new BehaviorSubject<INodeAction | null>(null);

  private readonly pageStatus$ = new BehaviorSubject<PageStatus>('editable');

  private modelList$ = new BehaviorSubject<IModel[]>([]);

  private nodeHeightMap$ = new BehaviorSubject<INodeHeightUpdate>(null);

  private flowConfigs$ = new BehaviorSubject<IFlowConfigs>(null);

  private isOpenGlbConf$ = new Subject<void>();

  // 存储trigger save的时间，用于展示"自动保存于xx::yy:zz"
  private readonly autoSaveTime$ = new BehaviorSubject<string>('');

  private silentUpdateNodeData$ = new BehaviorSubject<IUpdateNodeData>(null);

  private exceptionPort$ = new BehaviorSubject<IExceptionPortUpdate>(null);

  // 注册更新工作流的方法，在flow.component.ts中指定具体的实现，工作流相关组件主动调用工作流更新
  public updateFlowData: () => void;

  // 缩放系数
  private _localScale: number;
  public setLocalScale(val: number) {
    this._localScale = val;
  }
  public getLocalScale(): number {
    return this._localScale;
  }

  private runNodeIds: string[] = []; // 已运行的节点，判断前一个节点是否运行

  addRunNode(id: string) {
    this.runNodeIds.push(id);
  }

  initRunNode() {
    this.runNodeIds = [];
  }

  judgeRunNodeExist(id: string) {
    return this.runNodeIds.includes(id);
  }

  setExceptionPort(data: IExceptionPortUpdate) {
    this.exceptionPort$.next(data);
  }

  exceptionPortUpdate() {
    return this.exceptionPort$.asObservable();
  }

  setSilentUpdateNodeData(data: IUpdateNodeData) {
    this.silentUpdateNodeData$.next(data);
  }

  silentUpdateNodeDataUpdate() {
    return this.silentUpdateNodeData$.asObservable();
  }

  setNodeHeightMap(
    id: string,
    height: number,
    extra?: NodeHeightUpdateExtraInfo,
  ) {
    this.nodeHeightMap$.next({
      id,
      height,
      ...(extra ?? {}),
    });
  }

  setIsOpenGlbConf() {
    this.isOpenGlbConf$.next();
  }

  isOpenGlbConfUpdate() {
    return this.isOpenGlbConf$.asObservable();
  }

  nodeHeightMapUpdate() {
    return this.nodeHeightMap$.asObservable();
  }

  updateNodeHeight(
    el: ElementRef<HTMLDivElement>,
    id: string,
    extra?: NodeHeightUpdateExtraInfo,
  ) {
    const height = el?.nativeElement?.getBoundingClientRect()?.height;

    if (height) {
      this.setNodeHeightMap(id, height, extra);
    }
  }

  public readonly StatusMap = new Map<number | string, IStatusConfig>([
    [
      0,
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-development.svg'),
        status: 'DEVELOPMENT',
        text: 'developing',
      },
    ],
    [
      1,
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-done.svg'),
        status: 'PUBLISHED',
        text: 'submitted',
      },
    ],
    [
      2,
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-done.svg'),
        status: 'SUCCESS',
        text: 'success',
      },
    ],
    [
      3,
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-failed.svg'),
        status: 'FAIL',
        text: 'fail',
      },
    ],
  ]);

  public readonly AgentStatusMap = new Map<number | string, IStatusConfig>([
    [
      'draft',
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-development.svg'),
        status: 'DEVELOPMENT',
        text: 'developing',
      },
    ],
    [
      'published',
      {
        icon: cdnAssetUrl('assets/agent-center/icons/status-done.svg'),
        status: 'PUBLISHED',
        text: 'submitted',
      },
    ],
  ]);

  public readonly nodeDefaultNameMap = new Map<string, string>([
    ['LLM', i18next.t(`${I18nNamespace.AGENT_CENTER}:llm`)],
    ['Branch', i18next.t(`${I18nNamespace.AGENT_CENTER}:branch`)],
    [
      'IntentDetection',
      i18next.t(`${I18nNamespace.AGENT_CENTER}:intentDetection`),
    ],
    ['Code', i18next.t(`${I18nNamespace.AGENT_CENTER}:code`)],
    [
      'ComplexIntentDetection',
      i18next.t(`${I18nNamespace.AGENT_CENTER}:complexIntentDetection`),
    ],
    ['Loop', i18next.t(`${I18nNamespace.AGENT_CENTER}:Loop`)],
    ['Http', i18next.t(`${I18nNamespace.AGENT_CENTER}:http`)],
    ['Card', i18next.t(`${I18nNamespace.AGENT_CENTER}:Card`)],
    ['Message', i18next.t(`${I18nNamespace.AGENT_CENTER}:message`)],
    ['Questioner', i18next.t(`${I18nNamespace.AGENT_CENTER}:questioner`)],
    ['Input', i18next.t(`${I18nNamespace.AGENT_CENTER}:input`)],
    ['QA', i18next.t(`${I18nNamespace.AGENT_CENTER}:QA`)],
    [
      'StructuredMessagesException',
      i18next.t(`${I18nNamespace.AGENT_CENTER}:exception`),
    ],
    [
      'ParamExtraction',
      i18next.t(`${I18nNamespace.AGENT_CENTER}:ParamExtraction`),
    ],
    ['SetVariable', i18next.t(`${I18nNamespace.AGENT_CENTER}:SetVariable`)],
    ['LTM', i18next.t(`${I18nNamespace.AGENT_CENTER}:LTM`)],
    ['Aggregation', i18next.t(`${I18nNamespace.AGENT_CENTER}:aggregation`)],
    [
      'KnowledgeRepo',
      i18next.t(`${I18nNamespace.AGENT_CENTER}:knowledge_repo`),
    ],
    ['Sql', i18next.t(`${I18nNamespace.AGENT_CENTER}:database`)],
    ['DataQuery', i18next.t('appflowservice_1')],
    ['StreamTransform', i18next.t(`${I18nNamespace.AGENT_CENTER}:stream_transform`)],
  ]);

  public readonly nodeConstantNameMap = new Map<string, string>([
    ['End', i18next.t(`${I18nNamespace.AGENT_CENTER}:end`)],
    ['Start', i18next.t(`${I18nNamespace.AGENT_CENTER}:start`)],
    ['LoopInput', i18next.t(`${I18nNamespace.AGENT_CENTER}:loop_input`)],
    ['LoopOutput', i18next.t(`${I18nNamespace.AGENT_CENTER}:loop_output`)],
  ]);

  private readonly graph$ = new BehaviorSubject<Graph>(null);

  private readonly loopInnerRelationAction$ =
    new BehaviorSubject<ILoopInnerRalAction>(null);

  private readonly apiOriginInfo = new Map<string, INameId>();

  private readonly runSettings$ = new BehaviorSubject<IApiSetting[]>([]);

  /** version信息，作为运行工作流接口的入参 */
  private readonly versionInfo$ = new BehaviorSubject<number>(0);

  /** plugin_configs信息，作为运行工作流接口的入参 */
  private readonly pluginConfigs$ = new BehaviorSubject<IPluginConfig[]>([]);

  /** 表示工作流整体运行状态，成功或失败 */
  private readonly workflowStatus$ = new BehaviorSubject<string>('');

  // 存储创建的触发器信息
  private readonly triggerAdded$ = new BehaviorSubject<any>({
    trigger_id: '',
    cron: '',
    hook_url: '',
    invocation: '',
    name: '',
    type: '',
  });

  /** 自动保存于xx:yy:zz */
  public setAutoSaveTime(updateTime: string): void {
    this.autoSaveTime$.next(updateTime);
  }

  /** 设置添加好的触发器信息 */
  public setTrigger(trigger: {
    trigger_id: string;
    name: string;
    type: string;
    prompt: string;
    cron?: string;
    hook_url?: string;
    invocation?: string;
  }) {
    let updatedTrigger: any = {
      trigger_id: trigger.trigger_id,
      type: trigger.type,
      prompt: trigger.prompt,
      invocation: trigger.invocation,
      name: trigger.name,
    };
    if (trigger.type === 'TIMER') {
      updatedTrigger.cron = trigger.cron ?? '';
    }
    if (trigger.type === 'EVENT') {
      updatedTrigger.hook_url = trigger.hook_url ?? '';
    }
    this.triggerAdded$.next(updatedTrigger);
  }

  /** 是否点击【试运行】按钮。若点击，【开始运行】按钮恢复可编辑状态 */
  private readonly isRunBtnClicked$ = new BehaviorSubject<boolean>(false);

  /** 保证画布上只出现一类抽屉 */
  private readonly isNodeConfigOpen$ = new BehaviorSubject<EHalfmodalType>(
    EHalfmodalType.DEFAULT,
  );

  /** 是否点击开始节点配置弹窗的确定按钮。若点击，则更新startNodeParams */
  private readonly isStartNodeBtnClicked$ = new BehaviorSubject<boolean>(false);

  private readonly workflowType$ = new BehaviorSubject<WorkFlowType>('chat');

  /** 工作流校验的返回结果 */
  private validateRes$ = new BehaviorSubject<any>({
    success: true,
    errors: [],
  });

  /** 工作流中，资源节点是否升级新版本的结果 */
  private isResNodesUpdated$ = new BehaviorSubject<any>([]);

  /** 子工作流节点升级新版本调用put接口的请求体 */
  private childFlowPutBody$ = new BehaviorSubject<any>({});

  // 卡片更新
  private cardUpdate$ = new Subject<any>();

  /** 对话型工作流中，存储多轮answer的输入节点表单 */
  private answerInputForm$ = new BehaviorSubject<FormGroup>(this.fb.group({}));

  /** 传递工作流运行的流式数据。用于控制画布节点的运行状态，运行中/成功/失败 */
  private readonly nodeStatusStream$ = new BehaviorSubject<any>({});

  /** 传递节点状态修改连线动效*/
  private readonly edgeStatusStream$ = new BehaviorSubject<any>({});

  /** 表示点击调用链的哪个节点node_id */
  private readonly nodeIdClicked$ = new BehaviorSubject<string>('');

  /**选中节点*/
  private readonly nodeIdSelected$ = new BehaviorSubject<string[]>([]);

  /** 存储工作流的基础信息 */
  private readonly flowInfo$ = new BehaviorSubject<WorkFlowBriefInfo>({
    name: '',
    avatar: '',
  });

  /** 是否更新试运行抽屉中的插件鉴权参数。只有当删除或新增插件节点时 */
  private readonly isRefreshConfig$ = new BehaviorSubject<boolean>(false);

  private readonly isAddPluginList$ = new BehaviorSubject<any[]>([]);
  /** 不同意图节点对应的模式 */
  private readonly modeOfIntentNode$ = new BehaviorSubject<IModeOfIntentNode[]>(
    [],
  );

  /** 存储试运行中上传的文件信息列表 */
  private readonly fileList$ = new BehaviorSubject<any[]>([]);

  /** 存储从指定应用的引用资源列表接口中查到的数据 */
  private readonly refResources$ = new BehaviorSubject<IRefWorkflows[]>([]);

  /** 存储从指定应用的引用资源列表接口中查到的数据 */
  private readonly saveFlow$ = new BehaviorSubject<any>({});
  /** 存储从指定应用的引用资源列表接口中查到的数据 */
  private readonly nodeModalClose$ = new BehaviorSubject<any>({});

  // output修改
  private readonly refChange$ = new BehaviorSubject<any>({});

  /** 记录容器节点升级新版本后的dsl数据 */
  private readonly updateContainerDsl$ = new BehaviorSubject<
    IIntentContainerNode | IAgentRepo | null
  >(null);

  // 单步调试事件
  private readonly nodeTestInfoAction$ =
    new BehaviorSubject<INodeAction | null>(null);
  // 单步调试结果
  public nodeTestInfoMap = new Map();
  private readonly validateWorkflowList$ = new BehaviorSubject<any>([]);
  //记录修改节点名称事件，循环节点未更新
  private readonly nodeNameChange$ = new BehaviorSubject<any>(null);

  constructor(
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private readonly api: MCPService,
    private configServ: AgentConfigService,
    private commonService: CommonService,
  ) {}

  public setWorkflowType(type: WorkFlowType) {
    this.workflowType$.next(type);
  }

  get codeOptions() {
    return this.configServ.getConfigs().code_env_options;
  }

  public getWorkflowType() {
    return this.workflowType$.getValue();
  }

  public setGraph(graph: Graph) {
    this.graph$.next(graph);
  }

  public getGraph() {
    return this.graph$.getValue();
  }

  public setLoopInnerRal(action: ILoopInnerRalAction) {
    this.loopInnerRelationAction$.next(action);
  }

  public loopInnerRalUpdate() {
    return this.loopInnerRelationAction$.asObservable();
  }

  public setNodeAction(action: INodeAction): void {
    this.nodeAction$.next(action);
  }

  public setFlowConfigs(conf: IFlowConfigs) {
    this.flowConfigs$.next(conf);
  }

  public getFlowConfigs() {
    return this.flowConfigs$.getValue();
  }

  public nodeActionUpdate$(): Observable<INodeAction | null> {
    return this.nodeAction$.asObservable();
  }

  // 调试弹窗并回显结果
  public setNodeTestInfoAction(action: any): void {
    this.nodeTestInfoAction$.next(action);
  }

  public nodeTestInfoActionUpdate$(): Observable<any> {
    return this.nodeTestInfoAction$.asObservable();
  }

  public setSaveNodeTestInfo(ref: any): void {
    if (ref) {
      const { id, runInfo } = ref;
      if (id) {
        this.nodeTestInfoMap.set(id, runInfo ?? null);
      }
    } else {
      this.nodeTestInfoMap.clear();
    }
  }

  public getNodeTestInfo(id): any {
    return this.nodeTestInfoMap.get(id);
  }

  public setModelList(modeList: IModel[]) {
    this.modelList$.next(modeList);
  }

  public getTriggerUpdate$(): Observable<any> {
    return this.triggerAdded$.asObservable();
  }

  public getRunSettings(): IApiSetting[] {
    return this.runSettings$.getValue();
  }

  public setRunSettings(settings: IApiSetting[]): void {
    this.runSettings$.next(settings);
  }

  public getVersionInfo(): number {
    return this.versionInfo$.getValue();
  }

  /** 设置version信息 */
  public setVersionInfo(updated_on: number): void {
    this.versionInfo$.next(updated_on);
  }

  public versionInfoUpdate$(): Observable<number> {
    return this.versionInfo$.asObservable();
  }

  /** 设置plugin_configs信息 */
  public setPluginConfig(configs: IPluginConfig[]): void {
    this.pluginConfigs$.next(configs);
  }

  public pluginConfigUpdate$(): Observable<IPluginConfig[]> {
    return this.pluginConfigs$.asObservable();
  }

  /** 设置工作流的整体运行状态，成功或失败 */
  public setFlowStatus(status: string): void {
    this.workflowStatus$.next(status);
  }

  public flowStatusUpdate$(): Observable<string> {
    return this.workflowStatus$.asObservable();
  }

  /** 设置【试运行】按钮是否点击 */
  public setRunBtnClicked(isClicked: boolean): void {
    this.isRunBtnClicked$.next(isClicked);
  }

  public runBtnClickedUpdate$(): Observable<boolean> {
    return this.isRunBtnClicked$.asObservable();
  }

  /** 记录画布上出现的半屏抽屉类型 */
  public setNodeClicked(modalType: EHalfmodalType): void {
    this.isNodeConfigOpen$.next(modalType);
  }

  public getNodeClicked() {
    return this.isNodeConfigOpen$.getValue();
  }

  public nodeClickedUpdate$(): Observable<EHalfmodalType> {
    return this.isNodeConfigOpen$.asObservable();
  }

  /** 记录开始节点配置弹窗的确定按钮是否被点击 */
  public setStartNodeBtnClicked(isClicked: boolean): void {
    this.isStartNodeBtnClicked$.next(isClicked);
  }

  public startNodeBtnUpdate$(): Observable<boolean> {
    return this.isStartNodeBtnClicked$.asObservable();
  }

  /** 记录工作流校验的结果 */
  public setFlowErrors(result: any): void {
    this.validateRes$.next(result);
  }

  public flowErrorsUpdate$(): Observable<any> {
    return this.validateRes$.asObservable();
  }

  /** 记录资源节点列表是否升级新版本的结果 */
  public setResNodes(childFlows: any): void {
    this.isResNodesUpdated$.next(childFlows);
  }

  public resNodesUpdate(): Observable<any> {
    return this.isResNodesUpdated$.asObservable();
  }

  public getResNodes() {
    return this.isResNodesUpdated$.getValue();
  }

  /** 对话型工作流中，存储多轮answer的输入节点表单列表 */
  public setAnswerInputForm(form: any): void {
    this.answerInputForm$.next(form);
  }

  public getAnswerInputForm(): any {
    return this.answerInputForm$.getValue();
  }

  /** 记录子工作流节点升级新版本调用put接口的请求体 */
  public setChildFlowPutBody(body: any): void {
    this.childFlowPutBody$.next(body);
  }

  public childFlowPutBodyUpdate$(): Observable<any> {
    return this.childFlowPutBody$.asObservable();
  }

  // 卡片更新，用新版本更新卡片部分
  public setCardUpdate(body: any): void {
    this.cardUpdate$.next(body);
  }

  public getCardUpdate$(): Observable<any> {
    return this.cardUpdate$.asObservable();
  }

  /** 传递工作流运行的流式数据 */
  public setTokenData(token: any): void {
    this.nodeStatusStream$.next(token);
  }

  public tokenDataUpdate$(): Observable<any> {
    return this.nodeStatusStream$.asObservable();
  }

  /** 传递工作流运行的流式数据 */
  public setEdgeStatus(token: any): void {
    this.edgeStatusStream$.next(token);
  }

  public edgeStatusUpdate$(): Observable<any> {
    return this.edgeStatusStream$.asObservable();
  }

  /** 记录点击调用链的哪个节点 */
  public setNodeIdClicked(node_id: string): void {
    this.nodeIdClicked$.next(node_id);
  }

  public nodeIdClickedUpdate$(): Observable<string> {
    return this.nodeIdClicked$.asObservable();
  }

  public setNodeIdSelected(node_ids: string[]): void {
    this.nodeIdSelected$.next(node_ids);
  }

  public nodeIdSelectedUpdate$(): Observable<string[]> {
    return this.nodeIdSelected$.asObservable();
  }

  /** 存储工作流的基础信息，图标和名称 */
  public setFlowInfo(info: WorkFlowBriefInfo): void {
    this.flowInfo$.next(info);
  }

  public flowInfoUpdate$(): Observable<WorkFlowBriefInfo> {
    return this.flowInfo$.asObservable();
  }

  /** 是否更新试运行抽屉中的插件鉴权参数。只有当删除或新增插件节点时 */
  public setRefreshFlag(isRefresh: boolean): void {
    this.isRefreshConfig$.next(isRefresh);
  }

  public refreshFlagUpdate$(): Observable<boolean> {
    return this.isRefreshConfig$.asObservable();
  }

  public setPluginList(pluginList: any): void {
    this.isAddPluginList$.next(pluginList);
  }

  public refresPluginListUpdate$(): Observable<any> {
    return this.isAddPluginList$.asObservable();
  }

  public setNodeSaveMonitor(node: any): void {
    this.saveFlow$.next(node);
  }

  public nodeSaveMonitor$(): Observable<any> {
    return this.saveFlow$.asObservable();
  }

  public setNodeModalCloseMonitor(node: any): void {
    this.nodeModalClose$.next(node);
  }

  public nodeModalCloseMonitor$(): Observable<any> {
    return this.nodeModalClose$.asObservable();
  }

  public setValidateWorkflowList(node: any): void {
    this.validateWorkflowList$.next(node);
  }

  public updataValidateWorkflowList(): Observable<any> {
    return this.validateWorkflowList$.asObservable();
  }

  public setNodeRefChange(node: any): void {
    this.refChange$.next(node);
  }

  public nodeRefChange$(): Observable<any> {
    return this.refChange$.asObservable();
  }

  public setNodeNameChange(info: any): void {
    this.nodeNameChange$.next(info);
  }

  public nodeNameChange(): Observable<any> {
    return this.nodeNameChange$.asObservable();
  }

  // 试运行校验错误
  public testRunVerificationError = false;

  /** 记录不同意图节点对应的模式 */
  public setModeOfIntentNode(newIntentNode: IModeOfIntentNode): void {
    const curModes = this.modeOfIntentNode$.getValue();
    const isExistingItem = curModes.findIndex(
      (item) => item.node_id === newIntentNode.node_id,
    );

    if (isExistingItem !== -1) {
      // 更新已有意图节点的模式
      curModes[isExistingItem] = newIntentNode;
    } else {
      curModes.push(newIntentNode);
    }
    this.modeOfIntentNode$.next([...curModes]);
  }

  public modeOfIntentNodeUpdate$(): Observable<IModeOfIntentNode[]> {
    return this.modeOfIntentNode$.asObservable();
  }

  public clearModeOfIntents() {
    this.modeOfIntentNode$.next([]);
  }

  /** 存储试运行中上传的文件列表 */
  public setFileList(file: any): void {
    const curList = this.fileList$.getValue();

    // 针对已上传文件的参数列表，更新绑定的文件信息
    const updatedList = curList.map((item) =>
      item.name === file.name ? file : item,
    );
    // 针对未上传文件的参数列表，存储首次绑定的文件信息
    if (!curList.some((item) => item.name === file.name)) {
      updatedList.push(file);
    }

    this.fileList$.next(updatedList);
  }

  public fileListUpdate$(): Observable<any[]> {
    return this.fileList$.asObservable();
  }

  public resetFileList() {
    this.fileList$.next([]);
  }

  /** 存储从指定应用的引用资源列表接口中返回的数据 */
  public setAppRefs(list: IRefWorkflows[]) {
    this.refResources$.next(list);
  }

  public getAppRefs() {
    return this.refResources$.getValue();
  }

  public appRefsUpdate(): Observable<IRefWorkflows[]> {
    return this.refResources$.asObservable();
  }

  /** 记录容器节点升级新版本后的dsl数据 */
  public setContainerDsl(branches: IIntentContainerNode | IAgentRepo) {
    this.updateContainerDsl$.next(branches);
  }

  public containerDslUpdate$(): Observable<IIntentContainerNode | IAgentRepo> {
    return this.updateContainerDsl$.asObservable();
  }

  public setApiOriginInfo(apiInfo: INameId): void {
    if (this.apiOriginInfo.has(apiInfo.id)) {
      return;
    }

    this.apiOriginInfo.set(apiInfo.id, apiInfo);
  }

  public setCodeNode(obj: object) {
    this.codeNode$.next(obj);
  }

  public updateCodeNode() {
    return this.codeNode$.asObservable();
  }

  public getCodeNode() {
    return this.codeNode$.getValue();
  }

  public getApiOriginInfoByIds(ids: string[]): INameId[] {
    const info: INameId[] = [];

    // deduplicate
    Array.from(new Set(ids)).forEach((id) => {
      const apiInfo = this.apiOriginInfo.get(id);
      if (apiInfo) {
        info.push(apiInfo);
      }
    });

    return info;
  }

  public getGraphApiCmps(graph: Graph | null): INameId[] {
    if (!graph) {
      return [];
    }

    // only graph visible api nodes are processed
    // planner will be added later
    const nodes = graph.getNodes();
    const apiNodesData = (
      nodes
        .map((node) => (node.getData() as IViewNodeData).ngArguments.nodeInfo)
        .filter((node) => node.type === 'Plugin') as IPluginNode[]
    ).map((node) => {
      return {
        id: node.configs.id,
        name: node.name,
      };
    });

    return apiNodesData;
  }

  // 提供订阅的方法
  public modelListUpdate(): Observable<IModel[]> {
    return this.modelList$.asObservable();
  }

  public getModelList(): IModel[] {
    return this.modelList$.getValue();
  }

  public getModelParamsInfoMap(): Map<string, IModelParamInfo> {
    return new Map([
      [
        'temperature',
        {
          name: 'temperature',
          value: 0,
          min: 0,
          step: 0.1,
          default: 0.5,
          max: 1,
          mid: 0.5,
        },
      ],
      [
        'top_p',
        {
          name: 'top_p',
          value: 0.1,
          min: 0.1,
          max: 1,
          step: 0.1,
          default: 0.5,
          mid: 0.5,
        },
      ],
      [
        'max_tokens',
        {
          name: 'max_tokens',
          value: 2048,
          min: 0,
          step: 1,
          default: 2048,
          max: 4096,
          mid: 2048,
        },
      ],
    ]);
  }

  public getInitLLMChainNodeData(): ILLMNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('llm'),
      type: 'LLM',
      inputs: [
        {
          name: 'query',
          description: '',
          required: true,
          type: 'string',
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          source: 'user',
        },
      ],
      outputs: [
        {
          name: 'raw_output',
          description: this.i18n.transform('original_output'),
          required: true,
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          type: 'string',
          source: 'user',
        },
      ],
      configs: {
        isDefaultName: true,
        top_p: 0.5,
        template_content: '{{query}}',
        temperature: 0.5,
        model: {
          model_name: '',
          model_type: '',
          model_deployment_id: '',
          model_id: '',
        },
        history_size: 3,
        max_tokens: null,
        enable_history: false,
        format_instruction: '',
        stream: true,
        response_format: 'text',
        system_prompt: '',
      },
    };
  }

  public getInitBranchNodeData(): IBranchNode {
    return {
      id: `node_${Date.now()}`,
      name: this.i18n.transform('branch'),
      type: 'Branch',
      branches: [
        {
          id: 'if',
          configs: {
            logic: 'and',
            conditions: [
              {
                left: {
                  description: '',
                  name: '',
                  required: false,
                  value: {
                    type: 'ref',
                    content: {
                      ref_node_id: '',
                      ref_var_name: '',
                      source: '',
                    },
                    hint: '',
                  },
                  source: 'user',
                },
                operator: 'eq',
                right: {
                  description: '',
                  name: '',
                  required: false,
                  value: {
                    type: 'literal',
                    content: '',
                    hint: '',
                  },
                  source: 'user',
                },
              },
            ],
          },
        },
        {
          id: 'default',
        },
      ],
      configs: {
        isDefaultName: true,
      },
    };
  }

  public getInitCodeNodeData(): ICodeNode {
    const id = `node_${Date.now()}`;
    let codeOptions = this.codeOptions;
    return {
      id,
      type: 'Code',
      name: this.i18n.transform('code'),
      outputs: [getInitOutputParamConfig()],
      inputs: [getInitInputParamConfig()],
      configs: {
        code: DEFAULT_CODE,
        isDefaultName: true,
        exec_env: codeOptions?.length > 0 ? codeOptions[0] : 'fg', //默认值区取数组的第一个
      },
    };
  }

  public getInitChildFlowData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      name: this.i18n.transform('workflow'),
      id,
      inputs: [getInitInputParamConfig()],
      outputs: [getInitOutputParamConfig()],
      type: 'Workflow',
      isAction: true,
    };
  }

  public getInitMcpServiceData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('mcp'),
      type: 'Mcp',
      isAction: true,
      inputs: [getInitInputParamConfig()],
      outputs: [getInitOutputParamConfig()],
    };
  }

  public getInitQuestionerNodeData(): IQuestionerNode {
    const rewrite_chain: IQuesRewriteChain[] = [];
    const id = `node_${Date.now()}`;

    if (environment.envType === 'poc') {
      rewrite_chain.push({
        type: 'rewrite_api',
        enabled: false,
        index: 1,
        args: { url: '' },
      });
    }

    return {
      id,
      name: this.nodeDefaultNameMap.get('Questioner'),
      type: 'Questioner',
      inputs: [getInitInputParamConfig()],
      configs: {
        isDefaultName: true,
        mode: 'effect',
        model: {
          model_name: '',
          model_type: '',
          model_deployment_id: '',
          model_id: '',
        },
        top_p: 0.5,
        temperature: 0.2,
        extra_prompt_for_fields_extraction: '',
        question_content: '',
        with_chat_history: false,
        extract_fields_from_response: true,
        max_response: 10,
        rewrite_chain,
        example_content: '',
        allow_node_break: false,
        allow_node_confirm: false,
        auto_ask_template: '',
        template_anthropomorphic: false,
        enum_visible: false,
        max_tokens: null,
      },
      outputs: [
        {
          name: 'USER_RESPONSE',
          cn_name: '',
          description: this.i18n.transform(
            'intentDetection.outputs_user_response_description',
          ),
          required: false,
          type: 'string',
          value: { type: 'literal', content: '', hint: '', default: '' },
          source: 'user',
          validator: [],
          reflection: false,
        },
        {
          name: 'STATUS',
          cn_name: '',
          description: this.i18n.transform(
            'intentDetection.outputs_status_description',
          ),
          required: false,
          type: 'integer',
          value: {
            type: 'literal',
            content: '',
            hint: '',
            default: '',
          },
          source: 'user',
          validator: [],
          reflection: false,
        },
      ],
    };
  }

  public getInitIntentNodeData(): IIntentNode {
    const id = `node_${Date.now()}`;
    return {
      id,
      name: this.nodeDefaultNameMap.get('IntentDetection'),
      type: 'IntentDetection',
      inputs: [
        {
          name: 'input',
          description: '',
          required: false,
          type: 'string',
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          source: 'system',
        },
      ],
      configs: {
        isDefaultName: true,
        prompt: '',
        llm: {
          temperature: 0.5,
          top_p: 0.5,
          max_tokens: null,
          model: {
            model_name: '',
            model_type: '',
            model_deployment_id: '',
            model_id: '',
          },
        },
        chat_history_max_turn: 0,
      },
      outputs: [
        {
          name: 'classification_id',
          description: this.i18n.transform(
            'intentDetection.outputs_id_description',
          ),
          type: 'integer',
          required: true,
          value: {
            type: 'generated',
            content: null,
            hint: '',
          },
          source: 'system',
        },
        {
          name: 'name',
          description: this.i18n.transform(
            'intentDetection.outputs_name_description',
          ),
          type: 'string',
          required: true,
          value: {
            type: 'generated',
            content: null,
            hint: '',
          },
          source: 'system',
        },
        {
          name: 'result',
          description: this.i18n.transform(
            'intentDetection.outputs_result_description',
          ),
          required: false,
          type: 'string',
          value: { type: 'generated', content: '', hint: '' },
          source: 'system',
        },
        {
          name: 'reason',
          type: 'string',
          required: true,
          source: 'system',
          value: { type: 'generated', content: null, hint: '' },
        },
      ],
      branches: [
        {
          id: 'branch_0',
          configs: {
            category: this.i18n.transform('uncertain_other_intentions'),
          },
        },
        {
          id: 'branch_1',
          configs: { category: '' },
        },
      ],
    };
  }

  public getInitComplexIntentDetectionNodeData(): IIntentNode {
    const id = `node_${Date.now()}`;
    return {
      id,
      name: this.i18n.transform('complexIntentDetection'),
      type: 'ComplexIntentDetection',
      inputs: [
        {
          name: 'input',
          description: '',
          required: false,
          type: 'string',
          value: { type: 'literal', content: '', hint: '' },
          source: 'system',
        },
      ],
      outputs: [
        {
          name: 'classification_id',
          description: this.i18n.transform(
            'intentDetection.outputs_id_description',
          ),
          required: true,
          type: 'integer',
          value: { type: 'generated', content: null, hint: '' },
          source: 'system',
        },
        {
          name: 'name',
          description: this.i18n.transform(
            'intentDetection.outputs_name_description',
          ),
          type: 'string',
          value: {
            type: 'generated',
            content: null,
            hint: '',
          },
          source: 'system',
          required: true,
        },
        {
          name: 'result',
          description: this.i18n.transform(
            'intentDetection.outputs_result_description',
          ),
          required: false,
          type: 'string',
          value: { type: 'generated', content: '', hint: '' },
          source: 'system',
        },
        {
          name: 'reason',
          type: 'string',
          required: true,
          source: 'system',
          value: { type: 'generated', content: null, hint: '' },
        },
      ],
      configs: {
        isDefaultName: true,
        prompt: '',
        chat_history_max_turn: 0,
        llm: {
          temperature: 0.5,
          top_p: 0.5,
          max_tokens: null,
          model: {
            model_name: '',
            model_type: '',
            model_deployment_id: '',
            model_id: '',
          },
        },
      },
      branches: [],
    };
  }

  public getInitMessageNodeData(): IMessageNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Message'),
      inputs: [getInitInputParamConfig()],
      type: 'Message',
      outputs: [
        {
          name: 'result',
          description: this.i18n.transform('message_output'),
          required: false,
          type: 'string',
          value: {
            type: 'generated',
            content: '',
            hint: '',
          },
          source: 'system',
        },
      ],
      configs: {
        isDefaultName: true,
        template: '',
        enable_history: true,
      },
    };
  }

  public getInitStreamTransformNodeData(): IMessageNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('StreamTransform'),
      inputs: [getInitInputParamRefConfig()],
      type: 'StreamTransform',
      outputs: [
        {
          name: 'result',
          description: this.i18n.transform('message_output'),
          required: false,
          type: 'string',
          value: {
            type: 'generated',
            content: '',
            hint: '',
          },
          source: 'system',
        },
      ],
      configs: {
        isDefaultName: true,
        template: '',
        enable_history: true,
      },
    };
  }


  public getInitKnowledgeRepoNodeData(): IKnowledgeRepo {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('KnowledgeRepo'),
      type: 'KnowledgeRepo',
      inputs: [
        {
          name: 'query',
          type: 'string',
          description: this.i18n.transform('retrieve_query'),
          required: true,
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          source: 'user',
        },
      ],
      outputs: [
        {
          name: 'output_list',
          type: 'array',
          description: this.i18n.transform('query_result_list'),
          required: true,
          source: 'user',
          schema: {
            name: '',
            schema: [
              {
                name: 'document_name',
                required: true,
                description: this.i18n.transform('file_name'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'subtitle',
                required: true,
                description: this.i18n.transform('subheading_section_info'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'content',
                required: true,
                description: this.i18n.transform('retrieve_content'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'score',
                required: true,
                description: this.i18n.transform('match_score'),
                type: 'number',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'knowledge_base_id',
                required: true,
                description: this.i18n.transform('knowledge_id'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'file_id',
                required: true,
                description: this.i18n.transform('file_id'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
              {
                name: 'knowledge_base_type',
                required: true,
                description: this.i18n.transform('kb_type'),
                type: 'string',
                value: this.commonGetOutputValue() as any,
                source: 'user',
              },
            ],
            type: 'object',
          },
          reflection: false,
          value: this.commonGetOutputValue() as any,
        },
      ],
      configs: {
        isDefaultName: true,
        repos: [],
        faq_threshold: 0.9,
        top_k: 3,
        recall_threshold: 0.5,
        search_mode: 'doc',
        need_extras_faq_search: false,
        extra_params: [],
      },
    };
  }

  private commonGetOutputValue() {
    return {
      default: '',
      type: 'generated',
      hint: '',
      content: '',
    };
  }

  public getInitAggregationNodeData(): IAggregationNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Aggregation'),
      type: 'Aggregation',
      inputs: [],
      configs: {
        isDefaultName: true,
        mode: 'first-non-null',
        groups: {},
      },
      outputs: [],
    };
  }

  public getInitInputNodeData(): IInputNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Input'),
      type: 'Input',
      outputs: [],
      inputs: [{ ...getInitInputParamConfig() }],
      configs: {
        isDefaultName: true,
      },
    };
  }

  public getInitLoopNodeData(): ILoopNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Loop'),
      type: 'Loop',
      inputs: [],
      configs: {
        loop_type: 'numLoop',
        loop_body: [],
        isDefaultName: true,
      },
      outputs: [],
    };
  }

  public getInitLTMNodeData(): ILTMNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('LTM'),
      type: 'LTM',
      inputs: [
        {
          name: 'query',
          type: 'string',
          description: this.i18n.transform('user_input'),
          required: true,
          source: 'user',
          reflection: false,
          value: {
            type: 'ref',
            content: {
              ref_node_id: 'node_start',
              ref_var_name: 'query',
              source: 'system',
            },
            hint: '',
          },
        },
      ],
      configs: {
        isDefaultName: true,
        model: {
          model_name: '',
          model_type: '',
          model_deployment_id: '',
          model_id: '',
        },
        top_p: 0.5,
        temperature: 0.2,
        top_k: 3,
        recall_threshold: 0.8,
        output_mode: 'summary',
      },
      outputs: [appFlowOutput as any],
    };
  }

  public getInitSetVariableNodeData(): ISetVariableNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('SetVariable'),
      type: 'SetVariable',
      inputs: [],
      configs: {
        isDefaultName: true,
        settings: [],
      },
    };
  }

  public getInitLoopIONodesPosition(loopCell: Node<NodeProperties>) {
    const { x, y } = loopCell.getPosition();
    const { width, height } = loopCell.size();

    const offset = 30;
    const leftNodeX = x + offset;
    const rightNodeX = x + width - offset - NODE_SIZE.width / 2;
    const midY = y + height / 2;

    return {
      input: {
        x: leftNodeX,
        y: midY - 30,
      },
      output: {
        x: rightNodeX,
        y: midY - 30,
      },
    };
  }

  public getInitActionPluginNodeData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('plugin'),
      type: 'Plugin',
      inputs: [],
      outputs: [],
      isAction: true,
    };
  }

  public getInitDataAcquisitionNodeData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('data_obtain'),
      type: 'DataAcquisition',
      isAction: true,
      inputs: [getInitInputParamConfig()],
      outputs: [getInitOutputParamConfig()],
    };
  }

  public getInitDataProcessServiceData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      id,
      isAction: true,
      name: this.i18n.transform('data_process'),
      type: 'DataProcess',
      inputs: [getInitInputParamConfig()],
      outputs: [getInitOutputParamConfig()],
    };
  }

  public getInitDataSynthesisServiceData(): Omit<IPluginNode, 'configs'> {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('data_synthesis'),
      type: 'DataSynthesis',
      inputs: [getInitInputParamConfig()],
      outputs: [getInitOutputParamConfig()],
      isAction: true,
    };
  }

  public async getInitDataProcessNodeData(
    service: IMCPService,
    type,
  ): Promise<IMcpNode> {
    const id = `node_${Date.now()}`;
    const { server_id, name, desc, name_en, description_en, description } =
      service as any;
    const mcpId = service.id;
    const mcpInfo = service.mcpInfo;
    let tool_name = '';
    let test_name = '';
    let input_schema = '';
    let output_schema = '';
    let outputs: IWorkflowField[] = [];
    let inputs: IWorkflowField[] = [];
    if (mcpInfo && mcpInfo.tools && Array.isArray(mcpInfo.tools)) {
      const tools = mcpInfo.tools;
      tool_name = tools.length ? tools[0].name : '';
      input_schema = tools.length ? tools[0].input : '';
      output_schema = tools.length ? tools[0].output : '';
      test_name = tools.length ? tools[0].name : '';
      inputs = reqSchemaStrMCPField(input_schema);
      outputs = reqSchemaStrMCPField(output_schema);
    }
    return {
      id,
      name,
      type: type,
      inputs,
      outputs,
      configs: {
        id: mcpId,
        name,
        name_en,
        tool_name,
        original_info: {
          name,
          name_en,
          description: description_en || description,
        },
        valid: true,
      },
    };
  }

  public getInitHttpNodeData(): IHttpRepo {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Http'),
      type: 'Http',
      inputs: [
        {
          name: 'query',
          type: 'object',
          description: this.i18n.transform('http_node_request_parameters'),
          required: true,
          source: 'pre_defined',
          value: {
            type: 'nested',
            hint: '',
            content: null,
            default: '',
          },
          schema: [
            {
              name: '',
              type: 'string',
              description: '',
              source: 'pre_defined',
              required: true,
              value: {
                type: 'ref',
                content: {
                  ref_node_id: '',
                  ref_var_name: '',
                  source: '',
                },
                hint: '',
              },
            },
          ],
        },
        {
          name: 'headers',
          type: 'object',
          description: this.i18n.transform(
            'http_node_header_configuration_parameters',
          ),
          required: true,
          source: 'pre_defined',
          value: {
            type: 'nested',
            content: null,
            hint: '',
            default: '',
          },
          schema: [
            {
              name: '',
              type: 'string',
              description: '',
              required: true,
              value: {
                type: 'ref',
                content: {
                  ref_node_id: '',
                  ref_var_name: '',
                  source: '',
                },
                hint: '',
              },
              source: 'pre_defined',
            },
          ],
        },
        {
          name: '',
          required: true,
          description: '',
          type: 'string',
          value: {
            type: 'ref',
            content: {
              ref_node_id: '',
              ref_var_name: '',
              source: '',
            },
            hint: '',
          },
          source: 'user',
        },
      ],
      outputs: [
        {
          name: 'body',
          required: true,
          description: this.i18n.transform('request_response_body'),
          type: 'string',
          value: {
            type: 'generated',
            hint: '',
            content: null,
            default: '',
          },
          source: 'system',
        },
        {
          name: 'status_code',
          required: true,
          description: this.i18n.transform('request_status_code'),
          value: {
            type: 'generated',
            hint: '',
            content: null,
            default: '',
          },
          type: 'integer',
          source: 'system',
        },
        {
          name: 'headers',
          required: true,
          description: this.i18n.transform('request_response_header'),
          type: 'string',
          source: 'system',
          value: {
            type: 'generated',
            hint: '',
            content: null,
            default: '',
          },
        },
        {
          name: 'error_message',
          type: 'string',
          description: this.i18n.transform('error_message'),
          required: true,
          value: {
            type: 'generated',
            content: '',
            hint: '',
          },
          source: 'system',
        },
      ],
      configs: {
        isDefaultName: true,
        method: 'POST',
        endpoint: '',
        path: '',
        request_type: 'JSON',
        auth_info: {
          scope: 'SERVICE',
          domain: 'HEADERS',
          auth_keys: [
            {
              auth_key: '',
              target_name: '',
            },
          ],
        },
        request_body: '',
        exception_enable: true,
        exception_suppression: '{"body":"","status_code":0,"headers":""}',
      },
    };
  }

  public async getInitMcpNodeData(
    service: IMCPService,
    type: INodeType = 'Mcp',
  ): Promise<IMcpNode> {
    const id = `node_${Date.now()}`;
    const { server_id, name, desc, name_en, description_en, description } =
      service as any;
    const mcpId = service.id;
    const mcpInfo = service.mcpInfo;
    let tool_name = '';
    let input_schema = '';
    let output_schema = '';
    let inputs: IWorkflowField[] = [];
    let name_test = '';
    let outputs: IWorkflowField[] = [];
    let headerInput = [];
    if (type === 'Mcp' && mcpInfo.server_config) {
      try {
        const serverConfig = JSON.parse(mcpInfo.server_config);
        const headers = serverConfig?.mcpServers?.[MCP_SERVER[mcpInfo.org_type]]?.headers;
        if (headers) {
          Object.entries(headers).forEach(([key, value]) => {
            headerInput.push({
              name: key,
              type: 'string',
              description: '',
              required: true,
              source: 'user',
              reflection: false,
              value: {
                type: 'literal',
                content: value,
                hint: ''
              },
            });
          });
        }
      } catch (error) {
        // do nth
      }
    }
    if (mcpInfo && mcpInfo.tools && Array.isArray(mcpInfo.tools)) {
      const tools = mcpInfo.tools;
      tool_name = tools.length ? tools[0].name : '';
      input_schema = tools.length ? tools[0].input : '';
      output_schema = tools.length ? tools[0].output : '';
      name_test = tools.length ? tools[0].name : '';
      inputs = [
        ...headerInput,
        ...reqSchemaStrMCPField(input_schema),
      ];
      outputs = reqSchemaStrMCPField(output_schema);
    }
    return {
      id,
      name,
      type,
      inputs,
      outputs,
      configs: {
        id: mcpId,
        name,
        name_en,
        tool_name,
        valid: true,
        original_info: {
          name,
          name_en,
          description: description_en || description,
        },
      },
    };
  }

  public async getInitDataAcquisitionData(
    service: IMCPService,
    type: INodeType = 'DataAcquisition',
  ): Promise<IMcpNode> {
    const id = `node_${Date.now()}`;
    const { server_id, name, desc, name_en, description_en, description } =
      service as any;
    const mcpId = service.id;
    const mcpInfo = await this.api.getMcpToolInfo(mcpId);
    let tool_name = '';
    let input_schema = '';
    let output_schema = '';
    let inputs: IWorkflowField[] = [];
    let outputs: IWorkflowField[] = [];
    if (mcpInfo && mcpInfo.tools && Array.isArray(mcpInfo.tools)) {
      const tools = mcpInfo.tools;
      tool_name = tools.length ? tools[0].name : '';
      input_schema = tools.length ? tools[0].input : '';
      output_schema = tools.length ? tools[0].output : '';
      inputs = reqSchemaStrMCPField(input_schema);
      outputs = reqSchemaStrMCPField(output_schema);
    }
    return {
      id,
      name,
      type,
      inputs,
      outputs,
      configs: {
        id: mcpId,
        name,
        name_en,
        tool_name,
        valid: true,
        original_info: {
          name,
          name_en,
          description: description_en || description,
        },
      },
    };
  }

  public getInitAgentNodeData(): IAgentRepo {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: 'Agent',
      type: 'Agent',
      inputs: [],
      outputs: [
        {
          name: 'output',
          type: 'string',
          description: '',
          value: {
            type: 'generated',
            content: null,
            hint: '',
          },
          required: false,
          source: 'user', // 输出变量配置为用户级变量，暂不支持前端修改（置灰）
        },
      ],
      configs: {
        system_prompt: '',
        max_iteration: 9, // 最大工具调用轮次
        temperature: 0.5,
        model: {
          model_name: '',
          model_type: '',
          model_deployment_id: '',
          model_id: '',
        },
        top_p: 0.5,
        max_tokens: null,
        plugins: [],
        isDefaultName: true,
      },
    };
  }

  /** @param advancedIntentId 与新建的容器节点相绑定的高级意图节点id */
  public getInitIntentContainerNodeData(
    advancedIntentId: string,
  ): IIntentContainerNode {
    const id = `node_intent_container_${advancedIntentId}`;

    return {
      id,
      name: this.i18n.transform('IntentDetectionContainer'),
      type: 'IntentDetectionContainer',
      inputs: [
        {
          name: 'input',
          type: 'string',
          description: '',
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          required: false,
          source: 'system',
        },
      ],
      outputs: [
        {
          name: 'response_content',
          type: 'string',
          description: this.i18n.transform(
            'intentDetection.response_content_description',
          ),
          value: {
            type: 'generated',
            content: '',
            hint: '',
          },
          required: true,
          source: 'system',
        },
      ],
      branches: [],
      configs: {
        groups: {
          response_content: [
            { ...getInitInputParamConfig(), name: 'branch_0', type: 'string' },
          ],
        },
        mode: 'first-non-null',
      },
    };
  }

  /** 工作流节点，与多Agent控制器节点绑定 */
  public getInitWorkflowNodeData(
    name: string,
    inputs: IWorkflowField[],
    outputs: IWorkflowField[],
    configs: IWorkflowConfigs,
  ): IWorkflowNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name,
      type: 'Workflow',
      inputs,
      outputs,
      configs,
    };
  }

  /** 问答节点 */
  public getInitQANodeData(): IQANode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('QA'),
      type: 'QA',
      inputs: [],
      outputs: [
        {
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          name: 'response',
          description: '',
          required: true,
          type: 'string',
          source: 'user',
        },
      ],
      configs: {
        isDefaultName: true,
        qaStrategy: 'random',
        options: [],
        needReply: true,
      },
    };
  }

  /** 卡片节点 */
  public getInitCardNodeData(): ICardNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.i18n.transform('Card'),
      type: 'Card',
      inputs: [
        {
          name: '',
          description: '',
          required: true,
          subType: ['string'],
          type: 'string',
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          source: 'user',
        },
      ],
      outputs: [],
      configs: {
        isDefaultName: true,
      },
    };
  }

  public getInitExceptionNodeData(): IExceptionNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      outputs: [],
      name: this.nodeDefaultNameMap.get('StructuredMessagesException'),
      type: 'StructuredMessagesException',
      inputs: [getInitInputParamConfig()],
      configs: {
        isDefaultName: true,
        template: '',
      },
    };
  }

  public getInitParamExtractionNodeData(): IParamExtractionNode {
    const id = `node_${Date.now()}`;
    return {
      id,
      name: this.nodeDefaultNameMap.get('ParamExtraction'),
      type: 'ParamExtraction',
      inputs: [getInitInputParamConfig()],
      outputs: [],
      configs: {
        isDefaultName: true,
        domain_objects: [],
        model: {
          model_deployment_id: '',
          model_id: '',
          model_name: '',
          model_type: '',
        },
        prompt: '',
        enable_intent_break: true,
        intent_break_prompt: '',
        // entry_condition: {},
        extension_workflows: [],
        // break_condition: {},
        description: '',
        // exception_config: {},
      },
    };
  }
  public getInitDataQueryNodeData(): IDataQueryNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('DataQuery'),
      type: 'DataQuery',
      inputs: [
        {
          name: 'query',
          type: 'string',
          description: '',
          required: false,
          source: 'user',
          reflection: false,
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
        },
      ],
      outputs: [
        {
          name: 'output_list',
          description: '',
          required: true,
          type: 'array',
          schema: {
            name: '',
            type: 'object',
            schema: [],
          },
          value: {
            content: '',
            type: 'generated',
            hint: '',
          },
          source: 'user',
          reflection: false,
        },
        {
          name: 'row_num',
          description: i18next.t('appflowservice_2'),
          required: true,
          type: 'integer',
          value: {
            content: '',
            type: 'generated',
            hint: '',
          },
          source: 'user',
          reflection: false,
        },
      ],
      configs: {
        isDefaultName: true,
        id: '',
        name: '',
        sql: '',
      },
    };
  }

  /** 数据库节点 */
  public getInitSqlNodeData(): ISqlNode {
    const id = `node_${Date.now()}`;

    return {
      id,
      name: this.nodeDefaultNameMap.get('Sql'),
      type: 'Sql',
      inputs: [
        {
          name: 'query',
          required: true,
          source: 'user',
          reflection: false,
          value: {
            type: 'literal',
            content: '',
            hint: '',
          },
          type: 'string',
          description: '',
        },
      ],
      outputs: [
        {
          name: 'output_list',
          description: '',
          schema: {
            name: '',
            type: 'object',
            schema: [],
          },
          required: true,
          type: 'array',
          source: 'user',
          reflection: false,
          value: {
            content: '',
            type: 'generated',
            hint: '',
          },
        },
        {
          name: 'row_num',
          description: i18next.t('appflowservice_235'),
          required: true,
          type: 'integer',
          value: {
            content: '',
            type: 'generated',
            hint: '',
          },
          source: 'user',
          reflection: false,
        },
      ],
      configs: {
        isDefaultName: true,
        id: '',
        name: '',
        sql: '',
      },
    };
  }

  public getUpdateGraphData(
    graph: Graph,
    workflow: IWorkflow,
    is_sub_controller_update = false,
  ): IWorkflow {
    const cellList = graph?.toJSON().cells;
    const nodes = [] as any[];
    const edges = [] as EdgeData[];
    const params = { ...workflow };
    const comments = [] as any[];

    cellList?.forEach((item) => {
      if (item.shape === 'dag-edge' || item.shape === 'edge') {
        const { id, shape, source, target } = item as EdgeData;
        if (target) {
          //没有目标节点的边不保存
          edges.push({ id, shape, source, target } as EdgeData);
        }
      } else if (item.shape === 'op-comment-node') {
        const { id, shape, position, size, data } = item as any;
        this.fixQAInputRef(data);
        comments.push({
          id,
          shape,
          position,
          size,
          data: {
            ...data.ngArguments.nodeInfo,
          },
        });
      } else {
        const { id, shape, position, data, ports } = item as any;
        this.fixQAInputRef(data);
        nodes.push({
          id,
          shape,
          position,
          data: {
            ...data.ngArguments.nodeInfo,
          },
          ports,
        });
      }
    });

    params.workflow_details = this.nodeDataToFetchData(
      { nodes, edges, comments },
      workflow,
      is_sub_controller_update,
    );

    return params;
  }

  /** 移除没有目标节点的边 */
  removeNotLinkedEdge(graph: Graph) {
    try {
      const allEdges = graph.getEdges();

      allEdges.forEach((edge) => {
        if (!edge.getTargetCellId()) {
          edge.remove({ ignoreHistory: true });
        }
      });
    } catch (e) {
      //do nothing
    }
  }

  /** 判断节点之间有没有连线 */
  judgeLinkedEdge(graph: Graph, sourceId: string, targetId: string) {
    const allEdges = graph.getEdges();
    return allEdges.some((edge) => {
      return (
        edge.getTargetCellId() === targetId &&
        edge.getSourceCellId() === sourceId
      );
    });
  }
  /** 判断节点连线桩之间有没有连线 */
  judgeLinkedEdgeByPort(graph: Graph, sourceId: string, targetId: string,sourcePort: string) {
    const allEdges = graph.getEdges();
    return allEdges.some((edge) => {
      return (
        edge.getTargetCellId() === targetId &&
        edge.getSourceCellId() === sourceId &&
        edge.getSourcePortId() === sourcePort
      );
    });
  }

  private nodeDataToFetchData(
    cellData: CellData,
    workflow: IWorkflow,
    is_sub_controller_update = false,
  ): IWorkflowDetail {
    const controller_node: any = workflow?.details?.nodes?.find(
      (item) => item.type === 'Controller',
    );
    const agents = controller_node ? controller_node.configs.agents : [];

    const nodes: NodeData[] = cellData.nodes;
    const newNodes: NodeInfo[] = [];
    const layouts: ILayouts = {};
    const edges: EdgeData[] = cellData.edges;
    const comments: NodeData[] = cellData.comments;
    const commentNodes: ICommentNode[] = [];

    nodes.forEach((item: any) => {
      const { id, shape, position, data } = item;
      layouts[id as string] = position as Position;

      if (id === 'controller' && is_sub_controller_update) {
        data?.configs?.agents?.forEach((ag, index) => {
          const has_agents = agents?.find((item) => item.id === ag.id);
          if (has_agents) {
            data.configs.agents[index] = agents?.find(
              (item) => item.id === ag.id,
            );
          }
        });
      }

      const newFetchData = {
        id,
        type: shape,
        name: data.name,
        ...data,
      };

      if (newFetchData?.nodeInfo) {
        delete newFetchData?.nodeInfo;
      }

      newNodes.push(newFetchData);
    });

    comments.forEach((item: any) => {
      const {
        id,
        position: { x, y },
        size: { width, height },
        data: { name, type, content },
      } = item;
      const newCommentData = {
        id,
        name,
        type,
        x,
        y,
        width,
        height,
        content,
      };
      commentNodes.push(newCommentData);
    });

    const newEdges = edges.map((item: EdgeData) => {
      const sourceCell = item.source;
      const targetCell = item.target;
      const source = sourceCell.cell;
      const target = targetCell.cell;
      const edge = { source, target } as IWorkflowEdge;
      const node = nodes.find((n: NodeData) => n.id === source);
      if (sourceCell.port === 'exception_branch') {
        edge.exception_branch = true;
      }
      if (
        node &&
        (node.shape === 'op-branch-node' ||
          (node.shape === 'op-intentdetection-node' &&
            FlowUtils.isNormalMode(node.data as any)))
      ) {
        edge.branch = sourceCell.port;
      }
      return edge;
    });
    const uniqEdges = uniqWith(newEdges,isEqual);
    return {
      id: workflow?.workflow_id,
      name: workflow?.name,
      nodes: newNodes,
      comments: commentNodes,
      edges: uniqEdges,
      description: workflow?.description,
      configs: workflow?.workflow_details?.configs,
      layouts,
    };
  }

  public plugin2ApiNode(pluginContent): IPluginNode {
    const id = `node_${Date.now()}`;
    const inputs: IWorkflowField[] = reqSchemaStr2Field(
      pluginContent?.input_schema,
    );
    //插件路径参数
    const pluginPathInputs: IWorkflowField[] = reqSchemaStr2Field(
      pluginContent?.request_info?.basic_info?.input_schema,
    );

    // 若插件支持流式输出，增加自定义输出参数
    const outputs: IWorkflowField[] =
      pluginContent?.intf_type === 'streaming'
        ? [
            {
              name: 'raw_output',
              description: this.i18n.transform('plug_in_streaming_output'),
              value: {
                type: 'literal',
                content: '',
                hint: '',
              },
              type: 'string',
              source: 'user',
              isDisabled: false,
              required: false,
            },
            ...resSchemaStr2Field(pluginContent.output_schema),
          ]
        : resSchemaStr2Field(pluginContent.output_schema);

    return {
      id,
      name: `${pluginContent.plugin_chinese_name}/${pluginContent.tool_chinese_name}`,
      type: 'Plugin',
      inputs: [...inputs, ...pluginPathInputs],
      outputs,
      configs: {
        id: pluginContent.id,
        streaming: pluginContent?.intf_type === 'streaming',
        tool_id: pluginContent.tool_id,
        type: pluginContent.type,
        ...(pluginContent?.last_version_id && {
          version_id: pluginContent.last_version_id,
        }),
        name: pluginContent?.tool_chinese_name,
        valid: true,
        output_schema: pluginContent?.output_schema,
        original_info: {
          name: pluginContent?.tool_chinese_name,
          name_en: pluginContent.tool_display_name,
          description: pluginContent.tool_desc,
          type: pluginContent?.type,
        },
      },
    };
  }

  public childFlow2ApiNode(flowContent: IWorkflow): IFlowNode {
    const id = `node_${Date.now()}`;

    let copy_name = 'node_module';

    const inputs: IWorkflowField[] = (
      flowContent.workflow_details.nodes.find(
        (item) => item.type === 'Start',
      ) as IStartNode
    ).outputs.filter(
      (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
    );

    let test_name = copy_name;

    inputs.forEach((item) => {
      const { default: defaultValue } = item.value;
      const content = isNil(defaultValue) ? '' : defaultValue;
      const value: IWorkflowFieldValue = {
        content,
        hint: '',
        type: 'literal',
      };

      test_name = test_name + 'node';

      if (!isNil(defaultValue)) {
        value.default = defaultValue;
      }

      item.value = value;
    });

    const outputs: IWorkflowField[] = (
      flowContent.workflow_details.nodes.find(
        (item) => item.type === 'End',
      ) as IEndNode
    ).outputs;

    return {
      id,
      name: flowContent.name,
      type: 'Workflow',
      inputs,
      outputs,
      configs: {
        id: '',
        version_name: '',
        plugins: [],
        original_info: {
          name: flowContent.name,
          name_en: flowContent.code,
          description: flowContent.description,
        },
        name: '',
        version_id: '',
      },
    };
  }

  public childFlow2ApiNodeNew(
    flowContent: IWorkflow,
    node: PublishedWorkflow,
  ): IFlowNode {
    const id = `node_${Date.now()}`;

    let copy_id = id;

    const inputs: IWorkflowField[] = (
      flowContent.workflow_details.nodes.find(
        (item) => item.type === 'Start',
      ) as IStartNode
    ).outputs.filter(
      (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
    );

    let test_name = copy_id;

    inputs.forEach((item) => {
      const { default: defaultValue } = item.value;
      const content = isNil(defaultValue) ? '' : defaultValue;
      const value: IWorkflowFieldValue = {
        content,
        hint: '',
        type: 'literal',
      };

      test_name = copy_id;

      if (!isNil(defaultValue)) {
        value.default = defaultValue;
      }

      item.value = value;
    });

    const outputs: IWorkflowField[] = (
      flowContent.workflow_details.nodes.find(
        (item) => item.type === 'End',
      ) as IEndNode
    ).outputs;

    return {
      id,
      name: flowContent.name,
      type: 'Workflow',
      inputs,
      outputs,
      configs: {
        id: node.workflow_id,
        name: flowContent.name,
        version_id: node.version_id,
        original_info: {
          name: flowContent.name,
          name_en: flowContent.code,
          description: flowContent.description,
        },
        version_name: node.version_name,
        plugins: [],
      },
    };
  }

  /** 子工作流节点升级新版本后，处理开始节点的输入参数列表 */
  public updateChildFlow2ApiNode(inputs: IWorkflowField[]): IWorkflowField[] {
    const filteredInputs = inputs.filter(
      (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
    );
    filteredInputs.forEach((item) => {
      if (!item.value?.content) {
        item.value = { content: '', hint: '', type: 'literal' };
      }
    });
    return filteredInputs;
  }

  public getNewGraph(container: HTMLDivElement, isMulti: boolean) {
    const that = this
    return new Graph({
      container,
      width: container.offsetWidth,
      height: container.offsetHeight,
      background: {
        color: '#f7f7f8',
      },
      embedding: {
        enabled: true,
        findParent({ node }) {
          const isConnectedNode = !!this.getConnectedEdges(node).length;
          const isEmbeded = node.getParent();

          if (isConnectedNode && !isEmbeded) {
            return [];
          }

          const bbox = node.getBBox();
          const movingData = node?.data?.ngArguments
            ?.nodeInfo as NodeInfo | null;

          if (movingData.type === 'Loop') {
            return [];
          }

          if (movingData && !CANT_EMBEDDING_NODES.includes(movingData.type)) {
            const parentNodes = this.getNodes().filter((targetNode) => {
              const data = targetNode.getData();
              const isLoop =
                (data?.ngArguments?.nodeInfo as NodeInfo).type === 'Loop';

              if (data && targetNode.id !== node.id && isLoop) {
                const targetBBox = targetNode.getBBox();
                return bbox.isIntersectWithRect(targetBBox);
              }

              return false;
            });
            // 不允许直接拖拽到其他循环内
            if (parentNodes.length && isEmbeded) {
              return [isEmbeded];
            }
            return parentNodes;
          }

          return [];
        },
      },
      highlighting: {
        embedding: {
          args: {
            className: 'embedding-highlighting',
          },
          name: 'className',
        },
      },
      autoResize: true,
      connecting: {
        router: 'orth',
        snap: true,
        connector: 'bezier',
        sourceAnchor: {
          name: 'center',
          args: {
            dx: 8,
          },
        },
        targetAnchor: {
          name: 'center',
          args: {
            dx: -16,
          },
        },
        connectionPoint: 'anchor',
        allowBlank: !isMulti, // 多智能体不支持
        allowLoop: false,
        highlight: true,

        // 连接桩校验
        validateConnection({
          sourceMagnet,
          targetMagnet,
          sourceView,
          sourceCell,
          targetCell,
          sourcePort,
        }) {
          if (!sourceView) {
            return false;
          }
          const graph = sourceView.graph as Graph;
          // 禁止节点连接到自己
          if (sourceCell && targetCell && sourceCell.id === targetCell.id) {
            return false;
          }
          // 已有连线的不能在连线
          if(sourceCell && targetCell && that.judgeLinkedEdgeByPort(graph,sourceCell.id,targetCell.id,sourcePort)){
            return  false
          }
          // 只能从输出left连接桩创建连接
          if (
            !sourceMagnet ||
            sourceMagnet.getAttribute('port-group') === 'left'
          ) {
            return false;
          }

          // 只能连接到输入连接桩 非 left
          if (
            !targetMagnet ||
            targetMagnet.getAttribute('port-group') !== 'left'
          ) {
            return false;
          }

          const sourceNodeInfo = sourceCell?.data?.ngArguments
            ?.nodeInfo as NodeInfo;
          if (FlowUtils.isAdvancedModeNew(sourceNodeInfo)) {
            return false;
          }

          const targetParent = targetCell.getParent();
          const sourceParent = sourceCell.getParent();

          if (
            sourceParent &&
            sourceMagnet.getAttribute(PORT_CONNECTED_ATTR) ===
              PORT_CONNECTED.connected
          ) {
            return false;
          }

          if (!!targetParent !== !!sourceParent) {
            return false;
          }

          if (targetParent && targetParent.id !== sourceParent.id) {
            return false;
          }

          // 如果target是提问器节点并且并行分支里已经有提问器节点
          // 返回 false
          const targetType = (
            targetCell?.data?.ngArguments?.nodeInfo as NodeInfo
          )?.type;

          if (targetType === 'IntentDetectionContainer') {
            return false;
          }

          if (INTERACTION_NODES.includes(targetType)) {
            const hasParallel = graph
              .getOutgoingEdges(sourceCell)
              .filter((edge) => {
                const eSourcePort = (edge.source as IConnection)?.port;
                const hasConnectedTarget = !!(edge.target as IConnection)?.port;

                return (
                  eSourcePort &&
                  eSourcePort === sourcePort &&
                  hasConnectedTarget
                );
              })
              .some((edge) => {
                const targetNode = edge.getTargetCell();
                const existType = (
                  targetNode?.data?.ngArguments?.nodeInfo as NodeInfo
                )?.type;

                return (
                  INTERACTION_NODES.includes(existType) &&
                  existType === targetType
                );
              });

            return !hasParallel;
          }

          return true;
        },
        createEdge() {
          return new Shape.Edge({
            attrs: {
              line: {
                strokeWidth: 2,
                stroke: FLOW_COLORS.defaultLine,
                targetMarker: TargetMarker,
              },
            },
            zIndex: -1,
          });
        },
      },
      panning: {
        enabled: true,
        modifiers: null,
        eventTypes: ['leftMouseDown'],
      },
      mousewheel: {
        enabled: true,
      },
      scaling: {
        min: 0.1,
        max: 2,
      },
      grid: {
        type: 'plus-pattern',
        size: 18,
        visible: true,
      },
      interacting: (cellView) => {
        // 多智能体不能连线，并且没有注释节点
        if (isMulti){
          return { magnetConnectable: false }
        }
        const cell = cellView.cell;
        if (cell.isNode() && cell.getData()?.isEditing) {
          return { nodeMovable: false };
        }
        return true;
      },
      async: false,
      virtual: { enabled: false, margin: 200 },
    });
  }

  /** 临时规避修改开始节点参数默认值，问答节点引用同名参数会报ir错误 */
  private fixQAInputRef(data) {
    const { type, inputs } = data.ngArguments.nodeInfo;
    if (type === 'QA') {
      inputs?.forEach((item) => {
        if (item.value.type === 'ref') {
          item.value.content = Array.isArray(item.value.content)
            ? item.value.content?.[0]
            : item.value.content;
        }
      });
    }
  }

  /*请求变量*/
  public requestVariablesFn(info) {
    const nameRefOptions = cloneDeep(info);
    const startParam: any = nameRefOptions?.find(
      (item) => item.type === 'Start',
    );
    if (!startParam) {
      return [];
    }
    startParam.name = this.i18n.transform('request_param');
    startParam.source = 'request';
    startParam.ref_node_id = 'node_start_request';
    startParam.type = 'Request';
    const origin_children = startParam.children?.slice(1);
    startParam.children = origin_children?.map((item) => {
      item?.children?.forEach((child) => {
        child.source = 'request';
        child.ref_node_id = 'node_start_request';
      });
      return {
        ...item,
        source: 'request',
        ref_node_id: 'node_start_request',
      };
    });
    return startParam.children?.length > 0 ? [startParam] : [];
  }

  /**
   * 判断多智能体是否有嵌套子智能体
   * @param graph
   */
  judgeExceedsSubController(graph): string[] {
    const cellList = graph?.toJSON().cells;
    const result = [] ;
    cellList?.forEach((cell) => {
      if (cell.shape === 'op-subcontroller-node') {
        const nodeInfo = cell.data.ngArguments.nodeInfo
        if (nodeInfo?.configs?.agents?.length) {
          result.push(nodeInfo.name)
        }
      }
    });
    return result
  }
}
