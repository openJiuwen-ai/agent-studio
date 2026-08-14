import { Component, Output, EventEmitter, ViewChild, ElementRef, Input, Optional, Inject } from '@angular/core';
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

  @Input() intentId: string;

  @Input() intentName: string;

  @Output() refreshTable = new EventEmitter<void>();

  constructor(
    private readonly i18n: I18NextEagerPipe,
    private readonly api: IntentPackageService,
    private commonLogic: agentCommonLogic,
    @Optional() private modalRef: NzModalRef,
    @Optional() @Inject(NZ_MODAL_DATA) private nzData: any
  ) {}

  public changeUrl = cdnAssetUrl;

  public uplaodFile: any = {};

  /**
   * 统一取 intentId：兼容 @Input() 直接绑定（模板中静态使用）
   * 和 nzModalService.create 传入 nzData.context.intentId 两种调用方式。
   */
  private get modalContext(): { intentId?: string; intentName?: string; outputs?: { refreshTable?: (ids?: string[]) => void } } {
    return this.nzData?.context ?? {};
  }

  private get effectiveIntentId(): string {
    return this.intentId ?? this.modalContext.intentId ?? '';
  }

  private get effectiveIntentName(): string {
    return this.intentName ?? this.modalContext.intentName ?? '';
  }

  /**
   * 关闭弹窗：取消按钮、导入成功后、X 按钮（由 nz-modal 内部调用）都走这里。
   * 必须销毁 NzModalRef，否则点取消弹窗无反应。
   */
  public dismiss() {
    if (this.modalRef) {
      this.modalRef.destroy();
    }
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
      .uploadIntent(this.effectiveIntentId, this.effectiveIntentName, formData)
      .then((res: any) => {
        if (res.success) {
          this.dismiss();
          MessageComponent.showSuccess(this.i18n.transform('upload_success'), 3000);
          // 兼容两种调用方式：模板 @Output 绑定 + nzModalService.create 的 nzData.context.outputs
          this.refreshTable.emit(res.intent_ids);
          this.modalContext.outputs?.refreshTable?.(res.intent_ids);
        }
      })
      .finally(() => {});
  }
}
