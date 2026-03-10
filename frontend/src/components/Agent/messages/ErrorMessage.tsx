import { Markdown } from '@test-agentstudio/base-ui'
import type { ChatMessage } from './chatTypes'

export function ErrorMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="p-3 rounded-xl shadow-sm overflow-x-hidden bg-red-50 dark:bg-red-900/20 border-2 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300">
      <Markdown
        content={message.content}
        className="prose prose-sm max-w-none prose-red prose-headings:text-red-900 dark:prose-headings:text-red-300 prose-p:text-red-800 dark:prose-p:text-red-300 prose-strong:text-red-900 dark:prose-strong:text-red-300"
      />
    </div>
  )
}
