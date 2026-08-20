import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { FormBuilder, FormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { ModelType } from '@enums/jiuwen-model.enum';
import { I18nNamespace } from '@i18n';
import { KB_DEFAULT_ICON_BASE64_STR } from '@routes/agent-center/app-knowledge/create-knowledge/default-icon-base64';
import { UploadImageComponent } from '@routes/knowledge-center/components/upload-image/upload-image.component';
import { KbUtils } from '@routes/knowledge-center/kb.utils';
import { KbConstantConfigKey } from '@routes/knowledge-center/knowledge-base.interface';
import { CreateTipModalComponent } from '@routes/platform-management/resource-management/alert-model/create-tip-modal/create-tip-modal.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { CommonUtils } from '../../../utils/common.util';
import { IDENTIFIER_OPTIONS, RAG_CHUNK_METHOD_OPTIONS, RAG_IDENTIFIER_OPTIONS } from '../knowledge.const';
import { KBRepoType, ModalType, SplitMode } from '../knowledge.types';
import { SegmentRuleComponent } from '../segment-rule/segment-rule.component';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzCardModule } from 'ng-zorro-antd/card';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzBadgeModule } from 'ng-zorro-antd/badge';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSliderModule } from 'ng-zorro-antd/slider';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzIconModule } from 'ng-zorro-antd/icon';

export interface NzButtonItem {
  text: string;
  value: any;
  disabled?: boolean;
}

@Component({
  selector: 'knowledge-form-drawer',
  templateUrl: './knowledge-form-drawer.component.html',
  styleUrls: ['./knowledge-form-drawer.component.less'],
  standalone: true,
  imports: [
    MODULES,
    FormsModule,
    ReactiveFormsModule,
    SegmentRuleComponent,
    UploadImageComponent,
    NzCardModule,
    NzFormModule,
    NzInputModule,
    NzSelectModule,
    NzButtonModule,
    NzTagModule,
    NzBadgeModule,
    NzToolTipModule,
    NzCheckboxModule,
    NzRadioModule,
    NzSliderModule,
    NzInputNumberModule,
    NzSwitchModule,
    NzIconModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
      ],
    },
    NzModalService
  ],
})
export class KnowledgeFormDrawerComponent implements OnInit {
  @Input() type: ModalType = ModalType.CREATE;

  @Input() formData: any;

  @Output() cancelForm = new EventEmitter();

  @Output() submitForm = new EventEmitter();

  @ViewChild('embeddingModelSelect') embeddingModelSelect: any;
  @ViewChild('rerankModelSelect') rerankModelSelect: any;

  defaultIcon = KB_DEFAULT_ICON_BASE64_STR;

  public form: FormGroup;

  public imageConfigOptions: Array<NzButtonItem> = [
    {
      text: this.i18n.transform('image_enable_text'),
      value: 'TEXT',
      disabled: false,
    },
    {
      text: this.i18n.transform('image_enable_image'),
      value: 'IMAGE',
      disabled: false,
    },
  ];

  public splitModeOptions: Array<NzButtonItem> = [
    {
      text: this.i18n.transform('split_mode_auto'),
      value: SplitMode.AUTO,
    },
    {
      text: this.i18n.transform('split_mode_length'),
      value: SplitMode.LENGTH,
    },
    {
      text: this.i18n.transform('split_mode_level'),
      value: SplitMode.LEVEL,
    },
  ];

  public levelSplitModeOptions: Array<NzButtonItem> = [
    {
      text: this.i18n.transform('level_mode_catalog'),
      value: SplitMode.CATALOG,
    },
    {
      text: this.i18n.transform('level_mode_rule'),
      value: SplitMode.RULE,
    },
  ];

  public combineTitleOptions: Array<NzButtonItem> = [
    {
      text: this.i18n.transform('combine_title_true'),
      value: true,
    },
    {
      text: this.i18n.transform('combine_title_false'),
      value: false,
    },
  ];

  public identifierOptions = IDENTIFIER_OPTIONS.map((item) => {
    const { value } = item;
    return {
      label: this.i18n.transform(value),
      value,
    };
  });

  public chunkMethodOptions = RAG_CHUNK_METHOD_OPTIONS.map((item) => {
    const { value } = item;
    return {
      label: this.i18n.transform(`rag_${value}`),
      tip: this.i18n.transform(`rag_${value}_tip`),
      value,
    };
  });

  public embeddingModelOptions = [];

  public rerankModelOptions = [];

  public total = 100;

  public hasOcr = false;

  public isRagFlow = false;
  public isOpenJiuwen = false;
  public isConfigLoaded = false;

  public showChunkMethod = true;

  public rerankModelLabel = this.i18n.transform('rerank_model');

  defaultModelLogo: string = cdnAssetUrl('assets/images/tag/test.svg');
  public confirmLoading = false;
  modelDescription: any[] = null;

  separatorIdsValidation = {
    tip: this.i18n.transform('segment_identifier_count_limit'),
  };

  protected readonly ModelType = ModelType;

  serviceResourceType: 'basic' | 'enterprise' | '' = '';

  constructor(
    private fb: FormBuilder,
    private knowledgeRepoServ: KnowledgeRepoService,
    private appAgentRepoServ: AppAgentRepoService,
    public i18n: I18NextEagerPipe,
    private modalService: NzModalService,
    private jiuwenModelServ: JiuwenModelService,
    public kbAbilities: KbAbilitiesService,
    private configServ: AgentConfigService,
  ) {
    this.form = this.fb.group({
      icon: [''],
      display_name: [
        '',
        [
          Validators.required,
          CommonValidation.customVerify(
            /^[A-Za-z0-9\u4e00-\u9fa5][A-Za-z0-9\u4e00-\u9fa5_-]{0,49}$/,
            this.i18n.transform('knowledge_name_validation'),
          ),
        ],
      ],
      description: ['', [Validators.required]],
      embedding_model: ['', [Validators.required]],
      rerank_model: [''],
      parse_conf: this.fb.group({
        ocr_enabled: [false],
        image_enabled: [false],
        header_footer_enabled: [false],
        catalog_enabled: [false],
        image_conf: ['IMAGE'],
      }),
      split_conf: this.fb.group({
        split_mode1: ['AUTO'],
        split_mode2: ['CATALOG'],
        rule_regex_id: [''],
        title_level: [3],
        combine_title: [true],
        merge_titles: [true],
        separator_ids: [
          [
            'period_zh',
            'period_en',
            'exclamation_mark_zh',
            'exclamation_mark_en',
            'question_mark_zh',
            'question_mark_en',
          ],
        ],
        chunk_size1: [500],
        chunk_size2: [500],
      }),
      rag_chunk_parser_conf: this.fb.group({
        chunk_method: ['naive'],
        chunk_token_num1: [512],
        chunk_token_num2: [512],
        delimiter: [['wrap_en']],
      }),
    });

    this.kbAbilities.getKbConfigWithCache().subscribe(res => {
      const url = res.configs.find(config => config.key === KbConstantConfigKey.KB_MODEL_MANAGE_URL);
      if (url?.value) {
        this.modelDescription = [
          { type: 'text', text: this.i18n.transform('ks_model_tip') },
          {
            type: 'link',
            link: { href: url.value, text: this.i18n.transform('create_ks_model') }
          },
          {
            type: 'icon',
            tip: { content: this.i18n.transform('ks_link_tip') },
            class: 'link-tip-class'
          }
        ];
      }
    });
  }

  get isEnterprise() {
    return this.serviceResourceType === 'enterprise';
  }

  get embeddingModelForm() {
    return this.form.get('embedding_model');
  }

  get rerankForm() {
    return this.form.get('rerank_model');
  }

  public get modalTitle() {
    const titles = {
      create: this.i18n.transform('create_kb'),
      edit: this.i18n.transform('modify_kb'),
      advanced: this.i18n.transform('advanced'),
    };

    return titles[this.type];
  }

  public get showCreateForm() {
    return ModalType.CREATE === this.type;
  }

  public get showEditForm() {
    return ModalType.EDIT === this.type;
  }

  public get showAdvancedForm() {
    return ModalType.ADVANCED === this.type;
  }

  public get imageEnabled() {
    return this.form.get('parse_conf.image_enabled').value;
  }

  public get splitMode1() {
    return this.form.get('split_conf.split_mode1').value;
  }

  public get splitMode2() {
    return this.form.get('split_conf.split_mode2').value;
  }

  public get showLengthConf() {
    return (
      SplitMode.LENGTH === this.splitMode1 ||
      SplitMode.LEVEL === this.splitMode1
    );
  }

  public get showLevelConf() {
    return SplitMode.LEVEL === this.splitMode1;
  }

  public get showRuleConf() {
    return SplitMode.RULE === this.splitMode2;
  }

  public get filteredSplitModeOptions() {
    if (this.isOpenJiuwen) {
      return this.splitModeOptions.filter(item => item.value === SplitMode.AUTO);
    }
    return this.splitModeOptions;
  }

  ngOnInit(): void {
    if (this.formData && this.formData.icon) {
      this.defaultIcon = this.formData.icon;
    }

    this.initDefaultOptions();
  }

  public handleChunkSizeChange(key: string) {
    const anotherKey = 'chunk_size1' === key ? 'chunk_size2' : 'chunk_size1';
    const newValue = this.form.get('split_conf.' + key).value;
    this.form.patchValue({
      split_conf: {
        [anotherKey]: newValue,
      },
    });
  }

  public handleChunkConfigChange(key: string, initKey1: string, initKey2: string) {
    const anotherKey = initKey1 === key ? initKey2 : initKey1;
    const newValue = this.form.get('rag_chunk_parser_conf.' + key).value;
    this.form.patchValue({
      rag_chunk_parser_conf: {
        [anotherKey]: newValue,
      },
    });
  }

  public chunkMethodChange(event) {
    this.showChunkMethod = event === 'naive';
  }

  public getOCRStatus() {
    this.imageConfigOptions[0].disabled = !this.hasOcr;
    if (this.hasOcr) {
      this.form.get('parse_conf.ocr_enabled').enable();
    } else {
      this.form.get('parse_conf.ocr_enabled').disable();
      this.form.get('parse_conf.image_conf').setValue('IMAGE');
    }
  }

  public handleCancel() {
    this.cancelForm.emit();
  }

  public setConfirmLoading(v: boolean) {
    this.confirmLoading = v;
  }

  public handleConfirm() {
    if (this.kbAbilities.isResourceDisabled && CommonUtils.judeg_develop_space()) {
      this.modalService.create({
        nzContent: CreateTipModalComponent,
        nzClosable: true,
        nzMaskClosable: false,
        nzClassName: 'develop_space_create_model',
      });
      return;
    }
    if (!this.isRagFlow) {
      if (['LENGTH', 'LEVEL'].includes(this.form.get('split_conf.split_mode1').value)) {
        let control = this.form.get('split_conf.separator_ids');
        control.addValidators(Validators.required);
        control.updateValueAndValidity();
      } else if (['AUTO'].includes(this.form.get('split_conf.split_mode1').value)) {
        let control = this.form.get('split_conf.separator_ids');
        control.removeValidators(Validators.required);
        control.updateValueAndValidity();
      }
    }
    let isValid = true;
    if (this.showCreateForm) {
      isValid = this.validateSpecificFields();
    } else if (this.showEditForm) {
      isValid = this.validateSpecificFields(['display_name', 'description']);
    } else if (this.showAdvancedForm) {
      isValid = this.validateSpecificFields([
        'rerank_model',
      ]);
    }
    if (!isValid) {
      return;
    }
    if (!this.isRagFlow) {
      let isSeparatorIdsValid = true;
      if (['LENGTH', 'LEVEL'].includes(this.form.get('split_conf.split_mode1').value)) {
        isSeparatorIdsValid = this.validateSpecificFields([
          'split_conf.separator_ids',
        ]);
      }
      if (!isSeparatorIdsValid) {
        return;
      }
    }
    this.submitForm.emit({
      form: this.formatOutputFormData(),
      setConfirmLoading: this.setConfirmLoading.bind(this),
    });
  }

  async getModelOptionsApi(modelType: string, idParam) {
    if (!this.isRagFlow && !this.isOpenJiuwen) {
      const { models } = await this.knowledgeRepoServ.getKnowledgeBaseUseModel({
        model_type: modelType,
        ...idParam,
      });
      return models;
    } else {
      const { data } = await this.jiuwenModelServ.getModelService(
        modelType === 'embedding' ? 'Text-Embedding' : 'RERANK',
      );
      return data?.length
        ? data.map(item => ({
          name: item.service_name,
          type: modelType,
          model_type: modelType,
          id: item.id,
        }))
        : [];
    }
  }

  public async getModelOptions(modelType: string, isLoading = false) {
    const idParam = this.formData
      ? { repo_id: this.kbAbilities.getKbId(this.formData) }
      : {};
    if (modelType === 'embedding') {
      const models = await this.getModelOptionsApi(modelType, idParam);
      this.embeddingModelOptions = models ?? [];
    } else if (modelType === 'rerank') {
      const models = await this.getModelOptionsApi(modelType, idParam);
      this.rerankModelOptions = models ?? [];
    }
  }

  private initFormGroup() {
    if (!this.formData) {
      return;
    }
    const { split_conf, embedding_model, rerank_model, parse_conf, rag_chunk_parser_conf, ...form } =
      this.formData;
    const embeddingOption = this.embeddingModelOptions.find(
      (item) => !this.isRagFlow ? embedding_model === item.name : embedding_model === item.id,
    ) || (!this.isRagFlow ? { name: embedding_model, type: 'embedding' } : {});
    const rerankOption = this.rerankModelOptions.find(
      (item) => !this.isRagFlow ? rerank_model === item.name : rerank_model === item.id,
    ) || (!this.isRagFlow ? { name: rerank_model, type: 'rerank' } : {});
    const { split_mode, chunk_size, ...other } = split_conf || {};
    let split_mode1 = split_mode;
    let split_mode2 = SplitMode.CATALOG;
    if ([SplitMode.CATALOG, SplitMode.RULE].includes(split_mode)) {
      split_mode1 = SplitMode.LEVEL;
      split_mode2 = split_mode;
    }
    let formValue: any = {
      ...form,
      embedding_model: embeddingOption,
      rerank_model: rerankOption,
      split_conf: {
        ...other,
        split_mode1,
        split_mode2,
        chunk_size1: chunk_size,
        chunk_size2: chunk_size,
      },
      parse_conf: {
        ocr_enabled: parse_conf?.ocr_enabled ?? false,
        image_enabled: parse_conf?.image_enabled ?? false,
        header_footer_enabled: parse_conf?.header_footer_enabled ?? false,
        catalog_enabled: parse_conf?.catalog_enabled ?? false,
        image_conf: parse_conf?.image_conf ?? 'IMAGE',
      },
    };
    if (rag_chunk_parser_conf) {
      const { chunk_token_num, chunk_method, ...otherRagConfig } = rag_chunk_parser_conf;
      formValue.rag_chunk_parser_conf = {
        chunk_token_num1: chunk_token_num,
        chunk_token_num2: chunk_token_num,
        chunk_method: chunk_method ?? 'naive',
        ...otherRagConfig,
      };
    }
    this.form.patchValue(formValue);
    if (this.formData?.repo_type === KBRepoType.SHARE) {
      this.form.get('rerank_model').disable();
    }
  }

  private validateSpecificFields(fieldNames?: string[]) {
    if (!fieldNames) {
      Object.values(this.form.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      return this.form.valid;
    }
    let isValid = true;
    fieldNames.forEach((fieldName) => {
      const control = this.form.get(fieldName);
      if (!control) {
        return;
      }
      control.markAsDirty();
      control.updateValueAndValidity({ onlySelf: true });
      isValid = isValid && !control.invalid;
    });
    return isValid;
  }

  private formatOutputFormData() {
    const { split_conf, embedding_model, rerank_model, icon, rag_chunk_parser_conf, ...form } =
      this.form.value;
    const {
      split_mode1,
      split_mode2,
      chunk_size1,
      separator_ids,
      combine_title,
      merge_titles,
      rule_regex_id,
      title_level,
    } = split_conf;
    const split_mode =
      SplitMode.LEVEL === split_mode1 ? split_mode2 : split_mode1;
    form.parse_conf.ocr_enabled = form.parse_conf.ocr_enabled || false;
    let temp: any = {
      split_mode,
    };
    if (icon && icon !== this.formData?.icon) {
      form.icon = icon;
    }
    if (embedding_model) {
      const { type, name, desc, url, id } = embedding_model;
      form.embedding_model = {
        type,
        name,
        detail: desc,
        url,
        id,
      };
    }
    if (rerank_model) {
      const { type, name, desc, url, id } = rerank_model;
      form.rerank_model = {
        type,
        name,
        detail: desc,
        url,
        id,
      };
    }
    if (SplitMode.LENGTH === split_mode) {
      temp = {
        ...temp,
        separator_ids,
        chunk_size: chunk_size1,
      };
    } else if (SplitMode.RULE === split_mode) {
      temp = {
        ...temp,
        rule_regex_id,
        title_level,
        combine_title,
        merge_titles,
        separator_ids,
        chunk_size: chunk_size1,
      };
    } else if (SplitMode.CATALOG === split_mode) {
      temp = {
        ...temp,
        title_level,
        combine_title,
        merge_titles,
        separator_ids,
        chunk_size: chunk_size1,
      };
    }
    if (this.isRagFlow) {
      const { chunk_token_num1, chunk_token_num2, ...otherConfig } = rag_chunk_parser_conf;
      let rankChunkParserConf: any = {
        chunk_method: rag_chunk_parser_conf.chunk_method,
      };
      if (rankChunkParserConf.chunk_method === 'naive') {
        rankChunkParserConf = {
          chunk_token_num: chunk_token_num1 ? chunk_token_num1 : chunk_token_num2,
          ...otherConfig,
        };
      }
      const params: any = {
        description: form.description,
        display_name: form.display_name,
        embedding_model: form.embedding_model,
        rag_chunk_parser_conf: rankChunkParserConf,
        rerank_model: form.rerank_model,
      };
      if (form?.icon) {
        params.icon = form.icon;
      }
      return params;
    }
    return {
      ...form,
      split_conf: temp,
    };
  }

  private async initDefaultOptions() {
    try {
      const { ocr_enable, knowledge_source } =
        await this.appAgentRepoServ.getConfigs();
      this.hasOcr = ocr_enable;
      this.isRagFlow = knowledge_source === 'AgentBaseRag';

      try {
        const defaultConfig = await this.knowledgeRepoServ.getKnowledgeDefaultConfigDetail(
          'default_lakesearch_inside_connection_id',
        );
        if (this.configServ.openjiuwenKbEnable() && defaultConfig?.knowledge_base_connection_detail?.connector_id === 'OpenjiuwenInside') {
          this.isOpenJiuwen = true;
        }
      } catch (e) {
        // 默认配置查询失败时不影响创建流程
      }
      this.isConfigLoaded = true;

      const rerankControl = this.form.get('rerank_model');
      if (!this.isRagFlow) {
        rerankControl.setValidators([Validators.required]);
      } else {
        rerankControl.clearValidators();
      }
      rerankControl.updateValueAndValidity();

      if (this.isRagFlow) {
        this.rerankModelLabel = this.i18n.transform('ranking_model_optional');
        this.identifierOptions = RAG_IDENTIFIER_OPTIONS.map((item) => {
          const { value } = item;
          return {
            label: this.i18n.transform(value),
            value,
          };
        });
      }
      await Promise.all([
        this.getModelOptions('embedding'),
        this.getModelOptions('rerank'),
      ]);
    } finally {
      this.initFormGroup();
      this.getOCRStatus();
    }
  }

  onImageChanged(file: File) {
    KbUtils.readFileAsBase64(file).then(res => {
      this.form.get('icon').setValue(res);
    })
  }
}
