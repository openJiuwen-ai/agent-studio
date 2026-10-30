// iframe SSO 桥接单参数解析 spec：resolveIframeSsoTokenParam 严格解析（纯函数，浏览器安全）。
// 规则：空 / 占位符残留 / 含非法字符（仅允许 [A-Za-z0-9_-]，兼作 URL 参数名/Cookie 名/
// 头名，且无正则元字符可安全内嵌 RegExp）一律返回 null = 定制关闭（默认，行为与现状一致）。
// 占位符三处同源（.staging/src index.html、start.sh、部署文件）由
// scripts/check-large-dsl-threshold-consistency.mjs 构建期断言，spec 只测解析语义。

import {
  IFRAME_SSO_TOKEN_PARAM_PLACEHOLDER,
  resolveIframeSsoTokenParam,
} from '../../environment/environment';

describe('resolveIframeSsoTokenParam（严格解析，空/非法一律关闭）', () => {
  describe('合法输入生效', () => {
    it('常规参数名生效', () => {
      expect(resolveIframeSsoTokenParam('access_token')).toBe('access_token');
      expect(resolveIframeSsoTokenParam('token')).toBe('token');
    });

    it('允许字母/数字/下划线/连字符', () => {
      expect(resolveIframeSsoTokenParam('Token-1_x')).toBe('Token-1_x');
    });

    it('首尾空白被 trim', () => {
      expect(resolveIframeSsoTokenParam('  access_token ')).toBe('access_token');
    });
  });

  describe('空值关闭（默认）', () => {
    it('空串/纯空白 → null', () => {
      expect(resolveIframeSsoTokenParam('')).toBeNull();
      expect(resolveIframeSsoTokenParam('   ')).toBeNull();
    });
  });

  describe('占位符残留关闭（防 start.sh 未替换的部署误开）', () => {
    it('占位符字面量（含带空白） → null', () => {
      expect(resolveIframeSsoTokenParam(IFRAME_SSO_TOKEN_PARAM_PLACEHOLDER)).toBeNull();
      expect(resolveIframeSsoTokenParam(`  ${IFRAME_SSO_TOKEN_PARAM_PLACEHOLDER}  `)).toBeNull();
    });
  });

  describe('非法字符关闭（参数/Cookie/头名合法字符集之外）', () => {
    it('空格/&/=/%/中文等 → null', () => {
      expect(resolveIframeSsoTokenParam('access token')).toBeNull();
      expect(resolveIframeSsoTokenParam('a&b')).toBeNull();
      expect(resolveIframeSsoTokenParam('a=b')).toBeNull();
      expect(resolveIframeSsoTokenParam('a%20b')).toBeNull();
      expect(resolveIframeSsoTokenParam('令牌')).toBeNull();
    });
  });

  describe('类型非法关闭', () => {
    it('数值/布尔/对象/数组/null/undefined → null', () => {
      expect(resolveIframeSsoTokenParam(123)).toBeNull();
      expect(resolveIframeSsoTokenParam(true)).toBeNull();
      expect(resolveIframeSsoTokenParam({ v: 'access_token' })).toBeNull();
      expect(resolveIframeSsoTokenParam(['access_token'])).toBeNull();
      expect(resolveIframeSsoTokenParam(null)).toBeNull();
      expect(resolveIframeSsoTokenParam(undefined)).toBeNull();
    });
  });
});
