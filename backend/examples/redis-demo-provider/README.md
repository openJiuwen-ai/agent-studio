# redis-demo-provider

Redis Provider 插件化接入示例（演示 Provider）。**示例工程：不进产品默认 reactor，不出现在任何产品 artifact 与镜像。**

增强内存后端（ConcurrentHashMap）演示企业自研 Provider 的完整接入形态：

- 真实 TTL（读路径懒判定，`set(Duration)` / `expire` / 计数器 TTL / List TTL）
- 真实跨线程锁竞争（`ReentrantLock.tryLock(timeout)`）
- `setAndKeepTtl` 保留剩余 TTL（镜像默认 Redisson 实现语义）
- 可选注入项：`logCommands`（逐命令日志）、`latencyMillis`（每命令延迟注入）

## 构建

```bash
cd backend
mvn -Pexamples -pl examples/redis-demo-provider -am package
# 产物：examples/redis-demo-provider/target/redis-demo-provider-0.0.1.jar
```

默认 reactor 不含本模块（根 pom 以 `-Pexamples` profile 门控），产品构建与镜像不受影响。

## 契约验收

`DemoProviderContractTest` 继承契约基类 `RedisContractTestBase`（本工程测试源自带副本，
与 studio-manager-service 测试树同源），与默认 Redisson 实现跑同一套用例（String/Key、TTL、返回哨兵、
锁互斥/超时、List 边界、计数器、setAndKeepTtl、原文读取）。企业接入时连同基类副本一起拷贝、
提供自己实现的子类即可复用全部验收用例。

## 接入 manager（两种注入方式）

1. **ServiceLoader 自动发现**：将 jar 放入 manager classpath（如 Docker 镜像 `/opt/plugins/`
   目录或启动脚本 `-cp` 追加），配置：

   ```yaml
   redis:
     client-type: custom
   ```

   classpath 上仅此一个 Provider 工厂时自动选取（jar 内已含
   `META-INF/services/...RedisProviderFactory` 注册文件）。

2. **显式指定类名**：

   ```yaml
   redis:
     client-type: custom
     provider-class: com.openjiuwen.examples.redis.DemoRedisProviderFactory
   ```

## 企业专属参数

框架不解析 Provider 内部参数，经 `redis.provider-config`（内联 JSON）或
`redis.provider-config-file`（文件路径）透传，Provider 内经
`RedisProviderContext#getRawConfig(key)` 读取：

```yaml
redis:
  client-type: custom
  provider-class: com.openjiuwen.examples.redis.DemoRedisProviderFactory
  provider-config: '{"logCommands":true,"latencyMillis":5}'
```

## 企业接入清单

1. 新建 Maven 工程，仅依赖 `studio-manager-api`（SPI 在其 `common.redis` 包，零 Redisson）；
2. 实现 `RedisProviderFactory`（推荐）或直接实现 `RedisClient` + 无参构造 + `init(RedisProviderContext)`；
3. 连接参数从 `RedisProviderContext` 获取（密码已由框架解密），企业专属参数走 `getRawConfig`；
4. 提供契约测试子类（继承 `RedisContractTestBase`）作为合格性验收；
5. （可选）注册 `META-INF/services` 支持 ServiceLoader 自动发现；
6. jar 放 classpath + yml 切换 `client-type`，业务代码零改动。
