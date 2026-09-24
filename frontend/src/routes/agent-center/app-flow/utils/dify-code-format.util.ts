/**
 * Dify 代码节点 → jiuwen 沙箱兼容格式转换工具。
 *
 * 背景：Dify 导入工作流时，后端 CodeNodeConverter 正确保留代码（configs.code），
 * 但前端 dify-migrate-modal 的 code-compare 组件在平台未配置 FunctionGraph 时
 * （code_env_options 默认 ["sandbox","local"] 不含 fg），直接用 DEFAULT_CODE 默认模板
 * 覆盖 configs.code，导致所有代码节点业务逻辑丢失（详见 bugfix 文档
 * 《Dify导入代码节点代码丢失.md》）。
 *
 * 调用约定差异（转换必要性）：
 * - Dify：main(变量1, 变量2, ...) 按输入变量名逐个命名传参；
 * - jiuwen 沙箱：main(args) 单参数，args 为所有输入变量的 dict
 *   （runtime base_code_runner.build_wrapped_code：`args = {inputs}; main(args)`，
 *   args 的 key = 输入字段名，见 flow_code._coerce_inputs 按 field_def["id"] 遍历）。
 * 直接预填 Dify 代码会：单变量节点语义错位（参数收到整个 args dict，静默取空值）、
 * 多变量节点 TypeError。
 *
 * 转换方式（行级替换，不做函数体重组）：
 * 只把 `def main(参数)` 签名替换为 `def main(args: dict) -> dict:` 并在其后插入
 * 参数解包行；def 前的 import 语句与函数体（含 helper 函数）原样保留
 * （实证：客户 yml 14 个代码节点中多个 def 前有 import）。
 *
 * 转换判定（按签名参数与变量名的一致性，不按参数名是否为 'args'）：
 * Dify 导入路径上代码均为 Dify 风格；`def main(args)` 出现意味着变量名恰好叫 'args'
 * （Dify 按名传参），仍属 Dify 风格需转换。解包行 `args = args.get('args')` 为
 * Python 合法的名字遮蔽；变量名含 args 时该行最后生成，避免遮蔽后续解包行的读取。
 *
 * 分层回退：
 * 1. def main 定位 + 参数解析成功 且 参数列表==变量名列表 → 转换；
 * 2. def main 定位到但参数解析失败 → 用变量名列表生成解包行
 *    （Dify"参数==变量名"不变量，14/14 节点实证成立）；
 * 3. 定位不到 def main / 括号不配对 / 无变量名可兜底 / 参数与变量名不一致 →
 *    原样返回，交用户在迁移弹窗右侧编辑器手动调整（显性优于错误转换）。
 */

/** 在 text 中查找首个"顶层"（不在 ()/[]/{}/ 内层）的 target 字符位置；找不到返回 -1 */
function topLevelIndexOf(text: string, target: string): number {
  let depth = 0;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth--;
    } else if (ch === target && depth === 0) {
      return i;
    }
  }
  return -1;
}

/**
 * 解析 main 签名参数文本，提取参数名列表（去类型注解、去默认值）。
 *
 * @returns 参数名列表；空签名返回 []；结构异常（空段/*args 等）返回 null 表示解析失败
 */
function parseMainParamNames(paramsText: string): string[] | null {
  const text = paramsText.trim();
  if (!text) {
    return [];
  }
  // 顶层按逗号分割（忽略默认值中 dict/list 等内层逗号）
  const segments: string[] = [];
  let depth = 0;
  let current = '';
  for (const ch of text) {
    if (ch === '(' || ch === '[' || ch === '{') {
      depth++;
    } else if (ch === ')' || ch === ']' || ch === '}') {
      depth--;
    }
    if (ch === ',' && depth === 0) {
      segments.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  segments.push(current);

  const names: string[] = [];
  for (const segment of segments) {
    let s = segment.trim();
    if (!s || s.startsWith('*')) {
      // 空参数段（连续逗号）或 *args/**kwargs：非 Dify 标准签名，走解析失败分支
      return null;
    }
    const colonIdx = topLevelIndexOf(s, ':');
    if (colonIdx >= 0) {
      s = s.slice(0, colonIdx).trim();
    }
    const eqIdx = topLevelIndexOf(s, '=');
    if (eqIdx >= 0) {
      s = s.slice(0, eqIdx).trim();
    }
    if (!s || /\s/.test(s)) {
      return null;
    }
    names.push(s);
  }
  return names;
}

function arraysEqual<T>(a: T[], b: T[]): boolean {
  return a.length === b.length && a.every((v, i) => v === b[i]);
}

/**
 * 将 Dify 风格代码转换为 jiuwen 沙箱兼容格式。
 *
 * @param code Dify 原代码（含 def main(变量...)）
 * @param variableNames 节点输入变量名列表（后端已从 Dify variables 映射为 inputs.name）
 * @returns 转换后的代码；判定不转换（结构异常/参数与变量名不一致）时原样返回入参
 */
export function convertToSandboxFormat(code: string, variableNames: string[]): string {
  if (!code) {
    return code;
  }
  // 定位 def main(（允许行首缩进；不依赖签名单行假设——括号配对扫描跨行安全）
  const defMatch = /(?:^|\n)([ \t]*)def main[ \t]*\(/.exec(code);
  if (!defMatch) {
    return code;
  }
  const defIndent = defMatch[1] ?? '';
  const defKeywordStart = defMatch.index + (defMatch[0].startsWith('\n') ? 1 : 0) + defIndent.length;
  const openParenIndex = defMatch.index + defMatch[0].length - 1;

  // 括号配对扫描找匹配的右括号
  let depth = 0;
  let closeParenIndex = -1;
  for (let i = openParenIndex; i < code.length; i++) {
    const ch = code[i];
    if (ch === '(') {
      depth++;
    } else if (ch === ')') {
      depth--;
      if (depth === 0) {
        closeParenIndex = i;
        break;
      }
    }
  }
  if (closeParenIndex < 0) {
    return code;
  }

  // 签名行尾冒号（含可能的返回注解 -> dict；泛型注解用 [] 不会引入冒号）
  const colonIndex = code.indexOf(':', closeParenIndex);
  if (colonIndex < 0) {
    return code;
  }

  const parsedParams = parseMainParamNames(code.slice(openParenIndex + 1, closeParenIndex));
  let unpackNames: string[];
  if (parsedParams === null) {
    // 参数解析失败：有变量名列表才兜底（分层回退第 2 层），否则原样保留
    if (!variableNames || variableNames.length === 0) {
      return code;
    }
    unpackNames = variableNames;
  } else if (!arraysEqual(parsedParams, variableNames ?? [])) {
    // 参数与变量名不一致：非预期 Dify 风格，原样保留交用户手动调整
    return code;
  } else {
    unpackNames = parsedParams;
  }

  // 行级替换：签名整体换成 def main(args: dict) -> dict:，其后插入解包行。
  // 解包行不带默认值（缺失=None），与 Dify 侧缺失输入即 None 的语义一致。
  // 变量名含 args 时其解包行必须最后生成：`args = args.get('args')` 会遮蔽形参 args，
  // 若 args 非末位，其后的解包行读取的已是遮蔽值而非原始入参 dict（检视意见 #1）。
  // 其余解包行只读 args 不写、相互无顺序依赖，重排安全。
  const unpackIndent = defIndent + '    ';
  const orderedNames = [
    ...unpackNames.filter(name => name !== 'args'),
    ...unpackNames.filter(name => name === 'args'),
  ];
  const unpackLines = orderedNames.map(name => `${unpackIndent}${name} = args.get('${name}')`);
  const newSignature = 'def main(args: dict) -> dict:';
  return (
    code.slice(0, defKeywordStart) +
    newSignature +
    (unpackLines.length ? '\n' + unpackLines.join('\n') : '') +
    code.slice(colonIndex + 1)
  );
}
