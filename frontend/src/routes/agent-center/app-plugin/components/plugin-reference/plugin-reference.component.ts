import { Component, ViewChild, Input, inject, Inject } from '@angular/core';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { IMappings } from '@routes/agent-center/types/common.types';
import { MCPService } from '@services/agent-center/mcp.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { ActivatedRoute } from '@angular/router';
import { HttpService } from '@services/http.service';
import { NZ_DRAWER_DATA, NzDrawerRef } from 'ng-zorro-antd/drawer';
@Component({
  selector: 'meta-plugin-reference',
  templateUrl: './plugin-reference.component.html',
  styleUrl: './plugin-reference.component.scss',
  standalone: true,
  imports: [MODULES, NzTableModule, NzTabsModule, NzEmptyModule, NzSpinModule, NzIconModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class PluginReferenceComponent {
  @Input() tool_id = '';

  @Input() type!: string;
  public isLoading = false;

  public btnLoading = false;

  public isFromAgentBuilder = false;

  public publishedCards;

  public cdnAssetUrl = cdnAssetUrl;

  public curActiveTabId = 'agent';

  public tabs: any = [
    {
      id: 'agent',
      title: this.i18n.transform('single_agent_app'),
      active: true,
    },
    {
      id: 'workflow',
      title: this.i18n.transform('workflow_app'),
      active: false,
    },
  ];

  tabSelectIndex = 0;

  public relations = [];

  public displayedData: any[] = [];

  srcData: any = {
    data: [],
    state: {
      searched: false,
      sorted: false,
      paginated: true,
    },
  };

  public currentPage: number = 1;

  public totalNumber: number = 0;

  public columns: any[] = [
    {
      title: this.i18n.transform('name'),
    },
    {
      title: this.i18n.transform('version'),
    },
    {
      title: this.i18n.transform('reference_plugin_version'),
    },
  ];

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  workspaceId = '';
  constructor(
    private i18n: I18NextEagerPipe,
    private readonly mcpRepoServe: MCPService,
    private route: ActivatedRoute,
    private readonly http: HttpService,
    @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {
    this.tool_id = this.nzData.tool_id;
    if (this.nzData.type) {
      this.type = this.nzData.type;
    }
    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
    });
  }

  ngOnInit(): void {
    this.workspaceId = this.http.getWorkspaceId();
    this.getReferenceList();
    this.tabSelectIndex = this.tabs.findIndex(item => item.active);
  }

  getReferenceList() {
    this.mcpRepoServe
      .getReferenceList(this.tool_id, {
        offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
        limit: this.pageSize.size,
        showlatest: true,
        app_type: this.curActiveTabId,
        resource_type: 'tool',
      })
      .then((res: IMappings) => {
        this.relations = res.relations;
        this.srcData.data = this.relations.filter(item => item.app_type === this.curActiveTabId);
        this.totalNumber = res.count;
      });
  }

  public navigateAppDetail(row: any) {
    const url = window.location.href?.split('/home');
    const prefixUrl = url[0];
    const { app_type, app_id } = row;

    if (app_type === 'agent') {
      window.open(`${prefixUrl}/home/agent-center/app-agent/detail?agentId=${app_id}`, '_blank');
    }

    if (app_type === 'workflow') {
      window.open(`${prefixUrl}/home/agent-center/app-flow/flow?id=${app_id}&workspace_id=${this.workspaceId}`, '_blank');
    }
  }

  public tabActiveChange(e: any) {
    const id = this.tabs[e.index]?.id;
    this.curActiveTabId = id;
    this.getReferenceList();
  }
}
