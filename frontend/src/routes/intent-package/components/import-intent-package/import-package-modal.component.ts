import { Component, ViewChild, ElementRef, Optional, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { CommonUtils } from 'src/utils/common.util';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { IntentPackageService } from '../../intent-package.service';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
@Component({
  selector: 'import-intent-package-modal',
  templateUrl: './import-package-modal.component.html',
  styleUrls: ['./import-package-modal.component.less'],
  standalone: true,
  imports: [CommonModule, MODULES, NzButtonModule, NzIconModule, NzSpinModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ImportPackageModalComponent {
  @ViewChild('importRef') importRef: ElementRef<HTMLInputElement>;
  @ViewChild('fileInput') fileInput: ElementRef<HTMLInputElement>;

  public changeUrl = cdnAssetUrl;
  public uplaodFile: any = {};
  public isLoading = false;

  constructor(
    private readonly intentPackageServ: IntentPackageService,
    private readonly i18n: I18NextEagerPipe,
    private message: NzMessageService,
    @Optional() private modalRef: NzModalRef,
    private commonLogic: agentCommonLogic,
    @Optional() @Inject(NZ_MODAL_DATA) public nzData: any,
  ) {}

  downloadTemplate(): void {
    this.intentPackageServ.downloadTemlate().then(res => {
      CommonUtils.downloadFile(
        new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
        `${this.commonLogic.getFormattedDateTime()}.xlsx`
      );
    });
  }

  public onUploadFile(e: Event): void {
    const fileInput = e.target as HTMLInputElement;
    if (!fileInput.files || fileInput.files.length === 0) return;
    const fileObj: File = fileInput.files[0];

    if (fileObj.size > 1024 * 1024 * 5) {
      this.message.warning(this.i18n.transform('file_size_error'));
      return;
    }

    const fileExt = fileObj.name.split('.').pop()?.toLowerCase();
    if (!['xlsx'].includes(fileExt || '')) {
      this.message.warning(this.i18n.transform('file_type_error'));
      return;
    }

    this.uplaodFile.name = fileObj.name;
    this.uplaodFile.file = fileObj;
  }

  public uploadIntent(): void {
    if (this.fileInput && this.fileInput.nativeElement) {
      this.fileInput.nativeElement.value = '';
      this.fileInput.nativeElement.click();
    }
  }

  public removeFile(): void {
    this.uplaodFile = {};
    if (this.fileInput?.nativeElement) {
      this.fileInput.nativeElement.value = '';
    }
  }

  public importIntent(): void {
    if (this.isLoading || !this.uplaodFile.file) {
      return;
    }

    this.isLoading = true;

    const formData = new FormData();
    formData.append('file', this.uplaodFile.file);
    this.intentPackageServ
      .uploadFile(formData)
      .then((res: any) => {
        if (res.success) {
          this.dismiss();
          this.message.success(this.i18n.transform('upload_success'));
          if (this.nzData?.outputs?.refreshTable) {
            this.nzData.outputs.refreshTable();
          }
        }
      })
      .finally(() => {
        this.isLoading = false;
      });
  }

  public dismiss() {
    if (this.modalRef) {
      this.modalRef.destroy();
    }
  }
}
