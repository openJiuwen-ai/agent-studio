import { Component, EventEmitter, Input, OnDestroy, OnInit, Output, ViewChild } from '@angular/core';

import { catchError, map, of, Subject, takeUntil } from 'rxjs';

import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzModalModule, NzModalService } from 'ng-zorro-antd/modal';
import { NzCheckboxModule } from 'ng-zorro-antd/checkbox';

import { MODULES } from '@shared/modules';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { SKILL_MAX_COUNT, SkillPublishedAsset, SkillStatus, SkillTabId } from '@enums/skill.enum';
import { CommonService } from '@services/common.service';
import { SkillApi } from '@agentcore/api/skill.api';
import { IMPORT_TYPE } from '@agentcore/constants/skill';
import { ImportSkillModalComponent } from '@agentcore/library/skill/import-skill-modal/import-skill-modal.component';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { I18nService } from '@agentcore/core/i18n.service';

import { SkillCardComponent } from './skill-card/skill-card.component';
import { ImportSkillButtonComponent } from '@agentcore/library/skill/import-skill-button/import-skill-button.component';
import { NewCommonNoDataWithBtnComponent } from "@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component";

@Component({
  selector: 'add-skill-halfmodal',
  templateUrl: './add-skill-halfmodal.component.html',
  styleUrls: ['./add-skill-halfmodal.component.scss'],
  standalone: true,
  imports: [MODULES, I18nPipe, SkillCardComponent, ImportSkillButtonComponent, NzDrawerModule, NzTabsModule, NzAlertModule, NzInputModule, NzButtonModule, NzIconModule, NzEmptyModule, NzSpinModule, NzToolTipModule, NzModalModule, NzCheckboxModule, NewCommonNoDataWithBtnComponent],
  providers: [I18nService, NzModalService],
})
export class AddSkillHalfModalComponent implements OnInit, OnDestroy {
  @Input() isFlowReadonly = false;
  @Output() batchAddSkill = new EventEmitter<any>();
  @ViewChild('skillModal') skillDrawer: any;

  public drawerVisible = false;
  public selectedItems: Array<any> = [];
  public canSelectedStatus: Array<SkillStatus> = [SkillStatus.DEVELOPED];
  public selectedIds: Array<string> = [];
  public skillSelectedIds: Array<string> = [];
  public skillsList: Array<any> = [];
  public skillTabs: any = [
    {
      id: SkillTabId.SKILL_MARKET,
      title: this.i18n.transform('skill.modal.tab.market'),
      active: true,
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.selectTab(SkillTabId.SKILL_MARKET);
        }
      },
    },
    {
      id: SkillTabId.SKILL_LIBRARY,
      title: this.i18n.transform('skill.modal.tab.library'),
      active: false,
      onActiveChange: (isActive: boolean): void => {
        if (isActive) {
          this.selectTab(SkillTabId.SKILL_LIBRARY);
        }
      },
    },
  ];
  public loading = false;
  public searchValue = '';
  public currentTab: SkillTabId = this.skillTabs[0].id;
  private destroy$ = new Subject<void>();
  private hasMore = true;
  private total = 0;
  private pageLimit = 100;

  get selectedSkills() {
    return this.i18n.transform('skill.modal.selected.skill', { num: this.selectedItems.length });
  }

  get isLibrary() {
    return this.currentTab === SkillTabId.SKILL_LIBRARY;
  }

  get skillLimit() {
    return this.configService.getConfigs()?.agent_skill_limit ?? SKILL_MAX_COUNT;
  }

  get disabledSubmit() {
    if (this.selectedIds.length > this.skillLimit) {
      return {
        disabled: true,
        tip: this.i18n.transform('skill.add.disabled.tip', { number: this.skillLimit }),
      };
    }
    if (!this.selectedIds.length) {
      return {
        disabled: true,
        tip: '',
      };
    }
    return {
      disabled: false,
      tip: '',
    };
  }

  constructor(
    private i18n: I18nService,
    private configService: AgentConfigService,
    private commonService: CommonService,
    private skillApi: SkillApi,
    private nzModal: NzModalService
  ) {}

  ngOnInit() {}

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public show(list): void {
    this.selectedItems = [...list];
    this.getSkillList(this.skillTabs[0].id);
    this.skillSelectedIds = list.map(item => item.skill_id);
    this.selectedIds = list.map(item => item.skill_id);
    this.drawerVisible = true;
  }

  public close(): void {
    this.dismiss();
  }

  public dismiss(): void {
    this.skillTabs.forEach((tab: any, index: number) => {
      tab.active = index === 0;
    });
    this.currentTab = this.skillTabs[0].id;
    this.drawerVisible = false;
    this.skillsList = [];
    this.hasMore = true;
    this.searchValue = '';
  }

  public importZip(importType: IMPORT_TYPE) {
    this.nzModal.create({
      nzTitle: this.i18n.transform('skill.create.button.importSkill'),
      nzContent: ImportSkillModalComponent,
      nzData: {
        importType,
        outputs: {
          importSuccess: () => {
            this.getSkillList(this.currentTab, true);
          },
        },
      },
    });
  }

  public addSkill() {
    if (this.selectedIds.length > this.skillLimit) {
      return;
    }
    this.batchAddSkill.emit(this.selectedItems);
  }

  public onSkillItemClick(skillItem: any): void {
    if (skillItem.disabled) {
      return;
    }
    const index = this.selectedIds.indexOf(skillItem.skill_id);
    if (index > -1) {
      this.selectedIds.splice(index, 1);
      this.selectedItems.splice(index, 1);
    } else {
      this.selectedIds.push(skillItem.skill_id);
      this.selectedItems.push(skillItem);
    }
    this.skillCardSetDisabled();
  }

  public onScroll() {
    const scrollableElement = document.getElementById('skill-tab-list');
    if (scrollableElement) {
      const { scrollTop, scrollHeight, clientHeight } = scrollableElement;
      if (scrollHeight - (scrollTop + clientHeight) < 100) {
        if (!this.loading) {
          this.getSkillList(this.currentTab);
        }
      }
    }
  }

  public buildRequestParams(tabId: SkillTabId, offset: number): Record<string, any> {
    const params: Record<string, any> = {
      limit: this.pageLimit,
      offset,
      priority_status: SkillStatus.DEVELOPED,
      // 广场tab：仅已上架（published=1）；组件库tab：查全部（含已上架，FRS-091 上架不改变组件库可见性）
      published_asset: tabId === SkillTabId.SKILL_MARKET ? SkillPublishedAsset.PUBLISHED : undefined,
    };

    if (this.searchValue) {
      params.name = this.searchValue;
    }

    return params;
  }

  public handleResponse(res: any) {
    const newItems = res.list.filter((item: any) => !this.skillsList.some(existing => existing.skill_id === item.skill_id));

    this.skillsList = [...this.skillsList, ...newItems];
    this.skillCardSetDisabled();
    this.total = res.count;
    this.hasMore = this.skillsList.length < this.total;
  }

  public handleError() {
    this.hasMore = false;
  }

  public onComplete() {
    this.loading = false;
  }

  public getSkillList(tabId: SkillTabId, resetPage = false) {
    if (!this.hasMore && !resetPage) {
      return;
    }

    if (resetPage) {
      this.skillsList = [];
    }
    this.loading = true;

    const params = this.buildRequestParams(tabId, this.skillsList.length);

    this.fetchPage(params)
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (res: any) => this.handleResponse(res),
        error: () => this.handleError(),
        complete: () => this.onComplete(),
      });
  }

  public clearFilter() {
    this.searchValue = '';
    this.getSkillList(this.currentTab, true);
  }

  private fetchPage(searchParams) {
    return this.skillApi.querySkillList(searchParams).pipe(
      map((res: any) => ({
        list: Array.isArray(res?.items) ? res.items : [],
        count: Number(res?.total) || 0,
      })),
      catchError(err =>
        of({
          list: [],
          count: 0,
        })
      )
    );
  }

  private resetState() {
    this.skillsList = [];
    this.total = 0;
    this.hasMore = true;
    this.loading = false;
  }

  private selectTab(tabId: SkillTabId) {
    this.searchValue = '';
    this.currentTab = tabId;
    this.resetState();
    this.getSkillList(tabId);
  }

  private skillCardSetDisabled() {
    const selectedSkillNames = new Set(this.selectedItems.filter(item => item.skill_name).map(item => item.skill_name));

    this.skillsList.forEach(item => {
      const isSelected = this.selectedItems.some(selectedItem => selectedItem.skill_id === item.skill_id);
      const isDeveloping = item.status === SkillStatus.DEVELOPING;

      if (isSelected) {
        item.disabled = false;
        item.tip = '';
        return;
      }

      const hasOtherSameNameSelected = selectedSkillNames.has(item.skill_name);

      item.disabled = hasOtherSameNameSelected || isDeveloping;

      if (isDeveloping) {
        item.tip = this.i18n.transform('skill.add.disabled.select.tip');
      } else if (hasOtherSameNameSelected) {
        item.tip = this.i18n.transform('skill.selected.repeat.tip');
      } else {
        item.tip = '';
      }
    });
  }
}
