/**
 * 模型API地址环境变量占位符格式转换工具
 */

/**
 * 将后台存储格式${_env.plugin_url_params.VAR}转换为用户显示格式{VAR}
 */
export function convertModelApiUrlToUserFormat(backendValue: string): string {
  if (!backendValue) return backendValue;
  return backendValue.replace(/\$\{_env\.plugin_url_params\.([a-zA-Z_$][a-zA-Z0-9_$]*)\}/g,
    (_, varName) => `{${varName}}`);
}

/**
 * 将用户输入的{VAR}格式转换为后台存储格式${_env.plugin_url_params.VAR}
 * 仅当输入整串为{VAR}占位符时才转换，避免误转换URL路径中的{param}段
 */
export function convertModelApiUrlToBackendFormat(userInput: string): string {
  if (!userInput) return userInput;
  const trimmed = userInput.trim();
  // 严格匹配整串为 {合法变量名} 格式才转换
  const match = /^\{([a-zA-Z_$][a-zA-Z0-9_$]*)\}$/.exec(trimmed);
  if (match) {
    return `\${_env.plugin_url_params.${match[1]}}`;
  }
  // 普通URL原样返回，不做任何替换
  return userInput;
}

/** 后端存储格式占位符：${_env.plugin_url_params.VAR}（子串匹配，任意位置出现即算） */
const BACKEND_ENV_PLACEHOLDER = /\$\{_env\.plugin_url_params\.[a-zA-Z_$][a-zA-Z0-9_$]*\}/;
/** 后端存储格式整串占位符：整串就是 ${_env.plugin_url_params.VAR} */
const BACKEND_ENV_PLACEHOLDER_FULL = /^\$\{_env\.plugin_url_params\.[a-zA-Z_$][a-zA-Z0-9_$]*\}$/;
/** 用户格式纯占位符：{VAR}（整串匹配）；注意：不把 URL 路径中的 {param} 段误判为占位符 */
export const USER_ENV_PLACEHOLDER = /^\{[a-zA-Z_$][a-zA-Z0-9_$]*\}$/;
/** 用户格式空占位符：{}（点击 {} 按钮未填变量名时的初始值） */
export const USER_EMPTY_PLACEHOLDER = '{}';
/** 合法 http(s) URL（不含未转义花括号） */
export const USER_URL_PATTERN = /^https?:\/\/[^{}\s]+$/i;

/** api_url 是否含环境变量占位符。同时识别后端格式(${_env...})与用户格式({VAR})，
 *  因为不同入口存的 api_url 格式不同（model-detail 详情页已转成用户格式，列表接口若返回则为后端原格式）。
 *  含占位符 → 该模型 URL 运行期才解析，发布期可用性探测无意义，应跳过 available_check。 */
export function hasEnvPlaceholder(apiUrl: string | undefined | null): boolean {
  const v = (apiUrl || '').trim();
  if (!v) return false;
  return BACKEND_ENV_PLACEHOLDER.test(v) || USER_ENV_PLACEHOLDER.test(v) || v === USER_EMPTY_PLACEHOLDER;
}

/** api_url 是否是整串占位符(后端存的完整 ${_env...} 或 用户输入的 {VAR} / {})，
 *  这类值保存时应跳过 URL/SSRF 校验（运行期才解析）。 */
export function isFullPlaceholder(apiUrl: string | undefined | null): boolean {
  const v = (apiUrl || '').trim();
  if (!v) return false;
  return v === USER_EMPTY_PLACEHOLDER
    || USER_ENV_PLACEHOLDER.test(v)
    || BACKEND_ENV_PLACEHOLDER_FULL.test(v);
}
