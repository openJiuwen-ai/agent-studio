import { DiffVersionModalComponent } from '../../shared/components/release-history-halfmodal/diff-version-modal/diff-version-modal.component';

// Unit 4 spec：每侧异步治理 + commitIfCurrent + per-side tooLarge + 移除 Mask。
// 用 deferred 控制 promise 顺序，mock 服务，不真加载 Monaco。

function deferred<T = any>() {
  let resolve!: (v: T) => void;
  let reject!: (e: any) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function mockModel(initial: string) {
  const m = jasmine.createSpyObj('ITextModel', ['getValue', 'setValue', 'dispose']);
  m.getValue.and.returnValue(initial);
  return m;
}

function mockEditor(original: any, modified: any) {
  const disposable = jasmine.createSpyObj('IDisposable', ['dispose']);
  const editor = jasmine.createSpyObj(
    'IStandaloneDiffEditor',
    ['getModel', 'onDidUpdateDiff', 'getLineChanges', 'setModel', 'isDisposed', 'dispose'],
  );
  editor.getModel.and.returnValue({ original, modified });
  editor.onDidUpdateDiff.and.returnValue(disposable);
  editor.getLineChanges.and.returnValue([]);
  editor.isDisposed.and.returnValue(false);
  return editor;
}

describe('DiffVersionModal Unit 4 — 每侧异步治理 + commitIfCurrent + per-side tooLarge', () => {
  let comp: DiffVersionModalComponent;
  let agentRepo: any;
  let flowRepo: any;
  let originalModel: any;
  let modifiedModel: any;

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
    comp = new DiffVersionModalComponent(agentRepo, flowRepo, i18n, cdr, ngZone);
    comp.type = 'workflow';
    comp.app_id = 'app1';
    // 大阈值：正常测试不触发 tooLarge；tooLarge 专项测试自行调小
    (comp as any).largeDslBytesThreshold = 10 * 1024 * 1024;
    originalModel = mockModel('');
    modifiedModel = mockModel('');
    // 接通 editor（applyValues 需 model 引用）
    (comp as any).onDiffInit(mockEditor(originalModel, modifiedModel));
  });

  it('成功：写入 value/sourceText/lastSuccessfulVersionId，loading 结束', async () => {
    flowRepo.getFlow.and.returnValue(Promise.resolve({ workflow_details: { v: 'A' } }));
    comp.leftSelectedId = 'latest';
    await (comp as any).loadSide('original', 'latest');
    expect(comp.originalValue).toContain('"v": "A"');
    expect((comp as any).originalState.loading).toBe(false);
    expect((comp as any).originalState.lastSuccessfulVersionId).toBe('latest');
    expect((comp as any).originalState.sourceText).toContain('"v": "A"');
    expect((comp as any).originalState.error).toBeNull();
  });

  it('A 后 B：B 胜出，A 旧响应不覆盖（commitIfCurrent）', async () => {
    const dA = deferred();
    const dB = deferred();
    agentRepo.rollbackFlowVersion.and.callFake((_id: string, v: string) => (v === 'v1' ? dA.promise : dB.promise));
    comp.leftSelectedId = 'v1';
    const pA = (comp as any).loadSide('original', 'v1');
    comp.leftSelectedId = 'v2';
    const pB = (comp as any).loadSide('original', 'v2');
    // B 先返回
    dB.resolve({ workflow_details: { v: 'B' } });
    await pB;
    expect(comp.originalValue).toContain('"v": "B"');
    // A 后返回，不得覆盖
    dA.resolve({ workflow_details: { v: 'A' } });
    await pA;
    expect(comp.originalValue).toContain('"v": "B"');
  });

  it('失败：error 置位、保留上次成功 value、loading 结束', async () => {
    flowRepo.getFlow.and.returnValues(
      Promise.resolve({ workflow_details: { v: 'OK' } }),
      Promise.reject(new Error('boom')),
    );
    comp.leftSelectedId = 'latest';
    await (comp as any).loadSide('original', 'latest'); // 成功
    expect(comp.originalValue).toContain('"v": "OK"');
    await (comp as any).loadSide('original', 'latest'); // 失败
    expect((comp as any).originalState.error).toBeTruthy();
    expect((comp as any).originalState.loading).toBe(false);
    expect(comp.originalValue).toContain('"v": "OK"'); // 保留上次成功
  });

  it('过期请求 finally 不能关新请求 loading（commitIfCurrent 守卫 finally）', async () => {
    const dA = deferred();
    const dB = deferred();
    agentRepo.rollbackFlowVersion.and.callFake((_id: string, v: string) => (v === 'v1' ? dA.promise : dB.promise));
    comp.leftSelectedId = 'v1';
    const pA = (comp as any).loadSide('original', 'v1');
    comp.leftSelectedId = 'v2';
    const pB = (comp as any).loadSide('original', 'v2');
    // A 完成（过期）→ 不应关 B 的 loading
    dA.resolve({ workflow_details: { v: 'A' } });
    await pA;
    expect((comp as any).originalState.loading).toBe(true); // B 仍在加载
    dB.resolve({ workflow_details: { v: 'B' } });
    await pB;
    expect((comp as any).originalState.loading).toBe(false);
  });

  it('大 DSL：tooLarge=true、value 不写（保留旧）、sourceText 存大文本、dslTooLarge 派生', async () => {
    // 先成功一个小值（13 字节 < 阈值）
    flowRepo.getFlow.and.returnValues(
      Promise.resolve({ workflow_details: { small: 1 } }),
      Promise.resolve({ workflow_details: { big: 'x'.repeat(200) } }), // JSON ~220 字节 > 阈值
    );
    (comp as any).largeDslBytesThreshold = 100;
    comp.leftSelectedId = 'latest';
    await (comp as any).loadSide('original', 'latest');
    const smallValue = comp.originalValue;
    expect(smallValue).toContain('small');
    // 再加载大 DSL
    await (comp as any).loadSide('original', 'latest');
    expect((comp as any).originalState.tooLarge).toBe(true);
    expect(comp.originalValue).toBe(smallValue); // 保留旧 value，不写大文本
    expect((comp as any).originalState.sourceText).toContain('big');
    expect((comp as any).dslTooLarge).toBe(true);
  });

  it('大→小切换：tooLarge 重置、value 恢复写入', async () => {
    flowRepo.getFlow.and.returnValues(
      Promise.resolve({ workflow_details: { big: 'x'.repeat(200) } }),
      Promise.resolve({ workflow_details: { small: 1 } }),
    );
    (comp as any).largeDslBytesThreshold = 100;
    comp.leftSelectedId = 'latest';
    await (comp as any).loadSide('original', 'latest');
    expect((comp as any).originalState.tooLarge).toBe(true);
    await (comp as any).loadSide('original', 'latest');
    expect((comp as any).originalState.tooLarge).toBe(false);
    expect(comp.originalValue).toContain('small');
    expect((comp as any).dslTooLarge).toBe(false);
  });

  it('左右侧独立：左 loading 不影响右', async () => {
    const dLeft = deferred();
    flowRepo.getFlow.and.returnValue(dLeft.promise);
    agentRepo.rollbackFlowVersion.and.returnValue(Promise.resolve({ workflow_details: { r: 1 } }));
    comp.leftSelectedId = 'latest';
    comp.rightSelectedId = 'vR';
    const pLeft = (comp as any).loadSide('original', 'latest');
    const pRight = (comp as any).loadSide('modified', 'vR');
    expect((comp as any).originalState.loading).toBe(true);
    await pRight;
    expect((comp as any).modifiedState.loading).toBe(false);
    expect((comp as any).originalState.loading).toBe(true); // 左仍加载
    dLeft.resolve({ workflow_details: { l: 1 } });
    await pLeft;
    expect((comp as any).originalState.loading).toBe(false);
  });

  it('agent：loadSide → error "不支持"且不发网络请求', async () => {
    comp.type = 'agent';
    comp.leftSelectedId = 'latest';
    await (comp as any).loadSide('original', 'latest');
    expect((comp as any).originalState.error).toBeTruthy();
    expect(flowRepo.getFlow).not.toHaveBeenCalled();
    expect(agentRepo.getMultiAgent).not.toHaveBeenCalled();
    expect((comp as any).originalState.loading).toBe(false);
  });

  it('destroyed 后晚到响应：不改 value、不抛', async () => {
    const d = deferred();
    flowRepo.getFlow.and.returnValue(d.promise);
    comp.leftSelectedId = 'latest';
    const p = (comp as any).loadSide('original', 'latest');
    (comp as any).ngOnDestroy();
    d.resolve({ workflow_details: { v: 'LATE' } });
    await expectAsync(p).toBeResolved();
    expect(comp.originalValue).not.toContain('LATE');
  });

  // —— 4.1 并发过期组合：过期大 DSL 响应不得污染当前请求的 tooLarge ——
  it('A 大、B 小，A 过期先返回：最终显示 B，不出现超限遮罩', async () => {
    const dA = deferred();
    const dB = deferred();
    agentRepo.rollbackFlowVersion.and.callFake((_id: string, v: string) => (v === 'v1' ? dA.promise : dB.promise));
    (comp as any).largeDslBytesThreshold = 100;
    comp.leftSelectedId = 'v1';
    const pA = (comp as any).loadSide('original', 'v1'); // A 大
    comp.leftSelectedId = 'v2';
    const pB = (comp as any).loadSide('original', 'v2'); // B 小
    // A（大、过期）先返回
    dA.resolve({ workflow_details: { big: 'x'.repeat(200) } });
    await pA;
    // B（小、当前）后返回
    dB.resolve({ workflow_details: { small: 1 } });
    await pB;
    expect((comp as any).originalState.tooLarge).toBe(false);
    expect((comp as any).dslTooLarge).toBe(false);
    expect(comp.originalValue).toContain('small');
  });

  it('B 小先成功、过期大 A 后返回：A 不得把 B 的 tooLarge 重新打开', async () => {
    const dA = deferred();
    const dB = deferred();
    agentRepo.rollbackFlowVersion.and.callFake((_id: string, v: string) => (v === 'v1' ? dA.promise : dB.promise));
    (comp as any).largeDslBytesThreshold = 100;
    comp.leftSelectedId = 'v1';
    const pA = (comp as any).loadSide('original', 'v1'); // A 大
    comp.leftSelectedId = 'v2';
    const pB = (comp as any).loadSide('original', 'v2'); // B 小
    dB.resolve({ workflow_details: { small: 1 } });
    await pB;
    expect((comp as any).originalState.tooLarge).toBe(false);
    expect(comp.originalValue).toContain('small');
    dA.resolve({ workflow_details: { big: 'x'.repeat(200) } });
    await pA;
    // 过期大 A 返回后，B 的状态不被污染
    expect((comp as any).originalState.tooLarge).toBe(false);
    expect((comp as any).dslTooLarge).toBe(false);
    expect(comp.originalValue).toContain('small');
  });

  it('A 小、B 大：最终只反映 B 的超限状态', async () => {
    const dA = deferred();
    const dB = deferred();
    agentRepo.rollbackFlowVersion.and.callFake((_id: string, v: string) => (v === 'v1' ? dA.promise : dB.promise));
    (comp as any).largeDslBytesThreshold = 100;
    comp.leftSelectedId = 'v1';
    const pA = (comp as any).loadSide('original', 'v1'); // A 小
    comp.leftSelectedId = 'v2';
    const pB = (comp as any).loadSide('original', 'v2'); // B 大（当前）
    dA.resolve({ workflow_details: { small: 1 } });
    await pA;
    dB.resolve({ workflow_details: { big: 'x'.repeat(200) } });
    await pB;
    expect((comp as any).originalState.tooLarge).toBe(true);
    expect((comp as any).dslTooLarge).toBe(true);
  });
});
