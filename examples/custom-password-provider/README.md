# custom-password-provider — 自定义数据库密码获取

通过实现 `DataSourcePasswordProvider` 接口自定义数据库密码获取方式，支持对接 KMS、Vault、K8s Secret 等外部凭据管理服务。Java 侧和 Python 侧均提供示例实现。

## 适用场景

- 数据库密码通过 K8s Secret 以环境变量注入，配置文件中不存储明文密码
- 密码托管在 HashiCorp Vault、华为云 KMS 等外部密钥管理系统，启动时动态拉取
- 密码需要经过自定义加解密逻辑处理后再使用

## 配置项

### Python 侧

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `DATASOURCE_PASSWORD_PROVIDER_TYPE` | 否 | `DEFAULT` | 密码获取方式：`DEFAULT`（本地解密）/ `CUSTOM`（自定义实现） |
| `DATASOURCE_PASSWORD_PROVIDER_MODULE` | CUSTOM 时必填 | — | 自定义实现模块路径（`.py` 文件路径或已安装的 Python 模块名） |
| `DATASOURCE_PASSWORD_PROVIDER_CLASS` | CUSTOM 时必填 | — | 自定义实现类名（须继承 `DataSourcePasswordProvider`） |

### Java 侧

| 环境变量 | 必填 | 默认值 | 说明 |
|----------|------|--------|------|
| `datasource_password_provider_type` | 否 | `DEFAULT` | 密码获取方式：`DEFAULT`（本地解密）/ `CUSTOM`（自定义实现） |
| `datasource_password_provider_custom_class` | CUSTOM 时必填 | — | 自定义实现类全限定名（须实现 `DataSourcePasswordProvider`） |
| `datasource_password_provider_custom_classpath` | CUSTOM 时必填 | — | 外部 JAR 路径，多个用路径分隔符分隔 |

> `type` 大小写敏感，仅接受全大写 `DEFAULT` / `CUSTOM`，非法值会导致启动失败。

## 示例说明

两侧 `EnvPasswordProvider` 实现逻辑一致：从环境变量 `DB_REAL_PASSWORD` 获取数据库密码，模拟容器化部署中通过 K8s Secret 注入密码的场景。

| 文件 | 说明 |
|------|------|
| `custom_password_provider.py` | Python 侧 `EnvPasswordProvider` 实现 |
| `java/pom.xml` | Java 侧 Maven 构建文件 |
| `java/src/main/java/.../EnvPasswordProvider.java` | Java 侧 `EnvPasswordProvider` 实现 |

## Python 侧运行

> 以下命令需使用已安装项目依赖的 Python 环境。

### 1. 集成到服务

将 `custom_password_provider.py` 部署到任意目录，设置环境变量后启动服务：

```bash
export DATASOURCE_PASSWORD_PROVIDER_TYPE=CUSTOM
export DATASOURCE_PASSWORD_PROVIDER_MODULE=/opt/plugins/custom_password_provider.py
export DATASOURCE_PASSWORD_PROVIDER_CLASS=EnvPasswordProvider
export DB_REAL_PASSWORD=your_real_password
export STORE_DB_HOST=your_db_host
export STORE_DB_USER=your_db_user
export STORE_DB_PASSWORD=placeholder
export STORE_DB_DATABASE=your_db_name
# 启动服务...
```

## Java 侧运行

> 以下命令需确保 `JAVA_HOME` 指向 **JDK 17+**。

### 1. 编译 studio-storage 模块（生成依赖 JAR）

```bash
cd backend
mvn package -pl studio-storage -am -DskipTests
# 产出 studio-storage/target/studio-storage-0.0.1.jar
cd ..
```

### 2. 编译打包示例 JAR

```bash
cd examples/custom-password-provider/java
mkdir -p target/classes
javac -encoding UTF-8 \
  -cp ../../../backend/studio-storage/target/studio-storage-0.0.1.jar \
  -d target/classes \
  src/main/java/com/openjiuwen/studio/examples/EnvPasswordProvider.java
jar cf target/custom-password-provider.jar -C target/classes .
# 产出 target/custom-password-provider.jar
cd ../../..
```

### 3. 配置并启动服务

将 JAR 部署到 `/opt/plugins/`，设置环境变量后启动服务：

```bash
export datasource_password_provider_type=CUSTOM
export datasource_password_provider_custom_class=com.openjiuwen.studio.examples.EnvPasswordProvider
export datasource_password_provider_custom_classpath=/opt/plugins/custom-password-provider.jar
export DB_REAL_PASSWORD=your_real_password
export spring_datasource_url=jdbc:mysql://your_db_host:3306/your_db_name
export spring_datasource_username=your_db_user
export spring_datasource_password=placeholder
# 启动 Java 服务...
```

## 自定义实现指南

### Python 侧

1. 继承 `DataSourcePasswordProvider` 并实现 `get_password` 方法：

```python
from common_utils.password_provider import DataSourcePasswordProvider

class MyPasswordProvider(DataSourcePasswordProvider):
    def get_password(self, raw_password: str) -> str:
        # 自定义逻辑：从 Vault/KMS/环境变量等获取密码
        return fetch_from_vault()
```

2. 设置环境变量指向你的实现：

```bash
export DATASOURCE_PASSWORD_PROVIDER_TYPE=CUSTOM
export DATASOURCE_PASSWORD_PROVIDER_MODULE=/path/to/your_provider.py
export DATASOURCE_PASSWORD_PROVIDER_CLASS=MyPasswordProvider
```

### Java 侧

1. 实现 `DataSourcePasswordProvider` 接口：

```java
import com.openjiuwen.studio.agent.common.datasource.DataSourcePasswordProvider;

public class MyPasswordProvider implements DataSourcePasswordProvider {
    @Override
    public String getPassword(String rawPassword) {
        // 自定义逻辑：从 Vault/KMS/环境变量等获取密码
        return fetchFromVault();
    }
}
```

2. 打包为 JAR，设置环境变量：

```bash
export datasource_password_provider_type=CUSTOM
export datasource_password_provider_custom_class=com.example.MyPasswordProvider
export datasource_password_provider_custom_classpath=/path/to/your-provider.jar
```

## 两侧对齐

| 维度 | Java 侧 | Python 侧 |
|------|---------|-----------|
| 接口 | `DataSourcePasswordProvider` 接口 | `DataSourcePasswordProvider` ABC |
| 默认实现 | `DefaultDataSourcePasswordProvider`（CryptoUtils 解密） | `DefaultDataSourcePasswordProvider`（crypto_tool.decrypt） |
| 自定义加载 | 外部 JAR + `ExternalJarLoader` 反射实例化 | `.py` 文件 / 模块名 + `importlib` 动态加载 |
| 配置项 | `datasource_password_provider_type` | `DATASOURCE_PASSWORD_PROVIDER_TYPE` |
| 非法值行为 | 无 Bean 激活 → 注入失败 → 启动失败 | Pydantic Literal 校验 → 启动失败 |
