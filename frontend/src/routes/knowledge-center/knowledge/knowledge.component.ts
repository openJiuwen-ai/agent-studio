import { Location } from '@angular/common';
import { Component, inject, OnDestroy, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzModalService, NzModalModule } from 'ng-zorro-antd/modal';
import { NzDrawerService, NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzBreadCrumbModule } from 'ng-zorro-antd/breadcrumb';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDescriptionsModule } from 'ng-zorro-antd/descriptions';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { KB_DEFAULT_ICON_BASE64_STR } from '@routes/agent-center/app-knowledge/create-knowledge/default-icon-base64';
import { IKnowledge } from '@routes/agent-center/app-knowledge/knowledge.types';
import {
  KB_SCOPE_MAP,
  knowledgeBaseStatusMap,
} from '@routes/knowledge-center/knowledge-base-list/knowledge-base-list.map';
import { KBStatus } from '@routes/knowledge-center/knowledge-base.interface';
import { KbTagManageComponent } from '@routes/knowledge-center/knowledge/kb-tag-management/kb-tag-manage.component';
import {
  ObsSettingModalComponent,
} from '@routes/knowledge-center/knowledge/obs-setting-modal/obs-setting-modal.component';
import { ReferenceModalComponent } from '@routes/knowledge-center/knowledge/reference-modal/reference-modal.component';
import { AgentCenterHomeService } from '@services/agent-center/agent-center-home.service';
import { KnowledgeRepoService } from '@services/agent-center/knowledge.service';
import { KbAbilitiesService } from '@services/knowledge-center/kb-abilities.service';
import { KbOperationFilterService } from '@services/knowledge-center/kb-operation-filter.service';
import { MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subscription } from 'rxjs';
import { BytesPipe } from 'src/pipes/bytes.pipe';
import { KnowledgeFormDrawerComponent } from '../knowledge-form-drawer/knowledge-form-drawer.component';
import { KBScope, ModalType } from '../knowledge.types';
import { cdnAssetUrl } from '../../../single-spa/assets-url';
import { DocumentComponent } from './document/document.component';
import { FAQDocumentComponent } from './faq-document/faq-document.component';
import { FAQComponent } from './faq/faq.component';
import { TaskManageComponent } from './task-manage/task-manage.component';
import { CommonService } from '@services/common.service';
import { PipesModule } from "../../../pipes/pipes.module";

export interface TpLink {
  label: string;
  key?: string;
}

@Component({
  selector: 'meta-knowledge',
  templateUrl: './knowledge.component.html',
  styleUrls: ['./knowledge.component.less'],
  standalone: true,
  imports: [
    MODULES,
    BytesPipe,
    DocumentComponent,
    FAQComponent,
    FAQDocumentComponent,
    TaskManageComponent,
    ObsSettingModalComponent,
    PipesModule,
    KbTagManageComponent,
    NzBreadCrumbModule,
    NzButtonModule,
    NzIconModule,
    NzToolTipModule,
    NzDescriptionsModule,
    NzTabsModule,
    NzSpinModule,
    NzModalModule,
    NzDrawerModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.KNOWLEDGE,
        I18nNamespace.AGENT_CENTER,
      ],
    },
    NzMessageService,
    NzModalService,
    NzDrawerService
  ],
})
export class KnowledgeComponent implements OnInit, OnDestroy {
  @ViewChild('obsSettingModal') obsSettingModalRef: any;
  @ViewChild('documentCom') documentCom:any;
  showObsConfig = false;
  crumbItems: Array<TpLink> = [
    {
      label: this.i18n.transform('my_knowledge_base'),
      key: 'list',
    },
    {
      label: this.i18n.transform('knowledge_base_details'),
    },
  ];
  public kbId = '';
  public isOpenJiuwen = false;

  public bytes = new BytesPipe();

  public kb: IKnowledge = {
    knowledge_repo_id: '',
    display_name: '',
    name: '',
    id: '',
    description: '',
    size: 0,
    creator: '',
    create_time: '',
    update_time: '',
    icon: KB_DEFAULT_ICON_BASE64_STR,
    status: null,
    update_user_name: '',
    workspace_id: '',
    share_scope: KBScope.SELF,
  };
  public isLoading = false;
  public selectedIndex = 0;
  public tabs: any[] = [
    {
      title: 'knowledge_file',
      active: true,
    },
  ];
  public count = 0;
  protected readonly knowledgeBaseStatusMap = knowledgeBaseStatusMap;
  #routeQuery;
  chunkMethod = '';
  public kbScope: KBScope;
  public isMarket: boolean = false;
  routeUnsub: Subscription;
  kbOperationFilterService = inject(KbOperationFilterService);

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private kbRepoServ: KnowledgeRepoService,
    private ppServ: AgentCenterHomeService,
    private nzMessage: NzMessageService,
    private nzModal: NzModalService,
    private nzDrawerService: NzDrawerService,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    private setSidebarVisibilityService: SetSidebarVisibilityService,
    private location: Location,
    private commonService: CommonService,
    public kbAbilitiesService: KbAbilitiesService,
  ) {
    this.route.queryParams.subscribe(param => {
      this.#routeQuery = param;
    });
  }

  public get statusDicts() {
    return KBStatus.CLOSE !== this.kb?.status
      ? {
        tag: 'status_open',
        btnName: 'button_close',
        btnIcon: 'pause-circle',
      }
      : {
        tag: 'status_close',
        btnName: 'button_open',
        btnIcon: 'play-circle',
      };
  }

  public get type() {
    return this.selectedIndex;
  }

  ngOnInit() {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('init');
    this.route.params.subscribe(async (params) => {
      this.kbId = params?.id ?? '';
      await this.getKb();
    });
    this.route.queryParams.subscribe((params) => {
      this.isMarket = params?.isMarket === 'true';
    }).unsubscribe();
    this.routeUnsub = this.route.queryParams.subscribe(() => {
      this.setCurrentActiveTab();
    });
    this.showObsConfig = this.configServ.knowledgeSource() !== 'AgentBaseRag' && !this.commonService.isSite();
  }

  goToTagManage() {
    const index = this.tabs.findIndex(tab => tab.title === 'kb_tag_management');
    if (index > -1) {
      this.selectedIndex = index;
      this.tabs.forEach((tab, i) => tab.active = i === index);
    }
  }

  get isGlobal() {
    return this.kbScope === KBScope.GLOBAL;
  }

  changeKbScope() {
    const scopeItem = KB_SCOPE_MAP.get(this.kb.share_scope);
    if (scopeItem) {
      this.nzModal.confirm({
        nzTitle: this.i18n.transform('confirm_cancel_shared_app'),
        nzContent: this.i18n.transform('share_kb_2'),
        nzOnOk: async () => {
          await this.kbRepoServ.changeKbScope(this.kbAbilitiesService.getKbId(this.kb), { share_scope: scopeItem.operationParam });
          this.nzMessage.success(`${this.i18n.transform(scopeItem.buttonName)}${this.i18n.transform('success')}`);
          this.kbScope = KBScope.SELF;
        }
      });
    }
  }

  ngOnDestroy(): void {
    this.setSidebarVisibilityService.setSidebarsVisibilityByState('destroy');
    this.ppServ.setImportRes({});
    this.kbAbilitiesService.kbConfig = null;
    this.routeUnsub?.unsubscribe();
  }

  public async handleStatusChange() {
    if (this.kbAbilitiesService.isResourceDisabled || (this.kb?.status === 'OPEN' && this.kb?.share_scope === 'GLOBAL')) {
      return;
    }
    const { status } = this.kb;
    const modalAdapter = {
      open: (options: any) => {
        this.nzModal.confirm({
          nzTitle: options.title,
          nzContent: options.content,
          nzOnOk: options.okButton.click
        });
      }
    };

    KBStatus.OPEN === status
      ? await this.kbRepoServ.handleKbStop(this.kbId)
      : await this.kbRepoServ.handleKbStart(this.kbId);
    await this.getKb();
  }

  public copyKnowledgeRepoId() {
    this.kbRepoServ.handleIdCopy(this.kb.knowledge_repo_id);
  }

  public async getKb() {
    try {
      this.isLoading = true;
      this.kb = await this.kbRepoServ.retrieveKb(this.kbId);
      this.kbScope = this.kb.share_scope;
      if (this.configServ.knowledgeSource() === 'AgentBaseRag') {
        this.chunkMethod = this.kb?.rag_chunk_parser_conf?.chunk_method || '';
      }
      // 判断是否为 OpenJiuwen 知识库
      this.isOpenJiuwen = this.configServ.openjiuwenKbEnable() && this.kb?.source?.knowledge_base_connector_id === 'OpenjiuwenInside';
      // 添加 FAQ问答对、FAQ文档、任务管理标签页（OpenJiuwen 不支持）
      if (!this.isOpenJiuwen && this.configServ.faqEnable()) {
        const hasFaqTab = this.tabs.some(tab => tab.title === 'faq_tab');
        if (!hasFaqTab) {
          this.tabs.push(
            { title: 'faq_tab', active: false },
            { title: 'faq_file', active: false },
          );
        }
        if (!this.isMarket) {
          const hasTaskTab = this.tabs.some(tab => tab.title === 'task_manage');
          if (!hasTaskTab) {
            this.tabs.push({ title: 'task_manage', active: false });
          }
        }
      }
      this.setCurrentActiveTab();
      const tagTab = this.tabs.find(item => item.title === 'kb_tag_management');
      if (!this.isMarket && this.kbAbilitiesService.isSupTag(this.kb) && !tagTab) {
        this.tabs.push({
          title: 'kb_tag_management',
          active: false,
        })
        this.setCurrentActiveTab();
      }
    } finally {
      this.isLoading = false;
    }
  }

  private setCurrentActiveTab() {
    const { active } = this.route.snapshot.queryParams;
    if (active) {
      const index = this.tabs.findIndex((tab) => tab.title === active);
      if (index > -1) {
        this.selectedIndex = index;
        this.tabs.forEach((t) => (t.active = false));
        this.tabs[index].active = true;
      }
    }
  }

  public back() {
    if (this.kbAbilitiesService.isDevelopSpace) {
      (window as unknown as { developSpaceKnowledge: boolean }).developSpaceKnowledge = true;
    }
    if (this.#routeQuery.externalAdd && this.#routeQuery.previousUrl) {
      this.router.navigateByUrl(`${this.#routeQuery.previousUrl}&kbId=${this.kbId}`);
    } else {
      if (this.#routeQuery.previousUrl.includes('library-home')) {
        this.router.navigate(['/home/agent-center/library-home'], {
          queryParams: {
            tabId: 'knowledge',
          },
        });
      } else {
        this.location.back();
      }
    }
  }

  public toHitTesting() {
    this.router.navigate([`/home/knowledge-center/knowledge/${ this.kbId }/hit-testing`], {
      queryParams: {
        display_name: this.kb.display_name,
        id: this.kbId,
        isMarket: this.isMarket,
      },
    });
  }

  public async handleEdit(form) {
    const { icon, display_name, description } = form;
    return await this.kbRepoServ.modifyKb(this.kbId, {
      icon,
      display_name,
      description,
    });
  }

  public openHalfmodal(type: string) {
    const drawerRef = this.nzDrawerService.create({
      nzContent: KnowledgeFormDrawerComponent,
      nzWidth: '700px',
      nzMaskClosable: true,
      nzData: {
        type,
        formData: this.kb,
      },
    });

    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      if (instance) {
        instance.submitForm.subscribe(async (ctx: any) => {
          const { form, setConfirmLoading } = ctx;
          try {
            setConfirmLoading(true);
            ModalType.EDIT === type
              ? await this.handleEdit(form)
              : await this.kbRepoServ.modifyKb(this.kbId, form);
            await this.delay(1000);
            this.nzMessage.success(this.i18n.transform('update_success'));
            drawerRef.close();
            await this.getKb();
          } finally {
            setConfirmLoading(false);
          }
        });
        instance.cancelForm.subscribe(() => drawerRef.close());
      }
    });
  }

  public openReference() {
    this.nzDrawerService.create({
      nzContent: ReferenceModalComponent,
      nzWidth: '900px',
      nzMaskClosable: true,
      nzData: {
        kbId: this.kbId,
      },
    });
  }

  public openObsSettings() {
    this.obsSettingModalRef.open();
  }

  public onTabChange(index: number) {
    this.selectedIndex = index;
    this.tabs.forEach((t, i) => (t.active = i === index));
    this.handleTabChange(this.tabs[index]);
  }

  public handleTabChange(tab) {
    const { title, active } = tab;
    if (!active) {
      return;
    }
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        active: title,
      },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  crumbSelect(item) {
    if (item.key === 'list') {
      this.back();
    }
  }

  refreshDocument() {
    if (this.documentCom?.gridRef) {
      this.documentCom.gridRef.refreshGridData();
    }
  }

  private delay(time: number) {
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        clearTimeout(timer);
        resolve(null);
      }, time);
    });
  }

  protected readonly cdnAssetUrl = cdnAssetUrl;
}
