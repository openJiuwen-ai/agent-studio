/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable import/no-cycle */
import { ChangeDetectorRef, Component, ElementRef, Input, NgZone, SimpleChanges } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { NODE_ACTIONS } from '@routes/agent-center/constants/workflow-common.const';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { AppFlowService } from '../../app-flow.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type { IPluginNode } from '../../node.type';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import { IPlugin } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { HttpService } from '@services/http.service';
import { ActivatedRoute } from '@angular/router';
import { takeUntil } from 'rxjs';
import { FlowUtils } from '../../utils/flow-utils';
import { EHalfmodalType } from '@routes/agent-center/app-flow/app-flow.types';
import { NzModalService } from 'ng-zorro-antd/modal';
@Component({
  selector: 'meta-plugin-node',
  templateUrl: './plugin-node.component.html',
  styleUrls: ['./plugin-node.component.less', '../common-styles.less'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginNodeComponent extends NodeBaseComponent {
  @Input('nodeInfo') nodeInfo: IPluginNode;

  public apiImgUrl = WORKFLOW_SVGS.Plugin;

  public updateFlowTip = '';
  workspaceId = '';

  override actions = [...NODE_ACTIONS];

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private i18n: I18NextEagerPipe,
    private ngZone: NgZone,
    private nzModal: NzModalService,
    private appFlowRepoServe: AppFlowRepoService,
    private configServ: AgentConfigService,
    private readonly http: HttpService,
    private route: ActivatedRoute
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override ngOnInit(): void {
    this.workspaceId = this.http.getWorkspaceId();
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    if (this.configServ.getConfigs()?.studio_btn_show) {
      this.actions.unshift({
        id: 'detail',
        label: this.i18n.transform('plugin_details'),
      });
    }

    this.appFlowServ.setApiOriginInfo({
      id: this.nodeInfo.configs.id,
      name: this.nodeInfo.name,
    });

    // 响应式订阅：resNodes 数据到达时更新 updateFlowTip，避免 ngOnInit 同步读取时数据未到
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
        }
      });

    // 如果 super.ngOnInit() 中数据已同步到达，也处理一次
    this.updateFlowTip = this.i18n.transform('update_flow_tip', {
      versionName: this.isChildFlowsUpdated?.ref_workflows?.last_version_name,
    });

    this.appFlowServ
      .nodeRefChange$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((data: any) => {
        FlowUtils.handelNodeRefChange(data, this.nodeInfo?.inputs);
      });
  }

  override onClickAction(action: any) {
    let from_id = this.route.snapshot.queryParams.id;
    if (action.id === 'detail') {
      const prefixUrl = window.location.href?.split('/home')[0];

      if (this.nodeInfo.configs?.original_info?.type === 'inner') {
        window.open(
          `${prefixUrl}/home/plugin-market/market-detail?id=${this.nodeInfo.configs.id}&type=server&from=flow&from_id=${from_id}&workspace_id=${this.workspaceId}`,
          '_blank'
        );
      } else {
        window.open(
          `${prefixUrl}/home/agent-center/custom-plugin/detail?id=${this.nodeInfo.configs.id}&from=flow&from_id=${from_id}&workspace_id=${this.workspaceId}`,
          '_blank'
        );
      }
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  public openUpdateFlowModal() {
    this.appFlowServ.setNodeClicked(EHalfmodalType.DEFAULT);
    const { configs, ref_workflows } = this.isChildFlowsUpdated ?? {};
    const { last_version_id, last_version_name, workflow_id } = ref_workflows ?? {};
    this.ngZone.run(() => {
      this.nzModal.warning({
        nzTitle: this.i18n.transform('update_flow_modal_title'),
        nzContent: configs?.version_id
          ? this.i18n.transform('pluginnodecomponent_545', { last_version_name: last_version_name })
          : this.i18n.transform('pluginnodecomponent_546', { last_version_name: last_version_name }),
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOnOk: async () => {
          this.appFlowRepoServe.getPluginVersionInfo(workflow_id, last_version_id).then(res => {
            const oldNodeInfo = this.nodeInfo;
            const pluginVersion = res.data;
            const tool_id = this.nodeInfo.configs.tool_id;
            const input_schema_obj = pluginVersion.input_schema.find(item => tool_id === item.tool_id);
            const output_schema_obj = pluginVersion.output_schema.find(item => tool_id === item.tool_id);
            const tool_info = pluginVersion.request_info.tool_info.find(item => tool_id === item.tool_id);
            const intf_type = pluginVersion.intf_type.find(item => tool_id === item.tool_id);
            const tool_obj = {
              id: pluginVersion.plugin_id,
              ...pluginVersion,
              ...tool_info,
              ...intf_type,
              input_schema: input_schema_obj.input_schema,
              output_schema: output_schema_obj.output_schema,
            };
            const apiVersionData = this.appFlowServ.plugin2ApiNode(tool_obj);
            const bodyParams = {
              ...apiVersionData,
              id: this.nodeBase?.id,
              configs: {
                ...apiVersionData.configs,
                version_id: last_version_id,
                descriptionText: this.nodeInfo.configs?.descriptionText || '',
              },
              name: oldNodeInfo.name,
            };
            bodyParams.outputs.forEach(item => {
              const find = oldNodeInfo.outputs.find(findItem => findItem.name === item.name);
              if (find) {
                item.value = find.value;
              }
            });
            bodyParams.inputs.forEach(item => {
              const find = oldNodeInfo.inputs.find(findItem => findItem.name === item.name);
              if (find) {
                item.value = find.value;
              }
            });
            this.appFlowServ.setChildFlowPutBody(bodyParams);
          });
        },
      });
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
