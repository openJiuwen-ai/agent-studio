import { Injectable } from '@angular/core';
import { NzMessageService } from 'ng-zorro-antd/message';
export interface HttpConfig {
  url: string | {
    s: string;
    o?: object;
  };
  headers?: {
    [propName: string]: string;
  };
  timeout?: number;
  targetUrl?: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH' | 'HEAD' | 'OPTIONS' | 'TRACE' | 'CONNECT';
  body?: BodyInit | null;
  query?: object;
  params?: object;
  dataType?: 'json' | 'text' | 'blob' | 'arrayBuffer' | 'formData';
  keepalive?: boolean;
  cache?: RequestCache;
  credentials?: RequestCredentials;
  mode?: RequestMode;
  redirect?: RequestRedirect;
  referrer?: string;
  isShow403?: boolean;
  abortController?: AbortController;
  signal?: AbortSignal;
  targetService?: string;
  requestFromFramework?: boolean;
  dynamicIndex?: boolean;
}

let messageServiceInstance: NzMessageService;

export function initMessageService(nzMessageService: NzMessageService): void {
  messageServiceInstance = nzMessageService;
}

@Injectable({
  providedIn: 'root',
})
export class MaskComponent {
  static maskCount = 0;
  private static background: HTMLDivElement = document.createElement('div');
  private static loading: HTMLDivElement = document.createElement('div');

  static show(): void {
    if (++this.maskCount === 1) {
      this.background.className = 'cf-mask-cover-background';
      document.body.appendChild(this.background);
      this.loading.className = 'cf-mask-loading';
      document.body.appendChild(this.loading);
    }
  }

  static hide(): void {
    if (this.maskCount > 0) {
      this.maskCount--;
    }
    if (this.maskCount === 0) {
      const pBackground = this.background?.parentNode;
      if (pBackground) {
        pBackground.removeChild(this.background);
      }
      const pLoading = this.loading?.parentNode;
      if (pLoading) {
        pLoading.removeChild(this.loading);
      }
    }
  }
}

@Injectable({
  providedIn: 'root',
})
export class MessageComponent {
  static showError(message: string, duration = 3000): void {
    messageServiceInstance?.error(message, { nzDuration: duration });
  }

  static showSuccess(message: string, duration = 3000): void {
    messageServiceInstance?.success(message, { nzDuration: duration });
  }

  static showPrompt(message: string, duration = 3000): void {
    messageServiceInstance?.info(message, { nzDuration: duration });
  }

  static showWarn(message: string, duration = 3000): void {
    messageServiceInstance?.warning(message, { nzDuration: duration });
  }

  static storageMsg(type: string, msg: string, duration = 3000): void {
    messageServiceInstance?.[type](msg, { nzDuration: duration });
  }

  static alertMsg(type: string, message: string, duration = 3000): void {
    messageServiceInstance?.[type](message, { nzDuration: duration });
  }
}

@Injectable({
  providedIn: 'root',
})
export class StorageService {
  static cookieStorage: any;
  static specialKeys: string[] = [];

  constructor() {}

  static setCookie(key: string, value: any, expires?: number, domain?: string): void {
    let cookieStr = `${encodeURIComponent(key)}=${encodeURIComponent(value)}`;
    if (expires !== undefined) {
      const expiresDate = new Date(Date.now() + expires * 1000);
      cookieStr += `; expires=${expiresDate.toUTCString()}`;
    }
    if (domain) {
      cookieStr += `; domain=${domain}`;
    }
    cookieStr += '; path=/';
    document.cookie = cookieStr;
  }

  static getCookie(key: string): any {
    const name = encodeURIComponent(key) + '=';
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.indexOf(name) === 0) {
        return decodeURIComponent(trimmed.substring(name.length));
      }
    }
    return null;
  }

  static delCookie(key: string): void {
    this.setCookie(key, '', -1);
  }

  static flushCookie(): void {
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
      const name = cookie.split('=')[0].trim();
      this.delCookie(decodeURIComponent(name));
    }
  }

  static getLocalStorage(key: string, isErr?: boolean, cacheVersion?: string): any {
    try {
      const value = localStorage.getItem(key);
      if (value === null) return null;
      return value;
    } catch {
      return null;
    }
  }

  static JsonParse(value: string): any {
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }

  static endsWith(str: string, suffix: string): boolean {
    return str.endsWith(suffix);
  }

  static clearExpiredStorage(): void {
    const keys = Object.keys(localStorage);
    const now = Date.now();
    for (const key of keys) {
      try {
        const item = localStorage.getItem(key);
        if (item) {
          const parsed = JSON.parse(item);
          if (parsed && parsed.__expire && parsed.__expire < now) {
            localStorage.removeItem(key);
          }
        }
      } catch {}
    }
  }

  static setLocalStorage(key: string, value: any, expires?: number, cacheVersion?: string): any {
    try {
      if (expires !== undefined) {
        const item = {
          value,
          __expire: Date.now() + expires * 1000,
        };
        localStorage.setItem(key, JSON.stringify(item));
      } else {
        localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
      }
      return true;
    } catch {
      return false;
    }
  }

  static delLocalStorage(name: string): boolean {
    try {
      localStorage.removeItem(name);
      return true;
    } catch {
      return false;
    }
  }

  static getSessionStorage(key: string): any {
    try {
      return sessionStorage.getItem(key);
    } catch {
      return null;
    }
  }

  static setSessionStorage(key: string, value: any): boolean {
    try {
      sessionStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
      return true;
    } catch {
      return false;
    }
  }

  static delSessionStorage(name: string): boolean {
    try {
      sessionStorage.removeItem(name);
      return true;
    } catch {
      return false;
    }
  }
}

@Injectable({
  providedIn: 'root',
})
export class UtilService {
  static getTypeOfData(data: any): string {
    const res = Object.prototype.toString.call(data);
    return res.substr(0, res.length - 1).split(' ')[1];
  }

  static convertObj2SearchString(params: Record<string, any> = {}): string {
    const result: string[] = [];
    const keys = Object.keys(params);
    keys.forEach(key => {
      const type = UtilService.getTypeOfData(params[key]);
      if (type === 'Array') {
        params[key].forEach((value: any) => {
          const valueType = UtilService.getTypeOfData(value);
          const encodedValue = ['Number', 'String', 'Boolean'].includes(valueType) ? encodeURIComponent(value) : '';
          result.push(`${encodeURIComponent(key)}=${encodedValue}`);
        });
      } else {
        const value = ['Number', 'String', 'Boolean'].includes(type) ? params[key] : '';
        result.push(`${encodeURIComponent(key)}=${encodeURIComponent(value)}`);
      }
    });
    return result.join('&');
  }
}
