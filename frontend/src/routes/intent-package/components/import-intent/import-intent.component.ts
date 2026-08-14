import { Component, ViewChild, ElementRef, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { CommonUtils } from 'src/utils/common.util';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { MessageComponent } from '@shared/services/cfdata.service';
import { IntentPackageService } from '../../intent-package.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
@Component({
  selector: 'import-intent-modal',
  templateUrl: './import-intent.component.html',
  styleUrls: ['./import-intent.component.less'],
  standalone: true,
  imports: [CommonModule, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ImportIntentModalComponent {
  @ViewChild('importRef') importRef: ElementRef<HTMLInputElement>;

  @ViewChild('fileInput') fileInput: ElementRef<HTMLInputElement>;

  constructor(
    private readonly i18n: I18NextEagerPipe,
    private readonly api: IntentPackageService,
    private commonLogic: agentCommonLogic,
    private modalRef: NzModalRef,
    @Inject(NZ_MODAL_DATA) public nzData: any,
  ) {}

  public changeUrl = cdnAssetUrl;

  public uplaodFile: any = {};

  get intentId(): string {
    return this.nzData?.intentId;
  }

  get intentName(): string {
    return this.nzData?.intentName;
  }

  downTemplate(): void {
    this.api.downloadTemlate().then(res => {
      CommonUtils.downloadFile(
        new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
        `${this.commonLogic.getFormattedDateTime()}.xlsx`
      );
    });
  }

  uploadIntent(): void {
    this.fileInput.nativeElement.value = null;
    this.fileInput.nativeElement.click();
  }

  public onUploadFile(e: Event): void {
    const input = e.target as HTMLInputElement;
    const file: File = input.files[0];
    if (file.size > 1024 * 1024 * 5) {
      MessageComponent.showError(this.i18n.transform('file_size_error'), 3000);
      return;
    }

    const fileExtension = file.name.split('.').pop().toLowerCase();
    if (!['xlsx'].includes(fileExtension)) {
      MessageComponent.showError(this.i18n.transform('file_type_error'), 3000);
      return;
    }

    this.uplaodFile.name = file.name;
    this.uplaodFile.file = file;
  }

  importIntent(): void {
    if (!this.uplaodFile.file) {
      return;
    }
    const options: any = {
      target: this.importRef?.nativeElement,
    };
    const formData = new FormData();
    formData.append('file', this.uplaodFile.file);
    this.api
      .uploadIntent(this.intentId, this.intentName, formData)
      .then((res: any) => {
        if (res.success) {
          this.dismiss();
          MessageComponent.showSuccess(this.i18n.transform('upload_success'), 3000);
          if (this.nzData?.outputs?.refreshTable) {
            this.nzData.outputs.refreshTable(res.intent_ids);
          }
        }
      })
      .finally(() => {});
  }

  dismiss() {
    this.modalRef.close();
  }
}
