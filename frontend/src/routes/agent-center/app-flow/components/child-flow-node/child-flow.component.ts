/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable import/no-cycle */
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  NgZone,
} from '@angular/core';
import { I18nNamespace } from '@i18n';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { NODE_ACTIONS } from '@routes/agent-center/constants/workflow-common.const';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { takeUntil } from 'rxjs';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IFlowNode, IWorkflowField } from '../../node.type';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { HttpService } from '@services/http.service';
import { NzModalService } from 'ng-zorro-antd/modal';

@Component({
  selector: 'meta-child-flow',
  templateUrl: './child-flow.component.html',
  styleUrls: ['../common-styles.less', './child-flow.component.less'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ChildFlowComponent extends NodeBaseComponent {
  @Input('nodeInfo') nodeInfo: IFlowNode;

  public codeImgUrl = WORKFLOW_SVGS.Workflow;

  public updateFlowTip = '';

  public showUpdatedIcon: string = 'init';

  override actions = [
    {
      id: 'detail',
      label: this.i18n.transform('sub_workflow_details'),
    },
    ...NODE_ACTIONS,
  ];

  public childFlowsUpdated_tip = this.i18n.transform('childFlowsUpdated_tip');

  private childFlowInfo: any;
  workspaceId = ''
  public apiImgUrl = WORKFLOW_SVGS.Workflow;

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private nzModal: NzModalService,
    private ngZone: NgZone,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
    private appAgentRepoServe: AppAgentRepoService,
    private readonly http: HttpService,
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override async ngOnInit(): Promise<void> {
    this.workspaceId = this.http.getWorkspaceId()
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    // 响应式订阅：resNodes 数据到达时重新计算 showUpdatedIcon，避免 ngOnInit 同步读取时数据未到
    this.appFlowServ
      .resNodesUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((childFlowNodes) => {
        const matchedNode = childFlowNodes.find((n) => n.id === this.nodeBase?.id);
        if (matchedNode) {
          this.isChildFlowsUpdated = matchedNode;
          this.updateFlowTip = this.i18n.transform('update_flow_tip', {
            versionName: matchedNode.ref_workflows?.last_version_name,
          });
          this.processChildFlowUpdate();
        }
      });

    // 如果 super.ngOnInit() 中数据已同步到达，也处理一次
    this.updateFlowTip = this.i18n.transform('update_flow_tip', {
      versionName: this.isChildFlowsUpdated?.ref_workflows?.last_version_name,
    });
    this.processChildFlowUpdate();
  }

  private async processChildFlowUpdate() {
    if (this.showUpdatedIcon === 'show' || this.showUpdatedIcon === 'nested') {
      return; // 已经处理过，不重复请求
    }
    if (this.isChildFlowsUpdated?.showIcon) {
      const childFlowInfo = await this.appAgentRepoServe.rollbackFlowVersion(
        this.isChildFlowsUpdated.ref_workflows?.workflow_id,
        this.isChildFlowsUpdated.ref_workflows?.last_version_id,
      );
      this.childFlowInfo = childFlowInfo;

      if (this.configServ.getConfigs().son_workflow_level_limit === false) {
        this.showUpdatedIcon = 'show';
        this.cdr.markForCheck();
        return;
      }

      if (childFlowInfo?.ref_workflows && !childFlowInfo.ref_workflows.length) {
        this.showUpdatedIcon = 'show';
      }

      if (childFlowInfo?.ref_workflows && childFlowInfo.ref_workflows.length) {
        this.showUpdatedIcon = 'nested';
      }
      this.cdr.markForCheck();
    }
  }

  override onClickAction(action: any) {
    if (action.id === 'detail') {
      this.onClickWorkflow();
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  public get versionName() {
    return (
      this.nodeInfo?.configs?.version_name ||
      this.isChildFlowsUpdated?.configs?.version_name ||
      ''
    );
  }

  public openUpdateFlowModal() {
    const { configs, ref_workflows } = this.isChildFlowsUpdated || {};
    this.ngZone.run(() => {
      this.nzModal.confirm({
        nzTitle: this.i18n.transform('update_flow_modal_title'),
        nzContent: configs?.version_name
          ? this.i18n.transform('update_flow_modal_content', {
              versionName: configs.version_name,
              latestVersionName: ref_workflows?.last_version_name,
            })
          : this.i18n.transform('childflowcomponent_273',{last_version_name:ref_workflows?.last_version_name}),
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOnOk: async () => {
          const startNode = this.childFlowInfo?.workflow_details?.nodes?.filter(
            (node) => node.type === 'Start',
          );
          const endNode = this.childFlowInfo?.workflow_details?.nodes?.filter(
            (node) => node.type === 'End',
          );
          const pluginNodes: any =
            this.childFlowInfo?.workflow_details?.nodes?.filter(
              (node) => node.type === 'Plugin',
            );

          const oldInputs = this.nodeInfo.inputs;
          const newIputs = startNode?.[0]?.outputs;
          const updatedInputs = this.fillPreviousInputs(newIputs, oldInputs);

          const bodyParams = {
            id: this.nodeBase?.id,
            inputs: updatedInputs,
            outputs: endNode?.[0]?.outputs,
            type: 'Workflow',
            configs: {
              id: this.childFlowInfo?.workflow_id,
              name: this.childFlowInfo?.name,
              version_id: ref_workflows?.last_version_id,
              version_name: ref_workflows?.last_version_name,
              plugins: pluginNodes?.map((node) => ({
                id: node?.id,
                version: '',
              })),
              type: this.childFlowInfo?.type,
              exception_process:this.nodeInfo.configs.exception_process,
              descriptionText: this.nodeInfo.configs?.descriptionText || ''
            },
          };
          this.appFlowServ.setChildFlowPutBody(bodyParams);
        },
      });
    });
  }

  /** 回填上一次更新版本前，同名且同类型的开始节点输出变量值 */
  private fillPreviousInputs(
    newIputs: IWorkflowField[],
    oldInputs: IWorkflowField[],
  ) {
    return newIputs?.map((item) => {
      let matchingItem = oldInputs?.find(
        (inputItem) =>
          inputItem.name === item.name && inputItem.type === item.type,
      );
      //新版本必填项信息 覆盖旧版本必填项信息
      if (matchingItem) {
        matchingItem.required = item.required
      }
      return matchingItem ?? item;
    });
  }

  public onClickWorkflow() {
    const config = this.nodeInfo.configs;
    const prefixUrl = window.location.href?.split('/home')[0];
    // fromShare 添加的是分享出来的工作流，进只读页面
    const queryParams = `?id=${config.id}&versionId=${config.version_id}&versionName=${config.version_name}&workspace_id=${this.workspaceId}&fromShare=${config.fromShare || ''}`;
    const newurl = `${prefixUrl}/home/agent-center/app-flow/flow${queryParams}`;
    window.open(newurl, '_blank');
  }

  delNode(e: Event) {
    
    e.stopPropagation();
    this.appFlowServ.setNodeAction({
      type: 'delete',
      id: this.nodeBase.id,
    });
  }
}
