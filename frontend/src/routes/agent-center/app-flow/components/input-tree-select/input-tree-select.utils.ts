/**
 * input-tree-select 纯函数：类型兼容表、叶子禁用、高亮克隆。
 * 组件与单测共用，避免 spec 内重实现导致回归测不到。
 */

/** 与 modal-base.getCompatibleTypes 对齐：string 可引用 file/* 等 */
export function getCompatibleTypes(type: string): string[] {
  const t = type?.toLowerCase();
  if (!t) {
    return [];
  }
  const fileSubTypes = ['default', 'doc', 'txt', 'excel', 'ppt', 'image', 'audio', 'video'];
  if (t === 'string') {
    return ['string', ...fileSubTypes.map(s => `file/${s}`)];
  }
  if (t === 'array<string>') {
    return ['array<string>', ...fileSubTypes.map(s => `array<file/${s}>`)];
  }
  if (t === 'file/default') {
    return fileSubTypes.map(s => `file/${s}`);
  }
  if (t === 'array<file/default>') {
    return fileSubTypes.map(s => `array<file/${s}>`);
  }
  return [t];
}

/**
 * 叶子按兼容类型禁用；中间节点保持可展开（disabled=false），
 * 类型不兼容时打 selectDisabled，禁止选中但仍可展开到嵌套同类型字段。
 */
export function setDifferentTypeDisabledEacl(list: any[], compatible: string[]): any[] {
  return (list || []).map(item => {
    const hasChildren = !!item.children?.length;
    const itemType = String(item.type ?? '').toLowerCase();
    const typeMismatch = itemType.length > 0 && !compatible.includes(itemType);
    if (hasChildren) {
      item.disabled = false;
      item.selectDisabled = typeMismatch;
      item.children = setDifferentTypeDisabledEacl(item.children, compatible);
    } else {
      item.disabled = typeMismatch;
      item.selectDisabled = typeMismatch;
    }
    return item;
  });
}

/** 当前节点是否为已选引用（按 ref_node_id + ref_var_name，不依赖对象引用） */
export function isNodeSelected(value: any, node: any): boolean {
  const selected = value?.[0];
  if (!selected || !node) {
    return false;
  }
  return selected.ref_node_id === node.ref_node_id && selected.ref_var_name === node.ref_var_name;
}

/**
 * 克隆二级树并只在副本上打 selected/expanded，避免多字段共享 options 时高亮串色。
 * selectedKeys 会被原地追加选中节点的 key。
 */
export function cloneTreeWithSelection(
  nodes: any[],
  value: any,
  selectedKeys: string[] = [],
): { tree: any[]; selectedKeys: string[] } {
  if (!nodes?.length) {
    return { tree: [], selectedKeys };
  }
  const tree = nodes.map(node => {
    const selected = isNodeSelected(value, node);
    const cloned: any = {
      ...node,
      selected,
      expanded: true,
      children: node.children ? cloneTreeWithSelection(node.children, value, selectedKeys).tree : undefined,
    };
    if (selected && cloned.key != null) {
      selectedKeys.push(String(cloned.key));
    }
    return cloned;
  });
  return { tree, selectedKeys };
}

/** 节点是否允许作为引用选中（展开不受影响） */
export function isNodeRefSelectable(node: any): boolean {
  if (!node) {
    return false;
  }
  if (node.disabled === true || node.selectDisabled === true) {
    return false;
  }
  return true;
}
