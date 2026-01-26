from functools import wraps
from typing import Callable

from fastapi import status
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    get_db_jw, get_val_from_dict)
from openjiuwen_studio.models.reference import ReferenceDB
from openjiuwen_studio.schemas.common import ResponseModel


class ReferenceRepository():
    def __init__(self) -> None:
        pass

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: Reference data processing failed")
                logger.debug(f"Reference processing exception: {type(e).__name__}", exc_info=True)
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message=f"Error: Reference db data could not be processed: {type(e).__name__}").model_dump(exclude_none=True)
        return wrapper

    @with_exception_handling
    def reference_create(self, reference_data: dict) -> dict:
        """
        创建引用关系

        入参:
        {
            "space_id": str,           # 空间ID
            "referenced_type": str,    # 被引用者类型: TOOL/WORKFLOW
            "referenced_id": str,      # 被引用者ID
            "referenced_version": str, # 被引用者版本 (可选，默认为'draft')
            "referer_type": str,       # 引用者类型: WORKFLOW/AGENT
            "referer_id": str,         # 引用者ID
            "referer_version": str     # 引用者版本 (可选，默认为'draft')
        }
        """
        with get_db_jw() as db:
            reference_db = JiuwenBaseRepository(db, ReferenceDB)
            if not reference_data:
                logger.debug(f"No reference data to register: \ndata: {reference_data}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST,
                    message="No reference data to register"
                ).model_dump(exclude_none=True)

            find_id = {
                "space_id": get_val_from_dict(reference_data, ["space_id"]),
                "referenced_type": get_val_from_dict(reference_data, ["referenced_type"]),
                "referenced_id": get_val_from_dict(reference_data, ["referenced_id"]),
                "referenced_version": get_val_from_dict(reference_data, ["referenced_version"]),
                "referer_type": get_val_from_dict(reference_data, ["referer_type"]),
                "referer_id": get_val_from_dict(reference_data, ["referer_id"]),
                "referer_version": get_val_from_dict(reference_data, ["referer_version"]),
            }

            # 设置默认版本
            if not find_id["referenced_version"]:
                find_id["referenced_version"] = ReferenceDB.__version_none__
            if not find_id["referer_version"]:
                find_id["referer_version"] = ReferenceDB.__version_none__

            timestamp = milliseconds()
            if "create_time" not in reference_data:
                reference_data["create_time"] = timestamp
            if "update_time" not in reference_data:
                reference_data["update_time"] = timestamp

            return reference_db.register_dl_in_sql(find_id=find_id, dl=reference_data).model_dump(exclude_none=True)

    @with_exception_handling
    def reference_list_by_referenced(self, space_id: str, referenced_type: str, referenced_id: str) -> dict:
        """
        根据被引用者查询引用关系列表

        入参:
        - space_id: str           # 空间ID
        - referenced_type: str    # 被引用者类型: TOOL/WORKFLOW
        - referenced_id: str      # 被引用者ID
        """
        with get_db_jw() as db:
            reference_db = JiuwenBaseRepository(db, ReferenceDB)

            find_id = {
                "space_id": space_id,
                "referenced_type": referenced_type,
                "referenced_id": referenced_id,
            }

            res = reference_db.get_dl_in_sql(find_id=find_id)
            return res.model_dump(exclude_none=True)

    @with_exception_handling
    def get_records_by_referer_with_version(self, space_id: str, referer_type: str, referer_id: str,
                                           referer_version: str):
        """
        根据引用者（带版本）查询引用关系记录

        入参:
        - space_id: str           # 空间ID
        - referer_type: str       # 引用者类型: WORKFLOW/AGENT
        - referer_id: str         # 引用者ID
        - referer_version: str    # 引用者版本
        """
        with get_db_jw() as db:
            reference_db = JiuwenBaseRepository(db, ReferenceDB)

            find_id = {
                "space_id": space_id,
                "referer_type": referer_type,
                "referer_id": referer_id,
                "referer_version": referer_version,
            }
            return reference_db.get_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)


    @with_exception_handling
    def reference_delete_by_referer_with_version(
        self, space_id: str, referer_type: str, referer_id: str, referer_version: str
    ) -> dict:
        """
        根据引用者（带版本）批量删除引用关系

        入参:
        - space_id: str           # 空间ID
        - referer_type: str       # 引用者类型: WORKFLOW/AGENT
        - referer_id: str         # 引用者ID
        - referer_version: str    # 引用者版本
        """
        with get_db_jw() as db:
            reference_db = JiuwenBaseRepository(db, ReferenceDB)

            find_id = {
                "space_id": space_id,
                "referer_type": referer_type,
                "referer_id": referer_id,
                "referer_version": referer_version,
            }

            return reference_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)

    @with_exception_handling
    def reference_delete_by_referer(self, space_id: str, referer_type: str, referer_id: str) -> dict:
        """
        根据引用者批量删除引用关系

        入参:
        - space_id: str           # 空间ID
        - referer_type: str       # 引用者类型: WORKFLOW/AGENT
        - referer_id: str         # 引用者ID
        """
        with get_db_jw() as db:
            reference_db = JiuwenBaseRepository(db, ReferenceDB)

            find_id = {
                "space_id": space_id,
                "referer_type": referer_type,
                "referer_id": referer_id,
            }

            return reference_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)


reference_repository = ReferenceRepository()