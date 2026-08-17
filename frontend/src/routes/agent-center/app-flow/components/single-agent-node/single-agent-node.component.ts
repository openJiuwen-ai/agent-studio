import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
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

  private workspaceId = '';

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private i18n: I18NextEagerPipe,
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
}
