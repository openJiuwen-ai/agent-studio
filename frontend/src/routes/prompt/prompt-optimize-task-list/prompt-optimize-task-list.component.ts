import { ChangeDetectorRef, Component, EventEmitter, Input, Output } from '@angular/core';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { PromptOptimizeTaskStatusComponent } from '@routes/prompt/prompt-optimize-task-list/prompt-optimize-task-status/prompt-optimize-task-status.component';
import { Router } from '@angular/router';
import { PromptOptimizeService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import { OptimizeTaskItem } from '@interfaces/prompt/prompt-optimize-task.interface';
import { CommonService } from '@services/common.service';
import { MessageComponent } from '@shared/services/cfdata.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { debounceTime, Subject, takeUntil } from 'rxjs';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { HttpService } from '@services/http.service';
import { PipesModule } from 'src/pipes/pipes.module';
import { NoDataGuideComponentComponent } from '@shared/components/no-data-guide/no-data-guide.component';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzTableModule } from 'ng-zorro-antd/table';
import { NzPaginationModule } from 'ng-zorro-antd/pagination';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzDropDownModule } from 'ng-zorro-antd/dropdown';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { FormsModule } from '@angular/forms';

interface ActionMenuItem {
  id: string;
  label: string;
  disabled?: boolean;
  popConfig?: {
    position: string;
    content: string;
    close: () => void;
    dismiss: () => void;
  };
}

interface TableColumn {
  title: string;
  width?: string;
}

interface PageSizeConfig {
  options: number[];
  size: number;
}

@Component({
  selector: 'meta-prompt-optimize-task-list',
  standalone: true,
  imports: [
    COMMON_MODULES,
    MODULES,
    FormsModule,
    PromptOptimizeTaskStatusComponent,
    NewCommonNoDataWithBtnComponent,
    PipesModule,
    NoDataGuideComponentComponent,
    NzTabsModule,
    NzSelectModule,
    NzButtonModule,
    NzTableModule,
    NzPaginationModule,
    NzSpinModule,
    NzDropDownModule,
    NzToolTipModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
  ],
  templateUrl: './prompt-optimize-task-list.component.html',
  styleUrl: './prompt-optimize-task-list.component.scss',
})
export class PromptOptimizeTaskListComponent {
  @Input() isLibraryPrompt = false;
  operatingTaskId: string | null = null;
  isLoading = false;
  taskList = {
    data: [],
    state: undefined,
  };
  columns: Array<TableColumn> = [
    {
      title: this.i18n.transform('prompt_optimize_task_name'),
      width: '220px',
    },
    {
      title: this.i18n.transform('prompt_type'),
    },
    {
      title: this.i18n.transform('prompt_description'),
      width: '260px',
    },
    {
      title: this.i18n.transform('prompt_status'),
      width: '150px',
    },
    {
      title: this.i18n.transform('execution_time'),
    },
    {
      title: this.i18n.transform('prompt_update_time'),
    },
    {
      title: this.i18n.transform('operation'),
      width: '220px',
    },
  ];
  @Output() changePromptButton = new EventEmitter<string>();
  @Output() clickGuideDesc = new EventEmitter<string>();
  subscribeBtnStatus = this.commonService.getSubscribeStatus();
  totalNumber: number = 0;
  currentPage: number = 1;
  pageSize: PageSizeConfig = {
    options: [10, 15, 20],
    size: 10,
  };
  filterOption = {
    typeFilter: {
      options: [
        { label: this.i18n.transform('all_types'), value: '', num: 0 },
        { label: this.i18n.transform('text'), value: 'text', num: 0 },
        { label: this.i18n.transform('multimodal'), value: 'multi', num: 0 },
      ],
      value: '',
    },
    statusFilter: {
      options: [
        { label: this.i18n.transform('all_tasks'), value: '', num: 0 },
        { label: this.i18n.transform('draft'), value: 'DRAFT', num: 0 },
        { label: this.i18n.transform('optimizing'), value: 'RUNNING', num: 0 },
        { label: this.i18n.transform('completed'), value: 'SUCCESS', num: 0 },
        {
          label: this.i18n.transform('eval_status_pending'),
          value: 'WAITING',
          num: 0,
        },
        {
          label: this.i18n.transform('eval_status_failed1'),
          value: 'FAILED',
          num: 0,
        },
        { label: this.i18n.transform('stop'), value: 'PAUSE', num: 0 },
      ],
      value: '',
    },
    searchText: {
      value: '',
    },
  };
  private listDebounceSubject = new Subject<any>();
  private destroy$ = new Subject<void>();
  public subTabs: Array<any> = [
    {
      title: this.i18n.transform('prompt'),
      id: 'prompt',
      active: false,
    },
    {
      title: this.i18n.transform('optimization_task'),
      id: 'optimize',
      active: true,
    },
  ];
  public buttonGroupSelected: string = this.subTabs[1].id;
  public isShowGuide = true;
  public btnTitle = this.i18n.transform('promptoptimizetasklist1');
  public isFirstLoading = true;
  selectTableIndex = 0;
  public title = this.i18n.transform('prompt');
  get isShowNoDataGuide() {
    return !this.taskList?.data?.length && !this.isLoading && this.searchNameIsEmpty;
  }

  get searchNameIsEmpty() {
    return this.filterOption.statusFilter.value === '' && this.filterOption.typeFilter.value === '' && !this.filterOption.searchText.value;
  }

  constructor(
    private router: Router,
    private promptOptimizeService: PromptOptimizeService,
    private commonService: CommonService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private readonly http: HttpService
  ) {
    this.http.getCurrentUserResourceStatus().subscribe(res => {});
  }

  ngOnInit() {
    if (this.isLibraryPrompt) {
      this.title = this.i18n.transform('optimization_task');
    }

    this.listTasks();
    this.listDebounceSubject.pipe(debounceTime(300), takeUntil(this.destroy$)).subscribe(() => {
      this.listTasks();
    });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    this.listDebounceSubject.complete();
  }

  handleClickClearSearch() {
    this.filterOption.statusFilter.value = this.filterOption.statusFilter.options[0].value;
    this.filterOption.typeFilter.value = this.filterOption.typeFilter.options[0].value;
    this.filterOption.searchText.value = '';
    this.listTasks();
  }

  dataToItemsFn(data: any) {
    const res = [];
    if (['success'].includes(data.status)) {
      res.push({
        id: 'show',
        label: this.i18n.transform('view'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['optimizing'].includes(data.status) && data.progressRate > 0) {
      res.push({
        id: 'show',
        label: this.i18n.transform('view'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['draft'].includes(data.status)) {
      res.push({
        id: 'edit',
        label: this.i18n.transform('base_edit'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['optimizing'].includes(data.status)) {
      res.push({
        id: 'stop',
        label: this.i18n.transform('stop'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['failed'].includes(data.status)) {
      res.push({
        id: 'retry',
        label: this.i18n.transform('base_retry'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['pause'].includes(data.status)) {
      res.push({
        id: 'continue',
        label: this.i18n.transform('continue'),
        disabled: !this.subscribeBtnStatus,
      });
    }
    if (['success', 'waiting', 'failed', 'optimizing'].includes(data.status)) {
      res.push({
        id: 'copy',
        label: this.i18n.transform('create_copy'),
        disabled: !this.subscribeBtnStatus,
      });
    }

    if (['draft', 'pause', 'success', 'waiting', 'failed'].includes(data.status)) {
      res.push({
        id: 'del',
        label: this.i18n.transform('base_remove'),
        disabled: !this.subscribeBtnStatus,
        popConfig: {
          position: 'bottom',
          content: this.i18n.transform('confirm_delete_task_tip'),
          close: () => {
            this.delTask(data.id);
          },
          dismiss: (): void => {},
        },
      });
    }
    return res;
  }

  onSelect(action: ActionMenuItem, task: any): void {
    if (action.id === 'show') {
      this.router.navigate(['/home/prompt/optimize/detail'], {
        queryParams: { id: task.id },
      });
    } else if (action.id === 'edit') {
      this.router.navigate(['/home/prompt/optimize/edit'], {
        queryParams: { id: task.id },
      });
    } else if (action.id === 'del') {
    } else if (action.id === 'retry') {
      this.operatingTaskId = task.id;
      this.promptOptimizeService
        .retryTask(task.id)
        .then(res => {
          MessageComponent.showSuccess(
            this.i18n.transform('start_retry', {
              task: task.taskName,
            })
          );
          this.listTasks();
        })
        .finally(() => {
          this.operatingTaskId = null;
        });
    } else if (action.id === 'stop') {
      this.operatingTaskId = task.id;
      this.promptOptimizeService
        .stopTask(task.id)
        .then(res => {
          MessageComponent.showSuccess(
            this.i18n.transform('task_pause', {
              task: task.taskName,
            })
          );
          this.listTasks();
        })
        .finally(() => {
          this.operatingTaskId = null;
        });
    } else if (action.id === 'continue') {
      this.operatingTaskId = task.id;
      this.promptOptimizeService
        .continueTask(task.id)
        .then(res => {
          MessageComponent.showSuccess(
            this.i18n.transform('task_resume', {
              task: task.taskName,
            })
          );
          this.listTasks();
        })
        .finally(() => {
          this.operatingTaskId = null;
        });
    } else if (action.id === 'copy') {
      this.operatingTaskId = task.id;
      this.promptOptimizeService
        .copyTask(task.id)
        .then(res => {
          MessageComponent.showSuccess(this.i18n.transform('task_copy_success'));
          this.router.navigate(['/home/prompt/optimize/edit'], {
            queryParams: { id: res.task_id },
          });
        })
        .finally(() => {
          this.operatingTaskId = null;
        });
    }
  }

  async toCreateTask() {
    await this.router.navigate(['/home/prompt/optimize/create']);
  }

  private convertTask(task: OptimizeTaskItem) {
    const res = {
      id: task.id,
      taskName: task.name,
      type: this.convertType(task.pt_type),
      desc: task.desc,
      status: this.convertStatus(task.status),
      log: task.message,
      progressRate: task.progress_rate,
      executionTime: task.exec_time,
      createTime: task.created_time,
      updatedTime: task.updatedTime,
      originData: task,
      actionList: [],
    };
    res.actionList = this.dataToItemsFn(res);
    return res;
  }

  private convertStatus(status: string) {
    switch (status) {
      case 'DRAFT':
        return 'draft';
      case 'RUNNING':
        return 'optimizing';
      case 'SUCCESS':
        return 'success';
      case 'FAILED':
        return 'failed';
      case 'WAITING':
        return 'waiting';
      case 'PAUSE':
        return 'pause';
      case 'PAUSING':
        return 'pausing';
      default:
        return 'unknown';
    }
  }

  private convertType(status: string) {
    switch (status) {
      case 'text':
        return this.i18n.transform('text');
      case 'multi':
        return this.i18n.transform('multimodal');
      default:
        return 'null';
    }
  }

  public handlePageChange(page: number) {
    this.currentPage = page;
    this.listTasks(page, this.pageSize.size);
  }

  public handlePageSizeChange() {
    this.currentPage = 1;
    this.listTasks(1, this.pageSize.size);
  }

  public handleSearch() {
    this.isLoading = true;
    this.listDebounceSubject.next(null);
  }

  public listTasks(page = 1, pageSize = 10) {
    this.totalNumber = 0;
    this.taskList.data = [];
    this.subTabs[0].active = false;
    this.subTabs[1].active = true;
    this.buttonGroupSelected = this.subTabs[1].id;
    this.isLoading = true;
    const params: any = {};
    if (this.filterOption.searchText.value) {
      params.name = this.filterOption.searchText?.value;
    }
    if (this.filterOption.typeFilter.value) {
      params.type = this.filterOption.typeFilter?.value;
    }
    if (this.filterOption.statusFilter.value) {
      params.status = this.filterOption.statusFilter?.value;
    }
    this.promptOptimizeService
      .listTasks(params, pageSize, page)
      .then(res => {
        const statusStatics = JSON.parse(res.message);
        this.filterOption.statusFilter.options[1].num = statusStatics.DRAFT ?? 0;
        this.filterOption.statusFilter.options[2].num = statusStatics.RUNNING ?? 0;
        this.filterOption.statusFilter.options[3].num = statusStatics.SUCCESS ?? 0;
        this.filterOption.statusFilter.options[4].num = statusStatics.WAITING ?? 0;
        this.filterOption.statusFilter.options[5].num = statusStatics.FAILED ?? 0;
        this.filterOption.statusFilter.options[6].num = statusStatics.PAUSE ?? 0;
        this.filterOption.statusFilter.options[0].num = statusStatics.TOTAL ?? 0;
        this.filterOption.typeFilter.options[0].num = statusStatics.TOTAL ?? 0;
        this.filterOption.typeFilter.options[1].num = statusStatics.TEXT ?? 0;
        this.filterOption.typeFilter.options[2].num = statusStatics.MULTI ?? 0;
        this.filterOption.statusFilter.value = this.filterOption.statusFilter.options.find(item => item.value === this.filterOption.statusFilter.value)?.value;
        this.currentPage = res.data?.pageNum ?? 1;
        this.pageSize.size = res.data?.pageSize ?? 10;
        this.totalNumber = res.data?.total ?? 0;
        this.taskList.data =
          res.data?.list?.map(item => {
            return this.convertTask(item);
          }) ?? [];
        this.cdr.markForCheck();
      })
      .finally(() => {
        this.isLoading = false;
        this.isFirstLoading = false;
      });
  }

  public delTask(id: string) {
    this.promptOptimizeService.deleteTask(id).then(res => {
      MessageComponent.showSuccess(this.i18n.transform('delete_task_success'));
      this.listTasks();
    });
  }

  public handleTabChange(e: any) {
    const tab = this.subTabs[e.index];
    if (tab.active) {
      this.buttonGroupSelected = tab.id;
      if (this.buttonGroupSelected === this.subTabs[0].id) {
        this.changePromptButton.emit();
      }
    }
  }

  public handleGuideClick(e) {
    if (!this.subscribeBtnStatus) {
      return;
    }
    if (e === 'create') {
      this.buttonGroupSelected = this.subTabs[0].id;
      this.changePromptButton.emit();
      this.clickGuideDesc.emit('create');
    }
    if (e === 'import') {
      this.buttonGroupSelected = this.subTabs[0].id;
      this.changePromptButton.emit();
      this.clickGuideDesc.emit('import');
    }
    if (e === 'createTask') {
      this.toCreateTask();
    }
    if (e === 'taskList') {
      this.listTasks();
    }
  }

  protected readonly changeUrl = cdnAssetUrl;
}
