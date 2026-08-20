import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnInit, OnDestroy } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { ModelServiceCompareRouter } from './components/model-service-compare-router/model-service-compare-router.component';
import { Network } from '@model';
import { JiuwenModelService } from '@services/jiuwen-model/jiuwen-model.service';
import { ModelServiceType, ModelType } from '@enums/jiuwen-model.enum';
import { ActivatedRoute } from '@angular/router';
import {
  AbstractControl,
  FormArray,
  FormBuilder,
  FormControl,
  FormGroup,
  ValidationErrors,
  Validators,
  FormsModule,
  ReactiveFormsModule
} from '@angular/forms';
import { ModelRouterStrategiesService } from '@services/repositories/model-router-strategies';
import { MessageComponent } from '@shared/services/cfdata.service';
import { SetSidebarVisibilityService } from "@shared/services/set-sidebar-visibility.service";
import { LLMSelectComponent } from "@routes/agent-center/app-flow/components/llm-select/llm-select.component";
import { IModel } from "@routes/agent-center/app-flow/app-flow.types";
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSliderModule } from 'ng-zorro-antd/slider';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';

@Component({
  selector: 'meta-create-model-route',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MODULES,
    ModelServiceCompareRouter,
    LLMSelectComponent,
    NzFormModule,
    NzInputModule,
    NzInputNumberModule,
    NzButtonModule,
    NzIconModule,
    NzToolTipModule,
    NzRadioModule,
    NzSliderModule,
    NzSwitchModule,
    NzAlertModule,
    NzSpinModule,
    NzModalModule
  ],
  templateUrl: './create-model-route.component.html',
  styleUrls: ['./create-model-route.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
    NzModalService
  ],
})
export class CreateModelRouteComponent implements OnInit, OnDestroy {
  public isLoading = false;
  btnLoading = false;
  myForm: FormGroup;
  readonly maxStrategyDescriptionLength = 100;

  public modelOptions: IModel[] = [];

  ziMu = ['A', 'B', 'C', 'D', 'E'];
  aiNum = 2;
  aiNumCopy = 3;

  private newModelItem(title?: string, model_info?: any): FormGroup {
    return this.fb.group({
      title: title || this.i18n.transform('model')+'A',
      model_info: model_info || {},
    });
  }

  constructor(
    private modelRouterStrategiesService: ModelRouterStrategiesService,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private jiuwenModelServ: JiuwenModelService,
    private nzModalService: NzModalService,
    private route: ActivatedRoute,
    private i18n: I18NextEagerPipe,
    private elementRef: ElementRef,
    private fb: FormBuilder,
  ) {
    this.myForm = this.fb.group({
      strategy_name: new FormControl('', [
        Validators.required,
        this.validateName(),
      ]),
      model_service_list: this.fb.array([]),
      strategy_timeout: new FormControl(10000, [
        Validators.required,
        Validators.min(1000),
        Validators.max(1000000),
      ]),
      strategy_retry_count: new FormControl(0, [
        Validators.min(0),
        Validators.max(100),
      ]),
      strategy_description: new FormControl('', [
        Validators.maxLength(this.maxStrategyDescriptionLength),
      ]),
    });
  }

  validateName() {
    return (control: AbstractControl): ValidationErrors | null => {
      const _val = control.value as string;
      if (!/^(?!_)(?!\d)[a-zA-Z0-9_\-\u4e00-\u9fa5.]{2,36}$/.test(_val)) {
        return {
          serviceName: {
            tiErrorMessage: this.i18n.transform('validate_name_format'),
          },
        };
      }
      return null;
    };
  }

  public providerInfo: any = {};
  public serviceType: string = ModelType.LLM;
  public model_list_options: Array<any> = [
    { label: this.i18n.transform('model_service_api'), children: [] },
    { label: this.i18n.transform('preset_model_api'), children: [] },
    { label: this.i18n.transform('my_model_api'), children: [] },
  ];
  public radioList: Array<any> = [
    { id: '1', label: this.i18n.transform('non_streaming'), value: false, disabled: false },
    { id: '2', label: this.i18n.transform('streaming'), value: true, disabled: false },
  ];
  public strategyInfo: any = {
    service_list: [{ id: null }]
  };
  public serviceMap: any = {};
  public limit = 2;
  public uniKey = 'id';
  public settingInfo = {
    stream_val: true,
    securityVerify: false,
  };

  configs: Array<any> = [
    {
      name: 'max_tokens',
      value: 2048,
      min: 100,
      max: 32768,
      step: 1,
      scales: [100, 32768],
      title: this.i18n.transform('limit_max_tokens'),
    },
    {
      name: 'temperature',
      title: this.i18n.transform('temperature'),
      min: 0.01,
      max: 2,
      step: 0.01,
      value: 0.5,
      scales: [0.01, 2],
      desc: this.i18n.transform('temperature_desc'),
    },
    {
      name: 'top_p',
      title: this.i18n.transform('diversity'),
      min: 0,
      max: 1,
      step: 0.1,
      value: 0.5,
      scales: [0, 1],
      desc: this.i18n.transform('top_p_desc'),
    },
    {
      name: 'presence_penalty',
      title: this.i18n.transform('exist_penalty'),
      min: -2,
      max: 2,
      step: 0.1,
      value: 0,
      scales: [-2, 2],
      desc: this.i18n.transform('presence_penalty'),
    },
    {
      name: 'frequency_penalty',
      title: this.i18n.transform('frequency_penalty'),
      min: -2,
      max: 2,
      step: 0.1,
      value: 0,
      scales: [-2, 2],
      desc: this.i18n.transform('frequency_penalty_desc'),
    },
  ];
  switch_value = false;
  service_type_list = ModelType;

  public strategyId = '';

  strategy_spinner_Value = 10000;
  filterInfo = {
    model_type: ModelType.LLM,
    publish_status: 'online',
    only_private: true
  }

  handleBeforeChange(state) {
    this.switch_value = state;
    this.nzModalService.info({
      nzContent: this.switch_value
        ? this.i18n.transform('enable_content_safety_monitoring')
        : this.i18n.transform('disable_content_safety_monitoring')
    });
  }

  changeServiceType(item: any) {
    this.serviceType = item?.value;
  }

  onPageBack() {
    window.history.back();
  }

  public getFormArray(paramName: string): FormArray {
    const control = this.myForm.get(paramName);
    if (control instanceof FormArray) {
      return control;
    }
    throw new Error(`${paramName} control is not a FormArray`);
  }

  async filterModelList() {
    await this.jiuwenModelServ.getModelService('LLM', 'online').then((res) => {
      this.modelOptions = res.data ?? [];
      const _services = res.data ?? [];
      if (_services.length) {
        const privateIntegation = _services.filter(
          (item) => item.model_deploy_type === ModelServiceType.privateIntegation,
        );
        const platformIntegation = _services.filter(
          (item) => item.model_deploy_type === ModelServiceType.platformIntegation,
        );
        const privateDeploy = _services.filter(
          (item) => item.model_deploy_type === ModelServiceType.privateDeploy,
        );
        const platformDeploy = _services.filter(
          (item) => item.model_deploy_type === ModelServiceType.platformDeploy,
        );
        const mySelf = privateDeploy.concat(privateIntegation);

        platformIntegation.forEach((data) => {
          const _id = data[this.uniKey];
          this.model_list_options[0].children.push(this.generateOptions(data));
          this.serviceMap[_id] = data;
        });

        platformDeploy.forEach((data) => {
          const _id = data[this.uniKey];
          this.model_list_options[1].children.push(this.generateOptions(data));
          this.serviceMap[_id] = data;
        });

        mySelf.forEach((data) => {
          const _id = data[this.uniKey];
          this.model_list_options[2].children.push(this.generateOptions(data));
          this.serviceMap[_id] = data;
        });
      }
    });
  }

  generateOptions(service) {
    return {
      label: service.service_name,
      name: service.service_name,
      logo: service.logo ?? `${Network.ASSETS_PATH}model/assist.svg`,
      id: service[this.uniKey],
      service_key: service.service_key,
      is_support_function: service.is_support_function,
    };
  }

  public addServiceFn() {
    const control = this.myForm.get('model_service_list') as FormArray;
    let i = control.length;
    if (i < this.aiNumCopy) {
      const item = this.newModelItem(`${this.i18n.transform('model')}${this.ziMu[i]}`);
      const idItem = { id: '' };
      control.push(item);
      this.strategyInfo?.service_list.push(idItem);
      this.aiNum = this.aiNumCopy - control.length;
    }
  }

  public delServiceFn(index: number) {
    const control = this.myForm.get('model_service_list') as FormArray;
    control.removeAt(index);
    const list = control.getRawValue();
    this.aiNum = this.aiNumCopy - list.length;
    const new_list = [];
    for (let i = 0; i < list.length; i++) {
      list[i].title = `${this.i18n.transform('model')}${this.ziMu[i]}`;
      new_list.push(list[i]);
    }
    this.myForm.controls.model_service_list.setValue(new_list);
    this.strategyInfo.service_list = [];
    new_list.forEach((item, index) => {
      this.strategyInfo.service_list.push(item.model_info);
    });
  }

  checkGroup(): boolean {
    if (this.myForm.invalid) {
      Object.values(this.myForm.controls).forEach(control => {
        if (control instanceof FormArray) {
          control.controls.forEach(c => {
            c.markAsDirty();
            c.updateValueAndValidity({ onlySelf: true });
          });
        } else {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      const firstInvalidControlName = Object.keys(this.myForm.controls).find(
        key => this.myForm.controls[key].invalid
      );
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

  submit() {
    if (!this.checkGroup()) {
      return;
    }
    const value = this.myForm.getRawValue();
    let model_service_list = [];
    value.model_service_list.forEach((item) => {
      if(item?.model_info?.id){
        model_service_list.push(item.model_info);
      }
    });

    if(model_service_list.length === 0){
      MessageComponent.showError(this.i18n.transform('select_ai_model'), 3000);
      return;
    }

    const params = {
      strategy_name: value.strategy_name,
      model_service_list: model_service_list,
      strategy_timeout: value.strategy_timeout,
      strategy_retry_count: value.strategy_retry_count,
      strategy_description: value.strategy_description,
    };

    this.btnLoading = true;
    if (this.strategyId) {
      this.modelRouterStrategiesService
        .modifyModelRouterStrategies(this.strategyId, params)
        .then((res) => {
          MessageComponent.showSuccess(this.i18n.transform('edit_route_policy_success'), 3000);
          this.btnLoading = false;
        }).catch(() => { this.btnLoading = false; });
    } else {
      this.modelRouterStrategiesService
        .createModelRouterStrategies(params)
        .then((res:any) => {
          MessageComponent.showSuccess(this.i18n.transform('create_route_policy_success'), 3000);
          this.strategyId = res.id;
          this.strategyInfo = {...res, ...this.strategyInfo};
          this.btnLoading = false;
        }).catch(() => { this.btnLoading = false; });
    }
  }

  getStrategiesDetail(id) {
    this.modelRouterStrategiesService
      .getModelRouterStrategiesDetail(id)
      .then((res: any) => {
        this.strategyInfo = res;
        this.handleServiceList(res.service_list);
        this.myForm.controls.strategy_timeout.setValue(res.strategy_timeout);
        this.myForm.controls.strategy_retry_count.setValue(res.strategy_retry_count);
        this.myForm.controls.strategy_name.setValue(res.strategy_name);
        this.myForm.controls.strategy_description.setValue(res.strategy_description);
      });
  }

  handleServiceList(model_service_list) {
    this.aiNum = this.aiNumCopy - model_service_list.length;
    const control = this.myForm.get('model_service_list') as FormArray;
    for (let i = 0; i < model_service_list.length; i++) {
      model_service_list[i].label = model_service_list[i].model_name;
      let item = this.newModelItem(
        `${this.i18n.transform('model')}${this.ziMu[i]}`,
        model_service_list[i],
      );
      control.push(item);
    }
  }

  async ngOnInit() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    await this.filterModelList();
    const key = '_value';
    this.strategyId = this.route.queryParams[key].id;

    if (this.strategyId) {
      this.getStrategiesDetail(this.strategyId);
    } else {
      this.addServiceFn();
    }
  }

  ngOnDestroy() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
  }

  public updateModel(modelInfo: any){
    const control = this.myForm.get('model_service_list') as FormArray;
    const list = control.getRawValue();
    const selectedModel = this.modelOptions.find(
      (model) => model.id === modelInfo.id
    );
    list[modelInfo.index] = {
      title: list[modelInfo.index].title,
      model_info: selectedModel ? selectedModel : {},
    };
    control.setValue(list);
    this.strategyInfo.service_list = [];
    list.forEach((item, index) => {
      this.strategyInfo.service_list.push(item.model_info);
    });
    this.strategyInfo.service_list = [...this.strategyInfo.service_list];
  }
}
