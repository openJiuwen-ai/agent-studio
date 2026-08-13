/**
 * 判断键盘事件的 target 是否位于可编辑控件内。
 *
 * 全局 Delete/Backspace 处理使用本函数区分两种场景：
 * - target 位于可编辑控件（input/textarea/select/contenteditable/Monaco/富文本编辑器）：
 *   只编辑文本，不删除画布节点；
 * - target 不位于可编辑控件（画布、抽屉外壳、按钮、tab 等非编辑元素）：
 *   删除当前 X6 选中节点/边。
 *
 * 注意：不要再用 "document.activeElement 必须是 body" 作为画布删除条件，
 * 节点切换后配置抽屉/表单遗留的焦点（往往落在非编辑元素上）会被该规则误判为编辑态，
 * 导致画布节点无法删除。
 */
const EDITABLE_SELECTOR = [
  '[contenteditable=""]',
  '[contenteditable="true"]',
  '[contenteditable="plaintext-only"]',
  'input',
  'textarea',
  'select',
  // Monaco
  '.monaco-editor',
  // 代码全屏编辑器
  '.function-graph-code-main',
  // CodeMirror
  '.CodeMirror',
  // Quill
  '.ql-editor',
  // Draft.js
  '.public-DraftEditor-content',
  // ProseMirror / 通用 ARIA 文本框
  '[role="textbox"]',
].join(',');

/**
 * 可编辑判定所需的最小元素形状。抽离为接口便于在不依赖真实 DOM（jsdom/浏览器）
 * 的环境下对判定逻辑做单元测试：测试可用 duck-typed 对象覆盖 input/textarea/
 * contenteditable/Monaco 等场景，而不需要实例化真实 HTMLElement。
 */
export interface EditableElementLike {
  tagName: string;
  isContentEditable: boolean;
  closest: (selector: string) => Element | null;
}

/**
 * 纯逻辑核心：根据元素形状判定是否位于可编辑控件。不触碰任何全局 DOM 构造器，
 * 因此可在纯 Node 环境（ts-node）下被单测。isEditableTarget() 负责把真实
 * EventTarget 适配为该形状后再委托本函数。
 */
export function isEditableElement(
  el: EditableElementLike | null | undefined,
): boolean {
  if (!el) {
    return false;
  }
  // 原生可编辑元素
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') {
    return true;
  }
  // contenteditable 元素（富文本编辑器宿主常带此属性）
  if (el.isContentEditable) {
    return true;
  }
  // Monaco / Quill / Draft / ProseMirror 等编辑器内部子节点未必带 contenteditable，
  // 向上查找已知的编辑器宿主。
  return el.closest(EDITABLE_SELECTOR) !== null;
}

export function isEditableTarget(target: EventTarget | null): boolean {
  // SSR/非 DOM 环境（HTMLElement 未定义）或 target 非 HTMLElement（Document、
  // SVGElement、Text 节点、null 等）时一律视为非可编辑控件，且不能抛错。
  if (typeof HTMLElement === 'undefined' || !(target instanceof HTMLElement)) {
    return false;
  }
  return isEditableElement(target);
}
