/**
 * MarkdownLink 组件
 * 只处理普通链接 <a href="url">text</a>
 */

import React from 'react'

export interface MarkdownLinkProps {
  href?: string
  children: React.ReactNode
  className?: string
  target?: string
  rel?: string
}

/**
 * Markdown 普通链接组件
 *
 * @description
 * - 处理标准的 Markdown 链接
 * - 支持自定义 target、rel 等属性
 * - 不处理引用链接或推理图链接
 */
export const MarkdownLink: React.FC<MarkdownLinkProps> = ({
  href,
  children,
  className = 'text-primary hover:underline',
  target = '_blank',
  rel = 'noopener noreferrer',
}) => {
  return (
    <a href={href} target={target} rel={rel} className={className}>
      {children}
    </a>
  )
}