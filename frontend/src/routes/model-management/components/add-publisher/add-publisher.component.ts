import { Component, Input, ElementRef, ViewChild, OnInit, Optional, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgForm, FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from '../../../../single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { I18nNamespace } from '@i18n';
import { CommonValidation } from '@shared/validation/commonValidation';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonService } from '@services/common.service';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';

enum mapKeys {
  sgovUrl = 'sgovUrl',
  ak = 'ak',
  sk = 'sk',
  apikey = 'apikey',
  appCode = 'appCode',
  iamUser = 'iamUser',
  iamProject = 'iamProject',
  iamDomain = 'iamDomain',
  iamPassword = 'iamPassword',
  iamUrl = 'iamUrl',
  iamAK = 'iamAK',
  iamSK = 'iamSK',
  appId = 'appId',
  credential = 'credential',
  iamAccount = 'iamAccount',
  iamSecret = 'iamSecret',
  'iamEnterprise' = 'iamEnterprise',
  'scenarioUuid' = 'scenarioUuid',
  'userId' = 'userId',
  verify = 'verify',
  auth_type = 'auth_type',
  logo = 'logo',
  'API Key' = 'API Key',
  'APP Code' = 'APP Code',
}

@Component({
  selector: 'meta-add-publisher',
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    FormsModule,
    ReactiveFormsModule,
    NzButtonModule,
    NzIconModule,
    NzFormModule,
    NzInputModule,
    NzUploadModule,
    NzRadioModule,
    NzToolTipModule,
  ],
  templateUrl: './add-publisher.component.html',
  styleUrls: ['./add-publisher.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
  ],
})
export class AddPublisherComponent implements OnInit {
  @Input() title = this.i18n.transform('add_model', { ns: I18nNamespace.MODEL_ACCESS });
  @Input() provider_id: any;
  @Input() source: any;

  @ViewChild('authkeyForm') authkeyForm: NgForm;

  API_KEY = 'API_KEY';
  AK_SK = 'AK_SK';
  NO_AUTH = 'NO_AUTH';
  APP_CODE = 'APP_CODE';
  HMAC = 'HMAC';

  iamTip = {
    iamUrl: this.i18n.transform('iam_tip.iam_url'),
    iamDomain: this.i18n.transform('iam_tip.iam_domain'),
    iamProject: this.i18n.transform('iam_tip.iam_project'),
    iamUser: this.i18n.transform('iam_tip.iam_user'),
    iamPassword: this.i18n.transform('iam_tip.iam_password'),
    iamAK: this.i18n.transform('iam_tip.iam_ak'),
    iamSK: this.i18n.transform('iam_tip.iam_sk'),
  };

  apiCollapsed = false;

  radioList: Array<{ label: string; id: string; tip?: string; show?: boolean }> = [
    { label: this.i18n.transform('radio_list.no_authentication_required', { ns: I18nNamespace.MODEL_ACCESS }), show: true, id: this.NO_AUTH },
    {
      label: this.i18n.transform('radio_list.api_key', { ns: I18nNamespace.MODEL_ACCESS }),
      id: this.API_KEY,
      show: true,
      tip: this.i18n.transform('Api_key_tip'),
    },
    { label: this.i18n.transform('radio_list.AK_SK', { ns: I18nNamespace.MODEL_ACCESS }), id: this.AK_SK, show: false, tip: this.i18n.transform('AK_SK_tip') },
    {
      label: this.i18n.transform('radio_list.App-code', { ns: I18nNamespace.MODEL_ACCESS }),
      id: this.APP_CODE,
      show: false,
      tip: this.i18n.transform('APP_code_tip'),
    },
    {
      label: this.i18n.transform('radio_list.CUSTOM_APIKEY', { ns: I18nNamespace.MODEL_ACCESS }),
      id: 'CUSTOM_APIKEY',
      show: true,
      tip: this.i18n.transform('custom_tip'),
    },
    {
      label: this.i18n.transform('radio_list.CUSTOM_IAM', { ns: I18nNamespace.MODEL_ACCESS }),
      id: 'CUSTOM_IAM',
      show: false,
      tip: this.i18n.transform('IAM_tip'),
    },
    { label: 'HisIAM', id: 'HIS_IAM', show: this.configServ.getConfigs()?.his_openai_enable, tip: this.i18n.transform('HisIAM_tip') },
    { label: 'HisSGOV', id: 'SGOV', show: false, tip: this.i18n.transform('HisSGOV_tip') },
    { label: 'HMAC', id: 'HMAC', show: this.configServ.getConfigs()?.hmac_auth_enabled, tip: this.i18n.transform('HMAC_tip') },
  ];

  authList = [...this.radioList];
  loading = false;
  logoIsError = false;
  btnLoading = false;
  collapsed = false;

  apiKeyAuthArgs = [{ target_name: '', auth_key: '' }];

  verifyMethods = [
    { label: this.i18n.transform('verify_methods.iam_username_and_password'), id: 'iam' },
    { label: 'Access Key ID/Secret Access Key', id: 'aksk' },
  ];

  myForm: FormGroup;

  public formKeyMap = {
    ak: 'ak',
    sk: 'sk',
    iamUrl: 'iamUrl',
    iamDomain: 'iamDomain',
    iamProject: 'iamProject',
    iamPassword: 'iamPassword',
    iamAK: 'iamAK',
    iamSK: 'iamSK',
    iamAccount: 'iamAccount',
    iamSecret: 'iamSecret',
    iamEnterprise: 'iamEnterprise',
    scenarioUuid: 'scenarioUuid',
    credential: 'credential',
    sgovUrl: 'sgovUrl',
    iamUser: 'iamUser',
  };

  private urlPattern = /^https?:\/\/.+/;

  constructor(
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private configServ: AgentConfigService,
    private elementRef: ElementRef,
    public commonService: CommonService,
    private modelManagementService: ModelManagementService,
    private message: NzMessageService,
    @Optional() private drawerRef: NzDrawerRef,
    @Optional() private modalRef: NzModalRef,
    private cdr: ChangeDetectorRef
  ) {
    this.myForm = this.fb.group({
      provider_name: new FormControl('', [
        Validators.required,
        CommonValidation.modeNameVerify(this.i18n.transform('validation-name-tip1')),
        Validators.minLength(1),
        Validators.maxLength(64),
      ]),
      provider_name_en: new FormControl('', [
        Validators.required,
        CommonValidation.modeEnNameVerify(this.i18n.transform('validation-name-tip')),
        Validators.minLength(1),
        Validators.maxLength(64),
      ]),
      logo: new FormControl(cdnAssetUrl('assets/model/default_model.svg')),
      auth_type: new FormControl('NO_AUTH', [Validators.required]),
      apikey: new FormControl(''),
      appCode: new FormControl(''),
      ak: new FormControl(''),
      sk: new FormControl(''),
      description: new FormControl(''),
      iamDomain: new FormControl(''),
      iamUrl: new FormControl(''),
      iamUser: new FormControl(''),
      iamProject: new FormControl(''),
      iamPassword: new FormControl(''),
      iamAK: new FormControl(''),
      iamSK: new FormControl(''),
      verify: new FormControl('iam'),
      sgovUrl: new FormControl(''),
      credential: new FormControl(''),
      appId: new FormControl(''),
      iamAccount: new FormControl(''),
      iamSecret: new FormControl(''),
      iamEnterprise: new FormControl(''),
      scenarioUuid: new FormControl(''),
      userId: new FormControl(''),
    });
    this.changeAuthType('NO_AUTH');
  }

  ngOnInit() {
    this.authList = this.radioList.filter(item => item?.show);
    if (this.provider_id) {
      this.getModelPublisherInfoFn();
    }
  }

  backfillData(providerInfo: any) {
    this.myForm.controls.provider_name.setValue(providerInfo.provider_name);
    this.myForm.controls.provider_name_en.setValue(providerInfo.provider_name_en);
    this.myForm.controls.logo.setValue(providerInfo.logo || cdnAssetUrl('assets/model/default_model.svg'));
    this.myForm.controls.description.setValue(providerInfo.description);
    let auth_type = providerInfo.auth_configs[0].auth_type;
    this.myForm.controls.auth_type.setValue(auth_type);
    this.changeAutoType(providerInfo.auth_configs[0]);
  }

  resetControl() {
    this.myForm.controls[mapKeys.ak]?.setValidators([]);
    this.myForm.controls[mapKeys.sk]?.setValidators([]);
    this.myForm.controls[mapKeys.apikey]?.setValidators([]);
    this.myForm.controls[mapKeys.appCode]?.setValidators([]);
    this.myForm.controls[mapKeys.iamUser]?.setValidators([]);
    this.myForm.controls[mapKeys.iamProject]?.setValidators([]);
    this.myForm.controls[mapKeys.iamDomain]?.setValidators([]);
    this.myForm.controls[mapKeys.iamPassword]?.setValidators([]);
    this.myForm.controls[mapKeys.iamUrl]?.setValidators([]);
    this.myForm.controls[mapKeys.iamAK]?.setValidators([]);
    this.myForm.controls[mapKeys.iamSK]?.setValidators([]);
    this.myForm.controls[mapKeys.appId]?.setValidators([]);
    this.myForm.controls[mapKeys.credential]?.setValidators([]);
    this.myForm.controls[mapKeys.sgovUrl]?.setValidators([]);
    this.myForm.controls[mapKeys.iamAccount]?.setValidators([]);
    this.myForm.controls[mapKeys.iamSecret]?.setValidators([]);
    this.myForm.controls[mapKeys.iamEnterprise]?.setValidators([]);
    this.myForm.controls[mapKeys.scenarioUuid]?.setValidators([]);
    this.myForm.controls[mapKeys.userId]?.setValidators([]);
  }

  checkGroup(form: FormGroup | NgForm): boolean {
    if (form.invalid) {
      Object.values(form.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      const firstErrorKey = Object.keys(form.controls).find(key => form.controls[key].invalid);
      if (firstErrorKey) {
        const el = this.elementRef.nativeElement.querySelector(`[formControlName="${firstErrorKey}"], [name="${firstErrorKey}"]`);
        if (el) el.focus();
      }
      return false;
    }
    return true;
  }

  beforeUploadLogo = (file: NzUploadFile): boolean => {
    const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isJpgOrPng) {
      this.message.error(this.i18n.transform('unsupported_file_type'));
      return false;
    }
    const isLt100k = file.size! / 1024 <= 100;
    if (!isLt100k) {
      this.message.error(this.i18n.transform('unsupported_file_type_1'));
      return false;
    }

    const reader = new FileReader();
    reader.readAsDataURL(file as any);
    reader.onload = () => {
      this.myForm.controls.logo.setValue(reader.result);
      this.logoIsError = false;
      this.cdr.markForCheck();
    };
    return false;
  };

  handleAutoInfo() {
    const value = this.myForm.getRawValue();
    let auth_info = {};
    if (value.auth_type === this.API_KEY) {
      auth_info = { 'API Key': value.apikey };
    }
    if (value.auth_type === this.AK_SK || value.auth_type === this.HMAC) {
      auth_info = { ak: value.ak, sk: value.sk };
    }
    if (value.auth_type === this.APP_CODE) {
      auth_info = { 'APP Code': value.appCode };
    }

    if (value.auth_type === 'CUSTOM_APIKEY') {
      let obj = {};
      this.apiKeyAuthArgs.forEach(item => {
        obj[item.target_name] = item.auth_key;
      });
      auth_info = obj;
    }

    if (value.auth_type === 'CUSTOM_IAM') {
      auth_info = {
        'iamUrl': value.iamUrl,
        'iamDomain': value.iamDomain,
        'iamProject': value.iamProject,
      };
      let param = {};
      if (value.verify === 'iam') {
        param = { 'iamUser': value.iamUser, 'iamPassword': value.iamPassword };
      } else {
        param = { 'iamAK': value.iamAK, 'iamSK': value.iamSK };
      }
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
        'userId': value.userId,
      };
    }

    if (value.auth_type === 'SGOV') {
      auth_info = {
        'appId': value.appId,
        'credential': value.credential,
        'sgovUrl': value.sgovUrl,
        'scenarioUuid': value.scenarioUuid,
      };
    }

    return {
      provider_name: value.provider_name,
      provider_name_en: value.provider_name_en,
      description: value.description,
      logo: value.logo,
      auth_type: value.auth_type,
      auth_info: JSON.stringify(auth_info),
    };
  }

  changeAutoType(res: any) {
    this.resetControl();
    let auth_info = JSON.parse(res.auth_info);
    let auth_type = res.auth_type;

    if (Object.keys(auth_info).indexOf('API Key') > -1) {
      res.apikey = auth_info[mapKeys['API Key']];
      res.auth_type = this.API_KEY;
    } else if (Object.keys(auth_info).indexOf('ak') > -1 || auth_type === 'HMAC') {
      res.ak = auth_info[this.formKeyMap.ak];
      res.sk = auth_info[this.formKeyMap.sk];
    } else if (Object.keys(auth_info).indexOf('APP Code') > -1) {
      res.auth_type = this.APP_CODE;
      res.appCode = auth_info[mapKeys['APP Code']];
    } else if (auth_type === 'CUSTOM_APIKEY') {
      this.apiKeyAuthArgs = [];
      Object.keys(auth_info).forEach(item => {
        this.apiKeyAuthArgs.push({
          target_name: item,
          auth_key: '',
        });
      });
    } else if (auth_type === 'CUSTOM_IAM') {
      this.myForm.controls[mapKeys.iamUrl].setValue(auth_info[this.formKeyMap.iamUrl]);
      this.myForm.controls[mapKeys.iamDomain].setValue(auth_info[this.formKeyMap.iamDomain]);
      if (auth_info[this.formKeyMap.iamUser]) {
        this.myForm.controls[mapKeys.iamUser].setValue(auth_info[this.formKeyMap.iamUser]);
        this.myForm.controls[mapKeys.verify].setValue('iam');
      } else {
        this.myForm.controls[mapKeys.verify].setValue('aksk');
      }
    } else if (auth_type === 'HIS_IAM') {
      this.myForm.controls[mapKeys.iamUrl].setValue(auth_info[this.formKeyMap.iamUrl]);
      this.myForm.controls[mapKeys.iamAccount].setValue(auth_info[this.formKeyMap.iamAccount]);
      this.myForm.controls[mapKeys.iamEnterprise].setValue(auth_info[this.formKeyMap.iamEnterprise]);
      this.myForm.controls[mapKeys.scenarioUuid].setValue(auth_info[this.formKeyMap.scenarioUuid]);
      this.myForm.controls[mapKeys.userId].setValue(auth_info.userId);
    } else if (auth_type === 'SGOV') {
      this.myForm.controls[mapKeys.appId].setValue(auth_info.appId);
      this.myForm.controls[mapKeys.sgovUrl].setValue(auth_info[this.formKeyMap.sgovUrl]);
      this.myForm.controls[mapKeys.scenarioUuid].setValue(auth_info[this.formKeyMap.scenarioUuid]);
    } else {
      res.auth_type = this.NO_AUTH;
    }
    this.myForm.controls[mapKeys.auth_type].setValue(auth_type);
  }

  getModelPublisherInfoFn() {
    return this.modelManagementService.getModelPublisherInfo(this.provider_id, this.source).then(res => {
      this.backfillData(res);
    });
  }

  createPublisher() {
    const isMainValid = this.checkGroup(this.myForm);
    const isCustomValid = this.myForm.value.auth_type === 'CUSTOM_APIKEY' ? this.checkGroup(this.authkeyForm?.form) : true;

    if (!isMainValid || !isCustomValid) {
      return;
    }

    this.btnLoading = true;
    let providerInfo = this.handleAutoInfo();

    if (this.provider_id) {
      this.modelManagementService
        .updateModelProviders(this.provider_id, providerInfo)
        .then(() => {
          this.btnLoading = false;
          this.message.success(this.i18n.transform('modified_providers_successfully', { ns: I18nNamespace.MODEL_ACCESS }));
          this.close();
        })
        .catch(() => (this.btnLoading = false));
    } else {
      this.modelManagementService
        .createModelProviders(providerInfo)
        .then(() => {
          this.btnLoading = false;
          this.message.success(this.i18n.transform('providers_added_successfully', { ns: I18nNamespace.MODEL_ACCESS }));
          this.close();
        })
        .catch(() => (this.btnLoading = false));
    }
  }

  deleteLogo() {
    this.myForm.controls[mapKeys.logo].setValue('');
  }

  submit() {
    this.createPublisher();
  }

  changeAuthType(auth: string) {
    if (auth === this.NO_AUTH) {
      this.resetControl();
    }
    if (auth === this.API_KEY) {
      this.resetControl();
      this.myForm.controls[mapKeys.apikey].setValidators([Validators.required]);
    }
    if (auth === this.AK_SK || auth === this.HMAC) {
      this.resetControl();
      this.myForm.controls[mapKeys.ak].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.sk].setValidators([Validators.required]);
    }
    if (auth === this.APP_CODE) {
      this.resetControl();
      this.myForm.controls[mapKeys.appCode].setValidators([Validators.required]);
    }
    if (auth === 'CUSTOM_APIKEY') {
      this.resetControl();
      // 显式清除 apikey 的 required 校验器并立即刷新状态
      // setValidators([]) 在某些场景下未生效，使用 clearValidators 确保
      this.myForm.controls[mapKeys.apikey]?.clearValidators();
      this.myForm.controls[mapKeys.apikey]?.updateValueAndValidity({ onlySelf: true });
    }
    if (auth === 'CUSTOM_IAM') {
      this.resetControl();
      this.myForm.controls[mapKeys.iamUrl].setValidators([Validators.required, Validators.pattern(this.urlPattern)]);
      this.myForm.controls[mapKeys.iamDomain].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamProject].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamUser].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamPassword].setValidators([Validators.required]);
    }
    if (auth === 'HIS_IAM') {
      this.resetControl();
      this.myForm.controls[mapKeys.iamUrl].setValidators([Validators.required, Validators.pattern(this.urlPattern)]);
      this.myForm.controls[mapKeys.iamAccount].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamProject].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamSecret].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamEnterprise].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.scenarioUuid].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.userId].setValidators([Validators.required]);
    }
    if (auth === 'SGOV') {
      this.resetControl();
      this.myForm.controls[mapKeys.sgovUrl].setValidators([Validators.required, Validators.pattern(this.urlPattern)]);
      this.myForm.controls[mapKeys.appId].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.credential].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamEnterprise].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.scenarioUuid].setValidators([Validators.required]);
    }
    // 修复：setValidators 后刷新表单状态，避免 myForm.status 残留旧值导致 checkGroup 误判
    this.myForm.updateValueAndValidity();
  }

  public changeApi(): void {
    this.apiCollapsed = !this.apiCollapsed;
  }

  public addArgs() {
    this.apiKeyAuthArgs.push({ target_name: '', auth_key: '' });
  }

  public deleteArgs(i: number) {
    this.apiKeyAuthArgs.splice(i, 1);
  }

  public change(): void {
    this.collapsed = !this.collapsed;
  }

  changeVerifyMethod(verify: string) {
    if (verify === 'iam') {
      this.myForm.controls[mapKeys.iamUser].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamPassword].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamAK].setValidators([]);
      this.myForm.controls[mapKeys.iamSK].setValidators([]);
      this.myForm.controls[mapKeys.iamAK].setValue('');
      this.myForm.controls[mapKeys.iamSK].setValue('');
    } else {
      this.myForm.controls[mapKeys.iamUser].setValue('');
      this.myForm.controls[mapKeys.iamPassword].setValue('');
      this.myForm.controls[mapKeys.iamUser].setValidators([]);
      this.myForm.controls[mapKeys.iamPassword].setValidators([]);
      this.myForm.controls[mapKeys.iamAK].setValidators([Validators.required]);
      this.myForm.controls[mapKeys.iamSK].setValidators([Validators.required]);
    }
  }

  close(): void {
    if (this.drawerRef) {
      this.drawerRef.close();
    } else if (this.modalRef) {
      this.modalRef.destroy();
    }
  }

  dismiss(): void {
    if (this.drawerRef) {
      this.drawerRef.close();
    } else if (this.modalRef) {
      this.modalRef.destroy();
    }
  }
}
