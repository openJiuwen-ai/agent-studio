/**
 * 智能图片组件
 * 支持懒加载、错误处理、降级显示
 */

import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { ImageOff } from 'lucide-react'
import type { ImageProps } from './types'

/**
 * 图片加载状态
 */
type ImageLoadStatus = 'loading' | 'loaded' | 'error'

/**
 * 降级显示组件
 */
const ImageFallback: React.FC<{ alt?: string }> = ({ alt: _alt }) => {
  const { t } = useTranslation()
  return (
    <div className="inline-flex items-center justify-center w-64 h-40 bg-gray-100 rounded-lg border-2 border-dashed border-gray-300">
      <div className="text-center p-4">
        <ImageOff className="w-8 h-8 mx-auto text-gray-400 mb-2" strokeWidth={1.5} />
        <p className="text-xs text-gray-500">{t('apps.notifications.imageLoadFailed')}</p>
      </div>
    </div>
  )
}

/**
 * 加载占位符
 */
const ImageSkeleton: React.FC = () => (
  <div className="inline-flex items-center justify-center w-64 h-40 bg-gray-100 rounded-lg animate-pulse">
    <div className="w-full h-full flex items-center justify-center">
      <div className="w-12 h-12 border-4 border-gray-300 border-t-blue-500 rounded-full animate-spin" />
    </div>
  </div>
)

/**
 * 智能图片组件
 */
export const SmartImage: React.FC<ImageProps> = ({
  src,
  alt = '',
  className = 'rounded',
  loading = 'lazy',
  width,
  height,
}) => {
  const [status, setStatus] = useState<ImageLoadStatus>('loading')
  const imgRef = useRef<HTMLImageElement>(null)

  const handleError = () => {
    setStatus('error')
  }

  const handleLoad = () => {
    setStatus('loaded')
  }

  // 如果加载失败，显示降级 UI
  if (status === 'error') {
    return <ImageFallback alt={alt} />
  }

  // 如果正在加载且设置了懒加载，显示骨架屏
  if (status === 'loading' && loading === 'lazy') {
    return (
      <div className="relative">
        <ImageSkeleton />
        <img
          ref={imgRef}
          src={src}
          alt={alt}
          className="absolute inset-0 opacity-0"
          loading={loading}
          width={width}
          height={height}
          onError={handleError}
          onLoad={handleLoad}
        />
      </div>
    )
  }

  // 正常显示图片（可点击查看大图）
  return (
    <a
      href={src}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-block"
    >
      <img
        ref={imgRef}
        src={src}
        alt={alt}
        className={className}
        loading={loading}
        width={width}
        height={height}
        onError={handleError}
        onLoad={handleLoad}
      />
    </a>
  )
}

export default SmartImage