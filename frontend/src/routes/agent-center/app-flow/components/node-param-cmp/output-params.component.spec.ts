import { TestBed } from '@angular/core/testing';
import { I18NextEagerPipe } from 'angular-i18next';
import { OutputParamsComponent } from './output-params.component';
import { LineClampDirective } from '@shared/directives/line-clamp.directive';
import { ValueWarnDirective } from '@shared/directives/value-warn.directive';
import { I18NextModule } from 'angular-i18next';

/**
 * OutputParamsComponent - hasInvalidDescendant 单元测试。
 * 覆盖 bug001 画布字段高亮向上传递：父字段名合法但后代字段名违规时也应高亮。
 */
describe('OutputParamsComponent - hasInvalidDescendant', () => {
  let component: OutputParamsComponent;
  const i18nSpy = { transform: (k: string) => k } as unknown as I18NextEagerPipe;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OutputParamsComponent, LineClampDirective, ValueWarnDirective, I18NextModule],
      providers: [{ provide: I18NextEagerPipe, useValue: i18nSpy }],
    }).compileComponents();
    component = TestBed.createComponent(OutputParamsComponent).componentInstance;
  });

  // 后端 schema 形式：array<object>，schema={type:object, schema:[子字段]}
  const buildArrayObjectField = (subFields: any[]) => ({
    name: 'ppp',
    type: 'array',
    schema: { type: 'object', schema: subFields },
  });

  const buildObjectField = (subFields: any[]) => ({
    name: 'ppp',
    type: 'object',
    schema: subFields,
  });

  it('父 ppp(array<object>) + 子 123(违规) → 应返回 true', () => {
    const field = buildArrayObjectField([{ name: '123', type: 'string' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(true);
  });

  it('父 ppp(array<object>) + 子 ppp(合法) → 应返回 false', () => {
    const field = buildArrayObjectField([{ name: 'ppp', type: 'string' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(false);
  });

  it('父 ppp(object) + 子 123(违规) → 应返回 true', () => {
    const field = buildObjectField([{ name: '123', type: 'string' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(true);
  });

  it('嵌套：父 ppp → 子 addr(object, 合法) → 孙 123(违规) → 应返回 true', () => {
    const field = buildArrayObjectField([
      { name: 'addr', type: 'object', schema: [{ name: '123', type: 'string' }] },
    ]);
    expect(component.hasInvalidDescendant(field as any)).toBe(true);
  });

  it('全合法 → 应返回 false', () => {
    const field = buildArrayObjectField([{ name: 'age', type: 'integer' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(false);
  });

  it('array<string>(无子字段) → 应返回 false', () => {
    const field = { name: 'ppp', type: 'array', schema: { type: 'string' } };
    expect(component.hasInvalidDescendant(field as any)).toBe(false);
  });

  it('无 schema → 应返回 false', () => {
    const field = { name: 'ppp', type: 'string' };
    expect(component.hasInvalidDescendant(field as any)).toBe(false);
  });

  it('子字段名含连字符（合法，与后端 isNameValid 一致）→ 应返回 false', () => {
    // 后端 isNameValid 允许连字符 [a-zA-Z0-9_-]*，前端 isNameValid 需一致
    const field = buildArrayObjectField([{ name: 'my-field', type: 'string' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(false);
  });

  it('子字段名含点号（非法）→ 应返回 true', () => {
    const field = buildArrayObjectField([{ name: 'my.field', type: 'string' }]);
    expect(component.hasInvalidDescendant(field as any)).toBe(true);
  });
});
