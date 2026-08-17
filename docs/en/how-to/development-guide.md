# Development Guide

This guide covers the various development and extension capabilities of the agent-studio project.

## Table of Contents

- [Encryption Extension](#encryption-extension)
- [SSO Remote Auth Configuration](#sso-remote-auth-configuration)
- [Storage Configuration and Extension](#storage-configuration-and-extension)
- [Database Password Provider Extension](#database-password-provider-extension)

---

## Encryption Extension

This document describes how to extend encryption/decryption implementations in agent-runtime, agent-builder, and studio-manager.

### agent-runtime / agent-builder

#### Implement Encryption Class by Inheriting BaseCrypt

1. Create a new class inheriting `BaseCrypt` (from `openjiuwen.core.common.security.crypt_utils`).

2. Define the `NAME` constant as a unique identifier, and register it in the system in `__init__`.

   ```python
   from openjiuwen.core.common.security.crypt_utils import BaseCrypt, CryptUtils
   from common_utils.crypto_tool import CryptTool

   class MyCrypt(BaseCrypt):
       NAME = "my_crypt"

       def __init__(self):
           CryptUtils.register_crypt(self.NAME, self)

       def encrypt(self, key: bytes, origin: str) -> str:
           # your encryption logic
           ...

       def decrypt(self, key: bytes, encrypt_str: str) -> str:
           # your decryption logic
           ...
   ```

3. Complete registration and set as default encryption implementation on service startup.

**Note**: The code placement must be before `from xxx_base import main as start_server`

**agent-runtime** (entry `EIStart.py`):

   ```python
   from common_utils.crypto_tool import CryptTool
   from agent_runtime.xxx import MyCrypt

   # Initialize and set as default encryption implementation
   MyCrypt()
   CryptTool.set_default(MyCrypt.NAME)

   from EIStart_base import main as start_server
   ```

**agent-builder** (entry `EIBuilder.py`):

   ```python
   from common_utils.crypto_tool import CryptTool
   from agent_builder.xxx import MyCrypt

   # Initialize and set as default encryption implementation
   MyCrypt()
   CryptTool.set_default(MyCrypt.NAME)

   from EIBuilder_base import main as start_server
   ```

**Business-side Encryption Usage**

agent-runtime and agent-builder both use the common utility class:

   ```python
   # decrypt
   from common_utils.crypto_tool import decrypt
   plain_text = decrypt(secret_text)

   # encrypt
   from common_utils.crypto_tool import encrypt
   secret_text = encrypt(plain_text)
   ```

#### Related Interface Description

| Interface | Description |
|---|---|
| `CryptTool.register(name, impl)` | Register encryption implementation |
| `CryptTool.set_default(name)` | Set default encryption method |
| `encrypt(data, key=None, crypt_name=None)` | Encrypt; if `crypt_name` is passed, uses the specified implementation; otherwise uses default |
| `decrypt(data, key=None, crypt_name=None)` | Decrypt; if decryption fails (input is plaintext), returns the original text |

### studio-manager

#### Implement Cipher Interface

1. Create a new class in the `studio-common/src/main/java/com/openjiuwen/studio/agent/common/crypt/` directory, implementing the `Cipher` interface.

2. Assign a unique `name()` string to the implementation.

3. Annotate the class with `@Component`; Spring will auto-discover and register it in the `Ciphers` facade.

   ```java
   @Component
   public class AesCipher implements Cipher {

       @Override
       public String name() { return "AES"; }

       @Override
       public byte[] encrypt(String plainText, byte[] initVector) throws AgentStudioException {
           // encryption logic
           ...
       }

       @Override
       public String decrypt(byte[] cipherText, byte[] initVector) throws AgentStudioException {
           // decryption logic
           ...
       }

       @Override
       public byte[] genIV() throws AgentStudioException {
           // generate initialization vector
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

#### Ciphers Facade Class Method Description

`Ciphers` is the unified entry point for encryption/decryption operations; it internally calls the corresponding implementation based on the configured default cipher name.

##### Encrypt Methods

```java
// Encrypt using default cipher (without vector)
String encrypt(String plainText)

// Encrypt using default cipher (with vector); currently a reserved method, not yet used; can be ignored — return empty string in implementation
String encrypt(String plainText, byte[] vector)
```

**Return value description**: Returns the encrypted ciphertext string (string converted from UTF-8 encoded byte array).

##### Decrypt Methods

```java
// Decrypt using default cipher (without vector)
String decrypt(String cipherText)

// Decrypt using default cipher (with vector); currently a reserved method, not yet used; can be ignored — return empty string in implementation
String decrypt(String cipherText, byte[] vector)
```

**Input description**: The `cipherText` parameter is a ciphertext string (UTF-8 encoded). During decryption, it is internally converted to a byte array, then the corresponding cipher's `decrypt` method is called.

##### Other Methods

```java
// Generate initialization vector for the specified cipher
byte[] genIV(String cipherName)
```

#### Configure Default Encryption

Set `system.crypt.name` to your Cipher name (e.g. `AES`) in the YAML config file. If not configured, `NO_OP_CIPHER` (passthrough, no encryption/decryption) is used by default.

---

## SSO Remote Auth Configuration

This section describes the SSO remote auth capability of the openJiuwen Studio server-side, explaining how to integrate with the customer's SSO Server in studio-manager / studio-runtime for unified auth verification.

### Feature Overview

The server-side can enable SSO remote auth on demand: when enabled, the platform forwards the auth Token in the request to the customer's SSO Server for verification, achieving unified identity authentication. The platform supports custom auth field Header name (`auth_sso_header`) and mapping of SSO response fields to platform user attributes (`user_info_claims_*`), to adapt to different SSO Server interface conventions.

Configuring `auth_sso_validate_url` automatically enables SSO remote auth; if not configured, Simple local auth (default) is used; the two modes are mutually exclusive.

**SSO Auth Flow:**

Client → sends request with auth Token to platform → platform extracts Token and forwards to SSO Server for verification → pass: allow / fail: return 401

> When the SSO Server is briefly unavailable, the platform degrades to read Token cache within 300 seconds to allow requests; if no cache or cache expired, returns 401. Token cache is proactively cleared when the Token is invalidated.

### Usage Constraints

- Only the server-side provides auth capability; frontend SSO login integration is implemented by the customer
- The customer has deployed an SSO Server and provided auth interface info (URL, request/response field conventions)

### Configuration Steps

1. **Confirm SSO auth interface conventions**: Check the table below to verify whether the customer's SSO Server interface conventions match the platform defaults. Note that the auth Header name applies to both the platform extracting the client Token and forwarding to the SSO Server; it must be consistent with the SSO Server convention.

   | Config item | Default | Location | Required | Environment variable |
   |---|---|---|---|---|
   | Auth Header name | `Access-Token` | Request header | Yes | `auth_sso_header` |
   | User unique identifier | `user_id` | Response body | Yes | `user_info_claims_user_id` |
   | User name | `user_name` | Response body | Yes | `user_info_claims_user_name` |
   | Domain identifier | `domain_id` | Response body | No (defaults to `0` if missing) | `user_info_claims_domain_id` |
   | Project identifier | `project_id` | Response body | No (defaults to `0` if missing) | `user_info_claims_project_id` |

   Example: The platform by default extracts the user unique identifier from the `user_id` field in the SSO response. If the field is named `account_id` in the SSO response, configure `user_info_claims_user_id=account_id`. The same applies to other fields; modify the corresponding environment variable when inconsistent with defaults.

   > The following configurations generally do not need modification but can be adjusted as needed:
   > - Values when domain/project identifiers are missing can be modified via `user_info_defaults_domain_id`, `user_info_defaults_project_id` (default `0`)
   > - Auth-exempt paths via `auth_path_excluded` config (default `/v1/health, /health`), multiple paths comma-separated, supports Ant wildcards (e.g. `/v3/**`)

2. **Configure `auth_sso_validate_url` to enable SSO auth**: Set `auth_sso_validate_url` to the SSO Server's auth interface URL; modify environment variables for any inconsistent items in Step 1; restart studio-manager / studio-runtime services to take effect.

### Rollback and Disable

Clear the `auth_sso_validate_url` environment variable and restart the studio-manager / studio-runtime services to roll back to Simple local auth mode.

---

## Storage Configuration and Extension

This section describes the parameter configuration, considerations, and container disk mount requirements for the three storage modes (OBS / LOCAL / CUSTOM) of agent-studio.

### OBS Mode (Default)

OBS object storage, suitable for production environments.

#### studio-manager Configuration

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `storage_type` | Yes | Set to `OBS` |
| `obs_url` | Yes | OBS endpoint address |
| `obs_bucket` | Yes | Business data bucket name |
| `obs_staging_bucket` | Yes | Staging bucket name |
| `obs_ak` | Yes | Access Key |
| `obs_sk` | Yes | Secret Key (supports encrypted storage) |
| `DATASOURCE_OBS_PATH_STYLE` | No | Addressing style, default `path` (path-style), optional `virtual` (virtual-hosted-style) |

#### studio-builder Configuration

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `STORAGE_TYPE` | Yes | Set to `OBS` |
| `DATASOURCE_OBS_SERVER` | Yes | OBS/S3 endpoint address |
| `DATASOURCE_OBS_BUCKET` | Yes | Bucket name |
| `DATASOURCE_OBS_AK` | Yes | Access Key |
| `DATASOURCE_OBS_SK` | Yes | Secret Key (supports encrypted storage) |
| `DATASOURCE_OBS_ENABLE_SSL` | No | SSL verification, default `false` |
| `DATASOURCE_OBS_PATH_STYLE` | No | Addressing style, default `path` |

#### Notes

- OBS mode does not require container disk mounting

### LOCAL Mode

Local file system storage, suitable for development/testing or private deployment environments without OBS.

#### studio-manager Configuration

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `storage_type` | Yes | Set to `LOCAL` |
| `storage_local_base_path` | Yes | Storage root directory |
| `storage_local_bucket` | Yes | Business data bucket directory name |
| `storage_local_staging_bucket` | Yes | Staging bucket directory name |
| `storage_local_server_url` | Yes | Local download service address |

Actual file path: `{base_path}/{bucket}/{objectKey}`.

#### agent-builder/agent-runtime Configuration

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `STORAGE_TYPE` | Yes | Set to `LOCAL` |
| `STORAGE_LOCAL_BASE_PATH` | Yes | Storage root directory |
| `STORAGE_LOCAL_BUCKET` | Yes | Bucket directory name |

#### Notes

- **studio-manager writes, agent-builder/agent-runtime reads**. The Java side handles IR upload/delete/copy and other write operations; the Python side only reads
- `storage_local_server_url` is used to generate download URLs (`{serverUrl}/api/storage/download?path=xxx`); in LOCAL mode, studio-manager auto-registers `StorageDownloadController` to provide the download endpoint
- The Python side's `STORAGE_LOCAL_BASE_PATH` and `STORAGE_LOCAL_BUCKET` must align with the Java side, otherwise file path mismatch will cause read failures

### CUSTOM Mode

Custom storage implementation, suitable for scenarios requiring integration with non-OBS storage (e.g. MinIO, Ceph, Alibaba Cloud OSS, etc.).

#### studio-manager Configuration (Java)

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `storage_type` | Yes | Set to `CUSTOM` |
| `STORAGE_CUSTOM_CLASS` | Yes | Implementation class fully qualified name, e.g. `com.example.MinioFileStore` |
| `STORAGE_CUSTOM_CLASSPATH` | Yes | External JAR path, e.g. `/opt/cloud/storage-plugins/minio-storage.jar` |

**Implementation requirements**:
1. Implement the `FileStore` interface (`com.openjiuwen.studio.agent.common.storage.FileStore`)
2. Provide a no-arg constructor
3. JAR must be a fat jar (including all dependencies), or place dependency JARs in the same directory

#### agent-builder/agent-runtime Configuration (Python)

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `STORAGE_TYPE` | Yes | Set to `CUSTOM` |
| `STORAGE_CUSTOM_MODULE` | Yes | Python module path, supports two formats (see below) |
| `STORAGE_CUSTOM_CLASS` | Yes | Implementation class name, e.g. `MinioStorageProvider` |

**Implementation requirements**:
1. Inherit `ObjectStorageProvider` (`agent_runtime.common.ir_interfaces.ObjectStorageProvider`)
2. Implement abstract method `get_content(self, object_key: str) -> str`
3. Provide a no-arg constructor (`__init__` with no required arguments)
4. Optionally override `get_object_bytes()` / `download_to_file()` for better performance

#### CUSTOM Configuration Differences: studio-manager vs agent-builder/agent-runtime

| Dimension | studio-manager (Java) | agent-builder/agent-runtime (Python) |
|-----------|----------------------|------------------------|
| Type config | `storage_type=CUSTOM` | `STORAGE_TYPE=CUSTOM` |
| Implementation specified | `STORAGE_CUSTOM_CLASS` (fully qualified class name) | `STORAGE_CUSTOM_CLASS` (class name) |
| Load path | `STORAGE_CUSTOM_CLASSPATH` (JAR file path) | `STORAGE_CUSTOM_MODULE` (.py path or module name) |
| Load mechanism | `URLClassLoader` + reflection instantiation | `importlib` dynamic import |
| Spring injection | Not supported (use `System.getenv()` to read config) | Not supported (use `os.getenv()` to read config) |
| Dependency management | fat jar or same-directory JAR | pip install or same-directory .py |
| Storage operations | Full read/write (write/read/delete/copy/list etc.) | Read-only (get_content/get_object_bytes/download_to_file) |

### Container Disk Mounting

#### LOCAL Mode

In LOCAL mode, all containers share the host storage directory; `hostPath` mount must be configured in K8s Deployment:

**Key requirement**:
- **studio-manager, agent-builder, and agent-runtime must mount the same host directory**, otherwise cross-service read/write inconsistency

#### CUSTOM Mode

In CUSTOM mode, external JAR / .py plugin files need to be mounted into the container:

**Usage**:
- Java (studio-manager): Place JAR in host `/opt/cloud/storage-plugins/`, configure `STORAGE_CUSTOM_CLASSPATH` as `/opt/cloud/storage-plugins/xxx.jar`
- Python (agent-builder/agent-runtime): Place .py in host `/opt/cloud/storage-plugins/`, configure `STORAGE_CUSTOM_MODULE` as `/opt/cloud/storage-plugins/xxx`

#### Complete Mount Example

The following is the complete volumes and volumeMounts configuration for studio-manager; agent-builder and agent-runtime are similar:

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

#### Mount List

| Mount name | Host path | Container path | Purpose | Read/Write | Required |
|-----------|-----------|---------------|---------|------------|----------|
| `storage-data` | `/data/storage` | `/data/storage` | LOCAL mode shared storage | Read/Write | Required for LOCAL mode |
| `storage-plugins` | `/opt/cloud/storage-plugins` | `/opt/cloud/storage-plugins` | CUSTOM mode plugin JAR / .py | Read-only | Required for CUSTOM mode |

---

## Database Password Provider Extension

This section describes the abstraction layer for database password retrieval in agent-studio, supporting external custom implementations to integrate with KMS, Vault, and other credential management services.

### Feature Overview

agent-studio abstracts database password retrieval into a `DataSourcePasswordProvider` interface, supporting two modes:

- **DEFAULT** (default): Uses the platform's built-in encryption/decryption tools (Java: `CryptoUtils`, Python: `crypto_tool`) to decrypt the ciphertext password in configuration
- **CUSTOM**: Loads a custom implementation via external JAR (Java) or .py file (Python), enabling integration with KMS, Vault, cloud credential management, and other external services

### DEFAULT Mode (Default)

In DEFAULT mode, the platform uses built-in encryption capabilities to handle database passwords:

- **studio-manager (Java)**: `DefaultDataSourcePasswordProvider` calls `CryptoUtils.decrypt()` to decrypt the `spring.datasource.password` config value
- **agent-runtime / agent-builder (Python)**: `DefaultDataSourcePasswordProvider` calls `crypto_tool.decrypt()` to decrypt the `STORE_DB_PASSWORD` environment variable value

> DEFAULT mode requires no additional configuration — simply leave `DATASOURCE_PASSWORD_PROVIDER_TYPE` unset or set it to `DEFAULT`.

### CUSTOM Mode

Custom password retrieval implementation, suitable for scenarios requiring integration with KMS, Vault, or other external credential management services.

#### studio-manager Configuration (Java)

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `datasource_password_provider_type` | Yes | Set to `CUSTOM` |
| `datasource_password_provider_custom_class` | Yes | Implementation class fully qualified name, e.g. `com.example.KmsPasswordProvider` |
| `datasource_password_provider_custom_classpath` | Yes | External JAR path, e.g. `/opt/cloud/plugins/kms-password-provider.jar` |

**Implementation requirements**:
1. Implement the `DataSourcePasswordProvider` interface (`com.openjiuwen.studio.agent.common.datasource.DataSourcePasswordProvider`)
2. Provide a no-arg constructor
3. JAR must be a fat jar (including all dependencies), or place dependency JARs in the same directory

   ```java
   public class KmsPasswordProvider implements DataSourcePasswordProvider {

       @Override
       public String getPassword(String rawPassword) {
           // rawPassword is the original value from config (may be a ciphertext reference, or empty)
           // Call KMS/Vault API here to fetch the plaintext password and return it
           return fetchFromKms(rawPassword);
       }
   }
   ```

#### agent-builder / agent-runtime Configuration (Python)

| Environment variable | Required | Description |
|---------------------|----------|-------------|
| `DATASOURCE_PASSWORD_PROVIDER_TYPE` | Yes | Set to `CUSTOM` |
| `DATASOURCE_PASSWORD_PROVIDER_MODULE` | Yes | Python module path, supports two formats (see below) |
| `DATASOURCE_PASSWORD_PROVIDER_CLASS` | Yes | Implementation class name, e.g. `KmsPasswordProvider` |

**Implementation requirements**:
1. Inherit `DataSourcePasswordProvider` (`common_utils.password_provider.DataSourcePasswordProvider`)
2. Implement abstract method `get_password(self, raw_password: str) -> str`
3. Provide a no-arg constructor (`__init__` with no required arguments)

   ```python
   from common_utils.password_provider import DataSourcePasswordProvider

   class KmsPasswordProvider(DataSourcePasswordProvider):

       def get_password(self, raw_password: str) -> str:
           # raw_password is the original value from environment variable
           # Call KMS/Vault API here to fetch the plaintext password and return it
           return self._fetch_from_kms(raw_password)
   ```

#### CUSTOM Configuration Differences: studio-manager vs agent-builder / agent-runtime

| Dimension | studio-manager (Java) | agent-builder / agent-runtime (Python) |
|-----------|----------------------|----------------------------------------|
| Type config | `datasource_password_provider_type=CUSTOM` | `DATASOURCE_PASSWORD_PROVIDER_TYPE=CUSTOM` |
| Implementation specified | `datasource_password_provider_custom_class` (fully qualified class name) | `DATASOURCE_PASSWORD_PROVIDER_CLASS` (class name) |
| Load path | `datasource_password_provider_custom_classpath` (JAR file path) | `DATASOURCE_PASSWORD_PROVIDER_MODULE` (.py path or module name) |
| Load mechanism | `URLClassLoader` + reflection instantiation + Spring DI | `importlib` dynamic import |
| Spring injection | Supported (`@Autowired` / `@Value` available) | Not supported (use `os.getenv()` to read config) |
| Dependency management | fat jar or same-directory JAR | pip install or same-directory .py |

> **`DATASOURCE_PASSWORD_PROVIDER_MODULE` supports two formats**:
> - File path: `/opt/cloud/plugins/custom_password_provider` (`.py` suffix auto-appended)
> - Module name: `my_package.custom_provider` (must be installed to site-packages)

### Interface Definition

#### Java Interface

```java
public interface DataSourcePasswordProvider {

    /**
     * Get the database password (plaintext).
     *
     * @param rawPassword the original password from config (may be encrypted ciphertext, or plaintext)
     * @return the decrypted plaintext password
     */
    String getPassword(String rawPassword);
}
```

#### Python Abstract Base Class

```python
from abc import ABC, abstractmethod

class DataSourcePasswordProvider(ABC):

    @abstractmethod
    def get_password(self, raw_password: str) -> str:
        """Get the database password (plaintext).

        Args:
            raw_password: the original password from config (may be encrypted ciphertext, or plaintext)

        Returns:
            the decrypted plaintext password
        """
        ...
```

### Container Deployment

In CUSTOM mode, external JAR / .py plugin files need to be mounted into the container, similar to CUSTOM mode for storage extension:

- **Java (studio-manager)**: Place JAR in host `/opt/cloud/plugins/`, configure `datasource_password_provider_custom_classpath` as `/opt/cloud/plugins/xxx.jar`
- **Python (agent-builder / agent-runtime)**: Place .py in host `/opt/cloud/plugins/`, configure `DATASOURCE_PASSWORD_PROVIDER_MODULE` as `/opt/cloud/plugins/xxx`

K8s Deployment mount example:

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

> You can also reuse the `storage-plugins` mount directory from the storage extension and place password provider plugin JARs / .py files alongside storage plugins.

### Rollback and Disable

Set `DATASOURCE_PASSWORD_PROVIDER_TYPE` (Python side) or `datasource_password_provider_type` (Java side) to `DEFAULT`, or clear the environment variable, and restart the service to roll back to the default local decryption mode.
