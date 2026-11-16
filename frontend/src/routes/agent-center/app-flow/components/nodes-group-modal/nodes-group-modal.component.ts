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
        { data: this.appFlowServ.getInitTemplateTransformNodeData() },
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
        { data: this.appFlowServ.getInitHttpNodeData() },
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
    {
      name: this.i18n.transform('node_g_database'),
      nodes: [
        {
          data: this.appFlowServ.getInitSqlNodeData(),
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

  /** 拖拽期间在 document 级跟踪的最后已知鼠标坐标（client 系）；null = 本次拖拽尚未跟踪到位置 */
  public lastDragX: number | null = null;

  public lastDragY: number | null = null;

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

  public onDragStart(e: DragEvent) {
    if (this.isFlowReadonly) {
      return;
    }

    this.clickNodeX = e.offsetX;
    this.clickNodeY = e.offsetY;
    // 重置回退坐标：避免 Firefox"未移动即释放"（不触发 dragover）时
    // 误用上一次拖拽残留的陈旧坐标
    this.lastDragX = null;
    this.lastDragY = null;
    // Firefox 的 dragend 事件不携带有效坐标（clientX/Y 为 0），
    // 拖拽期间在 document 上持续跟踪最后已知鼠标位置作为回退
    this.trackLastDragPosition();
  }

  /** document 级拖拽监听的清理函数；null = 当前无活跃监听 */
  private removeDragListeners: (() => void) | null = null;

  /** 拖拽期间在 document 级跟踪最后已知鼠标坐标（client 系），供 dragend 坐标缺失时回退 */
  private trackLastDragPosition() {
    this.removeDragTrackListeners();
    const onDragOver = (ev: DragEvent) => {
      this.lastDragX = ev.clientX;
      this.lastDragY = ev.clientY;
    };
    const onDragEndCleanup = () => {
      this.removeDragTrackListeners();
    };
    this.removeDragListeners = () => {
      document.removeEventListener('dragover', onDragOver);
      document.removeEventListener('dragend', onDragEndCleanup);
      document.removeEventListener('drop', onDragEndCleanup);
    };
    document.addEventListener('dragover', onDragOver);
    document.addEventListener('dragend', onDragEndCleanup);
    document.addEventListener('drop', onDragEndCleanup);
  }

  private removeDragTrackListeners() {
    this.removeDragListeners?.();
    this.removeDragListeners = null;
  }

  ngOnDestroy() {
    // 兜底清理 document 级监听：组件销毁、浏览器失焦等场景
    // dragend/drop 可能不触发，避免监听器残留持有组件引用
    this.removeDragTrackListeners();
  }

  public onDragEnd(e: DragEvent, node: NodeInfo) {
    if (this.isFlowReadonly) {
      return;
    }

    // 用户按 Esc 取消或拖出窗口等无效拖放时 dropEffect 为 none，
    // 此时释放点即使落在画布内也不应创建节点
    if (e.dataTransfer && e.dataTransfer.dropEffect === 'none') {
      return;
    }

    // Chrome/Edge 的 dragend 携带准确坐标，优先使用；Firefox 的 dragend
    // 不携带有效坐标（clientX/Y 为 0），回退到拖拽期间跟踪的最后已知位置；
    // 两者均无（未移动即释放）→ 无有效落点，取消创建
    const dragendValid = e.clientX !== 0 || e.clientY !== 0;
    const clientX = dragendValid ? e.clientX : this.lastDragX;
    const clientY = dragendValid ? e.clientY : this.lastDragY;
    if (clientX === null || clientY === null) {
      return;
    }

    // 仅当释放点的实际顶层元素位于画布容器内才创建节点。
    // 节点面板 absolute 定位覆盖在画布之上，拖回面板释放时坐标仍会落在画布
    // 矩形范围内，仅凭矩形判断无法区分，需穿透层叠取真实元素判定；
    // 面板内 / 画布外 / 坐标无效（elementFromPoint 返回 null）均视为取消拖拽
    const hitElement = document.elementFromPoint(clientX, clientY);
    if (!hitElement || !this.graph.container.contains(hitElement)) {
      return;
    }

    // pageToLocal 期望页面坐标（含滚动偏移），由 client 坐标换算
    const pageX = clientX + window.scrollX;
    const pageY = clientY + window.scrollY;
    const ptl = this.graph.pageToLocal(pageX, pageY);
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
