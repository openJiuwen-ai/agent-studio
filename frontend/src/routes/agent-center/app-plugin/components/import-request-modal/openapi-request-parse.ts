/**
 * OpenAPI / Swagger helpers for「导入请求」.
 * Keeps parseYaml free of TypeError on $ref, Swagger 2.0 params,
 * non-JSON bodies, and path-level `parameters` keys.
 */

const HTTP_METHODS = new Set([
  'get',
  'post',
  'put',
  'delete',
  'patch',
  'head',
  'options',
]);

const BODY_CONTENT_TYPES = [
  'application/json',
  'application/x-www-form-urlencoded',
  'multipart/form-data',
];

export type ImportedApiParam = {
  name: string;
  default?: unknown;
  type?: string;
  schema?: unknown;
  location: string;
};

export type ImportedApiInfo = {
  method: string;
  url: string;
  headers: { key: string; value: unknown }[];
  params: ImportedApiParam[];
};

export type ParseOpenApiResult =
  | { ok: true; apiInfo: ImportedApiInfo }
  | { ok: false; error: string };

/** Resolve a local `#/a/b/c` $ref one level deep against the root document. */
export function resolveLocalRef(doc: any, node: any): any {
  if (!node || typeof node !== 'object' || typeof node.$ref !== 'string') {
    return node;
  }
  const ref: string = node.$ref;
  if (!ref.startsWith('#/')) {
    return node;
  }
  const parts = ref.slice(2).split('/');
  let cur: any = doc;
  for (const part of parts) {
    if (cur == null || typeof cur !== 'object') {
      return node;
    }
    cur = cur[part];
  }
  return cur ?? node;
}

export function capitalizeFirstLetter(value: string | undefined | null): string {
  if (value == null || value === '') {
    return '';
  }
  const trimmed = String(value).trim();
  return trimmed.slice(0, 1).toUpperCase() + trimmed.slice(1);
}

/** Map OpenAPI / Swagger `in` to tool schema location labels. */
export function mapParamLocation(paramIn: string | undefined | null): string {
  if (paramIn == null || paramIn === '') {
    return '';
  }
  const key = String(paramIn).trim().toLowerCase();
  if (key === 'header' || key === 'headers') {
    return 'Headers';
  }
  if (key === 'formdata' || key === 'form_data') {
    return 'Body';
  }
  return capitalizeFirstLetter(paramIn);
}

export function pickHttpMethod(
  pathItem: Record<string, unknown> | undefined | null,
): string | null {
  if (!pathItem || typeof pathItem !== 'object') {
    return null;
  }
  const key = Object.keys(pathItem).find((k) =>
    HTTP_METHODS.has(k.toLowerCase()),
  );
  return key ?? null;
}

export function buildBaseUrl(doc: any): string {
  const serverUrl = doc?.servers?.[0]?.url;
  if (typeof serverUrl === 'string' && serverUrl) {
    return serverUrl.replace(/\/$/, '');
  }
  // Swagger 2.0
  const host = doc?.host;
  if (typeof host === 'string' && host) {
    const scheme =
      Array.isArray(doc.schemes) && doc.schemes[0]
        ? String(doc.schemes[0])
        : 'https';
    const basePath =
      typeof doc.basePath === 'string' ? doc.basePath.replace(/\/$/, '') : '';
    return `${scheme}://${host}${basePath}`;
  }
  return '';
}

function paramSchema(item: any): { schema: any; defaultVal: unknown; type: string | undefined } {
  // OpenAPI 3 inline schema
  if (item?.schema && typeof item.schema === 'object') {
    return {
      schema: item.schema,
      defaultVal: item.schema.default ?? item.schema.example,
      type: item.schema.type,
    };
  }
  // Swagger 2.0: type / default on the parameter itself
  if (item?.type != null || item?.default != null || item?.example != null) {
    const schema = {
      type: item.type,
      default: item.default,
      example: item.example,
      format: item.format,
    };
    return {
      schema,
      defaultVal: item.default ?? item.example,
      type: item.type,
    };
  }
  return { schema: undefined, defaultVal: undefined, type: undefined };
}

export function mapYamlParameters(
  doc: any,
  parameters: any[] | undefined | null,
): ImportedApiParam[] {
  if (!Array.isArray(parameters)) {
    return [];
  }
  const mapped: ImportedApiParam[] = [];
  for (const raw of parameters) {
    const item = resolveLocalRef(doc, raw);
    if (!item || typeof item !== 'object' || !item.name) {
      continue;
    }
    const { schema, defaultVal, type } = paramSchema(item);
    mapped.push({
      name: item.name,
      default: defaultVal,
      type,
      schema,
      location: mapParamLocation(item.in),
    });
  }
  return mapped;
}

/**
 * Extract body fields from requestBody.
 * Supports application/json and form content types; returns an error
 * string when content exists but none of the known types are present,
 * or when requestBody is an unresolved $ref-only object without content.
 */
export function mapYamlRequestBody(
  doc: any,
  requestBody: any | undefined | null,
): { params: ImportedApiParam[]; error?: string } {
  if (!requestBody) {
    return { params: [] };
  }
  const body = resolveLocalRef(doc, requestBody);
  if (!body || typeof body !== 'object') {
    return {
      params: [],
      error: 'Unsupported requestBody structure in OpenAPI document.',
    };
  }
  const content = body.content;
  if (!content || typeof content !== 'object') {
    // Swagger 2.0 often puts body in parameters (in: body); no error here.
    return { params: [] };
  }

  let properties: Record<string, any> | undefined;
  for (const ct of BODY_CONTENT_TYPES) {
    const schema = content[ct]?.schema;
    if (schema?.properties && typeof schema.properties === 'object') {
      properties = schema.properties;
      break;
    }
  }

  if (!properties) {
    const keys = Object.keys(content);
    if (keys.length > 0) {
      return {
        params: [],
        error: `Unsupported request body content-type: ${keys.join(', ')}. Supported: ${BODY_CONTENT_TYPES.join(', ')}.`,
      };
    }
    return { params: [] };
  }

  return {
    params: Object.keys(properties).map((key) => ({
      name: key,
      default: properties![key]?.example ?? properties![key]?.default,
      type: properties![key]?.type,
      location: 'Body',
    })),
  };
}

export function parseOpenApiDoc(doc: any): ParseOpenApiResult {
  if (!doc || typeof doc !== 'object' || !doc.paths || typeof doc.paths !== 'object') {
    return {
      ok: false,
      error: 'Invalid OpenAPI document: missing paths.',
    };
  }

  const pathKeys = Object.keys(doc.paths);
  if (pathKeys.length === 0) {
    return { ok: false, error: 'Invalid OpenAPI document: paths is empty.' };
  }

  const path = pathKeys[0];
  const pathItem = doc.paths[path];
  const method = pickHttpMethod(pathItem);
  if (!method) {
    return {
      ok: false,
      error: 'Invalid OpenAPI document: no HTTP method under the first path.',
    };
  }

  const data = pathItem[method] || {};
  const pathParams = Array.isArray(pathItem?.parameters)
    ? pathItem.parameters
    : [];
  const opParams = Array.isArray(data.parameters) ? data.parameters : [];
  const parameters = mapYamlParameters(doc, [...pathParams, ...opParams]);

  const bodyResult = mapYamlRequestBody(doc, data.requestBody);
  if (bodyResult.error) {
    return { ok: false, error: bodyResult.error };
  }

  let headers: { key: string; value: unknown }[] = [];
  const rawHeaders = data.headers;
  if (rawHeaders && typeof rawHeaders === 'object' && !Array.isArray(rawHeaders)) {
    headers = Object.keys(rawHeaders).map((key) => {
      const schema = rawHeaders[key]?.schema;
      return {
        key,
        value: schema?.default ?? schema?.example,
      };
    });
  }

  const base = buildBaseUrl(doc);
  return {
    ok: true,
    apiInfo: {
      method: method.toUpperCase(),
      url: `${base}${path}`,
      headers,
      params: [...parameters, ...bodyResult.params],
    },
  };
}
