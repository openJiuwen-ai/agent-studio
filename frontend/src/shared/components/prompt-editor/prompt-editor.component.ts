import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { PromptEditorService } from '@services/prompt-editor.service';
import { MODULES } from '@shared/modules';
import { ClipboardModule } from '@angular/cdk/clipboard';
import { IPromptChunk, IVariant } from '@interfaces/prompt/prompt-editor.interface';
import { I18nNamespace } from '@i18n';
import * as I18next from 'angular-i18next';
import { EChunkType, EConfirmBtnStatus } from '@enums/prompt-editor.enum';
import { Subject, filter, fromEvent, takeUntil, throttleTime, from, mergeMap, tap, catchError, of, finalize } from 'rxjs';
import {
  EDITOR_BORDER_FOCUS_STYLE,
  EDITOR_BORDER_STYLE,
  MAX_VAR_NUM,
  GETVARIANT_REG,
  CHECKVARIABLENAME_REG,
  EDITOR_BG_CONFIRM_COLOR,
  EDITOR_BG_COLOR,
  SNIPPET_REG,
  EDITOR_BORDER_ERROR_STYLE,
  VARIANT_NAME_ERROR_POS,
  EDITOR_BG_ERROR_COLOR,
  TEMPLATENAME_REG,
} from '@constants/exp-tmpl-config.const';
import { NzPopconfirmModule } from 'ng-zorro-antd/popconfirm';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { Validators } from '@angular/forms';

interface TiValidationConfig {
  type: string;
}
import { cloneDeep, isNil } from 'lodash';
import { MessageComponent } from '@shared/services/cfdata.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ModelService } from '@services/model.service';
import { FormBuilder, FormControl, FormGroup } from '@angular/forms';
import { RouteParamsService } from '@services/routeParams.service';
import { CommonValidation } from '@shared/validation/commonValidation';
import { PromptWritingService } from '@services/prompt-writing.service';
import { ECandSaveType, EWritingStatus } from '@enums/prompt-writing.enum';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import { CommonUtils } from 'src/utils/common.util';
import { TmplVariantTagComponent } from '../tmpl-variant-tag/tmpl-variant-tag.component';
import { TmplSnippetComponent } from '../tmpl-snippet/tmpl-snippet.component';
import { v4 as uuidV4 } from 'uuid';
import { PromptWritingRepoService } from '@services/repositories/prompt-writing-repo.service';
import { FileItem } from '@interfaces/prompt/prompt-editor.interface';

@Component({
  selector: 'prompt-editor',
  templateUrl: './prompt-editor.component.html',
  standalone: true,
  styleUrls: ['./prompt-editor.component.less'],
  imports: [MODULES, TmplVariantTagComponent, TmplSnippetComponent, ClipboardModule, NzPopconfirmModule, NzIconModule, NzToolTipModule],
  providers: [
    {
      provide: I18next.I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.PROMPT_PLATFORM],
    },
  ],
})
export class PromptEditorComponent implements AfterViewInit, OnInit, OnDestroy, OnChanges {
  @Input() taskId: string;

  @Input() candidateId?: string;

  @Input() defaultCandTitle: string;

  @Output() isExistErrorTips = new EventEmitter<boolean>();

  public value = '';

  public promptChunks: IPromptChunk[] = [];

  public isConfirmVisible: EConfirmBtnStatus = EConfirmBtnStatus.CONFIRMHIDDEN;

  public varPool: IVariant[] = [];

  public newVarPop = {
    content: this.i18n.transform('writing_var_ref_exceed'),
    key: '',
  };

  public isFocus = false;

  public editorBorderStyle = EDITOR_BORDER_STYLE;

  public isOnConfirm = false;

  public isInputError = false;

  // 光标位置
  public selectionStart = 0;

  public uniqueFailToVerify = [];

  public candidateformName: FormGroup<{
    candidateNameInput: FormControl<string | null>;
  }>;

  public isEditCandidateName = false;

  public isEditorDisabled = false;

  public validation: TiValidationConfig = {
    type: 'changeAlert',
  };

  public validationRules = [CommonValidation.templateNameVerify(this.i18n.transform('')), Validators.required];

  public isDefaultTitle = false;

  /** 用于判断当前是否在输入法编辑器中进行输入 */
  private isComposition = false;

  private destroy$ = new Subject<void>();

  private confirmPromptChunks: IPromptChunk[] = [];

  /** 是否点击了取消按钮 */
  private isClickCancel = false;

  @ViewChild('textarea') textarea: ElementRef<HTMLTextAreaElement>;

  @ViewChild('styledContent') styledContent: ElementRef<HTMLDivElement>;

  public fileAccept = '.png,.jpg,.jpeg,.gif,.webp';

  isNameEditor = false;
  nameEditorValue = '';
  constructor(
    private promptEditorService: PromptEditorService,
    private promptWritingServ: PromptWritingService,
    private i18n: I18next.I18NextEagerPipe,
    private changeDetector: ChangeDetectorRef,
    private modelServ: ModelService,
    private fb: FormBuilder,
    private routeParamsServe: RouteParamsService,
    private candidateTemplateListServe: CandidateTemplateListService,
    private promptWritingRepoServ: PromptWritingRepoService
  ) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.defaultCandTitle && this.isDefaultTitle) {
      this.candidateformName = this.buildForm(changes.defaultCandTitle.currentValue as string);
    }
    this.onCancel();
  }

  ngOnInit(): void {
    this.subEditSingleTmplUpdate();
    this.subPromptUpdate();
    this.subVarPoolUpdate();
    this.subCursorPosUpdate();
    this.subWritingStateUpdate();
    this.subConfirmBtnStateUpdate();
    this.subTmplPromptUpdate();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  ngAfterViewInit(): void {
    /**
     * 节流时间若超过 100ms 会导致：
     * 当用户输入 {{ 后立马按回车时，同时触发选择变量和正常的回车事件
     */
    fromEvent(this.textarea.nativeElement, 'keydown')
      .pipe(throttleTime(100))
      .subscribe((event: Event) => {
        const keyboardEvent = event as KeyboardEvent;

        if (['ArrowUp', 'ArrowDown', 'Enter'].includes(keyboardEvent.key)) {
          this.onSelectVar(keyboardEvent);
        }
      });

    if (this.uniqueFailToVerify.length > 0) {
      this.editorBorderStyle = EDITOR_BORDER_ERROR_STYLE;
    } else {
      this.editorBorderStyle = EDITOR_BORDER_FOCUS_STYLE;
    }
    this.changeDetector.detectChanges();
  }

  public changeUrl = cdnAssetUrl;

  public subTmplPromptUpdate(): void {
    this.promptEditorService
      .tmplPromptUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async tmplPrompt => {
        if (tmplPrompt.file?.fileId) {
          this.uploadData = [tmplPrompt.file];
          this.promptEditorService.setFileId(this.uploadData[0]?.fileId);
        } else {
          this.uploadData = [];
          this.promptEditorService.setFileId('');
        }
      });
  }

  public subEditSingleTmplUpdate(): void {
    this.routeParamsServe.editSingleTmplUpdate$().subscribe(variants => {
      if (variants && variants.split(';').length > 1) {
        this.isDefaultTitle = false;
        const info = variants.split(';');

        // 如果信息有3种，说明携带了临时变更信息，不予应用本次更新
        if (info.length < 3) {
          /**
           * variants.split(';')[0] 为打分的星星数，
           * variants.split(';')[1] 为候选名称
           */
          const title = info[1];
          this.candidateformName = this.buildForm(title);
        }
      } else {
        this.isDefaultTitle = true;
        this.candidateformName = this.buildForm(this.defaultCandTitle);
      }
    });
  }

  public subPromptUpdate(): void {
    this.promptEditorService
      .promptUpdate$()
      .pipe(
        filter(incoming => incoming !== this.value),
        takeUntil(this.destroy$)
      )
      .subscribe(prompt => {
        this.value = prompt;
        if (this.promptEditorService.getTmplPrompt().file?.fileId) {
          this.uploadData = [this.promptEditorService.getTmplPrompt().file];
          this.promptEditorService.setFileId(this.uploadData[0]?.fileId);
        }
        this.promptChunks = this.getChunksEndWithNewLine(this.value, this.promptEditorService.processVar(this.value, true, false));
        if (prompt === '') {
          /** 点击新的撰写按钮，恢复正常编辑态 */
          this.restoreInputState();
          this.isClickCancel = true;
        }
      });
  }

  public subVarPoolUpdate(): void {
    this.promptEditorService
      .varPoolUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(varPool => {
        this.varPool = varPool;
      });
  }

  /** 监听选中变量后光标位置的变化 */
  public subCursorPosUpdate(): void {
    this.promptEditorService
      .selectionStartUpdate$()
      .pipe(
        filter(index => index !== this.selectionStart),
        takeUntil(this.destroy$)
      )
      .subscribe(index => {
        this.textarea?.nativeElement.focus();
        setTimeout(() => {
          // 更新在变量提示面板中变量选中后光标的位置
          this.textarea?.nativeElement.setSelectionRange(index, index);
        }, 0);
      });
  }

  public subWritingStateUpdate(): void {
    this.promptWritingServ
      .currCmpStateUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        this.isEditorDisabled = this.getEditorDisabledState(state);
      });
  }

  public subConfirmBtnStateUpdate(): void {
    this.promptEditorService
      .confirmBtnStateUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(state => {
        if (state) {
          this.isConfirmVisible = state;
        }
      });
  }

  public onInput(event: Event): void {
    this.promptEditorService.setTextareaValue((event.target as HTMLInputElement).value);
    this.promptEditorService.setPrompt(this.value);
    this.isConfirmVisible = EConfirmBtnStatus.CONFIRMVISIBLE_WITHPOP;

    if (!this.isComposition) {
      /** 当前光标的位置 */
      this.selectionStart = (event.target as HTMLTextAreaElement).selectionStart;

      this.promptEditorService.setSelectionStart(this.selectionStart);

      const pre = this.value.slice(0, this.selectionStart);
      const next = this.value.slice(this.selectionStart);

      if (next !== '' && this.isInputInTheMidOfVar(pre, next)) {
        this.promptChunks = this.getChunksEndWithNewLine(this.value, this.promptEditorService.processVar(this.value, true, false));
        this.promptChunks = this.illegalVarsRed(this.confirmPromptChunks, this.promptChunks);
      } else {
        /**
         * 将 prompt 从光标处拆分为两部分处理,
         * 前一部分为该 prompt 从下标 0 到当前输入位置, 可能会触发 SNIPPET
         * 后一部分在上一次变更后已渲染处理，只包含 COMMON 与 VARIANT
         */
        let chunks: IPromptChunk[] = [];
        if (next === '') {
          chunks = this.promptEditorService.processPrompt(pre);
        } else {
          chunks = this.promptEditorService.processPrompt(pre).concat(this.promptEditorService.processVar(next, true, false));
        }
        if (!this.isClickCancel) {
          chunks = this.illegalVarsRed(this.confirmPromptChunks, chunks);
        }
        /**
         * 如果最后一个字符为换行符，渲染时需要追加一个空格字符将换行符的高度撑开
         * 否则在出现滚动条的 textarea 的最后一行输入换行符会导致 textarea
         * 和 styledContent 的高度不一致
         */
        this.promptChunks = this.getChunksEndWithNewLine(this.value, chunks);
      }
      /** 如果输入变量非法，再次修改时视作正常编辑状态。 */
      this.restoreInputState();
    }
  }

  /**
   * 若有多个非法变量，用户修改其中一个，其他非法变量仍保持红色
   * 用户修改后，则视作未定义变量
   */
  public illegalVarsRed(confirmPromptChunks: IPromptChunk[], promptChunks: IPromptChunk[]): IPromptChunk[] {
    const updatePromptChunks = promptChunks.slice();

    confirmPromptChunks.forEach((confirmInput: IPromptChunk) => {
      if (confirmInput.pos === VARIANT_NAME_ERROR_POS) {
        const idx = promptChunks.findIndex(item => item.type === confirmInput.type && item.value === confirmInput.value);

        if (idx !== -1) {
          updatePromptChunks[idx] = {
            ...updatePromptChunks[idx],
            pos: VARIANT_NAME_ERROR_POS,
          };
        }
      }
    });
    return updatePromptChunks;
  }

  public onCompositionstart(): void {
    this.isComposition = true;
  }

  /**
   * 当使用输入法编辑器(例如拼音输入) 输入时, 双向绑定
   * 的 value 并不会更新, 只有在选中输入的值时(即触发
   * compositionend 事件) 才会进行更新, 所以此处需要
   * 手动更新该值到 prompt 渲染器中
   */
  public onCompositionupdate(event: CompositionEvent): void {
    this.selectionStart = (event.target as HTMLTextAreaElement).selectionStart;
    this.promptEditorService.setSelectionStart(this.selectionStart);

    const prompt = this.promptEditorService.insertString(this.value, event.data, this.selectionStart);

    this.promptChunks = this.promptEditorService.processPrompt(prompt);
  }

  public onCompositionend(): void {
    this.isComposition = false;
  }

  /** 当有变量输入提示时，阻止默认的方向上下键和 enter 键的行为 */
  public onSelectVar(event: KeyboardEvent): void {
    if (!this.promptChunks.length) {
      return;
    }

    // 没有出现变量选择列表overlay时不阻止键盘默认事件
    // 以光标前一段prompt中最后一个块来判断是否为snippet
    const lastChunk = this.promptEditorService.processPrompt(this.value.slice(0, this.promptEditorService.getSelectionStart())).pop();

    if (lastChunk.type === EChunkType.SNIPPET && this.promptEditorService.getCandidates(lastChunk.value).length) {
      event.preventDefault();
    }
  }

  public onConfirm(): void {
    this.isClickCancel = false;
    const variants = this.getVarsOnEditor();

    /** 将 variants 去重 */
    const uniqueVars = CommonUtils.getUniqueVars(variants);

    /** 计算新增变量数 */
    const newVars = this.countNewVarNums(uniqueVars);

    if (newVars.length > 0) {
      this.isOnConfirm = true;

      /** 检查是否超出最大变量定义范围 */
      if (this.isOutOfVarDefRange(uniqueVars)) {
        this.isExistErrorTips.emit(false);
        this.newVarPop = {
          key: 'error',
          content: this.i18n.transform('writing_var_ref_exceed'),
        };
      } else {
        // 变量命名的正则表达（第6条）
        const regex = new RegExp(CHECKVARIABLENAME_REG);
        const variables = this.processPromptVar(this.value);
        const failToVerify = [];
        variables.forEach(item => {
          if (!regex.test(item.name)) {
            failToVerify.push(item.key);
          }
        });
        this.uniqueFailToVerify = [...new Set(failToVerify)];
        if (this.uniqueFailToVerify.length > 0) {
          this.isExistErrorTips.emit(true);
          this.editorBorderStyle = EDITOR_BORDER_ERROR_STYLE;
          this.isOnConfirm = false;
          this.isInputError = true;
          this.isConfirmVisible = EConfirmBtnStatus.CONFIRMVISIBLE_WITHOUTPOP;
        } else {
          this.restoreCancelState();
          this.newVarPop = {
            key: 'confirm',
            content: `${this.i18n.transform('writing_var_def_new_pre')} ${newVars.length} ${this.i18n.transform('writing_var_def_new_suff')}`,
          };

          this.promptEditorService.setPrompt(this.value);
        }
      }
    } else {
      /** 没有新增变量, 将prompt同步到调优面板 */
      this.promptEditorService.setTmplPrompt({
        prompt: this.value,
        variants: uniqueVars,
        file: this.uploadData[0],
      });
      this.restoreCancelState();
      this.isConfirmVisible = EConfirmBtnStatus.CONFIRMHIDDEN;

      this.promptEditorService.setPrompt(this.value);
    }
    if (this.uploadData.length) {
      this.promptEditorService.setFileId(this.uploadData[0]?.fileId);
    } else {
      this.promptEditorService.setFileId('');
    }
  }

  popConfirm() {
    if (this.newVarPop.key === 'error') {
      this.isOnConfirm = false;
    } else {
      const variants = this.getVarsOnEditor();
      /** 将 variants 去重 */
      const uniqueVars = CommonUtils.getUniqueVars(variants);
      /** 计算新增变量数 */
      const newVars = this.countNewVarNums(uniqueVars);
      /** unique variants 写入 varPool 中 */
      this.promptEditorService.addVars2VarPool(newVars);

      /** 之前未定义的变量此时已定义，重新渲染变量背景色 */
      this.promptChunks = this.getChunksEndWithNewLine(this.value, this.promptEditorService.processVar(this.value));

      const preScrollTop = this.textarea.nativeElement.scrollTop;
      // 重新渲染后需要将内容滚动高度恢复到点击确定前的位置
      setTimeout(() => {
        this.styledContent.nativeElement.scrollTop = preScrollTop;
      }, 0);

      /** 同步到调优面板 */
      this.promptEditorService.setTmplPrompt({
        prompt: this.value,
        variants: uniqueVars,
        file: this.uploadData[0],
      });
      this.isConfirmVisible = EConfirmBtnStatus.CONFIRMHIDDEN;
      this.isOnConfirm = false;
    }
  }

  popCancel() {
    this.isOnConfirm = false;
  }

  /** 为了避免uniqueVars检查变量不全，直接处理Prompt文本 */
  public processPromptVar(input: string): IVariant[] {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map(match => ({
        key: match,
        value: '',
        name: match.slice(2, -2),
      }));
      return extractedValues;
    }
    return [];
  }

  public onCancel(): void {
    this.value = this.promptEditorService.getPrePrompt();
    this.promptEditorService.setPrompt(this.value);
    this.promptChunks = this.getChunksEndWithNewLine(this.value, this.promptEditorService.processVar(this.value, true, false));
    this.restoreCancelState();
    this.isConfirmVisible = EConfirmBtnStatus.CONFIRMHIDDEN;
    this.isClickCancel = true;
  }

  public onFocus(): void {
    this.isFocus = true;
    if (this.uniqueFailToVerify.length > 0) {
      this.editorBorderStyle = EDITOR_BORDER_ERROR_STYLE;
    } else {
      this.editorBorderStyle = EDITOR_BORDER_FOCUS_STYLE;
    }
  }

  public onBlur(): void {
    this.isFocus = false;
    if (this.uniqueFailToVerify.length > 0) {
      this.editorBorderStyle = EDITOR_BORDER_ERROR_STYLE;
    } else {
      this.editorBorderStyle = EDITOR_BORDER_STYLE;
    }
  }

  /** styledContent 需要随着 textarea 一起滚动 */
  public onScroll(event: Event): void {
    if (event.target === this.textarea.nativeElement) {
      this.styledContent.nativeElement.scrollTop = (event.target as HTMLTextAreaElement).scrollTop;
    }
  }

  public onCopy(): void {
    MessageComponent.showSuccess(this.i18n.transform('base_copy'));
  }

  public onClear(): void {
    this.promptEditorService.initWriting();
    this.modelServ.initParam();
    this.clearFile();
  }

  public getBGColor(): string {
    if (this.isInputError) {
      return EDITOR_BG_ERROR_COLOR;
    }
    return this.isOnConfirm ? EDITOR_BG_CONFIRM_COLOR : EDITOR_BG_COLOR;
  }

  public setDiffHeight(): string {
    return this.uniqueFailToVerify.length > 0 ? 'calc(100% - 24px)' : '100%';
  }

  public onChangeCandNameConfirm(): void {
    const startAndName = this.routeParamsServe.getEditSingleTmpl();
    const name = this.candidateformName.value.candidateNameInput;
    let star = '0';

    if (startAndName) {
      const startAndNameArr = startAndName.split(';');
      this.routeParamsServe.setEditSingleTmpl(`${startAndNameArr[0]};${name}`);
      star = startAndNameArr[0];
    } else {
      this.routeParamsServe.setEditSingleTmpl(`0;${name}`);
    }

    // 如果在非writing情况下编辑, 则保存这次编辑
    if (this.promptWritingServ.getCurrCmpState() !== EWritingStatus.WRITING) {
      this.candidateTemplateListServe
        .updateCandidateTmplTitle({
          id: this.candidateId,
          manual_score: star,
          name,
        })
        .subscribe({
          next: () => {
            MessageComponent.showSuccess(this.i18n.transform('base_edit_success'));

            // 刷新菜单
            this.promptWritingServ.setCandChangeInfo({
              type: ECandSaveType.SAVE,
            });
          },
        });
    }
  }

  public cancelTitleChange(): void {
    this.candidateformName.controls.candidateNameInput.setValue(this.nameEditorValue);
    this.closeValidateMsgCmp();
  }

  public onEditTitle(event: Event): void {
    if (!TEMPLATENAME_REG.test((event.target as HTMLInputElement).value)) {
      // 如果修改的名称不符合正则，则提示
      MessageComponent.showError(this.i18n.transform('prompt_writing_verifyNameInput'), 3000);
    } else {
      // 通过校验，如果有校验不通过的弹窗，需要关闭
      this.closeValidateMsgCmp();
    }
  }

  /** 计算新增变量 */
  private countNewVarNums(variants: IVariant[]): IVariant[] {
    const newVars: IVariant[] = [];

    variants.forEach(variant => {
      if (!this.varPool.map(v => v.key).includes(variant.key)) {
        newVars.push(variant);
      }
    });

    return newVars;
  }

  /** 获取当前编辑内容中的变量 */
  private getVarsOnEditor(): IVariant[] {
    this.promptChunks = this.getChunksEndWithNewLine(this.value, this.promptEditorService.processVar(this.value, false, true));
    this.confirmPromptChunks = this.promptChunks;

    return this.promptChunks
      .filter(chunk => chunk.type === EChunkType.VARIANT)
      .map(chunk => {
        const preVal = this.varPool.find(v => v.key === chunk.value);

        return {
          key: chunk.value,
          value: preVal?.value ?? '',
          name: preVal?.name ?? chunk.value.replace(/{{|}}/g, ''),
        };
      });
  }

  /** 检查新增变量是否超出变量定义范围
   * 1. 编辑器中的变量不能超过 20 个
   * 2. 新增变量 + 全局变量不能超过 20 个
   */
  private isOutOfVarDefRange(editorVars: IVariant[]): boolean {
    return editorVars.length > MAX_VAR_NUM || CommonUtils.getUniqueVars(editorVars.concat(this.promptEditorService.getGlobalVars())).length > MAX_VAR_NUM;
  }

  private isInputInTheMidOfVar(pre: string, next: string): boolean {
    const preMatch = pre.match(SNIPPET_REG);
    const nextMatch = (next.length > 1 && next.startsWith('}}')) || (next.length > 0 && next.startsWith('}'));

    return preMatch && nextMatch;
  }

  /** 若给出的prompt以换行符结尾，需要在chunks最后追加一个空格chunk */
  private getChunksEndWithNewLine(prompt: string, chunks: IPromptChunk[]): IPromptChunk[] {
    const chunksCopy = cloneDeep(chunks);

    if (prompt.endsWith('\n')) {
      chunksCopy.push({
        type: EChunkType.COMMON,
        value: ' ',
      });
    }

    return chunksCopy;
  }

  private inputAndCancelCommonState() {
    this.isInputError = false;
    this.uniqueFailToVerify = [];
    this.isExistErrorTips.emit(false);
  }

  /** 编辑状态：去除border、background和errorTips，边框为篮色 */
  private restoreInputState() {
    this.inputAndCancelCommonState();
    this.editorBorderStyle = EDITOR_BORDER_FOCUS_STYLE;
  }

  /** 取消状态：边框为灰色 */
  private restoreCancelState() {
    this.inputAndCancelCommonState();
    this.editorBorderStyle = EDITOR_BORDER_STYLE;
  }

  private buildForm(name: string): FormGroup {
    return this.fb.group({
      candidateNameInput: new FormControl(name, [CommonValidation.templateNameVerify(this.i18n.transform('prompt_writing_verifyNameInput'))]),
    });
  }

  private getEditorDisabledState(state: EWritingStatus): boolean {
    return state === EWritingStatus.RCANDIDATE;
  }

  private closeValidateMsgCmp(): void {
    const errorMsgIcon = document.querySelector('.cf-message-close.hwsicon-frame-image-close');

    if (errorMsgIcon) {
      (errorMsgIcon as HTMLSpanElement).click();
    }
  }

  public uploadData: FileItem[] = [];

  public uploading = false;

  @ViewChild('fileInput') fileInput: ElementRef<HTMLInputElement>;

  public initFile() {
    this.uploadData = [];
    this.promptEditorService.setFileId('');
    const tmplPrompt = this.promptEditorService.getTmplPrompt();
    this.promptEditorService.setTmplPrompt({
      ...tmplPrompt,
      file: null,
    });
  }

  public clearFile() {
    this.initFile();
  }

  public uploadFile() {
    if (this.isEditorDisabled) {
      return;
    }
    this.fileInput.nativeElement.click();
    this.isConfirmVisible = EConfirmBtnStatus.CONFIRMVISIBLE_WITHPOP;
  }

  public onUploadFile(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = input.files;
    const len = files?.length;
    if (len <= 0) {
      return;
    }
    if (len + this.uploadData.length > 20) {
      MessageComponent.showWarn(this.i18n.transform('upload_max_files_tip'));
      return;
    }
    this.uploading = true;
    const fileArray = Array.from(files);
    const validFiles: FileItem[] = fileArray.flatMap(file => {
      const ext = file.name.split('.').pop()?.toLowerCase() || '';
      const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg'].includes(ext);
      const limit = 1024 * 1024 * 5;

      if (!isImage) {
        MessageComponent.showWarn(this.i18n.transform(this.i18n.transform('prompteditorcomponent_67')));
        return [];
      }

      if (file.size > limit) {
        MessageComponent.showWarn(this.i18n.transform('image_size_cannot_exceed_5mb'));
        return [];
      }

      return [
        {
          progress: 'loading',
          type: isImage ? 'image' : 'file',
          name: file.name,
          url: '',
          file_id: '',
          file,
          isImage,
          fileId: uuidV4(),
          controller: new AbortController(),
        },
      ];
    });
    this.uploadData = validFiles;
    from(validFiles)
      .pipe(
        takeUntil(this.destroy$),
        mergeMap(item => {
          const { file, isImage, controller } = item;
          const formData = new FormData();
          formData.append('file', file);
          formData.append('is_image', JSON.stringify(isImage));
          return from(this.promptWritingRepoServ.uploadFile(formData, controller.signal)).pipe(
            tap(res => {
              item.progress = 'succeeded';
              item.url = res.tempUrl;
              item.fileId = res.file_id;
              this.isConfirmVisible = EConfirmBtnStatus.CONFIRMVISIBLE_WITHPOP;
            }),
            catchError(() => {
              item.progress = 'failed';
              return of(null);
            })
          );
        }, 5),
        finalize(() => {
          this.uploading = false;
          input.value = '';
        })
      )
      .subscribe();
  }

  editName() {
    this.isNameEditor = true;
    this.nameEditorValue = this.candidateformName.controls.candidateNameInput.value;
  }
}
