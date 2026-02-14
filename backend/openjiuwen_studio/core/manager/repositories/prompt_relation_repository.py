import copy
from functools import wraps
from typing import Callable

from fastapi import status
from sqlalchemy import update
from sqlalchemy.orm import Session

from openjiuwen.core.common.logging import logger
from openjiuwen_studio.core.database import milliseconds
from openjiuwen_studio.core.manager.repositories import JiuwenBaseRepository
from openjiuwen_studio.core.manager.repositories.jiuwen_base_repository import get_db_jw
from openjiuwen_studio.models.prompt_relation import PromptRelationDB
from openjiuwen_studio.schemas import related_member
from openjiuwen_studio.schemas.common import ResponseModel


class PromptRelationRepository():
    def __init__(self) -> None:
        pass
    # def __init__(self, db: Session) -> None:
    #     # 关键：显式写出 [A] 和 [B]
    #     self._prompt_relation_db: JiuwenBaseRepository[PromptRelationDB] = JiuwenBaseRepository(db, PromptRelationDB)

    def with_exception_handling(func) -> Callable:
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.error("Error: prompt&workflow&agent db data preprocessing error")
                logger.debug(f"Exception details: {type(e).__name__}", exc_info=True)
                return ResponseModel(code=status.HTTP_400_BAD_REQUEST, 
                                     message=f"Error: prompt&workflow&agent db data preprocessing error, {type(e).__name__}")
        return wrapper

    @with_exception_handling
    def create_prompt_relate_tbl(self, space_id: str, prompt_info: related_member.RelatedMemberInfo, 
                                 relate_member_info: related_member.RelatedMemberInfo, 
                                 db_session: Session | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            prompt_relation_db = JiuwenBaseRepository(db, PromptRelationDB)
            # 先将agent/workflow相关的所有prompt的is_acitve置false
            find_id = {
                "space_id": space_id,
                "id": relate_member_info.id,
                "version": relate_member_info.version,
                "type": relate_member_info.type.value,
                "is_active": 1,
            }
            is_active_false = {"is_active": 0}
            # 设置 commit=False，让外层统一控制事务提交
            prompt_relation_db._update_dl_in_sql_directly(find_id=find_id, update_dl=is_active_false, commit=False)

            # 创建或者更新数据
            find_id.update({
                "prompt_id": prompt_info.id,
                "prompt_version": prompt_info.version,
            })
            update_dl = copy.deepcopy(find_id)
            update_dl.update({"prompt_name": prompt_info.name, "name": relate_member_info.name})
            find_id.pop("is_active", None)
            timestamp = milliseconds()
            create_dl = {"create_time": timestamp}
            if "update_time" not in update_dl:
                update_dl["update_time"] = timestamp
            result = prompt_relation_db.update_dl_in_sql(find_id=find_id, update_dl=update_dl,
                                                        create_dl=create_dl)
            # 统一提交事务
            if result.code == status.HTTP_200_OK:
                db.commit()
            else:
                db.rollback()
            return result
    
    '''
    description: 删除相关联的prompt_relation数据
    param {str} space_id 空间id
    param {related_member} delete_member_info  用于删除定位的信息
    param {Session} db_session  可选的输入数据库会话
    return {*}
    '''
    @with_exception_handling
    def delete_prompt_relate_tbl(self, space_id: str, delete_member_info: related_member.RelatedMemberInfo,
                                 db_session: Session | None = None) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            prompt_relation_db = JiuwenBaseRepository(db, PromptRelationDB)
            if delete_member_info.type == related_member.MemberType.PROMPT:
                # prompt类型
                find_id = {
                    "space_id": space_id,
                    "prompt_id": delete_member_info.id,
                    "prompt_version": delete_member_info.version,
                }
            else:
                # agent/workflow类型
                find_id = {
                    "space_id": space_id,
                    "id": delete_member_info.id,
                    "version": delete_member_info.version,
                    "type": delete_member_info.type.value,
                }
            result = prompt_relation_db.unregister_dl_in_sql(find_id=find_id)
            # 统一提交事务
            if result.code == status.HTTP_200_OK:
                db.commit()
            else:
                db.rollback()
            return result
    
    '''
    description: 获取相关联的promt_realte数据
    param {str} space_id    空间id
    param {related_member} find_member_info     定位的信息
    param {bool} only_active        是否只返回活跃的关联数据
    param {Session} db_session      可选的数据库会话
    return {*}
    '''
    @with_exception_handling
    def get_prompt_relate_tbl(self, space_id: str, find_member_info: related_member.RelatedMemberInfo,
                              only_active: bool = False, db_session: Session | None = None) -> ResponseModel[list[dict] | None]:
        with get_db_jw(db_session) as db:
            prompt_relation_db = JiuwenBaseRepository(db, PromptRelationDB)
            if find_member_info.type == related_member.MemberType.PROMPT:
                find_id = {
                    "space_id": space_id,
                    "prompt_id": find_member_info.id,
                    "prompt_version": find_member_info.version,
                }
            else:
                find_id = {
                    "space_id": space_id,
                    "id": find_member_info.id,
                    "version": find_member_info.version,
                    "type": find_member_info.type.value,
                }
            if only_active:
                find_id["is_active"] = 1
            return prompt_relation_db.get_dl_in_sql(find_id=find_id, order_cols_desc=["update_time"])

    '''
    description: 通用方法。当 workflow/agent 名称更新时，同步更新 prompt_relation 表中对应关联记录的 name。
    - WORKFLOW: 关联表 id(aw_id) 格式为 "工作流id&工作流节点id"，用 LIKE 匹配。
    - AGENT: 关联表 id(aw_id) 即为智能体id，精确匹配。
    param {str} space_id 空间id
    param {str} member_type "WORKFLOW" | "AGENT"
    param {str} member_id 工作流id 或 智能体id
    param {str} new_name 新名称
    param {Session} db_session 可选的数据库会话
    return {ResponseModel}
    '''
    @with_exception_handling
    def update_member_name_in_prompt_relation(
        self,
        space_id: str,
        member_type: str,
        member_id: str,
        new_name: str,
        db_session: Session | None = None,
    ) -> ResponseModel[None]:
        with get_db_jw(db_session) as db:
            prompt_relation_db = JiuwenBaseRepository(db, PromptRelationDB)
            find_id = {
                "space_id": space_id,
                "type": member_type,
            }
            if member_type == "WORKFLOW":
                # id 格式为 "workflow_id&node_id"
                other_limitations = [PromptRelationDB.id.like(f"{member_id}&%")]
            else:
                # AGENT: id 即为智能体id
                other_limitations = [PromptRelationDB.id == member_id]
            result = prompt_relation_db.get_dl_in_sql(
                find_id=find_id,
                other_sqlalchemy_limitations=other_limitations,
            )
            if result.code != status.HTTP_200_OK or not result.data:
                return ResponseModel(code=status.HTTP_200_OK, message="No prompt_relation to update.")
            timestamp = milliseconds()
            primary_ids = [row["primary_id"] for row in result.data]
            stmt = (
                update(PromptRelationDB)
                .where(PromptRelationDB.primary_id.in_(primary_ids))
                .values(name=new_name, update_time=timestamp)
            )
            try:
                db.execute(stmt)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error("Error updating member name in prompt_relation: %s", e)
                return ResponseModel(
                    code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Error updating prompt_relation name: {e!s}",
                )
            return ResponseModel(
                code=status.HTTP_200_OK,
                message=f"Updated {member_type} name in {len(result.data)} prompt_relation record(s).",
            )


prompt_relation_repository = PromptRelationRepository()