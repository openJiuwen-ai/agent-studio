import React from 'react'
import { Search, X } from 'lucide-react'

export interface SearchInputProps {
  searchTerm: string
  placeholder: string
  onChange: (value: string) => void
  onCompositionStart?: () => void
  onCompositionEnd?: () => void
}

export const SearchInput: React.FC<SearchInputProps> = ({
  searchTerm,
  placeholder,
  onChange,
  onCompositionStart,
  onCompositionEnd,
}) => {
  return (
    <div className="relative w-80">
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#9CA3AF]" />
      <input
        type="text"
        placeholder={placeholder}
        value={searchTerm}
        onChange={e => onChange(e.target.value)}
        onCompositionStart={onCompositionStart}
        onCompositionEnd={onCompositionEnd}
        className="w-full h-8 pl-8 pr-7 bg-white border border-[#E5E7EB] rounded-[6px] text-sm text-[#1F2937] placeholder-[#9CA3AF] focus:outline-none focus:border-[#3B82F6] focus:ring-1 focus:ring-[#3B82F6] transition-colors"
      />
      {searchTerm && (
        <button
          onClick={() => onChange('')}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
          type="button"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  )
}

export default SearchInput
