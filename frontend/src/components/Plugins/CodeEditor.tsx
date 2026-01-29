import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Box, FormControl, InputLabel, Select, MenuItem, Button, Typography, Tooltip, IconButton, Chip, Snackbar, Alert } from '@mui/material'
import { Code, Play, RotateCcw, FileText, Copy, Check } from 'lucide-react'
import CodeMirror from '@uiw/react-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { oneDark } from '@codemirror/theme-one-dark'

interface CodeEditorProps {
  code: string
  language: 'javascript' | 'python'
  onCodeChange: (code: string) => void
  onLanguageChange: (language: 'javascript' | 'python') => void
  onRun?: () => void
  height?: string
  readOnly?: boolean
}

interface CodeTemplate {
  language: 'javascript' | 'python'
  name: string
  description: string
  template: string
}

const codeTemplates: CodeTemplate[] = [
  {
    language: 'python',
    name: '基础函数',
    description: '简单的数据处理函数',
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
    name: '基础函数',
    description: '简单的数据处理函数',
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
]

const CodeEditor: React.FC<CodeEditorProps> = ({ code, language, onCodeChange, onLanguageChange, onRun, height = '400px', readOnly = false }) => {
  const { t } = useTranslation()
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [showTemplates, setShowTemplates] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)
  const [copyError, setCopyError] = useState<string | null>(null)

  const extensions = [language === 'javascript' ? javascript({ jsx: true }) : python(), oneDark]

  const languageExtensions = {
    javascript: 'js',
    python: 'py',
  }

  const languageOptions = [
    { value: 'javascript', label: 'JavaScript', icon: '🟢', extension: 'js' },
    { value: 'python', label: 'Python 3', icon: '🐍', extension: 'py' },
  ]

  const availableTemplates = codeTemplates.filter(template => template.language === language)

  const handleTemplateSelect = (templateName: string) => {
    const template = codeTemplates.find(t => t.name === templateName && t.language === language)
    if (template) {
      onCodeChange(template.template)
      setSelectedTemplate(templateName)
    }
  }

  const handleCopyCode = async () => {
    try {
      setCopyError(null)
      setCopySuccess(false)

      // Try modern Clipboard API first (available in secure contexts)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(code)
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
        return
      }

      // Fallback to older method for broader compatibility
      const textArea = document.createElement('textarea')
      textArea.value = code

      // Make the textarea invisible
      textArea.style.position = 'fixed'
      textArea.style.left = '-999999px'
      textArea.style.top = '-999999px'
      textArea.style.opacity = '0'
      textArea.style.pointerEvents = 'none'
      textArea.setAttribute('readonly', '')

      // Add to DOM, select, and copy
      document.body.appendChild(textArea)
      textArea.select()
      textArea.setSelectionRange(0, 999999) // For mobile devices

      const successful = document.execCommand('copy')

      // Clean up
      document.body.removeChild(textArea)

      if (successful) {
        setCopySuccess(true)
        setTimeout(() => setCopySuccess(false), 2000)
      } else {
        throw new Error('Copy command failed')
      }
    } catch (error) {
      console.error('Failed to copy code:', error)
      setCopyError(t('plugins.pluginConfig.copyCodeFailed', '复制失败，请手动选择并复制代码'))
      setTimeout(() => setCopyError(null), 3000)
    }
  }

  const handleResetCode = () => {
    onCodeChange('')
    setSelectedTemplate('')
  }

  const getLanguageFromRuntime = () => {
    return language === 'javascript' ? 'javascript' : 'python'
  }

  return (
    <div className="space-y-4">
      {/* Language Selector and Actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <FormControl size="small" style={{ minWidth: '200px' }}>
            <InputLabel>{t('plugins.pluginConfig.language', '语言')}</InputLabel>
            <Select
              value={getLanguageFromRuntime()}
              onChange={e => onLanguageChange(e.target.value as 'javascript' | 'python')}
              label={t('plugins.pluginConfig.language', '语言')}
              disabled={readOnly}
            >
              {languageOptions.map(option => (
                <MenuItem key={option.value} value={option.value}>
                  <div className="flex items-center space-x-2">
                    <span>{option.icon}</span>
                    <span>{option.label}</span>
                    <span className="text-xs text-gray-500">.{option.extension}</span>
                  </div>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Template Selector */}
          {availableTemplates.length > 0 && (
            <Button variant="outlined" size="small" onClick={() => setShowTemplates(!showTemplates)} startIcon={<FileText className="w-4 h-4" />}>
              {t('plugins.pluginConfig.codeTemplates', '代码模板')}
            </Button>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center space-x-2">
          <Tooltip title={copySuccess ? t('plugins.pluginConfig.copySuccess', '复制成功!') : t('plugins.pluginConfig.copyCode', '复制代码')}>
            <IconButton size="small" onClick={handleCopyCode} disabled={!code.trim()} color={copySuccess ? 'success' : 'default'}>
              {copySuccess ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
            </IconButton>
          </Tooltip>

          <Tooltip title={t('plugins.pluginConfig.resetCode', '重置代码')}>
            <IconButton size="small" onClick={handleResetCode}>
              <RotateCcw className="w-4 h-4" />
            </IconButton>
          </Tooltip>

          {onRun && (
            <Button variant="contained" size="small" onClick={onRun} disabled={!code.trim()} startIcon={<Play className="w-4 h-4" />}>
              {t('plugins.pluginConfig.runCode', '运行代码')}
            </Button>
          )}
        </div>
      </div>

      {/* Template Selection */}
      {showTemplates && availableTemplates.length > 0 && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
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
                  <Chip label={language === 'javascript' ? 'JS' : 'PY'} size="small" color={language === 'javascript' ? 'success' : 'info'} />
                </div>
                <Typography variant="body2" className="text-gray-600 text-sm">
                  {template.description}
                </Typography>
              </div>
            ))}
          </div>

          <div className="mt-3 flex justify-end">
            <Button size="small" onClick={() => setShowTemplates(false)}>
              {t('common.actions.close', '关闭')}
            </Button>
          </div>
        </div>
      )}

      {/* Code Editor */}
      <div className="border border-gray-300 rounded-lg overflow-hidden">
        <div className="bg-gray-800 text-gray-200 px-4 py-2 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Code className="w-4 h-4" />
            <Typography variant="body2" className="font-mono text-sm">
              main.{languageExtensions[language]}
            </Typography>
          </div>
          {selectedTemplate && <Chip label={`${t('plugins.pluginConfig.template', '模板')}: ${selectedTemplate}`} size="small" variant="outlined" className="text-xs" />}
        </div>

        <Box
          sx={{
            height,
            maxHeight: '600px', // 设置最大高度，避免过长
            overflow: 'auto', // 允许滚动
            '& .cm-editor': {
              height: '100% !important',
            },
            '& .cm-scroller': {
              overflowX: 'auto !important', // 水平滚动
              overflowY: 'auto !important', // 垂直滚动
            }
          }}
        >
          <CodeMirror
            value={code}
            height="100%"
            extensions={extensions}
            theme={oneDark}
            onChange={onCodeChange}
            basicSetup={{
              lineNumbers: true,
              highlightActiveLineGutter: true,
              highlightActiveLine: true,
              foldGutter: true,
              dropCursor: false,
              allowMultipleSelections: true,
              indentOnInput: true,
              bracketMatching: true,
              autocompletion: true,
              highlightSelectionMatches: true,
            }}
            editable={!readOnly}
            placeholder={`${t('plugins.pluginConfig.writeCodeHere', { language: language === 'javascript' ? 'JavaScript' : 'Python' })}`}
          />
        </Box>
      </div>

      {/* Usage Tips */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <Typography variant="subtitle2" className="mb-2 text-blue-900">
          {t('plugins.pluginConfig.usageTips', '💡 使用提示')}
        </Typography>
        <div className="space-y-1 text-sm text-blue-800">
          {language === 'python' ? (
            <>
              <div>
                • {t('plugins.pluginConfig.pythonTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main()</code> {t('plugins.pluginConfig.pythonTips2', '函数作为入口点')}
              </div>
              <div>• {t('plugins.pluginConfig.pythonTips3', '使用标准库函数，避免依赖需要额外安装的包')}</div>
              <div>• {t('plugins.pluginConfig.pythonTips4', '返回JSON序列化的数据结构，便于API调用')}</div>
            </>
          ) : (
            <>
              <div>
                • {t('plugins.pluginConfig.jsTips1', '确保导出')} <code className="bg-blue-100 px-1 rounded">main</code> {t('plugins.pluginConfig.jsTips2', '函数作为入口点')}
              </div>
              <div>• {t('plugins.pluginConfig.jsTips3', '使用CommonJS模块系统（require/module.exports）')}</div>
              <div>• {t('plugins.pluginConfig.jsTips4', '避免使用ES6模块语法，除非项目支持')}</div>
              <div>• {t('plugins.pluginConfig.jsTips5', '返回JSON可序列化的数据结构')}</div>
            </>
          )}
          <div>• {t('plugins.pluginConfig.templateTips', '使用模板可以快速开始开发')}</div>
        </div>
      </div>

      {/* Error Snackbar */}
      <Snackbar open={!!copyError} autoHideDuration={3000} onClose={() => setCopyError(null)} anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert onClose={() => setCopyError(null)} severity="error" sx={{ width: '100%' }}>
          {copyError}
        </Alert>
      </Snackbar>
    </div>
  )
}

export default CodeEditor
