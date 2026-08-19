// 烟雾测试：验证 Karma + Jasmine + ChromeHeadlessCI 测试入口可执行。
// 不依赖任何业务代码，仅断言测试框架本身工作。
describe('smoke', () => {
  it('should pass a trivial assertion', () => {
    expect(true).toBe(true);
  });
});
