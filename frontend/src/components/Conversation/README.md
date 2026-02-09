# 前端消息组件使用文档

基于 `readme.md` 中的界面设计要求，已完成前端初版设计。

## 📁 文件结构

```
src/
├── stores/
│   └── useConversationStore.ts          # 消息状态管理Store
└── components/
    └── Conversation/
        ├── index.ts                      # 导出所有消息组件
        ├── MessageList.tsx               # 消息列表容器
        ├── UserMessageItem.tsx           # 用户消息组件
        ├── SystemMessageItem.tsx         # 系统消息组件
        ├── ResultPanel.tsx               # 右侧结果面板
        ├── PlaybackPanel.tsx             # SSE回放控制面板
        ├── ErrorBoundary.tsx             # 错误边界组件
        ├── utils/                        # 工具函数
        │   ├── formatDuration.ts         # 时间格式化工具
        │   └── spinnerStyles.tsx        # 动画样式组件
        └── messageTypes/                 # 消息子组件
            ├── index.ts
            ├── TextMessage.tsx           # 普通文本消息
            ├── LinkMessage.tsx           # 外部链接
            ├── DetailLinkMessage.tsx     # 详情链接
            ├── TaskMessage.tsx           # 任务类型（递归渲染）
            ├── ReportMessage.tsx         # 报告类型（递归渲染）
            ├── DeepSearchReportCard.tsx  # DeepSearch最终报告卡片
            ├── TextContentCard.tsx       # 文本内容卡片（共用组件）
            ├── ErrorMessage.tsx          # 错误信息
            └── InterruptMessage.tsx      # 中断等待输入
```

## 🔧 Store 功能

### 核心方法

| 方法 | 说明 |
|------|------|
| `createConversation(title, config)` | 创建新会话 |
| `addUserMessage(conversationId, content)` | 添加用户消息 |
| `addSystemMessage(conversationId, type, content)` | 添加系统消息 |
| `updateMessage(messageItemsId, messageId, updates)` | 更新消息 |
| `appendMessageContent(messageItemsId, messageId, content)` | 追加消息内容 |
| `handleSSEMessage(sseData, conversationId)` | 处理SSE流式消息 |

### 数据结构

```typescript
interface MessageItems {
  id: string;
  status: TaskStatus;
  messagesIds: string[];       // 消息Message的id list
  createdAt: number;
  updatedAt: number;
  conversationId: string;
  isUser: boolean;             // 是否用户消息
  agentType?: AgentType;       // Agent类型（ordinary/deepsearch）
}

enum MessageType {
  TEXT = 'text',              // 普通文本/Markdown
  REPORT = 'report',          // 报告类型
  LINK = 'link',              // 外部链接
  DETAIL_LINK = 'detail_link',// 详情链接
  TASK = 'task',              // 任务容器
  ERROR = 'error',            // 错误信息
  INTERRUPT = 'interrupt',    // 中断等待用户输入
}

enum TaskStatus {
  PENDING = 'pending',        // 未开始
  IN_PROGRESS = 'in_progress', // 进行中
  COMPLETED = 'completed',    // 完成
  FAILED = 'failed',          // 失败
  CANCELLED = 'cancelled',    // 手动结束
  UNKNOWN = 'unknown',        // 未知状态
}

interface Message {
  id: string;
  type: MessageType;
  status: TaskStatus;
  content: string | LinkContent;  // 数据内容
  title?: string;
  parentMessageId?: string;   // 父消息ID（用于构建树形结构）
  messageItemsId: string;
  conversationId: string;
  createdAt: number;
  updatedAt: number;
  isStreaming?: boolean;
  sectionIdx?: number;        // 章节索引（用于task类型）
}

interface LinkContent {
  url: string;
  title: string;
  query?: string;
  description?: string;
  source?: string;
  publishTime?: string;
  cardStyle?: 'text' | 'card';
}
```

## 🎨 组件说明

### 1. MessageList - 消息列表容器

**功能：**
- 遍历 `messageItemsList`
- 自动滚动到底部
- 支持用户手动滚动时暂停自动滚动（3秒后恢复）

**使用：**
```tsx
import { MessageList } from '@/components/Conversation';

function MyPage() {
  return (
    <div className="flex-1 overflow-hidden">
      <MessageList />
    </div>
  );
}
```

### 2. UserMessageItem - 用户消息

**显示规则：**
- 右对齐，蓝色背景 (`bg-blue-50`)
- 显示在 MessageBox 右侧
- Markdown 格式渲染

**数据要求：**
```typescript
{
  isUser: true,
  messages: [
    { content: "用户的问题", type: "text" }
  ]
}
```

### 3. SystemMessageItem - 系统消息

**显示规则：**
- 左对齐，白色背景
- 所有 message 依次显示在同一消息框内
- 进行中时，最后的 message 跟随数据更新
- 之前的 message 不会变化

**支持的 message 类型：**

| 类型 | 组件 | 说明 |
|------|------|------|
| TEXT | TextMessage | Markdown文本（entry、generate_questions、sub_reporter等） |
| LINK | LinkMessage | 外部链接（collector_info_retrieval） |
| DETAIL_LINK | DetailLinkMessage | 详情链接（打开右侧面板） |
| TASK | TaskMessage | 任务类型（outline、plan_reasoning），支持递归渲染子任务 |
| REPORT | ReportMessage | 报告类型，支持递归渲染子报告和子任务 |
| ERROR | ErrorMessage | 错误信息 |
| INTERRUPT | InterruptMessage | 中断等待用户输入（feedback_handler） |

### 4. ResultPanel - 右侧结果面板

**功能：**
- 显示选中的消息详情
- 支持REPORT类型消息的完整报告展示
- 支持LINK类型消息的链接详情
- 实时更新（流式内容）
- 可关闭面板

**使用：**
```tsx
import { ResultPanel } from '@/components/Conversation';

function MyPage() {
  return <ResultPanel className="w-full h-full" />;
}
```

### 5. PlaybackPanel - SSE回放控制面板

**功能：**
- 显示所有SSE录制记录
- 支持回放历史对话
- 支持调整回放速度（1x/2x/5x/10x）
- 支持下载和删除录制记录
- 支持压缩录制以节省存储空间

### 6. ErrorBoundary - 错误边界

**功能：**
- 捕获子组件树中的渲染错误
- 防止整个应用崩溃
- 显示错误信息和刷新按钮

## 🔧 工具函数

### formatDuration

格式化时间间隔（毫秒）为可读字符串。

```typescript
import { formatDuration } from '@/components/Conversation/utils/formatDuration';

formatDuration(90000); // "1m30s"
formatDuration(3661000); // "1h1m"
formatDuration(90061000); // "1d1h1m"
```

### Spinner样式组件

提供iOS风格的loading动画组件。

```typescript
import {
  IosSpinnerStyles,
  IosSpinnerSmallStyles,
  LoadingDotStyles,
  SpinnerDots
} from '@/components/Conversation/utils/spinnerStyles';

// 使用示例
<IosSpinnerStyles />
<div className="ios-spinner">
  <SpinnerDots />
</div>
```

## 📝 使用示例

### 基础用法

```tsx
import { useConversationStore } from '@/stores/useConversationStore';
import { MessageList } from '@/components/Conversation';

function ChatPage() {
  const {
    messageItemsList,
    addUserMessage,
    handleSSEMessage
  } = useConversationStore();

  // 添加用户消息
  const handleSend = (content: string) => {
    addUserMessage('conv_123', content);
  };

  // 处理SSE消息
  useEffect(() => {
    const eventSource = new EventSource('/api/stream');

    eventSource.onmessage = (event) => {
      const sseData = JSON.parse(event.data);
      handleSSEMessage(sseData, 'conv_123');
    };

    return () => eventSource.close();
  }, []);

  return (
    <div className="h-screen flex flex-col">
      <MessageList />
      {/* InputBox */}
    </div>
  );
}
```

### SSE 流式数据处理

```typescript
// 后端发送的SSE数据格式
const sseData = {
  conversation_id: "conv_123",
  agent: "entry",              // agent类型
  message_id: "msg_456",
  role: "assistant",
  content: "你好，我是助手",
  message_type: "message_chunk",
  event: "start",              // start / message / done / summary_response
  created_time: "1234567890",
  section_idx: "0"
};

// 自动映射到对应的Message类型
// entry → TEXT
// generate_questions → TEXT
// outline → TASK
// plan_reasoning → SECTION
// collector_info_retrieval → LINK
// sub_reporter → TEXT
// collector_summary → TEXT
// end → TEXT
// feedback_handler → INTERRUPT
```

## 🔄 数据流

```
用户输入
  ↓
addUserMessage()
  ↓
创建 MessageItems (isUser = true)
  ↓
发送请求到后端
  ↓
接收SSE流式数据
  ↓
handleSSEMessage()
  ↓
根据 event 类型处理：
  - start → addSystemMessage() 创建新消息
  - message → appendMessageContent() 追加内容
  - done → updateMessage() 标记完成，解析JSON
  - summary_response → 一次性设置完整内容
  ↓
messageItemsList 更新
  ↓
MessageList 重新渲染
  ↓
显示用户消息/系统消息
```

## ✨ 特性

1. **流式更新**：支持SSE流式数据实时更新
2. **智能滚动**：自动滚动到底部
3. **类型映射**：后端agent类型自动映射到前端Message类型
4. **递归渲染**：支持Task和Report类型消息的递归渲染
5. **状态管理**：完整的状态管理（pending/in_progress/completed/failed/cancelled/unknown）
6. **错误处理**：使用ErrorBoundary捕获渲染错误
7. **回放功能**：支持SSE事件录制和回放
8. **共用组件**：提取了TextContentCard等共用组件，避免代码重复

## 🎯 组件层次结构

```
MessageList (消息列表容器)
  ├─ ErrorBoundary (错误边界)
  │   ├─ UserMessageItem (用户消息)
  │   └─ SystemMessageItem (系统消息)
  │       ├─ TextMessage (文本消息)
  │       ├─ LinkMessage (链接消息)
  │       ├─ DetailLinkMessage (详情链接)
  │       ├─ TaskMessage (任务消息，递归)
  │       │   ├─ TaskMessage (子任务)
  │       │   ├─ TextContentCard (文本内容)
  │       │   ├─ LinkSet (链接集合)
  │       │   └─ ReportMessage (子报告)
  │       ├─ ReportMessage (报告消息，递归)
  │       │   ├─ ReportCard (报告卡片)
  │       │   ├─ TaskMessage (子任务)
  │       │   ├─ TextContentCard (文本内容)
  │       │   └─ ReportMessage (子报告)
  │       ├─ ErrorMessage (错误消息)
  │       └─ InterruptMessage (中断消息)
  └─ ResultPanel (右侧结果面板)
```

## 💡 代码优化建议

1. **避免重复代码**：使用共用的工具函数和组件（如 `formatDuration`、`TextContentCard`）
2. **类型安全**：避免使用 `as any`，使用正确的类型定义
3. **清理调试代码**：生产环境移除所有 `console.log`
4. **错误处理**：使用 ErrorBoundary 包裹可能出错的组件
5. **性能优化**：使用 `useMemo` 和 `useCallback` 优化渲染性能
