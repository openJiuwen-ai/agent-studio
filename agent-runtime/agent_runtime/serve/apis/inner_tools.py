# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved.
"""Inner tools API — 预置插件端点（文件解析 + 文档生成）
"""

import io
import uuid
from typing import Optional

import aiohttp
from docx import Document
from docx.oxml.ns import qn
from fastapi import APIRouter, HTTPException, Query
from openjiuwen.core.common.logging import workflow_logger
from pydantic import BaseModel, Field

from agent_runtime.common.config import settings
from agent_runtime.utils.file_parser import FileParser
from agent_runtime.storage.object_storage import S3StorageProvider
from jiuwen.common.utils.utils import illegal_url

inner_tools_router = APIRouter(tags=["inner_tools"])

# --- 请求/响应模型 ---


class FileResolveResponse(BaseModel):
    content: str = Field(..., description="文件内容")


class CreateDocumentRequest(BaseModel):
    input: str = Field(..., description="文档内容")
    document_name: str = Field(..., description="文档名")
    expires: Optional[int] = Field(default=None, description="签名URL有效期（天）")


class CreateDocumentResponse(BaseModel):
    url: str = Field(..., description="文档下载链接")


# --- 端点 ---


async def _download_file(file_url: str) -> bytes:
    """aiohttp 下载文件到内存
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(
            file_url,
            timeout=aiohttp.ClientTimeout(total=60),
            ssl=settings.object_storage.enable_ssl,
        ) as resp:
            resp.raise_for_status()
            return await resp.read()


@inner_tools_router.post(
    "/v1/inner-tools/file/resolve",
    response_model=FileResolveResponse,
    summary="解析文件",
)
async def resolve_file(
    file_url: str = Query(..., description="文件访问url"),
):
    """根据 file_url 下载并解析文件内容，支持 txt/csv/xlsx/docx"""
    # SSRF 防护
    if illegal_url(file_url):
        workflow_logger.warning("Resolve file rejected by SSRF check: {}", file_url)
        raise HTTPException(status_code=400, detail="非法文件URL")

    # 下载文件
    try:
        data = await _download_file(file_url)
    except Exception as e:
        workflow_logger.error("Download file failed: url={}, error:{}", file_url, e, exc_info=True)
        raise HTTPException(status_code=400, detail=f"下载文件失败: {e}") from e

    # 按扩展名分发解析
    suffix = FileParser.get_suffix(file_url)
    try:
        content = FileParser.parse(data, suffix)
    except Exception as e:
        workflow_logger.error("Parse file failed: suffix={}, error:{}", suffix, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"解析文件失败: {e}") from e

    # 截断
    content = FileParser.truncate(content, settings.object_storage.max_resolve_size)
    return FileResolveResponse(content=content)


@inner_tools_router.post(
    "/v1/inner-tools/document/create",
    response_model=CreateDocumentResponse,
    summary="文档生成",
)
async def create_document(req: CreateDocumentRequest):
    """根据文本内容生成 docx，上传 OBS 返回临时下载链接"""
    # 文件名校验
    name = FileParser.build_legal_name(req.document_name)

    # 生成 docx
    doc = Document()
    rpr_default = (
        doc.styles.element.find(qn("w:docDefaults"))
        .find(qn("w:rPrDefault"))
        .find(qn("w:rPr"))
    )
    r_fonts = rpr_default.find(qn("w:rFonts"))
    r_fonts.set(qn("w:eastAsia"), "宋体")
    r_fonts.attrib.pop(qn("w:eastAsiaTheme"), None)
    for line in req.input.split("\n"):
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    # 上传 OBS staging 桶
    object_key = f"file/{uuid.uuid4()}/{name}.docx"
    bucket = settings.object_storage.staging_bucket or None
    storage = S3StorageProvider.instance()
    try:
        await storage.put_object_bytes(object_key, docx_bytes, bucket_name=bucket)
    except Exception as e:
        workflow_logger.error(
            "Upload document failed: {}, {}", object_key, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"上传文档失败: {e}") from e

    # 生成签名下载 URL
    expires_days = (
        req.expires
        if req.expires and req.expires > 0
        else settings.object_storage.expire_time
    )
    expires_seconds = expires_days * 86400
    try:
        url = await storage.get_presigned_url(
            object_key, expires_seconds, bucket_name=bucket
        )
    except Exception as e:
        workflow_logger.error(
            "Generate presigned url failed: {}, {}", object_key, e, exc_info=True
        )
        raise HTTPException(status_code=500, detail=f"生成下载链接失败: {e}") from e

    return CreateDocumentResponse(url=url)
