import { Network } from '@model';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { WORKFLOW_SVGS } from './flow.const';
import i18next from 'i18next';

/**
 * 工作流调试的通用逻辑
 */
const commonLogic = {
  /** 使用正则匹配，获取每个流式块的event值 */
  extractEventFromStream(eventData: any) {
    const reg = /"event":"(?<event>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"event":"${currentStr[1]}"}`);
      return result.event;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的node_id值 */
  extractNodeIdFromStream(eventData: any) {
    const reg = /"node_id":"(?<node_id>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"node_id":"${currentStr[1]}"}`);
      return result.node_id;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的node_name值 */
  extractNodeNameFromStream(eventData: any) {
    const reg = /"node_name":"(?<node_name>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"node_name":"${currentStr[1]}"}`);
      return result.node_name;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的node_type值 */
  extractNodeTypeFromStream(eventData: any) {
    const reg = /"node_type":"(?<node_type>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"node_type":"${currentStr[1]}"}`);
      return result.node_type;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的is_finished值 */
  extractIsFinishedFromStream(eventData: any) {
    const reg = /"is_finished":(?<is_finished>(true|false))/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"is_finished":${currentStr[1]}}`);
      return result.is_finished;
    }
    return false;
  },

  /** 使用正则匹配，获取每个流式块的inputs值 */
  extractInputsFromStream(eventData: any) {
    const reg = /"inputs":({.*?})/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(currentStr[1]);
      return result;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的outputs值 */
  extractOutputsFromStream(eventData: any) {
    const reg = /"outputs":({.*?})/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(currentStr[1]);
      return result;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的status.desc值，包含NodeInfo和WorkflowInfo */
  extractStatusFromStream(eventData: any) {
    const reg = /"status":\{[^{}]*"desc":"(?<desc>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"status_desc":"${currentStr[1]}"}`);
      return result.status_desc;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的start_time值 */
  extractStartTimeFromStream(eventData: any) {
    const reg = /"start_time":(?<start_time>\d+)/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"start_time":"${currentStr[1]}"}`);
      return result.start_time;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的end_time值 */
  extractEndTimeFromStream(eventData: any) {
    const reg = /"end_time":(?<end_time>\d+)/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"end_time":"${currentStr[1]}"}`);
      return result.end_time;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的metadata.tokens值 */
  extractTokensFromStream(eventData: any) {
    const reg = /"metadata":\{[^{}]*"tokens":(?<tokens>\d+)/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"tokens":"${currentStr[1]}"}`);
      return result.tokens;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的text值 */
  extractTextFromStream(eventData: any) {
    const reg = /"text":"(?<text>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"text":"${currentStr[1]}"}`);
      return result.text;
    }
    return '';
  },

  /** 使用正则匹配，获取每个流式块的event值 */
  extracteErrorMsgFromStream(eventData: any) {
    const reg = /"error_message":"(?<error_message>[^"]*)"/;
    let currentStr = eventData.match(reg);
    if (currentStr) {
      let result = JSON.parse(`{"error_message":"${currentStr[1]}"}`);
      return result.error_message;
    }
    return '';
  },

  /** 调用链，获取不同类型节点的icon */
  getNodeIcon(node_type: string): string {
    const svgMap = {
      Start: cdnAssetUrl('assets/agent-center/flow/Start.svg'),
      LLM: cdnAssetUrl('assets/agent-center/flow/LLM.svg'),
      Code: cdnAssetUrl('assets/agent-center/flow/Code.svg'),
      Branch: cdnAssetUrl('assets/agent-center/flow/Branch.svg'),
      IntentDetection: cdnAssetUrl('assets/agent-center/flow/Intent.svg'),
      Questioner: cdnAssetUrl('assets/agent-center/flow/Questioner.svg'),
      Plugin: cdnAssetUrl('assets/agent-center/flow/Plugin.svg'),
      Mcp: cdnAssetUrl('assets/agent-center/images/service-default.svg'),
      mcp: cdnAssetUrl('assets/agent-center/images/service-default.svg'),
      End: cdnAssetUrl('assets/agent-center/flow/End.svg'),
      Message: cdnAssetUrl('assets/agent-center/flow/message.svg'),
      StreamTransform: cdnAssetUrl('assets/agent-center/flow/stream-transform.svg'),
      llm: cdnAssetUrl('assets/agent-center/flow/LLM.svg'),
      plugin: cdnAssetUrl('assets/agent-center/flow/Plugin.svg'),
      knowledge: cdnAssetUrl('assets/agent-center/flow/Knowledge.svg'),
      KnowledgeRepo: cdnAssetUrl('assets/agent-center/flow/KnowledgeRepo.svg'),
      Aggregation: cdnAssetUrl('assets/agent-center/flow/Aggregation.svg'),
      Workflow: cdnAssetUrl('assets/agent-center/flow/ChildFlow.svg'),
      Input: cdnAssetUrl('assets/agent-center/flow/Input.svg'),
      Loop: cdnAssetUrl('assets/agent-center/flow/Loop.svg'),
      SetVariable: cdnAssetUrl('assets/agent-center/flow/SetVariable.svg'),
      Http: cdnAssetUrl('assets/agent-center/flow/Http.svg'),
      Agent: cdnAssetUrl('assets/agent-center/flow/Agent.svg'),
      LTM: cdnAssetUrl('assets/agent-center/flow/LTM.svg'),
      ComplexIntentDetection: cdnAssetUrl(
        'assets/agent-center/flow/Intent.svg',
      ),
      IntentDetectionContainer: cdnAssetUrl(
        'assets/agent-center/flow/Intent.svg',
      ),
      LoopInput: cdnAssetUrl('assets/agent-center/flow/Start.svg'),
      LoopOutput: cdnAssetUrl('assets/agent-center/flow/End.svg'),
      QA: cdnAssetUrl('assets/agent-center/flow/QA.svg'),
      Sql: cdnAssetUrl('assets/agent-center/flow/Sql.svg'),
      DataQuery: cdnAssetUrl('assets/agent-center/flow/Sql.svg'),
      StructuredMessagesException: cdnAssetUrl('assets/agent-center/flow/Exception.svg'),
      ParamExtraction: cdnAssetUrl('assets/agent-center/flow/param-extraction.svg'),
      Card:cdnAssetUrl('assets/agent-center/flow/Card.svg'),
      Controller: cdnAssetUrl('assets/agent-center/flow/Controller.svg'),
    };

    return svgMap[node_type];
  },

  /** 调用链，获取节点不同状态的icon */
  getNodeStatus(node_status: string): string {
    const svgMap = {
      waiting: cdnAssetUrl(`assets/agent-center/flow/call-node-loading.svg`),
      loading: cdnAssetUrl(`assets/agent-center/flow/call-node-loading.svg`),
      running: cdnAssetUrl(`assets/agent-center/flow/call-node-loading.svg`),
      succeed: cdnAssetUrl(`assets/agent-center/flow/call-node-success.svg`),
      succeeded: cdnAssetUrl(`assets/agent-center/flow/call-node-success.svg`),
      finished: cdnAssetUrl(`assets/agent-center/flow/call-node-success.svg`),
      aborted: WORKFLOW_SVGS.ValidateAlert,
      failed: WORKFLOW_SVGS.ValidateAlert,
      FAILED: WORKFLOW_SVGS.ValidateAlert,
      exception: WORKFLOW_SVGS.exception,
      exception_stop: WORKFLOW_SVGS.exception,
    };

    return svgMap[node_status];
  },

  /** 计算工作流和调用节点的完成时间 */
  calcElapsedTime(start_time: number, end_time: number): string {
    const elapsed_time = end_time - start_time;
    const abs_elapsed_time = Math.abs(elapsed_time);

    if (abs_elapsed_time >= 60000) {
      const minutes = abs_elapsed_time / 60000;
      return `${elapsed_time < 0 ? '-' : ''}${minutes.toFixed(2)}min`;
    } else if (abs_elapsed_time >= 1000) {
      const seconds = abs_elapsed_time / 1000;
      return `${elapsed_time < 0 ? '-' : ''}${seconds.toFixed(2)}s`;
    } else {
      return `${elapsed_time.toFixed(2)}ms`;
    }
  },

  /** 工作流，获取不同运行状态的字体颜色 */
  getWorkflowStatusDescColor(workflow_status: string): string {
    const colorMap = {
      waiting: '#1476FF',
      loading: '#1476FF',
      running: '#1476FF',
      succeed: '#5CB300',
      succeeded: '#5CB300',
      finished: '#5CB300',
      aborted: '#FF0000',
      failed: '#FF0000',
      FAILED: '#FF0000',
    };

    return colorMap[workflow_status] || '#191919'; // 默认颜色为黑色
  },

  /** 工作流，获取不同运行状态的文字描述 */
  getWorkflowStatusDesc(workflow_status: string): string {
    const colorMap = {
      waiting: 'running',
      loading: 'running',
      running: 'running',
      succeed: 'success',
      succeeded: 'success',
      finished: 'success',
      aborted: 'run_aborted',
      failed: 'fail',
      FAILED: 'fail',
      exception: 'run_exception',
      exception_stop: 'exception_stop',
    };
    return i18next.t(colorMap[workflow_status]) || '';
  },

  /** 将tagId List翻译成对应的中文标签名数组 */
  translateTagsToLabels(tagList: any, tagNameList: any) {
    return tagList
      ?.map(
        (tag: string) =>
          tagNameList.find((item: any) => item.tag_id === tag)?.name,
      )
      .filter((item: any) => item !== undefined);
  },

  /** 安全的JSON解析 */
  stringToObject(s: any) {
    try {
      return JSON.parse(s);
    } catch {
      return {};
    }
  },
};

export default commonLogic;
