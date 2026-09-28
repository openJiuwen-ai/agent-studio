# Redis 适配层与自研 Provider 接入指南

本文介绍 openJiuwen Studio 的 Redis 能力抽象层（适配层）：如何在 Java 与 Python 双栈以插件方式接入企业自研 Redis（自研代理、改造集群、自定义认证链路等），无需 fork 修改框架源码。

---

## 1. 概述

企业用户普遍持有自研 Redis，出于协议适配、安全合规（自研鉴权/审计/国密）、统一运维与高可用治理的要求，无法直接使用开源客户端接入。适配层将平台对 Redis 的调用收敛到统一的能力抽象接口，并以 Provider 插件机制支持实现替换：

- **能力面收敛**：以平台实际使用的 Redis 命令与语义为限定义接口（KV、TTL、hash、set、zset、list、计数器、分布式锁、按前缀删除、scan 等），接口附完整契约文档（方法语义、错误分类、前置条件）。
- **原生默认实现**：Java 侧为 Redisson（单机/集群/哨兵），Python 侧为 redis-py（`RedisClientManager` 包装），默认行为零变更。
- **Provider 插件化**：配置切换实现，企业自研实现通过一致性测试套件（TCK）自验证。
- **存量兼容**：Java 侧保留 `redis.client-type` 配置与 `RedisClient3rd` 扩展点兼容（已废弃，建议迁移）。

| 技术栈 | 抽象接口 | 默认实现 | 测试实现 | Provider SPI |
| --- | --- | --- | --- | --- |
| Java（studio-common） | `RedisClient` | `RedisClientRedisson` | `RedisClientMemory` | `RedisClientProvider` |
| Python（packages/common_utils） | `BaseSyncRedisClient` / `BaseAsyncRedisClient` | `RedisPySyncClient` / `RedisPyAsyncClient` | `InMemorySyncRedisClient` 等 | `RedisProvider` |

---

## 2. Java 侧接入（studio-common）

### 2.1 配置项

| 配置项 | 说明 | 默认值 |
| --- | --- | --- |
| `redis.provider.type` | Provider 标识（内置 `redisson` / `memory`，或 ServiceLoader 注册的企业标识） | 空（回退 `redis.client-type`） |
| `redis.provider.class` | Provider 实现类全限定名（优先级最高） | 空 |
| `redis.client-type` | 存量配置（`redisson` / `memory`），兼容保留 | `redisson` |

解析优先级：`redis.provider.class` > `redis.provider.type` > `redis.client-type=memory` > 存量 `RedisClient3rd`（classpath 存在时兼容启用） > 默认 `redisson`。

### 2.2 实现 Provider

```java
package com.yourcompany.redis;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider;

public class YourRedisClientProvider implements RedisClientProvider {
    @Override
    public String name() {
        return "your-redis";  // 全局唯一，内置 redisson/memory 不可复用
    }

    @Override
    public RedisClient createClient(RedisClientConfig config) {
        return new YourRedisClient(config);  // 必须满足 RedisClient 契约
    }
}
```

接入方式（任选其一）：

**方式一：ServiceLoader 插件包（推荐）**

将实现打成 jar 并注册 SPI 文件 `META-INF/services/com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider`（内容为实现类全限定名），jar 放入应用 classpath，配置：

```yaml
redis:
  provider:
    type: your-redis
```

**方式二：显式类名**

```yaml
redis:
  provider:
    class: com.yourcompany.redis.YourRedisClientProvider
```

### 2.3 一致性测试套件（TCK）

自研实现应继承 `studio-common` 测试源码中的 `AbstractRedisClientContractTest` 跑批（覆盖 `RedisClient` 全部方法的语义与边界：TTL、结构类型、锁互斥、批量读取等）。参考 `MemoryRedisClientContractTest`：

```java
class YourRedisClientContractTest extends AbstractRedisClientContractTest {
    @Override
    protected RedisClient createClient() {
        return new YourRedisClient(testConfig());
    }
}
```

### 2.4 契约要点（错误分类）

`RedisClient` 实现应将底层异常原样抛出，由平台包装层 `RedisClientWrapper` 统一分类：

1. 读取溢出（解码约束超限）：抛出 `RedisReadOverflowException`，由调用方清理降级；
2. 数据解码失败（格式损坏/不兼容）：告警并降级返回 null；
3. 连接/超时等故障：记录错误并降级，调用方需具备服务降级能力。

---

## 3. Python 侧接入（packages/common_utils）

### 3.1 配置项（环境变量）

| 环境变量 | 说明 | 默认值 |
| --- | --- | --- |
| `REDIS_PROVIDER_TYPE` | Provider 标识（内置 `redis` / `memory`） | `redis` |
| `REDIS_PROVIDER_MODULE` | 自定义 Provider 模块路径（Python 模块名或 `.py` 文件路径） | 空 |
| `REDIS_PROVIDER_CLASS` | 自定义 Provider 实现类名（必须继承 `RedisProvider`） | 空 |

与 `DATASOURCE_PASSWORD_PROVIDER_*` 加载约定一致：`REDIS_PROVIDER_MODULE` + `REDIS_PROVIDER_CLASS` 显式指定时优先于 `REDIS_PROVIDER_TYPE`。

### 3.2 实现 Provider

```python
from common_utils.common_config import RedisSettings
from common_utils.redis_provider import (
    BaseAsyncRedisClient, BaseSyncRedisClient, RedisProvider,
)

class YourRedisProvider(RedisProvider):
    NAME = "your-redis"

    def name(self) -> str:
        return self.NAME

    def create_sync_client(self, settings: RedisSettings) -> BaseSyncRedisClient:
        return YourSyncRedisClient(settings)

    def create_async_client(self, settings: RedisSettings) -> BaseAsyncRedisClient:
        return YourAsyncRedisClient(settings)
```

启动配置（以文件路径为例，自动加 `.py` 后缀）：

```bash
export REDIS_PROVIDER_TYPE=custom
export REDIS_PROVIDER_MODULE=/opt/plugins/your_redis_provider
export REDIS_PROVIDER_CLASS=YourRedisProvider
```

业务侧获取客户端：

```python
from common_utils.redis_provider import get_provider_sync_client, get_provider_async_client

sync_client = get_provider_sync_client()   # BaseSyncRedisClient
async_client = get_provider_async_client()  # BaseAsyncRedisClient
```

### 3.3 一致性测试套件（TCK）

自研实现应继承 `packages/common_utils/tests/test_redis_provider_tck.py` 中的 `SyncClientContractMixin` 跑批（同步/异步契约：bytes 值语义、TTL、hash/set/list、scan、锁互斥等）。参考 `TestDemoCustomProviderContract` 与 `tests/demo_custom_provider.py`（演示用自研 Provider）。

### 3.4 契约要点

- key 一律 `str`，value 一律 `bytes`（对齐 redis-py `decode_responses=False` 现状，调用方自行解码）；
- TTL 秒数必须为正；`ttl` 返回 `-2`（不存在）/ `-1`（永不过期）/ 剩余秒数；
- 底层异常原样透传（`redis.exceptions.RedisError` 及其子类），由调用方降级。

---

## 4. 存量兼容与迁移说明

- **Java `RedisClient3rd` 扩展点**：classpath 存在该类且未配置新式 Provider 时自动兼容启用（构造签名 `host/password/port` 不变）；已废弃，建议迁移到 `RedisClientProvider`（可获得 TCK 与插件包形态支持）。
- **Java `RedisClient.get(String, Codec)`**：接口已移除 Redisson `Codec` 类型泄漏，等价语义为 `getRaw(String)`（绕过对象解码读取原始字符串）；`RedisClientWrapper` 保留已废弃的双参 `get` 作为兼容桥接。
- **Python `RedisClientManager`**：保持原样不动（存量调用零行为变更），新代码建议通过 `get_provider_sync_client()` / `get_provider_async_client()` 获取客户端。
- **直连收敛**：studio-manager 的 `SessionService` / `SamlAuthFilter` / `SamlController` 已收敛到 `RedisClient` 适配层；studio-space `RedisUtils` 与 agent-runtime 存量直连点的收敛将在后续版本分阶段实施（见 issue #1490）。

---

## 5. 常见问题

**Q: Provider 加载失败如何排查？**

Java 侧报错信息包含可用 Provider 标识列表与加载原因（类不存在、缺少无参构造、未实现接口等）；Python 侧报错含模块加载失败原因与类名校验结果。检查配置项拼写与插件包是否在 classpath / 模块搜索路径中。

**Q: 自研实现必须支持全部能力面吗？**

是。平台按契约调用各能力面方法，实现必须完整并通过 TCK；对未使用的命令语义（如 pub/sub）未纳入能力面，无需实现。

**Q: 如何在单元测试中使用内存实现？**

Java 配置 `redis.client-type: memory`（或 `redis.provider.type: memory`）；Python 设置 `REDIS_PROVIDER_TYPE=memory` 或直接实例化 `InMemorySyncRedisClient`。
