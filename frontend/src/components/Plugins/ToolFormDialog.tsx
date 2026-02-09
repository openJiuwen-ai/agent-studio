import React, { useState } from 'react'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  Button,
  IconButton,
  Tooltip,
  CircularProgress,
} from '@mui/material'
import { Info, Plus, Trash } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { validateToolPath, getPathHelpText } from '../../utils/validationUtils'

interface ToolForm {
  name: string
  description: string
  path: string
  method: string
}

interface ToolFormDialogProps {
  open: boolean
  loading?: boolean
  form: ToolForm
  onFormChange: (_field: keyof ToolForm, _value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

const ToolFormDialog: React.FC<ToolFormDialogProps> = ({ open, loading = false, form, onFormChange, onSubmit, onCancel }) => {
  const { t } = useTranslation()
  const [pathError, setPathError] = useState<string>('')

  // 校验路径
  const validatePath = (path: string) => {
    const validation = validateToolPath(path)
    setPathError(validation.error)
    return validation.isValid
  }

  // 处理路径变化
  const handlePathChange = (value: string) => {
    onFormChange('path', value)
    if (value.trim()) {
      validatePath(value)
    } else {
      setPathError('')
    }
  }

  // 表单是否有效
  const isFormValid = form.name.trim() && form.description.trim() && form.path.trim() && form.method && !pathError

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle>{t('plugins.pluginConfig.createTool', '创建工具')}</DialogTitle>
      <DialogContent>
        <div className="space-y-6">
          {/* Basic Info Section */}
          <div className="space-y-4">
            <div className="flex items-center">
              <h3 className="text-lg font-medium text-gray-900">{t('plugins.basicInfoLabel', '基本信息')}</h3>
              <div className="ml-2 h-px bg-gray-300 flex-1"></div>
            </div>

            {/* Tool Name */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                {t('plugins.tools.name', '工具名称')} <span className="text-red-500 ml-1">*</span>
              </label>
              <TextField
                value={form.name}
                onChange={e => onFormChange('name', e.target.value)}
                fullWidth
                required
                placeholder={t('plugins.pluginConfig.toolNameExample', '例如：获取用户信息、查询天气数据')}
                helperText={`${t('plugins.pluginConfig.toolNameHelper', `建议使用简洁明了的名称，便于识别和使用`)} (${form.name.length}/128)`}
                inputProps={{ maxLength: 128 }}
              />
            </div>

            {/* Tool Description */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                {t('plugins.tools.description', '工具描述')} <span className="text-red-500 ml-1">*</span>
              </label>
              <TextField
                value={form.description}
                onChange={e => onFormChange('description', e.target.value)}
                fullWidth
                required
                multiline
                rows={3}
                placeholder={t('plugins.pluginConfig.toolDescriptionTooltip', '详细描述工具的功能、用途、参数说明等...')}
                helperText={`${t('plugins.pluginConfig.toolDescriptionHelper', `建议包含：主要功能、输入参数、输出结果、使用示例等信息`)} (${form.description.length}/256)`}
                inputProps={{ maxLength: 256 }}
              />
            </div>
          </div>

          {/* More Info Section */}
          <div className="space-y-4">
            <div className="flex items-center">
              <h3 className="text-lg font-medium text-gray-900">{t('plugins.pluginConfig.moreInfo', '更多信息')}</h3>
              <div className="ml-2 h-px bg-gray-300 flex-1"></div>
            </div>

            {/* Tool Path */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                {t('plugins.pluginConfig.toolPath', '工具路径')} <span className="text-red-500 ml-1">*</span>
                <Tooltip title={getPathHelpText()} placement="top" arrow>
                  <Info className="w-4 h-4 ml-2 text-gray-400 hover:text-gray-600 cursor-help" />
                </Tooltip>
              </label>
              <TextField
                value={form.path}
                onChange={e => handlePathChange(e.target.value)}
                fullWidth
                required
                placeholder={t('plugins.pluginConfig.toolPathPlaceholder', '例如：/api/users/get')}
                helperText={pathError || t('plugins.pluginConfig.toolPathHelper', '请提供完整的API接口路径，以/开头，只能包含英文、数字、下划线、连字符和斜杠')}
                error={!!pathError}
              />
            </div>

            {/* Request Method */}
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700 flex items-center">
                {t('plugins.pluginConfig.method', '请求方法')} <span className="text-red-500 ml-1">*</span>
              </label>
              <FormControl fullWidth required>
                <Select value={form.method} onChange={e => onFormChange('method', e.target.value)} displayEmpty>
                  <MenuItem value="" disabled>
                    {t('plugins.pluginConfig.methodPlaceholder', '请选择请求方法')}
                  </MenuItem>
                  <MenuItem value="GET">GET</MenuItem>
                  <MenuItem value="POST">POST</MenuItem>
                </Select>
              </FormControl>
            </div>
          </div>
        </div>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel}>{t('common.buttons.cancel', '取消')}</Button>
        <Button onClick={onSubmit} variant="contained" color="primary" disabled={!isFormValid || loading}>
          {loading ? (
            <>
              <CircularProgress size={16} className="mr-2" />
              {t('plugins.config.creating', '创建中...')}
            </>
          ) : (
            t('common.buttons.create', '创建')
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default ToolFormDialog
