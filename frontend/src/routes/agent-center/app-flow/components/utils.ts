import { MessageComponent } from '@shared/services/cfdata.service';
import { capitalize, cloneDeep } from 'lodash';
import { removeHTMLTag } from 'src/utils/utils';
import { IModel, IRefInfo } from '../app-flow.types';
import { getInitOutputParamConfig, WORKFLOW_SVGS } from '../flow.const';
import { TreeUtil } from './tree-util';
import {
  FieldValueContent,
  FieldValueType,
  INodeType,
  IParamExtractionNode,
  IParamRef,
  IParamSource,
  IRefContentType,
  IWFView,
  IWFViewParentType,
  IWFViewWithMultiType,
  IWorkflowField,
  IWorkflowFieldSchema,
  IWorkflowFieldType,
  NodeInfo,
} from '../node.type';
import i18next from 'i18next';

export interface IRefIndex {
  id: string;
  type: IWorkflowFieldType;
  schema?: IWorkflowFieldSchema;
}

interface IFieldProcessConfig {
  useContentType?: boolean;
  handleRef?: boolean;
}

interface ILayerIndexWidthConfig {
  widthArr?: number[];
}

export const EditorOptions = {
  theme: 'vs',
  language: 'json',
  overviewRulerLanes: 0,
  hideCursorInOverviewRuler: true,
  minimap: { enabled: false },
  tabSize: 2,
};

export interface IRef2TreeConfig {
  disableObj?: boolean;
  disableArr?: boolean;
  simpleArrRefFirst?: boolean;
  strOnly?: boolean;
  arrOnly?: boolean;
  intOnly?: boolean;
  appendName?: string;
  refRootArrItem?: boolean;
  disableArrObj?: boolean;
  hideArrObjChildren?: boolean; //隐藏Array<Object>类型的子属性，变量赋值节点左边不可选
}

export const NodeUtils = {
  /**
   * 将引用数据结构的 IRefContentType 类型转成字符串类型，结构形如
   * `${content.ref_node_id}.${content.ref_var_name}`
   * 便于前端下拉列表展示
   */
  fieldsRefInputMapper(field: IWorkflowField): IWorkflowField {
    const fieldCopy = cloneDeep(field);
    if (fieldCopy.value.type === 'ref') {
      fieldCopy.value.content = NodeUtils.refContentStringify(fieldCopy.value.content as IRefContentType);

      return fieldCopy;
    }

    return fieldCopy;
  },

  /**
   * 将字符串类型的引用标识转为 IRefContentType 类型
   */
  fieldsRefOutputMapper(field: IWorkflowField): IWorkflowField {
    const fieldCopy = cloneDeep(field);
    if (fieldCopy.value.type === 'ref') {
      const contentArr = (fieldCopy.value.content as string).split('.');

      fieldCopy.value.content = {
        ref_node_id: contentArr[0],
        ref_var_name: contentArr[1],
        source: contentArr?.[2] as IParamSource,
      };

      return fieldCopy;
    }

    return fieldCopy;
  },

  getChangeContent(type: FieldValueType): FieldValueContent {
    return type === 'literal'
      ? ''
      : {
          ref_node_id: '',
          ref_var_name: '',
          source: 'user',
        };
  },

  checkModelExistence(nodeName: string, model_deployment_id: string, models: IModel[]) {
    if (model_deployment_id && models.length > 0 && !models.map(m => m.model_deployment_id).includes(model_deployment_id)) {
      MessageComponent.showError(i18next.t('checkModel_tip', { node: removeHTMLTag(nodeName) }));
    }
    return null;
  },

  refContentStringify(content: IRefContentType): string {
    if (!content?.ref_node_id && !content?.ref_var_name) {
      return '';
    }

    return `${content.ref_node_id}.${content.ref_var_name}`;
  },

  outputStringify(nodeId: string, field: IWorkflowField): string {
    return `${nodeId}.${field.name}.${field.source}`;
  },

  fields2Views(fields: IWorkflowField[], depth = 0, parentType: IWFViewParentType = 'none'): IWFView[] {
    const views: IWFView[] = fields.map((field, index) => {
      const { name, type, description, required, schema, source, value, isDisabled, aging_level, storage_method } = field;

      const view: IWFView = {
        name,
        key: `k_${depth}_${index}_${Math.random().toString(36).substring(2, 10)}`,
        type,
        description,
        required,
        source,
        depth,
        parentType,
        value,
        ...(isDisabled !== undefined && { isDisabled }),
      };

      if (aging_level && storage_method) {
        view.aging_level = aging_level;
        view.storage_method = storage_method;
      }

      if (type === 'array') {
        if ((schema as IWorkflowField).type === 'object') {
          view.type = 'array<object>';
          view.children = this.fields2Views(((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[], depth + 1, view.type);
          view.expanded = true;
        } else {
          if ((schema as IWorkflowField).type) {
            view.type = `array<${(schema as IWorkflowField).type}>` as IWorkflowFieldType;
          } else if ((field?.schema as any)?.type) {
            view.type = `array<${(field?.schema as any)?.type}>` as IWorkflowFieldType;
          }
        }
      }

      if (type === 'object') {
        view.children = this.fields2Views((schema ?? []) as IWorkflowField[], depth + 1, view.type);
        view.expanded = true;
      }

      return view;
    });

    return views;
  },

  fields2ViewsUnchangeType(fields: IWorkflowField[], depth = 0, parentType: IWFViewParentType = 'none', parentVisibility?: boolean): IWFView[] {
    const views: IWFView[] = fields.map(field => {
      const { name, type, description, required, schema, source, value, isDisabled, aging_level, storage_method, visibility } = field;

      const view: IWFView = {
        name,
        type,
        description,
        showRequired: required,
        source,
        depth,
        parentType,
        value,
        schema,
        visibility,
        required: parentType === 'object' ? !parentVisibility : !visibility,
        ...(isDisabled !== undefined && { isDisabled }),
      };

      if (aging_level && storage_method) {
        view.aging_level = aging_level;
        view.storage_method = storage_method;
      }
      //array 不展开
      if (type === 'array' && false) {
        if ((schema as IWorkflowField).type === 'object') {
          view.children = this.fields2ViewsUnchangeType(((schema as IWorkflowField)?.schema ?? []) as IWorkflowField[], depth + 1, view.type, visibility);
          view.expanded = true;
        }
      }

      if (type === 'object') {
        view.children = this.fields2ViewsUnchangeType((schema ?? []) as IWorkflowField[], depth + 1, view.type, visibility);
        view.isDisabled = true;
        view.expanded = true;
      }

      return view;
    });

    return views;
  },

  views2Fields(views: IWFView[]): IWorkflowField[] {
    const fields: IWorkflowField[] = views.map(view => {
      const { name, type, description, required, children, source, value, aging_level, storage_method } = view;
      const field: IWorkflowField = {
        name,
        type,
        description,
        required,
        source,
        value,
      };

      if (aging_level && storage_method) {
        field.aging_level = aging_level;
        field.storage_method = storage_method;
      }

      if (type.startsWith('array<')) {
        field.type = 'array';
        const itemType = type.match(/array<(.+)>/)[1];
        (field.schema as IWorkflowField) = {
          name: '',
          type: itemType as IWorkflowFieldType,
        };
        if (itemType === 'object') {
          (field.schema as IWorkflowField).schema = children ? this.views2Fields(children) : [];
        }
      }
      if (type === 'object') {
        if ((view as any).schema) {
          field.schema = this.views2Fields((view as any).schema);
        } else if (children) {
          field.schema = this.views2Fields(children);
        } else {
          field.schema = [];
        }
      }
      return field;
    });

    return fields;
  },

  multiTypeViews2Fields(views: IWFViewWithMultiType[]): IWorkflowField[] {
    const fields: IWorkflowField[] = views.map(view => {
      const { name, description, required, children, source, value } = view;
      const type = view.type.join('/') as IWorkflowFieldType;
      const field: IWorkflowField = {
        name,
        type,
        description,
        required,
        source,
        value,
      };

      if (type.startsWith('array<')) {
        field.type = 'array';
        let itemType;
        if (type.includes('file')) {
          itemType = `${type.match(/array<(.+)>/)[1]}/${view.type[1]}`;
        } else {
          itemType = type.match(/array<(.+)>/)[1];
        }
        (field.schema as IWorkflowField) = {
          name: '',
          type: itemType as IWorkflowFieldType,
        };

        if (itemType === 'object') {
          (field.schema as IWorkflowField).schema = children ? this.multiTypeViews2Fields(children) : [];
        }
      }

      if (field.type === 'object') {
        field.schema = children ? this.multiTypeViews2Fields(children) : [];
      }

      return field;
    });

    return fields;
  },

  isObjectLikeType(type: string | string[]) {
    let typeCopy = '';
    if (Array.isArray(type)) {
      typeCopy = type.join('/');
    } else {
      typeCopy = type;
    }

    return ['object', 'array<object>'].includes(typeCopy);
  },

  isSimpleType(type: string | string[]) {
    let typeCopy = '';
    if (Array.isArray(type)) {
      typeCopy = type.join('/');
    } else {
      typeCopy = type;
    }

    return typeCopy !== 'object' && !typeCopy.startsWith('array');
  },

  getLayerIndexWidth(param: IWFView, isNormalView = true, configs?: ILayerIndexWidthConfig): string {
    const commonDiff = 24;
    let layer0 = 145;
    let slimLayer0 = 136;

    if (configs?.widthArr?.length === 2) {
      [layer0, slimLayer0] = configs.widthArr;
    }

    const map = {
      0: `${layer0}px`,
      1: `${layer0 - commonDiff}px`,
      2: `${layer0 - commonDiff * 2}px`,
      3: `${layer0 - commonDiff * 3}px`,
    };

    const slimMap = {
      0: `${slimLayer0}px`,
      1: `${slimLayer0 - commonDiff}px`,
      2: `${slimLayer0 - commonDiff * 2}px`,
      3: `${slimLayer0 - commonDiff * 3}px`,
    };

    const [childLayer0, slimChildLayer0] = [layer0 - 20, slimLayer0 - 20];
    const mapWithChildren = {
      0: `${childLayer0}px`,
      1: `${childLayer0 - commonDiff}px`,
      2: `${childLayer0 - commonDiff * 2}px`,
    };

    const slimMapWithChildren = {
      0: `${slimChildLayer0}px`,
      1: `${slimChildLayer0 - commonDiff}px`,
      2: `${slimChildLayer0 - commonDiff * 2}px`,
    };

    const useMap = isNormalView ? map : slimMap;
    const useWithChildrenMap = isNormalView ? mapWithChildren : slimMapWithChildren;

    return param?.children ? useWithChildrenMap[param.depth] : useMap[param.depth];
  },

  onOutputParamTypeChange(param: IWFView) {
    if (NodeUtils.isSimpleType(param.type) && param?.children) {
      delete param?.children;
      return;
    }

    if (param.type.startsWith('array') && param.type !== 'array<object>' && param?.children) {
      delete param?.children;
    }

    if (this.isObjectLikeType(param.type)) {
      if (!param?.children) {
        this.addChild(param);
      }
    }
  },

  addChild(param: IWFView) {
    const child = {
      ...getInitOutputParamConfig(),
      depth: param.depth + 1,
      parentType: param.type,
      key: `child_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`,
    };

    if (param?.children) {
      param.children = [...param.children, child];
    } else {
      param.children = [child];
    }

    param.expanded = true;
  },

  fields2RefParams(
    fields: IWorkflowField[],
    nodeId: string,
    preNames: string[] = [],
    configs: IRef2TreeConfig = {
      disableObj: false,
      disableArr: false,
      simpleArrRefFirst: false,
      strOnly: false,
      arrOnly: false,
      intOnly: false,
      appendName: '',
      refRootArrItem: false,
      disableArrObj: false,
      hideArrObjChildren: false,
    }
  ) {
    const refs: IParamRef[] = fields.map(field => {
      const { name, type, schema, source } = field;
      const names = [...preNames, name];

      const ref: IParamRef = {
        name,
        type: type ?? 'string',
        source,
        ref_node_id: nodeId,
        ref_var_name: names.join('.'),
        isTop: false,
      };

      if (type === 'array') {
        const workflowField = schema as IWorkflowField;
        ref.schema = schema;

        // 处理引用根数组项的逻辑
        if (configs?.refRootArrItem) {
          configs.refRootArrItem = false;
        } else {
          const lastIndex = names.length - 1;
          names[lastIndex] = `${names[lastIndex]}[0]`;
        }

        // 根据数组项类型处理不同的逻辑分支
        if (workflowField?.type === 'object') {
          ref.type = 'array<object>';
          if (!configs?.hideArrObjChildren) {
            // 获取对象类型的schema，默认为空数组
            const itemSchema = workflowField.schema ?? [];

            ref.children = this.fields2RefParams(itemSchema as IWorkflowField[], nodeId, names, configs);
            ref.expanded = true;
          }
          if (!(ref.schema as any).schema) {
            (ref.schema as any).schema = [];
          }
        } else {
          // 处理基础类型的数组
          const itemType = workflowField?.type ?? 'unknown';
          ref.type = `array<${itemType}>` as IWorkflowFieldType;

          if (configs?.simpleArrRefFirst) {
            ref.ref_var_name = names.join('.');
          }
        }
      }

      if (type === 'object') {
        // 设置基本属性
        ref.schema = schema;
        ref.expanded = true;

        // 处理对象禁用状态
        if (configs?.disableObj) {
          ref.disabled = true;
        }

        // 递归处理子字段
        const childFields = (ref.schema ?? []) as IWorkflowField[];
        ref.children = this.fields2RefParams(childFields, nodeId, names, configs);
      }

      if (configs?.intOnly === true && ref.type !== 'integer') {
        ref.disabled = true;
      }

      if (configs?.strOnly === true && ref.type !== 'string') {
        ref.disabled = true;
      }

      if (configs?.arrOnly === true && !ref.type.startsWith('array')) {
        ref.disabled = true;
      }

      if (configs?.disableArr === true && ref.type.startsWith('array')) {
        ref.disabled = true;
      }

      if (configs?.appendName) {
        ref.ref_var_name = `${ref.ref_var_name}.${configs.appendName}`;
      }

      if (ref.ref_node_id === 'node_start' && ref.name === 'sys') {
        ref.disabled = true;
      }

      if (configs?.disableArrObj && ref.type === 'array<object>') {
        ref.disabled = true;
      }

      return ref;
    });

    return refs;
  },

  refInfo2Tree(
    refInfo: IRefInfo[],
    configs: IRef2TreeConfig = {
      simpleArrRefFirst: false,
      disableObj: false,
      disableArr: false,
      strOnly: false,
      intOnly: false,
      appendName: '',
      refRootArrItem: false,
      arrOnly: false,
    }
  ): IParamRef[] {
    const paramRefs: IParamRef[] = [];
    refInfo.forEach(info => {
      const { refNodeId, refNodeName, type, outputs } = info;
      let item: IParamRef = {
        ref_node_id: refNodeId,
        ref_var_name: '',
        name: refNodeName,
        isTop: true,
        type,
        source: 'user',
        expanded: true,
        children: this.fields2RefParams(outputs, refNodeId, [], configs),
      };
      if (type !== 'ComplexIntentDetection') {
        paramRefs.push(item);
      }
    });

    return paramRefs;
  },

  cantClick(e: Event) {
    e.stopPropagation();
  },

  type2Img(type: INodeType) {
    return WORKFLOW_SVGS[type];
  },

  attachRefs2Input(inputs: IWorkflowField[], ops: IParamRef[]): IWorkflowField[] {
    if (!inputs?.length) {
      return [];
    }
    return inputs.map(field => {
      return {
        ...cloneDeep(field),
        refs: cloneDeep(ops),
      };
    });
  },

  initSelectedTreeNode(params: IWorkflowField[]) {
    params.forEach(this.selectTreeNodeInRefsByValue);
  },

  selectTreeNodeInRefsByValue(param: IWorkflowField) {
    if (param?.value?.type === 'ref') {
      const paramContent = param?.value.content as IRefContentType;

      TreeUtil.traverse(param.refs, (node: any) => {
        if (!node.isTop && node.ref_var_name === paramContent?.ref_var_name && node.ref_node_id === paramContent?.ref_node_id) {
          node.checked = true;
          param.value.content = [node];
        }
      });
    }
  },

  selectTreeNodeInRefsChhangeByValue(param: IWorkflowField) {
    if (param?.value?.type === 'ref') {
      const paramContent = param?.value.content as IRefContentType;

      TreeUtil.traverse(param.refs, (node: any) => {
        if (!node.isTop && node.ref_var_name === paramContent?.ref_var_name && node.ref_node_id === paramContent?.ref_node_id) {
          node.checked = true;
          param.value.content = [node];
        }
      });
    }
  },

  reSelectRefWithNewOps(param: IWorkflowField, ops: IParamRef[]) {
    param.refs = cloneDeep(ops);

    // 重新选中引用
    if (param.value.type === 'ref') {
      const paramContent = Array.isArray(param.value.content) ? (param.value.content[0] as IParamRef) : (param.value.content as IRefContentType);

      let isMatch = false;
      TreeUtil.traverse(param.refs, (node: any) => {
        if (!node.isTop && node.ref_var_name === paramContent?.ref_var_name && node.ref_node_id === paramContent?.ref_node_id) {
          node.checked = true;
          param.value.content = [node];
          isMatch = true;
        }
      });

      if (paramContent?.ref_var_name && paramContent?.ref_node_id && !isMatch) {
        param.value.content = {
          ref_node_id: '',
          ref_var_name: '',
          source: 'user',
        };
      }
    }
  },

  reSelectRefsWithNewOps(fields: IWorkflowField[], ops: IParamRef[]) {
    fields.forEach(param => {
      this.reSelectRefWithNewOps(param, ops);
    });
  },

  initInputs(rawParams: IWorkflowField[], ops: IParamRef[]) {
    const params = this.attachRefs2Input(rawParams, ops);
    this.initSelectedTreeNode(params);
    return params;
  },

  initRefField(param: IWorkflowField, ops: IParamRef[]) {
    param.refs = cloneDeep(ops);
    if (param.value.type === 'ref') {
      const paramContent = param.value.content as IRefContentType;

      TreeUtil.traverse(param.refs, (node: any) => {
        if (!node.isTop && node.ref_var_name === paramContent?.ref_var_name && node.ref_node_id === paramContent?.ref_node_id) {
          node.checked = true;
          param.value.content = [node];
        }
      });
    }

    return param;
  },

  getDtoInputs(params: IWorkflowField[], config?: IFieldProcessConfig): IWorkflowField[] {
    const paramCopy = cloneDeep(params);
    paramCopy.forEach(param => {
      this.getDtoInput(param, config);
    });

    return paramCopy;
  },

  resetSchemaSource(schema: IWorkflowFieldSchema, source: IParamSource) {
    if (Array.isArray(schema)) {
      schema.forEach(s => {
        this.resetSchemaSource(s, source);
      });
    } else {
      if (schema?.source) {
        schema.source = source;
      }

      if (schema?.schema) {
        this.resetSchemaSource(schema.schema, source);
      }
    }
  },

  getDtoInput(
    param: IWorkflowField,
    config: IFieldProcessConfig = {
      useContentType: true,
    }
  ): IWorkflowField {
    if ((param.value.type === 'ref' || param.value.type === 'input_ref') && config.handleRef !== false) {
      const contentArr = (param.value.content as IParamRef[])?.[0];
      if (contentArr) {
        const { ref_node_id, ref_var_name, source, schema, type } = contentArr;
        param.value.content = {
          ref_node_id,
          ref_var_name,
          source,
        };
        if (config.useContentType) {
          if (type?.startsWith('array')) {
            param.type = 'array';
          } else {
            param.type = type as IWorkflowFieldType;
          }
        }

        if (['object', 'array']?.includes(param.type)) {
          this.resetSchemaSource(schema, param.source);

          if (config?.useContentType) {
            param.schema = schema;
          }
        } else {
          delete param?.schema;
        }
      }
    }

    if (param.value?.type === 'literal' && typeof param.value.content === 'string') {
      param.value.content = removeHTMLTag(param.value.content);
    }

    delete param?.refs;

    return param;
  },

  showDelete(param: IWFView, ops: IWFView[] | IWFViewWithMultiType[]) {
    if (param.source === 'system') {
      return false;
    }

    if (param.depth === 0 && ops.length === 1) {
      return false;
    }

    if (param.depth > 0) {
      const parentNode = TreeUtil.getParentNode(ops, param);
      if (parentNode && parentNode.children.length === 0) {
        return false;
      }
    }

    return true;
  },

  getOutputsRefIndex(nodeId: string, fields: IWorkflowField[], pathNameArr: string[] = [], indexArr: IRefIndex[] = []): IRefIndex[] {
    fields?.forEach(field => {
      const { name, type } = field;
      const pathNames = [...pathNameArr, name];

      if (type === 'array') {
        const arrSchema = field.schema as IWorkflowField;
        indexArr.push({
          id: `${nodeId}.${pathNames.join('.')}`,
          type,
          schema: cloneDeep(field.schema),
        });

        const lastIndex = pathNames.length - 1;
        const last = pathNames[lastIndex];
        pathNames[lastIndex] = `${last}[0]`;

        if (arrSchema.type === 'object') {
          this.getOutputsRefIndex(nodeId, arrSchema.schema as IWorkflowField[], pathNames, indexArr);
        } else {
          indexArr.push({
            id: `${nodeId}.${pathNames.join('.')}`,
            type: arrSchema.type,
          });
        }
      } else if (type === 'object') {
        indexArr.push({
          id: `${nodeId}.${pathNames.join('.')}`,
          type,
          schema: cloneDeep(field.schema),
        });

        this.getOutputsRefIndex(nodeId, field.schema as IWorkflowField[], pathNames, indexArr);
      } else {
        indexArr.push({
          id: `${nodeId}.${pathNames.join('.')}`,
          type,
        });
      }
    });

    return indexArr;
  },

  isStringType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'string';
    }

    return param.value.type === 'literal';
  },

  isMultiplesType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase().includes('|');
    }

    return param.value.type === 'literal';
  },

  isIntType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'integer';
    }

    return false;
  },

  isNumType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'number';
    }

    return false;
  },

  isBooleanType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'boolean';
    }

    return false;
  },

  isComplexType(param: IWorkflowField): boolean {
    if (param?.type) {
      return ['object', 'array'].includes(param.type.toLowerCase());
    }

    return false;
  },

  isArrayType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'array';
    }

    return false;
  },

  isObjectType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.toLowerCase() === 'object';
    }

    return false;
  },

  isFileType(param: IWorkflowField): boolean {
    if (param?.type) {
      return param.type.startsWith('file/');
    }

    return false;
  },

  getFieldTypeView(field: IWorkflowField): string {
    if (!field?.type) {
      return 'String';
    }

    const typeArr = field.type.split('/');

    if (typeArr.length > 1) {
      if (typeArr[0].startsWith('array<file')) {
        const [mainType, subType] = typeArr[0].split('<');
        return `${capitalize(mainType)}<${capitalize(subType)}/${capitalize(typeArr[1])}`;
      }
      return capitalize(typeArr[1]);
    }

    const type = typeArr[0] as IWorkflowFieldType;
    if (type.startsWith('array')) {
      const schemaType = (field.schema as IWorkflowField)?.type ?? '';
      const capitalizedType = schemaType.split('/').map(capitalize).join('/');
      return `Array<${capitalizedType}>`;
    }

    return capitalize(type);
  },

  getRequiredText(status: boolean): string {
    if (status) {
      return i18next.t('required_1');
    }
    return i18next.t('selected');
  },

  /**
   *
   * @param options
   * @param query disabledRefIds [`${ref_node_id}.${ref_var_name}.${source}`]
   * @returns
   */
  narrowRefOption(
    options: IParamRef[],
    query: {
      type: IWorkflowFieldType;
      disabledRefIds?: string[];
    }
  ) {
    const ops = cloneDeep(options);
    TreeUtil.traverse(ops, (node: any) => {
      if (!node.isTop) {
        if (node.type !== query.type) {
          node.disabled = true;
        }

        if (query?.disabledRefIds && query.disabledRefIds.includes(`${node.ref_node_id}.${node.ref_var_name}.${node.source}`)) {
          node.disabled = true;
        }
      }
    });

    return ops;
  },

  traversalNodeSource(nodeData: NodeInfo): NodeInfo {
    const res = nodeData as any;
    if (res?.inputs && res?.inputs.length > 0) {
      res.inputs = res.inputs.map(item => {
        if (item.source && item?.value?.content?.source === 'environment') {
          item.source = 'environment';
        }
        return item;
      });
    }
    return res as NodeInfo;
  },

  transformInputs(inputs: any, dataConfig: any) {
    inputs.forEach((input: any) => {
      if (
        input.value?.type === 'literal' &&
        ['number', 'integer'].includes(input.type) &&
        input.value.content !== null &&
        typeof input.value.content !== 'number'
      ) {
        input.value.content = Number(input.value.content);
      }
      if (input.type === 'object' && input.value.content === '') {
        input.value.content = '{}';
      }
      if (input.type === 'array' && input.value.content === '') {
        input.value.content = '[]';
      }
      if (input?.name === 'contentType') {
        input.value.content = dataConfig[1];
      }
      if (input.name === 'fileFormat') {
        input.value.content = dataConfig[2];
      }
    });
  },
  validJsonType(inputParams) {
    return inputParams.some(obj => this.isArrOrObj(obj.type) && obj.value?.content === '' && obj.required);
  },
  isArrOrObj(type: string) {
    return type.startsWith('array') || type === 'object';
  },
  getParamExtractionRelationFlow(node: IParamExtractionNode) {
    const result = [];
    node?.configs?.extension_workflows?.forEach(e => {
      result.push(e);
    });

    node?.configs?.domain_objects?.forEach(d => {
      d?.processing_workflows?.forEach(p => {
        result.push(p);
      });
    });
    return result;
  },
};
