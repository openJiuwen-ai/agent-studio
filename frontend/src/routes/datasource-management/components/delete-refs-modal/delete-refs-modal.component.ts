import { Component, EventEmitter, Input, Output, inject } from '@angular/core';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { RefTypeToTextPipe } from 'src/pipes/ref-type-to-text.pipe';
import { IPage } from '@routes/agent-center/types/common.types';
import { HttpService } from '@services/http.service';
@Component({
  selector: 'meta-delete-refs-modal',
  templateUrl: './delete-refs-modal.component.html',
  styleUrls: ['./delete-refs-modal.component.scss'],
  standalone: true,
  imports: [MODULES, RefTypeToTextPipe],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class DeleteRefsModalComponent {
  readonly modalRef = inject(NzModalRef);

  @Input() title: string = '';

  @Input() alertText: string = '';

  @Input() secondConfirmConfig: any;

  @Input() srcData: any = {
    data: [],
    state: {
      searched: false,
      sorted: false,
      paginated: true,
    },
  };

  @Input() totalNumber: number = 0;

  @Output() confirm = new EventEmitter();

  @Output() pageInfo = new EventEmitter<IPage>();
  workspaceId = '';

  public columns: Array<any> = [
    {
      title: this.i18n.transform('name'),
    },
    {
      title: this.i18n.transform('version'),
    },
    {
      title: this.i18n.transform('type'),
    },
  ];

  public pageSize = {
    options: [10, 20, 50, 100],
    size: 10,
  };

  public currentPage: number = 1;

  public errorClass = false;

  public deleteVal = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private readonly http: HttpService
  ) {}
  ngOnInit() {
    this.workspaceId = this.http.getWorkspaceId();
  }

  public close() {
    this.modalRef.destroy();
  }

  public dismiss() {
    this.modalRef.destroy();
  }

  public onConfirm() {
    if (this.deleteVal.toUpperCase() === 'DELETE' || this.srcData.data.length === 0) {
      this.close();
      this.confirm.emit();
    } else {
      this.errorClass = true;
    }
  }

  public getMappingsByPage() {
    this.pageInfo.emit({
      limit: this.pageSize.size,
      offset: this.currentPage,
    });
  }

  public navigateAppDetail(row: any) {
    const url = window.location.href?.split('/home');
    const prefixUrl = url[0];
    const { app_type, app_id, app_version } = row;

    if (app_type === 'workflow') {
      window.open(
        `${prefixUrl}/home/agent-center/app-flow/flow?id=${app_id}${app_version ? '&versionId=' + app_version : ''}&workspace_id=${this.workspaceId}`,
        '_blank'
      );
    } else if (app_type === 'agent') {
      if (row.is_controller) {
        window.open(
          `${prefixUrl}/home/agent-center/app-flow/flow?id=${app_id}${app_version ? '&versionId=' + app_version : ''}&type=multi&workspace_id=${this.workspaceId}`,
          '_blank'
        );
        return;
      }
      window.open(`${prefixUrl}/home/agent-center/app-agent/detail?agentId=${app_id}${app_version ? '&versionId=' + app_version : ''}`, '_blank');
    }
  }
}
