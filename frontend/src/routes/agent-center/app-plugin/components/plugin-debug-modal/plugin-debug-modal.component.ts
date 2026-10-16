import { Component, ViewChild, inject, Input } from '@angular/core';
import { MODULES } from '@shared/modules';
import { filter, take } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { Clipboard } from '@angular/cdk/clipboard';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { isArray, isInteger } from 'lodash';
import { AssetSuccessIconComponent } from '@shared/components/assets/asset-success-icon/asset-success-icon.component';
import { AssetErrorIconComponent } from '@shared/components/assets/asset-error-icon/asset-error-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { AssetGenerateLoadingIconComponent } from '@shared/components/assets/asset-generate-loading-icon/asset-generate-loading-icon.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { AssetAlertIconComponent } from '@shared/components/assets/asset-alert-icon/asset-alert-icon.component';
import { initializeReqItem, pluginSchemaStr2Path } from '@routes/agent-center/app-plugin/utils';
import { EnvManagementService } from '@routes/platform-management/environment-management/env-management.service';
import { EnvironmentVariablesManagementService } from '@routes/platform-management/environment-variables-management/environment-variables-management.service';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzAlertModule } from 'ng-zorro-antd/alert';

/** 加密环境变量的脱敏占位符：回填后通过必填校验，提交后由后端按默认环境解密解析 */
const ENV_VAR_SECRET_MASK = '******';

/** 运行时环境变量占位符前缀：加密变量提交该占位符，由后端按默认环境解密解析 */
const ENV_VAR_PLACEHOLDER_PREFIX = '${_env.plugin_url_params.';

@Component({
  selector: 'plugin-debug-modal',
  templateUrl: './plugin-debug-modal.component.html',
  styleUrls: ['./plugin-debug-modal.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    DynamicNodeParamsComponent,
    JsonViewerComponent,
    AssetSuccessIconComponent,
    AssetErrorIconComponent,
    AssetCopyIconComponent,
    AssetCopySuccessIconComponent,
    AssetLoadingIconComponent,
    AssetGenerateLoadingIconComponent,
    NoDataIconComponent,
    AssetAlertIconComponent,
    NzButtonModule,
    NzIconModule,
    NzToolTipModule,
    NzAlertModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginDebugModalComponent {
  readonly modalRef = inject(NzModalRef);

  @Input() requestArgs = [];

  @Input() hideParseBtn = false;

  @Input() pluginBodyParams;

  @ViewChild('dynamicFormIns')
  dynamicFormIns!: DynamicNodeParamsComponent;

  public requestArgToDynamicForm = [];

  public tabs: string[] = ['Body', 'URL', 'Headers'];

  public activeTab: string = 'Body';

  // 调测接口的结果
  public debugResult = null;

  public rawRequestBody;

  public rawResponse;

  // 记录输入区域的不同标签的复制按钮状态
  public inputCopyState: Record<string, boolean> = {};

  // 记录输出区域的复制按钮状态
  public isOutputCopying = false;

  public isLoading = false;

  public showResponseJson=false;

  /** 绑定的环境变量在当前默认环境中缺失的参数清单（切换默认环境后常见），用于弹窗提示 */
  public envVarMissingList: { paramName: string; varName: string }[] = [];

  /** 当前默认环境名，用于缺失提示 */
  public defaultEnvName = '';

  /** 是否存在默认环境（存在绑定关系但未设置默认环境时为 false，用于提示） */
  public hasDefaultEnv = true;

  /** 调测参数是否已就绪（环境变量回填完成）；未就绪前禁止调测，避免提交空参数或未回填参数 */
  public isParamsReady = false;

  /** 环境变量加载是否失败（接口异常）：用于提示，并保证强转默认值不被误当作手填值提交 */
  public envVarLoadFailed = false;
  constructor(
    private i18n: I18NextEagerPipe,
    private commonLogic: agentCommonLogic,
    private monacoLoader: MonacoEditorLoaderService,
    private appPluginRepoServe: AppPluginRepoService,
    private clipboard: Clipboard,
    private agentDataServe: AgentDataService,
    private envManagementService: EnvManagementService,
    private envVarService: EnvironmentVariablesManagementService,
  ) {}

  ngOnInit() {
    //插件路径参数
    let pluginPathArgs = pluginSchemaStr2Path(this.pluginBodyParams?.request_info?.basic_info?.input_schema)
    pluginPathArgs = pluginPathArgs.map((item) => initializeReqItem(item))
    // requestArgs 为 @Input（与父组件共享引用），这里深拷贝一份再回填环境变量，
    // 避免直接修改 item.value/controlValue 污染父组件状态（影响父组件展示、保存或再次打开弹窗的初始值）
    const requestArgToDynamicForm = [...this.requestArgs, ...pluginPathArgs].map((item) => ({
      ...item,
      value: { ...(item?.value || {}) },
    }));
    // 回填绑定的环境变量值：非加密变量直接填充，加密变量前端拿不到明文，交由后端按默认环境解析
    this.applyBoundEnvVarValues(requestArgToDynamicForm).then((list) => {
      this.requestArgToDynamicForm = list;
      // 参数就绪后才允许调测，避免异步回填完成前提交空参数/未回填参数
      this.isParamsReady = true;
      this.registerJSONValidationSchema();
    });
  }

  /**
   * 回填 requestArgs 中通过 env_var_ref 绑定的环境变量值（取当前默认环境）。
   * 加密变量（secret=true）接口只会返回 ****** 占位符，前端无法拿到明文，回填脱敏占位符由后端解析；
   * 绑定的变量在默认环境中不存在时（如切换默认环境后），记录到 envVarMissingList 用于提示。
   */
  private async applyBoundEnvVarValues(list: any[]): Promise<any[]> {
    if (!list?.some((item) => item?.env_var_ref)) {
      return list;
    }
    this.envVarMissingList = [];
    this.hasDefaultEnv = true;
    this.envVarLoadFailed = false;
    this.defaultEnvName = '';
    try {
      const envRes = await this.envManagementService.getEnvironmentList({
        offset: 0,
        limit: 99,
        isDefault: true,
      });
      const envInfo = envRes?.env_info || [];
      const defaultEnv = envInfo.find((env: any) => env.isDefault) || envInfo[0];
      if (!defaultEnv?.id) {
        this.hasDefaultEnv = false;
        // 无默认环境时全部绑定字段均不可解析：登记后提交时会剔除被动态表单强转的 0/false，
        // 避免其被后端误判为用户手填值而跳过回填与缺失拦截
        this.collectBoundFieldNames(list);
        return list;
      }
      this.defaultEnvName = defaultEnv.name || defaultEnv.id;
      const varRes = await this.envVarService.getEnvVariablesDetail(defaultEnv.id);
      const varMap = new Map<string, { content: string; secret: boolean }>();
      (varRes?.variables || []).forEach((variable: any) => {
        if (variable?.name) {
          varMap.set(variable.name, {
            content: variable?.value?.content ?? '',
            secret: variable?.value?.secret === true,
          });
        }
      });
      list.forEach((item) => {
        if (!item?.env_var_ref) {
          return;
        }
        const matched = varMap.get(item.env_var_ref);
        if (!matched) {
          // 绑定的环境变量在当前默认环境中不存在（常见于切换默认环境后），记录用于提示
          this.envVarMissingList.push({ paramName: item.name, varName: item.env_var_ref });
          return;
        }
        item.envVarBound = true;
        // 加密变量前端拿不到明文，回填脱敏占位符 ******：既能通过必填校验，又由后端按默认环境解密解析；
        // 用户仍可手动覆盖该值（手动输入优先）。
        if (matched.secret || matched.content === ENV_VAR_SECRET_MASK) {
          item.envVarBoundSecret = true;
          item.value = { ...(item.value || {}), default: ENV_VAR_SECRET_MASK };
          item.controlValue = ENV_VAR_SECRET_MASK;
          return;
        }
        if (!matched.content) {
          // 变量存在但内容为空：同样视为不可解析，登记缺失清单，
          // 避免非 string 字段被动态表单强转为 0/false 后当作手填值下发、后端跳过环境变量解析
          this.envVarMissingList.push({ paramName: item.name, varName: item.env_var_ref });
          return;
        }
        item.value = { ...(item.value || {}), default: matched.content };
        item.controlValue = matched.content;
      });
    } catch (e) {
      // 环境变量加载失败：绑定字段视为不可解析（避免强转出的 0/false 被当作手填值静默下发），并给出提示
      this.envVarLoadFailed = true;
      this.collectBoundFieldNames(list);
    }
    return list;
  }

  /** 将全部绑定字段登记为「当前环境不可解析」，供提交时剔除被动态表单强转的默认值 */
  private collectBoundFieldNames(list: any[]): void {
    this.envVarMissingList = [];
    list.forEach((item: any) => {
      if (item?.env_var_ref) {
        this.envVarMissingList.push({ paramName: item.name, varName: item.env_var_ref });
      }
    });
  }

  /** 按钮禁用：rawResponse为空 或者 errorMessage为空 */
  get isDebugBtnDisabled() {
    return (
      (this.debugResult?.success && !this.rawResponse) ||
      (!this.debugResult?.success && !this.debugResult?.errorMessage)
    );
  }

  public async onDebugging() {
    // 安全兜底：参数未就绪（环境变量回填未完成）时直接返回，避免提交空参数或未回填参数
    if (!this.isParamsReady) {
      return;
    }
    this.isLoading = false;
    let dynamicFormPass = true;
    // 检查基础类型入参
    dynamicFormPass = this.dynamicFormIns
      ? this.dynamicFormIns.validatePrimitiveInputs()
      : true;
    // 检查复杂类型入参
    const validationResults = this.dynamicFormIns?.validateJsonSchemas() || [];
    for (const item of validationResults) {
      if (item.type === 'object' || item.type.startsWith('array')) {
        if (item.required) {
          if (item.isError || item.isEmpty) {
            dynamicFormPass = false;
          }
        } else {
          if (item.isError) {
            dynamicFormPass = false;
          }
        }
      }
    }

    if (dynamicFormPass) {
      this.debugResult = null;
      this.isLoading = true;

      try {
        let tool_id = '';
        if (this.pluginBodyParams.tool_id) {
          const res = await this.appPluginRepoServe.modifyDebugPluginId(
            this. pluginBodyParams.plugin_id,
            this.pluginBodyParams.tool_id,
          );
          tool_id = res.data||res.tool_id||this.pluginBodyParams.tool_id;
        } else {
          const req = {...this.pluginBodyParams}
          if(req?.request_info?.basic_info?.input_schema){
            req.request_info.input_schema = req.request_info.basic_info.input_schema
          }
          const res = await this.appPluginRepoServe.getDebugPluginId(
            req
          );
          tool_id = res.tool_id;
        }

        const params = this.getDebugBodyParams() || {};
        const jsonStr = JSON.stringify(params);
        this.debugResult = await this.appPluginRepoServe.debugPluginById(
          tool_id,
          jsonStr
        );
        this.rawRequestBody =
          this.debugResult?.raw_request_body &&
          this.safeJsonParse(this.debugResult.raw_request_body);

        // 超长json格式化会卡死，检测到超长直接以文本展示并提示不能格式化
        if (this.debugResult?.raw_response) {
          if (this.debugResult.raw_response.length>10000){
            this.rawResponse = this.debugResult.raw_response;
          }
          else{
            this.rawResponse =
              this.debugResult?.raw_response &&
              this.safeJsonParse(this.debugResult.raw_response);
            this.showResponseJson=true;
          }
        }
      } finally {
        this.isLoading = false;
      }
    }
  }

  public onParseRes() {
    let resSchema;
    if (this.debugResult?.success) {
      resSchema = this.resStr2Schema(this.debugResult?.raw_response);
    } else {
      resSchema = this.resStr2Schema(this.debugResult?.errorMessage);
    }
    if (resSchema) {
      this.agentDataServe.setPluginDebugRes(JSON.stringify(resSchema));
    } else {
      this.agentDataServe.setPluginDebugRes('');
    }
    this.close();
  }

  public setActiveTab(tab: string): void {
    this.activeTab = tab;
    if (!this.inputCopyState[tab]) {
      this.inputCopyState[tab] = false;
    }
  }

  public copyInput() {
    let text = '';
    switch (this.activeTab) {
      case 'Body':
        text = this.debugResult.raw_request_body;
        break;
      case 'URL':
        text = this.debugResult.raw_request_url;
        break;
      case 'Headers':
        text = JSON.stringify(this.debugResult.raw_request_headers);
        break;
      default:
        return;
    }

    const currentTab = this.activeTab;
    if (this.clipboard.copy(text)) {
      this.inputCopyState[currentTab] = true;
      setTimeout(() => {
        this.inputCopyState[currentTab] = false;
      }, 3000);
    }
  }

  public copyOutput() {
    let text = '';
    if (this.debugResult?.success) {
      text = this.debugResult.raw_response || '';
    } else {
      text = this.debugResult.errorMessage || '';
    }

    if (this.clipboard.copy(text)) {
      this.isOutputCopying = true;
      setTimeout(() => {
        this.isOutputCopying = false;
      }, 3000);
    }
  }

  public isSuccess(code: number) {
    return code >= 200 && code < 300;
  }

  public isValidJson(rawResponse: string) {
    try {
      JSON.parse(rawResponse);
      return true;
    } catch (e) {
      return false;
    }
  }

  private safeJsonParse(s: any) {
    try {
      return JSON.parse(s);
    } catch {
      return s;
    }
  }

  /** 点击【开始调测】，获取表单key-value，作为插件调测接口的入参 */
  private getDebugBodyParams() {
    const params = this.dynamicFormIns?.getDynamicParams() || {};
    // 加密环境变量字段保留 ****** 展示（通过必填校验），提交时替换为运行时占位符，
    // 由后端按默认环境解密解析；用户手填的值原样提交。
    this.requestArgToDynamicForm.forEach((item: any) => {
      if (!item?.env_var_ref) {
        return;
      }
      if (item.envVarBoundSecret && this.isUntouchedSecretField(item, params[item.name])) {
        params[item.name] = `${ENV_VAR_PLACEHOLDER_PREFIX}${item.env_var_ref}}`;
        return;
      }
      // 变量缺失的绑定字段：动态表单会把空默认值强转为 0/false，或保留脱敏显示值 ******；
      // 未手动修改时不提交该字段，让后端按"空值"走缺失拦截（必填报错）/放行（非必填）逻辑
      if (this.isMissingBoundVar(item.name) && this.isUntouchedMissingValue(item, params[item.name])) {
        delete params[item.name];
      }
    });
    return params;
  }

  /** 判断参数绑定的环境变量是否在当前默认环境中缺失 */
  private isMissingBoundVar(paramName: string): boolean {
    return this.envVarMissingList.some((missing) => missing.paramName === paramName);
  }

  /**
   * 判断变量缺失的绑定字段是否仍为「未手动修改」的动态表单默认态。
   * 动态表单会把空默认值强制转换（integer/number → 0，boolean → false），或保留脱敏显示值 ******；
   * 用户未编辑（pristine）时这些值不代表用户输入；用户手输的值（含手输的 ******，控件已 dirty）原样提交。
   */
  private isUntouchedMissingValue(item: any, submitted: any): boolean {
    if (this.dynamicFormIns?.isControlPristine(item?.name) !== true) {
      return false;
    }
    // 脱敏显示掩码：未手动修改时不应作为用户值提交（后端不再把 ****** 当作回填信号）
    if (submitted === ENV_VAR_SECRET_MASK) {
      return true;
    }
    // 插件 schema 显式声明了默认值时，表单提交的就是该默认值（如显式默认 0/false），不应作为"空默认被强转"剔除；
    // 这里用 schema 原始默认值 item.default 判断，避免 value.default 被 parseInt/parseFloat/布尔转换后的产物造成误判
    const rawDefault = item?.default;
    if (rawDefault !== undefined && rawDefault !== null && rawDefault !== '') {
      return false;
    }
    if (item?.type === 'integer' || item?.type === 'number') {
      return typeof submitted === 'number' && (Number.isNaN(submitted) || submitted === 0);
    }
    if (item?.type === 'boolean') {
      return submitted === false;
    }
    return false;
  }

  /**
   * 判断加密绑定字段是否仍为「未手动修改」的默认态。
   * 动态表单会把非 string 类型默认值强制转换（integer/number 的 ****** → 0，boolean → false），
   * 因此除固定掩码外还需识别这些转换后形态，否则掩码会被当成用户输入而无法替换为运行时占位符，
   * 导致 0/false 被当作真实值下发且后端不再回填该加密变量。
   * 类型强转后的 0/false 与用户真实输入无法从值本身区分，须结合表单控件 pristine 状态判定：
   * 仅当控件未被用户编辑过时才视为默认态，用户手输的 0/false 原样提交（手动输入优先）。
   */
  private isUntouchedSecretField(item: any, submitted: any): boolean {
    if (submitted === ENV_VAR_SECRET_MASK) {
      // 掩码需结合 pristine 判定：用户手动输入的 ****** 原样提交（手动输入优先）；
      // 未手动修改时才替换为运行时占位符，交由后端按默认环境解析
      return this.dynamicFormIns?.isControlPristine(item.name) === true;
    }
    if (item?.type === 'integer' || item?.type === 'number') {
      return (
        typeof submitted === 'number' &&
        (Number.isNaN(submitted) || submitted === 0) &&
        this.dynamicFormIns?.isControlPristine(item.name) === true
      );
    }
    if (item?.type === 'boolean') {
      return submitted === false && this.dynamicFormIns?.isControlPristine(item.name) === true;
    }
    return false;
  }

  private registerJSONValidationSchema() {
    this.monacoLoader.isMonacoLoaded$
      .pipe(
        filter((isLoaded) => isLoaded),
        take(1),
      )
      .subscribe(() => {
        // 为每个请求参数添加 modelUri 字段
        this.requestArgToDynamicForm.forEach((input) => {
          input.modelUri = this.commonLogic.getModelUriByType(
            input.type,
            input.name,
          );
          input.isError = false;
          input.isEmpty = false;
        });
        // 收集所有 JSON Schema
        const schemas = this.requestArgToDynamicForm.map((input) => ({
          uri: input.modelUri?.toString(),
          schema: this.commonLogic.getJSONSchemaByType(input.type)?.schema,
          fileMatch: [input.modelUri?.toString()],
        }));
        // 避免覆盖之前设置的 JSON Schema
        monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
          validate: true,
          schemas: schemas,
          schemaValidation: 'error',
        });
      });
  }

  private close() {
    this.modalRef.destroy();
  }

  private resStr2Schema(jsonStr: string) {
    let obj;

    try {
      obj = JSON.parse(jsonStr);
      if (!obj || typeof obj !== 'object') {
        return '';
      }
    } catch {
      return '';
    }
    return this.resObject2Schema(obj);
  }

  /** 将插件调测结果对应的object对象转换成JSON Schema */
  private resObject2Schema(data) {
    const schema: any = {};

    if (isArray(data)) {
      if (data.length === 0) {
        return undefined; // 过滤空数组，无法知道具体属于Array<...>
      }
      schema.type = 'array';
      const elmTypes = [...new Set(data.map((item) => this.getType(item)))];

      if (elmTypes.length === 1) {
        schema.items =
          elmTypes[0] === 'object'
            ? this.resObject2Schema(data[0]) // array<object>类型，递归转换JSON Schema
            : { type: elmTypes[0] }; // 单一类型数组
      } else {
        schema.items = { type: 'mixed' }; // 混合类型数组
      }
    } else if (this.getType(data) === 'object') {
      const properties = {};

      Object.entries(data || {}).forEach(([key, value]) => {
        if (value === null) {
          return; // 过滤null，无法知道null属于某个类型
        }

        const propSchema = this.resObject2Schema(value);
        if (
          propSchema !== null &&
          propSchema !== undefined &&
          Object.keys(propSchema).length > 0
        ) {
          properties[key] = propSchema;
        }
      });

      if (Object.keys(properties).length === 0) {
        return undefined; // 过滤空对象，无法解析出对象属性，可能导致工作流运行失败
      }

      schema.type = 'object';
      schema.properties = properties;
      schema.required = Object.keys(properties);
    } else {
      // 基础类型
      schema.type = this.getType(data);
    }

    return schema;
  }

  /** 获取入参的具体数据类型 */
  private getType(value): string {
    if (isArray(value)) {
      return 'array';
    }

    if (typeof value === 'number') {
      return isInteger(value) ? 'integer' : 'number';
    }

    if (['boolean', 'string', 'object'].includes(typeof value)) {
      return typeof value;
    }

    return 'unknown';
  }
}
