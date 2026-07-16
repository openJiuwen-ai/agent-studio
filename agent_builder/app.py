#  Copyright (c) Huawei Technologies Co., Ltd. 2023-2024. All rights reserved.

"""
application
"""

import logging
import os
import time

from agent_builder.serve.common.logger.log_init import init_logger
from agent_builder.serve.server import ServerApp
from flask import request, session, g
from agent_builder.adapter.exception_bridge import JiuWenException
from werkzeug.serving import WSGIRequestHandler

SERVER_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "serve", "settings.yaml"
)
FRAMEWORK_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "serve", "application.yaml"
)
init_logger()

server_app = ServerApp(
    default_server_config=SERVER_CONFIG_PATH,
    default_framework_config=FRAMEWORK_CONFIG_PATH,
)
app = server_app.get_app()


@app.before_request
def set_server_header():
    """server_header"""
    WSGIRequestHandler.server_version = "default"
    WSGIRequestHandler.sys_version = ""


@app.before_request
def start_timer():
    """start_timer"""
    g.start_time = time.time()


@app.before_request
def refresh_session():
    """authenticate"""
    session.permanent = True  # 将permanent设置为true，使有效期配置生效
    session.modified = True  # 标记session为已修改，刷新过期时间


@app.before_request
def method_limit():
    """method_limit"""
    if request.method.lower() == "options":
        res = "", 404
    else:
        res = None
    return res


@app.after_request
def after_request(response):
    """process audit data after each request"""
    # 解决点击劫持，关闭则不允许iframe嵌入其他页面
    response.headers["X-Frame-Options"] = "DENY"
    # 使用HTTP严格传输安全（HSTS）
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    # 禁用浏览器内容探测
    response.headers["X-Content-Type-Options"] = "nosniff"
    # 禁用缓存
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    # 配置Content-Security-Policy
    csp = "object-src 'none'; frame-ancestors 'none'; form-action 'self';"
    response.headers["Content-Security-Policy"] = csp
    # 防止跨站脚本攻击（XSS）
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


def check_root():
    """check is root"""
    if os.name == "posix" and os.geteuid() == 0:
        # 判断linux下启动用户
        raise JiuWenException("please start with valid identity")


def log_disable():
    """disable flask default console logger"""
    log = logging.getLogger("werkzeug")
    log.disabled = True


def run():
    """
    app 运行
    """
    log_disable()
    check_root()
    host, port = server_app.get_host_and_port()
    if not isinstance(host, str):
        raise JiuWenException("host should be a string")

    app.run(host=host, port=port, ssl_context=server_app.http_ssl_context, debug=False)


if __name__ == "__main__":
    run()
