import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { ModalManagementComponent } from '@routes/model-management/model-management.component';
import { ModelRouteComponent } from '@routes/model-management/model-route/model-route.component';
import { OnlineTestComponent } from '@routes/model-management/online-test/online-test.component';
import { InformationTemplateComponent } from '@routes/information-template/information-template.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonService } from '@services/common.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { CertificationComponent } from '@routes/model-management/certification/certification.component';
import { HttpService } from '@services/http.service';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService } from 'ng-zorro-antd/modal';
import { IntentPackageComponent } from '@routes/intent-package/intent-package/intent-package.component';
import { ObjectManageComponent } from '@routes/object-manage/object-manage.component';
import { DatasourceManagementComponent } from '@routes/datasource-management/datasource-management.component';
@Component({
  selector: 'development-configuration',
  templateUrl: './development-configuration.component.html',
  styleUrls: ['./development-configuration.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    ModalManagementComponent,
    ModelRouteComponent,
    OnlineTestComponent,
    InformationTemplateComponent,
    CertificationComponent,
    NzTabsModule,
    IntentPackageComponent,
    ObjectManageComponent,
    DatasourceManagementComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.KNOWLEDGE, I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.MODEL_ACCESS, I18nNamespace.TRACE],
    },
    NzModalService,
  ],
})
export class DevelopmentConfigurationComponent implements OnInit, OnDestroy {
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  showBetaTip = false;
  isBetaLoading = true;

  tabs = [
    { id: 'custom-model', i18nKey: 'custom_model', active: false, show: true },
    { id: 'route-policy', i18nKey: 'route_policy', active: false, show: true },
    { id: 'model-test', i18nKey: 'model_test', active: false, show: true },
    { id: 'intent-manage', i18nKey: 'intent_management', active: false, show: true },
    { id: 'message-template', i18nKey: 'message_template', active: false, show: true },
    { id: 'object-manage', i18nKey: 'object_manage', active: false, show: true },
    { id: 'datasource', i18nKey: 'data_source_management', active: false, show: true },
  ];

  activeId = 'custom-model';
  activeTabs = [];
  selectedIndex = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private configServ: AgentConfigService,
    private commonService: CommonService,
    private visibilityService: SetSidebarVisibilityService,
    private readonly http: HttpService,
    private message: NzMessageService
  ) {
    this.checkDatasourceVisibility();
  }

  async ngOnInit(): Promise<void> {
    this.visibilityService.setSidebarsVisibilityByState(null);

    this.route.queryParams.subscribe(params => {
      this.activateTabByUrl(params?.previousUrl);
    });
    await this.initBetaStatus();
  }

  handleTabChange(index: number) {
    const tab = this.activeTabs[index];
    if (tab && !tab.active) {
      this.tabs.forEach(t => (t.active = false));
      tab.active = true;
      this.activeId = tab.id;
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: {
          previousUrl: this.activeId,
        },
        replaceUrl: true,
      });
    }
  }

  private checkDatasourceVisibility(): void {
    const { block_nodes = [] } = this.configServ.getConfigs();
    const blockedSet = new Set(block_nodes.map(node => node?.toLowerCase()));
    this.tabs.forEach(item => {
      if (item.id === 'datasource') {
        item.show = !(blockedSet.has('sql') && blockedSet.has('dataquery'));
      }
    });
    this.activeTabs = this.tabs.filter(t => t.show);
  }

  private async initBetaStatus(): Promise<void> {
    this.isBetaLoading = false;
  }

  private activateTabByUrl(previousUrl: string): void {
    this.tabs.forEach(item => (item.active = false));
    let tabItem = this.tabs.find(item => item.id === previousUrl);

    if (tabItem && tabItem.show) {
      tabItem.active = true;
      this.activeId = tabItem.id;
      this.selectedIndex = this.activeTabs.findIndex(t => t.id === this.activeId);
    } else {
      if (this.activeTabs.length > 0) {
        this.activeId = this.activeTabs[0].id;
        this.tabs.find(t => t.id === this.activeId)!.active = true;
        this.selectedIndex = 0;
      }
    }
  }

  ngOnDestroy(): void {
    this.visibilityService.setSidebarsVisibilityByState('destroy');
  }
}
