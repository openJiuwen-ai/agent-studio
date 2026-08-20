import { Component, OnInit, Input, ChangeDetectorRef, Output, EventEmitter, inject, Inject } from '@angular/core';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import * as angularI18next from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { ActivatedRoute } from '@angular/router';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import commonLogicWorkflow from '../../../app-flow/common-logic-workflow';
import { MessageComponent } from '@shared/services/cfdata.service';
import { Subject, takeUntil } from 'rxjs';
import { IUpdateSingleAgentConfig } from '@routes/agent-center/types/my-workspace.types';
import { agentCommonLogic } from '../../common-logic-agent';
import { CommonUtils } from 'src/utils/common.util';
import { NzModalRef, NZ_MODAL_DATA } from 'ng-zorro-antd/modal';
@Component({
  selector: 'meta-optimize-prompt-modal',
  templateUrl: './optimize-prompt-modal.component.html',
  styleUrls: ['./optimize-prompt-modal.component.scss'],
  imports: [MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class OptimizePromptModalComponent implements OnInit {
  instruct: any = '';

  isWorkflow: boolean = false;

  @Output() tipsChange = new EventEmitter<string>();
  readonly modalRef = inject(NzModalRef);
  public state = {
    fetching: false,
    optimizeResult: '',
    isLoading: false,
    hasError: false,
  };

  public agentId = '';

  public lang = CommonUtils.getLanguage();

  private modelDeploymentId = '';

  private modelType = '';

  private model = '';

  private sseInstance: any;

  private destroy$ = new Subject<void>();

  constructor(
    private cdr: ChangeDetectorRef,
    private agentDataServe: AgentDataService,
    private route: ActivatedRoute,
    private appAgentRepoServe: AppAgentRepoService,
    private readonly i18n: angularI18next.I18NextEagerPipe,
    private commonLogic: agentCommonLogic,
    @Inject(NZ_MODAL_DATA) public nzData: any
  ) {
    this.instruct = this.nzData.instruct;
    this.isWorkflow = this.nzData.isWorkflow;
    this.route.queryParams.subscribe(params => {
      this.agentId = params.agentId || params.id;
    });

    this.agentDataServe
      .promptAndModelConfigUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((promptAndModelConfig: any) => {
        const { modelConfig } = promptAndModelConfig;
        this.modelDeploymentId = modelConfig.model_deployment_id || modelConfig.id;
        this.modelType = modelConfig.model_type || modelConfig.source;
        // 兼容各个节点类型数据格式 id=model=model_name
        this.model = modelConfig.model_name || modelConfig.model || modelConfig.id;
      });
  }

  ngOnInit() {
    this.optimizePrompt({
      instruct: typeof this.instruct === 'object' ? this.instruct.value : this.instruct,
      tools: [],
      stream: true,
      modelInfo: {
        model: this.modelDeploymentId,
        model_source: this.modelType,
        model_name: this.model,
        headers: {},
      },
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  /** 弹窗中智能生成的Prompt，点击确定时，调用put接口实时保存 */
  public confirm() {
    this.close();
    this.modalRef.destroy();
    if (this.isWorkflow) {
      this.tipsChange.emit(this.state.optimizeResult);
      if (this.nzData?.tipsChange) {
        this.nzData.tipsChange(this.state.optimizeResult);
      }
      this.state.optimizeResult = '';
      return;
    }
    this.agentDataServe.setPromptText(this.state.optimizeResult);
    this.doTriggerSave({
      data: {
        instructions: this.state.optimizeResult,
      },
    });
    this.state.optimizeResult = '';
  }

  private doTriggerSave(
    config: IUpdateSingleAgentConfig = {
      data: {},
      successCb: () => {},
      failCb: () => {},
      finallyCb: () => {},
    }
  ) {
    this.commonLogic.doTriggerSave(this.agentId, config);
  }

  public close() {}

  public dismiss() {}

  public dismissStream() {
    this.sseInstance?.close();
    this.state.fetching = false;
    this.state.optimizeResult = '';
    this.modalRef.destroy();
  }

  private optimizePrompt(inputs: any) {
    this.state.fetching = true;
    this.state.isLoading = true; // 显示loading+智能生成中
    this.sseInstance = this.appAgentRepoServe.optimizePromptSSE(inputs, this.agentId, this.lang, {
      onMessage: (event: any) => {
        try {
          const { code, message, data } = event.data && commonLogicWorkflow.stringToObject(event.data);
          if (code === 0 && data) {
            this.state.isLoading = false;
            this.state.optimizeResult += data;
          }
          if (code !== 0) {
            this.state.isLoading = false;
            this.state.hasError = true;
            this.state.optimizeResult = message !== '' ? message : this.i18n.transform('NetErrorTips');
          }
        } catch {}
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      onDone: () => {
        this.state.fetching = false;
        this.state.isLoading = false;
        this.cdr.markForCheck();
      },
      onError: (error: { data: string; status: any }) => {
        this.state.fetching = false;
        this.state.isLoading = false;
        this.state.hasError = true;
        if (error.data) {
          try {
            const errInfo = JSON.parse(error.data);
            const apiError = errInfo?.error_msg
              ? this.i18n.transform('ApiError', {
                  errCode: errInfo.error_code,
                  reason: errInfo.error_msg,
                })
              : '';

            this.state.optimizeResult = this.i18n.transform('NetErrorTips') + apiError;
          } catch {}
        } else {
          this.state.optimizeResult = this.i18n.transform('NetErrorTips');
        }
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
      onTimeout: () => {
        this.state.fetching = false;
        this.state.isLoading = false;
        this.state.hasError = true;
        MessageComponent.showError(this.i18n.transform('streaming_timeout'), 3000);
        this.sseInstance?.close();
        /** 如果没有之前的回答 */
        if (this.state.optimizeResult === '') {
          this.state.optimizeResult = this.i18n.transform('streaming_timeout');
        }
        this.scrollToBottom();
        this.cdr.markForCheck();
      },
    });
  }

  /** 流式打印过程中，弹窗的滚动条到最底部 */
  private scrollToBottom() {
    setTimeout(() => {
      const element = document.querySelector('#optimize-scroll-body');
      if (element) {
        element.scrollTop = element.scrollHeight;
      }
    }, 0);
  }
}
