import { SkillCommonService } from '@agentcore/library/skill/services/skill.common.service';
import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { KnowledgeBaseListComponent } from '@routes/knowledge-center/knowledge-base-list/knowledge-base-list.component';
import { MemoryLibManagementComponent } from '@routes/memory-lib/memory-lib-management/memory-lib-management.component';
import { CommonService } from '@services/common.service';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { ComponentLibraryComponent } from '../component-library/component-library.component';
import { PromptTemplateComponent } from '@routes/prompt/prompt-template/prompt-template.component';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { SkillComponent } from '@agentcore/library/skill/skill.component';
@Component({
  selector: 'library-home-component',
  templateUrl: './library-home.component.html',
  styleUrls: ['./library-home.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    ComponentLibraryComponent,
    KnowledgeBaseListComponent,
    MemoryLibManagementComponent,
    NzTabsModule,
    PromptTemplateComponent,
    SkillComponent,
  ],
  providers: [
    SkillCommonService,
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
        I18nNamespace.PROMPT_PLATFORM,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.MEMORY_LIB,
      ],
    },
  ],
})
export class LibraryHomeComponent implements OnInit, OnDestroy {
  activeTabs: any[] = [
    {
      show: true,
      id: 'skill',
      title: this.i18n.transform('skill_market'),
      active: true,
    },
    {
      show: true,
      id: 'plugin',
      title: this.i18n.transform('plugin'),
      active: false,
    },
    {
      show: true,
      id: 'mcp',
      title: 'MCP',
      active: false,
    },
    {
      show: true,
      id: 'prompt',
      title: this.i18n.transform('route_prompt'),
      active: false,
    },
    {
      show: true,
      id: 'knowledge',
      title: this.i18n.transform('knowledge_base'),
      active: false,
    },
    {
      show: true,
      id: 'memoryLib',
      title: this.i18n.transform('memory.management.title'),
      active: false,
    },
    {
      show: true,
      id: 'card',
      title: this.i18n.transform('Card'),
      active: false,
    },
  ];

  public tabs: any[] = this.activeTabs.filter(t => t.show);

  public currentTabId = this.tabs[0].id;
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  tabSelectIndex = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private i18n: I18NextEagerPipe,
    public configServ: AgentConfigService,
    private commonService: CommonService,
    private visibilityService: SetSidebarVisibilityService
  ) {
    this.route.queryParams.subscribe(params => {
      this.tabs.forEach(item => (item.active = false));
      const tabItem = this.tabs.find(item => item.id === params.tabId);
      if (tabItem) {
        tabItem.active = true;
        this.currentTabId = tabItem.id;
      } else {
        this.currentTabId = this.tabs[0].id;
        this.tabs[0].active = true;
      }
    });
  }

  ngOnInit() {
    this.visibilityService.setSidebarsVisibilityByState(null);
    let projectID: any = '';
    try {
      const curSpaceOptions = StorageService?.getSessionStorage('CUR_SPACE_OPTIONS');
      projectID = JSON.parse(curSpaceOptions || '{}').projectId;
    } catch (error) {
      projectID = '';
    }
    const cardWhitelist = (this.configServ.getConfigs()?.card_whitelist || '').split(',');
    const hideCard = cardWhitelist.indexOf(projectID) < 0;
    if (hideCard) {
      this.tabs = this.tabs.filter(item => item.id !== 'card');
    }
    this.filterMemoryLib();
    this.tabSelectIndex = this.tabs.findIndex(item => item.active);
  }

  ngOnDestroy(): void {
    this.visibilityService.setSidebarsVisibilityByState('destroy');
  }

  filterMemoryLib() {
    this.tabs = this.tabs.filter(tab => {
      if (tab.id === 'memoryLib') {
        return this.configServ.isSupportUserPersona();
      }
      return true;
    });
  }

  public handleTabChange(index: number) {
    this.tabs.forEach((item, i) => {
      item.active = i === index;
    });
    const tab = this.tabs[index];
    if (tab.active) {
      this.currentTabId = tab.id;
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: {
          tabId: this.currentTabId,
        },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    }
  }
}
