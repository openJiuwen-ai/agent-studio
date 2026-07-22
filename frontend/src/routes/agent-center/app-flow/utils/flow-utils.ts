/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
import { Graph, Node, Util } from '@antv/x6';
import type { NodeMetadata, NodeProperties } from '@antv/x6';
import { I18NextEagerPipe } from 'angular-i18next';
import { capitalize, cloneDeep, isEmpty, omit } from 'lodash';
import {
  EHalfmodalType,
  IConnection,
  IEdgeType,
  ILayouts,
  IWorkflow,
  IWorkflowEdge,
} from '../app-flow.types';
import {
  EXCEPTION_PORT_NODE,
  FLOW_COLORS,
  NODE_SIZE,
  NODE_TYPE,
  PORT_CONNECTED,
  PORT_CONNECTED_ATTR,
  PORT_HOVER_NODE_RADIUS,
  PORT_HOVER_PORT_RADIUS,
  PORT_RADIUS,
  PORT_STROKE_WIDTH,
} from '../flow.const';
import {
  IAgentRepo,
  IBranch,
  IBranchNode, ICommentNode,
  IControllerAgents,
  IControllerFlow,
  IIntentBranch,
  IIntentContainerNode,
  IIntentNode,
  INodeType,
  IParamExtractionNode,
  ISetVariableNode,
  ISingleAgentNode,
  IViewNodeData,
  type IWFView,
  IWFViewParentType,
  IWFViewWithMultiType,
  IWorkflowField,
  NodeInfo,
} from '../node.type';
import { AppFlowService, INodeHeightUpdate } from '../app-flow.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { ICreateNodeConfig, IUpdateFlowConfig } from '../flow/flow.component';
import { NodeUtils } from '../components/utils';
import i18next from 'i18next';
import Hierarchy from '@antv/hierarchy';
import { I18nNamespace } from '@i18n';
import { AGENT_MODE_CODE } from '@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.constant';
import { isArray, isString } from "lodash";

/** 连接桩配置信息 */
export const ports = {
  groups: {
    top: {
      position: 'top',
      attrs: {
        circle: {
          r: PORT_RADIUS,
          magnet: true,
          style: {
            visibility: 'hidden',
          },
          stroke: FLOW_COLORS.portStroke,
          strokeWidth: PORT_STROKE_WIDTH,
          fill: '#C2C2C2',
        },
      },
    },
    right: {
      position: 'right',
      attrs: {
        circle: {
          style: {
            visibility: 'visible',
          },
          r: PORT_RADIUS,
          magnet: true,
          stroke: FLOW_COLORS.portStroke,
          strokeWidth: PORT_STROKE_WIDTH,
          fill: FLOW_COLORS.defaultPort,
        },
      },
    },
    bottom: {
      position: 'bottom',
      attrs: {
        circle: {
          strokeWidth: PORT_STROKE_WIDTH,
          fill: '#C2C2C2',
          r: PORT_RADIUS,
          magnet: true,
          stroke: FLOW_COLORS.portStroke,
          style: {
            visibility: 'hidden',
          },
        },
      },
    },
    left: {
      position: 'left',
      attrs: {
        circle: {
          r: PORT_RADIUS,
          magnet: true,
          stroke: FLOW_COLORS.portStroke,
          strokeWidth: PORT_STROKE_WIDTH,
          fill: FLOW_COLORS.defaultPort,
          style: {
            visibility: 'visible',
          },
        },
      },
    },
    ab: {
      position: 'absolute',
      attrs: {
        circle: {
          r: PORT_RADIUS,
          magnet: true,
          stroke: FLOW_COLORS.portStroke,
          strokeWidth: PORT_STROKE_WIDTH,
          fill: FLOW_COLORS.defaultPort,
          style: {
            visibility: 'visible',
          },
        },
      },
      args: { x: '100%', y: '50%' },
    },
  },
  items: [
    {
      group: 'left',
    },
    {
      group: 'right',
    },
  ],
};
export const HoverPorkMarkup = [
  {
    tagName: 'circle',
    selector: 'button',
    attrs: {
      r: PORT_HOVER_PORT_RADIUS,
      fill: '#1890ff',
      stroke: '#fff',
      strokeWidth: 2,
      cursor: 'crosshair',
    },
  },
  {
    tagName: 'line',
    selector: 'h-line',
    attrs: {
      x1: -5,
      y1: 0,
      x2: 5,
      y2: 0,
      stroke: '#fff',
      strokeWidth: 2,
      strokeLinecap: 'round',
      pointerEvents: 'none',
    },
  },
  {
    tagName: 'line',
    selector: 'v-line',
    attrs: {
      x1: 0,
      y1: -5,
      x2: 0,
      y2: 5,
      stroke: '#fff',
      strokeWidth: 2,
      strokeLinecap: 'round',
      pointerEvents: 'none',
    },
  },
];

const findNodeInputs = (inputs, name) => {
  if (inputs.schema) {
    for (let i = 0; i < inputs.schema.length; i++) {
      if (`intermediate_loop_var.${inputs.schema[i].name}` === name) {
        return true;
      }
    }
  }
  return false;
};

export const TargetMarker = {
  tagName: 'path',
  d: Util.normalizeMarker(' M0,0 L8,8 M0,0 L8,-8'),
  fill: 'none',
  strokeWidth: 2,
  strokeLinejoin: 'round',
  strokeLinecap: 'round',
};

export const FlowUtils = {
  initTemplateNode(params: {
    x: any;
    y: any;
    id: any;
    name: any;
    type: any;
    shape: string;
    ports?: any;
    data?: any;
    graph?: Graph;
    height?: number | any;
  }): NodeMetadata {
    const initParams: NodeMetadata = {
      shape: params.shape,
      x: Number(params.data.display_x) || params.x,
      y: Number(params.data.display_y) || params.y,
      id: params.id,
      type: params.data.type,
      name: params.data.name,
      ports: {
        groups: ports.groups,
        items: params.ports,
      },
      data: {
        ngArguments: {
          nodeInfo: { ...params.data },
        },
      },
    };
    if (params.type === 'Comment') {
      initParams.width = params.data.width??NODE_SIZE.width;
      initParams.height = params.data.height?? NODE_SIZE.height;
    }
    if (params.height) {
      initParams.width = NODE_SIZE.width;
      initParams.height = Math.max(params.height, NODE_SIZE.height);
    }
    return initParams;
  },

  getStartEndNode(params: {
    x: number;
    y: number;
    id: string;
    name: string;
    type: string;
    ports?: any;
    isStartOrEnd?: any;
    data?: any;
  }): any {
    return {
      shape: `op-${params.type.toLowerCase()}-node`,
      x: Number(params.data.display_x) || params.x,
      y: Number(params.data.display_y) || params.y,
      id: params.id,
      type: params.type,
      name: params.name,
      ports: {
        groups: ports.groups,
        items:
          params.type === 'Start'
            ? [
                {
                  id: params.ports[0].id,
                  group: 'right',
                  attrs: {
                    circle: {
                      r: PORT_RADIUS,
                      fill: FLOW_COLORS.defaultPort,
                      stroke: FLOW_COLORS?.portStroke,
                      strokeWidth: PORT_STROKE_WIDTH,
                      magnet: true,
                    },
                  },
                },
              ]
            : [
                {
                  id: params.ports[1].id,
                  group: 'left',
                  attrs: {
                    circle: {
                      r: PORT_RADIUS,
                      magnet: true,
                      stroke: FLOW_COLORS.portStroke,
                      strokeWidth: PORT_STROKE_WIDTH,
                      fill: FLOW_COLORS.defaultPort,
                    },
                  },
                },
              ],
      },
      data: {
        ngArguments: {
          nodeInfo: params.data.nodeInfo,
        },
      },
    };
  },

  processFetchedNodes(nodes: NodeInfo[], layout: ILayouts, env: string): any[] {
    const isMultiAgent = nodes.some((item) => item.type === 'Controller');

    return (nodes || []).map((item: NodeInfo) => {
      const pos = layout[item.id];

      let nodePorts;
      let height;

      if (item.type === 'Branch') {
        nodePorts = this.getBranchNodePorts(
          item.id,
          (item as IBranchNode).branches,
          (item as IBranchNode).isTemp
        );
      } else if (
        item.type === 'IntentDetection' ||
        item.type === 'ComplexIntentDetection'
      ) {
        // 若configs对象中存在意图包，表示为高级模式
        if (this.isAdvancedModeNew(item)) {
          nodePorts = [
            {
              id: 'branch_0',
              group: 'right',
            },
            {
              id: `${item.id as string}-4`,
              group: 'left',
            },
          ];
        } else {
          const branches = (item as IIntentNode).branches;
          height = branches.length * NODE_SIZE.onePortHeight;
          nodePorts = this.getIntentNodePorts(item.id, branches);
        }
      } else if (['LoopInput', 'LoopOutput'].includes(item.type)) {
        if (item.type === 'LoopInput') {
          nodePorts = [
            {
              id: `${item.id}-2`,
              group: 'right',
            },
          ];
        } else {
          nodePorts = [
            {
              id: `${item.id}-4`,
              group: 'left',
            },
          ];
        }
      } else {
        if (env === 'multi') {
          nodePorts = this.processMultiAgentNodes(item);
        } else {
          nodePorts = this.getNormalNodePorts(item.id);
        }
      }

      const configs = (item as any).configs;
      //异常分支增加port
      if (
        EXCEPTION_PORT_NODE.includes(item.type) &&
        configs?.exception_process?.handle_type === 'errorbranch'
      ) {
        nodePorts.push({
          id: `exception_branch`,
          group: 'right',
        });
      }
      if (
        item.type === 'ParamExtraction' &&
        configs?.exception_config?.exception_condition?.conditions?.length
      ) {
        nodePorts.push({
          id: `exception_branch`,
          group: 'right',
        });
      }

      const workflowShapeSuffix =
        isMultiAgent && item.type === 'Workflow' ? '-multi' : '';

      const singleAgentPrefix = this.isSingleAgentNodeType(
        isMultiAgent,
        item as ISingleAgentNode,
      )
        ? 'single-'
        : '';

      return {
        id: item.id,
        shape: `op-${singleAgentPrefix}${(
          item.type as string
        ).toLowerCase()}${workflowShapeSuffix}-node`,
        y: pos?.y ?? 225,
        x: pos?.x ?? 225,
        name: item.name,
        type: item.type,
        ports: nodePorts,
        data: {
          nodeInfo: item,
          ...item,
        },
        height,
      };
    });
  },

  processFetchedComments(
    nodes: ICommentNode[],
    layout: ILayouts,
    env: string,
  ): any[] {
    return (nodes || []).map((item: ICommentNode) => {

      return {
        id: item.id,
        shape: `op-${(item.type as string).toLowerCase()}-node`,
        y: item?.y ?? 225,
        x: item?.x ?? 225,
        name: item.name,
        type: item.type,
        width: item.width,
        height: item.height,
        data: {
          ...item,
        },
      };
    });
  },

  isSingleAgentNodeType(
    isMultiAgent: boolean,
    nodeInfo: ISingleAgentNode,
  ): boolean {
    return (
      isMultiAgent &&
      nodeInfo.type?.toLowerCase?.() === NODE_TYPE.AGENT &&
      [
        AGENT_MODE_CODE.DEEP_MODE,
        AGENT_MODE_CODE.GENERAL_MODE,
        AGENT_MODE_CODE.PLANNING_MODE,
      ].includes(nodeInfo.configs?.mode?.toLowerCase?.() as AGENT_MODE_CODE)
    );
  },

  processFetchedEdgeData(edges: IWorkflowEdge[]): IEdgeType[] {
    let index = 1;

    return (edges || []).flatMap((item) => {
      const edgeId = `edge${index++}`;
      const sourceCell = item.source;
      let sourcePort = `${item.source}-2`;
      const targetCell = item.target;
      const targetPort = `${item.target}-4`;

      if (item.branch) {
        // 如果有 branch 说明该连接的sourceCell是分支节点或者意图识别节点
        sourcePort = item.branch;
      }

      if (item.exception_branch) {
        // 如果有 branch 说明该连接的sourceCell是分支节点或者意图识别节点
        sourcePort = 'exception_branch';
      }

      return [
        {
          id: edgeId,
          shape: 'dag-edge',
          source: {
            cell: sourceCell,
            port: sourcePort,
          },
          target: {
            cell: targetCell,
            port: targetPort,
          },
          zIndex: 1,
        },
      ];
    });
  },

  getInitNodePorts(
    params: NodeInfo,
    env: string,
  ): {
    ports: Array<{ id: string; group: string }>;
    height?: number;
  } {
    if (params.type === 'Branch') {
      return {
        ports: [
          {
            id: `${params.id}-4`,
            group: 'left',
          },
          {
            id: `if`,
            group: 'right',
          },
          {
            id: `default`,
            group: 'right',
          },
        ],
      };
    }
    if (params.type === 'IntentDetection') {
      const topOffset = 100;
      const step = 57.8;

      let branches = cloneDeep((params as IIntentNode).branches);
      if (branches.length > 0 && branches[0].id === 'branch_0') {
        branches = branches.slice(1).concat(branches[0]);
      }

      return {
        ports: [
          {
            id: `${params.id}-4`,
            group: 'left',
          },
          ...branches?.map((item: IIntentBranch, i: number) => {
            return {
              id: item?.id,
              group: 'ab',
              args: {
                x: '100%',
                y: topOffset + i * step,
              },
            };
          }),
        ],
        height: 197,
      };
    }

    if (params.type === 'ComplexIntentDetection') {
      const topOffset = 100;
      const step = 57.8;

      let branches = cloneDeep((params as IIntentNode).branches);
      if (branches.length > 0 && branches[0].id === 'branch_0') {
        branches = branches.slice(1).concat(branches[0]);
      }

      return {
        ports: [
          {
            id: `branch_0`,
            group: 'right',
          },
          {
            id: `${params.id}-4`,
            group: 'left',
          },
          ...branches.map((item: IIntentBranch, i: number) => {
            return {
              id: item.id,
              group: 'ab',
              args: {
                x: '100%',
                y: topOffset + i * step,
              },
            };
          }),
        ],
        height: 197,
      };
    }

    if (env === 'multi') {
      const ports = this.processMultiAgentNodes(params);
      if (ports.length) {
        return { ports };
      }
    }

    return { ports: this.getNormalNodePorts(params.id) };
  },

  getNormalNodePorts(id: string) {
    return [
      {
        id: `${id}-2`,
        group: 'right',
      },
      {
        id: `${id}-4`,
        group: 'left',
      },
    ];
  },

  getBranchNodePorts(id: string, branches: IBranch[], isTemp = false) {
    if (isTemp) {
      return [
        {
          id: `${id}-4`,
          group: 'left',
        },
        ...(branches || []).map((item) => ({
          id: item.branch,
          group: 'right',
        })),
      ];
    }
    const branchPorts = [
      {
        id: `${id}-4`,
        group: 'left',
      },
      {
        id: `if`,
        group: 'right',
      },
      {
        id: `default`,
        group: 'right',
      },
    ];

    if (branches?.length) {
      const elseIfPorts = branches
        .map((b) => b.id)
        .filter((portId) => {
          // id 形如 'elseIf-1'
          const idParts = portId.split('-');
          if (idParts.length > 1 && idParts[0] === 'elseIf') {
            return true;
          }
          return false;
        });

      if (elseIfPorts.length) {
        branchPorts.splice(
          2,
          0,
          ...elseIfPorts.map((portId) => ({
            id: portId,
            group: 'right',
          })),
        );
      }
    }

    return branchPorts;
  },

  getIntentNodePorts(id: string, branches: IIntentBranch[]) {
    let branchesCopy = cloneDeep(branches);
    if (branchesCopy.length > 0 && branchesCopy[0].id === 'branch_0') {
      branchesCopy = branchesCopy.slice(1).concat(branchesCopy[0]);
    }

    const branchPorts = [
      {
        id: `${id}-4`,
        group: 'left',
      },
      ...(branchesCopy || []).map((item) => ({
        id: item.id,
        group: 'right',
      })),
    ];

    return branchPorts;
  },

  getBranchPortIndex(name: string): number {
    const nameFrags = name.split('_');

    return Number(nameFrags[nameFrags.length - 1]);
  },

  getIntentBranchPortText(name: string) {
    if (name === 'branch_0') {
      return `${i18next.t('other_intentions', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      })}`;
    }

    return `${i18next.t('intention', {
      ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    })}${this.getBranchPortIndex(name)}`;
  },

  updatePortColor(graph: Graph, portId: IConnection, color: string): void {
    const node = graph.getCellById(portId.cell) as Node;
    const port = node?.getPort(portId.port);

    if (port) {
      const connectedStatus =
        color === FLOW_COLORS.connected
          ? PORT_CONNECTED.connected
          : PORT_CONNECTED.defaultPort;

      node?.portProp(
        portId.port,
        {
          attrs: {
            circle: {
              fill: color,
              [PORT_CONNECTED_ATTR]: connectedStatus,
            },
          },
        },
        { ignoreHistory: true },
      );
    }
  },

  updateEdgePortColor(graph: Graph, edge: IEdgeType, color: string): void {
    graph.batchUpdate(() => {
      const { target, source } = edge;

      this.updatePortColor(graph, target, color);
      this.updatePortColor(graph, source, color);
    });
  },

  getGraphNodeNames(graph: Graph): string[] {
    return graph
      .getNodes()
      .map((cls) => cls?.data?.ngArguments?.nodeInfo?.name ?? '');
  },

  getUniqueName(names: string[], originName: string): string {
    let i = 1;
    let name = originName;

    while (names.includes(name)) {
      name = `${originName}_${i}`;
      ++i;
    }

    return name;
  },

  initNode(params: any, graph: Graph, env: string): NodeMetadata {
    const { x, y, shape, ...restData } = params;
    const portsInfo = this.getInitNodePorts(params, env);

    // 确保新拖入的节点名称不重复
    const names = this.getGraphNodeNames(graph);
    restData.name = this.getUniqueName(names, restData.name);
    const initParams: NodeMetadata = {
      id: params.id,
      shape,
      x,
      y,
      ports: {
        ...ports,
        items: portsInfo.ports,
      },
      data: {
        ngArguments: {
          nodeInfo: restData,
        },
      },
    };
    if (portsInfo.height) {
      initParams.width = NODE_SIZE.width;
      initParams.height = portsInfo.height;
    }
    return initParams;
  },
  initCommentNode(params: any, graph: Graph, env: string): NodeMetadata {
    const { x, y, shape, ...restData } = params;

    // 确保新拖入的节点名称不重复
    const names = this.getGraphNodeNames(graph);
    restData.name = this.getUniqueName(names, restData.name);
    const initParams: NodeMetadata = {
      id: params.id,
      shape,
      x,
      y,
      data: {
        ngArguments: {
          nodeInfo: {
            ...restData,
            content: restData?.content ? restData.content : '',
          },
        },
      },
      width: restData?.width,
      height: restData?.height,
    };

    return initParams;
  },

  getLoopIONode(
    ioType: 'input' | 'output',
    loopId: string,
    i18n: I18NextEagerPipe,
  ) {
    const id = `${loopId}_${ioType}`;
    const name = i18n.transform(`loop_${ioType}`);
    const type = `Loop${capitalize(ioType)}`;

    return {
      shape: `op-loop${ioType}-node`,
      id,
      type,
      name,
      ports: {
        ...ports,
        items: [
          {
            id: `${id}-${ioType === 'input' ? 2 : 4}`,
            group: `${ioType === 'input' ? 'right' : 'left'}`,
          },
        ],
      },
      data: {
        ngArguments: {
          nodeInfo: {
            id,
            type,
            name,
          },
        },
      },
    };
  },

  /** 意图节点切换为高级模式后，修改连接桩的布局 */
  advancedIntentNodePortHandler(
    node: Node<NodeProperties>,
    nodeUpdate: INodeHeightUpdate,
  ) {
    let topOffset = 80;
    const tipsHeight = 24;

    if (nodeUpdate.hasTips) {
      topOffset += tipsHeight;
    }

    const updateIds =
      (node.getData()?.ngArguments?.nodeInfo as IIntentNode)?.branches?.map(
        (branch: any) => branch.id,
      ) ?? [];
    const currentPortIds = node
      .getPorts()
      .filter((p) => p.group !== 'left')
      .map((p) => p.id) as string[];

    const isExpand = nodeUpdate.isExpand;

    for (let i = 0; i < updateIds.length; ++i) {
      if (!currentPortIds.includes(updateIds[i])) {
        // insert
        const insertIndex = FlowUtils.getBranchPortIndex(updateIds[i]);
        node.insertPort(insertIndex, {
          id: updateIds[i],
          attrs: {
            circle: {
              fill: FLOW_COLORS.defaultPort,
              [PORT_CONNECTED_ATTR]: PORT_CONNECTED.defaultPort,
            },
          },
          group: isExpand ? 'ab' : 'right',
        });
      }
    }

    currentPortIds.forEach((branchId) => {
      if (!updateIds.includes(branchId)) {
        node.removePort(branchId);
      }
    });

    if (nodeUpdate.isExpand) {
      const ports = node.getPorts().filter((p) => p.group !== 'left');
      for (let i = 0; i < ports.length; ++i) {
        node.portProp(
          ports[i].id,
          {
            group: 'right',
            attrs: {
              text: null,
            },
          },
          { ignoreHistory: true },
        );
      }
    } else {
      const ports = node.getPorts().filter((p) => p.group !== 'left');
      ports.forEach((p, i) => {
        node.portProp(
          p.id,
          {
            group: 'right',
            args: null,
            attrs: {
              text: {
                fontSize: 12,
                fill: '#666',
              },
            },
          },
          { ignoreHistory: true },
        );
      });
    }
  },

  /** 在容器节点和相绑定的高级意图节点之间，创建连接线 */
  linkIntentAndContainerNode(graph: Graph) {
    const allNodes = graph.getNodes();
    allNodes.forEach((node) => {
      const advancedIntentId = node.id;
      const uuid = advancedIntentId.split('_')[1];
      const containerNodeId = `node_intent_container_${uuid}`;
      const containerNode = graph.getCellById(containerNodeId);

      if (containerNode) {
        const containerZIndex = containerNode.getZIndex();
        const nestedZIndex =
          containerZIndex - 1 === 0 ? 1 : containerZIndex - 1;
        const edgeZIndex = containerNode.getParent() ? nestedZIndex : 0;

        const edge = graph.addEdge({
          id: `edge_${Date.now()}`,
          shape: 'dag-edge',
          source: {
            cell: advancedIntentId,
            port: 'branch_0',
          },
          target: {
            cell: containerNodeId,
            port: `${containerNodeId}-4`,
          },
          zIndex: edgeZIndex,
        });

        FlowUtils.updateEdgePortColor(
          graph,
          edge as IEdgeType,
          FLOW_COLORS.connected,
        );
      }
    });
  },

  /** @param id 画布上，当前被用户选中的高级意图节点id */
  getAdvancedNodeClicked(id: string, graph: Graph): any {
    const allNodesData = graph.getNodes().map((node: any) => {
      return {
        ...node.getData(),
        ...node.getBBox(),
      };
    });

    const intentDetectionNode = allNodesData.find(
      (node: any) =>
        node.ngArguments.nodeInfo.type === 'ComplexIntentDetection' &&
        node.ngArguments.nodeInfo.id === id,
    );
    return intentDetectionNode;
  },

  /** 在节点对象里，若configs对象中存在意图包，表示为高级模式-新 */
  isAdvancedModeNew(node: NodeInfo): boolean {
    return node?.type === 'ComplexIntentDetection';
  },

  /** 在节点对象里，若configs对象中存在意图包，表示为高级模式 */
  isAdvancedMode(node: NodeInfo): boolean {
    return (
      node.type === 'IntentDetection' &&
      !!(node as IIntentNode)?.configs?.intent?.id?.trim()
    );
  },

  /** 在节点对象里，若configs中没有意图包，表示为普通模式 */
  isNormalMode(node: NodeInfo): boolean {
    return (
      node?.type === 'IntentDetection' &&
      !(node as IIntentNode)?.configs?.intent
    );
  },

  /**
   * 更新被选中的子工作流节点版本
   * @param body - 被选中的子工作流节点的最新版本数据。
   * @param updateFlowData - 更新工作流的dsl。
   * @param checkRefChangeAndUpdateNode - 更新子工作流的节点配置抽屉和卡片上最新输入参数列表。
   */
  updateChildFlowVersion(
    body: any,
    graph: Graph,
    workflowDetail: IWorkflow,
    appFlowServ: AppFlowService,
    updateFlowData: Function,
    checkRefChangeAndUpdateNode: Function,
  ) {
    if (!isEmpty(body)) {
      const inputs = appFlowServ.updateChildFlow2ApiNode(body.inputs);
      const bodyParams: any = appFlowServ.getUpdateGraphData(
        graph,
        workflowDetail,
      );

      let oldFlowNodeData = null;
      let newFlowNodeData = null;

      bodyParams.workflow_details.nodes = bodyParams.workflow_details.nodes.map(
        (node: any) => {
          const { ref_workflows, showIcon, ...restParams } = node;

          if (node.id === body.id) {
            oldFlowNodeData = { ...restParams };
            newFlowNodeData = {
              ...restParams,
              ...body,
              inputs,
            };
            return newFlowNodeData;
          }

          if (node.type === 'Workflow') {
            const matchedNode = appFlowServ
              .getResNodes()
              .find((i) => i.ref_workflows?.workflow_id === node.configs?.id && i.id === node.id);

            const showIcon = matchedNode?.showIcon;
            return {
              ...node,
              showIcon,
            };
          }

          return node;
        },
      );

      if (oldFlowNodeData && newFlowNodeData) {
        checkRefChangeAndUpdateNode(oldFlowNodeData, newFlowNodeData);
      }

      updateFlowData(
        {
          isDrag: false,
          successCb: () => {
            // 升级新版本成功后，卡片上的提示图标消失
            const newChildFlowWithIcon = {
              ...newFlowNodeData,
              showIcon: false,
            };
            appFlowServ.setResNodes([newChildFlowWithIcon]);
            MessageComponent.showSuccess(
              i18next.t('upgrade_success_alert', {
                ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
              }),
              3000,
            );

            // 升级新版本成功后，刷新卡片上的版本号信息
            const nodes = bodyParams?.workflow_details?.nodes || [];
            const childFlowNodes = nodes
              .filter((node) => node?.type === 'Workflow')
              .map((node) => {
                const ref_workflows = appFlowServ
                  .getAppRefs()
                  ?.filter((item) => item.workflow_id === node.configs?.id);

                return {
                  ...node,
                  ref_workflows: ref_workflows[0],
                };
              });
            appFlowServ.setResNodes(childFlowNodes);
          },
        },
        bodyParams,
      );
    }
  },

  /**
   * 生成意图节点的唯一名称。
   * 高级模式，需要在原有nodeName前面添加"高级"；
   * 普通模式，需要移除nodeName最前面的"高级"。
   */
  uniqueIntentName(
    graph: Graph,
    nodeData: NodeInfo,
    isAdvanced: boolean,
  ): string {
    let updatedName = nodeData.name;

    const prefix = i18next.t('advanced', {
      ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    });
    if (isAdvanced && !nodeData.name.startsWith(prefix)) {
      updatedName = `${prefix}${nodeData.name}`;
    }

    if (!isAdvanced && nodeData.name.startsWith(prefix)) {
      updatedName = nodeData.name.replace(new RegExp(`^${prefix}`), '');
    }

    // 过滤当前节点的名称，避免每次点确定时，重复添加后缀
    const currentNames = FlowUtils.getGraphNodeNames(graph).filter(
      (name) => name !== nodeData.name,
    );
    return FlowUtils.getUniqueName(currentNames, updatedName);
  },

  /**
   * 切换意图包后，需要将对应的容器节点的dsl信息更新成默认值。
   * @param nodeData 当前被选中的高级意图节点数据
   * @param containerNodeId 与高级意图节点绑定的容器节点id
   */
  updateContainerNodeDsl(
    graph: Graph,
    workflowDetail: IWorkflow,
    nodeData: NodeInfo,
    containerNodeId: string,
    getNodeInfoById: (id: string) => NodeInfo | null,
    appFlowServ: AppFlowService,
  ) {
    const isContainerNode = getNodeInfoById(
      containerNodeId,
    ) as IIntentContainerNode;

    if (!isContainerNode) {
      return null;
    }

    const intentIds = isContainerNode.branches
      .map((item) => item.configs.intent_id)
      .filter((item) => item && item.trim() !== '');

    const bodyParams = appFlowServ.getUpdateGraphData(graph, workflowDetail);

    // 检查高级意图节点的意图包和容器节点的意图包是否一致。若不同，则将容器节点的dsl信息恢复成默认值
    if (
      intentIds[0] &&
      (nodeData as IIntentNode).configs.intent.id !== intentIds[0]
    ) {
      const targetIndex = bodyParams.workflow_details.nodes.findIndex(
        (node: any) => node.id === containerNodeId,
      );

      if (targetIndex !== -1) {
        const { branches, configs, inputs, outputs } =
          appFlowServ.getInitIntentContainerNodeData(isContainerNode.id);

        bodyParams.workflow_details.nodes[targetIndex] = {
          ...bodyParams.workflow_details.nodes[targetIndex],
          branches,
          configs,
          inputs,
          outputs,
        };
      }
    }

    return bodyParams;
  },

  /** 将容器节点的最新数据同步到X6节点的ngArguments中 */
  syncContainerInfoToGraph(
    graph: Graph,
    bodyParams: IWorkflow,
    containerNodeId: string,
  ) {
    const containerDslInfo = bodyParams.workflow_details.nodes.find(
      (node) => node.id === containerNodeId,
    ) as IIntentContainerNode;

    if (!containerDslInfo) {
      return;
    }

    // 获取容器节点最新的dsl数据
    const { branches, configs, inputs, outputs } = containerDslInfo;
    // 获取X6画布上的容器节点
    const containerNode = graph.getCellById(containerNodeId);
    const nodeInfo = containerNode.data.ngArguments
      .nodeInfo as IIntentContainerNode;

    nodeInfo.branches = branches;
    nodeInfo.configs = configs;
    nodeInfo.inputs = inputs;
    nodeInfo.outputs = outputs;
  },

  syncParamExtractionInfoToGraph(
    graph: Graph,
    bodyParams: IWorkflow,
    nodeId: string,
  ) {
    const paramExtractionDslInfo = bodyParams.workflow_details.nodes.find(
      (node) => node.id === nodeId,
    ) as IParamExtractionNode;

    if (!paramExtractionDslInfo) {
      return;
    }

    // 获取容器节点最新的dsl数据
    const { configs, inputs, outputs } = paramExtractionDslInfo;
    // 获取X6画布上的容器节点
    const paramExtractionNode = graph.getCellById(nodeId);
    const nodeInfo = paramExtractionNode.data.ngArguments
      .nodeInfo as IParamExtractionNode;

    nodeInfo.configs = configs;
    nodeInfo.inputs = inputs;
    nodeInfo.outputs = outputs;
  },

  /** 更新容器节点的dsl数据，并同步到X6对应节点的ngArguments中 */
  updateContainerFlowData(
    graph: Graph,
    workflowDetail: IWorkflow,
    appFlowServ: AppFlowService,
    updateFlowData: (
      config: IUpdateFlowConfig,
      bodyParams?: any,
    ) => Promise<void>,
    newContainerDsl: IIntentContainerNode | IAgentRepo,
  ): void {
    if (isEmpty(newContainerDsl)) {
      return;
    }

    const bodyParams = appFlowServ.getUpdateGraphData(graph, workflowDetail);
    bodyParams.workflow_details.nodes = bodyParams.workflow_details.nodes.map(
      (node) => {
        return node.id === newContainerDsl.id ? newContainerDsl : node;
      },
    );

    updateFlowData(
      {
        isDrag: false,
        successCb: () => {
          if (newContainerDsl.type === 'IntentDetectionContainer') {
            MessageComponent.showPrompt(
              i18next.t('upgrade_intent_container_success_tip', {
                ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
              }),
              3000,
            );
            const { branches } = newContainerDsl as IIntentContainerNode;
            const containerNode = graph.getCellById(newContainerDsl.id);
            const nodeInfo = containerNode.data.ngArguments
              .nodeInfo as IIntentContainerNode;
            nodeInfo.branches = branches;
          } else {
            MessageComponent.showSuccess(
              i18next.t('upgrade_version_successful', {
                ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
              }),
            );
            const { configs } = newContainerDsl as IAgentRepo;
            const agentNode = graph.getCellById(newContainerDsl.id);
            const nodeInfo = agentNode.data.ngArguments.nodeInfo as IAgentRepo;
            nodeInfo.configs.plugins = configs.plugins;
          }
        },
      },
      bodyParams,
    );
  },

  /**
   * 复制一个整体内的容器节点。
   * @param {string} id 被选中待复制的高级意图节点id
   * @param {string} newId 复制完成的高级意图节点id
   */
  copyContainerNodeInGroup(
    nodeId: string,
    graph: Graph,
    newId: string,
    createNode: (params, configs: ICreateNodeConfig) => Node,
    handleAdvancedIntentConns: Function,
    updateRef: Function,
    updateFlowData: Function,
  ) {
    const uuid = nodeId.split('_')[1];
    // 获取被选中待复制的这个整体内的容器节点id
    const containerNodeId = `node_intent_container_${uuid}`;
    const containerNode = graph.getCellById(containerNodeId);

    if (containerNode) {
      const { position, shape, data } = containerNode.toJSON();
      // 复制完成的新容器节点id
      const newContainerId = `node_intent_container_${newId.split('_')[1]}`;

      const { name, type, ...restData } = data.ngArguments.nodeInfo as NodeInfo;

      createNode(
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
      setTimeout(async () => {
        handleAdvancedIntentConns(newId);
        updateRef();
        await updateFlowData({
          isDrag: false,
        });
      });
    }
  },

  /** 更改全局配置后更新相关节点 */
  updateRefsAfterConfigsChange(
    configs,
    oldConfigs,
    graph,
    updateRefType,
    self,
  ) {
    const oldMemory = cloneDeep(oldConfigs?.memory);
    const newMemory = cloneDeep(configs?.memory);
    const updateMemory = newMemory?.filter((newItem) =>
      oldMemory?.some((oldItem) => oldItem.name === newItem.name),
    );
    const initialNodeIds = [];
    const nodes = graph.getNodes();
    nodes.forEach((node) => {
      const incomingEdges = graph.getIncomingEdges(node);
      if (!incomingEdges?.length) {
        initialNodeIds.push(node.id);
      }
    });
    const updateRefs = NodeUtils.getOutputsRefIndex(
      'node_start',
      updateMemory,
      ['memory'],
    );
    initialNodeIds.forEach((id) => updateRefType.bind(self)(id, updateRefs));
  },

  /** 处理生成节点赋值更新后的settings */
  getSetvariableNewSettings(affectedNode) {
    const newSettings = (affectedNode as ISetVariableNode).configs.settings.map(
      (setting, index) => {
        const { type, value, schema } = (affectedNode as ISetVariableNode)
          .inputs[index];
        const left = {
          type,
          value,
          schema,
        };
        if (!schema) {
          delete left.schema;
          delete setting.right.schema;
        } else {
          setting.right.schema = cloneDeep(left.schema);
        }
        setting.left = left;
        if (setting.right.type !== left.type) {
          setting.right.type = left.type;
        }
        return setting;
      },
    );
    return newSettings;
  },

  getNodePosByAddFromBar(graph: Graph, nodeType: INodeType) {
    let x = 0;
    let y = 0;
    const graphNodesData = graph.getNodes().map((node) => {
      return {
        ...node.getData(),
        ...node.getBBox(),
      };
    });

    const graphApiNodesData = graphNodesData.filter(
      (node) => node.ngArguments.nodeInfo.type === nodeType,
    );

    if (graphApiNodesData.length) {
      x = (graphApiNodesData[graphApiNodesData.length - 1].x as number) + 60;
      y = (graphApiNodesData[graphApiNodesData.length - 1].y as number) + 60;
    }

    if (graphNodesData.length) {
      x = (graphNodesData[graphNodesData.length - 1].x as number) + 60;
      y = (graphNodesData[graphNodesData.length - 1].y as number) + 60;
    }

    return { x, y };
  },

  /** 生成树形布局的数据结构，并按照水平方向进行排列 */
  generateTreeLayout(
    allNodeData: any,
    appFlowServ: AppFlowService,
    workflows: IControllerFlow[] | IViewNodeData[],
    isOptimized: boolean,
    agents: any[],
    graph: any,
  ) {
    const controllerNode = allNodeData.find(
      (node: any) => node.ngArguments.nodeInfo.type === 'Controller',
    );
    if (!controllerNode) {
      return null;
    }

    const getMergedConfigs = (id, configs) => {
      const oldNode = allNodeData.find(
        node => node.ngArguments?.nodeInfo?.configs?.id === id
      );

      const oldConfigs = oldNode?.ngArguments?.nodeInfo?.configs || {};
      const filteredConfigs = Object.entries(configs).reduce((acc, [key, value]) => {
        if (value !== undefined) {
          acc[key] = value;
        }
        return acc;
      }, {});

      return {
        ...oldConfigs,
        ...filteredConfigs
      };
    };

    const render_workflow_nodes = (workflows) => {
      if(!workflows) {
        return [];
      }

      return workflows.map((f) => {
        return {
          ...appFlowServ.getInitWorkflowNodeData(
            f.name,
            f.inputs,
            f.outputs,
            getMergedConfigs(f.id, f.configs),
          ),
          id: f.node_id,
          x: controllerNode.x + 1200,
          parent_node_type: 'sub_controller',
          shape: 'op-workflow-multi-node',
        };
      });
    };

    const treeData = {
      id: controllerNode.ngArguments.nodeInfo.id,
      children: [],
    };

    workflows.forEach((f) => {
      if (!f) {
        return;
      }

      if (isOptimized) {
        // 布局优化
        treeData.children.push({
          id: f.node_id,
        });
      } else {
        // 新增/修改一个工作流卡片
        if (f?.inputs && f?.outputs) {
          treeData.children.push({
            ...appFlowServ.getInitWorkflowNodeData(
              f.name,
              f.inputs,
              f.outputs,
              getMergedConfigs(f.id, f.configs),
            ),
            id: f.node_id,
            x: controllerNode.x + 250,
            shape: 'op-workflow-multi-node',
          });
        }
      }
    });

    agents.forEach((aItems) => {
      const configs = getMergedConfigs(aItems.id, aItems.configs);
      if(aItems.type?.toLowerCase() === 'agent') {
        treeData.children.push({
          id: aItems?.node_id ?? aItems.id,
          name: aItems.name,
          type: 'Agent',
          configs: configs,
          x: controllerNode.x + 250,
          input: null,
          output: null,
          with: 378,
          height: 155,
          shape: 'op-single-agent-node',
        });
      } else {
        treeData.children.push({
          id: aItems?.node_id ?? aItems.id,
          name: aItems.name,
          type: 'SubController',
          configs: configs,
          x: controllerNode.x + 250,
          shape: 'op-subcontroller-node',
          with: 378,
          height: 390,
          children: render_workflow_nodes(aItems.configs?.workflows),
        });
      }
    });

    const layoutRes = Hierarchy.mindmap(treeData, {
      direction: 'H',
      getHeight(d: any) {
        return d.height ?? 180;
      },
      getWidth(d: any) {
        return d.width ?? 75;
      },
      getHGap: () => 80,
      getVGap: () => 10,
      getSide: () => 'right',
    });
    return { controllerNode, layoutRes };
  },

  /** 连接控制器节点和叶子结点 */
  linkControllerToLeaf(
    controllerId: string,
    leafId: string,
    workflowDetail: IWorkflow,
    graph: Graph,
  ) {
    const edge = graph.addEdge({
      id: `edge_${leafId}`,
      shape: 'dag-edge',
      source: { cell: controllerId, port: `${controllerId}-2` },
      target: { cell: leafId, port: `${leafId}-4` },
      zIndex: 0,
    });

    FlowUtils.updateEdgePortColor(
      graph,
      edge as IEdgeType,
      FLOW_COLORS.connected,
    );
  },

  /** 删除工作流卡片：若X6画布里有id等于"end"的对象，但workflows数组里没有 */
  deleteWorkflowNodes(
    allNodeData: any,
    workflows: IControllerFlow[],
    deleteNode: Function,
  ) {
    const workflowNodes = allNodeData.filter(
      (f) => f.ngArguments.nodeInfo.type === 'Workflow',
    );

    const workflowNodeIds = workflowNodes.map((f) => f.ngArguments.nodeInfo.id);
    const workflowIds = workflows
      .filter((f) => f && f.node_id)
      .map((f) => f.node_id);

    // 获取X6画布里存在，但workflows数组里没有的节点对象
    const extraNodes = workflowNodeIds.filter(
      (nodeId) => !workflowIds.includes(nodeId),
    );
    // 删除
    extraNodes.forEach((nodeId) => deleteNode(nodeId, false));
  },

  /*删除sub_controller 子agent*/
  deleteSubControllerNodes(
    allNodeData: any,
    agents: IControllerAgents[],
    deleteNode: Function,
    graph: any,
  ) {
    const subControllerNodeIds = allNodeData
      .filter((f) => {
        const type = f.ngArguments.nodeInfo.type;
        return type === 'SubController' || type  === 'Agent';
      }).map((f) =>
        f.ngArguments.nodeInfo.id,
      );
    const subControllerIds = agents
      ?.filter((f) => f && f.node_id)
      .map((f) => f.node_id);

    // 获取X6画布里存在，但workflows数组里没有的节点对象
    const extraNodes = subControllerNodeIds.filter(
      (nodeId) => !subControllerIds.includes(nodeId),
    );

    // 删除
    extraNodes.forEach((nodeId) => {
      deleteNode(nodeId, false);
    });
  },
  /** 在multi agent中，对控制器和工作流节点应用树形布局算法 */
  applyTreeLayout(
    allNodeData: any[],
    appFlowServ: AppFlowService,
    workflows: IControllerFlow[] | IViewNodeData[],
    agents: any[],
    isOptimized: boolean,
    localScale: string,
    workflowDetail: IWorkflow,
    graph: Graph,
  ) {
    const result = this.generateTreeLayout(
      allNodeData,
      appFlowServ,
      workflows,
      isOptimized,
      agents,
      graph,
    );
    if (!result) {
      return;
    }

    const { controllerNode, layoutRes } = result;
    // 计算local坐标系和graph坐标系的坐标偏移量
    const localToGraphDeltaY = controllerNode.position.y - layoutRes.y;
    const localToGraphDeltaX = controllerNode.position.x - layoutRes.x;
    // 基于controller节点卡片高度一半的偏移量
    const scale = Number(localScale) / 100;
    const controllerHalfYOffset = (controllerNode.height * scale) / 3.4;

    layoutRes.children.forEach((node: any) => {
      if (!isOptimized) {
        // 新建
        const newLeafNode = this.initNode(
          {
            ...node.data,
            y: node.y + localToGraphDeltaY + controllerHalfYOffset, // 根据树形布局结果修正纵坐标偏移
          },
          graph,
          'multi',
        );
        // 创建叶子节点添加到X6画布上
        graph.addNode(newLeafNode);
        // 叶子节点在画布上的连线关系
        this.linkControllerToLeaf(
          controllerNode.ngArguments.nodeInfo.id,
          newLeafNode.id,
          workflowDetail,
          graph,
        );

        node.children.forEach((sub_child) => {
          const subnewLeafNode = this.initNode(
            {
              ...sub_child.data,
              y: sub_child.y + localToGraphDeltaY + controllerHalfYOffset, // 根据树形布局结果修正纵坐标偏移
            },
            graph,
            'multi',
          );
          // 创建叶子节点添加到X6画布上
          graph.addNode(subnewLeafNode);
          // 叶子节点在画布上的连线关系
          this.linkControllerToLeaf(
            node.id,
            subnewLeafNode.id,
            workflowDetail,
            graph,
          );
        });
      } else {
        // 布局优化
        const controllerCell = graph.getCellById(
          controllerNode.ngArguments.nodeInfo.id,
        );
        if (controllerCell?.isNode()) {
          // 更新根节点坐标
          (controllerCell as Node).position(
            layoutRes.x + localToGraphDeltaX - 320,
            layoutRes.y + localToGraphDeltaY,
          );
        }

        const cell = graph.getCellById(node.id);

        if (cell?.isNode()) {
          (cell as Node).position(
            node.x + localToGraphDeltaX,
            node.y + localToGraphDeltaY + controllerHalfYOffset,
          );
        }
      }
    });
  },

  /** multi agent：构造put接口的请求体，删除多余key-value */
  buildMultiAgentReqParams(flowReqParams: IWorkflow) {
    return {
      ...omit(flowReqParams, [
        'workflow_details',
        'icon',
        'tools',
        'workflows',
        'ref_workflows',
        'mcp_servers',
        'knowledge_repos',
        'status',
        'creator',
        'creator_id',
        'created_on',
        'workflow_switch_enabled',
        'scheduling_mode',
        'is_drag',
      ]),
      details: {
        ...flowReqParams.details,
        nodes: flowReqParams.workflow_details.nodes,
        edges: flowReqParams.workflow_details.edges,
        layouts: flowReqParams.workflow_details.layouts,
      },
      type: 'controller',
    };
  },

  /** 在multi agent中，去除多余连接桩 */
  processMultiAgentNodes(item: NodeInfo & { shape?: string }) {
    if ((item as any)?.shape === 'op-workflow-multi-node') {
      return [{ id: `${item.id}-4`, group: 'left' }];
    }

    switch (item.type) {
      case 'SubController': {
        return [
          { id: `${item.id}-2`, group: 'right' },
          { id: `${item.id}-4`, group: 'left' },
        ];
      }
      case 'Controller': {
        return [{ id: `${item.id}-2`, group: 'right' }];
      }
      case 'Workflow': {
        return [{ id: `${item.id}-4`, group: 'left' }];
      }
      case 'Agent': {
        if (this.isSingleAgentNodeType(true, item as ISingleAgentNode)) {
          return [{ id: `${item.id}-4`, group: 'left' }];
        }
        return [];
      }
      default: {
        return [];
      }
    }
  },

  fields2Views(
    fields: IWorkflowField[],
    depth = 0,
    parentType: IWFViewParentType = 'none',
  ): IWFViewWithMultiType[] {
    const views: IWFViewWithMultiType[] = fields.map((field, index) => {
      const { name, type, description, required, schema, source, value } =
        field;
      const view: IWFViewWithMultiType = {
        name,
        key: `k_${depth}_${index}_${Math.random().toString(36).substring(2, 10)}`,
        type: type.split('/'),
        description,
        required,
        source,
        depth,
        parentType,
        value,
      };

      if (type === 'array') {
        if ((schema as IWorkflowField).type === 'object') {
          view.type = ['array<object>'];
          view.children = this.fields2Views(
            ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
            depth + 1,
            view.type[0] as IWFViewParentType,
          );
          view.expanded = true;
        } else {
          const subType = (schema as IWorkflowField).type;
          if (subType.includes('file')) {
            const fileType = subType.split('/')[1];
            view.type = [`${type}<file>`, fileType];
          } else {
            view.type = [`array<${subType}>`];
          }
        }
      }

      if (type === 'object') {
        view.children = this.fields2Views(
          (schema ?? []) as IWorkflowField[],
          depth + 1,
          view.type[0] as IWFViewParentType,
        );
        view.expanded = true;
      }

      return view;
    });

    return views;
  },

  //开始节点对象模板导入格式转换
  objectTempStartNodeFields2Views(
    fields: IWorkflowField[],
    depth = 0,
    parentType: IWFViewParentType = 'none',
  ): IWFViewWithMultiType[] {
    const views: IWFViewWithMultiType[] = fields.map((field, index) => {
      const { name, type, description, schema, value } = field;
      const view: IWFViewWithMultiType = {
        name,
        type: type.split('/'),
        description,
        required: true,
        source: 'user',
        depth,
        parentType,
        value,
        key: `${depth}_${index}_${name}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      };

      if (type === 'array') {
        if ((schema as IWorkflowField).type === 'object') {
          view.type = ['array<object>'];
          view.children = this.objectTempStartNodeFields2Views(
            ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
            depth + 1,
            view.type[0] as IWFViewParentType,
          );
          view.expanded = true;
        } else {
          const subType = (schema as IWorkflowField).type;
          if (subType.includes('file')) {
            const fileType = subType.split('/')[1];
            view.type = [`${type}<file>`, fileType];
          } else {
            view.type = [`array<${subType}>`];
          }
        }
      }

      if (type === 'object') {
        view.children = this.objectTempStartNodeFields2Views(
          (schema ?? []) as IWorkflowField[],
          depth + 1,
          view.type[0] as IWFViewParentType,
        );
        view.expanded = true;
      }

      return view;
    });

    return views;
  },

  //上下文变量对象模板导入格式转换
  objectTempIWFields2Views(
    fields: IWorkflowField[],
    depth = 0,
    parentType: IWFViewParentType = 'none',
  ): IWFView[] {
    const views: IWFView[] = fields.map((field, index) => {
      const { name, type, description, schema, value } = field;
      let midValue = value;
      if (value && value.default !== null) {
        midValue = {
          content: value.default,
          type: 'literal',
          hint: '',
          default: '',
        };
      }
      const view: IWFView = {
        name,
        type: type,
        description,
        required: true,
        source: 'pre_defined',
        depth,
        parentType,
        value: midValue,
        key: `${depth}_${index}_${name}_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
      };

      if (type === 'array') {
        if ((schema as IWorkflowField).type === 'object') {
          view.type = 'array<object>';
          view.children = this.objectTempIWFields2Views(
            ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
            depth + 1,
            'array<object>' as IWFViewParentType,
          );
          view.expanded = true;
        }
      }

      if (type === 'object') {
        view.children = this.objectTempIWFields2Views(
          (schema ?? []) as IWorkflowField[],
          depth + 1,
          'object' as IWFViewParentType,
        );
        view.expanded = true;
      }

      return view;
    });

    return views;
  },

  /**
   * 关闭所有不等于当前类型的半屏抽屉
   * @param type 各类半屏抽屉的枚举值
   * @param modalConfig 每个EHalfmodalType都映射到一个关闭方法
   */
  closeOtherHalfmodal(
    type: EHalfmodalType,
    modalConfig: { [key in EHalfmodalType]: () => void },
  ) {
    Object.entries(modalConfig).forEach(([key, modalAction]) => {
      const modalType = key as EHalfmodalType;
      if (type !== modalType) {
        modalAction();
      }
    });
  },

  getNodeDSLFromRaw(node: Node) {
    return node.data?.ngArguments?.nodeInfo as NodeInfo | null;
  },

  nodeDesci18nMap(type: string) {
    if (type === 'IntentDetectionContainer') {
      return '';
    }

    return i18next?.t(`nodeDesc.${type}`, {
      ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    });
  },


  checkPath(data, path: string[]): boolean {
    if (path.length === 0) {
      return true;
    }

    const currentPath = path[0];
    const arr = currentPath.split('[');
    const currentName = arr[0];

    const currentItem = data.find(item => item.name === currentName);
    if (!currentItem) {
      return false;
    }

    let nextData: any;
    if (currentItem.type === 'object') {
      nextData = currentItem.schema;
    } else if (currentItem.type === 'array') {
      nextData = currentItem.schema.schema;
    } else {
      return currentItem.name === currentName;
    }

    if (Array.isArray(nextData)) {
      const nextItem = nextData;
      return this.checkPath(nextItem, path.slice(1));
    } else {
      return false;
    }
  },

  // 判断引用参数是否存在
  handelNodeRefChange(data: any, inputs = []) {
    const { outputsMap, memory, environment, request, nodesList} = data;
    if (!outputsMap) {
      return;
    } else {
      inputs.forEach((v: any) => {
        if (v?.value?.type === 'ref') {
          const ref_var_name = v.value?.content?.ref_var_name || '';
          const ref_source = v.value?.content?.source || '';
          const refNode = cloneDeep(outputsMap[v.value?.content?.ref_node_id]);
          if (ref_var_name.includes('memory.')) {
            // 对比记忆变量
            if (memory.length) {
              let memos = cloneDeep(memory);
              let memosNames = memos.map(m => {
                return `memory.${m.name}`;
              });
              v.refWithout = !memosNames.includes(ref_var_name);
            } else {
              v.refWithout = true;
            }
          } else if (ref_var_name.includes('sys.')) {
            // 系统变量
            v.refWithout = false;
          } else if (ref_source === 'environment') {
            // 环境变量
            v.refWithout = !environment.find(env => {
              return env.name === ref_var_name;
            });
          } else if (ref_source === 'request') {
            // 请求变量
            if (ref_var_name.includes('.')) {
              const haveRef = this.checkPath(request, ref_var_name.split('.'));
              v.refWithout = !haveRef;
            } else {
              v.refWithout = !request.find(env => {
                return env.name === ref_var_name;
              });
            }
          } else {
            // 前置节点引用参数
            const names = refNode?.map(v => v.name) || [];
            // 不是系统变量
            if (names.length) {
              // 纯对象的判断
              if (ref_var_name.includes('.')) {
                const haveRef = this.checkPath(refNode, ref_var_name.split('.'));
                v.refWithout = !haveRef;
              } else {
                v.refWithout = !names.includes(v.value?.content?.ref_var_name);
              }
            } else {
              v.refWithout = true;
            }

            // 引用循环节点index,中间参数
            const nodeFind = nodesList.find(findNode => findNode.id === v.value?.content?.ref_node_id);
            if (nodeFind && nodeFind.type === 'Loop') {
              if (ref_var_name === 'index' && v.value?.content?.source === 'pre_defined') {
                v.refWithout = false;
              }
              if (ref_var_name.startsWith('intermediate_loop_var.')) {
                const nodeIntermediateLoop = nodeFind.inputs.find(nodeInputs => nodeInputs.name === 'intermediate_loop_var');
                v.refWithout = !findNodeInputs(nodeIntermediateLoop, ref_var_name);
              }
            }
          }
        } else {
          if (v) {
            v.refWithout = false;
          }
        }
      });
    }
  },
  getLlmField(metadata: any, field: 'llm_inputs' | 'llm_outputs') {
    if (!metadata?.llm_info) {
      return null;
    }

    const llmInfo = metadata?.llm_info;
    // 若llm_info是对象
    if (!isArray(llmInfo)) {
      //去除开头换行
      if (field === 'llm_outputs' && isString(llmInfo[field])) {
        return llmInfo[field].trim()
      }
      return llmInfo[field];
    }

    // 若llm_info是数组，取最后一个元素
    if (isArray(llmInfo) && llmInfo.length > 0) {
      const lastElm = llmInfo[llmInfo.length - 1];
      //去除开头换行
      if (field === 'llm_outputs' && isString(lastElm[field])) {
        return lastElm[field].trim()
      }
      return lastElm[field];
    }
    return null;
  }
};
