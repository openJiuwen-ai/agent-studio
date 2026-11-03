import { ChangeDetectionStrategy, Component, EventEmitter, inject, Input, OnChanges, Output, SimpleChanges, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextModule } from 'angular-i18next';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { I18nNamespace } from '@i18n';

import { MemoryServiceInstanceApiService } from '@routes/memory-lib/memory-service-instance-api.service';
import { ContextService } from '@services/context.service';

@Component({
  selector: 'memory-service-instance-modal',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    I18NextModule,
    NzFormModule,
    NzInputModule,
    NzButtonModule,
    NzSpinModule,
    NzModalModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MEMORY_LIB, I18nNamespace.COMMON],
    },
  ],
  templateUrl: './memory-service-instance-modal.component.html',
  styleUrl: './memory-service-instance-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryServiceInstanceModalComponent implements OnChanges {
  @Input() visible = false;
  @Input() instanceId = '';
  @Output() saved = new EventEmitter<void>();
  @Output() cancelled = new EventEmitter<void>();

  private readonly fb = inject(FormBuilder);
  private readonly instanceApiService = inject(MemoryServiceInstanceApiService);
  private readonly ctxServ = inject(ContextService);

  loading = signal(false);
  isEdit = signal(false);

  formGroup = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(128)]],
    base_url: ['', [Validators.required, Validators.maxLength(512)]],
    api_key: ['', [Validators.maxLength(1024)]],
  });

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['visible'] && this.visible) {
      this.open();
    }
  }

  private open() {
    this.isEdit.set(!!this.instanceId);
    this.formGroup.reset({ name: '', base_url: '', api_key: '' });
    if (this.instanceId) {
      this.loadDetail();
    }
  }

  private loadDetail() {
    this.loading.set(true);
    const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
    this.instanceApiService
      .showInstance(workspaceId, this.instanceId)
      .then(res => {
        this.formGroup.patchValue({
          name: res.name,
          base_url: res.base_url,
          api_key: '',
        });
      })
      .finally(() => {
        this.loading.set(false);
      });
  }

  onSubmit(): void {
    if (this.formGroup.invalid) {
      Object.values(this.formGroup.controls).forEach(c => {
        c.markAsDirty();
        c.updateValueAndValidity({ onlySelf: false });
      });
      return;
    }

    this.loading.set(true);
    const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
    const values = this.formGroup.getRawValue();

    if (this.isEdit()) {
      // Edit: only send non-empty api_key (empty = don't change)
      const params: any = {
        name: values.name,
        base_url: values.base_url,
      };
      if (values.api_key) {
        params.api_key = values.api_key;
      }
      this.instanceApiService
        .modifyInstance(workspaceId, this.instanceId, params)
        .then(() => {
          this.loading.set(false);
          this.saved.emit();
        })
        .catch(() => {
          this.loading.set(false);
        });
    } else {
      // Create
      const params = {
        name: values.name,
        base_url: values.base_url,
        api_key: values.api_key || undefined,
      };
      this.instanceApiService
        .createInstance(workspaceId, params)
        .then(() => {
          this.loading.set(false);
          this.saved.emit();
        })
        .catch(() => {
          this.loading.set(false);
        });
    }
  }

  onCancel(): void {
    this.cancelled.emit();
  }
}
