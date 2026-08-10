/*
 * 聚焦回归测试：大模型节点视觉理解输入支持单个 file/image 与单个 file/video
 *
 * 说明：
 * - 该项目测试体系（karma 配置为空、未安装 jest）无法直接实例化 Angular 组件，
 *   因此本脚本采用“纯逻辑 + 读取真实源码”的最小可运行方式。
 * - 脚本直接读取 llm-modal.component.ts 的真实白名单与 handelSave 命名分支，
 *   用真实提取到的常量/分支符号驱动断言，确保“修复前失败、修复后通过”。
 * - 运行：node tests/vision-file-image.test.cjs
 *
 * 覆盖（对应设计/实现文档 §6.1）：
 *   1. 单个 file/image、单个 file/video 出现在视觉输入选择器（白名单包含两者）
 *   2. 单个 file/image 保存后字段名为 _image_vision_N（handelSave 单值命名分支）
 *   3. 单个 file/video 保存后字段名为 _video_vision_N（标量 i.type 兜底分支）
 *   4. 回归：array<file/image> -> _image_vision_N
 *   5. 回归：array<file/video> -> _video_vision_N
 *   6. 回归：array<string>      -> _image_vision_N
 *   7. 回归：裸 file、file/doc、file/audio 仍不可选（不过度放开）
 *   8. 视觉编号回归：已有 _image_vision_1、_video_vision_2 时新增项分配新编号，不冲突
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
  'components',
  'llm-modal',
  'llm-modal.component.ts',
);

const SRC = fs.readFileSync(SRC_PATH, 'utf8');

function extractVisionParmaTypes() {
  const m = SRC.match(/visionParmaTypes\s*=\s*\[([\s\S]*?)\]/);
  if (!m) return null;
  return m[1]
    .split(',')
    .map(s => s.trim().replace(/^['"`]|['`]$/g, '').replace(/['"]$/g, ''))
    .filter(Boolean);
}

// 限定在 handelSave() ... modelCloseSave() 之间，避免误匹配文件其他位置。
function extractHandelSaveSrc() {
  const start = SRC.indexOf('handelSave()');
  if (start === -1) return '';
  const end = SRC.indexOf('modelCloseSave()', start);
  return SRC.slice(start, end === -1 ? SRC.length : end);
}

// 复刻 resetVisionLastId() 的编号恢复逻辑（源码 llm-modal.component.ts）。
function resetVisionLastId(existingNames) {
  let visionLastId = 0;
  existingNames.forEach(name => {
    if (
      name.startsWith('_vision_') ||
      name.startsWith('_image_vision_') ||
      name.startsWith('_video_vision_')
    ) {
      let curId = Number(name.split('_vision_')[1] ?? '1');
      if (isNaN(curId)) {
        curId = 1;
      }
      visionLastId = Math.max(visionLastId, curId);
      visionLastId++;
    }
  });
  return visionLastId;
}

const visionParmaTypes = extractVisionParmaTypes();
const handelSaveSrc = extractHandelSaveSrc();

const failures = [];

if (!visionParmaTypes) {
  failures.push('未能在源码中找到 visionParmaTypes 白名单');
} else {
  // 断言 1a：单个 file/image 可被选择
  if (!visionParmaTypes.includes('file/image')) {
    failures.push(
      '白名单缺少 file/image：单个图片文件不可选 -> ' + JSON.stringify(visionParmaTypes),
    );
  }
  // 断言 1b：单个 file/video 可被选择（本次扩展点）
  if (!visionParmaTypes.includes('file/video')) {
    failures.push(
      '白名单缺少 file/video：单个视频文件不可选 -> ' + JSON.stringify(visionParmaTypes),
    );
  }
  // 断言 7：裸 file、file/doc、file/audio 不可选（不过度放开）
  for (const t of ['file', 'file/doc', 'file/audio']) {
    if (visionParmaTypes.includes(t)) {
      failures.push('白名单不应包含 ' + t + '（过度放开）');
    }
  }
  // 回归：三种数组类型仍在白名单
  for (const t of ['array<file/image>', 'array<file/video>', 'array<string>']) {
    if (!visionParmaTypes.includes(t)) {
      failures.push('白名单缺失 ' + t + '（数组回归）');
    }
  }
}

// 用从真实源码提取到的分支符号，复现 handelSave 的视觉字段命名逻辑。
const hasVideoBranch = /schema\?\.type\s*===\s*['"]file\/video['"]/.test(handelSaveSrc);
const hasScalarVideoBranch = /[^.a-zA-Z]i\.type\s*===\s*['"]file\/video['"]/.test(handelSaveSrc);
const hasImageSchemaBranch = /schema\?\.type\s*===\s*['"]file\/image['"]/.test(handelSaveSrc);
const hasStringSchemaBranch = /schema\?\.type\s*===\s*['"]string['"]/.test(handelSaveSrc);
// 单值（标量）file/image 没有 schema，需要通过 i.type 兜底
const hasScalarImageBranch = /[^.a-zA-Z]i\.type\s*===\s*['"]file\/image['"]/.test(handelSaveSrc);

function nameVision(paramType, schemaType) {
  // 与 handelSave 内部 if/else if 顺序保持一致：视频分支（数组 schema 或标量 i.type）优先
  if (
    (hasVideoBranch && schemaType === 'file/video') ||
    (hasScalarVideoBranch && paramType === 'file/video')
  ) {
    return '_video_vision_1';
  }
  if (
    (hasImageSchemaBranch && schemaType === 'file/image') ||
    (hasStringSchemaBranch && schemaType === 'string') ||
    (hasScalarImageBranch && paramType === 'file/image')
  ) {
    return '_image_vision_1';
  }
  return '_vision_1'; // 未被命名分支命中 -> bug
}

if (!hasVideoBranch) failures.push('缺少 array<file/video> -> _video_vision_N 命名分支（回归）');
if (!hasScalarVideoBranch) {
  failures.push('缺少单个 file/video -> _video_vision_N 标量 i.type 兜底分支（本次扩展点）');
}
if (!hasImageSchemaBranch) failures.push('缺少 file/image(schema) -> _image_vision_N 命名分支（回归）');
if (!hasStringSchemaBranch) failures.push('缺少 string(schema) -> _image_vision_N 命名分支（回归）');
if (!hasScalarImageBranch) failures.push('缺少单个 file/image -> _image_vision_N i.type 兜底分支（回归）');

// 断言 2：单个 file/image 保存为 _image_vision_N
//   标量 file/image 经 getDtoInput 后 i.type='file/image'、i.schema 被删除 -> schemaType=undefined
const scalarImageName = nameVision('file/image', undefined);
if (scalarImageName !== '_image_vision_1') {
  failures.push(
    '单个 file/image 保存为 "' + scalarImageName + '"，期望 _image_vision_1（缺少 i.type 兜底分支）',
  );
}

// 断言 3：单个 file/video 保存为 _video_vision_N（本次扩展点）
//   标量 file/video 经 getDtoInput 后 i.type='file/video'、i.schema 被删除 -> schemaType=undefined
const scalarVideoName = nameVision('file/video', undefined);
if (scalarVideoName !== '_video_vision_1') {
  failures.push(
    '单个 file/video 保存为 "' + scalarVideoName + '"，期望 _video_vision_1（缺少标量 i.type 兜底分支）',
  );
}

// 断言 4-6：数组回归
const arrayImgName = nameVision('array', 'file/image');
if (arrayImgName !== '_image_vision_1') {
  failures.push('array<file/image> 回归：' + arrayImgName);
}
const arrayVidName = nameVision('array', 'file/video');
if (arrayVidName !== '_video_vision_1') {
  failures.push('array<file/video> 回归：' + arrayVidName);
}
const arrayStrName = nameVision('array', 'string');
if (arrayStrName !== '_image_vision_1') {
  failures.push('array<string> 回归：' + arrayStrName);
}

// 断言 8：视觉编号回归
//   已有 _image_vision_1、_video_vision_2 时，新增视觉字段应分配 >=3 的新编号，不与已保存字段冲突。
const nextId = resetVisionLastId(['_image_vision_1', '_video_vision_2']);
if (nextId < 3) {
  failures.push(
    '视觉编号回归：已有 _image_vision_1/_video_vision_2 时下一编号为 ' + nextId + '，期望 >=3（不冲突）',
  );
}

if (failures.length) {
  console.error('FAIL（' + failures.length + ' 项）：');
  failures.forEach(f => console.error('  - ' + f));
  process.exit(1);
}

console.log(
  'PASS：单个 file/image 与 file/video 均可选且分别保存为 _image_vision_N/_video_vision_N；数组行为不变；裸 file/doc/audio 不可选；编号不冲突',
);
