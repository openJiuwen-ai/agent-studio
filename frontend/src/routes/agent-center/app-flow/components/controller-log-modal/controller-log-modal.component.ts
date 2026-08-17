import { ChangeDetectorRef, Component, Input, Output, EventEmitter } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { Clipboard } from '@angular/cdk/clipboard';
import { TimeLineComponent } from '@routes/agent-center/app-insight/components/time-line/time-line.component';
import { ActivatedRoute } from '@angular/router';
import { IControllerNode } from '../../node.type';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { v4 as uuidV4 } from 'uuid';
import { AppFlowService } from '../../app-flow.service';
import { AssetLogIconComponent } from '@shared/components/assets/asset-log-icon/asset-log-icon.component';
import { AssetListIconComponent } from '@shared/components/assets/asset-list-icon/asset-list-icon.component';
import { AssetCalendarIconComponent } from '@shared/components/assets/asset-calendar-icon/asset-calendar-icon.component';
import { AssetSequenceIconComponent } from '@shared/components/assets/asset-sequence-icon/asset-sequence-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetSuccessIconComponent } from '@shared/components/assets/asset-success-icon/asset-success-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { AssetErrorIconComponent } from '@shared/components/assets/asset-error-icon/asset-error-icon.component';
import { AssetGenerateLoadingIconComponent } from '@shared/components/assets/asset-generate-loading-icon/asset-generate-loading-icon.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { cloneDeep } from 'lodash';
import { AppControllerRepoService, CONVERSATION_TYPE } from '@services/agent-center/app-controller.service';
import { ParamExtractionLogComponent } from '@routes/agent-center/app-flow/components/flow-log-modal/param-extraction-log/param-extraction-log.component';

import type { IWorkflow } from '@routes/agent-center/app-flow/app-flow.types';
import { WORKFLOW_SVGS } from '@routes/agent-center/app-flow/flow.const';
import { FlowLogModalComponent, IConversationRequest, LIMIT_COUNT } from '@routes/agent-center/app-flow/components/flow-log-modal/flow-log-modal.component';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { Node, NodeProperties } from '@antv/x6';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';
import { DateOptionRender } from '@routes/agent-center/app-agent/components/date-option-render/date-option-render.component';

@Component({
  selector: 'controller-log-modal',
  templateUrl: './controller-log-modal.component.html',
  styleUrls: ['./controller-log-modal.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    JsonViewerComponent,
    AppMarkdownAnswerComponent,
    TimeLineComponent,
    AssetLogIconComponent,
    AssetListIconComponent,
    AssetCalendarIconComponent,
    AssetSequenceIconComponent,
    AssetCopyIconComponent,
    AssetLoadingIconComponent,
    AssetCopySuccessIconComponent,
    AssetSuccessIconComponent,
    AssetGenerateLoadingIconComponent,
    AssetErrorIconComponent,
    NoDataIconComponent,
    ParamExtractionLogComponent,
    DateOptionRender,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ControllerLogModalComponent extends FlowLogModalComponent {
  @Input() workflowDetail!: IWorkflow;

  controllerTree: any = [];

  callChainInfoTree: any = [];

  workflowMap = new Map();

  paramExtractionWorkflowMap = {};

  constructor(
    public override route: ActivatedRoute,
    public override clipboard: Clipboard,
    public override cdr: ChangeDetectorRef,
    public override i18n: I18NextEagerPipe,
    public override flowRepoServe: AppFlowRepoService,
    public override flowServe: AppFlowService,
    public controllerServe: AppControllerRepoService
  ) {
    super(route, clipboard, cdr, i18n, flowRepoServe, flowServe);
    this.route.queryParams.subscribe(params => {
      this.workflow_id = params.id;
    });
    this.initializeDates();
  }

  override ngAfterViewInit() {
    this.getWorkflowMap();
    this.getConversations().then(() => {
      this.handleAllDate();
    });
  }

  initController() {
    const controller: IControllerNode = <IControllerNode>this.workflowDetail?.details?.nodes?.find(node => node.type === 'Controller');
    if (!controller) {
      return;
    }
    const { id, name, type, configs } = controller;
    const tempTree = {
      id,
      name,
      treeType: 'controller',
      children: [],
      expanded: true,
    };
    configs.agents.forEach((agent: any) => {
      const { id, name, configs } = agent;
      const result = {
        id,
        name,
        treeType: 'subController',
        children: [],
        expanded: true,
      };
      result.children = agent.configs.workflows.map(({ id, name }) => {
        return { id, name, treeType: 'workflow' };
      });
      tempTree.children.push(result);
    });
    configs.workflows.forEach(({ id, name }) => {
      tempTree.children.push({ id, name, treeType: 'workflow' });
    });
    this.controllerTree = [tempTree];
    this.callChainInfoTree = cloneDeep(this.controllerTree);
  }

  getWorkflowMap() {
    this.workflowDetail?.details?.nodes?.forEach((node: any) => {
      if (node.type === 'Workflow') {
        if (node.configs?.id) {
          this.workflowMap.set(node.configs.id, {
            name: node.name,
            node_id: node.id,
          });
        }
      }
    });
  }

  public override async onBeforeOpenConv(isOpen: boolean) {
    if (isOpen) {
      this.loadingConversation = true;
      this.cdr.markForCheck();
      try {
        const result = await this.controllerServe.getConversationList(this.workflow_id, {
          ...this.dateRange,
          limit: LIMIT_COUNT,
          offset: 0,
          type: CONVERSATION_TYPE.CONTROLLER,
        });
        this.conversationList = result.conversation_infos;
      } catch {
        this.conversationList = [];
      }
      this.loadingConversation = false;
      this.cdr.markForCheck();
    }
  }

  public override async onBeforeOpenExec(isOpen: boolean) {
    if (isOpen) {
      this.loadingExecution = true;
      this.cdr.markForCheck();
      const { conversation_id } = this.conversationSelected || {};
      if (conversation_id) {
        try {
          const result = await this.controllerServe.getExecList(this.workflow_id, conversation_id);
          this.executionList = result.executions;
        } catch {
          this.executionList = [];
        }
      } else {
        this.executionList = [];
      }
      this.loadingExecution = false;
      this.cdr.markForCheck();
    }
  }

  loadingConversation = false;
  loadingExecution = false;

  public getSVG(type: string) {
    if (type === 'workflow') {
      return WORKFLOW_SVGS.WorkflowMulti;
    }
    return WORKFLOW_SVGS.Controller;
  }

  protected override async getConversations(params: IConversationRequest = {}) {
    if (!this.showLogDrawer) {
      return;
    }
    try {
      const res = await this.controllerServe.getConversationList(this.workflow_id, {
        ...params,
        limit: LIMIT_COUNT,
        offset: 0,
        type: CONVERSATION_TYPE.CONTROLLER,
      });
      this.conversationList = res.conversation_infos;
      if (this.conversationList.length > 0) {
        const prevId = this.conversationSelected?.conversation_id;
        const matched = prevId
          ? this.conversationList.find((c: any) => c.conversation_id === prevId)
          : null;
        if (matched) {
          this.conversationSelected = matched;
        } else if (this.conversationId) {
          const found = this.conversationList.find((c: any) => c.conversation_id === this.conversationId);
          this.conversationSelected = found || this.conversationList[0];
        } else {
          this.conversationSelected = this.conversationList[0];
        }
        const { conversation_id } = this.conversationSelected || {};
        this.getExecutions(conversation_id);
      } else {
        this.conversationSelected = {};
        this.executionSelected = {};
        this.callChainInfo.list = [];
        this.timelineData = {};
        this.workflowDebugInfo = {
          status: '',
          status_desc: '',
          list: [],
          result: '',
        };
      }
      this.cdr.markForCheck();
    } catch {
      this.conversationList = [];
      this.cdr.markForCheck();
    }
  }

  protected override async getExecutions(conversation_id: string) {
    try {
      const res = await this.controllerServe.getExecList(this.workflow_id, conversation_id);
      this.executionList = res.executions;
      if (this.executionList.length > 0) {
        this.executionSelected = this.executionList?.[0];
        const { conversation_id, execution_id } = this.executionList?.[0] || {};
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

  protected override getSingleExecDetail(workflowId: string, conversationId: string, executionId: string) {
    this.controllerServe.getSingleExecInfo(workflowId, executionId).then((result: any) => {
      this.result = [];
      const invocations = [];
      this.paramExtractionWorkflowMap = {};
      (result?.nestedWorkflows || []).forEach(e => {
        const { workflow_id, workflow_name } = e || {};
        if (workflow_id && workflow_name) {
          this.paramExtractionWorkflowMap[workflow_id] = workflow_name;
        }
      });
      (result?.invocations || []).forEach(item => {
        item.node_uuid = uuidV4();
        if (item.application_type === 'WORKFLOW' && !item.parent_node_id) {
          const app = this.workflowMap.get(item.application_id);
          if (app) {
            const matchStart = invocations.find(i => i.node_id === app.node_id && i.node_status === 'node_started');
            const matchFinish = invocations.find(i => i.node_id === app.node_id && i.node_status === 'node_finished');
            if (!matchStart && !matchFinish) {
              invocations.push({
                node_id: app.node_id,
                node_name: app.name,
                node_type: 'Workflow',
                node_status: 'node_started',
                inputs: {},
                outputs: {},
                start_time: 0,
                end_time: 0,
              });
              invocations.push({
                node_id: app.node_id,
                node_name: app.name,
                node_type: 'Workflow',
                node_status: 'node_finished',
                inputs: {},
                outputs: {},
                start_time: 0,
                end_time: 0,
              });
            } else {
              if (item.node_type === 'Start') {
                matchStart.inputs = item.inputs;
                matchStart.start_time = item.start_time;
              }
              if (item.node_type === 'StructuredMessagesException') {
                if (this.isIOEmpty(item.outputs)) {
                  item.outputs = {
                    error_message: JSON.stringify(item.inputs),
                  };
                }
              }
              if (!matchFinish.isEnd) {
                matchFinish.status = item.status;
                matchFinish.outputs = item.outputs;
                matchFinish.error_message = item.error_message;
                matchFinish.end_time = item.end_time;
                matchFinish.inputs = matchStart.inputs;
                matchFinish.start_time = matchStart.start_time;
              }
              if (item.node_type === 'End' && item.node_status === 'node_finished') {
                matchFinish.isEnd = true;
              }
            }
            item.parent_node_id = app.node_id;
          }
        }
        invocations.push(item);
      });
      result.event_list = invocations;

      this.result = result;

      this.callChainInfo.list = this.convertToTableData(this.result?.event_list).filter(item => !item.parent_node_id);

      this.crumb = [
        {
          label: this.i18n.transform('parent'),
          id: '',
        },
      ];
      this.timelineData = this.convertToTimelineData(this.result?.event_list);
      this.timelineData.childInvokes = this.timelineData.childInvokes.filter(item => !item?.parent_node_id);

      const { status, start_time, end_time, outputs, error_info } = result;
      this.updateWorkflowDebugInfo(result);
      this.updateWorkflowStatus(status);
      if (status === 'succeeded') {
        this.workflowDebugInfo.result = outputs?.responseContent ?? '';
      } else {
        this.workflowDebugInfo.result = error_info ?? '';
      }
      this.cdr.markForCheck();
    });
  }

  private convertToTreeData(invocations: any[]): any[] {
    if (!invocations) {
      return [];
    }
    const eventListCopy = cloneDeep(invocations);
    const resultTree = cloneDeep(this.controllerTree);
    resultTree.forEach(c => {
      const cMatch = eventListCopy.findLast(e => c.id === e.node_id) || {};
      c.children.forEach(sw => {
        const swMatch = eventListCopy.findLast(e => c.id === e.node_id) || {};
        if (sw.treeType === 'subController') {
          sw.children.forEach(w => {
            const wMatch = eventListCopy.findLast(e => c.id === e.node_id) || {};
            w = {
              ...w,
              wMatch,
            };
          });
          sw = {
            ...sw,
            swMatch,
          };
        }
      });
      c = {
        ...c,
        cMatch,
      };
    });
    return resultTree;
  }

  protected override convertToTableData(invocations: any[]): any[] {
    if (!invocations) {
      return [];
    }
    const eventListCopy = cloneDeep(invocations);

    const startList = eventListCopy.filter(item => item.node_status === 'node_started' || item.node_status === 'STARTED' || !item.node_status);

    const llmNodeIds = eventListCopy
      .filter(item => {
        return (item.node_status === 'node_wait' || item.node_status === 'WAIT') && item.node_type === 'LLM';
      })
      .map(item => item.node_id);

    const tableData = startList
      .map(item => {
        if (!item.node_status) {
          return this.createTableItem({
            ...item,
            node_name: this.i18n.transform('llm_intent_identification'),
            node_type: 'Controller',
          });
        }
        const { node, additionalInfo } = this.findMatchingEndNode(eventListCopy, item);
        if (!node) return null;

        if (llmNodeIds.includes(node.node_id)) {
          const hasFinishedNode = eventListCopy.some(
            el => el.node_id === node.node_id && (el.node_status === 'node_finished' || el.node_status === 'FINISHED')
          );
          if (!hasFinishedNode) {
            node.status.desc = 'succeeded';
          }
        }

        let tableItem;
        if ((node.node_status === 'node_wait' || node.node_status === 'WAIT') && additionalInfo) {
          tableItem = this.createTableItemError(node, additionalInfo);
        } else {
          tableItem = this.createTableItem(node);
        }
        if (tableItem?.node_type === 'Questioner' || tableItem?.node_type === 'Agent') {
          if (additionalInfo) {
            this.processQuestionerNode(tableItem, node, additionalInfo);
          } else {
            this.processQuestionerNode(tableItem, node);
          }
        }
        if (tableItem?.node_type === 'ParamExtraction' || tableItem?.node_type === 'ParamOutput') {
          this.processParamExtractionNode(tableItem, node);
        }

        return tableItem;
      })
      .filter(item => item !== null);
    return tableData;
  }

  protected override processParamExtractionNode(callItem: any, node: any) {
    const cell: Node = this.graph?.getCellById(node.node_id) as Node<NodeProperties>;
    if (cell) {
      const nodeInfo = FlowUtils.getNodeDSLFromRaw(cell);
      callItem.nodeInfo = nodeInfo;
    }
    callItem.nestedWorkflows = this.paramExtractionWorkflowMap;
  }
}
