import { Component, ChangeDetectorRef, ElementRef, EventEmitter, forwardRef, HostListener, Inject, Input, Output, ViewChild } from '@angular/core';
import { ControlContainer, ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { CommonService } from '@services/common.service';
import { RefSelectedRequireDirective } from '@shared/directives/common-validator.directive';
import { MODULES } from '@shared/modules';
import { I18NEXT_NAMESPACE } from 'angular-i18next';
import { Subscription } from 'rxjs';
import { ParamLabelPipe } from 'src/pipes/param-label.pipe';
import { NodeUtils } from 'src/routes/agent-center/app-flow/components/utils';
import { WORKFLOW_SVGS } from 'src/routes/agent-center/app-flow/flow.const';
import type { INodeType, IWorkflowFieldType } from 'src/routes/agent-center/app-flow/node.type';
import { CdkConnectedOverlay, CdkOverlayOrigin, ConnectedPosition } from '@angular/cdk/overlay';
import {
  cloneTreeWithSelection,
  getCompatibleTypes,
  isNodeRefSelectable,
  isNodeSelected as matchSelectedRef,
  setDifferentTypeDisabledEacl,
} from './input-tree-select.utils';

@Component({
  selector: 'input-tree-select',
  templateUrl: './input-tree-select.html',
  styleUrls: ['./input-tree-select.less'],
  standalone: true,
  imports: [MODULES, RefSelectedRequireDirective, ParamLabelPipe, CdkConnectedOverlay, CdkOverlayOrigin],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON],
    },
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => InputTreeSelect),
      multi: true,
    },
  ],
})
export class InputTreeSelect implements ControlValueAccessor {
  @Input('options') options: Array<any>;
  @Input('tiValidation') tiValidation: any;
  @Input('errorMessageWrapper') errorMessageWrapper: any;
  @Input('placeholder') placeholder: any;
  @Input('radiusLeft') radiusLeft: boolean = false;
  @Input('specifyType') specifyType: any = null;
  @Input('name') name: any;
  @Output('select') select = new EventEmitter<any>();

  _value: any = '';
  selectVal: any;
  showSelectDiv = false;
  path: Array<any> = [];
  control: any;
  searchSelectList: any = [];
  searchTimeout: any = null;
  treeSelectIndexList = [];
  treeSelectIndex = -1;
  showPathIcon = false;
  urlPathIcon = '';
  inputFirstNode = '';
  inputNodeName = '';
  inputTypeString = '';
  treeDivPosition = {
    top: '0px',
    right: '0px',
    tr: '',
  };
  searchVal = '';
  /** 二级树当前选中 key，避免污染共享 options 上的 checked/selected */
  selectedTreeKeys: string[] = [];
  @ViewChild('selectDivDom') selectDivDom: ElementRef;
  @ViewChild('selectTreeDom') selectTreeDom: ElementRef;
  @ViewChild('inputDom') inputDom: ElementRef;
  overlayPositions: ConnectedPosition[] = [
    { originX: 'start', originY: 'bottom', overlayX: 'start', overlayY: 'top' },
    { originX: 'start', originY: 'top', overlayX: 'start', overlayY: 'bottom' },
  ];
  cScrollStartCt = false;
  cScrollTop = 0;
  thisSubscribe: Subscription;
  vInvalid = false;

  constructor(
    public commonService: CommonService,
    @Inject(ControlContainer) public controlContainer: ControlContainer,
    private el: ElementRef,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit() {
    this.control = this.controlContainer?.control;
    this.thisSubscribe = this.controlContainer?.control?.valueChanges?.subscribe(val => {
      setTimeout(() => {
        this.vInvalid = !!this.control?.controls[this.name].errors && this.control?.controls[this.name].dirty;
      });
    });
  }

  ngOnDestroy() {
    this.thisSubscribe?.unsubscribe();
  }

  get borderClass(): any {
    let res = '';
    if (this.radiusLeft) {
      res = this.showSelectDiv ? 'this-input-class-left this-input-class-click' : 'this-input-class-left this-input-class-unclick';
    } else {
      res = this.showSelectDiv ? 'this-input-class this-input-class-click' : 'this-input-class this-input-class-unclick';
    }
    return res;
  }

  get tooltipState(): string {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const metrics = ctx.measureText(`${this.inputFirstNode}${this.inputNodeName}`);
    if (metrics?.width + 110 > this.inputDom?.nativeElement?.clientWidth) {
      return 'topRight';
    } else {
      return 'top';
    }
  }

  get value(): any {
    return this._value;
  }

  set value(v: any) {
    if (v !== this._value) {
      this._value = v;
      this.onChange(v);
      this.onTouched(v);
      this.setShowValRoute();
    }
  }

  onChange: any = (val: any) => {};
  onTouched: any = (val: any) => {};

  registerOnChange(fn: any): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: any): void {
    this.onTouched = fn;
  }

  writeValue(val): void {
    this._value = val;
    this.value = val;
    this.setShowValRoute();
  }

  selectClick(event: Event) {
    event.stopPropagation();
    if (this.showSelectDiv) {
      this.closeSelectPanel();
      this.control?.controls?.[this.name]?.markAsDirty();
      this.vInvalid = !!this.control?.controls?.[this.name]?.errors && this.control?.controls?.[this.name]?.dirty;
    } else {
      this.showSelectDiv = true;
      this.searchVal = '';
      this.setDifferentTypeDisabled();
      // 先按当前值算 path，再定位高亮（重开页面 / 多次换引用后必走）
      this.setShowValRoute();
      setTimeout(() => {
        this.findTreeSelectIndex();
      }, 0);
    }
  }

  /** 当前节点是否为已选引用（按 ref_node_id + ref_var_name，不依赖对象引用） */
  isNodeSelected(node: any): boolean {
    return matchSelectedRef(this._value, node);
  }

  private closeSelectPanel() {
    this.showSelectDiv = false;
    this.treeSelectIndexList = [];
    this.treeSelectIndex = -1;
    this.selectedTreeKeys = [];
  }

  /** 仅计算二级面板滚动位置，不写共享 options */
  private collectScrollOffset(list: any[]) {
    if (!list?.length || !this.path?.[0] || !this._value?.[0]) {
      return;
    }
    for (const value of list) {
      if (this.path[0].ref_node_id === value.ref_node_id && this.path[0].ref_var_name === value.ref_var_name) {
        this.cScrollStartCt = true;
        this.cScrollTop = 0;
      }
      if (
        this.cScrollStartCt &&
        (this.path[0].ref_node_id !== value.ref_node_id || this.path[0].ref_var_name !== value.ref_var_name)
      ) {
        this.cScrollTop += 1;
      }
      if (this.isNodeSelected(value)) {
        this.cScrollStartCt = false;
      }
      if (value.children?.length) {
        this.collectScrollOffset(value.children);
      }
    }
  }

  setDifferentTypeDisabled() {
    const type: string = this.specifyType;
    if (type) {
      const compatible = getCompatibleTypes(type);
      this.options.forEach(item => {
        if (item.children) {
          item.children = setDifferentTypeDisabledEacl(item.children, compatible);
        }
      });
    }
  }

  onSearch(val) {
    this.onInputChange(val);
  }

  onInputChange(val) {
    if (val) {
      this.treeSelectIndexList = [];
      this.treeSelectIndex = -1;
      if (this.searchTimeout) {
        clearTimeout(this.searchTimeout);
        this.searchTimeout = null;
      }
      this.searchTimeout = setTimeout(() => {
        this.searchSelectList = this.getSearchSelectList(val);
        this.cdr.markForCheck();
      }, 200);
    } else {
      // 清空搜索后恢复当前值的一二级高亮
      this.findTreeSelectIndex();
    }
  }

  getSearchSelectList(val) {
    let res = [];
    res = this.treeToList(this.options, [], val);
    return res;
  }

  findTreeSelectIndex() {
    if (this.path.length <= 0 || !this.selectDivDom?.nativeElement) {
      return;
    }
    const i = this.path[0].treeIndex;
    this.treeSelectIndex = i;
    this.selectedTreeKeys = [];
    this.cScrollStartCt = false;
    this.cScrollTop = 0;
    this.collectScrollOffset(this.options);
    // 用副本渲染二级树，并带上 selected / nzSelectedKeys
    const cloned = cloneTreeWithSelection(this.options[i]?.children || [], this._value, this.selectedTreeKeys);
    this.treeSelectIndexList = cloned.tree;
    this.selectDivDom.nativeElement.scrollTop = i * 32;

    const searchItems = this.selectDivDom.nativeElement.querySelectorAll('.search-item');
    const targetItem = searchItems[i];
    if (!targetItem) {
      return;
    }

    const oTop = targetItem.offsetTop;
    const isTop = window.innerHeight - oTop < 300;
    if (isTop) {
      this.treeDivPosition = {
        top: `${oTop - this.selectDivDom.nativeElement.scrollTop + 40}px`,
        right: `${this.selectDivDom.nativeElement.offsetWidth + 1}px`,
        tr: 'translateY(-100%)',
      };
    } else {
      this.treeDivPosition = {
        top: `${oTop - this.selectDivDom.nativeElement.scrollTop - 8}px`,
        right: `${this.selectDivDom.nativeElement.offsetWidth + 1}px`,
        tr: 'translateY(0%)',
      };
    }
    setTimeout(() => {
      if (this.selectTreeDom?.nativeElement) {
        this.selectTreeDom.nativeElement.scrollTop = Math.max(0, (this.cScrollTop - 3) * 32);
      }
      this.cdr.markForCheck();
    }, 10);
  }

  @HostListener('document:click', ['$event'])
  onClick(event: MouseEvent) {
    if (!this.showSelectDiv) {
      return;
    }
    const target = event.target as Node;
    const isInside = this.el.nativeElement.contains(target);
    const isOwnOverlay = !!(target as HTMLElement)?.closest?.('.select-tree-dom');
    if (!isInside && !isOwnOverlay) {
      this.control?.controls?.[this.name]?.markAsDirty();
      this.vInvalid = !!this.control?.controls?.[this.name]?.errors && this.control?.controls?.[this.name]?.dirty;
      this.closeSelectPanel();
    }
  }

  setShowValRoute() {
    if (this._value?.length > 0 && this.options?.length > 0) {
      this.selectVal = this.findPath(this._value[0], this.options);
    } else {
      this.selectVal = '';
    }
  }

  traverse = (node, tree) => {
    for (let i = 0; i < tree.length; i++) {
      tree[i].treeIndex = i;
      this.path.push(tree[i]);
      if (node.ref_var_name === tree[i].ref_var_name && node.ref_node_id === tree[i].ref_node_id) {
        return true;
      }
      if (tree[i].children) {
        if (this.traverse(node, tree[i].children)) {
          return true;
        }
      }
      this.path.pop();
    }
    return false;
  };

  findPath = (node, tree) => {
    this.path = [];
    this.urlPathIcon = null;
    this.inputFirstNode = '';
    this.inputNodeName = '';
    this.inputTypeString = null;
    this.showPathIcon = false;
    if (this.traverse(node, tree)) {
      let text = '';
      for (let i = 0; i < this.path.length; i++) {
        if (i === 0) {
          this.showPathIcon = true;
          this.urlPathIcon = WORKFLOW_SVGS[this.path[i].type];
          this.inputFirstNode = this.path[i].name;
        }
        if (i === this.path.length - 1) {
          this.inputNodeName = this.path[i].name;
          this.inputTypeString = this.path[i].type;
        }
        text += `${this.path[i].name}/`;
      }
      return text.slice(0, -1);
    } else {
      return '';
    }
  };

  treeToList(tree, text, val) {
    let list = [];
    for (let i = 0; i < tree.length; i++) {
      const index = tree[i].name.indexOf(val);
      let treeItemText = text;
      const topStr = text.length > 0 ? ' / ' : '';
      if (index >= 0) {
        treeItemText = [
          ...treeItemText,
          {
            key: false,
            text: `${topStr}${tree[i].name.substring(0, index)}`,
          },
          {
            key: true,
            text: tree[i].name.substring(index, index + val.length),
          },
          {
            key: false,
            text: tree[i].name.substring(index + val.length, tree[i].name.length),
          },
        ];
      } else {
        treeItemText = [
          ...treeItemText,
          {
            key: false,
            text: `${topStr}${tree[i].name}`,
          },
        ];
      }

      let childItem = [];
      if (tree[i].children) {
        childItem = this.treeToList(tree[i].children, treeItemText, val);
      }

      if (index >= 0 && isNodeRefSelectable(tree[i]) && text.length > 0) {
        list.push({ item: tree[i], text: treeItemText });
      }
      list = [...list, ...childItem];
    }

    return list;
  }

  selectItem(item) {
    if (!isNodeRefSelectable(item?.item)) {
      return;
    }
    this.closeSelectPanel();
    this.value = [item.item];
    setTimeout(() => {
      this.select.emit();
    });
  }

  treeNodeEnter(e, i) {
    this.treeSelectIndex = i;
    this.selectedTreeKeys = [];
    // 悬停切换一级时也用副本 + 当前值高亮，避免多个引用字段残留 checked
    const cloned = cloneTreeWithSelection(this.options[i]?.children || [], this._value, this.selectedTreeKeys);
    this.treeSelectIndexList = cloned.tree;
    const isTop = window.innerHeight - e.clientY < 300;
    if (isTop) {
      this.treeDivPosition = {
        top: `${e.currentTarget.offsetTop - this.selectDivDom.nativeElement.scrollTop + 40}px`,
        right: `${this.selectDivDom.nativeElement.offsetWidth + 1}px`,
        tr: 'translateY(-100%)',
      };
    } else {
      this.treeDivPosition = {
        top: `${e.currentTarget.offsetTop - this.selectDivDom.nativeElement.scrollTop - 8}px`,
        right: `${this.selectDivDom.nativeElement.offsetWidth + 1}px`,
        tr: 'translateY(0%)',
      };
    }
  }

  treeNodeLeave(e) {}

  onTreeSelect(e) {
    // 中间节点可展开但类型不兼容时 selectDisabled=true，禁止选中（仍可展开嵌套）
    if (!isNodeRefSelectable(e.node.origin)) {
      return;
    }
    this.closeSelectPanel();
    this.value = [e.node.origin];
    setTimeout(() => {
      this.select.emit();
    });
  }

  type2Img(type: INodeType | IWorkflowFieldType) {
    return NodeUtils.type2Img(type as INodeType);
  }

  getTreeNodeParamName(name: string) {
    return name?.split('.')?.pop() ?? '';
  }

  get domSelectTreeTop() {
    const rect = this.inputDom?.nativeElement?.getBoundingClientRect();
    if (!rect) return '0px';
    return `${rect.bottom}px`;
  }

  get domSelectTreeLeft() {
    const rect = this.inputDom?.nativeElement?.getBoundingClientRect();
    if (!rect) return '0px';
    return `${rect.left}px`;
  }

  get domSelectTreeWidth() {
    return `${this.inputDom?.nativeElement?.getBoundingClientRect().width || 0}px`;
  }

  get domSearchDivWidth() {
    return `${this.inputDom?.nativeElement?.getBoundingClientRect().width - 32 || 0}px`;
  }

  handelSelect() {
    this.select.emit();
  }
}
