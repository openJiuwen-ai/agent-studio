import {
  AfterViewInit,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  OnInit
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { FormsModule, UntypedFormArray, UntypedFormBuilder, UntypedFormGroup, AbstractControl, ValidationErrors, Validators } from "@angular/forms";
import { NzDrawerModule, NzDrawerRef } from "ng-zorro-antd/drawer";
import { NzAlertModule } from "ng-zorro-antd/alert";
import { NzButtonModule } from "ng-zorro-antd/button";
import { NzIconModule } from "ng-zorro-antd/icon";
import { NzInputModule } from "ng-zorro-antd/input";
import { NzSelectModule } from "ng-zorro-antd/select";
import { NzTagModule } from "ng-zorro-antd/tag";
import { NzToolTipModule } from "ng-zorro-antd/tooltip";
import { NzFormModule } from "ng-zorro-antd/form";
import { DragDropModule, CdkDragDrop, moveItemInArray } from "@angular/cdk/drag-drop";
import { Subject, takeUntil } from "rxjs";
import { debounceTime, distinctUntilChanged } from "rxjs/operators";
import { v4 as uuidV4 } from "uuid";
import { GuideCardItemComponent } from "./components/guide-card-item/guide-card-item.component";
import { DependencyItemComponent } from "./components/dependency-item/dependency-item.component";
import { ScenarioGuideModalService } from "./scenario-guide-modal.service";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";
import { I18nNamespace } from "@i18n";
import {
  IGuide,
  type ISceneData,
  ISkillChildrenOption,
  ITool,
  PERFORM_ACTION_MAX_LEN,
  SCENE_DESC_MAX_LEN,
  SCENE_NAME_MAX_LEN,
  TRIGGER_CON_MAX_LEN,
  SCENARIO_FIELD_ID,
  FIELD_TYPE,
  LEAST_GUIDE_COUNT,
  LEAST_DEPENDENCY_GUIDE_COUNT
} from "./scenario-guide-modal.constant";
import { MODULES } from "@shared/modules";

@Component({
  selector: "app-scenario-guide-modal",
  templateUrl: "./scenario-guide-modal.component.html",
  styleUrls: ["./scenario-guide-modal.component.scss"],
  standalone: true,
  imports: [
    MODULES,
    CommonModule,
    DragDropModule,
    GuideCardItemComponent,
    DependencyItemComponent
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER, I18nNamespace.COMMON]
    }
  ]
})
export class ScenarioGuideModalComponent implements OnInit, AfterViewInit, OnDestroy {
  @Input() skillSetOptions: any[];
  @Input() originData: ISceneData;
  @Input() saveData: Function;
  @Input() curSceneMaxGuideCount: number;

  protected SCENARIO_FIELD_ID = SCENARIO_FIELD_ID;
  protected FIELD_TYPE = FIELD_TYPE;
  protected LEAST_GUIDE_COUNT = LEAST_GUIDE_COUNT;
  protected LEAST_DEPENDENCY_GUIDE_COUNT = LEAST_DEPENDENCY_GUIDE_COUNT;

  public modalLoaded = false;
  public modalData: ISceneData;
  public modalFormGroup: UntypedFormGroup;
  public guideFormList: UntypedFormArray;
  public dependencyFormList: UntypedFormArray;
  public dependencyCollapsed = true;
  public dependencyOptions = [];
  public highlightedCycleRows = new Set<number>();
  public cycleErrorMessage = "";
  public inValidGuideGlobalTip = "";
  public inValidGuideGlobalOpen = true;
  public guideFormListData = [];
  public dependencyFormListData = [];
  public confirmBtnLoading = false;
  private ngUnsubscribe = new Subject<void>();

  public guideFormConfig = {
    [SCENARIO_FIELD_ID.TRIGGER_CONDITION]: {
      label: this.i18n.transform("trigger_condition_label"),
      id: SCENARIO_FIELD_ID.TRIGGER_CONDITION,
      helpTip: this.i18n.transform("trigger_condition_tip"),
      required: true,
      errorTip: this.i18n.transform("trigger_condition_not_empty_tip"),
      validators: [
        Validators.required,
        (control: AbstractControl): ValidationErrors | null => this.getTriggerRenameValidator()(control)
      ],
      type: FIELD_TYPE.TEXT_INPUT
    },
    [SCENARIO_FIELD_ID.PERFORM_ACTION]: {
      label: this.i18n.transform("perform_action_label"),
      id: SCENARIO_FIELD_ID.PERFORM_ACTION,
      helpTip: this.i18n.transform("perform_action_tip"),
      required: true,
      errorTip: this.i18n.transform("perform_action_not_empty_tip"),
      validators: [Validators.required],
      type: FIELD_TYPE.TEXT_INPUT
    },
    [SCENARIO_FIELD_ID.SKILL_SET]: {
      label: this.i18n.transform("skill_set_label"),
      id: SCENARIO_FIELD_ID.SKILL_SET,
      helpTip: this.i18n.transform("skill_set_tip"),
      validators: [],
      type: FIELD_TYPE.SELECT
    }
  };

  public dependencyFormConfig = {
    [SCENARIO_FIELD_ID.DEPEND_ITEM]: {
      label: "",
      id: SCENARIO_FIELD_ID.DEPEND_ITEM,
      required: true,
      errorTip: this.i18n.transform("dependency_item_required_tip"),
      validators: [Validators.required],
      type: FIELD_TYPE.SELECT
    },
    [SCENARIO_FIELD_ID.DEPEND_SYMBOL]: {
      label: "",
      id: SCENARIO_FIELD_ID.DEPEND_SYMBOL,
      defaultValue: this.i18n.transform("dependent_relation_label"),
      type: FIELD_TYPE.TEXT_INPUT
    },
    [SCENARIO_FIELD_ID.BE_DEPENDED_ITEM]: {
      label: "",
      id: SCENARIO_FIELD_ID.BE_DEPENDED_ITEM,
      required: true,
      errorTip: this.i18n.transform("be_depended_item_required_tip"),
      type: FIELD_TYPE.SELECT,
      validators: [Validators.required]
    }
  };

  public modalFormConfig = {
    [SCENARIO_FIELD_ID.SCENE_NAME]: {
      label: this.i18n.transform("scene_label"),
      id: SCENARIO_FIELD_ID.SCENE_NAME,
      required: true,
      errorTip: this.i18n.transform("scene_name_not_empty_tip"),
      validators: [Validators.required],
      defaultValue: ""
    },
    [SCENARIO_FIELD_ID.SCENE_DESC]: {
      label: this.i18n.transform("description_label"),
      id: SCENARIO_FIELD_ID.SCENE_DESC,
      defaultValue: "",
      validators: []
    },
    [SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST]: {
      label: this.i18n.transform("guide_config_label"),
      id: SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST,
      defaultValue: [],
      children: this.guideFormConfig
    },
    [SCENARIO_FIELD_ID.DEPENDENCY_LIST]: {
      label: "",
      id: SCENARIO_FIELD_ID.DEPENDENCY_LIST,
      defaultValue: [],
      children: this.dependencyFormConfig
    }
  };

  public modalFormData = {
    [SCENARIO_FIELD_ID.SCENE_NAME]: "",
    [SCENARIO_FIELD_ID.SCENE_DESC]: ""
  };

  constructor(
    private i18n: I18NextEagerPipe,
    private formBuilder: UntypedFormBuilder,
    private scenarioGuideModalServ: ScenarioGuideModalService,
    private cdr: ChangeDetectorRef,
    private elementRef: ElementRef,
    private drawerRef: NzDrawerRef
  ) {
  }

  public cancel(): void {
    this.drawerRef.close();
  }

  ngOnInit(): void {
  }

  ngAfterViewInit() {
    const guideLines = this.scenarioGuideModalServ.getGuideFormDataByOrigin(this.originData);
    this.initGuideFormListData(this.originData?.guidelines);
    this.updateDependencyOptions(guideLines);

    let defaultData;
    if (this.originData?.id) {
      defaultData = {
        [SCENARIO_FIELD_ID.SCENE_NAME]: this.originData.name,
        [SCENARIO_FIELD_ID.SCENE_DESC]: this.originData.description,
        [SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST]: guideLines,
        [SCENARIO_FIELD_ID.DEPENDENCY_LIST]: this.originData.relations?.map((item) => ({
          [SCENARIO_FIELD_ID.DEPEND_ITEM]: this.dependencyOptions.find((option) => item.src === option.priority),
          [SCENARIO_FIELD_ID.BE_DEPENDED_ITEM]: this.dependencyOptions.find((option) => item.tgt === option.priority)
        }))
      };
    }

    this.modalFormGroup = this.getFormGroup(this.modalFormConfig, defaultData);
    this.initDependencyFormListData(this.dependencyFormList.value);
    this.updateAvailableBOptions();
    this.updateInValidGuideGlobalTip();
    this.dependencyCollapsed = !this.dependencyFormList.value?.length;

    if (this.originData?.id) {
      this.checkFormValid();
    }

    this.guideFormList.valueChanges.pipe(takeUntil(this.ngUnsubscribe)).subscribe((data) => {
      this.updateDependencyOptions(data);
    });

    this.dependencyFormList.valueChanges.pipe(
      takeUntil(this.ngUnsubscribe),
      debounceTime(150),
      distinctUntilChanged()
    ).subscribe(() => {
      this.updateAvailableBOptions();
      this.checkCycleDependencies();
    });

    this.modalLoaded = true;
  }

  ngOnDestroy(): void {
    this.ngUnsubscribe.next();
    this.ngUnsubscribe.complete();
  }

  public onConfirm(): void {
    this.guideFormList.controls?.forEach((formGroup, index) => {
      this.removeEffectiveSkillTip(formGroup, this.guideFormListData[index]);
    });
    const result = this.checkFormValid();
    if (result) {
      this.modalData = this.scenarioGuideModalServ.getModalData(this.modalFormGroup, this.originData);
      this.saveData?.();
    }
  }

  public drop(event: CdkDragDrop<string[]>): void {
    moveItemInArray(this.guideFormList.controls, event.previousIndex, event.currentIndex);
    moveItemInArray(this.guideFormListData, event.previousIndex, event.currentIndex);
    this.updateDependencyOptions(this.guideFormList.controls.map((item) => item.value));
  }

  public changeCardCollapse(item, formGroup?: any, targetValue?: boolean): void {
    const originCollapse = item[SCENARIO_FIELD_ID.COLLAPSE];
    this.collapseAllGuideCard();
    item[SCENARIO_FIELD_ID.COLLAPSE] = targetValue ?? !originCollapse;
    if (!item[SCENARIO_FIELD_ID.COLLAPSE]) {
      setTimeout(() => {
        const originData = formGroup?.value;
        (formGroup as UntypedFormGroup)?.patchValue(originData, { onlySelf: true });
      }, 100);
    }
  }

  public deleteGuide(index): void {
    if (this.guideFormListData.length === 1) {
      return;
    }
    this.guideFormListData.splice(index, 1);
    this.guideFormList.removeAt(index);
    if (this.guideFormListData.length === 1) {
      this.guideFormListData[0][SCENARIO_FIELD_ID.COLLAPSE] = false;
      this.dependencyFormList.clear();
      this.dependencyFormListData = [];
    }
    this.updateInValidGuideGlobalTip();
  }

  public deleteDependency(index: number): void {
    this.dependencyFormListData.splice(index, 1);
    this.dependencyFormList.removeAt(index);
  }

  public addGuide(): void {
    if (this.guideFormListData.length >= this.curSceneMaxGuideCount) {
      return;
    }
    this.collapseAllGuideCard();
    const rowValue = {
      randomId: uuidV4(),
      [SCENARIO_FIELD_ID.COLLAPSE]: false,
      deletedSkills: [],
      effectiveSkills: []
    };
    this.guideFormListData.push(rowValue);
    this.guideFormList.push(this.getFormGroup(this.guideFormConfig));
  }

  public addDependency(): void {
    this.dependencyFormListData.push(this.initDependencyRowData());
    this.dependencyFormList.push(this.getFormGroup(this.dependencyFormConfig));
  }

  public trackById(item): string {
    return item.randomId;
  }

  public changeDependencyCollapse(): void {
    this.dependencyCollapsed = !this.dependencyCollapsed;
  }

  public removeDeletedSkillTip(guideData): void {
    guideData.deletedSkills = [];
    guideData.invalidSkillTip = this.getInvalidSkillTip(guideData.deletedSkills, guideData.effectiveSkills);
    this.updateInValidGuideGlobalTip();
  }

  public removeEffectiveSkillTip(formGroup, guideData): void {
    const originSkill = formGroup.value?.[SCENARIO_FIELD_ID.SKILL_SET] || [];
    formGroup.patchValue({
      [SCENARIO_FIELD_ID.SKILL_SET]: originSkill.filter((item) => !item.disabled)
    });
    guideData.effectiveSkills = [];
    guideData.deletedSkills = [];
    guideData.invalidSkillTip = this.getInvalidSkillTip(guideData.deletedSkills, guideData.effectiveSkills);
    this.updateInValidGuideGlobalTip();
  }

  private dependencyRowsCompleteValidator = (control: AbstractControl): ValidationErrors | null => {
    const rows = control.value || [];
    const hasIncomplete = rows.some(
      (item) => !item?.[SCENARIO_FIELD_ID.DEPEND_ITEM] || !item?.[SCENARIO_FIELD_ID.BE_DEPENDED_ITEM]
    );
    return hasIncomplete ? { incomplete: true } : null;
  };

  private getFormGroup(formConfig: any, defaultData?: any): UntypedFormGroup {
    const formGroup = this.formBuilder.group({});
    Object.keys(formConfig).forEach((key) => {
      const formItem = formConfig[key];
      let field: any;

      if (formItem.id === SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST) {
        const defaultGuidelines = defaultData?.[SCENARIO_FIELD_ID.GUIDE_CONFIG_LIST];
        if (defaultGuidelines?.length) {
          field = this.formBuilder.array(defaultGuidelines.map((item) => this.getFormGroup(formItem.children, item)));
        } else {
          field = this.formBuilder.array([this.getFormGroup(formItem.children)]);
        }
        this.guideFormList = field;
      } else if (formItem.id === SCENARIO_FIELD_ID.DEPENDENCY_LIST) {
        const defaultRelations = defaultData?.[SCENARIO_FIELD_ID.DEPENDENCY_LIST];
        const relationControls = defaultRelations?.length
          ? defaultRelations.map((item) => this.getFormGroup(formItem.children, item))
          : [];
        field = this.formBuilder.array(relationControls, {
          validators: [this.dependencyRowsCompleteValidator]
        });
        this.dependencyFormList = field;
      } else {
        field = this.formBuilder.control(defaultData?.[formItem.id] || formItem.defaultValue, formItem.validators);
      }
      formGroup.addControl(formItem.id, field);
    });
    return formGroup;
  }

  private initGuideFormListData(guideLines: IGuide[] = []): void {
    const dataLength = guideLines.length || 1;
    this.guideFormListData = Array.from({ length: dataLength }, (_, index) => {
      const deletedSkills = guideLines[index]?.deletedSkills || [];
      const effectiveSkills = guideLines[index]?.effectiveSkills || [];
      const invalidSkillTip = this.getInvalidSkillTip(deletedSkills, effectiveSkills);
      return {
        randomId: uuidV4(),
        [SCENARIO_FIELD_ID.COLLAPSE]: index !== dataLength - 1,
        deletedSkills,
        effectiveSkills,
        invalidSkillTip
      };
    });
  }

  private getInvalidSkillTip(deletedSkills: ITool[] = [], effectiveSkills: ISkillChildrenOption[] = []): string {
    const deletedSkillsName = deletedSkills.map((item) => item.name).join("、");
    const effectiveSkillsName = effectiveSkills.map((item) => item.label).join("、");

    if (deletedSkills.length && effectiveSkills.length) {
      return this.i18n.transform("scene_guide_invalid_skill_remove_tip")
        .replace("{{deletedSkills}}", deletedSkillsName)
        .replace("{{effectiveSkills}}", effectiveSkillsName);
    }
    if (deletedSkills.length) {
      return this.i18n.transform("scene_guide_deleted_skill_remove_tip").replace("{{deletedSkills}}", deletedSkillsName);
    }
    if (effectiveSkills.length) {
      return this.i18n.transform("scene_guide_effectiveSkill_skill_remove_tip").replace("{{effectiveSkills}}", effectiveSkillsName);
    }
    return "";
  }

  private updateInValidGuideGlobalTip(): void {
    const invalidCount = this.guideFormListData.filter((item) => !!(item.deletedSkills?.length || item.effectiveSkills?.length)).length;
    this.inValidGuideGlobalTip = this.inValidGuideGlobalOpen && invalidCount
      ? this.i18n.transform("scene_guide_skill_abnormal_tip", { count: invalidCount })
      : "";
  }

  private initDependencyFormListData(data = []): void {
    this.dependencyFormListData = data.map((item, index) => this.initDependencyRowData());
  }

  private initDependencyRowData() {
    return {
      randomId: uuidV4(),
      aOptions: [],
      bOptions: []
    };
  }

  private collapseAllGuideCard(): void {
    this.guideFormListData.forEach((item) => {
      item[SCENARIO_FIELD_ID.COLLAPSE] = true;
    });
  }

  private updateDependencyOptions(guideDta = []): void {
    this.dependencyOptions = guideDta.map((item, index) => {
      const priorityText = this.i18n.transform("guide_priority_label", {
        priorityIndex: this.scenarioGuideModalServ.getPriorityByIndex(index)
      });
      return {
        ...item,
        id: this.guideFormListData[index]?.randomId,
        priority: this.scenarioGuideModalServ.getPriorityByIndex(index),
        priorityText,
        name: item[SCENARIO_FIELD_ID.TRIGGER_CONDITION] || priorityText
      };
    });
  }

  private updateAvailableBOptions(): void {
    this.dependencyFormList.controls.forEach((rowControl, index) => {
      this.dependencyFormListData[index].bOptions = this.computeAvailableBOptions(rowControl, index);
      const bValueId = rowControl?.value?.[SCENARIO_FIELD_ID.BE_DEPENDED_ITEM]?.id;
      if (bValueId && !this.dependencyFormListData[index].bOptions.find((item) => item.id === bValueId)) {
        rowControl.patchValue({ [SCENARIO_FIELD_ID.BE_DEPENDED_ITEM]: undefined });
      }
    });
  }

  private computeAvailableBOptions(rowControl: AbstractControl, currentIndex: number) {
    const dependItemControl = rowControl.get(SCENARIO_FIELD_ID.DEPEND_ITEM);
    const selectedA = dependItemControl.value?.id;
    if (!dependItemControl || !selectedA) {
      return this.dependencyOptions;
    }

    const forbiddenBs = new Set<string>();
    forbiddenBs.add(selectedA);

    this.dependencyFormList.controls.forEach((control, index) => {
      const aControl = control.get(SCENARIO_FIELD_ID.DEPEND_ITEM);
      const bControl = control.get(SCENARIO_FIELD_ID.BE_DEPENDED_ITEM);
      if (aControl?.value?.id === selectedA && bControl?.value?.id && currentIndex !== index) {
        forbiddenBs.add(bControl.value?.id);
      }
    });

    return !forbiddenBs.size ? this.dependencyOptions : this.dependencyOptions.filter((opt) => !forbiddenBs.has(opt.id));
  }

  private checkCycleDependencies() {
    const graph: { [key: string]: Set<string> } = {};
    const rowData: { aValue: string | null; bValue: string | null }[] = [];

    this.dependencyFormList.controls.forEach((ctrl, idx) => {
      const aValue = ctrl.get(SCENARIO_FIELD_ID.DEPEND_ITEM)?.value?.id;
      const bValue = ctrl.get(SCENARIO_FIELD_ID.BE_DEPENDED_ITEM)?.value?.id;
      rowData.push({ aValue, bValue });
      if (aValue && bValue && aValue !== bValue) {
        if (!graph[aValue]) graph[aValue] = new Set();
        graph[aValue].add(bValue);
      }
    });

    const cyclePath = this.findCyclePath(graph, Object.keys(graph));

    if (cyclePath?.length >= 3) {
      const cycleEdges = cyclePath.slice(0, -1).map((node, i) => [node, cyclePath[i + 1]]);
      const indices = new Set<number>();

      rowData.forEach((row, idx) => {
        if (row.aValue && row.bValue && cycleEdges.some((edge) => edge[0] === row.aValue && edge[1] === row.bValue)) {
          indices.add(idx);
        }
      });

      this.highlightedCycleRows = indices;
      this.cycleErrorMessage = this.formatCycleMessage(cyclePath);
    } else {
      this.highlightedCycleRows = new Set();
      this.cycleErrorMessage = "";
    }
  }

  private findCyclePath(graph: { [key: string]: Set<string> }, nodes: string[]): string[] | null {
    const visited = new Set<string>();
    const recStack: string[] = [];
    const indexMap = new Map<string, number>();

    const dfs = (node: string): string[] | null => {
      visited.add(node);
      recStack.push(node);
      indexMap.set(node, recStack.length - 1);

      for (const neighbor of graph[node] || []) {
        if (indexMap.has(neighbor)) {
          const start = indexMap.get(neighbor)!;
          const cycle = recStack.slice(start);
          cycle.push(neighbor);
          return cycle;
        }
        if (!visited.has(neighbor)) {
          const res = dfs(neighbor);
          if (res) return res;
        }
      }

      indexMap.delete(node);
      recStack.pop();
      return null;
    };

    for (const node of nodes) {
      if (!visited.has(node)) {
        const cycle = dfs(node);
        if (cycle) return cycle;
      }
    }
    return null;
  }

  private formatCycleMessage(path: string[]): string {
    const chain = path.slice(0, -1).map((node, i) => {
      const nodeName = this.dependencyOptions?.find((item) => item.id === node)?.name;
      const nodeNameAfter = this.dependencyOptions?.find((item) => item.id === path[i + 1])?.name;
      return this.i18n.transform("dependency_related_ab_label", { a: nodeName, b: nodeNameAfter });
    }).join("、");
    return this.i18n.transform("dependency_cycle_tip", { chain });
  }

  private getTriggerRenameValidator() {
    return (control: AbstractControl): ValidationErrors | null => {
      if (!control.value || !this.guideFormList?.length) return null;

      const currentIndex = this.guideFormList.controls.findIndex(
        (group) => (group as UntypedFormGroup).get(SCENARIO_FIELD_ID.TRIGGER_CONDITION) === control
      );

      if (currentIndex === -1 || this.guideFormList.length <= 1) return null;

      for (let i = 0; i < this.guideFormList.length; i++) {
        if (i === currentIndex) continue;
        const otherGroup = this.guideFormList.at(i) as UntypedFormGroup;
        const otherTriggerControl = otherGroup.get(SCENARIO_FIELD_ID.TRIGGER_CONDITION);
        if (otherTriggerControl?.value && otherTriggerControl.value === control.value) {
          return { reName: { message: this.i18n.transform("trigger_condition_rename_tip") } };
        }
      }
      return null;
    };
  }

  private checkFormValid(): boolean {
    this.modalFormGroup.markAllAsTouched();
    this.triggerControlStatusChanges(this.modalFormGroup);
    if (this.modalFormGroup.valid) {
      this.guideFormListData.forEach((item) => { item.inValid = false; });
      return true;
    }

    this.guideFormListData.forEach((item, index) => {
      const guideGroup = this.guideFormList.at(index) as UntypedFormGroup;
      item.inValid = guideGroup.invalid;
    });

    const dependencyErrorKeys = Object.keys(this.modalFormGroup.get(SCENARIO_FIELD_ID.DEPENDENCY_LIST)?.errors || {});

    if (dependencyErrorKeys.length || this.cycleErrorMessage) {
      this.dependencyCollapsed = false;
    }

    setTimeout(() => {
      let elementRef;
      if (this.modalFormGroup.get(SCENARIO_FIELD_ID.SCENE_NAME)?.invalid) {
        elementRef = this.elementRef.nativeElement.querySelector(`[id=${SCENARIO_FIELD_ID.SCENE_NAME}]`);
      } else {
        const firstInvalidGuideIndex = this.guideFormListData.findIndex((item) => item.inValid);
        if (firstInvalidGuideIndex !== -1) {
          elementRef = this.elementRef.nativeElement.querySelector(`[id=guideCard${firstInvalidGuideIndex}]`);
          this.changeCardCollapse(this.guideFormListData[firstInvalidGuideIndex], this.guideFormList?.controls?.[firstInvalidGuideIndex], false);
        } else if (dependencyErrorKeys.length) {
          const firstInvalidDependencyIndex = this.dependencyFormList.controls.findIndex((item) => item.invalid);
          if (firstInvalidDependencyIndex !== -1) {
            elementRef = this.elementRef.nativeElement.querySelector(`[id=dependency${firstInvalidDependencyIndex}]`);
          }
        }
      }
      elementRef?.scrollIntoView({ behavior: "smooth" });
    }, 100);

    return false;
  }

  private triggerControlStatusChanges(control: AbstractControl): void {
    if (control instanceof UntypedFormArray) {
      control.controls.forEach(child => this.triggerControlStatusChanges(child));
    } else if (control instanceof UntypedFormGroup) {
      Object.values(control.controls).forEach(child => this.triggerControlStatusChanges(child));
    }
    control.updateValueAndValidity({ emitEvent: true, onlySelf: true });
  }
}
