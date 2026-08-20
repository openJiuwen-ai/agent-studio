import { Component, EventEmitter, OnInit, Output, inject, Inject } from '@angular/core';
import { IGetTmplQuery, ITmpl, PromptService } from '@services/prompt.service';
import { CommonNoDataComponent } from '@shared/components/common-no-data/common-no-data.component';
import { MultiFieldSearchComponent, ISearchTag } from '@shared/components/multi-field-search/multi-field-search.component';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { CommonUtils } from 'src/utils/common.util';
import { AssertSquareTagType } from '@routes/agent-center/app-agent/common-logic-agent';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
enum mapKeys {
  category = 'category',
}

@Component({
  selector: 'meta-ref-prompt',
  template: `
    <div *nzModalTitle>{{ 'select_prompt_template' | i18nextEager }}</div>
    <div class="!overflow-hidden h-[496px]">
      <div class="relative h-full w-full">
        <nz-tabset id="ref-prompt-tabs" class=" top-level-tab" [(nzSelectedIndex)]="outerPromptIndex" (nzSelectedIndexChange)="onTopTabChange()">
          <nz-tab class=" mt-1" *ngFor="let tab of tabs" [nzTitle]="tab.title">
            <nz-tabset
              [nzTabPosition]="'top'"
              [nzType]="'line'"
              [nzAnimated]="false"
              class="app-prompt-tabs"
              (nzSelectedIndexChange)="onAppTabChange()"
              [(nzSelectedIndex)]="innerPromptIndex"
            >
              <nz-tab *ngFor="let tab of appPromptTabs; let i = index" [nzTitle]="tab.name"></nz-tab>
            </nz-tabset>
          </nz-tab>
        </nz-tabset>
        <div class="mt-1 flex flex-col gap-[16px] h-[calc(100%-124px)]">
          <div class="flex w-full items-center gap-2">
            <multi-field-search
              [searchItems]="searchItems"
              [(searchTags)]="searchName"
              [(searchField)]="searchField"
              (searchChange)="onSearchContentChange()"
              class="flex-1"
            ></multi-field-search>
            <button (click)="getPrompts()" class="h-8 w-8" nz-button>
              <nz-icon nzType="reload" nzTheme="outline" />
            </button>
          </div>
          <div class="flex h-[calc(100%-52px)] w-full rounded-[8px] border-[1px] border-solid border-[#dfdfdf]">
            <ng-container *ngIf="tmpls.length">
              <div class="border-r-solid w-[310px] border-r-[1px] border-r-[#dfdfdf] p-[20px] h-full">
                <div (scroll)="onScroll($event)" class="flex  w-full flex-col gap-[8px] h-full overflow-auto">
                  <div
                    [ngStyle]="{
                      'border-color': tmpl.template_id === curTmpl?.template_id ? '#1476ff' : 'transparent',
                    }"
                    class="flex w-full cursor-pointer flex-col gap-[4px] rounded-[6px] border-[1px] border-solid bg-[#fafafa] p-[16px]"
                    *ngFor="let tmpl of tmpls"
                    (click)="onSelectTmpl(tmpl)"
                  >
                    <div class="flex items-center gap-[8px]">
                      <div class="max-w-[calc(100%-40px)] shrink-0 font-bold text-[#191919]">
                        {{ tmpl.template_name }}
                      </div>

                      <div class="tag-container flex flex-1 items-center gap-[2px] overflow-hidden">
                        <div class="whitespace-nowrap shrink-0 rounded-[4px] bg-[#f5f5f5] px-[4px] text-[12px]" *ngFor="let tag of tmpl.tag_list">
                          {{ lang === 'zh-cn' ? tag.name : tag?.name_en }}
                        </div>
                      </div>
                    </div>
                    <div class="text-[12px] text-desc">
                      {{ 'come_from' | i18nextEager }}
                      {{ lang === 'zh-cn' ? tmpl.industry.name : tmpl.industry.name_en }}
                    </div>
                  </div>
                  <nz-spin *ngIf="isLoading" class="flex w-full items-center justify-center" />
                </div>
              </div>
              <div class=" w-[calc(100%-310px)] p-[20px] overflow-auto">
                <div *ngIf="curTmpl" class="flex flex-col gap-[8px] text-desc">
                  <div class="text-[14px] font-bold text-[#191919]">
                    {{ curTmpl.template_name }}
                  </div>
                  <div class="flex w-full items-center gap-[4px]">
                    <div class="flex items-center gap-[4px] rounded-[4px] border-[1px] border-solid border-[#f0f0f0] bg-white px-[10px]">
                      <span class="text-[#595959]">
                        {{ lang === 'zh-cn' ? curTmpl.industry?.name : curTmpl.industry?.name_en }}
                      </span>
                    </div>

                    <div class="flex items-center gap-[4px]">
                      <div class="rounded-[4px] bg-[#f5f5f5] px-[8px]" *ngFor="let tag of curTmpl.tag_list">
                        {{ lang === 'zh-cn' ? tag.name : tag?.name_en }}
                      </div>
                    </div>
                  </div>
                  <div>
                    {{ 'creator_with_colon' | i18nextEager }}
                    {{ curTmpl.creator }}
                  </div>
                  <div>
                    {{ 'creation_time_with_colon' | i18nextEager }}
                    {{ curTmpl.created_on | date: 'yyyy-MM-dd HH:mm:ss' }}
                  </div>
                  <div class="mt-[8px]">
                    <pre style="white-space: pre-wrap; font-family: PingFang SC;">{{ curTmpl.content }}</pre>
                  </div>
                </div>
              </div>
            </ng-container>
            <ng-container *ngIf="!tmpls.length">
              <div class="flex  w-full items-center justify-center">
                <app-common-no-data *ngIf="!isLoading" />
                <nz-spin class="flex  w-full items-center justify-center" *ngIf="isLoading" />
              </div>
            </ng-container>
          </div>
        </div>
      </div>
    </div>
    <div *nzModalFooter class="!pt-0" style="margin-top: 16px">
      <div class="flex items-center justify-between text-[14px]">
        <div class="h-1 w-1"></div>
      </div>
      <div class="mt-[32px] flex justify-end gap-2">
        <button type="button" nz-button (click)="dismiss()">
          {{ 'cancel' | i18nextEager }}
        </button>
        <button type="button" nz-button nzType="primary" (click)="onSelect()" [disabled]="!curTmpl">
          {{ 'ok' | i18nextEager }}
        </button>
      </div>
    </div>
  `,
  styles: [
    `
      ::ng-deep {
        #ref-prompt-tabs {
          .ant-tabs-nav {
            border-bottom-color: transparent !important;
          }

          .ant-tabs-content {
            height: calc(100% - 34px) !important;
          }
        }
      }

      .ind-default {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-default.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-industry {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-industry.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-finance {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-finance.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-government {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-government.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-medical {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-medical.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-make {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-make.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-it {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-it.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .ind-education {
        display: inline-block;
        vertical-align: middle;
        background: url('src/assets/icons/ind-education.svg') no-repeat center;
        background-color: #fff;
        cursor: pointer;
        width: 16px;
        height: 16px;
      }

      .tag-container {
        position: relative;
      }

      .tag-container::after {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 6px;
        height: 100%;
        background: linear-gradient(to right, rgba(255, 255, 255, 0), #fafafa);
        pointer-events: none;
      }
    `,
  ],
  standalone: true,
  imports: [MODULES, CommonNoDataComponent, MultiFieldSearchComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
})
export class RefPromptComponent implements OnInit {
  @Output() select = new EventEmitter<ITmpl>();
  readonly modalRef = inject(NzModalRef);
  public tabs = [
    {
      id: 'preset',
      title: this.i18n.transform('prompt_market', {
        ns: I18nNamespace.PROMPT_PLATFORM,
      }),
      active: true,
    },
    {
      id: 'mine',
      title: this.i18n.transform('custom_prompt_tab'),
      active: false,
    },
  ];
  public isLoading = false;
  public curTmpl: ITmpl | null = null;

  public offset = 0;
  public limit = 10;

  public hasNextPage = true;
  public controller = new AbortController();
  public searchItems: any[] = [
    {
      label: this.i18n.transform('industry'),
      field: 'industry_list',
      type: 'checkbox',
      options: [],
      valueKey: 'id',
    },
    {
      label: this.i18n.transform('label'),
      field: 'tag_list',
      type: 'checkbox',
      valueKey: 'id',
      options: [],
    },
    {
      label: this.i18n.transform('template_name'),
      field: 'template_name',
    },
    {
      label: 'ID',
      field: 'template_id',
      options: [],
    },
    {
      label: this.i18n.transform('search_item_content_'),
      field: 'content',
    },
  ];
  public searchedItems: any[] = [];
  public curActived = 'preset';
  public tmpls: ITmpl[] = [];
  public searchValue: string = '';
  public searchName: ISearchTag[] = [];
  public searchField: string = 'template_name';

  public lang = CommonUtils.getLanguage();
  appPromptTabs: AssertSquareTagType[] = [
    {
      name: this.i18n.transform('all'),
      name_en: 'all',
      id: 'all',
      active: true,
      description: '',
      library_type: '',
      created_on: 0,
      updated_on: 0,
    },
  ];
  selectedTagId: string = '';
  public outerPromptIndex = 0;
  public innerPromptIndex = 0;

  constructor(
    private promptServ: PromptService,
    private i18n: I18NextEagerPipe,
    public promptService: PromptService,
    @Inject(NZ_MODAL_DATA) public nzData: any
  ) {}

  async ngOnInit() {
    this.getPromptTagData();
    this.getSearchOps().then();
    this.getPrompts().then();
  }

  public async getSearchOps() {
    try {
      const [industries, tags] = await Promise.all([
        this.promptServ.getIndustryListAsync(),
        this.promptServ.getTagListAsync({
          limit: 100,
          offset: 0,
        }),
      ]);

      this.searchItems[0].options = industries?.map(industry => ({
        id: industry.id,
        label: this.lang === 'zh-cn' ? industry.name : industry.name_en,
      }));

      this.searchItems[1].options = tags?.data?.map(tag => ({
        id: tag.id,
        label: this.lang === 'zh-cn' ? tag.name : tag.nameEn,
      }));
    } catch {
      // do nth
    }
  }

  public onSearchContentChange() {
    this.offset = 0;
    this.hasNextPage = true;
    this.getPrompts();
  }

  public async getPrompts(conf: { isScroll: boolean } = { isScroll: false }) {
    try {
      if (this.controller) {
        this.controller.abort();
      }

      this.controller = new AbortController();
      this.isLoading = true;

      const params: IGetTmplQuery = {
        template_name: '',
        offset: conf?.isScroll ? this.offset : 0,
        limit: 10,
      };

      const industryTag = this.searchName.find(t => t.field === 'industry_list');
      const tagTag = this.searchName.find(t => t.field === 'tag_list');
      const nameTag = this.searchName.find(t => t.field === 'template_name');
      const idTag = this.searchName.find(t => t.field === 'template_id');
      const contentTag = this.searchName.find(t => t.field === 'content');

      if (industryTag?.id) {
        params.industry_list = [industryTag.id];
      }
      if (tagTag?.id) {
        params.tag_list = [tagTag.id];
      }
      if (nameTag?.value) {
        params.template_name = nameTag.value;
      }
      if (idTag?.value) {
        params.template_id = idTag.value;
      }
      if (contentTag?.value) {
        params.content = contentTag.value;
      }

      const query = {};

      if (this.selectedTagId) {
        query[mapKeys.category] = this.selectedTagId;
      }

      if (this.curActived === 'preset') {
        params.source = 'PRESET';
      }

      const { data, has_next_page, count } = await this.promptServ.getPromptTemplateListAsync(params, this.controller.signal, query);
      this.hasNextPage = has_next_page;
      if (conf?.isScroll) {
        this.tmpls.push(...data);
      } else {
        this.tmpls = data;
      }

      this.searchItems.find(item => item.field === 'template_id').options = data.map(d => ({ label: d.template_id, id: d.template_id }));

      this.offset += data.length;

      if (this.tmpls.length) {
        this.curTmpl = this.tmpls[0];
      }
    } finally {
      this.isLoading = false;
    }
  }

  public onScroll(event: Event): void {
    const container = event.target as HTMLElement;
    // 直接相加会有一位小数的误差，导致无法触发加载
    // 添加一个偏移常量确保计算结果能够大于容器高度
    const isBottom = container.scrollTop + container.clientHeight + 10 >= container.scrollHeight;

    if (isBottom && !this.isLoading && this.hasNextPage) {
      this.getPrompts({ isScroll: true });
    }
  }

  public activeChange(activeId: string, isActive: boolean) {
    if (isActive) {
      this.offset = 0;
      this.hasNextPage = true;
      this.curActived = activeId;
      this.tmpls = [];
      this.getPrompts();
    }
  }

  public onTopTabChange() {
    this.tabs.forEach(item => (item.active = false));
    const tab = this.tabs[this.outerPromptIndex];
    tab.active = true;
    if (tab) {
      this.activeChange(tab.id, true);
    }
  }

  public onAppTabChange() {
    this.appPromptTabs.forEach(item => (item.active = false));
    const tab = this.appPromptTabs[this.innerPromptIndex];
    tab.active = true;
    if (tab) {
      this.changeAppTab(tab);
    }
  }

  public onSelectTmpl(tmpl: ITmpl) {
    this.curTmpl = tmpl;
  }

  dismiss(): void {
    this.modalRef.destroy();
  }

  close(): void {}

  public onSelect() {
    if (this.nzData?.select) {
      this.nzData.select(this.curTmpl);
    }
    this.select.emit(this.curTmpl);
    this.modalRef.destroy();
  }

  /** 获取tab标签 **/
  private getPromptTagData() {
    const params = {
      library_type: 'prompt',
    };
    this.promptService
      ?.getAssertTagAsync(params)
      .then(response => {
        const firstTab = this.appPromptTabs[0];
        this.appPromptTabs.length = 0;
        this.appPromptTabs.push(firstTab);
        for (let index = 0; index < response.length; index++) {
          this.appPromptTabs.push(response[index]);
        }
      })
      .catch();
  }

  changeAppTab(tab: AssertSquareTagType) {
    if (tab.active) {
      this.tmpls.length = 0;
      if (tab.id === 'all') {
        this.selectedTagId = '';
      } else {
        this.selectedTagId = tab.id;
      }
    }
    this.getPrompts().then();
  }
}
