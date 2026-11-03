/**
 * 重命名输入变量时，只替换 Jinja `{{ name }}` 完整 token，避免误伤共享前缀
 *（如 data 与 data_items）。边界：空白、`.`、`[`、`|`、或 `}}`。
 */
export function rewriteTemplateInputRefs(template: string, oldName: string, newName: string): string {
  if (!template || !oldName || oldName === newName) {
    return template;
  }
  const escaped = oldName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const re = new RegExp(`(\\{\\{)(\\s*)${escaped}(?=\\s|[.\\[|]|\\}\\})`, 'g');
  return template.replace(re, (_match, open: string, ws: string) => `${open}${ws}${newName}`);
}
