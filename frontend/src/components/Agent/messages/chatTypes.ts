export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
  kind?: 'normal' | 'error' | 'opening' | 'interaction' | 'notice'
  responseTime?: number
  detailInfo?: any
  chunks?: MessageChunk[]
}

export interface MessageChunk {
  id: string
  type: string
  nodeId?: string
  nodeName?: string
  content: string
  status: 'streaming' | 'done'
  index?: number
}
