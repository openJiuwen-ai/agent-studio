import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component, EventEmitter,
  Input, Output, inject,
  Inject
} from "@angular/core";
import { CommonModule } from "@angular/common";
import { MODULES } from "@shared/modules";
import { I18nNamespace } from "@i18n";
import { I18NEXT_NAMESPACE, I18NextEagerPipe } from "angular-i18next";

import { AppFlowRepoService } from "@services/agent-center/app-flow-repo.service";
import { cdnAssetUrl } from "src/single-spa/assets-url";
import { AgentCenterHomeService } from "@services/agent-center/agent-center-home.service";
import { AppPluginRepoService } from "@services/agent-center/app-plugin-repo.service";
import { AppAgentRepoService } from "@services/agent-center/app-agent-repo.service";
import { v4 as uuidV4 } from "uuid";
import { environment } from "src/environment/environment";
import { ApplicationType } from "@enums/agent-center.enum";
import { MessageComponent } from '@shared/services/cfdata.service';
import { cloneDeep, uniqBy } from "lodash";
import { ImportResultModalComponent } from "@shared/components/import-modal/import-result-modal/import-result-modal.component";
import { NzModalRef, NZ_MODAL_DATA } from "ng-zorro-antd/modal";
import { NzModalService } from "ng-zorro-antd/modal";
import { NzShowUploadList } from "ng-zorro-antd/upload";
@Component({
  selector: "meta-import-modal",
  templateUrl: "./import-modal.component.html",
  styleUrls: ["./import-modal.component.scss"],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    MODULES
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [
        I18nNamespace.COMMON,
        I18nNamespace.AGENT_CENTER]
    }
  ]
})
export class ImportModalComponent {
  readonly modalRef = inject(NzModalRef);
  @Input() importToolType = ApplicationType.SINGLE_AGENT;

  @Input() importTypeOptions = [
    {
      id: ApplicationType.SINGLE_AGENT,
      text: this.i18n.transform("import_to_agent")
    },
    {
      id: ApplicationType.WORKFLOW,
      text: this.i18n.transform("import_to_workflow")
    }
  ];

  @Output() importSuccess = new EventEmitter();
  public max_size = 128 * 1024 * 1024;
  public upload_type = [".jsonl"];

  // 是否上传了文件。用于控制空状态的文字说明
  public isFileImported = false;

  public parseContent: Array<any> = [];

  // 父级对应的选中值
  public parentContentChecked: any = [];

  // 子级对应的选中值
  public childContentChecked: any = [];

  // 第三层对应的选中值
  public grandChildContentChecked: any = [];

  // 将三层和二层合并
  public all_child_checked = [];

  public alertContent = "";

  public isLoading = false;

  // 是否正在导入中
  public isImporting = false;

  // 上传的本地文件，解析是否出错
  public isParseError = false;

  // 上传的本地文件，解析是否存在重复内容
  public isDuplicateContent = false;

  // 上传文件类型的判断
  public import_type_tip = false;

  public cdnUrl = cdnAssetUrl;

  public fileInfo: File;

  public isSelectError = false;
  public isOldImport = false; // 是否为旧版本导入文件
  public bottomTip = "";
  checkedList: Array<any> = [];
  displayedData: Array<any> = [];
  srcData: any = {
    data: [],
    state: undefined
  };

  // 解析出的依赖type字段与中文名称的映射关系
  private typeMapping = {
    workflow: this.i18n.transform("workflow"),
    agent: this.i18n.transform("single_agent"),
    controller: this.i18n.transform("multiple_agent"),
    model: this.i18n.transform("model"),
    tool: this.i18n.transform("插件"),
    repo: "repo",
    strategy: this.i18n.transform("route_policy"),
    provider: this.i18n.transform("model_supplier"),
    card: this.i18n.transform("Card"),
    sql: "sql",
    functiongraph: "FunctionGraph"
  };

  public columns: Array<any> = [
    {
      title: this.i18n.transform("agent_name"),
      width: "40%",
      key: "name"
    },
    {
      title: this.i18n.transform("description"),
      width: "30%",
      key: "description"
    },
    {
      title: this.i18n.transform("status"),
      width: "30%",
      key: "import_description"
    }
  ];

  get fileButtonName() {
    if (this.parseContent.length) {
      return this.i18n.transform("re_select");
    } else {
      return this.i18n.transform("select_file");
    }
  }

  /** 导入按钮是否置灰 */
  get isCanImport() {
    if (!this.parseContent.length) {
      return true;
    }

    const hasWorkflowType = this.parseContent.some(
      (item) => item.type === this.importToolType
    );
    return !hasWorkflowType;
  }

  get isShowRemoveBtn() {
    return (
      environment.envType === "poc" &&
      this.parseContent.length &&
      this.importToolType === ApplicationType.WORKFLOW
    );
  }

  public get isWorkflow() {
    return this.importToolType === ApplicationType.WORKFLOW;
  }

  uploadFileList = [];

  showUploadList: boolean | NzShowUploadList = false;

  constructor(
    private appFlowRepoServe: AppFlowRepoService,
    private appPluginRepoServe: AppPluginRepoService,
    private ppServ: AgentCenterHomeService,
    private service: AppAgentRepoService,
    private cdr: ChangeDetectorRef,
    private i18n: I18NextEagerPipe,
    private nzModal: NzModalService,
    @Inject(NZ_MODAL_DATA) private modalData: any,
  ) {
    this.importToolType = modalData.importToolType;
    this.importTypeOptions = modalData.importTypeOptions;
  }

  ngOnInit() {
    if (this.importToolType === ApplicationType.WORKFLOW) {
      this.columns[0].title = this.i18n.transform("workflow_name");
    }
    if (this.importToolType === ApplicationType.MULTI_AGENT) {
      this.columns[0].title = this.i18n.transform("controller_name");
    }
    if (this.importToolType === ApplicationType.PLUGIN) {
      this.columns[0].title = this.i18n.transform("plugin_name");
    }
  }

  /*拍平树*/
  public flattenTreeDFS(root) {
    const result = [];

    function flattenDFS(node) {
      if (node === null) return;
      const { id, description, name, prohibited, status, type, import_description, isChecked } = node;
      result.push({ id, description, name, prohibited, status, type, import_description, isChecked });
      if (node.dependencies) {
        for (const child of node.dependencies) {
          flattenDFS(child);
        }
      }

    }

    flattenDFS(root);
    return result;
  }

  public onAddFileSuccess(fileItem: any): void {
    this.showUploadList = false;
    if (fileItem.type === "removed") {
      this.onRemoveItems(null);
      return;
    }
    if (fileItem.type !== "start") {
      return;
    }

    if (this.uploadFileList.length >= 2) {
      this.uploadFileList = [this.uploadFileList[1]];
    }

    if (this.uploadFileList.length >= 1) {
      setTimeout(() => {
        this.uploadFileList[0].status = 'done';
        this.uploadFileList[0].response = '';
        this.uploadFileList[0].error = '';
        this.showUploadList = {
          showRemoveIcon: true,
          showPreviewIcon: false,
          showDownloadIcon: false
        };
        this.cdr.markForCheck();
      }, 50);
    }

    this.isFileImported = true;
    this.isParseError = false;
    this.isDuplicateContent = false;
    this.isSelectError = false;
    this.fileInfo = fileItem.file.originFileObj;
    this.isLoading = true;
    const formData = new FormData();
    formData.append("file", fileItem.file.originFileObj);
    this.appFlowRepoServe.parseFile(formData).then(
      (res: any) => {
        this.isLoading = false;
        this.isOldImport = !Boolean(res[0]?.import_description);
        this.isDuplicateContent = this.checkDuplicateContent(res);
        // 通过增加 dependencies: [], 保证插件对应的jsonl文件解析出的数据结构和工作流一致
        const filter_res = this.filteredRes(res);
        this.import_type_tip = filter_res.length <= 0;
        this.parseContent = filter_res.map((item) => ({
          ...item,
          collapsed: true,
          dependencies: (item?.dependencies || []).map((childItem) => ({
            ...childItem,
            collapsed: true,
            uniqueId: `${item.id}-${childItem.id}-${uuidV4()}`,
            disabled: childItem.status,
            dependencies: (childItem?.dependencies || []).map(
              (grandChildItem) => ({
                ...grandChildItem,
                uniqueId: `${item.id}-${childItem.id}-${
                  grandChildItem.id
                }-${uuidV4()}`,
                disabled: grandChildItem.status
              })
            )
          }))
        }));
        this.parseContent = this.initializeCheckStatus(this.parseContent);

        const copy_data = cloneDeep(this.parseContent);

        for (let i = 0; i < copy_data.length; i++) {
          copy_data[i].plat_dependencies = [];
          for (let j = 0; j < copy_data[i].dependencies.length; j++) {
            const new_sub_dependencies = this.flattenTreeDFS(copy_data[i].dependencies[j]);
            copy_data[i].plat_dependencies.push(...new_sub_dependencies);
          }
        }

        for (let i = 0; i < copy_data.length; i++) {
          copy_data[i].dependencies = uniqBy(copy_data[i].plat_dependencies, "id");
        }

        this.parseContent = copy_data;
        this.srcData.data = this.parseContent;
        // prohibited等于true，表示这是不允许导入的预置插件
        this.parentContentChecked = [...this.parseContent].filter(
          (item) => !item.prohibited
        );
        const { childChecked, grandChildChecked } = this.checkAllDependencies(
          this.parseContent
        );
        this.childContentChecked = childChecked;
        this.grandChildContentChecked = grandChildChecked;
        this.cdr.markForCheck();
      },
      () => {
        this.isLoading = false;
        this.isParseError = true;
        this.parseContent = [];
        this.parentContentChecked = [];
        this.childContentChecked = [];
        this.grandChildContentChecked = [];
        this.all_child_checked = [];
        this.srcData.data = [];
        this.cdr.markForCheck();
      }
    );
  }

  public onAddItemFailed(info) {
    const error_type = info.validResults[0];
    if (error_type === "type") {
      MessageComponent.showError(
        this.i18n.transform("only_support_upload_format", { types: this.upload_type.join(",") }),
        3000
      );
    }
    if (error_type === "maxSize") {
      MessageComponent.showError(
        this.i18n.transform("file_size_cannot_exceed", { size: this.max_size / (1024 * 1024) }),
        3000
      );
    }
  }

  public onRemoveItems(info) {
    this.parseContent = [];
    this.isFileImported = false;
    this.srcData.data = [];
  }

  public dismiss() {
    this.modalRef.destroy();
  }

  /** 点击弹窗的导入按钮 */
  public async importTool() {
    const checkIds = this.collectCheckedIds(this.parseContent);
    if (checkIds.length <= 0) {
      this.isSelectError = true;
      return;
    }
    this.isImporting = true;
    // 导入插件
    let res = null;
    let importType = "";
    try {
      if (this.importToolType === ApplicationType.PLUGIN) {
        const formData = new FormData();
        const pluginListStr = checkIds
          .filter((item) => item.type === "Plugin")
          .map((item) => item.id)
          .join(",");

        formData.append("file", this.fileInfo);
        formData.append("import_ids", pluginListStr);
        res = await this.appPluginRepoServe.importPlugin(formData);
        importType = "plugin";
      } else if (this.importToolType === ApplicationType.WORKFLOW) {
        // 导入工作流
        const formData = new FormData();
        formData.append("file", this.fileInfo);
        if (this.isOldImport) {
          const dependencies = this.getAllDependencies(this.parseContent, checkIds);
          const mergedArray = [...checkIds, ...dependencies];
          const flows = this.extractIdsByType(mergedArray, this.importToolType);
          const plugins = this.extractIdsByType(mergedArray, "Plugin");
          formData.append("import_workflows", flows);
          formData.append("import_tools", plugins);
        }
        res = await this.appFlowRepoServe.importWorkflow(formData);
        importType = "workflow";
      } else {
        // 导入知识型Agent
        const formData = new FormData();
        const flowIdsChecked = checkIds.filter(
          (item) => item.type === "workflow"
        );
        const dependencies = this.getAllDependencies(
          this.parseContent,
          flowIdsChecked
        );
        formData.append("file", this.fileInfo);
        if (this.isOldImport) {
          const mergedArray = [...checkIds, ...dependencies];
          const agents = this.importToolType === "controller"
            ? this.extractIdsByType(mergedArray, this.importToolType, ["agent"])
            : this.extractIdsByType(mergedArray, this.importToolType);
          const flows = this.extractIdsByType(mergedArray, "workflow");
          const plugins = this.extractIdsByType(mergedArray, "Plugin");
          formData.append("import_agents", agents);
          formData.append("import_workflows", flows);
          formData.append("import_tools", plugins);
        }
        res = await this.service.importAgents(formData);
        importType = "agent";
      }
      ;
    } catch (error) {
      this.isImporting = false;
      this.cdr.markForCheck();
      this.dismiss();
      return;
    }
    this.clearImportAlert();
    this.isImporting = false;
    this.cdr.markForCheck();
    this.dismiss();
    if (this.isOldImport) {
      this.ppServ.setImportRes({
        ...res,
        isShow: "success",
        importType
      });
    } else {
      this.importSuccess.emit();
      const thisNzModal: any = this.nzModal.create({
        nzContent: ImportResultModalComponent,
        nzWidth: "700px"
      });
      const instance = thisNzModal.getContentComponent();
      instance.importResult = res;
      instance.importToolType = this.importToolType;
    }
    ;
  }

  public changeCollapsedState(item: any) {
    if (item?.dependencies && item.dependencies.length === 0) {
      return;
    }
    item.collapsed = !item.collapsed;
  }

  /** 获取type字段对应的中文名称 */
  public getTypeName(type: string): string {
    return this.typeMapping[type] || type;
  }


  /** 自定义父依赖的点击事件，并更新父依赖复选框的选中状态 */
  public customParentChecked(event: any, parentItem: any): void {
    const inputElement = event.target as HTMLInputElement;
    const isChecked = inputElement.checked;
    parentItem.isChecked = isChecked;
    if (!isChecked) {
      // 取消父级的√后，移除该父级对应的所有子项选中状态，即dependencies字段
      this.childContentChecked = this.childContentChecked?.filter(
        (item: any) =>
          !this.containsItem(parentItem.dependencies, item.uniqueId, item.type)
      );
      this.grandChildContentChecked = this.grandChildContentChecked?.filter(
        (gCItem: any) => {
          return !parentItem.dependencies.some(
            (cItem: any) =>
              cItem.dependencies &&
              this.containsItem(
                cItem.dependencies,
                gCItem.uniqueId,
                gCItem.type
              )
          );
        }
      );
      // 置灰该父级对应的所有子项和孙级
      parentItem.dependencies.forEach((childItem: any) => {
        childItem.disabled = false;
        if (childItem.dependencies) {
          childItem.dependencies.forEach((grandChildItem: any) => {
            grandChildItem.disabled = false;
          });
        }
      });
    } else {
      // 重新√上父级后，该父级对应的所有子项和第三层恢复一开始的选中状态
      this.childContentChecked = [
        ...(this.childContentChecked || []),
        ...parentItem.dependencies
      ].filter((item) => !item.prohibited);
      parentItem.dependencies.forEach((childItem: any) => {
        if (childItem.dependencies) {
          this.grandChildContentChecked = [
            ...(this.grandChildContentChecked || []),
            ...(childItem.dependencies || [])
          ];
        }
      });
      // 有重复内容的子项和第三层展示为浅蓝色，表示禁止取消选中
      parentItem.dependencies.forEach((item: any) => {
        item.disabled = item.status;
        if (item.dependencies) {
          item.dependencies.forEach((grandChildItem: any) => {
            grandChildItem.disabled = grandChildItem.status;
          });
        }
      });
    }
  }

  /** 检查子依赖数组中是否包含传入的id和类型对应的元素 */
  private containsItem(list: any, id: string, type: string): boolean {
    return list?.some((item) => item.uniqueId === id && item.type === type);
  }

  /** 初始化依赖数组中的isChecked字段，默认值为true，表示选中 */
  private initializeCheckStatus(parseContent: any[]): any[] {
    return parseContent.map(item => this.processItem(item));
  }

  private processItem(item: any): any {
    if (!item) return item;

    // 为当前项添加isChecked属性
    item.isChecked = true;

    // 递归处理dependencies
    if (item.dependencies && item.dependencies.length > 0) {
      item.dependencies = item.dependencies.map((dependency: any) =>
        this.processItem(dependency)
      );
    }

    return item;
  }

  /**
   * 由于文件解析接口未区分type。
   * 若是从知识型Agent打开导入弹窗，则只保留父依赖类型是"agent"的。插件和工作流同理
   */
  private filteredRes(res: any) {
    return res.filter((item) => {
      if (this.importToolType === ApplicationType.SINGLE_AGENT) {
        return item.type === ApplicationType.SINGLE_AGENT;
      } else if (this.importToolType === ApplicationType.PLUGIN) {
        return item.type !== "workflow" && item.type !== "agent";
      } else if (this.importToolType === ApplicationType.WORKFLOW) {
        return item.type === ApplicationType.WORKFLOW;
      } else if (this.importToolType === ApplicationType.MULTI_AGENT) {
        return item.type === ApplicationType.MULTI_AGENT;
      }
      return true;
    });
  }

  /** 收集被选中的依赖id，组装导入接口的入参 */
  private collectCheckedIds(parentContent: any[]): any[] {
    let checkedIds = [];
    parentContent.forEach((item) => {
      if (item.isChecked) {
        checkedIds.push({ id: item.id, type: item.type });
      }
      if (item.dependencies && item.dependencies.length > 0) {
        item.dependencies.forEach((subItem) => {
          if (subItem.isChecked) {
            checkedIds.push({ id: subItem.id, type: subItem.type });
          }
        });
      }
    });
    return checkedIds;
  }

  /** 默认选中所有解析出来的依赖列表 */
  private checkAllDependencies(parseContent: any) {
    const hasEmptyDependencies = parseContent.some(
      (parentItem) =>
        !parentItem.dependencies || parentItem.dependencies.length === 0
    );
    // 文件解析返回的数据结构只有1层
    if (hasEmptyDependencies) {
      return parseContent.map((item) => item);
    }

    // 文件解析返回的数据结构有2层嵌套 或者 3层嵌套结构
    const childChecked = [];
    const grandChildChecked = [];
    parseContent.forEach((parentItem) => {
      if (!parentItem.dependencies || parentItem.dependencies.length === 0) {
        childChecked.push(parentItem);
      } else {
        parentItem.dependencies.forEach((childItem) => {
          childChecked.push(childItem);
          if (childItem.dependencies && childItem.dependencies.length > 0) {
            grandChildChecked.push(...childItem.dependencies);
          }
        });
      }
    });
    return { childChecked, grandChildChecked };
  }

  /** 检查本地文件解析出的依赖列表是否存在重复内容 */
  private checkDuplicateContent(parseContent: any): boolean {
    return parseContent.some((parentItem) => {
      // 检查父级依赖的status
      if (parentItem.status === true) {
        return true;
      }
      // 检查子级依赖的status
      return parentItem.dependencies?.some(
        (dependency) => dependency.status === true
      );
    });
  }

  private clearImportAlert() {
    this.ppServ.setImportRes({
      succeed_len: 0,
      failed_len: 0,
      inner_plugins_msg: [],
      isShow: "back",
      importType: ""
    });
  }

  /** 获取所有被选中的父级所需的依赖列表 */
  private getAllDependencies(parseData, checkIds) {
    const res = [];

    const matchedNodes = this.getMatchingNodes(parseData, checkIds);
    matchedNodes.forEach((item) => {
      this.collectDeps([item], res);
    });

    return res;
  }

  /** 从文件解析出的嵌套数据结构中，获取被选中的父级所在的对象 */
  private getMatchingNodes(parseData, checkIds) {
    const res: any[] = [];

    // 遍历parseData中的每个对象，并递归搜索
    parseData.forEach((item) => this.searchDependencies(item, checkIds, res));
    return res;
  }

  /** 递归搜索文件解析出的嵌套数据结构 */
  private searchDependencies(item, checkIds, res) {
    // 若找到，则存入结果数组res
    if (checkIds.some((check) => check.id === item.id)) {
      res.push(item);
    }

    // 递归
    item.dependencies?.forEach((dep) =>
      this.searchDependencies(dep, checkIds, res)
    );
  }

  /** 从被选中的某个父级所在的对象里，递归获取嵌套的dependencies中的所有依赖列表 */
  private collectDeps(parseObj, res) {
    if (!parseObj?.length) {
      return;
    }

    parseObj.forEach((item) => {
      if (!item.dependencies?.length) {
        return;
      }

      item.dependencies.forEach((dep: any) => {
        res.push({
          id: dep.id,
          type: dep.type,
          prohibited: dep?.prohibited
        });

        // 递归
        this.collectDeps([dep], res);
      });
    });
  }

  /** 组装导入接口入参 */
  private extractIdsByType(arr, type, additionalType = []) {
    const filteredItems = arr.filter((item) => {
      if (type === "Plugin") {
        return item.type === "Plugin" && item.prohibited !== true; // 过滤prohibited等于true的预置插件
      }
      return item.type === type || additionalType.includes(item.type);
    });
    const uniqueIds = new Set(filteredItems.map((item) => item.id));
    return Array.from(uniqueIds).join(",");
  }

  public getStatusInfo(childItem) {
    const typeMap = {
      "newResource": {
        icon: "cloudx-action-state-operation",
        color: "#5db303",
        text: this.i18n.transform("add_resource"),
        tip: this.i18n.transform("add_resource_tip")
      },
      "newResourceVersion": {
        icon: "cloudx-action-state-operation",
        color: "#5db303",
        text: this.i18n.transform("add_resource_version"),
        tip: this.i18n.transform("add_resource_version_tip")
      },
      "updateResource": {
        icon: "cloudx-action-state-operation",
        color: "#5db303",
        text: this.i18n.transform("update_resource"),
        tip: this.i18n.transform("update_resource_tip")
      },
      "resourceExists": {
        icon: "cloudx-action-state-freeze",
        color: "#fe8803",
        text: this.i18n.transform("exist_resource"),
        tip: this.i18n.transform("exist_resource_tip")
      },
      "prohibited": {
        icon: "cloudx-action-state-freeze",
        color: "#fe8803",
        text: this.i18n.transform("prohibited_resource"),
        tip: this.i18n.transform("prohibited_resource_tip")
      },
      "oldUpdateResource": {
        icon: "cloudx-action-state-operation",
        color: "#5db303",
        text: this.i18n.transform("update_resource"),
        tip: this.i18n.transform("update_resource_tip2")
      },
      "resourceMatch": {
        icon: "cloudx-action-state-operation",
        color: "#5db303",
        text: this.i18n.transform("match_resource"),
        tip: this.i18n.transform("match_resource_tip")
      },
      "resourceNotMatch": {
        icon: "cloudx-action-state-freeze",
        color: "#fe8803",
        text: this.i18n.transform("not_match_resource"),
        tip: this.i18n.transform("not_match_resource_tip")
      }
    };

    if (childItem.prohibited) {
      return typeMap.prohibited;
    } else {
      if (this.isOldImport && this.importToolType === ApplicationType.PLUGIN) {
        // 旧格式插件没有 import_description。status=true 表示同一资源已存在，
        // 后端会覆盖更新；status=false 才是新增，不能再展示成“资源已存在并跳过”。
        return childItem.status ? typeMap.updateResource : typeMap.newResource;
      } else if (childItem.import_description) {
        return typeMap[childItem.import_description];
      } else { // 旧版本导入文件
        return typeMap[childItem.status ? "resourceExists" : "oldUpdateResource"];
      }
    }
  }
}
