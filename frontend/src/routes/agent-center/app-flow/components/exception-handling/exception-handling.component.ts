import {
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { filter, Subject, take } from 'rxjs';
import { cdnAssetUrl } from '../../../../../single-spa/assets-url';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import * as nodeType from '@routes/agent-center/app-flow/node.type';
import {
  MonacoEditorComponent,
  MonacoEditorLoaderService,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { EditorOptions } from '@routes/agent-center/app-flow/components/utils';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { MonacoUri } from '@routes/agent-center/app-flow/components/node-exe/node-exe.component';
import { JSONSchemaFaker } from 'json-schema-faker';

export enum ExceptionHandleType {
  INTERRUPT = 'interrupt',
  DEFAULT_OUTPUTS = 'defaultOutputs',
  ERROR_BRANCH = 'errorbranch',
}

@Component({
  selector: 'exception-handling',
  templateUrl: './exception-handling.component.html',
  styleUrls: ['./exception-handling.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    MonacoEditorModule,
    NonEmptyValidatorDirective,
    ObjTypeValidatorDirective,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ExceptionHandlingComponent implements OnInit, OnDestroy {
  @Input('nodeInfo') nodeInfo: nodeType.INodeBase;

  @ViewChild('editorCmp') editorCmp: MonacoEditorComponent;

  @ViewChild('contentForm') contentForm: NgForm;

  @Output('changeValue') changeValue = new EventEmitter<any>();

  public destroy$ = new Subject<void>();

  public changeUrl = cdnAssetUrl;

  public retryOptions: any[] = [
    { value: 0, label: this.i18n.transform('exceptionhandlingcomponent_324') },
    { value: 1, label: this.i18n.transform('exceptionhandlingcomponent_325') },
    { value: 2, label: this.i18n.transform('exceptionhandlingcomponent_326') },
    { value: 3, label: this.i18n.transform('exceptionhandlingcomponent_327') },
  ];
  public handleOptions: any[] = [
    {
      value: ExceptionHandleType.INTERRUPT,
      label: this.i18n.transform('exceptionhandlingcomponent_328'),
    },
    {
      value: ExceptionHandleType.DEFAULT_OUTPUTS,
      label: this.i18n.transform('exceptionhandlingcomponent_329'),
    },
    {
      value: ExceptionHandleType.ERROR_BRANCH,
      label: this.i18n.transform('exceptionhandlingcomponent_330'),
    },
  ];

  isShowCode = false;

  demoCode = JSON.stringify(
    {
      output: '',
    },
    null,
    2,
  );

  public exception_process = {
    timeout: 900,
    retry_times: 0,
    handle_type: ExceptionHandleType.INTERRUPT,
    default_outputs: this.demoCode,
  };

  public exceptionEnable = false;

  public editorUri: MonacoUri = null;

  stream = false; //llm流式，下拉框固定不重试和中断流程
  response_format = '' //llm输出格式

  maxTimeout = 900;
  minTimeout = 0.1;

  onTimeoutChange() {
    if (this.exception_process.timeout > this.maxTimeout) {
      this.exception_process.timeout = this.maxTimeout;
    }
    if (this.exception_process.timeout < this.minTimeout) {
      this.exception_process.timeout = this.minTimeout;
    }
    this.changeValue.emit();
  }

  onHandleTypeChange(e: string) {
    this.isShowCode = false;
    if (e === ExceptionHandleType.DEFAULT_OUTPUTS) {
      this.isShowCode = true;
      setTimeout(() => {
        this.scrollToCode();
      });
      // 所有节点类型：确保 default_outputs 是有效的字符串值供 Monaco 编辑器使用
      if (
        !this.exception_process.default_outputs ||
        typeof this.exception_process.default_outputs !== 'string'
      ) {
        this.exception_process.default_outputs = this.demoCode;
      }
    }
    this.changeValue.emit();
  }

  handelChangeValue() {
    this.changeValue.emit();
  }

  scrollToCode() {
    const element = document.querySelector('.exception-code');
    element.scrollIntoView({ behavior: 'smooth' });
  }

  formatContent() {
    this.editorCmp?.editor?.getAction('editor.action.formatDocument')?.run();
    this.changeValue.emit();
  }

  getContentError() {
    return (
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      this.contentForm?.controls?.ignoreMsg?.errors?.arrErr?.msg ||
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      this.contentForm?.controls?.ignoreMsg?.errors?.serviceName?.tiErrorMessage
    );
  }

  constructor(
    private fb: FormBuilder,
    private i18n: I18NextEagerPipe,
    private elementRef: ElementRef<HTMLDivElement>,
    private monacoLoader: MonacoEditorLoaderService,
  ) { }

  async ngOnInit() {
    if (this.nodeInfo.type === 'Plugin') {
      try {
        const schema = JSON.parse(
          (this.nodeInfo as any).configs?.output_schema,
        );
        JSONSchemaFaker.option({
          maxItems: 1,
          fillProperties: false,
          alwaysFakeOptionals: true,
        });
        const defaultMsg = await JSONSchemaFaker.resolve(schema);
        this.demoCode = JSON.stringify(defaultMsg, null, 2);
      } catch (e) {
        this.demoCode = '{}';
      }
      this.exception_process.default_outputs = this.demoCode;
    } else if (this.nodeInfo.type === 'Mcp') {
      // MCP 协议输出结构固定：content 数组 + isError
      this.demoCode = JSON.stringify(
        {
          content: [{ type: 'text', text: '' }],
          isError: true,
        },
        null,
        2,
      );
      this.exception_process.default_outputs = this.demoCode;
    }
    this.monacoLoader.isMonacoLoaded$
      .pipe(
        filter((isLoaded) => isLoaded),
        take(1),
      )
      .subscribe(() => {
        this.editorUri = monaco.Uri.parse(
          `agent://flow/plugin/${this.nodeInfo.id}/exception_suppression.json`,
        );
        const configEP = (this.nodeInfo as any)?.configs?.exception_process;
        if (configEP) {
          this.exception_process = configEP;
          if (this.exception_process.default_outputs) {
            if (typeof this.exception_process.default_outputs !== 'string') {
              this.exception_process.default_outputs = JSON.stringify(
                this.exception_process.default_outputs,
                null,
                2,
              );
            }
          } else if (
            this.exception_process.handle_type === ExceptionHandleType.DEFAULT_OUTPUTS
          ) {
            // 保存过但没有 default_outputs 值，补上默认模板
            this.exception_process.default_outputs = this.demoCode;
          }
          if (
            this.exception_process.handle_type ===
            ExceptionHandleType.DEFAULT_OUTPUTS
          ) {
            this.isShowCode = true;
          }
          this.exceptionEnable = true;
        }
      });
  }

  changeStream(e) {
    this.stream = e;
    if (this.stream) {
      setTimeout(() => {
        this.exception_process.handle_type = ExceptionHandleType.INTERRUPT;
        this.isShowCode = false;
        this.exception_process.retry_times = 0;
        delete this.exception_process.timeout;
      });
    } else {
      if (this.exception_process.timeout === undefined) {
        this.exception_process.timeout = 900;
      }
    }
  }

  changeResponseFormat(e) {
    this.response_format = e;
    if (['text', 'markdown'].includes(this.response_format)) {
      setTimeout(() => {
        this.exception_process.handle_type = ExceptionHandleType.INTERRUPT;
        this.isShowCode = false;
      });
    }
  }

  validate() {
    if (!this.exceptionEnable) {
      return true;
    }
    if (
      this.exception_process.handle_type === ExceptionHandleType.DEFAULT_OUTPUTS
    ) {
      return this.contentForm?.valid ?? true;
    }
    return true;
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.changOutput();
  }

  changOutput() {
    if (typeof this.exception_process.default_outputs === 'string') {
      try {
        this.exception_process.default_outputs = JSON.parse(
          this.exception_process.default_outputs,
        );
      } catch (e) {
        this.exception_process.default_outputs = {} as any;
      }
    }
  }

  switchExceptionEnable(enable: boolean) {
    if (enable) {
      (this.nodeInfo as any).configs.exception_process = this.exception_process;
    } else {
      (this.nodeInfo as any).configs.exception_process = undefined;
    }
    this.changeValue.emit();
  }

  protected readonly editorOps = EditorOptions;
}
