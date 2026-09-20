import {
  Component,
  EventEmitter,
  Input,
  OnInit,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { DataSourceManagementRepoService } from '@services/repositories/datasource-management-repo.service';
import { cloneDeep } from 'lodash';
import { AppFlowService } from '../../app-flow.service';
import {
  getInitInputParamConfig,
  getInputParamTypes,
  getNoneObjOutputParamTypes,
  getOutputParamTypes,
  LAZY_LOAD_LIMIT,
  WORKFLOW_SVGS,
} from '../../flow.const';
import { NodeService } from '../../node.service';
import type {
  IParamRef,
  ISqlNode,
  IDataQueryNode,
  IWFViewWithMultiType,
  IWorkflowField,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { AddPropsIconComponent } from '../add-props-icon/add-props-icon.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { EditNameComponent } from '../edit-name/edit-name.component';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import { NodeUtils } from '../utils';
import { InputTreeSelect } from 'src/routes/agent-center/app-flow/components/input-tree-select/input-tree-select';
import { NonEmptyValidatorDirective, ValueValidityValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { IDatasourceList, IDatasourceItem } from '@routes/agent-center/types/datasource.types';
import { FlowUtils } from '../../utils/flow-utils';

@Component({
  selector: 'meta-sql-modal',
  templateUrl: './sql-modal.component.html',
  styleUrls: ['./sql-modal.component.scss', '../common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    ValueValidityValidatorDirective,
    AddPropsIconComponent,
    EditNameComponent,
    NodeDescriptionComponent,
    InputTreeSelect,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class SqlModalComponent extends ModalBaseComponent implements OnInit, OnDestroy {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: ISqlNode | IDataQueryNode;

  @Output('confirm') confirm = new EventEmitter<ISqlNode | IDataQueryNode>();

  @ViewChild('inputForm') inputForm: NgForm;

  @ViewChild('outputForm') outputForm: NgForm;

  public get iconUrl(): string {
    return this.nodeInfo?.type === 'DataQuery'
      ? WORKFLOW_SVGS.DataQuery
      : WORKFLOW_SVGS.Sql;
  }

  public inputParams: IWorkflowField[] = [];

  public inputSourceOptions = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public datasourceOptions: IDatasourceItem[] = [];
  public datasourceLoading = false;
  public selectedDatasource: any = null;
  private datasourceTotal = 0;
  private datasourceSearchValue = '';

  public sql = '';

  public outputParams: IWFViewWithMultiType[] = [];

  public outputDataTypes = getOutputParamTypes();
  public noneObjDataTypes = getNoneObjOutputParamTypes();
  public inputTypeOptions = getInputParamTypes();

  public isObjectLikeType = NodeUtils.isObjectLikeType;
  public isSimpleType = NodeUtils.isSimpleType;
  public addChild = NodeUtils.addChild;
  public onOutputParamTypeChange = NodeUtils.onOutputParamTypeChange;

  override slimParamLableWidth = {
    name: '180px',
    type: '180px',
    desc: '0',
  };

  private nameRefOptions: IParamRef[] = [];

  updateTimeout: any = null;

  constructor(
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private i18n: I18NextEagerPipe,
    private dataSourceRepoServe: DataSourceManagementRepoService,
  ) {
    super(nodeServ, appFlowServ);
  }

  override ngOnInit() {
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode, { strOnly: true }).subscribe(
        (info) => {
          this.onRefUpdate(info);
        },
      );
    } else {
      this.getSelfRefs({ strOnly: true }).subscribe((info) => {
        this.onRefUpdate(info);
      });
    }

    this.outputParams = FlowUtils.fields2Views(
      (this.nodeInfo as ISqlNode).outputs,
    );

    this.selectedDatasource = this.nodeInfo.configs?.id
      ? {
          id: this.nodeInfo.configs.id,
          name: this.nodeInfo.configs.name,
          type: this.nodeInfo.configs.type,
        }
      : null;
    this.sql = this.nodeInfo.configs?.sql || '';

    this.loadDatasourceOptions(true);
  }

  compareDatasource = (a: any, b: any): boolean => {
    return a && b && a.id === b.id;
  };

  public get tipVals() {
    return this.inputParams.map((param) => param.name);
  }

  public handelSave() {
    if (this.tagCompareNoChange()) {
      return;
    }
    const datasource = this.selectedDatasource;
    const configs = {
      ...cloneDeep(this.nodeInfo.configs),
      id: datasource?.id,
      name: datasource?.name,
      type: datasource?.type,
      sql: this.sql,
    };
    this.appFlowServ.setNodeSaveMonitor({
      nodeData: {
        ...this.nodeInfo,
        inputs: NodeUtils.getDtoInputs(this.inputParams),
        configs,
        outputs: NodeUtils.multiTypeViews2Fields(this.outputParams),
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

  dismiss(): void {}

  close(): void {}

  private onRefUpdate(info: IParamRef[]) {
    this.nameRefOptions = info;

    if (this.isInit) {
      this.inputParams = NodeUtils.initInputs(
        this.nodeInfo.inputs,
        this.nameRefOptions,
      );
    } else {
      NodeUtils.reSelectRefsWithNewOps(this.inputParams, this.nameRefOptions);
    }

    this.isInit = false;
  }

  onNameChange() {
    window.setTimeout(() => {
      this.outputForm?.form?.updateValueAndValidity();
    });
  }

  getInputNames(index: number): { existingValues: string[] } {
    const names = this.inputParams.map((p) => p.name);
    names.splice(index, 1);
    return { existingValues: names };
  }

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
    this.onSave();
  }

  public addInputParam() {
    this.inputParams.push({
      ...getInitInputParamConfig(),
      refs: cloneDeep(this.nameRefOptions),
    });
    this.onSave();
  }

  public deleteInputParam(index: number): void {
    this.inputParams.splice(index, 1);
    this.onSave();
  }

  showDelete(param: IWFViewWithMultiType) {
    if (this.disableEdit(param)) {
      return false;
    }
    if (param.depth === 0 && this.outputParams.length === 1) {
      return false;
    }
    return true;
  }

  disableEdit(param: IWFViewWithMultiType) {
    return param.name === 'output_list' || param.name === 'row_num';
  }

  onStartNodeNameChange() {
    window.setTimeout(() => {
      this.outputForm?.form?.updateValueAndValidity();
    });
  }

  getOutputNames(param: IWFViewWithMultiType): { existingValues: string[] } {
    let names: string[] = [];
    if (param.depth === 0) {
      names = this.outputParams.map((arg) => arg.name);
    } else {
      const parentNode = this.findParentNode(this.outputParams, param);
      names = parentNode?.children?.map((arg) => arg.name) || [];
    }
    names.splice(names.indexOf(param.name), 1);
    return { existingValues: names };
  }

  private findParentNode(nodes: IWFViewWithMultiType[], target: any): IWFViewWithMultiType | null {
    for (const node of nodes) {
      if (node.children?.includes(target)) {
        return node;
      }
      if (node.children) {
        const found = this.findParentNode(node.children, target);
        if (found) return found;
      }
    }
    return null;
  }

  deleteOutputParam(param: IWFViewWithMultiType) {
    const removeNode = (nodes: IWFViewWithMultiType[], target: any): boolean => {
      const idx = nodes.indexOf(target);
      if (idx >= 0) {
        nodes.splice(idx, 1);
        return true;
      }
      for (const node of nodes) {
        if (node.children && removeNode(node.children, target)) {
          if (node.children.length === 0) {
            delete node.children;
          }
          return true;
        }
      }
      return false;
    };
    removeNode(this.outputParams, param);
    this.onSave();
  }

  onDatasourceSearch(value: string) {
    this.datasourceSearchValue = value;
    this.loadDatasourceOptions(true);
  }

  onDatasourceLoadMore() {
    if (this.datasourceOptions.length >= this.datasourceTotal) {
      return;
    }
    this.loadDatasourceOptions(false);
  }

  private loadDatasourceOptions(reset: boolean) {
    if (reset) {
      this.datasourceOptions = [];
    }
    this.datasourceLoading = true;
    const page = Math.floor(this.datasourceOptions.length / LAZY_LOAD_LIMIT) + 1;
    const params: any = {
      page,
      pageSize: LAZY_LOAD_LIMIT,
    };
    if (this.datasourceSearchValue) {
      params.name = this.datasourceSearchValue;
    }
    this.dataSourceRepoServe
      .getDatasourceList(params)
      .then((result: IDatasourceList) => {
        this.datasourceOptions = [...this.datasourceOptions, ...(result.datasources || [])];
        this.datasourceTotal = result.total || 0;
      })
      .finally(() => {
        this.datasourceLoading = false;
      });
  }

  onSave() {
    this.changeUpdateTime();
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  modelCloseSave() {
    if (!this.tagCompareNoChange()) {
      this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    }
    this.handelSave();
  }

  treeSelect() {
    setTimeout(() => {
      this.onSave();
    });
  }

  inputOnSave() {
    if (this.appFlowServ.testRunVerificationError) {
      this.handelSave();
    }
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.modelCloseSave();
  }
}
