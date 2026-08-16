/*
 * 回归测试：CDK 虚拟滚动 viewport 必须禁用浏览器 scroll anchoring
 *
 * 背景（2026-08 修复）：
 * - nz-select（ng-zorro）下拉使用 CDK virtual-scroll-viewport 渲染选项列表；
 *   run-modal / flow-log-modal 等处也直接使用 cdk-virtual-scroll-viewport。
 * - CDK 在渲染窗口（render range）前移时会移除顶部 DOM 并用 content-wrapper
 *   的 transform 重定位补偿视觉位置。若 viewport 未禁用 scroll anchoring，
 *   Chrome 会对“可视区上方内容移除”再做一次 scrollTop 补偿 → 双重补偿 →
 *   慢速滚动越过首屏（minBufferPx 边界）后每滚一格都被拉回。
 *   实测现象：工作流大模型节点“模型配置”模型下拉卡在第 2 页开头
 *   （滚轮 +100 → 修正 -32/-96 → 每格净 +4）。
 * - 根因：angular.json 只引入了 cdk 的 overlay/text-field prebuilt 样式，
 *   CDK 组件自带样式中没有 overflow-anchor 规则，ng-zorro 仅在旧版
 *   .ant-select-dropdown-content-wrapper（非虚拟滚动路径）上有。
 * - 修复：src/styles/global.css 追加
 *   .cdk-virtual-scroll-viewport { overflow-anchor: none; }
 *
 * 本测试沿用 tests/vision-file-image.test.cjs 的“读取真实资源 + 纯逻辑断言”方式，
 * 防止该规则被误删。动态复现/验证脚本思路见本文件头部注释（需运行中的前端环境，
 * 未纳入自动化）。运行：node tests/virtual-scroll-anchor.test.cjs
 */
'use strict';

const fs = require('fs');
const path = require('path');

const GLOBAL_CSS = path.join(__dirname, '..', 'src', 'styles', 'global.css');
const ANGULAR_JSON = path.join(__dirname, '..', 'angular.json');

let failures = 0;
function assert(cond, msg) {
  if (cond) {
    console.log('  PASS: ' + msg);
  } else {
    failures++;
    console.error('  FAIL: ' + msg);
  }
}

console.log('[1] global.css 含 overflow-anchor 守卫规则');
const css = fs.readFileSync(GLOBAL_CSS, 'utf8');
assert(
  /\.cdk-virtual-scroll-viewport\s*\{[^}]*overflow-anchor\s*:\s*none/i.test(css),
  'global.css 中存在 .cdk-virtual-scroll-viewport { overflow-anchor: none; }'
);

console.log('[2] 项目源码中没有把 overflow-anchor 改回的覆盖');
// 递归收集 src 下样式/组件样式中的 overflow-anchor 声明（排除 global.css 中的守卫本身）
function walk(dir, acc) {
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) walk(p, acc);
    else if (/\.(css|scss|less)$/.test(name)) acc.push(p);
  }
  return acc;
}
const styleFiles = walk(path.join(__dirname, '..', 'src'), []);
const offenders = [];
for (const f of styleFiles) {
  const text = fs.readFileSync(f, 'utf8');
  const re = /overflow-anchor\s*:\s*([a-z]+)/gi;
  let m;
  while ((m = re.exec(text)) !== null) {
    if (m[1].toLowerCase() !== 'none') offenders.push(`${path.relative(path.join(__dirname, '..'), f)}: ${m[0]}`);
  }
}
assert(offenders.length === 0, '所有 overflow-anchor 声明均为 none' + (offenders.length ? '，违规：' + offenders.join('; ') : ''));

console.log('[3] angular.json 样式清单未被破坏（守卫仍在生效的样式链上）');
const angularJson = JSON.parse(fs.readFileSync(ANGULAR_JSON, 'utf8'));
const build = angularJson.projects && Object.values(angularJson.projects)[0];
const styles = (((build || {}).architect || {}).build || {}).options
  ? build.architect.build.options.styles
  : angularJson.projects['agent-console'].architect.build.options.styles;
assert(
  Array.isArray(styles) && styles.some((s) => String(s).endsWith('global.css')),
  'angular.json build.styles 包含 src/styles/global.css'
);

if (failures > 0) {
  console.error(`\n${failures} 项断言失败`);
  process.exit(1);
}
console.log('\n全部通过');
