import { ChangeDetectorRef, Component, Input, OnInit, Optional } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { DataSourceManagementRepoService } from '@services/repositories/datasource-management-repo.service';
import { IDatasourceDetail } from '@routes/agent-center/types/datasource.types';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';

@Component({
  selector: 'editable-datasource-halfmodal',
  templateUrl: './editable-datasource-halfmodal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
    },
    NzMessageService
  ],
})
export class EditableDatasourceHalfmodalComponent implements OnInit {
  @Input() title = this.i18n.transform('connect_data_source');
  @Input() id = '';

  public form: FormGroup;

  public typeOptions = [
    {
      label: 'MySQL',
      value: 'MYSQL',
    },
  ];

  public internetAccessOptions = [
    { label: this.i18n.transform('public_network'), value: 'public' },
  ];

  public btnLoading = false;
  public status = '';
  public lastErrorMessage = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private fb: FormBuilder,
    private dataSourceRepoServe: DataSourceManagementRepoService,
    private nzMessage: NzMessageService,
    private cdr: ChangeDetectorRef,
    @Optional() private drawerRef: NzDrawerRef
  ) {
    this.form = this.fb.group({
      name: ['', [Validators.required, Validators.maxLength(64)]],
      desc: ['', [Validators.maxLength(2048)]],
      type: [this.typeOptions[0], [Validators.required]],
      internet_access: ['public'],
      host: ['', [Validators.required, Validators.maxLength(64)]],
      port: ['', [Validators.required, Validators.maxLength(16)]],
      database_name: ['', [Validators.required, Validators.maxLength(64)]],
      ssl_enabled: [true],
      user: ['', [Validators.required, Validators.maxLength(64)]],
      password: ['', [Validators.required, Validators.maxLength(64)]],
    });
  }

  ngOnInit() {
    if (this.id) {
      this.getDatasourceDetail();
    }
  }

  dismiss(): void {
    this.drawerRef?.close();
  }

  close(): void {
    this.drawerRef?.close();
  }

  public async createDatasource() {
    if (this.form.invalid) {
      Object.values(this.form.controls).forEach(control => {
        if (control.invalid) {
          control.markAsDirty();
          control.updateValueAndValidity({ onlySelf: true });
        }
      });
      return;
    }

    this.btnLoading = true;
    const raw = this.form.value;
    const params = {
      name: raw.name,
      desc: raw.desc,
      type: raw.type.value,
      connectionInfo: {
        host: raw.host,
        port: raw.port,
        sslEnabled: raw.ssl_enabled,
        databaseName: raw.database_name,
        user: raw.user,
        password: raw.password,
      },
    };
    try {
      if (this.id) {
        await this.dataSourceRepoServe.modifyDatasource(this.id, params);
        this.nzMessage.success(
          this.i18n.transform('successfully_modify_datasource'),
        );
      } else {
        await this.dataSourceRepoServe.createDatasource(params);
        this.nzMessage.success(
          this.i18n.transform('successfully_create_datasource'),
        );
      }
      this.close();
    } catch {
      // 错误已由 HTTP 全局错误处理器展示
    } finally {
      this.btnLoading = false;
      this.cdr.detectChanges();
    }
  }

  private getDatasourceDetail() {
    this.dataSourceRepoServe
      .getDatasourceDetail(this.id)
      .then((res: IDatasourceDetail) => {
        this.backfillData(res);
      });
  }

  private backfillData(res: IDatasourceDetail) {
    const selectedType = this.typeOptions.find((i) => i.value === res.type);

    this.form.controls.name.setValue(res.name);
    this.form.controls.desc.setValue(res.desc);
    this.form.controls.type.setValue(selectedType);
    this.form.controls.host.setValue(res.connectionInfo?.host);
    this.form.controls.port.setValue(res.connectionInfo?.port);
    this.form.controls.database_name.setValue(
      res.connectionInfo?.databaseName,
    );
    this.form.controls.ssl_enabled.setValue(res.connectionInfo?.sslEnabled);
    this.form.controls.user.setValue(res.connectionInfo?.user);
    this.form.controls.password.setValue(res.connectionInfo?.password);
    this.status = res.status;
    this.lastErrorMessage = res.lastErrorMessage || '';
  }
}
