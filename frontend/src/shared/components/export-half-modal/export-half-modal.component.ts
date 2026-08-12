import { Component, EventEmitter, Input, OnInit, Output, Inject, ChangeDetectorRef } from '@angular/core';
import { ApplicationType } from '@enums/agent-center.enum';
import { I18nNamespace } from '@i18n';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { from, map } from 'rxjs';
import { PromptService } from '@services/prompt.service';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzModalModule } from 'ng-zorro-antd/modal';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { I18NextModule } from 'angular-i18next';
import { inject } from '@angular/core';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzDrawerRef, NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';
@Component({
  selector: 'meta-export-modal',
  templateUrl: './export-half-modal.component.html',
  styleUrls: ['./export-half-modal.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    I18NextModule,
    NzFormModule,
    NzRadioModule,
    NzButtonModule,
    NzModalModule,
    NzSpaceModule,
    NzTableModule,
    NzInputModule,
    NzSelectModule,
    NzCheckboxModule,
    NzToolTipModule,
    NzIconModule,
    NzPaginationModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ExportHalfModalComponent implements OnInit {
  readonly modalRef = inject(NzDrawerRef);
  @Input() exportType = ApplicationType.SINGLE_AGENT;
  @Input() exportTypeOptions = [
    {
      id: ApplicationType.SINGLE_AGENT,
      text: this.i18n.transform('export_single_agent_app'),
      colName: this.i18n.transform('single_agent_app'),
      desc: 'app_export_desc',
      rowKey: 'agent_id',
    },
    {
      id: ApplicationType.WORKFLOW,
      text: this.i18n.transform('export_workflow_app'),
      colName: this.i18n.transform('workflow_app'),
      desc: 'workflow_export_desc',
      rowKey: 'workflow_id',
    },
    {
      id: ApplicationType.MULTI_AGENT,
      text: this.i18n.transform('export_multi_agent_app'),
      rowKey: 'agent_id',
      desc: 'multi_agent_export_desc',
      colName: this.i18n.transform('multi_agent_app'),
    },
  ];

  @Output() confirm = new EventEmitter();

  public get selectedType() {
    return this.exportTypeOptions.find(item => item.id === this.exportType);
  }

  public apiList = {
    [ApplicationType.SINGLE_AGENT]: this.getAgentList,
    [ApplicationType.WORKFLOW]: this.getFlowList,
    [ApplicationType.PLUGIN]: this.getPluginList,
    [ApplicationType.MULTI_AGENT]: this.getAgentList,
    [ApplicationType.PROMPT]: this.getPromptList,
  };

  public listOfColumns: any[] = [];
  public listOfData: any[] = [];
  public total = 0;
  public loading = true;
  public pageSize = 10;
  public pageIndex = 1;
  public searchValue = '';

  isAllChecked = false;
  public selectedRows: any[] = [];
  public setOfCheckedId = new Set<any>();
  public checkedDataMap = new Map<any, any>();

  constructor(
    private i18n: I18NextEagerPipe,
    private service: AppAgentRepoService,
    private appflowRepoServe: AppFlowRepoService,
    private appPluginRepoServe: AppPluginRepoService,
    private promptService: PromptService,
    private cdr: ChangeDetectorRef,
    @Inject(NZ_DRAWER_DATA) public nzData: any
  ) {}

  ngOnInit(): void {
    this.initColumns();
    this.loadData();
  }

  public initColumns(): void {
    this.listOfColumns = this.getColumns();
  }

  private getColumns(): any[] {
    if (this.exportType === ApplicationType.PLUGIN) {
      return [
        {
          title: this.i18n.transform('plugin'),
          dataIndex: 'plugin_chinese_name',
          width: 200,
        },
        {
          title: this.i18n.transform('description'),
          dataIndex: 'plugin_desc',
        },
      ];
    } else if (this.exportType === ApplicationType.PROMPT) {
      return [
        {
          title: this.i18n.transform('prompt'),
          dataIndex: 'template_name',
          width: 200,
        },
        {
          title: this.i18n.transform('description'),
          dataIndex: 'description',
        },
      ];
    }
    return [
      {
        title: this.selectedType.colName,
        dataIndex: 'name',
        width: 200,
      },
      {
        title: this.i18n.transform('description'),
        dataIndex: 'description',
      },
      {
        title: this.i18n.transform('status'),
        dataIndex: 'status',
        width: 250,
      },
    ];
  }

  private getAgentList(queryParams, offset, limit) {
    return from(
      this.service.getAgentList(
        {
          ...queryParams,
          type: this.exportType,
        },
        offset,
        limit
      )
    ).pipe(
      map(res => {
        const { agent_list, count } = res;
        return {
          data: agent_list || [],
          total: count || 0,
        };
      })
    );
  }

  private getFlowList(queryParams, offset, limit) {
    return from(
      this.appflowRepoServe.getFlows({
        ...queryParams,
        offset,
        limit,
      })
    ).pipe(
      map(res => {
        const { workflow_list, count } = res;
        return {
          data: workflow_list || [],
          total: count || 0,
        };
      })
    );
  }

  private getPluginList(queryParams, offset, limit) {
    return from(
      this.appPluginRepoServe.getPluginList({
        call_mode: 'api',
        entry_point: 'partial',
        ...queryParams,
        offset,
        limit,
      })
    ).pipe(
      map(res => {
        const { plugin_list, count } = res;
        return {
          data: plugin_list || [],
          total: count || 0,
        };
      })
    );
  }

  public getPromptList(queryParams, offset, limit) {
    return from(
      this.promptService.getPromptTemplateList({
        ...queryParams,
        offset,
        limit,
      })
    ).pipe(
      map(res => {
        const { data, count } = res;
        return {
          data: data || [],
          total: count || 0,
        };
      })
    );
  }

  public loadData(): void {
    this.loading = true;
    const offset = (this.pageIndex - 1) * this.pageSize;
    const queryParams: { [key: string]: string } = {};
    if (this.searchValue) {
      if (this.exportType === ApplicationType.PLUGIN) {
        queryParams.tool_chinese_name = this.searchValue;
      } else if (this.exportType === ApplicationType.PROMPT) {
        queryParams.template_name = this.searchValue;
      } else {
        queryParams.name = this.searchValue;
      }
    }
    this.apiList[this.exportType].call(this, queryParams, offset, this.pageSize).subscribe({
      next: res => {
        this.listOfData = res.data;
        this.total = res.total;
        this.loading = false;
        this.refreshCheckedStatus();
        this.cdr.detectChanges();
      },
      error: () => {
        this.listOfData = [];
        this.total = 0;
        this.loading = false;
        this.cdr.detectChanges();
      },
    });
  }

  public onSearch(): void {
    this.pageIndex = 1;
    this.clearSelection();
    this.loadData();
  }

  public onClear(): void {
    this.searchValue = '';
    this.pageIndex = 1;
    this.clearSelection();
    this.loadData();
  }

  public onRefresh(): void {
    this.searchValue = '';
    this.pageIndex = 1;
    this.clearSelection();
    this.loadData();
  }

  public onPageIndexChange(index: number): void {
    this.pageIndex = index;
    this.loadData();
  }

  public onPageSizeChange(size: number): void {
    this.pageSize = size;
    this.pageIndex = 1;
    this.loadData();
  }

  public onQueryParamsChange(params: any): void {
    if (params.pageIndex) {
      this.pageIndex = params.pageIndex;
    }
    if (params.pageSize) {
      this.pageSize = params.pageSize;
    }
    this.loadData();
  }

  public clearSelection(): void {
    this.setOfCheckedId.clear();
    this.checkedDataMap.clear();
    this.selectedRows = [];
    this.isAllChecked = false;
  }

  public updateCheckedSet(id: any, data: any, checked: boolean): void {
    if (checked) {
      this.setOfCheckedId.add(id);
      if (data) {
        this.checkedDataMap.set(id, data);
      }
    } else {
      this.setOfCheckedId.delete(id);
      this.checkedDataMap.delete(id);
    }
    this.selectedRows = Array.from(this.checkedDataMap.values());
  }

  public onItemChecked(id: any, data: any, checked: boolean): void {
    this.updateCheckedSet(id, data, checked);
    this.refreshCheckedStatus();
  }

  public onAllChecked(checked: boolean): void {
    this.listOfData.forEach(item => this.updateCheckedSet(item[this.selectedType.rowKey], item, checked));
    this.refreshCheckedStatus();
  }

  public refreshCheckedStatus(): void {
    this.isAllChecked = this.listOfData.length > 0 && this.listOfData.every(item => this.setOfCheckedId.has(item[this.selectedType.rowKey]));
  }

  public dismiss() {
    this.modalRef.close();
  }

  public handleExport() {
    if (this.nzData.confirm && typeof this.nzData.confirm === 'function') {
      this.nzData.confirm({
        type: this.exportType,
        rows: this.selectedRows,
      });
    }
    this.confirm.emit({
      type: this.exportType,
      rows: this.selectedRows,
    });
    this.modalRef.close();
  }
  public close() {
    this.modalRef.close();
  }
}
