/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable import/no-cycle */
import { ChangeDetectorRef, Injectable, OnInit,
  Output,
  EventEmitter, inject, } from '@angular/core';
import { Graph } from '@antv/x6';
import { cloneDeep } from 'lodash';
import { combineLatest, debounceTime, map, takeUntil } from 'rxjs';
import { environment } from 'src/environment/environment';
import { AppFlowService } from '../../app-flow.service';
import { WF_MAX_PARAMS_NUM } from '../../flow.const';
import { NodeService } from '../../node.service';
import { ILoopNode, IParamRef, IWFView, IWorkflowField } from '../../node.type';
import { IRef2TreeConfig, NodeUtils } from '../utils';
import { BaseComponent } from './base.component';
import { cdnAssetUrl } from 'src/single-spa/assets-url';

@Injectable()
export abstract class ModalBaseComponent
  extends BaseComponent
  implements OnInit
{
  public paramNameMaxLen = 64;

  protected paramLimit = WF_MAX_PARAMS_NUM;

  protected isInit = true;

  protected isConfirmLoading = false;

  protected isPOC = environment.envType === 'poc';

  protected isNormalView = true;

  protected opMarginLeft = '4px';

  protected normalParamLableWidth = {
    name: '145px',
    type: '90px',
    desc: '120px',
  };

  protected slimParamLableWidth = {
    name: '136px',
    type: '86px',
    desc: '92px',
  };

  protected labelWidth = this.normalParamLableWidth;

  protected initTime;
  protected changeTime;

  @Output('editCodeEvent') editCodeEvent = new EventEmitter();

  protected modalCdr = inject(ChangeDetectorRef);

  constructor(
    protected override nodeServ: NodeService,
    protected override appFlowServ: AppFlowService,
  ) {
    super(nodeServ, appFlowServ);
  }

  ngOnInit(): void {
    this.updateChangeAndInitTime();
    this.nodeServ
      .isConfirmLoadingUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((stat) => {
        this.isConfirmLoading = stat;
      });

    this.appFlowServ
      .nodeNameChange()
      .pipe(takeUntil(this.destroy$))
      .subscribe((info) => {
        if (info && info.id === this.nodeBase.id) {
          this.nodeBase.name = info.name;
          this.modalCdr.detectChanges();
        }
      });

    this.isNormalView = document.querySelector('body').offsetWidth >= 1920;

    this.labelWidth = this.isNormalView
      ? this.normalParamLableWidth
      : this.slimParamLableWidth;
    this.opMarginLeft = this.isNormalView ? '4px' : '0px';
  }

  protected handleKeyDown(event: KeyboardEvent) {
    if (
      event.target instanceof HTMLInputElement ||
      event.target instanceof HTMLTextAreaElement ||
      (event.target instanceof HTMLDivElement &&
        event.target.className.includes('editor'))
    ) {
      if (
        (event.ctrlKey || event.metaKey) &&
        ['s', 'c', 'v', 'z', 'y','a'].includes(event.key)
      ) {
        event.stopPropagation();
      }

      if (
        ['v', 'h', 'q'].includes(event.key) || event.code === 'Space'|| event.code === 'Tab' || event.key === 'Backspace'
      ) {
        event.stopPropagation();
      }
    }
  }

  protected getProviderIcon(provider) {
    return cdnAssetUrl(`assets/model/${provider}.svg`);
  }

  protected getLayerIndexWidth(param: IWFView) {
    return NodeUtils.getLayerIndexWidth(param, this.isNormalView);
  }

  protected isReachedParamLimit(paramArr: any[]): boolean {
    return (paramArr?.length ?? 0) === this.paramLimit;
  }

  protected updateName() {
    if (this.nodeBase.configs?.isDefaultName) {
      this.nodeBase.configs.isDefaultName = false;
    }
    this.nodeServ.setUpdateView();
  }

  protected updateView() {
    this.nodeServ.setUpdateView();
  }

  protected getSelfRefs(configs?: IRef2TreeConfig) {
    return this.nodeServ.refInfoUpdate$().pipe(
      map((info) => {
        const info_list = NodeUtils.refInfo2Tree(info, configs);
         const requestVariables = this.appFlowServ.requestVariablesFn(info_list);
        return [...info_list,...requestVariables]
      }),
      takeUntil(this.destroy$),
    );
  }

  protected getParentRefs(configs?: IRef2TreeConfig) {
    return this.nodeServ.parentRefInfoUpdate$().pipe(
      map((info) => {
        const info_list = NodeUtils.refInfo2Tree(info, configs);
        const requestVariables = this.appFlowServ.requestVariablesFn(info_list);
        return [...info_list,...requestVariables]
      }),
      takeUntil(this.destroy$),
    );
  }

  protected getLoopInnerNodeRefs(
    nodeInfo: ILoopNode,
    configs?: IRef2TreeConfig,
  ) {
    return this.withLoopInnerNodePreRefs(
      this.getLoopRefs(nodeInfo, configs),
      configs,
    );
  }

  protected getLoopInnerNodePreRefs(configs?: IRef2TreeConfig) {
    return this.withLoopInnerNodePreRefs(null, configs);
  }

  protected withLoopInnerNodePreRefs(
    otherRef?: IParamRef,
    configs?: IRef2TreeConfig,
  ) {
    return combineLatest([
      this.getSelfRefs(configs),
      this.getParentRefs(configs),
    ]).pipe(
      debounceTime(0),
      map(([inner, parent]) => {
        // 记忆变量和环境变量需要排除，不能重复
        const parentWithoutMemosAndEnv = parent.filter(
          (ref) => ref.type !== 'MemoVal' && ref.type !== 'environment',
        );

        return otherRef
          ? [...inner, ...parentWithoutMemosAndEnv, otherRef]
          : [...inner, ...parentWithoutMemosAndEnv];
      }),
      takeUntil(this.destroy$),
    );
  }

  protected getParentNodeInfo(graph: Graph): ILoopNode | undefined {
    // 防御层：删除节点后，异步初始化的配置面板可能仍以已不存在的节点 id 调用本方法，
    // 此时 graph 可能为 null、nodeBase.id 为空或 getCellById 返回 null，
    // 不得再调用 getParent()，否则抛 “Cannot read properties of null (reading 'getParent')”。
    // 有效节点行为保持不变：仍返回其父循环节点信息（无父节点时为 undefined）。
    if (!graph || !this.nodeBase?.id) {
      return undefined;
    }
    const cell = graph.getCellById(this.nodeBase.id);
    if (!cell) {
      return undefined;
    }
    const parentCell = cell.getParent();
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    const parentData = parentCell?.data?.ngArguments?.nodeInfo as ILoopNode;

    return parentData;
  }

  protected onRefSubscribe(onRefUpdate: Function) {
    const parentNode = this.getParentNodeInfo(this.appFlowServ.getGraph());
    if (parentNode) {
      this.getLoopInnerNodeRefs(parentNode).subscribe((info) => {
        onRefUpdate(info);
      });
    } else {
      this.getSelfRefs().subscribe((info) => {
        onRefUpdate(info);
      });
    }
  }

  protected getEmptyLoopRef(loopId: string, loopName: string): IParamRef {
    return {
      ref_node_id: loopId,
      ref_var_name: '',
      name: loopName,
      isTop: true,
      type: 'Loop',
      source: 'user',
      expanded: true,
      children: [],
    };
  }

  public getLoopMidVarRefs(nodeInfo: ILoopNode, configs?: IRef2TreeConfig) {
    if (nodeInfo && nodeInfo.type === 'Loop') {
      const mid = nodeInfo.inputs.find(
        (input) => input.name === 'intermediate_loop_var',
      );

      if (mid) {
        const midCopy = cloneDeep(mid);
        const midRef = this.getEmptyLoopRef(nodeInfo.id, nodeInfo.name);
        const intermediateObjRefs = NodeUtils.fields2RefParams(
          [midCopy],
          midRef.ref_node_id,
          [],
          configs,
        );

        if (intermediateObjRefs.length) {
          midRef.children = intermediateObjRefs[0].children;
          return [midRef];
        }
      }
    }

    return [];
  }

  protected getLoopRefs(nodeInfo: ILoopNode, configs?: IRef2TreeConfig) {
    if (nodeInfo && nodeInfo.type === 'Loop') {
      const loopRef = this.getEmptyLoopRef(nodeInfo.id, nodeInfo.name);

      // array item
      const arrayVar = nodeInfo.inputs.find(
        (input) => input.name === 'arr_loop_var',
      );
      if (arrayVar && arrayVar.type?.startsWith('array')) {
        const arrVarCopy = cloneDeep(arrayVar);
        arrVarCopy.name = `${arrVarCopy.name}.item`;

        const arrLoopVarRef = NodeUtils.fields2RefParams(
          [arrVarCopy],
          nodeInfo.id,
          [],
          {
            refRootArrItem: true,
            ...configs,
          },
        );

        if (arrLoopVarRef.length) {
          const arrRef = arrLoopVarRef[0];
          const itemInfo = arrRef.schema as IWorkflowField;

          const arrItem: IParamRef = {
            isTop: false,
            name: 'item(in arr_loop_var)',
            ref_node_id: nodeInfo.id,
            ref_var_name: arrRef.name,
            type: itemInfo.type,
            source: arrRef.source,
          };

          if (arrItem.type === 'object') {
            arrItem.schema = itemInfo.schema;
            arrItem.children = arrRef.children;
            arrItem.expanded = true;
          }

          loopRef.children.push(arrItem);
        }
      }

      // index
      loopRef.children.push({
        isTop: false,
        name: 'index',
        type: 'integer',
        ref_node_id: nodeInfo.id,
        ref_var_name: 'index',
        source: 'pre_defined',
        disabled: configs?.strOnly,
      });

      // mid refs
      const midRefs = this.getLoopMidVarRefs(nodeInfo, configs);
      if (midRefs.length) {
        loopRef.children.push(...cloneDeep(midRefs[0].children));
      }

      return loopRef;
    }

    return null;
  }

  getDifferentType(refInfo) {
    let type: string = refInfo.type;
    if (type === 'array') {
      type = type + `<${(refInfo.schema as IWorkflowField)?.type as string}>`;
    }
    return type;
  }

  protected changeUpdateTime() {
    this.changeTime = new Date().getTime();
  }

  protected updateChangeAndInitTime() {
    this.initTime = new Date().getTime();
    this.changeTime = this.initTime;
  }

  protected tagCompareNoChange(): boolean {
    return this.initTime === this.changeTime;
  }

  private getCompatibleTypes(type: string): string[] {
    const t = type?.toLowerCase();

    if (!t) return [];

    // file/... 全集。default 是 file 类型的超集
    const fileSubTypes = this.getAllFileTypes();

    // 1）string 能匹配 自身 和 file/...
    if (t === 'string') {
      return ['string', ...fileSubTypes.map((s) => `file/${s}`)];
    }

    // 2）array<string> 能匹配 自身 和 array<file/...>
    if (t === 'array<string>') {
      return ['array<string>', ...fileSubTypes.map((s) => `array<file/${s}>`)];
    }

    // 3）file/default 能匹配所有 file/...
    if (t === 'file/default') {
      return fileSubTypes.map((s) => `file/${s}`);
    }

    // 4）array<file/default> 能匹配所有 array<file/...>
    if (t === 'array<file/default>') {
      return fileSubTypes.map((s) => `array<file/${s}>`);
    }

    // 5）其他，只匹配自身
    return [t];
  }

  private getAllFileTypes(): string[] {
    return ['default', 'doc', 'txt', 'excel', 'ppt', 'image', 'audio'];
  }
}
