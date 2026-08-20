import { Injectable, Renderer2 } from '@angular/core';
import { NodeService } from '../node.service';
import { AppFlowService, INodeHeightUpdate } from '../app-flow.service';
import { FlowUtils } from './flow-utils';
import { Cell, CellMetadata, Graph, MiniMap, Node, NodeProperties } from '@antv/x6';
import {
  BRANCH_ARRAY,
  IBranchNode,
  IIntentNode,
  ILoopNode,
} from '../node.type';
import {
  FLOW_COLORS,
  NODE_HEIGHT_OFFSET,
  NODE_SIZE,
  PORT_CONNECTED,
  PORT_CONNECTED_ATTR,
} from '../flow.const';
import { IEdgeType, IWorkflow } from '../app-flow.types';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { FormBuilder } from '@angular/forms';
import { Params, Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class FlowHelperService {
  static deleteDefineAmd(): void {
    const define = (window as any).define;
    if (typeof define === 'function' && define.amd) {
      delete define.amd;
    }
  }

  static toEditWorkflow(router: Router, queryParams: Params): void {
    this.deleteDefineAmd();
    router.navigate([`/home/agent-center/app-flow/flow`], {
      queryParams,
    });
  }

  constructor() {}
  public cleanupAppFlowService(
    appFlowServ: AppFlowService,
    agentDataServ: AgentDataService,
    nodeServ: NodeService,
    fb: FormBuilder,
  ): void {
    appFlowServ.setFlowErrors({
      success: true,
      errors: [],
    });
    appFlowServ.setTokenData({});
    appFlowServ.setNodeIdClicked('');
    agentDataServ.setRollbackId({
      version_id: '',
      isFlowReadonly: false,
    });
    agentDataServ.setPublishStatus('');
    appFlowServ.setRefreshFlag(false);
    nodeServ.cleanIsolatedTestNodesCtx();
    appFlowServ.setResNodes([]);
    appFlowServ.setChildFlowPutBody({});
    appFlowServ.setAnswerInputForm(fb.group({}));
    appFlowServ.setGraph(null);
    appFlowServ.clearModeOfIntents();
    appFlowServ.resetFileList();
    appFlowServ.setAppRefs([]);
    appFlowServ.setContainerDsl(null);
    appFlowServ.setNodeSaveMonitor({});
    appFlowServ.setNodeRefChange({});
    appFlowServ.setNodeAction(null);
    appFlowServ.setNodeModalCloseMonitor(null);
    appFlowServ.setNodeTestInfoAction(null);
  }

  public adjustTopForNodeModal(nodeModalTop: number, renderer: Renderer2) {
    const modal = document.getElementById('flow-common-half-modal');

    if (modal) {
      renderer.setStyle(modal, 'top', `${nodeModalTop}px`);
    }

    const logModel = document.getElementById('flow-log-half-modal');
    if (logModel) {
      renderer.setStyle(logModel, 'top', `${nodeModalTop}px`);
      renderer.setStyle(logModel, 'right', `0px`);
    }

    const checkWorkflowModel = document.getElementById(
      'checkerrorworkflow-half-modal',
    );
    if (checkWorkflowModel) {
      renderer.setStyle(checkWorkflowModel, 'top', `${nodeModalTop}px`);
    }
  }

  observerDomWidth = {};

  observer = new ResizeObserver((entries) => {
    // 遍历变化的元素
    for (const entry of entries) {
      // 打印元素的新尺寸信息
      if (
        entry.contentRect.width > 0 &&
        this.observerDomWidth[entry.target.id] > 0 &&
        entry.target.getBoundingClientRect().width !==
          this.observerDomWidth[entry.target.id]
      ) {
        this.unSetTimeAdjustRightForNodeModal('', 'left');
      }
    }
  });

  hafModalSetTime = null;

  public unSetTimeAdjustRightForNodeModal(addmodalID, position) {
    // 监听dom
    const divElement = document.getElementById('app-flow-container');
    if (!divElement) {
      return;
    }
    this.observer.observe(divElement);
    const divElementRect =
      divElement?.getBoundingClientRect().width || window.innerWidth;
    let right = window.innerWidth - divElementRect;
    this.observerDomWidth[divElement.id] = divElementRect;

    // 并排弹窗list
    const allWindowIds = [
      'flow-common-half-modal',
      'checkerrorworkflow-half-modal',
      'runTestHalfModel',
      'flow-log-half-modal',
    ];
    let hfModalList = [];
    for (let i = 0; i < allWindowIds.length; i++) {
      const idDom = document.getElementById(allWindowIds[i]);
      if (idDom) {
        hfModalList.push(idDom);
      }
    }

    hfModalList = hfModalList.sort((a: any, b: any) => {
      return b.getBoundingClientRect().right - a.getBoundingClientRect().right;
    });

    if (hfModalList.length <= 0) {
      return;
    }

    let startZindex = 880;

    if (position === 'left') {
      for (let i = 0; i < hfModalList.length; i++) {
        const rect = hfModalList[i].getBoundingClientRect();
        if (
          hfModalList[i].id !== addmodalID &&
          rect.width > 0 &&
          rect.height > 0
        ) {
          hfModalList[i]?.style?.setProperty(
            'right',
            `${right}px`,
            'important',
          );
          hfModalList[i]?.style?.setProperty(
            'z-index',
            `${startZindex}`,
            'important',
          );
          startZindex += 1;
          right = right + rect?.width + 1;
          this.observer.observe(hfModalList[i]);
          this.observerDomWidth[hfModalList[i].id] = rect?.width;
        } else if (rect.width <= 0 || rect.height <= 0) {
          hfModalList[i]?.style?.setProperty('right', `0px`, 'important');
        }
      }
      const modal = document.getElementById(addmodalID);
      if (modal) {
        modal.style.animation = 'none';
        modal.style.setProperty('right', `${right}px`, 'important');
        modal.style?.setProperty('z-index', `${startZindex}`, 'important');
        startZindex += 1;
        this.observer.observe(modal);
        this.observerDomWidth[modal.id] = modal?.getBoundingClientRect().width;
      }
    } else if (position === 'right') {
      const modal = document.getElementById(addmodalID);
      if (modal) {
        modal.style.animation = 'none';
        modal?.style?.setProperty('right', `${right}px`, 'important');
        modal.style?.setProperty('z-index', `${startZindex}`, 'important');
        startZindex += 1;
        right = modal.getBoundingClientRect().width + 1 + right;
        this.observer.observe(modal);
        this.observerDomWidth[modal.id] = modal?.getBoundingClientRect().width;
      }
      for (let i = 0; i < hfModalList.length; i++) {
        const rect = hfModalList[i]?.getBoundingClientRect();
        if (
          hfModalList[i].id !== addmodalID &&
          rect.width > 0 &&
          rect.height > 0
        ) {
          hfModalList[i]?.style?.setProperty(
            'right',
            `${right}px`,
            'important',
          );
          hfModalList[i]?.style?.setProperty(
            'z-index',
            `${startZindex}`,
            'important',
          );
          startZindex += 1;
          right = right + rect?.width + 1;
          this.observer.observe(hfModalList[i]);
          this.observerDomWidth[hfModalList[i].id] = rect?.width;
        } else if (rect.width <= 0 || rect.height <= 0) {
          hfModalList[i]?.style?.setProperty('right', `0px`, 'important');
        }
      }
    }
  }

  public adjustRightForNodeModal(addmodalID, position) {
    this.observer.disconnect();
    if (this.hafModalSetTime) {
      clearTimeout(this.hafModalSetTime);
      this.hafModalSetTime = null;
    }
    this.hafModalSetTime = setTimeout(() => {
      this.unSetTimeAdjustRightForNodeModal(addmodalID, position);
    }, 260);
  }

  public useDataPaintWorkflow(
    flow: IWorkflow,
    graph: Graph,
    addNew = false,
    portColor = FLOW_COLORS.connected,
    env = 'workflow',
  ): void {
    const { nodes, edges, layouts, comments } = flow.workflow_details || {};
    const nodeInfo = FlowUtils.processFetchedNodes(nodes, layouts, env);
    const edgeInfo = FlowUtils.processFetchedEdgeData(edges);
    const commentInfo = FlowUtils.processFetchedComments(
      comments,
      layouts,
      env,
    );
    this.initPresetTmpl(
      [...nodeInfo, ...edgeInfo, ...commentInfo],
      graph,
      addNew,
    );

    // 更新连接port的颜色
    const graphEdges = graph.getEdges();
    graphEdges.forEach((edge) => {
      FlowUtils.updateEdgePortColor(graph, edge as IEdgeType, portColor);
    });
  }

  /** 根据节点和边的信息 渲染画布数据 */
  public initPresetTmpl(
    data: CellMetadata[],
    graph: Graph,
    addNew = false,
  ): void {
    const cells: Cell[] = [];
    data.forEach((item) => {
      if (['op-start-node', 'op-end-node'].includes(item.shape)) {
        const node = graph.createNode(FlowUtils.getStartEndNode(item as any));
        cells.push(node);
      } else if (item.shape !== 'dag-edge') {
        const node = graph.createNode(FlowUtils.initTemplateNode(item as any));
        cells.push(node);
      } else {
        const edge = graph.createEdge(item);
        cells.push(edge);
      }
    });
    if (!addNew) {
      graph.resetCells(cells);
    } else {
      graph.addCell(cells);
    }
  }

  public setMiniMap(minimapContainer: HTMLElement, graph: Graph, previewMiniMap?: MiniMap): MiniMap {
    const exist = graph.getPlugin('minimap') as any;
    if (exist) {
      // 主图内容变化后（如大图异步布局完成），ratio 可能仍为空图时代的旧值，
      // 需重算 updatePaper（更新 ratio）再刷新视口框，否则蓝色框按 1:1 主画布尺寸溢出缩略图
      exist.updatePaper(graph.options.width, graph.options.height);
      exist.updateViewport();
      return previewMiniMap;
    }

    previewMiniMap?.dispose();
    const miniMap = new MiniMap({
      container: minimapContainer,
      width: 180,
      height: 108,
      padding: 8,
      scalable: false,
    });

    graph.use(miniMap);
    return miniMap;
  }

  /** 根据浏览器视口大小，自适应缩放工作流 */
  public flowZoomToFit(graph: Graph): void {
    graph?.zoomToFit({
      padding: {
        left: 40,
        top: 40,
        right: 20,
        bottom: 20,
      },
      maxScale: 1,
    });
  }

  public handleMultiPortNodeExpand(
    node: Node<NodeProperties>,
    nodeUpdate: INodeHeightUpdate,
  ): void {
    if (node) {
      if (nodeUpdate.nodeType === 'Branch') {
        this.branchNodePortChangeHandler(node, nodeUpdate);
      }

      if (nodeUpdate.nodeType === 'IntentDetection') {
        this.intentNodePortChangeHandler(node, nodeUpdate);
      } else if (nodeUpdate.nodeType === 'ComplexIntentDetection') {
        FlowUtils.advancedIntentNodePortHandler(node, nodeUpdate);
      }
    }
  }

  public initLoop(loopNodesIds: string[], graph: Graph): void {
    if (loopNodesIds.length) {
      loopNodesIds.forEach((loopId) => {
        const node = graph.getCellById(loopId) as Node<NodeProperties>;
        const nodeData = FlowUtils.getNodeDSLFromRaw(node);
        const childIds = (nodeData as ILoopNode).configs?.loop_body;
        if (childIds?.length) {
          childIds.forEach((id) => {
            const childNode = graph.getCellById(id) as Node<NodeProperties>;
            if (!childNode) {
              return;
            }
            const connectedEdges = graph.getConnectedEdges(childNode);
            connectedEdges.forEach((edge) => {
              if (!edge.getZIndex()) {
                edge.setZIndex(node.getZIndex());
              }
            });

            node.addChild(childNode);
          });
        }

        const loopInput = graph.getCellById(`${loopId}_input`);
        const loopOutput = graph.getCellById(`${loopId}_output`);
        node.addChild(loopInput);
        node.addChild(loopOutput);
      });
    }
  }

  public intentNodePortChangeHandler(
    node: Node<NodeProperties>,
    nodeUpdate: INodeHeightUpdate,
  ): void {
    let topOffset = 72;
    const step = 50;
    const tipsHeight = 24;
    const unExpTop = 14;

    if (nodeUpdate.hasTips) {
      topOffset += tipsHeight;
    }

    const updateIds =
      (FlowUtils.getNodeDSLFromRaw(node) as IIntentNode)?.branches?.map(
        (branch: any) => branch.id,
      ) ?? [];

    const currentIds = node
      .getPorts()
      .filter((p) => p.group !== 'left')
      .map((p) => p.id) as string[];

    for (let i = 0; i < updateIds.length; ++i) {
      if (!currentIds.includes(updateIds[i])) {
        const insertIndex = FlowUtils.getBranchPortIndex(updateIds[i]);
        node.insertPort(insertIndex, {
          id: updateIds[i],
          group: nodeUpdate.isExpand ? 'ab' : 'right',
          attrs: {
            circle: {
              fill: FLOW_COLORS.defaultPort,
              [PORT_CONNECTED_ATTR]: PORT_CONNECTED.defaultPort,
            },
          },
        });
      }
    }

    currentIds.forEach((branchId) => {
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
            group: 'ab',
            args: {
              x: '100%',
              y: topOffset + i * step,
            },
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
        if (nodeUpdate.hasTips) {
          node.portProp(
            p.id,
            {
              group: 'ab',
              args: {
                x: '100%',
                y: tipsHeight + unExpTop + i * 23,
              },
              attrs: {
                text: {
                  fontSize: 12,
                  text: FlowUtils.getIntentBranchPortText(p.id),
                  fill: '#666',
                },
              },
            },
            { ignoreHistory: true },
          );
        } else {
          node.portProp(
            p.id,
            {
              group: 'right',
              args: null,
              attrs: {
                text: {
                  fontSize: 12,
                  text: FlowUtils.getIntentBranchPortText(p.id),
                  fill: '#666',
                },
              },
            },
            { ignoreHistory: true },
          );
        }
      });
    }
  }

  public branchNodePortChangeHandler(
    node: Node<NodeProperties>,
    nodeUpdate: INodeHeightUpdate,
  ): void {
    let topOffset = 51;
    const tipsHeight = 24;
    const unExpTop = 14;
    const singleLineHeight = 18;
    const lineGap = 12;
    const baseBlockHeight = 42;
    const isExpand = nodeUpdate.isExpand;

    if (nodeUpdate.hasTips) {
      topOffset += tipsHeight;
    }

    const branchArr = BRANCH_ARRAY;
    const nodeInfo = node.getData()?.ngArguments?.nodeInfo as IBranchNode;
    const updateIds = nodeInfo?.branches?.map((branch: any) => branch.id) ?? [];

    branchArr.forEach((branchId) => {
      const currentIds = node.getPorts().map((p) => p.id) as string[];

      // insert
      if (updateIds.includes(branchId) && !currentIds.includes(branchId)) {
        const insertIndex = currentIds.length - 1;
        node.insertPort(insertIndex, {
          id: branchId,
          group: isExpand ? 'ab' : 'right',
          attrs: {
            circle: {
              fill: FLOW_COLORS.defaultPort,
              [PORT_CONNECTED_ATTR]: PORT_CONNECTED.defaultPort,
            },
          },
        });
      }

      // remove
      if (!updateIds.includes(branchId) && currentIds.includes(branchId)) {
        node.removePort(branchId);
      }
    });

    const ports = node.getPorts().filter((p) => p.group !== 'left');
    if (nodeUpdate.isExpand) {
      let preH = topOffset;
      for (let i = 0; i < ports.length; ++i) {
        const br = nodeInfo?.branches?.find(
          (branch) => branch.id === ports[i].id,
        );
        const conNum = br?.configs?.conditions?.length ?? 0;
        const gapH = conNum === 0 ? 0 : 8;
        const lineBlockH =
          conNum === 0 ? 0 : conNum * singleLineHeight + (conNum - 1) * lineGap;
        const selfHeight = baseBlockHeight + lineBlockH + gapH;

        node.portProp(
          ports[i].id,
          {
            group: 'ab',
            args: {
              x: '100%',
              y: preH + selfHeight / 2,
            },
          },
          { ignoreHistory: true },
        );

        preH += selfHeight + 8;
      }
    } else {
      ports.forEach((p, i) => {
        if (nodeUpdate.hasTips) {
          node.portProp(
            p.id,
            {
              group: 'ab',
              args: {
                x: '100%',
                y: tipsHeight + unExpTop + i * 23,
              },
            },
            { ignoreHistory: true },
          );
        } else {
          node.portProp(
            p.id,
            {
              group: 'right',
            },
            { ignoreHistory: true },
          );
        }
      });
    }
  }

  public isHeightNormal(val: INodeHeightUpdate, localScale: string): boolean {
    if (!val?.height) {
      return false;
    }

    const scale = Number(localScale) / 100;
    const minHeight = NODE_SIZE.height * scale - NODE_HEIGHT_OFFSET;
    return val?.height >= minHeight;
  }
}
