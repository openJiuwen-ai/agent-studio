import {
  Component,
  ViewChild,
  ViewChildren,
  ChangeDetectorRef,
  Output,
  QueryList,
  EventEmitter,
  OnInit,
  Input,
  Optional,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import {
  type MonacoEditorComponent,
  MonacoEditorLoaderService,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { ArrTypeValidatorDirective } from '@shared/directives/array-type-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { EditorOptions } from '../utils';
import { isArray, isInteger } from 'lodash';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import i18next from 'i18next';
import { NzModalService, NzModalRef } from 'ng-zorro-antd/modal';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-import-json-modal',
  templateUrl: './start-import-json-modal.component.html',
  styleUrls: ['./start-import-json-modal.component.less'],
  standalone: true,
  imports: [
    MODULES,
    MonacoEditorModule,
    ArrTypeValidatorDirective,
    NonEmptyValidatorDirective,
    AssetFormatIconComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzModalService,
    NzMessageService,
  ],
})
export class StartImportJsonModalComponent implements OnInit {
  @ViewChild('paramForm') paramForm: NgForm;

  @ViewChildren('exeEditor') editors: QueryList<any>;

  @Output('confirm') confirm = new EventEmitter();

  @Output('cancel') cancel = new EventEmitter();

  @Input() defaultJson: string;

  @Input() defaultDataList: any[];

  @Input() showDefaultValue = true;

  public changeUrl = cdnAssetUrl;

  public jsonData = this.i18n.transform('startimportjsonmodalcomponent_594');

  public editorOps = EditorOptions;

  public show = false;

  public isImportValue = true;

  public existNotMatchData = false;

  private resSchema: Object;

  constructor(
    protected readonly cdr: ChangeDetectorRef,
    protected readonly i18n: I18NextEagerPipe,
    protected readonly monacoLoader: MonacoEditorLoaderService,
    private nzModal?: NzModalService,
    private nzMessage?: NzMessageService,
    @Optional() private nzModalRef?: NzModalRef,
  ) {}

  ngOnInit() {
    this.isImportValue = this.showDefaultValue;
    this.jsonData = this.defaultJson || this.jsonData;
  }

  /** 点击确认按钮 */
  onJsonOkClick() {
    this.resSchema = this.resStr2Schema(this.jsonData);
    if (!this.defaultDataList) {
      this.show = !this.show;
      return;
    }

    if (this.existNotMatchData) {
      this.show = true;
      return;
    }

    this.onConfirm();
  }

  /** 点击二次确认按钮 */
  onConfirm() {
    if (this.resSchema) {
      this.confirm.emit(this.resSchema);
    } else {
      this.nzMessage?.error(i18next.t('json_parse_error'));
    }
    this.show = false;
  }

  public onInputJSONChange() {
    this.cdr.detectChanges();
  }

  public formatDoc() {
    const editors = this.editors.toArray() as MonacoEditorComponent[];
    const editorCmp = editors[0];

    if (editorCmp) {
      editorCmp.editor.getAction('editor.action.formatDocument').run();
    }
  }

  private resStr2Schema(jsonStr: string) {
    let resObj;

    try {
      resObj = JSON.parse(jsonStr);
      if (!resObj || typeof resObj !== 'object') {
        return '';
      }
    } catch {
      return '';
    }

    return this.defaultDataList
      ? this.resObject2SchemaForDefaultData(resObj)
      : this.resObject2Schema(resObj);
  }

  private resObject2SchemaForDefaultData(data) {
    this.existNotMatchData = false;
    const newDataList = [];
    Object.entries(data || {}).forEach(([key, value]) => {
      const matchKeyData = this.defaultDataList.find(
        (item) => item.name === key,
      );
      if (matchKeyData?.value) {
        if (
          'object' === matchKeyData.type ||
          matchKeyData.type.startsWith('array')
        ) {
          matchKeyData.value.default = value
            ? JSON.stringify(value, null, 2)
            : value;
        } else if (['integer', 'number'].includes(matchKeyData.type)) {
          // 给数字表单项设置null值，不会触发表单值变化，需要转换为undefined
          matchKeyData.value.default = value === null ? undefined : value;
        } else {
          matchKeyData.value.default = value;
        }
        newDataList.push(matchKeyData);
      } else {
        this.existNotMatchData = true;
      }
    });

    return newDataList;
  }

  private resObject2Schema(data) {
    const schema: any = {};

    if (Array.isArray(data)) {
      if (!data.length) {
        return {
          type: 'array',
          items: {type: 'string'},
          ...(this.isImportValue ? { default: JSON.stringify(data) } : {}),
        };
      }

      schema.type = 'array';
      const elmTypes = [...new Set(data.map((item) => this.getType(item)))];

      if (elmTypes.length === 1) {
        schema.items =
          elmTypes[0] === 'object'
            ? this.resObject2Schema(data[0]) // array<object>类型，递归转换JSON Schema
            : {type: elmTypes[0]}; // 单一类型数组
        if (this.isImportValue) {
          schema.default = JSON.stringify(data);
        }
      } else {
        schema.items = {type: 'mixed'}; // 混合类型数组
      }
    } else if (this.getType(data) === 'object') {
      const properties = {};

      Object.entries(data || {}).forEach(([key, value]) => {
        if (value === null) {
          return; // 过滤null，无法知道null属于某个类型
        }

        const propsSchema = this.resObject2Schema(value);
        if (
          propsSchema !== null &&
          propsSchema !== undefined &&
          Object.keys(propsSchema).length > 0
        ) {
          properties[key] = propsSchema;
        }
      });

      if (Object.keys(properties).length === 0) {
        return undefined; // 过滤空对象，无法解析出对象属性，可能导致工作流运行失败
      }
      if (this.isImportValue) {
        schema.default = JSON.stringify(data);
      }

      schema.type = 'object';
      schema.properties = properties;
      schema.required = Object.keys(properties);
    } else {
      // 基础类型
      schema.type = this.getType(data);
      if (this.isImportValue) {
        if (schema.type === 'boolean') {
          schema.default = String(data);
        } else {
          schema.default = data;
        }
      }
    }

    return schema;
  }

  /** 获取入参的具体数据类型 */
  private getType(value): string {
    if (isArray(value)) {
      return 'array';
    }

    if (typeof value === 'number') {
      return isInteger(value) ? 'integer' : 'number';
    }

    if (['boolean', 'string', 'object'].includes(typeof value)) {
      return typeof value;
    }

    return 'unknown';
  }

  dismiss() {
    this.nzModalRef?.close();
    this.cancel.emit();
  }
}
