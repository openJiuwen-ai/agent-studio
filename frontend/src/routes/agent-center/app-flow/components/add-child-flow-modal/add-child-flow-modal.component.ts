import { Component, EventEmitter, Input, OnInit, Output, ChangeDetectorRef, inject, NgZone } from '@angular/core';
import { Router } from "@angular/router";
import { FormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { IWorkflow, PublishedWorkflow } from '../../app-flow.types';
import { IPluginNode } from '../../node.type';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { ADD_TYPE, AddTypeOptions } from '@routes/app-center/app-center-management/app-center-management.config';
import { ShareService } from '@routes/app-center/components/edit-share-modal/share.service';
import { PAGINATION_LIMIT_NUM } from '@routes/agent-center/types/my-workspace.types';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { CommonService } from '@services/common.service';
import { CommonUtils } from 'src/utils/common.util';
import { cloneDeep } from "lodash";
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
export interface IWorkflowInfoAdapter {
  id: string;
  name: string;
  description: string;
}

@Component({
  selector: 'meta-add-child-flow-modal',
  templateUrl: './add-child-flow-modal.component.html',
  styleUrls: ['./add-child-flow-modal.component.less'],
  standalone: true,
  imports: [
    MODULES,
    NewCommonNoDataWithBtnComponent,
    FormsModule,
    NzButtonModule,
    NzInputModule,
    NzTabsModule,
    NzIconModule,
    NzSelectModule,
    NzToolTipModule,
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
export class AddChildFlowModalComponent implements OnInit {
  @Input() workflowType: string;
  @Input() workflowId: string;
  @Output('workflowChange') workflowChange = new EventEmitter<{
    workflow: IWorkflow;
    config: any;
  }>();
  @Input() isAgentPage: boolean;
  @Input() outputs: {
    workflowChange?: (data: { workflow: IWorkflow; config: any }) => void;
    closeDrawer?: () => void;
    workflowSelectEvent?: (data: any) => void;
    workflowSelectListEvent?: (data: any) => void;
  };
  @Input() workflowSelected: any = [];
  readonly drawerRef = inject(NzDrawerRef);
  @Input() isAgentSingle: boolean;
  @Input() workflowSelectedLimit = 1;
  @Input() multiFlowType: string;
  @Output('workflowSelectEvent') workflowSelectEvent = new EventEmitter<any>();
  @Output('workflowSelectListEvent') workflowSelectListEvent = new EventEmitter<any>();
  agentSingleSelect: any;
  public controller = new AbortController();
  public is_current_sapce = true;
  public noDataBtnStr = this.i18n.transform('app_create_flow');
  public is_site = this.commonService.isSite();// 是否是lite环境

  public add_workflows_tabs: any = [
    {
      title: this.i18n.transform('addchildflowmodal_1'),
      active: true,
      onActiveChange: (info) => {
        if (info) {
          this.workflows = [];
          this.is_current_sapce = true;
          this.noDataBtnStr = this.i18n.transform('app_create_flow');
          this.initApiList();
        }
      },
    },
    {
      title: this.i18n.transform('addchildflowmodal_2'),
      disabled: false,
      onActiveChange: (info) => {
        if (info) {
          this.workflows = [];
          this.is_current_sapce = false;
          this.noDataBtnStr = ''
          this.initList();
        }
      },
    },
  ];

  public tabs = [
    {
      id: 'personal',
      title: this.i18n.transform('personal_workflow'),
      active: true,
    },
  ];
  public workflows = [];

  public currentPage = 1;

  public totalNumber = 0;

  public pageSize: any = {
    options: [10, 20, 30, 40, 50, 100],
    size: 10,
  };

  public isLoading = false;

  public addedCnt = 0;

  public addedNumMap: Record<string, number> = {};

  private currTab = 'personal';

  public addTypeOptions = cloneDeep(AddTypeOptions);
  public activeTabId = this.addTypeOptions[0].id;
  public searchKey = '';
  public activeTabIndex = 0;

  get isShareTab() {
    return this.activeTabId === ADD_TYPE.SHARE;
  }
  get isAppTab() {
    return this.activeTabId === ADD_TYPE.OFFICIAL;
  }

  public lang = CommonUtils.getLanguage();
  get isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  constructor(
    private appFlowRepoServe: AppFlowRepoService,
    private configServ: AgentConfigService,
    private i18n: I18NextEagerPipe,
    private router: Router,
    private shareService: ShareService,
    private readonly commonService: CommonService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
  ) {
  }

  ngOnInit() {
    if (this.workflowSelected.length) {
      this.addedCnt = this.workflowSelected.length;
    }
    this.initList();
  }

  public isDisabled(workflow: PublishedWorkflow) {

    // 任务型工作流不支持添加对话型工作流
    if (workflow.type === 'chat' && this.workflowType === 'task') {
      return true;
    }
    // 工作流不支持引用自己
    if (workflow.workflow_id === this.workflowId) {
      return true;
    }
    // 子工作流可以嵌套
    if (this.configServ.getConfigs().son_workflow_level_limit === false) {
      return false;
    }
    // 子工作流不可以嵌套
    if (workflow.reference_workflows) {
      return true;
    }
    return false;
  }

  getWorkflowType(type) {
    return type === 'chat'
      ? this.i18n.transform('chat')
      : this.i18n.transform('task');
  }

  public disabledTip(workflow: PublishedWorkflow) {
    if (workflow.type === 'chat' && this.workflowType === 'task') {
      return this.i18n.transform('task_wf_not_support_add_conversational_wf');
    }
    if (workflow.workflow_id === this.workflowId) {
      return this.i18n.transform('wf_not_support_referencing_self');
    }
    if (this.configServ.getConfigs().son_workflow_level_limit === false) {
      return '';
    }
    if (workflow.reference_workflows) {
      return this.i18n.transform('not_support_nested_multilayer_wf');
    }
    return '';
  }

  /*当前空间*/
  public async initApiList(type?: string) {
    if (this.controller) {

      this.controller = new AbortController();
      this.isLoading = true;

      if ('search' === type) {
        this.currentPage = 1;
      }

      const params = {
        offset: ((this.currentPage || 1) - 1) * this.pageSize.size,
        limit: this.pageSize.size,
        name: this.searchKey,
      };
      // 增加区分预置和当前的参数

      try {
        const data = await this.appFlowRepoServe.getPublishedFlows(params);
        this.isLoading = false;
        const list = data?.workflow_version_list ?? [];
        list.forEach((v: any) => {
          if (v.version_info_list?.length && !v.version_info_list[0]?.value) {
            v.version_info_list = v.version_info_list.map((item: any) => ({
              value: item.version_id,
              label: item.version_name,
            }));
          }
        });
        this.workflows = [...list];
        this.totalNumber = data.count;
        this.cdr.detectChanges();
      } catch (error) {
        this.cdr.detectChanges();
      } finally {
        this.isLoading = false;
      }
    }
  }

  /*搜索*/
  public search_fn(type?: string) {
    this.currentPage = 1;
    if (this.isShareTab) {
      this.initShareList();
    } else {
      this.initApiList('search');
    }
  }

  public clicked: boolean = false; //组件

  public get isWorkflowSelectionLimitReached(): boolean {
    return !this.isAgentPage && this.addedCnt >= this.workflowSelectedLimit;
  }

  public async addWorkflow(e: Event, workflow: PublishedWorkflow) {
    e.stopPropagation();
    if (this.clicked || this.isWorkflowSelectionLimitReached) {
      return;
    }
    this.clicked = true;
    if (this.isAgentPage) {
      this.clicked = false;
      return;
    }
    try {
      const flow = await this.appFlowRepoServe.getFlowVersionInfo(
        workflow.workflow_id,
        workflow.version_id,
      );
      ++this.addedCnt;
      this.addedNumMap[workflow.workflow_id] = this.addedNumMap[
        workflow.workflow_id
      ]
        ? ++this.addedNumMap[workflow.workflow_id]
        : 1;

      if (this.isShareTab && workflow.version_info_list) {
        const getVal: any = workflow.version_info_list.find(
          (item: any) => workflow.version_id === item.value,
        );
        workflow.version_name = getVal?.label;
      }

      const result = {
        workflow: flow,
        config: {
          id: workflow.workflow_id,
          version_id: workflow.version_id,
          version_name: workflow.version_name,
          name: workflow.name,
          type: workflow.type,
          fromShare: workflow.fromShare,
          plugins: (flow.workflow_details.nodes.filter((item) => item.type === 'Plugin') as IPluginNode[]
          ).map((item) => {
            return {
              id: item.id,
              version: '',
            };
          }),
        },
      };
      this.ngZone.run(() => {
        this.workflowChange.emit(result);
        if (this.outputs && this.outputs.workflowChange) {
          this.outputs.workflowChange(result);
        }
        this.clicked = false;
        this.cdr.markForCheck();
        this.cdr.detectChanges();
        this.drawerRef.close();
      });
    } catch (error) {
      console.error('addWorkflow error:', error);
      this.ngZone.run(() => {
        this.clicked = false;
        this.cdr.markForCheck();
        this.cdr.detectChanges();
      });
    }
  }

  public onActiveChange(
    tab: { title: string; active: boolean; id: string },
    isActive: boolean,
  ) {
    if (isActive) {
      this.currentPage = 1;
      this.totalNumber = 0;
      this.pageSize.size = 10;
      this.currTab = tab.id;
      this.initList();
    }
  }

  public getCardIcon(workflow: PublishedWorkflow) {
    return workflow.avatar || WORKFLOW_SVGS.Workflow;
  }

  public close(): void {
    this.outputs?.closeDrawer?.();
  }
  public dismiss(): void {
    this.outputs?.closeDrawer?.();
  }

  submit(): void {
    if (this.isAgentPage) {
      if (this.isAgentSingle) {
        this.outputs?.workflowSelectEvent?.(this.agentSingleSelect);
        this.workflowSelectEvent.emit(this.agentSingleSelect);
      } else {
        this.outputs?.workflowSelectListEvent?.(this.workflowSelected);
        this.workflowSelectListEvent.emit(this.workflowSelected);
      }
    }
    this.outputs?.closeDrawer?.();
  }

  createWorkflow() {
    localStorage.removeItem('multiFlowTypeInfo');
    this.router.navigate(['/home/agent-center/create'], {
      queryParams: {
        from: 'edit-flow',
        multiFlowType: this.multiFlowType ?? '',
        workflowId: this.workflowId,
      },
    });
  }

  handleClickClearSearch() {
    this.searchKey = '';
    this.currentPage = 1;
    if (this.isShareTab) {
      this.initShareList();
    } else {
      this.initApiList();
    }
  }

  public tabChange(tab: any): void {
    this.activeTabId = tab.id;
    this.searchKey = '';
    this.initList();
    this.is_current_sapce = tab.id !== ADD_TYPE.CURRENT_SPACE;
  }

  public onTabIndexChange(index: number): void {
    const tab = this.addTypeOptions[index];
    if (tab) {
      this.tabChange(tab);
    }
  }

  public init($event?: any) {
    this.currentPage = 1;
    this.agentSingleSelect = null;
  }

  public initList($event?: any) {
    this.init()
    if (this.isShareTab) {
      this.initShareList('search');
    } else {
      this.initApiList('search');
    }
  }

  public pageChange() {
    if (this.isShareTab) {
      this.initShareList();
    } else {
      this.initApiList();
    }
  }

  public initShareList(type?: string) {
    if ('search' === type) {
      this.currentPage = 1;
    }

    const params: any = {
      offset: ((this.currentPage || 1) - 1) * PAGINATION_LIMIT_NUM,
      limit: PAGINATION_LIMIT_NUM,
      resource_type: 'workflow',
      // 增加区分预置和当前的参数
    };
    if (this.searchKey) {
      params.resourceName = this.searchKey;
    }

    this.isLoading = true;
    this.shareService.getShareList(params).then(
      (res: any) => {
        this.isLoading = false;
        const list = res?.resource_list || [];
        list.forEach(v => {
          v.name = v.resource_name_ch;
          v.description = v.resource_desc;
          v.status = 1;
          v.workflow_id = v.resource_id;
          v.code = v.resource_name_ch;
          v.avatar = v.resource_icon;
          v.fromShare = true;
          if (v.version_info_list?.length) {
            v.version_id = v.version_info_list[0].version_id;
            v.version_name = v.version_info_list[0].version_name;
            if (v.version_info_list[0]?.version_id && !v.version_info_list[0]?.value) {
              v.version_info_list = v.version_info_list.map((item: any) => ({
                value: item.version_id,
                label: item.version_name,
              }));
            }
          }
        });
        this.workflows = [...list];
        this.totalNumber = res?.count;
        this.cdr.detectChanges();
      },
      () => {
        this.isLoading = false;
        this.cdr.detectChanges();
      },
    );
  }

  public handleIconClick(type: string, item: any, event: any) {
    event.stopPropagation();
    if (type === 'add') {
      this.addOneWorkflow(item);
    } else {
      this.reduceOneWorkflow(item);
    }
  }

  public addOneWorkflow(item: any) {
    this.workflowSelected.push(item);
    ++this.addedCnt;
  }
  public reduceOneWorkflow(item: any) {
    const index = this.workflowSelected.findIndex(
      (workflowItem: any) => (workflowItem.id || workflowItem.workflow_id) === item.workflow_id,
    );
    if (index > -1) {
      this.workflowSelected.splice(index, 1);
      --this.addedCnt;
    }
  }

  /** 每个工作流卡片显示+，还是- */
  public isAddOrReduceIcon(item: any) {
    return this.workflowSelected.some(
      (workflowId: any) => (workflowId.id || workflowId.workflow_id) === item.workflow_id,
    );
  }

  public changeSelectCard(card: any): void {
    if (this.isAgentPage && this.isAgentSingle) {
      this.agentSingleSelect = card;
    }

  }

  public visionSelectedChange(select: any, workflow) {
    workflow.version_id = select.version_id;
  }

  visionClick(event) {
    event?.stopPropagation();
  }

}
