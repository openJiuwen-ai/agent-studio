import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  Output,
} from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { NzModalService } from 'ng-zorro-antd/modal';
import { ActivatedRoute } from '@angular/router';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { NoDataIconComponent } from '../no-data-icon/no-data-icon.component';
import { Subject, takeUntil } from 'rxjs';
import { MessageComponent } from '@shared/services/cfdata.service';
import { DeleteRefsService } from '@shared/services/delete-refs.service';
import { RestoreVersionModalComponent } from '../restore-version-modal/restore-version-modal.component';
import type { IWorkflow } from '@routes/agent-center/app-flow/app-flow.types';
import { PipesModule } from '../../../pipes/pipes.module';
import { DiffVersionModalComponent } from './diff-version-modal/diff-version-modal.component';

@Component({
  selector: 'release-history-halfmodal',
  templateUrl: './release-history-halfmodal.component.html',
  styleUrls: ['./release-history-halfmodal.component.scss'],
  standalone: true,
  imports: [MODULES, NoDataIconComponent, PipesModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
    DeleteRefsService,
  ],
})
export class ReleaseHistoryHalfmodalComponent {
  @Input() isShowHistory = false;

  @Input() type = 'agent';

  @Input() workflowDetail: IWorkflow;

  @Output('close') close = new EventEmitter<void>();

  public publishedCards = [];

  public isLoading = false;

  private app_id = '';

  private app_type = 'agent';
  private destroy$ = new Subject<void>();
  public selectedTab = -1;

  constructor(
    private route: ActivatedRoute,
    private agentRepoServe: AppAgentRepoService,
    private agentDataServe: AgentDataService,
    private nzModal: NzModalService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private deleteRefsServe: DeleteRefsService,
  ) {
    this.route.queryParams.subscribe((params) => {
      this.app_id = params.agentId || params.id;
      if (params.id && !params.type) {
        this.app_type = 'workflows';
      }
    });
  }

  ngOnInit() {
    if (this.type === 'agent' || this.type === 'multi') {
      this.getAgentVersions();
    } else if(this.type === 'workflow' ){
      this.getFlowVersions();
    }
    this.agentDataServe
      .publishStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((status: string) => {
        if (status === 'succeeded') {
          if (this.type === 'agent' || this.type === 'multi') {
            this.getAgentVersions();
          } else if(this.type === 'workflow' ){
            this.getFlowVersions();
          }
        }
      });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  public onClose() {
    this.close.emit();
  }

  public revertDraft() {
    this.selectedTab = -1;
    this.agentDataServe.setRollbackId({
      version_id: '',
      version_name: '',
      isFlowReadonly: false,
      draft: true,
    });
  }

  public viewHistory($event, card, index = 0) {
    this.selectedTab = index;
    if ($event.target.nodeName !== 'A') {
      this.agentDataServe.setRollbackId({
        version_id: card?.version_id,
        version_name: card?.version_name,
        isFlowReadonly: true,
      });
    }
  }

  /** 还原版本的二次确认弹窗 */
  public restoreVersion(version_id: string) {
    const modalRef = this.nzModal.create({
      nzTitle: '',
      nzContent: RestoreVersionModalComponent,
      nzWidth: 400,
      nzFooter: null,
      nzClosable: false,
    });
    const instance = modalRef.getContentComponent();
    instance.type = this.type;
    instance.close = (): void => {
      this.agentDataServe.setRollbackId({
        version_id: version_id,
        isFlowReadonly: false,
        revert: true,
      });
      modalRef.close();
    };
    instance.dismiss = (): void => {
      modalRef.close();
    };
  }

  /** 删除版本的二次确认弹窗 */
  public openDeleteVersionModal(version_id: string) {
    let resource_type: string;
    if (this.type === 'agent') {
      resource_type = 'agent';
    } else if (this.type === 'multi') {
      resource_type = 'controller';
    } else {
      resource_type = 'workflow';
    }
    this.deleteRefsServe.onDeleteRefs(
      {
        id: this.app_id,
        query: {
          resource_type,
          version:version_id,
        },
      },
      {
        title: this.i18n.transform('del_workflow_version'),
        alertText: this.i18n.transform('del_plugin_version_tips'),
        secondConfirmLabel: `${this.i18n.transform(
          'del_sure_tips',
        )} <strong>DELETE</strong>`,
        tiMsgTitle: this.i18n.transform('del_plugin_version_title'),
        // tiMsgContent: this.i18n.transform('del_plugin_version_content'),
        tiMsgContent: '',
      },
      () => {
        this.deleteVersion(version_id);
      },
    );
  }

  public clickCopy(e: Event, version_id: string) {
    e.stopPropagation();
    if (!version_id) {
      return;
    }
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(version_id).then(
        () => {
          MessageComponent.showSuccess(
            this.i18n.transform('copy_success'),
            3000,
          );
        },
        () => {
          this.fallbackCopy(version_id);
        },
      );
    } else {
      this.fallbackCopy(version_id);
    }
  }

  private fallbackCopy(text: string) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
      document.execCommand('copy');
      MessageComponent.showSuccess(
        this.i18n.transform('copy_success'),
        3000,
      );
    } finally {
      document.body.removeChild(textarea);
    }
  }

  private getFlowVersions() {
    this.isLoading = true;
    this.agentRepoServe.getFlowVersion(this.app_id).then(
      (res: any) => {
        this.isLoading = false;
        const { version_list } = res || {};
        this.publishedCards = version_list;
        this.agentDataServe.setVersionList(version_list);
        this.cdr.markForCheck();
      },
      () => {
        this.isLoading = false;
        this.publishedCards = [];
        this.agentDataServe.setVersionList([]);
        this.cdr.markForCheck();
      },
    );
  }
  private getAgentVersions() {
    this.isLoading = true;
    this.agentRepoServe.getAgentVersionList(this.app_id).then(
      (res: any) => {
        this.isLoading = false;
        const { version_list } = res || {};
        this.publishedCards = version_list;
        this.agentDataServe.setVersionList(version_list);
        this.cdr.markForCheck();
      },
      () => {
        this.isLoading = false;
        this.publishedCards = [];
        this.agentDataServe.setVersionList([]);
        this.cdr.markForCheck();
      },
    );
  }

  private deleteVersion(version_id: string) {
    this.isLoading = true;
    if (['agent', 'multi'].includes(this.type)) {
      this.agentRepoServe.deleteAgentVersion(this.app_id, version_id).then(
        () => {
          this.postDel(version_id);
          this.cdr.markForCheck();
        },
        () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        },
      );
    } else {
      this.agentRepoServe.deleteFlowVersion(this.app_id, version_id).then(
        () => {
          this.postDel(version_id);
          this.cdr.markForCheck();
        },
        () => {
          this.isLoading = false;
          this.cdr.markForCheck();
        },
      );
    }
  }

  private postDel(version_id: string) {
    this.isLoading = false;
    this.publishedCards = this.publishedCards.filter(
      (item) => item.version_id !== version_id,
    );
    if (this.type === 'agent' || this.type === 'multi') {
      this.getAgentVersions();
    } else {
      this.getFlowVersions();
    }
    MessageComponent.showSuccess(
      this.i18n.transform('version_deleted_successfully'),
      3000,
    );
  }

  showDiff(e, index) {
    e.stopPropagation();
    e.preventDefault();
    const modalRef = this.nzModal.create({
      nzContent: DiffVersionModalComponent,
      nzWidth: 1100,
      nzFooter: null,
    });
    const instance = modalRef.getContentComponent();
    instance.app_id = this.app_id;
    instance.versionList = this.publishedCards;
    instance.leftIndex = this.selectedTab;
    instance.rightIndex = index;
    instance.type = this.type;
  }
}
