/* eslint-disable eslint-comments/disable-enable-pair */
/* eslint-disable @typescript-eslint/no-unsafe-return */
import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MessageComponent, StorageService, HttpConfig } from '@shared/services/cfdata.service';
import { PE_SESSION_KEY, POC_JS_SESSION_KEY } from '@constants/exp-tmpl-config.const';
import { I18nNamespace } from '@i18n';
import { blockedErrorUrls } from '@shared/config/ConfigUrl';
import * as I18next from 'angular-i18next';
import i18next from 'i18next';
import { BehaviorSubject, Observable } from 'rxjs';
import { buildErrorMsgStr, ICommonError } from 'src/utils/utils';
import { environment } from '../environment/environment';
import { HttpClient, HttpParams, HttpErrorResponse, HttpHeaders } from '@angular/common/http';
import { catchError, throwError, map } from 'rxjs';
import { CommonUtils } from "../utils/common.util";

interface IHttpConfig extends HttpConfig {
  /** 是否覆写 url */
  overrideUrl?: boolean;
  /** 跳过 handleError 里的全局错误 toast，由调用方自行 catch 处理（避免错误提示污染其他页面） */
  cancelGlobalError?: boolean;
}

enum mapKeys {
  WORKSPACE_ID = 'workspace_id',
  _USER_ID_ = '_userId_',
}

@Injectable({
  providedIn: 'root',
})
export class HttpService {
  public proxyHttp = null;

  private pocServicePrefix = new BehaviorSubject<string>('');
  private PROMPT_ENGINEERING_ME: string = 'PROMPT_ENGINEERING_ME';
  private setPermission$ = new BehaviorSubject<any>('');
  private setCurrentUserResourceStatus$ = new BehaviorSubject<any>(false);
  private setResourceWhiteListStatus$ = new BehaviorSubject<any>(true);
  private setServiceStatementAgreement$ = new BehaviorSubject<any>(false);
  private setFristCreateError$ = new BehaviorSubject<any>(false);

  constructor(
    private httpClient:HttpClient,
    private activatedRoute: ActivatedRoute,
    private i18n: I18next.I18NextEagerPipe,
    private router: Router,
  ) {
    this.activatedRoute.queryParams.subscribe(params => {
      this.proxyHttp = params.proxy;
    });
  }

  public getCurrentUserResourceStatus(): Observable<any> {
    return this.setCurrentUserResourceStatus$.asObservable();
  }

  public getResourceWhiteList(): Observable<any> {
    return this.setResourceWhiteListStatus$.asObservable();
  }


  public getServiceStatementAgreement(): Observable<any> {
    return this.setServiceStatementAgreement$.asObservable();
  }

  public getFristCreateError(): Observable<any> {
    return this.setFristCreateError$.asObservable();
  }

  getPocServicePrefix() {
    return this.pocServicePrefix.getValue();
  }

  setPocServicePrefix(value: string) {
    this.pocServicePrefix.next(value);
  }

  /** 权限有问题的话 */
  public setPermissionError(body: any): void {
    this.setPermission$.next(body);
  }

  public getPermissionError(): Observable<any> {
    return this.setPermission$.asObservable();
  }

  private handleError(error: HttpErrorResponse, httpConfig?: IHttpConfig): Observable<any> {
    // 处理接口application/json返回text
    if (error.status === 200 && error.error?.text) {
      return new Observable(observer => {
        observer.next(error.error.text as any);
        observer.complete();
      });
    }
    if (error.error?.error_code) {
      if (['Openjiuwen.02001084'].includes(error.error?.error_code)) {
        const params = {
          error_msg: error.error?.error_msg,
          error_code: error.error?.error_code,
        };
        this.setPermissionError(params);
        return throwError(() => error);
      }
    }
    if (error.status === 401 && error.error && error.error.redirectUrl) {
      window.location.href = error.error.redirectUrl;
      return throwError(() => error);
    }

    const defaultMsg = this.i18n.transform('MAStudio.00410400', {
      ns: I18nNamespace.ERROR,
    });

    if (error.error?.error_code) {
      if (['Openjiuwen.02001064', 'Openjiuwen.02001022', 'Openjiuwen.02501052', 'Openjiuwen.03002017'].includes(error.error?.error_code)) {
        StorageService.setSessionStorage('error_code', error.error?.error_code);
        const params = {
          error_msg: error.error?.error_msg,
          error_code: error.error?.error_code,
        };
        return throwError(() => error);
      }

      if (['common.01010003'].includes(error.error?.error_code)) {
        return throwError(() => error);
      }

      error.error.error_msg_front = this.i18n.transform(error.error.error_code as string, {
        ns: I18nNamespace.ERROR,
        defaultValue: defaultMsg,
      });
    }

    let cancelInterfaceErrorFlag = error.url?.indexOf('cancelInterfaceErrorTip') > -1;
    if (blockedErrorUrls.some(i => error.url?.includes(i)) || cancelInterfaceErrorFlag || httpConfig?.cancelGlobalError) {
      return throwError(() => error);
    }
    const errorInstance: ICommonError = error.error as ICommonError;
    const errMsg = buildErrorMsgStr(errorInstance);
    if (errMsg) {
      MessageComponent.showError(errMsg);
    }
    return throwError(() => error);
  }

  get defaultConfig(): Partial<HttpConfig> {
    return {
      timeout: 900_000,
    };
  }

  get prefixPath(): Readonly<string> {
    const {prefixPath, envType} = environment;
    if (prefixPath) {
      const pocServType = this.getPocServicePrefix();
      if (pocServType) {
        return `${prefixPath}/${pocServType}`;
      }
      return prefixPath;
    }
    return `${window.AppWebPath}rest`;
  }

  public postBlobAsync(httpConfig: IHttpConfig): Promise<Blob> {
    return new Promise((resolve, reject) => {
      this.postBlob(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public getBlobAsync(httpConfig: IHttpConfig): Promise<Blob> {
    return new Promise((resolve, reject) => {
      this.getBlob(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public getAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return new Promise((resolve, reject) => {
      this.get<T>(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public postAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return new Promise((resolve, reject) => {
      this.post<T>(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public putAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return new Promise((resolve, reject) => {
      this.put<T>(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public deleteAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return new Promise((resolve, reject) => {
      this.delete<T>(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public patchAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return new Promise((resolve, reject) => {
      this.patch<T>(httpConfig).subscribe({
        next: (data) => resolve(data),
        error: (err) => reject(err),
      });
    });
  }

  public fetchAsync<T>(httpConfig: IHttpConfig): Promise<T> {
    return this.getAsync<T>(httpConfig);
  }

  public getBlob(httpConfig: IHttpConfig): Observable<Blob> {
    const config = this.mergeConfig(httpConfig);
    let params = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        params = params.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    return this.httpClient.get(config.url as string, { params, headers: headers, responseType: 'blob' }).pipe() as Observable<Blob>;
  }

  public get<T>(httpConfig: IHttpConfig): Observable<T> {
    const config = this.mergeConfig(httpConfig);
    let params = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        params = params.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    return this.httpClient.get<T>(config.url as string, {params, headers}).pipe(
      catchError((err) => this.handleError(err, httpConfig))
    ) as Observable<T>;
  }

  public post<T>(httpConfig: IHttpConfig): Observable<T> {
    const config = this.mergeConfig(httpConfig);
    let queryParams = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        queryParams = queryParams.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    const body = config.body ?? config.params;
    return this.httpClient.post<T>(config.url as string, body, {params: queryParams, headers}).pipe(
      catchError((err) => this.handleError(err, httpConfig))
    ) as Observable<T>;
  }

  public postBlob(httpConfig: IHttpConfig): Observable<Blob> {
    const config = this.mergeConfig(httpConfig);
    let queryParams = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        queryParams = queryParams.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    const body = config.body ?? config.params;
    return this.httpClient.post(config.url as string, body, { params: queryParams, headers: headers, responseType: 'blob' }).pipe() as Observable<Blob>;
  }

  public put<T>(httpConfig: IHttpConfig): Observable<T> {
    const config = this.mergeConfig(httpConfig);
    let queryParams = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        queryParams = queryParams.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    const body = config.body ?? config.params;
    return this.httpClient.put<T>(config.url as string, body, {params: queryParams, headers}).pipe(
      catchError((err) => this.handleError(err, httpConfig))
    ) as Observable<T>;
  }

  public delete<T>(httpConfig: IHttpConfig): Observable<T> {
    const config = this.mergeConfig(httpConfig);
    let params = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        params = params.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    const body = config.body ?? config.params;
    return this.httpClient.delete<T>(config.url as string, {params, headers, body}).pipe(
      catchError((err) => this.handleError(err, httpConfig))
    ) as Observable<T>;
  }

  public patch<T>(httpConfig: IHttpConfig): Observable<T> {
    const config = this.mergeConfig(httpConfig);
    let queryParams = new HttpParams();
    if (config.query) {
      Object.keys(config.query).forEach(key => {
        queryParams = queryParams.set(key, config.query[key as keyof typeof config.query] as string);
      });
    }
    const headers = this.buildHeaders();
    const body = config.body ?? config.params;
    return this.httpClient.patch<T>(config.url as string, body, {params: queryParams, headers}).pipe(
      catchError((err) => this.handleError(err, httpConfig))
    ) as Observable<T>;
  }

  private buildHeaders(): HttpHeaders {
    let headers = new HttpHeaders();
    headers = headers.set('X-Language', CommonUtils.getLanguage());
    return headers;
  }

  public fetch<T>(httpConfig: IHttpConfig): Observable<T> {
    if (httpConfig.method === 'POST') {
      if (httpConfig.dataType === 'blob') {
        const config = this.mergeConfig(httpConfig);
        let queryParams = new HttpParams();
        if (config.query) {
          Object.keys(config.query).forEach(key => {
            queryParams = queryParams.set(key, config.query[key as keyof typeof config.query] as string);
          });
        }
        const headers = this.buildHeaders();
        const body = config.body ?? config.params;
        return this.httpClient.post(config.url as string, body, {
          params: queryParams,
          headers: headers,
          responseType: 'blob',
          observe: 'response'
        }).pipe(
          map((res: any) => ({ data: res.body, headers: res.headers }))
        ) as Observable<T>;
      }
      return this.post<T>(httpConfig);
    }
    if (httpConfig.dataType === 'blob') {
      return this.getBlob(httpConfig) as Observable<T>;
    }
    return this.get<T>(httpConfig);
  }

  public fetchAsyncDefaultWorkspaceId<T>(httpConfig: IHttpConfig): Promise<T> {
    return this.getAsync<T>(this.mergeConfigDefaultWorkspaceId(httpConfig));
  }

  public fetchDefaultWorkspaceId<T>(httpConfig: IHttpConfig): Observable<T> {
    return this.get<T>(this.mergeConfigDefaultWorkspaceId(httpConfig));
  }

  private mergeConfig(httpConfigExt: IHttpConfig): HttpConfig {
    const {overrideUrl, ...httpConfig} = httpConfigExt;

    if (overrideUrl) {
      return {...this.defaultConfig, ...httpConfig};
    }

    httpConfig.url = `${this.prefixPath}${httpConfig.url}`;

    let workspaceId = this.getWorkspaceId();

    if (!httpConfig.query) {
      httpConfig.query = {
        'workspace_id': workspaceId,
      };
    } else {
      httpConfig.query[mapKeys.WORKSPACE_ID] = httpConfig.query[mapKeys.WORKSPACE_ID] || workspaceId;
    }

    return {...this.defaultConfig, ...httpConfig};
  }

  private mergeConfigDefaultWorkspaceId(httpConfigExt: IHttpConfig): HttpConfig {
    const {overrideUrl, ...httpConfig} = httpConfigExt;

    if (overrideUrl) {
      return {...this.defaultConfig, ...httpConfig};
    }

    httpConfig.url = `${this.prefixPath}${httpConfig.url}`;

    return {...this.defaultConfig, ...httpConfig};
  }

  public getWorkspaceId(): string {
    let workspaceId = '';
    try {
      if (window.location.href && window.location.href.indexOf('from=agentBuilder') !== -1 && window.location.href.indexOf('work_space_id=') !== -1) {
        const match = window.location.href.match(/work_space_id=([^&]*)/);
        return match ? match[1] : '';
      }

      const match = window.location.href.match(/workspace_id=([^&]*)/);
      if (match) {
        return match[1];
      }

      let userInfo = StorageService.getLocalStorage(PE_SESSION_KEY);

      if (userInfo?.workspaceId) {
        workspaceId = userInfo.workspaceId;
      }
      const cur_space_options_str = StorageService.getSessionStorage('CUR_SPACE_OPTIONS');
      if (cur_space_options_str) {
        const cur_space_options = JSON.parse(StorageService.getSessionStorage('CUR_SPACE_OPTIONS'));
        const meData = StorageService.getLocalStorage(this.PROMPT_ENGINEERING_ME);
        if (meData && cur_space_options && meData.userId && cur_space_options[mapKeys._USER_ID_]) {
          if (meData.userId !== cur_space_options[mapKeys._USER_ID_]) {
            StorageService.setSessionStorage('CUR_SPACE_OPTIONS', '{}');
            this.confirmFn();
            return '';
          }
        }

        return cur_space_options?.id ? cur_space_options.id : workspaceId || '';
      }
    } catch {
      this.confirmFn();
    }
    return workspaceId;
  }

  public confirmFn() {
    this.router.navigate(['/home/overview']);
  }

  public parseBlobError(blob: Blob): Observable<never> {
    return new Observable(observer => {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const error = JSON.parse(reader.result as string);
          observer.error(error);
        } catch {
          observer.error(i18next.t('httpservice_7'));
        }
      };
      reader.readAsText(blob);
    });
  }
}
