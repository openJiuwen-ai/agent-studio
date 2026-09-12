import { Component, forwardRef, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { Subject, takeUntil, debounceTime, distinctUntilChanged } from 'rxjs';
import { SchedulerService } from './scheduler.service';

export interface ScheduleValue {
  type: 'cron' | 'visual' | 'natural_language';
  cronExpression?: string;
  visual?: VisualSchedule;
  naturalLanguageText?: string;
}

export interface VisualSchedule {
  frequency: 'hourly' | 'daily' | 'workdays' | 'weekly' | 'monthly';
  hour?: number;
  minute?: number;
  weekdays?: number[];
  monthDay?: number;
  lastDayOfMonth?: boolean;
}

@Component({
  selector: 'app-schedule-rule-picker',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    NzInputModule,
    NzRadioModule,
    NzSelectModule,
    NzCheckboxModule,
    NzInputNumberModule,
    NzDatePickerModule,
    NzIconModule,
    NzToolTipModule,
  ],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ScheduleRulePickerComponent),
      multi: true,
    },
  ],
  template: `
    <div class="schedule-picker">
      <nz-radio-group [(ngModel)]="inputMode" (ngModelChange)="onModeChange()">
        <label nz-radio-button [nzValue]="'cron'">Cron 表达式</label>
        <label nz-radio-button [nzValue]="'visual'">可视化设置</label>
        <label nz-radio-button [nzValue]="'natural_language'">自然语言</label>
      </nz-radio-group>

      <!-- Cron 表达式 -->
      <div *ngIf="inputMode === 'cron'" class="schedule-section">
        <div class="cron-input-row">
          <input
            nz-input
            [(ngModel)]="cronExpr"
            placeholder="例: 0 9 * * * (每天9点执行)"
            (ngModelChange)="onCronChange()"
            [nzStatus]="cronError ? 'error' : ''"
          />
          <nz-icon
            nzType="info-circle"
            nz-tooltip
            nzTooltipTitle="格式: 分 时 日 月 周  |  例: 0 9 * * 1 (每周一9点)"
            class="cron-hint-icon"
          />
        </div>
        <div *ngIf="cronError" class="cron-error">{{ cronError }}</div>
        <div *ngIf="cronPreview && !cronError" class="cron-preview">
          <nz-icon nzType="clock-circle" />
          <span>预览: {{ cronPreview }}</span>
        </div>
      </div>

      <!-- 可视化周期选择器 -->
      <div *ngIf="inputMode === 'visual'" class="schedule-section">
        <div class="visual-row">
          <label class="field-label">执行频率</label>
          <nz-select [(ngModel)]="visual.frequency" style="width: 180px;" (ngModelChange)="onVisualChange()">
            <nz-option nzValue="hourly" nzLabel="每小时"></nz-option>
            <nz-option nzValue="daily" nzLabel="每天"></nz-option>
            <nz-option nzValue="workdays" nzLabel="工作日 (周一至周五)"></nz-option>
            <nz-option nzValue="weekly" nzLabel="每周"></nz-option>
            <nz-option nzValue="monthly" nzLabel="每月"></nz-option>
          </nz-select>
        </div>

        <!-- 每小时/每天/工作日：选 时/分 -->
        <div *ngIf="visual.frequency !== 'monthly'" class="visual-row">
          <label class="field-label">执行时间</label>
          <nz-input-number
            [(ngModel)]="visual.hour"
            [nzMin]="0" [nzMax]="23" [nzStep]="1"
            [nzFormatter]="formatHour"
            [nzParser]="parseHour"
            style="width: 100px;"
            (ngModelChange)="onVisualChange()"
          ></nz-input-number>
          <span class="time-sep">:</span>
          <nz-input-number
            [(ngModel)]="visual.minute"
            [nzMin]="0" [nzMax]="59" [nzStep]="5"
            style="width: 100px;"
            (ngModelChange)="onVisualChange()"
          ></nz-input-number>
        </div>

        <!-- 每周：勾选星期 -->
        <div *ngIf="visual.frequency === 'weekly'" class="visual-row weekday-row">
          <label class="field-label">选择星期</label>
          <div class="weekday-group">
            <label
              *ngFor="let wd of weekDays; let i = index"
              nz-checkbox
              [ngModel]="visual.weekdays?.includes(wd.value)"
              (ngModelChange)="toggleWeekday(wd.value, $event)"
              class="weekday-item"
            >{{ wd.label }}</label>
          </div>
        </div>

        <!-- 每月：选日期 或 月末 -->
        <div *ngIf="visual.frequency === 'monthly'" class="visual-row">
          <label class="field-label">每月日期</label>
          <nz-select [(ngModel)]="visual.monthDayType" style="width: 200px;" (ngModelChange)="onVisualChange()">
            <nz-option nzValue="specific" nzLabel="指定日期"></nz-option>
            <nz-option nzValue="last" nzLabel="月末最后一天"></nz-option>
          </nz-select>
          <nz-input-number
            *ngIf="visual.monthDayType === 'specific'"
            [(ngModel)]="visual.monthDay"
            [nzMin]="1" [nzMax]="31" [nzStep]="1"
            style="width: 100px; margin-left: 8px;"
            (ngModelChange)="onVisualChange()"
          ></nz-input-number>
        </div>

        <div *ngIf="visualPreview" class="cron-preview">
          <nz-icon nzType="clock-circle" />
          <span>生成规则: {{ visualPreview }}</span>
        </div>
      </div>

      <!-- 自然语言 -->
      <div *ngIf="inputMode === 'natural_language'" class="schedule-section">
        <div class="cron-input-row">
          <textarea
            nz-input
            [(ngModel)]="nlText"
            [nzAutosize]="{ minRows: 2, maxRows: 4 }"
            placeholder="例: 每周一早上9点、每天下午2点30分、每月15号"
            (ngModelChange)="onNlChange()"
            [nzStatus]="nlError ? 'error' : ''"
          ></textarea>
        </div>
        <div *ngIf="nlError" class="cron-error">{{ nlError }}</div>
        <div *ngIf="nlPreview && !nlError" class="cron-preview">
          <nz-icon nzType="bulb" />
          <span>解析结果: {{ nlPreview }}</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .schedule-picker {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .schedule-section {
      margin-top: 4px;
      padding: 12px 16px;
      background: #fafafa;
      border-radius: 6px;
      border: 1px solid #f0f0f0;
    }
    .cron-input-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .cron-input-row input,
    .cron-input-row textarea {
      flex: 1;
    }
    .cron-hint-icon {
      font-size: 16px;
      color: #999;
      cursor: pointer;
    }
    .cron-error {
      margin-top: 4px;
      font-size: 12px;
      color: #ff4d4f;
    }
    .cron-preview {
      margin-top: 8px;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      color: #1f42ce;
      background: #f0f5ff;
      padding: 6px 10px;
      border-radius: 4px;
    }
    .cron-preview nz-icon {
      font-size: 14px;
    }
    .visual-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
    }
    .visual-row:last-child {
      margin-bottom: 0;
    }
    .field-label {
      min-width: 80px;
      font-size: 13px;
      color: #666;
      white-space: nowrap;
    }
    .time-sep {
      font-size: 18px;
      font-weight: 600;
      color: #333;
    }
    .weekday-group {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }
    .weekday-item {
      margin-right: 0 !important;
    }
  `],
})
export class ScheduleRulePickerComponent implements ControlValueAccessor, OnInit, OnDestroy {
  private destroy$ = new Subject<void>();
  private onChange: (value: any) => void = () => {};
  private onTouched: () => void = () => {};

  inputMode: 'cron' | 'visual' | 'natural_language' = 'cron';
  cronExpr = '';
  cronError = '';
  cronPreview = '';

  visual: VisualSchedule & { monthDayType?: 'specific' | 'last' } = {
    frequency: 'daily',
    hour: 9,
    minute: 0,
    weekdays: [1, 2, 3, 4, 5],
    monthDay: 1,
    monthDayType: 'specific',
  };
  visualPreview = '';

  nlText = '';
  nlError = '';
  nlPreview = '';

  weekDays = [
    { label: '一', value: 1 },
    { label: '二', value: 2 },
    { label: '三', value: 3 },
    { label: '四', value: 4 },
    { label: '五', value: 5 },
    { label: '六', value: 6 },
    { label: '日', value: 0 },
  ];

  private nlDebounce$ = new Subject<string>();

  constructor(private schedulerService: SchedulerService) {}

  ngOnInit(): void {
    this.nlDebounce$.pipe(
      debounceTime(600),
      distinctUntilChanged(),
      takeUntil(this.destroy$),
    ).subscribe(text => {
      this.parseNaturalLanguage(text);
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  writeValue(value: ScheduleValue): void {
    if (!value) return;
    if (value.type === 'cron') {
      this.inputMode = 'cron';
      this.cronExpr = value.cronExpression || '';
      this.validateCron();
    } else if (value.type === 'visual') {
      this.inputMode = 'visual';
      if (value.visual) {
        this.visual = { ...this.visual, ...value.visual };
      }
      this.generateVisualPreview();
    } else if (value.type === 'natural_language') {
      this.inputMode = 'natural_language';
      this.nlText = value.naturalLanguageText || '';
      this.nlPreview = this.nlText;
    }
  }

  registerOnChange(fn: any): void { this.onChange = fn; }
  registerOnTouched(fn: any): void { this.onTouched = fn; }

  onModeChange(): void {
    this.emitValue();
  }

  onCronChange(): void {
    this.validateCron();
    this.emitValue();
  }

  onVisualChange(): void {
    this.generateVisualPreview();
    this.emitValue();
  }

  onNlChange(): void {
    this.nlDebounce$.next(this.nlText);
    this.emitValue();
  }

  toggleWeekday(wd: number, checked: boolean): void {
    if (!this.visual.weekdays) this.visual.weekdays = [];
    if (checked) {
      this.visual.weekdays.push(wd);
    } else {
      this.visual.weekdays = this.visual.weekdays.filter(d => d !== wd);
    }
    this.onVisualChange();
  }

  formatHour(value: number): string {
    return `${String(value).padStart(2, '0')}:00`;
  }

  parseHour(value: string): number {
    return parseInt(value, 10) || 0;
  }

  private validateCron(): void {
    this.cronError = '';
    this.cronPreview = '';
    if (!this.cronExpr.trim()) {
      this.cronError = '请输入 Cron 表达式';
      return;
    }
    const parts = this.cronExpr.trim().split(/\s+/);
    if (parts.length < 5 || parts.length > 6) {
      this.cronError = 'Cron 表达式需要 5-6 个部分 (分 时 日 月 周)';
      return;
    }
    const ranges = [
      { min: 0, max: 59, label: '分钟' },
      { min: 0, max: 23, label: '小时' },
      { min: 1, max: 31, label: '日期' },
      { min: 1, max: 12, label: '月份' },
      { min: 0, max: 7, label: '星期' },
    ];
    for (let i = 0; i < 5; i++) {
      const part = parts[i];
      if (part !== '*' && !/^[0-9,\-\/]+$/.test(part)) {
        this.cronError = `${ranges[i].label} 部分格式错误: "${part}"`;
        return;
      }
    }
    this.cronPreview = this.describeCron(this.cronExpr.trim());
  }

  private describeCron(expr: string): string {
    const parts = expr.split(/\s+/);
    const [min, hour, dom, mon, dow] = parts;
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

    if (dom === '*' && mon === '*' && dow === '*') {
      if (hour === '*' && min === '*') return '每分钟执行';
      if (hour === '*') return `每小时的第 ${min} 分钟执行`;
      return `每天 ${hour.padStart(2, '0')}:${min.padStart(2, '0')} 执行`;
    }
    if (dow !== '*' && dom === '*') {
      const dayName = weekdays[parseInt(dow)] || dow;
      return `每周${dayName} ${hour.padStart(2, '0')}:${min.padStart(2, '0')} 执行`;
    }
    if (dom !== '*' && dow === '*') {
      return `每月 ${dom} 号 ${hour.padStart(2, '0')}:${min.padStart(2, '0')} 执行`;
    }
    return `Cron: ${expr}`;
  }

  private generateVisualPreview(): void {
    const h = String(this.visual.hour ?? 9).padStart(2, '0');
    const m = String(this.visual.minute ?? 0).padStart(2, '0');
    const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

    switch (this.visual.frequency) {
      case 'hourly':
        this.visualPreview = `每小时的第 ${this.visual.minute ?? 0} 分钟执行`;
        break;
      case 'daily':
        this.visualPreview = `每天 ${h}:${m} 执行`;
        break;
      case 'workdays':
        this.visualPreview = `工作日 (周一至周五) ${h}:${m} 执行`;
        break;
      case 'weekly': {
        const days = (this.visual.weekdays || [])
          .sort((a, b) => a - b)
          .map(d => `周${weekdays[d]}`)
          .join('、');
        this.visualPreview = days ? `${days} ${h}:${m} 执行` : '请选择星期';
        break;
      }
      case 'monthly':
        if (this.visual.monthDayType === 'last') {
          this.visualPreview = `每月最后一天 ${h}:${m} 执行`;
        } else {
          this.visualPreview = `每月 ${this.visual.monthDay ?? 1} 号 ${h}:${m} 执行`;
        }
        break;
    }
  }

  private parseNaturalLanguage(text: string): void {
    this.nlError = '';
    this.nlPreview = '';
    if (!text.trim()) return;
    this.nlPreview = `将在保存后由后端解析: "${text}"`;
  }

  private emitValue(): void {
    let value: ScheduleValue;
    switch (this.inputMode) {
      case 'cron':
        value = {
          type: 'cron',
          cronExpression: this.cronExpr,
        };
        break;
      case 'visual':
        value = {
          type: 'visual',
          visual: { ...this.visual },
        };
        break;
      case 'natural_language':
        value = {
          type: 'natural_language',
          naturalLanguageText: this.nlText,
        };
        break;
    }
    this.onChange(value);
    this.onTouched();
  }
}
