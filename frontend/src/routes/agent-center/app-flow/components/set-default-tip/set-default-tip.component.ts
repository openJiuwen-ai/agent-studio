import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import {
  MonacoEditorComponent,
  MonacoEditorModule,
} from '@materia-ui/ngx-monaco-editor';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { ArrTypeValidatorDirective } from '@shared/directives/array-type-validator.directive';
import { ClickOutsideDirective } from '@shared/directives/click-outside.directive';
import {
  IntegerStrValidatorDirective,
  NumberStrValidatorDirective,
} from '@shared/directives/common-validator.directive';
import { ObjTypeValidatorDirective } from '@shared/directives/obj-type-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { debounce } from 'lodash';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { getInitInputParamConfig } from '../../flow.const';
import type {
  IWFView,
  IWFViewWithMultiType,
  IWorkflowField,
} from '../../node.type';
import { MonacoUri } from '../node-exe/node-exe.component';
import { EditorOptions, NodeUtils } from '../utils';
import { v4 as uuidV4 } from 'uuid';
import {
  createFileItem,
  uploadFile,
  validateFileSize,
  FileItem,
} from '@routes/agent-center/multiUpload.utils';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { formatUploadSizeMb } from '@routes/agent-center/utils';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import {
  UploadFileAccPipe,
  UploadFileDescPipe,
} from 'src/pipes/upload-file.pipe';
import { NzMessageService } from 'ng-zorro-antd/message';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzSpinModule } from 'ng-zorro-antd/spin';

interface IField extends IWorkflowField {
  file?: File;
  uploadData?: FileItem;
  uploadDatas?: Array<FileItem>;
}

interface IFormObj {
  value?: string;
  desc?: string;
  isClose: boolean;
  display?: string;
}

@Component({
  selector: 'meta-set-default-tip',
  templateUrl: './set-default-tip.component.html',
  styleUrls: ['./set-default-tip.component.less'],
  standalone: true,
  imports: [
    MODULES,
    MonacoEditorModule,
    IntegerStrValidatorDirective,
    NumberStrValidatorDirective,
    AssetFormatIconComponent,
    ArrTypeValidatorDirective,
    ObjTypeValidatorDirective,
    ClickOutsideDirective,
    UploadFileIconComponent,
    UploadFileAccPipe,
    UploadFileDescPipe,
    NzInputModule,
    NzSelectModule,
    NzIconModule,
    NzToolTipModule,
    NzSpinModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
    NzMessageService,
  ],
})
export class SetDefaultTipComponent implements OnInit, OnDestroy {
  @Input() param: IWFViewWithMultiType | IWFView = null;

  @Input() isNormalWidth = true;

  @Input() isShowDesc: boolean;

  @Input() host: string;

  @Input() cmpWidth: string;

  @ViewChild('valueForm') valueForm: NgForm;

  @ViewChild('editorCmp') editorCmp: MonacoEditorComponent;

  @Input() close: (state: IFormObj) => void;
  @Input() valueChange: (state: any) => void;

  public field: IField = getInitInputParamConfig();

  public isMulti = true;

  public editorOps = EditorOptions;

  public editorUri: MonacoUri = null;

  public value = '';

  public desc = '';

  public booleanOps = [
    {
      label: 'true',
      value: 'true',
    },
    {
      label: 'false',
      value: 'false',
    },
  ];

  public width = '520px';

  public cdn = cdnAssetUrl;

  public isUploading = false;

  public fileList: FileItem[] = [];

  public fileTypeAccept: string;

  public uploadDesc: string;

  public display = '';

  constructor(
    public cdr: ChangeDetectorRef,
    public i18n: I18NextEagerPipe,
    public repoServ: AppAgentRepoService,
    private configServ: AgentConfigService,
    private nzMessage?: NzMessageService,
  ) {}

  ngOnInit(): void {
    if (!this.param) {
      return;
    }
    this.isMulti = Array.isArray(this.param.type);
    const normalWith = this.isShowDesc ? '526px' : '520px';
    const useInnerWidthLogic = this.isNormalWidth ? normalWith : '386px';
    this.width = this.cmpWidth ? this.cmpWidth : useInnerWidthLogic;
    if (this.host === 'json-input') {
      this.value = String(this.param.value?.content) ?? ''; // 工作流或mcp节点支持json输入，显示value.content
    } else {
      this.value = this.param.value.default ?? ''; // 开始节点设置默认值，显示value.default
    }
    this.desc = this.param.description ?? '';
    this.initParam();
  }

  ngAfterViewInit(): void {
    if (this.field?.type === 'number' || this.field?.type === 'integer') {
      setTimeout(() => {
        const emailControl = this.valueForm?.controls?.defaultValue;
        emailControl?.markAsTouched();
        emailControl?.updateValueAndValidity();
      }, 50);
    }
  }

  formatContent() {
    this.editorCmp?.editor?.getAction('editor.action.formatDocument')?.run();
  }

  onArrChange() {
    this.cdr.detectChanges();
  }

  getError() {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    return this.valueForm?.controls?.defaultValue?.errors?.arrErr?.msg;
  }

  ngOnDestroy(): void {
    this.close?.({
      isClose: true,
    });
  }

  protected fileList2Value() {
    if (!this.fileList.length) {
      this.value = '';
      this.display = '';
      return;
    }
    const { names, urls } = this.fileList.reduce(
      (res, fileItem) => {
        const { progress, name, url } = fileItem;
        if (progress === 'succeeded') {
          res.names.push(name);
          res.urls.push(url);
        }
        return res;
      },
      {
        names: [],
        urls: [],
      },
    );
    if(this.isMulti){
      this.value = JSON.stringify(urls);
    }else{
      this.value = urls[0] ?? '';
    }
    this.display = names.join(',');
  }

  public async onUploadFile(e: Event) {
    this.isUploading = true;
    const input = e.target as HTMLInputElement;
    const files = input.files as FileList;
    const len = files.length;
    if (!len) {
      return;
    }
    if (!this.isMulti) {
      const file: File = files[0];
      const fileExtension = file.name.split('.').pop().toLowerCase();
      let isImage = false;
      // 上传大小限制： 图片5mb 非图片由部署配置控制
      if (
        ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(fileExtension)
      ) {
        if (file.size > 5 * 1024 * 1024) {
          this.nzMessage?.warning(
            this.i18n.transform('image_size_cannot_exceed_5mb'),
          );
          return;
        }
        isImage = true;
      } else if (file.size > this.configServ.getFileMaxSizeKb() * 1024) {
        this.nzMessage?.warning(
          this.i18n.transform('file_size_cannot_exceed', { size: formatUploadSizeMb(this.configServ.getFileMaxSizeKb()) }),
        );
        return;
      }

      const fileItem: FileItem = {
        fileId: uuidV4(),
        name: file.name,
        progress: 'loading',
        controller: new AbortController(),
        type: file.type,
        url: '',
      };
      this.fileList = [fileItem];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('is_image', JSON.stringify(isImage));
      try {
        const res = await this.repoServ.uploadFile(
          formData,
          fileItem.controller.signal,
        );
        fileItem.progress = 'succeeded';
        fileItem.url = res.url;
        this.cdr.detectChanges();
      } catch (error) {
        this.fileList = this.fileList.filter((f) => f.fileId !== fileItem.fileId);
        this.cdr.detectChanges();
      }
    } else {
      if (len + this.fileList.length > 10) {
        this.nzMessage?.warning(
          this.i18n.transform('upload_max_ten_files_tip'),
        );
        return;
      }
      for (const file of files) {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(
          extension,
        );
        const validationError = validateFileSize(file, isImage, 5 * 1024, this.configServ.getFileMaxSizeKb());
        if (validationError) {
          this.nzMessage?.warning(this.i18n.transform(validationError.key, validationError.params));
          continue;
        }
        const fileItem = createFileItem(file);
        this.fileList.push(fileItem);
        this.cdr.detectChanges();
        await new Promise(resolve => setTimeout(resolve));
        await uploadFile(this.repoServ, file, isImage, fileItem, () => {
          this.fileList = this.fileList.filter((f) => f.fileId !== fileItem.fileId);
          this.cdr.detectChanges();
        });
      }
    }
    this.isUploading = false;
    input.value = '';
    this.saveFile();
  }

  saveFile() {
    if (
      this.param.type.includes('file') ||
      this.param.type.includes('array<file>')
    ) {
      this.fileList2Value();
      this.valueChange?.(
        {
          value: this.value,
          desc: this.desc,
          display: this.display
        }
      );
    }
  }

  removeFile(event: Event, index: number) {
    event.stopPropagation();
    const fileItem = this.fileList[index];
    // 如果删除的文件还未上传完成，则中止请求
    if (fileItem.progress === 'loading') {
      fileItem.controller.abort();
    }
    this.fileList.splice(index, 1);
    this.saveFile();
  }

  initParam() {
    const result = this.isMulti
      ? NodeUtils.multiTypeViews2Fields([this.param as IWFViewWithMultiType])
      : NodeUtils.views2Fields([this.param as IWFView]);
    if (!result.length) {
      this.field = getInitInputParamConfig();
      return;
    }
    this.field = result[0];
    if (
      !this.param.type.includes('file') &&
      !this.param.type.includes('array<file>')
    ) {
      return;
    }
    const [, type = 'default'] = this.param.type || [];
    this.isMulti = this.param.type.includes('array<file>');
    this.fileTypeAccept = `file/${type}`;
    this.uploadDesc = this.isMulti ? `array<file/${type}>` : this.field.type;
    const { default: defaultVal = '', display = '' } = this.field?.value || {};
    if (!defaultVal) {
      return;
    }
    let urls: string[] = [];
    try {
      urls = JSON.parse(defaultVal);
    } catch (err) {
      urls = defaultVal.split(',');
    }
    const names = display.split(',');
    this.fileList = urls.map((url, i) => {
      const name = names[i] || this.getFileNameByUrl(url);
      return {
        name,
        url,
        progress: 'succeeded',
        fileId: uuidV4(),
        type: '',
        controller: null,
      };
    });
  }

  debounceInput = debounce(this.onValueChange.bind(this), 200);

  debounceInputDesc = debounce(this.onDescChange.bind(this), 200);

  onDescChange() {
    this.close?.({
      value: this.value,
      desc: this.desc,
      isClose: false,
    });
  }

  onValueChange() {
    if (this.valueForm?.form?.invalid) {
      return;
    }

    const emitObj: IFormObj = {
      value: this.value,
      isClose: false,
    };

    if (this.isShowDesc) {
      emitObj.desc = this.desc;
    }

    this.close?.(emitObj);
  }

  onClickOutside(e: Event) {
    if (
      (e?.target as HTMLElement)?.tagName?.toLowerCase() === 'nz-popover'
    ) {
      return;
    }

    if (this.isUploading) {
      return;
    }
    if (
      !this.param ||
      this.param.type.includes('file') ||
      this.param.type.includes('array<file>')
    ) {
      this.fileList2Value();
    }

    if (this.valueForm?.form?.invalid) {
      this.value = '';
    }
    const emitObj: IFormObj = {
      value: this.value,
      display: this.display,
      isClose: true,
    };

    if (this.isShowDesc) {
      emitObj.desc = this.desc;
    }

    this.close?.(emitObj);
  }

  getFileNameByUrl(url) {
    return decodeURIComponent(
      url?.split('file/')?.[1]?.split('?')[0] || 'unknown',
    );
  }

  public handleKeyDown(event: KeyboardEvent) {
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      (event.target instanceof HTMLDivElement &&
        event.target.className.includes('editor'))
    ) {
      if (
        (event.ctrlKey || event.metaKey) &&
        ['s', 'c', 'v', 'z', 'y'].includes(event.key)
      ) {
        event.stopPropagation();
      }
    }
  }
}
