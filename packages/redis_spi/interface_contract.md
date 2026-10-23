# Redis Provider 适配层 接口契约文档

> 适用范围：`redis_spi` / `redis_native` / `redis_contract_tests` / `redis_demo_provider`（Python）与
> Java manager 侧（SPI 位于 `studio-manager-api`、Redisson 实现与装配位于 `studio-manager-service`）。
> 读者：企业自研 Redis Provider 开发者、平台维护者、验收测试人员。
> 实现级设计见 `设计文档/Redis适配层-特性设计.md`。

## 1. 分层与包结构

### Python（agent-runtime / agent-builder 共享 venv）

| 包 | 角色 | 依赖 |
|---|---|---|
| `redis_spi` | SPI：协议面（核心命令 + 能力组）+ 类型 + 异常 + Provider 工厂/注册 + accessor | 零 redis-py 依赖 |
| `redis_native` | 缺省原生实现（redis-py 直连），含 `compat.as_native_client` 原生视图 | redis-py |
| `redis_contract_tests` | 契约套件（core / pipeline / error_mapping / capability 四组） | redis_spi |
| `redis_demo_provider` | 接入示例（独立实现 / Wrapper 两种形态） | redis_spi |

### Java（backend Maven reactor）

| 位置 | 角色 | 依赖 |
|---|---|---|
| `studio-manager-api` 内 `common.redis` 包 | SPI：`RedisClient` 接口（零 Redisson）+ `RedisLock` + `spi/`（Factory/Context/Exception）+ Wrapper | 无 Redisson |
| `studio-manager-service` 内 `common.redis` 包 | 缺省实现（Redisson）+ 单点装配 `RedisProviderAutoConfig` / `RedisProviderResolver` / `RedisClientConfig` + 契约基类 `RedisContractTestBase`（测试树） | api + redisson |
| `examples/redis-demo-provider` | 接入示例（`-Pexamples` 门控，不进产品 reactor；契约基类为测试源自带副本，与 manager-service 同源） | manager-api |

## 2. 核心契约（Python 协议面）

### 2.1 命令组（protocols.py）

- **核心必选**（`RedisClient` 协议，所有 Provider 必须实现）：
  `KeyCommands`（exists/delete/expire/ttl/persist…）、`StringCommands`（get/set/mget/mset…）、
  `HashCommands`、`ListCommands`、`SetCommands`、`ScanCommands`、pipeline、`ping`。
- **可选能力组**（`supports()` 声明，按声明跑批）：`CounterCapability`、`SortedSetCapability`、
  `BitmapCapability`、`HyperLogLogCapability`、`GeoCapability`、`ScriptingCapability`、
  `PubSubCapability`、`BlockingCommands`。
  （注：ZSet 命令属可选能力组 `SortedSetCapability`，不在核心必选面——与 protocols.py 一致）

### 2.2 类型与语义约定

| 约定 | 内容 |
|---|---|
| 值类型 | 默认 **bytes**（对齐 redis-py `decode_responses=False`）；`REDIS_TEXT_MODE=true` 可切 text 视图（memory_server 场景） |
| TTL | 显式 `Duration` 类型（`Duration.seconds(n)` / `Duration.milliseconds(ms)`），禁止裸 int |
| SET 条件 | `condition=SetCondition.NX / XX`（替代 redis-py `nx=True`） |
| 返回哨兵 | key 缺失 → `get` 返回 `None`；`lrange` 返回 `[]`；计数器不存在从 0 起 |
| pipeline | 运行期命令错误不回滚已执行命令（与 redis-py 语义一致） |
| 装配 | `RedisProviderFactory.create(settings)`：解析 → `start()` → **ping fail-fast**（失败自动 stop 回收） |
| 生命周期 | accessor 进程级单例；`initialize` 幂等；`aclose` 幂等 |

### 2.3 Java 侧对应口径

- `RedisClient` 接口 = Python 核心面的 Java 子集（String/Key + 锁 + List + 计数器 + `getRaw` 原文读取）；
  死接口（`setObj`/`scoredSorted*`）`@Deprecated` + default 抛 `CapabilityUnsupportedException`，不计入自研 Provider 强制实现面。
- 装配：`RedisProviderResolver` 五级解析链（显式 `redis.provider-class` > ServiceLoader > memory > legacy RedisClient3rd 兼容 > 缺省 redisson）。
- **锁语义**：可重入（Redisson RLock 同构）；`tryLock(maxWait)` 等待超时语义；跨线程互斥。
- **计数器 TTL 属实现定义**：`timeoutSeconds` 为提示值（Redisson 的 options timeout 不兑现过期；
  需要确定 TTL 的调用方显式 `expire()`，参考 `AgentServiceProxyService#checkUploadNum` 固定窗口实践）。

## 3. 错误分类与错误码登记表（Q7）

`redis_spi.exceptions` 全部异常携带数字 `code`，登记于 **260000 段**（与平台既有段避让：
manager 02xxxxx / workflow 10xxxx / builder 131xxxx / NL2 100029 谱系）：

| code | 异常 | 语义 |
|---|---|---|
| 260000 | `RedisError`（根） | 兜底 |
| 260001 | `RedisConfigError` | 配置错误（provider 名不存在 / 参数非法 / 原生视图不可用） |
| 260002 | `RedisConnectionError` | 连不上 / 网络故障（可重试） |
| 260003 | `RedisAuthFailureError` | 认证失败（`RedisConnectionError` 子类） |
| 260004 | `RedisTimeoutError` | 超时（写结果可能未知，禁止盲重试） |
| 260005 | `RedisCommandError` | 命令错误（调用方错误） |
| 260006 | `RedisWrongTypeError` | WRONGTYPE（`RedisCommandError` 子类） |
| 260007 | `CapabilityNotSupportedError` | 调用未实现/未声明的能力 |
| 260008 | `RedisScriptError` | Lua 脚本运行期 / NOSCRIPT |
| 260009 | `RedisClusterError` | 集群拓扑类错误 |

Java 侧对应（J4 已交付，`studio-manager-api` 的 `common.redis.exception` 包）：
`RedisAccessException`（根，携带 redisKey/operation）→ `RedisConnectionFailureException`（可重试可降级）/
`RedisTimeoutException`（写/计数结果可能未知，禁盲重试）/ `RedisCommandException`（含
`RedisWrongTypeException` 子类）/ `CapabilityUnsupportedException`；既有异常归族：
`RedisReadOverflowException` ⊂ `RedisCommandException`、`RedisProviderException` ⊂ `RedisAccessException`。
`RedisExceptionClassifier`（类名/消息字符串匹配，零 Redisson 依赖）供 Provider 边界翻译与
Wrapper 分类日志使用。Wrapper 降级行为不变（连接/解码失败降级 null、溢出抛异常），
分类供需要区分的调用方使用（Q12 渐进口径）。两栈分类对齐 Python 260000 段。

## 4. Provider 接入契约

注册方式（二选一）：

1. **显式配置**：`REDIS_PROVIDER=自定义名` + `REDIS_PROVIDER_CLASS=全限定类名或文件路径`（Java：`redis.provider-class`）
2. **自动发现**：Python `entry_points`（`redis_spi.providers`）；Java `META-INF/services/...RedisProviderFactory`（ServiceLoader）

配置面（Python env / Java yml 同名映射）：

| 配置 | env | Java yml | 缺省 |
|---|---|---|---|
| Provider 名 | `REDIS_PROVIDER` | `redis.client-type`+`redis.provider-class` | `native` / `redisson` |
| 实现类 | `REDIS_PROVIDER_CLASS` | `redis.provider-class` | — |
| 企业专属参数 | `REDIS_PROVIDER_CONFIG`（JSON）/ `REDIS_PROVIDER_CONFIG_FILE` | `redis.provider-config(-file)` | 空（框架不解析内部字段，透传 `getRawConfig`） |
| 连接 | `REDIS_HOST/PORT/PASSWORD/DATABASE/MODE` | `redis.host/port/password/…` | 127.0.0.1:6379 single |
| 集群/哨兵 | `REDIS_CLUSTER_NODES` / `REDIS_SENTINEL_*` | `redis.cluster_node_list` / `redis.sentinel_*` | — |

企业接入清单（五步）：仅依赖 spi 包 → 实现 Provider/Factory → 契约子类验收 → （可选）ServiceLoader 注册 →
classpath + 配置切换，业务代码零改动。完整指南见 `packages/redis_demo_provider/README.md`（Python）
与 `backend/examples/redis-demo-provider/README.md`（Java）。

## 5. 契约套件与 CI 接入

### 5.1 Python（redis_contract_tests，四组）

| 组 | 覆盖 |
|---|---|
| `test_core_contract.py` | 核心命令语义 / TTL / 返回哨兵 / SCAN |
| `test_pipeline_contract.py` | pipeline 事务与非事务语义 |
| `test_error_mapping.py` | 错误分类映射（含连接族/超时族自分类） |
| `test_capability_contract.py` | 按 `supports()` 声明跑批 + Lua 引擎探测 |

运行命令矩阵（CI 逐行执行，互不依赖；后端经 `REDIS_CONTRACT_TARGET` 注入，
取值形态：`native` / `module:Class` / `file.py:Class` / entry_points 注册名）：

```bash
# ① 委托层替身后端（零基础设施）
REDIS_CONTRACT_TARGET=redis_contract_tests.stub_backend:StubRedisProvider \
  python -m pytest --pyargs redis_contract_tests -q
# ② demo Provider（形态一独立实现 / 形态二 Wrapper）
REDIS_CONTRACT_TARGET=acme_demo python -m pytest --pyargs redis_contract_tests -q
REDIS_CONTRACT_TARGET=redis_demo_provider.wrapper:WrapperDemoProvider \
  python -m pytest --pyargs redis_contract_tests -q
# ③ native × 真实 Redis（REDIS_* 指定连接）
REDIS_CONTRACT_TARGET=native REDIS_HOST=127.0.0.1 REDIS_PORT=6379 REDIS_PASSWORD=*** \
  python -m pytest --pyargs redis_contract_tests -q
```

### 5.2 Java（`RedisContractTestBase`，17 用例；基类位于 studio-manager-service 测试树，demo 工程自带同源副本）

String/Key 语义、真实 TTL 过期、返回哨兵、锁互斥与等待超时、List 边界（负索引/lTrim）、
计数器、`setAndKeepTtl` 保留剩余 TTL、`getRaw`、每用例独立前缀 + 清理。

```bash
# ① demo Provider（无基础设施）
mvn -Pexamples -pl examples/redis-demo-provider -am test
# ② Redisson × 真实 Redis（env 门控）
REDIS_CONTRACT_TARGET=127.0.0.1:6379 REDIS_CONTRACT_PASSWORD=*** \
  mvn -pl studio-manager-service -am test -Dtest=RedissonRealRedisContractTest
```

企业验收：实现 `RedisContractTestBase` 子类（Java）或指定 `--backend`（Python）跑同一套语义。

## 6. 跨语言命令语义对照表

同一命令在 Python / Java 两栈的行为对齐基准（验收时两栈结论必须一致）：

| 语义 | Python（redis_spi） | Java（RedisClient） | 对齐基准 |
|---|---|---|---|
| SET + TTL | `set(k, v, duration=Duration.seconds(n))` | `set(k, v, Duration.ofSeconds(n))` | 秒级显式单位 |
| SET 条件 | `condition=SetCondition.NX` | `condition` 由实现消化（当前无暴露面） | Python 全量 |
| GET 缺失 | `None` | `null` | 一致 |
| 原文读取 | bytes/text 视图 | `getRaw(k)`（绕过编解码） | 语义一致（形态各栈内部） |
| EXPIRE | `expire(k, Duration)` → bool | `expire(k, Duration)` → bool | 一致 |
| DEL | `delete(*keys)` → int | `delete(*keys)` → int | 一致 |
| EXISTS | `exists(*keys)` → int | `exists(*keys)` → int | 一致 |
| RPUSH/LRANGE/LLEN | `rpush/lrange/llen`（stop=-1 到末尾） | `rPushAll(批量)/lRange/lLen`（Java 为批量推入形态） | 语义一致 |
| 计数器 | `CounterCapability.incr/decr`（TTL 实现定义） | `getAndIncrement/addAndGet`（前值/累加；TTL 实现定义） | TTL 不入契约，调用方显式 expire |
| 保留 TTL 写 | — | `setAndKeepTtl`（保留剩余 TTL，不重置） | Java 专属（溢出清理场景） |
| 锁 | 无（Python 侧用分布式锁另议） | `getLock().tryLock(maxWait)` 可重入 + 等待超时 | Java 专属 |
| WRONGTYPE | `RedisWrongTypeError`（260006） | Wrapper 降级（连接族）/实现抛 | 分类口径一致，传播策略各栈 |
| 超时 | `RedisTimeoutError`（260004，禁盲重试） | Wrapper 降级 null + 日志 | 同左 |
| pipeline | `pipeline()`（错误不回滚） | 无暴露面（实现内部） | Python 专属 |

## 7. 版本兼容性注记（2026-10-13 双版本验证完成）

契约套件与 native 实现已在 **redis-py 8.1.0**（本地 venv）与 **6.4.0**（Docker
`agent-runtime/requirements.txt` 口径，隔离 venv 实测）双版本下全量验证通过：

| 后端 | redis-py 8.1.0 | redis-py 6.4.0 |
|---|---|---|
| native × 真实 Redis | 71/71（阻塞超时浮点缺陷修复**前**的口径：fakeredis 宽容浮点掩盖了真实 Redis 整数秒要求——PR 评审复现推翻本行结论；修复后经真实 Redis 定向实证阻塞路径恢复，全量重验待 CI 接入） | 同左 |
| 委托层替身 | 49 过 | 49 过 |
| native 单测 | 202/202 | 202/202 |

**6.4.0 特有差异与适配**（已修复，双版本行为一致）：redis-py 6.4.0 的 pipeline
运行期错误 raise 路径存在消息模板格式化缺陷——输出字面量 `{exception.args}`，
原始错误文本（WRONGTYPE 等）完全丢失，错误分类无从识别。`NativePipeline.execute`
因此改用 `execute(raise_on_error=False)` 模式：命令级错误以**原始异常对象**形式
出现在结果列表中（各 redis-py 版本一致），逐个翻译后抛第一个——不依赖 raise 消息
格式。不支持该参数的替身客户端（fakeredis FakePipeline）经构造期签名探测自动回退
raise 路径（原行为，替身消息含原文可识别）。

## 8. 已知边界（review 2026-10-14 拍板）

| 边界 | 说明 |
|---|---|
| **builder 对适配层的强依赖** | agent-builder 与 agent-runtime 共享 venv，`redis_spi` 视为强制依赖（history.py 顶层 import）；`server_fastapi._init_redis_provider` 的 ImportError 回退仅防御无适配层的独立环境。 |
| **builder 装配失败 fail-fast** | Provider 装配失败（ping 不通/配置错）时 builder 启动终止（与 runtime 一致）——异步存储直调 accessor 无 legacy 回退，半可用状态（同步通/异步永久失败）是慢性隐蔽故障，显式失败交由进程重启自愈。 |
| **会话缓存格式变更（Java）** | SessionService 迁移后 Redis 中会话值由 RedisTemplate 带类型 JSON 改为纯 JSON：升级瞬间存量登录态失效一次（用户需重新登录，安全降级无崩溃）；滚动部署窗口内新旧 pod 的会话缓存互不可读，窗口期内可能出现重复登录提示。 |
| **错误消息脱敏** | Java `parseProviderConfig` 与 Python `REDIS_PROVIDER_CONFIG` 校验错误的日志不回显原始配置内容（可能含企业凭证）；`RedisClientConfig` 的 `redisPassword`/`providerConfig` 字段排除出 toString。 |
| **`redis.provider-class` 为部署信任配置** | 该配置项驱动反射类加载（等价于既有 Spring `logging.config` 等运维原语），仅限 operator 管理，不得暴露给租户级配置入口。 |
| **wrapper 原始类型方法的失败语义** | `getAndIncrement`/`addAndGet`/包装 `tryLock` 在 Redis 故障时抛 NPE（继承自存量 wrapper 行为，测试已锁定）——与降级契约存在张力，调用方应感知；后续版本可对齐 `lLen` 的零值降级。 |
