/*
 * 聚焦回归测试：LLM 视觉字段类型切换同步（标量与数组、图片与视频）
 *
 * 说明：
 * - 该项目无可用 Angular/Karma 组件测试链路，本脚本沿用“读取真实源码 + 纯逻辑断言”方式。
 * - 直接读取 flow.component.ts 的 fixRefTypeOutdate() 与 changeLLMVisionName() 真实实现，
 *   做两类断言：
 *     A. 源码契约断言（修复前失败、修复后通过）：
 *        - changeLLMVisionName 用 `newRef.schema?.type ?? newRef.type` 识别媒体类型（标量兜底）
 *        - findIndex() === -1 时安全 no-op（不写 configs.vision[-1]）
 *        - 不再使用 `?? 0`（对 -1 无效）
 *        - fixRefTypeOutdate 对标量与数组都调用 changeLLMVisionName（不只 array/object）
 *     B. 行为复现：复刻 changeLLMVisionName 的命名/同步逻辑，覆盖四种切换与边界。
 * - 运行：node tests/vision-type-switch.test.cjs
 *
 * 对应设计/实现文档 §4.2、§5（flow.component.ts 改动点）。
 */
'use strict';

const fs = require('fs');
const path = require('path');

const SRC_PATH = path.join(
  __dirname,
  '..',
  'src',
  'routes',
  'agent-center',
  'app-flow',
  'flow',
  'flow.component.ts',
);

const SRC = fs.readFileSync(SRC_PATH, 'utf8');

const failures = [];

// ---- 源码提取 ------------------------------------------------------------
// 提取 changeLLMVisionName 定义体（用 `private changeLLMVisionName(` 锚定定义，避免命中调用点）
function extractChangeLLMVisionNameSrc() {
  const m = SRC.match(/private\s+changeLLMVisionName\s*\([\s\S]*?\n  \}/);
  return m ? m[0] : '';
}

// 提取 fixRefTypeOutdate 定义体
function extractFixRefTypeOutdateSrc() {
  const m = SRC.match(/private\s+fixRefTypeOutdate\s*\([\s\S]*?\n  \}/);
  return m ? m[0] : '';
}

const changeSrc = extractChangeLLMVisionNameSrc();
const fixRefSrc = extractFixRefTypeOutdateSrc();

if (!changeSrc) failures.push('未能在源码中找到 changeLLMVisionName 定义');
if (!fixRefSrc) failures.push('未能在源码中找到 fixRefTypeOutdate 定义');

// ---- A. 源码契约断言 ----------------------------------------------------
if (changeSrc) {
  // 标量兜底：数组 schema 子类型优先，否则标量 newRef.type
  if (!/newRef\.schema\?\.type\s*\?\?\s*newRef\.type/.test(changeSrc)) {
    failures.push(
      'changeLLMVisionName 缺少标量兜底 newRef.schema?.type ?? newRef.type -> 标量图片↔视频漏同步',
    );
  }
  // findIndex === -1 安全 no-op
  if (!/findIndex/.test(changeSrc)) {
    failures.push('changeLLMVisionName 缺少 findIndex 定位 configs.vision');
  }
  if (!/===\s*-1/.test(changeSrc)) {
    failures.push('changeLLMVisionName 缺少 findIndex === -1 安全 no-op -> 可能写 configs.vision[-1]');
  }
  // 不再使用 ?? 0（对 findIndex 返回的 -1 无效：-1 ?? 0 === -1）
  if (/\?\?\s*0/.test(changeSrc)) {
    failures.push('changeLLMVisionName 仍含 ?? 0（对 findIndex -1 无效，会写 configs.vision[-1]）');
  }
}

if (fixRefSrc) {
  // fixRefTypeOutdate 必须调用 changeLLMVisionName
  if (!/this\.changeLLMVisionName\(\s*field\s*,\s*index\s*,\s*node\s*\)/.test(fixRefSrc)) {
    failures.push('fixRefTypeOutdate 未调用 this.changeLLMVisionName(field, index, node)');
  }
  // changeLLMVisionName 不得仅在 array/object 分支内调用（否则标量引用漏同步）
  const arrayBranch = fixRefSrc.match(
    /if\s*\(\s*\[\s*'array'\s*,\s*'object'\s*\]\.includes\(field\.type\)\s*\)\s*\{([\s\S]*?)\}\s*else/,
  );
  const arrayBranchBody = arrayBranch ? arrayBranch[1] : '';
  if (arrayBranchBody && /changeLLMVisionName/.test(arrayBranchBody)) {
    failures.push('changeLLMVisionName 仍在 array/object 分支内 -> 标量引用类型切换漏同步');
  }
  if (!arrayBranchBody) {
    failures.push('未能定位 fixRefTypeOutdate 的 array/object 分支以校验标量同步');
  }
}

// ---- B. 行为复现 ---------------------------------------------------------
// 复刻修复后的 changeLLMVisionName 逻辑（与源码保持一致）。
function changeLLMVisionName(field, newRef, node) {
  if (node?.type !== 'LLM') return { changed: false };
  if (!node?.configs?.vision) return { changed: false };
  const refType = newRef.schema?.type ?? newRef.type;
  const isVideo = refType === 'file/video';
  const isImage = refType === 'file/image' || refType === 'string';
  if (!isVideo && !isImage) return { changed: false };

  const currentIsImage = field.name.startsWith('_image_vision_');
  const currentIsVideo = field.name.startsWith('_video_vision_');
  if (!currentIsImage && !currentIsVideo) return { changed: false };
  if ((isVideo && currentIsVideo) || (isImage && currentIsImage)) return { changed: false };

  const originIndex = node.configs.vision.findIndex((v) => v === field.name);
  if (originIndex === -1) return { changed: false };

  const before = field.name;
  field.name = isVideo
    ? field.name.replace('_image_', '_video_')
    : field.name.replace('_video_', '_image_');
  node.configs.vision[originIndex] = field.name;
  return { changed: true, before, after: field.name, originIndex };
}

function deepEq(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// 标量引用：无 schema
const scalarImgRef = { type: 'file/image' };
const scalarVidRef = { type: 'file/video' };
// 数组引用：schema.type 标识元素媒体
const arrayImgRef = { type: 'array', schema: { type: 'file/image' } };
const arrayVidRef = { type: 'array', schema: { type: 'file/video' } };
const arrayStrRef = { type: 'array', schema: { type: 'string' } };

function mkLLM(visionArr) {
  return { type: 'LLM', configs: { vision: visionArr ? visionArr.slice() : [] } };
}

// 媒体类型变化的切换：命名前缀与 configs.vision 同步
const switchCases = [
  // label, fieldName, newRef, visionBefore, expectedName, expectedVision
  ['scalar image -> scalar video', '_image_vision_1', scalarVidRef, ['_image_vision_1'], '_video_vision_1', ['_video_vision_1']],
  ['scalar video -> scalar image', '_video_vision_2', scalarImgRef, ['_video_vision_2'], '_image_vision_2', ['_image_vision_2']],
  ['array image -> array video', '_image_vision_3', arrayVidRef, ['_image_vision_3'], '_video_vision_3', ['_video_vision_3']],
  ['array video -> array image', '_video_vision_4', arrayImgRef, ['_video_vision_4'], '_image_vision_4', ['_image_vision_4']],
  ['scalar image -> array video', '_image_vision_5', arrayVidRef, ['_image_vision_5'], '_video_vision_5', ['_video_vision_5']],
  ['array video -> scalar image', '_video_vision_6', scalarImgRef, ['_video_vision_6'], '_image_vision_6', ['_image_vision_6']],
  ['array video -> array<string>(image)', '_video_vision_7', arrayStrRef, ['_video_vision_7'], '_image_vision_7', ['_image_vision_7']],
];

for (const [label, fieldName, newRef, visionBefore, expectedName, expectedVision] of switchCases) {
  const field = { name: fieldName };
  const node = mkLLM(visionBefore);
  const res = changeLLMVisionName(field, newRef, node);
  if (!res.changed) {
    failures.push(label + ': 期望发生重命名，但 changed=false');
    continue;
  }
  if (field.name !== expectedName) {
    failures.push(label + ': 字段名 期望 ' + expectedName + '，实际 ' + field.name);
  }
  if (!deepEq(node.configs.vision, expectedVision)) {
    failures.push(label + ': configs.vision 期望 ' + JSON.stringify(expectedVision) + '，实际 ' + JSON.stringify(node.configs.vision));
  }
  // vision 数组长度不变（替换而非追加）
  if (node.configs.vision.length !== expectedVision.length) {
    failures.push(label + ': configs.vision 长度变化（应原地替换）');
  }
  // 不得产生 vision[-1] 残留
  if (node.configs.vision[-1] !== undefined) {
    failures.push(label + ': configs.vision[-1] 被写入（应安全 no-op 未触发）');
  }
}

// 媒体类型未变化：不重命名、不改动 configs.vision
const noChangeCases = [
  ['image -> image (no change)', '_image_vision_10', scalarImgRef, ['_image_vision_10']],
  ['video -> video (no change)', '_video_vision_11', scalarVidRef, ['_video_vision_11']],
  ['array image -> array image', '_image_vision_12', arrayImgRef, ['_image_vision_12']],
  ['array video -> array video', '_video_vision_13', arrayVidRef, ['_video_vision_13']],
  ['array<string> -> array<string>', '_image_vision_14', arrayStrRef, ['_image_vision_14']],
];
for (const [label, fieldName, newRef, visionBefore] of noChangeCases) {
  const field = { name: fieldName };
  const node = mkLLM(visionBefore);
  const res = changeLLMVisionName(field, newRef, node);
  if (res.changed) {
    failures.push(label + ': 媒体类型未变化不应重命名，但 changed=true');
  }
  if (field.name !== fieldName) {
    failures.push(label + ': 字段名不应变化，实际 ' + field.name);
  }
  if (!deepEq(node.configs.vision, visionBefore)) {
    failures.push(label + ': configs.vision 不应变化');
  }
}

// findIndex === -1 安全 no-op：旧字段名不在 configs.vision 中
const missingCases = [
  ['empty vision', '_image_vision_20', scalarVidRef, []],
  ['vision has other name', '_image_vision_21', scalarVidRef, ['_other_name']],
];
for (const [label, fieldName, newRef, visionBefore] of missingCases) {
  const field = { name: fieldName };
  const node = mkLLM(visionBefore);
  const res = changeLLMVisionName(field, newRef, node);
  if (res.changed) {
    failures.push(label + ': findIndex=-1 应安全 no-op，但 changed=true');
  }
  if (field.name !== fieldName) {
    failures.push(label + ': 字段名不应变化');
  }
  if (!deepEq(node.configs.vision, visionBefore)) {
    failures.push(label + ': configs.vision 不应变化，实际 ' + JSON.stringify(node.configs.vision));
  }
  // 关键：不得写入 configs.vision[-1]
  if (node.configs.vision[-1] !== undefined) {
    failures.push(label + ': configs.vision[-1] 被写入（findIndex=-1 未安全处理）');
  }
  if (Object.keys(node.configs.vision).includes('-1')) {
    failures.push(label + ': configs.vision 出现 -1 键（findIndex=-1 未安全处理）');
  }
}

// 非 LLM 节点 / 无 vision 配置 / 非视觉字段名 / 非媒体类型：均 no-op
const noopCases = [
  ['non-LLM node', { name: '_image_vision_30' }, scalarVidRef, { type: 'Code', configs: { vision: ['_image_vision_30'] } }],
  ['LLM without vision config', { name: '_image_vision_31' }, scalarVidRef, { type: 'LLM', configs: {} }],
  ['non-vision field name', { name: 'query' }, scalarVidRef, mkLLM(['query'])],
  ['non-media ref type (file/doc)', { name: '_image_vision_32' }, { type: 'file/doc' }, mkLLM(['_image_vision_32'])],
];
for (const [label, field, newRef, node] of noopCases) {
  const nameBefore = field.name;
  const visionBefore = node?.configs?.vision ? node.configs.vision.slice() : undefined;
  const res = changeLLMVisionName(field, newRef, node);
  if (res.changed) {
    failures.push(label + ': 应 no-op，但 changed=true');
  }
  if (field.name !== nameBefore) {
    failures.push(label + ': 字段名不应变化');
  }
  if (visionBefore && !deepEq(node.configs.vision, visionBefore)) {
    failures.push(label + ': configs.vision 不应变化');
  }
}

if (failures.length) {
  console.error('FAIL（' + failures.length + ' 项）：');
  failures.forEach(f => console.error('  - ' + f));
  process.exit(1);
}

console.log(
  'PASS：changeLLMVisionName 标量兜底 + findIndex=-1 安全 no-op；fixRefTypeOutdate 标量也同步；四种切换/未变化/缺失/边界 no-op 全部一致',
);
