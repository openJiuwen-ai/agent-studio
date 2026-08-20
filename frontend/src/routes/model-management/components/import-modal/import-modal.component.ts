import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import {
  ModelManagementService,
  ModelImportPreviewRsp,
  ModelImportRsp,
} from '@services/repositories/model-management-new';
import { NZ_MODAL_DATA, NzModalRef } from 'ng-zorro-antd/modal';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzUploadModule, NzUploadFile } from 'ng-zorro-antd/upload';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzMessageService } from 'ng-zorro-antd/message';

type ConflictStrategy = 'SKIP' | 'COVER';

/**
 * 模型批量导入弹窗：上传 .jsonl → 预检（解析+验签+冲突检测）→ 选冲突策略 → 确认导入 → 结果。
 * 鉴权 MASKED：导入后 authInfo 为空，需在目标环境重新配置鉴权（提示于预检阶段）。
 */
@Component({
  selector: 'meta-model-import-modal',
  imports: [
    CommonModule,
    FormsModule,
    MODULES,
    NzButtonModule,
    NzUploadModule,
    NzRadioModule,
    NzTableModule,
    NzTagModule,
    NzSpinModule,
    NzIconModule,
  ],
  templateUrl: './import-modal.component.html',
  styleUrls: ['./import-modal.component.scss'],
  standalone: true,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.MODEL_ACCESS],
    },
  ],
})
export class ModelImportModalComponent {
  fileName = '';
  fileSize = 0;
  private file: File | null = null;

  previewLoading = false;
  preview: ModelImportPreviewRsp | null = null;

  importLoading = false;
  importRsp: ModelImportRsp | null = null;

  /** 是否曾成功导入过（即便后续重传文件清空了 importRsp，父组件仍据此决定是否刷新列表）。 */
  private hasImported = false;

  /** 预检请求序号：丢弃过期响应，避免快速连续选文件导致预检结果与当前文件不匹配。 */
  private previewSeq = 0;

  conflictStrategy: ConflictStrategy = 'SKIP';

  /** 详情页只导模型导入时，传入的目标供应商 id；列表页导入时不传（走供应商+模型 upsert）。 */
  get targetProviderId(): string | undefined {
    return this.nzData?.targetProviderId;
  }

  constructor(
    private modelManagementService: ModelManagementService,
    private modalRef: NzModalRef,
    private message: NzMessageService,
    public i18n: I18NextEagerPipe,
    @Inject(NZ_MODAL_DATA) public nzData: any
  ) {}

  beforeUpload = (file: NzUploadFile): boolean => {
    const raw: File = (file as any).originFileObj ?? (file as unknown as File);
    const name = raw.name || file.name || '';
    if (!name.toLowerCase().endsWith('.jsonl')) {
      this.message.error(this.i18n.transform('import_model_file_type_invalid'));
      return false;
    }
    this.file = raw;
    this.fileName = name;
    this.fileSize = raw.size || 0;
    this.preview = null;
    this.importRsp = null;
    this.runPreview();
    return false;
  };

  runPreview() {
    const file = this.file;
    if (!file) {
      return;
    }
    // 客户端预校验：读首行 JSON 判文件类型，与当前入口匹配——
    // (1) 只导模型文件（provider_metadata 缺失）不能在列表页（无 targetProviderId）导入，
    //     否则模型会以源空间 providerId 落库成孤儿；
    // (2) 供应商+模型文件（provider_metadata 非空）不能在详情页（有 targetProviderId）导入，
    //     否则 target 被静默忽略、模型挂到文件自带供应商而非当前页供应商。
    // 命中即拦并提示，免去后端预检往返。**文件类型由 provider_metadata 是否存在区分（文件固有内容），
    // 不依赖后端是否序列化 model_only 标记**——即便后端未重启（旧导出文件无 model_only），前端仍能自洽拦截。
    this.detectContextMismatch(file).then(mismatchKey => {
      if (mismatchKey) {
        this.message.error(this.i18n.transform(mismatchKey));
        return;
      }
      this.callPreview(file);
    });
  }

  /**
   * 读文件首行，判文件类型与当前入口是否匹配；不匹配返回对应 i18n key，匹配返回 null。
   * 文件类型由 provider_metadata 是否存在区分（只导模型文件无该字段；供应商+模型文件有），
   * 不依赖后端 model_only 标记，自洽。
   * - 列表页（targetProviderId 空）+ provider_metadata 缺失 → 只导模型误入列表页
   * - 详情页（有 target）+ provider_metadata 非空 → 供应商+模型误入详情页
   * 解析失败/无 payload → 返回 null，交后端预检。
   */
  private async detectContextMismatch(file: File): Promise<string | null> {
    const detailPage = !!this.targetProviderId;
    try {
      const text = await file.text();
      const firstLine = text.split('\n').find(l => l.trim().length > 0);
      if (!firstLine) {
        return null;
      }
      const line = JSON.parse(firstLine);
      const payload = line?.payload;
      if (!payload) {
        return null;
      }
      // == null 同时覆盖 undefined（字段缺失）与 null（显式空），两种都意味着无供应商元数据=只导模型文件
      const isModelOnly = payload.provider_metadata == null;
      if (!detailPage && isModelOnly) {
        return 'import_model_only_requires_target';
      }
      if (detailPage && !isModelOnly) {
        return 'import_model_provider_requires_list';
      }
      return null;
    } catch {
      return null; // 非法 JSON / 格式异常交后端预检报错
    }
  }

  private callPreview(file: File) {
    const seq = ++this.previewSeq;
    this.previewLoading = true;
    this.modelManagementService
      .previewImportModels(file, this.targetProviderId)
      .then(res => {
        if (seq !== this.previewSeq) {
          return; // 过期响应，丢弃
        }
        this.preview = res;
      })
      .catch(() => {
        if (seq !== this.previewSeq) {
          return;
        }
        this.message.error(this.i18n.transform('import_model_preview_failed'));
      })
      .finally(() => {
        if (seq === this.previewSeq) {
          this.previewLoading = false;
        }
      });
  }

  get canConfirm(): boolean {
    if (!this.preview || this.preview.total_count <= 0 || this.importRsp) {
      return false;
    }
    const items = this.preview.items || [];
    // 任意条目 cipher_adapted===false 时禁止导入（当前环境无法解密）
    const hasCipherMismatch = items.some(i => i.cipher_adapted === false);
    // 任意条目 signature_valid===false（行级校验失败：只导模型误入列表页/验签失败/格式错）禁止导入，
    // 与后端守卫一致——避免用户对预检失败行点确认。
    const hasInvalidLine = items.some(i => i.signature_valid === false);
    return !hasCipherMismatch && !hasInvalidLine;
  }

  confirmImport() {
    const file = this.file;
    if (!file) {
      this.message.warning(this.i18n.transform('import_model_select_file_first'));
      return;
    }
    this.importLoading = true;
    this.modelManagementService
      .importModels(file, this.conflictStrategy, this.targetProviderId)
      .then(res => {
        this.importRsp = res;
        this.hasImported = true;
        const succeed = res.succeed_len ?? 0;
        const failed = res.failed_len ?? 0;
        const skipped = res.skipped_len ?? 0;
        const hasError = failed > 0;
        const tip = hasError
          ? this.i18n.transform('import_model_partial_tip', { succeed, failed, skipped })
          : this.i18n.transform('import_model_success_tip', { succeed, skipped });
        if (hasError) {
          this.message.warning(tip);
        } else {
          this.message.success(tip);
        }
      })
      .catch(() => {
        this.message.error(this.i18n.transform('import_model_failed'));
      })
      .finally(() => {
        this.importLoading = false;
      });
  }

  close() {
    // 返回是否曾成功导入，供父组件决定是否刷新列表（即便用户导入后重传文件清空了 importRsp）。
    this.modalRef.close(this.hasImported);
  }
}
