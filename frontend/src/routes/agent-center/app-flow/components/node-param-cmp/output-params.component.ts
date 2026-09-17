import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { LineClampDirective } from '@shared/directives/line-clamp.directive';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { IWorkflowField, IWorkflowFieldSchema } from '../../node.type';
import { NodeUtils } from '../utils';
import { ValueWarnDirective } from '@shared/directives/value-warn.directive';

@Component({
  selector: 'meta-output-params',
  template: `
    <div class="flex flex-col gap-2" *ngIf="outputs?.length">
      <div *ngFor="let param of outputs" class="flex items-center">
        <div class="flex w-[calc(100%-120px)] items-center gap-[30px]">
          <div class="node-param-shallow w-[54px]" lineClamp valueWarn [valueWarn]="{ textContent: param.name, isParamName: true, noRequired: !param.required, hasInvalidDescendant: hasInvalidDescendant(param) }">
            {{ getFieldName(param) }}
          </div>
          <div class="node-param-tag" lineClamp>
            {{ getTypeView(param) }}
          </div>
        </div>
        <div class="node-param-shallow w-[120px]" lineClamp [valueWarn]="{ textContent: param.description, noRequired: true}">
          {{ getFieldDesc(param) }}
        </div>
      </div>
    </div>

    <div *ngIf="!outputs?.length" class="text-desc">
      {{ 'not_configured' | i18nextEager }}
    </div>
  `,
  styleUrls: ['../common-styles.less'],
  standalone: true,
  imports: [CommonModule, I18NextModule, LineClampDirective, ValueWarnDirective],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class OutputParamsComponent {
  @Input() outputs: IWorkflowField[];

  constructor(private i18n: I18NextEagerPipe) {}

  getFieldName(param: IWorkflowField) {
    return param.name || this.i18n.transform('not_configured');
  }

  getTypeView = NodeUtils.getFieldTypeView;

  getFieldDesc(param: IWorkflowField) {
    return param.description || this.i18n.transform('not_configured');
  }

  /** 字段名合规规则，与 ValueWarnDirective 保持一致 */
  private isNameValid(name?: string): boolean {
    return !!name && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(name);
  }

  /**
   * 判断 param 的任一后代（schema 子字段）字段名是否违规。
   * schema 兼容两种形式：子字段列表（IWorkflowField[]）或元素描述（{schema: 子字段列表}）。
   * 用于父字段向上传递高亮：父字段名自身合法但后代违规时，父字段也高亮。
   */
  hasInvalidDescendant(param: IWorkflowField): boolean {
    const check = (field: IWorkflowField): boolean => {
      const subFields = this.resolveSubFields(field?.schema);
      if (!subFields) {
        return false;
      }
      for (const sub of subFields) {
        if (!this.isNameValid(sub.name)) {
          return true;
        }
        if (this.hasInvalidDescendant(sub)) {
          return true;
        }
      }
      return false;
    };
    return check(param);
  }

  /** 从 schema 解析出子字段列表；非数组返回 null。 */
  private resolveSubFields(schema?: IWorkflowFieldSchema): IWorkflowField[] | null {
    if (!schema) {
      return null;
    }
    if (Array.isArray(schema)) {
      return schema as IWorkflowField[];
    }
    // 元素描述形式：{ name, type, schema: 子字段列表 }
    const elementSchema = (schema as IWorkflowField).schema;
    if (Array.isArray(elementSchema)) {
      return elementSchema as IWorkflowField[];
    }
    return null;
  }
}
