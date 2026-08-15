import { Clipboard } from '@angular/cdk/clipboard';
import { TextFieldModule } from '@angular/cdk/text-field';
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  QueryList,
  SimpleChanges,
  ViewChild,
  ViewChildren,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { Graph } from '@antv/x6';
import { NzMessageService } from 'ng-zorro-antd/message';
import {
  type MonacoEditorComponent,
  MonacoEditorLoaderService,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { Network } from '@model';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AssetClearIconComponent } from '@shared/components/assets/asset-clear-icon/asset-clear-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetDisabledClearIconComponent } from '@shared/components/assets/asset-disabled-chat-icon/asset-disabled-chat-icon.component';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { AssetUserIconComponent } from '@shared/components/assets/asset-user-icon/asset-user-icon.component';
import { FlexibleTextFieldComponent } from '@shared/components/flexible-text-field/flexible-text-field.component';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { ArrTypeValidatorDirective } from '@shared/directives/array-type-validator.directive';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzAlertModule } from 'ng-zorro-antd/alert';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzInputModule } from 'ng-zorro-antd/input';
import { type SSE } from '@shared/services/sse';
import { cloneDeep } from 'lodash';
import { filter, take } from 'rxjs';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { v4 as uuidV4 } from 'uuid';
import { AppFlowService } from '../../app-flow.service';
import FlowCommonLogic from '../../common-logic-workflow';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type {
  IPluginNode,
  IsolatedTestableNode,
  IWorkflowField,
  IWorkflowFieldType,
} from '../../node.type';
import { EditorOptions, NodeUtils } from '../utils';
import { isEmpty, isNil } from 'lodash';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import {
  createFileItem,
  uploadFile,
  validateFileSize,
} from '@routes/agent-center/multiUpload.utils';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import {
  UploadFileAccPipe,
  UploadFileDescPipe,
} from 'src/pipes/upload-file.pipe';
import { CommonUtils } from 'src/utils/common.util';
import { checkFileTypeAndSize } from '@routes/agent-center/utils';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';

type PlainType = string | number | boolean | Record<string, any>;

type ExeFieldVal = PlainType | Array<PlainType>;

type RunStatus = 'failed' | 'succeeded' | 'loading';

interface ISSEData {
  data: string;
  [key: string]: any;
}

interface IExeData {
  event:
    | 'node_finished'
    | 'node_started'
    | 'message'
    | 'end'
    | 'error'
    | 'node_wait';
  data: {
    node_id: string;
    status: {
      code: number;
      desc: RunStatus;
    };
    inputs: Record<string, any>;
    outputs: Record<string, any>;
    start_time: number;
    end_time: number;
    message?: string;
    messages?: {
      role: 'user' | 'assistant';
      content: string;
    }[];
    error_message?: string;
    text?: string;
    is_finished?: boolean;
  };
}

export type MonacoUri = monaco.Uri;

interface FileItem {
  fileId: string;
  name: string;
  progress: RunStatus;
  type: string;
  url?: string;
  isHover?: boolean;
  controller: AbortController;
}

export interface IExeField extends IWorkflowField {
  val: ExeFieldVal;
  uri?: MonacoUri;
  file?: File;
  uploadData?: {
    progress?: 'loading' | 'succeeded' | 'failed';
    name?: string;
  };
  uploadDatas?: Array<FileItem>;
}

interface IRunInfo {
  status: RunStatus;
  startTime: number;
  endTime: number;
  duration: string;
  tokens?: number;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  answer?: string;
}

const INIT_VAL_MAP = {
  number: 0,
  integer: 0,
  array: '[]',
  object: '{}',
  string: '',
};

@Component({
  selector: 'flow-node-exe',
  templateUrl: './node-exe.component.html',
  styleUrls: ['./node-exe.component.less', '.././modal-common.less'],
  standalone: true,
  imports: [
    MODULES,
    MonacoEditorModule,
    FlexibleTextFieldComponent,
    NonEmptyValidatorDirective,
    AssetFormatIconComponent,
    ArrTypeValidatorDirective,
    ObjTypeValidatorDirective,
    NoDataIconComponent,
    JsonViewerComponent,
    AssetCopyIconComponent,
    AssetCopySuccessIconComponent,
    AssetDisabledClearIconComponent,
    AssetClearIconComponent,
    AssetUserIconComponent,
    TextFieldModule,
    AppMarkdownAnswerComponent,
    UploadFileIconComponent,
    UploadFileAccPipe,
    UploadFileDescPipe,
    NzIconModule,
    NzAlertModule,
    NzTabsModule,
    NzSwitchModule,
    NzButtonModule,
    NzSpinModule,
    NzInputModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
  ],
})
export class NodeExeComponent implements OnChanges {
  @Input() nodeInfo: IsolatedTestableNode;

  @Input() workflowIcon: string;

  @Input() graph!: Graph;

  @Input() conversationId = '';

  @Input() workflowId = '';

  @Input() enableLongMemory = false;

  @Output('close') close = new EventEmitter<void>();

  @ViewChild('paramForm') paramForm: NgForm;

  @ViewChild('pluginForm') pluginForm: NgForm;

  @ViewChild('chatTextarea') chatTextarea!: ElementRef<HTMLTextAreaElement>;

  @ViewChild('chatContainerRef') chatContainerRef!: ElementRef<HTMLDivElement>;

  @ViewChild('resultScrollRef') resultScrollRef?: ElementRef<HTMLDivElement>;

  @ViewChildren('exeEditor') editors: QueryList<any>;

  @ViewChildren('fileInput') fileInputs: QueryList<any>;

  public isPluginConfigVisible = false;

  public showInputsCopySuccess = false;

  public showOutputsCopySuccess = false;

  public tabs = [
    {
      id: 'conf',
      title: this.i18n.transform('config_info'),
      active: true,
    },
    {
      id: 'run',
      title: this.i18n.transform('running_results'),
      active: false,
    },
  ];

  public selectedTabIndex = 0;

  get icon() {
    if (this.nodeInfo?.type) {
      return WORKFLOW_SVGS[this.nodeInfo.type];
    }

    return '';
  }

  get canSend() {
    return !this.isLoading && this.query.trim();
  }

  public validateAlertIcon = WORKFLOW_SVGS.ValidateAlert;

  public params: IExeField[] = [];

  public getTypeFunc = NodeUtils.getFieldTypeView;

  public isFile = NodeUtils.isFileType;

  public isStr = NodeUtils.isStringType;

  public isMultiples = NodeUtils.isMultiplesType;

  public isNum = NodeUtils.isNumType;

  public isInt = NodeUtils.isIntType;

  public isBool = NodeUtils.isBooleanType;

  public isArr = NodeUtils.isArrayType;

  public isObj = NodeUtils.isObjectType;

  public isComplex = NodeUtils.isComplexType;

  public editorOps = EditorOptions;

  public isLoading = false;

  public runInfo: Partial<IRunInfo> | null = null;

  public authParams: {
    name: string;
    value: string;
  }[] = [];

  public errorMsg: any;

  public isShowChat = false;

  public showPreRunCheckInfo = false;

  public runBtnDisabled = false;

  get clearChatDisabled() {
    return !this.chats.length;
  }

  public isShowBorderAnime = false;

  public query = '';

  public loadingGif = `${Network.ASSETS_PATH}app-library/chating.gif`;

  public chats: {
    query: string;
    answer: {
      text: string;
      loading: boolean;
      isError: boolean;
    };
  }[] = [];

  get lastChat() {
    const len = this.chats.length;
    if (len) {
      return this.chats[len - 1];
    }

    return null;
  }

  public isUploading = false;
  public inputIndex: number;

  private sseInstance: SSE | null = null;

  public cdn = cdnAssetUrl;

  public lang = CommonUtils.getLanguage();

  showCodeCopySuccess = false;

  constructor(
    private cdr: ChangeDetectorRef,
    private monacoLoader: MonacoEditorLoaderService,
    private nodeServ: NodeService,
    private repoServ: AppAgentRepoService,
    private appFlowServe: AppFlowService,
    private clipboard: Clipboard,
    private appPluginRepoServ: AppPluginRepoService,
    private i18n: I18NextEagerPipe,
    private nzMessage: NzMessageService,
    private configServ: AgentConfigService,
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes?.nodeInfo?.currentValue) {
      this.initState();
      const info = this.appFlowServe.getNodeTestInfo(this?.nodeInfo?.id);
      if (info) {
        this.selectedTabIndex = 1;
        this.tabs[1].active = true;
        this.tabs[0].active = false;
        this.runInfo = info;
        if (info.errorMsg) {
          this.errorMsg = info.errorMsg;
        }
      } else {
        // 清掉所有
        this.appFlowServe.setSaveNodeTestInfo(null);
      }
      this.monacoLoader.isMonacoLoaded$
        .pipe(
          filter((isLoaded) => isLoaded),
          take(1),
        )
        .subscribe(() => {
          this.initParams();
          this.cdr.detectChanges();
        });
    }

    if (this?.nodeInfo?.type === 'LTM' && changes?.enableLongMemory) {
      this.showPreRunCheckInfo = !changes?.enableLongMemory.currentValue;
      this.runBtnDisabled = this.showPreRunCheckInfo;
    }
  }

  ngAfterViewInit() {
    this.chatTextarea.nativeElement.addEventListener(
      'keydown',
      this.onKeydown.bind(this),
    );
  }

  ngOnDestroy() {
    this.cleanupChatTxtListener();
  }

  private cleanupChatTxtListener() {
    if (this.chatTextarea) {
      this.chatTextarea.nativeElement.removeEventListener(
        'keydown',
        this.onKeydown.bind(this),
      );
    }
  }

  get statusText(): string {
    if (this.runInfo.status === 'loading') {
      return this.i18n.transform('running');
    } else if (this.runInfo.status === 'succeeded') {
      return this.i18n.transform('success');
    } else {
      return this.i18n.transform('fail');
    }
  }

  onClose() {
    const ctx: Record<string, IExeField> = {};
    this.params.forEach((param) => {
      ctx[param.name] = param;
    });
    this.nodeServ.setIsolatedTestNodeCtx(this.nodeInfo.id, ctx);

    this.close.emit();
    this.params.forEach((param) => {
      if (['object', 'array'].includes(param.type)) {
        monaco.editor.getModel(param.uri)?.dispose();
      }
    });

    this.initState();
  }

  public stopChat() {
    this.cleanChats();
    this.isLoading = false;
    this.cdr.markForCheck();
  }

  public initState() {
    this.authParams = [];
    this.errorMsg = '';
    this.isShowChat = false;
    this.runInfo = null;
    this.chats = [];
    this.isPluginConfigVisible = false;
    this.selectedTabIndex = 0;
    this.tabs.forEach((tab) => {
      if (tab.id === 'run') {
        tab.active = false;
      } else {
        tab.active = true;
      }
    });
  }

  onBooleanChange() {
    this.cdr.detectChanges();
  }

  run(type: 'config' | 'chat') {
    if (type === 'chat' && !this.canSend) {
      return;
    }
    if (this.isUploading) {
      this.nzMessage.warning(
        this.i18n.transform('waiting_upload_complete'),
      );
      return;
    }
    if (this.params.length) {
      this.paramForm.form.markAllAsTouched();
      if (this.paramForm.form.invalid) {
        return;
      }
    }

    if (
      this.isShowPluginConfig &&
      this.pluginForm
    ) {
      this.pluginForm.form.markAllAsTouched();
      if (this.pluginForm.form.invalid) {
        return;
      }
    }

    if (
      type === 'config' &&
      (this.nodeInfo.type === 'Questioner' || this.nodeInfo.type === 'Agent')
    ) {
      this.isShowChat = true;
      if (this.nodeInfo.type === 'Agent') {
        return;
      }
    }

    this.errorMsg = '';
    this.isLoading = true;

    this.selectedTabIndex = 1;
    this.tabs.forEach((tab) => {
      if (tab.id === 'run') {
        tab.active = true;
      } else {
        tab.active = false;
      }
    });

    if (this.nodeInfo.type === 'Questioner' || this.nodeInfo.type === 'Agent') {
      this.chats.push({
        query: this.query,
        answer: {
          text: '',
          isError: false,
          loading: true,
        },
      });

      this.scrollToBottom();
    }

    if (this.runInfo && !isEmpty(this.runInfo)) {
      this.runInfo = null;
    }
    this.sseInstance = this.repoServ.exeNode({
      workflowId: this.workflowId,
      conversationId: this.conversationId,
      nodeId: this.nodeInfo.id,
      data: {
        inputs: this.getInputParams(),
        globals: {},
        plugin_configs: this.getPluginParam(),
      },
      invokeMode: 'DEBUG',
      lang: this.lang,
      onmessage: (event: ISSEData) => {
        if (event?.data) {
          try {
            const exeResult = JSON.parse(event.data) as IExeData;
            const exeResultAddFrom = {...exeResult, fromType:'nodeExe'};
            this.appFlowServe.setTokenData(exeResultAddFrom);

            const {
              start_time,
              end_time,
              inputs,
              outputs,
              status,
              messages,
              text,
            } = exeResult.data;

            if (exeResult.event === 'node_started') {
              this.isLoading = false;
              if (isEmpty(this.runInfo)) {
                this.runInfo = { status: 'loading', startTime: start_time };
              } else {
                this.runInfo = {
                  ...this.runInfo,
                  status: 'loading',
                  startTime: start_time,
                };
              }
            }

            if (exeResult.event === 'node_finished') {
              this.isLoading = false;
              this.runInfo = {
                ...this.runInfo,
                status: status.desc,
                startTime: start_time,
                endTime: end_time,
                duration: FlowCommonLogic.calcElapsedTime(start_time, end_time),
                inputs:
                  this.nodeInfo.type === 'Questioner' ||
                  this.nodeInfo.type === 'Agent'
                    ? messages
                    : inputs,
                outputs,
              };

              if (
                this.nodeInfo.type === 'Questioner' ||
                this.nodeInfo.type === 'Agent'
              ) {
                this.isShowChat = false;
              }
            }

            if (
              exeResult.event === 'node_wait' &&
              this.lastChat &&
              messages?.length &&
              messages[messages.length - 1].role === 'assistant'
            ) {
              this.isLoading = false;
              const lastIdx = messages.length - 1;
              this.lastChat.answer.text = messages[lastIdx].content;
              this.lastChat.answer.loading = false;
              this.scrollToBottom();
            }

            if (exeResult.event === 'error') {
              this.isLoading = false;
              this.errorMsg = exeResult.data;
              if (isEmpty(this.runInfo)) {
                this.runInfo = {
                  status: 'failed',
                };
              } else {
                this.runInfo = {
                  ...this.runInfo,
                  status: 'failed',
                };
              }

              if (
                this.nodeInfo.type === 'Questioner' ||
                this.nodeInfo.type === 'Agent'
              ) {
                this.lastChat.answer.text = exeResult.data.message;
                this.lastChat.answer.loading = false;

                this.isShowChat = false;
              }
            }

            if (exeResult.event === 'message') {
              this.isLoading = false;
              if (isEmpty(this.runInfo)) {
                this.runInfo = { answer: '' };
              }
              this.runInfo.answer = (this.runInfo.answer || '') + text;
              this.scrollAnswerToBottom();

              if (exeResult.data.is_finished) {
                this.lastChat.answer.loading = false;
              }
            }
          } catch {
            // do nth
          }
        }
      },
      ondone: () => {
        this.isLoading = false;
        this.appFlowServe.setSaveNodeTestInfo({
          id: this.nodeInfo.id,
          runInfo: cloneDeep({
            ...this.runInfo,
            errorMsg: this.errorMsg,
          }),
        });
      },
      onerror: () => {
        this.isLoading = false;
      },
      ontimeout: () => {
        this.isLoading = false;
        this.nzMessage.error(
          this.i18n.transform('streaming_call_timeout'),
        );
      },
    });
  }

  public initParams() {
    const cachedParams =
      this.nodeServ.getIsolatedTestNodeCtx(this.nodeInfo.id) ?? {};
    const schemas = [];
    const complexCtx: { val: string; uri: MonacoUri }[] = [];

    this.params = this.nodeInfo?.inputs.map((input) => {
      const param: IExeField = {
        ...cloneDeep(input),
        val: this.getInitValFromCache(cachedParams[input.name], input),
      };

      if (['array', 'object'].includes(input.type)) {
        const schemaType = (input.schema as IWorkflowField)?.type;
        if (schemaType && schemaType.includes('file')) {
          param.type = `array<${schemaType}>` as IWorkflowFieldType;
        } else {
          param.uri = this.generateUri(input);

          schemas.push({
            uri: param.uri.toString(),
            schema: this.generateSchema(input),
            fileMatch: [param.uri.toString()],
          });

          complexCtx.push({
            val: param.val as string,
            uri: param.uri,
          });
        }
      }

      return param;
    });

    if (schemas.length) {
      setTimeout(() => {
        monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
          validate: true,
          schemas,
        });

        const editors = this.editors.toArray() as MonacoEditorComponent[];

        complexCtx.forEach((ctx, index) => {
          try {
            const model = monaco.editor.createModel(ctx.val, 'json', ctx.uri);
            editors[index].editor.setModel(model);
          } catch {
            // do nth
          }
        });
      });
    }

    if (this.nodeInfo.type === 'Plugin') {
      this.initAuthParams();

      setTimeout(() => {
        this.params.forEach((param, index) => {
          if (!param.required) {
            this.paramForm.form.controls[`param${index}`].clearValidators();
          }
        });
      });
    }
  }

  public goToConfig() {
    this.appFlowServe.setIsOpenGlbConf();
  }

  public handleCopy(
    content: string | Record<string, any>,
    type: 'inputs' | 'outputs',
  ) {
    if (typeof content === 'string') {
      this.clipboard.copy(content);
    } else {
      this.clipboard.copy(JSON.stringify(content));
    }

    if (type === 'inputs') {
      this.showInputsCopySuccess = true;
    } else {
      this.showOutputsCopySuccess = true;
    }

    window.setTimeout(() => {
      if (type === 'inputs') {
        this.showInputsCopySuccess = false;
      } else {
        this.showOutputsCopySuccess = false;
      }
    }, 2000);
  }

  handleCopyErrorCode(code) {
    if (typeof code === 'string') {
      this.clipboard.copy(code);
    } else {
      this.clipboard.copy(JSON.stringify(code));
    }
    this.showCodeCopySuccess = true;
    setTimeout(() => {
      this.showCodeCopySuccess = false;
    }, 2000);
  }

  public onInput() {
    this.isShowBorderAnime = true;

    setTimeout(() => {
      this.isShowBorderAnime = false;
    }, 4000);
  }

  public cleanChats() {
    this.sseInstance?.close();
    this.chats = [];
    this.conversationId = uuidV4();
    this.isLoading = false;
    this.appFlowServe.setTokenData({});
  }

  public async onUploadFile(
    e: Event,
    inputItem: IExeField,
    uploadType = 'multi',
  ): Promise<void> {
    const input = e.target as HTMLInputElement;
    if (uploadType === 'single') {
      const file: File = input.files[0];
      if (!file) {
        return;
      }

      const fileExtension = file.name.split('.').pop().toLowerCase();
      const valid = checkFileTypeAndSize(
        fileExtension,
        file.size,
        this.i18n,
        this.configServ.getFileMaxSizeKb(),
      );

      if (!valid) {
        return;
      }

      const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(fileExtension);

      inputItem.uploadData = {
        name: file.name,
        progress: 'loading',
      };
      inputItem.file = file;
      input.value = '';

      const formData = new FormData();
      formData.append('file', file);
      formData.append('is_image', JSON.stringify(isImage));
      this.repoServ
        .uploadFile(formData)
        .then((res: { url: string }) => {
          inputItem.uploadData.progress = 'succeeded';
          inputItem.val = res.url;
          this.cdr.detectChanges();
        })
        .catch(() => {
          inputItem.uploadData = null;
          inputItem.file = undefined;
          this.cdr.detectChanges();
        });
    } else {
      const len = input?.files?.length;
      if (!len) {
        return;
      }
      this.inputIndex = this.params.findIndex(
        (item) => item.name === inputItem.name,
      );
      if (!inputItem.uploadDatas) {
        inputItem.uploadDatas = [];
      }
      if (len + inputItem.uploadDatas.length > 10) {
        this.nzMessage.warning(
          this.i18n.transform('upload_max_ten_files_tip'),
        );
        return;
      }
      for (const file of input.files) {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(
          extension,
        );
        const validationError = validateFileSize(file, isImage, 5 * 1024, this.configServ.getFileMaxSizeKb());
        if (validationError) {
          this.nzMessage.warning(this.i18n.transform(validationError.key, validationError.params));
          continue;
        }
        const fileItem = createFileItem(file);
        inputItem.uploadDatas.push(fileItem);
        this.cdr.detectChanges();
        this.isUploading = true;
        await new Promise(resolve => setTimeout(resolve));
        uploadFile(this.repoServ, file, isImage, fileItem, () => {
          inputItem.uploadDatas = inputItem.uploadDatas.filter((f) => f.fileId !== fileItem.fileId);
          this.cdr.detectChanges();
        }).finally(() => {
          this.cdr.detectChanges();
          this.isUploading = false;
        });
      }
      input.value = '';
    }
  }

  private getInitValFromCache(
    cachedParam: IExeField | null,
    param: IWorkflowField,
  ) {
    if (cachedParam && this.isSameType(cachedParam, param)) {
      return cachedParam.val;
    }

    return INIT_VAL_MAP[param?.type] ?? '';
  }

  private isSameType(param1: IExeField, param2: IWorkflowField) {
    if (param1?.type === param2?.type) {
      if (param1?.type === 'array') {
        return (
          (param1.schema as IWorkflowField).type ===
          (param2.schema as IWorkflowField).type
        );
      }

      return true;
    }

    return false;
  }

  public formatDoc(uri: MonacoUri) {
    const editors = this.editors.toArray() as MonacoEditorComponent[];
    const editorCmp = editors.find((e) => e.uri === uri);

    if (editorCmp) {
      editorCmp.editor.getAction('editor.action.formatDocument').run();
    }
  }

  public getComplexErr(i: number): string | null {
    return (
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      this.paramForm?.controls[`param${i}`]?.errors?.arrErr?.msg ||
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      this.paramForm?.controls[`param${i}`]?.errors?.serviceName?.tiErrorMessage
    );
  }

  public onInputJSONChange() {
    this.cdr.detectChanges();
  }

  public isXParams(name: string): boolean {
    const regex = /^x-auth-token$/i;
    return regex.test(name.toLowerCase());
  }

  public isAnswerValid(runInfo): boolean {
    return !isNil(runInfo.answer) && runInfo.answer !== '';
  }

  public isShowMultiBtn(param) {
    return (
      param.type?.includes('array<file') &&
      param?.uploadDatas?.length &&
      param?.uploadDatas?.length < 10
    );
  }

  public addMultiFile(index): void {
    if (this.isUploading) {
      return;
    }
    let element = this.fileInputs.find((el) =>
      el.nativeElement.className.includes(`input${index}`),
    );
    if (element) {
      element.nativeElement.click();
    }
  }

  public onFileItemHover(fileItem, val) {
    fileItem.isHover = val;
    this.cdr.detectChanges();
  }

  private generateUri(param: IWorkflowField) {
    return monaco.Uri.parse(
      `agent://flow/isolated/${this.nodeInfo.id}/${param.name}.json`,
    );
  }

  private scrollToBottom() {
    setTimeout(() => {
      this.chatContainerRef.nativeElement.scrollTop =
        this.chatContainerRef.nativeElement.scrollHeight;
    }, 0);
  }

  private scrollAnswerToBottom() {
    setTimeout(() => {
      if (this.resultScrollRef?.nativeElement) {
        this.resultScrollRef.nativeElement.scrollTop =
          this.resultScrollRef.nativeElement.scrollHeight;
      }
    }, 0);
  }

  private generateSchema(param: IWorkflowField) {
    if (param.type === 'array') {
      return {
        $schema: 'http://json-schema.org/draft-07/schema#',
        type: 'array',
        items: {
          type: (param.schema as IWorkflowField).type,
        },
      };
    }

    return {
      $schema: 'http://json-schema.org/draft-07/schema#',
      type: 'object',
      additionalProperties: true,
      properties: {},
      not: {
        anyOf: [
          { type: 'array' },
          { type: 'string' },
          { type: 'number' },
          { type: 'boolean' },
          { type: 'null' },
        ],
      },
    };
  }

  private onKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      if (event.ctrlKey) {
        this.query += '\n';
      } else {
        this.run('chat');
      }
      event.preventDefault();
    }
  }

  private getInputParams() {
    const inputsObj: Record<string, any> = {};
    this.params.forEach((param) => {
      if (param.type?.includes('array<file')) {
        inputsObj[param.name] = (param.uploadDatas || []).map(
          (fileItem) => fileItem.url,
        );
      } else {
        inputsObj[param.name] = param.val;
      }
    });

    if (this.nodeInfo.type === 'Questioner' || this.nodeInfo.type === 'Agent') {
      if(this.query){
        inputsObj.query = this.query;
        this.query = '';
      }
    }

    return inputsObj;
  }

  private getPluginParam() {
    if (this.authParams.length) {
      const pluginParam = {
        plugin_id: (this.nodeInfo as IPluginNode).configs.id,
        config: {},
      };

      this.authParams.forEach((auth) => {
        pluginParam.config[auth.name] = auth.value;
      });

      return [pluginParam];
    }

    return [];
  }

  private async initAuthParams() {
    try {
      const value = await this.appPluginRepoServ.getPluginList({
        offset: 0,
        limit: 1,
        id: (this.nodeInfo as IPluginNode).configs.id,
      });

      if (
        value.plugin_list.length &&
        value.plugin_list[0].auth_info.scope === 'USER'
      ) {
        this.authParams = value.plugin_list[0].auth_info.auth_keys.map(
          (auth) => ({ name: auth.source_name, value: '' }),
        );
        this.isPluginConfigVisible = this.isShowPluginConfig();
        this.cdr.detectChanges();
      }
    } catch {
      // do nth
    }
  }

  private isShowPluginConfig() {
    return !!(this.nodeInfo?.type === 'Plugin' && this.authParams.length);
  }

  removeFile(inputItem, fileItem?) {
    if (!fileItem) {
      inputItem.file = '';
      inputItem.uploadData = {};
      return;
    }
    if (
      this.isUploading &&
      this.params[this.inputIndex].name !== inputItem.name
    ) {
      return;
    }
    // 如果删除的文件还未上传完成，则中止请求
    if (fileItem.progress === 'loading') {
      fileItem.controller.abort();
    }
    inputItem.uploadDatas = inputItem.uploadDatas.filter(
      (item) => item.fileId !== fileItem.fileId,
    );
    this.cdr.detectChanges();
  }

  getFileNameByUrl(url) {
    return decodeURIComponent(
      url?.split('file/')?.[1]?.split('?')[0] || 'unknown',
    );
  }
}
