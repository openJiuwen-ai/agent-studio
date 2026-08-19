/**
 * 阶段三 3A：单智能体版本业务配置投影。
 *
 * 策略：元数据黑名单 —— 从 AgentInfo 整对象删除元数据字段，剩余业务字段全部自动纳入 Diff。
 * 与工作流/多智能体"整对象提取（workflow_details / details）"同一哲学：后端加业务字段自动进、
 * 前端不改；仅后端加元数据字段时需补黑名单（漏了只是多显示一条噪声差异，可见可接受，
 * 不会漏真实差异）。
 *
 * 准入：sub_type 归一（null / "agent" → common，与后端 AgentImportService 归一一致）；
 * common / planexecute 本阶段开放；deepresearch 暂不开放；未知 sub_type 抛错禁止展示。
 *
 * 代码依据：AgentInfo.java、AgentImportService.uploadAgentDsl 三分支、
 * AgentManagementService.getAgentVersionInfo（版本侧 OBS dsl → AgentInfo + triggerList/updateTime 覆盖）。
 * 字段固化表：工作记录/20260810/2026-08-10-001-阶段三单智能体投影字段固化表.md
 */

/** 单智能体版本业务配置投影 = AgentInfo 整对象 − 元数据黑名单。 */
export type SingleAgentDiffDsl = Record<string, unknown>;

/** 元数据黑名单：从投影中删除，不进入 Diff。字段理由见字段固化表 §3.2。 */
const META_BLACKLIST: readonly string[] = [
  'agent_id', // 智能体唯一标识，对比两侧同体恒同
  'project_id', // 所属项目标识
  'workspace_id', // 工作空间标识
  'tags', // 组织/分类元数据
  'creator', // 发布者名称
  'creator_id', // 发布者 ID
  'create_time', // 创建时间戳
  'update_time', // 更新时间戳（version 侧被 DB 覆盖，版本间恒同）
  'publish_time', // 发布时间戳（版本间不同但属版本管理元数据）
  'url', // 访问地址
  'status', // 运行状态
  'is_template', // 模板标记
  'is_share', // 分享标记
  'channel_type', // 渠道类型
  'free_trial_quota', // 免费试用配额
  'character_dr', // 语义不明（deepresearch 相关），本阶段排除
  'updated_on', // 额外时间戳字段
];

/**
 * 已知业务字段集：仅用于开发期未知字段告警比对，**不用于投影筛选**。
 * 投影靠黑名单删除 —— 字段不在黑名单即纳入。后端新增业务字段会自动进 Diff，
 * 同时此处告警会在开发期提醒确认新字段归属（进黑名单还是保留为业务），避免静默扩展。
 */
const KNOWN_BUSINESS_FIELDS: ReadonlySet<string> = new Set([
  // 基础与类型
  'name', 'type', 'sub_type', 'description', 'icon',
  // 提示与交互
  'instructions', 'prologue', 'suggest_queries', 'additional_questions_config',
  'voice_interaction', 'reference',
  // 模型与调度
  'model_deployment_id', 'model_name', 'service_name', 'model_endpoint', 'model_version',
  'model_type', 'model', 'model_config', 'scheduling_mode', 'plan_qa_independent',
  'plan_model_deployment_id', 'plan_model_name', 'plan_model_type', 'plan_model', 'plan_model_config',
  // 能力引用
  'tools', 'workflows', 'mcp_servers', 'skills', 'knowledge_repos', 'search_engine', 'scenes',
  // 知识与记忆
  'knowledge_retrieve_policy', 'memory_variables', 'memory_config',
  // 变量与触发
  'agent_variables', 'input_variables', 'trigger_list',
  // 安全与其它业务
  'content_review', 'safety_barrier', 'workflow_switch_enabled', 'planning', 'writing_template',
  // details（ControllerVO）：单智能体一般 null，非空则显差异，黑名单不在即纳入
  'details',
]);

/** 归一 sub_type：null / undefined / 空白 / "agent" → "common"（与后端 AgentImportService 归一一致）。 */
function normalizeSubType(raw: unknown): string {
  if (raw === null || raw === undefined) {
    return 'common';
  }
  const s = String(raw).trim();
  if (s === '' || s === 'agent') {
    return 'common';
  }
  return s;
}

/**
 * 从 AgentInfo 响应提取版本业务配置投影（整对象 − 元数据黑名单）。
 * latest（/agents/{id}）与 version（rollbackAgentVersion GET）两侧结构同构，共用同一投影。
 *
 * @throws response 为空、sub_type 为 deepresearch 或未知时抛错（本阶段暂不开放 deepresearch，未知类型禁止展示）
 */
export function extractSingleAgentDsl(response: unknown): SingleAgentDiffDsl {
  if (!response || typeof response !== 'object') {
    throw new Error('agent 响应为空，无法对比');
  }

  const source = response as Record<string, unknown>;
  const subType = normalizeSubType(source.sub_type);
  if (subType === 'deepresearch') {
    throw new Error('deepresearch 子类型暂不支持对比');
  }
  if (subType !== 'common' && subType !== 'planexecute') {
    throw new Error(`不支持的智能体子类型: ${subType}`);
  }

  // 浅拷贝后删除元数据黑名单字段（不修改原 response；嵌套业务对象为引用，仅用于只读序列化）
  const projected: Record<string, unknown> = { ...source };
  for (const key of META_BLACKLIST) {
    delete projected[key];
  }
  // 归一写回 sub_type（null / "agent" → common），使投影后两侧 sub_type 一致，避免历史值噪声
  projected.sub_type = subType;

  // 开发期：未知字段告警（剩余字段不在已知业务字段集 → 提醒确认归属，避免静默扩展）
  if (typeof console !== 'undefined' && console.warn) {
    for (const key of Object.keys(projected)) {
      if (!KNOWN_BUSINESS_FIELDS.has(key)) {
        console.warn(
          `[single-agent-dsl-for-diff] 未知字段 "${key}" 不在已知业务字段集，` +
            `请确认该字段应加入 META_BLACKLIST（元数据）还是 KNOWN_BUSINESS_FIELDS（业务）。`,
        );
      }
    }
  }

  return projected;
}

type JsonObject = Record<string, unknown>;

const compareText = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

/**
 * 引用集合排序白名单：字段名 → 元素稳定身份字段名。
 * 已确认这 6 个引用集合顺序不影响 runtime 行为，可安全按 ID 排序（依据：后端 runtime 查证）：
 * - Java IR 构建（IrAdapterService.java）对 tools/workflows/mcp_servers/skills 都从 DB mapping 表
 *   重新查（selectByAppIdAndResourceType），不迭代 AgentInfo 对应列表 → AgentInfo 列表顺序不流入 IR。
 * - openjiuwen runtime 用 dict by name/id 存（ability_manager.py），按需查；显式 reorder 才改可见序。
 * - knowledge_repos 转 search_datasets id 集合；scenes LLM 语义匹配选 id + id 回找
 *   （scenes 顺序只影响 plan_execute 匹配 prompt 的场景列举序，不影响 LLM 选哪个场景）。
 * 因此按 ID 排序消除保存路径噪声，不改变 runtime 调用。详见工作记录/20260810 字段固化表。
 */
const SORTABLE_REF_FIELDS: ReadonlyMap<string, string> = new Map<string, string>([
  ['tools', 'tool_id'],
  ['workflows', 'workflow_id'],
  ['mcp_servers', 'mcp_server_id'],
  ['skills', 'skill_id'],
  ['knowledge_repos', 'knowledge_repo_id'],
  ['scenes', 'id'],
]);

/**
 * 阶段三 3B：单智能体 DSL 顺序规范化纯函数（只用于版本对比展示，不修改输入、不改保存数据）。
 *
 * 规则（计划 §6.4）：
 * 1. 输入只读，返回全新 JSON 树。
 * 2. 所有普通对象递归按 key 二值字符串排序 —— 消除对象 key 插入顺序噪声
 *    （latest buildComplexAgentInfo 与 version OBS json parse 的 key 顺序可能不同）。
 * 3. 业务数组默认保序：suggest_queries / agent_variables / input_variables /
 *    memory_variables / trigger_list 等有展示/调度语义，换序应产生 Diff。
 * 4. 引用集合按白名单 SORTABLE_REF_FIELDS 中的 ID 排序（tools/workflows/mcp_servers/
 *    skills/knowledge_repos/scenes），缺失/重复 ID 用完整规范化对象 JSON 兜底，不丢元素、不去重。
 *    仅"顶层"（path.length === 1，即根对象直接字段）的引用集合排序；嵌套同名数组
 *    （如 some_config.tools）不排序 —— 传递 path + '[]' 标记数组层级以区分顶层与嵌套。
 */
function canonicalize(value: unknown, path: string[] = []): unknown {
  if (Array.isArray(value)) {
    const items = value.map((item) => canonicalize(item, [...path, '[]']));
    // 仅顶层字段（path.length === 1，数组所属字段在根对象直接下）命中白名单才排序
    const topLevelField = path.length === 1 ? path[0] : undefined;
    const idField = topLevelField ? SORTABLE_REF_FIELDS.get(topLevelField) : undefined;
    if (idField) {
      const idKey = (item: any): string => String(item?.[idField] ?? '');
      return [...items].sort((a: any, b: any) => {
        const primary = compareText(idKey(a), idKey(b));
        return primary !== 0 ? primary : compareText(JSON.stringify(a), JSON.stringify(b));
      });
    }
    return items;
  }
  if (value && typeof value === 'object') {
    return Object.keys(value as JsonObject)
      .sort(compareText)
      .reduce<JsonObject>(
        (result, key) => {
          result[key] = canonicalize((value as JsonObject)[key], [...path, key]);
          return result;
        },
        {},
      );
  }
  return value;
}

/** 只用于版本对比展示：把单智能体投影 DSL 转为对象 key 顺序稳定、引用集合按 ID 排序的等价 JSON 树。不修改输入。 */
export function normalizeSingleAgentDslForDiff(dsl: unknown): unknown {
  return canonicalize(dsl);
}

/**
 * 序列化接入点：投影 → 规范化 → 美化。
 * 出问题时可退回 JSON.stringify(extractSingleAgentDsl(response), null, 2) 而不关 Diff 功能；
 * 也可单独回滚 normalize（保留原始对比），不影响投影与黑名单。
 */
export function serializeSingleAgentDslForDiff(response: unknown): string {
  return JSON.stringify(normalizeSingleAgentDslForDiff(extractSingleAgentDsl(response)), null, 2);
}
