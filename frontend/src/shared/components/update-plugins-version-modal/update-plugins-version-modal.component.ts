import { Component, Input, Output, EventEmitter, inject } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NodeDependencies } from '@routes/agent-center/app-flow/components/modules';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import type { IIntentContainerBranch, IAgentRepo } from '@routes/agent-center/app-flow/node.type';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
@Component({
  selector: 'meta-update-plugins-version-modal',
  templateUrl: './update-plugins-version-modal.component.html',
  styleUrls: ['./update-plugins-version-modal.component.scss'],
  standalone: true,
  imports: [MODULES, NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class UpdatePluginsVersionModalComponent {
  @Input() boundFlowVersionList = [];

  @Input('nodeInfo') nodeInfo: IAgentRepo;

  @Output('confirm') confirm = new EventEmitter<IIntentContainerBranch[]>();

  readonly modalRef = inject(NzModalRef);

  public table: any = {
    checkedList: [],
    displayedData: [],
    srcData: {
      data: [],
      state: undefined,
    },
    currentPage: 1,
    totalNumber: 0,
  };

  public columns: Array<any> = [
    {
      title: this.i18n.transform('plugin_name'),
    },
    {
      title: this.i18n.transform('current_version'),
    },
    {
      title: this.i18n.transform('latest_version'),
    },
  ];

  public pageSize: any = {
    options: [6],
    hide: true,
  };

  constructor(
    private appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe
  ) {}

  ngOnInit(): void {
    this.table.srcData.data = this.boundFlowVersionList;
    this.table.totalNumber = this.boundFlowVersionList.length;
  }

  public trackByFn(index: number, item: any): number {
    return item.branch_id;
  }

  public isAllChecked(): boolean {
    return this.table.displayedData.length > 0 && this.table.displayedData.every(row => this.table.checkedList.indexOf(row) !== -1);
  }

  public isIndeterminate(): boolean {
    return this.table.checkedList.length > 0 && this.table.checkedList.length < this.table.displayedData.length;
  }

  public onAllCheckedChange(checked: boolean): void {
    if (checked) {
      this.table.displayedData.forEach(row => {
        if (this.table.checkedList.indexOf(row) === -1 && !row.disabled) {
          this.table.checkedList.push(row);
        }
      });
    } else {
      this.table.checkedList = [];
    }
  }

  public onItemCheckedChange(row: any, checked: boolean): void {
    if (checked) {
      if (this.table.checkedList.indexOf(row) === -1) {
        this.table.checkedList.push(row);
      }
    } else {
      this.table.checkedList = this.table.checkedList.filter(item => item !== row);
    }
  }

  public updateVersions() {
    // 用户手动选上的插件的最新版本信息
    const pluginsSelected = this.table.checkedList.map(item => ({
      description: item.description,
      id: item.id,
      name: item.name,
      version_id: item.last_version_id,
    }));

    const plugins = this.nodeInfo.configs.plugins.map(item => {
      const matchingItem = pluginsSelected.find(subItem => item.id === subItem.id);
      return matchingItem || item;
    });
    this.appFlowServ.setContainerDsl({
      ...this.nodeInfo,
      configs: {
        ...this.nodeInfo.configs,
        plugins,
      },
    });
    this.confirm.emit(plugins);
    this.close();
  }

  close(): void {
    this.modalRef.destroy();
  }

  dismiss() {
    this.close();
  }
}
