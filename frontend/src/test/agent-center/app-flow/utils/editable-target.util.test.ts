/**
 * isEditableTarget 的最小可运行单元测试。
 *
 * 运行方式（项目内已安装 ts-node，无需引入大规模测试基础设施）：
 *   cd frontend
 *   pnpm exec ts-node --compiler-options '{"module":"commonjs","moduleResolution":"node"}' \
 *     src/test/agent-center/app-flow/utils/editable-target.util.test.ts
 *
 * 说明：项目的 Karma 配置 (src/test/karma.conf.js) 是空壳且本环境无 Chrome，
 * 无法可靠运行 Angular/X6 组件级测试；故对纯函数 isEditableTarget 抽离出
 * DOM 无关的核心 isEditableElement，用 duck-typed 对象在纯 Node 环境下覆盖
 * input/textarea/select/contenteditable/Monaco/画布/抽屉非编辑区域等场景。
 * 测试代码集中置于 src/test/ 下，与源码分离；通过相对路径回引 routes 源文件。
 */
import assert from 'node:assert/strict';
import {
  isEditableElement,
  isEditableTarget,
  EditableElementLike,
} from '../../../../routes/agent-center/app-flow/utils/editable-target.util';

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

// 构造 duck-typed 元素，控制 closest 的命中行为以模拟 Monaco/Quill 等编辑器宿主。
function fakeEl(opts: {
  tag?: string;
  isContentEditable?: boolean;
  closestHit?: boolean;
}): EditableElementLike {
  return {
    tagName: opts.tag ?? 'DIV',
    isContentEditable: opts.isContentEditable ?? false,
    closest: () => (opts.closestHit ? ({} as Element) : null),
  };
}

// —— isEditableElement：核心判定（覆盖可编辑控件应被拦截）——
check('input 拦截', () => assert.equal(isEditableElement(fakeEl({tag: 'INPUT'})), true));
check('textarea 拦截', () => assert.equal(isEditableElement(fakeEl({tag: 'TEXTAREA'})), true));
check('select 拦截', () => assert.equal(isEditableElement(fakeEl({tag: 'SELECT'})), true));
check('contenteditable 拦截', () =>
  assert.equal(isEditableElement(fakeEl({isContentEditable: true})), true),
);
check('Monaco 子节点拦截（closest 命中 .monaco-editor）', () =>
  assert.equal(isEditableElement(fakeEl({closestHit: true})), true),
);
check('Quill/Draft/ProseMirror 同样经 closest 命中拦截', () =>
  assert.equal(isEditableElement(fakeEl({closestHit: true})), true),
);

// —— isEditableElement：核心判定（覆盖画布与抽屉非编辑区域应允许删除）——
check('画布 DIV 不拦截（无 closest 命中、非可编辑）', () =>
  assert.equal(isEditableElement(fakeEl({tag: 'DIV'})), false),
);
check('抽屉外壳 DIV 不拦截', () =>
  assert.equal(isEditableElement(fakeEl({tag: 'DIV'})), false),
);
check('按钮不拦截', () => assert.equal(isEditableElement(fakeEl({tag: 'BUTTON'})), false));
check('tab 容器不拦截', () =>
  assert.equal(isEditableElement(fakeEl({tag: 'DIV'})), false),
);
check('SVG/circle 之外的非可编辑元素不拦截', () =>
  assert.equal(isEditableElement(fakeEl({tag: 'SPAN'})), false),
);
check('null 不拦截', () => assert.equal(isEditableElement(null), false));
check('undefined 不拦截', () => assert.equal(isEditableElement(undefined), false));

// —— isEditableTarget：EventTarget 适配 + SSR/类型安全（不能抛错）——
check('null target 不拦截且不抛错', () =>
  assert.equal(isEditableTarget(null), false),
);
check('undefined target 不拦截且不抛错', () =>
  assert.equal(isEditableTarget(undefined), false),
);
check('字符串 target 不拦截且不抛错', () =>
  assert.equal(isEditableTarget('foo' as unknown as EventTarget), false),
);
check('普通对象 target 不拦截且不抛错', () =>
  assert.equal(isEditableTarget({} as unknown as EventTarget), false),
);

// SSR/非 DOM 环境模拟：临时移除全局 HTMLElement，函数不得抛错且返回 false。
check('SSR（HTMLElement 未定义）不抛错且不拦截', () => {
  const orig = (globalThis as {HTMLElement?: unknown}).HTMLElement;
  delete (globalThis as {HTMLElement?: unknown}).HTMLElement;
  try {
    assert.equal(isEditableTarget(null), false);
    assert.equal(isEditableTarget({} as unknown as EventTarget), false);
  } finally {
    (globalThis as {HTMLElement?: unknown}).HTMLElement = orig;
  }
});

// eslint-disable-next-line no-console
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exit(1);
}
