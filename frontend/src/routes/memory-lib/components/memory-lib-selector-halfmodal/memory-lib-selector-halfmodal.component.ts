import { Component, inject, Input, linkedSignal, OnInit, signal, Optional, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';

// NG-ZORRO 导入
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NZ_DRAWER_DATA } from 'ng-zorro-antd/drawer';

import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { IMemoryLibItem, MemoryLibCardDisplayConfig } from '@routes/memory-lib/memory-lib-interfaces';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { MemoryLibCardDisplayComponent } from '@routes/memory-lib/components/memory-lib-card-display/memory-lib-card-display.component';
import { MemoryLibService } from '@routes/memory-lib/memory-lib.service';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'memory-lib-selector',
  templateUrl: './memory-lib-selector-halfmodal.component.html',
  styleUrls: ['./memory-lib-selector-halfmodal.component.scss'],
  standalone: true,
  imports: [
    MemoryLibCardDisplayComponent,
    I18NextModule,
    FormsModule,
    NzButtonModule,
    NzIconModule,
    NzInputModule,
    NzAlertModule,
    NzPaginationModule,
    NzSpinModule,
    NzToolTipModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.MEMORY_LIB],
    },
  ],
})
export class MemoryLibSelectorHalfmodalComponent implements OnInit {
  @Input() existedLibs: IMemoryLibItem[] = [];

  readonly memoryLibService = inject(MemoryLibService);
  readonly memoryLibApiService = inject(MemoryLibApiService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly agentConfigService = inject(AgentConfigService);
  readonly message = inject(NzMessageService);

  constructor(@Optional() @Inject(NZ_DRAWER_DATA) public nzData: any) {}

  existedMemoryLibs = linkedSignal<IMemoryLibItem[]>(() => this.existedLibs);
  memoryLibs = signal<IMemoryLibItem[]>([]);

  // 兼容 Zorro 简单搜索，映射回原接口需要的格式
  tempSearchValue = '';

  currentPage = signal(1);
  pageSize = signal({
    size: 10,
  });
  totalNumber = signal(0);

  cardDisplayConfig: MemoryLibCardDisplayConfig = {
    cardSize: 'small',
    cardNameBold: false,
    descriptionConfig: { enable: true, maxLine: 1 },
    layoutConfig: { layout: 'flex', flexQuantities: 2 },
    tagsConfig: { enable: true, tagSize: 'small' },
    operationConfig: { enable: true },
  };

  isLoading = signal(false);

  ngOnInit() {
    this.queryData();
  }

  onPageChange(page: number) {
    this.currentPage.set(page);
    this.queryData();
  }

  queryInSearch() {
    this.currentPage.set(1);
    this.queryData();
  }

  queryData() {
    this.isLoading.set(true);

    // 构造原业务逻辑需要的 params 格式
    const searchParams: any = {};
    if (this.tempSearchValue) {
      searchParams.name = this.tempSearchValue;
    }

    this.memoryLibApiService
      .queryMemoryLibs({
        offset: (this.currentPage() - 1) * this.pageSize().size,
        limit: this.pageSize().size,
        ...searchParams,
      })
      .then(res => {
        this.memoryLibs.update(() => res.items ?? []);
        this.totalNumber.set(res.total ?? 0);
      })
      .catch(() => {
        this.memoryLibs.update(() => []);
      })
      .finally(() => {
        this.isLoading.set(false);
      });
  }

  selectChange(selectLibs: IMemoryLibItem[]) {
    this.existedMemoryLibs.update(() => selectLibs);
  }

  createMemoryLib() {
    this.memoryLibService.showSelectCreateType(createData => {
      const { reason, halfModalRef, data, setLoading } = createData;
      if (reason && data) {
        setLoading(true);
        this.memoryLibApiService
          .createMemoryLibs(data)
          .then(() => {
            this.message.success(this.i18n.transform('memory.create.tip.success'));
            setLoading(false);
            halfModalRef.close?.(reason);
            this.queryData();
          })
          .catch(() => {
            setLoading(false);
          });
      } else {
        halfModalRef.close?.(reason);
      }
    });
  }

  dismiss() {}

  close(): void {
    if (this.nzData?.beforeHide && typeof this.nzData.beforeHide === 'function') {
      this.nzData.beforeHide({
        reason: true,
      });
    }
  }
}
