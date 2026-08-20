import {
  normalizeGraphDslForDiff,
  serializeGraphDslForDiff,
} from '../../shared/components/release-history-halfmodal/diff-version-modal/normalize-graph-dsl-for-diff';

// 阶段二 spec：图 DSL 顺序规范化纯函数。
// 规则：根级 nodes/comments 按 String(id) 排序、edges 按 [source,target,branch,exception_branch] 排序、
// 所有普通对象键递归排序、其余数组（含嵌套）保序、不修改输入。

describe('normalizeGraphDslForDiff — 图 DSL 顺序规范化', () => {
  it('nodes 仅顺序不同 → 输出一致', () => {
    const a = { nodes: [{ id: 'b' }, { id: 'a' }, { id: 'c' }] };
    const b = { nodes: [{ id: 'c' }, { id: 'b' }, { id: 'a' }] };
    expect(JSON.stringify(normalizeGraphDslForDiff(a))).toBe(JSON.stringify(normalizeGraphDslForDiff(b)));
  });

  it('comments 仅顺序不同 → 输出一致', () => {
    const a = { comments: [{ id: 'c2' }, { id: 'c1' }] };
    const b = { comments: [{ id: 'c1' }, { id: 'c2' }] };
    expect(JSON.stringify(normalizeGraphDslForDiff(a))).toBe(JSON.stringify(normalizeGraphDslForDiff(b)));
  });

  it('edges 仅顺序不同 → 输出一致', () => {
    const a = {
      edges: [
        { source: 'n1', target: 'n2' },
        { source: 'n1', target: 'n2', branch: 'yes' },
        { source: 'n3', target: 'n4' },
      ],
    };
    const b = {
      edges: [
        { source: 'n3', target: 'n4' },
        { source: 'n1', target: 'n2', branch: 'yes' },
        { source: 'n1', target: 'n2' },
      ],
    };
    expect(JSON.stringify(normalizeGraphDslForDiff(a))).toBe(JSON.stringify(normalizeGraphDslForDiff(b)));
  });

  it('普通边与异常边不同排列 → 输出完全一致（异常边进排序身份，两条都保留）', () => {
    const normal = { source: 'n1', target: 'n2' };
    const exception = { source: 'n1', target: 'n2', exception_branch: true };
    const left = { edges: [normal, exception] };
    const right = { edges: [exception, normal] };
    // 不同排列 → 规范化后完全一致（异常边参与排序身份）
    expect(serializeGraphDslForDiff(left)).toBe(serializeGraphDslForDiff(right));
    // 两条边都保留，exception_branch 未丢
    const out = normalizeGraphDslForDiff(left) as any;
    expect(out.edges.length).toBe(2);
    expect(out.edges.some((e: any) => e.exception_branch === true)).toBe(true);
  });

  it('对象键插入顺序不同 → 输出一致', () => {
    const a = { z: 1, a: 2, m: { y: 1, b: 2 } };
    const b = { a: 2, m: { b: 2, y: 1 }, z: 1 };
    expect(JSON.stringify(normalizeGraphDslForDiff(a))).toBe(JSON.stringify(normalizeGraphDslForDiff(b)));
  });

  it('业务数组(agents/branches/inputs/outputs)换序 → 仍产生差异(保序)', () => {
    const a = { configs: { agents: [{ id: 'x' }, { id: 'y' }] }, branches: ['b1', 'b2'] };
    const b = { configs: { agents: [{ id: 'y' }, { id: 'x' }] }, branches: ['b2', 'b1'] };
    expect(JSON.stringify(normalizeGraphDslForDiff(a))).not.toBe(JSON.stringify(normalizeGraphDslForDiff(b)));
  });

  it('输入对象不被原地修改（深相等）', () => {
    const input = { nodes: [{ id: 'b' }, { id: 'a' }], edges: [{ source: 'n2', target: 'n1' }] };
    const snapshot = JSON.parse(JSON.stringify(input));
    normalizeGraphDslForDiff(input);
    expect(input).toEqual(snapshot);
  });

  it('节点 id 重复/缺失，不同排列 → 输出一致且不丢元素', () => {
    const left = { nodes: [{ id: 'a', x: 1 }, { noId: true }, { id: 'a', x: 2 }] };
    const right = { nodes: [{ id: 'a', x: 2 }, { id: 'a', x: 1 }, { noId: true }] };
    // 不同排列 → 规范化后完全一致（重复 id 用完整对象 JSON 兜底排序，缺失 id 当 '' 排最前）
    expect(serializeGraphDslForDiff(left)).toBe(serializeGraphDslForDiff(right));
    expect((normalizeGraphDslForDiff(left) as any).nodes.length).toBe(3);
  });

  it('嵌套字段也叫 nodes → 数组顺序保持不变（只根级排序）', () => {
    const a = {
      nodes: [{ id: 'b' }, { id: 'a', configs: { nodes: [{ id: 'z' }, { id: 'y' }] } }],
    };
    const out = normalizeGraphDslForDiff(a) as any;
    // 根级 nodes 按 id 排：a 在 b 前
    expect(out.nodes[0].id).toBe('a');
    expect(out.nodes[1].id).toBe('b');
    // 嵌套 configs.nodes 顺序保持原样：z 仍在 y 前（未被排序）
    expect(out.nodes[0].configs.nodes.map((n: any) => n.id)).toEqual(['z', 'y']);
  });

  it('Multi 无 comments 字段 → 正常处理（不报错、nodes 仍排序）', () => {
    const a = { nodes: [{ id: 'b' }, { id: 'a' }], edges: [] };
    const out = normalizeGraphDslForDiff(a) as any;
    expect(out.nodes.map((n: any) => n.id)).toEqual(['a', 'b']);
    expect(out.edges).toEqual([]);
    expect(out.comments).toBeUndefined();
  });

  it('nodes/edges/comments 为空数组 → 正常处理', () => {
    const out = normalizeGraphDslForDiff({ nodes: [], edges: [], comments: [] }) as any;
    expect(out.nodes).toEqual([]);
    expect(out.edges).toEqual([]);
    expect(out.comments).toEqual([]);
  });

  it('layouts 坐标变化 → 仍产生差异（坐标值保留）', () => {
    const a = { layouts: { n1: { x: 10, y: 20 } } };
    const b = { layouts: { n1: { x: 99, y: 20 } } };
    expect(serializeGraphDslForDiff(a)).not.toBe(serializeGraphDslForDiff(b));
  });

  it('global_variables（业务数组）换序 → 仍产生差异', () => {
    const a = { global_variables: [{ name: 'a' }, { name: 'b' }] };
    const b = { global_variables: [{ name: 'b' }, { name: 'a' }] };
    expect(serializeGraphDslForDiff(a)).not.toBe(serializeGraphDslForDiff(b));
  });

  it('serializeGraphDslForDiff = 美化 JSON 序列化规范化结果', () => {
    const a = { nodes: [{ id: 'b' }, { id: 'a' }] };
    const text = serializeGraphDslForDiff(a);
    expect(text).toBe(JSON.stringify({ nodes: [{ id: 'a' }, { id: 'b' }] }, null, 2));
  });
});
