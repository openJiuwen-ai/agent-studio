import { Component, ViewChild, Input, inject, Inject, Optional, ChangeDetectorRef } from '@angular/core';
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
import { NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
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

  private reqSeq = 0;

  private readonly cdr = inject(ChangeDetectorRef);

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
    @Optional() @Inject(NZ_MODAL_DATA) public nzData: any,
    @Optional() @Inject(NZ_DRAWER_DATA) public drawerData: any
  ) {
    // 兼容 modal（NZ_MODAL_DATA）与 drawer（NZ_DRAWER_DATA）两种打开方式：
    // plugin-market 走 modal，app-plugin 走 drawer，取先不为空者
    const data = this.nzData || this.drawerData;
    this.tool_id = data?.tool_id ?? '';
    if (data?.type) {
      this.type = data.type;
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
    // 捕获调用时的 app_type 与请求序号，避免慢响应在切 Tab 后回来覆盖/滤空
    const seq = ++this.reqSeq;
    const reqType = this.curActiveTabId;
    // 切 Tab 时立即清空旧数据，避免上一个 Tab 的数据在新 Tab 下短暂显示
    this.srcData.data = [];
    // 进入加载态：模板依赖 isLoading 切换转圈/内容，避免慢接口期间显示空表格
    this.isLoading = true;
    this.cdr.markForCheck();
    this.mcpRepoServe
      .getReferenceList(this.tool_id, {
        offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
        limit: this.pageSize.size,
        showlatest: true,
        app_type: reqType,
        resource_type: 'tool',
      })
      .then((res: IMappings) => {
        if (seq !== this.reqSeq) {
          return;
        }
        this.relations = res.relations;
        // 后端 selectByResourceIdAndVersionId 已按 app_type 过滤，前端直接使用即可
        this.srcData.data = this.relations;
        this.totalNumber = res.count;
        this.isLoading = false;
        this.cdr.markForCheck();
      })
      .catch(() => {
        if (seq !== this.reqSeq) {
          return;
        }
        this.relations = [];
        this.srcData.data = [];
        this.totalNumber = 0;
        this.isLoading = false;
        this.cdr.markForCheck();
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
    // 切 Tab 回到第 1 页并清零总数，避免沿用旧 Tab 的分页/总数导致新 Tab 空表错位
    this.currentPage = 1;
    this.totalNumber = 0;
    this.getReferenceList();
  }

  public onPageSizeChange() {
    // 切换每页条数后回到第 1 页并重新请求
    this.currentPage = 1;
    this.getReferenceList();
  }
}
