import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnInit,
} from '@angular/core';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { I18nNamespace } from '@i18n';
import { AppFlowService } from '../../app-flow.service';
import type { IHttpRepo } from '../../node.type';
import { NodeService } from '../../node.service';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeBaseComponent } from '../base/node-base.component';
import { NodeDependencies } from '../modules';
import { takeUntil } from 'rxjs';
import { FlowUtils } from '../../utils/flow-utils';

@Component({
  selector: 'meta-http-node',
  standalone: true,
  templateUrl: './http-node.component.html',
  styleUrls: ['../common-styles.less', './http-node.component.scss'],
  imports: [NodeDependencies],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class HttpNodeComponent extends NodeBaseComponent implements OnInit {
  @Input('nodeInfo') nodeInfo: IHttpRepo;

  public httpImgUrl = WORKFLOW_SVGS.Http;

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
