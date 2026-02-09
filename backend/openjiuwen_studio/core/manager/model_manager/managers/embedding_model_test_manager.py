from typing import Dict, Any
import time

from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen.core.retrieval.common.config import EmbeddingConfig
from openjiuwen.core.retrieval.embedding.openai_embedding import OpenAIEmbedding
from openjiuwen_studio.core.manager.repositories import EmbeddingModelConfigRepository
from openjiuwen_studio.schemas.embedding_model_config import EmbeddingModelTestRequest
from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils
from openjiuwen.core.common.exception.errors import BaseError
from openjiuwen_studio.core.exceptions import (
    ModelConfigNotFoundError,
    ModelTestError,
    ValidationError
)


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
                # Create EmbeddingConfig
                embed_config = EmbeddingConfig(
                    model_name=model.model_id,  # model_id is the model name for API calls
                    api_key=api_key,
                    base_url=model.api_base,
                )

                # Create OpenAIEmbedding instance
                embed_model = OpenAIEmbedding(
                    config=embed_config,
                    timeout=60,
                    max_retries=1,
                    max_batch_size=model.max_batch_size,
                )

                # Prepare test text
                raw_texts = []
                if test_request.texts:
                    raw_texts.extend(test_request.texts)
                if test_request.text:
                    raw_texts.append(test_request.text)
                test_texts = [
                    text.strip()
                    for text in raw_texts
                    if isinstance(text, str) and text.strip()
                ]
                if not test_texts:
                    raise ValidationError("No valid test text provided for embedding model test")
                
                # Embed test texts
                embeddings = await embed_model.embed_documents(test_texts)

                response_time = time.time() - start_time
                logger.info(
                    f"Embedding model test successful: {model.model_name} (ID: {model_id}, User ID: {user_id}), "
                    f"response time: {response_time:.2f}s"
                )
                return {
                    "model": model.model_id,
                    "data": [
                        {"object": "embedding", "embedding": emb, "index": idx}
                        for idx, emb in enumerate(embeddings)
                    ]
                    if embeddings
                    else [],
                    "response_time": response_time,
                }
                    
            except BaseError as api_error:
                response_time = time.time() - start_time

                # Extract status code
                error_cause = getattr(api_error, "__cause__", None)
                status_code = getattr(error_cause, "status_code", None)
                # Extract error message
                error_body = getattr(error_cause, "body", None)
                error_detail = str(api_error)
                if isinstance(error_body, dict):
                    error_detail = error_body.get("message", error_detail)
                else:
                    error_detail = getattr(error_cause, "message", error_detail)
                error_lower = str(error_detail).lower()
                
                # Determine type of error based on error message and status code
                config_issue = None
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
                elif isinstance(status_code, int) and status_code >= 500:
                    config_issue = "API server"
                else:
                    config_issue = "configuration"
                
                # Build error message with config issue
                if config_issue:
                    error_message = f"Embedding model '{model.model_name}' {config_issue} is invalid: {error_detail}"
                else:
                    error_message = f"Embedding model '{model.model_name}' API call failed: {error_detail}"
                
                logger.error(
                    f"Embedding model API call failed: {model.model_name} (ID: {model_id}, User ID: {user_id}), "
                    f"error: {error_message}, status_code: {status_code}"
                )
                
                if config_issue in {"insufficient quota", "API key", "API URL", "model name", "request parameters"}:
                    raise ModelTestError(error_message) from api_error

                # Return error message for exceptional errors (such as network or service abnormalities)
                return {
                    "error": error_message,
                    "status_code": status_code,
                    "response_time": response_time,
                }
                
        except (ModelConfigNotFoundError, ModelTestError):
            raise
        except Exception as e:
            logger.error(f"Failed to test embedding model {model_id} (User ID: {user_id}): {str(e)}", exc_info=True)
            raise ValidationError(f"Failed to test embedding model: {str(e)}") from e

