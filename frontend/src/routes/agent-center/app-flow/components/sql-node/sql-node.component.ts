import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnInit,
} from '@angular/core';
import { NodeDependencies } from '../modules';
import { ReadonlyParamsComponent } from '../readonly-params/readonly-params.component';
import { I18NEXT_NAMESPACE,I18NextEagerPipe } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { NodeBaseComponent } from '../base/node-base.component';
import { WORKFLOW_SVGS } from '../../flow.const';
import { AppFlowService } from '../../app-flow.service';
import { NodeService } from '../../node.service';
import { type ISqlNode } from '../../node.type';
import type { IDataQueryNode } from '../../node.type';
import { MODULES } from '@shared/modules';
import { takeUntil } from 'rxjs';
import { FlowUtils } from '../../utils/flow-utils';
@Component({
  selector: 'meta-sql-node',
  templateUrl: './sql-node.component.html',
  styleUrls: ['../common-styles.less', './sql-node.component.scss'],
  standalone: true,
  imports: [NodeDependencies, ReadonlyParamsComponent, MODULES],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SqlNodeComponent extends NodeBaseComponent implements OnInit {
  @Input('nodeInfo') nodeInfo: ISqlNode | IDataQueryNode;

  public get icon(): string {
    return this.nodeInfo?.type === 'DataQuery'
      ? WORKFLOW_SVGS.DataQuery
      : WORKFLOW_SVGS.Sql;
  }

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    protected override elementRef: ElementRef<HTMLDivElement>,
    private i18n: I18NextEagerPipe,
    protected override cdr: ChangeDetectorRef,
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
