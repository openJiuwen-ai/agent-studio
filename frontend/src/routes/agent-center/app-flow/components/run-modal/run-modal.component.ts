import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { MODULES } from '@shared/modules';
import { TextFieldModule } from '@angular/cdk/text-field';
import { type Graph } from '@antv/x6';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { Clipboard } from '@angular/cdk/clipboard';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { ActivatedRoute } from '@angular/router';
import { AppConversationRepoService } from '@services/repositories/app-conversation-repo.service';
import { AppFlowService } from '../../app-flow.service';
import type { IPluginConfig, IWorkflow } from '../../app-flow.types';
import { CopyType } from '../../node.type';
import { takeUntil } from 'rxjs';
import { NgForm } from '@angular/forms';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { TimeLineComponent } from '@routes/agent-center/app-insight/components/time-line/time-line.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetListIconComponent } from '@shared/components/assets/asset-list-icon/asset-list-icon.component';
import { AssetSequenceIconComponent } from '@shared/components/assets/asset-sequence-icon/asset-sequence-icon.component';
import { AssetGenerateLoadingIconComponent } from '@shared/components/assets/asset-generate-loading-icon/asset-generate-loading-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { v4 as uuidV4 } from 'uuid';
import type { IStartNode } from '../../node.type';
import flowCommonLogic from '../../common-logic-workflow';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { isNil, isNaN } from 'lodash';
import { WorkflowChatBaseComponent } from '@shared/base/workflow-chat-base.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import CommonLogic from '../../../../app-center/common-logic-app-center';
import { TASK_FILTER_KEYS } from '@routes/agent-center/types/common.types';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzBreadCrumbModule } from 'ng-zorro-antd/breadcrumb';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { ScrollingModule } from '@angular/cdk/scrolling';

@Component({
  selector: 'flow-run-modal',
  templateUrl: './run-modal.component.html',
  styleUrls: ['./run-modal.component.less'],
  standalone: true,
  imports: [
    MODULES,
    TextFieldModule,
    JsonViewerComponent,
    DynamicNodeParamsComponent,
    AppMarkdownAnswerComponent,
    TimeLineComponent,
    AssetListIconComponent,
    AssetSequenceIconComponent,
    AssetCopyIconComponent,
    AssetCopySuccessIconComponent,
    AssetGenerateLoadingIconComponent,
    AssetLoadingIconComponent,
    NoDataIconComponent,
    NzIconModule,
    NzTabsModule,
    NzButtonModule,
    NzSpinModule,
    NzCollapseModule,
    NzFormModule,
    NzInputModule,
    NzBreadCrumbModule,
    NzToolTipModule,
    ScrollingModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class RunModalComponent extends WorkflowChatBaseComponent {
  @Input() override currWorkflow!: IWorkflow;

  @Input() showRunModal = false;
  // @Input() workflow_type;

  @Input() override graph!: Graph;

  @Input() conversationId = '';

  @Output('close') close = new EventEmitter<void>();

  @ViewChild('dynamicNodeParams')
  override dynamicNodeParams!: DynamicNodeParamsComponent;

  @ViewChild('chatContainerRef')
  override chatContainerRef!: ElementRef;

  @ViewChild('pluginForm') override pluginForm: NgForm;

  @ViewChild('pluginAreaRef') pluginAreaRef!: ElementRef;

  @Input() environment_id: string;

  /** 工作流调试信息 */
  public workflowDebugInfo: any = {
    status: '',
    status_desc: '',
    list: [],
  };

  /** 调用链信息 */
  public callChainInfo: any = {
    title: '',
    list: [],
  };

  public tabs: any = [
    { title: this.i18n.transform('config_info'), active: true },
    { title: this.i18n.transform('running_results'), active: false },
    { title: this.i18n.transform('call_details'), active: false },
  ];

  public selectedTabIndex = 0;

  /** 消息框中，运行结果Tab是否存在试运行信息 */
  public isEmptyRunResult = true;

  public chartViewMode = 'list';

  public nodeIdClicked = '';

  // 时序图数据
  public timelineData = {};

  public curNodeId = '';

  public crumb = [];

  private childInvokes: any[] = [];

  private workflow_info = {
    start_time: null,
    end_time: null,
    tokens: null,
    status: null,
  };

  private version: number = 0;

  @ViewChild('mainLogDomRef') mainLogDomRef: ElementRef;

  get getDomHeight() {
    let res = 0;
    if (this.mainLogDomRef?.nativeElement) {
      res = this.mainLogDomRef.nativeElement.getBoundingClientRect().height - 120;
    }
    return `${res}px`;
  }

  constructor(
    protected override appFlowServe: AppFlowService,
    protected override appAgentServe: AppAgentRepoService,
    protected override configServ: AgentConfigService,
    protected override commonLogic: agentCommonLogic,
    protected override monacoLoader: MonacoEditorLoaderService,
    protected override i18n: I18NextEagerPipe,
    protected override cdr: ChangeDetectorRef,
    protected override agentDataServe: AgentDataService,
    protected override pluginRepoServe: AppPluginRepoService,
    private conversationServe: AppConversationRepoService,
    private route: ActivatedRoute,
    private clipboard: Clipboard,
  ) {
    super(
      appFlowServe,
      appAgentServe,
      configServ,
      commonLogic,
      monacoLoader,
      i18n,
      cdr,
      agentDataServe,
      pluginRepoServe,
    );

    this.route?.queryParams.subscribe((params) => {
      const { id, type, versionId } = params;
      this.workflow_id = id;
      this.type = type;
      this.versionId = versionId;
    });

    /** 订阅试运行按钮是否被点击 */
    this.appFlowServe
      .runBtnClickedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (isClicked: boolean) => {
        this.isRetryRunning = isClicked;
        if (isClicked) {
          this.selectedTabIndex = 0;
          this.tabs[0].active = true;
          this.isEmptyRunResult = true;
          // 存储已填的插件入参，并组装插件节点的输入参数
          this.appFlowServe?.setRunSettings(this.settingsList);
          await this.buildSettingsData();
        }
      });

    /** 订阅试运行流式接口的version值 */
    this.appFlowServe
      .versionInfoUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version: number) => {
        this.version = version;
      });

    /** 订阅工作流的整体运行状态，成功或失败 */
    this.appFlowServe
      .flowStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        this.updateWorkflowStatus(status);
      });

    // 只有当删除或新增插件节点时，才会更新插件鉴权参数
    this.appFlowServe
      .refreshFlagUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isRefresh: boolean) => {
        if (isRefresh) {
          this.appFlowServe?.setRunSettings(this.settingsList);
          this.buildSettingsData();
        }
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    // 每次点击试运行按钮，清空上一次的【运行结果】Tab页数据
    if (changes.showRunModal && changes.showRunModal.currentValue) {
      this.clearOutputs();
    }

    const graphValue = changes.graph ? changes.graph.currentValue : this.graph;
    const workflowDetailValue = changes.currWorkflow
      ? changes.currWorkflow.currentValue
      : this.currWorkflow;
    this.updateInputParams(graphValue, workflowDetailValue);
    this.registerJSONValidationSchema();
  }

  override onParamsValid() {
    this.selectedTabIndex = 1;
    this.tabs[1].active = true;
    // 把上一次流式打印的【工作流】运行状态和时间、【调用链】和【大模型输出】信息，恢复默认值
    this.clearOutputs(true);
    let startInputsList = this.getRunWorkflowParams() || {};
    // 试运行里，针对非必填参数，若不填，则body体不带。避免出现{ 可选变量名:null }或{ 可选变量名:'' }
    startInputsList = Object.entries(startInputsList).reduce(
      (acc, [key, value]) => {
        if (!(isNil(value) || value === '' || isNaN(value))) {
          acc[key] = value;
        }
        return acc;
      },
      {},
    );
    const pluginConfigs = this.buildPluginConfigs();
    this.debugWorkflow(
      startInputsList,
      pluginConfigs,
      this.chatLoop.length - 1,
    );
  }

  override onMessage(curIndex: number, token: any) {
    super.onMessage(curIndex, token);

    const chunkObj = token.data && flowCommonLogic.stringToObject(token.data);
    const { event, data } = chunkObj ?? {};
    const { start_time, end_time } = data ?? {};

    if (event === 'node_started') {
      this.addCallNode(data);
    }

    if (event === 'node_finished' || event === 'node_wait') {
      this.updateCallNode(data);
      this.convertToTimelineData(data);
    }

    if (event === 'workflow_started') {
      this.workflow_info.start_time = start_time;
      this.workflow_info.end_time = null;
      this.updateWorkflowDebugInfo(this.workflow_info);
    }

    if (event === 'error') {
      this.isStreamFail = true;
      this.appFlowServe.setFlowStatus('failed');
    }

    if (event === 'workflow_finished') {
      if (!this.isStreamFail) {
        this.appFlowServe.setFlowStatus('succeed');
      }
      this.workflow_info.start_time = start_time;
      this.workflow_info.end_time = end_time;
      this.updateWorkflowDebugInfo(this.workflow_info);
    }
  }

  override onDone(curIndex: number, token: any) {
    super.onDone(curIndex, token);

    this.updateLLMsStatus();
    if (this.chatLoop[this.index]?.answer === '') {
      this.chatLoop[this.index].answer = ' ';
    }
  }

  override onError(curIndex: number, error: any) {
    super.onError(curIndex, error);

    this.isStreamFail = true;
    this.appFlowServe.setFlowStatus('failed');
  }

  override onTimeout(curIndex: number) {
    super.onTimeout(curIndex);

    this.isStreamFail = true;
    this.appFlowServe.setFlowStatus('failed');
  }

  get isShowEmptyTmpl(): boolean {
    return (
      this.isEmptyRunResult ||
      (this.isStreamFail &&
        (this.isEmptyObject(this.timelineData) ||
          this.callChainInfo.list.length === 0))
    );
  }

  public onClose() {
    this.appFlowServe.setRunSettings(this.settingsList);
    this.close.emit();
  }

  public get runWorkflowButtonText(): string {
    return this.commonLogic.runFlowButtonText(
      this.isRetryRunning,
      this.isStreamFail,
      this.isRequesting,
    );
  }

  public getNodeIcon(node_type: string) {
    return flowCommonLogic.getNodeIcon(node_type);
  }

  public getNodeStatus(node_status: string) {
    return flowCommonLogic.getNodeStatus(node_status);
  }

  public getWorkflowStatusDescColor(workflow_status: string) {
    return flowCommonLogic.getWorkflowStatusDescColor(workflow_status);
  }

  public changeCollapsedState(configInfo: any) {
    configInfo.collapsed = !configInfo.collapsed;
    const { node_id } = configInfo;
    this.appFlowServe.setNodeIdClicked(node_id);
  }

  /** 判断工作流调试整体信息中content字段，是否为时间戳 */
  public isTimestamp(content: any): boolean {
    return typeof content === 'number' && !isNaN(content);
  }

  /** 判断调用节点的输入和输出是否为空对象 或 空数组 或 undefined/null */
  public isIOEmpty(IO: any): boolean {
    if (isNil(IO)) {
      return true;
    }

    if (Array.isArray(IO)) {
      return IO.length === 0;
    }
    if (typeof IO === 'object') {
      return Object.keys(IO).length === 0;
    }

    return false;
  }

  public handleCopy(data: any, target: CopyType) {
    const contentToCopy = target === 'input' ? data.inputs : data.outputs;

    if (typeof contentToCopy === 'string') {
      this.clipboard.copy(contentToCopy);
    } else {
      this.clipboard.copy(JSON.stringify(contentToCopy) as string);
    }

    if (target === 'input') {
      data.inputsCopyIcon = true;
    } else {
      data.outputsCopyIcon = true;
    }

    setTimeout(() => {
      if (target === 'input') {
        data.inputsCopyIcon = false;
      } else {
        data.outputsCopyIcon = false;
      }
      this.cdr.markForCheck();
    }, 3000);
  }

  public changePluginFormCollapse(pluginForm: any) {
    const collapsed = pluginForm.collapsed;
    pluginForm.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  public onActivateDetails() {
    this.chartViewMode = 'list';
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  /** 切换调用详情的视图模式，如表格还是时序图 */
  public switchViewMode(type: string) {
    this.chartViewMode = type;
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  public isEmptyObject(obj: any) {
    return obj && Object.keys(obj).length === 0;
  }

  /** 在时序图模式下，调用详情Tab相关的操作函数 */
  public onNodeClicked(node_id: string) {
    this.nodeIdClicked = node_id;
    this.appFlowServe.setNodeIdClicked(node_id);
    // 点击时序图上的某个节点后，展示该节点对应的输入输出，默认展开
    const nodeClicked = this.callChainInfo.list.find(
      (item) => item.node_id === node_id,
    );
    if (nodeClicked) {
      nodeClicked.collapsed = false;
    }
  }

  /** 开始节点的输入参数列表通过校验后，点击【开始运行】，获取表单key-value，作为run接口的入参 */
  private getRunWorkflowParams() {
    return this.dynamicNodeParams.getDynamicParams();
  }

  private debugWorkflow(
    inputs: any,
    pluginConfigs: IPluginConfig[],
    curIndex: number,
  ) {
    this.isRequesting = true;
    this.isEmptyRunResult = false;
    this.index = 0;
    this.appFlowServe.setTokenData({});
    this.isStreamFail = false;
    this.nodeIdBlock = {};
    this.previousNodeId = '';
    this.hasSetPreviousNodeId = false;
    const params: any = {
      inputs,
      globals: {},
      plugin_configs: pluginConfigs,
      version: this.version,
    }
    if (this.environment_id) {
      params.environment_id = this.environment_id;
    }
    this.sseInstance = this.conversationServe.debugWorkflowSSE(
      params,
      this.workflow_id,
      this.conversationId,
      'DEBUG',
      this.lang,
      this.handleSSEEvents(curIndex),
      this.versionId,
    );
  }

  /** 遇到event_type等于'workflow_finished'的流式块，更新工作流信息 */
  private updateWorkflowDebugInfo(workflow_info: any) {
    this.workflowDebugInfo.list = [];
    const { start_time, end_time } = workflow_info;
    this.workflowDebugInfo.list.push({
      title: this.i18n.transform('start_time_label'),
      content: start_time,
    });

    if (end_time) {
      this.workflowDebugInfo.list.push(
        { title: this.i18n.transform('end_time_label'), content: end_time },
        {
          title: this.i18n.transform('running_time_label'),
          content: flowCommonLogic.calcElapsedTime(start_time, end_time),
        },
      );
    }
  }

  public stopChat() {
    this.sseInstance.close();
    this.isRequesting = false;
    this.appFlowServe.setFlowStatus('failed');
    this.cdr.markForCheck();
  }

  /** 更新工作流状态和描述 */
  private updateWorkflowStatus(status: string) {
    this.workflowDebugInfo.status = status;
    this.workflowDebugInfo.status_desc =
      flowCommonLogic.getWorkflowStatusDesc(status);
    this.cdr.markForCheck();
  }

  /** 清空上一次流式接口的返回数据 */
  private clearOutputs(isRegenerate = false) {
    this.updateWorkflowStatus(isRegenerate ? 'loading' : '');
    this.workflowDebugInfo.list = [];
    this.callChainInfo = { title: '', list: [] };
    this.timelineData = {};
    this.childInvokes = [];
    this.index = 0;
    this.chatLoop = [
      CommonLogic.createFlowChatItem({
        query: '',
        dialogId: uuidV4(),
      }),
    ];
    this.appFlowServe.setTokenData({});
  }

  /** 更新开始节点的入参列表 */
  private updateInputParams(graphValue: any, workflowDetailValue: any) {
    const { nodes } = this.appFlowServe.getUpdateGraphData(graphValue, workflowDetailValue).workflow_details;
    // 存储已填的开始节点入参，确保在自动更新时不会丢失数据，导致重复填写
    const startNode = nodes.find(node => node.type === 'Start') as IStartNode;
    if (!startNode) {
      return;
    }

    this.startNodeParams = this.getDebugConfigParams(startNode.outputs, TASK_FILTER_KEYS);
    this.startNodeParams = this.addControlValueField(this.startNodeParams);
  }

  /** 遇到event_type等于'node_started'的流式块，添加调用节点 */
  private addCallNode(node_info: any) {
    const { node_id, node_name, node_type, start_time, parent_node_id = '', loop_index } = node_info;
    this.callChainInfo.title = this.i18n.transform('call_chain');
    this.callChainInfo.list.push(
      this.addCallItemAttr({
        node_id,
        node_name,
        collapsed: true,
        node_type,
        node_status: 'loading',
        elapsed_time: '',
        start_time,
        parent_node_id,
        loop_index,
      })
    );
  }

  addCallItemAttr(callItem) {
    callItem.isIOEmptyInputs = this.isIOEmpty(callItem.inputs);
    callItem.isIOEmptyOutputs = this.isIOEmpty(callItem.outputs);
    return callItem;
  }

  trackById(index: number, user: any): number {
    return index;
  }

  /** 遇到event_type等于'node_finished'的流式块，更新调用节点信息 */
  private updateCallNode(node_info: any) {
    const {
      node_id,
      status,
      end_time,
      inputs,
      outputs,
      parent_node_id = '',
      loop_index,
      start_time,
    } = node_info;
    const node = this.callChainInfo.list.find(
      (item: any) =>
        item.node_id === node_id &&
        item.parent_node_id === parent_node_id &&
        item.loop_index === loop_index &&
        item.start_time === start_time,
    );

    if (node) {
      node.node_status = status.desc;
      node.elapsed_time = flowCommonLogic.calcElapsedTime(
        node.start_time,
        end_time,
      );
      node.inputs = inputs;
      node.outputs = outputs;
      node.isIOEmptyInputs = this.isIOEmpty(inputs);
      node.isIOEmptyOutputs = this.isIOEmpty(outputs);
    }
  }

  /** 遇到event_type等于'node_finished'的流式块，组装成时序图数据 */
  private convertToTimelineData(node_info: any): any {
    const { node_id, node_name, node_type, start_time, end_time } = node_info;
    const existingChildInvoke = this.childInvokes.find(
      (child: any) => child.node_id === node_id,
    );

    if (existingChildInvoke) {
      if(end_time){
        existingChildInvoke.endTime = new Date(end_time).toISOString();
      }
    } else {
      const startTime = this.formatTimestamp(start_time);
      const endTime = this.formatTimestamp(end_time);

      this.childInvokes.push({
        startTime,
        endTime,
        invokeType: node_type,
        node_name: node_name,
        node_id: node_id,
      });
    }

    if (!this.childInvokes.length) {
      return;
    }

    const startTime = this.childInvokes[0].startTime;
    const endTime = this.childInvokes[this.childInvokes.length - 1].endTime;
    this.timelineData = {
      childInvokes: this.childInvokes,
      startTime,
      endTime,
    };
  }

  /** 调用链表格中所有节点恢复成收起状态 */
  private resetCollapsedState() {
    this.callChainInfo.list.forEach((item) => {
      item.collapsed = true;
    });
  }

  /** 遇到结束标记时，更新未被引用的大模型节点状态，刷新为"运行成功" */
  private updateLLMsStatus() {
    this.callChainInfo.list.forEach((item: any) => {
      if (item.node_type === 'LLM' && item.node_status === 'waiting') {
        item.node_status = 'succeeded';
      }
    });
  }

  public getChildWorkflow(node) {
    const { node_id, parent_node_id, node_name } = node;
    this.curNodeId = node_id;
    if (!this.crumb.length) {
      this.crumb = [
        {
          label: this.i18n.transform('parent'),
          id: parent_node_id,
        },
        {
          label: node_name,
          id: node_id,
        },
      ];
    } else {
      this.crumb.push({
        label: node_name,
        id: node_id,
      });
    }
  }

  onSelectWorkflow(crumbItem) {
    const { id } = crumbItem;
    this.curNodeId = id;
    if (!id) {
      this.crumb = [];
    } else {
      const selectedIndex = this.crumb.findIndex((item) => item.id === id);
      this.crumb.splice(selectedIndex + 1);
    }
  }

  /** 将时间戳转换为yyyy-MM-dd HH:mm:ss.SSSSSS  */
  protected formatTimestamp(timestamp: number): string {
    if (!timestamp) {
      return '';
    }

    const date = new Date(timestamp);
    const datePart = date?.toISOString().slice(0, 10);
    const timePart = date?.toISOString().slice(11, 26);
    return `${datePart} ${timePart}`;
  }
}
