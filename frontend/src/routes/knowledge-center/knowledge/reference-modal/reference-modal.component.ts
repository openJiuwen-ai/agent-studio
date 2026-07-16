import { Component, Input, OnInit, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { CommonNoDataComponent } from '@shared/components/common-no-data/common-no-data.component';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { MCPService } from '@services/agent-center/mcp.service';
import { IMappings } from '@routes/agent-center/types/common.types';
import { HttpService } from '@services/http.service';

import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'reference-modal',
  templateUrl: './reference-modal.component.html',
  styleUrls: ['./reference-modal.component.less'],
  standalone: true,
  imports: [MODULES, CommonNoDataComponent, CommonModule, NzTableModule, NzTabsModule, NzSpinModule, NzPaginationModule, NzToolTipModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT, I18nNamespace.KNOWLEDGE],
    },
  ],
})
export class ReferenceModalComponent implements OnInit {
  @Input() kbId = '';

  public isLoading = false;

  public cdnAssetUrl = cdnAssetUrl;

  public currentActiveTab = 'agent';
  public selectedIndex = 0;

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

  public columns = [
    {
      title: this.i18n.transform('name'),
    },
    {
      title: this.i18n.transform('version'),
    },
  ];

  public relations = [];

  srcData = {
    data: [],
  };

  public currentPage = 1;

  public totalNumber = 0;

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  isDevelopSpace = false;

  workspaceId = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private readonly mcpRepoServe: MCPService,
    private router: Router,
    private route: ActivatedRoute,
    private readonly http: HttpService,
    private cdr: ChangeDetectorRef
  ) {
    this.route.queryParams.subscribe(params => {
      this.isDevelopSpace = (params.from && params.from === 'develop-space') || this.router.url.includes('develop-space');
    });
  }

  ngOnInit(): void {
    this.workspaceId = this.http.getWorkspaceId();
    this.getReferenceList();
  }

  getReferenceList() {
    this.isLoading = true;
    this.mcpRepoServe
      .getReferenceList(this.kbId, {
        limit: this.pageSize.size,
        showlatest: true,
        offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
        app_type: this.currentActiveTab,
        resource_type: 'repo',
      })
      .then((res: IMappings) => {
        this.relations = res.relations;
        this.srcData.data = this.relations.filter(item => item.app_type === this.currentActiveTab);
        this.totalNumber = res.count;
      })
      .finally(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  public navigateAppDetail(row: any) {
    const url = window.location.href?.split('/home');
    const prefixUrl = url[0];
    const { app_type, app_id } = row;

    if (app_type === 'agent') {
      if (this.isDevelopSpace) {
        this.router.navigate(['/home/agent-center/app-agent/detail'], {
          queryParams: {
            agentId: app_id,
            from: 'develop-space',
          },
        });
      } else {
        window.open(`${prefixUrl}/home/agent-center/app-agent/detail?agentId=${app_id}`, '_blank');
      }
    }

    if (app_type === 'workflow') {
      if (this.isDevelopSpace) {
        this.router.navigate([`/home/agent-center/app-flow/flow`], {
          queryParams: {
            id: app_id,
            from: 'develop-space',
          },
        });
      } else {
        window.open(`${prefixUrl}/home/agent-center/app-flow/flow?id=${app_id}&workspace_id=${this.workspaceId}`, '_blank');
      }
    }
  }

  public onTabChange(index: number) {
    const tab = this.tabs[index];
    if (tab) {
      this.currentActiveTab = tab.id;
      this.currentPage = 1;
      this.getReferenceList();
    }
  }
}
