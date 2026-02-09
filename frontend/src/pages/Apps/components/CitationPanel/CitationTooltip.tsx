/**
 * 引用提示组件（基于 Radix UI Tooltip）
 */

import React from 'react'
import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import { cn } from '@test-agentstudio/base-ui'

export interface CitationTooltipProps {
  children: React.ReactNode
  title: React.ReactNode
  open?: boolean
  onOpenChange?: (open: boolean) => void
  side?: 'top' | 'right' | 'bottom' | 'left'
  sideOffset?: number
  delayDuration?: number
  className?: string
}

function ShadcnTooltip({ children, delayDuration, open }: { children: React.ReactNode; delayDuration?: number; open?: boolean }) {
  return (
    <TooltipPrimitive.Provider delayDuration={delayDuration}>
      <TooltipPrimitive.Root open={open}>{children}</TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  )
}

// TooltipTrigger 组件
function TooltipTrigger({ children }: { children: React.ReactNode }) {
  return <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
}

// TooltipContent 组件
function TooltipContent({
  className,
  side,
  sideOffset,
  children,
}: {
  className?: string
  side?: 'top' | 'right' | 'bottom' | 'left'
  sideOffset?: number
  children: React.ReactNode
}) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        className={cn(
          'animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 z-[70] max-w-[32rem] origin-(--radix-tooltip-content-transform-origin) rounded-lg shadow-lg border border-gray-200 bg-white [&_svg]:!bg-white [&_svg]:!fill-white',
          className,
        )}
        side={side}
        sideOffset={sideOffset}
      >
        {children}
        <TooltipPrimitive.Arrow className="fill-white" />
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  )
}

/**
 * 引用提示组件
 */
export const CitationTooltip: React.FC<CitationTooltipProps> = ({
  children,
  title,
  open,
  side = 'top',
  sideOffset = 2,
  delayDuration = 750,
  className
}) => {
  return (
    <ShadcnTooltip delayDuration={delayDuration} open={open}>
      <TooltipTrigger>{children}</TooltipTrigger>
      <TooltipContent className={className} side={side} sideOffset={sideOffset}>
        {title}
      </TooltipContent>
    </ShadcnTooltip>
  )
}

export default CitationTooltip