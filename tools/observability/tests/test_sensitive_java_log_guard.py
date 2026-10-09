#  Copyright (c) Huawei Technologies Co., Ltd. 2024-2024. All rights reserved.
"""SYNC-01 P1.3: Java 敏感值日志直出防回归（静态扫描，修正版）。

修正前版 bug：
1. rstrip(";).") 剥掉 getBody() 闭括号 → 坏代码放过（p1 实审发现）
2. 只扫单行 log.X( → 多行参数不解析（p1 实审发现）
3. 无坏例注入 → 通过不证明能捕获坏写法

修正：
1. clean_arg 按括号深度剥多余闭括号（保 getBody() 平衡）
2. _merge_continuation_lines 合并 log.X( 未在本行闭合的续行（多行覆盖）
3. split_args 按括号深度=0 的逗号 split
4. fault_injection 测试（坏代码必须失败）含多行坏例

守卫边界（不宣称全路径已锁，留人工复扫 + P7 最终树补扫；与 Runtime 守卫
口径对齐，82598163 自审复核 §2.3 补声明）：
- 复合表达式：识别敏感参数依赖变量名与 getBody() 正则，
  `String.valueOf(headers)`、`new JSONObject(headers)`、三元
  `cond ? headers : ""`、方法包装后的容器不识别（9 个受保护文件当前无
  此类写法）
- 动态构造/别名传递不追踪
P7 最终树补扫（D-05 硬门②）兜底。
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

_GUARDED_FILES = [
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/service/plugin/impl/PluginBaseImpl.java",
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/service/plugin/impl/PluginAdapterImpl.java",
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/utils/IamServiceUtils.java",
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/service/AgentManagementService.java",
    "backend/studio-space/studio-space-app/src/main/java/com/openjiuwen/studio/agent/space/app/service/client/AgentManagerService.java",
    "backend/studio-space/studio-space-app/src/main/java/com/openjiuwen/studio/agent/space/app/filter/authitem/impl/IamTokenAuthItem.java",
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/rce/service/JiuWenService.java",
    "backend/studio-manager-service/src/main/java/com/openjiuwen/studio/agent/manager/service/mcp/apigservice/apig/ApigApiService.java",
    "backend/studio-space/studio-space-app/src/main/java/com/openjiuwen/studio/agent/space/app/util/WebClientUtils.java",
]

_SENSITIVE_VARS = ("headers", "requestBody", "errorBody")
# 容许 \s*：多行合并会在 response 与 .getBody() 间插入空格（方法链跨行），
# 带空格的 `response .getBody()` 仍是敏感值，不应放过
_SENSITIVE_EXPRS = (r"response\s*\.getBody\(\)", r"responseEntity\s*\.getBody\(\)")
_SAFE_SUFFIXES = (".size()", ".keySet()", ".length()")

_LOG_CALL = re.compile(r"\.(debug|info|warn|warning|error|trace)\s*\(")


def _clean_arg(a: str) -> str:
    """剥多余闭括号（log 调用的 `)`），保 getBody() 等平衡括号。"""
    a = a.strip().rstrip(";").strip()
    while a.endswith(")") and a.count(")") > a.count("("):
        a = a[:-1].strip()
    return a


def _split_args(s: str) -> list:
    """按括号深度=0 的逗号 split（不切方法调用内的逗号）。"""
    args, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
            cur += ch
        elif ch == ")":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            args.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def _is_sensitive_arg(arg: str) -> bool:
    a = _clean_arg(arg)
    if not a or a.endswith(_SAFE_SUFFIXES):
        return False
    if a in _SENSITIVE_VARS:
        return True
    for pat in _SENSITIVE_EXPRS:
        if re.search(pat, a):
            return True
    return False


def _extract_args(line: str) -> list:
    """从 log.X("format", arg1, arg2) 提取引号外的参数。"""
    m = _LOG_CALL.search(line)
    if not m:
        return []
    rest = line[m.end():].rstrip(";").strip()
    q = re.search(r'"[^"]*"\s*,?\s*(.*)', rest)
    if not q:
        # 无格式串（如 log.error(response.getBody())）—— 整个 rest 是参数
        return _split_args(rest) if rest else []
    argstr = q.group(1).rstrip(";").strip()
    if not argstr:
        return []
    return _split_args(argstr)


def _merge_continuation_lines(src: str) -> list:
    """合并多行 log 调用：log.X( 未在同一行闭合时，把后续行拼到闭合行。

    p1 实审要求：多行 log 调用（敏感参数在下一行）必须被扫描到。
    单行扫描会漏掉：
        log.error("msg: {}",
            response.getBody());
    合并后变为单行 `log.error("msg: {}", response.getBody());` 再走 _extract_args。
    """
    merged = []
    buf = ""
    for line in src.splitlines():
        if buf:
            buf += " " + line.strip()
            # 行尾出现 ); 或 ) 视为 log 调用闭合
            if ");" in line or line.rstrip().endswith(")"):
                merged.append(buf)
                buf = ""
            elif len(buf) > 2000:  # 防畸形超长拼接
                merged.append(buf)
                buf = ""
        elif _LOG_CALL.search(line) and not line.rstrip().endswith(");"):
            # log.X( 开了但本行没闭合到 ); —— 进入续行缓冲
            buf = line.rstrip()
        else:
            merged.append(line)
    if buf:
        merged.append(buf)
    return merged


class SensitiveJavaLogGuard(unittest.TestCase):
    """断言 9 文件无敏感值作为 log 参数直出。"""

    def _assert_no_sensitive_value_logging(self, rel: str) -> None:
        path = _REPO_ROOT / rel
        if not path.exists():
            self.skipTest(f"{rel} 不存在")
        src = path.read_text(encoding="utf-8", errors="ignore")
        # 合并多行 log 调用（p1 实审要求覆盖跨行参数）
        merged_lines = _merge_continuation_lines(src)
        for lineno, line in enumerate(merged_lines, 1):
            if not _LOG_CALL.search(line):
                continue
            for arg in _extract_args(line):
                if _is_sensitive_arg(arg):
                    raise AssertionError(
                        f"{rel}:{lineno} log 调用参数 `{arg}` 是敏感值直出：{line.strip()}\n"
                        f"应改为键名/size/存在性/异常对象，不得输出原始值容器。"
                    )

    def test_PluginBaseImpl_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[0])

    def test_PluginAdapterImpl_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[1])

    def test_IamServiceUtils_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[2])

    def test_AgentManagementService_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[3])

    def test_AgentManagerService_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[4])

    def test_IamTokenAuthItem_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[5])

    def test_JiuWenService_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[6])

    def test_ApigApiService_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[7])

    def test_WebClientUtils_no_sensitive_value(self):
        self._assert_no_sensitive_value_logging(_GUARDED_FILES[8])

    # --- 坏例注入：验证坏代码会触发拒绝（p1 实审要求） ---

    def test_fault_injection_headers_rejected(self):
        """坏例：log.error("msg: {}", headers) 必须被拒绝。"""
        self.assertTrue(_is_sensitive_arg("headers"),
            "headers 作为参数应被识别为敏感")

    def test_fault_injection_response_getBody_rejected(self):
        """坏例：response.getBody() 作为参数必须被拒绝（修正前 rstrip bug 会放过）。"""
        self.assertTrue(_is_sensitive_arg("response.getBody())"),
            "response.getBody() 应被识别为敏感（修正前 rstrip 剥闭括号导致漏判）")

    def test_fault_injection_responseEntity_getBody_rejected(self):
        """坏例：responseEntity.getBody() 必须被拒绝。"""
        self.assertTrue(_is_sensitive_arg("responseEntity.getBody())"),
            "responseEntity.getBody() 应被识别为敏感")

    def test_fault_injection_errorBody_rejected(self):
        """坏例：errorBody 作为参数必须被拒绝。"""
        self.assertTrue(_is_sensitive_arg("errorBody)"),
            "errorBody 应被识别为敏感")

    def test_fault_injection_body_as_message_rejected(self):
        """坏例：log.error(response.getBody()) 无格式串，body 直接作 message 必须被拒绝。"""
        args = _extract_args('log.error(response.getBody());')
        self.assertTrue(any(_is_sensitive_arg(a) for a in args),
            "body-as-message（无格式串）应被识别为敏感")

    def test_fault_injection_multi_arg_rejected(self):
        """坏例：response.getBody(), e 多参数必须被拒绝。"""
        args = _extract_args('log.error("msg: {}", response.getBody(), e);')
        self.assertTrue(any(_is_sensitive_arg(a) for a in args),
            "response.getBody(), e 多参数应被识别为敏感")

    def test_fault_injection_multiline_rejected(self):
        """坏例：多行 log 调用（敏感参数在下一行）必须被拒绝（p1 实审要求多行覆盖）。

        修正前只扫单行，会漏掉：
            log.error("msg: {}",
                response.getBody());
        本例走完整链路：_merge_continuation_lines → _extract_args → _is_sensitive_arg。
        """
        multiline_src = (
            'log.error("msg: {}",\n'
            '    response.getBody());\n'
        )
        merged = _merge_continuation_lines(multiline_src)
        # 合并后应为单行闭合调用
        self.assertEqual(len(merged), 1, f"多行应合并为 1 行，实际 {len(merged)}: {merged}")
        args = _extract_args(merged[0])
        self.assertTrue(any(_is_sensitive_arg(a) for a in args),
            f"多行 log 调用合并后 response.getBody() 应被识别为敏感，args={args}")

    def test_fault_injection_multiline_body_only_message_rejected(self):
        """坏例：多行无格式串（body 直接作 message 跨行）必须被拒绝。"""
        multiline_src = (
            'log.error(response\n'
            '    .getBody());\n'
        )
        merged = _merge_continuation_lines(multiline_src)
        args = _extract_args(merged[0])
        self.assertTrue(any(_is_sensitive_arg(a) for a in args),
            f"多行 body-as-message 合并后应被识别为敏感，args={args}")

    # --- 好例：验证安全写法不被误杀 ---

    def test_good_size_not_rejected(self):
        """好例：requestBody.size() 不应被拒绝。"""
        self.assertFalse(_is_sensitive_arg("requestBody.size()"),
            "size() 不应被识别为敏感")

    def test_good_keySet_not_rejected(self):
        """好例：headers.keySet() 不应被拒绝。"""
        self.assertFalse(_is_sensitive_arg("headers.keySet()"),
            "keySet() 不应被识别为敏感")

    def test_good_exception_not_rejected(self):
        """好例：e（异常对象）不应被拒绝。"""
        self.assertFalse(_is_sensitive_arg("e"),
            "异常对象 e 不应被识别为敏感")

    def test_good_status_code_not_rejected(self):
        """好例：statusCode 不应被拒绝。"""
        self.assertFalse(_is_sensitive_arg("statusCode"),
            "statusCode 不应被识别为敏感")


if __name__ == "__main__":
    unittest.main()
