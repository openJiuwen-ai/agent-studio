import type { IWorkflowFieldType } from '../node.type';

/**
 * set-variable（变量赋值）节点：左值类型归一相关的**纯判定函数**。
 * 抽出以便脱离 Angular 环境用 ts-node 做单测（对齐 pending-open-node.util 的范式），
 * 并让 init / onRefUpdate / onLeftSelect 共用同一份判定，避免多处镜像实现漂移。
 */

/** 支持"空值/运算"来源的目标类型集合（与业务既有口径一致）。 */
export const HAS_EMPTY_TYPE = [
  'integer',
  'number',
  'string',
  'boolean',
  'object',
  'array<string>',
  'array<number>',
  'array<integer>',
];

/** 左值类型是否为复杂类型（对象 / 数组）。 */
export function isComplexLeftType(type: string | undefined): boolean {
  const t = (type || '').toLowerCase();
  return t === 'object' || t.startsWith('array');
}

/** literal 各类型的默认内容：integer/number→0、boolean→false、其余→''。 */
export function defaultLiteralContent(
  type: IWorkflowFieldType,
): string | number | boolean {
  if (type === 'boolean') {
    return false;
  }
  if (type === 'integer' || type === 'number') {
    return 0;
  }
  return '';
}

/**
 * 右值"来源"(ref/literal/operator) 是否应回退为 ref：
 * - 已是 ref：不回退；
 * - 当前来源已不在可选集合（sourceStillValid=false），或
 * - 左值为复杂类型时 literal 不可选。
 */
export function shouldRevertSourceToRef(
  rightSource: string | undefined,
  sourceStillValid: boolean,
  isComplex: boolean,
): boolean {
  if (rightSource === 'ref') {
    return false;
  }
  return !sourceStillValid || (isComplex && rightSource === 'literal');
}

/** 当前选中的引用节点是否已被窄化为 disabled（类型不再匹配）。 */
export function isMismatchedRefSelected(content: unknown): boolean {
  const node: any = Array.isArray(content) ? content[0] : content;
  return !!node?.disabled;
}

/** 当前运算符是否仍在新类型的运算符菜单中（不合法则需归一）。 */
export function isOperatorOptionValid(
  operatorOpts: Array<{ value: unknown }> | undefined,
  operator: unknown,
): boolean {
  return !!operatorOpts && operatorOpts.some((option) => option.value === operator);
}
