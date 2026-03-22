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
} from '../useConversationStore';
import i18n from '@/i18n';

/**
 * Deepsearch SSE Handler
 *
 * 专门处理 deepsearch agent 类型的 SSE 消息
 */

// ===== 类型定义 =====

// DeepSearch SSE 事件数据类型
export interface SSEData {
  event: 'start' | 'message' | 'done' | 'summary_response' | 'waiting_user_input' | 'user_input_ended' | 'error';
  agent: string;
  content?: string | JSONObject;
  section_idx?: string | number;
  plan_idx?: string | number;
  step_idx?: string | number;
  conversation_id?: string;  // 对话的conversationId
}

interface StoreDependencies {
  getCurrentMessageItems: () => MessageItems | undefined;
  addSystemMessage: (conversationId: string, type: MessageType, content: any, parentId?: string, title?: string, agentType?: string) => Message | null;
  addMessageAsChild: (messageItemsId: string, parentId: string, type: MessageType, content: any, title?: string) => Message;
  updateMessage: (messageItemsId: string, messageId: string, updates: Partial<Message>) => void;
  deleteMessage: (messageItemsId: string, messageId: string) => void;
  updateMessageItems: (id: string, updates: Partial<MessageItems>) => void;
  appendMessageContent: (messageItemsId: string, messageId: string, content: string) => void;
  getMessageById: (id: string) => Message | undefined;
  getMessageTree: (messageId: string) => Message | null;  // 新增：获取消息树
  getChildMessages: (messageId: string) => Message[];
  getMessageItemsIsUser: (messageItems: MessageItems) => boolean;  // 新增：兼容历史数据
  setSessionConversationId: (conversationId: string | null) => void;  // 新增：设置连续对话系列ID
}

interface StreamCache {
  get: (key: string) => string[] | undefined;
  set: (key: string, chunks: string[]) => void;
  delete: (key: string) => void;
}

// ===== Handler 类 =====

export class DeepsearchSSEHandler {
  private store: StoreDependencies;
  private streamCache: StreamCache;
  private conversationId: string;
  private messageFindCache: Map<string, Message | null>;

  constructor(store: StoreDependencies, streamCache: StreamCache, conversationId: string) {
    this.store = store;
    this.streamCache = streamCache;
    this.conversationId = conversationId;
    this.messageFindCache = new Map();
  }

  /**
   * 将 deepsearch agent 类型映射到消息类型
   */
  private mapAgentToMessageType(agent: string): MessageType {
    const agentTypeMap: Record<string, MessageType> = {
      'entry': MessageType.TEXT,
      'generate_questions': MessageType.TEXT,
      'feedback_handler': MessageType.INTERRUPT,
      'outline': MessageType.TASK,
      'outline_interaction': MessageType.OUTLINE_INTERACTION,
      'plan_reasoning': MessageType.TASK,
      'sub_reporter': MessageType.REPORT,
      'collector_info_retrieval': MessageType.LINK,
      'collector_summary': MessageType.TEXT,
      'end': MessageType.REPORT,
    };
    return agentTypeMap[agent] || MessageType.TEXT;
  }

  /**
   * 主入口：处理 SSE 消息
   */
  public handleSSEMessage(sseData: SSEData): void {
    const lastMessageItems = this.store.getCurrentMessageItems();

    // 如果对话已被取消，忽略所有后续 SSE 事件
    // 这发生在用户点击取消按钮后，但 SSE 事件仍在队列中或继续到达的情况
    if (lastMessageItems && lastMessageItems.status === TaskStatus.CANCELLED) {
      console.log('[DeepsearchSSEHandler] MessageItems cancelled, ignoring SSE event:', sseData.event);
      return;
    }

    // HITL 延续场景：如果当前 MessageItems 状态为 COMPLETED，重新设置为 IN_PROGRESS
    // 这发生在用户回复 interrupt 消息后，SSE 流继续的情况
    if (lastMessageItems && !this.store.getMessageItemsIsUser(lastMessageItems)) {
      if (lastMessageItems.status === TaskStatus.COMPLETED) {
        // HITL 延续：重新激活 MessageItems 状态
        this.store.updateMessageItems(lastMessageItems.id, { status: TaskStatus.IN_PROGRESS });
      }
    }

    const sectionIdx = this.parseOptionalIndex(sseData.section_idx);
    const planIdx = this.parseOptionalIndex(sseData.plan_idx);
    const stepIdx = this.parseOptionalIndex(sseData.step_idx);

    switch (sseData.event) {
      case 'start':
        this.handleStart(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case 'message':
        this.handleMessage(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case 'done':
        this.handleDone(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case 'summary_response':
        this.handleSummaryResponse(sseData, sectionIdx, planIdx, stepIdx);
        break;
      case 'waiting_user_input':
        this.handleWaitingUserInput(sseData);
        break;
      case 'user_input_ended':
        this.handleUserInputEnded(sseData);
        break;
      case 'error':
        this.handleError(sseData, sectionIdx, planIdx, stepIdx);
        break;
    }
  }

  /**
   * 处理 start 事件
   */
  private handleStart(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { addSystemMessage, updateMessage } = this.store;

    // 生成流缓存 key
    const streamKey = this.generateStreamKey(sseData.agent, sectionIdx, planIdx, stepIdx);

    // outline: 只初始化缓存，不创建消息卡片
    if (sseData.agent === 'outline') {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.streamCache.set(streamKey, [content]);
      return;
    }

    // plan_reasoning: 初始化缓存，更新对应 section task 的状态和时间
    if (sseData.agent === 'plan_reasoning') {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.streamCache.set(streamKey, [content]);

      const lastMessageItems = this.store.getCurrentMessageItems();
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
            rootTask = this.createRootTaskFromOutline(lastMessageItems.id, outlineContent);
          } else {
            console.warn('[DeepsearchSSEHandler] No cached outline found for creating root TASK');
          }
        }

        const sectionTask = this.findTaskInMessages(
          lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
          `section_${sectionIdx}` // 添加缓存key
        );

        // 【步骤1】更新上一个 planTask (task_1_x_(n-1))
        if (planIdx > 1 && sectionTask) {
          const prevPlanTitle = i18n.t('apps.deepSearch.informationCollection', { index: planIdx - 1 });
          const prevPlanTask = this.store.getChildMessages(sectionTask.id).find(task =>
            task.title?.includes(prevPlanTitle)
          );

          if (prevPlanTask &&
              (prevPlanTask.status === TaskStatus.PENDING ||
               prevPlanTask.status === TaskStatus.IN_PROGRESS)) {
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
    if (sseData.agent === 'sub_reporter' && sectionIdx !== undefined && sectionIdx > 0) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      // 重置流缓存
      this.streamCache.set(streamKey, [content]);

      const lastMessageItems = this.store.getCurrentMessageItems();
      if (!lastMessageItems) return;

      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
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
        } else {
          // 先有条件地递归更新本章节的最后一个子Message(子Message.status=PENDING 或 IN_PROGRESS):
          const sectionChildren = this.store.getChildMessages(sectionTask.id);
          const lastChildMessage = sectionChildren.length > 0 ? sectionChildren[sectionChildren.length - 1] : null;
          if (lastChildMessage &&
              (lastChildMessage.status === TaskStatus.PENDING || lastChildMessage.status === TaskStatus.IN_PROGRESS)) {
            this.updateUnfinishedTasksRecursively(
              lastChildMessage.id,
              lastMessageItems.id,
              TaskStatus.UNKNOWN
            );
          }

          // 情况1: 不存在章节报告 - 创建新消息（原有逻辑）
          const subTitle = `${i18n.t('deepResearch.handler.chapterReport')}: ${sectionTask.title}`;
          const childMessage = this.store.addMessageAsChild(
            lastMessageItems.id,
            sectionTask.id,
            MessageType.REPORT,
            '',
            subTitle
          );

          updateMessage(lastMessageItems.id, childMessage.id, {
            status: TaskStatus.IN_PROGRESS,
            isStreaming: true,
          });
        }

      }
      return;
    }

    // entry: 初始化缓存，创建占位消息
    if (sseData.agent === 'entry') {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.streamCache.set(streamKey, [content]);

      addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), '', undefined, undefined, 'deepsearch');

      const lastMessageItems = this.store.getCurrentMessageItems();
      if (lastMessageItems) {
        const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
      const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;
        if (lastMessage) {
          updateMessage(lastMessageItems.id, lastMessage.id, {
            content: sseData.content || '',
            isStreaming: true,
          });
        }
      }
      return;
    }

    // 其他类型：创建普通TEXT消息，比如generate_questions
    const content = typeof sseData.content === 'string' ? sseData.content : '';
    addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), content, undefined, undefined, 'deepsearch');
  }

  /**
   * 处理 message 事件
   */
  private handleMessage(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const streamKey = this.generateStreamKey(sseData.agent, sectionIdx, planIdx, stepIdx);

    // outline: 追加内容到缓存，不创建消息
    if (sseData.agent === 'outline') {
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
    if (sseData.agent === 'plan_reasoning') {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.addToCache(streamKey, content);
      return;
    }

    // sub_reporter: 追加内容到缓存和消息
    if (sseData.agent === 'sub_reporter' && sectionIdx !== undefined && sectionIdx > 0) {
      const content = typeof sseData.content === 'string' ? sseData.content : '';
      this.addToCache(streamKey, content);

      const lastMessageItems = this.store.getCurrentMessageItems();
      if (!lastMessageItems) return;

      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
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

    // 其他消息：追加内容
    const lastMessageItems = this.store.getCurrentMessageItems();
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
    const lastMessageItems = this.store.getCurrentMessageItems();


    if (sseData.agent === 'outline') {
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
      // 清除缓存
      this.messageFindCache.clear();
      return;
    }

    // plan_reasoning 完成
    if (sseData.agent === 'plan_reasoning' && sectionIdx !== undefined && planIdx !== undefined) {
      let sectionTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
        msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx
      );

      // ===== 修复：如果section任务不存在（因为outline为空），动态创建 =====
      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found for plan_reasoning, creating one. sectionIdx:', sectionIdx);

        // 找到根大纲任务（sectionIdx=0）
        const rootTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
          msg.type === MessageType.TASK && msg.sectionIdx === 0
        );

        if (rootTask) {
          sectionTask = this.store.addMessageAsChild(
            lastMessageItems.id,
            rootTask.id,
            MessageType.TASK,
            i18n.t('apps.deepSearch.researchChapter', { index: sectionIdx }),
            i18n.t('apps.deepSearch.chapter', { index: sectionIdx })
          );

          updateMessage(lastMessageItems.id, sectionTask.id, {
            sectionIdx: sectionIdx,
            status: TaskStatus.PENDING,
            isStreaming: false,
          });

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

        const planTask = this.findOrCreatePlanTask(sectionTask, planIdx, lastMessageItems.id);
        
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

        // 为每个 step 创建子任务
        if (parsedContent.steps && Array.isArray(parsedContent.steps)) {
          const planChildren = this.store.getChildMessages(planTask.id);

          parsedContent.steps.forEach((step: any, _stepIndex: number) => {
            const existingStep = planChildren.find(st => st.title === step.title);
            if (existingStep) return;

            const stepTask = this.store.addMessageAsChild(
              lastMessageItems.id,
              planTask.id,
              MessageType.TASK,
              step.description || '',
              step.title
            );

            updateMessage(lastMessageItems.id, stepTask.id, {
              status: TaskStatus.PENDING,
              isStreaming: false,
            });

          });
        }

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
    if (sseData.agent === 'sub_reporter' && sectionIdx !== undefined && sectionIdx > 0) {
      const cachedContent = this.getCacheContent(streamKey);
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (sectionTask) {
        const childMessages = this.store.getChildMessages(sectionTask.id);
        if (childMessages.length > 0) {
          const lastChild = childMessages[childMessages.length - 1];
          if (lastChild) {
            updateMessage(lastMessageItems.id, lastChild.id, {
              content: cachedContent,
              status: TaskStatus.COMPLETED,
              isStreaming: false,
            });
          }
        }
      }

      this.streamCache.delete(streamKey);
      return;
    }

    // entry 完成
    if (sseData.agent === 'entry') {
      const cachedContent = this.getCacheContent(streamKey);

      const lastMessageId = lastMessageItems.messagesIds[lastMessageItems.messagesIds.length - 1];
      const lastMessage = lastMessageId ? this.store.getMessageById(lastMessageId) : undefined;

      // 检查 entry 的 content 是否为空，如果为空则删除该消息
      if (!cachedContent || cachedContent.trim() === '') {
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

      this.streamCache.delete(streamKey);
      // Entry 处理完成，直接返回，避免执行后面的通用逻辑
      return;
    }

    // end 完成：保存 DeepSearch 结果
    if (sseData.agent === 'end') {
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
          const outlineTask = this.findTaskInMessages(
            lastMessageItems.messagesIds,
            msg => msg.type === MessageType.TASK && msg.sectionIdx === 0,
            'outline_root' // 添加缓存key
          );

          if (outlineTask) {
            const finalReportTask = this.store.addMessageAsChild(
              lastMessageItems.id,
              outlineTask.id,
              MessageType.REPORT,  // 修正：应该是 REPORT 类型
              content || '',
              MESSAGE_TITLES.FINAL_REPORT
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

    // 处理完成后清除缓存
    this.messageFindCache.clear();
  }

  /**
   * 处理 summary_response 事件
   */
  private handleSummaryResponse(sseData: SSEData, sectionIdx?: number, planIdx?: number, stepIdx?: number): void {
    const { updateMessage, updateMessageItems, addSystemMessage } = this.store;
    const lastMessageItems = this.store.getCurrentMessageItems();
    if (!lastMessageItems) return;

    // collector_info_retrieval 和 collector_summary
    if (['collector_info_retrieval', 'collector_summary'].includes(sseData.agent) &&
        sectionIdx !== undefined && planIdx !== undefined && stepIdx !== undefined) {

      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
        `section_${sectionIdx}` // 添加缓存key
      );

      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found, sectionIdx:', sectionIdx);
        return;
      }

      const sectionChildren = this.store.getChildMessages(sectionTask.id);
      const planTitle = i18n.t('apps.deepSearch.informationCollection', { index: planIdx });
      const planTask = sectionChildren.find(task =>
        task.title && task.title.includes(planTitle)
      );

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

      // 【步骤0】更新上一个 stepTask (task_1_x_n_(k-1))，只在存在上一个stepTask且当前retrieval是本step的第1个retrieval时才更新
      if (stepIdx > 1 && (!stepTask.childMessageIds || stepTask.childMessageIds.length === 0)) {
        const prevStepTask = planChildren[stepIdx - 2];

        if (prevStepTask &&
            (prevStepTask.status === TaskStatus.PENDING ||
             prevStepTask.status === TaskStatus.IN_PROGRESS)) {
          // 从上一个 stepTask 开始递归更新
          this.updateUnfinishedTasksRecursively(
            prevStepTask.id,
            lastMessageItems.id,
            TaskStatus.UNKNOWN
          );
        }
      }

      // 处理 content
      if (sseData.agent === 'collector_info_retrieval') {
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
          messageTitle
        );

        /// 更新本step状态为正在进行中（只有PENDING状态才更新）
        if (stepTask.status === TaskStatus.PENDING) {
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
        i18n.t('deepResearch.handler.informationSummary')
      );

      updateMessage(lastMessageItems.id, childMessage.id, {
        status: TaskStatus.COMPLETED,
        isStreaming: false,
      });

      // 如果是 collector_summary，更新 step 状态
      if (sseData.agent === 'collector_summary') {
        updateMessage(lastMessageItems.id, stepTask.id, {
          status: TaskStatus.COMPLETED,
        });

        // 检查 plan 的所有子任务是否都完成
        const planChildren = this.store.getChildMessages(planTask.id);
        const allStepsFinished = planChildren.every(step =>
          step.status !== TaskStatus.PENDING && step.status !== TaskStatus.IN_PROGRESS
        );

        if (allStepsFinished) {
          updateMessage(lastMessageItems.id, planTask.id, {
            status: TaskStatus.COMPLETED,
          });
        }
      }

      return;
    }

    // sub_reporter: 处理章节子报告（summary_response 事件）
    if (sseData.agent === 'sub_reporter' &&
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

      // 2. 找到对应的 sectionTask
      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
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
        // 情况A: 最后一个 child 是 REPORT - 更新现有消息
        updateMessage(lastMessageItems.id, lastChild.id, {
          content: sseData.content,
          isStreaming: false,
          status: TaskStatus.FAILED,
        });
      } else {
        // 情况B: 最后一个 child 不是 REPORT 或不存在 - 创建新消息
        const subTitle = `${i18n.t('deepResearch.handler.chapterReport')}: ${sectionTask.title}`;
        const newReport = this.store.addMessageAsChild(
          lastMessageItems.id,
          sectionTask.id,
          MessageType.REPORT,
          sseData.content,
          subTitle
        );

        updateMessage(lastMessageItems.id, newReport.id, {
          isStreaming: false,
          status: TaskStatus.FAILED,
        });
      }

      // 5. 递归更新倒数第二个 child message（task_x_(N-1)_0_0）
      // 条件：N > 1 且该 message 的状态是 PENDING 或 IN_PROGRESS
      if (sectionChildren.length > 1) {
        const secondLastChild = sectionChildren[sectionChildren.length - 2];
        if (secondLastChild &&
            (secondLastChild.status === TaskStatus.PENDING ||
             secondLastChild.status === TaskStatus.IN_PROGRESS)) {
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
    if (sseData.agent === 'end') {
      const outlineTask = this.findTaskInMessages(lastMessageItems.messagesIds, msg =>
        msg.type === MessageType.TASK && msg.sectionIdx === 0
      );

      // "SECTION END" 标识 (第6点)
      if (sseData.content === 'SECTION END' && sectionIdx !== undefined) {
        const sectionTask = this.findTaskInMessages(lastMessageItems.messagesIds,
          msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx
        );

        if (sectionTask) {
          // 1. 根据 sectionTask 的最后一个子 Message 的状态来更新 sectionTask
          const sectionChildren = this.store.getChildMessages(sectionTask.id);
          const lastChildMessage = sectionChildren.length > 0 ? sectionChildren[sectionChildren.length - 1] : null;

          if (lastChildMessage) {
            if (lastChildMessage.type !== MessageType.REPORT) {
              // 最后一个子 Message 不是 REPORT 类型，将 sectionTask 更新为 FAILED
              this.updateUnfinishedTasksRecursively(
                sectionTask.id,
                lastMessageItems.id,
                TaskStatus.FAILED
              );
            } else {
              // 最后一个子 Message 是 REPORT 类型，根据其状态决定 sectionTask 的状态
              let targetStatus = lastChildMessage.status;

              // 如果子 REPORT 的状态是 PENDING 或 IN_PROGRESS，将其变为 UNKNOWN
              if (targetStatus === TaskStatus.PENDING || targetStatus === TaskStatus.IN_PROGRESS) {
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
          const allChildrenFinished = outlineChildren.every(child =>
            child.status !== TaskStatus.PENDING && child.status !== TaskStatus.IN_PROGRESS
          );

          if (allChildrenFinished) {
            // 创建最终报告 message（与 outline_task 同级）
            const finalReportMessage = addSystemMessage(
              this.conversationId,
              MessageType.REPORT,
              '',  // 初始 content 为空
              undefined,  // parentId 为 undefined，与 outline_task 同级
              MESSAGE_TITLES.FINAL_REPORT,
              'deepsearch'  // agent 类型
            );
            if (finalReportMessage) {
              updateMessage(lastMessageItems.id, finalReportMessage.id, {
                status: TaskStatus.IN_PROGRESS,
                isStreaming: false,
              });
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
            (msg.status === TaskStatus.PENDING || msg.status === TaskStatus.IN_PROGRESS) &&
            isFinalReportMessage(msg.title) &&
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
          // 只有在存在 outline 任务时才创建最终报告
          // 如果没有 outline 任务，说明这不是真正的研究请求，不需要创建最终报告
          if (outlineTask || endData.exception_info) {
            console.warn('[DeepsearchSSEHandler] No pending REPORT message found, creating new one');
            const finalReportMessage = addSystemMessage(
              this.conversationId,
              MessageType.REPORT,
              endData || '',
              undefined,  // 与 outline_task 同级
              MESSAGE_TITLES.FINAL_REPORT,
              'deepsearch'  // agent 类型
            );
            if (finalReportMessage) {
              updateMessage(lastMessageItems.id, finalReportMessage.id, {
                status: TaskStatus.COMPLETED,
                isStreaming: false,
              });
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
                  'deepsearch'
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
            isFinalReportMessage(msg.title) &&
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
        this.markAllIncompleteMessages(lastMessageItems, isReportSuccess);

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

        // 4. 更新整个 MessageItems 的状态为 COMPLETED
        updateMessageItems(lastMessageItems.id, {
          status: TaskStatus.COMPLETED,
        });

        return;
      }
    }

    // 其他 summary_response
    addSystemMessage(this.conversationId, this.mapAgentToMessageType(sseData.agent), sseData.content || '', undefined, undefined, 'deepsearch');
  }

  /** 处理 waiting_user_input 事件
   */
  private handleWaitingUserInput(sseData: SSEData): void {
    const { addSystemMessage, updateMessage, getCurrentMessageItems } = this.store;

    // 检查当前 MessageItems 状态，如果已经是 CANCELLED，说明用户已手动取消，不需要再创建消息
    const lastMessageItems = getCurrentMessageItems();
    if (lastMessageItems && lastMessageItems.status === TaskStatus.CANCELLED) {
      console.log('[DeepsearchSSEHandler] MessageItems already cancelled, skipping waiting_user_input event');
      return;
    }

    // 根据 agent 类型创建不同类型的消息
    const isOutlineInteraction = sseData.agent === 'outline_interaction';
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
      'deepsearch'
    );

    // 如果创建失败（例如对话已被取消），跳过后续处理
    if (!message || !lastMessageItems) {
      return;
    }

    // 更新消息状态
    updateMessage(lastMessageItems.id, message.id, {
      status: TaskStatus.IN_PROGRESS,
      isStreaming: false,
    });

    // 给 SESSION_CONVERSATION_ID 赋值
    if (sseData.conversation_id) {
      this.store.setSessionConversationId(sseData.conversation_id);
    }
  }

  /**
   * 处理 user_input_ended 事件
   * 当大纲交互达到最大修改次数时触发，创建 TASK 消息显示大纲并继续流程
   */
  private handleUserInputEnded(sseData: SSEData): void {
    const { getCurrentMessageItems } = this.store;
    const lastMessageItems = getCurrentMessageItems();

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
      const taskMessage = this.createRootTaskFromOutline(lastMessageItems.id, outlineContent);
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
    const lastMessageItems = this.store.getCurrentMessageItems();

    if (!lastMessageItems || getMessageItemsIsUser(lastMessageItems)) return;

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
      if (sseData.agent === 'end') {
        // 找到最终报告 message（与 outline_task 同级的 REPORT）
        const finalReportMessage = lastMessageItems.messagesIds
          .map(msgId => this.store.getMessageById(msgId))
          .find(msg =>
            msg?.type === MessageType.REPORT &&
            isFinalReportMessage(msg.title) &&
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
            'deepsearch'  // agent 类型
          );
          if (newReport) {
            updateMessage(lastMessageItems.id, newReport.id, {
              status: TaskStatus.FAILED,
              isStreaming: false,
            });
          }
        }
      }
    }

    // collector_info_retrieval 和 collector_summary 的错误处理
    if (['collector_info_retrieval', 'collector_summary'].includes(sseData.agent) &&
        sectionIdx !== undefined && planIdx !== undefined && stepIdx !== undefined) {

      const sectionTask = this.findTaskInMessages(
        lastMessageItems.messagesIds,
        msg => msg.type === MessageType.TASK && msg.sectionIdx === sectionIdx,
        `section_${sectionIdx}`
      );

      if (!sectionTask) {
        console.warn('[DeepsearchSSEHandler] Section task not found for error, sectionIdx:', sectionIdx);
        // 跳过后续处理，继续执行 end agent 的清理逻辑（如果是 end 的话）
      } else {
        const sectionChildren = this.store.getChildMessages(sectionTask.id);
        const planTitle = i18n.t('apps.deepSearch.informationCollection', { index: planIdx });
        const planTask = sectionChildren.find(task =>
          task.title && task.title.includes(planTitle)
        );

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
            if (sseData.agent === 'collector_info_retrieval') {
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
                messageTitle
              );

              updateMessage(lastMessageItems.id, childMessage.id, {
                status: TaskStatus.FAILED,
                isStreaming: false,
              });
              // 不更新 stepTask 状态
            }
            // collector_summary 错误处理
            else if (sseData.agent === 'collector_summary') {
              // 和正常流程一样，content 是字符串
              const summaryContent = typeof sseData.content === 'string'
                ? sseData.content
                : String(sseData.content || '');

              const childMessage = this.store.addMessageAsChild(
                lastMessageItems.id,
                stepTask.id,
                MessageType.TEXT,
                summaryContent,
                i18n.t('deepResearch.handler.informationSummary')
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
              const allStepsFinished = planChildren.every(step =>
                step.status !== TaskStatus.PENDING && step.status !== TaskStatus.IN_PROGRESS
              );

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
    if (sseData.agent === 'end') {
      // 先将所有未完成的消息标记为 FAILED
      this.markAllIncompleteMessages(lastMessageItems, false);
      // 再更新 MessageItems 的状态
      this.store.updateMessageItems(lastMessageItems.id, { status: TaskStatus.COMPLETED });
    }
  }

  // ===== 辅助方法 =====

  /**
   * 递归更新未完成任务及其所有子孙的状态
   * 只更新状态为 PENDING 或 IN_PROGRESS 的任务
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

      // 只更新 PENDING 或 IN_PROGRESS 状态的任务
      if (currentTask.status === TaskStatus.PENDING ||
          currentTask.status === TaskStatus.IN_PROGRESS) {
        this.store.updateMessage(messageItemsId, currentTask.id, {
          status: updateStatus,
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

    // 查找 type=REPORT 且 title 以 "章节报告:" 开头的消息
    const existingReport = childMessages.find(msg =>
      msg.type === MessageType.REPORT &&
      msg.title?.startsWith(i18n.t('deepResearch.handler.chapterReport') + ':')
    );

    return existingReport || null;
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

  private parseOptionalIndex(value?: string | number): number | undefined {
    if (value === undefined || value === null || value === '') {
      return undefined;
    }

    const parsed = Number.parseInt(String(value), 10);
    return Number.isNaN(parsed) ? undefined : parsed;
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

  private createRootTaskFromOutline(messageItemsId: string, outlineContent: any): Message | null {
    const { addSystemMessage, updateMessage } = this.store;
    const title = outlineContent.title || i18n.t('deepResearch.handler.researchOutline');

    const rootTask = addSystemMessage(
      this.conversationId,
      MessageType.TASK,
      outlineContent.thought || '',
      undefined,
      title,
      'deepsearch'
    );

    if (!rootTask) {
      return null;
    }

    updateMessage(messageItemsId, rootTask.id, {
      status: TaskStatus.IN_PROGRESS,
      isStreaming: false,
      sectionIdx: 0,
    });

    if (outlineContent.sections && Array.isArray(outlineContent.sections)) {
      outlineContent.sections.forEach((section: any, index: number) => {
        const sectionTitle = section.title || i18n.t('deepResearch.handler.chapter', { index: index + 1 });
        const sectionDescription = section.description || '';

        const sectionTask = this.store.addMessageAsChild(
          messageItemsId,
          rootTask.id,
          MessageType.TASK,
          sectionDescription,
          sectionTitle
        );

        updateMessage(messageItemsId, sectionTask.id, {
          sectionIdx: index + 1,
          status: TaskStatus.PENDING,
          isStreaming: false,
        });
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
  private findOrCreatePlanTask(sectionTask: Message, targetPlanIdx: number, messageItemsId: string): Message | null {
    const childMessages = this.store.getChildMessages(sectionTask.id);

    const planTitle = i18n.t('apps.deepSearch.informationCollection', { index: targetPlanIdx });
    const existingPlan = childMessages.find(task =>
      task.title && task.title.includes(planTitle)
    );

    if (existingPlan) {
      return existingPlan;
    }

    const planTask = this.store.addMessageAsChild(
      messageItemsId,
      sectionTask.id,
      MessageType.TASK,
      { title: planTitle },
      planTitle
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
   * @param markAsCompleted true=标记为 COMPLETED, false=标记为 FAILED
   * 注意：不包括用户手动停止的 CANCELLED 状态
   */
  public markAllIncompleteMessages(messageItems: MessageItems, markAsCompleted: boolean): void {
    const { updateMessage, getChildMessages } = this.store;
    const targetStatus = markAsCompleted ? TaskStatus.COMPLETED : TaskStatus.FAILED;
    let count = 0;

    const markRecursively = (message: Message) => {
      // 递归处理子消息
      const children = getChildMessages(message.id);
      children.forEach(child => markRecursively(child));

      // 只标记非 COMPLETED/CANCELLED（用户手动停止）/UNKNOWN / FAILED 的消息
      if (message.status !== TaskStatus.COMPLETED && message.status !== TaskStatus.CANCELLED && 
        message.status !== TaskStatus.FAILED && (/*markAsCompleted ||*/ message.status !== TaskStatus.UNKNOWN)) {
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
