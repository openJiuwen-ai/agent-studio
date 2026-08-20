/**
 * shouldInvalidatePendingOpen 的最小可运行单元测试。
 *
 * 运行方式（项目内已安装 ts-node，无需引入大规模测试基础设施）：
 *   cd frontend
 *   pnpm exec ts-node --compiler-options '{"module":"commonjs","moduleResolution":"node"}' \
 *     src/test/agent-center/app-flow/utils/pending-open-node.util.test.ts
 *
 * 说明：与 editable-target.util.test.ts 一致，对从 node:click 防抖/延迟打开逻辑
 * 中抽出的纯判定核心做覆盖。无需 Karma/Chrome/Angular/X6 组件环境。
 * 测试代码集中置于 src/test/ 下，与源码分离；通过相对路径回引 routes 源文件。
 */
import assert from 'node:assert/strict';
import {
  shouldClearHalfModalOnClose,
  shouldInvalidatePendingOpen,
  shouldSkipScheduleForOpenNode,
} from '../../../../routes/agent-center/app-flow/utils/pending-open-node.util';

let passed = 0;
let failed = 0;

function check(name: string, fn: () => void): void {
  try {
    fn();
    passed++;
    // eslint-disable-next-line no-console
    console.log(`ok   - ${name}`);
  } catch (e) {
    failed++;
    // eslint-disable-next-line no-console
    console.error(`FAIL - ${name}: ${(e as Error).message}`);
  }
}

// —— 首次点击（未进入防抖窗口）：不应失效 ——
check('首次点击不失效（scheduleOpenNodeModal 自身 token++ 已处理）', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: false,
      clickedNodeId: 'node_A',
      lastClickedNodeId: undefined,
    }),
    false,
  ),
);

// —— 同节点连击（防抖窗口内、同一节点）：不应失效，保留 250ms 延迟打开 ——
check('同节点连击不失效（保留单击 250ms 后打开）', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: 'node_A',
      lastClickedNodeId: 'node_A',
    }),
    false,
  ),
);

check('同节点连击（lastClickedNodeId === clickedNodeId）不失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: 'node_A',
      lastClickedNodeId: 'node_A',
    }),
    false,
  ),
);

// —— 快速切换节点（防抖窗口内、不同节点）：应失效，避免旧节点延迟打开 ——
check('快速切换到不同节点应失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: 'node_B',
      lastClickedNodeId: 'node_A',
    }),
    true,
  ),
);

check('A→B→C 连续切换，每次均应失效', () => {
  // 第一拍：A 点击后进入防抖
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: false,
      clickedNodeId: 'node_A',
      lastClickedNodeId: undefined,
    }),
    false,
  );
  // 第二拍：A→B 切换，应失效
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: 'node_B',
      lastClickedNodeId: 'node_A',
    }),
    true,
  );
});

// —— 边界：未进入防抖但节点不同 —— 不失效（由 scheduleOpenNodeModal token 处理）——
check('未防抖时即便节点不同也不失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: false,
      clickedNodeId: 'node_B',
      lastClickedNodeId: 'node_A',
    }),
    false,
  ),
);

// —— 边界：缺失 clickedNodeId —— 不失效 ——
check('防抖中但本次点击无节点 id 不失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: undefined,
      lastClickedNodeId: 'node_A',
    }),
    false,
  ),
);

check('clickedNodeId 为空字符串不失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: '',
      lastClickedNodeId: 'node_A',
    }),
    false,
  ),
);

// —— 边界：lastClickedNodeId 为 undefined（防御性，正常不会出现）——
// 进入防抖意味着上一拍已设置 lastClickedNodeId，但若异常缺失，对新节点的
// 失效仍应返回 true（token 自增是幂等的安全兜底）。
check('防抖中切换到新节点且 lastClickedNodeId 缺失：安全失效', () =>
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: true,
      clickedNodeId: 'node_B',
      lastClickedNodeId: undefined,
    }),
    true,
  ),
);

// —— 序列判定：模拟 node:click 防抖状态机，真实覆盖 A→B / A→B→A 等快速切换 ——
//
// simulateEventSequence 镜像 FlowEventUtils.addGraphEventListeners 中 node:click /
// edge:click / blank:click 的防抖状态机（仅判定层面，不依赖真实 X6/Angular）：
// - 首次点击：不失效，进入防抖并排队打开该节点；
// - 防抖内同节点连击：不失效、不重新排队（直接 return），保留首次排队的 250ms 延迟打开；
// - 防抖内切换到不同节点：先失效旧任务，再为新节点重新排队，并刷新 lastClickedNodeId；
// - edge:click / blank:click（interrupt）：调用 invalidatePendingOpenNode 失效所有待打开
//   任务，并调用 resetNodeClickDebounce 复位防抖状态（isDebouncing=false、
//   lastClickedNodeId=undefined），使下一次 node:click 视为首次点击 —— 修复
//   A→edge/blank→A 中旧 A 调度已被失效、最新 A 又被“同节点 return”跳过、最终无节点打开。
// 事件类型：字符串 = node:click 该节点；{type:'interrupt'} = edge:click / blank:click。
// 返回每拍 {clickedNodeId, invalidated, scheduledNodeId} 与最终排队的节点（即 250ms 后
// 真正会打开的节点）。
type SeqEvent = string | {type: 'interrupt'};

function simulateEventSequence(events: SeqEvent[]) {
  let isDebouncing = false;
  let lastClickedNodeId: string | undefined;
  const decisions: {
    clickedNodeId: string | null;
    invalidated: boolean;
    scheduledNodeId: string | null;
  }[] = [];
  let finalScheduledNodeId: string | null = null;
  for (const event of events) {
    if (typeof event !== 'string') {
      // edge:click / blank:click：无差别失效 + 重置防抖状态（不排队）。
      decisions.push({
        clickedNodeId: null,
        invalidated: true,
        scheduledNodeId: null,
      });
      isDebouncing = false;
      lastClickedNodeId = undefined;
      continue;
    }
    const clickedNodeId = event;
    const invalidated = shouldInvalidatePendingOpen({
      isDebouncing,
      clickedNodeId,
      lastClickedNodeId,
    });
    // 防抖内同节点连击：保留旧调度，不重新排队、不刷新状态。
    if (isDebouncing && clickedNodeId === lastClickedNodeId) {
      decisions.push({clickedNodeId, invalidated, scheduledNodeId: null});
      continue;
    }
    // 首次点击 / 切换到不同节点：排队打开并刷新防抖窗口与 lastClickedNodeId。
    decisions.push({clickedNodeId, invalidated, scheduledNodeId: clickedNodeId});
    finalScheduledNodeId = clickedNodeId;
    isDebouncing = true;
    lastClickedNodeId = clickedNodeId;
  }
  return {decisions, finalScheduledNodeId};
}

// 仅节点点击序列的便捷包装，等价于 simulateEventSequence(纯字符串事件)。
function simulateClickSequence(clicks: string[]) {
  return simulateEventSequence(clicks);
}

check('A→B：A 首次不失效并排队，B 失效旧 A 并重新排队 B，最终打开 B', () => {
  const {decisions, finalScheduledNodeId} = simulateClickSequence([
    'node_A',
    'node_B',
  ]);
  assert.equal(decisions.length, 2);
  // 第一拍 A：首次点击，不失效，排队 A
  assert.equal(decisions[0].invalidated, false);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  // 第二拍 B：切换，失效旧 A，重新排队 B
  assert.equal(decisions[1].invalidated, true);
  assert.equal(decisions[1].scheduledNodeId, 'node_B');
  // 最终排队的（即会打开的）是 B，旧 A 被失效不会打开
  assert.equal(finalScheduledNodeId, 'node_B');
});

check('A→B→A：每拍切换都失效旧任务并重新排队，最终只打开最新 A', () => {
  const {decisions, finalScheduledNodeId} = simulateClickSequence([
    'node_A',
    'node_B',
    'node_A',
  ]);
  assert.equal(decisions.length, 3);
  // 第一拍 A：首次点击，不失效，排队 A
  assert.equal(decisions[0].invalidated, false);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  // 第二拍 B：切换，失效旧 A，排队 B
  assert.equal(decisions[1].invalidated, true);
  assert.equal(decisions[1].scheduledNodeId, 'node_B');
  // 第三拍切回 A：失效旧 B，排队最新 A（不打开旧 A / B）
  assert.equal(decisions[2].invalidated, true);
  assert.equal(decisions[2].scheduledNodeId, 'node_A');
  // 最终排队的（即会打开的）是最新 A
  assert.equal(finalScheduledNodeId, 'node_A');
});

check('A→A 同节点连击：第二拍不失效、不重新排队，最终仍打开首次排队的 A', () => {
  const {decisions, finalScheduledNodeId} = simulateClickSequence([
    'node_A',
    'node_A',
  ]);
  assert.equal(decisions.length, 2);
  assert.equal(decisions[0].invalidated, false);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  // 同节点连击：不失效、不重新排队
  assert.equal(decisions[1].invalidated, false);
  assert.equal(decisions[1].scheduledNodeId, null);
  // 最终排队的仍是首次的 A
  assert.equal(finalScheduledNodeId, 'node_A');
});

check('A→B→B→A：中间同节点连击不重新排队，最终打开最新 A', () => {
  const {decisions, finalScheduledNodeId} = simulateClickSequence([
    'node_A',
    'node_B',
    'node_B',
    'node_A',
  ]);
  assert.equal(decisions.length, 4);
  // 第一拍 A：首次点击，排队 A
  assert.equal(decisions[0].invalidated, false);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  // 第二拍 B：切换，失效旧 A，排队 B
  assert.equal(decisions[1].invalidated, true);
  assert.equal(decisions[1].scheduledNodeId, 'node_B');
  // 第三拍 B 同节点连击：不失效、不重新排队
  assert.equal(decisions[2].invalidated, false);
  assert.equal(decisions[2].scheduledNodeId, null);
  // 第四拍切回 A：失效旧 B，排队最新 A
  assert.equal(decisions[3].invalidated, true);
  assert.equal(decisions[3].scheduledNodeId, 'node_A');
  assert.equal(finalScheduledNodeId, 'node_A');
});

// —— 边界：防抖窗口过期后再次点击应被视为首次点击（不失效）——
// 模拟 A 点击 → 防抖窗口结束（isDebouncing 复位）→ B 点击，B 应不失效并排队。
check('防抖过期后再点 B：视为首次点击，不失效并排队 B', () => {
  // 第一拍 A：首次点击，排队 A，进入防抖
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: false,
      clickedNodeId: 'node_A',
      lastClickedNodeId: undefined,
    }),
    false,
  );
  // 防抖窗口结束：isDebouncing 复位为 false、lastClickedNodeId 清空
  // 第二拍 B：再次视为首次点击，不失效，排队 B
  assert.equal(
    shouldInvalidatePendingOpen({
      isDebouncing: false,
      clickedNodeId: 'node_B',
      lastClickedNodeId: undefined,
    }),
    false,
  );
});

// ============ Bug1 回归：A→edge/blank→A 重置防抖后最新 A 重新排队 ============
// 旧实现：edge:click / blank:click 只调用 invalidatePendingOpenNode()，未清空
// nodeClick / lastClickedNodeId / nodeClickTimer。随后 300ms 防抖窗口内再次点击
// A，命中 clickedNodeId === lastClickedNodeId 直接 return，但旧延迟任务已被失效，
// A 不会重新 scheduleOpenNodeModal —— 最终无节点打开。
// 修复后：edge:click / blank:click 调用 resetNodeClickDebounce() 复位防抖状态，
// 最新 A 视为首次点击并重新排队。
check('A→edge→A：edge 重置防抖后，最新 A 视为首次点击并重新排队', () => {
  const {decisions, finalScheduledNodeId} = simulateEventSequence([
    'node_A',
    {type: 'interrupt'}, // edge:click
    'node_A',
  ]);
  assert.equal(decisions.length, 3);
  // 第一拍 A：首次点击，不失效，排队 A
  assert.equal(decisions[0].invalidated, false);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  // 第二拍 edge：失效旧 A 调度 + 重置防抖（不排队）
  assert.equal(decisions[1].invalidated, true);
  assert.equal(decisions[1].scheduledNodeId, null);
  // 第三拍 A：防抖已重置，视为首次点击，不失效并重新排队 A
  // （旧实现此处因 lastClickedNodeId 仍为 A 而同节点 return，不排队）
  assert.equal(decisions[2].invalidated, false);
  assert.equal(decisions[2].scheduledNodeId, 'node_A');
  assert.equal(finalScheduledNodeId, 'node_A');
});

check('A→blank→A：blank 重置防抖后，最新 A 重新排队', () => {
  const {decisions, finalScheduledNodeId} = simulateEventSequence([
    'node_A',
    {type: 'interrupt'}, // blank:click
    'node_A',
  ]);
  assert.equal(decisions.length, 3);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  assert.equal(decisions[1].invalidated, true);
  assert.equal(decisions[1].scheduledNodeId, null);
  assert.equal(decisions[2].invalidated, false);
  assert.equal(decisions[2].scheduledNodeId, 'node_A');
  assert.equal(finalScheduledNodeId, 'node_A');
});

check('A→B→edge→A：B 排队后 edge 失效 B 并重置，最新 A 重新排队', () => {
  const {decisions, finalScheduledNodeId} = simulateEventSequence([
    'node_A',
    'node_B',
    {type: 'interrupt'}, // edge:click
    'node_A',
  ]);
  assert.equal(decisions.length, 4);
  assert.equal(decisions[0].scheduledNodeId, 'node_A');
  assert.equal(decisions[1].invalidated, true); // A→B 切换失效旧 A
  assert.equal(decisions[1].scheduledNodeId, 'node_B');
  assert.equal(decisions[2].invalidated, true); // edge 失效 B + 重置
  assert.equal(decisions[2].scheduledNodeId, null);
  // 防抖已重置，最新 A 视为首次点击
  assert.equal(decisions[3].invalidated, false);
  assert.equal(decisions[3].scheduledNodeId, 'node_A');
  assert.equal(finalScheduledNodeId, 'node_A');
});

// ============ Bug2 回归：shouldSkipScheduleForOpenNode 分支判定 ============
// 旧实现：node:click 末尾 `if (halfModalNodeId === clickedNodeId) return`。
// halfModalNodeId 在抽屉 afterClose 动画回调中才清空，存在窗口：A 抽屉已打开 →
// 快速 A→B→A 时，B 点击 closeNodeConfigDrawer() 同步把 showNodeConfigDrawer 置
// false 并触发关闭动画，但 halfModalNodeId 仍为旧 'A'，最新 A 被误判跳过、
// 旧 A/B 调度又被失效，最终无节点打开。
// 修复后：只有 showNodeConfigDrawer && clickedNodeId === halfModalNodeId 才跳过。

// —— 稳定同节点重复点击：跳过（保留已打开抽屉，不重复调度）——
check('抽屉稳定打开且同节点重复点击：跳过重复调度', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'node_A',
      halfModalNodeId: 'node_A',
      showNodeConfigDrawer: true,
    }),
    true,
  ),
);

// —— Bug2 核心：关闭动画中（showNodeConfigDrawer=false 但 halfModalNodeId 仍为旧 A）
//    点击最新 A：不跳过，允许重新调度 ——
check('抽屉关闭动画中点击最新 A（halfModalNodeId 仍为旧值）：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'node_A',
      halfModalNodeId: 'node_A', // afterClose 尚未清空
      showNodeConfigDrawer: false, // closeNodeConfigDrawer 已同步置 false
    }),
    false,
  ),
);

// —— 不同节点：不跳过，允许切换 ——
check('A 抽屉打开时点击不同节点 B：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'node_B',
      halfModalNodeId: 'node_A',
      showNodeConfigDrawer: true,
    }),
    false,
  ),
);

// —— 无抽屉：不跳过 ——
check('无抽屉（halfModalNodeId=""）点击 A：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'node_A',
      halfModalNodeId: '',
      showNodeConfigDrawer: false,
    }),
    false,
  ),
);

// —— 防御分支：showNodeConfigDrawer=true 但 halfModalNodeId 为空（异常态）：不跳过 ——
check('showNodeConfigDrawer=true 但 halfModalNodeId 为空：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'node_A',
      halfModalNodeId: '',
      showNodeConfigDrawer: true,
    }),
    false,
  ),
);

// —— 防御分支：clickedNodeId 缺失：不跳过（交由 nodeInfo 守卫）——
check('clickedNodeId 为 undefined：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: undefined,
      halfModalNodeId: 'node_A',
      showNodeConfigDrawer: true,
    }),
    false,
  ),
);

check('clickedNodeId 为空字符串：不跳过', () =>
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: '',
      halfModalNodeId: '',
      showNodeConfigDrawer: false,
    }),
    false,
  ),
);

// ============ Bug2 集成：A→B→A 旧抽屉关闭动画未完成时最新 A 不被误判 ============
// 端到端模拟 node:click 处理顺序：先 shouldInvalidatePendingOpen 决定是否失效，
// 再 shouldSkipScheduleForOpenNode 决定是否跳过调度，并维护防抖 / halfModal 状态。
// 镜像 flow-event-utils.ts node:click + closeNodeConfigDrawer 的副作用顺序。
check('A→B→A（旧 A 抽屉关闭动画未完成）：最新 A 不被误判跳过，最终排队最新 A', () => {
  // 初始：A 抽屉稳定打开，防抖已过期。
  let isDebouncing = false;
  let lastClickedNodeId: string | undefined;
  let showNodeConfigDrawer = true;
  let halfModalNodeId = 'node_A';
  let finalScheduledNodeId: string | null = 'node_A'; // 已打开

  // 第 1 拍 node:click B（A 抽屉已打开、防抖外）
  {
    const clickedNodeId = 'node_B';
    const invalidated = shouldInvalidatePendingOpen({
      isDebouncing,
      clickedNodeId,
      lastClickedNodeId,
    });
    assert.equal(invalidated, false); // 防抖外首次点击不失效
    // A 抽屉虽打开，但 clickedNodeId='B' !== halfModalNodeId='A'，不跳过
    const skip = shouldSkipScheduleForOpenNode({
      clickedNodeId,
      halfModalNodeId,
      showNodeConfigDrawer,
    });
    assert.equal(skip, false);
    // 调度 B；closeNodeConfigDrawer 同步置 false，halfModalNodeId 暂留旧值（afterClose 未触发）
    finalScheduledNodeId = clickedNodeId;
    showNodeConfigDrawer = false;
    isDebouncing = true;
    lastClickedNodeId = clickedNodeId;
  }

  // 第 2 拍 node:click A（B 调度尚未触发 / A 抽屉 afterClose 尚未清空 halfModalNodeId）
  {
    const clickedNodeId = 'node_A';
    const invalidated = shouldInvalidatePendingOpen({
      isDebouncing,
      clickedNodeId,
      lastClickedNodeId,
    });
    assert.equal(invalidated, true); // 切换 B→A，失效 B 调度
    // 关键：showNodeConfigDrawer=false（已被 B 的 closeNodeConfigDrawer 同步关闭），
    // 即便 halfModalNodeId 仍为旧 'A'，也不应跳过最新 A 的调度。
    const skip = shouldSkipScheduleForOpenNode({
      clickedNodeId,
      halfModalNodeId, // 仍为 'node_A'（afterClose 未触发）
      showNodeConfigDrawer, // false
    });
    assert.equal(skip, false); // 修复后不跳过；旧实现此处会 return 导致无节点打开
    finalScheduledNodeId = clickedNodeId; // 调度最新 A
    isDebouncing = true;
    lastClickedNodeId = clickedNodeId;
  }

  assert.equal(finalScheduledNodeId, 'node_A');
});

// ============ 稳定同节点重复点击集成：不重复调度 ============
check('A 抽屉稳定打开时重复点击 A：不失效、不重新调度（保留已打开抽屉）', () => {
  const showNodeConfigDrawer = true;
  const halfModalNodeId = 'node_A';
  let isDebouncing = false;
  let lastClickedNodeId: string | undefined;
  const schedules: string[] = [];

  for (const clickedNodeId of ['node_A', 'node_A']) {
    const invalidated = shouldInvalidatePendingOpen({
      isDebouncing,
      clickedNodeId,
      lastClickedNodeId,
    });
    // 防抖外首次 / 防抖内同节点连击：均不失效
    assert.equal(invalidated, false);
    const skip = shouldSkipScheduleForOpenNode({
      clickedNodeId,
      halfModalNodeId,
      showNodeConfigDrawer,
    });
    if (!skip) {
      schedules.push(clickedNodeId);
    }
    // 同节点连击不刷新防抖状态；首次点击进入防抖
    if (!(isDebouncing && clickedNodeId === lastClickedNodeId)) {
      isDebouncing = true;
      lastClickedNodeId = clickedNodeId;
    }
  }
  // 两次点击均被跳过：抽屉已稳定打开且同节点，不重复调度
  assert.equal(schedules.length, 0);
});

// ============ Bug3 回归：抽屉 afterClose 竞态守卫 shouldClearHalfModalOnClose ============
// 旧实现：openNodeModal 创建新抽屉时设置 halfModalNodeId = 新 id，并为该抽屉订阅
// afterClose(() => { this.halfModalNodeId = '' })。但旧抽屉的关闭动画可能在 新抽屉
// 创建并已写入 halfModalNodeId 之后才完成，旧 afterClose 晚到会无条件清空新抽屉
// 的 id，破坏“稳定打开同一节点”去重——此时新抽屉虽仍打开，halfModalNodeId 已
// 为空，后续同节点点击因 clickedNodeId !== halfModalNodeId 而不再被
// shouldSkipScheduleForOpenNode 跳过，重复调度打开。
// 修复后：afterClose 闭包捕获创建时的抽屉实例与版本号，仅当“正在关闭的抽屉仍是
// 当前 halfModalRef 且版本未变”时才清空。用对象引用模拟 NzDrawerRef 实例
// （nzDrawerService.create 每次返回新实例，引用互不相同）。

const drawerA = {tag: 'A'};
const drawerB = {tag: 'B'};
const drawerA2 = {tag: 'A2'};

// —— 当前抽屉 afterClose：实例与版本均一致，允许清空 ——
check('当前抽屉 afterClose（实例与版本均一致）：允许清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA,
      currentRef: drawerA,
      closingVersion: 1,
      currentVersion: 1,
    }),
    true,
  ),
);

// —— Bug3 核心：旧 afterClose 晚于新抽屉创建（实例已变），不得清空 ——
check('旧抽屉 afterClose 晚于新抽屉创建（实例已变）：不得清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA, // 旧抽屉
      currentRef: drawerB, // 已指向新抽屉
      closingVersion: 1,
      currentVersion: 2,
    }),
    false,
  ),
);

// —— 版本不匹配（即便实例相同）：不得清空（防御性兜底）——
check('版本不匹配（实例相同）：不得清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA,
      currentRef: drawerA,
      closingVersion: 1,
      currentVersion: 2,
    }),
    false,
  ),
);

// —— 实例不匹配（即便版本相同）：不得清空（防御性兜底）——
check('实例不匹配（版本相同）：不得清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA,
      currentRef: drawerB,
      closingVersion: 1,
      currentVersion: 1,
    }),
    false,
  ),
);

// —— 防御：closingRef 为 undefined（组件初始未创建抽屉的异常态）：不得清空 ——
check('closingRef 为 undefined：不得清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: undefined,
      currentRef: drawerA,
      closingVersion: 0,
      currentVersion: 1,
    }),
    false,
  ),
);

// —— 防御：currentRef 为 undefined（组件已销毁 / 异常态）：不得清空 ——
check('currentRef 为 undefined：不得清空', () =>
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA,
      currentRef: undefined,
      closingVersion: 1,
      currentVersion: 1,
    }),
    false,
  ),
);

// ============ Bug3 集成：A→B afterClose 时序不破坏新 B 状态 ============
// 镜像 openNodeModal + afterClose 生命周期：每创建一个抽屉就自增版本、捕获
// (closingRef, closingVersion) 到该抽屉的 afterClose 闭包，并按“真实关闭动画完成
// 顺序”触发回调，验证 halfModalNodeId 仅在当前抽屉关闭时被清空。
check('A→B：旧 A afterClose 晚于新 B 创建不得清空，B 正常关闭才清空', () => {
  let halfModalRef: unknown;
  let halfModalVersion = 0;
  let halfModalNodeId = '';
  const afterCloseCbs: Array<() => void> = [];

  // openNodeModal(A)
  halfModalNodeId = 'A';
  const closingVersionA = ++halfModalVersion;
  halfModalRef = {tag: 'A'};
  const closingRefA = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefA,
        currentRef: halfModalRef,
        closingVersion: closingVersionA,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // A 关闭动画开始但 afterClose 未触发；用户快速切换到 B：openNodeModal(B)
  halfModalNodeId = 'B';
  const closingVersionB = ++halfModalVersion;
  halfModalRef = {tag: 'B'};
  const closingRefB = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefB,
        currentRef: halfModalRef,
        closingVersion: closingVersionB,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // 新 B 抽屉已打开，halfModalNodeId 应为 'B'（旧实现此处会被旧 A afterClose 清空）
  assert.equal(halfModalNodeId, 'B');

  // 旧 A 的 afterClose 晚到：不得清空新 B 状态
  afterCloseCbs[0]();
  assert.equal(halfModalNodeId, 'B');

  // 新 B 正常关闭：允许清空
  afterCloseCbs[1]();
  assert.equal(halfModalNodeId, '');
});

// ============ Bug3 集成：A→B→A 关闭动画完成顺序不破坏新 A 状态 ============
check('A→B→A：旧 A/B afterClose 晚到不清空，最终新 A 正常关闭才清空', () => {
  let halfModalRef: unknown;
  let halfModalVersion = 0;
  let halfModalNodeId = '';
  const afterCloseCbs: Array<() => void> = [];

  // openNodeModal(A)
  halfModalNodeId = 'A';
  const closingVersionA = ++halfModalVersion;
  halfModalRef = {tag: 'A'};
  const closingRefA = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefA,
        currentRef: halfModalRef,
        closingVersion: closingVersionA,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // 切换到 B：openNodeModal(B)
  halfModalNodeId = 'B';
  const closingVersionB = ++halfModalVersion;
  halfModalRef = {tag: 'B'};
  const closingRefB = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefB,
        currentRef: halfModalRef,
        closingVersion: closingVersionB,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // 切回 A：openNodeModal(A2)（新 A 抽屉）
  halfModalNodeId = 'A';
  const closingVersionA2 = ++halfModalVersion;
  halfModalRef = {tag: 'A2'};
  const closingRefA2 = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefA2,
        currentRef: halfModalRef,
        closingVersion: closingVersionA2,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // 新 A 抽屉已打开，halfModalNodeId 应为 'A'
  assert.equal(halfModalNodeId, 'A');

  // 旧 A afterClose 晚到：不得清空新 A 状态
  afterCloseCbs[0]();
  assert.equal(halfModalNodeId, 'A');
  // 旧 B afterClose 晚到：不得清空
  afterCloseCbs[1]();
  assert.equal(halfModalNodeId, 'A');
  // 新 A2 正常关闭：允许清空
  afterCloseCbs[2]();
  assert.equal(halfModalNodeId, '');
});

// ============ Bug3 集成：当前抽屉正常关闭（无新抽屉）允许清空 ============
check('当前抽屉正常关闭（无新抽屉）：允许清空 halfModalNodeId', () => {
  let halfModalRef: unknown;
  let halfModalVersion = 0;
  let halfModalNodeId = '';
  const afterCloseCbs: Array<() => void> = [];

  halfModalNodeId = 'A';
  const closingVersionA = ++halfModalVersion;
  halfModalRef = {tag: 'A'};
  const closingRefA = halfModalRef;
  afterCloseCbs.push(() => {
    if (
      shouldClearHalfModalOnClose({
        closingRef: closingRefA,
        currentRef: halfModalRef,
        closingVersion: closingVersionA,
        currentVersion: halfModalVersion,
      })
    ) {
      halfModalNodeId = '';
    }
  });

  // 无新抽屉，A 正常关闭：允许清空
  afterCloseCbs[0]();
  assert.equal(halfModalNodeId, '');
});

// ============ Bug3 集成：稳定同节点重复点击不被 afterClose 清空破坏 ============
// 旧实现：A 抽屉稳定打开 → 切换到 B 触发 A 关闭动画 → 切回 A 创建新 A 抽屉 →
// 旧 A afterClose 晚到清空 halfModalNodeId='' → 此时新 A 抽屉虽打开，但
// halfModalNodeId 已为空，再次点击 A 不被 shouldSkipScheduleForOpenNode 跳过 →
// 重复调度打开 A。修复后 halfModalNodeId 始终为 'A'，重复点击被正确跳过。
check('A→B→A 后新 A 稳定打开：halfModalNodeId 保持 A，同节点重复点击被跳过', () => {
  let halfModalRef: unknown;
  let halfModalVersion = 0;
  let halfModalNodeId = '';
  let showNodeConfigDrawer = false;
  const afterCloseCbs: Array<() => void> = [];

  const openNodeModal = (id: string, tag: string) => {
    halfModalNodeId = id;
    const closingVersion = ++halfModalVersion;
    halfModalRef = {tag};
    const closingRef = halfModalRef;
    showNodeConfigDrawer = true;
    afterCloseCbs.push(() => {
      if (
        shouldClearHalfModalOnClose({
          closingRef,
          currentRef: halfModalRef,
          closingVersion,
          currentVersion: halfModalVersion,
        })
      ) {
        halfModalNodeId = '';
      }
    });
  };

  openNodeModal('A', 'A');
  // 切换到 B（A 关闭动画开始），再切回 A
  openNodeModal('B', 'B');
  openNodeModal('A', 'A2');

  // 新 A 抽屉已打开
  assert.equal(halfModalNodeId, 'A');
  assert.equal(showNodeConfigDrawer, true);

  // 旧 A / 旧 B 的 afterClose 依次晚到：不得清空
  afterCloseCbs[0]();
  afterCloseCbs[1]();
  assert.equal(halfModalNodeId, 'A');

  // 此时同节点重复点击 A 应被 shouldSkipScheduleForOpenNode 跳过（不重复调度）
  assert.equal(
    shouldSkipScheduleForOpenNode({
      clickedNodeId: 'A',
      halfModalNodeId,
      showNodeConfigDrawer,
    }),
    true,
  );
});

// eslint-disable-next-line no-console
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exit(1);
}
