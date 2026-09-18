import { TextFieldModule } from '@angular/cdk/text-field';
import { CommonModule } from '@angular/common';
import {
  Component,
  Input,
  QueryList,
  SimpleChanges,
  ViewChildren,
} from '@angular/core';
import {
  FormBuilder,
  FormControl,
  FormGroup,
  ValidationErrors,
  Validators,
} from '@angular/forms';
import { I18nNamespace } from '@i18n';
import { MonacoEditorModule } from '@materia-ui/ngx-monaco-editor';
import { agentCommonLogic } from '@routes/agent-center/app-agent/common-logic-agent';
import { AppAgentRepoService } from '@services/agent-center/app-agent-repo.service';
import { ToolService } from '@services/tool.service';
import { AssetFormatIconComponent } from '@shared/components/assets/asset-format-icon/asset-format-icon.component';
import { MODULES } from '@shared/modules';

import { I18NEXT_NAMESPACE, I18NextEagerPipe } from 'angular-i18next';
import { cloneDeep, isNil } from 'lodash';
import { cdnAssetUrl } from 'src/single-spa/assets-url';
import { AppFlowService } from '@routes/agent-center/app-flow/app-flow.service';
import { Subject, takeUntil } from 'rxjs';
import { MessageComponent } from '@shared/services/cfdata.service';
import { v4 as uuidV4 } from 'uuid';
import {
  createFileItem,
  uploadFile,
  validateFileSize,
} from '@routes/agent-center/multiUpload.utils';
import { UploadFileIconComponent } from '../upload-file-icon/upload-file-icon.component';
import {
  UploadFileAccPipe,
  UploadFileDescPipe,
} from 'src/pipes/upload-file.pipe';
import { NodeUtils } from '@routes/agent-center/app-flow/components/utils';
import { checkFileTypeAndSize } from '@routes/agent-center/utils';
import { AgentConfigService } from '@routes/agent-center/agent-config.service';

@Component({
  selector: 'dynamic-node-params',
  templateUrl: './dynamic-node-params.component.html',
  styleUrls: [
    './dynamic-node-params.component.less',
    '../../../styles/text-field-prebuilt.css',
  ],
  standalone: true,
  imports: [
    CommonModule,
    MODULES,
    TextFieldModule,
    MonacoEditorModule,
    AssetFormatIconComponent,
    UploadFileIconComponent,
    UploadFileAccPipe,
    UploadFileDescPipe,
  ],
  providers: [
    {
      provide: I18NEXT_NAMESPACE,
      useValue: [I18nNamespace.AGENT_CENTER],
    },
  ],
})
export class DynamicNodeParamsComponent {
  @Input() inputList: any = [];
  @Input() uriType: string;

  @ViewChildren('editor') editors: QueryList<any>;
  @ViewChildren('fileInput') fileInputs: QueryList<any>;

  private editorsMap = new Map<string, any>();

  public parameterFromGroup: FormGroup;

  public startNodeInputs: any = [];

  public oldStartNodeInputs: any[] = [];

  public validation: any = {
    type: 'changeAlert',
  };

  public editorOptions = this.toolServ.EditorOptions;

  public changeUrl = cdnAssetUrl;

  public fileLoading = false;

  public isUploading = false;
  public inputIndex: number;
  public multiType: string;

  public getType = NodeUtils.getFieldTypeView;

  private fileList = [];

  private destroy$ = new Subject<void>();

  constructor(
    private fb: FormBuilder,
    private toolServ: ToolService,
    private commonLogic: agentCommonLogic,
    private appAgentServe: AppAgentRepoService,
    private i18n: I18NextEagerPipe,
    private appFlowServe: AppFlowService,
    private configServ: AgentConfigService,
  ) {
    this.parameterFromGroup = this.fb.group({});

    this.appFlowServe
      .fileListUpdate$()
      .pipe(takeUntil(this.destroy$))
      .subscribe((fileList: any[]) => {
        this.fileList = fileList;
      });
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.inputList) {
      this.oldStartNodeInputs = cloneDeep(this.startNodeInputs);
      this.startNodeInputs = cloneDeep(changes.inputList.currentValue);
      // 回填已上传的文件信息
      this.inputList = this.inputList.map((item: any) => {
        if (item.type.includes('array<file')) {
          const isFileExist = item.value.default;
          if (isFileExist) {
            const display = item.value.display ?? '';
            const names = display.split(',');
            let uploadDatas = [];
            try {
              const urlArr = JSON.parse(isFileExist);
              uploadDatas = urlArr.map((item, i) => ({
                fileId: uuidV4(),
                name: names[i] || this.getFileNameByUrl(item),
                url: item,
              }));
            } catch (e) {
              uploadDatas = isFileExist.split(',').map((item, i) => ({
                fileId: uuidV4(),
                name: names[i] || this.getFileNameByUrl(item),
                url: item,
              }));
            }
            return {
              ...item,
              uploadDatas,
            };
          }
        } else {
          const isFileExist = this.fileList.find(
            (file) => file.name === item.name && file.type === item.type,
          );
          if (isFileExist) {
            return {
              ...item,
              file: isFileExist.file,
              uploadData: isFileExist.uploadData,
            };
          }
          const { type, value } = item;
          if (type?.includes('file') && value?.default) {
            return {
              ...item,
              uploadData: {
                name:
                  item.value.display || this.getFileNameByUrl(value.default),
                progress: 'succeeded',
                url: value.default,
              },
            };
          }
        }
        return item;
      });

      this.initDynamicForm(this.startNodeInputs);

      /**
       * 在子组件中设置model Uri
       * 作用：确保更新画布数据后，<ngx-monaco-editor>使用自定义的model Uri，而不是默认的inmemory Uri
       * !!!必须要setTimeout，确保monaco编辑器已初始化
       */
      setTimeout(() => {
        if (typeof monaco !== 'undefined') {
          // 记录复杂类型的index
          let editorIndex = 0;

          this.inputList.forEach((inputItem) => {
            // 只处理复杂类型：object 或 array
            if (this.isComplexType(inputItem.type)) {
              // 根据复杂参数类型和名称，生成model Uri
              const modelUri = this.commonLogic.getModelUriByType(
                inputItem.type,
                inputItem.name,
                this.uriType,
              );
              const existingModelUri = monaco.editor.getModel(
                monaco.Uri.parse(modelUri),
              );
              // 获取<ngx-monaco-editor>实例
              const editorInstance = this.editors.toArray()[editorIndex].editor;

              if (!existingModelUri) {
                // 使用用户已填入的JSON文本创建新模型，并绑定到对应的Uri上
                const model = monaco.editor.createModel(
                  inputItem.controlValue,
                  'json',
                  monaco.Uri.parse(modelUri),
                );
                editorInstance.setModel(model);
              }

              // 手动触发校验
              const model = editorInstance.getModel();
              if (model) {
                const markers = monaco.editor.getModelMarkers({
                  resource: model.uri,
                });
                // 将标记设置到对应的model实例上
                monaco.editor.setModelMarkers(model, 'owner', markers);
              }
              // 复杂类型index递增
              editorIndex += 1;
            }
          });
        }
        this.updateEditorValues(this.inputList);
        this.resetValidationRes();
      }, 0);
    }
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  getPlaceholder(item) {
    if (item.front_content) {
      return item.front_content;
    }

    return `${this.i18n.transform('input_placeholder')} ${item.name}`;
  }

  public patchFormValue(formData, newInputList) {
    this.parameterFromGroup.patchValue(formData);
    this.updateEditorValues(newInputList, true);
}

  public isShowEditor(type: string) {
    if (type === 'object') {
      return true;
    }
    const [prefix] = type.split('<');
    return prefix === 'array' && !type.includes('file');
  }

  public handleUserInput(control_name: string, isValidate: boolean) {
    // 用户输入时重置错误标志，立即清除错误提示
    const inputItem = this.inputList?.find(item => item.name === control_name);
    if (inputItem) {
      inputItem.isEmpty = false;
      inputItem.isError = false;
    }
    // 启用校验
    const control = this.parameterFromGroup.get([`${control_name}`]);
    if (control) {
      control.setValidators(null);
      control.updateValueAndValidity();
    }
  }

  /** 校验基础类型参数是否合法。点击【开始运行】按钮，触发该函数 */
  public validatePrimitiveInputs() {
    let pass = true;

    this.inputList
      ?.filter(
        (requirement) =>
          (this.isPrimitiveType(requirement.type) &&
            requirement.type !== 'boolean') ||
          requirement.type.startsWith('file'),
      )
      .forEach((requirement: any) => {
        const { name } = requirement;
        const control = this.parameterFromGroup.get([`${name}`]);
        const validators = requirement.required
          ? [
              Validators.required,
              Validators.maxLength(10000000),
            ]
          : null;

        this.updateFileControlValue(requirement, this.parameterFromGroup);
        control.setValidators(validators);
        control.updateValueAndValidity();
        if (control.hasError('required')) {
          pass = false;
          requirement.isEmpty = true;
        }
      });
      return pass;
  }

  /** 获取表单中的输入值，包括基础类型和复杂类型 */
  public getDynamicParams(skipFiles = false) {
    const formValues: { [key: string]: any } = {};
    this.inputList.forEach((item) => {
      if (
        skipFiles &&
        (item.type.startsWith('file') || item.type.startsWith('array<file'))
      ) {
        return;
      }
      let value;
      if (this.isPrimitiveType(item.type)) {
        value = this.getControlValue(item.name);
      } else if (item.type.startsWith('file')) {
        value = item?.uploadData?.url;
      } else if (item.type.startsWith('array<file')) {
        value = item?.uploadDatas?.map((file) => file.url);
      } else {
        const stringVal = this.getEditorValueByName(item.name);
        try {
          value = JSON.parse(stringVal);
        } catch {
          value = null;
        }
      }
      formValues[item.name] = value;
    });
    return formValues;
  }

  /** 调用 Monaco Editor Format API，格式化输入内容 */
  public formatJson(name: string) {
    this.initEditorsMap();
    const editorComponent = this.editorsMap.get(name);
    const editorInstance = editorComponent?.editor;
    if (editorInstance) {
      editorInstance.getAction('editor.action.formatDocument').run();
    }
  }

  /** 根据控件名称，获取formGroup表单中的输入值 */
  public getControlValue(controlName: string) {
    return this.parameterFromGroup.get([`${controlName}`])?.value;
  }

  /** 根据控件名称，获取 <ngx-monaco-editor> 编辑器双向绑定的输入值 */
  public getEditorValueByName(controlName: string): any {
    const inputItem = this.inputList.find((item) => item.name === controlName);
    return inputItem ? inputItem.controlValue : null;
  }

  /** 设置默认值 **/
  public getEditorDefaultValueByName(controlName: string): any {
    const inputItem = this.inputList.find((item) => item.name === controlName);
    if (inputItem?.value?.default) {
      return inputItem.value.default;
    }
    return inputItem ? inputItem.controlValue : null;
  }

  /** 根据控件名称，获取file/*类型的上传文件 */
  public getFileInfoByName(name: string): any {
    return this.inputList.find((item) => item.name === name);
  }

  /** 清空上一次的校验结果和错误标记 */
  public resetValidationRes() {
    // 记录复杂类型的index
    let editorIndex = 0;
    this.inputList.forEach((inputItem) => {
      if (this.isComplexType(inputItem.type)) {
        inputItem.isError = false;
        inputItem.isEmpty = false;
      }

      if (this.isComplexType(inputItem.type)) {
        const editorInstance = this.editors.toArray()[editorIndex].editor;
        const model = editorInstance?.getModel();
        // 清空错误标记
        if (typeof monaco !== 'undefined') {
          monaco.editor.setModelMarkers(model, 'owner', []);
        }
        editorIndex += 1;
      }
    });
  }

  /** 校验 Object 或 Array 复杂类型是否合法。点击【开始运行】按钮，触发该函数 */
  public validateJsonSchemas() {
    // 清空上一次的校验结果和错误标记
    this.resetValidationRes();

    // 记录复杂类型的index
    let editorIndex = 0;
    this.inputList.forEach((inputItem) => {
      if (this.isComplexType(inputItem.type)) {
        const editorInstance = this.editors.toArray()[editorIndex].editor;
        const model = editorInstance.getModel();
        const markers = monaco.editor.getModelMarkers({ resource: model?.uri });
        const errors = markers.filter(
          (marker) => marker.severity === monaco.MarkerSeverity.Error,
        );
        const rawValue = editorInstance.getValue().trim();
        const isEmpty = rawValue === '';
        let hasError = errors.length > 0;
        // 语法合法且非空时，再校验值是否符合声明的复杂类型（如 array<object> 必须是对象数组）
        if (!hasError && !isEmpty) {
          let parsed: any;
          try {
            parsed = JSON.parse(rawValue);
          } catch {
            parsed = undefined;
          }
          if (parsed === undefined || !this.matchType(parsed, inputItem.type, inputItem.children ?? inputItem.schema)) {
            hasError = true;
          }
        }
        inputItem.isError = hasError;
        inputItem.isEmpty = isEmpty;
        // 复杂类型index递增
        editorIndex += 1;
      }

      this.updateFileControlValue(inputItem, this.parameterFromGroup);
      // 判断上传文件是否为空
      const errors: ValidationErrors | null = null;

      if (errors) {
        Object.keys(errors).forEach((error) => {
          const errorItem = this.inputList.find((item) => item.name === error);
          if (errorItem.type.startsWith('file')) {
            errorItem.isEmpty = true;
          }
        });
      }
    });
    return this.inputList;
  }

  /** 初始化动态表单 */
  private initDynamicForm(list: any) {
    this.parameterFromGroup = this.fb.group({});
    list?.forEach((requirement: any) => {
      let { controlValue, value } = requirement;
      let defaultValue = value?.default || controlValue;
      if (requirement.type === 'integer' || requirement.type === 'number') {
        defaultValue = isNaN(Number(defaultValue)) ? 0 : Number(defaultValue);
      }
      const possiableDefaultValue = this.getDefaultValue(requirement);
      if (possiableDefaultValue) {
        defaultValue = possiableDefaultValue;

        if (requirement.type === 'boolean') {
          defaultValue = defaultValue === 'true' || defaultValue === true;
        }
        if (requirement.type === 'integer' || requirement.type === 'number') {
          defaultValue = isNaN(Number(defaultValue)) ? 0 : Number(defaultValue);
        }
      } else {
        // 修复开始节点配置boolean类型并且初始值为false时，该boolean类型字段未传递给试运行接口
        if (requirement.type === 'boolean') {
          defaultValue = defaultValue ?? false;
        }
      }

      this.parameterFromGroup.addControl(requirement.name, new FormControl(defaultValue, []));
    });
  }

  /** 使用writeValue，回填monaco-editor编辑器的值 */
  private updateEditorValues(inputList, isFullyCover = false) {
    let editorIndex = 0;
    if (isFullyCover) {
      this.initEditorsMap();
    }
    inputList.forEach((inputItem) => {
      // 复杂类型的处理
      const editor = isFullyCover
        ? this.editorsMap.get(inputItem.name)
        : this.editors.toArray()[editorIndex];
      if (this.isComplexType(inputItem.type) && editor) {
        if (inputItem.children && !isFullyCover) {
          //创建工具调测使用场景，结构中存在children
          inputItem.controlValue =
            this.getObjectDefault(inputItem) ?? inputItem.controlValue;
        } else {
          inputItem.controlValue = isFullyCover
            ? inputItem.value.default
            : this.getDefaultValue(inputItem) ?? inputItem.controlValue;
        }
        editor.writeValue(inputItem.controlValue);
        editorIndex += 1;
      }
    });
  }

  private getObjectDefault(item: any) {
    let defaultValue = '';
    //注意：transformTree(item) 在调试的复杂类型时会多出一层
    let processedData = {};
    try {
      if (item.type === 'object') {
        processedData = this.transformTree(item.children)
        defaultValue = JSON.stringify(processedData);
      } else if (item.type.startsWith('array')) {
        processedData = this.transformTree(item.children)
        defaultValue = JSON.stringify([processedData]);
      }
    } catch {
      defaultValue = '';
    }
    const isNew = !this.oldStartNodeInputs.find(
      (input) => input.name === item.name,
    );

    return (isNew || !item?.controlValue) && !isNil(defaultValue)
      ? defaultValue
      : null;
  }

  private transformTree(node: any) {
    if(node instanceof Array){
      //兼容父级object 子 array
      const childrenArray = node.map((child) =>
        this.transformTree(child),
      );
      let childrenItem = {};
      childrenArray.forEach((item) => {
        childrenItem = { ...childrenItem, ...item };
      });
      return childrenItem
    } else if (node.children && node.children.length > 0) {
      const childrenArray = node.children.map((child) =>
        this.transformTree(child),
      );
      if (node.type === 'object') {
        let childrenItem = {};
        childrenArray.forEach((item) => {
          childrenItem = { ...childrenItem, ...item };
        });
        return {
          [node.name]: childrenItem,
        };
      } else {
        return {
          [node.name]: childrenArray,
        };
      }
    } else {
      return {
        [node.name]: node.default,
      };
    }
  }

  private getDefaultValue(item: any) {
    const defaultValue = item.value?.default;
    const isNew = !this.oldStartNodeInputs.find(
      (input) => input.name === item.name,
    );

    return (isNew || !item?.controlValue) && !isNil(defaultValue)
      ? defaultValue
      : null;
  }

  private initEditorsMap() {
    this.editors.forEach((editor: any) => {
      const name = editor.uri.path.split('/')
        .pop()
        ?.split('-')[1]
        ?.replace('.json', '');
      this.editorsMap.set(name, editor);
    });
  }

  /** 判断类型是否为基础类型 */
  private isPrimitiveType(type: string): boolean {
    return (
      type === 'string' ||
      type === 'integer' ||
      type === 'number' ||
      type === 'boolean'
    );
  }

  /** 判断类型是否为复杂类型 */
  private isComplexType(type: string): boolean {
    if (type.includes('array<file')) {
      return false;
    }
    return type === 'object' || type.startsWith('array');
  }

  /**
   * 判断解析后的 JSON 值是否符合声明的复杂类型（object / array / array<T>）。
   * subFields 为 object / array<object> 元素的子字段声明，存在时递归校验声明字段的类型
   * （仅校验声明字段，缺失/未知字段不报错）。subFields 兼容两种来源：
   *   - children：前端配置侧格式（IWFViewWithMultiType[]，type 为 string[]）
   *   - schema：后端格式（IWorkflowField[]，type 为 string，子字段声明在 .schema）
   */
  private matchType(value: any, type: string, subFields?: any): boolean {
    if (type === 'object') {
      if (typeof value !== 'object' || value === null || Array.isArray(value)) {
        return false;
      }
      return this.matchObjectFields(value, subFields);
    }
    if (type === 'array') {
      if (!Array.isArray(value)) {
        return false;
      }
      // subFields 可能为元素描述（{type:元素类型, schema:子字段声明}），解析元素类型并递归校验每个元素
      // 兼容后端 schema 格式：array + schema={type:'object',schema:[...]}
      const elementType = this.schemaFieldType(subFields);
      if (elementType == null || elementType === 'any') {
        return true; // 无元素类型声明，仅校验是数组
      }
      const elementSchema = this.schemaFieldSchema(subFields);
      return value.every((el) => this.matchElementType(el, elementType, elementSchema));
    }
    if (type.startsWith('array<') && type.endsWith('>')) {
      const elementType = type.slice(6, -1).trim(); // 'object' | 'string' | 'integer' | 'number' | 'boolean' | 'any'
      if (!Array.isArray(value)) {
        return false;
      }
      if (elementType === 'any') {
        return true;
      }
      return value.every((el) => {
        // array<object> 时，subFields 可能为元素描述（后端 schema 格式 {type:object,schema:[...]}），
        // 需先 schemaFieldSchema 提取子字段列表，否则 asFieldList 返回 null 跳过嵌套校验
        const elementSubFields = Array.isArray(subFields) ? subFields : this.schemaFieldSchema(subFields);
        return this.matchElementType(el, elementType, elementSubFields);
      });
    }
    // 基础类型（递归 object 子字段时可能走到这里）
    return this.matchElementType(value, type);
  }

  /**
   * 校验 object 值中已声明字段的类型。仅校验声明且存在值的字段；
   * 字段缺失或出现未声明字段均不报错（与"仅校验声明字段类型"的严格度一致）。
   * subFields 兼容 children（type:string[]）与 schema（type:string + .schema）两种来源。
   */
  private matchObjectFields(objValue: any, subFields?: any): boolean {
    const fields = this.asFieldList(subFields);
    if (!fields || fields.length === 0) {
      return true; // 无子字段声明，不校验内部
    }
    for (const field of fields) {
      const childValue = objValue?.[field.name];
      if (childValue === undefined || childValue === null) {
        continue; // 缺失字段不报
      }
      const childType = Array.isArray(field.type) ? field.type.join('/') : String(field.type ?? '');
      if (!this.matchType(childValue, childType, field.children ?? field.schema)) {
        return false;
      }
    }
    return true;
  }

  /** 将子字段声明统一规整为数组；非数组（如后端 schema 为单个元素描述）返回 null。 */
  private asFieldList(subFields: any): any[] | null {
    if (Array.isArray(subFields)) {
      return subFields;
    }
    return null;
  }

  /** 从元素描述（Map/对象，{type, schema}）取其 type，转小写；非对象返回 null。 */
  private schemaFieldType(schema: any): string | null {
    if (schema && typeof schema === 'object' && !Array.isArray(schema) && schema.type != null) {
      return String(schema.type).toLowerCase();
    }
    return null;
  }

  /** 从元素描述（{type, schema}）取其 schema（子字段声明）。 */
  private schemaFieldSchema(schema: any): any {
    if (schema && typeof schema === 'object' && !Array.isArray(schema)) {
      return schema.schema;
    }
    return null;
  }

  /**
   * 判断数组元素是否符合声明的元素类型，语义与 ArrTypeValidatorDirective 保持一致。
   * elementType 为 object 时，subFields 为该 object 的子字段声明，递归校验。
   */
  private matchElementType(value: any, elementType: string, subFields?: any): boolean {
    switch (elementType) {
      case 'string':
        return typeof value === 'string';
      case 'integer':
        // integer 需为整数（与后端 isElementTypeValid 整数约束一致），兼容字符串数字
        if (typeof value === 'number') {
          return Number.isFinite(value) && value === Math.floor(value);
        }
        if (typeof value === 'string') {
          const n = Number(value);
          return Number.isFinite(n) && n === Math.floor(n);
        }
        return false;
      case 'number':
        if (typeof value === 'number') {
          return true;
        }
        if (typeof value === 'string') {
          const n = Number(value);
          return !Number.isNaN(n) && Number.isFinite(n);
        }
        return false;
      case 'boolean':
        return typeof value === 'boolean';
      case 'object':
        if (typeof value !== 'object' || value === null || Array.isArray(value)) {
          return false;
        }
        return this.matchObjectFields(value, subFields);
      case 'array':
        return Array.isArray(value);
      default:
        return true; // 'any' / 'file' / 未知
    }
  }

  public async onUploadFile(e: Event, inputItem, uploadType = 'multi'): Promise<void> {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    input.value = '';
    if (uploadType === 'single') {
      const file: File = files[0];
      if (!file) {
        return;
      }
      const fileExtension = file.name.split('.').pop().toLowerCase();
      const valid = checkFileTypeAndSize(
        fileExtension,
        file.size,
        this.i18n,
        this.configServ.getFileMaxSizeKb(),
      );

      if (!valid) {
        return;
      }

      inputItem.uploadData = {};
      inputItem.uploadData.name = file.name;
      inputItem.file = file;
      this.parameterFromGroup.controls[inputItem.name].setValue(file);

      input.value = '';

      inputItem.uploadData.progress = 'loading';
      inputItem.isEmpty = false;
      this.fileLoading = true;
      let postIsImg = false;
      if (['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(fileExtension)) {
        postIsImg = true;
      }
      const formData = new FormData();
      formData.append('file', file);
      formData.append('is_image', JSON.stringify(postIsImg));
      this.appAgentServe
        .uploadFile(formData)
        .then((res: any) => {
          inputItem.uploadData.progress = 'succeeded';
          this.fileLoading = false;
          this.parameterFromGroup.controls[inputItem.name].setValue(res.url);
          inputItem.uploadData.url = res.url;
          this.parameterFromGroup.controls[inputItem.name].setValue(inputItem);
          this.appFlowServe.setFileList(inputItem);
        })
        .catch(() => {
          inputItem.uploadData = null;
          inputItem.file = null;
          this.fileLoading = false;
          this.parameterFromGroup.controls[inputItem.name].setValue('');
        });
    } else {
      const fileLen = files?.length;
      if (!fileLen) {
        return;
      }

      inputItem.isEmpty = false;
      if (!inputItem.uploadDatas) {
        inputItem.uploadDatas = [];
      }
      if (fileLen + inputItem.uploadDatas.length > 20) {
        MessageComponent.showWarn(
          this.i18n.transform('upload_max_files_tip'),
        );
        return;
      }
      // 同名文件整批拒绝（完整文件名含后缀，忽略大小写）
      if (
        Array.from(files as any as File[]).some((f) =>
          inputItem.uploadDatas.some(
            (u) => u.name.toLowerCase() === f.name.toLowerCase(),
          ),
        )
      ) {
        MessageComponent.showWarn(
          this.i18n.transform('duplicate_files_rejected_tip'),
        );
        return;
      }

      this.inputIndex = this.inputList.findIndex(
        (item) => item.name === inputItem.name,
      );

      // 批次开始置位、整批结束复位，驱动一键清空/添加按钮的上传中禁用
      this.isUploading = true;
      for (const file of files as any) {
        const extension = file.name.split('.').pop()?.toLowerCase() || '';
        const isImage = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(
          extension,
        );
        const validationError = validateFileSize(file, isImage, 5 * 1024, this.configServ.getFileMaxSizeKb());
        if (validationError) {
          MessageComponent.showWarn(this.i18n.transform(validationError.key, validationError.params));
          continue;
        }
        const fileItem = createFileItem(file);
        inputItem.uploadDatas.push(fileItem);
        await new Promise(resolve => setTimeout(resolve));
        await uploadFile(this.appAgentServe, file, isImage, fileItem, () => {
          inputItem.uploadDatas = inputItem.uploadDatas.filter((f) => f.fileId !== fileItem.fileId);
        });
      }
      this.isUploading = false;
      this.parameterFromGroup.controls[inputItem.name].setValue(
        inputItem.uploadDatas,
      );
      input.value = '';
    }
  }

  /** 多文件上传是否展示添加按钮 */
  public isShowMultiBtn(inputItem) {
    return (
      inputItem.type?.includes('array<file') && inputItem.uploadDatas?.length > 0
    );
  }

  /** 清空多文件参数的全部已上传文件 */
  public clearMultiFiles(inputItem): void {
    if (this.isUploading) {
      return;
    }
    inputItem.uploadDatas = [];
    this.parameterFromGroup.controls[inputItem.name]?.setValue([]);
  }

  /** 多文件上传添加按钮点击事件 */
  public addMultiFile(index): void {
    if (this.isUploading) {
      return;
    }
    let element = this.fileInputs.find((el) =>
      el.nativeElement.className.includes(`input${index}`),
    );
    if (element) {
      element.nativeElement.click();
    }
  }

  removeFile(inputItem, fileItem?) {
    // File类型删除
    if (!fileItem) {
      inputItem.file = '';
      inputItem.uploadData = {};
      this.parameterFromGroup.controls[inputItem.name].setValue('');
      this.startNodeInputs.forEach((item) => {
        if (item.name === inputItem.name) {
          item.file = '';
          item.uploadData = {};
        }
      });
      return;
    }

    // Array<File>类型删除
    if (
      this.isUploading &&
      this.inputList[this.inputIndex].name !== inputItem.name
    ) {
      return;
    }

    // 如果删除的文件还未上传完成，则中止请求
    if (fileItem.progress === 'loading') {
      fileItem.controller.abort();
    }
    inputItem.uploadDatas = inputItem.uploadDatas.filter(
      (item) => item.fileId !== fileItem.fileId,
    );
  }

  /** 处理文件类型的表单项，回填文件值到对应的表单控件中*/
  private updateFileControlValue(item: any, formGroup: FormGroup): void {
    if (item.type.startsWith('file')) {
      const control = formGroup.controls[item.name];
      const file = item?.file;
      if (control && file) {
        control.setValue(file);
      }
    }
  }

  getFileNameByUrl(url) {
    return decodeURIComponent(
      url?.split('file/')?.[1]?.split('?')[0] || 'unknown',
    );
  }
}
