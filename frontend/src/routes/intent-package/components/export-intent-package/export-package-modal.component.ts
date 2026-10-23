import { Component, OnInit, Optional, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonUtils } from 'src/utils/common.util';
import { IntentPackageService } from '../../intent-package.service';
import { FormsModule } from '@angular/forms';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzEmptyModule } from 'ng-zorro-antd/empty';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzDrawerRef } from 'ng-zorro-antd/drawer';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
@Component({
  selector: 'export-intent-package-modal',
  templateUrl: './export-package-modal.component.html',
  styleUrls: ['./export-package-modal.component.less'],
  standalone: true,
  imports: [CommonModule, MODULES, FormsModule, NzTableModule, NzPaginationModule, NzButtonModule, NzInputModule, NzToolTipModule, NzEmptyModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ExportPackageModalComponent implements OnInit {
  public displayData: any[] = [];
  public loading = false;
  public submitting = false;
  public totalNumber = 0;
  public currentPage = 1;
  public pageSize = 10;
  public searchName = '';
  public pagerSelectOptions = [10, 20, 50, 100];
  public changeUrl = cdnAssetUrl;
  public setOfCheckedId = new Set<string>();
  public checked = false;
  public indeterminate = false;

  constructor(
    private readonly api: IntentPackageService,
    private readonly i18n: I18NextEagerPipe,
    @Optional() private modalRef: NzModalRef,
    @Optional() private drawerRef: NzDrawerRef,
    private commonLogic: agentCommonLogic,
    private readonly cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.refreshData();
  }

  /** 获取列表数据 */
  public refreshData(): void {
    this.loading = true;
    const params = {
      limit: this.pageSize,
      offset: (this.currentPage - 1) * this.pageSize,
      name: this.searchName || undefined,
    };

    this.api
      .getIntentGroupList(params)
      .then((res: any) => {
        this.displayData = res?.intents ?? [];
        this.totalNumber = res.count ?? 0;
        this.refreshCheckedStatus();
      })
      .catch(() => {
        this.displayData = [];
        this.totalNumber = 0;
      })
      .finally(() => {
        this.loading = false;
        this.cdr.detectChanges();
      });
  }

  /** 搜索 */
  public onSearch(): void {
    this.currentPage = 1;
    this.refreshData();
  }

  /** 分页索引变化 */
  public onPageIndexChange(index: number): void {
    this.currentPage = index;
    this.refreshData();
  }

  /** 分页大小变化 */
  public onPageSizeChange(size: number): void {
    this.pageSize = size;
    this.currentPage = 1;
    this.refreshData();
  }

  /** 全选逻辑 */
  public onAllChecked(checked: boolean): void {
    this.displayData.forEach(({ intent_id }) => this.updateCheckedSet(intent_id, checked));
    this.refreshCheckedStatus();
  }

  /** 单选逻辑 */
  public onItemChecked(id: string, checked: boolean): void {
    this.updateCheckedSet(id, checked);
    this.refreshCheckedStatus();
  }

  public updateCheckedSet(id: string, checked: boolean): void {
    if (checked) {
      this.setOfCheckedId.add(id);
    } else {
      this.setOfCheckedId.delete(id);
    }
  }

  public refreshCheckedStatus(): void {
    const listCount = this.displayData.length;
    this.checked = listCount > 0 && this.displayData.every(({ intent_id }) => this.setOfCheckedId.has(intent_id));
    this.indeterminate = this.displayData.some(({ intent_id }) => this.setOfCheckedId.has(intent_id)) && !this.checked;
  }

  /** 导出 */
  public exportIntentPackage(): void {
    // 防止连点导致重复导出
    if (this.submitting) {
      return;
    }
    this.submitting = true;
    const params = {
      ids: Array.from(this.setOfCheckedId),
    };
    this.api.exportIntent(params).then(res => {
      CommonUtils.downloadFile(
        new Blob([res], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
        `${this.commonLogic.getFormattedDateTime()}.xlsx`
      );
      this.dismiss();
    }).finally(() => {
      this.submitting = false;
    });
  }

  public dismiss(): void {
    if (this.modalRef) {
      this.modalRef.destroy();
    } else if (this.drawerRef) {
      this.drawerRef.close();
    }
  }
}
