import { Component, EventEmitter, Input, Output } from "@angular/core";
import { MODULES } from "@shared/modules";
import { I18nNamespace } from "@i18n";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { MessageComponent } from '@shared/services/cfdata.service';
import { DeleteRefsService } from "@shared/services/delete-refs.service";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { NzDrawerService } from "ng-zorro-antd/drawer";
import { ShareVersionComponent } from "../share-version/share-version.component";
import { EditShareModalComponent } from "../edit-share-modal/edit-share-modal.component";
import { SHARE_PAGE, SHARE_TOOL_TYPE } from "../edit-share-modal/edit-share-modal.config";
import { InlineSvgComponent } from "@shared/components/inline-svg.component";
import { ShareDeleteModalComponent } from "../share-delete-modal/share-delete-modal.component";
import { ShareReferenceComponent } from "../share-reference/share-reference.component";
import { ShareService } from "../edit-share-modal/share.service";
import { CardService } from "@routes/agent-center/my-card/card.service";
import { Router } from "@angular/router";
import { NzModalService } from "ng-zorro-antd/modal";

@Component({
  selector: "share-detail-btn",
  templateUrl: "./share-detail-btn.component.html",
  styleUrl: "./share-detail-btn.component.scss",
  standalone: true,
  imports: [MODULES, InlineSvgComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    },
    DeleteRefsService
  ]
})
export class ShareDetailBtnComponent {
  @Input() shareInfo: any;
  @Input() toolId = "";
  @Input() versionId = "";
  @Input() visionsList = [];
  @Input() pageType: SHARE_PAGE = SHARE_PAGE.apply;
  @Input() toolType: SHARE_TOOL_TYPE = SHARE_TOOL_TYPE.workflow;
  @Output() changeVersion = new EventEmitter();
  @Output() updateShare = new EventEmitter();
  @Output() changeShearVersion = new EventEmitter();
  public historyIcon = cdnAssetUrl(
    "assets/agent-center/icons/release-history.svg"
  );

  public selectedTab = -1;

  constructor(
    private i18n: I18NextEagerPipe,
    private nzDrawerService: NzDrawerService,
    private shareService: ShareService,
    private cardService: CardService,
    private router: Router,
    private modalService: NzModalService
  ) {
  }

  ngOnInit(): void {
  }

  getReference() {
    this.nzDrawerService.create<ShareReferenceComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzExtra: "Extra",
      nzContent: ShareReferenceComponent,
      nzWidth: 700,
      nzContentParams: {
        toolId: this.toolId,
        versionId: this.versionId,
        pageType: this.pageType,
        toolType: this.toolType,
        shareInfo: this.shareInfo
      }
    });
  }

  getHistory() {
    const drawerRef = this.nzDrawerService.create<ShareVersionComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzExtra: "Extra",
      nzContent: ShareVersionComponent,
      nzWidth: 500,
      nzContentParams: {
        toolId: this.toolId,
        versionId: this.versionId,
        pageType: this.pageType,
        shareInfo: this.shareInfo,
        visionsList: this.visionsList
      }
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();

      // 监听子组件Output事件
      instance.changeVersion.subscribe((id: string) => {
        this.changeVersion.emit(id);
      });

      instance.changeShearVersion.subscribe((id: string) => {
        this.changeShearVersion.emit(id);
      });

    });
  }

  private getReferList(data) {
    const param = {
      offset: 0,
      limit: 100,
      reference_type: "share",
      resource_type: data.resource_type === SHARE_PAGE.plugin ? "tool" : data.resource_type
    };
    this.cardService
      .selectQuoteList(data.resource_id, param)
      .then((res) => {
        let count = res.count;
        if (count) {
          this.openShareDelModal(data);
        } else {
          this.delShareMoal(data);
        }
      })
      .finally(() => {
      });
  }

  private delShareMoal(data) {
    this.modalService.confirm({
      nzTitle: this.i18n.transform("shared_model_tip1"),
      nzOnOk: (): void => {
        this.delShare(data);
      }
    });
  }

  private openShareDelModal(data) {
    const modal = this.modalService.create({
      nzTitle: "",
      nzFooter: null,
      nzWidth: 700,
      nzClosable: false,
      nzMaskClosable: false,
      nzContent: ShareDeleteModalComponent
    });
    modal.componentInstance.shareData = data;
    modal.componentInstance.pageType = this.pageType;
    modal.afterClose.subscribe((result) => {
      if (result) {
        this.backHome();
      }
    });
  }

  private delShare(data) {
    this.shareService.deleteShare(data.resource_id, {
      resource_type: data.resource_type
    }).then((res) => {
      this.backHome();
    });
  }


  deleteShare() {
    this.getReferList(this.shareInfo);
  }

  deleteShareItem() {
    this.shareService.deleteShare(this.toolId, {
      resource_type: this.shareInfo.resource_type
    }).then((res) => {
      MessageComponent.showSuccess(
        this.i18n.transform("delete_success"),
        3000
      );
    }).finally(() => {
      this.backHome();
    });
    // 返回列表
    // 删除共享应用
  }

  editShare() {
    const drawerRef = this.nzDrawerService.create({
      nzTitle: "",
      nzFooter: null,
      nzWidth: 500,
      nzClosable: false,
      nzMaskClosable: false,
      nzPlacement: "right",
      nzContent: EditShareModalComponent,
      nzContentParams: {
        sharePage: this.pageType,
        shareInfo: this.shareInfo,
        isEdit: true
      }
    });
    drawerRef.afterClose.subscribe(() => {
      // handle after close if needed
    });
  }

  backHome() {
    if (this.shareInfo.resource_type === SHARE_PAGE.plugin) {
      this.router.navigate(["/home/plugin-market"], {
        state: {
          formTab: "share",
          myShare: true
        }
      });
    } else {
      this.router.navigate(["/home/app-library"], {
        state: {
          formTab: "share",
          myShare: true
        }
      });
    }
  }
}
