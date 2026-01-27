import { useState, MouseEvent } from 'react'
import { useScopedTranslation } from '@/i18n'
import { Menu, MenuItem } from '@mui/material'
import { Plus } from 'lucide-react'

const AddButton = ({
  onSelect,
  options,
  disabled = false,
}: {
  onSelect: (addType: string) => void
  options?: Array<{ label: string; value: string }>
  disabled?: boolean
}) => {
  const { t } = useScopedTranslation('agents')
  const defaultOptions = [
    { label: t('addBtn.addExisting'), value: 'existing' },
    { label: t('addBtn.createNew'), value: 'new' },
  ]
  const finalOptions = options || defaultOptions

  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  const handleClick = (event: MouseEvent<HTMLElement>) => {
    event.stopPropagation()
    if (!disabled) {
      setAnchorEl(event.currentTarget)
    }
  }

  const handleClose = () => {
    setAnchorEl(null)
  }

  return (
    <>
      <div
        className={`p-1 rounded-full flex items-center justify-center ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer hover:bg-gray-100'}`}
        onClick={handleClick}
        aria-disabled={disabled}
      >
        <Plus className="w-4 h-4 text-gray-600" />
      </div>
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        onClick={e => e.stopPropagation()}
        PaperProps={{
          elevation: 0,
          sx: {
            overflow: 'visible',
            filter: 'drop-shadow(0px 2px 8px rgba(0,0,0,0.15))',
            mt: 1,
          },
        }}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
      >
        {finalOptions.map((option, index) => (
          <MenuItem
            key={index}
            onClick={() => {
              if (!disabled) {
                onSelect(option.value)
                handleClose()
              }
            }}
            disabled={disabled}
          >
            {option.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  )
}

export default AddButton
