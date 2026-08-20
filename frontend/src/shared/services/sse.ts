import CommonLogic from '@routes/agent-center/app-flow/common-logic-workflow';
import { buildErrorMsgStr, ICommonError } from 'src/utils/utils';
import {MessageComponent, StorageService} from '@shared/services/cfdata.service';

type SSEventTarget = {
  response?: any;
};

export interface ISSEvent extends CustomEvent {
  source?: any;
  readyState?: number;
  data?: any;
  id?: string | number;
}

export class SSE {
  readonly CONNECTING = 0;

  readonly INITIALIZING = -1;

  readonly FIELD_SEPARATOR = ':';

  readonly OPEN = 1;

  readonly CLOSED = 2;

  private url: string;

  private headers: Record<string, string>;

  private payload: XMLHttpRequestBodyInit;

  private method: 'POST' | 'GET';

  private withCredentials: boolean;

  private withCsrf: boolean;

  private listeners: Record<string, EventListener[]>;

  private xhr: XMLHttpRequest;

  private readyState: number;

  private progress: number;

  private chunk: string;

  /** 接口超时参数 */
  private timeout: number;

  /** 流式回答超时参数 */
  private streamTimeout: number;

  /** 首次回答超时时间 */
  private streamFirstChunkTimeout: number;

  private timer: number;

  /** user system发送的当前时间 */
  private requestStartTime: Date | null = null;

  /** 是否已接收第一个message event，而非第一个start event */
  private firstTokenReceived: boolean = false;

  constructor(
    url: string,
    options: {
      headers?: Record<string, string>;
      payload?: XMLHttpRequestBodyInit;
      method?: 'POST' | 'GET';
      withCsrf?: boolean;
      timeout?: number;
      streamTimeout?: number;
      streamFirstChunkTimeout?: number;
    },
  ) {
    this.timeout = options.timeout || 60_000;
    this.streamTimeout = options.streamTimeout || 60_000;
    this.streamFirstChunkTimeout = options.streamFirstChunkTimeout ?? 30_000;
    this.url = url;

    this.headers = options.headers || {};
    this.payload = options.payload === undefined ? '' : options.payload;
    this.method = options.method || (this.payload && 'POST') || 'GET';
    this.withCredentials = false;
    this.withCsrf = options.withCsrf;
    this.listeners = {};

    this.xhr = null;
    this.readyState = this.INITIALIZING;
    this.progress = 0;
    this.chunk = '';
  }

  addEventListener(type: string | number, listener: EventListener) {
    if (this.listeners[type] === undefined) {
      this.listeners[type] = [];
    }

    if (!this.listeners[type].includes(listener)) {
      this.listeners[type].push(listener);
    }
  }

  removeEventListener(type: string | number, listener: EventListener) {
    if (this.listeners[type] === undefined) {
      return;
    }

    const filterArr: EventListener[] = [];
    this.listeners[type].forEach((item: EventListener) => {
      if (item !== listener) {
        filterArr.push(item);
      }
    });
    if (filterArr.length === 0) {
      delete this.listeners[type];
    } else {
      this.listeners[type] = filterArr;
    }
  }

  dispatchEvent = (e: ISSEvent) => {
    if (!e) {
      return true;
    }

    if (['error', 'done', 'timeout', 'abort'].includes(e.type)) {
      this.clearTimer();
    }

    e.source = this;

    const onHandler = `on${e.type}`;
    if (Object.prototype.hasOwnProperty.call(this, onHandler)) {
      this[onHandler].call(this, e);
      if (e.defaultPrevented) {
        return false;
      }
    }
    // 统一拦截错误
    if(e.type==='error'){
      if (e.data && typeof e.data === 'string') {
        try{
          const errorInstance:ICommonError=JSON.parse(e.data) as ICommonError;
          const errMsg = buildErrorMsgStr(errorInstance);
          if  (errMsg){
            MessageComponent.showError(errMsg);
          }
        }catch (error){
          // 报错说明不是后端统一响应格式，可能没有进到后端
          // do nth
        }
      }

    }
    if (this.listeners[e.type]) {
      return this.listeners[e.type].every((callback: EventListener) => {
        callback(e);
        return !e.defaultPrevented;
      });
    }

    return true;
  };

  close() {
    if (this.readyState === this.CLOSED) {
      return;
    }

    this.xhr.abort();
    this.xhr = null;
    this.setReadyStatus(this.CLOSED);
  }

  stream = () => {
    this.setReadyStatus(this.CONNECTING);

    this.xhr = new XMLHttpRequest();
    this.xhr.timeout = this.timeout;

    this.xhr.addEventListener('progress', this.onStreamProgress.bind(this));
    this.xhr.addEventListener('load', this.onStreamLoaded.bind(this));
    this.xhr.addEventListener(
      'readystatechange',
      this.checkStreamClosed.bind(this),
    );
    this.xhr.addEventListener('error', this.onStreamFail.bind(this));

    this.xhr.addEventListener('abort', this.onStreamAbort.bind(this));
    this.xhr.addEventListener('timeout', () => {
      this.dispatchEvent(new CustomEvent('timeout'));
    });

    this.xhr.open(this.method, this.url);

    Object.keys(this.headers).forEach((header) => {
      if (Object.prototype.hasOwnProperty.call(this.headers, header)) {
        this.xhr.setRequestHeader(header, this.headers[header]);
      }
    });

    if (this.withCsrf) {
      this.xhr.setRequestHeader('cftk', StorageService.getCookie('cftk') ?? '');
      this.xhr.setRequestHeader('cf2-cftk', StorageService.getCookie('cftk') ?? '');
    }
    this.xhr.withCredentials = this.withCredentials;
    this.xhr.send(this.payload);

    // query发送的当前时间
    this.requestStartTime = new Date();
    this.firstTokenReceived = false;

    // 附带一个定时器处理成功状态的流式接口返回超时问题
    this.addTimer(this.streamFirstChunkTimeout);
  };

  private setReadyStatus(state: number) {
    const event: ISSEvent = new CustomEvent('readystatechange');
    event.readyState = state;
    this.readyState = state;
    this.dispatchEvent(event);
  }

  private onStreamFail(e: Event) {
    const event: ISSEvent = new CustomEvent('error');
    event.data = (e.currentTarget as SSEventTarget).response;
    this.dispatchEvent(event);
    this.close();
  }

  private onStreamAbort() {
    this.dispatchEvent(new CustomEvent('abort'));
    this.close();
  }

  private addTimer(time: any) {
    if (this.timer) {
      this.clearTimer();
    }

    this.timer = window.setTimeout(() => {
      this.dispatchEvent(new CustomEvent('timeout'));
    }, time);
  }

  private clearTimer() {
    clearTimeout(this.timer);
  }

  private onStreamProgress(e: Event) {
    if (!this.xhr) {
      return;
    }

    if (this.xhr.status !== 200) {
      this.onStreamFail(e);
      return;
    }

    if (this.readyState === this.CONNECTING) {
      this.dispatchEvent(new CustomEvent('open'));
      this.setReadyStatus(this.OPEN);
    }

    if (e.type === 'progress') {
      this.addTimer(this.streamTimeout);
    }

    const data = this.xhr.responseText.slice(Math.max(0, this.progress));
    this.progress += data.length;
    data.split(/(\r\n|\r|\n){2}/g).forEach((part) => {
      if (part.trim().length === 0) {
        const eventChunk = this.parseEventChunk(this.chunk.trim());
        this.chunk = '';
        try {
          this.handleFirstToken(eventChunk);
          this.dispatchEvent(eventChunk);
        } catch (err) {
          // 监听器异常不能中断解析循环，否则剩余字节丢失会让后续事件拼接成损坏数据
          console.error('[SSE] event listener error:', err);
        }
      } else {
        this.chunk += part;
      }
    });
  }

  private onStreamLoaded(e: Event) {
    this.onStreamProgress(e);

    const tailChunk = this.parseEventChunk(this.chunk);
    this.chunk = '';
    try {
      this.dispatchEvent(tailChunk);
    } catch (err) {
      console.error('[SSE] event listener error:', err);
    }
  }

  private checkStreamClosed = () => {
    if (!this.xhr) {
      return;
    }

    if (this.xhr.readyState === XMLHttpRequest.DONE) {
      this.setReadyStatus(this.CLOSED);
    }
  };

  protected parseEventChunk(chunk: string): ISSEvent | null {
    if (!chunk || chunk.length === 0) {
      return null;
    }

    const e = { id: null, retry: null, data: '', event: 'message' };
    chunk.split(/\n|\r\n|\r/).forEach((line: string) => {
      line = line.trimEnd();
      const index = line.indexOf(this.FIELD_SEPARATOR);
      if (index <= 0) {
        return;
      }

      const field: string = line.slice(0, Math.max(0, index));
      if (!(field in e)) {
        return;
      }
      const value = line.slice(Math.max(0, index + 1));
      if (field === 'data') {
        e.data += value;
      }
    });

    let event: ISSEvent;
    if (
      e.data === '[DONE]' ||
      this.isDebugRunCompleted(e.data) ||
      e.data === '[Done]'
    ) {
      event = new CustomEvent('done');
    } else {
      event = new CustomEvent('message');
      // message 类型还需要检查是否是流式报错，统一拦截
      try {
        const eventData = JSON.parse(e.data);
        if (Object.hasOwn(eventData, 'event') && eventData?.event === 'error') {
          // 流式响应报错
          const errorInstance: ICommonError = eventData?.data as ICommonError;
          const errMsg = buildErrorMsgStr(errorInstance);
          if (errMsg) {
            MessageComponent.showError(errMsg);
          }
        }
      } catch (e) {
        // json解析失败，非json数据，联系后端排查
      }
    }
    event.data = e.data;
    event.id = e.id;
    return event;
  }

  /** 判断工作流调试接口 或 知识型Agent预览调试接口是否完成。当event字段值等于'end'或'summary_response' */
  private isDebugRunCompleted = (data: string): boolean => {
    const { event } = CommonLogic.stringToObject(data);
    return event === 'end' || event === 'done';
  };

  /** 计算接收到第一个message event的前端时延 */
  private handleFirstToken(eventChunk: ISSEvent) {
    const { event } = CommonLogic.stringToObject(eventChunk?.data) || {};

    if (event && event !== 'start') {
      if (!this.firstTokenReceived) {
        this.firstTokenReceived = true;
        const firstTokenTime = new Date();
        if (this.requestStartTime) {
          const latency =
            firstTokenTime.getTime() - this.requestStartTime.getTime();

          let latencyStr;
          if (latency < 1000) {
            latencyStr = `${latency}ms`;
          } else if (latency < 60_000) {
            latencyStr = `${(latency / 1000).toFixed(2)}s`;
          } else {
            latencyStr = `${(latency / 60_000).toFixed(2)}min`;
          }

          // 通过自定义事件传递首token时延
          this.dispatchEvent(
            new CustomEvent('firstTokenLatency', { detail: latencyStr }),
          );
        }
      }
    }
  }
}
