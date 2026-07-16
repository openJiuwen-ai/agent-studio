import { ChangeDetectionStrategy, ChangeDetectorRef, Component, Input, inject, Inject } from '@angular/core';
import { MODULES } from '@shared/modules';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { PromptEditorComponent } from '@routes/prompt/prompt-editor/prompt-editor.component';
import { PromptService } from '@services/prompt.service';
import { CommonUtils } from 'src/utils/common.util';
import { IPaginationListResp } from '@interfaces/prompt/prompt-template.interface';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import PromptValidators from '@routes/prompt/share/validators/validators';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { I18nNamespace } from '@i18n';
import { VariableType } from '@interfaces/prompt/prompt-optimize-task.interface';
import { EnsureChangeTypeComponent } from '@routes/prompt/share/ensure-change-type/ensure-change-type.component';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NZ_DRAWER_DATA, NzDrawerModule, NzDrawerRef } from 'ng-zorro-antd/drawer';
@Component({
  selector: 'meta-prompt-save',
  standalone: true,
  imports: [
    MODULES,
    PromptEditorComponent,
    CdkTextareaAutosize,
    ReactiveFormsModule,
    NzInputModule,
    NzSelectModule,
    NzButtonModule,
    NzFormModule,
    NzDrawerModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  templateUrl: './prompt-save.component.html',
  styleUrl: './prompt-save.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromptSaveComponent {
  readonly drawerRef = inject(NzDrawerRef);
  @Input() isOptimize = false;
  @Input() title?: string = this.i18n.transform('save_prompt');
  @Input() promptSaveInitInfo?: {
    taskId?: string;
    promptId?: string;
    name?: string;
    desc?: string;
    type?: string;
    prompt?: string;
    tags?: Array<any>;
    industry?: any;
    variableList?: Array<{ type: VariableType; value: string }>;
  };

  public get promptMaxLength() {
    return this.configServ.getConfigs().prompt_max_length ?? 20000;
  }

  public industryList: Array<any> = [];
  public tagOptions: Array<any> = [];
  public variables: Array<{ type: VariableType; value: string }> = [];
  public initVariables: Array<{ type: VariableType; value: string }> = [];

  public isShowInserter = false;
  public promptTypeOptions: Array<any> = [
    {
      label: this.i18n.transform('text'),
      value: 'text',
    },
    {
      label: this.i18n.transform('multimodal'),
      value: 'multi',
    },
  ];
  public promptTypeSelected = this.promptTypeOptions[0].value;
  public savePromptFormLabel = {
    name: this.i18n.transform('base_name'),
    industry: this.i18n.transform('prompt_tmpl_industry_label'),
    tags: this.i18n.transform('base_label_optional'),
    desc: this.i18n.transform('base_desc_optional'),
    prompt: this.i18n.transform('prompt_optimize_task_prompt_content'),
    type: this.i18n.transform('prompt_optimize_task_prompt_type'),
  };

  public savePromptForm = this.fb.group({
    name: new FormControl(undefined, [
      Validators.required,
      PromptValidators.PatternValidator(
        /^[\u4e00-\u9fa5a-zA-Z][\u4e00-\u9fa5\w-()（）]{0,32}[\u4e00-\u9fa5a-zA-Z0-9()（）]$/,
        this.i18n.transform('input_validation_rules')
      ),
    ]),
    industry: new FormControl(undefined, [Validators.required]),
    tags: new FormControl([], []),
    desc: new FormControl(undefined, []),
    prompt: new FormControl('', [Validators.required]),
    type: new FormControl(this.promptTypeOptions[0].value, [Validators.required]),
  });
  public lang = CommonUtils.getLanguage();

  public get confirmDisabled() {
    return !!(this.savePromptForm.controls.name.errors || this.savePromptForm.controls.industry.errors || this.savePromptForm.controls.prompt.errors);
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private cdr: ChangeDetectorRef,
    private promptServ: PromptService,
    private nzModal: NzModalService,
    private configServ: AgentConfigService,
    @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {
    this.savePromptForm.valueChanges.subscribe(() => {
      this.cdr.markForCheck();
    });
  }

  ngOnInit() {
    this.listIndustry();
    this.listTags();
    this.savePromptForm.controls.name.setValue(this.promptSaveInitInfo.name);
    this.savePromptForm.controls.desc.setValue(this.promptSaveInitInfo.desc);
    this.savePromptForm.controls.prompt.setValue(this.promptSaveInitInfo.prompt);
    this.savePromptForm.controls.type.setValue(this.promptSaveInitInfo.type === 'multi' ? this.promptTypeOptions[1].value : this.promptTypeOptions[0].value);
    this.promptTypeSelected = this.savePromptForm.value.type;

    this.variables = this.promptSaveInitInfo?.variableList ?? [];
    this.initVariables = this.variables;
    this.cdr.markForCheck();
  }

  dismiss() {
    this.drawerRef.close();
  }

  public listTags() {
    const params = {
      limit: 1000,
      offset: 0,
    };
    this.promptServ.getTagList(params).subscribe({
      next: (res: IPaginationListResp) => {
        const selectedTagList = [];
        this.tagOptions = res.data.map(tag => {
          const item = {
            label: this.lang === 'en-us' ? tag.nameEn || tag.name : tag?.name,
            id: tag.id,
          };
          if (
            this.promptSaveInitInfo?.tags?.find(iTag => {
              return iTag.id === item.id;
            })
          ) {
            selectedTagList.push(item.id);
          }
          return item;
        });
        this.savePromptForm.controls.tags.setValue(selectedTagList);
      },
    });
  }

  public listIndustry() {
    this.promptServ.getIndustryList().subscribe({
      next: data => {
        this.industryList = data?.map(industry => {
          const item = {
            id: industry.id,
            label: this.lang === 'en-us' ? industry.name_en || industry.name : industry.name,
          };
          if (item.id === this.promptSaveInitInfo?.industry?.id) {
            this.savePromptForm.controls.industry.setValue(item.id);
          }
          return item;
        });
      },
    });
  }

  /**
   * 保存提示词
   * @param saveAs 是否另存为
   */
  public savePrompt(saveAs = false) {
    const prompt_template = {
      id: saveAs ? undefined : this.promptSaveInitInfo.promptId,
      name: this.savePromptForm.value.name,
      content: this.savePromptForm.value.prompt,
      description: this.savePromptForm.value.desc,
      pt_type: this.savePromptForm.value.type,
      source: 'NO_SOURCE',
      variables:
        JSON.stringify(
          this.variables.map(item => {
            return {
              name: item.value,
              type: item.type === 'text' ? 'text' : 'multi',
            };
          })
        ) || '',
      tags: this.savePromptForm.value.tags,
      task_id: this.promptSaveInitInfo.taskId,
      industry_id: this.savePromptForm.value.industry,
    };
    if (this.nzData.savePromptTemplate && typeof this.nzData.savePromptTemplate === 'function') {
      this.nzData.savePromptTemplate(prompt_template);
    }
  }

  public undateVariables(variables: any) {
    this.variables = variables;
    this.cdr.detectChanges();
  }

  public hideInserter() {
    this.isShowInserter = false;
  }

  public showInserter() {
    this.isShowInserter = !this.isShowInserter;
  }

  public handleTypeSelect(value: any) {
    const isMultiType = value === 'multi';
    const hasImageType = this.variables.some(item => item.type === 'image');

    if (isMultiType || !hasImageType) {
      this.savePromptForm.controls.type.setValue(value);
      return;
    }
    this.nzModal.create({
      nzClassName: 'ensure-change-type-modal',
      nzContent: EnsureChangeTypeComponent,
      nzClosable: false,
      nzOnOk: () => {
        this.savePromptForm.controls.type.setValue(value);
        this.cdr.markForCheck();
      },
      nzOnCancel: () => {
        this.savePromptForm.controls.type.setValue(this.promptTypeOptions[1]);
        this.promptTypeSelected = this.promptTypeOptions[1];
        this.cdr.markForCheck();
      },
    });
  }
  public validatePrompt() {
    this.savePromptForm.controls.prompt.markAsTouched();
    this.savePromptForm.controls.prompt.updateValueAndValidity();
  }

  protected readonly changeUrl = cdnAssetUrl;
  protected readonly confirm = confirm;
}
