import traceback
from typing import Any
from fastapi import HTTPException

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.config import settings
from openjiuwen_studio.core.common.language_thread_context import get_language


def _get_message(zh_msg: str, en_msg: str) -> str:
    """
    根据当前语言环境返回对应的错误消息
    
    Args:
        zh_msg: 中文消息
        en_msg: 英文消息
        
    Returns:
        str: 对应语言的错误消息
    """
    language = get_language()
    if language == 'zh-cn' or language == 'zh':
        return zh_msg
    return en_msg


ERROR_MESSAGE_MAPPING = {
    # 网络相关异常
    'ConnectionError': ("服务连接失败，请稍后重试", "Service connection failed, please try again later"),
    'TimeoutError': ("服务连接超时，请稍后重试", "Service connection timeout, please try again later"),
    # 权限认证相关异常
    'PermissionError': ("权限不足或认证失败", "Insufficient permissions or authentication failed"),
    'AuthenticationError': ("权限不足或认证失败", "Insufficient permissions or authentication failed"),
    # 参数验证相关异常
    'ValueError': ("请求参数格式错误", "Invalid request parameter format"),
    'ValidationError': ("请求参数格式错误", "Invalid request parameter format"),
    # 文件操作相关异常
    'FileNotFoundError': ("文件操作失败", "File operation failed"),
    'IOError': ("文件操作失败", "File operation failed"),
    # 数据库相关异常
    'DatabaseError': ("数据库操作失败", "Database operation failed"),
    'IntegrityError': ("数据库操作失败", "Database operation failed"),
}


ERROR_CODE_MAPPING = {
    # 模型相关错误码 (181xxx)
    181001: ("模型调用失败，请检查模型配置（API Key、Base URL、模型名称等）",
             "Model call failed, please check model configuration (API Key, Base URL, model name, etc.)"),
    181002: ("模型服务配置错误，请检查模型配置",
             "Model service configuration error, please check model configuration"),
    181003: ("模型配置错误，请检查模型参数",
             "Model configuration error, please check model parameters"),
    181004: ("模型调用参数错误，请检查输入参数",
             "Model call parameter error, please check input parameters"),
    181005: ("模型客户端配置无效，请检查模型配置",
             "Model client configuration invalid, please check model configuration"),
    
    # 智能体控制器相关错误码 (123xxx)
    123000: ("智能体控制器调用失败，请检查智能体配置",
             "Agent controller call failed, please check agent configuration"),
    123003: ("智能体控制器运行时错误，请联系管理员",
             "Agent controller runtime error, please contact the administrator"),
    
    # 智能体工具相关错误码 (120xxx)
    120000: ("智能体工具未找到，请检查工具配置",
             "Agent tool not found, please check tool configuration"),
    120001: ("智能体工具执行错误，请检查工具配置",
             "Agent tool execution error, please check tool configuration"),
    120003: ("智能体工作流执行错误，请检查工作流配置",
             "Agent workflow execution error, please check workflow configuration"),
    
    # 提问器组件相关错误码 (101xxx)
    101070: ("提问器输入参数错误，请检查提问器配置",
             "Questioner input parameter error, please check questioner configuration"),
    101071: ("提问器配置错误，请检查提问器参数设置",
             "Questioner configuration error, please check questioner parameter settings"),
    101072: ("提问器输入无效，请检查输入数据格式",
             "Questioner input invalid, please check input data format"),
    101073: ("提问器状态初始化失败，请检查提问器配置",
             "Questioner state initialization failed, please check questioner configuration"),
    101074: ("提问器运行错误：达到最大响应次数仍未获取所有必需信息，请增加最大响应次数或简化问题",
             "Questioner runtime error: Maximum response count reached without obtaining all "
             "required information, please increase max response count or simplify questions"),
    101075: ("提问器调用失败，请检查提问器配置",
             "Questioner call failed, please check questioner configuration"),
    101076: ("提问器执行过程错误，请检查提问器配置",
             "Questioner execution process error, please check questioner configuration"),
}


def _extract_model_error_message(error_message: str) -> str:
    """
    从模型调用错误消息中提取用户友好的错误提示
    
    Args:
        error_message: 原始错误消息
        
    Returns:
        str: 用户友好的错误消息
    """
    error_lower = error_message.lower()
    
    if "302" in error_message or "redirect" in error_lower:
        return _get_message(
            "模型服务地址重定向错误，请检查模型配置中的Base URL是否正确",
            "Model service URL redirect error, please check if the Base URL in model configuration is correct"
        )
    
    if "401" in error_message or "invalid_api_key" in error_lower or "incorrect api key" in error_lower:
        return _get_message(
            "模型API Key无效或已过期，请检查模型配置中的API Key",
            "Model API Key is invalid or expired, please check the API Key in model configuration"
        )
    
    if "403" in error_message or "forbidden" in error_lower or "access denied" in error_lower:
        return _get_message(
            "模型访问权限不足，请检查API Key权限或账户余额",
            "Insufficient model access permissions, please check API Key permissions or account balance"
        )
    
    if "404" in error_message or "not found" in error_lower:
        if "model" in error_lower:
            return _get_message(
                "模型不存在或模型名称错误，请检查模型配置中的模型名称",
                "Model does not exist or model name is incorrect, please check the model name in model configuration"
            )
        return _get_message(
            "模型服务地址错误，请检查模型配置中的Base URL",
            "Model service URL is incorrect, please check the Base URL in model configuration"
        )
    
    if "429" in error_message or "rate limit" in error_lower or "quota" in error_lower:
        return _get_message(
            "模型调用频率超限或配额不足，请稍后重试或检查账户余额",
            "Model call rate limit exceeded or insufficient quota, please try again later or check account balance"
        )
    
    server_errors = ("500", "502", "503")
    if any(code in error_message for code in server_errors) or "internal server error" in error_lower:
        return _get_message(
            "模型服务异常，请稍后重试或联系服务提供商",
            "Model service error, please try again later or contact the service provider"
        )
    
    if "timeout" in error_lower or "timed out" in error_lower:
        return _get_message(
            "模型调用超时，请检查网络连接或增加超时时间配置",
            "Model call timeout, please check network connection or increase timeout configuration"
        )
    
    if "connection" in error_lower or "network" in error_lower or "dns" in error_lower:
        return _get_message(
            "模型服务连接失败，请检查网络连接和模型服务地址",
            "Model service connection failed, please check network connection and model service URL"
        )
    
    if "ssl" in error_lower or "certificate" in error_lower:
        return _get_message(
            "模型服务SSL证书验证失败，请检查安全配置",
            "Model service SSL certificate verification failed, please check security configuration"
        )
    
    return None


def log_exception(e: Exception):
    """记录异常详情到日志，包含完整的堆栈信息"""
    logger.error(f"Exception: {repr(e)}")
    stack_frames = traceback.extract_tb(e.__traceback__)
    for frame in stack_frames:
        logger.debug(
            f"File \"{frame.filename}\", line {frame.lineno}, in {frame.name}")


def get_safe_error_message(e: Exception, custom_message: str = None) -> str:
    """
    获取安全的错误消息，避免敏感信息泄露

    Args:
        e: 异常对象
        custom_message: 自定义错误消息

    Returns:
        str: 安全的错误消息
    """
    if settings.debug:
        # 开发环境：返回详细错误信息
        return f"{custom_message}: {str(e)}" if custom_message else str(e)
    # 生产环境：返回通用错误消息
    if custom_message:
        return custom_message

    # 根据异常类型返回相应的通用消息
    error_type = type(e).__name__
    
    # 优先尝试从错误消息中提取模型相关的具体错误（优先级最高）
    error_message = str(e)
    model_error = _extract_model_error_message(error_message)
    if model_error:
        return model_error
    
    # 检查错误码映射（针对BaseError等有code属性的异常）
    if hasattr(e, 'code'):
        error_code = getattr(e, 'code', None)
        if error_code and error_code in ERROR_CODE_MAPPING:
            # 使用预定义的错误码映射（支持中英双语）
            zh_msg, en_msg = ERROR_CODE_MAPPING[error_code]
            return _get_message(zh_msg, en_msg)
    
    # 检查异常对象是否有code属性（如BaseError）
    if hasattr(e, 'code'):
        error_code = getattr(e, 'code', None)
        # 如果有具体的错误码，尝试提取错误消息中的有用信息
        if error_code and error_code != -1:
            # 对于已知的业务错误，返回原始错误消息
            if hasattr(e, 'message') and e.message:
                return e.message

    # 根据异常类型返回相应的通用消息（支持中英双语）
    if error_type in ERROR_MESSAGE_MAPPING:
        zh_msg, en_msg = ERROR_MESSAGE_MAPPING[error_type]
        return _get_message(zh_msg, en_msg)
    
    return _get_message(
        "系统内部错误，请联系管理员",
        "System internal error, please contact the administrator"
    )


def handle_http_exception(e: Exception, custom_message: str = None, status_code: int = 500) -> Exception:
    """
    处理HTTP异常，返回安全的异常信息

    Args:
        e: 原始异常
        custom_message: 自定义错误消息
        status_code: HTTP状态码

    Returns:
        Exception: 处理后的HTTPException
    """
    # 记录完整异常信息到日志
    log_exception(e)

    # 获取安全的错误消息
    safe_message = get_safe_error_message(e, custom_message)

    return HTTPException(status_code=status_code, detail=safe_message)
