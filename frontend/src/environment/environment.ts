import { IEnvironment } from './environment.types';

/**
 * DSL 版本对比大 DSL 降级阈值（单侧规范化后文本字节，Monaco 对比计算保护阈值）。
 * 默认 10MB / 上限 100MB 均为压测前暂定值，与 start.sh 中常量同值
 * （TS 常量 Shell 不能直接引用，靠一致性检查 spec 断言两处相等防漂移）。
 */
export const DEFAULT_LARGE_DSL_BYTES_THRESHOLD = 10 * 1024 * 1024;
export const MAX_LARGE_DSL_BYTES_THRESHOLD = 100 * 1024 * 1024;

/**
 * 严格解析：先校验类型与十进制格式（^[1-9][0-9]*$，与 Shell 接受范围一致），
 * 再做数值范围判断。不能先 Number(raw) —— '1e6'/'01'/true/[1024] 会被错误接受。
 */
export function resolveLargeDslBytesThreshold(raw: unknown): number {
  if (typeof raw !== 'string' && typeof raw !== 'number') {
    return DEFAULT_LARGE_DSL_BYTES_THRESHOLD;
  }
  const text = String(raw);
  if (!/^[1-9][0-9]*$/.test(text)) {
    return DEFAULT_LARGE_DSL_BYTES_THRESHOLD;
  }
  const value = Number(text);
  return Number.isSafeInteger(value) && value <= MAX_LARGE_DSL_BYTES_THRESHOLD
    ? value
    : DEFAULT_LARGE_DSL_BYTES_THRESHOLD;
}

export const environment: IEnvironment = {
  prefixPath: window.location.origin,
  jumpObsPath: '/console/#obs',
  envType: 'site',
  serviceType: 'test',
  toolAPIServiceId: '',
  toolAPIName: 'rest-api-test',
  serviceName: 'jiuwen-agent',
  largeDslBytesThreshold: resolveLargeDslBytesThreshold(window.largeDslBytesThreshold),
};
