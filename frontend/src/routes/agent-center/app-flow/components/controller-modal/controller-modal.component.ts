import {
  ChangeDetectorRef,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  OnInit,
  Output,
  TemplateRef,
  ViewChild,
} from '@angular/core';
import { FormBuilder, NgForm } from '@angular/forms';
import { NzModalRef, NzModalService } from 'ng-zorro-antd/modal';
import { NzDrawerService, NzDrawerRef } from 'ng-zorro-antd/drawer';

interface PageSizeConfig {
  options: number[];
  size: number;
  hide?: boolean;
}

interface TableColumns {
  title?: string;
  width?: string;
}

interface TableRowData {
  [key: string]: any;
}

interface TableSrcData {
  data: TableRowData[];
  state?: any;
}

interface ValidationConfig {
  errorMessage?: {
    required?: string;
  };
  type?: string;
}
import { I18nNamespace } from '@i18n';
import { AppFlowRepoService } from '@services/agent-center/app-flow-repo.service';
import {
  NonEmptyValidatorDirective,
  ValueValidityValidatorDirective,
  VariableNameValidatorDirective,
} from '@shared/directives/variable-name-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep, isNil } from 'lodash';
import { debounceTime, Subject, Subscription, takeUntil } from 'rxjs';
import { v4 as uuidV4 } from 'uuid';

import { AppFlowService } from '../../app-flow.service';
import { IModel, IRefWorkflows } from '../../app-flow.types';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import type {
  ControllerSubFlowType,
  FlowAction,
  IControllerFlow,
  IControllerNode,
  IEndNode,
  IGlobalIntent,
  IIntentHandler,
  IStartNode,
  IWorkflowField,
  IWorkflowFieldValue,
  IWorkflowNode,
} from '../../node.type';
import { AccBlockComponent } from '../acc-block/acc-block.component';
import { ModalBaseComponent } from '../base/modal-base.component';
import { ParamSelectorComponent } from '../param-selector/param-selector.component';
import { NodeUtils } from '../utils';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import { isSystemTypeWithNames } from '@routes/agent-center/utils';
import { AssetIntelligentAddComponent } from '@shared/components/assets/asset-intelligent-add/asset-intelligent-add.component';
import { AssetIntelligentAddDisabledComponent } from '@shared/components/assets/asset-intelligent-add-disabled/asset-intelligent-add-disabled.component';
import { RefPromptComponent } from '@routes/agent-center/ref-prompt/ref-prompt.component';
import { ITmpl } from '@services/prompt.service';
import { LLMSelectComponent } from '@routes/agent-center/app-flow/components/llm-select/llm-select.component';
import { AgentDataService } from '@services/agent-center/agent-data.service';
import { GETVARIANT_REG } from '@constants/exp-tmpl-config.const';
import { CandidateTemplateListService } from '@services/candidate-template-list.service';
import moment from 'moment';
import { ActivatedRoute } from '@angular/router';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';
import { SubControllerService } from '@services/agent-center/sub-controller.service';
import { FlowItemComponent } from './flow-item/flow-item.component';
import { AddChildFlowModalComponent } from '../add-child-flow-modal/add-child-flow-modal.component';
import { AddMultipleAgentModalComponent } from './add-multiple-agent-modal/add-multiple-agent-modal.component';

import { CommonService } from '@services/common.service';
import { NodeDescriptionComponent } from '../node-description/node-description.component';
import {ApplicationType} from "@enums/agent-center.enum";
import {CONTROLLER_SUB_FLOW_LIMIT, SubAgentModel, SubApplication, SubWorkFlow} from "@routes/agent-center/app-flow/components/controller-modal/controller-modal.interface";
import { OptimizePromptModalComponent } from '@routes/agent-center/app-agent/components/optimize-prompt-modal/optimize-prompt-modal.component';
import { SaveTmplLibraryModalComponent } from '@routes/prompt/prompt-candidate-template/save-tmpl-library-modal/save-tmpl-library-modal.component';

const SUBFLOW_LIMIT = CONTROLLER_SUB_FLOW_LIMIT;

interface INeedUpdateFlow extends IRefWorkflows {
  version_id: string;
  old_inputs: IWorkflowField[];
}

const CHAT_HISTORY_MAX_TURN_DEFAULT = 20;

const MAX_ITERATION_DEFAULT = 9;

@Component({
  selector: 'meta-controller-modal',
  templateUrl: './controller-modal.component.html',
  styleUrls: ['./controller-modal.component.less', '.././common-styles.less'],
  standalone: true,
  imports: [
    MODULES,
    AccBlockComponent,
    VariableNameValidatorDirective,
    NonEmptyValidatorDirective,
    ValueValidityValidatorDirective,
    ParamSelectorComponent,
    LLMSelectComponent,
    AssetIntelligentAddComponent,
    AssetIntelligentAddDisabledComponent,
    FlowItemComponent,
    AddMultipleAgentModalComponent,
    NodeDescriptionComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class ControllerModalComponent
  extends ModalBaseComponent
  implements OnInit, OnDestroy {
  @Input('names') names: string[];

  @Input('nodeInfo') nodeInfo: IControllerNode;

  @Input() outputs: {
    confirm?: (data: IControllerNode) => void;
    closeDrawer?: () => void;
    editCodeEvent?: (data: any) => void;
  } = {};

  @ViewChild('intentForm') intentForm: NgForm;

  @ViewChild('subFlowForm') subFlowForm: NgForm;

  @ViewChild('updateVersionModal')
  updateVersionModal: TemplateRef<HTMLDivElement>;

  @ViewChild('updateVersionModalFooter')
  updateVersionModalFooter: TemplateRef<HTMLDivElement>;

  @Output('confirm') confirm = new EventEmitter<IControllerNode>();

  displayeIntentdData: Array<TableRowData> = [];

  srcData: TableSrcData = {
    data: [],
    state: undefined,
  };

  columns: Array<TableColumns> = [
    {
      title: this.i18n.transform('controllermodalcomponent_303'),
    },
    {
      title: this.i18n.transform('controllermodalcomponent_304'),
    },
    {
      title: this.i18n.transform('controllermodalcomponent_305'),
    },
    {
      title: this.i18n.transform('controllermodalcomponent_306'),
    },
  ];

  public iconUrl = WORKFLOW_SVGS.Controller;

  public modelFormGroup = this.fb.group({
       model: [''],
  });

  public modelParams = {
    top_p: 0.5,
    temperature: 0.5,
  };

  public modelListSubscription: Subscription;

  public modelOptions: IModel[] = [];

  public modelName = '';

  public prompt = '';

  public description = '';

  public flowOps: SubWorkFlow[] = [];

  public subFlowOps: SubWorkFlow[] = [];

  public isLoadingFlows = false;

  public startFlow: any;
  public startFlowId = '';
  public startFlowName = '';

  public intentFlow: any;
  public intentFlowId = '';
  public intentFlowName = '';

  public intent_name: string = '';
  public intent_desc: string = '';

  public defaultFlowCtx: any = {
  };
  public defaultFlowName = '';
  public defaultFlow: any;

  public endFlow: any;
  public endFlowId = '';
  public endFlowName = '';

  public subFlowCtx: SubWorkFlow[] = [];
  public associationAgentCtx: SubAgentModel[] = [];

  public intents: IGlobalIntent[] = [];

  public intentTypeOps = [
    { label: this.i18n.transform('process_jump'), value: 'Workflow' },
    { label: this.i18n.transform('direct_response'), value: 'Text' },
  ];

  public intentActionOps = [
    { label: this.i18n.transform('continue'), value: 'Continue' },
    { label: this.i18n.transform('termination'), value: 'Terminal' },
    { label: this.i18n.transform('waiting_for_input'), value: 'WaitUserInput' },
  ];

  public flowInfoMap = new Map<string, IWorkflowNode>();
  public select_agent_detail_map = new Map();

  public promptPlaceholder = this.i18n.transform(
    'controller_prompt_placeholder',
  );

  public needUpdateFlowCtx: INeedUpdateFlow[] = [];

  public displayedData: TableRowData[] = [];

  public tableSrcData: TableSrcData = {
    data: [],
    state: undefined,
  };

  public hasTitleCols: TableColumns[] = [
    {
      title: this.i18n.transform('workflow_name'),
    },
    {
      title: this.i18n.transform('current_version'),
    },
    {
      title: this.i18n.transform('latest_version'),
    },
  ];

  public tableCols: TableColumns[] = [
    {
      title: '',
    },
    ...this.hasTitleCols,
  ];

  public pageSize: PageSizeConfig = {
    options: [6, 12, 18, 24],
    size: 6,
    hide: true,
  };

  public currentPage = 0;

  /**
   * @type INeedUpdateFlow[]
   */
  public checkedFlows: any = [];

  public allChecked = false;

  public indeterminate = false;

  public updateModal: NzModalRef = null;
  public drawerRef: NzDrawerRef = null;

  public modelValidation: ValidationConfig = {
    errorMessage: {
      required: this.i18n.transform('select_model'),
    },
    type: 'changeAlert',
  };

  public chatHistoryMaxTurn = CHAT_HISTORY_MAX_TURN_DEFAULT;

  public maxIteration = MAX_ITERATION_DEFAULT;

  private isLoadingFlowData = false;

  private isTriggeredConfirm = false;

  protected override destroy$ = new Subject<void>();

  private paramsId: string;

  public router_params: any = {
    id: '',
  };

  public readOnly = false;

  get mutilagent_max_iteration() {
    return this.configServ.getConfigs().mutilagent_max_iteration ?? 30;
  }
  new_scales = [10, 20, 30];
  showUpdatedIcon = false;
  relations = [];
  intent_params_detail_rule_link = '';

  constructor(
    private fb: FormBuilder,
    private nzModal: NzModalService,
    private appAgentRepoServe: AppAgentRepoService,
    protected override appFlowServ: AppFlowService,
    protected override nodeServ: NodeService,
    private appFlowRepoServe: AppFlowRepoService,
    private i18n: I18NextEagerPipe,
    private agentDataServe: AgentDataService,
    private candidateTemplateListServe: CandidateTemplateListService,
    private route: ActivatedRoute,
    private configServ: AgentConfigService,
    private nzDrawer: NzDrawerService,
    private readonly commonService: CommonService,
    private subControllerService: SubControllerService,
    private cd: ChangeDetectorRef,
  ) {
    super(nodeServ, appFlowServ);
  }

  async ngAfterViewInit() {
    this.route.queryParams.subscribe((params) => {
      this.router_params = params;
    });
    try {
      let info = JSON.parse(localStorage.getItem('multiFlowTypeInfo'));
      if (info?.id) {
        const flow: IControllerFlow = {
          node_id: '',
          id: info.id,
          name: info.name || '',
          type: 'Normal',
          description: info.description || '',
          version: info.version,
          version_id: info.version,
          version_name: info.version_name,
          code: info.code || '',
        };
        if (info.multiFlowType === 'intentFlow') {
          await this.onSelectFlow(flow, 'IntentIdentification');
          this.intentFlow = flow;
          this.intentFlowId = flow.id;
        }
        if (info.multiFlowType === 'startFlow') {
          await this.onSelectFlow(flow, 'Start');
          this.startFlow = flow;
          this.startFlowId = flow.id;
        }
        if (info.multiFlowType === 'endFlow') {
          await this.onSelectFlow(flow, 'End');
          this.endFlow = flow;
          this.endFlowId = flow.id;
        }
        if (info.multiFlowType === 'defaultFlow') {
          if (!flow.action) {
            flow.action = 'Continue';
          }
          await this.onSelectFlow(flow, 'Default');
          this.defaultFlow = flow;
          this.defaultFlowCtx.id = flow.id;
          this.defaultFlowCtx.action = flow.action;
        }
        if (info.multiFlowType === 'subWorkflow') {
          const sub: SubWorkFlow = {
            node_id: '',
            id: info.id,
            name: info.name || '',
            type: 'Normal',
            subAgentType: ApplicationType.WORKFLOW,
            flowType: info.type,
            description: info.description || '',
            version_id: info.version,
            version_name: info.version_name,
            code: info.code || '',
            action: 'Continue',
          };
          await this.onSelectFlow(sub, 'Normal');
          this.subFlowCtx.push(sub);
        }
        localStorage.removeItem('multiFlowTypeInfo');
      }
    } catch {
    }
  }

  public override ngOnInit() {
    this.new_scales = this.mutilagent_max_iteration === 30 ? [0, 10, 20, 30] : [0, 25, 50, 75, 100]
    this.route.queryParams.subscribe((params) => {
      this.paramsId = params.id;
    });
    if (
      !this.nodeInfo.configs?.model?.id &&
      this.nodeInfo.configs?.model?.model_deployment_id
    ) {
      this.nodeInfo.configs.model.id =
        this.nodeInfo.configs.model.model_deployment_id;
    }
    this.setNodeBase(this.nodeInfo);
    super.ngOnInit();

    this.readOnly = this.nodeInfo.type === 'SubController';

    this.description = this.nodeInfo.configs.description;

    this.modelName = this.nodeInfo.configs?.model.model_name;

    const flowIntents = this.nodeInfo.configs.global_intents.filter(
      (intent) => intent.handler_type === 'Workflow',
    );
    const resource = this.appFlowServ.getAppRefs();
    flowIntents.forEach((intent) => {
      const { id, configs } = intent.handler as IWorkflowNode;
      const matchedFlow = resource.find((flow) => {
        if (
          flow.workflow_id === id &&
          flow.resource_version === configs.version_id &&
          flow.last_version_id !== configs.version_id
        ) {
          return true;
        }

        return false;
      });

      if (matchedFlow) {
        this.needUpdateFlowCtx.push({
          ...matchedFlow,
          version_id: (intent.handler as IWorkflowNode)?.configs?.version_id,
          old_inputs: (intent.handler as IWorkflowNode)?.inputs,
        });
      }
    });

    this.modelListSubscription = this.appFlowServ
      .modelListUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((models) => {
        this.modelOptions = models ?? [];
      });
    this.modelFormGroup.setValue({
      model: this.nodeInfo.configs?.model?.id ?? '',
    });
    if (!this.nodeInfo.configs.fromShare) {
      NodeUtils.checkModelExistence(
        this.nodeInfo.name,
        this.nodeInfo.configs?.model?.id ?? '',
        this.modelOptions,
      );
    }
    const { top_p = 0.5, temperature = 0.5 } = this.nodeInfo.configs;
    this.modelParams = { top_p, temperature };

    this.initAgents();
    this.getFlows();
    this.handleWorkflow();
    this.initIntents();

    this.srcData.data = this.intents;
    this.displayeIntentdData = this.intents;
    this.agentDataServe.setPromptAndModelConfig({
      modelConfig: this.nodeInfo.configs?.model,
    });
    this.intent_name = this.nodeInfo.configs?.intent?.name ?? ''
    this.intent_desc = this.nodeInfo.configs?.intent?.description ?? '';
  }

  get_handler_type(type) {
    const ops = this.intentTypeOps.filter((item) => item.value === type);
    return ops[0].label ?? '';
  }
  get_action(action) {
    const ops = this.intentActionOps.filter((item) => item.value === action);
    return ops[0].label ?? '';
  }

  dismiss(): void {
    this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    this.outputs?.closeDrawer?.();
  }

  handleWorkflow() {
    let newWorkflows = [];
    if (this.nodeInfo.type === 'SubController') {
      for (let i = 0; i < this.nodeInfo.configs.workflows.length; i++) {
        let workflow = this.nodeInfo.configs.workflows[i];
        if (workflow) {
          if (
            workflow.type === 'IntentIdentification' ||
            workflow.type === 'Start' ||
            workflow.type === 'End' ||
            workflow.type === 'Default' ||
            workflow.type === 'Normal'
          ) {
            newWorkflows.push(workflow);
          }
        }
      }
    } else {
      for (let i = 0; i < this.nodeInfo.configs.workflows.length; i++) {
        let workflow = this.nodeInfo.configs.workflows[i];
        if (
          workflow.type === 'IntentIdentification' ||
          workflow.type === 'Start' ||
          workflow.type === 'End' ||
          workflow.type === 'Default' ||
          workflow.type === 'Normal'
        ) {
          newWorkflows.push(workflow);
        }
      }
    }

    this.nodeInfo.configs.workflows = newWorkflows;
    const intentIdentificationFlow = this.nodeInfo.configs?.workflows?.find(
      (flow) => flow.type === 'IntentIdentification',
    );

    if (intentIdentificationFlow) {
      this.intentFlowId = intentIdentificationFlow.id;
      this.intentFlowName = intentIdentificationFlow.name;
      const { configs = {}, ...rest } = intentIdentificationFlow;
      this.intentFlow = {
        ...rest,
        ...configs,
      };
    }

    const startFlow = this.nodeInfo.configs?.workflows?.find(
      (flow) => flow.type === 'Start',
    );
    if (startFlow) {
      this.startFlowId = startFlow.id;
      this.startFlowName = startFlow.name;
      const { configs = {}, ...rest } = startFlow;
      this.startFlow = {
        ...rest,
        ...configs,
      };
    }

    const endFlow = this.nodeInfo.configs?.workflows?.find(
      (flow) => flow.type === 'End',
    );
    if (endFlow) {
      this.endFlowId = endFlow.id;
      this.endFlowName = endFlow.name;
      const { configs = {}, ...rest } = endFlow;
      this.endFlow = {
        ...rest,
        ...configs,
      };
    }

    const defaultFlow = this.nodeInfo.configs.workflows.find(
      (flow) => flow.type === 'Default',
    );
    if (defaultFlow) {
      this.defaultFlowCtx = {
        id: defaultFlow.id,
        action: defaultFlow?.action ?? 'Continue',
        type: '',
      };
      const { configs = {}, ...rest } = defaultFlow;
      this.defaultFlow = {
        ...rest,
        ...configs,
      };
      this.defaultFlowName = defaultFlow.name;
    }

    this.subFlowCtx = this.nodeInfo.configs.workflows
      .filter((flow) => flow.type === 'Normal')
      .map((flow) => {
        const { configs } = flow;
        return {
          id: flow.id,
          node_id: flow.node_id,
          name: flow.name,
          type: flow.type,
          flowType: flow.flowType ?? 'chat',
          subAgentType: ApplicationType.WORKFLOW,
          description: configs.description,
          version_id: configs.version_id,
          version_name: configs.version_name,
          checked: true,
          action: flow?.action ?? 'Continue',
          code: configs.code,
          valid: configs.valid ?? true,
        };
      });

    this.prompt = this.nodeInfo.configs.prompt || this.promptPlaceholder;
    if (!isNil(this.nodeInfo.configs?.chat_history_max_turn)) {
      this.chatHistoryMaxTurn = this.nodeInfo.configs?.chat_history_max_turn;
    }

    if (!isNil(this.nodeInfo.configs?.max_iteration)) {
      this.maxIteration = this.nodeInfo.configs.max_iteration;
    }
    this.getMutilAgentLastVersionFn();
  }

  addSubFlow() {
    if (this.subFlowCtx.length < SUBFLOW_LIMIT) {
      this.addIntentFlow('subWorkflow');
    }
  }
  addAssociationAgent() {
    if (this.associationAgentCtx.length < SUBFLOW_LIMIT) {
      this.addAgent();
    }
  }

  private initAgents() {
    if (!this.nodeInfo.configs?.agents?.length) {
      return;
    }

    this.associationAgentCtx = this.nodeInfo.configs.agents?.map(
      (agent) => {
        const { configs } = agent;
        const applicationType = agent.mode === 'PlanExecute'
          ? ApplicationType.SINGLE_AGENT : ApplicationType.MULTI_AGENT;

        return {
          id: agent.id,
          node_id: agent.node_id,
          name: agent.name,
          mode: agent.mode,
          type: configs.type,
          subAgentType: applicationType,
          description: configs.description,
          version_id: configs.version_id,
          version_name: configs.version_name,
          checked: true,
          valid: configs.valid ?? true,
        };
      },
    );

    for (let i = 0; i < this.nodeInfo.configs?.agents.length; i++) {
      const agents = this.nodeInfo.configs.agents[i];
      const version_id = agents?.configs?.version_id ?? '';
      this.setPublishedSubAgentDetails(agents.id, version_id);
    }
  }

  onConfirm(): void {
    const detail_map = this.select_agent_detail_map.entries();
    const obj = {};
    for (const [key, value] of detail_map) {
      obj[key] = value;
    }
    StorageService.setSessionStorage('detail_map', JSON.stringify(obj));
    if (
      this.subFlowForm
      && !this.subFlowForm.valid
    ) {
      this.subFlowForm.control.markAllAsTouched();
      return;
    }
    if (
      !this.intentForm.valid
    ) {
      this.intentForm.control.markAllAsTouched();
      return;
    }

    if (this.isLoadingFlowData) {
      this.isTriggeredConfirm = true;
      return;
    } else {
      this.isTriggeredConfirm = false;
    }
    this.handelSave();
    this.appFlowServ.setNodeModalCloseMonitor({ id: this.nodeInfo.id });
    this.outputs?.closeDrawer?.();
  }

  getWorkflows() {
    let flows: IControllerFlow[] = [];
    if (this.intentFlowId) {
      flows.push(
        this.getFlowInfoById(this.intentFlowId, {
          type: 'IntentIdentification',
        }),
      );
    }

    if (this.startFlowId) {
      flows.push(
        this.getFlowInfoById(this.startFlowId, {
          type: 'Start',
        }),
      );
    }

    this.subFlowCtx.forEach((flow) => {
      if (flow?.id) {
        flows.push(
          this.getFlowInfoById(flow.id, {
            type: 'Normal',
            action: flow.action,
          }),
        );
      }
    });

    if (this.defaultFlow?.id) {
      flows.push(
        this.getFlowInfoById(this.defaultFlowCtx.id, {
          type: 'Default',
          action: this.defaultFlow.action,
        }),
      );
    }

    if (this.endFlowId) {
      flows.push(
        this.getFlowInfoById(this.endFlowId, {
          type: 'End',
        }),
      );
    }
    if (flows[0] == null) {
      flows = [];
    }
    return flows;
  }

  getAgents() {
    const newAgents = [];
    this.associationAgentCtx.forEach((agent) => {
      const newAgent = agent.subAgentType === ApplicationType.MULTI_AGENT
        ? this.getSubMultiAgent(agent) : this.getSubSingleAgent(agent);
      newAgents.push(...newAgent);
    });
    return newAgents;
  }

  private getSubMultiAgent(res) {
    const agentId = res.id;
    const agentInfo = this.select_agent_detail_map.get(agentId);
    const controller = agentInfo?.details?.nodes.find(
      (item) => item.id === 'controller',
    );

    if(!controller){
      return [];
    }

    // 添加agents的configs的信息
    controller.configs = {
      ...res,
      ...controller?.configs,
      intent: res.intent
    };

    // 添加workflow的config
    const controllerFlows = agentInfo?.details?.nodes.filter(
      (item) => item.type === 'Workflow',
    );

    // 使用 map 替代双重循环
    controller.configs.workflows = controller.configs.workflows
      .map((wf) => {
        // nodeId会变，使用id进行匹配
        const matchedFlow = controllerFlows.find(matchFlow =>
          matchFlow.configs?.id === wf.configs?.id
        );
        if (!matchedFlow) return null; // 未找到匹配项时跳过

        return {
          id: wf.id,
          node_id: this.getNewFleshAgWorkflow(wf.node_id),
          name: wf.name,
          configs: {
            ...matchedFlow.configs,
            fromShare: matchedFlow.configs.fromShare || res.fromShare,
          },
          type: wf.type,
          inputs: matchedFlow.inputs,
          outputs: matchedFlow.outputs,
          parent_node_type: 'sub_controller',
        };
      }).filter(Boolean);

    const agent = {
      node_id: `sub_controller_${uuidV4()}`,
      id: agentId,
      name: agentInfo.name ?? this.i18n.transform('controllermodalcomponent_309'),
      mode: 'Controller',
      type: ApplicationType.MULTI_AGENT,
      configs: {
        ...controller.configs,
        fromShare: res.fromShare,
      },
    };
    return [agent];
  }

  private getSubSingleAgent(agent) {
    const agentInfo = this.select_agent_detail_map.get(agent.id);
    const agentDetail = {
      node_id: `node_${uuidV4()}`,
      id: agentInfo.agent_id,
      name: agentInfo.name,
      mode: 'PlanExecute',
      type: 'agent',
      configs: {
        node_id: '',
        id: agentInfo.agent_id,
        name: agentInfo.name,
        mode: 'PlanExecute',
        type: ApplicationType.SINGLE_AGENT,
        description: agentInfo.description,
        version: agent.version_id,
        version_id: agent.version_id,
        version_name: agent.version_name,
        model: {
          model_name: agentInfo.model_name,
          model_type: agentInfo.model_type,
          id: agentInfo.model_deployment_id,
          model_deployment_id: agentInfo.model_deployment_id,
        },
        workflows: agentInfo.workflows,
        agents: []
      }
    };

    return [agentDetail];
  }

  getNewFleshAgWorkflow(node_id) {
    const type = node_id.split('_')[0];
    const nodeIdMap = {
      start: `start_${uuidV4()}`,
      end: `end_${uuidV4()}`,
      node: `node_${uuidV4()}`,
      default: `default_${uuidV4()}`,
      intentIdentification: `intentIdentification_${uuidV4()}`,
    };

    return nodeIdMap[type];
  }

  getFlowInfoById(
    flowId: string,
    configs: {
      type: ControllerSubFlowType;
      action?: FlowAction;
    },
  ): IControllerFlow {
    const originalFlow = this.nodeInfo.configs.workflows.find(
      (f) => f.type === configs.type && f.id === flowId,
    );

    const newFlow = this.flowInfoMap.get(`${flowId}_${configs.type}`);

    if (originalFlow) {
      if (!newFlow) {
        if (
          ['Start', 'End'].includes(configs.type) ||
          (originalFlow?.action && originalFlow.action === configs.action)
        ) {
          return originalFlow;
        }

        return {
          ...originalFlow,
          action: configs.action,
        };
      }

      return this.getFreshFlow(newFlow, configs);
    }

    if (newFlow) {
      return this.getFreshFlow(newFlow, configs);
    }

    return null;
  }

  getFreshFlow(
    flow: IWorkflowNode,
    configs: {
      type: ControllerSubFlowType;
      action?: FlowAction;
    },
  ) {
    const { type, action } = configs;
    const { name, id, inputs, outputs, configs: flowConfigs } = flow ?? {};

    const nodeIdMap = {
      Start: `start_${uuidV4()}`,
      End: `end_${uuidV4()}`,
      Normal: `node_${uuidV4()}`,
      Default: `default_${uuidV4()}`,
      IntentIdentification: `intentIdentification_${uuidV4()}`,
    };

    return {
      node_id: nodeIdMap[type],
      type,
      name,
      id,
      inputs,
      outputs,
      configs: flowConfigs,
      action,
    };
  }

  isReachedAddSubFlowLimit() {
    return this.subFlowCtx.length === SUBFLOW_LIMIT;
  }
  isReachedAddAssociationAgentLimit() {
    return this.associationAgentCtx?.length === SUBFLOW_LIMIT;
  }

  trackByFn(index: number) {
    return index;
  }

  isFlowHandler(handler: IIntentHandler): handler is IWorkflowNode {
    return typeof handler === 'object' && handler !== null;
  }

  onChangeHandlerType(intent: IGlobalIntent) {
    if (intent.handler_type === 'Text') {
      intent.handler = '';
    } else {
      intent.handler = {
        id: '',
        name: '',
        type: 'Workflow',
        inputs: [],
        outputs: [],
        configs: {
          id: '',
          name: '',
          version_id: '',
          version_name: '',
          description: '',
          code: '',
        },
      };
    }
  }

  addIntent() {
    this.intents.push({
      id: `${Date.now()}`,
      name: '',
      description: '',
      handler_type: 'Text',
      handler: '',
      action: 'Terminal',
    });
    this.displayeIntentdData = [...this.intents];
  }

  gotoWorkflow(id: string) {
    const urlFragement = window.location.href.split('?id=');
    if (urlFragement.length) {
      window.open(`${urlFragement[0]}?id=${id}`, '_black');
    }
  }

  deleteIntent(index: number) {
    this.intents.splice(index, 1);
    this.displayeIntentdData = [...this.intents];
  }

  async onSelectFlowSelected(e: any) {
    const findItem = this.flowOps.find(item => item.id === e);
    this.onSelectFlow(findItem, 'Intent');
  }

  async onSelectFlow(flow: any, type: ControllerSubFlowType, isUpdate = false) {
    if (!this.flowInfoMap.get(`${flow.id}_${type}`)) {
      this.isLoadingFlowData = true;
      const f: any = await this.appFlowRepoServe.getFlowVersionInfo(
        flow.id,
        flow.version,
      ) || {};
      flow.code = f.code ?? '';
      flow.description = f.description ?? '';
      flow.name = f.name ?? '';
      this.cd.markForCheck();
      this.isLoadingFlowData = false;

      const { id = '', nodes = [] } = f.workflow_details || {};

      const inputs: IWorkflowField[] = (
        nodes.find((item) => item.type === 'Start') as IStartNode
      )?.outputs?.filter(
        (item) => !isSystemTypeWithNames(item, ['conversation_history', 'sys']),
      ) ?? [];
      inputs.forEach((item) => {
        const { default: defaultValue } = item.value;
        const content = isNil(defaultValue) ? '' : defaultValue;
        const value: IWorkflowFieldValue = {
          content,
          hint: '',
          type: 'literal',
        };

        if (!isNil(defaultValue)) {
          value.default = defaultValue;
        }

        item.value = value;
      });

      this.flowInfoMap.set(`${flow.id}_${type}`, {
        id,
        name: f.name,
        type: 'Workflow',
        inputs,
        outputs: (nodes.find((item) => item.type === 'End') as IEndNode)
          .outputs,
        configs: {
          id,
          name: flow.name,
          description: f.description,
          version_id: flow.version_id,
          version_name: flow.version_name,
          code: f.code,
          fromShare: flow.fromShare,
        },
      });

      if (flow.update) {
        flow.update = null;
      }
      if (this.isTriggeredConfirm) {
        this.onConfirm();
      }
      if (isUpdate) {
        this.handelSave();
      }
    }
  }

  private async onSelectSubAgent(agentInfo, isUpdate = false) {
    if (!agentInfo) {
      return;
    }
    await this.setPublishedSubAgentDetails(agentInfo.id, agentInfo.version_id);
    if (agentInfo.update) {
      agentInfo.update = null;
      this.cd.markForCheck();
    }
    if (isUpdate) {
      this.handelSave();
    }
  }

  private async setPublishedSubAgentDetails(agentId: string, versionId: string) {
    return this.appFlowRepoServe.getPublishedMutilAgentDetails(
      agentId,
      versionId,
    ).then(res => {
      this.select_agent_detail_map.set(agentId, res);
      return Promise.resolve(res);
    });
  }

  onIntentNameChange() {
    window.setTimeout(() => {
      this.intentForm?.form?.markAllAsTouched();
    });
  }

  openUpdateModal() {
    this.tableSrcData.data = this.needUpdateFlowCtx;

    this.updateModal = this.nzModal.create({
      nzTitle: '',
      nzContent: this.updateVersionModal,
      nzClassName: 'update-version-modal',
      nzFooter: this.updateVersionModalFooter,
    });
  }

  dismissUpdateModal(): void {
    this.updateModal?.close();
  }

  confirmUpdate() {
    Promise.all(
      (this.checkedFlows as INeedUpdateFlow[]).map((flow) =>
        this.appAgentRepoServe.rollbackFlowVersion(
          flow.workflow_id,
          flow.last_version_id,
        ),
      ),
    ).then((workflows) => {
      workflows.forEach((flow) => {
        const startNode = flow?.workflow_details?.nodes?.filter(
          (node) => node.type === 'Start',
        );
        const endNode = flow?.workflow_details?.nodes?.filter(
          (node) => node.type === 'End',
        );

        const { old_inputs, last_version_id, last_version_name } =
          this.needUpdateFlowCtx.find(
            (flowCtx) => flowCtx.workflow_id === flow.workflow_id,
          );
        const newIputs = startNode?.[0]?.outputs;
        const updatedInputs = this.fillPreviousInputs(newIputs, old_inputs);
        const { workflow_id, name, description, code } = flow;

        const newHandler: IWorkflowNode = {
          id: workflow_id,
          inputs: updatedInputs,
          outputs: endNode?.[0]?.outputs,
          type: 'Workflow',
          name,
          configs: {
            id: workflow_id,
            name,
            description,
            version_id: last_version_id,
            version_name: last_version_name,
            code,
          },
        };

        this.nodeInfo.configs.global_intents.forEach((intent) => {
          if (
            intent.handler_type === 'Workflow' &&
            (intent.handler as IWorkflowNode).id === workflow_id
          ) {
            intent.handler = newHandler;
          }
        });
      });

      this.initIntents();
      this.appFlowServ.setSilentUpdateNodeData({
        nodeInfo: this.nodeInfo,
        successCb: () => {
          this.needUpdateFlowCtx = this.needUpdateFlowCtx.filter(
            (ctx) => !(this.checkedFlows as INeedUpdateFlow[]).includes(ctx),
          );
          this.checkedFlows = [];
          this.allChecked = false;
          this.indeterminate = false;
          this.cd.markForCheck();

          MessageComponent.showSuccess(this.i18n.transform('update_success'));
          this.updateModal?.destroy();
        },
      });
    });
  }

  public getmodelStatus(is_connecting) {
    if (is_connecting) {
      return this.i18n.transform('running');
    }

    return this.i18n.transform('call_failed');
  }

  private fillPreviousInputs(
    newIputs: IWorkflowField[],
    oldInputs: IWorkflowField[],
  ) {
    return newIputs
      ?.map((item) => {
        const matchingItem = oldInputs?.find(
          (inputItem) =>
            inputItem.name === item.name && inputItem.type === item.type,
        );
        return matchingItem ?? item;
      })
      .filter((input) => input.name !== 'sys');
  }

  private initIntents() {
    this.intents = cloneDeep(this.nodeInfo.configs?.global_intents)?.map(
      (intent) => {
        if (intent.action) {
          return intent;
        }

        return {
          ...intent,
          action: intent.termination ? 'Terminal' : 'Continue',
        };
      },
    ) ?? [];
  }

  public updateModel(modelInfo: any) {
    this.modelFormGroup.controls.model.setValue(modelInfo.id);
  }
  /** 处理"保存候选模板作为正式模板"接口中的入参variables */
  public processString(input: string): string {
    const matches = input.match(GETVARIANT_REG);
    if (matches) {
      const extractedValues = matches.map((match) => match.slice(2, -2));
      return extractedValues.join(',');
    }
    return '';
  }

  public showSaveTmplModal() {
    if (this.prompt && this.prompt.length > 0) {
    const thisMOdal = this.nzModal.create({
      nzContent: SaveTmplLibraryModalComponent,
      nzWidth: 600,
      nzData: {
        currentTmpl: {
          is_workflow: true,
          created_on: moment().format('YYYY-MM-DD HH:mm:ss'),
          content: this.prompt,
          model_config: {
            temperature: null,
            top_p: null,
            max_tokens: null,
            presence_penalty: null,
          },
        },
        // 调用接口，保存候选模板作为正式模板
        modalClose: form => {
          const params = {
            task_id: this.paramsId,
            id: '',
            name: form.value.templateName,
            tags: form.value.tags,
            industry_id: form.value.industrys,
            content: this.prompt,
            source: 'PLAYGROUND',
            variables: this.processString(this.prompt),
          };
          this.candidateTemplateListServe.saveFormalTmpl(params).subscribe({
            next: (res) => {
              MessageComponent.showSuccess(
                this.i18n.transform('single_tmpl_save_success_tip'),
              );
            },
          });
          this.cd.markForCheck();
        },
      },
    });


    }
  }

  public onIntelligentAdd() {
    if (!this.prompt || this.isFlowReadonly) return;
    this.nzModal.create({
      nzContent: OptimizePromptModalComponent,
      nzWidth: 600,
      nzData: {
        instruct: this.prompt,
        isWorkflow: true,
        tipsChange: value => {
          this.prompt = value ?? '';
          this.cd.markForCheck();
        },
      },
    });

  }

  public openRefModal() {
    const myModal = this.nzModal.create({
      nzContent: RefPromptComponent,
      nzWidth: 1000,
      nzData: {
        select: (tmpl: ITmpl) => {
          this.prompt = tmpl.content;
          this.cd.markForCheck();
        },
      },
    })
  }

  addIntentFlow(flowType: string) {
    this.drawerRef = this.nzDrawer.create({
      nzContent: AddChildFlowModalComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzWrapClassName: 'add-child-flow-drawer',
      nzContentParams: {
        workflowId: this.paramsId,
        workflowSelected: flowType === 'subWorkflow' ? this.subFlowCtx : [],
        isAgentPage: true,
        isAgentSingle: flowType !== 'subWorkflow',
        workflowSelectedLimit: flowType === 'subWorkflow' ? SUBFLOW_LIMIT : 1,
        multiFlowType: flowType,
      } as any,
    });
    setTimeout(() => {
      const componentInstance = (this.drawerRef as any).componentRef?.instance;
      if (componentInstance) {
        componentInstance.outputs = {
          closeDrawer: () => {
            this.drawerRef.close();
          },
          workflowSelectEvent: (agentSingleSelect: any) => {
            const flow: IControllerFlow = {
              node_id: '',
              id: agentSingleSelect.workflow_id,
              name: agentSingleSelect.name,
              type: 'Normal',
              description: agentSingleSelect.description,
              version: agentSingleSelect.version_id,
              version_id: agentSingleSelect.version_id,
              version_name: agentSingleSelect.version_name,
              code: agentSingleSelect.code,
              fromShare: agentSingleSelect.fromShare,
            }
            if (flowType === 'intentFlow') {
              this.intentFlow = flow;
              this.onSelectFlow(flow, 'IntentIdentification');
              this.intentFlowId = flow.id;
            }
            if (flowType === 'startFlow') {
              this.startFlow = flow;
              this.onSelectFlow(flow, 'Start');

              this.startFlowId = flow.id;
            }
            if (flowType === 'endFlow') {
              this.onSelectFlow(flow, 'End');
              this.endFlow = flow;
              this.endFlowId = flow.id;
            }
            if (flowType === 'defaultFlow') {
              if (!flow.action) {
                flow.action = 'Continue';
              }
              this.onSelectFlow(flow, 'Default');
              this.defaultFlow = flow;
              this.defaultFlowCtx.id = flow.id;
              this.defaultFlowCtx.action = flow.action;
            }
            this.drawerRef.close();
          },
          workflowSelectListEvent: (agentSelectList: any) => {
            this.subFlowCtx = agentSelectList.map(v => {
              return {
                node_id: '',
                id: v.workflow_id || v.id,
                name: v.name,
                type: 'Normal',
                description: v.description,
                version: v.version_id || v.version,
                version_id: v.version_id || v.version,
                version_name: v.version_name,
                code: v.code,
                action: v.action || 'Continue',
                fromShare: v.fromShare,
              }
            });
            this.subFlowCtx.forEach((v: any) => {
              this.onSelectFlow(v, 'Normal');
            });
            this.drawerRef.close();
          },
        };
      }
    });
  }

  deleteIntentFlowEvent() {
    this.intentFlow = null;
    this.intentFlowId = null;
  }

  updateIntentFlowEvent() {
    this.updateDefaultFlow(this.intentFlow, 'IntentIdentification');
  }

  deleteStartFlowEvent() {
    this.startFlow = null;
    this.startFlowId = null;
  }

  updateStartFlowEvent() {
    this.updateDefaultFlow(this.startFlow, 'Start');
  }

  deleteEndFlowEvent() {
    this.endFlow = null;
    this.endFlowId = null;
  }

  updateEndFlowEvent() {
    this.updateDefaultFlow(this.endFlow, 'End');
  }

  deleteDefaultFlowEvent() {
    this.defaultFlow = null;
    this.defaultFlowCtx = {};
  }

  updateDefaultFlowEvent() {
    this.updateDefaultFlow(this.defaultFlow, 'Default');
  }


  deleteSubFlowEvent(i = 0) {
    this.subFlowCtx.splice(i, 1);
  }

  updateSubFlowEvent(i = 0) {
    this.updateDefaultFlow(this.subFlowCtx[i], 'Normal');
  }

  updateDefaultFlow(flow: any, type: ControllerSubFlowType) {
    const update: any = flow.update;
    flow.version = update.version;
    flow.version_id = update.version;
    flow.version_name = update.name;
    flow.name = update.resourceName;
    this.onSelectFlow(flow, type, true);
  }

  onDeleteSubAgent(i = 0) {
    this.associationAgentCtx.splice(i, 1);
  }

  onUpdateSubAgent(agent: any) {
    const update: any = agent.update;
    agent.version = update.version;
    agent.version_id = update.version;
    agent.version_name = update.name;
    agent.name = update.resourceName;
    this.associationAgentCtx = [...this.associationAgentCtx];
    this.onSelectSubAgent(agent, true);
  }

  addAgent() {
    this.drawerRef = this.nzDrawer.create({
      nzContent: AddMultipleAgentModalComponent,
      nzWidth: '700px',
      nzPlacement: 'right',
      nzWrapClassName: 'add-agent-drawer',
      nzContentParams: {
        agentSelected: [...this.associationAgentCtx, ...this.subFlowCtx],
        currentAgentId: this.paramsId,
        agentSelectedLimit: SUBFLOW_LIMIT,
      } as any,
    });
    setTimeout(() => {
      const componentInstance = (this.drawerRef as any).componentRef?.instance;
      if (componentInstance) {
        componentInstance.outputs = {
          closeDrawer: () => {
            this.drawerRef.close();
          },
          agentSelectListEvent: (agentSelectList: SubApplication[]) => {
            const selectedAgents: SubAgentModel[] = agentSelectList.filter(item =>
              item.subAgentType !== ApplicationType.WORKFLOW
            ) as SubAgentModel[];
            this.associationAgentCtx = selectedAgents.map(item => {
              const { tags, ...agent } = item;
              return {
                ...agent,
                node_id: '',
                avatar: null,
                type: item.type,
                subAgentType: item.subAgentType,
                version: item.version_id,
              }
            });
            this.associationAgentCtx.forEach((v: any) => {
              this.onSelectSubAgent(v);
            });

            const selectedFlow: SubWorkFlow[] = agentSelectList.filter(item =>
              item.subAgentType === ApplicationType.WORKFLOW
            ) as SubWorkFlow[];
            this.subFlowCtx = selectedFlow.map(item => {
              const { tags, ...flow } = item;
              return {
                ...flow,
                node_id: '',
                avatar: null,
                version: item.version_id,
                action: item.action || 'Continue',
                fromShare: item.fromShare,
              }
            });
            this.subFlowCtx.forEach((v: any) => {
              this.onSelectFlow(v, 'Normal');
            });
            this.drawerRef.close();
          },
        };
      }
    });
  }

  public async getMutilAgentLastVersionFn() {
    const flowId = this.route.snapshot.queryParams.id;
    await this.subControllerService.getMutilAgentLastVersion(
      flowId,
    ).then((res: any): void => {
      this.relations = res.relations;
      if (this.startFlow) {
        this.startFlow.update = this.handleShowUpdatedIcon(this.startFlowId, this.startFlow.version_id);
      }
      if (this.intentFlow) {
        this.intentFlow.update = this.handleShowUpdatedIcon(this.intentFlowId, this.intentFlow.version_id);
      }
      if (this.endFlow) {
        this.endFlow.update = this.handleShowUpdatedIcon(this.endFlowId, this.endFlow.version_id);
      }
      if (this.defaultFlow) {
        this.defaultFlow.update = this.handleShowUpdatedIcon(this.defaultFlow.id, this.defaultFlow.version_id);
      }
      if (this.subFlowCtx.length) {
        this.subFlowCtx.forEach((v: any) => {
          v.update = this.handleShowUpdatedIcon(v.id, v.version_id);
        });
      }
      if (this.associationAgentCtx.length) {
        this.associationAgentCtx.forEach((v: any) => {
          v.update = this.handleShowUpdatedIcon(v.id, v.version_id);
        });
      }
      this.cd.markForCheck();
    });
  }

  handleShowUpdatedIcon(id: string, version: string) {
    const app = this.relations.find(v => v.resource_id === id);
    if(!app) {
      return null;
    }

    const needUpdate = this.isNeedUpdate(version, app);
    if (needUpdate) {
      return {
        name: app.resource_latest_version_name,
        version: app.resource_latest_version,
        resourceName: app.resource_name
      };
    }
    return null;
  }

  goToIntentParamsDetail() {
    window.open(this.intent_params_detail_rule_link);
  }

  private async getFlows() {
    try {
      this.isLoadingFlows = true;

      const data = await this.appFlowRepoServe.getPublishedFlows({
        offset: 0,
        limit: 2000,
      });
      this.flowOps =
        data?.workflow_version_list.map((w) => ({
          node_id: '',
          id: w.workflow_id,
          name: w.name,
          subAgentType: ApplicationType.WORKFLOW,
          type: 'Normal',
          flowType: w.type,
          description: w.description,
          version: w.version_id,
          version_id: w.version_id,
          version_name: w.version_name,
          code: w.code,
        })) ?? [];

      this.subFlowOps = cloneDeep(this.flowOps).map((f) => ({
        ...f,
        disabled: !isNil(this.subFlowCtx.find((flow) => flow.id === f.id)),
      }));

      this.handleWorkflow();
    } finally {
      this.isLoadingFlows = false;
      setTimeout(()=>{
        this.cd.markForCheck();
      });
    }
  }

  private isNeedUpdate(version: string, app): boolean {
    const hasNewVersion = version < app.resource_latest_version;
    if(app.resource_type === ApplicationType.SINGLE_AGENT) {
      return hasNewVersion && app.latest_version_app_sub_type === 'planexecute';
    }
    return hasNewVersion;
  }

  handelData(){
    const selectedModel = this.modelOptions.find(
      (model) => model.id === this.modelFormGroup.controls.model.value,
    );
    this.nodeInfo.configs.description = this.description;
    this.nodeInfo.configs.intent = {
      name: this.intent_name,
      description: this.intent_desc,
    };

    let madel_params = {}
    if(selectedModel){
      let modelType = selectedModel?.type === 'router' ? 'strategy' : selectedModel?.model_type ?? '';
      madel_params =  {
        model_name: selectedModel?.model_name ?? '',
        model_type: modelType,
        id: selectedModel?.id ?? '',
        model_deployment_id: selectedModel?.model_deployment_id ?? '',
        ...(selectedModel?.model && { model: selectedModel.model }),
      }
    }

    const controllerData: IControllerNode = {
      id: this.nodeInfo.id,
      name: this.nodeInfo.name,
      type: this.nodeInfo.type,
      configs: {
        ...this.nodeInfo.configs,
        prompt: this.prompt,
        model: madel_params,
        temperature: Number(this.modelParams.temperature),
        top_p: Number(this.modelParams.top_p),
        workflows: this.getWorkflows(),
        agents: this.getAgents(),
        global_intents: this.intents.map((intent) => {
          if (intent.handler_type === 'Workflow') {
            const flow = this.flowInfoMap.get(
              `${(intent.handler as IWorkflowNode).id}_Intent`,
            );

            if (flow) {
              intent.handler = {
                id: flow.id,
                name: flow.name,
                type: 'Workflow',
                inputs: flow.inputs,
                outputs: flow.outputs,
                configs: flow.configs,
              };
            }
          }

          return intent;
        }),
        max_iteration: this.maxIteration,
        chat_history_max_turn: this.chatHistoryMaxTurn,
      },
    };
    return controllerData;
  }

  handelSave() {
    const controllerData = this.handelData();
    this.appFlowServ.setNodeSaveMonitor({ nodeData: controllerData });
  }

  getIterationMarks(): Record<number, string> {
    const marks: Record<number, string> = {};
    const max = this.mutilagent_max_iteration;
    if (max === 30) {
      marks[0] = '0';
      marks[10] = '10';
      marks[20] = '20';
      marks[30] = '30';
    } else {
      marks[0] = '0';
      marks[25] = '25';
      marks[50] = '50';
      marks[75] = '75';
      marks[100] = '100';
    }
    return marks;
  }

  checkAll(checked: boolean) {
    if (checked) {
      this.checkedFlows = [...this.tableSrcData.data.filter((item) => !item.disabled)];
    } else {
      this.checkedFlows = [];
    }
    this.refreshAllCheckedState();
  }

  checkItem(row: any, checked: boolean) {
    if (checked) {
      if (!this.checkedFlows.includes(row)) {
        this.checkedFlows.push(row);
      }
    } else {
      this.checkedFlows = this.checkedFlows.filter((item) => item !== row);
    }
    this.refreshAllCheckedState();
  }

  refreshAllCheckedState() {
    const selectable = this.tableSrcData.data.filter((item) => !item.disabled);
    const checkedCount = selectable.filter((item) => this.checkedFlows.includes(item)).length;
    this.allChecked = checkedCount === selectable.length && selectable.length > 0;
    this.indeterminate = checkedCount > 0 && checkedCount < selectable.length;
  }
}
