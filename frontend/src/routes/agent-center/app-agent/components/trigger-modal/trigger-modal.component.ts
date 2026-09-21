import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  QueryList,
  Renderer2,
  ViewChild,
  ViewChildren,
  ViewEncapsulation,
  inject
} from "@angular/core";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import { FormsModule, ReactiveFormsModule } from "@angular/forms";
import { TextFieldModule } from "@angular/cdk/text-field";
import { triggerTimeOptions } from "@routes/agent-center/types/my-workspace.types";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { ActivatedRoute } from "@angular/router";
import { getInitOutputParamConfig } from "@routes/agent-center/app-flow/flow.const";
import { CommonUtils } from "src/utils/common.util";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { Subject, takeUntil } from "rxjs";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { AppFlowService } from "@routes/agent-center/app-flow/app-flow.service";
import { NzModalRef, NZ_MODAL_DATA } from "ng-zorro-antd/modal";
import { NzMessageService } from 'ng-zorro-antd/message';

import {
  agentCommonLogic
} from "../../common-logic-agent";
import {
  AbstractControl,
  FormBuilder,
  FormControl,
  NgForm,
  ValidationErrors,
  ValidatorFn,
  Validators
} from "@angular/forms";
import { MODULES } from "@shared/modules";

@Component({
  selector: "trigger-halfmodal",
  templateUrl: "./trigger-modal.component.html",
  styleUrls: [
    "./trigger-modal.component.scss",
    "../../../../../styles/text-field-prebuilt.css"
  ],
  encapsulation: ViewEncapsulation.None,
  imports: [
    MODULES,
    FormsModule,
    ReactiveFormsModule,
    TextFieldModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER]
    }
  ]
})
export class TriggerHalfmodalComponent {
  @ViewChild("descTipHost") descTipHost!: ElementRef;
  @ViewChildren("outputErrwrapper") outputErrwrappers: QueryList<ElementRef>;
  @ViewChild("outputForm") outputForm: NgForm;

  @Input() showCallMethod: boolean = false;
  @Input() onDismiss!: (params: any) => void;
  @Input() onCreate?: (params: any) => void;
  @Input() onUpdate?: (params: any) => void;

  regConfig = {
    operationId: {
      reg: /^(?!_)(?!-)[A-Za-z\d-_]+$/,
      msg: this.i18n.transform("triggermodalcomponent_171")
    },
    description: {
      reg: /^(?!_)(?![\s()])(?!-)[\u4e00-\u9fa5a-zA-Z\d_\s\-,，.。:：;；()（）、\\!！&*#]{0,512}$/,
      msg: this.i18n.transform("triggermodalcomponent_171")
    },
    triggerName: {
      reg: /^(?!_)(?![\s()])(?!-)[a-zA-Z\d_\-()\u4e00-\u9fa5]{0,64}$/,
      msg: this.i18n.transform("triggermodalcomponent_172")
    }
  };

  readonly modalRef = inject(NzModalRef);

  readonly nzModalData = inject<any>(NZ_MODAL_DATA);

  edit_data: any[] = [];

  public triggerType: "time" | "polling" = "time";

  public timeTriggerForm;

  public eventTriggerForm;

  public asyncTriggerForm;

  public pollingTriggerForm;

  public pollIntervalOptions = [
    {
      label: this.i18n.transform("triggermodalcomponent_poll_interval_unit_second"),
      value: "seconds"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_poll_interval_unit_minute"),
      value: "minute"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_poll_interval_unit_hour"),
      value: "hours"
    }
  ];

  public invocationTypeOptions = [
    {
      label: this.i18n.transform("toollistcomponent_57"),
      value: "sync"
    },
    {
      label: this.i18n.transform("toollistcomponent_56"),
      value: "async"
    }
  ];

  public data: any[] = triggerTimeOptions;

  public bodyParams: any[] = [];

  public bodyParamTypes = [
    {
      label: "String",
      value: "string"
    }
  ];

  public url = "";
  public types = [this.i18n.transform("triggermodalcomponent_175"), this.i18n.transform("triggermodalcomponent_176")];
  public selected_type = 0;

  private existingTriggers = [];

  private existingTimes = [];

  private agent_id = "";

  private workflow_id = "";

  private trigger_id = "";

  private destroy$ = new Subject<void>();

  private allParamNames = [];

  public timeFormat: string = "HH:mm:ss";
  public dateOptions = [
    {
      label: this.i18n.transform("commonlogicagent_13"),
      value: "day"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_178"),
      value: "week"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_179"),
      value: "month"
    }
  ];

  public weekOptions = [
    {
      label: this.i18n.transform("commonlogicagent_6"),
      value: "1"
    },
    {
      label: this.i18n.transform("commonlogicagent_7"),
      value: "2"
    },
    {
      label: this.i18n.transform("commonlogicagent_8"),
      value: "3"
    },
    {
      label: this.i18n.transform("commonlogicagent_9"),
      value: "4"
    },
    {
      label: this.i18n.transform("commonlogicagent_10"),
      value: "5"
    },
    {
      label: this.i18n.transform("commonlogicagent_11"),
      value: "6"
    },
    {
      label: this.i18n.transform("commonlogicagent_5"),
      value: "7"
    }
  ];

  public IntervalOptions = [
    {
      label: this.i18n.transform("triggerhalfmodalcomponent_117"),
      value: "day"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_188"),
      value: "hours"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_189"),
      value: "minute"
    },
    {
      label: this.i18n.transform("triggermodalcomponent_190"),
      value: "seconds"
    }
  ];
  public weekShow = false;
  public monthShow = false;

  public errorTimeObj = {
    periodMonthDay: {
      val: false,
      text: ""
    },
    IntervalDay: {
      val: false,
      text: ""
    }
  };

  public get errorTimeMsg() {
    let msg = "";
    Object.keys(this.errorTimeObj).forEach((item) => {
      if (this.errorTimeObj[item].val) {
        msg += `${this.errorTimeObj[item].text},`;
      }
    });
    return msg.substring(0, msg.length - 1);
  }


  get hasErrors(): boolean {
    return this.bodyParams.some((param) => param.error === true);
  }

  constructor(
    private elementRef: ElementRef,
    private fb: FormBuilder,
    private agentCommonLogic: agentCommonLogic,
    private appAgentServe: AppAgentRepoService,
    private appFlowRepoServ: AppFlowRepoService,
    private appFlowServ: AppFlowService,
    private route: ActivatedRoute,
    private agentDataServe: AgentDataService,
    private cdr: ChangeDetectorRef,
    private renderer: Renderer2,
    private i18n: I18NextEagerPipe,
    private messageServ: NzMessageService
  ) {
    this.asyncTriggerForm = this.fb.group({
      invocationType: new FormControl("sync", [Validators.required])
    });

    this.eventTriggerForm = this.fb.group({
      name: new FormControl("", [Validators.required]),
      prompt: new FormControl("", [Validators.required])
    });

    this.pollingTriggerForm = this.fb.group({
      name: new FormControl("", [Validators.required, this.noDuplicateKeywordsValidator()]),
      poll_url: new FormControl("", [Validators.required, Validators.pattern(/^https?:\/\/.+/)]),
      pollInterval: new FormControl(5, [Validators.required, Validators.min(1)]),
      pollIntervalUnit: new FormControl("minute", []),
      prompt: new FormControl("", [Validators.required, Validators.maxLength(500)])
    });

    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.agent_id = params.agentId;
    });

    this.route.queryParams.pipe(takeUntil(this.destroy$)).subscribe((params) => {
      this.workflow_id = params.id;
    });

    this.agentDataServe
      .triggerBtnUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((isClicked: any) => {
        if (isClicked) {
          this.onDateSelect({ value: "day" });
          this.triggerType = "time";
          this.timeTriggerForm?.reset({
            name: "",
            prompt: "",
            periodType: "day",
            periodMonthDay: "1",
            periodWeek: "1",
            periodTime: this.getNextFullHourNew(),
            IntervalType: "day",
            IntervalDay: "1"
          });
          this.eventTriggerForm.reset({ name: "", prompt: "" });
          this.pollingTriggerForm?.reset({
            name: "",
            poll_url: "",
            pollInterval: 5,
            pollIntervalUnit: "minute",
            prompt: ""
          });
          this.bodyParams = [];
        }
      });
  }

  ngOnInit() {
    this.initTimeTriggerForm();
    this.existingTriggers = this.nzModalData.historyTriggers;
    this.edit_data = this.nzModalData.edit_data;
    this.showCallMethod = this.nzModalData.showCallMethod;
    if (this.edit_data.length > 0) {
      this.timeTriggerForm?.controls.name.setValue(this.edit_data[0].name);
      this.timeTriggerForm?.controls.prompt.setValue(this.edit_data[0].prompt);
      this.getSelectDataTime(2, this.edit_data[0].cron);
      this.asyncTriggerForm?.controls.invocationType.setValue(
        this.edit_data[0].invocation
      );
      // Polling 编辑回填
      if (this.edit_data[0].type === 'POLLING') {
        this.triggerType = 'polling';
        this.pollingTriggerForm?.controls.name.setValue(this.edit_data[0].name || '');
        this.pollingTriggerForm?.controls.poll_url.setValue(this.edit_data[0].poll_url || '');
        this.pollingTriggerForm?.controls.prompt.setValue(this.edit_data[0].prompt || '');
        // 反向拆分 poll_interval_seconds 为数字+单位
        const seconds = this.edit_data[0].poll_interval_seconds || 300;
        const { interval, unit } = this.secondsToIntervalUnit(seconds);
        this.pollingTriggerForm?.controls.pollInterval.setValue(interval);
        this.pollingTriggerForm?.controls.pollIntervalUnit.setValue(unit);
      }
    }

  }

  public onDateSelect(info) {
    if (info.value === "week") {
      this.weekShow = true;
      this.monthShow = false;
    } else if (info.value === "month") {
      this.weekShow = false;
      this.monthShow = true;
    } else {
      this.weekShow = false;
      this.monthShow = false;
    }
  }

  public selectTypes(index) {
    this.selected_type = index;
  }

  private noDuplicateKeywordsValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      const _val = control.value as string;
      if (!/^(?!_)(?!\d)[a-zA-Z0-9_\u4e00-\u9fa5]{2,20}$/.test(_val)) {
        return {
          serviceName: {
            nzErrorMessage:
              this.i18n.transform("triggermodalcomponent_191")
          }
        };
      }
      return null;
    };
  }

  private clearMsg(type) {
    if (String(type) === "0") {
      this.errorTimeObj.periodMonthDay.val = false;
    } else {
      this.errorTimeObj.IntervalDay.val = false;
    }
  }

  private monthDayValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      this.errorTimeObj.periodMonthDay.val = false;
      this.clearMsg(1);
      if (this.selected_type === 0) {
        const periodType = this.timeTriggerForm?.controls.periodType.value;
        const periodMonthDay =
          this.timeTriggerForm?.controls.periodMonthDay.value;
        if (periodType === "month") {
          if (
            periodMonthDay === "" ||
            periodMonthDay === null ||
            periodMonthDay === undefined
          ) {
            this.errorTimeObj.periodMonthDay.val = true;
            this.errorTimeObj.periodMonthDay.text = this.i18n.transform("triggermodalcomponent_192");
          } else if (
            Number(periodMonthDay) < 1 ||
            Number(periodMonthDay) > 31
          ) {
            this.errorTimeObj.periodMonthDay.val = true;
            this.errorTimeObj.periodMonthDay.text = this.i18n.transform("triggermodalcomponent_193");
          }
        }
      }
      return this.errorTimeObj.periodMonthDay.val
        ? {
          serviceName: {
            nzErrorMessage: ""
          }
        }
        : null;
    };
  }

  private dayValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
      this.errorTimeObj.IntervalDay.val = false;
      this.clearMsg(0);
      if (this.selected_type === 1) {
        const IntervalType = this.timeTriggerForm?.controls.IntervalType.value;
        const IntervalDay = this.timeTriggerForm?.controls.IntervalDay.value;
        if (
          IntervalDay === "" ||
          IntervalDay === null ||
          IntervalDay === undefined
        ) {
          this.errorTimeObj.IntervalDay.val = true;
          this.errorTimeObj.IntervalDay.text = this.i18n.transform("triggerhalfmodalcomponent_115");
        } else if (
          IntervalType === "day" &&
          (Number(IntervalDay) < 1 || Number(IntervalDay) > 31)
        ) {
          this.errorTimeObj.IntervalDay.val = true;
          this.errorTimeObj.IntervalDay.text = this.i18n.transform("triggermodalcomponent_195");
        } else if (
          IntervalType === "hours" &&
          (Number(IntervalDay) < 1 || Number(IntervalDay) > 23)
        ) {
          this.errorTimeObj.IntervalDay.val = true;
          this.errorTimeObj.IntervalDay.text = this.i18n.transform("triggermodalcomponent_196");
        } else if (
          IntervalType === "minute" &&
          (Number(IntervalDay) < 1 || Number(IntervalDay) > 59)
        ) {
          this.errorTimeObj.IntervalDay.val = true;
          this.errorTimeObj.IntervalDay.text = this.i18n.transform("triggermodalcomponent_197");
        } else if (
          IntervalType === "seconds" &&
          (Number(IntervalDay) < 1 || Number(IntervalDay) > 59)
        ) {
          this.errorTimeObj.IntervalDay.val = true;
          this.errorTimeObj.IntervalDay.text = this.i18n.transform("triggermodalcomponent_198");
        }
      }
      return this.errorTimeObj.IntervalDay.val
        ? {
          serviceName: {
            nzErrorMessage: ""
          }
        }
        : null;
    };
  }

  private initTimeTriggerForm() {
    this.onDateSelect({ value: "day" });
    const formConfig: any = {
      name: ["", [Validators.required, this.noDuplicateKeywordsValidator()]],
      prompt: ["", [Validators.maxLength(500)]],
      periodType: ["day", []],
      periodMonthDay: ["1", [this.monthDayValidator()]],
      periodWeek: ["1", []],
      periodTime: [this.getNextFullHourNew(), []],
      IntervalType: ["day", []],
      IntervalDay: ["1", [this.dayValidator()]]
    };
    if (!this.showCallMethod) {
      formConfig.prompt[1] = [Validators.required, Validators.maxLength(500)];
    }
    this.timeTriggerForm = this.fb.group(formConfig);
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public selectTriggerType(id: "time" | "polling") {
    this.triggerType = id;
  }

  public triggerAdded = {
    title: this.i18n.transform("request_params"),
    collapsed: false
  };

  public changeCollapsedState(configInfo: any) {
    const collapsed = configInfo.collapsed;
    configInfo.collapsed = !collapsed;
    this.cdr.markForCheck();
  }

  public isControlInvalid(control: any): boolean {
    return control?.invalid && (control?.dirty || control?.touched);
  }

  public addBodyParam() {
    this.bodyParams.push(getInitOutputParamConfig());
  }

  public onDeleteBodyParam(index: number) {
    this.bodyParams.splice(index, 1);
  }

  public dismiss(): void {
    this.modalRef.destroy();
  }

  public updateTrigger(type: string): void {
    if (type === "polling") {
      const isPass = this.checkPollingGroup();
      if (isPass) {
        const params = {
          name: this.pollingTriggerForm?.controls.name?.value,
          type: "POLLING",
          poll_url: this.pollingTriggerForm?.controls.poll_url?.value,
          poll_interval_seconds: this.pollIntervalToSeconds(
            this.pollingTriggerForm?.controls.pollInterval?.value,
            this.pollingTriggerForm?.controls.pollIntervalUnit?.value
          ),
          prompt: this.pollingTriggerForm?.controls.prompt?.value,
          trigger_id: this.edit_data[0].trigger_id
        };
        this.appAgentServe
          .editOneTrigger(this.agent_id, params)
          .then((res: any) => {
            this.agentDataServe.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "POLLING",
              poll_url: params.poll_url,
              poll_interval_seconds: params.poll_interval_seconds,
              prompt: params.prompt
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_poll_updated"), { nzDuration: 3000 });
            this.agentDataServe.setAutoSaveTime(res.created_on);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_poll_updated_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
    if (type === "time") {
      const isPass = this.checkGroup();
      if (isPass) {
        const selectTimeData = this.getSelectDataTime(1, "");

        const params = {
          name: this.timeTriggerForm?.controls.name?.value,
          type: "TIMER",
          cron: selectTimeData,
          prompt: this.timeTriggerForm?.controls.prompt?.value,
          trigger_id: this.edit_data[0].trigger_id
        };
        this.appAgentServe
          .editOneTrigger(this.agent_id, params)
          .then((res: any) => {
            this.agentDataServe.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "TIMER",
              prompt: params.prompt,
              cron: params.cron
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_200"),{nzDuration:3000})
            this.agentDataServe.setAutoSaveTime(res.created_on);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_200_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
  }

  public createTrigger(type: string): void {
    if (type === "polling") {
      const isPass = this.checkPollingGroup();
      if (isPass) {
        const params = {
          name: this.pollingTriggerForm?.controls.name?.value,
          type: "POLLING",
          poll_url: this.pollingTriggerForm?.controls.poll_url?.value,
          poll_interval_seconds: this.pollIntervalToSeconds(
            this.pollingTriggerForm?.controls.pollInterval?.value,
            this.pollingTriggerForm?.controls.pollIntervalUnit?.value
          ),
          prompt: this.pollingTriggerForm?.controls.prompt?.value
        };
        this.appAgentServe
          .addOneTrigger(this.agent_id, params)
          .then((res: any) => {
            this.agentDataServe.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "POLLING",
              poll_url: params.poll_url,
              poll_interval_seconds: params.poll_interval_seconds,
              prompt: params.prompt
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_poll_created"), { nzDuration: 3000 });
            this.agentDataServe.setAutoSaveTime(res.updated_on);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_poll_created_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
    if (type === "time") {
      const isPass = this.checkGroup();
      if (isPass) {
        const selectTimeData = this.getSelectDataTime(1, "");
        const params = {
          name: this.timeTriggerForm?.controls.name?.value,
          type: "TIMER",
          cron: selectTimeData,
          prompt: this.timeTriggerForm?.controls.prompt?.value
        };
        this.appAgentServe
          .addOneTrigger(this.agent_id, params)
          .then((res: any) => {
            this.agentDataServe.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "TIMER",
              prompt: params.prompt,
              cron: params.cron
            });
            this.messageServ.success(this.i18n.transform("triggerhalfmodalcomponent_109"),{nzDuration:3000})
            this.agentDataServe.setAutoSaveTime(res.updated_on);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggerhalfmodalcomponent_109_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
    if (type === "event") {
      const outputErr = this.validateForm(this.eventTriggerForm);
      const matches = this.extractMatches(
        this.eventTriggerForm.get("prompt").value
      );
      const allParamsWithReference = this.verifyParamsRef(matches);
      if (outputErr) {
        allParamsWithReference.forEach((param, index) => {
          const formName = `outputFormName${index}`;
          if (outputErr[formName] && outputErr[formName].serviceName?.nzErrorMessage) {
            return;
          }
          this.updateErrorMsg(param, index);
        });
        return;
      }
      if (!outputErr) {
        allParamsWithReference.forEach((param, index) => {
          this.updateErrorMsg(param, index);
        });

        const hasUnrefParam = allParamsWithReference?.some(
          (param) => !param.isReferenced
        );
        if (hasUnrefParam) {
          return;
        }
      }
      if (CommonUtils.checkAndFocusFirstError(this.elementRef, this.eventTriggerForm)) {
        return;
      }

      const params = {
        trigger_id: this.trigger_id,
        name: this.eventTriggerForm?.controls.name?.value,
        type: "EVENT",
        prompt: this.eventTriggerForm?.controls.prompt?.value,
        params: this.bodyParams.map((item) => {
          return { name: item.name, description: item.description };
        }),
        hook_url: this.url
      };
      this.appAgentServe.addOneTrigger(this.agent_id, params)
        .then((res: any) => {
          this.agentDataServe.setTrigger({
            trigger_id: res.trigger_id,
            name: params.name,
            type: "EVENT",
            prompt: params.prompt,
            hook_url: this.url
          });
          this.messageServ.success(this.i18n.transform("triggerhalfmodalcomponent_110"),{nzDuration:3000})
          this.agentDataServe.setAutoSaveTime(res.updated_on);
          this.cdr.markForCheck();
        })
        .catch((err: any) => {
          this.messageServ.error(this.i18n.transform("triggerhalfmodalcomponent_110_failed"), { nzDuration: 3000 });
        })
        .finally(() => {
          this.dismiss();
        });
    }
  }

  public createTriggerWorkflow(type: string): void {
    if (type === "polling") {
      const isPass = this.checkPollingGroup();
      if (isPass) {
        const params = {
          name: this.pollingTriggerForm?.controls.name?.value,
          type: "POLLING",
          poll_url: this.pollingTriggerForm?.controls.poll_url?.value,
          poll_interval_seconds: this.pollIntervalToSeconds(
            this.pollingTriggerForm?.controls.pollInterval?.value,
            this.pollingTriggerForm?.controls.pollIntervalUnit?.value
          ),
          prompt: this.pollingTriggerForm?.controls.prompt?.value,
          invocation: this.asyncTriggerForm?.controls.invocationType?.value
        };
        if (this.onCreate) {
          this.onCreate(params);
          this.dismiss();
          return;
        }
        this.appFlowRepoServ
          .addOneTrigger(this.workflow_id, params)
          .then((res: any) => {
            this.appFlowServ.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "POLLING",
              poll_url: params.poll_url,
              poll_interval_seconds: params.poll_interval_seconds,
              prompt: params.prompt,
              invocation: params.invocation
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_poll_created"), { nzDuration: 3000 });
            this.appFlowServ.setAutoSaveTime(res.update_time);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_poll_created_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
    if (type === "time") {
      const isPass = this.checkGroup();
      if (isPass) {
        const selectTimeData = this.getSelectDataTime(1, "");

        const params = {
          name: this.timeTriggerForm?.controls.name?.value,
          type: "TIMER",
          prompt: this.timeTriggerForm?.controls.prompt?.value,
          cron: selectTimeData,
          invocation: this.asyncTriggerForm?.controls.invocationType?.value
        };

        if (this.onCreate) {
          this.onCreate(params);
          this.dismiss();
          return;
        }

        this.appFlowRepoServ
          .addOneTrigger(this.workflow_id, params)
          .then((res: any) => {
            this.appFlowServ.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "TIMER",
              prompt: params.prompt,
              cron: params.cron,
              invocation: params.invocation
            });
            this.messageServ.success(this.i18n.transform("triggerhalfmodalcomponent_109"),{nzDuration:3000})
            this.appFlowServ.setAutoSaveTime(res.update_time);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggerhalfmodalcomponent_109_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
  }

  public updateTriggerWorkflow(type: string): void {
    if (type === "polling") {
      const isPass = this.checkPollingGroup();
      if (isPass) {
        const params = {
          name: this.pollingTriggerForm?.controls.name?.value,
          type: "POLLING",
          poll_url: this.pollingTriggerForm?.controls.poll_url?.value,
          poll_interval_seconds: this.pollIntervalToSeconds(
            this.pollingTriggerForm?.controls.pollInterval?.value,
            this.pollingTriggerForm?.controls.pollIntervalUnit?.value
          ),
          prompt: this.pollingTriggerForm?.controls.prompt?.value,
          trigger_id: this.edit_data[0].trigger_id,
          invocation: this.asyncTriggerForm.get("invocationType")?.value
        };
        if (this.onUpdate) {
          this.onUpdate(params);
          this.dismiss();
          return;
        }
        this.appFlowRepoServ
          .editOneTrigger(this.workflow_id, params)
          .then((res: any) => {
            this.appFlowServ.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "POLLING",
              poll_url: params.poll_url,
              poll_interval_seconds: params.poll_interval_seconds,
              prompt: params.prompt,
              invocation: params.invocation
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_poll_updated"), { nzDuration: 3000 });
            this.appFlowServ.setAutoSaveTime(res.update_time);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_poll_updated_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
    if (type === "time") {
      const isPass = this.checkGroup();
      if (isPass) {
        const selectTimeData = this.getSelectDataTime(1, "");

        const params = {
          name: this.timeTriggerForm?.controls.name?.value,
          type: "TIMER",
          cron: selectTimeData,
          prompt: this.timeTriggerForm?.controls.prompt?.value,
          trigger_id: this.edit_data[0].trigger_id,
          invocation: this.asyncTriggerForm.get("invocationType")?.value
        };

        if (this.onUpdate) {
          this.onUpdate(params);
          this.dismiss();
          return;
        }

        this.appFlowRepoServ
          .editOneTrigger(this.workflow_id, params)
          .then((res: any) => {
            this.appFlowServ.setTrigger({
              trigger_id: res.trigger_id,
              name: params.name,
              type: "TIMER",
              prompt: params.prompt,
              cron: params.cron,
              invocation: params.invocation
            });
            this.messageServ.success(this.i18n.transform("triggermodalcomponent_203"),{nzDuration:3000})
            this.appFlowServ.setAutoSaveTime(res.update_time);
            this.cdr.markForCheck();
          })
          .catch((err: any) => {
            this.messageServ.error(this.i18n.transform("triggermodalcomponent_203_failed"), { nzDuration: 3000 });
          })
          .finally(() => {
            this.dismiss();
          });
      }
    }
  }

  public getOutputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.bodyParams.map((p) => p.name);
    names.splice(index, 1);
    this.allParamNames = this.bodyParams.map((p) => p.name);
    return {
      existingValues: names
    };
  }

  public onStartNodeNameChange() {
    window.setTimeout(() => {
      this.validateForm(this.outputForm?.form);
    });
  }

  private validateForm(form: any): ValidationErrors | null {
    const errors: ValidationErrors = {};
    if (!form) return null;

    Object.keys(form.controls).forEach(key => {
      const control = form.controls[key];
      if (control.invalid) {
        errors[key] = control.errors;
      }
    });

    return Object.keys(errors).length > 0 ? errors : null;
  }

  private parseTimeToDate(timeStr: string): Date {
    const parts = timeStr.split(":").map(Number);
    const d = new Date();
    d.setHours(parts[0] || 0, parts[1] || 0, parts[2] || 0, 0);
    return d;
  }

  private getNextFullHourNew(): Date {
    const now = new Date();
    let nextHour = now.getHours();
    const minutes = now.getMinutes();
    if (minutes > 0) {
      nextHour += 1;
    }
    if (nextHour === 24) {
      nextHour = 0;
    }
    const result = new Date();
    result.setHours(nextHour, 0, 0, 0);
    return result;
  }

  private getSelectDataTime(type, data): string {
    if (type === 1) {
      if (this.selected_type === 0) {
        const periodType = this.timeTriggerForm?.controls.periodType.value;
        const periodTime = this.timeTriggerForm?.controls.periodTime.value;
        let hours: number;
        let minutes: number;
        let seconds: number;
        if (periodTime instanceof Date) {
          hours = periodTime.getHours();
          minutes = periodTime.getMinutes();
          seconds = periodTime.getSeconds();
        } else {
          const periodTimeArray = String(periodTime).split(":").map(Number);
          seconds = periodTimeArray[2] || 0;
          minutes = periodTimeArray[1] || 0;
          hours = periodTimeArray[0] || 0;
        }

        if (periodType === "day") {
          return `${seconds} ${minutes} ${hours} * * ?`;
        }
        if (periodType === "week") {
          const periodWeek = this.timeTriggerForm?.controls.periodWeek.value;
          return `${seconds} ${minutes} ${hours} ? * ${periodWeek}`;
        }
        if (periodType === "month") {
          const periodMonthDay =
            this.timeTriggerForm?.controls.periodMonthDay.value;
          return `${seconds} ${minutes} ${hours} ${periodMonthDay} * ?`;
        }
      } else {
        const IntervalType = this.timeTriggerForm?.controls.IntervalType.value;
        const IntervalDay = this.timeTriggerForm?.controls.IntervalDay.value;

        if (IntervalType === "day") {
          return `0 0 0 */${IntervalDay} * ?`;
        }
        if (IntervalType === "hours") {
          return `0 0 */${IntervalDay} * * ?`;
        }
        if (IntervalType === "minute") {
          return `0 */${IntervalDay} * * * ?`;
        }
        if (IntervalType === "seconds") {
          return `*/${IntervalDay} * * * * ?`;
        }
      }
    } else {
      if (data.indexOf("*/") < 0) {
        const parts = data.split(" ");
        const seconds = parts[0].padStart(2, "0");
        const min = parts[1].padStart(2, "0");
        const hour = parts[2].padStart(2, "0");
        const day = parts[3];
        const month = parts[4];
        const dayOfWeek = parts[5];

        const newTime = `${hour}:${min}:${seconds}`;
        const newTimeDate = this.parseTimeToDate(newTime);
        if (day === "*" && month === "*" && dayOfWeek === "?") {
          this.selected_type = 0;
          this.timeTriggerForm?.controls.periodType.setValue("day");
          this.onDateSelect({ value: "day" });
          this.timeTriggerForm?.controls.periodTime.setValue(newTimeDate);
          return "";
        }
        if (day === "?" && month === "*" && dayOfWeek !== "*") {
          this.selected_type = 0;
          this.timeTriggerForm?.controls.periodType.setValue("week");
          this.onDateSelect({ value: "week" });
          this.timeTriggerForm?.controls.periodTime.setValue(newTimeDate);
          this.timeTriggerForm?.controls.periodWeek.setValue(dayOfWeek);
          return "";
        }
        const dayIsNumeric = day !== "*" && day.match(/^\d+$/);
        if (dayIsNumeric && month === "*" && dayOfWeek === "?") {
          this.selected_type = 0;
          this.timeTriggerForm?.controls.periodType.setValue("month");
          this.onDateSelect({ value: "month" });
          this.timeTriggerForm?.controls.periodTime.setValue(newTimeDate);
          this.timeTriggerForm?.controls.periodMonthDay.setValue(day);
          return "";
        }
      } else {
        const parts = data.split(" ");
        this.selected_type = 1;
        const seconds = parts[0];
        const min = parts[1];
        const hour = parts[2];
        const day = parts[3];
        if (day.indexOf("*/") >= 0) {
          this.timeTriggerForm?.controls.IntervalType.setValue("day");
          this.timeTriggerForm?.controls.IntervalDay.setValue(day.substring(2));
        }
        if (hour.indexOf("*/") >= 0) {
          this.timeTriggerForm?.controls.IntervalType.setValue("hours");
          this.timeTriggerForm?.controls.IntervalDay.setValue(hour.substring(2));
        }
        if (min.indexOf("*/") >= 0) {
          this.timeTriggerForm?.controls.IntervalType.setValue("minute");
          this.timeTriggerForm?.controls.IntervalDay.setValue(min.substring(2));
        }
        if (seconds.indexOf("*/") >= 0) {
          this.timeTriggerForm?.controls.IntervalType.setValue("seconds");
          this.timeTriggerForm?.controls.IntervalDay.setValue(seconds.substring(2));
        }
        return "";
      }
    }
    return "";
  }

  private checkGroup(): boolean {
    Object.keys(this.timeTriggerForm.controls).forEach(key => {
      this.timeTriggerForm.controls[key].markAsDirty();
      this.timeTriggerForm.controls[key].markAsTouched();
      this.timeTriggerForm.controls[key].updateValueAndValidity();
    });
    const errors: ValidationErrors | null = this.validateForm(this.timeTriggerForm);
    if (errors) {
      const firstError: any = Object.keys(errors)[0];
      this.elementRef.nativeElement.querySelector(`[formControlName=${firstError}]`)?.focus();
      return false;
    }

    return true;
  }

  private checkPollingGroup(): boolean {
    if (!this.pollingTriggerForm) {
      return true;
    }
    // 非 workflow 时 prompt 必填
    if (!this.showCallMethod) {
      this.pollingTriggerForm.controls.prompt.setValidators([Validators.required, Validators.maxLength(500)]);
    } else {
      this.pollingTriggerForm.controls.prompt.setValidators([Validators.maxLength(500)]);
    }
    Object.keys(this.pollingTriggerForm.controls).forEach(key => {
      this.pollingTriggerForm.controls[key].markAsDirty();
      this.pollingTriggerForm.controls[key].markAsTouched();
      this.pollingTriggerForm.controls[key].updateValueAndValidity();
    });
    const errors: ValidationErrors | null = this.validateForm(this.pollingTriggerForm);
    if (errors) {
      const firstError: any = Object.keys(errors)[0];
      this.elementRef.nativeElement.querySelector(`[formControlName=${firstError}]`)?.focus();
      return false;
    }
    return true;
  }

  private pollIntervalToSeconds(interval: number, unit: string): number {
    switch (unit) {
      case 'seconds':
        return interval;
      case 'minute':
        return interval * 60;
      case 'hours':
        return interval * 3600;
      default:
        return interval;
    }
  }

  private secondsToIntervalUnit(seconds: number): { interval: number; unit: string } {
    if (seconds >= 3600 && seconds % 3600 === 0) {
      return { interval: seconds / 3600, unit: 'hours' };
    }
    if (seconds >= 60 && seconds % 60 === 0) {
      return { interval: seconds / 60, unit: 'minute' };
    }
    return { interval: seconds, unit: 'seconds' };
  }

  private extractMatches(prompt: string): string[] {
    const regex = /\{\{([^{}\s]+)\}\}/g;
    const matches = [];
    let match;
    while ((match = regex.exec(prompt)) !== null) {
      matches.push(match[1]);
    }
    return matches;
  }

  private verifyParamsRef(
    matches: string[]
  ): { name: string; isReferenced: boolean }[] {
    return this.allParamNames.map((param) => {
      if (!param) {
        return { name: param, isReferenced: false };
      }
      const isReferenced = matches.some((match) => match === param);
      return { name: param, isReferenced };
    });
  }

  private updateErrorMsg(param: any, index: number) {
    const wrapper = this.outputErrwrappers.toArray()[index];
    if (!param.isReferenced) {
      if (!wrapper.nativeElement.firstChild) {
        this.bodyParams[index].error = true;
        this.addErrorMessage(wrapper, this.i18n.transform("trigger_modal_1"));
      }
    } else {
      this.bodyParams[index].error = false;
      while (wrapper.nativeElement.firstChild) {
        wrapper.nativeElement.removeChild(wrapper.nativeElement.firstChild);
      }
    }
  }

  private addErrorMessage(errWrapper: ElementRef, message: string): void {
    const errorMsg = this.renderer.createElement("div");
    this.renderer.addClass(errorMsg, "nz-validate-error-container");
    this.renderer.setStyle(errorMsg, "display", "flex");
    this.renderer.setStyle(errorMsg, "color", "#f23030");
    this.renderer.setStyle(errorMsg, "margin-top", "8px");
    this.renderer.setStyle(errorMsg, "align-items", "center");

    const errorIcon = this.renderer.createElement("span");
    this.renderer.addClass(errorIcon, "nz-error-icon");
    this.renderer.setStyle(errorIcon, "color", "#f23030");
    this.renderer.setStyle(errorIcon, "font-size", "16px");
    this.renderer.setStyle(errorIcon, "margin-right", "4px");

    const errorText = this.renderer.createElement("span");
    this.renderer.addClass(errorText, "nz-validate-text");
    const text = this.renderer.createText(message);
    this.renderer.appendChild(errorText, text);
    this.renderer.appendChild(errorMsg, errorIcon);
    this.renderer.appendChild(errorMsg, errorText);
    this.renderer.appendChild(errWrapper.nativeElement, errorMsg);
  }
}
