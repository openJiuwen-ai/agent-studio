import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MonacoEditorModule, MonacoEditorConstructionOptions } from '@materia-ui/ngx-monaco-editor';
import { I18nNamespace } from '@i18n';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { type IHttpConfig } from '../../../node.type';
import { AccBlockComponent } from '../../acc-block/acc-block.component';
import { NODE_SAVE_DEBOUNCE_TIME } from '../../../flow.const';

@Component({
  selector: 'meta-config-exception',
  standalone: true,
  imports: [MODULES, MonacoEditorModule, AccBlockComponent],
  templateUrl: './config-exception.component.html',
  styleUrl: './config-exception.component.less',
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: I18nNamespace.AGENT_CENTER,
    },
  ],
})
export class ConfigExceptionComponent {
  @Input() configs!: IHttpConfig;
  @Output() valueChange = new EventEmitter<void>();

  editorOptions: MonacoEditorConstructionOptions = {
    theme: 'vs',
    language: 'json',
    minimap: { enabled: false },
  };

  private codeTimeout: any = null;
  private isInit = 0;

  onValueChange(): void {
    this.valueChange.emit();
  }

  editorOnSave(): void {
    if (this.isInit <= 0) {
      this.isInit += 1;
      return;
    }
    if (this.codeTimeout) {
      clearTimeout(this.codeTimeout);
      this.codeTimeout = null;
    }
    this.codeTimeout = setTimeout(() => {
      this.onValueChange();
    }, NODE_SAVE_DEBOUNCE_TIME);
  }
}
