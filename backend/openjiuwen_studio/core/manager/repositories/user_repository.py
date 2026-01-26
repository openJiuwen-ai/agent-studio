from functools import wraps
from typing import Callable, List, Optional, Union

from fastapi import status
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import (
    get_db_jw, get_val_from_dict)
from openjiuwen_studio.models.user import SpaceDB, SpaceUserDB, UserDB
from openjiuwen_studio.schemas.common import ResponseModel


class UserRepository():
    def __init__(self) -> None:
        pass

    # def __init__(self, db: Session) -> None:
    #     self._user_db: JiuwenBaseRepository[UserDB] = JiuwenBaseRepository(db, UserDB)
    #     self._space_db: JiuwenBaseRepository[SpaceDB] = JiuwenBaseRepository(db, SpaceDB)
    #     self._space_user_db: JiuwenBaseRepository[SpaceUserDB] = JiuwenBaseRepository(db, SpaceUserDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error: user&space db data preprocessing failed: {str(e)}")
                return ResponseModel(
                    code=status.HTTP_400_BAD_REQUEST, 
                    message=f"Error: user&space db data preprocessing failed: {str(e)}"
                ).model_dump(exclude_none=True)
        return wrapper

    '''
    description: 往数据库创建user数据
    param {dict} user_info  待创建数据, email要求必须要有
    return {*}
    '''
    @with_exception_handling
    def create_user_tbl(self, user_info: dict):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": get_val_from_dict(user_info, ["email"]),
            }
            return user_db.register_dl_in_sql(find_id=find_id, dl=user_info).model_dump(exclude_none=True)
    
    @with_exception_handling
    def update_user_tbl(self, user_info: dict):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": get_val_from_dict(user_info, ["email"]),
            }
            return user_db.update_dl_in_sql(find_id=find_id, update_dl=user_info).model_dump(exclude_none=True)
    
    '''
    description: 从数据库中查找user数据是否存在
    param {Optional} email  email和下面的session_key至少要有一个
    param {Optional} session_key
    param {int} role_type   
    return {*}
    '''
    @with_exception_handling
    def find_user_tbl(self, email: Optional[str] = None, session_key: Optional[str] = None):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": email,
                "session_key": session_key,
            }
            find_id = UserDB.filter_invalid_keys(find_id)
            return user_db._find_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)
       
    '''
    description: 从数据库中获取user数据
    param {Optional} email  email和下面的session_key至少要有一个
    param {Optional} session_key
    param {int} role_type
    return {*}
    '''
    @with_exception_handling
    def get_user_tbl(self, email: Optional[str] = None, session_key: Optional[str] = None):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": email,
                "session_key": session_key,
            }
            find_id = UserDB.filter_invalid_keys(find_id)
            return user_db.get_dl_in_sql(find_id=find_id, return_first_item=True).model_dump(exclude_none=True)

    '''
    description: 更新数据库中user的session_key
    param {str} email   email作为健值定位user
    param {str} session_key
    return {*}
    '''
    @with_exception_handling
    def update_session_key(self, email: str, session_key: str):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": email,
            }
            update_data = {
                "session_key": session_key,
            }
            return user_db.update_dl_in_sql(find_id=find_id, update_dl=update_data).model_dump(exclude_none=True)
    
    '''
    description: 删除数据库中的user
    param {Optional} email  email和下面的session_key至少要有一个
    param {Optional} session_key
    param {int} role_type
    return {*}
    '''
    @with_exception_handling
    def delete_user_tbl(self, email: Optional[str] = None, session_key: Optional[str] = None, role_type: int = 0):
        with get_db_jw() as db:
            user_db = JiuwenBaseRepository(db, UserDB)
            find_id = {
                "email": email,
                "session_key": session_key,
            }
            find_id = UserDB.filter_invalid_keys(find_id)
            return user_db.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)

    '''
    description: 往数据库中的space和space_user表中新增space数据
    param {dict} space_db   待创建的space数据
    return {*}
    '''
    @with_exception_handling
    def create_space_tbl(self, space_db: dict):
        with get_db_jw() as db:
            space_repos = JiuwenBaseRepository(db, SpaceDB)
            space_user_repos = JiuwenBaseRepository(db, SpaceUserDB)
            find_id_space = {
                "space_id": get_val_from_dict(space_db, ["space_id"]),
            }
            reg_space = space_repos.register_dl_in_sql(find_id=find_id_space, dl=space_db)
            if reg_space.code != status.HTTP_200_OK:
                return reg_space.model_dump(exclude_none=True)
            find_id_spase_user = {
                "space_id": get_val_from_dict(space_db, ["space_id"]),
                "user_id_str": get_val_from_dict(space_db, ["user_id_str"]),
            }
            reg_space_user = space_user_repos.register_dl_in_sql(find_id=find_id_spase_user,
                                                      dl=space_db)
            if reg_space_user.code != status.HTTP_200_OK:
                # 删除注册成功的space表
                space_repos.unregister_dl_in_sql(find_id=find_id_space)
            return reg_space_user.model_dump(exclude_none=True)
    
    @with_exception_handling
    def update_space_tbl(self, space_db: dict):
        with get_db_jw() as db:
            with db.begin():
                space_repos = JiuwenBaseRepository(db, SpaceDB)
                space_user_repos = JiuwenBaseRepository(db, SpaceUserDB)
                find_id_space = {
                    "space_id": get_val_from_dict(space_db, ["space_id"]),
                }
                reg_space = space_repos.update_dl_in_sql(find_id=find_id_space, update_dl=space_db)
                if reg_space.code != status.HTTP_200_OK:
                    return reg_space.model_dump(exclude_none=True)
                find_id_spase_user = {
                    "space_id": get_val_from_dict(space_db, ["space_id"]),
                    "user_id_str": get_val_from_dict(space_db, ["user_id_str"]),
                }
                return space_user_repos.update_dl_in_sql(
                    find_id=find_id_spase_user,
                    update_dl=space_db
                ).model_dump(exclude_none=True)
    
    @with_exception_handling
    def get_space_tbl(self, space_id: Union[int, str]):
        with get_db_jw() as db:
            space_repos = JiuwenBaseRepository(db, SpaceDB)
            find_id = {
                "space_id": str(space_id),
            }
            return space_repos.get_dl_in_sql(find_id=find_id, return_first_item=True).model_dump(exclude_none=True)
    
    @with_exception_handling
    def get_space_id(self, user_id: Union[int, str]):
        with get_db_jw() as db:
            space_user_repos = JiuwenBaseRepository(db, SpaceUserDB)
            find_id = {
                "user_id_str": str(user_id),
            }
            res = space_user_repos.get_dl_in_sql_with_cols(find_id=find_id, cols_find=['space_id'])
            if res.code != status.HTTP_200_OK:
                return res.model_dump(exclude_none=True)
            res.data = [d['space_id'] for d in res.data]
            return res.model_dump(exclude_none=True)

    @with_exception_handling
    def delete_space_tbl(self, space_id: Union[int, str]):
        with get_db_jw() as db:
            space_repos = JiuwenBaseRepository(db, SpaceDB)
            space_user_repos = JiuwenBaseRepository(db, SpaceUserDB)
            find_id = {
                "space_id": str(space_id),
            }
            del_space = space_repos.unregister_dl_in_sql(find_id=find_id)
            if del_space.code != status.HTTP_200_OK:
                return del_space.model_dump(exclude_none=True)
            return space_user_repos.unregister_dl_in_sql(find_id=find_id).model_dump(exclude_none=True)
        

user_repository = UserRepository()