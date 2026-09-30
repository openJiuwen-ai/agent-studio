# Redis Adaptation Layer and Custom Provider Integration Guide

This guide describes the openJiuwen Studio Redis capability abstraction layer (adaptation layer): how to plug enterprise-custom Redis implementations (custom proxies, modified clusters, custom authentication chains, etc.) into both the Java and Python stacks without forking framework source code.

---

## 1. Overview

Enterprise users often run proprietary Redis implementations for protocol adaptation, security compliance (custom auth/auditing/SM-crypto), unified operations, and HA governance, and therefore cannot use open-source clients directly. The adaptation layer converges all Redis access in the platform onto a unified capability interface, with a Provider plugin mechanism for implementation replacement:

- **Converged capability surface**: interfaces are defined strictly by the Redis commands and semantics the platform actually uses (KV, TTL, hash, set, zset, list, counters, distributed locks, prefix deletion, scan, etc.), each documented with a full contract (method semantics, error classification, preconditions).
- **Native default implementations**: Redisson on the Java side (single/cluster/sentinel); redis-py wrapped via `RedisClientManager` on the Python side. Default behavior is unchanged.
- **Provider plugin mechanism**: implementations are switched by configuration; custom implementations self-verify against the consistency test kit (TCK).
- **Backward compatibility**: the Java side keeps the legacy `redis.client-type` property and the `RedisClient3rd` extension point (deprecated, migration recommended).

| Stack | Abstraction | Default impl | Test impl | Provider SPI |
| --- | --- | --- | --- | --- |
| Java (studio-common) | `RedisClient` | `RedisClientRedisson` | `RedisClientMemory` | `RedisClientProvider` |
| Python (packages/common_utils) | `BaseSyncRedisClient` / `BaseAsyncRedisClient` | `RedisPySyncClient` / `RedisPyAsyncClient` | `InMemorySyncRedisClient` etc. | `RedisProvider` |

---

## 2. Java Integration (studio-common)

### 2.1 Configuration

| Property | Description | Default |
| --- | --- | --- |
| `redis.provider.type` | Provider name (built-in `redisson` / `memory`, or a ServiceLoader-registered custom name) | empty (falls back to `redis.client-type`) |
| `redis.provider.class` | Fully-qualified provider implementation class (highest priority) | empty |
| `redis.client-type` | Legacy property (`redisson` / `memory`), kept for compatibility | `redisson` |

Resolution order: `redis.provider.class` > `redis.provider.type` > `redis.client-type=memory` > legacy `RedisClient3rd` (enabled automatically when present on the classpath) > default `redisson`.

### 2.2 Implementing a Provider

```java
package com.yourcompany.redis;

import com.openjiuwen.studio.agent.common.redis.RedisClient;
import com.openjiuwen.studio.agent.common.redis.config.RedisClientConfig;
import com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider;

public class YourRedisClientProvider implements RedisClientProvider {
    @Override
    public String name() {
        return "your-redis";  // globally unique; built-in names cannot be reused
    }

    @Override
    public RedisClient createClient(RedisClientConfig config) {
        return new YourRedisClient(config);  // must satisfy the RedisClient contract
    }
}
```

Integration options (either one):

**Option 1: ServiceLoader plugin package (recommended)**

Package the implementation as a jar and register the SPI file `META-INF/services/com.openjiuwen.studio.agent.common.redis.provider.RedisClientProvider` (content: the fully-qualified implementation class name). Put the jar on the application classpath and configure:

```yaml
redis:
  provider:
    type: your-redis
```

**Option 2: explicit class name**

```yaml
redis:
  provider:
    class: com.yourcompany.redis.YourRedisClientProvider
```

### 2.3 Consistency test kit (TCK)

Custom implementations should extend `AbstractRedisClientContractTest` from the studio-common test sources (covers the semantics and boundaries of every `RedisClient` method: TTL, structure types, lock mutual exclusion, batch reads, etc.). See `MemoryRedisClientContractTest`:

```java
class YourRedisClientContractTest extends AbstractRedisClientContractTest {
    @Override
    protected RedisClient createClient() {
        return new YourRedisClient(testConfig());
    }
}
```

### 2.4 Contract highlights (error classification)

`RedisClient` implementations should propagate underlying exceptions as-is; the platform wrapper `RedisClientWrapper` classifies them:

1. Read overflow (decode constraint exceeded): raises `RedisReadOverflowException`; the caller decides the eviction/degradation strategy.
2. Data decode failure (corrupted/incompatible format): warns and degrades to null.
3. Connection/timeout failures: logged and degraded; callers must be able to degrade gracefully.

---

## 3. Python Integration (packages/common_utils)

### 3.1 Configuration (environment variables)

| Variable | Description | Default |
| --- | --- | --- |
| `REDIS_PROVIDER_TYPE` | Provider name (built-in `redis` / `memory`) | `redis` |
| `REDIS_PROVIDER_MODULE` | Custom provider module path (Python module name or `.py` file path) | empty |
| `REDIS_PROVIDER_CLASS` | Custom provider class name (must inherit `RedisProvider`) | empty |

The loading convention matches `DATASOURCE_PASSWORD_PROVIDER_*`: explicitly setting `REDIS_PROVIDER_MODULE` + `REDIS_PROVIDER_CLASS` takes precedence over `REDIS_PROVIDER_TYPE`.

### 3.2 Implementing a Provider

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

Startup configuration (file path example; the `.py` suffix is appended automatically):

```bash
export REDIS_PROVIDER_TYPE=custom
export REDIS_PROVIDER_MODULE=/opt/plugins/your_redis_provider
export REDIS_PROVIDER_CLASS=YourRedisProvider
```

Obtaining clients in business code:

```python
from common_utils.redis_provider import get_provider_sync_client, get_provider_async_client

sync_client = get_provider_sync_client()    # BaseSyncRedisClient
async_client = get_provider_async_client()  # BaseAsyncRedisClient
```

### 3.3 Consistency test kit (TCK)

Custom implementations should extend `SyncClientContractMixin` from `packages/common_utils/tests/test_redis_provider_tck.py` (sync/async contracts: bytes value semantics, TTL, hash/set/list, scan, lock mutual exclusion, etc.). See `TestDemoCustomProviderContract` and `tests/demo_custom_provider.py` (demo custom provider).

### 3.4 Contract highlights

- Keys are always `str`; values are always `bytes` (aligned with redis-py `decode_responses=False`; callers decode themselves).
- TTL seconds must be positive; `ttl` returns `-2` (missing) / `-1` (no expiry) / remaining seconds.
- Underlying exceptions propagate as-is (`redis.exceptions.RedisError` subclasses); callers degrade.

---

## 4. Compatibility and Migration Notes

- **Java `RedisClient3rd` extension point**: enabled automatically when the class is on the classpath and no new-style provider is configured (constructor signature `host/password/port` unchanged); deprecated — migrate to `RedisClientProvider` for TCK support and the plugin package form.
- **Java `RedisClient.get(String, Codec)`**: the Redisson `Codec` type leak has been removed from the interface; the equivalent semantics are `getRaw(String)` (raw string read bypassing object decoding). `RedisClientWrapper` keeps a deprecated two-argument `get` as a compatibility bridge.
- **Python `RedisClientManager`**: unchanged (zero behavior change for existing callers); new code should obtain clients via `get_provider_sync_client()` / `get_provider_async_client()`.
- **Direct-connection convergence**: `SessionService` / `SamlAuthFilter` / `SamlController` in studio-manager have converged onto the `RedisClient` abstraction; convergence of studio-space `RedisUtils` and the legacy direct usages in agent-runtime will be delivered in follow-up phases (see issue #1490).

---

## 5. FAQ

**Q: How do I troubleshoot provider loading failures?**

Java error messages include the list of available provider names and the failure reason (class missing, no no-arg constructor, interface not implemented, etc.); Python errors include module loading failures and class-name validation results. Check property spelling and whether the plugin package is on the classpath / module search path.

**Q: Must a custom implementation support the entire capability surface?**

Yes. The platform invokes capability methods per the contract, so implementations must be complete and pass the TCK. Command semantics unused by the platform (e.g. pub/sub) are out of the capability surface and need not be implemented.

**Q: How do I use the in-memory implementation in unit tests?**

Java: set `redis.client-type: memory` (or `redis.provider.type: memory`); Python: set `REDIS_PROVIDER_TYPE=memory` or instantiate `InMemorySyncRedisClient` directly.
