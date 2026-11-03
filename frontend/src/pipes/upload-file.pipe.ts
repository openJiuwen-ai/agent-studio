import { Pipe, PipeTransform } from '@angular/core';
import i18next from 'i18next';

const fileUploadDesc = {
  'file/default': i18next.t('file_default'),
  'file/doc': i18next.t('file_doc'),
  'file/txt': i18next.t('file_txt'),
  'file/excel': i18next.t('file_excel'),
  'file/ppt': i18next.t('file_ppt'),
  'file/image': i18next.t('file_image'),
  'file/audio': i18next.t('file_audio'),
  'file/video': i18next.t('file_video'),
  'array<file/default>': i18next.t('file_default'),
  'array<file/doc>': i18next.t('file_doc'),
  'array<file/txt>': i18next.t('file_txt'),
  'array<file/excel>': i18next.t('file_excel'),
  'array<file/ppt>': i18next.t('file_ppt'),
  'array<file/image>': i18next.t('file_image'),
  'array<file/audio>': i18next.t('file_audio'),
  'array<file/video>': i18next.t('file_video'),
};

const formatAudio =
  '.wav,.amr,.flac,.m4a,.mp3,.ogg,.webm,.aac,.ac3,.mov,.wma,.mp4,.avi,.rmvb,.mkv,.flv,.f4v,.wmv,.3gp';
const formatVideo =
  '.mp4,.avi,.rmvb,.mkv,.flv,.f4v,.wmv,.3gp';

export const fileUploadAcc = {
  'file/default':
    '.docx,.doc,.pdf,.txt,.xls,.xlsx,.csv,.ppt,.pptx,.png,.jpg,.jpeg,.gif,.webp,.svg,.mp3,.m4a,.wav,.mp4,.mov,.webm,.jsonl',
  'file/doc': '.docx,.doc,.pdf',
  'file/txt': '.txt',
  'file/excel': '.xls,.xlsx,.csv',
  'file/ppt': '.ppt,.pptx',
  'file/image': '.png,.jpg,.jpeg,.gif,.webp,.svg',
  'file/audio': formatAudio,
  'file/video': formatVideo,
  'array<file/default>':
    '.docx,.doc,.pdf,.txt,.xls,.xlsx,.csv,.ppt,.pptx,.png,.jpg,.jpeg,.gif,.webp,.svg,.mp3,.m4a,.wav,.mp4,.mov,.webm,.jsonl',
  'array<file/doc>': '.docx,.doc,.pdf',
  'array<file/txt>': '.txt',
  'array<file/excel>': '.xls,.xlsx,.csv',
  'array<file/ppt>': '.ppt,.pptx',
  'array<file/image>': '.png,.jpg,.jpeg,.gif,.webp,.svg',
  'array<file/audio>': formatAudio,
  'array<file/video>': formatVideo,
};

@Pipe({
  name: 'fileDesc',
  standalone: true,
})
export class UploadFileDescPipe implements PipeTransform {
  transform(value: string): string {
    return fileUploadDesc[value];
  }
}

@Pipe({
  name: 'fileAcc',
  standalone: true,
})
export class UploadFileAccPipe implements PipeTransform {
  transform(value: string): string {
    return fileUploadAcc[value];
  }
}
