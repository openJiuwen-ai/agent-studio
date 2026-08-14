import { Component, EventEmitter, Input, OnInit, Output, TemplateRef, inject } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { MessageComponent } from '@shared/services/cfdata.service';
import { CommonNoDataComponent } from '@shared/components/common-no-data/common-no-data.component';
import { MCPService } from '@services/agent-center/mcp.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { IMCPService } from '../../app-flow.types';
import { CommonValidation } from '@shared/validation/commonValidation';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { SetHalfmodalPropsService } from '@shared/services/set-halfmodal-props.service';
import {
  AddMcpServersComponent
} from '@routes/agent-center/app-agent/components/add-mcp-servers/add-mcp-servers.component';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { MasOperatorService } from '@services/mas-operator.service';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'meta-add-mcp-service-modal',
  templateUrl: './add-mcp-service-modal.component.html',
  styleUrls: ['./add-mcp-service-modal.component.less'],
  standalone: true,
  imports: [MODULES, AddMcpServersComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class AddMCPServiceModalComponent implements OnInit {
  @Output('mcpServiceChange') mcpServiceChange =
    new EventEmitter<IMCPService>();
  @Output() createMcpRes = new EventEmitter<any>();
  @Input() outputs: { mcpServiceChange: (mcpService: IMCPService) => void; createMcpRes: (data: any) => void };

  @Input() type = '';
  @Input() mcpCreateSub;
  readonly drawerRef = inject(NzDrawerRef);

  public controller = new AbortController();
  public tabs = [
    {
      id: 'preset',
      title: this.i18n.transform('pre_mcp_service'),
      active: true,
    },
    {
      id: 'personal',
      title: this.i18n.transform('personal_mcp_service'),
      active: false,
    },
  ];

  public searchItems: any[] = [
    {
      label: this.i18n.transform('service_name'),
      field: 'name',
      options: [],
    },
  ];
  public searchedItem: any[] = [];
  public mcpServiceList: IMCPService[] = [];
  public currentPage = 1;
  public totalNumber = 0;
  public pageSize: any = {
    options: [10, 20, 30, 40, 50, 100],
    size: 10,
  };
  public isLoading = false;

  public addedCnt = 0;
  public addedNumMap: Record<string, number> = {};
  private currTab = 'preset';
  public authKeyList: any[] = [];
  public form = this.fb.group({});
  public validator = {
    validate: {
      tip: this.i18n.transform('variable_validator4'),
      errorMessage: {
        pattern: this.i18n.transform('variable_validator4'),
      },
    },
  };

  public modalTop = '';
  public mcpLimit = 0;
  public emptyPlaceholder = this.i18n.transform('search_placeholder');
  public searchMarketVal: any[] = [];

  constructor(
    private readonly fb: FormBuilder,
    private readonly api: MCPService,
    private readonly configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private halfmodalPropsServe: SetHalfmodalPropsService,
    private agentDataServe: AgentDataService,
    private masOperatorService: MasOperatorService,
  ) {
    // 64是工作流顶部导航条的高度
    this.modalTop = `${this.halfmodalPropsServe.calcHalfmodalPosition().top}px`;
    this.agentDataServe.setClickFlagMCP('add');
  }

  get searchNameIsEmpty(): boolean {
    return this.searchedItem.length === 0;
  }

  ngOnInit() {
    this.initApiList();
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  public async initApiList(type?: string) {
    if (this.controller) {
      this.controller.abort();
    }

    this.controller = new AbortController();
    this.isLoading = true;
    const currentMasOperator = this.masOperatorService.getCurrentMasOperators();
    const externalMapFlag = currentMasOperator.externalMappingInfo?.length;
    if ('search' === type) {
      this.currentPage = 1;
    }
    const query:any = {
      language: 'ZH',
      name: this.searchedItem.find((item) => item.field === 'name')?.value,
    };
    if (externalMapFlag) {
      query.visibility = 'global';
    }
    const params = {
      offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
      limit: this.pageSize.size,
    };

    try {
      if (['DataProcess', 'DataSynthesis'].includes(this.type)) {
        query.node_type = this.type;
      }
      const data = await this.api.getServiceList(query, params);
      this.mcpServiceList = data?.mcps ?? [];
      this.mcpServiceList.forEach((v) => {
        v.expand = false;
      });
      this.totalNumber = data.total;
    } catch (error) {
      // do nth
    } finally {
      this.isLoading = false;
    }
  }

  public clicked: boolean = false; //组件

  public async addMcpService(e: Event, mcpService: any) {
    if (this.clicked) {
      return;
    }
    this.clicked = true;
    if (e && e.stopPropagation) {
      e.stopPropagation();
    }
    const serverId = mcpService.id;
    try {
      const mcpInfo = await this.api.getMcpToolInfo(serverId);
      if (mcpInfo) {
        this.addedNumMap[serverId] = this.addedNumMap[serverId]
          ? ++this.addedNumMap[serverId]
          : 1;
        ++this.addedCnt;

        const result = { ...mcpService, mcpInfo };
        this.mcpServiceChange.emit(result);
        this.outputs?.mcpServiceChange?.(result);
        this.drawerRef.close();
      }
    } finally {
      this.clicked = false;
    }
  }

  public onActiveChange(
    tab: { title: string; active: boolean; id: string },
    isActive: boolean,
  ) {
    if (isActive) {
      this.totalNumber = 0;
      this.currentPage = 1;
      this.pageSize.size = 10;
      this.currTab = tab.id;

      this.initApiList();
    }
  }

  public getCardIcon(mapService: IMCPService) {
    if (mapService.icon) {
      return mapService.icon.startsWith('data:image')
        ? mapService.icon
        : 'data:image/png;base64,' + mapService.icon;
    }
    return this.getIcon();
  }

  private getIcon() {
    if (this.type === 'Mcp') {
      return WORKFLOW_SVGS.Mcp;
    }
    if (this.type === 'DataSynthesis') {
      return WORKFLOW_SVGS.DataSynthesis;
    }
    return WORKFLOW_SVGS.DataProcess;
  }

  changeExpand(service: IMCPService) {
    this.form = this.fb.group({});
    this.mcpServiceList.forEach((v) => {
      if (v.server_id !== service.server_id) {
        v.expand = false;
      }
    });
    service.expand = !service.expand;
    if (service.expand) {
      this.authKeyList = service.auth?.auth_keys || [];
      this.authKeyList.forEach((v, i) => {
        const name = v.target_name + i;
        this.form.addControl(
          name,
          this.fb.control('', [
            CommonValidation.provisionServiceVerify(),
          ]),
        );
      });
    }
  }

  cancelProvision() {
    this.form = this.fb.group({});
    this.mcpServiceList.forEach((v) => {
      v.expand = false;
    });
  }

  provisioning(service: IMCPService) {
    this.form.markAllAsTouched();
    if (this.form.valid) {
      const auth_keys = this.authKeyList.map((v, i) => {
        return {
          ...v,
          auth_key: this.form.value[v.target_name + i],
        };
      });
      const params = {
        serverId: service.server_id,
        auth_keys,
      };
      this.api.provisionService(params).then((res: any) => {
        MessageComponent.showSuccess(
          this.i18n.transform('service_provision_success'),
        );
        this.mcpServiceList.forEach((v) => {
          if (v.server_id === service.server_id) {
            v.config_status = 'done';
            v.expand = false;
          }
        });
      });
    } else {
      MessageComponent.showError(this.i18n.transform('data_verify_fail'));
    }
  }

  /** 关闭MCP的侧边栏的回调函数 **/
  dismiss() {

  }

  /** 新增MCP **/
  handleMCPsAdded(data: any, $event: any) {
    if (data && data.length <= 0) {
      return;
    }
    this.addMcpService($event, data[data.length - 1]).then();
  }

  /** 删除MCP **/
  handleMCPsReduced(data: any) {}

  /** 返回添加MCP页面 **/
  backToMcpListEmit() {}

  /** 把创建的MCP添加到工作流中 **/
  public addMcpToAgent(context: any) {

  }

  /** 把子组件创建工作流的消息透传到父组件 **/
  public handleClickCreateMcpEmit(event: any) {
    this.createMcpRes.emit(event);
    this.outputs?.createMcpRes?.(event);
  }

  public test() {
  }


  handleClickClearSearch() {
    this.searchedItem = [];
    this.currentPage = 1;
    this.initApiList();
  }
}
