// 阶段三 3A spec：单智能体投影（extractSingleAgentDsl）。
// 策略：元数据黑名单 —— 整对象 − 元数据，业务字段自动纳入。
// 覆盖：黑名单删除、业务保留、sub_type 归一/准入、不修改原 response、两侧同构、序列化。
// 字段固化表：工作记录/20260810/2026-08-10-001-阶段三单智能体投影字段固化表.md

import {
  extractSingleAgentDsl,
  serializeSingleAgentDslForDiff,
} from '../../shared/components/release-history-halfmodal/diff-version-modal/single-agent-dsl-for-diff';
import commonDraft from './fixtures/agent-common-draft.json';
import commonVersion from './fixtures/agent-common-version.json';
import planexecuteDraft from './fixtures/agent-planexecute-draft.json';
import planexecuteVersion from './fixtures/agent-planexecute-version.json';

describe('extractSingleAgentDsl (阶段三 3A 单智能体投影)', () => {
  // 完整 AgentInfo：含全部元数据黑名单字段 + 代表性业务字段
  const baseAgent: Record<string, unknown> = {
    // —— 元数据黑名单（应被删除）——
    agent_id: 'a-1',
    project_id: 'p-1',
    workspace_id: 'w-1',
    tags: ['t1'],
    creator: '张三',
    creator_id: 'u-1',
    create_time: '2026-08-01 10:00:00',
    update_time: '2026-08-10 10:00:00',
    publish_time: '2026-08-05 10:00:00',
    url: 'http://x/a-1',
    status: 'PUBLISHED',
    is_template: false,
    is_share: 0,
    channel_type: ['web'],
    free_trial_quota: { quota: 100 },
    character_dr: 1,
    updated_on: '2026-08-09',
    // —— 业务字段（应保留）——
    name: '测试智能体',
    type: 'agent',
    sub_type: 'common',
    description: '一个测试智能体',
    icon: 'icon-key',
    instructions: '你是助手',
    prologue: '你好',
    suggest_queries: ['q1', 'q2'],
    model: 'glm-5',
    model_config: { temperature: 0.7 },
    tools: [{ tool_id: 't1' }],
    workflows: [{ workflow_id: 'w1' }],
    memory_variables: [{ name: 'm1' }],
    trigger_list: [{ trigger_id: 'tr1' }],
    agent_variables: [],
    input_variables: [],
    knowledge_repos: [],
  };

  describe('黑名单删除', () => {
    it('全部元数据黑名单字段被删除', () => {
      const dsl = extractSingleAgentDsl(baseAgent);
      const removed = [
        'agent_id', 'project_id', 'workspace_id', 'tags', 'creator', 'creator_id',
        'create_time', 'update_time', 'publish_time', 'url', 'status', 'is_template',
        'is_share', 'channel_type', 'free_trial_quota', 'character_dr', 'updated_on',
      ];
      for (const key of removed) {
        expect((dsl as Record<string, unknown>)[key]).withContext(`字段 ${key} 应被删除`).toBeUndefined();
      }
    });

    it('浅拷贝：不修改原 response（原对象元数据仍在）', () => {
      const input: Record<string, unknown> = { ...baseAgent };
      extractSingleAgentDsl(input);
      expect(input.agent_id).toBe('a-1');
      expect(input.create_time).toBe('2026-08-01 10:00:00');
      expect(input.creator).toBe('张三');
    });
  });

  describe('业务字段保留', () => {
    it('基础/提示/模型/能力/记忆/触发字段保留', () => {
      const dsl = extractSingleAgentDsl(baseAgent) as Record<string, unknown>;
      expect(dsl.name).toBe('测试智能体');
      expect(dsl.sub_type).toBe('common');
      expect(dsl.instructions).toBe('你是助手');
      expect(dsl.prologue).toBe('你好');
      expect(dsl.suggest_queries).toEqual(['q1', 'q2']);
      expect(dsl.model).toBe('glm-5');
      expect(dsl.model_config).toEqual({ temperature: 0.7 });
      expect(dsl.tools).toEqual([{ tool_id: 't1' }]);
      expect(dsl.workflows).toEqual([{ workflow_id: 'w1' }]);
      expect(dsl.memory_variables).toEqual([{ name: 'm1' }]);
      expect(dsl.trigger_list).toEqual([{ trigger_id: 'tr1' }]);
    });

    it('details 非空时保留（自动纳入，不属元数据）', () => {
      const dsl = extractSingleAgentDsl({ ...baseAgent, details: { nodes: [] } }) as Record<string, unknown>;
      expect(dsl.details).toEqual({ nodes: [] });
    });

    it('planexecute 专属字段保留', () => {
      const dsl = extractSingleAgentDsl({
        ...baseAgent,
        sub_type: 'planexecute',
        planning: { mode: 'auto' },
        scenes: [{ id: 's1' }],
        plan_model: 'glm-plan',
        plan_model_config: { temperature: 0.3 },
      }) as Record<string, unknown>;
      expect(dsl.sub_type).toBe('planexecute');
      expect(dsl.planning).toEqual({ mode: 'auto' });
      expect(dsl.scenes).toEqual([{ id: 's1' }]);
      expect(dsl.plan_model).toBe('glm-plan');
      expect(dsl.plan_model_config).toEqual({ temperature: 0.3 });
    });
  });

  describe('sub_type 归一与准入', () => {
    it('sub_type=null 归一为 common，不抛错', () => {
      const dsl = extractSingleAgentDsl({ ...baseAgent, sub_type: null }) as Record<string, unknown>;
      expect(dsl.sub_type).toBe('common');
    });

    it('sub_type="" 归一为 common（空字符串，5.5 修复）', () => {
      const dsl = extractSingleAgentDsl({ ...baseAgent, sub_type: '' }) as Record<string, unknown>;
      expect(dsl.sub_type).toBe('common');
    });

    it('sub_type="  " 归一为 common（仅空白，5.5 修复）', () => {
      const dsl = extractSingleAgentDsl({ ...baseAgent, sub_type: '  ' }) as Record<string, unknown>;
      expect(dsl.sub_type).toBe('common');
    });

    it('sub_type="agent" 归一为 common（历史数据兼容）', () => {
      const dsl = extractSingleAgentDsl({ ...baseAgent, sub_type: 'agent' }) as Record<string, unknown>;
      expect(dsl.sub_type).toBe('common');
    });

    it('sub_type=common 允许', () => {
      expect(() => extractSingleAgentDsl({ ...baseAgent, sub_type: 'common' })).not.toThrow();
    });

    it('sub_type=planexecute 允许', () => {
      expect(() => extractSingleAgentDsl({ ...baseAgent, sub_type: 'planexecute' })).not.toThrow();
    });

    it('sub_type=deepresearch 抛"暂不支持"', () => {
      expect(() => extractSingleAgentDsl({ ...baseAgent, sub_type: 'deepresearch' }))
        .toThrowError(/暂不支持/);
    });

    it('未知 sub_type 抛"不支持的智能体子类型"', () => {
      expect(() => extractSingleAgentDsl({ ...baseAgent, sub_type: 'foo' }))
        .toThrowError(/不支持的智能体子类型/);
    });
  });

  describe('空响应与两侧同构', () => {
    it('response 为 null/undefined 抛错', () => {
      expect(() => extractSingleAgentDsl(null)).toThrow();
      expect(() => extractSingleAgentDsl(undefined)).toThrow();
    });

    it('latest 与 version 两侧相同输入投影一致（共用同一投影器）', () => {
      const latest = extractSingleAgentDsl(baseAgent);
      const version = extractSingleAgentDsl(baseAgent);
      expect(version).toEqual(latest);
    });
  });

  describe('开发期未知字段告警', () => {
    it('未知字段触发 console.warn 并提示确认归属', () => {
      const warnSpy = spyOn(console, 'warn');
      extractSingleAgentDsl({ ...baseAgent, new_unknown_field: 'x' });
      expect(warnSpy).toHaveBeenCalled();
      expect(warnSpy.calls.mostRecent().args[0]).toContain('new_unknown_field');
    });

    it('已知业务字段不触发告警', () => {
      const warnSpy = spyOn(console, 'warn');
      extractSingleAgentDsl(baseAgent);
      expect(warnSpy).not.toHaveBeenCalled();
    });
  });

  describe('serializeSingleAgentDslForDiff', () => {
    it('返回美化 JSON：业务在、元数据不在', () => {
      const text = serializeSingleAgentDslForDiff(baseAgent);
      expect(text).toContain('测试智能体');
      expect(text).toContain('你是助手');
      expect(text).not.toContain('agent_id');
      expect(text).not.toContain('张三');
      expect(text).not.toContain('PUBLISHED');
      // 美化缩进
      expect(text.includes('\n  ')).toBe(true);
    });
  });

  describe('DSL 演进健壮性（后端增/删/改字段不破坏对比，看护用）', () => {
    it('后端新增业务字段：两侧都有 → 进 Diff、不抛、差异体现', () => {
      const a = { ...baseAgent, new_business_field: 'v1' };
      const b = { ...baseAgent, new_business_field: 'v2' };
      const ta = serializeSingleAgentDslForDiff(a);
      const tb = serializeSingleAgentDslForDiff(b);
      expect(ta).toContain('new_business_field');
      expect(ta).not.toBe(tb);
    });

    it('后端删除业务字段：一侧有一侧无 → 不抛、Diff 反映', () => {
      const a: Record<string, unknown> = { ...baseAgent, custom_field: 'x' };
      const b: Record<string, unknown> = { ...baseAgent };
      expect(() => serializeSingleAgentDslForDiff(a)).not.toThrow();
      expect(() => serializeSingleAgentDslForDiff(b)).not.toThrow();
      expect(serializeSingleAgentDslForDiff(a)).not.toBe(serializeSingleAgentDslForDiff(b));
    });

    it('后端改 key：旧 key 消失、新 key 出现 → 不抛、Diff 反映', () => {
      const a = { ...baseAgent, old_key: 'v' };
      const b = { ...baseAgent, new_key: 'v' };
      expect(() => serializeSingleAgentDslForDiff(a)).not.toThrow();
      const ta = serializeSingleAgentDslForDiff(a);
      const tb = serializeSingleAgentDslForDiff(b);
      expect(ta).toContain('old_key');
      expect(tb).toContain('new_key');
      expect(ta).not.toBe(tb);
    });

    it('后端新增元数据字段（未加黑名单）：自动进 Diff、不抛、合法 JSON（黑名单策略保证不漏差异）', () => {
      const a = { ...baseAgent, new_meta_field: 'meta' };
      const ta = serializeSingleAgentDslForDiff(a);
      expect(ta).toContain('new_meta_field');
      expect(() => JSON.parse(ta)).not.toThrow();
    });

    it('两侧字段集不同（版本演进）：serialize 各自合法 JSON、不抛、Diff 仍工作', () => {
      const draft: Record<string, unknown> = { ...baseAgent, draft_only: 1 };
      const version: Record<string, unknown> = { ...baseAgent, version_only: 2 };
      const ta = serializeSingleAgentDslForDiff(draft);
      const tb = serializeSingleAgentDslForDiff(version);
      expect(() => JSON.parse(ta)).not.toThrow();
      expect(() => JSON.parse(tb)).not.toThrow();
      expect(ta).not.toBe(tb);
    });

    it('任意嵌套结构：serialize 始终合法 JSON、不抛', () => {
      const weird = { ...baseAgent, nested: { a: { b: [1, 2, { c: null }] } } };
      const text = serializeSingleAgentDslForDiff(weird);
      expect(() => JSON.parse(text)).not.toThrow();
    });
  });
});

describe('真实 fixture 投影（common/planexecute 草稿+版本，5.6 接入）', () => {
  it('common 草稿：元数据删、业务保留、sub_type=common', () => {
    const dsl = extractSingleAgentDsl(commonDraft) as Record<string, unknown>;
    expect(dsl.agent_id).toBeUndefined();
    expect(dsl.create_time).toBeUndefined();
    expect(dsl.creator).toBeUndefined();
    expect(dsl.sub_type).toBe('common');
    expect(dsl.name).toBeTruthy();
  });

  it('common 版本：元数据删、sub_type=common', () => {
    const dsl = extractSingleAgentDsl(commonVersion) as Record<string, unknown>;
    expect(dsl.agent_id).toBeUndefined();
    expect(dsl.creator).toBeUndefined();
    expect(dsl.sub_type).toBe('common');
  });

  it('planexecute 草稿：sub_type=planexecute、scenes 保留、元数据删', () => {
    const dsl = extractSingleAgentDsl(planexecuteDraft) as Record<string, unknown>;
    expect(dsl.sub_type).toBe('planexecute');
    expect(dsl.scenes).toBeDefined();
    expect(dsl.agent_id).toBeUndefined();
  });

  it('planexecute 版本：sub_type=planexecute、scenes 保留', () => {
    const dsl = extractSingleAgentDsl(planexecuteVersion) as Record<string, unknown>;
    expect(dsl.sub_type).toBe('planexecute');
    expect(dsl.scenes).toBeDefined();
  });

  it('planexecute 草稿 vs 版本：serialize 输出不同（验证 Diff 能力）', () => {
    expect(serializeSingleAgentDslForDiff(planexecuteDraft)).not.toBe(
      serializeSingleAgentDslForDiff(planexecuteVersion),
    );
  });
});
