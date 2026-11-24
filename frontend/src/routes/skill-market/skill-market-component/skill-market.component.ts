import { CommonModule } from '@angular/common';
import { Component, DestroyRef, ElementRef, inject, ViewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { finalize, fromEvent, sampleTime, Subscription, tap } from 'rxjs';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzModalService } from 'ng-zorro-antd/modal';
import { SkillApi } from '@agentcore/api/skill.api';
import { PublishAssetModalComponent } from '@routes/agent-center/component-library/shelf-modal/publish-asset-modal.component';
import { I18N_NAMESPACE } from '@agentcore/constants/common';
import { SKILL_RESOURCE_TYPE_CONFIG, SkillDetail, SkillDetailFromPage, SkillResourceType } from '@agentcore/constants/skill.model';
import { i18nProviderValue, I18nService } from '@agentcore/core/i18n.service';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { SpaceTeamManagementService } from '@services/space-team-management.service';
import { ContextService } from '@services/context.service';
import { PromptService } from '@services/prompt.service';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { CommonUtils } from 'src/utils/common.util';

@Component({
  selector: 'skill-market',
  templateUrl: './skill-market.component.html',
  styleUrls: ['./skill-market.component.less'],
  standalone: true,
  imports: [
    NzIconModule,
    NzEmptyModule,
    NzTabsModule,
    NzInputModule,
    NzButtonModule,
    NzTagModule,
    NzSpinModule,
    NzSelectModule,
    CommonModule,
    FormsModule,
    I18nPipe,
  ],
  providers: [
    I18nService,
    {
      provide: I18NEXT_NAMESPACE,
      useValue: i18nProviderValue([I18N_NAMESPACE.Skill]),
    },
  ],
})
export class SkillMarketComponent {
  cardHovered = '';
  @ViewChild('scrollContainer') scrollContainer: ElementRef;
  resourceConfig = SKILL_RESOURCE_TYPE_CONFIG;
  // 分类由后端 t_pe_industry（library_type='skill'）下发，前端不硬编码 ID（#1731）；
  // tabs 动态构建：初始仅"全部"，ngAfterViewInit 拉取后端分类追加；skillTagMap 供卡片 tagId→name 展示
  tabs: { id: string; title: string; active?: boolean }[] = [
    {
      id: SkillResourceType.ALL,
      title: this._i18n.transform(SKILL_RESOURCE_TYPE_CONFIG.all.i18key),
      active: true,
    },
  ];

  selectedTab = this.tabs.find(e => e.active) ?? this.tabs[0];
  // 后端分类 id→分类对象（卡片展示用，替代硬编码 resourceConfig[tagId] 查不到的问题）
  skillTagMap: Record<string, AssertSquareTagType> = {};
  tags: Array<{ label: string; value: string }> = [];
  searchValue = '';
  cards: SkillDetail[] = [];
  loading = false;
  destroyRef = inject(DestroyRef);
  filter: Record<string, any> = {};
  hasFilter = false;
  loadSub: Subscription;
  total = 0;
  public activeTabIndex = 0;
  public canPublish = true;
  constructor(
    private _router: Router,
    private _skillApi: SkillApi,
    private _i18n: I18nService,
    private nzModal: NzModalService,
    private spaceTeamManagementService: SpaceTeamManagementService,
    private ctxServ: ContextService,
    private promptService: PromptService
  ) {}

  openPublishModal(): void {
    this.nzModal.create({
      nzContent: PublishAssetModalComponent,
      nzWidth: 560,
      nzTitle: this._i18n.transform('plaza_onshelf'),
      nzFooter: null,
      nzData: {
        assetType: 'skill',
        onPublished: () => {
          // 上架成功后清空列表重载首页（loadMore 为滚动分页，直接调用会按旧 offset 追加，新条目在第一页不会出现）
          this.cards = [];
          this.total = 0;
          this.loadMore();
        },
      },
    });
  }

  unpublishSkill(card: SkillDetail): void {
    // 下架前查引用：存量引用会因下架失效，引用确认让用户知情（方案 B，#1733）
    // queryReference 默认 catchError 吞错返空，故查询失败时 count=0 走无引用通用确认，不阻塞下架
    this._skillApi
      .queryReference(card.skillId, 0, 100, { showFailMessage: false })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((res: any) => this.confirmUnpublish(card, res?.relations || [], res?.count || 0));
  }

  /**
   * 下架二次确认：有引用时动态文案展示引用方数量与名称，无引用走通用确认。
   * 下架是全局生效（published_asset=0 后存量引用解析失败），故引用数量须在下架前展示。
   * 组件 ns 限定 skill/common，plaza_* 文案在 agent-center 命名空间，故显式传 ns。
   */
  private confirmUnpublish(card: SkillDetail, relations: any[], count: number): void {
    const agentCenterNs = { ns: I18nNamespace.AGENT_CENTER };
    const commonNs = { ns: I18nNamespace.COMMON };
    const confirmTitle =
      count > 0
        ? this.buildReferenceWarningTitle(relations, count, agentCenterNs)
        : this._i18n.transform('plaza_offshelf_confirm', agentCenterNs);
    this.nzModal.confirm({
      nzTitle: confirmTitle,
      nzOkText: this._i18n.transform('plaza_offshelf', agentCenterNs),
      // cancel 在 common 命名空间，组件 ns 含 common 默认可访问；显式传 ns 防御 ns 解析差异
      nzCancelText: this._i18n.transform('cancel', commonNs),
      nzOkDanger: true,
      nzOnOk: () => {
        this._skillApi
          .unpublishSkill(card.skillId)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe(() => {
            this.cards = [];
            this.loadMore();
          });
      },
    });
  }

  /**
   * 构造引用提示文案：分类计数（workflow/agent，基于 relations）+ count 总数兜底
   * （count>relations.length 时显示"共 count 个引用"，因 limit 截断时分类计数不全但总数准）
   * + 名称用 relations 前 3 个 app_name，分隔符走 i18n（zh=、 en=, ）避免硬编码顿号。
   * app_type 实测值为 'agent'/'workflow'（后端 MappingEntity.app_type）。
   */
  private buildReferenceWarningTitle(relations: any[], count: number, ns: { ns: I18nNamespace }): string {
    const workflowCount = relations.filter(r => r?.app_type === 'workflow').length;
    const agentCount = relations.filter(r => r?.app_type === 'agent').length;
    const separator = this._i18n.transform('plaza_offshelf_referenced_name_separator', ns);
    const names = relations
      .map(r => r?.app_name)
      .filter((n): n is string => !!n)
      .slice(0, 3)
      .join(separator);
    const summary = this._i18n.transform('plaza_offshelf_referenced_summary', {
      ...ns,
      workflow: workflowCount,
      agent: agentCount,
    });
    // count>relations.length 说明 relations 被 limit 截断，分类计数不全，补总数兜底
    const total = count > relations.length
      ? this._i18n.transform('plaza_offshelf_referenced_total', { ...ns, count })
      : '';
    const tail = names
      ? this._i18n.transform('plaza_offshelf_referenced_names', { ...ns, names })
      : this._i18n.transform('plaza_offshelf_referenced_no_names', ns);
    return `${this._i18n.transform('plaza_offshelf_referenced_prefix', ns)}${summary}${total}${tail}`;
  }

  ngAfterViewInit() {
    this.watchLatest();
    this.loadMore();
    this.checkPublishPermission();
    this.loadSkillTags();
  }

  /**
   * 从后端拉取 Skill 分类（t_pe_industry, library_type='skill'），动态追加筛选 tab + 填充 tagId→分类映射。
   * #1731：前端不硬编码分类 ID；上架写入与筛选查询同源（同一套后端分类 id）。
   */
  private loadSkillTags(): void {
    this.promptService
      ?.getAssertTagAsync({ library_type: 'skill' })
      .then((res: AssertSquareTagType[]) => {
        (res || []).forEach(tag => {
          this.tabs.push({ id: tag.id, title: this.tagName(tag) });
          this.skillTagMap[tag.id] = tag;
        });
      })
      .catch(() => {});
  }

  /** 按当前语言取分类名（#1731 巡检2：对齐 plugin-market:320 isZH 口径，name_en 缺失兜底 name） */
  private tagName(tag: AssertSquareTagType | undefined): string {
    if (!tag) {
      return '';
    }
    return this.isZH() ? tag.name : (tag.name_en || tag.name);
  }

  /** 卡片 tagId → 分类名（skillTagMap 存对象，按语言取 name/name_en） */
  tagNameById(tagId: string | undefined): string {
    if (!tagId) {
      return '';
    }
    return this.tagName(this.skillTagMap[tagId]);
  }

  isZH(): boolean {
    return CommonUtils.getLanguage() === 'zh-cn';
  }

  async checkPublishPermission() {
    try {
      const res = await this.spaceTeamManagementService.getWorkspaceDetial(this.ctxServ.currentWorkspaceId);
      if (res?.type === 'TEAM' && res?.role && res.role !== 'OWNER' && res.role !== 'ADMIN') {
        this.canPublish = false;
      }
    } catch {
      this.canPublish = false;
    }
  }

  onActiveChange(index: number): void {
    const tab = this.tabs[index];
    this.selectedTab = this.tabs.find(e => e.id === tab.id);
    this.refresh();
  }

  loadMore() {
    if (this.cards.length === 0 || this.cards.length < this.total) {
      this.loading = true;
      this.loadSub && this.loadSub?.unsubscribe();
      this.loadSub = this._skillApi
        .queryResourceSkill({
          offset: this.cards.length,
          limit: 100,
          tagId: this.selectedTab?.id === SkillResourceType.ALL ? undefined : this.selectedTab?.id,
          name: this.filter?.name,
          description: this.filter?.description,
        })
        .pipe(
          tap(res => {
            this.total = res.total;
            this.cards = this.cards.concat(res.items);
          }),
          finalize(() => {
            this.loading = false;
          }),
          takeUntilDestroyed(this.destroyRef)
        )
        .subscribe();
    }
  }

  watchLatest() {
    fromEvent(this.scrollContainer.nativeElement, 'scroll')
      .pipe(sampleTime(100), takeUntilDestroyed(this.destroyRef))
      .subscribe((event: any) => {
        this.checkScroll(event.target);
      });
  }

  getTitleLabel() {
    return this.cards.length
      ? this._i18n.transform('skill.resource.title.count', { title: this.selectedTab.title, count: this.cards.length })
      : this.selectedTab.title;
  }

  onClear() {
    this.searchValue = '';
    this.filter = {};
    this.hasFilter = false;
    this.refresh();
  }

  onNgModelChange(e) {
    this.filter = {};
    if (this.searchValue) {
      this.filter.name = this.searchValue;
    }
    this.hasFilter = Object.keys(this.filter).length > 0;
    this.refresh();
  }

  gotoDetail(card) {
    this._router.navigate(['/home/skill/detail'], {
      queryParams: {
        from: SkillDetailFromPage.RESOURCE,
        id: card.skillId,
      },
    });
  }

  refresh() {
    this.cards = [];
    this.loadMore();
  }

  private checkScroll(target: HTMLElement) {
    // 关键公式：可视高度 + 滚动距离 >= 实际内容总高度
    const threshold = 50; // 预留 50px 缓冲区，提前加载
    const isAtBottom = target.scrollTop + target.clientHeight >= target.scrollHeight - threshold;
    if (isAtBottom) {
      this.loadMore();
    }
  }
}
