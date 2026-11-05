import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output, NgZone, } from '@angular/core';
import { I18NextEagerPipe, I18NEXT_NAMESPACE } from 'angular-i18next';
import { NzModalService } from 'ng-zorro-antd/modal';
import { FormsModule } from '@angular/forms';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzTagModule } from 'ng-zorro-antd/tag';
import { NzSelectModule } from 'ng-zorro-antd/select';

import { WORKFLOW_DEFAULT_ICON_BASE64_STR } from '../../create-workflow/default-icon-base64';
import { WORKFLOW_SVGS } from '@routes/agent-center/app-flow/flow.const';
import { I18nNamespace } from '@i18n';
import { ApplicationType } from "@enums/agent-center.enum";
import { MODULES } from '@shared/modules';
import {SubAgentModel, SubWorkFlow} from "@routes/agent-center/app-flow/components/controller-modal/controller-modal.interface";

@Component({
  selector: 'controller-flow-item',
  standalone: true,
  imports: [MODULES, FormsModule, NzIconModule, NzToolTipModule, NzTagModule, NzSelectModule],
  templateUrl: './flow-item.component.html',
  styleUrl: './flow-item.component.less',
  changeDetection: ChangeDetectionStrategy.OnPush,
    providers: [
      {
        provide: I18NEXT_NAMESPACE,
        useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
      },
    ],
})
export class FlowItemComponent {
  @Input() isFlowReadonly: boolean;
  @Input() itemFlow: SubAgentModel | SubWorkFlow;
  @Input() type: string = ApplicationType.WORKFLOW;
  @Input() showAction = false;
  @Input() showTags = false;
  @Input() update: any;
  @Output() deleteItemEvent = new EventEmitter<any>();
  @Output() updateCardEvent = new EventEmitter<any>();
  @Output() changeActionEvent = new EventEmitter<any>();

  public intentActionOps = [
    { label: this.i18n.transform('continue'), value: 'Continue' },
    { label: this.i18n.transform('termination'), value: 'Terminal' },
    { label: this.i18n.transform('waiting_for_input'), value: 'WaitUserInput' },
  ];

  get isWorkflow() {
    return this.type === ApplicationType.WORKFLOW;
  }

  src = '';
  tip = '';
  updateFlowTip = '';
  public tags = [];

  private defaultIconMap = {
    [ApplicationType.WORKFLOW]: WORKFLOW_SVGS.WorkflowMulti,
    [ApplicationType.MULTI_AGENT]: WORKFLOW_SVGS.Controller,
    [ApplicationType.SINGLE_AGENT]: WORKFLOW_SVGS.SingleAgent,
  }

  constructor(
    private nzModal: NzModalService,
    private i18n: I18NextEagerPipe,
    private ngZone: NgZone,
  ) {

  }

  ngOnInit() {
    if (this.itemFlow?.valid === false) {
      let tip = '';
      if (this.isWorkflow) {
        tip = this.itemFlow.validVersion
          ? this.i18n.transform('flowitemcomponent_23', {
            validVersion: this.itemFlow.validVersion,
          })
          : this.i18n.transform('flowitemcomponent_21');
      } else {
        tip = this.itemFlow.validVersion
          ? this.i18n.transform('flowitemcomponent_24', {
            validVersion: this.itemFlow.validVersion,
          })
          : this.i18n.transform('flowitemcomponent_22');
      }
      this.tip = tip;
    }
  }

  ngOnChanges(){
    this.updateFlowTip = this.i18n.transform('update_flow_tip', {
      versionName: this.update?.name,
    });
    if (!this.itemFlow.avatar) {
      this.src = this.defaultIconMap[this.type] || this.defaultIconMap[ApplicationType.WORKFLOW];
    } else {
      this.src = this.itemFlow.avatar?.startsWith('data:image/') ? this.itemFlow.avatar : `data:image/png;base64,${this.itemFlow.avatar}`;
    }
    this.getTagText();
  }

  deleteOneFlow() {
    this.deleteItemEvent.emit();
  }

  public openUpdateFlowModal() {
    const ct = this.isWorkflow ? this.i18n.transform('flowitemcomponent_26',{name:this.update?.name}) : this.i18n.transform('flowitemcomponent_25',{name:this.update?.name});
    this.ngZone.run(() => {
      this.nzModal.confirm({
        nzTitle: this.i18n.transform('update_flow_modal_title'),
        nzContent: ct,
        nzOkText: this.i18n.transform('update_flow_modal_btn'),
        nzOkType: 'primary',
        nzOnOk: () => {
          this.updateCardEvent.emit();
        },
      });
    });
  }

  changeAction() {
    this.changeActionEvent.emit();
  }

  private getTagText(): void {
    if(!this.showTags) {
      return;
    }
    if(this.itemFlow.subAgentType === ApplicationType.SINGLE_AGENT) {
      // 单智能体成员按实际 mode 展示：'PlanExecute' 为规划模式，'agent' 为通用模式
      // （历史存量数据均为 'PlanExecute'）
      const isPlanningMode = (this.itemFlow as SubAgentModel).mode === 'PlanExecute';
      this.tags = [
        this.i18n.transform('single_agent'),
        this.i18n.transform(isPlanningMode ? 'agent_planning_mode' : 'agent_mode_gen')
      ];
      return;
    }

    if(this.itemFlow.subAgentType === ApplicationType.MULTI_AGENT) {
      this.tags = [this.i18n.transform('multiple_agent')];
      return;
    }

    const i18nKey = (this.itemFlow as SubWorkFlow).flowType === 'chat'
      ? 'workflow_chat' : 'workflow_task';
    this.tags = [this.i18n.transform(i18nKey)];
  }
}
