#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# Copyright (c) Huawei Technologies Co., Ltd. 2025-2025. All rights reserved.
from functools import wraps
from typing import Callable
from fastapi import status
from packaging.version import Version

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.models.plugin import PluginBaseDB, PluginPublishDB
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_val_from_dict, get_db_jw
from openjiuwen_studio.core.database import milliseconds


class PluginRepository():
    def __init__(self) -> None:
        pass

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error: Plugin data processing failed: {str(e)}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                     message=f"Error: Plugin processing exception:, {str(e)}").model_dump(
                    exclude_none=True)

        return wrapper

    @with_exception_handling
    def plugin_create(self, plugin_data: dict) -> dict:
        with get_db_jw() as db:
            plugin_db = JiuwenBaseRepository(db, PluginBaseDB)
            if not plugin_data:
                logger.debug(f"No plugin data to register: \ndata: {plugin_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                     message="No plugin data to register").model_dump(exclude_none=True)
            find_id = {
                "plugin_id": get_val_from_dict(plugin_data, ["plugin_id"]),
            }
            if not plugin_data.get('plugin_version', ""):
                plugin_data['plugin_version'] = PluginBaseDB.__version_none__
            timestamp = milliseconds()
            if "create_time" not in plugin_data:
                plugin_data["create_time"] = timestamp
            if "update_time" not in plugin_data:
                plugin_data["update_time"] = timestamp
            return plugin_db.register_dl_in_sql(find_id=find_id, dl=plugin_data).model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_get(self, query_body: dict) -> (dict, list[dict]):
        with get_db_jw() as db:
            plugin_db = JiuwenBaseRepository(db, PluginBaseDB)
            find_id = {
                "plugin_id": get_val_from_dict(query_body, ["plugin_id"]),
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
            }
            res = plugin_db.get_dl_in_sql(find_id=find_id, return_first_item=True, return_declarativebase=True)
            if res.code != status.HTTP_200_OK or not res.data:
                return res.model_dump(exclude_none=True), []
            tool_list: list[dict] = []
            for tool in res.data.tool_list:	 
                tool_list.append(tool.to_dict())

            return res.model_dump(exclude_none=True), tool_list

    @with_exception_handling
    def plugin_save(self, plugin_data: dict):
        with get_db_jw() as db:
            plugin_db = JiuwenBaseRepository(db, PluginBaseDB)
            if not plugin_data:
                logger.debug("No plugin data to update")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                     message="No plugin data to update").model_dump(exclude_none=True)
            find_id = {
                "plugin_id": get_val_from_dict(plugin_data, ["plugin_id"]),
                "space_id": get_val_from_dict(plugin_data, ["space_id", "spaceId"]),
            }
            find_id = PluginBaseDB.filter_invalid_keys(find_id)
            timestamp = milliseconds()
            if "update_time" not in plugin_data:
                plugin_data["update_time"] = timestamp
            return plugin_db.update_dl_in_sql(find_id=find_id, update_dl=plugin_data).model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_delete(self, query_body: dict) -> dict:
        with get_db_jw() as db:
            plugin_db = JiuwenBaseRepository(db, PluginBaseDB)
            # 删除操作需要谨慎，所以这里要求find_id必须所有值都非空
            find_id = {
                "plugin_id": get_val_from_dict(query_body, ["plugin_id"]),
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
            }
            return plugin_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_list(self, query_body: dict) -> dict:
        with get_db_jw() as db:
            plugin_db = JiuwenBaseRepository(db, PluginBaseDB)
            
            # 获取分页参数
            page = int(query_body.get("page", 1))
            size = int(query_body.get("size", 10))
            offset = (page - 1) * size
            return_range = [offset, size]
            
            find_id = {
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
            }
            find_id = PluginBaseDB.filter_invalid_keys(find_id)
            
            # 获取总数
            count_result = plugin_db.count_dl_in_sql(find_id=find_id)
            total = count_result.data if count_result.code == status.HTTP_200_OK else 0
            
            # 获取分页数据
            if total > 0:
                # 按更新时间降序排序
                result = plugin_db.get_dl_in_sql(
                    find_id=find_id,
                    order_cols_desc=["update_time"],
                    order_cols_asc=[],
                    return_range=return_range
                )
                
                if result.code == status.HTTP_200_OK and result.data:
                    plugin_list = result.data if isinstance(result.data, list) else [result.data]
                    # 清理 plugin_version 字段
                    for idx, data in enumerate(plugin_list):
                        if data.get("plugin_version", None) == PluginBaseDB.__version_none__:
                            plugin_list[idx].pop("plugin_version")
                else:
                    plugin_list = []
            else:
                plugin_list = []
            
            # 计算总页数
            total_pages = max(1, (total + size - 1) // size) if total > 0 else 1
            
            # 构建返回数据
            return_data = {
                "plugin_infos": plugin_list,
                "pagination": {
                    "total": total,
                    "total_pages": total_pages,
                    "page": page,
                    "page_size": size
                }
            }
            
            return ResponseModel(
                code=status.HTTP_200_OK,
                message="Get plugin list success",
                data=return_data
            ).model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_publish_create(self, publish_data: dict) -> dict:
        """Create plugin publish version"""
        with get_db_jw() as db:
            plugin_publish_db = JiuwenBaseRepository(db, PluginPublishDB)
            if not publish_data:
                logger.debug(f"No plugin data to publish: \ndata: {publish_data}")
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST,
                                     message="No plugin data to publish").model_dump(exclude_none=True)

            find_id = {
                "plugin_id": get_val_from_dict(publish_data, ["plugin_id"]),
                "space_id": get_val_from_dict(publish_data, ["space_id", "spaceId"]),
                "plugin_version": get_val_from_dict(publish_data, ["plugin_version"])
            }
            timestamp = milliseconds()
            if "create_time" not in publish_data:
                publish_data["create_time"] = timestamp
            if "update_time" not in publish_data:
                publish_data["update_time"] = timestamp

            return plugin_publish_db.register_dl_in_sql(find_id=find_id, dl=publish_data).model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_publish_get(self, query_body: dict) -> dict:
        """Get plugin publish version (latest version)"""
        with get_db_jw() as db:
            plugin_publish_db = JiuwenBaseRepository(db, PluginPublishDB)
            find_id = {
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
                "plugin_id": get_val_from_dict(query_body, ["plugin_id"]),
                "plugin_version": get_val_from_dict(query_body, ["plugin_version"])
            }

            find_id = PluginPublishDB.filter_invalid_keys(find_id)
            # Get all versions and return the latest one
            db_res = plugin_publish_db.get_dl_in_sql(find_id=find_id)
            if db_res.code != status.HTTP_200_OK or not db_res.data:
                return db_res.model_dump(exclude_none=True)

            # Sort by version and return the latest
            try:
                # Sort by version (simple string comparison for now)
                sorted_data = sorted(db_res.data, key=lambda x: Version(x.get('plugin_version', '0.0.0')), reverse=True)
                db_res.data = sorted_data[0] if sorted_data else None
            except Exception as e:
                logger.warning(f"Error sorting plugin versions: {e}")
                db_res.data = db_res.data[0] if db_res.data else None

            return db_res.model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_publish_list(self, query_body: dict) -> dict:
        """Get all plugin publish versions"""
        with get_db_jw() as db:
            plugin_publish_db = JiuwenBaseRepository(db, PluginPublishDB)
            find_id = {
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
                "plugin_id": get_val_from_dict(query_body, ["plugin_id"]),
            }

            db_res = plugin_publish_db.get_dl_in_sql(find_id=find_id)
            if db_res.code != status.HTTP_200_OK or not db_res.data:
                return db_res.model_dump(exclude_none=True)

            # Sort by version descending
            try:
                sorted_data = sorted(db_res.data, key=lambda x: Version(x.get('plugin_version', '0.0.0')), reverse=True)
                db_res.data = sorted_data
            except Exception as e:
                logger.warning(f"Error sorting plugin versions: {e}")

            return db_res.model_dump(exclude_none=True)

    @with_exception_handling
    def plugin_publish_delete(self, query_body: dict) -> dict:
        """Delete plugin publish version"""
        with get_db_jw() as db:
            plugin_publish_db = JiuwenBaseRepository(db, PluginPublishDB)
            find_id = {
                "plugin_id": get_val_from_dict(query_body, ["plugin_id"]),
                "space_id": get_val_from_dict(query_body, ["space_id", "spaceId"]),
                "plugin_version": get_val_from_dict(query_body, ["plugin_version"])
            }
            logger.info(f"find id: {find_id}")
            return plugin_publish_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)


plugin_repository = PluginRepository()