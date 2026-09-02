import { Component, EventEmitter, Input, Output, SimpleChanges, } from '@angular/core';
import { ActivatedRoute } from "@angular/router";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject, takeUntil } from "rxjs";

import { MessageComponent } from '@shared/services/cfdata.service';

import { I18nNamespace } from '@i18n';
import type { IWorkflow } from "@routes/agent-center/app-flow/app-flow.types";
import { FlowAsyncTestService } from "@routes/agent-center/app-flow/flow-async-test/flow-async-test.service";
import { FlowTaskService } from "@services/agent-center/flow-task.service";
import { NoDataIconComponent } from "@shared/components/no-data-icon/no-data-icon.component";
import { MODULES } from '@shared/modules';
import { cdnAssetUrl } from "../../../../../../single-spa/assets-url";
import { FlowCreateTaskParams, FlowCreateTaskQuery, FlowParsedTask, FlowTask, FlowTaskStatus } from '../../flow-async-test.interface';
import { TaskGroup } from './flow-task-list.interface';
import { FLOW_TASK_QUERY_INTERVAL } from '../../flow-async-test.constant';

@Component({
  selector: 'flow-task-list',
  templateUrl: './flow-task-list.component.html',
  styleUrls: ['./flow-task-list.component.less'],
  standalone: true,
  imports: [
    MODULES,
    NoDataIconComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class FlowTaskListComponent {
  @Input() currWorkflow!: IWorkflow;
  @Output() selectTask = new EventEmitter<FlowParsedTask>();

  public changeUrl = cdnAssetUrl;

  public taskList: FlowParsedTask[] = [];
  public taskGroup: TaskGroup[] = [
    {
      id: 'today',
      groupLabel: this.i18n.transform('flow_time_group_today'),
      taskList: []
    },
    {
      id: 'yesterday',
      groupLabel: this.i18n.transform('flow_time_group_yesterday'),
      taskList: []
    },
    {
      id: 'lastWeek',
      groupLabel: this.i18n.transform('flow_time_group_last_week'),
      taskList: []
    },
    {
      id: 'lastMonth',
      groupLabel: this.i18n.transform('flow_time_group_last_month'),
      taskList: []
    },
    {
      id: 'other',
      groupLabel: this.i18n.transform('flow_time_group_other'),
      taskList: []
    }
  ];
  public displayGroup: TaskGroup[] = [];

  public selectId: string;

  public countMap = {
    running: 0,
    success: 0,
    fail: 0,
    total: 0
  };
  public isLoading = true;
  public versionId: string = '';

  private queryTimer;
  private destroy$ = new Subject<void>();

  constructor(
    private flowTaskService: FlowTaskService,
    private route: ActivatedRoute,
    private flowAsyncTestService: FlowAsyncTestService,
    private i18n: I18NextEagerPipe,
  ) {
    /** 任务状态是否发生改变 */
    this.flowAsyncTestService
      .taskStatusUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe(async (isChange: boolean) => {
        if (isChange && this.currWorkflow?.workflow_id) {
          this.getTaskList();
        }
      });
  }

  ngOnChanges(changes: SimpleChanges) {
    // 每次点击试运行按钮，清空上一次的【运行结果】Tab页数据
    if (this.currWorkflow?.workflow_id) {
      this.getTaskList();
    }
  }

  ngAfterViewInit(): void {
    this.init();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    clearTimeout(this.queryTimer);
    this.queryTimer = null;
  }

  public createTask() {
    const params: FlowCreateTaskParams = {
      'type': 'chat', // 根据工作流类型支持chat\task，对话型和任务型
      'name': this.i18n.transform('flow_async_new_task'),
      'mode': 'ASYNC',
      'version': this.versionId ? '' : String(this.currWorkflow.update_time)
    };
    let query: FlowCreateTaskQuery = {};
    if (this.versionId) {
      query.version = this.versionId;
    }
    this.flowTaskService.createTask(this.currWorkflow.workflow_id, params, query).then((res) => {
      MessageComponent.showSuccess(this.i18n.transform('flowtasklistcomponent_648'));
      this.selectId = res.id;
      this.getTaskList();
    })
  }

  handleTask(event: Event, type: string, item: FlowParsedTask): string {
    event.stopPropagation();

    switch (type) {
      case 'edit':
        item.editName = item.name;
        item.isEdit = true;
        return;
      case 'delete':
        this.deleteTask(item)
        return;
      case 'cancel':
        item.isEdit = false;
        return;
      case 'confirm':
        item.isEdit = false;
        this.changeTask(item)
        return;
      case 'select':
        this.doSelectTask(item)
        return;
      default:
        return;
    }
  }

  private init(): void {
    this.route.queryParams.subscribe((params) => {
      const {id, versionId, type, versionName} = params;
      this.versionId = versionId;
    });
  }

  private doSelectTask(item: FlowParsedTask): void {
    this.selectTask.emit(item);
    this.selectId = item.id;
  }

  private changeTask(taskInfo: FlowParsedTask) {
    if(!taskInfo.editName){
      MessageComponent.showError(this.i18n.transform('flowtasklistcomponent_649'));
      return
    }
    taskInfo.name = taskInfo.editName;
    const { editName, isEdit, ...params } = taskInfo;
    this.flowTaskService.putTask(this.currWorkflow.workflow_id, taskInfo.id, params).then((res) => {
      MessageComponent.showSuccess(this.i18n.transform('flowtasklistcomponent_650'));
    })
  }

  private deleteTask(taskInfo: FlowParsedTask) {
    this.flowTaskService.deleteTask(this.currWorkflow.workflow_id, taskInfo.id).then((res) => {
      MessageComponent.showSuccess(this.i18n.transform('flowtasklistcomponent_651'));
      this.getTaskList();
    })
  }

  private getTaskList(): void {
    this.isLoading = true;
    this.flowTaskService.getTaskList(this.currWorkflow.workflow_id).then((res) => {
      this.countMap = {
        running: 0,
        success: 0,
        fail: 0,
        total: 0
      };

      this.countMap.total = res.count;
      this.taskList = res.data.map(task => {
        if (task.status === FlowTaskStatus.INIT || task.status === FlowTaskStatus.RUNNING) {
          this.countMap.running++;
        } else if (task.status === FlowTaskStatus.COMPLETED) {
          this.countMap.success++;
        } else if (task.status === FlowTaskStatus.FAILED || task.status === FlowTaskStatus.CANCELLED) {
          this.countMap.fail++;
        }
        return this.parseTaskItem(task);
      });
      this.divideTaskToGroup();

      if (this.taskList.length) {
        const defaultItem = this.taskList.find(item => item.id === this.selectId) || this.taskList[0];
        this.doSelectTask(defaultItem);
      }
      if (this.countMap.running) {
        clearTimeout(this.queryTimer);
        this.queryTimer = setTimeout(() => {
          this.getTaskList();
        }, FLOW_TASK_QUERY_INTERVAL);
      }
    }).finally(() => {
      this.isLoading = false;
    });
  }

  private parseTaskItem(task: FlowTask): FlowParsedTask {
    return {
      ...task,
      isEdit: false,
      editName: task.name,
    }
  }

  private divideTaskToGroup() {
    this.taskGroup.forEach(group => {
      group.taskList = [];
    });

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    this.taskList.forEach(task => {
      const taskDate = new Date(task.create_time);
      taskDate.setHours(0, 0, 0, 0);

      const diffDays = Math.floor((today.getTime() - taskDate.getTime()) / (1000 * 60 * 60 * 24));

      if (diffDays === 0) {
        this.taskGroup.find(g => g.id === 'today').taskList.push(task);
      } else if (diffDays === 1) {
        this.taskGroup.find(g => g.id === 'yesterday').taskList.push(task);
      } else if (diffDays >= 2 && diffDays <= 7) {
        this.taskGroup.find(g => g.id === 'lastWeek').taskList.push(task);
      } else if (diffDays >= 8 && diffDays <= 30) {
        this.taskGroup.find(g => g.id === 'lastMonth').taskList.push(task);
      } else {
        this.taskGroup.find(g => g.id === 'other').taskList.push(task);
      }
    });

    this.displayGroup = this.taskGroup.filter(group => group.taskList.length);
  }
}
