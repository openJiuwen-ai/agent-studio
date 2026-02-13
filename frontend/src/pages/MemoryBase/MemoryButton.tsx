import { useState, useEffect, useMemo } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, IconButton, Button, Tooltip, CircularProgress, Alert } from '@mui/material'
import { Shell, Settings, X, Variable, Brain, Trash } from 'lucide-react'
import axios from 'axios'
import { useScopedTranslation } from '@/i18n'
import { useTranslation } from 'react-i18next'
import { useAuthStore } from '@/stores/useAuthStore'

type MenuKey = 'variables' | 'longterm'

/* ---------- 后端接口（占位路径，按实际调整） ---------- */
const api = {
  /* 变量 */
  listVariables: async (user_id: string, group_id: string) => {
    const response = await fetch('/api/v1/execution/memory/get_user_variable', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
    const data = await response.json()
    console.log('listVar: ', data)
    return data
  },
  deleteUserVariable: async (user_id: string, group_id: string, key: string) => {
    const response = await fetch('/api/v1/execution/memory/delete_user_variable', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        name: key,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
  },

  /* 长期记忆 */
  listLongTerm: async (user_id: string, group_id: string) => {
    const response = await fetch('/api/v1/execution/memory/get_longterm_mem', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        num: 999,
        page: 1,
      }),
    })
    const data = await response.json()
    console.log('listLongTerm: ', data)
    return data
  },  
  deleteLongTerm: async (user_id: string, group_id: string, id: string) => {
    const response = await fetch('/api/v1/execution/memory/delete_longterm_mem', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
      },
      body: JSON.stringify({
        user_id: user_id,
        group_id: group_id,
        mem_id: id,
      }),
    })
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
  },
}

interface Row {
  id: number
  field: string
  value: string
  time: string
  /* 长期记忆扩展 */
  _id?: string // 后端真实 id
}

interface MemoryButtonProps {
  userId: string
  groupId: string
  enableLongTerm?: boolean
}



export default function MemoryButton({ userId, groupId, enableLongTerm = true }: MemoryButtonProps) {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.memoryManager')
  const { t: globalT } = useTranslation();
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<MenuKey>('variables')

  /* 正式数据 */
  const [varList, setVarList] = useState<Row[]>([])
  const [longList, setLongList] = useState<Row[]>([])

  /* 草稿镜像 - 长期记忆按时间排序 */
  const [draftVars, setDraftVars] = useState<Row[]>([])
  const [draftLong, setDraftLong] = useState<Row[]>([])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  /* 待删除集合 */
  const [toDeleteVar, setToDeleteVar] = useState<Set<string>>(new Set()) // 变量 field
  const [toDelete, setToDelete] = useState<Set<string>>(new Set()) // 长期记忆 _id

  // 排序函数：将最新的修改时间排在最前面
  const sortLongTermByTime = (rows: Row[]): Row[] => {
    return [...rows].sort((a, b) => {
      const timeA = a.time ? new Date(a.time).getTime() : 0
      const timeB = b.time ? new Date(b.time).getTime() : 0
      return timeB - timeA // 降序排列（最新的在前）
    })
  }

  /* 打开弹窗：正式 → 草稿，长期记忆按时间排序 */
  useEffect(() => {
    if (open) {
      setDraftVars([...varList])
      // 设置状态
      setDraftLong([...longList]);
      setToDeleteVar(new Set())
      setToDelete(new Set())
    }
  }, [open, varList, longList])

  /* 弹窗打开时自动刷新全量数据 */
  useEffect(() => {
    if (!open) return
    setLoading(true)
    // 并行拉取变量 & 长期记忆
    Promise.all([api.listVariables(userId, groupId), api.listLongTerm(userId, groupId)])
      .then(([vRes, lRes]) => {
        /* 变量 */
        const vObj = vRes.data?.variable_data || {}
        const vList = Object.entries(vObj).map(([k, v], idx) => ({
          id: idx + 1,
          field: k,
          value: String(v),
          time: '', // 隐藏列
        }))
        setVarList(vList)
        setDraftVars([...vList])

        /* 长期记忆 */
        const arr = lRes.data?.longterm_mem_data || []
        const lList = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.type || t('menus.longterm'),
          value: r.content,
          _id: r.mem_id,
          time: '',
        }))
        setLongList(lList)
        setDraftLong(lList)

        /* 清空待删集合 */
        setToDeleteVar(new Set())
        setToDelete(new Set())
      })
      .catch(e => {
        setError(e.message || t('errors.autoRefreshFailed'))
      })
      .finally(() => {
        setLoading(false)
      })
  }, [open, userId, groupId])

  const show = () => setOpen(true)
  const hide = () => setOpen(false)

  /* 侧边栏加载数据 */
  const handleMenuClick = async (key: MenuKey) => {
    setActive(key)
    setLoading(true)
    setError('')
    try {
      if (key === 'variables') {
        const res = await api.listVariables(userId, groupId)
        const obj = res.data?.variable_data || {}
        const list = Object.entries(obj).map(([k, v], idx) => ({ 
          id: idx + 1, 
          field: k, 
          value: String(v), 
          time: new Date().toLocaleString('zh-CN') 
        }))
        setVarList(list)
        setDraftVars([...list])
      } else {
        const res = await api.listLongTerm(userId, groupId)
        const arr = res.data?.longterm_mem_data || []
        const list = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.type || t('menus.longterm'),
          value: r.content,
          time: '',
          _id: r.mem_id || r.id, // 统一使用 mem_id
        }))
        setLongList(list)
        setDraftLong(list)
      }
    } catch (e: any) {
      setError(e.message || t('errors.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  /* 删除：只改草稿 + 记录待删 key/_id */
  const handleDelete = (id: number) => {
    if (active === 'variables') {
      const target = draftVars.find(r => r.id === id)
      if (!target) return
      setToDeleteVar(prev => new Set(prev).add(target.field))
      setDraftVars(prev => prev.filter(r => r.id !== id))
    } else {
      const target = draftLong.find(r => r.id === id)
      if (!target || !target._id) return
      setToDelete(prev => new Set(prev).add(target._id!))
      
      // 从草稿中移除
      const updatedDraft = draftLong.filter(r => r.id !== id)
      setDraftLong(updatedDraft)
    }
  }

  /* 保存：执行删除操作，最后拉全量 */
  const handleSave = async () => {
    setLoading(true)
    try {
      /* 1. 变量：删除 */
      if (active === 'variables' && toDeleteVar.size > 0) {
        const delPromises = Array.from(toDeleteVar).map(k => 
          api.deleteUserVariable(userId, groupId, k)
        )
        
        await Promise.allSettled(delPromises)

        // 刷新数据
        const freshRes = await api.listVariables(userId, groupId)
        const freshObj = freshRes.data?.variable_data || {}
        const freshList = Object.entries(freshObj).map(([k, v], idx) => ({
          id: idx + 1,
          field: k,
          value: String(v),
          time: new Date().toLocaleString('zh-CN'),
        }))
        setVarList(freshList)
        setDraftVars([...freshList])
        setToDeleteVar(new Set())
      }

      /* 2. 长期记忆：删除 */
      if (active === 'longterm' && toDelete.size > 0) {
        const delPromises = Array.from(toDelete).map(id => 
          api.deleteLongTerm(userId, groupId, id)
        )
        
        await Promise.allSettled(delPromises)

        // 刷新数据
        const freshRes = await api.listLongTerm(userId, groupId)
        const arr = freshRes.data?.longterm_mem_data || []
        const freshList = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.type || t('menus.longterm'),
          value: r.content,
          time: '',
          _id: r.mem_id || r.id,
        }))
        setLongList(freshList)
        setDraftLong(freshList)
        setToDelete(new Set())
      }

      hide()
    } catch (e: any) {
      setError(t('errors.saveFailed') + (e.message || t('errors.unknown')))
    } finally {
      setLoading(false)
    }
  }

  /* 通用表格渲染 */
  const renderTable = (list: Row[]) => {
    if (loading) return <CircularProgress className="!w-6 !h-6" />
    if (error) return <Alert severity="error">{error}</Alert>
    if (list.length === 0) return <div className="text-sm text-gray-400">{t('table.empty')}</div>

    const isLong = active === 'longterm'
    const getMemoryTypeName = (type: string) => {
      switch (type) {
        case 'variable':
          return globalT('memoryBases.memoryType.variable');
        case 'summary':
          return globalT('memoryBases.memoryType.summary');
        case 'user_profile':
          return globalT('memoryBases.memoryType.longterm');
        case 'scenario':
          return globalT('memoryBases.memoryType.longterm');
        case 'semantic':
          return globalT('memoryBases.memoryType.longterm');
        default:
          return type;
      }
    };
    const getGridClasses = (isLong) => {
      return 'grid grid-cols-2 gap-4 flex-1'; // 统一2列 + 合理间距
    };
    return (
      <div className="space-y-3 w-full">
        {/* 表头：语义化 + 样式统一 */}
        <div className="flex items-center justify-between px-3 py-2 text-sm text-gray-500 bg-gray-50 rounded-md">
          <div className={getGridClasses(isLong)}>
            {isLong ? (
              <>
                <span className="font-medium">{t('table.headers.longTerm.memory')}</span>
                <span className="font-medium">{t('table.headers.longTerm.type')}</span>
              </>
            ) : (
              <>
                <span className="font-medium">{t('table.headers.variables.field')}</span>
                <span className="font-medium">{t('table.headers.variables.value')}</span>
              </>
            )}
          </div>
          {/* 占位替换空span：语义化更优，避免无用标签 */}
          <div className="w-8"></div>
        </div>

        {/* 列表项：优化 hover 交互 + 布局对齐 + 响应式 */}
        {list.length > 0 ? (
          list.map((row) => (
            <div
              key={row.id}
              className="flex items-center justify-between rounded-lg border border-gray-200 p-3 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200"
            >
              <div className={getGridClasses(isLong)}>
                {isLong ? (
                  <>
                    <span className="text-gray-600 px-2 py-1 break-words max-w-full">
                      {row.value}
                    </span>
                    <span className="text-gray-400 text-sm">{getMemoryTypeName(row.field)}</span>
                  </>
                ) : (
                  <>
                    <span className="font-medium break-words">{row.field}</span>
                    <span className="text-gray-600 px-2 py-1 break-words max-w-full">
                      {row.value}
                    </span>
                  </>
                )}
              </div>

              {/* 删除按钮：优化 hover 效果 + 尺寸统一 */}
              <Tooltip title={t('delete.tooltip')} arrow placement="top">
                <IconButton
                  size="small"
                  onClick={() => handleDelete(row.id)}
                  className="w-8 h-8 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-full transition-colors"
                  aria-label="delete item" // 无障碍优化
                >
                <Trash className="w-4 h-4" />
              </IconButton>
            </Tooltip>
          </div>
          ))
        ) : (
          // 空状态优化：提升用户体验
          <div className="text-center py-6 text-gray-400 text-sm">
            {t('table.empty.noData')}
          </div>
        )}
      </div>
    )
  }

  const menus = useMemo(() => {
    const base = [
      { key: 'variables' as MenuKey, label: t('menus.variables'), icon: Variable },
      { key: 'longterm' as MenuKey, label: t('menus.longterm'), icon: Brain },
    ]
    return enableLongTerm ? base : base.filter(m => m.key !== 'longterm')
  }, [enableLongTerm, t])

  /* 若当前页签被关掉，自动切回 variables */
  useEffect(() => {
    if (!enableLongTerm && active === 'longterm') {
      setActive('variables')
    }
  }, [enableLongTerm, active])

  return (
    <>
      <Tooltip title={t('tooltip')} arrow>
        <IconButton 
          aria-label={t('ariaLabel')} 
          size="small" 
          onClick={show} 
          className="border border-blue-300 text-blue-600 hover:border-blue-400 hover:bg-blue-50"
        >
          <div className="relative inline-flex">
            <Shell className="w-5 h-5 text-gray-500" />
            <Settings className="w-3 h-3 text-gray-600 absolute -right-0 -bottom-0 bg-white rounded-full p-[1px] border border-gray-200" />
          </div>
        </IconButton>
      </Tooltip>

      <Dialog open={open} onClose={hide} maxWidth={false} PaperProps={{ style: { width: 1421, height: 709 } }}>
        <DialogTitle className="flex items-center justify-between !p-4 !pb-3">
          <span className="text-lg font-semibold">{t('title')}</span>
          <IconButton onClick={hide} size="small">
            <X className="w-5 h-5" />
          </IconButton>
        </DialogTitle>

        <div className="flex h-[calc(709px-120px)] border-t">
          <nav className="w-48 border-r bg-gray-50 p-3 space-y-2">
            {menus.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => handleMenuClick(key)}
                className={`w-full flex items-center gap-2 rounded px-3 py-2 text-sm transition
                  ${active === key ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100'} ${
                    loading && active !== key ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                disabled={loading && active !== key}
              >
                <Icon className="w-4 h-4" />
                {label}
              </button>
            ))}
          </nav>

          <DialogContent className="flex-1 !p-4 overflow-auto">
            {active === 'variables' && renderTable(draftVars)}
            {active === 'longterm' && renderTable(draftLong)}
          </DialogContent>
        </div>

        <DialogActions className="border-t px-4 py-3">
          <Button onClick={hide} disabled={loading}>{t('actions.close')}</Button>
          <Button 
            variant="contained" 
            onClick={handleSave}
            disabled={loading}
          >
            {loading ? <CircularProgress size={20} /> : t('actions.save')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
