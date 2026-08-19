import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { DeleteModalComponent } from './delete-modal/delete-modal.component';
import { AddPublisherComponent } from '@routes/model-management/components/add-publisher/add-publisher.component';
import { ModelImportModalComponent } from '@routes/model-management/components/import-modal/import-modal.component';
import { CommonUtils } from '../../utils/common.util';
import { DeleteRefsService } from '@shared/services/delete-refs.service';
import { AuthModalComponent } from '@routes/model-management/components/auth-modal/auth-modal.component';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { formatTime } from 'src/utils/commonFn';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerModule, NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
@Component({
  selector: 'meta-model-management',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    MonacoEditorModule,
    NoDataGuideComponentComponent,
    NzButtonModule,
    NzTagModule,
    NzInputModule,
    NzPaginationModule,
    NzIconModule,
    NzSpinModule,
    NzTypographyModule,
    NzEmptyModule,
    NzModalModule,
    NzDrawerModule,
  ],
  templateUrl: './model-management.component.html',
  styleUrls: ['./model-management.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS, I18nNamespace.GUIDE, I18nNamespace.AGENT_CENTER],
    },
    DeleteRefsService,
    NzModalService,
    NzDrawerService,
    NzMessageService,
  ],
})
export class ModalManagementComponent implements OnInit, OnDestroy {
  @Input() isFromDevelopSpace = false;

  public iconNoneEmpty = cdnAssetUrl('assets/model/default_model.svg');
  public searchName = '';
  public currentPage = 1;
  public totalNumber = 0;
  public pageSize = { options: [12, 24, 48, 64], size: 12 };

  public subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public isShowGuide = true;
  public isFirstLoading = true;
  public isShowNoDataGuide = false;
  public customLoading = false;
  public noDataTitle = this.i18n.transform('no_data');
  public changeUrl = cdnAssetUrl;
  protected readonly formatTime = formatTime;
  public customData: { data: any[]; state?: any } = { data: [] };

  constructor(
    private i18n: I18NextEagerPipe,
    private drawerService: NzDrawerService,
    private modalService: NzModalService,
    private messageService: NzMessageService,
    private modelManagementService: ModelManagementService,
    private router: Router,
    private commonService: CommonService,
    private http: HttpService,
    private sidebarVisibilityServ: SetSidebarVisibilityService
  ) {}

  ngOnInit() {
    if (this.isFromDevelopSpace) {
      this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    }
    this.getCustomData();
  }

  ngOnDestroy() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
  }

  private getAuthStatusTextKey(status: string): string {
    switch (status) {
      case 'part_available':
        return 'partial_access';
      case 'available':
        return 'auth_available';
      default:
        return 'auth_disable';
    }
  }

  private checkSearchValid(): boolean {
    if (this.searchName && !this.validateUserInput(this.searchName)) {
      this.messageService.warning(this.i18n.transform('support_char_types'));
      return false;
    }
    return true;
  }

  public getCustomData(isDelete = false) {
    if (!this.checkSearchValid()) {
      this.customLoading = false;
      return;
    }

    this.customLoading = true;
    if (isDelete) {
      const deleteCurrent = Math.ceil((this.totalNumber - 1) / this.pageSize.size);
      this.currentPage = deleteCurrent < this.currentPage ? Math.max(this.currentPage - 1, 1) : this.currentPage;
    }

    const param: any = {
      page_num: this.currentPage,
      page_size: this.pageSize.size,
      ...(this.searchName ? { query: this.searchName } : {}),
    };

    this.modelManagementService
      .getPublisherList(param, 'integration')
      .then(res => {
        const result = res.data || [];
        this.customData.data = result.map(item => {
          const textKey = this.getAuthStatusTextKey(item.auth_config_status);

          return {
            ...item,
            tagStatus: {
              type: item.auth_config_status === 'available' ? 'success' : 'warning',
              text: this.i18n.transform(textKey),
            },
            last_updated_date: CommonUtils.getDateToString(item.last_updated_date),
            created_date: CommonUtils.getDateToString(item.created_date),
            isHovering: false,
          };
        });
        this.totalNumber = res.total;
      })
      .finally(() => {
        this.customLoading = false;
        this.isFirstLoading = false;
        this.isShowNoDataGuide = !this.customData.data?.length && !this.searchName;
      });
  }

  public customOnSearch(): void {
    this.currentPage = 1;
    this.getCustomData();
  }

  public toDetail(row: any) {
    if (!this.checkSearchValid()) {
      return;
    }

    const param = {
      page_num: this.currentPage,
      page_size: this.pageSize.size,
      ...(this.searchName ? { query: this.searchName } : {}),
    };

    const queryParams: any = {
      activeName: 'CUSTOM',
      provider_id: row.id,
      queryFilter: JSON.stringify(param),
    };

    if (this.isFromDevelopSpace) {
      queryParams.from = 'develop-space';
    }

    this.router.navigate(['/home/model/management-detail'], {
      queryParams,
      replaceUrl: true,
    });
  }

  onCardHover(item: any): void {
    if (item) item.isHovering = true;
  }

  onCardLeave(item: any): void {
    if (item) item.isHovering = false;
  }

  onHoverButtonClick(action: 'auth' | 'edit' | 'delete' | 'export', item: any, event: Event): void {
    event.stopPropagation();
    if (action !== 'export' && (!this.subscribeBtnStatus || item.id?.startsWith('cdi-'))) {
      return;
    }
    switch (action) {
      case 'auth':
        if (item.auth_configs?.[0]?.auth_type !== 'NO_AUTH') {
          this.authModal(item);
        }
        break;
      case 'edit':
        this.openPublisherHalfModel(item);
        break;
      case 'delete':
        this.deleteModal(item);
        break;
      case 'export':
        this.exportByProvider(item);
        break;
      default:
        break;
    }
    item.isHovering = false;
  }

  /** 供应商卡片导出（供应商+模型）：导出该供应商+其下全部模型。 */
  public exportByProvider(item: any): void {
    if (!this.subscribeBtnStatus || item.id?.startsWith('cdi-')) {
      return;
    }
    this.modelManagementService
      .exportModelsByProvider(item.id)
      .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'provider-models.jsonl';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        this.messageService.success(this.i18n.transform('export_model_success'));
      })
      .catch(() => {
        this.messageService.error(this.i18n.transform('export_model_failed'));
      });
  }

  /** 列表页导入（供应商+模型）：不传 targetProviderId，后端走供应商+模型 upsert 路径。 */
  public openImportModal(): void {
    const modalRef = this.modalService.create({
      nzContent: ModelImportModalComponent,
      nzTitle: this.i18n.transform('import_models'),
      nzWidth: '760px',
      nzFooter: null,
    });
    modalRef.afterClose.subscribe((imported: boolean) => {
      if (imported) {
        this.getCustomData();
      }
    });
  }

  public authModal(item: any) {
    const modalRef = this.modalService.create({
      nzContent: AuthModalComponent,
      nzWidth: '500px',
      nzFooter: null,
    });

    const instance = modalRef.getContentComponent();
    instance.id = item.id;
    instance.provider_info = item;

    modalRef.afterClose.subscribe(() => {
      this.getCustomData();
    });
  }

  public deleteModal(item: any) {
    const modalRef = this.modalService.create({
      nzContent: DeleteModalComponent,
      nzWidth: '500px',
      nzFooter: null,
      nzData: {
        context: {
          id: item.id,
          title: this.i18n.transform('del_providers'),
          tip: this.i18n.transform('confirm_delete_supplier_desc', { provider_name: item.provider_name }),
          fnName: 'deleteProvider',
          close: () => {
            this.messageService.success(this.i18n.transform('model_supplier_delete_success_tip'));
            this.getCustomData(true);
            modalRef.close();
          },
        },
      } as any,
    });
  }

  public openPublisherHalfModel(provider?: any) {
    const drawerRef = this.drawerService.create({
      nzContent: AddPublisherComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzContentParams: {
        title: provider
          ? this.i18n.transform('edit-model-publisher', { ns: I18nNamespace.MODEL_ACCESS })
          : this.i18n.transform('add-model-publisher', { ns: I18nNamespace.MODEL_ACCESS }),
        source: 'integration',
        provider_id: provider?.id,
      },
    });

    drawerRef.afterClose.subscribe(() => {
      this.customOnSearch();
    });
  }

  private validateUserInput(userInput: string): boolean {
    return /^[\u4e00-\u9fa5a-zA-Z0-9_ -]{1,64}$/.test(userInput);
  }

  public onSearchChange(value: string): void {
    if (!value) {
      this.customOnSearch();
    }
  }
}
