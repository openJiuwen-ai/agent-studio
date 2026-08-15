import { ChangeDetectionStrategy, ChangeDetectorRef, Component, ViewEncapsulation } from '@angular/core';
import { HeaderComponent } from '@routes/prompt/prompt-optimize-task-config/header/header.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { FooterComponent } from '@routes/prompt/prompt-optimize-task-config/footer/footer.component';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { FormBuilder, FormControl, Validators } from '@angular/forms';
import { NzDatePickerModule } from 'ng-zorro-antd/date-picker';
import { NzModalService } from 'ng-zorro-antd/modal';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { UseCasesComponent } from '@routes/prompt/prompt-optimize-task-config/use-cases/use-cases.component';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { PromptEditorComponent } from '@routes/prompt/prompt-editor/prompt-editor.component';
import { PromptOptimizeService, UseCaseService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import {
  IVariable,
  OptimizeTask,
  OptimizeTaskDraft,
  OptimizeUseCase,
  PromptExampleItem,
  TaskType,
  VariableType,
} from '@interfaces/prompt/prompt-optimize-task.interface';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { debounceTime, Subscription } from 'rxjs';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { PromptService } from '@services/prompt.service';
import { EnsureChangeTypeComponent } from '@routes/prompt/share/ensure-change-type/ensure-change-type.component';
import { ConfigConstants } from '@routes/prompt/prompt-optimize-task-config/constant';
import { ModelType } from '@enums/versatile-model.enum';
import { VariableService } from '@services/agent-center/prompt-optimize-task/prompt-editor.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonUtils } from 'src/utils/common.util';
import { DebounceDecorators } from '@shared/decorators/debouncing-throttling.directive';
@Component({
  selector: 'meta-prompt-optimize-task-config',
  standalone: true,
  imports: [HeaderComponent, FooterComponent, MODULES, PromptEditorComponent, UseCasesComponent, LLMSelectComponent, NzDatePickerModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  templateUrl: './prompt-optimize-task-config.component.html',
  styleUrls: ['./prompt-optimize-task-config.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  encapsulation: ViewEncapsulation.None,
})
export class PromptOptimizeTaskConfigComponent {
  public lang: string = CommonUtils.getLanguage();
  public exampleUrl: string = '';
  public optimizeHelpUrl: string = '';
  public modelType;
  public activeStep = 0;
  public isShowInserter = false;
  public draft: OptimizeTask;
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
  promptTypeSelected = this.promptTypeOptions[0].value;
  // 应用对象类型
  public objectApplyTypeOptions: Array<any> = [
    {
      label: this.i18n.transform('base_model'),
      value: 'model',
    },
    {
      label: this.i18n.transform('base_agent'),
      value: 'agent',
      disabled: true,
      tip: this.i18n.transform('feature_not_yet_open'),
    },
  ];
  public promptExample: Array<PromptExampleItem> = ConfigConstants.zh_cn.promptExample;
  public basicInfoFormLabel = {
    taskName: this.i18n.transform('prompt_optimize_task_name'),
    type: this.i18n.transform('prompt_optimize_task_prompt_type'),
    desc: this.i18n.transform('prompt_optimize_task_desc'),
    prompt: this.i18n.transform('prompt_optimize_task_prompt_content'),
    theObjectToApply: this.i18n.transform('prompt_optimize_task_the_object_to_apply'),
  };
  public basicInfoForm = this.fb.group({
    taskName: new FormControl('', [Validators.required, Validators.maxLength(64)]),
    type: new FormControl(this.promptTypeOptions[0].value, [Validators.required]),
    desc: new FormControl('', [Validators.required]),
    prompt: new FormControl('', [Validators.required]),
    theObjectToApply: new FormControl('', [Validators.required]),
    theTypeOfObjectToApply: new FormControl('model', [Validators.required]),
  });

  public taskTypeOptions: Array<any> = [
    {
      title: this.i18n.transform('subjective_task'),
      value: TaskType.SUBJECTIVE,
      content: this.i18n.transform('subjective_task_desc'),
      example: this.i18n.transform('subjective_task_example'),
    },
    {
      title: this.i18n.transform('objective_task'),
      value: TaskType.OBJECTIVE,
      content: this.i18n.transform('objective_task_desc'),
      example: this.i18n.transform('objective_task_example'),
    },
  ];
  public numberOfPromptExamplesItems: Array<{ text: string }> = [
    {
      text: '0',
    },
    {
      text: '1',
    },
    {
      text: '2',
    },
    {
      text: '3',
    },
    {
      text: '4',
    },
    {
      text: '5',
    },
  ];
  public basicSettingsFormLabel = {
    executionTime: this.i18n.transform('prompt_optimize_task_execution_time'),
    model: this.i18n.transform('prompt_optimize_task_model'),
    targetAccuracy: this.i18n.transform('prompt_optimize_task_target_accuracy'),
    maximumRound: this.i18n.transform('prompt_optimize_task_maximum_round'),
    algorithm: this.i18n.transform('prompt_optimize_task_algorithm'),
    numberOfPromptExamples: this.i18n.transform('prompt_optimize_task_number_of_prompt_examples'),
    taskType: this.i18n.transform('prompt_optimize_task_type'),
  };
  public basicSettingsForm = this.fb.group({
    executionTime: new FormControl(new Date(), [Validators.required]),
    executionTimeMode: new FormControl(true, []),
    model: new FormControl('', [Validators.required]),
    targetAccuracy: new FormControl(60, [Validators.required]),
    maximumRound: new FormControl(1, [Validators.required]),
    numberOfPromptExamples: new FormControl(this.numberOfPromptExamplesItems[1], [Validators.required]),
    taskType: new FormControl(this.taskTypeOptions[0].value, [Validators.required]),
  });

  public isShowAdvancedSettings = false;
  public advancedSettingsFormLabel = {
    scoringCriteria: this.i18n.transform('prompt_optimize_task_scoring_criteria'),
    backgroundPrompt: this.i18n.transform('prompt_optimize_task_background_prompt'),
  };
  public backgroundPromptPlaceholder = ConfigConstants.zh_cn.backgroundPromptPlaceholder;
  public scoringCriteriaPlaceholder = ConfigConstants.zh_cn.scoringCriteriaPlaceholder;
  public advancedSettingsForm = this.fb.group({
    scoringCriteria: new FormControl(''),
    backgroundPrompt: new FormControl(''),
    enableScoringCriteria: new FormControl(false),
  });

  // 实际存储变量
  public variableList: Array<IVariable> = [];
  // 初始化控制
  public initVariableList: Array<IVariable> = [];
  public useCases: Array<any> = [];

  public pageInfo = {
    page: 1,
    pageSize: 10,
    total: 0,
  };

  public isInit = false;
  public variablesInit = false;
  public taskId: string;

  public promptId: string;
  public minExecutionTime: Date;
  public HWCloudTopHeight: number = 0;

  public variant: 'compact' | 'simple' | '常规' = 'compact';

  private taskNameErrorShown: 'required' | 'maxlength' | null = null;

  public get footerDisabled(): string {
    if (this.activeStep === 0) {
      const taskNameError = this.getTaskNameError();
      if (taskNameError) {
        return this.getTaskNameErrorMessage(taskNameError);
      }
      if (!this.basicInfoForm.controls.desc.valid) {
        return this.i18n.transform('prompt_optimize_task_config_2');
      }
      if (!this.basicInfoForm.controls.theObjectToApply.valid) {
        return this.i18n.transform('prompt_optimize_task_config_3');
      }
      if (!this.basicInfoForm.controls.prompt.valid) {
        return this.i18n.transform('prompt_optimize_task_config_4');
      }
      if (this.useCases.length < 1) {
        return this.i18n.transform('prompt_optimize_task_config_5');
      }
      return '';
    } else if (this.activeStep === 1) {
      if (!this.basicSettingsForm.controls.model.valid) {
        return this.i18n.transform('prompt_optimize_task_config_6');
      }
      return '';
    } else {
      return '';
    }
  }

  private getTaskNameError(): 'required' | 'maxlength' | null {
    const taskNameControl = this.basicInfoForm.controls.taskName;
    if (taskNameControl.hasError('required')) {
      return 'required';
    }
    if (taskNameControl.hasError('maxlength')) {
      return 'maxlength';
    }
    return null;
  }

  private getTaskNameErrorMessage(error: 'required' | 'maxlength'): string {
    const messageKey =
      error === 'required' ? 'prompt_optimize_task_config_1' : 'prompt_optimize_task_config_name_max_length';
    return this.i18n.transform(messageKey);
  }

  public get promptMaxLength() {
    return this.configServ.getConfigs().prompt_max_length ?? 20000;
  }
  isSpinning = false;

  private isEdit: boolean = false;
  constructor(
    private variableService: VariableService,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private promptOptimizeService: PromptOptimizeService,
    private promptService: PromptService,
    private useCaseService: UseCaseService,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private router: Router,
    private nzModal: NzModalService,
    private configServ: AgentConfigService
  ) {}

  ngOnInit() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    // 图片国际化
    if (this.lang === 'zh-cn') {
      this.exampleUrl = this.changeUrl('assets/prompt/optimize-example_zh.svg');
      this.optimizeHelpUrl = this.changeUrl('assets/prompt/optimize-help_zh.svg');
    } else {
      this.exampleUrl = this.changeUrl('assets/prompt/optimize-example_en.svg');
      this.optimizeHelpUrl = this.changeUrl('assets/prompt/optimize-help_en.svg');
      this.promptExample = ConfigConstants.en_us.promptExample;
      this.scoringCriteriaPlaceholder = ConfigConstants.en_us.scoringCriteriaPlaceholder;
      this.backgroundPromptPlaceholder = ConfigConstants.en_us.backgroundPromptPlaceholder;
    }
    const path = this.route.snapshot.url.map(segment => segment.path);
    // 检查最后一段是否为 'edit',如果是，则加载已有数据
    if (path.length > 0 && path[path.length - 1] === 'edit') {
      this.isEdit = true;
      this.route.queryParams.subscribe(queryParams => {
        this.taskId = queryParams.id;
        this.loadTaskDetail().then(() => {
          setTimeout(() => {
            // 确保回写数据完成后再开启监听，避免触发不必要的保存操作
            this.isInit = true;
            this.variablesInit = true;
            this.enableAutoSave();
          }, 2000);
        });
        this.loadUseCases();
      });
    } else {
      // 从query获取promptId
      this.promptId = this.route.snapshot.queryParams.prompt_id;
      if (this.promptId) {
        // 优化原有提示词
        this.loadFromTemplate().then(() => {
          setTimeout(() => {
            // 确保回写数据完成后再开启监听，避免触发不必要的保存操作
            this.isInit = true;
            // 新建任务回显数据后尝试保存一次
            this.saveDraft();
            this.enableAutoSave();
          }, 2000);
        });
      } else {
        this.isInit = true;
        this.variablesInit = true;
        this.enableAutoSave();
      }
    }
  }

  ngOnDestroy(): void {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
    this.autoSaveSubscription.forEach(subscription => {
      subscription.unsubscribe();
    });
  }

  private autoSaveSubscription: Subscription[] = [];

  private enableAutoSave() {
    // 监听内容修改
    this.autoSaveSubscription.push(
      this.basicInfoForm.valueChanges.pipe(debounceTime(1000)).subscribe(value => {
        if (!this.isInit) {
          return;
        }
        this.saveDraft();
      })
    );

    this.autoSaveSubscription.push(
      this.basicSettingsForm.valueChanges.pipe(debounceTime(1000)).subscribe(value => {
        if (!this.isInit) {
          return;
        }
        this.saveDraft();
      })
    );
    this.autoSaveSubscription.push(
      this.advancedSettingsForm.valueChanges.pipe(debounceTime(1000)).subscribe(value => {
        if (!this.isInit) {
          return;
        }
        this.saveDraft();
      })
    );
  }

  disabledDate = (current: Date): boolean => {
    return current < new Date();
  };

  public handleNextStep() {
    this.activeStep += 1;

    // initVariableList 用于初始化编辑器内部变量类型,只在初始化时使用一次,只可在编辑器初始化之前更新,后续不可更改
    // 点击下一步时,编辑器实例被注销,回到上一步时重新初始化
    // 所以点击下一步时需要用当前变量列表更新initVariableList
    this.initVariableList = this.variableList;

    setTimeout(() => {
      // 大部分情况下1.5秒足够
      const temp = this.basicSettingsForm.value.model;
      this.basicSettingsForm.controls.model.setValue('');
      this.basicSettingsForm.controls.model.setValue(temp);
      this.cdr.detectChanges();
    }, 1500);
  }

  public handlePreviousStep() {
    this.activeStep -= 1;
    setTimeout(() => {
      const temp = this.basicInfoForm.value.theObjectToApply;
      this.basicInfoForm.controls.theObjectToApply.setValue('');
      this.basicInfoForm.controls.theObjectToApply.setValue(temp);
      this.cdr.detectChanges();
    }, 1500);
  }

  public handleConfirm() {
    this.isSpinning = true;
    this.promptOptimizeService
      .createTask(this.taskId)
      .then(res => {
        MessageComponent.showSuccess(this.i18n.transform('task_create_success'));
        StorageService.setSessionStorage('activeTab', '1');
        this.router.navigate(['/home/agent-center/library-home'], {
          state: {
            activeTab: 1,
          },
          queryParams: {
            tabId: 'prompt',
          },
        });
      })
      .finally(() => {
        this.isSpinning = false;
      });
  }

  public showInserter() {
    this.isShowInserter = !this.isShowInserter;
  }

  public hideInserter() {
    this.isShowInserter = false;
  }

  public handleApplyObjectChange(value: any) {
    this.basicInfoForm.controls.theObjectToApply.setValue(value.modelInfo.id);
  }

  public handleTypeSelect(value: any) {
    const isMultiType = value === 'multi';
    const hasImageType = this.variableList.some(item => item.type === 'image');
    if (isMultiType) {
      this.modelType = ModelType.IMAGE_TO_TEXT;
    }
    if (isMultiType || !hasImageType) {
      this.basicInfoForm.controls.type.setValue(value);
      return;
    }
    const thisNzModal: any = this.nzModal.create({
      nzContent: EnsureChangeTypeComponent,
      nzWidth: '700px',
    });
    const instance = thisNzModal.getContentComponent();
    instance.ensure.subscribe((res) => {
      if(res){
        this.basicInfoForm.controls.type.setValue(value);
        this.modelType = ModelType.LLM;
        this.cdr.markForCheck();
      }else{
        this.basicInfoForm.controls.type.setValue(this.promptTypeOptions[1].value);
        this.promptTypeSelected = this.promptTypeOptions[1].value;
        this.cdr.markForCheck();
      }
    });
  }

  public scrollToEditor() {
    setTimeout(() => {
      // 只在第一步时滚动到编辑器
      if (this.activeStep === 0 && this.basicInfoForm.value.prompt.trim() === '') {
        const editorElement = document.querySelector('.prompt-editor') as HTMLElement;
        if (editorElement && editorElement.offsetParent !== null) {
          const basicInfoContainer = document.querySelector('.basic-info') as HTMLElement;
          if (basicInfoContainer) {
            const rect = editorElement.getBoundingClientRect();
            const containerRect = basicInfoContainer.getBoundingClientRect();
            const relativeTop = rect.top - containerRect.top + basicInfoContainer.scrollTop - 20;

            basicInfoContainer.scrollTo({
              top: relativeTop,
              behavior: 'smooth',
            });
          }
        }
      }
    }, 100);
  }

  public handleExecuteModelChange(value: any) {
    this.basicSettingsForm.controls.model.setValue(value.modelInfo.id);
  }

  public handleTargetAccuracyChange() {
    this.basicSettingsForm.controls.targetAccuracy.setValue(this.basicSettingsForm.value.targetAccuracy);
  }

  public handleMaxRoundChange() {
    setTimeout(() => {
      const value = this.basicSettingsForm.value.maximumRound;
      this.basicSettingsForm.controls.maximumRound.setValue(null);
      this.basicSettingsForm.controls.maximumRound.setValue(value);
    }, 0);
  }

  public updateVariables(variables: IVariable[]) {
    if (!this.variablesInit) {
      // 变量处于初始化过程中，不更新
      return;
    }
    this.variableList = variables.filter(item => item.value.trim() !== '');
    this.variableService.setVariables(this.variableList);
    this.cdr.detectChanges();
    if (this.isInit) {
      this.saveDraft();
    }
  }

  protected readonly changeUrl = cdnAssetUrl;

  /**
   * 构建草稿数据
   */
  public buildDraftData(): OptimizeTaskDraft {
    return {
      promptId: this.promptId,
      name: this.basicInfoForm.value.taskName || '',
      desc: this.basicInfoForm.value.desc || '',
      execTime: this.basicSettingsForm.value.executionTimeMode
        ? (this.basicSettingsForm.value.executionTime?.getTime()?.toString() ?? '')
        : Date.now().toString(),
      ptType: this.basicInfoForm.value.type || '',
      ptText: this.basicInfoForm.value.prompt || '',
      ptVars:
        JSON.stringify([
          ...this.variableList.map(item => {
            return {
              name: item.value,
              type: item.type === 'text' ? 'text' : 'multi',
            };
          }),
          {
            name: 'AGENT_BUILDER_PROMPT_OUTPUT',
            type: 'text',
          },
        ]) || '',
      ptObject: {
        model: this.basicInfoForm.value.theObjectToApply || '',
        exec_type: this.basicInfoForm.value.theTypeOfObjectToApply || '',
      },
      assitantObject: {
        model: this.basicSettingsForm.value.model || '',
        exec_type: 'model',
      },
      maxIterNum: this.basicSettingsForm.value.maximumRound || 1,
      targetAcc: '1',
      showCaseNum: parseInt(this.basicSettingsForm.value.numberOfPromptExamples.text) ?? 1,
      targetType: this.basicSettingsForm.value.taskType || '',
      // 评分标准可关闭
      scoreStandard: this.advancedSettingsForm.value.enableScoringCriteria ? this.advancedSettingsForm.value.scoringCriteria : '',
      // 多模态不支持背景知识
      backKnowledge: this.basicInfoForm.value.type === 'text' ? this.advancedSettingsForm.value.backgroundPrompt : '',
    } as OptimizeTaskDraft;
  }

  /**
   * 上传单条用例
   * @param useCase
   */
  public uploadOneUseCase(useCase: OptimizeUseCase) {
    this.promptOptimizeService.uploadOneUseCase(this.taskId, useCase).then(res => {
      this.loadUseCases();
    });
  }

  /**
   * 批量上传用例,只有点击示例时使用
   * @param useCases
   */
  public uploadUseCases(useCases: OptimizeUseCase[]) {
    this.promptOptimizeService
      .uploadUseCases(this.taskId, useCases)
      .then(res => {
        if (this.isEdit) {
          // 编辑时上传完成后重新加载数据
          this.loadUseCases();
        } else {
          // 新建时上传完成后跳转到编辑
          this.router.navigate(['/home/prompt/optimize/edit'], {
            queryParams: {
              id: this.taskId,
            },
          });
        }
      })
      .finally(() => {
        this.isInit = true;
      });
  }

  public updateOneUseCase(useCase: OptimizeUseCase) {
    this.promptOptimizeService.updateOneUseCase(this.taskId, useCase).then(res => {
      this.loadUseCases();
    });
  }

  public deleteOneUseCase(id: string) {
    this.promptOptimizeService.deleteOneUseCase(this.taskId, id).then(res => {
      this.loadUseCases();
    });
  }

  /**
   * 通过文件导入用例
   * @param file
   */
  public handleImportUseCaseByFile(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    this.promptOptimizeService.uploadUseCaseByFile(this.taskId, formData).then(res => {
      if (res.code === 200) {
        this.useCaseService.closeImportModal();
        this.loadUseCases();
      } else {
        this.useCaseService.pushErrorMessages(res.data || res.message);
      }
    });
  }

  public async loadFromTemplate() {
    this.isSpinning = true;
    const params = {
      limit: 1,
      offset: 0,
      template_name: '',
      template_id: this.promptId,
      content: '',
      tag_list: [],
      industry_list: [],
    };

    const res = await this.promptService.getPromptTemplateListAsync(params);
    if (res.count) {
      const template = res.data[0];
      try {
        this.variableList = JSON.parse(template?.variables || '[]').map(item => {
          return {
            type: item.type === 'text' ? 'text' : 'image',
            value: item.name,
          };
        });
        this.initVariableList = this.variableList;
        this.cdr.markForCheck();
      } catch (e) {
        this.variableList = [];
        this.initVariableList = [];
      }
      this.variableService.setVariables(this.variableList);
      this.basicInfoForm.patchValue({
        taskName: template.template_name,
        desc: template.description,
        type: (template.pt_type ?? 'text') === 'text' ? this.promptTypeOptions[0].value : this.promptTypeOptions[1].value,
      });
      // 修改表单后，数据还未同步给组件，导致进行提示词解析时缺少参数，类型解析错误，需要强制同步
      this.cdr.detectChanges();
      // 同步完成后，变量初始化完成
      this.variablesInit = true;
      this.basicInfoForm.controls.prompt.setValue(template.content);
      this.promptTypeSelected = this.basicInfoForm.value.type;
    }
    this.isSpinning = false;
  }

  public async loadTaskDetail(): Promise<void> {
    this.isSpinning = true;
    const res = await this.promptOptimizeService.TaskDetail(this.taskId);
    this.draft = res.data;
    this.initDraft(this.draft);
    this.isSpinning = false;
  }

  public loadUseCases(page = 1, pageSize = 10) {
    this.promptOptimizeService.listUseCase(this.taskId, page, pageSize).then(res => {
      this.useCases =
        res?.data?.list?.map((item: { content: string; id: any }) => {
          // 数组转对象
          const content = {};
          JSON.parse(item.content).forEach((useCase: { name: string; type: string; content: string }) => {
            content[useCase.name] = useCase.content;
          });

          return {
            id: item.id,
            content: content,
          };
        }) ?? [];
      this.pageInfo = {
        page: res.data?.pageNum ?? 1,
        pageSize: res.data?.pageSize ?? this.pageInfo.pageSize,
        total: res.data?.total ?? 0,
      };
      this.cdr.detectChanges();
    });
  }

  public initDraft(draft: OptimizeTask) {
    this.promptId = draft.prompt_id;
    // 确保变量和提示词类型放在提示词前面,避免提示词模板变量渲染错误
    this.variableList = draft.pt_vars
      .filter(item => item.name !== 'AGENT_BUILDER_PROMPT_OUTPUT' && item.name.trim() !== '')
      .map(item => {
        return {
          type: item.type === 'text' ? VariableType.TEXT : VariableType.IMAGE,
          value: item.name,
        };
      });
    this.basicInfoForm.controls.type.setValue(this.promptTypeOptions.find(item => item.value === draft.pt_type).value);
    this.variableService.setVariables(this.variableList);
    this.initVariableList = this.variableList;
    this.basicInfoForm.controls.taskName.setValue(draft.name);
    this.basicInfoForm.controls.desc.setValue(draft.desc);
    this.basicInfoForm.controls.prompt.setValue(draft.pt_text);

    this.promptTypeSelected = this.promptTypeOptions.find(item => item.value === draft.pt_type).value;
    this.basicInfoForm.controls.theObjectToApply.setValue(draft.pt_model_config.model);
    this.basicInfoForm.controls.theTypeOfObjectToApply.setValue(this.objectApplyTypeOptions.find(item => item.value === draft.pt_model_config.exec_type).value);
    this.basicSettingsForm.controls.model.setValue(draft.exec_object_config.model);

    this.basicSettingsForm.controls.executionTime.setValue(draft.exec_time ? new Date(draft.exec_time) : null);
    if (this.basicSettingsForm.value.executionTime.getTime() < Date.now()) {
      this.basicSettingsForm.controls.executionTimeMode.setValue(false);
    }
    this.basicSettingsForm.controls.maximumRound.setValue(draft.max_iter_num);
    this.basicSettingsForm.controls.targetAccuracy.setValue(draft.target_acc * 100);
    this.basicSettingsForm.controls.numberOfPromptExamples.setValue(
      this.numberOfPromptExamplesItems.find(item => item.text === draft.show_case_num.toString())
    );
    this.basicSettingsForm.controls.taskType.setValue(
      this.taskTypeOptions.find(item => item.value === draft.target_type)?.value ?? this.taskTypeOptions[0].value
    );
    if (draft.score_standard.trim() !== '') {
      this.advancedSettingsForm.controls.enableScoringCriteria.setValue(true);
      this.advancedSettingsForm.controls.scoringCriteria.setValue(draft.score_standard);
    } else {
      this.advancedSettingsForm.controls.enableScoringCriteria.setValue(false);
    }

    this.advancedSettingsForm.controls.backgroundPrompt.setValue(draft.back_knowledge);
    setTimeout(() => {
      // 处理模型选择器加载数据时延
      this.basicInfoForm.controls.theObjectToApply.setValue(draft.pt_model_config.model);
      this.basicSettingsForm.controls.model.setValue(draft.exec_object_config.model);
      this.cdr.detectChanges();
    }, 1000);
  }

  public handlePageChange(pageInfo: { page: number; pageSize: number }) {
    this.loadUseCases(pageInfo.page, pageInfo.pageSize);
  }

  public handleExampleClick(example: PromptExampleItem) {
    this.isInit = false;
    this.initVariableList = example.useCases[0].map(item => {
      return {
        type: item.type,
        value: item.name,
      };
    });
    // 不触发表单更新事件 { emitEvent: false }
    this.basicInfoForm.patchValue(
      {
        taskName: `${example.title.substring(0, 50)}#${Date.now()}`,
        desc: example.title,
        prompt: example.value,
      },
      { emitEvent: false }
    );
    this.advancedSettingsForm.patchValue(
      {
        backgroundPrompt: example.backgroundPrompt ?? '',
        scoringCriteria: example.scoringCriteria ?? '',
        enableScoringCriteria: !!example.scoringCriteria,
      },
      { emitEvent: false }
    );
    this.basicSettingsForm.patchValue(
      {
        maximumRound: 20,
        taskType:
          this.taskTypeOptions.find(item => {
            return item.value === example.taskType;
          })?.value ?? this.taskTypeOptions[0].value,
      },
      { emitEvent: false }
    );

    this.saveDraft().then(() => {
      return this.uploadUseCases(
        example.useCases.map(item => {
          return {
            content: JSON.stringify(item),
          };
        })
      );
    });
  }

  public handleClickSwitch() {
    // 等待数据同步
    setTimeout(() => {
      if (this.advancedSettingsForm.value.enableScoringCriteria && this.advancedSettingsForm.value.scoringCriteria.trim() === '') {
        this.advancedSettingsForm.controls.scoringCriteria.setValue(this.scoringCriteriaPlaceholder);
        // 等待同步
        setTimeout(() => {
          this.cdr.detectChanges();
        }, 0);
      }
    }, 0);
  }

  private async saveDraft() {
    const taskNameError = this.getTaskNameError();
    if (taskNameError) {
      if (this.taskNameErrorShown !== taskNameError) {
        MessageComponent.showError(this.getTaskNameErrorMessage(taskNameError));
        this.taskNameErrorShown = taskNameError;
      }
      return;
    }
    this.taskNameErrorShown = null;

    const draft = this.buildDraftData();
    if (this.taskId) {
      const res = await this.promptOptimizeService.updateDraft(this.taskId, draft);
      this.draft.updatedTime = res?.data;
    } else {
      const res = await this.promptOptimizeService.createDraft(draft);
      this.taskId = res.task_id;
      if (!this.isInit) {
        // 初始化状态下不要跳转
        return;
      }
      MessageComponent.showSuccess(this.i18n.transform('draft_create_success'));
      this.router.navigate(['/home/prompt/optimize/edit'], {
        queryParams: { id: res.task_id },
      });
    }
  }

  protected readonly Boolean = Boolean;
}
