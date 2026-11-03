import {
  convertToSandboxFormat,
} from '../../routes/agent-center/app-flow/utils/dify-code-format.util';

// bug① 哨兵：Dify 代码 → jiuwen 沙箱格式转换矩阵。
// 关键不变量：
// 1. 签名参数列表 == 变量名列表才转换（行级替换：只换签名 + 插解包行）；
// 2. 定位不到 def main / 括号不配对 / 参数不一致时原样返回——绝不落 DEFAULT_CODE，
//    否则复刻"导入后代码丢失"bug；
// 3. def 前的 import 与函数体（含嵌套 helper）原样保留。
// 背景见 bugfix 文档《Dify导入代码节点代码丢失.md》。

describe('convertToSandboxFormat — 转换分支（参数==变量名）', () => {
  it('单变量：签名替换 + 解包行', () => {
    const code = 'def main(user: dict) -> dict:\n    return {"a": user.get("x")}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "    user = args.get('user')\n" +
      '    return {"a": user.get("x")}\n');
  });

  it('多变量：按序生成解包行，函数体保留', () => {
    const code = 'def main(fallback: dict, llm_json: dict, thought: str) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['fallback', 'llm_json', 'thought']);
    expect(out).toContain('def main(args: dict) -> dict:');
    expect(out).toContain("    fallback = args.get('fallback')");
    expect(out).toContain("    llm_json = args.get('llm_json')");
    expect(out).toContain("    thought = args.get('thought')");
    expect(out).toContain('    return {}');
  });

  it('def 前的 import 原样保留（客户 yml 多节点如此）', () => {
    const code = 'import json\nimport re\n\ndef main(user: dict) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['user']);
    expect(out.startsWith('import json\nimport re\n\n')).toBe(true);
    expect(out).toContain("    user = args.get('user')");
  });

  it('变量名恰好为 args：仍属 Dify 风格需转换（名字遮蔽语义正确）', () => {
    const code = 'def main(args: dict) -> dict:\n    return {"r": args}\n';
    const out = convertToSandboxFormat(code, ['args']);
    expect(out).toContain("    args = args.get('args')");
  });

  it('变量名含 args 且非末位：args 解包行最后生成，避免遮蔽后续读取（检视 #1）', () => {
    const code = 'def main(args: dict, other: str) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['args', 'other']);
    const lines = out.split('\n');
    const argsIdx = lines.findIndex(l => l === "    args = args.get('args')");
    const otherIdx = lines.findIndex(l => l === "    other = args.get('other')");
    expect(argsIdx).toBeGreaterThan(-1);
    expect(otherIdx).toBeGreaterThan(-1);
    expect(argsIdx).toBeGreaterThan(otherIdx, 'args 解包行必须在 other 之后（最后）');
  });

  it('变量名含 args 且为末位：顺序不变（other 在前，args 收尾）', () => {
    const code = 'def main(other: str, args: dict) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['other', 'args']);
    expect(out).toBe(
      'def main(args: dict) -> dict:\n' +
      "    other = args.get('other')\n" +
      "    args = args.get('args')\n" +
      '    return {}\n');
  });

  it('跨行签名（括号换行）也能定位', () => {
    const code = 'def main(\n    user: dict,\n    thought: str\n) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['user', 'thought']);
    expect(out).toContain('def main(args: dict) -> dict:');
    expect(out).toContain("    user = args.get('user')");
    expect(out).toContain("    thought = args.get('thought')");
  });

  it('参数带默认值：去默认值后按名匹配', () => {
    const code = 'def main(user: dict = None) -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, ['user'])).toContain("    user = args.get('user')");
  });

  it('无参数签名 + 空变量列表：仅替换签名，无解包行', () => {
    const code = 'def main() -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, [])).toBe('def main(args: dict) -> dict:\n    return {}\n');
  });
});

describe('convertToSandboxFormat — 原样返回分支（绝不落 DEFAULT_CODE）', () => {
  it('空代码原样返回', () => {
    expect(convertToSandboxFormat('', ['user'])).toBe('');
  });

  it('无 def main 原样返回', () => {
    const code = 'import os\n\n# no main here\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(code);
  });

  it('参数与变量名不一致原样返回（交用户手动调整）', () => {
    const code = 'def main(a: dict, b: str) -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, ['x', 'y'])).toBe(code);
  });

  it('参数顺序不一致也原样返回', () => {
    const code = 'def main(b: str, a: dict) -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, ['a', 'b'])).toBe(code);
  });

  it('括号不配对原样返回', () => {
    const code = 'def main(user: dict -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(code);
  });
});

describe('convertToSandboxFormat — 解析失败兜底（层 2：用变量名生成解包行）', () => {
  it('*args 签名：解析失败但变量名可用 → 按变量名解包', () => {
    const code = 'def main(*args) -> dict:\n    return {}\n';
    const out = convertToSandboxFormat(code, ['user']);
    expect(out).toContain('def main(args: dict) -> dict:');
    expect(out).toContain("    user = args.get('user')");
  });

  it('解析失败且无变量名 → 原样返回（层 3）', () => {
    const code = 'def main(*args) -> dict:\n    return {}\n';
    expect(convertToSandboxFormat(code, [])).toBe(code);
  });
});

describe('convertToSandboxFormat — 函数体保真', () => {
  it('体内嵌套 helper def 原样保留，不受签名替换影响', () => {
    const body = '    def pick(key, default=""):\n        v = user.get(key)\n        return v if v not in (None, "") else default\n';
    const code = `def main(user: dict) -> dict:\n${body}    return {}\n`;
    const out = convertToSandboxFormat(code, ['user']);
    expect(out).toContain(body);
    expect(out).toContain('def main(args: dict) -> dict:');
    expect(out.match(/def pick/g)?.length).toBe(1);
  });
});

describe('convertToSandboxFormat — 缩进沿用原体（检视 #3）', () => {
  it('2 空格缩进体：解包行沿用 2 空格，不产生 IndentationError', () => {
    const code = 'def main(user: dict) -> dict:\n  return {"a": user.get("x")}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "  user = args.get('user')\n" +
      '  return {"a": user.get("x")}\n');
  });

  it('tab 缩进体：解包行沿用 tab', () => {
    const code = 'def main(user: dict) -> dict:\n\treturn {}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "\tuser = args.get('user')\n" +
      '\treturn {}\n');
  });

  it('体首个有效行前有空行/纯注释行：跳过它们检测真实体缩进', () => {
    const code = 'def main(user: dict) -> dict:\n\n# 注释在 0 列（合法，不决定块缩进）\n  return {}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "  user = args.get('user')\n" +
      '\n' +
      '# 注释在 0 列（合法，不决定块缩进）\n' +
      '  return {}\n');
  });

  it('单行 def：体移到解包行后独立成行（原实现会拼出同行 SyntaxError）', () => {
    const code = 'def main(user): return {"r": 1}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "    user = args.get('user')\n" +
      '    return {"r": 1}\n');
  });

  it('单行 def 带同行尾注释：注释一并移为独立行，合法且语义不变', () => {
    const code = 'def main(user):  # 尾注释\n    return {}\n';
    expect(convertToSandboxFormat(code, ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "    user = args.get('user')\n" +
      '    # 尾注释\n' +
      '    return {}\n');
  });

  it('无有效体行（def 后即 EOF）：回退默认 4 空格', () => {
    expect(convertToSandboxFormat('def main(user):', ['user'])).toBe(
      'def main(args: dict) -> dict:\n' +
      "    user = args.get('user')");
  });
});
