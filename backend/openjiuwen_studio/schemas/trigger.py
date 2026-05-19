from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from croniter import croniter
from pydantic import BaseModel, Field, field_validator


# ── Type-specific config sub-schemas ────────────────────────────────────────

class CronConfig(BaseModel):
    cron_expr: str = Field(..., description="POSIX cron expression, e.g. '0 9 * * 1'")

    @field_validator("cron_expr")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        if not croniter.is_valid(v):
            raise ValueError(f"Invalid cron expression: {v!r}")
        return v


class WebhookConfig(BaseModel):
    # None = accept all POST requests; non-None = validate X-Hub-Signature-256 header
    webhook_secret: Optional[str] = Field(None, max_length=512)


class PollingConfig(BaseModel):
    poll_url: str = Field(..., min_length=1, max_length=2048)
    poll_interval_seconds: int = Field(
        default=300,
        ge=60,       # minimum: 1 minute
        le=86400,    # maximum: 1 day
        description="How often to poll, in seconds"
    )


# ── Request schemas ──────────────────────────────────────────────────────────

class TriggerCreate(BaseModel):
    space_id: str
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    trigger_type: Literal["cron", "webhook", "polling"]
    target_type: Literal["agent", "workflow"]
    target_id: str = Field(..., min_length=1, max_length=100)
    target_version: str = Field(default="draft", max_length=100)
    input_payload: Optional[Dict[str, Any]] = None
    # Exactly one of these must match trigger_type — validated in the manager
    cron_config: Optional[CronConfig] = None
    webhook_config: Optional[WebhookConfig] = None
    polling_config: Optional[PollingConfig] = None


class TriggerGet(BaseModel):
    space_id: str
    trigger_id: str


class TriggerUpdate(BaseModel):
    space_id: str
    trigger_id: str
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    target_type: Optional[Literal["agent", "workflow"]] = None
    target_id: Optional[str] = Field(None, min_length=1, max_length=100)
    target_version: Optional[str] = Field(None, max_length=100)
    input_payload: Optional[Dict[str, Any]] = None
    cron_config: Optional[CronConfig] = None
    webhook_config: Optional[WebhookConfig] = None
    polling_config: Optional[PollingConfig] = None


class TriggerActivate(BaseModel):
    space_id: str
    trigger_id: str


class TriggerList(BaseModel):
    space_id: str
    trigger_type: Optional[str] = None      # filter by type
    target_type: Optional[str] = None       # filter by agent/workflow
    is_active: Optional[bool] = None        # filter by active status
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TriggerLogsFilter(BaseModel):
    space_id: str
    trigger_id: str
    status: Optional[str] = None            # filter: running|success|error|skipped
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TriggerLogDetail(BaseModel):
    space_id: str
    log_id: int


# ── Response schemas ─────────────────────────────────────────────────────────

class TriggerDetail(BaseModel):
    trigger_id: str
    space_id: str
    name: str
    description: Optional[str]
    trigger_type: str
    target_type: str
    target_id: str
    target_version: str
    input_payload: Optional[Dict[str, Any]]
    is_active: bool
    config: Optional[Dict[str, Any]]
    # Exposed to the trigger owner so they can build the inbound URL
    webhook_token: Optional[str]
    scheduler_job_id: Optional[str]
    create_time: Optional[int]
    update_time: Optional[int]


class TriggerListResponse(BaseModel):
    items: List[TriggerDetail]
    total: int
    page: int
    page_size: int


class TriggerExecutionLogRecord(BaseModel):
    id: int
    trigger_id: str
    trace_id: Optional[str]
    conversation_id: Optional[str]
    status: str
    fired_by: Optional[str]
    trigger_type: str
    started_at: Optional[int]
    finished_at: Optional[int]
    duration_ms: Optional[int]
    inputs_snapshot: Optional[Dict[str, Any]]
    outputs: Optional[Dict[str, Any]]
    error_message: Optional[str]
    poll_hash_seen: Optional[str]
    create_time: Optional[int]


class TriggerExecutionLogSummary(BaseModel):
    log_id: int
    status: str
    trace_id: Optional[str]
    started_at: Optional[int]


class TriggerLogsResponse(BaseModel):
    items: List[TriggerExecutionLogRecord]
    total: int
    page: int
    page_size: int
