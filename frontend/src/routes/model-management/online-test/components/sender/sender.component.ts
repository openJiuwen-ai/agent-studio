import { Component, Input, OnDestroy } from '@angular/core';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { VoiceService } from '@services/voice.service';
import { SenderComponent } from '@shared/components/sender/sender.component';
import { CdkTextareaAutosize } from '@angular/cdk/text-field';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import { ModelType } from '@enums/jiuwen-model.enum';
import { v4 as uuidV4 } from 'uuid';

import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { NzInputModule } from 'ng-zorro-antd/input';

interface FileItem {
  type: string;
  progress: string;
  name: string;
  url: string;
  file?: File;
  fileId?: string;
  isImage?: boolean;
  controller?: AbortController;
}

@Component({
  selector: 'model-meta-sender',
  templateUrl: './sender.component.html',
  styleUrls: ['./sender.component.less'],
  standalone: true,
  imports: [
    MODULES,
    CdkTextareaAutosize,
    UploadFileIconComponent,
    NzIconModule,
    NzToolTipModule,
    NzInputModule
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.JIUWEN_MODEL,
        I18nNamespace.AGENT_CENTER,
        I18nNamespace.JIUWEN_MODEL,
      ],
    },
    VoiceService,
  ],
})
export class ModelSenderComponent
  extends SenderComponent
  implements OnDestroy
{
  @Input() modelType: string = ModelType.LLM;

  public chat_placeholder_llm = this.i18n.transform('chat_placeholder_llm', {
    ns: I18nNamespace.JIUWEN_MODEL,
  });

  public chat_placeholder_vision = this.i18n.transform(
    'chat_placeholder_vision',
    {
      ns: I18nNamespace.JIUWEN_MODEL,
    },
  );

  override fileAccept =
    '.png,.jpg,.jpeg,.gif,.webp,.mp4,.avi,.rmvb,.mkv,.flv,.f4v,.wmv,.3gp';

  override uploadFile() {
    if (this.disabled) {
      return;
    }
    if (this.uploadData.length >= 20) {
      return;
    }
    this.fileInput.nativeElement.click();
  }

  override async onUploadFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    const len = files?.length;
    if (len <= 0) {
      return;
    }
    if (len + this.uploadData.length > 20) {
      this.message.warning(
        this.i18n.transform('upload_max_files_tip'),
      );
      return;
    }
    this.uploading = true;
    const fileArray = Array.from(files);
    const validFiles: FileItem[] = fileArray.flatMap((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg'].includes(ext);
      const limit = isImage ? 1024 * 1024 * 5 : 1024 * 1024 * 60;

      if (file.size > limit) {
        this.message.warning(
          this.i18n.transform(
            isImage
              ? 'image_size_cannot_exceed_5mb'
              : 'file_size_cannot_exceed_128mb',
          ),
        );
        return [];
      }

      return [
        {
          progress: 'loading',
          type: isImage ? 'image' : 'file',
          name: file.name,
          url: '',
          file,
          isImage,
          fileId: uuidV4(),
          controller: new AbortController(),
        },
      ];
    });
    for (const validFile of validFiles) {
      const { file } = validFile;
      let url: any = '';
      if (file) {
        url = await this.readFile(file);
      }
      this.uploading = false;
      this.uploadData.push({
        ...validFile,
        url,
        progress: 'succeeded',
      });
    }
  }

  readFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();

      reader.onload = function (event) {
        resolve(event.target.result);
      };

      reader.onerror = function (event) {
        reject(event.target.error);
      };

      reader.readAsDataURL(file);
    });
  }

}
