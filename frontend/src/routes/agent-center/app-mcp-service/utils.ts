import { MessageComponent } from '@shared/services/cfdata.service';
import { IWorkflowField, IWorkflowFieldType } from '../app-flow/node.type';
import {
  IDataAcquisitionConfigSchema,
  IReqSchema,
  IResSchema,
} from '../app-plugin/app-plugin.interface';
import {
  getInitInputParamConfig,
  getInitOutputParamConfig,
} from '../app-flow/flow.const';
import {
  isArraySchema,
  isObjSchema,
  isResArraySchema,
  isResObjSchema,
} from '../app-plugin/utils';
import i18next from 'i18next';

// MCP请求参数解析
export const reqSchemaStrMCPField = (schemaStr: string): IWorkflowField[] => {
  let result: IWorkflowField[] = [];

  if (!schemaStr) {
    return result;
  }

  try {
    const data: IReqSchema = JSON.parse(schemaStr);
    result = reqSchemaMCPField(data);
  } catch {
    MessageComponent.showError(i18next.t('parse_req_error'));

    result = [
      {
        ...getInitInputParamConfig(),
      },
    ];
  }

  return result;
};

// MCP响应参数解析
export const resSchemaStrMCPField = (schemaStr: string): IWorkflowField[] => {
  // 无出参时静默返回，避免详情页误弹「响应参数数据格式有误」
  if (!schemaStr) {
    return [];
  }
  let result: IWorkflowField[] = [];

  try {
    const data: IResSchema = JSON.parse(schemaStr);
    if (!data || typeof data !== 'object') {
      return [];
    }
    result = resSchemaMCPField(data);
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

// DataAcquisition配置参数解析
export const configSchemaField = (
  schemaStr: string,
): IDataAcquisitionConfigSchema[] => {
  let result: IDataAcquisitionConfigSchema[] = [];

  try {
    result = JSON.parse(schemaStr);
    result.map((r) => {
      if (!r.value) {
        r.value = r.label;
      }
    });
  } catch {
    MessageComponent.showError(i18next.t('parse_data_acquisition_error'));
  }

  return result;
};

export const reqSchemaMCPField = (schema: IReqSchema): IWorkflowField[] => {
  const fields: IWorkflowField[] = [];
  const properties = schema.properties ?? {};
  const requiredKeys = new Set(schema.required || []);

  for (const [key, property] of Object.entries(properties)) {
    const {
      description = '',
      type,
      default: defaultVal,
      oneOf,
      anyOf,
    } = property;

    if (Array.isArray(oneOf) || Array.isArray(anyOf)) {
      const dataArr = oneOf || anyOf;
      const types: any = [...new Set(dataArr.map((item) => item.type))].join(
        ' | ',
      );
      const desc: any = [
        ...new Set(dataArr.map((item) => item.description)),
      ].join(';');
      const ofFields: any = dataArr.map((v: any, i: number) => {
        if (v.type !== 'array' && v.type !== 'object') {
          return {
            name: '',
            required: v.required,
            description: v.description,
            type: v.type,
            value: {
              type: 'literal',
              content: '',
              hint: '',
            },
            source: 'user',
          };
        } else {
          const res = reqSchemaMCPField({
            type: v.type,
            properties: v.properties ?? {},
            required: v.required ?? [],
          });
          if (v.type === 'array' && res.length === 0) {
            return {};
          }
          return res;
        }
      });

      fields.push({
        name: key,
        required: requiredKeys.has(key),
        description: desc,
        type: types,
        value: {
          type: 'literal',
          content: '',
          hint: '',
        },
        schema: ofFields,
        source: 'user',
      });
      continue;
    }

    let defaultValue: string | number | boolean | Record<string, any> =
      defaultVal;
    if (type === 'boolean' && typeof defaultVal !== 'boolean') {
      if (defaultVal === 'true') {
        defaultValue = true;
      } else if (defaultVal === 'false') {
        defaultValue = false;
      }
    }

    const field: IWorkflowField = {
      name: key,
      required: requiredKeys.has(key),
      description,
      type: type as IWorkflowFieldType,
      value: {
        type: 'literal',
        content:
          typeof defaultValue === 'object'
            ? JSON.stringify(defaultValue)
            : defaultValue ?? '',
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
        (field.schema as IWorkflowField).schema = reqSchemaMCPField(
          property.items,
        );
      }
    }

    if (isObjSchema(property)) {
      if (property.properties) {
        field.schema = reqSchemaMCPField(property);
      } else {
        field.schema = [];
      }
    }
    fields.push(field);
  }

  return fields;
};

export const resSchemaMCPField = (schema: IResSchema): IWorkflowField[] => {
  const fields: IWorkflowField[] = [];
  const properties = schema.properties ?? {};
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
        content: null,
        hint: '',
        type: 'generated',
        default: '',
      },
      source: 'user',
    };

    if (isResArraySchema(property)) {
      field.schema = {
        type: property.items.type as IWorkflowFieldType,
        name: '',
      };

      if (property.items.type === 'object') {
        (field.schema as IWorkflowField).schema = resSchemaMCPField(
          property.items,
        );
      }
    }

    if (isResObjSchema(property)) {
      if (property.properties) {
        field.schema = resSchemaMCPField(property);
      } else {
        field.schema = [];
      }
    }

    fields.push(field);
  }

  return fields;
};


export const resSchemaDataField = (schemaStr: string) => {
    let result={};

    if (!schemaStr) {
      return result;
    }

    try {
      const data  = JSON.parse(schemaStr);
      result = data
    } catch {
      MessageComponent.showError(i18next.t('parse_req_error'));
    }

    return result;
  };
