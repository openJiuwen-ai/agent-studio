/**
 * 判断 node:click 防抖窗口内的二次点击是否应令旧节点的延迟打开任务失效。
 *
 * 背景：node:click 在 300ms 防抖窗口（nodeClick === true）内的二次点击会直接
 * return，导致为新节点调度的 scheduleOpenNodeModal 不被调用、旧节点 250ms 延迟
 * 打开的 token 不被刷新，250ms 后仍会弹出旧节点配置面板。
 *
 * 本函数抽出“是否需要失效”的纯判定核心，便于在纯 Node 环境下覆盖同节点连击 /
 * 快速切换 / 首次点击等场景（项目 Karma 为空壳、无 Chrome，无法跑 Angular/X6
 * 组件级测试，故沿用 editable-target.util 的纯函数抽离方式）。
 *
 * 规则：
 * - 首次点击（未进入防抖）或本次点击无节点 id：不失效（scheduleOpenNodeModal
 *   自身的 token++ 已能令旧任务失效，无需额外处理）。
 * - 同节点连击：不失效，保留旧节点的延迟打开，使“单击当前节点 250ms 后打开
 *   配置”的正常行为不被粗暴取消。
 * - 切换到不同节点：令旧节点延迟打开失效，避免 250ms 后弹出旧节点面板。
 */
export interface PendingOpenInvalidationInput {
  /** 当前是否处于 300ms 防抖窗口（nodeClick === true）。 */
  isDebouncing: boolean;
  /** 本次点击的节点 id。 */
  clickedNodeId: string | undefined;
  /** 开始本轮防抖窗口时所点击的节点 id（同窗口内不变）。 */
  lastClickedNodeId: string | undefined;
}

export function shouldInvalidatePendingOpen(
  input: PendingOpenInvalidationInput,
): boolean {
  if (!input.isDebouncing || !input.clickedNodeId) {
    return false;
  }
  return input.clickedNodeId !== input.lastClickedNodeId;
}

/**
 * 判断 node:click 末尾是否应跳过为当前节点重新调度打开配置面板。
 *
 * 背景：node:click 末尾有提前 return，避免“点击已经打开的同一节点”重复打开
 * 抽屉。旧判定仅比较 halfModalNodeId === clickedNodeId，但 halfModalNodeId 是
 * 在抽屉 afterClose 动画回调中才清空的，存在窗口：
 *   A 抽屉已打开 → 快速 A→B→A 时，B 点击会调用 closeNodeConfigDrawer()，
 *   该函数同步把 showNodeConfigDrawer 置 false 并触发关闭动画，但
 *   halfModalNodeId 仍为旧值 'A'，直到 afterClose 才清空。此时最新 A 的点击
 *   会因 halfModalNodeId === 'A' 被误判为“已打开同一节点”而提前 return，
 *   而旧 A 调度已被失效、B 调度也已被最新 A 失效，最终无节点打开。
 *
 * 修正：只有“配置抽屉确实仍处于打开状态（showNodeConfigDrawer === true）且
 * 当前节点正是该已打开节点”时才允许跳过；抽屉已被 closeNodeConfigDrawer 关闭
 * /正在切换时（showNodeConfigDrawer 同步为 false，即便 halfModalNodeId 尚未
 * 被 afterClose 清空）不应跳过，让本次点击继续生成 nodeInfo、关闭旧抽屉并
 * scheduleOpenNodeModal。
 *
 * 抽出纯判定核心，便于在纯 Node 环境下覆盖“稳定同节点跳过 / 关闭动画中不
 * 跳过 / 不同节点不跳过 / 无抽屉不跳过 / clickedNodeId 缺失不跳过”等分支。
 */
export interface SkipScheduleInput {
  /** 本次点击的节点 id。 */
  clickedNodeId: string | undefined;
  /** 当前已打开配置抽屉对应的节点 id（'' 表示无抽屉；afterClose 前可能仍为旧值）。 */
  halfModalNodeId: string;
  /** 配置抽屉是否确实处于打开状态（closeNodeConfigDrawer 会同步置 false）。 */
  showNodeConfigDrawer: boolean;
}

export function shouldSkipScheduleForOpenNode(input: SkipScheduleInput): boolean {
  // 抽屉未打开（含关闭动画中 showNodeConfigDrawer 已同步为 false）或本次点击
  // 无节点 id：一律不跳过，让本次点击继续走 nodeInfo 守卫与调度流程。
  if (!input.showNodeConfigDrawer || !input.clickedNodeId) {
    return false;
  }
  return input.clickedNodeId === input.halfModalNodeId;
}

/**
 * 判断节点配置抽屉的 afterClose 回调是否仍属于“当前抽屉”，从而是否允许清空
 * halfModalNodeId。
 *
 * 背景：openNodeModal 创建新抽屉时设置 halfModalNodeId = 新节点 id，并为该抽屉
 * 订阅 afterClose 以便关闭后清空 halfModalNodeId。但抽屉关闭动画与新建抽屉存在
 * 时序竞态：旧抽屉（A）的关闭动画可能在新抽屉（B / 新 A）创建并已将
 * halfModalNodeId 设为新值之后才完成，旧 A 的 afterClose 回调晚到。若旧回调
 * 无条件 `this.halfModalNodeId = ''`，会把新抽屉的 id 一并清空，破坏“稳定打开
 * 同一节点”的去重状态——此时新抽屉虽仍打开，halfModalNodeId 已为空，后续同
 * 节点点击因 clickedNodeId !== halfModalNodeId 而不再被
 * shouldSkipScheduleForOpenNode 跳过，重复调度打开。
 *
 * 修复：afterClose 回调闭包创建时捕获该抽屉实例与版本号；回调触发时只有“正在
 * 关闭的抽屉实例仍是当前 halfModalRef、且版本号未自增”才允许清空。任一条件不
 * 满足都意味着此 afterClose 来自已被替换的旧抽屉，不得清空当前状态。
 *
 * 同时校验实例与版本：实例校验直接命中“halfModalRef 已指向新实例”；版本校验作
 * 为整数化兜底信号，便于在纯 Node 环境下覆盖（实例为引用相等、版本为数值相等）。
 * 两者一致是允许清空的必要条件——用 AND 而非 OR，确保旧抽屉的晚到回调无论从
 * 实例还是版本角度都不得误清空新抽屉状态。
 */
export interface HalfModalCloseGuardInput {
  /** afterClose 回调闭包创建时所捕获的、正在关闭的抽屉实例。 */
  closingRef: unknown;
  /** 回调触发时组件当前持有的最新抽屉实例（this.halfModalRef）。 */
  currentRef: unknown;
  /** afterClose 回调闭包创建时所捕获的版本号。 */
  closingVersion: number;
  /** 回调触发时组件当前持有的最新版本号（this.halfModalVersion）。 */
  currentVersion: number;
}

export function shouldClearHalfModalOnClose(
  input: HalfModalCloseGuardInput,
): boolean {
  return (
    input.closingRef === input.currentRef &&
    input.closingVersion === input.currentVersion
  );
}
