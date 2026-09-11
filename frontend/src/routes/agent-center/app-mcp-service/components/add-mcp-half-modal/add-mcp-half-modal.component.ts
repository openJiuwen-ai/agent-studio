import { ChangeDetectorRef, Component, ElementRef, EventEmitter, Input, OnInit, Output, ViewChild, inject } from '@angular/core';
import { MessageComponent } from '@shared/services/cfdata.service';
import { HelpDocKey } from '@constants/support-topic.const';
import { I18nNamespace } from '@i18n';
import * as mcpInterfaces from '@interfaces/mcp/mcp.interfaces';
import { McpInterfaces } from '@interfaces/mcp/mcp.interfaces';
import { PromptType, VariableType, IVariable } from '@interfaces/prompt/prompt-optimize-task.interface';
import { MonacoEditorConstructionOptions, MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { ParamEditorComponent } from '@routes/agent-center/app-plugin/components/param-editor/param-editor.component';
import { MCPService } from '@services/agent-center/mcp.service';
import { CommonService } from '@services/common.service';
import { PromptService } from '@services/prompt.service';
import { EnvManagementService } from '@routes/platform-management/environment-management/env-management.service';
import { EnvironmentVariablesManagementService } from '@routes/platform-management/environment-variables-management/environment-variables-management.service';
import { MCP_DEFAULT_ICON_BASE64_STR } from '@shared/config/default-icons-base64';
import { MODULES } from '@shared/modules';
import { HelpLinksService } from '@shared/services/help-links.service';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { mockMcpList } from '../../../../../mock/mcp';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { CommonUtils } from '../../../../../utils/common.util';
import { NzDrawerModule, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalRef } from 'ng-zorro-antd/modal';
enum mapKeys {
  category = 'category',
  offset = 'offset',
  limit = 'limit',
}

@Component({
  selector: 'add-mcp-half-modal-component',
  templateUrl: './add-mcp-half-modal.component.html',
  styleUrls: ['./add-mcp-half-modal.component.scss'],
  standalone: true,
  imports: [MODULES, MonacoEditorModule, NzEmptyModule, NzDrawerModule, ParamEditorComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.MODEL_ACCESS, I18nNamespace.AGENT, I18nNamespace.KMS],
    },
  ],
})
export class AddMcpHalfModalComponent implements OnInit {
  @Input('type') type: string = 'server'; // 用于标识当前弹框是从平台还是从用户界面来创建MCP
  @Input('action') action: string = 'create'; // 用于表示当前是编辑还是创建
  @Input('selectMcpData') selectMcpData: mcpInterfaces.McpInterfaces = null;
  @Input('teamplateType') teamplateType = 'blank-creation'; // 默认为空白模板创建
  @Input('title') title = ''; // 默认为空白模板创建
  @ViewChild('previewIcon') previewIcon: ElementRef;
  @ViewChild('iconInput') iconInput: ElementRef<HTMLInputElement> | null = null;
  @Output('mcpModalSelectedData') mcpModalSelectedData = new EventEmitter<McpInterfaces>();
  readonly modalRef = inject(NzModalRef);
  steps: Array<any> = [
    {
      label: this.i18n.transform('selectMcpService'),
      id: 'selectMcpService',
    },
    {
      label: this.i18n.transform('selectMcpConfig'),
      id: 'selectMcpConfig',
    },
  ];
  activeMcpStep: number = 0;
  selectedTabIndex: number = 0;
  public searchMcpModalName: string = '';
  public mcpModalCurrentPage: number = 1;
  public lang: string = '';
  public cardPageSize: any = {
    options: [12, 24, 48, 64],
    size: 12,
  };
  mcpModalLoading = true;
  public isFgAuth = false;
  public isCreating = false;
  public mcpModalList: mcpInterfaces.McpInterfaces[] = [];
  public mcpModalSelected: mcpInterfaces.McpInterfaces = {} as mcpInterfaces.McpInterfaces; //这里需要初始化为空对象，否则开始时html中会报错
  public mcpModalTotalNum: number = 0;
  protected readonly mockMcpList = mockMcpList;
  public emptyTemplateId: string = '1';
  public mcpModalDataType: string = 'form';
  public mcpModalData = {
    param: {
      value: '',
      isVisible: false,
    },
    environments: [],
    headers: [],
    editor: JSON.stringify({}, null, 2),
  };
  /** 默认环境的环境变量列表，供 URL 引用选择 */
  public envVarList: { name: string; type: string }[] = [];
  /** meta-param-editor 变量插入器状态 */
  public isShowInserter: boolean = false;
  public variables: Array<IVariable> = [];
  public initVariables: Array<IVariable> = [];
  /** 从 URL 中提取的 {varName} 参数列表，每项含 env_var_ref 绑定 */
  public mcpUrlParams: Array<{ name: string; env_var_ref: string }> = [];
  protected readonly PromptType = PromptType;
  public editorOptions: MonacoEditorConstructionOptions = {
    theme: 'vs-dark',
    language: 'json',
    lineNumbers: 'off',
    readOnly: false,
    minimap: {
      enabled: false,
    },
  };
  public mcpModalConfig = {
    NPX: {
      mcpServers: {
        'example-npx': {
          command: 'npx',
          args: ['-y', '@example'],
        },
      },
    },
    SSE: {
      mcpServers: {
        'example-sse': {
          url: '',
        },
      },
    },
    UVX: {
      mcpServers: {
        'example-uvx': {
          command: 'uvx',
          args: ['example-args'],
        },
      },
    },
    // 添加 STREAMABLE_HTTP 配置
    STREAMABLE_HTTP: {
      mcpServers: {
        'example-streamable-http': {
          url: '',
        },
      },
    },
  };
  protected readonly MCP_DEFAULT_ICON_BASE64_STR = MCP_DEFAULT_ICON_BASE64_STR;
  public iconAccept = '.png,.jpeg,.gif,.jpg';
  public isHcs: boolean = false;
  public isSite: boolean = true;
  public isInitLoading: boolean = true; // 由于搜索框会自动搜索数据，所以防止初始化的时候，搜索框会自动搜索一次
  public isCollapseMcpConfig: boolean = false;
  public fgGrantPermissionTip = '';
  public isDisabledConfirmBtn: boolean = false;

  appMcpTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform('all'),
      name_en: 'all',
      id: 'all',
      active: true,
      description: '',
      library_type: '',
      created_on: 0,
      updated_on: 0,
    },
  ];
  selectedTagId: string = '';
  authConfigType = [
    {
      id: '1',
      label: this.i18n.transform('mcp_no_auth'),
      value: '',
    },
    {
      id: '2',
      label: this.i18n.transform('mcp_api_auth'),
      value: 'SERVICE',
    },
    {
      id: '3',
      label: this.i18n.transform('mcp_oauth_auth'),
      value: 'OAUTH',
    },
  ];
  authSecretPosition = [
    {
      id: '1',
      label: 'Header',
      value: 'HEADERS',
    },
    {
      id: '2',
      label: 'Query',
      value: 'QUERY',
    },
  ];
  mcpAuthConfigData = {
    selectedAuthType: '',
    selectedAuthPos: 'HEADERS',
    authHeaderParams: [],
    authQueryParams: [],
    authParams: {
      url: '',
      id: '',
      secret: '',
      scope: '',
    },
  };

  oauthErrors = {
    url: false,
    id: false,
    secret: false,
    scope: false,
  };

  oauthURLErrors = '';

  validateOauthField(field: string) {
    this.oauthErrors[field] = !this.mcpAuthConfigData.authParams[field]?.trim();
  }

  constructor(
    private readonly api: MCPService,
    private readonly i18n: angularI18next.I18NextEagerPipe,
    public commonService: CommonService,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService,
    public promptService: PromptService,
    public helpLinksService: HelpLinksService,
    private envManagementService: EnvManagementService,
    private envVarService: EnvironmentVariablesManagementService,
  ) {
    this.lang = CommonUtils.getLanguage();
    this.isHcs = false;
    this.isSite = true;
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  public ngOnInit() {
    this.loadEnvVarList();
    if (!this.title) {
      this.title = this.action === 'create' ? this.i18n.transform('createMcp') : this.i18n.transform('editMcp');
    }
    if (this.selectMcpData) {
      this.activeMcpStep = 1;
      this.mcpModalLoading = true;
      if (this.type === 'server') {
        this.getServerDetail();
      } else {
        this.getServiceDetail();
      }
      return;
    }
    if (this.teamplateType === 'blank-creation') {
      this.mcpModalSelected = JSON.parse(JSON.stringify(this.mockMcpList[0]));
      this.setMcpModalData();
    }
    if (this.teamplateType === 'official-creation') {
      this.getMcpTagData();
      this.getMCPServerList();
    }
    this.initFgGrantPermissionTip();
  }

  initFgGrantPermissionTip() {
    this.fgGrantPermissionTip = this.helpLinksService.processHelpLinkTipWithI18n(this.i18n, 'add_mcp_half_modal_4', HelpDocKey.FG_GRANT_PERMISSION);
  }
  /**
   * 查询MCP_SERVER的详情
   * **/
  private getServerDetail() {
    this.api
      .getServerDetail(this.selectMcpData.id)
      .then(res => {
        this.mcpModalSelected = res;
        this.mcpModalSelected.icon = this.mcpModalSelected.icon || MCP_DEFAULT_ICON_BASE64_STR;
        this.setMcpModalData();
      })
      .finally(() => {
        this.mcpModalLoading = false;
      });
  }

  /**
   * 查询MCP_SERVICE的详情
   * **/
  private getServiceDetail() {
    this.api
      .getServiceDetail(this.selectMcpData.id)
      .then(res => {
        this.mcpModalSelected = res;
        this.mcpModalSelected.icon = this.mcpModalSelected.icon || MCP_DEFAULT_ICON_BASE64_STR;
        this.setMcpModalData();
        this.setMcpAuthConfigData();
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.mcpModalLoading = false;
      });
  }

  private setMcpAuthConfigData() {
    if (!this.mcpModalSelected.auth_info || Object.keys(this.mcpModalSelected.auth_info).length <= 0) {
      this.mcpAuthConfigData.selectedAuthType = '';
      return;
    }
    if (this.mcpModalSelected.auth_info.scope === 'OAUTH') {
      this.mcpAuthConfigData.selectedAuthType = 'OAUTH';
      this.mcpAuthConfigData.authParams.url = this.mcpModalSelected.auth_info.custom_oauth.endpoint_url;
      this.mcpAuthConfigData.authParams.id = this.mcpModalSelected.auth_info.custom_oauth.client_id;
      this.mcpAuthConfigData.authParams.secret = this.mcpModalSelected.auth_info.custom_oauth.client_secret;
      this.mcpAuthConfigData.authParams.scope = this.mcpModalSelected.auth_info.custom_oauth.scope;
      return;
    }
    if (this.mcpModalSelected.auth_info.scope === 'SERVICE') {
      this.mcpAuthConfigData.selectedAuthType = 'SERVICE';
      if (this.mcpModalSelected.auth_info.domain === 'HEADERS') {
        this.mcpAuthConfigData.selectedAuthPos = 'HEADERS';
        this.mcpAuthConfigData.authHeaderParams.length = 0;
        for (let index = 0; index < this.mcpModalSelected.auth_info.auth_keys.length; index++) {
          this.mcpAuthConfigData.authHeaderParams.push({
            name: this.mcpModalSelected.auth_info.auth_keys[index].target_name,
            value: this.mcpModalSelected.auth_info.auth_keys[index].auth_key,
          });
        }
        return;
      }
      if (this.mcpModalSelected.auth_info.domain === 'QUERY') {
        this.mcpAuthConfigData.selectedAuthPos = 'QUERY';
        this.mcpAuthConfigData.authQueryParams.length = 0;
        for (let index = 0; index < this.mcpModalSelected.auth_info.auth_keys.length; index++) {
          this.mcpAuthConfigData.authQueryParams.push({
            name: this.mcpModalSelected.auth_info.auth_keys[index].target_name,
            value: this.mcpModalSelected.auth_info.auth_keys[index].auth_key,
          });
        }
        return;
      }
      return;
    }
    return;
  }

  /**
   * 查询server
   * **/
  public onSearchInnerMcp() {
    if (this.searchMcpModalName === '' && this.isInitLoading) {
      return;
    }
    this.mcpModalCurrentPage = 1;
    this.getMCPServerList();
  }

  public clearSearchBoxKeyword() {
    this.searchMcpModalName = '';
  }

  /*
   * 设置卡片的查询参数
   */
  private getServerListParams() {
    if (this.mcpModalCurrentPage === 1) {
      if (this.searchMcpModalName === '') {
        return this.cardPageSize.size - 1;
      } else {
        return this.cardPageSize.size;
      }
    }
    return this.cardPageSize.size;
  }

  /** 刷新数据 **/
  public refreshData() {
    this.searchMcpModalName = '';
    this.delayInitLoading();
    this.mcpModalCurrentPage = 1;
    this.getMCPServerList();
  }

  /** 延迟更新状态 **/
  private delayInitLoading() {
    this.isInitLoading = true;
    setTimeout(() => {
      this.isInitLoading = false;
    }, 1500);
  }
  /*
   * 获取Server的list数据（平台预置）
   */
  public getMCPServerList() {
    const query = {
      language: 'ZH',
      name: '',
    };
    if (this.selectedTagId) {
      query[mapKeys.category] = this.selectedTagId;
    }
    if (this.searchMcpModalName !== '') {
      query.language = this.isZH() ? 'ZH' : 'EN';
      query.name = this.searchMcpModalName;
    }
    const size = this.cardPageSize.size;
    const params = {
      offset: (this.mcpModalCurrentPage - 1) * size,
      limit: size,
    };
    this.mcpModalLoading = true;
    this.mcpModalList.length = 0;
    this.mcpModalSelected = null;
    query[mapKeys.offset] = params.offset;
    query[mapKeys.limit] = params.limit;
    this.api
      .getServerList(query)
      .then(res => {
        this.mcpModalList = res.mcps || [];
        this.mcpModalTotalNum = res.total;
        if (this.mcpModalList.length <= 0) {
          return;
        }
        if (this.searchMcpModalName !== '') {
          this.mcpModalSelected = this.mcpModalList[0];
          this.mcpModalSelected.isSelected = true;
          return;
        }
        this.mcpModalSelected = this.mcpModalList[0];
        this.mcpModalSelected.isSelected = true;
      })
      .finally(() => {
        this.mcpModalLoading = false;
        this.delayInitLoading();
      });
  }

  /*
   * 查询卡片的详情信息
   * */
  private getMCPServerDetail() {
    if (this.mcpModalSelected.id === this.emptyTemplateId) {
      this.mcpModalSelected = JSON.parse(JSON.stringify(this.mcpModalSelected));
      this.setMcpModalData();
      return;
    }
    this.api
      .getServerDetail(this.mcpModalSelected.id)
      .then(res => {
        this.mcpModalSelected = res || {};
        this.setMcpModalData();
      })
      .finally(() => {});
  }

  /*
    设置卡片的配置信息
   */
  private setMcpModalData() {
    this.mcpModalData.headers.length = 0;
    this.mcpModalData.environments.length = 0;
    this.mcpModalData.param.value = '';
    this.mcpModalData.param.isVisible = true;
    this.mcpUrlParams = [];
    this.variables = [];
    this.initVariables = [];
    if (this.mcpModalSelected.id === this.emptyTemplateId) {
      // 此时用户选择的是空白模板
      if (this.mcpModalSelected.org_type === 'NPX') {
        this.mcpModalData.param.value = '-y,@example';
        this.mcpModalData.param.isVisible = true;
        this.mcpModalData.editor = JSON.stringify(this.mcpModalConfig.NPX, null, 2);
      } else if (this.mcpModalSelected.org_type === 'UVX') {
        this.mcpModalData.param.value = 'example-args';
        this.mcpModalData.editor = JSON.stringify(this.mcpModalConfig.UVX, null, 2);
      } else if (this.mcpModalSelected.org_type === 'STREAMABLE_HTTP') {
        // 添加 STREAMABLE_HTTP 处理
        this.mcpModalData.param.value = this.mcpModalConfig.STREAMABLE_HTTP.mcpServers['example-streamable-http'].url;
        this.mcpModalData.param.isVisible = true;
        this.mcpModalData.editor = JSON.stringify(this.mcpModalConfig.STREAMABLE_HTTP, null, 2);
      } else {
        this.mcpModalData.param.value = this.mcpModalConfig.SSE.mcpServers['example-sse'].url;
        this.mcpModalData.param.isVisible = true;
        this.mcpModalData.editor = JSON.stringify(this.mcpModalConfig.SSE, null, 2);
      }
      return;
    }
    // 此时是非空白模板
    this.setMcpModalDataWithNotEmptyTemplate();
    // 设置鉴权信息
  }

  private setMcpModalDataWithNotEmptyTemplate() {
    try {
      const serverConfig = JSON.parse(this.mcpModalSelected.server_config);
      if (typeof serverConfig !== 'object') {
        return;
      }
      if (Array.isArray(serverConfig)) {
        return;
      }
      const serverConfigKeys = Object.keys(serverConfig);
      if (typeof serverConfig[serverConfigKeys[0]] !== 'object' || Array.isArray(serverConfig[serverConfigKeys[0]])) {
        return;
      }
      const innerObj = serverConfig[serverConfigKeys[0]];
      const innerObjKeys = Object.keys(innerObj);
      if (innerObjKeys.length <= 0) {
        return;
      }
      this.processMcpModelDataWithNotEmptyTemplate(innerObj, innerObjKeys);
    } catch (e) {
      console.error('setMcpModalDataWithNotEmptyTemplate error:', e);
    }
  }

  private processMcpModelDataWithNotEmptyTemplate(innerObj: object, innerObjKeys: string[]) {
    this.mcpModalData.editor = this.mcpModalSelected.server_config;
    if (this.mcpModalSelected.org_type === 'NPX' || this.mcpModalSelected.org_type === 'UVX') {
      this.mcpModalData.param.value = Array.isArray(innerObj[innerObjKeys[0]].args) ? innerObj[innerObjKeys[0]].args.join(',') : '';
      if (innerObj[innerObjKeys[0]].headers) {
        Object.keys(innerObj[innerObjKeys[0]].headers).forEach(key => {
          this.mcpModalData.headers.push({
            key: key,
            value: innerObj[innerObjKeys[0]].headers[key],
            isVisible: false,
          });
        });
      }
      if (innerObj[innerObjKeys[0]].env) {
        Object.keys(innerObj[innerObjKeys[0]].env).forEach(key => {
          this.mcpModalData.environments.push({
            key: key,
            value: innerObj[innerObjKeys[0]].env[key],
            isVisible: false,
          });
        });
      }
      return;
    }
    // 添加 STREAMABLE_HTTP 类型
    if (this.mcpModalSelected.org_type === 'SSE' || this.mcpModalSelected.org_type === 'STREAMABLE_HTTP') {
      const innerObjKeys = Object.keys(innerObj);
      const savedUrl = innerObj[innerObjKeys[0]]?.url;
      if (savedUrl) {
        this.mcpModalData.param.value = this.initUrlFromSaved(savedUrl);
      }
      if (innerObj[innerObjKeys[0]].headers) {
        Object.keys(innerObj[innerObjKeys[0]].headers).forEach(key => {
          this.mcpModalData.headers.push({
            key: key,
            value: innerObj[innerObjKeys[0]].headers[key],
            isVisible: false,
          });
        });
      }
    }
  }

  /*
   * 点击弹框中的卡片
   */
  public handleClickMcpModalCard(data: mcpInterfaces.McpInterfaces) {
    data.isSelected = true;
    for (let index = 0; index < this.mcpModalList.length; index++) {
      if (data.id !== this.mcpModalList[index].id) {
        this.mcpModalList[index].isSelected = false;
      }
    }
    this.mcpModalSelected = data;
  }

  /*
   * 国际化语言环境
   */
  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  /** 加载默认环境的环境变量列表，供 URL 引用选择 */
  private loadEnvVarList(): void {
    this.envManagementService.getEnvironmentList({ offset: 0, limit: 99 }).then(res => {
      const defaultEnv = (res?.env_info || []).find((e: any) => e.isDefault);
      if (!defaultEnv?.id) {
        this.envVarList = [];
        return;
      }
      this.envVarService.getEnvVariablesDetail(defaultEnv.id).then(varRes => {
        this.envVarList = (varRes?.variables || [])
          .filter(v => v.name)
          .map(v => ({ name: v.name, type: v.value?.type || 'string' }));
        this.cdr.detectChanges();
      }).catch(() => { this.envVarList = []; });
    }).catch(() => { this.envVarList = []; });
  }

  /** 切换变量插入器显示 */
  public showInserter(): void {
    this.isShowInserter = !this.isShowInserter;
  }

  /** 隐藏变量插入器 */
  public hideInserter(): void {
    this.isShowInserter = false;
  }

  /** meta-param-editor 变量变更回调 */
  public updateVariables(variables: IVariable[]): void {
    this.variables = variables;
    this.cdr.detectChanges();
    this.onMcpUrlChange();
  }

  /** 从 URL 中提取 {varName} 参数，构建 mcpUrlParams（保留已有 env_var_ref 绑定） */
  public onMcpUrlChange(): void {
    const url = this.mcpModalData.param.value || '';
    const matches = url.match(/{[a-zA-Z0-9_$-]+}/g) ?? [];
    const names = matches.map(m => m.replace(/{|}/g, ''));
    const newParams: Array<{ name: string; env_var_ref: string }> = [];
    for (const name of names) {
      const existing = this.mcpUrlParams.find(p => p.name === name);
      newParams.push({
        name,
        env_var_ref: existing?.env_var_ref || '',
      });
    }
    this.mcpUrlParams = newParams;
    this.updateConfirmBtnState();
  }

  /** 环境变量未选全时禁用确认按钮 */
  public updateConfirmBtnState(): void {
    if (this.mcpUrlParams.length > 0) {
      this.isDisabledConfirmBtn = this.mcpUrlParams.some(p => !p.env_var_ref);
    } else {
      this.isDisabledConfirmBtn = false;
    }
  }

  /** 保存时将 URL 中的 {varName} 转换为 ${_env.plugin_url_params.envVarRef} */
  private convertUrlForSave(url: string): string {
    if (!url || !this.mcpUrlParams.length) {
      return url;
    }
    let result = url;
    for (const param of this.mcpUrlParams) {
      if (param.env_var_ref) {
        const escapedName = param.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        result = result.replace(
          new RegExp(`\\{${escapedName}\\}`, 'g'),
          `\${_env.plugin_url_params.${param.env_var_ref}}`,
        );
      }
    }
    return result;
  }

  /** 加载时将 URL 中的 ${_env.plugin_url_params.VAR} 转换回 {VAR} 并重建 mcpUrlParams */
  private initUrlFromSaved(url: string): string {
    if (!url) {
      return url;
    }
    const displayUrl = url.replace(
      /\$\{_env\.plugin_url_params\.([^}]+)\}/g,
      '{$1}',
    );
    // 重建 mcpUrlParams
    const matches = displayUrl.match(/{[a-zA-Z0-9_$-]+}/g) ?? [];
    const names = matches.map(m => m.replace(/{|}/g, ''));
    this.mcpUrlParams = names.map(name => ({
      name,
      env_var_ref: name,
    }));
    // 重建 variables 供 meta-param-editor 使用
    this.variables = names.map(name => ({ type: VariableType.TEXT, value: name }));
    this.initVariables = [...this.variables];
    this.updateConfirmBtnState();
    return displayUrl;
  }

  /**
   * 点击上一步
   * **/
  handleClickMcpModalPreviousStep() {
    this.activeMcpStep--;
    this.delayInitLoading();
  }

  /*
   * 点击下一步按钮
   * */
  handleClickMcpModalNextStep() {
    this.activeMcpStep++;
    this.getMCPServerDetail();
  }

  /**
   * 创建MCP
   * **/
  handleClickMcpModalConfirm() {
    if (this.mcpModalSelected.name === '' || this.mcpModalSelected.description === '') {
      MessageComponent.showError(this.i18n.transform('MCPValidateError'));
      return;
    }
    if (this.mcpAuthConfigData.selectedAuthType === 'OAUTH') {
      this.changeOauthUrlError();
      this.oauthErrors.url = !this.mcpAuthConfigData.authParams.url?.trim();
      this.oauthErrors.id = !this.mcpAuthConfigData.authParams.id?.trim();
      this.oauthErrors.secret = !this.mcpAuthConfigData.authParams.secret?.trim();
      this.oauthErrors.scope = !this.mcpAuthConfigData.authParams.scope?.trim();
      if (this.oauthErrors.url || this.oauthErrors.id || this.oauthErrors.secret || this.oauthErrors.scope) {
        this.cdr.detectChanges();
        return;
      }
      if (this.oauthURLErrors) {
        this.cdr.detectChanges();
        return;
      }
    }
    try {
      JSON.parse(this.mcpModalData.editor);
    } catch (e) {
      MessageComponent.showError(this.i18n.transform('MCPJSONData'));
      return;
    }
    const data = {
      description: this.mcpModalSelected.description,
      description_en: this.mcpModalSelected.description_en,
      icon: this.mcpModalSelected.icon,
      name: this.mcpModalSelected.name,
      name_en: this.mcpModalSelected.name_en,
      org_type: this.mcpModalSelected.org_type,
      server_config: '',
      readme: this.mcpModalSelected.readme,
    };
    if (!data.icon.startsWith('data:image/')) {
      if (!/^data:image\/(?:png|jpeg|jpg|svg\+xml);base64,[A-Za-z0-9+/=\r\n]+$/.test('data:image/png;base64,' + data.icon)) {
        MessageComponent.showError(this.i18n.transform('addmcpcomponent_676'));
        return;
      }
    } else {
      if (!/^data:image\/(?:png|jpeg|jpg|svg\+xml);base64,[A-Za-z0-9+/=\r\n]+$/.test(data.icon)) {
        MessageComponent.showError(this.i18n.transform('addmcpcomponent_676'));
        return;
      }
    }
    if (this.mcpModalDataType === 'form') {
      this.handleClickChangeMode('json', false);
    }
    data.server_config = this.mcpModalData.editor;

    this.isCreating = true; //禁用创建按钮
    if (this.action === 'create') {
      try {
        this.setAuthConfig(data);
      } catch (e) {
        MessageComponent.showError(this.i18n.transform('MCPSubmitFail'));
        this.isCreating = false;
        this.cdr.detectChanges();
      }
      this.api
        .deployMcpServer(this.mcpModalSelected.id, data)
        .then(() => {
          MessageComponent.showSuccess(this.i18n.transform('MCPSubmitSuccessContent'));
          this.mcpModalSelectedData.emit(this.mcpModalSelected);
          this.modalRef.destroy();
          this.close();
        })
        .catch(() => {})
        .finally(() => {
          this.isCreating = false;
          this.cdr.detectChanges();
        });
    } else if (this.action === 'edit') {
      const _id = 'id';
      data[_id] = this.mcpModalSelected.id;
      try {
        this.setAuthConfig(data);
      } catch (e) {
        MessageComponent.showError(this.i18n.transform('MCPSubmitFail'));
        this.isCreating = false;
        this.cdr.detectChanges();
      }
      this.api
        .modifyMcpService(data)
        .then(() => {
          MessageComponent.showSuccess(this.i18n.transform('MCPUpdateSuccess'), 8000);
          this.mcpModalSelectedData.emit(this.mcpModalSelected);
          this.modalRef.destroy();
          this.close();
        })
        .catch(() => {})
        .finally(() => {
          this.isCreating = false;
          this.cdr.detectChanges();
        });
    }
  }

  /** 设置鉴权信息 **/
  private setAuthConfig(mcpData: any) {
    if (this.mcpModalSelected.org_type === 'SSE' || this.mcpModalSelected.org_type === 'STREAMABLE_HTTP') {
      if (!this.mcpAuthConfigData.selectedAuthType) {
        mcpData.auth_info = {};
        return;
      }
      if (this.mcpAuthConfigData.selectedAuthType === 'SERVICE') {
        mcpData.auth_info = {
          scope: 'SERVICE',
          domain: 'HEADERS',
          auth_keys: [],
        };
        if (this.mcpAuthConfigData.selectedAuthPos === 'HEADERS') {
          for (let index = 0; index < this.mcpAuthConfigData.authHeaderParams.length; index++) {
            mcpData.auth_info.auth_keys.push({
              auth_key: this.mcpAuthConfigData.authHeaderParams[index].value,
              target_name: this.mcpAuthConfigData.authHeaderParams[index].name,
            });
          }
        } else {
          mcpData.auth_info.domain = 'QUERY';
          for (let index = 0; index < this.mcpAuthConfigData.authQueryParams.length; index++) {
            mcpData.auth_info.auth_keys.push({
              auth_key: this.mcpAuthConfigData.authQueryParams[index].value,
              target_name: this.mcpAuthConfigData.authQueryParams[index].name,
            });
          }
        }
        return;
      }
      if (this.mcpAuthConfigData.selectedAuthType === 'OAUTH') {
        mcpData.auth_info = {
          scope: 'OAUTH',
          custom_oauth: {
            endpoint_url: this.mcpAuthConfigData.authParams.url,
            client_id: this.mcpAuthConfigData.authParams.id,
            client_secret: this.mcpAuthConfigData.authParams.secret,
            scope: this.mcpAuthConfigData.authParams.scope,
          },
        };
        return;
      }
    }
    return;
  }

  /*
   * 切换数据模式 NPX <-> SSE <-> UVX <-> STREAMABLE_HTTP
   * */
  handleClickChangeOrgType(value: string) {
    if (value === 'NPX' || value === 'UVX') {
      this.isDisabledConfirmBtn = false;
    }
    if (this.mcpModalSelected.id !== this.emptyTemplateId) {
      return;
    }
    if (value === 'SSE' || value === 'STREAMABLE_HTTP') {
      this.handleChangeAPIKeyRadio();
    }
    this.mcpModalSelected.org_type = value;
    if (this.mcpModalSelected.id === this.emptyTemplateId) {
      this.setMcpModalData();
    }
  }

  getMouseStatus(type: string) {
    if (this.mcpModalSelected.id !== this.emptyTemplateId) {
      return this.mcpModalSelected.org_type !== type ? 'not-allowed' : '';
    } else {
      return '';
    }
  }

  /**
   * 跳转获取凭证获取
   * **/
  openUrl(url: string) {
    const win = window.open(url, '_blank');
    if (win && win.opener) {
      win.opener = null;
    }
  }

  /**
   * 关闭弹框
   * **/
  dismiss() {
    this.modalRef.destroy();
  }

  close() {
    this.modalRef.destroy();
  }

  public notChangeMode() {
    return this.action === 'edit' && (this.mcpModalSelected.org_type === 'NPX' || this.mcpModalSelected.org_type === 'UVX');
  }

  /**
   * 修改数据模式: form <-> JSON
   * **/
  public handleClickChangeMode(value: string, isNeedSwitch = true) {
    try {
      if (this.notChangeMode()) {
        return;
      }
      const data = JSON.parse(this.mcpModalData.editor);
      if (typeof data !== 'object' || Array.isArray(data)) {
        this.mcpModalDataType = value;
        return;
      }
      const dataKeys = Object.keys(data);
      if (dataKeys.length <= 0) {
        this.mcpModalDataType = value;
        return;
      }
      const firstKeyValue = data[dataKeys[0]];
      const keys = Object.keys(firstKeyValue);
      if (keys.length <= 0) {
        this.mcpModalDataType = value;
        return;
      }
      if (value === 'form') {
        this.processChangeModeWithForm(firstKeyValue, keys, value, isNeedSwitch);
        return;
      }
      this.processChangeModeWithJSON(firstKeyValue, keys, value, data, isNeedSwitch);
    } catch (e) {
      // do something
    }
  }

  // 处理form表单
  private processChangeModeWithForm(firstKeyValue: object, keys: string[], value: any, isNeedSwitch = true) {
    if (firstKeyValue[keys[0]].headers && typeof firstKeyValue[keys[0]].headers === 'object') {
      this.mcpModalData.headers.length = 0;
      const headersData = firstKeyValue[keys[0]].headers;
      Object.keys(headersData).forEach(key => {
        this.mcpModalData.headers.push({
          key: key,
          value: headersData[key],
          isVisible: false,
        });
      });
    }
    if (this.mcpModalSelected.org_type === 'SSE' || this.mcpModalSelected.org_type === 'STREAMABLE_HTTP') {
      this.mcpModalData.param.value = this.initUrlFromSaved(firstKeyValue[keys[0]].url);
      this.mcpModalData.param.isVisible = true;
      if (isNeedSwitch) {
        this.mcpModalDataType = value;
      }
      return;
    }
    if (this.mcpModalSelected.org_type === 'UVX' || this.mcpModalSelected.org_type === 'NPX') {
      if (firstKeyValue[keys[0]].args && Array.isArray(firstKeyValue[keys[0]].args)) {
        this.mcpModalData.param.value = firstKeyValue[keys[0]].args.join(',');
      }
      if (firstKeyValue[keys[0]].env && typeof firstKeyValue[keys[0]].env === 'object') {
        this.mcpModalData.environments.length = 0;
        const envData = firstKeyValue[keys[0]].env;
        Object.keys(envData).forEach(key => {
          this.mcpModalData.environments.push({
            key: key,
            value: envData[key],
            isVisible: false,
          });
        });
      }
      if (isNeedSwitch) {
        this.mcpModalDataType = value;
      }
      return;
    }
  }

  // 处理JSON数据
  private processChangeModeWithJSON(firstKeyValue: object, keys: string[], value: any, data: object, isNeedSwitch = true) {
    delete firstKeyValue[keys[0]].headers;
    delete firstKeyValue[keys[0]].env;
    if (this.mcpModalData.headers.length > 0) {
      firstKeyValue[keys[0]].headers = {};
      for (let index = 0; index < this.mcpModalData.headers.length; index++) {
        firstKeyValue[keys[0]].headers[this.mcpModalData.headers[index].key] = this.mcpModalData.headers[index].value;
      }
    }
    if (this.mcpModalSelected.org_type === 'SSE' || this.mcpModalSelected.org_type === 'STREAMABLE_HTTP') {
      firstKeyValue[keys[0]].url = this.convertUrlForSave(this.mcpModalData.param.value);
      this.mcpModalData.editor = JSON.stringify(data, null, 2);
      if (isNeedSwitch) {
        this.mcpModalDataType = value;
      }
      return;
    }
    if (this.mcpModalSelected.org_type === 'UVX' || this.mcpModalSelected.org_type === 'NPX') {
      firstKeyValue[keys[0]].args = this.mcpModalData.param.value.split(',').filter(Boolean);
      if (this.mcpModalData.environments.length > 0) {
        firstKeyValue[keys[0]].env = {};
        for (let index = 0; index < this.mcpModalData.environments.length; index++) {
          firstKeyValue[keys[0]].env[this.mcpModalData.environments[index].key] = this.mcpModalData.environments[index].value;
        }
      }
      this.mcpModalData.editor = JSON.stringify(data, null, 2);
      if (isNeedSwitch) {
        this.mcpModalDataType = value;
      }
      return;
    }
  }

  /**
   * 删除环境数据
   * **/
  handleClickDeleteEnvironmentData(index: number) {
    this.mcpModalData.environments.splice(index, 1);
  }

  /**
   * 添加环境数据
   * **/
  handleClickAddEnvironmentData() {
    this.mcpModalData.environments.push({
      key: '',
      value: '',
      isVisible: false,
    });
  }

  /**
   * 删除请求头数据
   * **/
  handleClickDeleteRequestData(index: number) {
    this.mcpModalData.headers.splice(index, 1);
  }

  /**
   * 添加请求头数据
   * **/
  handleClickAddRequestData() {
    this.mcpModalData.headers.push({
      key: '',
      value: '',
      isVisible: false,
    });
  }

  handleClickUploadFile(event: any) {
    const file = event.target.files[0];
    if (!file) {
      return;
    }
    const allowedTypes = ['image/png', 'image/svg+xml', 'image/jpeg', 'image/jpg'];
    if (!allowedTypes.includes(file.type)) {
      MessageComponent.showError(this.i18n.transform('ImageError'));
      return;
    }
    const maxSize = 1024 * 1024;
    if (file.size > maxSize) {
      MessageComponent.showError(this.i18n.transform('ImageSizeError'));
      return;
    }
    // 创建FileReader对象
    const reader = new FileReader();
    reader.addEventListener('load', event => {
      const base64String = event.target.result;
      if (file.type.startsWith('image/')) {
        if (typeof base64String === 'string') {
          this.mcpModalSelected.icon = base64String;
        }
      }
    });
    reader.readAsDataURL(file);
  }

  /**
   * 获取图标
   * **/
  public getIcon(data: McpInterfaces) {
    if (!data.icon) {
      return MCP_DEFAULT_ICON_BASE64_STR;
    }
    if (data.icon.startsWith('data:image/')) {
      return data.icon;
    }
    return 'data:image/png;base64,' + data.icon;
  }

  public getFGAuth() {
    this.api.getAuth().then(res => {
      this.isFgAuth = res?.data === 'all';
    });
  }

  /** 获取tab标签 **/
  private getMcpTagData() {
    const params = {
      library_type: 'mcp',
    };
    this.promptService
      ?.getAssertTagAsync(params)
      .then(response => {
        const firstTab = this?.appMcpTabs[0];
        this.appMcpTabs.length = 0;
        this.appMcpTabs.push(firstTab);
        for (let index = 0; index < response.length; index++) {
          this.appMcpTabs.push(response[index]);
        }
      })
      .catch();
  }

  /** 获取卡片的标签 **/
  getCategoryLabel(tagId: string): string {
    if (!tagId || this.appMcpTabs.length <= 0) {
      return '';
    }
    const filterData = this.appMcpTabs.filter(item => item.id === tagId);
    if (filterData && filterData.length > 0) {
      return this.isZH() ? filterData[0].name : filterData[0].name_en;
    }
    return '';
  }

  /** 修改tab窗口的类型 **/
  changeAppTab(tab: AssertSquareTagType) {
    if (tab.active) {
      this.mcpModalList.length = 0;
      if (tab.id === 'all') {
        this.selectedTagId = '';
      } else {
        this.selectedTagId = tab.id;
      }
      this.getMCPServerList();
    }
  }

  onTabChange(index: number) {
    const tab = this.appMcpTabs[index];
    if (tab) {
      tab.active = true;
      this.changeAppTab(tab);
    }
  }

  /** 是否展示获取token的alert **/
  isShowTokenAlert() {
    return (
      this.mcpModalSelected.org_type === 'UVX' ||
      this.mcpModalSelected.org_type === 'NPX' ||
      this.mcpModalSelected.org_type === 'SSE' ||
      this.mcpModalSelected.org_type === 'STREAMABLE_HTTP'
    );
  }

  /** 控制MCP填写参数的展示与否 **/
  handleClickChangeCollapseMcpConfig() {
    this.isCollapseMcpConfig = !this.isCollapseMcpConfig;
  }

  /** 添加api-key/header或者query认证参数 **/
  handleClickAddAPIParams() {
    if (this.mcpAuthConfigData.selectedAuthPos === 'HEADERS') {
      this.mcpAuthConfigData.authHeaderParams.push({
        name: '',
        value: '',
      });
    } else {
      this.mcpAuthConfigData.authQueryParams.push({
        name: '',
        value: '',
      });
    }
    this.handleChangeAPIKeyRadio();
  }

  /** 删除api-key/header或者query认证参数 **/
  handleClickDeleteAPIParams(index: number) {
    if (this.mcpAuthConfigData.selectedAuthPos === 'HEADERS') {
      if (this.mcpAuthConfigData.authHeaderParams.length <= 0) {
        return;
      }
      this.mcpAuthConfigData.authHeaderParams.splice(index, 1);
      this.handleChangeAPIKeyRadio();
      return;
    }
    if (this.mcpAuthConfigData.authQueryParams.length <= 0) {
      return;
    }
    this.mcpAuthConfigData.authQueryParams.splice(index, 1);
    this.handleChangeAPIKeyRadio();
  }

  /** 是否展示api-key的参数名称 **/
  isShowAPIParams() {
    if (this.mcpAuthConfigData.selectedAuthType !== 'SERVICE') {
      return false;
    }
    if (this.mcpAuthConfigData.selectedAuthPos === 'HEADERS') {
      return this.mcpAuthConfigData.authHeaderParams.length > 0;
    }
    if (this.mcpAuthConfigData.selectedAuthPos === 'QUERY') {
      return this.mcpAuthConfigData.authQueryParams.length > 0;
    }
    return false;
  }

  /** 是否展示密钥位置 **/
  isShowSecretPos() {
    return this.mcpAuthConfigData.selectedAuthType === 'SERVICE';
  }

  /** 是否展示Oauth的配置信息 **/
  isShowOauthConfig() {
    return this.mcpAuthConfigData.selectedAuthType === 'OAUTH';
  }

  /** 是否展示参数列表 **/
  isShowParamList() {
    return this.mcpAuthConfigData.selectedAuthType === 'SERVICE';
  }

  // 切换APIKEY中的Header和Query
  handleChangeAPIKeyRadio() {
    if (this.mcpAuthConfigData.selectedAuthType !== 'SERVICE') {
      this.isDisabledConfirmBtn = false;
      return;
    }
    if (this.mcpAuthConfigData.selectedAuthPos === 'HEADERS') {
      this.isDisabledConfirmBtn = false;
      if (this.mcpAuthConfigData.authHeaderParams.length <= 0) {
        this.isDisabledConfirmBtn = false;
        return;
      }
      for (let index = 0; index < this.mcpAuthConfigData.authHeaderParams.length; index++) {
        if (this.mcpAuthConfigData.authHeaderParams[index].name === '' || this.mcpAuthConfigData.authHeaderParams[index].value === '') {
          this.isDisabledConfirmBtn = true;
          break;
        }
      }
      return;
    }
    if (this.mcpAuthConfigData.selectedAuthPos === 'QUERY') {
      this.isDisabledConfirmBtn = false;
      if (this.mcpAuthConfigData.authQueryParams.length <= 0) {
        this.isDisabledConfirmBtn = false;
        return;
      }
      for (let index = 0; index < this.mcpAuthConfigData.authQueryParams.length; index++) {
        if (this.mcpAuthConfigData.authQueryParams[index].name === '' || this.mcpAuthConfigData.authQueryParams[index].value === '') {
          this.isDisabledConfirmBtn = true;
          break;
        }
      }
      return;
    }
    return;
  }

  // 切换鉴权方式要取消按钮的置灰操作
  handleChangeAuthWay() {
    this.oauthErrors = { url: false, id: false, secret: false, scope: false };
    if (this.mcpAuthConfigData.selectedAuthType === 'SERVICE') {
      this.handleChangeAPIKeyRadio();
      return;
    }
    this.isDisabledConfirmBtn = false;
  }

  changeOauthUrlError() {
    if (this.mcpAuthConfigData.authParams.url) {
      if (/^https?:\/\/.+/.test(this.mcpAuthConfigData.authParams.url)) {
        this.oauthURLErrors = '';
      } else {
        this.oauthURLErrors = 'URL格式不正确';
      }
    } else {
      this.oauthURLErrors = '请填写URL';
    }
  }

  protected readonly changeUrl = cdnAssetUrl;
}
