import {
  ChangeDetectionStrategy,
  Component,
  ViewChild,
  Output,
  EventEmitter,
  Input, inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { FormBuilder, FormControl, FormGroup, FormArray, NgForm, ValidationErrors } from '@angular/forms';
import { CommonValidation } from '@shared/validation/commonValidation';

@Component({
  selector: 'model-auth-modal',
  templateUrl: './model-auth-modal.component.html',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MODULES,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.MODEL_ACCESS,
      ],
    },
  ],
})
export class ModelAuthModalComponent {
  readonly modalRef = inject(NzModalRef);
  @ViewChild('authkeyForm') authkeyForm: NgForm;
  @Input() id: string = '';
  @Output() saveSuccess = new EventEmitter<any>();

  public radioList: Array<{ label: string; id: string; tip?: string; show?: boolean }> = [
    {
      label: this.i18n.transform('radio_list.no_authentication_required', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'NO_AUTH',
    },
    {
      label: this.i18n.transform('radio_list.api_key', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'API_KEY',
      tip: this.i18n.transform('Api_key_tip', { ns: I18nNamespace.MODEL_ACCESS }),
    },
    {
      label: this.i18n.transform('radio_list.AK_SK', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'AK_SK',
      tip: this.i18n.transform('AK_SK_tip', { ns: I18nNamespace.MODEL_ACCESS }),
    },
    {
      label: this.i18n.transform('radio_list.App-code', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'APP_CODE',
      tip: this.i18n.transform('APP_code_tip', { ns: I18nNamespace.MODEL_ACCESS }),
    },
    {
      label: this.i18n.transform('radio_list.CUSTOM_APIKEY', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'CUSTOM_APIKEY',
      tip: this.i18n.transform('custom_tip', { ns: I18nNamespace.MODEL_ACCESS }),
    },
    {
      label: this.i18n.transform('radio_list.CUSTOM_IAM', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'CUSTOM_IAM',
      tip: this.i18n.transform('IAM_tip', { ns: I18nNamespace.MODEL_ACCESS }),
    },
    {
      label: 'HisIAM',
      id: 'HIS_IAM',
      show:this.configServ.getConfigs()?.his_openai_enable,
      tip: this.i18n.transform('HisIAM_tip')
    },
    {
      label:'HisSGOV',
      id: 'SGOV',
      show: false,
      tip: this.i18n.transform('HisSGOV_tip')
    },
    {
      label:'HMAC',
      id: 'HMAC',
      show: this.configServ.getConfigs()?.hmac_auth_enabled,
      tip: this.i18n.transform('HMAC_tip')
    },
  ];

  public apiKeyForm: FormGroup;
  public collapsed = false;

  public verifyMethods = [
    {
      label: this.i18n.transform('verify_methods.iam_username_and_password', { ns: I18nNamespace.MODEL_ACCESS }),
      id: 'iam',
    },
    {
      label: 'Access Key ID/Secret Access Key',
      id: 'aksk',
    },
  ];

  public apiCollapsed = false;
  public apiKeyAuthArgs = [
    {
      target_name: '',
      auth_key: '',
    },
  ];

  constructor(
    private appFlowRepoServe: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private configServ: AgentConfigService,
  ) {
    this.apiKeyForm = this.fb.group({
      auth_type: new FormControl('NO_AUTH', []),
      apikey: new FormControl(''),
      appCode: new FormControl(''),
      description: new FormControl(''),
      iamDomain: new FormControl(''),
      ak: new FormControl(''),
      sk: new FormControl(''),
      iamUrl: new FormControl(''),
      iamUser: new FormControl(''),
      iamProject: new FormControl(''),
      iamPassword: new FormControl(''),
      iamAK: new FormControl(''),
      iamSK: new FormControl(''),
      verify: new FormControl('iam'),
      sgovUrl: new FormControl(''),
      credential: new FormControl(''),
      iamAccount: new FormControl(''),
      appId: new FormControl(''),
      iamSecret: new FormControl(''),
      iamEnterprise: new FormControl(''),
      scenarioUuid: new FormControl(''),
      userId: new FormControl(''),
    });
    this.changeAuthType('NO_AUTH');
  }

  ngOnInit() { }

  public dismiss() {
    this.modalRef.destroy();
  }

  public beforeToggle(row: any): void {
    row.showDetails = !row.showDetails;
  }

  public changeAuthType(auth) {
    if (auth === 'NO_AUTH') {
      this.resetControl();
    }

    if (auth === 'API_KEY') {
      this.resetControl();
      this.apiKeyForm.controls.apikey.setValidators([]);
    }

    if (auth === 'AK_SK' || auth === 'HMAC') {
      this.resetControl();
      this.apiKeyForm.controls.ak.setValidators([]);
      this.apiKeyForm.controls.sk.setValidators([]);
    }

    if (auth === 'APP_CODE') {
      this.resetControl();
      this.apiKeyForm.controls.appCode.setValidators([]);
    }

    if (auth === 'CUSTOM_APIKEY') {
      this.resetControl();
    }

    if (auth === 'CUSTOM_IAM') {
      this.resetControl();
      this.apiKeyForm.controls.iamUrl.setValidators([]);
      this.apiKeyForm.controls.iamDomain.setValidators([]);
      this.apiKeyForm.controls.iamProject.setValidators([]);
      this.apiKeyForm.controls.iamUser.setValidators([]);
      this.apiKeyForm.controls.iamPassword.setValidators([]);
    }

    if (auth === 'HIS_IAM') {
      this.resetControl();
      this.apiKeyForm.controls.iamUrl.setValidators([]);
      this.apiKeyForm.controls.iamAccount.setValidators([]);
      this.apiKeyForm.controls.iamProject.setValidators([]);
      this.apiKeyForm.controls.iamSecret.setValidators([]);
      this.apiKeyForm.controls.iamEnterprise.setValidators([]);
      this.apiKeyForm.controls.iamEnterprise.setValidators([]);
      this.apiKeyForm.controls.scenarioUuid.setValidators([]);
      this.apiKeyForm.controls.userId.setValidators([]);
    }

    if (auth === 'SGOV') {
      this.resetControl();
      this.apiKeyForm.controls.sgovUrl.setValidators([]);
      this.apiKeyForm.controls.appId.setValidators([]);
      this.apiKeyForm.controls.credential.setValidators([]);
      this.apiKeyForm.controls.iamEnterprise.setValidators([]);
      this.apiKeyForm.controls.scenarioUuid.setValidators([]);
    }
  }

  public resetControl() {
    this.apiKeyForm.controls.ak.setValidators([]);
    this.apiKeyForm.controls.sk.setValidators([]);
    this.apiKeyForm.controls.apikey.setValidators([]);
    this.apiKeyForm.controls.appCode.setValidators([]);
    this.apiKeyForm.controls.iamUser.setValidators([]);
    this.apiKeyForm.controls.iamAK.setValidators([]);
    this.apiKeyForm.controls.iamSK.setValidators([]);
    this.apiKeyForm.controls.appId.setValidators([]);
    this.apiKeyForm.controls.credential.setValidators([]);
    this.apiKeyForm.controls.sgovUrl.setValidators([]);
    this.apiKeyForm.controls.iamProject.setValidators([]);
    this.apiKeyForm.controls.iamDomain.setValidators([]);
    this.apiKeyForm.controls.iamPassword.setValidators([]);
    this.apiKeyForm.controls.iamUrl.setValidators([]);
    this.apiKeyForm.controls.iamAccount.setValidators([]);
    this.apiKeyForm.controls.iamSecret.setValidators([]);
    this.apiKeyForm.controls.iamEnterprise.setValidators([]);
    this.apiKeyForm.controls.scenarioUuid.setValidators([]);
    this.apiKeyForm.controls.userId.setValidators([]);
  }

  public confirm() {
    let errors: ValidationErrors | null;
    if (this.apiKeyForm.value.auth_type === 'CUSTOM_APIKEY') {
      errors = null;
    } else {
      errors = null;
    }
    const params = this.handleAutoInfo();
    this.appFlowRepoServe.saveAutheConfig(params, this.id).then(res => {
      this.saveSuccess.emit();
      this.modalRef.destroy();
    });
  }

  /**
   * 输入事件处理：过滤不可见控制字符和零宽字符
   * 应用于 API Key、AK、SK、AppCode 等认证凭据输入框
   */
  onAuthInputChange(controlName: string, event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = CommonValidation.sanitizeInvisibleChars(input.value);
    if (sanitized !== input.value) {
      const cursorPos = Math.max(0, input.selectionStart - (input.value.length - sanitized.length));
      this.apiKeyForm.controls[controlName]?.setValue(sanitized);
      requestAnimationFrame(() => {
        const pos = Math.min(cursorPos, sanitized.length);
        input.setSelectionRange(pos, pos);
      });
    }
  }

  /**
   * CUSTOM_APIKEY 模式下动态参数值的输入过滤
   */
  onCustomApikeyInput(index: number, event: Event): void {
    const input = event.target as HTMLInputElement;
    const sanitized = CommonValidation.sanitizeInvisibleChars(input.value);
    if (sanitized !== input.value) {
      const cursorPos = Math.max(0, input.selectionStart - (input.value.length - sanitized.length));
      this.apiKeyAuthArgs[index].auth_key = sanitized;
      requestAnimationFrame(() => {
        const pos = Math.min(cursorPos, sanitized.length);
        input.setSelectionRange(pos, pos);
      });
    }
  }

  public handleAutoInfo() {
    const value = this.apiKeyForm.getRawValue();
    let auth_info = {};
    if (value.auth_type === 'API_KEY') {
      auth_info = {
        'API Key': value.apikey,
      };
    }
    if (value.auth_type === 'APP_CODE') {
      auth_info = {
        'APP Code': value.appCode,
      };
    }
    if (value.auth_type === 'AK_SK' || value.auth_type === 'HMAC') {
      auth_info = {
        ak: value.ak,
        sk: value.sk,
      };
    }
    if (value.auth_type === 'CUSTOM_APIKEY') {
      let _obj = {};
      this.apiKeyAuthArgs.forEach((item) => {
        _obj[item.target_name] = item.auth_key;
      });
      auth_info = _obj;
    }
    if (value.auth_type === 'CUSTOM_IAM') {
      auth_info = {
        'iamUrl': value.iamUrl,
        'iamDomain': value.iamDomain,
        'iamProject': value.iamProject,
      };
      let param = value.verify === 'iam' ? {
        'iamUser': value.iamUser,
        'iamPassword': value.iamPassword,
      } : {
        'iamAK': value.iamAK,
        'iamSK': value.iamSK,
      };
      auth_info = { ...auth_info, ...param };
    }
    if (value.auth_type === 'HIS_IAM') {
      auth_info = {
        'iamUrl': value.iamUrl,
        'iamAccount': value.iamAccount,
        'iamProject': value.iamProject,
        'iamSecret': value.iamSecret,
        'iamEnterprise': value.iamEnterprise,
        'scenarioUuid': value.scenarioUuid,
        'userId':value.userId,
      }
    }

    if (value.auth_type === 'SGOV') {
      auth_info = {
        'appId': value.appId,
        'credential': value.credential,
        'sgovUrl': value.sgovUrl,
        'scenarioUuid': value.scenarioUuid,
      }
    }
    const params: any = {
      auth_type: value.auth_type,
      auth_info: JSON.stringify(auth_info),
    };
    return params;
  }

  public change(): void {
    this.collapsed = !this.collapsed;
  }

  public changeVerifyMethod(verify) {
    if (verify === 'iam') {
      this.apiKeyForm.controls.iamUser.setValidators([]);
      this.apiKeyForm.controls.iamPassword.setValidators([]);
      this.apiKeyForm.controls.iamAK.setValidators([]);
      this.apiKeyForm.controls.iamSK.setValidators([]);
      this.apiKeyForm.controls.iamSK.setValue('');
      this.apiKeyForm.controls.iamAK.setValue('');
    } else {
      this.apiKeyForm.controls.iamUser.setValue('');
      this.apiKeyForm.controls.iamPassword.setValue('');
      this.apiKeyForm.controls.iamUser.setValidators([]);
      this.apiKeyForm.controls.iamPassword.setValidators([]);
      this.apiKeyForm.controls.iamSK.setValidators([]);
      this.apiKeyForm.controls.iamAK.setValidators([]);
    }
  }

  public changeApi(): void {
    this.apiCollapsed = !this.apiCollapsed;
  }

  // 获取 apiKeyAuthArgs FormArray 的 getter
  get apiKeyAuthArgsArray() {
    return this.apiKeyForm.get('apiKeyAuthArgs') as FormArray;
  }

  public deleteArgs(i: number) {
    this.apiKeyAuthArgs.splice(i, 1);
  }

  public addArgs() {
    this.apiKeyAuthArgs.push({
      target_name: '',
      auth_key: '',
    });
  }

  public getKeyNames(index: number): {
    existingValues: string[];
    isHttp: boolean;
  } {
    const names = this.apiKeyAuthArgs.map((p) => p.target_name);
    names.splice(index, 1);
    return { existingValues: names, isHttp: true };
  }
}
