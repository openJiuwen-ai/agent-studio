import { CommonModule } from '@angular/common';
import { ChangeDetectorRef, Component, ContentChild, EventEmitter, Input, Output, SimpleChanges, TemplateRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { NzModalService } from 'ng-zorro-antd/modal';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { ModelImageDataService } from '@routes/agent-center/app-agent/components/info-and-prompt-builder/model-image-src.service';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { CommonService } from '@services/common.service';
import { MODULES } from '@shared/modules';
import { environment } from 'src/environment/environment';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { type IWorkflow } from '../../app-flow.types';
import { ModifyWorkflowComponent } from '../modify-workflow/modify-workflow.component';

@Component({
  selector: 'flow-detail-header',
  templateUrl: './flow-detail-header.component.html',
  styleUrls: ['./flow-detail-header.component.less'],
  standalone: true,
  imports: [MODULES, CommonModule, FormsModule, NzIconModule, NzToolTipModule],
})
export class FlowDetailHeaderComponent {
  @Input('isFlowReadonly') isFlowReadonly = false;

  // 左边操作区
  @ContentChild('opLeft') opLeftTemplate: TemplateRef<any>;

  // 右边操作区
  @ContentChild('opRight') opRightTemplate: TemplateRef<any>;

  @ContentChild('center') centerTemplate: TemplateRef<any>;

  // 右边操作区
  @ContentChild('statusBar') statusBarTemplate: TemplateRef<any>;

  @Input() workflowDetail: IWorkflow;

  @Input() isFromAgentBuilder: boolean = false;

  @Input() loading = false;

  @Input() showDivider = false;

  @Input() showLeftDivider = false;

  @Output() backClick = new EventEmitter<void>();

  @Output() titleChange = new EventEmitter<string>();

  @Input() public logo = '';

  public isPOC = environment.envType === 'poc';

  public type = '';
  experienceCreation = false;
  studioBtnShow = true;
  constructor(
    private nzModal: NzModalService,
    private cdr: ChangeDetectorRef,
    private configServ: AgentConfigService,
    private route: ActivatedRoute,
    private appFlowRepoServ: AppFlowRepoService,
    private modelImageDataService: ModelImageDataService,
    private appFlowServe: AppFlowService,
    private commonService: CommonService
  ) {
    this.studioBtnShow = this.configServ.getConfigs()?.studio_btn_show;
    this.route.queryParams.subscribe(params => {
      const { type, from } = params;
      this.type = type ?? '';
      if (from === 'experience-creation') {
        this.experienceCreation = true;
      }
    });
  }

  get site() {
    return this.configServ.getConfigs().site;
  }

  public onClickBack(): void {
    this.backClick.emit();
  }

  public onClickEditor() {
    const modal: NzModalRef = this.nzModal.create({
      nzContent: ModifyWorkflowComponent,
      nzWidth: '520px',
      nzFooter: null,
      nzMaskClosable: false,
      nzClosable: true,
    });
    Object.assign(modal.componentInstance, {
      workflowDetail: this.workflowDetail,
      type: this.type,
    });
    modal.componentInstance.workflowDetailChange.subscribe((workflowDetail: IWorkflow) => {
      this.workflowDetail = workflowDetail;
      this.logo = this.workflowDetail?.avatar;
      this.cdr.detectChanges();
    });
  }

  ngOnChanges(changes: SimpleChanges) {
    if (changes.workflowDetail?.currentValue?.update_time && this.experienceCreation) {}
  }

  createFlow(icon, workflow_id, update_time) {
    this.appFlowRepoServ
      .modifyFlow({
        avatar: icon,
        workflow_id: workflow_id,
        update_time: update_time,
      })
      .then(res => {
        this.logo = res.avatar;
        this.experienceCreation = false;
        this.appFlowServe.setVersionInfo(res.update_time);
        this.workflowDetail = res;
        this.iconLoading = false;
        this.cdr.detectChanges();
      });
  }
  iconLoading = false;

  generationImage(description, name, workflow_id, update_time) {
    this.iconLoading = true;
    this.modelImageDataService
      .getModelImageData({
        name: name,
        description: description,
      })
      .then(res => {
        this.createFlow(res.icons.icon, workflow_id, update_time);
      });
  }
  protected readonly changeUrl = cdnAssetUrl;
}
