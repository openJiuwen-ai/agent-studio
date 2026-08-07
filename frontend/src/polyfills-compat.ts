/**
 * polyfills-compat.ts
 *
 * 为 Chrome 90/91 等旧内核浏览器补齐业务代码用到、但内核缺失的运行时 API。
 * 通过 angular.json 的 polyfills 数组引入,Angular 构建时会与 zone.js 一起
 * 打包进 polyfills-xxx.js,作为 <script type="module"> 在 main.js 之前执行,
 * 确保所有 API 在 Angular 启动前补齐。core-js 采用「原生 || polyfill」模式,
 * 新版浏览器原生 API 优先,polyfill 不覆盖,向上兼容。
 *
 * Chrome 90 缺失(实测报错 + 产物扫描,均来自业务源码如 sse.ts、preview-debug 等):
 *   - Object.hasOwn        (Chrome 93+)
 *   - Array.prototype.at   (Chrome 92+)
 *   - Array.prototype.findLast / findLastIndex (Chrome 97+)
 *   - structuredClone      (Chrome 98+)
 *
 * 注意:core-js 的 structuredClone polyfill (web.structured-clone) 依赖若干
 * 前置模块,core-js 内部已处理依赖,直接 import 即可。
 */
import 'core-js/modules/es.object.has-own.js';
import 'core-js/modules/es.array.at.js';
import 'core-js/modules/es.array.find-last.js';
import 'core-js/modules/es.array.find-last-index.js';
import 'core-js/modules/web.structured-clone.js';
