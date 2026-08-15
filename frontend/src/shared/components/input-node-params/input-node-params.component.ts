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
        item.type = `array<${item.actualType}>`;
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
    if (uploadType === 'single') {
      const file: File = input.files[0];
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
      const len = input?.files?.length;
      if (!len) {
        return;
      }
      inputItem.isEmpty = false;
      if (!inputItem.uploadDatas) {
        inputItem.uploadDatas = [];
      }
      if (len + inputItem.uploadDatas.length > 10) {
        MessageComponent.showWarn(
          this.i18n.transform('upload_max_ten_files_tip'),
        );
        return;
      }
      this.inputIndex = this.inputList.findIndex(
        (item) => item.name === inputItem.name,
      );
      for (const file of input.files as any) {
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
      this.disabled !== 'confirmed'
    );
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
