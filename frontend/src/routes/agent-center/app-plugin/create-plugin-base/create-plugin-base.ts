/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormControl, NgForm, Validators } from '@angular/forms';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
import { I18nNamespace } from '@i18n';
import { AccBlockComponent } from '@routes/agent-center/app-flow/components/acc-block/acc-block.component';

import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { ContextService } from '@services/context.service';

import { NoCnDirective } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective, PluginAuthNameValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { handleCommonReqError, removeHTMLTag } from 'src/utils/utils';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzStepsModule } from 'ng-zorro-antd/steps';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzTreeModule } from 'ng-zorro-antd/tree';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzIconModule } from 'ng-zorro-antd/icon';
import {
  ApiKeyAuthArguments,
  IAuthInfo,
  IPluginWithTools,
  IRequestArgsView,
  IServAuthKV,
  IToolCreate,
  IUserAuthKV,
  PluginDetail,
  UserAuthArguments,
} from '../app-plugin.interface';
import { isSimpleType, pluginSchemaStr2Path, showFromError, STREAM_RESPONSE_EXAMPLE, view2Schema } from '../utils';
import { StreamResponseTipComponent } from '@shared/components/stream-response-tip/stream-response-tip.component';
import { environment } from 'src/environment/environment';
import { Subject } from 'rxjs';
import { IconUploadComponent } from '@routes/knowledge-center/knowledge/icon-upload.component';
import { isNil } from 'lodash';
import { CollapseText } from '@routes/agent-center/app-plugin/components/collapse-text/collapse-text';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonUtils } from 'src/utils/common.util';
import { CreateTipModalComponent } from '@routes/platform-management/resource-management/alert-model/create-tip-modal/create-tip-modal.component';
import { CommonService } from '@services/common.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { ParamEditorComponent } from '@routes/agent-center/app-plugin/components/param-editor/param-editor.component';
import { PromptType, VariableType } from '@interfaces/prompt/prompt-optimize-task.interface';
import { pluginContentImportModal } from '@routes/agent-center/app-plugin/components/import-openapi-modal/plugin-content-import-modal.component';
import { IResponse } from '@routes/agent-center/interfaces/plugin/app-plugin.interface';
import { pinyin } from 'pinyin-pro';

const CREATE_ALERT_TIPS_STKEY = 'create_alert_tips_stkey';

@Component({
  selector: 'create-plugin-base',
  templateUrl: './create-plugin-base.html',
  styleUrls: ['./create-plugin-base.scss'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    PluginAuthNameValidatorDirective,
    NonEmptyValidatorDirective,
    NoCnDirective,
    StreamResponseTipComponent,
    IconUploadComponent,
    CollapseText,
    ParamEditorComponent,
    NzFormModule,
    NzInputModule,
    NzRadioModule,
    NzSwitchModule,
    NzStepsModule,
    NzAlertModule,
    NzTreeModule,
    NzEmptyModule,
    NzButtonModule,
    NzToolTipModule,
    NzIconModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT, I18nNamespace.MODEL_ACCESS, I18nNamespace.AGENT_CENTER],
    },
    NzModalService,
  ],
})
export class CreatePluginBaseComponent implements OnInit {
  @Input('pluginInfo') pluginInfo: any;

  @Input('pluginId') pluginId: string;

  @Input('lockedStep') lockedStep: number;
  // common:正常创建 agent:单智能体 flow:工作流
  @Input() usedFrom: string = 'common';

  @Input() agentNode = ''; // 用于工作流里agent节点里的新建插件

  @ViewChild('apiAuthForm') apiAuthForm: NgForm;

  @ViewChild('responseForm') responseForm: NgForm;

  @Output('confirm') confirm = new EventEmitter<void>();

  readonly modalRef = inject(NzModalRef, { optional: true });
  readonly drawerRef = inject(NzDrawerRef, { optional: true });
  readonly isInModal = !!this.modalRef;

  public readonly PromptType = PromptType;

  public isPOC = environment.envType === 'poc'; // 当前是否为POC环境

  public pluginDetail: PluginDetail = {
    name: '',
    tool_chinese_name: '',
    description: '',
    url: '',
    method: '',
    headers: '',
    logo: '',
    visibility: 'user',
    auth: '',
    arguments: '',
    response: '',
    is_input_list: false,
    is_output_list: false,
    intf_type: 'blocking',
    auth_required: false,
    metadata: '',
    call_mode: '',
  };

  isSimpleType = isSimpleType;

  private destroy$ = new Subject<void>();

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private fb: FormBuilder,
    private appPluginRepoServ: AppPluginRepoService,
    private agentDataServe: AgentDataService,
    private ctxServ: ContextService,
    private nzModal: NzModalService,
    private router: Router,
    private route: ActivatedRoute,
    private configServ: AgentConfigService,
    private readonly commonService: CommonService
  ) {}

  public logo = cdnAssetUrl('assets/agent-center/images/plugin-default.svg');
  public debugIcon = cdnAssetUrl('assets/agent-center/icons/plugin-debug-icon.svg');

  // 表单label
  public createPluginFormLabel = {
    pluginName: this.i18n.transform('name'),
    pluginZhName: this.i18n.transform('name'),
    defaultPlaceholder: this.i18n.transform('input_placeholder'),
    pluginDescription: this.i18n.transform('description'),
    pluginMethod: this.i18n.transform('request_method'),
    pluginAuth: this.i18n.transform('request_auth'),
    pluginAuthLoc: this.i18n.transform('request_secretKey'),
    requestHeader: this.i18n.transform('request_header'),
    requestArguments: this.i18n.transform('request_params'),
    requestResponse: this.i18n.transform('res_params'),
    projectId: this.i18n.transform('project_id'),
    auth_required: this.i18n.transform('auth_required'),
    metadata: this.i18n.transform('metadata'),
    protocol: this.i18n.transform('plugin_protocol'),
    host: this.i18n.transform('plugin_host'),
    baseURL: this.i18n.transform('plugin_url'),
    pluginLogo: this.i18n.transform('plugin_logo'),
  };

  public pluginName: string;

  public modalTitle: string = this.i18n.transform('create_plugin');

  steps: Array<any> = [
    {
      label: this.i18n.transform('basic_info'),
    },
    {
      label: this.i18n.transform('config_info'),
    },
  ];

  step = 0;

  showTips = true;

  public loading = false;

  activeStep: any = this.steps[this.step];

  typeRadioList: Array<{ label: string; id: string }> = [
    {
      label: this.i18n.transform('createpluginbase_761'),
      id: 'api',
    },
    {
      label: this.i18n.transform('createpluginbase_762'),
      id: 'functiongraph',
    },
  ];

  authRadioList: Array<{ label: string; id: string; show: boolean }> = [
    {
      label: this.i18n.transform('no_auth'),
      id: 'pluginNoNeedAuth',
      show: true,
    },
    {
      label: 'API Key',
      id: 'pluginApiKey',
      show: true,
    },
    {
      label: 'HisIAM',
      id: 'HIS_IAM',
      show: this.configServ.getConfigs()?.his_openai_enable,
    },
    {
      label: 'HisSGOV',
      id: 'SGOV',
      show: this.configServ.getConfigs()?.his_openai_enable,
    },
  ];

  public iamTip = {
    iamUrl: this.i18n.transform('iam_tip.iam_url', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamDomain: this.i18n.transform('iam_tip.iam_domain', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamProject: this.i18n.transform('iam_tip.iam_project', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamUser: this.i18n.transform('iam_tip.iam_user', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamPassword: this.i18n.transform('iam_tip.iam_password', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamAK: this.i18n.transform('iam_tip.iam_ak', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
    iamSK: this.i18n.transform('iam_tip.iam_sk', {
      ns: I18nNamespace.MODEL_ACCESS,
    }),
  };

  authList = [...this.authRadioList];

  protocolList: Array<{ label: string; id: string }> = [
    {
      label: 'https',
      id: 'https',
    },
    {
      label: 'http',
      id: 'http',
    },
  ];

  userAuthRadioList: Array<{ label: string; id: string }> = [
    {
      label: 'Header',
      id: 'Header',
    },
    {
      label: 'Query',
      id: 'Query',
    },
  ];

  authConfigRadioList: Array<{ label: string; id: string }> = [
    {
      label: this.i18n.transform('no_manual_activation'),
      id: 'false',
    },
    {
      label: this.i18n.transform('manual_activation'),
      id: 'true',
    },
  ];

  public userAuthArgs: UserAuthArguments[] = [
    {
      name: '',
      sourceName: '',
    },
  ];

  public apiKeyAuthArgs: ApiKeyAuthArguments[] = [
    {
      name: '',
      value: '',
    },
  ];

  public projectId = '';

  public isLocked = false;

  private originKeys = [];

  public numberValidateOps = [
    {
      label: this.i18n.transform('num_label'),
      value: 'NUM',
    },
  ];

  public isHideFg: boolean = false; // 是否是hcs环境

  public isOp = false;

  verifyMethods = [
    {
      label: this.i18n.transform('verify_methods.iam_username_and_password', {
        ns: I18nNamespace.MODEL_ACCESS,
      }),
      id: 'iam',
    },
    {
      label: 'Access Key ID/Secret Access Key',
      id: 'aksk',
    },
  ];
  public streamResExamples = STREAM_RESPONSE_EXAMPLE;

  public groupFormControl = this.fb.group({
    pluginName: new FormControl('', []),
    pluginZhName: new FormControl('', [Validators.required, CommonValidation.pluginZHNameVerify(this.i18n.transform('variable_validator10'))]),
    pluginDescription: new FormControl('', [Validators.required]),
    pluginLogo: new FormControl(''),
    visibility: new FormControl(false),
    pluginMethod: new FormControl('GET', []),
    pluginAuthMethod: new FormControl(this.authList[0].id),
    pluginApiAuth: new FormControl(this.userAuthRadioList[0].label),
    isInputList: new FormControl(false),
    isOutputList: new FormControl(false),
    intf_type: new FormControl(false),
    auth_required: new FormControl(this.authConfigRadioList[0].id),
    metadata: new FormControl(''),
    protocol: new FormControl('https', []),
    host: new FormControl('', [CommonValidation.pluginParamHostVerify(this.i18n.transform('plugin_host_error'))]),
    baseURL: new FormControl('', [CommonValidation.pluginParamBaseUrlVerify(this.i18n.transform('plugin_baseURL_error'))]),
    callMode: new FormControl('api', []),
    iamUrl: new FormControl('', []),
    sgovUrl: new FormControl('', []),
    credential: new FormControl(''),
    appId: new FormControl(''),
    iamProject: new FormControl(''),
    iamAccount: new FormControl(''),
    iamSecret: new FormControl(''),
    iamEnterprise: new FormControl(''),
    iamDomain: new FormControl(''),
    iamUser: new FormControl(''),
    iamPassword: new FormControl(''),
    iamAK: new FormControl(''),
    iamSK: new FormControl(''),
    verify: new FormControl('iam'),
  });

  hostError = '';
  baseURLError = '';
  pluginZhNameError = '';
  pluginDescriptionError = '';

  get callModeIsFunctionGraph() {
    return this.groupFormControl.controls.callMode.value === 'functiongraph';
  }

  // 导入openAPI相关
  isImport = false; // 标志是否是通过解析openAPI文件创建的插件
  importedPlugin: IPluginWithTools; // 记录解析的插件结果，点击创建时可直接提取工具

  ngOnInit() {
    this.isOp = this.ctxServ.isOpAccount;
    this.isHideFg = true;
    this.authList = this.authRadioList.filter(item => item?.show);
    this.showTips = StorageService.getLocalStorage(CREATE_ALERT_TIPS_STKEY) !== 0;
    this.isLocked = !isNil(this.lockedStep);
    this.step = this.lockedStep ?? 0;
    if (this.pluginInfo) {
      this.modalTitle = this.i18n.transform('update_plugin');
      this.pluginDetail = this.plugin2PluginDetail(this.pluginInfo);
      this.InitPluginConfigs();
    }

    if (this.isLocked) {
      this.modalTitle = this.i18n.transform('update_plugin').concat('-', this.i18n.transform(`modify_plugin_${this.lockedStep}`));
    }

    this.groupFormControl.controls.baseURL.valueChanges.subscribe(() => {
      this.onPathChange();
    });
    this.groupFormControl.controls.host.valueChanges.subscribe(() => {
      this.onPathChange();
    });
    this.groupFormControl.controls.protocol.valueChanges.subscribe(() => {
      this.onPathChange();
    });
  }

  ngOnDestroy(): void {
    this.agentDataServe.setPluginDebugRes('');
  }

  InitPluginConfigs(): void {
    this.groupFormControl.controls.visibility.setValue(this.pluginDetail.visibility === 'user');
    if (this.pluginId) {
      this.groupFormControl.controls.callMode.disable();
      this.groupFormControl.controls.visibility.disable();
      this.groupFormControl.controls.host.setValue(this.pluginInfo.request_info.basic_info.host);
      this.groupFormControl.controls.baseURL.setValue(this.pluginInfo.request_info.basic_info.path);
      const pathList = pluginSchemaStr2Path(this.pluginInfo.request_info.basic_info?.input_schema);
      this.InitPathConfigs(pathList);
      this.groupFormControl.controls.protocol.setValue(this.pluginInfo.request_info.basic_info.protocol);
    }
    this.groupFormControl.controls.pluginName.setValue(this.pluginDetail.name);
    this.groupFormControl.controls.pluginZhName.setValue(this.pluginDetail.tool_chinese_name);
    this.groupFormControl.controls.pluginDescription.setValue(this.pluginDetail.description);
    this.groupFormControl.controls.pluginMethod.setValue(this.pluginDetail.method.toUpperCase());
    this.groupFormControl.controls.pluginLogo.setValue(this.pluginDetail.logo);
    this.groupFormControl.controls.isInputList.setValue(this.pluginDetail.is_input_list);
    this.groupFormControl.controls.callMode.setValue(this.pluginDetail.call_mode);
    this.groupFormControl.controls.isOutputList.setValue(this.pluginDetail.is_output_list);
    this.groupFormControl.controls.intf_type.setValue(this.pluginDetail.intf_type === 'streaming');
    if (this.pluginDetail.auth_required) {
      this.groupFormControl.controls.auth_required.setValue(this.pluginDetail.auth_required.toString());
      this.groupFormControl.controls.metadata.setValidators([]);
      this.groupFormControl.controls.metadata.setValue(this.pluginDetail.metadata);
    }

    this.InitAuthConfigs();
  }

  InitAuthConfigs(): void {
    if (Object.keys(this.pluginDetail.auth).length > 0) {
      if (this.pluginDetail.auth?.scope === 'SERVICE') {
        this.groupFormControl.controls.pluginAuthMethod.setValue(this.authRadioList[1].id);
        if ('headers' in this.pluginDetail.auth) {
          this.groupFormControl.controls.pluginApiAuth.setValue(this.userAuthRadioList[0].label);

          this.apiKeyAuthArgs = Object.keys(this.pluginDetail.auth.headers).map(key => ({
            name: key,
            value: this.pluginDetail.auth.headers[key],
          }));
        } else {
          this.groupFormControl.controls.pluginApiAuth.setValue(this.userAuthRadioList[1].label);
          this.apiKeyAuthArgs = Object.keys(this.pluginDetail.auth.query).map(key => ({
            name: key,
            value: '',
          }));
        }

        this.originKeys = this.apiKeyAuthArgs.map(arg => arg.name);
      }
      if (this.pluginDetail.auth?.scope === 'HIS_IAM') {
        let auth_info = this.pluginDetail.auth.his_iam_info;
        this.groupFormControl.controls.pluginAuthMethod.setValue('HIS_IAM');
        this.groupFormControl.controls.iamUrl.setValue(auth_info.iam_url);
        this.groupFormControl.controls.iamAccount.setValue(auth_info.iam_account);
        this.groupFormControl.controls.iamProject.setValue(auth_info.iam_project);
        this.groupFormControl.controls.iamSecret.setValue('');
        this.groupFormControl.controls.iamEnterprise.setValue(auth_info.iam_enterprise);
      }

      if (this.pluginDetail.auth?.scope === 'SGOV') {
        let auth_info = this.pluginDetail.auth.his_sgov;
        this.groupFormControl.controls.pluginAuthMethod.setValue('SGOV');
        this.groupFormControl.controls.appId.setValue(auth_info.app_id);
        this.groupFormControl.controls.credential.setValue('');
        this.groupFormControl.controls.sgovUrl.setValue(auth_info.sgov_url);
      }

      if (this.pluginDetail.auth?.scope === 'CUSTOM_IAM') {
        let auth_info = this.pluginDetail.auth.custom_iam_credentials;
        this.groupFormControl.controls.pluginAuthMethod.setValue('CUSTOM_IAM');
        this.groupFormControl.controls.iamUrl.setValue(auth_info.iam_url);
        this.groupFormControl.controls.iamDomain.setValue(auth_info.iam_domain);
        this.groupFormControl.controls.iamProject.setValue(auth_info.iam_project);
        this.groupFormControl.controls.iamUser.setValue(auth_info.iam_user);
        if (auth_info.iam_ak) {
          this.groupFormControl.controls.verify.setValue('aksk');
        }
      }

      if (this.pluginDetail.auth?.scope === 'IAM' || this.pluginDetail.auth?.scope === 'HIS') {
        this.groupFormControl.controls.pluginAuthMethod.setValue(this.pluginDetail.auth?.scope);
      }
    }
  }

  dismiss(): void {
    this.closeContainer();
  }

  close(): void {
    this.closeContainer();
  }

  private closeContainer(): void {
    if (this.modalRef) {
      this.modalRef.destroy();
    } else if (this.drawerRef) {
      this.drawerRef.close();
    }
  }

  public isOriginAuth(name: string) {
    return this.originKeys.includes(name);
  }

  public deleteArgs(key: string, index: number) {
    switch (key) {
      case 'userAuthArgs': {
        this.userAuthArgs.splice(index, 1);
        break;
      }
      case 'apiAuth': {
        this.apiKeyAuthArgs.splice(index, 1);
        break;
      }
      default: {
        break;
      }
    }
  }

  public btnDisabledFunc(step: number): boolean {
    const form = this.groupFormControl.controls;
    if (step === 0) {
      if (form.pluginZhName.errors || form.pluginName.errors || form.pluginDescription.errors) {
        return true;
      }
    } else if (step === 1) {
      const formVali = form.host.errors || form.pluginMethod.errors || form.baseURL.errors;
      if (formVali) {
        return true;
      }
      if (form.auth_required.value === 'true' && form.metadata.errors) {
        return true;
      }
      if (form.pluginAuthMethod.value === 'pluginApiKey') {
        if (this.apiAuthForm.invalid) {
          return true;
        }
        return this.apiKeyAuthArgs.some(param => !param.name || !param.value);
      }

      if (form.pluginAuthMethod.value === 'CUSTOM_IAM') {
        let error = null;
        error = form.iamUrl.errors || form.iamDomain.errors || form.iamProject.errors;
        if (form.verify.value === 'iam') {
          error = error || form.iamUser.errors || form.iamPassword.errors;
          return !!error || !form.iamUrl.value || !form.iamDomain.value || !form.iamProject.value || !form.iamUser.value || !form.iamPassword.value;
        } else {
          error = error || form.iamAK.errors || form.iamSK.errors;
          return !!error || !form.iamUrl.value || !form.iamDomain.value || !form.iamProject.value || !form.iamAK.value || !form.iamSK.value;
        }
      }

      if (form.pluginAuthMethod.value === 'HIS_IAM') {
        let error = form.iamUrl.errors || form.iamAccount.errors || form.iamProject.errors || form.iamSecret.errors || form.iamEnterprise.errors;

        return !!error || !form.iamAccount.value || !form.iamUrl.value || !form.iamProject.value || !form.iamSecret.value || !form.iamEnterprise.value;
      }
      if (form.pluginAuthMethod.value === 'SGOV') {
        let error = form.appId.errors || form.credential.errors || form.sgovUrl.errors;
        return !!error || !form.appId.value || !form.credential.value || !form.sgovUrl.value;
      } else {
        this.groupFormControl.controls.auth_required.setValue('false');
      }
    } else if (step === 2) {
      return false;
    }
    return false;
  }

  laststep(): void {
    this.step -= 1;
    this.activeStep = this.steps[this.step];
  }

  nextstep(): void {
    if (this.step === 1) {
      if (this.groupFormControl.controls.auth_required.value === 'true') {
      }

      if (this.groupFormControl.controls.pluginAuthMethod.value === 'pluginApiKey') {
        return;
      }
    }
    if (this.step === 0) {
      const form = this.groupFormControl.controls;
      if (form.host.value.includes('\n')) {
        form.host.setValue(form.host.value.replaceAll('\n', ''));
      }
      if (form.baseURL.value.includes('\n')) {
        form.baseURL.setValue(form.baseURL.value.replaceAll('\n', ''));
      }
    }
    this.step += 1;
    this.activeStep = this.steps[this.step];
  }

  async onConfirm() {
    if (this.groupFormControl.controls.auth_required.value === 'true' && !showFromError(this, this.groupFormControl)) {
      return;
    }

    if (
      this.groupFormControl.controls.pluginAuthMethod.value !== 'pluginNoNeedAuth' &&
      this.groupFormControl.controls.pluginAuthMethod.value !== 'pluginApiKey' &&
      !showFromError(this, this.groupFormControl)
    ) {
      return;
    }

    // 提交前校验完整URL长度，与后端 requestInfo.url @Length(max=256) 一致
    const form = this.groupFormControl.controls;
    if (form.host.value && form.baseURL.value) {
      const fullUrl = `${form.protocol.value}://${form.host.value}${form.baseURL.value}`;
      if (fullUrl.length > 256) {
        this.baseURLError = '协议+域名+基准URL拼接后长度不能超过256';
        return;
      }
    }

    const data = this.buildRequestBody();
    this.loading = true;
    if (this.pluginId) {
      await this.updatePlugin(data);
    } else {
      await this.registerPlugin(data);
    }
    this.loading = false;
  }

  async updatePlugin(data) {
    const params = {
      data: this.pluginDetail2Plugin(data),
      id: this.pluginId,
    };
    if (this.lockedStep !== 1) {
      delete params.data.auth_info;
    }
    try {
      await this.appPluginRepoServ.updatePlugins(params);
      this.confirm.emit();
      this.closeContainer();
      MessageComponent.showSuccess(this.i18n.transform('update_plugin_success'), 3000);
      this.close();
    } catch (error) {
      handleCommonReqError(error);
    } finally {
      this.cdr.detectChanges();
    }
  }

  async registerPlugin(data) {
    try {
      const subscribeBtnStatus = this.commonService.getSubscribeStatus();
      if (!subscribeBtnStatus && CommonUtils.judeg_develop_space()) {
        const thisNzModal: any = this.nzModal.create({
          nzContent: CreateTipModalComponent,
          nzWidth: '700px',
          nzClosable: false,
        });
        return;
      }
      const params = this.pluginDetail2Plugin(data);
      const res = await this.appPluginRepoServ.registerPlugins(params);
      let total: number;
      let isCreateToolsSuccess = true;
      // 如果是通过导入创建，还需要创建工具
      if (this.isImport) {
        try {
          const tools: IToolCreate[] = this.extractToolsFromPlugin(this.importedPlugin, res.tool_id);
          if (tools.length === 0) {
            return;
          }
          total = tools.length;
          await this.appPluginRepoServ.registerToolBatch(tools);
        } catch (e) {
          isCreateToolsSuccess = false;
          MessageComponent.showError(this.i18n.transform('addpluginmodalcomponent_259'));
        }
      }

      this.agentDataServe.setClickFlagPlugin('create');
      this.confirm.emit();
      this.closeContainer();
      this.close();
      let from_id = '';
      let agent_node = '';
      if (this.usedFrom === 'flow') {
        from_id = this.route.snapshot.queryParams.id;
        agent_node = this.agentNode;
        await this.router.navigate(['/home/agent-center/app-flow/flow'], {
          queryParams: { id: from_id },
          state: { currentModal: 'plugin', new_plugin_id: res.tool_id },
        });
      } else {
        if (this.usedFrom === 'agent') {
          from_id = this.route.snapshot.queryParams.agentId;
        }
        await this.router.navigate(['/home/agent-center/custom-plugin/detail'], {
          queryParams: {
            id: res.tool_id,
            from: this.usedFrom,
            from_id,
            agent_node,
          },
        });
      }
      if (!this.isImport) {
        MessageComponent.showSuccess(this.i18n.transform('addpluginmodalcomponent_257'));
      } else if (isCreateToolsSuccess) {
        const messageKey = total ? 'addpluginmodalcomponent_258' : 'addpluginmodalcomponent_257';
        MessageComponent.showSuccess(this.i18n.transform(messageKey, { total }));
      } else {
        MessageComponent.showSuccess(this.i18n.transform('addpluginmodalcomponent_261'));
      }
    } catch (error) {
      handleCommonReqError(error);
    } finally {
      this.cdr.detectChanges();
    }
  }

  public importOpenAPI() {
    const thisNzModal: any = this.nzModal.create({
      nzContent: pluginContentImportModal,
      nzWidth: '700px',
    });
    const instance = thisNzModal.getContentComponent();
    instance.importContentType = 'OpenAPI';
    instance.confirm.subscribe((openAPIData: string) => {
      this.appPluginRepoServ.parsePlugin(openAPIData).then((res: IResponse) => {
        const plugin: IPluginWithTools = res.data as IPluginWithTools;
        this.convertImportedPlugin(plugin);
        this.importedPlugin = plugin;
        this.isImport = true;
        thisNzModal.destroy();
        MessageComponent.showPrompt(this.i18n.transform('create_plugin_import_openapi_tip'));
      });
    });
  }

  capitalizeFirstLetter(string) {
    return string.slice(0, 1).toUpperCase() + string.slice(1);
  }

  isObjectLikeType(type: string) {
    return ['object', 'array<object>'].includes(type);
  }

  public hideTips() {
    this.showTips = false;
    StorageService.setLocalStorage(CREATE_ALERT_TIPS_STKEY, 0);
  }

  /** 将流式响应样例转成字符串 */
  public formatJson(item: any): string {
    return JSON.stringify(item, null, 2);
  }

  private buildRequestBody() {
    const authMethod = this.groupFormControl.controls.pluginAuthMethod.value;
    const ApiAuth = this.groupFormControl.controls.pluginApiAuth.value;
    const data = {
      name: this.groupFormControl.controls.pluginName.value,
      tool_chinese_name: this.groupFormControl.controls.pluginZhName.value,
      description: removeHTMLTag(this.groupFormControl.controls.pluginDescription.value),
      visibility: this.groupFormControl.controls.visibility.value ? 'user' : 'project',
      method: this.groupFormControl.controls.pluginMethod.value,
      is_input_list: this.groupFormControl.controls.isInputList.value,
      is_output_list: this.groupFormControl.controls.isOutputList.value,
      intf_type: this.groupFormControl.controls.intf_type.value ? 'streaming' : 'blocking',
      auth_required: this.groupFormControl.controls.auth_required.value === 'true',
      metadata: authMethod === 'pluginApiKey' ? this.groupFormControl.controls.metadata.value : '',
      host: this.groupFormControl.controls.host.value,
      path: this.groupFormControl.controls.baseURL.value,
      logo: null,
      auth: null,
      protocol: this.groupFormControl.controls.protocol.value,
      call_mode: this.groupFormControl.controls.callMode.value,
    };

    let auth: any = {};
    if (authMethod === 'pluginApiKey') {
      auth = ApiAuth === 'Header' ? { scope: 'SERVICE', headers: {} } : { scope: 'SERVICE', query: {} };
      if (ApiAuth === 'Header') {
        for (const param of this.apiKeyAuthArgs) {
          auth.headers[param.name] = param.value;
        }
      } else {
        for (const param of this.apiKeyAuthArgs) {
          auth.query[param.name] = param.value;
        }
      }
    } else if (authMethod === 'HIS_IAM') {
      auth = {
        scope: 'HIS_IAM',
        his_iam_info: {
          iam_url: this.groupFormControl.controls.iamUrl.value,
          iam_project: this.groupFormControl.controls.iamProject.value,
          iam_account: this.groupFormControl.controls.iamAccount.value,
          iam_secret: this.groupFormControl.controls.iamSecret.value,
          iam_enterprise: this.groupFormControl.controls.iamEnterprise.value,
        },
      };
    } else if (authMethod === 'SGOV') {
      auth = {
        scope: 'SGOV',
        his_sgov: {
          app_id: this.groupFormControl.controls.appId.value,
          sgov_url: this.groupFormControl.controls.sgovUrl.value,
          credential: this.groupFormControl.controls.credential.value,
        },
      };
    } else if (authMethod === this.i18n.transform('iam_auth')) {
      auth = {
        scope: 'IAM',
        iam_credentials: {
          projectId: this.projectId,
        },
      };
    } else if (authMethod === 'IAM' || authMethod === 'HIS') {
      auth = {
        scope: authMethod,
        iam_credentials: {
          projectId: this.projectId,
        },
      };
    } else if (authMethod === 'CUSTOM_IAM') {
      auth = {
        scope: 'CUSTOM_IAM',
        custom_iam_credentials: {
          iam_url: this.groupFormControl.controls.iamUrl.value,
          iam_domain: this.groupFormControl.controls.iamDomain.value,
          iam_project: this.groupFormControl.controls.iamProject.value,
          iam_user: this.groupFormControl.controls.iamUser.value,
          iam_password: this.groupFormControl.controls.iamPassword.value,
          iam_ak: this.groupFormControl.controls.iamAK.value,
          iam_sk: this.groupFormControl.controls.iamSK.value,
        },
      };
    } else {
      // do nth
    }

    if (auth) {
      data.auth = auth;
    }

    const logo = this.groupFormControl.controls.pluginLogo.value;
    if (logo && logo !== this.pluginInfo?.icon) {
      data.logo = logo;
    }

    return data;
  }

  /** @param pluginDebug  表示是否为插件调测模式（默认值是false，默认非插件调测） */
  private pluginDetail2Plugin(detail, pluginDebug = false) {
    const input_schema = this.args2JSONSchemaStr(this.patchArgs);
    return {
      tool_display_name: pinyin(detail.tool_chinese_name, { toneType: 'none' }).replace(/ü/g, 'v').replace(/ /g, '').substring(0, 64).trim(),
      tool_desc: detail.description,
      icon: detail.logo,
      visibility: detail.visibility,
      tool_chinese_name: detail.tool_chinese_name,
      request_info: {
        url: `${detail.protocol}://${detail.host}${detail.path}`,
        method: 'GET',
        input_schema,
      },
      auth_info: this.buildAuthInfo(detail.auth),
      call_mode: detail.call_mode,
      auth_required: this.groupFormControl.controls.auth_required.value === 'true',
      metadata: this.groupFormControl.controls.metadata.value,
    };
  }

  /**
   * 将导入的信息填入表单
   * @param plugin IPluginWithTools
   * @private
   */
  private convertImportedPlugin(plugin: IPluginWithTools) {
    this.importedPlugin = plugin;
    this.groupFormControl.patchValue({
      pluginName: plugin.plugin_display_name,
      pluginZhName: plugin.plugin_chinese_name,
      pluginDescription: plugin.plugin_desc,
      protocol: plugin.request_info.basic_info.protocol,
      host: plugin.request_info.basic_info.host,
      baseURL: plugin.request_info.basic_info.path,
    });
  }

  private extractToolsFromPlugin(plugin: IPluginWithTools, plugin_id: string): IToolCreate[] {
    const { protocol, host, path } = plugin.request_info.basic_info;
    return plugin.request_info.tool_info.map(tool => {
      return {
        plugin_id,
        ...(tool as any as IToolCreate), // ITool先转any再转IToolCreate，避免ts报错
        tool_id: undefined,
        request_info: {
          method: tool.method,
          headers: tool.headers,
          url: `${protocol}://${host}${path}${tool.path}`,
        },
        input_schema: plugin.input_schema.find(input_schema => {
          return input_schema.tool_id === tool.tool_id;
        }).input_schema,
        output_schema: plugin.output_schema.find(output_schema => {
          return output_schema.tool_id === tool.tool_id;
        }).output_schema,
        is_input_list: false,
        is_output_list: false,
        intf_type: 'blocking',
      };
    });
  }

  private args2JSONSchemaStr(args: IRequestArgsView[]): string {
    try {
      const schema = view2Schema(args);
      return JSON.stringify(schema) as string;
    } catch (e) {
      return '[]';
    }
  }

  private plugin2PluginDetail(plugin): PluginDetail {
    try {
      return {
        name: plugin.plugin_display_name,
        tool_chinese_name: plugin.plugin_chinese_name,
        description: plugin.plugin_desc,
        url: plugin.request_info.path,
        method: plugin.request_info.method || 'POST',
        headers: plugin.request_info?.headers ?? '',
        visibility: plugin?.visibility ?? 'project',
        logo: plugin?.icon,
        auth: this.buildAuth(plugin?.auth_info),
        call_mode: plugin?.call_mode ? plugin?.call_mode : 'api',
        is_input_list: !!plugin?.is_input_list,
        is_output_list: !!plugin?.is_output_list,
        intf_type: plugin?.intf_type ?? 'blocking',
        auth_required: plugin?.auth_required,
        metadata: plugin?.metadata,
      };
    } catch {
      MessageComponent.showError(this.i18n.transform('plugin_error'));
      return {
        name: '',
        description: '',
        url: '',
        method: '',
        headers: '',
        logo: '',
        auth: '',
        arguments: [],
        visibility: 'project',
        response: [],
        is_input_list: false,
        is_output_list: false,
        intf_type: 'blocking',
        call_mode: 'api',
      };
    }
  }

  private buildAuthInfo(auth: any): IAuthInfo {
    if (Object.keys(auth).length === 0) {
      return {};
    }

    if (auth?.scope === 'SERVICE') {
      const domain = Object.keys(auth).find(key => ['query', 'headers'].includes(key));

      return {
        scope: auth.scope,
        domain: domain.toUpperCase(),
        auth_keys: Object.keys(auth[domain]).map(key => ({
          auth_key: auth[domain][key],
          target_name: key,
        })),
      };
    }

    if (auth?.scope === 'CUSTOM_IAM') {
      return {
        scope: auth.scope,
        custom_iam_credentials: auth.custom_iam_credentials,
      };
    }

    if (auth?.scope === 'IAM' || auth?.scope === 'HIS') {
      return {
        scope: auth.scope,
        iam_credentials: auth.iam_credentials,
      };
    }
    if (auth?.scope === 'HIS_IAM' || auth?.scope === 'SGOV') {
      return auth;
    }

    return auth;
  }

  private buildAuth(authInfo: IAuthInfo) {
    if (Object.keys(authInfo).length === 0) {
      return {};
    }

    const auth: {
      scope: string;
      [key: string]: any;
    } = {
      scope: authInfo.scope,
    };

    if (authInfo.scope === 'SERVICE') {
      if (authInfo.domain === 'HEADERS') {
        auth.headers = {};
        for (const param of authInfo.auth_keys as IServAuthKV[]) {
          auth.headers[param.target_name] = param?.auth_key;
        }
      } else {
        auth.query = {};
        for (const param of authInfo.auth_keys as IServAuthKV[]) {
          auth.query[param.target_name] = param?.auth_key;
        }
      }
    } else if (authInfo.scope === 'IAM') {
      auth.iam_credentials = authInfo.iam_credentials;
    } else if (authInfo.scope === 'HIS_IAM' || authInfo.scope === 'SGOV' || authInfo.scope === 'CUSTOM_IAM') {
      // do nothing
      return authInfo;
    } else {
      auth.source = {
        domain: authInfo.domain?.toLowerCase(),
        auth_keys: [],
      };
      auth.target = {
        domain: authInfo.domain?.toLowerCase(),
        auth_keys: [],
      };

      (authInfo.auth_keys as IUserAuthKV[])?.forEach(authItem => {
        auth.source.auth_keys.push(authItem.source_name);
        auth.target.auth_keys.push(authItem.target_name);
      });
    }

    return auth;
  }

  changeType(item) {
    if (item === 'api') {
      this.steps = [
        {
          label: this.i18n.transform('basic_info'),
        },
        {
          label: this.i18n.transform('config_info'),
        },
      ];
    } else {
      this.steps = [
        {
          label: this.i18n.transform('basic_info'),
        },
      ];
    }
    this.activeStep = this.steps[this.step];
  }

  changeAuthType(auth) {
    this.resetControl();
    if (auth === 'pluginApiKey') {
      this.groupFormControl.controls.metadata.setValidators([]);
    }
    if (auth === 'HIS_IAM') {
      this.groupFormControl.controls.iamUrl.setValidators([]);
      this.groupFormControl.controls.iamAccount.setValidators([]);
      this.groupFormControl.controls.iamProject.setValidators([]);
      this.groupFormControl.controls.iamSecret.setValidators([]);
      this.groupFormControl.controls.iamEnterprise.setValidators([]);
    }

    if (auth === 'SGOV') {
      this.groupFormControl.controls.sgovUrl.setValidators([]);
      this.groupFormControl.controls.appId.setValidators([]);
      this.groupFormControl.controls.credential.setValidators([]);
    }

    if (auth === 'CUSTOM_IAM') {
      this.groupFormControl.controls.iamUrl.setValidators([]);
      this.groupFormControl.controls.iamDomain.setValidators([]);
      this.groupFormControl.controls.iamProject.setValidators([]);
      this.groupFormControl.controls.iamUser.setValidators([]);
      this.groupFormControl.controls.iamPassword.setValidators([]);
    }
  }

  resetControl() {
    this.groupFormControl.controls.sgovUrl.setValidators([]);
    this.groupFormControl.controls.appId.setValidators([]);
    this.groupFormControl.controls.credential.setValidators([]);
    this.groupFormControl.controls.iamUrl.setValidators([]);
    this.groupFormControl.controls.iamAccount.setValidators([]);
    this.groupFormControl.controls.iamProject.setValidators([]);
    this.groupFormControl.controls.iamSecret.setValidators([]);
    this.groupFormControl.controls.iamEnterprise.setValidators([]);
    this.groupFormControl.controls.metadata.setValidators([]);
    this.groupFormControl.controls.iamUser.setValidators([]);
    this.groupFormControl.controls.iamDomain.setValidators([]);
    this.groupFormControl.controls.iamPassword.setValidators([]);
    this.groupFormControl.controls.iamAK.setValidators([]);
    this.groupFormControl.controls.iamSK.setValidators([]);
  }

  changeVerifyMethod(verify) {
    if (verify === 'iam') {
      this.groupFormControl.controls.iamUser.setValidators([]);
      this.groupFormControl.controls.iamPassword.setValidators([]);
      this.groupFormControl.controls.iamAK.setValidators([]);
      this.groupFormControl.controls.iamSK.setValidators([]);
      this.groupFormControl.controls.iamAK.setValue('');
      this.groupFormControl.controls.iamSK.setValue('');
    } else {
      this.groupFormControl.controls.iamUser.setValue('');
      this.groupFormControl.controls.iamPassword.setValue('');
      this.groupFormControl.controls.iamUser.setValidators([]);
      this.groupFormControl.controls.iamPassword.setValidators([]);
      this.groupFormControl.controls.iamAK.setValidators([]);
      this.groupFormControl.controls.iamSK.setValidators([]);
    }
  }

  addInputParam() {
    this.apiKeyAuthArgs.push({
      name: '',
      value: '',
    });
  }

  public patchArgs: any[] = [];

  InitPathConfigs(input_schema): void {
    if (input_schema?.length > 0) {
      this.patchArgs = input_schema.map(arg => {
        return {
          ...arg,
          depth: 0,
        };
      });
    } else {
      this.patchArgs = [];
    }
    const hostPatchList = this.groupFormControl.controls.host.value.match(/{[a-zA-Z0-9_-]+}/g) ?? [];
    const baseUrlPatchList = this.groupFormControl.controls.baseURL.value.match(/{[a-zA-Z0-9_-]+}/g) ?? [];
    this.variables = hostPatchList.map(item => {
      const name = item.replace('{', '').replace('}', '');
      return { type: 'text' as any, value: name };
    });
    this.initVariables = this.variables;
    this.variablesBase = baseUrlPatchList.map(item => {
      const name = item.replace('{', '').replace('}', '');
      return { type: 'text' as any, value: name };
    });
    this.initVariablesBase = this.variablesBase;
  }

  onPathChange() {
    const form = this.groupFormControl.controls;
    if (form.host.value.includes('\n')) {
      form.host.setValue(form.host.value.replaceAll('\n', ''));
    }
    if (form.baseURL.value.includes('\n')) {
      form.baseURL.setValue(form.baseURL.value.replaceAll('\n', ''));
    }
    if (form.host.errors) {
      this.hostError = form.host.errors.serviceName?.tiErrorMessage ?? 'Error';
    } else {
      this.hostError = '';
    }
    if (form.baseURL.errors) {
      this.baseURLError = form.baseURL.errors.serviceName?.tiErrorMessage ?? 'Error';
    } else {
      this.baseURLError = '';
    }
    // 校验拼接后的完整URL长度（协议+host+基准URL），与后端 requestInfo.url 的 @Length(max=256) 保持一致
    if (!this.baseURLError && form.host.value && form.baseURL.value) {
      const fullUrl = `${form.protocol.value}://${form.host.value}${form.baseURL.value}`;
      if (fullUrl.length > 256) {
        this.baseURLError = '协议+域名+基准URL拼接后长度不能超过256';
      }
    }
    const hostPatchList = this.groupFormControl.controls.host.value.match(/{[a-zA-Z0-9_-]+}/g) ?? [];
    let baseUrlPatchList: any = this.groupFormControl.controls.baseURL.value.match(/{[a-zA-Z0-9_-]+}/g) ?? [];
    baseUrlPatchList = baseUrlPatchList.filter((item, index) => baseUrlPatchList.indexOf(item) === index);
    const patchList = [...hostPatchList, ...baseUrlPatchList];
    let newPatchArgs: any[] = [];
    if (patchList) {
      patchList.map(item => {
        const name = item.replace('{', '').replace('}', '');
        const find = this.patchArgs.find(findItem => findItem.name === name);
        if (find) {
          newPatchArgs.push({ ...find });
        } else {
          newPatchArgs.push({
            default: '',
            depth: 0,
            description: '',
            location: 'Path',
            name: name,
            name_cn: '',
            parentType: null,
            required: true,
            type: 'string',
            validate_rule: '',
            validate_type: 'CHAR',
            validated: false,
          });
        }
      });
    }
    this.patchArgs = newPatchArgs;
  }

  isShowInserter: boolean = false;
  variables: Array<{ type: VariableType; value: string }> = [];
  initVariables: Array<{ type: VariableType; value: string }> = [];

  public updateVariables(variables: any) {
    this.variables = variables;
    this.cdr.detectChanges();
    this.onPathChange();
  }

  public hideInserter() {
    this.isShowInserter = false;
  }

  public showInserter() {
    this.isShowInserter = !this.isShowInserter;
  }

  isShowInserterBase: boolean = false;
  variablesBase: Array<{ type: VariableType; value: string }> = [];
  initVariablesBase: Array<{ type: VariableType; value: string }> = [];

  public updateVariablesBase(variables: any) {
    this.variablesBase = variables;
    this.cdr.detectChanges();
    this.onPathChange();
  }

  public hideInserterBase() {
    this.isShowInserterBase = false;
  }

  public showInserterBase() {
    this.isShowInserterBase = !this.isShowInserterBase;
  }

  protected readonly changeUrl = cdnAssetUrl;
}
