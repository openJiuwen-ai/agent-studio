import React, { createContext } from 'react'

interface CardContextValue {
  onClick?: () => void
}

const CardContext = createContext<CardContextValue | undefined>(undefined)

interface CardProps {
  children: React.ReactNode
  className?: string
  onClick?: () => void
}

export const Card: React.FC<CardProps> = ({ children, className, onClick }) => {
  return (
    <CardContext.Provider value={{ onClick }}>
      <div
        className={`group bg-white rounded-[8px] border border-[#E2E8F0] hover:border-[#CBD5E1] hover:shadow-sm transition-all duration-200 cursor-pointer flex flex-col ${className || ''}`}
        onClick={onClick}
      >
        {children}
      </div>
    </CardContext.Provider>
  )
}

interface CardHeaderProps {
  children: React.ReactNode
  className?: string
}

export const CardHeader: React.FC<CardHeaderProps> = ({ children, className }) => {
  return (
    <div className={`flex gap-3 px-5 pt-4 pb-3 ${className || ''}`}>
      {children}
    </div>
  )
}

interface CardHeaderIconProps {
  children: React.ReactNode
  bgColor?: string
  textColor?: string
  className?: string
}

export const CardHeaderIcon: React.FC<CardHeaderIconProps> = ({ children, bgColor, textColor, className }) => {
  return (
    <div className={`w-12 flex-shrink-0 ${bgColor || ''} rounded-lg flex items-center justify-center ${className || ''}`}>
      <span className={textColor || ''}>{children}</span>
    </div>
  )
}

interface CardHeaderContentProps {
  children: React.ReactNode
  className?: string
}

export const CardHeaderContent: React.FC<CardHeaderContentProps> = ({ children, className }) => {
  return (
    <div className={`flex-1 min-w-0 flex flex-col h-[48px] ${className || ''}`}>
      {children}
    </div>
  )
}

interface CardBodyProps {
  children: React.ReactNode
  className?: string
}

export const CardBody: React.FC<CardBodyProps> = ({ children, className }) => {
  return (
    <div className={`px-5 pb-2 flex-1 ${className || ''}`}>
      {children}
    </div>
  )
}

interface CardFooterProps {
  children: React.ReactNode
  className?: string
  showBorder?: boolean
}

export const CardFooter: React.FC<CardFooterProps> = ({ children, className, showBorder = true }) => {
  return (
    <div className={`px-5 pb-3 pt-0 ${showBorder ? 'border-t border-transparent' : ''} ${className || ''}`}>
      {children}
    </div>
  )
}

interface CardFooterRowProps {
  children: React.ReactNode
  className?: string
}

export const CardFooterRow: React.FC<CardFooterRowProps> = ({ children, className }) => {
  return (
    <div className={`flex items-center justify-between ${className || ''}`}>
      {children}
    </div>
  )
}

export default Card
