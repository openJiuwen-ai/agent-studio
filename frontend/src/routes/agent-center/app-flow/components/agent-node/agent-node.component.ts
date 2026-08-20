import { ChangeDetectorRef, Component, ElementRef, Input, NgZone } from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AppFlowService } from '../../app-flow.service';
import type { IAgentRepo } from '../../node.type';
import { NodeService } from '../../node.service';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { ReadonlyParamsComponent } from '../readonly-params/readonly-params.component';
import { NzModalService } from 'ng-zorro-antd/modal';
import { UpdatePluginsVersionModalComponent } from '@shared/components/update-plugins-version-modal/update-plugins-version-modal.component';
import { takeUntil } from 'rxjs';
import { FlowUtils } from '../../utils/flow-utils';

@Component({
  selector: 'meta-agent-node',
  standalone: true,
  imports: [NodeDependencies, ReadonlyParamsComponent],
  templateUrl: './agent-node.component.html',
  styleUrls: ['../common-styles.less', './agent-node.component.scss'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AgentNodeComponent extends NodeBaseComponent {
  @Input('nodeInfo') nodeInfo: IAgentRepo;

  public refWorkflows = this.appFlowServ.getAppRefs();

  public boundFlowVersionList = [];

  public updateFlowTip = '';

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private ngZone: NgZone,
    private nzModal: NzModalService,
    private i18n: I18NextEagerPipe
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override ngOnInit(): void {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.appFlowServ
      .nodeRefChange$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: any) => {
        FlowUtils.handelNodeRefChange(data, this.nodeInfo?.inputs);
      });

    this.getBoundFlowVersionList(this.nodeInfo.configs?.plugins);
  }

  public forceDetectChanges() {
    this.cdr.detectChanges();
  }

  /** 在容器节点里，打开意图分支绑定的工作流最新版本信息的弹窗 */
  public openUpdateFlowListModal() {
    this.ngZone.run(() => {
      const modalRef = this.nzModal.create({
        nzContent: UpdatePluginsVersionModalComponent,
        nzWidth: 600,
      });
      const instance = modalRef.getContentComponent();
      instance.boundFlowVersionList = this.boundFlowVersionList;
      instance.nodeInfo = this.nodeInfo;
      modalRef.afterOpen.subscribe(() => {
        instance.confirm.subscribe((newBranches: any[]) => {
          this.getBoundFlowVersionList(newBranches);
        });
      });
    });
  }

  /** 比较ref_workflows列表和意图分支绑定的工作流版本，获取Tip提示和待更新的列表信息 */
  private getBoundFlowVersionList(branches: any[]) {
    const list = [];

    branches?.forEach(item => {
      const match = this.refWorkflows.find(subItem => subItem.workflow_id === item.id);

      if (match && match.last_version_id && (Number(match.last_version_id) > Number(item.version_id) || !item.version_id)) {
        list.push({
          ...item,
          last_version_id: match.last_version_id,
        });
      }
    });

    this.updateFlowTip = this.i18n.transform('agentnodecomponent_262', {
      list: list.length,
    });
    this.boundFlowVersionList = list;
  }
}
