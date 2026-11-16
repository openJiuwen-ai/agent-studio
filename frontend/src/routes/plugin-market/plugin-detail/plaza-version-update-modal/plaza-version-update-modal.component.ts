import { Component, Inject } from '@angular/core';
import { I18NextEagerPipe, I18NEXT_NAMESPACE } from 'angular-i18next';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';

/**
 * 资产广场上架版本更新弹窗（FRS-091）
 * 展示当前上架版本，用户自选发布版本重新上架；默认选中最新发布版本。
 * 所选版本与当前上架版本一致时，提示"已是最新，无需更新"，不发起请求。
 */
@Component({
  selector: 'app-plaza-version-update-modal',
  templateUrl: './plaza-version-update-modal.component.html',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
})
export class PlazaVersionUpdateModalComponent {
  selectedVersionId = '';
  currentAnchorName = '--';

  constructor(
    private modalRef: NzModalRef,
    private i18n: I18NextEagerPipe,
    private message: NzMessageService,
    @Inject(NZ_MODAL_DATA)
    public nzData: {
      versions: any[];
      currentAnchorVersionId: string;
      latestVersionId: string;
      currentAnchorName: string;
      onUpdate: (versionId: string) => void;
    }
  ) {}

  ngOnInit(): void {
    this.currentAnchorName = this.nzData.currentAnchorName || '--';
    this.selectedVersionId = this.nzData.latestVersionId || this.nzData.currentAnchorVersionId || '';
  }

  onCancel(): void {
    this.modalRef.close();
  }

  onUpdate(): void {
    if (!this.selectedVersionId) {
      return;
    }
    if (this.selectedVersionId === this.nzData.currentAnchorVersionId) {
      this.message.warning(this.i18n.transform('plaza_anchor_already_latest'));
      return;
    }
    this.nzData.onUpdate(this.selectedVersionId);
    this.modalRef.close();
  }
}
