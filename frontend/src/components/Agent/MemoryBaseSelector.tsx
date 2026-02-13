import React, { useState, useEffect, useMemo } from 'react';
import { Typography, Button, Pagination, Box } from '@mui/material';
import { X, Cpu, AlertCircle } from 'lucide-react';
import { MemoryBaseService, useEmbeddingModel, embeddingModelService } from '@test-agentstudio/api-client';
import { getDefaultSpaceId } from '@/utils/spaceUtils';
import { MemoryBaseItem } from '@test-agentstudio/api-client';
import { useScopedTranslation } from '@/i18n';

interface MemoryBaseSelectorProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (selectedMemoryBaseId: string | null) => void;
  initialSelected?: string | null;
}

// 单个记忆库项组件，用于显示 embedding 模型信息
const MemoryBaseItemComponent: React.FC<{
  mb: MemoryBaseItem;
  isSelected: boolean;
  spaceId: string;
  onToggle: () => void;
}> = ({ mb, isSelected, spaceId, onToggle }) => {
  // 获取 embedding 模型信息
  const { data: embeddingModel } = useEmbeddingModel(mb.embedding_model_config_id?.toString() || '', spaceId);
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  return (
    <div
      className={`p-4 rounded-xl border-2 transition-all duration-300 cursor-pointer ${
        isSelected ? 'border-blue-400 bg-blue-50 shadow-lg' : 'border-gray-200 bg-white'
      }`}
      onClick={onToggle}
      aria-selected={isSelected}
      role="option"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4 flex-1 min-w-0">
          <div
            className={`w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0 ${
              isSelected ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
            }`}
          >
            💾
          </div>
          <div className="flex-1 min-w-0 overflow-hidden">
            <h4 
              className={`font-semibold text-base truncate ${isSelected ? 'text-blue-800' : 'text-gray-800'}`}
              title={mb.name}
            >
              {mb.name}
            </h4>
            {mb.description && <p className="text-gray-600 text-sm truncate" title={mb.description}>{mb.description}</p>}
            {embeddingModel && (
              <div className="flex items-center space-x-1 mt-1" title={`Embedding 模型: ${embeddingModel.name} (${embeddingModel.modelId})`}>
                <Cpu className="w-3 h-3 text-gray-500" />
                <span className="text-xs text-gray-500 truncate max-w-[200px]">
                  {embeddingModel.name}
                  {embeddingModel.modelId && <span className="ml-1">({embeddingModel.modelId})</span>}
                </span>
              </div>
            )}
          </div>
        </div>

        {isSelected && (
          <div className="flex items-center space-x-2 flex-shrink-0 ml-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <span className="text-sm text-blue-700 font-medium">{t('orchestrationPage.memory.memoryBase.selected')}</span>
          </div>
        )}
      </div>
    </div>
  );
};

const MemoryBaseSelector: React.FC<MemoryBaseSelectorProps> = ({ open, onClose, onConfirm, initialSelected = null }) => {
  const { t } = useScopedTranslation('agents.agentEditor.orchestration')
  const [selectedMemoryBase, setSelectedMemoryBase] = useState<string | null>(initialSelected);;
  const [memoryBaseList, setMemoryBaseList] = useState<MemoryBaseItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [embeddingModelError, setEmbeddingModelError] = useState<string | null>(null);

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const spaceId = useMemo(() => getDefaultSpaceId() || '', []);

  // 加载记忆库列表
  useEffect(() => {
    if (!open || !spaceId) return;

    const loadMemoryBases = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await MemoryBaseService.getMemoryBases({
          space_id: spaceId,
          page: currentPage,
          page_size: pageSize,
        });

        if (response.code === 200 && response.data) {
          {response.data.items.map(mb => {
            if (mb.status === undefined) {
              mb.status = "active"
                }
              }
            )
          }
          setMemoryBaseList(response.data.items);
          setTotal(response.data.total);
          setTotalPages(Math.ceil(response.data.total / pageSize));
        } else {
          setError('获取记忆库列表失败');
        }
      } catch (err) {
        console.error('Failed to load memory bases:', err);
        setError('加载记忆库列表时出错');
      } finally {
        setIsLoading(false);
      }
    };

    loadMemoryBases();
  }, [open, spaceId, currentPage]);

  // 当对话框打开时，重置选中状态
  useEffect(() => {
    if (open) {
      setSelectedMemoryBase(initialSelected);
      setCurrentPage(1);
    }
  }, [open, initialSelected]);

  const handleToggle = (mbId: string) => { // ✅ 新的单选逻辑
    // 如果点击的是已选项，则取消选择；否则选择该项。
    setSelectedMemoryBase(prev => prev === mbId ? null : mbId);
  };

  const handleConfirm = () => {
    onConfirm(selectedMemoryBase); // ✅ 传递单个ID或null
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex items-center justify-center min-h-screen px-4">
        <div className="fixed inset-0 bg-black opacity-25" onClick={onClose}></div>

        <div className="relative bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-xl">
          <div className="flex items-center justify-between p-6 border-b">
            <Typography variant="h5" component="h2" sx={{ fontWeight: 'bold' }}>
              {t('orchestrationPage.memory.memoryBase.select')}
            </Typography>
            <button onClick={onClose} className="text-gray-400 hover:text-gray-500">
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="p-6 max-h-[60vh] overflow-y-auto">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
                <span className="ml-2 text-gray-600">加载中...</span>
              </div>
            ) : error ? (
              <div className="text-center py-12 text-red-500">{error}</div>
            ) : memoryBaseList.length === 0 ? (
              <div className="text-center py-12 text-gray-500">暂无记忆库</div>
            ) : memoryBaseList.length > 0 && (
              <>
                <div className="space-y-3">
                  {memoryBaseList.map(mb => (
                    <MemoryBaseItemComponent
                      key={mb.mdb_id}
                      mb={mb}
                      // isSelected={selectedMemoryBases.includes(mb.mdb_id)} // ❌ 旧的判断方式
                      isSelected={selectedMemoryBase === mb.mdb_id} // ✅ 新的判断方式
                      spaceId={spaceId}
                      onToggle={() => handleToggle(mb.mdb_id)}
                    />
                  ))}
                </div>

                {totalPages > 1 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                    <Pagination
                      count={totalPages}
                      page={currentPage}
                      onChange={(_, page) => setCurrentPage(page)}
                      color="primary"
                    />
                  </Box>
                )}
              </>
            )}
          </div>

          <div className="flex items-center justify-end space-x-2 p-6 border-t">
            <Button variant="outlined" onClick={onClose}>
              {t('orchestrationPage.memory.memoryBase.cancel')}
            </Button>
            <Button
              variant="contained"
              onClick={handleConfirm}
              // disabled={!!embeddingModelError || selectedMemoryBases.length === 0} // ❌ 旧的禁用条件
              disabled={selectedMemoryBase === null} // ✅ 新的禁用条件：未选择任何项
            >
              {/* 确认 ({selectedMemoryBases.length}) // ❌ 旧的带计数文本 */}
              {t('orchestrationPage.memory.memoryBase.confirm')} {/* ✅ 简单的确认文本 */}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default MemoryBaseSelector;