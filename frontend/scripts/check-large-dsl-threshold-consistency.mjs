#!/usr/bin/env node
/**
 * 大 DSL 阈值常量一致性检查（node 环境，不在 Karma 浏览器沙箱执行）。
 *
 * TS 常量不能被 Shell 引用，前端 environment.ts 与 docker start.sh 分别定义同值常量，
 * 本脚本读取多处来源并断言相等/存在，防止压测后调值时只改一处产生漂移：
 *   1. frontend/src/environment/environment.ts   （DEFAULT/MAX_LARGE_DSL_BYTES_THRESHOLD）
 *   2. docker/studio-console/script/start.sh     （DEFAULT/MAX_LARGE_DSL_BYTES_THRESHOLD）
 *   3. frontend/.staging/index.html              （large_dsl_placeholder 占位符；真实构建入口，
 *      angular.json "index": ".staging/index.html" —— 检查 src/index.html 无意义）
 *   4. deploy/.env.template / docker-compose.yml / k8s studio-console.yaml 的默认值 10485760
 *   5. （若存在）frontend/dist/hws/index.html    （构建产物层：能发现构建配置变化/HTML 优化
 *      导致占位符丢失 —— 由 postbuild 调用，构建后执行）
 *
 * 用法：npm run check:threshold（构建前，prebuild 自动执行）
 *       npm run check:threshold:dist（构建后，postbuild 自动执行）
 */

import { readFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const frontendRoot = resolve(here, '..');
const repoRoot = resolve(frontendRoot, '..');

const withDist = process.argv.includes('--dist');

let failures = [];
function fail(msg) {
  failures.push(msg);
}

function read(rel) {
  const p = resolve(repoRoot, rel);
  if (!existsSync(p)) {
    return null;
  }
  return readFileSync(p, 'utf-8');
}

function extractNumber(source, name, label) {
  // environment.ts 写法是 `10 * 1024 * 1024` 表达式，start.sh 是纯数字；两种都支持并求积
  const m = source.match(new RegExp(`${name}\\s*=\\s*([\\d\\s*]+?)[;\\n]`));
  if (!m) {
    fail(`[FAIL] ${label} 未定义 ${name}`);
    return null;
  }
  return m[1]
    .split('*')
    .map((s) => Number(s.trim()))
    .filter((n) => !Number.isNaN(n))
    .reduce((acc, n) => acc * n, 1);
}

// ---- 1. 前端与 Shell 常量 ----
const envTs = read('frontend/src/environment/environment.ts');
const startSh = read('docker/studio-console/script/start.sh');
if (!envTs || !startSh) {
  console.error('[FAIL] environment.ts 或 start.sh 不可读');
  process.exit(1);
}
const tsDefault = extractNumber(envTs, 'DEFAULT_LARGE_DSL_BYTES_THRESHOLD', 'environment.ts');
const tsMax = extractNumber(envTs, 'MAX_LARGE_DSL_BYTES_THRESHOLD', 'environment.ts');
const shDefault = extractNumber(startSh, 'DEFAULT_LARGE_DSL_BYTES_THRESHOLD', 'start.sh');
const shMax = extractNumber(startSh, 'MAX_LARGE_DSL_BYTES_THRESHOLD', 'start.sh');
if (tsDefault !== shDefault) fail(`[FAIL] DEFAULT 不一致：environment.ts=${tsDefault}, start.sh=${shDefault}`);
if (tsMax !== shMax) fail(`[FAIL] MAX 不一致：environment.ts=${tsMax}, start.sh=${shMax}`);

// ---- 2. 构建入口占位符（真实入口是 .staging/index.html，不是 src/index.html）----
const PLACEHOLDER_LINE = "window.largeDslBytesThreshold = 'large_dsl_placeholder'";
const stagingHtml = read('frontend/.staging/index.html');
if (!stagingHtml) {
  fail('[FAIL] frontend/.staging/index.html 不可读');
} else if (!stagingHtml.includes(PLACEHOLDER_LINE)) {
  fail('[FAIL] .staging/index.html（真实构建入口）缺少 large_dsl_placeholder 占位符');
}
// src/index.html 不参与构建（angular.json 未引用）；若存在则保持同步提示
const srcHtml = read('frontend/src/index.html');
if (srcHtml && !srcHtml.includes(PLACEHOLDER_LINE)) {
  fail('[WARN->FAIL] src/index.html 与 .staging 不同步（缺占位符；建议两处保持一致）');
}

// ---- 3. 部署默认值（.env.template / docker-compose / k8s）与 start.sh DEFAULT 一致 ----
const envTpl = read('deploy/.env.template');
if (envTpl) {
  const m = envTpl.match(/^LARGE_DSL_BYTES_THRESHOLD=(\d+)$/m);
  if (!m) fail('[FAIL] deploy/.env.template 未定义 LARGE_DSL_BYTES_THRESHOLD=<数字>');
  else if (Number(m[1]) !== shDefault) fail(`[FAIL] .env.template 默认值 ${m[1]} ≠ start.sh DEFAULT ${shDefault}`);
} else {
  fail('[FAIL] deploy/.env.template 不可读');
}
const compose = read('deploy/docker-compose.yml');
if (compose) {
  const m = compose.match(/LARGE_DSL_BYTES_THRESHOLD:\s*\$\{LARGE_DSL_BYTES_THRESHOLD:-(\d+)\}/);
  if (!m) fail('[FAIL] docker-compose 未定义 ${LARGE_DSL_BYTES_THRESHOLD:-<数字>} 形式默认值');
  else if (Number(m[1]) !== shDefault) fail(`[FAIL] docker-compose 默认值 ${m[1]} ≠ start.sh DEFAULT ${shDefault}`);
} else {
  fail('[FAIL] deploy/docker-compose.yml 不可读');
}
const k8s = read('deploy/k8s/studio-console.yaml');
if (k8s) {
  const m = k8s.match(/name:\s*LARGE_DSL_BYTES_THRESHOLD\s*\n\s*value:\s*'?(\d+)'?/);
  if (!m) fail('[FAIL] k8s studio-console.yaml 未定义 LARGE_DSL_BYTES_THRESHOLD env');
  else if (Number(m[1]) !== shDefault) fail(`[FAIL] k8s 默认值 ${m[1]} ≠ start.sh DEFAULT ${shDefault}`);
} else {
  fail('[FAIL] deploy/k8s/studio-console.yaml 不可读');
}

// ---- 4. 构建产物层（--dist / postbuild）：dist/hws/index.html 必须仍含占位符 ----
if (withDist) {
  const distHtml = read('frontend/dist/hws/index.html');
  if (!distHtml) {
    fail('[FAIL] dist/hws/index.html 不存在（先 pnpm run build）');
  } else if (!distHtml.includes(PLACEHOLDER_LINE)) {
    fail('[FAIL] 构建产物 dist/hws/index.html 丢失占位符（构建配置/HTML 优化导致？Console 将启动失败）');
  }
}

if (failures.length) {
  console.error(failures.join('\n'));
  console.error('\n常量漂移：请同步调整 environment.ts / start.sh / .staging/index.html / 部署文件（压测后调值时）。');
  process.exit(1);
}

console.log(
  `[OK] 常量一致：DEFAULT=${tsDefault} (${(tsDefault / 1024 / 1024).toFixed(0)}MB), ` +
    `MAX=${tsMax} (${(tsMax / 1024 / 1024).toFixed(0)}MB)，构建入口与部署默认值一致` +
    (withDist ? '，构建产物含占位符' : ''),
);
