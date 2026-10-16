import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { getDayOfWeekLabel } from '../../common-logic-agent';
import { AssetDetailsIconComponent } from '@shared/components/assets/asset-details-icon/asset-details-icon.component';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import {ToolListService} from "@routes/agent-center/app-agent/components/tool-list/tool-list.service";
import { NzIconModule } from 'ng-zorro-antd/icon';

@Component({
  selector: 'tool-list',
  templateUrl: './tool-list.component.html',
  styleUrls: ['./tool-list.component.scss'],
  imports: [MODULES, AssetDetailsIconComponent, AssetIntelligentAddComponent, NzIconModule],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ToolListComponent {
  @Input() toolAdded = {
    title: '',
    collapsed: false,
    list: [],
    imageClass: '',
    isLoading: false,
  };

  @Input() agentType: string = 'agent';

  @Input() noDataText = '';

  @Input() isFlowReadonly = false;

  @Output() collapseRegionFlag = new EventEmitter<any>();

  @Output() addBtnClickedFlag = new EventEmitter<any>();

  @Output() deleteTrigger = new EventEmitter<any>();
  allow_add_num = 3;
  allow_add_num_workflow = 3;

  constructor(
    private agentDataServe: AgentDataService,
    private i18n: I18NextEagerPipe,
    private toolListService: ToolListService,
  ) {}

  public changeCollapseEvent(tool: any) {
    this.collapseRegionFlag.emit(tool);
  }

  public addBtnClickedEvent() {
    this.addBtnClickedFlag.emit();
    this.agentDataServe.setTriggerBtnClicked(true);
  }

  public getTriggerType(type: string): string {
    if (type === 'EVENT') {
      return this.i18n.transform('toollistcomponent_66');
    } else if (type === 'POLLING') {
      return this.i18n.transform('toollistcomponent_polling');
    } else {
      return this.i18n.transform('toollistcomponent_67');
    }
  }

  public getTipText(item: any, agentType) {
    if (!item) { return null; }
    const { cron, hook_url, prompt, invocation, poll_url, poll_interval_seconds } = item;
    const showCallMethod = agentType === 'workflow';
    if (item.type === 'TIMER') {
      if (showCallMethod) {
        return {
          cron: this.toolListService.convertFromCronExpression(cron),
          prompt,
          invocation,
        };
      }
      return { cron: this.toolListService.convertFromCronExpression(cron), prompt };
    } else if (item.type === 'POLLING') {
      if (showCallMethod) {
        return { poll_url, poll_interval_seconds, prompt, invocation };
      }
      return { poll_url, poll_interval_seconds, prompt };
    } else {
      return { hook_url, prompt };
    }
  }
  public editOneTrigger(item) {
    this.addBtnClickedFlag.emit(item);
  }

  public deleteOneTrigger(item: any) {
    this.deleteTrigger.emit(item);
  }
}
