/**
 * Markdown 核心渲染组件
 * 使用 react-markdown 进行渲染，支持自定义组件
 */

import React, { useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import 'katex/dist/katex.min.css'
import type { Components } from 'react-markdown'
import type { MarkdownProps } from './types'
import { MarkdownLink } from './MarkdownLink'
import { CitationLink } from '../CitationPanel/CitationLink'
import { InferenceLink } from '../InferenceGraph'
import { SmartImage } from './SmartImage'
import { MermaidChart } from './MermaidChart/index'

/**
 * Markdown 核心渲染器
 */
export const MarkdownRenderer: React.FC<{
  instanceId?: MarkdownProps['instanceId']
  content: string
  citations?: MarkdownProps['citations']
  inferMessages?: MarkdownProps['inferMessages']
}> = ({ content, citations, instanceId, inferMessages }) => {
  // 构建默认组件映射
  const defaultComponents = useMemo(() => {
    const markdownComponents: Components = {
      // 处理 a 标签
      a: ({ node, href, children, ...rest }) => {
        const childrenText = children !== undefined && children !== null ? children.toString() : ''

        // 判断链接类型
        const isInferenceLink = /#inference:\d+/.test(href || '')
        const isCitation = /^\[(\d+)\]$/.test(childrenText)

        // 推理图链接 → InferenceLink
        if (isInferenceLink) {
          return (
            <InferenceLink
              key={`${instanceId || 'no-id'}-inference-${childrenText}`}
              href={href}
              instanceId={instanceId}
            >
              {children}
            </InferenceLink>
          )
        }

        // 引用链接 → CitationLink
        if (isCitation) {
          return (
            <CitationLink
              key={`${instanceId || 'no-id'}-citation-${childrenText}`}
              href={href}
              citations={citations}
              markdownInstanceId={instanceId}
            >
              {children}
            </CitationLink>
          )
        }

        // 普通链接 → MarkdownLink
        return (
          <MarkdownLink key={`${instanceId || 'no-id'}-link-${childrenText}`} href={href ?? '#'} {...rest}>
            {children}
          </MarkdownLink>
        )
      },

      // 处理 img 标签
      img: ({ node, src, alt, ...rest }) => {
        return <SmartImage src={src || ''} alt={alt || ''} {...rest} />
      },

      // 处理代码块（pre 标签）
      pre: ({ node, children, ...rest }) => {
        // 检查是否是 mermaid 代码块
        if (React.isValidElement(children)) {
          const childElement = children as React.ReactElement<any>
          if (childElement.props?.className?.includes('language-mermaid')) {
            const codeContent = childElement.props?.children
            const code = Array.isArray(codeContent) ? codeContent.join('') : String(codeContent || '')
            return <MermaidChart code={code.replace(/\n$/, '')} />
          }
        }
        return <pre {...rest}>{children}</pre>
      },

      // 处理行内代码
      code({ node, className, children, ...rest }) {
        return (
          <code className={className} {...rest}>
            {children}
          </code>
        )
      },
    }

    return markdownComponents
  }, [citations, instanceId])

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, [remarkMath, { singleDollarTextMath: true }]]}
      rehypePlugins={[rehypeRaw, rehypeKatex]}
      components={defaultComponents}
    >
      {content}
    </ReactMarkdown>
  )
}
