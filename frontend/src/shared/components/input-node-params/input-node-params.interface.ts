import { FileItem } from "@routes/agent-center/multiUpload.utils";
import { IInputItem } from "@routes/agent-center/types/common.types";
import { FileUrlMode } from "@shared/components/file-url-input/file-url-input.component";

interface inputUploadData extends FileItem {
  isHover?: boolean;
}

export interface InputParamConfig extends IInputItem {
  isEmpty?: boolean;
  value?: any;
  file?: File;
  uploadDatas?: inputUploadData[];
  uploadData?: {
    name?: string;
    progress?: string;
    url?: string;
  };
  /** file 参数录入模式：本地上传 | URL 链接（仅 image/video 子类型可切换） */
  urlMode?: FileUrlMode;
}

export interface InputChatItem {
  dialogId?: string;
}