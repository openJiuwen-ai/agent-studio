import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import * as angularI18next from 'angular-i18next';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { NzModalService } from 'ng-zorro-antd/modal';
import { AppLibraryRepoService } from '@services/app-library/app-library-repo.service';
import { CommonService } from '@services/common.service';
import { CommonUtils } from 'src/utils/common.util';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import {
  MARKET_TYPE,
  OFFICIAL_TYPE,
  SHARE_CARD_MENU_TYPE,
  SHARE_TYPE,
  ShareTypeTag,
} from '@routes/app-center/app-center-management/app-center-management.config';
import { ShareService } from '../edit-share-modal/share.service';
import {
  SHARE_PAGE,
  SHARE_TOOL_TYPE,
} from '../edit-share-modal/edit-share-modal.config';
import { ShareDeleteModalComponent } from '../share-delete-modal/share-delete-modal.component';
import { HttpService } from '@services/http.service';
import { PipesModule } from '../../../../pipes/pipes.module';
import { CardService } from '@routes/agent-center/my-card/card.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { Subject, takeUntil } from 'rxjs';
import { PermissionService } from '@services/permission.service';
import { CardOperatorService } from '@shared/services/card-operator.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { AgentConfigService } from "@routes/agent-center/agent-config.service";

enum mapKeys {
  typeTabs = 'typeTabs',
  from = 'from'
}
const OTHER_HEIGHT = 272;
const MAX_HEIGHT = 1270;

@Component({
  selector: 'meta-app-center-cards',
  templateUrl: './app-center-cards.component.html',
  styleUrls: ['./app-center-cards.component.scss'],
  standalone: true,
  imports: [
    COMMON_MODULES,
    MODULES,
    NewCommonNoDataWithBtnComponent,
    PipesModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
  ],
})
export class AppCenterCardsComponent implements OnInit, OnDestroy {
  // 首页需要按需展示
  @Input() isShowDom: boolean = true;
  @Input() appTabs = [];
  @Input() limit: number = -1;
  @Input() offset: number = -1;
  @Input() isFromOverview: boolean = false;
  @Input() selectType: any;
  @Input() isFresh: boolean = false;
  @Output() clear = new EventEmitter();

  activeTabId = MARKET_TYPE.OFFICIAL;
  shareTypeSelect = '';
  typeSelect = '';
  appTagId = '';
  keyword = '';
  otherShare = true;
  hasMore = true;
  public isLodingCard = false;
  public currentCardPage = 1;
  public totalCardNumber = 0;
  public noData = false;
  public cardPageSize: any = {
    options: [24, 48, 64],
    size: 24,
  };
  public cardList: Array<any> = [];
  public lang = CommonUtils.getLanguage();
  public workflowType = {
    ['chat']: this.i18n.transform('chat'),
    ['task']: this.i18n.transform('task'),
  };
  public agentType = {
    ['agent']: this.i18n.transform('single_agent'),
    ['controller']: this.i18n.transform('multiple_agent'),
  };

  shareMenus = [
    {
      label: this.i18n.transform('app_center_cards_1'),
      id: SHARE_CARD_MENU_TYPE.CANCEL_SHARE,
    },
  ];
  public controller = new AbortController();
  public controllerShare = new AbortController();
  public controllerMyShare = new AbortController();
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  public currentPermissions: any;
  private isShare = false;
  protected ngUnsubscribe: Subject<void>;
  public quotaLimit = 0;
  public isHC = false;

  get activeTabIsOfficial() {
    return this.activeTabId === MARKET_TYPE.OFFICIAL;
  }

  constructor(
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private router: Router,
    private activatedRoute: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private service: AppLibraryRepoService,
    private commonService: CommonService,
    private shareService: ShareService,
    private cardService: CardService,
    private nzModalService: NzModalService,
    private readonly http: HttpService,
    private permissionService: PermissionService,
    private cardOperatorService: CardOperatorService,
    public configServ: AgentConfigService,
    private sidebarServ: SetSidebarVisibilityService,
  ) {
    this.http.getCurrentUserResourceStatus().subscribe((res) => {});
    this.ngUnsubscribe = new Subject();
    this.isShare = this.activatedRoute.snapshot.queryParams.isShare === 'true';
  }

  ngOnInit(): void {
    this.sidebarServ.setSidebarsVisibilityByState('hideSidebar');
    this.permissionService.permissions$
      .pipe(takeUntil(this.ngUnsubscribe))
      .subscribe((permissions) => {
        this.currentPermissions = permissions;
        if (this.activeTabIsOfficial && this.cardList?.length) {
          this.cardList.forEach((item) => {
            const menuItem = item.shareMenus?.find(
              (item) => item.id === SHARE_CARD_MENU_TYPE.COPY_TO_WORK,
            );
            if (menuItem) {
              menuItem.disabled = this.getCopyToWorkDisabled();
              item.shareMenus = [...item.shareMenus];
            }
          });
        }
      });
  }

  ngOnDestroy(): void {
    this.sidebarServ.setSidebarsVisibilityByState('destroy');
    this.ngUnsubscribe.next();
    this.ngUnsubscribe.complete();
  }

  cardInit(listParams: any) {
    if (window.innerHeight - OTHER_HEIGHT > MAX_HEIGHT) {
      this.cardPageSize.size = this.cardPageSize.options[1];
    } else {
      this.cardPageSize.size = this.cardPageSize.options[0];
    }
    const {
      activeTabId,
      shareTypeSelect,
      typeSelect,
      appTagId,
      keyword,
      activeShareTabId,
    } = listParams;
    this.typeSelect = typeSelect;
    this.appTagId = appTagId;
    this.keyword = keyword;
    this.activeTabId = activeTabId;
    this.shareTypeSelect = shareTypeSelect;
    this.isLodingCard = false;
    this.currentCardPage = 1;
    this.totalCardNumber = 0;
    this.noData = false;
    this.cardList = [];
    this.otherShare = activeShareTabId === SHARE_TYPE.OTHER_SHARE;
    this.getCardList();
  }

  public getCardList(isNeedLoading: boolean = false) {
    if (this.activeTabIsOfficial) {
      this.getAppList();
    } else {
      this.getShareList();
    }
  }

  public onCurrentPageChange(): void {
    this.getCardList();
  }

  public filterAppTagId(type: any) {
    return type?.map((tag: string) =>
      this.appTabs.find((item: any) => item.tag_id === tag),
    );
  }

  public resourceTypeTag(type: any) {
    if (
      type === OFFICIAL_TYPE.Agent ||
      type === SHARE_TOOL_TYPE.multipleAgent
    ) {
      return this.agentType[type];
    } else {
      return this.workflowType[type];
    }
  }

  public getQuotaTag(type: any, isHC: boolean) {
    return null;
  }

  public toCardDetail(item: any) {
    if (!this.subscribeBtnStatus) {
      return;
    }
    const appId = item.resource_id || '';
    const queryParams: any = {
      appId,
    };
    if (this.isFromOverview) {
      queryParams[mapKeys.from] = 'overview';
    }
    if (this.activeTabId === MARKET_TYPE.SHARE) {
      queryParams.isShare = true;
      queryParams.releaseVersion = item.version_id;
    }
    if (item.resource_type === OFFICIAL_TYPE.Agent) {
      // 智能体
      this.router.navigate([`home/app-library/knowledge-bot`], {
        queryParams,
      });
    } else if (item.resource_type === OFFICIAL_TYPE.workflow) {
      // 工作流 对话型 任务型
      if (item.workflow_type === 'chat') {
        this.router.navigate([`home/app-library/flow/knowledge-bot`], {
          queryParams,
        });
      } else {
        this.router.navigate([`home/app-library/scenario-bot/scene/${appId}`], {
          queryParams,
        });
      }
    } else if (item.resource_type === SHARE_TOOL_TYPE.multipleAgent) {
      queryParams.isMultipleAgent = true;
      // 去多智能体
      this.router.navigate([`home/app-library/flow/knowledge-bot`], {
        queryParams,
      });
    }
  }

  public handleClickClearData() {
    this.clear.emit();
  }

  public shareMenuOnClick(event: Event, data: any): void {
    event.stopPropagation();
  }

  private getReferList(data) {
    const param = {
      offset: 0,
      limit: 100,
      reference_type: 'share',
      resource_type: data.resource_type,
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
      .finally(() => {});
  }

  private delShareMoal(data) {
    this.nzModalService.confirm({
      nzTitle: this.i18n.transform('app_center_cards_3'),
      nzContent: this.i18n.transform('app_center_cards_2'),
      nzOkText: this.i18n.transform('ok'),
      nzOnOk: () => {
        this.delShare(data);
      },
    });
  }

  private openShareDelModal(data) {
    const modal = this.nzModalService.create({
      nzTitle: '',
      nzFooter: null,
      nzWidth: 700,
      nzClosable: false,
      nzMaskClosable: false,
      nzContent: ShareDeleteModalComponent,
    });
    modal.componentInstance.shareData = data;
    modal.componentInstance.pageType = SHARE_PAGE.apply;
    modal.afterClose.subscribe((result) => {
      if (result) {
        this.getCardList();
      }
    });
  }

  private delShare(data) {
    this.shareService
      .deleteShare(data.resource_id, {
        resource_type: data.resource_type,
      })
      .then((res) => {
        this.getCardList();
      });
  }

  public shareMenuSelect($event, event: any, data: any): void {
    if (event.id === SHARE_CARD_MENU_TYPE.CANCEL_SHARE) {
      // 取消共享应用
      $event.stopPropagation();
      this.getReferList(data);
      return;
    }

    //复制到当前空间
    if (event.id === SHARE_CARD_MENU_TYPE.COPY_TO_WORK) {
      const type = data.resource_type === 'workflow' ? 'workflow' : 'agent';
      this.cardOperatorService.copyToWorkbench(
        data.resource_id,
        type
      );
      return;
    }

    if (event.id === SHARE_CARD_MENU_TYPE.INFO) {
      this.toCardDetail(data);
    }
  }

  getAppList() {
    if (this.controllerShare) {
      this.controllerShare.abort();
    }
    if (this.controllerMyShare) {
      this.controllerMyShare.abort();
    }
    if (this.controller) {
      this.controller.abort();
    }
    this.controller = new AbortController();
    const params = {
      source: this.typeSelect, //'workflow'
      tag_id: this.appTagId,
      name: this.keyword,
    };
    this.isLodingCard = true;
    if (this.limit >= 0) {
      this.currentCardPage = this.limit;
    }
    if (this.offset >= 0) {
      this.cardPageSize.size = this.offset;
    }
    this.service
      .getAppCenterList(
        params,
        ((this.currentCardPage || 1) - 1) * (this.cardPageSize.size as number),
        this.cardPageSize.size as number,
        this.controller.signal,
      )
      .then(
        (res) => {
          const data = res || {};
          this.isLodingCard = false;
          this.totalCardNumber = data.count || 0;
          this.noData = data.count === 0;
          const isHC = false;
          const cardList = data.app_list || [];
          cardList.forEach((v) => {
            v.freeQuota = true
            v.resourceTag = this.resourceTypeTag(v.resource_type);
            v.quotaTag = this.getQuotaTag(v, false);
            v.showTags = this.filterAppTagId(v.tags);
            if (!this.isShare) {
              v.shareMenus = [
                {
                  label: this.i18n.transform('app_center_cards_7'),
                  id: SHARE_CARD_MENU_TYPE.INFO,
                  disabled: !this.subscribeBtnStatus,
                },
                {
                  label: this.i18n.transform('app_center_cards_6'),
                  id: SHARE_CARD_MENU_TYPE.COPY_TO_WORK,
                  disabled: !this.subscribeBtnStatus || this.getCopyToWorkDisabled(),
                },
              ];
            }
          });
          this.cardList.push(...cardList);
          this.currentCardPage++;
          this.hasMore =
            this.currentCardPage <
            Math.ceil(res.count / this.cardPageSize.size) + 1;
          this.isLodingCard = false;
          this.cdr.markForCheck();
          this.commonService.FurionReportCustomTime();
        },
        () => {
          this.isLodingCard = false;
          this.commonService.FurionReportCustomTime();
        },
      );
  }

  getShareList() {
    if (this.controllerShare) {
      this.controllerShare.abort();
    }
    if (this.controllerMyShare) {
      this.controllerMyShare.abort();
    }
    if (this.controller) {
      this.controller.abort();
    }
    this.controllerShare = new AbortController();
    this.controllerMyShare = new AbortController();
    if (this.limit >= 0) {
      this.currentCardPage = this.limit;
    }
    if (this.offset >= 0) {
      this.cardPageSize.size = this.offset;
    }
    const params = {
      tag_id: this.appTagId,
      resource_name: this.keyword,
      offset:
        ((this.currentCardPage || 1) - 1) * (this.cardPageSize.size as number),
      limit: this.cardPageSize.size as number,
      resource_type: this.typeSelect,
    };
    this.isLodingCard = true;
    const req = this.otherShare
      ? this.shareService.getShareList(params, this.controllerShare.signal)
      : this.shareService.getMyShareList(params, this.controllerMyShare.signal);
    req.then(
      (res) => {
        this.isLodingCard = false;
        this.totalCardNumber = res.count;
        this.noData = res.count === 0;
        const cardList = res.resource_list || [];
        this.cardList.length = 0;
        cardList?.forEach((v) => {
          v.icon = v.resource_icon;
          v.description = v.resource_desc;
          v.name = v.resource_name_ch;
          if (v.resource_type === OFFICIAL_TYPE.workflow) {
            v.workflow_type = v.type;
          } else {
            v.resourceTag = this.resourceTypeTag(v.resource_type);
          }
          v.showTags = this.filterAppTagId(v.tags);
          v.shareTag = ShareTypeTag('');
          if (!this.otherShare) {
            this.shareMenus.forEach((btn: any) => {
              btn.disabled = !this.subscribeBtnStatus;
            });
            v.shareMenus = [this.shareMenus[0]];
          }
          v.version_id = v.version_info_list?.[0].version_id;
          v.version_name = v.version_info_list?.[0].version_name;
        });
        this.cardList.push(...cardList);
        this.currentCardPage++;
        this.hasMore =
          this.currentCardPage <
          Math.ceil(res.count / this.cardPageSize.size) + 1;
        this.isLodingCard = false;
        this.commonService.FurionReportCustomTime();
      },
      () => {
        this.isLodingCard = false;
        this.commonService.FurionReportCustomTime();
      },
    );
  }

  loadMore(): void {
    if (this.isLodingCard || !this.hasMore) {
      return;
    }

    this.isLodingCard = true;
    this.getCardList();
  }

  onScroll(): void {
    const scrollableElement = document.querySelector('.card-container');
    if (scrollableElement) {
      const { scrollTop, scrollHeight, clientHeight } = scrollableElement;
      if (scrollHeight - (scrollTop + clientHeight) < 100) {
        this.loadMore();
      }
    }
  }
  private getCopyToWorkDisabled(): boolean {
    return Boolean(
      this.currentPermissions?.OPERATOR || !this.subscribeBtnStatus,
    );
  }
}
