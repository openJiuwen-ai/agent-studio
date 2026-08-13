import { Component } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonUtils } from '../../../utils/common.util';
import { AddPublisherComponent } from '@routes/model-management/components/add-publisher/add-publisher.component';
import { AddModelComponent } from '@routes/model-management/components/add-model/add-model.component';
import { DeleteModalComponent } from '@routes/model-management/delete-modal/delete-modal.component';
import { statusNewMap, statusMeta } from '@constants/status';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { AuthModalComponent } from '@routes/model-management/components/auth-modal/auth-modal.component';
import { ModelType } from '@enums/jiuwen-model.enum';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';

enum mapKeys {
  authConfigs = 'auth_configs',
}

@Component({
  selector: 'model-management-detail',
  templateUrl: './model-management-detail.component.html',
  styleUrls: ['./model-management-detail.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    NewCommonNoDataWithBtnComponent,
    MultiFieldSearchComponent,
    NzSpinModule,
    NzIconModule,
    NzTagModule,
    NzButtonModule,
    NzInputModule,
    NzDropDownModule,
    NzPaginationModule,
    NzToolTipModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
    NzModalService,
    NzDrawerService,
  ],
})
export class ModalManagementDetailComponent {
  public changeUrl = cdnAssetUrl;
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  constructor(
    private readonly i18n: I18NextEagerPipe,
    private route: ActivatedRoute,
    private modelManagementService: ModelManagementService,
    private router: Router,
    private nzModalService: NzModalService,
    private nzDrawerService: NzDrawerService,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private nzMessageService: NzMessageService
  ) {}

  public currentPage = 1;

  public totalNumber = 0;

  public pageSize = {
    options: [12, 16, 20, 50],
    size: 12,
  };
  public pageData = [];
  public provider_id = '';
  public loading = false;
  public basicData = {} as any;
  public activeName = '';
  // 是否来自于开发者空间
  public isFromDevelopSpace: boolean = false;

  public iconEmpty = cdnAssetUrl('assets/images/model/empty.svg');
  public iconNoneEmpty = cdnAssetUrl('assets/model/default_model_detail.svg');
  public iconBasicNoneEmpty = cdnAssetUrl('assets/model/default_model.svg');

  public itemsTab1: Array<any> = [
    {
      label: this.i18n.transform('auth_configuration'),
      disabled: !this.subscribeBtnStatus,
      type: 'authModal',
      disIcon: cdnAssetUrl('assets/model/dis_new_setting.svg'),
      icon: cdnAssetUrl('assets/model/new_setting.svg'),
    },
  ];

  public itemsTab2: Array<any> = [
    {
      label: this.i18n.transform('auth_configuration'),
      disabled: !this.subscribeBtnStatus,
      type: 'authModal',
      disIcon: cdnAssetUrl('assets/model/dis_new_setting.svg'),
      icon: cdnAssetUrl('assets/model/new_setting.svg'),
    },
    {
      label: this.i18n.transform('edit'),
      disabled: !this.subscribeBtnStatus,
      type: 'openPublisherHalfModel',
      icon: cdnAssetUrl('assets/model/new_edit.svg'),
      disIcon: cdnAssetUrl('assets/images/model/editGray.svg'),
    },
    {
      label: this.i18n.transform('delete'),
      disabled: !this.subscribeBtnStatus,
      type: 'deleteModal',
      icon: cdnAssetUrl('assets/model/new_delete.svg'),
      disIcon: cdnAssetUrl('assets/agent-observatory/delete.svg'),
    },
  ];
  public tagMap = {
    'is_support_function': {
      name: this.i18n.transform('tag_tool'),
      color: 'rgb(255,235,209)',
      text_color: 'rgb(217,105,0)',
      icon: 'assets/images/tag/is_tool.svg',
    },
    'is_reasoning': {
      name: this.i18n.transform('tag_reasoning'),
      color: 'rgb(244,224,252)',
      text_color: 'rgb(131,47,214)',
      icon: 'assets/images/tag/is_think.svg',
    },
    'is_network': {
      name: this.i18n.transform('tag_network'),
      color: 'rgb(222,236,255)',
      text_color: 'rgb(20,118,255)',
      icon: 'assets/images/tag/is_network.svg',
    },
  };
  public options2: Array<any> = [];

  public onBeforeOpen(visible: boolean, data) {
    if (!visible) return;
    if (this.activeName === 'PLATFORM') {
      this.options2 = [
        {
          label: this.i18n.transform('tune_model'),
          disabled: !data.auth_id || !this.subscribeBtnStatus,
          type: 'authModal',
          key: 'onlineTest',
          icon: cdnAssetUrl('assets/model/new_setting.svg'),
        },
      ];
    } else {
      this.options2 = [
        {
          label: this.i18n.transform('tune_model'),
          disabled: !data.auth_id || !this.subscribeBtnStatus,
          key: 'onlineTest',
          icon: cdnAssetUrl('assets/images/model/onlineTest.svg'),
          iconDisabled: cdnAssetUrl('assets/images/model/onlineTestGray.svg'),
        },
        {
          label: statusNewMap[data?.publish_status]?.operateText ?? statusNewMap.offline.operateText,
          key: 'stopGray',
          icon: statusNewMap[data?.publish_status]?.operateIcon ?? statusNewMap.offline.operateIcon,
          iconDisabled: cdnAssetUrl('assets/images/model/stopGray.svg'),
          disabled: data?.provider_id.startsWith('cdi-') || !this.subscribeBtnStatus,
        },
        {
          label: this.i18n.transform('edit'),
          key: 'edit',
          icon: cdnAssetUrl('assets/images/model/edit.svg'),
          iconDisabled: cdnAssetUrl('assets/images/model/editGray.svg'),
          disabled: data?.publish_status === 'online' || !this.subscribeBtnStatus,
        },
        {
          label: this.i18n.transform('delete'),
          key: 'delete',
          icon: cdnAssetUrl('assets/images/model/delete.svg'),
          disabled: data?.publish_status === 'online' || !this.subscribeBtnStatus,
        },
      ];
    }
  }

  public onSelectTop(item) {
    if (item.disabled) {
      return;
    }
    if (item.type === 'authModal') {
      this.authTopModal(this.basicData);
    } else if (item.type === 'openPublisherHalfModel') {
      this.openTopPublisherHalfModel(this.basicData);
    } else if (item.type === 'deleteModal') {
      this.deleteTopModal(this.basicData);
    }
  }

  public authTopModal(item) {
    const modal = this.nzModalService.create({
      nzContent: AuthModalComponent,
      nzWidth: '500px',
    });
    const instance = modal.getContentComponent();
    instance.id = item.id;
    instance.provider_info = item;

    modal.afterClose.subscribe(() => {
      this.getDetail();
      this.getTopPublisherListFn();
      modal.close();
    });
  }

  public openTopPublisherHalfModel(provider?) {
    const drawer = this.nzDrawerService.create({
      nzContent: AddPublisherComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzContentParams: {
        title: provider
          ? this.i18n.transform('edit-model-publisher', {
              ns: I18nNamespace.MODEL_ACCESS,
            })
          : this.i18n.transform('add-model-publisher', {
              ns: I18nNamespace.MODEL_ACCESS,
            }),
        source: this.activeName === 'PLATFORM' ? 'platform' : 'integration',
        provider_id: provider?.id,
        context: {},
        close: () => {
          this.getDetail();
          this.getTopPublisherListFn();
          drawer.close();
        },
        dismiss: () => drawer.close(),
      } as any,
    });
    drawer.afterClose.subscribe(() => {
      this.getDetail();
      this.getTopPublisherListFn();
    });
  }

  public pageloading = false;
  getTopPublisherListFn() {
    this.pageloading = true;
    return this.modelManagementService
      .getPublisherList(this.queryFilter, this.activeName === 'PLATFORM' ? 'platform' : 'integration')
      .then(res => {
        let result = res.data;
        for (const item of result) {
          item.tagStatus = {
            type: item.auth_config_status === 'available' ? 'success' : 'warning',
            text: this.getText(item),
          };
          item.last_updated_date = CommonUtils.getDateToString(item.last_updated_date);
          item.created_date = CommonUtils.getDateToString(item.created_date);
        }
        let obj = result.filter(item => item.id === this.basicData.id)[0];
        this.basicData = { ...obj };
        if (this.basicData.id.startsWith('cdi-') || !this.basicData?.created_by_user) {
          this.itemsTab2.forEach((item, index) => {
            item.disabled = !(index === 0 && !this.basicData?.created_by_user);
          });
        }
        if (this.basicData.auth_config_status === 'available') {
          this.itemsTab1[0].label = this.i18n.transform('clear_auth');
          this.itemsTab1[0].icon = cdnAssetUrl('assets/model/new_delete.svg');
          this.itemsTab2[0].label = this.i18n.transform('clear_auth');
          this.itemsTab2[0].icon = cdnAssetUrl('assets/model/new_delete.svg');
        } else {
          this.itemsTab1[0].label = this.i18n.transform('auth_configuration');
          this.itemsTab1[0].icon = cdnAssetUrl('assets/model/new_setting.svg');
          this.itemsTab2[0].label = this.i18n.transform('auth_configuration');
          this.itemsTab2[0].icon = cdnAssetUrl('assets/model/new_setting.svg');
        }
        this.itemsTab2[0].disabled = this.basicData[mapKeys.authConfigs][0].auth_type === 'NO_AUTH';
      })
      .finally(() => {
        this.pageloading = false;
      });
  }

  private getText(data) {
    if (data.auth_config_status) {
      return this.i18n.transform('partial_access');
    } else if (data.auth_config_status === 'available') {
      return this.i18n.transform('auth_available');
    }
    return this.i18n.transform('auth_disable');
  }

  public deleteTopModal(item) {
    const modal = this.nzModalService.create({
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
            this.nzMessageService.success(this.i18n.transform('model_supplier_delete_success_tip'));
            this.onPageBack();
            modal.close();
          },
        },
      } as any,
    });
  }

  public searchItems: any[] = [
    { label: this.i18n.transform('service_name'), field: 'service_name' },
    { label: this.i18n.transform('model_name'), field: 'model_name' },
    {
      label: this.i18n.transform('model_type'),
      field: 'model_type',
      options: [
        { label: this.i18n.transform('LLM'), id: ModelType.LLM },
        { label: this.i18n.transform('Text-Embedding'), id: ModelType.Text_Embedding },
        { label: this.i18n.transform('RERANK'), id: ModelType.RERANK },
        { label: this.i18n.transform('IMAGE-TO-TEXT'), id: ModelType.IMAGE_TO_TEXT },
      ],
    },
    {
      label: this.i18n.transform('publish_status'),
      field: 'publish_status',
      options: [
        { label: this.i18n.transform('published'), id: statusMeta.online },
        { label: this.i18n.transform('not_published'), id: statusMeta.offline },
      ],
    },
  ];
  public searchName: ISearchTag[] = [];
  public searchField: string = 'service_name';
  public searchString = '';
  public queryFilter = {};
  public provider_boolean = false;

  ngOnInit() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    this.route.queryParams.subscribe(params => {
      if (params.from && params.from === 'develop-space') {
        this.isFromDevelopSpace = true;
      }
      this.activeName = params.activeName;
      this.queryFilter = JSON.parse(params.queryFilter || '{}');
      this.provider_id = this.basicData.id;
      this.provider_id = params.provider_id;
      this.getDetail();
    });
  }

  goModelTest(row) {
    this.router.navigate(['/home/development-configuration'], {
      queryParams: {
        activeName: this.activeName,
        providerId: this.provider_id,
        id: row.id,
        modelType: row.model_type,
        previousUrl: 'model-test',
      },
    });
  }

  getDetail() {
    this.modelManagementService.getModelPublisherInfo(this.provider_id, this.activeName === 'PLATFORM' ? 'platform' : 'integration').then(res => {
      this.provider_boolean = !!res.provider_url;

      res.tagStatus = {
        type: res.auth_config_status === 'available' ? 'success' : 'warning',
        text: this.getText1(res),
      };
      res.last_updated_date = CommonUtils.getDateToString(res.last_updated_date);
      res.created_date = CommonUtils.getDateToString(res.created_date);
      this.basicData = res;
      this.itemsTab1[0].disabled = this.basicData[mapKeys.authConfigs][0].auth_type === 'NO_AUTH';
      this.itemsTab2[0].disabled = this.basicData[mapKeys.authConfigs][0].auth_type === 'NO_AUTH';
      // 同步按钮标签，与 getTopPublisherListFn 保持一致
      if (this.basicData.auth_config_status === 'available') {
        this.itemsTab1[0].label = this.i18n.transform('clear_auth');
        this.itemsTab1[0].icon = cdnAssetUrl('assets/model/new_delete.svg');
        this.itemsTab2[0].label = this.i18n.transform('clear_auth');
        this.itemsTab2[0].icon = cdnAssetUrl('assets/model/new_delete.svg');
      } else {
        this.itemsTab1[0].label = this.i18n.transform('auth_configuration');
        this.itemsTab1[0].icon = cdnAssetUrl('assets/model/new_setting.svg');
        this.itemsTab2[0].label = this.i18n.transform('auth_configuration');
        this.itemsTab2[0].icon = cdnAssetUrl('assets/model/new_setting.svg');
      }
      if (this.basicData.id.startsWith('cdi-') || !this.basicData?.created_by_user) {
        this.itemsTab2.forEach((item, index) => {
          item.disabled = !(index === 0 && !this.basicData?.created_by_user);
        });
      }

      this.getData();
    });
  }

  private getText1(data) {
    if (data.auth_config_status === 'part_available') {
      return this.i18n.transform('partial_access');
    } else if (data.auth_config_status === 'available') {
      return this.i18n.transform('auth_available');
    }
    return this.i18n.transform('auth_disable');
  }

  changeModelStatus(data) {
    let query = {};
    if (data?.publish_status === 'offline') {
      query = {
        available_check: true,
      };
    }
    this.modelManagementService.publishModelInfo(data.id, data?.publish_status === 'online' ? 'offline' : 'online', query).then(() => {
      this.currentPage = 1;
      this.getData();
      this.nzMessageService.success(
        data.publish_status === 'online' ? this.i18n.transform('model_service_unpublish_success') : this.i18n.transform('model_service_publish_success'),
        { nzDuration: 3000 }
      );
    });
  }

  createModelService() {
    if (this.provider_boolean) {
      this.synchronizeModelService();
    } else {
      this.openHalfModel();
    }
  }

  public deleteModal(item) {
    const modal = this.nzModalService.create({
      nzContent: DeleteModalComponent,
      nzWidth: '500px',
      nzFooter: null,
      nzData: {
        context: {
          id: item?.id,
          title: this.i18n.transform('delete_model'),
          tip: `${this.i18n.transform('confirm_delete_model_service')} ${item.service_name}`,
          fnName: 'deleteModel',
          close: () => {
            this.getData();
            this.nzMessageService.success(this.i18n.transform('model_service_delete_success'), { nzDuration: 3000 });
            modal.close();
          },
        },
      } as any,
    });
  }

  synchronizeModelService() {
    this.modelManagementService.getSynchronizeModelService(this.provider_id).then(res => {
      this.nzMessageService.success(this.i18n.transform('synchronize-model-service-success'), { nzDuration: 3000 });
      this.getData();
    });
  }

  openHalfModel(model?) {
    const drawer = this.nzDrawerService.create({
      nzTitle: model?.id ? this.i18n.transform('edit_model') : this.i18n.transform('add_model'),
      nzContent: AddModelComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzContentParams: {
        title: model?.id ? this.i18n.transform('edit_model') : this.i18n.transform('add_model'),
        model_id: model?.id,
        provider_id: this.provider_id,
        close: () => {
          this.getDetail();
          drawer.close();
        },
        dismiss: () => drawer.close(),
      } as any,
    });
    drawer.afterClose.subscribe(() => {
      this.getDetail();
    });
  }

  ngOnDestroy(): void {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
  }

  onPageBack() {
    if (this.isFromDevelopSpace) {
      this.router.navigate(['/home/develop-space'], {
        state: {
          currentNavigator: 'model',
        },
      });
      localStorage.setItem('activeName', this.activeName);
      return;
    }
    this.router.navigate(['/home/development-configuration'], {
      queryParams: {
        previousUrl: 'custom-model',
      },
    });
    localStorage.setItem('activeName', this.activeName);
  }

  toDetail(row) {
    this.router.navigate(['/home/model/detail'], {
      queryParams: {
        id: row.id,
        from: this.isFromDevelopSpace ? 'develop-space' : '',
      },
    });
  }

  clickstopProp(e) {
    e.stopPropagation();
  }

  validateUserInput(userInput: string): boolean {
    const regex = /^[\u4e00-\u9fa5a-zA-Z0-9:. _|-]{1,64}$/;
    return regex.test(userInput);
  }

  getData = () => {
    const params = {};
    for (let item of this.searchName) {
      if (item.field === 'service_name' || item.field === 'model_name') {
        if (!this.validateUserInput(item.value)) {
          this.nzMessageService.warning(`${this.i18n.transform('support_char_set')}`, { nzDuration: 3000 });
          this.loading = false;
          return false;
        }
        params[item.field] = item.value;
      } else if (item.id !== undefined) {
        params[item.field] = item.id;
      } else {
        params[item.field] = item.value;
      }
    }
    const param = {
      provider_id: this.provider_id,
      page_num: this.currentPage,
      page_size: this.pageSize.size,
      ...params,
    };
    this.loading = true;
    this.modelManagementService
      .getModelList(param)
      .then(res => {
        this.pageData = res.data ?? [];
        this.pageData.forEach(item => {
          item.last_updated_date = CommonUtils.getDateToString(item.last_updated_date);
          item.modelTags = [];
          if (item.model_tags && item.model_tags.trim()) {
            item.modelTags = item.model_tags.split(',');
          }
        });
        this.totalNumber = res.total;
      })
      .finally(() => {
        this.loading = false;
      });
    return true;
  };

  getPublisherListFn() {
    this.getData();
  }

  freshData() {
    this.currentPage = 1;
    this.getPublisherListFn();
  }

  public onSearchContentChange(): void {
    this.currentPage = 1;
    this.getPublisherListFn();
  }

  openPublisherHalfModel(provider?) {
    const drawer = this.nzDrawerService.create({
      nzContent: AddPublisherComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzContentParams: {
        title: provider
          ? this.i18n.transform('edit-model-publisher', {
              ns: I18nNamespace.MODEL_ACCESS,
            })
          : this.i18n.transform('add-model-publisher', {
              ns: I18nNamespace.MODEL_ACCESS,
            }),
        source: this.activeName === 'PLATFORM' ? 'platform' : 'integration',
        provider_id: provider?.id,
        context: {},
        close: () => {
          this.getPublisherListFn();
          drawer.close();
        },
        dismiss: () => drawer.close(),
      } as any,
    });
    drawer.afterClose.subscribe(() => {
      this.getPublisherListFn();
    });
  }

  public onSelect(menuItem, item) {
    if (menuItem.disabled) return;

    if (menuItem.key === 'onlineTest') {
      this.goModelTest(item);
    } else if (menuItem.key === 'stopGray') {
      this.changeModelStatus(item);
    } else if (menuItem.key === 'edit') {
      this.openHalfModel(item);
    } else if (menuItem.key === 'delete') {
      this.deleteModal(item);
    }
  }
}
