import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, tap, timeout } from 'rxjs/operators';
import { CustomErrorResponse } from '../types/request';
import { Router } from '@angular/router';
import { I18NextEagerPipe } from 'angular-i18next';
import { environment } from 'src/environment/environment';
import { AGENT_CORE } from '../constants/common';
import {
  buildErrorMsgStr,
  convertObj2SearchString,
  getLocalStorage,
  getSessionStorage,
  ICommonError,
  isObject,
  setSessionStorage,
  isFunction,
} from 'src/utils/utils';
import { NzMessageService } from 'ng-zorro-antd/message';
import { CommonUtils } from '../../utils/common.util';
import { StorageService } from '@shared/services/cfdata.service';
enum MethodType {
  GET = 'GET',
  POST = 'POST',
  DELETE = 'DELETE',
  PUT = 'PUT',
  PATCH = 'PATCH',
}

function isPlainObject(value: any): boolean {
  return isObject(value) && !Array.isArray(value);
}

export interface MessageConfig {
  success?: string | ((res: any) => string);
  fail?: string | ((res: CustomErrorResponse) => string);
  inProgress?: string | ((res: any) => string);
  showFailMessage?: boolean; // 默认true
  /** 期望调用者能感知到每个接口的报错，做出明确的处理，所以此配置建议仅特定场景使用，如列表，抛错时会持续无意义loading */
  thorwWhenFail?: boolean; // 默认true, 失败时是否抛出错误
  customError?: boolean; // 默认false
}

export interface HttpConfig {
  url: string;
  serviceId?: string;
  workspaceId?: string;
  messageConfig?: MessageConfig;
  query: any;
  params: any;
  headers: any;
  body: any;
  dataType: any;
  timeout: any;
}

@Injectable({
  providedIn: 'root',
})
export class RequestService {
  private i18nCommonNamespace = `${AGENT_CORE}.common`;
  private sessionKey = 'PROMPT_ENGINEERING_ME';
  private spaceOptionsSessionKey = 'CUR_SPACE_OPTIONS';

  constructor(
    private httpClient: HttpClient,
    private i18nPipe: I18NextEagerPipe,
    private router: Router,
    private message: NzMessageService,
  ) {}

  /**
   * Get 请求
   * @param config 参数配置
   * @param messageConfig
   * @returns
   */
  get(config: HttpConfig, messageConfig?: MessageConfig): Observable<any> {
    removePropertyWhen(config.query ?? config.params, {
      valueList: [undefined, ''],
    });
    return this.request(MethodType.GET, config, messageConfig);
  }

  /**
   * POST 请求
   * @param config 参数配置
   * @param messageConfig
   */
  post(config: HttpConfig, messageConfig?: MessageConfig): Observable<any> {
    return this.request(MethodType.POST, config, messageConfig);
  }

  /**
   * DELETE 请求
   * @param config 参数配置
   * @param messageConfig
   */
  delete(config: HttpConfig, messageConfig?: MessageConfig): Observable<any> {
    return this.request(MethodType.DELETE, config, messageConfig);
  }

  /**
   * PUT 请求
   * @param config 参数配置
   * @param messageConfig
   */
  put(config: HttpConfig, messageConfig?: MessageConfig): Observable<any> {
    return this.request(MethodType.PUT, config, messageConfig);
  }

  /**
   * patch 请求
   * @param config 参数配置
   * @param messageConfig
   */
  patch(config: HttpConfig, messageConfig?: MessageConfig): Observable<any> {
    return this.request(MethodType.PATCH, config, messageConfig);
  }

  /**
   * 请求统一处理
   * @param methodType 请求类型
   * @param config
   * @param msgConf
   */
  public request(methodType: MethodType, config: HttpConfig, msgConf: MessageConfig = { showFailMessage: true }): Observable<any> {
    const messageConfig = {
      ...config.messageConfig,
      ...msgConf,
    };

    config.url = this.commonParamsReplacer(config.url);

    this.handleParams(config.params ?? {});

    const headers = this.generateRequestHeader(config);

    const url = this.getUrl(methodType, config);

    const options: any = { headers };

    if (config.dataType) {
      options.responseType = config.dataType.toLowerCase();
    }
    if (methodType !== MethodType.GET && (config.body || config.params)) {
      options.body = config.body ?? config.params;
    }

    return this.httpClient.request(methodType.toString(), `${url}`, options).pipe(
      timeout(config.timeout ?? 120000),
      tap(res => {
        if (messageConfig.success) {
          const successDesc = this.getMsgDescription(messageConfig.success, res);
          if (successDesc) {
            this.message.create('success', successDesc);
          }
          return;
        }
        if (messageConfig.inProgress) {
          const inProgressDesc = this.getMsgDescription(messageConfig.inProgress, res);
          if (inProgressDesc) {
            this.message.create('info', inProgressDesc);
          }
        }
      }),
      catchError((errorRes: CustomErrorResponse) => {
        if (messageConfig.customError) {
          throw errorRes;
        }

        if (messageConfig.showFailMessage !== false) {
          this.handleFailRequest(this.getCodeAndMessage(errorRes, config));
        }

        if (messageConfig.thorwWhenFail !== false) {
          throw errorRes;
        }
        return of(null);
      })
    );
  }

  /**
   * 生成请求头
   * @param config
   * @returns
   */
  generateRequestHeader(config: HttpConfig) {
    const headers = {
      ...(config?.headers || {}),
      Accept: 'application/json, text/plain, */*',
      'Content-Type': 'application/json; charset=UTF-8',
      'X-Language': CommonUtils.getLanguage() || '',
    };
    // 文件上传需要去掉 content-type请求头
    if (Object.prototype.toString.call(config.body) === '[object FormData]') {
      Reflect.deleteProperty(headers, 'Content-Type');
    }

    return new HttpHeaders(headers);
  }

  private getMsgDescription(msgConfig: string | Function, data: any) {
    if (typeof msgConfig === 'string') {
      return msgConfig;
    }
    try {
      return msgConfig?.(data);
    } catch (error) {
      return undefined;
    }
  }

  private getCodeAndMessage(errorRes: CustomErrorResponse, config: HttpConfig): ICommonError {
    const error = config.serviceId.startsWith('iam') ? errorRes.error?.error : errorRes.error;

    const code = error?.code ?? error?.error_code ?? errorRes.status?.toString();

    let message = error?.message ?? error?.error_msg ?? errorRes.message ?? error?.error_msg_front;
    const reason = error?.error_reason;
    const suggestion = error?.error_suggestion;

    // 如果错误状态是0 且 错误提示是原始响应的信息，则替换掉
    if (code === '0' && message === errorRes.message) {
      message = this.i18nPipe.transform('common.net.error', {
        ns: this.i18nCommonNamespace,
      });
    }

    try {
      if (typeof message === 'string' && message.trim()) {
        const parsedObj = JSON.parse(message);
        message = parsedObj.error_msg;
      }
    } catch (e) {}

    return {
      error_code: code,
      error_msg: message,
      error_reason: reason,
      error_suggestion: suggestion,
    };
  }

  private handleFailRequest(error: ICommonError) {
    this.message.create('error', buildErrorMsgStr(error));
  }

  /**
   * 处理参数
   * @param params
   */
  private handleParams(params: any) {
    Object.keys(params).forEach((key) => {
      if (typeof params[key] === 'string') {
        params[key] = this.commonParamsReplacer(params[key]);
      }

      if (Array.isArray(params[key])) {
        params[key].forEach((p) => {
          if (!isObject(p)) {
            return;
          }
          this.handleParams(p);
        });
      }

      if (isPlainObject(params[key])) {
        this.handleParams(params[key]);
      }
    });
  }

  private commonParamsReplacer(str: string) {
    return str.replaceAll('{projectId}', this.getProjectId()).replaceAll('{workspaceId}', this.getWorkspaceId());
  }

  private blobToJson(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsText(blob, 'utf-8');
      reader.onload = () => {
        try {
          const json = JSON.parse(reader.result as string);
          resolve(json);
        } catch (e) {
          reject(e);
        }
      };
    });
  }

  private getUrl(type: MethodType, config: HttpConfig) {
    let { url } = config;
    const querySearchParams = convertObj2SearchString(config.query);
    if (type === MethodType.GET && (config.params || config.query)) {
      const query = config.query ? querySearchParams : convertObj2SearchString(config.params);
      url += (url.indexOf('?') === -1 ? '?' : '&') + query;
    } else if (config.query) {
      url += (url.indexOf('?') === -1 ? '?' : '&') + querySearchParams;
    }
    return url;
  }

  public getProjectId(): string {
    let projectId = '';
    let userInfo = StorageService.getLocalStorage('PROMPT_ENGINEERING_ME');
    try {
      projectId = JSON.parse(userInfo)?.projectId;
    } finally {
      return projectId || '0';
    }
  }

  public getWorkspaceId(): string {
    let workspaceId = '';
    try {
      // ab场景  请放第一顺位
      if (
        window.location.href &&
        window.location.href.indexOf('from=agentBuilder') !== -1 &&
        window.location.href.indexOf('work_space_id=') !== -1
      ) {
        // 兼容agentBuilder场景
        const match = window.location.href.match(/work_space_id=([^&]*)/);
        return match ? match[1] : '';
      }

      // 如果URL上有先从URL上去，如果没有则去内存上拿
      const match = window.location.href.match(/workspace_id=([^&]*)/);
      if (match) {
        return match[1];
      }

      let userInfo = StorageService.getSessionStorage(this.sessionKey);

      if (environment.envType === 'poc' || environment.envType === 'site') {
        userInfo = StorageService.getLocalStorage(this.sessionKey);
      }
      if (userInfo?.workspaceId) {
        workspaceId = userInfo.workspaceId;
      }
      const cur_space_options_str = StorageService.getSessionStorage(this.spaceOptionsSessionKey);
      if (cur_space_options_str) {
        const cur_space_options = JSON.parse(StorageService.getSessionStorage(this.spaceOptionsSessionKey));
        // 判断是不是同一个用户
        const meData = StorageService.getLocalStorage(this.sessionKey);
        if (meData && cur_space_options && meData.userId && cur_space_options._userId_) {
          if (meData.userId !== cur_space_options._userId_) {
            StorageService.setSessionStorage(this.spaceOptionsSessionKey, '{}');
            this.confirmFn();
            return '';
          }
        }

        return cur_space_options?.id ? cur_space_options.id : workspaceId || '';
      }
    } catch (err) {
      this.confirmFn();
    }
    return workspaceId;
  }

  private confirmFn() {
    if (this.isInIframe() && environment.envType === 'hc') {
      this.router.navigate(['/home/develop-space']);
    } else {
      this.router.navigate(['/home/overview']);
    }
  }

  private isInIframe() {
    try {
      return window.self !== window.top;
    } catch (e) {
      // 如果出现跨域错误，说明确实被 iframe 嵌套了
      return true;
    }
  }
}

/**
 * 移除符合条件的属性
 * @param obj
 * @param condition
 * @returns
 */
function removePropertyWhen(obj: Object, condition: ((key: string, value: unknown) => boolean) | { keyList?: string[]; valueList?: unknown[] }): void {
  if (!isPlainObject(obj)) {
    return;
  }

  let func: (key: string, value: any) => boolean;

  if (isFunction(condition)) {
    func = condition;
  } else {
    func = (key: string, value: unknown) => Boolean(condition.keyList?.includes(key) || condition.valueList?.includes(value));
  }

  Object.entries(obj).forEach(([k, v]) => {
    if (func(k, v)) {
      Reflect.deleteProperty(obj, k);
    }
  });
}
