import { TextField, InputAdornment, IconButton, Tooltip, Button, Divider } from '@mui/material'
import type { ChatMessage } from './chatTypes'
import { useMemo, useState, useEffect, useRef } from 'react'
import { Type, Hash, List, Braces, ToggleLeft, Calendar, X, HelpCircle } from 'lucide-react'
import { useScopedTranslation } from '@/i18n'
import { MessageContent } from './NormalMessage'

type InteractionField = { input_name: string; description?: string; type?: string; required?: boolean; defaultValue?: string }

const typeIconFor = (t?: string) => {
  const s = String(t || '').toLowerCase()
  if (!s) return null
  if (s.includes('string')) return Type
  if (s.includes('integer')) return Hash
  if (s.includes('number')) return Hash
  if (s.includes('boolean')) return ToggleLeft
  if (s.includes('array')) return List
  if (s.includes('date') || s.includes('time')) return Calendar
  return Braces
}

const TypeBadge = ({ type }: { type?: string }) => {
  const Icon = typeIconFor(type)
  if (!type || !Icon) return null
  return (
    <Tooltip title={String(type)} placement="top" enterDelay={150}>
      <span className="inline-flex items-center justify-center text-gray-600 rounded px-2">
        <Icon className="w-3 h-3" />
      </span>
    </Tooltip>
  )
}

const normalizeField = (v: any): InteractionField => {
  if (v && typeof v === 'object') {
    const defaultValue = v.default ?? v.default_value ?? v.value ?? v.initial ?? v.defaultValue
    return {
      input_name: String(v.input_name || v.label || v.name || ''),
      description: v.description ? String(v.description) : undefined,
      type: v.type ? String(v.type) : undefined,
      required: Boolean(v.required),
      defaultValue: defaultValue != null ? String(defaultValue) : undefined,
    }
  }
  return { input_name: String(v) }
}

const parseInteractionMsg = (raw: any): InteractionField[] => {
  if (Array.isArray(raw)) return raw.map(normalizeField)
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed)) return parsed.map(normalizeField)
      return [{ input_name: raw }]
    } catch {
      return [{ input_name: raw }]
    }
  }
  return []
}

const canSubmitValues = (values: Record<string, string>, fields: InteractionField[]) => {
  const requiredFields = fields.filter(f => f.required)
  const requiredFilled = requiredFields.every(f => (values[f.input_name] || '').trim())
  const hasAny = Object.values(values).some(v => (v || '').trim())
  return requiredFields.length > 0 ? requiredFilled : hasAny
}

export function InteractionMessage({
  message,
  onSubmit,
  disabled,
  inputFocused,
}: {
  message: ChatMessage
  onSubmit?: (value: string, ts: number) => void
  disabled?: boolean
  inputFocused?: boolean
}) {
  const { t } = useScopedTranslation('agents.agentEditor.previewDebug.agentDebugChat.interactionMessage')
  const info = message.detailInfo
  const submitted = info?.submittedValue
  const fields: InteractionField[] = useMemo(() => parseInteractionMsg(info?.interaction_msg), [info])
  const [formValues, setFormValues] = useState<Record<string, string>>({})
  const isSubmitted = Boolean(submitted)
  const isExpired = Boolean(disabled && !isSubmitted)

  const safeParse = (s: string) => {
    try {
      return JSON.parse(s)
    } catch {
      return undefined
    }
  }

  const parsedSubmitted: Record<string, string> | undefined = useMemo(() => {
    const s = submitted
    if (!s) return undefined
    if (typeof s === 'string') {
      const obj = safeParse(s)
      if (obj && typeof obj === 'object') return obj as Record<string, string>
      const v = obj !== undefined ? String(obj) : String(s)
      return { input_value: v, input: v }
    }
    if (typeof s === 'object') return s as Record<string, string>
    return undefined
  }, [submitted])

  const lastTimestampRef = useRef<number | null>(null)
  useEffect(() => {
    if (lastTimestampRef.current !== message.timestamp) {
      lastTimestampRef.current = message.timestamp

      if (parsedSubmitted) return

      const defaults: Record<string, string> = {}
      fields.forEach(f => {
        if (f.defaultValue !== undefined) defaults[f.input_name] = f.defaultValue as string
      })
      setFormValues(defaults)
    }
  }, [message.timestamp, fields, parsedSubmitted])

  const handleChange = (key: string, v: string) => {
    setFormValues(prev => ({ ...prev, [key]: v }))
  }

  const getValue = (name: string) => {
    const a = parsedSubmitted?.[name]
    const c = formValues[name]
    return a ?? c ?? ''
  }

  const handleSubmit = () => {
    if (!onSubmit) return
    if (isExpired) return
    if (!canSubmitValues(formValues, fields)) return
    const payload = JSON.stringify(formValues)
    onSubmit(payload, message.timestamp)
  }

  return (
    <div className="w-full">
      {(message.content || (message.chunks && message.chunks.length > 0)) && (
        <div className="mb-2 text-gray-800 overflow-x-hidden w-fit max-w-full">
          <MessageContent message={message} />
        </div>
      )}
      <div className="w-full rounded-xl border border-gray-200 bg-white p-4 shadow-sm min-h-40">
        <div className="flex items-center justify-between mb-3">
          {isSubmitted ? (
            <span className={`px-2 py-0.5 rounded-full text-xs bg-green-50 text-green-700 border border-green-200`}>{t('submitted')}</span>
          ) : isExpired ? (
            <span className={`px-2 py-0.5 rounded-full text-xs bg-gray-50 text-gray-500 border border-gray-200`}>{t('expired')}</span>
          ) : (
            <span className={`px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-200`}>{t('fillAndSubmit')}</span>
          )}
        </div>
        <div className="space-y-4">
          {fields.length === 0 ? (
            <div className="space-y-2">
              <div className="w-full">
                {(() => {
                  const v = getValue('input')
                  return (
                    <TextField
                      value={v}
                      onChange={e => handleChange('input', e.target.value)}
                      placeholder={t('inputPlaceholder')}
                      size="small"
                      disabled={isSubmitted || isExpired}
                      fullWidth
                      autoComplete="off"
                      autoFocus={!isSubmitted && !isExpired && Boolean(inputFocused)}
                      inputProps={{ autoComplete: 'off', autoCorrect: 'off', autoCapitalize: 'none', spellCheck: false }}
                      InputProps={{
                        endAdornment:
                          !isSubmitted && !isExpired && String(v).length > 0 ? (
                            <InputAdornment position="end">
                              <IconButton aria-label={t('clearInputAria')} size="small" onClick={() => handleChange('input', '')} className="clear-btn">
                                <X className="w-4 h-4" />
                              </IconButton>
                            </InputAdornment>
                          ) : null,
                      }}
                      sx={{
                        '& .clear-btn': { opacity: 0, transition: 'opacity 0.15s' },
                        '& .MuiInputBase-root:hover .clear-btn': { opacity: 1 },
                      }}
                    />
                  )
                })()}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {fields.map((field, index) => (
                <div key={field.input_name} className="space-y-1">
                  <div className="text-sm text-gray-700 flex items-center gap-1">
                    {field.required ? <span className="text-red-500">*</span> : null}
                    <span>{field.input_name}</span>
                    {field.description && (
                      <Tooltip title={field.description} placement="top" arrow>
                        <HelpCircle className="w-3.5 h-3.5 text-gray-400" />
                      </Tooltip>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-full">
                      {(() => {
                        const v = getValue(field.input_name)
                        return (
                          <TextField
                            value={v}
                            onChange={e => handleChange(field.input_name, e.target.value)}
                            size="small"
                            disabled={isSubmitted || isExpired}
                            fullWidth
                            autoComplete="off"
                            autoFocus={!isSubmitted && !isExpired && index === 0 && Boolean(inputFocused)}
                            inputProps={{ autoComplete: 'off', autoCorrect: 'off', autoCapitalize: 'none', spellCheck: false }}
                            InputProps={{
                              endAdornment: (
                                <InputAdornment position="end">
                                  <div className="flex items-center gap-2">
                                    {!isSubmitted && !isExpired && String(v).length > 0 ? (
                                      <IconButton
                                        aria-label={t('clearInputAria')}
                                        size="small"
                                        onClick={() => handleChange(field.input_name, '')}
                                        className="clear-btn"
                                      >
                                        <X className="w-4 h-4" />
                                      </IconButton>
                                    ) : null}
                                    <Divider orientation="vertical" flexItem />
                                    <TypeBadge type={field.type} />
                                  </div>
                                </InputAdornment>
                              ),
                            }}
                            sx={{
                              '& .clear-btn': { opacity: 0, transition: 'opacity 0.15s' },
                              '& .MuiInputBase-root:hover .clear-btn': { opacity: 1 },
                            }}
                          />
                        )
                      })()}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {!isSubmitted ? (
            <div className="flex items-center justify-end">
                <Button variant="contained" color="primary" onClick={handleSubmit} disabled={isExpired || !canSubmitValues(formValues, fields)}>
                {t('submit')}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
