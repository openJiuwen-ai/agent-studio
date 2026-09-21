import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { DataSourceManagementRepoService } from '@services/repositories/datasource-management-repo.service';
import { CommonService } from '@services/common.service';
import { FormateTimePipe } from 'src/pipes/formate-time.pipe';
import {
  NewCommonNoDataWithBtnComponent
} from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { PipesModule } from '../../pipes/pipes.module';
import {
  EditableDatasourceHalfmodalComponent
} from '@routes/datasource-management/components/editable-datasource-halfmodal/editable-datasource-halfmodal.component';
import { HttpService } from '@services/http.service';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
import { IDatasourceList } from '@routes/agent-center/types/datasource.types';

@Component({
  selector: 'datasource-management',
  templateUrl: './datasource-management.component.html',
  styleUrls: ['./datasource-management.component.scss'],
  standalone: true,
  imports: [MODULES, NewCommonNoDataWithBtnComponent, PipesModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    },
    FormateTimePipe,
    NzModalService,
    NzDrawerService,
    NzMessageService
  ],
  encapsulation: ViewEncapsulation.None,
})
export class DatasourceManagementComponent implements OnInit {
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  is_white_list = false;

  constructor(
    private i18n: I18NextEagerPipe,
    private dataSourceRepoServe: DataSourceManagementRepoService,
    private nzDrawer: NzDrawerService,
    private nzModal: NzModalService,
    private nzMessage: NzMessageService,
    private commonService: CommonService,
    private readonly http: HttpService,
  ) {
    this.http.getResourceWhiteList().subscribe(res => {
      this.is_white_list = res;
    });
  }

  ngOnInit() {
    this.getDatasourceListData();
  }

  loading = false;
  srcData: { data: any[] } = {
    data: [],
  };
  checkedList: any[] = [];
  allChecked = false;
  indeterminate = false;

  listColumns: Array<{ title: string; width?: string; fixed?: string }> = [
    { title: '' },
    { title: this.i18n.transform('data_source_name') },
    { title: this.i18n.transform('database_type') },
    { title: this.i18n.transform('description') },
    { title: this.i18n.transform('operator1') },
    { title: this.i18n.transform('operation_time') },
    {
      title: this.i18n.transform('operation'),
      fixed: 'right',
      width: '120px',
    },
  ];

  public trackByFn(index: number) {
    return index;
  }

  updateCheckStatus(): void {
    this.allChecked = this.srcData.data.length > 0 && this.srcData.data.every(item => this.isChecked(item));
    this.indeterminate = this.checkedList.length > 0 && !this.allChecked;
  }

  isChecked(row: any): boolean {
    return this.checkedList.includes(row);
  }

  onItemChecked(row: any, checked: boolean): void {
    if (checked) {
      if (!this.checkedList.includes(row)) {
        this.checkedList.push(row);
      }
    } else {
      this.checkedList = this.checkedList.filter(i => i !== row);
    }
    this.updateCheckStatus();
  }

  onAllChecked(checked: boolean): void {
    if (checked) {
      this.srcData.data.forEach(item => {
        if (!this.checkedList.includes(item)) {
          this.checkedList.push(item);
        }
      });
    } else {
      this.checkedList = this.checkedList.filter(i => !this.srcData.data.includes(i));
    }
    this.updateCheckStatus();
  }

  listAction(key: string, row: any) {
    if (key === 'edit') {
      this.openHalfModel(row.id);
    } else if (key === 'delete') {
      this.deleteDatasource(row.id, row.name);
    }
  }

  searchValue = '';
  get searchNameIsEmpty(): boolean {
    return this.searchValue.length === 0;
  }

  currentPage = 1;
  pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  totalNumber = 0;

  pageIndexChange(index: number) {
    this.currentPage = index;
    this.getDatasourceListData();
  }

  pageSizeChange(size: number) {
    this.pageSize.size = size;
    this.currentPage = 1;
    this.getDatasourceListData();
  }

  getDatasourceListData() {
    this.loading = true;
    const params: any = {
      page: this.currentPage,
      pageSize: this.pageSize.size,
    };
    if (this.searchValue.trim()) {
      params.name = this.searchValue.trim();
    }
    this.dataSourceRepoServe
      .getDatasourceList(params)
      .then((res: IDatasourceList) => {
        this.srcData.data = res.datasources || [];
        this.totalNumber = res.total || 0;
        this.checkedList = [];
        this.updateCheckStatus();
      })
      .finally(() => {
        this.loading = false;
      });
  }

  private deleteDatasource(id: string, name: string): void {
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('delete_data_source'),
      nzContent: this.i18n.transform('delete_warn', { name }),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        this.dataSourceRepoServe.deleteDatasource(id).then(() => {
          this.nzMessage.success(this.i18n.transform('delete_success'));
          this.searchList();
        });
      },
    });
  }

  deleteData() {
    const ids = this.checkedList.map(item => item.id);
    this.nzModal.confirm({
      nzTitle: this.i18n.transform('batch_delete_data_source'),
      nzContent: this.i18n.transform('batch_delete_warn'),
      nzOkText: this.i18n.transform('ok'),
      nzOkType: 'primary',
      nzOkDanger: true,
      nzCancelText: this.i18n.transform('cancel'),
      nzOnOk: () => {
        this.dataSourceRepoServe.batchDeleteDatasource(ids).then(() => {
          this.nzMessage.success(
            this.i18n.transform('successfully_batch_delete_datasource'),
          );
          this.searchList();
        });
      },
    });
  }

  public createDatasource() {
    this.openHalfModel();
  }

  private openHalfModel(id?: string) {
    const drawerRef = this.nzDrawer.create({
      nzContent: EditableDatasourceHalfmodalComponent,
      nzWidth: '600px',
      nzMaskClosable: true,
      nzContentParams: {
        id: id || '',
        title: id
          ? this.i18n.transform('edit_data_source')
          : this.i18n.transform('connect_data_source'),
      },
    });
    drawerRef.afterClose.subscribe(() => {
      this.getDatasourceListData();
    });
  }

  handleClickClearSearch() {
    this.searchValue = '';
    this.searchList();
  }

  searchList() {
    this.currentPage = 1;
    this.getDatasourceListData();
  }
}
