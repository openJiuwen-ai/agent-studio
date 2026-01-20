from typing import Optional, Dict, Any
import time
import logging
import requests

from sqlalchemy.orm import Session

from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.schemas.embedding_model_config import EmbeddingModelTestRequest
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils
from openjiuwen_studio.core.exceptions import (
    ModelConfigNotFoundError,
    ModelTestError,
    ValidationError
)

logger = logging.getLogger(__name__)


class EmbeddingModelTester:
    """Embedding 模型测试器 - 直接返回 API 原始响应"""
    
    def __init__(self, db: Session):
        self.db = db
        self.repo = EmbeddingModelConfigRepository(db)
        self.security_utils = SecurityUtils()
    
    async def test_embedding_model(
        self,
        model_id: int,
        test_request: EmbeddingModelTestRequest,
        user_id: int
    ) -> Dict[str, Any]:
        """测试 embedding 模型配置
        
        Args:
            model_id: 模型配置ID
            test_request: 测试请求数据
            user_id: 测试用户ID
            
        Returns:
            Embedding 模型测试响应
            
        Raises:
            ModelConfigNotFoundError: 模型配置不存在
            ModelTestError: 模型测试失败
            ValidationError: 数据验证失败
        """
        start_time = time.time()
        
        try:
            # 获取模型配置
            model = self.repo.get_by_id(model_id)
            if not model:
                raise ModelConfigNotFoundError(f"Embedding model configuration not found: {model_id}")
            
            # 检查模型状态
            if not model.is_active:
                raise ModelTestError(f"Embedding model {model.model_name} is currently inactive and cannot be tested")
            
            # 解密 API key
            api_key = ""
            if model.api_key:
                try:
                    api_key = self.security_utils.decrypt_api_key(model.api_key)
                except Exception as e:
                    raise ModelTestError(f"API key decryption failed: {str(e)}") from e
            
            # 验证 API key
            if not api_key:
                raise ModelTestError(f"Embedding model {model.model_name} lacks a valid API key")
            
            # 直接调用 embedding API，返回原始响应
            try:
                headers = {
                    "Content-Type": "application/json",
                }
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                
                # 构建请求 payload
                payload = {
                    "model": model.model_id,
                    "input": test_request.texts if test_request.texts else test_request.text,
                }
                
                # 发送请求
                resp = requests.post(
                    model.api_base,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                resp.raise_for_status()
                api_response = resp.json()
                
                response_time = time.time() - start_time
                
                logger.info(
                    f"Embedding model test successful: {model.model_name} (ID: {model_id}), "
                    f"response time: {response_time:.2f}s"
                )
                
                # 直接返回 API 的原始响应
                return api_response
                    
            except requests.exceptions.RequestException as api_error:
                response_time = time.time() - start_time
                
                # Extract detailed error message from response if available
                error_detail = str(api_error)
                config_issue = None
                status_code = None
                
                if hasattr(api_error, 'response') and api_error.response is not None:
                    status_code = api_error.response.status_code
                    try:
                        error_response = api_error.response.json()
                        if isinstance(error_response, dict):
                            # 尝试从多个可能的字段中提取错误信息
                            error_msg_from_api = (
                                error_response.get('error', {}).get('message', '') or
                                error_response.get('message', '') or
                                error_response.get('error', '')
                            )
                            if error_msg_from_api:
                                error_detail = error_msg_from_api
                    except Exception:
                        # If JSON parsing fails, use status code to determine issue
                        pass
                    
                    # Determine which config is wrong based on status code and error message
                    error_lower = error_detail.lower()
                    # 检查是否是配额不足（429 Too Many Requests, 402 Payment Required）
                    # 或错误信息中包含配额相关关键词
                    is_quota_status = status_code == 429 or status_code == 402
                    has_quota_keyword = (
                        "quota" in error_lower or
                        "insufficient" in error_lower or
                        "limit exceeded" in error_lower or
                        "rate limit" in error_lower
                    )
                    is_quota_error = is_quota_status or has_quota_keyword
                    
                    if is_quota_error:
                        config_issue = "insufficient quota"
                    elif status_code == 401 or status_code == 403:
                        config_issue = "API key"
                    elif status_code == 404:
                        # 404 可能是 URL 不对或 model name 不对
                        # 优先检查是否是 URL 问题（错误信息中包含 "for url:" 或 "url:"）
                        if "for url:" in error_lower or "url:" in error_lower or "endpoint" in error_lower:
                            config_issue = "API URL"
                        # 如果错误信息明确提到 model 不存在，则是 model name 问题
                        elif "model" in error_lower and ("does not exist" in error_lower or 
                                                          "not found" in error_lower):
                            config_issue = "model name"
                        else:
                            # 默认情况下，404 更可能是 URL 问题
                            config_issue = "API URL"
                    elif status_code == 400:
                        # 400 可能是 model name、API key 或请求参数问题
                        # 检查是否是 model name 问题
                        is_model_error = "model" in error_lower
                        model_not_exist = "does not exist" in error_lower
                        model_invalid = "invalid" in error_lower and "model" in error_lower.split()[:3]
                        is_model_name_issue = is_model_error and (model_not_exist or model_invalid)
                        
                        if is_model_name_issue:
                            config_issue = "model name"
                        elif "key" in error_lower or "auth" in error_lower or "unauthorized" in error_lower:
                            config_issue = "API key"
                        else:
                            config_issue = "request parameters"
                    elif status_code >= 500:
                        config_issue = "API server"
                    else:
                        config_issue = "configuration"
                
                # Build error message with config issue
                if config_issue:
                    error_message = f"Embedding model '{model.model_name}' {config_issue} is invalid: {error_detail}"
                else:
                    error_message = f"Embedding model '{model.model_name}' API call failed: {error_detail}"
                
                logger.error(
                    f"Embedding model API call failed: {model.model_name} (ID: {model_id}), "
                    f"error: {error_message}, status_code: {status_code}"
                )
                
                # 返回错误信息
                return {
                    "error": error_message,
                    "status_code": status_code
                }
                
        except (ModelConfigNotFoundError, ModelTestError):
            raise
        except Exception as e:
            logger.error(f"Failed to test embedding model {model_id}: {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to test embedding model: {str(e)}") from e

