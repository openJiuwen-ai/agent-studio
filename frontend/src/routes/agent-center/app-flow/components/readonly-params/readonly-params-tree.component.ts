import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { MODULES } from '@shared/modules';
import { type IWorkflowField } from '../../node.type';
import { NodeUtils } from '../utils';
import { NzTreeModule, NzFormatEmitEvent } from 'ng-zorro-antd/tree';
import { NzTreeNodeOptions } from 'ng-zorro-antd/tree';

@Component({
  selector: 'readonly-params-tree',
  template: `
    <nz-tree
      id="output-param-tree"
      [nzData]="nzTreeNodes"
      [nzShowLine]="true"
      [nzExpandAll]="true"
    >
    </nz-tree>
  `,
  styles: [],
  standalone: true,
  imports: [MODULES, NzTreeModule],
})
export class ReadonlyParamsTreeComponent implements OnChanges {
  @Input() params: IWorkflowField[];

  public outputParams: any[];

  public nzTreeNodes: NzTreeNodeOptions[] = [];

  public getType = NodeUtils.getFieldTypeView;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['params']) {
      this.updateTree();
    }
  }

  ngOnInit(): void {
    this.updateTree();
  }

  private updateTree(): void {
    this.outputParams = NodeUtils.fields2Views(this.params);
    this.nzTreeNodes = this.convertToNzTree(this.outputParams);
  }

  private convertToNzTree(nodes: any[]): NzTreeNodeOptions[] {
    return nodes.map(node => this.createTreeNode(node));
  }

  private createTreeNode(node: any): NzTreeNodeOptions {
    const typeLabel = this.getType(node);
    const treeNode: NzTreeNodeOptions = {
      title: `${node.name} (${typeLabel})`,
      key: node.key,
      isLeaf: !node.children || node.children.length === 0,
    };

    if (node.children && node.children.length > 0) {
      treeNode.children = node.children.map((child: any) => this.createTreeNode(child));
    }

    return treeNode;
  }
}
