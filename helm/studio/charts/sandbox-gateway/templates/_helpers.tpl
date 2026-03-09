{{- define "sandbox-gateway.name" -}}
{{ .Chart.Name }}
{{- end }}

{{- define "sandbox-gateway.fullname" -}}
{{ printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "sandbox-gateway.labels" -}}
app.kubernetes.io/name: {{ include "sandbox-gateway.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}
