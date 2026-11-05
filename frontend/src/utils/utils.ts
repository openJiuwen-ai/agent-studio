import { MessageComponent, StorageService } from '@shared/services/cfdata.service';
import {
  NodeInfo,
  IIntentNode,
  IControllerNode,
} from '@routes/agent-center/app-flow/node.type';
import { FlowUtils } from '@routes/agent-center/app-flow/utils/flow-utils';
import i18next from 'i18next';

export function handleCommonReqError(error: any): void {
  if (error?.data?.error_code) {
    MessageComponent.showError(error.data.error_msg, 3000);
  }
}

export function compressImage(
  file: File,
  maxSizeKB: number,
  successCb: (base64String: string) => void,
  errorCb: (error: any) => void,
) {
  const reader = new FileReader();

  reader.addEventListener('load', (event) => {
    if (file.size / 1024 <= maxSizeKB) {
      successCb(reader.result as string);
      return;
    }

    const img = new Image();
    img.src = event.target.result as string;

    img.addEventListener('load', () => {
      try {
        const cvs = document.createElement('canvas');
        const ctx = cvs.getContext('2d');
        const width = img.width;
        const height = img.height;

        cvs.width = width;
        cvs.height = height;
        ctx.drawImage(img, 0, 0, width, height);

        let quality = 0.9;
        let base64String = cvs.toDataURL('image/jpeg', quality);

        while (base64String.length / 1024 > maxSizeKB && quality > 0.1) {
          quality = Math.round((quality - 0.1) * 10) / 10;
          base64String = cvs.toDataURL('image/jpeg', quality);
        }

        successCb(base64String);
      } catch (error) {
        errorCb(error);
      }
    });
  });

  reader.readAsDataURL(file);
}

export const isIntegerStr = (value: string | number): boolean => {
  if (typeof value === 'number') {
    return true;
  }

  if (value?.endsWith('.')) {
    return false;
  }

  const num = Number(value);
  return !Number.isNaN(num) && Number.isInteger(num);
};

export const isNumberStr = (value: string | number): boolean => {
  if (typeof value === 'number') {
    return true;
  }

  if (typeof value === 'boolean' || value.endsWith('.')) {
    return false;
  }

  return !!value && !Number.isNaN(Number(value));
};

export const isMacOS = () => {
  return navigator.userAgent.toLowerCase().includes('mac');
};

export const removeHTMLTag = (str: string) => {
  return str.replace(/<[^>]*>/g, '');
};

/** 在高级模式的意图识别节点的dsl中，将branches赋值为空数组 */
export const modifyAdvancedDsl = (nodes: NodeInfo[]) => {
  nodes.forEach((item) => {
    if (FlowUtils.isAdvancedModeNew(item)) {
      (item as IIntentNode).branches = [];
    }
  });
}

export function getTypeOfData(data: any): string {
  const res = Object.prototype.toString.call(data);
  return res.substr(0, res.length - 1).split(' ')[1];
}

export function convertSearchString2Obj(search: string): Record<string, any> {
  const res: Record<string, any> = {};
  const searchParams = search?.startsWith('?') ? search.substring(1) : search;
  if (!searchParams) {
    return res;
  }
  searchParams.split('&').forEach((item) => {
    const [key, value] = item.split('=');
    if (key) {
      if (res[key]) {
        if (Array.isArray(res[key])) {
          res[key].push(value);
        } else {
          res[key] = [res[key], value];
        }
      } else {
        res[key] = value;
      }
    }
  });
  return res;
}

export function convertObj2SearchString(params: Record<string, any> = {}): string {
  const result: string[] = [];
  const keys = Object.keys(params);
  keys.forEach((key) => {
    const type = getTypeOfData(params[key]);
    if (type === 'Array') {
      params[key].forEach((value: any) => {
        const valueType = getTypeOfData(value);
        const encodedValue = ['Number', 'String', 'Boolean'].includes(valueType) ? value : '';
        result.push(encodeURIComponent(key) + '=' + encodeURIComponent(encodedValue));
      });
    } else {
      const encodedValue = ['Number', 'String', 'Boolean'].includes(type) ? params[key] : '';
      result.push(encodeURIComponent(key) + '=' + encodeURIComponent(encodedValue));
    }
  });
  return result.join('&');
}

export function reArrangeSearchParam(curUrl: URL): string {
  const { origin, pathname, search, hash } = curUrl;
  const hashRoute = hash.split('?')[0];
  let suffixStr = hash.split('?')[1] || '';
  const prefixStr = search.substring(1);
  const prefixObj = convertSearchString2Obj(prefixStr);
  const defaultPrefixParams = [
    'locale',
    'region',
    'agencyId',
    'app_id',
    'source',
    'enterprise_project_id',
    'iscros',
    'cfModuleHide',
    'serviceModuleHide',
  ];
  Object.keys(prefixObj).forEach((param) => {
    if (!defaultPrefixParams.includes(param)) {
      suffixStr = suffixStr ? `${suffixStr}&${param}=${prefixObj[param]}` : `${param}=${prefixObj[param]}`;
      delete prefixObj[param];
    }
  });
  const newPrefixStr = convertObj2SearchString(prefixObj);
  const newSearch = newPrefixStr ? `?${newPrefixStr}` : '';
  const newHash = hashRoute + (suffixStr ? `?${suffixStr}` : '');
  return `${origin}${pathname}${newSearch}${newHash}`;
}

export function initHistoryInterceptor(): void {
  const historyWrapper = (type: string) => {
    const originHistoryEvent = history[type];
    return function (this: any, ...args: any[]) {
      let fullUrl: URL;
      const { origin, pathname, search } = location;
      if (args[2]?.startsWith('#')) {
        fullUrl = new URL(`${origin}${pathname}${search}${args[2]}`);
      } else {
        fullUrl = new URL(args[2]);
      }
      if (search) {
        args[2] = reArrangeSearchParam(fullUrl);
      }
      const res = originHistoryEvent.apply(this, args);
      window.dispatchEvent(new Event(type));
      return res;
    };
  };
  history.pushState = historyWrapper('pushState');
  history.replaceState = historyWrapper('replaceState');
};

/** output手动输出的需要补上type string */
export const modifyOutput = (params: any) => {
  const nodes = params?.details?.nodes || [];
  nodes.forEach((node) => {
    if (node?.type === 'Workflow') {
      node.outputs?.forEach((o) => {
        if (!o.type) {
          o.type = 'string';
        }
      });
    }
  });
};

/** 填充高级意图节点的branches字段，作为右链接桩 */
export const fillAdvancedBranches = (nodes: NodeInfo[], edges: any[]) => {
  nodes.forEach((item) => {
    if (FlowUtils.isAdvancedModeNew(item)) {
      (item as IIntentNode).branches = [
        {
          id: 'branch_0',
          configs: {
            category: i18next.t('other_intention'),
          },
        },
      ];
    }
  });
  edges.forEach((item) => {
    if (item?.target?.includes('intent_container')) {
      item.branch = 'branch_0';
    }
  });
};

/** 删除视图层所需的key-value，保证dsl结构的一致性 */
export const deleteViewParamsForDsl = (nodes: NodeInfo[]) => {
  const controllerNode = nodes.find(
    (n) => n.type === 'Controller',
  ) as IControllerNode;

  if (controllerNode) {
    controllerNode.configs.workflows = controllerNode.configs.workflows.map(
      (item) => {
        const { inputs, outputs, ...rest } = item;
        return rest;
      },
    );
  }
};

export function isDevelpor() {
  const userInfo =
    StorageService.getSessionStorage('CUR_SPACE_OPTIONS') &&
    JSON.parse(StorageService.getSessionStorage('CUR_SPACE_OPTIONS'));
  return userInfo?.role === 'DEVELOPER';
}


export function halfModalWidth(windowWidth) {

  if (windowWidth> 1920) {
    return '900px';
  } else {
    return '700px';
  }
}

export interface ICommonError{
  error_code:string,

  message?:string,
  error_msg?:string,
  error_msg_front? : string,

  error_reason?:string,
  error_suggestion?:string,

  /** 字段级校验明细（如工具 schema 缺 description/location） */
  details?: { error_code?: string; error_msg?: string }[];

}
 /**
 * 构建错误信息的dom
 * @param error
 * @private
 */
export function buildErrorMsgStr(error:ICommonError) {

  let err_dom = '';
  // 1. 优先使用 message 字段
  const err_message = error?.error_msg || error?.message || error?.error_msg_front;
  if (!err_message) {
    // 如果没有 err_message，直接返回
    return "";
  }
  err_dom+= `<strong  style="font-size:14px;">${err_message}</strong>`

  // 2. 如果有 error_reason
  const reason = error?.error_reason;
  if(reason){
    err_dom += `${i18next.t('httpservice_4')}${reason}`;
  }
  // 3. 如果有 error_suggestion
  const suggestion = error?.error_suggestion;
  if(suggestion){
    err_dom += `${i18next.t('httpservice_5')}${suggestion}`;
  }
  // 4. 字段级 details：当主文案未带上具体属性原因时补展示（REQ_015）
  const details = error?.details;
  if (Array.isArray(details) && details.length > 0) {
    const detailMsgs = details
      .map(d => d?.error_msg)
      .filter((msg): msg is string => !!msg && !err_message.includes(msg));
    if (detailMsgs.length > 0) {
      err_dom += `<br/>${detailMsgs.join('<br/>')}`;
    }
  }
  // 5.错误码
  const error_code = error?.error_code;
  if(error_code){
    err_dom += `${i18next.t('httpservice_8')}${error_code}`;
  }
  return err_dom
}

export function getSessionStorage(key: string): any {
  try {
    const sessionData = window.sessionStorage.getItem(key);
    if (sessionData === null) {
      return {};
    }
    return JSON.parse(sessionData);
  } catch {
    return {};
  }
}

export function getLocalStorage(
  key: string,
  isErr: boolean = false,
  cacheVersion: string = 'cfdata-default'
): any {
  if (!window.localStorage) {
    return null;
  }
  const versionItem = localStorage.getItem(key + '_cacheVersion');
  const expiresItem = localStorage.getItem(key + '_expiresIn');
  const value = localStorage.getItem(key);
  if (expiresItem === undefined || expiresItem === null) {
    return parseJson(value, null);
  }
  const expiresIn = Number(expiresItem) || 0;
  if (cacheVersion !== versionItem) {
    delLocalStorage(key);
    return null;
  }
  if (expiresIn < Date.now() && !isErr) {
    delLocalStorage(key);
    return null;
  }
  return parseJson(value, null);
}

export function parseJson(value: string | null, defaultValue: any = null): any {
  if (value === null || value === undefined) {
    return defaultValue;
  }
  try {
    return JSON.parse(value);
  } catch {
    return defaultValue;
  }
}

export function delLocalStorage(key: string): void {
  if (!window.localStorage) {
    return;
  }
  localStorage.removeItem(key);
  localStorage.removeItem(key + '_cacheVersion');
  localStorage.removeItem(key + '_expiresIn');
}

export function setSessionStorage(key: string, value: any): boolean {
  let valueStr: string;
  try {
    valueStr = JSON.stringify(value);
  } catch (e) {
    return false;
  }
  try {
    sessionStorage.setItem(key, valueStr);
  } catch (e) {
    return false;
  }
  return true;
}

export function delSessionStorage(name: string): boolean {
  sessionStorage.removeItem(name);
  return true;
}

export function setLocalStorage(
  key: string,
  value: any,
  expires?: number,
  cacheVersion: string = 'cfdata-default'
): boolean {
  if (!localStorage) {
    return false;
  }
  clearExpiredStorage();
  let expireSecs: number;
  if (expires === undefined || expires === null) {
    expireSecs = 24 * 60 * 60;
  } else {
    expireSecs = Math.abs(expires);
  }
  const schedule = Date.now() + expireSecs * 1000;
  let valueStr: string;
  try {
    valueStr = JSON.stringify(value);
  } catch (e) {
    return false;
  }
  try {
    localStorage.setItem(key, valueStr);
    localStorage.setItem(key + '_expiresIn', schedule.toString());
    localStorage.setItem(key + '_cacheVersion', cacheVersion);
  } catch (e) {
    const tempScripts: any[] = [];
    for (const item in localStorage) {
      if (item.indexOf(key) === 0) {
        const parsed = parseJson(localStorage[item], null);
        if (parsed) {
          tempScripts.push(parsed);
        }
      }
    }
    if (tempScripts.length) {
      tempScripts.sort((a, b) => a.stamp - b.stamp);
      delLocalStorage(tempScripts[0].key);
      return setLocalStorage(key, value, expireSecs);
    } else {
      return false;
    }
  }
  return true;
}

export function clearExpiredStorage(): void {
  Object.keys(localStorage).forEach((item) => {
    if (item?.endsWith('_expiresIn')) {
      const expireTime = localStorage.getItem(item);
      if (!expireTime || !Number(expireTime) || Number(expireTime) < Date.now()) {
        delLocalStorage(item.replace('_expiresIn', ''));
      }
    }
  });
}


interface CookieCacheItem {
  key: string;
  domain: string;
}

const cookieCache: CookieCacheItem[] = [];

function getCookieDomain(domain?: string): string {
  if (domain) {
    return domain;
  }
  const domains = document.domain.split('.');
  return domains.length > 3 ? domains.slice(1).join('.') : domains.slice(-2).join('.');
}

export function getCookie(key: string): any {
  const cookies = document.cookie.split('; ');
  for (const cookie of cookies) {
    const [cookieKey, cookieValue] = cookie.split('=');
    if (cookieKey === key) {
      return parseJson(cookieValue, cookieValue);
    }
  }
  return '';
}

export function delCookie(key: string): void {
  const date = new Date();
  date.setTime(date.getTime() - 10000);
  document.cookie = `${key}=v; expires=${date.toUTCString()}`;
}

export function flushCookie(): void {
  cookieCache.forEach(({ key, domain }) => {
    const date = new Date();
    date.setTime(date.getTime() - 10000);
    document.cookie = `${key}=v; expires=${date.toUTCString()};path=/;domain=${domain}`;
  });
  cookieCache.length = 0;
}

export function isFunction(value: any): value is Function {
  return typeof value === 'function';
}

export function isObject(value: any): boolean {
  return typeof value === 'object' && value !== null;
}

export function deepClone<T>(obj: T): T {
  if (obj === null || typeof obj !== 'object') {
    return obj;
  }

  if (obj instanceof Date) {
    return new Date(obj.getTime()) as any;
  }

  if (obj instanceof Array) {
    return obj.map(item => deepClone(item)) as any;
  }

  if (obj instanceof RegExp) {
    return new RegExp(obj.source, obj.flags) as any;
  }

  if (obj instanceof Map) {
    const cloneMap = new Map();
    obj.forEach((value, key) => {
      cloneMap.set(key, deepClone(value));
    });
    return cloneMap as any;
  }

  if (obj instanceof Set) {
    const cloneSet = new Set();
    obj.forEach(value => {
      cloneSet.add(deepClone(value));
    });
    return cloneSet as any;
  }

  const cloneObj = {} as T;
  for (const key in obj) {
    if (Object.prototype.hasOwnProperty.call(obj, key)) {
      cloneObj[key] = deepClone(obj[key]);
    }
  }
  return cloneObj;
}

export function removeNode(tree: any[], targetNode: any): void {
  if (!tree || !Array.isArray(tree) || tree.length === 0) {
    return;
  }

  for (let i = 0; i < tree.length; i++) {
    const node = tree[i];
    if (node === targetNode) {
      tree.splice(i, 1);
      return;
    }
    if (node.children && Array.isArray(node.children)) {
      removeNode(node.children, targetNode);
    }
  }
}
