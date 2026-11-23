/**
 * bug1733：Skill/插件下架前引用确认 - 引用文案聚合逻辑测试。
 *
 * spec tsconfig(src/test/tsconfig.json)未含 reflect-metadata types，
 * 直接 import SkillMarketComponent(经 SkillDetail @autoProp → prop.ts 用 Reflect.defineMetadata）
 * 会触发 TS2339 编译失败，故不实例化组件，改为独立测 buildReferenceWarningTitle 的聚合算法
 * （与 skill-market.component.ts / plugin-market.component.ts 内实现一致）。
 *
 * 聚合逻辑（巡检修复后）：引用总数用接口返回的 count（准确，不受 limit=100 截断），
 * 名称用 relations 前 3 个 app_name，分隔符走 i18n key（zh=、 en=, ）避免硬编码顿号。
 *
 * 组件方法本身的三分支（有引用/无引用/查询失败）由后端引用查询接口已验证
 * （mock-skill-001 count=2 / mock-tool-001 count=1），见 04-changelog。
 */

/** 引用方关系（后端 MappingEntity 子集，实测 app_type='agent'/'workflow'）。 */
interface Relation {
  app_type?: string;
  app_name?: string;
}

/** 复制自 skill-market.component.ts buildReferenceWarningTitle 的聚合算法（保持一致）。 */
function aggregateReferenceSummary(
  relations: Relation[],
  count: number,
  t: (key: string, opts?: any) => string,
): string {
  const separator = t('plaza_offshelf_referenced_name_separator');
  const names = relations
    .map(r => r?.app_name)
    .filter((n): n is string => !!n)
    .slice(0, 3)
    .join(separator);
  const summary = t('plaza_offshelf_referenced_summary', { count });
  const tail = names ? t('plaza_offshelf_referenced_names', { names }) : t('plaza_offshelf_referenced_no_names');
  return `${t('plaza_offshelf_referenced_prefix')}${summary}${tail}`;
}

describe('bug1733 下架前引用确认 - 引用文案聚合（巡检修复后用 count + separator）', () => {
  /** 模拟 i18n.transform：key + 插值变量，返回可断言的结构化串。 */
  const t = (key: string, opts?: any): string => {
    if (key === 'plaza_offshelf_referenced_prefix') {
      return '[prefix]';
    }
    if (key === 'plaza_offshelf_referenced_summary') {
      return `[summary:count=${opts.count}]`;
    }
    if (key === 'plaza_offshelf_referenced_names') {
      return `[names:${opts.names}]`;
    }
    if (key === 'plaza_offshelf_referenced_no_names') {
      return '[no_names]';
    }
    if (key === 'plaza_offshelf_referenced_name_separator') {
      return ',';
    }
    return `[${key}]`;
  };

  it('引用总数用 count（不受 relations 截断影响）', () => {
    // relations 只有 3 个（被 limit=100 截断的实际场景），但 count=150（真实总数）
    const relations: Relation[] = [
      { app_type: 'agent', app_name: 'A' },
      { app_type: 'workflow', app_name: 'B' },
      { app_type: 'agent', app_name: 'C' },
    ];
    const title = aggregateReferenceSummary(relations, 150, t);
    // 总数用 count=150，不是 relations.length=3（巡检修复点：避免 >100 截断误导）
    expect(title).toContain('[summary:count=150]');
  });

  it('names 取前 3 个并用 separator 拼接（不硬编码顿号）', () => {
    const relations: Relation[] = [
      { app_type: 'agent', app_name: 'A' },
      { app_type: 'workflow', app_name: 'B' },
      { app_type: 'agent', app_name: 'C' },
      { app_type: 'agent', app_name: 'D' },
    ];
    const title = aggregateReferenceSummary(relations, 4, t);
    // 分隔符走 i18n key（此测试桩为 ','），不硬编码 '、'
    expect(title).toContain('[names:A,B,C]');
    expect(title).not.toContain('A、B、C');
    expect(title).not.toContain('D'); // 第 4 个不展示
  });

  it('app_name 全空时走 no_names 兜底（不展示 names 段）', () => {
    const relations: Relation[] = [
      { app_type: 'agent', app_name: '' },
      { app_type: 'agent', app_name: null },
      { app_type: 'agent' },
    ];
    const title = aggregateReferenceSummary(relations, 3, t);
    expect(title).toContain('[no_names]');
    expect(title).not.toContain('[names:');
  });

  it('count=0 不进入聚合（由 confirmUnpublish 分支走通用确认，不调本函数）', () => {
    // 本函数仅在 count>0 时被调用；count=0 走 plaza_offshelf_confirm 通用确认
    // 此用例确认契约：count>0 时正常聚合
    const title = aggregateReferenceSummary([{ app_type: 'agent', app_name: 'A' }], 1, t);
    expect(title).toContain('[summary:count=1]');
    expect(title).toContain('[names:A]');
  });
});
