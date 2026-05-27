import React, { useState, useRef, useEffect, useMemo } from 'react'
import { createPortal } from 'react-dom'
import { Maximize2, X } from 'lucide-react'

interface Props {
  htmlContent: string
  title: string
}

function parseNaturalDimensions(html: string): { width: number; height: number } {
  const match =
    html.match(/class="chart-container"[^>]*style="width:(\d+)px;\s*height:(\d+)px/) ||
    html.match(/style="width:(\d+)px;\s*height:(\d+)px/)
  if (match) {
    return { width: parseInt(match[1]), height: parseInt(match[2]) }
  }
  return { width: 1500, height: 750 }
}

export const InteractiveChartIframe: React.FC<Props> = ({ htmlContent, title }) => {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const [scale, setScale] = useState(1)

  const { width: naturalWidth, height: naturalHeight } = useMemo(
    () => parseNaturalDimensions(htmlContent),
    [htmlContent]
  )

  useEffect(() => {
    const el = wrapperRef.current
    if (!el) return
    const observer = new ResizeObserver(([entry]) => {
      const containerWidth = entry.contentRect.width
      setScale(containerWidth / naturalWidth)
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [naturalWidth])

  const scaledHeight = Math.round(naturalHeight * scale)

  return (
    <>
      {/* 缩放内联视图 */}
      <div ref={wrapperRef} style={{ position: 'relative', width: '100%', margin: '16px 0' }}>
        <div
          style={{
            height: scaledHeight,
            overflow: 'hidden',
            position: 'relative',
            borderRadius: 8,
            border: '1px solid #e5e7eb',
            background: '#fff',
          }}
        >
          <iframe
            srcDoc={htmlContent}
            title={title}
            style={{
              width: naturalWidth,
              height: naturalHeight,
              border: 'none',
              transform: `scale(${scale})`,
              transformOrigin: 'top left',
              position: 'absolute',
              top: 0,
              left: 0,
            }}
          />
        </div>

        {/* 展开按钮 */}
        <button
          onClick={() => setIsModalOpen(true)}
          title="展开查看原图"
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            background: 'rgba(255,255,255,0.92)',
            border: '1px solid #e5e7eb',
            borderRadius: 6,
            padding: '4px 10px',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 4,
            fontSize: 12,
            color: '#555',
            zIndex: 2,
            boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
          }}
        >
          <Maximize2 size={13} />
          展开
        </button>
      </div>

      {/* 全页面弹窗，挂到 document.body */}
      {isModalOpen && createPortal(
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 9999,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onClick={(e) => { if (e.target === e.currentTarget) setIsModalOpen(false) }}
        >
          <div
            style={{
              background: 'white',
              borderRadius: 12,
              overflow: 'hidden',
              maxWidth: '95vw',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
            }}
          >
            {/* 弹窗标题栏 */}
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 16px',
                borderBottom: '1px solid #eee',
                flexShrink: 0,
              }}
            >
              <span style={{ fontSize: 14, fontWeight: 600, color: '#333' }}>
                {title || '交互图表'}
              </span>
              <button
                onClick={() => setIsModalOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  padding: 4,
                  borderRadius: 4,
                  color: '#666',
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <X size={18} />
              </button>
            </div>

            {/* 弹窗内原图大小 iframe，支持滚动 */}
            <div style={{ overflow: 'auto', flex: 1 }}>
              <iframe
                srcDoc={htmlContent}
                title={title}
                style={{
                  width: naturalWidth,
                  height: naturalHeight,
                  border: 'none',
                  display: 'block',
                }}
              />
            </div>
          </div>
        </div>,
        document.body
      )}
    </>
  )
}
