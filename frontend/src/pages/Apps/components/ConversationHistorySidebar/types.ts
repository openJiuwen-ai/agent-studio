import type { Conversation } from '../../../../stores/useConversationStore'

export interface ConversationHistorySidebarProps {
  /** Currently selected conversation ID */
  currentConversationId: string | null;
  /** Callback when a conversation is selected */
  onConversationSelect: (conversationId: string) => Promise<void>;
  /** Callback to create a new conversation */
  onNewConversation: () => void;
  /** Whether SSE streaming is in progress */
  isStreaming: boolean;
  /** Whether to force collapse the sidebar (e.g., when report panel is open) */
  forceCollapsed?: boolean;
}

export interface ConversationItemProps {
  /** The conversation data */
  conversation: Conversation;
  /** Whether this conversation is currently active */
  isActive: boolean;
  /** Callback when clicked to select this conversation */
  onClick: () => void;
  /** Callback when delete is requested */
  onDelete: (conversationId: string) => Promise<void>;
  /** Whether SSE streaming is in progress */
  isStreaming: boolean;
}

export interface ConversationListProps {
  /** Currently selected conversation ID */
  currentConversationId: string | null;
  /** Callback when a conversation is selected */
  onConversationSelect: (conversationId: string) => Promise<void>;
  /** Callback when delete is requested */
  onDeleteConversation: (conversationId: string) => Promise<void>;
  /** Whether SSE streaming is in progress */
  isStreaming: boolean;
}
