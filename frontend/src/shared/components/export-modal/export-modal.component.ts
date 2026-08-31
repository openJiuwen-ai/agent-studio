import {
  OnInit,
  Component,
  Input,
  Inject,
  Output,
  EventEmitter, ChangeDetectorRef
} from "@angular/core";
import { ApplicationType } from "@enums/agent-center.enum";
import { I18nNamespace } from "@i18n";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { AppPluginRepoService } from "@services/agent-center/app-plugin-repo.service";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { from, map } from "rxjs";
import { CommonModule } from "@angular/common";
import { FormsModule } from "@angular/forms";
import { I18NextModule } from "angular-i18next";
import { MODULES } from "@shared/modules";
import { NzModalRef, NZ_MODAL_DATA } from "ng-zorro-antd/modal";

@Component({
  selector: "meta-export-modal",
  templateUrl: "./export-modal.component.html",
  styleUrls: ["./export-modal.component.less"],
  standalone: true,
  imports: [
    MODULES,
    CommonModule,
    FormsModule,
    I18NextModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER]
    }
  ]
})
export class ExportModalComponent implements OnInit {
  @Input() exportType;
  @Input() exportTypeOptions;

  @Output() confirm = new EventEmitter();

  public get selectedType() {
    return this.modalData.exportTypeOptions.find((item) => item.id === this.exportType);
  }

  public listOfColumns: any[] = [];
  public listOfData: any[] = [];
  public total = 0;
  public loading = true;
  public pageSize = 10;
  public pageIndex = 1;
  public searchValue = "";

  public selectedRows: any[] = [];
  public setOfCheckedId = new Set<any>();
  public selectedRowsMap = new Map<any, any>();

  public get allChecked(): boolean {
    return this.listOfData.length > 0 && this.listOfData.every((item) =>
      this.setOfCheckedId.has(item[this.selectedType.rowKey])
    );
  }

  public apiList = {
    [ApplicationType.SINGLE_AGENT]: this.getAgentList,
    [ApplicationType.WORKFLOW]: this.getFlowList,
    [ApplicationType.PLUGIN]: this.getPluginList,
    [ApplicationType.MULTI_AGENT]: this.getAgentList
  };

  constructor(
    private i18n: I18NextEagerPipe,
    private service: AppAgentRepoService,
    private appflowRepoServe: AppFlowRepoService,
    private appPluginRepoServe: AppPluginRepoService,
    private modalRef: NzModalRef,
    @Inject(NZ_MODAL_DATA) private modalData: any,
    private cdr: ChangeDetectorRef,
  ) {
    this.exportType = modalData.exportType || ApplicationType.SINGLE_AGENT;
    this.exportTypeOptions = modalData.exportTypeOptions || [{
      id: ApplicationType.SINGLE_AGENT,
      text: this.i18n.transform("export_single_agent_app"),
      desc: "export_modal_top_tip",
      colName: this.i18n.transform("agent_name"),
      rowKey: "agent_id"
    },
      {
        id: ApplicationType.WORKFLOW,
        text: this.i18n.transform("export_workflow_app"),
        desc: "export_modal_top_tip",
        colName: this.i18n.transform("workflow_app"),
        rowKey: "workflow_id"
      },
      {
        id: ApplicationType.MULTI_AGENT,
        text: this.i18n.transform("export_multi_agent_app"),
        desc: "export_modal_top_tip",
        colName: this.i18n.transform("multi_agent_app"),
        rowKey: "agent_id"
      }
    ];
  }

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
          title: this.i18n.transform("plugin"),
          dataIndex: "plugin_chinese_name",
          width: 200
        },
        {
          title: this.i18n.transform("description"),
          dataIndex: "plugin_desc"
        }
      ];
    }
    return [
      {
        title: this.selectedType.colName,
        dataIndex: "name",
        width: 200
      },
      {
        title: this.i18n.transform("description"),
        dataIndex: "description"
      },
      {
        title: this.i18n.transform("homecomponent_1224"),
        dataIndex: "status",
        width: 120
      }
    ];
  }

  public handleTypeChange(): void {
    this.pageIndex = 1;
    this.searchValue = "";
    this.initColumns();
    this.loadData();
  }

  private getAgentList(queryParams, offset, limit) {
    return from(
      this.service.getAgentList({ ...queryParams, type: this.exportType },
        offset,
        limit
      )
    ).pipe(map((res) => {
        const { agent_list, count } = res;
        return {
          data: agent_list || [],
          total: count || 0
        };
      })
    );
  }

  private getFlowList(queryParams, offset, limit) {
    return from(
      this.appflowRepoServe.getFlows({
        ...queryParams,
        offset,
        limit
      })
    ).pipe(map((res) => {
        const { workflow_list, count } = res;
        return {
          data: workflow_list || [],
          total: count || 0
        };
      })
    );
  }

  private getPluginList(queryParams, offset, limit) {
    return from(this.appPluginRepoServe.getPluginList({
        ...queryParams,
        offset,
        limit
      })
    ).pipe(
      map((res) => {
        const { plugin_list, count } = res;
        return {
          data: plugin_list || [],
          total: count || 0
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
      } else {
        queryParams.name = this.searchValue;
      }
    }
    this.apiList[this.exportType].call(this, queryParams, offset, this.pageSize)
      .subscribe({
        next: (res) => {
          const published = this.i18n.transform('submitted');
          const unPublished = this.i18n.transform('not_submitted');
          this.listOfData = res.data.map(item => {
            if ([ApplicationType.SINGLE_AGENT, ApplicationType.MULTI_AGENT].includes(this.exportType)) {
              item.status = item.status === 'published' ? published : unPublished;
            } else {
              item.status = item.status === 1 ? published : unPublished;
            }
            return item;
          });
          this.total = res.total;
          this.loading = false;
          this.cdr.detectChanges();
        },
        error: () => {
          this.listOfData = [];
          this.total = 0;
          this.loading = false;
        }
      });
  }

  public onSearch(): void {
    this.pageIndex = 1;
    this.loadData();
  }

  public onClear(): void {
    this.searchValue = '';
    this.pageIndex = 1;
    this.loadData();
  }

  public onRefresh(): void {
    this.searchValue = '';
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

  public updateCheckedSet(id: any, checked: boolean): void {
    if (checked) {
      this.setOfCheckedId.add(id);
    } else {
      this.setOfCheckedId.delete(id);
    }
  }

  public onItemChecked(id: any, checked: boolean): void {
    this.updateCheckedSet(id, checked);
    const item = this.listOfData.find((d) => d[this.selectedType.rowKey] === id);
    if (checked && item) {
      this.selectedRowsMap.set(id, item);
    } else {
      this.selectedRowsMap.delete(id);
    }
    this.selectedRows = this.listOfData.filter((item) =>
      this.setOfCheckedId.has(item[this.selectedType.rowKey])
    );
  }

  public onAllChecked(checked: boolean): void {
    this.listOfData.forEach((item) => {
      const id = item[this.selectedType.rowKey];
      this.updateCheckedSet(id, checked);
      if (checked) {
        this.selectedRowsMap.set(id, item);
      } else {
        this.selectedRowsMap.delete(id);
      }
    });
    this.selectedRows = checked ? [...this.listOfData] : [];
  }

  public handleExport(): void {
    this.confirm.emit({
      type: this.exportType,
      rows: Array.from(this.selectedRowsMap.values())
    });
  }

  public dismiss(): void {
    this.modalRef.close();
  }

  public close(): void {
    this.modalRef.close();
  }
}
