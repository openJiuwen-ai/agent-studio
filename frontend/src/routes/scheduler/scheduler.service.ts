import { Injectable } from '@angular/core';
import { HttpService } from '@services/http.service';
import { ContextService } from '@services/context.service';
import { Observable } from 'rxjs';

export interface ScheduleConfig {
  type: 'cron' | 'rrule' | 'natural_language';
  config: any;
}

export interface RepeatConfig {
  type: 'once' | 'always';
}

export interface NotificationConfig {
  notify_on_success: boolean;
  notify_on_failure: boolean;
  channels: string[];
}

export interface ExecutorConfig {
  type: 'llm_prompt' | 'http_call' | 'agent_run' | 'workflow_run';
  config: any;
}

export interface ScheduledTask {
  id: string;
  tenant_id: string;
  workspace_id: string;
  creator_id: string;
  creator_name?: string;
  name: string;
  description: string;
  status: 'enabled' | 'disabled';
  schedule_type: string;
  schedule_config: any;
  schedule_description?: string;
  repeat_type: string;
  valid_from: string | null;
  valid_until: string | null;
  executor_type: string;
  executor_config: any;
  model_id: string | null;
  model_name?: string;
  prompt: string | null;
  skills: string[];
  connector_type: string | null;
  max_retries: number;
  notification: NotificationConfig;
  is_running: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_run_status: string | null;
  run_count: number;
  total_credits_used: number;
  created_at: string;
  updated_at: string;
  _triggering?: boolean;
  _toggling?: boolean;
}

export interface ExecutionLog {
  id: string;
  task_id: string;
  task_name: string;
  status: 'success' | 'failed' | 'running' | 'pending' | 'retrying';
  trigger_type: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  model_output: string | null;
  credits_used: number;
  retry_count: number;
  artifacts: any[];
}

export interface TaskListResponse {
  items: ScheduledTask[];
  total: number;
  page: number;
  page_size: number;
}

export interface ExecutionListResponse {
  items: ExecutionLog[];
  total: number;
  page: number;
  page_size: number;
}

@Injectable({ providedIn: 'root' })
export class SchedulerService {
  private get prefix() {
    return `${this.ctxServ.baseUrl}/agent-manager/scheduler`;
  }

  constructor(private http: HttpService, private ctxServ: ContextService) {}

  getWorkspaceId(): string {
    return this.http.getWorkspaceId();
  }

  listTasks(params: {
    page?: number;
    page_size?: number;
    workspace_id?: string;
    status?: string;
    search?: string;
  }): Observable<any> {
    return this.http.get({
      url: this.prefix,
      query: {
        page: String(params.page ?? 1),
        page_size: String(params.page_size ?? 20),
        ...(params.workspace_id ? { workspace_id: params.workspace_id } : {}),
        ...(params.status ? { status: params.status } : {}),
        ...(params.search ? { search: params.search } : {}),
      },
    });
  }

  getTask(taskId: string): Observable<any> {
    return this.http.get({
      url: `${this.prefix}/${taskId}`,
      query: {},
    });
  }

  createTask(payload: any): Observable<any> {
    return this.http.post({
      url: this.prefix,
      params: payload,
    });
  }

  updateTask(taskId: string, payload: any): Observable<any> {
    return this.http.put({
      url: `${this.prefix}/${taskId}`,
      params: payload,
    });
  }

  deleteTask(taskId: string): Observable<any> {
    return this.http.delete({
      url: `${this.prefix}/${taskId}`,
      query: {},
    });
  }

  enableTask(taskId: string): Observable<any> {
    return this.http.post({
      url: `${this.prefix}/${taskId}/enable`,
      params: {},
    });
  }

  disableTask(taskId: string): Observable<any> {
    return this.http.post({
      url: `${this.prefix}/${taskId}/disable`,
      params: {},
    });
  }

  triggerTask(taskId: string): Observable<any> {
    return this.http.post({
      url: `${this.prefix}/${taskId}/trigger`,
      params: {},
    });
  }

  listExecutions(taskId: string, params: {
    page?: number;
    page_size?: number;
    status?: string;
  }): Observable<any> {
    return this.http.get({
      url: `${this.prefix}/${taskId}/executions`,
      query: {
        page: String(params.page ?? 1),
        page_size: String(params.page_size ?? 10),
        ...(params.status ? { status: params.status } : {}),
      },
    });
  }

  previewSchedule(schedule: any): Observable<any> {
    return this.http.post({
      url: `${this.prefix}/preview`,
      params: schedule,
    });
  }

  getExecutorTypes(): Observable<any> {
    return this.http.get({
      url: `${this.prefix}/executor-types`,
      query: {},
    });
  }
}
