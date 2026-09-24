#!/usr/bin/env bash
# Studio 2.0 错误码治理工具本地验收脚本。
#
# 用法：
#   tools/observability/scripts/run_local_governance_validation.sh
#   tools/observability/scripts/run_local_governance_validation.sh /tmp/report-dir
#
# 可通过 EXPECTED_ISSUE_COUNT 覆盖当前已评审存量数量；修改该值前必须先完成人工评审。

set -euo pipefail

OBSERVABILITY_SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
STUDIO_REPO_ROOT=$(CDPATH= cd -- "$OBSERVABILITY_SCRIPT_DIR/../../.." && pwd)
EXPECTED_ISSUE_COUNT=${EXPECTED_ISSUE_COUNT:-1782}

if [[ $# -gt 1 ]]; then
  echo "用法：$0 [报告目录]" >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  GOVERNANCE_REPORT_DIR=$1
  mkdir -p -- "$GOVERNANCE_REPORT_DIR"
else
  GOVERNANCE_REPORT_DIR=$(mktemp -d /tmp/studio-ext01-local.XXXXXX)
fi

cd -- "$STUDIO_REPO_ROOT"

run_validation_step() {
  local step_name=$1
  shift
  printf '\n==> %s\n' "$step_name"
  "$@"
}

# 测试项 1：运行治理目录单元测试（Java 敏感日志守卫 21 + 治理脚本 10 = 31）。
# 功能：Java 守卫锁 9 文件敏感值直出防回归；治理脚本验证 SHA/路径/防绕过/基线元数据规则。
# 通过条件：unittest discover 输出 OK（31 项）。
run_validation_step \
  "1/9 治理脚本单元测试" \
  python3 -m unittest discover -s tools/observability/tests -p 'test_*.py'

# 测试项 2：运行 Runtime 出站 Header 容器守卫（AST 反转设计，19 项）。
# 功能：agent-runtime 5 个受保护文件不得把完整 Header 容器（custom_headers/
# request_params.headers 等）以任何静态表达式形式传入日志；坏例注入覆盖
# f-string/参数化/无格式串/%/.format/嵌套字面量/.log/BoolOp/IfExp/下标/
# 星号/推导式。7d3750bb 复核 §2.6 接入，消除 P7/CI 漏跑风险。
# 通过条件：unittest discover 输出 OK（19 项）。
run_validation_step \
  "2/9 Runtime Header 守卫" \
  python3 -m unittest discover -s agent-runtime/tests/unit_tests/common -p 'test_outbound_header_log_guard.py'

# 测试项 3：检查双语错误码目录是否由当前Manifest正确生成。
# 功能：发现手工编辑生成文档、Manifest更新后未重新生成目录等漂移。
# 通过条件：输出 error-code reference documents are up to date。
run_validation_step \
  "3/9 双语错误码目录一致性" \
  python3 tools/observability/scripts/generate_error_code_docs.py --check

# 测试项 4：校验Manifest、协议和生成目录的静态契约。
# 功能：检查协议版本与哈希、号段、Owner、错误码格式、HTTP状态、生命周期、definition/reference和评审记录。
# 通过条件：输出 error-code Manifest and generated documents are valid。
run_validation_step \
  "4/9 Manifest与协议静态契约" \
  python3 tools/observability/scripts/check_error_codes.py

# 测试项 5：扫描当前三服务错误码存量并与已评审基线比较。
# 功能：发现新增未登记定义、重复位置、Owner不一致、未知字面引用、跨服务引用和i18n缺失。
# 通过条件：命令退出码为0，并生成JSON与Markdown报告。
run_validation_step \
  "5/9 存量增量扫描" \
  python3 tools/observability/scripts/check_error_code_inventory.py \
    --json-report "$GOVERNANCE_REPORT_DIR/inventory-report.json" \
    --markdown-report "$GOVERNANCE_REPORT_DIR/inventory-report.md"

# 测试项 6：断言当前扫描结果与冻结快照完全一致。
# 功能：避免只依赖退出码而漏看“已消失问题”；当前阶段要求1782/1782、新增0、消失0。
# 通过条件：数量等于EXPECTED_ISSUE_COUNT，新增和消失数组均为空。
printf '\n==> 6/9 存量报告精确断言\n'
python3 - "$GOVERNANCE_REPORT_DIR/inventory-report.json" "$EXPECTED_ISSUE_COUNT" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
expected_count = int(sys.argv[2])
report = json.loads(report_path.read_text(encoding="utf-8"))

actual = report.get("current_issue_count")
known = report.get("known_issue_count")
new = report.get("new_issues")
resolved = report.get("resolved_baseline_issues")

errors = []
if actual != expected_count:
    errors.append(f"current_issue_count={actual}, expected={expected_count}")
if known != expected_count:
    errors.append(f"known_issue_count={known}, expected={expected_count}")
if new != []:
    errors.append(f"new_issues is not empty: {len(new or [])}")
if resolved != []:
    errors.append(f"resolved_baseline_issues is not empty: {len(resolved or [])}")

if errors:
    raise SystemExit("存量报告不符合冻结快照：\n- " + "\n- ".join(errors))

print(f"存量报告符合预期：current={actual}, known={known}, new=0, resolved=0")
PY

# 测试项 7：以strict模式运行与CI相同的组合入口。
# 功能：组合执行Manifest校验和存量扫描，验证报告生成以及未来阻断模式使用的非零退出能力。
# 通过条件：总体无warning且命令退出码为0；该本地strict运行不改变远程CI模式。
run_validation_step \
  "7/9 strict组合入口" \
  python3 tools/observability/scripts/run_error_code_advisory.py \
    --strict \
    --report-dir "$GOVERNANCE_REPORT_DIR/advisory"

# 测试项 8：校验组合入口写出的机器可读状态。
# 功能：防止提示文本看似正常但底层Manifest或Inventory检查实际返回非零。
# 通过条件：mode=strict、两个退出码均为0、has_warning=false。
printf '\n==> 8/9 组合入口状态断言\n'
python3 - "$GOVERNANCE_REPORT_DIR/advisory/check-status.json" <<'PY'
import json
import sys
from pathlib import Path

status_path = Path(sys.argv[1])
status = json.loads(status_path.read_text(encoding="utf-8"))
expected = {
    "mode": "strict",
    "manifest_check_exit_code": 0,
    "inventory_check_exit_code": 0,
    "has_warning": False,
}
errors = [
    f"{key}={status.get(key)!r}, expected={value!r}"
    for key, value in expected.items()
    if status.get(key) != value
]
if errors:
    raise SystemExit("组合入口状态不符合预期：\n- " + "\n- ".join(errors))

print("组合入口状态符合预期：strict、两个底层检查均为0、无warning")
PY

# 测试项 9：检查未暂存和已暂存Git差异的空白符错误。
# 功能：发现行尾空格、错误缩进等会导致提交检查失败的问题。
# 通过条件：两个git diff --check命令均无输出并返回0。
printf '\n==> 9/9 Git差异格式检查\n'
git diff --check
git diff --cached --check

printf '\n全部本地治理验收项通过。\n'
printf '报告目录：%s\n' "$GOVERNANCE_REPORT_DIR"
