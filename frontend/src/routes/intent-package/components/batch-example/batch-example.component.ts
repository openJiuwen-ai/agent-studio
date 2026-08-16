import { Component, Output, EventEmitter, Inject, OnDestroy } from '@angular/core';
import { MODULES } from '@shared/modules';
import { CommonModule } from '@angular/common';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { FormBuilder, FormControl, AbstractControl, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Subject } from 'rxjs';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'batch-example',
  templateUrl: './batch-example.component.html',
  styleUrls: ['./batch-example.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MODULES,
    NzInputModule,
    NzButtonModule,
    NzFormModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class BatchExampleComponent implements OnDestroy {
  @Output('getIntentExampleName') getIntentExampleName = new EventEmitter<string>();

  private destroy$ = new Subject<void>();

  constructor(
    private readonly fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private modalRef: NzModalRef,
    private message: NzMessageService,
    @Inject(NZ_MODAL_DATA) public nzData: any
  ) {}

  public pluginNameVerify() {
    return (control: AbstractControl) => {
      const regExp = new RegExp(
        '^(?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-]{1,63})(?:,(?:[\\u4e00-\\u9fa5a-zA-Z0-9_\\-]{1,63}))*$',
      );
      const v: string = control.value || '';

      return regExp.test(v)
        ? null
        : { nameChAllow: true };
    };
  }

  public form = this.fb.group({
    name: new FormControl('', [Validators.required, this.pluginNameVerify()]),
  });

  submit() {
    if (!this.#validate()) {
      return;
    }
    const val = this.form.value.name;
    this.getIntentExampleName.emit(val);
    if (this.nzData?.outputs?.getIntentExampleName) {
      this.nzData.outputs.getIntentExampleName(val);
    }

    this.form.reset();
    this.dismiss();
  }

  #validate(): boolean {
    if (this.form.invalid) {
      Object.values(this.form.controls).forEach(control => {
        control.markAsDirty();
        control.updateValueAndValidity({ onlySelf: true });
      });
      this.message.warning(this.i18n.transform('form_verify_fail_tips'));
      return false;
    }
    return true;
  }

  dismiss(): void {
    this.modalRef.close();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
