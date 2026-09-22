/**
 * file 类型参数 URL 录入的校验与工具函数（特性：开始节点支持URL方式）。
 *
 * URL 模式仅对 file/image、file/video（含 array 形态）开放；
 * 校验规则：协议头 ∈ {http:, https:, data:}，扩展名白名单复用上传口径
 * （pipes/upload-file.pipe.ts 的 fileUploadAcc，单一来源不复制）。
 * 校验仅在前端录入时阻断，不做连通性/大小/内容探测。
 */

import { v4 as uuidV4 } from 'uuid';
import { fileUploadAcc } from 'src/pipes/upload-file.pipe';
import type { FileItem } from './multiUpload.utils';

/** data: URI mediatype → 扩展名映射（对齐 fileUploadAcc 白名单口径） */
const DATA_MEDIA_TYPE_MAP: Record<string, string> = {
  'image/png': 'png',
  'image/jpeg': 'jpg',
  'image/gif': 'gif',
  'image/webp': 'webp',
  'image/svg+xml': 'svg',
  'video/mp4': 'mp4',
  'video/x-msvideo': 'avi',
  'video/x-ms-wmv': 'wmv',
  'video/x-flv': 'flv',
  'video/x-f4v': 'f4v',
  'video/3gpp': '3gp',
  'video/x-matroska': 'mkv',
  'application/vnd.rn-realmedia': 'rmvb',
};

/** 是否为支持 URL 录入的 file 类型（image/video 子类型，含 array 形态） */
export function isSupportedUrlType(type: string): boolean {
  return /file\/(image|video)/.test(type || '');
}

/** URL 校验错误类型（对应 agent-center i18n key） */
export type FileUrlCheckError =
  | 'url_invalid_format'
  | 'url_invalid_protocol'
  | 'url_invalid_extension';

/** 校验单条 URL：协议头 + 扩展名白名单；合法返回 null */
export function checkFileUrl(
  url: string,
  type: string,
): FileUrlCheckError | null {
  const trimmed = (url || '').trim();
  if (!trimmed) {
    return 'url_invalid_format';
  }

  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    return 'url_invalid_format';
  }

  if (parsed.protocol === 'data:') {
    const extension = getDataUriExtension(trimmed);
    if (!extension || !isExtensionAllowed(extension, type)) {
      return 'url_invalid_extension';
    }
    return null;
  }

  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return 'url_invalid_protocol';
  }

  const extension = getUrlExtension(parsed);
  if (!extension || !isExtensionAllowed(extension, type)) {
    return 'url_invalid_extension';
  }
  return null;
}

/** 从 URL pathname 取末段扩展名（剥离 query；decode 失败回退原文） */
export function getUrlExtension(parsed: URL): string | null {
  const lastSegment =
    decodePath(parsed.pathname || '').split('/').pop() || '';
  const dotIndex = lastSegment.lastIndexOf('.');
  // dotIndex <= 0：无扩展名或以 . 开头的隐藏文件名，均视为无扩展名
  if (dotIndex <= 0 || dotIndex === lastSegment.length - 1) {
    return null;
  }
  return lastSegment.slice(dotIndex + 1).toLowerCase();
}

/** 从 data: URI 提取 mediatype 对应的白名单扩展名 */
export function getDataUriExtension(url: string): string | null {
  const matched = /^data:([^;,]+)/i.exec((url || '').trim());
  if (!matched) {
    return null;
  }
  return DATA_MEDIA_TYPE_MAP[matched[1].toLowerCase()] ?? null;
}

/** 扩展名是否在指定 file 类型的上传白名单内 */
export function isExtensionAllowed(extension: string, type: string): boolean {
  const whitelist = (fileUploadAcc[type] || '')
    .split(',')
    .map((item) => item.trim().toLowerCase().replace(/^\./, ''))
    .filter(Boolean);
  return whitelist.includes((extension || '').trim().toLowerCase());
}

/** URL 显示名：path 末段（去 query）；data: URI 以 mediatype 合成 */
export function getUrlDisplayName(url: string): string {
  const trimmed = (url || '').trim();
  if (trimmed.startsWith('data:')) {
    const extension = getDataUriExtension(trimmed) || 'bin';
    return `data.${extension}`;
  }
  try {
    const parsed = new URL(trimmed);
    const lastSegment =
      decodePath(parsed.pathname || '').split('/').pop() || '';
    if (lastSegment) {
      return lastSegment;
    }
  } catch {
    // 非法 URL 由 checkFileUrl 拦截，这里仅尽力取名
  }
  return 'unknown';
}

/** 多行文本拆分为 URL 列表（trim + 剔除空行） */
export function splitUrlText(text: string): string[] {
  return (text || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

/** 构造与上传产物同构的 URL 条目（progress 恒为 succeeded，供宿主列表复用） */
export function createUrlFileItem(url: string): FileItem {
  return {
    fileId: uuidV4(),
    name: getUrlDisplayName(url),
    progress: 'succeeded',
    type: '',
    url,
    controller: new AbortController(),
    fromUrl: true,
  };
}

/** 条目列表中是否存在本地上传来源的条目（URL 条目带 fromUrl: true 标记） */
export function hasLocalFileItems(
  items?: Array<{ fromUrl?: boolean }>,
): boolean {
  return (items || []).some((item) => item?.fromUrl !== true);
}

/** 条目列表中是否存在 URL 录入来源的条目 */
export function hasUrlFileItems(
  items?: Array<{ fromUrl?: boolean }>,
): boolean {
  return (items || []).some((item) => item?.fromUrl === true);
}

function decodePath(path: string): string {
  try {
    return decodeURIComponent(path);
  } catch {
    return path;
  }
}
