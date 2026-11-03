import { Component } from '@angular/core';

import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { CommonModule } from '@angular/common';
import { MODULES } from '@shared/modules';
import { TextFieldModule } from '@angular/cdk/text-field';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { UploadFileIconComponent } from '@shared/components/upload-file-icon/upload-file-icon.component';
import { UploadFileAccPipe, UploadFileDescPipe } from '../../../pipes/upload-file.pipe';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { FileUrlInputComponent } from '@shared/components/file-url-input/file-url-input.component';

@Component({
  selector: 'dynamic-node-params-chat',
  templateUrl: './dynamic-node-params-chat.component.html',
  styleUrls: [
    './dynamic-node-params-chat.component.less',
    '../../../styles/text-field-prebuilt.css',
  ],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    MonacoEditorModule,
    AssetFormatIconComponent,
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
export class DynamicNodeParamsComponentChat extends DynamicNodeParamsComponent {}
