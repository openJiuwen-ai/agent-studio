import { TestBed } from '@angular/core/testing';
import { FormBuilder } from '@angular/forms';
import { DynamicNodeParamsComponent } from './dynamic-node-params.component';
import { ToolService } from '@services/tool.service';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { I18NextEagerPipe } from 'angular-i18next';
import { of } from 'rxjs';

/**
 * DynamicNodeParamsComponent - matchType 递归校验单元测试。
 * 覆盖 bug001 runtime 输入语义校验：array<object> 元素子字段类型递归，
 * 兼容 children（配置侧）与 schema（run-modal 后端格式）两种声明格式。
 * matchType 为 private 方法，通过 as any 访问。
 */
describe('DynamicNodeParamsComponent - matchType', () => {
  let component: any;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DynamicNodeParamsComponent],
      providers: [
        FormBuilder,
        { provide: ToolService, useValue: { EditorOptions: {} } as any },
        { provide: agentCommonLogic, useValue: {} as any },
        { provide: AppAgentRepoService, useValue: {} as any },
        { provide: I18NextEagerPipe, useValue: { transform: (k: string) => k } as any },
        { provide: AppFlowService, useValue: { fileListUpdate$: () => of([]) } as any },
        { provide: AgentConfigService, useValue: {} as any },
      ],
    }).compileComponents();
    component = TestBed.createComponent(DynamicNodeParamsComponent).componentInstance;
  });

  const callMatchType = (value: any, type: string, subFields?: any) =>
    (component as any).matchType(value, type, subFields);

  // ===== runtime 一层：array<object> =====

  it('array<object> + 123(非数组) → false', () => {
    expect(callMatchType(123, 'array<object>')).toBe(false);
  });

  it('array<object> + [{a:1}](对象数组) → true', () => {
    expect(callMatchType([{ a: 1 }], 'array<object>')).toBe(true);
  });

  it('array<object> + [1,2](元素非 object,无 schema) → false(元素类型为 object,数字非 object)', () => {
    expect(callMatchType([1, 2], 'array<object>')).toBe(false);
  });

  // ===== runtime 递归：children 格式（配置侧，type:string[]）=====

  const childrenConfig = [
    { name: 'name', type: ['string'] },
    { name: 'age', type: ['integer'] },
  ];

  it('children 格式：[{name:"ppp",age:1}] → true（子字段类型全对）', () => {
    expect(callMatchType([{ name: 'ppp', age: 1 }], 'array<object>', childrenConfig)).toBe(true);
  });

  it('children 格式：[{name:123,age:1}] → false（name 应 string 实 number）', () => {
    expect(callMatchType([{ name: 123, age: 1 }], 'array<object>', childrenConfig)).toBe(false);
  });

  it('children 格式：[{name:"ppp",age:"123"}] → false（age 应 integer 实 string）', () => {
    expect(callMatchType([{ name: 'ppp', age: '123' }], 'array<object>', childrenConfig)).toBe(false);
  });

  it('children 格式：[{name:"ppp"}] → true（缺失字段不报）', () => {
    expect(callMatchType([{ name: 'ppp' }], 'array<object>', childrenConfig)).toBe(true);
  });

  // ===== runtime 递归：schema 格式（run-modal 后端，type:string + .schema）=====

  const schemaBackend = [
    { name: 'name', type: 'string' },
    { name: 'addr', type: 'object', schema: [{ name: 'city', type: 'string' }] },
  ];

  it('schema 格式：[{name:"ppp"}] → true', () => {
    expect(callMatchType([{ name: 'ppp' }], 'array<object>', schemaBackend)).toBe(true);
  });

  it('schema 格式：[{name:123}] → false（name 应 string 实 number）', () => {
    expect(callMatchType([{ name: 123 }], 'array<object>', schemaBackend)).toBe(false);
  });

  it('schema 格式：[{name:"ppp",addr:{city:123}}] → false（addr.city 应 string 实 number）', () => {
    expect(callMatchType([{ name: 'ppp', addr: { city: 123 } }], 'array<object>', schemaBackend)).toBe(false);
  });

  it('schema 格式：[{name:"ppp",addr:{city:"sh"}}] → true', () => {
    expect(callMatchType([{ name: 'ppp', addr: { city: 'sh' } }], 'array<object>', schemaBackend)).toBe(true);
  });

  // ===== type === 'array' + schema 元素描述（中风险1）=====

  it('type=array + schema={type:object,schema:[{name:name,type:string}]}：[{name:123}] → false', () => {
    const elementSchema = { type: 'object', schema: [{ name: 'name', type: 'string' }] };
    expect(callMatchType([{ name: 123 }], 'array', elementSchema)).toBe(false);
  });

  it('type=array + schema={type:string}：["a","b"] → true', () => {
    expect(callMatchType(['a', 'b'], 'array', { type: 'string' })).toBe(true);
  });

  it('type=array + schema={type:string}：[1,2] → false（元素非 string）', () => {
    expect(callMatchType([1, 2], 'array', { type: 'string' })).toBe(false);
  });

  it('type=array + 无 schema：[1,2,3] → true（只校验是数组）', () => {
    expect(callMatchType([1, 2, 3], 'array', null)).toBe(true);
  });

  // ===== object 类型 =====

  it('object + {a:1}(无子字段声明) → true', () => {
    expect(callMatchType({ a: 1 }, 'object', null)).toBe(true);
  });

  it('object + 非 object → false', () => {
    expect(callMatchType(123, 'object', null)).toBe(false);
    expect(callMatchType([1], 'object', null)).toBe(false);
  });

  // ===== integer 整数约束（中风险2：与后端一致）=====

  it('integer 1 → true（整数）', () => {
    expect(callMatchType(1, 'integer')).toBe(true);
  });

  it('integer 1.5 → false（浮点应拒绝）', () => {
    expect(callMatchType(1.5, 'integer')).toBe(false);
  });

  it('integer "1" → true（字符串整数）', () => {
    expect(callMatchType('1', 'integer')).toBe(true);
  });

  it('integer "1.5" → false（字符串浮点应拒绝）', () => {
    expect(callMatchType('1.5', 'integer')).toBe(false);
  });

  it('number 1.5 → true（number 接受浮点）', () => {
    expect(callMatchType(1.5, 'number')).toBe(true);
  });

  it('number "1.5" → true（number 接受字符串浮点）', () => {
    expect(callMatchType('1.5', 'number')).toBe(true);
  });

  it('integer "" → false（空串拒绝，与后端 Double.parseDouble 一致）', () => {
    expect(callMatchType('', 'integer')).toBe(false);
  });

  it('integer "  " → false（纯空白拒绝）', () => {
    expect(callMatchType('  ', 'integer')).toBe(false);
  });

  it('number "" → false（空串拒绝）', () => {
    expect(callMatchType('', 'number')).toBe(false);
  });

  // ===== array<object> + 后端 schema 元素描述（中风险1：schemaFieldSchema 提取）=====

  it('array<object> + 后端 schema 元素描述：[{name:123}] → false（子字段类型递归校验）', () => {
    // 后端 schema 格式：array<object>, subFields = {type:object, schema:[{name:name,type:string}]}
    const elementDesc = { type: 'object', schema: [{ name: 'name', type: 'string' }] };
    expect(callMatchType([{ name: 123 }], 'array<object>', elementDesc)).toBe(false);
  });

  it('array<object> + 后端 schema 元素描述：[{name:"ppp"}] → true', () => {
    const elementDesc = { type: 'object', schema: [{ name: 'name', type: 'string' }] };
    expect(callMatchType([{ name: 'ppp' }], 'array<object>', elementDesc)).toBe(true);
  });
});
