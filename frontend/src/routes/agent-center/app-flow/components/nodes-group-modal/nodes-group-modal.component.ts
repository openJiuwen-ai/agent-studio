import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  OnInit,
  Output,
  SimpleChanges,
} from '@angular/core';
import { Graph } from '@antv/x6';
import { StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { IPlugin, IPluginWithTools } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import {
  AppPluginRepoService
} from "@services/agent-center/app-plugin-repo.service";
import { CommonService } from '@services/common.service';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '../../app-flow.service';
import type {
  PublishedWorkflow,
  WorkFlowType
} from '../../app-flow.types';
import { WORKFLOW_SVGS } from '../../flow.const';
import {
  INodeType,
  NodeInfo
} from '../../node.type';

interface INodeGroup {
  name: string;
  nodes: {
    data: NodeInfo;
    visible?: boolean;
  }[];
  visible?: boolean;
}


interface NodeGroup {
  name: string;
  pluginData?: IPluginWithTools[];
  workflowData?: PublishedWorkflow[]
}

export type AddMode = 'common' | 'onCell';

@Component({
  selector: 'meta-nodes-group-modal',
  templateUrl: './nodes-group-modal.component.html',
  styleUrls: ['./nodes-group-modal.component.less'],
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
    AppFlowService,
  ],
})
export class NodesGroupModalComponent implements OnChanges, OnInit {
  @Input('isFlowReadonly') isFlowReadonly = false;

  @Input('workflowType') workflowType: WorkFlowType = 'chat';

  @Input('addMode') addMode: AddMode = 'common';

  @Input() graph: Graph;

  @Output() createNode = new EventEmitter<
    NodeInfo & {
      id: string;
      name: string;
      type: INodeType;
      x: number;
      y: number;
      shape: string;
    }
  >();

  public nodeIcons = {
    Move: cdnAssetUrl('assets/agent-center/flow/move.svg'),
    ...WORKFLOW_SVGS,
  };

  public tabs :any = [
    {
      title:  this.i18n.transform('preset'),
      active: true
    },
  ];
  public nodeGroups: INodeGroup[] = [
    {
      name: this.i18n.transform('node_g_general'),
      nodes: [
        { data: this.appFlowServ.getInitLLMChainNodeData() },
        { data: this.appFlowServ.getInitChildFlowData() },
        { data: this.appFlowServ.getInitAgentNodeData() },
      ],
    },
    {
      name: this.i18n.transform('node_g_logic'),
      nodes: [
        { data: this.appFlowServ.getInitBranchNodeData() },
        { data: this.appFlowServ.getInitIntentNodeData() },
        { data: this.appFlowServ.getInitCodeNodeData() },
        { data: this.appFlowServ.getInitComplexIntentDetectionNodeData() },
        { data: this.appFlowServ.getInitLoopNodeData() },
      ],
    },
    {
      name: this.i18n.transform('node_g_tool'),
      nodes: [
        {
          data: this.appFlowServ.getInitActionPluginNodeData(),
        },
        { data: this.appFlowServ.getInitMcpServiceData() },
      ],
    },
    {
      name: this.i18n.transform('node_g_msg'),
      nodes: [
        { data: this.appFlowServ.getInitMessageNodeData() },
        { data: this.appFlowServ.getInitStreamTransformNodeData() },
        { data: this.appFlowServ.getInitQuestionerNodeData() },
        { data: this.appFlowServ.getInitInputNodeData() },
        { data: this.appFlowServ.getInitQANodeData() },
        { data: this.appFlowServ.getInitExceptionNodeData() },
        { data: this.appFlowServ.getInitParamExtractionNodeData() },
      ],
    },
    {
      name: this.i18n.transform('node_g_data'),
      nodes: [
        {
          data: this.appFlowServ.getInitSetVariableNodeData(),
        },
        {
          data: this.appFlowServ.getInitAggregationNodeData(),
        },
        {
          data: this.appFlowServ.getInitKnowledgeRepoNodeData(),
        },
      ],
    },
  ];

  public customNodeGroups: NodeGroup[] = [
    {
      name: this.i18n.transform('plugin'),
      pluginData: [],
    },
    {
      name: this.i18n.transform('workflow'),
      workflowData: [],
    },
  ];

  public clickNodeX = 0;

  public clickNodeY = 0;

  public addedNum = 0;

  constructor(
    private appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    private appPluginRepoServ: AppPluginRepoService,
    private flowServ: AppFlowRepoService,
    protected commonService: CommonService,
  ) {}
  ngOnInit(): void {
    let projectID: any = '';
    try {
      const curSpaceOptions = StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
      projectID = JSON.parse(curSpaceOptions || '{}').projectId;
    } catch (error) {
      projectID = '';
    }
    const showMyCard = (this.configServ.getConfigs()?.card_whitelist || '').split(',').indexOf(projectID) !== -1;
    if (showMyCard) {
      this.nodeGroups[2].nodes.push({ data: this.appFlowServ.getInitCardNodeData() });
    }
    this.initNodeGroups();
    const params ={
      customize_node:true
    }
    this.getPluginList(params,0,30)
    this.getWorkflowList(params,0,30)
  }

  ngOnChanges(changes: SimpleChanges) {
    if (
      changes?.workflowType?.currentValue &&
      !changes?.workflowType.firstChange
    ) {
      this.initNodeGroups();
    }
  }

  initNodeGroups() {
    const { ltm_enable, site, block_nodes } =
      this.configServ.getConfigs() ?? {};
    const disableNodeTypes = [
      'Questioner',
      'Message',
      'Input',
      'Agent',
      'QA',
      'ParamExtraction'
    ];
    const blockNodeTypesCI = (block_nodes ?? []).map((type) =>
      type?.toLowerCase(),
    );

    this.nodeGroups.forEach((group) => {
      let unvisibleNodesCnt = 0;

      group.nodes.forEach((node) => {
        const muteInteractionNodeCondition =
          this.workflowType === 'task' &&
          disableNodeTypes.includes(node.data.type);
        const muteNodesBySetting = blockNodeTypesCI.includes(
          node.data.type?.toLowerCase(),
        );

        if (
          muteInteractionNodeCondition ||
          muteNodesBySetting
        ) {
          node.visible = false;
          ++unvisibleNodesCnt;
        } else {
          node.visible = true;
        }
      });

      if (unvisibleNodesCnt === group.nodes.length) {
        group.visible = false;
      } else {
        group.visible = true;
      }
    });
  }

  nodeDescription(type) {
    // 没有描述词条时则不显示
    if (this.i18n.transform(`nodeDesc.${type}`) !== `nodeDesc.${type}`) {
      return this.i18n.transform(`nodeDesc.${type}`);
    }
    return '';
  }

  public onDragStart(e: MouseEvent) {
    if (this.isFlowReadonly) {
      return;
    }

    this.clickNodeX = e.offsetX;
    this.clickNodeY = e.offsetY;
  }

  public onDragEnd(e: MouseEvent, node: NodeInfo) {
    if (this.isFlowReadonly) {
      return;
    }

    const ptl = this.graph.pageToLocal(e.pageX, e.pageY);
    const x =
      ptl.x < this.clickNodeX && ptl.x > 0 ? 0 : ptl.x - this.clickNodeX;
    const y =
      ptl.y < this.clickNodeY && ptl.y > 0 ? 0 : ptl.y - this.clickNodeY;

    this.createNode.emit({
      ...node,
      id: `node_${Date.now()}`,
      name: node.name,
      type: node.type,
      x,
      y,
      shape: `op-${node.type.toLowerCase()}-node`,
    });
  }

  public onClickAdd(e: MouseEvent, node: NodeInfo) {
    if (this.isFlowReadonly) {
      return;
    }
    const nodeX = 645;
    let { x, y } = this.graph.clientToLocal(nodeX + 32, e.clientY);
    x += this.addedNum * 32;
    y -= this.addedNum * 32;

    this.createNode.emit({
      ...node,
      id: `node_${Date.now()}`,
      name: node.name,
      type: node.type,
      x,
      y,
      shape: `op-${node.type.toLowerCase()}-node`,
    });

    ++this.addedNum;
  }

  public async onClickAddWorkflowNode(e: MouseEvent, node: PublishedWorkflow) {
    if (this.isFlowReadonly) {
      return;
    }
    const flow = await this.flowServ.getFlowVersionInfo(
      node.workflow_id,
      node.version_id,
    );
    const nodeX = 645;
    let { x, y } = this.graph.clientToLocal(nodeX + 32, e.clientY);
    x += this.addedNum * 32;
    y -= this.addedNum * 32;
    const apiNodeData = this.appFlowServ.childFlow2ApiNodeNew(flow, node);
    this.createNode.emit({
      ...apiNodeData,
      id: `node_${Date.now()}`,
      name: apiNodeData.name,
      type: apiNodeData.type,
      x,
      y,
      shape: `op-${apiNodeData.type.toLowerCase()}-node`,
    });
    ++this.addedNum;
  }

  public async onDragdWorkflowEnd(e: MouseEvent, node: PublishedWorkflow) {
    if (this.isFlowReadonly) {
      return;
    }
    const flow = await this.flowServ.getFlowVersionInfo(
      node.workflow_id,
      node.version_id,
    );
    const ptl = this.graph.pageToLocal(e.pageX, e.pageY);
    const x =
      ptl.x < this.clickNodeX && ptl.x > 0 ? 0 : ptl.x - this.clickNodeX;
    const y =
      ptl.y < this.clickNodeY && ptl.y > 0 ? 0 : ptl.y - this.clickNodeY;

    const apiNodeData = this.appFlowServ.childFlow2ApiNodeNew(flow, node);
    this.createNode.emit({
      ...apiNodeData,
      id: `node_${Date.now()}`,
      name: apiNodeData.name,
      type: apiNodeData.type,
      x,
      y,
      shape: `op-${apiNodeData.type.toLowerCase()}-node`,
    });
  }
  public async onClickAddPluginNode(e: MouseEvent, node: IPlugin) {
    if (this.isFlowReadonly) {
      return;
    }
    const nodeX = 645;
    let { x, y } = this.graph.clientToLocal(nodeX + 32, e.clientY);
    x += this.addedNum * 32;
    y -= this.addedNum * 32;
    const apiNodeData = this.appFlowServ.plugin2ApiNode(node);
    this.createNode.emit({
      ...apiNodeData,
      id: `node_${Date.now()}`,
      name: apiNodeData.name,
      type: apiNodeData.type,
      x,
      y,
      shape: `op-${apiNodeData.type.toLowerCase()}-node`,
    });
    ++this.addedNum;
  }


  public async onDragdPluginEnd(e: MouseEvent, node: IPlugin) {
    if (this.isFlowReadonly) {
      return;
    }
    const apiNodeData = this.appFlowServ.plugin2ApiNode(node);
    const ptl = this.graph.pageToLocal(e.pageX, e.pageY);
    const x =
      ptl.x < this.clickNodeX && ptl.x > 0 ? 0 : ptl.x - this.clickNodeX;
    const y =
      ptl.y < this.clickNodeY && ptl.y > 0 ? 0 : ptl.y - this.clickNodeY;
    this.createNode.emit({
      ...apiNodeData,
      id: `node_${Date.now()}`,
      name: apiNodeData.name,
      type: apiNodeData.type,
      x,
      y,
      shape: `op-${apiNodeData.type.toLowerCase()}-node`,
    });
  }

  private async getPluginList(params, offset, limit) {
    const {plugin_list, count} =
      await this.appPluginRepoServ.getPluginList({
        offset,
        limit,
        ...params,
        type:"inner"
      });
    this.customNodeGroups[0].pluginData = plugin_list
  }


  private async getWorkflowList(params, offset, limit) {
    const {workflow_version_list, count} = await this.flowServ.getPublishedFlows({
      offset,
      limit,
      ...params,
    });
    this.customNodeGroups[1].workflowData = workflow_version_list
  }

}
