# Copyright (c) Huawei Technologies Co., Ltd. 2025. All rights reserved.
"""
ReActAgent File Reader Adapter — 从 URL 下载并读取文件内容的 Tool
"""

import os
import tempfile
from typing import Any

from openjiuwen.core.foundation.tool import Tool, ToolCard


class ReactFileReaderAdapter(Tool):
    """从 URL 读取文件的工具，包装为 ReActAgent 可调用的 Tool"""

    def __init__(self):
        card = ToolCard(
            id="read_file_from_url",
            name="read_file_from_url",
            description="读取文件内容。输入参数 url 是完整的文件链接（http/https URL），工具会自动下载并读取文件，返回文本内容。必须传入用户提供的完整 URL，不要自行构造！支持格式：.txt, .md, .json, .xml, .html（纯文本），.docx（Word），.pdf，.xlsx/.xls（Excel），.csv。",
            input_params={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "文件的完整 URL，从用户消息中提取（不要构造或修改）",
                    }
                },
                "required": ["url"],
            },
        )
        super().__init__(card=card)

    async def invoke(self, inputs: dict, **kwargs) -> dict:
        """从 URL 下载并读取文件内容"""
        url = inputs.get("url", "")
        if not url:
            return {"error": "url is required", "content": ""}

        try:
            content = await self._fetch_file_content(url)
            return {"content": content}
        except Exception as e:
            return {"error": str(e), "content": ""}

    async def stream(self, inputs: dict, **kwargs):
        """流式调用（ReActAgent 不使用，但需实现抽象方法）"""
        result = await self.invoke(inputs, **kwargs)
        yield result

    async def _fetch_file_content(self, url: str) -> str:
        """从 URL 获取文件内容"""
        import aiohttp
        import ssl
        from urllib.parse import urlparse

        # 解析 URL 获取路径部分（去掉查询参数）
        parsed = urlparse(url)
        path = parsed.path

        url_lower = path.lower()
        # 判断文件类型
        is_docx = url_lower.endswith('.docx')
        is_pdf = url_lower.endswith('.pdf')
        is_excel = url_lower.endswith(('.xlsx', '.xls'))
        is_csv = url_lower.endswith('.csv')

        # 使用路径的扩展名作为临时文件后缀
        suffix = os.path.splitext(path)[1] or '.tmp'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name

        try:
            # 创建不验证 SSL 证书的 context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    resp.raise_for_status()
                    with open(tmp_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            f.write(chunk)

            if is_docx:
                return self.read_docx(tmp_path)
            elif is_pdf:
                return self.read_pdf(tmp_path)
            elif is_excel:
                return self.read_excel(tmp_path, is_xlsx=url_lower.endswith('.xlsx'))
            elif is_csv:
                return self.read_csv(tmp_path)
            else:
                return self.read_text(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def read_text(self, path: str) -> str:
        """读取纯文本文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, LookupError):
                continue
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    def read_docx(self, path: str) -> str:
        """读取 docx 文件"""
        try:
            from docx import Document
            doc = Document(path)
            return '\n'.join([p.text for p in doc.paragraphs])
        except ImportError:
            return "[无法读取 docx 文件，请安装 python-docx 库]"

    def read_pdf(self, path: str) -> str:
        """读取 pdf 文件"""
        try:
            import pymupdf
            doc = pymupdf.open(path)
            try:
                text = ''
                for page in doc:
                    text += page.get_text()
                return text
            finally:
                doc.close()
        except ImportError:
            return "[无法读取 pdf 文件，请安装 pymupdf 库]"

    def read_excel(self, path: str, is_xlsx: bool = True) -> str:
        """读取 excel 文件"""
        try:
            import pandas as pd
            df = pd.read_excel(path, engine='openpyxl' if is_xlsx else 'xlrd')
            return df.to_string(index=False)
        except ImportError:
            return "[无法读取 excel 文件，请安装 pandas 和 openpyxl/xlrd 库]"
        except Exception as e:
            return f"[读取 excel 文件失败: {e}]"

    def read_csv(self, path: str) -> str:
        """读取 csv 文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'gb18030']
        try:
            import pandas as pd
            for encoding in encodings:
                try:
                    df = pd.read_csv(path, encoding=encoding)
                    return df.to_string(index=False)
                except UnicodeDecodeError:
                    continue
            # 最后尝试忽略错误
            df = pd.read_csv(path, encoding='utf-8', errors='ignore')
            return df.to_string(index=False)
        except ImportError:
            # 没有 pandas，手动解析
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        except Exception as e:
            return f"[读取 csv 文件失败: {e}]"