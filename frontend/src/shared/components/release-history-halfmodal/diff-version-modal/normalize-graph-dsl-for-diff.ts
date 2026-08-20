/**
 * 阶段二：图 DSL 顺序规范化纯函数（只用于版本对比展示，不修改输入、不改保存数据）。
 *
 * 背景：工作流/多智能体控制器保存数据来自 graph.toJSON().cells，X6 cell collection 会随 zIndex
 * 变化重新排序（点击/拖动节点调 toFront()），导致下次保存的 nodes/edges/comments 顺序抖动，
 * 直接 JSON.stringify 会产生大量数组搬移噪声。
 *
 * 规则（参考《版本对比diff节点顺序稳定化方案》）：
 * 1. 输入只读，返回全新 JSON 树。
 * 2. 所有普通对象递归按 key 做二值字符串排序（稳定 layouts 等对象键，坐标值保留）。
 * 3. 仅"根对象"的 nodes、comments 按 String(id) 排序；id 缺失/重复时以规范化完整对象 JSON 兜底。
 * 4. 仅"根对象"的 edges 按 [source, target, branch, exception_branch] 元组排序，再以完整 edge JSON 兜底。
 * 5. exception_branch 必须进入边身份（不能当可选）。
 * 6. 其它数组（含 configs.agents、branches、inputs、outputs、memory、trigger_list、控制器 global_variables）
 *    保持元素先后顺序，只规范化元素内部对象 key。
 * 7. 嵌套字段即使也叫 nodes/edges/comments 也不得排序（仅 path.length === 1 的顶层字段）。
 * 8. 二值字符串比较，不依赖 localeCompare。
 */

type JsonObject = Record<string, unknown>;

const compareText = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

const canonicalJson = (value: unknown): string => JSON.stringify(value);

const compareBy = <T>(left: T, right: T, primaryKey: (value: T) => string): number => {
  const primary = compareText(primaryKey(left), primaryKey(right));
  return primary !== 0 ? primary : compareText(canonicalJson(left), canonicalJson(right));
};

/** 边排序键：[source, target, branch, exception_branch]，序列化为确定性 JSON 字符串。 */
const edgeKey = (edge: any): string =>
  JSON.stringify([
    String(edge?.source ?? ''),
    String(edge?.target ?? ''),
    String(edge?.branch ?? ''),
    edge?.exception_branch === true ? 1 : 0,
  ]);

function canonicalize(value: unknown, path: string[] = []): unknown {
  if (Array.isArray(value)) {
    const items = value.map((item) => canonicalize(item, [...path, '[]']));
    // 仅根对象的顶层字段（path.length === 1）参与白名单排序
    const topLevelField = path.length === 1 ? path[0] : undefined;

    if (topLevelField === 'nodes' || topLevelField === 'comments') {
      return [...items].sort((a: any, b: any) => compareBy(a, b, (item) => String(item?.id ?? '')));
    }
    if (topLevelField === 'edges') {
      return [...items].sort((a: any, b: any) => compareBy(a, b, edgeKey));
    }
    // 业务数组：只规范化元素内部对象键，不改元素先后顺序
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

/** 只用于版本对比展示：把图 DSL（workflow_details / 控制器 details）转为顺序稳定的等价 JSON 树。不修改输入。 */
export function normalizeGraphDslForDiff(details: unknown): unknown {
  return canonicalize(details);
}

/** 单一接入点：规范化后美化序列化。出问题时可退回 JSON.stringify(dsl, null, 2) 而不关 Diff 功能。 */
export function serializeGraphDslForDiff(dsl: unknown): string {
  return JSON.stringify(normalizeGraphDslForDiff(dsl), null, 2);
}
