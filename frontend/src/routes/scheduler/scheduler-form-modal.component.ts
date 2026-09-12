import { Component, OnInit, OnDestroy, Inject, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators } from '@angular/forms';
import { NzModalModule, NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { Subject, takeUntil } from 'rxjs';
import { SchedulerService } from './scheduler.service';
import type { ScheduledTask } from './scheduler.service';
import { ScheduleRulePickerComponent, ScheduleValue } from './schedule-rule-picker.component';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { ModelManagementService } from '@services/repositories/model-management-new';

@Component({
  selector: 'app-scheduler-form-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    NzModalModule,
    NzFormModule,
    NzInputModule,
    NzSelectModule,
    NzSwitchModule,
    NzDatePickerModule,
    NzButtonModule,
    NzIconModule,
    NzToolTipModule,
    NzInputNumberModule,
    NzRadioModule,
    ScheduleRulePickerComponent,
  ],
  template: `
    <!-- 标题栏：左上角按钮 -->
    <div class="form-modal-header">
      <div class="header-left">
        <button *ngIf="viewMode === 'form' && !editTask"
          nz-button nzType="default" nzSize="small"
          (click)="switchToConversation()">
          <nz-icon nzType="message"></nz-icon>
          新建定时会话
        </button>
        <span class="form-modal-title" *ngIf="viewMode === 'form'">{{ editTask ? '编辑自动化' : '新建自动化' }}</span>
        <span class="form-modal-title" *ngIf="viewMode === 'conversation'">
          <nz-icon nzType="message" style="margin-right: 6px; color: #1890ff;"></nz-icon>
          定时会话任务
        </span>
      </div>
      <div class="header-right" *ngIf="viewMode === 'conversation'">
        <button nz-button nzType="link" nzSize="small" (click)="switchToForm()">
          <nz-icon nzType="form"></nz-icon>
          高级模式
        </button>
      </div>
    </div>

    <!-- ==================== 会话模式 ==================== -->
    <div *ngIf="viewMode === 'conversation'" class="conversation-view">
      <div class="conversation-body">
        <!-- 任务名称 -->
        <div class="conv-field">
          <label class="conv-label">任务名称 <span class="required">*</span></label>
          <input nz-input [(ngModel)]="convName" placeholder="给这个定时任务起个名字" maxlength="100" />
        </div>

        <!-- 模型选择 -->
        <div class="conv-field">
          <label class="conv-label">执行模型</label>
          <nz-select [(ngModel)]="convModelId" style="width: 100%;" placeholder="选择模型（选填）" nzShowSearch>
            <nz-option *ngFor="let m of modelOptions" [nzValue]="m.id" [nzLabel]="m.name"></nz-option>
          </nz-select>
        </div>

        <!-- 对话区域 -->
        <div class="conv-chat-area">
          <div class="conv-chat-label">执行内容</div>
          <div class="conv-chat-box">
            <div class="conv-chat-role">用户</div>
            <textarea
              nz-input
              [(ngModel)]="convPrompt"
              [nzAutosize]="{ minRows: 6, maxRows: 16 }"
              placeholder="输入你想让 AI 在指定时间执行的内容...&#10;&#10;例如：每天早上 9 点发送一份系统状态报告&#10;例如：每周一总结上周的工作进展"
            ></textarea>
          </div>
          <div class="conv-chat-box conv-chat-response" *ngIf="convPrompt">
            <div class="conv-chat-role">AI 将执行</div>
            <div class="conv-chat-preview">{{ convPrompt }}</div>
          </div>
        </div>

        <!-- 调度配置 -->
        <div class="conv-field">
          <label class="conv-label">执行计划 <span class="required">*</span></label>
          <nz-radio-group [(ngModel)]="convScheduleType" class="conv-radio-group">
            <label nz-radio [nzValue]="'once'">一次性</label>
            <label nz-radio [nzValue]="'recurring'">周期重复</label>
          </nz-radio-group>
        </div>

        <!-- 一次性：选时间 -->
        <div class="conv-field" *ngIf="convScheduleType === 'once'">
          <label class="conv-label">执行时间 <span class="required">*</span></label>
          <nz-date-picker
            [(ngModel)]="convOnceTime"
            nzShowTime
            nzFormat="yyyy-MM-dd HH:mm"
            style="width: 100%;"
            placeholder="选择执行时间"
          ></nz-date-picker>
        </div>

        <!-- 周期重复：调度规则 -->
        <div class="conv-field" *ngIf="convScheduleType === 'recurring'">
          <label class="conv-label">调度规则 <span class="required">*</span></label>
          <nz-select [(ngModel)]="convCronPreset" style="width: 100%;" placeholder="选择频率">
            <nz-option nzValue="hourly" nzLabel="每小时"></nz-option>
            <nz-option nzValue="daily_09" nzLabel="每天 9:00"></nz-option>
            <nz-option nzValue="daily_18" nzLabel="每天 18:00"></nz-option>
            <nz-option nzValue="workdays_09" nzLabel="工作日 9:00"></nz-option>
            <nz-option nzValue="weekly_mon_09" nzLabel="每周一 9:00"></nz-option>
            <nz-option nzValue="monthly_1_09" nzLabel="每月 1 号 9:00"></nz-option>
            <nz-option nzValue="custom" nzLabel="自定义..."></nz-option>
          </nz-select>
          <div *ngIf="convCronPreset === 'custom'" style="margin-top: 8px;">
            <input nz-input [(ngModel)]="convCronCustom" placeholder="输入 cron 表达式，如: 0 9 * * 1-5" />
          </div>
        </div>
      </div>

      <!-- 底部按钮 -->
      <div class="form-modal-footer">
        <button nz-button (click)="onCancel()">取消</button>
        <button nz-button nzType="primary" [nzLoading]="saving" (click)="onConversationSubmit()">
          <nz-icon nzType="schedule"></nz-icon>
          创建定时任务
        </button>
      </div>
    </div>

    <!-- ==================== 表单模式（原版） ==================== -->
    <div *ngIf="viewMode === 'form'" class="form-modal-body">
      <form nz-form [formGroup]="form" nzLayout="vertical">
          <!-- 任务名称 -->
          <nz-form-item>
            <nz-form-label nzRequired>任务名称</nz-form-label>
            <nz-form-control nzErrorTip="请输入任务名称">
              <input nz-input formControlName="name" placeholder="请输入任务名称" maxlength="100" />
            </nz-form-control>
          </nz-form-item>

          <!-- 任务描述 -->
          <nz-form-item>
            <nz-form-label>任务描述</nz-form-label>
            <nz-form-control>
              <textarea nz-input formControlName="description" placeholder="任务描述（选填）"
                [nzAutosize]="{ minRows: 2, maxRows: 4 }"></textarea>
            </nz-form-control>
          </nz-form-item>

          <!-- 调度配置 -->
          <nz-form-item>
            <nz-form-label nzRequired>调度类型</nz-form-label>
            <nz-form-control>
              <nz-radio-group formControlName="scheduleType" (ngModelChange)="onScheduleTypeChange()">
                <label nz-radio [nzValue]="'once'">一次性任务</label>
                <label nz-radio [nzValue]="'recurring'">周期重复任务</label>
              </nz-radio-group>
            </nz-form-control>
          </nz-form-item>

          <!-- 一次性任务：选时间点 -->
          <nz-form-item *ngIf="form.get('scheduleType')?.value === 'once'">
            <nz-form-label nzRequired>执行时间</nz-form-label>
            <nz-form-control>
              <nz-date-picker
                formControlName="onceTime"
                nzShowTime
                nzFormat="yyyy-MM-dd HH:mm"
                style="width: 100%;"
                placeholder="选择执行时间"
              ></nz-date-picker>
            </nz-form-control>
          </nz-form-item>

          <!-- 周期重复任务：调度规则选择器 -->
          <nz-form-item *ngIf="form.get('scheduleType')?.value === 'recurring'">
            <nz-form-label nzRequired>调度规则</nz-form-label>
            <nz-form-control>
              <app-schedule-rule-picker formControlName="scheduleRule"></app-schedule-rule-picker>
            </nz-form-control>
          </nz-form-item>

          <!-- 生效时间范围 -->
          <nz-form-item>
            <nz-form-label>生效时间范围</nz-form-label>
            <nz-form-control>
              <div class="time-range-row">
                <nz-date-picker
                  formControlName="validFrom"
                  nzShowTime
                  nzFormat="yyyy-MM-dd HH:mm"
                  style="width: calc(50% - 12px);"
                  placeholder="开始时间（选填）"
                ></nz-date-picker>
                <span class="time-range-sep">至</span>
                <nz-date-picker
                  formControlName="validUntil"
                  nzShowTime
                  nzFormat="yyyy-MM-dd HH:mm"
                  style="width: calc(50% - 12px);"
                  placeholder="截止时间（选填）"
                ></nz-date-picker>
              </div>
            </nz-form-control>
          </nz-form-item>

          <!-- 执行配置 -->
          <nz-form-item>
            <nz-form-label nzRequired>执行方式</nz-form-label>
            <nz-form-control>
              <nz-select formControlName="executorType" style="width: 100%;" placeholder="选择执行方式">
                <nz-option nzValue="llm_prompt" nzLabel="大模型调用"></nz-option>
                <nz-option nzValue="agent_run" nzLabel="运行智能体"></nz-option>
                <nz-option nzValue="workflow_run" nzLabel="运行工作流"></nz-option>
                <nz-option nzValue="http_call" nzLabel="HTTP 请求"></nz-option>
              </nz-select>
            </nz-form-control>
          </nz-form-item>

          <!-- 选择智能体/工作流 -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'agent_run'">
            <nz-form-label nzRequired>选择智能体</nz-form-label>
            <nz-form-control>
              <nz-select
                formControlName="agentId"
                style="width: 100%;"
                placeholder="选择智能体"
                nzShowSearch
                [nzOptions]="agentOptions"
                (nzOnSearch)="searchAgents($event)"
              ></nz-select>
            </nz-form-control>
          </nz-form-item>

          <!-- 智能体入参（query） -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'agent_run' && form.get('agentId')?.value">
            <nz-form-label nzRequired>入参配置</nz-form-label>
            <nz-form-control nzErrorTip="请输入智能体的运行入参">
              <textarea
                nz-input
                formControlName="prompt"
                [nzAutosize]="{ minRows: 3, maxRows: 8 }"
                placeholder="输入定时执行时传给智能体的 query，例如：生成今日系统状态报告"
              ></textarea>
            </nz-form-control>
          </nz-form-item>

          <nz-form-item *ngIf="form.get('executorType')?.value === 'workflow_run'">
            <nz-form-label nzRequired>选择工作流</nz-form-label>
            <nz-form-control>
              <nz-select
                formControlName="workflowId"
                style="width: 100%;"
                placeholder="选择工作流"
                nzShowSearch
                [nzOptions]="workflowOptions"
                (nzOnSearch)="searchWorkflows($event)"
                (ngModelChange)="onWorkflowSelect($event)"
              ></nz-select>
            </nz-form-control>
          </nz-form-item>

          <!-- 工作流入参（根据开始节点动态渲染） -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'workflow_run' && workflowInputParams.length > 0">
            <nz-form-label nzRequired>入参配置</nz-form-label>
            <nz-form-control>
              <div class="wf-input-row" *ngFor="let p of workflowInputParams">
                <span class="wf-input-label" [title]="p.description || p.name">
                  {{ p.name }}<span class="required" *ngIf="p.required"> *</span>
                  <span class="wf-input-type">{{ p.type }}</span>
                </span>
                <input
                  nz-input
                  [(ngModel)]="workflowInputs[p.name]"
                  [ngModelOptions]="{ standalone: true }"
                  [placeholder]="p.description || ('请输入 ' + p.name)"
                />
              </div>
            </nz-form-control>
          </nz-form-item>

          <!-- HTTP 请求配置 -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'http_call'">
            <nz-form-label nzRequired>请求 URL</nz-form-label>
            <nz-form-control>
              <input nz-input formControlName="httpUrl" placeholder="https://example.com/api" />
            </nz-form-control>
          </nz-form-item>

          <!-- 模型选择 -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'llm_prompt' || form.get('executorType')?.value === 'agent_run'">
            <nz-form-label>模型选择</nz-form-label>
            <nz-form-control>
              <nz-select formControlName="modelId" style="width: 100%;" placeholder="选择模型（选填）" nzShowSearch>
                <nz-option *ngFor="let m of modelOptions" [nzValue]="m.id" [nzLabel]="m.name"></nz-option>
              </nz-select>
            </nz-form-control>
          </nz-form-item>

          <!-- Prompt 输入 -->
          <nz-form-item *ngIf="form.get('executorType')?.value === 'llm_prompt'">
            <nz-form-label nzRequired>Prompt</nz-form-label>
            <nz-form-control>
              <textarea
                nz-input
                formControlName="prompt"
                [nzAutosize]="{ minRows: 4, maxRows: 12 }"
                placeholder="输入定时执行的提示词"
              ></textarea>
            </nz-form-control>
          </nz-form-item>

          <!-- 通知配置 -->
          <nz-form-item>
            <nz-form-label>通知配置</nz-form-label>
            <nz-form-control>
              <div class="notify-row">
                <label class="notify-item">
                  <nz-switch formControlName="notifyOnSuccess" nzSize="small"></nz-switch>
                  <span>任务成功通知</span>
                </label>
                <label class="notify-item">
                  <nz-switch formControlName="notifyOnFailure" nzSize="small"></nz-switch>
                  <span>任务失败通知</span>
                </label>
              </div>
            </nz-form-control>
          </nz-form-item>

          <!-- 重试次数 -->
          <nz-form-item>
            <nz-form-label>失败重试次数</nz-form-label>
            <nz-form-control>
              <nz-input-number formControlName="maxRetries" [nzMin]="0" [nzMax]="10" [nzStep]="1" style="width: 120px;"></nz-input-number>
            </nz-form-control>
          </nz-form-item>
        </form>
      </div>
      <div class="form-modal-footer">
        <button nz-button (click)="onCancel()">取消</button>
        <button nz-button nzType="primary" [nzLoading]="saving" (click)="onSubmit()">保存</button>
      </div>
  `,
  styles: [`
    .form-modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .form-modal-title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
    }
    .form-modal-body {
      max-height: 60vh;
      overflow-y: auto;
      padding: 8px 0;
    }
    .form-modal-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 20px;
      padding-top: 12px;
      border-top: 1px solid #f0f0f0;
    }
    .time-range-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .time-range-sep {
      color: #999;
      font-size: 13px;
    }
    .notify-row {
      display: flex;
      gap: 24px;
    }
    .notify-item {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
    }
    .notify-item span {
      font-size: 13px;
      color: #333;
    }
    .wf-input-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
    }
    .wf-input-label {
      flex: 0 0 160px;
      font-size: 13px;
      color: #333;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .wf-input-label .required {
      color: #ff4d4f;
    }
    .wf-input-type {
      margin-left: 4px;
      font-size: 12px;
      color: #999;
    }
    /* ===== 会话模式样式 ===== */
    .conversation-view {
      display: flex;
      flex-direction: column;
      height: 100%;
    }
    .conversation-body {
      max-height: 55vh;
      overflow-y: auto;
      padding: 0;
    }
    .conv-field {
      margin-bottom: 16px;
    }
    .conv-label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: #333;
      margin-bottom: 6px;
    }
    .conv-label .required {
      color: #ff4d4f;
    }
    .conv-radio-group {
      display: flex;
      gap: 16px;
    }
    .conv-chat-area {
      margin-bottom: 16px;
    }
    .conv-chat-label {
      font-size: 13px;
      font-weight: 500;
      color: #333;
      margin-bottom: 6px;
    }
    .conv-chat-box {
      border: 1px solid #e8e8e8;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 8px;
      background: #fff;
    }
    .conv-chat-response {
      background: #f6ffed;
      border-color: #b7eb8f;
    }
    .conv-chat-role {
      font-size: 12px;
      font-weight: 600;
      color: #1890ff;
      margin-bottom: 6px;
    }
    .conv-chat-response .conv-chat-role {
      color: #52c41a;
    }
    .conv-chat-preview {
      font-size: 13px;
      color: #333;
      white-space: pre-wrap;
      line-height: 1.6;
      max-height: 200px;
      overflow-y: auto;
    }
  `],
})
export class SchedulerFormModalComponent implements OnInit, OnDestroy {
  get editTask(): ScheduledTask | null {
    return this.modalData?.editTask ?? null;
  }

  viewMode: 'form' | 'conversation' = 'form';

  form!: FormGroup;
  saving = false;
  agentOptions: any[] = [];
  workflowOptions: any[] = [];
  modelOptions: any[] = [];

  // 工作流入参：所选工作流开始节点的参数定义及用户填写的值
  workflowInputParams: any[] = [];
  workflowInputs: Record<string, any> = {};

  // 会话模式字段
  convName = '';
  convModelId: string | null = null;
  convPrompt = '';
  convScheduleType = 'once';
  convOnceTime: Date | null = null;
  convCronPreset = 'daily_09';
  convCronCustom = '';

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private modal: NzModalRef,
    private message: NzMessageService,
    private schedulerService: SchedulerService,
    private appAgentRepo: AppAgentRepoService,
    private appFlowRepo: AppFlowRepoService,
    private modelManagementService: ModelManagementService,
    @Inject(NZ_MODAL_DATA) private modalData: any,
  ) {}

  ngOnInit(): void {
    this.initForm();
    this.loadModels();
    this.loadAgents();
    this.loadWorkflows();
    if (this.editTask) {
      this.populateForm();
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  switchToConversation(): void {
    this.viewMode = 'conversation';
  }

  switchToForm(): void {
    this.viewMode = 'form';
  }

  onConversationSubmit(): void {
    if (!this.convName.trim()) {
      this.message.warning('请输入任务名称');
      return;
    }
    if (!this.convPrompt.trim()) {
      this.message.warning('请输入执行内容');
      return;
    }

    let scheduleConfig: any;
    let scheduleType: string;
    let repeatType: string;

    if (this.convScheduleType === 'once') {
      if (!this.convOnceTime) {
        this.message.warning('请选择执行时间');
        return;
      }
      scheduleType = 'cron';
      repeatType = 'once';
      const d = new Date(this.convOnceTime);
      scheduleConfig = {
        type: 'cron',
        config: {
          expression: `${d.getMinutes()} ${d.getHours()} ${d.getDate()} ${d.getMonth() + 1} *`,
          run_at: this.convOnceTime.toISOString(),
        },
      };
    } else {
      const cronExpr = this.resolveCronPreset();
      if (!cronExpr) {
        this.message.warning('请选择调度规则');
        return;
      }
      scheduleType = 'cron';
      repeatType = 'always';
      scheduleConfig = { type: 'cron', config: { expression: cronExpr } };
    }

    const payload: any = {
      name: this.convName.trim(),
      description: '',
      workspace_id: this.schedulerService.getWorkspaceId(),
      schedule: scheduleConfig,
      repeat: { type: repeatType },
      valid_from: null,
      valid_until: null,
      executor: { type: 'llm_prompt', config: {} },
      model_id: this.convModelId || null,
      prompt: this.convPrompt.trim(),
      notification: { notify_on_success: true, notify_on_failure: true, channels: ['in_app'] },
      max_retries: 3,
    };

    this.saving = true;
    this.schedulerService.createTask(payload).pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.message.success('定时会话任务创建成功');
        this.modal.close(true);
      },
      error: () => {
        this.message.error('创建失败');
        this.saving = false;
      },
    });
  }

  private resolveCronPreset(): string | null {
    switch (this.convCronPreset) {
      case 'hourly': return '0 * * * *';
      case 'daily_09': return '0 9 * * *';
      case 'daily_18': return '0 18 * * *';
      case 'workdays_09': return '0 9 * * 1-5';
      case 'weekly_mon_09': return '0 9 * * 1';
      case 'monthly_1_09': return '0 9 1 * *';
      case 'custom': return this.convCronCustom.trim() || null;
      default: return '0 9 * * *';
    }
  }

  private initForm(): void {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(100)]],
      description: [''],
      scheduleType: ['recurring', [Validators.required]],
      onceTime: [null],
      scheduleRule: [null],
      validFrom: [null],
      validUntil: [null],
      executorType: ['llm_prompt', [Validators.required]],
      agentId: [null],
      workflowId: [null],
      httpUrl: [''],
      modelId: [null],
      prompt: [''],
      notifyOnSuccess: [false],
      notifyOnFailure: [true],
      maxRetries: [3],
    });
  }

  private populateForm(): void {
    if (!this.editTask) return;
    const t = this.editTask;

    this.form.patchValue({
      name: t.name,
      description: t.description || '',
      scheduleType: t.repeat_type === 'once' ? 'once' : 'recurring',
      executorType: t.executor_type || 'llm_prompt',
      agentId: t.executor_config?.agent_id || null,
      workflowId: t.executor_config?.workflow_id || null,
      httpUrl: t.executor_config?.url || '',
      modelId: t.model_id || null,
      prompt: t.prompt || t.executor_config?.query || '',
      notifyOnSuccess: t.notification?.notify_on_success ?? false,
      notifyOnFailure: t.notification?.notify_on_failure ?? true,
      maxRetries: t.max_retries ?? 3,
      validFrom: t.valid_from ? new Date(t.valid_from) : null,
      validUntil: t.valid_until ? new Date(t.valid_until) : null,
    });

    // 编辑工作流任务时，加载所选工作流的入参定义并回填已保存的值
    if (t.executor_type === 'workflow_run' && t.executor_config?.workflow_id) {
      this.onWorkflowSelect(t.executor_config.workflow_id, t.executor_config?.inputs || {});
    }

    if (t.repeat_type === 'once') {
      this.form.patchValue({ onceTime: t.schedule_config?.run_at ? new Date(t.schedule_config.run_at) : null });
    } else {
      let scheduleValue: ScheduleValue;
      if (t.schedule_type === 'cron') {
        scheduleValue = { type: 'cron', cronExpression: t.schedule_config?.expression || '' };
      } else if (t.schedule_type === 'natural_language') {
        scheduleValue = { type: 'natural_language', naturalLanguageText: t.schedule_config?.text || '' };
      } else {
        scheduleValue = { type: 'cron', cronExpression: t.schedule_config?.expression || '' };
      }
      this.form.patchValue({ scheduleRule: scheduleValue });
    }
  }

  onScheduleTypeChange(): void {}

  onCancel(): void {
    this.modal.close();
  }

  onSubmit(): void {
    if (this.form.invalid) {
      Object.values(this.form.controls).forEach(c => c.markAsDirty());
      const invalidFields = Object.keys(this.form.controls)
        .filter(key => this.form.controls[key].invalid)
        .join('、');
      this.message.warning(`表单校验未通过，请检查: ${invalidFields || '必填项'}`);
      return;
    }
    const val = this.form.value;

    let scheduleConfig: any;
    let scheduleType: string;
    let repeatType: string;

    if (val.scheduleType === 'once') {
      if (!val.onceTime) {
        this.message.warning('请选择执行时间');
        return;
      }
      scheduleType = 'cron';
      repeatType = 'once';
      const d = new Date(val.onceTime);
      scheduleConfig = {
        type: 'cron',
        config: {
          expression: `${d.getMinutes()} ${d.getHours()} ${d.getDate()} ${d.getMonth() + 1} *`,
          run_at: val.onceTime.toISOString(),
        },
      };
    } else {
      const rule: ScheduleValue = val.scheduleRule;
      if (!rule) {
        this.message.warning('请配置调度规则');
        return;
      }
      repeatType = 'always';
      if (rule.type === 'cron') {
        scheduleType = 'cron';
        scheduleConfig = { type: 'cron', config: { expression: rule.cronExpression } };
      } else if (rule.type === 'natural_language') {
        scheduleType = 'natural_language';
        scheduleConfig = { type: 'natural_language', config: { text: rule.naturalLanguageText } };
      } else {
        scheduleType = 'cron';
        const expr = this.visualToCron(rule.visual!);
        scheduleConfig = { type: 'cron', config: { expression: expr } };
      }
    }

    if (val.executorType === 'agent_run' && !val.agentId) {
      this.message.warning('请选择智能体');
      return;
    }
    if (val.executorType === 'agent_run' && !(val.prompt || '').trim()) {
      this.message.warning('请配置智能体的运行入参');
      return;
    }
    if (val.executorType === 'workflow_run' && !val.workflowId) {
      this.message.warning('请选择工作流');
      return;
    }
    if (val.executorType === 'workflow_run') {
      const missingRequired = this.workflowInputParams.some(
        (p: any) => p.required && !String(this.workflowInputs[p.name] ?? '').trim(),
      );
      if (missingRequired) {
        this.message.warning('请填写工作流的必填入参');
        return;
      }
    }

    const executorConfig: any = { type: val.executorType };
    if (val.executorType === 'agent_run') {
      executorConfig.config = { agent_id: val.agentId, query: (val.prompt || '').trim() };
    } else if (val.executorType === 'workflow_run') {
      executorConfig.config = { workflow_id: val.workflowId, inputs: { ...this.workflowInputs } };
    } else if (val.executorType === 'http_call') executorConfig.config = { url: val.httpUrl };
    else if (val.executorType === 'llm_prompt') executorConfig.config = {};

    const payload: any = {
      name: val.name,
      description: val.description || '',
      workspace_id: this.schedulerService.getWorkspaceId(),
      schedule: scheduleConfig,
      repeat: { type: repeatType },
      valid_from: val.validFrom ? val.validFrom.toISOString() : null,
      valid_until: val.validUntil ? val.validUntil.toISOString() : null,
      executor: executorConfig,
      model_id: val.modelId || null,
      prompt: val.prompt || null,
      notification: {
        notify_on_success: val.notifyOnSuccess,
        notify_on_failure: val.notifyOnFailure,
        channels: ['in_app'],
      },
      max_retries: val.maxRetries,
    };

    this.saving = true;
    const req$ = this.editTask
      ? this.schedulerService.updateTask(this.editTask.id, payload)
      : this.schedulerService.createTask(payload);

    req$.pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.message.success(this.editTask ? '任务更新成功' : '任务创建成功');
        this.modal.close(true);
      },
      error: () => {
        this.message.error(this.editTask ? '更新失败' : '创建失败');
        this.saving = false;
      },
    });
  }

  private visualToCron(v: any): string {
    const h = v.hour ?? 9;
    const m = v.minute ?? 0;
    switch (v.frequency) {
      case 'hourly': return `${m} * * * *`;
      case 'daily': return `${m} ${h} * * *`;
      case 'workdays': return `${m} ${h} * * 1-5`;
      case 'weekly': {
        const days = (v.weekdays || []).join(',');
        return `${m} ${h} * * ${days || '1'}`;
      }
      case 'monthly': {
        if (v.monthDayType === 'last') return `${m} ${h} L * *`;
        return `${m} ${h} ${v.monthDay || 1} * *`;
      }
      default: return `${m} ${h} * * *`;
    }
  }

  searchAgents(keyword: string): void {
    const params: any = {};
    if (keyword) params.name = keyword;
    this.appAgentRepo.getAgentList(params, 0, 50).then((res: any) => {
      this.agentOptions = (res?.agent_list || []).map((a: any) => ({
        // 后端返回的字段是 agent_id（不是 id），否则所有选项 value 都是 undefined，无法逐个选择
        value: a.agent_id,
        label: a.name,
      }));
    }).catch(() => {});
  }

  searchWorkflows(keyword: string): void {
    const params: any = {};
    if (keyword) params.name = keyword;
    this.appAgentRepo.getWorkflowList(params, 0, 50).then((res: any) => {
      this.workflowOptions = (res?.workflow_list || []).map((w: any) => ({
        value: w.workflow_id,
        label: w.name,
      }));
    }).catch(() => {});
  }

  loadAgents(): void { this.searchAgents(''); }
  loadWorkflows(): void { this.searchWorkflows(''); }

  /** 系统内置参数名，不作为用户入参渲染 */
  private static readonly WORKFLOW_INPUT_FILTER_KEYS = ['sys', 'conversation_history', 'env'];

  /**
   * 选择工作流后，拉取工作流详情并解析开始节点的输出参数，作为需要配置的入参。
   * @param workflowId 工作流 id
   * @param preservedInputs 编辑场景下已保存的入参值，用于回填
   */
  onWorkflowSelect(workflowId: string, preservedInputs?: Record<string, any>): void {
    this.workflowInputParams = [];
    this.workflowInputs = {};
    if (!workflowId) {
      return;
    }
    this.appFlowRepo.getFlow(workflowId).then((wf: any) => {
      const nodes = wf?.workflow_details?.nodes || wf?.details?.nodes || [];
      const startNode = nodes.find((n: any) => n.type === 'Start');
      const outputs = Array.isArray(startNode?.outputs) ? startNode.outputs : [];
      this.workflowInputParams = outputs.filter(
        (p: any) => p?.name && !SchedulerFormModalComponent.WORKFLOW_INPUT_FILTER_KEYS.includes(p.name),
      );
      this.workflowInputParams.forEach((p: any) => {
        this.workflowInputs[p.name] = preservedInputs?.[p.name] ?? '';
      });
    }).catch(() => {
      this.message.error('获取工作流入参失败');
    });
  }

  loadModels(): void {
    this.modelManagementService
      .getAvailableModelList({
        groupby: 'provider',
        publish_status: 'online',
        model_type: 'LLM,IMAGE-TO-TEXT',
        with_router: false,
      })
      .then((res: any) => {
        const options: any[] = [];
        (res?.data ?? []).forEach((provider: any) => {
          (provider.models ?? []).forEach((model: any) => {
            options.push({
              id: model.id,
              name: model.model_name,
            });
          });
        });
        this.modelOptions = options;
      })
      .catch(() => {});
  }
}
