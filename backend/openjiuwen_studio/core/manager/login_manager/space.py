from typing import List

from fastapi import HTTPException, Depends, status

from openjiuwen.core.common.logging import logger

from openjiuwen_studio.core.manager.repositories.user_repository import user_repository
from openjiuwen_studio.core.manager.dfx.status import get_space_status_by_id
from openjiuwen_studio.core.manager.login_manager.user import get_user_id
from openjiuwen_studio.schemas.space import SpaceInfo, SpaceDBPd, SpaceBase
from openjiuwen_studio.schemas.user import RoleType


def create_space_info(space_db: SpaceDBPd) -> SpaceInfo:
    # 获取 SpaceDBPd 的基础字段
    base_fields = set(SpaceBase.__fields__.keys())
    base_data = space_db.dict(include=base_fields)

    # 添加 SpaceInfo 的特有字段（使用默认值）
    return SpaceInfo(**base_data)


def get_space_by_user_id(user_id: str) -> List[SpaceInfo]:
    ret = user_repository.get_space_id(user_id)
    if ret["code"] != status.HTTP_200_OK:
        raise HTTPException(status_code=404, detail="space id not found")
    space_list = ret.get("data", [])
    space_info_list = []
    
    # 容错处理：如果某个 space 查询失败，记录警告但继续处理其他 space
    for space_id in space_list:
        ret = user_repository.get_space_tbl(space_id)
        if ret["code"] != status.HTTP_200_OK:
            error_msg = ret.get('message', 'unknown error')
            error_code = ret.get('code')
            logger.warning(
                f"[GET_SPACE_BY_USER] Failed to get space {space_id} for user {user_id}: "
                f"{error_msg}, code: {error_code}"
            )
            continue  # 跳过失败的 space，继续处理其他的
        try:
            space_db = ret["data"]
            space_info = create_space_info(SpaceDBPd(**space_db))
            space_info_list.append(space_info)
        except Exception as e:
            logger.warning(
                f"[GET_SPACE_BY_USER] Failed to create space info for space {space_id}: {str(e)}"
            )
            continue  # 跳过创建失败的 space，继续处理其他的

    if not space_info_list:
        logger.error(f"[GET_SPACE_BY_USER] No valid spaces found for user {user_id} from space_list: {space_list}")
        raise HTTPException(status_code=404, detail="No valid spaces found for user")
    
    return space_info_list


def find_space_by_id(space_id: str, space_info_list: List[SpaceInfo]) -> SpaceInfo:
    """根据空间ID在空间列表中查找特定空间"""
    for space in space_info_list:
        if space_id == space.space_id:
            return space
    raise HTTPException(status_code=404, detail=f"User doesn't have space id: {space_id}")


def get_space_list(current_user: dict) -> List[SpaceInfo]:
    """Get all spaces by user ID get from session token"""
    try:
        user_id = get_user_id(current_user)
        if user_id is None:
            raise HTTPException(status_code=404, detail="user id not found")

        return get_space_by_user_id(user_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve space list: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve space list") from e


def check_user_space(space_id: str, current_user: dict) -> SpaceInfo:
    """check the access by space id"""
    try:
        # Trigger-fired executions run as system_trigger — bypass space check
        user_data = current_user.get("data") or {}
        if user_data.get("user_id_str") == "system_trigger":
            # Return a minimal SpaceInfo for system trigger - no validation needed
            return SpaceInfo(
                space_id=space_id,
                spacename="System Trigger",
                description="",
                role_type=RoleType.SUPER_USER,
            )

        space_info_list = get_space_list(current_user)
        space_info = None
        for space in space_info_list:
            if space_id == space.space_id:
                space_info = space
                break
        if space_info is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"space_id {space_id} Access Denied")
        get_space_status_by_id(space_info, space_id)
        return space_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check user space: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
