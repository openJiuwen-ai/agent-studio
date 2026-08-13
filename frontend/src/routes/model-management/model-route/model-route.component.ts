import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonUtils } from '../../../utils/common.util';
import { DeleteRefsService } from '@shared/services/delete-refs.service';
import { AuthModalComponent } from '@routes/model-management/components/auth-modal/auth-modal.component';
import { DeleteModalComponent } from '@routes/model-management/delete-modal/delete-modal.component';
import { ModelRouterStrategiesService } from '@services/repositories/model-router-strategies';
import { getNewServiceKeyList } from '../router-policy-detail/router-common';
import { Router } from '@angular/router';
import { NewCommonNoDataWithBtnComponent } from "@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component";
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
export interface MachineState {
  state: string;
}

@Component({
  selector: 'model-route',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    NewCommonNoDataWithBtnComponent,
    NoDataGuideComponentComponent,
    NzButtonModule,
    NzInputModule,
    NzPaginationModule,
    NzTagModule,
    NzTableModule,
    NzDropDownModule,
    NzIconModule,
    NzModalModule
  ],
  templateUrl: './model-route.component.html',
  styleUrls: ['./model-route.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS, I18nNamespace.GUIDE, I18nNamespace.AGENT_CENTER,],
    },
    DeleteRefsService,
    NzModalService
  ],
})
export class ModelRouteComponent implements OnInit {
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  displayedData: Array<any> = [];
  columns: Array<any> = [
    { title: this.i18n.transform('policy_name') },
    { title: this.i18n.transform('policy_des') },
    { title: this.i18n.transform('AI_model') },
    { title: this.i18n.transform('service_key') },
    { title: this.i18n.transform('create_time') },
    { title: this.i18n.transform('update_time') },
    { title: this.i18n.transform('action'), width: '180px', fixed: 'right' },
  ];

  srcData: any = {
    data: [],
    state: { searched: false, sorted: false, paginated: true },
  };

  public searchName: string = '';

  public loading = false;
  public currentPage = 1;
  public totalNumber = 0;
  public activeName = 'PLATFORM';

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  public btnTitle = this.i18n.transform(this.subscribeBtnStatus?'create_route_policy':'');
  public isShowGuide = true;
  public isShowNoDataGuide = false;
  public isFirstLoading = true;
  public dataToItems = this.dataToItemsList();

  get getHeight() {
    if (this.isShowNoDataGuide) {
      return 'calc(100vh - 232px)';
    } else {
      return this.isShowGuide? 'calc(100vh - 496px)' : 'calc(100vh - 290px)';
    }
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private router: Router,
    private nzModalService: NzModalService,
    private modelRouterStrategiesService: ModelRouterStrategiesService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    protected cdr: ChangeDetectorRef,
    private message: NzMessageService,
  ) {
    this.http.getCurrentUserResourceStatus().subscribe(res=>{
      this.dataToItems = this.dataToItemsList();
      this.cdr.markForCheck();
    })
  }

  get gteSubscribeBtnStatus(){
    return !this.subscribeBtnStatus;
  }

  ngOnInit() {
    this.getModelRouterStrategiesListFn();
  }

  dataToItemsList() {
    return [
      {
        id: 'test',
        label: this.i18n.transform('model_test'),
        disabled: this.gteSubscribeBtnStatus,
        icon: cdnAssetUrl('assets/images/model/auto-setting.svg'),
      },
      {
        id: 'edit',
        label: this.i18n.transform('edit'),
        disabled: this.gteSubscribeBtnStatus,
        icon: ('assets/images/model/edit.svg'),
      },
      {
        id: 'delete',
        label: this.i18n.transform('delete'),
        disabled: this.gteSubscribeBtnStatus,
        icon: cdnAssetUrl('assets/images/model/delete.svg'),
      },
    ];
  }

  public onSelect(item: any, row: any) {
    if (item.disabled) return;

    if (item.id === 'test') {
      this.goModelTest(row);
    } else if (item.id === 'edit') {
      this.addRoutePolicy(row);
    } else if (item.id === 'delete') {
      this.deleteModal(row);
    }
  }

  public onSearchContentChange(): void {
    this.currentPage = 1;
    this.getModelRouterStrategiesListFn();
  }

  public onClearSearchContentChange(): void {
    this.searchName = ''
    this.onSearchContentChange();
  }

  goModelTest(row) {
    this.router.navigate(['/home/development-configuration'], {
      queryParams: {
        id: row.id,
        modelType: 'LLM',
        activeName:  'ROUTE-POLICY',
        previousUrl: 'model-test',
      },
    });
  }

  goStrategyDetail(row) {
    this.router.navigate(['/home/model/route-policy-detail'], {
      queryParams: {
        id: row.id,
      },
    });
  }

  validateUserInput(userInput: string): boolean {
    const regex = /^[\u4e00-\u9fa5a-zA-Z0-9._-]{1,64}$/;
    return regex.test(userInput);
  }

  getModelRouterStrategiesListFn(isDelete = false) {
    this.loading = true;
    if (isDelete && this.currentPage > 1) {
      if (Math.ceil((this.totalNumber - 1) / this.pageSize?.size) < this.currentPage) {
        this.currentPage -= 1;
      }
    }

    const param:any = {
      page_num: this.currentPage,
      page_size: this.pageSize.size,
    };
    if (this.searchName) {
      if (!this.validateUserInput(this.searchName)) {
        this.message.warning(this.i18n.transform('support_chars'));
        this.loading = false;
        return
      }
      param.query= this.searchName;
    }

    this.modelRouterStrategiesService
      .getModelRouterStrategiesList(param)
      .then((res: any) => {
        let result = res?.data;
        for (const item of result) {
          item.created_date = CommonUtils.getDateToString(item.created_date);
          item.last_updated_date = CommonUtils.getDateToString(
            item.last_updated_date,
          );
          item.strategy_description = item.strategy_description || '-';
          const _service_key_list = getNewServiceKeyList(item.service_list);
          item.service_key_list = _service_key_list.join(' | ') || '-';
        }
        this.srcData.data = result;
        this.totalNumber = res.total;
      })
      .finally(() => {
        this.loading = false;
        this.isShowNoDataGuide = !this.srcData.data?.length && !this.loading && !this.searchName;
        this.isFirstLoading = false;
      });
  }

  public authModal(item) {
    const modal = this.nzModalService.create({
      nzContent: AuthModalComponent,
      nzWidth: '500px',
      nzFooter: null,
      nzData: {
        context: {
          id: item.id,
          provider_info: item,
        },
        close: () => {
          this.getModelRouterStrategiesListFn();
          modal.close();
        },
      } as any
    });
  }

  public deleteModal(item) {
    const modal = this.nzModalService.create({
      nzContent: DeleteModalComponent,
      nzWidth: '500px',
      nzFooter: null,
      nzData: {
        context: {
          id: item.id,
          title: this.i18n.transform('delete_route_policy'),
          tip: this.i18n.transform('confirm_delete_route_policy',{strategy_name: item.strategy_name}),
          fnName: 'deleteModelRouterStrategies',
          close: () => {
            this.getModelRouterStrategiesListFn(true);
            this.message.success(
              this.i18n.transform('del_route_policy_success'),
            );
            modal.close();
          },
        },
      } as any
    });
  }

  addRoutePolicy(data?: any) {
    if (data) {
      this.router.navigate(['/home/model/create-route-policy'], {
        queryParams: {
          id: data.id,
        },
      });
    } else {
      this.router.navigate(['/home/model/create-route-policy']);
    }
  }

  public freshBtn() {
    this.getModelRouterStrategiesListFn();
  }
}
