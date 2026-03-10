import { Markdown } from '@test-agentstudio/base-ui'
import type { ChatMessage } from './chatTypes'

export function MessageContent({ message }: { message: ChatMessage }) {
  const isOpening = message.kind === 'opening'

  const renderContent = (content: string) => {
    if (isOpening) {
      return (
        <div className={`text-sm leading-relaxed break-words whitespace-pre-wrap ${message.role === 'user' ? 'text-white' : 'text-gray-800 dark:text-gray-200'}`}>{content}</div>
      )
    }
    return (
      <Markdown
        className={`text-sm leading-relaxed break-words ${message.role === 'user' ? 'text-white' : 'text-gray-800 dark:text-gray-200'}`}
        content={content}
        enableMath={false}
      />
    )
  }

  const renderChunkHeader = (type: string, nodeId?: string, nodeName?: string) => {
    const showTypeLabel = type && type !== 'agent'
    const rawLabel = nodeName || (nodeId != null && String(nodeId).trim() ? String(nodeId) : '')
    const displayNodeLabel = rawLabel ? `#${rawLabel}` : ''
    if (!showTypeLabel && !displayNodeLabel) return null

    return (
      <div className="text-xs text-gray-400 dark:text-gray-500 mb-1 flex items-center gap-1 select-none">
        {showTypeLabel && <span className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-gray-500 dark:text-gray-400 font-medium scale-90 origin-left">{type}</span>}
        {displayNodeLabel && <span className="font-mono text-gray-400 dark:text-gray-500 scale-90 origin-left">{displayNodeLabel}</span>}
      </div>
    )
  }

  const isAssistantWithChunks = message.role === 'assistant' && message.chunks && message.chunks.length > 0

  if (isAssistantWithChunks) {
    const chunks = message.chunks || []
    const groupsMap = new Map<string, typeof chunks>()
    for (const chunk of chunks) {
      const key = chunk.type || 'default'
      const list = groupsMap.get(key)
      if (list) {
        list.push(chunk)
      } else {
        groupsMap.set(key, [chunk])
      }
    }
    const groups = Array.from(groupsMap.entries())

    return (
      <div className="space-y-3">
        {groups.map(([key, groupChunks]) => (
          <div key={key} className="p-3 rounded-xl shadow-sm overflow-x-hidden bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-200">
            <div className="space-y-3">
              {groupChunks.map((chunk, idx) => (
                <div key={chunk.id} className="relative">
                  {idx > 0 && <div className="h-px bg-gray-200 dark:bg-gray-600 my-3" />}
                  {renderChunkHeader(chunk.type, chunk.nodeId, chunk.nodeName)}
                  {renderContent(chunk.content)}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return (
    <>
      {message.role === 'assistant' && message.detailInfo?.streaming && !(message.content || '').trim() ? (
        <div className="flex items-center justify-center space-x-2">
          <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-pulse"></div>
          <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
        </div>
      ) : (
        renderContent(message.content)
      )}
    </>
  )
}

export function NormalMessage({ message }: { message: ChatMessage }) {
  const isAssistantWithChunks = message.role === 'assistant' && message.chunks && message.chunks.length > 0
  
  // If it has chunks, MessageContent already renders the containers/bubbles.
  if (isAssistantWithChunks) {
    return <MessageContent message={message} />
  }

  return (
    <div
      className={`p-3 rounded-xl shadow-sm overflow-x-hidden ${
        message.role === 'user' 
          ? 'bg-gradient-to-r from-blue-500 to-indigo-600 text-white' 
          : 'bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-800 dark:text-gray-200'
      }`}
    >
      <MessageContent message={message} />
    </div>
  )
}
