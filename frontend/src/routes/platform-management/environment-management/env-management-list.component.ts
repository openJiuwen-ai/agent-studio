import { Component, OnInit, OnDestroy, ViewContainerRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { SharedModule } from '@shared/shared.module';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { CommonUtils } from '../../../utils/common.util';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { formatTime } from 'src/utils/commonFn';
import {
  UntypedFormControl,
  UntypedFormGroup,
  AbstractControl,
  ValidationErrors,
  Validators,
  FormsModule,
  ReactiveFormsModule
} from '@angular/forms';
import { EnvManagementService } from './env-management.service';
import { environmentStatusMap } from '@routes/platform-management/environment-management/env-management.map';
import { EnvDetailComponent } from '@routes/platform-management/environment-management/env-detail/env-detail.component';
import { EnvDeleteComponent } from '@routes/platform-management/environment-management/env-delete/env-delete.component';
import { CommonValidation } from '@shared/validation/commonValidation';
import { CommonService } from '@services/common.service';
import {
  NewCommonNoDataWithBtnComponent
} from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzFormModule } from 'ng-zorro-antd/form';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzDrawerModule, NzDrawerService, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'env-management-list',
  templateUrl: './env-management-list.component.html',
  styleUrls: ['./env-management-list.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MODULES,
    SharedModule,
    NewCommonNoDataWithBtnComponent,
    NzTableModule,
    NzInputModule,
    NzPaginationModule,
    NzAlertModule,
    NzTagModule,
    NzSelectModule,
    NzFormModule,
    NzButtonModule,
    NzIconModule,
    NzDropDownModule,
    NzDrawerModule,
    NzModalModule,
    NzToolTipModule,
    EnvDeleteComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.PLATFORM_MANAGEMENT,
        I18nNamespace.TRACE,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT,
      ],
    },
    agentCommonLogic,
    NzModalService,
    NzDrawerService
  ],
})
export class EnvManagementListComponent implements OnInit, OnDestroy {
  isHasPermission = true;
  formGroup = new UntypedFormGroup({
    name: new UntypedFormControl({ value: '', disabled: false }, [
      Validators.required,
      Validators.maxLength(48),
      Validators.minLength(4),
      CommonValidation.customVerify(
        /^[a-zA-Z][a-zA-Z0-9-]*$/,
        this.i18n.transform('create_env_name_verify'),
      ),
    ]),
    description: new UntypedFormControl('', [
      Validators.maxLength(128),
      (control: AbstractControl): ValidationErrors | null => {
        const value = control.value;
        if (!value || value.trim().length === 0) {
          return null;
        }
        const pattern = /^[\u4e00-\u9fa5a-zA-Z0-9][\u4e00-\u9fa5a-zA-Z0-9_()\-\s]*$/;
        if (!pattern.test(value)) {
          return {
            customPattern: {
              tiErrorMessage: this.i18n.transform('create_env_desc_verify'),
            },
          };
        }
        return null;
      },
    ]),
    vpcId: new UntypedFormControl('', [Validators.required]),
    subnetId: new UntypedFormControl('', [Validators.required]),
  });

  isDrawerVisible = false;
  modalTypeName = '';
  environmentId: string = '';

  private refreshTimer: any = null;
  private readonly REFRESH_INTERVAL = 30000;
  private isPolling = false;
  private isRefreshing = false;

  async showModal(type: string, data?: any) {
    if (type === 'create') {
      this.modalTypeName = this.i18n.transform('create_env');
    } else if (type === 'edit') {
      const result = await this.environmentManagementService.getEnvironmentDetail(data.id);
      this.modalTypeName = this.i18n.transform('edit_env');
      this.environmentId = data.id;
      this.formGroup.get('name')?.disable();
      this.formGroup.get('vpcId')?.disable();
      this.formGroup.get('subnetId')?.disable();
      this.formGroup.setValue({
        name: result.name,
        description: result.description || '',
        vpcId: this.findMatchingVpc(result, this.vpcOptions)?.id || '',
        subnetId: this.findMatchingSubnet(result, this.subnetsOptions)?.id || '',
      });
    }
    this.isDrawerVisible = true;
  }

  findMatchingVpc(item: any, vpcList: any[]): any {
    return vpcList.find(
      (vpc) => vpc.cidr === item.vpcCidr && vpc.name === item.vpcName,
    );
  }

  findMatchingSubnet(item: any, subnetList: any[]): any {
    return subnetList.find(
      (subnet) =>
        subnet.cidr === item.subnetCidr && subnet.name === item.subnetName,
    );
  }

  public hideModal(): void {
    this.clearValue();
    this.formGroup.reset();
    this.isDrawerVisible = false;
  }

  clearValue() {
    this.modalTypeName = this.i18n.transform('create_env');
    this.formGroup.get('name')?.enable();
    this.formGroup.get('vpcId')?.enable();
    this.formGroup.get('subnetId')?.enable();
    this.environmentId = '';
  }

  noDataDescTip = this.i18n.transform('no_env_data_tip');
  noDataBtnStr = this.i18n.transform('create_env');

  currentPage: number = 1;
  totalNumber: number = 0;
  pageSize: { options: number[]; size: number } = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  srcData: any = {
    data: [],
    state: undefined,
  };

  listColumns: Array<any> = [
    { title: this.i18n.transform('name') },
    { title: this.i18n.transform('description') },
    { title: this.i18n.transform('status') },
    { title: this.i18n.transform('update_time') },
    { title: this.i18n.transform('operation'), fixed: 'right', width: '160px' },
  ];

  loading = false;
  searchValue = '';
  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  constructor(
    private environmentManagementService: EnvManagementService,
    private nzDrawerService: NzDrawerService,
    private nzModalService: NzModalService,
    public commonService: CommonService,
    private i18n: I18NextEagerPipe,
    private message: NzMessageService,
    private viewContainerRef: ViewContainerRef
  ) {
    this.lang = CommonUtils.getLanguage();
  }

  createVpcUrl = '';
  createSubnetUrl = '';
  agentRunUrl = '';
  regionId = '';

  async ngOnInit() {
    this.getEnvironmentListData();
  }

  findItemByText(data, textValue) {
    return data.find((item) => item.text === textValue);
  }

  async getCheckPermission(): Promise<void> {
    try {
      const res = await this.environmentManagementService.checkPermission();
      this.isHasPermission = res;
    } catch (error) {
      this.isHasPermission = false;
    }
  }

  createVpc() {
    if (this.createVpcUrl) {
      window.open(this.createVpcUrl, '_blank');
    }
  }

  createSubnet() {
    window.open(this.createSubnetUrl, '_blank');
  }

  toAgentRun() {
    window.open(this.agentRunUrl, '_blank');
  }

  dataToItemsFn = (data: any): Array<any> => {
    const items: any[] = [
      {
        label: this.i18n.transform('edit'),
        id: 'edit',
        disabled: data.isNoEditPermission,
      },
      {
        label: this.i18n.transform('delete'),
        id: 'delete',
        disabled: data.isNoDeletePermission,
      },
    ];

    if (!data.isDefault) {
      items.push({
        label: this.i18n.transform('set_as_default'),
        id: 'setDefault',
        disabled: data.isSetDefaultPermission,
      });
    }

    return items;
  };

  public listAction($event: any, row: any) {
    if ($event.id === 'delete') {
      this.deleteEnvData(row);
    } else if ($event.id === 'edit') {
      this.showModal('edit', row);
    } else if ($event.id === 'setDefault') {
      this.environmentManagementService
        .setDefaultEnvironment(row.id)
        .then(() => {
          this.message.success(this.i18n.transform('setting_success'));
          this.getEnvironmentListData();
        });
    }
  }

  deleteEnvData(data: any): void {
    this.environmentManagementService
      .queryAssociatedInstance(data.id, { page: 1, pageSize: 10 })
      .then((response) => {
        const modal = this.nzModalService.create({
          nzContent: EnvDeleteComponent,
          nzViewContainerRef: this.viewContainerRef,
          nzClassName: response.env_info.length > 0 ? 'delete-env-modal-class' : 'delete-env-modal-class-another',
          nzFooter: null,
          nzData: {
            context: {
              data: data,
              envInfo: response.env_info || [],
            },
            close: (): void => {
              this.environmentManagementService
                .deleteEnvironment(data.id)
                .then(() => {
                  this.message.success(this.i18n.transform('start_delete'));
                  this.getEnvironmentListData();
                  modal.close();
                });
            },
            dismiss: (): void => {
              modal.close();
            },
          } as any
        });
      });
  }

  pageUpdate($event: any) {
    this.currentPage = $event.currentPage;
    this.pageSize.size = $event.size;
    this.getEnvironmentListData();
  }

  onPageIndexChange(page: number): void {
    this.pageUpdate({ currentPage: page, size: this.pageSize.size });
  }

  onPageSizeChange(size: number): void {
    this.pageUpdate({ currentPage: 1, size: size });
  }

  searchList() {
    this.currentPage = 1;
    this.pageSize.size = 10;
    this.getEnvironmentListData();
  }

  handleClickClearSearch() {
    this.searchValue = '';
    this.searchList();
  }

  validateUserInput(userInput: string): boolean {
    const regex = /^[a-zA-Z][a-zA-Z0-9-]*$/;
    return regex.test(userInput);
  }

  private processEnvironmentData(envInfo: any[]): any[] {
    return envInfo.map((item) => {
      item.isHasPermission = this.isHasPermission;
      item.isNoEditPermission = !(
        !['DELETE_FAILED', 'DELETING', 'FAILED', 'creating', 'CREATING'].includes(item.status) &&
        this.isHasPermission &&
        this.subscribeBtnStatus
      );
      item.isNoDeletePermission = !(
        !['DELETING', 'creating', 'CREATING'].includes(item.status) &&
        this.isHasPermission &&
        this.subscribeBtnStatus
      );
      item.isSetDefaultPermission = !(
        !['DELETE_FAILED', 'DELETING', 'FAILED', 'creating', 'CREATING'].includes(item.status) &&
        this.isHasPermission &&
        this.subscribeBtnStatus
      );
      item.actionItems = this.dataToItemsFn(item);

      return item;
    });
  }

  private getEnvironmentQueryParams(): any {
    const params: any = {
      limit: this.pageSize.size,
      offset: (this.currentPage - 1) * this.pageSize.size,
    };
    if (this.searchValue && this.validateUserInput(this.searchValue)) {
      params.name = this.searchValue;
    }
    return params;
  }

  private updateTableData(result: any): void {
    this.srcData.data = this.processEnvironmentData(result.env_info || []);
    this.totalNumber = result.total || 0;
  }

  public async getEnvironmentListData(): Promise<void> {
    try {
      this.loading = true;
      if (this.searchValue && !this.validateUserInput(this.searchValue)) {
        this.message.error(this.i18n.transform('create_env_name_verify'));
        this.loading = false;
        return;
      }
      const params = this.getEnvironmentQueryParams();
      const result = await this.environmentManagementService.getEnvironmentList(params);
      this.updateTableData(result);
      this.checkAndStartPolling();
    } finally {
      this.loading = false;
    }
  }

  public formValidate(): boolean {
    let ignore: string[] = [];
    ignore = ['vpcId', 'subnetId'];

    let isValid = true;
    Object.keys(this.formGroup.controls).forEach(key => {
      if (!ignore.includes(key)) {
        const control = this.formGroup.get(key);
        if (control) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
          if (control.invalid) {
            isValid = false;
          }
        }
      }
    });

    return isValid;
  }

  createEnvironment() {
    if (!this.formValidate()) {
      return;
    }

    const params = {
      name: this.formGroup.get('name')!.value,
      description: this.formGroup.get('description')!.value,
      vpcId: this.formGroup.get('vpcId')!.value || 'default',
      subnetId: this.formGroup.get('subnetId')!.value || 'default',
    };

    if (this.environmentId) {
      this.environmentManagementService
        .editEnvironment(this.environmentId, params)
        .then(() => {
          this.message.success(this.i18n.transform('edit_success_1'));
          this.hideModal();
          this.getEnvironmentListData();
        });
    } else {
      this.environmentManagementService.createEnvironment(params).then(() => {
        this.message.success(this.i18n.transform('create_success'));
        this.hideModal();
        this.getEnvironmentListData();
      });
    }
  }

  vpcOptions: Array<any> = [];
  vpcLoading = false;

  onVpcOpenChange(open: boolean): void {
    if (open) {
      this.vpcLoading = true;
      this.environmentManagementService
        .queryVpcs()
        .then((res) => {
          this.vpcOptions = res.map((item) => {
            item.text = item.name + '（' + item.cidr + '）';
            return item;
          });
        })
        .catch(() => {
          this.vpcOptions = [];
        })
        .finally(() => {
          this.vpcLoading = false;
        });
    }
  }

  refreshVpc() {
    this.environmentManagementService
      .queryVpcs()
      .then((res) => {
        this.vpcOptions = res.map((item) => {
          item.text = item.name + '（' + item.cidr + '）';
          return item;
        });
      })
      .catch((error) => {
        this.vpcOptions = [];
      });
  }

  subnetsOptions: Array<any> = [];
  subnetLoading = false;

  onSubnetOpenChange(open: boolean): void {
    if (open) {
      if (!this.formGroup.get('vpcId')?.value) {
        this.message.error(
          this.i18n.transform('select_env_resource_vpc'),
        );
        return;
      }

      this.subnetLoading = true;
      this.environmentManagementService
        .querySubnets({
          vpc_id: this.formGroup.get('vpcId')?.value,
        })
        .then((res) => {
          this.subnetsOptions = res.subnet.map((item) => {
            item.text = item.name + '（' + item.cidr + '）';
            return item;
          });
        })
        .catch((error) => {
          this.subnetsOptions = [];
        })
        .finally(() => {
          this.subnetLoading = false;
        });
    }
  }

  refreshSubnet() {
    if (!this.formGroup.get('vpcId')?.value) {
      this.message.error(
        this.i18n.transform('select_env_resource_vpc'),
      );
      return;
    }
    this.environmentManagementService
      .querySubnets({
        vpc_id: this.formGroup.get('vpcId')?.value,
      })
      .then((res) => {
        this.subnetsOptions = res.subnet.map((item) => {
          item.text = item.name + '（' + item.cidr + '）';
          return item;
        });
      })
      .catch(() => {
        this.subnetsOptions = [];
      });
  }

  public modalRefDetail: NzDrawerRef | null = null;

  async openComponent(id: string) {
    try {
      const result = await this.environmentManagementService.getEnvironmentDetail(id);
      this.modalRefDetail = this.nzDrawerService.create({
        nzContent: EnvDetailComponent,
        nzWidth: '700px',
        nzPlacement: 'right',
        nzData: {
          context: {
            data: result,
            outputs: {},
          }
        } as any
      });
      this.modalRefDetail.afterClose.subscribe(() => {
        this.modalRefDetail = null;
      });
    } catch (error) {}
  }

  ngModelChange(option: any) {
    this.formGroup.get('subnetId')?.setValue('');
  }

  createEnvWithEntrust() {
    this.showModal('create');
  }

  get searchNameIsEmpty() {
    return this.searchValue.length === 0;
  }

  public trackByFn(index: number, item: any): any {
    return item.id || index;
  }

  isZH(): boolean {
    return this.lang === 'zh-cn';
  }

  getNzTagColor(type: string | undefined): string {
    switch (type) {
      case 'success':
      case 'green':
        return 'success';
      case 'error':
      case 'danger':
      case 'red':
        return 'error';
      case 'warning':
      case 'yellow':
        return 'warning';
      case 'primary':
      case 'blue':
      case 'info':
        return 'processing';
      default:
        return 'default';
    }
  }

  private checkAndStartPolling(): void {
    this.stopPolling();
    const hasCreatingEnv = this.srcData.data.some((item) =>
      ['creating', 'CREATING'].includes(item.status),
    );
    if (hasCreatingEnv && !this.isPolling) {
      this.startPolling();
    }
  }

  private startPolling(): void {
    this.isPolling = true;
    this.refreshTimer = setInterval(() => {
      this.pollEnvironmentList();
    }, this.REFRESH_INTERVAL);
  }

  private async pollEnvironmentList(): Promise<void> {
    if (this.isRefreshing) {
      return;
    }

    try {
      this.isRefreshing = true;
      const params = this.getEnvironmentQueryParams();
      const result = await this.environmentManagementService.getEnvironmentList(
        params,
      );
      this.updateTableData(result);
      const stillHasCreatingEnv = this.srcData.data.some((item) =>
        ['creating', 'CREATING'].includes(item.status),
      );
      if (!stillHasCreatingEnv) {
        this.stopPolling();
      }
    } catch (error) {
      this.stopPolling();
    } finally {
      this.isRefreshing = false;
    }
  }

  private stopPolling(): void {
    if (this.refreshTimer) {
      clearInterval(this.refreshTimer);
      this.refreshTimer = null;
    }
    this.isPolling = false;
  }

  ngOnDestroy() {
    if (this.modalRefDetail) {
      this.modalRefDetail.close();
    }
    this.stopPolling();
  }

  private readonly lang: string = '';

  protected readonly changeUrl = cdnAssetUrl;
  protected readonly formatTime = formatTime;
  protected readonly environmentStatusMap = environmentStatusMap;
}
