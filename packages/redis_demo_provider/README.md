# redis-demo-provider

**企业自研 Redis Provider 的可运行参照**（设计文档 §八）——同时是"企业自研
实现接入指南"的活样板：怎么写 Provider、怎么声明能力、怎么注入、怎么自证。

**产物边界：本包不进 studio-runtime 生产镜像**（requirements/Dockerfile 均
不含）；演示与验收时经 pip 安装或 `REDIS_PROVIDER` 指路径注入——这本身就是
插件注入正路的现场演示，同时杜绝演示 Provider 被生产误启用。

## 两种形态怎么选

| | 形态一 `acme_demo`（fakeredis） | 形态二 `acme_wrapper`（Wrapper） |
|---|---|---|
| 定位 | **从零实现**的完整样板：自己实现 Provider + 核心客户端 | **包装治理**样板：包装 `NativeRedisClient` 加鉴权/审计/抖动 |
| 依赖 | redis-spi + fakeredis（**不依赖 redis-native**） | + redis-native（wrapper extra） |
| 外部 Redis | 不需要（全内存） | 可选（`fakeredis: true` 即离线） |
| 能力声明 | 核心 + PubSub + Blocking | native 全能力面 |
| 演示什么 | "自研 SDK 怎么适配 SPI 契约" | "怎么不改框架加自研鉴权/审计链路" |
| 适用 | CI、离线演示、验收第 3 条 | 治理教学、代理模拟、专属参数演示 |

## 快速开始

```bash
pip install -e packages/redis_demo_provider

# 形态一：entry_points 注册名
REDIS_PROVIDER=acme_demo python -c "import asyncio; from redis_spi import accessor; \
    c = asyncio.run(accessor.initialize()); print(asyncio.run(c.ping()))"

# 形态二：鉴权 + 注入（专属参数经 REDIS_PROVIDER_CONFIG）
REDIS_PROVIDER=redis_demo_provider.wrapper:WrapperDemoProvider \
REDIS_PROVIDER_CONFIG='{"appId":"demo-app","passport":"demo-pass","maxAttempts":3,"fakeredis":true}' \
    python -c "..."
```

## 注入方式（四种，全部可用 demo 验证）

1. **entry_points 注册名**（安装后即得）：`REDIS_PROVIDER=acme_demo`
2. **module:Class**：`REDIS_PROVIDER=redis_demo_provider.provider:AcmeDemoProvider`
3. **文件路径**（卷挂载场景）：`REDIS_PROVIDER=/opt/plugins/demo.py:AcmeDemoProvider`
   ——见 `examples/file_injection_demo.py`（卷挂载单文件的最小形态）
4. **REDIS_PROVIDER + REDIS_PROVIDER_CLASS 分置**（OBS 命名对齐）

## 形态二专属参数（REDIS_PROVIDER_CONFIG）

```json
{
  "appId": "demo-app",       // 必填：代理鉴权 appId（缺失/鉴权失败 → RedisAuthFailureError 启动期 fail-fast）
  "passport": "demo-pass",   // 必填：代理鉴权凭证
  "maxAttempts": 3,          // 鉴权重试上限（默认 3）
  "authFailures": 0,         // 模拟前 N 次鉴权失败（演示重试链路）
  "delayMs": 0,              // 每命令延迟注入（毫秒，默认 0=关）
  "failureRate": 0.0,        // 每命令失败注入概率 0~1（模拟代理抖动，抛 RedisConnectionError）
  "rateLimitPerSec": 0,      // 每秒命令数限流（0=关，超限抛 RedisConnectionError）
  "fakeredis": true          // 底座切 fakeredis（离线演示/契约跑批用；缺省连真实实例）
}
```

注入默认全关（透明模式）——治理层不影响语义，契约套件全绿即证明。

## 用契约套件自证（接入验收的标准动作）

```bash
REDIS_CONTRACT_TARGET=acme_demo python -m pytest --pyargs redis_contract_tests -v
# 形态二（透明模式 + fakeredis 底座）
REDIS_CONTRACT_TARGET=redis_demo_provider.wrapper:WrapperDemoProvider \
REDIS_PROVIDER_CONFIG='{"appId":"a","passport":"p","fakeredis":true}' \
    python -m pytest --pyargs redis_contract_tests -v
```

## 企业自研实现接入清单

1. **实现核心面**（必选）：`redis_spi.protocols.RedisClient` 的全部方法
   ——参照 `redis_demo_provider/client.py`（参数校验 fail-fast / 异常边界翻译
   `errors.py` / 返回哨兵归一 bool/None/-1/-2 / TTL 用 Duration 值对象）；
2. **声明能力组**（可选）：框架自身路径只依赖 **核心 + PubSub + Blocking**
   （设计文档 4.5 已核验）——实现多少声明多少（`supports()`），未声明组调用
   收到 `CapabilityNotSupportedError`，契约套件按声明自动 skip；
3. **写 Provider**：`start(settings)` 建客户端（`settings.raw_provider_config()`
   取专属参数）、`stop()` 幂等回收——参照 `provider.py` / `wrapper.py`；
4. **异常翻译在边界**：业务层不接触你 SDK 的原生异常——参照 `errors.py`
   把 SDK 异常映射为 `redis_spi.exceptions` 体系（`__cause__` 保留原始异常）；
5. **发布与注入**：pyproject 声明
   `[project.entry-points."openjiuwen.redis_providers"] 名字 = "模块:类"`，
   或让运维 `/opt/plugins` 卷挂载 `.py` 指路径注入；
6. **自证**：跑 `redis_contract_tests`（见上）——声明面必过、未声明面自动
   skip，通过即完成接入验收。

## FAQ

**Q：企业 Provider 必须实现什么？**
A：**核心必选；能力组按声明实现，未声明的能力组对应命令无需实现**。调用前
`supports()` 探测；未探测直接调用收到 `CapabilityNotSupportedError`。要全量
支持就声明实现所有能力组（如 native）。把能力承诺写成可测试口径：TCK 按
声明矩阵跑批。

**Q：我的 SDK 不是 redis-py 兼容怎么办？**
A：形态一就是为此存在的——`client.py` 是"SPI 协议 → 你的 SDK"的完整适配
样板，把对 fakeredis 的调用换成你 SDK 的等价调用即可；`converters.py` 展示
参数风格映射（TTL 单位/条件参数）该放在哪。

**Q：怎么做鉴权/审计/限流而不改框架？**
A：形态二——在 Provider 层包装客户端（`wrapper.py`），start 期做鉴权
（fail-fast），命令面包日志/注入层。框架全程只认 SPI 协议。

**Q：demo 会不会进生产？**
A：不会。分包发布，requirements/Dockerfile 均不含本包；生产想误启用也
`import` 不到。
