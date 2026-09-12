import { Component, OnInit, OnDestroy, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDescriptionsModule } from 'ng-zorro-antd/descriptions';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { Subject, takeUntil } from 'rxjs';
import { SchedulerService, ExecutionLog } from './scheduler.service';

@Component({
  selector: 'app-scheduler-logs-modal',
  standalone: true,
  imports: [
    CommonModule,
    NzTableModule,
    NzTagModule,
    NzButtonModule,
    NzIconModule,
    NzEmptyModule,
    NzSpinModule,
    NzToolTipModule,
    NzDescriptionsModule,
    NzDividerModule,
  ],
  template: `
    <div class="logs-container">
      <nz-table
        #logTable
        [nzData]="logs"
        [nzLoading]="loading"
        [nzPageSize]="pageSize"
        [(nzPageIndex)]="currentPage"
        [nzTotal]="total"
        nzShowPagination
        (nzPageIndexChange)="loadLogs()"
        [nzFrontPagination]="false"
        [nzSize]="'small'"
      >
          <thead>
            <tr>
              <th>执行时间</th>
              <th>状态</th>
              <th>触发方式</th>
              <th>耗时</th>
              <th>消耗</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <ng-container *ngFor="let log of logTable.data">
              <tr>
                <td>{{ log.started_at | date:'yyyy-MM-dd HH:mm:ss' }}</td>
                <td>
                  <nz-tag [nzColor]="getLogStatusColor(log.status)">{{ getLogStatusLabel(log.status) }}</nz-tag>
                </td>
                <td>{{ getTriggerLabel(log.trigger_type) }}</td>
                <td>{{ log.duration_ms ? (log.duration_ms / 1000 | number:'1.1-1') + 's' : '-' }}</td>
                <td>{{ log.credits_used || 0 }}</td>
                <td>
                  <button nz-button nzType="link" nzSize="small" (click)="toggleDetail(log)">
                    <nz-icon [nzType]="expandedId === log.id ? 'up' : 'down'"></nz-icon>
                    {{ expandedId === log.id ? '收起' : '详情' }}
                  </button>
                </td>
              </tr>
              <!-- 展开详情 -->
              <tr *ngIf="expandedId === log.id">
                <td colspan="6" class="log-detail-cell">
                  <nz-descriptions nzBordered [nzColumn]="2" nzSize="small">
                    <nz-descriptions-item nzTitle="执行ID">{{ log.id }}</nz-descriptions-item>
                    <nz-descriptions-item nzTitle="任务ID">{{ log.task_id }}</nz-descriptions-item>
                    <nz-descriptions-item nzTitle="开始时间">{{ log.started_at | date:'yyyy-MM-dd HH:mm:ss' }}</nz-descriptions-item>
                    <nz-descriptions-item nzTitle="结束时间">{{ log.finished_at ? (log.finished_at | date:'yyyy-MM-dd HH:mm:ss') : '执行中...' }}</nz-descriptions-item>
                    <nz-descriptions-item nzTitle="重试次数">{{ log.retry_count }}</nz-descriptions-item>
                    <nz-descriptions-item nzTitle="消耗积分">{{ log.credits_used }}</nz-descriptions-item>
                  </nz-descriptions>

                  <div *ngIf="log.error_message" class="log-section">
                    <div class="log-section-title">
                      <nz-icon nzType="close-circle" style="color: #ff4d4f;"></nz-icon>
                      错误信息
                    </div>
                    <pre class="error-output">{{ log.error_message }}</pre>
                  </div>

                  <div *ngIf="log.model_output" class="log-section">
                    <div class="log-section-title">
                      <nz-icon nzType="file-text" style="color: #1f42ce;"></nz-icon>
                      模型输出
                    </div>
                    <pre class="model-output">{{ log.model_output }}</pre>
                  </div>

                  <div *ngIf="log.artifacts?.length" class="log-section">
                    <div class="log-section-title">
                      <nz-icon nzType="paper-clip"></nz-icon>
                      附件列表
                    </div>
                    <div class="artifact-list">
                      <div *ngFor="let art of log.artifacts" class="artifact-item">
                        <nz-icon nzType="file"></nz-icon>
                        <span>{{ art.name || '附件' }}</span>
                      </div>
                    </div>
                  </div>
                </td>
              </tr>
            </ng-container>
          </tbody>
        </nz-table>

        <nz-empty *ngIf="!loading && logs.length === 0" nzNotFoundContent="暂无执行日志"></nz-empty>
      </div>
  `,
  styles: [`
    .logs-container {
      min-height: 300px;
      max-height: 60vh;
      overflow-y: auto;
    }
    .log-detail-cell {
      background: #fafafa;
      padding: 16px !important;
    }
    .log-section {
      margin-top: 12px;
    }
    .log-section-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 500;
      color: #333;
      margin-bottom: 6px;
    }
    .error-output, .model-output {
      background: #fff;
      border: 1px solid #e8e8e8;
      border-radius: 4px;
      padding: 10px 12px;
      font-size: 12px;
      line-height: 1.6;
      max-height: 200px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-all;
      margin: 0;
    }
    .error-output {
      border-color: #ffccc7;
      background: #fff2f0;
    }
    .artifact-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .artifact-item {
      display: flex;
      align-items: center;
      gap: 4px;
      padding: 4px 10px;
      background: #f5f5f5;
      border-radius: 4px;
      font-size: 12px;
    }
  `],
})
export class SchedulerLogsModalComponent implements OnInit, OnDestroy {
  taskId = '';
  taskName = '';

  logs: ExecutionLog[] = [];
  loading = false;
  currentPage = 1;
  pageSize = 10;
  total = 0;
  expandedId = '';

  private destroy$ = new Subject<void>();

  constructor(
    private schedulerService: SchedulerService,
    @Inject(NZ_MODAL_DATA) private data: any,
  ) {
    this.taskId = data?.taskId || '';
    this.taskName = data?.taskName || '';
  }

  ngOnInit(): void {
    this.loadLogs();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  loadLogs(): void {
    this.loading = true;
    this.schedulerService.listExecutions(this.taskId, {
      page: this.currentPage,
      page_size: this.pageSize,
    }).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res: any) => {
        this.logs = res?.items || [];
        this.total = res?.total || 0;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  toggleDetail(log: ExecutionLog): void {
    this.expandedId = this.expandedId === log.id ? '' : log.id;
  }



  getLogStatusColor(status: string): string {
    const m: Record<string, string> = {
      success: 'success',
      failed: 'error',
      running: 'processing',
      pending: 'default',
      retrying: 'orange',
    };
    return m[status] || 'default';
  }

  getLogStatusLabel(status: string): string {
    const m: Record<string, string> = {
      success: '成功',
      failed: '失败',
      running: '执行中',
      pending: '等待中',
      retrying: '重试中',
    };
    return m[status] || status;
  }

  getTriggerLabel(type: string): string {
    const m: Record<string, string> = {
      scheduled: '定时调度',
      manual: '手动触发',
      retry: '自动重试',
    };
    return m[type] || type || '-';
  }
}
