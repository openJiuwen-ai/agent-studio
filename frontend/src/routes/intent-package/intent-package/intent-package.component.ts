import {
  Component,
  OnInit,
  ViewEncapsulation,
  OnDestroy
} from '@angular/core';
import { Subscription } from 'rxjs';
import { I18nNamespace } from '@i18n';
import { Router } from '@angular/router';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { IntentPackageService } from '../intent-package.service';
import { ImportPackageModalComponent } from '../components/import-intent-package/import-package-modal.component';
import { ExportPackageModalComponent } from '../components/export-intent-package/export-package-modal.component';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { FormateTimePipe } from 'src/pipes/formate-time.pipe';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { PipesModule } from 'src/pipes/pipes.module';
import { FormsModule } from '@angular/forms';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzDrawerModule, NzDrawerService } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'intent-package',
  templateUrl: './intent-package.component.html',
  styleUrls: ['./intent-package.component.less'],
  standalone: true,
  imports: [
    COMMON_MODULES,
    MODULES,
    NewCommonNoDataWithBtnComponent,
    NoDataGuideComponentComponent,
    PipesModule,
    FormsModule,
    NzButtonModule,
    NzInputModule,
    NzTableModule,
    NzPaginationModule,
    NzDropDownModule,
    NzIconModule,
    NzModalModule,
    NzDrawerModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    },
    FormateTimePipe,
    NzModalService,
    NzMessageService,
    NzDrawerService
  ],
  encapsulation: ViewEncapsulation.None,
})
export class IntentPackageComponent implements OnInit, OnDestroy {
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  private subscribeBtnStatusSubscription: Subscription;

  searchValue = '';
  srcData = {
    data: [],
    state: undefined,
  };
  displayedData = [];

  readonly listColumns: Array<any> = [
    { title: this.i18n.transform('intent_package_name') },
    { title: this.i18n.transform('intent_num') },
    { title: this.i18n.transform('creator') },
    { title: this.i18n.transform('create_time') },
    {
      title: this.i18n.transform('operation'),
      width: '120px',
    },
  ];
  currentPage = 1;
  totalNumber = 0;
  readonly pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  loading = false;
  public isShowGuide = true;
  public isShowNoDataGuide = false;
  public isFirstLoading = true;

  constructor(
    private intentPackageService: IntentPackageService,
    private router: Router,
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private commonService: CommonService,
    private readonly http: HttpService,
    private nzModal: NzModalService,
    private nzMessageService: NzMessageService,
    private nzDrawerService: NzDrawerService
  ) {}

  ngOnInit() {
    this.searchList();
  }

  ngOnDestroy(): void {
    if (this.subscribeBtnStatusSubscription) {
      this.subscribeBtnStatusSubscription.unsubscribe();
    }
  }

  trackByFn(index: number, item: any) {
    return item.id;
  }

  get searchNameIsEmpty(): boolean {
    return this.searchValue.length === 0;
  }

  listAction($event: any, row: any) {
    if ($event.key === 'edit') {
      if (this.subscribeBtnStatus) {
        this.router.navigate(['/home/intent-package/intent-detail'], {
          queryParams: {
            id: row.intent_id || '',
          },
        });
      }
    } else if ($event.key === 'delete') {
      if (this.subscribeBtnStatus) {
        this.nzModal.confirm({
          nzTitle: this.i18n.transform('delete_package_title'),
          nzContent: this.i18n.transform('delete_package_tips'),
          nzOkText: this.i18n.transform('determined'),
          nzOkType: 'primary',
          nzOnOk: () => {
            return this.intentPackageService
              .deleteIntentPackage(row.intent_id)
              .then(() => {
                this.searchList();
                this.nzMessageService.success(
                  this.i18n.transform('deleted_successfully'),
                  { nzDuration: 3000 }
                );
              });
          },
        });
      }
    }
  }

  /** 导出意图包 */
  public exportTool() {
    this.nzDrawerService.create({
      nzContent: ExportPackageModalComponent,
      nzWidth: '700px',
      nzPlacement: 'right'
    });
  }

  /** 导入意图包 */
  public importTool() {
    this.nzModal.create({
      nzContent: ImportPackageModalComponent,
      nzClassName: 'import-intent-modal',
      nzFooter: null,
      nzWidth: '600px',
      nzData: {
        outputs: {
          refreshTable: () => {
            this.searchList();
          },
        },
      }
    });
  }

  public toCreate() {
    this.router.navigate(['/home/intent-package/intent-detail'], {
      queryParams: {
        previousUrl: 'intent-manage',
      },
    });
  }

  searchList() {
    this.currentPage = 1;
    this.getIntentManagementListData();
  }

  async getIntentManagementListData(): Promise<void> {
    try {
      this.loading = true;
      const params = {
        limit: this.pageSize.size,
        offset: (this.currentPage - 1) * this.pageSize.size,
        ...(this.searchValue && { name: this.searchValue }),
      };
      const result = await this.intentPackageService.getIntentGroupList(params);
      this.srcData.data = result.intents || [];
      this.totalNumber = result.count;
    } finally {
      this.loading = false;
      this.isShowNoDataGuide = !this.srcData.data?.length && !this.loading && this.searchNameIsEmpty;
      this.isFirstLoading = false;
    }
  }

  toDetail(row) {
    this.router.navigate(['/home/intent-package/intent-detail'], {
      queryParams: {
        id: row.intent_id || '',
      },
    });
  }

  handleClickClearSearch() {
    this.searchValue = '';
    this.searchList();
  }
}
