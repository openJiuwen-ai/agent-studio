import {Component, EventEmitter, Input, Output, QueryList, SimpleChanges, ViewChildren,} from '@angular/core';
import {FormBuilder, FormControl, FormGroup, Validators} from '@angular/forms';
import {MODULES} from '@shared/modules';
import {I18nNamespace} from '@i18n';
import {I18NEXT_NAMESPACE, I18NextEagerPipe} from 'angular-i18next';
import {TextFieldModule} from '@angular/cdk/text-field';
import {cloneDeep} from 'lodash';
import {cdnAssetUrl} from 'src/single-spa/assets-url';
import {AppAgentRepoService} from '@services/agent-center/app-agent-repo.service';
import {AppFlowService} from '@routes/agent-center/app-flow/app-flow.service';
import {MessageComponent} from '@shared/services/cfdata.service';
import {createFileItem, uploadFile, validateFileSize,} from '@routes/agent-center/multiUpload.utils';
import {AgentConfigService} from '@routes/agent-center/agent-config.service';
import {formatUploadSizeMb} from '@routes/agent-center/utils';
import {UploadFileIconComponent} from '../upload-file-icon/upload-file-icon.component';
import {UploadFileAccPipe, UploadFileDescPipe,} from 'src/pipes/upload-file.pipe';
import {
  createUrlFileItem,
  getUrlDisplayName,
  hasLocalFileItems,
  hasUrlFileItems,
} from '@routes/agent-center/file-url.utils';
import {FileUrlInputComponent} from '@shared/components/file-url-input/file-url-input.component';
import type {InputChatItem, InputParamConfig} from './input-node-params.interface';

@Component({
  selector: 'input-node-params',
  templateUrl: './input-node-params.component.html',
  styleUrls: [
    './input-node-params.component.scss',
    '../../../styles/text-field-prebuilt.css',
  ],
  standalone: true,
  imports: [
    MODULES,
    TextFieldModule,
    UploadFileIconComponent,
    UploadFileAccPipe,
    UploadFileDescPipe,
    FileUrlInputComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class InputNodeParamsComponent {
  @ViewChildren('fileInput') fileInputs: QueryList<any>;

  // 传入的类型实际为 IInputItem，组件存在内部修改，需优化
  @Input() inputList: InputParamConfig[] = [];

  @Input() disabled: string;

  @Input() chatItem: InputChatItem;

  @Output() fileUploadStatus = new EventEmitter<string>();

  public parameterFromGroup: FormGroup;

  // 对话型工作流中，所有answer卡片中出现的输入节点的控件列表
  public allControlValues: { [key: string]: any } = {};

  public changeUrl = cdnAssetUrl;
  public isUploading = false;
  public inputIndex: number;

  constructor(
    private fb: FormBuilder,
    private appAgentServe: AppAgentRepoService,
    private appFlowServe: AppFlowService,
    private i18n: I18NextEagerPipe,
    private configServ: AgentConfigService,
  ) {
    this.parameterFromGroup = this.fb.group({});
  }

  ngOnChanges(changes: SimpleChanges): void {
    this.inputList.forEach((item) => {
      if (item.name === 'multi') {
        item.type = `array<file/default>`;
      }
      if (item.type === 'array' && item?.actualType?.includes('file')) {
        // actualType 可能为完整数组类型（Array<File> 参数经 IR 转换后为 array<file/image>），
        // 再包一层会得到 array<array<file/image>>（fileAcc/fileUploadAcc 均取不到键，
        // 上传 accept 与 URL 扩展名白名单全失效），仅在未包裹时拼接
        item.type = item.actualType?.startsWith('array<')
          ? item.actualType
          : `array<${item.actualType}>`;
      }
      if (item.type === 'string' && item?.actualType?.includes('file')) {
        item.type = item.actualType;
      }
    });
    if (changes.inputList) {
      const inputNodeParams = cloneDeep(changes.inputList.currentValue);
      this.initDynamicForm(inputNodeParams);
    }
  }

  public handleUserInput(control_name: string, isValidate: boolean) {
    // 启用校验
    const control = this.parameterFromGroup.get(control_name);
    if (control) {
      const validators = isValidate ? [] : null;
      control.setValidators(validators);
      control.updateValueAndValidity();
    }
  }

  public checkInput(list: any[]): boolean {
    list?.forEach((requirement: any) => {
      const { uniqueId } = requirement;
      const control = this.parameterFromGroup.get(uniqueId);
      const validators = requirement.required ? Validators.required : null;
      control.setValidators(validators);
      control.updateValueAndValidity();
    });

    let pass = true;
    this.parameterFromGroup.markAllAsTouched();
    list?.forEach((requirement: any) => {
      const control = this.parameterFromGroup.get(requirement.uniqueId);
      if (control?.hasError('required')) {
        pass = false;
        requirement.isEmpty = true;
      } else {
        requirement.isEmpty = false;
      }
    });

    return pass;
  }

  public getDynamicParams(dialogId: string) {
    return this.filterFormControls(dialogId);
  }

  public resetFormVal() {
    this.parameterFromGroup.reset();
  }

  public removeFile(inputItem: InputParamConfig, canDelete: string, fileItem?) {
    if (canDelete === 'confirmed') {
      return;
    }
    if (!fileItem) {
      inputItem.file = undefined;
      inputItem.uploadData = {};
      this.parameterFromGroup.controls[inputItem.uniqueId].setValue('');
      return;
    }
    if (
      this.isUploading &&
      this.inputList[this.inputIndex].name !== inputItem.name
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
    this.parameterFromGroup.controls[inputItem.uniqueId].setValue(
      inputItem.uploadDatas,
    );
    setTimeout(() => {
      if (!this.isUploading) {
        this.updateUploadStatus();
      }
    });
  }

  public async onUploadFile(e: Event, inputItem: InputParamConfig, uploadType = 'multi'): Promise<void> {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = '';
    if (uploadType === 'single') {
      const file: File = files[0];
      if (!file) {
        return;
      }
      const fileExtension = file.name.split('.').pop().toLowerCase();
      let isImage = false;
      // 上传大小限制： 图片5mb 非图片由部署配置控制
      if (
        ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(fileExtension)
      ) {
        if (file.size > 5 * 1024 * 1024) {
          MessageComponent.showWarn(
            this.i18n.transform('image_size_cannot_exceed_5mb'),
          );
          return;
        }
        isImage = true;
      } else if (file.size > this.configServ.getFileMaxSizeKb() * 1024) {
        MessageComponent.showWarn(
          this.i18n.transform('file_size_cannot_exceed', { size: formatUploadSizeMb(this.configServ.getFileMaxSizeKb()) }),
        );
        return;
      }
      inputItem.uploadData = {};
      inputItem.uploadData.name = file.name;
      inputItem.file = file;
      this.parameterFromGroup.controls[inputItem.uniqueId].setValue(file);
      input.value = '';

      inputItem.uploadData.progress = 'loading';
      this.fileUploadStatus.emit('loading');
      inputItem.isEmpty = false;

      const formData = new FormData();
      formData.append('file', file);
      formData.append('is_image', JSON.stringify(isImage));
      this.appAgentServe
        .uploadFile(formData)
        .then((res: any) => {
          inputItem.uploadData.progress = 'succeeded';
          this.fileUploadStatus.emit('succeeded');
          this.parameterFromGroup.controls[inputItem.uniqueId].setValue(
            res.url,
          );
        })
        .catch(() => {
          inputItem.uploadData = null;
          inputItem.file = undefined;
          this.fileUploadStatus.emit('failed');
          this.parameterFromGroup.controls[inputItem.uniqueId].setValue('');
        });
    } else {
      const len = files?.length;
      if (!len) {
        return;
      }
      inputItem.isEmpty = false;
      if (!inputItem.uploadDatas) {
        inputItem.uploadDatas = [];
      }
      if (len + inputItem.uploadDatas.length > 20) {
        MessageComponent.showWarn(
          this.i18n.transform('upload_max_files_tip'),
        );
        return;
      }
      // 同名文件整批拒绝（完整文件名含后缀，忽略大小写）
      if (
        Array.from(files as any as File[]).some((f) =>
          inputItem.uploadDatas.some(
            (u) => u.name.toLowerCase() === f.name.toLowerCase(),
          ),
        )
      ) {
        MessageComponent.showWarn(
          this.i18n.transform('duplicate_files_rejected_tip'),
        );
        return;
      }
      this.inputIndex = this.inputList.findIndex(
        (item) => item.name === inputItem.name,
      );
      // 批次开始置位、整批结束复位，驱动一键清空/添加按钮的上传中禁用
      this.isUploading = true;
      for (const file of files as any) {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(
          extension,
        );
        const validationError = validateFileSize(file, isImage, 5 * 1024, this.configServ.getFileMaxSizeKb());
        if (validationError) {
          MessageComponent.showWarn(this.i18n.transform(validationError.key, validationError.params));
          continue;
        }
        const fileItem = createFileItem(file);
        inputItem.uploadDatas.push(fileItem);
        await new Promise(resolve => setTimeout(resolve));
        await uploadFile(this.appAgentServe, file, isImage, fileItem, () => {
          inputItem.uploadDatas = inputItem.uploadDatas.filter((f) => f.fileId !== fileItem.fileId);
        });
      }
      this.isUploading = false;
      this.parameterFromGroup.controls[inputItem.uniqueId].setValue(
        inputItem.uploadDatas,
      );
      input.value = '';
    }
  }

  public getControlValue(dialogId: string, inputName: string): any {
    this.parameterFromGroup = this.appFlowServe.getAnswerInputForm();

    const existingControls = this.parameterFromGroup.controls;
    Object.keys(existingControls).forEach((item) => {
      this.allControlValues[item] = this.parameterFromGroup.get(item)?.value;
    });
    const item = `${dialogId}-${inputName}`;
    return this.allControlValues[item];
  }

  public isShowMultiBtn(inputItem) {
    return (
      inputItem.type.includes('array<file') &&
      inputItem.uploadDatas?.length > 0 &&
      inputItem.urlMode !== 'url' &&
      this.disabled !== 'confirmed' &&
      // 互斥：已存在 URL 录入条目时不再追加本地上传（需先清空文件）
      !hasUrlFileItems(inputItem.uploadDatas)
    );
  }

  /**
   * 互斥：当前参数是否已存在本地上传来源的条目。
   * 多文件按条目 fromUrl 标记判定；单文件本地上传路径 file 恒有值
   * （URL 录入不带 file）。
   */
  public hasLocalFileEntries(inputItem: InputParamConfig): boolean {
    return inputItem.type.includes('array<file')
      ? hasLocalFileItems(inputItem.uploadDatas)
      : !!inputItem.file;
  }

  /** 互斥：当前参数是否已存在 URL 录入来源的条目 */
  public hasUrlFileEntries(inputItem: InputParamConfig): boolean {
    return inputItem.type.includes('array<file')
      ? hasUrlFileItems(inputItem.uploadDatas)
      : inputItem.uploadData?.fromUrl === true;
  }

  public clearMultiFiles(inputItem): void {
    if (this.isUploading) {
      return;
    }
    inputItem.uploadDatas = [];
    this.parameterFromGroup.controls[inputItem.uniqueId]?.setValue([]);
  }

  public addMultiFile(index): void {
    if (this.isUploading || this.disabled === 'confirmed') {
      return;
    }
    let element = this.fileInputs.find((el) =>
      el.nativeElement.className.includes(`input${index}`),
    );
    if (element) {
      element.nativeElement.click();
    }
  }

  /** URL 模式新增条目（file-url-input 已完成协议头/扩展名校验与去重） */
  public onAddUrlEntries(inputItem: InputParamConfig, urls: string[]): void {
    // 互斥：已存在本地上传条目时禁止再录入 URL（file-url-input 已阻断，双保险）
    if (this.disabled === 'confirmed' || !urls.length || this.hasLocalFileEntries(inputItem)) {
      return;
    }
    inputItem.isEmpty = false;
    if (inputItem.type.includes('array<file')) {
      inputItem.uploadDatas = [
        ...(inputItem.uploadDatas || []),
        ...urls.map((url) => createUrlFileItem(url)),
      ];
      // 与上传路径同契约：控件值 = FileItem 对象数组（消费方按 url 字段取值）
      this.parameterFromGroup.controls[inputItem.uniqueId]?.setValue(
        inputItem.uploadDatas,
      );
    } else {
      // 单文件：与上传成功路径同契约（控件值 = URL 字符串）
      inputItem.uploadData = {
        name: getUrlDisplayName(urls[0]),
        progress: 'succeeded',
        url: urls[0],
        fromUrl: true,
      };
      inputItem.file = undefined;
      this.parameterFromGroup.controls[inputItem.uniqueId]?.setValue(
        urls[0],
      );
    }
  }

  /** 供 URL 去重：当前已录入条目的 URL 列表 */
  public getExistingUrls(inputItem: InputParamConfig): string[] {
    if (inputItem.type.includes('array<file')) {
      return (inputItem.uploadDatas || [])
        .map((item) => item.url)
        .filter(Boolean);
    }
    if (inputItem.uploadData?.url) {
      return [inputItem.uploadData.url];
    }
    // 上传成功路径的 URL 存于控件值（uploadData 无 url 字段）
    const controlVal = this.parameterFromGroup.controls[inputItem.uniqueId]
      ?.value;
    return typeof controlVal === 'string' && controlVal ? [controlVal] : [];
  }

  /**
   * 编辑已录入的 URL 条目（原位编辑）：条目保留在列表中，切到 URL 模式
   * 并把 URL 回填输入框，用户修改后点「保存」提交（onSaveUrlEntry），
   * 点「取消」或切换页签放弃编辑（条目原值不受影响）。
   */
  public editUrlEntry(inputItem: InputParamConfig, fileItem?): void {
    if (this.disabled === 'confirmed' || this.isUploading) {
      return;
    }
    const url = fileItem?.url || inputItem.uploadData?.url;
    if (!url) {
      return;
    }
    inputItem.urlMode = 'url';
    inputItem.urlEditReq = { url };
  }

  /** 编辑态保存：按原 URL 定位条目并原位替换为新 URL（同步控件值） */
  public onSaveUrlEntry(
    inputItem: InputParamConfig,
    edit: { originalUrl: string; url: string },
  ): void {
    if (this.disabled === 'confirmed') {
      return;
    }
    if (inputItem.type.includes('array<file')) {
      const uploadDatas = inputItem.uploadDatas || [];
      const index = uploadDatas.findIndex(
        (item) => item.fromUrl === true && item.url === edit.originalUrl,
      );
      if (index < 0) {
        return;
      }
      inputItem.uploadDatas = uploadDatas.map((item, i) =>
        i === index
          ? { ...item, url: edit.url, name: getUrlDisplayName(edit.url) }
          : item,
      );
      // 与上传路径同契约：控件值 = FileItem 对象数组（消费方按 url 字段取值）
      this.parameterFromGroup.controls[inputItem.uniqueId]?.setValue(
        inputItem.uploadDatas,
      );
    } else {
      if (inputItem.uploadData?.url !== edit.originalUrl) {
        return;
      }
      inputItem.uploadData = {
        ...inputItem.uploadData,
        url: edit.url,
        name: getUrlDisplayName(edit.url),
      };
      // 单文件：与上传成功路径同契约（控件值 = URL 字符串）
      this.parameterFromGroup.controls[inputItem.uniqueId]?.setValue(
        edit.url,
      );
    }
  }

  /** 初始化动态表单 */
  private initDynamicForm(list: any) {
    this.parameterFromGroup = this.appFlowServe.getAnswerInputForm();

    list?.forEach((requirement: any) => {
      this.parameterFromGroup.addControl(
        requirement.uniqueId,
        new FormControl(null, []),
      );
      if(requirement.value){
        this.parameterFromGroup.controls[requirement.uniqueId].setValue(requirement.value);
      }
    });

    this.appFlowServe.setAnswerInputForm(this.parameterFromGroup);
  }

  private filterFormControls(dialogId: string) {
    const controlsFiltered = {};
    Object.keys(this.parameterFromGroup?.controls ?? {}).forEach((item) => {
      let value = ''
      if (item.startsWith(dialogId)) {
        const newName = item.replace(`${dialogId}-`, '');
        value= this.parameterFromGroup.get(item).value;
        controlsFiltered[newName] = value;
      }else if(!dialogId){
        //异步场景加入的判断
        value = this.parameterFromGroup.get(item).value;
        controlsFiltered[item] = value;
      }
    });
    return controlsFiltered;
  }

  private updateUploadStatus() {
    const inputItem = this.inputList[this.inputIndex];
    if (inputItem.uploadDatas?.some((f) => f.progress === 'failed')) {
      this.fileUploadStatus.emit('failed');
    } else {
      this.fileUploadStatus.emit('succeeded');
    }
  }
}
