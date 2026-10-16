import { Injectable } from '@angular/core';
import type {IFlowTrigger, IWorkflowInfo} from "@routes/agent-center/app-flow/app-flow.types";
import {CompatibilityType, MigrateNodeType} from "@routes/agent-center/app-flow/components/dify-migrate-modal/dify-migrate-modal.interface";
import {I18NextEagerPipe} from "angular-i18next";
import {I18nNamespace} from "@i18n";
import {MessageComponent} from '@shared/services/cfdata.service';
import {AppFlowRepoService} from "@services/agent-center/app-flow-repo.service";
import {Router} from "@angular/router";
import { cloneDeep } from "lodash";

@Injectable({
  providedIn: 'root'
})
export class DifyMigrateService {

  public workFlowDsl: IWorkflowInfo;
  public parsedDSL: IWorkflowInfo;
  public oldDifyTrigger: IFlowTrigger;
  public fgUpdateMap = new Map();

  public fullCompatible = {
    label: this.i18n.transform(`${I18nNamespace.AGENT_CENTER}:dsl_entire_match`),
    icon: 'check-circle',
    color: '#52c41a',
    collapsed: false,
    nodes: [],
  };

  public halfCompatible = {
    label: this.i18n.transform(`${I18nNamespace.AGENT_CENTER}:dsl_half_match`),
    icon: 'warning',
    color: '#faad14',
    collapsed: false,
    nodes: [],
  };

  public notCompatible = {
    label: this.i18n.transform(`${I18nNamespace.AGENT_CENTER}:dsl_not_match`),
    icon: 'close-circle',
    color: '#ff4d4f',
    collapsed: false,
    nodes: [],
  };

  public migrateRes = [
    this.fullCompatible,
    this.halfCompatible,
    this.notCompatible
  ];

  private compareMap = {
    [MigrateNodeType.START]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.END]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.Message]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.Loop]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.LoopInput]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.LoopOutput]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.Aggregation]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.Branch]: {
      checkCompatibility: () => CompatibilityType.FULL_COMPATIBLE
    },
    [MigrateNodeType.LLM]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.IntentDetection]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.Code]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.KnowledgeRepo]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.SetVariable]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.Agent]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.Http]: {
      checkCompatibility: () => CompatibilityType.HALF_COMPATIBLE
    },
    [MigrateNodeType.Empty]: {
      checkCompatibility: () => CompatibilityType.NOT_COMPATIBLE
    },
    [MigrateNodeType.Mcp]: {
      checkCompatibility: () => CompatibilityType.NOT_COMPATIBLE
    },
    [MigrateNodeType.Plugin]: {
      checkCompatibility: () => CompatibilityType.NOT_COMPATIBLE
    }
  }

  constructor(
    private i18n: I18NextEagerPipe,
    private router: Router,
    private appFlowRepoService: AppFlowRepoService,
  ) { }

  public setParseDsl(parsedDSL: IWorkflowInfo): void {
    this.parsedDSL = parsedDSL;

    this.workFlowDsl = cloneDeep(this.parsedDSL);
    this.initNodeGroup();

    // 设置虚拟节点
    this.setTriggerNode();
    this.setGlobalConfigNode();
  }

  public createWorkFlow(callBack?: () => void): void {
    const fgList = Array.from(this.fgUpdateMap);
    fgList.forEach(([nodeId, fgData]) => {
      this.updateFgDetail(fgData);
    });

    this.appFlowRepoService.createFlow(this.workFlowDsl as any).then(res => {
      callBack?.();
      MessageComponent.showSuccess(
        this.i18n.transform(`${I18nNamespace.AGENT_CENTER}:imported_succeeded_dify_tip`),
        3000,
      );

      this.router.navigate(['/home/agent-center/app-flow/flow'], {
        queryParams: {
          id: res.workflow_id,
        },
      });
    });
  }

  private initNodeGroup(): void {
    if (!this.workFlowDsl.workflow_details.nodes?.length) {
      return;
    }

    const fullCompatibleNodes = [];
    const halfCompatibleNodes = [];
    const notCompatibleNodes = [];
    this.workFlowDsl.workflow_details.nodes.forEach(node => {
      const compatibility = this.compareMap[node.type]?.checkCompatibility(node)
        ?? CompatibilityType.NOT_COMPATIBLE;

      if (compatibility === CompatibilityType.FULL_COMPATIBLE) {
        fullCompatibleNodes.push(node);
      } else if (compatibility === CompatibilityType.HALF_COMPATIBLE) {
        halfCompatibleNodes.push(node);
      } else {
        notCompatibleNodes.push(node);
      }
    });

    this.fullCompatible.nodes = fullCompatibleNodes;
    this.halfCompatible.nodes = halfCompatibleNodes;
    this.notCompatible.nodes = notCompatibleNodes;
  }

  private setTriggerNode() {
    this.oldDifyTrigger = this.workFlowDsl.workflow_details.configs.trigger;
    this.workFlowDsl.workflow_details.configs.trigger = null;

    if(this.oldDifyTrigger?.frequency) {
      // 推入虚拟触发器节点
      this.halfCompatible.nodes.push({
        type: MigrateNodeType.Trigger
      });
    }
  }

  private setGlobalConfigNode(): void {
    const additionalQuestionsConfig = this.workFlowDsl.workflow_details.configs.additional_questions_config;

    if(additionalQuestionsConfig?.enable) {
      this.halfCompatible.nodes.push({
        type: MigrateNodeType.GlobalConfig
      })
    }
  }

  private updateFgDetail(fgData) {
    const { id, ...params } = fgData;
    this.appFlowRepoService
      .putFunctionsdetail(id, params)
      .then((res) => {

      });
  }
}
