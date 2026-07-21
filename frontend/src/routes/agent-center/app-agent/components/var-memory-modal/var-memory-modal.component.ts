import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  EventEmitter, Input, OnInit, Output,
  ViewChild
} from "@angular/core";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { MODULES } from "@shared/modules";
import { I18nNamespace } from "@i18n";
import { NgForm } from "@angular/forms";
import { AccBlockComponent } from "@routes/agent-center/app-flow/components/acc-block/acc-block.component";
import {
  LengthValidatorDirective,
  variableLongMemoryNameValidatorDirective
} from "@shared/directives/variable-name-validator.directive";
import { cdnAssetUrl } from "../../../../../single-spa/assets-url";
import { formatTime } from "src/utils/commonFn";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { NzMessageService } from "ng-zorro-antd/message";
import { AgentVarInfo, InputVarInfo } from "@routes/agent-center/types/my-workspace.types";
import { Subject, Subscription, takeUntil } from "rxjs";
import { WindowResizeService } from "@shared/base/window-resize.service";
import {
  CommonSelectType, MemoryVariableInputParamType,
  MemoryVariableType, MemoryVariableUserParamType
} from "@routes/agent-center/interfaces/agent/app-agent.interface";
import { AgentDataService } from "@services/agent-center/agent-data.service";
import { cloneDeep } from "lodash";
import { NzInputNumberModule } from 'ng-zorro-antd/input-number';
import { CommonNoDataComponent } from "@shared/components/common-no-data/common-no-data.component";

enum mapKeys {
  userVars = "userVars",
  inputVars = "inputVars",
}

@Component({
  selector: "meta-var-memory-modal",
  imports: [MODULES, AccBlockComponent, variableLongMemoryNameValidatorDirective, LengthValidatorDirective, CommonNoDataComponent],
  templateUrl: "./var-memory-modal.component.html",
  styleUrls: ["./var-memory-modal.component.scss"],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.AGENT]
    },
    NzMessageService
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: true
})
export class VarMemoryModalComponent implements OnInit {
  @ViewChild("varMemoryModal", { static: true }) varMemoryModal: any;
  @ViewChild("userForm") userForm: NgForm;
  @ViewChild("inputForm") inputForm: NgForm;
  @ViewChild("memoryVariableInputParams") memoryVariableInputParams: NgForm;
  @Input() actionType = "VIEW";
  @Input() agentId = "";
  @Input() isShowUserVars = true;
  @Input() isShowInputVars = true;
  @Output() saveMemoryVars = new EventEmitter<any>();
  public modalTop = "";
  public variableType: CommonSelectType[] = [
    {
      label: "String",
      value: "string"
    },
    {
      label: "Integer",
      value: "integer"
    },
    {
      label: "Number",
      value: "number"
    },
    {
      label: "Boolean",
      value: "boolean"
    }
  ];
  // 用户变量
  public customParams: MemoryVariableUserParamType[] = [];
  // 入参变量
  public inputParams: MemoryVariableInputParamType[] = [];
  // 在试运行页面展示的入参变量
  public copyInputParams: MemoryVariableInputParamType[] = [];
  // 复制一份旧的copyInputParamsName的值，用于预览调试时，用户填写错误数据时，数据能复原
  public oldCopyInputParams: MemoryVariableInputParamType[] = [];
  // 用户变量
  public oldCustomParamsName: Array<string> = [];
  isCanReset = true;
  selectedTabIndex = 0;
  displayedData: any[] = [];
  srcData: any = {
    data: [],
    state: undefined
  };
  listColumns: any[] = [
    {
      title: this.i18n.transform("varmemorymodalcomponent_225")
    },
    {
      title: this.i18n.transform("varmemorymodalcomponent_226")
    },
    {
      title: this.i18n.transform("operate")
    }
  ];
  noDataTitle: string = this.i18n.transform("no_memory");
  noDataDesc = [];
  loading = false;
  public windowWidth: number;
  private resizeSub: Subscription;
  protected readonly changeUrl = cdnAssetUrl;
  protected readonly formatTime = formatTime;
  public variableMemoryTabs: MemoryVariableType[] = [
    {
      id: "user",
      name: this.i18n.transform("varmemorymodalcomponent_217"),
      active: true
    },
    {
      id: "input",
      name: this.i18n.transform("variable-memory-tip3"),
      active: false
    }
  ];

  // 用户变量功能暂时不对外开放：isShowUserVars=false 时仅展示入参变量 tab
  public get visibleMemoryTabs(): MemoryVariableType[] {
    return this.isShowUserVars
      ? this.variableMemoryTabs
      : this.variableMemoryTabs.filter(tab => tab.id !== "user");
  }
  private destroy$ = new Subject<void>();

  constructor(
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private agentRepoService: AppAgentRepoService,
    private windowResizeService: WindowResizeService,
    private agentDataService: AgentDataService,
    private message: NzMessageService
  ) {
    this.agentDataService.inputMemoryVarsUpdate$().pipe(takeUntil(this.destroy$)).subscribe((list) => {
      this.copyInputParams = [];
      this.oldCopyInputParams = [];
      list?.map(varData => {
        this.copyInputParams.push({
          key: varData.variable_key,
          value: varData.default_value,
          description: varData.description,
          type: varData.input_type,
          isRight: true
        });
        this.oldCopyInputParams.push({
          key: varData.variable_key,
          value: varData.default_value,
          description: varData.description,
          type: varData.input_type,
          isRight: true
        });
      });
    });
  }

  ngOnInit(): void {
    this.resizeSub = this.windowResizeService.getWindowWidth().subscribe((width) => {
      this.windowWidth = width;
    });
  }

  trackByFn(index: number, item: any): number {
    return item.id;
  }

  public dismiss(): void {
    this.beforeHideModal();
  }

  public closeAndSaveMemoryVar(): void {
    if (this.actionType === "VIEW" && this.variableMemoryTabs[1].active) {
      this.setInputMemoryToPreview();
      this.beforeHideModal();
      return;
    }
    let hasError = false;
    if (this.isShowUserVars && this.userForm) {
      this.markFormDirty(this.userForm);
      if (this.userForm.invalid) {
        hasError = true;
      }
    }
    if (this.isShowInputVars && this.inputForm) {
      this.markFormDirty(this.inputForm);
      if (this.inputForm.invalid) {
        hasError = true;
      }
    }
    const data: any[] = [...this.customParams, ...this.inputParams];
    for (const item of data) {
      if (Object.prototype.hasOwnProperty.call(item, "isRight") && !item.isRight) {
        hasError = true;
        break;
      }
    }
    if (hasError) {
      this.cdr.markForCheck();
      return;
    }
    let result = {};
    if (this.isShowUserVars) {
      result[mapKeys.userVars] = this.customParams;
    }
    if (this.isShowInputVars) {
      this.formateInputParams(this.inputParams);
      result[mapKeys.inputVars] = this.inputParams;
    }
    this.saveMemoryVars.emit(result);
  }

  private markFormDirty(form: NgForm): void {
    Object.keys(form.controls).forEach(key => {
      form.controls[key].markAsDirty();
      form.controls[key].markAsTouched();
    });
  }

  // 在这里发送数据给预览调试
  public setInputMemoryToPreview() {
    this.agentDataService.setInputMemoryInPreviewDebugger(this.copyInputParams);
  }

  // 监听copyInputParams数据格式是否有问题
  public ngModelChangeCopyInputParams(param: MemoryVariableInputParamType): void {
    this.handleChangeInputParamType(param);
  }

  // 判断是否置灰确定按钮
  public isDisabledConfirmBtn(): boolean {
    if (this.actionType === "VIEW" && this.variableMemoryTabs[1].active) {
      let result: boolean = false;
      for (let index = 0; index < this.copyInputParams.length; index++) {
        if (Object.prototype.hasOwnProperty.call(this.copyInputParams[index], "isRight") && !this.copyInputParams[index].isRight) {
          result = true;
          break;
        }
      }
      return result;
    }
    const data: any[] = [...this.customParams, ...this.inputParams];
    let result = false;
    for (let index = 0; index < data.length; index++) {
      if (data[index].key === "") {
        result = true;
        break;
      }
      if (Object.prototype.hasOwnProperty.call(data[index], "isRight") && !data[index].isRight) {
        result = true;
        break;
      }
    }
    if (this.isShowUserVars && this.userForm?.invalid) {
      result = true;
    }
    if (this.isShowInputVars && this.inputForm?.invalid) {
      result = true;
    }
    return result;
  }

  public open(data?: Array<AgentVarInfo | InputVarInfo>, isShowUserVars = true, isShowInputVars = true) {
    this.isShowUserVars = isShowUserVars;
    this.isShowInputVars = isShowInputVars;
    this.oldCustomParamsName = [];
    this.customParams = [];
    this.inputParams = [];
    if (this.actionType === "VIEW") {
      this.isShowUserVars = false;
      this.variableMemoryTabs[0].active = false;
      this.variableMemoryTabs[1].active = true;
      this.selectedTabIndex = this.isShowUserVars ? 0 : 1;
      if(this.isShowUserVars){
        this.queryMemoryVarList();
      }
    } else {
      this.selectedTabIndex = 0;
      if (data?.length) {
        if (this.isShowUserVars) {
          this.setUserParamsData(data as Array<AgentVarInfo>);
        }
        if (isShowInputVars) {
          this.setInputParamsData(data as Array<InputVarInfo>);
        }
      }
    }
    this.varMemoryModal.open();
  }

  private setUserParamsData(data: AgentVarInfo[]): void {
    data.forEach(item => {
      this.customParams.push({
        key: item.variable_key,
        value: item.default_value,
        description: item.description
      });
    });
    this.oldCustomParamsName = data.map(item => item.variable_key);
  }

  private setInputParamsData(data: InputVarInfo[]): void {
    data.forEach(item => {
      this.inputParams.push({
        key: item.variable_key,
        value: item.default_value,
        description: item.description,
        type: item.input_type,
        isRight: true
      });
    });
  }

  isModelReachedParamLimit(type: "user" | "input") {
    if (type === "user") {
      return this.customParams.length >= 30;
    }
    return this.inputParams.length >= 30;
  }

  addInputParam(type: "user" | "input") {
    if (type === "user") {
      this.customParams.push({
        key: "",
        value: this.customParams.length.toString(),
        description: ""
      });
      return;
    }
    this.inputParams.push({
      key: "",
      value: this.inputParams.length.toString(),
      type: this.variableType[0].value,
      description: "",
      isRight: true
    });
  }

  deleteInputParam(event: Event, index: number, type: "user" | "input") {
    event.stopPropagation();
    if (type === "user") {
      this.customParams.splice(index, 1);
      return;
    }
    this.inputParams.splice(index, 1);
  }

  getUserNames(index: number): {
    existingValues: string[];
  } {
    const names = this.customParams.map((p) => p.key);
    names.splice(index, 1);
    return { existingValues: [...names] };
  }


  getInputNames(index: number): {
    existingValues: string[];
  } {
    const names = this.inputParams.map((p) => p.key);
    names.splice(index, 1);
    return { existingValues: [...names] };
  }

  queryMemoryVarList() {
    this.srcData.data = [];
    this.loading = true;
    this.isCanReset = true;
    this.agentRepoService.getNewLongMemoryVarList(this.agentId).then(res => {
      if (res.items.length > 0) {
        this.srcData.data = res.items;
      } else {
        this.isCanReset = false;
      }
      this.cdr.markForCheck();
      this.loading = false;
    }).catch(() => {
      this.loading = false;
    });
  }

  deleteVar(varKey: string) {
    if (varKey) {
      this.agentRepoService.batchDeleteVarByKey(this.agentId, [varKey]).then(res => {
        if (res) {
          this.message.success(this.i18n.transform("varmemorymodalcomponent_231"));
          this.queryMemoryVarList();
        }
      });
    }

  }

  resetAllLongMemoryVar() {
    if (this.isCanReset) {
      this.agentRepoService.ResetAllNewLongMemoryVar(this.agentId).then(res => {
        if (res?.result) {
          this.message.success(this.i18n.transform("varmemorymodalcomponent_231"));
          this.queryMemoryVarList();
        }
      });
    }
  }

  get halfModalWidth() {
    if (this.windowWidth > 1920) {
      return "800px";
    } else {
      return "600px";
    }
  }

  ngOnDestroy() {
    this.resizeSub?.unsubscribe();
  }

  // 切换tab窗口
  changeAppTab(tabData: MemoryVariableType) {
  }

  onVariableMemoryTabChange(index: number) {
    this.selectedTabIndex = index;
    this.variableMemoryTabs.forEach((tab, i) => {
      tab.active = i === index;
    });
  }

  // 当确认按钮失效时，按钮的提示信息告诉用户缺填的信息
  public disabledBtnContent() {
    return this.isDisabledConfirmBtn() ? this.i18n.transform("variable-memory-tip6") : "";
  }

  // 当输入数据的时候，需要判断用户输入的数据是否正确
  public handleChangeInputValue(data: MemoryVariableInputParamType) {
    this.handleChangeInputParamType(data);
  }

  // 当切换下拉框中的数据类型时，需要判断输入框中的数据格式是否正确
  public handleChangeInputParamType(data: MemoryVariableInputParamType) {
    data.errorMsg = '';
    if (data.type === "string") {
      data.isRight = true;
      return;
    }
    if (data.type === "integer") {
      if (!this.isIntegerString(data.value as string)) {
        data.isRight = false;
        data.errorMsg = this.getIntegerErrorMsg(data.value as string);
      } else {
        data.isRight = true;
      }
      return;
    }
    if (data.type === "number") {
      if (!this.isNumberString(data.value as string)) {
        data.isRight = false;
        data.errorMsg = this.getNumberErrorMsg(data.value as string);
      } else {
        data.isRight = true;
      }
      return;
    }
    if (data.type === "boolean") {
      data.isRight = this.isBooleanString(data.value as string);
      if (!data.isRight) {
        data.errorMsg = this.i18n.transform('variable-memory-tip5');
      }
      return;
    }
    return;
  }

  private getIntegerErrorMsg(str: string): string {
    if (!/^[-+]?\d+$/.test(str)) {
      return this.i18n.transform('variable-memory-tip5');
    }
    return this.i18n.transform('variable-memory-overflow');
  }

  private getNumberErrorMsg(str: string): string {
    if (!/^[-+]?(\d+\.?\d*|\.\d+)$/.test(str)) {
      return this.i18n.transform('variable-memory-tip5');
    }
    return this.i18n.transform('variable-memory-overflow');
  }

  // 判断是否是Integer类型
  private isIntegerString(str: string): boolean {
    if (str === "") {
      return true;
    }
    if (!/^[-+]?\d+$/.test(str)) {
      return false;
    }
    return Math.abs(Number(str)) <= Number.MAX_SAFE_INTEGER;
  }

  private isNumberString(str: string): boolean {
    if (str === "") {
      return true;
    }
    if (!/^[-+]?(\d+\.?\d*|\.\d+)$/.test(str)) {
      return false;
    }
    return Math.abs(Number(str)) <= Number.MAX_SAFE_INTEGER;
  }

  // 判断是否是Boolean类型
  private isBooleanString(str: string): boolean {
    if (str === "") {
      return true;
    }
    return str === "true" || str === "false";
  }

  // 格式化入参数据
  private formateInputParams(inputs: MemoryVariableInputParamType[]) {
    for (let index = 0; index < inputs.length; index++) {
      if (inputs[index].type === "integer") {
        inputs[index].value = this.changeStringToInt(inputs[index].value as string);
      } else if (inputs[index].type === "number") {
        inputs[index].value = this.changeStringToNumber(inputs[index].value as string);
      } else if (inputs[index].type === "boolean") {
        inputs[index].value = this.changeStringToBoolean(inputs[index].value as string);
      }
    }
  }

  // 将number类型的字符串转为number
  private changeStringToNumber(data: string): number {
    return Number(data);
  }

  // 将integer类型的字符串转为int
  private changeStringToInt(data: string): number {
    return parseInt(data, 10);
  }

  // 将boolean类型的字符串转为boolean
  private changeStringToBoolean(data: string): boolean {
    const trueValues = ["true"];
    return trueValues.includes(data);
  }

  // 弹框关闭前的回调事件
  public beforeHideModal(): void {
    if (this.actionType === "VIEW" && this.variableMemoryTabs[1].active) {
      this.setRollbackCopyInputParams();
    }
    this.varMemoryModal.close();
    this.variableMemoryTabs[0].active = true;
    this.variableMemoryTabs[1].active = false;
    this.selectedTabIndex = 0;
  }

  // 关闭弹框前要判断用户输入的入参变量是否合法，不合法要回滚数据
  private setRollbackCopyInputParams() {
    let isNeedRollback = false;
    for (let index = 0; index < this.copyInputParams.length; index++) {
      if (!this.copyInputParams[index].isRight) {
        isNeedRollback = true;
      }
    }
    if (isNeedRollback) {
      this.copyInputParams = cloneDeep(this.oldCopyInputParams);
    }
  }

  // 获取创建变量的抽屉标题
  public getVariableMemoryTitle() {
    if (this.isShowUserVars && this.isShowInputVars) {
      return "add_var";
    }
    if (this.isShowUserVars && !this.isShowInputVars) {
      return "add_var_user";
    }
    if (!this.isShowUserVars && this.isShowInputVars) {
      return "add_var_input";
    }
    return "add_var";
  }
}
