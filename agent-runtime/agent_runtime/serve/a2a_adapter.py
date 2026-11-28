# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""
A2A HTTP/2 → HTTP/1.1 适配层（FEAT-131）.

高码 gateway（Java HttpClient，默认 HTTP/2）直连低码 runtime（uvicorn，仅 HTTP/1.1）
时，h11 解析器拒绝 HTTP/2 升级请求。本模块在 runtime 前面加一层透明 TCP 适配层：

  gateway (HTTP/2 h2c upgrade) → adapter (TCP, 剥离 Upgrade 头) → uvicorn (HTTP/1.1)

适配层在 TCP 字节层面剥离 HTTP/2 升级相关 headers（Upgrade、HTTP2-Settings、
Connection 中的 upgrade token），使 Java HttpClient 回退到 HTTP/1.1，uvicorn 正常处理。
无业务逻辑，纯字节级协议适配。

启动方式见 EIStart_base.py 的 --with-adapter 参数。
"""

import asyncio
import logging

_logger = logging.getLogger(__name__)

# 需要剥离的 HTTP/2 升级相关 header 关键字（小写）
_H2C_STRIP_HEADERS = {b"upgrade", b"http2-settings"}
_H2C_CONNECTION_TOKENS = {b"upgrade", b"http2-settings"}


def _strip_h2c_headers(data: bytes) -> bytes:
    """从原始 HTTP 请求数据中剥离 h2c 升级相关 headers。

    在 headers 区块（\\r\\n\\r\\n 之前）逐行过滤：
    - 删除 Upgrade: h2c 行
    - 删除 HTTP2-Settings: ... 行
    - 从 Connection: ... 中移除 upgrade 和 http2-settings token

    body 区块（\\r\\n\\r\\n 之后）原样保留。
    """
    # 分离 headers 和 body
    header_end = data.find(b"\r\n\r\n")
    if header_end == -1:
        # headers 还没读完，原样返回（后续数据会补全）
        return data

    header_block = data[:header_end]
    body = data[header_end + 4:]

    # 按 \r\n 分割 headers
    lines = header_block.split(b"\r\n")
    request_line = lines[0]  # POST /a2a HTTP/1.1
    filtered_lines = [request_line]

    for line in lines[1:]:
        if not line:
            continue

        # 解析 header name
        colon_pos = line.find(b":")
        if colon_pos == -1:
            filtered_lines.append(line)
            continue

        header_name = line[:colon_pos].strip().lower()

        if header_name in _H2C_STRIP_HEADERS:
            # 跳过 Upgrade 和 HTTP2-Settings headers
            continue

        if header_name == b"connection":
            # 从 Connection header 中移除 upgrade 和 http2-settings token
            value = line[colon_pos + 1:].strip()
            tokens = [t.strip() for t in value.split(b",")]
            filtered_tokens = [t for t in tokens if t.lower() not in _H2C_CONNECTION_TOKENS]
            if filtered_tokens:
                filtered_lines.append(b"Connection: " + b", ".join(filtered_tokens))
            # 如果所有 token 都被移除，跳过整个 header
            continue

        filtered_lines.append(line)

    # 重新组装
    new_header_block = b"\r\n".join(filtered_lines)
    return new_header_block + b"\r\n\r\n" + body


async def _pipe_with_strip(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """从 gateway 读取数据，剥离 h2c headers 后转发到 uvicorn。

    缓冲数据直到完整的 HTTP header 区块（\\r\\n\\r\\n）出现后再剥离，
    避免 TCP 分片导致 Upgrade 头跨块时被原样转发。
    """
    buffer = b""
    headers_done = False
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                # 刷出残留 buffer（不完整的 header 区块，原样转发）
                if buffer:
                    writer.write(buffer)
                    await writer.drain()
                break

            if headers_done:
                # header 区块已处理完，后续数据（body）原样转发
                writer.write(data)
                await writer.drain()
                continue

            buffer += data
            header_end = buffer.find(b"\r\n\r\n")
            if header_end == -1:
                # header 还没读完，继续缓冲
                continue

            # header 完整了，剥离 h2c 头后转发整块
            cleaned = _strip_h2c_headers(buffer)
            writer.write(cleaned)
            await writer.drain()
            buffer = b""
            headers_done = True
    except (ConnectionResetError, BrokenPipeError):
        _logger.debug("Connection closed during pipe_with_strip")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            _logger.debug("Error closing writer in pipe_with_strip: %s", e)


async def _pipe_raw(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """从 uvicorn 读取响应原样转发到 gateway。"""
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionResetError, BrokenPipeError):
        _logger.debug("Connection closed during pipe_raw")
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            _logger.debug("Error closing writer in pipe_raw: %s", e)


async def _handle_connection(
    client_reader: asyncio.StreamReader,
    client_writer: asyncio.StreamWriter,
    internal_host: str,
    internal_port: int,
):
    """处理一个 gateway → adapter 连接：建立到 uvicorn 的连接，双向 pipe。"""
    try:
        uvicorn_reader, uvicorn_writer = await asyncio.open_connection(
            internal_host, internal_port
        )
    except ConnectionRefusedError:
        _logger.warning("Cannot connect to uvicorn at %s:%s", internal_host, internal_port)
        client_writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n"
                            b'{"error":"Adapter cannot reach uvicorn"}')
        await client_writer.drain()
        client_writer.close()
        await client_writer.wait_closed()
        return

    # gateway → adapter → uvicorn（剥离 h2c headers）
    # uvicorn → adapter → gateway（原样透传）
    await asyncio.gather(
        _pipe_with_strip(client_reader, uvicorn_writer),
        _pipe_raw(uvicorn_reader, client_writer),
    )


async def start_adapter(host: str, port: int, internal_host: str, internal_port: int):
    """启动 TCP 适配层。

    Args:
        host: adapter 监听地址
        port: adapter 监听端口
        internal_host: uvicorn 内部地址
        internal_port: uvicorn 内部端口
    """
    _logger.info("Starting A2A adapter on %s:%s → %s:%s (h2c header strip)",
                 host, port, internal_host, internal_port)

    server = await asyncio.start_server(
        lambda r, w: _handle_connection(r, w, internal_host, internal_port),
        host,
        port,
    )

    # server 创建成功意味着端口已绑定
    sockets = ", ".join(str(s.getsockname()) for s in server.sockets)
    _logger.info("A2A adapter started, listening on %s → forwarding to %s:%s",
                 sockets, internal_host, internal_port)

    async with server:
        await server.serve_forever()
