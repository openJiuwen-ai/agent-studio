import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { TextField, Typography, IconButton, Tooltip, Alert } from '@mui/material'
import { Copy, Check } from 'lucide-react'
import { API_CONFIG } from '@test-agentstudio/api-client'

interface WebhookConfigFormProps {
  webhookToken: string | null
  webhookSecret: string
  onSecretChange: (value: string) => void
  disabled?: boolean
}

const WebhookConfigForm: React.FC<WebhookConfigFormProps> = ({
  webhookToken,
  webhookSecret,
  onSecretChange,
  disabled,
}) => {
  const { t } = useTranslation()
  const [copied, setCopied] = useState(false)

  const apiBase = API_CONFIG.BASE_URL
  const apiOrigin = apiBase.startsWith('http') ? new URL(apiBase).origin : window.location.origin
  const webhookUrl = webhookToken
    ? `${apiOrigin}/api/v1/triggers/inbound/${webhookToken}`
    : t('triggers.form.webhookUrlPending', 'URL available after saving')

  const handleCopy = async () => {
    if (!webhookToken) return

    // navigator.clipboard is only available in secure contexts (https / localhost).
    // Fall back to the legacy execCommand approach for plain-http environments.
    const legacyCopy = (text: string): boolean => {
      const ta = document.createElement('textarea')
      ta.value = text
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.focus()
      ta.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(ta)
      return ok
    }

    let success = false
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(webhookUrl)
        success = true
      } else {
        success = legacyCopy(webhookUrl)
      }
    } catch {
      success = legacyCopy(webhookUrl)
    }

    if (success) {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <Typography variant="subtitle2" className="mb-1">
          {t('triggers.form.webhookUrl', 'Inbound URL')}
        </Typography>
        <div className="flex items-center gap-2">
          <TextField
            fullWidth
            value={webhookUrl}
            disabled
            size="small"
            InputProps={{ readOnly: true }}
          />
          <Tooltip title={copied ? t('triggers.form.webhookCopied', 'Copied!') : t('triggers.form.webhookCopy', 'Copy URL')}>
            <span>
              <IconButton onClick={handleCopy} disabled={!webhookToken} size="small">
                {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
              </IconButton>
            </span>
          </Tooltip>
        </div>
        {!webhookToken && (
          <Alert severity="info" className="mt-2">
            {t('triggers.form.webhookUrlPendingHint', 'Save the trigger first to get the inbound URL.')}
          </Alert>
        )}
      </div>
      <TextField
        fullWidth
        label={t('triggers.form.webhookSecret', 'HMAC Secret (optional)')}
        value={webhookSecret}
        onChange={e => onSecretChange(e.target.value)}
        disabled={disabled}
        placeholder=""
        helperText={t('triggers.form.webhookSecretHint', 'Leave empty to accept all POST requests')}
        size="small"
        type="password"
      />
    </div>
  )
}

export default WebhookConfigForm
