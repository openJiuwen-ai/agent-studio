import { ElementRef } from '@angular/core';
import { DiffVersionModalComponent } from '../../shared/components/release-history-halfmodal/diff-version-modal/diff-version-modal.component';

// Unit 3 spec：Monaco 单 Model 更新路径 + 资源释放。
// 用 mock editor/model 句柄，不在 Karma 里真加载 Monaco。

function mockDisposable() {
  return jasmine.createSpyObj('IDisposable', ['dispose']);
}

function mockModel(initial: string) {
  const m = jasmine.createSpyObj('ITextModel', ['getValue', 'setValue', 'dispose']);
  m.getValue.and.returnValue(initial);
  return m;
}

function mockEditor(opts: { original: any; modified: any; lineChanges?: any[] | null; disposed?: boolean }) {
  const disposable = mockDisposable();
  const editor = jasmine.createSpyObj(
    'IStandaloneDiffEditor',
    ['getModel', 'onDidUpdateDiff', 'getLineChanges', 'setModel', 'isDisposed', 'dispose'],
  );
  editor.getModel.and.returnValue({ original: opts.original, modified: opts.modified });
  editor.onDidUpdateDiff.and.callFake((cb: Function) => {
    (editor as any).__diffCb = cb;
    return disposable;
  });
  editor.getLineChanges.and.returnValue(opts.lineChanges === undefined ? [] : opts.lineChanges);
  editor.isDisposed.and.returnValue(!!opts.disposed);
  (editor as any).__disposable = disposable;
  return editor;
}

describe('DiffVersionModal Unit 3 — Monaco 单 Model 更新 + 资源释放', () => {
  let comp: DiffVersionModalComponent;
  let originalModel: any;
  let modifiedModel: any;

  beforeEach(() => {
    const agentRepo = jasmine.createSpyObj('AppAgentRepoService', [
      'rollbackFlowVersion',
      'rollbackAgentVersion',
      'getMultiAgent',
      'fetchAgentDetail',
    ]);
    const flowRepo = jasmine.createSpyObj('AppFlowRepoService', ['getFlow']);
    const i18n: any = { transform: (k: string) => k };
    const cdr: any = { detectChanges: () => {} };
    const ngZone: any = { run: (fn: Function) => fn() };
    comp = new DiffVersionModalComponent(agentRepo, flowRepo, i18n, cdr, ngZone, new ElementRef(document.createElement('div')));
    originalModel = mockModel('old-o');
    modifiedModel = mockModel('old-m');
  });

  it('onDiffInit 存 editor/model 引用并初始 applyValues', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).originalValue = 'old-o';
    (comp as any).modifiedValue = 'old-m';
    (comp as any).onDiffInit(editor);
    expect((comp as any).diffEditor).toBe(editor);
    expect((comp as any).originalModel).toBe(originalModel);
    expect((comp as any).modifiedModel).toBe(modifiedModel);
  });

  it('applyValues：original 变、modified 不变 → 只 original.setValue', () => {
    (comp as any).diffEditor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).originalModel = originalModel;
    (comp as any).modifiedModel = modifiedModel;
    originalModel.getValue.and.returnValue('old-o'); // 与现值同
    modifiedModel.getValue.and.returnValue('old-m'); // 与现值同
    (comp as any).originalValue = 'new-o';
    (comp as any).modifiedValue = 'old-m';
    (comp as any).applyValues();
    expect(originalModel.setValue).toHaveBeenCalledWith('new-o');
    expect(modifiedModel.setValue).not.toHaveBeenCalled();
  });

  it('applyValues：两侧与现值相同 → 都不调 setValue（幂等）', () => {
    (comp as any).diffEditor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).originalModel = originalModel;
    (comp as any).modifiedModel = modifiedModel;
    originalModel.getValue.and.returnValue('same');
    modifiedModel.getValue.and.returnValue('same');
    (comp as any).originalValue = 'same';
    (comp as any).modifiedValue = 'same';
    (comp as any).applyValues();
    expect(originalModel.setValue).not.toHaveBeenCalled();
    expect(modifiedModel.setValue).not.toHaveBeenCalled();
  });

  it('applyValues：diffEditor 未就绪 → no-op 不抛', () => {
    (comp as any).diffEditor = undefined;
    expect(() => (comp as any).applyValues()).not.toThrow();
  });

  it('getLineChanges 返回 null → 行统计 0/0 不抛', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel, lineChanges: null });
    (comp as any).originalValue = 'old-o';
    (comp as any).modifiedValue = 'old-m';
    (comp as any).onDiffInit(editor);
    const cb = (editor as any).__diffCb;
    expect(() => cb()).not.toThrow();
    expect(comp.lineAdd).toBe(0);
    expect(comp.lineDel).toBe(0);
  });

  it('onDiffInit：destroyed=true → 直接 return，不存 editor/挂 disposable', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).destroyed = true;
    (comp as any).onDiffInit(editor);
    expect((comp as any).diffEditor).toBeUndefined();
    expect(editor.onDidUpdateDiff).not.toHaveBeenCalled();
  });

  it('ngOnDestroy：释放 disposable + 两 Model + 置空引用；editor 未释放时 setModel(null) 被调', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).onDiffInit(editor);
    const storedDisposable = (editor as any).__disposable;
    (comp as any).ngOnDestroy();
    expect(storedDisposable.dispose).toHaveBeenCalled();
    expect(originalModel.dispose).toHaveBeenCalled();
    expect(modifiedModel.dispose).toHaveBeenCalled();
    expect(editor.setModel).toHaveBeenCalledWith(null);
    expect((comp as any).diffEditor).toBeUndefined();
    expect((comp as any).originalModel).toBeUndefined();
    expect((comp as any).modifiedModel).toBeUndefined();
  });

  it('ngOnDestroy：editor 已释放（isDisposed=true）→ setModel 被守卫跳过，不抛，两 Model 仍 dispose', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel, disposed: true });
    (comp as any).onDiffInit(editor);
    expect(() => (comp as any).ngOnDestroy()).not.toThrow();
    expect(editor.setModel).not.toHaveBeenCalled();
    expect(originalModel.dispose).toHaveBeenCalled();
    expect(modifiedModel.dispose).toHaveBeenCalled();
  });

  it('ngOnDestroy 后晚到 applyValues → 不改 Model（destroyed 守卫）', () => {
    const editor = mockEditor({ original: originalModel, modified: modifiedModel });
    (comp as any).onDiffInit(editor);
    (comp as any).ngOnDestroy();
    // onDiffInit 时 applyValues 会合法地 setValue（初始 ''),reset 后只看晚到这一次
    originalModel.setValue.calls.reset();
    modifiedModel.setValue.calls.reset();
    originalModel.getValue.and.returnValue('old-o');
    modifiedModel.getValue.and.returnValue('old-m');
    (comp as any).originalValue = 'late-o';
    (comp as any).modifiedValue = 'late-m';
    (comp as any).applyValues();
    expect(originalModel.setValue).not.toHaveBeenCalled();
    expect(modifiedModel.setValue).not.toHaveBeenCalled();
  });

  it('纯新增/纯删除行统计：Monaco 0 区间不误计', () => {
    const editor = mockEditor({
      original: originalModel,
      modified: modifiedModel,
      lineChanges: [
        // 纯新增：无 original 区间
        { modifiedStartLineNumber: 2, modifiedEndLineNumber: 4, originalStartLineNumber: 0, originalEndLineNumber: 0 },
        // 纯删除：无 modified 区间
        { originalStartLineNumber: 1, originalEndLineNumber: 3, modifiedStartLineNumber: 0, modifiedEndLineNumber: 0 },
      ],
    });
    (comp as any).originalValue = 'old-o';
    (comp as any).modifiedValue = 'old-m';
    (comp as any).onDiffInit(editor);
    const cb = (editor as any).__diffCb;
    cb();
    // 纯新增 3 行（2..4）、纯删除 3 行（1..3）
    expect(comp.lineAdd).toBe(3);
    expect(comp.lineDel).toBe(3);
  });
});
