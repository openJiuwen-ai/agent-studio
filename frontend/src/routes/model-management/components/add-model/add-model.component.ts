import { Component, ElementRef, Input, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormControl, FormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
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
import { convertModelApiUrlToBackendFormat, convertModelApiUrlToUserFormat, USER_ENV_PLACEHOLDER, USER_URL_PATTERN, USER_EMPTY_PLACEHOLDER } from '../../../../utils/model-api-url.util';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
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

  loading = false;
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
  /** IME 组合中标识 */
  private isComposing: boolean = false;
  /** 标签输入框内联错误（过长/重复提示） */
  tagInputError: string = '';
  /** 即将提交：mousedown 于确定按钮时置位，blur 定时器需放弃清空（submit 会处理） */
  private submitPending: boolean = false;
  /** 点按了 ✓/✗ 按钮（mousedown 先于 blur 触发），blur 定时器需放弃清空 */
  private tagActionPending: boolean = false;
  private static readonly TAG_MAX_LEN = 10;
  private static readonly TAG_MAX_COUNT = 5;

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
  // 占位符变量名长度上限：与环境变量配置侧 config-env-variable NAME_MAX_LENGTH 对齐（64）。
  // 占位符变量名必须能在环境管理里建成同名变量才能被解析，超长则环境管理根本无法配置同名变量，占位符永不解析。
  private readonly ENV_VAR_NAME_MAX_LENGTH = 64;
  logoIsError = false;

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
      api_url: new FormControl<string>('', {
        nonNullable: true,
        updateOn: 'blur',
        validators: [
          Validators.required,
          (control: AbstractControl) => {
            const value = (control.value as string)?.trim() || '';
            // 空占位符 {}：点击 {} 按钮未填变量名的中间态，允许保存(后端原样存储为 "{}"，
            // 等价于"尚未配置占位符"；调测/运行时 builder 侧 hasEnvPlaceholder 仅识别 ${_env...} 和 {VAR}，
            // 不会把 "{}" 当占位符也不会当合法 URL，会给出友好错误提示)。
            if (value === USER_EMPTY_PLACEHOLDER) {
              return null;
            }
            // 合法完整占位符 {VAR}：校验变量名长度
            if (USER_ENV_PLACEHOLDER.test(value)) {
              const varName = value.slice(1, -1);
              if (varName.length > this.ENV_VAR_NAME_MAX_LENGTH) {
                return {
                  placeholderNameTooLong: {
                    tiErrorMessage: this.i18n.transform('api_url_placeholder_name_too_long', { maxLength: this.ENV_VAR_NAME_MAX_LENGTH }),
                  },
                };
              }
              return null;
            }
            // 合法 http(s) URL（禁止含未转义花括号）
            if (USER_URL_PATTERN.test(value)) {
              return null;
            }
            // 其他情况一律报错（包括未闭合的 {xxx、含花括号的伪URL、非 http(s) scheme 等）
            return { invalidUrl: { tiErrorMessage: this.i18n.transform('api_url_invalid_tip') } };
          },
          Validators.maxLength(255),
        ],
      }),
      interface_protocol: new FormControl('openai', [Validators.required]),
      throttling_policy: new FormControl('none', [Validators.required]),
      is_support_stream: new FormControl('true', [Validators.required]),
      model_description: new FormControl(''),
      modelTagInputValue: new FormControl(''),
      is_public: new FormControl(false),
      is_support_close_reasoning: new FormControl(false),
    });
  }

  ngOnInit() {
    this.getApiProtocol();
    if (this.model_id) {
      this.getModelInfo();
    }
    // Belt-and-suspenders: any form value change that makes it past other handlers gets re-validated here.
    // We do NOT truncate here (we want the user to see what they typed) but we do refresh the inline error.
    this.myForm.controls.modelTagInputValue.valueChanges.subscribe((v: string) => {
      this.validateTagInput(v || '', false);
    });
  }

  /** Validate current tag input value; return true if acceptable to commit. */
  private validateTagInput(value: string, toastOnError: boolean): boolean {
    const trimmed = (value || '').trim();
    const TAG_MAX_LEN = AddModelComponent.TAG_MAX_LEN;
    if (trimmed.length > TAG_MAX_LEN) {
      const msg = this.i18n.transform('tag_length_error_tip');
      this.tagInputError = msg;
      if (toastOnError) this.message.warning(msg);
      return false;
    }
    if (trimmed.length > 0 && this.findModelTagFirstIndex(this.modelTags, 'label', trimmed) !== -1) {
      const msg = this.i18n.transform('tag_duplicate_error_tip');
      this.tagInputError = msg;
      if (toastOnError) this.message.warning(msg);
      return false;
    }
    if (this.modelTags.length >= AddModelComponent.TAG_MAX_COUNT && trimmed.length > 0) {
      const msg = this.i18n.transform('tag_count_error_tip');
      this.tagInputError = msg;
      if (toastOnError) this.message.warning(msg);
      return false;
    }
    this.tagInputError = '';
    return true;
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
    this.myForm.controls.api_url.setValue(this.convertToUserFormat(model.api_url));
    this.myForm.controls.model_type.setValue(model.model_type);
    this.myForm.controls.service_name.setValue(model.service_name);
    this.myForm.controls.model_name.setValue(model.model_name);
    this.myForm.controls.model_description.setValue(model.model_description);

    let model_protocol = model.model_type === 'RERANK' ? 'WISEAGENT' : 'openai';
    this.myForm.controls.interface_protocol.setValue(this.protocolMap[model.interface_protocol] ? model.interface_protocol : model_protocol);
    this.myForm.controls.logo.setValue(model.logo || cdnAssetUrl('assets/model/default_model_detail.svg'));
    this.myForm.controls.is_support_stream.setValue(model.is_support_stream.toString());
    const TAG_MAX_LEN = AddModelComponent.TAG_MAX_LEN;
    const TAG_MAX_COUNT = AddModelComponent.TAG_MAX_COUNT;
    const seen = new Set<string>();
    this.modelTags = model.model_tags
      ? model.model_tags
          .split(',')
          .map(item => (item || '').trim())
          .filter(l => l.length > 0)
          .filter(l => {
            if (seen.has(l)) return false;
            seen.add(l);
            return true;
          })
          .slice(0, TAG_MAX_COUNT)
          .map(item => ({ label: item.length > TAG_MAX_LEN ? item.slice(0, TAG_MAX_LEN) : item }))
      : [];
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

  // 异步回调里更新按钮 loading 后，变更检测可能不会及时作用到当前视图
  // （表现：报错后按钮一直转圈，直到用户再次与表单交互）。此处主动刷新。
  stopBtnLoading(): void {
    this.btnLoading = false;
    this.cdr.detectChanges();
  }

  createModel(modelInfo) {
    if (!this.checkGroup()) return;

    if (this.model_id) {
      this.modelManagementService
        .updateModel(this.model_id, modelInfo)
        .then(() => {
          this.stopBtnLoading();
          this.message.success(this.i18n.transform('modified_service_successfully'));
          this.close();
        })
        .catch(() => {
          this.stopBtnLoading();
        });
    } else {
      this.modelManagementService
        .createModel(modelInfo)
        .then(() => {
          this.stopBtnLoading();
          this.message.success(this.i18n.transform('added_service_successfully'));
          this.close();
        })
        .catch(() => {
          this.stopBtnLoading();
        });
    }
  }

  /** Flush any in-progress tag input when submitting the whole form.
   *  Returns true if the input can be safely ignored (empty or successfully committed), false if invalid. */
  private flushPendingTagInput(toast: boolean): boolean {
    if (!this.showModelTagInput) return true;
    const rawValue = this.myForm.getRawValue().modelTagInputValue;
    const value = (rawValue || '').trim();
    if (value.length === 0) {
      this.myForm.controls.modelTagInputValue.setValue('');
      this.showModelTagInput = false;
      this.tagInputError = '';
      return true;
    }
    if (!this.validateTagInput(value, toast)) {
      return false;
    }
    this.modelTags = [...this.modelTags, { label: value }];
    this.myForm.controls.modelTagInputValue.setValue('');
    this.showModelTagInput = false;
    this.tagInputError = '';
    return true;
  }

  handleAutoInfo() {
    const value = this.myForm.getRawValue();
    const TAG_MAX_LEN = AddModelComponent.TAG_MAX_LEN;
    const TAG_MAX_COUNT = AddModelComponent.TAG_MAX_COUNT;
    const seen = new Set<string>();
    // Build tag list from existing modelTags; defense in depth: strip empty/duplicate/over-long tags.
    // Over-long tags that slipped past UI are DROPPED here — submit() should already have blocked them.
    const safeTags = (this.modelTags || [])
      .map(t => (t?.label || '').trim())
      .filter(l => l.length > 0 && l.length <= TAG_MAX_LEN)
      .filter(l => {
        if (seen.has(l)) return false;
        seen.add(l);
        return true;
      })
      .slice(0, TAG_MAX_COUNT);
    this.modelTags = safeTags.map(l => ({ label: l }));
    const params: any = {
      provider_id: this.provider_id,
      api_url: this.convertToBackendFormat(value.api_url),
      interface_protocol: value.interface_protocol,
      is_support_function: this.modelInfo.is_support_function,
      is_support_stream: value.is_support_stream !== 'false',
      model_description: value.model_description,
      model_name: value.model_name,
      model_type: value.model_type,
      service_name: value.service_name,
      model_id: this.model_id,
      model_tags: safeTags.join(','),
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
    // Step 1: If the tag input is currently open, try to flush/validate it first.
    if (this.showModelTagInput) {
      if (!this.flushPendingTagInput(true)) {
        return;
      }
    }
    // Step 2: Validate committed tags
    const TAG_MAX_LEN = AddModelComponent.TAG_MAX_LEN;
    const TAG_MAX_COUNT = AddModelComponent.TAG_MAX_COUNT;
    const invalidTag = this.modelTags.find(t => !t.label || t.label.trim().length === 0 || t.label.length > TAG_MAX_LEN);
    if (invalidTag) {
      this.message.warning(this.i18n.transform('tag_length_error_tip'));
      return;
    }
    if (this.modelTags.length > TAG_MAX_COUNT) {
      this.message.warning(this.i18n.transform('tag_count_error_tip'));
      return;
    }

    let modelInfo = this.handleAutoInfo();
    if (!this.checkGroup()) return;

    this.btnLoading = true;

    if (this.model_id) {
      this.createModel(modelInfo);
      return;
    }

    this.modelManagementService.checkModelName({ model_name: modelInfo.model_name }).then(res => {
      if (res.exist_model_name) {
        this.message.error(this.i18n.transform('exist_model_name'));
        this.stopBtnLoading();
        return;
      }

      this.createModel(modelInfo);
    }).catch(() => {
      this.stopBtnLoading();
    });
  }

  changeModelType(type) {
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

  insertEnvPlaceholder(): void {
    const inputEl = this.elementRef.nativeElement.querySelector('[formControlName="api_url"]') as HTMLInputElement;
    if (!inputEl) return;

    const currentValue = this.myForm.controls.api_url.value || '';
    const trimmed = currentValue.trim();

    // 环境变量占位符必须是整个URL（不能内嵌），如果已有URL内容则清空并插入{}
    // 仅当输入框为空、处于未闭合占位符输入中（以{开头但无}）、已是{}、或已是完整{VAR}时，才在光标处插入
    if (trimmed === '' || (trimmed.startsWith('{') && !trimmed.includes('}')) || trimmed === USER_EMPTY_PLACEHOLDER || USER_ENV_PLACEHOLDER.test(trimmed)) {
      const start = inputEl.selectionStart || 0;
      const end = inputEl.selectionEnd || 0;
      const placeholder = '{}';
      const insertPos = start === end ? start : end;
      const newValue = currentValue.substring(0, insertPos) + placeholder + currentValue.substring(insertPos);
      this.myForm.controls.api_url.setValue(newValue);
      setTimeout(() => {
        inputEl.focus();
        const cursorPos = insertPos + 1;
        inputEl.setSelectionRange(cursorPos, cursorPos);
      }, 0);
    } else {
      // 已有普通URL内容，直接替换为{}（光标放括号内）
      this.myForm.controls.api_url.setValue('{}');
      setTimeout(() => {
        inputEl.focus();
        inputEl.setSelectionRange(1, 1);
      }, 0);
    }
  }

  /**
   * 将用户输入的{VAR}格式转换为后台存储格式${_env.plugin_url_params.VAR}
   */
  private convertToBackendFormat(userInput: string): string {
    return convertModelApiUrlToBackendFormat(userInput);
  }

  /**
   * 将后台存储格式转换为用户显示格式${_env.plugin_url_params.VAR} -> {VAR}
   */
  private convertToUserFormat(backendValue: string): string {
    return convertModelApiUrlToUserFormat(backendValue);
  }

  dismiss(): void {
    // 传 false 表示只是取消，不需要刷新
    this.drawerRef.close(false);
  }

  onCustomTagDelete(item: any): void {
    this.modelTags = this.modelTags.filter(t => t !== item);
  }

  onModelTagClick(): void {
    if (this.modelTags.length >= AddModelComponent.TAG_MAX_COUNT) {
      this.message.warning(this.i18n.transform('tag_count_error_tip'));
      return;
    }
    this.showModelTagInput = true;
    this.tagInputError = '';
    this.myForm.controls.modelTagInputValue.setValue('');
    this.refocusTagInput();
  }

  /** IME composition start */
  onCompositionStart(): void {
    this.isComposing = true;
  }

  /** IME composition end (candidate confirmed). Validate and show inline error, but do NOT auto-add. */
  onCompositionEnd(event: Event): void {
    this.isComposing = false;
    const input = event.target as HTMLInputElement;
    this.validateTagInput(input.value, false);
  }

  /** Enter key handler: commit current tag via confirmCurrentTag(). IME Enter during composition is ignored. */
  onModelTagEnter(event: Event): void {
    if (this.isComposing) return;
    event.preventDefault();
    event.stopPropagation();
    this.confirmCurrentTag();
  }

  /** ✓ button or Enter: add current tag if valid; empty input is a no-op (clear & refocus).
   *  NOTE: 不在此复位 tagActionPending —— mousedown 设置的标志需存活到 onModelTagBlur 的 150ms 定时器消费，
   *  否则随后触发的 blur 会看到 false 而错误清空输入。标志位统一由 onModelTagBlur 复位。 */
  confirmCurrentTag(): void {
    const value: string = (this.myForm.getRawValue().modelTagInputValue || '').trim();
    if (value === '') {
      this.myForm.controls.modelTagInputValue.setValue('');
      this.tagInputError = '';
      this.cdr.markForCheck();
      if (this.showModelTagInput && this.modelTags.length < AddModelComponent.TAG_MAX_COUNT) {
        this.refocusTagInput();
      }
      return;
    }
    if (this.modelTags.length >= AddModelComponent.TAG_MAX_COUNT) {
      this.message.warning(this.i18n.transform('tag_count_error_tip'));
      this.showModelTagInput = false;
      this.myForm.controls.modelTagInputValue.setValue('');
      this.tagInputError = '';
      this.cdr.markForCheck();
      return;
    }
    if (!this.validateTagInput(value, true)) {
      this.cdr.markForCheck();
      return;
    }
    this.modelTags = [...this.modelTags, { label: value }];
    this.myForm.controls.modelTagInputValue.setValue('');
    this.tagInputError = '';
    if (this.modelTags.length >= AddModelComponent.TAG_MAX_COUNT) {
      this.showModelTagInput = false;
    } else {
      this.refocusTagInput();
    }
    this.cdr.markForCheck();
  }

  /** ✗ button or blur: discard current input, close input, return to + button state. */
  cancelTagInput(): void {
    this.myForm.controls.modelTagInputValue.setValue('');
    this.showModelTagInput = false;
    this.tagInputError = '';
    this.cdr.markForCheck();
  }

  /** mousedown on ✓/✗ fires before blur — set flag so blur handler doesn't clobber the click. */
  onTagActionMouseDown(): void {
    this.tagActionPending = true;
  }

  /** Blur: treat as cancel unless a ✓/✗ click or drawer submit is in progress. */
  onModelTagBlur(): void {
    setTimeout(() => {
      if (this.tagActionPending || this.submitPending) {
        // ✓/✗ 点击或确定按钮 submit 正在处理：不清空输入，复位标志位防止泄漏。
        this.tagActionPending = false;
        this.submitPending = false;
        return;
      }
      this.cancelTagInput();
    }, 150);
  }

  /** mousedown on the drawer 确定 button — fires before blur so we can preserve pending tag input for submit(). */
  onSubmitMouseDown(): void {
    this.submitPending = true;
  }

  private refocusTagInput(): void {
    setTimeout(() => {
      const input = this.elementRef.nativeElement.querySelector('input[formControlName="modelTagInputValue"]') as HTMLInputElement | null;
      if (input) input.focus();
    }, 0);
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

  close(): void {
    // 传 true 表示操作成功，需要刷新列表
    this.drawerRef.close(true);
  }
}
