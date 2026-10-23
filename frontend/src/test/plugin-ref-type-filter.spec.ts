/**
 * 插件引用类型过滤：import 真实 getCompatibleTypes / setDifferentTypeDisabledEacl。
 * 覆盖 bug 5142740。
 */
import {
  getCompatibleTypes,
  isNodeRefSelectable,
  setDifferentTypeDisabledEacl,
} from '../routes/agent-center/app-flow/components/input-tree-select/input-tree-select.utils';

describe('plugin ref type filter helpers', () => {
  it('integer 入参应禁用 string 叶子，保留 object 可展开但不可选', () => {
    const compatible = getCompatibleTypes('integer');
    const tree = setDifferentTypeDisabledEacl(
      [
        {
          type: 'object',
          name: 'sys',
          children: [
            { type: 'string', name: 'user_id', key: 'u1' },
            { type: 'integer', name: 'dialogue_count', key: 'd1' },
          ],
        },
        { type: 'string', name: 'query', key: 'q1' },
      ],
      compatible,
    );
    expect(tree[0].disabled).toBe(false);
    expect(tree[0].selectDisabled).toBe(true);
    expect(isNodeRefSelectable(tree[0])).toBe(false);
    expect(tree[0].children[0].disabled).toBe(true);
    expect(tree[0].children[1].disabled).toBe(false);
    expect(isNodeRefSelectable(tree[0].children[1])).toBe(true);
    expect(tree[1].disabled).toBe(true);
  });

  it('嵌套 object 类型不匹配时 selectDisabled，子叶子仍可按类型选', () => {
    const compatible = getCompatibleTypes('integer');
    const tree = setDifferentTypeDisabledEacl(
      [
        {
          type: 'object',
          name: 'sys',
          children: [
            {
              type: 'object',
              name: 'sub',
              children: [{ type: 'integer', name: 'n', key: 'n1' }],
            },
          ],
        },
      ],
      compatible,
    );
    expect(tree[0].selectDisabled).toBe(true);
    expect(tree[0].children[0].disabled).toBe(false);
    expect(tree[0].children[0].selectDisabled).toBe(true);
    expect(tree[0].children[0].children[0].disabled).toBe(false);
  });

  it('string 入参可兼容 file/image 与 file/video', () => {
    const compatible = getCompatibleTypes('string');
    expect(compatible).toContain('string');
    expect(compatible).toContain('file/image');
    expect(compatible).toContain('file/video');
    const tree = setDifferentTypeDisabledEacl(
      [
        { type: 'file/image', name: 'img', key: 'i1' },
        { type: 'file/video', name: 'vid', key: 'v1' },
      ],
      compatible,
    );
    expect(tree[0].disabled).toBe(false);
    expect(isNodeRefSelectable(tree[0])).toBe(true);
    expect(tree[1].disabled).toBe(false);
    expect(isNodeRefSelectable(tree[1])).toBe(true);
  });

  it('object 入参可选中同类型中间节点', () => {
    const compatible = getCompatibleTypes('object');
    const tree = setDifferentTypeDisabledEacl(
      [{ type: 'object', name: 'sys', children: [{ type: 'string', name: 'q', key: 'q1' }] }],
      compatible,
    );
    expect(tree[0].disabled).toBe(false);
    expect(tree[0].selectDisabled).toBe(false);
    expect(isNodeRefSelectable(tree[0])).toBe(true);
  });
});
