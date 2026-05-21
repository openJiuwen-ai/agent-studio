import { postProcessLayout, enforceDepthBasedYPositions, alignParentChildNodes } from '../../components/Conversation/MindMap/postProcessLayout';
import { v4 as uuidv4 } from 'uuid';
import {
  ThoughtNode,
  ThoughtEdge,
  ThoughtGraph,
  LayoutConfig,
  LayoutDirection,
  ThoughtNodeType,
  EdgeRelationType,
  NODE_DIMENSIONS,
  LayoutOptions,
  DEFAULT_LAYOUT_OPTIONS,
  getNodeWidth,
  getNodeHeight
} from './deepsearchMindMapTypes';

// 重新导出类型，保持向后兼容
export type {
  ThoughtNode,
  ThoughtEdge,
  ThoughtGraph,
  LayoutConfig,
  LayoutDirection,
  LayoutOptions
};

export {
  ThoughtNodeType,
  EdgeRelationType,
  NODE_DIMENSIONS,
  DEFAULT_LAYOUT_OPTIONS,
  getNodeWidth,
  getNodeHeight
};

// ===== 操作函数类型定义 =====
// todo: 将 MindMap 均改成 ThoughtGraph; deepsearchMindMapHandler.ts 改成 thoughtGraphHandler.ts，然后作为普适性的思维链图操作接口； 
/**
 * 思维链图操作接口
 */
export interface MindMapOperations {
  // ===== Node 操作 =====
  /**
   * 增加节点
   */
  addNode: (node: Omit<ThoughtNode, 'createdAt' | 'updatedAt'>) => ThoughtNode;

  /**
   * 更新节点
   */
  updateNode: (
    messageId: string,
    updates: Partial<Omit<ThoughtNode, 'messageId' | 'createdAt' | 'updatedAt'>>
  ) => ThoughtNode | null;

  /**
   * 更新节点位置（手动拖动）
   * 标记位置为手动调整，不触发布局更新，不持久化到IndexDB
   */
  updateNodePositionManually: (messageId: string, position: { x: number; y: number }) => ThoughtNode | null;

  /**
   * 删除节点（级联删除相关边）
   */
  deleteNode: (messageId: string) => boolean;

  /**
   * 获取节点
   */
  getNode: (messageId: string) => ThoughtNode | undefined;

  // ===== Edge 操作 =====
  /**
   * 增加边
   */
  addEdge: (edge: Omit<ThoughtEdge, 'id' | 'createdAt' | 'updatedAt'>) => ThoughtEdge;

  /**
   * 更新边
   */
  updateEdge: (
    edgeId: string,
    updates: Partial<Omit<ThoughtEdge, 'id' | 'createdAt' | 'updatedAt'>>
  ) => ThoughtEdge | null;

  /**
   * 删除边（通过 sourceId + targetId）
   */
  deleteEdge: (sourceId: string, targetId: string) => boolean;

  /**
   * 删除单条边（通过 edgeId）
   */
  deleteEdgeById: (edgeId: string) => boolean;

  /**
   * 获取边
   */
  getEdge: (edgeId: string) => ThoughtEdge | undefined;

  // ===== 图操作 =====
  /**
   * 获取所有节点
   */
  getAllNodes: () => ThoughtNode[];

  /**
   * 获取所有边
   */
  getAllEdges: () => ThoughtEdge[];


  /**
   * 获取节点的所有父节点边（即其他节点指向该节点的边）
   */
  getParentEdges: (messageId: string) => ThoughtEdge[];

  /**
   * 获取节点的所有子节点边（即该节点指向其他节点的边）
   */
  getChildEdges: (messageId: string) => ThoughtEdge[];

  /**
   * 获取节点的所有父节点（即以该节点为终点的所有起点节点）
   */
  getParentNodes: (messageId: string) => ThoughtNode[];

  /**
   * 获取节点的所有子节点（即以该节点为起点的所有终点节点）
   */
  getChildNodes: (messageId: string) => ThoughtNode[];

  /**
   * 清空图
   */
  clearGraph: () => void;

  /**
   * 获取图统计信息
   */
  getGraphStats: () => { nodeCount: number; edgeCount: number };

  /**
   * 获取是否需要重新布局
   */
  getNeedLayout: () => boolean;

  /**
   * 设置是否需要重新布局
   */
  setNeedLayout: (value: boolean) => void;

  /**
   * 重新生成所有节点的深度
   * 1. 将所有节点的深度置为 undefined
   * 2. 找到所有根节点（没有父节点的节点）
   * 3. 从所有根节点开始深度生成
   */
  regenerateAllDepths: () => void;

  /**
   * 重新生成单个节点及其子孙节点的深度
   * 1. 将该节点的深度置为 undefined
   * 2. 从该节点开始深度生成
   * @param messageId 节点的 messageId
   */
  regenerateNodeDepth: (messageId: string) => void;
}

// ===== 工具函数 =====

/**
 * 生成唯一的 UUID
 * 优先使用浏览器原生 crypto.randomUUID()，失败时降级到 uuid 包
 */
const generateUUID = (): string => {
  const id = crypto?.randomUUID?.();
  return id ?? uuidv4();
};

/**
 * 判断两个节点之间是否存在边
 */
export const hasEdgeBetweenNodes = (
  graph: ThoughtGraph,
  sourceId: string,
  targetId: string,
  relation?: EdgeRelationType
): boolean => {
  return graph.edges.some(
    edge =>
      edge.sourceId === sourceId &&
      edge.targetId === targetId &&
      (!relation || edge.relation === relation)
  );
};

/**
 * 获取节点之间的边
 */
export const getEdgeBetweenNodes = (
  graph: ThoughtGraph,
  sourceId: string,
  targetId: string,
  relation?: EdgeRelationType
): ThoughtEdge | undefined => {
  return graph.edges.find(
    edge =>
      edge.sourceId === sourceId &&
      edge.targetId === targetId &&
      (!relation || edge.relation === relation)
  );
};

// ===== 默认配置 =====

/**
 * 默认布局配置
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  direction: 'TB',
  isAutoLayout: true,
  nodeSpacing: 100,
  levelSpacing: 150,
};

/**
 * 创建空的思维链图
 */
export const createEmptyThoughtGraph = (
  messageItemsId: string,
  conversationId: string
): ThoughtGraph => {
  return {
    id: generateUUID(),
    messageItemsId,
    conversationId,
    nodes: [],
    edges: [],
    layoutConfig: undefined,
    needLayout: true,
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
};

// ===== 操作函数实现 =====

/**
 * 思维链图管理类
 * 实现所有图操作的具体逻辑
 */
export class MindMapManager implements MindMapOperations {
  private graph: ThoughtGraph;

  constructor(
    initialGraph?: ThoughtGraph,
    messageItemsId?: string,
    conversationId?: string
  ) {
    if (initialGraph) {
      this.graph = initialGraph;
    } else if (messageItemsId && conversationId) {
      this.graph = createEmptyThoughtGraph(messageItemsId, conversationId);
    } else {
      throw new Error(
        'Must provide either initialGraph or both messageItemsId and conversationId'
      );
    }
  }

  // ===== 图信息获取方法 =====

  /**
   * 获取图的 ID
   */
  getGraphId(): string {
    return this.graph.id;
  }

  /**
   * 获取所属 MessageItems 的 ID
   */
  getMessageItemsId(): string {
    return this.graph.messageItemsId;
  }

  /**
   * 获取所属 Conversation 的 ID
   */
  getConversationId(): string {
    return this.graph.conversationId;
  }

  // ===== Node 操作 =====

  addNode(node: Omit<ThoughtNode, 'createdAt' | 'updatedAt'>): ThoughtNode {
    const now = Date.now();
    const newNode: ThoughtNode = {
      ...node,
      createdAt: now,
      updatedAt: now,
    };

    this.graph.nodes.push(newNode);
    this.graph.needLayout = true;
    this.updateGraphTimestamp();
    return newNode;
  }

  updateNode(
    messageId: string,
    updates: Partial<Omit<ThoughtNode, 'messageId' | 'createdAt' | 'updatedAt'>>
  ): ThoughtNode | null {
    const nodeIndex = this.graph.nodes.findIndex(n => n.messageId === messageId);
    if (nodeIndex === -1) {
      return null;
    }

    const updatedNode: ThoughtNode = {
      ...this.graph.nodes[nodeIndex],
      ...updates,
      updatedAt: Date.now(),
    };

    this.graph.nodes[nodeIndex] = updatedNode;
    this.updateGraphTimestamp();
    return updatedNode;
  }

  /**
   * 更新节点位置（手动拖动）
   * 此方法标记位置为手动调整，不会触发布局更新，也不会持久化到IndexDB
   */
  updateNodePositionManually(messageId: string, position: { x: number; y: number }): ThoughtNode | null {
    return this.updateNode(messageId, {
      position,
      isManuallyPositioned: true
    });
  }

  deleteNode(messageId: string): boolean {
    const nodeIndex = this.graph.nodes.findIndex(n => n.messageId === messageId);
    if (nodeIndex === -1) {
      return false;
    }

    // 删除节点
    this.graph.nodes.splice(nodeIndex, 1);

    // 级联删除相关边（删除所有 sourceId 或 targetId 为该节点的边）
    this.graph.edges = this.graph.edges.filter(
      edge => edge.sourceId !== messageId && edge.targetId !== messageId
    );
    this.graph.needLayout = true;

    this.updateGraphTimestamp();
    return true;
  }

  getNode(messageId: string): ThoughtNode | undefined {
    return this.graph.nodes.find(n => n.messageId === messageId);
  }

  // ===== Edge 操作 =====

  addEdge(edge: Omit<ThoughtEdge, 'id' | 'createdAt' | 'updatedAt'>): ThoughtEdge {
    const now = Date.now();
    const newEdge: ThoughtEdge = {
      ...edge,
      id: generateUUID(),
      createdAt: now,
      updatedAt: now,
    };

    this.graph.edges.push(newEdge);
    this.graph.needLayout = true;
    this.updateGraphTimestamp();
    return newEdge;
  }

  updateEdge(
    edgeId: string,
    updates: Partial<Omit<ThoughtEdge, 'id' | 'createdAt' | 'updatedAt'>>
  ): ThoughtEdge | null {
    const edgeIndex = this.graph.edges.findIndex(e => e.id === edgeId);
    if (edgeIndex === -1) {
      return null;
    }

    const updatedEdge: ThoughtEdge = {
      ...this.graph.edges[edgeIndex],
      ...updates,
      updatedAt: Date.now(),
    };

    this.graph.edges[edgeIndex] = updatedEdge;
    this.updateGraphTimestamp();
    return updatedEdge;
  }

  deleteEdge(sourceId: string, targetId: string): boolean {
    const initialLength = this.graph.edges.length;
    this.graph.edges = this.graph.edges.filter(
      edge => !(edge.sourceId === sourceId && edge.targetId === targetId)
    );

    this.graph.needLayout = true;
    if (this.graph.edges.length < initialLength) {
      this.updateGraphTimestamp();
      return true;
    }
    return false;
  }

  deleteEdgeById(edgeId: string): boolean {
    const edgeIndex = this.graph.edges.findIndex(e => e.id === edgeId);
    if (edgeIndex === -1) {
      return false;
    }
    this.graph.needLayout = true;

    this.graph.edges.splice(edgeIndex, 1);
    this.updateGraphTimestamp();
    return true;
  }

  getEdge(edgeId: string): ThoughtEdge | undefined {
    return this.graph.edges.find(e => e.id === edgeId);
  }

  // ===== 图操作 =====

  getAllNodes(): ThoughtNode[] {
    return [...this.graph.nodes];
  }

  getAllEdges(): ThoughtEdge[] {
    return [...this.graph.edges];
  }

  getParentEdges(messageId: string): ThoughtEdge[] {
    return this.graph.edges.filter(edge => edge.targetId === messageId);
  }

  getChildEdges(messageId: string): ThoughtEdge[] {
    return this.graph.edges.filter(edge => edge.sourceId === messageId);
  }

  /**
   * 获取节点的所有父节点（即以该节点为终点的所有起点节点）
   */
  getParentNodes(messageId: string): ThoughtNode[] {
    const parentEdges = this.getParentEdges(messageId);
    const parentNodeIds = parentEdges.map(edge => edge.sourceId);
    return this.graph.nodes.filter(node => parentNodeIds.includes(node.messageId));
  }

  /**
   * 获取节点的所有子节点（即以该节点为起点的所有终点节点）
   */
  getChildNodes(messageId: string): ThoughtNode[] {
    const childEdges = this.getChildEdges(messageId);
    const childNodeIds = childEdges.map(edge => edge.targetId);
    return this.graph.nodes.filter(node => childNodeIds.includes(node.messageId));
  }

  /**
   * 获取目标节点的前序兄节点（共享至少一个父节点，且 createdAt 早于目标节点）
   */
  private getPrecedingSiblingNodes(messageId: string): ThoughtNode[] {
    const node = this.getNode(messageId);
    if (!node) return [];

    const parentNodes = this.getParentNodes(messageId);
    if (parentNodes.length === 0) return [];

    const siblingIds = new Set<string>();
    parentNodes.forEach(parent => {
      this.getChildNodes(parent.messageId).forEach(sibling => {
        if (sibling.messageId !== messageId && sibling.createdAt < node.createdAt) {
          siblingIds.add(sibling.messageId);
        }
      });
    });

    return this.graph.nodes.filter(n => siblingIds.has(n.messageId));
  }

  clearGraph(): void {
    this.graph.nodes = [];
    this.graph.edges = [];
    this.updateGraphTimestamp();
  }

  getGraphStats(): { nodeCount: number; edgeCount: number } {
    return {
      nodeCount: this.graph.nodes.length,
      edgeCount: this.graph.edges.length,
    };
  }

  // ===== 额外辅助方法 =====

  /**
   * 获取当前图的引用（用于调试或高级操作）
   */
  getGraph(): ThoughtGraph {
    return this.graph;
  }

  /**
   * 批量添加节点
   */
  addNodes(nodes: Omit<ThoughtNode, 'createdAt' | 'updatedAt'>[]): ThoughtNode[] {
    const now = Date.now();
    const newNodes: ThoughtNode[] = nodes.map(node => ({
      ...node,
      createdAt: now,
      updatedAt: now,
    }));

    this.graph.nodes.push(...newNodes);
    this.graph.needLayout = true;
    this.updateGraphTimestamp();
    return newNodes;
  }

  /**
   * 批量添加边
   */
  addEdges(edges: Omit<ThoughtEdge, 'id' | 'createdAt' | 'updatedAt'>[]): ThoughtEdge[] {
    const now = Date.now();
    const newEdges: ThoughtEdge[] = edges.map(edge => ({
      ...edge,
      id: generateUUID(),
      createdAt: now,
      updatedAt: now,
    }));

    this.graph.edges.push(...newEdges);
    this.graph.needLayout = true;
    this.updateGraphTimestamp();
    return newEdges;
  }

  /**
   * 更新布局配置
   */
  updateLayoutConfig(config: Partial<LayoutConfig>): void {
    this.graph.layoutConfig = {
      ...this.graph.layoutConfig,
      ...config,
    } as LayoutConfig;
    this.updateGraphTimestamp();
    this.graph.needLayout = true;
  }

  /**
   * 更新图的时间戳
   */
  private updateGraphTimestamp(): void {
    this.graph.updatedAt = Date.now();
  }
  
  /**
   * 获取是否需要重新布局
   */
  getNeedLayout(): boolean {
    return this.graph.needLayout;
  }

  /**
   * 设置是否需要重新布局
   */
  setNeedLayout(value: boolean): void {
    this.graph.needLayout = value;
  }

  /**
   * 应用后处理布局优化
   * @param addNodeId 可选的新增节点ID，用于增量优化
   * @private
   */
  private applyPostProcessLayout(addNodeId?: string): void {
    // 后处理计算节点的位置
    const maxHeight = Math.max(...this.graph.nodes.map(node => NODE_DIMENSIONS[node.type].height));
    const layerHeight = Math.round(maxHeight * 1.5);
    // const optimizedNodes = postProcessLayout(
    //   this.graph.nodes,
    //   this.graph.edges,
    //   layerHeight,
    //   addNodeId
    // );

    // // 更新节点的位置
    // optimizedNodes.forEach(optimizedNode => {
    //   const nodeIndex = this.graph.nodes.findIndex(n => n.messageId === optimizedNode.messageId);
    //   if (nodeIndex !== -1 && optimizedNode.position) {
    //     this.graph.nodes[nodeIndex].position = optimizedNode.position;
    //     this.graph.nodes[nodeIndex].depth = optimizedNode.depth;
    //   }
    // });

    enforceDepthBasedYPositions(
      this.graph.nodes,
      layerHeight,
      addNodeId
    );

    alignParentChildNodes(
      this.graph.nodes, 
      this.graph.edges, 
      DEFAULT_LAYOUT_OPTIONS.nodeSpacing, 
      addNodeId
    );

  }

  // ===== 深度管理方法 =====

  /**
   * 重新生成所有节点的深度
   */
  regenerateAllDepths(): void {
    const totalNodes = this.graph.nodes.length;

    // 步骤1：将所有节点的深度置为 undefined
    this.graph.nodes.forEach(node => {
      node.depth = undefined;
    });

    // 步骤2：找到所有根节点（没有父节点的节点）
    const rootNodes = this.graph.nodes.filter(node => {
      const parentNodes = this.getParentNodes(node.messageId);
      return parentNodes.length === 0;
    });

    // 步骤3：从所有根节点开始深度生成
    rootNodes.forEach(rootNode => {
      this.depthGenerate(rootNode.messageId, false, totalNodes);
    });

    // 后处理计算节点的位置
    this.applyPostProcessLayout();

    this.updateGraphTimestamp();
  }

  /**
   * 重新生成单个节点及其子孙节点的深度
   */
  regenerateNodeDepth(messageId: string): void {
    // 验证节点是否存在
    const node = this.getNode(messageId);
    if (!node) {
      return;
    }

    const totalNodes = this.graph.nodes.length;

    // 从该节点开始深度生成（入口调用，需要重置深度）
    this.depthGenerate(messageId, true, totalNodes);

    // 后处理计算节点的位置
    this.applyPostProcessLayout(messageId);

    this.updateGraphTimestamp();
  }

  /**
   * 深度生成核心逻辑（私有方法）
   * @param messageId 节点的 messageId
   * @param resetDepth 是否重置该节点的深度（只在入口调用时为 true）
   * @param maxDepth 最大深度阈值（用于检测循环依赖）
   */
  private depthGenerate(messageId: string, resetDepth: boolean, maxDepth: number): void {
    const node = this.getNode(messageId);
    if (!node) {
      return;
    }

    // 步骤1：如果需要重置深度，将该节点的 depth 置为 undefined
    if (resetDepth) {
      node.depth = undefined;
    }

    // 步骤2：获取该节点的所有父节点
    const parentNodes = this.getParentNodes(messageId);

    // 步骤3：根据父节点情况计算深度
    if (parentNodes.length === 0) {
      // 没有父节点，直接设置为 0
      node.depth = 0;
    } else {
      // 有父节点，检查是否所有父节点都有深度
      const allParentsHaveDepth = parentNodes.every(
        parentNode => parentNode.depth !== undefined
      );

      if (!allParentsHaveDepth) {
        // 有父节点的深度为 undefined，直接返回
        return;
      }

      // 所有父节点都有深度，计算本节点深度
      const maxParentDepth = Math.max(
        ...parentNodes.map(parent => parent.depth as number)
      );
      const newDepth = maxParentDepth + 1;

      // 检查循环依赖：如果 depth >= 节点总数，说明存在循环依赖
      if (newDepth >= maxDepth) {
        return;
      }

      // 兄节点约束：前序兄节点（与目标节点无依赖边）的深度不能大于本节点深度
      const precedingSiblings = this.getPrecedingSiblingNodes(messageId);
      let finalDepth = newDepth;
      for (const sibling of precedingSiblings) {
        const hasDependency =
          hasEdgeBetweenNodes(this.graph, messageId, sibling.messageId) ||
          hasEdgeBetweenNodes(this.graph, sibling.messageId, messageId);
        if (!hasDependency && sibling.depth !== undefined) {
          finalDepth = Math.max(finalDepth, sibling.depth);
        }
      }

      node.depth = finalDepth;
    }

    // 步骤4：按 createdAt 升序排序后递归处理子节点（保证前序兄节点先于后序兄节点处理）
    const childNodes = this.getChildNodes(messageId);
    const sortedChildNodes = [...childNodes].sort((a, b) => a.createdAt - b.createdAt);
    sortedChildNodes.forEach(childNode => {
      this.depthGenerate(childNode.messageId, false, maxDepth);
    });
  }
}

// ===== 工厂函数 =====

/**
 * 创建思维链图管理器
 * @param initialGraph 可选的初始图数据
 * @param messageItemsId 当没有 initialGraph 时，必须提供此参数
 * @param conversationId 当没有 initialGraph 时，必须提供此参数
 */
export const createMindMapManager = (
  initialGraph?: ThoughtGraph,
  messageItemsId?: string,
  conversationId?: string
): MindMapManager => {
  return new MindMapManager(initialGraph, messageItemsId, conversationId);
};
