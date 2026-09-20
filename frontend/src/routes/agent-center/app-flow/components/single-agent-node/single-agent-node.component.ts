import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AppFlowService } from '../../app-flow.service';
import type { ISingleAgentNode } from '../../node.type';
import { NodeService } from '../../node.service';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { WORKFLOW_SVGS } from '../../flow.const';
import { Clipboard } from '@angular/cdk/clipboard';
import { HttpService } from '@services/http.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { URL_FROM_MULTI_AGENT } from '@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.constant';
import { NzModalService } from 'ng-zorro-antd/modal';
import { SubControllerService } from '@services/agent-center/sub-controller.service';
import { takeUntil } from 'rxjs';
import { ApplicationType } from '@enums/agent-center.enum';

@Component({
  selector: 'meta-single-agent-node',
  templateUrl: './single-agent-node.component.html',
  styleUrls: ['../common-styles.less', './single-agent-node.component.scss'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SingleAgentNodeComponent
  extends NodeBaseComponent
  implements OnInit
{
  @Input('nodeInfo') nodeInfo!: ISingleAgentNode;

  public icon = WORKFLOW_SVGS.SingleAgent;

  public description = '';

  // 升级铃铛：最新版本信息（来自 t_mapping 映射出的 ref_workflows 关系）
  public updateFlowTip = '';
  public last_version_id = '';
  public last_version_name = '';
  public resource_id = '';
  public lastAgentsInfo: any = {};

  private workspaceId = '';

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private i18n: I18NextEagerPipe,
    private ngZone: NgZone,
    private nzModal: NzModalService,
    private SubControllerService: SubControllerService,
    private clipboard: Clipboard,
    private readonly http: HttpService,
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override ngOnChanges(changes: SimpleChanges) {
    super.ngOnChanges(changes);
    this.description = this.nodeInfo.configs?.intent?.description
      ? this.nodeInfo.configs?.intent?.description
      : this.nodeInfo.configs?.description;
  }

  override ngOnInit(): void {
    this.workspaceId = this.http.getWorkspaceId();
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    // resNodesUpdate 为 BehaviorSubject（订阅即得当前值）。
    // 铃铛展示由基类订阅写入的 isChildFlowsUpdated.showIcon 驱动；
    // 此处提取 ref_workflows 中的最新版本信息，供升级动作使用
    this.appFlowServ
      .resNodesUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((childFlowNodes) => {
        const matchedNode = childFlowNodes.find(
          (n) => n.id === this.nodeBase?.id,
        );
        if (matchedNode?.ref_workflows) {
          const { ref_workflows } = matchedNode;
          this.updateFlowTip = this.i18n.transform('update_flow_tip', {
            versionName: ref_workflows?.last_version_name,
          });
          this.last_version_id = ref_workflows?.last_version_id ?? '';
          this.last_version_name = ref_workflows?.last_version_name ?? '';
          this.resource_id = ref_workflows?.workflow_id ?? '';
        }
      });
  }

  public get versionId() {
    return this.nodeInfo?.configs?.version_id || '';
  }

  override actions = [
    {
      id: 'detail',
      label: this.i18n.transform('agent_detail'),
    },
    {
      id: 'copyId',
      label: this.i18n.transform('copy_agent_id'),
    },
  ];

  override onClickAction(action: { id: string }): void {
    switch (action.id) {
      case 'detail': {
        this.onClickAgentDetail();
        break;
      }
      case 'copyId': {
        this.onCopyAgentId();
        break;
      }
      default: {
        break;
      }
    }
  }

  private onClickAgentDetail(): void {
    const config = this.nodeInfo.configs;
    const prefixUrl = window.location.href?.split('/home')[0];
    const queryParams = `?agentId=${config.id}&versionId=${config.version_id}&versionName=${config.version_name}&from=${URL_FROM_MULTI_AGENT}&readonly_mode=true&workspace_id=${this.workspaceId}`;
    const newUrl = `${prefixUrl}/home/agent-center/app-agent/detail${queryParams}`;
    window.open(newUrl, '_blank');
  }

  private onCopyAgentId(): void {
    this.clipboard.copy(this.nodeInfo.configs.id);
    MessageComponent.showSuccess(
      this.i18n.transform('copy_single_agent_id_successfully'),
    );
  }

  /**
   * 画布单智能体节点点击升级铃铛（仅多智能体画布会出现）：
   * 拉取最新发布版本详情，构造与编排弹窗 getSubSingleAgent 同构的 configs，
   * 复用 SubController 升级的 setSubAgentsBody 通道——flow.component 的
   * subAgentsBodyUpdate$ 订阅会同步更新画布节点与 Controller configs.agents
   * 对应成员并自动保存，不改变既有业务流程。
   */
  public onConfirmUpdateFlow(): void {
    const configs: any = this.nodeInfo.configs;
    const last_version_name = this.last_version_name;

    this.ngZone.run(() => {
      this.nzModal.confirm({
        nzTitle: this.i18n.transform('update_flow_modal_title'),
        nzContent: configs?.version_name
          ? this.i18n.transform('update_agent_modal_content', {
              versionName: configs.version_name,
              latestVersionName: last_version_name,
            })
          : this.i18n.transform('sub-controller-node_1', {
              version: last_version_name,
            }),
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOkType: 'primary',
        nzOnOk: async () => {
          await this.getAgentLastVersionInfo();

          const agentInfo = this.lastAgentsInfo;
          agentInfo.version_id = this.last_version_id;
          agentInfo.version_name = this.last_version_name;

          // configs 与编排弹窗 getSubSingleAgent 生成的单智能体成员 DSL 同构；
          // 保留画布节点已有 intent（与 SubController 画布升级先例一致），
          // fromShare/valid 等其余字段由 createMultiAgentTree 的
          // getMergedConfigs 从画布节点旧 configs 合并回来
          const bodyParams = {
            id: this.nodeInfo?.id,
            name: agentInfo.name,
            type: 'Agent',
            configs: {
              node_id: '',
              id: agentInfo.agent_id,
              name: agentInfo.name,
              mode: 'PlanExecute',
              type: ApplicationType.SINGLE_AGENT,
              description: agentInfo.description,
              version: this.last_version_id,
              version_id: this.last_version_id,
              version_name: this.last_version_name,
              model: {
                model_name: agentInfo.model_name,
                model_type: agentInfo.model_type,
                id: agentInfo.model_deployment_id,
                model_deployment_id: agentInfo.model_deployment_id,
              },
              workflows: agentInfo.workflows,
              agents: [],
              intent: configs?.intent,
            },
          };

          this.SubControllerService.setSubAgentsBody(bodyParams);
        },
      });
    });
  }

  public async getAgentLastVersionInfo(): Promise<void> {
    await this.SubControllerService.getPublishedMutilAgentDetails(
      this.resource_id,
      this.last_version_id,
    ).then((val: any): void => {
      this.lastAgentsInfo = val;
    });
  }
}
