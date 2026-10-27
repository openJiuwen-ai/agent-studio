/**
 * 变量引用下拉高亮：按 ref 匹配，且克隆树不污染共享 options。
 * 覆盖 bug 5142625 / versatile_variable_Reference_2002 的核心判定。
 */
import {
  cloneTreeWithSelection,
  isNodeSelected,
} from '../routes/agent-center/app-flow/components/input-tree-select/input-tree-select.utils';

describe('input-tree-select highlight helpers', () => {
  const sharedOptions = [
    {
      key: 'n1',
      name: '开始',
      ref_node_id: 'node_start',
      ref_var_name: '',
      children: [
        { key: 'q1', name: 'query', ref_node_id: 'node_start', ref_var_name: 'query', type: 'string' },
        { key: 's1', name: 'sys', ref_node_id: 'node_start', ref_var_name: 'sys', type: 'object' },
      ],
    },
    {
      key: 'n2',
      name: '代码',
      ref_node_id: 'node_code',
      ref_var_name: '',
      children: [
        { key: 'd1', name: 'data', ref_node_id: 'node_code', ref_var_name: 'data', type: 'object' },
      ],
    },
  ];

  it('只高亮当前选中的叶子，不误伤兄弟节点', () => {
    const value = [{ ref_node_id: 'node_start', ref_var_name: 'query' }];
    const { tree, selectedKeys } = cloneTreeWithSelection(sharedOptions[0].children, value);
    expect(tree[0].selected).toBe(true);
    expect(tree[1].selected).toBe(false);
    expect(selectedKeys).toEqual(['q1']);
  });

  it('克隆后改 selected 不影响共享 options', () => {
    const value = [{ ref_node_id: 'node_code', ref_var_name: 'data' }];
    const { tree } = cloneTreeWithSelection(sharedOptions[1].children, value);
    expect(tree[0].selected).toBe(true);
    expect((sharedOptions[1].children[0] as any).selected).toBeUndefined();
  });

  it('切换到另一引用值时只有新值高亮', () => {
    const v1 = [{ ref_node_id: 'node_start', ref_var_name: 'query' }];
    const v2 = [{ ref_node_id: 'node_start', ref_var_name: 'sys' }];
    const first = cloneTreeWithSelection(sharedOptions[0].children, v1);
    const second = cloneTreeWithSelection(sharedOptions[0].children, v2);
    expect(first.tree.filter((n: any) => n.selected).map((n: any) => n.key)).toEqual(['q1']);
    expect(second.tree.filter((n: any) => n.selected).map((n: any) => n.key)).toEqual(['s1']);
  });

  it('isNodeSelected 按 ref 匹配', () => {
    const value = [{ ref_node_id: 'node_start', ref_var_name: 'query' }];
    expect(isNodeSelected(value, sharedOptions[0].children[0])).toBe(true);
    expect(isNodeSelected(value, sharedOptions[0].children[1])).toBe(false);
  });
});
