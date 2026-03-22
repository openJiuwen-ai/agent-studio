import { create } from 'zustand'
import { conversationDB, conversationEventEmitter } from '../utils/conversationDB'
import i18n from '../i18n'

// ===== LocalStorage 键名常量 =====
const STORAGE_KEYS = {
  CONVERSATION_DATA_PREFIX: 'conv_data_',
  CONVERSATIONS_INDEX: 'conv_index',
} as const

// ===== 枚举定义 =====
// 消息的类型定义
export enum MessageType {
  // 基础类型
  TEXT = 'text',              // 普通文本/Markdown
  REPORT = 'report',          // 报告类型, 其他数据和TEXT一样，只是前端使用报告的模板进行显示
  LINK = 'link',              // 外部链接（网页）
  DETAIL_LINK = 'detail_link',// 详情链接（打开右侧面板）

  // 任务类型（带子任务）
  TASK = 'task',              // 任务容器

  // 特殊类型
  ERROR = 'error',            // 错误信息
  INTERRUPT = 'interrupt',    // 中断等待用户输入
  OUTLINE_INTERACTION = 'outline_interaction', // 大纲交互等待用户确认
}

export enum TaskStatus {
  PENDING = 'pending',        // 未开始
  IN_PROGRESS = 'in_progress', // 进行中
  COMPLETED = 'completed',    // 完成
  FAILED = 'failed',          // 失败
  CANCELLED = 'cancelled',    // 手动结束
  UNKNOWN = 'unknown',        // 未知/提示状态, 有时后端api可能缺少某些流程的数据，导致消息的状态未知
}

// 对话过程中，某次发问所选择的agent类型
export enum AgentType {
  ORDINARY = 'ordinary',   // 普通agent
  DEEPSEARCH = 'deepsearch', // 深度研究
}

// ===== 错误消息配置 =====
/**
 * 错误消息配置接口
 * 用于在消息处理失败时添加错误提示
 */
export interface ErrorMessageConfig {
  title: string;
  content: string;
}

// ===== 消息标题常量 =====
// 用于程序判断，与语言环境无关
export const MESSAGE_TITLES = {
  FINAL_REPORT: 'FINAL_REPORT',
} as const;

// ===== 兼容性：历史标题 =====
// 用于识别已生成的旧数据（使用国际化文本作为标题）
const LEGACY_FINAL_REPORT_TITLES = ['最终报告', 'Final Report'] as const;

// ===== SSE超时监控配置 =====
// SSE超时时间（分钟）- 超过这个时间没有收到SSE事件，将标记未完成消息为FAILED
export const SSE_TIMEOUT_MINUTES = 30;

// ===== 大纲交互常量 =====
// 大纲最大修改次数限制
export const OUTLINE_INTERACTION_MAX_ROUNDS = 100;
// 大纲交互提醒阈值（剩余次数小于等于该值时提醒）
export const OUTLINE_INTERACTION_WARNING_THRESHOLD = 3;

/**
 * 判断消息是否为最终报告
 * 兼容新旧数据：
 * - 新数据：使用 MESSAGE_TITLES.FINAL_REPORT（'FINAL_REPORT'）
 * - 旧数据：使用国际化文本（'最终报告'、'Final Report'）
 *
 * @param title - 消息标题
 * @returns 是否为最终报告
 */
export function isFinalReportMessage(title: string | undefined): boolean {
  if (!title) return false;
  return title === MESSAGE_TITLES.FINAL_REPORT ||
         LEGACY_FINAL_REPORT_TITLES.includes(title as any);
}


export interface LinkContent {
  url: string;                 // 链接地址
  title: string;               // 链接标题
  query?: string;              // 搜索词（collector_info_retrieval返回）
  description?: string;        // 简短描述
  source?: string;             // 来源（如：网页、知识库）
  publishTime?: string;        // 发布时间
  cardStyle?: 'text' | 'card'; // 展示样式
}

// JSON 对象类型定义
export type JSONObject = Record<string, unknown>;

// Message 内容的类型定义
export type MessageContent = string | LinkContent | JSONObject;

export interface Message {
  // ===== 必选字段 =====
  id: string;                  // 消息唯一标识，格式：task_1[_{section}[_{plan}[_{step}]]]
  type: MessageType;           // 消息类型
  status: TaskStatus;          // 状态
  content: MessageContent;     // 数据内容
                               // - TEXT/REPORT: Markdown字符串或JSONObject
                               // - LINK/DETAIL_LINK: LinkContent对象

  // ===== 可选字段 =====
  title?: string;              // 标题（可选）
  icon?: string;               // 图标标识

  // ===== 元数据字段 =====
  parentMessageId?: string;    // 父消息ID（用于构建树形结构）
  childMessageIds?: string[];     // 子任务ID列表（只存ID，不存对象）

  // ===== 外键字段（用于关联和快速查找） =====
  messageItemsId: string;      // 所属 MessageItems 的 ID
  conversationId: string;       // 所属 Conversation 的 ID

  // ===== 时间字段 =====
  createdAt: number;           // 创建时间戳
  updatedAt: number;           // 最后更新时间戳

  // ===== SSE流式相关 =====
  isStreaming?: boolean;       // 是否正在接收

  // TASK类型数据相关
  sectionIdx?: number;         // 作用于task类型消息中，用于章节索引：0=主任务, 1-10=章节，用于标识任务在层级结构中的位置
}

export interface MessageItems {
  id: string;                  // MessageItems唯一标识
  status: TaskStatus;          // 状态
  messagesIds: string[];       // 消息Message的id list, 如果是task的message，只写入根节点的id(子节点由根节点去索引)

  // ===== 时间字段 =====
  createdAt: number;           // 创建时间戳
  updatedAt: number;           // 最后更新时间戳

  // ===== 其他 =====
  conversationId: string;      // 会话ID

  // ===== 配置信息 =====
  isUser: boolean;             // 是否用户消息
  agentType?: AgentType;       // Agent类型，用于HITL场景判断agent匹配
  llm?: string;                // 大模型名称
  agentConfig?: { [key: string]: any }; // agent的参数配置项
}

export interface Conversation {
  id: string;                  // Conversation的id
  title: string;
  createdAt: number;
  updatedAt: number;
  config: {
    agentType: string;         // agent类型：deepsearch|travel|...
    [key: string]: any;
  };
  messageItemsIds: string[];    // 消息MessageItems的id列表
  last_session_conversation_id?: string; // 连续对话系列中的上一个会话ID，用于恢复对话上下文；连续对话类型包括：deepsearch,
}

// ===== 数据导出类型 =====

export interface ConversationData {
  conversation: Conversation;
  messageItems: MessageItems[];
  messages: Record<string, Message>;  // Map转对象以便序列化
}

export interface ConversationsIndex {
  conversations: Record<string, {
    id: string;
    title: string;
    createdAt: number;
    updatedAt: number;
    config: Conversation['config'];
  }>;
  lastUpdated: number;
}

export interface ConversationStore {
  // ===== 核心数据存储 =====

  // 1. 所有实体数据的Map（类似数据库表）
  conversationsMap: Map<string, Conversation>;      // conversationId -> Conversation
  messageItemsMap: Map<string, MessageItems>;       // messageItemsId -> MessageItems
  messagesMap: Map<string, Message>;                // messageId -> Message

  // 2. 当前会话状态
  currentConversationId: string | null;

  // 3. 列表数据（用于UI展示，缓存）
  conversationsList: string[];          // 所有conversation的ID列表（按时间排序）

  // 4. UI状态
  isLoading: boolean;
  selectedResultMessageId: string | null;
  sseStreamCache: Map<string, string[]>; // SSE流式数据缓存：key -> content chunks
  sseEventQueue: Array<{sseData: JSONObject; conversationId: string; agentType: string}>; // SSE 事件队列（确保按顺序处理）
  sseProcessingQueue: boolean; // 是否正在处理队列

  // ========== SSE超时监控状态 ==========
  lastSSEEventTime: number | null;  // 上次SSE事件时间戳
  sseTimeoutCheckInterval: number | null;  // 超时检查定时器ID

  // ========== 连续对话系列状态 ==========
  SESSION_CONVERSATION_ID: string | null;  // 连续对话系列的conversationId（null表示非连续对话）

  // ========== 大纲交互状态 ==========
  pendingOutlineInteraction: {
    messageId: string;
    userMessage: string;
    backendMessage?: string;
    interruptFeedback: string;
  } | null;  // 待处理的大纲交互接受请求

  // ========== Conversation 层级：查询函数 ==========

  /**
   * 获取当前 Conversation 对象
   */
  getCurrentConversation: () => Conversation | null;

  /**
   * 根据 ID 获取 Conversation
   */
  getConversationById: (id: string) => Conversation | undefined;

  /**
   * 获取所有 Conversation 列表（用于侧边栏展示）
   */
  getAllConversations: () => Conversation[];

  /**
   * 获取当前 Conversation 的所有 MessageItems
   */
  getCurrentMessageItems: () => MessageItems[];

  /**
   * 获取当前对话的完整数据（用于序列化保存）
   */
  getCurrentConversationData: () => ConversationData | null;

  /**
   * 获取指定对话的完整数据
   */
  getConversationData: (conversationId: string) => ConversationData | null;

  // ========== MessageItems 层级：查询函数 ==========

  /**
   * 根据 conversationId 获取所有关联的 MessageItems
   */
  getMessageItemsByConversationId: (conversationId: string) => MessageItems[];

  /**
   * 根据 ID 获取 MessageItems
   */
  getMessageItemsById: (id: string) => MessageItems | undefined;

  /**
   * 获取 MessageItems 的所有根消息（展开消息树）
   */
  getMessagesByMessageItemsId: (messageItemsId: string) => Message[];

  // ========== Message 层级：查询函数 ==========

  /**
   * 根据 ID 获取 Message
   */
  getMessageById: (id: string) => Message | undefined;

  /**
   * 递归获取消息树（包含子消息）
   * @param messageId 根消息ID
   * @returns 完整的消息树
   */
  getMessageTree: (messageId: string) => Message | null;

  /**
   * 获取子消息列表
   */
  getChildMessages: (messageId: string) => Message[];

  // ========== Conversation 操作函数 ==========

  /**
   * 创建新 Conversation
   * @param title 标题
   * @param config 配置
   * @returns conversationId
   */
  createConversation: (title: string, config: any) => string;

  /**
   * 切换到指定 Conversation（支持懒加载）
   * @param conversationId 目标ID
   */
  switchConversation: (conversationId: string) => Promise<void>;

  /**
   * 更新 Conversation
   */
  updateConversation: (
    conversationId: string,
    updates: Partial<Conversation>
  ) => void;

  /**
   * 删除 Conversation（级联删除关联的 MessageItems 和 Messages）
   */
  deleteConversation: (conversationId: string) => Promise<void>;

  // ========== MessageItems 操作函数 ==========

  /**
   * 添加 MessageItems 到 Conversation
   * @param messageItems MessageItems 对象
   * @param conversationId 所属 Conversation ID（可选，默认当前对话）
   */
  addMessageItems: (
    messageItems: MessageItems,
    conversationId?: string
  ) => void;

  /**
   * 更新 MessageItems
   */
  updateMessageItems: (
    messageItemsId: string,
    updates: Partial<MessageItems>
  ) => void;

  /**
   * 删除 MessageItems（级联删除关联的 Messages）
   */
  deleteMessageItems: (messageItemsId: string) => void;

  // ========== Message 操作函数 ==========

  /**
   * 添加用户消息（快捷方法）
   * @param conversationId Conversation ID
   * @param content 消息内容
   * @returns 创建的 MessageItems
   */
  addUserMessage: (
    conversationId: string,
    content: string
  ) => MessageItems;

  /**
   * 添加系统消息（快捷方法）
   * @param agentType Agent类型（如：deepsearch），用于设置MessageItems.agentType，用于HITL场景匹配
   * @returns 返回创建的 Message，如果对话已取消则返回 null
   */
  addSystemMessage: (
    conversationId: string,
    type: MessageType,
    content: any,
    parentId?: string,
    title?: string,
    agentType?: string
  ) => Message | null;

  /**
   * 添加 Message 到 MessageItems
   * @param messageItemsId MessageItems ID
   * @param message Message 对象
   * @param isRootMessage 是否为根消息（决定是否加入 messagesIds）
   */
  addMessage: (
    messageItemsId: string,
    message: Message,
    isRootMessage?: boolean
  ) => void;

  /**
   * 更新 Message
   */
  updateMessage: (
    messageItemsId: string,
    messageId: string,
    updates: Partial<Message>
  ) => void;

  /**
   * 删除 Message（级联删除子消息）
   */
  deleteMessage: (messageItemsId: string, messageId: string) => void;

  /**
   * 追加 Message 内容（用于流式输出）
   */
  appendMessageContent: (messageItemsId: string, messageId: string, content: string) => void;

  /**
   * 添加子消息到父消息（构建树形结构）
   */
  addMessageAsChild: (
    messageItemsId: string,
    parentId: string,
    type: MessageType,
    content: any,
    title?: string
  ) => Message;

  // ========== 流式消息处理 =====
  handleSSEMessage: (sseData: JSONObject, conversationId: string, agentType?: string) => void;
  processSSEQueue: () => void; // 处理 SSE 事件队列

  // ========== 状态管理 ==========
  setLoading: (loading: boolean) => void;
  clearCurrentConversation: () => void;
  clearAll: () => void; // 清空所有对话数据
  setSelectedResultMessageId: (messageId: string | null) => void;

  // ===== 辅助方法 =====
  generateMessageId: (sectionIdx?: number, planIdx?: number, stepIdx?: number, ...extra: number[]) => string;
  generateMessageItemsId: () => string;
  generateConversationId: () => string;
  debugLogMessageItems: (messageItemsId?: string, label?: string) => void;
  debugLogConversation: (conversationId?: string) => void;

  /**
   * 检查内存中对话数据的大小
   * 如果超过 100MB，在控制台输出警告
   */
  checkMemorySize: () => void;

  /**
   * 获取 MessageItems 的 isUser 属性（兼容历史数据）
   * 历史数据中 isUser 在 config 中，新数据直接在顶层
   */
  getMessageItemsIsUser: (messageItems: MessageItems) => boolean;

  /**
   * 检查创建新对话前是否需要警告
   * 返回警告信息，如果不需要警告则返回 null
   */
  checkCreateConversationWarning: () => Promise<{
    type: 'count-warning' | 'storage-warning' | null
    currentCount?: number
    maxCount?: number
    currentSize?: number
    maxSize?: number
    warningThreshold?: number
    oldestConversation?: {
      id: string
      title: string
      createdAt: number
    }
  } | null>;

  // ========== IndexDB 持久化 ==========

  /**
   * 保存对话到 IndexDB
   * 在系统消息（AI回复）结束时调用
   */
  saveConversationToDB: (conversationId: string) => Promise<void>;

  /**
   * 获取或创建回放专用对话
   * - 如果存在标题为"回放对话"的对话，返回其 ID
   * - 如果不存在，创建一个新的"回放对话"并返回其 ID
   */
  getOrCreatePlaybackConversation: () => string;

  /**
   * 从 IndexDB 初始化对话数据
   * 只在内存中没有数据时才加载
   */
  initializeFromDB: () => Promise<void>;

  /**
   * 加载单个对话的完整数据（包含 messageItems 和 messages）
   * 用于切换对话时懒加载
   */
  loadConversationFullData: (conversationId: string) => Promise<void>;

  /**
   * 卸载当前对话的详细数据（messageItems 和 messages）
   * 保留基本信息，释放内存
   */
  unloadCurrentConversation: () => void;

  // ========== SSE超时监控方法 ==========

  /**
   * 启动SSE超时监控
   * @param conversationId 要监控的对话ID
   */
  startSSETimeoutMonitor: (conversationId: string) => void;

  /**
   * 停止SSE超时监控
   */
  stopSSETimeoutMonitor: () => void;

  /**
   * 更新最后SSE事件时间
   */
  updateLastSSEEventTime: () => void;

  /**
   * 检查并标记当前对话中未完成的MessageItems为FAILED
   * @returns 是否标记了失败的消息
   */
  checkAndMarkIncompleteAsFailed: () => boolean;

  /**
   * 标记当前对话中最后一个MessageItems（及其所有未完成的消息）为FAILED
   * @param errorMessage 可选的错误消息配置，如果提供则添加错误消息到MessageItems中
   */
  markCurrentConversationIncompleteAsFailed: (errorMessage?: ErrorMessageConfig | null) => void;

  /**
   * 设置 SESSION_CONVERSATION_ID
   * @param conversationId 连续对话系列的conversationId
   */
  setSessionConversationId: (conversationId: string | null) => void;

  /**
   * 触发大纲交互接受
   * @param messageId 消息ID
   * @param userMessage 用户消息
   * @param backendMessage 发送给后端 message 字段的数据
   * @param interruptFeedback 中断反馈标识
   */
  triggerOutlineInteractionAccept: (messageId: string, userMessage: string, backendMessage?: string, interruptFeedback?: string) => void;

  /**
   * 清除待处理的大纲交互
   */
  clearPendingOutlineInteraction: () => void;

  /**
   * 更新当前 MessageItems 状态为 CANCELLED（用于 DeepSearch 取消功能）
   * 同时更新所有子消息的状态，确保 UI 正确显示取消状态
   * 如果没有 INTERRUPT 消息，会创建一个 CANCELLED 状态的 INTERRUPT 消息用于显示取消提示
   */
  updateMessageItemsStatusToCancelled: () => void;
}

// ===== Store实现 =====

/**
 * 递归删除消息的辅助函数
 * @param messageId 要删除的消息ID
 * @param messagesMap 消息Map（会被修改）
 * @param originalMessagesMap 原始消息Map（用于查找子消息）
 */
function deleteMessageRecursively(
  messageId: string,
  messagesMap: Map<string, Message>,
  originalMessagesMap: Map<string, Message>
): void {
  const msg = originalMessagesMap.get(messageId);
  if (msg?.childMessageIds) {
    msg.childMessageIds.forEach(childId =>
      deleteMessageRecursively(childId, messagesMap, originalMessagesMap)
    );
  }
  messagesMap.delete(messageId);
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  // ===== 初始状态 =====
  conversationsMap: new Map<string, Conversation>(),
  messageItemsMap: new Map<string, MessageItems>(),
  messagesMap: new Map<string, Message>(),
  currentConversationId: null,
  conversationsList: [],
  isLoading: false,
  selectedResultMessageId: null,
  sseStreamCache: new Map<string, string[]>(),
  sseEventQueue: [],
  sseProcessingQueue: false,
  lastSSEEventTime: null,
  sseTimeoutCheckInterval: null,
  SESSION_CONVERSATION_ID: null,
  pendingOutlineInteraction: null,

  // ========== Conversation 层级：查询函数 ==========

  getCurrentConversation: () => {
    const { currentConversationId, conversationsMap } = get();
    return currentConversationId ? conversationsMap.get(currentConversationId) || null : null;
  },

  getConversationById: (id: string) => {
    return get().conversationsMap.get(id);
  },

  getAllConversations: () => {
    const { conversationsList, conversationsMap } = get();
    return conversationsList
      .map(id => conversationsMap.get(id))
      .filter((conv): conv is Conversation => conv !== undefined);
  },

  getCurrentMessageItems: () => {
    const { currentConversationId } = get();
    if (!currentConversationId) return [];
    return get().getMessageItemsByConversationId(currentConversationId);
  },

  getCurrentConversationData: () => {
    const { currentConversationId } = get();
    if (!currentConversationId) return null;
    return get().getConversationData(currentConversationId);
  },

  getConversationData: (conversationId: string) => {
    const state = get();
    const conversation = state.conversationsMap.get(conversationId);
    if (!conversation) return null;

    const messageItems = state.getMessageItemsByConversationId(conversationId);

    // 收集所有相关的 messages
    const messagesMap: Record<string, Message> = {};
    messageItems.forEach(items => {
      items.messagesIds.forEach(msgId => {
        const msg = state.getMessageTree(msgId);
        if (msg) {
          // 递归收集消息树中的所有消息
          const collectMessages = (message: Message) => {
            messagesMap[message.id] = message;
            if (message.childMessageIds) {
              message.childMessageIds.forEach(childId => {
                const child = state.messagesMap.get(childId);
                if (child) collectMessages(child);
              });
            }
          };
          collectMessages(msg);
        }
      });
    });

    return {
      conversation,
      messageItems,
      messages: messagesMap,
    };
  },

  // ========== MessageItems 层级：查询函数 ==========

  getMessageItemsByConversationId: (conversationId: string) => {
    const state = get();
    const conversation = state.conversationsMap.get(conversationId);
    if (!conversation) return [];

    return conversation.messageItemsIds
      .map(id => state.messageItemsMap.get(id))
      .filter((items): items is MessageItems => items !== undefined)
      .sort((a, b) => a.createdAt - b.createdAt);
  },

  getMessageItemsById: (id: string) => {
    return get().messageItemsMap.get(id);
  },

  getMessagesByMessageItemsId: (messageItemsId: string) => {
    const state = get();
    const messageItems = state.messageItemsMap.get(messageItemsId);
    if (!messageItems) return [];

    return messageItems.messagesIds
      .map(id => state.getMessageTree(id))
      .filter((msg): msg is Message => msg !== undefined);
  },

  // ========== Message 层级：查询函数 ==========

  getMessageById: (id: string) => {
    return get().messagesMap.get(id);
  },

  getMessageTree: (messageId: string) => {
    const state = get();
    const message = state.messagesMap.get(messageId);
    if (!message) return null;

    // 深拷贝消息对象，并递归构建子消息树
    const buildTree = (msg: Message): Message => {
      const children = msg.childMessageIds?.map(childId =>
        state.messagesMap.get(childId)
      ).filter((m): m is Message => m !== undefined);

      return {
        ...msg,
        // 递归构建子消息
        ...(children && children.length > 0 ? {
          childMessageIds: msg.childMessageIds,
          // 可以选择性地在这里构建嵌套的子消息对象
        } : {}),
      };
    };

    return buildTree(message);
  },

  getChildMessages: (messageId: string) => {
    const message = get().messagesMap.get(messageId);
    if (!message || !message.childMessageIds) return [];

    return message.childMessageIds
      .map(id => get().messagesMap.get(id))
      .filter((msg): msg is Message => msg !== undefined);
  },

  // ========== Conversation 操作函数 ==========

  createConversation: (title: string, config: any) => {
    const conversationId = get().generateConversationId();
    const conversation: Conversation = {
      id: conversationId,
      title,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      config,
      messageItemsIds: [],
    };

    set((state) => {
      const newConversationsMap = new Map(state.conversationsMap);
      newConversationsMap.set(conversationId, conversation);

      return {
        conversationsMap: newConversationsMap,
        conversationsList: [...state.conversationsList, conversationId],
        currentConversationId: conversationId,
      };
    });

    return conversationId;
  },

  switchConversation: async (conversationId: string) => {
    const state = get();
    const conversation = state.conversationsMap.get(conversationId);
    if (!conversation) {
      console.warn('[switchConversation] Conversation not found:', conversationId);
      return;
    }

    // 如果有当前对话且与目标对话不同，先卸载当前对话的详细数据
    if (state.currentConversationId && state.currentConversationId !== conversationId) {
      get().unloadCurrentConversation();
    }

    // 切换到新对话
    set({ currentConversationId: conversationId, SESSION_CONVERSATION_ID: null });

    // 加载新对话的完整数据
    await get().loadConversationFullData(conversationId);
  },

  updateConversation: (conversationId: string, updates: Partial<Conversation>) => {
    set((state) => {
      const conversation = state.conversationsMap.get(conversationId);
      if (!conversation) return state;

      const newConversationsMap = new Map(state.conversationsMap);

      // 如果是"回放对话"，阻止修改 title
      const finalUpdates = { ...updates };
      if (conversation.title === '回放对话' && updates.title !== undefined) {
        console.warn('[updateConversation] Cannot modify title of playback conversation');
        delete finalUpdates.title;
      }

      newConversationsMap.set(conversationId, {
        ...conversation,
        ...finalUpdates,
        updatedAt: Date.now(),
      });

      return {
        conversationsMap: newConversationsMap,
      };
    });
  },

  deleteConversation: async (conversationId: string) => {
    // 先卸载要删除的对话的数据（如果它是当前对话）
    const state = get();
    const isCurrentConversation = state.currentConversationId === conversationId;

    set((state) => {
      const conversation = state.conversationsMap.get(conversationId);
      if (!conversation) {
        console.warn('[deleteConversation] Conversation not found:', conversationId);
        return state;
      }

      const newConversationsMap = new Map(state.conversationsMap);
      const newMessageItemsMap = new Map(state.messageItemsMap);
      const newMessagesMap = new Map(state.messagesMap);

      // 级联删除 messageItems（如果已加载）
      conversation.messageItemsIds.forEach(itemsId => {
        const items = state.messageItemsMap.get(itemsId);
        if (items) {
          // 级联删除 messages
          items.messagesIds.forEach(msgId =>
            deleteMessageRecursively(msgId, newMessagesMap, state.messagesMap)
          );
        }
        newMessageItemsMap.delete(itemsId);
      });

      // 删除 conversation
      newConversationsMap.delete(conversationId);

      // 更新列表
      const newConversationsList = state.conversationsList.filter(id => id !== conversationId);

      // ===== 新增：清理 localStorage =====
      // 1. 删除对话数据
      const cacheKey = `${STORAGE_KEYS.CONVERSATION_DATA_PREFIX}${conversationId}`;
      try {
        localStorage.removeItem(cacheKey);
      } catch (error) {
        console.error('[deleteConversation] Failed to remove conversation data:', error);
      }

      // 2. 更新索引（删除后需要保存新的索引）
      try {
        const index: ConversationsIndex = {
          conversations: {},
          lastUpdated: Date.now(),
        };

        newConversationsList.forEach(id => {
          const conv = newConversationsMap.get(id);
          if (conv) {
            index.conversations[id] = {
              id: conv.id,
              title: conv.title,
              createdAt: conv.createdAt,
              updatedAt: conv.updatedAt,
              config: conv.config,
            };
          }
        });

        localStorage.setItem(STORAGE_KEYS.CONVERSATIONS_INDEX, JSON.stringify(index));
      } catch (error) {
        console.error('[deleteConversation] Failed to update index:', error);
      }

      // ===== 新增：如果删除的是当前对话，切换到最新的对话 =====
      let newCurrentConversationId = state.currentConversationId;
      if (state.currentConversationId === conversationId) {
        // 找到最新的对话（按 updatedAt 排序）
        const latestConversationId = newConversationsList.reduce<string | null>((latestId, id) => {
          const conv = newConversationsMap.get(id);
          if (!conv) return latestId;
          if (!latestId) return conv.id;
          const latestConv = newConversationsMap.get(latestId);
          return latestConv && conv.updatedAt > latestConv.updatedAt ? conv.id : latestId;
        }, null);

        newCurrentConversationId = latestConversationId;
      }

      return {
        conversationsMap: newConversationsMap,
        messageItemsMap: newMessageItemsMap,
        messagesMap: newMessagesMap,
        conversationsList: newConversationsList,
        currentConversationId: newCurrentConversationId,
      };
    });

    // ===== 从 IndexDB 删除对话（在 set 之后异步执行）=====
    try {
      await conversationDB.deleteConversation(conversationId);
    } catch (error) {
      console.error('[deleteConversation] Failed to delete from IndexDB:', error);
    }

    // ===== 如果删除的是当前对话且切换到了新对话，加载新对话的数据 =====
    if (isCurrentConversation) {
      const newState = get();
      if (newState.currentConversationId) {
        await get().loadConversationFullData(newState.currentConversationId);
      }
    }
  },

  // ========== MessageItems 操作函数 ==========

  addMessageItems: (messageItems: MessageItems, conversationId?: string) => {
    const targetConversationId = conversationId || get().currentConversationId;
    if (!targetConversationId) {
      console.warn('[addMessageItems] No conversation ID provided');
      return;
    }

    set((state) => {
      const conversation = state.conversationsMap.get(targetConversationId);
      if (!conversation) {
        console.warn('[addMessageItems] Conversation not found:', targetConversationId);
        return state;
      }

      const newMessageItemsMap = new Map(state.messageItemsMap);
      newMessageItemsMap.set(messageItems.id, messageItems);

      const newConversationsMap = new Map(state.conversationsMap);
      newConversationsMap.set(targetConversationId, {
        ...conversation,
        messageItemsIds: [...conversation.messageItemsIds, messageItems.id],
        updatedAt: Date.now(),
      });

      return {
        messageItemsMap: newMessageItemsMap,
        conversationsMap: newConversationsMap,
      };
    });
  },

  updateMessageItems: (messageItemsId: string, updates: Partial<MessageItems>) => {
    set((state) => {
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (!messageItems) {
        console.warn('[updateMessageItems] MessageItems not found:', messageItemsId);
        return state;
      }

      // 检查是否真的有变化
      const hasChanges = Object.keys(updates).some(key => {
        const updateValue = (updates as any)[key];
        const currentValue = (messageItems as any)[key];
        return JSON.stringify(updateValue) !== JSON.stringify(currentValue);
      });

      if (!hasChanges) return state;

      // 创建新的MessageItems对象
      const updatedMessageItems: MessageItems = {
        ...messageItems,
        ...updates,
        updatedAt: Date.now(),
      };

      const newMessageItemsMap = new Map(state.messageItemsMap);
      newMessageItemsMap.set(messageItemsId, updatedMessageItems);

      return {
        messageItemsMap: newMessageItemsMap,
      };
    });

    // 检查是否系统消息已结束（status 变为 COMPLETED/FAILED/CANCELLED）
    // 如果是，则触发保存到 IndexDB
    const messageItems = get().messageItemsMap.get(messageItemsId);
    if (
      messageItems &&
      !get().getMessageItemsIsUser(messageItems) &&  // 只保存系统消息（AI回复）
      updates.status &&
      [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.UNKNOWN].includes(updates.status)
    ) {
      get().saveConversationToDB(messageItems.conversationId);
    }
  },

  deleteMessageItems: (messageItemsId: string) => {
    set((state) => {
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (!messageItems) return state;

      const newMessageItemsMap = new Map(state.messageItemsMap);
      const newMessagesMap = new Map(state.messagesMap);

      // 级联删除 messages
      messageItems.messagesIds.forEach(msgId =>
        deleteMessageRecursively(msgId, newMessagesMap, state.messagesMap)
      );
      newMessageItemsMap.delete(messageItemsId);

      // 从 conversation 中移除
      const conversation = state.conversationsMap.get(messageItems.conversationId);
      if (conversation) {
        const newConversationsMap = new Map(state.conversationsMap);
        newConversationsMap.set(messageItems.conversationId, {
          ...conversation,
          messageItemsIds: conversation.messageItemsIds.filter(id => id !== messageItemsId),
          updatedAt: Date.now(),
        });

        return {
          messageItemsMap: newMessageItemsMap,
          messagesMap: newMessagesMap,
          conversationsMap: newConversationsMap,
        };
      }

      return {
        messageItemsMap: newMessageItemsMap,
        messagesMap: newMessagesMap,
      };
    });
  },

  // ========== Message 操作函数 ==========

  addUserMessage: (conversationId: string, content: string) => {
    // 检查内存大小
    get().checkMemorySize();

    // 检查是否是第一次提问，如果是则更新对话标题
    const conversation = get().conversationsMap.get(conversationId);
    const isFirstMessage = conversation && conversation.messageItemsIds.length === 0;

    const messageItemsId = get().generateMessageItemsId();
    const messageId = get().generateMessageId();

    const message: Message = {
      id: messageId,
      type: MessageType.REPORT,
      status: TaskStatus.COMPLETED,
      content,
      messageItemsId,
      conversationId,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    const messageItems: MessageItems = {
      id: messageItemsId,
      isUser: true,
      status: TaskStatus.COMPLETED,
      messagesIds: [messageId],
      conversationId,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    // 添加 message 到 messagesMap
    set((state) => {
      const newMessagesMap = new Map(state.messagesMap);
      newMessagesMap.set(messageId, message);
      return { messagesMap: newMessagesMap };
    });

    // 添加 messageItems
    get().addMessageItems(messageItems, conversationId);

    // 如果是第一次提问，更新对话标题为前20个字符
    if (isFirstMessage) {
      const newTitle = content.slice(0, 20);
      get().updateConversation(conversationId, { title: newTitle });
    }

    return messageItems;
  },

  addSystemMessage: (conversationId: string, type: MessageType, content: any, parentId?: string, title?: string, agentType?: string) => {
    const messageId = get().generateMessageId();

    // 查找当前正在进行中的MessageItems，如果没有则创建新的
    const currentMessageItemsList = get().getCurrentMessageItems();
    let lastMessageItems = currentMessageItemsList[currentMessageItemsList.length - 1];
    let messageItemsId: string;

    // 如果最后一个MessageItems是用户消息，或者不存在，创建新的系统MessageItems
    if (!lastMessageItems || get().getMessageItemsIsUser(lastMessageItems)) {
      messageItemsId = get().generateMessageItemsId();
      lastMessageItems = {
        id: messageItemsId,
        isUser: false,
        status: TaskStatus.IN_PROGRESS,
        messagesIds: [messageId],
        conversationId,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        agentType: agentType === 'deepsearch' ? AgentType.DEEPSEARCH : AgentType.ORDINARY,  // 保存 agent 类型到 MessageItems（用于HITL场景匹配）
      };

      get().addMessageItems(lastMessageItems, conversationId);
    } else {
      // 检查最后一个非用户 MessageItems 是否已被取消，如果是则不应该添加新消息
      if (lastMessageItems.status === TaskStatus.CANCELLED) {
        console.log('[addSystemMessage] MessageItems is cancelled, skipping adding message');
        return null;
      }
      messageItemsId = lastMessageItems.id;
      // 添加到现有的MessageItems
      const newMessageItemsMap = new Map(get().messageItemsMap);
      const existingItems = newMessageItemsMap.get(lastMessageItems.id);
      if (existingItems) {
        newMessageItemsMap.set(lastMessageItems.id, {
          ...existingItems,
          messagesIds: [...existingItems.messagesIds, messageId],
          updatedAt: Date.now(),
          // 如果传入了 agentType 且当前 MessageItems 没有 agentType，则保存
          ...(agentType && !existingItems.agentType ? { agentType: agentType === 'deepsearch' ? AgentType.DEEPSEARCH : AgentType.ORDINARY } : {}),
        });
        set({ messageItemsMap: newMessageItemsMap });
      }
    }

    // 创建包含外键字段的 message
    const message: Message = {
      id: messageId,
      type,
      status: TaskStatus.IN_PROGRESS,
      content,
      title,
      messageItemsId,
      conversationId,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isStreaming: true,
      parentMessageId: parentId,
      childMessageIds: type === MessageType.TASK ? [] : undefined,
    };

    // 添加 message 到 messagesMap
    set((state) => {
      const newMessagesMap = new Map(state.messagesMap);
      newMessagesMap.set(messageId, message);
      return { messagesMap: newMessagesMap };
    });

    return message;
  },

  addMessage: (messageItemsId: string, message: Message, isRootMessage = true) => {
    set((state) => {
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (!messageItems) {
        console.warn('[addMessage] MessageItems not found:', messageItemsId);
        return state;
      }

      const newMessagesMap = new Map(state.messagesMap);
      // 更新外键字段
      const updatedMessage: Message = {
        ...message,
        messageItemsId,
        conversationId: messageItems.conversationId,
      };
      newMessagesMap.set(message.id, updatedMessage);

      const newMessageItemsMap = new Map(state.messageItemsMap);
      if (isRootMessage) {
        newMessageItemsMap.set(messageItemsId, {
          ...messageItems,
          messagesIds: [...messageItems.messagesIds, message.id],
          updatedAt: Date.now(),
        });
      } else {
        newMessageItemsMap.set(messageItemsId, {
          ...messageItems,
          updatedAt: Date.now(),
        });
      }

      return {
        messagesMap: newMessagesMap,
        messageItemsMap: newMessageItemsMap,
      };
    });
  },

  updateMessage: (messageItemsId: string, messageId: string, updates: Partial<Message>) => {
    set((state) => {
      const existingMessage = state.messagesMap.get(messageId);
      if (!existingMessage) {
        console.warn('[updateMessage] Message not found:', messageId);
        return state;
      }

      // ===== 前处理：根据子 message 的状态调整 status =====
      let finalUpdates = { ...updates };

      if (updates.status) {
        // 获取子 message
        const childMessages = existingMessage.childMessageIds
          ?.map(id => state.messagesMap.get(id))
          .filter((msg): msg is Message => msg !== undefined) || [];

        // 根据不同的传入 status 进行调整
        switch (updates.status) {
          case TaskStatus.UNKNOWN:
            // 优先级：FAILED > CANCELLED > 保持 UNKNOWN
            if (childMessages.some(child => child.status === TaskStatus.FAILED)) {
              finalUpdates.status = TaskStatus.FAILED;
            } else if (childMessages.some(child => child.status === TaskStatus.CANCELLED)) {
              finalUpdates.status = TaskStatus.CANCELLED;
            }
            // 其他情况保持 UNKNOWN
            break;

          case TaskStatus.COMPLETED:
            // 优先级：FAILED > CANCELLED > UNKNOWN > 保持 COMPLETED
            if (childMessages.some(child => child.status === TaskStatus.FAILED)) {
              finalUpdates.status = TaskStatus.FAILED;
            } else if (childMessages.some(child => child.status === TaskStatus.CANCELLED)) {
              finalUpdates.status = TaskStatus.CANCELLED;
            } else if (childMessages.some(child =>
              child.status === TaskStatus.PENDING ||
              child.status === TaskStatus.IN_PROGRESS ||
              child.status === TaskStatus.UNKNOWN
            )) {
              finalUpdates.status = TaskStatus.UNKNOWN;
            }
            // 其他情况保持 COMPLETED
            break;

          // PENDING / IN_PROGRESS / FAILED / CANCELLED 保持不变
          default:
            break;
        }

        // 在根消息的直接子消息状态变为终态时，保存到 IndexDB
        // 条件：1. 是子消息（有 parentMessageId）
        //       2. 父消息是根消息（父消息没有 parentMessageId）
        //       3. 状态变为 COMPLETED/FAILED/CANCELLED（非 PENDING/IN_PROGRESS）
        //       4. 状态确实发生了变化
        if (
          existingMessage.parentMessageId &&  // 是子消息
          finalUpdates.status &&
          ![TaskStatus.PENDING, TaskStatus.IN_PROGRESS].includes(finalUpdates.status) &&
          finalUpdates.status !== existingMessage.status  // 状态确实发生了变化
        ) {
          // 检查父消息是否是根消息
          const parentMessage = state.messagesMap.get(existingMessage.parentMessageId);
          if (parentMessage && !parentMessage.parentMessageId) {  // 父消息是根消息
            const messageItems = state.messageItemsMap.get(messageItemsId);
            if (messageItems && !get().getMessageItemsIsUser(messageItems)) {
              // 异步保存，不阻塞当前流程
              get().saveConversationToDB(messageItems.conversationId);
            }
          }
        }
      }

      // 创建新的Message对象
      const updatedMessage: Message = {
        ...existingMessage,
        ...finalUpdates,
        updatedAt: Date.now(),
      };

      const newMessagesMap = new Map(state.messagesMap);
      newMessagesMap.set(messageId, updatedMessage);

      // 更新 messageItems 时间戳
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (messageItems) {
        const updatedMessageItems: MessageItems = {
          ...messageItems,
          updatedAt: Date.now(),
        };

        const newMessageItemsMap = new Map(state.messageItemsMap);
        newMessageItemsMap.set(messageItemsId, updatedMessageItems);

        return {
          messagesMap: newMessagesMap,
          messageItemsMap: newMessageItemsMap,
        };
      }

      return {
        messagesMap: newMessagesMap,
      };
    });
  },

  deleteMessage: (messageItemsId: string, messageId: string) => {
    set((state) => {
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (!messageItems) return state;

      const newMessagesMap = new Map(state.messagesMap);

      // 递归删除子消息
      deleteMessageRecursively(messageId, newMessagesMap, state.messagesMap);

      // 更新 messageItems
      const updatedMessageItems: MessageItems = {
        ...messageItems,
        messagesIds: messageItems.messagesIds.filter(id => id !== messageId),
        updatedAt: Date.now(),
      };

      const newMessageItemsMap = new Map(state.messageItemsMap);
      newMessageItemsMap.set(messageItemsId, updatedMessageItems);

      // 从父消息的 childMessageIds 中移除
      const message = state.messagesMap.get(messageId);
      if (message?.parentMessageId) {
        const parentMessage = newMessagesMap.get(message.parentMessageId);
        if (parentMessage?.childMessageIds) {
          const updatedParent: Message = {
            ...parentMessage,
            childMessageIds: parentMessage.childMessageIds.filter(id => id !== messageId),
            updatedAt: Date.now(),
          };
          newMessagesMap.set(message.parentMessageId, updatedParent);
        }
      }

      return {
        messagesMap: newMessagesMap,
        messageItemsMap: newMessageItemsMap,
      };
    });
  },

  appendMessageContent: (messageItemsId: string, messageId: string, content: string) => {
    set((state) => {
      const existingMessage = state.messagesMap.get(messageId);
      if (!existingMessage) {
        console.warn('[appendMessageContent] Message not found:', messageId);
        return state;
      }

      if (!content || content.length === 0) return state;

      // 创建新的Message对象
      const currentContent = typeof existingMessage.content === 'string' ? existingMessage.content : '';
      const updatedMessage: Message = {
        ...existingMessage,
        content: currentContent + content,
        updatedAt: Date.now(),
      };

      const newMessagesMap = new Map(state.messagesMap);
      newMessagesMap.set(messageId, updatedMessage);

      // 更新 messageItems 时间戳
      const messageItems = state.messageItemsMap.get(messageItemsId);
      if (messageItems) {
        const updatedMessageItems: MessageItems = {
          ...messageItems,
          updatedAt: Date.now(),
        };

        const newMessageItemsMap = new Map(state.messageItemsMap);
        newMessageItemsMap.set(messageItemsId, updatedMessageItems);

        return {
          messagesMap: newMessagesMap,
          messageItemsMap: newMessageItemsMap,
        };
      }

      return {
        messagesMap: newMessagesMap,
      };
    });
  },

  addMessageAsChild: (messageItemsId: string, parentId: string, type: MessageType, content: any, title?: string) => {
    const messageId = get().generateMessageId();

    // 获取 messageItems 以获得 conversationId
    const messageItems = get().messageItemsMap.get(messageItemsId);
    if (!messageItems) {
      console.error('[addMessageAsChild] MessageItems not found:', messageItemsId);
      throw new Error(`MessageItems not found: ${messageItemsId}`);
    }

    const newMessage: Message = {
      id: messageId,
      type,
      status: TaskStatus.IN_PROGRESS,
      content,
      title,
      messageItemsId,
      conversationId: messageItems.conversationId,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      isStreaming: false,
      parentMessageId: parentId,
      childMessageIds: type === MessageType.TASK ? [] : undefined,
    };

    set((state) => {
      // 1. 添加新消息到 messagesMap
      const newMessagesMap = new Map(state.messagesMap);
      newMessagesMap.set(messageId, newMessage);

      // 2. 更新父消息的 childMessageIds
      const parentMessage = newMessagesMap.get(parentId);
      if (!parentMessage) {
        console.error('[addMessageAsChild] Parent message not found:', parentId);
        return state;
      }

      const updatedParent: Message = {
        ...parentMessage,
        childMessageIds: [...(parentMessage.childMessageIds || []), messageId],
        updatedAt: Date.now(),
      };

      newMessagesMap.set(parentId, updatedParent);

      // 3. 更新 messageItemsMap 的时间戳
      const newMessageItemsMap = new Map(state.messageItemsMap);
      const items = newMessageItemsMap.get(messageItemsId);
      if (items) {
        newMessageItemsMap.set(messageItemsId, {
          ...items,
          updatedAt: Date.now(),
        });
      }

      return {
        messagesMap: newMessagesMap,
        messageItemsMap: newMessageItemsMap,
      };
    });

    return newMessage;
  },

  // ========== 流式消息处理 =====

  handleSSEMessage: (sseData: JSONObject, conversationId: string, agentType: string = 'deepsearch') => {
    // 将事件添加到队列
    set((state) => ({
      sseEventQueue: [...state.sseEventQueue, { sseData, conversationId, agentType }],
    }));

    // 如果当前没有在处理队列，则开始处理
    const state = get();
    if (!state.sseProcessingQueue) {
      get().processSSEQueue();
    }
  },

  processSSEQueue: () => {
    const state = get();
    if (state.sseEventQueue.length === 0) {
      // 队列为空，停止处理
      set({ sseProcessingQueue: false });
      return;
    }

    // 标记正在处理队列
    set({ sseProcessingQueue: true });

    // 使用requestAnimationFrame批量处理
    const BATCH_SIZE = 10; // 每批处理10个事件

    const processBatch = () => {
      const currentState = get();
      const eventsToProcess = currentState.sseEventQueue.slice(0, BATCH_SIZE);

      if (eventsToProcess.length === 0) {
        // 队列为空，准备重置处理状态
        // 但在重置前，先检查是否有新事件到达（处理 race condition）
        requestAnimationFrame(() => {
          const nextState = get();
          if (nextState.sseEventQueue.length > 0) {
            // 有新事件到达，继续处理（保持 sseProcessingQueue 为 true）
            get().processSSEQueue();
          } else {
            // 确认没有新事件，安全重置处理状态
            set({ sseProcessingQueue: false });
          }
        });
        return;
      }

      // 获取当前 MessageItems
      const getCurrentMessageItems = () => {
        const currentList = get().getCurrentMessageItems();
        return currentList[currentList.length - 1];
      };

      // 动态导入 deepsearch 处理器
      import('./handlers/deepsearchSSEHandler').then(({ DeepsearchSSEHandler }) => {
        const handler = new DeepsearchSSEHandler(
          {
            getCurrentMessageItems: getCurrentMessageItems,
            addSystemMessage: get().addSystemMessage,
            addMessageAsChild: get().addMessageAsChild,
            updateMessage: get().updateMessage,
            deleteMessage: get().deleteMessage,
            updateMessageItems: get().updateMessageItems,
            appendMessageContent: get().appendMessageContent,
            getMessageById: get().getMessageById,
            getMessageTree: get().getMessageTree,
            getChildMessages: get().getChildMessages,
            getMessageItemsIsUser: get().getMessageItemsIsUser,
            setSessionConversationId: get().setSessionConversationId,
          },
          {
            get: (key: string) => get().sseStreamCache.get(key),
            set: (key: string, chunks: string[]) => {
              set((state) => {
                const newCache = new Map(state.sseStreamCache);
                newCache.set(key, chunks);
                return { sseStreamCache: newCache };
              });
            },
            delete: (key: string) => {
              set((state) => {
                const newCache = new Map(state.sseStreamCache);
                newCache.delete(key);
                return { sseStreamCache: newCache };
              });
            },
          },
          eventsToProcess[0].conversationId
        );

        // 批量处理事件
        eventsToProcess.forEach(event => {
          // 在处理每个事件之前，检查是否已取消
          const currentMessageItems = getCurrentMessageItems();
          if (currentMessageItems && currentMessageItems.status === TaskStatus.CANCELLED) {
            console.log('[SSE Processor] MessageItems cancelled during processing, skipping event');
            return;  // 跳过此事件
          }
          // 使用类型断言，因为 useConversationStore 不应该知道具体的 SSE 数据结构
          handler.handleSSEMessage(event.sseData as any);
        });

        // 从队列中移除已处理的事件
        set((state) => ({
          sseEventQueue: state.sseEventQueue.slice(eventsToProcess.length),
        }));

        // 继续处理下一批
        requestAnimationFrame(processBatch);
      }).catch((error) => {
        console.error('[processSSEQueue] Failed to load deepsearch handler:', error);

        // 降级处理：批量创建简单的文本消息
        eventsToProcess.forEach(event => {
          const sseData = event.sseData as any;
          if (sseData.event === 'start' || sseData.event === 'message') {
            get().addSystemMessage(event.conversationId, MessageType.REPORT, sseData.content || '');
          }
        });

        // 从队列中移除失败的事件，继续处理下一批
        set((state) => ({
          sseEventQueue: state.sseEventQueue.slice(eventsToProcess.length),
        }));
        requestAnimationFrame(processBatch);
      });
    };

    requestAnimationFrame(processBatch);
  },

  // ========== 状态管理 ==========

  setLoading: (loading: boolean) => {
    set({ isLoading: loading });
  },

  clearCurrentConversation: () => {
    set({
      currentConversationId: null,
    });
  },

  clearAll: async () => {
    // 清空内存
    set({
      conversationsMap: new Map<string, Conversation>(),
      messageItemsMap: new Map<string, MessageItems>(),
      messagesMap: new Map<string, Message>(),
      currentConversationId: null,
      conversationsList: [],
      isLoading: false,
      selectedResultMessageId: null,
      sseStreamCache: new Map<string, string[]>(),
      sseEventQueue: [],
      sseProcessingQueue: false,
    });

    // 清空 IndexDB
    try {
      await conversationDB.clearAll();
    } catch (error) {
      console.error('[clearAll] Failed to clear IndexDB:', error);
    }
  },

  setSelectedResultMessageId: (messageId: string | null) => {
    set({ selectedResultMessageId: messageId });
  },

  // ===== 辅助方法 =====

  generateMessageId: (sectionIdx?: number, planIdx?: number, stepIdx?: number, ...extra: number[]) => {
    // 如果没有提供层级信息，使用随机ID
    if (sectionIdx === undefined) {
      return `msg_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
    }

    // 生成层级ID：task_1[_section][_plan][_step][_extra...]
    const parts = ['task', '1', sectionIdx];
    if (planIdx !== undefined) parts.push(planIdx);
    if (stepIdx !== undefined) parts.push(stepIdx);
    if (extra.length > 0) parts.push(...extra);

    return parts.join('_');
  },

  generateMessageItemsId: () => {
    return `items_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  },

  generateConversationId: () => {
    return `conv_${Date.now()}_${Math.random().toString(36).substring(2, 11)}`;
  },

  debugLogMessageItems: (messageItemsId?: string, label?: string) => {
    const state = get();
    const targetId = messageItemsId || state.currentConversationId;
    if (!targetId) {
      console.log('[debugLogMessageItems] No messageItemsId provided and no current conversation');
      return;
    }

    const messageItems = state.messageItemsMap.get(targetId);
    if (!messageItems) {
      console.log('[debugLogMessageItems] MessageItems not found:', targetId);
      return;
    }

    const logLabel = label || 'MessageItems';
    console.log(`[${logLabel}] ===== 开始打印 =====`);
    console.log(`[${logLabel}] ID:`, messageItems.id);
    console.log(`[${logLabel}] Status:`, messageItems.status);
    console.log(`[${logLabel}] Total messages:`, messageItems.messagesIds.length);

    // 递归格式化消息树
    const formatMessageTree = (messageId: string, indent: string = ''): string => {
      const message = state.messagesMap.get(messageId);
      if (!message) return `${indent}├─ Message not found: ${messageId}\n`;

      const contentPreview = typeof message.content === 'string'
        ? (message.content.length > 50 ? message.content.substring(0, 50) + '...' : message.content)
        : JSON.stringify(message.content).substring(0, 50) + '...';

      const info = [
        `${indent}├─ Message [${message.id}]`,
        `${indent}   type: ${message.type}`,
        `${indent}   title: ${message.title || '(无标题)'}`,
        `${indent}   status: ${message.status}`,
        `${indent}   content: ${contentPreview}`,
        `${indent}   children: ${message.childMessageIds?.length || 0}`,
      ];

      // 递归打印子消息
      let childInfo = '';
      if (message.childMessageIds && message.childMessageIds.length > 0) {
        childInfo = message.childMessageIds
          .map(childId => formatMessageTree(childId, indent + '  │'))
          .join('\n');
      }

      return [...info, childInfo].filter(Boolean).join('\n');
    };

    // 打印所有顶层消息
    messageItems.messagesIds.forEach((msgId, index) => {
      console.log(`\n[${logLabel}] --- Message ${index + 1} ---`);
      console.log(formatMessageTree(msgId, ''));
    });

    console.log(`\n[${logLabel}] ===== 打印完成 =====`);
  },

  debugLogConversation: (conversationId?: string) => {
    const state = get();
    const targetId = conversationId || state.currentConversationId;
    if (!targetId) {
      console.log('[debugLogConversation] No conversationId provided and no current conversation');
      return;
    }

    const conversation = state.conversationsMap.get(targetId);
    if (!conversation) {
      console.log('[debugLogConversation] Conversation not found:', targetId);
      return;
    }

    const logLabel = `Conversation[${targetId}]`;
    console.log(`[${logLabel}] ===== 开始打印 =====`);
    console.log(`[${logLabel}] ID:`, conversation.id);
    console.log(`[${logLabel}] Title:`, conversation.title);
    console.log(`[${logLabel}] Created:`, new Date(conversation.createdAt).toLocaleString());
    console.log(`[${logLabel}] Updated:`, new Date(conversation.updatedAt).toLocaleString());
    console.log(`[${logLabel}] Config:`, conversation.config);
    console.log(`[${logLabel}] MessageItems count:`, conversation.messageItemsIds.length);

    // 打印所有 MessageItems
    conversation.messageItemsIds.forEach((itemsId, index) => {
      console.log(`\n[${logLabel}] --- MessageItems ${index + 1} ---`);
      get().debugLogMessageItems(itemsId, `${logLabel}-Items${index}`);
    });

    console.log(`\n[${logLabel}] ===== 打印完成 =====`);
  },

  checkMemorySize: () => {
    if (typeof window === 'undefined') return;

    try {
      const state = get();
      const WARNING_THRESHOLD = 50 * 1024 * 1024; // 50MB in bytes

      // 使用更轻量的估算方法
      const estimateSize = (obj: any): number => {
        if (obj === null || obj === undefined) return 0;
        if (typeof obj === 'string') return obj.length * 2; // UTF-16
        if (typeof obj === 'number') return 8;
        if (typeof obj === 'boolean') return 4;
        if (obj instanceof Date) return 24;

        if (Array.isArray(obj)) {
          return obj.reduce((sum, item) => sum + estimateSize(item), 0) + 16; // 数组开销
        }

        if (obj instanceof Map) {
          let size = 16; // Map开销
          obj.forEach((value, key) => {
            size += estimateSize(key) + estimateSize(value) + 16; // entry开销
          });
          return size;
        }

        if (typeof obj === 'object') {
          let size = 16; // 对象开销
          for (const key in obj) {
            if (obj.hasOwnProperty(key)) {
              size += estimateSize(key) + estimateSize(obj[key]) + 16;
            }
          }
          return size;
        }

        return 0;
      };

      // 计算各个 Map 的大小
      const conversationsSize = estimateSize(state.conversationsMap);
      const messageItemsSize = estimateSize(state.messageItemsMap);
      const messagesSize = estimateSize(state.messagesMap);

      const totalSize = conversationsSize + messageItemsSize + messagesSize;
      const totalSizeInMB = totalSize / (1024 * 1024);

      // 打印当前内存使用情况
      console.log('[Memory Usage] Conversation data in memory:', {
        conversations: {
          count: state.conversationsMap.size,
          bytes: conversationsSize,
          mb: (conversationsSize / (1024 * 1024)).toFixed(2),
        },
        messageItems: {
          count: state.messageItemsMap.size,
          bytes: messageItemsSize,
          mb: (messageItemsSize / (1024 * 1024)).toFixed(2),
        },
        messages: {
          count: state.messagesMap.size,
          bytes: messagesSize,
          mb: (messagesSize / (1024 * 1024)).toFixed(2),
        },
        total: {
          bytes: totalSize,
          mb: totalSizeInMB.toFixed(2),
          thresholdMB: (WARNING_THRESHOLD / (1024 * 1024)).toFixed(2),
        },
      });

      // 如果超过阈值，打印警告
      if (totalSize > WARNING_THRESHOLD) {
        console.warn(
          `[Memory Warning] ⚠️ Conversation data size (${totalSizeInMB.toFixed(2)}MB) exceeds 100MB threshold! ` +
          `Consider clearing old conversations to free up memory.`
        );
      }
    } catch (error) {
      console.error('[checkMemorySize] Failed to calculate memory size:', error);
    }
  },

  /**
   * 检查创建新对话前是否需要警告
   * 返回警告信息，如果不需要警告则返回 null
   */
  checkCreateConversationWarning: async () => {
    try {
      const result = await conversationDB.checkLimitWarning();
      return result;
    } catch (error) {
      console.error('[checkCreateConversationWarning] Failed to check warning:', error);
      return null;
    }
  },

  /**
   * 获取 MessageItems 的 isUser 属性（兼容历史数据）
   * 历史数据中 isUser 在 config 中，新数据直接在顶层
   */
  getMessageItemsIsUser: (messageItems: MessageItems) => {
    // 新数据：直接在顶层
    if ('isUser' in messageItems) {
      return messageItems.isUser;
    }
    // 历史数据：在 config 中（如果存在 config 对象）
    if ((messageItems as any).config && typeof (messageItems as any).config === 'object' && 'isUser' in (messageItems as any).config) {
      return (messageItems as any).config.isUser;
    }
    // 默认为 false（系统消息）
    console.warn('[getMessageItemsIsUser] Cannot determine isUser, defaulting to false (system message)', messageItems);
    return false;
  },

  // ========== IndexDB 持久化 ==========

  /**
   * 保存对话到 IndexDB
   * 在系统消息（AI回复）结束时调用
   */
  saveConversationToDB: async (conversationId: string) => {
    try {
      const state = get();
      const conversation = state.conversationsMap.get(conversationId);

      if (!conversation) {
        console.warn('[saveConversationToDB] Conversation not found:', conversationId);
        return;
      }

      // 获取对话的完整数据
      const conversationData = state.getConversationData(conversationId);

      if (!conversationData) {
        console.warn('[saveConversationToDB] Failed to get conversation data:', conversationId);
        return;
      }

      // 保存到 IndexDB
      await conversationDB.saveConversation(conversationData);
    } catch (error) {
      console.error('[saveConversationToDB] Failed to save conversation:', error);
    }
  },

  /**
   * 获取或创建回放专用对话
   * - 如果存在标题为"回放对话"的对话，返回其 ID
   * - 如果不存在，创建一个新的"回放对话"并返回其 ID
   */
  getOrCreatePlaybackConversation: (): string => {
    const state = get();

    // 查找已存在的"回放对话"
    for (const [id, conversation] of state.conversationsMap) {
      if (conversation.title === '回放对话') {
        return id;
      }
    }

    // 不存在则创建新的"回放对话"
    const conversationId = get().generateConversationId();
    const conversation: Conversation = {
      id: conversationId,
      title: '回放对话',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      config: { agentType: 'deepsearch' },
      messageItemsIds: [],
    };

    set((state) => {
      const newConversationsMap = new Map(state.conversationsMap);
      newConversationsMap.set(conversationId, conversation);

      return {
        conversationsMap: newConversationsMap,
        conversationsList: [...state.conversationsList, conversationId],
        currentConversationId: conversationId,
      };
    });

    return conversationId;
  },

  /**
   * 从 IndexDB 初始化对话数据
   * 只在内存中没有数据时才加载
   * 优化：只加载对话列表基本信息，不加载完整数据
   */
  initializeFromDB: async () => {
    try {
      const state = get();

      // 如果内存中已有数据，不加载
      if (state.conversationsList.length > 0) {
        return;
      }

      // 从 IndexDB 加载对话基本信息（不包含 messageItems 和 messages）
      const basicInfoList = await conversationDB.getAllConversationsBasicInfo();

      if (basicInfoList.length === 0) {
        return;
      }

      // 恢复基本数据到内存
      set((state) => {
        const newConversationsMap = new Map(state.conversationsMap);
        const newConversationsList: string[] = [];

        // 只恢复对话基本信息
        basicInfoList.forEach((info) => {
          newConversationsMap.set(info.id, {
            id: info.id,
            title: info.title,
            createdAt: info.createdAt,
            updatedAt: info.updatedAt,
            config: info.config,
            messageItemsIds: [], // 基本信息不包含 messageItems，留空
          });
          newConversationsList.push(info.id);
        });

        return {
          conversationsMap: newConversationsMap,
          conversationsList: newConversationsList,
        };
      });

      // 自动加载最新对话的完整数据
      const latestConversationId = basicInfoList[0]?.id;
      if (latestConversationId) {
        await get().loadConversationFullData(latestConversationId);
        // 设置为当前对话
        set({ currentConversationId: latestConversationId });
      }
    } catch (error) {
      console.error('[initializeFromDB] Failed to initialize from IndexDB:', error);
    }
  },

  /**
   * 加载单个对话的完整数据（包含 messageItems 和 messages）
   * 用于切换对话时懒加载
   */
  loadConversationFullData: async (conversationId: string) => {
    try {
      // 从 IndexDB 获取完整数据
      const doc = await conversationDB.getConversation(conversationId);

      if (!doc) {
        console.warn('[loadConversationFullData] Conversation not found in IndexDB:', conversationId);
        return;
      }

      set((state) => {
        // 恢复 messageItems
        const newMessageItemsMap = new Map(state.messageItemsMap);
        doc.messageItems.forEach((items) => {
          newMessageItemsMap.set(items.id, items);
        });

        // 恢复 messages
        const newMessagesMap = new Map(state.messagesMap);
        Object.entries(doc.messages).forEach(([msgId, msg]) => {
          newMessagesMap.set(msgId, msg);
        });

        // 更新 conversation 的 messageItemsIds
        const newConversationsMap = new Map(state.conversationsMap);
        const existingConversation = newConversationsMap.get(conversationId);
        if (existingConversation) {
          newConversationsMap.set(conversationId, {
            ...existingConversation,
            messageItemsIds: doc.messageItems.map(items => items.id),
          });
        }

        return {
          messageItemsMap: newMessageItemsMap,
          messagesMap: newMessagesMap,
          conversationsMap: newConversationsMap,
        };
      });
    } catch (error) {
      console.error('[loadConversationFullData] Failed to load conversation:', error);
    }
  },

  /**
   * 卸载当前对话的详细数据（messageItems 和 messages）
   * 保留基本信息，释放内存
   */
  unloadCurrentConversation: () => {
    const state = get();
    const { currentConversationId, conversationsMap } = state;

    if (!currentConversationId) {
      return;
    }

    const conversation = conversationsMap.get(currentConversationId);
    if (!conversation) {
      console.warn('[unloadCurrentConversation] Current conversation not found:', currentConversationId);
      return;
    }

    set((state) => {
      // 删除当前对话的所有 messageItems
      const newMessageItemsMap = new Map(state.messageItemsMap);
      conversation.messageItemsIds.forEach((itemsId) => {
        newMessageItemsMap.delete(itemsId);
      });

      // 删除属于当前对话的所有 messages
      // 先收集要删除的 messageId，因为不能在遍历Map时删除
      const messageIdsToDelete: string[] = [];
      state.messagesMap.forEach((msg, msgId) => {
        if (msg.conversationId === currentConversationId) {
          messageIdsToDelete.push(msgId);
        }
      });

      // 删除收集到的消息
      const newMessagesMap = new Map(state.messagesMap);
      messageIdsToDelete.forEach(msgId => {
        newMessagesMap.delete(msgId);
      });

      return {
        messageItemsMap: newMessageItemsMap,
        messagesMap: newMessagesMap,
      };
    });
  },

  // ========== SSE超时监控方法 ==========

  /**
   * 启动SSE超时监控
   */
  startSSETimeoutMonitor: (conversationId: string) => {
    // 先清理旧的监控
    get().stopSSETimeoutMonitor();

    // 记录开始时间
    const startTime = Date.now();
    set({ lastSSEEventTime: startTime });

    // 设置定时检查（每30秒检查一次）
    const CHECK_INTERVAL_MS = 30 * 1000;  // 30秒
    const timeoutMs = SSE_TIMEOUT_MINUTES * 60 * 1000;

    let checkCount = 0;
    const intervalId = window.setInterval(() => {
      checkCount++;
      const { lastSSEEventTime, currentConversationId } = get();
      const timeSinceLastEvent = lastSSEEventTime ? Date.now() - lastSSEEventTime : 0;

      // 如果当前对话已切换，停止监控
      if (currentConversationId !== conversationId) {
        get().stopSSETimeoutMonitor();
        return;
      }

      // 检查是否超时
      if (lastSSEEventTime && timeSinceLastEvent > timeoutMs) {
        // 标记未完成消息为失败，并添加超时错误消息
        get().markCurrentConversationIncompleteAsFailed({
          title: i18n.t('common.messages.sse.timeoutError.title'),
          content: i18n.t('common.messages.sse.timeoutError.content'),
        });
        // 停止监控
        get().stopSSETimeoutMonitor();
      }
    }, CHECK_INTERVAL_MS);

    set({ sseTimeoutCheckInterval: intervalId });
  },

  /**
   * 停止SSE超时监控
   */
  stopSSETimeoutMonitor: () => {
    const { sseTimeoutCheckInterval } = get();
    if (sseTimeoutCheckInterval !== null) {
      window.clearInterval(sseTimeoutCheckInterval);
      set({ sseTimeoutCheckInterval: null });
    }
  },

  /**
   * 更新最后SSE事件时间
   */
  updateLastSSEEventTime: () => {
    set({ lastSSEEventTime: Date.now() });
  },

  /**
   * 检查并标记当前对话中未完成的MessageItems为FAILED
   */
  checkAndMarkIncompleteAsFailed: () => {
    const { currentConversationId } = get();
    if (!currentConversationId) {
      return false;
    }

    const messageItemsList = get().getCurrentMessageItems();
    if (messageItemsList.length === 0) {
      return false;
    }

    // 检查最后一个MessageItems
    const lastMessageItems = messageItemsList[messageItemsList.length - 1];

    // 如果是用户消息，不需要检查
    if (get().getMessageItemsIsUser(lastMessageItems)) {
      return false;
    }

    // 检查状态是否为 PENDING 或 IN_PROGRESS
    if (lastMessageItems.status === TaskStatus.PENDING ||
        lastMessageItems.status === TaskStatus.IN_PROGRESS) {
      console.warn('[SSE Timeout] 检测到超时的未完成消息，标记为FAILED');
      get().markCurrentConversationIncompleteAsFailed();
      return true;
    }

    return false;
  },

  /**
   * 标记当前对话中最后一个MessageItems（及其所有未完成的消息）为FAILED
   * @param errorMessage 可选的错误消息配置，如果提供则添加错误消息到MessageItems中
   */
  markCurrentConversationIncompleteAsFailed: (errorMessage?: ErrorMessageConfig | null) => {
    const { currentConversationId } = get();
    if (!currentConversationId) {
      return;
    }

    const messageItemsList = get().getCurrentMessageItems();
    if (messageItemsList.length === 0) {
      return;
    }

    const lastMessageItems = messageItemsList[messageItemsList.length - 1];

    // 动态导入 handler
    import('./handlers/deepsearchSSEHandler').then(({ DeepsearchSSEHandler }) => {
      const handler = new DeepsearchSSEHandler(
        // 传入空的 dependencies，我们只使用 markAllIncompleteMessages 方法
        {} as any,
        {} as any,
        lastMessageItems.conversationId
      );
      // 调用公共方法标记为失败
      handler.markAllIncompleteMessages(lastMessageItems, false);  // false = 标记为 FAILED

      // 添加错误消息（如果提供）
      if (errorMessage) {
        const errorMsg: Message = {
          id: get().generateMessageId(),
          type: MessageType.ERROR,
          status: TaskStatus.FAILED,
          content: errorMessage.content,
          title: errorMessage.title,
          messageItemsId: lastMessageItems.id,
          conversationId: lastMessageItems.conversationId,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        get().addMessage(lastMessageItems.id, errorMsg, true);
        // 手动保存到 IndexDB
        get().saveConversationToDB(lastMessageItems.conversationId);
      }
    }).catch((error) => {
      console.error('[markCurrentConversationIncompleteAsFailed] Failed to load handler:', error);

      // 降级处理: 直接遍历所有消息并标记
      const markRecursively = (messageId: string) => {
        const msg = get().getMessageById(messageId);
        if (!msg) return;

        // 递归处理子消息
        if (msg.childMessageIds) {
          msg.childMessageIds.forEach(childId => markRecursively(childId));
        }

        // 标记未完成的消息
        if (msg.status === TaskStatus.PENDING || msg.status === TaskStatus.IN_PROGRESS) {
          get().updateMessage(lastMessageItems.id, msg.id, { status: TaskStatus.FAILED });
        }
      };

      lastMessageItems.messagesIds.forEach(msgId => markRecursively(msgId));

      // 更新 MessageItems 状态
      get().updateMessageItems(lastMessageItems.id, { status: TaskStatus.FAILED });

      // 添加错误消息（如果提供）
      if (errorMessage) {
        const errorMsg: Message = {
          id: get().generateMessageId(),
          type: MessageType.ERROR,
          status: TaskStatus.FAILED,
          content: errorMessage.content,
          title: errorMessage.title,
          messageItemsId: lastMessageItems.id,
          conversationId: lastMessageItems.conversationId,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        get().addMessage(lastMessageItems.id, errorMsg, true);
        // 手动保存到 IndexDB
        get().saveConversationToDB(lastMessageItems.conversationId);
      }
    });
  },

  /**
   * 设置 SESSION_CONVERSATION_ID
   */
  setSessionConversationId: (conversationId: string | null) => {
    set({ SESSION_CONVERSATION_ID: conversationId });
  },

  triggerOutlineInteractionAccept: (messageId: string, userMessage: string, backendMessage?: string, interruptFeedback: string = 'accepted') => {
    set({ pendingOutlineInteraction: { messageId, userMessage, backendMessage, interruptFeedback } });
  },

  clearPendingOutlineInteraction: () => {
    set({ pendingOutlineInteraction: null });
  },

  /**
   * 更新当前 MessageItems 状态为 CANCELLED（用于 DeepSearch 取消功能）
   * 同时更新所有子消息的状态，确保 UI 正确显示取消状态
   * 如果没有 MessageItems（SSE 还未返回数据），会创建一个 CANCELLED 状态的 INTERRUPT 消息
   * 如果没有 INTERRUPT 消息，会创建一个 CANCELLED 状态的 INTERRUPT 消息用于显示取消提示
   */
  updateMessageItemsStatusToCancelled: () => {
    const { getCurrentMessageItems, updateMessageItems, updateMessage, getMessageById, getChildMessages, getCurrentConversation, saveConversationToDB, addMessageItems } = get();
    const messageItems = getCurrentMessageItems();

    // 清空 SSE 队列，防止取消后仍有事件被处理
    set({ sseEventQueue: [] });

    // 场景 1：没有任何 MessageItems（SSE 还未返回数据）
    if (!messageItems || messageItems.length === 0) {
      const currentConversation = getCurrentConversation();
      if (currentConversation) {
        // 创建新的 MessageItems
        const messageItemsId = get().generateMessageItemsId();
        const messageId = get().generateMessageId();

        // 创建 CANCELLED 状态的 INTERRUPT 消息
        const interruptMessage: Message = {
          id: messageId,
          type: MessageType.INTERRUPT,
          status: TaskStatus.CANCELLED,
          content: '',
          title: undefined,
          messageItemsId,
          conversationId: currentConversation.id,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          isStreaming: false,
          parentMessageId: undefined,
          childMessageIds: undefined,
        };

        // 创建 MessageItems
        const newMessageItems: MessageItems = {
          id: messageItemsId,
          isUser: false,
          status: TaskStatus.CANCELLED,
          messagesIds: [messageId],
          conversationId: currentConversation.id,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          agentType: AgentType.DEEPSEARCH,
        };

        // 添加到 stores
        set((state) => {
          const newMessagesMap = new Map(state.messagesMap);
          newMessagesMap.set(messageId, interruptMessage);

          const newMessageItemsMap = new Map(state.messageItemsMap);
          newMessageItemsMap.set(messageItemsId, newMessageItems);

          return {
            messagesMap: newMessagesMap,
            messageItemsMap: newMessageItemsMap,
          };
        });

        // 添加到 conversation 的 messageItemsIds
        set((state) => {
          const conversation = state.conversationsMap.get(currentConversation.id);
          if (conversation) {
            const updatedConversation = {
              ...conversation,
              messageItemsIds: [...conversation.messageItemsIds, messageItemsId],
              updatedAt: Date.now(),
            };
            const newConversationsMap = new Map(state.conversationsMap);
            newConversationsMap.set(currentConversation.id, updatedConversation);
            return { conversationsMap: newConversationsMap };
          }
          return state;
        });
      }
      return;
    }

    // 场景 2：已有 MessageItems（SSE 已返回数据，可能已经有消息）
    const lastMessageItems = messageItems[messageItems.length - 1];

    // 检查最后一个 MessageItems 是否是用户消息
    // 如果是用户消息，需要创建一个新的系统 MessageItems 来显示取消状态
    const isLastMessageUser = lastMessageItems.isUser === true;

    if (isLastMessageUser) {
      // 用户消息后面没有系统消息，创建一个新的系统 MessageItems
      const currentConversation = getCurrentConversation();
      if (currentConversation) {
        const messageItemsId = get().generateMessageItemsId();
        const messageId = get().generateMessageId();

        // 创建 CANCELLED 状态的 INTERRUPT 消息
        const interruptMessage: Message = {
          id: messageId,
          type: MessageType.INTERRUPT,
          status: TaskStatus.CANCELLED,
          content: '',
          title: undefined,
          messageItemsId,
          conversationId: currentConversation.id,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          isStreaming: false,
          parentMessageId: undefined,
          childMessageIds: undefined,
        };

        // 创建系统 MessageItems
        const newMessageItems: MessageItems = {
          id: messageItemsId,
          isUser: false,
          status: TaskStatus.CANCELLED,
          messagesIds: [messageId],
          conversationId: currentConversation.id,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          agentType: AgentType.DEEPSEARCH,
        };

        // 添加到 stores
        set((state) => {
          const newMessagesMap = new Map(state.messagesMap);
          newMessagesMap.set(messageId, interruptMessage);

          const newMessageItemsMap = new Map(state.messageItemsMap);
          newMessageItemsMap.set(messageItemsId, newMessageItems);

          return {
            messagesMap: newMessagesMap,
            messageItemsMap: newMessageItemsMap,
          };
        });

        // 添加到 conversation 的 messageItemsIds
        set((state) => {
          const conversation = state.conversationsMap.get(currentConversation.id);
          if (conversation) {
            const updatedConversation = {
              ...conversation,
              messageItemsIds: [...conversation.messageItemsIds, messageItemsId],
              updatedAt: Date.now(),
            };
            const newConversationsMap = new Map(state.conversationsMap);
            newConversationsMap.set(currentConversation.id, updatedConversation);
            return { conversationsMap: newConversationsMap };
          }
          return state;
        });
      }
      // 场景 2a 结束：已为用户消息创建新的系统 MessageItems
    } else {
      // 场景 2b：最后一个 MessageItems 是系统消息，继续原来的逻辑
      // 1. 更新 MessageItems 状态为 CANCELLED（无论当前状态是什么）
      updateMessageItems(lastMessageItems.id, { status: TaskStatus.CANCELLED });

      // 2. 递归更新所有子消息的状态为 CANCELLED
      const updateMessageToCancelled = (messageId: string) => {
        const message = getMessageById(messageId);
        if (message) {
          // 只要消息状态不是已经完成的或失败的，都更新为 CANCELLED
          if (message.status === TaskStatus.IN_PROGRESS || message.status === TaskStatus.PENDING || message.status === TaskStatus.COMPLETED) {
            updateMessage(lastMessageItems.id, messageId, {
              status: TaskStatus.CANCELLED,
              isStreaming: false,  // 清除流式标志
            });
          }
        }
        // 递归处理子消息
        const children = getChildMessages(messageId);
        children?.forEach(child => updateMessageToCancelled(child.id));
      };

      // 遍历所有顶级消息
      lastMessageItems.messagesIds.forEach(messageId => {
        updateMessageToCancelled(messageId);
      });

      // 3. 检查是否存在 INTERRUPT 消息，如果存在则更新其状态为 CANCELLED，如果不存在则创建
      const hasInterruptMessage = lastMessageItems.messagesIds.some(messageId => {
        const message = getMessageById(messageId);
        return message?.type === MessageType.INTERRUPT;
      });

      if (hasInterruptMessage) {
        // 找到 INTERRUPT 消息并更新其状态为 CANCELLED
        lastMessageItems.messagesIds.forEach(messageId => {
          const message = getMessageById(messageId);
          if (message?.type === MessageType.INTERRUPT) {
            updateMessage(lastMessageItems.id, messageId, {
              status: TaskStatus.CANCELLED,
              isStreaming: false,
            });
          }
        });
      } else {
        // 创建 INTERRUPT 消息（用于显示"对话已取消"提示）
        // 直接添加消息到当前 MessageItems，不检查状态
        const currentConversation = getCurrentConversation();
        if (currentConversation) {
          // 手动创建消息，绕过 addSystemMessage 的状态检查
          const messageId = get().generateMessageId();
          const messageItemsId = lastMessageItems.id;

          // 创建消息
          const interruptMessage: Message = {
            id: messageId,
            type: MessageType.INTERRUPT,
            status: TaskStatus.CANCELLED,  // 直接设置为 CANCELLED
            content: '',
            title: undefined,
            messageItemsId,
            conversationId: currentConversation.id,
            createdAt: Date.now(),
            updatedAt: Date.now(),
            isStreaming: false,
            parentMessageId: undefined,
            childMessageIds: undefined,
          };

          // 添加到 messagesMap
          set((state) => {
            const newMessagesMap = new Map(state.messagesMap);
            newMessagesMap.set(messageId, interruptMessage);
            return { messagesMap: newMessagesMap };
          });

          // 添加到 MessageItems 的 messagesIds 数组
          set((state) => {
            const newMessageItemsMap = new Map(state.messageItemsMap);
            const existingItems = newMessageItemsMap.get(messageItemsId);
            if (existingItems) {
              newMessageItemsMap.set(messageItemsId, {
                ...existingItems,
                messagesIds: [...existingItems.messagesIds, messageId],
                updatedAt: Date.now(),
              });
            } else {
              console.warn('[updateMessageItemsStatusToCancelled] MessageItems not found in map:', messageItemsId);
            }
            return { messageItemsMap: newMessageItemsMap };
          });
        }
      }
    }

    // 4. 确保保存到 IndexDB
    const finalMessageItems = getCurrentMessageItems();
    if (finalMessageItems && finalMessageItems.length > 0) {
      saveConversationToDB(lastMessageItems.conversationId);
    }
  },
}));
// ===== 监听 IndexDB 删除事件，同步删除内存中的对话 =====
if (typeof window !== 'undefined') {
  conversationEventEmitter.on('conversation-deleted', async (event: any) => {
    const { conversationId } = event;

    // 从内存中删除对话
    useConversationStore.setState((state) => {
      // 删除conversationsMap中的条目
      const newConversationsMap = new Map(state.conversationsMap);
      newConversationsMap.delete(conversationId);

      // 从conversationsList中移除
      const newConversationsList = state.conversationsList.filter(id => id !== conversationId);

      // 如果删除的是当前对话，清空当前对话ID
      const newCurrentConversationId = state.currentConversationId === conversationId
        ? null
        : state.currentConversationId;

      return {
        conversationsMap: newConversationsMap,
        conversationsList: newConversationsList,
        currentConversationId: newCurrentConversationId,
      };
    });
  });
}

// 开发环境下暴露 store 到 window 对象，方便调试
if (typeof window !== 'undefined' && process.env.NODE_ENV === 'development') {
  (window as any).useConversationStore = useConversationStore;
}
