import { Injectable } from '@angular/core';
import { MessageComponent } from '@shared/services/cfdata.service';
import { Network } from '@model';
import { AgentBotPageService } from '@routes/agent-center/app-agent/agent-bot-page/agent-bot-page.service';
import {
  EPluginCategoryTabId,
  IUpdateSingleAgentConfig,
} from '../types/my-workspace.types';
import { I18NextEagerPipe } from 'angular-i18next';
import i18next from 'i18next';
import { IsLongTextOverflowService } from '@shared/services/is-long-text-overflow.service';
import { ToolService } from '@services/tool.service';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ContextService } from '@services/context.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { I18nNamespace } from '@i18n';

export const exampleTipText = `## ${i18next.t('character_settings')}
${i18next.t('as_a')}________，${i18next.t('your_task_is')}________。

## ${i18next.t('component_capability')}
${i18next.t('you_possess')}________${i18next.t('capacity')}。

## ${i18next.t('requirements_and_restrictions')}
1.${i18next.t('style_requirements_for_output')}________。
2.${i18next.t('the_format_of_the_output')}________。
3.${i18next.t('the_word_limit')}________。`;

export const exampleTipInsideList = ['ti3-tooltip', 'ti3-tooltip-content'];

export const autoGenerateTipInsideList = [
  'auto-tip-container',
  'auto-tip-title',
  'auto-alert-icon',
  'auto-alert-title',
  'auto-tip-content',
  'auto-tip-bottom-btns',
  'ti3-tooltip',
  'ti3-tooltip-content',
];

export const prologueBtnClassList = [
  'opening-container',
  'optimize-opening-icon',
  'optimize-opening-text',
];

export const questionsBtnClassList = [
  'questions-container',
  'optimize-question-icon',
  'optimize-question-text',
];

export const modeSelectTipText = [
  {
    mode: `${i18next.t('accurate')}：`,
    desc: i18next.t('accurate_desc'),
  },
  {
    mode: `${i18next.t('balanced')}：`,
    desc: i18next.t('balanced_desc'),
  },
  {
    mode: `${i18next.t('creative')}：`,
    desc: i18next.t('creative_desc'),
  },
  {
    mode: `${i18next.t('custom_mode')}：`,
    desc: i18next.t('custom_mode_desc'),
  },
];

/**
 * Agent应用的通用逻辑
 */
@Injectable({
  providedIn: 'root',
})
export class agentCommonLogic {
  private canTriggerSave = false;
  private triggerSaveQueue = [];
  private triggerSaveIndex = 0;
  private agentCreatorId = '';

  constructor(
    private readonly i18n: I18NextEagerPipe,
    private isLongTextOverflowServe: IsLongTextOverflowService,
    private toolServ: ToolService,
    private agentDataServe: AgentDataService,
    private service: AppAgentRepoService,
    private ctxServ: ContextService,
    private configServ: AgentConfigService,
    private agentBotPageService: AgentBotPageService,
  ) {}

  setAgentCreatorId(id: string) {
    this.agentCreatorId = id;
  }

  /** 检查触发点击事件的元素类名，是否被包含在一个特定的列表中。用于模拟tip组件的外侧点击API  */
  hasTargetClass(target: HTMLElement, classes: string[]): boolean {
    const targetClassList = target.classList;
    return classes.some((className) => targetClassList.contains(className));
  }

  getTagStyle(type: string) {
    let backgroundColor = 'rgb(236, 239, 255)';
    let borderColor = 'rgb(217, 224, 255)';
    let fontColor = 'rgb(37, 43, 58)';

    if (type === 'primary') {
      backgroundColor = 'rgb(236, 239, 255)';
      borderColor = 'rgb(217, 224, 255)';
    } else if (type === 'success') {
      backgroundColor = 'rgb(240, 249, 235)';
      borderColor = 'rgb(225, 243, 216)';
    } else if (type === 'info') {
      backgroundColor = 'rgb(244, 244, 245)';
      borderColor = 'rgb(233, 233, 235)';
    } else if (type === 'disabled') {
      backgroundColor = 'rgb(247, 247, 249)';
      borderColor = 'rgba(0, 0, 0, 0)';
      fontColor = 'rgb(184, 186, 191)';
    }

    return {
      'background-color': backgroundColor,
      'border-color': borderColor,
      color: fontColor,
    };
  }

  getAppStoreTagStyle(type: string) {
    let backgroundColor = '#f5f5f5';
    let borderColor = '#f5f5f5';
    let fontColor = '#595959';

    if (type === 'selected') {
      backgroundColor = '#1476ff';
      borderColor = '#1476ff';
      fontColor = '#fff';
    } else if (type === 'unselected') {
      backgroundColor = '#f5f5f5';
      borderColor = '#f5f5f5';
      fontColor = '#595959';
    } else if (type === 'disabled') {
      backgroundColor = 'rgb(247, 247, 249)';
      borderColor = 'rgba(0, 0, 0, 0)';
      fontColor = 'rgb(184, 186, 191)';
    }

    return {
      'background-color': backgroundColor,
      'border-color': borderColor,
      color: fontColor,
    };
  }

  /** 构造Prompt builder顶部的tags数组 */
  handlePrompttags(prompt: string): any {
    // 匹配所有以##开头，以换行符结束的字符串
    const regex = /##(.*?)\n/g;
    const matches = [];
    let match;
    while ((match = regex.exec(prompt)) !== null) {
      if (match) {
        matches.push(match[1]);
      }
    }

    const filteredMatches = matches.filter((item) => {
      return (
        item &&
        !item.includes('#') &&
        typeof item !== 'undefined' &&
        item.trim() !== ''
      );
    });

    const types = ['primary', 'success', 'info'];
    return filteredMatches.map((item, index) => {
      const type = types[index % types.length];
      return {
        name: item,
        type: type,
      };
    });
  }

  /** 获取当前激活态的Tab类型。如个人插件 或 预置插件，预置MCP服务 或 个人MCP服务 */
  getCurrentTabId(
    arr: { active: boolean }[],
    firstTab: EPluginCategoryTabId,
    secondTab: EPluginCategoryTabId,
    shareTab: EPluginCategoryTabId,
  ): EPluginCategoryTabId {
    if (arr[0]?.active === true) {
      return firstTab;
    } else if (arr[1]?.active === true) {
      return secondTab;
    } else if (arr[2]?.active === true) {
      return shareTab;
    } else {
      return firstTab;
    }
  }

  /** 针对/v1/myAgent接口解构出来的字段值是null，进行赋初值。避免Angular变更检测失效 */
  handleDefaultValues(data: any) {
    let {
      workflows,
      workflow_switch_enabled,
      scheduling_mode,
      knowledge_repos,
      instructions,
      prologue,
      suggest_queries,
      additional_questions_config,
      memory_variables,
      tools,
      trigger_list,
      // eslint-disable-next-line prefer-const
      knowledge_retrieve_policy,
      mcp_servers,
      voice_interaction,
      content_review,
      safety_barrier,
      agent_variables,
      input_variables,
      memory_config,
      scenes,
      skills
    } = data;

    instructions = instructions || '';
    workflows = workflows || [];
    workflow_switch_enabled = workflow_switch_enabled || false;
    scheduling_mode = scheduling_mode || '';
    knowledge_repos = knowledge_repos || [];
    memory_variables = memory_variables || [];
    agent_variables = agent_variables || [];
    input_variables = input_variables|| []
    memory_config = memory_config || { long_term_memory: false };
    prologue = prologue || '';
    suggest_queries = suggest_queries || [];
    additional_questions_config = additional_questions_config || {};
    tools = tools || [];
    trigger_list = trigger_list || [];
    mcp_servers = mcp_servers || [];
    voice_interaction = voice_interaction ?? {
      language: '',
      timbre: '',
      domain: '',
    };
    content_review = content_review || {};
    safety_barrier = safety_barrier || false;
    return {
      instructions,
      workflows,
      workflow_switch_enabled,
      scheduling_mode,
      knowledge_repos,
      prologue,
      suggest_queries,
      additional_questions_config,
      memory_variables,
      tools,
      trigger_list,
      knowledge_retrieve_policy,
      mcp_servers,
      voice_interaction,
      content_review,
      safety_barrier,
      agent_variables,
      input_variables,
      memory_config,
      scenes: scenes || [],
      skills: skills || []
    };
  }

  /**
   * 若Agent配置的modelConfig是空对象 或 无法在availableModels数组中查到和modelConfig.model_deployment_id同名的对象
   * 则取availableModels数组中的第一个对象，作为modelConfig的值
   */
  updateModelConfig(modelConfig: any, availableModels: any[]) {
    let modelConfigUpdated: any;
    let modelSelected = '';
    const modelInfo = availableModels.filter(
      (model: any) =>
        model.model_deployment_id === modelConfig.model_deployment_id,
    );
    if (
      modelConfig?.model_name &&
      modelConfig?.model_name !== '' &&
      modelInfo.length > 0
    ) {
      modelConfigUpdated = {
        service_name: modelInfo[0].service_name,
        ...modelConfig,
        isUpdated: false,
      };
    } else {
      modelConfigUpdated = {
        ...availableModels[0],
        isUpdated: true,
      };
    }
    modelSelected =
      modelConfigUpdated?.service_name || this.i18n.transform('model_nodata');
    return { modelConfigUpdated, modelSelected };
  }

  /** 应用卡片页，已发布和未发布的icon图标 */
  getAgentStatusIcon(node_status: string): string {
    const svgMap = {
      published: `${Network.ASSETS_PATH}agent-center/images/status-published.svg`,
      draft: `${Network.ASSETS_PATH}agent-center/images/status-unpublished.svg`,
    };

    return svgMap[node_status];
  }

  /** 知识型Agent发布状态的中英文映射 */
  getAgentStatusMap(status: string): string {
    switch (status) {
      case 'draft': {
        return this.i18n.transform('unpublished');
      }
      case 'published': {
        return this.i18n.transform('released');
      }
      default: {
        return '';
      }
    }
  }

  /** tip的content取的是innerHTML，保留innerHTML样式，同时反转义<或>，避免出现&lt;等 */
  decodeinnerHTML(innerHTML: any) {
    const tipDecode = document.createElement('textarea');
    tipDecode.innerHTML = innerHTML;
    return tipDecode.value;
  }

  /** 在首页和聊天页的输入框中，ctrl+enter——换行，enter——发送问题 */
  handleKeyboardEvent(component: any, event: KeyboardEvent) {
    if (event.key === 'Enter') {
      if (event.ctrlKey) {
        // ctrl+enter
        component.questionInputed += '\n';
      } else {
        component.sendQuestion();
      }
      event.preventDefault();
    }
  }

  /** 对话型——使用正则匹配，获取每个流式块的content值 */
  processEventData(eventData: any) {
    const chunkDataObject = this.processEventDataObject(eventData);
    if (chunkDataObject === 'session.message.completed') {
      return '';
    }

    const reg = /"content":"(?<content>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"content":"${currentStr[1]}"}`); // 可能会有JSON解析失败的风险
      return result.content;
    }
    return '';
  }

  /** 对话型——使用正则匹配，获取每个流式块的object值 */
  processEventDataObject(eventData: any) {
    const reg = /"object":"(?<object>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"object":"${currentStr[1]}"}`);
      return result.object;
    }
    return '';
  }

  /** 发送新问题时，抽离chatLoop数组每个对象的初始字段值 */
  createChatItem(questionInputed: string) {
    return {
      loading: true,
      showQuestion: questionInputed.trim(),
      showAnswer: undefined,
      showBottomBtns: false,
      isTimeoutOrError: false,
      chunkIds: [],
      showCopiedTip: false,
      passContentReview: true,
      isPopconfirmOpen: false,
      isClickLikeBtn: false,
      isClickDislikeBtn: false,
    };
  }

  /** 处理Agent流式接口调用插件/工作流能力的3种颜色变化 */
  getColor(content: any): string {
    if (content?.isRuning) {
      return 'rgb(20, 118, 255)';
    } else {
      return content?.workflowState === 'error' ? 'red' : 'rgb(92, 179, 0)';
    }
  }

  /** 导出文件的时间格式化为YYYY-MM-DD-hh-mm-ss */
  getFormattedDateTime(): string {
    const date = new Date();
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // 月份从 0 开始计数，因此需要加 1
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${year}-${month}-${day}-${hours}-${minutes}-${seconds}`;
  }

  createTip(descTipHostArray: any[], tipService: any) {
    setTimeout(() => {
      descTipHostArray.forEach((tipHost: any) => {
        if (tipHost) {
          tipService.create(tipHost.nativeElement, {
            position: 'left',
            trigger: 'mouse',
            showFn: (): any => {
              const isOverflow = this.isLongTextOverflowServe.isTextOverflow(
                tipHost?.nativeElement,
                40,
              );
              const tipText = isOverflow
                ? this.decodeinnerHTML(tipHost.nativeElement.innerHTML)
                : '';
              return { content: tipText, context: tipText };
            },
          });
        }
      });
    }, 0);
  }

  /** 根据复杂参数类型，获取对应的 JSON Schema */
  getJSONSchemaByType(type: string): any {
    switch (type) {
      case 'object': {
        return this.toolServ.FlowObjectJSONSchema;
      }
      case 'array<integer>': {
        return this.toolServ.FlowIntegerArrayJSONSchema;
      }
      case 'array<number>': {
        return this.toolServ.FlowFloatArrayJSONSchema;
      }
      case 'array<string>': {
        return this.toolServ.FlowStringArrayJSONSchema;
      }
      case 'array<boolean>': {
        return this.toolServ.FlowBooleanArrayJSONSchema;
      }
      case 'array<object>': {
        return this.toolServ.FlowObjectArrayJSONSchema;
      }
      default:
        return null;
    }
  }

  /** 根据复杂参数类型和名称，获取对应的模型 URI */
  getModelUriByType(valueType: string, name: string, uriType?: string): any {
    // 增加uri前缀用于区分开始节点和记忆变量同时渲染，且相同的参数名称
    const baseUri = `agent://flow/${uriType ? `${uriType}/` : ''}`;

    switch (valueType) {
      case 'object': {
        return monaco.Uri.parse(`${baseUri}object-${name}.json`);
      }
      case 'array<integer>': {
        return monaco.Uri.parse(`${baseUri}integerArr-${name}.json`);
      }
      case 'array<number>': {
        return monaco.Uri.parse(`${baseUri}floatArr-${name}.json`);
      }
      case 'array<string>': {
        return monaco.Uri.parse(`${baseUri}stringArr-${name}.json`);
      }
      case 'array<boolean>': {
        return monaco.Uri.parse(`${baseUri}booleanArr-${name}.json`);
      }
      case 'array<object>': {
        return monaco.Uri.parse(`${baseUri}objectArr-${name}.json`);
      }
      default:
        return null;
    }
  }

  /** 根据运行状态，返回按钮文本 */
  runFlowButtonText(
    isRetryRunning: boolean,
    isFlowRunFailed: boolean,
    isRequesting: boolean,
    type?: string,
  ): string {
    if (isRetryRunning || isFlowRunFailed) {
      return this.i18n.transform('start_running');
    }
    return this.getButtonText(isRequesting, type);
  }

  private getButtonText(isRequesting: boolean, type: string): string {
    if (isRequesting) {
      return this.i18n.transform('running');
    }
    if (type === 'async') {
      return this.i18n.transform('save_run');
    }
    return this.i18n.transform('start_running');
  }

  async doTriggerSave(agentId: string, config: IUpdateSingleAgentConfig) {
    if (this.ctxServ.user.userId !== this.agentCreatorId) {
      if (this.configServ.getConfigs().enable_edit_in_workspace === false) {
        return;
      }
    }
    if (this.canTriggerSave) {
      this.handleInitTriggerSaveQueue();
      return;
    }
    this.canTriggerSave = true;
    const update_time = this.agentDataServe.getAutoSaveTime();
    config.data.update_time = update_time;
    this.service
      .triggerSave(agentId, config.data)
      .then((res: any) => {
        // 刷新service的trigger save时间值
        this.agentDataServe.setAutoSaveTime(res.update_time);
        this.agentDataServe.setAgentStatus(res.status);
        this.agentBotPageService.agentDetail.set(res);
        config?.successCb?.();
      })
      .catch((error) => {
        config?.failCb?.(error);
      })
      .finally(() => {
        config?.finallyCb?.();
        this.handleFinallyTriggerSave(agentId, config);
      });
  }

  private handleInitTriggerSaveQueue() {
    this.triggerSaveQueue.push(this.triggerSaveIndex);
  }

  private handleFinallyTriggerSave(
    agentId: string,
    config: IUpdateSingleAgentConfig,
  ) {
    this.canTriggerSave = false;
    this.triggerSaveQueue.shift();
    if (this.triggerSaveQueue.length > 0) {
      this.doTriggerSave(agentId, config);
      this.triggerSaveQueue.length = 0;
    }
  }

  public feedbackOptions = [
    {
      id: 1,
      label: this.i18n.transform('feedback_options_off_topic'),
    },
    {
      id: 2,
      label: this.i18n.transform('feedback_options_missing_content'),
    },
    {
      id: 3,
      label: this.i18n.transform('feedback_options_unhelpful'),
    },
    {
      id: 4,
      label: this.i18n.transform('feedback_options_misunderstood_intent'),
    },
    {
      id: 5,
      label: this.i18n.transform('feedback_options_logical_error'),
    },
    {
      id: 6,
      label: this.i18n.transform('feedback_options_bias/discrimination'),
    },
    {
      id: 7,
      label: this.i18n.transform('feedback_options_factual_error'),
    },
    {
      id: 8,
      label: this.i18n.transform('feedback_options_other_reason'),
    },
  ];
}

export function getValidatedFiles(
  rawFiles: FileList,
  kbFileType: 'document' | 'sheet',
): File[] {
  const fileArr = Array.from(rawFiles);
  const files: File[] = [];

  // 1024 * 1024 * 10 & 1024 * 1024 * 10
  const limit = kbFileType === 'document' ? 10 : 10_485_760;

  fileArr.forEach((file) => {
    if (file.size > limit) {
      MessageComponent.showError(
        i18next.t('file_oversize', { name: file.name }),
      );
    } else {
      files.push(file);
    }
  });

  return files;
}

export function getDayOfWeekLabel(dayOfWeek: string): string {
  switch (dayOfWeek) {
    case '0':
      return i18next.t('commonlogicagent_5', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    case '1':
      return i18next.t('commonlogicagent_6', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });

    case '2':
      return i18next.t('commonlogicagent_7', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    case '3':
      return i18next.t('commonlogicagent_8', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    case '4':
      return i18next.t('commonlogicagent_9', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    case '5':
      return i18next.t('commonlogicagent_10', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    case '6':
      return i18next.t('commonlogicagent_11', {
        ns: [I18nNamespace.COMMON, I18nNamespace.AGENT_CENTER],
      });
    default:
      throw new Error('');
  }
}

/** 根据悬停和valid属性，获取卡片的背景色 */
export function getCardBgColor(item: { valid?: boolean; hover?: boolean, isKnowledge?: boolean }) {
  const isValid = item.valid ?? true;
  const isHover = item.hover ?? false;
  const isKnowledge = item.isKnowledge ?? false;

  if (!isValid && isKnowledge) {
    return '#feeeea';
  }
  if (isHover && isValid) {
    return '#f0f7ff';
  }
  return '#fafafa';
}

export interface AssertSquareTagType {
  id: string;
  name: string;
  name_en?: string;
  description: string;
  library_type: string;
  created_on: number;
  updated_on: number;
  active: boolean;
}
