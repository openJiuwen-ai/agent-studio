import { ChangeDetectorRef, Component, EventEmitter, Input, OnInit, Output, Inject } from "@angular/core";
import { NzDrawerRef, NZ_DRAWER_DATA } from "ng-zorro-antd/drawer";
import { I18nNamespace } from "@i18n";
import { AgentConfigService } from "@routes/agent-center/agent-config.service";
import { KbCardDisplayComponent } from "@routes/knowledge-center/components/kb-card-display/kb-card-display.component";
import { knowledgeBaseStatusMap } from "@routes/knowledge-center/knowledge-base-list/knowledge-base-list.map";
import {
  KbCardDisplayConfig,
  KBCardOperation,
  KbCardOperationType,
  type KbItem,
  KbShareTargetType,
  KBStatus,
  KbTagType,
  KBType
} from "@routes/knowledge-center/knowledge-base.interface";
import { KBRepoType, KBScope, KnowledgeBaseType } from "@routes/knowledge-center/knowledge.types";
import { KnowledgeRepoService } from "@services/agent-center/knowledge.service";
import { KbAbilitiesService } from "@services/knowledge-center/kb-abilities.service";
import { MODULES } from "@shared/modules";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { NzMessageService } from "ng-zorro-antd/message";

@Component({
  selector: "knowledge-base-selector",
  templateUrl: "./knowledge-base-selector.component.html",
  styleUrls: ["./knowledge-base-selector.component.less"],
  standalone: true,
  imports: [MODULES, KbCardDisplayComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.AGENT
      ]
    }
  ]
})
export class KnowledgeBaseSelectorComponent implements OnInit {
  @Input({
    required: false
  }) isPermitCreate = true;

  @Input({
    required: false
  }) existedKbs: string[] = [];

  @Input({
    required: false
  }) pageSize = 10;

  @Input({
    required: false
  }) kbStatusLimit: KBStatus | null = KBStatus.OPEN;

  @Input({
    required: false
  }) beforeSelect: (kb: KbItem, selectedKbs: KbItem[]) => boolean;

  @Input({
    required: false
  }) limit = 0;

  @Output() createKB = new EventEmitter();

  @Output() addKB = new EventEmitter();

  @Output() selectedChange = new EventEmitter<KbItem[]>();

  public drawerWidth = "700px";

  public kbQuantityLimit = 1;

  public kbTypeOptions: Array<any> = [
    {
      label: this.i18n.transform("default"),
      value: KBType.INTERNAL
    },
    {
      label: this.i18n.transform("third_party"),
      value: KBType.EXTERNAL
    }
  ];

  // CUSTOM 模式下的知识库类型下拉选项
  public kbTypeOptionsForCustom: Array<any> = [
    {
      label: '个人知识库',
      value: KnowledgeBaseType.PERSONAL
    },
    {
      label: '企业知识库',
      value: KnowledgeBaseType.ENTERPRISE
    }
  ];

  public searchState: {
    kbType: "";
    searchName: string;
    knowledgeBaseType: number | null;
  } = {
    kbType: null,
    searchName: "",
    knowledgeBaseType: null
  };

  public kbs: KbItem[] = [];

  public pageState = {
    currentPage: 1,
    totalNumber: 0,
    pageSize: 10
  };

  public selectedKbs: KbItem[] = [];

  public isLoading = false;

  public knowledgeBaseSourceMap = new Map([
    ["internal", { label: this.i18n.transform("default"), color: "#1476FF" }],
    ["external", { label: this.i18n.transform("third_party"), color: "#029931" }]
  ]);

  tabs: {
    title: string,
    active: boolean,
    id: string,
    value: null | string,
    onActiveChange: (isActive: boolean) => void,
  }[] = [
    {
      title: this.i18n.transform("kb_self_space"),
      active: true,
      id: "currentSpace",
      value: null,
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.currentTab = this.tabs[0];
          this.getKBList();
        }
      }
    },
    {
      title: this.i18n.transform("kb_share_space"),
      active: false,
      id: "shareSpace",
      value: KbShareTargetType.OTHER_SHARED,
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.currentTab = this.tabs[1];
          this.getKBList();
        }
      }
    }
  ];

  currentTab = this.tabs[0];

  cardDisplayConfig: KbCardDisplayConfig = {
    cardSize: "small",
    cardNameBold: false,
    descriptionConfig: {
      enable: true,
      maxLine: 1
    },
    layoutConfig: {
      layout: "flex",
      flexQuantities: 2
    },
    tagsConfig: {
      enable: [KbTagType.INVALID, KbTagType.TYPE],
      tagSize: "small"
    },
    operationConfig: {
      enable: true
    }
  };

  studioBtnShow = true;

  constructor(
    public configServ: AgentConfigService,
    public i18n: I18NextEagerPipe,
    private kbRepo: KnowledgeRepoService,
    public kbAbilitiesService: KbAbilitiesService,
    private cdr: ChangeDetectorRef,
    private drawerRef: NzDrawerRef,
    private message: NzMessageService,
    @Inject(NZ_DRAWER_DATA) private modalData: any
  ) {

  }

  public get currentSpaceType() {
    return this.currentTab.id;
  }

  public get isCustomSource() {
    return this.configServ.knowledgeSource() === 'CUSTOM';
  }

  public get currentTabValue() {
    return this.currentTab.value;
  }

  public get selectedIds() {
    return this.selectedKbs.map(kb => kb.id);
  }

  ngOnInit() {
    this.pageState.pageSize = this.pageSize;

    // 默认全局config加载完毕
    if (this.limit) {
      this.kbQuantityLimit = this.limit;
    } else {
      this.kbQuantityLimit = this.configServ.getConfigs()?.agent_knowledge_bound_limit ?? this.kbQuantityLimit;
    }

    this.studioBtnShow = this.configServ.getConfigs()?.studio_btn_show;

    // CUSTOM 模式下，默认选中"个人知识库"
    if (this.isCustomSource) {
      this.searchState.knowledgeBaseType = KnowledgeBaseType.PERSONAL;
    }

    this.getKBList();
    this.existedKbs = this.modalData?.existedKbs || [];
    if (this.existedKbs.length) {
      this.getExistedKbs(this.existedKbs);
    }
  }

  public getKBInSearch() {
    this.pageState.currentPage = 1;
    this.getKBList();
  }

  public getKBList() {
    const params: any = {
      name: this.searchState.searchName,
      type: this.searchState.kbType,
      ...(this.isCustomSource && this.searchState.knowledgeBaseType != null
        && { knowledge_base_type: this.searchState.knowledgeBaseType }),
    };
    this.isLoading = true;
    this.kbRepo.getKnowledgeBaseList({
      ...params,
      status: this.kbStatusLimit,
      offset: (this.pageState.currentPage - 1) * this.pageState.pageSize,
      limit: this.pageState.pageSize,
      share_type: this.currentTabValue
    }).then(
      (res) => {
        this.isLoading = false;
        this.kbs = this.kbAbilitiesService.normalizeKBList(res.items ?? []);
        this.pageState.totalNumber = res?.total ?? 0;
        this.cdr.detectChanges();
      },
      (err: any) => {
        this.message.error(
          `${this.i18n.transform("failed_knowledge_reason")}${
            err?.data?.error_msg
          }`);
        this.isLoading = false;
        this.cdr.detectChanges();
      }
    );
  }

  public getExistedKbs(kbIds: string[]) {
    this.kbRepo.getKnowledgeBaseList({
      knowledge_base_ids: kbIds,
      offset: (this.pageState.currentPage - 1) * this.pageState.pageSize,
      limit: this.pageState.pageSize,
      share_scope: KBScope.ALL
    }).then(
      (res) => {
        this.selectedKbs = [...this.selectedKbs, ...this.kbAbilitiesService.normalizeKBList(res.items ?? [])];
        this.cdr.detectChanges();
      }
    );
  }

  cardHandler(cardEvent: KBCardOperation) {
    const { kb, type } = cardEvent;
    if (type === KbCardOperationType.SELECT_CHANGE) {
      this.toggleKbSelected(kb);
    }
  }

  public toggleKbSelected(kb: KbItem) {
    if (kb.selected) {
      this.cancelSelect(kb);
    } else {
      this.selectKB(kb);
    }
  }

  public selectKB(kb: KbItem) {
    this.selectedKbs = [...this.selectedKbs, this.kbs.find(kbItem => kb.id === kbItem.id)];
    this.change();
  }

  public cancelSelect(kb: KbItem) {
    this.selectedKbs = this.selectedKbs.filter(kbItem => kbItem.id !== kb.id);
    this.cdr.detectChanges();
    this.change();
  }

  public get sharedKbLimitSelection() {
    const freeEditionKB = this.selectedKbs.find(kb => kb.repo_type === KBRepoType.SHARE);
    if (freeEditionKB) {
      return this.selectedKbs.length > 0;
    }
    return false;
  }

  private change() {
    this.selectedChange.emit(this.selectedKbs);
  }

  dismiss() {
    this.drawerRef?.close();
  }

  close() {
    this.addKB.emit();
    this.drawerRef?.close();
  }

  protected readonly knowledgeBaseStatusMap = knowledgeBaseStatusMap;
}
