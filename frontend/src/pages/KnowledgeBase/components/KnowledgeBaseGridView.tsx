import React from 'react'
import { Empty } from '@/components/Common/Empty'
import { KnowledgeBaseCardNew } from './KnowledgeBaseCardNew'
import type { KnowledgeBase } from '@/types/knowledgeBase'

export interface KnowledgeBaseGridViewProps {
  knowledgeBases: KnowledgeBase[]
  searchTerm?: string
  onCreateClick?: () => void
  onEdit: (kb: KnowledgeBase) => void
  onDelete: (kb: KnowledgeBase) => void
  onClick?: (kb: KnowledgeBase) => void
}

export const KnowledgeBaseGridView: React.FC<KnowledgeBaseGridViewProps> = ({
  knowledgeBases,
  searchTerm = '',
  onCreateClick,
  onEdit,
  onDelete,
}) => {
  if (knowledgeBases.length === 0) {
    return <Empty searchTerm={searchTerm} type="knowledgeBases" onCreateClick={onCreateClick} />
  }

  return (
    <div className="grid grid-cols-3 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {knowledgeBases.map(kb => (
        <KnowledgeBaseCardNew
          key={kb.id}
          knowledgeBase={kb}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}

export default KnowledgeBaseGridView
