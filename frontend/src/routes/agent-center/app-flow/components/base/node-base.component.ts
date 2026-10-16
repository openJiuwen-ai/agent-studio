/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable import/no-cycle */
import {
  AfterViewInit,
  ChangeDetectorRef,
  ElementRef,
  Injectable,
  OnChanges,
  OnInit,
  SimpleChanges,
} from '@angular/core';
import { filter, takeUntil } from 'rxjs';
import i18next from 'i18next';
import { AppFlowService } from '../../app-flow.service';
import flowCommonLogic from '../../common-logic-workflow';
import { WORKFLOW_SVGS } from '../../flow.const';
import { NodeService } from '../../node.service';
import { IRefContentType, IWorkflowField } from '../../node.type';
import { NodeUtils } from '../utils';
import { BaseComponent } from './base.component';
import { isNil } from 'lodash';

interface IValidateErr {
  id: string;
  reason: string;
}

@Injectable()
export abstract class NodeBaseComponent
  extends BaseComponent
  implements OnInit, AfterViewInit, OnChanges
{
  protected alertContent: string[] = [];

  // 是否显示子工作流的更新icon
  protected isChildFlowsUpdated;

  protected runNodeStatus = '';

  protected nodeElapsedTime = '';

  protected isSelected = false;

  protected isSelection = false; //是否被框选

  protected validateAlertIcon = WORKFLOW_SVGS.ValidateAlert;

  protected isExpand = true;

  // 每个意图节点对应的模式
  protected curModeOfIntent: 'normal' | 'advanced' = 'normal';

  constructor(
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
    protected cdr: ChangeDetectorRef,
    protected elementRef: ElementRef<HTMLDivElement>,
  ) {
    super(nodeServ, appFlowServ);
  }

  ngOnInit(): void {
    this.nodeServ
      .currSelectedNodeUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((nodeId) => {
        this.isSelected = nodeId === this.nodeBase.id;
      });

    this.nodeServ
      .isAllExpandUpdate$()
      .pipe(
        filter((val) => val !== this.isExpand),
        takeUntil(this.destroy$),
      )
      .subscribe((isAllExpand) => {
        this.isExpand = isAllExpand;

        window.setTimeout(() => {
          this.updateNodeHeight();
        }, 0);
      });

    this.appFlowServ
      .flowErrorsUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((validateRes) => {
        const { success, errors } = validateRes;

        if (!success && errors) {
          this.alertContent = (errors as IValidateErr[])
            .filter((item) => item.id === this.nodeBase.id)
            .map((error) => error.reason);
        } else {
          this.alertContent = [];
        }

        this.updateNodeHeight();
      });

    this.appFlowServ
      .resNodesUpdate()
      .pipe(takeUntil(this.destroy$))
      .subscribe((childFlowNodes) => {
        childFlowNodes.forEach((node) => {
          if (node.id === this.nodeBase.id) {
            this.isChildFlowsUpdated = node;
          }
        });
      });

    let llmNodeIds: string[] = [];
    this.appFlowServ
      .tokenDataUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((tokenObj) => {
        if (tokenObj && Object.keys(tokenObj).length === 0) {
          this.runNodeStatus = '';
          this.nodeElapsedTime = '';
          this.appFlowServ.initRunNode();
        }

        const { event, data } = tokenObj || {};
        let {
          node_id,
          status,
          start_time,
          end_time,
          node_type,
          parent_node_id,
          loop_node_id,
          outputs,
        } = data || {};

        if(event && tokenObj.fromType) {
          this.tokenDataFrom = tokenObj.fromType;
        }
        //对象提取特殊处理
        if (node_id?.startsWith('composite_node_')) {
          node_id = node_id?.substring(10, 28);
          node_type = 'ParamExtraction';
        }
        // 过滤子工作流内部节点的事件（其 node_id 可能与父画布节点冲突，如 node_start/node_end，
        // 避免结束节点卡片上的状态先匹配到子工作流里的）；
        // 循环节点体内的事件（带 loop_node_id）属于本画布，放行以显示循环体节点运行状态
        if (parent_node_id && !loop_node_id) {
          return;
        }

        // 如果event等于node_wait并且node_type等于LLM，记录node_id
        if (event === 'node_wait' && node_type === 'LLM') {
          llmNodeIds.push(node_id);
        }
        if (node_id === this.nodeBase.id) {
          if (event === 'node_started') {
            this.runNodeStatus = 'loading';
            this.appFlowServ.addRunNode(node_id);
            this.appFlowServ.setEdgeStatus({ node_id, status: 'loading' });
          } else if (event === 'node_finished') {
            this.appFlowServ.setEdgeStatus({ node_id, status: 'end' });
            if (status.desc === 'succeeded') {
              if (outputs?.isSuccess === false) {
                this.runNodeStatus = 'exception';
              } else {
                this.runNodeStatus = 'succeeded';
              }
            } else if (status.desc === 'failed') {
              if (outputs?.isSuccess === false) {
                this.runNodeStatus = 'exception';
              } else {
                this.runNodeStatus = 'failed';
              }
            }
            this.nodeElapsedTime = this.calcNodeElapsedTime(
              start_time,
              end_time,
            );
          }
        }

        // 遇到结束标记时，检查llmNodeIds数组中是否包含this.nodeBase.id，并且对应的runNodeStatus是否为loading
        // 通过workflow_finished，避免含交互式节点的工作流，一轮execution需要调用多个流式接口
        if (event === 'workflow_finished' && llmNodeIds.length > 0) {
          if (
            llmNodeIds.includes(this.nodeBase.id) &&
            this.runNodeStatus === 'loading'
          ) {
            // 规避后续节点未引用大模型节点的输出，导致大模型节点一直是"运行中"状态
            this.runNodeStatus = 'succeeded';
          }
        }

        // 遇到event:error时，检查当前状态是否为loading，满足则标记为failed。避免只返回node_started和error这两个token块
        // 改为运行终止状态
        if (
          (event === 'error' || event === 'exception') &&
          this.runNodeStatus === 'loading'
        ) {
          this.runNodeStatus = 'exception_stop';
          this.appFlowServ.setEdgeStatus({
            node_id: this.nodeBase.id,
            status: 'end',
          });
        }

        if (event === 'workflow_finished' && this.runNodeStatus !== 'loading') {
          this.appFlowServ.setEdgeStatus({
            node_id: this.nodeBase.id,
            status: 'end',
          });
        }
        // 大模型并行异常节点处理
        if (event === 'end' && llmNodeIds.length > 0) {
          if (
            llmNodeIds.includes(this.nodeBase.id) &&
            this.runNodeStatus === 'loading'
          ) {
            this.runNodeStatus = '';
            this.appFlowServ.setEdgeStatus({
              node_id: this.nodeBase.id,
              status: 'end',
            });
          }
        }
        // 用户手动停止,恢复正在运行的非提问器节点
        if (event === 'user_stop' && this.runNodeStatus === 'loading' && this.nodeBase.type !== 'Questioner') {
          this.runNodeStatus = '';
          this.appFlowServ.setEdgeStatus({
            node_id: this.nodeBase.id,
            status: 'end',
          });
        }

        this.updateNodeHeight();
      });

    // 在调用详情Tab下，点击表格（或时序图）中的某个节点，选中画布中的对应节点
    this.appFlowServ
      .nodeIdClickedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((nodeIdClicked: string) => {
        if (nodeIdClicked) {
          this.isSelected = nodeIdClicked === this.nodeBase.id;
        }
      });

    this.appFlowServ
      .nodeIdSelectedUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((nodeIds: string[]) => {
        this.isSelection = nodeIds.includes(this.nodeBase.id);
      });

    this.appFlowServ
      .modeOfIntentNodeUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((modes) => {
        const matchedNode = modes.find(
          (item) => item.node_id === this.nodeBase.id,
        );
        this.curModeOfIntent = matchedNode ? matchedNode.mode : 'normal';
      });
  }

  ngAfterViewInit() {
    // 此处调用更新高度的函数，会导致某个意图节点连续触发三次高度变化，左边连接桩不居中
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes?.nodeInfo?.currentValue) {
      this.cdr.detectChanges();

      window.setTimeout(() => {
        this.updateNodeHeight();
      }, 0);
    }
  }

  protected onSwitchExpand() {
    this.isExpand = !this.isExpand;
    this.cdr.detectChanges();

    this.updateNodeHeight();
  }

  protected updateNodeHeight() {
    this.appFlowServ.updateNodeHeight(this.elementRef, this.nodeBase.id, {
      isExpand: this.isExpand,
      nodeType: this.nodeBase.type,
      hasTips: this.alertContent?.length > 0 || !!this.runNodeStatus,
    });
  }

  protected getFieldType(param: IWorkflowField) {
    return param.value.type;
  }

  protected getFieldContentValue(param: IWorkflowField) {
    if (param.value.type === 'ref') {
      return (
        (param.value.content as IRefContentType).ref_var_name
      );
    }

    if (isNil(param?.value?.content) || param.value.content === '') {
      return '';
    }

    return param.value.content;
  }

  protected getFieldName(param: IWorkflowField) {
    return param.name || i18next.t('not_configured');
  }

  protected getFieldDesc(param: IWorkflowField) {
    return param.description || i18next.t('not_configured');
  }

  protected getNodeStatus(node_status: string) {
    return flowCommonLogic.getNodeStatus(node_status);
  }

  protected getBgColor(node_status: string) {
    const colorMap = {
      loading: '#deecff',
      succeeded: '#D5F2DC',
      failed: '#ffeae8',
      exception: '#FFE7CC',
      exception_stop: '#FFE7CC',
    };

    return colorMap[node_status] || '';
  }

  protected getColor(node_status: string) {
    const colorMap = {
      loading: '#1476ff',
      succeeded: '#029931',
      failed: '#F23030',
      exception: '#FF8800',
      exception_stop: '#FF8800',
    };

    return colorMap[node_status] || '';
  }

  protected getNodeStatusText(node_status: string) {
    return flowCommonLogic.getWorkflowStatusDesc(node_status);
  }

  protected calcNodeElapsedTime(start_time: number, end_time: number) {
    return flowCommonLogic.calcElapsedTime(start_time, end_time);
  }

  protected getTypeView = NodeUtils.getFieldTypeView;
}
