import { Component, ElementRef, Input, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormControl, FormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from '../../../../single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { I18nNamespace } from '@i18n';
import { CommonValidation } from '@shared/validation/commonValidation';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonService } from '@services/common.service';
import { HelpCenterService } from '@services/help-center.service';
import { CommonUtils } from '../../../../utils/common.util';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-add-model',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MODULES,
    NzFormModule,
    NzInputModule,
    NzRadioModule,
    NzSwitchModule,
    NzTagModule,
    NzButtonModule,
    NzIconModule,
    NzUploadModule,
    NzToolTipModule,
  ],
  templateUrl: './add-model.component.html',
  styleUrls: ['./add-model.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
  ],
})
export class AddModelComponent implements OnInit {
  @Input() model_id?: string;
  @Input() provider_id?: string;

  public lang: string = CommonUtils.getLanguage();

  get showSwitch() {
    return this.configServ.getConfigs().public_model_enabled;
  }

  modelTypeList = [
    { id: 'LLM', label: this.i18n.transform('LLM') },
    { id: 'Text-Embedding', label: this.i18n.transform('Text-Embedding') },
    { id: 'RERANK', label: this.i18n.transform('RERANK') },
    { id: 'IMAGE-TO-TEXT', label: this.i18n.transform('IMAGE-TO-TEXT') },
  ];

  modelProtocolMap = {
    LLM: [],
    'Text-Embedding': [],
    RERANK: [],
    'IMAGE-TO-TEXT': [],
  };
  protocolMap = {};

  apiProtocolOptions = [];
  apiProtocolModel = 'openai';

  btnLoading = false;

  myForm: FormGroup;
  flowControlOptions = [
    { label: this.i18n.transform('no_limit'), id: 'none' },
    { label: this.i18n.transform('times_per_second', { limit: '10' }), id: '10' },
    { label: this.i18n.transform('times_per_second', { limit: '50' }), id: '50' },
    { label: this.i18n.transform('times_per_second', { limit: '100' }), id: '100' },
    { label: this.i18n.transform('times_per_second', { limit: '200' }), id: '200' },
  ];

  showModelTagInput: boolean = false;
  modelTags: Array<any> = [];

  modelInfo = {
    is_network: false,
    is_reasoning: false,
    is_support_function: false,
    is_public: false,
    is_support_close_reasoning: false,
  };
  public isHide = true;
  public changeUrl = cdnAssetUrl;
  tagList = [
    {
      id: 'is_support_function',
      name: this.i18n.transform('tag_tool'),
      color: 'rgb(255,235,209)',
      border: 'rgb(217,105,0)',
      disIcon: this.changeUrl('assets/images/tag/dis_tool.svg'),
      icon: this.changeUrl('assets/images/tag/is_tool.svg'),
      value: false,
    },
    {
      id: 'is_reasoning',
      name: this.i18n.transform('tag_reasoning'),
      color: 'rgb(244,224,252)',
      border: 'rgb(131,47,214)',
      disIcon: this.changeUrl('assets/images/tag/dis_think.svg'),
      icon: this.changeUrl('assets/images/tag/is_think.svg'),
      value: false,
    },
    {
      id: 'is_network',
      name: this.i18n.transform('tag_network'),
      color: 'rgb(222,236,255)',
      border: 'rgb(20,118,255)',
      disIcon: this.changeUrl('assets/images/tag/dis_network.svg'),
      icon: this.changeUrl('assets/images/tag/is_network.svg'),
      value: false,
    },
  ];

  validateServiceUrlTip = ``;
  logoIsError = false;

  urlSuffixMap: Record<string, string> = {
    'LLM': '/v1/chat/completions',
    'IMAGE-TO-TEXT': '/v1/chat/completions',
    'Text-Embedding': '/v1/embeddings',
    'RERANK': '/v1/rerank',
  };
  apiUrlPlaceholder = '请完整填写路径，例如：http://{ip:port}/v1/chat/completions';

  constructor(
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private elementRef: ElementRef,
    private modelManagementService: ModelManagementService,
    private configServ: AgentConfigService,
    private commonService: CommonService,
    private helpCenterService: HelpCenterService,
    private drawerRef: NzDrawerRef,
    private message: NzMessageService,
    private cdr: ChangeDetectorRef
  ) {
    this.myForm = this.fb.group({
      service_name: new FormControl('', [
        Validators.required,
        CommonValidation.modeServiceNameVerify(this.i18n.transform('validation-name-tip2')),
        Validators.minLength(2),
        Validators.maxLength(64),
      ]),
      model_name: new FormControl('', [
        Validators.required,
        CommonValidation.modelNameVerify(this.i18n.transform('validation-name-tip3')),
        Validators.minLength(2),
        Validators.maxLength(64),
      ]),
      logo: new FormControl(cdnAssetUrl('assets/model/default_model_detail.svg')),
      model_type: new FormControl('LLM', [Validators.required]),
      api_url: new FormControl('', [
        Validators.required,
        Validators.pattern(/^(https?:\/\/)?(([a-zA-Z0-9_-]+\.)+[a-zA-Z]{2,}|\d{1,3}(\.\d{1,3}){3}|localhost)(:\d+)?(\/.*)?$/i),
        Validators.maxLength(255),
      ]),
      interface_protocol: new FormControl('openai', [Validators.required]),
      throttling_policy: new FormControl('none', [Validators.required]),
      is_support_stream: new FormControl('true', [Validators.required]),
      model_description: new FormControl(''),
      modelTagInputValue: new FormControl('', [Validators.maxLength(10)]),
      is_public: new FormControl(false),
      is_support_close_reasoning: new FormControl(false),
    });
  }

  ngOnInit() {
    this.getApiProtocol();
    if (this.model_id) {
      this.getModelInfo();
    }
  }

  beforeUpload = (file: NzUploadFile): boolean => {
    const isJpgOrPng = file.type === 'image/jpeg' || file.type === 'image/png';
    if (!isJpgOrPng) {
      this.message.error(this.i18n.transform('unsupported_file_type'));
      return false;
    }
    const isLt100K = file.size! / 1024 < 100;
    if (!isLt100K) {
      this.message.error(this.i18n.transform('file_size_exceeded'));
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

  deleteLogo() {
    this.myForm.controls.logo.setValue('');
  }

  getModelInfo() {
    this.modelManagementService.getModelInfo(this.model_id).then(res => {
      this.modelInfo = res;
      this.backfillData(res);
    });
  }

  backfillData(model) {
    this.myForm.controls.api_url.setValue(model.api_url);
    this.myForm.controls.model_type.setValue(model.model_type);
    this.myForm.controls.service_name.setValue(model.service_name);
    this.myForm.controls.model_name.setValue(model.model_name);
    this.myForm.controls.model_description.setValue(model.model_description);

    let model_protocol = model.model_type === 'RERANK' ? 'WISEAGENT' : 'openai';
    this.myForm.controls.interface_protocol.setValue(this.protocolMap[model.interface_protocol] ? model.interface_protocol : model_protocol);
    this.myForm.controls.logo.setValue(model.logo || cdnAssetUrl('assets/model/default_model_detail.svg'));
    this.myForm.controls.is_support_stream.setValue(model.is_support_stream.toString());
    this.modelTags = model.model_tags ? model.model_tags?.split(',').map(item => ({ label: item })) : [];
    this.myForm.controls.throttling_policy.setValue(model.throttling_policy ? model.throttling_policy.toString() : 'none');
    this.myForm.controls.is_public.setValue(model?.is_public ? model.is_public : false);
    this.myForm.controls.is_support_close_reasoning.setValue(model?.is_support_close_reasoning ? model.is_support_close_reasoning : false);
  }

  checkGroup(): boolean {
    if (this.myForm.invalid) {
      Object.values(this.myForm.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      const firstInvalidControlName = Object.keys(this.myForm.controls).find(key => this.myForm.controls[key].invalid);
      if (firstInvalidControlName) {
        const targetElement = this.elementRef.nativeElement.querySelector(`[formControlName="${firstInvalidControlName}"]`);
        if (targetElement) {
          targetElement.focus();
        }
      }
      return false;
    }
    return true;
  }

  createModel(modelInfo) {
    if (!this.checkGroup()) return;

    if (this.model_id) {
      this.modelManagementService
        .updateModel(this.model_id, modelInfo)
        .then(() => {
          this.message.success(this.i18n.transform('modified_service_successfully'));
          this.close();
        })
        .finally(() => {
          setTimeout(() => {
            this.btnLoading = false;
            this.cdr.markForCheck();
          }, 3000);
        });
    } else {
      this.modelManagementService
        .createModel(modelInfo)
        .then(() => {
          this.message.success(this.i18n.transform('added_service_successfully'));
          this.close();
        })
        .finally(() => {
          setTimeout(() => {
            this.btnLoading = false;
            this.cdr.markForCheck();
          }, 3000);
        });
    }
  }

  handleAutoInfo() {
    const value = this.myForm.getRawValue();
    const params: any = {
      provider_id: this.provider_id,
      api_url: value.api_url,
      interface_protocol: value.interface_protocol,
      is_support_function: this.modelInfo.is_support_function,
      is_support_stream: value.is_support_stream !== 'false',
      model_description: value.model_description,
      model_name: value.model_name,
      model_type: value.model_type,
      service_name: value.service_name,
      model_id: this.model_id,
      model_tags: this.modelTags?.map(item => item.label)?.join(','),
      throttling_policy: value.throttling_policy === 'none' ? '' : value.throttling_policy,
      is_network: this.modelInfo.is_network,
      logo: value.logo,
      is_reasoning: this.modelInfo.is_reasoning,
      is_public: value.is_public,
      is_support_close_reasoning: this.modelInfo.is_reasoning && value.is_support_close_reasoning,
    };
    return params;
  }

  submit() {
    let modelInfo = this.handleAutoInfo();
    if (!this.checkGroup()) return;

    this.btnLoading = true;

    if (this.model_id) {
      this.createModel(modelInfo);
      return;
    }

    this.modelManagementService
      .checkModelName({ model_name: modelInfo.model_name })
      .then(res => {
        if (res.exist_model_name) {
          this.message.success(this.i18n.transform('exist_model_name'));
        }
        this.createModel(modelInfo);
      })
      .catch(() => {
        this.btnLoading = false;
        this.cdr.markForCheck();
      });
  }

  changeModelType(type) {
    const suffix = this.urlSuffixMap[type] || '/v1/chat/completions';
    this.apiUrlPlaceholder = `请完整填写路径，例如：http://{ip:port}${suffix}`;
    this.apiProtocolOptions = this.modelProtocolMap[type] || [];
    if (this.apiProtocolOptions.length) {
      this.apiProtocolModel = this.apiProtocolOptions[0].value;
      this.apiProtocolOptions = [...this.apiProtocolOptions];
    } else {
      setTimeout(() => {
        if (this.apiProtocolOptions.length > 0) {
          this.apiProtocolModel = this.apiProtocolOptions[0].value;
          this.apiProtocolOptions = [...this.apiProtocolOptions];
        }
      }, 1000);
    }
  }

  changeProtocol(type) {}

  close(): void {
    // 传 true 表示操作成功，需要刷新列表
    this.drawerRef.close(true);
  }

  dismiss(): void {
    // 传 false 表示只是取消，不需要刷新
    this.drawerRef.close(false);
  }

  onCustomTagDelete(item: any): void {
    const index: number = this.modelTags.indexOf(item);
    if (index !== -1) {
      this.modelTags.splice(index, 1);
    }
  }

  onModelTagClick(): void {
    this.showModelTagInput = true;
  }

  onModelTagInputKeyup(event: any): void {
    const formValue = this.myForm.getRawValue();
    const value: string = formValue.modelTagInputValue;

    if (value.trim() === '' || value.length > 10 || this.findModelTagFirstIndex(this.modelTags, 'label', value) !== -1) {
      this.showModelTagInput = false;
      return;
    }

    this.myForm.controls.modelTagInputValue.setValue('');
    this.showModelTagInput = false;
    this.modelTags.push({ label: value });
  }

  private findModelTagFirstIndex(arr: any, key: string, value: string): number {
    if (!(arr instanceof Array)) return -1;
    return arr.findIndex((i: any) => i[key] === value);
  }

  handelTag(item) {
    this.modelInfo[item.id] = !this.modelInfo[item.id];
  }

  getApiProtocol() {
    this.modelManagementService.getInterfaceProtocoList().then(res => {
      this.handelProtocoMap(res.data);
    });
  }

  handelProtocoMap(data) {
    data.forEach(item => {
      this.protocolMap[item.protocol] = this.lang === 'zh-cn' ? item.zh_name : item.en_name;

      this.modelTypeList.forEach(model => {
        if (item.model_types.indexOf(model.id) > -1) {
          this.modelProtocolMap[model.id].push({
            value: item.protocol,
            label: this.lang === 'zh-cn' ? item.zh_name : item.en_name,
          });
        }
      });
      this.apiProtocolOptions = this.modelProtocolMap[this.myForm.controls.model_type.value] || [];
    });
  }
}
