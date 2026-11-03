import { ChangeDetectorRef, Component, ElementRef, Input } from '@angular/core';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { takeUntil } from 'rxjs';
import type { ITemplateTransformNode } from '../../node.type';
import { AppFlowService } from '../../app-flow.service';
import { NodeService } from '../../node.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { FlowUtils } from '../../utils/flow-utils';

@Component({
  selector: 'meta-template-transform-node',
  templateUrl: './template-transform-node.component.html',
  styleUrls: ['../common-styles.less', './template-transform-node.component.less'],
  standalone: true,
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class TemplateTransformNodeComponent extends NodeBaseComponent {
  @Input('nodeInfo') nodeInfo: ITemplateTransformNode;

  public icon = WORKFLOW_SVGS.TemplateTransform;

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override cdr: ChangeDetectorRef,
    protected override elementRef: ElementRef<HTMLDivElement>,
  ) {
    super(nodeServ, appFlowServ, cdr, elementRef);
  }

  override ngOnInit(): void {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();
    this.appFlowServ.nodeRefChange$().pipe(takeUntil(this.destroy$)).subscribe((data: any) => {
      FlowUtils.handelNodeRefChange(data, this.nodeInfo?.inputs);
    });
  }
}
