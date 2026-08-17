import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { DeleteModalComponent } from "@routes/model-management/delete-modal/delete-modal.component";
import { NzModalService, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import type { ProviderInfo } from "@routes/model-management/components/auth-modal/auth.type";

@Component({
  selector: 'meta-auth-modal',
  standalone: true,
  imports: [CommonModule, MODULES, FormsModule, NzInputModule, NzIconModule, NzToolTipModule],
  templateUrl: './auth-modal.component.html',
  styleUrls: ['./auth-modal.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS, I18nNamespace.JIUWEN_MODEL],
    },
  ],
})
export class AuthModalComponent implements OnInit {
  @Input() id: '';

  iamLabel = {
    iamUrl: this.i18n.transform('server_address'),
    iamDomain: this.i18n.transform('account_name'),
    iamProject: this.i18n.transform('project'),
    iamUser: this.i18n.transform('iam_username'),
    iamPassword: this.i18n.transform('iam_user_password'),
    iamAK: 'Access Key ID',
    iamSK: 'Secret Access Key',
    iamEnterprise: this.i18n.transform('enterprise'),
    iamSecret: this.i18n.transform('password'),
    iamAccount: this.i18n.transform('account'),
    sgovUrl: 'URL',
    credential: this.i18n.transform('credential'),
    appId: 'APP ID',
  };

  @Input() provider_info: ProviderInfo;

  loading = false;
  authsInfo: any = {
    'API Key': '',
    auth_type: '',
    auth_id: '',
  };

  authsList: any[] = [];
  authType = '';
  apiKeyAuthArgs = [{ target_name: '', auth_key: '' }];

  constructor(
    private modelManagementService: ModelManagementService,
    private modalService: NzModalService,
    private modalRef: NzModalRef,
    private i18n: I18NextEagerPipe,
    private message: NzMessageService,
  ) {}

  ngOnInit() {
    if (this.provider_info?.id) {
      this.geAuthsInfo();
    }
  }

  geAuthsInfo() {
    this.modelManagementService
      .getProviderAuths({ provider_id: this.provider_info.id })
      .then((res: any) => {
        this.authsList = [];
        this.authType = res?.data[0]?.auth_type || '';
        if (res?.data[0]?.auth_info) {
          this.authsInfo = JSON.parse(res?.data[0].auth_info);
          const passwordList = [
            'API Key',
            'ak',
            'sk',
            'APP Code',
            'iamPassword',
            'iamAK',
            'iamSK',
          ];
          if (res?.data[0].auth_type === 'CUSTOM_APIKEY') {
            this.apiKeyAuthArgs = [];
            Object.keys(this.authsInfo).forEach((key) => {
              this.apiKeyAuthArgs.push({
                target_name: key,
                auth_key: this.authsInfo[key],
              });
              this.authsInfo[key] = '***';
            });
          }
          Object.keys(this.authsInfo).forEach((key) => {
            let nj = {
              key: key,
              labelName: key,
              hide: passwordList.indexOf(key) > -1,
              modalVal: this.authsInfo[key],
            };
            if (
              res?.data[0].auth_type === 'CUSTOM_IAM' ||
              res?.data[0].auth_type === 'CUSTOM_APIKEY' ||
              res?.data[0].auth_type === 'HIS_IAM' ||
              res?.data[0].auth_type === 'SGOV'
            ) {
              nj = {
                key: key,
                hide: passwordList.indexOf(key) > -1,
                labelName: this.iamLabel[key as keyof typeof this.iamLabel] || key,
                modalVal: this.authsInfo[key],
              };
            }
            this.authsList.push(nj);
          });
          this.provider_info.auth_url = res?.data[0].auth_url;

          if (!this.provider_info.auth_configs) {
            this.provider_info.auth_configs = res.data;
          }

          this.authsInfo.auth_id = res?.data[0].auth_id;
        } else {
          this.authsInfo = res?.data[0] || {};
          if (this.authType === 'CUSTOM_APIKEY') {
            this.apiKeyAuthArgs = [{ target_name: '', auth_key: '' }];
          }
        }
      });
  }

  handelAuth() {
    let checkAuth = true;
    this.loading = true;

    if (this.authType === 'CUSTOM_APIKEY') {
      if (this.authsInfo.auth_id) {
        const modal = this.modalService.create({
          nzContent: DeleteModalComponent,
          nzWidth: '500px',
          nzFooter: null,
          nzData: {
            context: {
              id: this.authsInfo.auth_id,
              title: this.i18n.transform('remove_auth'),
              tip: this.i18n.transform('confirm_remove_auth'),
              fnName: 'deleteProviderAuths',
              close: () => {
                this.message.success(this.i18n.transform('remove_success'));
                this.close();
                modal.close();
              },
            },
          } as any,
        });
        this.loading = false;
        return;
      }
      checkAuth = this.apiKeyAuthArgs.every(
        (item) => item.target_name.trim() && item.auth_key.trim()
      );
      if (!checkAuth) {
        this.message.error(this.i18n.transform('input_auth_info'));
        this.loading = false;
        return;
      }
      let authInfo = {};
      this.apiKeyAuthArgs.forEach((item) => {
        authInfo[item.target_name] = item.auth_key;
      });
      let params = {
        metadata_id: this.provider_info.auth_configs[0].metadata_id,
        auth_info: authInfo,
      };
      this.modelManagementService
        .postProviderAuths(params, { available_check: true })
        .then((res: any) => {
          this.message.success(this.i18n.transform('auth_config_success'));
          this.close();
        })
        .catch((error) => {
          this.message.error(this.i18n.transform('auth_config_failed'));
        })
        .finally(() => {
          this.loading = false;
        });
      return;
    }

    Object.keys(this.authsInfo).forEach((key) => {
      if (key !== 'auth_id' && !this.authsInfo[key]) {
        checkAuth = false;
      }
    });
    if (!checkAuth) {
      this.message.error(this.i18n.transform('input_auth_info'));
      this.loading = false;
      return;
    }
    if (this.authsInfo.auth_id) {
      const modal = this.modalService.create({
        nzContent: DeleteModalComponent,
        nzWidth: '500px',
        nzFooter: null,
        nzData: {
          context: {
            id: this.authsInfo.auth_id,
            title: this.i18n.transform('remove_auth'),
            tip: this.i18n.transform('confirm_remove_auth'),
            fnName: 'deleteProviderAuths',
            close: () => {
              this.message.success(this.i18n.transform('remove_success'));
              this.close();
              modal.close();
            },
          },
        } as any,
      });
      this.loading = false;
      return;
    } else {
      let params = {
        metadata_id: this.provider_info.auth_configs[0].metadata_id,
        auth_info: this.authsInfo,
      };
      this.modelManagementService
        .postProviderAuths(params, { available_check: true })
        .then((res: any) => {
          this.message.success(this.i18n.transform('auth_config_success'));
          this.close();
        })
        .catch((error) => {
          this.message.error(this.i18n.transform('auth_config_failed'));
        }).finally(() => {this.loading = false});
    }
  }

  public addArgs() {
    this.apiKeyAuthArgs.push({ target_name: '', auth_key: '' });
  }

  public deleteArgs(i: number) {
    this.apiKeyAuthArgs.splice(i, 1);
  }

  delete() {
    // @ts-ignore 绕过索引签名检查，如果 modelManagementService 里确实有该方法
    this.modelManagementService.deleteProviderAuths(this.authsInfo.auth_id)
      .then(() => {
        this.close();
      })
      .finally(() => {
        this.loading = false;
      });
  }

  close(): void {
    this.modalRef.close(true);
  }

  dismiss(): void {
    this.modalRef.destroy();
  }
}
