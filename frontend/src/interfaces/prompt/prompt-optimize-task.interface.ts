export enum PromptType {
  TEXT = 'text',
  MULTI = 'multi',
}

export enum VariableType {
  IMAGE = 'image',
  TEXT = 'text',
}

export interface IVariable {
  type: VariableType;
  value: string;
}

export enum TaskType {
  OBJECTIVE = 'objective',
  SUBJECTIVE = 'subjective',
}

interface PromptExampleItemUseCase {
  name: string;
  type: VariableType;
  content: string;
}

export interface PromptExampleItem {
  title: string;
  value: string;
  type: PromptType;
  taskType: TaskType;
  scoringCriteria?: string;
  backgroundPrompt?: string;
  useCases?: Array<PromptExampleItemUseCase[]>;
}

export interface IConfigConstants {
  [key: string]: {
    backgroundPromptPlaceholder: string;
    scoringCriteriaPlaceholder: string;
    promptExample: Array<PromptExampleItem>;
  };
}

export interface OptimizeTaskDraft {
  promptId: string;
  name: string;
  desc: string;
  /** 执行时间毫秒串；任务无排程时为 null（后端创建/更新均允许 null），不再以空串冒充 */
  execTime: string | null;
  ptType: string;
  ptText: string;
  ptVars: string;
  ptObject: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  assitantObject: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  maxIterNum: number;
  targetAcc: string;
  showCaseNum: number;
  targetType: string;
  scoreStandard: string;
  backKnowledge: string;
  created_time?: string;
  updatedTime?: string;
}

export interface OptimizeTask {
  prompt_id: string;
  name: string;
  desc: string;
  exec_time: string;
  pt_type: string;
  pt_text: string;
  pt_vars: [
    {
      name: string;
      type: VariableType;
    },
  ];
  pt_model_config: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  exec_object_config: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  max_iter_num: number;
  target_acc: number;
  show_case_num: number;
  target_type: string;
  score_standard: string;
  back_knowledge: string;
  created_time?: string;
  updatedTime?: string;
}

export interface OptimizeTaskRunningDetail extends OptimizeTask {
  status: 'SUCCESS' | 'DRAFT' | 'RUNNING' | 'FAILED' | 'WAITING' | 'PAUSE';
  progress_rate: number;
  iteration_results: {
    current_best_prompt: string;
    iteration_info_list: Array<{
      iteration_round: number;
      optimized_prompt: string;
      success_rate: number;
    }>;
  };
}

export interface OptimizeUseCase {
  id?: string;
  content: string;
}

export interface OptimizeTaskItem {
  /**
   * 查询列表中的每一条数据
   */

  id: string;
  prompt_id: string;
  jiuwen_task_id: string;
  name: string;
  desc: string;
  pt_type: string;
  pt_text: string;
  pt_vars: [
    {
      name: string;
      type: string;
    },
  ];
  exec_time: string;
  pt_model_config: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  exec_object_config: {
    model: string;
    exec_type: string;
    top_p?: number;
    temperature?: number;
    max_tokens?: number;
  };
  max_iter_num: number;
  target_acc: number;
  show_case_num: number;
  target_type: string;
  score_standard: string;
  back_knowledge: string;
  progress_rate: number;
  status: string;
  message: string;
  project_id: string;
  workspace_id: string;
  created_time: string;
  creator: string;
  creator_id: string;
  updatedTime: string;
  actionList: Array<any>;
}

export interface UseCase {
  id?: string;
  content: string;
}
