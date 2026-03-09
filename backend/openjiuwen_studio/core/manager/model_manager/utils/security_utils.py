"""Security Utils

Provides comprehensive API key security management functionality,
including key storage, validation, and format checking.
Supports Huawei Cloud KMS for root key encryption.
"""
import os
import base64
from typing import Dict, Any

from dotenv import load_dotenv

from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from openjiuwen.core.common.logging import logger

project_root = os.path.dirname(os.path.abspath(__file__))
for _ in range(6):
    project_root = os.path.dirname(project_root)
load_dotenv(os.path.join(project_root, '.env'))


class SecurityUtils:
    """Security Utils
    
    Provides API key security management functionality including:
    - API key storage and retrieval with AES-GCM encryption
    - Huawei Cloud KMS integration for root key protection (optional)
    - Key format validation
    - Key masking for display
    - Provider-specific validation rules
    
    Attributes:
        logger: Logger instance for audit and error tracking
        use_kms: Whether to use Huawei Cloud KMS for root key management
        kms_client: Huawei Cloud KMS client instance (if KMS enabled)
    """

    def __init__(self, master_key: bytes = None, use_kms: bool = None) -> None:
        """
        初始化安全工具类
        
        Args:
            master_key: 如果传入则直接使用，否则根据环境变量读取
            use_kms: 是否使用华为云KMS管理根密钥
        """
        # 非KMS模式
        service_mode = os.getenv('SERVICE_MODE', 'develop')
        self.master_key = None
        if master_key is None:
            # In product mode, AES only be read from environment variables
            # In develop mode, AES can also be read from the .env file
            key_base64 = os.getenv('SERVER_AES_MASTER_KEY_ENV')
            if not key_base64 and service_mode == 'develop':
                if os.getenv('SERVER_AES_MASTER_KEY'):
                    os.environ['SERVER_AES_MASTER_KEY_ENV'] = os.getenv('SERVER_AES_MASTER_KEY')
                    key_base64 = os.getenv('SERVER_AES_MASTER_KEY_ENV')
            if key_base64:
                self.master_key = base64.b64decode(key_base64)
        else:
            self.master_key = master_key

        # KMS模式支持
        if use_kms is None:
            use_kms = os.getenv('HUAWEICLOUD_KMS_ENABLED', 'false').lower() == 'true'
        
        self.use_kms = use_kms
        if self.use_kms:
            self._init_kms()
            self.master_key = self._get_master_key()

        if self.master_key:
            if len(self.master_key) != 32:
                raise ValueError('master_key length must be 32 bytes')
    
    def get_initialized_master_key(self) -> bytes | None:
        """
        返回初始化完成后当前生效的 master_key。
        
        - 非 KMS 模式：为从环境变量或入参传入的 32 字节本地密钥
        - KMS 模式：为通过 KMS 解密得到的 32 字节根密钥
        - 若未成功初始化，则返回 None
        """
        return self.master_key
    
    def _init_kms(self):
        """初始化华为云KMS客户端"""
        try:
            from .huaweicloud_iam import HuaweiCloudIAM
            from .huaweicloud_kms import HuaweiCloudKMS
            
            # 从环境变量读取KMS配置
            username = os.getenv('HUAWEICLOUD_USERNAME')
            password = os.getenv('HUAWEICLOUD_PASSWORD')
            domain_name = os.getenv('HUAWEICLOUD_DOMAIN_NAME')
            project_name = os.getenv('HUAWEICLOUD_PROJECT_NAME')
            project_id = os.getenv('HUAWEICLOUD_PROJECT_ID')
            region = os.getenv('HUAWEICLOUD_REGION', 'cn-north-4')
            
            if not all([username, password]):
                raise ValueError(
                    "Missing KMS configuration. Required environment variables: "
                    "HUAWEICLOUD_USERNAME, HUAWEICLOUD_PASSWORD"
                )
            
            if not project_name and not project_id:
                raise ValueError(
                    "Missing project configuration. Required one of: "
                    "HUAWEICLOUD_PROJECT_NAME or HUAWEICLOUD_PROJECT_ID"
                )
            
            iam_endpoint = os.getenv('HUAWEICLOUD_IAM_ENDPOINT')
            
            # 初始化IAM客户端
            iam_client = HuaweiCloudIAM(
                username, 
                password, 
                domain_name=domain_name,
                iam_endpoint=iam_endpoint
            )
            
            # 先获取token以访问KMS服务
            if project_name and not project_id:
                iam_client.get_token(project_name=project_name)
                project_id = iam_client.project_id
                if not project_id:
                    raise ValueError(f"Failed to get project_id for project_name: {project_name}")
            
            kms_endpoint = os.getenv('HUAWEICLOUD_KMS_ENDPOINT')
            
            # 初始化KMS客户端
            self.kms_client = HuaweiCloudKMS(
                iam_client, 
                project_id, 
                region,
                kms_endpoint=kms_endpoint
            )
            self.kms_key_id = os.getenv('HUAWEICLOUD_KMS_KEY_ID')
            # KMS模式下，SERVER_AES_MASTER_KEY存储的是KMS加密后的根密钥
            self.encrypted_root_key = self.master_key.decode('utf-8') if self.master_key else None
            
            if not self.kms_key_id:
                raise ValueError("Missing HUAWEICLOUD_KMS_KEY_ID environment variable")
            
            logger.info("KMS client initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import KMS modules: {str(e)}")
            raise RuntimeError("KMS modules not available") from e
        except Exception as e:
            logger.error(f"Failed to initialize KMS: {str(e)}")
            raise
    
    def _get_master_key(self) -> bytes:
        """
        获取主密钥（根密钥）
        
        根据use_kms标志决定从KMS解密获取还是使用本地密钥
        
        Returns:
            主密钥字节（32字节）
            
        Raises:
            ValueError: 如果无法获取主密钥
        """
        if not self.kms_client:
            raise ValueError("KMS client not initialized")
        
        if not self.encrypted_root_key:
            raise ValueError("SERVER_AES_MASTER_KEY not found in environment (KMS mode requires encrypted root key)")
        
        try:
            logger.debug("Decrypting root key from KMS...")
            root_key = self.kms_client.decrypt(
                self.kms_key_id,
                self.encrypted_root_key
            )

            logger.debug("Root key decrypted successfully from KMS")

            root_key = base64.b64decode(root_key)
            return root_key
            
        except Exception as e:
            logger.error(f"Failed to decrypt root key from KMS: {str(e)}")
            raise ValueError(f"Failed to decrypt root key from KMS: {str(e)}") from e

    @classmethod
    def generate_random_key(cls, length: int = 16) -> bytes:
        return os.urandom(length)

    @classmethod
    def hkdf_drive(cls, master_key, salt):
        return HKDF(master_key, 32, salt, SHA256, context=b'sensitive-data-salt')

    def encrypt_api_key(self, api_key: str) -> str:
        """Store API key

        Args:
            api_key: API key to store
            user_id: Optional user ID for logging
            
        Returns:
            str: Original API key
            
        Raises:
            ValueError: When API key format is invalid
        """
        if not api_key:
            return None
        
        if not isinstance(api_key, str):
            raise ValueError("API key must be a string")

        if not self.master_key:
            return api_key

        try:
            salt = self.generate_random_key()
            encryption_key = self.hkdf_drive(self.master_key, salt)
            nonce = get_random_bytes(12)
            cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            ciphertext, auth_tag = cipher.encrypt_and_digest(api_key.encode('utf-8'))
            # salt + nonce + ciphertext + auth_tag
            combined_data = salt + nonce + ciphertext + auth_tag
            return base64.b64encode(combined_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to store API key: {str(e)}")
            raise ValueError(f"Failed to store API key: {str(e)}") from e
    
    def decrypt_api_key(self, stored_key: str) -> str | None:
        """Retrieve API key (current version returns directly without decryption)
        
        Args:
            stored_key: Stored API key
            
        Returns:
            str: Original API key
            
        Raises:
            ValueError: When stored key format is invalid
        """
        if not stored_key:
            return None
        
        if not isinstance(stored_key, str):
            raise ValueError("Stored key must be a string")

        if not self.master_key:
            return stored_key

        try:
            data = base64.b64decode(stored_key)
        except Exception:
            return stored_key
        min_encrypted_len = 16 + 12 + 16  # salt + nonce + auth_tag (ciphertext can be 0+)
        if len(data) < min_encrypted_len:
            # Too short to be encrypted → treat as plaintext
            return stored_key
        
        try:
            salt_len = 16  # Depends on the length returned by generate_random_key.
            nonce_len = 12
            tag_len = 16  # GCM default length.

            salt = data[:salt_len]
            nonce = data[salt_len: salt_len + nonce_len]
            ciphertext = data[salt_len + nonce_len: -tag_len]
            auth_tag = data[-tag_len:]

            encryption_key = self.hkdf_drive(self.master_key, salt)
            cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
            plaintext = cipher.decrypt_and_verify(ciphertext, auth_tag)

            return plaintext.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to retrieve API key, "
                         f"the ciphertext does not correspond to the correct key: {str(e)}")
            raise ValueError(f"Failed to retrieve API key, "
                             f"the ciphertext does not correspond to the correct key: {str(e)}") from e

    @staticmethod
    def mask_api_key(api_key: str, visible_chars: int = 4) -> str | None:
        """Mask API key for display purposes
        
        Args:
            api_key: API key to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            str: Masked API key
        """
        if not api_key:
            return None
        
        if len(api_key) <= visible_chars:
            return "*" * len(api_key)
        
        return "*" * (len(api_key) - visible_chars) + api_key[-visible_chars:]
    
    @staticmethod
    def get_decrypted_secret(env_key: str, default: str = None) -> str:
        """
        Retrieve decrypted sensitive configuration items (Supports automatic decryption in KMS mode)
        
        This is a general-purpose method for obtaining sensitive configuration values 
        from environment variables across all scenarios requiring sensitive data access.
        
        - KMS mode: Always treats the value as AES-GCM encrypted ciphertext and decrypts it
        - Non-KMS mode: Returns raw environment variable value (maintains legacy behavior)
        
        Args:
            env_key (str): Environment variable key name
            default (str, optional): Default value to return if environment variable is not found
        
        Returns:
            str: Decrypted plaintext key (in KMS mode) or original raw value (in non-KMS mode)
        """
        encrypted_value = os.getenv(env_key, default)
        if not encrypted_value:
            return default
        
        use_kms = os.getenv('HUAWEICLOUD_KMS_ENABLED', 'false').lower() == 'true'
        
        if not use_kms:
            # Non-KMS mode: return raw value
            return encrypted_value
        
        # KMS mode: always treat the value as ciphertext and attempt decryption
        # In KMS mode, environment variables should contain AES-GCM encrypted values
        # that were encrypted using the root key (which is itself encrypted by KMS)
        try:
            security_utils = SecurityUtils()
            decrypted = security_utils.decrypt_api_key(encrypted_value)
            
            # In KMS mode, if decrypt_api_key returns the original value unchanged,
            # it means the value was not in the expected encrypted format
            # This should be treated as an error in KMS mode
            if decrypted == encrypted_value:
                raise ValueError(
                    f"Secret '{env_key}' appears to be plaintext, but KMS mode requires encrypted values. "
                    f"Please encrypt the value using the encryption tool before setting it in environment variables."
                )
            
            return decrypted
        except ValueError as e:
            # Re-raise ValueError as-is (it's already a meaningful error message)
            raise
        except Exception as e:
            logger.error(f"Failed to decrypt secret '{env_key}' in KMS mode: {str(e)}")
            raise ValueError(
                f"Failed to decrypt secret '{env_key}' in KMS mode"
            ) from e
    
    @staticmethod
    def validate_api_key_format(api_key: str, provider: str) -> Dict[str, Any]:
        """Validate API key format based on provider
        
        Args:
            api_key: API key to validate
            provider: Provider name
            
        Returns:
            Dict[str, Any]: Dictionary containing validation results
        """
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if not api_key:
            result["valid"] = False
            result["errors"].append("API key is required")
            return result
        
        # Provider-specific validation
        if provider == "openai":
            if not api_key.startswith("sk-"):
                result["valid"] = False
                result["errors"].append("OpenAI API key must start with 'sk-'")
            elif len(api_key) < 20:
                result["valid"] = False
                result["errors"].append("OpenAI API key is too short")
        
        elif provider == "anthropic":
            if not api_key.startswith("sk-ant-"):
                result["valid"] = False
                result["errors"].append("Anthropic API key must start with 'sk-ant-'")
        
        elif provider == "deepseek":
            if not api_key.startswith("sk-"):
                result["valid"] = False
                result["errors"].append("DeepSeek API key must start with 'sk-'")
        
        elif provider == "qwen":
            if len(api_key) < 10:
                result["valid"] = False
                result["errors"].append("Qwen API key is too short")
        
        # General security checks
        if len(api_key) > 200:
            result["warnings"].append("API key is unusually long")
        
        # Check for common patterns that may indicate test/fake keys
        test_patterns = ["test", "demo", "example", "fake", "dummy"]
        if any(pattern in api_key.lower() for pattern in test_patterns):
            result["warnings"].append("API key appears to be a test/demo key")
        
        return result