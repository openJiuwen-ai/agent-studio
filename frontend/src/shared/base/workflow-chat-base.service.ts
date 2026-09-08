import {
  ChangeDetectorRef,
  ElementRef,
  Injectable,
  Input,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { Graph } from '@antv/x6';
import { MonacoEditorLoaderService } from '@materia-ui/ngx-monaco-editor';
import { I18NextEagerPipe } from 'angular-i18next';
import { filter, Subject, take, takeUntil } from 'rxjs';

import { MessageComponent } from '@shared/services/cfdata.service';

import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import {
  EViewType,
  IApiSetting,
  IPluginConfig,
  type IWorkflow,
} from '@routes/agent-center/app-flow/app-flow.types';
import flowCommonLogic from '@routes/agent-center/app-flow/common-logic-workflow';
import type {
  IChatStartNode,
  IWorkflowField,
} from '@routes/agent-center/app-flow/node.type';
import { IControllerNode, userDrivenNodeTypes } from '@routes/agent-center/app-flow/node.type';
import { ENodeStatus, IFlowChatCard, IFlowChatItem } from '@routes/agent-center/types/common.types';
import { isSystemTypeWithNames } from '@routes/agent-center/utils';
import CommonLogic from '@routes/app-center/common-logic-app-center';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AppPluginRepoService } from '@services/agent-center/app-plugin-repo.service';
import { DynamicNodeParamsComponent } from '@shared/components/dynamic-node-params/dynamic-node-params.component';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { CommonUtils } from 'src/utils/common.util';
import { v4 as uuidV4 } from 'uuid';

interface IChatMemory extends IWorkflowField {
  modelUri: string;
  isError: boolean;
  isEmpty: boolean;
}

@Injectable()
export abstract class WorkflowChatBaseComponent {
  @Input() currWorkflow!: IWorkflow;

  @Input() graph!: Graph;
  // 这个实际上只有一个继承者使用，在afterViewInit绑定了一个keyDown事件
  @ViewChild('chatFlowTextarea') protected chatTextarea!: ElementRef;

  @ViewChild('chatContainerRef') protected chatContainerRef!: ElementRef;

  @ViewChild('dynamicNodeParams')
  protected dynamicNodeParams!: DynamicNodeParamsComponent;

  @ViewChild('globalParams')
  protected globalParams!: DynamicNodeParamsComponent;

  @ViewChild('pluginForm') pluginForm: NgForm;

  // 开始节点的输出参数列表
  protected startNodeParams: IChatStartNode[] = [];

  // 全局配置参数列表
  protected globalConfigParams: IChatMemory[] = [];

  // 问答对
  protected chatLoop: IFlowChatItem[] = [];

  // 是否存在一个流式接口
  protected isRequesting = false;

  protected sseInstance: any;

  protected hasSetPreviousNodeId = false;

  protected isPlanMode = false;

  protected planModeData;

  protected isStartFlowRunning = false;

  protected previousNodeId = '';

  protected nodeIdBlock: Record<string, ENodeStatus> = {};

  // 每一轮回答中，表示第几个分块
  protected index = 0;

  // 是否清空上一次QA完成的运行状态。通过execution是否完成来判断
  protected isClearRunStatus: boolean = false;

  // 交互式节点的node_id数组
  protected userDrivenNodeIds = [];

  protected inputList = [];

  // 表示用户是否向上滚动
  protected isUserScrolling = false;

  protected userQueryLimit: number;

  protected isFlowReadonly = false;

  protected type?: string;

  protected workflow_id = '';

  protected lang = CommonUtils.getLanguage();

  protected changeUrl = cdnAssetUrl;

  protected destroy$ = new Subject<void>();

  // 当前视图类型。默认值是CONFIG
  protected curView: EViewType = EViewType.CONFIG;

  protected chatView: EViewType = EViewType.CHAT_EMPTY;

  protected isPluginAuthLoading = false;

  // 插件节点的入参配置
  protected settingsList: IApiSetting[] = [];

  // 工作流中是否包含插件节点。插件节点可能是用户级鉴权/API Key/无需鉴权
  protected pluginNodes = [];

  protected versionId = '';

  // 是否重新点击【试运行】按钮
  protected isRetryRunning = false;

  // 工作流是否运行失败（3种标识：event:error/onError/onTimeout）
  // 遇到event:error的流式块，之后再遇到workflow_finished，不会刷新工作流运行状态
  protected isStreamFail = false;

  protected nodeSet = new Set();

  testStatusObj= {
    show: false,
    status: '',
    text: '',
  }

  //添加isBindEvent，在chat-flow-page中 is_agreement setServiceStatementAgreement$ 初始值为false,接口返回慢时，无法绑定keydown事件
  protected isBindEvent = false;
  constructor(
    protected appFlowServe: AppFlowService,
    protected appAgentServe: AppAgentRepoService,
    protected configServ: AgentConfigService,
    protected commonLogic: agentCommonLogic,
    protected monacoLoader: MonacoEditorLoaderService,
    protected i18n: I18NextEagerPipe,
    protected cdr: ChangeDetectorRef,
    protected agentDataServe: AgentDataService,
    protected pluginRepoServe: AppPluginRepoService,
  ) {
    this.agentDataServe
      .rollbackIdUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((version) => {
        this.versionId = version.version_id;
        this.isFlowReadonly = version.isFlowReadonly;
      });
  }

  ngOnInit() {
    this.userQueryLimit =
      this.configServ.getConfigs().user_query_limit ?? 100000;
    this.registerJSONValidationSchema();
  }

  ngAfterViewInit() {
    if (this.chatTextarea?.nativeElement && !this.isBindEvent) {
      // 监听底部输入框的键盘事件
      this.chatTextarea.nativeElement.addEventListener(
        'keydown',
        this.onKeydown.bind(this),
      );
      this.isBindEvent = true;
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
    if (this.chatTextarea) {
      this.chatTextarea.nativeElement.removeEventListener(
        'keydown',
        this.onKeydown.bind(this),
      );
    }
  }

  protected abstract onParamsValid(): void;

  protected updateCurAndChatView(): void {
    this.curView = EViewType.CHAT;

    if (!this.chatLoop.length) {
      this.chatView = EViewType.CHAT_EMPTY;
    } else {
      this.chatView = EViewType.CHAT_NOT_EMPTY;
    }
  }

  /** 获取输入节点的表单key-value，并转换为包含:和\n的字符串，作为run接口的入参 */
  protected getFormattedData(inputData: any) {
    const entries = Object.entries(inputData ?? {}).map(([key, value]) => {
      const formattedValue = value === null ? '' : value;
      return `${key}:${formattedValue}`;
    });
    return entries.join('\n');
  }

  protected handleSSEEvents(curIndex: number, callbackFn?) {
    this.testStatusObj.show = true;
    this.testStatusObj.status = 'run';
    this.testStatusObj.text = this.i18n.transform('workflow_chat_run', {time: ''});
    return {
      onMessage: (token: any) => this.onMessage(curIndex, token),
      onDone: (token: any) => {
        this.onDone(curIndex, token);
        if(callbackFn){
          callbackFn();
        }
      },
      onError: (error: { data: string; status: any }) => {
        this.testStatusObj.show = false;
        this.testStatusObj.status = 'error';
        this.testStatusObj.text = this.i18n.transform('workflow_chat_error', {time: ''});
        this.onError(curIndex, error);
        if(callbackFn){
          callbackFn();
        }
      },
      onTimeout: () => {
        this.testStatusObj.show = false;
        this.testStatusObj.status = 'error';
        this.testStatusObj.text = this.i18n.transform('workflow_chat_error', {time: ''});
        this.onTimeout(curIndex);
        if(callbackFn){
          callbackFn();
        }
      },
    };
  }

  protected onMessage(curIndex: number, token: any) {
    const chunkObj = token.data && flowCommonLogic.stringToObject(token.data);
    const chunkObjAddFrom = {...chunkObj, fromType:'onMessage'};
    this.appFlowServe.setTokenData(chunkObjAddFrom);
    this.getRunningNode(chunkObj);

    const { event, data, createdTime } = chunkObj;
    const {
      text,
      summary,
      message,
      is_finished,
      node_type,
      node_id,
      reasoning_content,
      offset,
      card,
    } = data || {};

    if ((event === 'scene_match') && this.type === 'multi') {
      this.isPlanMode = true;
    }

    if (['workflow_resume', 'workflow_start'].includes(event) && this.type === 'multi') {
      this.isStartFlowRunning = this.isStartFlow(data.workflow_id);
      if(this.isStartFlowRunning) {
        this.chatLoop[curIndex].plans = [{
          id: 'startFlow',
          title: this.i18n.transform('start_workflow'),
          status: 'loading',
          steps: [{
            description: '',
            step_idx: 1,
            step_name: ''
          }]
        }];
      }
    }

    // 多智能体子智能体规划模式
    if(this.isPlanMode) {
      if (event === 'scene_match') {
        const oldPlans = this.chatLoop[curIndex].plans || [];
        this.planModeData = {
          plans: [
            ...oldPlans,
            {
              title: data?.scene_name? `${this.i18n.transform('plan_model.tip_1')} ${data.scene_name}`
                : this.i18n.transform('plan_model.tip_4'),
              status: 'finished'
            }, {
              id: 'plan',
              title: this.i18n.transform('plan_model.tip_2'),
              status: 'loading',
              steps:[]
            }
          ],
        }
        this.chatLoop[curIndex] = {
          ...this.chatLoop[curIndex],
          ...this.planModeData,
        };
      }

      if (!this.chatLoop[curIndex].plans) {
        this.chatLoop[curIndex] = {
          ...this.chatLoop[curIndex],
          plans: [],
        };
      }

      const curPlans = this.chatLoop[curIndex].plans;

      if (event === 'plan_end' && data.steps?.length && curPlans?.length) {
        const plan = curPlans[curPlans.length-1];
        plan.steps = data.steps;
        plan.status = 'finished';
        this.chatLoop[curIndex] = {...this.chatLoop[curIndex]};
      }

      if (event === 'step_start') {
        const stepPlan = curPlans?.find(plan => plan.type === 'execStep');
        if (!stepPlan) {
          curPlans.push({
            type: 'execStep',
            title: this.i18n.transform('plan_model.tip_3'),
            status: 'loading',
            actionSteps: [
              {title:`${data?.step_idx}.${data?.step_name}`,actions:[]}
            ]}
          );
        } else {
          stepPlan.actionSteps.push({title:`${data?.step_idx}.${data?.step_name}`,actions:[]});
        }
      }

      if (event === 'step_end') {
        const stepPlan = curPlans?.find(plan => plan.type === 'execStep');
        const lastActionStep = stepPlan.actionSteps[stepPlan.actionSteps.length - 1];

        if (lastActionStep && data?.result_summary) {
          lastActionStep.actions.push({
            content: data.result_summary,
            title: ''
          });
        }
      }

      if(event === 'message' && (node_type === 'End' || node_type  === 'Message')) {
        const stepPlan = curPlans?.find(plan => plan.type === 'execStep');
        const lastActionStep = stepPlan.actionSteps[stepPlan.actionSteps.length-1];
        if(data.index === 0) {
          lastActionStep.actions.push({
            content: data.text,
            title: this.i18n.transform('plan_model.action_2', {name: data.node_name})
          });
        } else {
          const action = lastActionStep.actions[lastActionStep.actions.length - 1];
          action.content += data.text;
        }

        console.log(stepPlan);
      }

      if (event === 'task_complete' && curPlans?.length) {
        const plan = curPlans[curPlans?.length-1];
        plan.status = 'finished';
      }

      if (event === 'plugin_start' && curPlans?.length) {
        const plan = curPlans[curPlans.length-1];
        const actionSteps = plan.actionSteps[plan.actionSteps.length-1];
        const actions = actionSteps?.actions;
        const tool = this.handlePluginStart(chunkObj)
        actions.push({
          title: this.i18n.transform(this.getActionTitle(tool.type), {name: tool.name})
        });
      }

      if (event === 'summary_response') {
        this.chatLoop[curIndex].showAnswer.push({
          text: chunkObj.content,
          loading: false,
          isShowInputParams: false,
          isConfirmed: 'init',
          uuid: node_id,
          isFinished: true,
          messageId: createdTime,
        });
      }
    }

    if(event === 'message' && this.isStartFlowRunning) {
      const plan = this.chatLoop[curIndex].plans?.find(item => item.id === 'startFlow');

      if (plan && text && node_type !== 'Input') {
        const step = plan.steps[0];
        step.description += text;
      }
    }

    if (!this.hasSetPreviousNodeId && event === 'message' && node_id && !this.isStartFlowRunning) {
      this.previousNodeId = node_id;
      this.hasSetPreviousNodeId = true;
      this.nodeIdBlock[node_id] = ENodeStatus.NOTFINISHED;
      const len = this.chatLoop[curIndex].showAnswer.length;
      this.chatLoop[curIndex].showAnswer[len - 1].uuid = node_id;
    }

    // 新增一个卡片消息
    if (event === 'message' && node_type === 'Card' && !this.isStartFlowRunning) {
      let curCard = this.chatLoop[curIndex].cards.find(
        (item) => item.node_id === data.node_id,
      );
      if (!curCard) {
        curCard = this.getNewCard(data);
        this.chatLoop[curIndex].cards.push(curCard);
      }

      if (!data.is_finished) {
        const context = data.card.context;
        if (context?.desc) {
          if (context.desc?.stream === 'true') {
            curCard.desc = `${curCard.desc ?? ''}` + context.desc.answer;
          } else {
            curCard.desc = context.desc ?? '';
          }
        }

        if (context?.title) {
          if (context.title.stream === 'true') {
            curCard.title = `${curCard.title ?? ''}${context.title.answer}`;
          } else {
            curCard.title = context.title ?? '';
          }
        }
      }
    }

    if (event === 'message' && reasoning_content) {
      this.chatLoop[curIndex].thinkLoading = false;
      this.chatLoop[curIndex].thinkValue =
        this.chatLoop[curIndex].thinkValue + reasoning_content;
      this.chatLoop[curIndex].thinking = true;
    } else if (text || message) {
      this.chatLoop[curIndex].thinking = false;
      this.chatLoop[curIndex].collapsed = !this.isPlanMode;
    }

    if (event === 'message' && node_id !== this.previousNodeId && !this.isStartFlowRunning) {
      this.chatLoop[curIndex].thinkLoading = false;
      if (
        !this.nodeIdBlock[node_id] ||
        this.nodeIdBlock[node_id] === ENodeStatus.FINISHED
      ) {
        this.index += 1;
        this.nodeIdBlock[node_id] = ENodeStatus.ADDED; // 表示新增一个answer块
      }
      this.previousNodeId = node_id;
    }

    if (is_finished) {
      const answerToFinish = this.chatLoop[curIndex].showAnswer?.find(
        (i) => i.uuid === node_id && i.isFinished === false,
      );
      if (answerToFinish) {
        answerToFinish.isFinished = true;
      }

      if (!this.nodeIdBlock[node_id]) {
        this.index += 1;
        this.nodeIdBlock[node_id] = ENodeStatus.ADDED;
      } else {
        this.nodeIdBlock[node_id] = ENodeStatus.FINISHED;
        this.previousNodeId = '';
        const prevAns = this.chatLoop[curIndex].showAnswer?.[this.index];
        // 修复消息节点返回空输出的情况：结构化信息走 summary 字段，非 text
        if (prevAns && (!prevAns?.text || !text)) {
          prevAns.text = prevAns?.text || summary || ' ';
          prevAns.loading = false;
          prevAns.messageId = createdTime;
        } else if (!text) {
          this.chatLoop[curIndex].showAnswer.push({
            text: summary || ' ',
            loading: false,
            isShowInputParams: false,
            isConfirmed: 'init',
            uuid: node_id,
            isFinished: false,
            messageId: createdTime,
          });
        }
      }
    }

    if (
      event === 'workflow_finished' &&
      !this.isFlowReadonly && // 预览时不用设置状态
      this.shouldUpdatePublishBtn() &&
      data?.status?.code === 1 //试运行成功后才能发布
    ) {
      this.updateStatus(true);
    }

    if (this.nodeIdBlock[node_id] === 'added') {
      this.chatLoop[curIndex].showAnswer.push({
        text: '',
        loading: true,
        isShowInputParams: false,
        isConfirmed: 'init',
        uuid: node_id,
        isFinished: false,
      });
      this.nodeIdBlock[node_id] = ENodeStatus.NOTFINISHED; // 表示正在流式打印中
    }

    if (event === 'message' && text && node_type !== 'Input' && !this.isStartFlowRunning
      && (node_type !== 'End' && node_type !== 'Message' || !this.isPlanMode)
    ) {
      this.chatLoop[curIndex].thinkLoading = false;
      const currentAns = this.chatLoop[curIndex].showAnswer.find(
        (i) => i.uuid === node_id && i.isFinished === false,
      );
      if (currentAns) {
        currentAns.text += text;
        currentAns.loading = false;
      }
    }

    if (this.testStatusObj.status !== 'error' && this.testStatusObj.status !== 'success') {
      this.testStatusObj.status = 'run';
      const t = this.chatLoop[curIndex]?.latency || '';
      this.testStatusObj.text = this.i18n.transform('workflow_chat_run', {time: t});
    }

    if(event === 'workflow_end' && this.isStartFlowRunning) {
      this.isStartFlowRunning = false;
      const plan = this.chatLoop[curIndex].plans?.find(item => item.id === 'startFlow');
      plan.status = 'finished';
    }

    if (event === 'workflow_finished') {
      this.chatLoop[curIndex].thinkLoading = false;
      this.chatLoop[curIndex].thinking = false;
      this.removeLastEmptyAnswer();
      this.chatLoop[curIndex].latency = flowCommonLogic.calcElapsedTime(
        data.start_time,
        data.end_time,
      );
      this.isClearRunStatus = true;
      this.userDrivenNodeIds = [];
      if (this.testStatusObj.show) {
        if(this.testStatusObj.status === 'error') {
          const t = this.chatLoop[curIndex]?.latency || '';
          this.testStatusObj.text = this.i18n.transform('workflow_chat_error', {time: t});
        } else {
          this.testStatusObj.status = 'success';
          const t = this.chatLoop[curIndex]?.latency || '';
          this.testStatusObj.text = this.i18n.transform('workflow_chat_success', {time: t});
        }
      }
    }

    // 支持用户画像
    if (event === 'MEMORY_UPDATED') {
      this.chatLoop[curIndex].userPersona = {
        event,
        data,
      };
    }

    if (event === 'error') {
      this.testStatusObj.show = true;
      this.testStatusObj.status = 'error';
      this.testStatusObj.text = this.i18n.transform('workflow_chat_error', {time: ''});
      this.chatLoop[curIndex].thinkLoading = false;
      this.chatLoop[curIndex].thinking = false;
      const len = this.chatLoop[curIndex].showAnswer.length - 1;
      const lastChatAns = this.chatLoop[curIndex].showAnswer[len];
      if (!lastChatAns.isException) {
        if (lastChatAns && !lastChatAns?.text) {
          lastChatAns.text = this.i18n.transform('run_error');
          lastChatAns.loading = false;
          lastChatAns.isError = true;
        } else {
          this.chatLoop[curIndex].showAnswer.push({
            text: this.i18n.transform('run_error'),
            loading: false,
            isError: true,
          });
        }
        if (this.shouldUpdatePublishBtn()) {
          this.updateStatus(false);
        }
      }
    }

    if (event === 'exception') {
      this.chatLoop[curIndex].thinkLoading = false;
      this.chatLoop[curIndex].thinking = false;
      const len = this.chatLoop[curIndex].showAnswer.length - 1;
      const lastChatAns = this.chatLoop[curIndex].showAnswer[len];
      if (lastChatAns && !lastChatAns?.text) {
        lastChatAns.text = JSON.stringify(data, null, 2);
        lastChatAns.loading = false;
        lastChatAns.isError = true;
        lastChatAns.isException = true;
      } else {
        this.chatLoop[curIndex].showAnswer.push({
          text: JSON.stringify(data, null, 2),
          loading: false,
          isError: true,
        });
      }
      if (this.shouldUpdatePublishBtn()) {
        this.updateStatus(false);
      }
      this.removeLastEmptyAnswer();
      this.chatLoop[curIndex].latency = flowCommonLogic.calcElapsedTime(
        data.start_time,
        data.end_time,
      );
      this.isClearRunStatus = true;
      this.userDrivenNodeIds = [];
    }

    this.handleDebugNodeData(event, node_type, node_id);

    if (text && node_type === 'Input') {
      this.chatLoop[curIndex].thinkLoading = false;
      const { inputs } = text && flowCommonLogic.stringToObject(text);
      this.inputList = inputs?.map((item) => {
        return {
          ...item,
          uniqueId: `${this.chatLoop[curIndex].dialogId}-${item.name}`,
        };
      });
    }

    // 遇到最后一个node_type等于'Input'时，回答中出现表单
    if (node_type === 'Input' && is_finished === true) {
      const previousAns = this.chatLoop[curIndex].showAnswer[this.index];
      if (previousAns && !previousAns?.isShowInputParams) {
        previousAns.loading = false;
        previousAns.isShowInputParams = true;
        previousAns.isConfirmed = 'not-confirmed';
        // 输入节点的输入参数列表
        previousAns.inputList = this.inputList;
      }
    }

    if (event === 'sensitive') {
      const curAns = this.chatLoop[curIndex].showAnswer.find(
        (i) => i.uuid === node_id && i.isFinished === false,
      );
      if (!curAns) {
        return;
      }

      const curAnsText = curAns?.text ?? '';
      const safeOffset = Math.min(offset, curAnsText.length);
      curAns.text = curAnsText.slice(0, safeOffset) + (text ?? '');

      const curThinkVal = this.chatLoop[curIndex].thinkValue;
      const safeOffsetThink = Math.min(offset, curThinkVal.length);
      this.chatLoop[curIndex].thinkValue =
        curAnsText.slice(0, safeOffsetThink) + (reasoning_content ?? '');
    }

    if (this.type === 'multi') {
      if(event === 'task_end') {
        this.chatLoop[curIndex].thinkLoading = false;
        this.chatLoop[curIndex].thinking = false;
        this.chatLoop[curIndex].plans?.forEach(plan => {
          plan.status = 'finished';
        });
        this.isPlanMode = false;
      }
      if (event === 'task_end' && data.executionId) {
        this.chatLoop[curIndex].execution_id = data.executionId;
      }
      if (event === 'task_end' && !data?.executionId) {
        this.chatLoop[curIndex].showAnswer.push({
          text: `${this.i18n.transform('multi_no_intent')}`,
        });
      }
    } else {
      if (event === 'workflow_finished' && data.execution_id) {
        this.chatLoop[curIndex].execution_id = data.execution_id;
      }
    }
    this.scrollToBottom();
    this.cdr.markForCheck();
  }


  /**
   * 处理插件开始事件
   */
  public handlePluginStart(chunkDataObj: any,): { name: any; type: string } {
    let tool = {name: chunkDataObj.plugin.name, type: chunkDataObj.plugin.type}
    if (this.isUseSkill(chunkDataObj.plugin)) {
      console.log(chunkDataObj.plugin)
      tool = {
        type: 'skill',
        name: this.getSkillName(chunkDataObj.plugin.arguments)
      }
    }
    return tool
  }

  getActionTitle(type){
    switch (type) {
      case 'plugin':
        return 'plan_model.action_1';
      case 'skill':
        return 'plan_model.action_3';
      default:
        return 'plan_model.action_2';
    }
  }

  public isUseSkill(plugin){
    const skillTool = ['read_file']
    return skillTool.indexOf(plugin.name) > -1
  }
  public getSkillName(skillString){
    const regex = /\/skills\/[^\/]+\/(.*?)\//;
    const match = skillString.match(regex);
    if (match && match[1]) {
      return  match[1]
    } else {
      return 'Skill'
    }
  }

  protected onDone(curIndex: number, token: any) {
    const chunkObj = token.data && flowCommonLogic.stringToObject(token.data);
    const chunkObjAddFrom = {...chunkObj, fromType:'onDone'};
    this.appFlowServe.setTokenData(chunkObjAddFrom);
    this.getRunningNode(chunkObj);
    this.removeLastEmptyAnswer(true);
    // 将当前QA对的thinkLoading设置为false。避免只返回{"event": "end"}，会出现多个loading
    const curQA = this.chatLoop[curIndex];
    if (curQA) {
      curQA.thinkLoading = false;
      curQA.plans?.forEach(plan => {
        plan.status = 'finished';
      });
    }
    this.isRequesting = false;
    this.cdr.markForCheck();
  }

  getRunningNode(chunkObj){
    const { event, data } = chunkObj || {};
    let {
      node_id,
    } = data || {};
    if(event === 'node_started'){
      this.nodeSet.add(node_id)
    }
    if(event === 'node_finished'){
      this.nodeSet.delete(node_id)
    }
  }

  initializeNodeStatus() {
    this.nodeSet = new Set();
  }

  /** 判断是否需要更新发布按钮状态（在chat-flow-page组件中，需要override） */
  protected shouldUpdatePublishBtn(): boolean {
    return this.type !== 'multi';
  }

  protected onError(curIndex: number, error: { data: string; status: any }) {
    this.isRequesting = false;
    if (error.data) {
      const len = this.chatLoop[curIndex].showAnswer.length - 1;
      const lastChatAns = this.chatLoop[curIndex].showAnswer[len];
      lastChatAns.text = this.i18n.transform('NetErrorTips');
      lastChatAns.loading = false;
      lastChatAns.isError = true;
      this.chatLoop[curIndex].thinkLoading = false;
    }
    if (this.shouldUpdatePublishBtn()) {
      this.updateStatus(false);
    }
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  protected onTimeout(curIndex: number) {
    this.isRequesting = false;
    MessageComponent.showError(this.i18n.transform('streaming_timeout'), 3000);
    if (this.shouldUpdatePublishBtn()) {
      this.updateStatus(false);
    }
    this.sseInstance?.close();
    /** 如果没有之前的回答 */
    const len = this.chatLoop[curIndex].showAnswer.length - 1;
    const lastChatAns = this.chatLoop[curIndex].showAnswer[len];
    if (lastChatAns && lastChatAns?.text === '') {
      lastChatAns.text = this.i18n.transform('streaming_timeout');
      lastChatAns.loading = false;
      lastChatAns.isError = true;
    }
    this.chatLoop[curIndex].thinkLoading = false;
    this.scrollToBottom();
    this.cdr.markForCheck();
  }

  /** 移除最后一个"正在生成中"的空答案 */
  protected removeLastEmptyAnswer(isDone: Boolean = false): void {
    const lastChat = this.chatLoop[this.chatLoop.length - 1];

    if (isDone) {
      lastChat.showAnswer = lastChat.showAnswer?.filter(item => !(item?.text === '' && item?.loading === true));
    } else {
      const lastChatAns = lastChat.showAnswer[lastChat.showAnswer.length - 1];
      if (lastChatAns && lastChatAns?.text === '' && lastChatAns?.loading === true) {
        lastChat.showAnswer.pop();
      }
    }
  }

  /** 处理交互式节点（如提问器节点和输入节点）的insight数据 */
  protected handleDebugNodeData(
    event: string,
    node_type: string,
    node_id: string,
  ) {
    if (event === 'node_started' && userDrivenNodeTypes.includes(node_type)) {
      this.userDrivenNodeIds.push(node_id);
      this.isClearRunStatus = false;
    }

    if (event === 'node_wait' && this.userDrivenNodeIds.includes(node_id)) {
      if (!this.isClearRunStatus) {
        this.isClearRunStatus = false;
      }
    }
  }

  protected updateStatus(status) {
    this.appAgentServe
      .updateFlowStatus(this.workflow_id, {
        success: status,
      })
      .then(() => {
        this.currWorkflow.test_status = status ? 1 : 0;
      });
  }

  /** 回答完成 或 发送新问题时，页面滚动条到最底部 */
  protected scrollToBottom() {
    if (!this.isUserScrolling) {
      setTimeout(() => {
        if (this.chatContainerRef) {
          this.chatContainerRef.nativeElement.scrollTop =
            this.chatContainerRef.nativeElement.scrollHeight;
        }
      }, 0);
    }
  }

  protected registerJSONValidationSchema(
    isHandleGlobalConfig = false,
    addModeUri = false,
  ) {
    this.monacoLoader.isMonacoLoaded$
      .pipe(
        filter((isLoaded) => isLoaded),
        take(1),
      )
      .subscribe(() => {
        this.addModelUri(this.startNodeParams, addModeUri ? 'startNode' : '');
        const schemasForStart = this.getSchemas(this.startNodeParams);

        let schemasForGlobal = [];
        if (isHandleGlobalConfig) {
          this.addModelUri(
            this.globalConfigParams,
            addModeUri ? 'globalConfig' : '',
          );
          schemasForGlobal = this.getSchemas(this.globalConfigParams);
        }

        // 避免覆盖之前设置的 JSON Schema
        monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
          validate: true,
          schemas: [...schemasForStart, ...schemasForGlobal],
          schemaValidation: 'error',
        });
      });
  }

  protected addModelUri(
    inputList: IChatStartNode[] | IChatMemory[],
    uriType: string,
  ): void {
    // 为每个输入参数添加 modelUri 字段
    inputList.forEach((input) => {
      input.modelUri = this.commonLogic.getModelUriByType(
        input.type,
        input.name,
        uriType,
      );
      input.isError = false;
      input.isEmpty = false;
    });
  }

  protected getSchemas(inputList: IChatStartNode[] | IChatMemory[]): {
    uri: string;
    schema: any;
    fileMatch: string[];
  }[] {
    // 收集所有 JSON Schema
    return inputList.map((input) => ({
      uri: input.modelUri?.toString(),
      schema: this.commonLogic.getJSONSchemaByType(input.type)?.schema,
      fileMatch: [input.modelUri?.toString()],
    }));
  }

  protected onKeydown(event: KeyboardEvent) {
    CommonLogic.handleKeyboardEvent(this, event);
  }

  /** 为开始节点的每个输入参数增加 controlValue 字段，用于记录输入参数的控件值 */
  protected addControlValueField(params: any[]): any[] {
    return params.map((item) => {
      if (
        item.type === 'string' ||
        item.type === 'integer' ||
        item.type === 'number' ||
        item.type === 'boolean'
      ) {
        item.controlValue = this.dynamicNodeParams?.getControlValue(item.name);
      } else {
        item.controlValue = this.dynamicNodeParams?.getEditorDefaultValueByName(
          item.name,
        );
      }
      return {
        ...item,
      };
    });
  }

  /**
   * 获取试运行的配置参数列表。（1）工作流：开始节点的输出参数（2）multi agent：全局配置中的输入变量
   * @param source 配置参数化列表
   * @param filterKeys 需要被过滤的输入参数名称列表
   */
  protected getDebugConfigParams(
    source: IWorkflowField[],
    filterKeys: string[],
  ) {
    return source
      ?.map((param: any) => {
        if (param.type === 'array' && param.schema) {
          param.type = `${param.type}<${param.schema.type}>`;
        }
        return { ...param };
      })
      .filter((item) => !isSystemTypeWithNames(item, filterKeys));
  }

  /** 运行按钮是否置灰 */
  protected canRunWorkflow(): boolean {
    if (this.isRetryRunning || this.isStreamFail) {
      return false;
    }
    return this.isRequesting;
  }

  protected async runWorkflow() {
    this.appFlowServe.setRunBtnClicked(false);
    let dynamicNodeParamsPass = true;
    // 检查基础类型入参
    dynamicNodeParamsPass = this.dynamicNodeParams
      ? this.dynamicNodeParams.validatePrimitiveInputs()
      : true;
    // 检查复杂类型入参
    const validationResults =
      this.dynamicNodeParams?.validateJsonSchemas() || [];

    for (const item of validationResults) {
      if (item.type === 'object' || item.type.startsWith('array')) {
        if (item.isError || (item.required && item.isEmpty)) {
          dynamicNodeParamsPass = false;
        }
      }
    }

    if (
      this.settingsList.length &&
      this.pluginForm?.form
    ) {
      return;
    }

    if (dynamicNodeParamsPass) {
      this.onParamsValid(); // 钩子方法，由子类实现
    }
  }

  // ==== [用户级插件节点鉴权参数的相关函数 - 开始] ====
  protected async getPluginsAuthInfo(ids: string[]) {
    this.isPluginAuthLoading = true;

    return this.pluginRepoServe.getPluginList({ ids }).then(
      (res) => {
        const { plugin_list } = res || {};
        this.isPluginAuthLoading = false;
        const userAuthPlugins = plugin_list.filter(
          (item) => item.auth_info?.scope === 'USER',
        );
        this.settingsList.forEach((item) => {
          const plugin = userAuthPlugins.find((p) => p.plugin_id === item.id);
          if (plugin) {
            item.scope = plugin.auth_info?.scope;
            item.params = plugin.auth_info?.auth_keys.map((item) => {
              return {
                key: uuidV4(),
                name: item.source_name,
                value: '',
              };
            });
          }
        });
        // 试运行时，只需填写【用户级鉴权】插件的参数信息
        this.settingsList = this.settingsList.filter(
          (item) => item.scope === 'USER',
        );
        this.cdr.markForCheck();
        return this.settingsList;
      },
      () => {
        this.isPluginAuthLoading = false;
        this.cdr.markForCheck();
        return [];
      },
    );
  }

  protected buildPluginConfigs(): IPluginConfig[] {
    const configs = this.settingsList.map((setting) => {
      const config = {};
      setting.params.forEach((kvObj) => {
        if (!(this.isOptional(kvObj.name) && kvObj.value === '')) {
          config[kvObj.name] = kvObj.value;
        }
      });

      return {
        plugin_id: setting.id,
        config,
      };
    });

    return configs;
  }

  protected async buildSettingsData() {
    const currApis = this.appFlowServe.getGraphApiCmps(this.graph);
    const pluginIds = currApis.map((item) => item.id);
    this.pluginNodes = pluginIds;
    if (pluginIds?.length === 0) {
      return;
    }
    currApis.forEach((item) => {
      this.appFlowServe.setApiOriginInfo(item);
    });
    // get original name
    const apiNameIdPairs = this.appFlowServe.getApiOriginInfoByIds(
      currApis.map((c) => c.id),
    );

    const lastSettings = this.appFlowServe.getRunSettings();

    this.settingsList = apiNameIdPairs.map((api) => {
      const { id, name } = api;
      const params =
        lastSettings.find((setting) => setting.id === id)?.params ?? [];

      return {
        id,
        name,
        collapsed: false, // 默认是展开状态
        params,
      };
    });
    this.settingsList = await this.getPluginsAuthInfo(pluginIds);
  }

  // ==== [用户级插件节点鉴权参数的相关函数 - 结束] ====

  protected isOptional(name: string): boolean {
    const regex = /^x-auth-token$/i;
    return regex.test(name.toLowerCase());
  }

  protected isStartFlow(flowId: string): boolean {
    const controller: IControllerNode = this.currWorkflow?.details?.nodes?.find(
      (item) => item.id === 'controller',
    ) as IControllerNode;
    const flows = controller?.configs?.workflows ?? [];

    return flows.some(flow => flow.id === flowId && flow.type === 'Start');
  }

  protected getNewCard(data): IFlowChatCard {
    return {
      instance_id: data.instance_id,
      resource_url: data.resource_url,
      node_id: data.node_id,
      node_type: data.node_type,
      node_name: data.node_name,
      workflow_id: data.workflow_id,
      workflow_name: data.workflow_name,
      createdTime: data.createdTime,
      desc: data.desc,
      title: data.title
    }
  }
}
