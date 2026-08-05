import {Component, Input} from '@angular/core';
import {CommonModule} from "@angular/common";
import {I18NEXT_NAMESPACE, I18NextEagerPipe} from "angular-i18next";

import {LLMSelectComponent} from "@routes/agent-center/app-flow/components/llm-select/llm-select.component";
import {
    MigrateCompareRowComponent
} from "@routes/agent-center/app-flow/components/dify-migrate-modal/components/migrate-compare-row/migrate-compare-row.component";
import {MODULES} from "@shared/modules";
import {I18nNamespace} from "@i18n";
import type {IAgentRepo, ILLMNode} from "@routes/agent-center/app-flow/node.type";

@Component({
  selector: 'agent-compare',
  templateUrl: './agent-compare.component.html',
  styleUrls: ['../common-compare.less', './agent-compare.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    MigrateCompareRowComponent,
    LLMSelectComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class AgentCompareComponent {
  @Input() node: IAgentRepo;

  public oldModelName: string;
  public selected;

  public modelValidation = {
    errorMessage: {
      required: this.i18n.transform('select_model'),
    },
    type: 'changeAlert',
  };

  constructor(
    private i18n: I18NextEagerPipe,
  ) { }

  ngOnInit(): void {
    this.oldModelName = this.node?.configs?.model?.model_name || '';
  }

  public updateModel(model:any){
    this.node.configs.model = {
      model_id: model.id,
      model_deployment_id: model.id,
      model_name: model.modelInfo.model_name,
      model_type: model.modelInfo.model_type
    }
  }
}
