import { ChangeDetectionStrategy, ChangeDetectorRef, Component } from '@angular/core';
import { MODULES } from '@shared/modules';
import { PromptService } from '@services/prompt.service';
import { CommonUtils } from '../../../../utils/common.util';
import { cdnAssetUrl } from '../../../../single-spa/assets-url';
import { MessageComponent } from '@shared/services/cfdata.service';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import i18next from 'i18next';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
import { NzModalModule, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-import-template-modal',
  standalone: true,
  imports: [NzButtonModule, NzUploadModule, NzModalModule, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  templateUrl: './import-template-modal.component.html',
  styleUrl: './import-template-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImportTemplateModalComponent {
  public selectedFile: NzUploadFile | null = null;
  public fileList: NzUploadFile[] = [];
  private nativeFile: File | null = null;
  public readonly maxSize = 20 * 1024 * 1024;
  public readonly uploadType = ['.xls', '.xlsx'];
  constructor(
    private service: PromptService,
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private message: NzMessageService,
    private modalRef: NzModalRef,
    private cdr: ChangeDetectorRef,
  ) {}

  beforeUpload = (file: NzUploadFile): boolean => {
    const nativeFile = ((file as any)._file || file) as File;
    const fileName = file.name || nativeFile.name || '';
    const extension = fileName.slice(fileName.lastIndexOf('.')).toLowerCase();

    if (!this.uploadType.includes(extension)) {
      this.message.error(this.i18n.transform('file_wrong_type', { name: fileName }));
      return false;
    }
    if (nativeFile.size > this.maxSize) {
      this.message.error(
        this.i18n.transform('file_size_cannot_exceed', { size: this.maxSize / (1024 * 1024) })
      );
      return false;
    }

    this.selectedFile = file;
    this.nativeFile = nativeFile;
    this.fileList = [file];
    this.cdr.markForCheck();
    return false;
  };

  onRemove = (): boolean => {
    this.selectedFile = null;
    this.nativeFile = null;
    this.fileList = [];
    this.cdr.markForCheck();
    return true;
  };

  dismiss(): void {
    this.modalRef.destroy();
  }

  close(): void {
    this.modalRef.destroy();
  }

  confirm() {
    if (!this.nativeFile) return;
    const formData = new FormData();
    formData.append('file', this.nativeFile);
    this.service.importPromptTmplV2(formData).subscribe(res => {
      if (res.length === 0) {
        this.close();
      } else {
        MessageComponent.showError(res.join(','));
        this.dismiss();
      }
    });
  }

  downloadTemplate() {
    this.service.downloadImportTmplCase().subscribe(res => {
      CommonUtils.downloadFile(
        new Blob([res.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
        res.headers.get('Content-Disposition')
      );
    });
  }

  protected readonly changeUrl = cdnAssetUrl;
  protected readonly i18next = i18next;
}
