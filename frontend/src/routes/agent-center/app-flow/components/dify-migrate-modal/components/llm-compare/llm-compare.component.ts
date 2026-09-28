import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';

import { NzAlertModule } from 'ng-zorro-antd/alert';

import { MODULES } from '@shared/modules';
import { MigrateCompareRowComponent } from '../migrate-compare-row/migrate-compare-row.component';
import { I18nNamespace } from '@i18n';
import type { ILLMNode } from '@routes/agent-center/app-flow/node.type';
import { LLMSelectComponent } from '../../../llm-select/llm-select.component';

@Component({
  selector: 'llm-compare',
  templateUrl: './llm-compare.component.html',
  styleUrls: ['../common-compare.less', './llm-compare.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    NzAlertModule,
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
export class LlmCompareComponent {
  @Input() node: ILLMNode;

  public oldModelName: string;
  public showVisionModelTip = false;
  public selected;
  private modelAutoMatched = false;

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
    this.oldModelName = this.node.configs.model.model_name;
    this.showVisionModelTip = Boolean(this.node.configs.vision);
  }

  public updateModel(model:any){
    this.node.configs.model = {
      model_id: model.id,
      model_deployment_id: model.id,
      model_name: model.modelInfo.model_name,
      model_type: model.modelInfo.model_type
    }
  }

  /**
   * 模型列表加载后，按 Dify 模型名自动匹配同名已部署模型并回填 model_deployment_id，
   * 避免跳过迁移比对时模型部署标识为空；用户手动改选后不再覆盖
   */
  public onModelOptionsLoaded(options: any[]): void {
    if (this.modelAutoMatched || this.node.configs.model?.model_deployment_id || !this.oldModelName) {
      return;
    }
    const matched = this.findModelByName(options);
    if (matched) {
      this.modelAutoMatched = true;
      this.selected = matched.id;
      this.updateModel({ id: matched.id, modelInfo: matched });
    }
  }

  private findModelByName(options: any[]): any | undefined {
    const targetName = String(this.oldModelName).trim().toLowerCase();
    return (options || [])
      .flatMap(group => group?.children || [])
      .find(model => model?.model_name?.trim().toLowerCase() === targetName);
  }
}
