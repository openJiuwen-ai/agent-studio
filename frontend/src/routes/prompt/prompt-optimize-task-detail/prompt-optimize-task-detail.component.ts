import { ChangeDetectionStrategy, ChangeDetectorRef, Component, TemplateRef, ViewChild, ElementRef } from '@angular/core';
import { ReactiveFormsModule } from '@angular/forms';
import { COMMON_MODULES, MODULES } from '@shared/modules';
import { SetSidebarVisibilityService } from '@shared/services/set-sidebar-visibility.service';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { HeaderComponent } from '@routes/prompt/prompt-optimize-task-detail/header/header.component';
import { PromptComparatorComponent } from '@routes/prompt/prompt-optimize-task-detail/prompt-comparator/prompt-comparator.component';
import { PromptOptimizeService } from '@services/agent-center/prompt-optimize-task/prompt-optimize.service';
import { ActivatedRoute, Router } from '@angular/router';
import { OptimizeTaskRunningDetail, VariableType } from '@interfaces/prompt/prompt-optimize-task.interface';
import { NzModalService } from 'ng-zorro-antd/modal';
import { PromptSaveComponent } from '@routes/prompt/prompt-save/prompt-save.component';
import { UseCasesAssessDetailComponent } from '@routes/prompt/prompt-optimize-task-detail/use-cases-assess-detail/use-cases-assess-detail.component';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { NzModalRef } from 'ng-zorro-antd/modal';
import { PromptService } from '@services/prompt.service';
import { ModelManagementService } from '@services/repositories/model-management-new';
import { FormateTimePipe } from 'src/pipes/formate-time.pipe';
import { NzDrawerService } from 'ng-zorro-antd/drawer';
import * as echarts from 'echarts';
@Component({
  selector: 'meta-prompt-optimize-task-detail',
  standalone: true,
  imports: [HeaderComponent, ReactiveFormsModule, COMMON_MODULES, MODULES, PromptComparatorComponent],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.COMMON, I18nNamespace.PROMPT_PLATFORM],
    },
    FormateTimePipe,
  ],
  templateUrl: './prompt-optimize-task-detail.component.html',
  styleUrls: ['./prompt-optimize-task-detail.component.scss', '../share/styles/common-styles.less'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PromptOptimizeTaskDetailComponent {
  @ViewChild('completeModal') completeModal: TemplateRef<any>;
  notShowCompleteModal = false;
  public promptId: string;
  public taskId: string;
  public taskDetail: OptimizeTaskRunningDetail;
  public basicInfoConfig: any = {
    title: this.i18n.transform('base_info'),
    colsNumber: 2,
    colsGap: ['16px'],
    colsWidth: ['50%', '50%'],
  };
  public basicInfoData = [
    {
      label: this.i18n.transform('prompt_optimize_task_name'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_prompt_type'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_desc'),
      colspan: 2,
      value: '--',
    },
    {
      label: this.i18n.transform('candidate_template_createTime'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_execution_time'),
      colspan: 1,
      value: '--',
    },
  ];
  public optimizeConfig: any = {
    title: this.i18n.transform('optimization_conf'),
    colsNumber: 2,
    colsGap: ['16px'],
    colsWidth: ['50%', '50%'],
  };
  public optimizeData = [
    {
      label: this.i18n.transform('prompt_optimize_task_round'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_number_of_prompt_examples'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_the_object_to_apply_1'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_model'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_type'),
      colspan: 1,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_scoring_criteria'),
      colspan: 2,
      value: '--',
    },
    {
      label: this.i18n.transform('prompt_optimize_task_background_prompt'),
      colspan: 2,
      value: '--',
    },
  ];

  // 图表
  public chartIns: any;
  public chartOption = {
    grid: {
      top: '30px',
      left: '30px',
      right: '70px',
      bottom: '25px',
    },
    legend: {
      show: false,
      icon: 'line',
    },
    tooltip: {
      formatter: params => {
        let htmlString = '';
        const { name, value, color } = params;
        htmlString += 'V' + name + '<br/>';
        htmlString +=
          '<div>' +
          '<span style="width:10px;display:inline-block;height:10px;border-radius:5px; background-color:' +
          color +
          ';">' +
          '</span>' +
          '<span style="margin-left:6px;>' +
          '<span style="width:100px;display:inline-block;">' +
          this.i18n.transform('success_rate') +
          '</span>' +
          '<span style="font-weight:bold"> ' +
          value +
          '%</span>' +
          '</span>' +
          '</div>';
        return htmlString;
      },
    },
    xAxis: {
      type: 'category',
      name: '迭代轮次',
      data: [],
    },
    yAxis: {
      name: '成功率%',
      type: 'value',
    },
    series: [
      {
        data: [],
        type: 'line',
      },
    ],
  };
  public chartType = 'LineChart';
  initFlag = true;
  //高亮差异
  public originPrompt: string = '';
  public originAcc: number;
  public optimizedPrompt: Array<{
    iteration_round: number;
    optimized_prompt: string;
    success_rate: number;
    is_best: boolean;
  }> = [];
  public variableList: Array<{ type: VariableType; value: string }> = [];
  public initVariableList: Array<{ type: VariableType; value: string }> = [];
  public diffHighLight = false;
  isSpinning = false;

  @ViewChild('chartContainer', { static: false }) chartContainer: ElementRef;

  constructor(
    private router: Router,
    private sidebarVisibilityServ: SetSidebarVisibilityService,
    private i18n: I18NextEagerPipe,
    private promptOptimizeService: PromptOptimizeService,
    private promptService: PromptService,
    private route: ActivatedRoute,
    private cdr: ChangeDetectorRef,
    private nzModal: NzModalService,
    private modelManagementService: ModelManagementService,
    private formateTimePipe: FormateTimePipe,
    private nzDrawerService: NzDrawerService
  ) {
    this.notShowCompleteModal = !(StorageService.getLocalStorage('PROMPT_OPTIMIZE_SHOW_COMPLETE') ?? true);
  }

  ngOnInit() {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('init');
    this.route.queryParams.subscribe(queryParams => {
      this.taskId = queryParams.id;
      this.loadTaskDetail();
    });
  }

  ngOnDestroy(): void {
    this.sidebarVisibilityServ.setSidebarsVisibilityByState('destroy');
  }

  ngOnChanges() {
    if (this.initFlag) {
      this.initFlag = false;
      return;
    }
    this.renderChart();
  }

  public loadTaskDetail() {
    this.isSpinning = true;
    this.promptOptimizeService
      .TaskDetail(this.taskId)
      .then(res => {
        const task: OptimizeTaskRunningDetail = res.data;
        task.iteration_results.iteration_info_list.forEach(item => {
          this.chartOption.xAxis.data.push(item.iteration_round.toString());
          this.chartOption.series[0].data.push(item.success_rate * 100);
        });
        this.taskDetail = task;
        this.initTaskDetail(task);
        this.renderChart();
      })
      .catch(error => {
        //加载失败，跳回列表
        this.onBack();
      })
      .finally(() => {
        this.isSpinning = false;
      });
  }

  onBack() {
    StorageService.setSessionStorage('activeTab', '1');
    this.router.navigate(['/home/agent-center/library-home'], {
      queryParams: {
        tabId: 'prompt',
      },
    });
  }

  public renderChart() {
    setTimeout(() => {
      let data = this.chartOption;
      this.chartIns = echarts.init(this.chartContainer.nativeElement);
      this.chartIns.setOption(data);
    }, 500);
  }

  public initTaskDetail(task: OptimizeTaskRunningDetail) {
    this.promptId = task.prompt_id;

    this.basicInfoData = [
      {
        label: this.i18n.transform('prompt_optimize_task_name'),
        colspan: 1,
        value: task.name,
      },
      {
        label: this.i18n.transform('prompt_optimize_task_prompt_type'),
        colspan: 1,
        value: this.i18n.transform(task.pt_type),
      },
      {
        label: this.i18n.transform('prompt_optimize_task_desc'),
        colspan: 2,
        value: task.desc,
      },
      {
        label: this.i18n.transform('candidate_template_createTime'),
        colspan: 1,
        value: this.formateTimePipe.transform(task.created_time),
      },
      {
        label: this.i18n.transform('prompt_optimize_task_execution_time'),
        colspan: 1,
        value: this.formateTimePipe.transform(task.exec_time),
      },
    ];

    let execModelName = '';
    let ptModelName = '';
    const query = {
      publish_status: 'online',
      with_router: true,
      model_type: 'LLM,IMAGE-TO-TEXT',
    };
    this.modelManagementService.getAvailableModelList(query).then(res => {
      res?.data?.forEach(item => {
        if (item.id === task.exec_object_config.model) {
          execModelName = item.model_name;
        }
        if (item.id === task.pt_model_config.model) {
          ptModelName = item.model_name;
        }
      });
      this.optimizeData = [
        {
          label: this.i18n.transform('prompt_optimize_task_round'),
          colspan: 1,
          value: task.max_iter_num.toString(),
        },
        {
          label: this.i18n.transform('prompt_optimize_task_number_of_prompt_examples'),
          colspan: 1,
          value: task.show_case_num.toString(),
        },
        {
          label: this.i18n.transform('prompt_optimize_task_the_object_to_apply_1'),
          colspan: 1,
          value: ptModelName,
        },
        {
          label: this.i18n.transform('prompt_optimize_task_model'),
          colspan: 1,
          value: execModelName,
        },
        {
          label: this.i18n.transform('prompt_optimize_task_type'),
          colspan: 1,
          value: task.target_type === 'subjective' ? this.i18n.transform('subjective_task') : this.i18n.transform('objective_task'),
        },
        {
          label: this.i18n.transform('prompt_optimize_task_scoring_criteria'),
          colspan: 2,
          value: task.score_standard || '--',
        },
        {
          label: this.i18n.transform('prompt_optimize_task_background_prompt'),
          colspan: 2,
          value: task.back_knowledge || '--',
        },
      ];
      this.cdr.markForCheck();
    });

    this.originPrompt = task.pt_text;

    const iterationInfoList = task.iteration_results.iteration_info_list.slice(1);
    this.originAcc = task.iteration_results?.iteration_info_list[0]?.success_rate;

    if (iterationInfoList.length > 0) {
      // 正常优化
      let bestPromptIndex = null;
      // 初始为原提示词准确率
      let bestPromptSuccessRate = this.originAcc;
      for (let i = 0; i < iterationInfoList.length; i++) {
        const promptInfo = iterationInfoList[i];
        if (promptInfo.success_rate > bestPromptSuccessRate) {
          bestPromptSuccessRate = promptInfo.success_rate;
          bestPromptIndex = i;
        }
      }
      if (bestPromptIndex === undefined) {
        this.notShowCompleteModal = true;
      }
      this.optimizedPrompt = iterationInfoList.map((promptInfo, index) => ({
        iteration_round: promptInfo.iteration_round,
        optimized_prompt: promptInfo.optimized_prompt,
        success_rate: promptInfo.success_rate,
        is_best: index === bestPromptIndex,
      }));
    } else {
      // 提前终止
      MessageComponent.showWarn(this.i18n.transform('promptcomparator_early_termination_tip1'));
      this.notShowCompleteModal = true;
    }
    this.variableList = task.pt_vars
      .filter(item => item.name !== 'AGENT_BUILDER_PROMPT_OUTPUT')
      .map(item => {
        return {
          type: item.type,
          value: item.name,
        };
      });
    this.initVariableList = this.variableList;
    this.cdr.markForCheck();
  }

  public handleRetryTask() {
    this.isSpinning = true;
    this.promptOptimizeService
      .copyTask(this.taskId)
      .then(res => {
        const taskId = res.task_id;
        MessageComponent.showSuccess(this.i18n.transform('auto_created_copy'));
        this.router.navigate(['/home/prompt/optimize/edit'], {
          queryParams: { id: taskId },
        });
      })
      .finally(() => {
        this.isSpinning = false;
      });
  }

  public handleCompleteTask() {
    if (!this.notShowCompleteModal) {
      this.openCompleteModal();
    } else {
      this.onBack();
    }
  }

  public handleStopTask() {
    this.isSpinning = true;
    this.promptOptimizeService
      .stopTask(this.taskId)
      .then(res => {
        MessageComponent.showSuccess(this.i18n.transform('task_paused'));
        this.loadTaskDetail();
      })
      .finally(() => {
        this.isSpinning = false;
      });
  }

  public handleContinueTask() {
    this.isSpinning = true;
    this.promptOptimizeService
      .continueTask(this.taskId)
      .then(res => {
        MessageComponent.showSuccess(this.i18n.transform('task_continued'));
        this.loadTaskDetail();
      })
      .finally(() => {
        this.isSpinning = false;
      });
  }

  public async openSaveModal(targetPrompt: string) {
    let initInfo: any = {
      promptId: this.promptId,
      name: this.taskDetail.name,
      desc: this.taskDetail.desc,
      taskId: this.taskId,
      prompt: targetPrompt,
      type: this.taskDetail.pt_type,
      variableList: this.variableList,
    };
    if (this.promptId) {
      const res = await this.promptService.getPromptTemplateListAsync({
        offset: 0,
        limit: 1,
        template_id: this.promptId,
      });
      const promptDetail = res.data[0];
      initInfo = {
        ...initInfo,
        tags: promptDetail.tag_list,
        industry: promptDetail.industry,
      };
    }
    const drawerRef = this.nzDrawerService.create({
      nzContent: PromptSaveComponent,
      nzWidth: '700px',
      nzData: {
        isOptimize: true,
        promptSaveInitInfo: initInfo,
        savePromptTemplate: promptTemplate => {
          this.promptOptimizeService.savePromptTemplate(promptTemplate).then(res => {
            const href = `${window.location.href.split('#')[0]}#/home/agent-center/library-home?tabId=prompt`;
            MessageComponent.showSuccess(`${this.i18n.transform('prompt_creation_success')} <a href="${href}">${this.i18n.transform('goto_view')}</a>`);
          });
        },
      },
    });
  }

  public openAssessDetailModal(iterNum: string) {
    const drawerRef = this.nzDrawerService.create({
      nzContent: UseCasesAssessDetailComponent,
      nzWidth: '1000px',
    });
    drawerRef.afterOpen.subscribe(() => {
      const instance = drawerRef.getContentComponent();
      instance.taskId = this.taskId;
      instance.iterNum = iterNum;
      instance.ptType = this.taskDetail.pt_type as any;
      instance.variables = this.variableList;
      instance.getDetail();
    });
  }

  public openCompleteModal(): void {
    const modalRef = this.nzModal.create({
      nzContent: this.completeModal,
      nzOnOk: (nzModalRef: NzModalRef): void => {
        StorageService.setLocalStorage('PROMPT_OPTIMIZE_SHOW_COMPLETE', !this.notShowCompleteModal);
        modalRef.destroy();
        this.openSaveModal(this.taskDetail.iteration_results.current_best_prompt);
      },
      nzOnCancel: (nzModalRef: NzModalRef): void => {},
    });
  }

  protected readonly changeUrl = cdnAssetUrl;
}
