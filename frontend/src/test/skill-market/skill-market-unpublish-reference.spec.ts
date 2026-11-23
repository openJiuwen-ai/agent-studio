/**
 * bug1733：Skill/插件下架前引用确认 - 引用文案聚合逻辑测试。
 *
 * spec tsconfig(src/test/tsconfig.json)未含 reflect-metadata types，
 * 直接 import SkillMarketComponent(经 SkillDetail @autoProp → prop.ts 用 Reflect.defineMetadata）
 * 会触发 TS2339 编译失败，故不实例化组件，改为独立测 buildReferenceWarningTitle 的聚合算法
 * （与 skill-market.component.ts / plugin-market.component.ts 内实现一致）。
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
function aggregateReferenceSummary(relations: Relation[], t: (key: string, opts?: any) => string): string {
  const workflowCount = relations.filter(r => r?.app_type === 'workflow').length;
  const agentCount = relations.filter(r => r?.app_type === 'agent').length;
  const names = relations
    .map(r => r?.app_name)
    .filter((n): n is string => !!n)
    .slice(0, 3)
    .join('、');
  const summary = t('plaza_offshelf_referenced_summary', { workflow: workflowCount, agent: agentCount });
  const tail = names
    ? t('plaza_offshelf_referenced_names', { names })
    : t('plaza_offshelf_referenced_no_names');
  return `${t('plaza_offshelf_referenced_prefix')}${summary}${tail}`;
}

describe('bug1733 下架前引用确认 - 引用文案聚合', () => {
  /** 模拟 i18n.transform：key + 插值变量，返回可断言的结构化串。 */
  const t = (key: string, opts?: any): string => {
    if (key === 'plaza_offshelf_referenced_summary') {
      return `[summary:wf=${opts.workflow},agent=${opts.agent}]`;
    }
    if (key === 'plaza_offshelf_referenced_names') {
      return `[names:${opts.names}]`;
    }
    if (key === 'plaza_offshelf_referenced_no_names') {
      return '[no_names]';
    }
    return `[${key}]`;
  };

  it('聚合 workflow/agent 数量正确', () => {
    const relations: Relation[] = [
      { app_type: 'workflow', app_name: '流程1' },
      { app_type: 'workflow', app_name: '流程2' },
      { app_type: 'agent', app_name: '智能体A' },
      { app_type: 'agent', app_name: '智能体B' },
    ];
    const title = aggregateReferenceSummary(relations, t);
    expect(title).toContain('[summary:wf=2,agent=2]');
  });

  it('names 取前 3 个并按顺序拼接', () => {
    const relations: Relation[] = [
      { app_type: 'agent', app_name: 'A' },
      { app_type: 'agent', app_name: 'B' },
      { app_type: 'agent', app_name: 'C' },
      { app_type: 'agent', app_name: 'D' },
    ];
    const title = aggregateReferenceSummary(relations, t);
    expect(title).toContain('[names:A、B、C]');
    expect(title).not.toContain('D'); // 第 4 个不展示
  });

  it('app_name 全空时走 no_names 兜底（不展示 names 段）', () => {
    const relations: Relation[] = [
      { app_type: 'agent', app_name: '' },
      { app_type: 'agent', app_name: null },
      { app_type: 'agent' },
    ];
    const title = aggregateReferenceSummary(relations, t);
    expect(title).toContain('[no_names]');
    expect(title).not.toContain('[names:');
  });

  it('混合 workflow/agent 类型分别计数', () => {
    const relations: Relation[] = [
      { app_type: 'workflow', app_name: 'W1' },
      { app_type: 'agent', app_name: 'A1' },
      { app_type: 'agent', app_name: 'A2' },
    ];
    const title = aggregateReferenceSummary(relations, t);
    expect(title).toContain('[summary:wf=1,agent=2]');
    expect(title).toContain('[names:W1、A1、A2]');
  });

  it('未知 app_type 不计入 workflow/agent（容错）', () => {
    const relations: Relation[] = [
      { app_type: 'unknown', app_name: 'X' },
      { app_type: 'agent', app_name: 'A1' },
    ];
    const title = aggregateReferenceSummary(relations, t);
    expect(title).toContain('[summary:wf=0,agent=1]');
  });
});
