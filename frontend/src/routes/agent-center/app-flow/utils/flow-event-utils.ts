import { FlowComponent } from '@routes/agent-center/app-flow/flow/flow.component';
import {
  IConnection,
  IEdgeType,
  Position,
} from '@routes/agent-center/app-flow/app-flow.types';
import {
  ADD_NODES_MODAL_HEIGHT,
  ADD_NODES_MODAL_HEIGHT_TASK,
  ADD_NODES_MODAL_WIDTH,
  FLOW_COLORS,
  HOVER_TOOLS_NAME,
  PORT_HOVER_NODE_RADIUS,
  PORT_HOVER_PORT_RADIUS,
  PORT_RADIUS,
} from '@routes/agent-center/app-flow/flow.const';
import { Edge, EdgeView, Rectangle, Node, Graph, Util, Cell } from '@antv/x6';
import { ILoopNode, NodeInfo } from '@routes/agent-center/app-flow/node.type';
import {
  FlowUtils,
  HoverPorkMarkup,
} from '@routes/agent-center/app-flow/utils/flow-utils';
import { CommonUtils } from 'src/utils/common.util';
import { DagreLayout } from '@antv/layout';
import { shouldInvalidatePendingOpen, shouldSkipScheduleForOpenNode } from './pending-open-node.util';

export const FlowEventUtils = {
  addGraphEventListeners(flowComponent: FlowComponent) {
    let ctrlPressed = false;
    let dragRemoveEdge = null;
    let nodeClick = false;
    // 最近一次“开始防抖周期”所点击的节点 id。仅在 nodeClick 防抖窗口内有效，
    // 用于判断快速二次点击是否切换到了不同节点；切换到不同节点时需令此前为
    // 旧节点排队的延迟打开任务失效，并为最新节点重新排队打开。同节点连击
    // 不失效、不重新排队，保留“单击当前节点 250ms 后打开”的正常行为。
    let lastClickedNodeId: string | undefined;
    // nodeClick 防抖窗口的 timer 句柄。每次“会进入调度”的有效点击（首次点击
    // 或切换到不同节点）都重置该 timer，使快速连击期间 lastClickedNodeId 始终
    // 指向最新点击节点；同节点连击直接 return 不重置。窗口结束后清空状态，
    // 使下一次点击被视为首次点击。
    let nodeClickTimer: ReturnType<typeof setTimeout> | null = null;

    // 重置 node:click 防抖窗口的局部状态：清掉待触发的 timer 句柄并把
    // nodeClick / lastClickedNodeId 复位为“未进入防抖”，使下一次 node:click 被视为
    // 首次点击。timer 回调本身只复位这三个闭包局部变量、不触碰 graph/DOM，故组件
    // 销毁后即便有未触发的 300ms timer 残留，回调执行也是无害的；本函数同时作为
    // addGraphEventListeners 的返回值，供组件 ngOnDestroy 显式清理，避免销毁时
    // 残留 timer。edge:click / blank:click 也会调用它，使 A→edge/blank→A 中最新
    // A 不被“同节点连击”规则误判跳过（旧 A 调度已被失效，最新 A 需重新排队）。
    const resetNodeClickDebounce = () => {
      if (nodeClickTimer) {
        clearTimeout(nodeClickTimer);
        nodeClickTimer = null;
      }
      nodeClick = false;
      lastClickedNodeId = undefined;
    };

    flowComponent.graph.on('render:done', (data: any) => {
      // 画布渲染完成，重新设置连接桩样式
      this.resetNodePort(flowComponent.graph);
      //重新设置loop节点大小
      flowComponent.graph.getNodes().forEach((node) => {
        const nodeType = (node.data.ngArguments.nodeInfo as NodeInfo).type;
        // 排除循环输入和输出
        if (nodeType === 'Loop') {
          this.resetParentSize(node);
        }
      });
    });

    flowComponent.graph.on('node:click', (data: any) => {
      if (data?.e?.shiftKey) {
        //按住shift多选节点，不需要展开侧边栏
        return;
      }
      flowComponent.bringEdgeBack();
      const hasAaAncestor = data?.e?.target?.closest('.node-oprs') !== null
      const className: string =
        typeof data?.e?.target?.className === 'string'
          ? data.e.target.className
          : '';
      if (flowComponent.isClickOpAction(className) || hasAaAncestor) {
        return;
      }

      if (data?.e?.target.nodeName === 'circle') {
        //点击连接桩不打开侧边栏
        return;
      }
      const clickedNodeId = data?.node?.id;
      const clickedNode = data?.node;
      // 防抖窗口（nodeClick===true）内的二次点击：
      // - 切换到不同节点：令旧节点延迟打开失效，并继续向下为新节点重新排队
      //   打开（不直接 return），避免 A→B→A 时旧 A 被取消后 B / 最新 A 都
      //   不打开。A→B→A 最终只打开最新 A，不打开旧 A / B。
      // - 同节点连击：保留首次点击已排队的延迟打开，直接 return，避免反复
      //   刷新 250ms 计时导致单击后迟迟打不开。是否失效的判定抽出为纯函数
      //   以便单测（见 pending-open-node.util）。
      if (nodeClick) {
        if (
          shouldInvalidatePendingOpen({
            isDebouncing: nodeClick,
            clickedNodeId,
            lastClickedNodeId,
          })
        ) {
          flowComponent.invalidatePendingOpenNode();
        }
        if (clickedNodeId === lastClickedNodeId) {
          // 同节点连击：不重新排队，保留旧调度的 250ms 延迟打开。
          return;
        }
        // 切换到不同节点：继续向下为新节点重新排队打开。
      }

      // 首次点击 或 切换到不同节点：进入/刷新 300ms 防抖窗口，记录最新点击
      // 节点。重置 timer 使快速连击期间 lastClickedNodeId 始终指向最新节点。
      if (nodeClickTimer) {
        clearTimeout(nodeClickTimer);
      }
      nodeClick = true;
      lastClickedNodeId = clickedNodeId;
      nodeClickTimer = setTimeout(() => {
        resetNodeClickDebounce();
      }, 300);

      if (clickedNode) {
        flowComponent.bringNodeToFront(flowComponent.graph, clickedNode);
      }
      // 只有当前节点配置抽屉确实仍打开且当前节点仍是该已打开节点时才允许跳过；
      // 抽屉已被 closeNodeConfigDrawer 关闭 / 正在切换时（showNodeConfigDrawer
      // 同步置 false，但 halfModalNodeId 可能要等 afterClose 才清空）不应跳过，
      // 否则快速 A→B→A 时最新 A 会被旧 halfModalNodeId 误判跳过，最终无节点打开。
      // 判定抽出为纯函数以便单测（见 pending-open-node.util）。
      if (
        shouldSkipScheduleForOpenNode({
          clickedNodeId,
          halfModalNodeId: flowComponent.halfModalNodeId,
          showNodeConfigDrawer: flowComponent.showNodeConfigDrawer,
        })
      ) {
        return;
      }
      const nodeInfo = FlowUtils.getNodeDSLFromRaw(data?.node);
      if (nodeInfo) {
        flowComponent.closeNodeConfigDrawer()
        // 通过令牌化的延迟调度打开配置面板：切换节点/空白点击/删除节点/销毁
        // 都会令此前的待打开任务失效，避免删除后仍打开已删除节点。
        flowComponent.scheduleOpenNodeModal(nodeInfo);
      }
    });

    flowComponent.graph.on('node:move', ({node, e}) => {
      if (!node.getParent()) {
        flowComponent.bringNodeToFront(flowComponent.graph, node);
      }
      if (e?.ctrlKey) {
        //按住ctrl，可以拖出循环节点
        return;
      }
    });

    flowComponent.graph.on('node:moved', (e: any) => {
      if (flowComponent.isPrevEventEmbedded) {
        flowComponent.isPrevEventEmbedded = false;
        return;
      }

      flowComponent.updateFlowData({
        isDrag: true,
      });
    });

    flowComponent.graph.on('translate', () => {
      flowComponent.addTipContent.show = false;
    });

    flowComponent.graph.on('edge:mousedown', ({edge, view}) => {
      flowComponent.draggingEdge = true;
      if ((flowComponent.currentInActionEdge as any)?.target.cell) {
        return;
      }
      flowComponent.currentInActionEdge?.remove();
    });

    flowComponent.graph.on('edge:mouseup', ({edge, view}) => {
      flowComponent.draggingEdge = false;
      flowComponent.addTipContent.show = false;
      const {x, y} = (edge?.target as Position) || {};
      const sourcePort = (edge?.source as any)?.port;
      const sourceCellId = (edge?.source as any)?.cell;
      const sourceCell = flowComponent.graph.getCellById(sourceCellId);
      if (sourcePort?.endsWith('-4') && !sourcePort?.startsWith('elseIf')) {
        //起点为左边port
        edge.remove({ignoreHistory: true});
        return;
      }
      if (
        sourceCell?.data?.ngArguments?.nodeInfo?.type ===
        'ComplexIntentDetection' &&
        x !== undefined
      ) {
        edge.remove({ignoreHistory: true});
        return;
      }
      const {width, height} = edge.getBBox();
      let isClickPort = width < 10 && height < 10; // 是否点击连接桩

      if (x === undefined || y === undefined) {
        return;
      }
      if (!isClickPort) {
        //判断是否是连接到节点
        const frontNode = this.getTopNodeAtPoint(flowComponent.graph, x, y);
        const sourceId = (edge?.source as any)?.cell;
        // 禁止节点连接到自己
        if (sourceId === frontNode?.id) {
          edge?.remove({ignoreHistory: true});
          return;
        }
        // 注释节点不能连接
        if (frontNode?.data?.ngArguments?.nodeInfo?.type === 'Comment') {
          edge?.remove({ignoreHistory: true});
          return;
        }

        const parentNode = flowComponent.graph
          .getCellById(sourceId)
          .getParent();
        if (frontNode) {
          const frontParentNode = flowComponent.graph
            .getCellById(frontNode?.id)
            .getParent();
          if (
            parentNode?.id !== frontParentNode?.id &&
            parentNode?.id !== frontNode?.id
          ) {
            edge?.remove({ignoreHistory: true});
            return;
          }
          if (parentNode && dragRemoveEdge === edge.id) {
            //循环节点拖拽到空白
            dragRemoveEdge = null;
            edge.remove();
            flowComponent.updateRef();
            flowComponent.updateFlowData({
              isDrag: false,
              successCb: () => {
                flowComponent.graph.trigger('blank:click');
              },
            });
            return;
          }
        } else {
          if (dragRemoveEdge === edge.id) {
            dragRemoveEdge = null;
            edge.remove();
            flowComponent.updateRef();
            flowComponent.updateFlowData({
              isDrag: false,
              successCb: () => {
                flowComponent.graph.trigger('blank:click');
              },
            });
            return;
          }
        }
        if (frontNode && frontNode.id !== parentNode?.id) {
          //开始节点return
          const frontNodeInfo = frontNode.data?.ngArguments
            ?.nodeInfo as NodeInfo;
          if (frontNodeInfo && frontNodeInfo.type === 'Start') {
            edge?.remove({ignoreHistory: true});
            return;
          }
          //循环节点内部判断是否是父节点
          const frontNodePorts = frontNode.getPorts();
          const leftPort = frontNodePorts.find((port) => port.group === 'left');
          if (leftPort) {
            //存在连线
            const exist = flowComponent.appFlowServ.judgeLinkedEdgeByPort(
              flowComponent.graph,
              sourceCellId,
              frontNode.id,
              sourcePort
            );
            if (exist) {
              edge?.remove({ignoreHistory: true});
              return;
            }
            edge.setTarget({
              cell: frontNode.id,
              port: leftPort.id,
            });
            edge.toFront({ignoreHistory: true});
            flowComponent.updateRef();
            flowComponent.updateFlowData({
              isDrag: false,
              successCb: () => {
                flowComponent.graph.trigger('blank:click');
              },
            });
          }
          return;
        }
      } else {
        edge.removeTools({ignoreHistory: true});
        edge.prop('shape', 'temp-edge', {
          ignoreHistory: true,
        });
        edge.attr(
          {
            line: {
              stroke: 'opacity',
              strokeWidth: 1,
              targetMarker: {
                name: 'diamond',
                width: 1,
                height: 1,
              },
            },
          },
          {
            ignoreHistory: true,
          },
        );
      }
      edge?.toFront();
      const e = flowComponent.graph.localToClient(x, y);
      const panelWidth = ADD_NODES_MODAL_WIDTH;
      //需要根据当前显示的节点数量计算高度，待优化
      const panelHeight =
        flowComponent.workflow_type === 'chat'
          ? ADD_NODES_MODAL_HEIGHT
          : ADD_NODES_MODAL_HEIGHT_TASK;
      const padding = 16;

      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const clickX = e.x;
      const clickY = e.y;

      let left = clickX + padding;
      let top = clickY;

      if (left + panelWidth > viewportWidth) {
        left = clickX - panelWidth - padding;
      }

      if (top + panelHeight > viewportHeight) {
        top = viewportHeight - panelHeight - padding - 75;
      }

      if (top < padding) {
        top = padding;
      }

      setTimeout(() => {
        const existEdge = flowComponent.graph.getCellById(edge.id);
        if (existEdge) {
          flowComponent.addPanelPos.left = left;
          flowComponent.addPanelPos.top = top;

          flowComponent.showAddPanel = true;

          flowComponent.cdr.detectChanges();

          edge.toFront();
          flowComponent.currentInActionEdge = edge;
          flowComponent.currentInActionEdgeView = view as EdgeView;
        }
      });
    });

    flowComponent.graph.on('edge:removed', ({edge}) => {
      flowComponent.showAddPanel = false;

      if (
        !(edge?.target as IConnection)?.cell ||
        !(edge?.source as IConnection)?.cell
      ) {
        return;
      }

      FlowUtils.updateEdgePortColor(
        flowComponent.graph,
        edge as IEdgeType,
        FLOW_COLORS.defaultPort,
      );
    });
    flowComponent.graph.on(
      'edge:connected',
      ({
         edge,
         isNew,
         previousCell,
         previousPort,
         currentCell,
         currentPort,
       }) => {
        dragRemoveEdge = null;
        if (isNew) {
          flowComponent.onEdgeConnected(edge);
          flowComponent.updateRef();
          flowComponent.updateFlowData({
            isDrag: false,
            successCb: () => {
              flowComponent.graph.trigger('blank:click');
            },
          });
        } else {
          if (!currentPort) {
            dragRemoveEdge = edge.id;
          } else {
            flowComponent.updateFlowData({
              isDrag: false,
              successCb: () => {
                flowComponent.graph.trigger('blank:click');
              },
            });
          }
        }
      },
    );

    flowComponent.graph.on('edge:mouseenter', ({edge}) => {
      const targetCell = (edge.target as any)?.cell;
      // 若满足if判断，表示这是连接容器和高级意图的边，不能被删除
      if (targetCell?.includes('intent_container')) {
        edge.removeTools({
          ignoreHistory: true,
        });
      }
    });

    flowComponent.graph.on('translate', () => {
      flowComponent.hiddenAddNodePanel();
      flowComponent.debounceSetMiniMap();
    });

    flowComponent.graph.on('resize', () => {
      flowComponent.hiddenAddNodePanel();
      flowComponent.debounceSetMiniMap();
    });

    flowComponent.graph.on('scale', (e: any) => {
      flowComponent.hiddenAddNodePanel();

      if (e?.sx) {
        flowComponent.localScale = (
          (e.sx as number) * flowComponent.defaultScale
        ).toFixed(0);
        flowComponent.appFlowServ.setLocalScale(
          (e.sx as number) * flowComponent.defaultScale,
        );
      }

      flowComponent.debounceSetMiniMap();
    });

    flowComponent.graph.on('node:mouseenter', ({node, view}) => {
      if (
        flowComponent.isFlowReadonly ||
        flowComponent.notUserSelf ||
        flowComponent.type === 'multi'
      ) {
        return;
      }
      const nodePorts = node.getPorts();
      nodePorts.forEach((port) => {
        const r = node.getPortProp(port.id, 'attrs/circle/r');
        node.setPortProp(port.id, 'attrs/circle/fill', FLOW_COLORS.hoverPort, {
          ignoreHistory: true,
        });
        if (r === PORT_RADIUS) {
          node.setPortProp(port.id, 'attrs/circle/r', PORT_HOVER_NODE_RADIUS, {
            ignoreHistory: true,
          });
        }
      });
    });

    flowComponent.graph.on('node:mouseleave', ({node, view}) => {
      if (
        flowComponent.isFlowReadonly ||
        flowComponent.notUserSelf ||
        flowComponent.type === 'multi'
      ) {
        return;
      }
      const nodePorts = node.getPorts();
      nodePorts.forEach((port) => {
        if (!this.hasPortEdges(flowComponent.graph, node, port.id)) {
          node.setPortProp(
            port.id,
            'attrs/circle/fill',
            FLOW_COLORS.defaultPort,
            {
              ignoreHistory: true,
            },
          );
        }
        node.setPortProp(port.id, 'attrs/circle/r', PORT_RADIUS, {
          ignoreHistory: true,
        });
        node.setPortProp(port.id, 'markup', null, {
          ignoreHistory: true,
        });
      });
    });

    flowComponent.graph.on(
      'node:port:mouseenter',
      ({node, view, e, port}) => {
        if (
          flowComponent.isFlowReadonly ||
          flowComponent.notUserSelf ||
          flowComponent.type === 'multi'
        ) {
          return;
        }
        const target = e.target;
        if (!(port?.endsWith('-4') && !port?.startsWith('elseIf'))) {
          setTimeout(() => {
            if (target.getBoundingClientRect().width > 0) {
              const flowRect =
                flowComponent.nativeElementRef.getBoundingClientRect();
              let lang = CommonUtils.getLanguage();
              let xWidth = lang === 'zh-cn' ? 46 : 88;
              flowComponent.addTipContent.show = true;
              flowComponent.addTipContent.left =
                target.getBoundingClientRect().x +
                target.getBoundingClientRect().width / 2 -
                xWidth;
              flowComponent.addTipContent.top =
                target.getBoundingClientRect().y - 68 - flowRect.y;
            }
          }, 50);
        }
        const prop = node.getPortProp(port);
        if (prop.group !== 'left') {
          node.setPortProp(port, 'attrs/circle/fill', FLOW_COLORS.hoverPort, {
            ignoreHistory: true,
          });
          node.setPortProp(port, 'attrs/circle/r', PORT_HOVER_PORT_RADIUS, {
            ignoreHistory: true,
          });
          node.setPortProp(port, 'markup', HoverPorkMarkup, {
            ignoreHistory: true,
          });
        }
      },
    );

    flowComponent.graph.on(
      'node:port:mouseleave',
      ({node, view, e, port}) => {
        if (
          flowComponent.isFlowReadonly ||
          flowComponent.notUserSelf ||
          flowComponent.type === 'multi'
        ) {
          return;
        }
        flowComponent.addTipContent.show = false;
        // 获取鼠标的全局坐标
        const {clientX, clientY} = e;

        // 将坐标转换为画布坐标
        const point = flowComponent.graph.clientToLocal(clientX, clientY);

        // 获取该位置的所有节点
        const cellsAtPoint = flowComponent.graph.getNodesFromPoint(point);
        //是否还在节点内
        const isInNode = cellsAtPoint.some((c) => c.id === node.id);
        const prop = node.getPortProp(port);
        if (prop.group !== 'left') {
          if (isInNode) {
            node.setPortProp(port, 'attrs/circle/fill', FLOW_COLORS.hoverPort, {
              ignoreHistory: true,
            });
            node.setPortProp(port, 'attrs/circle/r', PORT_HOVER_NODE_RADIUS, {
              ignoreHistory: true,
            });
            node.setPortProp(port, 'markup', null, {
              ignoreHistory: true,
            });
          } else {
            if (!this.hasPortEdges(flowComponent.graph, node, port)) {
              node.setPortProp(
                port,
                'attrs/circle/fill',
                FLOW_COLORS.defaultPort,
                {ignoreHistory: true},
              );
            }
            node.setPortProp(port, 'attrs/circle/r', PORT_RADIUS, {
              ignoreHistory: true,
            });
            node.setPortProp(port, 'markup', null, {
              ignoreHistory: true,
            });
          }
        }
      },
    );

    flowComponent.graph.on('cell:mouseenter', ({cell, view}) => {
      if (
        flowComponent.isFlowReadonly ||
        flowComponent.notUserSelf ||
        flowComponent.type === 'multi'
      ) {
        return;
      }
      if (flowComponent.showAddPanel) {
        return;
      }
      this.setEdgeDefault(flowComponent, cell.id);
      if (cell.shape === 'edge' || cell.shape === 'dag-edge') {
        const that = flowComponent;
        const _this = this;
        if (!view.hasTools(HOVER_TOOLS_NAME)) {
          view.addTools({
            name: HOVER_TOOLS_NAME,
            items: [
              {
                name: 'button',
                args: {
                  distance: '50%',
                  markup: [
                    {
                      tagName: 'circle',
                      selector: 'button',
                      attrs: {
                        r: 10,
                        fill: '#1890ff',
                        stroke: '#fff',
                        strokeWidth: 2,
                        cursor: 'pointer',
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
                  ],
                  onClick({e}) {
                    const {top, left} = _this.setPanelPosition(that.workflow_type, e.clientX, e.clientY);
                    that.addPanelPos.left = left;
                    that.addPanelPos.top = top;

                    that.showAddPanel = true;

                    that.cdr.detectChanges();
                  },
                },
              },
              {
                name: 'target-arrowhead',
                args: {
                  tagName: 'circle',
                  attrs: {
                    r: 20,
                    fill: 'transparent',
                    stroke: 'none',
                    cursor: 'move',
                  },
                },
              },
            ]
          });
        }

        cell.toFront({
          ignoreHistory: true,
        });

        cell.setAttrs(
          {
            line: {
              stroke: FLOW_COLORS.edgeActive,
            },
          },
          {
            ignoreHistory: true,
          },
        );

        flowComponent.currentInActionEdge = cell;
        flowComponent.currentInActionEdgeView = view as EdgeView;

        flowComponent.hoverEdges.push(cell.id);
      }
    });

    flowComponent.graph.on('cell:mouseleave', (data: any) => {
      const cell = data.cell as Edge;
      if (cell.shape === 'edge' || cell.shape === 'dag-edge') {
        this.setEdgeDefault(flowComponent);
      }
    });

    flowComponent.graph.on('edge:click', ({cell}) => {
      if (flowComponent.selectedEdgeId) {
        flowComponent.bringEdgeBack();
      }
      // 点击边也会关闭节点抽屉：令已排队的延迟打开任务失效，避免节点点击
      // 后 250ms 内点边、旧节点面板仍在 250ms 后弹出。同时重置 node:click 防抖
      // 窗口的局部状态，使随后的 node:click 被视为首次点击而非“同节点连击”，
      // 否则 A→edge→A 时旧 A 调度已被失效、最新 A 又被同节点 return 跳过，
      // 最终无节点打开。
      flowComponent.invalidatePendingOpenNode();
      resetNodeClickDebounce();
      flowComponent.closeNodeConfigDrawer();
      flowComponent.nodeServ.setCurrSelectedNode('');
      cell.setAttrs(
        {
          line: {
            strokeWidth: 3,
            stroke: FLOW_COLORS.edgeActive,
          },
        },
        {
          ignoreHistory: true,
        },
      );

      cell.toFront({
        ignoreHistory: true,
      });
      const targetCell = (cell.getTarget() as any)?.cell;
      if (targetCell?.includes('intent_container')) {
        cell.setAttrs(
          {
            line: {
              strokeWidth: 2,
            },
          },
          {
            ignoreHistory: true,
          },
        );
        return;
      }

      flowComponent.selectedEdgeId = cell.id;
    });

    flowComponent.graph.on('blank:click', () => {
      // 空白点击令待打开节点失效，避免点击空白后仍弹出此前节点的配置面板。
      // 同步重置 node:click 防抖窗口局部状态，使随后 node:click 视为首次点击
      // （A→blank→A 不应因 lastClickedNodeId 仍为 A 而被同节点 return 跳过）。
      flowComponent.invalidatePendingOpenNode();
      resetNodeClickDebounce();
      if (flowComponent.type !== 'multi') {
        flowComponent.closeNodeConfigDrawer();
      }
      flowComponent.bringEdgeBack();
      flowComponent.addTipContent.show = false;
      flowComponent.appFlowServ.removeNotLinkedEdge(flowComponent.graph);
      flowComponent.draggingEdge = false;
      flowComponent.nodeServ.setCurrSelectedNode('');
      this.setEdgeDefault(flowComponent);
    });

    flowComponent.graph.on('blank:dblclick', (e) => {
      if (
        flowComponent.isFlowReadonly ||
        flowComponent.notUserSelf ||
        flowComponent.type === 'multi'
      ) {
        return;
      }
      //触发新增节点弹窗
      const x = e.x;
      const y = e.y;
      if (x && y) {
        const e = flowComponent.graph.localToClient(x, y);

        const {top, left} = this.setPanelPosition(
          flowComponent.workflow_type,
          e.x,
          e.y,
        );

        setTimeout(() => {
          flowComponent.addPanelPos.left = left;
          flowComponent.addPanelPos.top = top;
          flowComponent.addPanelPos.x = e.x;
          flowComponent.addPanelPos.y = e.y;

          flowComponent.showAddPanel = true;

          flowComponent.currentInActionEdge = null;
          flowComponent.currentInActionEdgeView = null as EdgeView;

          flowComponent.cdr.detectChanges();
        });
      }
    });

    flowComponent.graph.on('node:move', () => {
      flowComponent.bringEdgeBack();
    });

    flowComponent.graph.on(
      'node:change:parent',
      ({node, current, previous, options}) => {
        if (options.skipParentHandler) {
          return;
        }

        const previousParent = flowComponent.graph.getCellById(previous);
        const currentParent = flowComponent.graph.getCellById(current);
        setTimeout(() => {
          if (currentParent) {
            this.resetParentSize(currentParent);
          } else if (previousParent) {
            this.resetParentSize(previousParent);
          }
        });

        if (!previousParent) {
          return;
        }
        if (
          !current &&
          (previousParent.data.ngArguments.nodeInfo as NodeInfo).type === 'Loop'
        ) {
          flowComponent.graph.batchUpdate(() => {
            flowComponent.appFlowServ.setLoopInnerRal({
              loopNodeId: previousParent.id,
              childNodeId: node.id,
              action: 'delete',
            });
            const nodeInfo = previousParent.data.ngArguments
              .nodeInfo as ILoopNode;

            nodeInfo.configs.loop_body = nodeInfo.configs.loop_body.filter(
              (childId) => childId !== node.id,
            );
            this.removeNodeRelated(flowComponent.graph, node.id);
          });

          flowComponent.isPrevEventEmbedded = true;
          flowComponent.updateFlowData({isDrag: false});
        }
      },
    );
    /**
     * 重置ctrl按键状态
     */
    flowComponent.graph.on('node:mousedown', () => {
      ctrlPressed = false;
    });

    /**
     *  寻找目标节点过程中触发，赋值ctrl按键状态
     */
    flowComponent.graph.on('node:embedding', ({e, node}) => {
      const nodeType = (node.data.ngArguments.nodeInfo as NodeInfo).type;
      // 排除循环输入和输出
      if (nodeType === 'LoopInput' || nodeType === 'LoopOutput') {
        return;
      }
      ctrlPressed = e.metaKey || e.ctrlKey;
    });

    flowComponent.graph.on(
      'node:embedded',
      ({node, previousParent, currentParent}) => {
        ctrlPressed = false;
        if (
          !previousParent &&
          (currentParent.data.ngArguments.nodeInfo as NodeInfo).type === 'Loop'
        ) {
          flowComponent.appFlowServ.setLoopInnerRal({
            loopNodeId: currentParent.id,
            childNodeId: node.id,
            action: 'add',
          });

          (
            currentParent.data.ngArguments.nodeInfo as ILoopNode
          ).configs.loop_body.push(node.id);
          flowComponent.isPrevEventEmbedded = true;
          flowComponent.updateFlowData({isDrag: false});
        }
      },
    );

    flowComponent.graph.on('node:change:size', ({node, options}) => {
      if (options.skipParentHandler) {
        return;
      }

      const children = node.getChildren();
      if (children && children.length) {
        node.prop('originSize', node.getSize());
      }
    });

    flowComponent.graph.on('node:change:position', ({node, options}) => {
      if (options.skipParentHandler || ctrlPressed) {
        return;
      }
      const children = node.getChildren();
      if (children && children.length) {
        node.prop('originPosition', node.getPosition());
      }

      const parent = node.getParent();
      this.resetParentSize(parent);
    });

    flowComponent.graph.on('selection:changed', () => {
      const selected = flowComponent.graph.getSelectedCells();
      const ids = selected.map((n) => n.id);
      flowComponent.selectionTip.show = ids.length > 1;
      flowComponent.selectionTip.count = ids.length;
      flowComponent.appFlowServ.setNodeIdSelected(ids);
    });

    // 返回防抖状态清理函数，供组件 ngOnDestroy 调用，避免销毁时残留 300ms
    // node:click 防抖 timer。
    return resetNodeClickDebounce;
  },
  //获取连接桩相关连线
  getPortEdges(graph: Graph, node: Node, portId: string): Edge[] {
    const edges = graph.getConnectedEdges(node); // 获取与节点相连的所有边
    return edges.filter((edge) => {
      const source: any = edge.getSource();
      const target: any = edge.getTarget();
      return (
        (source.port === portId && source.cell === node.id) ||
        (target.port === portId && target.cell === node.id)
      );
    });
  },
  hasPortEdges(graph: Graph, node: Node, portId: string): boolean {
    return this.getPortEdges(graph, node, portId).length > 0;
  },
  //获取最上层的节点
  getTopNodeAtPoint(graph: Graph, x: number, y: number) {
    const nodes = graph.getNodesFromPoint(x, y);
    if (nodes.length === 0) return null;

    // 按 z-index 和绘制顺序排序
    const sortedNodes = nodes.sort((a, b) => {
      // 1. 按 z-index 降序（z-index 大的在上层）
      const aZIndex = a.getZIndex() || 0;
      const bZIndex = b.getZIndex() || 0;

      if (aZIndex !== bZIndex) {
        return bZIndex - aZIndex;
      }

      // 2. 如果 z-index 相同，按添加到图中的顺序
      // X6 内部会维护一个渲染顺序，后来添加的在上层
      // 我们可以通过获取所有节点的顺序来判断
      const allNodes = graph.getNodes();
      const aIndex = allNodes.findIndex((n) => n.id === a.id);
      const bIndex = allNodes.findIndex((n) => n.id === b.id);

      return bIndex - aIndex; // 后添加的在上层
    });

    return sortedNodes[0];
  },
  //设置连线为默认样式
  setEdgeDefault(flowComponent, excludeEdgeId?: string) {
    if (flowComponent.draggingEdge) {
      return;
    }
    flowComponent.hoverEdges.forEach((edgeId: string) => {
      const cell = flowComponent.graph.getCellById(edgeId);
      if (!cell) {
        return;
      }
      if (!(cell.shape === 'edge' || cell.shape === 'dag-edge')) {
        return;
      }
      if (
        cell.id !== flowComponent.selectedEdgeId &&
        cell.id !== excludeEdgeId
      ) {
        if (!flowComponent.showAddPanel) {
          const view = flowComponent.graph.findViewByCell(cell);
          cell.removeTools({
            ignoreHistory: true,
          });
          view?.removeTools();
        }
        cell.setAttrs(
          {
            line: {
              stroke: FLOW_COLORS.connected,
            },
          },
          {
            ignoreHistory: true,
          },
        );
        const targetCell = cell.getTargetCell();
        const hasParent = targetCell?.getParent();
        if (targetCell && hasParent) {
          const targetZIndex = targetCell.getZIndex();
          cell.setZIndex(targetZIndex - 1 === 0 ? 1 : targetZIndex - 1, {
            ignoreHistory: true,
          });
        } else {
          cell.setZIndex(0, {
            ignoreHistory: true,
          });
        }
      }
    });
    flowComponent.hoverEdges = [];
  },
  // 重置节点连接桩样式
  resetNodePort(graph: Graph) {
    const nodes = graph.getNodes();
    nodes.forEach((node) => {
      const nodePorts = node.getPorts();
      nodePorts.forEach((port) => {
        if (this.hasPortEdges(graph, node, port.id)) {
          node.setPortProp(
            port.id,
            'attrs/circle/fill',
            FLOW_COLORS.hoverPort,
            {
              ignoreHistory: true,
            },
          );
        }
      });
    });
  },
  // 移除节点的相关连线，移除循环节点场景
  removeNodeRelated(graph: Graph, nodeId: string) {
    // 获取与节点相关的所有边
    const allEdges = graph.getEdges();

    allEdges.forEach((edge) => {
      const source = edge.getSourceCell();
      const target = edge.getTargetCell();
      if (source && target && (source.id === nodeId || target.id === nodeId)) {
        edge.remove();
      }
    });
  },
  // 修改父节点大小
  resetParentSize(parent: Cell) {
    if (parent && parent.isNode()) {
      // 获取或保存原始尺寸和位置
      let originSize = parent.prop('originSize') as {
        width: number;
        height: number;
      };
      if (originSize == null) {
        originSize = parent.getSize();
        parent.prop('originSize', originSize);
      }

      let originPosition = parent.prop('originPosition') as Position;
      if (originPosition == null) {
        originPosition = parent.getPosition();
        parent.prop('originPosition', originPosition);
      }

      let x = originPosition.x + originSize.width / 2;
      let y = originPosition.y + originSize.height / 2;
      let cornerX = originPosition.x + originSize.width / 2;
      let cornerY = originPosition.y + originSize.height / 2;
      let hasChange = false;

      const pChildren = parent.getChildren();
      if (pChildren && pChildren.length > 0) {
        pChildren.forEach((child) => {
          const bbox = child.getBBox();
          this.inflateDirectional(bbox, 90, 20, 20, 20);

          const corner = bbox.getCorner();

          if (bbox?.x < x) {
            x = bbox.x;
            hasChange = true;
          }

          if (bbox?.y < y) {
            y = bbox.y;
            hasChange = true;
          }

          if (corner?.x > cornerX) {
            cornerX = corner.x;
            hasChange = true;
          }

          if (corner?.y > cornerY) {
            cornerY = corner.y;
            hasChange = true;
          }
        });
      }

      if (hasChange) {
        parent?.prop(
          {
            position: {x, y},
            size: {width: cornerX - x, height: cornerY - y},
          },
          {skipParentHandler: true},
        );
      }
    }
  },

  /**
   * 设置节点面板位置
   */
  setPanelPosition(workflowType, clientX, clientY) {
    const panelWidth = ADD_NODES_MODAL_WIDTH;
    //需要根据当前显示的节点数量计算高度，待优化
    const panelHeight =
      workflowType === 'chat'
        ? ADD_NODES_MODAL_HEIGHT
        : ADD_NODES_MODAL_HEIGHT_TASK;
    const padding = 16;

    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = clientX + padding;
    let top = clientY;

    if (left + panelWidth > viewportWidth) {
      left = clientX - panelWidth - padding;
    }

    if (top + panelHeight > viewportHeight) {
      top = viewportHeight - panelHeight - padding - 75;
    }

    if (top < padding) {
      top = padding;
    }

    return {top, left};
  },
  inflateDirectional(
    bbox: Rectangle,
    top = 0,
    right = 0,
    bottom = 0,
    left = 0,
  ) {
    bbox.x -= left;
    bbox.y -= top;
    bbox.width += left + right;
    bbox.height += top + bottom;
  },
  // 获取父节点大小和相对位置
  getParentSize(pChildren: any[]) {
    if (!pChildren || pChildren.length === 0) {
      return null;
    }

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    pChildren.forEach((child) => {
      const bbox: any = {
        x: child.x,
        y: child.y,
        width: child.size.width,
        height: child.size.height,
      };

      // 应用边距
      this.inflateDirectional(bbox, 90, 20, 20, 20);

      // 更新边界
      minX = Math.min(minX, bbox.x);
      minY = Math.min(minY, bbox.y);
      maxX = Math.max(maxX, bbox.x + bbox.width);
      maxY = Math.max(maxY, bbox.y + bbox.height);
    });

    return {
      x: minX,
      y: minY,
      width: maxX - minX,
      height: maxY - minY,
    };
  },
  optimizeDagreLayout(graph: Graph) {
    // Dagre布局
    const data: any = {
      nodes: [],
      edges: [],
    };

    // 构建边数据
    data.edges = graph.getEdges().map((edge) => {
      return {
        source: edge.getSourceCellId(),
        target: edge.getTargetCellId(),
      };
    });

    // 按节点分组，处理群组节点
    const loopNodeMap = {};

    // 第一遍：只收集没有父节点的节点
    graph.getNodes().forEach((node) => {
      const parent = node.getParent();
      if (parent) {
        if (loopNodeMap[parent.id]) {
          loopNodeMap[parent.id].push({
            id: node.id,
            size: {
              width: node.size().width,
              height: node.size().height,
            },
            parentId: parent.id,
          });
        } else {
          loopNodeMap[parent.id] = [
            {
              id: node.id,
              size: {
                width: node.size().width,
                height: node.size().height,
              },
              parentId: parent.id,
            },
          ];
        }
      } else {
        data.nodes.push({
          id: node.id,
          size: {
            width: node.size().width,
            height: node.size().height,
          },
        });
      }
    });

    const dagreLayout = new DagreLayout({
      type: 'dagre',
      rankdir: 'LR',
      nodesep: 20,
      ranksep: 20,
    });

    const normalizeNodePosition = (nodes: typeof data.nodes) => {
      nodes.forEach((node) => {
        node.x -= node.size.width / 2;
        node.y -= node.size.height / 2;
      });
    };

    // 第二遍：处理群组节点的布局和大小计算
    Object.keys(loopNodeMap).forEach((loopId) => {
      const children = loopNodeMap[loopId];
      // 为群组节点构建子节点图
      const model = dagreLayout.layout({
        nodes: children,
        edges: data.edges,
      });
      normalizeNodePosition(model.nodes as any);

      // 计算父节点所需的大小
      const parentRect = this.getParentSize(model.nodes);
      if (parentRect) {
        const loopNode = data.nodes.find((node) => node.id === loopId);
        if (loopNode) {
          loopNode.size = {
            ...parentRect,
          };
          loopNode.x = parentRect.x;
          loopNode.y = parentRect.y;
        }
      }
    });

    // 执行整体布局
    const model = dagreLayout.layout(data);
    normalizeNodePosition(model.nodes as any);

    // 第三遍：应用布局结果，同时处理群组内子节点的位置
    graph.batchUpdate(() => {
      model.nodes.forEach((node: any) => {
        const cell = graph.getCellById(node.id);

        if (cell?.isNode()) {
          // 更新群组/节点位置
          (cell as Node).position(node.x, node.y);

          // 更新群组内子节点的位置
          const children = loopNodeMap[node.id];
          if (children) {
            children.forEach((child) => {
              const dx = child.x - node.size.x;
              const dy = child.y - node.size.y;
              const childCell = graph.getCellById(child.id);
              if (childCell?.isNode()) {
                (childCell as Node).position(node.x + dx, node.y + dy);
              }
            });
          }
        }
      });
    });
  },
};
