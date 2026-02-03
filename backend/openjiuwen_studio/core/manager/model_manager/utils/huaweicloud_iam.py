import logging
import os

import requests

logger = logging.getLogger(__name__)


class HuaweiCloudIAM:
    """华为云IAM鉴权模块 - 纯API调用实现
    
    支持账号密码方式认证，使用华为云IAM v3 API获取临时Token。
    """
    
    def __init__(self, 
                 username: str,
                 password: str,
                 domain_name: str = None,
                 iam_endpoint: str = None):
        """
        初始化IAM客户端
        
        Args:
            username: 华为云账号用户名
            password: 华为云账号密码
            domain_name: 租户/域名（可选，默认使用"Default"）
            iam_endpoint: IAM服务端点（可选，默认从环境变量读取或使用默认值）
        """
        self.username = username
        self.password = password
        self.domain_name = domain_name or "Default"
        self.iam_endpoint = iam_endpoint or os.getenv('HUAWEICLOUD_IAM_ENDPOINT', 'https://iam.myhuaweicloud.com')
        self.project_id = None
    
    def get_token(self, project_name: str = None, project_id: str = None, domain_name: str = None) -> str:
        """
        获取临时安全令牌 (Token)
        
        用于后续KMS操作的鉴权
        
        Args:
            project_name: 项目名称（可选，如 "ap-southeast-1"）
            project_id: 项目ID（可选，如果提供则使用项目ID）
            domain_name: 域名（可选，默认使用Default）
            
        Returns:
            token: IAM认证令牌
        """
        url = f"{self.iam_endpoint}/v3/auth/tokens?nocatalog=true"
        
        effective_domain = domain_name or self.domain_name
        
        # 构建请求体 - 使用账号密码方式认证
        auth_identity = {
            "methods": ["password"],
            "password": {
                "user": {
                    "name": self.username,
                    "password": self.password,
                    "domain": {
                        "name": effective_domain
                    }
                }
            }
        }
        
        auth_scope = {}
        if project_name:
            auth_scope["project"] = {"name": project_name}
        elif project_id:
            auth_scope["project"] = {"id": project_id}
        else:
            auth_scope["domain"] = {"name": effective_domain}
        
        body = {
            "auth": {
                "identity": auth_identity,
                "scope": auth_scope
            }
        }
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        try:
            response = requests.post(url, json=body, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 从响应头获取token
            token = response.headers.get('X-Subject-Token')
            if not token:
                raise ValueError("Failed to get X-Subject-Token from IAM response")
            
            if not self.project_id:
                if project_id:
                    self.project_id = project_id
                else:
                    try:
                        token_data = response.json().get('token', {})
                        project_info = token_data.get('project', {})
                        if project_info:
                            self.project_id = project_info.get('id')
                    except Exception as e:
                        logger.debug("Failed to parse IAM token response for project_id", exc_info=True)
            
            logger.info("Successfully obtained IAM token")
            return token
            
        except requests.RequestException as e:
            logger.error(f"Failed to get IAM token: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"IAM error detail: {error_detail}")
                except Exception:
                    logger.error(f"IAM error response: {e.response.text}")
            raise RuntimeError(f"IAM authentication failed: {str(e)}") from e
    
