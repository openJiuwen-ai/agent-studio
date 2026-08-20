import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  NgZone,
  OnInit, SimpleChanges,
} from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AppFlowService } from '../../app-flow.service';
import type { IControllerNode } from '../../node.type';
import { NodeService } from '../../node.service';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { WORKFLOW_SVGS } from '../../flow.const';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { MessageComponent } from '@shared/services/cfdata.service';
import { Clipboard } from '@angular/cdk/clipboard';
import { NzModalService } from 'ng-zorro-antd/modal';
import { SubControllerService } from '@services/agent-center/sub-controller.service';
import { ActivatedRoute } from '@angular/router';
import { takeUntil } from 'rxjs';
import { v4 as uuidV4 } from "uuid";
import { HttpService } from '@services/http.service';

enum mapKeys {
  id = 'id'
}

@Component({
  selector: 'meta-sub-controller-node',
  templateUrl: './sub-controller-node.component.html',
  styleUrls: ['../common-styles.less', './sub-controller-node.component.scss'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SubControllerNodeComponent
  extends NodeBaseComponent
  implements OnInit
{
  @Input('nodeInfo') nodeInfo: IControllerNode;

  public icon = WORKFLOW_SVGS.Controller;

  public changeUrl = cdnAssetUrl;

  public showUpdatedIcon: boolean = false;
  public updateFlowTip: string = '';
  public agent_id = '';
  public relations;
  public lastAgentsInfo: any = {};
  public last_version_id = '';
  public last_version_name = '';
  public resource_id = '';
  description = ''
  workspaceId = ''
  public apiImgUrl = WORKFLOW_SVGS.Controller;
  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private i18n: I18NextEagerPipe,
    private ngZone: NgZone,
    private nzModal: NzModalService,
    private SubControllerService: SubControllerService,
    private route: ActivatedRoute,
    private clipboard: Clipboard,
    private readonly http: HttpService,
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
    this.SubControllerService.agentsNodesUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info: boolean) => {
        if (info) {

        }
      });
  }

  override ngOnChanges(changes: SimpleChanges) {
    super.ngOnChanges(changes);
    this.description =this.nodeInfo.configs?.intent?.description?this.nodeInfo.configs?.intent?.description:this.nodeInfo.configs?.description
  }

  override async ngOnInit(): Promise<void> {
    this.workspaceId = this.http.getWorkspaceId()
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.agent_id = this.route.snapshot.queryParams[mapKeys.id];

    // 响应式订阅：resNodes 数据到达时更新版本相关字段，避免 ngOnInit 同步读取时数据未到
    this.appFlowServ
      .resNodesUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((childFlowNodes) => {
        const matchedNode = childFlowNodes.find((n) => n.id === this.nodeBase?.id);
        if (matchedNode) {
          this.isChildFlowsUpdated = matchedNode;
          const { ref_workflows } = matchedNode;
          this.updateFlowTip = this.i18n.transform('update_flow_tip', {
            versionName: ref_workflows?.last_version_name,
          });
          this.relations = ref_workflows;
          this.last_version_id = ref_workflows?.last_version_id ?? '';
          this.last_version_name = ref_workflows?.last_version_name ?? '';
          this.resource_id = ref_workflows?.workflow_id ?? '';
        }
      });

    // 如果 super.ngOnInit() 中数据已同步到达，也处理一次
    const { ref_workflows } = this.isChildFlowsUpdated || {};
    this.updateFlowTip = this.i18n.transform('update_flow_tip', {
      versionName: ref_workflows?.last_version_name,
    });
    this.relations = ref_workflows;
    this.last_version_id = ref_workflows?.last_version_id ?? '';
    this.last_version_name = ref_workflows?.last_version_name ?? '';
    this.resource_id = ref_workflows?.workflow_id ?? '';
    this.actions[0].disabled = this.route.snapshot.queryParams.fromShare === 'true';
  }

  public get versionId() {
    return (
      this.nodeInfo?.configs?.version_id ||
      this.isChildFlowsUpdated?.configs?.version_id ||
      ''
    );
  }

  override actions = [
    {
      id: 'detail',
      label: this.i18n.transform('agent_detail'),
      disabled: false,
    },
    {
      id: 'copyId',
      label: this.i18n.transform('copy_agent_id'),
      disabled: false,
    },
  ];
  override onClickAction(action: any) {
    switch (action.id) {
      case 'detail': {
        this.onClickAgentsflow();
        break;
      }
      case 'copyId': {
        this.onClickAgentsflowId();
        break;
      }
      default: {
        break;
      }
    }
  }
  get normalFlows() {
    return this.nodeInfo.configs?.workflows?.filter(
      (item) => item?.type === 'Normal',
    );
  }

  get startFlow() {
    return this.nodeInfo.configs?.workflows?.filter(
      (item) => item?.type === 'Start',
    );
  }

  get intentDetectionFlow() {
    return this.nodeInfo.configs?.workflows?.filter(
      (item) => item?.type === 'IntentIdentification',
    );
  }

  get endFlow() {
    return this.nodeInfo.configs?.workflows?.filter(
      (item) => item?.type === 'End',
    );
  }
  public onClickAgentsflow() {
    const config = this.nodeInfo.configs;
    const prefixUrl = window.location.href?.split('/home')[0];
     // fromShare 添加的是分享出来的工作流，进只读页面
    const queryParams = `?id=${config.id}&type=multi&versionId=${config.version_id}&versionName=${config.version_name}&workspace_id=${this.workspaceId}&fromShare=${config.fromShare || ''}`;

    const newurl = `${prefixUrl}/home/agent-center/app-flow/flow${queryParams}`;
    window.open(newurl, '_blank');
  }

  public onClickAgentsflowId() {
    const config = this.nodeInfo.configs;
    this.clipboard.copy(config.id);
    MessageComponent.showSuccess(
      this.i18n.transform('copy_workflow_id_successfully'),
    );
  }

  public async onConfirmUpdateFlow() {

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
          : this.i18n.transform('sub-controller-node_1',{
            version:last_version_name,
          }),
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOkType: 'primary',
        nzOnOk: async () => {

          await this.getAgentLastVersionInfo();

          this.lastAgentsInfo.version_id = this.last_version_id;
          this.lastAgentsInfo.version_name = this.last_version_name;

          const last_agents_detials = this.lastAgentsInfo.details.nodes.filter(
            (nodes) => nodes.type === 'Controller',
          )[0];
          const last_agnets_wf = this.lastAgentsInfo.details.nodes.filter(
            (nodes) => nodes.type === 'Workflow',
          );

          const nodeIdMap = {
            start: `Start`,
            end: `End`,
            node: `Normal`,
            default: `Default`,
            intentIdentification: `IntentIdentification`,
          };
          last_agnets_wf.forEach((item) => {
            const type = item.id.split('_')[0];
            item.node_id = item.id;
            item.type =nodeIdMap[type];
            item.parent_node_type = 'sub_controller';
          });

          const bodyParams = {
            id: this.nodeInfo?.id,
            name: this.lastAgentsInfo.name,
            type: 'SubController',
            configs: {
              agents: last_agents_detials.configs.agents,
              chat_history_max_turn:
                last_agents_detials.configs.chat_history_max_turn,
              creator: this.lastAgentsInfo.creator,
              description: this.lastAgentsInfo.description,
              disabled: '',
              enable_history: last_agents_detials.configs.enable_history,
              global_intents: last_agents_detials.configs.global_intents,
              icon: this.lastAgentsInfo.icon,
              id: this.lastAgentsInfo.details.id,
              max_iteration: last_agents_detials.configs.max_iteration,
              model: last_agents_detials.configs.model,
              name: this.lastAgentsInfo.name,
              prompt: last_agents_detials.configs.prompt,
              specify_workflow_order:
                last_agents_detials.configs.specify_workflow_order,
              temperature: last_agents_detials.configs.temperature,
              top_p: last_agents_detials.configs.top_p,
              version_id: this.lastAgentsInfo.version_id,
              version_name: this.lastAgentsInfo.version_name,
              workflows: last_agnets_wf,
              intent:configs.intent
            },
          };

          this.SubControllerService.setSubAgentsBody(bodyParams);
        },
      });
    });
  }
  public async getMutilAgentLastVersionFn() {
    await this.SubControllerService.getMutilAgentLastVersion(
      this.agent_id,
    ).then((res: any): void => {
      const get_cur_relations = res.relations.filter(
        (item) => item.resource_id === this.nodeInfo.configs.id,
      );
      if (get_cur_relations.length) {
        this.showUpdatedIcon =
          this.nodeInfo.configs.version_name <
          get_cur_relations[0].resource_latest_version_name
            ? true
            : false;
      }

      this.relations = get_cur_relations;

      if (get_cur_relations.length) {
        this.last_version_id =
          get_cur_relations[0]?.resource_latest_version ?? '';
        this.last_version_name =
          get_cur_relations[0]?.resource_latest_version_name ?? '';
        this.resource_id = get_cur_relations[0]?.resource_id ?? '';
      }
    });
  }
  public async getAgentLastVersionInfo() {
    await this.SubControllerService.getPublishedMutilAgentDetails(
      this.resource_id,
      this.last_version_id,
    ).then((val: any): void => {
      this.lastAgentsInfo = val;
    });
  }

  delNode(e: Event) {
    e.stopPropagation();
    this.appFlowServ.setNodeAction({
      type: 'delete',
      id: this.nodeBase.id,
    });
  }
}
