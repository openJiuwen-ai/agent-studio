/**
 * set-variable.util 的最小可运行单元测试（脱离 Angular，设纯函数覆盖）。
 *
 * 运行方式（项目内已安装 ts-node）：
 *   cd frontend
 *   pnpm exec ts-node --compiler-options '{"module":"commonjs","moduleResolution":"node"}' \
 *     src/test/agent-center/app-flow/utils/set-variable.util.test.ts
 */
import assert from 'node:assert/strict';
import {
  defaultLiteralContent,
  isComplexLeftType,
  isMismatchedRefSelected,
  isOperatorOptionValid,
  shouldRevertSourceToRef,
} from '../../../../routes/agent-center/app-flow/utils/set-variable.util';

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

// —— 左值复杂类型判定 ——
check('object/array 视为复杂类型', () => {
  assert.equal(isComplexLeftType('object'), true);
  assert.equal(isComplexLeftType('array<string>'), true);
  assert.equal(isComplexLeftType('Array<Object>'), true);
});
check('标量/空 不视为复杂类型', () => {
  assert.equal(isComplexLeftType('string'), false);
  assert.equal(isComplexLeftType('integer'), false);
  assert.equal(isComplexLeftType(undefined), false);
});

// —— literal 默认内容（修复 Number('abc')=NaN / 非布尔字符串）——
check('literal 默认内容按类型', () => {
  assert.equal(defaultLiteralContent('integer' as any), 0);
  assert.equal(defaultLiteralContent('number' as any), 0);
  assert.equal(defaultLiteralContent('boolean' as any), false);
  assert.equal(defaultLiteralContent('string' as any), '');
});

// —— 来源回退 ref ——
check('已是 ref 不回退', () => {
  assert.equal(shouldRevertSourceToRef('ref', false, true), false);
});
check('来源不在可选集合 → 回退', () => {
  assert.equal(shouldRevertSourceToRef('literal', false, false), true);
  assert.equal(shouldRevertSourceToRef('operator', false, false), true);
});
check('复杂左值 + literal → 回退', () => {
  assert.equal(shouldRevertSourceToRef('literal', true, true), true);
});
check('标量 + literal 仍合法 → 不回退', () => {
  assert.equal(shouldRevertSourceToRef('literal', true, false), false);
});

// —— 失效引用（被窄化为 disabled）——
check('disabled 的选中引用判为不匹配', () => {
  assert.equal(isMismatchedRefSelected([{ disabled: true }]), true);
  assert.equal(isMismatchedRefSelected({ disabled: true }), true);
});
check('未失效引用不算不匹配', () => {
  assert.equal(isMismatchedRefSelected([{ disabled: false }]), false);
  assert.equal(isMismatchedRefSelected([{}]), false);
  assert.equal(isMismatchedRefSelected(undefined), false);
});

// —— 运算符有效性 ——
check('运算符仍在菜单为有效', () => {
  assert.equal(isOperatorOptionValid([{ value: 'increment' }, { value: 'empty' }], 'increment'), true);
});
check('运算符被剔除为无效', () => {
  assert.equal(isOperatorOptionValid([{ value: 'empty' }], 'increment'), false);
  assert.equal(isOperatorOptionValid(undefined, 'empty'), false);
});

// eslint-disable-next-line no-console
console.log(`\n${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exitCode = 1;
}
