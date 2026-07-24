import { ChangeDetectorRef, Component, EventEmitter, Input, Output, SimpleChanges, inject } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import flowCommonLogic from '../../common-logic-workflow';
import { TimeLineComponent } from '@routes/agent-center/app-insight/components/time-line/time-line.component';
import { Clipboard } from '@angular/cdk/clipboard';
import { CopyType } from '../../node.type';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { ActivatedRoute } from '@angular/router';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { v4 as uuidV4 } from 'uuid';
import { AppFlowService } from '../../app-flow.service';
import { Subject, takeUntil } from 'rxjs';
import { AssetLogIconComponent } from '@shared/components/assets/asset-log-icon/asset-log-icon.component';
import { AssetCalendarIconComponent } from '@shared/components/assets/asset-calendar-icon/asset-calendar-icon.component';
import { AssetListIconComponent } from '@shared/components/assets/asset-list-icon/asset-list-icon.component';
import { AssetSequenceIconComponent } from '@shared/components/assets/asset-sequence-icon/asset-sequence-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { AssetSuccessIconComponent } from '@shared/components/assets/asset-success-icon/asset-success-icon.component';
import { AssetErrorIconComponent } from '@shared/components/assets/asset-error-icon/asset-error-icon.component';
import { AssetGenerateLoadingIconComponent } from '@shared/components/assets/asset-generate-loading-icon/asset-generate-loading-icon.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { isNil, isEmpty, isArray, cloneDeep, isString } from 'lodash';
import { addConversationCount, ALL, format2ConvTime, format2ExecTime, getTimeByDate } from '../../utils/log-utils';
import { ParamExtractionLogComponent } from '@routes/agent-center/app-flow/components/flow-log-modal/param-extraction-log/param-extraction-log.component';
import { Graph, Node, NodeProperties } from '@antv/x6';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';
import { DateOptionRender } from '@routes/agent-center/app-agent/components/date-option-render/date-option-render.component';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzBreadCrumbModule } from 'ng-zorro-antd/breadcrumb';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';
import { NzDrawerRef, NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';

export const LIMIT_COUNT = 500; // 目前保存的历史会话不超过100

export interface IConversationRequest {
  start_time?: number;
  end_time?: number;
  limit?: number;
  offset?: number;
}

@Component({
  selector: 'flow-log-modal',
  templateUrl: './flow-log-modal.component.html',
  styleUrls: ['./flow-log-modal.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    JsonViewerComponent,
    TimeLineComponent,
    AppMarkdownAnswerComponent,
    AssetLogIconComponent,
    AssetCalendarIconComponent,
    AssetListIconComponent,
    AssetSequenceIconComponent,
    AssetCopyIconComponent,
    AssetCopySuccessIconComponent,
    AssetLoadingIconComponent,
    AssetSuccessIconComponent,
    AssetErrorIconComponent,
    AssetGenerateLoadingIconComponent,
    NoDataIconComponent,
    ParamExtractionLogComponent,
    DateOptionRender,
    NzSelectModule,
    NzBreadCrumbModule,
    NzIconModule,
    NzTabsModule,
    NzCollapseModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class FlowLogModalComponent {
  @Input() isShowLog = true;

  @Input() graph!: Graph;

  @Input() openNodeId: string;

  @Input() showLogDrawer: boolean;

  @Output('close') close = new EventEmitter<void>();

  @Output('openNode') openNode = new EventEmitter<any>();

  @Input() inputWorkflowId?: string;

  public ALL_ITEM = ALL;

  public conversationList: any = [];

  public conversationSelected: any;

  // 工作流调试信息
  public workflowDebugInfo: any = {
    status: '',
    list: [],
    result: '',
    status_desc: '',
  };

  public executionList: any = [];

  public tabs = [
    { title: this.i18n.transform('running_results'), active: false },
    { title: this.i18n.transform('call_details'), active: true },
  ];

  public executionSelected: any;

  public chartViewMode = 'list';

  public selectedIndex = 1;

  // 调用链信息
  public callChainInfo: any = {
    list: [],
  };

  public result;

  public crumb = [];

  // 时序图数据
  public timelineData: any = {};

  public curInvodeId = '';

  public nodeIdClicked = '';

  public dates: Array<{ value: string; label: string; startTime?: number; endTime?: number }>;

  public selectDate = this.ALL_ITEM;

  protected dateRange: { start_time?: number; end_time?: number } = {};

  protected workflow_id = '';

  protected destroy$ = new Subject<void>();

  indexMap = { '1': '1st', '2': '2nd', '3': '3rd' };

  isReq = false;
  hasUpdate = false;

  constructor(
    public route: ActivatedRoute,
    public clipboard: Clipboard,
    public cdr: ChangeDetectorRef,
    public i18n: I18NextEagerPipe,
    public flowRepoServe: AppFlowRepoService,
    public flowServe: AppFlowService
  ) {
    this.route.queryParams.subscribe(params => {
      this.workflow_id = params.id || this.inputWorkflowId;
    });
    this.initializeDates();
  }

  ngAfterViewInit() {
    this.workflow_id = this.workflow_id || this.inputWorkflowId;
    this.isReq = false;
    this.hasUpdate = false;
    this.getPageData();

    this.flowServe
      .tokenDataUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(tokenObj => {
        this.hasUpdate = true;
        setTimeout(() => {
          this.getPageData();
        }, 100);
      });
  }

  getPageData() {
    if (!this.showLogDrawer) {
      return;
    }
    if (!this.isReq && this.workflow_id) {
      this.isReq = true;
      this.getConversations()
        .then(() => {
          this.handleAllDate();
        })
        .finally(() => {
          this.isReq = false;
          if (this.hasUpdate) {
            this.hasUpdate = false;
            this.getPageData();
          }
        });
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public onClose() {
    this.close.emit();
  }

  public onSelectDate(event: { value: string; startTime?: number; endTime?: number }) {
    this.selectDate = event.value;

    if (this.selectDate === this.ALL_ITEM) {
      this.dateRange = {};
    } else {
      this.dateRange = {
        start_time: event.startTime,
        end_time: event.endTime,
      };
    }
    this.getConversations(this.dateRange).then(() => {
      if (this.selectDate === this.ALL_ITEM) {
        this.handleAllDate();
      }
    });
  }

  public onBeforeOpenConv(selectComp?: any) {
    this.flowRepoServe
      .getConversationList(this.workflow_id, {
        ...this.dateRange,
        limit: LIMIT_COUNT,
        offset: 0,
      })
      .then(result => {
        this.conversationList = result.conversation_infos;
        this.cdr.markForCheck();
      })
      .catch(() => {
        this.conversationList = [];
        this.cdr.markForCheck();
      });
  }

  public onBeforeOpenExec(selectComp?: any) {
    const { conversation_id } = this.conversationSelected || {};
    if (conversation_id) {
      this.flowRepoServe
        .getExecList(this.workflow_id, conversation_id)
        .then(result => {
          this.executionList = result.execution_infos;
          this.cdr.markForCheck();
        })
        .catch(() => {
          this.executionList = [];
          this.cdr.markForCheck();
        });
    } else {
      this.executionList = [];
      this.cdr.markForCheck();
    }
  }

  public changeConvSelected() {
    const { conversation_id } = this.conversationSelected;
    this.getExecutions(conversation_id);
  }

  public changeExecSelected() {
    const { conversation_id, execution_id } = this.executionSelected || {};
    this.getSingleExecDetail(this.workflow_id, conversation_id, execution_id);
  }

  public isEmptyObject(obj: any) {
    return obj && Object.keys(obj).length === 0;
  }

  /** 从运行结果Tab切回调用详情Tab */
  public onActivateDetails() {
    this.chartViewMode = 'list';
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  public handleCopy(data: any, target: CopyType) {
    let temp_copy_data = {};
    const copyInfoMap = {
      input: { content: data.inputs, icon: 'inputsCopyIcon' },
      modelInput: {
        content: this.getLlmField(data?.metadata, 'llm_inputs'),
        icon: 'modelInputCopyIcon',
      },
      output: { content: data.outputs, icon: 'outputsCopyIcon' },
      modelOutput: {
        icon: 'modelOutputCopyIcon',
        content: this.getLlmField(data?.metadata, 'llm_outputs'),
      },
      functionLog: {
        icon: 'functionLogCopyIcon',
        content: data?.metadata?.function_log || '',
      },
      variables: {
        icon: 'variablesCopyIcon',
        content: this.getNewVariables(data?.metadata),
      },
    };

    temp_copy_data = copyInfoMap.input;

    const targetInfo = copyInfoMap[target];
    if (!targetInfo) {
      return;
    }

    let temp_copy_target = targetInfo;

    const { content, icon } = targetInfo;
    if (typeof content === 'string') {
      this.clipboard.copy(content);
    } else {
      this.clipboard.copy(JSON.stringify(content) as string);
    }

    temp_copy_target = 'A_node';

    data[icon] = true;
    setTimeout(() => {
      data[icon] = false;
      this.cdr.markForCheck();
    }, 3000);
  }

  public copyQuestionNodeIO(data: any) {
    const { uuid, copyIcon, ...contentToCopy } = data;
    data.copyIcon = true;

    if (typeof contentToCopy === 'string') {
      this.clipboard.copy(contentToCopy);
    } else {
      this.clipboard.copy(JSON.stringify(contentToCopy) as string);
    }

    setTimeout(() => {
      data.copyIcon = false;
      this.cdr.markForCheck();
    }, 3100);
  }

  /** 判断调用节点的输入和输出是否为空对象 或 空数组 或 undefined/null */
  public isIOEmpty(IO: any): boolean {
    if (isNil(IO)) {
      return true;
    }

    if (isArray(IO)) {
      return IO.length === 0;
    }
    if (typeof IO === 'object') {
      return isEmpty(IO);
    }

    return false;
  }

  public removeUuid(obj: any): any {
    const { uuid, copyIcon, roundIndex, ...rest } = obj || {};
    return rest;
  }

  /** 通过uuid字段值，过滤提问器展示的某一次QA对应的输入和输出 */
  public getMessagesByUuid(msg: any[], uuid: string) {
    return msg.filter(item => item.uuid === uuid);
  }

  public getNodeStatus(node_status: string) {
    return flowCommonLogic.getNodeStatus(node_status);
  }

  public isQuestionNode(type: string) {
    return type === 'Questioner' || type === 'Agent';
  }

  public isParamExtractionNode(type: string) {
    return type === 'ParamExtraction' || type === 'ParamOutput'; //调测
  }

  public getNodeIcon(node_type: string) {
    return flowCommonLogic?.getNodeIcon(node_type);
  }

  public isLLMNode(type: string) {
    return type === 'LLM';
  }

  /** 在表格模式下，调用详情Tab相关的操作函数 */
  public changeCollapsedState(configInfo: any) {
    configInfo.collapsed = !configInfo.collapsed;
    const { node_id } = configInfo;
    this.flowServe?.setNodeIdClicked(node_id);
  }

  public changeInputCollapsedState(configInfo: any) {
    configInfo.inputsCollapsed = !configInfo.inputsCollapsed;
  }

  public changeOutputsCollapsedState(configInfo: any) {
    configInfo.outputsCollapsed = !configInfo.outputsCollapsed;
  }

  /** 在时序图模式下，调用详情Tab相关的操作函数 */
  public onNodeClicked(uuid: string) {
    this.nodeIdClicked = uuid;
    this.flowServe?.setNodeIdClicked(uuid);
    // 点击时序图上的某个节点后，展示该节点对应的输入输出，默认展开
    const nodeClicked = this.callChainInfo.list.find(item => item.node_uuid === uuid);
    if (nodeClicked) {
      nodeClicked.collapsed = false;
    }
  }

  /** 切换调用详情的视图模式，如表格还是时序图 */
  public switchViewMode(type: string) {
    this.chartViewMode = type;
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  public getWorkflowStatusDescColor(workflow_status: string) {
    return flowCommonLogic?.getWorkflowStatusDescColor(workflow_status);
  }

  /** 判断工作流调试整体信息中content字段，是否为时间戳 */
  public isTimestamp(content: any): boolean {
    return typeof content === 'number' && !isNaN(content);
  }

  public formatToConvTime(timestamp: number): string {
    return format2ConvTime(timestamp);
  }

  public formatToExecTime(timestamp: number): string {
    return format2ExecTime(timestamp);
  }

  /** 获取metadata.llm_info中的模型输入和输出字段值 */
  public getLlmField(metadata: any, field: 'llm_inputs' | 'llm_outputs') {
    return FlowUtils.getLlmField(metadata, field);
  }

  getNewVariables(metadata) {
    if (!metadata?.new_variables) {
      return '';
    }
    let json: any;
    try {
      json = JSON.parse(metadata.new_variables);
    } catch (e) {
      json = metadata.new_variables;
    }
    return json;
  }

  /** 获取conversation list */
  protected async getConversations(params: IConversationRequest = {}) {
    if (!this.showLogDrawer) {
      return;
    }
    try {
      const res = await this.flowRepoServe.getConversationList(this.workflow_id, {
        ...params,
        limit: LIMIT_COUNT,
        offset: 0,
      });
      this.conversationList = res?.conversation_infos;
      if (this.conversationList.length > 0) {
        this.conversationSelected = this.conversationList[0];
        const { conversation_id } = this.conversationList[0] || {};
        this.getExecutions(conversation_id);
      } else {
        this.timelineData = {};
        this.callChainInfo.list = [];
        this.conversationSelected = {};
        this.executionSelected = {};
        this.workflowDebugInfo = {
          status: '',
          list: [],
          result: '',
          status_desc: '',
        };
      }
      this.cdr.markForCheck();
    } catch {
      this.conversationList = [];
      this.cdr.markForCheck();
    }
  }

  /** 获取execution list */
  protected async getExecutions(conversation_id: string) {
    try {
      const res = await this.flowRepoServe.getExecList(this.workflow_id, conversation_id);
      this.executionList = res?.execution_infos;
      if (this.executionList.length > 0) {
        this.executionSelected = this.executionList[0];
        const { conversation_id, execution_id } = this.executionList[0] || {};
        this.getSingleExecDetail(this.workflow_id, conversation_id, execution_id);
      } else {
        this.executionSelected = {};
      }
      this.cdr.markForCheck();
    } catch {
      this.executionList = [];
      this.cdr.markForCheck();
    }
  }

  /** 根据executionId，查询节点的调用详情 */
  protected getSingleExecDetail(workflowId: string, conversationId: string, executionId: string) {
    this.flowRepoServe.getSingleExecInfo(workflowId, executionId).then((result: any) => {
      // 通过增加node_uuid字段，保证点击时序图上的某个节点，可以展开对应的调用链信息
      result.event_list.forEach(item => {
        item.node_uuid = uuidV4();
      });

      this.result = result;
      this.callChainInfo.list = this.convertToTableData(this.result?.event_list).filter(item => !item.parent_node_id);
      this.crumb = [
        {
          label: this.i18n.transform('parent'),
          id: '',
        },
      ];
      this.timelineData = this.convertToTimelineData(this.result.event_list);
      this.timelineData.childInvokes = this.timelineData.childInvokes.filter(item => !item.parent_node_id);

      const { status, outputs, error_info } = result;
      this.updateWorkflowDebugInfo(result);
      let temp_name = '';
      this?.updateWorkflowStatus(status);
      if (status === 'succeeded') {
        this.workflowDebugInfo.result = outputs?.responseContent;
      } else {
        this.workflowDebugInfo.result = error_info;
      }
      this.cdr.markForCheck();
    });
  }

  getChildWorkflow(workflow) {
    const list = this.result.event_list.filter(item => item.parent_node_id === workflow?.node_id);
    this.callChainInfo.list = this.convertToTableData(list);
    this.timelineData = this?.convertToTimelineData(list);
    this.crumb.push({
      id: workflow.node_id,
      label: workflow.node_name,
    });
  }

  onSelectWorkflow(curmbItem) {
    if (curmbItem.id) {
      const list = this.result.event_list.filter(item => item.parent_node_id === curmbItem?.id);
      this.callChainInfo.list = this.convertToTableData(list);
      this.timelineData = this.convertToTimelineData(list);
      const parent_node_id = this.callChainInfo?.list[0]?.parent_node_id;
      const level = this.crumb.findIndex(item => item.id === parent_node_id);
      this.crumb = this.crumb.slice(0, level + 1);
    } else {
      this.callChainInfo.list = this?.convertToTableData(this.result.event_list);
      this.callChainInfo.list = this.callChainInfo?.list.filter(item => !item.parent_node_id);
      this.timelineData = this?.convertToTimelineData(this.result.event_list);
      this.timelineData.childInvokes = this.timelineData?.childInvokes.filter(item => !item.parent_node_id);
      this.crumb = this.crumb.slice(0, 1);
    }
  }

  /** 遇到event_type等于'workflow_finished'的流式块，更新工作流信息 */
  protected updateWorkflowDebugInfo(workflow_info: any) {
    this.workflowDebugInfo.list = [];
    const { status, start_time, end_time } = workflow_info;
    if (start_time) {
      this.workflowDebugInfo?.list.push({
        title: this.i18n.transform('start_time_label'),
        content: start_time,
      });
    }

    if (end_time && !['INIT', 'RUNNING'].includes(status?.toUpperCase())) {
      this.workflowDebugInfo?.list.push(
        { title: this.i18n.transform('end_time_label'), content: end_time },
        {
          title: this.i18n.transform('running_time_label'),
          content: flowCommonLogic?.calcElapsedTime(start_time, end_time),
        }
      );
    }
  }

  /** 更新工作流运行结果的状态和描述 */
  protected updateWorkflowStatus(status: string) {
    const isQuestionWait = this.callChainInfo?.list.find(
      item => (item.node_type === 'Questioner' || item.node_type === 'Agent') && item.node_status === 'waiting'
    );

    if (isQuestionWait) {
      this.workflowDebugInfo.status = isQuestionWait?.node_status;
    } else {
      this.workflowDebugInfo.status = status;
    }

    this.workflowDebugInfo.status_desc = flowCommonLogic?.getWorkflowStatusDesc(this.workflowDebugInfo.status);
    this.cdr.markForCheck();
  }

  /** 将接口返回的调用详情数据，组装成表格数据 */
  protected convertToTableData(event_list: any[]): any[] {
    if (!event_list) {
      return [];
    }
    const eventListCopy = cloneDeep(event_list);

    const startList = eventListCopy.filter(item => item?.node_status === 'node_started');

    // 存储node_status等于node_wait并且node_type等于LLM对应的node_id list
    const llmNodeIds = eventListCopy
      .filter(item => {
        return item.node_status === 'node_wait' && item?.node_type === 'LLM';
      })
      .map(item => item.node_id);

    const tableData = startList
      .map(item => {
        const { node, additionalInfo } = this?.findMatchingEndNode(eventListCopy, item);
        if (!node) return null;

        // 优先匹配node_finished对象中的status.desc值，若没有则更新为"运行成功"
        if (llmNodeIds.includes(node.node_id)) {
          const hasFinishedNode = eventListCopy.some(el => el.node_id === node?.node_id && el?.node_status === 'node_finished');
          if (!hasFinishedNode) {
            node.status.desc = 'succeeded';
          }
        }

        let tableItem;
        if (node.node_status === 'node_wait' && additionalInfo) {
          tableItem = this?.createTableItemError(node, additionalInfo);
        } else {
          tableItem = this.createTableItem(node);
        }
        if (tableItem?.node_type === 'Questioner' || tableItem?.node_type === 'Agent') {
          if (additionalInfo) {
            this.processQuestionerNode(tableItem, node, additionalInfo);
          } else {
            this?.processQuestionerNode(tableItem, node);
          }
        }
        if (tableItem?.node_type === 'ParamExtraction' || tableItem?.node_type === 'ParamOutput') {
          this?.processParamExtractionNode(tableItem, node);
        }
        tableItem.error_message = this.handelErrorMsg(tableItem.error_message);

        if (tableItem) {
          tableItem = this.addTableItemAttr(tableItem);
        }
        return tableItem;
      })
      .filter(item => item !== null);
    return tableData;
  }

  addTableItemAttr(tableItem) {
    tableItem.isQuestionNode = this.isQuestionNode(tableItem?.node_type);
    tableItem.isLLMNode = this.isLLMNode(tableItem?.node_type);
    tableItem.nodeSrc = this.getNodeStatus(tableItem?.node_status);
    tableItem.isParamExtractionNode = this.isParamExtractionNode(tableItem?.node_type);
    tableItem.isIOEmpty = this.isIOEmpty(tableItem?.outputs);
    tableItem.messagesByUuid = this.getMessagesByUuid(tableItem.messages, tableItem.roundSelected?.uuid);
    if (tableItem.messagesByUuid.length && tableItem.messagesByUuid[0]) {
      tableItem.messagesByUuid[0].isIOEmpty = this.isIOEmpty(tableItem.messagesByUuid[0]);
      if (Object.keys(tableItem.messagesByUuid[0]).length > 0) {
        tableItem.messagesByUuid[0].removeUuid = this.removeUuid(tableItem.messagesByUuid[0]);
      }
    }
    if (tableItem.messagesByUuid.length && tableItem.messagesByUuid[1]) {
      tableItem.messagesByUuid[1].isIOEmpty = this.isIOEmpty(tableItem.messagesByUuid[1]);
      if (Object.keys(tableItem.messagesByUuid[0]).length > 0) {
        tableItem.messagesByUuid[1].removeUuid = this.removeUuid(tableItem.messagesByUuid[1]);
      }
    }
    tableItem.nodeIcon = this.getNodeIcon(tableItem?.node_type);
    return tableItem;
  }

  /** 将接口返回的调用详情数据，组装成时序图数据 */
  protected convertToTimelineData(eventList): any {
    if (this?.isEmptyObject(this.result)) {
      return {};
    }
    const eventListCopy = cloneDeep(eventList);

    const timelineData = {
      childInvokes: [],
      endTime: '',
      startTime: '',
    };

    const startList = eventListCopy.filter(item => item.node_status === 'node_started');

    timelineData.childInvokes = startList.map(item => {
      const { node, additionalInfo } = this.findMatchingEndNode(eventListCopy, item);

      const baseData = {
        invokeId: this.result.execution_id,
        invokeType: node?.node_type,
        node_name: node?.node_name,
        node_uuid: node?.node_uuid,
        parent_node_id: node?.parent_node_id,
        node_id: node?.node_id,
      };

      if (node?.node_status === 'node_wait' && additionalInfo) {
        return {
          ...baseData,
          startTime: this.formatTimestamp(additionalInfo?.start_time),
          endTime: this.formatTimestamp(additionalInfo?.end_time),
        };
      } else {
        return {
          ...baseData,
          startTime: this.formatTimestamp(node?.start_time),
          endTime: this.formatTimestamp(node?.end_time),
        };
      }
    });

    this.curInvodeId = this.result.execution_id;

    if (timelineData?.childInvokes.length > 0) {
      timelineData.startTime = timelineData.childInvokes[0].startTime;
      timelineData.endTime = timelineData.childInvokes[timelineData?.childInvokes.length - 1].endTime;
    }
    return timelineData;
  }

  /**
   * 通过node_started对应的node_id，去匹配是否存在相同node_id的node_finished对象，
   * 如果找不到的话，再去匹配是否存在相同node_id的node_wait的最后一个对象
   */
  protected findMatchingEndNode(event_list: any[], start: any): any {
    const { node_id, node_type, parent_node_id, start_time } = start || {};

    // 同样的node_id对应的node_finished可能出现多次(循环+子工作流节点)。通过found等于true，标识已经匹配到该次输出
    const finishes = event_list.filter(item => item.node_id === node_id && item.parent_node_id === parent_node_id && item.node_status === 'node_finished');
    let finish: any = {};

    for (const f of finishes) {
      if (!f.start_time) {
        f.start_time = start_time;
      }
      const fItem = this.createTableItem(f);
      if (f.inner_error) {
        fItem.node_status = 'exception';
        finish = Object.assign(finish, f);
        if (!finish.exceptionChildren) {
          finish.exceptionChildren = [];
        }
        finish.exceptionChildren.push(fItem);
        finish.collapsed = false;
        fItem.index = finish.exceptionChildren.length - 1;
      } else {
        if (!f.found) {
          if (finish.exceptionChildren) {
            finish = Object.assign(finish, f);
            finish.exceptionChildren.push(fItem);
            fItem.index = finish.exceptionChildren.length - 1;
            f.found = true;
          } else {
            finish = f;
            f.found = true;
            break;
          }
        }
      }
    }

    let additionalInfo = finish;

    if (node_type === 'Questioner' || node_type === 'Agent') {
      if (finish.node_id && (!finish.messages || finish.messages.length === 0)) {
        return {
          node: this.getMaxMessagesNode(event_list, node_id) || finish,
          additionalInfo,
        };
      }
      if (!finish?.node_id) {
        return {
          node: this.getMaxMessagesNode(event_list, node_id),
          additionalInfo: null,
        };
      }
      return {
        node: finish,
        additionalInfo: null,
      };
    } else {
      if (!finish?.node_id) {
        return {
          node: this.getMaxMessagesNode(event_list, node_id),
          additionalInfo: null,
        };
      }
      return {
        node: finish,
        additionalInfo: null,
      };
    }
  }

  protected getMaxMessagesNode(event_list: any[], node_id: string, node_type?: string): any {
    const waitList = event_list.filter(item => item?.node_id === node_id && item?.node_status === 'node_wait');

    if (node_type === 'LLM') {
      return waitList[waitList.length - 1];
    }
    return waitList.reduce((maxNode, curNode) => ((curNode?.messages?.length || 0) > (maxNode?.messages?.length || 0) ? curNode : maxNode), null);
  }

  private handelErrorMsg(errorString): string {
    try {
      const jsonStart = errorString.indexOf('{');
      const jsonEnd = errorString.lastIndexOf('}');
      const jsonString = errorString.substring(jsonStart, jsonEnd + 1).replace(/\t/g, '');
      return JSON.parse(jsonString);
    } catch {
      return errorString;
    }
  }

  handleCopyErrorCode(event, item, code) {
    event.stopPropagation();
    if (typeof code === 'string') {
      this.clipboard.copy(code);
    } else {
      this.clipboard.copy(JSON.stringify(code));
    }
    item.showCodeCopySuccess = true;
    setTimeout(() => {
      item.showCodeCopySuccess = false;
    }, 1000);
  }

  protected createTableItem(nodeData: any): any {
    const { outputs, start_time, end_time, error_message, prefill_time, startup_time } = nodeData;

    const elapsed_time = flowCommonLogic?.calcElapsedTime(start_time, end_time);

    let first_token_time;
    if (!isNil(prefill_time) && !isNil(startup_time)) {
      first_token_time = flowCommonLogic?.calcElapsedTime(startup_time, prefill_time);
    }

    let updatedOutputs;
    if (this.isEmptyObject(outputs) && !error_message) {
      updatedOutputs = {};
    } else if (error_message) {
      updatedOutputs = { ...outputs, error_message };
    } else {
      updatedOutputs = outputs;
    }
    let node_status = nodeData?.status?.desc ?? 'succeeded';
    if (outputs?.isSuccess === false) {
      node_status = 'exception';
    }
    let collapsed = true;
    //异常节点默认展开
    if (nodeData.collapsed === false) {
      collapsed = false;
    }
    if (nodeData.node_id === this.openNodeId) {
      collapsed = false;
    }

    const res = this.addTableItemAttr({
      ...nodeData,
      collapsed,
      node_status,
      elapsed_time,
      outputs: updatedOutputs,
      messages: nodeData.messages || [],
      first_token_time,
    });

    return res;
  }

  protected createTableItemError(nodeData: any, additionalInfo: any): any {
    const { start_time, end_time, prefill_time, startup_time } = additionalInfo;

    const elapsed_time = flowCommonLogic?.calcElapsedTime(start_time, end_time);

    let first_token_time;
    if (!isNil(prefill_time) && !isNil(startup_time)) {
      first_token_time = flowCommonLogic?.calcElapsedTime(startup_time, prefill_time);
    }

    const res = this.addTableItemAttr({
      ...nodeData,
      collapsed: true,
      node_status: additionalInfo.status.desc,
      messages: nodeData.messages || [],
      first_token_time,
      elapsed_time,
      start_time,
    });

    return res;
  }

  protected processQuestionerNode(callItem: any, node: any, additionalInfo?: any) {
    const { node_status } = node;
    if (node_status === 'node_finished') {
      this?.addFinalAnsToMsg(node, node);
    }
    if (node_status === 'node_wait' && additionalInfo) {
      this?.addFinalAnsToMsg(node, additionalInfo);
    }

    let curUuid = '';
    // 确保 messages 字段存在
    if (!node?.messages) {
      node.messages = [];
    }

    node.messages = node?.messages?.map((msg, index, array) => {
      if (msg.role === 'user') {
        curUuid = uuidV4();
        msg.uuid = curUuid;
        msg.copyIcon = false;
        msg.roundIndex = index;

        if (array[index + 1]) {
          array[index + 1].uuid = curUuid;
          array[index + 1].copyIcon = false;
          array[index + 1].roundIndex = index;
        }
      }
      return msg;
    });

    callItem.questionerRounds = node?.messages.filter(message => message.role === 'user');
    if (callItem?.questionerRounds.length > 0) {
      callItem.roundSelected = callItem?.questionerRounds[0];
    }
  }

  /**
   * 处理参数提取节点
   * @param callItem
   * @param node
   * @protected
   */
  protected processParamExtractionNode(callItem: any, node: any) {
    const cell: Node = this.graph?.getCellById(node.node_id) as Node<NodeProperties>;
    if (cell) {
      const nodeInfo = FlowUtils.getNodeDSLFromRaw(cell);
      callItem.nodeInfo = nodeInfo;
    }
  }

  showChildEvent(events, callItem) {
    this.callChainInfo.list = this.convertToTableData(events);
    this.timelineData = this.convertToTimelineData(events);
    this.crumb.push({
      label: callItem.nodeInfo?.name ?? callItem.node_name,
      id: callItem.nodeInfo?.id ?? callItem.node_id,
    });
  }

  protected addFinalAnsToMsg(node: any, source: any): void {
    const finalAnswer = source?.error_message ? { error_message: source?.error_message } : source.outputs;

    // 确保 messages 字段存在
    if (!node.messages) {
      node.messages = [];
    }
    node?.messages.push(finalAnswer);
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

  /** 调用链表格中所有节点恢复成收起状态 */
  protected resetCollapsedState() {
    this.callChainInfo?.list.forEach(item => {
      item.collapsed = true;
    });
  }

  protected initializeDates(): void {
    const dates = new Array(7).fill(0).map((item, i) => {
      let date = new Date();
      date.setDate(date?.getDate() - i);
      const formattedDate = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
      return {
        value: formattedDate,
        label: formattedDate,
        ...getTimeByDate(formattedDate),
      };
    });

    this.dates = [{ value: this.ALL_ITEM, label: this.i18n.transform('all') }, ...dates];
  }

  protected handleAllDate(): void {
    addConversationCount(this.conversationList, this.dates);
  }

  openErrorNode(item) {
    this.openNode.emit(item.node_id);
  }
}
