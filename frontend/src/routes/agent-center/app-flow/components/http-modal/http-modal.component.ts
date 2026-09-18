import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
  ViewChild,
} from '@angular/core';
import { Validators } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { CommonValidation } from '@shared/validation/commonValidation';
import { I18NEXT_NAMESPACE, I18NextEagerPipe, I18NextModule } from 'angular-i18next';
import { cloneDeep } from 'lodash';
import { takeUntil } from 'rxjs';
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
    I18NextModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
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
    private i18n: I18NextEagerPipe,
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
  ) {
    super(nodeServ, appFlowServ);
  }

  override ngOnInit(): void {
    this.ensureHttpInputContainers();
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
    // refs 订阅随弹窗销毁终止，避免组件销毁后仍回调 onRefUpdate
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { strOnly: true })
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => this.onRefUpdate(info));
    } else {
      this.getSelfRefs()
        .pipe(takeUntil(this.destroy$))
        .subscribe((info) => this.onRefUpdate(info));
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

  /**
   * 自愈：确保 nodeInfo.inputs 里存在 query / headers 两个容器条目。
   * 背景（FB-1）：历史上把某个分区的行删光后，容器条目会连同 schema 一起从
   * 已存 DSL 中丢失；此后 handelSave 用 find('query'/'headers') 找不到容器便
   * 静默跳过写回，导致请求头/请求参数再也存不上（节点进入终态损坏）。
   * 打开面板时按工厂默认补回缺失容器，坏节点即可恢复可保存。
   */
  ensureHttpInputContainers(): void {
    if (!Array.isArray(this.nodeInfo.inputs)) {
      this.nodeInfo.inputs = [];
    }
    const defaults = this.appFlowServ.getInitHttpContainerInputs();
    defaults.forEach((container) => {
      const exist = this.nodeInfo.inputs.find(
        (item) => item.name === container.name,
      );
      if (!exist) {
        this.nodeInfo.inputs.push(cloneDeep(container));
      } else if (!Array.isArray(exist.schema)) {
        exist.schema = [];
      }
    });
  }

  handelSave(): void {
    if (this.tagCompareNoChange()) {
      return;
    }

    // FB-1 自愈：容器缺失会导致下面 find 静默跳过、行参数永远存不上，先确保容器存在。
    // 行数据本身如实保存（含空白行），与代码/大模型节点的单层结构行为约定一致：
    // 空白行落 DSL 后由试运行时后端校验报错，提醒用户填写或删除。
    this.ensureHttpInputContainers();

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
    // 清理未决的 200ms 更新定时器，避免组件销毁后触发 updateChangeAndInitTime
    if (this.updateTimeout) {
      clearTimeout(this.updateTimeout);
      this.updateTimeout = null;
    }
    super.ngOnDestroy();
    this.modelCloseSave();
  }
}
