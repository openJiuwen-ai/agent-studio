import { CommonModule } from "@angular/common";
import { Component } from "@angular/core";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";

import { NzMessageService } from "ng-zorro-antd/message";
import { NzModalRef } from "ng-zorro-antd/modal";
import { NzUploadModule, NzUploadFile } from "ng-zorro-antd/upload";

import { I18nNamespace } from "@i18n";
import { MODULES } from "@shared/modules";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { WorkflowImportQuery } from "../../app-flow.types";
import { DifyMigrateModalComponent } from "../dify-migrate-modal/dify-migrate-modal.component";
import { DifyMigrateService } from "@routes/agent-center/app-flow/components/dify-migrate-modal/dify-migrate.service";
import { NzDrawerService } from "ng-zorro-antd/drawer";

@Component({
  selector: "dify-import-modal",
  templateUrl: "./dify-import-modal.component.html",
  styleUrl: "./dify-import-modal.component.less",
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    NzUploadModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER
      ]
    }
  ]
})
export class DifyImportModalComponent {

  public fileInfo: File;
  public fileList: NzUploadFile[] = [];
  public maxSize = 128 * 1024 * 1024;
  public uploadType = ".yml";
  public isAnalyzing = false;

  constructor(
    private i18n: I18NextEagerPipe,
    private appFlowRepoService: AppFlowRepoService,
    private difyMigrateService: DifyMigrateService,
    private messageService: NzMessageService,
    private modalRef: NzModalRef,
    public drawerServ: NzDrawerService
  ) {
  }

  public dismiss() {
    this.modalRef.close();
  }

  public importTool() {
    this.isAnalyzing = true;
    const query: WorkflowImportQuery = { type: "Dify" };
    const formData = new FormData();
    formData.append("file", this.fileInfo);

    this.appFlowRepoService.importParseWorkFlow(query, formData).then(res => {
      // 解析失败时保留弹窗以便重试。
      this.difyMigrateService.setParseDsl(res);
      this.dismiss();
      const halfComNodes = this.difyMigrateService.halfCompatible.nodes;
      const notComNodes = this.difyMigrateService.notCompatible.nodes;

      if (
        !halfComNodes?.length
        && !notComNodes?.length
      ) {
        this.difyMigrateService.createWorkFlow();
      } else {
        const width = halfComNodes.some(node => node.type === "Code")
          ? "1200px" : "900px";
        this.drawerServ.create({
          nzTitle: this.i18n.transform("dify_migrate_label"),
          nzWidth: width,
          nzPlacement: "right",
          nzHeight: "auto",
          nzClosable: true,
          nzMaskClosable: false,
          nzContent: DifyMigrateModalComponent
        });
      }
    }).catch(() => {
      // 显式提示，避免静默失败。
      this.messageService.error(
        this.i18n.transform(`${I18nNamespace.AGENT_CENTER}:imported_failed_dify_tip`)
      );
    }).finally(() => {
      this.isAnalyzing = false;
    });
  }

  public onAddItemFailed(error: { type: string; msg: string }) {
    if (error.type === "type") {
      this.messageService.error(
        this.i18n.transform("only_support_upload_format", { types: this.uploadType })
      );
    }
    if (error.type === "size") {
      this.messageService.error(
        this.i18n.transform("file_size_cannot_exceed", { size: this.maxSize / (1024 * 1024) })
      );
    }
  }

  public onRemove = (file: NzUploadFile): boolean => {
    this.fileInfo = null;
    this.fileList = [];
    return true;
  };

  public beforeUpload = (file: NzUploadFile): boolean => {
    const isYml = file.name?.endsWith(".yml") || file.name?.endsWith(".yaml");
    if (!isYml) {
      this.messageService.error(
        this.i18n.transform("only_support_upload_format", { types: this.uploadType })
      );
      return false;
    }
    const isOverSize = file.size! > this.maxSize;
    if (isOverSize) {
      this.messageService.error(
        this.i18n.transform("file_size_cannot_exceed", { size: this.maxSize / (1024 * 1024) })
      );
      return false;
    }
    this.fileInfo = file as unknown as File;
    this.fileList = [file];
    return false;
  };
}
