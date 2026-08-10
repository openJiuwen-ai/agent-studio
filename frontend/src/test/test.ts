import { getTestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

// 初始化 Angular 测试环境。
// zone.js/testing 由 `@angular/build:karma` 的 zoneTestingEntryPoint 自动加载，
// 此处不手动 import，避免重复初始化（zone.js 0.15.x 也无 `dist/zone-testing` 路径）。
// spec 发现由 builder 的 findTests/getTestEntrypoints 按 tsconfig.spec.json 的 include glob 完成，
// 不使用 webpack 的 require.context（esbuild 版 builder 不支持）。

// 测试环境 shim：single-spa 全局（window.AppWebPath）在 Karma 下未注入，
// 但传递依赖（http.service → utils → flow-utils → flow.const → cdnAssetUrl）
// 在模块加载期读 window.AppWebPath，须先提供，否则 spec 模块初始化即抛错。
const w = window as unknown as { AppWebPath?: string; __x6_instances__?: unknown[] };
w.AppWebPath = w.AppWebPath ?? '/';
w.__x6_instances__ = w.__x6_instances__ ?? [];

getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
);
