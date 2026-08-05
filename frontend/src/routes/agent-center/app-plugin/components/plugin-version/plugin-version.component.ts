import { Component, Input, inject, Output, EventEmitter, Inject, ChangeDetectorRef } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { DeleteRefsService } from '@shared/services/delete-refs.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { NoDataIconComponent } from '@shared/components//no-data-icon/no-data-icon.component';
import { PipesModule } from '../../../../../pipes/pipes.module';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTypographyModule } from 'ng-zorro-antd/typography';
import { NzSpaceModule } from 'ng-zorro-antd/space';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NZ_DRAWER_DATA, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzMessageService } from 'ng-zorro-antd/message';
import { Subject, takeUntil } from 'rxjs';

@Component({
  selector: 'meta-plugin-version',
  templateUrl: './plugin-version.component.html',
  styleUrl: './plugin-version.component.scss',
  standalone: true,
  imports: [MODULES, NoDataIconComponent, PipesModule, NzIconModule, NzTypographyModule, NzSpaceModule, NzSpinModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
    DeleteRefsService,
  ],
})
export class PluginVersionComponent {
  @Input() tool_id = '';

  readonly drawerRef = inject(NzDrawerRef);

  isLoading = false;

  publishedCards = [];

  public selectedTab = -1;

  private destroy$ = new Subject<void>();

  selectVersionInfo = null;
  constructor(
    private i18n: I18NextEagerPipe,
    private deleteRefsServe: DeleteRefsService,
    private agentRepoServe: AppAgentRepoService,
    private agentDataServe: AgentDataService,
    private modal: NzModalService,
    private message: NzMessageService,
    @Inject(NZ_DRAWER_DATA) public nzData: any,
    private cdr: ChangeDetectorRef
  ) {
    this.agentDataServe
      .getPreviewVersion()
      .pipe(takeUntil(this.destroy$))
      .subscribe(versionInfo => {
        this.selectVersionInfo = versionInfo;
      });
  }

  ngOnInit(): void {
    this.tool_id = this.nzData.tool_id;
    this.getPluginVersionList();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  getPluginVersionList(isDelete = false) {
    this.isLoading = true;
    this.agentRepoServe
      .getPluginVersionList(this.tool_id)
      .then(res => {
        this.publishedCards = res.version_list;
        if (isDelete && !this.selectVersionInfo?.version_id) {
          this.agentDataServe.setPreviewVersion(undefined);
        }
      })
      .finally(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  deleteVersionModal(event, version_id) {
    event.preventDefault();

    const query = {
      version: version_id,
      resource_type: 'tool',
    };

    this.deleteRefsServe.onDeleteRefs(
      {
        id: this.tool_id,
        query,
      },
      {
        title: this.i18n.transform('del_workflow_version'),
        alertText: this.i18n.transform('del_plugin_version_tips'),
        secondConfirmLabel: `${this.i18n.transform('del_sure_tips')} <strong>DELETE</strong>`,
        tiMsgTitle: this.i18n.transform('del_plugin_version_title'),
        tiMsgContent: this.i18n.transform('del_plugin_version_msg_content'),
      },
      () => {
        this.deleteVersion(version_id);
      }
    );
  }

  deleteVersion(version_id) {
    this.agentRepoServe
      .deletePluginVersion(this.tool_id, version_id)
      .then(() => {
        this.isLoading = false;
        this.publishedCards = this.publishedCards.filter(item => item.version_id !== version_id);
        this.getPluginVersionList(true);
        MessageComponent.showSuccess(this.i18n.transform('version_deleted_successfully'), 3000);
      })
      .finally(() => {
        this.isLoading = false;
        this.cdr.markForCheck();
      });
  }

  cardClick($event, { version_id, version_name }, index) {
    this.selectedTab = index;
    if ($event.target.nodeName !== 'A') {
      this.agentDataServe.setPreviewVersion({ version_id, version_name });
    }
  }

  exitPreview() {
    this.selectedTab = -1;
    this.agentDataServe.setPreviewVersion(undefined);
    if (this.drawerRef?.close) {
      this.drawerRef?.close();
    }
  }

  restoreVersion(event, card) {
    this.modal.create({
      nzTitle: '确定还原该版本吗?',
      nzContent: '还原后，将覆盖最新编写的内容，使用原本版本配置的内容',
      nzMaskClosable: false,
      nzClosable: false,
      nzOnOk: () => {
        this.agentRepoServe.restorePluginVersion(this.tool_id, card.version_id).then(res => {
          if (this.nzData.update) {
            this.message.create(`success`, `版本还原成功`);
            this.nzData.update();
            this.drawerRef?.close();
          }
        });
      },
    });
  }
}
