import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzDividerModule } from 'ng-zorro-antd/divider';
import { Subject, takeUntil } from 'rxjs';
import { SchedulerService, ScheduledTask } from './scheduler.service';
import { SchedulerFormModalComponent } from './scheduler-form-modal.component';
import { SchedulerLogsModalComponent } from './scheduler-logs-modal.component';
import { HttpService } from '@services/http.service';
import { StorageService } from '@shared/services/cfdata.service';

@Component({
  selector: 'app-scheduler',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NzTableModule,
    NzButtonModule,
    NzIconModule,
    NzTagModule,
    NzInputModule,
    NzDropDownModule,
    NzPopconfirmModule,
    NzModalModule,
    NzSpinModule,
    NzEmptyModule,
    NzToolTipModule,
    NzSwitchModule,
    NzDividerModule,
  ],
  template: `
    <div class="scheduler-page">
      <!-- 页面头部 -->
      <div class="page-header">
        <div class="header-left">
          <h2 class="page-title">自动化</h2>
          <span class="task-count" *ngIf="total > 0">共 {{ total }} 个任务</span>
        </div>
        <div class="header-right">
          <div class="search-box">
            <input
              nz-input
              [(ngModel)]="searchValue"
              placeholder="搜索任务名称"
              nzSearch
              (ngModelChange)="onSearchChange()"
            />
            <nz-icon
              *ngIf="searchValue"
              nzType="close-circle"
              class="search-clear"
              (click)="clearSearch()"
            ></nz-icon>
          </div>
          <button nz-button nzType="primary" (click)="openCreateModal()">
            <nz-icon nzType="plus"></nz-icon>
            新建任务
          </button>
        </div>
      </div>

      <!-- 任务列表 -->
      <nz-table
        #taskTable
        [nzData]="taskList"
        [nzLoading]="loading"
        [nzPageSize]="pageSize"
        [(nzPageIndex)]="currentPage"
        [nzTotal]="total"
        nzShowPagination
        [nzFrontPagination]="false"
        [nzSize]="'middle'"
        (nzPageIndexChange)="loadTasks()"
        (nzPageSizeChange)="onPageSizeChange($event)"
        [nzShowSizeChanger]="true"
        [nzPageSizeOptions]="[10, 20, 50]"
      >
        <thead>
          <tr>
            <th nzWidth="20%">任务名称</th>
            <th nzWidth="8%">状态</th>
            <th nzWidth="22%">调度规则</th>
            <th nzWidth="14%">下次执行</th>
            <th nzWidth="8%">执行次数</th>
            <th nzWidth="28%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr *ngFor="let task of taskTable.data">
            <td>
              <div class="task-name-cell">
                <span class="task-name" [nzTooltipTitle]="task.name" nz-tooltip>{{ task.name }}</span>
                <span class="task-desc" *ngIf="task.description" [nzTooltipTitle]="task.description" nz-tooltip>
                  {{ task.description }}
                </span>
              </div>
            </td>
            <td>
              <nz-tag [nzColor]="task.status === 'enabled' ? 'green' : 'default'">
                {{ task.status === 'enabled' ? '启用' : '禁用' }}
              </nz-tag>
            </td>
            <td>
              <span class="schedule-desc" [nzTooltipTitle]="getScheduleTooltip(task)" nz-tooltip>
                {{ getScheduleDisplay(task) }}
              </span>
            </td>
            <td>
              <span *ngIf="task.next_run_at">{{ task.next_run_at | date:'MM-dd HH:mm' }}</span>
              <span *ngIf="!task.next_run_at" class="text-muted">-</span>
            </td>
            <td>{{ task.run_count || 0 }}</td>
            <td>
              <div class="action-cell">
                <!-- 编辑 -->
                <button
                  nz-button
                  nzType="link"
                  nzSize="small"
                  (click)="openEditModal(task)"
                  [nzTooltipTitle]="canEdit(task) ? '编辑' : '无编辑权限'"
                  nz-tooltip
                  [disabled]="!canEdit(task)"
                >
                  <nz-icon nzType="edit"></nz-icon>
                  编辑
                </button>

                <!-- 立即执行 -->
                <button
                  nz-button
                  nzType="link"
                  nzSize="small"
                  (click)="triggerTask(task)"
                  [nzLoading]="task._triggering"
                  nz-tooltip
                  nzTooltipTitle="立即执行一次"
                  [disabled]="task.status !== 'enabled'"
                >
                  <nz-icon nzType="play-circle"></nz-icon>
                  执行
                </button>

                <!-- 查看日志 -->
                <button
                  nz-button
                  nzType="link"
                  nzSize="small"
                  (click)="openLogsModal(task)"
                >
                  <nz-icon nzType="file-text"></nz-icon>
                  日志
                </button>

                <!-- 启用/禁用 -->
                <button
                  nz-button
                  nzType="link"
                  nzSize="small"
                  (click)="toggleStatus(task)"
                  [nzLoading]="task._toggling"
                  [disabled]="!canEdit(task)"
                >
                  <nz-icon [nzType]="task.status === 'enabled' ? 'pause-circle' : 'check-circle'"></nz-icon>
                  {{ task.status === 'enabled' ? '禁用' : '启用' }}
                </button>

                <!-- 删除 -->
                <button
                  nz-button
                  nzType="link"
                  nzSize="small"
                  nzDanger
                  nz-popconfirm
                  nzPopconfirmTitle="确定删除该任务？"
                  nzPopconfirmPlacement="bottomRight"
                  (nzOnConfirm)="deleteTask(task)"
                  [disabled]="!canEdit(task)"
                >
                  <nz-icon nzType="delete"></nz-icon>
                  删除
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </nz-table>

      <nz-empty *ngIf="!loading && taskList.length === 0 && !searchValue" nzNotFoundContent="暂无自动化" nzNotFoundContent="点击右上角新建任务"></nz-empty>
      <nz-empty *ngIf="!loading && taskList.length === 0 && searchValue" [nzNotFoundContent]="'未找到包含 ' + searchValue + ' 的任务'"></nz-empty>
    </div>
  `,
  styles: [`
    .scheduler-page {
      padding: 24px;
      height: 100%;
      display: flex;
      flex-direction: column;
    }
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .header-left {
      display: flex;
      align-items: baseline;
      gap: 12px;
    }
    .page-title {
      margin: 0;
      font-size: 20px;
      font-weight: 600;
      color: #1a1a1a;
    }
    .task-count {
      font-size: 13px;
      color: #999;
    }
    .header-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .search-box {
      position: relative;
      width: 240px;
    }
    .search-box input {
      padding-right: 32px;
    }
    .search-clear {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 14px;
      color: #bbb;
      cursor: pointer;
    }
    .search-clear:hover {
      color: #666;
    }
    .task-name-cell {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .task-name {
      font-weight: 500;
      color: #1a1a1a;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }
    .task-desc {
      font-size: 12px;
      color: #999;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }
    .schedule-desc {
      font-size: 13px;
      color: #555;
      max-width: 220px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }
    .text-muted {
      color: #bbb;
    }
    .action-cell {
      display: flex;
      align-items: center;
      gap: 2px;
      flex-wrap: nowrap;
    }
    .action-cell button {
      padding: 0 4px;
    }
  `],
})
export class SchedulerComponent implements OnInit, OnDestroy {
  private destroy$ = new Subject<void>();

  taskList: ScheduledTask[] = [];
  loading = false;
  currentPage = 1;
  pageSize = 20;
  total = 0;
  searchValue = '';
  currentUserId = '';

  constructor(
    private schedulerService: SchedulerService,
    private modal: NzModalService,
    private message: NzMessageService,
    private http: HttpService,
  ) {}

  ngOnInit(): void {
    this.loadUserInfo();
    this.loadTasks();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private loadUserInfo(): void {
    try {
      const me = StorageService.getLocalStorage('PROMPT_ENGINEERING_ME');
      this.currentUserId = me?.userId || '';
    } catch {}
  }

  loadTasks(): void {
    this.loading = true;
    this.schedulerService.listTasks({
      page: this.currentPage,
      page_size: this.pageSize,
      search: this.searchValue || undefined,
    }).pipe(takeUntil(this.destroy$)).subscribe({
      next: (res: any) => {
        this.taskList = (res?.items || []).map((t: any) => ({
          ...t,
          _triggering: false,
          _toggling: false,
        }));
        this.total = res?.total || 0;
        this.loading = false;
      },
      error: () => {
        this.message.error('加载任务列表失败');
        this.loading = false;
      },
    });
  }

  onSearchChange(): void {
    this.currentPage = 1;
    this.loadTasks();
  }

  clearSearch(): void {
    this.searchValue = '';
    this.currentPage = 1;
    this.loadTasks();
  }

  onPageSizeChange(size: number): void {
    this.pageSize = size;
    this.currentPage = 1;
    this.loadTasks();
  }

  canEdit(task: ScheduledTask): boolean {
    if (!this.currentUserId) return true;
    return task.creator_id === this.currentUserId;
  }

  openCreateModal(): void {
    const modalRef = this.modal.create({
      nzContent: SchedulerFormModalComponent,
      nzWidth: '720px',
      nzFooter: null,
      nzClosable: true,
      nzData: { editTask: null },
      nzOnOk: () => {},
    });
    modalRef.afterClose.subscribe(result => {
      if (result) this.loadTasks();
    });
  }

  openEditModal(task: ScheduledTask): void {
    const modalRef = this.modal.create({
      nzContent: SchedulerFormModalComponent,
      nzWidth: '720px',
      nzFooter: null,
      nzClosable: true,
      nzData: { editTask: task },
    });
    modalRef.afterClose.subscribe(result => {
      if (result) this.loadTasks();
    });
  }

  openLogsModal(task: ScheduledTask): void {
    this.modal.create({
      nzContent: SchedulerLogsModalComponent,
      nzTitle: `执行日志 - ${task.name}`,
      nzWidth: '900px',
      nzFooter: null,
      nzClosable: true,
      nzData: { taskId: task.id, taskName: task.name },
    });
  }

  triggerTask(task: ScheduledTask): void {
    (task as any)._triggering = true;
    this.schedulerService.triggerTask(task.id).pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.message.success(`任务「${task.name}」已触发执行`);
        (task as any)._triggering = false;
        this.loadTasks();
      },
      error: () => {
        this.message.error('触发执行失败');
        (task as any)._triggering = false;
      },
    });
  }

  toggleStatus(task: ScheduledTask): void {
    (task as any)._toggling = true;
    const req$ = task.status === 'enabled'
      ? this.schedulerService.disableTask(task.id)
      : this.schedulerService.enableTask(task.id);

    req$.pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.message.success(task.status === 'enabled' ? '任务已禁用' : '任务已启用');
        (task as any)._toggling = false;
        this.loadTasks();
      },
      error: () => {
        this.message.error('操作失败');
        (task as any)._toggling = false;
      },
    });
  }

  deleteTask(task: ScheduledTask): void {
    this.schedulerService.deleteTask(task.id).pipe(takeUntil(this.destroy$)).subscribe({
      next: () => {
        this.message.success('任务已删除');
        if (this.taskList.length === 1 && this.currentPage > 1) {
          this.currentPage--;
        }
        this.loadTasks();
      },
      error: () => {
        this.message.error('删除失败');
      },
    });
  }

  getScheduleDisplay(task: ScheduledTask): string {
    if (task.schedule_description) return task.schedule_description;
    if (task.schedule_type === 'cron' && task.schedule_config?.expression) {
      return this.describeCron(task.schedule_config.expression);
    }
    if (task.schedule_type === 'natural_language' && task.schedule_config?.text) {
      return task.schedule_config.text;
    }
    return task.schedule_type || '-';
  }

  getScheduleTooltip(task: ScheduledTask): string {
    const parts: string[] = [];
    parts.push(`类型: ${task.schedule_type}`);
    if (task.schedule_config?.expression) parts.push(`表达式: ${task.schedule_config.expression}`);
    if (task.valid_from) parts.push(`生效: ${task.valid_from}`);
    if (task.valid_until) parts.push(`截止: ${task.valid_until}`);
    return parts.join('\n');
  }

  private describeCron(expr: string): string {
    const parts = expr.split(/\s+/);
    if (parts.length < 5) return expr;
    const [min, hour, dom, mon, dow] = parts;
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

    if (dom === '*' && mon === '*' && dow === '*') {
      if (hour === '*') return `每小时第${min}分钟`;
      return `每天 ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
    }
    if (dow !== '*' && dom === '*') {
      const dayName = weekdays[parseInt(dow)] || dow;
      return `每周${dayName} ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
    }
    if (dom !== '*' && dow === '*') {
      return `每月${dom}号 ${hour.padStart(2, '0')}:${min.padStart(2, '0')}`;
    }
    return expr;
  }
}
