from fastapi import APIRouter, HTTPException, status, Depends

from openjiuwen_studio.core.manager.login_manager.space import get_space_list, check_user_space
from openjiuwen_studio.core.manager.login_manager.user import get_current_user
from openjiuwen_studio.schemas.space import SpaceInfo, SpaceResponse
from openjiuwen_studio.schemas.common import ResponseModel
from openjiuwen_studio.core.manager.dfx.status import *

space_router = APIRouter()


def create_space_response(space_info_list: list) -> SpaceResponse:
    space_response = {
        "space_list": space_info_list,
        "has_personal_space": True,
        "team_space_num": 0,
        "recently_used_space_list": space_info_list,
        "space_total_num": len(space_info_list),
        "has_more": False
    }
    return SpaceResponse(**space_response)


@space_router.get("/{space_id}", response_model=ResponseModel[SpaceInfo])
async def get_user(
        space_id: str,
        current_user: dict = Depends(get_current_user)
):
    """Get a specific space by space ID"""
    try:
        space_info = check_user_space(space_id, current_user)

        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Space retrieved successfully",
            data=space_info.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@space_router.get("/", response_model=ResponseModel[dict])
def get_spaces(
        current_user: dict = Depends(get_current_user)
):
    """Get all spaces by user ID get from session token"""
    try:
        space_info_list = get_space_list(current_user)
        space_res = create_space_response(space_info_list)
        return ResponseModel(
            code=status.HTTP_200_OK,
            message="Space retrieved successfully",
            data=space_res.model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
