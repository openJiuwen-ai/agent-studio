// 大 DSL 阈值配置化 spec：resolveLargeDslBytesThreshold 严格解析（纯函数，浏览器安全）。
// 规划：工作记录/20260808/2026-08-08-001-大DSL阈值配置化规划.md（三轮审视后终版）
// 规则：与 Shell start.sh 接受范围一致（^[1-9][0-9]*$ + ≤ MAX），先格式校验再数值转换，
// 不能先 Number(raw)（'1e6'/'01'/true/[1024] 会被错误接受）。
// 常量一致性检查（environment.ts vs start.sh vs index.html）在 node 脚本
// scripts/check-large-dsl-threshold-consistency.mjs 执行（npm run check:threshold），
// 不在 Karma 浏览器沙箱读文件。

import {
  DEFAULT_LARGE_DSL_BYTES_THRESHOLD,
  MAX_LARGE_DSL_BYTES_THRESHOLD,
  resolveLargeDslBytesThreshold,
} from '../../environment/environment';

describe('resolveLargeDslBytesThreshold（严格解析，与 Shell 规则一致）', () => {
  describe('合法输入生效', () => {
    it('十进制字符串生效', () => {
      expect(resolveLargeDslBytesThreshold('10485760')).toBe(10485760);
      expect(resolveLargeDslBytesThreshold('1')).toBe(1);
    });

    it('数值类型生效', () => {
      expect(resolveLargeDslBytesThreshold(10485760)).toBe(10485760);
    });

    it('100MB 边界值生效', () => {
      expect(resolveLargeDslBytesThreshold(MAX_LARGE_DSL_BYTES_THRESHOLD)).toBe(
        MAX_LARGE_DSL_BYTES_THRESHOLD,
      );
      expect(resolveLargeDslBytesThreshold(String(MAX_LARGE_DSL_BYTES_THRESHOLD))).toBe(
        MAX_LARGE_DSL_BYTES_THRESHOLD,
      );
    });
  });

  describe('类型非法回退默认', () => {
    it('布尔/对象/数组/null/undefined 回退', () => {
      expect(resolveLargeDslBytesThreshold(true)).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold(false)).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold({ v: 10485760 })).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold([1024])).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold(null)).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold(undefined)).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
    });
  });

  describe('十进制格式非法回退默认（Shell 同样拒绝）', () => {
    it('科学计数法回退（Number("1e6")=1000000 但格式不符）', () => {
      expect(resolveLargeDslBytesThreshold('1e6')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('1E6')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
    });

    it('前导零/小数/负数/零/带空格/正号回退', () => {
      expect(resolveLargeDslBytesThreshold('01')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('1.5')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('-10485760')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('0')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold(' 10485760 ')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('+10485760')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
    });

    it('占位符/空串/含非数字字符回退（防注入同源）', () => {
      expect(resolveLargeDslBytesThreshold('large_dsl_placeholder')).toBe(
        DEFAULT_LARGE_DSL_BYTES_THRESHOLD,
      );
      expect(resolveLargeDslBytesThreshold('')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold("10485760'; alert(1)")).toBe(
        DEFAULT_LARGE_DSL_BYTES_THRESHOLD,
      );
    });
  });

  describe('超上限回退默认', () => {
    it('100MB+1 / 1GB / 4GB 回退（isSafeInteger 通过但 > MAX）', () => {
      expect(resolveLargeDslBytesThreshold(MAX_LARGE_DSL_BYTES_THRESHOLD + 1)).toBe(
        DEFAULT_LARGE_DSL_BYTES_THRESHOLD,
      );
      expect(resolveLargeDslBytesThreshold('1073741824')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
      expect(resolveLargeDslBytesThreshold('4294967296')).toBe(DEFAULT_LARGE_DSL_BYTES_THRESHOLD);
    });

    it('超 JS 安全整数回退', () => {
      expect(resolveLargeDslBytesThreshold('9007199254740993')).toBe(
        DEFAULT_LARGE_DSL_BYTES_THRESHOLD,
      );
    });
  });
});
