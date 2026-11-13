import { ChangeDetectionStrategy, ChangeDetectorRef, Component, EventEmitter, Input, Output, SimpleChanges } from '@angular/core';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { MODULES } from '@shared/modules';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { ImportModalComponent } from '@routes/prompt/prompt-optimize-task-config/use-cases/import-modal/import-modal.component';
import { OptimizeUseCase, PromptType, VariableType } from '@interfaces/prompt/prompt-optimize-task.interface';
import { PromptOptimizeService, UseCaseService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import { I18nNamespace } from '@i18n';
import { CommonUtils } from 'src/utils/common.util';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'meta-use-cases',
  standalone: true,
  imports: [I18NextModule, MODULES],
  templateUrl: './use-cases.component.html',
  styleUrls: ['./use-cases.component.scss', '../../share/styles/common-styles.less'],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UseCasesComponent {
  @Input() taskId: string;
  @Input() variables: Array<{ type: VariableType; value: string }>;
  @Input() useCases: Array<any> = [];
  @Input() pageInfo: { page: number; pageSize: number; total: number };
  @Input() promptType: PromptType = PromptType.TEXT;
  @Output() uploadOneItem = new EventEmitter<OptimizeUseCase>();
  @Output() updateOneItem = new EventEmitter<OptimizeUseCase>();
  @Output() deleteOneItem = new EventEmitter<string>();
  @Output() importByFile = new EventEmitter<File>();
  @Output() pageChange = new EventEmitter<{ page: number; pageSize: number }>();

  public changeUrl = cdnAssetUrl;
  displayedData: Array<any> = [];
  useCasesData: { data: any[]; state?: any } = {
    data: [],
  };
  columns: Array<{ title: string; width?: string; fixed?: string }> = [
    {
      title: this.i18n.transform('base_number'),
      width: '100px',
    },
    {
      title: this.i18n.transform('expected_output'),
      width: '360px',
    },
    {
      title: this.i18n.transform('operation'),
      fixed: 'right',
      width: '150px',
    },
  ];
  pageSize: { options: Array<number>; size: number } = {
    options: [10, 20, 50, 100],
    size: 10,
  };
  currentPage: number = 2;
  totalNumber: number = 0;
  _isEditing: boolean = false;
  private observer: MutationObserver | null = null;

  constructor(
    private useCaseService: UseCaseService,
    private nzModal: NzModalService,
    private promptOptimizeService: PromptOptimizeService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private message: NzMessageService
  ) {}

  ngOnChanges(changes: SimpleChanges) {
    if (changes.variables) {
      const variablesColumns = this.variables.map((item, index) => {
        if (item.type === 'image') {
          return {
            title: `{{${item.value}}}`,
            width: '160px',
          };
        } else {
          return {
            title: `{{${item.value}}}`,
            width: '240px',
          };
        }
      });
      this.columns = [
        {
          title: this.i18n.transform('base_number'),
          width: '100px',
        },
        ...variablesColumns,
        {
          title: this.i18n.transform('expected_output'),
          width: '360px',
        },
        {
          title: this.i18n.transform('operation'),
          fixed: 'right',
          width: '150px',
        },
      ];
    }
    if (changes.useCases) {
      const base_id = this.pageInfo.pageSize * (this.pageInfo.page - 1);
      this.useCasesData.data = this.useCases.map((useCase, index) => {
        const useCaseData: any = {
          isEdit: false,
          disabled: false,
          editState: '',
          id: base_id + index + 1,
          useCaseId: useCase.id,
          expectedOutput: useCase.content.AGENT_BUILDER_PROMPT_OUTPUT,
          variables: useCase.content,
          images: {},
        };
        useCaseData.action = this.dataToItemsFn(useCase);
        return useCaseData;
      });
    }
    if (changes.pageInfo) {
      this.pageSize.size = this.pageInfo.pageSize;
      this.currentPage = this.pageInfo.page;
      this.totalNumber = this.pageInfo.total;
    }
    this.cdr.markForCheck();
  }

  ngAfterViewInit() {
    // 注册图片加载失败监听
    this.initImageErrorFix();
  }

  /**
   * 初始化图片加载失败自动修复逻辑
   */
  private initImageErrorFix(): void {
    this.observer = new MutationObserver(mutationsList => {
      for (const mutation of mutationsList) {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === node.ELEMENT_NODE) {
              let imgList = (node as Element).querySelectorAll('.ti3-picture-card-item-img');
              imgList.forEach(img => this.handleImageError(img as HTMLImageElement, 'assets/prompt/err-img-1.png'));
              imgList = (node as Element).querySelectorAll('.ti3-image-preview-container>img');
              imgList.forEach(img => this.handleImageError(img as HTMLImageElement, 'assets/prompt/err-img.svg'));
            }
          });
        }
      }
    });

    // 开始观察整个文档（包括子元素）
    this.observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  ngOnDestroy() {
    this.observer?.disconnect();
  }

  /**
   * 处理单个图片的 onerror 逻辑
   */
  private handleImageError(img: HTMLImageElement, errEmgUrl: string = 'assets/prompt/err-img-1.png'): void {
    // 避免重复绑定
    if (img.dataset.imgErrorBound === 'true') {
      return;
    }
    img.dataset.imgErrorBound = 'true';

    img.onerror = () => {
      // 设置失败占位图
      img.src = this.changeUrl(errEmgUrl);
      img.classList.add('error');
    };

    // 如果已有 src，尝试触发一次加载检测
    if (img.src) {
      const tempImg = new Image();
      tempImg.onload = () => {
        // 加载成功，不处理
      };
      tempImg.onerror = () => {
        // 加载失败，触发 onerror
        const event = new Event('error');
        img.onerror(event);
      };
      tempImg.src = img.src;
    }
  }

  get isEditing(): boolean {
    return this._isEditing;
  }

  set isEditing(value: boolean) {
    this._isEditing = value;
    if (value) {
      this.useCasesData.data.forEach(item => {
        item.disabled = !item.isEdit;
      });
    } else {
      this.useCasesData.data.forEach(item => {
        item.disabled = value;
      });
    }
  }
  public lang: string = CommonUtils.getLanguage();
  get separator() {
    return this.lang === 'zh-cn' ? '，' : ', ';
  }
  dataToItemsFn: (data: any) => Array<{ id: string; label: string; disabled?: boolean; tip?: string }> = (data: any) => {
    let items: Array<{ id: string; label: string; disabled?: boolean; tip?: string }> = [];
    if (data.isEdit) {
      const emptyVariables = this.validateEdit(data);
      items.push(
        {
          id: 'cancel',
          label: this.i18n.transform('cancel'),
        },
        {
          id: 'save',
          label: this.i18n.transform('save'),
          disabled: emptyVariables.length > 0,
          tip: emptyVariables.length > 0 ? `${emptyVariables.join(this.separator)} ${this.i18n.transform('use_case_1')}` : '',
        }
      );
    } else if (!data.isEdit) {
      items.push(
        {
          id: 'del',
          label: this.i18n.transform('delete'),
          disabled: data.disabled,
          tip: data.disabled ? this.i18n.transform('save_or_cancel_modified_row') : '',
        },
        {
          id: 'edit',
          label: this.i18n.transform('edit1'),
          disabled: data.disabled,
          tip: data.disabled ? this.i18n.transform('save_or_cancel_modified_row') : '',
        }
      );
    }
    return items;
  };

  onSelect(action: { id: string; label: string }, useCase: any): void {
    if (action.id === 'cancel') {
      this.cancelRow(useCase);
    } else if (action.id === 'save') {
      this.saveRow(useCase);
    } else if (action.id === 'del') {
      this.delRow(useCase);
    } else if (action.id === 'edit') {
      this.editRow(useCase);
    } else {
      // do nth
    }
  }

  addOneRow() {
    this.useCasesData.data.unshift({
      isEdit: true,
      disabled: false,
      editState: 'add',
      id: '',
      expectedOutput: '',
      variables: {},
      images: {},
    });
    this.isEditing = true;
    this.updateActionState();
  }

  editRow(rowData: any) {
    this.isEditing = true;
    rowData.isEdit = true;
    rowData.editState = 'update';
    rowData.backData = JSON.parse(JSON.stringify(rowData));
    this.updateActionState();
  }

  delRow(rowData: any) {
    const index = this.useCasesData.data.indexOf(rowData);
    this.useCasesData.data.splice(index, 1);
    this.deleteOneItem.emit(rowData.useCaseId);
    this.isEditing = false;
  }

  async saveRow(rowData: any) {
    const emptyVariables = this.validateEdit(rowData);
    if (emptyVariables.length > 0) {
      this.updateActionState();
      return;
    }
    for (const variable of this.variables) {
      if (variable.type === 'image') {
        if (rowData.images[variable.value]) {
          rowData.variables[variable.value] = await this.uploadImage(rowData.images[variable.value]);
        }
      }
    }
    rowData.isEdit = false;
    delete rowData.backData;
    this.isEditing = false;
    if (rowData.editState === 'add') {
      this.uploadOneUseCase(rowData);
    } else {
      this.updateOneUseCase(rowData);
    }
  }

  public updateActionState() {
    this.useCasesData.data.forEach(item => {
      item.action = this.dataToItemsFn(item);
    });
    this.cdr.detectChanges();
  }

  private validateEdit(rowData: any) {
    const emptyVariables = [];
    for (const variable of this.variables) {
      if (variable.type === 'image') {
        if (!rowData.images[variable.value] && !rowData.variables[variable.value]) {
          // 图片变量没有上传图片也没有历史图片
          emptyVariables.push(variable.value);
        }
      } else {
        if (!rowData.variables[variable.value]) {
          // 文本变量没有填写内容
          emptyVariables.push(variable.value);
        }
      }
    }
    if (rowData.expectedOutput === '' || rowData.expectedOutput === undefined) {
      emptyVariables.push(this.i18n.transform('expected_output'));
    }
    return emptyVariables;
  }

  cancelRow(rowData: any) {
    if (rowData.editState === 'add') {
      this.useCasesData.data = this.useCasesData.data.filter(item => item.id !== rowData.id);
    } else if (rowData.editState === 'update') {
      // 使用备份数据还原更改
      Object.keys(rowData.backData).forEach(key => {
        rowData[key] = rowData.backData[key];
      });
      rowData.isEdit = false;
      delete rowData.backData;
    }

    this.isEditing = false;
    this.updateActionState();
  }

  openImportModal() {
    const thisNzModal: any = this.nzModal.create({
      nzTitle: 'importUseCasesModal',
      nzContent: ImportModalComponent,
      nzOnOk: (): void => {
        this.useCaseService.pushErrorMessages(''); // 清空错误信息
      },
      nzOnCancel: (): void => {
        this.useCaseService.pushErrorMessages(''); // 清空错误信息
        thisNzModal.destroy();
      },
    });
    const instance = thisNzModal.getContentComponent();
    instance.promptType = this.promptType;
    instance.importUseCases.subscribe((fileItem: any) => {
      this.importByFile.emit(fileItem._file);
    });
  }

  public uploadOneUseCase(rowData: any) {
    const data = this.variables.map(variable => {
      return {
        name: variable.value,
        type: variable.type === 'text' ? 'text' : 'multi',
        content: rowData.variables[variable.value] ?? '',
      };
    });
    const useCase: OptimizeUseCase = {
      content: JSON.stringify([
        ...data,
        {
          name: 'AGENT_BUILDER_PROMPT_OUTPUT',
          type: 'text',
          content: rowData.expectedOutput ?? '',
        },
      ]),
    };
    this.uploadOneItem.emit(useCase);
  }

  public updateOneUseCase(rowData: any) {
    const data = this.variables.map(variable => {
      return {
        name: variable.value,
        type: variable.type === 'text' ? 'text' : 'multi',
        content: rowData.variables[variable.value] ?? '',
      };
    });
    const useCase: OptimizeUseCase = {
      id: rowData.useCaseId,
      content: JSON.stringify([
        ...data,
        {
          name: 'AGENT_BUILDER_PROMPT_OUTPUT',
          type: 'text',
          content: rowData.expectedOutput ?? '',
        },
      ]),
    };
    this.updateOneItem.emit(useCase);
  }

  public changePage(pageInfo: { currentPage: number; size: number }) {
    this.pageChange.emit({
      page: pageInfo.currentPage,
      pageSize: pageInfo.size,
    });
  }

  public changePageSize(size: number) {
    this.pageSize.size = size;
    this.currentPage = 1;
    this.pageChange.emit({
      page: 1,
      pageSize: size,
    });
  }

  getBase64(img: File, callback: (img: string) => void): void {
    const reader = new FileReader();
    reader.addEventListener('load', () => callback(reader.result!.toString()));
    reader.readAsDataURL(img);
  }

  public onAddFileSuccess(fileItem: any, useCase: any, variable: string) {
    if (fileItem.type === 'removed') {
      return;
    }
    if (fileItem.type !== 'start') {
      return;
    }
    if (['image/png', 'image/jpeg'].indexOf(fileItem.file.type) < 0) {
      this.message.error(this.i18n.transform('upload_image_type_invalid'));
      return;
    }
    useCase.images[variable] = fileItem.file.originFileObj;
    this.getBase64(fileItem.file.originFileObj, (img: string) => {
      useCase.variables[variable] = img;
      this.cdr.detectChanges();
    });

    this.updateActionState();
  }

  public async uploadImage(fileItem: any) {
    const formData = new FormData();
    formData.append('file', fileItem);
    const res = await this.promptOptimizeService.uploadImage(this.taskId, formData);
    return res.data;
  }

  public changeModel(e, data) {
    setTimeout(() => {
      data.action = this.dataToItemsFn(data);
      this.cdr.detectChanges();
    }, 0);
  }
}
