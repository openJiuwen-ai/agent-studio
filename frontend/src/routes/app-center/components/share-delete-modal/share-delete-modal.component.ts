import { Component, EventEmitter, Input, Output, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { MessageComponent } from '@shared/services/cfdata.service';
import { DatasetsService } from '@services/agent-observatory/datasets-service';
import { SHARE_PAGE } from '../edit-share-modal/edit-share-modal.config';
import { ShareUsageTableComponent } from '../share-usage-table/share-usage-table.component';
import { ShareService } from '../edit-share-modal/share.service';
import { Router } from '@angular/router';

@Component({
  selector: 'share-delete-modal',
  standalone: true,
  imports: [CommonModule, MODULES, ShareUsageTableComponent],
  templateUrl: './share-delete-modal.component.html',
  styleUrls: ['./share-delete-modal.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS, I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class ShareDeleteModalComponent {
  @Input() versionId: '';
  @Input() toolId: '';
  @Input() pageType = SHARE_PAGE.apply;
  @Input() shareData: any;
  @ViewChild('shareUsageTable') shareUsageTable: ShareUsageTableComponent;
  @Output() deleteVersionEvent= new EventEmitter();
  title = '';
  tip = '';
  configWord = '';
  confirmText = 'DELETE';
  loading = false;

  constructor(
    private modalRef: NzModalRef,
    private i18n: I18NextEagerPipe,
    private shareService: ShareService,
    private router: Router,
  ) { }

  ngOnInit() {
    const name = this.pageType === SHARE_PAGE.apply ? this.i18n.transform('app') : this.i18n.transform('plugin');
    this.title = `${this.i18n.transform('sharedetailbtn-1')}${this.versionId ? this.i18n.transform('share-delete-modal-1') : ''}`;
    this.tip = `${this.i18n.transform('share-delete-modal-2')}${this.versionId ? this.i18n.transform('versionmodal_46') : name}${this.i18n.transform('share-delete-modal-3')}`;
  }

  ngAfterViewInit() {
    this.shareUsageTable.queryUsage();
  }

  delete() {
    this.loading = true;
    if (this.versionId) {
       this.deleteVersionEvent.emit();
    } else {
      this.shareService
        .deleteShare(this.shareData.resource_id,{
          resource_type: this.shareData.resource_type,
        })
        .then(() => {
          this.close();
          if(this.shareData.resource_type === SHARE_PAGE.plugin){
            this.router.navigate(['/home/plugin-market'],{
              state:{
                formTab: 'share',
                myShare: true,
              }
            });
          } else{
            this.shareData.navigate(['/home/app-library'],{
              state:{
                formTab: 'share',
                myShare: true,
              }
            });
          }
        })
        .finally(() => {
          this.loading = false;
        });
    }

  }

  close(): void {
    this.modalRef.destroy(true);
  }
  dismiss(): void {
    this.modalRef.destroy(false);
  }

}
