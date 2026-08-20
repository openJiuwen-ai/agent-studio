import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { MODULES } from '@shared/modules';
import { Subject, takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { CommonUtils } from 'src/utils/common.util';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import {
  IPluginWithTools,
  IRequestArgsView,
  IResponseArgsView,
} from '@routes/agent-center/app-plugin/app-plugin.interface';
import {
  coverToolInfo, getFlatData,
} from '@routes/agent-center/app-plugin/utils';
import { PluginHeaderComponent } from '@routes/agent-center/app-plugin/plugin-header/plugin-header.component';
import { formatTime } from 'src/utils/commonFn';
import { PipesModule } from 'src/pipes/pipes.module';

@Component({
  selector: 'meta-plugin-tool-detail',
  templateUrl: './tool-detail.component.html',
  styleUrls: ['./tool-detail.component.less'],
  imports: [MODULES, PluginHeaderComponent, PipesModule],
  standalone: true,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginToolDetailComponent implements OnInit {
  public toolId = '';
  public pluginId = '';
  public isLoading = false;

  public name = '--';
  public toolInfo = {
    tool_display_name: '--',
    tool_desc: '--',
    output_schema: '',
    input_schema: '',
  };
  public plugin: IPluginWithTools = {} as IPluginWithTools;

  public authInfo: {
    type: 'no_auth' | 'API Key';
    location?: string;
    params?: {
      value: string;
      name: string;
    }[];
  } = {
    type: 'no_auth',
  };
  public lang = CommonUtils.getLanguage();
  public authTbd: any = {
    data: [],
    state: undefined,
  };

  public requestCol: any[] = [
    'param_name',
    'param_type',
    'req_loc',
    'default_v',
    'description',
    'required',
  ].map((key) => ({
    title: this.i18n.transform(key),
  }));

  public responseCol: any[] = [
    'param_name',
    'description',
    'param_type',
  ].map((key) => ({
    title: this.i18n.transform(key),
  }));
  public responseDisplayedData: any[] = [];

  public responseSrcData: any = {
    data: [],
    state: undefined,
  };

  public requestDisplayedData: any[] = [];

  public requestSrcData: any = {
    data: [],
    state: undefined,
  };

  public req: IRequestArgsView[] = [];

  public res: IResponseArgsView[] = [];

  public isPluginMarket = true;

  public previewVersionId = '';

  public previewVersionName = '';

  private destroy$ = new Subject<void>();

  public isFromAgentBuilder: boolean = false;
  public isFromDevelopSpace: boolean = false;

  constructor(
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private i18n: I18NextEagerPipe,
    private route: ActivatedRoute,
    private appPluginRepoServ: AppPluginRepoService,
    private router: Router,
    private agentDataServe: AgentDataService,
    private agentRepoServe: AppAgentRepoService,
  ) {
    this.pluginId = this.route.snapshot.queryParams.plugin_id;
    this.toolId = this.route.snapshot.queryParams.tool_id;
    this.isPluginMarket = this.router.url.indexOf('plugin-market/detail') > -1;
    this.route.queryParams.subscribe((params) => {
      if (params.from && params.from === 'agentBuilder') {
        this.isFromAgentBuilder = true;
      }
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
    });
    this.agentDataServe
      .getPreviewVersion()
      .pipe(takeUntil(this.destroy$))
      .subscribe((versionInfo) => {
        this.previewVersionName = versionInfo?.version_name;
        this.previewVersionId = versionInfo?.version_id;
        if (versionInfo?.version_id) {
          this.getPluginVersion(versionInfo.version_id);
        }
      });
  }

  async ngOnInit() {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    await this.getPluginDetails();
  }

  ngOnDestroy(): void {
    this.agentDataServe.setPreviewVersion(undefined);
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }
  exitViewHistory() {
    this.agentDataServe.setPreviewVersion(undefined);
  }
  coverPluginInfo() {
    coverToolInfo(this);
  }
  getPluginVersion(version_id: any) {
    this.agentRepoServe
      .getPluginVersion(this.toolId, version_id)
      .then((res) => {
        this.plugin = res;
        this.coverPluginInfo();
      });
  }
  private getFlatData(
    nodes: any[],
    level?: number,
  ): any[] {
    return getFlatData(nodes, level);
  }

  async getPluginDetails() {
    try {
      this.isLoading = true;
      let value: any;

      if (this.isPluginMarket) {
        value = await this.appPluginRepoServ.getPluginById(this.pluginId);
        this.plugin = value.data;
        this.coverPluginInfo();
      } else {
        value = await this.appPluginRepoServ.getPluginList({
          limit: 1,
          offset: 0,
          id: this.pluginId,
        });

        if (value.plugin_list?.length) {
          this.plugin = value.plugin_list[0];
          this.coverPluginInfo();
        }
      }
    } finally {
      this.isLoading = false;
    }
  }
  getLevelStyle(node: any): { 'padding-left': string } {
    return {
      'padding-left': `${node.level * 24 + 10}px`,
    };
  }
  toggle(node: any, type: 'req' | 'res'): void {
    node.expand = !node.expand;

    if (type === 'res') {
      this.responseSrcData.data = this.getFlatData(this.res);
    } else {
      this.requestSrcData.data = this.getFlatData(this.req);
    }
  }

  protected readonly formatTime = formatTime;
}
