import { AbstractControl, ValidationErrors } from '@angular/forms';
import {
  TEMPLATENAME_REG,
  MCP_SERVER_ADDRESS,
  MCP_SERVER_PARAM_VALUE,
} from '@constants/exp-tmpl-config.const';
import i18next from 'i18next';
/**
 *  自定义校验规则类
 */
export class CommonValidation {
  // 自定义正则与描述信息校验
  public static customVerify(regularity: string | RegExp, tip: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      new RegExp(regularity).test(control.value as string)
        ? null
        : { nameChAllow: { tiErrorMessage: tip } };
  }

  /**
   * 通用名称校验
   * 中文、字母开头，以中文、字母、数字结尾，长度2~32的字符串。只允许输入中文、字母、数字、中划线、下划线等字符
   */
  public static nameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[A-Za-z\u4E00-\u9FA5](?:[\w\u4E00-\u9FA5-]{0,30}[\dA-Za-z\u4E00-\u9FA5])$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static enNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[a-z0-9_]+$/.test(control.value as string)
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static nameUniquenessVerify(
    names: string[],
    tips: string,
    originName: string,
  ) {
    return (control: AbstractControl): ValidationErrors | null =>
      names.includes(control.value as string) && control.value !== originName
        ? { serviceName: { tiErrorMessage: tips } }
        : null;
  }

  public static enVarNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[A-Za-z]\w*[\dA-Za-z]$/.test(control.value as string)
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  /** 数据集名称校验
   *  中文、字母开头，以中文、字母、数字结尾，长度2~32的字符串。只允许输入中文、字母、数字、中划线、下划线等字符
   */
  public static datasetNameVerify(tips: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      return /^[A-Za-z\u4E00-\u9FA5](?:[\w\u4E00-\u9FA5-]{0,30}[\dA-Za-z\u4E00-\u9FA5])$/.test(
        v,
      )
        ? null
        : { nameChAllow: { tiErrorMessage: tips } };
    };
  }

  /** 模板名称校验
   *  中文、字母开头，以中文、字母、数字结尾，长度2~20的字符串。只允许输入中文、字母、数字、中划线、下划线等字符
   */
  public static templateNameVerify(tips: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      return TEMPLATENAME_REG.test(v)
        ? null
        : { nameChAllow: { tiErrorMessage: tips } };
    };
  }

  // 节点校验
  private static checkNode(
    params: { max: number; min: number; step: number },
    inputValue: number,
  ): boolean {
    return inputValue >= 1 && (inputValue - params.min) % params.step === 0;
  }

  public static customVerifyNode(
    params: { max: number; min: number; step: number },
    tip: string,
  ) {
    return (control: AbstractControl): ValidationErrors | null =>
      this.checkNode(params, control.value as number)
        ? null
        : { nameChAllow: { tiErrorMessage: tip } };
  }

  /** 变量名称校验
   *  中文、字母开头，以中文、字母、数字结尾，长度1~10个字符。只允许输入中文、字母、数字、中划线、下划线等字符
   */
  public static varNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[A-Za-z\u4E00-\u9FA5](?:[\w\u4E00-\u9FA5-]{0,8}[\dA-Za-z\u4E00-\u9FA5])?$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  /** 在场景型体验页中，校验左侧表单值调用trim()之后，是否为空。若为空，则校验不通过 */
  public static isBlankVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      const value = String(control.value)?.trim();
      return value ? null : { serviceName: { tiErrorMessage: tips } };
    };
  }

  /** score Threshold
   * 匹配两位浮点数
   */
  public static scoreVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^(([1-9]{1}\d*)|(0{1}))(\.\d{0,2})$/.test(control.value as string)
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  // 创建插件名称校验
  public static pluginNameVerify(emptyMsg: string, errMsg: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      if (v.length === 0) {
        return { nameChAllow: { tiErrorMessage: emptyMsg } };
      }

      return /^[a-zA-Z0-9_]+$/.test(v)
        ? null
        : {
            nameChAllow: {
              tiErrorMessage: errMsg,
            },
          };
    };
  }
  // 创建工具英文名称校验
  public static toolNameVerify(emptyMsg: string, errMsg: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      if (v.length === 0) {
        return { nameChAllow: { tiErrorMessage: emptyMsg } };
      }

      return /^[a-zA-Z0-9_]{1,64}$/.test(v)
        ? null
        : {
          nameChAllow: {
            tiErrorMessage: errMsg,
          },
        };
    };
  }
  // 创建工具中文名称校验
  public static toolZhNameVerify(emptyMsg: string, errMsg: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      if (v.length === 0) {
        return { nameChAllow: { tiErrorMessage: emptyMsg } };
      }

      return /^.{1,64}$/.test(v)
        ? null
        : {
          nameChAllow: {
            tiErrorMessage: errMsg,
          },
        };
    };
  }
  // 创建插件Header校验
  public static pluginHeaderVerify(tips: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      if (!v.trim()) {
        return null;
      }
      if (!v.startsWith('{') || !v.endsWith('}')) {
        return { nameChAllow: { tiErrorMessage: tips } };
      }

      try {
        const obj = JSON.parse(v);
        // eslint-disable-next-line @typescript-eslint/no-unsafe-argument
        if (typeof obj === 'object' && obj && Object.keys(obj).length > 0) {
          return null;
        }

        return { nameChAllow: { tiErrorMessage: tips } };
      } catch {
        return { nameChAllow: { tiErrorMessage: tips } };
      }
    };
  }

  // 创建插件描述校验
  public static pluginDescVerify(emptyMsg: string, defaultMsg: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      const v: string = control.value || '';
      if (v.length === 0) {
        return { nameChAllow: { tiErrorMessage: emptyMsg } };
      }

      return v ? null : { nameChAllow: { tiErrorMessage: defaultMsg } };
    };
  }

  // 创建服务地址校验
  public static serviceAddressVerify() {
    return (control: AbstractControl): ValidationErrors | null => {
      const v: string = control.value || '';
      if (v.trim().length === 0) {
        return {
          nameChAllow: {
            tiErrorMessage: i18next.t('service_msg_validate_msg1'),
          },
        };
      }
      if (!MCP_SERVER_ADDRESS.test(v)) {
        return {
          nameChAllow: {
            tiErrorMessage: i18next.t('service_msg_validate_msg2'),
          },
        };
      }
      return null;
    };
  }

  // MCP开通服务参数值校验
  public static provisionServiceVerify() {
    return (control: AbstractControl): ValidationErrors | null => {
      const v: string = control.value || '';
      if (!MCP_SERVER_PARAM_VALUE.test(v)) {
        return {
          nameChAllow: {
            tiErrorMessage: i18next.t('variable_validator4'),
          },
        };
      }
      return null;
    };
  }

  public static pluginHostVerify(tips: string) {
    return (control: AbstractControl) => {
      const value: string = control.value || '';
      // 验证IPv4地址（支持端口号）
      const ipv4Regex = /^(\d{1,3}\.){3}\d{1,3}(\:\d+)?$/;
      // 验证域名（支持端口号）
      const domainRegex = /^([a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}(\:\d+)?$/;

      // 判断是否符合 IPv4 或域名格式
      if (ipv4Regex.test(value) || domainRegex.test(value)) {
        // 提取端口号
        const portMatch = value.match(/:(\d+)$/);
        if (portMatch) {
          const port = parseInt(portMatch[1], 10);
          // 限制端口号范围在 1 到 65535
          if (port < 1 || port > 65535) {
            return { hostInvalid: { tiErrorMessage: tips } };
          }
        }
        return null; // 验证通过
      } else {
        return { hostInvalid: { tiErrorMessage: tips } };
      }
    };
  }
  // 创建插件url校验
  public static pluginUrlVerify(tips: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      return /^(?<protocol>https?:\/\/)(?<number>[0-9a-z.]+)/i.test(v)
        ? null
        : { nameChAllow: { tiErrorMessage: tips } };
    };
  }
  // 创建插件请求方式校验
  public static pluginMethodVerify(tips: string) {
    return (control: AbstractControl) => {
      const v: string = control.value || '';
      return /^(?<methods>get|post)$/i.test(v)
        ? null
        : { nameChAllow: { tiErrorMessage: tips } };
    };
  }

  // 校验定时触发器的时间是否重复
  public static isTimeDuplicated(existingTimes: any, tips: string) {
    return (control: AbstractControl) => {
      const timeSelected = (control.value || []).map((item) => item.label);

      const isDuplicated = existingTimes.some((item) => {
        return (
          item.length === timeSelected.length &&
          item.every((value, index) => value === timeSelected[index])
        );
      });
      return isDuplicated ? { nameChAllow: { tiErrorMessage: tips } } : null;
    };
  }

  public static wfEnNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[a-zA-Z][a-zA-Z0-9_\s\-.]{0,62}[a-zA-Z0-9]$/.test(control.value as string)
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static wfNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^(?! )[a-zA-Z0-9\u4e00-\u9fa5_-](?:[a-zA-Z0-9\u4e00-\u9fa5 _-]{0,62})[a-zA-Z0-9\u4e00-\u9fa5_-]$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  // 校验插件展示名称是否合法
  public static pluginZHNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^(?! )[a-zA-Z0-9\u4e00-\u9fa5_](?:[a-zA-Z0-9\u4e00-\u9fa5_]{0,62})[a-zA-Z0-9\u4e00-\u9fa5_]$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static regVerify(reg: RegExp, tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      reg.test(control.value as string)
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  // 校验数据源option对象中的id不能为空字符串
  public static isDatasourceIdEmpty(tips: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      const id = control.value?.id;
      return id === '' ? { objectIdRequired: { tiErrorMessage: tips } } : null;
    };
  }


  // 创建插件描述校验
  public static modeNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[a-zA-Z0-9_|\- \u4e00-\u9fa5]{2,64}$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static modeEnNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[a-zA-Z0-9_|\- ]{2,64}$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  //支持英文、数字、下划线、中划线
  public static validAPIKEYVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^(?!_)(?!\d)[a-zA-Z0-9_\-\u4e00-\u9fa5.]{2,36}$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  // 仅支持英文、数字、下划线,且需要以字母开头
  public static validNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[A-Za-z][A-Za-z0-9_]*$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static modeServiceNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[\u4e00-\u9fa5a-zA-Z0-9](?:[\u4e00-\u9fa5a-zA-Z0-9_.|\\/:-]{0,62}[\u4e00-\u9fa5a-zA-Z0-9])?$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static modelNameVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^[\u4e00-\u9fa5a-zA-Z0-9](?:[\u4e00-\u9fa5a-zA-Z0-9@_.|\\/:-]{0,62}[\u4e00-\u9fa5a-zA-Z0-9])?$/.test(
        control.value as string,
      )
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  public static pluginParamHostVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      if (control.value.length > 256 || control.value.length < 1) {
        return { serviceName: { tiErrorMessage: '长度在1~256之间' } };
      }

      return /^[A-Za-z0-9_\-{}:.]+$/.test(control.value as string) ? null : { serviceName: { tiErrorMessage: tips } };
    };
  }

  public static pluginParamBaseUrlVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null => {
      return /^\/[A-Za-z0-9_\-{}\/]*$/.test(control.value as string) || (control.value as string) === '' ? null : { serviceName: { tiErrorMessage: tips } };
    };
  }
  
  public static pluginParamToolPathVerify(tips: string) {
    return (control: AbstractControl): ValidationErrors | null =>
      /^\/\S*$/.test(
        control.value as string,
      ) || control.value as string === ''
        ? null
        : { serviceName: { tiErrorMessage: tips } };
  }

  // 名称长度限制
  public static NAME_LENGTH_LIMIT = 32;

  // 内容长度限制
  public static CONTENT_LENGTH_LIMIT = 4000;

  // 描述长度限制
  public static DESP_LENGTH_LIMIT = 100;

  // Agent名称长度限制
  public static AGENT_NAME_LENGTH_LIMIT = 64;

  // Agent描述长度限制
  public static AGENT_DESP_LENGTH_LIMIT = 500;
}
