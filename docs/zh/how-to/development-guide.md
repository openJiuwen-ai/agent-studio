# 开发指南

本指南涵盖 agent-studio 项目的各项开发扩展能力。

## 目录

- [加解密扩展](#加解密扩展)
- [SSO 远程鉴权配置](#sso-远程鉴权配置)
- [存储配置与扩展](#存储配置与扩展)
- [数据库密码获取扩展](#数据库密码获取扩展)

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
   | 项目标识 | `project_id` | 响应 Body | 否（缺失取 `0`） | `user_info_claims_project_id` |

   示例：平台默认从 SSO 响应的 `user_id` 字段提取用户唯一标识。若 SSO 响应中该字段名为 `account_id`，则需配置 `user_info_claims_user_id=account_id`。其他字段同理，与默认不一致时修改对应环境变量即可。

   > 以下配置默认无需修改，可根据实际使用调整：
   > - 域标识 / 项目标识缺失时的取值可通过 `user_info_defaults_domain_id`、`user_info_defaults_project_id` 修改（默认 `0`）
   > - 免鉴权路径通过 `auth_path_excluded` 配置（默认 `/v1/health, /health`），多路径逗号分隔，支持 Ant 通配符（如 `/v3/**`）

2. **配置 `auth_sso_validate_url` 启用 SSO 鉴权**：将 `auth_sso_validate_url` 设置为 SSO Server 的鉴权接口 URL，步骤 1 中不一致项的环境变量同步修改，重启 studio-manager / studio-runtime 服务生效。

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
- **agent-runtime / agent-builder（Python）**：`DefaultDataSourcePasswordProvider` 调用 `crypto_tool.decrypt()` 解密 `STORE_DB_PASSWORD` 环境变量值

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

#### agent-builder / agent-runtime 配置（Python）

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

#### CUSTOM 配置差异：studio-manager vs agent-builder / agent-runtime

| 维度 | studio-manager（Java） | agent-builder / agent-runtime（Python） |
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
- **Python（agent-builder / agent-runtime）**：.py 放宿主机 `/opt/cloud/plugins/`，`DATASOURCE_PASSWORD_PROVIDER_MODULE` 配为 `/opt/cloud/plugins/xxx`

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
