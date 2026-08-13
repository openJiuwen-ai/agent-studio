import { ChangeDetectorRef, Component, EventEmitter, Inject, Input, OnDestroy, OnInit, Optional, Output, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { TypedJsonInputComponent } from '@shared/components/typed-json-input/typed-json-input.component';
import { NumberStrValidatorDirective, NzTreeRefSelectedRequireDirective, RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { NonEmptyValidatorDirective } from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { Subject } from 'rxjs';
import { AppFlowService } from '../../app-flow.service';
import { NodeService } from '../../node.service';
import type { IParamRef, IWorkflowField } from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ParamTreeComponent } from '../param-tree/param-tree.component';
import { NodeUtils } from '../utils';
import { IRefInfo } from '../../app-flow.types';
import { IRequestArgsView } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { cloneDeep } from 'lodash';
import { NewCommonNoDataWithBtnComponent } from '@shared/components/new-common-no-data-with-btn/new-common-no-data-with-btn.component';
import { NzDrawerModule, NzDrawerRef } from 'ng-zorro-antd/drawer';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzIconModule } from 'ng-zorro-antd/icon';
import { NzTreeModule } from 'ng-zorro-antd/tree';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzInputModule } from 'ng-zorro-antd/input';
import { NzSpinModule } from 'ng-zorro-antd/spin';
import { NzToolTipModule } from 'ng-zorro-antd/tooltip';
import { FormsModule } from '@angular/forms';
import { ParamLabelPipe } from 'src/pipes/param-label.pipe';

export interface IPluginParamConf {
  inputs: IWorkflowField[];
  outputs: IWorkflowField[];
}

@Component({
  selector: 'meta-plugin-config-modal',
  standalone: true,
  templateUrl: './plugin-config-modal.component.html',
  styleUrls: ['./plugin-config-modal.component.scss', '.././common-styles.less'],
  imports: [
    MODULES,
    AccBlockComponent,
    NonEmptyValidatorDirective,
    RefSelectedRequireDirective,
    NzTreeRefSelectedRequireDirective,
    ParamLabelPipe,
    NumberStrValidatorDirective,
    MonacoEditorModule,
    ParamTreeComponent,
    TypedJsonInputComponent,
    NewCommonNoDataWithBtnComponent,
    NzDrawerModule,
    NzButtonModule,
    NzIconModule,
    NzTreeModule,
    NzSelectModule,
    NzSwitchModule,
    NzInputModule,
    NzSpinModule,
    NzToolTipModule,
    FormsModule,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class PluginConfigModalComponent implements OnInit, OnDestroy {
  @Input() detail?: any = {};
  @Input() type?: string = 'tool';
  @Input() inputParams: IWorkflowField[] = [];
  @Input() outputParams: any[] = [];
  @Input() isFlowReadonly = false;
  @Input() refInfos: IRefInfo[] = [];

  @ViewChild('inputForm') inputForm: NgForm;
  @Output('confirm') confirm = new EventEmitter<{ conf: any; type: string }>();
  @Output('cancel') cancelEvt = new EventEmitter<void>();

  public isLoadingParams = false;
  public nameRefOptions: IParamRef[] = [];
  public inputs: any[] = [];
  public isValidated = false;
  public loading = false;
  public isSimpleType = NodeUtils.isSimpleType;
  public options = [
    { label: this.i18n.transform('ref'), value: 'ref' },
    { label: this.i18n.transform('literal'), value: 'literal' },
  ];

  public booleanOps = [
    {
      label: 'true',
      value: true,
    },
    {
      label: 'false',
      value: false,
    },
  ];

  public getType = NodeUtils.getFieldTypeView;
  public getRrequired = NodeUtils.getRequiredText;
  public displayWithFn = (node: any) => node?.origin?.variable_key || node?.origin?.name || node?.title || '';
  private destroy$ = new Subject<void>();

  constructor(
    protected nodeServ: NodeService,
    protected appFlowServ: AppFlowService,
    private i18n: I18NextEagerPipe,
    private cdr: ChangeDetectorRef,
    @Optional() @Inject(NzDrawerRef) private drawerRef: NzDrawerRef | null
  ) {}

  async ngOnInit() {
    if (!this.inputParams || !this.outputParams) {
    }
    const that = this;
    this.inputs = NodeUtils.fields2ViewsUnchangeType(this.inputParams);
    this.handelSelectOptions(this.inputs);
    this.changeInputTypeToRef();
    this.initTreeSelectorHover();
    this.outputParams = NodeUtils.fields2Views(this.outputParams);
  }

  // 当引用类型是入参类型时，需要将type: input_type ---> type: ref, 保存的时候会自动把ref --> input_ref
  private changeInputTypeToRef() {
    for (let index = 0; index < this.inputs.length; index++) {
      if (this.inputs[index].value.type === 'input_ref') {
        this.inputs[index].value.type = 'ref';
      }
    }
  }

  handelSelectOptions(inputs) {
    inputs.forEach(v => {
      v.options = [
        {
          label: this.i18n.transform('ref'),
          value: 'ref',
          disabled: v.type.indexOf('array') > -1 || v.type !== 'string',
        },
        { label: this.getType(v), value: 'literal' },
      ];
      v.refs = this.convertRefsForTreeSelect(cloneDeep(this.refInfos));
      v._refSelectedKey = this.extractRefKey(v.value?.content);
      if (v.children) {
        this.handelSelectOptions(v.children);
      }
    });
  }

  private extractRefKey(content: any): string {
    if (Array.isArray(content) && content.length > 0) {
      return content[0].variable_key || content[0].ref_var_name || '';
    }
    return null;
  }

  private convertRefsForTreeSelect(refInfos: any[]): any[] {
    return refInfos.filter(group => !group.hidden).map(group => ({
      title: group._label || group.name,
      key: group.name,
      expanded: group.expanded ?? true,
      disabled: true,
      children: (group.children || []).map(child => ({
        title: child.variable_key || child.name || child.label,
        key: child.variable_key || child.name || child.label,
        isLeaf: true,
        origin: child,
        ...child,
      })),
      origin: group,
    }));
  }

  // 让引用参数的下拉框可以初始化的时候被选中
  private initTreeSelectorHover() {
    const needCheckValueContent = {};
    for (let index = 0; index < this.inputs.length; index++) {
      const content = this.inputs[index].value.content;
      const type = this.inputs[index].value.type;
      for (let i = 0; i < content.length; i++) {
        if (content[i].input_type) {
          needCheckValueContent[content[i].name] = 'input_ref';
        } else if (type === 'ref') {
          needCheckValueContent[content[i].name] = 'ref';
        }
      }
    }
    for (let index = 0; index < this.inputs.length; index++) {
      const refs = this.inputs[index].refs;
      for (let i = 0; i < refs.length; i++) {
        const children = refs[i].children;
        for (let childIndex = 0; childIndex < children.length; childIndex++) {
          const _name = children[childIndex].name;
          if (_name && !children[childIndex].input_type && needCheckValueContent[_name] === 'ref') {
            children[childIndex].checked = true;
          } else if (_name && children[childIndex].input_type && needCheckValueContent[_name] === 'input_ref') {
            children[childIndex].checked = true;
          }
        }
      }
    }
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onInputValueTypeChange(row: IWorkflowField) {
    row.value.content = NodeUtils.getChangeContent(row.value.type);
  }

  public onRefSelectChange(selectedKey: string, param: IWorkflowField): void {
    param._refSelectedKey = selectedKey;
    const selectedNode = this.findNodeByKey(param.refs, selectedKey);
    if (selectedNode) {
      const child = selectedNode.origin || selectedNode;
      param.value.content = [{
        name: child.variable_key || child.key,
        type: child.input_type || 'String',
        variable_key: child.variable_key || child.key,
        ref_node_id: child.ref_node_id || '',
        ref_var_name: child.ref_var_name || child.variable_key || child.key,
        default_value: child.default_value || '',
        source: 'user',
        input_type: child.input_type || undefined,
      }];
    }
  }

  private findNodeByKey(nodes: any[], key: string): any {
    for (const node of nodes) {
      if (node.key === key) return node;
      if (node.children) {
        const found = this.findNodeByKey(node.children, key);
        if (found) return found;
      }
    }
    return null;
  }

  public isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  }

  dismiss(): void {
    if (this.drawerRef) {
      this.drawerRef.close();
    }
    this.cancelEvt.emit();
  }

  close(): void {
    if (this.drawerRef) {
      this.drawerRef.close();
    }
  }

  onConfirm(): void {
    this.isValidated = true;
    this.inputForm.form.markAllAsTouched();
    Object.values(this.inputForm.controls).forEach(control => {
      control.markAsTouched();
      control.updateValueAndValidity();
    });
    this.cdr.markForCheck();
    const isJsonTypeInvalid = this.inputs.some(obj => this.type !== 'mcp' && obj.depth === 0 && !obj.visibility && obj.type?.startsWith('array') && obj.value?.content === '' && obj.required);
    if (this.inputForm.form.invalid || isJsonTypeInvalid) {
      return;
    }
    const inputs = NodeUtils.getDtoInputs(this.inputs, {
      useContentType: false,
      handleRef: false,
    });
    this.handleInputParams(inputs);
    this.detail.params = this.handleSubmitParamers(inputs);
    this.confirm.emit({ conf: this.detail, type: this.type });
    this.close();
  }

  // 处理入参数据
  private handleInputParams(inputs: IWorkflowField[]) {
    for (let index = 0; index < inputs.length; index++) {
      const contents = inputs[index]?.value?.content || [];
      let isInputParam = false;
      if (!Array.isArray(contents)) {
        continue;
      }
      let originType = inputs[index].value.type;
      for (let i = 0; i < contents.length; i++) {
        if (contents[i].input_type) {
          isInputParam = true;
          break;
        }
      }
      if (isInputParam) {
        inputs[index].value.type = 'input_ref';
      } else {
        inputs[index].value.type = originType;
      }
    }
  }

  handleSubmitParamers(inputs) {
    //todo 需确认有多余字段是否可以，在此进行处理
    inputs.forEach(input => {
      if (
        input.value.type === 'literal' &&
        ['number', 'integer'].includes(input.type) &&
        typeof input.value.content !== 'number' &&
        input.value.content !== ''
      ) {
        input.value.content = Number(input.value.content);
      }
      input.required = input.showRequired;
      if (input.children) {
        this.handleSubmitParamers(input.children);
      }
      if (input.options) {
        delete input.options;
      }
      delete input.showRequired;
    });
    return inputs;
  }

  getReqLayerIndexWidth(param: IRequestArgsView) {
    const map = {
      0: '200px',
      1: '176px',
      2: '152px',
      3: '128px',
    };

    const mapWithChildren = {
      0: '180px',
      1: '156px',
      2: '132px',
    };

    return param?.children ? mapWithChildren[param.depth] : map[param.depth];
  }

  onNgModelChange($event, param) {
    if (param.type === 'object' && param.children.length) {
      param.children.forEach(item => {
        item.required = !$event;
      });
    } else {
      param.required = !$event;
    }
  }

  public getTableWidth() {
    if (this.type === 'mcp') {
      return {
        name: '130px',
        nameTitle: '156px',
        description: '100px',
        required: '8%',
        default: '40%',
      };
    }
    return {
      name: '110px',
      nameTitle: '136px',
      description: '75px',
      required: '8%',
      default: '40%',
      visibility: '65px',
    };
  }

  public getModalTitle() {
    if (this.type === 'mcp') {
      return 'mcp_parameter_configuration';
    }
    if (this.type === 'tool') {
      return 'plugin_parameter_configuration';
    }
    if (this.type === 'workflow') {
      return 'plugin-config-modal_1';
    }
    return 'plugin-config-modal_1';
  }

  public getName(data) {
    if (!data || !data.content) {
      return {
        key: '',
        type: '',
        value: '',
      };
    }
    if (Array.isArray(data.content) && !data.content[0].input_type) {
      return {
        key: data.content[0].variable_key,
        type: 'String',
        value: data.content[0].default_value,
      };
    }
    if (Array.isArray(data.content) && data.content[0].input_type) {
      return {
        key: data.content[0].variable_key,
        type: data.content[0].input_type,
        value: data.content[0].default_value,
      };
    }
    return {
      key: '',
      type: '',
      value: '',
    };
  }
}
