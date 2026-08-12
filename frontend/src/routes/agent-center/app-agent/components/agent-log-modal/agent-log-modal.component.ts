import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
  SimpleChanges,
} from '@angular/core';

import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import flowCommonLogic from '../../../app-flow/common-logic-workflow';
import { Clipboard } from '@angular/cdk/clipboard';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { TimeLineComponent } from '@routes/agent-center/app-insight/components/time-line/time-line.component';
import { AssetCalendarIconComponent } from '@shared/components/assets/asset-calendar-icon/asset-calendar-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { AssetSuccessIconComponent } from '@shared/components/assets/asset-success-icon/asset-success-icon.component';
import { AssetErrorIconComponent } from '@shared/components/assets/asset-error-icon/asset-error-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetListIconComponent } from '@shared/components/assets/asset-list-icon/asset-list-icon.component';
import { AssetSequenceIconComponent } from '@shared/components/assets/asset-sequence-icon/asset-sequence-icon.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ActivatedRoute } from '@angular/router';
import { isNil } from 'lodash';
import {
  ALL,
  format2ConvTime,
  format2ExecTime,
  getDateByTemp,
  getTimeByDate,
} from '@routes/agent-center/app-flow/utils/log-utils';
import { IConversationRequest, LIMIT_COUNT } from '@routes/agent-center/app-flow/components/flow-log-modal/flow-log-modal.component';
import { CONVERSATION_TYPE } from '@services/agent-center/app-controller.service';

@Component({
  selector: 'agent-log-modal',
  templateUrl: './agent-log-modal.component.html',
  styleUrls: ['./agent-log-modal.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    JsonViewerComponent,
    TimeLineComponent,
    AssetCalendarIconComponent,
    AssetLoadingIconComponent,
    AssetSuccessIconComponent,
    AssetErrorIconComponent,
    AssetCopyIconComponent,
    AssetCopySuccessIconComponent,
    AssetListIconComponent,
    AssetSequenceIconComponent,
    NoDataIconComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class AgentLogModalComponent {
  @Input() showLogModal = false;

  @Input() conversationId = '';

  @Output('close') close = new EventEmitter<void>();

  public ALL_ITEM = ALL;

  public dates: Array<{ value: string; label: string; startTime?: number; endTime?: number; totalCount?: number; successCount?: number; failCount?: number; disabled?: boolean }> = [];

  private dateRange: { start_time?: number; end_time?: number } = {};

  public selectDateObj: { value: string; label: string; startTime?: number; endTime?: number; totalCount?: number; successCount?: number; failCount?: number; disabled?: boolean } = null;

  public activeTabIndex = 0;

  public tabs = [
    { title: this.i18n.transform('running_results'), active: true },
    { title: this.i18n.transform('call_details'), active: false },
  ];

  public conversationList: any = [];

  public conversationSelected = '';

  public executionList: any = [];

  public executionSelected = '';

  // Agent整体调试信息
  public agentDebugInfo: any = {
    status: '',
    status_desc: '',
    list: [],
    inputs: undefined,
    outputs: undefined,
  };

  public chartViewMode = 'list';

  // 调用链信息
  public callChainInfo = [];

  // 时序图数据
  public timelineData = {};

  public curInvodeId = '';

  public nodeIdClicked = '';

  private agent_id = '';

  constructor(
    private agentRepoServe: AppAgentRepoService,
    private route: ActivatedRoute,
    private clipboard: Clipboard,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
  ) {
    this.route.queryParams.subscribe((params) => {
      this.agent_id = params.agentId;
    });

    this.initializeDates();
  }

  ngAfterViewInit() {
    this.getConversations().then(() => {
      this.handleAllDate(this.conversationList);
      this.selectDateObj = this.dates?.[0] || null;
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.showLogModal && changes.showLogModal.currentValue) {
      this.conversationSelected = '';
      this.getConversations().then(() => {
        this.handleAllDate(this.conversationList);
        this.selectDateObj = this.dates?.[0] || null;
      });
    }
  }

  public onSelectDate(event: { value: string; startTime?: number; endTime?: number }) {
    if (event.value === this.ALL_ITEM) {
      this.dateRange = {};
    } else {
      this.dateRange = {
        start_time: event.startTime,
        end_time: event.endTime,
      };
    }

    this.getConversations(this.dateRange).then(() => {
      this.agentRepoServe.getConversationList(this.agent_id, {
        limit: LIMIT_COUNT,
        offset: 0,
        type: CONVERSATION_TYPE.AGENT,
      }).then((res) => {
        this.handleAllDate(res.conversation_infos || []);
      });
    });
  }

  public changeConvSelected() {
    const conversation = this.conversationList.find(c => c.conversation_id === this.conversationSelected);
    if (conversation) {
      this.getExecutions(conversation.conversation_id);
    }
  }

  public onClose() {
    this.close.emit();
  }

  public changeExecSelected() {
    const execution = this.executionList.find(e => e.execution_id === this.executionSelected);
    if (execution) {
      this.getSingleExecDetail(this.agent_id, execution.execution_id);
    }
  }

  public onConvOpenChange(open: boolean) {
    if (!open) return;
    this.agentRepoServe
      .getConversationList(this.agent_id, {
        ...this.dateRange,
        limit: LIMIT_COUNT,
        offset: 0,
        type: CONVERSATION_TYPE.AGENT,
      })
      .then((result) => {
        this.conversationList = result.conversation_infos || [];
      })
      .catch(() => {
        this.conversationList = [];
      })
      .finally(() => {
        this.cdr.markForCheck();
      });
  }

  public onExecOpenChange(open: boolean) {
    if (!open) return;
    const conversation = this.conversationList.find(c => c.conversation_id === this.conversationSelected);
    if (conversation) {
      this.agentRepoServe
        .getExecList(this.agent_id, conversation.conversation_id)
        .then((result) => {
          this.executionList = result.execution_queries || [];
        })
        .catch(() => {
          this.executionList = [];
        })
        .finally(() => {
          this.cdr.markForCheck();
        });
    } else {
      this.executionList = [];
    }
  }

  public getConvSelectedTime(conversationId: string): number {
    const conv = this.conversationList.find(c => c.conversation_id === conversationId);
    return conv?.start_time;
  }

  public formatToConvTime(timestamp: number): string {
    return format2ConvTime(timestamp);
  }

  public formatToExecTime(timestamp: number): string {
    return format2ExecTime(timestamp);
  }

  /** 从运行结果Tab切回调用详情Tab */
  public onActivateDetails() {
    this.chartViewMode = 'list';
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  public onTabIndexChange(index: number) {
    this.activeTabIndex = index;
  }

  /** 切换调用详情的视图模式，如表格还是时序图 */
  public switchViewMode(type: string) {
    this.chartViewMode = type;
    this.resetCollapsedState();
    this.nodeIdClicked = '';
  }

  /** 在时序图模式下，调用详情Tab相关的操作函数 */
  public onNodeClicked(node_id: string) {
    this.nodeIdClicked = node_id;
    // 点击时序图上的某个节点后，展示该节点对应的输入输出，默认展开
    const nodeClicked = this.callChainInfo.find(
      (item) => item.node_id === node_id,
    );
    if (nodeClicked) {
      nodeClicked.collapsed = false;
    }
  }

  public getNodeIcon(node_type: string) {
    return flowCommonLogic.getNodeIcon(node_type);
  }

  public getNodeStatus(node_status: string) {
    return flowCommonLogic.getNodeStatus(node_status);
  }

  public getAgentStatusDescColor(workflow_status: string) {
    return flowCommonLogic.getWorkflowStatusDescColor(workflow_status);
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

  public isEmptyObject(obj: any) {
    return obj && Object.keys(obj).length === 0;
  }

  public changeCollapsedState(configInfo: any) {
    configInfo.collapsed = !configInfo.collapsed;
  }

  public handleCopy(data: any, target: any) {
    const contentNeedToCopy = target === 'input' ? data.inputs : data.outputs;

    if (typeof contentNeedToCopy === 'string') {
      this.clipboard.copy(contentNeedToCopy);
    } else {
      this.clipboard.copy(JSON.stringify(contentNeedToCopy) as string);
    }

    if (target === 'input') {
      data.inputsCopyIcon = true;
    } else {
      data.outputsCopyIcon = true;
    }

    this.asyncSetData(data, target);
  }

  public handleCopyMetadata(data: any, target: any) {
    const contentNeedToCopy = data.meta_data;
    if (typeof contentNeedToCopy === 'string') {
      this.clipboard.copy(contentNeedToCopy);
    } else {
      this.clipboard.copy(JSON.stringify(contentNeedToCopy) as string);
    }
    data.metadataCopyIcon = true;
    setTimeout(() => {
      data.metadataCopyIcon = false;
      this.cdr.markForCheck();
    }, 3000);
  }

  private asyncSetData(data: any, target: string) {
    setTimeout(() => {
      if (target === 'input') {
        data.inputsCopyIcon = false;
      } else {
        data.outputsCopyIcon = false;
      }
      this.cdr.markForCheck();
    }, 3000);
  }

  /** 获取conversation list */
  private async getConversations(params: IConversationRequest = {}) {
    try {
      const res = await this.agentRepoServe.getConversationList(
        this.agent_id,
        {
          ...params,
          limit: LIMIT_COUNT,
          offset: 0,
          type: CONVERSATION_TYPE.AGENT,
        },
      );
      this.conversationList = res.conversation_infos;
      if (this.conversationList.length > 0) {
        const prevId = this.conversationSelected;
        const matched = prevId
          ? this.conversationList.find((c: any) => c.conversation_id === prevId)
          : null;
        if (matched) {
          this.conversationSelected = matched.conversation_id;
        } else if (this.conversationId) {
          const found = this.conversationList.find((c: any) => c.conversation_id === this.conversationId);
          this.conversationSelected = found ? found.conversation_id : this.conversationList[0].conversation_id;
        } else {
          this.conversationSelected = this.conversationList[0].conversation_id;
        }
        this.getExecutions(this.conversationSelected);
      } else {
        this.conversationSelected = '';
        this.executionSelected = '';
        this.timelineData = {};
        this.callChainInfo = [];
        this.agentDebugInfo = {
          status: '',
          status_desc: '',
          list: [],
          inputs: '',
          outputs: '',
        };
      }
      this.cdr.markForCheck();
    } catch {
      this.conversationList = [];
      this.cdr.markForCheck();
    }
  }

  /** 获取execution list */
  private async getExecutions(conversation_id: string) {
    try {
      const res = await this.agentRepoServe.getExecList(
        this.agent_id,
        conversation_id,
      );
      this.executionList = res.execution_queries;
      if (this.executionList.length > 0) {
        this.executionSelected = this.executionList[0].execution_id;
        const { execution_id } = this.executionList[0] || {};
        this.getSingleExecDetail(this.agent_id, execution_id);
      }
      this.cdr.markForCheck();
    } catch {
      this.executionList = [];
      this.cdr.markForCheck();
    }
  }

  /** 根据executionId，查询节点的调用详情 */
  private getSingleExecDetail(agent_id: string, execution_id: string) {
    this.agentRepoServe
      .getSingleExecInfo(agent_id, execution_id)
      .then((result: any) => {
        this.callChainInfo = this.convertToTableData(result.invoke_list);
        this.timelineData = this.convertToTimelineData(result);
        const { status } = result;
        this.updateAgentDebugInfo(result);
        this.updateAgentStatus(status);
        this.cdr.markForCheck();
      });
  }

  /** 将接口返回的调用详情数据，组装成表格数据 */
  private convertToTableData(invoke_list: any[]): any[] {
    if (!invoke_list) {
      return [];
    }

    const tableData = invoke_list.map((item) => {
      return this.createTableItem(item);
    });
    return tableData;
  }

  /** 将接口返回的调用详情数据，组装成时序图数据 */
  private convertToTimelineData(result: any): any {
    if (this.isEmptyObject(result)) {
      return {};
    }

    const timelineData = {
      childInvokes: [],
      startTime: '',
      endTime: '',
    };

    timelineData.childInvokes = result.invoke_list.map((item) => {
      let invokeType = item.node_type;
      if (invokeType === 'llm') {
        invokeType = 'LLM';
      } else if (invokeType === 'plugin') {
        invokeType = 'Plugin';
      } else if (invokeType === 'knowledge') {
        invokeType = 'Knowledge';
      }

      const baseData = {
        invokeId: result.execution_id,
        invokeType,
        node_name: item.node_name,
        node_id: item.node_id,
      };

      return {
        ...baseData,
        startTime: this.formatTimestamp(item.start_time),
        endTime: this.formatTimestamp(item.end_time),
      };
    });

    this.curInvodeId = result.execution_id;

    if (timelineData.childInvokes.length > 0) {
      timelineData.startTime = timelineData.childInvokes[0].startTime;
      timelineData.endTime =
        timelineData.childInvokes[timelineData.childInvokes.length - 1].endTime;
    }
    return timelineData;
  }

  private createTableItem(nodeData: any): any {
    const {
      node_id,
      node_name,
      node_type,
      node_status,
      inputs,
      outputs,
      meta_data,
      start_time,
      end_time,
      error_message,
    } = nodeData;
    const elapsed_time = flowCommonLogic.calcElapsedTime(start_time, end_time);
    let updatedOutputs;
    if (this.isEmptyObject(outputs) && !error_message) {
      updatedOutputs = {};
    } else if (error_message) {
      updatedOutputs = { ...outputs, error_message };
    } else {
      updatedOutputs = outputs;
    }
    return {
      collapsed: true,
      node_id,
      node_name,
      node_type,
      node_status,
      elapsed_time,
      start_time,
      inputs,
      outputs: updatedOutputs,
      meta_data,
    };
  }

  /** 更新Agent的整体调试信息 */
  private updateAgentDebugInfo(agent_info: any) {
    this.agentDebugInfo.list = [];
    if (this.isEmptyObject(agent_info)) {
      return;
    }

    const { start_time, end_time, inputs, outputs, error_info } = agent_info;
    if (start_time) {
      this.agentDebugInfo.list.push({
        title: this.i18n.transform('start_time_label'),
        content: start_time,
      });
    }

    if (end_time) {
      this.agentDebugInfo.list.push(
        { title: this.i18n.transform('end_time_label'), content: end_time },
        {
          title: this.i18n.transform('running_time_label'),
          content: flowCommonLogic.calcElapsedTime(start_time, end_time),
        },
      );
    }
    this.agentDebugInfo.inputs = inputs;
    let updatedOutputs;
    if (!outputs && !error_info) {
      updatedOutputs = '';
    } else if (error_info) {
      updatedOutputs = { outputs, error_info };
    } else {
      updatedOutputs = outputs;
    }
    this.agentDebugInfo.outputs = updatedOutputs;
  }

  /** 更新Agent运行结果的状态和描述 */
  private updateAgentStatus(status: string) {
    this.agentDebugInfo.status = status;
    this.agentDebugInfo.status_desc = flowCommonLogic.getWorkflowStatusDesc(
      this.agentDebugInfo.status,
    );
    this.cdr.markForCheck();
  }

  /** 调用链表格中所有节点恢复成收起状态 */
  private resetCollapsedState() {
    this.callChainInfo.forEach((item) => {
      item.collapsed = true;
    });
  }

  /** 将时间戳转换为yyyy-MM-dd HH:mm:ss.SSSSSS  */
  private formatTimestamp(timestamp: number): string {
    const date = new Date(timestamp);
    const datePart = date.toISOString().slice(0, 10);
    const timePart = date.toISOString().slice(11, 26);
    return `${datePart} ${timePart}`;
  }

  private initializeDates(): void {
    const dates = new Array(7).fill(0).map((item, i) => {
      let date = new Date();
      date.setDate(date.getDate() - i);
      const formattedDate = `${date.getFullYear()}-${String(
        date.getMonth() + 1,
      ).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
      return { value: formattedDate, label: formattedDate, totalCount: 0, successCount: 0, failCount: 0, disabled: false, ...getTimeByDate(formattedDate) };
    });
    this.dates = [{ value: this.ALL_ITEM, label: this.i18n.transform('all'), totalCount: 0, successCount: 0, failCount: 0, disabled: false }, ...dates];
  }

  private handleAllDate(convListParam?: any[]): void {
    this.resetDateCounts();
    const convList = convListParam || this.conversationList || [];
    if (!convList.length) {
      this.updateDateDisabled();
      return;
    }

    const allExecPromises = convList.map(conv =>
      this.agentRepoServe.getExecList(this.agent_id, conv.conversation_id)
        .then(res => res.execution_queries || [])
        .catch(() => [])
    );

    Promise.all(allExecPromises).then(allExecutions => {
      const flatExecutions = allExecutions.flat();
      flatExecutions.forEach((item) => {
        const dateString = getDateByTemp(item.start_time);
        const dateItem = this.dates.find(date => date.value === dateString);
        if (!dateItem) {
          return;
        }
        dateItem.totalCount += 1;
        dateItem.successCount += item.status === 'succeeded' ? 1 : 0;
        dateItem.failCount += item.status === 'failed' ? 1 : 0;
      });
      this.updateDateDisabled();
      this.cdr.markForCheck();
    });
  }

  private resetDateCounts(): void {
    this.dates.forEach(item => {
      item.totalCount = 0;
      item.successCount = 0;
      item.failCount = 0;
    });
  }

  private updateDateDisabled(): void {
    this.dates.forEach(item => {
      if (item.value === 'all') {
        return;
      }
      item.disabled = !item.totalCount;
    });
  }
}
