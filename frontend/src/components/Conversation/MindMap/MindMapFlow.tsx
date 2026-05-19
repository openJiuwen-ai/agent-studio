import React, { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import { Network, ListTree } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  Panel,
  Node,
  Edge,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import { useConversationStore, MessageType } from '../../../stores/useConversationStore';
import { ThoughtNode, ThoughtEdge, MindMapManager, ThoughtNodeType } from '../../../stores/handlers/deepsearchMindMapHandler';
import { ThoughtGraphType } from '../../../types/conversationTypes';
import {
  NodeData,
  DEFAULT_LAYOUT_OPTIONS,
  NODE_DIMENSIONS,
} from './types';
import { getEdgeLabelI18n } from '../../../utils/deepsearchMindMapUtils';
import {
  OutlineNode,
  SectionNode,
  PlanNode,
  SubReportNode,
  FinalReportNode,
} from './nodes';
import { performSmartLayout, performSimpleLayout, getNodeTypeString } from './layoutUtils';

const nodeTypes = {
  outline: OutlineNode,
  section: SectionNode,
  plan: PlanNode,
  sub_report: SubReportNode,
  final_report: FinalReportNode,
};

interface MindMapFlowComponentProps {
  messageItemsId: string;
  direction?: 'TB' | 'LR';
  className?: string;
  graphType?: 'sectionGraph' | 'taskGraph';
  onGraphTypeChange?: (graphType: 'sectionGraph' | 'taskGraph') => void;
}

const MindMapFlow: React.FC<MindMapFlowComponentProps> = ({
  messageItemsId,
  direction = 'TB',
  className = '',
  graphType: propsGraphType = 'sectionGraph',
  onGraphTypeChange,
}) => {
  const { t } = useTranslation();
  const getMindMapManager = useConversationStore(state => state.getMindMapManager);
  const getMessageById = useConversationStore(state => state.getMessageById);
  const getChildMessages = useConversationStore(state => state.getChildMessages);
  const saveConversationToDB = useConversationStore(state => state.saveConversationToDB);
  const setSelectedResultMessageId = useConversationStore(state => state.setSelectedResultMessageId);

  // 处理报告导航 - 跳转到右侧面板报告页面
  const handleNavigateToReport = useCallback((messageId: string) => {
    setSelectedResultMessageId(messageId);
  }, [setSelectedResultMessageId]);

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [needLayout, setNeedLayout] = useState(false);
  const [graphType, setGraphType] = useState<'sectionGraph' | 'taskGraph'>(propsGraphType);
  const reactFlowRef = useRef<any>(null);
  const fitViewTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const nodesRef = useRef<Node[]>([]); // 用于存储最新的 nodes，避免闭包陷阱
  const { fitView } = useReactFlow(); // 获取 fitView 方法

  // 用于缓存之前的edges数据，避免不必要的更新
  const previousEdgesRef = useRef<string>('');

  // 用于缓存之前的nodes签名，避免不必要的更新
  const previousNodesSignatureRef = useRef<string>('');

  // 边的状态样式定义
  const EDGE_STYLES = useMemo(() => ({
    NOT_STARTED: {
      stroke: '#94a3b8',        // 灰色
      strokeWidth: 1,
      labelColor: '#777777',    // 深灰色文字
      labelBgColor: '#dfdfdf',  // 灰色底
      labelBgOpacity: 0.9,
      strokeDasharray: '5,5',   // 虚线
    },
    STARTED: {
      stroke: '#6236ff',        // 蓝紫色
      strokeWidth: 1,
      labelColor: '#0a59f7',    // 蓝色文字
      labelBgColor: '#e6eeff',  // 浅蓝底
      labelBgOpacity: 1,
      strokeDasharray: '5,5',   // 虚线
    },
  }), []);

  // 缓存边的样式对象，避免重复创建
  const edgeStyleCache = useMemo(() => {
    const cache = new Map<string, any>();

    // 为两种状态创建缓存
    cache.set('NOT_STARTED', {
      stroke: EDGE_STYLES.NOT_STARTED.stroke,
      strokeWidth: EDGE_STYLES.NOT_STARTED.strokeWidth,
      strokeDasharray: '5,5',   // 虚线
    });
    cache.set('STARTED', {
      stroke: EDGE_STYLES.STARTED.stroke,
      strokeWidth: EDGE_STYLES.STARTED.strokeWidth,
      strokeDasharray: '5,5',   // 虚线
    });

    return cache;
  }, [EDGE_STYLES]);

  // 缓存边的data对象
  const edgeDataCache = useMemo(() => {
    const cache = new Map<string, any>();

    // 为不同的边状态和label组合创建缓存
    const createCacheKey = (status: string, label: string | undefined) => {
      return `${status}-${label || ''}`;
    };

    return { cache, createCacheKey };
  }, []);

  // 根据节点状态判断边的状态
  const getEdgeStatus = useCallback((sourceNode: ThoughtNode, targetNode: ThoughtNode): 'NOT_STARTED' | 'STARTED' => {
    // 如果任意一个端点是pending状态，则为未开始
    const sourceMessage = getMessageById(sourceNode.messageId);
    const targetMessage = getMessageById(targetNode.messageId);

    if (sourceMessage?.status === 'pending' || targetMessage?.status === 'pending') {
      return 'NOT_STARTED';
    }

    return 'STARTED';
  }, [getMessageById]);
  
  // 当props中的graphType变化时，更新内部状态
  useEffect(() => {
    setGraphType(propsGraphType);
  }, [propsGraphType]);

  // 统一的 fitView 调用函数（带防抖）
  const triggerFitView = () => {
    // 清除之前的定时器
    if (fitViewTimeoutRef.current) {
      clearTimeout(fitViewTimeoutRef.current);
    }

    // 设置新的定时器（防抖500ms）
    fitViewTimeoutRef.current = setTimeout(() => {
      const currentNodes = nodesRef.current;
      if (currentNodes.length > 0 && typeof fitView === 'function') {
        fitView({ padding: 0.2 });
      }
    }, 500);
  };

  // 清理定时器
  useEffect(() => {
    return () => {
      if (fitViewTimeoutRef.current) {
        clearTimeout(fitViewTimeoutRef.current);
      }
    };
  }, []);

  // 当messageItemsId变化时（切换思维链），强制调用 fitView
  useEffect(() => {
    setTimeout(() => {
      triggerFitView();
    }, 100);
  }, [messageItemsId]);

  // 当内部graphType变化时，通知父组件
  useEffect(() => {
    if (onGraphTypeChange) {
      onGraphTypeChange(graphType);
    }
  }, [graphType, onGraphTypeChange]);

  const thoughtGraphType = graphType === 'sectionGraph'
    ? ThoughtGraphType.SECTION
    : ThoughtGraphType.TASK;

  const graph = useMemo((): MindMapManager | null => {
    return getMindMapManager(messageItemsId, thoughtGraphType) || null;
  }, [messageItemsId, thoughtGraphType, getMindMapManager]);

  // 处理节点拖动结束事件
  const onNodeDragStop = useCallback((_event: React.MouseEvent, node: Node) => {
    if (!graph) return;

    // 保存手动调整的位置到store中，但不持久化到IndexDB
    graph.updateNodePositionManually(node.id, node.position);
  }, [graph]);

  const convertToFlowNodes = useCallback(
    (thoughtNodes: ThoughtNode[]): Node<NodeData>[] => {
      return thoughtNodes.map((node) => {
        const message = getMessageById(node.messageId);
        const nodeData: NodeData = {
          messageId: node.messageId,
          type: node.type,
          message,
          status: message?.status,
          title: message?.title,
          content: typeof message?.content === 'string' ? message.content : '',
          onNodeClick: handleNavigateToReport,
        };

        const dimensions = NODE_DIMENSIONS[node.type];

        const flowNode: Node<NodeData> = {
          id: node.messageId,
          type: getNodeTypeString(node.type),
          position: node.position || { x: 0, y: 0 },
          data: nodeData,
          width: dimensions.width,
          height: dimensions.height,
        };

        if (node.type === ThoughtNodeType.SECTION) {
          const children = getChildMessages(node.messageId);
          const hasReport = children.some(
            child => child.type === MessageType.REPORT && child.title?.includes('章节报告')
          );
          (flowNode.data as any).hasReport = hasReport;
        }

        if (node.type === ThoughtNodeType.PLAN) {
          const children = getChildMessages(node.messageId);
          const subTasks = children
            .filter(child => child.type === MessageType.LINK || child.type === MessageType.TEXT)
            .map(child => ({
              id: child.id,
              title: child.title || '',
              status: child.status,
            }));
          (flowNode.data as any).subTasks = subTasks;
        }

        return flowNode;
      });
    },
    [getMessageById, getChildMessages, handleNavigateToReport]
  );

  const convertToFlowEdges = useCallback(
    (thoughtEdges: ThoughtEdge[]): Edge[] => {
      if (!graph) return [];

      const thoughtNodes = graph.getAllNodes();
      const nodeMap = new Map(thoughtNodes.map(node => [node.messageId, node]));

      return thoughtEdges
        .filter((edge) => edge.visible !== false)
        .map((edge) => {
          const sourceNode = nodeMap.get(edge.sourceId);
          const targetNode = nodeMap.get(edge.targetId);

          // 判断边的状态
          const edgeStatus = sourceNode && targetNode
            ? getEdgeStatus(sourceNode, targetNode)
            : 'NOT_STARTED';

          // 使用缓存的样式对象
          const style = edgeStyleCache.get(edgeStatus);

          // 根据边状态获取对应的样式
          const styleConfig = EDGE_STYLES[edgeStatus];

          // 使用缓存的data对象
          const dataCacheKey = edgeDataCache.createCacheKey(edgeStatus, edge.label);
          let data = edgeDataCache.cache.get(dataCacheKey);
          if (!data) {
            data = {
              relation: edge.relation,
              label: edge.label,
              visible: edge.visible,
              edgeStatus,
            };
            edgeDataCache.cache.set(dataCacheKey, data);
          }

          return {
            id: edge.id,
            source: edge.sourceId,
            target: edge.targetId,
            type: 'default', // 使用默认类型，让ReactFlow自动计算曲线
            animated: false,
            style,
            data,
            label: getEdgeLabelI18n(edge.label, t) || undefined, // 显示边的标签（已国际化）
            labelStyle: {
              fontSize: 12,
              fontWeight: 500,
              fill: styleConfig.labelColor,
            },
            labelBgStyle: {
              fill: styleConfig.labelBgColor,
              fillOpacity: styleConfig.labelBgOpacity,
            },
            labelShowBg: true,
            markerEnd: {
              type: 'arrowclosed',
              color: styleConfig.stroke,
              width: 20,
              height: 20,
            },
          };
        });
    },
    [graph, getEdgeStatus, edgeStyleCache, edgeDataCache, EDGE_STYLES, t, getEdgeLabelI18n]
  );

  // 获取消息项状态，用于判断是否需要继续更新
  const getMessageItemsById = useConversationStore(state => state.getMessageItemsById);
  const messageItems = graph ? getMessageItemsById(graph.getMessageItemsId()) : undefined;
  const isInProgress = messageItems?.status === 'in_progress';

  // 用于生成边的唯一标识字符串，用于比较
  const getEdgesSignature = useCallback((flowEdges: Edge[]): string => {
    return flowEdges.map(edge =>
      `${edge.id}-${edge.source}-${edge.target}-${edge.label || ''}-${edge.data?.relation}`
    ).sort().join('|');
  }, []);

  // 用于生成节点的唯一标识字符串，用于比较
  const getNodesSignature = useCallback((flowNodes: Node[]): string => {
    return flowNodes.map(node =>
      `${node.id}-${node.position.x}-${node.position.y}-${node.data.type}-${node.data.status}`
    ).sort().join('|');
  }, []);

  // 监听思维图和消息变化，实现实时更新
  useEffect(() => {
    if (!graph) return;

    const updateGraph = () => {
      const thoughtNodes = graph.getAllNodes();
      const thoughtEdges = graph.getAllEdges();

      const flowNodes = convertToFlowNodes(thoughtNodes);
      const flowEdges = convertToFlowEdges(thoughtEdges);

      // 生成edges的签名，用于比较是否真的发生了变化
      const edgesSignature = getEdgesSignature(flowEdges);

      // 只有当edges真的发生变化时才更新
      if (edgesSignature !== previousEdgesRef.current) {
        previousEdgesRef.current = edgesSignature;
        setEdges(flowEdges);
      }

      // 对于nodes，我们需要保留用户手动调整的位置
      // 所以我们只更新新节点或未被手动移动的节点
      setNodes(currentNodes => {
        const updatedNodes = flowNodes.map(flowNode => {
          const existingNode = currentNodes.find(n => n.id === flowNode.id);
          const thoughtNode = thoughtNodes.find(n => n.messageId === flowNode.id);

          // 如果节点存在且被用户手动移动过，保留其位置
          if (existingNode && thoughtNode?.isManuallyPositioned) {
            return {
              ...flowNode,
              position: existingNode.position
            };
          }
          return flowNode;
        });

        // 检查更新后的nodes是否真的发生了变化
        const updatedNodesSignature = getNodesSignature(updatedNodes);
        if (updatedNodesSignature !== previousNodesSignatureRef.current) {
          previousNodesSignatureRef.current = updatedNodesSignature;
          return updatedNodes;
        } else {
          return currentNodes; // 返回当前nodes，避免触发重新渲染
        }
      });

      setNeedLayout(graph.getNeedLayout());
    };

    // 初始更新
    updateGraph();

    // 只有当消息处理中时才定期检查更新
    // 当消息处理完毕后，自动停止检查更新
    let checkInterval: NodeJS.Timeout | null = null;
    if (isInProgress) {
      checkInterval = setInterval(updateGraph, 200);
    }

    return () => {
      if (checkInterval) {
        clearInterval(checkInterval);
      }
    };
  }, [graph, isInProgress, convertToFlowNodes, convertToFlowEdges, setNodes, setEdges, setNeedLayout, getEdgesSignature, getNodesSignature]);

  const handleLayout = useCallback(async () => {
    if (!graph) return;

    const thoughtNodes = graph.getAllNodes();
    const thoughtEdges = graph.getAllEdges();

    try {
      const layoutedNodes = await performSmartLayout(
        thoughtNodes,
        thoughtEdges,
        { ...DEFAULT_LAYOUT_OPTIONS, direction },
        graphType // 传递图类型，用于任务图的SECTION节点特殊处理
      );

      // 重新布局时，清除所有手动位置标记，重新生成所有节点位置
      layoutedNodes.forEach((layoutedNode) => {
        graph.updateNode(layoutedNode.messageId, {
          position: layoutedNode.position,
          isManuallyPositioned: false // 清除手动位置标记
        });
      });

      graph.setNeedLayout(false);
      setNeedLayout(false);

      const flowNodes = convertToFlowNodes(layoutedNodes);
      setNodes(flowNodes);

      // 保存到 IndexDB
      const conversationId = graph.getConversationId();
      if (conversationId) {
        saveConversationToDB(conversationId);
      }

      // 布局完成后适应视图
      setTimeout(() => {
        fitView({ padding: 0.2 });
      }, 100);
    } catch (error) {
      console.error('Layout failed:', error);
      const layoutedNodes = performSimpleLayout(thoughtNodes, thoughtEdges, direction);

      // 重新布局时，清除所有手动位置标记，重新生成所有节点位置
      layoutedNodes.forEach((layoutedNode) => {
        graph.updateNode(layoutedNode.messageId, {
          position: layoutedNode.position,
          isManuallyPositioned: false // 清除手动位置标记
        });
      });

      graph.setNeedLayout(false);
      setNeedLayout(false);
      const flowNodes = convertToFlowNodes(layoutedNodes);
      setNodes(flowNodes);

      // 保存到 IndexDB
      const conversationId = graph.getConversationId();
      if (conversationId) {
        saveConversationToDB(conversationId);
      }

      // 布局完成后适应视图
      setTimeout(() => {
        fitView({ padding: 0.2 });
      }, 100);
    }
  }, [graph, direction, graphType, convertToFlowNodes, setNodes, saveConversationToDB]);

  useEffect(() => {
    if (needLayout) {
      handleLayout();
    }
  }, [needLayout, handleLayout]);

  // 当节点或边变化时，自动适应视图
  useEffect(() => {
    // 同步最新的 nodes 到 ref
    nodesRef.current = nodes;

    if (nodes.length > 0) {
      triggerFitView();
    }
  }, [nodes.length, edges.length]); // 只依赖长度，避免引用变化导致的循环

  // 当思维图类型变化时，强制触发布局和适应视图
  useEffect(() => {
    // 延迟调用，确保新的思维图数据已加载
    const timer = setTimeout(() => {
      if (graph) {
        // 强制设置需要布局
        graph.setNeedLayout(true);
        setNeedLayout(true);

        // 延迟调用 fitView，确保节点已更新
        setTimeout(() => {
          triggerFitView();
        }, 500);
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [graphType]);



  if (!graph) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        <p>{t('apps.deepSearch.mindMap.noData')}</p>
      </div>
    );
  }

  const stats = graph.getGraphStats();

  return (
    <div className={`w-full h-full ${className}`}>
      <ReactFlow
        ref={reactFlowRef}
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStop={onNodeDragStop}
        nodeTypes={nodeTypes}
        minZoom={0.1}
        maxZoom={2}
        defaultEdgeOptions={{
          type: 'default', // 使用默认类型，配合ELK的SPLINES实现曲线
          style: {
            stroke: EDGE_STYLES.NOT_STARTED.stroke,
            strokeWidth: EDGE_STYLES.NOT_STARTED.strokeWidth,
            strokeDasharray: '5,5',   // 虚线
          },
          markerEnd: {
            type: 'arrowclosed',
            color: EDGE_STYLES.NOT_STARTED.stroke,
            width: 20,
            height: 20,
          },
          animated: false,
        }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#e2e8f0" />
        <MiniMap
          position="bottom-left"
          style={{ width: 120, height: 80 }}
          pannable
          zoomable
        />
        <Panel position="top-left" className="bg-white/80 px-3 py-1.5 rounded-lg shadow-sm">
          <span className="text-sm text-gray-600">
            {t('apps.deepSearch.mindMap.nodeStats', { nodes: stats.nodeCount, edges: stats.edgeCount })}
          </span>
        </Panel>
        <Panel position="top-right" className="flex items-center gap-2 bg-white p-2 rounded-lg shadow-sm border border-gray-200">
          <div className="flex border border-gray-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setGraphType('sectionGraph')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors ${graphType === 'sectionGraph' ? 'bg-gray-800 text-white font-bold' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              <ListTree size={16} />
              <span>{t('apps.deepSearch.mindMap.sectionGraph')}</span>
            </button>
            <button
              onClick={() => setGraphType('taskGraph')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm transition-colors ${graphType === 'taskGraph' ? 'bg-gray-800 text-white font-bold' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            >
              <Network size={16} />
              <span>{t('apps.deepSearch.mindMap.taskGraph')}</span>
            </button>
          </div>
          <button
            onClick={handleLayout}
            className="px-3 py-1.5 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-colors shadow-sm"
          >
            {t('apps.deepSearch.mindMap.relayout')}
          </button>
        </Panel>
        <Controls position="top-right" style={{ top: '60px' }} />
      </ReactFlow>
    </div>
  );
};

export default MindMapFlow;