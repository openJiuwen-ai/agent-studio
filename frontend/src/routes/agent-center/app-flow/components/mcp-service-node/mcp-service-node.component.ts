/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable import/no-cycle */
import {ChangeDetectorRef, Component, ElementRef, Input, SimpleChanges} from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import type { IMcpNode } from '../../node.type';
import { AppFlowService } from '../../app-flow.service';
import { NodeService } from '../../node.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import {resSchemaDataField} from "@routes/agent-center/app-mcp-service/utils";
import {MCPService} from "@services/agent-center/mcp.service";
import { HttpService } from '@services/http.service';
import { takeUntil } from 'rxjs';
import { FlowUtils } from '../../utils/flow-utils';

enum mapKeys {
  task_operators_console = 'task_operators_console',
  job_prompts = 'job_prompts'
}

@Component({
  selector: 'meta-mcp-service-node',
  templateUrl: './mcp-service-node.component.html',
  styleUrls: ['../common-styles.less', './mcp-service-node.component.less'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class MCPServicenNodeComponent extends NodeBaseComponent {
  @Input('nodeInfo') nodeInfo: IMcpNode;

  public codeImgUrl = WORKFLOW_SVGS.Mcp;

  public nodeOperators =[]

  public toolList=[]
  public workspaceId = ''

  constructor(
    private mcpService: MCPService,
    private readonly i18n: I18NextEagerPipe,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private configServ: AgentConfigService,
    private readonly http: HttpService,
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override ngOnInit(): void {
    this.codeImgUrl = this.getUrl();
    this.workspaceId = this.http.getWorkspaceId()
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    if (this.nodeInfo.type === 'Mcp' && this.configServ.getConfigs()?.studio_btn_show) {
      this.actions.unshift({
        id: 'detail',
        label: this.i18n.transform('mcp_service_detail'),
      });
    }
    if(['DataProcess', 'DataSynthesis'].includes(this.nodeInfo.type)){
      this.getServiceDeatil()
    }
    this.appFlowServ.nodeRefChange$().pipe(takeUntil(this.destroy$)).subscribe((data: any) => {
      FlowUtils.handelNodeRefChange(data, this.nodeInfo?.inputs);
    });
  }

  private getUrl() {
    if (this.nodeInfo.type === 'Mcp') {
      return WORKFLOW_SVGS.Mcp;
    } else {
      if (this.nodeInfo.type === 'DataSynthesis') {
        return WORKFLOW_SVGS.DataSynthesis;
      } else {
        return WORKFLOW_SVGS.DataProcess;
      }
    }
  }

  override ngOnChanges(changes: SimpleChanges){
    super.ngOnChanges(changes);
    let currentNode = changes.nodeInfo.currentValue
    this.getToolInfo(currentNode.configs.tool_name)
  }
  getServiceDeatil() {
    this.mcpService
      .getMcpToolInfo(this.nodeInfo.configs.id)
      .then((res: any) => {
        this.toolList = res.tools
        this.getToolInfo( this.nodeInfo.configs.tool_name)
      });

  }

  getToolInfo(name: string){
    const item = this.toolList.find((item) => item.name === name);
    if(!item || !item?.config){
      this.nodeOperators = []
      return
    };
    let nodeOperators = this.nodeInfo.type === 'DataProcess' ? resSchemaDataField(item.config)[mapKeys.task_operators_console] : resSchemaDataField(item.config)[mapKeys.job_prompts];
    this.nodeOperators = nodeOperators.map(item => {
      return {
        ...item,
        name: this.nodeInfo.type === 'DataProcess' ? item.operator_name : item.prompt_name,
        description: this.nodeInfo.type === 'DataProcess' ? item.operator_desc : '',
      }
    });
  }

  override onClickAction(action: any) {
    if (action.id === 'detail') {
      const url = window.location.href?.split('/home');
      const prefixUrl = url[0];
      window.open(
        `${prefixUrl}/home/agent-center/mcp-service/detail?id=${this.nodeInfo.configs.id}&type=service&workspace_id=${this.workspaceId}`,
        '_blank',
      );
    } else {
      this.appFlowServ.setNodeAction({
        type: action.id,
        id: this.nodeBase.id,
      });
    }
  }

  delNode(e: Event) {
    e.stopPropagation();
    this.appFlowServ.setNodeAction({
      type: 'delete',
      id: this.nodeBase.id,
    });
  }

  override actions: { id: string; label: string }[] = [
    {
      id: 'update',
      label: this.i18n.transform('rename'),
    },
    {
      id: 'copy',
      label: this.i18n.transform('copy'),
    },
    {
      id: 'delete',
      label: this.i18n.transform('delete'),
    },
  ];
}
