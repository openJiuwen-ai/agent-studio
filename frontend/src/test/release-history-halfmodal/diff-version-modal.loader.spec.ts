import { ElementRef } from '@angular/core';
import { DiffVersionModalComponent } from '../../shared/components/release-history-halfmodal/diff-version-modal/diff-version-modal.component';

// Unit 2 spec：类型分派取数 + 边界兜底 + 不吞错。
// 用 mock 服务直接 new 组件实例，绕开 Angular 生命周期，聚焦数据层。

describe('DiffVersionModal Unit 2 — 类型分派/取数/边界', () => {
  let agentRepo: any;
  let flowRepo: any;
  let comp: DiffVersionModalComponent;

  beforeEach(() => {
    agentRepo = jasmine.createSpyObj('AppAgentRepoService', [
      'rollbackFlowVersion',
      'rollbackAgentVersion',
      'getMultiAgent',
      'fetchAgentDetail',
    ]);
    flowRepo = jasmine.createSpyObj('AppFlowRepoService', ['getFlow']);
    const i18n: any = { transform: (k: string) => k };
    const cdr: any = { detectChanges: () => {} };
    const ngZone: any = { run: (fn: Function) => fn() };
    comp = new DiffVersionModalComponent(agentRepo, flowRepo, i18n, cdr, ngZone, new ElementRef(document.createElement('div')));
  });

  describe('projectDsl (纯函数投影)', () => {
    it('workflow → 取 workflow_details', () => {
      expect((comp as any).projectDsl('workflow', { workflow_details: { a: 1 } })).toEqual({ a: 1 });
    });

    it('multi → 取 details', () => {
      expect((comp as any).projectDsl('multi', { details: { b: 2 } })).toEqual({ b: 2 });
    });

    it('agent common → 投影（删元数据黑名单 + 归一 sub_type）', () => {
      const dsl = (comp as any).projectDsl('agent', {
        sub_type: 'common', name: 'x', agent_id: 'a1', create_time: '2026-08-10',
      });
      expect(dsl.name).toBe('x');
      expect(dsl.sub_type).toBe('common');
      expect(dsl.agent_id).toBeUndefined();
      expect(dsl.create_time).toBeUndefined();
    });

    it('agent deepresearch → 抛"暂不支持"', () => {
      expect(() => (comp as any).projectDsl('agent', { sub_type: 'deepresearch' })).toThrowError(/暂不支持/);
    });

    it('agent 未知 sub_type → 抛"不支持的智能体子类型"', () => {
      expect(() => (comp as any).projectDsl('agent', { sub_type: 'foo' })).toThrowError(/不支持的智能体子类型|unsupported/i);
    });

    it('workflow 字段缺失 → 抛错(不返 {})', () => {
      expect(() => (comp as any).projectDsl('workflow', {})).toThrow();
      expect(() => (comp as any).projectDsl('workflow', { workflow_details: null })).toThrow();
    });

    it('multi 字段缺失 → 抛错(不返 {})', () => {
      expect(() => (comp as any).projectDsl('multi', {})).toThrow();
      expect(() => (comp as any).projectDsl('multi', { details: undefined })).toThrow();
    });
  });

  describe('loadVersion (类型分派取数)', () => {
    it('workflow latest → 调 getFlow(app_id)', async () => {
      flowRepo.getFlow.and.returnValue(Promise.resolve({ workflow_details: { x: 1 } }));
      const dsl = await (comp as any).loadVersion('workflow', 'app1', 'latest');
      expect(flowRepo.getFlow).toHaveBeenCalledWith('app1');
      expect(agentRepo.rollbackFlowVersion).not.toHaveBeenCalled();
      expect(dsl).toEqual({ x: 1 });
    });

    it('workflow 版本 → 调 rollbackFlowVersion(app_id, versionId)', async () => {
      agentRepo.rollbackFlowVersion.and.returnValue(Promise.resolve({ workflow_details: { y: 2 } }));
      const dsl = await (comp as any).loadVersion('workflow', 'app1', 'v9');
      expect(agentRepo.rollbackFlowVersion).toHaveBeenCalledWith('app1', 'v9');
      expect(dsl).toEqual({ y: 2 });
    });

    it('multi latest → 调 getMultiAgent(app_id)', async () => {
      agentRepo.getMultiAgent.and.returnValue(Promise.resolve({ details: { m: 1 } }));
      const dsl = await (comp as any).loadVersion('multi', 'app1', 'latest');
      expect(agentRepo.getMultiAgent).toHaveBeenCalledWith('app1');
      expect(agentRepo.rollbackAgentVersion).not.toHaveBeenCalled();
      expect(dsl).toEqual({ m: 1 });
    });

    it('multi 版本 → 调 rollbackAgentVersion(app_id, versionId)', async () => {
      agentRepo.rollbackAgentVersion.and.returnValue(Promise.resolve({ details: { n: 2 } }));
      const dsl = await (comp as any).loadVersion('multi', 'app1', 'v7');
      expect(agentRepo.rollbackAgentVersion).toHaveBeenCalledWith('app1', 'v7');
      expect(dsl).toEqual({ n: 2 });
    });

    it('agent latest → 调 fetchAgentDetail(app_id) 且投影删元数据', async () => {
      agentRepo.fetchAgentDetail.and.returnValue(
        Promise.resolve({ sub_type: 'common', name: 'x', agent_id: 'a1', create_time: '2026-08-10' }),
      );
      const dsl = await (comp as any).loadVersion('agent', 'app1', 'latest');
      expect(agentRepo.fetchAgentDetail).toHaveBeenCalledWith('app1');
      expect(agentRepo.getMultiAgent).not.toHaveBeenCalled();
      expect(dsl.name).toBe('x');
      expect(dsl.agent_id).toBeUndefined();
      expect(dsl.create_time).toBeUndefined();
    });

    it('agent 版本 → 调 rollbackAgentVersion(app_id, versionId)', async () => {
      agentRepo.rollbackAgentVersion.and.returnValue(
        Promise.resolve({ sub_type: 'planexecute', name: 'y', scenes: [{ id: 's1' }] }),
      );
      const dsl = await (comp as any).loadVersion('agent', 'app1', 'v3');
      expect(agentRepo.rollbackAgentVersion).toHaveBeenCalledWith('app1', 'v3');
      expect(dsl.sub_type).toBe('planexecute');
      expect(dsl.scenes).toEqual([{ id: 's1' }]);
    });

    it('agent deepresearch → 抛"暂不支持"（projectDsl 阶段拒绝）', async () => {
      agentRepo.fetchAgentDetail.and.returnValue(Promise.resolve({ sub_type: 'deepresearch' }));
      await expectAsync((comp as any).loadVersion('agent', 'app1', 'latest')).toBeRejectedWithError(/暂不支持/);
    });

    it('workflow 版本端返回无 workflow_details → 抛错(不返 {})', async () => {
      agentRepo.rollbackFlowVersion.and.returnValue(Promise.resolve({}));
      await expectAsync((comp as any).loadVersion('workflow', 'app1', 'v1')).toBeRejected();
    });
  });

  describe('resolveSelectedId 边界兜底', () => {
    const opts = [
      { id: 'latest', label: 'cur' },
      { id: 'v1', label: 'V1' },
      { id: 'v2', label: 'V2' },
    ];
    it('index 超长 → 回退 latest', () => {
      expect((comp as any).resolveSelectedId(opts, 999)).toBe('latest');
    });
    it('index -1（草稿/当前）→ latest', () => {
      expect((comp as any).resolveSelectedId(opts, -1)).toBe('latest');
    });
    it('有效 index → 对应版本 id', () => {
      expect((comp as any).resolveSelectedId(opts, 0)).toBe('v1');
      expect((comp as any).resolveSelectedId(opts, 1)).toBe('v2');
    });
    it('空 options → latest', () => {
      expect((comp as any).resolveSelectedId([], 0)).toBe('latest');
    });
  });

  describe('失败态/同版本辅助', () => {
    it('isSameVersion：左右同 id 为 true', () => {
      comp.leftSelectedId = 'v1';
      comp.rightSelectedId = 'v1';
      expect(comp.isSameVersion).toBe(true);
      comp.rightSelectedId = 'v2';
      expect(comp.isSameVersion).toBe(false);
    });

    it('hasError：任一侧 error 即 true', () => {
      expect(comp.hasError).toBe(false);
      (comp as any).originalState.error = new Error('x');
      expect(comp.hasError).toBe(true);
      (comp as any).originalState.error = null;
      (comp as any).modifiedState.error = new Error('y');
      expect(comp.hasError).toBe(true);
    });

    it('displayedVersionLabel：按 lastSuccessfulVersionId 解析 label', () => {
      comp.leftOptions = [
        { id: 'latest', label: '当前' },
        { id: 'v1', label: 'V1' },
      ];
      (comp as any).originalState.lastSuccessfulVersionId = 'v1';
      expect((comp as any).displayedVersionLabel('original')).toBe('V1');
    });

    it('displayedVersionLabel：无成功版本 → 空串', () => {
      (comp as any).originalState.lastSuccessfulVersionId = null;
      expect((comp as any).displayedVersionLabel('original')).toBe('');
    });
  });
});
