import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Input,
  OnDestroy,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { InlineSvgComponent } from '../inline-svg.component';
import {
  catchError,
  concatMap,
  filter,
  finalize,
  from,
  of,
  Subject,
  takeUntil,
  tap,
} from 'rxjs';
import { TextFieldModule } from '@angular/cdk/text-field';
import { UploadFileIconComponent } from '../upload-file-icon/upload-file-icon.component';
import { MessageComponent } from '@shared/services/cfdata.service';
import { v4 as uuidV4 } from 'uuid';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { formatUploadSizeMb } from '@routes/agent-center/utils';
import { VoiceService } from '@services/voice.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AiAnswerListService } from '@routes/agent-center/app-agent/components/chat-item/ai-answer.component.service';
import { CommonService } from '@services/common.service';
import { HttpService } from '@services/http.service';
import { ActivatedRoute } from '@angular/router';
import type { ISingleAgentQueryResp } from '@routes/agent-center/types/my-workspace.types';
import { CommonModule } from '@angular/common';
import { NzMessageService } from 'ng-zorro-antd/message';

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

enum mapKeys {
  agentSubType = 'agentSubType',
}

export interface SendData {
  role: 'assistant' | 'user';
  content: string;
  uploadData?: FileItem[];
}

@Component({
  selector: 'meta-sender',
  templateUrl: './sender.component.html',
  styleUrls: ['./sender.component.less'],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    InlineSvgComponent,
    TextFieldModule,
    UploadFileIconComponent,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT],
    },
    VoiceService,
  ],
})
export class SenderComponent implements OnDestroy {
  @Input() showClear = true;
  @Input() sending = false;

  @Input() disabled = false;

  @Input() maxlength = 5000;

  @Input() isShowFileUpload = true;

  @Input() userVoiceControl = true; //工作流是否开启语音交互功能

  @Input() searchEngine: any[] = []; // 搜索引擎数据

  @Input() agentType: string = ''; // 标识当前agent是否是deepresearch

  @Input() agentInfo: ISingleAgentQueryResp = {
    icon: '',
    name: '',
    description: '',
    id: '',
    agentSubType: '', // 标识当前agent是否是deepresearch
  };

  @Input() placeholder?: string = ''; //根据任务状态对话框展示不同的提示

  @Input() aiDisclaimer?: string = this.i18n.transform('ai_generated_disclaimer_three');

  @Input() senderDiabledTip = '';

  @Output() clear = new EventEmitter<void>();

  @Output() send = new EventEmitter<SendData>();

  @Output() stop = new EventEmitter<void>();

  //写作模板
  @Output() fileTemplate = new EventEmitter<string>();

  //判断来自deep运行面
  @Input() isRuntime = false;

  //兼容工作流不可发送
  @Input() isDisableSender = false;

  @Input() fileInfo: any = {};

  @Output() disabledSender = new EventEmitter<boolean>();

  @ViewChild('textarea') textarea?: ElementRef<HTMLTextAreaElement>;

  @ViewChild('fileInput') fileInput: ElementRef<HTMLInputElement>;

  @ViewChild('singleInput') singleInput: ElementRef<HTMLInputElement>;

  public changeUrl = cdnAssetUrl;

  public content = '';

  public uploadData: FileItem[] = [];

  public isInput = false;

  public destroy$ = new Subject<void>();

  public showSend = false;

  public voiceEnable = false;

  public recording = false;

  public uploading = false;
  remainingTime: number;
  showConvertAudio: boolean;
  timerId: NodeJS.Timeout;

  public actions = [
    {
      icon: 'switcher',
      id: 'change',
      label: this.i18n.transform('change_template'),
    },
    {
      icon: 'delete',
      id: 'delete',
      label: this.i18n.transform('delete_template'),
    },
  ];



  public sendIconUrl = '';

  public fileAccept =
    '.docx,.doc,.pdf,.txt,.xls,.xlsx,.csv,.png,.jpg,.jpeg,.gif,.webp,.mp3,.m4a,.wav,.mp4,.mov,.webm';

  public isHttps = true;

  subscribeBtnStatus = this.commonService.getSubscribeStatus();

  type_page = '';
  public isDisabledSenderBtn: boolean = false;
  isSingleRow = true;

  public senderTip = '';

  constructor(
    protected i18n: I18NextEagerPipe,
    private appAgentServe: AppAgentRepoService,
    private configServ: AgentConfigService,
    public voiceService: VoiceService,
    private aiAnswerListService: AiAnswerListService,
    private readonly commonService: CommonService,
    private readonly http: HttpService,
    private route: ActivatedRoute,
    public message: NzMessageService,
  ) {
    this.route.queryParams.subscribe((params) => {
      this.type_page = params?.type ?? '';
    });

    this.voiceEnable = this.configServ.voiceEnable();
    this.voiceService
      .audioBlobObservable()
      .pipe(
        takeUntil(this.destroy$),
        filter((data) => !!data && data.role !== 'assistant'),
      )
      .subscribe((data) => {
        this.voiceService
          .voiceToTextPost({ data: data.base64 })
          .then((res) => {
            if (res?.message) {
              this.content += res?.message;
              this.onInput();
            }
          })
          .finally(() => {
            this.showConvertAudio = false;
          });
      });

    this.voiceService.isRecording$
      .pipe(takeUntil(this.destroy$))
      .subscribe((val) => {
        this.recording = val;
      });

      this.voiceService.stopRecord$.subscribe((val) => {
        this.stopRecording(false);
      });
  }


  ngOnInit() {
    this.isDisabledSenderBtn =
      this.searchEngine &&
      this.searchEngine.length <= 0 &&
      this.agentInfo &&
      this.agentInfo.agentSubType === 'deepresearch';
    this.disabledSender.emit(this.isDisabledSenderBtn);
  }

  ngAfterViewInit() {
    this.checkContentWidth();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.fileInfo) {
      this.fileInfo = changes.fileInfo.currentValue;
    }
    if (changes && changes.searchEngine) {
      this.isDisabledSenderBtn =
        this.searchEngine &&
        this.searchEngine.length <= 0 &&
        this.agentInfo &&
        this.agentInfo.agentSubType === 'deepresearch';
      this.disabledSender.emit(this.isDisabledSenderBtn);
    }
    if (changes && changes.agentType) {
      this.isDisabledSenderBtn =
        this.searchEngine &&
        this.searchEngine.length <= 0 &&
        this.agentInfo &&
        this.agentInfo.agentSubType === 'deepresearch';
      this.disabledSender.emit(this.isDisabledSenderBtn);
    }
    this.senderTip = this.getSenderTip();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private getSenderTip() {
    let tip = '';
    if (this.isDisableSender) {
      tip = this.senderDiabledTip;
    }
    return !tip && this.isDisabledSenderBtn ? this.i18n.transform('deepresearch-no-search') : tip;
  }

  public setContent(content: string) {
    this.content = content;
    this.onInput();
  }

  public onFocus() {
    this.isInput = true;
  }

  public onBlur() {
    // 延时处理blur，防止点击功能图标时会先触发blur，然后才触发图标点击事件
    const timer = setTimeout(() => {
      if (this.recording) {
        return;
      }
      this.isInput = false;
      clearTimeout(timer);
    }, 100);
  }

  public onSend() {
    if( this.isDisableSender){
      return;
    }
    if (this.isDisabledSenderBtn || this.showConvertAudio) {
      this.disabledSender.emit(true);
      return;
    }
    if (
      this.sending || // 正在发送
      this.recording || // 正在录音
      this.uploading || // 正在上传文件
      !this.showSend // 用户query内容为空
    ) {
      return;
    }
    this.send.emit({
      role: 'user',
      content: this.content.trim(),
      uploadData: this.uploadData,
    });
    this.textarea?.nativeElement.blur();
    this.showSend = false;
    this.content = '';
    this.uploadData = [];
    setTimeout(()=> {
      this.checkContentWidth();
    });
  }

  public onStop() {
    this.stop.emit();
  }

  public onInput() {
    this.showSend = this.content.trim().length !== 0;
  }

  public onClear() {
    this.aiAnswerListService.aiAnswerList = [];
    this.clear.emit();
  }

  public uploadFile() {
    if (this.uploadData.length >= 10) {
      return;
    }
    this.fileInput.nativeElement.click();
  }

  public onUploadFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    const len = files?.length;
    if (len <= 0) {
      return;
    }
    if (len + this.uploadData.length > 10) {
      MessageComponent.showWarn(
        this.i18n.transform('upload_max_ten_files_tip'),
      );
      return;
    }
    this.uploading = true;
    const fileArray = Array.from(files);
    const validFiles: FileItem[] = fileArray.flatMap((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg'].includes(ext);
      const limit = isImage ? 5 * 1024 * 1024 : this.configServ.getFileMaxSizeKb() * 1024;

      if (file.size > limit) {
        MessageComponent.showWarn(
          this.i18n.transform(
            isImage
              ? 'image_size_cannot_exceed_5mb'
              : 'file_size_cannot_exceed',
            isImage ? undefined : { size: formatUploadSizeMb(this.configServ.getFileMaxSizeKb()) },
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
    validFiles.forEach((item) => this.uploadData.push(item));
    this.checkContentWidth();
    setTimeout(() => {
      from(validFiles)
        .pipe(
          takeUntil(this.destroy$),
          concatMap((item) => {
            const { file, isImage, controller } = item;
            const formData = new FormData();
            formData.append('file', file);
            formData.append('is_image', JSON.stringify(isImage));
            return from(
              this.appAgentServe.uploadFile(formData, controller.signal),
            ).pipe(
              tap((res) => {
                item.progress = 'succeeded';
                item.url = res.url;
              }),
              catchError(() => {
                this.uploadData = this.uploadData.filter((f) => f.fileId !== item.fileId);
                this.checkContentWidth();
                return of(null);
              }),
            );
          }),
          finalize(() => {
            this.uploading = false;
            input.value = '';
            this.checkContentWidth();
          }),
        )
        .subscribe();
    });
  }

  public removeFile(i: number) {
    this.uploadData.splice(i, 1);
    if (!this.uploadData.length) {
      this.checkContentWidth();
    }
  }

  public startRecording() {
    this.recording = true;
    this.timerFn();
    this.isInput = true;
    this.voiceService.startRecording();
    this.checkContentWidth();
  }

  public timerFn() {
    this.remainingTime = 0;
    this.timerId = setInterval(() => {
      this.remainingTime++;

      // 当时间到0时，清除计时器并提示
      if (this.remainingTime === 60) {
        clearInterval(this.timerId);
        this.stopRecording(true);
      }
    }, 1000);
  }

  public stopRecording(hasPermission: boolean) {
    this.recording = false;
    clearInterval(this.timerId);
    this.voiceService.stop();
    if (hasPermission) {
      this.showConvertAudio = true;
    }
  }

  public addFileTemplate() {
    if (this.disabled || this.fileInfo.disabled) {
      return;
    }
    this.fileTemplate.emit('change');
  }

  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent) {

    if (event.key === 'Enter') {
      if (event.ctrlKey || event.altKey) {
        // ctrl+enter
        this.content += '\n';
        this.checkContentWidth();
      } else {
        this.onSend();
      }
      event.preventDefault();
    }
  }


  onClick(e) {
    e.stopPropagation();
  }

  deleteTemplate() {
    if (this.disabled || this.fileInfo.disabled) {
      return;
    }
    this.fileTemplate.emit('delete');
  }

  handelTask(type, item, indexObj) {
    switch (type) {
      case 'change':
        this.addFileTemplate();
        return;
      case 'delete':
        this.deleteTemplate();
        return;

      default:
        return;
    }
  }


  // 检查内容宽度是否小于 input 容器宽度
  checkContentWidth() {
    this.onInput();
    let inputWidth;
    let contentWidth;
    let inputEl;
    if(!this.singleInput && !this.textarea) {
      return;
    }

    if (/\n|\r\n/.test(this.content)) {
      this.isSingleRow = false;
      setTimeout(() => {
        this.textarea.nativeElement.focus();
      }, 0);
      return;
    }
    if (this.isSingleRow) {
      inputEl = this.singleInput.nativeElement;
      inputWidth = inputEl.offsetWidth;
      contentWidth = this.measureTextWidth(inputEl.value, inputEl);

    } else {
      inputEl = this.textarea.nativeElement;
      inputWidth = inputEl.offsetWidth;
      contentWidth = this.measureTextWidth(inputEl.value, inputEl) + 95;
    }

    let singleWidth = contentWidth <= inputWidth;


    this.isSingleRow = !this.showConvertAudio &&
      singleWidth &&
      !this.recording &&
      this.uploadData.length === 0 &&
      !this.isRuntime;

    if (!this.isSingleRow) {
      setTimeout(() => {
        this.textarea.nativeElement.focus();
      }, 0);
    } else {
      setTimeout(() => {
        this.singleInput.nativeElement.focus();
      }, 0);
    }
  }

  // 测量文本宽度
  measureTextWidth(text: string, inputEl: HTMLInputElement): number {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return 0;

    // 设置与 input 相同的字体样式
    const font = window.getComputedStyle(inputEl).font;
    context.font = font;

    return context.measureText(text).width;
  }



}
