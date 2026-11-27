export interface IEnvironment {
  prefixPath: string;
  jumpObsPath: string;
  envType: 'hc' | 'hcs' | 'hcso' | 'poc' | 'site' | 'icsl';
  serviceType: 'dev' | 'test' | 'prod';
  toolAPIServiceId: string;
  toolAPIName: string;
  serviceName: any;
  userEnv?: '';
  env203?: 'dev' | 'test';
  websocketConnectRelay?: boolean;
  serviceId?: string;
  /** DSL 版本对比单侧规范化后文本字节阈值（Monaco 对比计算保护阈值）。来源：部署时 start.sh 写入 index.html 的 window.largeDslBytesThreshold，无效/缺失回退默认。 */
  largeDslBytesThreshold: number;
  /** iframe SSO 极简接入（定制，默认关）：null = 关闭；非空 = 启用，值为 URL hash token 参数名（同时是 Cookie 名，须与后端 auth_sso_header 同值）。来源：部署时 start.sh 写入 index.html 的 window.iframeSsoTokenParam。 */
  iframeSsoTokenParam: string | null;
}
