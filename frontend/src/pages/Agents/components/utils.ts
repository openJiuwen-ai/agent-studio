const colors = [
  { bg: 'bg-[#dbeafe]', text: 'text-[#3b82f6]' },      // blue
  { bg: 'bg-[#dcfce7]', text: 'text-[#22c55e]' },      // green
  { bg: 'bg-[#fef9c3]', text: 'text-[#eab308]' },      // yellow
  { bg: 'bg-[#fee2e2]', text: 'text-[#ef4444]' },      // red
  { bg: 'bg-[#f3e8ff]', text: 'text-[#a855f7]' },      // purple
  { bg: 'bg-[#fce7f3]', text: 'text-[#ec4899]' },      // pink
  { bg: 'bg-[#e0f2fe]', text: 'text-[#0ea5e9]' },      // sky
  { bg: 'bg-[#fef3c7]', text: 'text-[#f59e0b]' },      // amber
]

const getAgentColorIndex = (agentId: string): number => {
  let hash = 0
  for (let i = 0; i < agentId.length; i++) {
    hash = agentId.charCodeAt(i) + ((hash << 5) - hash)
  }
  return Math.abs(hash) % colors.length
}

export const getAgentIconColor = (agent: { agent_id: string }): string => {
  return colors[getAgentColorIndex(agent.agent_id)].bg
}

export const getAgentIconTextColor = (agent: { agent_id: string }): string => {
  return colors[getAgentColorIndex(agent.agent_id)].text
}
