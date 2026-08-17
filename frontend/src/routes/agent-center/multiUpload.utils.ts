import { v4 as uuidV4 } from 'uuid';
import { AgentConfigService } from './agent-config.service';
import { formatUploadSizeMb } from './utils';

export interface FileItem {
  fileId: string;
  name: string;
  progress: 'loading' | 'succeeded' | 'failed';
  type: string;
  url: string;
  controller: AbortController;
}

export interface FileSizeError {
  key: string;
  params?: { size: number | string };
}

export function validateFileSize(
  file: File,
  isImage: boolean,
  maxImageSizeKb: number = 5 * 1024,
  maxFileSizeKb: number = AgentConfigService.DEFAULT_FILE_MAX_SIZE_KB,
): FileSizeError | null {
  const extension = file.name.split('.').pop()?.toLowerCase() || '';
  const validImageExtensions = ['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'];

  // 检查文件类型是否为图片
  if (isImage && !validImageExtensions.includes(extension)) {
    return { key: 'Invalid image format' };
  }

  // 检查文件大小
  const maxSizeKb = isImage ? maxImageSizeKb : maxFileSizeKb;
  if (file.size > maxSizeKb * 1024) {
    return isImage
      ? { key: 'image_size_cannot_exceed_5mb' }
      : { key: 'file_size_cannot_exceed', params: { size: formatUploadSizeMb(maxFileSizeKb) } };
  }

  return null;
}

export function createFileItem(file: File): FileItem {
  return {
    fileId: uuidV4(),
    name: file.name,
    progress: 'loading',
    type: file.type,
    url: file.name,
    controller: new AbortController(),
  };
}

export async function uploadFile(
  repoServ: any, // 替换为实际服务类型
  file: File,
  isImage: boolean,
  fileItem: FileItem,
  onError?: () => void,
): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('is_image', JSON.stringify(isImage));

  try {
    const res = await repoServ.uploadFile(formData, fileItem.controller.signal);
    fileItem.progress = 'succeeded';
    fileItem.url = res.url;
  } catch (error) {
    fileItem.progress = 'failed';
    onError?.();
  }
}
