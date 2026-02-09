import Typography from '@mui/material/Typography';
import { Settings, Trash2, Database } from 'lucide-react';
import { useState } from 'react';
import DeleteConfirmationDialog from '@/components/Common/DeleteConfirmationDialog';

interface MemoryBaseItem {
  id: string;
  name: string;
  description?: string;
  desc?: string; // 兼容字段
}

// 记忆库列表组件
const MemoryBaseList = ({
  memoryBaseObjects,
  onClick,
  disabled = false,
}: {
  memoryBaseObjects: MemoryBaseItem[];
  onClick: (operate: 'delete' | 'setting', memoryBaseId: string) => void;
  disabled?: boolean;
}) => {
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<{ id: string; name: string } | null>(null);

  return (
    <div className="space-y-3">
      {memoryBaseObjects.map(mb => (
        <div
          key={mb.id}
          className="flex items-start justify-between py-2 px-3 bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-all duration-200"
        >
          <div className="flex items-start space-x-3 flex-1 min-w-0">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-purple-100 to-indigo-100 rounded-lg flex items-center justify-center border border-purple-200 mt-1">
              <Database className="w-4 h-4 text-purple-600" />
            </div>
            <div className="flex-1 min-w-0">
              <Typography sx={{ fontWeight: 'bold', fontSize: '1rem' }}>{mb.name}</Typography>
              {(mb.description || mb.desc) && (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontSize: '0.875rem',
                    lineHeight: 1.4,
                    mt: 0.5,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {mb.description || mb.desc}
                </Typography>
              )}
            </div>
          </div>
          <div className="flex space-x-4 pt-1">
            <button
              title="设置"
              onClick={e => {
                e.stopPropagation();
                onClick('setting', mb.id);
              }}
            >
              <Settings className="w-4 h-4 text-gray-600" />
            </button>
            <button
              title="删除"
              onClick={e => {
                e.stopPropagation();
                if (!disabled) {
                  setPendingDelete({ id: mb.id, name: mb.name });
                  setConfirmOpen(true);
                }
              }}
              disabled={disabled}
              className={`${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              <Trash2 className="w-4 h-4 text-gray-600" />
            </button>
          </div>
        </div>
      ))}
      {memoryBaseObjects.length === 0 && <div className="text-center py-6 text-gray-500">未添加记忆库，可点击右上角进行添加</div>}
      <DeleteConfirmationDialog
        isOpen={confirmOpen}
        onClose={() => {
          setConfirmOpen(false);
          setPendingDelete(null);
        }}
        onConfirm={() => {
          if (pendingDelete) onClick('delete', pendingDelete.id);
          setConfirmOpen(false);
          setPendingDelete(null);
        }}
        itemType="memoryBase"
        itemName={pendingDelete?.name || ''}
        title="移除记忆库"
        confirmButtonText="确认"
        message={`确定移除此记忆库？此操作无法撤销。`}
      />
    </div>
  );
};

export default MemoryBaseList;