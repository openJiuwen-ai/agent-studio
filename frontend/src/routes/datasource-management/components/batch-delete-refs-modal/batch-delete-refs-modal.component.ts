import {Component, EventEmitter, Input, Output} from '@angular/core';
import {MODULES} from '@shared/modules';
import {I18NEXT_NAMESPACE, I18NextEagerPipe} from 'angular-i18next';
import {I18nNamespace} from '@i18n';
import {IBatchMappings, IResourceList,} from '@routes/agent-center/types/common.types';
import {DataSourceManagementRepoService} from '@services/repositories/datasource-management-repo.service';
import {MessageComponent} from '@shared/services/cfdata.service';

@Component({
  selector: 'meta-batch-delete-refs-modal',
  templateUrl: './batch-delete-refs-modal.component.html',
  styleUrls: ['./batch-delete-refs-modal.component.scss'],
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class BatchDeleteRefsModalComponent {
  @Input() title: string = '';

  @Input() alertText: string = '';

  @Input() secondConfirmConfig: any;

  @Input() resource_ids: IResourceList[];

  @Output() confirm = new EventEmitter();

  public displayedData: Array<any> = [];

  public columns: Array<any> = [
    {
      title: this.i18n.transform('data_source_name'),
    },
    {
      title: this.i18n.transform('type'),
    },
    {
      title: this.i18n.transform('cited_count'),
    },
  ];

  public srcData: any = {
    data: [],
    state: {
      searched: false,
      sorted: false,
      paginated: true,
    },
  };

  public totalNumber: number = 0;

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  public currentPage: number = 0;

  public confirmMode: any = "simple";

  // 接收二次确认组件的校验方法
  private secondConfirmCheck: any;

  constructor(
    private dataSourceRepoServe: DataSourceManagementRepoService,
    private i18n: I18NextEagerPipe,
  ) {}

  ngOnInit() {
    this.dataSourceRepoServe
      .getBatchRefList({
        limit: this.resource_ids.length,
        offset: 0,
        resource_ids: this.resource_ids.map((item) => item.resource_id),
        resource_type :"sql"
      })
      .then((res: IBatchMappings) => {
        const { resource_list } = res;
        this.srcData.data = this.resource_ids.map((i) => {
          const match = resource_list.find(
            (r) => r.resource_id === i.resource_id,
          );
          return {
            ...i,
            reference_number: match
              ? match.reference_number
              : i.reference_number,
          };
        });
        this.totalNumber = this.resource_ids.length;
      });
  }

  get isRefsEmpty() {
    return this.srcData?.data?.some((i) => i.reference_number !== 0) ?? false;
  }

  public close() {}

  public dismiss() {}

  public onConfirm() {
    if (this.secondConfirmCheck()) {
      this.close();
      const ids = this.resource_ids.map((item) => item.resource_id);
      this.dataSourceRepoServe.batchDeleteDatasource(ids).then(() => {
        MessageComponent.showSuccess(
          this.i18n.transform('successfully_batch_delete_datasource'),
        );
        this.confirm.emit();
      });
    }
  }

  /**
   * 二次确认组件初始化完成后，对外提供的数据和api
   * @param $event 组件提供的数据和api
   */
  public initComplateFn(event: any): void {
    this.secondConfirmCheck = event.api.check;
  }
}
