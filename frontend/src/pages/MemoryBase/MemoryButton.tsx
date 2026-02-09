import { useState, useEffect, useMemo } from 'react'
import { Dialog, DialogTitle, DialogContent, DialogActions, IconButton, Button, Tooltip, CircularProgress, Alert } from '@mui/material'
import { Shell, Settings, X, Variable, Brain, Trash } from 'lucide-react'
import axios from 'axios'
import { useScopedTranslation } from '@/i18n'

type MenuKey = 'variables' | 'longterm'

/* ---------- 后端接口（占位路径，按实际调整） ---------- */
const api = {
  /* 变量 */
  listVariables: async (user_id: string, group_id: string) => {
    const { data } = await axios.post('/api/v1/execution/memory/get_user_variable', {
      user_id: user_id,
      group_id: group_id,
    })
    return data
  },
  deleteUserVariable: async (user_id: string, group_id: string, key: string) => {
    await axios.post('/api/v1/execution/memory/delete_user_variable', {
      user_id: user_id,
      group_id: group_id,
      name: key,
    })
  },

  /* 长期记忆 */
  listLongTerm: async (user_id: string, group_id: string) => {
    const { data } = await axios.post('/api/v1/execution/memory/get_longterm_mem', {
      user_id: user_id,
      group_id: group_id,
      num: 999,
      page: 1,
    })
    console.log('listLongTerm: ', data)
    return data
  },
  deleteLongTerm: async (user_id: string, group_id: string, id: string) => {
    await axios.post('/api/v1/execution/memory/delete_longterm_mem', {
      user_id: user_id,
      group_id: group_id,
      mem_id: id,
    })
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

/** 把后端 UTC 字符串 -> 本地格式 */
function formatLocalDate(utcStr?: string) {
  if (!utcStr) return ''
  const utc = utcStr.includes('Z') ? utcStr : utcStr.replace(' ', 'T') + 'Z'
  const date = new Date(utc)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export default function MemoryButton({ userId, groupId, enableLongTerm = true }: MemoryButtonProps) {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.memoryManager')
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
      setDraftVars(JSON.parse(JSON.stringify(varList)))
      // 长期记忆数据按修改时间排序
      const sortedLongList = sortLongTermByTime(longList)
      setDraftLong(sortedLongList)
      setToDeleteVar(new Set())
      setToDelete(new Set())
    }
  }, [open, varList, longList])

  /* 弹窗打开时自动刷新全量数据 */
  useEffect(() => {
    if (!open) return
    // 并行拉取变量 & 长期记忆
    Promise.all([api.listVariables(userId, groupId), api.listLongTerm(userId, groupId)])
      .then(([vRes, lRes]) => {
        /* 变量 */
        const vObj = vRes.data.variable_data
        const vList = Object.entries(vObj).map(([k, v], idx) => ({
          id: idx + 1,
          field: k,
          value: String(v),
          time: '', // 隐藏列
        }))
        setVarList(vList)
        setDraftVars(JSON.parse(JSON.stringify(vList)))

        /* 长期记忆 */
        const arr = lRes.data.longterm_mem_data || []
        const lList = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.type || t('menus.longterm'),
          value: r.content,
          _id: r.mem_id,
        }))
        setLongList(lList)
        // 长期记忆数据按修改时间排序
        const sortedLongList = sortLongTermByTime(lList)
        setDraftLong(sortedLongList)

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
        const obj = res.data.variable_data
        const list = Object.entries(obj).map(([k, v], idx) => ({ id: idx + 1, field: k, value: String(v), time: new Date().toLocaleString('zh-CN') }))
        setVarList(list)
        setDraftVars(JSON.parse(JSON.stringify(list)))
      } else {
        const res = await api.listLongTerm(userId, groupId)
        const arr = res.data.longterm_mem_data || []
        const list = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.profile_type || t('menus.longterm'),
          value: r.content,
          time: formatLocalDate(r.time || r.timestamp) || new Date().toLocaleString('zh-CN'),
          _id: r.id,
        }))
        setLongList(list)
        // 长期记忆数据按修改时间排序
        const sortedLongList = sortLongTermByTime(list)
        setDraftLong(sortedLongList)
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
      // 删除后重新排序
      setDraftLong(prev => sortLongTermByTime(prev.filter(r => r.id !== id)))
    }
  }

  /* 保存：执行删除操作，最后拉全量 */
  const handleSave = async () => {
    try {
      /* 1. 变量：删除 */
      if (active === 'variables') {
        const delArr = Array.from(toDeleteVar)
        if (delArr.length) await Promise.all(delArr.map(k => api.deleteUserVariable(userId, groupId, k)))

        const freshRes = await api.listVariables(userId, groupId)
        const freshList = Object.entries(freshRes.data.variable_data).map(([k, v], idx) => ({
          id: idx + 1,
          field: k,
          value: String(v),
          time: new Date().toLocaleString('zh-CN'),
        }))
        setVarList(freshList)
        setToDeleteVar(new Set())
        setDraftVars(JSON.parse(JSON.stringify(freshList)))
      }

      /* 2. 长期记忆：删除 */
      if (active === 'longterm') {
        const delArr = Array.from(toDelete)
        if (delArr.length) await Promise.all(delArr.map(id => api.deleteLongTerm(userId, groupId, id)))

        const freshRes = await api.listLongTerm(userId, groupId)
        const arr = freshRes.data.longterm_mem_data || []
        const freshList = arr.map((r: any, idx: number) => ({
          id: idx + 1,
          field: r.profile_type || t('menus.longterm'),
          value: r.content,
          time: formatLocalDate(r.time || r.timestamp) || new Date().toLocaleString('zh-CN'),
          _id: r.id,
        }))
        setLongList(freshList)
        // 保存后重新排序
        const sortedFreshList = sortLongTermByTime(freshList)
        setDraftLong(sortedFreshList)
        setToDelete(new Set())
      }

      hide()
    } catch (e: any) {
      alert(t('errors.saveFailed') + (e.message || t('errors.unknown')))
    }
  }

  /* 通用表格渲染 */
  const renderTable = (list: Row[]) => {
    if (loading) return <CircularProgress className="!w-6 !h-6" />
    if (error) return <Alert severity="error">{error}</Alert>
    if (list.length === 0) return <div className="text-sm text-gray-400">{t('table.empty')}</div>

    const isLong = active === 'longterm'
    const gridCls = isLong ? 'grid grid-cols-[1fr_1fr_36px]' : 'grid grid-cols-[1fr_1fr_36px]'

    return (
      <div className="space-y-3">
        <div className={`${gridCls} items-center text-sm text-gray-500 px-3`}>
          {isLong ? (
            <>
              <span>{t('table.headers.longTerm.memory')}</span>
              <span>{t('table.headers.longTerm.updatedAt')}</span>
              <span />
            </>
          ) : (
            <>
              <span>{t('table.headers.variables.field')}</span>
              <span>{t('table.headers.variables.value')}</span>
              <span />
            </>
          )}
        </div>

        {list.map(row => (
          <div key={row.id} className={`${gridCls} items-center rounded border border-gray-200 p-3`}>
            {isLong ? (
              <>
                <span className="text-gray-600 px-2 py-1">{row.value}</span>
                <span className="text-gray-400">{row.time}</span>
              </>
            ) : (
              <>
                <span className="font-medium">{row.field}</span>
                <span className="text-gray-600 px-2 py-1">{row.value}</span>
              </>
            )}

            <Tooltip title={t('delete.tooltip')} arrow>
              <IconButton size="small" onClick={() => handleDelete(row.id)} className="text-gray-400 hover:text-red-600">
                <Trash className="w-4 h-4" />
              </IconButton>
            </Tooltip>
          </div>
        ))}
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
        <IconButton aria-label={t('ariaLabel')} size="small" onClick={show} className="border border-blue-300 text-blue-600 hover:border-blue-400 hover:bg-blue-50">
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
                  ${active === key ? 'bg-blue-100 text-blue-700' : 'hover:bg-gray-100'}`}
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
          <Button onClick={hide}>{t('actions.close')}</Button>
          <Button variant="contained" onClick={handleSave}>
            {t('actions.save')}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}
