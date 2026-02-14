import React, { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Tooltip,
  CircularProgress,
  Box,
  IconButton,
  Typography,
  Chip,
} from '@mui/material'
import { Info, Code, Terminal, FileCode, RotateCcw, FileText } from 'lucide-react'
import { PythonCodeEditor, TypeScriptCodeEditor } from '../../../packages/workflow-canvas/src/form-materials/components/code-editor'
// Import the base-editor styles for the code editors to work properly
import '../../../packages/workflow-canvas/src/form-materials/components/base-editor/styles.css'

interface CodePluginToolForm {
  name: string
  description: string
  runtime: 'python3' | 'nodejs'
  code: string
  codeLanguage: 'javascript' | 'python'
}

interface CodeTemplate {
  language: 'javascript' | 'python'
  name: string
  description: string
  template: string
}


interface CodePluginToolFormDialogProps {
  open: boolean
  loading?: boolean
  form: CodePluginToolForm
  onFormChange: (_field: keyof CodePluginToolForm, _value: string) => void
  onSubmit: () => void
  onCancel: () => void
}

const CodePluginToolFormDialog: React.FC<CodePluginToolFormDialogProps> = ({ open, loading = false, form, onFormChange, onSubmit, onCancel }) => {
  const { t } = useTranslation()
  const isFormValid = form.name.trim() && form.description.trim() && form.runtime && form.code.trim()

  const codeTemplates: CodeTemplate[] = useMemo(() => [
    {
      language: 'python',
      name: t('plugins.pluginConfig.templateBasicFunction'),
      description: t('plugins.pluginConfig.templateBasicFunctionDesc'),
      template: `def add_test(a: int, b: int):
  return a + b

def main(args: Args):
  a = args.params['add1']
  b = args.params['add2']
  c = add_test(a, b)

  return {'res': c}`,
    },
    {
      language: 'javascript',
      name: t('plugins.pluginConfig.templateBasicFunction'),
      description: t('plugins.pluginConfig.templateBasicFunctionDesc'),
      template: `function main() {
  /**
   * 主要处理函数
   */
  // 在这里编写您的JavaScript代码
  const result = {
    message: "Hello World!",
    status: "success",
    timestamp: new Date().toISOString()
  };

  return result;
}

// 导出主函数
module.exports = { main };

// 如果直接运行此文件
if (require.main === module) {
  console.log(main());
}`,
    },
  ], [t])

  const runtimeOptions = [
    { value: 'python3', label: 'Python 3', icon: '🐍', description: t('plugins.pluginConfig.pythonDescription', '适用于数据分析、机器学习、自动化脚本') },
    { value: 'nodejs', label: 'Node.js', icon: '🟢', description: t('plugins.pluginConfig.nodejsDescription', '适用于Web API、实时应用、前端构建工具') },
  ]
  // Template state
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [showTemplates, setShowTemplates] = useState(false)

  const availableTemplates = codeTemplates.filter(template => template.language === form.codeLanguage)

  const handleTemplateSelect = (templateName: string) => {
    const template = codeTemplates.find(t => t.name === templateName && t.language === form.codeLanguage)
    if (template) {
      onFormChange('code', template.template)
      setSelectedTemplate(templateName)
    }
  }

  const handleResetCode = () => {
    onFormChange('code', '')
    setSelectedTemplate('')
  }

  const runtimeToLanguage = (runtime: 'python3' | 'nodejs'): 'javascript' | 'python' => {
    return runtime === 'nodejs' ? 'javascript' : 'python'
  }

  const languageToRuntime = (language: 'javascript' | 'python'): 'python3' | 'nodejs' => {
    return language === 'javascript' ? 'nodejs' : 'python3'
  }

  const handleRuntimeChange = (runtime: 'python3' | 'nodejs') => {
    const language = runtimeToLanguage(runtime)
    onFormChange('runtime', runtime)
    onFormChange('codeLanguage', language)
  }

  const handleCodeLanguageChange = (language: 'javascript' | 'python') => {
    const runtime = languageToRuntime(language)
    onFormChange('codeLanguage', language)
    onFormChange('runtime', runtime)
  }

  return (
    <Dialog open={open} onClose={onCancel} maxWidth="md" fullWidth>
      <DialogTitle className="flex items-center space-x-2">
        <Code className="w-5 h-5 text-blue-600" />
        <span>{t('plugins.pluginConfig.createTool', '创建工具')}</span>
      </DialogTitle>

      <DialogContent>
        <div className="space-y-6">
          {/* Tool Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.tools.name', '工具名称')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.pluginConfig.toolNameTooltip', '为工具起一个简洁明了的名称，便于识别和使用')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <TextField
              value={form.name}
              onChange={e => onFormChange('name', e.target.value)}
              fullWidth
              required
              placeholder={t('plugins.pluginConfig.toolNameExample', '例如：获取用户信息、查询天气数据')}
              helperText={`${t('plugins.pluginConfig.toolNameHelper', '建议使用简洁明了的名称，便于识别和使用')} (${form.name.length}/128)`}
              inputProps={{ maxLength: 128 }}
            />
          </div>

          {/* Tool Description */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.tools.description', '工具描述')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.toolConfig.toolDescriptionHelper', '详细描述工具的功能、用途、参数说明等')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <TextField
              value={form.description}
              onChange={e => onFormChange('description', e.target.value)}
              fullWidth
              required
              multiline
              rows={3}
              placeholder={t('plugins.toolConfig.toolDescriptionHelper', '详细描述工具的功能、用途、参数说明等...')}
              helperText={t('plugins.toolConfig.toolDescriptionPlaceholder', { count: form.description.length })}
              inputProps={{ maxLength: 256 }}
            />
          </div>

          {/* Runtime Selection */}
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700 flex items-center">
              {t('plugins.pluginConfig.runtime', 'IDE运行时')} <span className="text-red-500 ml-1">*</span>
              <Tooltip title={t('plugins.pluginConfig.runtimeTooltip', '选择工具运行的编程语言环境')} placement="top">
                <Info className="w-4 h-4 ml-1 text-gray-400 cursor-help" />
              </Tooltip>
            </label>
            <FormControl fullWidth required>
              <InputLabel>{t('plugins.pluginConfig.runtimeEnvironment', '运行时环境')}</InputLabel>
              <Select
                value={form.runtime}
                onChange={e => handleRuntimeChange(e.target.value as 'python3' | 'nodejs')}
                label={t('plugins.pluginConfig.runtimeEnvironment', '运行时环境')}
              >
                {runtimeOptions.map(option => (
                  <MenuItem key={option.value} value={option.value}>
                    <div className="flex flex-col space-y-1 py-1">
                      <div className="flex items-center space-x-2">
                        <span className="text-lg">{option.icon}</span>
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <span className="text-xs text-gray-500 ml-8">{option.description}</span>
                    </div>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </div>

          {/* Runtime Information */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start space-x-3">
              <Terminal className="w-5 h-5 text-blue-600 mt-0.5" />
              <div>
                <h4 className="text-sm font-medium text-blue-900 mb-2">{t('plugins.pluginConfig.runtimeInfoTitle', '运行时环境说明')}</h4>
                <div className="space-y-2 text-sm text-blue-800">
                  <div>
                    <strong>Python 3:</strong> {t('plugins.pluginConfig.pythonSuitableFor', '适合数据处理、机器学习、科学计算、自动化脚本等场景')}
                  </div>
                  <div>
                    <strong>Node.js:</strong> {t('plugins.pluginConfig.nodejsSuitableFor', '适合Web API开发、实时通信、前端构建工具、微服务等场景')}
                  </div>
                  <div className="text-blue-600 text-xs mt-2">
                    💡 {t('plugins.pluginConfig.runtimeSelectionHelper', '选择合适的运行时环境有助于获得最佳性能和兼容性')}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Code Editor Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <h3 className="text-lg font-medium text-gray-900 flex items-center">
                  <FileCode className="w-5 h-5 mr-2 text-purple-600" />
                  {t('plugins.pluginConfig.codeEditor', '代码编辑器')}
                  <span className="text-red-500 ml-1">*</span>
                </h3>
                <div className="ml-2 h-px bg-gray-300 flex-1"></div>
              </div>
              <div className="flex items-center space-x-2">
                <Chip label={`${t('plugins.pluginConfig.language', '语言')}: ${form.codeLanguage === 'javascript' ? 'JavaScript' : 'Python'}`} size="small" />
                <Chip label={t('plugins.pluginConfig.syntaxHighlighting', '语法高亮')} size="small" variant="outlined" />
                {selectedTemplate && (
                  <Chip label={`${t('plugins.pluginConfig.template', '模板')}: ${selectedTemplate}`} size="small" variant="outlined" className="text-xs" />
                )}
              </div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Code className="w-5 h-5 text-blue-600" />
                  <Typography variant="body2" className="font-medium">
                    {t('plugins.pluginConfig.codeEditorEnvironment', '代码编辑环境')}
                  </Typography>
                </div>
                <div className="flex items-center space-x-3">
                  {availableTemplates.length > 0 && (
                    <Button variant="outlined" size="small" onClick={() => setShowTemplates(!showTemplates)} startIcon={<FileText className="w-4 h-4" />}>
                      {t('plugins.pluginConfig.codeTemplates', '代码模板')}
                    </Button>
                  )}
                  <Button variant="outlined" size="small" onClick={handleResetCode} startIcon={<RotateCcw className="w-4 h-4" />}>
                    {t('plugins.pluginConfig.resetCode', '重置代码')}
                  </Button>
                </div>
              </div>

              {/* Template Selection */}
              {showTemplates && availableTemplates.length > 0 && (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <Typography variant="subtitle2" className="mb-3 flex items-center">
                    <FileText className="w-4 h-4 mr-2" />
                    {t('plugins.pluginConfig.selectCodeTemplate', '选择代码模板')}
                  </Typography>

                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {availableTemplates.map(template => (
                      <div
                        key={template.name}
                        className={`p-3 border rounded-lg cursor-pointer transition-all duration-200 ${
                          selectedTemplate === template.name ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-gray-200 hover:border-blue-300 hover:bg-blue-50'
                        }`}
                        onClick={() => handleTemplateSelect(template.name)}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <Typography variant="body2" className="font-medium">
                            {template.name}
                          </Typography>
                          <Chip
                            label={form.codeLanguage === 'javascript' ? 'JS' : 'PY'}
                            size="small"
                            color={form.codeLanguage === 'javascript' ? 'success' : 'info'}
                          />
                        </div>
                        <Typography variant="body2" className="text-gray-600 text-sm">
                          {template.description}
                        </Typography>
                      </div>
                    ))}
                  </div>

                  <div className="mt-3 flex justify-end">
                    <Button size="small" onClick={() => setShowTemplates(false)}>
                      {t('common.buttons.close', '关闭')}
                    </Button>
                  </div>
                </div>
              )}

              <div className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Code editor based on runtime language - no selector here */}
                <div className="bg-gray-50 border-b border-gray-200 p-3">
                  <Typography variant="body2" className="text-gray-600">
                    {t('plugins.pluginConfig.programmingLanguage', '编程语言')}: <span className="font-medium">{form.codeLanguage === 'javascript' ? 'JavaScript' : 'Python'}</span>
                  </Typography>
                </div>

                {/* Code editor based on language */}
                <div className="flex-1" style={{ height: '350px', minHeight: '300px' }}>
                  {form.codeLanguage === 'python' ? (
                    <PythonCodeEditor
                      value={form.code}
                      onChange={code => onFormChange('code', code)}
                      theme="light"
                      minHeight={300}
                      maxHeight={350}
                      lineNumbers={true}
                      foldGutter={true}
                      style={{ height: '100%' }}
                    />
                  ) : (
                    <TypeScriptCodeEditor
                      value={form.code}
                      onChange={code => onFormChange('code', code)}
                      theme="light"
                      minHeight={300}
                      maxHeight={350}
                      lineNumbers={true}
                      foldGutter={true}
                      style={{ height: '100%' }}
                    />
                  )}
                </div>
              </div>

              {/* Usage Tips */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <Typography variant="subtitle2" className="mb-2 text-blue-900">
                  {t('plugins.pluginConfig.usageTips', '💡 使用提示')}
                </Typography>
                <div className="space-y-1 text-sm text-blue-800">
                  {form.codeLanguage === 'python' ? (
                    <>
                      <div>
                        • {t('plugins.pluginConfig.pythonTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main()</code>{' '}
                        {t('plugins.pluginConfig.pythonTips2', '函数作为入口点')}
                      </div>
                      <div>• {t('plugins.pluginConfig.pythonTips3', '使用标准库函数，避免依赖需要额外安装的包')}</div>
                      <div>• {t('plugins.pluginConfig.pythonTips4', '返回JSON序列化的数据结构，便于API调用')}</div>
                    </>
                  ) : (
                    <>
                      <div>
                        • {t('plugins.pluginConfig.jsTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main</code>{' '}
                        {t('plugins.pluginConfig.jsTips2', '函数作为入口点')}
                      </div>
                      <div>• {t('plugins.pluginConfig.jsTips3', '使用CommonJS模块系统（require/module.exports）')}</div>
                      <div>• {t('plugins.pluginConfig.jsTips4', '避免使用ES6模块语法，除非项目支持')}</div>
                      <div>• {t('plugins.pluginConfig.jsTips5', '返回JSON可序列化的数据结构')}</div>
                    </>
                  )}
                  <div>• {t('plugins.pluginConfig.templateTips', '使用模板可以快速开始开发')}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>

      <DialogActions className="px-6 pb-4">
        <Button onClick={onCancel} variant="outlined" disabled={loading}>
          {t('common.actions.cancel', '取消')}
        </Button>
        <Button
          onClick={onSubmit}
          variant="contained"
          color="primary"
          disabled={!isFormValid || loading}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
        >
          {loading ? (
            <>
              <CircularProgress size={16} className="mr-2" />
              {t('common.actions.creating', '创建中...')}
            </>
          ) : (
            t('common.actions.create', '创建')
          )}
        </Button>
      </DialogActions>
    </Dialog>
  )
}

export default CodePluginToolFormDialog
