import { SkillApi } from '@agentcore/api/skill.api';
import { CARD_LIST_TYPE } from '@agentcore/constants/skill';
import { I18nService } from '@agentcore/core/i18n.service';
import { I18nPipe } from '@agentcore/shared/pipes/i18n.pipe';
import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, Input, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ComponentCardComponent } from '@routes/agent-center/component-library/component-card/component-card.component';
import { CommonService } from '@services/common.service';
import { MaterialUseType } from '@shared/components/material-use/material-use.enum';
import { DebounceDecorators } from '@shared/decorators/debouncing-throttling.directive';
import { MODULES } from '@shared/modules';
import { filter } from 'rxjs';
import { CommonUtils } from 'src/utils/common.util';
import { ImportSkillButtonComponent } from './import-skill-button/import-skill-button.component';
import { QueryParams, SkillCard } from './interface/skill.interface';
import { SkillCommonService } from './services/skill.common.service';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';
enum mapKeys {
  TYPE = 'type',
  VISIBILITY = 'visibility',
  LANGUAGE = 'language',
  WORK_SPACE_ID = 'work_space_id',
  entry_point = 'entry_point',
}

@Component({
  selector: 'component-lib-skill',
  templateUrl: './skill.component.html',
  styleUrls: ['./skill.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    CommonModule,
    ComponentCardComponent,
    NoDataGuideComponentComponent,
    ImportSkillButtonComponent,
    NewCommonNoDataWithBtnComponent,
    I18nPipe,
    MultiFieldSearchComponent,
  ],
  providers: [I18nService],
})
export class SkillComponent implements OnInit {
  @Input() isFromDevelopSpace = false;
  isFirstLoading = true; // 是否为初次加载
  isLoading = true;
  skillsHeaderConfig = {
    helptip: {
      label: this._i18n.transform('skill.title'),
    },
    buttons: [],
  };
  public cardListType = CARD_LIST_TYPE;
  public isFromAgentBuilder = false;
  // 监听浏览器宽度，做自适应弹框宽度
  public windowWidth: number;
  // 兼容agentBuilder
  workSpaceId = '';
  public currentCardPage = 1;
  public isLoadingCard = false;
  public cards: SkillCard[] = [];
  public cardPageSize = {
    options: [12, 24, 48, 64],
    size: 12,
  };
  public totalCardNumber = 0;
  public materialUseType = MaterialUseType;
  title: string = this._i18n.transform('common.noData');
  private destroyRef = inject(DestroyRef);
  searchName = [];
  searchField = 'name';
  public searchItems = [
    {
      label: this._i18n.transform('skill.list.name'),
      field: 'name',
    },
    {
      label: this._i18n.transform('skill.list.description'),
      field: 'description',
    },
  ];

  constructor(
    private _skillApi: SkillApi,
    private _i18n: I18nService,
    public commonService: CommonService,
    private skillCommonService: SkillCommonService
  ) {}

  ngOnInit() {
    this.querySkillList();
    this.skillCommonService.refreshSkillSub$
      .pipe(
        filter(res => res === true), // 只处理 true 的情况
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(() => this.querySkillList());
  }

  isZH() {
    return CommonUtils.getLanguage() === 'zh-cn';
  }

  @DebounceDecorators()
  onSearchContentChange(): void {
    this.currentCardPage = 1;
    this.querySkillList();
  }

  querySkillList() {
    this.isLoading = true;
    const params: QueryParams = {
      offset: 0,
      limit: this.cardPageSize.size || 10, // 提供默认值
      [mapKeys.LANGUAGE]: this.isZH() ? 'ZH' : 'EN', // 直接初始化语言参数
    };
    if (this.searchName.length > 0) {
      const searchParams = Object.fromEntries(this.searchName.map(item => [item.field, item.id || item.value]));
      Object.assign(params, searchParams);
    }
    const calculatePagination = (page: number, pageSize: number) => ({
      offset: (page - 1) * pageSize,
      limit: pageSize,
    });
    Object.assign(params, calculatePagination(this.currentCardPage, this.cardPageSize.size));
    this._skillApi
      .querySkillList(params)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(response => {
        this.cards = response?.items || [];
        this.totalCardNumber = response?.total;
        this.isFirstLoading = false;
        this.isLoading = false;
      });
  }

  handleClickClearSearch(): void {
    this.searchName = [];
    this.querySkillList();
  }

  /**
   * 卡片操作回调（上架/下架后刷新列表，FRS-091）
   */
  onCardHandle(event: any): void {
    this.querySkillList();
  }
}
