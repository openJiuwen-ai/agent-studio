import { ChangeDetectionStrategy, Component, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { NzMessageService } from 'ng-zorro-antd/message';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { Subject, takeUntil } from 'rxjs';

// NG-ZORRO 导入
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzBreadCrumbModule } from 'ng-zorro-antd/breadcrumb';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzDescriptionsModule } from 'ng-zorro-antd/descriptions';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzDrawerModule } from 'ng-zorro-antd/drawer';
import { NzModalModule } from 'ng-zorro-antd/modal';

import { I18nNamespace } from '@i18n';
import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { MEMORY_STRATEGY_MAP } from '@routes/memory-lib/memory-lib-constants';
import { IMemoryLibDetail } from '@routes/memory-lib/memory-lib-interfaces';
import { MemoryLibService } from '@routes/memory-lib/memory-lib.service';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';

import { PipesModule } from '../../../pipes/pipes.module';
import { SafeHtmlPipe } from '../../../pipes/safehtml.pipe';

@Component({
  selector: 'memory-lib-detail',
  templateUrl: './memory-lib-detail.component.html',
  styleUrl: './memory-lib-detail.component.scss',
  standalone: true,
  imports: [
    FormsModule,
    RouterModule,
    I18NextModule,
    PipesModule,
    SafeHtmlPipe,
    // NG-ZORRO
    NzButtonModule,
    NzBreadCrumbModule,
    NzIconModule,
    NzDescriptionsModule,
    NzTableModule,
    NzTagModule,
    NzTypographyModule,
    NzSpinModule,
    NzToolTipModule,
    NzDrawerModule,
    NzModalModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.MEMORY_LIB],
    },
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryLibDetailComponent implements OnInit, OnDestroy {
  readonly visibilityService = inject(SetSidebarVisibilityService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly route = inject(ActivatedRoute);
  readonly router = inject(Router);
  readonly memoryLibService = inject(MemoryLibService);
  readonly memoryLibApiService = inject(MemoryLibApiService);
  readonly message = inject(NzMessageService);

  memoryStrategyMap = MEMORY_STRATEGY_MAP;
  memoryLibId = signal('');
  memLibDetail = signal<IMemoryLibDetail | null>(null);
  loading = signal(false);

  crumbItems = signal<any[]>([
    {
      label: this.i18n.transform('memory.management.title'),
      routerLink: '/home/agent-center/library-home',
      queryParams: { tabId: 'memoryLib' },
    },
    {
      label: this.i18n.transform('memory.detail.crumb.memoryLibDetail'),
    },
  ]);

  operators = signal<any[]>([
    {
      iconaction: {
        label: this.i18n.transform('memory.management.edit'),
        iconName: 'edit',
        tipContent: this.i18n.transform('memory.management.edit'),
      },
      click: (): void => this.#editMemoryLib(),
    },
    {
      iconaction: {
        label: this.i18n.transform('memory.management.referenceResource'),
        iconName: 'link',
        tipContent: this.i18n.transform('memory.management.referenceResource'),
      },
      click: (): void => this.#viewReferenceResource(),
    },
  ]);

  private destroy$ = new Subject<void>();

  constructor() {
    this.#setMemoryLibId();
  }

  getMappedIcon(tinyIcon: string): string {
    const map: Record<string, string> = {
      'cloudx-action-edit': 'edit',
      'cloudx-action-binging': 'link',
    };
    return map[tinyIcon] || tinyIcon;
  }

  onBack() {
    this.router.navigate(['/home/agent-center/library-home'], { queryParams: { tabId: 'memoryLib' } });
  }

  #viewReferenceResource() {
    const detail = this.memLibDetail();
    if (detail?.memory_repo_id) {
      this.memoryLibService.showReference(detail.memory_repo_id);
    }
  }

  #setMemoryLibId() {
    this.route.params.pipe(takeUntil(this.destroy$)).subscribe(params => {
      this.memoryLibId.set(params.id);
      this.#getResourceInfo();
    });
  }

  #getResourceInfo(): void {
    const id = this.memoryLibId();
    if (!id) {
      return;
    }
    this.loading.set(true);
    this.memoryLibApiService
      .queryMemoryLibDetail(id)
      .then(detail => {
        this.memLibDetail.set(detail);
      })
      .catch(() => this.memLibDetail.set(null))
      .finally(() => this.loading.set(false));
  }

  #editMemoryLib() {
    const detail = this.memLibDetail();
    const repoId = detail?.memory_repo_id;

    if (repoId) {
      this.memoryLibService.createOrEditMemLib(editData => {
        const { reason, halfModalRef, data, setLoading } = editData;

        if (reason && data) {
          setLoading(true);
          this.memoryLibApiService
            .patchMemoryLib(repoId, data)
            .then(() => {
              this.message.success(this.i18n.transform('memory.patch.tip.success'));
              setLoading(false);
              halfModalRef.close?.(reason);
              this.#getResourceInfo();
            })
            .catch(() => setLoading(false));
        } else {
          halfModalRef.close?.(reason);
        }
      }, repoId);
    }
  }

  ngOnInit(): void {
    this.visibilityService.setSidebarsVisibilityByState('init');
  }

  ngOnDestroy(): void {
    this.visibilityService.setSidebarsVisibilityByState('destroy');
    this.destroy$.next();
    this.destroy$.complete();
  }
}
