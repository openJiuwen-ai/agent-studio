import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { DeleteRefsService } from '@shared/services/delete-refs.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { NoDataIconComponent } from '@shared/components//no-data-icon/no-data-icon.component';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { ShareDeleteModalComponent } from '../share-delete-modal/share-delete-modal.component';
import { SHARE_PAGE, SHARE_TOOL_TYPE } from '../edit-share-modal/edit-share-modal.config';
import { ShareService } from '../edit-share-modal/share.service';
import { CardService } from '@routes/agent-center/my-card/card.service';
import { Router } from '@angular/router';

@Component({
  selector: 'share-version',
  templateUrl: './share-version.component.html',
  styleUrl: './share-version.component.scss',
  standalone: true,
  imports: [MODULES, NoDataIconComponent, NzSpinModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
    DeleteRefsService,
  ],
})
export class ShareVersionComponent {
  @Input() toolId = '';
  @Input() versionId = '';
  @Input() shareInfo: any = {};
  @Input() visionsList = [];
  @Input() pageType = SHARE_PAGE.apply;
  @Input() toolType: SHARE_TOOL_TYPE = SHARE_TOOL_TYPE.workflow;
  @Output() changeVersion = new EventEmitter();
  @Output() changeShearVersion = new EventEmitter();
  isLoading = false;


  public selectedId = '';

  constructor(
    private i18n: I18NextEagerPipe,
    private deleteRefsServe: DeleteRefsService,
    private agentRepoServe: AppAgentRepoService,
    private agentDataServe: AgentDataService,
    private nzModal: NzModalService,
    private shareService: ShareService,
    private cardService: CardService,
    private router: Router,
  ) { }

  ngOnInit(): void {
    this.selectedId = this.versionId;
  }


  deleteVersionModal(event, version_id) {
    // 查看引用情况
    event.stopPropagation();
    this.getReferList(this.shareInfo, version_id);
  }

  deleteVersion(versionId?: string) {
    if (!versionId){
      versionId = this.selectedId;
    }
    this.isLoading = true;
    const versionList = this.visionsList.filter(v => v.version_id !== versionId).map(v => v.version_id);
    if (this.visionsList.length === 1) {
      // 只有一个走删除
      this.shareService.deleteShare(this.shareInfo.resource_id, {
        resource_type: this.shareInfo.resource_type,
      }).then((res) => {
        this.isLoading = false;
        // 返回列表
        this.backHome();
      }).finally(() => {
        this.isLoading = false;
      });
    } else {
      const params = {
        auth_workspace_id_list: this.shareInfo.workspace_list.map(v => {
          return v.workspace_id;
        }),
        resource_name: this.shareInfo.resource_name,
        resource_type: this.shareInfo.resource_type,
        resource_id:this.shareInfo.resource_id,
        version_list: versionList,
      }
      this.shareService.postShare(params).then((res) => {
        this.isLoading = false;
        MessageComponent.showSuccess(
          this.i18n.transform('version_deleted_successfully'),
          3000,
        );
        this.changeShearVersion.emit(versionList[0]);
        this.close();
      }).finally(() => {
        this.isLoading = false;
      });
    }
  }

  private getReferList(data, version_id) {
    const param = {
      offset: 0,
      limit: 100,
      reference_type: 'share',
      resource_type:  data.resource_type === SHARE_PAGE.plugin ? 'tool': data.resource_type,
      version: version_id,
    };
    this.cardService
      .selectQuoteList(data.resource_id, param)
      .then((res) => {
        let count = res.count;
        if (count) {
          this.openShareDelModal(data, version_id);
        } else {
          this.deleteVersion(version_id);
        }
      })
      .finally(() => {
      });
  }

  private openShareDelModal(data, versionId) {
    const modal = this.nzModal.create({
      nzTitle: this.i18n.transform('sharedetailbtn-1'),
      nzContent: ShareDeleteModalComponent,
      nzData: {
        shareData: data,
        versionId: versionId,
        pageType: this.pageType,
      },
      nzOnOk: () => {
        this.deleteVersion();
      },
    });
  }

  cardClick($event, { version_id, version_name }, index) {
    this.selectedId = version_id;
    this.changeVersion.emit(version_id);
  }

  backHome(){
    if(this.shareInfo.resource_type === SHARE_PAGE.plugin){
      this.router.navigate(['/home/plugin-market'],{
        state:{
          formTab: 'share',
          myShare: true,
        }
      });
    } else{
      this.router.navigate(['/home/app-library'],{
        state:{
          formTab: 'share',
          myShare: true,
        }
      });
    }
  }

  dismiss() { }
  close() { }
}
