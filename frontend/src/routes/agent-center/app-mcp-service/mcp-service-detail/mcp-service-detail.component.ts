import { Component, OnDestroy, OnInit, QueryList, ViewChild, ViewChildren } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, Subscription } from 'rxjs';
import { FormBuilder, FormControl, NgForm } from '@angular/forms';
import { CommonModule, Location } from '@angular/common';
import { NzModalService } from 'ng-zorro-antd/modal';
import { MessageComponent } from '@shared/services/cfdata.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ContextService } from '@services/context.service';
import { MCPService } from '@services/agent-center/mcp.service';
import { McpInterfaces, McpTool, McpToolProperties } from '@interfaces/mcp/mcp.interfaces';
import { CommonUtils } from '../../../../utils/common.util';
import { MarkdownComponent } from 'ngx-markdown';
import { MonacoEditorConstructionOptions, MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { MCP_DEFAULT_ICON_BASE64_STR, MCP_INSTALL_ICON_BASE64_STR } from '@shared/config/default-icons-base64';
import { CustomStarComponent } from '@shared/components/custom-star/custom-star.component';
import { CommonNoDataWithBtnComponent } from '@shared/components/common-no-data-with-btn/common-no-data-with-btn.component';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { AddMcpHalfModalComponent } from '@routes/agent-center/app-mcp-service/components/add-mcp-half-modal/add-mcp-half-modal.component';
import { PermissionService } from '@services/permission.service';
import { WindowResizeService } from '@shared/base/window-resize.service';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { McpAllService } from '@routes/service-market/mcp-all.service';
import { ITmplCard } from '@interfaces/prompt/prompt-template.interface';
import { McpDeployFailType } from '@routes/agent-center/types/common.types';
import { copyToClipboard } from '../../../../utils/commonFn';

enum mapKeys {
  WORK_SPACE_ID = 'work_space_id',
  developSpaceMCP = 'developSpaceMCP',
  score_avg = 'score_avg',
  from = 'from',
}

@Component({
  selector: 'mcp-service-detail',
  templateUrl: './mcp-service-detail.component.html',
  styleUrls: ['./mcp-service-detail.component.less'],
  standalone: true,
  imports: [CommonModule, MODULES, MarkdownComponent, MonacoEditorModule, CustomStarComponent, CommonNoDataWithBtnComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class MCPServiceDetailComponent implements OnInit, OnDestroy {
  @ViewChildren('runForm') runForm!: QueryList<NgForm>;
  @ViewChild(CustomStarComponent) starComponent: CustomStarComponent;
  public currentPermissions: any;
  private permissionSubscription: Subscription;
  private readonly destroy$ = new Subject<void>();
  public changeUrl = cdnAssetUrl;
  public serviceId = '';
  public mcpServiceDetail: McpInterfaces = null;
  public loading = false;
  public form = this.fb.group({
    authKeys: this.fb.array<FormControl>([]),
  });
  public validator = {
    validate: {
      tip: this.i18n.transform('variable_validator4'),
      errorMessage: {
        pattern: this.i18n.transform('variable_validator4'),
      },
    },
  };
  public booleanOps = [
    {
      label: 'true',
      value: true,
    },
    {
      label: 'false',
      value: false,
    },
  ];
  public isOpAccount = false;
  public currentUser = '';
  public lang: string;
  public tabs = [];
  public selectedMcpTool: McpTool = null;
  public toolParamCollapsed: boolean = false;
  public selectedMcpToolParams = [];
  public testMcpToolRes: string = JSON.stringify({}, null, 2);
  public editorOptions: MonacoEditorConstructionOptions = {
    theme: 'vs-dark',
    language: 'json',
    lineNumbers: 'off',
    readOnly: true,
    minimap: {
      enabled: false,
    },
  };
  public isLoading = true;
  public queryParamType: string = '';
  public scoreModalRef: any;
  public type: string = '';
  public recommendMCPList: McpInterfaces[] = [];
  public testMcpLoading: boolean = false;
  protected readonly MCP_DEFAULT_ICON_BASE64_STR = MCP_DEFAULT_ICON_BASE64_STR;
  private isFromDevelopSpace: boolean = false;
  private isFromOverview: boolean = false;

  public isFromAgentBuilder: boolean = false;
  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  private resizeSub: Subscription;
  // 兼容agentBuilder
  workSpaceId: string = '';
  // 是否正在获取NPX或者UVX的工具
  isPendingToolLoading: boolean = false;
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  mcpFailInfo: McpDeployFailType = {
    code: '',
    debug_info: '',
    message_en: '',
    message_cn: '',
    reason_en: '',
    reason_cn: '',
    suggestion_cn: '',
    suggestion_en: '',
  };
  resource = '';
  version_id = '';
  orgType = '';
  public isKmsError: boolean = false; // 是否kms加解密失败

  constructor(
    private readonly fb: FormBuilder,
    private readonly router: Router,
    private readonly route: ActivatedRoute,
    private readonly ctxServ: ContextService,
    private readonly i18n: I18NextEagerPipe,
    private readonly api: MCPService,
    private location: Location,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private permissionService: PermissionService,
    private windowResizeService: WindowResizeService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private mcpAllService: McpAllService,
    private nzModal: NzModalService
  ) {
    this.isOpAccount = this.ctxServ.isOpAccount;
    this.currentUser = this.ctxServ.user.userId;
    this.route.queryParams.subscribe(params => {
      this.serviceId = params.id;
      this.queryParamType = params.type;
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
      if (params[mapKeys.WORK_SPACE_ID]) {
        this.workSpaceId = params[mapKeys.WORK_SPACE_ID];
      }
    });
    this.lang = CommonUtils.getLanguage();
  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
        window[mapKeys.developSpaceMCP] = this.isFromDevelopSpace;
      }
      if (params.from && params.from === 'overview') {
        this.isFromOverview = true;
      }
    });
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.getRouteParams();
    this.getDetail();
    this.getMcpRecommendation();
    this.permissionSubscription = this.permissionService.permissions$.subscribe(permissions => {
      this.currentPermissions = permissions;
    });
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe(width => {
      this.windowWidth = width;
    });
  }

  private getRouteParams() {
    this.route.queryParams.subscribe(params => {
      const { id, type, resource, version_id, org_type } = params;
      this.type = type;
      this.serviceId = id;
      this.resource = resource || '';
      this.version_id = version_id || '';
      this.orgType = org_type || '';
    });
  }

  public initData(resData: McpInterfaces) {
    this.mcpServiceDetail = resData;
    this.mcpServiceDetail.score = Math.round(resData[mapKeys.score_avg] / 2);
    if (this.mcpServiceDetail.created_date) {
      this.mcpServiceDetail.created_date = this.formatToLocalTime(this.mcpServiceDetail.created_date);
    }
    this.setMcpDeployFail(resData.fail_reason_detail || ({} as any));
    this.setStatus();
    if (typeof this.mcpServiceDetail.tools === 'string') {
      try {
        this.mcpServiceDetail.tools = JSON.parse(this.mcpServiceDetail.tools as any);
        this.commonTools();
      } catch (e) {
        // do something
      }
    }
    this.setType();
    this.setTabs();
    this.isLoading = false;
  }

  private setStatus() {
    if (this.mcpServiceDetail.fc_instance_status === 'success') {
      this.mcpServiceDetail.status_cn = this.i18n.transform('mcpservicedetailcomponent_716');
      this.mcpServiceDetail.status_en = 'installed';
    } else if (this.mcpServiceDetail.fc_instance_status === 'creatingStack') {
      this.mcpServiceDetail.status_cn = this.i18n.transform('mcpservicedetailcomponent_717');
      this.mcpServiceDetail.status_en = 'installing';
    } else {
      this.mcpServiceDetail.status_cn = this.i18n.transform('mcpservicedetailcomponent_718');
      this.mcpServiceDetail.status_en = 'failed';
    }
  }

  private setType() {
    if (this.mcpServiceDetail.type === 'inner') {
      this.mcpServiceDetail.type_cn = this.i18n.transform('llmselectcomponent_425');
      this.mcpServiceDetail.type_en = 'Platform';
    } else {
      this.mcpServiceDetail.type_cn = this.i18n.transform('mcpservicedetailcomponent_720');
      this.mcpServiceDetail.type_en = 'User';
    }
  }

  public setDefaultData() {
    for (let index = 0; index < this.mcpServiceDetail.tools.length; index++) {
      const requiredArr = this.mcpServiceDetail.tools[index].inputSchema.required || [];
      const keys = Object.keys(this.mcpServiceDetail.tools[index].inputSchema.properties);
      for (let keyIndex = 0; keyIndex < keys.length; keyIndex++) {
        if (requiredArr.indexOf(keys[keyIndex]) !== -1) {
          this.mcpServiceDetail.tools[index].inputSchema.properties[keys[keyIndex]].isRequired = requiredArr.indexOf(keys[keyIndex]) !== -1;
        }
        this.mcpServiceDetail.tools[index].inputSchema.properties[keys[keyIndex]].value =
          this.mcpServiceDetail.tools[index].inputSchema.properties[keys[keyIndex]].default;
        this.setSpecialDefaultData(this.mcpServiceDetail.tools[index], keys[keyIndex]);
      }
    }
  }

  private setSpecialDefaultData(mcpTool: McpTool, key: string) {
    if (
      mcpTool.inputSchema.properties[key].value !== undefined &&
      mcpTool.inputSchema.properties[key].value !== null &&
      mcpTool.inputSchema.properties[key].value !== ''
    ) {
      mcpTool.inputSchema.properties[key].isRight = true;
      return;
    }
    if (!mcpTool.inputSchema.properties[key].type) {
      mcpTool.inputSchema.properties[key].type = 'string';
      mcpTool.inputSchema.properties[key].value = 'str';
      mcpTool.inputSchema.properties[key].isRight = true;
      return;
    }
    const keyType = mcpTool.inputSchema.properties[key].type.toLowerCase();
    if (keyType === 'boolean') {
      mcpTool.inputSchema.properties[key].value = true;
    } else if (keyType === 'number' || keyType === 'integer' || keyType === 'float' || keyType === 'double') {
      mcpTool.inputSchema.properties[key].value = 0;
    } else if (keyType === 'string') {
      mcpTool.inputSchema.properties[key].value = 'str';
    } else if (keyType === 'array') {
      if (!mcpTool.inputSchema.properties[key].items) {
        mcpTool.inputSchema.properties[key].value = [];
        mcpTool.inputSchema.properties[key].isRight = true;
        return;
      }
      const itemType = mcpTool.inputSchema.properties[key].items.type;
      if (typeof itemType !== 'string') {
        mcpTool.inputSchema.properties[key].value = [];
        mcpTool.inputSchema.properties[key].isRight = true;
        return;
      }
      if (itemType && itemType.toLowerCase() === 'string') {
        mcpTool.inputSchema.properties[key].value = JSON.stringify(new Array(1).fill('str'));
      } else if (
        itemType &&
        (itemType.toLowerCase() === 'number' ||
          itemType.toLowerCase() === 'integer' ||
          itemType.toLowerCase() === 'float' ||
          itemType.toLowerCase() === 'double')
      ) {
        mcpTool.inputSchema.properties[key].value = JSON.stringify(new Array(1).fill(0));
      } else {
        mcpTool.inputSchema.properties[key].value = JSON.stringify(new Array(0));
      }
    } else if (keyType === 'object' || keyType === 'map') {
      this.setObjectDefaultData(mcpTool, key);
    } else {
      mcpTool.inputSchema.properties[key].value = 'str';
    }
    mcpTool.inputSchema.properties[key].isRight = true;
  }

  private setObjectDefaultData(mcpTool: McpTool, key: string) {
    const properties = mcpTool.inputSchema.properties[key].properties;
    const obj = {};
    const keys = Object.keys(properties || {});
    for (let index = 0; index < keys.length; index++) {
      if (!properties[keys[index]].type) {
        obj[keys[index]] = '';
        properties[keys[index]].type = 'string';
        continue;
      }
      const type = properties[keys[index]].type.toLowerCase();
      if (type === 'string') {
        obj[keys[index]] = 'str';
        continue;
      }
      if (type === 'number' || type === 'float' || type === 'integer' || type === 'double') {
        obj[keys[index]] = 0;
        continue;
      }
      if (type === 'boolean') {
        obj[keys[index]] = true;
        continue;
      }
      if (type === 'array') {
        let _type = properties[keys[index]].items.type;
        if (typeof _type !== 'string') {
          obj[keys[index]] = new Array(0);
          continue;
        }
        _type = _type.toLowerCase();
        if (_type === 'string') {
          obj[keys[index]] = new Array(1).fill('str');
        } else if (_type === 'number' || _type === 'float' || _type === 'double' || _type === 'integer') {
          obj[keys[index]] = new Array(1).fill(0);
        } else if (_type === 'boolean') {
          obj[keys[index]] = new Array(1).fill(true);
        } else {
          obj[keys[index]] = new Array(0);
        }
        continue;
      }
      if (type === 'object' || type === 'map') {
        obj[keys[index]] = {};
        continue;
      }
      obj[keys[index]] = 'str';
    }
    mcpTool.inputSchema.properties[key].value = JSON.stringify(obj);
  }

  setTabs() {
    this.tabs.push({
      id: 0,
      title: this.i18n.transform('overview'),
      active: true,
    });
    this.tabs.push({
      id: 1,
      title: this.i18n.transform('node_g_tool'),
      active: false,
    });
    this.tabs.push({
      id: 2,
      title: this.i18n.transform('monitor'),
      active: false,
    });
  }

  ngOnDestroy(): void {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
    this.resizeSub?.unsubscribe();
    if (this.permissionSubscription) {
      this.permissionSubscription.unsubscribe();
    }
  }

  onPageBack() {
    const getStateVal: any = this.location.getState();
    const hasPreviousRoute = getStateVal?.navigationId > 1;
    if (this.isFromOverview) {
      this.router.navigate(['/home/overview']);
      return;
    }
    let queryParams: any = {};
    if (this.isFromAgentBuilder) {
      queryParams[mapKeys.from] = 'agentBuilder';
    }
    if (this.workSpaceId) {
      queryParams[mapKeys.WORK_SPACE_ID] = this.workSpaceId;
    }
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space']);
    } else if (this.type === 'server') {
      this.router.navigate(['/home/service-market']);
    } else if (this.type === 'service') {
      queryParams.tabId = 'mcp';
      this.router.navigate(['/home/agent-center/library-home'], { queryParams });
    } else {
      queryParams.tabId = 'mcp';
      hasPreviousRoute ? this.location.back() : this.router.navigate(['/home/agent-center/library-home'], { queryParams });
    }
  }

  getDetail() {
    this.isLoading = true;
    if (this.queryParamType === 'server') {
      this.api
        .getServerDetail(this.serviceId)
        .then((res: any) => {
          this.initData(res);
        })
        .catch(() => {
          this.isLoading = false;
          this.isKmsError = true;
        });
    } else if (this.queryParamType === 'service') {
      this.api
        .getServiceDetail(this.serviceId)
        .then((res: any) => {
          if (res && !res.tools) {
            if (res.fc_instance_status === 'success' || res.fc_instance_status === 'pendingTools' || res.fc_instance_status === 'creatingStack') {
              this.getTools(res.fc_instance_status);
            }
          }
          this.initData(res);
        })
        .catch(() => {
          this.isLoading = false;
          this.isKmsError = true;
        });
    } else if (this.queryParamType === 'third') {
      this.mcpAllService
        .getMcpSquareThirdDetail(this.serviceId, this.resource, this.version_id, this.orgType)
        .then((res: any) => {
          this.initData(res);
        })
        .finally(() => {
          this.isLoading = false;
        });
    }
  }

  private setMcpDeployFail(failInfo: McpDeployFailType) {
    this.mcpFailInfo.code = failInfo.code || 'Openjiuwen.Unknown';
    this.mcpFailInfo.debug_info = failInfo.debug_info || 'N/A';
    this.mcpFailInfo.message_cn = failInfo.message_cn || '服务状态异常。';
    this.mcpFailInfo.message_en = failInfo.message_en || 'Service Status Abnormal.';
    this.mcpFailInfo.reason_en = failInfo.reason_en || 'The system detected an abnormal deployment status, but no specific error code was captured.';
    this.mcpFailInfo.reason_cn = failInfo.reason_cn || '系统检测到服务部署状态异常，但未捕获到明确的错误码。';
    this.mcpFailInfo.suggestion_cn = failInfo.suggestion_cn || '请检查服务配置是否正确并重新部署。如多次失败，请联系管理员排查。';
    this.mcpFailInfo.suggestion_en =
      failInfo.suggestion_en || 'Please verify the configuration and redeploy. If the failure persists, contact the administrator.';
  }

  getTools(type: string) {
    if (type === 'pendingTools' || type === 'creatingStack') {
      this.isPendingToolLoading = true;
    }
    this.api
      .getMcpTools(this.serviceId)
      .then((tools: any) => {
        if (Array.isArray(tools)) {
          if (type === 'pendingTools' || type === 'creatingStack') {
            this.mcpServiceDetail.fc_instance_status = 'success';
          }
          this.mcpServiceDetail.tools = tools;
          this.commonTools();
        }
      })
      .catch(() => {
        if (type === 'creatingStack') {
          this.mcpServiceDetail.fc_instance_status = 'stackFail';
        }
      })
      .finally(() => {
        this.isPendingToolLoading = false;
      });
  }

  private commonTools() {
    if (!this.mcpServiceDetail.tools || this.mcpServiceDetail.tools.length === 0) {
      return;
    }
    for (let index = 0; index < this.mcpServiceDetail.tools.length; index++) {
      this.mcpServiceDetail.tools[index].isCollapsed = true;
    }
    this.mcpServiceDetail.tools[0].isCollapsed = false;
    this.selectedMcpTool = this.mcpServiceDetail.tools[0];
    this.setDefaultData();
    this.getSelectedMcpToolParams();
  }

  getMcpRecommendation() {
    if (this.type === 'service') {
      return;
    }
    this.api
      .getRecommendList()
      .then((res: any) => {
        if (Array.isArray(res)) {
          this.recommendMCPList.length = 0;
          for (let index = 0; index < res.length; index++) {
            this.recommendMCPList.push(res[index]);
          }
        }
      })
      .catch(err => {})
      .finally(() => {});
  }

  isCN(): boolean {
    return this.lang === 'zh-cn';
  }

  formatToLocalTime(isoString: string) {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false, // 24小时制
    })
      .format(date)
      .replace(/\//g, '-') // 将斜杠替换为短横线
      .replace(/(\d{2}):(\d{2}):(\d{2})/, '$1:$2:$3'); // 保持格式统一
  }

  handleClickTools(data: McpTool) {
    for (let index = 0; index < this.mcpServiceDetail.tools.length; index++) {
      if (this.mcpServiceDetail.tools[index].name === data.name) {
        continue;
      }
      this.mcpServiceDetail.tools[index].isCollapsed = true;
    }
    data.isCollapsed = !data.isCollapsed;
    if (!data.isCollapsed) {
      this.selectedMcpTool = data;
      this.getSelectedMcpToolParams();
      return;
    }
    this.mcpServiceDetail.tools[0].isCollapsed = false;
    this.selectedMcpTool = this.mcpServiceDetail.tools[0];
    this.getSelectedMcpToolParams();
  }

  private getSelectedMcpToolParams() {
    if (!this.selectedMcpTool || !this.selectedMcpTool.inputSchema || !this.selectedMcpTool.inputSchema.properties) {
      this.selectedMcpToolParams = [];
      return;
    }
    const data = [];
    const keys = Object.keys(this.selectedMcpTool.inputSchema.properties);
    for (let index = 0; index < keys.length; index++) {
      const obj = {
        key: keys[index],
        value: this.selectedMcpTool.inputSchema.properties[keys[index]],
        copyValue: '',
      };
      if (this.isDataEmpty(this.selectedMcpTool.inputSchema.properties[keys[index]].copyValue)) {
        this.selectedMcpTool.inputSchema.properties[keys[index]].copyValue = obj.value.value;
      }
      if (typeof obj.value.value !== 'object') {
        obj.copyValue = this.selectedMcpTool.inputSchema.properties[keys[index]].copyValue;
      } else {
        obj.copyValue = JSON.stringify(this.selectedMcpTool.inputSchema.properties[keys[index]].copyValue);
        obj.value.copyValue = obj.copyValue;
        obj.value.value = obj.copyValue;
        obj.value.default = obj.copyValue;
      }
      data.push(obj);
    }
    this.selectedMcpToolParams = data;
    return;
  }

  // 调测MCP工具
  public testMcpTool() {
    const data = {};
    let dataIsWrong = false;
    for (let index = 0; index < this.selectedMcpToolParams.length; index++) {
      try {
        this.selectedMcpToolParams[index].value.isRight = true;
        data[this.selectedMcpToolParams[index].key] = this.selectedMcpToolParams[index].value.value;

        if (this.selectedMcpToolParams[index].value.isRequired) {
          if (this.isDataEmpty(this.selectedMcpToolParams[index].value.value)) {
            this.selectedMcpToolParams[index].value.isRight = false;
            dataIsWrong = true;
            continue;
          }
          const result = this.commonTestMcpTool(data, index);
          if (result) {
            this.selectedMcpToolParams[index].value.isRight = false;
          }
          if (!dataIsWrong) {
            dataIsWrong = result;
          }
          continue;
        }

        if (this.isDataEmpty(this.selectedMcpToolParams[index].value.value)) {
          continue;
        }
        const result = this.commonTestMcpTool(data, index);
        if (result) {
          this.selectedMcpToolParams[index].value.isRight = false;
        }
        if (!dataIsWrong) {
          dataIsWrong = result;
        }
      } catch {
        dataIsWrong = true;
        this.selectedMcpToolParams[index].value.isRight = false;
      }
    }
    if (!dataIsWrong) {
      const params = {
        params: data,
        serviceId: this.serviceId,
        toolName: this.selectedMcpTool.name,
      };
      this.testMcpLoading = true;
      this.testMcpToolRes = JSON.stringify({}, null, 2);
      this.api
        .testMcpTools(params)
        .then(res => {
          this.testMcpToolRes = JSON.stringify(res, null, 2);
        })
        .catch(err => {
          this.testMcpToolRes = JSON.stringify({ result: this.i18n.transform('MCPTestError') }, null, 2);
        })
        .finally(() => {
          this.testMcpLoading = false;
        });
    }
  }

  // 抽取公共代码逻辑
  private commonTestMcpTool(data: object, index: number): boolean {
    if (this.selectedMcpToolParams[index].value.type === 'string') {
      return false;
    }
    try {
      data[this.selectedMcpToolParams[index].key] = JSON.parse(this.selectedMcpToolParams[index].value.value);
      return false;
    } catch (e) {
      return true;
    }
  }

  // 数据是否为空
  private isDataEmpty(data: any): boolean {
    return data === '' || data === null || data === undefined;
  }

  // 复原参数数据
  public recoveryParamsData(index: number) {
    if (typeof this.selectedMcpToolParams[index].copyValue !== 'object') {
      this.selectedMcpToolParams[index].value.value = this.selectedMcpToolParams[index].copyValue;
    } else {
      this.selectedMcpToolParams[index].value.value = JSON.stringify(this.selectedMcpToolParams[index].copyValue);
    }
    this.selectedMcpToolParams[index].value.isRight = true;
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  /**
   * 点击热门推荐的MCP应用
   * **/
  public handleClickMcpServer(item: McpInterfaces) {
    this.refreshComponent(item);
  }

  private refreshComponent(data: McpInterfaces) {
    this.isLoading = true;
    this.type = 'server';
    this.serviceId = data.id;
    this.getDetail();
    data.isHover = false;
  }

  onClick(event: Event) {
    event.stopPropagation();
  }

  /**
   * 操作MCP_SERVER
   * **/
  public handleClickActionMcpServer(event: MouseEvent, item: McpInterfaces, type: string) {
    if (type === 'create') {
      this.handleClickInstallMcpServer(event, item);
    } else {
      this.handleEditMcpServer(event, item);
    }
  }

  public hasPermission(): boolean {
    return this.currentPermissions && this.currentPermissions.OPERATOR;
  }

  /**
   * 安装MCP_SERVER
   * **/
  public handleClickInstallMcpServer(event: MouseEvent, item: McpInterfaces) {
    this.onClick(event);
    if (this.hasPermission()) {
      return;
    }
    if (this.type === 'third') {
      const new_params = {
        resource: this.resource,
        versionId: this.version_id,
      };
      const query = {};
      this.mcpAllService.getThirdDetail(query, new_params, this.serviceId).then(res => {
        this.installThird(res);
      });
    } else {
      const thisNzModal: any = this.nzModal.create({
        nzContent: AddMcpHalfModalComponent,
        nzWidth: '1000px',
      });
      const instance = thisNzModal.getContentComponent();
      instance.type = 'server';
      instance.selectMcpData = item;
      instance.action = 'create';
    }
  }

  public installThird(detail) {
    const query = {
      resource: this.resource,
    };
    const selectedRows = [detail];
    const new_servers = this.mcpAllService.installThirdCommonParams(selectedRows);
    const params = {
      servers: new_servers,
    };
    this.mcpAllService.thirdDeployBatch(query, params).then(res => {
      for (let i = 0; i < res.results.length; i++) {
        if (res.results[i].status === 'FAILED') {
          MessageComponent.showError(`${this.i18n.transform('service_name')}:${res.results[i].name}，${res.results[i].errorMessage}`, 3000);
        }
        if (res.results[i].status === 'SUCCESS') {
          this.nzModal.info({
            nzTitle: '',
            nzContent: this.i18n.transform('MCPSubmitSuccessContent'),
          });
        }
      }
    });
  }

  /**
   * 编辑MCP_SERVER
   * **/
  public handleEditMcpServer(event: MouseEvent, item: McpInterfaces) {
    this.onClick(event);

    const thisNzModal: any = this.nzModal.create({
      nzContent: AddMcpHalfModalComponent,
      nzWidth: '1000px',
    });
    const instance = thisNzModal.getContentComponent();
    instance.type = 'service';
    instance.selectMcpData = item;
    instance.action = 'edit';
    instance.close.subscribe(() => {
      this.getDetail();
    });
  }

  public updateScore(content: any) {
    this.scoreModalRef = this.nzModal.create({
      nzContent: content,
      nzFooter: null,
    });
  }

  public getChildStar(data: number) {
    this.mcpServiceDetail.score = data;
  }

  public updateMCPRatingFunc(context: any) {
    this.api
      .updateMcpRate({
        score: this.mcpServiceDetail.score,
        server_id: this.mcpServiceDetail.id,
      })
      .then(res => {
        this.scoreModalRef?.close();
        this.getDetail();
      })
      .catch(res => {});
  }

  /**
   * 获取图标
   * **/
  public getIcon(data: McpInterfaces) {
    if (!data.icon) {
      return MCP_DEFAULT_ICON_BASE64_STR;
    }
    if (data.icon.startsWith('http')) {
      return data.icon;
    }
    if (data.icon.startsWith('data:image/')) {
      return data.icon;
    }
    return 'data:image/png;base64,' + data.icon;
  }

  handleMouseEnterInstallMcp(item: any) {
    item.isHoverInstall = true;
  }

  handleMouseLeaveInstallMcp(item: any) {
    item.isHoverInstall = false;
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return '800px';
    } else {
      return '600px';
    }
  }

  copyData() {
    copyToClipboard(this.mcpFailInfo.code);
  }

  // 重新部署MCP
  public redeployMcp() {
    this.isLoading = true;
    this.api
      .getMcpTools(this.serviceId)
      .then(() => {
        MessageComponent.showSuccess(this.i18n.transform('MCPSubmitSuccessContent'), 6000);
        this.getDetail();
      })
      .catch(() => {
        this.isLoading = false;
      });
  }
}
