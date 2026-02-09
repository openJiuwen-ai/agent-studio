import React from 'react'
import { Typography, Slider, TextField, Tooltip, IconButton, Box } from '@mui/material'
import { HelpCircle } from 'lucide-react'

interface SliderFieldProps {
  label: string
  tooltip: string
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step?: number
  disabled?: boolean
  valueLabelFormat?: (value: number) => string
  minLabel?: string
  maxLabel?: string
  inputEndAdornment?: React.ReactNode
  allowZero?: boolean
}

export const SliderField: React.FC<SliderFieldProps> = ({
  label,
  tooltip,
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled = false,
  valueLabelFormat,
  minLabel,
  maxLabel,
  inputEndAdornment,
  allowZero = false,
}) => {
  const handleTextFieldChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const inputValue = e.target.value
    
    // 如果允许0且输入为空或0，直接设置为0
    if (allowZero && (inputValue === '' || inputValue === '0')) {
      onChange(0)
      return
    }
    
    const parsedValue = parseInt(inputValue)
    if (!isNaN(parsedValue)) {
      if (parsedValue >= min && parsedValue <= max) {
        onChange(parsedValue)
      }
    }
  }

  return (
    <div 
      className="flex items-center"
      style={{
        gap: 0,
      }}
    >
      <div 
        className="flex items-center flex-shrink-0"
        style={{ 
          width: 'clamp(1rem, 22vw, 10.5rem)',
          gap: 0,
        }}
      >
        <Tooltip title={label} arrow>
          <Typography 
            variant="subtitle2" 
            className="text-gray-700 truncate"
            sx={{
              fontSize: 'clamp(0.4rem, 1vw, 0.7rem)',
            }}
          >
            {label}
          </Typography>
        </Tooltip>
        <Tooltip title={tooltip}>
          <IconButton 
            size="small" 
            className="text-gray-400 hover:text-gray-600 p-0 flex-shrink-0"
            sx={{
              width: 'clamp(1rem, 2vw, 2rem)',
              height: 'clamp(1rem, 2vw, 2rem)',
            }}
          >
            <HelpCircle 
              style={{
                width: 'clamp(0.85rem, 1.5vw, 0.85rem)',
                height: 'clamp(0.85rem, 1.5vw, 0.85rem)',
              }}
            />
          </IconButton>
        </Tooltip>
      </div>
      <div 
        className="flex-1 flex items-center"
        style={{
          gap: 'clamp(0.125rem, 0.5vw, 0.25rem)',
          minWidth: 0,
        }}
      >
        <Typography 
          variant="caption" 
          className="text-gray-500 text-right flex-shrink-0" 
          sx={{ 
            width: 'clamp(0.75rem, 3vw, 1.5rem)',
            fontSize: 'clamp(0.5rem, 1.25vw, 0.65rem)',
          }}
        >
          {minLabel ?? min}
        </Typography>
        <Slider
          value={value}
          onChange={(_, newValue) => onChange(newValue as number)}
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          valueLabelDisplay="auto"
          valueLabelFormat={valueLabelFormat}
          sx={{
            flex: 1,
            minWidth: 0,
            '& .MuiSlider-valueLabel': {
              fontSize: 'clamp(0.625rem, 1.25vw, 0.7rem)',
            },
          }}
          className="bg-white/60 rounded"
          style={{
            padding: 'clamp(0.125rem, 0.5vw, 0.375rem)',
          }}
        />
        <Typography 
          variant="caption" 
          className="text-gray-500 text-left flex-shrink-0" 
          sx={{ 
            width: 'clamp(0.75rem, 3vw, 2rem)',
            fontSize: 'clamp(0.5rem, 1.25vw, 0.65rem)',
          }}
        >
          {maxLabel ?? max}
        </Typography>
      </div>
      <Box
        sx={{
          width: 'clamp(3.5rem, 12vw, 5rem)',
          flexShrink: 0,
          display: { xs: 'none', sm: 'block' },
        }}
      >
        <TextField
          size="small"
          type="number"
          value={value}
          onChange={handleTextFieldChange}
          inputProps={{
            min,
            max,
            step,
          }}
          disabled={disabled}
          className="bg-white/60"
          fullWidth
          sx={{
            fontSize: 'clamp(0.65rem, 1.5vw, 0.8rem)',
            '& .MuiOutlinedInput-root': {
              fontSize: 'clamp(0.65rem, 1.5vw, 0.8rem)',
              '& input': {
                padding: 'clamp(0.125rem, 0.5vw, 0.375rem)',
                textAlign: 'left',
              },
              '& fieldset': {
                borderColor: '#d1d5db',
              },
              '&:hover fieldset': {
                borderColor: '#9ca3af',
              },
              '&.Mui-focused fieldset': {
                borderColor: '#10b981',
              },
            },
            '& .MuiInputAdornment-root': {
              marginLeft: '0.125rem',
            },
          }}
          InputProps={inputEndAdornment ? {
            endAdornment: inputEndAdornment,
          } : undefined}
        />
      </Box>
    </div>
  )
}

