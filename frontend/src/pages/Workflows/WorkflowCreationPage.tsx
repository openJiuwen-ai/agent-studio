import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus } from 'lucide-react'
import { Button, TextField, Typography, Card } from '@mui/material'
import { useCreateWorkflow } from '@test-agentstudio/api-client'
import { useAuthStore } from '../../stores/useAuthStore'
import { ENV_CONFIG } from '../../config/environment'
import { validateVariableName } from '../../../packages/workflow-canvas/src/form-materials/validate'

interface WorkflowFormData {
  name: string
  description: string
  trigger: string
}

const WorkflowCreationPage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuthStore()
  const [formData, setFormData] = useState<WorkflowFormData>({
    name: '',
    description: '',
    trigger: 'schedule',
  })

  // 工作流名称校验状态
  const [nameValidationError, setNameValidationError] = useState<string>('')

  const createWorkflowMutation = useCreateWorkflow()

  const getDefaultSpaceId = () => {
    return user?.spaceId || ENV_CONFIG.DEFAULT_SPACE_ID
  }

  const spaceId = getDefaultSpaceId()

  const handleInputChange = (field: keyof WorkflowFormData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))

    // 如果是名称字段，进行实时校验
    if (field === 'name') {
      const validationResult = validateVariableName(value as string)
      if (!validationResult.isValid) {
        setNameValidationError(validationResult.message || '')
      } else {
        setNameValidationError('')
      }
    }
  }

  const handleCreate = async () => {
    try {
      const spaceId = getDefaultSpaceId()

      // Create the workflow using API
      const request = {
        name: formData.name.trim(),
        desc: formData.description.trim(),
        space_id: spaceId,
      }

      const response = await createWorkflowMutation.mutateAsync(request)

      if (response.code === 200) {
        const workflowId = response.data.workflow.workflow_id

        // Navigate to the workflow editor with the new workflow ID and space_id
        navigate(`/dashboard/workflows/editor/${workflowId}?spaceId=${spaceId}`)
      } else {
        console.error('创建工作流失败:', response.message)
      }
    } catch (error) {
      console.error('创建工作流失败:', error)
    }
  }

  const handleCancel = () => {
    navigate('/dashboard/workflows')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* Back button */}
        <div className="mb-6">
          <Button
            variant="outlined"
            startIcon={<ArrowLeft />}
            onClick={handleCancel}
            className="border-gray-300 text-gray-600 hover:border-gray-400 hover:bg-gray-50"
          >
            返回
          </Button>
        </div>

        {/* Main content */}
        <Card className="shadow-xl border-0 overflow-hidden">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-8 py-4">
            <div className="flex items-center justify-center">
              <Typography variant="h5" className="text-white font-semibold">
                工作流配置向导
              </Typography>
            </div>
          </div>

          <div className="p-8">
            <div className="space-y-6">
              {/* Workflow Form */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="px-6 py-4 bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200">
                  <Typography variant="h6" className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-gray-900 to-blue-800">
                    基本信息
                  </Typography>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {/* Workflow Name */}
                    <div>
                      <Typography variant="subtitle2" className="text-gray-700 mb-2 font-medium">
                        工作流名称 *
                      </Typography>
                      <TextField
                        fullWidth
                        size="small"
                        placeholder="输入工作流名称（仅支持字母、数字、下划线，且只能以字母开头）"
                        value={formData.name}
                        onChange={e => handleInputChange('name', e.target.value)}
                        inputProps={{ maxLength: 100 }}
                        helperText={nameValidationError ? nameValidationError : !formData.name.trim() ? '名称不能为空' : `${formData.name.length}/100`}
                        error={!formData.name.trim() || !!nameValidationError}
                        className="[& .MuiOutlinedInput-root]:rounded-xl [& .MuiOutlinedInput-root]:border-gray-200 [& .MuiOutlinedInput-root]:focus:border-blue-300 [& .MuiOutlinedInput-root]:focus:ring-blue-500"
                      />
                    </div>

                    {/* Description */}
                    <div>
                      <Typography variant="subtitle2" className="text-gray-700 mb-2 font-medium">
                        工作流描述 *
                      </Typography>
                      <TextField
                        fullWidth
                        size="small"
                        multiline
                        rows={6}
                        placeholder="描述工作流的功能和用途..."
                        value={formData.description}
                        onChange={e => handleInputChange('description', e.target.value)}
                        inputProps={{ maxLength: 500 }}
                        helperText={!formData.description.trim() ? '描述不能为空' : `${formData.description.length}/500`}
                        className="[& .MuiOutlinedInput-root]:rounded-xl [& .MuiOutlinedInput-root]:border-gray-200 [& .MuiOutlinedInput-root]:focus:border-blue-300 [& .MuiOutlinedInput-root]:focus:ring-blue-500"
                        error={!formData.description.trim()}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Action Buttons */}
            <div className="flex justify-end space-x-6 pt-8">
              <Button
                variant="outlined"
                size="large"
                startIcon={<ArrowLeft />}
                onClick={handleCancel}
                className="px-8 py-3 text-gray-600 border-gray-300 hover:border-gray-400 hover:bg-gray-50"
                disabled={createWorkflowMutation.isLoading}
              >
                取消
              </Button>

              <Button
                variant="contained"
                size="large"
                startIcon={createWorkflowMutation.isLoading ? <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div> : <Plus />}
                onClick={handleCreate}
                disabled={!formData.name.trim() || !formData.description.trim() || !!nameValidationError || createWorkflowMutation.isLoading}
                className="px-8 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 shadow-sm hover:shadow-xl transition-all duration-200"
              >
                {createWorkflowMutation.isLoading ? '创建中...' : '创建工作流'}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default WorkflowCreationPage
