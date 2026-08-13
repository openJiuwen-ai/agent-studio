/*
 * 聚焦回归测试：资源选择抽屉在“选择成功”后自动关闭
 *
 * Bug：在工作流画布新增工作流/插件/MCP 后，右侧资源选择抽屉（由
 * useAddPluginModal/useAddFlowModal/useAddMcpModal 通过 NzDrawerService.create()
 * 创建的动态抽屉）没有关闭。
 *
 * 说明（沿用项目既有 tests/*.test.cjs 纯逻辑方式，不引入新测试框架）：
 * - 该项目测试体系（jest 未安装、karma 配置为空）无法实例化 Angular 组件，
 *   亦不能 import flow.component.ts（会触发 Angular/X6 运行时）。
 * - 因此把“选择成功后关闭本次抽屉”的核心逻辑抽成无 Angular 依赖的纯函数
 *   withDrawerAutoClose（utils/drawer-auto-close.util.ts），本测试用已安装的
 *   typescript.transpileModule + Node Module._compile 直接加载该真实 .ts 源码
 *   做行为断言：不经过 Angular/X6、不读取项目 tsconfig（避免
 *   moduleResolution:bundler 与 commonjs 冲突）。
 * - 另读取 flow.component.ts 源码文本（与既有测试读取 i18n JSON 同样方式），
 *   断言三个工厂方法 useAddPluginModal/useAddFlowModal/useAddMcpModal 各自方法体
 *   内已接线 withDrawerAutoClose（覆盖 plugin/workflow/mcp 三类）。
 *
 * 运行：node tests/drawer-auto-close.test.cjs
 */
'use strict';

const fs = require('fs');
const path = require('path');
const ts = require('typescript');
const Module = require('module');

const HELPER_PATH = path.join(
  __dirname,
  '..',
  'src',
  'routes',
  'agent-center',
  'app-flow',
  'utils',
  'drawer-auto-close.util.ts',
);
const FLOW_COMPONENT_PATH = path.join(
  __dirname,
  '..',
  'src',
  'routes',
  'agent-center',
  'app-flow',
  'flow',
  'flow.component.ts',
);

const failures = [];

function assert(cond, msg) {
  if (!cond) {
    failures.push(msg);
  }
}

function assertEqual(actual, expected, msg) {
  if (actual !== expected) {
    failures.push(`${msg}（期望 ${JSON.stringify(expected)}，实际 ${JSON.stringify(actual)}）`);
  }
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function makeRef(closeSpy) {
  return { close: closeSpy };
}

// ---- 加载真实生产 helper（withDrawerAutoClose）----
function loadHelper() {
  if (!fs.existsSync(HELPER_PATH)) {
    failures.push(
      `未实现 withDrawerAutoClose：缺失 ${path.relative(process.cwd(), HELPER_PATH)}`,
    );
    return null;
  }
  const src = fs.readFileSync(HELPER_PATH, 'utf8');
  const { outputText } = ts.transpileModule(src, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  });
  const m = new Module(HELPER_PATH, module);
  m.filename = HELPER_PATH;
  m.paths = module.paths;
  m._compile(outputText, HELPER_PATH);
  const exported = m.exports;
  if (typeof exported.withDrawerAutoClose !== 'function') {
    failures.push('withDrawerAutoClose 未导出为函数');
    return null;
  }
  return exported.withDrawerAutoClose;
}

// ---- 源码接线断言：三个工厂方法体内都接了 withDrawerAutoClose ----
function assertFactoryWired(flowSrc, factoryName) {
  const defMarker = `private ${factoryName}(`;
  const defIdx = flowSrc.indexOf(defMarker);
  if (defIdx < 0) {
    failures.push(`未找到 ${factoryName} 定义（${defMarker}）`);
    return;
  }
  // 自定义义所在行起，到下一个“同类方法定义”为止为该方法体。
  const lines = flowSrc.slice(defIdx).split('\n');
  // 首行是定义；从第 2 行起找下一个 2-空格缩进的方法/访问器定义。
  const nextDefRe = /^  (private|public|protected|get|set)\s+\w+\s*[\(<]/;
  let body = lines[0] + '\n';
  for (let i = 1; i < lines.length; i++) {
    if (nextDefRe.test(lines[i])) {
      break;
    }
    body += lines[i] + '\n';
  }
  if (!body.includes('withDrawerAutoClose(')) {
    failures.push(
      `${factoryName} 方法体内未接线 withDrawerAutoClose（资源选择抽屉不会被关闭）`,
    );
  }
}

(async () => {
  // =====================================================================
  // 一、行为断言：withDrawerAutoClose 的 close 调用语义（plugin/workflow/mcp）
  // =====================================================================
  const withDrawerAutoClose = loadHelper();
  if (withDrawerAutoClose) {
    // 1) plugin（同步回调）成功 → close 被调用，且参数原样透传
    {
      let closed = 0;
      const ref = makeRef(() => closed++);
      let receivedPlugin = null;
      const wrapped = withDrawerAutoClose((plugin) => {
        receivedPlugin = plugin;
      }, () => ref);
      await wrapped({ id: 'p1', name: 'plugin-a' });
      assert(closed === 1, 'plugin: 同步成功后 close 应被调用一次');
      assertEqual(
        receivedPlugin && receivedPlugin.id,
        'p1',
        'plugin: 回调应收到原始 plugin 参数',
      );
    }

    // 2) workflow（同步回调，参数 {workflow, config}）成功 → close 被调用
    {
      let closed = false;
      const ref = makeRef(() => (closed = true));
      let receivedWorkflow = null;
      const wrapped = withDrawerAutoClose(({ workflow, config }) => {
        receivedWorkflow = workflow;
      }, () => ref);
      await wrapped({ workflow: { id: 'wf-1' }, config: { x: 1 } });
      assert(closed, 'workflow: 同步成功后 close 应被调用');
      assertEqual(receivedWorkflow && receivedWorkflow.id, 'wf-1', 'workflow: 参数解构正常');
    }

    // 3) mcp（异步回调）成功 → close 仅在异步初始化/节点创建完成后才被调用
    {
      let closed = false;
      const ref = makeRef(() => (closed = true));
      let initDone = false;
      const wrapped = withDrawerAutoClose(async (mcpService) => {
        await delay(5); // 模拟 getInitMcpNodeData 异步初始化
        initDone = true;
        return mcpService;
      }, () => ref);
      const p = wrapped({ id: 'mcp-1' });
      assert(!closed, 'mcp: 异步回调完成前 close 不应被调用');
      assert(!initDone, 'mcp: 异步初始化应尚未完成');
      await p;
      assert(initDone, 'mcp: 异步初始化应已完成');
      assert(closed, 'mcp: 异步成功完成后 close 应被调用');
    }

    // 4) plugin 同步失败（throw）→ close 不被调用，且错误被上抛/记录而非静默吞掉
    {
      let closed = false;
      const ref = makeRef(() => (closed = true));
      const errors = [];
      const origError = console.error;
      console.error = (...args) => errors.push(args[0]);
      let threw = false;
      try {
        const wrapped = withDrawerAutoClose(() => {
          throw new Error('plugin 选择失败');
        }, () => ref);
        await wrapped({ id: 'p2' });
      } catch (e) {
        threw = true;
      } finally {
        console.error = origError;
      }
      assert(!closed, 'plugin: 同步失败时 close 不应被调用（便于用户重试）');
      // 失败必须可观测（要么抛出，要么记录），不允许既不抛也不记的静默吞掉
      assert(threw || errors.length > 0, 'plugin: 失败应可观测（抛出或记录），不得静默吞掉');
    }

    // 5) mcp 异步失败（reject）→ close 不被调用，且失败可观测
    {
      let closed = false;
      const ref = makeRef(() => (closed = true));
      const errors = [];
      const origError = console.error;
      console.error = (...args) => errors.push(args[0]);
      let threw = false;
      try {
        const wrapped = withDrawerAutoClose(async () => {
          await delay(5);
          throw new Error('mcp 初始化失败');
        }, () => ref);
        await wrapped({ id: 'mcp-2' });
      } catch (e) {
        threw = true;
      } finally {
        console.error = origError;
      }
      assert(!closed, 'mcp: 异步失败时 close 不应被调用（便于用户重试）');
      assert(threw || errors.length > 0, 'mcp: 异步失败应可观测，不得静默吞掉');
    }

    // 6) getter 返回 null/undefined（ref 未就绪）→ 不抛错、不调用 close
    {
      let closed = false;
      let threw = false;
      try {
        const wrapped = withDrawerAutoClose(() => {}, () => undefined);
        await wrapped({});
      } catch (e) {
        threw = true;
      }
      assert(!threw, 'drawerRef 为空时不应抛错');
      assert(!closed, 'drawerRef 为空时不应调用 close');
    }

    // 7) 关闭的是“本次工厂调用各自独立局部 drawerRef”捕获的实例，而非
    //    另一次同类抽屉的实例。真实工厂每次调用各自声明局部
    //    `let drawerRef`（互不覆盖），getter 仅返回本次局部 ref；故快速打开
    //    另一个同类抽屉不会让前者的回调关闭后者（this.*ModalRef 被覆盖的隐患
    //    已通过使用局部 ref 规避）。
    {
      const refA = makeRef(() => {});
      const refB = makeRef(() => {});
      let aClosed = false;
      let bClosed = false;
      refA.close = () => (aClosed = true);
      refB.close = () => (bClosed = true);
      // 第一次工厂调用：独立局部 drawerRefA，最终赋值为 refA
      let drawerRefA;
      const onSelectA = withDrawerAutoClose(() => {}, () => drawerRefA);
      drawerRefA = refA;
      // 第二次工厂调用：另一个独立局部 drawerRefB（覆盖的是不同局部变量，
      // 不影响第一次的 drawerRefA）
      let drawerRefB;
      const onSelectB = withDrawerAutoClose(() => {}, () => drawerRefB);
      drawerRefB = refB;
      // 第一次的选择成功回调：只应关闭 refA
      await onSelectA({});
      assert(aClosed, '应关闭本次（A）抽屉实例');
      assert(!bClosed, '不得因后续打开同类抽屉而误关 B 实例（局部 ref 规避覆盖隐患）');
    }
  }

  // =====================================================================
  // 二、源码接线断言：flow.component.ts 三个工厂均接了 withDrawerAutoClose
  // =====================================================================
  if (!fs.existsSync(FLOW_COMPONENT_PATH)) {
    failures.push(`未找到 flow.component.ts：${FLOW_COMPONENT_PATH}`);
  } else {
    const flowSrc = fs.readFileSync(FLOW_COMPONENT_PATH, 'utf8');
    assertFactoryWired(flowSrc, 'useAddPluginModal');
    assertFactoryWired(flowSrc, 'useAddFlowModal');
    assertFactoryWired(flowSrc, 'useAddMcpModal');
  }

  if (failures.length) {
    console.error('FAIL（' + failures.length + ' 项）：');
    failures.forEach((f) => console.error('  - ' + f));
    process.exit(1);
  }

  console.log(
    'PASS：plugin/workflow/mcp 选择成功后 close 被调用、失败不关闭且可观测、空 ref 安全、仅关本次实例；三个工厂均已接线 withDrawerAutoClose',
  );
})();
