import { I18NextEagerPipe } from 'angular-i18next';
import { IWorkflowField } from './app-flow/node.type';
import { MessageComponent } from '@shared/services/cfdata.service';
import { AgentConfigService, MaxReplySetting } from './agent-config.service';
import { MCP_DEFAULT_ICON_BASE64_STR } from '@shared/config/default-icons-base64';
import { DISPATCH_MODE } from './app-agent/agent-bot-page/agent-bot-page.constant';
import { PluginCredentialStatus } from '@enums/agent-center.enum';
import { IPluginWithTools, PLUGIN_QUOTA } from '@routes/agent-center/app-plugin/app-plugin.interface';
import { pinyin } from "pinyin-pro";

/** 将 KB 限制值转换为展示用 MB 值。不进位，避免展示值大于真实限制。 */
export function formatUploadSizeMb(maxSizeKb: number): number | string {
  const mb = maxSizeKb / 1024;
  return Number.isInteger(mb) ? mb : Math.floor(mb * 100) / 100;
}

export const isSystemTypeWithName = (
  param: IWorkflowField,
  name: string,
): boolean => {
  return (
    (param.source === 'system' || param.source === 'environment') &&
    param.name === name
  );
};

export const isSystemTypeWithNames = (
  param: IWorkflowField,
  names: string[],
): boolean => {
  return (
    (param.source === 'system' || param.source === 'environment') &&
    names.includes(param.name)
  );
};

export function checkFileTypeAndSize(
  fileExtension: string,
  size: number,
  i18n: I18NextEagerPipe,
  maxFileSizeKb: number = AgentConfigService.DEFAULT_FILE_MAX_SIZE_KB,
) {
  if (['png', 'jpeg', 'gif', 'webp', 'jpg', 'svg'].includes(fileExtension)) {
    if (size > 5 * 1024 * 1024) {
      MessageComponent.showWarn(i18n.transform('image_size_cannot_exceed_5mb'));
      return false;
    }

    return true;
  } else if (size > maxFileSizeKb * 1024) {
    MessageComponent.showWarn(
      i18n.transform('file_size_cannot_exceed', { size: formatUploadSizeMb(maxFileSizeKb) }),
    );
    return false;
  } else {
    return true;
  }
}

export const getMaxReplySetting = (selectedModel): MaxReplySetting => {
  const { env = [] } = selectedModel || {};
  const envList = env[0]?.env_list;
  const maxReplySetting = envList?.find(
    (item) => item.env_name === 'max_tokens',
  );

  const defaultSettings = { min: 1, max: 131072, default: 4096 };

  if (maxReplySetting) {
    return {
      min: maxReplySetting.min ?? defaultSettings.min,
      max: maxReplySetting.max ?? defaultSettings.max,
      default: maxReplySetting.default_value ?? defaultSettings.default,
    };
  } else {
    return defaultSettings;
  }
};


export const changePythonJson = (content): any => {
  if(typeof content !== 'string'){
    return content
  }
  const jsonBlockPattern = /```json\s*\n([\s\S]*?)\n```/;
  const match = content.match(jsonBlockPattern)
  if (match && match[0].startsWith("```json") && match[0].endsWith("```")) {
    let str = match[0].replace(/^```json\n/, '').replace(/\n```$/, '')
    return tranJson(str)
  }
  return tranJson(content)
};

function tranJson(str) {
  try {
    let obj = JSON.parse(str);
    return obj;
  } catch (e) {
    return str;
  }
}

export const handleTime = (time) => {
  let date = time.split(' ')[0];
  let y = date.split('/')[0];
  let M = date.split('/')[1];
  let D = date.split('/')[2];
  let today = new Date(); //日期
  let DD = Number(String(today.getDate()).padStart(2, '0')); // 获取日
  let MM = Number(String(today.getMonth() + 1).padStart(2, '0')); //获取月份，1 月为 0
  let yyyy = today.getFullYear(); // 获取年

  if (yyyy - y >= 0 && MM - M >= 3) {
    return '1year';
  } else if (MM - M > 1) {
    return '3month';
  } else if ((MM - M === 0 && DD - D >= 7) || MM - M === 1) {
    return '1month';
  } else if (MM - M === 0 && DD - D > 1) {
    return '1week';
  } else if (MM - M === 0 && DD - D === 1) {
    return '1day';
  } else if (MM - M === 0 && DD - D === 0) {
    return 'today';
  }

  return 'today';
};

export const getMcpIcon = (icon) => {
  if (icon) {
    return icon.startsWith('data:image/') ? icon : `data:image/png;base64,${icon}`;
  }
  return MCP_DEFAULT_ICON_BASE64_STR;
};

export const getMode = (agentMultimodelEnable: boolean, modelSupportFunction: boolean, agentData: any) => {
  const { workflows, tools, mcp_servers, knowledge_repos } = agentData ?? {};
  if (agentMultimodelEnable) {
    return DISPATCH_MODE.TOOL_PRIORITY;
  } else if (workflows.length > 0 || tools.length > 0 || mcp_servers.length > 0) {
    return modelSupportFunction ? DISPATCH_MODE.MODEL_PRIORITY :  DISPATCH_MODE.TOOL_PRIORITY;
  } else if (knowledge_repos.length > 0) {
    return DISPATCH_MODE.KNOWLEDGE_PRIORITY;
  } else {
    return DISPATCH_MODE.MODEL_PRIORITY;
  }
};

export const getPluginQuota = (plugin: IPluginWithTools, isHC: boolean = false): number => {
  if (plugin.credential_status === PluginCredentialStatus.UNAUTHENTICATED) {
    return PLUGIN_QUOTA.NEED_AUTH_NO_QUOTA;
  }
  return PLUGIN_QUOTA.NOT_NEED_AUTH;
};

export const getQuotaTip = (i18n: I18NextEagerPipe, quota: number, limit: number, hasLink: boolean = false): string => {
  if (quota > 0) {
    return i18n.transform(hasLink ? 'quota_used_tip_link' : 'quota_used_tip', {total: limit, time: quota});
  } else if(quota === 0) {
    return i18n.transform(hasLink ? 'quota_used_end_tip_link' : 'quota_used_end_tip', {total: limit, time: quota});
  } else if(quota === PLUGIN_QUOTA.NEED_AUTH_NO_QUOTA) {
    return i18n.transform(hasLink ? 'to_authenticate_tip_link' : 'to_authenticate_tip');
  } else {
    return '';
  }
}

export const getQuotaTag = (plugin: IPluginWithTools, i18n: I18NextEagerPipe, isHC: boolean) => {
  let quota = getPluginQuota(plugin, false);
  if (quota > 0) {
    return {
      text: i18n.transform('app_center_tag_1', { time: quota }),
      color: 'orange',
      tip: i18n.transform('app_center_tag_2', { total: plugin.limit, time: quota }),
    };
  }
  return null;
};

export const pluginFormatter = (plugin: IPluginWithTools, i18n: I18NextEagerPipe, isHC: boolean, hasLink: boolean = false) => {
  let quota = getPluginQuota(plugin, false);
  let hasQuota = quota > 0;
  let tipText = getQuotaTip(i18n, quota, plugin.limit || 0, hasLink);

  return {
    ...plugin,
    unauthenticated: plugin.credential_status === PluginCredentialStatus.UNAUTHENTICATED,
    quota,
    hasQuota,
    authTip: hasQuota ? '' : tipText,
    quotaTip: hasQuota ? tipText : '',
  };
};

export const getUsedUp = (freeTrialQuota) => {
  if (freeTrialQuota) {
    return freeTrialQuota.limit <= freeTrialQuota.usage;
  }
  return false;
};
/**
 * 工作流创建修改，生成code，校验不通过首尾增加字母
 * @param name
 */
export const generateFlowCode = (name: string) => {
  if (!name) {
    return '';
  }
  let code = pinyin(name, { toneType: 'none' })
    .replace(/ü/g, 'v')
    .replace(/\s+/g, '')
    .substring(0, 64)
    .trim();
  if (!/^[a-zA-Z][a-zA-Z0-9_\s\-.]{0,62}[a-zA-Z0-9]$/.test(code)) {
    code = `a_${code.substring(0, 60)}_a`;
  }
  return code;
};
