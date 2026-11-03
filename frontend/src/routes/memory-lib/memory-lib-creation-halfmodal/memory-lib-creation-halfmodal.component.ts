import { ChangeDetectionStrategy, Component, computed, inject, Input, OnDestroy, OnInit, signal, Optional, Inject } from '@angular/core';
import { AbstractControl, FormBuilder, FormsModule, ReactiveFormsModule, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { Subject, takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzGridModule } from 'ng-zorro-antd/grid';

import { I18nNamespace } from '@i18n';
import { UploadImageComponent } from '@routes/knowledge-center/components/upload-image/upload-image.component';
import { KbUtils } from '@routes/knowledge-center/kb.utils';
import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { MEMORY_LIB_DEFAULT_ICON } from '@routes/memory-lib/memory-lib-constants';
import { LtmRetrievalStrategyComponent } from '@routes/memory-lib/memory-lib-creation-halfmodal/ltm-retrieval-strategy/ltm-retrieval-strategy.component';
import { IMemoryStrategy } from '@routes/memory-lib/memory-lib-interfaces';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { NzDrawerRef, NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';
import { NzModalRef } from 'ng-zorro-antd/modal';
@Component({
  selector: 'memory-lib-creation-halfmodal',
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
    LtmRetrievalStrategyComponent,
    UploadImageComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MEMORY_LIB, I18nNamespace.COMMON],
    },
  ],
  templateUrl: './memory-lib-creation-halfmodal.component.html',
  styleUrl: './memory-lib-creation-halfmodal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryLibCreationHalfmodalComponent implements OnInit, OnDestroy {
  @Input() libId = '';

  readonly visibilityService = inject(SetSidebarVisibilityService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly http = inject(HttpService);
  readonly commonService = inject(CommonService);
  readonly memoryLibApiService = inject(MemoryLibApiService);
  readonly fb = inject(FormBuilder);

  modalTitle = computed(() => (this.libId ? this.i18n.transform('memory.edit.title') : this.i18n.transform('memory.create.title')));
  loading = signal(false);
  defaultIcon = MEMORY_LIB_DEFAULT_ICON;

  memoryBackendType = signal<string | undefined>(undefined);
  memoryServiceInstanceId = signal<string | undefined>(undefined);

  helpConfig = {
    iconTip: this.i18n.transform('memory.create.strategy.triggerTip'),
  };

  basicInfoFormGroup = this.fb.group({
    name: ['', [Validators.required, Validators.maxLength(50), this.nameVerify()]],
    description: ['', [Validators.maxLength(1000)]],
    icon: [this.defaultIcon],
  });

  ltmRetrievalStrategyFormGroup = this.fb.group({
    ltmRetrievalStrategy: [[] as IMemoryStrategy[], [this.strategyRequiredValidator()]],
  });

  extractionFrequencyFormGroup = this.fb.group({
    conversation_round: [null as number | null, [this.valueErrorValidator(1, 30)]],
    time_span: [null as number | null, [this.valueErrorValidator(5, 60)]],
  });

  private destroy$ = new Subject<void>();

  public setLoading = (isLoading: boolean) => {
    this.loading.set(isLoading);
  };

  get currentNameLength() {
    return this.basicInfoFormGroup.get('name')?.value?.length ?? 0;
  }

  constructor(
    @Optional() private drawerRef: NzDrawerRef,
    @Optional() private modalRef: NzModalRef,
    @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {
    this.http.getCurrentUserResourceStatus().pipe(takeUntil(this.destroy$)).subscribe();
  }

  #queryDetail() {
    if (this.libId) {
      this.loading.set(true);
      this.memoryLibApiService
        .queryMemoryLibDetail(this.libId)
        .then(res => {
          this.basicInfoFormGroup.patchValue({
            name: res.name,
            description: res.description,
            icon: res.icon,
          });
          this.ltmRetrievalStrategyFormGroup.patchValue({
            ltmRetrievalStrategy: res.long_term_memory_strategies ?? [],
          });
          this.extractionFrequencyFormGroup.patchValue({
            conversation_round: res.conversation_round ?? null,
            time_span: res.time_span ?? null,
          });
          this.memoryBackendType.set(res.memory_backend_type);
          this.memoryServiceInstanceId.set(res.memory_service_instance_id);
        })
        .finally(() => {
          this.loading.set(false);
        });
    }
  }

  ngOnInit() {
    this.#queryDetail();
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
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

  onImageChanged(file: any) {
    if (!file) {
      return;
    }
    KbUtils.readFileAsBase64(file).then(res => {
      this.basicInfoFormGroup.patchValue({ icon: res });
    });
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

  dismiss(): void {
    if (this.nzData.beforeHide && typeof this.nzData.beforeHide === 'function') {
      this.nzData.beforeHide({
        reason: false,
      });
    }
  }
  close(): void {
    const errorBasicInfoForm = !this.showFromErrorByName(this.basicInfoFormGroup, []);
    const errorLtmRetrievalStrategyForm = !this.showFromErrorByName(this.ltmRetrievalStrategyFormGroup, []);
    const errorExtractionFrequencyForm = !this.showFromErrorByName(this.extractionFrequencyFormGroup, []);
    if (errorBasicInfoForm || errorLtmRetrievalStrategyForm || errorExtractionFrequencyForm) {
      return;
    }
    if (this.nzData.beforeHide && typeof this.nzData.beforeHide === 'function') {
      this.nzData.beforeHide({
        reason: true,
      });
    }
  }

  showFromErrorByName(form, validatorName): boolean {
    let res = true;
    const keysList = Object.keys(form.controls);
    if (keysList) {
      for (let i = 0; i < keysList.length; i++) {
        form.controls[keysList[i]].markAsDirty();
        form.controls[keysList[i]].updateValueAndValidity({ onlySelf: false });
        if (validatorName?.length > 0) {
          for (let j = 0; j < validatorName.length; j++) {
            if (keysList[i].indexOf(validatorName[j]) === 0) {
              if (form.controls[keysList[i]].errors) {
                res = false;
              }
            }
          }
        } else {
          if (form.controls[keysList[i]].errors) {
            res = false;
          }
        }
      }
    }

    return res;
  }
}
