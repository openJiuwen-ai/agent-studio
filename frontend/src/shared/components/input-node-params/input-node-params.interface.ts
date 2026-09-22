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
    /** URL 录入条目标记（本地上传条目无此标记） */
    fromUrl?: boolean;
  };
  /** file 参数录入模式：本地上传 | URL 链接（仅 image/video 子类型可切换） */
  urlMode?: FileUrlMode;
  /** 编辑 URL 条目的回填请求（每次新对象触发 file-url-input 载入输入框） */
  urlEditReq?: { url: string } | null;
}

export interface InputChatItem {
  dialogId?: string;
}