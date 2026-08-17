/**
 * 资源选择抽屉“选择成功后自动关闭”辅助函数。
 *
 * 背景：flow.component.ts 中的 useAddPluginModal / useAddFlowModal /
 * useAddMcpModal 通过 NzDrawerService.create() 创建的动态抽屉，既不受
 * showPluginDrawer / showChildFlowDrawer / showMcpServiceDrawer 布尔值控制，
 * 也不被 closeNodeConfigDrawer()（仅关闭 halfModalRef）影响。因此选择成功后
 * 必须显式关闭“本次创建”的抽屉实例。
 *
 * 设计要点：
 * - 通过 getter 读取 drawerRef，规避“outputs 必须先于 create() 传入 nzContentParams、
 *   而 drawerRef 由 create() 返回”的先后依赖——回调真正被调用时 ref 已就绪。
 * - 关闭的是 getter 捕获的“本次”局部实例，而非 this.*ModalRef——后者会被后续
 *   打开的同类抽屉覆盖，可能关闭错误实例。
 * - 回调成功（同步返回 / 异步 resolve）后才 close；回调抛错或拒绝则记录错误且不
 *   关闭，避免产生 unhandled rejection 并保留可观测性，便于用户重试。
 */
export interface DrawerLike {
  close(): void;
}

export type DrawerRefGetter = () => DrawerLike | null | undefined;

export function withDrawerAutoClose(
  callback: (...args: any[]) => unknown | Promise<unknown>,
  getDrawerRef: DrawerRefGetter,
): (...args: any[]) => Promise<void> {
  return async (...args: any[]) => {
    try {
      await callback(...args);
    } catch (err) {
      // 选择/创建失败：保留抽屉以便用户重试；记录错误用于排查，不关闭。
      console.error(err);
      return;
    }
    getDrawerRef()?.close();
  };
}
