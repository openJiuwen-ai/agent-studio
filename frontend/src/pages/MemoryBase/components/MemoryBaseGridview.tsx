// MemoryBaseGridView Component
import { Empty } from '@/components/Common/Empty';
import type { MemoryBase } from '@/types/memoryBase';
import {MemoryBaseCardNew} from './MemoryBaseCardNew';

export interface MemoryBaseGridViewProps {
  memoryBases: MemoryBase[];
  searchTerm?: string;
  onCreateClick?: () => void;
  onEdit: (mb: MemoryBase) => void;
  onDelete: (mb: MemoryBase) => void;
}

export const MemoryBaseGridView: React.FC<MemoryBaseGridViewProps> = ({
  memoryBases,
  searchTerm = '',
  onCreateClick,
  onEdit,
  onDelete,
}) => {
  if (memoryBases.length === 0) {
    return <Empty searchTerm={searchTerm} type="memoryBases" onCreateClick={onCreateClick} />;
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {memoryBases.map(mb => (
        <MemoryBaseCardNew
          key={mb.mdb_id}
          memoryBase={mb}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
};

export default MemoryBaseGridView;

