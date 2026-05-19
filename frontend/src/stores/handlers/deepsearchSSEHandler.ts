import {
  MessageType,
  TaskStatus,
  Message,
  MessageItems,
  JSONObject,
  MESSAGE_TITLES,
  isFinalReportMessage,
  OUTLINE_INTERACTION_MAX_ROUNDS,
  OUTLINE_INTERACTION_WARNING_THRESHOLD,
  isTaskOngoing,
  DeepsearchExecutionMethod
} from '../useConversationStore';
import { ThoughtNodeType, EdgeRelationType, ThoughtNode } from './deepsearchMindMapHandler';
import { DeepsearchEvent, DeepsearchAgentType, SSEData } from './deepsearchSSETypes';
import i18n from '@/i18n';

/**
 * Deepsearch SSE Handler
 *
 * 专门处理 deepsearch agent 类型的 SSE 消息
 */


interface StoreDependencies {
  getLastMessageItems: () => MessageItems | undefined;
  addSystemMessage: (conversationId: string, type: MessageType, content: any, parentId?: string, title?: string, agentType?: string, indexPath?: string) => Message | null;
  addMessageAsChild: (messageItemsId: string, parentId: string, type: MessageType, content: any, title?: string, indexPath?: string) => Message;
  updateMessage: (messageItemsId: string, messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (messageItemsId: string, messageId: string) => void;
  updateMessageItems: (id: string, updates: Partial<MessageItems>) => void;
  appendMessageContent: (messageItemsId: string, messageId: string, content: string) => void;
  getMessageById: (id: string) => Message | undefined;
  getMessageItemsById: (id: string) => MessageItems | undefined;  // 新增：通过ID获取MessageItems
  getMessageTree: (messageId: string) => Message | null;  // 新增：获取消息树
  getChildMessages: (messageId: string) => Message[];
  getMessageItemsIsUser: (messageItems: MessageItems) => boolean;  // 新增：兼容历史数据
  setSessionConversationId: (conversationId: string | null) => void;  // 新增：设置连续对话系列ID
  saveConversationToDB: (conversationId: string) => Promise<void>;
  getOrCreateMindMapManager: (messageItemsId: string) => any;  // 获取或创建思维链图管理器集合（{sectionGraph, taskGraph}）
}

interface StreamCache {
  get: (key: string) => string[] | undefined;
  set: (key: string, chunks: string[]) => void;
  delete: (key: string) => void;
}

// ===== 工具函数 =====

/**
 * 安全解析 SSE 内容为 JSON 对象
 * @param content SSE 消息内容（字符串或对象）
 * @param fallback 解析失败时的默认值
 * @returns 解析后的对象或 fallback
 */
function parseSSEContent<T = JSONObject>(content: string | JSONObject | undefined, fallback: T): T {
  if (!content) {
    return fallback;
  }
  if (typeof content === 'string') {
    try {
      return JSON.parse(content);
    } catch {
      return fallback;
    }
  }
  return content as T;
}

/**
 * 解析索引值，支持两种格式：
 * - 简单数字： "123" -> 123
 * - 复合格式： "1-2-3" -> 3 (取最后一个数字)
 */
function parseIndexValue(value: string | number | undefined): number | undefined {
  if (value === undefined || value === null) {
    return undefined;
  }

  const strValue = String(value);

  // 如果包含 '-'，按 '-' 分割并取最后一个部分
  if (strValue.includes('-')) {
    const parts = strValue.split('-');
    const lastPart = parts[parts.length - 1];
    return parseInt(lastPart, 10);
  }

  // 否则直接解析整个字符串
  return parseInt(strValue, 10);
}

/**
 * 构建 indexPath 字符串
 * @param sectionIdx 章节索引
 * @param planIdx 计划索引
 * @param stepIdx 步骤索引
 * @returns 格式 "section-plan-step"，如 "0-1-2"；如果所有参数都为 undefined 则返回 undefined
 */
function buildIndexPath(sectionIdx?: number, planIdx?: number, stepIdx?: number): string | undefined {
  if (sectionIdx === undefined && planIdx === undefined && stepIdx === undefined) {
    return undefined;
  }
  return `${sectionIdx ?? 0}-${planIdx ?? 0}-${stepIdx ?? 0}`;
}

// ===== Handler 类 =====

// Agent 名称常量
const AGENT_NAMES = {
  USER_FEEDBACK_PROCESSOR: 'user_feedback_processor',
} as const;

export class DeepsearchSSEHandler {
  private store: StoreDependencies;
  private streamCache: StreamCache;
  private conversationId: string;
  private messageFindCache: Map<string, Message | null>;

  // 按 conversationId 分组，跨 handler 实例持久化，仅在此模块内使用
  private static readonly deferredStatuses = new Map<
    string,
    Map<number, { messageItemsId: string; childMessageId: string; status: TaskStatus }>
  >();

  constructor(store: StoreDependencies, streamCache: StreamCache, conversationId: string) {
    this.store = store;
    this.streamCache = streamCache;
    this.conversationId = conversationId;
    this.messageFindCache = new Map();
  }

  private setDeferredSubReporterStatus(sectionIdx: number, messageItemsId: string, childMessageId: string, status: TaskStatus): void {
    if (!DeepsearchSSEHandler.deferredStatuses.has(this.conversationId)) {
      DeepsearchSSEHandler.deferredStatuses.set(this.conversationId, new Map());
    }
    DeepsearchSSEHandler.deferredStatuses.get(this.conversationId)!.set(sectionIdx, { messageItemsId, childMessageId, status });
  }

  private getDeferredSubReporterStatus(sectionIdx: number): { messageItemsId: string; childMessageId: string; status: TaskStatus } | null {
    return DeepsearchSSEHandler.deferredStatuses.get(this.conversationId)?.get(sectionIdx) ?? null;
  }

  private deleteDeferredSubReporterStatus(sectionIdx: number): void {
    DeepsearchSSEHandler.deferredStatuses.get(this.conversationId)?.delete(sectionIdx);
  }

  private clearDeferredSubReporterStatuses(): void {
    DeepsearchSSEHandler.deferredStatuses.delete(this.conversationId);
  }

  /**
   * 将 deepsearch agent 类型映射到消息类型
   */
  private mapAgentToMessageType(agent: string): MessageType {
    const agentTypeMap: Record<string, MessageType> = {
      [DeepsearchAgentType.ENTRY]: MessageType.TEXT,
      [DeepsearchAgentType.GENERATE_QUESTIONS]: MessageType.TEXT,
      [DeepsearchAgentType.FEEDBACK_HANDLER]: MessageType.INTERRUPT,
      [DeepsearchAgentType.OUTLINE]: MessageType.TASK,
      [DeepsearchAgentType.OUTLINE_INTERACTION]: MessageType.OUTLINE_INTERACTION,
      [DeepsearchAgentType.PLAN_REASONING]: MessageType.TASK,
      [DeepsearchAgentType.SUB_REPORTER]: MessageType.REPORT,
      [DeepsearchAgentType.COLLECTOR_INFO_RETRIEVAL]: MessageType.LINK,
      [DeepsearchAgentType.COLLECTOR_SUMMARY]: MessageType.TEXT,
      [DeepsearchAgentType.END]: MessageType.REPORT,
    };
    return agentTypeMap[agent] || MessageType.TEXT;
  }

  /**
   * 主入口：处理 SSE 消息
   */
  public handleSSEMessage(sseData: SSEData): void {
    const lastMessageItems = this.store.getLastMessageItems();

    // 如果对话已被取消，忽略所有后续 SSE 事件
    // 这发生在用户点击取消按钮后，但 SSE 事件仍在队列中或继续到达的情况
    if (lastMessageItems && lastMessageItems.status === TaskStatus.CANCELLED) {
      console.log('[DeepsearchSSEHandler] MessageItems cancelled, ignoring SSE event:', sseData.event);
      return;
    }

    // HITL 延续场景：如果当前 MessageItems 状态为 COMPLETED，重新设置为 IN_PROGRESS
    // 这发生在用户回复 interrupt 消息后，SSE 流继续的情况
    // 但对于 user_feedback_processor 相关事件（done, waiting_user_input），不应该重新激活状态
    // 因为此时报告已经完成，只是等待用户进行 AI 改写操作
    const isUserFeedbackProcessorEvent =
      sseData.agent === AGENT_NAMES.USER_FEEDBACK_PROCESSOR &&
      (sseData.event === DeepsearchEvent.DONE || sseData.event === DeepsearchEvent.WAITING_USER_INPUT);

    if (lastMessageItems && !this.store.getMessageItemsIsUser(lastMessageItems)) {
      if (lastMessageItems.status === TaskStatus.COMPLETED && !isUserFeedbackProcessorEvent) {
        // HITL 延续：重新激活 MessageItems 状态
        this.store.updateMessageItems(lastMessageItems.id, { status: TaskStatus.IN_PROGRESS });
      }
    }

    const sectionIdx = parseIndexValue(sseData.section_idx);
    const planIdx = parseIndexValue(sseData.plan_idx);
    const stepIdx = parseIndexValue(sseData.step_idx);

    switch (sseData.event) {
      case DeepsearchEvent.START:
        this.handleStart(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case DeepsearchEvent.MESSAGE:
        this.handleMessage(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case DeepsearchEvent.DONE:
        this.handleDone(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case DeepsearchEvent.SUMMARY_RESPONSE:
        this.handleSummaryResponse(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case DeepsearchEvent.WAITING_USER_INPUT:
        this.handleWaitingUserInput(sseData);
        break;
      case DeepsearchEvent.USER_INPUT_ENDED:
        this.handleUserInputEnded(sseData);
        break;
      case DeepsearchEvent.ERROR:
        this.handleError(sseData, sectionIdx, planIdx, stepIdx);
        break;
    }

    // 清除消息查找缓存，防止内存泄漏
    this.messageFindCache.clear();
  }

  /**
   * 处理 start 事件
   */
  private handleStart(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { addSystemMessage, updateMessage } = this.store;

    // 生成流缓存 key
    const streamKey = this.generateStreamKey(sseData.agent, sectionIdx, planIdx, stepIdx);

    // outline: 只初始化缓存，不创建消息卡片
    if (sseData.agent === DeepsearchAgentType.OUTLINE) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.streamCache.set(streamKey, [content]);
      return;
    }

    // plan_reasoning: 初始化缓存，更新对应 section task 的状态和时间
    if (sseData.agent === DeepsearchAgentType.PLAN_REASONING) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.streamCache.set(streamKey, [content]);

      let lastMessageItems = this.store.getLastMessageItems();
      if (lastMessageItems && sectionIdx !== undefined && planIdx !== undefined) {

        // 检查是否存在根 TASK 消息（sectionIdx=0），如果不存在则从缓存创建
        let rootTask = this.findTaskInMessages(
          lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.sectionIdx === 0,
          'section_0'
        );

        if (!rootTask) {
          const outlineContent = this.getOutlineContentFromCache();
          if (outlineContent) {
            rootTask = this.createRootTaskFromOutline(outlineContent);
            // 更新 lastMessageItems 指向 rootTask 的 messageItems
            if (rootTask) {
              lastMessageItems = this.store.getMessageItemsById(rootTask.messageItemsId);
              if(!lastMessageItems)
                return;
            }
          } else {
            console.warn('[DeepsearchSSEHandler] No cached outline found for creating root TASK');
          }
        }

        // 使用 indexPath 查找 sectionTask
        const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
        const sectionTask = this.findTaskInMessages(
          lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
          `section_${sectionIdx}` // 添加缓存key
        );

        // 【步骤1】更新上一个 planTask (task_1_x_(n-1))
        if (planIdx > 1 && sectionTask) {
          const prevPlanTask = this.store.getChildMessages(sectionTask.id).find(task =>
            task.indexPath === `${sectionIdx}-${planIdx - 1}-0`
          );

          if (prevPlanTask && isTaskOngoing(prevPlanTask.status)) {
            // 从上一个 planTask 开始递归更新
            this.updateUnfinishedTasksRecursively(
              prevPlanTask.id,
              lastMessageItems.id,
              TaskStatus.UNKNOWN
            );
          }
        }

        // 【步骤2】更新 section task（原有逻辑）
        if (sectionTask && sectionTask.status === TaskStatus.PENDING) {
          const now = Date.now();
          updateMessage(lastMessageItems.id, sectionTask.id, {
            status: TaskStatus.IN_PROGRESS,
            createdAt: now,
            updatedAt: now,
            isStreaming: true,
          });
        }
      }

      return;
    }

    // sub_reporter: 初始化缓存，创建或更新章节报告
    if (sseData.agent === DeepsearchAgentType.SUB_REPORTER && sectionIdx !== undefined && sectionIdx > 0) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      // 重置流缓存
      this.streamCache.set(streamKey, [content]);

      const lastMessageItems = this.store.getLastMessageItems();
      if (!lastMessageItems) return;

      // 使用 indexPath 查找 sectionTask
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (sectionTask) {
        // 检查是否已存在章节报告
        const existingReport = this.findExistingChapterReport(sectionTask);

        if (existingReport) {
          // 情况2: 已存在章节报告 - 更新现有消息
          // 替换 content，设置 isStreaming 和 status
          updateMessage(lastMessageItems.id, existingReport.id, {
            content: content,  // 直接替换为新的初始 content
            isStreaming: true,
            status: TaskStatus.IN_PROGRESS,
          });

          // 将父节点 sectionTask 状态改为 REPORTING
          updateMessage(lastMessageItems.id, sectionTask.id, {
            status: TaskStatus.REPORTING,
          });
        } else {
          // 先有条件地递归更新本章节的最后一个子Message(子Message.status=PENDING 或 IN_PROGRESS):
          const sectionChildren = this.store.getChildMessages(sectionTask.id);
          const lastChildMessage = sectionChildren.length > 0 ? sectionChildren[sectionChildren.length - 1] : null;
          if (lastChildMessage && isTaskOngoing(lastChildMessage.status)) {
            this.updateUnfinishedTasksRecursively(
              lastChildMessage.id,
              lastMessageItems.id,
              TaskStatus.UNKNOWN
            );
          }

          // 情况1: 不存在章节报告 - 创建新消息（原有逻辑）
          // const subTitle = `${i18n.t('deepResearch.handler.chapterReport')}: ${sectionTask.title}`;
          const subTitle = `${sectionTask.title}`;
          const childMessage = this.store.addMessageAsChild(
            lastMessageItems.id,
            sectionTask.id,
            MessageType.REPORT,
            '',
            subTitle,
            buildIndexPath(sectionIdx, 0, 0)
          );

          updateMessage(lastMessageItems.id, childMessage.id, {
            status: TaskStatus.IN_PROGRESS,
            isStreaming: true,
          });

          // 将父节点 sectionTask 状态改为 REPORTING
          updateMessage(lastMessageItems.id, sectionTask.id, {
            status: TaskStatus.REPORTING,
          });

          // 将子报告节点添加至思维链中
          this.addSubReportToMindMap(childMessage.id, lastMessageItems.id);
        }

      }
      return;
    }

    // entry 或 generate_questions: 创建占位消息（不使用 streamCache）
    if (sseData.agent === DeepsearchAgentType.ENTRY || sseData.agent === DeepsearchAgentType.GENERATE_QUESTIONS) {
      const lastMessage = addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), '', undefined, undefined, 'deepsearch', buildIndexPath(sectionIdx, planIdx, stepIdx));

      const lastMessageItems = this.store.getLastMessageItems();
      if (lastMessageItems && lastMessage) {
        updateMessage(lastMessageItems.id, lastMessage.id, {
          content: sseData.content || '',
          isStreaming: true,
        });
      }
      return;
    }

    // 其他类型：创建普通TEXT消息
    const content = typeof sseData.content === 'string' ? sseData.content : '';
    addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), content, undefined, undefined, 'deepsearch', buildIndexPath(sectionIdx, planIdx, stepIdx));
  }

  /**
   * 处理 message 事件
   */
  private handleMessage(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const streamKey = this.generateStreamKey(sseData.agent, sectionIdx, planIdx, stepIdx);

    // user_feedback_processor: 处理 final_result，更新或创建最终报告
    // 当开启 user_feedback_processor_enable 时，报告生成完成后会发送 final_result
    if (sseData.agent === AGENT_NAMES.USER_FEEDBACK_PROCESSOR) {
      this.handleUserFeedbackProcessorMessage(sseData);
      return;
    }

    // outline: 追加内容到缓存，不创建消息
    if (sseData.agent === DeepsearchAgentType.OUTLINE) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      if (!this.streamCache.get(streamKey)) {
        // 缓存不存在，初始化缓存
        this.streamCache.set(streamKey, [content]);
      } else {
        // 追加到缓存
        this.addToCache(streamKey, content);
      }
      return;
    }

    // plan_reasoning: 追加内容到缓存
    if (sseData.agent === DeepsearchAgentType.PLAN_REASONING) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.addToCache(streamKey, content);
      return;
    }

    // sub_reporter: 追加内容到缓存和消息
    if (sseData.agent === DeepsearchAgentType.SUB_REPORTER && sectionIdx !== undefined && sectionIdx > 0) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.addToCache(streamKey, content);

      const lastMessageItems = this.store.getLastMessageItems();
      if (!lastMessageItems) return;

      // 使用 indexPath 查找 sectionTask
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (sectionTask) {
        const childMessages = this.store.getChildMessages(sectionTask.id);
        if (childMessages.length > 0) {
          const lastChild = childMessages[childMessages.length - 1];
          if (lastChild && lastChild.isStreaming && typeof sseData.content === 'string') {
            this.store.appendMessageContent(lastMessageItems.id, lastChild.id, sseData.content);
          }
        }
      }
      return;
    }

    // 其他消息(如entry, generate_questions)：追加内容
    const lastMessageItems = this.store.getLastMessageItems();
    if (lastMessageItems && !this.store.getMessageItemsIsUser(lastMessageItems)) {
      const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
      const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;
      if (lastMessage && lastMessage.isStreaming) {
        const content = typeof sseData.content === 'string' ? sseData.content : '';
        this.store.appendMessageContent(lastMessageItems.id, lastMessage.id, content);
      }
    }
  }

  /**
   * 处理 done 事件
   */
  private handleDone(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { updateMessage, getMessageItemsIsUser } = this.store;
    const streamKey = this.generateStreamKey(sseData.agent, sectionIdx, planIdx, stepIdx);
    const lastMessageItems = this.store.getLastMessageItems();


    if (sseData.agent === DeepsearchAgentType.OUTLINE) {
      const cachedOutline = this.getCacheContent(streamKey);
      if (cachedOutline) {
        try {
          const outlineContent = JSON.parse(cachedOutline);
          // 存储解析后的大纲内容
          this.streamCache.set('__outline_content__', [JSON.stringify(outlineContent)]);
        } catch (e) {
          console.warn('[DeepsearchSSEHandler] Failed to parse outline content:', e);
        }
      } else {
        console.warn('[DeepsearchSSEHandler] No cached outline found for key:', streamKey);
      }
      return;
    }

    if (!lastMessageItems || getMessageItemsIsUser(lastMessageItems)) {
      return;
    }

    // plan_reasoning 完成
    if (sseData.agent === DeepsearchAgentType.PLAN_REASONING && sectionIdx !== undefined && planIdx !== undefined) {
      // 使用 indexPath 查找 sectionTask
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      let sectionTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
        msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath
      );

      // ===== 修复：如果section任务不存在（因为outline为空），动态创建 =====
      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found for plan_reasoning, creating one. sectionIdx:', sectionIdx);

        // 找到根大纲任务（使用 indexPath）
        const rootIndexPath = buildIndexPath(0, 0, 0);
        const rootTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
          msg.type === MessageType.TASK && msg.indexPath === rootIndexPath
        );

        if (rootTask) {
          sectionTask = this.store.addMessageAsChild(
            lastMessageItems.id,
            rootTask.id,
            MessageType.TASK,
            i18n.t('apps.deepSearch.researchChapter', { index: sectionIdx }),
            i18n.t('apps.deepSearch.chapter', { index: sectionIdx }),
            buildIndexPath(sectionIdx, 0, 0)
          );

          updateMessage(lastMessageItems.id, sectionTask.id, {
            sectionIdx: sectionIdx,
            status: TaskStatus.PENDING,
            isStreaming: false,
          });

          /// 将 sectionTask 节点添加到思维链 graph 中
          this.addSectionTaskToMindMap(sectionTask.id, lastMessageItems.id);
        } else {
          console.error('[DeepsearchSSEHandler] Root outline task not found, cannot create section task');
          this.streamCache.delete(streamKey);
          return;
        }
      }

      try {
        const cachedContent = this.getCacheContent(streamKey);

        // ===== 修复：处理空内容的情况 =====
        if (!cachedContent || cachedContent.trim() === '') {
          console.warn('[DeepsearchSSEHandler] Plan reasoning content is empty, using default structure');

          // 更新 section 任务状态
          updateMessage(lastMessageItems.id, sectionTask.id, {
            status: TaskStatus.IN_PROGRESS,
          });

          this.streamCache.delete(streamKey);
          return;
        }

        const parsedContent = JSON.parse(cachedContent);

        const planTask = this.findOrCreatePlanTask(sectionTask, planIdx, lastMessageItems.id, parsedContent.title);
        
        if (!planTask) {
          console.error('[DeepsearchSSEHandler] Failed to find or create plan task');
          this.streamCache.delete(streamKey);
          return;
        }

        // 更新 plan 任务
        updateMessage(lastMessageItems.id, planTask.id, {
          content: parsedContent.thought || '',
          status: parsedContent.is_research_completed ? TaskStatus.COMPLETED : TaskStatus.IN_PROGRESS,
        });

        // 更新 section 任务状态
        updateMessage(lastMessageItems.id, sectionTask.id, {
          status: TaskStatus.IN_PROGRESS,
        });

        // ===== 初始化计划级依赖集合 =====
        const dependOnPlanIds: { [id: string]: string } = {};
        // 为每个 step 创建子任务
        if (parsedContent.steps && Array.isArray(parsedContent.steps)) {
          const planChildren = this.store.getChildMessages(planTask.id);

          parsedContent.steps.forEach((step: any, _stepIndex: number) => {
            const existingStep = planChildren.find(st => st.title === step.title);
            if (existingStep) return;

            // ===== 依赖项解析 =====
            const dependIds: string[] = Array.isArray(step.parent_ids) ? step.parent_ids : [];
            const relationships: string[] = Array.isArray(step.relationships) ? step.relationships : [];

            const dependOnMessageIds: { [id: string]: string } = {};

            // 只有两个长度一致时才处理
            if (dependIds.length > 0 && dependIds.length === relationships.length) {
              for (let i = 0; i < dependIds.length; i++) {
                const dependIndexPath = dependIds[i];  // 直接使用,不加 "-0-0"

                const dependMessage = this.findTaskInMessages(
                  lastMessageItems.messagesIds,
                  msg => msg.indexPath === dependIndexPath && msg.type === MessageType.TASK
                );

                if (dependMessage) {
                  // 添加到消息级依赖
                  dependOnMessageIds[dependMessage.id] = relationships[i];

                  // 如果依赖的父消息不是当前planTask,添加到计划级依赖
                  if (dependMessage.parentMessageId && dependMessage.parentMessageId !== planTask.id) {
                    const parentId = dependMessage.parentMessageId;
                    if (!dependOnPlanIds[parentId]) {
                      dependOnPlanIds[parentId] = relationships[i];
                    } else {
                      dependOnPlanIds[parentId] += ", " + relationships[i];
                    }
                  }
                }
              }
            }

            const stepTask = this.store.addMessageAsChild(
              lastMessageItems.id,
              planTask.id,
              MessageType.TASK,
              step.description || '',
              step.title,
              buildIndexPath(sectionIdx, planIdx, _stepIndex + 1)
            );

            updateMessage(lastMessageItems.id, stepTask.id, {
              status: TaskStatus.PENDING,
              isStreaming: false,
              ...(Object.keys(dependOnMessageIds).length > 0 ? { dependOnMessageIds } : {}),  // 只在非空时添加
            });

          });

          // ===== 更新 planTask 的计划级依赖到 dependOnMessageIds =====
          if (Object.keys(dependOnPlanIds).length > 0) {
            updateMessage(lastMessageItems.id, planTask.id, {
              dependOnMessageIds: {
                ...(planTask.dependOnMessageIds || {}),
                ...dependOnPlanIds
              }
            });
          }
        }

        // 添加 plan节点至思维链图中
        this.addPlanTaskToMindMap(planTask.id, lastMessageItems.id);

        this.streamCache.delete(streamKey);
      } catch (e) {
        console.error('[DeepsearchSSEHandler] Plan reasoning JSON解析失败:', e);
        // ===== 修复：即使解析失败，也要更新section状态 =====
        if (sectionTask) {
          updateMessage(lastMessageItems.id, sectionTask.id, {
            status: TaskStatus.IN_PROGRESS,
          });
        }
        this.streamCache.delete(streamKey);
      }
      return;
    }

    // sub_reporter 完成
    if (sseData.agent === DeepsearchAgentType.SUB_REPORTER && sectionIdx !== undefined && sectionIdx > 0) {
      const cachedContent = this.getCacheContent(streamKey);
      // 使用 indexPath 查找 sectionTask
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (sectionTask) {
        const childMessages = this.store.getChildMessages(sectionTask.id);
        if (childMessages.length > 0) {
          const lastChild = childMessages[childMessages.length - 1];
          if (lastChild) {
            // 先更新内容并停止流式动画，status 延迟到 SECTION_END 时统一更新
            updateMessage(lastMessageItems.id, lastChild.id, {
              content: cachedContent,
              isStreaming: false,
            });
            this.setDeferredSubReporterStatus(sectionIdx, lastMessageItems.id, lastChild.id, TaskStatus.COMPLETED);
          }
        }
      }

      this.streamCache.delete(streamKey);
      return;
    }

    // entry 或 generate_questions 完成
    if (sseData.agent === DeepsearchAgentType.ENTRY || sseData.agent === DeepsearchAgentType.GENERATE_QUESTIONS) {
      const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
      const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;

      // 检查消息的实际内容是否为空，如果为空则删除该消息
      const messageContent = typeof lastMessage?.content === 'string' ? lastMessage.content : '';
      if (!messageContent || messageContent.trim() === '') {
        if (lastMessage && lastMessage.isStreaming) {
          // 删除空消息
          this.store.deleteMessage(lastMessageItems.id, lastMessage.id);
        }
      } else {
        // 更新消息状态为完成
        if (lastMessage && lastMessage.isStreaming) {
          updateMessage(lastMessageItems.id, lastMessage.id, {
            status: TaskStatus.COMPLETED,
            isStreaming: false,
          });
        }
      }

      // Entry 处理完成，直接返回，避免执行后面的通用逻辑
      return;
    }

    // end 完成：保存 DeepSearch 结果，流程不会走到这里
    if (sseData.agent === DeepsearchAgentType.END) {
      try {
        let content: string | JSONObject | undefined = sseData.content;

        // 如果 content 是字符串，尝试解析为 JSON
        if (typeof content === 'string' && content.trim()) {
          try {
            content = JSON.parse(content);
          } catch (e) {
            console.warn('[DeepsearchSSEHandler] Failed to parse content as JSON:', e);
            content = undefined;
          }
        }

        // 检查是否包含最终结果（不是简单的 SECTION END 或 ALL END）
        if (content && typeof content === 'object' && (content.response_content || content.exception_info)) {
          // 使用 indexPath 查找 outlineTask
          const outlineIndexPath = buildIndexPath(0, 0, 0);
          const outlineTask = this.findTaskInMessages(
            lastMessageItems.messagesIds,
            msg => msg.type === MessageType.TASK && msg.indexPath === outlineIndexPath,
            'outline_root' // 添加缓存key
          );

          if (outlineTask) {
            const finalReportTask = this.store.addMessageAsChild(
              lastMessageItems.id,
              outlineTask.id,
              MessageType.REPORT,  // 修正：应该是 REPORT 类型
              content || '',
              MESSAGE_TITLES.FINAL_REPORT,
              buildIndexPath(0, 0, 0)
            );
            updateMessage(lastMessageItems.id, finalReportTask.id, {
              status: TaskStatus.COMPLETED,
              isStreaming: false,
            });
          }

        }
      } catch (error) {
        console.error('[DeepsearchSSEHandler] Failed to process end event:', error);
      }

      this.streamCache.delete(streamKey);
      return;
    }

    // 其他 agent 的完成处理
    const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
    const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;
    if (lastMessage && lastMessage.isStreaming) {
      updateMessage(lastMessageItems.id, lastMessage.id, {
        status: TaskStatus.COMPLETED,
        isStreaming: false,
      });
    }
  }

  /**
   * 处理 summary_response 事件
   */
  private handleSummaryResponse(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { updateMessage, updateMessageItems, addSystemMessage } = this.store;
    const lastMessageItems = this.store.getLastMessageItems();
    if (!lastMessageItems) return;

    // collector_info_retrieval 和 collector_summary
    if ([DeepsearchAgentType.COLLECTOR_INFO_RETRIEVAL, DeepsearchAgentType.COLLECTOR_SUMMARY].includes(sseData.agent as DeepsearchAgentType) &&
        sectionIdx !== undefined && planIdx !== undefined && stepIdx !== undefined) {

      // 修复：使用 indexPath 查找 sectionTask
      // sectionTask 的 indexPath 格式：sectionIdx-0-0
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found, sectionIdx:', sectionIdx, 'sectionIndexPath:', sectionIndexPath);
        return;
      }

      const sectionChildren = this.store.getChildMessages(sectionTask.id);

      // 修复：使用 indexPath 查找 planTask，而不是依赖 title
      // planTask 的 indexPath 格式：sectionIdx-planIdx-0
      const planIndexPath = buildIndexPath(sectionIdx, planIdx, 0);
      const planTask = sectionChildren.find(task => task.indexPath === planIndexPath);

      if (!planTask) {
        console.warn('[DeepsearchSSEHandler] Plan task not found, planIdx:', planIdx);
        return;
      }

      const planChildren = this.store.getChildMessages(planTask.id);
      const stepTask = planChildren[stepIdx - 1];

      if (!stepTask) {
        console.warn('[DeepsearchSSEHandler] Step task not found, stepIdx:', stepIdx);
        return;
      }

      // 【步骤0】更新上一个 stepTask (task_1_x_n_(k-1))，只在平行模式，且存在上一个stepTask且当前retrieval是本step的第1个retrieval时才更新
      const executionMethod = lastMessageItems.agentConfig?.execution_method as string | undefined;
      if (executionMethod === DeepsearchExecutionMethod.PARALLEL && 
        stepIdx > 1 && (!stepTask.childMessageIds || stepTask.childMessageIds.length === 0)) {
        const prevStepTask = planChildren[stepIdx - 2];

        if (prevStepTask && isTaskOngoing(prevStepTask.status)) {
          // 从上一个 stepTask 开始递归更新
          this.updateUnfinishedTasksRecursively(
            prevStepTask.id,
            lastMessageItems.id,
            TaskStatus.UNKNOWN
          );
        }
      }

      // 处理 content
      if (sseData.agent === DeepsearchAgentType.COLLECTOR_INFO_RETRIEVAL) {
        // collector_info_retrieval: content是JSON对象，包含url、title、query
        let parsedContent: JSONObject;
        if (typeof sseData.content === 'string') {
          try {
            parsedContent = JSON.parse(sseData.content);
          } catch (e) {
            console.error('[DeepsearchSSEHandler] Failed to parse collector_info_retrieval content as JSON:', e);
            parsedContent = { title: sseData.content };
          }
        } else if (sseData.content && typeof sseData.content === 'object') {
          parsedContent = sseData.content;
        } else {
          parsedContent = {};
        }

        const contentTitle = (parsedContent?.title as string | undefined) || i18n.t('deepResearch.handler.searchResult');
        const messageTitle = `collector_info_retrieval: ${contentTitle || i18n.t('deepResearch.handler.searchResult')}`;

        const childMessage = this.store.addMessageAsChild(
          lastMessageItems.id,
          stepTask.id,
          MessageType.LINK,
          parsedContent,
          messageTitle,
          buildIndexPath(sectionIdx, planIdx, stepIdx)
        );

        /// 更新本step状态为正在进行中（非IN_PROGRESS状态才更新）
        if (stepTask.status != TaskStatus.IN_PROGRESS) {
          const now = Date.now();
          updateMessage(lastMessageItems.id, stepTask.id, {
            status: TaskStatus.IN_PROGRESS,
            createdAt: now,
            updatedAt: now,
          });
        }

        updateMessage(lastMessageItems.id, childMessage.id, {
          status: TaskStatus.COMPLETED,
          isStreaming: false,
        });

        return;
      }

      // collector_summary: content是纯字符串，直接使用
      const summaryContent = typeof sseData.content === 'string'
        ? sseData.content
        : String(sseData.content || '');

      const childMessage = this.store.addMessageAsChild(
        lastMessageItems.id,
        stepTask.id,
        MessageType.TEXT,
        summaryContent,
        i18n.t('deepResearch.handler.informationSummary'),
        buildIndexPath(sectionIdx, planIdx, stepIdx)
      );

      updateMessage(lastMessageItems.id, childMessage.id, {
        status: TaskStatus.COMPLETED,
        isStreaming: false,
      });

      // 如果是 collector_summary，更新 step 状态
      if (sseData.agent === DeepsearchAgentType.COLLECTOR_SUMMARY && stepTask.status != TaskStatus.FAILED) {
        updateMessage(lastMessageItems.id, stepTask.id, {
          status: TaskStatus.COMPLETED,
        });

        // 检查 plan 的所有子任务是否都完成
        const planChildren = this.store.getChildMessages(planTask.id);
        const allStepsFinished = planChildren.every(step => !isTaskOngoing(step.status));

        if (allStepsFinished) {
          updateMessage(lastMessageItems.id, planTask.id, {
            status: TaskStatus.COMPLETED,
          });
        }
      }

      return;
    }

    // sub_reporter: 处理章节子报告（summary_response 事件）
    if (sseData.agent === DeepsearchAgentType.SUB_REPORTER &&
        sectionIdx !== undefined &&
        sectionIdx > 0 &&
        planIdx === 0 &&
        stepIdx === 0) {

      // 1. 检查 content 是否为 SUCCESS，如果是则跳过
      const contentStr = typeof sseData.content === 'string'
        ? sseData.content.trim()
        : String(sseData.content || '').trim();

      if (contentStr === 'SUCCESS') {
        return; // 直接跳过，不处理
      }

      // 2. 找到对应的 sectionTask（使用 indexPath）
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (!sectionTask) {
        console.warn('[sub_reporter summary_response] Section task not found, sectionIdx:', sectionIdx);
        return;
      }

      // 3. 获取 sectionTask 下的所有子 messages
      const sectionChildren = this.store.getChildMessages(sectionTask.id);
      const lastChild = sectionChildren.length > 0 ? sectionChildren[sectionChildren.length - 1] : null;

      // 4. 判断是创建还是更新：检查最后一个 child 是否是 REPORT 类型
      if (lastChild && lastChild.type === MessageType.REPORT) {
        // 情况A: 最后一个 child 是 REPORT - 更新现有消息，status更新 延迟到 SECTION_END
        updateMessage(lastMessageItems.id, lastChild.id, {
          content: sseData.content,
          isStreaming: false,
        });
        this.setDeferredSubReporterStatus(sectionIdx, lastMessageItems.id, lastChild.id, TaskStatus.FAILED);
      } else {
        // 情况B: 最后一个 child 不是 REPORT 或不存在 - 创建新消息，status 延迟到 SECTION_END
        // const subTitle = `${i18n.t('deepResearch.handler.chapterReport')}: ${sectionTask.title}`;
        const subTitle = `${sectionTask.title}`;
        const newReport = this.store.addMessageAsChild(
          lastMessageItems.id,
          sectionTask.id,
          MessageType.REPORT,
          sseData.content,
          subTitle,
          buildIndexPath(sectionIdx, 0, 0)
        );

        updateMessage(lastMessageItems.id, newReport.id, {
          isStreaming: false,
        });
        this.setDeferredSubReporterStatus(sectionIdx, lastMessageItems.id, newReport.id, TaskStatus.FAILED);
      }

      // 5. 递归更新倒数第二个 child message（task_x_(N-1)_0_0）
      // 条件：N > 1 且该 message 的状态是进行中
      if (sectionChildren.length > 1) {
        const secondLastChild = sectionChildren[sectionChildren.length - 2];
        if (secondLastChild && isTaskOngoing(secondLastChild.status)) {
          this.updateUnfinishedTasksRecursively(
            secondLastChild.id,
            lastMessageItems.id,
            TaskStatus.COMPLETED
          );
        }
      }

      return;
    }

    // end 事件
    if (sseData.agent === DeepsearchAgentType.END) {
      // 使用 indexPath 查找 outlineTask
      const outlineIndexPath = buildIndexPath(0, 0, 0);
      const outlineTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
        msg.type === MessageType.TASK && msg.indexPath === outlineIndexPath
      );

      // "SECTION END" 标识 (第6点)
      if (sseData.content === 'SECTION END' && sectionIdx !== undefined) {
        // 使用 indexPath 查找 sectionTask
        const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
        const sectionTask = this.findTaskInMessages(lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath
        );

        if (sectionTask) {
          // 先将延迟的子报告状态落地，确保后续读取 lastChildMessage.status 时已是最终态
          const deferred = this.getDeferredSubReporterStatus(sectionIdx);
          if (deferred) {
            updateMessage(deferred.messageItemsId, deferred.childMessageId, {
              status: deferred.status,
            });
            this.deleteDeferredSubReporterStatus(sectionIdx);
          }

          // 1. 根据 sectionTask 的最后一个子 Message 的状态来更新 sectionTask
          const sectionChildren = this.store.getChildMessages(sectionTask.id);
          const lastChildMessage = sectionChildren.length > 0 ? sectionChildren[sectionChildren.length - 1] : null;

          if (lastChildMessage) {
            if (lastChildMessage.type !== MessageType.REPORT) {
              // ===== 依赖驱动模式下跳过此逻辑 =====
              const executionMethod = lastMessageItems.agentConfig?.execution_method as string | undefined;

              /// 依赖模式下，lastChildMessage非子报告的话，说明是信息收集类型，状态设置为准完成
              if (executionMethod === DeepsearchExecutionMethod.DEPENDENCY_DRIVING) {
              // 无论平行/依赖模式，没有报告都创建一下章节报告
              // if (1) {
                // 1. 将信息收集类型任务状态设置为准完成
                this.updateUnfinishedTasksRecursively(
                  lastChildMessage.id,
                  lastMessageItems.id,
                  TaskStatus.UNKNOWN
                );
                // 2. 创建章节报告 task_x_N_0_0，类型为 report
                const newReportTask = this.store.addMessageAsChild(
                  lastMessageItems.id,
                  sectionTask.id,
                  MessageType.REPORT,
                  '',
                  `${sectionTask.title}`,
                  buildIndexPath(sectionIdx, 0, 0)
                );
                // 更新 newReportTask.status 为 PENDING
                updateMessage(lastMessageItems.id, newReportTask.id, {
                  isStreaming: false,
                  status: TaskStatus.PENDING,
                });
                // 将章节报告加入思维链图
                this.addSubReportToMindMap(
                  newReportTask.id,
                  lastMessageItems.id
                )
                // 3. 更新 sectionTask.status 为 REPORTING
                updateMessage(lastMessageItems.id, sectionTask.id, {
                  status: TaskStatus.REPORTING,
                });
                return;
              }

              // 最后一个子 Message 不是 REPORT 类型，将 sectionTask 更新为 FAILED
              this.updateUnfinishedTasksRecursively(
                sectionTask.id,
                lastMessageItems.id,
                TaskStatus.FAILED
              );
            } else {
              // 最后一个子 Message 是 REPORT 类型，根据其状态决定 sectionTask 的状态
              let targetStatus = lastChildMessage.status;

              if(targetStatus == TaskStatus.PENDING) {
                // 如果子 REPORT 的状态是PENDING状态，说明任务没开始，则已经失败
                targetStatus = TaskStatus.FAILED;
              }
              else if(isTaskOngoing(targetStatus)) {
                // 任务还在进进行中，将其变为 UNKNOWN
                targetStatus = TaskStatus.UNKNOWN;
              }
              // 其他状态（COMPLETED/FAILED/CANCELLED/UNKNOWN）保持不变

              // 使用 updateUnfinishedTasksRecursively 将 sectionTask.status 更新为目标状态
              this.updateUnfinishedTasksRecursively(
                sectionTask.id,
                lastMessageItems.id,
                targetStatus
              );
            }
          } else {
            // sectionTask 没有子 Message，默认更新为 FAILED
            updateMessage(lastMessageItems.id, sectionTask.id, {
              status: TaskStatus.FAILED,
            });
          }
        } else {
          console.error('[SECTION END] Section task NOT FOUND for sectionIdx:', sectionIdx);
        }

        // 2. 检查 outline 的所有 childTasks 是否都完成
        if (outlineTask) {
          const outlineChildren = this.store.getChildMessages(outlineTask.id);
          const allChildrenFinished = outlineChildren.every(child => !isTaskOngoing(child.status));

          if (allChildrenFinished) {
            // 创建最终报告 message（与 outline_task 同级）
            const finalReportMessage = addSystemMessage(
              this.conversationId,
              MessageType.REPORT,
              '',  // 初始 content 为空
              undefined,  // parentId 为 undefined，与 outline_task 同级
              MESSAGE_TITLES.FINAL_REPORT,
              'deepsearch',  // agent 类型
              buildIndexPath(0, 0, 0)
            );
            if (finalReportMessage) {
              updateMessage(lastMessageItems.id, finalReportMessage.id, {
                status: TaskStatus.IN_PROGRESS,
                isStreaming: false,
              });

              // 将最终报告添加至思维链中
              this.addFinalReportToMindMap(finalReportMessage.id, lastMessageItems.id, outlineTask);
            }

            // 3. 更新 task_1 (outline_task): status = COMPLETED
            // updateMessage(lastMessageItems.id, outlineTask.id, {
            //   status: TaskStatus.COMPLETED,
            // });
          }
        }

        return;
      }

      // 最终报告+溯源信息 (第7点)
      /// 先将sseData.content转换为json对象
      let endData = null;
      if (typeof sseData.content === 'string' && sseData.content.trim().startsWith('{')) {
        try {
          endData = JSON.parse(sseData.content);
        } catch (e) {
          console.error('[DeepsearchSSEHandler] Failed to parse end content:', e);
        }
      } else if (typeof sseData.content === 'object' && (sseData.content.response_content || sseData.content.exception_info)) {
        endData = sseData.content;
      }

      if (endData && (endData.response_content || endData.exception_info)) {
        // 找到与 outline_task 同级的 PENDING 或 IN_PROGRESS REPORT message
        const pendingReportMessage = lastMessageItems.messagesIds
          .map(msgId => this.store.getMessageById(msgId))
          .filter((msg): msg is Message => msg !== undefined)
          .filter(msg =>
            msg.type === MessageType.REPORT &&
            isTaskOngoing(msg.status) &&
            isFinalReportMessage(msg) &&
            !msg.parentMessageId  // ← 确保是顶级 message
          )
          .pop();  // 取最后一个

        if (pendingReportMessage) {
          // 更新最终报告 message: content 和 status
          updateMessage(lastMessageItems.id, pendingReportMessage.id, {
            content: endData || '',
            status: TaskStatus.COMPLETED,
          });
        } else {
          // 只有在存在 outline 任务 或存在错误信息时 才创建最终报告
          // 如果没有 outline 任务，说明这不是真正的研究请求，不需要创建最终报告；或者存在错误信息，则显示有错误的最终报告
          if (outlineTask || endData.exception_info) {
            console.warn('[DeepsearchSSEHandler] No pending REPORT message found, creating new one');
            const finalReportMessage = addSystemMessage(
              this.conversationId,
              MessageType.REPORT,
              endData || '',
              undefined,  // 与 outline_task 同级
              MESSAGE_TITLES.FINAL_REPORT,
              'deepsearch',  // agent 类型
              buildIndexPath(0, 0, 0)
            );
            if (finalReportMessage) {
              updateMessage(lastMessageItems.id, finalReportMessage.id, {
                status: TaskStatus.COMPLETED,
                isStreaming: false,
              });
              // 将最终报告添加至思维链中
              this.addFinalReportToMindMap(finalReportMessage.id, lastMessageItems.id, outlineTask);
            }
          } else {
            // 非研究请求：将 response_content 作为普通消息显示
            console.warn('[DeepsearchSSEHandler] No outline task found, treating as normal message');
            const content = endData?.response_content || sseData.content || '';
            if (content && content.trim()) {
              // 查找 entry 创建的消息并更新其内容
              const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
              const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;
              if (lastMessage && lastMessage.type === MessageType.TEXT && lastMessage.isStreaming) {
                updateMessage(lastMessageItems.id, lastMessage.id, {
                  content: content,
                  status: TaskStatus.COMPLETED,
                  isStreaming: false,
                });
              } else if (!lastMessage || lastMessage.status === TaskStatus.COMPLETED) {
                // 如果没有找到正在流式传输的消息，创建新的普通消息
                const normalMessage = addSystemMessage(
                  this.conversationId,
                  MessageType.TEXT,
                  content,
                  undefined,
                  undefined,
                  'deepsearch',
                  buildIndexPath()
                );
                if (normalMessage) {
                  updateMessage(lastMessageItems.id, normalMessage.id, {
                    status: TaskStatus.COMPLETED,
                    isStreaming: false,
                  });
                }
              }
            }
          }
        }
        return;
      }

      // "ALL END" 标识 (第8点)
      if (sseData.content === 'ALL END') {
        // 1. 检查最终报告状态
        const finalReportMessage = lastMessageItems.messagesIds
          .map(msgId => this.store.getMessageById(msgId))
          .find(msg =>
            msg?.type === MessageType.REPORT &&
            isFinalReportMessage(msg) &&
            !msg.parentMessageId
          );

        // 判断最终报告是否生成成功
        let isReportSuccess = false;
        if (finalReportMessage) {
          const content = finalReportMessage.content;
          if (content && typeof content === 'object' && !('url' in content)) {
            const objContent = content as JSONObject;
            const hasResponseContent = !!(objContent.response_content as string | undefined)?.trim();
            const hasException = !!(objContent.exception_info as string | undefined)?.trim();
            isReportSuccess = hasResponseContent && !hasException;
          }
        } else {
          console.warn('[ALL END] Final report not found, marking all as FAILED');
        }

        // 2. 根据最终报告状态标记未完成的消息
        this.markAllIncompleteMessages(
          lastMessageItems,
          isReportSuccess ? TaskStatus.COMPLETED : TaskStatus.FAILED
        );

        // 3. 如果最终报告失败且为空，设置默认异常信息
        if (finalReportMessage && !isReportSuccess) {
          const content = finalReportMessage.content;
          const objContent = typeof content === 'object' && content ? content as JSONObject : null;
          const contentIsEmpty = !content ||
            (typeof content === 'string' && content.trim() === '') ||
            (objContent && !('url' in objContent) &&
             (!objContent.response_content || String(objContent.response_content).trim() === '') &&
             (!objContent.exception_info || String(objContent.exception_info).trim() === ''));

          if (contentIsEmpty) {
            updateMessage(lastMessageItems.id, finalReportMessage.id, {
              content: {
                response_content: '',
                exception_info: i18n.t('apps.deepSearch.finalReportStatus.noDataError'),
                citation_messages: null,
              } as JSONObject,
            });
          }
        }

        // 4. 清理所有尚未 flush 的 deferred sub-reporter 状态
        this.clearDeferredSubReporterStatuses();

        // 5. 更新整个 MessageItems 的状态为 COMPLETED
        updateMessageItems(lastMessageItems.id, {
          status: TaskStatus.COMPLETED,
        });

        return;
      }
    }

    // 其他 summary_response
    addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), sseData.content || '', undefined, undefined, 'deepsearch', buildIndexPath());
  }

  /**
   * 处理 user_feedback_processor 的 message 事件
   * 当开启 user_feedback_processor_enable 时，报告生成完成后会发送 final_result
   * 每次 AI 改写后都会发送新的 final_result，创建新的报告卡片
   */
  private handleUserFeedbackProcessorMessage(sseData: SSEData): void {
    const { addSystemMessage, updateMessage, updateMessageItems } = this.store;
    const lastMessageItems = this.store.getLastMessageItems();
    if (!lastMessageItems) return;

    // 使用工具函数解析 final_result
    const finalResult = parseSSEContent(sseData.content, null as any);
    if (!finalResult || (!finalResult.response_content && !finalResult.final_result)) {
      console.warn('[DeepsearchSSEHandler] No valid final_result in user_feedback_processor message');
      return;
    }

    // 提取实际的 final_result（可能在 nested 结构中）
    const actualFinalResult = finalResult.final_result || finalResult;
    const responseContent = actualFinalResult.response_content || '';
    const citationMessages = actualFinalResult.citation_messages || {};
    const inferMessages = actualFinalResult.infer_messages || [];
    const chartMessages = actualFinalResult.chart_messages || [];

    // 构建 content 对象
    const reportContent = {
      response_content: responseContent,
      citation_messages: citationMessages,
      infer_messages: inferMessages,
      chart_messages: chartMessages,
    };

    // 查找是否存在正在进行中的最终报告（由 SECTION END 创建的占位报告）
    const existingInProgressReport = lastMessageItems.messagesIds
      .map(msgId => this.store.getMessageById(msgId))
      .filter((msg): msg is Message => msg !== undefined)
      .find(msg =>
        msg.type === MessageType.REPORT &&
        isFinalReportMessage(msg) &&
        !msg.parentMessageId &&
        isTaskOngoing(msg.status)
      );

    // 查找 outline 任务（根节点）
    const outlineTask = this.findTaskInMessages(
      lastMessageItems.messagesIds,
      msg => msg.type === MessageType.TASK && msg.sectionIdx === 0
    );

    if (existingInProgressReport) {
      // 情况1: 存在进行中的报告 → 更新现有报告的内容和状态
      updateMessage(lastMessageItems.id, existingInProgressReport.id, {
        content: reportContent,
        status: TaskStatus.COMPLETED,
        isStreaming: false,
      });
      console.log('[DeepsearchSSEHandler] Updated existing IN_PROGRESS report with content');

      // 更新 outline 任务（根节点）状态为 COMPLETED
      if (outlineTask) {
        updateMessage(lastMessageItems.id, outlineTask.id, {
          status: TaskStatus.COMPLETED,
        });
      }
    } else {
      // 情况2: 不存在进行中的报告 → 创建新报告卡片（AI 改写后生成新版本）
      const finalReportMessage = addSystemMessage(
        this.conversationId,
        MessageType.REPORT,
        reportContent,
        undefined,
        MESSAGE_TITLES.FINAL_REPORT,
        'deepsearch',
        buildIndexPath(0, 0, 0)
      );
      if (finalReportMessage) {
        updateMessage(lastMessageItems.id, finalReportMessage.id, {
          status: TaskStatus.COMPLETED,
          isStreaming: false,
        });

        // 使用带缓存的 findTaskInMessages 查找 outline 任务并添加到思维链
        const outlineTask = this.findTaskInMessages(
          lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.sectionIdx === 0
        );

        if (outlineTask) {
          this.addFinalReportToMindMap(finalReportMessage.id, lastMessageItems.id, outlineTask);
          // 更新 outline 任务（根节点）状态为 COMPLETED
          updateMessage(lastMessageItems.id, outlineTask.id, {
            status: TaskStatus.COMPLETED,
          });
        }
        console.log('[DeepsearchSSEHandler] Created new final report from user_feedback_processor');
      }
    }

    // 更新 MessageItems 状态为 COMPLETED
    updateMessageItems(lastMessageItems.id, { status: TaskStatus.COMPLETED });
    console.log('[DeepsearchSSEHandler] Updated MessageItems status to COMPLETED');
  }

  /** 处理 waiting_user_input 事件
   */
  private handleWaitingUserInput(sseData: SSEData): void {
    const { addSystemMessage, getLastMessageItems, saveConversationToDB } = this.store;

    // 检查当前 MessageItems 状态，如果已经是 CANCELLED，说明用户已手动取消，不需要再创建消息
    const lastMessageItems = getLastMessageItems();

    if (lastMessageItems && lastMessageItems.status === TaskStatus.CANCELLED) {
      console.log('[DeepsearchSSEHandler] MessageItems already cancelled, skipping waiting_user_input event');
      return;
    }

    // 处理 user_feedback_processor 的 waiting_user_input 事件
    // 此时报告已经生成完成，后端保持连接等待用户发起 AI 改写操作
    // 不需要创建中断消息，用户可以主动对 report 进行编辑
    if (sseData.agent === AGENT_NAMES.USER_FEEDBACK_PROCESSOR) {
      // 给 SESSION_CONVERSATION_ID 赋值
      if (sseData.conversation_id) {
        this.store.setSessionConversationId(sseData.conversation_id);
      }
      saveConversationToDB(this.conversationId);
      console.log('[DeepsearchSSEHandler] user_feedback_processor waiting for user feedback action');
      return;
    }

    // 根据 agent 类型创建不同类型的消息
    const isOutlineInteraction = sseData.agent === DeepsearchAgentType.OUTLINE_INTERACTION;
    const messageType = isOutlineInteraction ? MessageType.OUTLINE_INTERACTION : MessageType.INTERRUPT;
    const currentRound = isOutlineInteraction ? this.parseOutlineInteractionRound(sseData.content) : undefined;
    const remainingRoundsInfo = this.buildOutlineInteractionRemainingInfo(currentRound);

    // 获取大纲内容（如果是 outline_interaction，需要从缓存中获取 outline 的内容）
    let outlineContent: any = sseData.content || '';
    if (isOutlineInteraction) {
      const cachedOutline = this.getOutlineContentFromCache();
      if (cachedOutline) {
        outlineContent = remainingRoundsInfo ? {
          ...cachedOutline,
          outlineInteractionCurrentRound: remainingRoundsInfo.currentRound,
          outlineInteractionRemainingRounds: remainingRoundsInfo.remainingRounds,
          outlineInteractionRemainingTip: remainingRoundsInfo.tip,
        } : cachedOutline;
        this.streamCache.set('__outline_content__', [JSON.stringify(outlineContent)]);
      }
    }

    // 创建消息
    const message = addSystemMessage(
      this.conversationId,
      messageType,
      outlineContent,
      undefined,
      undefined,
      'deepsearch', 
      buildIndexPath()
    );

    // 如果创建失败（例如对话已被取消），跳过后续处理
    if (!message || !lastMessageItems) {
      return;
    }

    // 更新消息状态
    if(lastMessageItems){
      this.store.updateMessage(lastMessageItems.id, message.id, {
        status: TaskStatus.IN_PROGRESS,
        isStreaming: false,
      });
    }

    // 给 SESSION_CONVERSATION_ID 赋值
    if (sseData.conversation_id) {
      this.store.setSessionConversationId(sseData.conversation_id);
    }

    saveConversationToDB(this.conversationId);
  }


  /**
   * 处理 user_input_ended 事件
   * 当大纲交互达到最大修改次数时触发，创建 TASK 消息显示大纲并继续流程
   */
  private handleUserInputEnded(sseData: SSEData): void {
    const { getLastMessageItems } = this.store;
    const lastMessageItems = getLastMessageItems();

    // 检查当前 MessageItems 状态
    if (lastMessageItems && lastMessageItems.status === TaskStatus.CANCELLED) {
      return;
    }

    // 从缓存中获取大纲内容
    const outlineContent = this.getOutlineContentFromCache();
    if (!outlineContent) {
      console.warn('[DeepsearchSSEHandler] No outline content stored in cache');
      return;
    }

    if (!lastMessageItems) {
      console.warn('[DeepsearchSSEHandler] No lastMessageItems found');
      return;
    }

    try {
      const taskMessage = this.createRootTaskFromOutline(outlineContent);
      if (!taskMessage) {
        return;
      }

      // 给 SESSION_CONVERSATION_ID 赋值
      if (sseData.conversation_id) {
        this.store.setSessionConversationId(sseData.conversation_id);
      }
    } catch (e) {
      console.error('[DeepsearchSSEHandler] Failed to process outline content:', e);
    }
  }


  /**
   * 处理 error 事件
   * error 事件包含 exception_info，需要更新到最终报告
   */

  private handleError(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { updateMessage, addSystemMessage, getMessageItemsIsUser } = this.store;
    const lastMessageItems = this.store.getLastMessageItems();

    // 如果不存在 lastMessageItems 或 不是用户消息且非end， 跳过处理
    if (!lastMessageItems || (getMessageItemsIsUser(lastMessageItems) && sseData.agent != DeepsearchAgentType.END)) return;

    // 解析 error content
    let errorData = null;
    if (typeof sseData.content === 'string' && sseData.content.trim().startsWith('{')) {
      try {
        errorData = JSON.parse(sseData.content);
      } catch (e) {
        console.error('[DeepsearchSSEHandler] Failed to parse error content as JSON:', e);
      }
    } else if (typeof sseData.content === 'object' && sseData.content !== null) {
      errorData = sseData.content;
    }

    if (errorData && errorData.exception_info) {
      // 如果是 end agent 的 error，更新最终报告
      if (sseData.agent === DeepsearchAgentType.END) {
        // 找到最终报告 message（与 outline_task 同级的 REPORT）
        const finalReportMessage = lastMessageItems.messagesIds
          .map(msgId => this.store.getMessageById(msgId))
          .find(msg =>
            msg?.type === MessageType.REPORT &&
            isFinalReportMessage(msg) &&
            !msg.parentMessageId  // ← 确保是顶级 message
          );

        if (finalReportMessage) {
          updateMessage(lastMessageItems.id, finalReportMessage.id, {
            content: errorData,
          });
        } else {
          console.warn('[DeepsearchSSEHandler] Final report not found, creating new one');
          // 如果没找到，创建新的最终报告
          const newReport = addSystemMessage(
            this.conversationId,
            MessageType.REPORT,
            errorData,
            undefined,
            MESSAGE_TITLES.FINAL_REPORT,
            'deepsearch',  // agent 类型
            buildIndexPath(0, 0, 0)
          );
          if (newReport) {
            updateMessage(lastMessageItems.id, newReport.id, {
                status: TaskStatus.FAILED,
                isStreaming: false,
              });
            // 将最终报告添加至思维链中
            this.addFinalReportToMindMap(newReport.id, lastMessageItems.id);
          }
        }
      }
    }

    // collector_info_retrieval 和 collector_summary 的错误处理
    if ([DeepsearchAgentType.COLLECTOR_INFO_RETRIEVAL, DeepsearchAgentType.COLLECTOR_SUMMARY].includes(sseData.agent as DeepsearchAgentType) &&
        sectionIdx !== undefined && planIdx !== undefined && stepIdx !== undefined) {

      // 使用 indexPath 查找 sectionTask
      const sectionIndexPath = buildIndexPath(sectionIdx, 0, 0);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.indexPath === sectionIndexPath,
        `section_${sectionIdx}`
      );

      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found for error, sectionIdx:', sectionIdx);
        // 跳过后续处理，继续执行 end agent 的清理逻辑（如果是 end 的话）
      } else {
        const sectionChildren = this.store.getChildMessages(sectionTask.id);
        // 使用 indexPath 查找 planTask，而不是依赖 title
        const planIndexPath = buildIndexPath(sectionIdx, planIdx, 0);
        const planTask = sectionChildren.find(task => task.indexPath === planIndexPath);

        if (!planTask) {
          console.warn('[DeepsearchSSEHandler] Plan task not found for error, planIdx:', planIdx);
          // 跳过后续处理
        } else {
          const planChildren = this.store.getChildMessages(planTask.id);
          const stepTask = planChildren[stepIdx - 1];

          if (!stepTask) {
            console.warn('[DeepsearchSSEHandler] Step task not found for error, stepIdx:', stepIdx);
            // 跳过后续处理
          } else {
            // collector_info_retrieval 错误处理
            if (sseData.agent === DeepsearchAgentType.COLLECTOR_INFO_RETRIEVAL) {
              // 和正常流程一样，解析 content
              let parsedContent: JSONObject;
              if (typeof sseData.content === 'string') {
                try {
                  parsedContent = JSON.parse(sseData.content);
                } catch (e) {
                  console.error('[DeepsearchSSEHandler] Failed to parse error content as JSON:', e);
                  parsedContent = { title: sseData.content };
                }
              } else if (sseData.content && typeof sseData.content === 'object') {
                parsedContent = sseData.content;
              } else {
                parsedContent = {};
              }

              const contentTitle = (parsedContent?.title as string | undefined) || i18n.t('deepResearch.handler.searchResult');
              const messageTitle = `collector_info_retrieval: ${contentTitle || i18n.t('deepResearch.handler.searchResult')}`;

              const childMessage = this.store.addMessageAsChild(
                lastMessageItems.id,
                stepTask.id,
                MessageType.LINK,
                parsedContent,
                messageTitle,
                buildIndexPath(sectionIdx, planIdx, stepIdx)
              );

              updateMessage(lastMessageItems.id, childMessage.id, {
                status: TaskStatus.FAILED,
                isStreaming: false,
              });
              // 不更新 stepTask 状态
            }
            // collector_summary 错误处理
            else if (sseData.agent === DeepsearchAgentType.COLLECTOR_SUMMARY) {
              // 和正常流程一样，content 是字符串
              const summaryContent = typeof sseData.content === 'string'
                ? sseData.content
                : String(sseData.content || '');

              const childMessage = this.store.addMessageAsChild(
                lastMessageItems.id,
                stepTask.id,
                MessageType.TEXT,
                summaryContent,
                i18n.t('deepResearch.handler.informationSummary'),
                buildIndexPath(sectionIdx, planIdx, stepIdx)
              );

              updateMessage(lastMessageItems.id, childMessage.id, {
                status: TaskStatus.FAILED,
                isStreaming: false,
              });

              // 更新 stepTask 状态为 FAILED
              updateMessage(lastMessageItems.id, stepTask.id, {
                status: TaskStatus.FAILED,
              });

              // 检查 plan 的所有子任务是否都完成或失败
              const planChildren = this.store.getChildMessages(planTask.id);
              const allStepsFinished = planChildren.every(step => !isTaskOngoing(step.status));

              if (allStepsFinished) {
                // 检查是否有任何一个 step 失败，如果有则 planTask 也失败
                const hasFailedStep = planChildren.some(step => step.status === TaskStatus.FAILED);
                updateMessage(lastMessageItems.id, planTask.id, {
                  status: hasFailedStep ? TaskStatus.FAILED : TaskStatus.COMPLETED,
                });
              }
            }
          }
        }
      }
    }

    // 如果是 end agent 的 error, 更新 lastMessageItems的状态为COMPLETED，所有未完成的Message标志为FAILED
    if (sseData.agent === DeepsearchAgentType.END) {
      // 先将所有未完成的消息标记为 FAILED
      this.markAllIncompleteMessages(lastMessageItems, TaskStatus.FAILED);
      // 再更新 MessageItems 的状态
      this.store.updateMessageItems(lastMessageItems.id, { status: TaskStatus.COMPLETED });
    }
  }

  // ===== 辅助方法 =====

  /**
   * 递归更新未完成任务及其所有子孙的状态
   * 只更新状态为 PENDING 或 IN_PROGRESS 或 REPORTING 的任务
   * @param taskId 任务ID
   * @param messageItemsId MessageItems ID
   * @param updateStatus 要更新的目标状态
   * @param timestamp 可选的时间戳，默认为当前时间
   * @returns 受影响的任务数量
   */
  private updateUnfinishedTasksRecursively(
    taskId: string,
    messageItemsId: string,
    updateStatus: TaskStatus,
    timestamp?: number
  ): number {
    const task = this.store.getMessageById(taskId);
    if (!task) return 0;

    const now = timestamp ?? Date.now();
    let count = 0;

    const updateRecursively = (currentTaskId: string): void => {
      const currentTask = this.store.getMessageById(currentTaskId);
      if (!currentTask) return;

      // 递归更新所有子孙
      const children = this.store.getChildMessages(currentTask.id);
      children.forEach(child => updateRecursively(child.id));

      // 只更新进行中状态的任务
      if (isTaskOngoing(currentTask.status)) {
        let finalStatus = updateStatus; // 默认使用传入的 updateStatus

        /// 如果当前updateMessage是step的任务，作特殊处理
        if (currentTask.type === MessageType.TASK && currentTask.indexPath) {
          // 1. 判断是否是 step 任务：type 是 TASK，indexPath 符合 "x-y-z" 格式，x,y,z >= 1
          // 检查 indexPath 的三个部分是否都 >= 1（排除 "0-1-1" 等情况）
          const [section, plan, step] = currentTask.indexPath.split('-').map(Number);
          const isValidStepTask = section >= 1 && plan >= 1 && step >= 1;
          if (isValidStepTask) {
            // 2. 检查子消息条件：有 summary（TEXT）但没有 link（LINK）
            const childMessages = this.store.getChildMessages(currentTask.id);
            const hasLink = childMessages.some(msg => msg.type === MessageType.LINK);
            // const hasSummary = childMessages.some(msg => msg.type === MessageType.TEXT);
            // 3. 如果满足条件，状态更新为失败；
            // if (hasSummary && !hasLink) {
            if (!hasLink) {
              finalStatus = TaskStatus.FAILED;
            }
          }
        }

        this.store.updateMessage(messageItemsId, currentTask.id, {
          status: finalStatus,
          updatedAt: now,
        });
        count++;
      }
    };

    updateRecursively(taskId);
    return count;
  }

  /**
   * 查找 section 下已存在的章节报告
   * @param sectionTask 章节 task 消息
   * @returns 已存在的章节报告消息，如果不存在则返回 null
   */
  private findExistingChapterReport(sectionTask: Message): Message | null {
    const childMessages = this.store.getChildMessages(sectionTask.id);

    // 查找 type=REPORT 且 indexPath 符合 "{i}-0-0" 格式的消息（i为自然数）
    const existingReport = childMessages.find(msg =>
      msg.type === MessageType.REPORT &&
      /^\d+-0-0$/.test(msg.indexPath || '')
    );

    return existingReport || null;
  }

  /**
   * 将 outline 节点添加到思维链中
   * @param lastMessageId 最后一条消息的id
   * @param lastMessageItemsId MessageItems ID
   */
  private addOutlineToMindMap(
    lastMessageId: string,
    lastMessageItemsId: string
  ): void {
    try {
      const mindMapManagers = this.store.getOrCreateMindMapManager(lastMessageItemsId);
      // OUTLINE节点添加到章节图中
      mindMapManagers.sectionGraph.addNode({
        messageId: lastMessageId,
        type: ThoughtNodeType.OUTLINE,
      });

      // OUTLINE节点添加到任务图中
      mindMapManagers.taskGraph.addNode({
        messageId: lastMessageId,
        type: ThoughtNodeType.OUTLINE,
      });

      // 生成 OUTLINE 节点的深度
      mindMapManagers.sectionGraph.regenerateNodeDepth(lastMessageId);
      mindMapManagers.taskGraph.regenerateNodeDepth(lastMessageId);
    } catch (error) {
      console.error('[DeepsearchSSEHandler] Failed to add outline node to mind map:', error);
    }
  }

  /**
   * 将 section 任务节点添加到思维链中
   * @param sectionTaskId section 任务消息的id
   * @param lastMessageItemsId MessageItems ID
   */
  private addSectionTaskToMindMap(
    sectionTaskId: string,
    lastMessageItemsId: string
  ): void {
    try {
      // 1. 获取 sectionTask
      const sectionTask = this.store.getMessageById(sectionTaskId);
      if (!sectionTask) {
        console.error('[DeepsearchSSEHandler] Section task not found:', sectionTaskId);
        return;
      }

      // 2. 获取父 outline 任务ID
      const outlineTaskId = sectionTask.parentMessageId;
      if (!outlineTaskId) {
        console.error('[DeepsearchSSEHandler] Section task has no parent message id');
        return;
      }

      // 3. 获取思维链管理器集合
      const mindMapManagers = this.store.getOrCreateMindMapManager(lastMessageItemsId);
      
      // 4. 添加 SECTION 节点添加到 sectionGraph 中
      mindMapManagers.sectionGraph.addNode({
        messageId: sectionTaskId,
        type: ThoughtNodeType.SECTION,
      });
      
      // 5. SECTION节点也添加到taskGraph中（因为task图包含所有节点）
      mindMapManagers.taskGraph.addNode({
        messageId: sectionTaskId,
        type: ThoughtNodeType.SECTION,
      });
      
      // 添加 section与outline的 PARENT 边
      mindMapManagers.taskGraph.addEdge({
        sourceId: outlineTaskId,
        targetId: sectionTaskId,
        relation: EdgeRelationType.PARENT,
        visible: true,
      });

      // 下面往 sectionGraph 添加章节的边
      const dependOnMessageIds = sectionTask.dependOnMessageIds || {};
      if (Object.keys(dependOnMessageIds).length > 0) {
        // 6. 往 sectionGraph 添加章节之间的依赖关系：如果 dependOnMessageIds 非空，则往图中加边
        Object.entries(dependOnMessageIds).forEach(([sourceId, label]) => {
          mindMapManagers.sectionGraph.addEdge({
            sourceId: sourceId,
            targetId: sectionTaskId,
            relation: EdgeRelationType.SECTION_DEPEND,
            label: label,
            visible: true,
          });
        });
      }
      else{
        // 7. 往 sectionGraph 添加 section与outline的 PARENT 边，只有章节无依赖的章节才添加
        mindMapManagers.sectionGraph.addEdge({
          sourceId: outlineTaskId,
          targetId: sectionTaskId,
          relation: EdgeRelationType.PARENT,
          visible: true,
        });
      }
            
      // 8. 生成 章节 节点的深度
      mindMapManagers.sectionGraph.regenerateNodeDepth(sectionTaskId);
      mindMapManagers.taskGraph.regenerateNodeDepth(sectionTaskId);
      
    } catch (error) {
      console.error('[DeepsearchSSEHandler] Failed to add section task to mind map:', error);
    }
  }

  /**
   * 将 plan 任务节点添加到思维链中
   * @param planTaskId plan 任务消息的id
   * @param lastMessageItemsId MessageItems ID
   */
  private addPlanTaskToMindMap(
    planTaskId: string,
    lastMessageItemsId: string
  ): void {
    try {
      // 1. 获取 planTask
      const planTask = this.store.getMessageById(planTaskId);
      if (!planTask) {
        console.error('[DeepsearchSSEHandler] Plan task not found:', planTaskId);
        return;
      }

      // 2. 获取父 sectionTask
      const sectionTaskId = planTask.parentMessageId;
      if (!sectionTaskId) {
        console.error('[DeepsearchSSEHandler] Plan task has no parent message id');
        return;
      }

      // 3. 获取思维链管理器集合
      const mindMapManagers = this.store.getOrCreateMindMapManager(lastMessageItemsId);
      
      // 4. 添加 PLAN 节点到 taskGraph 中
      mindMapManagers.taskGraph.addNode({
        messageId: planTaskId,
        type: ThoughtNodeType.PLAN,
      });

      // 5. 添加DEPEND边：将dependOnPlanIds中所有的边均添加至思维链中，类型根据是否跨章节决定，且可见
      const dependOnPlanIds = planTask.dependOnMessageIds || {};
      if (Object.keys(dependOnPlanIds).length > 0) {
        Object.entries(dependOnPlanIds).forEach(([sourceId, label]) => {
          const sourceMessage = this.store.getMessageById(sourceId);
          const sourceParentId = sourceMessage?.parentMessageId;
          // 判断是否跨章节依赖：如果source和target的parentId不一样，则为跨章节依赖
          const isCrossSection = sourceParentId !== planTask.parentMessageId;
          mindMapManagers.taskGraph.addEdge({
            sourceId: sourceId,
            targetId: planTaskId,
            relation: isCrossSection ? EdgeRelationType.CROSS_SECTION_DEPEND : EdgeRelationType.PLAN_DEPEND,
            // label: label,
            visible: true,
          });
        });
      }

      // 6. 判断是否添加PARENT边：只有当plan节点的父节点sectionTask的.id，不在dependOnPlanIds中所有节点的父节点集合中时才添加
      let shouldAddParentEdge = true;

      if (Object.keys(dependOnPlanIds).length > 0) {
        // 获取所有被依赖的 plan 的父节点ID集合
        const parentIdsOfDependedPlans = Object.keys(dependOnPlanIds)
          .map(planId => this.store.getMessageById(planId)?.parentMessageId)
          .filter((id): id is string => id !== undefined);

        // 判断 sectionTask.id 是否在这些父节点ID中
        shouldAddParentEdge = !parentIdsOfDependedPlans.includes(sectionTaskId);
      }

      if (shouldAddParentEdge) {
        mindMapManagers.taskGraph.addEdge({
          sourceId: sectionTaskId,
          targetId: planTaskId,
          relation: EdgeRelationType.PARENT,
          visible: true,
        });
      }

      // 7. 生成 章节 节点的深度
      mindMapManagers.taskGraph.regenerateNodeDepth(planTaskId);

    } catch (error) {
      console.error('[DeepsearchSSEHandler] Failed to add plan task to mind map:', error);
    }
  }

  /**
   * 将子报告节点添加至思维链中
   * @param subReportMessageId 子报告消息的id
   * @param lastMessageItemsId MessageItems ID
   */
  private addSubReportToMindMap(
    subReportMessageId: string,
    lastMessageItemsId: string
  ): void {
    try {
      // 1. 获取子报告消息
      const subReportMessage = this.store.getMessageById(subReportMessageId);
      if (!subReportMessage) {
        console.error('[DeepsearchSSEHandler] Sub report message not found:', subReportMessageId);
        return;
      }

      // 2. 获取父 sectionTask 的ID
      const sectionTaskId = subReportMessage.parentMessageId;
      if (!sectionTaskId) {
        console.error('[DeepsearchSSEHandler] Sub report has no parent message id');
        return;
      }

      // 3. 获取思维链管理器集合
      const mindMapManagers = this.store.getOrCreateMindMapManager(lastMessageItemsId);
      
      // 4. 添加子报告节点到 taskGraph 中
      mindMapManagers.taskGraph.addNode({
        messageId: subReportMessage.id,
        type: ThoughtNodeType.SUB_REPORT,
      });

      // 5. 获取 section 下所有的 plan 节点集合（排除子报告节点本身）
      const sectionChildren = this.store.getChildMessages(sectionTaskId);
      const planNodes = sectionChildren.filter(msg => msg.type === MessageType.TASK);

      // 6. 添加 章节报告与章节中各 plan任务的 DEPEND 边
      planNodes.forEach(planNode => {
        // 获取 plan 节点在思维链图中的子节点
        const childNodesInGraph = mindMapManagers.taskGraph.getChildNodes(planNode.id);

        // 判断：如果 plan 节点的子节点中有一个在 planNodes 集合中，则不添加边
        const hasChildInPlanSet = childNodesInGraph.some((childNode: ThoughtNode) =>
          planNodes.some(plan => plan.id === childNode.messageId)
        );

        // 只有在 plan 节点的子节点不在 planNodes 集合中时，才添加边
        if (!hasChildInPlanSet) {
          mindMapManagers.taskGraph.addEdge({
            sourceId: planNode.id,
            targetId: subReportMessage.id,
            relation: EdgeRelationType.REPORT_DEPEND,
            visible: true,
          });
        }
      });

      // 7. 生成 章节 节点的深度
      mindMapManagers.taskGraph.regenerateNodeDepth(subReportMessage.id);

    } catch (error) {
      console.error('[DeepsearchSSEHandler] Failed to add sub report to mind map:', error);
    }
  }
  
  /**
   * 将最终报告添加至思维链中
   * @param finalReportMessageId 最终报告消息的id
   * @param lastMessageItems 当前 MessageItems
   * @param outlineTask 大纲任务消息
   */
  private addFinalReportToMindMap(
    finalReportMessageId: string,
    lastMessageItemsId: string,
    outlineTask?: Message | null
  ): void {
    try {
      // 通过 ID 获取 finalReportMessage
      const finalReportMessage = this.store.getMessageById(finalReportMessageId);
      if (!finalReportMessage) {
        console.error('[DeepsearchSSEHandler] Final report message not found:', finalReportMessageId);
        return;
      }

      // 如果 outlineTask 输入的是空的，则先取outlineTask
      if (!outlineTask) {
        // 通过 ID 获取 MessageItems
        const messageItems = this.store.getMessageItemsById(lastMessageItemsId);
        if (!messageItems) return;

        // 遍历 messageItems.messagesIds 查找 outlineTask
        for (const messageId of messageItems.messagesIds) {
          const message = this.store.getMessageById(messageId);
          if (message && message.type === MessageType.TASK && message.indexPath === "0-0-0") {
            outlineTask = message;
            break;
          }
        }
      }

      // 如果 outlineTask 还是为空，直接返回
      if (!outlineTask) {
        return;
      }

      const mindMapManagers = this.store.getOrCreateMindMapManager(lastMessageItemsId);

      // 1. 添加最终报告节点
      mindMapManagers.sectionGraph.addNode({
        messageId: finalReportMessage.id,
        type: ThoughtNodeType.FINAL_REPORT,
      });

      mindMapManagers.taskGraph.addNode({
        messageId: finalReportMessage.id,
        type: ThoughtNodeType.FINAL_REPORT,
      });

      // 2. 如果存在 outlineTask，找到所有章节的子报告并添加 DEPEND 边
      const outlineChildren = this.store.getChildMessages(outlineTask.id);

      // 筛选出所有 SECTION 类型的节点
      const sectionTasks = outlineChildren.filter(msg => msg.type === MessageType.TASK && (msg.sectionIdx ?? 0) > 0);

      // 遍历每个 section，查找其子报告
      sectionTasks.forEach(sectionTask => {
        // 1. 往 sectionGraph 添加 章节 和 最终报告的边
        // 检查该章节在 sectionGraph 中是否已有出边，如果没有则添加指向最终报告的边
        const sectionChildEdges = mindMapManagers.sectionGraph.getChildEdges(sectionTask.id);
        if (sectionChildEdges.length === 0) {
          mindMapManagers.sectionGraph.addEdge({
            sourceId: sectionTask.id,
            targetId: finalReportMessage.id,
            relation: EdgeRelationType.REPORT_DEPEND,
            visible: true,
          });
        }

        // 2. 往 taskGraph 添加 章节报告和最终报告的边
        const sectionChildren = this.store.getChildMessages(sectionTask.id);

        // 2.1 查找该 section 下的 REPORT 类型消息（章节报告）
        const chapterReports = sectionChildren.filter(msg =>
          msg.type === MessageType.REPORT
        );

        // 2.2 为每个章节报告添加指向最终报告的 DEPEND 边
        chapterReports.forEach(chapterReport => {
          mindMapManagers.taskGraph.addEdge({
            sourceId: chapterReport.id,
            targetId: finalReportMessage.id,
            relation: EdgeRelationType.REPORT_DEPEND,
            visible: true,
          });
        });
      });

      // 3. 将2张图的节点深度都重新计算一遍
      mindMapManagers.sectionGraph.regenerateAllDepths();
      mindMapManagers.taskGraph.regenerateAllDepths();

    } catch (error) {
      console.error('[DeepsearchSSEHandler] Failed to add final report to mind map:', error);
    }
  }

  /**
   * 生成流缓存 key
   */
  private generateStreamKey(agent: string, sectionIdx?: number, planIdx?: number, stepIdx?: number): string {
    const parts = [agent];
    if (sectionIdx !== undefined) parts.push(sectionIdx.toString());
    if (planIdx !== undefined) parts.push(planIdx.toString());
    if (stepIdx !== undefined) parts.push(stepIdx.toString());
    return parts.join('_');
  }

  /**
   * 追加内容到缓存
   */
  private addToCache(key: string, content: string): void {
    const chunks = this.streamCache.get(key) || [];
    this.streamCache.set(key, [...chunks, content]);
  }

  private parseOutlineInteractionRound(content?: string | JSONObject): number | undefined {
    if (typeof content !== 'string') {
      return undefined;
    }
    const match = content.match(/Round\s+(\d+)\s*:/i);
    if (!match?.[1]) {
      return undefined;
    }
    const round = Number.parseInt(match[1], 10);
    return Number.isNaN(round) ? undefined : round;
  }

  private buildOutlineInteractionRemainingInfo(currentRound?: number): {
    currentRound: number;
    remainingRounds: number;
    tip: string;
  } | null {
    if (!currentRound || currentRound <= 0) {
      return null;
    }
    const remainingRounds = Math.max(0, OUTLINE_INTERACTION_MAX_ROUNDS - currentRound + 1);
    if (remainingRounds > OUTLINE_INTERACTION_WARNING_THRESHOLD) {
      return null;
    }
    return {
      currentRound,
      remainingRounds,
      tip: i18n.t('apps.outlineInteraction.remainingRoundsWarning', { count: remainingRounds }),
    };
  }

  /**
   * 获取缓存内容
   */
  private getCacheContent(key: string): string {
    const chunks = this.streamCache.get(key);
    return chunks ? chunks.join('') : '';
  }

  private getOutlineContentFromCache(): any | null {
    const cacheKeys = [
      '__outline_content__',
      this.generateStreamKey('outline', 0, 0, 0),
      this.generateStreamKey('outline'),
    ];

    for (const key of cacheKeys) {
      const cachedContent = this.getCacheContent(key);
      if (!cachedContent) {
        continue;
      }

      try {
        return JSON.parse(cachedContent);
      } catch (e) {
        console.warn('[DeepsearchSSEHandler] Failed to parse outline content from cache:', e);
      }
    }

    return null;
  }

  private createRootTaskFromOutline(outlineContent: any): Message | null {
    const { addSystemMessage, updateMessage } = this.store;
    const title = outlineContent.title || i18n.t('deepResearch.handler.researchOutline');

    const rootTask = addSystemMessage(
      this.conversationId,
      MessageType.TASK,
      outlineContent.thought || '',
      undefined,
      title,
      'deepsearch',
      buildIndexPath(0, 0, 0)
    );

    if (!rootTask) {
      return null;
    }

    updateMessage(rootTask.messageItemsId, rootTask.id, {
      status: TaskStatus.IN_PROGRESS,
      isStreaming: false,
      sectionIdx: 0,
    });

    // 将 outline 节点添加到思维链 graph 中
    this.addOutlineToMindMap(rootTask.id, rootTask.messageItemsId);


    if (outlineContent.sections && Array.isArray(outlineContent.sections)) {
      outlineContent.sections.forEach((section: any, index: number) => {
        const sectionTitle = section.title ? `${index + 1}. ${section.title}` : i18n.t('deepResearch.handler.chapter', { index: index + 1 });
        const sectionDescription = section.description || '';

        // ===== 依赖项解析 =====
        const dependIds: string[] = Array.isArray(section.parent_ids) ? section.parent_ids : [];
        const relationships: string[] = Array.isArray(section.relationships) ? section.relationships : [];

        const dependOnMessageIds: { [id: string]: string } = {};

        // 通过 messageItemsId 获取对应的 messageItems
        const messageItems = this.store.getMessageItemsById(rootTask.messageItemsId);

        // 依赖关系后处理：只有2个相关list的长度一致时，才处理依赖关系
        if (dependIds.length > 0 && dependIds.length === relationships.length && messageItems) {
          for (let i = 0; i < dependIds.length; i++) {
            const dependIndexPath = `${dependIds[i]}-0-0`;

            // 在当前messageItems中查找对应的依赖消息
            const dependMessage = this.findTaskInMessages(
              messageItems.messagesIds,
              msg => msg.indexPath === dependIndexPath && msg.type === MessageType.TASK
            );

            if (dependMessage) {
              dependOnMessageIds[dependMessage.id] = relationships[i];
            }
          }
        }

        // 创建sectionTask
        const sectionTask = this.store.addMessageAsChild(
          rootTask.messageItemsId,
          rootTask.id,
          MessageType.TASK,
          sectionDescription,
          sectionTitle,
          buildIndexPath(index + 1, 0, 0)
        );

        updateMessage(rootTask.messageItemsId, sectionTask.id, {
          sectionIdx: index + 1,
          status: TaskStatus.PENDING,
          isStreaming: false,
          ...(Object.keys(dependOnMessageIds).length > 0 ? { dependOnMessageIds } : {}),  // 只在非空时添加
        });
        
        // 将 sectionTask 节点添加到思维链 graph 中
        this.addSectionTaskToMindMap(sectionTask.id, rootTask.messageItemsId);
      });
    }

    return rootTask;
  }

  /**
   * 在消息列表中递归查找任务（带缓存）
   */
  private findTaskInMessages(messageIds: string[], predicate: (msg: Message) => boolean, cacheKey?: string): Message | null {
    // 如果有缓存key，先检查缓存
    if (cacheKey && this.messageFindCache.has(cacheKey)) {
      return this.messageFindCache.get(cacheKey)!;
    }

    // 递归查找
    for (const messageId of messageIds) {
      const msg = this.store.getMessageById(messageId);
      if (!msg) continue;

      if (predicate(msg)) {
        // 缓存结果
        if (cacheKey) {
          this.messageFindCache.set(cacheKey, msg);
        }
        return msg;
      }
      if (msg.childMessageIds && msg.childMessageIds.length > 0) {
        const found = this.findTaskInMessages(msg.childMessageIds, predicate);
        if (found) {
          // 缓存结果
          if (cacheKey) {
            this.messageFindCache.set(cacheKey, found);
          }
          return found;
        }
      }
    }

    return null;
  }

  /**
   * 查找或创建 plan 任务
   */
  private findOrCreatePlanTask(sectionTask: Message, targetPlanIdx: number, messageItemsId: string, title?: string): Message | null {
    const childMessages = this.store.getChildMessages(sectionTask.id);

    // 使用 indexPath 查找现有的 planTask
    const planIndexPath = buildIndexPath(sectionTask.sectionIdx, targetPlanIdx, 0);
    const existingPlan = childMessages.find(task => task.indexPath === planIndexPath);

    if (existingPlan) {
      return existingPlan;
    }

    // 如果不存在indexPath，使用标题查找：如果传入了自定义 title 且非空，则使用自定义格式
    const planTitle = title && title.trim()
      ? `${sectionTask.sectionIdx}.${targetPlanIdx} ${title}`.trim()
      : i18n.t('apps.deepSearch.informationCollection', { sectionId: sectionTask.sectionIdx, planIndex: targetPlanIdx });

    const planTask = this.store.addMessageAsChild(
      messageItemsId,
      sectionTask.id,
      MessageType.TASK,
      { title: planTitle },
      planTitle,
      planIndexPath
    );

    this.store.updateMessage(messageItemsId, planTask.id, {
      status: TaskStatus.IN_PROGRESS,
      isStreaming: false,
    });

    return planTask;
  }

  /**
   * 递归标记所有未完成的消息（公共方法）
   * @param messageItems MessageItems 对象
   * @param targetStatus 目标状态：COMPLETED/FAILED/CANCELLED
   */
  public markAllIncompleteMessages(
    messageItems: MessageItems,
    targetStatus: TaskStatus.COMPLETED | TaskStatus.FAILED | TaskStatus.CANCELLED
  ): void {
    const { updateMessage, getChildMessages } = this.store;
    let count = 0;

    const markRecursively = (message: Message) => {
      // 递归处理子消息
      const children = getChildMessages(message.id);
      children.forEach(child => markRecursively(child));

      // 只标记非最终状态的消息（不包括 COMPLETED/CANCELLED/FAILED/UNKNOWN）
      const finalStatuses = [
        TaskStatus.COMPLETED,
        TaskStatus.CANCELLED,
        TaskStatus.FAILED,
        TaskStatus.UNKNOWN
      ];

      if (!finalStatuses.includes(message.status)) {
        updateMessage(messageItems.id, message.id, {
          status: targetStatus,
        });
        count++;
      }
    };

    messageItems.messagesIds.forEach(msgId => {
      const msg = this.store.getMessageById(msgId);
      if (msg) markRecursively(msg);
    });
  }
}
