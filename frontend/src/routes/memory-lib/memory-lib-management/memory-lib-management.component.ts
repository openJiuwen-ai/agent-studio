import { ChangeDetectionStrategy, Component, computed, inject, signal, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { IMemoryLibItem } from '@routes/memory-lib/memory-lib-interfaces';
import { I18nNamespace } from '@i18n';
import { MemoryLibListComponent } from '@routes/memory-lib/memory-lib-management/memory-lib-list/memory-lib-list.component';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { MemoryLibService } from '@routes/memory-lib/memory-lib.service';
import { SelectMemoryCreateTypeComponent } from '@routes/memory-lib/components/select-memory-create-type/select-memory-create-type.component';
import { MemoryServiceInstanceManagementComponent } from '@routes/memory-lib/memory-service-instance-management/memory-service-instance-management.component';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'memory-lib-management',
  standalone: true,
  imports: [
    CommonModule,
    NoDataGuideComponentComponent,
    I18NextModule,
    NzButtonModule,
    NzIconModule,
    NzPaginationModule,
    NzInputModule,
    NzSpinModule,
    NzTabsModule,
    NewCommonNoDataWithBtnComponent,
    MemoryLibListComponent,
    SelectMemoryCreateTypeComponent,
    MemoryServiceInstanceManagementComponent,
    FormsModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.MEMORY_LIB],
    },
  ],
  templateUrl: './memory-lib-management.component.html',
  styleUrl: './memory-lib-management.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryLibManagementComponent implements OnInit {
  @ViewChild('selectCreateType') selectCreateType!: SelectMemoryCreateTypeComponent;

  readonly memoryLibService = inject(MemoryLibService);
  readonly memoryLibApiService = inject(MemoryLibApiService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly configServ = inject(AgentConfigService);
  readonly router = inject(Router);
  readonly route = inject(ActivatedRoute);
  readonly message = inject(NzMessageService);

  // Sub-tabs: memory repos vs external service instances
  subTabs = [
    { id: 'memoryRepo', title: this.i18n.transform('memory.management.title'), active: true },
    { id: 'memoryInstance', title: this.i18n.transform('memory.tab.memoryServiceInstance'), active: false },
  ];
  currentSubTabId = 'memoryRepo';
  subTabIndex = 0;

  onSubTabChange(index: number) {
    this.subTabIndex = index;
    this.currentSubTabId = this.subTabs[index].id;
  }

  libs = signal<IMemoryLibItem[]>([]);
  isShowGuide = signal(true);

  // 搜索框绑定值
  searchText = signal('');

  currentPage = signal(1);
  pageSize = signal({
    options: [10, 20, 50, 100],
    size: 10,
  });
  totalNumber = signal(0);

  loading = signal(false);
  isFirstLoading = signal(true);

  searchNameIsEmpty = computed(() => this.searchText().trim() === '');
  isNoDataGuideShow = computed(() => this.libs().length === 0 && this.searchNameIsEmpty() && !this.loading());

  ngOnInit() {
    this.queryLibs();
  }

  onSearchTextChange(val: string) {
    this.searchText.set(val);
    // 与知识库对齐：清空搜索词时自动恢复全量列表
    if (!val) {
      this.searchKbs();
    }
  }

  searchKbs() {
    this.currentPage.set(1);
    this.queryLibs();
  }

  queryLibs() {
    this.loading.set(true);
    const params: any = {
      offset: (this.currentPage() - 1) * this.pageSize().size,
      limit: this.pageSize().size,
    };

    if (this.searchText()) {
      params.name = this.searchText();
    }

    this.memoryLibApiService
      .queryMemoryLibs(params)
      .then(res => {
        this.libs.set(res.items ?? []);
        this.totalNumber.set(res.total ?? 0);
      })
      .catch(() => {
        this.libs.set([]);
        this.totalNumber.set(0);
      })
      .finally(() => {
        this.loading.set(false);
        this.isFirstLoading.set(false);
      });
  }

  onPageIndexChange(index: number) {
    this.currentPage.set(index);
    this.queryLibs();
  }

  onPageSizeChange(size: number) {
    this.pageSize.update(prev => ({ ...prev, size }));
    this.searchKbs();
  }

  noDataSearch() {
    this.searchText.set('');
    this.queryLibs();
  }

  createMemoryLib() {
    this.selectCreateType?.show();
  }

  createBuiltinMemoryLib() {
    this.memoryLibService.createOrEditMemLib(res => {
      const { reason, halfModalRef, data, setLoading } = res;
      if (reason && data) {
        setLoading(true);
        this.memoryLibApiService
          .createMemoryLibs(data)
          .then(() => {
            this.message.success(this.i18n.transform('memory.create.tip.success'));
            setLoading(false);
            halfModalRef.close?.(reason);
            this.queryLibs();
          })
          .catch(() => setLoading(false));
      } else {
        halfModalRef.close?.(reason);
      }
    });
  }

  connectExternalMemoryLib() {
    this.memoryLibService.connectExternalMemoryLib(res => {
      const { reason, halfModalRef, data, setLoading } = res;
      if (reason && data) {
        setLoading(true);
        this.memoryLibApiService
          .createMemoryLibs(data)
          .then(() => {
            this.message.success(this.i18n.transform('memory.create.tip.success'));
            setLoading(false);
            halfModalRef.close?.(reason);
            this.queryLibs();
          })
          .catch(() => setLoading(false));
      } else {
        halfModalRef.close?.(reason);
      }
    });
  }

  editMemoryLib(memoryLib: IMemoryLibItem) {
    this.memoryLibService.createOrEditMemLib(res => {
      const { reason, halfModalRef, data, setLoading } = res;
      if (reason && data) {
        setLoading(true);
        this.memoryLibApiService
          .patchMemoryLib(memoryLib.memory_repo_id, data)
          .then(() => {
            this.message.success(this.i18n.transform('memory.patch.tip.success'));
            setLoading(false);
            halfModalRef.close?.(reason);
            this.queryLibs();
          })
          .catch(() => setLoading(false));
      } else {
        halfModalRef.close?.(reason);
      }
    }, memoryLib.memory_repo_id);
  }
}
