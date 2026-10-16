import { ChangeDetectionStrategy, Component, computed, effect, inject, input, linkedSignal, output, signal } from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextModule } from 'angular-i18next';

// 替换为 NG-ZORRO 模块
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzTypographyModule } from 'ng-zorro-antd/typography';

import { MEMORY_LIB_DEFAULT_ICON } from '@routes/memory-lib/memory-lib-constants';
import { MemoryLibApiService } from '@routes/memory-lib/memory-lib-api.service';
import { I18nNamespace } from '@i18n';
import { MemoryLibSelectorTipType } from '@routes/memory-lib/memory-lib-enums';
import { IMemoryLibBaseInfo, IMemoryLibItem, IMemoryLibSelectData } from '@routes/memory-lib/memory-lib-interfaces';
import { MemoryLibService } from '@routes/memory-lib/memory-lib.service';

@Component({
  selector: 'memory-lib-selector',
  standalone: true,
  imports: [
    I18NextModule,
    NzIconModule,
    NzTagModule,
    NzToolTipModule,
    NzSpinModule,
    NzTypographyModule
  ],
  templateUrl: './memory-lib-selector.html',
  styleUrl: './memory-lib-selector.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.MEMORY_LIB],
    },
  ],
})
export class MemoryLibSelector {
  // 逻辑保持不变...
  readonly memoryLibService = inject(MemoryLibService);
  readonly memoryLibApiService = inject(MemoryLibApiService);

  isFold = input(true);
  tipType = input<MemoryLibSelectorTipType>(MemoryLibSelectorTipType.ICON);
  memoryLibs = input<IMemoryLibBaseInfo[]>([]);
  loading = input<boolean>(false);
  isNeedPadding = input(true);
  memoryLibSelectChange = output<IMemoryLibSelectData>();

  _folded = linkedSignal(() => this.isFold());
  _memoryLibs = signal<IMemoryLibItem[]>([]);
  isIconTip = computed(() => this.tipType() === MemoryLibSelectorTipType.ICON);
  isDescTip = computed(() => this.tipType() === MemoryLibSelectorTipType.DESCRIPTION);

  existedEffect = effect(() => {
    const currentLibs = this.memoryLibs();
    if (currentLibs?.filter(lib => Boolean(lib.memory_repo_id))?.length) {
      this.getExistedMemoryLib();
    } else {
      this._memoryLibs.set([]);
    }
  });

  changeFold() {
    this._folded.set(!this._folded());
  }

  showMemoryLibSelectorHalfModal() {
    this.memoryLibService.showMemoryLibSelector(this._memoryLibs(), data => {
      this.memoryLibSelectChange.emit(data);
    });
  }

  deleteMemoryLib(memoryLib: IMemoryLibItem) {
    this.memoryLibSelectChange.emit({
      reason: true,
      halfModalRef: null,
      data: this._memoryLibs().filter(lib => lib.memory_repo_id !== memoryLib.memory_repo_id),
    });
  }

  getExistedMemoryLib() {
    this.memoryLibApiService
      .queryMemoryLibs({
        offset: 0,
        limit: 10,
        ids: this.memoryLibs()
          .filter(lib => Boolean(lib.memory_repo_id))
          .map(item => item.memory_repo_id),
      })
      .then(res => {
        const existedMemoryLibs = new Map(res.items.map(item => [item.memory_repo_id, item]));
        const memoryLibs = this.memoryLibs()
          .filter(lib => Boolean(lib.memory_repo_id))
          .map(item => {
            if (existedMemoryLibs.has(item.memory_repo_id)) {
              return existedMemoryLibs.get(item.memory_repo_id)!;
            }
            return {
              ...item,
              invalid: true,
            };
          });
        this._memoryLibs.set(memoryLibs as IMemoryLibItem[]);
      })
      .catch(() => {
        this._memoryLibs.set(
          this.memoryLibs()
            .filter(lib => Boolean(lib.memory_repo_id))
            .map(lib => ({
              ...lib,
              icon: MEMORY_LIB_DEFAULT_ICON,
            })) as IMemoryLibItem[]
        );
      });
  }
}
