import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild
} from "@angular/core";
import { MODULES } from "@shared/modules";
import { TextFieldModule } from "@angular/cdk/text-field";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import type {
  IPromptTagItem,
  ISingleAgentQueryResp,
  IUpdateSingleAgentConfig
} from "../../../types/my-workspace.types";
import {
  BehaviorSubject,
  debounceTime,
  Observable,
  Subject,
  takeUntil
} from "rxjs";
import { agentCommonLogic, exampleTipText } from "../../common-logic-agent";
import { ActivatedRoute } from "@angular/router";
import { ExampleTipModalComponent } from "../example-tip-modal/example-tip-modal.component";
import { FormBuilder, FormControl, FormGroup, Validators } from "@angular/forms";
import { environment } from "src/environment/environment";
import { IconUploadComponent } from "@routes/knowledge-center/knowledge/icon-upload.component";
import {
  CmdTextareaComponent,
  CmdTextareaVariableGroup,
  CmdTextareaVariableItem
} from "@routes/agent-center/app-flow/components/cmd-textarea/cmd-textarea.component";
import { CommonValidation } from "@shared/validation/commonValidation";
import { GETVARIANT_REG } from "@constants/exp-tmpl-config.const";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { cdnAssetUrl } from "../../../../../single-spa/assets-url";
import { ModelImageDataService } from "@routes/agent-center/app-agent/components/info-and-prompt-builder/model-image-src.service";
import commonLogicWorkflow from "@routes/agent-center/app-flow/common-logic-workflow";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { CommonUtils } from "../../../../../utils/common.util";
import { NzFormModule } from 'ng-zorro-antd/form';
import { AGENT_MODE_CODE } from "../../agent-bot-page/agent-bot-page.constant";
import { CommonService } from "@services/common.service";
import { SkillInputPromptService } from "@services/agent-center/skill/skill-input-prompt.service";
import { NzMessageService } from "ng-zorro-antd/message";
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
import { SaveTmplLibraryModalComponent } from '@routes/prompt/prompt-candidate-template/save-tmpl-library-modal/save-tmpl-library-modal.component';
import { ITmpl } from '@services/prompt.service';
import moment from 'moment';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { MessageComponent } from '@shared/services/cfdata.service';

@Component({
  selector: "info-and-prompt-builder",
  templateUrl: "./info-and-prompt-builder.component.html",
  styleUrls: [
    "./info-and-prompt-builder.component.scss",
    "../../../../../styles/text-field-prebuilt.css"
  ],
  imports: [
    MODULES,
    TextFieldModule,
    ExampleTipModalComponent,
    IconUploadComponent,
    CmdTextareaComponent,
    NzFormModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    }
  ]
})
export class InfoAndPromptBuilderComponent implements OnInit {
  @ViewChild("exampleTip", { static: true }) exampleTipDirective: any;

  @ViewChild("promptTextareaRef") promptTextareaRef!: ElementRef;

  @ViewChild("autoGenerateTip") autoGeneTipDirective: any;

  @ViewChild("autoGeneDescriptionTip")
  descriptionTipDirective: any;

  @Input() agentInfo: ISingleAgentQueryResp = {
    icon: "",
    name: "",
    description: "",
    promptTags: [] as IPromptTagItem[]
  };
  @Input() modelConfig: any;
  @Input() promptInputed = "";

  @Input() dispatchSelectedType = "";

  @Input() isShowPrompt = true;

  @Input() curAgentModeCode: AGENT_MODE_CODE;

  @Output() nameUpdated = new EventEmitter<string>();

  @Output() logoUpdated = new EventEmitter<string>();

  public placeholderStr = `${this.i18n.transform("prompt_placeholder")}：\n
     1. ${this.i18n.transform("prompt_placeholder1")}\n
     2. ${this.i18n.transform("prompt_placeholder2")}\n`;

  /** 判断textarea是否正在输入中文拼音，控制absolute定位的placeholder中的圆点和连线显隐 */
  public isInputChinese = false;

  public isPOC = environment.envType === "poc";

  public agentId = "";

  public agentLogo = "";

  public groupFormControl: FormGroup;
  // 应用名称
  public openingInputed = "";

  // 描述
  public openingDescription = "";

  protected AGENT_MODE_CODE = AGENT_MODE_CODE;

  private promptInputSubject$ = new Subject<string>();

  private nameInputSubject$ = new Subject<string>();

  private descInputSubject$ = new Subject<string>();

  private destroy$ = new Subject<void>();

  public isFlowReadonly = false;

  public userVariants: Array<CmdTextareaVariableItem> = [];

  public inputVariables: Array<CmdTextareaVariableItem> = [];

  public variants: Array<CmdTextareaVariableGroup> = [];
  debounceTimer = null;

  get variableTip() {
    return this.userVariants.length || this.inputVariables.length
      ? ""
      : this.i18n.transform("prompt_no_variable_tip");
  }

  private paramsId: string;

  public get promptMaxLength() {
    return this.configServ.getConfigs().prompt_max_length ?? 20000;
  }

  private readonly showVarListSubject$ = new Subject<boolean>();
  experienceCreation = false;

  constructor(
    private configServ: AgentConfigService,
    private commonLogic: agentCommonLogic,
    private cdr: ChangeDetectorRef,
    private agentDataServe: AgentDataService,
    private route: ActivatedRoute,
    fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private modelImageDataService: ModelImageDataService,
    private appAgentRepoServe: AppAgentRepoService,
    public readonly commonService: CommonService,
    public inputService: SkillInputPromptService,
    private message: NzMessageService,
    private nzModal: NzModalService,
    private candidateTemplateListServe: CandidateTemplateListService,
  ) {
    this.groupFormControl = fb.group({
      name: new FormControl("", [
        Validators.required,
        Validators.maxLength(64),
        CommonValidation.wfNameVerify(
          this.i18n.transform("variable_validator5")
        )
      ]),
      description: new FormControl("", [
        Validators.required,
        Validators.minLength(1),
        Validators.maxLength(256)
      ])
    });

    this.route.queryParams.subscribe((params) => {
      this.agentId = params.agentId;
      this.paramsId = params.agentId;
      if (params.from === "experience-creation") {
        this.experienceCreation = true;
      }
    });

    this.agentDataServe
      .promptTextUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((optimizePrompt: string) => {
        if (optimizePrompt) {
          this.promptInputed = optimizePrompt.trim();
          this.agentInfo.promptTags =
            this.commonLogic.handlePrompttags(optimizePrompt);
        }
      });

    // 订阅还原版本的agent详情
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version) => {
        this.isFlowReadonly = version.isFlowReadonly;
        if (version.isFlowReadonly) {
          this.groupFormControl.disable();
        } else {
          this.groupFormControl.enable();
        }
      });

    // 处理用户变量
    this.agentDataServe
      .agentMemeryVarsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list) => {
        this.userVariants = list?.map((item) => {
          return {
            label: item.variable_key,
            value: `memory.${item.variable_key}`
          };
        });
        this.syncVariants();
      });

    // 处理入参变量
    this.agentDataServe
      .inputMemoryVarsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((list) => {
        this.inputVariables = list?.map((item) => {
          return {
            label: item.variable_key,
            value: `inputs.${item.variable_key}`
          };
        });
        this.syncVariants();
      });

    this.route.queryParams.subscribe((params) => {
      if (params && params.readonly_mode) {
        this.groupFormControl.controls.name.disable();
        this.groupFormControl.controls.description.disable();
      } else {
        this.groupFormControl.controls.name.enable();
        this.groupFormControl.controls.description.enable();
      }
    });
  }

  ngOnInit() {
    this.mountDebounceSave();
    this.mountDebounceNameSave();
    this.mountDebounceDescSave();
    this.agentDataServe
      .agentConfigUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((promptAndModelConfig: any) => {
        const { name, description, modelConfig } = promptAndModelConfig;
        if (!name) {
          return;
        }
        if (!this.experienceCreation) {
          return;
        }
        this.optimizePrompting({
          instruct: name + description,
          tools: [],
          stream: true,
          modelInfo: {
            model: modelConfig.model_deployment_id || modelConfig.id,
            model_source: modelConfig.model_type || modelConfig.source,
            model_name:
              modelConfig.model_name || modelConfig.model || modelConfig.id,
            headers: {}
          }
        });
      });
  }

  firstchange = true;

  ngOnChanges(changes: SimpleChanges) {
    if (changes.agentInfo && changes.agentInfo.currentValue) {
      const { icon, name, description } = changes.agentInfo.currentValue;
      this.agentLogo = icon;
      this.groupFormControl.patchValue({
        name,
        description
      });
    }
    if (
      changes.dispatchSelectedType &&
      changes.dispatchSelectedType.currentValue
    ) {
      this.dispatchSelectedType = changes.dispatchSelectedType.currentValue;
    }
    this.inputService.setInputValue(changes?.promptInputed?.currentValue || this.promptInputed || "");
  }

  tiLoading = false;

  ngOnDestroy(): void {
    this.agentDataServe.setPromptText("");
    this.promptInputSubject$.complete();
    this.nameInputSubject$.complete();
    this.descInputSubject$.complete();
    this.destroy$.next();
    this.destroy$.complete();
    this.agentDataServe.setAgentConfig({
      name: "",
      description: "",
      modelConfig: {}
    });
    this.inputService.setInputValue("");
  }

  iconValue = "";

  getIconPng() {
    if (this.agentLogo.startsWith("data:image/png;base64")) {
      return this.iconValue;
    } else {
      return this.agentLogo;
    }
  }

  public syncVariants() {
    this.variants = [
      {
        label: this.i18n.transform("variable-memory-tip7"),
        items: this.userVariants
      },
      {
        label: this.i18n.transform("variable-memory-tip3"),
        items: this.inputVariables
      }
    ];
  }

  public handleLogoChange() {
    this.doTriggerSave({
      data: { icon: this.getIconPng() }
    });
  }

  /** 自定义设置Prompt builder顶部的tags数组对应的背景色和边框色 */
  public getTagStyle(type: string) {
    return this.commonLogic.getTagStyle(type);
  }

  public onCompositionStart() {
    this.isInputChinese = true;
    this.cdr.markForCheck();
  }

  public onCompositionEnd() {
    if (this.promptInputed) {
      this.isInputChinese = false;
    }
  }

  public isNotEmptyAfterTrim(): boolean {
    const trimmedInput = this.promptInputed?.trim();
    return !!trimmedInput || this.promptInputed?.includes("\n");
  }

  /**
   * 用户手动修改textarea中的Prompt，1）需实时刷新顶部展示的tags数组，
   * 2）并且防抖500毫秒后，调用接口部分保存Agent config
   */
  public onInputChange(ev: any) {
    this.isInputChinese = false;
    this.agentInfo.promptTags = this.commonLogic.handlePrompttags(ev);
    this.debouncedSave(this.promptInputed);
    // 传递给skill用于自动推荐
    this.inputService.setInputValue(this.promptInputed);
    this.cdr.markForCheck();
  }

  public onInputName(event: any) {
    const name = (event.target as HTMLInputElement).value;
    // 防抖
    clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => {
      if (this.groupFormControl.valid) {
        this.agentDataServe.setNameAndPromptConfig({
          name
        });
        this.nameUpdated.emit(name);
        this.nameInputSubject$.next(name);
      }
    }, 1000);
  }

  public onInputDesc(event: any) {
    const desc = (event.target as HTMLInputElement).value;
    if (desc) {
      this.descInputSubject$.next(desc);
    }
  }

  /** 打开智能优化Prompt弹窗 */
  public openOptimizePromptModal() {
    if (!this.promptInputed || this.isFlowReadonly) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
      instruct:this.promptInputed
      }
    });
  }

  public openRefModal() {
    if (this.isFlowReadonly) {
      return;
    }

    const myModal = this.nzModal.create({
      nzContent: RefPromptComponent,
      nzWidth: 1000,
      nzData: {
        select: (tmpl: ITmpl) => {
          this.promptInputed = tmpl.content.trim();
          this.agentInfo.promptTags = this.commonLogic.handlePrompttags(this.promptInputed);
          this.doTriggerSave({
            data: {
              instructions: this.promptInputed,
            },
          });
          this.scrollToBottom();
        },
      },
    });
  }

  public showSaveTmplModal() {
    if (this.promptInputed && this.promptInputed.length > 0) {
      const thisMOdal = this.nzModal.create({
        nzContent: SaveTmplLibraryModalComponent,
        nzWidth: 600,
        nzData: {
          currentTmpl: {
            is_workflow: true,
            created_on: moment().format('YYYY-MM-DD HH:mm:ss'),
            content: this.promptInputed,
            model_config: {
              temperature: 0,
              top_p: 0,
              max_tokens: 0,
              presence_penalty: 0,
            } as any,
          },
          modalClose: form => {
            if (form?.value?.templateName) {
              const params = {
                task_id: this.paramsId,
                id: '',
                name: form.value.templateName,
                tags: form.value.tags,
                industry_id: form.value.industrys,
                content: this.promptInputed,
                source: 'PLAYGROUND',
                variables: this.processString(this.promptInputed),
              };
              this.candidateTemplateListServe.saveFormalTmpl(params).subscribe({
                next: res => {
                  MessageComponent.showSuccess(this.i18n.transform('single_tmpl_save_success_tip'));
                },
              });
            }
          },
        },
      });
    }
  }

  /** 点击示例，复制一组模板 */
  public addExamplePrompt() {
    if (this.isFlowReadonly) {
      return;
    }

    if (this.promptInputed.trim()) {
      this.promptInputed += '\n' + exampleTipText;
    } else {
      this.promptInputed += exampleTipText;
    }
    const tags = this.commonLogic.handlePrompttags(this.promptInputed);
    this.agentInfo.promptTags = [...this.agentInfo.promptTags, ...tags];
    this.doTriggerSave({
      data: {
        instructions: this.promptInputed,
      },
    });
    this.scrollToBottom();
  }

  public getUniqueTags(promptTags) {
    return promptTags.filter(
      (tag, index, self) =>
        index === self.findIndex((t) => t.name.trim() === tag.name.trim())
    );
  }

  private doTriggerSave(
    config: IUpdateSingleAgentConfig = {
      data: {},
      successCb: () => {
      },
      failCb: () => {
      },
      finallyCb: () => {
      }
    }
  ) {
    this.commonLogic.doTriggerSave(this.agentId, config);
  }

  /** 500毫秒触发一次put接口 */
  private debouncedSave(prompt: string): void {
    this.promptInputSubject$.next(prompt);
  }

  private mountDebounceSave(): void {
    this.promptInputSubject$.pipe(debounceTime(500)).subscribe((prompt) => {
      this.doTriggerSave({
        data: {
          instructions: prompt
        }
      });
    });
  }

  private mountDebounceNameSave(): void {
    this.nameInputSubject$.pipe(debounceTime(500)).subscribe((name) => {
      this.doTriggerSave({
        data: { name }
      });
    });
  }

  private mountDebounceDescSave(): void {
    this.descInputSubject$.pipe(debounceTime(500)).subscribe((desc) => {
      this.doTriggerSave({
        data: { description: desc }
      });
    });
  }

  /** 回答完成 或 发送新问题时，页面滚动条到最底部 */
  private scrollToBottom() {
    setTimeout(() => {
      this.promptTextareaRef.nativeElement.scrollTop =
        this.promptTextareaRef.nativeElement.scrollHeight;
    }, 0);
  }

  /** 处理“保存候选模板作为正式模板”接口中的入参variables */
  public processString(input: string): string {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map((match) => match.slice(2, -2));
      return extractedValues.join(",");
    }
    return "";
  }

  public showVarList(event) {
    event.preventDefault();
    event.stopPropagation();
    this.showVarListSubject$.next(true);
  }

  public showVarList$(): Observable<boolean> {
    return this.showVarListSubject$.asObservable();
  }

  iconLoading = false;

  generationImage() {
    this.iconLoading = true;
    this.modelImageDataService
      .getModelImageData({
        name: this.groupFormControl.value.name,
        description: this.groupFormControl.value.description
      })
      .then((res) => {
        this.iconValue = res.icons.icon; // png
        this.agentLogo = res.icons.icon_detail; //base
        this.handleLogoChange();
      })
      .finally(() => {
        this.iconLoading = false;
      });
  }

  showPromptTip() {
    return this.isNotEmptyAfterTrim()
      ? this.i18n.transform("intelligent_prompt")
      : this.i18n.transform("enter_prompt_content_below_first");
  }

  private sseInstance: any;
  public lang = CommonUtils.getLanguage();

  public state = {
    fetching: false,
    optimizeResult: "",
    isLoading: false
  };

  private optimizePrompting(inputs: any) {
    this.experienceCreation = false;
    this.tiLoading = true;
    this.sseInstance = this.appAgentRepoServe.optimizePromptSSE(
      inputs,
      this.agentId,
      this.lang,
      {
        onMessage: (event: any) => {
          try {
            const { code, message, data } =
            event.data && commonLogicWorkflow.stringToObject(event.data);
            if (code === 0 && data) {
              this.tiLoading = false;
              this.promptInputed += data;
            }
            if (code !== 0) {
              this.tiLoading = false;
              this.promptInputed =
                message !== "" ? message : this.i18n.transform("NetErrorTips");
            }
          } catch {
          }
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
        onDone: () => {
          this.doTriggerSave({
            data: {
              instructions: this.promptInputed
            }
          });
          this.tiLoading = false;
          this.cdr.markForCheck();
        },
        onError: (error: { data: string; status: any }) => {
          this.tiLoading = false;
          if (error.data) {
            try {
              const errInfo = JSON.parse(error.data);
              const apiError = errInfo?.error_msg
                ? this.i18n.transform("ApiError", {
                  errCode: errInfo.error_code,
                  reason: errInfo.error_msg
                })
                : "";

              this.state.optimizeResult =
                this.i18n.transform("NetErrorTips") + apiError;
            } catch {
            }
          } else {
            this.state.optimizeResult = this.i18n.transform("NetErrorTips");
          }
          this.scrollToBottom();
          this.cdr.markForCheck();
        },
        onTimeout: () => {
          this.tiLoading = false;
          this.message.error(this.i18n.transform("streaming_timeout"), { nzDuration: 3000 });
          this.sseInstance?.close();
          /** 如果没有之前的回答 */
          if (this.state.optimizeResult === "") {
            this.state.optimizeResult =
              this.i18n.transform("streaming_timeout");
          }
          this.scrollToBottom();
          this.cdr.markForCheck();
        }
      }
    );
  }

  get isZH(): boolean {
    return this.lang === "zh-cn";
  }

  protected readonly changeUrl = cdnAssetUrl;
}
