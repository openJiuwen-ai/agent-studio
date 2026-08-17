import { MessageComponent } from '@shared/services/cfdata.service';
import {
  IPluginWithTools,
  IReqArgProps,
  IReqArrayProps,
  IReqObjProps,
  IReqSchema,
  IRequestArgsBase,
  IRequestArgsView,
  IResArgProps,
  IResArrayProps,
  IResObjProps,
  IResponseArgsView,
  IResponseArgumentsBase,
  IResSchema,
  ITool,
} from './app-plugin.interface';
import {
  IWorkflowField,
  IWorkflowFieldType,
  IWFView,
} from '../app-flow/node.type';
import {
  getInitInputParamConfig,
  getInitOutputParamConfig,
} from '../app-flow/flow.const';
import i18next from 'i18next';
import { ValidationErrors } from '@angular/forms';
import { capitalize } from 'lodash';

const isArrayView = (prop: IReqArgProps): prop is IReqArrayProps => {
  return prop.type.startsWith('array');
};

export const isArraySchema = (prop: IReqArgProps): prop is IReqArrayProps => {
  return prop.type === 'array';
};

const isObjView = (prop: IReqArgProps): prop is IReqObjProps => {
  return prop.type === 'object';
};

export const isObjSchema = (prop: IReqArgProps): prop is IReqObjProps => {
  return prop.type === 'object';
};

const isResArrayView = (prop: IResArgProps): prop is IResArrayProps => {
  return prop.type.startsWith('array');
};

export const isResArraySchema = (
  prop: IResArgProps,
): prop is IResArrayProps => {
  return prop.type === 'array';
};

const isResObjView = (prop: IResArgProps): prop is IResObjProps => {
  return prop.type === 'object';
};

export const isResObjSchema = (prop: IResArgProps): prop is IResObjProps => {
  return prop.type === 'object';
};

export const isSimpleType = (type: string) => {
  return type !== 'object' && type?.startsWith && !type?.startsWith('array');
};

const getDefaultValue = (item: any) => {
  if (item.type === 'string') {
    return item?.default;
  } else if (item.type === 'integer') {
    return parseInt(item?.default, 10);
  } else if (item.type === 'number') {
    return parseFloat(item?.default);
  } else if (item.type === 'boolean') {
    if (item?.default === true) {
      return true;
    }
    return item?.default.toLowerCase() === 'true';
  } else {
    return '';
  }
};

export const initializeReqItem = (item: any): any => {
  return {
    ...item,
    controlValue: null,
    modelUri: null,
    isError: false,
    isEmpty: false,
    value: {
      default: getDefaultValue(item),
      type: 'generated',
      hint: '',
    },
  };
};

export const getInitStrTypeReq = (
  location: string = null,
): IRequestArgsBase => {
  let myLocation: string = 'Body';
  if (location) {
    myLocation = location;
  }
  return {
    name: '',
    name_cn: '',
    description: '',
    type: 'string',
    location: myLocation,
    required: true,
    default: '',
    validated: false,
    validate_rule: '',
    validate_type: 'CHAR',
    visible: true,
  };
};

export const getInitStrTypeRes = (): IResponseArgumentsBase => {
  return {
    name: '',
    description: '',
    type: 'string',
    required: true,
  };
};

export const schema2View = (
  schema: IReqSchema,
  depth = 0,
  parentType = 'none',
  ispath = false,
): IRequestArgsView[] => {
  const view: IRequestArgsView[] = [];
  const properties = schema.properties || {};
  const keys = Object.keys(properties);

  for (const key of keys) {
    const property = properties[key] as IRequestArgsBase;

    // 每个key对应的类型可能是obj、arr、普通类型
    const {
      name_cn,
      description,
      type,
      location,
      validate_rule,
      validated,
      validate_type,
      required,
    } = property;
    const item: IRequestArgsView = {
      name: key,
      depth,
      parentType,
      required: Array.isArray(schema.required)
        ? schema.required?.includes(key)
        : required,
      default: property?.default ?? '',
      name_cn,
      // 请求参数的描述是必填项，在导入时如果没有输入该项也要给一个默认值
      description: description ?? key,
      type,
      location: location || 'Body',
      validate_rule,
      validate_type,
      validated,
    };

    if (isArraySchema(property)) {
      if (property.items.type === 'object') {
        item.type = 'array<object>';
        item.children = schema2View(
          property.items,
          depth + 1,
          item.type,
          ispath,
        );
        item.expanded = true;
      } else {
        item.type = `array<${property.items.type}>`;
      }
    }

    if (isObjSchema(property)) {
      item.children = schema2View(property, depth + 1, item.type, ispath);
      item.expanded = true;
    }

    if (
      (ispath && item.location === 'Path') ||
      (!ispath && item.location !== 'Path')
    ) {
      view.push(item);
    }
  }

  return view;
};

export const view2Schema = (view: IRequestArgsView[]): IReqSchema => {
  const schema = {
    type: 'object',
    properties: {},
    required: [],
  };

  for (const item of view) {
    if (item.required) {
      schema.required.push(item.name);
    }

    const {
      description,
      location,
      validate_rule,
      validate_type,
      validated,
      name_cn,
      type,
    } = item;

    const property: IReqArgProps = {
      default: item.default,
      location,
      validate_rule,
      validate_type,
      validated,
      name_cn,
      type,
      description,
    };

    if (property?.default === '') {
      delete property.default;
    }

    if (isArrayView(property)) {
      property.type = 'array';
      const itemType = item.type.match(/array<(.+)>/)[1];

      if (itemType === 'object' && item.children) {
        property.items = view2Schema(item.children);
      } else {
        property.items = {
          type: itemType,
        };
      }
    }

    if (isObjView(property) && item.children) {
      const noneExtraPropsSchema = view2Schema(item.children);
      property.properties = noneExtraPropsSchema.properties;
      property.required = noneExtraPropsSchema.required;
    }

    schema.properties[item.name] = property;
  }

  return schema;
};

export const resSchema2View = (
  schema: IResSchema,
  depth = 0,
  parentType = 'none',
): IResponseArgsView[] => {
  const view: IResponseArgsView[] = [];
  const properties = schema.properties || {};
  const keys = Object.keys(properties);

  for (const key of keys) {
    const property = properties[key];

    const { description, type } = property;

    const item: IResponseArgsView = {
      name: key,
      depth,
      parentType,
      required: schema.required?.includes(key),
      description,
      type,
    };

    if (isResArraySchema(property)) {
      if (property.items.type === 'object') {
        item.type = 'array<object>';
        item.children = resSchema2View(property.items, depth + 1, item.type);
        item.expanded = true;
      } else {
        item.type = `array<${property.items.type}>`;
      }
    }

    if (isResObjSchema(property)) {
      item.children = resSchema2View(property, depth + 1, item.type);
      item.expanded = true;
    }

    view.push(item);
  }

  return view;
};

export const resView2Schema = (view: IResponseArgsView[]): IResSchema => {
  const schema = {
    type: 'object',
    properties: {},
    required: [],
  };

  for (const item of view) {
    if (item.required) {
      schema.required.push(item.name);
    }

    const { description, type } = item;

    const property: IResArgProps = {
      type,
      description: description ?? '',
    };

    if (isResArrayView(property)) {
      property.type = 'array';
      const itemType = item.type.match(/array<(.+)>/)[1];

      if (itemType === 'object' && item.children) {
        property.items = resView2Schema(item.children);
      } else {
        property.items = {
          type: itemType,
        };
      }
    }

    if (isResObjView(property) && item.children) {
      const noneExtraPropsSchema = resView2Schema(item.children);
      property.properties = noneExtraPropsSchema.properties;
      property.required = noneExtraPropsSchema.required;
    }

    schema.properties[item.name] = property;
  }

  return schema;
};

export const pluginSchemaStr2Args = (schemaStr: string): IRequestArgsView[] => {
  if (!schemaStr) {
    return [];
  }
  let result: IRequestArgsView[] = [];
  try {
    const data: IReqSchema = JSON.parse(schemaStr);
    result = schema2View(data);
  } catch (e) {
    MessageComponent.showError(i18next.t('parse_req_error'));

    result = [{ ...getInitStrTypeReq(), depth: 0 }];
  }

  return result;
};

export const pluginSchemaStr2Res = (schemaStr: string): IResponseArgsView[] => {
  let result: IResponseArgsView[] = [];

  try {
    const data: IResSchema = JSON.parse(schemaStr);
    result = resSchema2View(data);
  } catch (e) {
    MessageComponent.showError(i18next.t('parse_res_error'));

    result = [
      {
        ...getInitStrTypeRes(),
        depth: 0,
      },
    ];
  }

  return result;
};

export const pluginSchemaStr2Path = (schemaStr: string): IRequestArgsView[] => {
  if (!schemaStr) {
    return [];
  }
  let result: IRequestArgsView[] = [];
  try {
    const data: IReqSchema = JSON.parse(schemaStr);
    result = schema2View(data, null, null, true);
  } catch (e) {
    MessageComponent.showError(i18next.t('parse_req_error'));

    result = [{ ...getInitStrTypeReq(), depth: 0 }];
  }

  return result;
};

export const resSchema2Field = (schema: IResSchema): IWorkflowField[] => {
  const fields: IWorkflowField[] = [];
  const properties = schema.properties || {};
  const keys = Object.keys(properties);

  for (const key of keys) {
    const property = properties[key];

    const { description, type } = property;

    const field: IWorkflowField = {
      name: key,
      required: schema.required?.includes(key),
      description,
      type: type as IWorkflowFieldType,
      value: {
        type: 'generated',
        content: null,
        hint: '',
        default: '',
      },
      source: 'user',
    };

    if (isResArraySchema(property)) {
      field.schema = {
        name: '',
        type: property.items.type as IWorkflowFieldType,
      };

      if (property.items.type === 'object') {
        (field.schema as IWorkflowField).schema = resSchema2Field(
          property.items,
        );
      }
    }

    if (isResObjSchema(property)) {
      field.schema = resSchema2Field(property);
    }

    fields.push(field);
  }

  return fields;
};

export const reqSchema2Field = (schema: IReqSchema): IWorkflowField[] => {
  const fields: IWorkflowField[] = [];
  const properties = schema.properties || {};
  const keys = Object.keys(properties);

  for (const key of keys) {
    const property = properties[key];

    let { description, type, default: defaultVal } = property;
    let defaultValue: string | number | boolean | Record<string, any> =
      defaultVal;
    if (type === 'boolean' && typeof defaultVal !== 'boolean') {
      defaultValue = defaultVal === 'true';
    }
    if (type === undefined || type === null || type === '') {
      type = 'string';
    }
    // number/integer 类型：确保 content 是正确的数字类型或 null
    let content: any = defaultValue || '';
    if (type === 'number' || type === 'integer') {
      if (defaultValue === null || defaultValue === undefined || defaultValue === '') {
        content = null; // 无有效默认值时置 null，运行时跳过该参数
      } else {
        content = Number(defaultValue); // 字符串数字转为真数字
      }
    }

    const field: IWorkflowField = {
      name: key,
      required: schema.required?.includes(key),
      description,
      type: type as IWorkflowFieldType,
      value: {
        type: 'literal',
        content,
        hint: '',
      },
      source: 'user',
    };

    if (isArraySchema(property)) {
      field.schema = {
        name: '',
        type: property.items.type as IWorkflowFieldType,
      };

      if (property.items.type === 'object') {
        (field.schema as IWorkflowField).schema = reqSchema2Field(
          property.items,
        );
      }
    }

    if (isObjSchema(property)) {
      field.schema = reqSchema2Field(property);
    }

    fields.push(field);
  }

  return fields;
};

export const resSchemaStr2Field = (schemaStr: string): IWorkflowField[] => {
  let result: IWorkflowField[] = [];

  try {
    const data: IResSchema = JSON.parse(schemaStr);
    result = resSchema2Field(data);
  } catch {
    MessageComponent.showError(i18next.t('parse_res_error'));

    result = [
      {
        ...getInitOutputParamConfig(),
      },
    ];
  }

  return result;
};

export const reqSchemaStr2Field = (schemaStr: string): IWorkflowField[] => {
  let result: IWorkflowField[] = [];

  if (!schemaStr) {
    return result;
  }

  try {
    const data: IReqSchema = JSON.parse(schemaStr);
    result = reqSchema2Field(data);
  } catch (e) {
    MessageComponent.showError(i18next.t('parse_req_error'));

    result = [
      {
        ...getInitInputParamConfig(),
      },
    ];
  }

  return result;
};

export const startSchemaStrField = (schemaStr: string): IWorkflowField[] => {
  let result: IWorkflowField[] = [];
  try {
    const data: IResSchema = JSON.parse(schemaStr);
    result = startSchemaFieldReq(data);
  } catch {
    MessageComponent.showError(i18next.t('json_parse_error'));

    result = [getInitOutputParamConfig()];
  }

  return result;
};

export const startSchemaFieldReq = (schema: IResSchema): IWorkflowField[] => {
  const fields: IWorkflowField[] = [];
  const properties = schema.properties || {};
  const keys = Object.keys(properties);

  for (const key of keys) {
    const property = properties[key];

    const { description, type, default: defaultVal } = property;

    const field: IWorkflowField = {
      name: key,
      required: schema.required?.includes(key),
      description,
      type: type as IWorkflowFieldType,
      value: {
        type: 'generated',
        content: null,
        hint: '',
        default: defaultVal,
      },
      source: 'user',
    };

    if (isResObjSchema(property)) {
      field.schema = resSchema2Field(property);
    }

    if (isResArraySchema(property)) {
      field.schema = {
        name: '',
        type: property.items.type as IWorkflowFieldType,
      };

      if (property.items.type === 'object') {
        (field.schema as IWorkflowField).schema = resSchema2Field(
          property.items,
        );
      }
    }

    fields.push(field);
  }

  return fields;
};

export const STREAM_RESPONSE_EXAMPLE = [
  {
    stream_id: 'id_1',
    is_finish: false,
    content: `${i18next.t('you')}`,
    ext: {
      index_score: 1,
    },
    output_mode: 0,
    content_type: 0,
    return_type: 0,
    context_mode: 0,
  },
  {
    stream_id: 'id_2',
    is_finish: false,
    content: `${i18next.t('good')}`,
    ext: {
      index_score: 1,
    },
    output_mode: 0,
    content_type: 0,
    return_type: 0,
    context_mode: 0,
  },
  {
    stream_id: 'id_3',
    is_finish: true,
    content: `${i18next.t('what')}`,
    ext: {
      index_score: 1,
    },
    output_mode: 0,
    content_type: 0,
    return_type: 0,
    context_mode: 0,
  },
];

export const showFromError = (that, form) => {
  const errors: ValidationErrors | null = null;
  if (errors) {
    const firstError: any = Object.keys(errors)[0];

    if (
      that.elementRef.nativeElement.querySelector(
        `[formControlName=${firstError}]`,
      )
    ) {
      that.elementRef.nativeElement
        .querySelector(`[formControlName=${firstError}]`)
        ?.focus();
    } else {
      that.elementRef.nativeElement
        .querySelector(`[name=${firstError}]`)
        ?.focus();
    }
    return false;
  }
  return true;
};
export function coverPluginInfo(context: any) {
  const toolList: ITool = context.plugin.request_info.tool_info || [];
  const tool_status = context.plugin.test_status || [];

  context.srcData.data = toolList.map((item: ITool) => {
    return {
      tool_id: item.tool_id,
      tool_info: {
        ...item,
        input_schema:
          context.plugin.input_schema.find((i) => i.tool_id === item.tool_id)
            ?.input_schema ?? '{}',
        output_schema:
          context.plugin.output_schema.find((i) => i.tool_id === item.tool_id)
            ?.output_schema ?? '{}',
        intf_type: context.plugin.intf_type.find(
          (i) => i.tool_id === item.tool_id,
        )?.intf_type,
        is_input_list: context.plugin.is_input_list.find(
          (i) => i.tool_id === item.tool_id,
        )?.is_input_list,
        is_output_list: context.plugin.is_output_list.find(
          (i) => i.tool_id === item.tool_id,
        )?.is_output_list,
      },

      toolName: item.tool_chinese_name,
      debuggingStatus:
        tool_status.find((i) => i.tool_id === item.tool_id)?.test_status ?? '',
      toolDependency: context.plugin.tool_dependency_list?.find(
        (i) => i.tool_id === item.tool_id,
      ),
      createTime: context.plugin.created_on,
    };
  });
  context.name = getPluginName(context.plugin, context);

  if (
    context.plugin?.auth_info &&
    Object.keys(context.plugin.auth_info).length
  ) {
    if (
      context.plugin.auth_info.scope === 'HIS_IAM' ||
      context.plugin.auth_info.scope === 'SGOV' ||
      context.plugin.auth_info.scope === 'CUSTOM_IAM'
    ) {
      context.authInfo.type = context.plugin.auth_info.scope;
      let custom_iam_credentials =
        context.plugin.auth_info.custom_iam_credentials;
      if (context.authInfo.type === 'CUSTOM_IAM') {
        context.customIamList = [];
        Object.keys(custom_iam_credentials).forEach((key) => {
          if (custom_iam_credentials[key]) {
            context.customIamList.push({
              name: context.iamMap[key],
              value: custom_iam_credentials[key],
            });
          }
        });
      }
    } else {
      processApiKey(context);
    }
  } else {
    context.authInfo.type = 'no_auth';
    context.authInfo.location = null;
    context.authTbd.data = [];
  }
}
export function processApiKey(context: any) {
  context.authInfo.type = 'API Key';
  context.authInfo.location = capitalize(context.plugin.auth_info.domain);

  if (context.plugin.auth_info?.scope === 'SERVICE') {
    context.authTbd.data = context.plugin.auth_info.auth_keys.map((auth) => {
      return {
        name: auth.target_name,
        value: auth?.auth_key ?? '',
      };
    });
  }
}
export function coverToolInfo(context: any) {
  const tool_info = context.plugin?.request_info.tool_info?.find(
    (item) => item.tool_id === context.toolId,
  );
  tool_info.input_schema = context.plugin?.input_schema.find(
    (item) => item.tool_id === context.toolId,
  )?.input_schema;
  tool_info.output_schema = context.plugin?.output_schema.find(
    (item) => item.tool_id === context.toolId,
  )?.output_schema;
  context.toolInfo = tool_info;
  context.name = getPluginName(context.plugin, context);
  if (
    context.plugin?.auth_info &&
    Object.keys(context.plugin.auth_info).length
  ) {
    processApiKey(context);
  } else {
    context.authInfo.type = 'no_auth';
    context.authInfo.location = null;
    context.authTbd.data = [];
  }
  context.req = pluginSchemaStr2Args(context.toolInfo?.input_schema);
  context.res = pluginSchemaStr2Res(context.toolInfo.output_schema);
  context.requestSrcData.data = context.getFlatData(context.req);
  context.responseSrcData.data = context.getFlatData(context.res);
}

export function getPluginName(plugin: IPluginWithTools, context: any): string {
  if (context.lang === 'zh-cn') {
    return plugin.plugin_chinese_name
      ? `${plugin.plugin_chinese_name} ( ${plugin.plugin_display_name} )`
      : plugin.plugin_display_name;
  } else {
    return plugin.plugin_display_name;
  }
}

export function getFlatData(
  nodes: any[],
  level?: number,
): any[] {
  let result: any[] = [];
  if (!nodes) {
    return result;
  }
  nodes.forEach((item: any): void => {
    item.level = level ? level : 0;
    item.hasChildren = item.children && item.children.length > 0;
    result.push(item);
    if (item.expand && item.hasChildren) {
      result = result.concat(getFlatData(item.children, item.level + 1));
    }
  });

  return result;
}

export function IWorkflowFieldListToSchema(obj: IWorkflowField[]): any {
  const res = {
    properties: {},
    required: [],
    type: 'object',
  };
  for (let i = 0; i < obj.length; i++) {
    if (obj[i].name) {
      if (obj[i].type === undefined || obj[i].type === null) {
        obj[i].type = 'string';
      }
      res.properties[obj[i].name] = {
        default: obj[i]?.value?.content || '',
        description: obj[i].description,
        format: 'input',
        type: obj[i].type,
        'x-hw-default': '',
        'x-hw-format': 'input',
        'x-hw-label': '',
        'x-hw-select-options': [],
        'x-hw-visibility': 'none',
      };
      if (obj[i].required) {
        res.required.push(obj[i].name);
      }
    }
  }
  return res;
}

export function IWFViewListToSchema(obj: IWFView[]): any {
  const res = {
    properties: {},
    required: [],
    type: 'object',
  };
  for (let i = 0; i < obj.length; i++) {
    if (obj[i].name) {
      res.properties[obj[i].name] = {
        default: '',
        description: obj[i].description,
        format: 'input',
        type: obj[i].type,
        'x-hw-default': '',
        'x-hw-format': 'input',
        'x-hw-label': '',
        'x-hw-select-options': [],
        'x-hw-visibility': 'none',
      };
      if (obj[i].type.indexOf('array<') >= 0) {
        res.properties[obj[i].name].type = 'array';
        const itemType = obj[i].type.match(/array<(.+)>/)[1];
        if (itemType === 'object' && obj[i].children) {
          const childObj = IWFViewListToSchema(obj[i].children);
          res.properties[obj[i].name].items = {
            default: '',
            description: '',
            format: 'input',
            type: itemType,
            'x-hw-default': '',
            'x-hw-format': 'input',
            'x-hw-label': '',
            'x-hw-select-options': [],
            'x-hw-visibility': 'none',
            properties: childObj.properties,
            required: childObj.required,
          };
        } else {
          res.properties[obj[i].name].items = {
            default: '',
            description: '',
            format: 'input',
            type: itemType,
            'x-hw-default': '',
            'x-hw-format': 'input',
            'x-hw-label': '',
            'x-hw-select-options': [],
            'x-hw-visibility': 'none',
          };
        }
      } else if (obj[i].children) {
        const childObj = IWFViewListToSchema(obj[i].children);
        res.properties[obj[i].name].properties = childObj.properties;
        res.properties[obj[i].name].required = childObj.required;
      }
      if (obj[i].required) {
        res.required.push(obj[i].name);
      }
    }
  }
  return res;
}

export function mapTreeAddKeyIndex(tree, start) {
  return (tree || []).map((item, index) => {
    item.keyindex = `${start}_${index}`;
    if (item.children) {
      item.children = mapTreeAddKeyIndex(item.children, `${start}_${index}`);
    }
    return item;
  });
}

export function mapTreeAddKeyAndChildIndex(tree, start) {
  return (tree || []).map((item, index) => {
    item.key = `${index}`;
    if (item?.schema?.length > 0 && item.type === 'object') {
      item.isObjRoot = true;
      item.children = mapTreeSchemaIndex(item.schema, `${index}`, item.value.type);
      item.children = setAllChildrenVal(item.children, item.value);
    }
    return item;
  });
}

function mapTreeSchemaIndex(schema, start, rootValType) {
  return (schema || []).map((item, index) => {
    let newitem: any = {
      options: [{ label: item.type, value: 'literal' }],
      key: `${start}_${index}`,
      type: item.type,
      isChild: true,
      name: item.name,
      rootValType: rootValType,
      isObjChild: item.type === 'object',
      value: {
        content: '',
        default: '',
        hint: '',
        type: 'literal',
      },
    };

    if (item?.schema?.length > 0 && item.type === 'object') {
      newitem.children = mapTreeSchemaIndex(item.schema, `${start}_${index}`, rootValType);
    }
    return newitem;
  });
}

export function eachChildrenToRootObj(children, value) {
  let res = {};
  (children || []).map((item, index) => {
    if (item?.children?.length > 0 && item.type === 'object') {
      res[item.name] = eachChildrenToRootObj(item?.children, value);
    } else {
      if (item.key === value.key) {
        if (item.type.startsWith('array')) {
          try {
            res[item.name] = JSON.parse(value.value.content);
          } catch {
            res[item.name] = null;
          }
        } else {
          res[item.name] = value.value.content;
        }
      } else {
        let itemVal = item.value.content;
        if (item.type.startsWith('array')) {
          try {
            itemVal = JSON.parse(itemVal);
          } catch {
            itemVal = null;
          }
        }
        if (item.type === 'object') {
          try {
            itemVal = JSON.parse(itemVal);
          } catch {
            itemVal = null;
          }
        }
        res[item.name] = itemVal;
      }
    }
  });
  return res;
}

export function setAllChildrenVal(children, value) {
  let obj = {};
  try {
    obj = JSON.parse(value.content);
  } catch {
    obj = {};
  }
  if (value.type !== 'literal') {
    obj = {};
  }
  children = setEachAllChildrenVal(children, obj, value.type);
  return children;
}

function setEachAllChildrenVal(children, objVal, rootValType) {
  if (Object.keys(objVal).length <= 0) {
    return (children || []).map((item, index) => {
      item.rootValType = rootValType;
      item.value.content = '';
      if (item.children) {
        item.children = setEachAllChildrenVal(item.children, objVal, rootValType);
      }
      return item;
    });
  } else {
    return (children || []).map((item, index) => {
      item.rootValType = rootValType;
      if (objVal[item.name] !== null && objVal[item.name] !== undefined) {
        let newVal = objVal[item.name];
        if (item.type === 'object') {
          if (item.children) {
            item.children = setEachAllChildrenVal(item.children, objVal[item.name], rootValType);
          }
        } else {
          if (item.type.startsWith('array')) {
            if (newVal) {
              newVal = JSON.stringify(newVal);
            } else {
              newVal = null;
            }
          }

          item.value.content = newVal;
        }
      }
      return item;
    });
  }
}
