import React from 'react'

export interface TabSwitchOption {
  value: string
  label: string
}

export interface TabSwitchProps {
  /** 选项列表 */
  options: TabSwitchOption[]
  /** 当前选中的 value */
  value: string
  /** 切换回调 */
  onChange: (value: string) => void
  /** 根容器额外 class（如定位：absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2） */
  className?: string
}

/**
 * 通用 Tab 切换按钮组：灰底圆角容器，选中项白底阴影。
 */
const TabSwitch: React.FC<TabSwitchProps> = ({ options, value, onChange, className = '' }) => {
  return (
    <div
      className={`inline-flex bg-gray-100 rounded-lg p-0.5 ${className}`.trim()}
      role="tablist"
      aria-label="tab switch"
    >
      {options.map(opt => (
        <button
          key={opt.value}
          type="button"
          role="tab"
          aria-selected={value === opt.value}
          onClick={() => onChange(opt.value)}
          className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors whitespace-nowrap ${
            value === opt.value ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-600 hover:text-gray-900'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export default TabSwitch
