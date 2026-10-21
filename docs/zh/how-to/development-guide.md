# 开发指南

本指南涵盖 agent-studio 项目的各项开发扩展能力。

## 目录

- [加解密扩展](#加解密扩展)
- [SSO 远程鉴权配置](#sso-远程鉴权配置)
- [存储配置与扩展](#存储配置与扩展)
- [数据库密码获取扩展](#数据库密码获取扩展)
- [自定义插件开发](#自定义插件开发)
- [Redis 适配配置与扩展](#redis-适配配置与扩展)

---

## 加解密扩展

本文档介绍如何在 agent-runtime、agent-builder 和 studio-manager 中扩展加解密实现。

### agent-runtime / agent-builder

#### 继承 BaseCrypt 实现加解密类

1. 创建新类，继承 `BaseCrypt`（来自 `openjiuwen.core.common.security.crypt_utils`）。

2. 定义 `NAME` 常量作为唯一标识，并在 `__init__` 中注册到系统。

   ```python
   from openjiuwen.core.common.security.crypt_utils import BaseCrypt, CryptUtils
   from common_utils.crypto_tool import CryptTool

   class MyCrypt(BaseCrypt):
       NAME = "my_crypt"

       def __init__(self):
           CryptUtils.register_crypt(self.NAME, self)

       def encrypt(self, key: bytes, origin: str) -> str:
           # 你的加密逻辑
           ...

       def decrypt(self, key: bytes, encrypt_str: str) -> str:
           # 你的解密逻辑
           ...
   ```

3. 在服务启动时完成注册并设为默认加解密实现。

**注意**：代码放置的位置要在 `from xxx_base import main as start_server` 之前

**agent-runtime**（入口 `EIStart.py`）：

   ```python
   from common_utils.crypto_tool import CryptTool
   from agent_runtime.xxx import MyCrypt

   # 初始化设置为默认加解密实现
   MyCrypt()
   CryptTool.set_default(MyCrypt.NAME)

   from EIStart_base import main as start_server
   ```

**agent-builder**（入口 `EIBuilder.py`）：

   ```python
   from common_utils.crypto_tool import CryptTool
   from agent_builder.xxx import MyCrypt

   # 初始化设置为默认加解密实现
   MyCrypt()
   CryptTool.set_default(MyCrypt.NAME)

   from EIBuilder_base import main as start_server
   ```

**业务侧使用加解密**

agent-runtime 与 agent-builder 统一引用公共工具类：

   ```python
   # 解密
   from common_utils.crypto_tool import decrypt
   plain_text = decrypt(secret_text)

   # 加密
   from common_utils.crypto_tool import encrypt
   secret_text = encrypt(plain_text)
   ```

#### 相关接口说明

| 接口 | 说明                                |
|---|-----------------------------------|
| `CryptTool.register(name, impl)` | 注册加解密实现                           |
| `CryptTool.set_default(name)` | 设置默认的加解密方式                        |
| `encrypt(data, key=None, crypt_name=None)` | 加密，传入 `crypt_name` 则用指定实现，否则用默认实现 |
| `decrypt(data, key=None, crypt_name=None)` | 解密，若解密失败（输入为明文）则返回原文              |

### studio-manager

#### 实现 Cipher 接口

1. 在 `studio-common/src/main/java/com/openjiuwen/studio/agent/common/crypt/` 目录下创建新类，实现 `Cipher` 接口。

2. 为实现分配唯一的 `name()` 字符串。

3. 在类上标注 `@Component`，Spring 会自动发现并注册到 `Ciphers` 门面中。

   ```java
   @Component
   public class AesCipher implements Cipher {

       @Override
       public String name() { return "AES"; }

       @Override
       public byte[] encrypt(String plainText, byte[] initVector) throws AgentStudioException {
           // 加密逻辑
           ...
       }

       @Override
       public String decrypt(byte[] cipherText, byte[] initVector) throws AgentStudioException {
           // 解密逻辑
           ...
       }

       @Override
       public byte[] genIV() throws AgentStudioException {
           // 生成初始向量
           ...
       }

       @Override
       public byte[] encrypt(String plainText) throws AgentStudioException {
           return encrypt(plainText, null);
       }

       @Override
       public String decrypt(byte[] cipherText) throws AgentStudioException {
           return decrypt(cipherText, null);
       }
   }
   ```

#### Ciphers 门面类方法说明

`Ciphers` 是加解密操作的统一入口，内部根据配置的默认加密器名称调用对应实现。

##### 加密方法

```java
// 使用默认加密器加密（不带向量）
String encrypt(String plainText)

// 使用默认加密器加密（带向量），当前方法为预留方法，暂未使用，可暂时忽略，实现时，直接返回空字符串即可
String encrypt(String plainText, byte[] vector)
```

**返回值说明**：返回加密后的密文字符串（UTF-8 编码的字节数组转成的字符串）。

##### 解密方法

```java
// 使用默认加密器解密（不带向量）
String decrypt(String cipherText)

// 使用默认加密器解密（带向量），当前方法为预留方法，暂未使用，可暂时忽略，实现时，直接返回空字符串即可
String decrypt(String cipherText, byte[] vector)
```

**输入说明**：`cipherText` 参数为密文字符串（UTF-8 编码）。解密时内部会将其转换为字节数组，然后调用对应加密器的 `decrypt` 方法。

##### 其他方法

```java
// 生成指定加密器的初始向量
byte[] genIV(String cipherName)
```

#### 配置默认加解密

在 YAML 配置文件中设置 `system.crypt.name` 为你的 Cipher name（如 `AES`）。如不配置，默认使用 `NO_OP_CIPHER`（透传，不加密/解密）。

---

## SSO 远程鉴权配置

本节介绍 openJiuwen Studio 服务端的 SSO 远程鉴权能力，说明如何在 studio-manager / studio-runtime 中对接客户 SSO Server 完成统一的鉴权校验。

### 功能概述

服务端可按需开启 SSO 远程鉴权：启用后，平台将请求中的鉴权 Token 转发至客户 SSO Server 校验，实现统一的身份认证。平台支持自定义鉴权字段的 Header 名称（`auth_sso_header`）以及 SSO 响应字段与平台用户属性的映射（`user_info_claims_*`），以适配不同 SSO Server 的接口约定。

配置 `auth_sso_validate_url` 后自动启用 SSO 远程鉴权，未配置则使用 Simple 本地认证（默认），两种模式互斥。

**SSO 鉴权流程：**

客户端 → 携带鉴权 Token 请求平台 → 平台提取 Token 转发 SSO Server 校验 → 校验通过放行 / 失败返回 401

> SSO Server 短暂不可用时，平台降级读取 300 秒内的 Token 缓存放行请求；无缓存或缓存过期则返回 401。Token 失效时主动清除缓存。

### 使用约束

- 仅服务端提供鉴权能力，前端 SSO 登录集成由客户自行实现
- 客户侧已部署 SSO Server 并提供鉴权接口信息（URL、请求/响应字段约定）

### 配置步骤

1. **确认 SSO 鉴权接口约定**：对照下表检查客户 SSO Server 的接口约定是否与平台默认一致。注意鉴权 Header 名称同时作用于平台提取客户端 Token 和转发至 SSO Server，需与 SSO Server 约定一致。

   | 配置项 | 默认值 | 位置 | 必需 | 环境变量 |
   |---|---|---|---|---|
   | 鉴权 Header 名称 | `Access-Token` | 请求头 | 是 | `auth_sso_header` |
   | 用户唯一标识 | `user_id` | 响应 Body | 是 | `user_info_claims_user_id` |
   | 用户名称 | `user_name` | 响应 Body | 是 | `user_info_claims_user_name` |
   | 域标识 | `domain_id` | 响应 Body | 否（缺失取 `0`） | `user_info_claims_domain_id` |
   | 域名称 | `domain_name` | 响应 Body | 否（缺失取 `0`） | `user_info_claims_domain_name` |
   | 项目标识 | `project_id` | 响应 Body | 否（缺失取 `0`） | `user_info_claims_project_id` |

   > **域名称（`domain_name`）——部署时务必确认**：平台部分功能（如团队空间「添加成员」时通过 IAM 查询用户列表）需要用域名称换取 IAM domain token，而该域名称必须是 IAM 中真实存在的域。
   > - SSO 响应中包含域名称时：把 `user_info_claims_domain_name` 配成对应字段名（默认 `domain_name`）；
   > - SSO 响应中不含该字段时：**必须**把 `user_info_defaults_domain_name` 配置为真实的 IAM 域名。
   >
   > 未配置时平台会回退到 `0`（不会抛空指针，manager 日志会打印一条 warn 提示），但 `0` 通常不是真实域名，上述依赖 IAM 的功能会调用失败、成员列表仍为空。请勿依赖该回退值。

   示例：平台默认从 SSO 响应的 `user_id` 字段提取用户唯一标识。若 SSO 响应中该字段名为 `account_id`，则需配置 `user_info_claims_user_id=account_id`。其他字段同理，与默认不一致时修改对应环境变量即可。

   > 以下配置默认无需修改，可根据实际使用调整：
   > - 域标识 / 域名称 / 项目标识缺失时的取值可通过 `user_info_defaults_domain_id`、`user_info_defaults_domain_name`、`user_info_defaults_project_id` 修改（默认 `0`）
   > - 免鉴权路径通过 `auth_path_excluded` 配置（默认 `/v1/health, /health`），多路径逗号分隔，支持 Ant 通配符（如 `/v3/**`）

2. **配置 `auth_sso_validate_url` 启用 SSO 鉴权**：将 `auth_sso_validate_url` 设置为 SSO Server 的鉴权接口 URL，步骤 1 中不一致项的环境变量同步修改，重启 studio-manager / studio-runtime 服务生效。

### 系统用户配置（可选）

配置 `auth_system_user_ids` 后，SSO 校验返回的 userId 与配置值匹配时，将跳过空间成员校验和角色权限校验，适用于流水线/自动化场景下使用固定身份调用管理类接口。

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `auth_system_user_ids` | 空（不启用） | 系统用户 ID 列表，逗号分隔。SSO 返回的 userId 匹配后跳过空间成员校验和权限校验 |

> **运维安全须知**：
> - 配置的 userId 将获得**所有已存在工作区**的无限制访问能力，跳过全部角色与权限校验，等同于全局管理员
> - Token 仅限流水线/自动化系统持有，**不下发前端用户**，建议存储于 CI/CD 密钥管理或 K8s Secret
> - **严禁**将 `auth_system_user_ids` 设为 `unknown`（SSO 未返回 userId 时的默认值），否则所有未返回 userId 的请求都会获得免校验权限
> - 系统用户仍需携带有效 SSO Token（token 失效则 401；SSO 故障时降级使用 300 秒内缓存，与普通用户一致），仍需通过 workspaceId 格式校验和空间存在性校验
> - 系统用户操作已由 `@OperationLog` 和 `@DistributedLock` 记录，可通过日志追溯

### 回退与关闭

清除环境变量 `auth_sso_validate_url` 并重启 studio-manager / studio-runtime 服务，即可回退到 Simple 本地认证模式。

---

## 存储配置与扩展

本节说明 agent-studio 三种存储模式（OBS / LOCAL / CUSTOM）的参数配置、注意事项，以及容器部署时的磁盘挂载要求。

### OBS 模式（默认）

OBS 对象存储，适用于生产环境。

#### studio-manager 配置

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `storage_type` | 是 | 设为 `OBS` |
| `obs_url` | 是 | OBS 端点地址 |
| `obs_bucket` | 是 | 业务数据桶名 |
| `obs_staging_bucket` | 是 | 暂存桶名 |
| `obs_ak` | 是 | Access Key |
| `obs_sk` | 是 | Secret Key（支持加密存储） |
| `DATASOURCE_OBS_PATH_STYLE` | 否 | 寻址方式，默认 `path`（路径风格），可选 `virtual`（虚拟托管风格） |

#### studio-builder 配置

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `STORAGE_TYPE` | 是 | 设为 `OBS` |
| `DATASOURCE_OBS_SERVER` | 是 | OBS/S3 端点地址 |
| `DATASOURCE_OBS_BUCKET` | 是 | 桶名 |
| `DATASOURCE_OBS_AK` | 是 | Access Key |
| `DATASOURCE_OBS_SK` | 是 | Secret Key（支持加密存储） |
| `DATASOURCE_OBS_ENABLE_SSL` | 否 | SSL 验证，默认 `false` |
| `DATASOURCE_OBS_PATH_STYLE` | 否 | 寻址方式，默认 `path` |

#### 注意事项

- OBS 模式无需容器磁盘挂载

### LOCAL 模式

本地文件系统存储，适用于开发测试或无 OBS 的私有化环境。

#### studio-manager 配置

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `storage_type` | 是 | 设为 `LOCAL` |
| `storage_local_base_path` | 是 | 存储根目录 |
| `storage_local_bucket` | 是 | 业务数据桶目录名 |
| `storage_local_staging_bucket` | 是 |  |
| `storage_local_server_url` | 是 | 本地下载服务地址 |

文件实际路径：`{base_path}/{bucket}/{objectKey}`。

#### agent-builder/agent-runtime 配置

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `STORAGE_TYPE` | 是 | 设为 `LOCAL` |
| `STORAGE_LOCAL_BASE_PATH` | 是 | 存储根目录 |
| `STORAGE_LOCAL_BUCKET` | 是 | 桶目录名 |

#### 注意事项

- **studio-manager 写入，agent-builder/agent-runtime 读取**。Java 侧负责 IR 上传/删除/复制等写操作，Python 侧仅做读取
- `storage_local_server_url` 用于生成下载 URL（`{serverUrl}/api/storage/download?path=xxx`），LOCAL 模式下 studio-manager 会自动注册 `StorageDownloadController` 提供下载端点
- Python 侧的 `STORAGE_LOCAL_BASE_PATH` 和 `STORAGE_LOCAL_BUCKET` 必须与 Java 侧对齐，否则文件路径不一致导致读取失败

### CUSTOM 模式

自定义存储实现，适用于需要对接非 OBS 存储（如 MinIO、Ceph、阿里云 OSS 等）的场景。

#### studio-manager 配置（Java）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `storage_type` | 是 | 设为 `CUSTOM` |
| `STORAGE_CUSTOM_CLASS` | 是 | 实现类全限定名，如 `com.example.MinioFileStore` |
| `STORAGE_CUSTOM_CLASSPATH` | 是 | 外部 JAR 路径，如 `/opt/cloud/storage-plugins/minio-storage.jar` |

**实现要求**：
1. 实现 `FileStore` 接口（`com.openjiuwen.studio.agent.common.storage.FileStore`）
2. 提供无参构造函数
3. JAR 必须是 fat jar（包含所有依赖），或把依赖 JAR 放在同一目录

#### agent-builder/agent-runtime 配置（Python）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `STORAGE_TYPE` | 是 | 设为 `CUSTOM` |
| `STORAGE_CUSTOM_MODULE` | 是 | Python 模块路径，支持两种格式（见下文） |
| `STORAGE_CUSTOM_CLASS` | 是 | 实现类名，如 `MinioStorageProvider` |

**实现要求**：
1. 继承 `ObjectStorageProvider`（`agent_runtime.common.ir_interfaces.ObjectStorageProvider`）
2. 实现抽象方法 `get_content(self, object_key: str) -> str`
3. 提供无参构造函数（`__init__` 无必需参数）
4. 可选覆写 `get_object_bytes()` / `download_to_file()` 以获得更好的性能

#### studio-manager 与 agent-builder/agent-runtime CUSTOM 配置差异

| 维度 | studio-manager（Java） | agent-builder/agent-runtime（Python） |
|------|--------------------------------------|------------------------|
| 类型配置 | `storage_type=CUSTOM` | `STORAGE_TYPE=CUSTOM` |
| 实现指定 | `STORAGE_CUSTOM_CLASS`（全限定类名） | `STORAGE_CUSTOM_CLASS`（类名） |
| 加载路径 | `STORAGE_CUSTOM_CLASSPATH`（JAR 文件路径） | `STORAGE_CUSTOM_MODULE`（.py 路径或模块名） |
| 加载机制 | `URLClassLoader` + 反射实例化 | `importlib` 动态导入 |
| Spring 注入 | 不支持（需用 `System.getenv()` 读配置） | 不支持（需用 `os.getenv()` 读配置） |
| 依赖管理 | fat jar 或同目录 JAR | pip install 或同目录 .py |
| 存储操作 | 读写全量（write/read/delete/copy/list 等） | 只读（get_content/get_object_bytes/download_to_file） |

### 容器磁盘挂载

#### LOCAL 模式

LOCAL 模式下所有容器共享宿主机存储目录，必须在 K8s Deployment 中配置 `hostPath` 挂载：

**关键要求**：
- **studio-manager、agent-builder、agent-runtime 三个服务必须挂载同一个宿主机目录**，否则跨服务读写不一致

#### CUSTOM 模式

CUSTOM 模式下外部 JAR / .py 插件文件需挂载到容器内：

**使用方式**：
- Java（studio-manager）：JAR 放宿主机 `/opt/cloud/storage-plugins/`，`STORAGE_CUSTOM_CLASSPATH` 配为 `/opt/cloud/storage-plugins/xxx.jar`
- Python（agent-builder/agent-runtime）：.py 放宿主机 `/opt/cloud/storage-plugins/`，`STORAGE_CUSTOM_MODULE` 配为 `/opt/cloud/storage-plugins/xxx`

#### 完整挂载示例

以下为 studio-manager 的完整 volumes 和 volumeMounts 配置，agent-builder 和 agent-runtime 同理：

```yaml
spec:
  template:
    spec:
      volumes:
        - name: shm-volume
          emptyDir:
            medium: Memory
            sizeLimit: 2Gi
        - name: storage-plugins
          hostPath:
            path: /opt/cloud/storage-plugins
            type: DirectoryOrCreate
        - name: storage-data
          hostPath:
            path: /data/storage
            type: DirectoryOrCreate
      containers:
        - name: container-studio-manager
          volumeMounts:
            - name: shm-volume
              mountPath: /dev/shm
            - name: storage-plugins
              mountPath: /opt/cloud/storage-plugins
              readOnly: true
            - name: storage-data
              mountPath: /data/storage
```

#### 挂载清单

| 挂载名 | 宿主机路径 | 容器内路径 | 用途 | 读写 | 必需 |
|-------|-----------|-----------|------|------|------|
| `storage-data` | `/data/storage` | `/data/storage` | LOCAL 模式共享存储 | 读写 | LOCAL 模式必需 |
| `storage-plugins` | `/opt/cloud/storage-plugins` | `/opt/cloud/storage-plugins` | CUSTOM 模式插件 JAR / .py | 只读 | CUSTOM 模式必需 |

---

## 数据库密码获取扩展

本节说明 agent-studio 数据库密码获取的抽象层设计，支持通过外部自定义实现对接 KMS、Vault 等凭据管理服务。

### 功能概述

agent-studio 将数据库密码获取逻辑抽象为 `DataSourcePasswordProvider` 接口，支持两种模式：

- **DEFAULT**（默认）：使用平台内置的加解密工具（Java 侧 `CryptoUtils`，Python 侧 `crypto_tool`）解密配置文件中的密文密码
- **CUSTOM**：通过外部 JAR（Java）或 .py 文件（Python）加载自定义实现，可对接 KMS、Vault、云凭据管理等外部服务

### DEFAULT 模式（默认）

默认模式下，平台使用内置加解密能力处理数据库密码：

- **studio-manager（Java）**：`DefaultDataSourcePasswordProvider` 调用 `CryptoUtils.decrypt()` 解密 `spring.datasource.password` 配置值
- **agent-builder（Python）**：`DefaultDataSourcePasswordProvider` 调用 `crypto_tool.decrypt()` 解密 `STORE_DB_PASSWORD` 环境变量值

> DEFAULT 模式无需额外配置，只要不设置 `DATASOURCE_PASSWORD_PROVIDER_TYPE` 或设为 `DEFAULT` 即可。

### CUSTOM 模式

自定义密码获取实现，适用于需要对接 KMS、Vault 等外部凭据管理服务的场景。

#### studio-manager 配置（Java）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `datasource_password_provider_type` | 是 | 设为 `CUSTOM` |
| `datasource_password_provider_custom_class` | 是 | 实现类全限定名，如 `com.example.KmsPasswordProvider` |
| `datasource_password_provider_custom_classpath` | 是 | 外部 JAR 路径，如 `/opt/cloud/plugins/kms-password-provider.jar` |

**实现要求**：
1. 实现 `DataSourcePasswordProvider` 接口（`com.openjiuwen.studio.agent.common.datasource.DataSourcePasswordProvider`）
2. 提供无参构造函数
3. JAR 必须是 fat jar（包含所有依赖），或把依赖 JAR 放在同一目录

   ```java
   public class KmsPasswordProvider implements DataSourcePasswordProvider {

       @Override
       public String getPassword(String rawPassword) {
           // rawPassword 为配置文件中的原始值（可能为密文引用，也可能为空）
           // 在此调用 KMS/Vault API 获取明文密码并返回
           return fetchFromKms(rawPassword);
       }
   }
   ```

#### agent-builder 配置（Python）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `DATASOURCE_PASSWORD_PROVIDER_TYPE` | 是 | 设为 `CUSTOM` |
| `DATASOURCE_PASSWORD_PROVIDER_MODULE` | 是 | Python 模块路径，支持两种格式（见下文） |
| `DATASOURCE_PASSWORD_PROVIDER_CLASS` | 是 | 实现类名，如 `KmsPasswordProvider` |

**实现要求**：
1. 继承 `DataSourcePasswordProvider`（`common_utils.password_provider.DataSourcePasswordProvider`）
2. 实现抽象方法 `get_password(self, raw_password: str) -> str`
3. 提供无参构造函数（`__init__` 无必需参数）

   ```python
   from common_utils.password_provider import DataSourcePasswordProvider

   class KmsPasswordProvider(DataSourcePasswordProvider):

       def get_password(self, raw_password: str) -> str:
           # raw_password 为环境变量中的原始值
           # 在此调用 KMS/Vault API 获取明文密码并返回
           return self._fetch_from_kms(raw_password)
   ```

#### CUSTOM 配置差异：studio-manager vs agent-builder

| 维度 | studio-manager（Java） | agent-builder（Python） |
|------|------------------------|----------------------------------------|
| 类型配置 | `datasource_password_provider_type=CUSTOM` | `DATASOURCE_PASSWORD_PROVIDER_TYPE=CUSTOM` |
| 实现指定 | `datasource_password_provider_custom_class`（全限定类名） | `DATASOURCE_PASSWORD_PROVIDER_CLASS`（类名） |
| 加载路径 | `datasource_password_provider_custom_classpath`（JAR 文件路径） | `DATASOURCE_PASSWORD_PROVIDER_MODULE`（.py 路径或模块名） |
| 加载机制 | `URLClassLoader` + 反射实例化 + Spring 依赖注入 | `importlib` 动态导入 |
| Spring 注入 | 支持（`@Autowired` / `@Value` 可用） | 不支持（需用 `os.getenv()` 读配置） |
| 依赖管理 | fat jar 或同目录 JAR | pip install 或同目录 .py |

> **`DATASOURCE_PASSWORD_PROVIDER_MODULE` 支持两种格式**：
> - 文件路径：`/opt/cloud/plugins/custom_password_provider`（自动补 `.py` 后缀）
> - 模块名：`my_package.custom_provider`（需已安装到 site-packages）

### 接口定义

#### Java 接口

```java
public interface DataSourcePasswordProvider {

    /**
     * 获取数据库密码（明文）。
     *
     * @param rawPassword 配置文件中的原始密码（可能为加密密文，也可能为明文）
     * @return 解密后的明文密码
     */
    String getPassword(String rawPassword);
}
```

#### Python 抽象基类

```python
from abc import ABC, abstractmethod

class DataSourcePasswordProvider(ABC):

    @abstractmethod
    def get_password(self, raw_password: str) -> str:
        """获取数据库密码（明文）。

        Args:
            raw_password: 配置文件中的原始密码（可能为加密密文，也可能为明文）

        Returns:
            解密后的明文密码
        """
        ...
```

### 容器部署

CUSTOM 模式下外部 JAR / .py 插件文件需挂载到容器内，方式与存储扩展的 CUSTOM 模式一致：

- **Java（studio-manager）**：JAR 放宿主机 `/opt/cloud/plugins/`，`datasource_password_provider_custom_classpath` 配为 `/opt/cloud/plugins/xxx.jar`
- **Python（agent-builder）**：.py 放宿主机 `/opt/cloud/plugins/`，`DATASOURCE_PASSWORD_PROVIDER_MODULE` 配为 `/opt/cloud/plugins/xxx`

K8s Deployment 挂载示例：

```yaml
spec:
  template:
    spec:
      volumes:
        - name: password-plugins
          hostPath:
            path: /opt/cloud/plugins
            type: DirectoryOrCreate
      containers:
        - name: container-studio-manager
          volumeMounts:
            - name: password-plugins
              mountPath: /opt/cloud/plugins
              readOnly: true
```

> 也可复用存储扩展的 `storage-plugins` 挂载目录，将密码获取插件 JAR / .py 一并放入。

### 回退与关闭

将 `DATASOURCE_PASSWORD_PROVIDER_TYPE`（Python 侧）或 `datasource_password_provider_type`（Java 侧）设为 `DEFAULT` 或清除该环境变量，重启服务即可回退到默认本地解密模式。

---

## Redis 适配配置与扩展

本节说明 agent-studio 的 Redis 适配层：内置缺省实现（Java 侧 Redisson、Python 侧 redis-py 原生实现）的连接配置，以及企业自研 Provider 的插件化装配方式（对接自研 Redis 代理、云厂商专有 Redis 等）。适配方式与[存储配置与扩展](#存储配置与扩展)、[数据库密码获取扩展](#数据库密码获取扩展)同构。

### 功能概述

Redis 访问在两侧均为 **SPI 抽象 + 可插拔 Provider** 架构：

- **studio-manager（Java）**：`studio-redis-spi` 模块定义 `RedisClient` 接口、`RedisProviderFactory` 工厂接口与 `RedisExceptionClassifier` 异常族；`studio-redis-redisson` 模块提供缺省 Redisson 实现、内存实现（测试用）与统一装配入口 `RedisProviderResolver`
- **agent-builder / agent-runtime（Python）**：`packages/redis_spi` 包定义 `RedisProvider` 基类与 `RedisClient` 协议；`packages/redis_native` 包提供基于 redis-py 的缺省实现（native）

装配解析优先级两侧对齐：**显式指定实现 > 自动发现（ServiceLoader / entry_points）> 内置缺省**。缺省装配已通过启动期连接校验（fail-fast），不配置任何 Provider 项即为既有行为。

### 缺省装配（默认）

默认无需任何 Provider 配置，仅需连接参数。

#### studio-manager 配置（Java）

| 配置项 | 必填 | 说明 |
|-------|------|------|
| `redis.host` | 是 | Redis 地址 |
| `redis.port` | 是 | 端口 |
| `redis.password` | 否 | 密码 |
| `redis.cluster_node_list` | 集群模式 | 集群节点列表（`host:port` 逗号分隔） |
| `redis.master` + `redis.sentinel_ports` | 哨兵模式 | 哨兵 master 名与哨兵端口列表 |
| `redis.connection.pool.size` | 否 | 连接池大小，默认 `64` |
| `redis.connection.minimum.idle.size` | 否 | 最小空闲连接，默认 `24` |

#### agent-builder / agent-runtime 配置（Python）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `REDIS_HOST` | 是 | 默认 `127.0.0.1` |
| `REDIS_PORT` | 是 | 默认 `6379` |
| `REDIS_PASSWORD` | 否 | 密码 |
| `REDIS_MODE` | 否 | `single`（默认）/ `cluster` / `sentinel` |
| `REDIS_DATABASE` | 否 | 默认 `0` |
| `REDIS_CLUSTER_NODES` | `cluster` 模式 | 节点列表 |
| `REDIS_SENTINEL_MASTER` + `REDIS_SENTINEL_NODES` | `sentinel` 模式 | master 名与节点列表 |
| `REDIS_MAX_CONNECTIONS` | 否 | 连接池上限，默认 `50` |
| `REDIS_SOCKET_TIMEOUT` / `REDIS_SOCKET_CONNECT_TIMEOUT` | 否 | 超时（秒），默认 `5.0` |
| `REDIS_SSL_ENABLED` | 否 | 默认 `false` |
| `REDIS_TRANSACTION_ENABLED` | 否 | 事务管道，默认 `true` |

### CUSTOM 模式（自定义 Provider）

适用于对接非标准 Redis（自研代理、云厂商专有协议等）的场景。

#### studio-manager 配置（Java）

| 配置项 | 必填 | 说明 |
|-------|------|------|
| `redis.client-type` | 是 | 设为 `custom`（ServiceLoader 自动发现）；也可不设，直接用 `redis.provider-class` 显式指定 |
| `redis.provider-class` | 否 | 实现类全限定类名（如 `com.acme.NosProviderFactory`）或 ServiceLoader 注册名 |
| `redis.provider-config` | 否 | Provider 专属参数（内联），框架不解析内部字段 |
| `redis.provider-config-file` | 否 | Provider 专属参数文件路径（替代内联） |

**实现要求**（三选一，推荐 A）：

A. 实现 `RedisProviderFactory`（推荐）——框架调用 `create(RedisProviderContext)` 创建客户端：

```java
public class NosProviderFactory implements RedisProviderFactory {

    @Override
    public RedisClient create(RedisProviderContext context) {
        // context 携带连接参数、集群/哨兵配置与企业专属参数透传
        return new NosRedisClient(context);
    }
}
```

B. 直接实现 `RedisClient`，提供无参构造 + `void init(RedisProviderContext)` 方法
C. 兼容旧接缝：保留 `(String host, String password, int port)` 三参构造器（过渡期）

**ServiceLoader 注册**（`client-type=custom` 自动发现时需要）：在插件 JAR 内添加
`META-INF/services/com.openjiuwen.studio.agent.common.redis.spi.RedisProviderFactory`，内容为实现类全限定名。classpath 上仅有一个 Provider 时自动选取，多个时需 `redis.provider-class` 指明。

> **与存储/密码插件的差异**：存储与密码扩展支持 `URLClassLoader` 加载外部 JAR（`STORAGE_CUSTOM_CLASSPATH` 等）；Redis Provider 类需位于应用 classpath——插件 JAR 放入 studio-manager 部署目录的 `lib/` 即可（Spring Boot `loader.path` 加载）。

#### agent-builder / agent-runtime 配置（Python）

| 环境变量 | 必填 | 说明 |
|---------|------|------|
| `REDIS_PROVIDER` | 是 | `文件路径:类名`（如 `/opt/cloud/plugins/nos_provider.py:NosProvider`）或已安装模块名；`native` 为内置保留名，不可被同名插件覆盖 |
| `REDIS_PROVIDER_CLASS` | 与上配合 | 类名（`REDIS_PROVIDER` 为模块名形态时使用） |
| `REDIS_PROVIDER_CONFIG` | 否 | Provider 专属参数（JSON 对象），经 `settings.raw_provider_config()` 透传 |
| `REDIS_PROVIDER_CONFIG_FILE` | 否 | 参数文件路径（替代内联 JSON） |

**实现要求**：

1. 继承 `RedisProvider`（`redis_spi.factory.RedisProvider`）
2. 实现 `async start(settings) -> RedisClient` 与 `async stop()`——连接必须在 `start()` 内延迟建立（模块需可在无 Redis 连接的环境下 import）
3. 可选覆写 `capabilities()`（声明支持的扩展能力组）与 `native_client()`（暴露底层客户端）

```python
from redis_spi.factory import RedisProvider
from redis_spi.config import RedisProviderSettings


class NosProvider(RedisProvider):

    async def start(self, settings: RedisProviderSettings):
        # settings.raw_provider_config() 透传 REDIS_PROVIDER_CONFIG 企业专属参数
        return await build_nos_client(settings)

    async def stop(self) -> None:
        ...
```

装配后 ping fail-fast：连接不通立即报错并回收 Provider，不留半初始化状态。

#### CUSTOM 配置差异：studio-manager vs agent-builder / agent-runtime

| 维度 | studio-manager（Java） | agent-builder / agent-runtime（Python） |
|------|------------------------|----------------------------------------|
| 类型配置 | `redis.client-type=custom` | `REDIS_PROVIDER=<模块:类>` |
| 实现指定 | `redis.provider-class`（全限定类名 / ServiceLoader 注册名） | `REDIS_PROVIDER_CLASS`（类名） |
| 加载机制 | `ServiceLoader` / classpath 反射 | `importlib` 动态导入（文件路径或模块名） |
| 发行包注册 | `META-INF/services` 声明 | entry_points 注册表 |
| 企业专属参数 | `redis.provider-config`（经 `RedisProviderContext` 透传） | `REDIS_PROVIDER_CONFIG`（JSON 透传） |
| 装配校验 | Resolver 解析失败报错并列出全部可用实现名 | 装配后 ping fail-fast，失败回收 Provider |
| Spring 注入 | 不支持（经 `RedisProviderContext` 读配置） | 不支持（`os.getenv()` / settings 读配置） |

> **`REDIS_PROVIDER` 支持两种形态**：
> - 文件路径（可带 `:类名` 后缀）：`/opt/cloud/plugins/nos_provider`（自动补 `.py`）或 `/opt/cloud/plugins/nos_provider.py:NosProvider`
> - 模块名（需已安装）：`my_package.nos_provider`（配合 `REDIS_PROVIDER_CLASS=NosProvider`）

### 接口定义

#### Java 接口（studio-redis-spi）

```java
public interface RedisProviderFactory {

    /**
     * 创建 Redis 客户端实例。
     *
     * @param context 配置上下文（连接参数 + 集群/哨兵配置 + 企业专属参数透传）
     * @return RedisClient 客户端实例
     * @throws RedisProviderException 创建失败（配置缺失、连接不通等）
     */
    RedisClient create(RedisProviderContext context);
}
```

`RedisClient`（`com.openjiuwen.studio.agent.common.redis.RedisClient`）定义字符串/哈希/列表/集合等读写命令与 `RedisLock` 锁语义；不支持的能力抛 `CapabilityUnsupportedException`，访问异常经 `RedisExceptionClassifier` 归一为 `RedisAccessException` 分类族（连接失败/超时/类型错误/命令错误）。

#### Python 抽象基类（packages/redis_spi）

```python
class RedisProvider(ABC):

    @abstractmethod
    async def start(self, settings: RedisProviderSettings) -> RedisClient:
        """创建并返回客户端（含连接池初始化）。"""

    @abstractmethod
    async def stop(self) -> None:
        """回收全部资源。"""

    def capabilities(self) -> list[type]:
        """声明支持的可选能力组（capabilities.py 中的 Protocol 类）。默认无。"""

    def native_client(self) -> Any:
        """暴露底层原生客户端（过渡期兼容注入）。默认不支持。"""
```

`RedisClient` 为 `redis_spi.protocols` 中的分能力 `Protocol` 组合（`KeyCommands` / `StringCommands` / `HashCommands` / `ListCommands` / `SetCommands` / `ScanCommands` / `Pipeline` 等，扩展能力见 `capabilities.py`）。

### 升级注意事项（自旧 DATASOURCE_REDIS 体系升级）

| 变化点 | 旧行为 | 新行为 | 升级动作 |
|-------|--------|--------|---------|
| **配置面合并** | 意图识别/记忆走独立的 `DATASOURCE_REDIS_*`（可指向独立实例/db） | 统一并入 `REDIS_*`（同一 `RedisProviderSettings`） | 原本 `DATASOURCE_REDIS_HOST` 与 `REDIS_HOST` **指向不同实例/db** 的部署，升级后这些数据将读空（按默认值降级）——须把数据迁入统一实例，或将 `REDIS_*` 指向原独立实例 |
| **builder 启动语义** | Redis ping 失败 warn-and-continue | 装配期 ping fail-fast 终止进程（半可用慢性故障显式失败更可运维，与 runtime 一致） | 无 Redis 的 builder 环境须先部署 Redis（平台声明的必选依赖）或保持旧版本 |
| **哨兵节点密码** | `REDIS_SENTINEL_PASSWORD`（哨兵自身认证，与数据节点密码独立；旧体系对该值走 crypto 解密） | 已建模为 `RedisProviderSettings.sentinel_password`（同名环境变量）；**按原值透传，不做解密** | 哨兵集群启用 requirepass 的部署确认该变量已透传，且**存储形态须为明文**——若以密文存储，装配期将得到明确连接错误（fail-fast，非静默） |

### 回退与关闭

删除 Provider 相关配置（Java 侧 `redis.client-type` / `redis.provider-class` / `redis.provider-config*`，Python 侧 `REDIS_PROVIDER*`），重启服务即回退缺省实现（Java=Redisson，Python=native）。

---

## 自定义插件开发

当现有 HTTP API 插件无法满足需求（如数据库直连、文件处理、画布交互、本地计算等非 HTTP 场景）时，平台支持开发自定义 Python 插件，通过 Schema 驱动表单 + 自定义执行逻辑实现扩展能力。

详见 [自定义插件开发指南](./custom-plugin-development-guide.md)，包含插件结构、Python 接口契约、SQL 规范、集成方式和自查 Checklist。
