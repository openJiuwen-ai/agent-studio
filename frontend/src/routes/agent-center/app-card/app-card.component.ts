import { Clipboard } from "@angular/cdk/clipboard";
import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  HostBinding,
  Input,
  OnInit,
  Output,
  ViewChild,
  ViewContainerRef
} from "@angular/core";
import { Router } from "@angular/router";
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { I18nNamespace } from "@i18n";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { MODULES } from "@shared/modules";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { environment } from "src/environment/environment";
import { removeHTMLTag } from "src/utils/utils";
import { InlineSvgComponent } from "@shared/components/inline-svg.component";
import { TabIndex } from "@services/agent-center/agent-center-home.service";
import { ApplicationType } from "@enums/agent-center.enum";
import { DeleteRefsService } from "@shared/services/delete-refs.service";
import { ContextService } from "@services/context.service";
import {
  CopyToASpaceComponent
} from "@routes/agent-center/components/copy-to-a-sapce/copy-to-a-space.component";
import { AppExceedModalComponent } from "@routes/knowledge-center/components/app-exceed-modal/app-exceed-modal.component";
import { CommonService } from "@services/common.service";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { HttpService } from "@services/http.service";
import { FormateTimePipe } from "src/pipes/formate-time.pipe";
import { CommonUtils } from "src/utils/common.util";
import { AppAgentHighCodeService } from "@services/agent-center/app-agent-high-code.service";
import { ExportResultModalComponent } from "@shared/components/export-modal/export-result-modal/export-result-modal.component";
import { NzModalService } from "ng-zorro-antd/modal";

export interface CardAction {
  id: string;
  label: string;
  disabled?: boolean;
  tipContent?: string;
}

enum mapKeys {
  "from" = "from",
}

@Component({
  selector: "application-card",
  templateUrl: "./app-card.component.html",
  styleUrls: ["./app-card.component.less"],
  imports: [MODULES, InlineSvgComponent, AppExceedModalComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER]
    },
    NzModalService,
    DeleteRefsService,
    FormateTimePipe
  ]
})
export class AppCardComponent implements OnInit {
  @Input() type = 0;
  @Input() data: any;
  @Input() isFromDevelopSpace = false;
  @Input() cardIndex: Number;
  @Output() handleAction = new EventEmitter();
  @HostBinding("style.width") width = "";
  @Input() isFromOverview: boolean = false;

  @Input() activedTab: number = 0;
  @Input() exportEnable = false;

  @ViewChild("appNumExceedModal")
  appNumExceedModal: AppExceedModalComponent;

  channelType = {
    WEB_PAGE: this.i18n.transform("webpage"),
    CLOUD_STORE: this.i18n.transform("cloud_store")
  };
  public cardActions: CardAction[] = [];
  public visibleActions: CardAction[] = [];
  public overflowActions: CardAction[] = [];
  private readonly MAX_VISIBLE_ACTIONS = 3;
  public isOpAccount = false;
  TabIndex = TabIndex;
  public channelTypeNew = [];

  public get isApplication() {
    return (
      this.type === TabIndex.SINGLE_AGENT || this.type === TabIndex.MULTI_AGENT
    );
  }

  public get status() {
    if (this.isApplication) {
      return this.data.status === "published" ? "submitted" : "not_submitted";
    }
    if (this.type === TabIndex.HIGH) {
      return this.data.status === "deploy" ? "deployed" : "not_deployed";
    }
    return this.data.status === 1 ? "submitted" : "not_submitted";
  }

  public get statusColor() {
    return ["submitted", "deployed"].includes(this.status) ? "green" : "orange";
  }

  public get appTagIcon() {
    const { type } = this.data;

    const iconMaps = {
      [ApplicationType.MULTI_AGENT]: "cloudx-action-modelarts",
      [ApplicationType.SINGLE_AGENT]: "cloudx-action-cloud-up",
      [ApplicationType.CHAT_WORKFLOW]: "cloudx-action-information"
    };
    return iconMaps[type] || "cloudx-action-object";
  }

  public get appType() {
    const { type } = this.data;

    const typeMaps = {
      [ApplicationType.MULTI_AGENT]: "multiple_agent",
      [ApplicationType.SINGLE_AGENT]: "single_agent",
      [ApplicationType.CHAT_WORKFLOW]: "workflow_chat",
      [ApplicationType.AGENT_NEW]: "agent_new"
    };
    return typeMaps[type] || "workflow_task";
  }

  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  public lang = CommonUtils.getLanguage();

  constructor(
    private router: Router,
    private service: AppAgentRepoService,
    private flowServ: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private clipboard: Clipboard,
    private deleteRefsServe: DeleteRefsService,
    private ctxServ: ContextService,
    private nzModal: NzModalService,
    private commonService: CommonService,
    private configServ: AgentConfigService,
    private readonly http: HttpService,
    private formateTimePipe: FormateTimePipe,
    private highCodeService: AppAgentHighCodeService,
    protected cdr: ChangeDetectorRef,
    private viewContainerRef: ViewContainerRef
  ) {
    this.isOpAccount = this.ctxServ.isOpAccount;
    this.http.getCurrentUserResourceStatus().subscribe(res => {
      this.initCardActions();
      this.cdr.markForCheck();
    });
  }

  ngOnInit(): void {
    this.initCardActions();
  }

  ngOnChanges() {
    this.initCardActions();
  }

  initCardActions() {
    this.cardActions = [
      {
        id: "deploy",
        label: this.i18n.transform("deploy"),
        disabled: !this.subscribeBtnStatus || this.data?.status !== "published"
      },
      {
        id: "releaseChannel",
        label: this.i18n.transform("channel_mgmt"),
        tipContent: this.i18n.transform("please_submit_version"),
        disabled: !this.subscribeBtnStatus || (this.data?.status !== "published" && this.data?.status !== 1)
      },
      {
        id: "copy",
        label: this.i18n.transform("copy"),
        disabled: !this.subscribeBtnStatus
      },
      {
        id: "call",
        label: this.i18n.transform("call_path"),
        disabled: !this.subscribeBtnStatus || (this.data?.status !== "published" && this.data?.status !== 1)
      },
      {
        id: "copyID",
        label: this.i18n.transform("replication_id"),
        disabled: !this.subscribeBtnStatus
      },
      {
        id: "export",
        label: this.i18n.transform("export"),
        disabled: !this.subscribeBtnStatus || !this.exportEnable
      },
      {
        id: "delete",
        label: this.i18n.transform("deletion"),
        disabled: !this.subscribeBtnStatus
      }
    ];

    if (!this.configServ.getConfigs().agentops_deploy_display) {
      this.cardActions = this.cardActions.filter((item) => item.id !== "deploy");
    }

    if (["hcs", "hcso"].includes(environment.envType)) {
      this.cardActions = this.cardActions.filter((item) => item.id !== "call");
    }
    if (this.isApplication || !this.isOpAccount) {
      this.cardActions = this.cardActions.filter((item) => item.id !== "customizeNode");
    }
    if (this.type === TabIndex.HIGH) {
      this.cardActions = this.cardActions.filter((item) => ["copyID", "delete"].includes(item.id));
    }
    if (this.type !== TabIndex.SINGLE_AGENT) {
      this.cardActions = this.cardActions.filter((item) => item.id !== "releaseChannel");
    }
    this.splitActions();
  }

  private splitActions(): void {
    this.visibleActions = this.cardActions.slice(0, this.MAX_VISIBLE_ACTIONS);
    this.overflowActions = this.cardActions.slice(this.MAX_VISIBLE_ACTIONS);
  }

  onMouseLeave(): void {
    const element = document.getElementById(this.cardIndex + "area-menu");
    element.style.removeProperty("display");
    const element1 = document.getElementById(this.cardIndex + "area");
    element1.style.removeProperty("display");
  }

  public clickMenu(e: Event, data) {
    if (data?.customize_node) {
      this.cardActions.forEach((item) => {
        if (item.id === "customizeNode") {
          item.label = this.i18n.transform("remove_node");
        }
      });
    }
    e.stopPropagation();
  }

  public moreClick(isOpen: boolean) {
    if (isOpen) {
      const element = document.getElementById(this.cardIndex + "area-menu");
      element.style.display = "inline-block";
      const element1 = document.getElementById(this.cardIndex + "area");
      element1.style.display = "none";
    } else {
      const element = document.getElementById(this.cardIndex + "area-menu");
      element.style.removeProperty("display");
      const element1 = document.getElementById(this.cardIndex + "area");
      element1.style.removeProperty("display");
    }

  }

  private async copy_model() {
    const isExceed = await this.isResourceExceed();
    if (isExceed) {
      return;
    }

    const modal = this.nzModal.create<CopyToASpaceComponent, any>({
      nzTitle: null,
      nzFooter: null,
      nzContent: CopyToASpaceComponent,
      nzViewContainerRef: this.viewContainerRef,
      nzData: {
        favoriteLibrary: "angular",
        favoriteFramework: "angular"
      },
      nzOnOk: () => {
        this.new_copy(modal.getContentComponent().space_value);
      }
    });
  }

  async isResourceExceed() {
    const resourceType = ["agent", "workflow", "controller"];
    const res = await this.service.getResourceQuantity(
      resourceType[this.activedTab]
    );
    if (res) {
      const { isExceedLimit, totalAmount } = res;
      if (isExceedLimit) {
        const params = { totalAmount };
        this.appNumExceedModal.show(params);
        return Promise.resolve(true);
      }
    }
    return Promise.resolve(false);
  }

  private async copy() {
    this.isApplication
      ? await this.service.copyAgent(this.data.agent_id)
      : await this.flowServ.copyFlow(this.data.workflow_id, "");
    MessageComponent.showSuccess(this.i18n.transform("copy_successful"));
    this.handleAction.emit({
      action: "copy"
    });
  }

  private async new_copy(target_space: string) {
    this.isApplication
      ? await this.service.copyAgentToASpace(this.data.agent_id, target_space)
      : await this.flowServ.copyFlow(this.data.workflow_id, target_space);
    MessageComponent.showSuccess(this.i18n.transform("copy_successful"));
    this.handleAction.emit({
      action: "copy"
    });
  }

  private copyID() {
    this.clipboard.copy(this.data.agent_id || this.data.workflow_id);
    MessageComponent.showSuccess(this.i18n.transform("id_copied_successfully"));
  }

  private toDel(): void {
    const { agent_id, workflow_id, name } = this.data;
    let deleteTitle = "";
    let resource_type = "";
    let deleteTipKey = "del_workflow_tip";
    if (this.type === TabIndex.SINGLE_AGENT) {
      deleteTitle = this.i18n.transform("delete_single_agent");
      resource_type = "agent";
      deleteTipKey = "del_single_agent_tip";
    } else if (this.type === TabIndex.WORKFLOW) {
      deleteTitle = this.i18n.transform("delete_workflow");
      resource_type = "workflow";
      deleteTipKey = "del_workflow_tip";
    } else if (this.type === TabIndex.MULTI_AGENT) {
      deleteTitle = this.i18n.transform("delete_multi_agent");
      resource_type = "controller";
      deleteTipKey = "del_multi_agent_tip";
    } else if (this.type === TabIndex.HIGH) {
      deleteTitle = this.i18n.transform("delete_high_agent");
      resource_type = "high";
    } else {
      deleteTitle = this.i18n.transform("delete_workflow");
      deleteTipKey = "del_workflow_tip";
    }
    this.deleteRefsServe.onDeleteRefs(
      {
        id: (this.isApplication || this.type === TabIndex.HIGH) ? agent_id : workflow_id,
        query: {
          resource_type
        }
      },
      {
        title: this.i18n.transform("del_workflow_version"),
        alertText: this.i18n.transform(deleteTipKey),
        secondConfirmLabel: `${this.i18n.transform(
          "del_sure_tips"
        )} <strong>DELETE</strong>`,
        tiMsgTitle: deleteTitle,
        tiMsgContent: this.i18n.transform("plugin_delete_content", {
          name: removeHTMLTag(name)
        }),
        isShowChinese: this.type === TabIndex.WORKFLOW
      },
      () => {
        if (this.type === TabIndex.HIGH) {
          this.deleteHighAgent(agent_id);
        } else if (this.isApplication) {
          this.deleteAgent(agent_id);
        } else {
          this.deleteWorkflow(this.isApplication ? agent_id : workflow_id);
        }
      }
    );
  }

  private getMsgTitle() {
    if (this.appType.indexOf("workflow") > -1) {
      return this.i18n.transform("delete_workflow");
    }
    if (this.appType.indexOf("single") > -1) {
      return this.i18n.transform("delete_single_agent");
    }
    if (this.appType.indexOf("multi") > -1) {
      return this.i18n.transform("delete_multi_agent");
    }
    return this.i18n.transform("delete_workflow");
  }

  private postDelAgent(modalInstance: any) {
    modalInstance.setLoading(false);
    modalInstance.close();
    MessageComponent.showSuccess(this.i18n.transform("deleted_successfully"));

    this.handleAction.emit({
      action: "delete"
    });
  }

  public onClickAction(event, action: CardAction) {
    event.stopPropagation();
    const { id } = action;
    const { url, status } = this.data;
    switch (id) {
      case "deploy":
        this.deploy();
        break;
      case "releaseChannel":
        this.handleDetailView(true);
        break;
      case "copy":
        this.copy_model();
        break;
      case "copyID":
        this.copyID();
        break;
      case "call":
        this.handleAction.emit({
          action: id,
          id: url,
          status
        });
        break;
      case "customizeNode":
        this.handleAction.emit({
          action: id,
          data: this.data
        });
        break;
      case "delete":
        this.toDel();
        break;
      case "export":
        this.export();
        break;
      default:
        break;
    }
    const element = document.getElementById(this.cardIndex + "area-menu");
    element.style.removeProperty("display");
    const element1 = document.getElementById(this.cardIndex + "area");
    element1.style.removeProperty("display");
  }

  deploy() {
    this.router.navigate(["/home/agent-observatory/agentDeployment"]);
  }

  public export() {
    const idMap = {
      agent: "agent_id",
      workflow: "workflow_id",
      controller: "agent_id"
    };
    let type = this.data.type;
    if (type === "chat" || type === "task") {
      type = "workflow";
    }
    this.service.newExportAgents({
      resource_type: type,
      resource_versions: [{ resource_id: this.data[idMap[type]] }]
    }).then(res => {
      this.nzModal.create<ExportResultModalComponent, any>({
        nzTitle: null,
        nzFooter: null,
        nzContent: ExportResultModalComponent,
        nzViewContainerRef: this.viewContainerRef,
        nzData: {
          exportResult: res
        }
      });
    });
  }

  public handleDetailView(isRelease?: boolean) {
    if (this.data.type === "agent_new") {
      this.router.navigate([`/home/spec-driven/${this.data.agent_id}`]);
      return;
    }
    if (this.data.type === "agent") {
      if (this.ctxServ.user.userId !== this.data.creator_id) {
        if (this.configServ.getConfigs().enable_edit_in_workspace === false) {
          return;
        }
      }
    }
    const cur_space_options_str = StorageService.getSessionStorage("CUR_SPACE_OPTIONS");
    let cur_space_id = "default";
    if (cur_space_options_str) {
      const cur_space_options = JSON.parse(
        StorageService.getSessionStorage("CUR_SPACE_OPTIONS")
      );
      cur_space_id = cur_space_options.id;
    }

    const { agent_id, workflow_id, type } = this.data;
    if (!this.isApplication) {
      const queryParams = {
        id: workflow_id,
        workspace_id: cur_space_id,
        tabId: isRelease ? "releaseManage" : ""
      };
      if (this.isFromDevelopSpace) {
        queryParams[mapKeys.from] = "develop-space";
      }
      if (this.isFromOverview) {
        queryParams[mapKeys.from] = "overview";
      }
      this.router.navigate([`/home/agent-center/app-flow/flow`], {
        queryParams: queryParams
      });
      return;
    }
    if (type === ApplicationType.MULTI_AGENT) {
      const queryParams = {
        id: agent_id,
        type: "multi",
        workspace_id: cur_space_id,
        tabId: isRelease ? "releaseManage" : ""
      };
      if (this.isFromDevelopSpace) {
        queryParams[mapKeys.from] = "develop-space";
      }
      if (this.isFromOverview) {
        queryParams[mapKeys.from] = "overview";
      }
      this.router.navigate(["/home/agent-center/app-flow/flow"], {
        queryParams: queryParams
      });
      return;
    }
    const queryParams = {
      agentId: agent_id,
      workspace_id: cur_space_id,
      tabId: isRelease ? "releaseManage" : ""
    };
    if (this.isFromDevelopSpace) {
      queryParams[mapKeys.from] = "develop-space";
    }
    if (this.isFromOverview) {
      queryParams[mapKeys.from] = "overview";
    }
    this.router.navigate(["/home/agent-center/app-agent/detail"], {
      queryParams: queryParams
    });
  }

  deleteAgent(agent_id) {
    this.service.deleteAgent(agent_id).then(() => {
      MessageComponent.showSuccess(this.i18n.transform("deleted_successfully"));
      this.handleAction.emit({
        action: "delete"
      });
    });
  }

  deleteHighAgent(agent_id) {
    this.highCodeService.deleteHighAgent(agent_id).then(() => {
      MessageComponent.showSuccess(this.i18n.transform("deleted_successfully"));
      this.handleAction.emit({
        action: "delete"
      });
    });
  }

  private deleteWorkflow(id: string) {
    this.flowServ.deleteFlow(id).then(() => {
      MessageComponent.showSuccess(
        this.i18n.transform("deleted_successfully"),
        3000
      );
      this.handleAction.emit({
        action: "delete"
      });
    });
  }

  getTagColor() {
    if (this.appType === "agent_new") {
      return "purple";
    }
    return "default";
  }

  getStatusNzColor(): string {
    return this.statusColor === "green" ? "success" : "warning";
  }

  getTime(time: any) {
    return this.formateTimePipe.transform(time, "YYYY/MM/DD");
  }

  public getPublishPath() {
    let { channel_type = [] } = this.data;
    this.channelTypeNew = channel_type.filter(item => item !== "APP_STORE");
    let labelMap = this.channelTypeNew.map(item => {
      return this.channelType[item];
    });
    return labelMap.join(" | ");
  }

  public getShowMaxNum() {
    let bottomArea = document.getElementById(this.cardIndex + "bottom-area-menu");
    if (!bottomArea) {
      return 3;
    }
    let inputWidth = bottomArea.offsetWidth;
    if (inputWidth < 420) {
      return this.lang === "zh-cn" ? 4 : 3;
    } else if (inputWidth < 480) {
      return this.lang === "zh-cn" ? 5 : 4;
    } else {
      return this.lang === "zh-cn" ? 6 : 4;
    }
  }

  onDisabledClick(event) {
    event.stopPropagation();
  }
}
