import base64
import logging
import os

import requests

from .huaweicloud_iam import HuaweiCloudIAM

logger = logging.getLogger(__name__)


class HuaweiCloudKMS:
    """华为云DEW KMS加解密模块 - 纯API调用实现"""
    
    def __init__(self,
                 iam_client: HuaweiCloudIAM,
                 project_id: str,
                 region: str = "ap-southeast-1",
                 kms_endpoint: str = None,
                 encryption_algorithm: str = None):
        """
        初始化KMS客户端
        
        Args:
            iam_client: 已初始化的IAM客户端
            project_id: 华为云项目ID
            region: 区域代码 (如cn-north-4、cn-east-3)
            kms_endpoint: KMS服务端点（可选，默认从环境变量读取或根据region生成）
            encryption_algorithm: 加解密算法（可选，默认从环境变量读取或使用 RSAES_OAEP_SHA_256）
        """
        self.iam_client = iam_client
        self.project_id = project_id
        self.region = region
        
        # 优先级：传入参数 > 环境变量 > 根据region生成默认值
        if kms_endpoint:
            self.kms_endpoint = kms_endpoint
        else:
            # 从环境变量读取，如果没有则根据region生成
            env_endpoint = os.getenv('HUAWEICLOUD_KMS_ENDPOINT')
            if env_endpoint:
                self.kms_endpoint = env_endpoint
            else:
                self.kms_endpoint = f"https://kms.{region}.myhuaweicloud.com"

        # 加解密算法优先级：传入参数 > 环境变量 > 默认值
        self.encryption_algorithm = (
            encryption_algorithm
            or os.getenv("HUAWEICLOUD_KMS_ENCRYPTION_ALGORITHM")
            or "RSAES_OAEP_SHA_256"
        )
    
    def _get_headers(self) -> dict:
        """获取KMS API请求头（包含IAM认证信息）"""
        # 使用项目ID获取token（如果project_id已设置）
        token = self.iam_client.get_token(project_id=self.project_id)
        
        return {
            'Content-Type': 'application/json',
            'X-Auth-Token': token
        }
    
    def encrypt(self, 
                key_id: str, 
                plaintext: bytes) -> str:
        """
        使用KMS主密钥加密数据
        
        Args:
            key_id: 主密钥ID或别名
            plaintext: 要加密的明文数据（字节）
            
        Returns:
            ciphertext: Base64编码的密文
        """
        url = f"{self.kms_endpoint}/v1.0/{self.project_id}/kms/encrypt-data"
        
        # 明文需要Base64编码
        plaintext_b64 = base64.b64encode(plaintext).decode('utf-8')
        
        body = {
            "key_id": key_id,
            "plain_text": plaintext_b64,
            "encryption_algorithm": self.encryption_algorithm,
        }
        
        headers = self._get_headers()
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            ciphertext = result.get('cipher_text')
            
            if not ciphertext:
                raise ValueError("Failed to get cipher_text from KMS response")
            
            logger.info(f"Successfully encrypted data using KMS key: {key_id}")
            return ciphertext
            
        except requests.RequestException as e:
            logger.error(f"KMS encryption failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"KMS error detail: {error_detail}")
                except Exception:
                    logger.error(f"KMS error response: {e.response.text}")
            raise RuntimeError(f"KMS encryption failed: {str(e)}") from e
    
    def decrypt(self, 
                key_id: str,
                ciphertext: str) -> bytes:
        """
        使用KMS主密钥解密数据
        
        Args:
            key_id: 主密钥ID或别名
            ciphertext: Base64编码的密文
            
        Returns:
            plaintext: 解密后的原始数据（字节）
        """
        url = f"{self.kms_endpoint}/v1.0/{self.project_id}/kms/decrypt-data"
        
        body = {
            "key_id": key_id,
            "cipher_text": ciphertext,
            "encryption_algorithm": self.encryption_algorithm,
        }
        
        headers = self._get_headers()
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            plaintext = result.get('plain_text')
            
            if not plaintext:
                raise ValueError("Failed to get plain_text from KMS response")
            
            logger.info(f"Successfully decrypted data using KMS key: {key_id}")
            return plaintext
            
        except requests.RequestException as e:
            logger.error(f"KMS decryption failed: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"KMS error detail: {error_detail}")
                except Exception:
                    logger.error(f"KMS error response: {e.response.text}")
            raise RuntimeError(f"KMS decryption failed: {str(e)}") from e
