import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { MODULES } from '@shared/modules';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { I18nNamespace } from '@i18n';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';

import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import {
  ADD_TYPE,
  AddTypeOptions,
} from '@routes/app-center/app-center-management/app-center-management.config';
import { ShareService } from '@routes/app-center/components/edit-share-modal/share.service';
import { WORKFLOW_SVGS } from '@routes/agent-center/app-flow/flow.const';
import { CommonUtils } from 'src/utils/common.util';
import { ApplicationType } from '@enums/agent-center.enum';
import {
  CONTROLLER_SUB_CONTROLLER_LIMIT,
  CONTROLLER_SUB_FLOW_LIMIT,
  SubAgentModel,
  SubApplication,
  SubWorkFlow,
} from '@routes/agent-center/app-flow/components/controller-modal/controller-modal.interface';
import { ShareListReq } from '@routes/app-center/components/edit-share-modal/edit-share-modal.interface';
import { IBaseQuery } from '@routes/agent-center/app-flow/app-flow.types';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { CommonService } from '@services/common.service';

@Component({
  selector: 'add-multiple-agent-modal',
  templateUrl: './add-multiple-agent-modal.component.html',
  styleUrls: ['./add-multiple-agent-modal.component.less'],
  standalone: true,
  imports: [
    MODULES,
    FormsModule,
    NewCommonNoDataWithBtnComponent,
    NzTabsModule,
    NzAlertModule,
    NzButtonModule,
    NzInputModule,
    NzIconModule,
    NzToolTipModule,
    NzTagModule,
    NzCheckboxModule,
    NzSelectModule,
    NzPaginationModule,
    NzSpinModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AddMultipleAgentModalComponent implements OnInit {
  @Input() currentAgentId: string;
  @Input() agentSelected: (SubAgentModel | SubWorkFlow)[] = [];
  @Input() agentSelectedLimit = 1;
  @Input() outputs: {
    agentSelectListEvent?: (agents: (SubAgentModel | SubWorkFlow)[]) => void;
    closeDrawer?: () => void;
  };

  @Output('agentSelectListEvent') agentSelectListEvent = new EventEmitter<
    (SubAgentModel | SubWorkFlow)[]
  >();

  public agents: (SubAgentModel | SubWorkFlow)[] = [];
  public showTags = true;

  public currentPage = 1;
  public totalNumber = 0;
  public activeTabIndex = 0;
  public pageSize = {
    options: [10, 20, 30, 40, 50, 100],
    size: 10,
  };

  public isLoading = false;
  public agentTabs = [
    {
      id: ApplicationType.SINGLE_AGENT,
      title: this.i18n.transform('single_agent'),
      active: true,
    },
    {
      id: ApplicationType.WORKFLOW,
      title: this.i18n.transform('workflow'),
      active: false,
    },
    {
      id: ApplicationType.MULTI_AGENT,
      title: this.i18n.transform('multiple_agent'),
      active: false,
    },
  ];
  public activeTabId = this.agentTabs[0].id;

  public agentSpaceType = AddTypeOptions.map((type) => ({
    id: type.id,
    text: type.title,
  }));
  public agentSpace = this.agentSpaceType[0];
  public shareSearchKey = '';

  get isShareSpace() {
    return (
      this.agentSpace?.id === ADD_TYPE.SHARE &&
      this.activeTabId !== ApplicationType.SINGLE_AGENT
    );
  }

  get isSingleAgent() {
    return this.activeTabId === ApplicationType.SINGLE_AGENT;
  }

  get isZH(): boolean {
    return CommonUtils.getLanguage() === 'zh-cn';
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  private refreshFnMap: Record<string, () => void> = {
    [ApplicationType.SINGLE_AGENT]: () => {
      this.initSingleAgentList();
    },
    [ApplicationType.WORKFLOW]: () => {
      this.initWorkFlowList();
    },
    [ApplicationType.MULTI_AGENT]: () => {
      this.initMultiAgentList();
    },
  };
  constructor(
    private appFlowRepoServe: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private shareService: ShareService,
    private configServ: AgentConfigService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.agentTabs = this.agentTabs.filter(item => this.configServ.getConfigs()?.studio_btn_show || item.id !== ApplicationType.SINGLE_AGENT);
    this.agentTabs[0].active = true;
    this.activeTabId = this.agentTabs[0].id;

    if (!this.isShowSingleEnter()) {
      this.agentTabs = this.agentTabs.filter(
        (item) => item.id !== ApplicationType.SINGLE_AGENT,
      );
      this.agentTabs[0].active = true;
      this.activeTabId = this.agentTabs[0].id;
    }
    this.currentPage = 1;
    this.refreshList();
  }

  public close(): void {
    this.outputs?.closeDrawer?.();
  }

  public dismiss(): void {
    this.outputs?.closeDrawer?.();
  }

  public submit(): void {
    this.outputs?.agentSelectListEvent?.(this.agentSelected);
    this.outputs?.closeDrawer?.();
  }

  public onTabChange(tab: any): void {
    if (tab.active) {
      this.activeTabId = tab.id;
      this.showTags = this.activeTabId !== ApplicationType.MULTI_AGENT;
      this.shareSearchKey = '';
      this.refreshList();
    }
  }

  public onTabIndexChange(index: number): void {
    const tab = this.agentTabs[index];
    if (tab) {
      this.activeTabId = tab.id;
      this.showTags = this.activeTabId !== ApplicationType.MULTI_AGENT;
      this.shareSearchKey = '';
      this.refreshList();
    }
  }

  public onSpaceChange(): void {
    this.refreshList();
  }

  public onCardClick(agent: SubAgentModel | SubWorkFlow, event: Event): void {
    event.stopPropagation();
    if (agent.disable) {
      return;
    }
    if (this.isSingleAgent) {
      if (!agent.checked) {
        agent.checked = true;
        this.onCardSingleSelected(agent);
      }
    } else {
      agent.checked = !agent.checked;
      this.onCardMultiSelected(agent);
    }
  }

  public onCardSelected(agent: SubAgentModel | SubWorkFlow) {
    if (agent.disable) {
      return;
    }
    if (this.isSingleAgent) {
      if (agent.checked) {
        // 选中：单选语义，先清掉已选的单智能体再选当前
        this.onCardSingleSelected(agent);
      } else {
        // 取消选中：从已选列表移除，计数归零
        const index = this.agentSelected.findIndex(
          (item) => item.id === agent.id,
        );
        if (index > -1) {
          this.agentSelected.splice(index, 1);
        }
      }
    } else {
      this.onCardMultiSelected(agent);
    }
  }

  public onCardMultiSelected(agent: SubAgentModel | SubWorkFlow) {
    if (agent.checked) {
      this.agentSelected.push(agent);
    } else {
      const index = this.agentSelected.findIndex(
        (item) => item.id === agent.id,
      );
      if (index > -1) {
        this.agentSelected.splice(index, 1);
      }
    }

    this.agents.forEach(item => {
      item.disable = this.getCardDisable(item);
    });
  }

  public onCardSingleSelected(agent: SubAgentModel | SubWorkFlow) {
    this.agents.forEach((item) => {
      item.checked = false;
    });

    const index = this.agentSelected.findIndex(
      (item) => item.subAgentType ===  ApplicationType.SINGLE_AGENT,
    );
    if (index > -1) {
      this.agentSelected.splice(index, 1);
    }

    agent.checked = true;
    this.agentSelected.push(agent);
  }

  public refreshList(isSearch = false): void {
    if (isSearch) {
      this.currentPage = 1;
    }

    if (
      this.isShareSpace &&
      this.activeTabId !== ApplicationType.SINGLE_AGENT
    ) {
      this.initShareList();
      return;
    }

    const refreshFn = this.refreshFnMap[this.activeTabId];
    refreshFn?.();
  }

  public isShowSingleEnter() {
    return true;
  }

  private initSingleAgentList(): void {
    this.isLoading = true;
    const params = {
      ...this.getListPageParams(),
      type: 'agent',
      sub_type: 'planexecute',
      name: this.shareSearchKey || '',
    };
    this.appFlowRepoServe
      .getPublishedMutilAgentList(params)
      .then((data) => {
        this.isLoading = false;
        this.agents =
          data?.agent_version_list?.map((item) => {
            const id = item.id;
            const checked =
              this.agentSelected.findIndex((agent) => agent.id === id) > -1;

            const agent = {
              id: id,
              name: item.name,
              type: ApplicationType.SINGLE_AGENT,
              subAgentType: ApplicationType.SINGLE_AGENT,
              mode: 'PlanExecute',
              description: item.description,
              avatar: item.icon || WORKFLOW_SVGS.Agent,
              creator: item.creator,
              version_id: item.version_id,
              version_name: item.version_name,
              checked,
              disable: false,
              tags: [this.i18n.transform('agent_planning_mode')],
            };
            agent.disable = this.getCardDisable(agent);
            return agent;
          }) ?? [];

        this.totalNumber = data.count;
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  private initWorkFlowList(): void {
    this.isLoading = true;
    const params = {
      offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
      limit: this.pageSize.size,
      name: this.shareSearchKey || '',
    };
    this.appFlowRepoServe
      .getPublishedFlows(params)
      .then((data) => {
        this.isLoading = false;
        this.agents =
          data?.workflow_version_list?.map((item) => {
            const i18nKey =
              item.type === 'chat' ? 'workflow_chat' : 'workflow_task';
            const tags = [this.i18n.transform(i18nKey)];

            const agent: SubWorkFlow = {
              id: item.workflow_id,
              name: item.name,
              type: 'Normal',
              flowType: item.type,
              subAgentType: ApplicationType.WORKFLOW,
              description: item.description,
              avatar: item.avatar || WORKFLOW_SVGS.Workflow,
              creator: item.creator,
              version_id: item.version_id,
              version_name: item.version_name,
              disable: false,
              checked:
                this.agentSelected.findIndex(
                  (agent) => agent.id === item.workflow_id,
                ) > -1,
              tags,
            };
            agent.disable = this.getCardDisable(agent);
            return agent;
          }) ?? [];

        this.totalNumber = data.count;
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  private initMultiAgentList(): void {
    this.isLoading = true;
    const params = {
      ...this.getListPageParams(),
      name: this.shareSearchKey || '',
      type: 'controller',
    };
    this.appFlowRepoServe
      .getPublishedMutilAgentList(params)
      .then((data) => {
        this.isLoading = false;
        this.agents =
          data?.agent_version_list?.map((item) => {
            const agent = {
              id: item.id,
              name: item.name,
              type: ApplicationType.MULTI_AGENT,
              subAgentType: ApplicationType.MULTI_AGENT,
              mode: 'Controller',
              description: item.description,
              avatar: item.icon || WORKFLOW_SVGS.Controller,
              creator: item.creator,
              version_id: item.version_id,
              version_name: item.version_name,
              disable: item.id === this.currentAgentId,
              tip:
                item.id === this.currentAgentId
                  ? this.i18n.transform('addmultipleagentmodalcomponent_23')
                  : '',
              checked:
                this.agentSelected.findIndex((agent) => agent.id === item.id) >
                -1,
            };
            agent.disable = this.getCardDisable(agent);

            return agent;
          }) ?? [];

        this.totalNumber = data.count;
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  private initShareList() {
    const resourceType =
      this.activeTabId === ApplicationType.MULTI_AGENT
        ? ApplicationType.MULTI_AGENT
        : ApplicationType.WORKFLOW;
    const params: ShareListReq = {
      ...this.getListPageParams(),
      resource_name: this.shareSearchKey,
      resource_type: resourceType,
    };

    this.isLoading = true;
    this.shareService
      .getShareList(params)
      .then((res) => {
        this.isLoading = false;
        const list = res?.resource_list || [];
        this.agents = list.map((item) => {
          let tags = [];
          if (this.activeTabId === ApplicationType.WORKFLOW) {
            const i18nKey =
              item.type === 'chat' ? 'workflow_chat' : 'workflow_task';
            tags = [this.i18n.transform(i18nKey)];
          }

          const agent: SubApplication = {
            id: item.resource_id,
            name: item.resource_name_ch,
            type: resourceType,
            subAgentType: resourceType,
            description: item.resource_desc,
            avatar: item.resource_icon,
            workspace_id: item.workspace_id,
            workspace_name: item.workspace_name,
            version_info_list: item.version_info_list,
            version_id: item.version_info_list[0].version_id,
            version_name: item.version_info_list[0].version_name,
            disable: false,
            checked:
              this.agentSelected.findIndex(
                (agent) => agent.id === item.resource_id,
              ) > -1,
            fromShare: true,
            tags,
          };
          agent.disable = this.getCardDisable(agent);

          return agent;
        });
        this.totalNumber = res?.count;
        this.cdr.detectChanges();
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  private getListPageParams(): IBaseQuery {
    return {
      offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
      limit: this.pageSize.size,
    };
  }

  private getCardDisable(agent: SubApplication): boolean {
    if (agent.checked || agent.subAgentType === ApplicationType.SINGLE_AGENT) {
      return false;
    }

    if (agent.id === this.currentAgentId) {
      return true;
    }

    const limit = agent.subAgentType === ApplicationType.MULTI_AGENT
      ? CONTROLLER_SUB_CONTROLLER_LIMIT : CONTROLLER_SUB_FLOW_LIMIT;
    const currentNum = this.agentSelected.filter(item => item.subAgentType === agent.subAgentType).length;

    return currentNum >= limit;
  }
}
