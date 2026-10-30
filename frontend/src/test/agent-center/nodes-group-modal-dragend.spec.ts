import { NodesGroupModalComponent } from '../../routes/agent-center/app-flow/components/nodes-group-modal/nodes-group-modal.component';
import type { NodeInfo } from '../../routes/agent-center/app-flow/node.type';

/**
 * Regression for #1193: palette dragend must not create nodes for cancelled
 * or off-canvas drops.
 */
describe('NodesGroupModalComponent dragend (#1193)', () => {
  let createNodeEmit: jasmine.Spy;
  let pageToLocal: jasmine.Spy;
  let component: {
    isFlowReadonly: boolean;
    clickNodeX: number;
    clickNodeY: number;
    graph: { pageToLocal: jasmine.Spy };
    createNode: { emit: jasmine.Spy };
    onDragStart: NodesGroupModalComponent['onDragStart'];
    onDragEnd: NodesGroupModalComponent['onDragEnd'];
  };

  const node = { name: 'Code', type: 'Code' } as NodeInfo;

  beforeEach(() => {
    createNodeEmit = jasmine.createSpy('createNode.emit');
    pageToLocal = jasmine.createSpy('pageToLocal').and.returnValue({ x: 300, y: 200 });
    component = {
      isFlowReadonly: false,
      clickNodeX: 10,
      clickNodeY: 10,
      graph: { pageToLocal },
      createNode: { emit: createNodeEmit },
      onDragStart: NodesGroupModalComponent.prototype.onDragStart,
      onDragEnd: NodesGroupModalComponent.prototype.onDragEnd,
    };
  });

  function dragEndEvent(dropEffect: DataTransfer['dropEffect'] = 'copy'): DragEvent {
    return {
      pageX: 300,
      pageY: 200,
      dataTransfer: { dropEffect },
    } as DragEvent;
  }

  it('does not create a node when the drag is cancelled (dropEffect: none)', () => {
    component.onDragEnd.call(component, dragEndEvent('none'), node);
    expect(createNodeEmit).not.toHaveBeenCalled();
  });

  it('does not create a node when release maps to negative graph coordinates', () => {
    pageToLocal.and.returnValue({ x: -50, y: -20 });
    component.onDragEnd.call(component, dragEndEvent(), node);
    expect(createNodeEmit).not.toHaveBeenCalled();
  });

  it('creates a node on a successful accepted drop', () => {
    component.onDragEnd.call(component, dragEndEvent(), node);
    expect(createNodeEmit).toHaveBeenCalledTimes(1);
    expect(createNodeEmit.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({
        name: 'Code',
        type: 'Code',
        x: 290,
        y: 190,
        shape: 'op-code-node',
      }),
    );
  });

  it('does not create a node in read-only mode', () => {
    component.isFlowReadonly = true;
    component.onDragEnd.call(component, dragEndEvent(), node);
    expect(createNodeEmit).not.toHaveBeenCalled();
  });

  it('marks the drag as a copy operation on dragstart', () => {
    const dataTransfer = {
      setData: jasmine.createSpy('setData'),
      effectAllowed: 'uninitialized',
    };
    component.onDragStart.call(component, {
      offsetX: 12,
      offsetY: 8,
      dataTransfer,
      preventDefault: jasmine.createSpy('preventDefault'),
    } as unknown as DragEvent);

    expect(dataTransfer.setData).toHaveBeenCalledWith('text/plain', 'palette-node');
    expect(dataTransfer.effectAllowed).toBe('copy');
    expect(component.clickNodeX).toBe(12);
    expect(component.clickNodeY).toBe(8);
  });
});
