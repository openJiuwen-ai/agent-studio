import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { MODULES } from '@shared/modules';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { PromptOptimizeService, UseCaseService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import { CommonUtils } from 'src/utils/common.util';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { Subscription } from 'rxjs';
import { VariableService } from '@services/agent-center/prompt-optimize-task/prompt-editor.service';
import { PromptType } from '@interfaces/prompt/prompt-optimize-task.interface';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzUploadFile } from 'ng-zorro-antd/upload';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';

@Component({
  selector: 'meta-import-modal',
  standalone: true,
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  templateUrl: './import-modal.component.html',
  styleUrl: './import-modal.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImportModalComponent {
  @Input() promptType: PromptType = PromptType.TEXT;
  @Output() importUseCases = new EventEmitter<any>();
  accept = '.json,.xlsx,.xls';
  selectedFile: File | null = null;
  fileList: NzUploadFile[] = [];
  importModalCloseSubscription: Subscription;
  importErrMsgSubscription: Subscription;
  variables: string = '';
  errMsg: string = '';
  public lang = CommonUtils.getLanguage();

  constructor(
    private variableService: VariableService,
    private promptOptimizeService: PromptOptimizeService,
    private useCaseService: UseCaseService,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    private modalRef: NzModalRef,
    private commonLogic: agentCommonLogic
  ) {
    this.importModalCloseSubscription = this.useCaseService.importModalClose$.subscribe(() => {
      this.dismiss();
    });
    this.importErrMsgSubscription = this.useCaseService.importErrMsg$.subscribe(msg => {
      this.errMsg = msg;
      this.cdr.markForCheck();
    });
    this.variables = this.variableService
      .getVariables()
      .map(item => {
        return item.value;
      })
      .join('、');
  }

  ngOnInit(): void {
    if (this.promptType !== 'text') {
      this.accept = '.json,.xlsx,.xls,.zip';
    }
  }

  ngOnDestroy(): void {
    this.importModalCloseSubscription.unsubscribe();
    this.importErrMsgSubscription.unsubscribe();
  }

  close(): void {
    this.useCaseService.closeImportModal();
  }

  dismiss(): void {
    this.modalRef.destroy();
  }

  handleCancel(): void {
    this.useCaseService.closeImportModal();
  }

  beforeUpload = (file: NzUploadFile): boolean => {
    this.selectedFile = file as unknown as File;
    this.fileList = [file];
    this.errMsg = '';
    this.cdr.markForCheck();
    return false;
  };

  onRemove = (): boolean => {
    this.selectedFile = null;
    this.fileList = [];
    this.errMsg = '';
    this.cdr.markForCheck();
    return true;
  };

  downloadTemplate() {
    this.promptOptimizeService.downLoadTemplate(this.promptType).then(res => {
      CommonUtils.downloadFile(
        new Blob([res], {
          type: 'application/zip',
        }),
        'template.zip',
        true
      );
    });
  }

  confirm(): void {
    this.importUseCases.emit({ _file: this.selectedFile });
  }

  protected readonly changeUrl = cdnAssetUrl;
}
