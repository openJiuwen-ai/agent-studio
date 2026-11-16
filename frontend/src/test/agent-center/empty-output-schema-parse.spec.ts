/**
 * 空/残缺 output_schema 解析：不误弹 parse_res_error。
 * 覆盖 plugin / MCP 响应解析在 null、空串、非法 JSON、无 properties、合法 schema 下的语义。
 */
import { MessageComponent } from '@shared/services/cfdata.service';
import {
  pluginSchemaStr2Res,
  resSchemaStr2Field,
} from '../../routes/agent-center/app-plugin/utils';
import { resSchemaStrMCPField } from '../../routes/agent-center/app-mcp-service/utils';

describe('empty output_schema parse guards', () => {
  let showErrorSpy: jasmine.Spy;

  beforeEach(() => {
    showErrorSpy = spyOn(MessageComponent, 'showError');
  });

  const cases: Array<{
    name: string;
    input: any;
    expectEmpty: boolean;
    expectToast: boolean;
  }> = [
    { name: 'null/undefined 空值', input: null, expectEmpty: true, expectToast: false },
    { name: '空串', input: '', expectEmpty: true, expectToast: false },
    { name: '非法 JSON', input: '{', expectEmpty: false, expectToast: true },
    { name: '空对象 {}', input: '{}', expectEmpty: true, expectToast: false },
    {
      name: '仅 type 无 properties',
      input: '{"type":"object"}',
      expectEmpty: true,
      expectToast: false,
    },
    {
      name: '顶层数组 []',
      input: '[]',
      expectEmpty: true,
      expectToast: false,
    },
    {
      name: '合法 schema',
      input: '{"type":"object","properties":{"msg":{"type":"string","description":"d"}}}',
      expectEmpty: false,
      expectToast: false,
    },
    {
      name: '嵌套 array<object> 无 items.properties',
      input:
        '{"type":"object","properties":{"results":{"type":"array","items":{"type":"object"}}}}',
      expectEmpty: false,
      expectToast: false,
    },
  ];

  describe('pluginSchemaStr2Res', () => {
    for (const c of cases) {
      it(c.name, () => {
        const result = pluginSchemaStr2Res(c.input as any);
        if (c.expectEmpty) {
          expect(result.length).toBe(0);
        } else if (!c.expectToast) {
          expect(result.length).toBeGreaterThan(0);
        }
        if (c.expectToast) {
          expect(showErrorSpy).toHaveBeenCalled();
        } else {
          expect(showErrorSpy).not.toHaveBeenCalled();
        }
      });
    }
  });

  describe('resSchemaStr2Field', () => {
    for (const c of cases) {
      it(c.name, () => {
        const result = resSchemaStr2Field(c.input as any);
        if (c.expectEmpty) {
          expect(result.length).toBe(0);
        } else if (!c.expectToast) {
          expect(result.length).toBeGreaterThan(0);
        }
        if (c.expectToast) {
          expect(showErrorSpy).toHaveBeenCalled();
        } else {
          expect(showErrorSpy).not.toHaveBeenCalled();
        }
      });
    }
  });

  describe('resSchemaStrMCPField', () => {
    for (const c of cases) {
      it(c.name, () => {
        const result = resSchemaStrMCPField(c.input as any);
        if (c.expectEmpty) {
          expect(result.length).toBe(0);
        } else if (!c.expectToast) {
          expect(result.length).toBeGreaterThan(0);
        }
        if (c.expectToast) {
          expect(showErrorSpy).toHaveBeenCalled();
        } else {
          expect(showErrorSpy).not.toHaveBeenCalled();
        }
      });
    }
  });
});
