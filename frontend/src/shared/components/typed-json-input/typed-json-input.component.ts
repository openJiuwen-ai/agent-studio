import { Component, Input, EventEmitter, Output } from '@angular/core';
import { NodeDependencies } from '@routes/agent-center/app-flow/components/modules';
import { MODULES } from '@shared/modules';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import type {
  IWFViewParentType,
  IWFViewWithMultiType,
  IWorkflowField,
} from '@routes/agent-center/app-flow/node.type';
import { AssetJsonInputIconComponent } from '../assets/asset-json-input-icon/asset-json-input-icon.component';
import { SetDefaultComponent } from '@routes/agent-center/app-flow/components/set-default/set-default.component';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';

@Component({
  selector: 'typed-json-input',
  templateUrl: './typed-json-input.component.html',
  styleUrls: ['./typed-json-input.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    NodeDependencies,
    AssetJsonInputIconComponent,
    SetDefaultComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class TypedJsonInputComponent {
  @Input() param: IWorkflowField;

  @Input() isValidated: boolean = false;

  @Input() disabled: boolean = false;

  @Output('changeValue') changeValue = new EventEmitter<any>();

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }

  public formatText(param) {
    return param
      .replace(/\r?\n/g, '')
      .replace(/\\/g, '')
      .replace(/^"(.*)"$/, '$1');
  }

  public field2View(field: IWorkflowField | any): IWFViewWithMultiType {
    const { name, type, description, required, schema, source, value } = field;
    const view: IWFViewWithMultiType = {
      name,
      type: type.split('/'),
      description,
      required,
      source,
      value,
    };

    if (type === 'array') {
      if (!schema) {
        view.type = ['array<any>'];
        return view;
      }
      if ((schema as IWorkflowField).type === 'object') {
        view.type = ['array<object>'];
        view.children = FlowUtils.fields2Views(
          ((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[],
          0,
          view.type[0] as IWFViewParentType,
        );
        view.expanded = true;
      } else {
        view.type = [`array<${(schema as IWorkflowField).type}>`];
      }
    }

    if (type === 'object') {
      view.children = FlowUtils.fields2Views(
        (schema ?? []) as IWorkflowField[],
        0,
        view.type[0] as IWFViewParentType,
      );
      view.expanded = true;
    }

    return view;
  }

  public changeParam() {
    this.changeValue.emit();
  }
}
