import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { Validators } from '@angular/forms';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { cloneDeep } from 'lodash';
import { AppFlowService } from '../../app-flow.service';
import { NodeService } from '../../node.service';
import {
  IHttpConfig,
  IParamRef,
  IWorkflowField,
  type IHttpRepo,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ReadonlyParamsTreeComponent } from '../readonly-params/readonly-params-tree.component';
import { EditNameComponent } from '../edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { NodeUtils } from '../utils';
import { ConfigUrlComponent } from './config-url/config-url.component';
import { ConfigRequestComponent } from './config-request/config-request.component';
import { ConfigAuthComponent } from './config-auth/config-auth.component';
import { ConfigExceptionComponent } from './config-exception/config-exception.component';
import { ConfigInputOutputComponent } from './config-input-output/config-input-output.component';

@Component({
  selector: 'meta-http-modal',
  standalone: true,
  imports: [
    MODULES,
    ConfigUrlComponent,
    ConfigInputOutputComponent,
    ConfigRequestComponent,
    ConfigAuthComponent,
    ConfigExceptionComponent,
    AccBlockComponent,
    ReadonlyParamsTreeComponent,
    EditNameComponent,
    NodeDescriptionComponent,
  ],
  templateUrl: './http-modal.component.html',
  styleUrl: './http-modal.component.less',
})
export class HttpModalComponent extends ModalBaseComponent implements OnInit {
  @Input('names') names!: string[];
  @Input('nodeInfo') nodeInfo!: IHttpRepo;
  @Output('confirm') confirm = new EventEmitter<any>();

  @ViewChild('configUrl') configUrl!: ConfigUrlComponent;
  @ViewChild('configInputOutput') configInputOutput!: ConfigInputOutputComponent;
  @ViewChild('configRequest') configRequest!: ConfigRequestComponent;
  @ViewChild('configAuth') configAuth!: ConfigAuthComponent;

  inputParams: IWorkflowField[] = [];

  sourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  nameRefOptions: IParamRef[] = [];

  configs: IHttpConfig = {
    method: 'POST',
    endpoint: '',
    path: '',
    request_type: 'JSON',
    request_body: '',
    auth_info: {
      scope: 'SERVICE',
      domain: 'HEADERS',
      auth_keys: [{ auth_key: '', target_name: '' }],
    },
    exception_enable: true,
    exception_suppression: '{"body":"","status_code":0,"headers":""}',
  };

  private updateTimeout: any = null;
  private validationRules = [Validators.required];

  constructor(
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
  ) {
    super(nodeServ, appFlowServ);
  }

  override ngOnInit(): void {
    this.setNodeBase(this.nodeInfo);
    this.configs = cloneDeep(this.nodeInfo.configs);
    super.ngOnInit();
    this.validationRules.push(
      CommonValidation.nameUniquenessVerify(
        this.names,
        this.i18n.transform('name_uniqueness'),
        this.nodeInfo.name,
      ),
    );

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { strOnly: true }).subscribe(
        (info) => this.onRefUpdate(info),
      );
    } else {
      this.getSelfRefs().subscribe((info) => this.onRefUpdate(info));
    }
  }

  ngAfterViewInit(): void {
    if (this.appFlowServ.testRunVerificationError) {
      setTimeout(() => this.validateNode());
    }
  }

  onRefUpdate(info: IParamRef[]): void {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(
        this.nodeInfo.inputs,
        this.nameRefOptions,
      );
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.inputParams = this.inputParams.filter(
      (item) => item.name !== 'headers' && item.name !== 'query',
    );

    this.isInit = false;
  }

  validateNode(): void {
    if (this.configUrl?.apiForm) {
      this.configUrl.apiForm.control.markAllAsTouched();
    }
    if (this.configInputOutput?.inputForm) {
      this.configInputOutput.inputForm.control.markAllAsTouched();
    }
    if (this.configRequest?.requestForm) {
      this.configRequest.requestForm.control.markAllAsTouched();
    }
    if (this.configAuth?.authkeyForm) {
      this.configAuth.authkeyForm.control.markAllAsTouched();
    }
  }

  inputChange(params: IWorkflowField[]): void {
    this.inputParams = [...params];
    this.onSave();
  }

  handelSave(): void {
    if (this.tagCompareNoChange()) {
      return;
    }

    const queryParams = this.nodeInfo.inputs.find(
      (item) => item.name === 'query',
    );
    const headerParams = this.nodeInfo.inputs.find(
      (item) => item.name === 'headers',
    );

    if (queryParams) {
      queryParams.schema = NodeUtils.getDtoInputs(this.configRequest.queryParams);
    }
    if (headerParams) {
      headerParams.schema = NodeUtils.getDtoInputs(this.configRequest.headerParams);
    }

    const inputs = this.nodeInfo.inputs
      .filter((item) => item.name === 'headers' || item.name === 'query')
      .concat(this.inputParams);

    this.nodeInfo.inputs = NodeUtils.getDtoInputs(inputs);

    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        configs: {
          ...this.configs,
          request_body:
            this.configs.request_type === 'NONE'
              ? ''
              : this.configs.request_body,
        },
      },
    });

    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    this.updateTimeout = setTimeout(() => {
      this.updateChangeAndInitTime();
    }, 200);
  }

  onSave(): void {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  treeSelect(): void {
    setTimeout(() => this.onSave());
  }

  modelCloseSave(): void {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  inputOnSave(): void {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.modelCloseSave();
  }
}
