/*
 * 聚焦回归测试：视觉理解输入 tooltip 文案反映单个 File/Image 与单个 File/Video 支持
 *
 * 说明：
 * - 该项目测试体系（karma 配置为空、未安装 jest）无法直接实例化 Angular 组件，
 *   本脚本沿用 tests/vision-file-image.test.cjs 的“读取真实资源 + 纯逻辑断言”最小可运行方式。
 * - 直接读取 zh-CN / en-US 的 agent-center.json，对 visual_comprehension_input_tip 断言：
 *     1) 文案包含“独立的” File/Image（修复点：旧文案仅 Array<File/Image>）
 *     2) 文案包含“独立的” File/Video（本次扩展点）
 *     3) 保留 Array<File/Image>、Array<File/Video>、Array<String> 说明（数组回归）
 *     4) 保留 Array<String> 仅支持图片地址 的说明（回归）
 *     5) 不得把 Array<File/Video> 误判为独立 File/Video
 * - 判定“独立 TypeName”：先剔除所有 `Array<TypeName>` 子串，若仍残留 `TypeName`
 *   即说明存在独立（非数组包裹的）TypeName。
 * - 运行：node tests/vision-tooltip.test.cjs
 */
'use strict';

const fs = require('fs');
const path = require('path');

const FILES = {
  zh: path.join(__dirname, '..', 'src', 'assets', 'i18n', 'zh-CN', 'agent-center.json'),
  en: path.join(__dirname, '..', 'src', 'assets', 'i18n', 'en-US', 'agent-center.json'),
};

function readTip(localeKey) {
  const json = JSON.parse(fs.readFileSync(FILES[localeKey], 'utf8'));
  return typeof json.visual_comprehension_input_tip === 'string'
    ? json.visual_comprehension_input_tip
    : '';
}

// 先剔除所有 `Array<TypeName>`，再看是否仍残留独立的 `TypeName`。
function hasStandalone(tip, typeName) {
  const escaped = typeName.replace('/', '\\/');
  const withoutArray = tip.replace(new RegExp('Array<' + escaped + '>', 'g'), '');
  return new RegExp(escaped).test(withoutArray);
}

const failures = [];

for (const [localeKey, localeLabel] of [['zh', 'zh-CN'], ['en', 'en-US']]) {
  const tip = readTip(localeKey);
  if (!tip) {
    failures.push(`${localeLabel}: 未找到 visual_comprehension_input_tip`);
    continue;
  }

  // 断言 1：文案包含独立的 File/Image（修复点）
  if (!hasStandalone(tip, 'File/Image')) {
    failures.push(
      `${localeLabel}: 文案缺少独立的 File/Image（仍仅 Array<File/Image>） -> ${tip}`,
    );
  }

  // 断言 2：文案包含独立的 File/Video（本次扩展点）
  if (!hasStandalone(tip, 'File/Video')) {
    failures.push(
      `${localeLabel}: 文案缺少独立的 File/Video -> ${tip}`,
    );
  }

  // 断言 3：三种数组类型说明仍在（回归）
  for (const t of ['Array<File/Image>', 'Array<File/Video>', 'Array<String>']) {
    if (!tip.includes(t)) {
      failures.push(`${localeLabel}: 文案缺失 ${t}（数组回归）`);
    }
  }

  // 断言 4：Array<String> 仅支持图片地址 说明仍在（回归）
  const imageAddrHint = localeKey === 'zh' ? '图片地址' : 'image URLs';
  if (!tip.includes(imageAddrHint)) {
    failures.push(`${localeLabel}: 文案缺失 Array<String> 仅支持${imageAddrHint} 说明`);
  }
}

if (failures.length) {
  console.error('FAIL（' + failures.length + ' 项）：');
  failures.forEach(f => console.error('  - ' + f));
  process.exit(1);
}

console.log(
  'PASS：tooltip 含独立 File/Image 与 File/Video；Array<File/Image>/Array<File/Video>/Array<String> 说明保留；Array<String> 仅图片地址说明保留',
);
