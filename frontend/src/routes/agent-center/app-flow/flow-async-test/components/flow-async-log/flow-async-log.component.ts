import {
  Component,
  Input,
  SimpleChanges
} from '@angular/core';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { v4 as uuidV4 } from 'uuid';

import { I18nNamespace } from '@i18n';
import { DateOptionRender } from '@routes/agent-center/app-agent/components/date-option-render/date-option-render.component';
import type {
  IWorkflow
} from '@routes/agent-center/app-flow/app-flow.types';
import { FlowLogModalComponent } from '@routes/agent-center/app-flow/components/flow-log-modal/flow-log-modal.component';
import { TimeLineComponent } from '@routes/agent-center/app-insight/components/time-line/time-line.component';
import { AppMarkdownAnswerComponent } from '@shared/components/app-markdown-answer/app-markdown-answer.component';
import { AssetCalendarIconComponent } from '@shared/components/assets/asset-calendar-icon/asset-calendar-icon.component';
import { AssetCopyIconComponent } from '@shared/components/assets/asset-copy-icon/asset-copy-icon.component';
import { AssetCopySuccessIconComponent } from '@shared/components/assets/asset-copy-success-icon/asset-copy-success-icon.component';
import { AssetErrorIconComponent } from '@shared/components/assets/asset-error-icon/asset-error-icon.component';
import { AssetGenerateLoadingIconComponent } from '@shared/components/assets/asset-generate-loading-icon/asset-generate-loading-icon.component';
import { AssetListIconComponent } from '@shared/components/assets/asset-list-icon/asset-list-icon.component';
import { AssetLoadingIconComponent } from '@shared/components/assets/asset-loading-icon/asset-loading-icon.component';
import { AssetLogIconComponent } from '@shared/components/assets/asset-log-icon/asset-log-icon.component';
import { AssetPageFailComponent } from '@shared/components/assets/asset-page-fail/asset-page-fail.component';
import { AssetSequenceIconComponent } from '@shared/components/assets/asset-sequence-icon/asset-sequence-icon.component';
import { AssetSuccessIconComponent } from '@shared/components/assets/asset-success-icon/asset-success-icon.component';
import { JsonViewerComponent } from '@shared/components/json-viewer/json-viewer.component';
import { NoDataIconComponent } from '@shared/components/no-data-icon/no-data-icon.component';
import { MODULES } from '@shared/modules';
import { CopyType } from '../../../node.type';
import * as flowAsyncTestInterface from '../../flow-async-test.interface';
import { getDateByTemp } from '@routes/agent-center/app-flow/utils/log-utils';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzBreadCrumbModule } from 'ng-zorro-antd/breadcrumb';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTabsModule } from 'ng-zorro-antd/tabs';
import { NzCollapseModule } from 'ng-zorro-antd/collapse';

@Component({
  selector: 'flow-async-log',
  templateUrl: './flow-async-log.component.html',
  styleUrls: ['./flow-async-log.component.scss'],
  standalone: true,
  imports: [
    MODULES,
    JsonViewerComponent,
    TimeLineComponent,
    AssetLogIconComponent,
    AppMarkdownAnswerComponent,
    AssetCopySuccessIconComponent,
    AssetCalendarIconComponent,
    AssetListIconComponent,
    AssetSequenceIconComponent,
    AssetCopyIconComponent,
    AssetLoadingIconComponent,
    AssetSuccessIconComponent,
    AssetGenerateLoadingIconComponent,
    AssetErrorIconComponent,
    NoDataIconComponent,
    AssetPageFailComponent,
    DateOptionRender,
    NzSelectModule,
    NzBreadCrumbModule,
    NzIconModule,
    NzTabsModule,
    NzCollapseModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class FlowAsyncLogComponent extends FlowLogModalComponent {
  @Input() override conversationId: string = '';

  @Input() execListInput: any = [];

  @Input() currWorkflow!: IWorkflow;

  @Input() taskInfo: flowAsyncTestInterface.FlowTaskDetailRes;

  @Input() showExecList = false;

  versionId = '';

  override dates: Array<{ value: string; label: string; startTime?: number; endTime?: number; totalCount?: number; successCount?: number; failCount?: number; disabled?: boolean }> = [];

  selectDateObj: { value: string; label: string; startTime?: number; endTime?: number; totalCount?: number; successCount?: number; failCount?: number; disabled?: boolean } = null;

  override ngOnChanges(changes: SimpleChanges) {
    if (!this.dates) {
      this.initializeDates();
    }

    if (changes?.execListInput?.currentValue?.length > 0) {
      this.initializeDates();
      this.executionList = this.execListInput;
      this.executionSelected = this.executionList[0];
      this.selectDateObj = this.dates?.[0] || null;
      const { execution_id } = this.executionSelected || {};
      this.getSingleExecDetail(this.workflow_id, execution_id);
    } else {
      this.workflowDebugInfo = {
        status: '',
        status_desc: '',
        list: [],
        result: '',
      };
      this.executionList = [];
      this.executionSelected = null;
    }
    this.handleAllDate();

    if (changes.conversationId?.currentValue) {
      this.conversationSelected = this.conversationId;
    }
  }

  override ngAfterViewInit(): void {
    this.init();
  }

  public init(): void {
    this.route.queryParams.subscribe((params) => {
      const { id, versionId, type, versionName } = params;
      this.versionId = versionId;
    });
  }

  public override handleCopy(data: any, target: CopyType) {
    const copyInfoMap = {
      input: { content: data.inputs, icon: 'inputsCopyIcon' },
      output: { content: data.outputs, icon: 'outputsCopyIcon' },
      modelOutput: {
        content: this.getLlmField(data?.metadata, 'llm_outputs'),
        icon: 'modelOutputCopyIcon',
      },
      modelInput: {
        content: this.getLlmField(data?.metadata, 'llm_inputs'),
        icon: 'modelInputCopyIcon',
      },
    };

    const targetInfo = copyInfoMap[target];
    if (!targetInfo) {
      return;
    }

    const { content, icon } = targetInfo;
    if (typeof content === 'string') {
      this.clipboard.copy(content);
    } else {
      this.clipboard.copy(JSON.stringify(content) as string);
    }

    data[icon] = true;
    setTimeout(() => {
      data[icon] = false;
      this.cdr.markForCheck();
    }, 3000);
  }

  public override changeExecSelected() {
    this.getSingleExecDetail(this.workflow_id, this.executionSelected?.execution_id);
  }

  /** 根据executionId，查询节点的调用详情 */
  protected override getSingleExecDetail(
    workflowId: string,
    executionId: string,
  ) {
    this.flowRepoServe
      .getAsyncSingleExecInfo(
        workflowId,
        executionId,
        this.taskInfo.is_published ? { version: this.taskInfo.workflow.version_id } : {},
      )
      .then((result: any) => {
        // 通过增加node_uuid字段，保证点击时序图上的某个节点，可以展开对应的调用链信息
        result?.event_list?.forEach((item) => {
          item.node_uuid = uuidV4();
        });

        this.result = result;
        this.callChainInfo.list = this.convertToTableData(
          this.result?.event_list,
        ).filter((item) => !item.parent_node_id);
        this.crumb = [
          {
            label: this.i18n.transform('parent'),
            id: '',
          },
        ];
        this.timelineData = this.convertToTimelineData(this.result?.event_list);
        this.timelineData.childInvokes =
          this.timelineData?.childInvokes?.filter(
            (item) => !item?.parent_node_id,
          );

        const { status, start_time, end_time, outputs, error_info } = result;
        this.updateWorkflowDebugInfo(result);
        this.updateWorkflowStatus(status);
        if (status === 'succeeded') {
          this.workflowDebugInfo.result = outputs?.responseContent;
        } else {
          this.workflowDebugInfo.result = error_info;
        }
        this.cdr.markForCheck();
      });
  }

  public override onSelectDate(event: { value: string; startTime?: number; endTime?: number }) {
    if (event.value === this.ALL_ITEM) {
      this.executionList = this.execListInput;
    } else {
      this.executionList = this.execListInput.filter(exec => {
        return exec.start_time >= event.startTime && exec.start_time <= event.endTime;
      });
    }
    this.executionSelected = this.executionList?.[0] || null;
    if (this.executionSelected) {
      this.getSingleExecDetail(this.workflow_id, this.executionSelected?.execution_id);
    }
  }

  protected override initializeDates(): void {
    super.initializeDates();
    this.dates.forEach(dateItem => {
      dateItem.totalCount = 0;
      dateItem.successCount = 0;
      dateItem.failCount = 0;
    });
  }

  protected override handleAllDate(): void {
    const execList = this.executionList || [];
    execList?.forEach((item) => {
      const dateString = getDateByTemp(item.start_time);
      const dateItem = this.dates.find(date => date.value === dateString);
      if (!dateItem) {
        return;
      }

      dateItem.totalCount += 1;
      dateItem.successCount += item.status === 'succeeded' ? 1 : 0;
      dateItem.failCount += item.status === 'failed' ? 1 : 0;
    });

    this.dates.forEach(item => {
      if (item.value === 'all') {
        return;
      }
      item.disabled = !item.totalCount;
    })
  }
}
