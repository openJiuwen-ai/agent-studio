import { ChangeDetectionStrategy, Component, inject, Input, OnInit, signal, Optional, Inject } from '@angular/core';
import { AbstractControl, FormBuilder, FormsModule, ReactiveFormsModule, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { I18NextEagerPipe, I18NextModule, I18NEXT_NAMESPACE } from 'angular-i18next';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzGridModule } from 'ng-zorro-antd/grid';
import { NzSelectModule } from 'ng-zorro-antd/select';

import { I18nNamespace } from '@i18n';
import { UploadImageComponent } from '@routes/knowledge-center/components/upload-image/upload-image.component';
import { KbUtils } from '@routes/knowledge-center/kb.utils';
import { MEMORY_LIB_DEFAULT_ICON } from '@routes/memory-lib/memory-lib-constants';
import { LtmRetrievalStrategyComponent } from '@routes/memory-lib/memory-lib-creation-halfmodal/ltm-retrieval-strategy/ltm-retrieval-strategy.component';
import { IMemoryStrategy } from '@routes/memory-lib/memory-lib-interfaces';
import { MemoryServiceInstanceApiService } from '@routes/memory-lib/memory-service-instance-api.service';
import { IMemoryServiceInstanceItem } from '@routes/memory-lib/memory-service-instance-interfaces';
import { ContextService } from '@services/context.service';
import { NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'connect-external-memory-modal',
  standalone: true,
  imports: [
    FormsModule,
    ReactiveFormsModule,
    I18NextModule,
    NzFormModule,
    NzInputModule,
    NzInputNumberModule,
    NzButtonModule,
    NzSpinModule,
    NzIconModule,
    NzToolTipModule,
    NzGridModule,
    NzSelectModule,
    LtmRetrievalStrategyComponent,
    UploadImageComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MEMORY_LIB, I18nNamespace.COMMON],
    },
  ],
  templateUrl: './connect-external-memory-modal.component.html',
  styleUrl: './connect-external-memory-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConnectExternalMemoryModalComponent implements OnInit {
  @Input() libId = '';

  readonly i18n = inject(I18NextEagerPipe);
  readonly instanceApiService = inject(MemoryServiceInstanceApiService);
  readonly ctxServ = inject(ContextService);
  readonly fb = inject(FormBuilder);

  loading = signal(false);
  defaultIcon = MEMORY_LIB_DEFAULT_ICON;
  instances = signal<IMemoryServiceInstanceItem[]>([]);

  basicInfoFormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(50), this.nameVerify()]],
    description: ['', [Validators.maxLength(1000)]],
    icon: [this.defaultIcon],
  });

  instanceFormGroup = this.fb.group({
    memory_service_instance_id: [null as string | null, [Validators.required]],
  });

  ltmRetrievalStrategyFormGroup = this.fb.group({
    ltmRetrievalStrategy: [[] as IMemoryStrategy[], [this.strategyRequiredValidator()]],
  });

  extractionFrequencyFormGroup = this.fb.group({
    conversation_round: [null as number | null, [this.valueErrorValidator(1, 30)]],
    time_span: [null as number | null, [this.valueErrorValidator(5, 60)]],
  });

  get currentNameLength() {
    return this.basicInfoFormGroup.get('name')?.value?.length ?? 0;
  }

  constructor(
    @Optional() @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {}

  #loadInstances() {
    const workspaceId = this.ctxServ.currentWorkspaceId ?? '';
    if (!workspaceId) {
      return;
    }
    this.instanceApiService
      .listInstances(workspaceId)
      .then(res => {
        this.instances.set(res.items ?? []);
      })
      .catch(() => {
        this.instances.set([]);
      });
  }

  ngOnInit() {
    this.#loadInstances();
  }

  nameVerify(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value) {
        return null;
      }
      return /^(?!\s)[\u4e00-\u9fa5a-zA-Z0-9_\- ]{1,50}(?<!\s)$/.test(control.value)
        ? null
        : { name: { tiErrorMessage: this.i18n.transform('memory.create.name.regx') } };
    };
  }

  valueErrorValidator(min: number, max: number): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value = control.value;
      if (value === null || value === undefined || value === '') {
        return null;
      }
      const num = Number(value);
      return Number.isNaN(num) || num < min || num > max ? { range: { min, max, value } } : null;
    };
  }

  strategyRequiredValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const value = control.value;
      return !value || value.length < 1
        ? {
            isStrategyRequired: {
              value: control.value,
              errorMsg: this.i18n.transform('memory.create.errorTip.strategyNeed'),
            },
          }
        : null;
    };
  }

  onImageChanged(file: any) {
    if (!file) {
      return;
    }
    KbUtils.readFileAsBase64(file).then(res => {
      this.basicInfoFormGroup.patchValue({ icon: res });
    });
  }

  #markGroupDirty(group: any) {
    Object.values(group.controls).forEach((c: any) => {
      c.markAsDirty();
      c.updateValueAndValidity({ onlySelf: false });
    });
  }

  dismiss(): void {
    if (this.nzData?.beforeHide && typeof this.nzData.beforeHide === 'function') {
      this.nzData.beforeHide({ reason: false });
    }
  }

  close(): void {
    if (
      this.basicInfoFormGroup.invalid ||
      this.instanceFormGroup.invalid ||
      this.ltmRetrievalStrategyFormGroup.invalid ||
      this.extractionFrequencyFormGroup.invalid
    ) {
      this.#markGroupDirty(this.basicInfoFormGroup);
      this.#markGroupDirty(this.instanceFormGroup);
      this.#markGroupDirty(this.ltmRetrievalStrategyFormGroup);
      this.#markGroupDirty(this.extractionFrequencyFormGroup);
      return;
    }
    if (this.nzData?.beforeHide && typeof this.nzData.beforeHide === 'function') {
      this.nzData.beforeHide({ reason: true });
    }
  }

  getFormData() {
    const frequencyValues = this.extractionFrequencyFormGroup.getRawValue();
    const instanceValues = this.instanceFormGroup.getRawValue();
    return {
      ...this.basicInfoFormGroup.getRawValue(),
      long_term_memory_strategies: this.ltmRetrievalStrategyFormGroup.getRawValue().ltmRetrievalStrategy ?? [],
      conversation_round: frequencyValues.conversation_round ?? undefined,
      time_span: frequencyValues.time_span ?? undefined,
      memory_backend_type: 'EXTERNAL',
      memory_service_instance_id: instanceValues.memory_service_instance_id ?? undefined,
    };
  }
}
