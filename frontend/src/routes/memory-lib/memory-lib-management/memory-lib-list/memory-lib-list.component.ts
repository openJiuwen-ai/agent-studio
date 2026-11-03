import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';

import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';

// 引入 NG-ZORRO 模块
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTypographyModule } from 'ng-zorro-antd/typography';

import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { I18nNamespace } from '@i18n';
import { MEMORY_STRATEGY_MAP } from '@routes/memory-lib/memory-lib-constants';
import { IMemoryLibItem, IMemoryStrategy } from '@routes/memory-lib/memory-lib-interfaces';
import { MemoryLibService } from '@routes/memory-lib/memory-lib.service';
import { PipesModule } from '../../../../pipes/pipes.module';

@Component({
  selector: 'memory-lib-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    I18NextModule,
    PipesModule,
    NzTableModule,
    NzEmptyModule,
    NzButtonModule,
    NzToolTipModule,
    NzTagModule,
    NzDropDownModule,
    NzIconModule,
    NzTypographyModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.MEMORY_LIB],
    },
  ],
  templateUrl: './memory-lib-list.component.html',
  styleUrl: './memory-lib-list.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MemoryLibListComponent {
  readonly memoryLibService = inject(MemoryLibService);
  readonly i18n = inject(I18NextEagerPipe);
  readonly configServ = inject(AgentConfigService);
  readonly router = inject(Router);

  libs = input<IMemoryLibItem[]>();
  dataChange = output<void>();
  editMemoryLib = output<IMemoryLibItem>();

  /**
   * 获取策略类型的多语言拼接文本
   * @param data 行数据
   */
  getStrategyText(data: IMemoryLibItem): string {
    return data.long_term_memory_strategies
      ?.map((strategy: IMemoryStrategy) => this.i18n.transform(MEMORY_STRATEGY_MAP.get(strategy.type)?.name ?? ''))
      .filter(Boolean)
      .join(' | ') || '';
  }

  editMemory(memoryLib: IMemoryLibItem) {
    this.editMemoryLib.emit(memoryLib);
  }

  showReference(memoryLib: IMemoryLibItem) {
    this.memoryLibService.showReference(memoryLib.memory_repo_id);
  }

  deleteMemory(memoryLib: IMemoryLibItem) {
    if (this.memoryLibService.subscribeBtnDisabled()) {
      return;
    }
    this.memoryLibService.safeDeleteMemoryLib(memoryLib).then(isDeleted => {
      if (isDeleted) {
        this.dataChange.emit();
      }
    });
  }
}
