import json
from urllib.parse import urljoin, urlencode
import requests
from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.model_manager.utils.security_utils import SecurityUtils

security_utils = SecurityUtils()


def _decrypt_if_needed(value):
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    try:
        decrypted = security_utils.decrypt_api_key(text)
        return decrypted if isinstance(decrypted, str) else text
    except Exception:
        return text


def auth(auth_credentials: dict) -> dict:
    logger.info("开始执行插件鉴权")
    auth_type = (auth_credentials.get('type') or "").upper()

    # 公共请求方法
    def make_auth_request(url: str, payload: dict, method: str = "POST") -> dict:
        try:
            response = requests.post(
                url,
                data=json.dumps(payload),
                verify=True,
                headers={'Content-Type': 'application/json'},
                timeout=100
            )
            response.raise_for_status()  # 自动处理HTTP错误

            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("鉴权 API 请求异常: %s", e, exc_info=True)
            error_msg = f"API请求失败: {str(e)}"
            if e.response is not None:
                error_msg += f"\n状态码: {e.response.status_code}"
                try:
                    error_details = e.response.json()
                    error_msg += f"\n错误详情: {json.dumps(error_details, indent=2)}"
                except json.JSONDecodeError:
                    error_msg += f"\n响应内容: {e.response.text[:500]}"
            raise RuntimeError(error_msg) from e
        except json.JSONDecodeError as json_err:
            raise RuntimeError("API响应不是有效的JSON格式") from json_err

    # 认证类型路由
    if auth_type == 'OAUTH':
        url = auth_credentials['endpoint_url']
        client_secret = _decrypt_if_needed(auth_credentials.get('client_secret'))

        # 查询参数
        query_params = {
            'client_id': auth_credentials['client_id'],
            'client_secret': client_secret,
            'grant_type': 'client_credentials'
        }
        scope = auth_credentials.get('scope', '')
        if scope:
            query_params['scope'] = scope

        url_with_params = urljoin(url, '?' + urlencode(query_params))

        # 发送认证请求
        auth_data = make_auth_request(
            url_with_params,
            payload={}
        )
        headers = {"Authorization": "Bearer " + auth_data['access_token']}
        return {"headers": headers}

    elif auth_type == 'SERVICE':
        headers = auth_credentials.get('headers', {})
        query = auth_credentials.get('query', {})

        resolved_headers = {}
        if isinstance(headers, dict):
            for k, v in headers.items():
                if k:
                    resolved_headers[str(k)] = _decrypt_if_needed(v)

        resolved_query = {}
        if isinstance(query, dict):
            for k, v in query.items():
                if k:
                    resolved_query[str(k)] = _decrypt_if_needed(v)

        return {"headers": resolved_headers, "query": resolved_query}

    else:
        return auth_credentials
