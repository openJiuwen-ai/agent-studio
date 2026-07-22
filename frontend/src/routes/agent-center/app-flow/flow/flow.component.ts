/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-this-alias */
/* eslint-disable no-underscore-dangle */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-call */
import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  HostListener,
  Injector,
  isDevMode,
  NgZone,
  OnDestroy,
  OnInit,
  Renderer2,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Cell, Edge, EdgeView, Graph, Node, Selection, History } from '@antv/x6';
import type { CellMetadata, NodeMetadata, EdgeProperties, Rectangle, NodeProperties } from '@antv/x6';
import { MessageComponent } from '@shared/services/cfdata.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerRef, NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
import { I18nNamespace } from '@i18n';
import { IPlugin } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { AgentCenterHomeService, TabIndex } from '@services/agent-center/agent-center-home.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { ContextService } from '@services/context.service';
import { AssetLogIconComponent } from '@shared/components/assets/asset-log-icon/asset-log-icon.component';
import {
  AssetAsyncRunIconComponent
} from '@shared/components/assets/asset-async-run-icon/asset-async-run-icon.component';
import { AssetRunIconComponent } from '@shared/components/assets/asset-run-icon/asset-run-icon.component';
import { PublishVersionModalComponent } from '@shared/components/publish-version-modal/publish-version-modal.component';
import {
  ReleaseHistoryHalfmodalComponent
} from '@shared/components/release-history-halfmodal/release-history-halfmodal.component';
import { ITabHeader, TabsHeaderComponent, } from '@shared/components/tabs-header/tabs-header.component';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep, debounce, isEqual, isNil } from 'lodash';
import { debounceTime, delay, filter, Subject, Subscription, takeUntil } from 'rxjs';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonUtils } from 'src/utils/common.util';
import {
  deleteViewParamsForDsl,
  fillAdvancedBranches,
  handleCommonReqError,
  isMacOS,
  modifyAdvancedDsl,
  modifyOutput,
  removeHTMLTag,
} from 'src/utils/utils';
import { v4 as uuidV4 } from 'uuid';
import { AppFlowService, INodeHeightUpdate, IUpdateNodeData } from '../app-flow.service';
import {
  DragMode,
  EHalfmodalType,
  IEdgeType,
  IFlowConfigs,
  IMCPService,
  IModel,
  IRefInfo,
  IRefWorkflows,
  IWorkflow,
  IWorkflowInfo,
  Position,
  WorkFlowType,
} from '../app-flow.types';
import { AddChildFlowModalComponent } from '../components/add-child-flow-modal/add-child-flow-modal.component';
import { AddMCPServiceModalComponent } from '../components/add-mcp-service-modal/add-mcp-service-modal.component';
import { AddPluginModalComponent } from '../components/add-plugin-modal/add-plugin-modal.component';
import { AggregationModalComponent } from '../components/aggregation-modal/aggregation-modal.component';
import { BranchModalComponent } from '../components/branch-modal/branch-modal.component';
import { ChildFlowModalComponent } from '../components/child-flow-modal/child-flow-modal.component';
import { CodeModalComponent } from '../components/code-modal/code-modal.component';
import { ControllerModalComponent } from '../components/controller-modal/controller-modal.component';
import { DialogHalfmodalComponent } from '../components/dialog-halfmodal/dialog-halfmodal.component';
import { EndModalComponent } from '../components/end-modal/end-modal.component';
import { FlowDetailHeaderComponent } from '../components/flow-detail-header/flow-detail-header.component';
import { FlowLogModalComponent } from '../components/flow-log-modal/flow-log-modal.component';
import { FlowNodesWidgetComponent } from '../components/flow-nodes-widget/flow-nodes-widget.component';
import { GlobalConfigComponent } from '../components/global-config/global-config.component';
import { InputModalComponent } from '../components/input-modal/input-modal.component';
import { IntentContainerModalComponent } from '../components/intent-container-modal/intent-container-modal.component';
import { IntentModalComponent } from '../components/intent-modal/intent-modal.component';
import { KnowledgeModalComponent } from '../components/knowledge-modal/knowledge-modal.component';
import { LLMModalComponent } from '../components/llm-modal/llm-modal.component';
import { LoopModalComponent } from '../components/loop-modal/loop-modal.component';
import { MCPServiceModalComponent } from '../components/mcp-service-modal/mcp-service-modal.component';
import { MessageModalComponent } from '../components/message-modal/message-modal.component';
import { MultiAgentConfigComponent } from '../components/multi-agent-config/multi-agent-config.component';
import { NodeExeComponent } from '../components/node-exe/node-exe.component';
import { NodesGroupModalComponent } from '../components/nodes-group-modal/nodes-group-modal.component';
import { PluginModalComponent } from '../components/plugin-modal/plugin-modal.component';
import { QAModalComponent } from '../components/QA-modal/QA-modal.component';
import { QuestionerModalComponent } from '../components/questioner-modal/questioner-modal.component';
import { RunModalComponent } from '../components/run-modal/run-modal.component';
import { SetVariableModalComponent } from '../components/set-variable-modal/set-variable-modal.component';
import { SqlModalComponent } from '../components/sql-modal/sql-modal.component';
import { StartModalComponent } from '../components/start-modal/start-modal.component';
import { UpdateNodeNameModalComponent } from '../components/update-node-name-modal/update-node-name-modal.component';
import { IRefIndex, NodeUtils } from '../components/utils';
import { WorkflowModalComponent } from '../components/workflow-modal/workflow-modal.component';
import {
  ADD_BETWEEN_NODE_DISTANCE,
  EXCEPTION_PORT_NODE,
  FLOW_COLORS,
  flowConfig,
  flowMcpListParams,
  getFlowMcpNodeData,
  LAZY_LOAD_LIMIT,
  MULTI_PORT_NODE,
  PORT_CONNECTED,
  PORT_CONNECTED_ATTR,
} from '../flow.const';
import { NodeService } from '../node.service';
import {
  CANT_EMBEDDING_NODES,
  HasInputsNode,
  HasOutputsNode,
  IAgentRepo,
  IBranchNode,
  ICardNode,
  IControllerFlow,
  IControllerNode,
  IEndNode,
  IFlowNode,
  IIntentContainerNode,
  IIntentNode,
  ILLMNode,
  ILoopNode,
  IMcpNode,
  IPluginNode,
  IQuestionerNode,
  IRefContentType,
  ISetVariableNode,
  IsolatedTestableNode,
  IStartNode,
  IViewNodeData,
  IWorkflowField,
  IWorkflowNode,
  LLM_LIKE_NODES,
  NodeInfo,
  nonVersionedResNodes,
  NoOutputsNodeTypes,
  NoInputsNodeTypes,
  ExchangeUnSaveTypes,
  UnCopyNodeTypes,
  UnDeletableNodeTypes,
  versionedResNodes, ExchangeNoOutputType,
} from '../node.type';
import { FlowUtils, TargetMarker } from '../utils/flow-utils';
import { IAppRefList } from '@routes/agent-center/types/common.types';
import { getMaxReplySetting } from '@routes/agent-center/utils';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { ToolListComponent } from '@routes/agent-center/app-agent/components/tool-list/tool-list.component';
import {
  TriggerHalfmodalComponent,
} from '@routes/agent-center/app-agent/components/trigger-modal/trigger-modal.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import {
  ExceptionModalComponent,
} from '@routes/agent-center/app-flow/components/exception-modal/exception-modal.component';

import { SubControllerService } from '@services/agent-center/sub-controller.service';
import {
  UpdateNodeModalComponent
} from '@routes/agent-center/app-agent/components/update-node-modal/update-node-modal.component';

import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { MCPService } from '@services/agent-center/mcp.service';
import { WindowResizeService } from '@shared/base/window-resize.service';
import {
  ParamExtractionModalComponent,
} from '@routes/agent-center/app-flow/components/param-extraction-modal/param-extraction-modal.component';
import { CommonService } from '@services/common.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { ModelRouterStrategiesService } from '@services/repositories/model-router-strategies';
import { MaskComponent } from '@shared/services/cfdata.service';
import { StreamTransformModalComponent } from '../components/stream-transform-modal/stream-transform-modal.component';
import { PipesModule } from '../../../../pipes/pipes.module';
import { HttpService } from '@services/http.service';
import {
  EnvironmentVariablesManagementService,
} from '@routes/platform-management/environment-variables-management/environment-variables-management.service';
import { FlowEventUtils } from '@routes/agent-center/app-flow/utils/flow-event-utils';

import { PublishChannelPageComponent } from 'src/shared/components/publish-channel-page/publish-channel-page.component';
import {
  CheckErrorWorkflowModal,
} from '@routes/agent-center/app-flow/components/check-error-workflow/check-error-workflow.component';
import { SingleAgentModalComponent } from '../components/single-agent-modal/single-agent-modal.component';
import { HelpCenterService } from '@services/help-center.service';
import { FlowHelperService } from '../utils/flow-helper.service';
import { EventBusService } from '@agentcore/core/event-bus.service';
import { FlowNodeRegisterService } from '../flow-node-register.service';
import { IMemoryLibBaseInfo } from '@routes/memory-lib/memory-lib-interfaces';
import {
  ControllerLogModalComponent,
} from '@routes/agent-center/app-flow/components/controller-log-modal/controller-log-modal.component';

enum mapKeys {
  version_id = 'version_id',
  version_name = 'version_name',
}

const NodeMap = {
  LLM: LLMModalComponent,
  Plugin: PluginModalComponent,
  Start: StartModalComponent,
  End: EndModalComponent,
  Input: InputModalComponent,
  Mcp: MCPServiceModalComponent,
  Branch: BranchModalComponent,
  Code: CodeModalComponent,
  IntentDetection: IntentModalComponent,
  ComplexIntentDetection: IntentModalComponent,
  Questioner: QuestionerModalComponent,
  Message: MessageModalComponent,
  KnowledgeRepo: KnowledgeModalComponent,
  Aggregation: AggregationModalComponent,
  Workflow: ChildFlowModalComponent,
  Loop: LoopModalComponent,
  SetVariable: SetVariableModalComponent,
  IntentDetectionContainer: IntentContainerModalComponent,
  Controller: ControllerModalComponent,
  SubController: ControllerModalComponent,
  QA: QAModalComponent,
  Sql: SqlModalComponent,
  StructuredMessagesException: ExceptionModalComponent,
  ParamExtraction: ParamExtractionModalComponent,
  StreamTransform: StreamTransformModalComponent,
};

export interface ICreateNodeConfig {
  isUpdateFlowData?: boolean;
  ignoreLoopEmbedding?: boolean;
}

export interface IUpdateFlowConfig {
  isDrag?: boolean;
  successCb?: () => void;
  faildCb?: () => void;
  nodeInfo?: any;
}

@Component({
  selector: 'meta-flow',
  templateUrl: './flow.component.html',
  styleUrls: ['./flow.component.less'],
  standalone: true,
  imports: [
    MODULES,
    FlowDetailHeaderComponent,
    DialogHalfmodalComponent,
    RunModalComponent,
    AssetLogIconComponent,
    AssetRunIconComponent,
    AssetAsyncRunIconComponent,
    NodeExeComponent,
    TabsHeaderComponent,
    NodesGroupModalComponent,
    ClickOutsideDirective,
    FlowNodesWidgetComponent,
    ToolListComponent,
    PipesModule,
    PublishChannelPageComponent,
    CheckErrorWorkflowModal,
    ReleaseHistoryHalfmodalComponent,
    GlobalConfigComponent,
    FlowLogModalComponent,
    MultiAgentConfigComponent,
    ControllerLogModalComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.REVIEW,
        I18nNamespace.MEMORY_LIB,
      ],
    },
  ],
})
export class FlowComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('dropLTMModal') dropLTMModal: TemplateRef<HTMLDivElement>;

  @ViewChild('publishChannelPage')
  publishChannelPage: PublishChannelPageComponent;
  public graph!: Graph;
  // 默认缩放百分数
  public defaultScale = 100;
  // 当前缩放百分数
  public localScale = '100';

  /** 是否为初始的空画布 */
  public isInitialCanvas = true;
  // 是否可以撤销
  public canUndo = false;

  // 是否可以恢复（前进）
  public canRedo = false;

  // 这个是应用的ID
  public workflowId = '';

  public orginWorkflowId = '';

  public versionId = '';

  public showRunModal = false;

  public container = null;

  public workflowDetail!: IWorkflow;

  private destroy$ = new Subject<void>();

  public createMcpSub$ = new Subject<any>();

  public userId = '';

  public cdnUrl = cdnAssetUrl;

  public logo = '';

  public availableModelList = [];

  // 试运行工作流接口所需的入参conversation_id
  public conversationId = uuidV4();

  public showGlobalConfigDrawer = false;
  public showLogDrawer = false;
  public showPluginDrawer = false;
  public showChildFlowDrawer = false;
  public showMcpServiceDrawer = false;
  public showNodeConfigDrawer = false;
  public showTriggerModal = false;

  public halfModalRef: NzDrawerRef;
  public childFlowModalRef: NzDrawerRef;
  public pluginModalRef: NzDrawerRef;
  public mcpModalRef: NzDrawerRef;
  public halfModalNodeId = '';

  public globalConfigDrawerWidth = '480px';
  public nodeConfigDrawerWidth = '600px';
  public globalConfigInputs = [];
  public globalConfigVariables = [];
  public globalConfigMemoryConfig = null;
  public globalConfigEnvironment = '';
  public globalConfigFlowId = null;
  public logConversationId = '';
  public nodeConfigNodeInfo = null;
  public nodeConfigNodeType = '';
  public nodeConfigNames = [];

  public showLogIsShowLog: any;
  public showLogGraph: any;
  public showLogWorkflowDetail: any;
  public showLogOpenNodeId: any;

  public pluginCallback: (plugin: IPlugin) => void;
  public childFlowCallback: ({workflow, config}: { workflow: IWorkflow; config: any }) => void;
  public mcpServiceCallback: (mcpService: IMCPService) => void;
  public nodeConfigCallback: (nodeData: any) => void;

  public isFlowReadonly = false;

  public notUserSelf = false;

  public isAllExpand = true;

  public isF1 = this.ctxServ.isF1ReqList();

  // 工作流类型，分为任务型和对话型
  public workflow_type: WorkFlowType = 'chat';

  public selectedEdgeId = '';

  public hoverEdges = []; //鼠标hover的边，x6鼠标移出事件有问题，记录处理

  public showLogModal = false;

  public showHistoryModal = false;

  public logModalTop = '';

  public showSingleTest = false;

  public nodeExeConversationId = uuidV4();

  public currTestNodeId = '';

  public currTestNodeInfo: IsolatedTestableNode | null = null;

  public curActiveTabId = 'flow';

  public clickNodeX = 0;

  public clickNodeY = 0;

  public triggerEmptyText = this.i18n.transform('triggerEmptyText');

  public headerTabs: ITabHeader[] = [
    {
      id: 'flow',
      title: this.i18n.transform('arrangement_configuration'),
      active: true,
    },
    {
      id: 'analyze',
      title: this.i18n.transform('data_analysis'),
      active: false,
      disabled: true,
      tips: this.i18n.transform('release_first'),
    },
  ];

  public actionNodeModal: any = null;

  // 是否来自于开发者空间
  private isFromDevelopSpace: boolean = false;

  private isFromOverview: boolean = false;
  private isFromFeatured: boolean = false;
  // 工作流的发布按钮。只有F1环境 或 op账号能看到，非F1环境的最终租户无法看到
  public isOpAccount = false;

  public versionName = '';

  // 打开的分享子工作流，只读页面,不请求版本列表和更新情况
  public fromShare = false;
  public addPanelPos = {
    left: 0,
    top: 0,
    x: 0,
    y: 0,
  };

  public addTipContent = {
    show: false,
    left: 0,
    top: 0,
  };

  public selectionTip = {
    show: false,
    count: 0,
    copyDisabledReason: '',
    deleteDisabledReason: '',
  };

  public triggerAdded = {
    title: this.i18n.transform('trigger'),
    collapsed: false,
    list: [],
    imageClass: 'common-img',
    isLoading: false,
  };

  public showAddPanel = false;

  public currentInActionEdge: Cell = null;

  public currentInActionEdgeView: EdgeView = null;

  public type = '';

  private nodeModalTop: number | null = null;

  public isMac = isMacOS();

  public publish_tip = this.i18n.transform('publish_tip');

  public showAddNodesWidget = false;

  public showMiniMap = false;

  public showFlowNodesWidget = false;

  public isMultiAgent = false;

  public workflow_parent_node_type = 'controller';

  private copiedNodeId = '';
  public isAfterCreatePlugin = false;
  public isAfterCreateAgentPlugin = false;
  public AfterCreateAgentPluginInfo = {
    pluginId: '',
    agentNode: '',
  };
  public afterCreateCardInfo = {
    cardId: '',
    agentNode: '',
  };

  public AfterCreatePluginInfo = {
    pluginId: '',
  };

  // 开始节点配置弹窗的确定按钮是否被点击。当put接口报错时，通过该变量，更新试运行入参
  private isStartNodeBtnClicked = false;

  isPrevEventEmbedded = false;

  // 是否校验过工作流。避免每次点节点配置的确定按钮时，都会校验一次
  private isFlowValidated = false;
  // 所有意图识别节点对应的模式映射
  private intentModesMap = [];
  historyVersionList = [];
  private originTitle = '';
  private ref_workflows: IRefWorkflows[] = [];
  // 所有节点对应的高度映射
  private nodeHeightMap: Map<string, number> = new Map();
  // 表示是否重置nodeHeightMap映射。覆盖3种情况：1）修改节点配置，高度变大；2）修改节点配置，高度减小；3）高级意图；4）还原版本和退出版本预览
  private isResetNodeHeightMap = false;

  // ctrl + zy keyDown事件
  private keyDownSubject = new Subject<void>();

  // delete keyDown事件
  private keyDownDelSubject = new Subject<string>();
  //保存事件
  private saveSubject = new Subject<void>();
  //ctrl + v keyDown事件
  private keyDownVSubject = new Subject<void>();

  private envList: any = [];

  showEnv = true;
  public isFromAgentBuilder: boolean = false;
  public isFromEditFlow: boolean = false;

  public isShowSuccessAlert: boolean = false;
  public isShowFailAlert: boolean = false;
  public createNewMcpData: any = {};

  public isShowRename: boolean = false;

  public isAfterCreateCard = false;

  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  private resizeSub: Subscription;

  public HWCloudTopHeight: number = 0;
  public liteLicenseAlertTopHeight: number = 0;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  // 获取agentBuilder的版本信息
  agentBuilderVersionId: string = '';
  agentBuilderVersionName: string = '';

  intentRecommendModel: any = {};
  editCodeModal = false;

  isKeyDownSpace = false; //是否按住空格

  dragMode: string = DragMode.HAND; //拖拽模式
  isShowModeTip = {show: false}; //是否展示拖拽模式选择tip
  isShowAcceleratorKeyTip = {show: false}; //是否展示快捷键tip
  showMask = true;

  public configHeaderTabs: ITabHeader[] = [
    {
      id: 'appConfig',
      title: this.i18n.transform('multi_agent_config'),
      active: true,
    },
    {
      id: 'releaseManage',
      title: this.i18n.transform('channel_management'),
      active: false,
      disabled: !this.historyVersionList.length,
      tips: '',
    },
  ];
  public curActiveConfigTabId = this.configHeaderTabs[0].id;
  public publishParams: any = {};

  accelerator_key_guide_visible = {show: false};

  private updateFlowDataLoading = false;

  draggingEdge = false;

  get nativeElementRef() {
    return this.elementRef.nativeElement;
  }

  get elementTop() {
    if (this.commonService.isSite()) {
      return this.liteLicenseAlertTopHeight
    }
    return this.HWCloudTopHeight
  }

  saveStatusMap;

  testBtnLoading = false;

  private exchangeNodeInfo: IStartNode = null;

  constructor(
    private appPluginRepoServ: AppPluginRepoService,
    private router: Router,
    private route: ActivatedRoute,
    private elementRef: ElementRef,
    public appFlowServ: AppFlowService,
    public cdr: ChangeDetectorRef,
    private appFlowRepoServ: AppFlowRepoService,
    private injector: Injector,
    private nzModal: NzModalService,
    private ngZone: NgZone,
    public nodeServ: NodeService,
    private ctxServ: ContextService,
    private ppServ: AgentCenterHomeService,
    private renderer: Renderer2,
    private appAgentRepoServ: AppAgentRepoService,
    private agentDataServe: AgentDataService,
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private modelManagementService: ModelManagementService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private SubControllerService: SubControllerService,
    private readonly mcpService: MCPService,
    private windowResizeService: WindowResizeService,
    private commonService: CommonService,
    private configServ: AgentConfigService,
    private tiMessage: NzMessageService,
    private modelRouterStrategiesService: ModelRouterStrategiesService,
    private envVariablesManagement: EnvironmentVariablesManagementService,
    private readonly http: HttpService,
    private helpCenterService: HelpCenterService,
    private flowHelperServ: FlowHelperService,
    private eventBusService: EventBusService,
    private nodeRegisterService: FlowNodeRegisterService,
    private nzDrawerService: NzDrawerService
  ) {
    // 注册更新工作流的方法
    this.appFlowServ.updateFlowData = this.updateFlowData.bind(this);

    this.originTitle = document.title;
    this.isOpAccount = this.ctxServ.isOpAccount;
    if (
      !window.localStorage.getItem('accelerator_key_guide') &&
      this.type !== 'multi'
    ) {
      this.accelerator_key_guide_visible.show = true;
    }
    this.route.queryParams.subscribe((params) => {
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
      if (params.from && params.from === 'edit-flow') {
        this.isFromEditFlow = true;
      }
    });
    this.HWCloudTopHeight = this.windowResizeService.getHWCloudTopHeight();
    //设置折叠状态
    this.nodeServ
      .isAllExpandUpdate$()
      .pipe(
        filter((val) => val !== this.isAllExpand),
        takeUntil(this.destroy$),
      )
      .subscribe((isAllExpand) => {
        this.isAllExpand = isAllExpand;
      });

    //更新SubController 智能体
    this.SubControllerService.subAgentsBodyUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((new_sub_detail) => {
        if (new_sub_detail) {
          let new_detail: any;
          this.workflowDetail.details.nodes.forEach((node: any) => {
            if (node.id === new_sub_detail.id) {
              this.updateAgentsNodeData(new_sub_detail);
            }

            if (node.type === 'Controller') {
              (node as IControllerNode).configs.agents.forEach(
                (agents: any, index: number) => {
                  if (agents.node_id === new_sub_detail.id) {
                    (node as IControllerNode).configs.agents[index] = {
                      id: agents.id,
                      node_id: agents.node_id,
                      mode: agents.mode,
                      name: new_sub_detail.name,
                      configs: new_sub_detail.configs,
                    };
                  }
                },
              );

              this.updateAgentsNodeData(node);

              this.createMultiAgentTree(
                node.configs.workflows,
                node.configs.agents,
              );
              new_detail = JSON.parse(JSON.stringify(this.workflowDetail));
            }
          });
          // 解决桩的位置问题
          this.nodeServ.setIsAllExpand(false);
          setTimeout(() => {
            this.nodeServ.setIsAllExpand(true);
          }, 0);
          this.cdr.detectChanges();

          // 更新并保存数据
          this.updateFlowData(
            {
              successCb: () => {
                const subFlows = this.appFlowServ.getResNodes()?.map((flow) => {
                  if (flow.id === new_sub_detail.id) {
                    flow.showIcon = false;
                  }
                  return flow;
                });

                this.appFlowServ.setResNodes(subFlows);

                MessageComponent.showSuccess(
                  this.i18n.transform('upgrade_version_successful'),
                  3000,
                );
              },
            },
            null,
            new_detail,
            true,
          );
        }
      });

    /** 保证画布上只出现一类抽屉 */
    this.appFlowServ
      .nodeClickedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((type: EHalfmodalType) => {
        const modalConfig: { [key in EHalfmodalType]: () => void } = {
          [EHalfmodalType.SINGLE_TEST]: () => (this.showSingleTest = false),
          [EHalfmodalType.NODE_CONFIG]: () => this.closeNodeConfigDrawer(),
          [EHalfmodalType.GLOBAL]: () => this.closeGlobalConfigDrawer(),
          [EHalfmodalType.INSIGHT]: () => this.closeLogDrawer(),
          [EHalfmodalType.TEST_RUN]: () => (this.showRunModal = false),
          [EHalfmodalType.HISTORY]: () => (this.showHistoryModal = false),
          [EHalfmodalType.TRIGGER]: () => {
            this.showTriggerModal = false;
          },
          [EHalfmodalType.DEFAULT]: () => {
          },
        };
        FlowUtils.closeOtherHalfmodal(type, modalConfig);
      });

    this.appFlowServ
      .nodeIdClickedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((nodeIdClicked: string) => {
        if (nodeIdClicked) {
          const cell = this.graph.getCellById(nodeIdClicked);
          if (cell) {
            this.graph.centerCell(cell);
            this.bringNodeToFront(this.graph, cell as Node);
            this.nodeServ.setCurrSelectedNode(cell.id);
          }
        }
      });

    this.appFlowServ
      .getTriggerUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((triggerAdded: any) => {
        const {trigger_id, name, type, cron, prompt, hook_url, invocation} =
          triggerAdded;
        if (type === 'TIMER') {
          const is_has = this.triggerAdded.list.some(
            (item) => item.trigger_id === trigger_id,
          );
          if (is_has) {
            for (let i = 0; i < this.triggerAdded.list.length; i++) {
              const cur = this.triggerAdded.list[i];
              if (cur?.trigger_id === trigger_id) {
                this.triggerAdded.list[i] = triggerAdded;
                break;
              }
            }
          } else {
            this.triggerAdded.list = [
              ...this.triggerAdded.list,
              {name, type, trigger_id, cron, prompt, invocation},
            ];
          }
        }
        if (type === 'EVENT') {
          this.triggerAdded.list = [
            ...this.triggerAdded.list,
            {name, type, trigger_id, prompt, hook_url},
          ];
        }
      });

    this.appFlowServ
      .flowErrorsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((validateRes) => {
        const {success, errors} = validateRes || {};
        if (success) {
          this.isFlowValidated = false;
        } else if (!success && errors?.length > 0) {
          this.isFlowValidated = true;
        } else {
          this.isFlowValidated = false;
        }
      });

    // 订阅还原版本的工作流详情
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (version) => {
        this.versionName = version.version_name;
        this.versionId = version.version_id;
        if (version.version_id) {
          this.rollbackFlowVersion(version);
        }

        if (version.isFlowReadonly) {
          this.setFlowReadonly(true);
        }

        if (this.graph && !version.isFlowReadonly) {
          this.setFlowReadonly(false);
        }

        if (version?.draft) {
          this.versionId = ''; // 点击【草稿】后，调用的get接口不传入versionId
          await this.initAppRefs();
          this.initWorkflowData();
        }
        this.isResetNodeHeightMap = true;
      });

    this.agentDataServe
      .publishStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        if (status === 'succeeded') {
          this.updateAnalyzeTabStatus(false);
          if (this.type === 'multi') {
            this.getAgentVersions();
          } else {
            this.getFlowVersionsFn();
          }
        }
      });

    // 删光某个应用的发布历史后，置灰查询发布通道入口
    this.agentDataServe
      .versionListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list: any) => {
        this.historyVersionList = list;
        this.setReleaseManageTab();
      });

    // 升级子工作流节点版本
    this.appFlowServ
      .childFlowPutBodyUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((body: any) => {
        if (this.notUserSelf) {
          return;
        }
        if (this.type === 'multi') {
          this.updateMultiAgenSubFlow(body);
        } else {
          this.closeNodeConfigDrawer();
          FlowUtils.updateChildFlowVersion(
            body,
            this.graph,
            this.workflowDetail,
            this.appFlowServ,
            this.updateFlowData.bind(this),
            this.checkRefChangeAndUpdateNode.bind(this),
          );
        }
      });

    // 升级意图容器节点绑定的多个子工作流版本
    this.appFlowServ
      .containerDslUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: IIntentContainerNode | IAgentRepo) => {
        FlowUtils.updateContainerFlowData(
          this.graph,
          this.workflowDetail,
          this.appFlowServ,
          this.updateFlowData.bind(this),
          data,
        );
      });

    this.appFlowServ
      .isOpenGlbConfUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe(() => {
        this.ngZone.run(() => {
          this.openConfigHalfmodal();
        });
      });

    this.appFlowServ
      .silentUpdateNodeDataUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: IUpdateNodeData) => {
        if (!data) {
          return; // data等于null时，直接跳过，避免控制台报错
        }
        this.updateNodeData(data.nodeInfo);
        this.updateFlowData({
          successCb: data.successCb,
          faildCb: data.faildCb,
        });
      });
    this.appFlowServ
      .getCardUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: any) => {
        const {nodeInfo = {}} = data;
        if (!nodeInfo.id) {
          return;
        }
        // 关掉抽屉
        this.closeNodeConfigDrawer();
        this.updateNodeData(data.nodeInfo);
        this.updateFlowData({
          successCb: data.successCb,
          faildCb: data.faildCb,
        });
      });
    this.keyDownSubject
      .pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe(() => {
        //删除中间态的边
        this.removeNoTargetNodeEdge();
        this.appFlowServ.removeNotLinkedEdge(this.graph);
        this.updateFlowData();
      });
    this.keyDownDelSubject
      .pipe(debounceTime(500), takeUntil(this.destroy$))
      .subscribe((type: string) => {
        this.updateFlowData({
          successCb: () => {
            if (type === 'Plugin') {
              this.appFlowServ.setRefreshFlag(true);
            }
          },
        });
      });
    this.saveSubject
      .pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe(() => {
        this.updateFlowData({
          isDrag: false,
          successCb: () => {
            MessageComponent.showSuccess(
              this.i18n.transform('successfully_saved'),
              3000,
            );
          },
        });
      });
    this.keyDownVSubject
      .pipe(debounceTime(300), takeUntil(this.destroy$))
      .subscribe(() => {
        this.updateFlowData({
          isDrag: false,
        });
      });
    // 恢复页面操作状态
    const CurrentModal =
      this.router.getCurrentNavigation()?.extras?.state?.currentModal ?? '';
    const pluginId =
      this.router.getCurrentNavigation()?.extras?.state?.new_plugin_id ?? '';
    const agentNode =
      this.router.getCurrentNavigation()?.extras?.state?.agent_node ?? '';
    const newCardId =
      this.router.getCurrentNavigation()?.extras?.state?.new_card_id ?? '';
    // 插件的
    if (CurrentModal === 'plugin' && !agentNode) {
      this.isAfterCreatePlugin = true;
      this.AfterCreatePluginInfo.pluginId = pluginId;
    }
    // agent里的插件
    if (CurrentModal === 'plugin' && agentNode) {
      this.isAfterCreateAgentPlugin = true;
      // 这里用于agent里创建插件回来后要打开agent节点并添加插件
      this.AfterCreateAgentPluginInfo.pluginId = pluginId;
      this.AfterCreateAgentPluginInfo.agentNode = agentNode;
    }

    if (CurrentModal === 'card') {
      this.isAfterCreateCard = true;
      this.afterCreateCardInfo.agentNode = agentNode;
      if (newCardId) {
        this.afterCreateCardInfo.cardId = newCardId;
      }
    }
    this.refAgentUpdate();
    this.appFlowServ
      .edgeStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: any) => {
        this.changeNodeLinkEdgeStatus(data);
      });

    this.eventBusService.on('empty-node-open-panel')
      .pipe(takeUntil(this.destroy$))
      .subscribe(data => {
        const {top, left} = FlowEventUtils.setPanelPosition(this.workflow_type, data.clientX, data.clientY);
        this.addPanelPos = {
          ...this.addPanelPos,
          top,
          left
        };
        this.showAddPanel = true;
        this.currentInActionEdge = null;
        this.currentInActionEdgeView = null;
        this.exchangeNodeInfo = data.nodeInfo;
      });
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  get showAsync() {
    return this.configServ.getConfigs()?.workflow_async_enable;
  }


  refAgentUpdate() {
    let info = JSON.parse(localStorage.getItem('workflowInfo'));
    if (info && info?.id) {
      setTimeout(() => {
        this.addAgent(info);
      }, 0);
      localStorage.removeItem('workflowInfo');
    }
  }

  judgmentWorkflowParentType(nodeInfo) {
    // 得到agents下所有的workflows
    const all_nodes = this.workflowDetail.details?.nodes ?? [];
    const controller: any = all_nodes.filter(
      (node) => node.type === 'Controller',
    );
    const wf_list = [];
    controller[0]?.configs?.agents?.forEach((ag) => {
      if (ag.configs?.workflows) {
        wf_list.push(...ag.configs.workflows);
      }
    });
    const parent_node_type =
      wf_list.filter((wf) => wf.node_id === nodeInfo.nodeInfo?.id)[0]
        ?.parent_node_type ?? 'controller';
    return parent_node_type;
  }

  private getAgentVersions(callBackFn?) {
    if (!this.workflowId) {
      return;
    }
    this.appAgentRepoServ.getAgentVersionList(this.workflowId).then(
      (res: any) => {
        const {version_list} = res || {};
        this.historyVersionList = version_list;
        this.setReleaseManageTab();
        if (callBackFn) {
          callBackFn();
        }
      },
      () => {
        this.historyVersionList = [];
        this.setReleaseManageTab();
        if (callBackFn) {
          callBackFn();
        }
      },
    );
  }

  private getFlowVersionsFn(callBackFn?) {
    if (!this.workflowId) {
      return;
    }
    this.appAgentRepoServ.getFlowVersion(this.workflowId).then(
      (res: any) => {
        const {version_list} = res || {};
        this.historyVersionList = version_list;
        this.setReleaseManageTab();
        if (callBackFn) {
          callBackFn();
        }
      },
      () => {
        this.historyVersionList = [];
        this.setReleaseManageTab();
        if (callBackFn) {
          callBackFn();
        }
      },
    );
  }

  tabActiveChange(id: string) {
    this.curActiveTabId = id;
  }

  isHeightNormal(val: INodeHeightUpdate) {
    return this.flowHelperServ.isHeightNormal(val, this.localScale);
  }

  private adjustTopForNodeModal() {
    if (!this.nodeModalTop) {
      this.nodeModalTop = this.getContainerclientTop();
    }

    this.flowHelperServ.adjustTopForNodeModal(this.nodeModalTop, this.renderer);
  }

  private adjustZIndexForNodeModal() {
    if (this.showSingleTest) {
      const exeModal = document.querySelector('flow-node-exe') as HTMLElement;
      const exeZ = this.getZIndex(exeModal);
      const modal = document.getElementById('flow-common-half-modal');
      const currZ = this.getZIndex(modal);
      this.renderer.setStyle(modal, 'right', `0px`);
      if (currZ < exeZ) {
        this.renderer.setStyle(modal, 'z-index', `${exeZ + 1}`);
      }
    }
  }

  private getContainerclientTop() {
    const container = document.getElementById('app-flow-container');
    return container?.getBoundingClientRect()?.top ?? 113;
  }

  ngOnInit(): void {
    if (this.windowResizeService.getSafeAreaEnv()) {
      this.windowResizeService.getSafeAreaEnv().onChange((e: any) => {
        this.HWCloudTopHeight = e.detail.top;
      });
    }

    this.saveStatusMap = new Map();
    // 初始化试运行校验状态
    this.appFlowServ.testRunVerificationError = false;
    // 初始化的地方
    this.resizeSub = this.windowResizeService
      .getWindowWidth()
      .subscribe((width) => {
        this.windowWidth = width;
      });
    this.subNodeActions();
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.appFlowServ
      .modeOfIntentNodeUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((modes) => {
        this.intentModesMap = modes;
      });
    this.appFlowServ
      .exceptionPortUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data) => {
        const {nodeId, operate} = data ?? {};
        if (nodeId) {
          const node = this?.graph?.getCellById(
            nodeId,
          ) as Node<NodeProperties>;
          if (!node) {
            return;
          }
          if (operate === 'add') {
            this.addExceptionPort(node);
          } else if (operate === 'remove') {
            this.removeExceptionPort(node);
          }
        }
      });
    this.appFlowServ
      .nodeHeightMapUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((val) => {
        // 收起节点卡片(即val.isExpand等于false) 或 isResetNodeHeightMap为true时，重置nodeHeightMap
        if (!val?.isExpand || this.isResetNodeHeightMap) {
          this.nodeHeightMap.clear();
          this.isResetNodeHeightMap = false;
        }

        if (this.isHeightNormal(val) && val?.nodeType !== 'Loop') {
          const node = this?.graph?.getCellById(
            val?.id,
          ) as Node<NodeProperties>;

          if (node) {
            const scale = Number(this.localScale) / 100;
            const size = node.size();

            const prevHeight = this.nodeHeightMap.get(val.id) || 0;
            // 只有当订阅到的新高度比之前的大时，才执行node.size
            if (val.height > prevHeight) {
              node.size(size.width, val.height / scale);
              this.nodeHeightMap.set(val.id, val.height);
            }
            if (MULTI_PORT_NODE.includes(val.nodeType)) {
              this.handleMultiPortNodeExpand(node, val);
            }
          }
        }
      });
    this.modelManagementService
      .getAvailableModelList({with_router: true})
      .then((res) => {
        this.availableModelList = res.data.map((item: any) => ({
          ...item,
          merge_name: item.model_name,
          model_name: item.model_name,
          model_nickname: item.model_name,
          model_type: item.model_type,
          model_deployment_id: item.id,
          model_provider: item.logo,
          is_connecting: true,
          api_type: item.interface_protocol,
        }));
        if (!this.availableModelList.length) {
          MessageComponent.showError(this.i18n.transform('model_nodata_1'));
        }
        this.appFlowServ.setModelList(this.availableModelList);
      })
      .catch((error: any) => {
        handleCommonReqError(error);
      });

    this.modelManagementService
      .getAvailableModelList({
        intent_recognition: true,
        publish_status: 'online',
        groupby: 'provider',
      })
      .then((res) => {
        res.data.forEach((item) => {
          if (item.id === 'intent_recognition' && item.models.length > 0) {
            this.intentRecommendModel = item.models[0];
          }
        });
      })
      .catch((error: any) => {
        handleCommonReqError(error);
      });

    // 延迟500是为了在点击确定按钮时，同时触发更新视图的操作，接口不会重复下发
    this.nodeServ
      .updateViewUpdate$()
      .pipe(takeUntil(this.destroy$), delay(500))
      .subscribe(() => {
        if (this.updateFlowDataLoading) {
          return;
        }
        this.appFlowServ.setNodeNameChange({id: this.nodeConfigNodeInfo.id, name: this.nodeConfigNodeInfo.name});
        this.updateFlowData();
      });
    if (this.isAfterCreatePlugin) {
      this.afterCreatePlugin(this.AfterCreatePluginInfo.pluginId);
    }

    if (this.isAfterCreateAgentPlugin) {
      this.afterCreateAgentPlugin(this.AfterCreateAgentPluginInfo);
    }

    this.route.queryParams.subscribe((params) => {
      if (params && params[mapKeys.version_id]) {
        this.agentBuilderVersionId = params[mapKeys.version_id];
      }
      if (params && params[mapKeys.version_name]) {
        this.agentBuilderVersionName = params[mapKeys.version_name];
      }
    });

    if (this.agentBuilderVersionId && this.agentBuilderVersionName) {
      this.agentDataServe.setRollbackId({
        version_id: this.agentBuilderVersionId,
        version_name: this.agentBuilderVersionName,
        isFlowReadonly: true,
      });
    }

    // 节点抽屉关闭并触发保存时候
    this.appFlowServ.nodeModalCloseMonitor$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (nodeData: any) => {
        if (this.type !== 'multi' && nodeData?.id && !this.isFlowReadonly) {
          this.saveStatusMap.set(nodeData?.id, true);
        }
      })

    this.appFlowServ
      .nodeSaveMonitor$()
      .pipe(debounceTime(200), takeUntil(this.destroy$))
      .subscribe(async (ref: any) => {
        // 工作流只读，跳过
        if (this.isFlowReadonly) {
          return;
        }
        // 没有节点值，跳过
        if (!ref?.nodeData) {
          return;
        }
        let {nodeData = {}, nodeInfo = {}} = ref || {};

        // 保存
        this.exceptionBranchHandler(nodeData);
        nodeData = NodeUtils.traversalNodeSource(nodeData);
        this.nodeServ.setIsConfirmLoading(true);
        this.isResetNodeHeightMap = true;
        // 高级意图节点与其容器节点的连接线是异步创建的，避免多次调用updateFlowData导致数据不一致
        let isSkipUpdateFlow = false;
        // 高级模式
        if (FlowUtils.isAdvancedModeNew(nodeData)) {
          isSkipUpdateFlow = true;
          nodeData.name = FlowUtils.uniqueIntentName(
            this.graph,
            nodeData,
            true,
          );
          // 切换意图包后，需要将对应的容器节点的dsl恢复成默认值
          const uuid = nodeData.id.split('_')[1];
          const containerNodeId = `node_intent_container_${uuid}`;
          const isContainerNode = this.graph.getCellById(containerNodeId);
          this.createIntentContainerNode(nodeData.id);
          let bodyParams;
          setTimeout(async () => {
            if (isContainerNode) {
              // 若已存在意图动作配置节点，需异步更新DSL
              bodyParams = FlowUtils.updateContainerNodeDsl(
                this.graph,
                this.workflowDetail,
                nodeData,
                containerNodeId,
                this.getNodeInfoById.bind(this),
                this.appFlowServ,
              );
            }
            this.handleAdvancedIntentConns(nodeData.id);
            this.updateRef();
            await this.updateFlowData(
              {
                isDrag: false,
                nodeInfo: nodeData,
                successCb: () => {
                  if (isContainerNode) {
                    this.appFlowServ.setAppRefs(this.ref_workflows);
                    FlowUtils.syncContainerInfoToGraph(
                      this.graph,
                      bodyParams,
                      containerNodeId,
                    );
                  }
                },
                faildCb: () => {

                }
              },
              bodyParams,
            );
          });
        }
        // 普通模式
        if (FlowUtils.isNormalMode(nodeData)) {
          nodeData.name = FlowUtils.uniqueIntentName(
            this.graph,
            nodeData,
            false,
          );
          this.deleteContainerNode(nodeData.id, false);
        }

        if (nodeData?.id === 'node_start') {
          this.isStartNodeBtnClicked = true;
        }
        this.checkRefChangeAndUpdateNode(nodeInfo, nodeData);

        // 更新画布上的node
        if (nodeData?.type === 'SubController') {
          const exceedsList = this.appFlowServ.judgeExceedsSubController(this.graph)
          if (exceedsList.length) {
            const exceedsStr = exceedsList.join(',')
            MessageComponent.showError(`绑定子智能体【${exceedsStr}】达到最大深度限制，请删除后重试`, 5000);
            return
          }
          const controller_node: any = this.workflowDetail.details.nodes.find(contr_item => contr_item.type === 'Controller');
          controller_node.configs?.agents?.forEach(ag => {
            if (ag.node_id === nodeData.id) {
              ag.configs.intent = (nodeData as IControllerNode).configs.intent;
            }
          });
          this.updateAgentsNodeData(controller_node);
          this.updateAgentsNodeData(nodeData);

        } else {
          this.updateNodeData(nodeData);
        }
        try {
          if (isSkipUpdateFlow) {
            return;
          }
          // 在multi Agent中，根据控制器节点绑定的工作流列表，创建树形结构
          if (this.type === 'multi' && nodeData.type === 'Controller') {
            if (nodeData.type === 'Controller') {
              const {workflows, agents} = (nodeData as IControllerNode)
                .configs;
              this.createMultiAgentTree(workflows, agents);
            }
          }
          // 更新节点数据
          await this.updateFlowData({
            isDrag: false,
            nodeInfo: nodeData,
            successCb: () => {
              if (
                nodeData.type === 'ParamExtraction' ||
                nodeData.type === 'Card'
              ) {
                this.appFlowServ.setAppRefs(this.ref_workflows);
                FlowUtils.syncParamExtractionInfoToGraph(
                  this.graph,
                  this.workflowDetail,
                  nodeData.id,
                );
                this.checkResNodesUpdate();
              }
            },
          });
        } finally {
          this.nodeServ.setIsConfirmLoading(false);
          if (this.type !== 'multi' && nodeData?.id) {
            setTimeout(() => {
              this.saveStatusMap.set(nodeData?.id, false);
            });
          }
          if (this.isFlowValidated) {
            // 优化交互：当点击节点配置的确定按钮后，再次调用validate接口，刷新工作流节点的校验状态
            await this.getFlowValidateRes(false);
          }
          if (nodeData.type === 'Controller') {
            this.checkResNodesUpdate();
          }
        }
      });
  }

  /** 创建插件后 */
  public afterCreatePlugin(pluginId) {
    const modalRef = this.nzModal.create({
      nzContent: `<div>${this.i18n.transform('plug_created_success')}</div><div style="margin-top: 8px">${this.i18n.transform('pluginaddensure_535')}</div>`,
      nzWidth: '400px',
      nzMaskClosable: true,
      nzClosable: true,
      nzFooter: [
        {
          label: this.i18n.transform('cancel'),
          onClick: () => modalRef.destroy(),
        },
        {
          label: this.i18n.transform('ok'),
          type: 'primary',
          onClick: () => {
            this.addAllToolsByPluginId(pluginId);
            modalRef.destroy();
          },
        },
      ],
    });
  }

  /** 创建卡片后 */
  public afterCreateCard(afterCreateCardInfo) {
    if (this.afterCreateCardInfo.cardId) {
      const modalRef = this.nzModal.create({
        nzContent: `<div>${this.i18n.transform('editcardmodal_82')}</div><div style="margin-top: 8px">${this.i18n.transform('editcardmodal_1')}</div>`,
        nzWidth: '400px',
        nzMaskClosable: true,
        nzClosable: true,
        nzFooter: [
          {
            label: this.i18n.transform('cancel'),
            onClick: () => modalRef.destroy(),
          },
          {
            label: this.i18n.transform('ok'),
            type: 'primary',
            onClick: () => {
              this.addCardByCardId(
                this.afterCreateCardInfo.cardId,
                this.afterCreateCardInfo.agentNode,
              );
              this.putCardModel(this.afterCreateCardInfo.agentNode);
              modalRef.destroy();
            },
          },
        ],
      });
    } else {
      this.tiMessage.error(this.i18n.transform('editcardmodal_2'));
      setTimeout(() => {
        this.putCardModel(this.afterCreateCardInfo.agentNode);
      });
    }
  }

  /** 创建agent插件后 */
  public afterCreateAgentPlugin(AfterCreateAgentPluginInfo) {
    const modalRef = this.nzModal.create({
      nzContent: `<div>${this.i18n.transform('plug_created_success')}</div><div style="margin-top: 8px">${this.i18n.transform('flowcomponent_616')}</div>`,
      nzWidth: '400px',
      nzMaskClosable: true,
      nzClosable: true,
      nzFooter: [
        {
          label: this.i18n.transform('cancel'),
          onClick: () => modalRef.destroy(),
        },
        {
          label: this.i18n.transform('ok'),
          type: 'primary',
          onClick: () => {
            this.addAllToolsToAgentByPluginId(
              this.AfterCreateAgentPluginInfo.agentNode,
              this.AfterCreateAgentPluginInfo.pluginId,
            );
            modalRef.destroy();
          },
        },
      ],
    });
  }

  /**
   * 根据插件id，添加插件下的所有工具
   * @param pluginId
   */
  public addAllToolsByPluginId(pluginId: string) {
    if (!pluginId) {
      return;
    }
    this.appPluginRepoServ.getPluginById(pluginId).then((res) => {
      const plugin = res.data;
      plugin?.request_info?.tool_info?.forEach((tool) => {
        const toolNodeInfo = this.buildToolNodeInfo(plugin, tool);
        const apiNodeData = this.appFlowServ.plugin2ApiNode(toolNodeInfo);
        this.addActionNode(apiNodeData);
        this.debounceSetMiniMap();
      });
      this.updateFlowData({
        successCb: () => {
          this.appFlowServ.setRefreshFlag(true);
          const list = this.workflowDetail.workflow_details.nodes.filter(
            (node) => {
              return node.type === 'Plugin';
            },
          );
          this.appFlowServ.setPluginList(list);
          MessageComponent.showSuccess(
            this.i18n.transform('plugin_added_successfully', {
              pluginName: removeHTMLTag(plugin.plugin_display_name),
            }),
            3000,
          );
        },
      });
    });
  }

  addCardByCardId(cardId: string, nodeId: string) {
    // 添加创建的卡片
    const cardNode = this.workflowDetail.workflow_details.nodes.find(
      (item: any) => {
        return item.id === nodeId;
      },
    );
    if (cardNode) {
      (cardNode as ICardNode).configs.createCardId = cardId;
    }
  }

  putCardModel(nodeId: string) {
    // 打开卡片
    const node = this.graph.getCellById(nodeId);
    this.syncParamExtractionInfoToGraph(
      this.graph,
      this.workflowDetail,
      nodeId,
    );
    setTimeout(() => {
      this.graph.trigger('node:click', {node: node});
    });
  }

  /**
   * 根据插件id，给agent添加插件下的所有工具
   * @param pluginId
   * @param agentNodeId
   */
  public addAllToolsToAgentByPluginId(agentNodeId: string, pluginId: string) {
    if (!pluginId) {
      return;
    }
    this.appPluginRepoServ.getPluginById(pluginId).then((res) => {
      const plugin = res.data;
      const toolInfo = plugin?.request_info?.tool_info ?? [];
      const toolInfoList = toolInfo.map((v) => {
        return {
          description: v.tool_desc,
          id: pluginId,
          name: v.tool_chinese_name,
          tool_id: v.tool_id,
          type: plugin.type,
        };
      });
      const node = this.graph.getCellById(agentNodeId);
      if (!toolInfoList.length) {
        MessageComponent.showError(
          this.i18n.transform('flowcomponent_617'),
          3000,
        );
        this.graph.trigger('node:click', {node: node});
        return;
      }
      // 把插件下的工具都添加到agent节点的插件里
      let workflowDetailParams = cloneDeep(this.workflowDetail);
      let agentNode: any = workflowDetailParams.workflow_details.nodes.find(
        (node) => node.id === agentNodeId,
      );
      const plugins = agentNode?.configs?.plugins || [];
      const allTools = [...plugins, ...toolInfoList];
      agentNode.configs.plugins = Array.from(
        new Map(allTools.map((item) => [item.tool_id, item])).values(),
      );
      this.updateFlowData(
        {
          successCb: () => {
            // 添加成功，更新画布数据，打开agent抽屉
            this.syncParamExtractionInfoToGraph(
              this.graph,
              this.workflowDetail,
              agentNodeId,
            );
            setTimeout(() => {
              this.graph.trigger('node:click', {node: node});
            });
          },
          faildCb: () => {
            // 失败也打开agent抽屉
            this.graph.trigger('node:click', {node: node});
          },
        },
        workflowDetailParams,
      );
    });
  }

  syncParamExtractionInfoToGraph(
    graph: Graph,
    bodyParams: IWorkflow,
    nodeId: string,
  ) {
    const paramExtractionDslInfo: any = bodyParams.workflow_details.nodes.find(
      (node) => node.id === nodeId,
    );

    if (!paramExtractionDslInfo) {
      return;
    }

    // 获取容器节点最新的dsl数据
    const {configs, inputs, outputs} = paramExtractionDslInfo;
    // 获取X6画布上的容器节点
    const paramExtractionNode = graph.getCellById(nodeId);
    const nodeInfo = paramExtractionNode.data.ngArguments.nodeInfo;
    nodeInfo.configs = configs;
  }

  /**
   构建插件节点信息
   */
  public buildToolNodeInfo(plugin, tool) {
    return {
      ...tool,
      plugin_chinese_name: plugin.plugin_chinese_name,
      id: plugin.plugin_id,
      intf_type: plugin.intf_type.find(
        (toolIntfType) => toolIntfType.tool_id === tool.tool_id,
      ).intf_type,
      input_schema: plugin.input_schema.find(
        (toolInputSchema) => toolInputSchema.tool_id === tool.tool_id,
      ).input_schema,
      output_schema: plugin.output_schema.find(
        (toolOutputSchema) => toolOutputSchema.tool_id === tool.tool_id,
      ).output_schema,
      type: plugin.type,
    };
  }

  get statusBarInfo() {
    let backUpInfo;
    backUpInfo =
      this.type === 'workflow'
        ? this.appFlowServ.StatusMap.get(this.workflowDetail?.status)
        : this.appFlowServ.AgentStatusMap.get(this.workflowDetail?.status);
    return {
      icon: backUpInfo?.icon
        ? backUpInfo?.icon
        : cdnAssetUrl('assets/agent-center/flow/loading.gif'),
      text: backUpInfo?.text,
    };
  }

  //获取是否是 ‘有尚未发布的修改’ 的状态
  get releaseStatusBar() {
    if (
      this.workflowDetail?.status === 1 ||
      this.workflowDetail?.status === 'published'
    ) {
      return (
        this.workflowDetail?.publish_time < this.workflowDetail?.update_time
      );
    }
    return false;
  }

  ngAfterViewInit(): void {
    this.init();
    this.liteLicenseAlertTopHeight = this.windowResizeService.getLiteAlertTopHeight();
    if (
      !window.localStorage.getItem('accelerator_key_guide') &&
      this.type !== 'multi'
    ) {
      this.accelerator_key_guide_visible.show = true;

    }
  }

  ngOnDestroy(): void {
    this.helpCenterService.hideHelpPanel();
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.resizeSub.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
    this.closeNodeConfigDrawer();
    this.closeGlobalConfigDrawer();
    this.flowHelperServ.cleanupAppFlowService(
      this.appFlowServ,
      this.agentDataServe,
      this.nodeServ,
      this.fb,
    );
    this.nodeRegisterService.unregisterComponents();
    document.title = this.originTitle;
  }

  get publishBtnText() {
    if (this.historyVersionList.length > 0) {
      return this.i18n.transform('update_version');
    }

    return this.i18n.transform('submit_version');
  }

  public async exitViewHistory() {
    this.agentDataServe.setRollbackId({
      version_id: '',
      isFlowReadonly: false,
    });
    this.showHistoryModal = false;
    this.versionId = ''; // 退出预览态后，查询草稿态的工作流信息，调用的get接口不传入versionId
    await this.initAppRefs();
    this.initWorkflowData();
  }

  public async init() {
    // 初始化的地方
    this.route.queryParams.subscribe(async (params) => {
      let {id, versionId, type, versionName, from, workflowId, fromShare} =
        params;
      if (from && from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
      if (from && (from === 'overview' || from === 'experience-creation')) {
        this.isFromOverview = true;
      }
      if (from && from === 'featured') {
        this.isFromFeatured = true;
      }
      this.type = type || 'workflow';
      this.cdr.detectChanges();
      if (id) {
        this.workflowId = id;
      }
      if (workflowId) {
        this.orginWorkflowId = workflowId;
      }
      this.configHeaderTabs[0].title = this.i18n.transform(
        type === 'multi' ? 'multi_agent_config' : 'workflow_config',
      );
      this.fromShare = fromShare === 'true';
      this.initTab();
      this.initGraph();
      this.setGraphHistory();

      if (versionId) {
        this.versionId = versionId;
        if (!versionName) {
          let res;
          if (type === 'multi') {
            res = await this.appAgentRepoServ.getAgentVersionList(
              this.workflowId,
            );
          } else {
            res = await this.appAgentRepoServ.getFlowVersion(this.workflowId);
          }
          const {version_list} = res || {};
          const version = version_list.find((v) => {
            return v.version_id === versionId;
          });
          if (version) {
            versionName = version.version_name;
          }
        }
        this.versionName = versionName ?? '';
        this.setFlowReadonly(true);
      }
      if (!this.fromShare) {
        await this.initAppRefs();
      }
      this.initWorkflowData();
      if (!this.fromShare) {
        if (type === 'multi') {
          this.getAgentVersions();
        } else {
          this.getFlowVersionsFn();
        }
      }
      this.cdr.detectChanges();
    });
  }

  public initTab() {
    this.route.queryParams.subscribe((params) => {
      this.workflow_type = this.type === 'multi' ? 'controller' : 'chat';
      if (params.tabId && params.tabId === this.configHeaderTabs[1].id) {
        this.configHeaderTabs[0].active = false;
        this.configHeaderTabs[1].active = true;
        this.configHeaderTabs[1].disabled = false;
        this.configTabActiveChange(this.configHeaderTabs[1].id);
      }
    });
  }

  public initLoop(ids: string[]) {
    this.flowHelperServ.initLoop(ids, this.graph);
  }

  public subNodeActions() {
    this.appFlowServ
      .nodeActionUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (action) => {
        if (action) {
          if (action.type === 'delete') {
            this.deleteNode(action.id);
          }

          if (action.type === 'copy') {
            this.copyNodeById(action.id);
          }

          if (action.type === 'update') {
            this.openUpdateNodeNameModal(action.id);
          }

          if (action.type === 'test') {
            this.coloseAllWindow();
            MaskComponent.show();
            setTimeout(async () => {
              MaskComponent.hide();
              this.isStartCheckErrorWorkFlow = true;
              await this.checkErrorWorkFlow(true, action.id);
            }, 2000);
          }

          if (action.type === 'connect_end') {
            this.linkToEndNode(action.id);
          }
        }
      });
    // 调试详情
    this.appFlowServ
      .nodeTestInfoActionUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((action) => {
        if (action && action.id) {
          if (action.tokenDataFrom === 'nodeExe') {
            this.openSingleTestModal(action.id, true);
          } else {
            this.openLogHalfmodal([], action.id);
          }
        }
      });
  }

  public openSingleTestModal(nodeId: string, isInfo?: boolean) {
    if (this.showNodeConfigDrawer) {
      const exeModal = document.querySelector(
        'flow-node-exe',
      ) as HTMLDivElement;
      const nodeConfigDrawer = document.querySelector('nz-drawer') as HTMLDivElement;

      if (exeModal && nodeConfigDrawer) {
        const drawerZ = this.getZIndex(nodeConfigDrawer);
        const exeModalZ = this.getZIndex(exeModal);

        if (exeModalZ < drawerZ) {
          exeModal.style.zIndex = `${drawerZ + 1}`;
        }
      }
    }

    this.currTestNodeId = nodeId;
    const node = this.graph?.getCellById(nodeId);
    const {data} = node.toJSON();
    const nodeInfo = data.ngArguments.nodeInfo as IsolatedTestableNode;
    delete (nodeInfo as any)?.nodeInfo;
    this.currTestNodeInfo = nodeInfo;
    this.nodeExeConversationId = uuidV4();
    this.cdr.detectChanges();
    if (!isInfo) {
      this.appFlowServ.setTokenData({});
    }
    this.showSingleTest = true;
    this.appFlowServ.setNodeClicked(EHalfmodalType.SINGLE_TEST);
  }

  public onCloseSingleTestModal() {
    this.editCodeModal = false;
    const exeModal = document.querySelector('flow-node-exe') as HTMLDivElement;
    if (exeModal) {
      exeModal.style.zIndex = 'auto';
    }

    this.showSingleTest = false;
    this.cdr.detectChanges();
  }

  public onPageBack(): void {
    if (this.isFromFeatured) {
      this.router.navigate(['/home/app-library']);
      return;
    }
    if (this.isFromOverview) {
      this.router.navigate(['/home/overview']);
      return;
    }
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space'], {
        state: {currentAppType: this.type === 'multi' ? 'multi' : 'workflow'},
      });
      return;
    }
    if (this.isFromEditFlow) {
      window.history.go(-2);
      setTimeout(() => {
        window.location.reload();
      }, 0);
      return;
    }

    if (this.type === 'multi') {
      this.ppServ.goHome('multi', TabIndex.MULTI_AGENT);
    } else {
      this.ppServ.goHome('workflow', TabIndex.WORKFLOW);
    }
  }

  openUpdateNodeNameModal(id: string) {
    const node = this.graph?.getCellById(id);

    if (node) {
      const {data} = node.toJSON();
      const nodeInfo = data.ngArguments.nodeInfo as NodeInfo;

      if ((nodeInfo as any)?.nodeInfo) {
        delete (nodeInfo as any).nodeInfo;
      }
      this.isShowRename = true;
      const modalRef = this.nzModal.create({
        nzContent: UpdateNodeNameModalComponent,
        nzWidth: '520px',
        nzFooter: null,
        nzMaskClosable: false,
        nzClosable: true,
      });
      Object.assign(modalRef.componentInstance, {
        name: nodeInfo.name,
        names: FlowUtils.getGraphNodeNames(this.graph),
      });
      modalRef.afterClose.subscribe((result) => {
        if (result) {
          nodeInfo.name = removeHTMLTag(result);
          if (node?.data?.ngArguments?.nodeInfo) {
            node.data.ngArguments.nodeInfo.name = nodeInfo.name;
            node.data.ngArguments.nodeInfo.configs.isDefaultName = false;
          }
          this.appFlowServ.setNodeNameChange({id: nodeInfo.id, name: nodeInfo.name});
          this.updateFlowData();
        }
      });
    }
  }

  public saveTitle(title: string): void {
    this.workflowDetail.name = title;
    this.save();
  }

  /** 点击触发器的添加按钮 */
  public openTriggerHalfmodal(his, agentType): void {
    if (this.isFlowReadonly) {
      return;
    }
    const showCallMethod = agentType === 'workflow';
    const modalRef = this.nzModal.create({
      nzContent: TriggerHalfmodalComponent,
      nzWidth: '600px',
      nzMaskClosable: false,
      nzData:{
        historyTriggers:this.triggerAdded.list,
        edit_data:his ? [his] : [],
        showCallMethod:showCallMethod
      }
    });
  }

  public changeCollapsedState(configInfo: any) {
    try {
      const collapsed = configInfo;
      configInfo = !collapsed;
      this.cdr.markForCheck();
    } catch {
    }
  }

  public clickShowTrigger(): void {
    this.coloseAllWindow();
    this.showTriggerModal = true;
    this.appFlowServ.setNodeClicked(EHalfmodalType.TRIGGER);
  }

  public closeGlobalConfigDrawer(): void {
    this.showGlobalConfigDrawer = false;
  }

  public closeLogDrawer(): void {
    this.showLogDrawer = false;
  }

  public closeNodeConfigDrawer(): void {
    this.showNodeConfigDrawer = false;
    this.halfModalRef?.close()
  }

  public deleteTrigger(info: any) {
    this.appFlowRepoServ
      .deleteOneTrigger(this.workflowId, info.trigger_id)
      .then(() => {
        const index = this.triggerAdded.list.findIndex(
          (item: any) => item.trigger_id === info.trigger_id,
        );
        if (index > -1) {
          this.triggerAdded.list.splice(index, 1);
        }
        MessageComponent.showSuccess(
          this.i18n.transform('successfully_deleted_trigger'),
          3000,
        );
      });
  }

  public coloseAllWindow(exict?: Array<any>) {
    if (!(exict?.indexOf('flow-common-half-modal') >= 0)) {
      this.showNodeConfigDrawer = false;
    }
    this.showGlobalConfigDrawer = false;
    this.showPluginDrawer = false;
    this.showChildFlowDrawer = false;
    this.showMcpServiceDrawer = false;
    if (!(exict?.indexOf('flow-log-half-modal') >= 0)) {
      this.showLogDrawer = false;
    }
    if (!(exict?.indexOf('flow-log-half-modal') >= 0)) {
      this.showLogDrawer = false;
    }

    if (!(exict?.indexOf('checkErrorWorkflowHalfModalRef') >= 0)) {
      this.checkErrorWorkflowHalfModalRef = false;
    }
    if (!(exict?.indexOf('runTestHalfModel') >= 0)) {
      this.showRunModal = false;
    }
    this.showHistoryModal = false;
    this.showSingleTest = false;
    this.showLogModal = false;
    this.editCodeModal = false;
    this.flowHelperServ.adjustRightForNodeModal('', 'right');
  }

  // 工作流全局配置
  public openConfigHalfmodal() {
    this.coloseAllWindow();
    this.globalConfigDrawerWidth =
      document.querySelector('body').offsetWidth > 1920 ? '600px' : '480px';

    if (this.type === 'multi') {
      this.globalConfigInputs = this.workflowDetail.details.inputs;
      this.globalConfigVariables = this.workflowDetail.details.global_variables;
      this.globalConfigMemoryConfig = this.workflowDetail.memory_config;
      this.globalConfigEnvironment = this.workflowDetail.details.environment || '';
      this.globalConfigFlowId = this.workflowId;
    } else {
      this.globalConfigInputs = (this.workflowDetail.workflow_details.configs as any)?.inputs || [];
      this.globalConfigVariables = (this.workflowDetail.workflow_details.configs as any)?.global_variables || [];
    }

    this.showGlobalConfigDrawer = true;
    this.adjustTopForNodeModal();
    this.adjustZIndexForNodeModal();
    this.appFlowServ.setNodeClicked(EHalfmodalType.GLOBAL);
  }

  public onGlobalConfigsChange(configs: IFlowConfigs): void {
    FlowUtils.updateRefsAfterConfigsChange(
      configs,
      this.workflowDetail.workflow_details.configs,
      this.graph,
      this.updateRefType,
      this,
    );
    if (configs.default_model && configs.default_model_switch) {
      const {model_deployment_id, model_name, model_type, model} =
        configs.default_model;
      const nodes = this.graph
        .getNodes()
        ?.map(FlowUtils.getNodeDSLFromRaw)
        ?.filter((node) => LLM_LIKE_NODES.includes(node.type));
      if (nodes.length) {
        nodes.forEach((node) => {
          if (
            node.type === 'IntentDetection' ||
            node.type === 'ComplexIntentDetection'
          ) {
            (node as IIntentNode).configs.llm.model = {
              model_deployment_id,
              model_name,
              model_type,
              model,
            };
          } else if (node.type === 'LLM' || node.type === 'ParamExtraction') {
            (node as ILLMNode).configs.model = {
              model_deployment_id,
              model_name,
              model_type,
              model,
            };
          }
        });
      }
    }
    this.workflowDetail.workflow_details.configs = configs;
    this.updateFlowData({
      isDrag: false,
      successCb: () => {
        this.showGlobalConfigDrawer = false;
        this.envList = [];
        if (
          this.workflowDetail.workflow_details.configs
            ?.environment &&
          typeof this.workflowDetail.workflow_details.configs
            ?.environment === 'string'
        ) {
          this.envVariablesManagement
            .getEnvVariablesDetail(
              this.workflowDetail.workflow_details.configs
                .environment,
            )
            .then((res) => {
              this.envList = res?.variables;
              if (this.type !== 'multi') {
                this.updateOutputsMap();
              }
            });
        }
      },
    });
  }

  onGlobalConfigsMultiChange(configs: {
    inputs: IWorkflowField[];
    global_variables: IWorkflowField[];
    memory_config: IMemoryLibBaseInfo;
    environment: string;
  }) {
    this.workflowDetail.details.inputs = configs.inputs;
    this.workflowDetail.details.global_variables =
      configs.global_variables;
    this.workflowDetail.details.environment = configs.environment;
    if (this.configServ.isSupportUserPersona()) {
      this.workflowDetail.memory_config = configs.memory_config;
    }
    this.updateFlowData({
      isDrag: false,
      successCb: () => {
        this.showGlobalConfigDrawer = false;
      },
    });
  }

  public async openLogHalfmodal(exict?: Array<any>, openNodeId?: string) {
    this.coloseAllWindow(exict);
    if (this.workflow_type === 'task') {
      this.showRunModal = false;
    }
    this.logConversationId = this.conversationId;

    this.showLogIsShowLog = this.showLogModal;
    this.showLogGraph = this.graph;
    this.showLogWorkflowDetail = this.workflowDetail;
    this.showLogOpenNodeId = openNodeId ?? '';

    this.showLogDrawer = true;
    this.adjustTopForNodeModal();
    this.flowHelperServ.adjustRightForNodeModal('flow-log-half-modal', 'right');
  }

  /** 打开试运行的半屏弹窗，并触发validate接口进行工作流校验 */
  public async openRunHalfmodal() {
    if (this.testBtnLoading) {
      return;
    }
    this.coloseAllWindow();
    this.testBtnLoading = true;
    setTimeout(async () => {
      this.testBtnLoading = false;
      this.appFlowServ.setSaveNodeTestInfo(null);
      if (this.type === 'multi') {
        this.showRunModal = true;
      } else {
        // 预览状态下，不会调用校验接口
        if (this.isFlowReadonly) {
          this.showRunModal = true;
        } else {
          this.isStartCheckErrorWorkFlow = true;
          await this.checkErrorWorkFlow(true);
        }
      }
      this.appFlowServ.setRunBtnClicked(true);
      this.appFlowServ.setNodeClicked(EHalfmodalType.TEST_RUN);
      this.appFlowServ.setTokenData({}); // 置空画布对应节点的运行状态。避免同时出现"节点错误"和"运行状态"卡片
      this.nodeServ.setCurrSelectedNode('');
    }, 2000);
  }

  public save(): void {
    this.updateFlowData();
  }

  public showWorkflowData(workflow: IWorkflowInfo) {
    const {nodes, edges, layouts} = workflow.workflow_details;
    const nodeInfo = FlowUtils.processFetchedNodes(nodes, layouts, this.type);
    const edgeInfo = FlowUtils.processFetchedEdgeData(edges);
    this.initPresetTmpl([...nodeInfo, ...edgeInfo], true);
  }

  public initGraph() {
    this.container = this.nativeElementRef.querySelector(
      '#app-flow-container',
    ) as HTMLDivElement;

    this.nodeRegisterService.registerComponents(this.injector);
    this.graph = this.appFlowServ.getNewGraph(
      this.container,
      this.type === 'multi',
    );

    this.appFlowServ.setGraph(this.graph);
    FlowEventUtils.addGraphEventListeners(this);
    this.setSelection();
    if (isDevMode()) {
      window.__x6_instances__ = [];
      window.__x6_instances__.push(this.graph);
    }
  }

  setSelection() {
    this.graph.use(
      new Selection({
        enabled: true,
        multiple: true,
        rubberband: true,
        movable: true,
        showNodeSelectionBox: false,
        multipleSelectionModifiers: 'shift',
        filter: (cell) => cell.isNode(),
      }),
    );
    //默认手模式，关闭框选
    this.graph.disableRubberband();
    this.graph.enablePanning();
  }

  public allowDrop(e: MouseEvent) {
    e.preventDefault();
  }

  /** 定位到画布中间 */
  public onCenter() {
    this.graph.centerContent();
  }

  public toggleModeTip() {
    this.isShowModeTip.show = !this.isShowModeTip.show;
  }

  public toggleAcceleratorKeyTip(popover: any) {
    if (this.isShowAcceleratorKeyTip.show) {
      this.isShowAcceleratorKeyTip.show = false;
      popover.hide();
    } else {
      this.confirmGuide();
      this.isShowAcceleratorKeyTip.show = true;
      popover.show();
    }
  }

  public changeDragMode(mode: string) {
    if (mode === DragMode.POINTER) {
      this.graph.enableRubberband();
      this.updatePanningModifier('space');
      this.graph.disablePanning();
    } else {
      this.graph.disableRubberband();
      this.updatePanningModifier(null);
      this.graph.enablePanning();
    }
    this.dragMode = mode;
    this.isShowModeTip.show = false
  }

  /**
   * 修改画布拖拽的修饰键
   * @param newModifier
   */
  updatePanningModifier(newModifier: string | null) {
    this.graph.options.panning.modifiers = newModifier;
    this.graph.disablePanning();
    this.graph.enablePanning();
  }

  public expandAllSwitch() {
    this.isAllExpand = !this.isAllExpand;
    this.nodeServ.setIsAllExpand(this.isAllExpand);
  }

  /** 放大画布 */
  public addCanvas() {
    this.graph.zoom(0.1);
  }

  /** 缩小画布 */
  public supCanvas() {
    this.graph.zoom(-0.1);
  }

  /** 设置画布history */
  public setGraphHistory() {
    this.graph.use(
      new History({
        enabled: true,
        beforeAddCommand(event: any, args: any) {
          return !args?.options?.ignoreHistory;
        },
      }),
    );
    this.graph.on('history:change', () => {
      this.canUndo = this.graph.canUndo();
      this.canRedo = this.graph.canRedo();
      this.cdr.markForCheck();
    });
  }

  public setMiniMap() {
    const minimapContainer =
      this.nativeElementRef.querySelector('#minimap-container');

    this.flowHelperServ.setMiniMap(minimapContainer, this.graph);
  }

  public onClickShowFlowNodes(e: Event) {
    e.stopPropagation();

    this.showFlowNodesWidget = !this.showFlowNodesWidget;
  }

  debounceSetMiniMap = debounce(this.setMiniMap.bind(this), 200);

  // 初始化画布数据
  public async initWorkflowData() {
    try {
      let value;
      if (this.versionId) {
        value =
          this.type === 'multi'
            ? await this.appAgentRepoServ.rollbackAgentVersion(
              this.workflowId,
              this.versionId,
            )
            : await this.appAgentRepoServ.rollbackFlowVersion(
              this.workflowId,
              this.versionId,
            );
        if (this.type === 'multi') {
          value.workflow_details = value.details;
          value.avatar = value.icon;
        }
      } else if (this.type === 'multi') {
        value = await this.appAgentRepoServ.getMultiAgent(this.workflowId);
        value.workflow_details = value.details;
        value.avatar = value.icon;
      } else {
        value = await this.appFlowRepoServ.getFlow(this.workflowId);
      }
      this.isMultiAgent = value && ['controller', 'chat'].includes(value.type);
      fillAdvancedBranches(
        value.workflow_details.nodes,
        value.workflow_details.edges,
      );
      document.title = value.name;

      const {nodes} = value.workflow_details;
      nodes.sort((a, b) => Number(b.type === 'Loop') - Number(a.type === 'Loop'));
      this.setIntentModesMap(nodes);
      // 更新agents的configs
      value.workflow_details.nodes = this.updateAgentsConfigs(nodes);

      value.workflow_details.nodes = this.checkResNodesValid(value);
      this.appFlowServ.setVersionInfo(value.update_time);
      this.useDataPaintWorkflow(value);
      this.checkResNodesUpdate();
      this.updateAnalyzeTabStatus(!this.workflowDetail.status);
      this.triggerAdded.list = value?.trigger_list ?? [];
      this.appFlowServ.setFlowConfigs(
        this.workflowDetail?.workflow_details?.configs,
      );

      this.envList = [];
      if (
        this.workflowDetail.workflow_details.configs?.environment &&
        typeof this.workflowDetail.workflow_details.configs?.environment ===
        'string'
      ) {
        this.envVariablesManagement
          .getEnvVariablesDetail(
            this.workflowDetail.workflow_details.configs.environment,
          )
          .then((res) => {
            this.envList = res?.variables;
            if (this.type !== 'multi') {
              this.updateOutputsMap();
            }
          });
      } else {
        setTimeout(() => {
          if (this.type !== 'multi') {
            this.updateOutputsMap();
          }
        });
      }

      if (this.ctxServ.user.userId !== this.workflowDetail.creator_id) {
        // 解决不同账号不能编辑工作流的问题
        if (this.configServ.getConfigs().enable_edit_in_workspace === false) {
          this.nodeServ.setIsReadonlyFlow(true);
          this.notUserSelf = true;
          this.graph.options.interacting = false;
        }
      } else {
        if (!this.versionId) {
          // versionId为空时，即URL中不带versionId，设置为可编辑状态
          this.nodeServ.setIsReadonlyFlow(false);
          this.notUserSelf = false;
        }
      }

      if (!value?.update_time) {
        this.updateFlowData();
      }

      this.logModalTop = `${this.getContainerclientTop()}px`;
      document.documentElement.style.setProperty(
        '--modal-top',
        this.logModalTop,
      );
      this.debounceSetMiniMap();
      this.onCenter();
      this.flowZoomToFit();
      this.initLoop(
        value.workflow_details.nodes
          .filter((node) => node.type === 'Loop')
          .map((node) => node.id),
      );
      // 手动触发循环体节点的 node:change:position 事件，自适应布局
      setTimeout(() => {
        this.graph.getNodes().forEach((node) => {
          if (!node.getParent()) return;
          const options = {skipParentHandler: false};
          this.graph.trigger('node:change:position', {node, options});
        });
      });

      if (this.workflowDetail.workflow_details.configs?.nl2workflow_first) {
        setTimeout(() => {
          //nl2workflow首次进去需要布局优化并保存
          this.workflowDetail.workflow_details.configs.nl2workflow_first =
            false;
          this.optimizeLayout(true);
        }, 300);
      }
      setTimeout(() => {
        this.graph.cleanHistory();
      }, 1000);
      if (this.isAfterCreateCard) {
        this.afterCreateCard(this.afterCreateCardInfo);
      }
    } finally {
      this.cdr.detectChanges();
    }
  }

  private useDataPaintWorkflow(flow: IWorkflow) {
    const {type, avatar, workflow_details} = flow;
    this.workflow_type = type || 'chat';
    this.appFlowServ.setWorkflowType(this.workflow_type);
    this.logo = avatar;

    const {nodes, edges, layouts, comments} = workflow_details;
    const nodeInfo = FlowUtils.processFetchedNodes(nodes, layouts, this.type);
    const edgeInfo = FlowUtils.processFetchedEdgeData(edges);
    const commentInfo = FlowUtils.processFetchedComments(comments, layouts, this.type);
    this.initPresetTmpl([...nodeInfo, ...edgeInfo, ...commentInfo], true);

    // 更新连接port的颜色
    const graphEdges = this.graph.getEdges();
    graphEdges.forEach((edge) => {
      FlowUtils.updateEdgePortColor(
        this.graph,
        edge as IEdgeType,
        FLOW_COLORS.connected,
      );
    });

    this.workflowDetail = flow;
  }

  /** 根据节点和边的信息 渲染画布数据 */
  public initPresetTmpl(data: CellMetadata[], status?: boolean) {
    const cells: Cell[] = [];
    data.forEach((item) => {
      if (['op-start-node', 'op-end-node'].includes(item.shape)) {
        cells.push(
          this.graph.createNode(FlowUtils.getStartEndNode(item as any)),
        );
      } else if (item.shape !== 'dag-edge') {
        try {
          cells.push(
            this.graph.createNode(
              FlowUtils.initTemplateNode({...item, graph: this.graph} as any),
            ),
          )
        } catch (e) {
          //不支持的节点不渲染
        }
      } else {
        cells.push(this.graph.createEdge(item));
      }
    });

    // status为真，表示编辑时，回显模板；status为假，表示点击生成模板
    if (status) {
      this.graph.resetCells(cells);
    } else {
      this.drawNewCellsOnCanvas(cells);
    }
  }

  /** 使用removeCells和addCells，在画布上绘制新的cells */
  private drawNewCellsOnCanvas(cells: any) {
    const historyNodes = this.graph.getNodes();
    this.graph.model.removeCells(historyNodes, {
      silent: false,
      operationType: 'removeCells:operation',
    });
    this.graph.model.addCells(cells);
  }

  public onDropNode(params) {
    this.coloseAllWindow();
    if (
      params.type === 'LTM' &&
      !this?.workflowDetail?.workflow_details?.configs?.long_memory_enabled
    ) {
      const modalRef = this.nzModal.create({
        nzContent: this.dropLTMModal,
        nzWidth: '520px',
        nzMaskClosable: false,
      });
    } else {
      this.createNode(params);
    }
  }

  public createActionNode(params): Promise<NodeMetadata> {
    this.coloseAllWindow();
    if (
      params.isAction &&
      [
        'Plugin',
        'Workflow',
        'Mcp',
        'DataProcess',
        'DataAcquisition',
        'DataSynthesis',
      ].includes(params.type)
    ) {
      return new Promise((resolve) => {
        if (params.type === 'Plugin') {
          this.useAddPluginModal((plugin) => {
            const apiNodeData = this.appFlowServ.plugin2ApiNode(plugin);

            resolve({
              ...apiNodeData,
              id: `node_${Date.now()}`,
              name: apiNodeData.name,
              type: apiNodeData.type,
              shape: `op-${apiNodeData.type.toLowerCase()}-node`,
            });
          });
          return null;
        }
        if (params.type === 'Workflow') {
          this.useAddFlowModal(
            ({workflow, config}: { workflow: IWorkflow; config: any }) => {
              const apiNodeData = this.appFlowServ.childFlow2ApiNode(workflow);
              apiNodeData.configs = {
                ...apiNodeData.configs,
                ...config,
              };

              resolve({
                ...apiNodeData,
                id: `node_${Date.now()}`,
                name: apiNodeData.name,
                type: apiNodeData.type,
                shape: `op-${apiNodeData.type.toLowerCase()}-node`,
              });
            },
          );
          return null;
        }

        if (
          params.type === 'Mcp' ||
          params.type === 'DataProcess' ||
          params.type === 'DataSynthesis'
        ) {
          this.useAddMcpModal(async (mcpService: IMCPService) => {
            const apiNodeData = await this.appFlowServ.getInitMcpNodeData(
              mcpService,
              params.type,
            );

            resolve({
              ...apiNodeData,
              id: `node_${Date.now()}`,
              name: apiNodeData.name,
              type: apiNodeData.type,
              shape: `op-${apiNodeData.type.toLowerCase()}-node`,
            });
          }, params.type);
          return null;
        }

        if (params.type === 'DataAcquisition') {
          this.appAgentRepoServ
            .getMCPServiceList(flowMcpListParams)
            .then((mcpServices) => {
              if (mcpServices?.mcps?.length) {
                this.appFlowServ
                  .getInitDataAcquisitionData(mcpServices.mcps[0])
                  .then((apiNodeData) => {
                    resolve(getFlowMcpNodeData(apiNodeData));
                  });
              }
            });
          return null;
        }
        return null;
      });
    }
    return null;
  }

  // 增加节点
  public createNode(
    params,
    configs: ICreateNodeConfig = {
      isUpdateFlowData: true,
      ignoreLoopEmbedding: false,
    },
  ): Node {
    if (isNil(configs?.isUpdateFlowData)) {
      configs.isUpdateFlowData = true;
    }

    if (isNil(configs?.ignoreLoopEmbedding)) {
      configs.ignoreLoopEmbedding = false;
    }

    if (params.isAction && params.type === 'DataAcquisition') {
      this.appAgentRepoServ
        .getMCPServiceList(flowMcpListParams)
        .then((mcpServices) => {
          if (mcpServices?.mcps?.length) {
            this.appFlowServ
              .getInitDataAcquisitionData(mcpServices.mcps[0])
              .then((apiNodeData) => {
                this.addActionNode(apiNodeData);

                this.debounceSetMiniMap();
                this.updateFlowData();
              });
          }
        });
      return null;
    }

    if (params.isAction && params.type === 'Plugin') {
      this.useAddPluginModal((plugin: IPlugin) => {
        const apiNodeData = this.appFlowServ.plugin2ApiNode(plugin);
        this.addActionNode(apiNodeData);

        this.debounceSetMiniMap();
        this.updateFlowData({
          successCb: () => {
            let list = this.workflowDetail.workflow_details.nodes.filter(
              (node) => {
                return node.type === 'Plugin';
              },
            );
            this.appFlowServ.setRefreshFlag(true);
            this.appFlowServ.setPluginList(list);
            MessageComponent.showSuccess(
              this.i18n.transform('plugin_added_successfully', {
                pluginName: removeHTMLTag(apiNodeData.name),
              }),
              3000,
            );
          },
        });
      });

      return null;
    }

    if (params.isAction && params.type === 'Workflow') {
      this.useAddFlowModal(
        ({workflow, config}: { workflow: IWorkflow; config: any }) => {
          const apiNodeData = this.appFlowServ.childFlow2ApiNode(workflow);
          apiNodeData.configs = {
            ...apiNodeData.configs,
            ...config,
          };
          this.addActionNode(apiNodeData);

          this.debounceSetMiniMap();
          this.updateFlowData({
            successCb: () => {
              MessageComponent.showSuccess(
                this.i18n.transform('workflow_added_successfully', {
                  workflowName: removeHTMLTag(apiNodeData.name),
                }),
                3000,
              );
            },
          });
        },
      );

      return null;
    }

    if (params.isAction) {
      if (params.type === 'Mcp') {
        this.useAddMcpModal(async (mcpService: IMCPService) => {
          const apiNodeData = await this.appFlowServ.getInitMcpNodeData(
            mcpService,
          );
          this.addActionNode(apiNodeData);

          this.debounceSetMiniMap();
          this.updateFlowData({
            successCb: () => {
              MessageComponent.showSuccess(
                this.i18n.transform('mcp_service_added_successfully', {
                  mcpName: removeHTMLTag(apiNodeData.name),
                }),
                3000,
              );
            },
          });
        }, params.type);
      } else {
        this.useAddMcpModal(async (mcpService: IMCPService) => {
          const apiNodeData = await this.appFlowServ.getInitDataProcessNodeData(
            mcpService,
            params.type,
          );
          this.addActionNode(apiNodeData);

          this.debounceSetMiniMap();
          this.updateFlowData({
            successCb: () => {
              MessageComponent.showSuccess(
                this.i18n.transform('mcp_service_added_successfully', {
                  mcpName: removeHTMLTag(apiNodeData.name),
                }),
                3000,
              );
            },
          });
        }, params.type);
      }
      return null;
    }

    if (LLM_LIKE_NODES.includes(params?.type)) {
      const models = this.appFlowServ.getModelList();
      if (models.length) {
        let modelInfo: Partial<IModel> = models[0];
        const choosenModel =
          this.workflowDetail.workflow_details?.configs?.default_model;
        if (
          choosenModel &&
          models.find(
            (m) => m.model_deployment_id === choosenModel.model_deployment_id,
          )
        ) {
          modelInfo = choosenModel;
        }
        const maxTokens = getMaxReplySetting(modelInfo).default;
        let {model_name, model_type, model_deployment_id, model} = modelInfo;
        if (
          params.type === 'IntentDetection' ||
          params.type === 'ComplexIntentDetection'
        ) {
          if (this.intentRecommendModel && this.intentRecommendModel.id) {
            model_type = this.intentRecommendModel.model_type;
            model_deployment_id = this.intentRecommendModel.id;
            model_name = this.intentRecommendModel.model_name;
            model = this.intentRecommendModel.id;
          }
          params.configs.llm.max_tokens = maxTokens;
          params.configs.llm.model = {
            model_name,
            model_type,
            model_deployment_id,
            ...(model && {model}),
          };
          if (FlowUtils.isAdvancedModeNew(params)) {
            this.appFlowServ.setModeOfIntentNode({
              node_id: params.id,
              mode: 'advanced',
            });
          } else {
            this.appFlowServ.setModeOfIntentNode({
              node_id: params.id,
              mode: 'normal',
            });
          }
        } else {
          params.configs.max_tokens = maxTokens;
          params.configs.model = {
            model_name,
            model_type,
            model_deployment_id,
            ...(model && {model}),
          };
        }
      }
    }

    if (params.type === 'Comment') {
      this.graph.addNode(
        FlowUtils.initCommentNode(params, this.graph, params.type),
      );
      this.updateFlowData();
      return null;
    }

    const loopId = this.drop2LoopId(params);
    this.graph.startBatch('customAddNode');
    const addedNode = this.graph.addNode(
      FlowUtils.initNode(params, this.graph, this.type),
    );

    if (params.type === 'Loop') {
      const {input, output} =
        this.appFlowServ.getInitLoopIONodesPosition(addedNode);
      this.graph.batchUpdate(() => {
        const leftNode = this.graph.addNode({
          ...FlowUtils.getLoopIONode('input', addedNode.id, this.i18n),
          x: input.x,
          y: input.y,
        });
        const rightNode = this.graph.addNode({
          ...FlowUtils.getLoopIONode('output', addedNode.id, this.i18n),
          x: output.x,
          y: output.y,
        });

        addedNode.addChild(leftNode);
        addedNode.addChild(rightNode);
      });
    }

    if (!configs.ignoreLoopEmbedding && loopId) {
      this.checkisIntersectWithLoopThenAddChild(loopId, addedNode);
    }
    this.graph.stopBatch('customAddNode');
    this.debounceSetMiniMap();
    if (configs.isUpdateFlowData) {
      this.updateFlowData();
    }

    return addedNode;
  }

  public drop2LoopId({id, x, y, width, height}) {
    let result = '';
    const nodes = this.graph.getNodes();

    for (const node of nodes) {
      if (
        node.id !== id &&
        FlowUtils.getNodeDSLFromRaw(node)?.type === 'Loop' &&
        node.getBBox().isIntersectWithRect({x, y, width, height})
      ) {
        result = node.id;
      }
    }

    return result;
  }

  public zoomInFlow() {
    if (this.graph.zoom() < 0.8) {
      this.graph.zoomTo(0.8);
    }
  }

  public onClickShowThumb() {
    this.showMiniMap = !this.showMiniMap;
  }

  public checkisIntersectWithLoopThenAddChild(
    loopId: string,
    addedNode: Node<NodeProperties>,
  ) {
    const addedNodeData = FlowUtils.getNodeDSLFromRaw(addedNode);

    if (addedNodeData && !CANT_EMBEDDING_NODES.includes(addedNodeData.type)) {
      const loop = this.graph.getCellById(loopId);
      loop.addChild(addedNode);

      this.appFlowServ.setLoopInnerRal({
        loopNodeId: loop.id,
        childNodeId: addedNode.id,
        action: 'add',
      });

      (loop.data.ngArguments.nodeInfo as ILoopNode).configs.loop_body.push(
        addedNode.id,
      );
    }
  }

  public undo() {
    if (this.canUndo) {
      const history = this.graph.getPlugin('history') as any;
      const undoStack = history.undoStack;
      // preStep中，需要先撤销一步，然后检查撤销后得到的最新undoStack中，最后一个element是否为removeCells操作
      this.undoRecursion();
      const isRemoveCellsOp = this.checkLastElmBeforeUndoRedo(undoStack);
      if (isRemoveCellsOp) {
        this.graph.undo();
      }
      this.keyDownSubject.next();
    }
    this.canUndo = this.graph.canUndo();
    this.canRedo = this.graph.canRedo();
  }

  undoRecursion() {
    const history = this.graph.getPlugin('history') as any;
    const undoStack = history.undoStack;
    if (undoStack.length && undoStack[undoStack.length - 1]) {
      const lastUndo = undoStack[undoStack.length - 1];
      this.graph.undo();
      if (lastUndo?.length === 1) {
        if (
          lastUndo[0].event.includes('cell:change:') &&
          lastUndo[0].event !== 'cell:change:position' &&
          lastUndo[0].event !== 'cell:change:data' &&
          lastUndo[0].event !== 'cell:change:target'
        ) {
          this.undoRecursion();
        }
      }
    }
  }

  public redo() {
    if (this.canRedo) {
      const history = this.graph.getPlugin('history') as any;
      const redoStack = history.redoStack;
      const isRemoveCellsOp = this.checkLastElmBeforeUndoRedo(redoStack);
      // nextStep中，不要先前进一步，直接检查redoStack中，最后一个element是否为removeCells操作
      if (isRemoveCellsOp) {
        this.graph.redo();
        this.graph.redo();
      } else {
        this.redoRecursion();
      }
      this.keyDownSubject.next();
    }
    this.canUndo = this.graph.canUndo();
    this.canRedo = this.graph.canRedo();
  }

  redoRecursion() {
    const history = this.graph.getPlugin('history') as any;
    const redoStack = history.redoStack;
    if (redoStack.length && redoStack[0]) {
      const lastRedo = redoStack[0];
      this.graph.redo();
      if (lastRedo?.length === 1) {
        if (
          lastRedo[0].event.includes('cell:change:') &&
          lastRedo[0].event !== 'cell:change:position' &&
          lastRedo[0].event !== 'cell:change:data' &&
          lastRedo[0].event !== 'cell:change:target'
        ) {
          this.redoRecursion();
        }
      }
    }
  }

  public onClickShowAddNodesWidget(e: Event) {
    e.stopPropagation();

    if (!this.showAddNodesWidget) {
      this.showAddNodesWidget = true;
    }
  }

  public onClickOutsideAddNodesWidget() {
    this.showAddNodesWidget = false;
  }

  public onClickOutsideShowFlowNodesWidget() {
    this.showFlowNodesWidget = false;
  }

  /**
   * 作用：在撤销或前进之前，检查undoStack或redoStack中的最后一步是否为removeCells操作
   * 如果最后一步为removeCells操作，则undo和redo都要执行2次，避免空画布的中间态
   */
  private checkLastElmBeforeUndoRedo(stack: any) {
    let isRemoveCellsOp;
    if (Array.isArray(stack[stack.length - 1])) {
      isRemoveCellsOp =
        stack.length > 0 &&
        stack[stack.length - 1].every(
          (item: any) =>
            item.event === 'cell:removed' &&
            item.options &&
            item.options?.operationType === 'removeCells:operation',
        );
    }

    return isRemoveCellsOp;
  }

  private checkLastElmBranchResize(stack: any) {
    let isResizeOp;
    if (Array.isArray(stack[stack.length - 1])) {
      isResizeOp =
        stack.length > 0 &&
        stack[stack.length - 1].every(
          (item: any) => item.event === 'cell:change:size' && item.batch,
        );
    }

    return isResizeOp;
  }

  public clickAddNodeOutside(e: MouseEvent) {
    if (
      this.showAddPanel &&
      (e?.target as SVGAElement)?.nodeName !== 'circle'
    ) {
      this.showAddPanel = false;
      this.removeNoTargetNodeEdge();
      this.currentInActionEdge?.removeTools();
    }
  }

  public async onInsertNode(param) {
    const edge = this.currentInActionEdge as Edge;
    if (this.exchangeNodeInfo) { // 交换节点
      await this.onExchangeNode(param);
      return;
    }
    if (!edge) {
      await this.onCreateNewNode(param);
      return;
    }
    const sourceNodeId = edge.getSourceCellId();
    const targetNodeId = edge.getTargetCellId();
    if (!sourceNodeId || !this.currentInActionEdgeView) {
      return;
    }
    const sourceNode = this.graph.getCellById(sourceNodeId);
    if (sourceNode?.hasParent() && param.type === 'Loop') {
      MessageComponent.showError(
        this.i18n.transform('loop_node_nesting'),
        3000,
      );
      return;
    }
    if (!targetNodeId) {
      //连接桩拖拽到空白
      await this.onInsertRightNode(param);
      return;
    }
    await this.onInsertBetweenNode(param);
  }

  public async onInsertBetweenNode(param) {
    const edge = this.currentInActionEdge as Edge;
    const edgeBBox = edge.getBBox();
    let isClickPort = edgeBBox?.width < 10 && edgeBBox?.height < 10; // 是否点击连接桩，用连线很短来判断，待优化
    const sourceNodeId = edge.getSourceCellId();
    const targetNodeId = edge.getTargetCellId();
    const sourcePortId = edge.getSourcePortId();
    const targetPortId = edge.getTargetPortId();

    let {x, y, width} = edge.getSourceCell().getBBox();

    const edgeView = this.currentInActionEdgeView;
    const midpoint = edgeView.getPointAtRatio(0.5);

    let newNode: Node = null;

    try {
      await this.graph.batchUpdate(async () => {
        const sourceParent = edge.getSourceCell()?.getParent();
        let nodeRaw: NodeMetadata | null = null;

        if (param.isAction) {
          nodeRaw = await this.createActionNode(param);
          this.showPluginDrawer = false;
          this.showChildFlowDrawer = false;
          this.showMcpServiceDrawer = false;
        } else {
          nodeRaw = param;
        }

        this.graph.removeEdge(this.currentInActionEdge.id);
        if (isClickPort) {
          x += 140;
        }
        newNode = this.createNode(
          {
            ...nodeRaw,
            id: `node_${Date.now()}`,
            x: x + width + ADD_BETWEEN_NODE_DISTANCE,
            y: midpoint.y - 140,
          },
          {
            ignoreLoopEmbedding: true,
            isUpdateFlowData: false,
          },
        );

        const newNodePorts = newNode.getPorts();
        const leftPort = newNodePorts.find((port) => port.group === 'left');
        const rightPort = newNodePorts.find((port) => port.group !== 'left');

        const leftEdge = this.graph.addEdge({
          shape: 'dag-edge',
          source: {
            cell: sourceNodeId,
            port: sourcePortId,
          },
          target: {
            cell: newNode.id,
            port: leftPort.id,
          },
        });
        this.onEdgeConnected(leftEdge);

        const rightEdge = this.graph.addEdge({
          shape: 'dag-edge',
          source: {
            cell: newNode.id,
            port: rightPort.id,
          },
          target: {
            cell: targetNodeId,
            port: targetPortId,
          },
        });
        this.onEdgeConnected(rightEdge);
        //判断原来距离
        const originDistance = this.getNodeDistance(sourceNodeId, targetNodeId);
        const newWidth = newNode.getBBox().width;
        const newHeight = newNode.getBBox().height;
        const allWidth = newWidth + ADD_BETWEEN_NODE_DISTANCE * 2;
        if (originDistance < allWidth) {
          const newOffset = allWidth - originDistance;
          this.resetTargetNodePos(newNode, newOffset);
        } else {
          // 距离够放在中间
          newNode.position(midpoint.x - newWidth / 2, midpoint.y - newHeight);
        }
        if (newNode?.getChildren()?.length === 0) {
          newNode.toFront();
        }
        if (sourceParent) {
          this.checkisIntersectWithLoopThenAddChild(sourceParent.id, newNode);
          this.hiddenAddNodePanel();
          this.updateRef();
          setTimeout(() => {
            FlowEventUtils.resetParentSize(sourceParent)
            this.updateFlowData();
          }, 100)
        } else {
          this.hiddenAddNodePanel();
          this.updateRef();
          this.updateFlowData();
        }
      });
    } catch {
      // do nth
    }
  }

  getNodeDistance(sourceId, targetId) {
    const source = this.graph.getCellById(sourceId);
    const target = this.graph.getCellById(targetId);

    const bboxSource = source.getBBox();
    const bboxTarget = target.getBBox();

    return bboxTarget.x - (bboxSource.x + bboxSource.width);
  }

  public async onInsertRightNode(param) {
    const edge = this.currentInActionEdge as Edge;
    const edgeBBox = edge.getBBox();
    let isClickPort = edgeBBox?.width < 10 && edgeBBox?.height < 10; // 是否点击连接桩，用连线很短来判断，待优化
    const sourceNodeId = edge.getSourceCellId();
    const sourcePortId = edge.getSourcePortId();

    let {x, y} = edge.getTarget() as Position;

    let newNode: Node = null;

    try {
      await this.graph.batchUpdate(async () => {
        const sourceParent = edge.getSourceCell()?.getParent();
        let nodeRaw: NodeMetadata | null = null;

        if (param.isAction) {
          nodeRaw = await this.createActionNode(param);
          this.showPluginDrawer = false;
          this.showChildFlowDrawer = false;
          this.showMcpServiceDrawer = false;
        } else {
          nodeRaw = param;
        }

        this.graph.removeEdge(this.currentInActionEdge.id, {
          ignoreHistory: true,
        });
        if (isClickPort) {
          x += 140;
        }
        newNode = this.createNode(
          {
            ...nodeRaw,
            id: `node_${Date.now()}`,
            x: x,
            y: y - 140,
          },
          {
            ignoreLoopEmbedding: true,
            isUpdateFlowData: false,
          },
        );

        const newNodePorts = newNode.getPorts();
        const leftPort = newNodePorts.find((port) => port.group === 'left');

        const leftEdge = this.graph.addEdge({
          shape: 'dag-edge',
          source: {
            cell: sourceNodeId,
            port: sourcePortId,
          },
          target: {
            cell: newNode.id,
            port: leftPort.id,
          },
        });
        this.onEdgeConnected(leftEdge);
        if (sourceParent) {
          this.checkisIntersectWithLoopThenAddChild(sourceParent.id, newNode);
          this.hiddenAddNodePanel();
          this.updateRef();
          setTimeout(() => {
            FlowEventUtils.resetParentSize(sourceParent)
            this.updateFlowData();
          }, 100)
        } else {
          this.hiddenAddNodePanel();
          this.updateRef();
          this.updateFlowData();
        }
      });
    } catch {
      // do nth
    }
  }

  public async onCreateNewNode(param) {
    const {x, y} = this.graph.clientToLocal(
      this.addPanelPos.x,
      this.addPanelPos.y,
    );
    try {
      await this.graph.batchUpdate(async () => {
        let nodeRaw: NodeMetadata | null = null;

        if (param.isAction) {
          nodeRaw = await this.createActionNode(param);
          this.showPluginDrawer = false;
          this.showChildFlowDrawer = false;
          this.showMcpServiceDrawer = false;
        } else {
          nodeRaw = param;
        }

        this.createNode(
          {
            ...nodeRaw,
            id: `node_${Date.now()}`,
            x: x,
            y: y,
          },
          {
            ignoreLoopEmbedding: true,
            isUpdateFlowData: false,
          },
        );
        this.hiddenAddNodePanel();
        this.updateRef();
        this.updateFlowData();
      });
    } catch {
      // do nth
    }
  }

  /**
   * 更新画布数据: 拖动,添加,删除节点时调用
   *  @param config
   *  @param bodyParams 可选参数，子工作流节点升级新版本调用的put接口的body体
   * @param new_detail
   * @param is_sub_controller_update
   */
  async updateFlowData(
    config: IUpdateFlowConfig = {
      isDrag: false,
      nodeInfo: {},
      successCb: () => {
      },
      faildCb: () => {
      },
    },
    bodyParams?: any,
    new_detail?: any,
    is_sub_controller_update = false,
  ) {
    const _workflowDetail = is_sub_controller_update
      ? new_detail
      : this.workflowDetail;
    const newFlowData =
      bodyParams ||
      this.appFlowServ.getUpdateGraphData(
        this.graph,
        _workflowDetail,
        is_sub_controller_update,
      );
    deleteViewParamsForDsl(newFlowData.workflow_details.nodes);
    modifyAdvancedDsl(newFlowData.workflow_details.nodes);

    if (this.isStartNodeBtnClicked) {
      this.appFlowServ.setStartNodeBtnClicked(true);
    }
    newFlowData.is_drag = !!config?.isDrag;
    newFlowData.workflow_details.name = newFlowData?.code ?? '';
    newFlowData.update_time = this.appFlowServ.getVersionInfo();
    if (newFlowData) {
      delete newFlowData.avatar; // avatar没有修改并且是base64格式，接口禁止传入base64格式
      delete newFlowData.customize_node; // 移除customize_node，用于标识工作流是否为自定义节点
      try {
        let response;
        if (this.type === 'multi') {
          // 创建保存接口
          const params = FlowUtils.buildMultiAgentReqParams(newFlowData);
          modifyOutput(params);
          response = await this.appAgentRepoServ.modifyMultiAgent(params);
          response.avatar = response.icon;
          // 版本升级需要重新匹配
        } else {
          response = await this.appFlowRepoServ.modifyFlow(newFlowData);
        }
        this.workflowDetail = response;
        setTimeout(() => {
          // 最好放在操作里，位置改变不触发
          if (this.type === 'multi') {

          } else {
            this.updateOutputsMap();
          }
        });
        this.appFlowServ.setFlowConfigs(
          this.workflowDetail?.workflow_details?.configs,
        );
        this.updateAnalyzeTabStatus(!this.workflowDetail.status);
        // 设置version信息
        const {update_time} = response;
        this.appFlowServ.setVersionInfo(update_time);
        // 更新后校验工作流
        if (this.isStartCheckErrorWorkFlow) {
          this.checkErrorWorkFlow(false);
        }
        config?.successCb?.();

      } catch {
        config?.faildCb?.();
      }
    }
  }

  updateOutputsMap() {
    // 保存所有的能被引用的outpust
    let outputsMap = {};
    this.workflowDetail.workflow_details.nodes.filter((no: any) => {
      return no?.outputs?.length;
    }).forEach((no: any) => {
      outputsMap[no.id] = no.outputs;
    });
    const info = this.getPredecessorsRef('node_end');
    const info_list = NodeUtils.refInfo2Tree(info);
    const requestVariables = this.appFlowServ.requestVariablesFn(info_list);
    const environment = info_list.find(v => {
      return v.type === 'environment';
    })?.children || [];
    this.appFlowServ.setNodeRefChange({
      outputsMap,
      memory: this.workflowDetail.workflow_details?.configs?.memory || [],
      environment,
      request: requestVariables?.[0]?.children || [],
      nodesList: this.workflowDetail.workflow_details.nodes
    });
  }

  checkErrorWorkflowIcon = 0;
  checkErrorWorkflowSetTime = null;
  validateWorkflowList = []
  checkErrorWorkflowHalfModalRef = false;
  isStartCheckErrorWorkFlow = false;

  // 增加单步调试的参数，如果是单步也要增加校验
  async checkErrorWorkFlow(showModal, testId?: string, isPublish?: boolean) {
    if (this.type !== 'multi') {
      if (this.checkErrorWorkflowSetTime) {
        clearTimeout(this.checkErrorWorkflowSetTime);
        this.checkErrorWorkflowSetTime = null;
      }

      this.checkErrorWorkflowSetTime = setTimeout(async () => {
        const validateRes = await this.validateWorkflow();
        const {success, errors} = validateRes;
        if (success) {
          this.checkErrorWorkflowIcon = 0;
          this.appFlowServ.testRunVerificationError = false;
          this.validateWorkflowList = [];
          this.checkErrorWorkflowHalfModalRef = false;
          if (showModal) {
            this.showRunModal = true;
          }
          if (testId) {
            // 调试
            this.openSingleTestModal(testId);
          } else if (isPublish) {
            // 工作流发布版本
            this.handelPublish();
          } else {
            // 试运行
            this.flowHelperServ.adjustRightForNodeModal('', 'left');
          }
          this.isStartCheckErrorWorkFlow = false;
        } else {
          this.validateWorkflowList = errors;
          this.appFlowServ.testRunVerificationError = true;
          this.checkErrorWorkflowIcon = new Set(
            errors.map((error) => error.id),
          ).size;
          if (showModal && this.checkErrorWorkflowIcon > 0) {
            this.showCheckWorkflowModal();
          }
        }
        this.appFlowServ.setValidateWorkflowList(this.validateWorkflowList);
      }, 10);
    }
  }

  showCheckWorkflowModal() {
    this.coloseAllWindow(['checkErrorWorkflowHalfModalRef', 'flow-common-half-modal']);
    this.appFlowServ.setRunBtnClicked(false);
    this.checkErrorWorkflowHalfModalRef = true;
    this.adjustTopForNodeModal();
    this.flowHelperServ.adjustRightForNodeModal('checkerrorworkflow-half-modal', 'right');
  }

  clickCheckErrorWorkflowModal(e) {
    this.openNodeModal(e, ['checkErrorWorkflowHalfModalRef']);
  }

  dismissCheckErrorWorkflowModal() {
    this.checkErrorWorkflowHalfModalRef = false;
    this.flowHelperServ.adjustRightForNodeModal('', 'right');
  }

  onEdgeConnected(edge: Edge) {
    this.graph.batchUpdate(() => {
      // 修改连接桩颜色
      FlowUtils.updateEdgePortColor(
        this.graph,
        edge as IEdgeType,
        FLOW_COLORS.connected,
      );
      edge.setAttrs(
        {
          line: {
            stroke: FLOW_COLORS.connected,
            strokeWidth: 2,
            targetMarker: TargetMarker,
          },
        },
        {
          ignoreHistory: true,
        },
      );

      const targetCell = edge.getTargetCell();
      const hasParent = targetCell?.getParent();
      if (targetCell && hasParent) {
        const targetZIndex = targetCell.getZIndex();

        setTimeout(() => {
          edge.setZIndex(targetZIndex, {
            ignoreHistory: true,
          });
        });
      }
    });
  }

  isClickOpAction(className: string) {
    const ops = [
      'delete-node',
      'node-open',
      'node-close',
      'single-test-icon',
      'readonly-params-unfold',
      'readonly-params-fold',
      'update-flow-icon',
      'ti3-icon-more-rimless',
      'node-test-info',
    ];

    return ops.some((op) => className.includes(op));
  }

  private updateMultiAgenSubFlow(newFlow: IWorkflowNode) {
    this.workflowDetail.details.nodes.forEach((node) => {
      if (node.id === newFlow.id) {
        this.updateNodeData(newFlow);
      }

      if (node.type === 'Controller') {
        (node as IControllerNode).configs.workflows.forEach((flow, index) => {
          if (flow.node_id === newFlow.id) {
            (node as any).configs.workflows[index] = {
              ...flow,
              name: newFlow.name,
              configs: newFlow.configs,
            };
          }
        });

        if (FlowUtils.isSingleAgentNodeType(true, newFlow)) {
          (node as IControllerNode).configs.agents.forEach((agent, index) => {
            if (agent.node_id === newFlow.id) {
              (node as any).configs.agents[index] = {
                ...agent,
                name: newFlow.name,
                configs: newFlow.configs,
              };
            }
          });
        }

        this.updateNodeData(node);
      }
      // 再关掉抽屉画布的
      this.closeNodeConfigDrawer();
    });

    this.updateFlowData({
      successCb: () => {
        const subFlows = this.appFlowServ.getResNodes()?.map((flow) => {
          if (flow.id === newFlow.id) {
            flow.showIcon = false;
          }

          return flow;
        });

        this.appFlowServ.setResNodes(subFlows);
        MessageComponent.showSuccess(
          this.i18n.transform('upgrade_version_successful'),
          3000,
        );
      },
    });
  }

  /**
   * 移除没有连接节点的连线
   */
  removeNoTargetNodeEdge() {
    if (this.currentInActionEdge) {
      const target = (
        this.currentInActionEdge as Edge
      )?.getTarget() as Position;
      if (target?.x !== undefined) {
        this.currentInActionEdge.remove({
          ignoreHistory: true,
        });
      }
    }
  }

  /**
   * 将后续节点右移
   */
  resetTargetNodePos(startNode, newOffset = 500) {
    const result = [startNode];
    const stack = [startNode]; // 使用栈替代递归
    const visited = new Set();

    while (stack.length > 0) {
      const currentNode = stack.pop();

      // 获取出边
      const outgoingEdges = this.graph.getConnectedEdges(currentNode, {
        outgoing: true,
      });

      outgoingEdges.forEach((edge) => {
        const targetNode = edge.getTargetNode();
        if (targetNode && !visited.has(targetNode.id)) {
          visited.add(targetNode.id);
          result.push(targetNode);
          stack.push(targetNode);
        }
      });
    }

    result.forEach((node, index) => {
      //新增的节点距离已经修改过了
      if (index) {
        node.translate(newOffset, 0);
      }
    });
  }

  hiddenAddNodePanel() {
    this.showAddPanel = false;
    this.removeNoTargetNodeEdge();
    this.currentInActionEdge?.removeTools({
      ignoreHistory: true,
    });
  }

  bringEdgeBack() {
    if (this.selectedEdgeId) {
      const cell = this.graph.getCellById(this.selectedEdgeId);

      if (['edge', 'dag-edge'].includes(cell?.shape)) {
        cell.setAttrs(
          {
            line: {
              stroke: FLOW_COLORS.connected,
              strokeWidth: 2,
            },
          },
          {
            ignoreHistory: true,
          },
        );

        const targetCell = (cell as Edge<EdgeProperties>).getTargetCell();
        const hasParent = targetCell?.getParent();

        if (targetCell && hasParent) {
          const targetZIndex = targetCell.getZIndex();

          cell.setZIndex(targetZIndex - 1 === 0 ? 1 : targetZIndex - 1, {
            ignoreHistory: true,
          });
        } else {
          cell.toBack({
            ignoreHistory: true,
          });
        }
        cell.removeTools({
          ignoreHistory: true,
        });
        this.selectedEdgeId = '';
      }
    }
  }

  private updateAgentsNodeData(data: any) {
    const nodesData: any = this.graph.getNodes();
    const activeIndex = nodesData.findIndex((item: any) => {
      return item.id === data.id;
    });
    if (activeIndex >= 0) {
      nodesData[activeIndex].setData({
        ngArguments: {
          nodeInfo: {...data},
        },
      });

      // 更新数据的真正操作，并且不添加到历史记录
      nodesData[activeIndex].setData(null, {ignoreHistory: true});
      nodesData[activeIndex].setData(
        {
          ngArguments: {
            nodeInfo: {...data},
          },
        },
        {ignoreHistory: true},
      );
    }
  }

  private updateNodeData(data: any) {
    const nodesData = this.graph.getNodes();
    const activeIndex = nodesData.findIndex((item: any) => {
      return item.id === data.id;
    });

    if (activeIndex >= 0) {
      nodesData[activeIndex].setData({
        ngArguments: {
          nodeInfo: {...data},
        },
      });

      // 更新数据的真正操作，并且不添加到历史记录
      nodesData[activeIndex].setData(null, {ignoreHistory: true});
      nodesData[activeIndex].setData(
        {
          ngArguments: {
            nodeInfo: {...data},
          },
        },
        {ignoreHistory: true},
      );
    }
  }

  private deleteNode(
    id: string,
    isUpdateFlowData: boolean = true,
    isContainerNode: boolean = false,
  ) {
    const nodeInfo = this.getNodeInfoById(id);
    if (!nodeInfo) {
      return;
    }
    if (UnDeletableNodeTypes.includes(nodeInfo.type) && !isContainerNode) {
      return;
    }
    const {type} = nodeInfo;

    if (FlowUtils.isAdvancedModeNew(nodeInfo)) {
      this.deleteContainerNode(id, false); // 删除高级意图节点，同时删除容器节点
    }

    if (this.showNodeConfigDrawer && this.nodeServ.getCurrSelectedNodeId() === id) {
      this.closeNodeConfigDrawer();
    }
    const parent = this.graph.getCellById(id)?.getParent()
    const parentData = this.graph.getCellById(id)?.getParent()?.data
      ?.ngArguments?.nodeInfo as NodeInfo;
    if (parentData?.type === 'Loop') {
      this.appFlowServ.setLoopInnerRal({
        loopNodeId: parentData.id,
        childNodeId: id,
        action: 'delete',
      });

      (parentData as ILoopNode).configs.loop_body = (
        parentData as ILoopNode
      ).configs.loop_body.filter((childId) => childId !== id);
      this.updateNodeData(parentData);
    }

    this.graph.batchUpdate(() => {
      try {
        const node = this.graph.getCellById(id);
        if (!node) {
          return;
        }
        const subNodes = node.getDescendants({deep: true});
        subNodes.forEach(n => this.graph.removeCell(n));
        this.graph.removeCell(id);
      } catch (error) {
      }
    });
    // 是否更新工作流数据。目前唯一不更新的情况：删除意图容器节点。
    if (isUpdateFlowData) {
      this.keyDownDelSubject.next(type);
    }
  }

  private copyNodeById(id: string, isUpdateFlowData: boolean = true) {
    const node = this.graph.getCellById(id);
    if (node) {
      const {position, shape, data} = node.toJSON();
      const newId = `node_${Date.now()}`;
      const {name, type, ...restData} = data.ngArguments.nodeInfo as NodeInfo;

      if (name.length >= 64) {
        MessageComponent.showError(
          this.i18n.transform('flowcomponent_618'),
          3000,
        );
        return '';
      }
      // 是否为高级意图节点
      const isCopyAdvancedIntent = FlowUtils.isAdvancedModeNew(
        data.ngArguments.nodeInfo,
      );
      if (isCopyAdvancedIntent) {
        (restData as any).branches = []
      }
      this.createNode(
        {
          ...restData,
          id: newId,
          name,
          type,
          x: (position.x as number) + 100,
          y: (position.y as number) + 100,
          shape,
        },
        {
          isUpdateFlowData: !isCopyAdvancedIntent && isUpdateFlowData,
        },
      );
      const nilFunc = () => void 0;
      if (isCopyAdvancedIntent) {
        FlowUtils.copyContainerNodeInGroup(
          id,
          this.graph,
          newId,
          this.createNode.bind(this),
          this.handleAdvancedIntentConns.bind(this),
          this.updateRef.bind(this),
          isUpdateFlowData ? this.updateFlowData.bind(this) : nilFunc,
        );
      }
      return newId;
    }
    return '';
  }

  private copyNodeByIdDebounce() {
    const node = this.graph.getCellById(this.copiedNodeId);

    if (node) {
      const {position, shape, data} = node.toJSON();
      const newId = `node_${Date.now()}`;
      const {name, type, ...restData} = data.ngArguments.nodeInfo as NodeInfo;
      // 是否为高级意图节点
      const isCopyAdvancedIntent = FlowUtils.isAdvancedModeNew(
        data.ngArguments.nodeInfo,
      );

      this.createNode(
        {
          ...restData,
          id: newId,
          name,
          type,
          x: (position.x as number) + 100,
          y: (position.y as number) + 100,
          shape,
        },
        {
          isUpdateFlowData: false,
        },
      );

      if (isCopyAdvancedIntent) {
        const uuid = this.copiedNodeId.split('_')[1];
        // 获取被选中待复制的这个整体内的容器节点id
        const containerNodeId = `node_intent_container_${uuid}`;
        const containerNode = this.graph.getCellById(containerNodeId);

        if (containerNode) {
          const {position, shape, data} = containerNode.toJSON();
          // 复制完成的新容器节点id
          const newContainerId = `node_intent_container_${newId.split('_')[1]}`;

          const {name, type, ...restData} = data.ngArguments
            .nodeInfo as NodeInfo;

          this.createNode(
            {
              ...restData,
              id: newContainerId,
              name,
              type,
              x: (position.x as number) + 100,
              y: (position.y as number) + 100,
              shape,
            },
            {
              isUpdateFlowData: false,
            }, // 不在createNode函数内部更新工作流数据
          );
          // 仅在异步创建完连接线后，更新一次数据
          this.handleAdvancedIntentConns(newId);
          this.updateRef();
        }
      }
      this.keyDownVSubject.next();
    }
  }

  bringNodeToFront(graph: Graph, node: Node) {
    if (node.isNode()) {
      if (node.getChildren()?.length) {
        this.bringGroupToFront(graph, node);
      } else {
        node.toFront();
      }
    }
  }

  private bringGroupToFront(graph: Graph, group: Node) {
    const children = group.getChildren();

    const groupEdges = new Set<Edge>();
    children.forEach((child) => {
      const incomingEdges = graph.getIncomingEdges(child);
      const outgoingEdges = graph.getOutgoingEdges(child);

      if (incomingEdges) {
        incomingEdges.forEach((edge) => groupEdges.add(edge));
      }

      if (outgoingEdges) {
        outgoingEdges.forEach((edge) => groupEdges.add(edge));
      }
    });

    group.toFront({deep: true});

    groupEdges.forEach((edge) => edge.toFront());
  }


  resetEnvList(e) {
    this.envList = [];
    if (this.workflowDetail.workflow_details.configs?.environment && typeof this.workflowDetail.workflow_details.configs?.environment === 'string') {
      this.envList = e?.variables;
    }
  }

  // 获取前序节点的引用（outputs）信息，生成引用options
  private getPredecessorsRef(id: string): IRefInfo[] {
    const cell = this.graph.getCellById(id);
    const systemData: IRefInfo = {
      refNodeId: 'node_start',
      refNodeName: this.i18n.transform('system_parameter'),
      type: 'System',
      outputs: [],
    };

    let hasEnv = false;

    const memos: IRefInfo = {
      refNodeId: 'node_start',
      refNodeName: this.i18n.transform('memory_variable'),
      type: 'MemoVal',
      outputs: [],
    };

    if (this.workflowDetail.workflow_details?.configs?.memory) {
      memos.outputs = cloneDeep(
        this.workflowDetail.workflow_details.configs.memory,
      );
      memos.outputs.forEach((m) => {
        m.name = `memory.${m.name}`;
      });
    }

    if (cell) {
      const predecessors: IViewNodeData[] = this.graph
        .getPredecessors(cell)
        .map((pre) => pre.getData());

      const startData: IViewNodeData = predecessors.find(
        (pre) => pre.ngArguments.nodeInfo.type === 'Start',
      );
      if (startData) {
        systemData.outputs = (
          startData.ngArguments.nodeInfo as HasOutputsNode
        ).outputs.filter((v) => v.name === 'sys');
      }

      const data = predecessors
        .filter(
          (pre) =>
            !NoOutputsNodeTypes.includes(pre.ngArguments.nodeInfo.type) &&
            (pre.ngArguments.nodeInfo as HasOutputsNode).outputs?.length > 0,
        )
        .map((pre) => {
          const {
            id: refNodeId,
            name,
            type,
          } = pre.ngArguments.nodeInfo as HasOutputsNode;
          let {outputs} = pre.ngArguments.nodeInfo as HasOutputsNode;

          if (type === 'Start') {
            outputs = outputs.filter(
              (output) => output.name !== 'sys' && output.name !== 'env',
            );
          }

          if (type === 'IntentDetection') {
            outputs = outputs.filter(
              (output) =>
                output.name === 'classification_id' || output.name === 'name',
            );
          }

          return {
            refNodeId,
            refNodeName: name,
            type,
            outputs,
          };
        });

      const systemArr = systemData.outputs.length ? [systemData] : [];
      const memosArr = memos.outputs.length ? [memos] : [];
      const envArr: any = [];
      try {
        const outputsCfg = this.envList.map((item) => {
          return {
            description: '',
            name: item.name,
            reflection: false,
            required: false,
            source: 'environment',
            type: item.value.type,
            value: {
              default: item.value.content,
              type: 'literal',
              hint: '',
              content: null,
            },
          };
        });
        if (this.showEnv) {
          envArr.push({
            outputs: outputsCfg,
            refNodeName: this.i18n.transform('envParams'),
            type: 'environment',
          });
        }
      } catch {
      }
      return [...envArr, ...memosArr, ...data, ...systemArr];
    }

    return [];
  }

  optimizeLayout(is_need_save = true) {
    if (this.isFlowReadonly || this.notUserSelf) {
      return;
    }
    // 1. 优化前：记录注释节点与最近节点的相对位置关系
    const commentRelations = this.getCommentToNodeRelations();

    if (this.type === 'multi') {
      // 树形布局
      const allNodeData = this.graph.getNodes().map((node) => ({
        ...node.getData(),
        ...node.getBBox(),
        position: node.position(),
      }));
      const controllerNode = allNodeData.find(
        (node) => node.ngArguments.nodeInfo.type === 'Controller',
      );

      FlowUtils.applyTreeLayout(
        allNodeData,
        this.appFlowServ,
        controllerNode?.ngArguments.nodeInfo.configs.workflows,
        controllerNode?.ngArguments.nodeInfo.configs.agents,
        true,
        this.localScale,
        this.workflowDetail,
        this.graph,
      );
    } else {
      FlowEventUtils.optimizeDagreLayout(this.graph)
    }
    // 2. 优化后：根据记录的关系重新定位注释节点
    this.reallocateComments(commentRelations);
    this.flowZoomToFit();
    if (is_need_save) {
      this.updateFlowData({isDrag: true});
    }
  }

  /**
   * 获取注释节点到目标节点的映射关系
   * 用于在布局优化时将注释节点移动到目标节点的正下方
   */
  private getCommentToNodeRelations(): Map<string, string> {
    const commentRelations = new Map<string, string>();
    const cells = this.graph.getCells();
    const nodes = cells.filter(cell => cell.isNode() && cell.shape !== 'op-comment-node');
    const commentNodes = cells.filter(cell => cell.isNode() && cell.shape === 'op-comment-node');

    commentNodes.forEach(commentNode => {
      let minDistance = Infinity;
      let nearestNodeId = '';

      // 找到最近的非注释节点作为目标节点
      nodes.forEach(node => {
        const commentPos = (commentNode as any).position();
        const nodePos = (node as any).position();
        const distance = Math.sqrt(
          Math.pow(commentPos.x - nodePos.x, 2) +
          Math.pow(commentPos.y - nodePos.y, 2)
        );

        if (distance < minDistance) {
          minDistance = distance;
          nearestNodeId = node.id;
        }
      });

      // 记录注释节点与目标节点的关系
      if (nearestNodeId) {
        commentRelations.set(commentNode.id, nearestNodeId);
      }
    });

    return commentRelations;
  }

  /**
   * 根据目标节点的新位置重新定位注释节点
   * 将注释节点移动到目标节点的正下方，
   * 如果重叠则将则视情况调整其他节点
   * @param commentRelations
   * @private
   */
  private reallocateComments(commentRelations: Map<string, string>): void {
    this.graph.batchUpdate(() => {
      commentRelations.forEach((targetNodeId, commentId) => {
        const commentNode = this.graph.getCellById(commentId);
        const targetNode = this.graph.getCellById(targetNodeId);

        if (commentNode?.isNode() && targetNode?.isNode()) {
          const nodePos = targetNode.position();
          const nodeSize = targetNode.size();

          // 将注释节点移动到目标节点的正下方
          const commentX = nodePos.x;
          const commentY = nodePos.y + nodeSize.height + 4;

          this.updateCommentNodePosition(commentNode, commentX, commentY);
        }
      });
    });
  }

  /**
   * 检查注释节点位置是否与其他节点重叠，并处理重叠情况
   * @param commentNode
   * @param targetX
   * @param targetY
   * @private
   */
  private handleCommentNodeOverlap(commentNode: Node, targetX: number, targetY: number): void {
    const commentBBox = commentNode.getBBox();

    // 创建检测矩形：宽度略大于注释节点，高度为画布高度
    const detectionRect: Rectangle = {
      x: targetX - 5,          // 左边留5px余量
      y: targetY,
      width: commentBBox.width + 10,
      height: commentBBox.height + 10,
    } as Rectangle;

    // 获取所有节点
    const allNodes = this.graph.getNodes();
    // 统计下方节点
    const bottomNodes: Node[] = [];
    let needMoveBottom: boolean = false;

    // 统计需右移节点
    const rightNodes: Node[] = [];
    let needMoveRight: boolean = false;
    // 检查右侧节点是否需要右移,目标节点在（注释节点对应的 普通节点 的右边线）与（检测框 的右边线）之间
    allNodes.forEach(node => {
      if (node.id !== commentNode.id) {  // 排除节点本身
        const nodeBBox = node.getBBox();
        if (nodeBBox.x > targetX + 380) {
          rightNodes.push(node);
          if (nodeBBox.x < detectionRect.x + detectionRect.width) {
            needMoveRight = true;
          }
        }
      }
    });
    // 执行右移操作
    if (needMoveRight) {
      this.moveNodesToRight(rightNodes, detectionRect.x + detectionRect.width);
    }
    // 检查哪些节点与检测矩形重叠
    allNodes.forEach(node => {
      if (node.id !== commentNode.id) {  // 排除注释节点本身
        const nodeBBox = node.getBBox();
        if (!(nodeBBox.x > detectionRect.x + detectionRect.width ||
          nodeBBox.x + nodeBBox.width < detectionRect.x ||
          nodeBBox.y + nodeBBox.height < detectionRect.y)) {
          bottomNodes.push(node);
        }
      }
    });

    // 执行下移操作
    if (bottomNodes.length) {
      this.moveNodesToDown(bottomNodes, detectionRect.y + detectionRect.height);
    }
  }

  /**
   * 将目标节点移动到目标线右侧
   * @param targetNodes
   * @param targetX
   * @private
   */
  private moveNodesToRight(targetNodes: Node[], targetX: number) {
    // 找出目标节点中最左侧的边
    let mostLeftEdge = Number.MAX_VALUE;
    targetNodes.forEach(node => {
      const nodeBBox = node.getBBox();
      mostLeftEdge = Math.min(mostLeftEdge, nodeBBox.x);
    });
    // 计算要向右移动的距离，20安全距离
    const moveDistance = targetX - mostLeftEdge + 20;
    // 使用批量更新，将目标节点右移
    this.graph.batchUpdate(() => {
      targetNodes.forEach(node => {
        const currentPosition = node.position();
        node.position(currentPosition.x + moveDistance, currentPosition.y);
      });
    });
  }

  /**
   * 将目标节点移动到目标线下侧
   * @param targetNodes
   * @param targetY
   * @private
   */
  private moveNodesToDown(targetNodes: Node[], targetY: number): void {
    // 找出目标节点中最低的边缘
    let lowestEdge = Number.MAX_VALUE;
    targetNodes.forEach(node => {
      const nodeBBox = node.getBBox();
      lowestEdge = Math.min(lowestEdge, nodeBBox.y);
    });

    // 计算需要下移的距离（确保注释节点与重叠节点之间有20px间距）
    const moveDistance = targetY - lowestEdge + 200;

    // 使用批量更新，将所有目标节点下移
    this.graph.batchUpdate(() => {
      targetNodes.forEach(node => {
        const currentPosition = node.position();
        node.position(currentPosition.x, currentPosition.y + moveDistance);
      });
    });
  }

  /**
   * 更新注释节点位置，自动处理重叠
   * @param commentNode
   * @param x
   * @param y
   * @private
   */
  private updateCommentNodePosition(commentNode: Node, x: number, y: number): void {
    // 先处理重叠问题
    this.handleCommentNodeOverlap(commentNode, x, y);

    // 设置注释节点位置
    commentNode.position(x, y);
  }

  public openReleaseHistoryModal() {
    this.showHistoryModal = true;
    this.agentDataServe.setPublishStatus('');
    this.appFlowServ.setNodeClicked(EHalfmodalType.HISTORY);
  }

  public publishAgent() {
    if (this.type === 'multi') {
      this.handelPublish();
    } else {
      this.coloseAllWindow();
      // 调用校验接口,有问题改问题,没问题发布版本
      this.coloseAllWindow();
      MaskComponent.show();
      setTimeout(async () => {
        MaskComponent.hide();
        this.isStartCheckErrorWorkFlow = true;
        await this.checkErrorWorkFlow(false, '', true);
      }, 2000);
    }
  }

  handelPublish() {
    const modalRef = this.nzModal.create({
      nzContent: PublishVersionModalComponent,
      nzWidth: 600,
      nzMaskClosable: false,
      nzFooter: null,
    });
    Object.assign(modalRef.componentInstance, {
      app_id: this.workflowId,
      app_type: this.type === 'multi' ? 'multi' : 'flow',
      from: this.isFromEditFlow ? 'edit-flow' : '',
      orginWorkflowId: this.orginWorkflowId,
      workflowType: this.workflow_type,
      title: this.i18n.transform(
        this.historyVersionList.length > 0
          ? 'update_version'
          : 'submit_version',
      ),
    });
    (modalRef.componentInstance as any).outputs = {
      publishSuccess: () => {
        this.updateFlowData();
      },
      clickShare: () => {
        if (this.curActiveConfigTabId === this.configHeaderTabs[1].id) {
          this.publishChannelPage.initFn();
        } else {
          if (!this.historyVersionList?.length) {
            const getVersionsFn =
              this.type === 'multi'
                ? this.getAgentVersions
                : this.getFlowVersionsFn;
            getVersionsFn(() => {
              this.configHeaderTabs[0].active = false;
              this.configHeaderTabs[1].active = true;
              this.configTabActiveChange(this.configHeaderTabs[1].id);
            });
          } else {
            this.configHeaderTabs[0].active = false;
            this.configHeaderTabs[1].active = true;
            this.configTabActiveChange(this.configHeaderTabs[1].id);
          }
        }
      },
      close: () => {
        this.workflowDetail.publish_time = Date.now();
      },
    };
  }

  private useAddPluginModal(callback: (plugin: IPlugin) => void) {
    const addedPluginList = this.workflowDetail.workflow_details.nodes.filter(
      (node) => {
        return node.type === 'Plugin';
      },
    );
    this.appFlowServ.setPluginList(addedPluginList);
    this.pluginCallback = callback;
    const outputs = {
      pluginChange: callback,
    };
    this.pluginModalRef = this.nzDrawerService.create({
      nzTitle: this.i18n.transform('addpluginmodalcomponent_252'),
      nzContent: AddPluginModalComponent,
      nzPlacement: 'right',
      nzWidth: '700px',
      nzClosable: true,
      nzMaskClosable: true,
      nzWrapClassName: 'percent-halfmodal',
      nzContentParams: {
        addedPluginList: addedPluginList,
        outputs,
      },
    });
  }

  private useAddFlowModal(
    callback: ({
                 workflow,
                 config,
               }: {
      workflow: IWorkflow;
      config: any;
    }) => void,
  ) {
    this.childFlowCallback = callback;
    const outputs = {
      workflowChange: callback,
    };
    this.childFlowModalRef = this.nzDrawerService.create({
      nzTitle: '',
      nzContent: AddChildFlowModalComponent,
      nzPlacement: 'right',
      nzWidth: '700px',
      nzClosable: true,
      nzMaskClosable: true,
      nzWrapClassName: 'percent-halfmodal',
      nzContentParams: {
        workflowType: this.workflowDetail.type,
        workflowId: this.workflowDetail.workflow_id,
        outputs,
        isAgentPage: false,
        isAgentSingle: true,
        workflowSelected: [],
        workflowSelectedLimit: 1,
      },
    });
  }

  private useAddMcpModal(
    callback: (mcpService: IMCPService) => void,
    type: string,
  ) {
    this.mcpServiceCallback = callback;
    const outputs = {
      mcpServiceChange: callback,
      createMcpRes: (data: any) => {
        this.createMcpResEmit(data);
      },
    };
    this.mcpModalRef = this.nzDrawerService.create({
      nzTitle: '',
      nzContent: AddMCPServiceModalComponent,
      nzPlacement: 'right',
      nzWidth: '700px',
      nzClosable: true,
      nzMaskClosable: true,
      nzWrapClassName: 'percent-halfmodal',
      nzContentParams: {
        type: type,
        mcpCreateSub: this.createMcpSub$,
        outputs,
      },
    });
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return '800px';
    } else {
      return '600px';
    }
  }

  public createMcpResEmit(event: any) {
    if (event.result === 'success') {
      this.mcpService
        .getMcpToolInfo(event.data.id)
        .then(() => {
          this.isShowSuccessAlert = true;
          this.createNewMcpData = event?.data || {};
          this.autoCloseAlert();
        })
        .catch(() => {
          this.isShowFailAlert = true;
        });
    } else if (event?.result === 'fail') {
      this.isShowFailAlert = true;
    }
  }

  async handleClickAddNewMcpService() {
    this.isShowSuccessAlert = false;
    this.createMcpSub$.next(this.createNewMcpData);
  }

  @HostListener('window:keydown', ['$event'])
  handleKeyDown(event: KeyboardEvent) {
    if (this.isShowRename) {
      return;
    }
    if (
      !this.workflowDetail ||
      this.isFlowReadonly ||
      this.notUserSelf ||
      this.type === 'multi'
    ) {
      return;
    }

    const isWinDel =
      !this.isMac && (event.key === 'Delete' || event.key === 'Backspace');
    const isMacDel = this.isMac && event.key === 'Backspace';
    const curSelectId = this.nodeServ.getCurrSelectedNodeId();
    const nodeInfo = this.getNodeInfoById(curSelectId);

    if (isWinDel || isMacDel) {
      if (this.graph.getSelectedCells().length > 0) {
        if (document.querySelector('ti-modal-wrapper')) {
          return;
        }

        const activeElement = document.activeElement;
        if (activeElement && activeElement !== document.body) {
          return;
        }
        this.selectionDel();
        return;
      }
      if (curSelectId && !UnDeletableNodeTypes.includes(nodeInfo?.type)) {
        if (document.querySelector('ti-modal-wrapper')) {
          return;
        }

        const activeElement = document.activeElement;
        if (activeElement && activeElement !== document.body) {
          return;
        }

        this.deleteNode(curSelectId);
        this.nodeServ.setCurrSelectedNode('');
        this.closeNodeConfigDrawer();
        return;
      }

      if (this.selectedEdgeId) {
        this.graph.removeEdge(this.selectedEdgeId);
        this.updateRef();
        this.keyDownSubject.next();
      }
    }

    const opKey = this.isMac ? event.metaKey : event.ctrlKey;

    const isNodeConfOpenOrNoModal = [
      EHalfmodalType.NODE_CONFIG,
      EHalfmodalType.DEFAULT,
    ].includes(this.appFlowServ.getNodeClicked());

    //复制粘贴时有侧边栏存在都不允许，精细控制需要使用id或者记录open事件
    let hasOtherHalfModal = false;
    const elements = document.querySelectorAll('tp-halfmodalcontainer');
    elements?.forEach((e) => {
      if (e.id !== 'flow-common-half-modal') {
        hasOtherHalfModal = true;
      }
    });

    const modalElements = document.querySelectorAll('ti-modal-body');
    modalElements?.forEach((e) => {
      if (e.id === 'update-modal-body' || e.id === 'publish-version-modal') {
        hasOtherHalfModal = true;
      }
    });

    //code节点代码编辑
    const codeEditorElement = document.querySelector('.function-graph-code-main');
    if (codeEditorElement) {
      hasOtherHalfModal = true;
    }


    // copy
    if (
      opKey &&
      event.key === 'c' &&
      curSelectId &&
      !UnDeletableNodeTypes.includes(nodeInfo?.type) &&
      isNodeConfOpenOrNoModal &&
      !hasOtherHalfModal
    ) {
      this.copiedNodeId = curSelectId;
      MessageComponent.showPrompt(this.i18n.transform('node_copied'));
      return;
    }

    // paste
    if (
      opKey &&
      event.key === 'v' &&
      this.copiedNodeId &&
      isNodeConfOpenOrNoModal &&
      !hasOtherHalfModal
    ) {
      this.copyNodeByIdDebounce();
    }

    // save
    if (opKey && event.key === 's') {
      event.preventDefault();

      this.saveSubject.next();

      return;
    }

    if (opKey && ['z', 'y'].includes(event.key)) {
      // undo
      if (opKey && event.key === 'z') {
        this.undo();
      }

      // redo
      if (opKey && event.key === 'y') {
        this.redo();
      }
      return;
    }

    if (event.code === 'Space') {
      //空格
      this.isKeyDownSpace = true;
      //禁用框选
      this.graph.enablePanning();
      this.graph.disableRubberband();
      return;
    }
    if (event.code === 'Tab') {
      //空格
      event.stopPropagation();
      event.preventDefault();
      this.onClickShowAddNodesWidget(event);
      return;
    }

    // 指针模式
    if (!opKey && (event.key === 'v' || event.key === 'V')) {
      this.changeDragMode(DragMode.POINTER);
      return;
    }

    // 手模式
    if (event.key === 'h' || event.key === 'H') {
      this.changeDragMode(DragMode.HAND);
      return;
    }

    // 连接到结束节点
    if ((event.key === 'q' || event.key === 'Q') && nodeInfo) {
      this.linkToEndNode(nodeInfo?.id);
      return;
    }
    //全选
    if (opKey && event.key === 'a' &&
      isNodeConfOpenOrNoModal &&
      !hasOtherHalfModal) {
      event.stopPropagation();
      event.preventDefault();
      const nodes = this.graph.getNodes();
      this.graph.select(nodes);
      return;
    }
  }

  @HostListener('window:keyup', ['$event'])
  handleKeyUp(event: KeyboardEvent) {
    if (event.code === 'Space') {
      //空格
      this.isKeyDownSpace = false;
      //启用框选
      if (this.dragMode === DragMode.POINTER) {
        this.graph.enableRubberband();
        this.graph.disablePanning();
      }
      return;
    }
  }

  linkToEndNode(id: string) {
    const endNode = this.graph.getCells().find((cell) => {
      const nodeInfo = this.getNodeInfoById(cell.id);
      return nodeInfo?.type === 'End';
    });
    const currentNode = this.graph.getCellById(id);
    if (!currentNode || !endNode) {
      return;
    }
    if (currentNode.hasParent()) {
      return;
    }
    if (endNode.id !== id) {
      const exist = this.appFlowServ.judgeLinkedEdge(
        this.graph,
        id,
        endNode.id,
      );
      if (exist) {
        return;
      }
      const currentNodePorts = (currentNode as Node).getPorts();
      const endNodePorts = (endNode as Node).getPorts();
      const leftPort = endNodePorts.find((port) => port.group === 'left');
      const rightPort = currentNodePorts.find((port) => port.group !== 'left');
      if (!leftPort || !rightPort) {
        return;
      }
      const rightEdge = this.graph.addEdge({
        shape: 'dag-edge',
        source: {
          cell: currentNode.id,
          port: rightPort.id,
        },
        target: {
          cell: endNode.id,
          port: leftPort.id,
        },
      });
      this.onEdgeConnected(rightEdge);

      this.hiddenAddNodePanel();
      this.updateRef();
      this.updateFlowData();
    }
  }

  private getNodeInfoById(id: string) {
    return this.graph?.getCellById(id)?.data?.ngArguments
      ?.nodeInfo as NodeInfo | null;
  }

  public addExceptionPort(node: Node<NodeProperties>) {
    const currentIds = node
      .getPorts()
      .filter((p) => p.group !== 'left')
      .map((p) => p.id) as string[];
    if (currentIds.includes('exception_branch')) {
      return;
    }
    node.insertPort(currentIds.length, {
      id: 'exception_branch',
      group: 'right',
      attrs: {
        circle: {
          fill: FLOW_COLORS.defaultPort,
          [PORT_CONNECTED_ATTR]: PORT_CONNECTED.defaultPort,
        },
      },
    });
  }

  public removeExceptionPort(node: Node<NodeProperties>) {
    const eb_port = node
      .getPorts()
      .find((p) => p.group !== 'left' && p.id === 'exception_branch');
    if (eb_port) {
      node.removePort(eb_port);
    }
  }

  private handleMultiPortNodeExpand(
    node: Node<NodeProperties>,
    nodeUpdate: INodeHeightUpdate,
  ) {
    this.flowHelperServ.handleMultiPortNodeExpand(node, nodeUpdate);
  }

  private fixRefTypeOutdate(
    field: IWorkflowField,
    newRefs: IRefIndex[],
    node?: any,
  ) {
    if (!field) {
      return false;
    }

    let changedField = false;
    if (field.value.type === 'ref') {
      for (const index of newRefs) {
        if (
          NodeUtils.refContentStringify(
            field.value.content as IRefContentType,
          ) === index.id
        ) {
          field.type = index.type;

          if (['array', 'object'].includes(field.type)) {
            this.changeLLMVisionName(field, index, node);
            field.schema = index.schema;
          } else if (field?.schema) {
            delete field.schema;
          } else {
            // do nth
          }

          changedField = true;
          break;
        }
      }
    }

    return changedField;
  }

  /**
   * llm节点 视觉参数，需要根据类型修改名称
   * @param field
   * @param newRef
   * @param node
   * @private
   */
  private changeLLMVisionName(field: IWorkflowField, newRef: any, node: any) {
    if (node?.type !== 'LLM') {
      return;
    }
    if (!node?.configs?.vision) {
      return;
    }
    const type = newRef.schema?.type;
    if (field.name.startsWith('_image_vision_') && type === 'file/video') {
      const originIndex =
        node.configs.vision.findIndex((v) => {
          return v === field.name;
        }) ?? 0;
      field.name = field.name.replace('_image_', '_video_');
      node.configs.vision[originIndex] = field.name;
    } else if (
      field.name.startsWith('_video_vision_') &&
      type === 'file/image'
    ) {
      const originIndex =
        node.configs.vision.findIndex((v) => {
          return v === field.name;
        }) ?? 0;
      field.name = field.name.replace('_video_', '_image_');
      node.configs.vision[originIndex] = field.name;
    }
  }

  /**
   * 遍历 affectedNodeId 及其后继节点
   * 更新的引用类型
   * @param affectedNodeId 变更节点的直接后继
   * @param updatedRefs 需要更新的引用索引上下文
   */
  private updateRefType(affectedNodeId: string, updatedRefs: IRefIndex[]) {
    if (updatedRefs?.length) {
      const loopCells = [];
      const cell = this.graph.getCellById(affectedNodeId);
      const cellNodeData = cell.getData()?.ngArguments?.nodeInfo as NodeInfo;

      if (cellNodeData.type === 'Loop') {
        loopCells.push(cell);
      }

      const successors: (HasInputsNode | IBranchNode)[] = this.graph
        .getSuccessors(cell)
        .map((successor) => {
          const nodeInfo = successor.getData()?.ngArguments?.nodeInfo as
            | HasInputsNode
            | IBranchNode;

          if (nodeInfo.type === 'Loop') {
            loopCells.push(successor);
          }

          return nodeInfo;
        });

      const affectedNodes = [cellNodeData, ...successors];

      loopCells.forEach((loop) => {
        const subs = loop
          .getChildren()
          .filter(
            (child) =>
              child.isNode() &&
              !['LoopInput', 'LoopOutput'].includes(
                child?.data.ngArguments?.nodeInfo?.type,
              ),
          )
          .map((child) => child.getData()?.ngArguments?.nodeInfo);

        if (subs.length) {
          affectedNodes.push(...subs);
        }
      });

      affectedNodes.forEach((affectedNode) => {
        let isChanged = false;

        if (affectedNode.type === 'Branch') {
          const newBranches = (affectedNode as IBranchNode).branches.map(
            (branch) => {
              if (branch?.configs) {
                const newConditions = branch.configs.conditions.map(
                  (condition) => {
                    const innerIsChanged =
                      this.fixRefTypeOutdate(condition.left, updatedRefs) ||
                      this.fixRefTypeOutdate(condition.right, updatedRefs);

                    if (!isChanged && innerIsChanged) {
                      isChanged = innerIsChanged;
                    }

                    return condition;
                  },
                );

                if (isChanged) {
                  branch.configs.conditions = newConditions;
                }
              }

              return branch;
            },
          );

          if (isChanged) {
            (affectedNode as IBranchNode).branches = newBranches;
            this.updateNodeData(affectedNode);
          }
        } else {
          if (!(affectedNode as ISetVariableNode).inputs) {
            return;
          }
          const newInputs = (affectedNode as HasInputsNode)?.inputs.map(
            (input) => {
              const innerIsChanged = this.fixRefTypeOutdate(
                input,
                updatedRefs,
                affectedNode,
              );

              if (!isChanged && innerIsChanged) {
                isChanged = innerIsChanged;
              }

              if (
                affectedNode.type === 'Loop' &&
                innerIsChanged &&
                input.name === 'arr_loop_var' &&
                input.type.startsWith('array')
              ) {
                const arrayLoopItemField = cloneDeep(input);
                arrayLoopItemField.name = `${arrayLoopItemField.name}.item`;
                arrayLoopItemField.type = (
                  arrayLoopItemField.schema as IWorkflowField
                ).type;

                if (arrayLoopItemField.type === 'object') {
                  arrayLoopItemField.schema = (
                    arrayLoopItemField.schema as IWorkflowField
                  ).schema;
                } else {
                  delete arrayLoopItemField.schema;
                }

                const changedLoopRefs = NodeUtils.getOutputsRefIndex(
                  affectedNode.id,
                  [arrayLoopItemField],
                );

                updatedRefs.push(
                  ...changedLoopRefs.filter((ref) => !ref.id.endsWith('[0]')),
                );
              }
              // 全局配置修改后需要同步更新变量赋值节点中引用的参数类型
              if (affectedNode.type === 'SetVariable' && innerIsChanged) {
                (affectedNode as ISetVariableNode).configs.settings =
                  FlowUtils.getSetvariableNewSettings(affectedNode);
              }

              return input;
            },
          );

          if (isChanged) {
            (affectedNode as HasInputsNode).inputs = newInputs;
            this.updateNodeData(affectedNode);
          }

          if (affectedNode.type === 'End') {
            //处理结束节点的输出参数类型
            let outputIsChanged = false;
            const newOutputs = (affectedNode as IEndNode)?.outputs.map(
              (output) => {
                const innerIsChanged = this.fixRefTypeOutdate(
                  output,
                  updatedRefs,
                  affectedNode,
                );

                if (!outputIsChanged && innerIsChanged) {
                  outputIsChanged = innerIsChanged;
                }
                return output;
              },
            );
            if (outputIsChanged) {
              (affectedNode as IEndNode).outputs = newOutputs;
              this.updateNodeData(affectedNode);
            }
          }
        }
      });
    }
  }

  /**
   * 检查更新节点的后继节点是否引用了被删除的输出参数
   * @param oldNodeData 节点更新前的数据
   * @param nodeData 节点更新后的数据
   */
  private checkRefChangeAndUpdateNode(
    oldNodeData: NodeInfo,
    nodeData: NodeInfo,
  ) {
    this.updateNodeData(nodeData);

    if (
      nodeData && !NoOutputsNodeTypes.includes(nodeData.type) &&
      nodeData.type !== 'Plugin'
    ) {
      const cell = this.graph.getCellById(nodeData.id);
      const successors = this.graph
        .getSuccessors(cell)
        .map((successor) => successor.getData()?.ngArguments?.nodeInfo);

      if (successors.length) {
        const oldRefs = NodeUtils.getOutputsRefIndex(
          nodeData.id,
          (oldNodeData as HasOutputsNode).outputs as IWorkflowField[],
        );
        const currRefs = NodeUtils.getOutputsRefIndex(
          nodeData.id,
          (nodeData as HasOutputsNode).outputs as IWorkflowField[],
        );

        const updatedRefs = currRefs.filter((ref) => {
          const needUpdate = oldRefs.find((oldRef) => {
            if (oldRef.id === ref.id) {
              if (
                oldRef.type === ref.type &&
                isEqual(oldRef?.schema, ref?.schema)
              ) {
                return false;
              }

              return true;
            }

            return false;
          });

          return !!needUpdate;
        });

        this.updateRefType(successors[0].id, updatedRefs);
      }
    }
  }

  private setRefInfo(nodeId: string) {
    this.nodeServ.setRefInfo(this.getPredecessorsRef(nodeId));

    const pCell = this.graph.getCellById(nodeId)?.getParent();
    if (pCell && FlowUtils.getNodeDSLFromRaw(pCell as Node).type === 'Loop') {
      this.nodeServ.setParentRefInfo(this.getPredecessorsRef(pCell.id));
    }
  }

  openNodeModal(nodeInfo: any, exict: Array<any> = []): void {
    const newexict = [...exict, 'checkErrorWorkflowHalfModalRef'];
    if (this.route.snapshot.queryParams.fromShare === 'true') {
      // 共享的节点不能点
      return;
    }
    // 如果接口loading中，直接跳过
    const nodeStatus = this.saveStatusMap.get(nodeInfo.id);
    if (this.type !== 'multi' && nodeStatus === true) {
      return;
    }
    this.nodeServ.setCurrSelectedNode(nodeInfo.id);
    this.coloseAllWindow(newexict);
    // MCP服务被删除后，点击节点时阻止对话框弹出
    if (nodeInfo.type === 'Mcp' && !(nodeInfo as IMcpNode).configs.valid) {
      return;
    }
    this.nodeServ.setCurrSelectedNode(nodeInfo.id);
    const width =
      document.querySelector('body').offsetWidth >= 1920 ? '600px' : '550px';
    let cmp = NodeMap[nodeInfo.type];
    if (nodeInfo.type === 'Workflow' && this.type === 'multi') {
      cmp = WorkflowModalComponent;
    }
    if (nodeInfo.type === 'Workflow' && this.type === 'multi') {
      // 得到该工作流挂在在agents的类型
      this.workflow_parent_node_type =
        this.judgmentWorkflowParentType(nodeInfo);
    }
    if (FlowUtils.isSingleAgentNodeType(this.type === 'multi', nodeInfo)) {
      cmp = SingleAgentModalComponent;
    }
    if (cmp) {
      if (this.type !== 'multi') {
        this.setRefInfo(nodeInfo.id);
      }

      if (nodeInfo.type === 'Loop') {
        this.appFlowServ.setLoopInnerRal(null);
      }

      if (nodeInfo.type === 'IntentDetectionContainer') {
        this.getIntentGroupId(nodeInfo);
      }

      if (nodeInfo.type === 'Card') {
        // 卡片更新标志
        const {id, version_id} = (nodeInfo as ICardNode).configs || {};
        const matchedFlow = this.ref_workflows?.find(
          (item) => item?.workflow_id === id,
        );
        if (
          matchedFlow &&
          matchedFlow.last_version_id &&
          (Number(matchedFlow.last_version_id) > Number(version_id) ||
            !version_id)
        ) {
          (nodeInfo as ICardNode).configs.showIcon = true;
          (nodeInfo as ICardNode).configs.ref_workflows = matchedFlow;
        } else {
          (nodeInfo as ICardNode).configs.showIcon = false;
          (nodeInfo as ICardNode).configs.ref_workflows = null;
        }
      }
      const draggablList = [
        'Start',
        'LLM',
        'Code',
        'Input',
        'ParamExtraction',
        'Sql',
      ];
      // 设置 可拖动弹窗的范围
      const modalDraggable = draggablList.includes(nodeInfo.type);
      // 哪些节点不可以拖动
      const notDraggableList = [''];
      // 设置 不可拖动弹窗的范围
      const notModalDraggable = notDraggableList.includes(nodeInfo.type);

      this.nodeConfigNodeInfo = nodeInfo;
      this.nodeConfigNodeType = nodeInfo.type;
      this.nodeConfigNames = FlowUtils.getGraphNodeNames(this.graph);
      this.nodeConfigDrawerWidth = width;

      this.nodeConfigCallback = async (nodeData: NodeInfo) => {
        this.updateFlowDataLoading = true;
        this.exceptionBranchHandler(nodeData);
        nodeData = NodeUtils.traversalNodeSource(nodeData);
        this.nodeServ.setIsConfirmLoading(true);
        this.isResetNodeHeightMap = true;
        let isSkipUpdateFlow = false;
        if (FlowUtils.isAdvancedModeNew(nodeData)) {
          isSkipUpdateFlow = true;
          nodeData.name = FlowUtils.uniqueIntentName(
            this.graph,
            nodeData,
            true,
          );
          const uuid = nodeData.id.split('_')[1];
          const containerNodeId = `node_intent_container_${uuid}`;
          const isContainerNode = this.graph.getCellById(containerNodeId);
          this.createIntentContainerNode(nodeData.id);
          let bodyParams;
          setTimeout(async () => {
            if (isContainerNode) {
              bodyParams = FlowUtils.updateContainerNodeDsl(
                this.graph,
                this.workflowDetail,
                nodeData,
                containerNodeId,
                this.getNodeInfoById.bind(this),
                this.appFlowServ,
              );
            }
            this.handleAdvancedIntentConns(nodeData.id);
            this.updateRef();
            await this.updateFlowData(
              {
                isDrag: false,
                successCb: () => {
                  this.halfModalRef?.close();
                  if (isContainerNode) {
                    this.appFlowServ.setAppRefs(this.ref_workflows);
                    FlowUtils.syncContainerInfoToGraph(
                      this.graph,
                      bodyParams,
                      containerNodeId,
                    );
                  }
                },
              },
              bodyParams,
            );
          });
        }
        if (FlowUtils.isNormalMode(nodeData)) {
          nodeData.name = FlowUtils.uniqueIntentName(
            this.graph,
            nodeData,
            false,
          );
          this.deleteContainerNode(nodeData.id, false);
        }

        if (nodeData.id === 'node_start') {
          this.isStartNodeBtnClicked = true;
        }
        this.checkRefChangeAndUpdateNode(nodeInfo, nodeData);

        if (nodeData.type === 'SubController') {
          const exceedsList = this.appFlowServ.judgeExceedsSubController(this.graph)
          if (exceedsList.length) {
            const exceedsStr = exceedsList.join(',')
            MessageComponent.showError(`绑定子智能体【${exceedsStr}】达到最大深度限制，请删除后重试`, 5000);
            return
          }
          const controller_node: any =
            this.workflowDetail.details.nodes.find(
              (contr_item) => contr_item.type === 'Controller',
            );
          controller_node.configs?.agents?.forEach((ag) => {
            if (ag.node_id === nodeData.id) {
              ag.configs.intent = (
                nodeData as IControllerNode
              ).configs.intent;
            }
          });
          this.updateAgentsNodeData(controller_node);
          this.updateAgentsNodeData(nodeData);
        } else {
          this.updateNodeData(nodeData);
        }

        try {
          if (isSkipUpdateFlow) {
            return;
          }
          if (this.type === 'multi' && nodeData.type === 'Controller') {
            if (nodeData.type === 'Controller') {
              const {workflows, agents} = (nodeData as IControllerNode)
                .configs;
              this.createMultiAgentTree(workflows, agents);
            }
          }
          await this.updateFlowData({
            isDrag: false,
            successCb: () => {
              this.halfModalRef?.close();
              if (
                nodeData.type === 'ParamExtraction' ||
                nodeData.type === 'Card'
              ) {
                this.appFlowServ.setAppRefs(this.ref_workflows);
                FlowUtils.syncParamExtractionInfoToGraph(
                  this.graph,
                  this.workflowDetail,
                  nodeData.id,
                );
                this.checkResNodesUpdate();
              }
            },
          });
        } finally {
          this.nodeServ.setIsConfirmLoading(false);
          if (this.isFlowValidated) {
            await this.getFlowValidateRes(false);
          }
          if (nodeData.type === 'Controller') {
            this.checkResNodesUpdate();
          }
          this.updateFlowDataLoading = false;
        }
        this.updateFlowDataLoading = false;
      };

      this.halfModalNodeId = nodeInfo.id;
      this.halfModalRef = this.nzDrawerService.create({
        nzTitle: '',
        nzContent: cmp,
        nzPlacement: 'right',
        nzWidth: width,
        nzClosable: true,
        nzMaskClosable: true,
        nzMask: false,
        nzWrapClassName: 'flow-common-half-modal',
        nzContentParams: {
          nodeInfo,
          names: FlowUtils.getGraphNodeNames(this.graph),
          workflowType: this.workflowDetail.type,
          workflow_parent_node_type: this.workflow_parent_node_type,
          outputs: {
            confirm: this.nodeConfigCallback,
            closeDrawer: () => {
              this.halfModalRef.close();
            },
            editCodeEvent: (data) => {
              this.editCodeModal = data;
            },
          },
        },
      });
      this.showNodeConfigDrawer = true

      this.halfModalRef.afterClose.subscribe(() => {
        this.halfModalNodeId = '';
      });

      this.adjustTopForNodeModal();
    }
  }

  exceptionBranchHandler(nodeData: NodeInfo) {
    if (EXCEPTION_PORT_NODE.includes(nodeData?.type)) {
      const exception_process = (nodeData as any).configs?.exception_process;
      if (!exception_process) {
        this.appFlowServ.setExceptionPort({
          nodeId: nodeData.id,
          operate: 'remove',
        });
        return;
      }
      let target: any = {
        timeout: exception_process.timeout,
        retry_times: exception_process.retry_times,
        handle_type: exception_process.handle_type,
      };
      if (exception_process.handle_type === 'errorbranch') {
        this.appFlowServ.setExceptionPort({
          nodeId: nodeData.id,
          operate: 'add',
        });
      } else {
        this.appFlowServ.setExceptionPort({
          nodeId: nodeData.id,
          operate: 'remove',
        });
      }
      if (exception_process.handle_type === 'defaultOutputs') {
        if (typeof exception_process.default_outputs === 'string') {
          try {
            target.default_outputs = JSON.parse(
              exception_process.default_outputs,
            );
          } catch (e) {
            target.default_outputs = {};
          }
        } else {
          target.default_outputs = exception_process.default_outputs;
        }
      }
      (nodeData as any).configs.exception_process = target;
    }
    if (nodeData?.type === 'ParamExtraction') {
      if (
        (nodeData as any).configs?.exception_config?.exception_condition
          ?.conditions?.length
      ) {
        this.appFlowServ.setExceptionPort({
          nodeId: nodeData.id,
          operate: 'add',
        });
      } else {
        this.appFlowServ.setExceptionPort({
          nodeId: nodeData.id,
          operate: 'remove',
        });
      }
    }
  }

  /** 调用接口，刷新工作流节点的校验状态 */
  private async getFlowValidateRes(isShowModal: boolean) {
    const validateRes = await this.validateWorkflow();
    const {success, errors} = validateRes;
    if (success) {
      this.appFlowServ.setFlowErrors({
        success,
        errors,
      });
      if (isShowModal) {
        this.showRunModal = true;
      }
    } else {
      this.appFlowServ.setFlowErrors({
        success,
        errors,
      });
      if (isShowModal) {
        const errorNodeCount = new Set(errors.map((error) => error.id)).size;
        MessageComponent.showError(
          this.i18n.transform('error_node_count_tip', {errorNodeCount}),
        );
        this.showRunModal = false;
      }
    }
  }

  // 试运行失败点击弹出调试
  clickErrorInfo(e) {
    this.openLogHalfmodal(['runTestHalfModel']);
  }

  dialogHalfmodalClose() {
    this.showRunModal = false;
    this.flowHelperServ.adjustRightForNodeModal('', 'right');
  }

  /** 校验工作流 */
  private async validateWorkflow() {
    return this.appFlowRepoServ.validateFlow(this.workflowId);
  }

  updateRef() {
    const nodeId = this.nodeServ.getCurrSelectedNodeId();

    if (nodeId) {
      this.setRefInfo(nodeId);
    }
  }

  private updateAnalyzeTabStatus(disabled: boolean) {
    const analyzeIndex = this.headerTabs.findIndex(
      (tab) => tab.id === 'analyze',
    );

    this.headerTabs[analyzeIndex].disabled = disabled;
  }

  private async rollbackFlowVersion(version) {
    try {
      await this.initAppRefs(version.version_id);
      const data =
        this.type === 'multi'
          ? await this.appAgentRepoServ.rollbackAgentVersion(
            this.workflowId,
            version.version_id,
          )
          : await this.appAgentRepoServ.rollbackFlowVersion(
            this.workflowId,
            version.version_id,
          );

      if (this.type === 'multi') {
        data.workflow_details = data.details;
        data.avatar = data.icon;
      }
      document.title = data.name;
      this.useDataPaintWorkflow(data as IWorkflow);
      this.checkResNodesUpdate();
      this.initLoop(
        data.workflow_details.nodes
          .filter((node) => node.type === 'Loop')
          .map((node) => node.id),
      );
      if (this.type === 'multi') {
        // 刷新画布节点
        this.workflowDetail.details.nodes.forEach((node: any) => {
          if (!node.configs.valid) {
            this.updateNodeData(node);
          }
        });
      }

      if (version.revert) {
        this.updateFlowData({
          successCb: () => {
            MessageComponent.showSuccess(
              this.i18n.transform(
                this.i18n.transform('version_restored_successfully'),
              ),
              3000,
            );
          },
        });
      }
    } catch {
      // do nth
    }
  }

  private getZIndex(element: HTMLElement): number {
    const zIndex = window.getComputedStyle(element).zIndex;
    return zIndex === 'auto' ? 0 : parseInt(zIndex, 10);
  }

  /** 判断工作流中，资源节点是否需要升级新版本 */
  private checkResNodesUpdate() {
    let nodes = [];
    if (this.type === 'multi') {
      nodes = this.workflowDetail?.details?.nodes ?? [];
    } else {
      nodes = this.workflowDetail?.workflow_details?.nodes ?? [];
    }

    const ag_wf_list = [];
    if (this.type === 'multi') {
      const controller: any = nodes.filter(
        (node) => node.type === 'Controller',
      );

      controller[0]?.configs?.agents?.forEach((ag) => {
        if (ag.configs?.workflows) {
          ag_wf_list.push(...ag.configs.workflows);
        }
      });
    }

    const resourceNodes = nodes.filter(
      (node) =>
        versionedResNodes.includes(node?.type) ||
        node?.type === 'ParamExtraction',
    );

    resourceNodes.forEach((item: any) => {
      if (item.type === 'ParamExtraction') {
        const relationFlow = NodeUtils.getParamExtractionRelationFlow(item);
        item.showIcon = relationFlow.some((r) => {
          const matchedFlow = this.ref_workflows?.find(
            (refItem) => refItem?.workflow_id === r.id,
          );
          return (
            matchedFlow &&
            matchedFlow.last_version_id &&
            (Number(matchedFlow.last_version_id) > Number(r.version_id) ||
              !r.version_id)
          );
        });
        item.ref_workflows = this.ref_workflows;
      } else {
        let {id, version_id} = item?.configs || {};
        const matchedFlow = this.ref_workflows?.find(
          (item) => item?.workflow_id === id,
        );
        if (this.type === 'multi') {
          item.configs.valid = matchedFlow?.valid;
        }
        if (item.type === 'Workflow' && this.type === 'multi') {
          // 得到该工作流挂在在agents的类型
          item.parent_node_type = ag_wf_list.find((wf) => wf.node_id === item?.id)
            ?.parent_node_type ?? 'controller';
        }
        // 新增!version_id，用于兼容存量数据。绑定的资源是开发态，没有版本号
        if (
          matchedFlow &&
          matchedFlow.last_version_id &&
          (Number(matchedFlow.last_version_id) > Number(version_id) ||
            !version_id)
        ) {
          item.showIcon = true;
          item.ref_workflows = matchedFlow;
        } else {
          item.showIcon = false;
        }
      }
    });

    this.appFlowServ.setResNodes(resourceNodes);
  }

  /** 判断工作流中，资源节点是否失效 */
  private checkResNodesValid(value) {
    const nodes = value?.workflow_details.nodes ?? [];
    const resourceNodes = nodes.filter((node) =>
      [...versionedResNodes, ...nonVersionedResNodes].includes(node?.type),
    );

    resourceNodes.forEach((item: any) => {
      item.configs.valid = true;
      const {id, version_id} = item.configs ?? {};

      const matchRes = this.ref_workflows.find((r) => {
        // 没有版本管理的资源节点，只需根据资源id判断卡片样式
        if (nonVersionedResNodes.includes(item.type) && r.workflow_id === id) {
          return true;
        }

        if (r.workflow_id !== id) {
          return false;
        }

        // 说明是开发态
        if (!version_id) {
          return true;
        }

        // 说明是发布态
        return r?.resource_version === version_id;
      });

      if (matchRes) {
        item.configs.valid = matchRes.valid;
      }
    });
    return [...nodes];
  }

  /*agents 里的configs 由于details接口初始化时没有带出来，需要前端自己在外层找到，自己添加进去*/
  private updateAgentsConfigs(nodes) {
    const controller_nodes: any = nodes.filter(
      (node) => node.type === 'Controller',
    );
    //工作流也需要添加configs,inputs,outputs
    const controllerFlows = controller_nodes.length
      ? controller_nodes[0].configs?.workflows ?? []
      : [];
    this.updateWorkflowConfigs(controllerFlows, nodes);
    const agents_nodes = controller_nodes.length
      ? controller_nodes[0].configs?.agents ?? []
      : [];
    for (let i = 0; i < agents_nodes.length; i++) {
      const get_node = nodes.filter(
        (node) => node.id === agents_nodes[i].node_id,
      );
      agents_nodes[i].configs = get_node.length ? get_node[0].configs : [];

      //工作流也需要添加configs,inputs,outputs
      const subFlows = agents_nodes[i]?.configs?.workflows ?? [];
      this.updateWorkflowConfigs(subFlows, nodes);
    }
    if (agents_nodes.length) {
      nodes.forEach((node) => {
        if (node.type === 'Controller') {
          node.configs.agents = agents_nodes;
        }
      });
    }
    return nodes;
  }

  private updateWorkflowConfigs(workflows, nodes) {
    workflows.forEach((workflow) => {
      const resultNode = nodes.find((node) => node.id === workflow.node_id);
      if (resultNode) {
        workflow.configs = resultNode.configs;
        workflow.inputs = resultNode.inputs ?? [];
        workflow.outputs = resultNode.outputs ?? [];
      }
    });
  }

  /** 根据浏览器视口大小，自适应缩放工作流 */
  private flowZoomToFit() {
    setTimeout(() => {
      this.flowHelperServ.flowZoomToFit(this.graph);
    });
  }

  /** 若插件支持流式输出，使用自定义变量覆盖历史输出变量列表 */
  private updateStreamingPluginNodesOutputs(nodes: any[]) {
    return CommonUtils.updateStreamingPluginOutputs(nodes);
  }

  /** 将工作流中所有意图识别节点对应的模式，存入service */
  private setIntentModesMap(nodes: NodeInfo[]) {
    nodes.forEach((node: NodeInfo) => {
      if (
        node.type === 'IntentDetection' ||
        node.type === 'ComplexIntentDetection'
      ) {
        const nodeId = node.id;
        // 若configs对象中存在意图包，表示为高级模式
        const mode = FlowUtils.isAdvancedModeNew(node) ? 'advanced' : 'normal';
        this.appFlowServ.setModeOfIntentNode({
          node_id: nodeId,
          mode,
        });
      }
    });
  }

  /** 先移除以高级意图节点作为source的所有边，再连接上高级意图节点和容器节点 */
  private handleAdvancedIntentConns(nodeId: string) {
    const edges = this.graph.getConnectedEdges(nodeId);
    edges.forEach((item: any) => {
      if (item.source?.cell === nodeId) {
        this.graph.removeEdge(item.id);
      }
    });

    FlowUtils.linkIntentAndContainerNode(this.graph);
  }

  /** 增加意图容器节点 */
  private createIntentContainerNode(id: string) {
    const uuid = id.split('_')[1];
    const advancedNodeClicked = FlowUtils.getAdvancedNodeClicked(
      id,
      this.graph,
    );
    if (advancedNodeClicked) {
      const x = advancedNodeClicked.x + 480;
      const y = advancedNodeClicked.y;
      // 获取初始化的容器节点数据
      const containerDataAdded = {
        ...this.appFlowServ.getInitIntentContainerNodeData(uuid),
        x,
        y,
        shape: 'op-intentdetectioncontainer-node',
      };
      const parentNode = this.graph.getCellById(id).getParent();
      const containerCell = this.graph.addNode(
        FlowUtils.initNode(containerDataAdded, this.graph, this.type),
      );

      if (parentNode) {
        parentNode.addChild(containerCell);

        (
          parentNode.data.ngArguments.nodeInfo as ILoopNode
        ).configs.loop_body.push(containerDataAdded.id);
      }

      this.debounceSetMiniMap();
    }
  }

  /** 获取容器节点对应的高级意图节点配置的意图包id，传递给容器节点，用于获取意图分支列表 */
  private getIntentGroupId(nodeInfo: NodeInfo) {
    const advancedNodeUuid = nodeInfo.id.split('_')[3];
    const advancedNodeId = `node_${advancedNodeUuid}`;
    const advancedNode = this.getNodeInfoById(advancedNodeId);
    if (advancedNode) {
      const {configs} = advancedNode as IIntentNode;
      if (configs?.intent?.id) {
        (nodeInfo as any).intentId = configs.intent.id;
      }
    }
  }

  /** 删除意图容器节点 */
  private deleteContainerNode(intentNodeId: string, isUpdateFlowData: boolean) {
    const uuid = intentNodeId.split('_')[1];
    const nodeId = `node_intent_container_${uuid}`;
    const isContainerNode = this.graph.getCellById(nodeId);
    if (isContainerNode) {
      this.deleteNode(nodeId, isUpdateFlowData, true);
    }
  }

  public goToChannelPage() {
    const queryParams: any = {
      workflowId: this.workflowId,
      workflowType: this.workflow_type,
    };
    if (this.isFromDevelopSpace) {
      queryParams.from = 'develop-space';
    }
    const routeQueryParams = this.route.snapshot.queryParams;
    let _queryParams: Record<string, string> = {};
    if (routeQueryParams.from === 'agentBuilder') {
      Object.keys(routeQueryParams).forEach((key: string) => {
        if (key === 'from' || key === 'work_space_id') {
          _queryParams[key] = routeQueryParams[key];
        }
      });
    }

    this.publishParams = {...queryParams, ..._queryParams};
  }

  /** 以多Agent控制器作为根节点，使用树形布局算法，创建叶子节点添加到X6画布上 */
  private createMultiAgentTree(workflows: IControllerFlow[], agents) {
    const allNodeData = this.graph.getNodes().map((node: any) => ({
      ...node.getData(),
      ...node.getBBox(),
      position: node.position(), // 获取该节点在local坐标系中的坐标
    }));

    FlowUtils.deleteWorkflowNodes(
      allNodeData,
      workflows,
      this.deleteNode.bind(this),
    );

    FlowUtils.deleteSubControllerNodes(
      allNodeData,
      agents,
      this.deleteNode.bind(this),
      this.graph,
    );
    FlowUtils.applyTreeLayout(
      allNodeData,
      this.appFlowServ,
      workflows,
      agents,
      false,
      this.localScale,
      this.workflowDetail,
      this.graph,
    );
    this.flowZoomToFit();
    this.optimizeLayout(false);
  }

  /** 设置工作流是否为预览态 */
  private setFlowReadonly(isReadonly: boolean) {
    this.nodeServ.setIsReadonlyFlow(isReadonly);
    this.isFlowReadonly = isReadonly;
    this.graph.options.interacting = !isReadonly;
  }

  private addActionNode(node: IPluginNode | IFlowNode | IMcpNode) {
    const {x, y} = FlowUtils.getNodePosByAddFromBar(this.graph, node.type);
    this.graph.addNode(
      FlowUtils.initNode(
        {
          ...node,
          id: `node_${Date.now()}`,
          name: node.name,
          type: node.type,
          x,
          y,
          shape: `op-${node.type.toLowerCase()}-node`,
        },
        this.graph,
        this.type,
      ),
    );
  }

  private async initAppRefs(version_id = 'latest') {
    const params = {
      showlatest: true,
      version: version_id,
    };
    await this.appFlowRepoServ
      .getAppRefs(this.workflowId, params)
      .then((res: IAppRefList) => {
        this.ref_workflows = res.relations.map((item) => ({
          // 用于兼容历史逻辑（ref_workflows）
          last_version_id: item.resource_latest_version,
          last_version_name: item.resource_latest_version_name,
          workflow_id: item.resource_id,
          workflow_name: item.resource_name,
          valid: item.valid,
          resource_version: item.resource_version,
          app_type: item.app_type,
          latest_version_app_sub_type: item.latest_version_app_sub_type,
        }));
        this.cdr.markForCheck();
      })
      .finally(() => {
        this.appFlowServ.setAppRefs(this.ref_workflows);
        this.checkResNodesUpdate();
      });
  }

  async clickTestRun() {
    let status = await this.getAsyncFlowValidateRes();
    if (!status) {
      return;
    }

    this.router.navigate(['home/agent-center/app-flow/flow-async-test'], {
      queryParams: {
        id: this.workflowId,
        type: this.type,
        versionId: this.versionId,
      },
    });
    this.appFlowServ.setGraph(this.graph);
  }

  /** 调用接口，刷新工作流节点的校验状态 */
  private async getAsyncFlowValidateRes() {
    const validateRes = await this.validateWorkflow();
    const {success, errors} = validateRes;
    if (success) {
      this.appFlowServ.setFlowErrors({
        success,
        errors,
      });
    } else {
      this.appFlowServ.setFlowErrors({
        success,
        errors,
      });
      const errorNodeCount = new Set(errors.map((error) => error.id)).size;
      MessageComponent.showError(
        this.i18n.transform('error_node_count_tip', {errorNodeCount}),
      );
      return false;
    }
    return true;
  }

  public addAgent(info) {
    // 工作流的创建
    let tip = this.i18n.transform('flowcomponent_621');
    // 多智能体的创建
    if (info.multiFlowType) {
      tip = this.i18n.transform('flowcomponent_622');
    }
    const modalRef = this.nzModal.create({
      nzContent: UpdateNodeModalComponent,
      nzWidth: '520px',
      nzMaskClosable: false,
      nzClosable: true,
    });
    Object.assign(modalRef.componentInstance, {
      title: this.i18n.transform('configtoolscomponent_45'),
      context: tip,
    });
    modalRef.afterClose.subscribe(() => {
      if (info.multiFlowType) {
        const multiNode = this.workflowDetail.workflow_details.nodes.find(
          (node: any) => {
            return node.type === 'Controller';
          },
        );
        const node = this.graph.getCellById(multiNode.id);
        this.graph.trigger('node:click', {node: node});
      } else {
        this.handleWorkflow(info);
      }
      localStorage.removeItem('multiFlowTypeInfo');
    });
  }

  async handleWorkflow(info) {
    const flow = await this.appFlowRepoServ.getFlowVersionInfo(
      info.id,
      info.version,
    );

    this.appFlowRepoServ
      .getPublishedFlows({
        offset: 0,
        limit: LAZY_LOAD_LIMIT,
      })
      .then((result) => {
        let workflow: any =
          result?.workflow_version_list.find(
            (item) => item.workflow_id === info.id,
          ) ?? {};

        let config = {
          id: workflow.workflow_id,
          version_id: workflow.version_id,
          version_name: workflow.version_name,
          name: workflow.name,
          type: workflow.type,
          plugins: (
            flow.workflow_details.nodes.filter(
              (item) => item.type === 'Plugin',
            ) as IPluginNode[]
          ).map((item) => {
            return {
              id: item.id,
              version: '',
            };
          }),
        };
        const apiNodeData = this.appFlowServ.childFlow2ApiNode(flow);
        apiNodeData.configs = {
          ...apiNodeData.configs,
          ...config,
        };
        this.addActionNode(apiNodeData);
      });
  }

  functionGraphTestEvent(e) {
    const codeDom = document
      .getElementById('function-graph-code-id')
      ?.getBoundingClientRect();
    const flowExeDom = document
      .getElementById('flow-node-exe-id')
      ?.getBoundingClientRect();
    const showFlowExeDom = flowExeDom?.width > 0 && flowExeDom?.height > 0;
    const showCodeDom = codeDom?.width > 0 && codeDom?.height > 0;
    if (showFlowExeDom && showCodeDom) {
      return;
    }
    setTimeout(() => {
      ;
      this.editCodeModal = true;
    }, 0);
    this.appFlowServ.setNodeAction({
      type: 'test',
      id: this.nodeServ.getCurrSelectedNodeId(),
    });
  }

  functionGraphDisplayEvent(e) {
    this.editCodeModal = e;
  }

  /** 修改连线状态*/
  changeNodeLinkEdgeStatus(data) {
    if (!this.graph) {
      return;
    }
    const {node_id, status} = data || {};
    if (!node_id || !status) {
      return;
    }
    const node = this.graph.getCellById(node_id);
    const incomingEdges = this.graph.getConnectedEdges(node, {
      incoming: true,
    });
    incomingEdges.forEach((edge) => {
      if (!this.appFlowServ.judgeRunNodeExist(edge.getSourceCellId())) {
        return;
      }
      const edgeClass = 'running-line';
      if (status === 'loading') {
        this.graph.findView(edge).addClass(edgeClass);
      } else {
        this.graph.findView(edge).removeClass(edgeClass);
      }
    });
  }

  selectionCopy() {
    const selectionNodes = this.graph.getSelectedCells();
    if (selectionNodes) {
      const idMap = new Map();
      this.graph.batchUpdate(() => {
        let nodeIds = [];
        selectionNodes.forEach((node) => {
          const nodeInfo = this.getNodeInfoById(node.id);
          if (!node.getParent() && !UnCopyNodeTypes.includes(nodeInfo?.type)) {
            const newNodeId = this.copyNodeById(node.id, false);
            if (newNodeId) {
              nodeIds.push(node.id);
              idMap.set(node.id, newNodeId);
            }
          }
        });
        // 获取与选中节点相关的所有边
        const allEdges = this.graph.getEdges();

        const relatedEdges = allEdges.filter((edge) => {
          const source = edge.getSourceCell();
          const target = edge.getTargetCell();
          return (
            source &&
            target &&
            nodeIds.includes(source.id) &&
            nodeIds.includes(target.id)
          );
        });
        relatedEdges.forEach((edge) => {
          const edgeData = edge.toJSON();
          const {shape, source, target, zIndex} = edgeData;
          const copySource = idMap.get(source.cell);
          const copySourcePort = source.port.replaceAll(
            source.cell,
            idMap.get(source.cell),
          );
          const copyTarget = idMap.get(target.cell);
          const copyTargetPort = target.port.replaceAll(
            target.cell,
            idMap.get(target.cell),
          );

          const nodeZIndex = this.graph.getCellById(copySource).getZIndex();
          this.graph.addEdge(
            {
              id: `edge_${Date.now()}`,
              shape,
              source: {
                cell: copySource,
                port: copySourcePort,
              },
              target: {
                cell: copyTarget,
                port: copyTargetPort,
              },
              nodeZIndex,
            },
            {ignoreHistory: true},
          );
        });
        this.updateFlowData();
      });
    }
  }

  selectionDel() {
    const selectionNodes = this.graph.getSelectedCells();
    this.graph.batchUpdate(() => {
      selectionNodes.forEach((node) => {
        this.deleteNode(node.id, false);
      });
      this.updateFlowData();
    });
  }

  protected readonly changeUrl = cdnAssetUrl;

  public configTabActiveChange(id: string) {
    if (id === this.configHeaderTabs[1].id) {
      this.coloseAllWindow();
      this.goToChannelPage();
    }
    this.curActiveConfigTabId = id;
  }

  public setReleaseManageTab() {
    this.configHeaderTabs[1].disabled = !this.historyVersionList.length;
    this.configHeaderTabs[1].tips = this.historyVersionList.length
      ? ''
      : this.i18n.transform('submit_version_first');
  }

  confirmGuide() {
    this.accelerator_key_guide_visible.show = false;

    window.localStorage.setItem('accelerator_key_guide', 'read');
  }

  public onDragStart(e: MouseEvent) {
    if (this.isFlowReadonly) {
      return;
    }

    this.clickNodeX = e.offsetX;
    this.clickNodeY = e.offsetY;
  }

  public onDragEnd(e: MouseEvent) {
    this.addAnnotateNode(e);
  }

  public addAnnotateNode(e: MouseEvent): string {
    if (this.isFlowReadonly) {
      return '';
    }

    const ptl = this.graph.pageToLocal(e.pageX, e.pageY);
    const x =
      ptl.x < this.clickNodeX && ptl.x > 0 ? 0 : ptl.x - this.clickNodeX;
    const y =
      ptl.y < this.clickNodeY && ptl.y > 0 ? 0 : ptl.y - this.clickNodeY;
    const id = `node_${Date.now()}`;
    this.createNode(
      {
        id: id,
        name: '注释',
        type: 'Comment',
        x: x - 136,
        y: y - 76,
        width: 272,
        height: 152,
        shape: 'op-comment-node',
      },
      {isUpdateFlowData: false},
    );
    return id;
  }

  public onClickAddAnnotate(e: MouseEvent) {
    if (this.isFlowReadonly) {
      return;
    }
    const nodeId = this.addAnnotateNode(e);
    if (nodeId === '') {
      return;
    }
    const halfDefaultWidth: number = 272 / 2;
    const halfDefaultHeight: number = 152 / 2;
    const node: any = this.graph.getCellById(nodeId);
    const onMouseMove = (e: MouseEvent) => {
      const ptl = this.graph.pageToLocal(e.pageX, e.pageY);
      const x =
        ptl.x < this.clickNodeX && ptl.x > 0 ? 0 : ptl.x - this.clickNodeX - halfDefaultWidth;
      const y =
        ptl.y < this.clickNodeY && ptl.y > 0 ? 0 : ptl.y - this.clickNodeY - halfDefaultHeight;
      node.setPosition({x, y}, {ignoreHistory: true},);
    };
    const onClick = () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('click', onClick);
    };
    setTimeout(() => {
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('click', onClick);
    });

  }

  /**
   * 交换节点
   * 1. 获取当前节点连线的左右节点
   * 2. 删除当前节点
   * 3. 创建新的节点
   * 4. 添加连线
   * @param param 参数
   */
  private async onExchangeNode(param) {
    const {id} = this.exchangeNodeInfo;
    const curNode = this.graph.getCellById(id);
    if (!curNode || !curNode.isNode()) {
      return;
    }
    const {leftNodes, rightNodes} = this.getConnectedNodes(curNode);
    try {
      await this.graph.batchUpdate(async () => {
        const parentNode = curNode.getParent(); // 获取父节点
        // 删除原节点并创建新节点
        const newNode = await this.creatNode(curNode, this.getExchangeNewNodeParam(param));
        this.nodeServ.setCurrSelectedNode(newNode.id);
        // 获取新节点的左右端口
        const leftPort = this.getNodePort(newNode, 'left');
        const rightPoint = this.getNodePort(newNode, 'right');
        // 与原节点的左侧节点相连
        leftNodes.forEach(({node, portId}) => {
          this.addEdge(node, newNode, portId, leftPort);
        });
        // 与原节点的右侧节点相连
        rightNodes.forEach(({node, portId}) => {
          this.addEdge(newNode, node, rightPoint, portId);
        });
        if (parentNode) {
          this.checkisIntersectWithLoopThenAddChild(parentNode.id, newNode);
        }
        this.hiddenAddNodePanel();
        this.updateRef();
        setTimeout(() => {
          FlowEventUtils.resetParentSize(parentNode);
          this.updateFlowData();
        }, 100);
      });
    } catch (err) {
      // 暂不处理
    } finally {
      this.exchangeNodeInfo = null;
    }
  }

  private getExchangeNewNodeParam(param) {
    const {inputs, outputs} = this.exchangeNodeInfo;
    const newParam = {...param};

    if (ExchangeUnSaveTypes.includes(param.type)) {
      return newParam;
    }

    if (!ExchangeNoOutputType.includes(param.type)) {
      // outputs去重，优先取 exchangeNodeInfo 中的
      const outputMap = new Map();
      newParam.outputs.forEach(output => outputMap.set(output.name, output));
      outputs.forEach(output => outputMap.set(output.name, output));
      newParam.outputs = Array.from(outputMap.values());
    }

    if (!NoInputsNodeTypes.includes(param.type)) {
      const inputMap = new Map();
      newParam.inputs.forEach(input => inputMap.set(input.name, input));
      inputs.forEach(input => inputMap.set(input.name, input));
      newParam.inputs = Array.from(inputMap.values());
    }

    return newParam;
  }

  /**
   * 获取当前节点连线的左右节点
   * @param curNode 当前节点
   * @returns
   */
  private getConnectedNodes(curNode) {
    const allEdges = this.graph.getConnectedEdges(curNode);
    const leftNodes: { node: Node, portId: string }[] = [];
    const rightNodes: { node: Node, portId: string }[] = [];

    allEdges.forEach(edge => {
      const sourceNodeId = edge.getSourceCellId();
      const targetNodeId = edge.getTargetCellId();
      const sourcePortId = edge.getSourcePortId();
      const targetPortId = edge.getTargetPortId();

      // 找出“另一端”的节点
      let otherNode: Node | null = null;

      if (sourceNodeId === curNode.id) {
        // 当前节点是 source → 另一端是 target
        otherNode = this.graph.getCellById(targetNodeId) as Node;
        rightNodes.push({node: otherNode, portId: targetPortId});
      } else if (targetNodeId === curNode.id) {
        // 当前节点是 target → 另一端是 source
        otherNode = this.graph.getCellById(sourceNodeId) as Node;
        leftNodes.push({node: otherNode, portId: sourcePortId});
      }
    });

    return {leftNodes, rightNodes};
  }

  /**
   * 添加边
   * @param sourceNode 源节点
   * @param targetNode 目标节点
   * @param sourcePort 源端口
   * @param targetPort 目标端口
   */
  private addEdge(sourceNode, targetNode, sourcePort, targetPort) {
    const edge = this.graph.addEdge({
      shape: 'dag-edge',
      source: {
        cell: sourceNode.id,
        port: sourcePort,
      },
      target: {
        cell: targetNode.id,
        port: targetPort,
      },
    });
    this.onEdgeConnected(edge);
  }

  /**
   * 创建新节点
   * @param curNode 源节点
   * @param param 参数
   * @returns
   */
  private async creatNode(curNode, param): Promise<Node> {
    const {x, y} = curNode.position();
    this.graph.removeCell(curNode);
    let nodeRaw: NodeMetadata | null = null;
    if (param.isAction) {
      nodeRaw = await this.createActionNode(param);
      this.showPluginDrawer = false;
      this.showChildFlowDrawer = false;
      this.showMcpServiceDrawer = false;
    } else {
      nodeRaw = param;
    }

    return this.createNode(
      {
        ...nodeRaw,
        id: curNode.id,
        x: x,
        y: y,
      },
      {
        ignoreLoopEmbedding: true,
        isUpdateFlowData: false,
      },
    );
  }

  /**
   * 获取节点端口
   * @param node 节点
   * @param group 位置
   * @returns
   */
  private getNodePort(node, group) {
    return node.getPorts().find((port) => port.group === group)?.id;
  }

  /**
   * 自动关闭提示信息
   */
  private autoCloseAlert() {
    setTimeout(() => {
      this.isShowSuccessAlert = false;
    }, 5000);
  }

  protected readonly DragMode = DragMode;
}
