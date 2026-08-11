import { Injectable } from '@angular/core';
import { ContextService } from '@services/context.service';
import { BehaviorSubject } from 'rxjs';
import { CommonService } from "@services/common.service";

export interface ITimbreOption {
  property: string;
  scene: string;
  type: string;
  name: string;
  language: 'chinese' | 'english';
}

export interface IAgentConfigs {
  knowledge_repo_url?: string;
  retrieve_knowledge_repo_url?: string;
  memory_user_profile_enable?: boolean; // 是否支持记忆中的用户画像
  son_workflow_level_limit?: boolean;
  opsvc_project_id?: string;
  user_query_limit?: number;
  stream_first_chunk_timeout?: number;
  stream_interval_timeout?: number;
  site?: string; // 表示站点名
  agent_tool_bound_limit?: number;
  agent_workflow_bound_limit?: number;
  agent_knowledge_bound_limit?: number;
  agent_mcp_bound_limit?: number;
  ltm_enable?: boolean; // 长期记忆节点是否可见
  knowledge_recall_threshold_min?: number; // 知识库检索（相关度阈值、FAQ直出阈值）最小值
  knowledge_recall_threshold_max?: number; // 知识库检索（相关度阈值、FAQ直出阈值）最大值
  lakesearch_faq_enable?: boolean; // lakesearch特性开关
  block_nodes?: string[]; // 被屏蔽的节点类型，大小写不敏感
  agent_tool_priority_enable?: boolean; // 工具优先调度模式是否可见
  knowledge_source?: 'KooSearch' | 'LakeSearch' | 'AgentBaseRag' | 'CUSTOM';
  web_page_enable?: boolean; // 单智能体和工作流的发布网页渠道是否可见
  outer_app_enable?: boolean; // 百宝箱外部应用Tab是否可见
  audio_support_interaction?: boolean; // 语音服务是否可用
  audio_english_timbre?: ITimbreOption[]; // 英文音色
  audio_chinese_timbre?: ITimbreOption[]; // 中文音色
  prompt_engineering_enable?: boolean; // 提示词工程是否可见
  runtime_api_endpoint_prefix?: string; //api调用地址前缀
  enable_code_local?: boolean; //沙箱开关
  env_sandbox_enable?:boolean; //hc屏蔽沙箱
  code_env_options?:string[];
  his_openai_enable?:boolean;
  code_def_env?:string;
  workflow_async_enable?:boolean;
  plugin_publish_choice?:boolean;
  prompt_max_length?:number; //提示词最大长度
  platform_provider_id?:string; //推荐供货商id
  display_show_model_status?:boolean; //展示模型状态
  asset_app_free_trial_quota_limit?:number;//体验额度
  hmac_auth_enabled?:boolean;//hmac 认证
  [key: string]: any;
}

export interface MaxReplySetting {
  min: number;
  max: number;
  default: number;
}

@Injectable({
  providedIn: 'root',
})
export class AgentConfigService {
  private readonly configs$ = new BehaviorSubject<IAgentConfigs>({});

  constructor(
    private ctxServ: ContextService,
    private commonService: CommonService,
  ) {
  }

  public setConfigs(configs: IAgentConfigs) {
    this.configs$.next(configs);
  }
  data$ = this.configs$.asObservable();

  public getConfigs(): IAgentConfigs {
    return this.configs$.getValue();
  }

  public getConsoleJumpKbUrlPrefix() {
    const path = window.location.href;
    const service = 'agent-center';
    const serviceIndex = path.indexOf(service);
    return path.substring(0, serviceIndex + service.length);
  }

  public getPOCJumpKbUrlPrefix(kbId: string) {
    const repoUrlPrefix = this.configs$.getValue()?.retrieve_knowledge_repo_url;
    if (repoUrlPrefix) {
      return `${repoUrlPrefix}?indexName=${kbId}&userId=${this.ctxServ.user.userId}`;
    }

    return '';
  }

  public faqEnable() {
    const {lakesearch_faq_enable} = this.getConfigs();
    return lakesearch_faq_enable;
  }

  public knowledgeSource() {
    const { knowledge_source } = this.getConfigs();
    return knowledge_source;
  }

  public createKnowledgeBase() {
    const {knowledge_internal_enabled} = this.getConfigs();
    return knowledge_internal_enabled;
  }

  public isSupportSharedKb() {
    const { share_knowledge_enabled } = this.getConfigs();
    return share_knowledge_enabled;
  }

  public voiceEnable() {
    //语音服务是否可用
    const {audio_support_interaction} = this.getConfigs();
    return audio_support_interaction;
  }

  public longTermMemoryEnable() {
    const { long_term_memory_enabled } = this.getConfigs();
    return long_term_memory_enabled;
  }

  public isSupportUserPersona() {
    const { memory_user_profile_enable } = this.getConfigs();
    return true;
  }

  /** 记忆库功能开关，由后端 memory_repo_enable 配置控制 */
  public isSupportMemoryInSingleAgent() {
    const { memory_repo_enable } = this.getConfigs();
    return !!memory_repo_enable;
  }
}
