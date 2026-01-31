export interface Agent {
  agent_id: string
  agent_name: string
  description: string
  icon: string
  status: string
  model_name: string
  lastActive: string
  usage_count: number
  tags: string[]
  create_time: number
  update_time?: number
  api_endpoint: string
  agent_version: string
  agent_type: string
  model?: {
    model_info: {
      model_name: string
    }
  }
}

export interface DeleteDialogState {
  isOpen: boolean
  agentId: string
  agentName: string
}

