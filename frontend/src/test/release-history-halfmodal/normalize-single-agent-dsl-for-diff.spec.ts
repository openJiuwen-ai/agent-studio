// 阶段三 3B spec：单智能体 DSL 顺序规范化（normalizeSingleAgentDslForDiff）。
// 策略：对象 key 递归稳定 + 数组默认保序。引用集合排序白名单暂空（待业务确认）。
// 覆盖：key 稳定、嵌套 key 稳定、业务数组保序、引用集合当前保序、不修改输入、确定性、serialize 链路。

import {
  normalizeSingleAgentDslForDiff,
  serializeSingleAgentDslForDiff,
} from '../../shared/components/release-history-halfmodal/diff-version-modal/single-agent-dsl-for-diff';

describe('normalizeSingleAgentDslForDiff (阶段三 3B 单智能体排序规范化)', () => {
  describe('对象 key 稳定', () => {
    it('顶层对象 key 换序 → 输出一致', () => {
      const a = { b: 2, a: 1, c: 3 };
      const b = { c: 3, a: 1, b: 2 };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });

    it('嵌套对象 key 换序 → 输出一致', () => {
      const a = { model_config: { temp: 0.7, top_p: 0.9 }, name: 'x' };
      const b = { name: 'x', model_config: { top_p: 0.9, temp: 0.7 } };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });

    it('normalize 后对象 key 已按字母序排列', () => {
      const out = normalizeSingleAgentDslForDiff({ c: 3, a: 1, b: 2 }) as Record<string, unknown>;
      expect(Object.keys(out)).toEqual(['a', 'b', 'c']);
    });
  });

  describe('业务数组保序（不掩盖语义）', () => {
    it('suggest_queries 换序 → 输出不同', () => {
      const a = { suggest_queries: ['q1', 'q2'] };
      const b = { suggest_queries: ['q2', 'q1'] };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).not.toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });

    it('agent_variables 换序 → 输出不同', () => {
      const a = { agent_variables: [{ name: 'v1' }, { name: 'v2' }] };
      const b = { agent_variables: [{ name: 'v2' }, { name: 'v1' }] };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).not.toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });

    it('memory_variables 换序 → 输出不同', () => {
      const a = { memory_variables: [{ name: 'm1' }, { name: 'm2' }] };
      const b = { memory_variables: [{ name: 'm2' }, { name: 'm1' }] };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).not.toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });
  });

  describe('引用集合排序（白名单，按 ID）', () => {
    const cases: Array<{ field: string; id: string }> = [
      { field: 'tools', id: 'tool_id' },
      { field: 'workflows', id: 'workflow_id' },
      { field: 'mcp_servers', id: 'mcp_server_id' },
      { field: 'skills', id: 'skill_id' },
      { field: 'knowledge_repos', id: 'knowledge_repo_id' },
      { field: 'scenes', id: 'id' },
    ];
    for (const c of cases) {
      it(`${c.field} 换序 → 输出一致（按 ${c.id}）`, () => {
        const a = { [c.field]: [{ [c.id]: '1', n: 'x' }, { [c.id]: '2', n: 'y' }] };
        const b = { [c.field]: [{ [c.id]: '2', n: 'y' }, { [c.id]: '1', n: 'x' }] };
        expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).toBe(
          JSON.stringify(normalizeSingleAgentDslForDiff(b)),
        );
      });
    }

    it('缺失 ID 用完整对象 JSON 兜底，不丢元素', () => {
      const a = { tools: [{ tool_id: 't1' }, { name: 'no-id' }] };
      const b = { tools: [{ name: 'no-id' }, { tool_id: 't1' }] };
      const outA = normalizeSingleAgentDslForDiff(a) as { tools: unknown[] };
      const outB = normalizeSingleAgentDslForDiff(b) as { tools: unknown[] };
      expect(outA.tools.length).toBe(2);
      expect(JSON.stringify(outA)).toBe(JSON.stringify(outB));
    });

    it('重复 ID 用完整对象 JSON 兜底，不丢元素、不去重', () => {
      const a = { tools: [{ tool_id: 't1', a: 2 }, { tool_id: 't1', a: 1 }] };
      const out = normalizeSingleAgentDslForDiff(a) as { tools: Array<{ a: number }> };
      expect(out.tools.length).toBe(2);
      expect(out.tools[0].a).toBe(1);
      expect(out.tools[1].a).toBe(2);
    });

    it('嵌套同名白名单字段数组不排序（some_config.tools 保序，5.3 修复）', () => {
      // 仅顶层 path.length===1 的引用集合排序；嵌套同名 tools 不排
      const a = { some_config: { tools: [{ tool_id: 't1' }, { tool_id: 't2' }] } };
      const b = { some_config: { tools: [{ tool_id: 't2' }, { tool_id: 't1' }] } };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).not.toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });

    it('非白名单字段数组保序（other）', () => {
      const a = { other: [{ tool_id: 't1' }, { tool_id: 't2' }] };
      const b = { other: [{ tool_id: 't2' }, { tool_id: 't1' }] };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(a))).not.toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(b)),
      );
    });
  });

  describe('纯函数性', () => {
    it('不修改输入对象', () => {
      const input = { b: 2, a: 1, nested: { y: 2, x: 1 } };
      const snapshot = JSON.stringify(input);
      normalizeSingleAgentDslForDiff(input);
      expect(JSON.stringify(input)).toBe(snapshot);
    });

    it('确定性：相同输入两次 normalize 一致', () => {
      const input = { tools: [{ tool_id: 't1' }], model_config: { temp: 0.7 }, name: 'x' };
      expect(JSON.stringify(normalizeSingleAgentDslForDiff(input))).toBe(
        JSON.stringify(normalizeSingleAgentDslForDiff(input)),
      );
    });
  });

  describe('serialize 链路（投影 → 规范化 → 序列化）', () => {
    it('元数据黑名单生效、key 稳定、业务字段保留', () => {
      const text = serializeSingleAgentDslForDiff({
        sub_type: 'common',
        name: '助手',
        model_config: { temp: 0.7, top_p: 0.9 },
        agent_id: 'a-1',
        create_time: '2026-08-10',
        suggest_queries: ['q1'],
      });
      expect(text).toContain('助手');
      expect(text).toContain('q1');
      expect(text).not.toContain('agent_id');
      expect(text).not.toContain('2026-08-10');
      // normalize 后 key 字母序：model_config < name < sub_type < suggest_queries
      const idxModel = text.indexOf('model_config');
      const idxName = text.indexOf('"name"');
      const idxSub = text.indexOf('sub_type');
      const idxSuggest = text.indexOf('suggest_queries');
      expect(idxModel).toBeGreaterThan(-1);
      expect(idxName).toBeGreaterThan(idxModel);
      expect(idxSub).toBeGreaterThan(idxName);
      expect(idxSuggest).toBeGreaterThan(idxSub);
    });

    it('两侧 key 顺序不同但内容相同 → serialize 输出一致', () => {
      const left = { sub_type: 'common', name: 'x', model: 'glm' };
      const right = { model: 'glm', name: 'x', sub_type: 'common' };
      expect(serializeSingleAgentDslForDiff(left)).toBe(serializeSingleAgentDslForDiff(right));
    });
  });
});
