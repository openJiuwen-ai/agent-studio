/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-call */
/* eslint-disable @typescript-eslint/no-unsafe-member-access */
/* eslint-disable @typescript-eslint/no-unsafe-argument */
import { ChangeDetectorRef, Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild, inject } from '@angular/core';
import { FormBuilder, FormControl, NgForm, ValidationErrors, Validators } from '@angular/forms';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzTabsModule, NzTabComponent } from 'ng-zorro-antd/tabs';
import { NzTreeModule } from 'ng-zorro-antd/tree';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalModule } from 'ng-zorro-antd/modal';

function treeGetParentNode(data: any[], node: any): any {
  for (const item of data) {
    if (item.children && item.children.includes(node)) {
      return item;
    }
    if (item.children) {
      const parent = treeGetParentNode(item.children, node);
      if (parent) {
        return parent;
      }
    }
  }
  return null;
}

function treeRemoveNode(data: any[], node: any): void {
  const index = data.indexOf(node);
  if (index > -1) {
    data.splice(index, 1);
    return;
  }
  for (const item of data) {
    if (item.children) {
      treeRemoveNode(item.children, node);
    }
  }
}
import { I18nNamespace } from '@i18n';
import { AddPropsIconComponent } from '@routes/agent-center/app-flow/components/add-props-icon/add-props-icon.component';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { ContextService } from '@services/context.service';
import { DateSelectorComponent } from '@shared/components/date-selector/date-selector.component';
import { FlexibleTextFieldComponent } from '@shared/components/flexible-text-field/flexible-text-field.component';
import { NumberRangeComponent } from '@shared/components/number-range/number-range.component';
import {
  IntegerStrValidatorDirective,
  IsEmptyObjDirective,
  NumberStrValidatorDirective,
  PositiveIntValidatorDirective,
  IsEmptyObjReqDirective,
} from '@shared/directives/common-validator.directive';
import {
  EnumStrValidatorDirective,
  IntegerRangeValidatorDirective,
  NonEmptyValidatorDirective,
  NumberRangeValidatorDirective,
  PluginRequestArgsNameValidatorDirective,
  PluginRequestArgsNameValidatorDirectiveNew,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { handleCommonReqError, removeHTMLTag } from 'src/utils/utils';
import { type IPlugin, IReqSchema, IRequestArgsView, IResponseArgsView, PluginDetail } from '../app-plugin.interface';
import {
  getInitStrTypeReq,
  getInitStrTypeRes,
  initializeReqItem,
  isSimpleType,
  pluginSchemaStr2Args,
  pluginSchemaStr2Path,
  pluginSchemaStr2Res,
  resSchema2View,
  resView2Schema,
  schema2View,
  STREAM_RESPONSE_EXAMPLE,
  view2Schema,
  reqSchemaStr2Field,
  resSchemaStr2Field,
  IWorkflowFieldListToSchema,
  IWFViewListToSchema,
  mapTreeAddKeyIndex,
} from '../utils';
import { StreamResponseTipComponent } from '@shared/components/stream-response-tip/stream-response-tip.component';
import { PluginDebugModalComponent } from '../components/plugin-debug-modal/plugin-debug-modal.component';
import { ImportRequestModalComponent } from '../components/import-request-modal/import-request-modal.component';
import { environment } from 'src/environment/environment';
import { Subject, takeUntil } from 'rxjs';
import { CollapseText } from '@routes/agent-center/app-plugin/components/collapse-text/collapse-text';
import { PluginFunctionComponent } from '@routes/agent-center/app-plugin/components/plugin-function/plugin-function.component';
import { CommonService } from '@services/common.service';
import { EnvManagementService } from '@routes/platform-management/environment-management/env-management.service';
import { MonacoEditorConstructionOptions, MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { pluginContentImportModal } from '@routes/agent-center/app-plugin/components/import-openapi-modal/plugin-content-import-modal.component';
import { IParamRef, IWFView, IWorkflowField } from '@routes/agent-center/app-flow/node.type';
import { NodeUtils } from '@routes/agent-center/app-flow/components/utils';
import { SwaggerTreeConvertService } from '@routes/agent-center/app-plugin/plugin-action-detail/swagger-tree-convert.service';
const CREATE_ALERT_TIPS_STKEY = 'create_alert_tips_stkey';

@Component({
  selector: 'create-tool',
  templateUrl: './create-tool.html',
  styleUrls: ['./create-tool.scss'],
  standalone: true,
  imports: [
    MODULES,
    NzAlertModule,
    NzButtonModule,
    NzSpaceModule,
    NzFormModule,
    NzInputModule,
    NzSelectModule,
    NzSwitchModule,
    NzCheckboxModule,
    NzTabsModule,
    NzTreeModule,
    NzEmptyModule,
    NzModalModule,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    PluginRequestArgsNameValidatorDirectiveNew,
    PluginRequestArgsNameValidatorDirective,
    NumberStrValidatorDirective,
    EnumStrValidatorDirective,
    NumberRangeValidatorDirective,
    IntegerRangeValidatorDirective,
    IntegerStrValidatorDirective,
    NumberRangeComponent,
    DateSelectorComponent,
    FlexibleTextFieldComponent,
    IsEmptyObjDirective,
    AddPropsIconComponent,
    PositiveIntValidatorDirective,
    StreamResponseTipComponent,
    CollapseText,
    PluginFunctionComponent,
    IsEmptyObjReqDirective,
    MonacoEditorModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzModalService,
  ],
})
export class CreateToolComponent implements OnInit {
  readonly modalRef = inject(NzModalRef);

  @Input('pluginInfo') pluginInfo;

  @Input('toolInfo') toolInfo: IPlugin;

  @Input('toolId') toolId: string;

  @Input('lockedStep') lockedStep: number;

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('responseForm') responseForm: NgForm;

  @ViewChild('pathForm') pathForm: NgForm;

  @Output('confirm') confirm = new EventEmitter<void>();

  public isPOC = environment.envType === 'poc'; // 当前是否为POC环境

  public pluginDetail: PluginDetail = {
    name: '',
    description: '',
    tool_chinese_name: '',
    url: '',
    method: '',
    headers: '',
    visibility: 'user',
    logo: '',
    auth: '',
    arguments: [
      {
        default: 'application/json',
        depth: 0,
        description: 'Content-Type',
        location: 'Headers',
        name: 'Content-Type',
        name_cn: '',
        parentType: 'none',
        required: true,
        type: 'string',
        validate_rule: '',
        validate_type: 'CHAR',
        validated: false,
      },
    ],
    response: '',
    is_input_list: false,
    is_output_list: false,
    intf_type: 'blocking',
    auth_required: false,
    metadata: '',
  };

  isSimpleType = isSimpleType;

  public pluginReqWrapTips = this.i18n.transform('plugin_req_wrap_tip');

  public pluginResWrapTips = this.i18n.transform('plugin_res_wrap_tip');

  private destroy$ = new Subject<void>();

  public inputParams: IWorkflowField[] = [];

  public outputParams: IWFView[] = [];

  public nameRefOptions: IParamRef[] = [];

  editCodeModal = false;

  constructor(
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private fb: FormBuilder,
    private appPluginRepoServ: AppPluginRepoService,
    private agentDataServe: AgentDataService,
    private ctxServ: ContextService,
    private nzModal: NzModalService,
    private elementRef: ElementRef,
    public commonService: CommonService,
    private environmentManagementService: EnvManagementService,
    private swaggerTreeConvertService: SwaggerTreeConvertService
  ) {
    this.agentDataServe
      .pluginDebugResUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((resSchemaStr: string) => {
        if (!resSchemaStr) {
          return;
        }
        this.responseArgs = mapTreeAddKeyIndex(pluginSchemaStr2Res(resSchemaStr), 0);
      });
  }

  colsGap: Array<string> = ['16px'];

  public logo = cdnAssetUrl('assets/agent-center/images/plugin-default.svg');
  public debugIcon = cdnAssetUrl('assets/agent-center/icons/plugin-debug-icon.svg');

  public booleanOps = [
    {
      value: 'true',
      label: 'true',
    },
    {
      value: 'false',
      label: 'false',
    },
  ];

  public methods = [
    {
      label: 'GET',
      value: 'GET',
    },
    {
      label: 'POST',
      value: 'POST',
    },
  ];

  public selectedTab = 'Headers';
  // 表单label
  public createPluginFormLabel = {
    pluginName: this.i18n.transform('plugin_en_name'),
    pluginZhName: this.i18n.transform('plugin_name'),
    ToolName: this.i18n.transform('name'),
    ToolZhName: this.i18n.transform('create-app-name'),
    defaultPlaceholder: this.i18n.transform('input_placeholder'),
    pluginDescription: this.i18n.transform('plugin_description'),
    toolDescription: this.i18n.transform('description'),
    pluginURL: this.i18n.transform('plugin_url'),
    toolURL: this.i18n.transform('tool_url'),
    pluginMethod: this.i18n.transform('request_method'),
    pluginAuth: this.i18n.transform('request_auth'),
    pluginAuthLoc: this.i18n.transform('request_secretKey'),
    requestHeader: this.i18n.transform('request_header'),
    requestArguments: this.i18n.transform('request_params'),
    requestResponse: this.i18n.transform('res_params'),
    projectId: this.i18n.transform('project_id'),
    auth_required: this.i18n.transform('auth_required'),
    metadata: this.i18n.transform('metadata'),
  };

  public pluginName: string;

  public modalTitle: string = this.i18n.transform('createtool_777');

  tabs: any = [
    {
      title: this.i18n.transform('createtool_778'),
      active: true,
      id: 'Headers',
    },
    {
      title: this.i18n.transform('createtool_779'),
      active: false,
      id: 'Body',
    },
    {
      title: this.i18n.transform('createtool_780'),
      active: false,
      id: 'Query',
    },
    {
      title: this.i18n.transform('createtool_781'),
      active: false,
      id: 'Path',
    },
  ];

  tabsTip = [
    this.i18n.transform('createtool_782'),
    this.i18n.transform('createtool_783'),
    this.i18n.transform('createtool_784'),
    this.i18n.transform('createtool_785'),
  ];

  public editorOptions: MonacoEditorConstructionOptions = {
    theme: 'vs-dark',
    language: 'json',
    lineNumbers: 'on',
    readOnly: false,
    minimap: {
      enabled: false,
    },
  };

  steps: Array<any> = [
    {
      label: this.i18n.transform('basic_info'),
    },
    {
      label: this.i18n.transform('params_info'),
    },
  ];

  step = 0;

  showTips = true;

  public loading = false;

  public projectId = '';

  public isLocked = false;

  private originKeys = [];

  public changeUrl = cdnAssetUrl;

  public emptyImage = null;

  @ViewChild('requestArgsForm') requestArgsForm: NgForm;

  public get requestArgValidates() {
    return this.requestArgs.filter(args => this.selectedTab && args.validated);
  }

  public requestArgs: IRequestArgsView[] = [
    {
      name: '',
      name_cn: '',
      description: '',
      type: 'string',
      location: 'Body',
      required: true,
      default: '',
      validated: false,
      validate_rule: '',
      validate_type: 'CHAR',
      visible: true,
      depth: 0,
      parentType: 'none',
      keyindex: '0_0',
    },
  ];

  public showParams(id): any[] {
    return this.requestArgs.filter(args => args.location === id);
  }

  public responseArgs: any[] = [];

  public patchArgs: any[] = [];

  public strValidateOps = [
    {
      label: this.i18n.transform('char_label'),
      value: 'CHAR',
    },
    {
      label: this.i18n.transform('enum_label'),
      value: 'ENUM',
    },
    {
      label: this.i18n.transform('date_label'),
      value: 'DATE',
    },
  ];

  public numberValidateOps = [
    {
      label: this.i18n.transform('num_label'),
      value: 'NUM',
    },
  ];

  public headers: { key: string; value: string }[] = [
    {
      key: 'Content-Type',
      value: 'application/json',
    },
  ];

  public reqeustArgTypeOptions = [
    { label: 'String', value: 'string' },
    { label: 'Integer', value: 'integer' },
    { label: 'Number', value: 'number' },
    { label: 'Boolean', value: 'boolean' },
    { label: 'Object', value: 'object' },
    { label: 'Array<String>', value: 'array<string>' },
    { label: 'Array<Number>', value: 'array<number>' },
    { label: 'Array<Integer>', value: 'array<integer>' },
    { label: 'Array<Boolean>', value: 'array<boolean>' },
    { label: 'Array<Object>', value: 'array<object>' },
  ];

  public reqeustArgNoneObjTypeOptions = [
    { label: 'String', value: 'string' },
    { label: 'Integer', value: 'integer' },
    { label: 'Number', value: 'number' },
    { label: 'Boolean', value: 'boolean' },
    { label: 'Object', value: 'object', disabled: true },
    { label: 'Array<String>', value: 'array<string>', disabled: true },
    { label: 'Array<Number>', value: 'array<number>', disabled: true },
    { label: 'Array<Integer>', value: 'array<integer>', disabled: true },
    { label: 'Array<Boolean>', value: 'array<boolean>', disabled: true },
    { label: 'Array<Object>', value: 'array<object>', disabled: true },
  ];

  public isOp = false;

  public streamResExamples = STREAM_RESPONSE_EXAMPLE;

  public functionSelected = '';
  public groupFormControl = this.fb.group({
    pluginName: new FormControl('', [
      Validators.required,
      CommonValidation.toolNameVerify(this.i18n.transform('tool_name_validation_required'), this.i18n.transform('tool_name_validation_formatter')),
    ]),
    pluginZhName: new FormControl('', [
      Validators.required,
      CommonValidation.toolZhNameVerify(this.i18n.transform('tool_display_name_validation_required'), this.i18n.transform('tool_zh_name_validation_formatter')),
    ]),
    pluginDescription: new FormControl('', [Validators.required]),
    pluginLogo: new FormControl(''),
    visibility: new FormControl(false),
    pluginURL: new FormControl('/', [
      CommonValidation.pluginParamToolPathVerify(this.i18n.transform('plugin_tool_path_error')),
      Validators.minLength(1), // 最小长度为1
      Validators.maxLength(256), // 最大长度为256
    ]),
    pluginMethod: new FormControl('GET', [Validators.required]),
    isInputList: new FormControl(false),
    isOutputList: new FormControl(false),
    intf_type: new FormControl(false),
  });

  tabSelectIndex = 0;

  ngOnInit() {
    this.isOp = this.ctxServ.isOpAccount;

    this.showTips = StorageService.getLocalStorage(CREATE_ALERT_TIPS_STKEY) !== 0;
    if (!this.toolId) {
      this.modalTitle = this.i18n.transform('createtool_777');
    } else {
      this.modalTitle = this.i18n.transform('createtool_786');
      this.pluginDetail = this.plugin2PluginDetail(this.toolInfo);
      this.functionSelected = this.toolInfo.function_id;
      this.inputParams = reqSchemaStr2Field(this.toolInfo.input_schema);
      this.outputParams = NodeUtils.fields2Views(resSchemaStr2Field(this.toolInfo.output_schema));
    }
    this.InitPluginConfigs();
  }

  ngOnDestroy(): void {
    this.agentDataServe.setPluginDebugRes('');
  }

  InitPluginConfigs(): void {
    this.groupFormControl.controls.visibility.setValue(this.pluginDetail.visibility === 'user');
    if (this.toolId) {
      this.groupFormControl.controls.visibility.disable();
    }
    this.groupFormControl.controls.pluginName.setValue(this.pluginDetail.name);
    this.groupFormControl.controls.pluginZhName.setValue(this.pluginDetail.tool_chinese_name);
    this.groupFormControl.controls.pluginDescription.setValue(this.pluginDetail.description);
    this.groupFormControl.controls.pluginURL.setValue(this.pluginDetail.url);
    this.groupFormControl.controls.pluginMethod.setValue(this.pluginDetail.method.toUpperCase());
    this.groupFormControl.controls.pluginLogo.setValue(this.pluginDetail.logo);
    this.groupFormControl.controls.isInputList.setValue(this.pluginDetail.is_input_list);
    this.groupFormControl.controls.isOutputList.setValue(this.pluginDetail.is_output_list);
    this.groupFormControl.controls.intf_type.setValue(this.pluginDetail.intf_type === 'streaming');
    if (Object.keys(this.pluginDetail.headers).length > 0) {
      this.headers = Object.keys(this.pluginDetail.headers).map(key => ({
        key,
        value: this.pluginDetail.headers[key],
      }));
    }

    this.InitRequestConfigs();
    this.InitResponseConfigs();
  }

  InitRequestConfigs(): void {
    if (this.pluginDetail.arguments.length > 0) {
      this.requestArgs = this.pluginDetail.arguments.map(arg => {
        return {
          ...arg,
          depth: arg?.depth ?? 0,
        };
      });
      this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
    } else {
      this.requestArgs = [];
    }
  }

  InitPathConfigs(input_schema): void {
    if (input_schema.length > 0) {
      this.patchArgs = input_schema.map(arg => {
        return {
          ...arg,
          depth: 0,
        };
      });
      this.patchArgs = mapTreeAddKeyIndex(this.patchArgs, 0);
    } else {
      this.patchArgs = [];
    }
  }

  getReqLayerIndexWidth(param: IRequestArgsView) {
    const map = {
      0: '200px',
      1: '176px',
      2: '152px',
      3: '128px',
    };

    const mapWithChildren = {
      0: '180px',
      1: '156px',
      2: '132px',
    };

    return param?.children ? mapWithChildren[param.depth] : map[param.depth];
  }

  getResLayerIndexWidth(param: IRequestArgsView) {
    const map = {
      0: '280px',
      1: '256px',
      2: '232px',
      3: '208px',
    };

    const mapWithChildren = {
      0: '260px',
      1: '236px',
      2: '212px',
    };

    return param?.children ? mapWithChildren[param.depth] : map[param.depth];
  }

  InitResponseConfigs(): void {
    if (this.pluginDetail.response.length > 0) {
      this.responseArgs = mapTreeAddKeyIndex(
        this.pluginDetail.response.map(arg => {
          return {
            ...arg,
            depth: arg?.depth ?? 0,
          };
        }),
        0
      );
    }
  }

  dismiss(): void {
    this.modalRef.destroy();
  }

  close(): void {}

  public isOriginAuth(name: string) {
    return this.originKeys.includes(name);
  }

  public removeArg(param: IRequestArgsView | IResponseArgsView, type: 'req' | 'res') {
    const data = type === 'req' ? this.requestArgs : this.responseArgs;
    const parentNodeParam = treeGetParentNode(data, param) as IRequestArgsView;
    treeRemoveNode(data, param);

    if (this.isObjectLikeType(parentNodeParam?.type) && parentNodeParam?.children?.length === 0) {
      delete parentNodeParam.children;
    }
    if (type === 'req') {
      this.onInput();
    } else {
      this.onResponseInput();
    }
  }

  public deleteArgs(key: string, index: number) {
    switch (key) {
      case 'requestArgs': {
        this.requestArgs.splice(index, 1);
        this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
        break;
      }
      case 'responseArgs': {
        this.responseArgs.splice(index, 1);
        this.responseArgs = mapTreeAddKeyIndex(this.responseArgs, 0);
        break;
      }
      default: {
        break;
      }
    }
  }

  public addArgs(key: string) {
    switch (key) {
      case 'requestArgs': {
        const location = this.selectedTab;
        this.requestArgs.push({
          ...getInitStrTypeReq(location),
          depth: 0,
          parentType: 'none',
        });
        this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
        break;
      }
      case 'responseArgs': {
        this.responseArgs.push({
          ...getInitStrTypeRes(),
          depth: 0,
          parentType: 'none',
        });
        this.responseArgs = mapTreeAddKeyIndex(this.responseArgs, 0);
        break;
      }

      default: {
        break;
      }
    }
    if (key === 'requestArgs') {
      this.onInput();
    } else {
      this.onResponseInput();
    }
  }

  onResponseInput() {
    window.setTimeout(() => {
      this.responseArgs = mapTreeAddKeyIndex(this.responseArgs, 0);
      if (!this.responseForm) {
        return;
      }
      this.responseForm.control.markAllAsTouched();
    });
  }

  onInput() {
    window.setTimeout(() => {
      this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
      if (!this.inputForm) {
        return;
      }
      this.inputForm.control.markAllAsTouched();
    });
  }

  onParamTypeChange(param: IRequestArgsView) {
    if (!this.isSimpleType(param.type)) {
      param.validated = false;
      param.default = '';
    } else {
      delete param?.children;

      if (param.type === 'string') {
        param.validate_type = 'CHAR';
      } else {
        param.validate_type = 'NUM';
      }
    }

    if (param.type.startsWith('array') && param.type !== 'array<object>' && param?.children) {
      delete param?.children;
    }

    if (this.isObjectLikeType(param.type)) {
      if (!param?.children) {
        this.addReqObjProps(param);
      }
    }

    if (param.type !== 'string' && param.location === 'Headers') {
      param.location = 'Body';
    }
  }

  onPluginURLChange() {
    const patchList = this.groupFormControl.controls.pluginURL.value.match(/{[a-zA-Z0-9_-]+}/g);
    const newPatchArgs: any[] = [];
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
      this.patchArgs = mapTreeAddKeyIndex(newPatchArgs, 0);
    } else {
      this.patchArgs = [];
    }
  }

  showReqPropsDelete(param: IRequestArgsView) {
    if (param.depth === 0 && this.requestArgs.length === 1) {
      if (this.groupFormControl.controls.pluginMethod.value === 'GET') {
        return true;
      }

      return false;
    }

    return true;
  }

  showResPropsDelete(param: IResponseArgsView) {
    return true;
  }

  onResParamTypeChange(param: IResponseArgsView) {
    if (this.isSimpleType(param.type) && param?.children) {
      delete param?.children;
    }

    if (param.type.startsWith('array') && param.type !== 'array<object>' && param?.children) {
      delete param?.children;
    }

    if (this.isObjectLikeType(param.type)) {
      if (!param?.children) {
        this.addResObjProps(param);
      }
    }

    this.responseArgs = mapTreeAddKeyIndex(this.responseArgs, 0);
  }

  getResExistingNames(args: IResponseArgsView): string[] {
    let names = [];
    if (args.depth === 0) {
      names = this.responseArgs.map(arg => arg.name);
    } else {
      const parentNode = treeGetParentNode(this.responseArgs, args);
      names = parentNode?.children.map(arg => arg.name);
    }

    names?.splice(names.indexOf(args.name), 1);
    return names;
  }

  getReqExistingNames(args: IRequestArgsView): string[] {
    let names = [];
    if (args.depth === 0) {
      names = this.requestArgs.map(arg => arg.name);
    } else {
      const parentNode = treeGetParentNode(this.requestArgs, args);
      names = parentNode?.children.map(arg => arg.name);
    }

    names.splice(names.indexOf(args.name), 1);
    return names;
  }

  deleteHeader(index: number) {
    this.headers.splice(index, 1);
  }

  addHeader() {
    this.headers.push({
      key: '',
      value: '',
    });
  }

  isLegalString(name: string, regTem: RegExp): boolean {
    return regTem.test(name);
  }

  addResObjProps(param: IResponseArgsView) {
    const child = {
      ...getInitStrTypeRes(),
      depth: param.depth + 1,
      parentType: param.parentType,
    };

    if (param?.children) {
      param.children.push(child);
    } else {
      param.children = [child];
    }

    this.responseArgs = mapTreeAddKeyIndex(this.responseArgs, 0);
    param.expanded = true;
    this.onResponseInput();
  }

  addReqObjProps(param: IRequestArgsView) {
    const location = this.selectedTab;
    const child = {
      ...getInitStrTypeReq(location),
      depth: param.depth + 1,
      parentType: param.parentType,
    };

    if (param?.children) {
      param.children.push(child);
    } else {
      param.children = [child];
    }
    this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
    param.expanded = true;
    this.onInput();
  }

  showFromError(form): boolean {
    form.markAllAsTouched();
    const errors: ValidationErrors | null = form.invalid ? {} : null;
    if (errors && Object.keys(errors).length > 0) {
      const firstError: any = Object.keys(errors)[0];

      if (this.elementRef.nativeElement.querySelector(`[formControlName=${firstError}]`)) {
        this.elementRef.nativeElement.querySelector(`[formControlName=${firstError}]`)?.focus();
      } else {
        this.elementRef.nativeElement.querySelector(`[name=${firstError}]`)?.focus();
      }
      return false;
    }
    return true;
  }

  showFromErrorByName(form, validatorName, showSelect = false, forceTab = -1): boolean {
    let errorIndex = -1;
    let res = true;
    const keysList = Object.keys(form.controls);
    if (keysList) {
      for (let i = 0; i < keysList.length; i++) {
        form.controls[keysList[i]].markAsDirty();
        form.controls[keysList[i]].updateValueAndValidity({ onlySelf: false });
        if (validatorName?.length > 0) {
          for (let j = 0; j < validatorName.length; j++) {
            if (keysList[i].indexOf(validatorName[j]) === 0) {
              if (form.controls[keysList[i]].errors) {
                if (showSelect) {
                  if (keysList[i].indexOf('Headers') > 0) {
                    errorIndex = 0;
                  } else if (keysList[i].indexOf('Body') > 0) {
                    errorIndex = 1;
                  } else if (keysList[i].indexOf('Query') > 0) {
                    errorIndex = 2;
                  } else if (keysList[i].indexOf('Path') > 0) {
                    errorIndex = 3;
                  } else if (forceTab >= 0) {
                    errorIndex = forceTab;
                  }
                }
                res = false;
              }
            }
          }
        } else {
          if (form.controls[keysList[i]].errors) {
            res = false;
          }
        }
      }
    }

    if (showSelect && errorIndex >= 0) {
      this.tabSelectIndex = errorIndex;
      this.beforeActiveChange(errorIndex);
    }
    return res;
  }

  async onConfirm() {
    if (!this.showFromErrorByName(this.groupFormControl, [])) {
      return;
    }
    if (!this.showFromErrorByName(this.inputForm.form, ['inputFormName', 'inputFormDesc', 'inputFormDefault'], true)) {
      return;
    }
    if (!this.showFromErrorByName(this.responseForm.form, ['responseFormName'])) {
      return;
    }
    if (!this.showFromErrorByName(this.pathForm.form, ['responseFormDesc'], true, 3)) {
      return;
    }
    if (this.requestArgsForm && !this.showFromErrorByName(this.requestArgsForm.form, ['requestValidateRule'], true, 2)) {
      return;
    }

    const data = this.buildRequestBody();
    this.loading = true;
    if (this.toolId) {
      await this.updatePlugin(data);
    } else {
      await this.registerPlugin(data);
    }
    this.loading = false;
  }

  async updatePlugin(data: PluginDetail) {
    const params = {
      data: this.pluginDetail2Plugin(data),
      id: this.toolId,
    };
    if (this.lockedStep !== 1) {
      const key = 'auth_info';
      delete params.data[key];
    }
    try {
      await this.appPluginRepoServ.updateTool(params);
      this.confirm.emit();
      this.modalRef.destroy();
      MessageComponent.showSuccess(this.i18n.transform('update_plugin_success'), 3000);
      this?.close();
    } catch (error) {
      handleCommonReqError(error);
    } finally {
      this.cdr.detectChanges();
    }
  }

  async registerPlugin(data: PluginDetail) {
    try {
      const params = this.pluginDetail2Plugin(data);
      await this.appPluginRepoServ.registerTool(params);
      this.agentDataServe.setClickFlagPlugin('create');
      this.confirm.emit();
      this.modalRef.destroy();
      this.close();
    } catch (error) {
      handleCommonReqError(error);
    } finally {
      this.cdr?.detectChanges();
    }
  }

  public importRequst() {
    const thisNzModal: any = this.nzModal.create({
      nzContent: ImportRequestModalComponent,
      nzWidth: '800px',
      nzClosable: true,
    });

    const instance = thisNzModal.getContentComponent();
    instance.isEdit = !!this.toolInfo;
    instance.pluginInfo = this.pluginInfo;
    instance.confirm.subscribe(json => {
      try {
        const url = new URL(json.url);
        const basePath = this.pluginInfo.request_info.basic_info.path;
        const toolUrl = url.pathname.replace(basePath, '');
        this.groupFormControl.controls.pluginURL.setValue(toolUrl);
      } catch (e) {
        MessageComponent.showPrompt(this.i18n.transform('createtool_787'));
      }
      const method = json.method.toUpperCase();
      if (method === 'GET' || method === 'POST') {
        this.groupFormControl.controls.pluginMethod.setValue(method);
      } else {
        MessageComponent.showPrompt(this.i18n.transform('createtool_788'));
      }

      this.headers = json.headers;
      const headerArgs = json.headers.map(item => ({
        name: item.key,
        depth: 0,
        parentType: 'none',
        required: false,
        default: item.value,
        name_cn: item.key,
        description: item.key,
        type: 'string',
        location: 'Headers',
        validate_rule: '',
        validate_type: 'CHAR',
        validated: false,
      }));

      this.requestArgs = json.params.map(item => ({
        name: item.name,
        depth: 0,
        parentType: 'none',
        required: item.required,
        default: item.default,
        name_cn: '',
        description: item.name,
        type: item.type,
        location: item.location,
        validate_rule: '',
        validate_type: 'CHAR',
        validated: false,
        children: item.type === 'object' ? schema2View(item.schema, 1, 'object') : undefined,
      }));
      this.requestArgs.unshift(...headerArgs);
      this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
    });
  }

  capitalizeFirstLetter(string) {
    return string.slice(0, 1).toUpperCase() + string.slice(1);
  }

  public openDebugModal() {
    if (!this.showFromErrorByName(this.groupFormControl, [])) {
      return;
    }
    if (!this.showFromErrorByName(this.inputForm.form, ['inputFormName', 'inputFormDesc'], true)) {
      return;
    }
    if (!this.showFromErrorByName(this.responseForm.form, ['responseFormName'])) {
      return;
    }
    if (!this.showFromErrorByName(this.pathForm.form, ['responseFormDesc'], true, 3)) {
      return;
    }

    const data = this.buildRequestBody();
    const pluginBodyParams: any = this.pluginDetail2Plugin(data, true);
    pluginBodyParams.request_info.basic_info = this.pluginInfo?.request_info?.basic_info;
    const requestArgs = [...this.requestArgs, ...this.patchArgs].map(item => initializeReqItem(item));
    const thisNzModal: any = this.nzModal.create({
      nzContent: PluginDebugModalComponent,
      nzWidth: '1000px',
      nzClosable: true,
    });
    const instance = thisNzModal.getContentComponent();
    instance.requestArgs = requestArgs;
    instance.pluginBodyParams = pluginBodyParams;
  }

  public hideTips() {
    this.showTips = false;
    StorageService.setLocalStorage(CREATE_ALERT_TIPS_STKEY, 0);
  }

  isObjectLikeType(type: string) {
    return ['object', 'array<object>'].includes(type);
  }

  /** 将流式响应样例转成字符串 */
  public formatJson(item: any): string {
    return JSON.stringify(item, null, 2);
  }

  private buildRequestBody(): PluginDetail {
    const data: PluginDetail = {
      name: this.groupFormControl.controls.pluginName.value,
      tool_chinese_name: this.groupFormControl.controls.pluginZhName.value,
      description: removeHTMLTag(this.groupFormControl.controls.pluginDescription.value),
      url: this.groupFormControl.controls.pluginURL.value,
      visibility: this.groupFormControl.controls.visibility.value ? 'user' : 'project',
      method: this.groupFormControl.controls.pluginMethod.value,
      is_input_list: this.groupFormControl.controls.isInputList.value,
      is_output_list: this.groupFormControl.controls.isOutputList.value,
      intf_type: this.groupFormControl.controls.intf_type.value ? 'streaming' : 'blocking',
    };

    // headers
    if (this.headers.length) {
      const headersObj = {};
      this.headers.forEach(header => {
        headersObj[header.key] = header.value;
      });
      data.headers = headersObj;
    }
    data.arguments = [...this.filterArgs(this.requestArgs), ...this.patchArgs];
    data.response = this.filterArgs(this.responseArgs);

    const logo = this.groupFormControl.controls.pluginLogo.value;
    if (logo && logo !== this.toolInfo?.icon) {
      data.logo = logo;
    }

    return data;
  }

  /**
   * 过滤未填字段
   * @param args
   * */
  private filterArgs(args) {
    const result = [];
    for (const arg of args) {
      // 过滤未填的参数列
      if (arg.name.trim() === '') {
        continue;
      }
      if (arg.children?.length > 0) {
        arg.children = this.filterArgs(arg.children);
      }
      result.push(arg);
    }
    return result;
  }

  /** @param pluginDebug  表示是否为插件调测模式（默认值是false，默认非插件调测） */
  private pluginDetail2Plugin(detail: PluginDetail, pluginDebug = false) {
    const { protocol, host, path } = this.pluginInfo.request_info.basic_info;
    const cleanDetailUrl = detail.url;
    const pluginRaw = {
      plugin_id: this.pluginInfo.plugin_id,
      tool_display_name: detail.name,
      tool_desc: detail.description,
      icon: detail.logo,
      visibility: detail.visibility,
      tool_chinese_name: detail.tool_chinese_name,
      request_info: {
        url: `${protocol}://${host}${path}${cleanDetailUrl}`,
        method: detail.method,
        headers: detail.headers,
      },
      is_input_list: detail.is_input_list,
      is_output_list: detail.is_output_list,
      intf_type: detail.intf_type,
      auth_required: detail.auth_required,
      metadata: detail.metadata,
      output_schema: null,
      input_schema: null,
    };

    if (!pluginDebug) {
      pluginRaw.output_schema = this.res2JSONSchemaStr(detail.response);
    }
    pluginRaw.input_schema = this.args2JSONSchemaStr(detail.arguments);

    return pluginRaw;
  }

  private plugin2PluginDetail(plugin): PluginDetail {
    try {
      const pathList = pluginSchemaStr2Path(plugin?.input_schema);
      this.InitPathConfigs(pathList);
      return {
        name: plugin.tool_display_name,
        tool_chinese_name: plugin.tool_chinese_name,
        description: plugin.tool_desc,
        url: plugin.path,
        method: plugin.method,
        headers: plugin?.headers ?? '',
        visibility: this.pluginInfo.visibility ?? 'project',
        logo: '',
        arguments: pluginSchemaStr2Args(plugin?.input_schema),
        response: pluginSchemaStr2Res(plugin?.output_schema),
        is_input_list: !!plugin?.is_input_list,
        is_output_list: !!plugin?.is_output_list,
        intf_type: plugin?.intf_type ?? 'blocking',
        auth_required: this.pluginInfo.auth_required,
        metadata: this.pluginInfo?.metadata ?? '',
        function_id: this.pluginInfo?.function_id ?? '',
      };
    } catch {
      MessageComponent.showError(this.i18n.transform('plugin_error'));
      this.InitPathConfigs([]);
      return {
        headers: '',
        logo: '',
        auth: '',
        name: '',
        description: '',
        url: '',
        method: '',
        arguments: [],
        visibility: 'project',
        is_input_list: false,
        is_output_list: false,
        response: [],
        intf_type: 'blocking',
      };
    }
  }

  // 递归生成 Schema
  private generateSchema(obj, path = '', location?: string): any {
    const schema: any = {
      type: typeof obj,
      validate_rule: '',
      validate_type: 'CHAR',
      validated: false,
      location,
    };
    // 处理 null
    if (obj === null) {
      schema.type = 'null';
      return schema;
    }

    // 处理数组
    if (Array.isArray(obj)) {
      schema.type = 'array';
      if (obj.length === 0) {
        schema.items = { type: 'any' }; // 空数组，类型未知
      } else {
        // 取第一个元素生成 items
        const firstItem = obj[0];
        let subSchema: any = {};
        if (typeof firstItem !== 'object') {
          // 非对象元素，直接使用元素类型
          subSchema.type = typeof firstItem;
        } else {
          subSchema = this.generateSchema(firstItem, `${path}[0]`, location);
        }
        schema.items = subSchema;
      }
      return schema;
    }

    // 处理对象
    if (typeof obj === 'object') {
      schema.type = 'object';
      schema.properties = {};
      schema.required = [];

      for (const key in obj) {
        if (Object.prototype.hasOwnProperty.call(obj, key)) {
          const value = obj[key];
          const propSchema = this.generateSchema(value, `${path}.${key}`, location);
          propSchema.description = key;
          schema.properties[key] = propSchema;

          // 如果不是 null 或 undefined，认为是必填
          if (value !== null && value !== undefined) {
            schema.required.push(key);
          }
        }
      }

      // 如果没有 required 字段，去掉该属性
      if (schema.required.length === 0) {
        delete schema.required;
      }

      return schema;
    }

    // 处理基本类型
    if (schema.type === 'number') {
      if (Number.isInteger(obj)) {
        schema.type = 'integer';
      }
    }
    // 默认值
    if (schema.type === 'boolean') {
      schema.default = String(obj);
    } else {
      schema.default = obj;
    }

    return schema;
  }

  private JSON2JSONSchema(json: any, location?: string): IReqSchema {
    const schema = this.generateSchema(json, '', location);
    this.filterSchemaByLocation(schema, location);
    return schema;
  }

  private JSON2ReqArgs(json: any, location: string) {
    const schema = this.JSON2JSONSchema(json, location);
    const args: any[] = schema2View(schema);
    if (location === 'Path') {
      this.patchArgs = mapTreeAddKeyIndex(args, 0);
    } else {
      this.requestArgs = this.requestArgs
        .filter(item => {
          return item.location !== location;
        })
        .concat(args);
      this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
    }
  }

  private JSON2ResArgs(json: any, location?: string) {
    const schema = this.JSON2JSONSchema(json, location);
    this.responseArgs = mapTreeAddKeyIndex(resSchema2View(schema), 0);
  }
  private filterSchemaByLocation(schema: any, location: string) {
    if (location === 'Headers') {
      // 请求头参数只有string类型
      Object.keys(schema.properties).forEach(key => {
        if (schema.properties[key].type !== 'string') {
          delete schema.properties[key];
        }
      });
    }
    if (location === 'Query') {
      // 查询参数只有非对象
      Object.keys(schema.properties).forEach(key => {
        if (schema.properties[key].type === 'object' || schema.properties[key].type === 'array') {
          delete schema.properties[key];
        }
      });
    }
  }
  private JSONSchema2Args(schema: any, location: string) {
    Object.keys(schema.properties).forEach(key => {
      schema.properties[key].location = location;
    });
    this.filterSchemaByLocation(schema, location);
    const args = schema2View(schema);
    this.requestArgs = this.requestArgs
      .filter(item => {
        return item.location !== location;
      })
      .concat(args);
    this.requestArgs = mapTreeAddKeyIndex(this.requestArgs, 0);
  }

  private JSONSchema2Res(schema: any) {
    const args = resSchema2View(schema);
    this.responseArgs = mapTreeAddKeyIndex(args, 0);
  }

  private args2JSONSchemaStr(args: IRequestArgsView[], space?: number): string {
    const schema = view2Schema(args);
    return JSON.stringify(schema, null, space) as string;
  }

  private res2JSONSchemaStr(res: IResponseArgsView[], space?: number): string {
    const schema = resView2Schema(res);
    return JSON.stringify(schema, null, space) as string;
  }

  public beforeActiveChange(index: any) {
    this.tabs.forEach((item, i) => {
      item.active = i === index;
    });
    const tab = this.tabs[index];
    if (!this.showFromError(this.inputForm.form)) {
      return;
    }
    if (this.patchArgs && this.patchArgs.length > 0 && !this.showFromError(this.pathForm.form) && tab.id !== 'Path') {
      return;
    }
    this.selectedTab = tab.id;
  }

  openImportArgsModal(position: 'req' | 'res') {
    const thisNzModal = this.nzModal.create({
      nzContent: pluginContentImportModal,
      nzWidth: '600px',
      nzClosable: true,
    });
    const instance = thisNzModal.getContentComponent();
    instance.importContentType = 'args';
    instance.confirm.subscribe((args: { content: string; type: string }) => {
      try {
        const data: any = JSON.parse(args.content);
        if (position === 'req') {
          if (args.type === 'json') {
            this.JSON2ReqArgs(data, this.selectedTab);
          } else {
            this.JSONSchema2Args(data, this.selectedTab);
          }
        } else {
          if (args.type === 'json') {
            this.JSON2ResArgs(data);
          } else {
            this.JSONSchema2Res(data);
          }
        }
        thisNzModal.close();
      } catch (e) {
        thisNzModal.close();
        MessageComponent.showError(this.i18n.transform('parse_tool_args_err'));
        // 不合法的输入
        return;
      }
    });
  }

  editCodeFun(data) {
    this.editCodeModal = true;
  }

  onSave() {}

  functionGraphDisplayEvent(e) {
    this.editCodeModal = e;
  }
}
