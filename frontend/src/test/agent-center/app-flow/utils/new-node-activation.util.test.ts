/**
 * “新增节点自动选中并打开配置抽屉”的最小可运行单元测试。
 *
 * 覆盖两件事：
 * 1. 纯决策 planNewNodeActivation：给定新节点 DSL 与“是否在 NodeMap 中有配置组件”，
 *    决定 {select, openDrawer}。Comment 等无配置抽屉类型仅选中、不打开抽屉。
 * 2. 新增路径的时序不变量：复用既有 scheduleOpenNodeModal/invalidatePendingOpenNode
 *    的 token 机制与 openNodeModal 的节点存在性守卫，模拟 activateNewNode 的副作用顺序，
 *    覆盖“连续新增最后获胜 / 新增后被边或空白中断 / 新增后删除不打开 / Comment 不打开 /
 *    旧抽屉 afterClose 不破坏新抽屉”等场景。
 *
 * 运行方式（与 pending-open-node.util.test.ts 一致，纯 Node 环境，无 Karma/Chrome/X6）：
 *   cd frontend
 *   pnpm exec ts-node --transpile-only --compiler-options \
 *     '{"module":"commonjs","moduleResolution":"node","esModuleInterop":true}' \
 *     src/test/agent-center/app-flow/utils/new-node-activation.util.test.ts
 *
 * 说明：新增路径必须复用既有 token/抽屉竞态机制（不复制异步调度逻辑），故“最后获胜”
 * 的不变量在此通过模拟 activateNewNode 调用顺序 + token 计数器验证，与现有
 * pending-open-node.util.test.ts 的点击路径覆盖互补、不重复。
 */
import assert from 'node:assert/strict';
import {
  planNewNodeActivation,
  pickLastCreatedNode,
  shouldClearHalfModalOnClose,
  shouldProceedAfterWorkflowConfirm,
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

// ===========================================================================
// 一、纯决策 planNewNodeActivation
// ===========================================================================

// —— 有配置组件的普通节点（如 LLM）：选中 + 打开抽屉 ——
check('LLM 节点（hasConfigComponent=true）：select=true, openDrawer=true', () =>
  assert.deepEqual(
    planNewNodeActivation({
      nodeInfo: {id: 'node_llm', type: 'LLM'},
      hasConfigComponent: true,
    }),
    {select: true, openDrawer: true},
  ),
);

// —— Comment 不在 NodeMap 中：仅选中、不打开抽屉（按设计文档处理）——
check('Comment 节点（hasConfigComponent=false）：select=true, openDrawer=false', () =>
  assert.deepEqual(
    planNewNodeActivation({
      nodeInfo: {id: 'node_comment', type: 'Comment'},
      hasConfigComponent: false,
    }),
    {select: true, openDrawer: false},
  ),
);

// —— Loop 父节点：在 NodeMap 中，选中 + 打开（仅父节点进入激活，IO 子节点不进入）——
check('Loop 父节点（hasConfigComponent=true）：select=true, openDrawer=true', () =>
  assert.deepEqual(
    planNewNodeActivation({
      nodeInfo: {id: 'node_loop', type: 'Loop'},
      hasConfigComponent: true,
    }),
    {select: true, openDrawer: true},
  ),
);

// —— 无 nodeInfo（getNodeDSLFromRaw 返回 null）：不激活 ——
check('nodeInfo 为 null：不激活', () =>
  assert.deepEqual(
    planNewNodeActivation({nodeInfo: null, hasConfigComponent: true}),
    {select: false, openDrawer: false},
  ),
);

// —— nodeInfo 缺失 id：不激活（防御）——
check('nodeInfo 无 id：不激活', () =>
  assert.deepEqual(
    planNewNodeActivation({
      nodeInfo: {type: 'LLM'},
      hasConfigComponent: true,
    }),
    {select: false, openDrawer: false},
  ),
);

// —— nodeInfo 为 undefined：不激活 ——
check('nodeInfo 为 undefined：不激活', () =>
  assert.deepEqual(
    planNewNodeActivation({nodeInfo: undefined, hasConfigComponent: false}),
    {select: false, openDrawer: false},
  ),
);

// ===========================================================================
// 二、新增路径时序不变量（复用 token 机制，镜像 activateNewNode 副作用顺序）
// ===========================================================================
//
// 模拟器镜像 FlowComponent.activateNewNode + 既有 scheduleOpenNodeModal /
// invalidatePendingOpenNode / openNodeModal 守卫的真实行为（仅状态层面，不依赖
// 真实 X6/Angular）：
//   activateNewNode(nodeId, plan):
//     invalidate()         // openNodeModalToken++（取消此前待打开，含 Comment 不调度时也生效）
//     closeDrawer()        // closeNodeConfigDrawer：关旧抽屉、触发旧 afterClose
//     if plan.select:      // graph.resetSelection(nodeId) + NodeService.setCurrSelectedNode(nodeId)
//       selectedId = nodeId; currSelected = nodeId
//     if plan.openDrawer:  // scheduleOpenNodeModal：++token，250ms 后仅最新 token 且节点仍在才 open
//       schedule(nodeId)
//   interrupt():           // edge:click / blank:click：invalidate + closeDrawer + 清空选中
//   deleteNode(nodeId):    // 删除：移出 graph，invalidate（取消待打开）
//   flush():               // 推进 250ms：仅当前 token 且节点仍在 graph 时 open
//
// 每个 openNodeModal 创建抽屉时自增 halfModalVersion 并捕获 (closingRef, closingVersion)
// 到 afterClose 闭包；afterClose 仅当实例与版本均一致才清空 halfModalNodeId
// （复用 shouldClearHalfModalOnClose）。
interface Plan {
  select: boolean;
  openDrawer: boolean;
}

function createFlowState() {
  let openNodeModalToken = 0;
  let halfModalVersion = 0;
  let halfModalRef: unknown = undefined;
  let halfModalNodeId = '';
  let showNodeConfigDrawer = false;
  let selectedId: string | null = null; // X6 resetSelection 目标
  let currSelected = ''; // NodeService.getCurrSelectedNodeId()
  let openedNodeId: string | null = null; // 250ms 后真正 openNodeModal 打开的节点
  let activateCount = 0; // activateNewNode 实际执行（越过 null 守卫）的次数
  const graph = new Set<string>(); // 节点存在性
  const afterCloseCbs: Array<() => void> = [];

  function invalidate() {
    openNodeModalToken++;
  }
  function closeDrawer() {
    showNodeConfigDrawer = false;
    halfModalRef?.close?.(); // 触发旧抽屉关闭动画（此处立即派发 afterClose）
  }
  function schedule(nodeId: string) {
    const token = ++openNodeModalToken;
    // 250ms 回调（测试中由 flush() 同步推进）
    state.pending = {token, nodeId};
  }
  function openNodeModal(nodeId: string) {
    // openNodeModal 守卫：节点仍在 graph 才打开
    if (!graph.has(nodeId)) {
      return;
    }
    halfModalNodeId = nodeId;
    const closingVersion = ++halfModalVersion;
    halfModalRef = {tag: nodeId, close() {}};
    showNodeConfigDrawer = true;
    afterCloseCbs.push(() => {
      if (
        shouldClearHalfModalOnClose({
          closingRef: halfModalRef,
          currentRef: halfModalRef, // 模拟“当前抽屉正常关闭”
          closingVersion,
          currentVersion: halfModalVersion,
        })
      ) {
        halfModalNodeId = '';
      }
    });
    openedNodeId = nodeId;
  }
  function flush() {
    if (
      state.pending &&
      state.pending.token === openNodeModalToken &&
      graph.has(state.pending.nodeId)
    ) {
      openNodeModal(state.pending.nodeId);
    }
    state.pending = null;
  }
  const state = {pending: null as null | {token: number; nodeId: string}};

  function activateNewNode(nodeId: string | null, plan: Plan) {
    // 镜像 FlowComponent.activateNewNode 的前置守卫：!newNode / !nodeInfo?.id → 整体跳过
    if (!nodeId) {
      return;
    }
    activateCount++;
    invalidate();
    closeDrawer();
    if (plan.select) {
      selectedId = nodeId;
      currSelected = nodeId;
    }
    if (plan.openDrawer) {
      schedule(nodeId);
    }
  }
  function interrupt() {
    invalidate();
    closeDrawer();
    selectedId = null;
    currSelected = '';
  }
  function deleteNode(nodeId: string) {
    graph.delete(nodeId);
    invalidate();
    if (currSelected === nodeId || !graph.has(currSelected)) {
      // 仅当前节点确已不存在时清理（镜像既有删除逻辑）
      currSelected = '';
      selectedId = null;
    }
  }

  // —— 批量新增入口镜像 FlowComponent.addAllToolsByPluginId：
  //    forEach 对每个工具调用 addActionNode（返回实际创建 Node），结束后只对
  //    “最后一个实际创建的非空 Node”经 pickLastCreatedNode 选取后调用一次
  //    activateNewNode（而非为每项打开抽屉）。activate=false 时不激活任何节点，
  //    保护非用户主动新增的调用方。
  function batchAddThenActivate(
    nodeIds: Array<string>,
    activate: boolean,
    plan: Plan = PLAN_CONFIG,
  ) {
    const created: Array<string | null> = [];
    nodeIds.forEach((id) => {
      graph.add(id); // 镜像 addActionNode 实际创建并返回该 Node
      created.push(id);
    });
    // 镜像源码：this.activateNewNode(pickLastCreatedNode(created, activateAfterCreate))
    activateNewNode(pickLastCreatedNode(created, activate), plan);
  }

  // —— handleWorkflow 入口镜像 FlowComponent.handleWorkflow：创建单个 Workflow 节点后，
  //    经 pickLastCreatedNode([addedNode], activate) 决定是否激活（统一机制）。
  //    activate=false 时不激活（保护模板加载/复制/替换/历史回放等非用户新增调用）。
  function singleAddThenActivate(
    nodeId: string,
    activate: boolean,
    plan: Plan = PLAN_CONFIG,
  ) {
    graph.add(nodeId); // 镜像 addActionNode 实际创建并返回该 Node
    activateNewNode(pickLastCreatedNode([nodeId], activate), plan);
  }

  // —— addAgent 确认弹窗入口镜像 FlowComponent.addAgent 的 afterClose：
  //    用户在“新增子工作流”确认弹窗点 OK（close→true）才创建并激活 Workflow 节点；
  //    点取消（dismiss→false）或 X 关闭（destroy→undefined）则不创建、不激活、
  //    不改变已有选择。afterClose 回调以 shouldProceedAfterWorkflowConfirm(result)
  //    判定是否继续——仅确认（true）时才走 singleAddThenActivate（创建+激活）。
  function confirmThenAddWorkflow(
    result: unknown,
    nodeId: string,
    activate: boolean,
    plan: Plan = PLAN_CONFIG,
  ) {
    if (!shouldProceedAfterWorkflowConfirm(result)) {
      return; // 取消/X 关闭：不创建、不激活、不改变已有选择
    }
    singleAddThenActivate(nodeId, activate, plan);
  }

  return {
    graph,
    activateNewNode,
    interrupt,
    deleteNode,
    flush,
    batchAddThenActivate,
    singleAddThenActivate,
    confirmThenAddWorkflow,
    get state() {
      return {
        selectedId,
        currSelected,
        openedNodeId,
        halfModalNodeId,
        showNodeConfigDrawer,
        activateCount,
      };
    },
  };
}

const PLAN_CONFIG: Plan = {select: true, openDrawer: true};
const PLAN_COMMENT: Plan = {select: true, openDrawer: false};

// —— 首次新增普通节点：选中并打开 ——
check('首次新增 LLM：flush 后 openedNodeId=A，selectedId/currSelected=A', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.activateNewNode('A', PLAN_CONFIG);
  assert.equal(f.state.selectedId, 'A');
  assert.equal(f.state.currSelected, 'A');
  assert.equal(f.state.openedNodeId, null); // 250ms 未推进
  f.flush();
  assert.equal(f.state.openedNodeId, 'A');
  assert.equal(f.state.showNodeConfigDrawer, true);
});

// —— 连续新增 A→B→C：只有 C 打开（最后获胜，复用 token）——
check('连续新增 A→B→C：flush 后仅 openedNodeId=C，selectedId/currSelected=C', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.graph.add('B');
  f.graph.add('C');
  f.activateNewNode('A', PLAN_CONFIG);
  f.activateNewNode('B', PLAN_CONFIG);
  f.activateNewNode('C', PLAN_CONFIG);
  f.flush();
  assert.equal(f.state.openedNodeId, 'C');
  assert.equal(f.state.selectedId, 'C');
  assert.equal(f.state.currSelected, 'C');
});

// —— 新增 A 后立即点边/空白（250ms 内）：token 失效，不打开 ——
check('新增 A 后 edge/blank 中断：flush 后 openedNodeId=null，currSelected=""', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.activateNewNode('A', PLAN_CONFIG);
  f.interrupt();
  f.flush();
  assert.equal(f.state.openedNodeId, null);
  assert.equal(f.state.currSelected, '');
});

// —— 新增 A 后 250ms 内删除 A：节点已不在 graph，flush 不打开 ——
check('新增 A 后删除 A：flush 后 openedNodeId=null（节点存在性守卫）', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.activateNewNode('A', PLAN_CONFIG);
  f.deleteNode('A');
  f.flush();
  assert.equal(f.state.openedNodeId, null);
});

// —— Comment 新增：仅选中、不调度打开；且会令此前排队的 A 失效 ——
check('新增 A 后新增 Comment：A 失效、Comment 选中但 flush 后 openedNodeId=null', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.graph.add('CM');
  f.activateNewNode('A', PLAN_CONFIG);
  f.activateNewNode('CM', PLAN_COMMENT);
  assert.equal(f.state.selectedId, 'CM');
  assert.equal(f.state.currSelected, 'CM');
  f.flush();
  assert.equal(f.state.openedNodeId, null); // Comment 不调度；A 已失效
});

// —— A 抽屉已打开后新增 B：先关 A 抽屉，再调度 B，flush 打开 B ——
check('A 抽屉已打开后新增 B：flush 后 openedNodeId=B，currSelected=B', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.graph.add('B');
  f.activateNewNode('A', PLAN_CONFIG);
  f.flush();
  assert.equal(f.state.openedNodeId, 'A');
  // A 抽屉稳定打开后，快速新增 B
  f.activateNewNode('B', PLAN_CONFIG);
  f.flush();
  assert.equal(f.state.openedNodeId, 'B');
  assert.equal(f.state.currSelected, 'B');
});

// —— 新增路径复用 shouldClearHalfModalOnClose：旧 A afterClose 不得清空新 B 的 halfModalNodeId ——
check('A→B：旧 A 抽屉 afterClose 晚到不清空新 B 状态（复用 shouldClearHalfModalOnClose）', () => {
  // 直接复用既有纯函数，验证新增路径不会破坏抽屉关闭竞态守卫
  const drawerA = {tag: 'A'};
  const drawerB = {tag: 'B'};
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerA, // 旧 A 抽屉
      currentRef: drawerB, // 已指向新 B
      closingVersion: 1,
      currentVersion: 2,
    }),
    false,
  );
  // 新 B 正常关闭才清空
  assert.equal(
    shouldClearHalfModalOnClose({
      closingRef: drawerB,
      currentRef: drawerB,
      closingVersion: 2,
      currentVersion: 2,
    }),
    true,
  );
});

// —— 已点击排队 A（node:click 路径）后 250ms 内新增 B：A 失效，B 最终打开 ——
// 镜像 node:click 调度 A → 用户改走“新增”入口加 B：B 的 activateNewNode 调用
// invalidate() 令 A 的待打开失效，再调度 B。
check('点击排队 A 后新增 B：A 失效，flush 后 openedNodeId=B', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.graph.add('B');
  // 模拟 node:click 已 scheduleOpenNodeModal(A)
  f.activateNewNode('A', PLAN_CONFIG); // 复用同一 token 调度
  // 用户走新增入口加 B
  f.activateNewNode('B', PLAN_CONFIG);
  f.flush();
  assert.equal(f.state.openedNodeId, 'B');
});

// ===========================================================================
// 三、Review-1 P1 入口补强：addAllToolsByPluginId 批量 + handleWorkflow 单新增
// ===========================================================================
//
// 两个入口均绕过 createNode 直接调用 addActionNode，原先返回值被丢弃，故不进入
// activateNewNode。修复方案：addActionNode 已返回实际创建 Node；这两个入口各自增加
// 可选 activateAfterCreate 标志（默认 false，保护非用户新增调用方），经统一纯决策
// pickLastCreatedNode(createdNodes, activate) 选出激活目标后调用一次 activateNewNode。
//
// pickLastCreatedNode 语义：仅当激活开关开启时，返回 createdNodes 中最后一个非空
// 实际创建节点；否则返回 null（不激活任何节点）。批量“添加插件全部工具”据此在
// forEach 结束后只激活最后一个，而非为每项打开抽屉；handleWorkflow 单新增传
// [addedNode]，等价于“开启时激活该节点”。泛型 T 避免 util 依赖 X6 Node 类型。

// —— 纯决策 pickLastCreatedNode ——
check('pickLastCreatedNode([A,B,C], true)：返回最后一个 C', () =>
  assert.equal(pickLastCreatedNode(['A', 'B', 'C'], true), 'C'),
);

check('pickLastCreatedNode([A,B,C], false)：activate=false 返回 null（保护非用户调用）', () =>
  assert.equal(pickLastCreatedNode(['A', 'B', 'C'], false), null),
);

check('pickLastCreatedNode([A,null,C], true)：返回最后一个非空 C', () =>
  assert.equal(pickLastCreatedNode(['A', null, 'C'], true), 'C'),
);

check('pickLastCreatedNode([A,null], true)：尾部为 null 时返回最后一个非空 A', () =>
  assert.equal(pickLastCreatedNode(['A', null], true), 'A'),
);

check('pickLastCreatedNode([null,null], true)：全部为 null 返回 null', () =>
  assert.equal(pickLastCreatedNode([null, null], true), null),
);

check('pickLastCreatedNode([], true)：空批量返回 null', () =>
  assert.equal(pickLastCreatedNode([], true), null),
);

check('pickLastCreatedNode(undefined, true)：undefined 输入返回 null（防御）', () =>
  assert.equal(pickLastCreatedNode(undefined, true), null),
);

check('pickLastCreatedNode(null, true)：null 输入返回 null（防御）', () =>
  assert.equal(pickLastCreatedNode(null, true), null),
);

check('pickLastCreatedNode([A], true)：单元素（handleWorkflow 等价）返回 A', () =>
  assert.equal(pickLastCreatedNode(['A'], true), 'A'),
);

check('pickLastCreatedNode([A], false)：单元素 activate=false 返回 null', () =>
  assert.equal(pickLastCreatedNode(['A'], false), null),
);

// —— addAllToolsByPluginId 批量入口时序不变量 ——
//
// 批量新增 [P1,P2,P3] 且 activate=true：activateNewNode 仅被调用 1 次（非 3 次），
// 目标为最后一个实际创建节点 P3；flush 后仅 P3 选中、仅 P3 抽屉打开。
check('批量新增 [P1,P2,P3] activate=true：activateCount=1，flush 后 openedNodeId/selectedId=P3', () => {
  const f = createFlowState();
  f.batchAddThenActivate(['P1', 'P2', 'P3'], true);
  assert.equal(f.state.activateCount, 1, '批量只激活一次（非每项一次）');
  assert.equal(f.state.selectedId, 'P3');
  assert.equal(f.state.currSelected, 'P3');
  assert.equal(f.state.openedNodeId, null); // 250ms 未推进
  f.flush();
  assert.equal(f.state.openedNodeId, 'P3');
  assert.equal(f.state.showNodeConfigDrawer, true);
});

// 批量新增 activate=false（非用户主动新增调用方）：完全不激活，保护既有行为。
check('批量新增 activate=false：activateCount=0，flush 后无选中无抽屉', () => {
  const f = createFlowState();
  f.batchAddThenActivate(['P1', 'P2', 'P3'], false);
  assert.equal(f.state.activateCount, 0);
  assert.equal(f.state.selectedId, null);
  assert.equal(f.state.currSelected, '');
  f.flush();
  assert.equal(f.state.openedNodeId, null);
  assert.equal(f.state.showNodeConfigDrawer, false);
});

// 批量新增中最后一个节点 250ms 内被删除：节点存在性守卫，flush 不打开抽屉。
check('批量新增后删除最后一个 P3：flush 后 openedNodeId=null（节点存在性守卫）', () => {
  const f = createFlowState();
  f.batchAddThenActivate(['P1', 'P2', 'P3'], true);
  f.deleteNode('P3');
  f.flush();
  assert.equal(f.state.openedNodeId, null);
});

// 批量新增 P3 后被边/空白中断：token 失效，不打开抽屉（复用既有中断机制）。
check('批量新增 P3 后 edge/blank 中断：flush 后 openedNodeId=null', () => {
  const f = createFlowState();
  f.batchAddThenActivate(['P1', 'P2', 'P3'], true);
  f.interrupt();
  f.flush();
  assert.equal(f.state.openedNodeId, null);
  assert.equal(f.state.currSelected, '');
});

// —— handleWorkflow 单新增入口时序不变量 ——
//
// 用户新增 Workflow 节点（activate=true）：activateNewNode 调用 1 次、目标为该节点；
// flush 后该节点选中并打开配置抽屉（Workflow 在 NodeMap 中 → openDrawer=true）。
check('handleWorkflow 单新增 W activate=true：activateCount=1，flush 后 openedNodeId/selectedId=W', () => {
  const f = createFlowState();
  f.singleAddThenActivate('W', true);
  assert.equal(f.state.activateCount, 1);
  assert.equal(f.state.selectedId, 'W');
  assert.equal(f.state.currSelected, 'W');
  f.flush();
  assert.equal(f.state.openedNodeId, 'W');
  assert.equal(f.state.showNodeConfigDrawer, true);
});

// handleWorkflow activate=false（模板加载/复制/替换/历史回放等非用户新增调用）：
// 完全不激活，保护既有行为。
check('handleWorkflow activate=false：activateCount=0，flush 后无选中无抽屉', () => {
  const f = createFlowState();
  f.singleAddThenActivate('W', false);
  assert.equal(f.state.activateCount, 0);
  assert.equal(f.state.selectedId, null);
  assert.equal(f.state.currSelected, '');
  f.flush();
  assert.equal(f.state.openedNodeId, null);
  assert.equal(f.state.showNodeConfigDrawer, false);
});

// handleWorkflow 新增 W 后 250ms 内删除 W：节点存在性守卫，不打开抽屉。
check('handleWorkflow 新增 W 后删除 W：flush 后 openedNodeId=null', () => {
  const f = createFlowState();
  f.singleAddThenActivate('W', true);
  f.deleteNode('W');
  f.flush();
  assert.equal(f.state.openedNodeId, null);
});

// ===========================================================================
// 四、Review-2 P1：新增 Workflow 确认弹窗取消不触发新增/激活
// ===========================================================================
//
// 背景：addAgent 创建“新增子工作流”确认弹窗（UpdateNodeModalComponent）。用户点
// OK 时 close()→modalRef.close(true)，点取消时 dismiss()→modalRef.close(false)，
// 点 X 关闭（nzClosable）触发 destroy→afterClose 以 undefined 触发。原先
// afterClose.subscribe(() => {...}) 忽略 result，无论确认/取消/X 都调用
// handleWorkflow(info, true)（或 multiFlowType 的 node:click），导致取消操作仍
// 创建并激活新子工作流节点、打开配置抽屉，破坏用户原有选择。
//
// 修复：afterClose 回调以 shouldProceedAfterWorkflowConfirm(result) 判定——仅确认
// （result===true）时才创建/激活；取消（false）或 X 关闭（undefined）一律不创建、
// 不激活、不改变已有选择。纯决策抽出便于在纯 Node 环境覆盖各 result 分支。

// —— 纯决策 shouldProceedAfterWorkflowConfirm ——
check('shouldProceedAfterWorkflowConfirm(true)：确认成功 → 继续', () =>
  assert.equal(shouldProceedAfterWorkflowConfirm(true), true),
);

check('shouldProceedAfterWorkflowConfirm(false)：取消 → 不继续', () =>
  assert.equal(shouldProceedAfterWorkflowConfirm(false), false),
);

check('shouldProceedAfterWorkflowConfirm(undefined)：X 关闭/destroy → 不继续', () =>
  assert.equal(shouldProceedAfterWorkflowConfirm(undefined), false),
);

check('shouldProceedAfterWorkflowConfirm(null)：缺省值 → 不继续（防御）', () =>
  assert.equal(shouldProceedAfterWorkflowConfirm(null), false),
);

check('shouldProceedAfterWorkflowConfirm(1)：非布尔真值 → 不继续（严格 === true）', () =>
  assert.equal(shouldProceedAfterWorkflowConfirm(1), false),
);

// —— addAgent 确认弹窗入口时序不变量 ——
//
// 确认（true）：创建并激活 Workflow 节点，flush 后选中并打开抽屉。
check('确认弹窗 OK：activateCount=1，flush 后 openedNodeId/selectedId=W', () => {
  const f = createFlowState();
  f.confirmThenAddWorkflow(true, 'W', true);
  assert.equal(f.state.activateCount, 1);
  assert.equal(f.state.selectedId, 'W');
  assert.equal(f.state.currSelected, 'W');
  assert.equal(f.graph.has('W'), true); // 节点已创建
  f.flush();
  assert.equal(f.state.openedNodeId, 'W');
  assert.equal(f.state.showNodeConfigDrawer, true);
});

// 取消（false）：不创建、不激活、不改变已有选择，W 不进入 graph。
check('确认弹窗取消(false)：activateCount=0，无选中无抽屉，W 未创建', () => {
  const f = createFlowState();
  f.confirmThenAddWorkflow(false, 'W', true);
  assert.equal(f.state.activateCount, 0);
  assert.equal(f.state.selectedId, null);
  assert.equal(f.state.currSelected, '');
  assert.equal(f.graph.has('W'), false); // 节点未创建
  f.flush();
  assert.equal(f.state.openedNodeId, null);
  assert.equal(f.state.showNodeConfigDrawer, false);
});

// 关键：取消必须不破坏用户原有选择。已选中并打开 A，再取消新增 W → A 仍选中、
// A 抽屉仍打开、activateCount 不增、W 未创建（修复前会错误激活 W 并打开其抽屉）。
check('已选中 A 后取消新增 W：A 选择/抽屉保持不变，W 未创建', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.activateNewNode('A', PLAN_CONFIG);
  f.flush();
  // 基线：A 已选中并打开
  assert.equal(f.state.selectedId, 'A');
  assert.equal(f.state.openedNodeId, 'A');
  assert.equal(f.state.showNodeConfigDrawer, true);
  assert.equal(f.state.activateCount, 1);
  // 取消新增 W
  f.confirmThenAddWorkflow(false, 'W', true);
  assert.equal(f.state.selectedId, 'A'); // 原选择不变
  assert.equal(f.state.currSelected, 'A');
  assert.equal(f.state.openedNodeId, 'A'); // 原抽屉仍打开
  assert.equal(f.state.showNodeConfigDrawer, true);
  assert.equal(f.state.activateCount, 1); // 不增
  assert.equal(f.graph.has('W'), false); // W 未创建
});

// 对照：已选中 A 后确认新增 W → 切换到 W，A 抽屉被关闭，W 打开（与取消对比）。
check('已选中 A 后确认新增 W：切换到 W，A 抽屉关闭，flush 后 W 打开', () => {
  const f = createFlowState();
  f.graph.add('A');
  f.activateNewNode('A', PLAN_CONFIG);
  f.flush();
  assert.equal(f.state.openedNodeId, 'A');
  // 确认新增 W
  f.confirmThenAddWorkflow(true, 'W', true);
  assert.equal(f.state.selectedId, 'W');
  assert.equal(f.state.currSelected, 'W');
  f.flush();
  assert.equal(f.state.openedNodeId, 'W');
  assert.equal(f.state.showNodeConfigDrawer, true);
  assert.equal(f.state.activateCount, 2); // A + W
});

// eslint-disable-next-line no-console
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exit(1);
}
