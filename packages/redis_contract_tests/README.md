# redis-contract-tests

Redis Provider **契约/一致性测试套件**（设计文档 §七）——一套测试对任何
Provider 运行，验证 SPI 方法语义 / 返回哨兵值 / 原子性 / 异常分类，而非实现
细节。企业自研 Provider 以跑通本套件作为接入验收（TCK）。

**仅测试环境安装，不进生产镜像。**

## 安装

```bash
pip install -e packages/redis_contract_tests            # 套件本体（仅依赖 redis-spi）
pip install -e packages/redis_contract_tests[stub]      # + 委托层替身后端（redis-native）
pip install -e packages/redis_contract_tests[demo]      # + demo 后端（redis-demo-provider）
```

## 运行（目标由环境变量注入）

```bash
# ① 委托层替身（CI 默认，零外部依赖）：内存替身 × NativeRedisClient，
#    回归 redis_native 的"SPI 语义 → redis-py 调用"翻译链路（核心面）
REDIS_CONTRACT_TARGET=redis_contract_tests.stub_backend:StubRedisProvider \
    python -m pytest --pyargs redis_contract_tests -v

# ② demo·fakeredis 形态（离线）：自研 Provider 独立实现的样板自证
REDIS_CONTRACT_TARGET=acme_demo \
    python -m pytest --pyargs redis_contract_tests -v

# ③ demo·Wrapper 形态（离线，fakeredis 底座，注入默认关闭）
REDIS_CONTRACT_TARGET=redis_demo_provider.wrapper:WrapperDemoProvider \
    REDIS_PROVIDER_CONFIG='{"appId":"a","passport":"p","fakeredis":true}' \
    python -m pytest --pyargs redis_contract_tests -v

# ④ native × 真实 Redis 实例（黄金标准：全能力组）
REDIS_CONTRACT_TARGET=native REDIS_HOST=... REDIS_PORT=6379 \
    REDIS_PASSWORD=... REDIS_MODE=single \
    python -m pytest --pyargs redis_contract_tests -v

# ⑤ 企业自研实例：客户提供 Provider 后同构接入
REDIS_CONTRACT_TARGET=/opt/plugins/my_provider.py:MyProvider \
    python -m pytest --pyargs redis_contract_tests -v
```

Windows PowerShell 形态：`$env:REDIS_CONTRACT_TARGET = "..."` 后同上。

## 跑批口径

| 用例组 | 内容 | 后端要求 |
|---|---|---|
| `test_core_contract.py` | Key/String/Hash/List/Set/Scan 全量语义、TTL 哨兵（-1/-2）、SCAN 游标必须回到 0 | 全部后端必过 |
| `test_pipeline_contract.py` | 入队/执行顺序、transaction=True/False、入队期校验 fail-fast、运行期错误不回滚（Redis 语义） | 全部后端必过 |
| `test_error_mapping.py` | WRONGTYPE→`RedisWrongTypeError`、客户端校验→`RedisCommandError`、坏端口→`RedisConnectionError`（离线后端自动 skip）、能力守卫 | 全部后端必过 |
| `test_capability_contract.py` | 八个可选能力组语义（PubSub 独立订阅池冒烟、Blocking 超时返回 None、Lua 引擎探测） | **按 `supports()` 声明跑批**：声明必过，未声明自动 skip |

- 每用例独立 key 前缀 `contract:<uuid>:`；会话末全量清理（SCAN 循环到 0 + 分批 DEL）。
- 事件循环契约总则 #5：会话级单循环（fixture `loop`），客户端创建/用例/销毁同循环。
- 脚本能力组带 Lua 引擎探测：fakeredis 未装 `lua` 扩展时 skip（真实实例不受影响）。

## 后端一览

| 后端 | 用途 | 依赖 |
|---|---|---|
| `stub_backend:StubRedisProvider` | 委托层替身：手写内存 stub（redis-py 签名对齐）构造 `NativeRedisClient`，零外部依赖回归翻译链路；能力组恒 skip（核心面限定） | redis-native |
| `acme_demo` | demo 形态一（fakeredis 独立实现）：声明核心+PubSub+Blocking，未声明组 skip——能力矩阵口径的活样本 | redis-demo-provider |
| `acme_wrapper` | demo 形态二（Wrapper 治理层，透明模式）：native 全能力面 | redis-demo-provider + redis-native |
| `native` | redis-py 直连真实实例：黄金标准，全能力组（含 Lua） | redis-native + 实例 |
| 企业自研 | `/path/x.py:Class` / `module:Class` / entry_points 注册名 | 企业提供 |

## 给 Provider 实现者的接入清单

1. 实现 `redis_spi.RedisProvider`（start/stop/capabilities）与核心客户端协议；
2. `supports()` 只声明真正实现的能力组（未声明组套件自动 skip）；
3. 异常在边界翻译为 `redis_spi.exceptions` 体系（含 operation/key 上下文）；
4. 用本套件自证：`REDIS_CONTRACT_TARGET=<你的 Provider> pytest --pyargs redis_contract_tests`；
5. 参照 `redis_demo_provider/README.md`（接入指南与 FAQ）。
