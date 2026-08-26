declare interface Window {
  /**
   * CDN 地址
   *
   * `d_package.sh` 构建注入
   */
  readonly CDNAddress?: string;

  readonly AppWebPath?: string;

  /**
   * DSL 版本对比大 DSL 降级阈值（单侧规范化后文本字节）。
   * 部署时 studio-console start.sh 把 index.html 的 large_dsl_placeholder 替换为字节数；
   * 本地 ng serve 不替换，environment 侧回退默认值。
   */
  readonly largeDslBytesThreshold?: string | number;

  getConsoleContext: () => ConsoleFramework.ConsoleContext;

  __x6_instances__?: any[];
}

declare namespace ConsoleFramework {

  declare interface ConsoleContext {
    /**
     * 获取 Context 模块
     */
    get: (parameter: { name: string }) => any;

    /**
     * 设置 Console Framework 配置
     */
    set: (
      key: string,
      value: boolean | string | Record<string, string>,
    ) => void;

    /**
     * 添加事件监听
     */
    addEventListener: (
      eventName: string,
      handler: (event: CustomEvent) => void,
    ) => void;

    /**
     * 派遣事件
     */
    dispatchEvent: (event: CustomEvent) => void;

    /**
     * 移除事件监听
     */
    removeEventListener: (
      eventName: string,
      handler?: (event: CustomEvent) => void,
    ) => void;
  }
}
