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

// ---- C. 保存订阅入口契约（根因回归） ------------------------------------
// 根因：start-modal.handelSave 只发布 { nodeData }，无旧节点快照；flow.component.ts
// 保存订阅把不存在的 ref.nodeInfo 默认成 {} 传给 checkRefChangeAndUpdateNode，
// 致 oldRefs=[] -> updatedRefs=[] -> updateRefType/fixRefTypeOutdate/changeLLMVisionName
// 全部不执行，开始节点图片/视频切换后 LLM 的 _image_vision_N / _video_vision_N 与
// configs.vision 不同步。
// 修复契约：保存订阅在调用 checkRefChangeAndUpdateNode 前，按 nodeData.id 从当前
// graph 读取旧节点并深拷贝作为 oldNodeData；旧节点不存在时安全跳过差异检查。
function matchBrace(src, openIdx) {
  let depth = 0;
  for (let i = openIdx; i < src.length; i++) {
    const c = src[i];
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) return i; }
  }
  return -1;
}

function extractSaveSubscriptionBody() {
  const start = SRC.indexOf('nodeSaveMonitor$()');
  if (start === -1) return '';
  const sub = SRC.indexOf('.subscribe(', start);
  if (sub === -1) return '';
  const arrow = SRC.indexOf('=>', sub);
  if (arrow === -1) return '';
  const openBrace = SRC.indexOf('{', arrow);
  if (openBrace === -1) return '';
  const closeBrace = matchBrace(SRC, openBrace);
  if (closeBrace === -1) return '';
  return SRC.slice(openBrace, closeBrace + 1);
}

const saveSubBody = extractSaveSubscriptionBody();
if (!saveSubBody) {
  failures.push('未能在源码中提取 nodeSaveMonitor$ 订阅体（保存订阅入口契约无法校验）');
}

if (saveSubBody) {
  // C1. 必须按 nodeData.id 从当前 graph 读取旧节点（getNodeInfoById 或 getCellById 链）
  if (!/getNodeInfoById\(\s*nodeData\.id\s*\)/.test(saveSubBody)
      && !/getCellById\(\s*nodeData\.id\s*\)/.test(saveSubBody)) {
    failures.push(
      '保存订阅未按 nodeData.id 从 graph 读取旧节点 -> oldNodeData 恒为 {} -> updateRefType 不执行',
    );
  }
  // C2. 必须深拷贝旧节点，避免 graph 内引用被后续 updateNodeData 副作用篡改
  if (!/cloneDeep\(/.test(saveSubBody)) {
    failures.push('保存订阅未对旧节点深拷贝 -> oldNodeData 可能与 graph 共享引用被篡改');
  }
  // C3. 不得再把事件载荷里恒为 {} 的 nodeInfo 直接作为 oldNodeData 传入
  //     修复前：this.checkRefChangeAndUpdateNode(nodeInfo, nodeData);
  if (/this\.checkRefChangeAndUpdateNode\(\s*nodeInfo\s*,\s*nodeData\s*\)/.test(saveSubBody)) {
    failures.push(
      '保存订阅仍把 nodeInfo(事件载荷默认 {}) 作为 oldNodeData 传给 checkRefChangeAndUpdateNode',
    );
  }
  // C4. 旧节点不存在时安全跳过：cloneDeep 读取结果须兜底为 {}（不可为 null，否则
  //     checkRefChangeAndUpdateNode 内 (oldNodeData as HasOutputsNode).outputs 对 null 抛错）。
  //     接受三元 else 形式 `? cloneDeep(...) : ({} as NodeInfo)` 或空值合并 `cloneDeep(...) ?? ({} as ...)`。
  const safeFallback =
    /\?\s*cloneDeep\([^)]*\)\s*:\s*\(?\{\s*\}(?:\s+as\s+\w+)?\s*\)?/.test(saveSubBody) ||
    /cloneDeep\([^)]*\)\s*\?\?\s*\(?\{\s*\}(?:\s+as\s+\w+)?\s*\)?/.test(saveSubBody);
  if (!safeFallback) {
    failures.push('保存订阅未对旧节点缺失做 {} 兜底 -> 新增节点场景 oldNodeData 可能为 null');
  }
}

// ---- D. 保存入口 -> 引用同步 端到端纯逻辑回放（时序契约） ----------------
// 复刻 保存订阅 -> checkRefChangeAndUpdateNode(oldNodeData, nodeData)
//   -> getOutputsRefIndex(old) vs getOutputsRefIndex(new) -> updatedRefs
//   -> updateRefType -> fixRefTypeOutdate -> changeLLMVisionName 的数据流，
// 验证：旧节点取自 graph（修复）时 updatedRefs 非空且重命名触发；
//       旧节点取自事件载荷 {}（缺陷）时 updatedRefs 为空、不触发（即 bug 现场）。
function cloneDeepRepl(x) {
  return JSON.parse(JSON.stringify(x));
}

function getOutputsRefIndexRepl(nodeId, fields, acc = []) {
  (fields || []).forEach((f) => {
    const p = f.name;
    if (f.type === 'array' || f.type === 'object') {
      acc.push({ id: `${nodeId}.${p}`, type: f.type, schema: f.schema });
    } else {
      acc.push({ id: `${nodeId}.${p}`, type: f.type });
    }
  });
  return acc;
}

function replaySaveEntry(oldNodeData, nodeData, llm) {
  const oldRefs = getOutputsRefIndexRepl(nodeData.id, oldNodeData.outputs);
  const currRefs = getOutputsRefIndexRepl(nodeData.id, nodeData.outputs);
  const updatedRefs = currRefs.filter((r) => {
    const o = oldRefs.find((x) => x.id === r.id);
    return !!o && !(o.type === r.type);
  });
  if (!updatedRefs.length) {
    return { invoked: false, updatedRefs };
  }
  const field = llm.inputs[0];
  return { invoked: changeLLMVisionName(field, updatedRefs[0], llm), updatedRefs };
}

const startId = 'node_start';
const startOldImg = {
  id: startId,
  type: 'Start',
  outputs: [{ name: '_image_vision_1', type: 'file/image' }],
};
const startNewVid = {
  id: startId,
  type: 'Start',
  outputs: [{ name: '_image_vision_1', type: 'file/video' }],
};
const llmImg = {
  type: 'LLM',
  configs: { vision: ['_image_vision_1'] },
  inputs: [{
    name: '_image_vision_1',
    value: {
      type: 'ref',
      content: { node_id: startId, field_name: ['_image_vision_1'] },
    },
  }],
};

// 修复契约：旧节点取自 graph 深拷贝（旧节点存在）-> updatedRefs 非空 -> 重命名触发
const ok = replaySaveEntry(cloneDeepRepl(startOldImg), startNewVid, cloneDeepRepl(llmImg));
if (!ok.invoked || !ok.invoked.changed) {
  failures.push(
    '回放(旧节点取自graph)：期望触发 changeLLMVisionName，但 changed=false；updatedRefs='
    + JSON.stringify(ok.updatedRefs),
  );
} else if (ok.invoked.after !== '_video_vision_1') {
  failures.push(
    '回放(旧节点取自graph)：重命名后字段名期望 _video_vision_1，实际 ' + ok.invoked.after,
  );
}

// 缺陷现场：旧节点取自事件载荷 {} -> oldRefs 空 -> updatedRefs 空 -> 不触发（证明根因）
const bug = replaySaveEntry({}, startNewVid, cloneDeepRepl(llmImg));
if (bug.invoked !== false) {
  failures.push('回放(旧节点取自{} )：旧节点为空时不应触发重命名（updatedRefs 应为空）');
}
if (bug.updatedRefs.length !== 0) {
  failures.push(
    '回放(旧节点取自{} )：旧节点为空时 updatedRefs 应为空，实际 '
    + JSON.stringify(bug.updatedRefs),
  );
}

if (failures.length) {
  console.error('FAIL（' + failures.length + ' 项）：');
  failures.forEach(f => console.error('  - ' + f));
  process.exit(1);
}

console.log(
  'PASS：changeLLMVisionName 标量兜底 + findIndex=-1 安全 no-op；fixRefTypeOutdate 标量也同步；'
  + '四种切换/未变化/缺失/边界 no-op 全部一致；保存订阅入口按 nodeData.id 从 graph 深拷贝旧节点并 {} 兜底',
);
